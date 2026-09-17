#!/usr/bin/env bash
# Publish the already-qualified native clients and their exact public source.
# FOUNDER-ONLY / AGENT MUST NOT EXECUTE without --dry-run.
set -euo pipefail
version=; sequence=1; source_dir=; commit=; assets=; checksums_sha=; dry_run=0
while (($#)); do
  case "$1" in
    --version) version="$2"; shift 2 ;;
    --sequence) sequence="$2"; shift 2 ;;
    --source-dir) source_dir="$2"; shift 2 ;;
    --commit) commit="$2"; shift 2 ;;
    --assets) assets="$2"; shift 2 ;;
    --checksums-sha) checksums_sha="$2"; shift 2 ;;
    --dry-run) dry_run=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ && $sequence =~ ^[1-9][0-9]*$ ]] || { echo 'invalid version or sequence' >&2; exit 2; }
[[ $commit =~ ^[0-9a-f]{40}$ && $checksums_sha =~ ^[0-9a-f]{64}$ ]] || { echo 'exact source and checksum identities are required' >&2; exit 2; }
[[ -d $source_dir && -d $assets ]] || { echo 'source and asset directories must exist' >&2; exit 2; }
[[ $(shasum -a 256 "$assets/SHA256SUMS" | cut -d' ' -f1) == "$checksums_sha" ]] || { echo 'checksum-set identity mismatch' >&2; exit 1; }
git -C "$source_dir" cat-file -e "$commit^{commit}"
tree=$(git -C "$source_dir" rev-parse "$commit^{tree}")
python3 - "$assets" "$version" "$commit" "$tree" <<'PY'
import hashlib, json, pathlib, sys, tarfile
root, version, commit, tree = sys.argv[1:]
root = pathlib.Path(root)
receipts = {'windows-x64': 'windows-x64-qualification.json', 'linux-x64': 'qualification.json', 'macos-arm64': 'receipt.json'}
expected = set(receipts.values()) | {f'omp-{version}-{p}.tar.gz' for p in receipts}
entries = {}
for line in (root / 'SHA256SUMS').read_text().splitlines():
    digest, name = line.split('  ', 1)
    if name in entries or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise SystemExit('malformed checksum set')
    entries[name] = digest
if set(entries) != expected or {p.name for p in root.iterdir()} != expected | {'SHA256SUMS'}:
    raise SystemExit('asset directory is not the exact closed publication set')
for name, expected_digest in entries.items():
    with (root / name).open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != expected_digest:
            raise SystemExit(f'checksum mismatch: {name}')
for platform, receipt_name in receipts.items():
    receipt = json.loads((root / receipt_name).read_text())
    if receipt['source'] != {'commit': commit, 'tree': tree} or receipt['platform'] != platform:
        raise SystemExit(f'{platform}: source/platform identity mismatch')
    if receipt.get('providerFree') is not True or receipt.get('hardwareAccepted') is not False:
        raise SystemExit(f'{platform}: qualification boundary mismatch')
    archive = root / f'omp-{version}-{platform}.tar.gz'
    if receipt['archive']['name'] != archive.name or receipt['archive']['sha256'] != entries[archive.name] or receipt['archive']['bytes'] != archive.stat().st_size:
        raise SystemExit(f'{platform}: archive does not match qualification')
    prefix = f'omp-{version}-{platform}/'
    with tarfile.open(archive, 'r:gz') as tar:
        metadata = json.load(tar.extractfile(prefix + 'client-release.json'))
        binary = tar.extractfile(prefix + ('omp.exe' if platform == 'windows-x64' else 'omp'))
        digest = hashlib.file_digest(binary, 'sha256').hexdigest()
    if metadata['sourceCommit'] != commit or metadata['resultTree'] != tree or metadata['version'] != version or metadata['platform'] != platform:
        raise SystemExit(f'{platform}: embedded source identity mismatch')
    if digest != receipt['binary']['sha256'] or digest != metadata['binary']['sha256']:
        raise SystemExit(f'{platform}: binary identity mismatch')
    outcomes = receipt['outcomes']
    if platform == 'windows-x64' and receipt.get('passed') is not True:
        raise SystemExit('Windows qualification did not pass')
    if platform == 'linux-x64' and any(outcomes.get(k) != 'success' for k in ('archive', 'build', 'cleanup', 'install')):
        raise SystemExit('Linux qualification did not pass')
    if platform == 'macos-arm64' and (outcomes['install'].get('current') is not True or outcomes['architecture'].get('codesign') != 'valid'):
        raise SystemExit('macOS qualification did not pass')
print('All three archives, binaries, source trees, and qualification receipts verified.')
PY
source_tag="omp-v$version-ninfer-beta.$sequence"
component_tag="omp-$version-cross-platform-beta-$sequence"
gh auth status >/dev/null 2>&1
for pair in "alphastorm/oh-my-pi:$source_tag" "alphastorm/homebrew-omp:$component_tag"; do
  repository=${pair%%:*}; tag=${pair#*:}
  [[ $(gh api "repos/$repository" --jq .permissions.push) == true ]] || { echo "release write permission is unavailable: $repository" >&2; exit 1; }
  existing=$(git ls-remote --tags "https://github.com/$repository.git" "refs/tags/$tag")
  [[ -z $existing ]] || { echo "tag already exists: $repository@$tag" >&2; exit 1; }
  releases=$(gh api "repos/$repository/releases" --paginate --jq '.[].tag_name')
  if printf '%s\n' "$releases" | grep -Fxq "$tag"; then
    echo "release already exists: $repository@$tag" >&2; exit 1
  fi
done
git -C "$source_dir" push --dry-run git@github.com:alphastorm/oh-my-pi.git "$commit:refs/tags/$source_tag"
tap_commit=$(gh api repos/alphastorm/homebrew-omp/commits/main --jq .sha)
[[ $tap_commit =~ ^[0-9a-f]{40}$ ]] || exit 1
printf 'preflight ok: %s and %s; source %s, tree %s\n' "$source_tag" "$component_tag" "$commit" "$tree"
if ((dry_run)); then
  echo 'dry run: no tag, release, upload, installation, or production effect'
  exit 0
fi
asset_paths=()
for name in "omp-$version-windows-x64.tar.gz" "omp-$version-linux-x64.tar.gz" "omp-$version-macos-arm64.tar.gz" windows-x64-qualification.json qualification.json receipt.json SHA256SUMS; do
  asset_paths+=("$assets/$name")
done
notes="Exact native Windows x64, Linux x64, and macOS arm64 clients from public source $commit (tree $tree). Hosted provider-free build/install/CLI qualification only; product hardware/route acceptance and compatibility repinning are separate. No production activation or Homebrew cask change."
git -C "$source_dir" push git@github.com:alphastorm/oh-my-pi.git "$commit:refs/tags/$source_tag"
gh release create "$source_tag" --repo alphastorm/oh-my-pi --verify-tag --prerelease --latest=false --title "OMP $version NInfer beta $sequence" --notes "$notes" "${asset_paths[@]}"
gh release create "$component_tag" --repo alphastorm/homebrew-omp --target "$tap_commit" --prerelease --latest=false --title "OMP $version cross-platform beta $sequence" --notes "$notes" "${asset_paths[@]}"
printf 'published %s and %s; product compatibility and installed clients unchanged\n' "$source_tag" "$component_tag"
