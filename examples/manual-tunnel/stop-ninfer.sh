#!/usr/bin/env bash
set -euo pipefail

CONTAINER=omp-ninfer-beta
EXPECTED_RELEASE=v0.2.0-beta.1
EXPECTED_PROFILE=qwen38-rtx5090-manual-tunnel

if ! docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  printf '%s is absent\n' "$CONTAINER"
  exit 0
fi

ACTUAL_RELEASE=$(docker container inspect --format '{{ index .Config.Labels "org.omp-ninfer.release" }}' "$CONTAINER")
ACTUAL_PROFILE=$(docker container inspect --format '{{ index .Config.Labels "org.omp-ninfer.profile" }}' "$CONTAINER")
if [[ "$ACTUAL_RELEASE" != "$EXPECTED_RELEASE" || "$ACTUAL_PROFILE" != "$EXPECTED_PROFILE" ]]; then
  printf 'error: refusing to stop container with unexpected ownership labels\n' >&2
  printf 'release: expected %s, got %s\n' "$EXPECTED_RELEASE" "$ACTUAL_RELEASE" >&2
  printf 'profile: expected %s, got %s\n' "$EXPECTED_PROFILE" "$ACTUAL_PROFILE" >&2
  exit 1
fi

docker stop --time 30 "$CONTAINER"
docker rm "$CONTAINER"
printf 'stopped and removed %s; model, key, and request-log files were retained\n' "$CONTAINER"
