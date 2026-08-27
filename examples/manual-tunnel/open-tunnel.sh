#!/usr/bin/env bash
set -euo pipefail

if (($# != 1)); then
  printf 'usage: open-tunnel.sh user@runtime-host\n' >&2
  exit 2
fi
DESTINATION=$1
if [[ "$DESTINATION" == -* || "$DESTINATION" =~ [[:space:]] ||
      "$DESTINATION" != ?*@?* || "${DESTINATION#*@}" == *@* ]]; then
  printf 'error: destination must be one SSH user@host argument\n' >&2
  exit 2
fi

exec ssh -NT \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -L 127.0.0.1:18089:127.0.0.1:18089 \
  "$DESTINATION"
