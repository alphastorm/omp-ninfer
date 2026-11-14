#!/usr/bin/env python3
"""Retarget QUICKSTART identities without rewriting provenance or acceptance prose.

    python3 scripts/retarget_guide.py --from v0.20.0 --to v0.21.0 [--guide PATH] [--check]

Identities come from the two release manifests, compatibility authorities and profile
snapshots. A shared identity that splits between components needs an unambiguous component
anchor in its original Markdown block. Previous-distinct identities come from older ready
manifests, not from prose guesses. Immutable predecessor links remain untouched. The whole
guide remains the acceptance document; this tool does not grant release readiness.
A completed guide is checked for stale scoped component identities, never rewritten.
"""
from __future__ import annotations

import argparse
import bisect
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, NamedTuple
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import documented_route
from release_io import atomic_write
from verify_release import COMPONENT_TAG_RE, MARKDOWN_LINK_RE, checkpoint_host_directory

ROOT = Path(__file__).resolve().parents[1]
RELEASE_RE = re.compile(r"v\d+\.\d+\.\d+\Z")
VERSION_RE = re.compile(r"v?\d+\.\d+\.\d+\Z")
HEX_RE = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")
DIGEST_RE = re.compile(r"sha256:[0-9a-fA-F]{64}\Z")
IMAGE_RE = re.compile(r"[^\s@]+@sha256:[0-9a-fA-F]{64}\Z")
PACKAGE_KEYS = {"package_name", "artifact_name", "asset_name", "filename"}
CONTAINER = "rtx5090-container"
PROJECTIONS = {
    "hex": ("full", "prefix8", "prefix12"),
    "integer": ("full", "grouped"),
}
INTEGER_IDENTITY_KEYS = {
    "artifact_bytes", "asset_bytes", "binary_archive_bytes", "package_bytes",
    "source_archive_bytes", "bytes", "release_id", "artifact_release_id",
    "asset_id", "artifact_asset_id",
}
NAME_IDENTITY_KEYS = {
    "deployment_profile", "build_profile", "release_id", "release_instance_id",
    "checkpoint_mount_target",
}


class Refusal(ValueError):
    """An identity or document cannot be retargeted without guessing."""


class Leaf(NamedTuple):
    file: Path
    pointer: str
    line: int
    value: str
    scope: str
    kind: str = ""


class Replacement(NamedTuple):
    value: str | None
    tier: int
    origin: str = ""
    projection: str = ""


IdentityMap = dict[str, dict[str, set[Replacement]]]


class MarkdownBlock(NamedTuple):
    start: int
    end: int
    line: int
    fenced: bool


def immutable_regions(text: str, document: Path | str) -> tuple[tuple[int, int], ...]:
    """Every page supports balanced, non-nested record comment pairs.

    Markdown additionally supports Records to EOF and released changelog sections, including
    their tag definitions; the Unreleased comparison reference remains living.
    """
    document = Path(document)
    regions: list[tuple[int, int]] = []
    offset = 0
    html = document.suffix == ".html"
    opened: tuple[int, int] | None = None
    fence: str | None = None
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        fenced = re.match(r"^\s*(`{3,}|~{3,})", line) if not html else None
        if fenced:
            if fence is None:
                fence = fenced[1]
            elif fenced[1][0] == fence[0] and len(fenced[1]) >= len(fence):
                fence = None
        if not fenced and fence is None:
            visible = line if html else re.sub(r"(`+)(?!`).*?(?<!`)\1(?!`)", "", line)
            marker = visible.strip()
            if (any(value in visible for value in ("<!-- records -->", "<!-- /records -->"))
                    and line.strip() not in {"<!-- records -->", "<!-- /records -->"}):
                raise Refusal(f"{document}:{number}: records marker must occupy its own line")
            if marker == "<!-- records -->":
                if opened is not None:
                    raise Refusal(f"{document}:{number}: nested or duplicated records marker")
                opened = (offset, number)
            elif marker == "<!-- /records -->":
                if opened is None:
                    raise Refusal(f"{document}:{number}: records closing marker has no opener")
                regions.append((opened[0], offset + len(line)))
                opened = None
        offset += len(line)
    if opened is not None:
        raise Refusal(f"{document}:{opened[1]}: unclosed records marker")
    if html:
        return tuple(regions)
    records = False
    released = False
    fence = None
    offset = 0
    start: int | None = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            if fence is None:
                fence = marker[1]
            elif marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                fence = None
        if fence is None and not marker:
            if re.fullmatch(r" {0,3}##\s+Records(?:\s+#+)?\s*", line):
                records = True
            if document.name == "CHANGELOG.md" and re.match(r"^##\s+\[(?:v)?\d+\.\d+\.\d+\]", line):
                released = True
        comparison = document.name == "CHANGELOG.md" and re.match(r"^\[Unreleased\]:\s*", line)
        marked = records or (released and not comparison)
        if marked and start is None:
            start = offset
        elif not marked and start is not None:
            regions.append((start, offset))
            start = None
        offset += len(line)
    if start is not None:
        regions.append((start, len(text)))
    merged: list[tuple[int, int]] = []
    for start, end in sorted(regions):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return tuple(merged)


def records_mask(text: str, document: Path | str) -> str:
    pieces = []
    cursor = 0
    for start, end in immutable_regions(text, document):
        pieces.extend((text[cursor:start], re.sub(r"[^\r\n]", " ", text[start:end])))
        cursor = end
    return "".join([*pieces, text[cursor:]])


def evidence_reference(value: str) -> str | None:
    if any(character.isspace() for character in value):
        return None
    target = urlsplit(value)
    if target.scheme or target.netloc:
        if re.search(r"/measurements/[^/]+$", target.path):
            return f"{target.scheme}://{target.netloc}{target.path}"
        return None
    match = re.fullmatch(r"(?:\.\./)*(?:docs/)?measurements/(.+)", target.path)
    return "docs/measurements/" + match[1] if match else None


def identity_class(pointer: str, value: str) -> str | None:
    """Only identity-shaped string leaves participate, never free-form prose or numbers."""
    key = pointer.rsplit("/", 1)[-1]
    if HEX_RE.fullmatch(value):
        return "hex"
    if DIGEST_RE.fullmatch(value):
        return "digest"
    if IMAGE_RE.fullmatch(value):
        return "image"
    if COMPONENT_TAG_RE.fullmatch(value):
        return "component-tag"
    if VERSION_RE.fullmatch(value):
        return "version"
    if evidence_reference(value):
        return "evidence"
    if re.fullmatch(r"https?://\S+", value):
        return "url"
    if key in PACKAGE_KEYS and re.fullmatch(r"[\w.+-]+", value):
        return "package"
    if key == "checkpoint_host_directory" and value:
        return "checkpoint"
    return None


def leaf_scope(file: Path, pointer: str) -> str:
    parts = pointer.strip("/").split("/")
    if parts[0] in {"release", "product_release"} or parts[-1] == "checkpoint_host_directory":
        return "release"
    profile_parts = file.parts[file.parts.index("profiles") + 1:] if "profiles" in file.parts else ()
    native = next((part for part in profile_parts if re.fullmatch(r"rtx\d+", part)), None)
    if native:
        return f"{native}-windows-native"
    if parts[:2] == ["components", "ninfer_variants"] or parts[0] == "runtime_variants":
        return next((part[3:] for part in parts if part.startswith("id=")), "release")
    if parts[:2] == ["components", "omp"] or parts[0] == "client" or "client_distribution" in parts:
        return "client"
    if parts[:2] == ["components", "model"] or parts[0] == "model":
        return "model"
    if parts[:2] == ["components", "ninfer"] or parts[0] in {"runtime_identity", "server"}:
        return CONTAINER
    if parts[0] == "profiles" and "runtime" in parts:
        return CONTAINER
    if "gpu_qualification" in parts or parts[:2] == ["composition", "ninfer_lifecycle_source_commit"]:
        return CONTAINER
    if parts[0] == "composition" and parts[-1].endswith("source_commit"):
        return "client"
    return "release"


def string_leaves(file: Path, *, projections: bool = False) -> dict[str, Leaf]:
    """Flatten JSON with stable id-keyed lists and exact source locations."""
    try:
        text = file.read_text(encoding="utf-8")
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise Refusal(f"{file}:{error.lineno}: invalid JSON: {error.msg}") from error
    except (OSError, UnicodeError) as error:
        raise Refusal(f"{file}:1: cannot read identity source: {error}") from error
    decoder = json.JSONDecoder()
    locations: dict[tuple[str, ...], int] = {}

    def scan(position: int, parts: tuple[str, ...]) -> int:
        while text[position].isspace():
            position += 1
        if text[position] in "{[":
            object_node = text[position] == "{"
            closing = "}" if object_node else "]"
            position += 1
            index = 0
            while True:
                while text[position].isspace() or text[position] == ",":
                    position += 1
                if text[position] == closing:
                    return position + 1
                if object_node:
                    key, position = decoder.raw_decode(text, position)
                    while text[position].isspace() or text[position] == ":":
                        position += 1
                else:
                    key = str(index)
                position = scan(position, (*parts, key))
                index += 1
        value, end = decoder.raw_decode(text, position)
        if isinstance(value, str) or (projections and isinstance(value, int) and not isinstance(value, bool)):
            locations[parts] = text.count("\n", 0, position) + 1
        return end

    scan(0, ())
    leaves: dict[str, Leaf] = {}

    def flatten(value: Any, parts: tuple[str, ...], source: tuple[str, ...]) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                flatten(child, (*parts, key), (*source, key))
        elif isinstance(value, list):
            seen: set[str] = set()
            for index, child in enumerate(value):
                key = "id=" + child["id"] if isinstance(child, dict) and isinstance(child.get("id"), str) else str(index)
                if key in seen:
                    raise Refusal(f"{file}:1: duplicate list identity {key!r}")
                seen.add(key)
                flatten(child, (*parts, key), (*source, str(index)))
        elif isinstance(value, (str, int)) and not isinstance(value, bool):
            pointer = "/" + "/".join(part.replace("~", "~0").replace("/", "~1") for part in parts)
            key = parts[-1] if parts else ""
            kind = identity_class(pointer, value) if isinstance(value, str) else None
            if projections and isinstance(value, int) and value >= 1_000_000 and key in INTEGER_IDENTITY_KEYS:
                kind = "integer"
            if (projections and isinstance(value, str)
                    and (key in NAME_IDENTITY_KEYS or "build_profiles" in parts)):
                kind = kind or "name"
            if kind:
                leaves[pointer] = Leaf(file, pointer, locations[source], str(value),
                                       leaf_scope(file, pointer), kind)

    flatten(document, (), ())
    return leaves


def release_leaves(root: Path, release: str, *, projections: bool = False) -> dict[tuple[str, str], Leaf]:
    directory = root / "releases" / release
    files = [directory / "manifest.json", directory / "compatibility.json",
             *sorted((directory / "profiles").rglob("*.json"))]
    leaves = {(file.relative_to(directory).as_posix(), pointer): leaf
              for file in files for pointer, leaf in string_leaves(file, projections=projections).items()}
    for file in evidence_sources(directory):
        if file not in files:
            leaves.update({(file.relative_to(directory).as_posix(), pointer): leaf
                           for pointer, leaf in string_leaves(file).items()
                           if identity_class(pointer, leaf.value) == "evidence"})
    return leaves


def evidence_sources(directory: Path) -> list[Path]:
    return [file for file in [directory / "manifest.json", directory / "qualification.json",
                             *sorted((directory / "qualification").rglob("*.json")),
                             *sorted((directory / "acceptance").rglob("*.json")),
                             *sorted((directory / "profiles").rglob("*.json"))] if file.is_file()]


def bound_evidence(root: Path, release: str) -> set[str]:
    return {reference for file in evidence_sources(root / "releases" / release)
            for leaf in string_leaves(file).values()
            if (reference := evidence_reference(leaf.value)) is not None}


def boundary_pattern(values: Any) -> re.Pattern[str]:
    alternatives = "|".join(re.escape(value) for value in sorted(values, key=lambda item: (-len(item), item)))
    return re.compile(r"(?<![\w.-])(?:" + alternatives + r")(?![\w-]|\.\d)")


def release_version(release: str) -> tuple[int, ...]:
    return tuple(map(int, release[1:].split(".")))


def checkpoint_name(release: str) -> str:
    return checkpoint_host_directory(release)


def ready_history(root: Path, release: str, *, projections: bool = False) -> list[tuple[str, dict[str, Leaf]]]:
    history = []
    for file in (root / "releases").glob("*/manifest.json"):
        tag = file.parent.name
        if RELEASE_RE.fullmatch(tag) and release_version(tag) < release_version(release):
            leaves = string_leaves(file, projections=projections)
            if json.loads(file.read_text(encoding="utf-8")).get("status") == "ready":
                history.append((tag, leaves))
    return sorted(history, key=lambda item: release_version(item[0]), reverse=True)


def project(value: str, form: str) -> str:
    if form == "prefix8":
        return value[:8]
    if form == "prefix12":
        return value[:12]
    if form == "grouped":
        return f"{int(value):,}"
    return value


def identity_map(root: Path, predecessor: str, release: str, *,
                 projections: bool = False) -> tuple[IdentityMap, dict[str, str]]:
    before = release_leaves(root, predecessor, projections=projections)
    after = release_leaves(root, release, projections=projections)
    mappings: IdentityMap = {}
    anchors: dict[str, set[str]] = {}

    def add(value: str, scope: str, target: str | None, tier: int) -> None:
        mappings.setdefault(value, {}).setdefault(scope, set()).add(Replacement(target, tier))

    def add_leaf(old: Leaf, new: Leaf | None, tier: int) -> None:
        forms = PROJECTIONS.get(old.kind, ("full",)) if projections else ("full",)
        for form in forms:
            projected = projections and old.kind in PROJECTIONS
            origin = f"{old.file.name}:{old.pointer}" if projected else ""
            option = Replacement(project(new.value, form) if new else None, tier,
                                 origin, form if projected else "")
            mappings.setdefault(project(old.value, form), {}).setdefault(old.scope, set()).add(option)

    for key in before.keys() & after.keys():
        old, new = before[key], after[key]
        add_leaf(old, new, 1)
        if identity_class(old.pointer, old.value) == identity_class(new.pointer, new.value) == "evidence":
            old_reference, new_reference = evidence_reference(old.value), evidence_reference(new.value)
            assert old_reference is not None and new_reference is not None
            add(old_reference, old.scope, new_reference, 1)
            if old_reference.startswith("docs/") and new_reference.startswith("docs/"):
                add(old_reference[5:], old.scope, new_reference[5:], 1)
    if not any(old != option.value for old, scopes in mappings.items()
               for options in scopes.values() for option in options):
        raise Refusal(f"{root / 'releases' / release / 'manifest.json'}:1: refusal (b): identity map is empty")
    release_mapping = mappings.get(predecessor, {})
    if (set(release_mapping) != {"release"}
            or {option.value for option in release_mapping.get("release", ())} != {release}):
        raise Refusal(f"{root / 'releases' / release / 'manifest.json'}:1: refusal (b): identity map must map {predecessor} to {release}")

    history = ready_history(root, release, projections=projections)
    anchor_leaves = [*before.values(), *after.values()]

    def previous_distinct(tag: str, pointer: str, value: str) -> Leaf | None:
        return next((leaves[pointer] for prior, leaves in history
                     if release_version(prior) < release_version(tag)
                     and pointer in leaves and leaves[pointer].value != value), None)

    for key in before.keys() & after.keys():
        if key[0] != "manifest.json":
            continue
        old, new = before[key], after[key]
        prior = previous_distinct(predecessor, old.pointer, old.value)
        if prior is not None:
            target = previous_distinct(release, new.pointer, new.value)
            add_leaf(prior, target, 2)
            anchor_leaves.append(prior)
            if target:
                anchor_leaves.append(target)

    # The host store is derived from the product release sequence, including the frozen
    # historical naming convention. It is not a component's container mount name.
    old_prior = next((tag for tag, _ in history if release_version(tag) < release_version(predecessor)), None)
    new_prior = next((tag for tag, _ in history), None)
    if old_prior and new_prior:
        add(checkpoint_name(old_prior), "release", checkpoint_name(new_prior), 2)
    for leaf in anchor_leaves:
        if (leaf.pointer.rsplit("/", 1)[-1].endswith("tag")
                or identity_class(leaf.pointer, leaf.value) == "package") and leaf.scope != "release":
            anchors.setdefault(leaf.value, set()).add(leaf.scope)
        lane = re.match(r"rtx(\d+)", leaf.scope)
        if lane:
            anchors.setdefault(f"RTX {lane[1]}", set()).add(leaf.scope)
    return mappings, {anchor: next(iter(scopes)) for anchor, scopes in anchors.items() if len(scopes) == 1}


def markdown_blocks(text: str) -> list[MarkdownBlock]:
    """Table rows, list items, paragraphs and fences are separate attribution units."""
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    blocks = []
    index = 0
    item = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+")
    fence = re.compile(r"^\s*(`{3,}|~{3,})")
    while index < len(lines):
        start = index
        opening = fence.match(lines[index])
        html = re.match(r"^\s*<(tr|li|p)\b", lines[index], re.IGNORECASE)
        index += 1
        if opening:
            while index < len(lines):
                closing = fence.match(lines[index])
                index += 1
                if closing and closing[1][0] == opening[1][0] and len(closing[1]) >= len(opening[1]):
                    break
        elif html:
            closing = re.compile(r"</" + html[1] + r"\s*>", re.IGNORECASE)
            while not closing.search("".join(lines[start:index])) and index < len(lines):
                index += 1
        elif lines[start].strip() and not lines[start].lstrip().startswith(("|", "#")):
            while index < len(lines) and lines[index].strip():
                if (fence.match(lines[index]) or item.match(lines[index])
                        or re.match(r"^\s*<(?:tr|li|p)\b", lines[index], re.IGNORECASE)
                        or lines[index].lstrip().startswith(("|", "#"))):
                    break
                index += 1
        blocks.append(MarkdownBlock(offsets[start], offsets[index], start + 1, opening is not None))
    return blocks


def masked_text(text: str, predecessor: str, *, release_links: bool = True) -> str:
    """Hide immutable predecessor Markdown links, preserving offsets and line numbers."""
    blocks = markdown_blocks(text)
    starts = [block.start for block in blocks]
    pieces = []
    cursor = 0
    old = re.escape(predecessor)
    for match in MARKDOWN_LINK_RE.finditer(text):
        block = blocks[bisect.bisect_right(starts, match.start()) - 1]
        if block.fenced:
            continue
        target = urlsplit(match[1].strip("<>"))
        pinned_raw = (target.netloc == "raw.githubusercontent.com"
                      and re.match(r"^/[^/]+/[^/]+/[0-9a-fA-F]{40}/", target.path) is not None)
        immutable = release_links and (
            re.search(r"(?:^|/)releases/" + old + r"(?:/|$)", target.path)
            or re.search(r"/releases/tag/" + old + r"/?$", target.path)
            or re.search(r"/blob/" + old + r"/docs/QUICKSTART\.md$", target.path))
        if immutable or pinned_raw:
            pieces.extend((text[cursor:match.start()], re.sub(r"[^\r\n]", " ", match[0])))
            cursor = match.end()
    return "".join([*pieces, text[cursor:]])


def residual_versions(predecessor: str) -> set[str]:
    major, minor, patch = map(int, predecessor[1:].split("."))
    compact = f"v{major}{minor:02d}" + (f"-{patch}" if patch else "")
    return {predecessor, predecessor[1:], compact, f"checkpoints-{compact}"}


def identity_pattern(mappings: IdentityMap, *, projections: bool = False) -> re.Pattern[str]:
    if not projections:
        return boundary_pattern(mappings)
    alternatives = []
    for value in sorted(mappings, key=lambda item: (-len(item), item)):
        if value.replace(",", "").isdigit() and len(value.replace(",", "")) >= 7:
            guard = r"(?<![\w.,-])" + re.escape(value) + r"(?![\w-]|[.,]\d)"
        else:
            guard = r"(?<![\w.-])" + re.escape(value) + r"(?![\w-]|\.\w)"
        alternatives.append(guard)
    return re.compile("(?:" + "|".join(alternatives) + ")")


def unbound_evidence_links(text: str, bindings: set[str], *, masked: str | None = None) -> list[tuple[int, str]]:
    """Markdown, reference and HTML link targets share one evidence-binding rule."""
    view = text if masked is None else masked
    links = [(match.start(), match.end(), match[1]) for match in MARKDOWN_LINK_RE.finditer(text)]
    html_link = re.compile(r"""(?:href|src)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
    reference_link = re.compile(r"^\s{0,3}\[[^]]+\]:\s*<?(\S+?)>?(?:\s|$)", re.MULTILINE)
    links.extend((match.start(), match.end(), match[1]) for match in html_link.finditer(text))
    links.extend((match.start(), match.end(), match[1]) for match in reference_link.finditer(text))
    failures = []
    for start, end, target in sorted(links):
        reference = evidence_reference(target.strip("<>"))
        if reference is not None and reference not in bindings and view[start:end] == text[start:end]:
            failures.append((text.count("\n", 0, start) + 1, target))
    return failures


def evidence_diagnostics(text: str, bindings: set[str], document: Path, *,
                         mode: str, masked: str | None = None) -> list[tuple[int, str]]:
    """A candidate guide refuses unbound evidence; living pages send it to author review."""
    found = unbound_evidence_links(text, bindings, masked=masked)
    if mode == "guide":
        for line, target in found:
            raise Refusal(f"{document}:{line}: unbound evidence link: {target}")
    elif mode != "living":
        raise ValueError(f"unknown evidence mode: {mode}")
    return found


def retarget_text(text: str, guide: Path, predecessor: str, release: str,
                  mappings: IdentityMap, anchors: dict[str, str], *,
                  projections: bool = False, release_links: bool = True,
                  protected: Callable[[str], str] | None = None,
                  completed: bool | None = None,
                  edits: list[tuple[int, str, str]] | None = None) -> str:
    def view(value: str) -> str:
        masked = masked_text(value, predecessor, release_links=release_links)
        return protected(masked) if protected else masked

    masked = view(text)
    blocks = markdown_blocks(text)
    starts = [block.start for block in blocks]
    anchor_pattern = boundary_pattern(anchors) if anchors else None
    scopes_by_block: dict[int, set[str]] = {}
    pattern = identity_pattern(mappings, projections=projections)
    residual_keys = {value: scopes for value, scopes in mappings.items()
                     if any(option.value != value for options in scopes.values() for option in options)}
    residual_pattern = (identity_pattern(residual_keys, projections=True) if projections
                        else boundary_pattern(residual_versions(predecessor)))
    allowed: set[tuple[int, int]] = set()
    delta = 0
    if completed is None:
        # Published and prepared guides declare their subject explicitly. A rollback
        # sentence before that declaration does not make a completed guide a first pass.
        declarations = re.finditer(
            r"^ {0,3}>[ \t]+\*\*(?:Prepared|Versioned) guide:[ \t]+(v\d+\.\d+\.\d+)(?![\w.-])",
            masked, re.MULTILINE)
        current = next((match[1] for match in declarations
                        if not blocks[bisect.bisect_right(starts, match.start()) - 1].fenced), None)
        if current is None:
            literal = boundary_pattern([predecessor, release]).search(masked)
            current = literal[0] if literal else None
        completed = current == release
    previous_outputs: dict[str, set[str]] = {}
    target_outputs: dict[str, set[str]] = {}
    if projections or completed:
        for candidates in mappings.values():
            for scope, options in candidates.items():
                target_outputs.setdefault(scope, set()).update(
                    option.value for option in options
                    if option.value is not None and (projections or option.tier == 1))
                previous_outputs.setdefault(scope, set()).update(
                    option.value for option in options if option.tier == 2 and option.value is not None)

    def block_scopes(position: int) -> tuple[set[str], str]:
        index = bisect.bisect_right(starts, position) - 1
        block = blocks[index]
        if index not in scopes_by_block:
            scopes_by_block[index] = ({anchors[anchor[0]] for anchor in anchor_pattern.finditer(masked[block.start:block.end])}
                                      if anchor_pattern else set())
        return scopes_by_block[index], masked[block.start:block.end]

    def substitute(match: re.Match[str]) -> str:
        nonlocal delta
        if masked[match.start():match.end()] != match[0]:
            return match[0]
        candidates = mappings[match[0]]
        options = set().union(*candidates.values())
        mixed_roles = len(candidates) > 1 and len({option.tier for option in options}) > 1
        scopes: set[str] = set()
        targets = {option.value for option in options}
        if targets == {match[0]}:
            start = match.start() + delta
            allowed.update((start + item.start(), start + item.end())
                           for item in residual_pattern.finditer(match[0]))
            return match[0]
        if completed and not projections:
            # Product versions and their derived store names keep the residual checks.
            component_asset = (any(scope != "release" for scope in candidates)
                               and identity_class("/package_name", match[0]) in {"url", "package"})
            if (identity_class("", match[0]) not in {"hex", "digest", "image", "component-tag"}
                    and not component_asset
                    or not any(option.tier == 1 and option.value != match[0] for option in options)):
                return match[0]
            scopes, block_text = block_scopes(match.start())
            selected = ("release" if set(candidates) == {"release"} else
                        next(iter(scopes)) if len(scopes) == 1 else
                        next(iter(candidates)) if len(candidates) == 1 else None)
            block = blocks[bisect.bisect_right(starts, match.start()) - 1]
            prefix = re.split(r"[,;]|[.!?](?=\s)", block_text[:match.start() - block.start])[-1]
            roles = re.findall(r"\b(current|rollback)\b", prefix, re.IGNORECASE)
            rollback = bool(roles and roles[-1].lower() == "rollback")
            if (selected is not None
                    and (match[0] in target_outputs.get(selected, set())
                         or (rollback and match[0] in previous_outputs.get(selected, set())))):
                return match[0]
        collision = projections and (
            len({option.origin for option in options if option.origin}) > 1
            or any(option.projection in {"prefix8", "prefix12", "grouped"} for option in options)
            or match[0].replace(",", "").isdigit())
        if projections and completed:
            scopes, block_text = block_scopes(match.start())
            selected = ("release" if set(candidates) == {"release"} else
                        next(iter(scopes)) if len(scopes) == 1 else
                        next(iter(candidates)) if len(candidates) == 1 else None)
            explicit_previous = re.search(
                r"\b(?:previous|predecessor|rollback|retained|incumbent|supersed\w*|upgrad\w*\s+from)\b",
                block_text, re.IGNORECASE)
            if (selected is not None
                    and ((match[0] in previous_outputs.get(selected, set()) and explicit_previous)
                         or (selected not in candidates and match[0] in target_outputs.get(selected, set())))):
                start = match.start() + delta
                allowed.update((start + item.start(), start + item.end())
                               for item in residual_pattern.finditer(match[0]))
                return match[0]
        if len(targets) != 1 or mixed_roles or collision:
            scopes, _ = block_scopes(match.start())
            options = candidates.get(next(iter(scopes)), set()) if len(scopes) == 1 else set()
        targets = {option.value for option in options}
        if len(targets) != 1 or None in targets:
            line = text.count("\n", 0, match.start()) + 1
            raise Refusal(f"{guide}:{line}: refusal (a): ambiguous identity {match[0]!r}; "
                          f"candidate scopes: {', '.join(sorted(candidates))}; "
                          f"block anchors: {', '.join(sorted(scopes)) or 'none'}")
        target = next(iter(targets))
        assert target is not None
        if completed and not projections:
            line = text.count("\n", 0, match.start()) + 1
            raise Refusal(f"{guide}:{line}: refusal (c): guide still names a predecessor identity {match[0]!r}")
        if projections or any(option.tier == 2 for option in options) or target == match[0]:
            start = match.start() + delta
            allowed.update((start + item.start(), start + item.end())
                           for item in residual_pattern.finditer(target))
        if edits is not None and target != match[0]:
            edits.append((text.count("\n", 0, match.start()) + 1, match[0], target))
        delta += len(target) - len(match[0])
        return target

    # Substitute original spans once; rollback references may be legitimate tier-2 outputs.
    result = pattern.sub(substitute, text)
    if completed and not projections:
        tier_two = {option.value for scopes in mappings.values() for options in scopes.values()
                    for option in options if option.tier == 2 and option.value is not None}
        if tier_two:
            for match in boundary_pattern(tier_two).finditer(masked):
                allowed.update((match.start() + item.start(), match.start() + item.end())
                               for item in residual_pattern.finditer(match[0]))
    for residual in residual_pattern.finditer(view(result)):
        if residual.span() not in allowed:
            line = result.count("\n", 0, residual.start()) + 1
            raise Refusal(f"{guide}:{line}: refusal (c): residual predecessor identity {residual[0]!r}")
    return result


def retarget(root: Path, predecessor: str, release: str, guide: Path, *, check: bool = False) -> bool:
    """Validate the complete candidate before one atomic write; return whether bytes differ."""
    mappings, anchors = identity_map(root, predecessor, release)
    try:
        original = guide.read_bytes()
        text = original.decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise Refusal(f"{guide}:1: cannot read guide: {error}") from error
    result = retarget_text(text, guide, predecessor, release, mappings, anchors)
    bindings = bound_evidence(root, release)
    evidence_diagnostics(result, bindings, guide, mode="guide", masked=masked_text(result, predecessor))
    with tempfile.TemporaryDirectory() as directory:
        candidate = Path(directory) / guide.name
        atomic_write(candidate, result)
        for lane in documented_route.LANES:
            try:
                documented_route.lane_blocks(candidate, lane)
            except (KeyError, ValueError) as error:
                line = 1
                for step in documented_route.LANES[lane]:
                    if step.heading in str(error):
                        line = next((number for number, value in enumerate(text.splitlines(), 1)
                                     if value.lstrip("# ") == step.heading), 1)
                        break
                raise Refusal(f"{guide}:{line}: refusal (d): {lane}: {error}") from error
    changed = result.encode("utf-8") != original
    if changed and not check:
        atomic_write(guide, result)
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="predecessor", required=True)
    parser.add_argument("--to", dest="release", required=True)
    parser.add_argument("--guide", type=Path, default=ROOT / "docs" / "QUICKSTART.md")
    parser.add_argument("--check", action="store_true", help="exit 1 if the guide would change; never write it")
    args = parser.parse_args(argv)
    for value in (args.predecessor, args.release):
        if not RELEASE_RE.fullmatch(value):
            parser.error(f"expected a product release tag, got {value!r}")
    try:
        changed = retarget(ROOT, args.predecessor, args.release, args.guide, check=args.check)
    except Refusal as error:
        print(error, file=sys.stderr)
        return 1
    print(f"{args.guide}: " + ("would change" if args.check and changed else "retargeted" if changed else "unchanged"))
    return int(args.check and changed)


if __name__ == "__main__":
    raise SystemExit(main())
