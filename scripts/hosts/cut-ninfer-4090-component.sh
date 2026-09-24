#!/usr/bin/env bash
# Publish one RTX 4090 native NInfer component: the release tag at the exact source commit and one
# prerelease carrying the packager's closed asset set, after its canonical native qualification.
# The default mode is a no-effect preflight: it proves the outer SHA256SUMS closes and verifies the
# asset directory, the package build receipt and lane specification name the commit and release,
# the source archive holds exactly that commit's tree, and neither tag nor release exists yet.
# Live --publish is FOUNDER-ONLY / AGENT MUST NOT EXECUTE.
#
# Usage:
#   cut-ninfer-4090-component.sh --version v0.6.6 --commit <sha40> --assets DIR \
#     --checksums-sha <sha256> --notes-file FILE [--beta 1] [--publish]
set -euo pipefail

REPO=alphastorm/ninfer
LANE=rtx4090
RUNTIME_REPO_DIR="${NINFER_RUNTIME_DIR:-$HOME/Development/ninfer-lane-5090}"
version=""; commit=""; assets=""; checksums_sha=""; notes_file=""; beta=1; publish=0
while (($#)); do
  case "$1" in
    --version) version="$2"; shift 2 ;;
    --commit) commit="$2"; shift 2 ;;
    --assets) assets="$2"; shift 2 ;;
    --checksums-sha) checksums_sha="$2"; shift 2 ;;
    --notes-file) notes_file="$2"; shift 2 ;;
    --beta) beta="$2"; shift 2 ;;
    --publish) publish=1; shift ;;
    --dry-run) shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[[ $version =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "--version must be vX.Y.Z" >&2; exit 2; }
[[ $commit =~ ^[0-9a-f]{40}$ ]] || { echo "--commit must be a full lowercase sha" >&2; exit 2; }
[[ $checksums_sha =~ ^[0-9a-f]{64}$ ]] || { echo "--checksums-sha must be a sha256 hex" >&2; exit 2; }
[[ $beta =~ ^[1-9][0-9]*$ ]] || { echo "--beta must be a positive integer" >&2; exit 2; }
[[ -d $assets ]] || { echo "--assets must be a directory" >&2; exit 2; }
[[ -f $notes_file ]] || { echo "--notes-file must name the release notes" >&2; exit 2; }
git -C "$RUNTIME_REPO_DIR" cat-file -e "$commit^{commit}" || { echo "commit not in $RUNTIME_REPO_DIR" >&2; exit 1; }
[[ $(shasum -a 256 "$assets/SHA256SUMS" | cut -d' ' -f1) == "$checksums_sha" ]] \
  || { echo "SHA256SUMS does not match --checksums-sha" >&2; exit 1; }

spec_json=$(git -C "$RUNTIME_REPO_DIR" show "$commit:packaging/windows/lanes/$LANE/release-spec.json")
python3 - "$assets" "$version" "$beta" "$commit" "$RUNTIME_REPO_DIR" "$spec_json" <<'PY'
import hashlib, json, pathlib, subprocess, sys, tarfile
root, version, beta, commit, runtime, spec_text = sys.argv[1:]
root = pathlib.Path(root)
spec = json.loads(spec_text)
release_version = f"{version[1:]}-beta.{beta}"
if spec["release_version"] != release_version:
    raise SystemExit(f"lane specification names {spec['release_version']}, not {release_version}")
stem = f"{spec['product_prefix']}-v{release_version}"
package = f"{stem}-{spec['platform']}.tar.gz"
inner_sums = f"{stem}-{spec['platform']}.SHA256SUMS"
sbom = f"{stem}-{spec['platform']}.spdx.json"
source = f"{stem}-source.tar.gz"
support = ["Install-Release.ps1", "Control-Release.ps1", "Control-GpuOwner.ps1", "Protect-StateRoot.ps1"]
listed = set(support) | {package, inner_sums, sbom, source, "package-build-receipt.json"}

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

tag="$version-qwen38-4090-beta.$beta"
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
  --title "NInfer RTX 4090 native durable-session runtime ($version)" --notes-file "$notes_file" \
  "$assets"/*
echo "published $tag; bind it with scripts/bind_native_variant.py"
