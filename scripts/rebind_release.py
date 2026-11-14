#!/usr/bin/env python3
"""Recompute the release evidence hash chain after any bound file changes.

Order matters and is fixed: the lane receipts under ``releases/<release>/qualification/`` are
hashed into the compatibility authority, the qualification composition, and the manifest's
native variants; compatibility.json is rendered and mirrored; the composed acceptance rebinds the
compatibility hash; the qualification summary rebinds the composed acceptance; and the manifest
rebinds the qualification summary and compatibility.

URL pinning is a separate, later step (``--pin <commit>``) because immutable raw URLs can only
reference a commit that already contains the final bytes. The dance is four pins, each after a
commit: ``--stage lane`` is the cut (commit contains the final lane receipts; promotes the
release's compatibility copy to the root authority, rewrites the root profiles and launcher
examples from the manifest, pins the authority's receipt URLs, and reruns the chain),
``--stage platform`` (commit contains the final client platform acceptance receipts; pins each
compatibility profile's receipt URL and hash to those committed bytes and reruns the chain),
``--stage acceptance`` (commit contains the final composed acceptance), ``--stage manifest``
(commit contains the final qualification, compatibility, and variant receipts; runs the ready
verifier with --check-pins). ``--draft`` rebinds the release tree only and leaves the root
authority on the previous release, which is the checked-in posture of a staged draft.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_io import atomic_write, atomic_write_json
from release_profiles import stamp_profile
from verify_release import COMPONENT_TAG_RE, effective_native_model, product_version, runtime_contract_lanes

ROOT = Path(__file__).resolve().parents[1]
RAW = "https://raw.githubusercontent.com/alphastorm/omp-ninfer"
PRIMARY_RECEIPT = "qualification/rtx5090.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, document: dict) -> None:
    atomic_write_json(path, document)


def render(authority: Path, output: Path) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "render_compatibility.py"),
         "--authority", str(authority.relative_to(ROOT)),
         "--output", str(output.relative_to(ROOT))],
        check=True, cwd=ROOT,
    )


VARIANT_ROW_KEYS = ("release_tag", "source_commit", "package_name", "package_url",
                    "package_sha256", "package_bytes", "maximum_context_tokens")


def derive_runtime_contract_lanes(compatibility: dict, manifest: dict, release: str) -> None:
    """Identify existing rows by their stable lane prefix; never invent contract content."""
    if (product_version(release) or (0, 0, 0)) < (0, 18, 0):
        return
    lanes = runtime_contract_lanes(manifest)
    seen: set[str] = set()
    rows = compatibility.get("runtime_contracts")
    if not isinstance(rows, list):
        raise SystemExit("runtime_contracts must be an array")
    for row in rows:
        match = re.match(r"^RTX (5090|4090|3090) ", row.get("lane", "")) if isinstance(row, dict) else None
        if match is None:
            raise SystemExit(f"unrecognised runtime contract row: {row!r}")
        component = "rtx5090-container" if match[1] == "5090" else f"rtx{match[1]}-windows-native"
        if component in seen or component not in lanes:
            raise SystemExit(f"duplicate or unmatched runtime contract row: {component}")
        seen.add(component)
        row["lane"] = lanes[component]
    if seen != set(lanes):
        raise SystemExit(f"manifest component without a contract row: {sorted(set(lanes) - seen)}")


def derive_publication_target_tags(manifest: dict) -> None:
    """Replace only component tag tokens; surrounding operator prose is preserved."""
    components = manifest["components"]
    bound = {"5090": components["ninfer"]["release_tag"],
             "omp": components["omp"].get("component_release_tag")}
    bound.update({item["id"].split("-")[0].removeprefix("rtx"): item["release_tag"]
                  for item in components.get("ninfer_variants", [])})

    def replace(match: re.Match[str]) -> str:
        tag = match[0]
        lane = "omp" if tag.startswith("omp-") else next(
            (gpu for gpu in ("5090", "4090", "3090") if f"-{gpu}-" in tag), None)
        if not bound.get(lane):
            raise SystemExit(f"publication target names an unbound component tag: {tag}")
        return bound[lane]

    targets = manifest.get("publication", {}).get("targets", [])
    for index, target in enumerate(targets):
        if isinstance(target, str):
            targets[index] = COMPONENT_TAG_RE.sub(replace, target)


def bind_lane_receipts(release: str, compatibility_path: Path, manifest_path: Path,
                       qualification_path: Path) -> None:
    """Hash the release's lane receipts into every record that names them, and copy the
    runtime and native variant identities the compatibility authority mirrors from the
    manifest."""
    release_root = ROOT / "releases" / release
    primary_sha = sha256(release_root / PRIMARY_RECEIPT)

    manifest = load(manifest_path)
    ninfer = manifest["components"]["ninfer"]
    model = manifest["components"]["model"]
    native_model = effective_native_model(manifest)
    runtime = manifest["runtime_identity"]
    compatibility = load(compatibility_path)
    derive_runtime_contract_lanes(compatibility, manifest, release)
    derive_publication_target_tags(manifest)
    compatibility["product_release"] = release
    for profile in compatibility.get("profiles", []):
        profile["product_release"] = release
        profile["runtime"].update({
            "image_reference": ninfer["oci_reference"],
            "image_digest": ninfer["oci_manifest_digest"],
            "model_url": model["artifact_url"],
            "model_bytes": model["artifact_bytes"],
            "model_sha256": model["artifact_sha256"],
            "configuration_sha256": runtime["configuration_sha256"],
            "server_binary_sha256": ninfer["server_binary_sha256"],
        })
        gpu = profile["gpu_qualification"]
        gpu["profile"] = runtime["deployment_profile"]
        gpu["receipt"]["sha256"] = primary_sha
    variants = {item["id"]: item for item in manifest["components"].get("ninfer_variants", [])}
    for variant in compatibility.get("runtime_variants", []):
        source = variants[variant["id"]]
        for key in VARIANT_ROW_KEYS:
            variant[key] = source[key]
        variant.pop("build_profile", None)
        if "build_profile" in source:
            variant["build_profile"] = source["build_profile"]
        if "runtime_shape" in source:
            variant["runtime_shape"] = source["runtime_shape"]
        variant.update(model_url=native_model["artifact_url"],
                       model_bytes=native_model["artifact_bytes"],
                       model_sha256=native_model["artifact_sha256"])
        summary = source["qualification"]["summary"]
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
        source = variants[variant_id]
        entry["release_tag"] = source["release_tag"]
        entry["package_sha256"] = source["package_sha256"]
        entry.pop("build_profile", None)
        if "build_profile" in source:
            entry["build_profile"] = source["build_profile"]
        entry["repository_path"] = source["qualification"]["summary"]
        entry["sha256"] = source["qualification"]["sha256"]
    save(qualification_path, qualification)


def promote_root(release: str, manifest_path: Path) -> None:
    """The cut: the release's compatibility copy becomes the root authority, the root profiles
    and their existing release-local snapshots take identical manifest-stamped bytes,
    launcher pins advance, and a draft becomes an installable candidate."""
    release_root = ROOT / "releases" / release
    atomic_write(ROOT / "compatibility.json", (release_root / "compatibility.json").read_bytes())
    manifest = load(manifest_path)
    if manifest["status"] == "draft":
        manifest["status"] = "candidate"
        save(manifest_path, manifest)
    clients = {row["id"]: row["client_distribution"]
               for row in load(release_root / "compatibility.json")["profiles"]}
    for profile_path in sorted((ROOT / "profiles").glob("*.json")):
        staged_profile = release_root / "profiles" / profile_path.name
        profile = load(staged_profile if staged_profile.is_file() else profile_path)
        stamp_profile(profile, release, manifest, clients)
        save(profile_path, profile)
        if staged_profile.is_file():
            atomic_write(staged_profile, profile_path.read_bytes())
    for name, pattern, replacement in (
        ("start-ninfer.sh", r'^MANIFEST="\$ROOT/releases/[^/]+/manifest\.json"$',
         f'MANIFEST="$ROOT/releases/{release}/manifest.json"'),
        ("stop-ninfer.sh", r"^EXPECTED_RELEASE=\S+$", f"EXPECTED_RELEASE={release}"),
    ):
        path = ROOT / "examples" / "manual-tunnel" / name
        text, count = re.subn(pattern, replacement, path.read_text(encoding="utf-8"),
                              count=1, flags=re.MULTILINE)
        if count != 1:
            raise SystemExit(f"{path}: launcher pin not found")
        atomic_write(path, text)


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


def pin_platform_receipts(compatibility_path: Path, release: str, raw: str, commit: str) -> None:
    """Point every client profile at its platform receipt in the commit that holds its final
    bytes, refusing a commit whose bytes differ from the working tree's."""
    compatibility = load(compatibility_path)
    for profile in compatibility.get("profiles", []):
        receipt = profile.get("acceptance_receipt")
        if receipt is None:
            continue
        path = f"releases/{release}/acceptance/{receipt['url'].rsplit('/', 1)[-1]}"
        committed = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT,
                                   capture_output=True, check=True).stdout
        if committed != (ROOT / path).read_bytes():
            raise SystemExit(f"{path} at {commit} differs from the working tree")
        receipt["url"] = f"{raw}/{path}"
        receipt["sha256"] = hashlib.sha256(committed).hexdigest()
    save(compatibility_path, compatibility)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", required=True, help="release directory name, e.g. v0.3.0")
    parser.add_argument("--pin", metavar="COMMIT",
                        help="pin evidence URLs to this 40-hex commit, then rebind as the stage requires")
    parser.add_argument("--stage", choices=("lane", "platform", "acceptance", "manifest"),
                        default="acceptance",
                        help="pin stage: 'lane' rewrites the compatibility authority's lane-receipt "
                             "URLs and reruns the hash chain (commit must contain the final lane "
                             "receipts); 'platform' pins each client profile's platform receipt "
                             "URL and hash (commit must contain those receipts) and reruns the "
                             "chain; 'acceptance' rewrites the qualification's acceptance URL "
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
            if args.draft:
                raise SystemExit("--stage lane is the cut; it cannot keep the draft posture")
            promote_root(args.release, manifest_path)
            pin_lane_urls(authority_path, manifest_path, args.release, raw)
            print(f"promoted the root authority to {args.release} and pinned lane receipt "
                  f"URLs to {args.pin}; rebinding the chain")
        elif args.stage == "platform":
            if args.draft:
                raise SystemExit("--stage platform binds the root authority; it cannot keep the "
                                 "draft posture")
            pin_platform_receipts(authority_path, args.release, raw, args.pin)
            print(f"pinned client platform receipts to {args.pin}; rebinding the chain")
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
                 "--release", args.release, "--require-ready", "--check-pins"],
                check=True, cwd=ROOT,
            )
            return 0

    bind_lane_receipts(args.release, authority_path, manifest_path, qualification_path)
    if args.draft:
        render(authority_path, release_root / "COMPATIBILITY.md")
    else:
        render(authority_path, ROOT / "docs" / "COMPATIBILITY.md")
        atomic_write(release_root / "compatibility.json", authority_path.read_bytes())
        atomic_write(release_root / "COMPATIBILITY.md", (ROOT / "docs" / "COMPATIBILITY.md").read_bytes())
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
