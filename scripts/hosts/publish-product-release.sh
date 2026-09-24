#!/usr/bin/env bash
# Publish one OMP NInfer product release: merge its release pull request, tag the exact verified
# commit, and create the GitHub release as Latest with the release's own notes.
# The default mode is a no-effect preflight: it proves the commit is the pull request's head with
# every check passed and the branch mergeable, that neither the tag nor the release exists, and
# that a clean checkout of exactly that commit passes the ready verifier with its immutable pins.
# Live --publish is FOUNDER-ONLY / AGENT MUST NOT EXECUTE.
#
# Usage:
#   publish-product-release.sh --release v0.7.4 --commit <sha40> --pr 47 [--publish]
set -euo pipefail

REPO=alphastorm/omp-ninfer
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
release=""; commit=""; pr=""; publish=0
while (($#)); do
  case "$1" in
    --release) release="$2"; shift 2 ;;
    --commit) commit="$2"; shift 2 ;;
    --pr) pr="$2"; shift 2 ;;
    --publish) publish=1; shift ;;
    --dry-run) shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[[ $release =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "--release must be vX.Y.Z" >&2; exit 2; }
[[ $commit =~ ^[0-9a-f]{40}$ ]] || { echo "--commit must be a full lowercase sha" >&2; exit 2; }
[[ $pr =~ ^[1-9][0-9]*$ ]] || { echo "--pr must be a pull request number" >&2; exit 2; }

git -C "$ROOT" fetch -q origin
git -C "$ROOT" cat-file -e "$commit^{commit}" || { echo "commit $commit is not fetched" >&2; exit 1; }

pr_json=$(gh pr view "$pr" --repo "$REPO" \
  --json state,headRefOid,baseRefName,mergeable,statusCheckRollup)
python3 - "$pr_json" "$commit" <<'PY'
import json, sys
view, commit = json.loads(sys.argv[1]), sys.argv[2]
if view["state"] != "OPEN" or view["baseRefName"] != "main":
    raise SystemExit(f"pull request is {view['state']} into {view['baseRefName']}, not open into main")
if view["headRefOid"] != commit:
    raise SystemExit(f"pull request head is {view['headRefOid']}, not {commit}")
if view["mergeable"] != "MERGEABLE":
    raise SystemExit(f"pull request is {view['mergeable']}")
checks = view["statusCheckRollup"]
failing = [c.get("name") or c.get("context") for c in checks
           if (c.get("conclusion") or c.get("state")) not in ("SUCCESS", "NEUTRAL", "SKIPPED")]
if not checks or failing:
    raise SystemExit(f"pull request checks are not all green: {failing or 'none reported'}")
PY

if git -C "$ROOT" rev-parse -q --verify "refs/tags/$release" >/dev/null \
    || [[ -n $(git -C "$ROOT" ls-remote --tags origin "refs/tags/$release") ]]; then
  echo "tag $release already exists" >&2; exit 1
fi
if gh release view "$release" --repo "$REPO" >/dev/null 2>&1; then
  echo "GitHub release $release already exists" >&2; exit 1
fi

work=$(mktemp -d)
trap 'git -C "$ROOT" worktree remove --force "$work/tree" >/dev/null 2>&1 || true; rm -rf "$work"' EXIT
git -C "$ROOT" worktree add -q --detach "$work/tree" "$commit"
[[ $(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["product_release"])' \
      "$work/tree/compatibility.json") == "$release" ]] \
  || { echo "compatibility.json at $commit is not $release" >&2; exit 1; }
(cd "$work/tree" && python3 scripts/verify_release.py --release "$release" --require-ready --check-pins)
notes="$work/tree/releases/$release/NINFER_RELEASE_NOTES.md"
[[ -f $notes ]] || { echo "release notes are absent at $commit" >&2; exit 1; }
title=$(sed -n '1s/^# //p' "$notes")
[[ -n $title ]] || { echo "release notes have no title heading" >&2; exit 1; }
cp "$notes" "$work/notes.md"

echo "preflight passed: $release at $commit, pull request #$pr green and mergeable, title: $title"
if ((publish == 0)); then
  echo "no effect taken; rerun with --publish to merge, tag and publish (founder-only)"
  exit 0
fi

gh pr merge "$pr" --repo "$REPO" --merge --match-head-commit "$commit"
git -C "$ROOT" tag -a "$release" "$commit" -m "$title"
git -C "$ROOT" push origin "refs/tags/$release"
gh release create "$release" --repo "$REPO" --verify-tag --latest \
  --title "$title" --notes-file "$work/notes.md"
latest=$(gh api "repos/$REPO/releases/latest" --jq .tag_name)
[[ $latest == "$release" ]] || { echo "Latest is $latest, not $release" >&2; exit 1; }
echo "published $release as Latest: https://github.com/$REPO/releases/tag/$release"
