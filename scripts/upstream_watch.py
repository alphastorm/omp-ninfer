#!/usr/bin/env python3
"""Read-only upstream fork-watch for the omp-ninfer product family.

Reads upstream-watch.json, asks the GitHub API (via the ``gh`` CLI) for every
commit an upstream has accumulated past our recorded fork point, classifies
each commit, and scores its overlap with the downstream path classes that make
a change conflict-relevant to our forks.

The tool never mutates anything: no fetches into local trees, no pushes, no
issue writes. Output is a human summary on stdout and, with ``--receipt``, a
JSON document suitable for committing next to qualification receipts.

Modeled on omp-monorepo's fork-maintenance lane (upstream.lock.json +
upstream-watch.ts): same triage verdicts, without the reroll probe.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

CLASS_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("security", re.compile(r"secur|cve-|overflow|use.after.free|race\b|toctou", re.I)),
    ("fix", re.compile(r"^fix|\bfix\(|^bug", re.I)),
    ("perf", re.compile(r"^perf|\bperf\(|speedup|throughput|^bench", re.I)),
    ("feature", re.compile(r"^feat|\bfeat\(", re.I)),
    ("docs", re.compile(r"^docs?\b|^docs?\(", re.I)),
    ("test", re.compile(r"^test|\btest\(", re.I)),
    ("chore", re.compile(r"^chore|^refactor|^style|^ci\b", re.I)),
)


def classify(subject: str) -> str:
    for name, pattern in CLASS_PATTERNS:
        if pattern.search(subject):
            return name
    return "other"


def gh_api(path: str) -> Any:
    result = subprocess.run(
        ["gh", "api", path],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh api {path}: {result.stderr.strip()[:200]}")
    return json.loads(result.stdout)


def overlap_class(files: list[str], overlap_paths: list[str]) -> str:
    hits = sum(1 for name in files if any(name.startswith(p) for p in overlap_paths))
    if hits == 0:
        return "no-direct-path-overlap"
    if hits >= max(2, len(files) // 2):
        return "high-review-overlap"
    return "review-overlap"


def recommend(commit_class: str, overlap: str) -> str:
    if commit_class in ("docs", "chore", "test"):
        return "ignore"
    if commit_class == "security":
        return "review-now"
    if overlap == "no-direct-path-overlap":
        return "pull-candidate"
    if commit_class in ("fix", "perf"):
        return "next-release"
    return "next-release"


def watch_one(entry: dict[str, Any], per_commit_files: bool) -> dict[str, Any]:
    upstream = entry["upstream"]
    ref = entry["upstream_ref"]
    fork_point = entry["fork_point"]

    head = gh_api(f"repos/{upstream}/commits/{ref}")
    head_sha = head["sha"]
    head_date = head["commit"]["committer"]["date"]

    if head_sha == fork_point:
        return {
            "id": entry["id"],
            "upstream": upstream,
            "verdict": "up-to-date",
            "upstream_head": head_sha,
            "upstream_head_date": head_date,
            "ahead_by": 0,
            "commits": [],
        }

    compare = gh_api(f"repos/{upstream}/compare/{fork_point}...{head_sha}")
    commits: list[dict[str, Any]] = []
    for item in compare.get("commits", []):
        subject = item["commit"]["message"].splitlines()[0]
        record: dict[str, Any] = {
            "sha": item["sha"][:12],
            "date": item["commit"]["committer"]["date"][:10],
            "subject": subject,
            "class": classify(subject),
        }
        commits.append(record)

    # Aggregate overlap from the full comparison file list; per-commit file
    # queries are optional because they cost one API call each.
    files = [f["filename"] for f in compare.get("files", [])]
    aggregate_overlap = overlap_class(files, entry["overlap_paths"])

    if per_commit_files:
        for record in commits:
            detail = gh_api(f"repos/{upstream}/commits/{record['sha']}")
            names = [f["filename"] for f in detail.get("files", [])]
            record["overlap"] = overlap_class(names, entry["overlap_paths"])
            record["recommendation"] = recommend(record["class"], record["overlap"])
    else:
        for record in commits:
            record["overlap"] = aggregate_overlap
            record["recommendation"] = recommend(record["class"], aggregate_overlap)

    return {
        "id": entry["id"],
        "upstream": upstream,
        "verdict": "upgrade-available",
        "upstream_head": head_sha,
        "upstream_head_date": head_date,
        "fork_point": fork_point,
        "ahead_by": compare.get("ahead_by", len(commits)),
        "aggregate_overlap": aggregate_overlap,
        "commits": commits,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "upstream-watch.json",
    )
    parser.add_argument("--receipt", type=Path, help="write the JSON report here")
    parser.add_argument(
        "--only", action="append", help="watch only these manifest ids (repeatable)"
    )
    parser.add_argument(
        "--per-commit-files",
        action="store_true",
        help="score overlap per commit (one extra API call per commit)",
    )
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report: dict[str, Any] = {
        "artifact_type": "omp_ninfer_upstream_watch_report",
        "schema_version": 1,
        "generated_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "manifest": str(args.manifest),
        "upstreams": [],
    }

    failures = 0
    for entry in manifest["upstreams"]:
        if args.only and entry["id"] not in args.only:
            continue
        try:
            result = watch_one(entry, args.per_commit_files)
        except Exception as error:  # noqa: BLE001 - triage tool reports and continues
            failures += 1
            result = {"id": entry["id"], "upstream": entry["upstream"], "verdict": "error",
                      "error": str(error)}
        report["upstreams"].append(result)

    for result in report["upstreams"]:
        print(f"== {result['id']} ({result['upstream']}) -> {result['verdict']}")
        if result["verdict"] == "upgrade-available":
            print(f"   head {result['upstream_head'][:12]} ({result['upstream_head_date'][:10]}), "
                  f"{result['ahead_by']} commits past fork point, "
                  f"aggregate overlap: {result['aggregate_overlap']}")
            counts: dict[str, int] = {}
            for commit in result["commits"]:
                counts[commit["recommendation"]] = counts.get(commit["recommendation"], 0) + 1
            print(f"   recommendations: {json.dumps(counts, sort_keys=True)}")
            for commit in result["commits"]:
                if commit["recommendation"] in ("review-now", "pull-candidate"):
                    print(f"   {commit['recommendation']:>14}  {commit['sha']}  "
                          f"[{commit['class']}] {commit['subject'][:90]}")
        elif result["verdict"] == "error":
            print(f"   {result['error']}")

    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"receipt written: {args.receipt}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
