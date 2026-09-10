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
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
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
         receipt_path: Path, release: str) -> dict[str, Any]:
    variant_id = LANE_VARIANTS.get(lane)
    if variant_id is None:
        raise BindError(f"unknown native lane: {lane}")
    variants = manifest["components"].get("ninfer_variants", [])
    variant = next((item for item in variants if item.get("id") == variant_id), None)
    if variant is None:
        raise BindError(f"manifest has no {variant_id} variant")

    entries = parse_checksums(checksums)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("artifact_type") != "ninfer_windows_package_build_receipt":
        raise BindError("receipt is not a native package build receipt")
    if receipt.get("lane") != lane:
        raise BindError(f"receipt lane {receipt.get('lane')!r} is not {lane!r}")
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
    return variant


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--release", required=True, metavar="vX.Y.Z")
    parser.add_argument("--lane", required=True, choices=sorted(LANE_VARIANTS))
    parser.add_argument("--tag", required=True, help="component release tag the assets publish under")
    parser.add_argument("--checksums", type=Path, required=True, help="the lane's SHA256SUMS")
    parser.add_argument("--receipt", type=Path, required=True,
                        help="the lane's package-build-receipt.json")
    args = parser.parse_args()

    manifest_path = ROOT / "releases" / args.release / "manifest.json"
    if not manifest_path.is_file():
        parser.error(f"missing release manifest: {manifest_path}")
    for path in (args.checksums, args.receipt):
        if not path.is_file():
            parser.error(f"missing input: {path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    variant = bind(manifest, args.lane, args.tag, args.checksums, args.receipt, args.release)
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
