#!/usr/bin/env bash
# Publish one RTX 5090 NInfer runtime component: the binary prerelease, the exact source
# archive prerelease, and the runtime-image workflow run that wraps the published binary into
# a digest-addressed image. Every input is an exact identity; the script refuses to run unless
# the local assets hash to what the caller declares and neither tag exists yet.
#
# FOUNDER-ONLY / AGENT MUST NOT EXECUTE without --dry-run: this creates public releases.
#
# Usage:
#   cut-ninfer-5090-component.sh --version v0.5.1 --commit <sha40> \
#     --assets ~/Desktop/ninfer-v0.5.1-release --archive-sha <sha256> --sbom-sha <sha256> \
#     --source-archive-sha <sha256> [--beta 1] [--notes-file FILE] [--dry-run]
set -euo pipefail

REPO=alphastorm/ninfer
RUNTIME_REPO_DIR="${NINFER_RUNTIME_DIR:-$HOME/Development/ninfer-lane-5090}"
version=""; commit=""; assets=""; archive_sha=""; sbom_sha=""; source_sha=""; beta=1; notes_file=""; dry_run=0
while [ $# -gt 0 ]; do
  case "$1" in
    --version) version="$2"; shift 2 ;;
    --commit) commit="$2"; shift 2 ;;
    --assets) assets="$2"; shift 2 ;;
    --archive-sha) archive_sha="$2"; shift 2 ;;
    --sbom-sha) sbom_sha="$2"; shift 2 ;;
    --source-archive-sha) source_sha="$2"; shift 2 ;;
    --beta) beta="$2"; shift 2 ;;
    --notes-file) notes_file="$2"; shift 2 ;;
    --dry-run) dry_run=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[[ "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "--version must be vX.Y.Z" >&2; exit 2; }
[[ "$commit" =~ ^[0-9a-f]{40}$ ]] || { echo "--commit must be a full lowercase sha" >&2; exit 2; }
[[ "$archive_sha" =~ ^[0-9a-f]{64}$ && "$sbom_sha" =~ ^[0-9a-f]{64}$ && "$source_sha" =~ ^[0-9a-f]{64}$ ]] || { echo "every --*-sha must be a sha256 hex" >&2; exit 2; }
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
echo "preflight ok: $binary_tag and $source_tag at $commit; archive $archive_sha"
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
  -f "source_commit=$commit" -f "release_tag=$binary_tag" -f "binary_asset=$archive" -f "binary_sha256=$archive_sha"
echo "published $binary_tag and $source_tag; runtime-image workflow dispatched"
echo "next: wait for the workflow, then read image_digest from the $version-qwen38-5090-runtime-beta.$beta receipt and run scripts/stage_release.py"
