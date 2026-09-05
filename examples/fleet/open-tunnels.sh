#!/usr/bin/env bash
# Open the three authenticated SSH local forwards the fleet fragment expects:
#   127.0.0.1:18191 -> RTX 5090 container (loopback 18088 on its host)
#   127.0.0.1:18192 -> RTX 4090 native service (loopback 18082 on its host)
#   127.0.0.1:18193 -> RTX 3090 native service (loopback 18082 on its host)
# Each argument is one SSH user@host. Pass "-" to skip a lane. The forwards run in the
# foreground of this shell; stop them with Ctrl-C. Nothing here starts or stops a runtime.
set -euo pipefail

if (($# != 3)); then
  printf 'usage: open-tunnels.sh user@main-host|- user@heavy-host|- user@scout-host|-\n' >&2
  exit 2
fi

check() {
  local destination=$1
  if [[ "$destination" == -* || "$destination" =~ [[:space:]] ||
        "$destination" != ?*@?* || "${destination#*@}" == *@* ]]; then
    printf 'error: destination must be one SSH user@host argument, got %q\n' "$destination" >&2
    exit 2
  fi
}

pids=()
forward() {
  local destination=$1 local_port=$2 remote_port=$3
  [[ "$destination" == "-" ]] && return 0
  check "$destination"
  ssh -NT \
    -o ExitOnForwardFailure=yes \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    -L "127.0.0.1:${local_port}:127.0.0.1:${remote_port}" \
    "$destination" &
  pids+=("$!")
}

forward "$1" 18191 18088
forward "$2" 18192 18082
forward "$3" 18193 18082

if ((${#pids[@]} == 0)); then
  printf 'error: every lane was skipped\n' >&2
  exit 2
fi
trap 'kill "${pids[@]}" 2>/dev/null || true' INT TERM EXIT
wait
