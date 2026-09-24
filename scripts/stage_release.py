#!/usr/bin/env python3
"""Stage a new release tree from the previous one with a consistent hash chain.

Mechanizes the identity/hash plumbing that was executed by hand for v0.4.3 and
v0.4.4 (class closure: second manual run of the same sequence). It does NOT
author evidence: lane-receipt arcs, qualification gate numbers, CHANGELOG, and
doc prose remain the lead's job. What it owns:

  1. Copy releases/<from> -> releases/<release>.
  2. Rewrite the NInfer component pins in manifest.json (release tag, upstream
     and source commits, archive/binary/SBOM hashes, OCI digest, runtime receipt
     release, download URLs) and the runtime identity (deployment profile and
     configuration hash).
  3. Rewrite <from> -> <release> internal paths (variant qualification
     summaries and every provisional public URL).
  4. Rebase the release's compatibility.json (product_release, 5090 profile
     string, image digest, server binary, configuration hash).
  5. Rebase qualification.json identity and local-release-packaging pins.
  6. Recompute the hash chain through `rebind_release.py --draft`: lane
     receipts -> compatibility variants/qualification/manifest bindings ->
     acceptance compatibility binding -> acceptance hash -> qualification
     hash -> manifest summary hash. The root authority and profiles stay on
     the previous release (staged-draft posture) until the cut.
  7. Run the release verifier; the only residue is the draft posture, the
     commit-bound public-URL set, and the tag allowlist entry.

The cut is `rebind_release.py --pin <commit> --stage lane`, which promotes the
root authority, profiles, and launcher pins, followed by the acceptance and
manifest pin stages.

With --omp-component, the JSON object contains an "omp" manifest component and a
"platforms" map of darwin-arm64/windows-x64/linux-x64 client_distribution rows.
Raw upstream binary hashes must equal their asset hashes. Client acceptance is
reset, never inherited. Root profiles are not promoted by staging. The completed
draft reports surviving predecessor pins as file:line warnings so the lead can
replace its prose and evidence; --require-clean-client makes those warnings a
staging failure. Ready verification rejects retired fork tags, source commits
and asset URLs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_compatibility import OMP_PROFILE_PLATFORMS
from verify_release import (
    ContractError,
    client_identity_pins,
    client_pin_locations,
    load_json,
    validate_upstream_client_bindings,
    validate_upstream_omp_component,
)

ROOT = Path(__file__).resolve().parents[1]

# The four errors the URL-pin dance (rebind_release.py) resolves after commit;
# everything else is a staging defect this script must not leave behind.
PIN_RESIDUE = {
    "components.ninfer_variants.rtx3090-windows-native.qualification.public_url must bind an immutable product commit and path",
    "components.ninfer_variants.rtx4090-windows-native.qualification.public_url must bind an immutable product commit and path",
    "external acceptance public_url must bind an immutable product commit and path",
    "qualification.public_url must bind an immutable product commit and path",
}
# The root authority, matrix, and profiles stay on the previous release until the cut.
DRAFT_POSTURE_RESIDUE = {
    "profile: release must match the manifest",
    "profile: deployment_profile must match the manifest",
    "profiles/qwen38-rtx5090-manual-tunnel.json: release must match the manifest",
    "profiles/qwen38-rtx5090-manual-tunnel.json: deployment_profile must match the manifest",
    "root and release compatibility authorities must be byte-identical",
    "root and release compatibility matrices must be byte-identical",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=1) + "\n", encoding="utf-8")


def rewrite_text(path: Path, replacements: dict[str, str]) -> int:
    text = original = path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        text = text.replace(old, new)
    if text != original:
        path.write_text(text, encoding="utf-8")
    return sum(original.count(old) for old in replacements)


def load_omp_component(path: Path) -> dict:
    """Read {"omp": <components.omp>, "platforms": {<platform>: <client_distribution>}}.

    Platforms are darwin-arm64, windows-x64 and linux-x64. The omp object holds
    upstream provenance plus the primary raw binary; each platform row holds its
    own published asset. Compatibility bindings may be omitted: staging retains
    their provisional predecessor values and rebind recomputes the hash.
    """
    descriptor = load_json(path)
    omp = descriptor.get("omp")
    platforms = descriptor.get("platforms")
    if not isinstance(omp, dict):
        raise ValueError("OMP descriptor.omp must be a components.omp object")
    if not isinstance(platforms, dict) or set(platforms) != set(OMP_PROFILE_PLATFORMS.values()):
        raise ValueError("OMP descriptor.platforms must contain darwin-arm64, windows-x64 and linux-x64")
    if any(not isinstance(client, dict) for client in platforms.values()):
        raise ValueError("OMP descriptor platform client_distribution rows must be objects")
    errors: list[str] = []
    validate_upstream_omp_component(omp, errors)
    validate_upstream_client_bindings(omp, [
        {"id": profile_id, "client_distribution": platforms[platform]}
        for profile_id, platform in OMP_PROFILE_PLATFORMS.items()
    ], errors)
    if errors:
        raise ValueError("; ".join(errors))
    return descriptor


def bind_upstream_client(compatibility: dict, descriptor: dict, release: str) -> None:
    omp = descriptor["omp"]
    composition = compatibility["composition"]
    for key in ("qualification_source_commit", "lifecycle_main_commit", "lifecycle_main_tree",
                "lifecycle_semantic_tree", "lifecycle_generated_lock_tree", "hosted_ci"):
        composition.pop(key, None)
    composition.update({
        "status": f"{release} upstream OMP {omp['upstream_tag']} client acceptance pending",
        "lifecycle_repository": omp["upstream_repository"],
        "lifecycle_source_release": f"{omp['upstream_repository']}/releases/tag/{omp['upstream_tag']}",
        "lifecycle_source_commit": omp["upstream_commit"],
        "request_compatibility_source_commit": omp["upstream_commit"],
        "composed_source_commit": omp["upstream_commit"],
    })
    for profile in compatibility["profiles"]:
        platform = OMP_PROFILE_PLATFORMS[profile["id"]]
        profile["client_distribution"] = descriptor["platforms"][platform]
        profile["acceptance_receipt"] = None
        profile["installable"] = False
        if profile["status"] == "qualified":
            profile["status"] = "preview"
        profile["blockers"] = [f"upstream OMP {omp['upstream_tag']} client acceptance is pending"]


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--from", dest="source", required=True, metavar="vX.Y.Z",
                        help="previous release directory to stage from")
    parser.add_argument("--release", required=True, metavar="vX.Y.Z")
    parser.add_argument("--release-tag", required=True,
                        help="ninfer runtime release tag, e.g. v0.4.4-qwen38-5090-beta.1")
    parser.add_argument("--source-tag", required=True,
                        help="ninfer source release tag, e.g. v0.4.4-qwen38-5090-source.1")
    parser.add_argument("--source-commit", required=True, metavar="SHA40")
    parser.add_argument("--binary-sha", required=True, metavar="SHA256",
                        help="server binary sha256 inside the archive")
    parser.add_argument("--archive-sha", required=True, metavar="SHA256")
    parser.add_argument("--source-archive-sha", required=True, metavar="SHA256")
    parser.add_argument("--sbom-sha", required=True, metavar="SHA256")
    parser.add_argument("--image-digest", required=True, metavar="sha256:...",
                        help="published OCI manifest digest")
    parser.add_argument("--runtime-receipt-release", required=True,
                        help="companion runtime-image receipt release tag")
    parser.add_argument("--archive-name", default=None,
                        help="binary archive asset name; default derives from the release")
    parser.add_argument("--keep-deployment-profile", action="store_true",
                        help="variant-only rebind: keep the prior 5090 deployment profile "
                             "(v0.4.2 precedent - the container identity does not advance)")
    parser.add_argument("--profile-from", default=None, metavar="vX.Y.Z",
                        help="release whose 5090 deployment profile is currently live, when a "
                             "variant-only rebind left it behind the source release")
    parser.add_argument("--config-sha", default=None, metavar="SHA256",
                        help="configuration identity of the new 5090 deployment profile as the "
                             "lifecycle tool computes it (required unless "
                             "--keep-deployment-profile)")
    parser.add_argument("--upstream-commit", default=None, metavar="SHA40",
                        help="new upstream base of the runtime fork; default keeps the source "
                             "release's")
    parser.add_argument("--lane-receipt", type=Path, default=None, metavar="PATH",
                        help="the new release's RTX 5090 qualification receipt; installed as "
                             "releases/<release>/qualification/rtx5090.json before the hash "
                             "chain is computed, so the lane-receipt hash binds the real "
                             "evidence rather than the copied predecessor")
    parser.add_argument("--omp-component", type=Path, metavar="PATH",
                        help="upstream client JSON: omp manifest component plus platforms map "
                             "(darwin-arm64, windows-x64, linux-x64); requires fresh client acceptance")
    parser.add_argument("--require-clean-client", action="store_true",
                        help="after writing the draft, fail if any predecessor client pin remains; "
                             "otherwise report file:line warnings for the lead to resolve")
    args = parser.parse_args()
    if args.require_clean_client and args.omp_component is None:
        parser.error("--require-clean-client requires --omp-component")
    omp_descriptor = None
    if args.omp_component is not None:
        try:
            omp_descriptor = load_omp_component(args.omp_component)
        except (ContractError, ValueError) as error:
            parser.error(f"--omp-component: {error}")
    if args.lane_receipt is not None and not args.lane_receipt.is_file():
        parser.error(f"missing lane receipt: {args.lane_receipt}")

    if not args.image_digest.startswith("sha256:"):
        parser.error("--image-digest must start with sha256:")
    for name in ("binary_sha", "archive_sha", "source_archive_sha", "sbom_sha"):
        value = getattr(args, name)
        if len(value) != 64:
            parser.error(f"--{name.replace('_', '-')} must be a 64-hex sha256")
    if args.keep_deployment_profile:
        if args.config_sha is not None:
            parser.error("--config-sha changes the deployment profile; drop --keep-deployment-profile")
    elif args.config_sha is None or len(args.config_sha) != 64:
        parser.error("--config-sha must be a 64-hex sha256 (or pass --keep-deployment-profile)")
    if args.upstream_commit is not None and len(args.upstream_commit) != 40:
        parser.error("--upstream-commit must be a full 40-hex commit")

    src_dir = ROOT / "releases" / args.source
    dst_dir = ROOT / "releases" / args.release
    if not src_dir.is_dir():
        parser.error(f"missing source release tree: {src_dir}")
    if dst_dir.exists():
        parser.error(f"refusing to overwrite existing tree: {dst_dir}")

    # The archive is named by the RUNTIME version embedded in the release tag, which can
    # trail the product release (e.g. product v0.4.6 shipping runtime v0.4.5).
    runtime_version = args.release_tag.split("-", 1)[0]
    archive = args.archive_name or (
        f"ninfer-qwen38-rtx5090-{runtime_version}-linux-x86_64-cuda13.1.tar.gz"
    )
    download = f"https://github.com/alphastorm/ninfer/releases/download/{args.release_tag}"
    source_manifest = load(src_dir / "manifest.json")
    old_client_pins = (
        client_identity_pins(source_manifest["components"]["omp"],
                             load(src_dir / "compatibility.json"))
        if omp_descriptor is not None else set()
    )
    # The previous release may itself have kept an older profile (v0.6.4 shipped
    # qwen38-5090-v0.6.3): a kept profile is the one the source manifest records, not one
    # derived from the source release number.
    profile_from = (
        f"qwen38-5090-{args.profile_from}" if args.profile_from
        else source_manifest["runtime_identity"]["deployment_profile"]
    )
    profile_to = (
        profile_from if args.keep_deployment_profile else f"qwen38-5090-{args.release}"
    )
    config_sha = (
        source_manifest["runtime_identity"]["configuration_sha256"]
        if args.keep_deployment_profile else args.config_sha
    )

    # 1. Copy the tree.
    shutil.copytree(src_dir, dst_dir)

    # 2. Manifest component + identity pins.
    manifest_path = dst_dir / "manifest.json"
    manifest = load(manifest_path)
    manifest["release"] = args.release
    if omp_descriptor is not None:
        previous_omp = manifest["components"]["omp"]
        manifest["components"]["omp"] = {
            **{key: previous_omp[key] for key in (
                "compatibility_authority", "compatibility_url", "compatibility_sha256"
            ) if key in previous_omp},
            **omp_descriptor["omp"],
        }
    ninfer = manifest["components"]["ninfer"]
    old = {
        "digest": ninfer["oci_manifest_digest"],
        "binary": ninfer["server_binary_sha256"],
        "config": manifest["runtime_identity"]["configuration_sha256"],
    }
    ninfer.update({
        "release_tag": args.release_tag,
        "upstream_commit": args.upstream_commit or ninfer["upstream_commit"],
        "source_commit": args.source_commit,
        "source_archive_sha256": args.source_archive_sha,
        "server_binary_sha256": args.binary_sha,
        "binary_archive_url": f"{download}/{archive}",
        "binary_archive_sha256": args.archive_sha,
        "oci_reference": f"ghcr.io/alphastorm/ninfer-runtime@{args.image_digest}",
        "oci_manifest_digest": args.image_digest,
        "runtime_receipt_release": args.runtime_receipt_release,
        "sbom_url": f"{download}/{archive.removesuffix('.tar.gz')}.spdx.json",
        "sbom_sha256": args.sbom_sha,
        "source_archive_url": (
            f"https://github.com/alphastorm/ninfer/releases/download/"
            f"{args.source_tag}/runtime-source-{args.source_commit[:8]}.tar.gz"
        ),
    })
    manifest["runtime_identity"]["deployment_profile"] = profile_to
    manifest["runtime_identity"]["configuration_sha256"] = config_sha
    # A staged tree is a draft: the predecessor's acceptance does not carry, and the cut is
    # gated on a fresh composed acceptance against the published component.
    manifest["status"] = "draft"
    manifest["qualification"]["external_installation_passed"] = False
    manifest["publication"]["blockers"] = [
        f"external-installation acceptance has not been rerun against the published "
        f"{args.release_tag} component and runtime image {args.image_digest[7:15]}; the "
        "composed acceptance receipt is absent until it is",
    ]
    # 3. Release-relative evidence paths move with the tree; the commit part of every public
    #    URL is provisional until the pin dance.
    for variant in manifest["components"].get("ninfer_variants", []):
        qual = variant.get("qualification", {})
        for key in ("summary", "public_url"):
            if isinstance(qual.get(key), str):
                qual[key] = qual[key].replace(f"/{args.source}/", f"/{args.release}/")
    manifest_qualification = manifest["qualification"]
    if isinstance(manifest_qualification.get("public_url"), str):
        manifest_qualification["public_url"] = manifest_qualification["public_url"].replace(
            f"/releases/{args.source}/", f"/releases/{args.release}/"
        )
    dump(manifest_path, manifest)

    # 4. The release's compatibility copy: pins, paths, and the primary identities. Receipt
    #    hashes and native variant rows are derived by rebind_release.py from the manifest.
    compat_path = dst_dir / "compatibility.json"
    lane_path = dst_dir / "qualification" / "rtx5090.json"
    if args.lane_receipt is not None:
        shutil.copyfile(args.lane_receipt, lane_path)
    rewrite_text(compat_path, {
        old["digest"]: args.image_digest,
        old["binary"]: args.binary_sha,
        old["config"]: config_sha,
        profile_from: profile_to,
        f'"product_release": "{args.source}"': f'"product_release": "{args.release}"',
        f"releases/{args.source}/": f"releases/{args.release}/",
    })

    # 5. Qualification identity + packaging pins.
    if omp_descriptor is not None:
        compatibility = load(compat_path)
        bind_upstream_client(compatibility, omp_descriptor, args.release)
        dump(compat_path, compatibility)

    qual_path = dst_dir / "qualification.json"
    qualification = load(qual_path)
    qualification["release"] = args.release
    identity = qualification["runtime_identity"]
    identity.update({
        "upstream_commit": ninfer["upstream_commit"],
        "behavioral_source_commit": args.source_commit,
        "release_source_commit": args.source_commit,
        "release_source_archive_sha256": args.source_archive_sha,
        "release_server_binary_sha256": args.binary_sha,
        "configuration_sha256": config_sha,
        "deployment_profile": profile_to,
    })
    composition = qualification["composition"]
    behavioral = composition["behavioral_qualification"]
    behavioral["source_commit"] = args.source_commit
    behavioral["server_binary_sha256"] = args.binary_sha
    packaging = composition["local_release_packaging"]
    packaging.update({
        "release_source_commit": args.source_commit,
        "release_server_binary_sha256": args.binary_sha,
        "registry_reference": f"ghcr.io/alphastorm/ninfer-runtime@{args.image_digest}",
        "oci_manifest_digest": args.image_digest,
        "binary_package_sha256": args.archive_sha,
        "sbom_url": ninfer["sbom_url"],
        "sbom_sha256": args.sbom_sha,
        "component_release_url": (
            f"https://github.com/alphastorm/ninfer/releases/tag/{args.release_tag}"
        ),
    })
    qualification["external_installation_qualified"] = False
    composition["external_installation_acceptance"] = {
        "status": "pending",
        "note": (
            f"rerun against the published {args.release_tag} component (image "
            f"{args.image_digest[7:15]}) before the cut; the receipt lands at "
            f"releases/{args.release}/acceptance/composed-external-installation.json"
        ),
    }
    qualification["remaining_release_gates"] = [
        f"external-installation acceptance against the published {args.release_tag} "
        "component and runtime image"
    ]
    if omp_descriptor is not None:
        composition.pop("documented_route_acceptance", None)
        qualification["remaining_release_gates"].append(
            "fresh upstream OMP platform and documented-route acceptance"
        )
    dump(qual_path, qualification)
    shutil.rmtree(dst_dir / "acceptance", ignore_errors=True)

    # 6. Hash chain in dependency order, release tree only: the root authority and profiles
    #    stay on the previous release until the cut (staged-draft posture).
    subprocess.run(
        [sys.executable, "scripts/rebind_release.py", "--release", args.release, "--draft"],
        cwd=ROOT, check=True,
    )

    # 7. Report client pins for the lead, then verify the staged-draft contract.
    leftovers = client_pin_locations(dst_dir, old_client_pins) if omp_descriptor else []
    for location in leftovers:
        print(f"warning: releases/{args.release}/{location}", file=sys.stderr)
    draft_residue = set(DRAFT_POSTURE_RESIDUE)
    if omp_descriptor is not None:
        # As with runtime pins, root clients deliberately remain on the live release.
        draft_residue.add("profile: client archive must be the manifest's OMP component")
        draft_residue.update(
            f"profiles/{path.name}: client archive must be the manifest's OMP component"
            for path in (ROOT / "profiles").glob("*.json")
        )
    verify = subprocess.run(
        [sys.executable, "scripts/verify_release.py",
         "--release", args.release, "--json"],
        cwd=ROOT, capture_output=True, text=True,
    )
    report = json.loads(verify.stdout)
    errors = report.get("errors", [])
    if omp_descriptor is not None:
        # The lead rewrites copied notes after staging has removed client acceptance.
        # Only dangling links into this deliberately cleared directory are draft residue.
        for error in errors:
            document, separator, target = error.partition(" has missing local link: ")
            document_path = (ROOT / document).resolve()
            if separator and document_path.is_relative_to(dst_dir):
                target_path = (document_path.parent / target).resolve()
                if target_path.is_relative_to(dst_dir / "acceptance"):
                    draft_residue.add(error)
    for warning in report.get("warnings", []):
        if warning.removeprefix(f"releases/{args.release}/") not in leftovers:
            print(f"warning: {warning}", file=sys.stderr)
    allowlist_error = "components.ninfer.release_tag is invalid"
    unexpected = [
        error for error in errors
        if error not in PIN_RESIDUE and error not in draft_residue
        and error != allowlist_error
    ]
    print(f"staged releases/{args.release} from releases/{args.source}")
    for error in errors:
        if error in PIN_RESIDUE:
            marker = "pin-dance"
        elif error in draft_residue:
            marker = "draft-posture"
        elif error == allowlist_error:
            marker = "allowlist"
        else:
            marker = "UNEXPECTED"
        print(f"  [{marker}] {error}")
    if args.require_clean_client and (leftovers or report.get("warnings")):
        print("--require-clean-client: staged draft retains predecessor client pins", file=sys.stderr)
        return 1
    if unexpected:
        print("staging left unexpected verifier errors; fix before committing",
              file=sys.stderr)
        return 1
    print("remaining work, in order:")
    print("  1. [allowlist] add the new tag to NINFER_RELEASE_TAG_RE in "
          "scripts/verify_release.py (deliberate per-release act)")
    print("  2. author the release evidence by hand - lane-receipt arcs/gates, the composed "
          "acceptance receipt, CHANGELOG, RELEASES/BENCHMARKS/FACTS/README, and the "
          f"drift-test pins; rerun scripts/rebind_release.py --release {args.release} --draft "
          "after every edit and commit in the draft posture")
    print(f"  3. cut: scripts/rebind_release.py --release {args.release} --pin <commit that "
          "contains the final lane receipts> --stage lane promotes the root authority, "
          "profiles, and launcher pins, then commit")
    print(f"  4. scripts/rebind_release.py --release {args.release} --pin <commit> "
          "--stage acceptance | manifest (two more commits; the manifest stage runs the "
          "ready verifier with --check-pins)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
