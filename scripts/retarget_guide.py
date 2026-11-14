#!/usr/bin/env python3
"""Retarget QUICKSTART identities without rewriting provenance or acceptance prose.

    python3 scripts/retarget_guide.py --from v0.20.0 --to v0.21.0 [--guide PATH] [--check]

Identities come from the two release manifests, compatibility authorities and profile
snapshots. A shared identity that splits between components needs an unambiguous component
anchor in its original Markdown block. Previous-distinct identities come from older ready
manifests, not from prose guesses. Immutable predecessor links remain untouched. The whole
guide remains the acceptance document; this tool does not grant release readiness.
"""
from __future__ import annotations

import argparse
import bisect
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import documented_route
from release_io import atomic_write
from verify_release import COMPONENT_TAG_RE, MARKDOWN_LINK_RE

ROOT = Path(__file__).resolve().parents[1]
RELEASE_RE = re.compile(r"v\d+\.\d+\.\d+\Z")
VERSION_RE = re.compile(r"v?\d+\.\d+\.\d+\Z")
HEX_RE = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")
DIGEST_RE = re.compile(r"sha256:[0-9a-fA-F]{64}\Z")
IMAGE_RE = re.compile(r"[^\s@]+@sha256:[0-9a-fA-F]{64}\Z")
PACKAGE_KEYS = {"package_name", "artifact_name", "asset_name", "filename"}
CONTAINER = "rtx5090-container"


class Refusal(ValueError):
    """An identity or document cannot be retargeted without guessing."""


class Leaf(NamedTuple):
    file: Path
    pointer: str
    line: int
    value: str
    scope: str


class Replacement(NamedTuple):
    value: str | None
    tier: int


IdentityMap = dict[str, dict[str, set[Replacement]]]


class MarkdownBlock(NamedTuple):
    start: int
    end: int
    line: int
    fenced: bool


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
    if parts[0] in {"release", "product_release"}:
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


def string_leaves(file: Path) -> dict[str, Leaf]:
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
        if isinstance(value, str):
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
        elif isinstance(value, str):
            pointer = "/" + "/".join(part.replace("~", "~0").replace("/", "~1") for part in parts)
            if identity_class(pointer, value):
                leaves[pointer] = Leaf(file, pointer, locations[source], value, leaf_scope(file, pointer))

    flatten(document, (), ())
    return leaves


def release_leaves(root: Path, release: str) -> dict[tuple[str, str], Leaf]:
    directory = root / "releases" / release
    files = [directory / "manifest.json", directory / "compatibility.json",
             *sorted((directory / "profiles").rglob("*.json"))]
    leaves = {(file.relative_to(directory).as_posix(), pointer): leaf
              for file in files for pointer, leaf in string_leaves(file).items()}
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
    major, minor, patch = release_version(release)
    if (major, minor) < (0, 17):
        return "checkpoints-v013"
    return f"checkpoints-v{major}{minor:02d}" + (f"-{patch}" if patch else "")


def ready_history(root: Path, release: str) -> list[tuple[str, dict[str, Leaf]]]:
    history = []
    for file in (root / "releases").glob("*/manifest.json"):
        tag = file.parent.name
        if RELEASE_RE.fullmatch(tag) and release_version(tag) < release_version(release):
            leaves = string_leaves(file)
            if json.loads(file.read_text(encoding="utf-8")).get("status") == "ready":
                history.append((tag, leaves))
    return sorted(history, key=lambda item: release_version(item[0]), reverse=True)


def identity_map(root: Path, predecessor: str, release: str) -> tuple[IdentityMap, dict[str, str]]:
    before, after = release_leaves(root, predecessor), release_leaves(root, release)
    mappings: IdentityMap = {}
    anchors: dict[str, set[str]] = {}

    def add(value: str, scope: str, target: str | None, tier: int) -> None:
        mappings.setdefault(value, {}).setdefault(scope, set()).add(Replacement(target, tier))

    for key in before.keys() & after.keys():
        old, new = before[key], after[key]
        add(old.value, old.scope, new.value, 1)
        if identity_class(old.pointer, old.value) == identity_class(new.pointer, new.value) == "evidence":
            old_reference, new_reference = evidence_reference(old.value), evidence_reference(new.value)
            assert old_reference is not None and new_reference is not None
            add(old_reference, old.scope, new_reference, 1)
            if old_reference.startswith("docs/") and new_reference.startswith("docs/"):
                add(old_reference[5:], old.scope, new_reference[5:], 1)
    if not any(old != option.value for old, scopes in mappings.items()
               for options in scopes.values() for option in options):
        raise Refusal(f"{root / 'releases' / release / 'manifest.json'}:1: refusal (b): identity map is empty")
    if mappings.get(predecessor) != {"release": {Replacement(release, 1)}}:
        raise Refusal(f"{root / 'releases' / release / 'manifest.json'}:1: refusal (b): identity map must map {predecessor} to {release}")

    history = ready_history(root, release)
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
            add(prior.value, old.scope, target.value if target else None, 2)
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
        index += 1
        if opening:
            while index < len(lines):
                closing = fence.match(lines[index])
                index += 1
                if closing and closing[1][0] == opening[1][0] and len(closing[1]) >= len(opening[1]):
                    break
        elif lines[start].strip() and not lines[start].lstrip().startswith(("|", "#")):
            while index < len(lines) and lines[index].strip():
                if fence.match(lines[index]) or item.match(lines[index]) or lines[index].lstrip().startswith(("|", "#")):
                    break
                index += 1
        blocks.append(MarkdownBlock(offsets[start], offsets[index], start + 1, opening is not None))
    return blocks


def masked_text(text: str, predecessor: str) -> str:
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
        immutable = (re.search(r"(?:^|/)releases/" + old + r"(?:/|$)", target.path)
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


def retarget_text(text: str, guide: Path, predecessor: str, release: str,
                  mappings: IdentityMap, anchors: dict[str, str]) -> str:
    masked = masked_text(text, predecessor)
    blocks = markdown_blocks(text)
    starts = [block.start for block in blocks]
    anchor_pattern = boundary_pattern(anchors) if anchors else None
    scopes_by_block: dict[int, set[str]] = {}
    residual_pattern = boundary_pattern(residual_versions(predecessor))
    allowed: set[tuple[int, int]] = set()
    delta = 0

    def substitute(match: re.Match[str]) -> str:
        nonlocal delta
        if masked[match.start():match.end()] != match[0]:
            return match[0]
        candidates = mappings[match[0]]
        options = set().union(*candidates.values())
        mixed_roles = len(candidates) > 1 and len({option.tier for option in options}) > 1
        scopes: set[str] = set()
        if len({option.value for option in options}) != 1 or mixed_roles:
            index = bisect.bisect_right(starts, match.start()) - 1
            block = blocks[index]
            if index not in scopes_by_block:
                scopes_by_block[index] = ({anchors[anchor[0]] for anchor in anchor_pattern.finditer(masked[block.start:block.end])}
                                          if anchor_pattern else set())
            scopes = scopes_by_block[index]
            options = candidates.get(next(iter(scopes)), set()) if len(scopes) == 1 else set()
        targets = {option.value for option in options}
        if len(targets) != 1 or None in targets:
            line = text.count("\n", 0, match.start()) + 1
            raise Refusal(f"{guide}:{line}: refusal (a): ambiguous identity {match[0]!r}; "
                          f"candidate scopes: {', '.join(sorted(candidates))}; "
                          f"block anchors: {', '.join(sorted(scopes)) or 'none'}")
        target = next(iter(targets))
        assert target is not None
        if any(option.tier == 2 for option in options) or target == match[0]:
            start = match.start() + delta
            allowed.update((start + item.start(), start + item.end())
                           for item in residual_pattern.finditer(target))
        delta += len(target) - len(match[0])
        return target

    # The first unmasked product-release literal identifies the guide's current release.
    # Later predecessor references may be legitimate tier-2 outputs, including on a rerun.
    current = boundary_pattern([predecessor, release]).search(masked)
    completed = current is not None and current[0] == release
    result = text if completed else boundary_pattern(mappings).sub(substitute, text)
    if completed:
        tier_two = {option.value for scopes in mappings.values() for options in scopes.values()
                    for option in options if option.tier == 2 and option.value is not None}
        if tier_two:
            for match in boundary_pattern(tier_two).finditer(masked):
                allowed.update((match.start() + item.start(), match.start() + item.end())
                               for item in residual_pattern.finditer(match[0]))
    for residual in residual_pattern.finditer(masked_text(result, predecessor)):
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
    masked = masked_text(result, predecessor)
    for link in MARKDOWN_LINK_RE.finditer(result):
        reference = evidence_reference(link[1].strip("<>"))
        if (reference is not None and reference not in bindings
                and masked[link.start():link.end()] == link[0]):
            line = result.count("\n", 0, link.start()) + 1
            raise Refusal(f"{guide}:{line}: unbound evidence link: {link[1]}")
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
