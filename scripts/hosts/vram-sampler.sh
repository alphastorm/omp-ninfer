#!/usr/bin/env bash
# Samples device memory every five seconds into /campaign/logs/vram-<label>.jsonl.
# Runs inside the frozen experiment image beside the arm's server container.
set -euo pipefail
label="$1"
out="/campaign/logs/vram-${label}.jsonl"
while true; do
  used="$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -d ' ')"
  printf '{"utc":"%s","memory_used_mib":%s}\n' "$(date -u +%FT%TZ)" "$used" >> "$out"
  sleep 5
done
