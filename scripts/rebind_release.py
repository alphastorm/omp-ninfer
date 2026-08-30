#!/usr/bin/env python3
"""Recompute the release evidence hash chain after any bound file changes.

Order matters and is fixed: compatibility.json is rendered and mirrored first, the composed
acceptance rebinds the compatibility hash, the qualification summary rebinds the composed
acceptance, and the manifest rebinds the qualification summary and compatibility. URL pinning is
a separate, later step (`--pin <commit>`) because immutable raw URLs can only reference a commit
that already contains the final bytes; run the chain, commit, then pin and commit again.
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", required=True, help="release directory name, e.g. v0.3.0")
    parser.add_argument("--pin", metavar="COMMIT",
                        help="pin evidence URLs to this 40-hex commit instead of rebinding hashes")
    parser.add_argument("--stage", choices=("acceptance", "manifest"), default="acceptance",
                        help="pin stage: 'acceptance' rewrites the qualification's acceptance URL "
                             "(commit must contain the final acceptance bytes); 'manifest' rewrites "
                             "only the manifest's qualification/compatibility URLs (commit must "
                             "contain the final qualification and compatibility bytes)")
    args = parser.parse_args()

    release_root = ROOT / "releases" / args.release
    manifest_path = release_root / "manifest.json"
    qualification_path = release_root / "qualification.json"
    acceptance_path = release_root / "acceptance" / "composed-external-installation.json"

    if args.pin:
        if len(args.pin) != 40:
            raise SystemExit("--pin requires a full 40-hex commit")
        raw = f"{RAW}/{args.pin}"
        if args.stage == "acceptance":
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
        manifest = load(manifest_path)
        manifest["qualification"]["summary_sha256"] = sha256(qualification_path)
        manifest["qualification"]["public_url"] = f"{raw}/releases/{args.release}/qualification.json"
        manifest["components"]["omp"]["compatibility_url"] = f"{raw}/compatibility.json"
        save(manifest_path, manifest)
        print(f"pinned manifest evidence URLs to {args.pin}")
        return 0

    subprocess.run([sys.executable, str(ROOT / "scripts" / "render_compatibility.py")], check=True)
    shutil.copy(ROOT / "compatibility.json", release_root / "compatibility.json")
    shutil.copy(ROOT / "docs" / "COMPATIBILITY.md", release_root / "COMPATIBILITY.md")
    compatibility_sha = sha256(ROOT / "compatibility.json")

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
