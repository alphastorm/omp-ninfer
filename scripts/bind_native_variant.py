#!/usr/bin/env python3
"""Bind a native Windows runtime component into a release manifest from its own build outputs.

A native lane's release identity is entirely determined by two files the packager already
produces - `SHA256SUMS` (the closed outer distribution set) and `package-build-receipt.json` -
plus the component tag the assets are published under, which must name the native package
filename's version and beta. Transcribing those into `releases/<version>/manifest.json` by hand
is how a derived record drifts from the bytes it claims to describe, which is exactly the failure
v0.5.1 had to correct.

    python3 scripts/bind_native_variant.py --release v0.14.0 --lane rtx4090 \
        --tag v0.7.0-qwen38-4090-beta.3 \
        --checksums /path/to/SHA256SUMS \
        --receipt /path/to/package-build-receipt.json

The script never invents a value: every hash comes from the checksum set, every size and identity
from the build receipt, and every URL from the tag plus the asset's own filename. Copy the lane's
qualification receipt to `releases/<version>/qualification/<lane>.json` first: for a rebind as for
a new lane, the verifier must accept the derived row, that receipt and the supplied checksum set
before anything is written. Only then does the script check the set into the release tree and
write the manifest. It leaves the release's hash chain to `rebind_release.py`, which must run
afterwards.
For a new lane, pass --add, --maximum-context-tokens and --qualification-commit after
committing its real qualification receipt; the row's release-local compatibility/qualification
mirrors are added with it. Without --add, a missing row remains an error. Root compatibility is
never promoted here.

From v0.15.0 supply the authenticated tar beside SHA256SUMS (or --package). Its
schema-5 runtime_shape is derived from bytes. New/changed native runtimes bind
--quality-screen; unchanged MTP rebuilds may instead bind --t1-parity with 84/84
actual retained-output-byte comparisons. DFlash2 also requires --fit-proof.
--maximum-context-tokens replaces both an existing row and its release-local mirror.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tarfile
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from render_compatibility import RUNTIME_VARIANT_IDS
from verify_release import (
    effective_native_model,
    native_dependency_sbom_filename,
    native_package_component_tag,
    product_version,
    sha256_file,
    validate_dependency_sbom,
    validate_ninfer_variants,
)
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
         qualification_commit: str | None = None, add: bool = False,
         quality_screen: Path | None = None, t1_parity: Path | None = None,
         fit_proof: Path | None = None, package_path: Path | None = None) -> dict[str, Any]:
    """Derive the lane's row, have the verifier accept it, and only then put it in `manifest`.

    Nothing is written: the caller checks the set into the release tree after this returns.
    """
    variant_id = LANE_VARIANTS.get(lane)
    if variant_id is None:
        raise BindError(f"unknown native lane: {lane}")
    variants = manifest["components"].get("ninfer_variants", [])
    index = next((position for position, item in enumerate(variants)
                  if item.get("id") == variant_id), None)
    if index is None:
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
    else:
        variant = deepcopy(variants[index])
    if maximum_context_tokens is not None:
        if maximum_context_tokens <= 0:
            raise BindError("--maximum-context-tokens must be positive")
        variant["maximum_context_tokens"] = maximum_context_tokens

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
    named_tag = native_package_component_tag(package_name)
    if named_tag is None:
        raise BindError(f"{package_name} is not a native package filename")
    if tag != named_tag:
        raise BindError(f"component tag {tag} must name the package version and beta ({named_tag})")
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
    dependency_name = native_dependency_sbom_filename(package_name)
    dependency_files = [name for name in entries if name.endswith(".cdx.json")]
    if dependency_files and dependency_files != [dependency_name]:
        raise BindError("dependency SBOM must use the unique canonical package-stem .cdx.json name")
    dependency_pins = {}
    if dependency_name in entries:
        dependency_pins = {
            "sbom_dependency_url": f"{DOWNLOAD}/{tag}/{dependency_name}",
            "sbom_dependency_sha256": entries[dependency_name],
        }
    dependency_errors: list[str] = []
    validate_dependency_sbom(
        {"release_tag": tag, "package_name": package_name, **dependency_pins},
        variant_id, dependency_errors)
    if dependency_errors:
        raise BindError("; ".join(dependency_errors))

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
    for field in ("sbom_dependency_url", "sbom_dependency_sha256"):
        variant.pop(field, None)
    variant.update(dependency_pins)
    if (product_version(release) or (0, 0, 0)) >= (0, 15, 0):
        variant["runtime_shape"] = package_runtime_shape(
            package_path or checksums.parent / package_name, receipt)
    for field, asset in SUPPORT_ASSETS.items():
        variant[f"{field}_url"] = f"{DOWNLOAD}/{tag}/{asset}"
        variant[f"{field}_sha256"] = require(entries, asset)
    qualification = variant.setdefault("qualification", {})
    qualification["summary"] = f"releases/{release}/qualification/{lane}.json"
    summary_path = ROOT / qualification["summary"]
    if not summary_path.is_file():
        raise BindError(f"missing lane qualification receipt: {qualification['summary']}")
    qualification["sha256"] = hashlib.sha256(summary_path.read_bytes()).hexdigest()
    for field, path, suffix in (("quality_screen", quality_screen, "quality-screen"),
                                ("t1_parity", t1_parity, "t1-parity"),
                                ("fit", fit_proof, "fit")):
        qualification.pop(field, None)
        if path is not None:
            qualification[field] = {
                "path": f"releases/{release}/qualification/{variant_id}.{suffix}.json",
                "sha256": sha256_file(path),
            }
    if index is None:
        qualification["public_url"] = (
            f"https://raw.githubusercontent.com/alphastorm/omp-ninfer/"
            f"{qualification_commit}/{qualification['summary']}"
        )
    errors: list[str] = []
    validate_ninfer_variants(
        ROOT, release, [variant], {"runtime_variants": [variant]},
        native_model.get("artifact_sha256"), errors,
        allow_pending=manifest.get("status") == "draft",
        incoming_checksums={variant_id: checksums},
        incoming_quality_screens={variant_id: quality_screen} if quality_screen else None,
        incoming_t1_parities={variant_id: t1_parity} if t1_parity else None,
        incoming_fits={variant_id: fit_proof} if fit_proof else None,
    )
    if errors:
        raise BindError("; ".join(errors))
    if index is None:
        variants.append(variant)
        variants.sort(key=lambda item: RUNTIME_VARIANT_IDS.index(item["id"]))
        manifest["components"]["ninfer_variants"] = variants
    else:
        variants[index] = variant
    return variant


def package_runtime_shape(path: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    """Derive policy from the authenticated tar, not an unbound transcription of its spec."""
    if not path.is_file() or sha256_file(path) != receipt["package"]["sha256"]:
        raise BindError("v0.15.0 native binding requires the hash-matching package tar (--package)")
    metadata: dict[str, tuple[dict[str, Any], str]] = {}
    with tarfile.open(path, mode="r|gz") as archive:
        for member in archive:
            name = Path(member.name).name
            if name not in ("release-spec.json", "server-config.json"):
                continue
            if name in metadata or not member.isfile() or member.size > 1024 * 1024:
                raise BindError("native tar must carry unique regular spec/config metadata")
            stream = archive.extractfile(member)
            if stream is None:
                raise BindError("native tar metadata is unreadable")
            data = stream.read()
            metadata[name] = (json.loads(data), hashlib.sha256(data).hexdigest())
    if set(metadata) != {"release-spec.json", "server-config.json"}:
        raise BindError("native tar is missing release-spec.json or server-config.json")
    spec = metadata["release-spec.json"][0]
    config, config_sha = metadata["server-config.json"]
    shape = spec.get("runtime_shape")
    if (spec.get("schema_version") != 5 or spec.get("lane") != receipt.get("lane")
            or config_sha != receipt.get("config_sha256") or not isinstance(shape, dict)
            or shape.get("speculative_backend") != config.get("speculative", {}).get("backend")):
        raise BindError("schema-5 package policy/config identity must match the build receipt")
    return shape


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
                        help="qualified context ceiling; may replace an existing lane's ceiling")
    parser.add_argument("--quality-screen", type=Path, help="passing powered native screen verdict")
    parser.add_argument("--t1-parity", type=Path, help="84/84 retained-byte parity for an unchanged MTP rebuild")
    parser.add_argument("--fit-proof", type=Path, help="shipping-config native DFlash2 fit receipt")
    parser.add_argument("--package", type=Path, help="native tar; defaults to beside SHA256SUMS (v0.15.0+)")
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
                   qualification_commit=args.qualification_commit, add=args.add,
                   quality_screen=args.quality_screen, t1_parity=args.t1_parity,
                   fit_proof=args.fit_proof, package_path=args.package)
    compatibility_path = ROOT / "releases" / args.release / "compatibility.json"
    compatibility = None
    if not is_new and args.maximum_context_tokens is not None:
        compatibility = json.loads(compatibility_path.read_text(encoding="utf-8"))
        mirror = next((row for row in compatibility["runtime_variants"] if row.get("id") == variant["id"]), None)
        if mirror is None:
            raise BindError("existing lane must have a release-local compatibility mirror")
        mirror["maximum_context_tokens"] = variant["maximum_context_tokens"]
    if is_new:
        add_lane_rows(args.release, variant)
    # Every check has passed. The manifest binds the closed outer set - the SHA256SUMS that lists
    # every published asset, not the per-package inner listing - and the verifier requires a
    # byte-identical copy of it in the release tree.
    checked_in = ROOT / "releases" / args.release / "qualification" / f"{variant['id']}.SHA256SUMS"
    checked_in.write_bytes(args.checksums.read_bytes())
    for field, path in (("quality_screen", args.quality_screen), ("t1_parity", args.t1_parity),
                        ("fit", args.fit_proof)):
        if path is not None:
            (ROOT / variant["qualification"][field]["path"]).write_bytes(path.read_bytes())
    if compatibility is not None:
        compatibility_path.write_text(json.dumps(compatibility, indent=2) + "\n", encoding="utf-8")
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
    except (BindError, OSError, ValueError, tarfile.TarError) as error:
        print(f"bind failed: {error}")
        raise SystemExit(1)
