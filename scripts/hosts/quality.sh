#!/usr/bin/env bash
# Runs the private role corpus against the live arm server and scores it.
# Executed inside the arm's container (5090) or on the native host (4090) with the
# campaign root mounted/staged at $CAMPAIGN_ROOT (default /campaign).
#
# Usage: quality.sh <lane> <arm-label> <campaign-id> [base-url] [api-key-file] [model-id]
set -euo pipefail
lane="$1"
label="$2"
campaign_id="$3"
base_url="${4:-http://127.0.0.1:8080/v1}"
api_key_file="${5:-/run/secrets/ninfer_api_key}"
model_id="${6:-q38-ninfer}"
root="${CAMPAIGN_ROOT:-/campaign}"
qual="$root/qualification"
out="$root/quality/$label"
mkdir -p "$root/quality"
if [ -f "$out/scores.json" ]; then
  echo "quality already scored for $label"
  exit 0
fi
rm -rf "$out"
LOCAL_5090_API_KEY="$(tr -d '\r\n' < "$api_key_file")" \
python3 "$qual/scripts/run_qualification.py" \
  --model "$model_id" \
  --base-url "$base_url" \
  --cases "$qual/cases" \
  --fixtures "$qual/fixtures" \
  --out "$out" \
  --concurrency 1 \
  --reasoning-mode low \
  --reasoning-wire top-level \
  --reasoning-token-headroom 8192 \
  --timeout 900 \
  --no-ssh \
  --label "$lane/$label/$campaign_id"
python3 "$qual/scripts/score_qualification.py" --run "$out" --cases "$qual/cases"
test -f "$out/scores.json"
