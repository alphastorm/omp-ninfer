# Troubleshooting

Oh My Pi (coding-agent client) → OMP NInfer (qualified appliance and release layer) → NInfer
(inference engine) → Qwen3.8 27B (served model).

Fix the first concrete mismatch. Do not rerun an unchanged install or replace an immutable identity
with a local image or modified profile.

## Named-cause preflight

Run `python3 scripts/doctor.py --offline --json` from your clone for a no-host check, or use
the [quickstart doctor command](QUICKSTART.md#contributor-acceptance-and-preflight) on the
inference host before starting its lane. Each failure has a stable check name, a cause and a
remediation; JSON never includes bearer values, local filenames, GPU UUIDs or raw command output.
Exit 1 means a check failed. Offline exit 0 means the selected local checks passed, **not**
that a GPU host was checked. Doctor receipts are preflight, never release qualification.

- **`docker_reachability`, `wsl2_reachability`, `docker_bind_mounts`:** start the model-owning
  WSL2 distro, enable its Docker Desktop integration and restart Docker Desktop while the distro
  is running. The probe uses the pinned image with `--pull=never` and read-only mounts; it neither
  downloads an image nor starts/stops an existing container. Run in the model's WSL distro for
  Linux paths. The launcher remains authoritative for checkpoint-directory staging.
- **`docker_network_mode`, `container_network`:** use bridge publication
  `127.0.0.1:18089:8080`, not `--network host`. Issue #15 was fixed in the documented route:
  Docker Desktop's host network is the engine VM, not the Windows loopback endpoint.
- **`loopback_bind`, `loopback_port_free`, `loopback_reachability`:** the container route uses
  port 18089; both sequential native lanes share 18082. Inspect the owner rather than killing an
  unknown process. `--running` checks an existing listener and connectivity; it does not claim
  the service behind that port has the right runtime identity.
- **`driver_floor`, `gpu_selection`:** update the host NVIDIA driver or select the intended
  `--gpu-uuid`. Native driver floors come from the package release spec; the container uses a
  declared profile floor or CUDA 13's major compatibility floor of 580. This is a prerequisite,
  not a claim that every driver above it was qualified.
- **`ram_total_mib`, `ram_free_mib`, `vram_total_mib`, `vram_free_mib`:** floors come from the
  selected profile. Total RAM/VRAM floors are not reinterpreted as free-memory floors. Before
  startup, available RAM must at least back the profile's pinned host-KV pool unless the profile
  declares a separate free-RAM floor. Free VRAM is reported; a free-VRAM gate is applied only
  when the profile declares one. `--running` does not demand memory already allocated by NInfer
  be free. For a WSL RAM shortage, raise `[wsl2] memory=32GB` in `.wslconfig`, then shut down
  WSL and restart Docker **only during an owner-approved window**.
- **`model_file`, `model_bytes`, `model_sha256`, `omp_hash`, `bearer_permissions`:** use the
  pinned lane artifact and stock client, opt into full model hashing with `--hash-model`, and
  keep the bearer file owner-only. POSIX files must be owner-owned with no group/world access;
  native Windows uses a protected owner/SYSTEM/Administrators ACL. Do not paste keys into reports.

Doctor does not install, repair, stop production, change firewall rules or grant permission for
a maintenance window. Re-run only after fixing the named cause. A contributor's `rehearsal`
acceptance receipt is deliberately rejected by `verify_release.py`; obtain owner-run live and
release-gate evidence instead of relabeling the receipt.

## Release and identity

### `release manifest is not installable`

Use a clean clone of the current public release tag (`v0.13.1`) and run
`python3 scripts/verify_release.py --require-ready`. Moving `main`, an older tag, or a partially
staged manifest is not installable. A `draft` or `candidate` manifest retains explicit blockers; do
not fill missing component identities from a local cache.

### Model byte count or SHA-256 mismatch

Every lane binds the same artifact URL, revision, byte count, and SHA-256 in
[`releases/v0.13.1/manifest.json`](../releases/v0.13.1/manifest.json): all three lanes serve
`components.model` (`81f924d4`, 20,437,521,664 bytes, downloaded to `qwen3_8_27b-v3.ninfer`; prior
native releases through `v0.13.0` served `eec39564` at 18,210,531,328 bytes, which stays in
`qwen3_8_27b.ninfer` for historical recovery).

1. Keep the failed file out of the final model path.
2. Confirm whether the file matches the wrong lane's artifact or whether the download was
   interrupted, and check available disk space.
3. Resume the lane's pinned URL with `curl --continue-at -` (or `curl.exe --continue-at -` on
   Windows).
4. Re-run both byte-count and SHA-256 checks.

Do not select a file by modification time, substitute one lane's model artifact for the other, or
use another `.ninfer` file with the same filename.

### NInfer image or binary mismatch

The container image reference must contain `@sha256:`. A binary or package mismatch means the local
bytes do not match the qualified release (`v0.13.1`), even if a mutable tag or filename looks
correct. Preserve the expected and actual SHA-256 values, remove no unrelated images, and report
the release and profile IDs together with those two content-safe digests.

## Download and startup

### `container already exists: omp-ninfer-beta`

Inspect the existing container before changing it:

```sh
docker ps -a --filter name='^/omp-ninfer-beta$'
docker logs --tail 100 omp-ninfer-beta
```

If it was created by this release, use `examples/manual-tunnel/stop-ninfer.sh`; that script refuses
unexpected ownership labels. If labels do not match, do not stop or remove it through the release
script.

### The container exists but will not start after a host reboot

Docker Desktop stages a container's bind mounts when the container is created, from the
filesystem those paths live on. Restarting that filesystem's WSL distro - which every host reboot
does, because nothing starts a WSL distro at boot - replaces the staging, and the container that
was created against it cannot use it again. Two shapes, both from the same cause:

```sh
docker start omp-ninfer-beta
# Error response from daemon: ... error mounting
# ".../docker-desktop-bind-mounts/<distro>/<hash>" to rootfs at
# "/models/qwen3_8_27b.ninfer": ... not a directory
docker container inspect omp-ninfer-beta --format '{{.State.ExitCode}} {{.RestartCount}}'
# 127 0
```

`RestartCount 0` with exit `127` means Docker did not retry and will not: a restart policy cannot
fix a mount it cannot stage. The second shape is quieter and worse - the container starts, its
file mounts are empty, the server rejects its own empty key file, prints usage text, and exits
`1`; with a restart policy `docker ps` then shows `restarting` while the logs show usage rather
than an error.

Recovery is recreation, not `docker start`. Checkpoints live in the host store directory, not in
the container, so this continues the sessions it holds:

```sh
./examples/manual-tunnel/stop-ninfer.sh
./examples/manual-tunnel/start-ninfer.sh --model ... # the same arguments as the first launch
```

`start-ninfer.sh` proves the mounts inside a throwaway container before loading the 20.4 GB model,
so a still-broken engine is refused with what that container saw instead of entering a crash loop.
If it refuses, start the WSL distro that owns the paths, restart Docker Desktop while that distro
is running, and retry: the engine only stages a distro it saw when it initialized.

### `needs N MiB of runtime-host memory; this host offers M MiB`

The RTX 5090 profile (`qwen38-5090-v0.13.0`) declares a 20,867.734375 MiB (21,881,405,440-byte)
shared Host context budget and a 28,672 MiB runtime-host memory floor (`runtime_host.minimum_runtime_memory_mib`).
`start-ninfer.sh` reads that floor from the profile and compares it with `MemTotal` inside a
throwaway container, refusing before loading the model.

On Docker Desktop the container sees the WSL2 utility VM, which takes half the machine's RAM by
default - every distro and the engine share that one VM. Raise it in `%UserProfile%\.wslconfig`
and restart WSL:

```ini
[wsl2]
memory=32GB
```

```sh
wsl --shutdown
```

The refusal exists because an under-provisioned host does not degrade gracefully; in a 24 GiB WSL2
VM the server reached 24,006 MiB and was OOM-killed mid-request:

```sh
docker container inspect omp-ninfer-beta --format '{{.State.ExitCode}} {{.State.OOMKilled}}'
# 137 true
dmesg | grep -i 'out of memory'
# Out of memory: Killed process 2347 (ninfer-serve) total-vm:85995096kB ...
```

Do not lower `--host-context-mib` by hand or downgrade to `v0.6.10`: changing profile arguments
invalidates the configuration SHA-256 and leaves the qualified envelope, and `v0.6.10` and earlier
releases are unsupported.

### GPU is unavailable inside Docker

Establish the failure at the smallest boundary:

```sh
nvidia-smi
docker run --rm --gpus all nvidia/cuda:13.1.2-runtime-ubuntu24.04 nvidia-smi
```

The first command checks the host driver. The second checks Docker and NVIDIA Container Toolkit.
Fix that boundary before starting the 20.4 GB RTX 5090 model. Do not infer container GPU access
from a host-only `nvidia-smi` result.

### NInfer never becomes ready

Model load can take several minutes. The container launcher waits up to 900 seconds, then leaves
the owned container in place for diagnosis:

```sh
docker ps -a --filter name='^/omp-ninfer-beta$'
docker logs --tail 200 omp-ninfer-beta
```

Common first failures are insufficient GPU memory (or another process holding VRAM), the NVIDIA
container runtime not being available, model mount or permission errors, or an identity mismatch.
On native Windows lanes (`rtx4090-windows-native` and `rtx3090-windows-native`), the startup check
also refuses an active interactive GPU owner (such as Desktop Window Manager or an overlay above
the idle threshold) or a held GPU lease from the sibling native lane. Correct the named cause,
stop the owned container or native lane, and start once.

### Docker credential helper fails over non-interactive SSH

`docker pull` can fail with `error getting credentials … A specified logon session does not
exist` when Docker Desktop's Windows credential helper runs inside a non-interactive SSH
session — even for anonymous public pulls. Point `DOCKER_CONFIG` at an empty configuration for
the launcher invocation:

```sh
DOCKER_CONFIG=$(mktemp -d)
printf '{}\n' > "$DOCKER_CONFIG/config.json"
export DOCKER_CONFIG
```

This bypasses only credential lookup; digest pinning and hash verification are unchanged.

## Network and authentication

### Managed Mac tunnel (preview)

Use `python3 scripts/mac_tunnel.py status` to distinguish a stopped LaunchAgent, a starting
supervisor, a connecting SSH process, and exponential backoff. A `listener_owned` value of
`true` means the current supervisor's SSH child owns only the selected `127.0.0.1` listener;
it does not prove the remote server is ready. `python3 scripts/doctor.py --mac-tunnel --json`
checks the existing private bearer file and authenticated `/v1/models` over that listener.
It never probes Docker, WSL or the GPU and never promotes the macOS preview route.

If SSH repeatedly exits, verify the explicit user@hostname/IP and host key interactively,
using `ssh -F /dev/null USER@RUNTIME_HOST`; managed SSH ignores configuration aliases and
requires unattended authentication. Supply an existing `--identity-file PATH` during install
if needed. Do not disable host-key checking or paste credentials into a command. A passphrase
key that works only with a terminal's agent may not work in the GUI launchd environment.
The helper suppresses raw SSH output to avoid collecting private connection information;
use your interactive SSH session to diagnose the authentication failure.

If the local port is occupied, stop only your own manual tunnel or conflicting process.
The helper never kills a foreign listener; SSH exits and retries with capped backoff.
If SSH owns the listener but the endpoint check fails, check the existing bearer file
(owner-only permissions, nonempty, not a symlink), Windows loopback publication and remote
service readiness. No cloud provider or alternate port is substituted.

Run lifecycle commands as the logged-in Mac user without sudo. `stop` unloads and disables
the agent even across future logins; `start` enables it again. Stop before reinstalling to
change the destination or refresh the installed interpreter/helper. If launchd cannot find
the pinned Python executable after an upgrade, reinstall using a stable Python 3 path.
`uninstall` retains credentials and client settings. Private `status.json` snapshots and
`runtime.json` in `~/Library/Application Support/omp-ninfer/tunnel` contain transport state
only; stale runtime from a different supervisor PID is not treated as readiness.

### Port `18089` is occupied

On the RTX 5090 inference host, identify the loopback listener on `127.0.0.1:18089` before
stopping anything. On the Mac, `open-tunnel.sh` exits immediately when local port `18089` is taken
because it passes `ExitOnForwardFailure=yes`. On the two-GPU native Windows host, both the RTX 4090
and RTX 3090 native lanes share loopback port `127.0.0.1:18082` and only one may run at a time:
stop the active native lane with `Control-Release.ps1 -Action Stop -StateRoot $StateRoot` before
starting the other. Do not silently change a port on one side; the profile configuration identity
and OMP provider URL must match.

### The server logs that it is listening but the port is unreachable

Fixed in `v0.6.3`, and worth knowing if you are inspecting an older clone. Up to `v0.6.2` the
launcher ran its container with `--network host` and the server bound `127.0.0.1:18089`. On Docker
Desktop that network namespace belongs to the utility VM, not to Windows or the WSL2 distro: the
server is listening inside the VM, and neither Windows nor WSL2 can reach it
([EXP-031](measurements/2026-09-11-rtx5090-public-route-qualification.json),
[#15](https://github.com/alphastorm/omp-ninfer/issues/15)).

The RTX 5090 route runs the container on Docker `bridge` (`--host 0.0.0.0 --port 8080` inside the
container) and publishes that port on the inference host's loopback (`--publish
127.0.0.1:18089:8080`), which both Windows and WSL2 reach. Use the current `v0.13.1` release tag
rather than editing ports or bind addresses by hand: the profile's configuration SHA-256 covers
them, and the launcher refuses any modified profile.

### Authenticated status returns `401`

The client and the inference runtime must read the same single-line UTF-8 bearer key. On the
RTX 5090 container and macOS route, check file existence, permissions, and byte length without
printing the secret:

```sh
stat -c '%a %s %n' "$HOME/.config/omp-ninfer/api-key"   # inference host (WSL2/Linux)
stat -f '%Lp %z %N' "$HOME/.omp/agent/ninfer-beta.key" # macOS client
```

Both files must be mode `600` (no group or other permissions) and match in byte length; re-copy
over SSH if they differ. On native Windows OMP clients, confirm that the current PowerShell
session loaded `$env:NINFER_BETA_API_KEY` from `$HOME\.omp\agent\ninfer-beta.key` (RTX 5090 local
route) or `$env:NINFER_NATIVE_API_KEY` from `%ProgramData%\omp-ninfer-keys\api-key.txt` (native
RTX 4090 and RTX 3090 routes) before invoking `omp.exe`. Never print the key in a diagnostic
command, screenshot, issue, or shell trace.

### Tunnel connects but OMP cannot reach NInfer

- Keep `examples/manual-tunnel/open-tunnel.sh` running in its own terminal on the Mac.
- Confirm the SSH destination reaches the host or WSL2 environment where Docker published
  `127.0.0.1:18089`.
- Confirm `omp-ninfer-beta` is running and remote `127.0.0.1:18089` answers `/health`.
- Confirm Mac port `18089` is not occupied by a stale SSH tunnel or another local process.
- Confirm `~/.omp/agent/models.yml` uses `http://127.0.0.1:18089/v1` and model ID `q38-ninfer`.

Do not point OMP at a remote LAN or tailnet IP address as a workaround.

## Client configuration

### OMP cannot resolve `ninfer-beta/q38-ninfer`

Validate that `~/.omp/agent/models.yml` is valid YAML and contains a single `providers` mapping
with your lane's provider entry (`ninfer-beta` with model `q38-ninfer` from
`examples/manual-tunnel/models.fragment.yml` or
`examples/windows-docker-local/models.fragment.yml`; `ninfer-native-4090` with model `qwen3.8-27b`
from `examples/windows-native/models.fragment.yml`; or `ninfer-native-3090` with model `q38-ninfer`
from `examples/windows-native/models-rtx3090.fragment.yml`). If `models.yml` existed before setup,
merge the provider block rather than nesting a second `providers:` key or overwriting other
providers.

Stock Oh My Pi 18.12.6 uses per-model `compat.statefulResponses: true` under each NInfer model
entry (ignoring the retired fork-only `ninferStatefulResponses` key) and requires
`PI_OPENAI_STATEFUL` to be unset in the environment (`unset PI_OPENAI_STATEFUL` on POSIX or
`Remove-Item Env:PI_OPENAI_STATEFUL -ErrorAction SilentlyContinue` in PowerShell) so an inherited
`0` cannot disable Responses chaining.

Install or merge the fail-closed configuration into `~/.omp/agent/config.yml`, then run the
explicit provider/model route:

```sh
unset PI_OPENAI_STATEFUL
install -m 600 examples/manual-tunnel/fail-closed.yml "$HOME/.omp/agent/config.yml"
omp --model ninfer-beta/q38-ninfer
```

### Text works but image input fails

Vision is qualified only on the RTX 5090 container lane (`qwen38-5090-v0.13.0`, configuration
`751d22dc`, model artifact `81f924d4`), which launches `ninfer-serve` with `--vision` and declares
`input: [text, image]` in its OMP model fragments. The native Windows RTX 4090 and RTX 3090 lanes
launch `ninfer-serve` with `vision: false` (`input: [text]` in their OMP model fragments) and reject image inputs by design.
On the RTX 5090 lane, verify that `/v1/ninfer/status` reports `deployment_profile:
"qwen38-5090-v0.13.0"` and `config_sha256:
"751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47"`, that the image path is a
readable local file, and that no local OMP configuration overlay stripped `image` from the model's
`input` list.

### A long RTX 5090 session fails when OMP compacts it

Stock Oh My Pi 18.12.6 includes upstream [#13687](https://github.com/can1357/oh-my-pi/pull/13687),
which defaults custom and local OpenAI Responses endpoints to `detail: "auto"` for both live image
turns and replayed compaction images. Current `v0.13.1` model fragments therefore need no
image-detail override.

**Legacy pre-18.8.7 clients only:** OMP compacts a 131,072-token session automatically at about
111,412 tokens. On vision-capable models, its first compaction method archives earlier turns as
images and older OMP releases requested native image resolution (`detail: "original"`), which
NInfer refuses:

```text
400 only input_image detail 'auto' is supported
```

If you encounter this error, first verify that `omp --version` reports `omp/18.12.6` and that your
`models.yml` matches the current `v0.13.1` fragment. On historical pre-18.8.7 releases (such as
`v0.10.0` / OMP 18.4.10; see [release history](RELEASES.md#version-identities)), the workaround was
setting `supportsImageDetailOriginal: false` under the RTX 5090 model's `compat` mapping. The
text-only native RTX 4090 and RTX 3090 lanes never compact sessions into images.

### A turn fails with `request_queue_timeout` late in a long session

```text
503 inference request expired while waiting for admission
```

In `v0.13.1`, the RTX 5090 profile serves up to two requests in flight (`--max-concurrency 2`,
146,368-token automatic BF16 KV pool) with a 180 s pending timeout (`--pending-timeout-ms 180000`), while the
native Windows RTX 4090 and RTX 3090 lanes each serve one request at a time with a 30 s pending
timeout. A request arriving when a lane is full waits at the server and expires if admission takes
longer than the lane's pending timeout.

By default, OMP writes its compaction summary in a background request as a session approaches the
compaction threshold. Without a client-side concurrency cap, your next interactive turn queued
behind that background compaction at the server, expired repeatedly against the server's admission
timeout, and failed once the summary outlasted OMP's resends (56-61 s per background handoff on
RTX 4090 in [EXP-072](measurements/2026-09-28-omp-long-sessions.json)).

`examples/manual-tunnel/fail-closed.yml` caps every NInfer provider at its lane's concurrency so
OMP holds any excess request locally (with no deadline) until an in-flight request completes
([EXP-074](measurements/2026-09-29-long-session-cache.json),
[EXP-077](measurements/2026-09-29-rtx5090-two-requests-in-flight.json)). If you merged an older
`~/.omp/agent/config.yml`, add the complete `providers.maxInFlightRequests` map:

```yaml
providers:
  maxInFlightRequests:
    ninfer-beta: 2
    ninfer-native-4090: 1
    ninfer-native-3090: 1
    ninfer-main: 2
    ninfer-heavy: 1
```

Include every provider ID you route to a NInfer lane (OMP leaves any provider omitted from the map
unlimited). Keep `ninfer-beta: 2` and `ninfer-main: 2` only against a `v0.9.0` or newer RTX 5090
server; against an older one-request-at-a-time server, a client limit of 2 queues the second
request at the server's 30 s timeout. If your `config.yml` still carries the legacy `v0.8.6`
`compaction: asyncEnabled: false` setting, remove it once `maxInFlightRequests` is in place so
compaction summaries run in the background while you read or type.

### Fail-closed check returns a cloud answer

Stop testing. Preserve the command, explicit model ID, overlay identity, and provider/model name
from content-safe output. Do not repeat the request. This violates the qualified route contract and
blocks the release until locally reproduced and fixed.

## Session recovery

### Follow-up replay is cold or resume loses the nonce

Separate transcript correctness from continuation acceleration:

- If the OMP transcript is present and a full replay succeeds, transcript correctness is intact
   even when provider continuation state was not reused.
- If the transcript itself is missing, inspect OMP session selection and `--session-dir` storage
  rather than NInfer.
- If a qualified native Windows RTX 4090 or RTX 3090 process restarted, inspect what its previous
  stop recorded before blaming the session:
  `& "$StateRoot\Control-Release.ps1" -Action Status -StateRoot $StateRoot` reports the live
  endpoint and identity on both lanes, and `$StateRoot\last-stop.json` (`last_stop` in that status
  output) records the previous stop's mode (`stop-event`), whether it finished gracefully within
  the 900 s timeout, and how many live sessions it flushed to checkpoints or refused. On the
  RTX 3090 lane, a managed stop also restores the card's 370 W default power limit from its 300 W
  serving cap. `$StateRoot` is `%ProgramData%\NInfer\qwen38-4090-native` or
  `%ProgramData%\NInfer\qwen38-3090-native`.
- An unplanned reboot or crash is not a managed stop: work that was neither automatically
  checkpointed (past 32,768 frontier tokens) nor flushed by a graceful stop does not survive one,
  and OMP replays from its transcript on the next turn.
- Sessions saved under the historical fork client's `ninfer_session` naming are not addressable by
  stock OMP's `prompt_cache_key` identity; each takes one cold first turn after upgrading and older
  generations age out under the checkpoint quota.
- Endpoint, model, request-shape, branch, or committed-turn identity changes intentionally
  invalidate a provider snapshot.

Report the transition (same turn, OMP resume, tunnel reconnect, or NInfer restart), not private
conversation content.

### Two long sessions and what survives a restart

Current `v0.13.1` continuation and checkpoint recovery are bounded by each lane's qualified device
and host pools:

- **RTX 5090 container lane (`qwen38-5090-v0.13.0`, configuration `751d22dc`):** 146,368-token
  automatic BF16 device KV pool, two requests in flight (`--max-concurrency 2`), 180 s pending
  timeout, two extra device-state slots (`--device-state-slots 2`), a shared 20,867.734375 MiB
  (21,881,405,440-byte) Host context budget, and a 24,576 MiB checkpoint quota under
  `/checkpoints-v013` (`checkpoints-v013` on the host, schema 3,
  `--session-checkpoint-require-origin-auth`). Two requests run concurrently only while both
  prompts plus output reservations fit the 146,368-token pool. Admission saves a session's newest
  turn before evicting it, and checkpoint restore can save and reclaim reproducible resident
  sessions when host capacity is occupied.
- **Native Windows RTX 4090 and RTX 3090 lanes (`qwen38-4090-native-v0.7.0-beta.2` and `qwen38-3090-native-v0.7.0-beta.2`):**
  one request in flight (`concurrency: 1`), 30 s pending timeout, 131,072-token INT8 KV capacity,
  mandatory `--session-checkpoint-require-origin-auth`, a 24,576 MiB checkpoint quota under
  `cache/<release-instance-id>/session-checkpoints-v3` (schema 3, where `<release-instance-id>` is the installed release ID such as `qwen38-4090-native-v0.7.0-beta.2-7a25cd72f490`), and a shared 14,787.734375 MiB
  (15,506,063,360-byte) Host context budget (640 MiB admission headroom, 2 extra device-state
  slots) on RTX 4090 or a shared 11,715.734375 MiB (12,284,837,888-byte) Host context budget (768
  MiB admission headroom, 4 extra device-state slots) on RTX 3090.

Checkpointing remains best effort under live traffic. A crash, power loss, or expired graceful stop
can leave unpublished work unsaved, and if the engine declines a checkpoint restore on startup:

```sh
docker logs omp-ninfer-beta 2>&1 | grep 'restore declined'
# checkpoint restore declined for session <id>: the engine did not accept the checkpointed continuation
```

the declined session is not corrupted: the store remains intact and the session falls back to
re-prefilling from OMP's transcript. For the historical `v0.7.0` two-session restore-decline
diagnosis (`EXP-041`) and the `v0.7.2` restore-reclaim update (`EXP-047`), see
[`docs/RELEASES.md`](RELEASES.md#v070-public-release-two-long-sessions-keep-their-reuse) and
[`v0.7.2`](RELEASES.md#v072-historical-public-release-bounded-checkpoint-backed-restore-reclaim).

### Two long sessions alternate and each one re-prefills from scratch

When alternating long sessions repeatedly re-prefill from root, the cause is device or host KV
pool pressure rather than a lost OMP session. Active requests on the RTX 5090 share its
146,368-token automatic BF16 device KV pool across at most two requests in flight (180 s pending timeout),
while inactive resident continuations sit in the lane's host store (`20,867.734375 MiB` /
`21,881,405,440-byte` shared Host context budget on RTX 5090, `14,787.734375 MiB` /
`15,506,063,360-byte` shared Host budget on native RTX 4090, and `11,715.734375 MiB` /
`12,284,837,888-byte` shared Host budget on native RTX 3090; native
lanes serve one request at a time with a 30 s pending timeout). In the carried RTX 5090
multisession control, 2 of 8 continuations and forks fell back to root prefill without server
errors; universal warm reuse is not guaranteed.

Inspect `cache.host_kv` and `cache.private_evictions` in `GET /v1/ninfer/status`: occupancy near
capacity alongside rising eviction counts indicates that alternating sessions exceed the pool and
are evicting each other between turns. Single-session workflows and sessions that fit within the
lane's pool are unaffected.

Do not change `--host-kv-mib` or `--kv-dtype` on a published profile, and do not downgrade to
`v0.6.10`: editing server flags invalidates the release configuration SHA-256 (which the launcher
and controller refuse), and `v0.6.10` and earlier RTX 4090 packages are unsupported on the two-GPU
host. For the historical 8 GiB Host KV pool diagnosis (`EXP-039`) and the `v0.7.0` move to the
16 GiB pool, see
[`docs/RELEASES.md`](RELEASES.md#v070-public-release-two-long-sessions-keep-their-reuse).

## Reporting safely

### Safe issue material

Include release and profile IDs, public component hashes, OS/GPU/driver/Docker/OMP versions, step
name, and a redacted error. Exclude API keys, SSH configuration, usernames, hostnames, IP
addresses, private paths, prompts, model output, raw JSONL, session files, and unredacted Docker or
host inspection dumps.
