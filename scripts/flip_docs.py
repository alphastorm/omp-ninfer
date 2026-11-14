#!/usr/bin/env python3
"""Flip bound living-document identities; report prose that still needs an author.

    python3 scripts/flip_docs.py --from v0.20.0 --to v0.21.0 [--check]

The publication table in docs/RELEASES.md owns the page set. Records and released changelog
sections are immutable. This tool changes identity tokens, never release-state sentences,
measured results, publication dates, record entries or rendered images.
Check mode fails on bound-identity drift, unresolved identities or the verifier's stale-state
errors; results/provenance paragraphs and unbound evidence links are advisory author reviews.
"""
from __future__ import annotations

import argparse
import difflib
import html
import re
import sys
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import retarget_guide as engine
from release_io import atomic_write
from verify_release import (
    PENDING_PRODUCT_TERM_RE, PENDING_RELEASE_PROSE_RE, pending_release_state,
    validate_release_documentation,
)

ROOT = Path(__file__).resolve().parents[1]
HEADING = re.compile(r"^ {0,3}##\s+(.+?)\s*#*\s*$")
AUTHORING_PROSE = re.compile(
    r"\b(?:published|accepted|passed|failed|qualified|"
    r"measured|supersed\w*|rebuilt|re-cut|carried|shipped|keeps|uses|matches|pinned|review|"
    r"byte[- ]identical|rollback|qualification\s+(?:receipts?|results?|evidence|batch)|"
    r"waived|waiver|restor(?:ed|ation)|first[- ]attempt|Latest)\b", re.IGNORECASE)
RESULT = re.compile(
    r"\b\d[\d,.]*\s*(?:tok/s|tokens?/s|ms\b|s\b|seconds?\b|"
    r"prompts?\b|blocks?\b|phases?\b|samples?\b|%)|\b\d+/\d+\b|"
    r"\b(?:decode|retrieval|prefill|latency|throughput|TTFT|wall[- ]time)\b",
    re.IGNORECASE)
HTML_TEXT_BLOCK = re.compile(
    r"<(?P<tag>p|li|tr|figcaption|span|script)\b[^>]*>.*?</(?P=tag)\s*>"
    r"|<meta\b[^>]*>", re.IGNORECASE | re.DOTALL)


class Issue(NamedTuple):
    page: str
    line: int
    kind: str
    detail: str

    def __str__(self) -> str:
        if self.kind == "stale release state":
            return self.detail
        return f"{self.page}:{self.line}: {self.kind}: {self.detail}"


class Result(NamedTuple):
    changed: tuple[str, ...]
    issues: tuple[Issue, ...]
    edits: tuple[Issue, ...]
    statistics: tuple["PageStatistics", ...]


class PageStatistics(NamedTuple):
    page: str
    substitutions: int
    authoring_lines: int


def publication_pages(root: Path, *, declaration: Path | None = None) -> tuple[Path, ...]:
    """Read, not duplicate, the publication table's first column."""
    declaration = declaration or root / "docs" / "RELEASES.md"
    lines = declaration.read_text(encoding="utf-8").splitlines()
    start = next((index for index, line in enumerate(lines) if line == "## After publication"), None)
    if start is None:
        raise engine.Refusal(f"{declaration}:1: missing After publication page declaration")
    patterns: list[tuple[int, str]] = []
    table = False
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if HEADING.match(line):
            break
        if line.startswith("| Page |"):
            table = True
            continue
        if table and line.startswith("|"):
            cell = line.split("|", 2)[1]
            patterns.extend((index + 1, value) for value in re.findall(r"`([^`]+)`", cell))
        elif table and patterns:
            break
    if not patterns:
        raise engine.Refusal(f"{declaration}:{start + 1}: empty publication page declaration")
    pages: set[Path] = set()
    for line, pattern in patterns:
        if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
            raise engine.Refusal(f"{declaration}:{line}: publication page must be repository-relative: {pattern}")
        matches = sorted(root.glob(pattern))
        if not matches:
            raise engine.Refusal(f"{declaration}:{line}: declared page does not exist: {pattern}")
        for path in matches:
            if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
                raise engine.Refusal(f"{declaration}:{line}: declared page is not a confined file: {pattern}")
            relative = path.relative_to(root).as_posix()
            if (relative == "docs/QUICKSTART.md" or relative.startswith(("releases/", "profiles/"))
                    or relative in {"compatibility.json", "docs/COMPATIBILITY.md"}):
                raise engine.Refusal(f"{declaration}:{line}: publication page is release-candidate authority: {relative}")
            pages.add(path)
    return tuple(sorted(pages))


def blank(text: str) -> str:
    return re.sub(r"[^\r\n]", " ", text)


def records_mask(text: str, page: str) -> str:
    return engine.records_mask(text, page)


def paragraphs(text: str, page: str) -> list[engine.MarkdownBlock]:
    if not page.endswith(".html"):
        return engine.markdown_blocks(text)
    # Outer paragraphs/rows win over their nested spans: a result and its label must stay
    # together. Non-prose markup, scripts and styles never become inferred measurements.
    spans = sorted(((match.start(), match.end()) for match in HTML_TEXT_BLOCK.finditer(text)),
                   key=lambda span: (span[0], -span[1]))
    blocks = []
    last = -1
    for start, end in spans:
        if start >= last:
            blocks.append(engine.MarkdownBlock(start, end, text.count("\n", 0, start) + 1, False))
            last = end
    return blocks


def prose(value: str) -> str:
    value = engine.MARKDOWN_LINK_RE.sub(lambda match: match[0].split("](", 1)[0].lstrip("!["), value)
    return html.unescape(re.sub(r"<[^>]+>", " ", value))


def state_blocks(text: str, page: str) -> list[engine.MarkdownBlock]:
    records = records_mask(text, page)
    found = []
    for block in paragraphs(text, page):
        if block.fenced or not records[block.start:block.end].strip():
            continue
        original = text[block.start:block.end]
        if re.match(r"^\s*\[[^]]+\]:\s*\S+", original):
            continue
        body = prose(original)
        product_pending = PENDING_PRODUCT_TERM_RE.search(body)
        body = PENDING_PRODUCT_TERM_RE.sub("", body)
        body = re.sub(r"\bqualified (?:local inference )?appliance\b", "", body, flags=re.IGNORECASE)
        if (AUTHORING_PROSE.search(body) or pending_release_state(body)
                or PENDING_RELEASE_PROSE_RE.search(body)
                or (RESULT.search(body) and not product_pending)):
            found.append(block)
    return found


def identity_view(text: str, page: str) -> str:
    masked = records_mask(text, page)
    pieces = []
    cursor = 0
    for block in state_blocks(text, page):
        pieces.extend((masked[cursor:block.start], blank(masked[block.start:block.end])))
        cursor = block.end
    return "".join([*pieces, masked[cursor:]])


def source_posture(text: str, page: str, predecessor: str, release: str) -> bool:
    """The first living product tag, not an immutable record, identifies a page's release."""
    current = engine.boundary_pattern([predecessor, release]).search(records_mask(text, page))
    return current is not None and current[0] == predecessor


def needs_authoring(text: str, page: str, predecessor: str, release: str) -> list[Issue]:
    source = source_posture(text, page, predecessor, release)
    predecessor_re = engine.boundary_pattern(engine.residual_versions(predecessor))
    target_re = engine.boundary_pattern([release, release[1:]])
    issues = []
    for block in state_blocks(text, page):
        body = text[block.start:block.end]
        if predecessor_re.search(body) or (source and not target_re.search(body)):
            detail = " ".join(prose(body).split())
            issues.append(Issue(page, block.line, "needs authoring", detail))
    return issues


def target_posture(text: str, page: str, predecessor: str, release: str,
                   mappings: engine.IdentityMap) -> bool:
    # A state paragraph may deliberately remain on the predecessor until an author edits it.
    # A target-only identity outside that paragraph proves that identity substitution has
    # already started; do not advance its newly produced rollback identities a second time.
    witnesses = {option.value for old, scopes in mappings.items()
                 for options in scopes.values() for option in options
                 if option.tier == 1 and option.value is not None
                 and option.value != old and option.value not in mappings}
    visible = identity_view(text, page)
    if witnesses and engine.boundary_pattern(witnesses).search(visible):
        return True
    return not source_posture(text, page, predecessor, release)


def unbound_names(text: str, page: str, mappings: engine.IdentityMap) -> list[Issue]:
    """Detect, never invent, compound names not present in the bound snapshots."""
    view = identity_view(text, page)
    names = {value for value, scopes in mappings.items()
             if any(option.value != value for options in scopes.values() for option in options)
             and value.startswith(("native-", "qwen38-"))}
    issues = []
    for match in re.finditer(r"(?<![\w.-])[\w.-]+(?![\w.-])", view):
        if match[0] not in mappings and any(match[0].startswith(name + "-") for name in names):
            issues.append(Issue(page, text.count("\n", 0, match.start()) + 1, "needs authoring",
                                f"unbound compound identity {match[0]!r}; no shared naming derivation"))
    return issues


def flip(root: Path, predecessor: str, release: str, *, check: bool = False,
         declaration: Path | None = None) -> Result:
    mappings, anchors = engine.identity_map(root, predecessor, release, projections=True)
    bindings = engine.bound_evidence(root, release)
    changed = []
    issues = []
    edits = []
    statistics = []
    for path in publication_pages(root, declaration=declaration):
        page = path.relative_to(root).as_posix()
        original = path.read_bytes()
        text = original.decode("utf-8")
        source_lines = text.splitlines()
        try:
            authoring = needs_authoring(text, page, predecessor, release)
            names = unbound_names(text, page, mappings)
        except engine.Refusal as error:
            match = re.search(r":(\d+): (.+)", str(error))
            issues.append(Issue(page, int(match[1]) if match else 1, "refused",
                                match[2] if match else str(error)))
            statistics.append(PageStatistics(page, 0, 0))
            continue
        issues.extend(authoring)
        issues.extend(names)
        authoring_lines = {number for block in state_blocks(text, page)
                           if any(issue.line == block.line for issue in authoring)
                           for number in range(block.line, block.line + text[block.start:block.end].count("\n") + 1)
                           if number <= len(source_lines) and source_lines[number - 1].strip()}
        authoring_lines.update(issue.line for issue in names)
        substitutions: list[tuple[int, str, str]] = []
        try:
            candidate = engine.retarget_text(
                text, path, predecessor, release, mappings, anchors, projections=True,
                release_links=False, protected=lambda value: identity_view(value, page),
                completed=target_posture(text, page, predecessor, release, mappings),
                edits=substitutions,
            )
        except engine.Refusal as error:
            match = re.search(r":(\d+): (.+)", str(error))
            issues.append(Issue(page, int(match[1]) if match else 1, "refused",
                                match[2] if match else str(error)))
            statistics.append(PageStatistics(page, 0, len(authoring_lines)))
            continue
        left, right = text.splitlines(), candidate.splitlines()
        for operation, start, end, other_start, other_end in difflib.SequenceMatcher(
                a=left, b=right, autojunk=False).get_opcodes():
            if operation != "equal":
                edits.append(Issue(page, start + 1, "stale identities",
                                   "\n".join(left[start:end]) + " => " + "\n".join(right[other_start:other_end])))
        unbound = engine.evidence_diagnostics(candidate, bindings, path, mode="living",
                                              masked=records_mask(candidate, page))
        issues.extend(Issue(page, line, "review: evidence link", target) for line, target in unbound)
        statistics.append(PageStatistics(page, len(substitutions), len(authoring_lines)))
        if candidate.encode("utf-8") != original:
            changed.append(page)
            if not check:
                atomic_write(path, candidate)
    wording: list[str] = []
    validate_release_documentation(root, release, wording)
    for error in wording:
        location = re.match(r"(.+?):(\d+):", error)
        issues.append(Issue(location[1] if location else "docs/RELEASES.md",
                            int(location[2]) if location else 1, "stale release state", error))
    return Result(tuple(changed), tuple(issues), tuple(edits), tuple(statistics))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="predecessor", required=True)
    parser.add_argument("--to", dest="release", required=True)
    parser.add_argument("--check", action="store_true", help="report drift and authoring without writing")
    args = parser.parse_args(argv)
    if not all(engine.RELEASE_RE.fullmatch(value) for value in (args.predecessor, args.release)):
        parser.error("--from and --to must name product release tags")
    try:
        result = flip(ROOT, args.predecessor, args.release, check=args.check)
    except (engine.Refusal, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        return 1
    if args.check:
        for edit in result.edits:
            print(edit)
    else:
        for page in result.changed:
            print(f"{page}: identities retargeted")
    for issue in result.issues:
        print(issue, file=sys.stderr)
    if not result.changed and not result.issues:
        print("living documentation identities unchanged")
    refused = any(issue.kind in {"refused", "stale release state"} for issue in result.issues)
    return int(refused or (args.check and bool(result.edits)))


if __name__ == "__main__":
    raise SystemExit(main())
