#!/usr/bin/env python3
"""Read-only upstream fork-watch for the omp-ninfer product family.

Reads the current product composition and upstream-watch.json, then asks the
GitHub API (via ``gh``) for upstream drift. Title and path matches are triage,
never evidence that a change is applicable to the shipped product.

The tool never mutates anything: no fetches into local trees, no pushes, no
issue writes. Output is a human summary on stdout and, with ``--receipt``, a
JSON document suitable for committing next to qualification receipts. An existing
receipt supplies the previous observation; it never supplies the incorporated
baseline. Evidence identities exclude observation bookkeeping and run time.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API_COMMIT_LIMIT = 250
API_FILE_LIMIT = 300

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
        ["gh", "api", "--include", path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh api {path}: {result.stderr.strip()[:200]}")
    headers, body = result.stdout.replace("\r\n", "\n").split("\n\n", 1)
    document = json.loads(body)
    if isinstance(document, dict):
        document["_watch_has_next_page"] = any(
            line.lower().startswith("link:") and 'rel="next"' in line.lower()
            for line in headers.splitlines()
        )
    return document


def full_commit(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError("expected a full 40-hex commit identity")
    return value


def evidence_identity(document: Any) -> str:
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def load_composition(root: Path) -> dict[str, Any]:
    """The root authority selects the release; its manifest locks shipped sources."""
    authority = json.loads((root / "compatibility.json").read_text(encoding="utf-8"))
    release = authority["product_release"]
    manifest_path = Path("releases") / release / "manifest.json"
    manifest = json.loads((root / manifest_path).read_text(encoding="utf-8"))
    if manifest["release"] != release:
        raise ValueError("root authority and composition manifest releases disagree")
    components = manifest["components"]
    omp = components["omp"]
    engine = components["ninfer"]
    return {
        "product_release": release,
        "authority": "compatibility.json",
        "manifest": manifest_path.as_posix(),
        "client": {
            "repository": omp["upstream_repository"].removeprefix("https://github.com/"),
            "commit": full_commit(omp["upstream_commit"]),
            "tag": omp["upstream_tag"],
            "version": omp["distribution_version"],
        },
        "engine": {
            "repository": engine["repository"].removeprefix("https://github.com/"),
            "commit": full_commit(engine["source_commit"]),
            "tag": engine["release_tag"],
            "upstream_commit": full_commit(engine["upstream_commit"]),
            "variants": [
                {
                    "id": variant["id"],
                    "repository": variant["repository"].removeprefix("https://github.com/"),
                    "commit": full_commit(variant["source_commit"]),
                    "tag": variant["release_tag"],
                }
                for variant in components.get("ninfer_variants", [])
            ],
        },
    }


def incorporated_baseline(entry: dict[str, Any], composition: dict[str, Any]) -> dict[str, Any]:
    component = entry.get("baseline_component")
    if component == "omp":
        client = composition["client"]
        if entry["upstream"] != client["repository"]:
            raise ValueError("watched client repository differs from composition")
        return {
            "status": "derived",
            "role": "incorporated-upstream",
            **client,
            "product_release": composition["product_release"],
            "source": composition["manifest"] + "#/components/omp",
        }
    if component == "ninfer":
        engine = composition["engine"]
        if entry["fork_repo"] != engine["repository"]:
            raise ValueError("watched engine fork differs from composition")
        return {
            "status": "derived",
            "role": "incorporated-upstream-base",
            "repository": entry["upstream"],
            "commit": engine["upstream_commit"],
            "tag": None,
            "product_release": composition["product_release"],
            "source": composition["manifest"] + "#/components/ninfer/upstream_commit",
            "fork": engine,
        }
    if component is not None:
        raise ValueError(f"unknown baseline component {component!r}")
    return {
        "status": "declared-not-derived",
        "role": "declared-comparison-base; current incorporation not established",
        "repository": entry["upstream"],
        "commit": full_commit(entry["fork_point"]),
        "tag": entry.get("fork_point_tag"),
        "source": f"upstream-watch.json:upstreams[id={entry['id']}].fork_point",
        "meaning": entry["fork_point_meaning"],
    }


def overlap_class(files: list[str], overlap_paths: list[str]) -> str:
    if len(files) >= API_FILE_LIMIT:
        return "unknown-truncated"
    hits = sum(1 for name in files if any(name.startswith(p) for p in overlap_paths))
    if hits == 0:
        return "no-watched-path-match"
    if hits >= max(2, len(files) // 2):
        return "high-watched-path-match"
    return "watched-path-match"


def triage_label(commit_class: str, overlap: str) -> str:
    if overlap.startswith("unknown"):
        return "review-incomplete-evidence"
    if commit_class == "security":
        return "review-security-title"
    if commit_class in ("docs", "chore", "test"):
        return "review-low-priority-title"
    if overlap == "no-watched-path-match":
        return "review-no-watched-path-match"
    if commit_class in ("fix", "perf"):
        return "review-fix-or-perf-title"
    return "review"


def watch_one(
    entry: dict[str, Any],
    per_commit_files: bool,
    incorporated: dict[str, Any],
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    upstream = entry["upstream"]
    ref = entry["upstream_ref"]
    base = incorporated["commit"]

    head = gh_api(f"repos/{upstream}/commits/{ref}")
    head_sha = full_commit(head["sha"])
    last_seen = {
        "ref": ref,
        "commit": head_sha,
        "commit_date": head["commit"]["committer"]["date"],
        "tag": ref.removeprefix("refs/tags/") if ref.startswith("refs/tags/") else None,
    }
    if entry.get("observe_latest_release"):
        release = gh_api(f"repos/{upstream}/releases/latest")
        tag = release["tag_name"]
        peeled = gh_api(f"repos/{upstream}/commits/{tag}")
        last_seen["latest_release"] = {
            "tag": tag,
            "commit": full_commit(peeled["sha"]),
            "release_id": release["id"],
            "published_at": release["published_at"],
        }

    compare = (
        gh_api(f"repos/{upstream}/compare/{base}...{head_sha}")
        if head_sha != base else
        {"status": "identical", "ahead_by": 0, "total_commits": 0, "commits": [], "files": []}
    )
    items = compare.get("commits", [])
    files = [f["filename"] for f in compare.get("files", [])]
    ahead_by = compare.get("ahead_by")
    total = compare.get("total_commits", ahead_by)
    reasons = []
    commits_truncated = (
        not isinstance(total, int) or not isinstance(ahead_by, int)
        or len(items) < max(total, ahead_by)
        or len(items) >= API_COMMIT_LIMIT
    )
    files_truncated = len(files) >= API_FILE_LIMIT
    if commits_truncated:
        reasons.append("commit-list-truncated-or-unbounded")
    if files_truncated:
        reasons.append("file-list-at-api-limit")
    if compare.get("_watch_has_next_page"):
        reasons.append("pagination-incomplete")
    if "commits" not in compare or "files" not in compare:
        reasons.append("comparison-lists-missing")
    if compare.get("status") not in ("ahead", "identical"):
        reasons.append("non-forward-or-unknown-comparison")
    aggregate_overlap = (
        "unknown-truncated" if reasons else overlap_class(files, entry["overlap_paths"])
    )
    comparison_unknown = bool(reasons)
    commits: list[dict[str, Any]] = []
    for item in items:
        subject = item["commit"]["message"].splitlines()[0]
        record: dict[str, Any] = {
            "sha": full_commit(item["sha"]),
            "date": item["commit"]["committer"]["date"][:10],
            "subject": subject,
            "title_triage": classify(subject),
            "applicability": "not-assessed",
        }
        path_triage = aggregate_overlap
        if per_commit_files:
            detail = gh_api(f"repos/{upstream}/commits/{record['sha']}")
            names = [f["filename"] for f in detail.get("files", [])]
            detail_unknown = (
                detail.get("_watch_has_next_page") or "files" not in detail
                or len(names) >= API_FILE_LIMIT
            )
            if detail_unknown:
                reasons.append(f"commit-files-incomplete:{record['sha']}")
            path_triage = (
                "unknown-truncated" if detail_unknown or comparison_unknown
                else overlap_class(names, entry["overlap_paths"])
            )
        record["path_triage"] = path_triage
        record["triage"] = triage_label(record["title_triage"], path_triage)
        commits.append(record)

    result = {
        "id": entry["id"],
        "upstream": upstream,
        "fork_repo": entry["fork_repo"],
        "incorporated": incorporated,
        "last_seen": last_seen,
        "verdict": "unknown" if reasons else ("up-to-date" if head_sha == base else "delta-observed"),
        "comparison": {
            "status": "unknown" if reasons else "complete",
            "api_status": compare.get("status"),
            "base_commit": base,
            "head_commit": head_sha,
            "ahead_by": ahead_by,
            "commits_listed": len(commits),
            "commits_truncated": commits_truncated,
            "files_listed": len(files),
            "files_truncated": files_truncated,
            "path_triage": "unknown-truncated" if reasons else aggregate_overlap,
            "unknown_reasons": reasons,
        },
        "commits": commits,
    }
    result["evidence_identity"] = evidence_identity(result)
    old_seen = previous.get("last_seen") if previous else None
    result["observation"] = (
        "initial" if old_seen is None else ("unchanged" if old_seen == last_seen else "changed")
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "upstream-watch.json",
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
    composition = load_composition(ROOT)
    previous = {}
    if args.receipt and args.receipt.exists():
        previous = {
            (result["id"], result["upstream"]): result
            for result in json.loads(args.receipt.read_text(encoding="utf-8"))["upstreams"]
        }
    report: dict[str, Any] = {
        "artifact_type": "omp_ninfer_upstream_watch_report",
        "schema_version": 2,
        "generated_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        # repo-relative: a committed receipt must not carry the operator's absolute path
        "manifest": "./" + str(args.manifest.resolve().relative_to(ROOT))
        if args.manifest.resolve().is_relative_to(ROOT) else args.manifest.name,
        "composition": composition,
        "interpretation": "Title/path triage only; applicability is not assessed, including unchanged observations.",
        "residuals": [],
        "upstreams": [],
    }

    failures = 0
    for entry in manifest["upstreams"]:
        if args.only and entry["id"] not in args.only:
            continue
        try:
            incorporated = incorporated_baseline(entry, composition)
            if incorporated["status"] == "declared-not-derived":
                report["residuals"].append(
                    f"{entry['id']}: no composition manifest states incorporation of this watched "
                    "lineage; retained declared comparison base, not a current adoption claim."
                )
            result = watch_one(
                entry, args.per_commit_files, incorporated,
                previous.get((entry["id"], entry["upstream"])),
            )
        except Exception as error:  # noqa: BLE001 - triage tool reports and continues
            failures += 1
            result = {"id": entry["id"], "upstream": entry["upstream"], "verdict": "error",
                      "error": str(error)}
        report["upstreams"].append(result)

    report["evidence_identity"] = evidence_identity({
        "schema_version": report["schema_version"],
        "composition": composition,
        "inventory": manifest,
        "per_commit_files": args.per_commit_files,
        "upstreams": [
            {key: value for key, value in result.items() if key != "observation"}
            for result in report["upstreams"]
        ],
    })
    for result in report["upstreams"]:
        print(f"== {result['id']} ({result['upstream']}) -> {result['verdict']}")
        if result["verdict"] == "error":
            print(f"   {result['error']}")
            continue
        print(f"   baseline {result['incorporated']['commit']} "
              f"({result['incorporated']['status']})")
        print(f"   last seen {result['last_seen']['commit']} ({result['observation']})")
        comparison = result["comparison"]
        print(f"   {comparison['ahead_by']} commits ahead; comparison {comparison['status']}; "
              f"path triage {comparison['path_triage']}; applicability not assessed")
        if comparison["unknown_reasons"]:
            print(f"   unknown: {', '.join(comparison['unknown_reasons'])}")
    print(f"evidence identity: {report['evidence_identity']}")

    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"receipt written: {args.receipt}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
