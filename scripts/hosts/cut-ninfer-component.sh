#!/usr/bin/env bash
# Cut one exact-source NInfer component. Both kinds default to a no-effect preflight.
# Container: binary/source prereleases and a digest-addressed runtime-image workflow.
# Native: one prerelease carrying the packager's closed, qualified distribution set.
# Live --publish is FOUNDER-ONLY / AGENT MUST NOT EXECUTE.
#
# Usage:
#   cut-ninfer-component.sh --kind native [--lane rtx3090|rtx4090] \
#     --version vX.Y.Z --commit <sha40> --assets DIR \
#     --checksums-sha <sha256> --notes-file FILE [--beta 1] [--publish]
#   cut-ninfer-component.sh --kind container [--lane rtx5090] \
#     --version vX.Y.Z --commit <sha40> --assets DIR --archive-sha <sha256> \
#     --sbom-sha <sha256> --source-archive-sha <sha256> \
#     --base-image ghcr.io/alphastorm/ninfer@sha256:<64hex> \
#     --runtime-base-receipt-release runtime-base-<sha8>-<yyyymmdd> [--dry-run]
# --publish is required for either kind; --dry-run and --publish are mutually exclusive.
# RTX 3090 defaults --assets to C:/b/ninfer-rtx3090-<head8>/package-a.
set -euo pipefail

REPO=alphastorm/ninfer
RUNTIME_REPO_DIR="${NINFER_RUNTIME_DIR:-$HOME/Development/ninfer-lane-5090}"
kind=""; LANE=""; version=""; commit=""; assets=""; checksums_sha=""; notes_file=""; beta=1; publish=0; dry_run=0
archive_sha=""; sbom_sha=""; source_sha=""; base_image=""; runtime_base_receipt_release=""
while (($#)); do
  case "$1" in
    --kind|--lane|--version|--commit|--assets|--checksums-sha|--notes-file|--beta|--archive-sha|--sbom-sha|--source-archive-sha|--base-image|--runtime-base-receipt-release)
      (($# >= 2)) || { echo "$1 requires a value" >&2; exit 2; } ;;
  esac
  case "$1" in
    --kind) kind="$2"; shift 2 ;;
    --lane) LANE="$2"; shift 2 ;;
    --version) version="$2"; shift 2 ;;
    --commit) commit="$2"; shift 2 ;;
    --assets) assets="$2"; shift 2 ;;
    --checksums-sha) checksums_sha="$2"; shift 2 ;;
    --notes-file) notes_file="$2"; shift 2 ;;
    --beta) beta="$2"; shift 2 ;;
    --archive-sha) archive_sha="$2"; shift 2 ;;
    --sbom-sha) sbom_sha="$2"; shift 2 ;;
    --source-archive-sha) source_sha="$2"; shift 2 ;;
    --base-image) base_image="$2"; shift 2 ;;
    --runtime-base-receipt-release) runtime_base_receipt_release="$2"; shift 2 ;;
    --publish) publish=1; shift ;;
    --dry-run) dry_run=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
((publish && dry_run)) && { echo "choose --dry-run or --publish, not both" >&2; exit 2; }
[[ $kind == container || $kind == native ]] || { echo "--kind must be container or native" >&2; exit 2; }
if [[ $kind == container ]]; then
  LANE="${LANE:-rtx5090}"
  [[ $LANE == rtx5090 ]] || { echo "--lane must be rtx5090 for --kind container" >&2; exit 2; }
  [[ -z $checksums_sha ]] || { echo "--checksums-sha is native-only" >&2; exit 2; }
else
  LANE="${LANE:-rtx4090}"
  [[ $LANE == rtx3090 || $LANE == rtx4090 ]] || { echo "--lane must be rtx3090 or rtx4090 for --kind native" >&2; exit 2; }
  [[ -z $archive_sha$sbom_sha$source_sha$base_image$runtime_base_receipt_release ]] || { echo "container-only arguments passed for --kind native" >&2; exit 2; }
fi
[[ $version =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "--version must be vX.Y.Z" >&2; exit 2; }
[[ $commit =~ ^[0-9a-f]{40}$ ]] || { echo "--commit must be a full lowercase sha" >&2; exit 2; }
[[ $beta =~ ^[1-9][0-9]*$ ]] || { echo "--beta must be a positive integer" >&2; exit 2; }
if [[ $LANE == rtx3090 && -z $assets ]]; then assets="C:/b/ninfer-rtx3090-${commit:0:8}/package-a"; fi
[[ -d $assets ]] || { echo "--assets must be a directory" >&2; exit 2; }
sha() { shasum -a 256 "$1" | cut -d' ' -f1; }

if [[ $kind == container ]]; then
  [[ $archive_sha =~ ^[0-9a-f]{64}$ && $sbom_sha =~ ^[0-9a-f]{64}$ && $source_sha =~ ^[0-9a-f]{64}$ ]] || { echo "every --*-sha must be a sha256 hex" >&2; exit 2; }
  [[ $base_image =~ ^ghcr\.io/alphastorm/ninfer@sha256:[0-9a-f]{64}$ ]] || { echo "--base-image must be ghcr.io/alphastorm/ninfer@sha256:<64hex>" >&2; exit 2; }
  [[ $runtime_base_receipt_release =~ ^runtime-base-[0-9a-f]{8}-[0-9]{8}$ ]] || { echo "--runtime-base-receipt-release must be runtime-base-<sha8>-<yyyymmdd>" >&2; exit 2; }
  [[ -z $notes_file || -f $notes_file ]] || { echo "--notes-file missing" >&2; exit 2; }
  archive="ninfer-qwen38-rtx5090-$version-linux-x86_64-cuda13.1.tar.gz"
  sbom="ninfer-qwen38-rtx5090-$version-linux-x86_64-cuda13.1.spdx.json"
  sums="ninfer-qwen38-rtx5090-$version-linux-x86_64-cuda13.1.SHA256SUMS"
  source_archive="runtime-source-${commit:0:8}.tar.gz"
  binary_tag="$version-qwen38-5090-beta.$beta"
  source_tag="$version-qwen38-5090-source.$beta"
  for asset in "$archive" "$sbom" "$sums" "$source_archive"; do
    [[ -f $assets/$asset ]] || { echo "missing asset: $assets/$asset" >&2; exit 1; }
  done
  [[ $(sha "$assets/$archive") == "$archive_sha" ]] || { echo "archive sha256 does not match --archive-sha" >&2; exit 1; }
  [[ $(sha "$assets/$sbom") == "$sbom_sha" ]] || { echo "sbom sha256 does not match --sbom-sha" >&2; exit 1; }
  [[ $(sha "$assets/$source_archive") == "$source_sha" ]] || { echo "source archive sha256 does not match --source-archive-sha" >&2; exit 1; }
  (cd "$assets" && shasum -a 256 -c "$sums" >/dev/null) || { echo "SHA256SUMS does not verify" >&2; exit 1; }
  [[ $(git -C "$RUNTIME_REPO_DIR" archive --format=tar.gz "$commit" | shasum -a 256 | cut -d' ' -f1) == "$source_sha" ]] \
    || { echo "source archive is not git archive of $commit" >&2; exit 1; }
  identity="$(tar xzf "$assets/$archive" -O "${archive%.tar.gz}/build-identity.json")"
  [[ $(printf '%s' "$identity" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["patch_stack_sha"], d["release_version"], d["source_dirty"])') == "$commit $version False" ]] \
    || { echo "build-identity.json disagrees with --commit/--version or is dirty" >&2; exit 1; }
  git -C "$RUNTIME_REPO_DIR" cat-file -e "$commit^{commit}" || { echo "commit not in $RUNTIME_REPO_DIR" >&2; exit 1; }
  git -C "$RUNTIME_REPO_DIR" branch -r --contains "$commit" | grep -q 'origin/' || { echo "commit is not on any origin branch" >&2; exit 1; }
  git -C "$RUNTIME_REPO_DIR" cat-file -e "$commit:.github/workflows/publish-runtime-image.yml" || { echo "workflow file absent at commit" >&2; exit 1; }
  gh auth status >/dev/null 2>&1 || { echo "gh is not authenticated" >&2; exit 1; }
  for tag in "$binary_tag" "$source_tag"; do
    if gh api "repos/$REPO/git/ref/tags/$tag" >/dev/null 2>&1; then echo "tag already exists: $tag" >&2; exit 1; fi
    if gh release view "$tag" --repo "$REPO" >/dev/null 2>&1; then echo "release already exists: $tag" >&2; exit 1; fi
  done
  echo "preflight ok: $binary_tag and $source_tag at $commit; archive $archive_sha; base $base_image; base receipt $runtime_base_receipt_release"
  if ((!publish)); then
    echo "dry run: no tag, release, or workflow run was created"
    exit 0
  fi
  git -C "$RUNTIME_REPO_DIR" push origin "$commit:refs/tags/$binary_tag" "$commit:refs/tags/$source_tag"
  notes_args=()
  if [[ -n $notes_file ]]; then notes_args=(--notes-file "$notes_file"); else notes_args=(--notes "Exact RTX 5090 runtime binaries for $version from source $commit."); fi
  gh release create "$binary_tag" --repo "$REPO" --target "$commit" --prerelease \
    --title "NInfer RTX 5090 durable runtime binaries ($version)" "${notes_args[@]}" \
    "$assets/$archive" "$assets/$sbom" "$assets/$sums"
  gh release create "$source_tag" --repo "$REPO" --target "$commit" --prerelease \
    --title "NInfer RTX 5090 durable runtime source ($version)" \
    --notes "Exact source archive for the $version runtime binaries (${commit:0:8})." "$assets/$source_archive"
  gh workflow run publish-runtime-image.yml --repo "$REPO" --ref "$binary_tag" \
    -f "source_commit=$commit" -f "release_tag=$binary_tag" -f "binary_asset=$archive" -f "binary_sha256=$archive_sha" \
    -f "base_image=$base_image" -f "runtime_base_receipt_release=$runtime_base_receipt_release"
  echo "published $binary_tag and $source_tag; runtime-image workflow dispatched"
  echo "next: wait for the workflow, then read image_digest from the $version-qwen38-5090-runtime-beta.$beta receipt and run scripts/stage_release.py"
  exit 0
fi

[[ $checksums_sha =~ ^[0-9a-f]{64}$ ]] || { echo "--checksums-sha must be a sha256 hex" >&2; exit 2; }
[[ -f $notes_file ]] || { echo "--notes-file must name the release notes" >&2; exit 2; }
git -C "$RUNTIME_REPO_DIR" cat-file -e "$commit^{commit}" || { echo "commit not in $RUNTIME_REPO_DIR" >&2; exit 1; }
[[ $(sha "$assets/SHA256SUMS") == "$checksums_sha" ]] \
  || { echo "SHA256SUMS does not match --checksums-sha" >&2; exit 1; }

spec_json=$(git -C "$RUNTIME_REPO_DIR" show "$commit:packaging/windows/lanes/$LANE/release-spec.json")
python3 - "$assets" "$version" "$beta" "$commit" "$RUNTIME_REPO_DIR" "$spec_json" "$LANE" <<'PY'
import hashlib, json, pathlib, subprocess, sys, tarfile
root, version, beta, commit, runtime, spec_text, lane = sys.argv[1:]
root = pathlib.Path(root)
spec = json.loads(spec_text)
if (spec["lane"] != lane or spec["product_prefix"] != f"ninfer-{lane}-native"
        or spec["platform"] != f"windows-x86_64-cuda13.3-{lane}"):
    raise SystemExit("lane specification disagrees with --lane")
release_version = f"{version[1:]}-beta.{beta}"
if spec["release_version"] != release_version:
    raise SystemExit(f"lane specification names {spec['release_version']}, not {release_version}")
stem = f"{spec['product_prefix']}-v{release_version}"
package = f"{stem}-{spec['platform']}.tar.gz"
inner_sums = f"{stem}-{spec['platform']}.SHA256SUMS"
sbom = f"{stem}-{spec['platform']}.spdx.json"
dependency_sbom = f"{stem}-{spec['platform']}.cdx.json"
source = f"{stem}-source.tar.gz"
support = ["Install-Release.ps1", "Control-Release.ps1", "Control-GpuOwner.ps1", "Protect-StateRoot.ps1"]
listed = set(support) | {package, inner_sums, sbom, dependency_sbom, source, "package-build-receipt.json"}

raw = (root / "SHA256SUMS").read_bytes()
if b"\r" in raw or not raw.endswith(b"\n"):
    raise SystemExit("SHA256SUMS must use LF line endings")
entries = {}
for line in raw.decode().splitlines():
    digest, name = line.split("  ", 1)
    if name in entries or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise SystemExit("malformed SHA256SUMS")
    entries[name] = digest
if set(entries) != listed or {p.name for p in root.iterdir()} != listed | {"SHA256SUMS"}:
    raise SystemExit("asset directory is not the exact closed distribution set")
for name, expected in entries.items():
    with (root / name).open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
            raise SystemExit(f"checksum mismatch: {name}")

receipt = json.loads((root / "package-build-receipt.json").read_text())
for key in ("release_id", "release_version", "deployment_profile", "build_profile"):
    if receipt.get(key) != spec.get(key):
        raise SystemExit(f"package receipt {key} disagrees with the lane specification")
for key in ("patch_stack_sha", "runtime_source_sha", "package_source_sha"):
    if receipt.get(key) != commit:
        raise SystemExit(f"package receipt {key} is not {commit}")
if receipt.get("lane") != spec["lane"] or receipt.get("secret_values_recorded") != 0:
    raise SystemExit("package receipt lane or secret accounting is wrong")
if receipt["package"] != {"filename": package, "sha256": entries[package],
                          "bytes": (root / package).stat().st_size}:
    raise SystemExit("package receipt does not name the package bytes")
if receipt["checksums"].get("entries") != len(entries):
    raise SystemExit("package receipt counts a different outer checksum set")
dependency = receipt.get("dependency_sbom", {})
if (dependency.get("name") != dependency_sbom
        or dependency.get("sha256") != entries[dependency_sbom]
        or dependency.get("format") != "CycloneDX-1.5"):
    raise SystemExit("package receipt does not bind the dependency CycloneDX SBOM")
inventory = json.loads((root / dependency_sbom).read_text())
if inventory.get("bomFormat") != "CycloneDX" or inventory.get("specVersion") != "1.5":
    raise SystemExit("dependency SBOM must be CycloneDX 1.5, not the package SPDX")
component = inventory.get("metadata", {}).get("component", {})
if (component.get("version") != commit
        or {"alg": "SHA-256", "content": receipt["binaries"]["server_sha256"]}
        not in component.get("hashes", [])):
    raise SystemExit("dependency SBOM does not bind this source and server binary")
support_keys = {"Install-Release.ps1": "installer_sha256", "Control-Release.ps1": "controller_sha256",
                "Control-GpuOwner.ps1": "gpu_owner_controller_sha256",
                "Protect-StateRoot.ps1": "state_protection_sha256"}
for name, key in support_keys.items():
    if receipt["support_assets"].get(key) != entries[name]:
        raise SystemExit(f"package receipt does not name {name}")
inner = {}
for line in (root / inner_sums).read_text().splitlines():
    digest, name = line.split("  ", 1)
    inner[name] = digest
if inner != {package: entries[package], source: entries[source], sbom: entries[sbom]}:
    raise SystemExit("inner package checksums disagree with the outer set")

# The gzip layer is the packager's, but the tar stream is `git archive` of the commit: compare it
# byte for byte with this checkout's archive of the same commit under the same prefix.
with tarfile.open(root / source, "r:gz") as archive:
    first = archive.next()
    prefix = first.name.split("/", 1)[0] if first else ""
import gzip
with gzip.open(root / source, "rb") as stream:
    published_tar = stream.read()
expected_tar = subprocess.run(
    ["git", "-C", runtime, "-c", "core.autocrlf=false", "-c", "core.eol=lf", "archive",
     "--format=tar", f"--prefix={prefix}/", commit], check=True, capture_output=True).stdout
if not prefix or published_tar != expected_tar:
    raise SystemExit("source archive is not the exact tree of the commit")
print(f"assets verified: {package} {entries[package]}; source {prefix}/ is {commit}")
PY

gpu="${LANE#rtx}"
tag="$version-qwen38-$gpu-beta.$beta"
git -C "$RUNTIME_REPO_DIR" branch -r --contains "$commit" | grep -q 'origin/' || { echo "commit is not on any origin branch" >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh is not authenticated" >&2; exit 1; }
[[ $(gh api "repos/$REPO" --jq .permissions.push) == true ]] || { echo "release write permission is unavailable: $REPO" >&2; exit 1; }
[[ -z $(git ls-remote --tags "https://github.com/$REPO.git" "refs/tags/$tag") ]] || { echo "tag already exists: $tag" >&2; exit 1; }
if gh release view "$tag" --repo "$REPO" >/dev/null 2>&1; then echo "release already exists: $tag" >&2; exit 1; fi
git -C "$RUNTIME_REPO_DIR" push --dry-run origin "$commit:refs/tags/$tag" >/dev/null 2>&1 || { echo "tag push would be refused" >&2; exit 1; }
echo "preflight ok: $tag at $commit"
if ((!publish)); then
  echo "dry run: no tag, release, or upload was created"
  exit 0
fi

git -C "$RUNTIME_REPO_DIR" push origin "$commit:refs/tags/$tag"
gh release create "$tag" --repo "$REPO" --verify-tag --prerelease --latest=false \
  --title "NInfer RTX $gpu native durable-session runtime ($version)" --notes-file "$notes_file" \
  "$assets"/*
echo "published $tag; bind it with scripts/bind_native_variant.py"
