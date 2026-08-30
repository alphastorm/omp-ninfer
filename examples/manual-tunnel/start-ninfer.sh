#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
MANIFEST="$ROOT/releases/v0.3.0/manifest.json"
PROFILE="$ROOT/profiles/qwen38-rtx5090-manual-tunnel.json"
CONTAINER=omp-ninfer-beta
MODEL_PATH=
API_KEY_FILE=
LOG_DIR=
CHECK_CONTRACT=false

usage() {
  cat <<'EOF'
usage: start-ninfer.sh --model PATH --api-key-file PATH --log-dir PATH
       start-ninfer.sh --check-contract

Starts the exact digest-pinned v0.3.0 NInfer image on remote loopback.
The release manifest must be installable (`candidate` or `ready`); a draft is rejected before
Docker runs.
EOF
}

while (($#)); do
  case "$1" in
    --model)
      MODEL_PATH=${2:?--model requires a path}
      shift 2
      ;;
    --api-key-file)
      API_KEY_FILE=${2:?--api-key-file requires a path}
      shift 2
      ;;
    --log-dir)
      LOG_DIR=${2:?--log-dir requires a path}
      shift 2
      ;;
    --check-contract)
      CHECK_CONTRACT=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'error: unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if "$CHECK_CONTRACT"; then
  python3 "$ROOT/scripts/verify_release.py"
  printf 'launcher contract valid\n'
  exit 0
fi

if [[ -z "$MODEL_PATH" || -z "$API_KEY_FILE" || -z "$LOG_DIR" ]]; then
  usage >&2
  exit 2
fi

python3 "$ROOT/scripts/verify_release.py" --require-installable

for command in docker nvidia-smi python3 sha256sum; do
  if ! command -v "$command" >/dev/null 2>&1; then
    printf 'error: required command not found: %s\n' "$command" >&2
    exit 1
  fi
done

MODEL_PATH=$(realpath -- "$MODEL_PATH")
API_KEY_FILE=$(realpath -- "$API_KEY_FILE")
mkdir -p -- "$LOG_DIR"
LOG_DIR=$(realpath -- "$LOG_DIR")
chmod 700 -- "$LOG_DIR"

python3 - "$API_KEY_FILE" <<'PY'
import os
import stat
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    raw = path.read_bytes()
    mode = stat.S_IMODE(path.stat().st_mode)
except OSError as error:
    raise SystemExit(f"error: cannot read API key file: {error}")
value = raw.strip()
if not value or b"\n" in value or b"\r" in value or b"\x00" in value:
    raise SystemExit("error: API key file must contain one non-empty line")
try:
    value.decode("utf-8")
except UnicodeDecodeError:
    raise SystemExit("error: API key file must contain UTF-8") from None
if mode & 0o077:
    raise SystemExit("error: API key file must not grant group or other permissions")
PY

RELEASE_VALUES=()
while IFS= read -r -d '' value; do
  RELEASE_VALUES+=("$value")
done < <(
  python3 - "$MANIFEST" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
values = (
    manifest["release"],
    manifest["components"]["ninfer"]["oci_reference"],
    manifest["components"]["ninfer"]["server_binary_sha256"],
    manifest["components"]["ninfer"]["source_commit"],
    manifest["components"]["ninfer"]["upstream_commit"],
    manifest["components"]["model"]["artifact_sha256"],
    manifest["runtime_identity"]["configuration_sha256"],
)
for value in values:
    if not isinstance(value, str) or not value:
        raise SystemExit("release manifest is missing a required runtime identity")
    print(value, end="\0")
PY
)
RELEASE=${RELEASE_VALUES[0]}
IMAGE=${RELEASE_VALUES[1]}
EXPECTED_BINARY_SHA256=${RELEASE_VALUES[2]}
EXPECTED_SOURCE_COMMIT=${RELEASE_VALUES[3]}
EXPECTED_UPSTREAM_COMMIT=${RELEASE_VALUES[4]}
EXPECTED_MODEL_SHA256=${RELEASE_VALUES[5]}
EXPECTED_CONFIG_SHA256=${RELEASE_VALUES[6]}

PROFILE_VALUES=()
while IFS= read -r -d '' value; do
  PROFILE_VALUES+=("$value")
done < <(
  python3 - "$PROFILE" <<'PY'
import json
import sys
from pathlib import Path

profile = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(profile["profile_id"], end="\0")
server = profile["server"]
print(server["container_network_mode"], end="\0")
print(server["deployment_profile"], end="\0")
for argument in server["arguments"]:
    print(argument, end="\0")
PY
)
PROFILE_ID=${PROFILE_VALUES[0]}
CONTAINER_NETWORK_MODE=${PROFILE_VALUES[1]}
EXPECTED_DEPLOYMENT_PROFILE=${PROFILE_VALUES[2]}
PROFILE_ARGS=("${PROFILE_VALUES[@]:3}")

if [[ ! -f "$MODEL_PATH" ]]; then
  printf 'error: model is not a regular file: %s\n' "$MODEL_PATH" >&2
  exit 1
fi
ACTUAL_MODEL_SHA256=$(sha256sum -- "$MODEL_PATH" | cut -d ' ' -f 1)
if [[ "$ACTUAL_MODEL_SHA256" != "$EXPECTED_MODEL_SHA256" ]]; then
  printf 'error: model SHA-256 mismatch\nexpected: %s\nactual:   %s\n' \
    "$EXPECTED_MODEL_SHA256" "$ACTUAL_MODEL_SHA256" >&2
  exit 1
fi

if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  printf 'error: container already exists: %s\n' "$CONTAINER" >&2
  exit 1
fi

nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv,noheader
docker pull "$IMAGE"
ACTUAL_BINARY_SHA256=$(
  docker run --rm --entrypoint sha256sum "$IMAGE" /usr/local/bin/ninfer-serve |
    cut -d ' ' -f 1
)
if [[ "$ACTUAL_BINARY_SHA256" != "$EXPECTED_BINARY_SHA256" ]]; then
  printf 'error: NInfer server binary SHA-256 mismatch\nexpected: %s\nactual:   %s\n' \
    "$EXPECTED_BINARY_SHA256" "$ACTUAL_BINARY_SHA256" >&2
  exit 1
fi

CONTAINER_ID=$(
  docker run --detach \
    --name "$CONTAINER" \
    --restart no \
    --gpus all \
    --network "$CONTAINER_NETWORK_MODE" \
    --label "org.omp-ninfer.release=$RELEASE" \
    --label "org.omp-ninfer.profile=$PROFILE_ID" \
    --label "org.ninfer.source-commit=$EXPECTED_SOURCE_COMMIT" \
    --volume "$MODEL_PATH:/models/qwen3_8_27b.ninfer:ro" \
    --volume "$API_KEY_FILE:/run/secrets/ninfer_api_key:ro" \
    --volume "$LOG_DIR:/logs" \
    "$IMAGE" \
    /bin/sh -c \
      'model="$1"; shift; exec /usr/local/bin/ninfer-serve "$model" "$@" --api-key "$(cat /run/secrets/ninfer_api_key)"' \
    sh \
    /models/qwen3_8_27b.ninfer \
    "${PROFILE_ARGS[@]}" \
    --request-log-jsonl /logs/requests.jsonl
)
printf 'started %s (%s)\n' "$CONTAINER" "$CONTAINER_ID"

# Fail fast on the WSL mirrored-loopback drift signature: the server logs that it is
# listening on host loopback, but the port is unreachable from this namespace
# (docs/TROUBLESHOOTING.md, "The server listens but loopback is unreachable").
probe_loopback() {
  python3 - <<'PY'
import socket
import sys

probe = socket.socket()
probe.settimeout(3)
try:
    probe.connect(("127.0.0.1", 18089))
except OSError:
    sys.exit(1)
finally:
    probe.close()
PY
}

LISTENING_PATTERN='listening on http://127.0.0.1:18089'
LISTENING_GRACE=${NINFER_LOOPBACK_GRACE:-15}
PREFLIGHT_DEADLINE=$((SECONDS + 900))
LISTENING_SINCE=
LOOPBACK_REACHABLE=false
while ((SECONDS < PREFLIGHT_DEADLINE)); do
  if probe_loopback; then
    LOOPBACK_REACHABLE=true
    break
  fi
  if [[ -z "$LISTENING_SINCE" ]]; then
    if docker logs "$CONTAINER" 2>&1 | grep -qF "$LISTENING_PATTERN"; then
      LISTENING_SINCE=$SECONDS
    fi
  elif ((SECONDS - LISTENING_SINCE >= LISTENING_GRACE)); then
    printf 'error: wsl-mirrored-loopback-unavailable\n' >&2
    printf 'NInfer logs "%s", but host loopback cannot reach the port.\n' "$LISTENING_PATTERN" >&2
    printf 'The WSL/Docker Desktop loopback path has drifted on this host.\n' >&2
    printf 'Recovery: from Windows run `wsl --shutdown`, start Docker Desktop, then rerun this launcher.\n' >&2
    printf 'See docs/TROUBLESHOOTING.md; the container stays up for `docker logs %s`.\n' "$CONTAINER" >&2
    exit 1
  fi
  sleep 5
done
if [[ "$LOOPBACK_REACHABLE" != true ]]; then
  printf 'error: NInfer did not become ready within 900 seconds: loopback connection never succeeded\n' >&2
  printf 'Inspect `docker logs %s`; the container is left in place for diagnosis.\n' "$CONTAINER" >&2
  exit 1
fi

python3 - \
  "$API_KEY_FILE" \
  "$EXPECTED_UPSTREAM_COMMIT" \
  "$EXPECTED_SOURCE_COMMIT" \
  "$EXPECTED_BINARY_SHA256" \
  "$EXPECTED_MODEL_SHA256" \
  "$EXPECTED_CONFIG_SHA256" \
  "$EXPECTED_DEPLOYMENT_PROFILE" <<'PY'
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

key_path, upstream, source, binary_sha, model_sha, config_sha, deployment_profile = sys.argv[1:]
api_key = Path(key_path).read_text(encoding="utf-8").strip()
request = urllib.request.Request(
    "http://127.0.0.1:18089/v1/ninfer/status",
    headers={"Authorization": f"Bearer {api_key}"},
)
deadline = time.monotonic() + 900
last_error = "server did not answer"
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            status = json.load(response)
        break
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        last_error = str(error)
        time.sleep(5)
else:
    raise SystemExit(f"error: NInfer did not become ready within 900 seconds: {last_error}")

identity = status.get("identity", {})
runtime = status.get("runtime", {})
scheduler = status.get("scheduler", {})
expected = {
    "artifact_type": (status.get("artifact_type"), "ninfer_server_status"),
    "schema_version": (status.get("schema_version"), 1),
    "status": (status.get("status"), "ok"),
    "upstream_base_sha": (identity.get("upstream_base_sha"), upstream),
    "patch_stack_sha": (identity.get("patch_stack_sha"), source),
    "source_dirty": (identity.get("source_dirty"), False),
    "deployment_profile": (identity.get("deployment_profile"), deployment_profile),
    "binary_sha256": (identity.get("binary_sha256"), binary_sha),
    "model_artifact_sha256": (identity.get("model_artifact_sha256"), model_sha),
    "config_sha256": (identity.get("config_sha256"), config_sha),
    "public_model_id": (runtime.get("public_model_id"), "q38-ninfer"),
    "max_context": (runtime.get("max_context"), 131072),
    "kv_cache": (runtime.get("kv_cache"), "bf16"),
    "max_concurrency": (scheduler.get("max_concurrency"), 1),
}
mismatches = [
    f"{name}: expected {wanted!r}, got {actual!r}"
    for name, (actual, wanted) in expected.items()
    if actual != wanted
]
if mismatches:
    raise SystemExit("error: authenticated NInfer identity mismatch\n" + "\n".join(mismatches))
print(json.dumps({
    "artifact_type": status["artifact_type"],
    "schema_version": status["schema_version"],
    "status": status["status"],
    "public_model_id": runtime["public_model_id"],
    "deployment_profile": identity["deployment_profile"],
    "binary_sha256": identity["binary_sha256"],
    "model_artifact_sha256": identity["model_artifact_sha256"],
    "config_sha256": identity["config_sha256"],
}, indent=2, sort_keys=True))
PY

printf 'NInfer is ready on remote loopback http://127.0.0.1:18089\n'
