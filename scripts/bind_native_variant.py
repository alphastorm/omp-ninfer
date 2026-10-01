#!/usr/bin/env python3
"""Bind a native Windows runtime component into a release manifest from its own build outputs.

A native lane's release identity is entirely determined by two files the packager already
produces - `SHA256SUMS` (the closed outer distribution set) and `package-build-receipt.json` -
plus the component tag the assets are published under. Transcribing those into
`releases/<version>/manifest.json` by hand is how a derived record drifts from the bytes it
claims to describe, which is exactly the failure v0.5.1 had to correct.

    python3 scripts/bind_native_variant.py --release v0.6.0 --lane rtx4090 \
        --tag v0.6.0-qwen38-4090-native.1 \
        --checksums /path/to/SHA256SUMS \
        --receipt /path/to/package-build-receipt.json

The script never invents a value: every hash comes from the checksum set, every size and identity
from the build receipt, and every URL from the tag plus the asset's own filename. It refuses a
distribution set that does not carry each asset the manifest binds, and it leaves the release's
hash chain to `rebind_release.py`, which must run afterwards.
For a new lane, pass --add, --maximum-context-tokens and --qualification-commit after
committing its real qualification receipt. The verifier must accept that receipt before
the manifest row and its release-local compatibility/qualification mirrors are added.
Without --add, a missing row remains an error. Root compatibility is never promoted here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from render_compatibility import RUNTIME_VARIANT_IDS
from verify_release import effective_native_model, validate_ninfer_variants
DOWNLOAD = "https://github.com/alphastorm/ninfer/releases/download"
LANE_VARIANTS = {"rtx4090": "rtx4090-windows-native", "rtx3090": "rtx3090-windows-native"}
# Every manifest field that names a distribution asset, and the role it plays in the set.
SUPPORT_ASSETS = {
    "installer": "Install-Release.ps1",
    "controller": "Control-Release.ps1",
    "gpu_owner_controller": "Control-GpuOwner.ps1",
    "state_protection": "Protect-StateRoot.ps1",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class BindError(RuntimeError):
    pass


def parse_checksums(path: Path) -> dict[str, str]:
    """The packager writes `<sha256>  <name>` lines with LF endings and no directories."""
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, name = line.partition("  ")
        if not SHA256_RE.fullmatch(digest) or not name or "/" in name or "\\" in name:
            raise BindError(f"malformed checksum line: {line!r}")
        if name in entries:
            raise BindError(f"duplicate checksum entry: {name}")
        entries[name] = digest
    if not entries:
        raise BindError(f"empty checksum set: {path}")
    return entries


def require(entries: dict[str, str], name: str) -> str:
    if name not in entries:
        raise BindError(f"distribution set does not carry {name}")
    return entries[name]


def bind(manifest: dict[str, Any], lane: str, tag: str, checksums: Path,
         receipt_path: Path, release: str, *, maximum_context_tokens: int | None = None,
         qualification_commit: str | None = None, add: bool = False) -> dict[str, Any]:
    variant_id = LANE_VARIANTS.get(lane)
    if variant_id is None:
        raise BindError(f"unknown native lane: {lane}")
    variants = manifest["components"].get("ninfer_variants", [])
    variant = next((item for item in variants if item.get("id") == variant_id), None)
    new_variant = variant is None
    if variant is None:
        if not add:
            raise BindError(f"manifest has no {variant_id} variant; use --add to admit a new lane")
        if maximum_context_tokens is None or maximum_context_tokens <= 0:
            raise BindError("a new native variant requires --maximum-context-tokens")
        if not qualification_commit or not re.fullmatch(r"[0-9a-f]{40}", qualification_commit):
            raise BindError("a new native variant requires --qualification-commit (receipt commit)")
        variant = {
            "id": variant_id, "status": "qualified", "installable": True,
            "repository": "https://github.com/alphastorm/ninfer",
            "maximum_context_tokens": maximum_context_tokens,
        }

    entries = parse_checksums(checksums)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("artifact_type") != "ninfer_windows_package_build_receipt":
        raise BindError("receipt is not a native package build receipt")
    if receipt.get("lane") != lane:
        raise BindError(f"receipt lane {receipt.get('lane')!r} is not {lane!r}")
    native_model = effective_native_model(manifest)
    if receipt.get("model_sha256") != native_model.get("artifact_sha256"):
        raise BindError("build receipt model must match the effective native model")
    package = receipt["package"]
    package_name = package["filename"]
    if require(entries, package_name) != package["sha256"]:
        raise BindError("package hash disagrees between the build receipt and the checksum set")
    if require(entries, receipt_path.name) != hashlib.sha256(
            receipt_path.read_bytes()).hexdigest():
        raise BindError("the build receipt does not hash to its own checksum entry")

    stem = package_name.removesuffix(".tar.gz")
    sbom_name = f"{stem}.spdx.json"
    source_name = next((name for name in entries if name.endswith("-source.tar.gz")), None)
    if source_name is None:
        raise BindError("distribution set does not carry a source archive")
    # The manifest binds the closed outer set - the SHA256SUMS that lists every published asset,
    # not the per-package inner listing - and the verifier requires a byte-identical copy of it
    # in the release tree.
    checked_in = ROOT / "releases" / release / "qualification" / f"{variant_id}.SHA256SUMS"
    checked_in.write_bytes(checksums.read_bytes())

    variant.update({
        "release_tag": tag,
        "source_commit": receipt["patch_stack_sha"],
        "source_archive_url": f"{DOWNLOAD}/{tag}/{source_name}",
        "source_archive_sha256": entries[source_name],
        "package_name": package_name,
        "package_url": f"{DOWNLOAD}/{tag}/{package_name}",
        "package_sha256": package["sha256"],
        "package_bytes": package["bytes"],
        "sbom_url": f"{DOWNLOAD}/{tag}/{sbom_name}",
        "sbom_sha256": require(entries, sbom_name),
        "server_binary_sha256": receipt["binaries"]["server_sha256"],
        "configuration_sha256": receipt["config_sha256"],
        "model_artifact_sha256": receipt["model_sha256"],
        "checksums_url": f"{DOWNLOAD}/{tag}/{checksums.name}",
        "checksums_sha256": hashlib.sha256(checksums.read_bytes()).hexdigest(),
    })
    for field, asset in SUPPORT_ASSETS.items():
        variant[f"{field}_url"] = f"{DOWNLOAD}/{tag}/{asset}"
        variant[f"{field}_sha256"] = require(entries, asset)
    qualification = variant.setdefault("qualification", {})
    qualification["summary"] = f"releases/{release}/qualification/{lane}.json"
    summary_path = ROOT / qualification["summary"]
    if not summary_path.is_file():
        raise BindError(f"missing lane qualification receipt: {qualification['summary']}")
    qualification["sha256"] = hashlib.sha256(summary_path.read_bytes()).hexdigest()
    if new_variant:
        qualification["public_url"] = (
            f"https://raw.githubusercontent.com/alphastorm/omp-ninfer/"
            f"{qualification_commit}/{qualification['summary']}"
        )
        errors: list[str] = []
        validate_ninfer_variants(
            ROOT, release, [variant], {"runtime_variants": [variant]},
            native_model.get("artifact_sha256"), errors,
        )
        if errors:
            raise BindError("; ".join(errors))
        variants.append(variant)
        variants.sort(key=lambda item: RUNTIME_VARIANT_IDS.index(item["id"]))
        manifest["components"]["ninfer_variants"] = variants
    return variant


def add_lane_rows(release: str, variant: dict[str, Any]) -> None:
    """Create the authority mirrors only for a newly admitted, verified manifest lane.

    Rebind owns subsequent hash and URL promotion; the root authority remains untouched.
    """
    release_root = ROOT / "releases" / release
    compatibility_path = release_root / "compatibility.json"
    qualification_path = release_root / "qualification.json"
    compatibility = json.loads(compatibility_path.read_text(encoding="utf-8"))
    qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
    variant_id = variant["id"]
    lane = variant_id.split("-", 1)[0]
    summary = variant["qualification"]
    rows = compatibility.setdefault("runtime_variants", [])
    if any(row["id"] == variant_id for row in rows):
        raise BindError(f"compatibility already contains {variant_id} without a manifest row")
    rows.append({
        "id": variant_id, "status": variant["status"], "platform": "Windows 11 x64",
        "gpu": f"NVIDIA GeForce RTX {lane.removeprefix('rtx')}",
        "cuda_architecture": {"rtx3090": "sm_86", "rtx4090": "sm_89"}[lane],
        "installation_mode": "native-windows-package", "installable": variant["installable"],
        "silent_cloud_fallback": False,
        **{key: variant[key] for key in (
            "release_tag", "source_commit", "package_name", "package_url", "package_sha256",
            "package_bytes", "maximum_context_tokens")},
        "qualification_receipt": {"path": summary["summary"], "url": summary["public_url"],
                                  "sha256": summary["sha256"]},
    })
    rows.sort(key=lambda row: RUNTIME_VARIANT_IDS.index(row["id"]))
    native = qualification["composition"].setdefault("native_runtime_variants", {})
    native[variant_id] = {
        "status": "passed", "beta_qualified": True, "installable": True,
        "repository_path": summary["summary"], "sha256": summary["sha256"],
        "release_tag": variant["release_tag"], "package_sha256": variant["package_sha256"],
    }
    qualification["composition"]["native_runtime_variants"] = {
        key: native[key] for key in RUNTIME_VARIANT_IDS if key in native
    }
    for path, value in ((compatibility_path, compatibility), (qualification_path, qualification)):
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--release", required=True, metavar="vX.Y.Z")
    parser.add_argument("--lane", required=True, choices=sorted(LANE_VARIANTS))
    parser.add_argument("--tag", required=True, help="component release tag the assets publish under")
    parser.add_argument("--checksums", type=Path, required=True, help="the lane's SHA256SUMS")
    parser.add_argument("--receipt", type=Path, required=True,
                        help="the lane's package-build-receipt.json")
    parser.add_argument("--add", action="store_true", help="explicitly admit a missing native lane")
    parser.add_argument("--maximum-context-tokens", type=int,
                        help="qualified context ceiling; required when adding a lane")
    parser.add_argument("--qualification-commit",
                        help="40-hex product commit containing the lane receipt; required for a new lane")
    args = parser.parse_args()

    manifest_path = ROOT / "releases" / args.release / "manifest.json"
    if not manifest_path.is_file():
        parser.error(f"missing release manifest: {manifest_path}")
    for path in (args.checksums, args.receipt):
        if not path.is_file():
            parser.error(f"missing input: {path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    is_new = not any(row.get("id") == LANE_VARIANTS[args.lane]
                     for row in manifest["components"].get("ninfer_variants", []))
    variant = bind(manifest, args.lane, args.tag, args.checksums, args.receipt, args.release,
                   maximum_context_tokens=args.maximum_context_tokens,
                   qualification_commit=args.qualification_commit, add=args.add)
    if is_new:
        add_lane_rows(args.release, variant)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"bound {variant['id']} in releases/{args.release}/manifest.json")
    print(f"  package {variant['package_name']} {variant['package_bytes']} bytes")
    print(f"  source  {variant['source_commit']}")
    print(f"  tag     {variant['release_tag']}")
    print("run scripts/rebind_release.py next: the hash chain is not recomputed here")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BindError as error:
        print(f"bind failed: {error}")
        raise SystemExit(1)
