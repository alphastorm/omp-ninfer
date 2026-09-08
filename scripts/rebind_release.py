#!/usr/bin/env python3
"""Recompute the release evidence hash chain after any bound file changes.

Order matters and is fixed: the lane receipts under ``releases/<release>/qualification/`` are
hashed into the compatibility authority, the qualification composition, and the manifest's
native variants; compatibility.json is rendered and mirrored; the composed acceptance rebinds the
compatibility hash; the qualification summary rebinds the composed acceptance; and the manifest
rebinds the qualification summary and compatibility.

URL pinning is a separate, later step (``--pin <commit>``) because immutable raw URLs can only
reference a commit that already contains the final bytes. The dance is three pins, each after a
commit: ``--stage lane`` (commit contains the final lane receipts; rewrites the compatibility
authority's receipt URLs and reruns the chain), ``--stage acceptance`` (commit contains the final
composed acceptance), ``--stage manifest`` (commit contains the final qualification, compatibility,
and variant receipts). ``--draft`` rebinds the release tree only and leaves the root authority on
the previous release, which is the checked-in posture of a staged draft.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = "https://raw.githubusercontent.com/alphastorm/omp-ninfer"
PRIMARY_RECEIPT = "qualification/rtx5090.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def render(authority: Path, output: Path) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "render_compatibility.py"),
         "--authority", str(authority.relative_to(ROOT)),
         "--output", str(output.relative_to(ROOT))],
        check=True, cwd=ROOT,
    )


def bind_lane_receipts(release: str, compatibility_path: Path, manifest_path: Path,
                       qualification_path: Path) -> None:
    """Hash the release's lane receipts into every record that names them."""
    release_root = ROOT / "releases" / release
    primary_sha = sha256(release_root / PRIMARY_RECEIPT)

    compatibility = load(compatibility_path)
    for profile in compatibility.get("profiles", []):
        gpu = profile.get("gpu_qualification", {})
        if gpu.get("profile", "").startswith("qwen38-5090"):
            gpu["receipt"]["sha256"] = primary_sha
    manifest = load(manifest_path)
    variants = {item["id"]: item for item in manifest["components"].get("ninfer_variants", [])}
    for variant in compatibility.get("runtime_variants", []):
        summary = variants[variant["id"]]["qualification"]["summary"]
        receipt = variant["qualification_receipt"]
        receipt["path"] = summary
        receipt["sha256"] = sha256(ROOT / summary)
    save(compatibility_path, compatibility)

    for item in variants.values():
        item["qualification"]["sha256"] = sha256(ROOT / item["qualification"]["summary"])
    save(manifest_path, manifest)

    qualification = load(qualification_path)
    composition = qualification["composition"]
    behavioral = composition["behavioral_qualification"]
    behavioral["repository_path"] = f"releases/{release}/{PRIMARY_RECEIPT}"
    behavioral["sha256"] = primary_sha
    for variant_id, entry in composition.get("native_runtime_variants", {}).items():
        qual = variants[variant_id]["qualification"]
        entry["repository_path"] = qual["summary"]
        entry["sha256"] = qual["sha256"]
    save(qualification_path, qualification)


def pin_lane_urls(compatibility_path: Path, manifest_path: Path, release: str, raw: str) -> None:
    compatibility = load(compatibility_path)
    for profile in compatibility.get("profiles", []):
        gpu = profile.get("gpu_qualification", {})
        if gpu.get("profile", "").startswith("qwen38-5090"):
            gpu["receipt"]["url"] = f"{raw}/releases/{release}/{PRIMARY_RECEIPT}"
    manifest = load(manifest_path)
    variants = {item["id"]: item for item in manifest["components"].get("ninfer_variants", [])}
    for variant in compatibility.get("runtime_variants", []):
        summary = variants[variant["id"]]["qualification"]["summary"]
        variant["qualification_receipt"]["url"] = f"{raw}/{summary}"
    save(compatibility_path, compatibility)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", required=True, help="release directory name, e.g. v0.3.0")
    parser.add_argument("--pin", metavar="COMMIT",
                        help="pin evidence URLs to this 40-hex commit, then rebind as the stage requires")
    parser.add_argument("--stage", choices=("lane", "acceptance", "manifest"), default="acceptance",
                        help="pin stage: 'lane' rewrites the compatibility authority's lane-receipt "
                             "URLs and reruns the hash chain (commit must contain the final lane "
                             "receipts); 'acceptance' rewrites the qualification's acceptance URL "
                             "(commit must contain the final acceptance bytes); 'manifest' rewrites "
                             "the manifest's qualification, compatibility, and variant receipt URLs "
                             "(commit must contain the final qualification, compatibility, and "
                             "variant receipt bytes)")
    parser.add_argument("--draft", action="store_true",
                        help="rebind the release tree only; the root authority stays on the "
                             "previous release (staged-draft posture)")
    args = parser.parse_args()

    release_root = ROOT / "releases" / args.release
    manifest_path = release_root / "manifest.json"
    qualification_path = release_root / "qualification.json"
    acceptance_path = release_root / "acceptance" / "composed-external-installation.json"
    authority_path = release_root / "compatibility.json" if args.draft else ROOT / "compatibility.json"

    if args.pin:
        if len(args.pin) != 40:
            raise SystemExit("--pin requires a full 40-hex commit")
        raw = f"{RAW}/{args.pin}"
        if args.stage == "lane":
            pin_lane_urls(authority_path, manifest_path, args.release, raw)
            print(f"pinned lane receipt URLs to {args.pin}; rebinding the chain")
        elif args.stage == "acceptance":
            if acceptance_path.is_file():
                qualification = load(qualification_path)
                acceptance = qualification["composition"]["external_installation_acceptance"]
                acceptance["public_url"] = f"{raw}/releases/{args.release}/acceptance/composed-external-installation.json"
                save(qualification_path, qualification)
            manifest = load(manifest_path)
            manifest["qualification"]["summary_sha256"] = sha256(qualification_path)
            save(manifest_path, manifest)
            print(f"pinned acceptance URL to {args.pin}; commit, then run --stage manifest "
                  "with the NEW commit that contains these final qualification bytes")
            return 0
        else:
            manifest = load(manifest_path)
            manifest["qualification"]["summary_sha256"] = sha256(qualification_path)
            manifest["qualification"]["public_url"] = f"{raw}/releases/{args.release}/qualification.json"
            manifest["components"]["omp"]["compatibility_url"] = f"{raw}/compatibility.json"
            for variant in manifest["components"].get("ninfer_variants", []):
                variant["qualification"]["public_url"] = f"{raw}/{variant['qualification']['summary']}"
            save(manifest_path, manifest)
            print(f"pinned manifest evidence URLs to {args.pin}")
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "verify_release.py"),
                 "--release", args.release, "--require-ready"],
                check=True, cwd=ROOT,
            )
            return 0

    bind_lane_receipts(args.release, authority_path, manifest_path, qualification_path)
    if args.draft:
        render(authority_path, release_root / "COMPATIBILITY.md")
    else:
        render(authority_path, ROOT / "docs" / "COMPATIBILITY.md")
        shutil.copy(authority_path, release_root / "compatibility.json")
        shutil.copy(ROOT / "docs" / "COMPATIBILITY.md", release_root / "COMPATIBILITY.md")
    compatibility_sha = sha256(release_root / "compatibility.json")

    if acceptance_path.is_file():
        acceptance_doc = load(acceptance_path)
        if "compatibility_sha256" in acceptance_doc:
            acceptance_doc["compatibility_sha256"] = compatibility_sha
            save(acceptance_path, acceptance_doc)
        qualification = load(qualification_path)
        external = qualification["composition"]["external_installation_acceptance"]
        external["sha256"] = sha256(acceptance_path)
        if "compatibility_sha256" in external:
            external["compatibility_sha256"] = compatibility_sha
        save(qualification_path, qualification)

    manifest = load(manifest_path)
    manifest["components"]["omp"]["compatibility_sha256"] = compatibility_sha
    manifest["qualification"]["summary_sha256"] = sha256(qualification_path)
    save(manifest_path, manifest)
    print(f"rebound hash chain for {args.release}; compatibility {compatibility_sha[:12]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
