#!/usr/bin/env python3
"""Extract the fenced code blocks a reader runs from docs/QUICKSTART.md, exactly as written.

The route a release accepts must be the route the documentation gives a stranger. Every lane
qualified through an equivalent-looking tool instead of its documented blocks left the class of
defect recorded in omp-ninfer#39 invisible for four releases. This module addresses each
executable step of a documented route by its Markdown heading and block index, and writes the
steps of a lane as files whose bytes are the block's bytes; the host runners execute those files
in one shell session and record the SHA-256 of every block they ran, so an acceptance receipt
binds the documentation it exercised.

    python3 scripts/documented_route.py steps --lane rtx4090-native
    python3 scripts/documented_route.py bundle --lane rtx4090-native --output /tmp/route
    python3 scripts/documented_route.py extract --heading "Native lane acceptance"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOC = ROOT / "docs" / "QUICKSTART.md"
_HEADING_RE = re.compile(r"^(#{2,3}) (.+?)\s*$")
_FENCE_RE = re.compile(r"^```([A-Za-z0-9_-]*)\s*$")


@dataclass(frozen=True)
class Block:
    heading: str
    index: int
    language: str
    text: str

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Step:
    """One executable step of a documented route: a block address plus the runner language."""

    slug: str
    heading: str
    index: int = 0
    language: str = "powershell"


# The documented routes, as a reader meets them. Every step is a fenced block in the quickstart;
# prose between blocks (clone the tag, open an elevated shell) is the runner's precondition.
LANES: dict[str, tuple[Step, ...]] = {
    # RTX 4090 native Windows: the OMP client, then the lane section top to bottom.
    "rtx4090-native": (
        Step("client-install", "Install the exact native Windows client"),
        Step("variant", "Native Windows RTX 4090 and RTX 3090 release lanes", 0),
        Step("stage-and-install", "Native Windows RTX 4090 and RTX 3090 release lanes", 2),
        Step("operate", "Operate the native lane"),
        Step("provider", "Point OMP at the native lane"),
        Step("acceptance", "Native lane acceptance"),
    ),
    # RTX 3090 native Windows: identical route, the other variant id.
    "rtx3090-native": (
        Step("client-install", "Install the exact native Windows client"),
        Step("variant", "Native Windows RTX 4090 and RTX 3090 release lanes", 1),
        Step("stage-and-install", "Native Windows RTX 4090 and RTX 3090 release lanes", 2),
        Step("operate", "Operate the native lane"),
        Step("provider", "Point OMP at the native lane"),
        Step("acceptance", "Native lane acceptance"),
    ),
    # RTX 5090 container, inference-host half, run inside the WSL2 distro or on Linux.
    "rtx5090-container-host": (
        Step("prepare", "3. Prepare the model and key on the inference host", 0, "sh"),
        Step("start", "4. Start NInfer on the inference host", 0, "sh"),
    ),
    # RTX 5090 container, native Windows OMP client half (the quickstart's primary row).
    "rtx5090-windows-client": (
        Step("client-install", "Install the exact native Windows client"),
        Step("provider", "Native Windows OMP"),
        Step("acceptance", "Native Windows command forms", 0),
        Step("fail-closed", "Native Windows command forms", 1),
    ),
}


def parse_blocks(text: str) -> list[Block]:
    blocks: list[Block] = []
    heading = ""
    per_heading: dict[str, int] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        match = _HEADING_RE.match(line)
        if match:
            heading = match.group(2)
        fence = _FENCE_RE.match(line)
        if fence:
            language = fence.group(1)
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            body = "\n".join(lines[i + 1:j]) + "\n"
            index = per_heading.get(heading, 0)
            per_heading[heading] = index + 1
            blocks.append(Block(heading, index, language, body))
            i = j
        i += 1
    return blocks


def extract(doc: Path, heading: str, index: int = 0) -> Block:
    for block in parse_blocks(doc.read_text(encoding="utf-8")):
        if block.heading == heading and block.index == index:
            return block
    raise KeyError(f"no fenced block {index} under heading {heading!r} in {doc}")


def lane_blocks(doc: Path, lane: str) -> list[tuple[Step, Block]]:
    if lane not in LANES:
        raise KeyError(f"unknown lane {lane!r}; known: {', '.join(sorted(LANES))}")
    resolved: list[tuple[Step, Block]] = []
    for step in LANES[lane]:
        block = extract(doc, step.heading, step.index)
        if block.language != step.language:
            raise ValueError(
                f"{lane}/{step.slug}: block under {step.heading!r} is {block.language or 'unfenced'},"
                f" expected {step.language}"
            )
        resolved.append((step, block))
    return resolved


def bundle(doc: Path, lane: str, output: Path) -> dict:
    """Write each step's block as its own file and a manifest binding the bytes.

    Files are numbered so a runner executes them in reading order; the manifest records the
    heading, index, and SHA-256 of every block so the receipt can prove which documentation ran.
    """
    output.mkdir(parents=True, exist_ok=True)
    extension = {"powershell": "ps1", "sh": "sh"}
    steps = []
    for position, (step, block) in enumerate(lane_blocks(doc, lane), start=1):
        name = f"{position:02d}-{step.slug}.{extension[step.language]}"
        (output / name).write_text(block.text, encoding="utf-8", newline="\n")
        steps.append({
            "position": position, "slug": step.slug, "file": name, "heading": step.heading,
            "index": step.index, "language": step.language, "sha256": block.sha256,
        })
    manifest = {
        "artifact_type": "omp_ninfer_documented_route_bundle", "schema_version": 1,
        "lane": lane, "document": str(doc.relative_to(ROOT)) if doc.is_relative_to(ROOT) else str(doc),
        "document_sha256": hashlib.sha256(doc.read_bytes()).hexdigest(), "steps": steps,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    commands = parser.add_subparsers(dest="command", required=True)
    steps = commands.add_parser("steps", help="list a lane's documented steps")
    steps.add_argument("--lane", required=True, choices=sorted(LANES))
    build = commands.add_parser("bundle", help="write a lane's blocks as step files plus a manifest")
    build.add_argument("--lane", required=True, choices=sorted(LANES))
    build.add_argument("--output", type=Path, required=True)
    one = commands.add_parser("extract", help="print one block")
    one.add_argument("--heading", required=True)
    one.add_argument("--index", type=int, default=0)
    args = parser.parse_args()

    if args.command == "steps":
        for step, block in lane_blocks(args.doc, args.lane):
            print(f"{step.slug:18} {block.sha256[:12]}  {step.heading} [{step.index}]")
        return 0
    if args.command == "bundle":
        manifest = bundle(args.doc, args.lane, args.output)
        print(f"wrote {len(manifest['steps'])} steps for {args.lane} to {args.output}")
        return 0
    sys.stdout.write(extract(args.doc, args.heading, args.index).text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
