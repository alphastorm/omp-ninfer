#!/usr/bin/env bash
# Publish one RTX 5090 NInfer runtime component: the binary prerelease, the exact source
# archive prerelease, and the runtime-image workflow run that wraps the published binary into
# a digest-addressed image. Every input is an exact identity; the script refuses to run unless
# the local assets hash to what the caller declares and neither tag exists yet.
#
# Publication authority: the product owner authorizes who runs this; the v0.13.0 program delegated the
# component cuts to the release lead after a --dry-run, while the omp-ninfer product tag and GitHub
# release remain FOUNDER-ONLY. The --dry-run proves every identity without creating anything public.
#
# Usage:
#   cut-ninfer-5090-component.sh --version v0.5.1 --commit <sha40> \
#     --assets ~/Desktop/ninfer-v0.5.1-release --archive-sha <sha256> --sbom-sha <sha256> \
#     --source-archive-sha <sha256> --base-image ghcr.io/alphastorm/ninfer@sha256:<64hex> \
#     --runtime-base-receipt-release runtime-base-<sha8>-<yyyymmdd> \
#     [--beta 1] [--notes-file FILE] [--dry-run]
#
# --base-image is the image_reference from a publish-runtime-base.yml prerelease receipt
# named by --runtime-base-receipt-release: the digest-pinned master-compatible runtime dependency
# layer the runtime-image workflow wraps the published binaries onto. That workflow checks the
# receipt binding only after both prereleases exist, so the preflight (and --dry-run) proves the
# same binding before any public effect: the receipt release is a published prerelease at its
# receipt's source, the receipt names that release and --base-image, and that source commit is
# an ancestor of --commit in $NINFER_RUNTIME_DIR.
set -euo pipefail

REPO=alphastorm/ninfer
RUNTIME_REPO_DIR="${NINFER_RUNTIME_DIR:-$HOME/Development/ninfer-lane-5090}"
version=""; commit=""; assets=""; archive_sha=""; sbom_sha=""; source_sha=""; base_image=""; runtime_base_receipt_release=""; beta=1; notes_file=""; dry_run=0
while [ $# -gt 0 ]; do
  case "$1" in
    --version|--commit|--assets|--archive-sha|--sbom-sha|--source-archive-sha|--base-image|--runtime-base-receipt-release|--beta|--notes-file)
      (($# >= 2)) || { echo "$1 requires a value" >&2; exit 2; } ;;
  esac
  case "$1" in
    --version) version="$2"; shift 2 ;;
    --commit) commit="$2"; shift 2 ;;
    --assets) assets="$2"; shift 2 ;;
    --archive-sha) archive_sha="$2"; shift 2 ;;
    --sbom-sha) sbom_sha="$2"; shift 2 ;;
    --source-archive-sha) source_sha="$2"; shift 2 ;;
    --base-image) base_image="$2"; shift 2 ;;
    --runtime-base-receipt-release) runtime_base_receipt_release="$2"; shift 2 ;;
    --beta) beta="$2"; shift 2 ;;
    --notes-file) notes_file="$2"; shift 2 ;;
    --dry-run) dry_run=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[[ "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "--version must be vX.Y.Z" >&2; exit 2; }
[[ "$commit" =~ ^[0-9a-f]{40}$ ]] || { echo "--commit must be a full lowercase sha" >&2; exit 2; }
[[ "$archive_sha" =~ ^[0-9a-f]{64}$ && "$sbom_sha" =~ ^[0-9a-f]{64}$ && "$source_sha" =~ ^[0-9a-f]{64}$ ]] || { echo "every --*-sha must be a sha256 hex" >&2; exit 2; }
[[ "$base_image" =~ ^ghcr\.io/alphastorm/ninfer@sha256:[0-9a-f]{64}$ ]] || { echo "--base-image must be ghcr.io/alphastorm/ninfer@sha256:<64hex>" >&2; exit 2; }
[[ "$runtime_base_receipt_release" =~ ^runtime-base-[0-9a-f]{8}-[0-9]{8}$ ]] || { echo "--runtime-base-receipt-release must be runtime-base-<sha8>-<yyyymmdd>" >&2; exit 2; }
[[ "$beta" =~ ^[1-9][0-9]*$ ]] || { echo "--beta must be a positive integer" >&2; exit 2; }
[ -d "$assets" ] || { echo "--assets must be a directory" >&2; exit 2; }
[ -z "$notes_file" ] || [ -f "$notes_file" ] || { echo "--notes-file missing" >&2; exit 2; }

archive="ninfer-qwen38-rtx5090-$version-linux-x86_64-cuda13.1.tar.gz"
sbom="ninfer-qwen38-rtx5090-$version-linux-x86_64-cuda13.1.spdx.json"
sums="ninfer-qwen38-rtx5090-$version-linux-x86_64-cuda13.1.SHA256SUMS"
source_archive="runtime-source-${commit:0:8}.tar.gz"
binary_tag="$version-qwen38-5090-beta.$beta"
source_tag="$version-qwen38-5090-source.$beta"

sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
for asset in "$archive" "$sbom" "$sums" "$source_archive"; do
  [ -f "$assets/$asset" ] || { echo "missing asset: $assets/$asset" >&2; exit 1; }
done
[ "$(sha "$assets/$archive")" = "$archive_sha" ] || { echo "archive sha256 does not match --archive-sha" >&2; exit 1; }
[ "$(sha "$assets/$sbom")" = "$sbom_sha" ] || { echo "sbom sha256 does not match --sbom-sha" >&2; exit 1; }
[ "$(sha "$assets/$source_archive")" = "$source_sha" ] || { echo "source archive sha256 does not match --source-archive-sha" >&2; exit 1; }
(cd "$assets" && shasum -a 256 -c "$sums" >/dev/null) || { echo "SHA256SUMS does not verify" >&2; exit 1; }
# The source archive must be the exact tree of the commit: git archive is deterministic.
[ "$(git -C "$RUNTIME_REPO_DIR" archive --format=tar.gz "$commit" | shasum -a 256 | cut -d' ' -f1)" = "$source_sha" ] \
  || { echo "source archive is not git archive of $commit" >&2; exit 1; }
# The binary archive's identity must name the same commit and version, clean.
identity="$(tar xzf "$assets/$archive" -O "${archive%.tar.gz}/build-identity.json")"
[ "$(printf '%s' "$identity" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["patch_stack_sha"], d["release_version"], d["source_dirty"])')" = "$commit $version False" ] \
  || { echo "build-identity.json disagrees with --commit/--version or is dirty" >&2; exit 1; }
git -C "$RUNTIME_REPO_DIR" cat-file -e "$commit^{commit}" || { echo "commit not in $RUNTIME_REPO_DIR" >&2; exit 1; }
git -C "$RUNTIME_REPO_DIR" branch -r --contains "$commit" | grep -q 'origin/' || { echo "commit is not on any origin branch" >&2; exit 1; }
git -C "$RUNTIME_REPO_DIR" cat-file -e "$commit:.github/workflows/publish-runtime-image.yml" || { echo "workflow file absent at commit" >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh is not authenticated" >&2; exit 1; }
for tag in "$binary_tag" "$source_tag"; do
  if gh api "repos/$REPO/git/ref/tags/$tag" >/dev/null 2>&1; then echo "tag already exists: $tag" >&2; exit 1; fi
  if gh release view "$tag" --repo "$REPO" >/dev/null 2>&1; then echo "release already exists: $tag" >&2; exit 1; fi
done
base_release_json=$(gh release view "$runtime_base_receipt_release" --repo "$REPO" \
  --json tagName,isPrerelease,isDraft,targetCommitish) \
  || { echo "runtime base receipt release is unavailable: $runtime_base_receipt_release" >&2; exit 1; }
base_receipt_json=$(gh release download "$runtime_base_receipt_release" --repo "$REPO" \
  --pattern ninfer-runtime-base.json --output -) \
  || { echo "$runtime_base_receipt_release carries no ninfer-runtime-base.json" >&2; exit 1; }
python3 - "$base_release_json" "$base_receipt_json" "$runtime_base_receipt_release" "$base_image" \
  "$commit" "$RUNTIME_REPO_DIR" <<'PY'
import json, re, subprocess, sys
view, receipt, release, base_image, commit, runtime = sys.argv[1:]
try:
    view, receipt = json.loads(view), json.loads(receipt)
except ValueError:
    raise SystemExit(f"{release} release metadata or receipt is not JSON")
if not isinstance(view, dict) or not isinstance(receipt, dict):
    raise SystemExit(f"{release} release metadata or receipt is not a JSON object")
if view.get("tagName") != release or view.get("isPrerelease") is not True or view.get("isDraft") is not False:
    raise SystemExit(f"{release} is not a published runtime base prerelease")
for key, value in (("artifact_type", "ninfer_runtime_base_publication_receipt"), ("schema_version", 1),
                   ("runtime_base_release_tag", release), ("platform", "linux/amd64"),
                   ("build_target", "runtime-base")):
    if type(receipt.get(key)) is not type(value) or receipt.get(key) != value:
        raise SystemExit(f"{release} receipt {key} is not {value}")
if receipt.get("image_reference") != base_image:
    raise SystemExit(f"{release} receipt binds {receipt.get('image_reference')}, not --base-image {base_image}")
source = receipt.get("source_commit")
if not isinstance(source, str) or re.fullmatch(r"[0-9a-f]{40}", source) is None:
    raise SystemExit(f"{release} receipt source_commit is not a full commit")
if not release.startswith(f"runtime-base-{source[:8]}-") or view.get("targetCommitish") != source:
    raise SystemExit(f"{release} release name or target does not match receipt source {source}")
def git(*args):
    return subprocess.run(["git", "-C", runtime, *args], capture_output=True).returncode
if git("cat-file", "-e", f"{source}^{{commit}}"):
    raise SystemExit(f"runtime base source {source} is not in {runtime}")
if git("merge-base", "--is-ancestor", source, commit):
    raise SystemExit(f"runtime base source {source} is not an ancestor of {commit}")
print(f"runtime base verified: {release} binds {base_image}; source {source} is an ancestor of {commit}")
PY
echo "preflight ok: $binary_tag and $source_tag at $commit; archive $archive_sha; base $base_image; base receipt $runtime_base_receipt_release"
if [ "$dry_run" = 1 ]; then
  echo "dry run: no tag, release, or workflow run was created"
  exit 0
fi

git -C "$RUNTIME_REPO_DIR" push origin "$commit:refs/tags/$binary_tag" "$commit:refs/tags/$source_tag"
notes_args=()
if [ -n "$notes_file" ]; then notes_args=(--notes-file "$notes_file"); else notes_args=(--notes "Exact RTX 5090 runtime binaries for $version from source $commit."); fi
gh release create "$binary_tag" --repo "$REPO" --target "$commit" --prerelease \
  --title "NInfer RTX 5090 durable runtime binaries ($version)" "${notes_args[@]}" \
  "$assets/$archive" "$assets/$sbom" "$assets/$sums"
gh release create "$source_tag" --repo "$REPO" --target "$commit" --prerelease \
  --title "NInfer RTX 5090 durable runtime source ($version)" \
  --notes "Exact source archive for the $version runtime binaries (${commit:0:8})." \
  "$assets/$source_archive"
gh workflow run publish-runtime-image.yml --repo "$REPO" --ref "$binary_tag" \
  -f "source_commit=$commit" -f "release_tag=$binary_tag" -f "binary_asset=$archive" -f "binary_sha256=$archive_sha" \
  -f "base_image=$base_image" -f "runtime_base_receipt_release=$runtime_base_receipt_release"
echo "published $binary_tag and $source_tag; runtime-image workflow dispatched"
echo "next: wait for the workflow, then read image_digest from the $version-qwen38-5090-runtime-beta.$beta receipt and run scripts/stage_release.py"
