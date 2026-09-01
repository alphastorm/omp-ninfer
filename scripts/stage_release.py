#!/usr/bin/env python3
"""Stage a new release tree from the previous one with a consistent hash chain.

Mechanizes the identity/hash plumbing that was executed by hand for v0.4.3 and
v0.4.4 (class closure: second manual run of the same sequence). It does NOT
author evidence: lane-receipt arcs, qualification gate numbers, CHANGELOG, and
doc prose remain the lead's job. What it owns:

  1. Copy releases/<from> -> releases/<release>.
  2. Rewrite the NInfer component pins in manifest.json (release tag, source
     commit, archive/binary/SBOM hashes, OCI digest, runtime receipt release,
     download URLs) and the runtime-identity deployment profile.
  3. Rewrite <from> -> <release> internal paths (variant qualification
     summaries, compatibility receipt paths, profile files).
  4. Rebase compatibility.json (product_release, 5090 profile string, image
     digest and server-binary replacements, lane-receipt hash) and mirror it
     byte-identical to the repository root.
  5. Rebase qualification.json identity and local-release-packaging pins.
  6. Recompute the hash chain in dependency order:
     lane receipt -> behavioral/qualification bindings -> acceptance
     compatibility binding -> acceptance hash -> qualification hash ->
     manifest summary hash.
  7. Render both COMPATIBILITY.md files and run the release verifier.

Exit: verifier's error list printed; success when the only residue is the
commit-bound public-URL set, which the existing two-stage
`rebind_release.py --stage acceptance|manifest` dance resolves after commit.
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

# The four errors the URL-pin dance (rebind_release.py) resolves after commit;
# everything else is a staging defect this script must not leave behind.
PIN_RESIDUE = {
    "components.ninfer_variants.rtx3090-windows-native.qualification.public_url must bind an immutable product commit and path",
    "components.ninfer_variants.rtx4090-windows-native.qualification.public_url must bind an immutable product commit and path",
    "external acceptance public_url must bind an immutable product commit and path",
    "qualification.public_url must bind an immutable product commit and path",
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
    args = parser.parse_args()

    if not args.image_digest.startswith("sha256:"):
        parser.error("--image-digest must start with sha256:")
    for name in ("binary_sha", "archive_sha", "source_archive_sha", "sbom_sha"):
        value = getattr(args, name)
        if len(value) != 64:
            parser.error(f"--{name.replace('_', '-')} must be a 64-hex sha256")

    src_dir = ROOT / "releases" / args.source
    dst_dir = ROOT / "releases" / args.release
    if not src_dir.is_dir():
        parser.error(f"missing source release tree: {src_dir}")
    if dst_dir.exists():
        parser.error(f"refusing to overwrite existing tree: {dst_dir}")

    archive = args.archive_name or (
        f"ninfer-qwen38-rtx5090-{args.release}-linux-x86_64-cuda13.1.tar.gz"
    )
    download = f"https://github.com/alphastorm/ninfer/releases/download/{args.release_tag}"
    profile_from = (
        f"qwen38-5090-{args.profile_from}" if args.profile_from
        else f"qwen38-5090-{args.source}"
    )
    profile_to = (
        profile_from if args.keep_deployment_profile else f"qwen38-5090-{args.release}"
    )

    # 1. Copy the tree.
    shutil.copytree(src_dir, dst_dir)

    # 2. Manifest component + identity pins.
    manifest_path = dst_dir / "manifest.json"
    manifest = load(manifest_path)
    manifest["release"] = args.release
    ninfer = manifest["components"]["ninfer"]
    old = {
        "digest": ninfer["oci_manifest_digest"],
        "binary": ninfer["server_binary_sha256"],
    }
    ninfer.update({
        "release_tag": args.release_tag,
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
    # 3. Variant summaries stay inside the new release.
    for variant in manifest["components"].get("ninfer_variants", []):
        qual = variant.get("qualification", {})
        for key in ("summary", "public_url"):
            if isinstance(qual.get(key), str):
                qual[key] = qual[key].replace(f"/{args.source}/", f"/{args.release}/")
    dump(manifest_path, manifest)

    # Profiles reference the release and deployment profile by value.
    for profile_file in (ROOT / "profiles").glob("*.json"):
        rewrite_text(profile_file, {
            f'"{args.source}"': f'"{args.release}"',
            profile_from: profile_to,
        })

    # 4. Compatibility authority: pins, paths, and the lane-receipt hash.
    compat_path = dst_dir / "compatibility.json"
    lane_path = dst_dir / "qualification" / "rtx5090.json"
    rewrite_text(compat_path, {
        old["digest"]: args.image_digest,
        old["binary"]: args.binary_sha,
        profile_from: profile_to,
        f'"product_release": "{args.source}"': f'"product_release": "{args.release}"',
        f"releases/{args.source}/": f"releases/{args.release}/",
    })
    compat = load(compat_path)
    lane_sha = sha256_file(lane_path)
    for profile in compat.get("profiles", []):
        gpu = profile.get("gpu_qualification")
        if gpu and gpu.get("profile", "").startswith("qwen38-5090"):
            gpu["receipt"]["sha256"] = lane_sha
    for variant in compat.get("runtime_variants", []):
        receipt = variant.get("qualification_receipt", {})
        if isinstance(receipt.get("path"), str):
            receipt["sha256"] = sha256_file(ROOT / receipt["path"])
    dump(compat_path, compat)

    # 5. Qualification identity + packaging pins.
    qual_path = dst_dir / "qualification.json"
    qualification = load(qual_path)
    qualification["release"] = args.release
    identity = qualification["runtime_identity"]
    identity["release_source_commit"] = args.source_commit
    identity["release_server_binary_sha256"] = args.binary_sha
    identity["deployment_profile"] = profile_to
    composition = qualification["composition"]
    behavioral = composition["behavioral_qualification"]
    behavioral["repository_path"] = f"releases/{args.release}/qualification/rtx5090.json"
    behavioral["sha256"] = lane_sha
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
    })
    acceptance = composition["external_installation_acceptance"]
    acceptance["repository_path"] = (
        f"releases/{args.release}/acceptance/composed-external-installation.json"
    )
    dump(qual_path, qualification)

    # 6. Hash chain in dependency order.
    root_compat = ROOT / "compatibility.json"
    shutil.copyfile(compat_path, root_compat)
    compat_sha = sha256_file(root_compat)

    acceptance_path = dst_dir / "acceptance" / "composed-external-installation.json"
    receipt = load(acceptance_path)
    receipt["release"] = args.release
    receipt["compatibility_sha256"] = compat_sha
    dump(acceptance_path, receipt)

    qualification = load(qual_path)
    acceptance = qualification["composition"]["external_installation_acceptance"]
    acceptance["sha256"] = sha256_file(acceptance_path)
    acceptance["compatibility_sha256"] = compat_sha
    dump(qual_path, qualification)

    manifest = load(manifest_path)
    manifest["components"]["omp"]["compatibility_sha256"] = compat_sha
    manifest["qualification"]["summary_sha256"] = sha256_file(qual_path)
    dump(manifest_path, manifest)

    # 7. Render and verify.
    for authority, output in (
        ("compatibility.json", "docs/COMPATIBILITY.md"),
        (f"releases/{args.release}/compatibility.json",
         f"releases/{args.release}/COMPATIBILITY.md"),
    ):
        subprocess.run(
            [sys.executable, "scripts/render_compatibility.py",
             "--authority", authority, "--output", output],
            cwd=ROOT, check=True,
        )
    verify = subprocess.run(
        [sys.executable, "scripts/verify_release.py",
         "--release", args.release, "--json"],
        cwd=ROOT, capture_output=True, text=True,
    )
    report = json.loads(verify.stdout)
    errors = report.get("errors", [])
    allowlist_error = "components.ninfer.release_tag is invalid"
    unexpected = [
        error for error in errors
        if error not in PIN_RESIDUE and error != allowlist_error
    ]
    print(f"staged releases/{args.release} from releases/{args.source}")
    for error in errors:
        if error in PIN_RESIDUE:
            marker = "pin-dance"
        elif error == allowlist_error:
            marker = "allowlist"
        else:
            marker = "UNEXPECTED"
        print(f"  [{marker}] {error}")
    if unexpected:
        print("staging left unexpected verifier errors; fix before committing",
              file=sys.stderr)
        return 1
    print("remaining work, in order:")
    print("  1. [allowlist] add the new tag to NINFER_RELEASE_TAG_RE in "
          "scripts/verify_release.py (deliberate per-release act)")
    print("  2. author the release evidence by hand - lane-receipt arcs/gates, "
          "CHANGELOG, RELEASES/BENCHMARKS/FACTS/README, tunnel scripts, and "
          "the drift-test pins")
    print(f"  3. commit, then scripts/rebind_release.py --release {args.release} "
          "--pin <commit> --stage acceptance | manifest (two commits)")
    print("  4. re-pin variant qualification public_urls to the final commit "
          "(they keep the prior commit hash until then)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
