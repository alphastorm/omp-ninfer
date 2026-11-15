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
import ast
import base64
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API_COMMIT_LIMIT = 250
API_FILE_LIMIT = 300
QWEN4_MODELS_URL = "https://huggingface.co/api/models?author=Qwen&search=Qwen4"
DENSE_QWEN4_NAME = re.compile(r"qwen4(?:_(?:27b|dense)(?:_[a-z0-9]+)*)?")

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


def hf_models() -> dict[str, Any]:
    """Read the public organization search without forwarding GitHub credentials."""
    request = urllib.request.Request(QWEN4_MODELS_URL, method="GET")
    with urllib.request.urlopen(request, timeout=120) as response:
        return {
            "models": json.loads(response.read().decode("utf-8")),
            "has_next_page": bool(re.search(
                r'\brel="?next"?', response.headers.get("Link", ""), re.I,
            )),
        }


def validate_qwen4_readiness(result: dict[str, Any]) -> None:
    """Check the additive readiness receipt's closed schema and derived signals."""
    root_schema = {
        "schema_version": (int,), "id": (str,), "upstream": (str,), "verdict": (str,),
    }
    if result.get("verdict") == "error":
        root_schema["error"] = (str,)
    else:
        root_schema.update({
            "last_seen": (dict,), "hugging_face": (dict,), "engine": (dict,),
            "unknown_reasons": (list,), "applicability": (str,),
            "evidence_identity": (str,), "observation": (str,),
        })
    schemas = [(result, root_schema)]
    for document, schema in schemas:
        if (not isinstance(document, dict) or set(document) != set(schema)
                or any(type(document[key]) not in kinds for key, kinds in schema.items())):
            raise ValueError("invalid Qwen4 readiness receipt fields")
        if document is result and result["verdict"] != "error":
            schemas.extend([
                (result["last_seen"], {"ref": (str,), "commit": (str,), "commit_date": (str,)}),
                (result["hugging_face"], {
                    "url": (str,), "model_ids": (list,), "models_present": (bool, type(None)),
                    "has_next_page": (bool,),
                }),
                (result["engine"], {
                    "recipe_path": (str,), "dense_recipe_names": (list,),
                    "dense_recipe_present": (bool, type(None)), "models_path": (str,),
                    "dense_model_directories": (list,),
                    "dense_model_directory_present": (bool, type(None)), "models_truncated": (bool,),
                }),
            ])
    if result["schema_version"] != 1:
        raise ValueError("unsupported Qwen4 readiness receipt schema")
    if result["verdict"] == "error":
        return
    full_commit(result["last_seen"]["commit"])
    hf, engine = result["hugging_face"], result["engine"]
    if (hf["url"] != QWEN4_MODELS_URL
            or engine["recipe_path"] != "tools/convert/official_recipes.py"
            or engine["models_path"] != "src/models"):
        raise ValueError("unexpected Qwen4 readiness source")
    for values in (hf["model_ids"], engine["dense_recipe_names"],
                   engine["dense_model_directories"], result["unknown_reasons"]):
        if not all(isinstance(value, str) and value for value in values) or values != sorted(set(values)):
            raise ValueError("Qwen4 readiness lists must contain sorted unique strings")
    for present, values, incomplete in (
        (hf["models_present"], hf["model_ids"], hf["has_next_page"]),
        (engine["dense_recipe_present"], engine["dense_recipe_names"],
         "recipe-registry-not-understood" in result["unknown_reasons"]),
        (engine["dense_model_directory_present"], engine["dense_model_directories"],
         engine["models_truncated"]),
    ):
        expected = True if values else (None if incomplete else False)
        if present is not expected:
            raise ValueError("inconsistent Qwen4 readiness presence field")
    signals = (hf["models_present"], engine["dense_recipe_present"],
               engine["dense_model_directory_present"])
    verdict = ("unknown" if result["unknown_reasons"] else
               "delta-observed" if any(value is True for value in signals) else "up-to-date")
    if (result["verdict"] != verdict or result["applicability"] != "not-assessed"
            or result["observation"] not in ("initial", "changed", "unchanged")):
        raise ValueError("invalid Qwen4 readiness interpretation")
    evidence = {key: value for key, value in result.items()
                if key not in ("evidence_identity", "observation")}
    if result["evidence_identity"] != evidence_identity(evidence):
        raise ValueError("Qwen4 readiness evidence identity differs")


def watch_qwen4(
    entry: dict[str, Any], previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Observe official listings and named dense engine surfaces, never execute recipes."""
    hf = hf_models()
    models = hf["models"]
    if (not isinstance(models, list) or type(hf["has_next_page"]) is not bool
            or any(not isinstance(model, dict) or not isinstance(model.get("id"), str)
                   for model in models)):
        raise ValueError("expected Hugging Face model search objects with id fields")
    model_ids = sorted({model["id"] for model in models
                        if model["id"].startswith("Qwen/") and "qwen4" in model["id"][5:].lower()})
    upstream, ref = entry["upstream"], entry["upstream_ref"]
    head = gh_api(f"repos/{upstream}/commits/{ref}")
    sha = full_commit(head["sha"])
    recipe_path, models_path = "tools/convert/official_recipes.py", "src/models"
    recipe = gh_api(f"repos/{upstream}/contents/{recipe_path}?ref={sha}")
    if (not isinstance(recipe, dict) or recipe.get("encoding") != "base64"
            or not isinstance(recipe.get("content"), str)):
        raise ValueError("expected base64 GitHub recipe contents")
    source = base64.b64decode("".join(recipe["content"].split()), validate=True).decode("utf-8")
    reasons = []
    recipe_names = []
    try:
        registries = [
            node.value for node in ast.parse(source).body
            if (isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "RECIPES"
                        for target in node.targets))
            or (isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name) and node.target.id == "RECIPES")
        ]
        if len(registries) != 1 or not isinstance(registries[0], ast.Dict):
            raise ValueError("expected one literal RECIPES dictionary")
        keys = registries[0].keys
        if any(not isinstance(key, ast.Constant) or not isinstance(key.value, str) for key in keys):
            raise ValueError("expected literal recipe names")
        recipe_names = sorted({key.value for key in keys if DENSE_QWEN4_NAME.fullmatch(key.value)})
    except (SyntaxError, ValueError):
        reasons.append("recipe-registry-not-understood")
    directories = gh_api(f"repos/{upstream}/contents/{models_path}?ref={sha}")
    if (not isinstance(directories, list)
            or any(not isinstance(item, dict) or not isinstance(item.get("name"), str)
                   or item.get("type") not in ("file", "dir", "symlink", "submodule")
                   for item in directories)):
        raise ValueError("expected GitHub model directory listing")
    dense_directories = sorted({item["name"] for item in directories
                                if item["type"] == "dir" and DENSE_QWEN4_NAME.fullmatch(item["name"])})
    models_truncated = len(directories) >= 1000
    if models_truncated:
        reasons.append("model-directory-list-at-api-limit")
    if hf["has_next_page"]:
        reasons.append("hugging-face-pagination-incomplete")
    recipe_present = True if recipe_names else (None if "recipe-registry-not-understood" in reasons else False)
    directory_present = True if dense_directories else (None if models_truncated else False)
    weights_present = True if model_ids else (None if hf["has_next_page"] else False)
    result = {
        "schema_version": 1,
        "id": entry["id"],
        "upstream": upstream,
        "last_seen": {"ref": ref, "commit": sha, "commit_date": head["commit"]["committer"]["date"]},
        "hugging_face": {
            "url": QWEN4_MODELS_URL, "model_ids": model_ids,
            "models_present": weights_present, "has_next_page": hf["has_next_page"],
        },
        "engine": {
            "recipe_path": recipe_path, "dense_recipe_names": recipe_names,
            "dense_recipe_present": recipe_present, "models_path": models_path,
            "dense_model_directories": dense_directories,
            "dense_model_directory_present": directory_present, "models_truncated": models_truncated,
        },
        "verdict": ("unknown" if reasons else "delta-observed" if
                    any(value is True for value in (weights_present, recipe_present, directory_present))
                    else "up-to-date"),
        "unknown_reasons": sorted(reasons),
        "applicability": "not-assessed",
    }
    result["evidence_identity"] = evidence_identity(result)
    old_identity = previous.get("evidence_identity") if previous else None
    result["observation"] = (
        "initial" if old_identity is None else
        "unchanged" if old_identity == result["evidence_identity"] else "changed"
    )
    validate_qwen4_readiness(result)
    return result


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
    previous_checks = {}
    if args.receipt and args.receipt.exists():
        old_report = json.loads(args.receipt.read_text(encoding="utf-8"))
        previous = {
            (result["id"], result["upstream"]): result
            for result in old_report["upstreams"]
        }
        previous_checks = {
            (result["id"], result["upstream"]): result
            for result in old_report.get("readiness_checks", [])
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
        "readiness_checks": [],
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

    check = manifest.get("qwen4_readiness")
    if check and (not args.only or check["id"] in args.only):
        try:
            result = watch_qwen4(check, previous_checks.get((check["id"], check["upstream"])))
        except Exception as error:  # noqa: BLE001 - preserve the watch's report-and-continue contract
            failures += 1
            result = {"schema_version": 1, "id": check["id"], "upstream": check["upstream"],
                      "verdict": "error", "error": str(error)}
        validate_qwen4_readiness(result)
        report["readiness_checks"].append(result)

    report["evidence_identity"] = evidence_identity({
        "schema_version": report["schema_version"],
        "composition": composition,
        "inventory": manifest,
        "per_commit_files": args.per_commit_files,
        "upstreams": [
            {key: value for key, value in result.items() if key != "observation"}
            for result in report["upstreams"]
        ],
        "readiness_checks": [
            {key: value for key, value in result.items() if key != "observation"}
            for result in report["readiness_checks"]
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
    for result in report["readiness_checks"]:
        print(f"== {result['id']} ({result['upstream']}) -> {result['verdict']}")
        if result["verdict"] == "error":
            print(f"   {result['error']}")
            continue
        print(f"   last seen {result['last_seen']['commit']} ({result['observation']})")
        print(f"   official Qwen4 listing: {result['hugging_face']['models_present']}; "
              f"dense recipe: {result['engine']['dense_recipe_present']}; "
              f"dense model directory: {result['engine']['dense_model_directory_present']}; "
              "applicability not assessed")
        if result["unknown_reasons"]:
            print(f"   unknown: {', '.join(result['unknown_reasons'])}")
    print(f"evidence identity: {report['evidence_identity']}")

    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"receipt written: {args.receipt}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
