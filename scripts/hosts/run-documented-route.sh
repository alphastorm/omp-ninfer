#!/usr/bin/env bash
# Execute a documented route's shell blocks exactly as the quickstart prints them.
#
# Runs every step file of a bundle written by scripts/documented_route.py, in reading order, in
# this one shell - so variables one block defines (ROOT, STATE, LOGS, CHECKPOINTS, MODEL ...) are
# visible to the next, as they are for a reader pasting block after block into one terminal.
# Each step's bytes are hashed before execution and compared with the bundle manifest; the first
# failing command ends the run (fail-closed), and the receipt records every step's outcome either
# way. The receipt carries hashes, timings, the failing command and its exit status, never output.
#
#   run-documented-route.sh BUNDLE CLONE RECEIPT
#
# Two reader actions have no verbatim form for a runner and are recorded as substitutions: the
# placeholder SSH destination `USER@RUNTIME_HOST` is replaced by ROUTE_SSH_DESTINATION when set,
# and a block whose only command is a foreground tunnel (`open-tunnel.sh`) is started in the
# background and stopped before a block whose heading is "Fail closed" - which is exactly what
# the prose tells the reader to do with Ctrl-C.
set -eE -o pipefail
BUNDLE=$1; CLONE=$2; RECEIPT=$3
TUNNEL_PID=""
SUBSTITUTIONS=()
MANIFEST="$BUNDLE/manifest.json"
cd -- "$CLONE"
CLONE_COMMIT=$(git rev-parse HEAD 2>/dev/null || true)
STARTED=$(date -u +%Y-%m-%dT%H:%M:%SZ)
RECORDS=()
STATUS=running
CURRENT_POSITION=0; CURRENT_SLUG=; CURRENT_HEADING=; CURRENT_INDEX=0; CURRENT_SHA=; CURRENT_T0=0

record() {  # position slug heading index expected actual status elapsed error [substitution]
  RECORDS+=("$(python3 -c 'import json,sys; a=sys.argv[1:]; print(json.dumps({"position":int(a[0]),"slug":a[1],"heading":a[2],"index":int(a[3]),"block_sha256":a[4],"executed_sha256":a[5],"status":a[6],"elapsed_seconds":float(a[7]),"error":(a[8] or None),"substitution":(a[9] if len(a) > 9 and a[9] else None)}))' "$@")")
}

write_receipt() {
  python3 - "$RECEIPT" "$MANIFEST" "$CLONE_COMMIT" "$STARTED" "$STATUS" "${RECORDS[@]}" <<'PY'
import json, sys, datetime, pathlib, platform
receipt, manifest_path, commit, started, status, *records = sys.argv[1:]
manifest = json.load(open(manifest_path))
release = pathlib.Path("/etc/os-release")
host_os = ""
if release.is_file():
    for line in release.read_text().splitlines():
        if line.startswith("PRETTY_NAME="):
            host_os = line.split("=", 1)[1].strip().strip('"')
elif platform.system() == "Darwin":
    host_os = f"macOS {platform.mac_ver()[0]} {platform.machine()}"
out = {
    "artifact_type": "omp_ninfer_documented_route_run", "schema_version": 1,
    "lane": manifest["lane"], "document": manifest["document"],
    "document_sha256": manifest["document_sha256"], "started_utc": started,
    "completed_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "host_os": host_os, "clone_commit": commit,
    "steps": [json.loads(r) for r in records], "status": status,
}
with open(receipt, "w") as handle:
    json.dump(out, handle, indent=2); handle.write("\n")
PY
}

elapsed() { python3 -c "import time; print(round(time.time() - $CURRENT_T0, 3))"; }

# A predicate, not a command that fails: `set -E` propagates the ERR trap into functions, so a
# bare failing probe here would be recorded as the step's failure instead of answering "closed".
port_open() {
  python3 -c 'import socket, sys
s = socket.socket(); s.settimeout(1)
try: s.connect(("127.0.0.1", 18089))
except OSError: sys.exit(1)
finally: s.close()' && return 0 || return 1
}

# A bound local port only proves ssh's forward exists; the far end may serve nothing, which used
# to surface as a confusing failure two blocks later (measured 2026-09-12, post-cut). A tunnel
# step passes only when the route is actually reachable through it.
route_reachable() {
  python3 -c 'import sys, urllib.request
try:
    with urllib.request.urlopen("http://127.0.0.1:18089/health", timeout=3) as r:
        sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)' && return 0 || return 1
}

stop_tunnel() {
  # the block exec'd ssh inside a subshell; stop every process the wrapper started
  pkill -P "$TUNNEL_PID" 2>/dev/null || true
  kill "$TUNNEL_PID" 2>/dev/null || true
  wait "$TUNNEL_PID" 2>/dev/null || true
  for _ in $(seq 1 10); do port_open || break; sleep 1; done
  TUNNEL_PID=""
}

on_error() {
  local rc=$? cmd=$BASH_COMMAND
  trap - ERR
  # A failed run must not leave its forward listening: the next run's tunnel step would pass on
  # this listener without binding, and its fail-closed check would see a live route.
  [[ -n $TUNNEL_PID ]] && stop_tunnel
  record "$CURRENT_POSITION" "$CURRENT_SLUG" "$CURRENT_HEADING" "$CURRENT_INDEX" "$CURRENT_SHA" "$CURRENT_SHA" failed "$(elapsed)" "command failed with exit $rc: $cmd"
  while IFS=$'\t' read -r position slug heading index sha file; do
    if (( position > CURRENT_POSITION )); then
      record "$position" "$slug" "$heading" "$index" "$sha" "$(sha256sum -- "$BUNDLE/$file" | cut -d ' ' -f 1)" skipped 0 ""
    fi
  done < <(steps)
  STATUS=failed
  write_receipt
  echo "route $(lane): failed at step $CURRENT_POSITION ($CURRENT_SLUG)" >&2
  exit 1
}

steps() {
  python3 -c '
import json, sys
for s in json.load(open(sys.argv[1]))["steps"]:
    print("\t".join([str(s["position"]), s["slug"], s["heading"], str(s["index"]), s["sha256"], s["file"]]))' "$MANIFEST"
}
lane() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["lane"])' "$MANIFEST"; }

trap on_error ERR
# The step list is read up front and iterated as an array: a block that starts a background
# process or reads input must never share the loop's stdin, or the loop ends early and a
# partial run reads as a pass (measured on the macOS route's tunnel step).
STEP_LINES=()
while IFS= read -r line; do STEP_LINES+=("$line"); done < <(steps)
for line in "${STEP_LINES[@]}"; do
  IFS=$'\t' read -r position slug heading index sha file <<<"$line"
  path="$BUNDLE/$file"
  actual=$(sha256sum -- "$path" | cut -d ' ' -f 1)
  if [[ "$actual" != "$sha" ]]; then
    record "$position" "$slug" "$heading" "$index" "$sha" "$actual" refused 0 "step file bytes do not match the documented block"
    STATUS=failed; write_receipt; echo "route $(lane): refused step $position" >&2; exit 1
  fi
  CURRENT_POSITION=$position; CURRENT_SLUG=$slug; CURRENT_HEADING=$heading; CURRENT_INDEX=$index; CURRENT_SHA=$sha
  CURRENT_T0=$(python3 -c 'import time; print(time.time())')
  echo "== step $position: $slug ($heading [$index])"
  substitution=""
  text=$(cat -- "$path")
  if [[ -n ${ROUTE_SSH_DESTINATION:-} && $text == *USER@RUNTIME_HOST* ]]; then
    text=${text//USER@RUNTIME_HOST/$ROUTE_SSH_DESTINATION}
    substitution="USER@RUNTIME_HOST replaced by the operator's SSH destination"
  fi
  if [[ $heading == "Fail closed" && -n $TUNNEL_PID ]]; then
    stop_tunnel
    substitution="${substitution:+$substitution; }tunnel stopped before this block, as the prose instructs"
  fi
  if [[ $text == *open-tunnel.sh* ]]; then
    # A foreground process the reader keeps open in another terminal. The route's own tunnel must
    # own the port: a listener left by an earlier run answers the probe below, which would pass
    # this step without binding anything and then survive stop_tunnel, so the fail-closed block
    # sees a live route (measured 2026-09-12).
    if port_open; then
      echo "127.0.0.1:18089 is already listening; stop the stale forward before running the route" >&2
      false
    fi
    ( trap - ERR; set +eE; cd "$CLONE" && eval "$text" ) </dev/null & TUNNEL_PID=$!
    tunnel_ready=0
    for _ in $(seq 1 30); do
      sleep 1
      kill -0 "$TUNNEL_PID" 2>/dev/null || break
      if route_reachable; then tunnel_ready=1; break; fi
    done
    kill -0 "$TUNNEL_PID" 2>/dev/null || { false; }
    if (( tunnel_ready != 1 )); then
      echo "the tunnel is up but the route does not answer /health through it; start the runtime on the inference host first" >&2
      false
    fi
    substitution="${substitution:+$substitution; }foreground tunnel started in the background and kept open"
  else
    # Evaluate in this shell: the block's variables persist to the next block, and the ERR trap
    # above turns its first failing command into the recorded failure.
    eval "$text"
  fi
  record "$position" "$slug" "$heading" "$index" "$sha" "$actual" passed "$(elapsed)" "" "$substitution"
  write_receipt
done
trap - ERR
[[ -n $TUNNEL_PID ]] && stop_tunnel
if (( ${#RECORDS[@]} != ${#STEP_LINES[@]} )); then
  STATUS=failed; write_receipt
  echo "route $(lane): only ${#RECORDS[@]} of ${#STEP_LINES[@]} steps ran" >&2; exit 1
fi
STATUS=passed
write_receipt
echo "route $(lane): passed"
