# Troubleshooting

Oh My Pi (coding-agent client) → OMP NInfer (qualified appliance and release layer) → NInfer
(inference engine) → Qwen3.8 27B (served model).

Run the preflight below, or find the first error you saw, and fix that one mismatch. Do not rerun
an unchanged install, and do not replace a pinned artifact with a local image or a modified
profile. Release identities are in [the current release](FACTS.md#current-release); per-lane
limits are in [lanes and limits](FACTS.md#lanes-and-limits).

## Named-cause preflight

Run `python3 scripts/doctor.py --offline --json` from your clone for a check that needs no host,
or use the [quickstart doctor command](QUICKSTART.md#contributor-acceptance-and-preflight) on the
inference host before starting its lane. Each failure has a stable check name, a cause, and a
remediation. The JSON never includes bearer values, local filenames, GPU UUIDs, or raw command
output. Exit `1` means a check failed. Offline exit `0` means the selected local checks passed,
not that a GPU host was checked. Doctor receipts are preflight, never release qualification.

- **`docker_reachability`, `wsl2_reachability`, `docker_bind_mounts`:** Start the WSL2 distro that
  holds the model, enable its Docker Desktop integration, and restart Docker Desktop while the
  distro is running. Run the check in that distro for Linux paths. The probe uses the pinned image
  with `--pull=never` and read-only mounts: it downloads no image and neither starts nor stops an
  existing container. The launcher remains authoritative for checkpoint-directory staging.
- **`docker_network_mode`, `container_network`:** Use bridge publication `127.0.0.1:18089:8080`,
  not `--network host`. Docker Desktop's host network is the engine VM, not the Windows loopback
  endpoint, so a server on it is unreachable from Windows and WSL2. `start-ninfer.sh` runs the
  server on Docker `bridge` (`--host 0.0.0.0 --port 8080` inside the container) and publishes that
  port on the inference host's loopback (`--publish 127.0.0.1:18089:8080`), which both Windows and
  WSL2 reach. Do not edit ports or bind addresses by hand: the profile's configuration SHA-256
  covers them, and the launcher refuses any modified profile.
- **`loopback_bind`, `loopback_port_free`, `loopback_reachability`:** The container route uses port
  `18089`; the two native lanes share `18082` and run one at a time. Inspect the listener's owner
  rather than killing an unknown process ([occupied ports](#port-18089-is-occupied)). `--running`
  checks an existing listener and connectivity; it does not claim that the service behind the port
  has the right runtime identity.
- **`driver_floor`, `gpu_selection`:** Update the host NVIDIA driver, or select the intended card
  with `--gpu-uuid`. Native driver floors come from the package release spec; the container uses a
  declared profile floor or CUDA 13's major compatibility floor of 580. The floor is a
  prerequisite, not a claim that every driver above it was qualified.
- **`ram_total_mib`, `ram_free_mib`, `vram_total_mib`, `vram_free_mib`:** Floors come from the
  selected profile, and a total RAM or VRAM floor is not reinterpreted as a free-memory floor.
  Before startup, available RAM must at least back the profile's shared Host budget
  ([glossary](FACTS.md#glossary)) unless the profile declares a separate free-RAM floor. Free VRAM
  is reported; a free-VRAM gate applies only when the profile declares one. `--running` does not
  demand that memory NInfer already holds be free. For a WSL RAM shortage, raise the `[wsl2]`
  setting `memory=32GB` in `%UserProfile%\.wslconfig`, then shut down WSL and restart Docker, only
  during an owner-approved window.
- **`model_file`, `model_bytes`, `model_sha256`, `omp_hash`, `bearer_permissions`:** Use the pinned
  model artifact and the stock client, opt into full model hashing with `--hash-model`, and keep
  the bearer file owner-only. POSIX files must be owned by you with no group or world access;
  native Windows uses a protected owner, SYSTEM, and Administrators ACL. Do not paste keys into
  reports.

Doctor does not install, repair, stop production, change firewall rules, or grant permission for a
maintenance window. Run it again only after fixing the named cause. `verify_release.py` rejects a
contributor's `rehearsal` acceptance receipt on purpose; obtain owner-run live and release-gate
evidence instead of relabeling the receipt.

## Release and identity

### `release manifest is not installable`

You are on moving `main`, an older tag, or a partially staged manifest. Use a clean clone of the
[current release](FACTS.md#current-release) tag
([before you start](QUICKSTART.md#before-you-start)) and run
`python3 scripts/verify_release.py --require-ready`. A `draft` or `candidate` manifest keeps
explicit blockers; do not fill missing component identities from a local cache.

### Model byte count or SHA-256 mismatch

All three lanes serve one model artifact: `components.model` in the release manifest, downloaded
to `qwen3_8_27b-v3.ninfer` ([models](FACTS.md#models)). A mismatch means the download was
interrupted or a different `.ninfer` file sits at that path.

1. Keep the failed file out of the final model path.
2. Confirm whether the file is a different artifact or an interrupted download, and check the
   available disk space.
3. Resume the pinned `components.model` URL with `curl --continue-at -` (`curl.exe --continue-at -`
   on Windows), as in
   [prepare the model](QUICKSTART.md#3-prepare-the-model-and-key-on-the-inference-host).
4. Run both the byte-count check and the SHA-256 check again.

Do not select a file by modification time, and do not use another `.ninfer` file that has the same
filename.

### NInfer image or binary mismatch

The local image, binary, or package bytes do not match the
[current release](FACTS.md#current-release), even if a mutable tag or a filename looks correct.
The container image reference must contain `@sha256:`.

Keep the expected and the actual SHA-256 values, remove no unrelated images, and report the
release and profile IDs together with those two content-safe digests.

## Download and startup

### `container already exists: omp-ninfer-beta`

Inspect the existing container before changing it:

```sh
docker ps -a --filter name='^/omp-ninfer-beta$'
docker logs --tail 100 omp-ninfer-beta
```

If this release created it, run `examples/manual-tunnel/stop-ninfer.sh`; that script refuses
unexpected ownership labels. If the labels do not match, do not stop or remove the container
through the release script.

### The container exists but will not start after a host reboot

Docker Desktop stages a container's bind mounts when the container is created, from the
filesystem those paths live on. Restarting that filesystem's WSL distro replaces the staging, and
every host reboot restarts it, because nothing starts a WSL distro at boot. The container that was
created against the old staging cannot use it again. The failure takes one of two shapes:

```sh
docker start omp-ninfer-beta
# Error response from daemon: ... error mounting
# ".../docker-desktop-bind-mounts/<distro>/<hash>" to rootfs at
# "/models/qwen3_8_27b.ninfer": ... not a directory
docker container inspect omp-ninfer-beta --format '{{.State.ExitCode}} {{.RestartCount}}'
# 127 0
```

- **Exit `127` with `RestartCount 0`:** Docker did not retry and will not. A restart policy cannot
  fix a mount that Docker cannot stage.
- **The container starts with empty file mounts:** The server rejects its own empty key file,
  prints usage text, and exits `1`. With a restart policy, `docker ps` then shows `restarting`
  while the logs show usage text rather than an error.

Recreate the container instead of running `docker start`. Checkpoints live in the host store
directory, not in the container, so recreation continues the sessions that store holds:

```sh
./examples/manual-tunnel/stop-ninfer.sh
./examples/manual-tunnel/start-ninfer.sh --model ... # the same arguments as the first launch
```

`start-ninfer.sh` proves the mounts inside a throwaway container before it loads the model, so it
refuses a still-broken engine and reports what that container saw instead of entering a crash
loop. If it refuses, start the WSL distro that owns the paths, restart Docker Desktop while that
distro is running, and retry: the engine stages only a distro it saw when it initialized.

### `needs N MiB of runtime-host memory; this host offers M MiB`

`start-ninfer.sh` reads the runtime-host memory floor from the RTX 5090 profile
(`runtime_host.minimum_runtime_memory_mib`, 28,672 MiB) and compares it with `MemTotal` inside a
throwaway container. It refuses before loading the model.

On Docker Desktop the container sees the WSL2 utility VM, which takes half the machine's RAM by
default; every distro and the engine share that one VM. Raise the VM's memory in
`%UserProfile%\.wslconfig`, then shut down WSL and restart Docker, only during an owner-approved
window:

```ini
[wsl2]
memory=32GB
```

```sh
wsl --shutdown
```

The launcher refuses because an under-provisioned host does not degrade gracefully: the server is
OOM-killed mid-request. To see whether an earlier container died that way:

```sh
docker container inspect omp-ninfer-beta --format '{{.State.ExitCode}} {{.State.OOMKilled}}'
# 137 true
dmesg | grep -i 'out of memory'
# Out of memory: Killed process 2347 (ninfer-serve) total-vm:85995096kB ...
```

Do not lower `--host-context-mib` by hand. Changing profile arguments invalidates the
configuration SHA-256 and leaves the qualified envelope.

### GPU is unavailable inside Docker

Find the layer that fails:

```sh
nvidia-smi
docker run --rm --gpus all nvidia/cuda:13.1.2-runtime-ubuntu24.04 nvidia-smi
```

The first command checks the host driver. The second checks Docker and the NVIDIA Container
Toolkit. Fix the layer that fails before you start the model. Do not infer container GPU access
from a host-only `nvidia-smi` result.

### NInfer never becomes ready

Model load can take several minutes. The container launcher waits up to 900 seconds, then leaves
the container it owns in place for diagnosis:

```sh
docker ps -a --filter name='^/omp-ninfer-beta$'
docker logs --tail 200 omp-ninfer-beta
```

Common first failures are insufficient GPU memory (or another process holding VRAM), an
unavailable NVIDIA container runtime, model mount or permission errors, and an identity mismatch.

On the native Windows lanes (`rtx4090-windows-native` and `rtx3090-windows-native`), the startup
check also refuses an active interactive GPU owner, such as Desktop Window Manager or an overlay
above the idle threshold, and a GPU lease held by the sibling native lane. Read the lane's state
with `& "$StateRoot\Control-Release.ps1" -Action Status -StateRoot $StateRoot`, where `$StateRoot`
is `%ProgramData%\NInfer\qwen38-4090-native` or `%ProgramData%\NInfer\qwen38-3090-native`
(quickstart: [RTX 4090](QUICKSTART.md#operate-the-native-lane),
[RTX 3090](QUICKSTART.md#operate-the-rtx-3090-native-lane)).

Correct the named cause, stop the container (`./examples/manual-tunnel/stop-ninfer.sh`) or the
native lane (`Control-Release.ps1 -Action Stop -StateRoot $StateRoot`), and start once.

### Docker credential helper fails over non-interactive SSH

`docker pull` can fail with `error getting credentials … A specified logon session does not
exist` when Docker Desktop's Windows credential helper runs inside a non-interactive SSH session,
even for anonymous public pulls. Point `DOCKER_CONFIG` at an empty configuration for the launcher
invocation:

```sh
DOCKER_CONFIG=$(mktemp -d)
printf '{}\n' > "$DOCKER_CONFIG/config.json"
export DOCKER_CONFIG
```

This bypasses only the credential lookup; digest pinning and hash verification are unchanged.

## Network and authentication

<a id="managed-mac-tunnel-preview"></a>

### Managed Mac tunnel is in backoff or fails the endpoint check

Run both checks as the logged-in Mac user, without sudo:

- `python3 scripts/mac_tunnel.py status` distinguishes a stopped LaunchAgent, a starting
  supervisor, a connecting SSH process, and exponential backoff. A `listener_owned` value of
  `true` means the current supervisor's SSH child owns only the selected `127.0.0.1` listener; it
  does not prove that the remote server is ready.
- `python3 scripts/doctor.py --mac-tunnel --json` checks the existing private bearer file and
  authenticated `/v1/models` over that listener. It never probes Docker, WSL, or the GPU, and it
  never promotes the macOS preview route.

Then fix the case that matches:

- **SSH exits repeatedly:** Verify the explicit user@hostname or IP and the host key interactively
  with `ssh -F /dev/null USER@RUNTIME_HOST`. Managed SSH ignores configuration aliases and
  requires unattended authentication; supply an existing `--identity-file PATH` during install if
  needed. A passphrase key that works only with a terminal's agent may not work in the GUI launchd
  environment. The helper suppresses raw SSH output to avoid collecting private connection
  information, so use your interactive SSH session to diagnose the authentication failure. Do not
  disable host-key checking or paste credentials into a command.
- **The local port is occupied:** Stop only your own manual tunnel or conflicting process. The
  helper never kills a foreign listener; SSH exits and retries with capped backoff.
- **SSH owns the listener but the endpoint check fails:** Check the existing bearer file
  (owner-only permissions, nonempty, not a symlink), Windows loopback publication, and remote
  service readiness. No cloud provider or alternate port is substituted.
- **launchd cannot find the pinned Python executable after an upgrade:** Reinstall using a stable
  Python 3 path.

`stop` unloads and disables the agent, even across future logins; `start` enables it again. Stop
before reinstalling to change the destination or to refresh the installed interpreter or helper.
`uninstall` retains credentials and client settings. The private `status.json` snapshots and
`runtime.json` in `~/Library/Application Support/omp-ninfer/tunnel` contain transport state only;
stale runtime from a different supervisor PID is not treated as readiness.

<a id="port-18089-is-occupied"></a>

### Port `18089` or `18082` is occupied

- **RTX 5090 inference host:** Identify the loopback listener on `127.0.0.1:18089` before stopping
  anything.
- **Mac:** `open-tunnel.sh` exits immediately when local port `18089` is taken, because it passes
  `ExitOnForwardFailure=yes`. Stop your own stale tunnel or the conflicting local process.
- **Two-GPU native Windows host:** The RTX 4090 and RTX 3090 lanes share `127.0.0.1:18082`, and
  only one may run at a time. Stop the active lane with
  `Control-Release.ps1 -Action Stop -StateRoot $StateRoot` before starting the other.

Do not silently change a port on one side: the profile's configuration identity and the Oh My Pi
provider URL must match.

### Authenticated status returns `401`

The client and the inference runtime must read the same single-line UTF-8 bearer key.

On the RTX 5090 container and macOS route, check file existence, permissions, and byte length
without printing the secret:

```sh
stat -c '%a %s %n' "$HOME/.config/omp-ninfer/api-key"   # inference host (WSL2/Linux)
stat -f '%Lp %z %N' "$HOME/.omp/agent/ninfer-beta.key" # macOS client
```

Both files must be mode `600` (no group or other permissions) and match in byte length. Copy the
key again over SSH if they differ.

On a native Windows client, confirm that the current PowerShell session loaded the key before it
invoked `omp.exe` ([Windows client setup](QUICKSTART.md#native-windows-omp)):

- **RTX 5090 local route:** `$env:NINFER_BETA_API_KEY` from `$HOME\.omp\agent\ninfer-beta.key`.
- **Native RTX 4090 and RTX 3090 routes:** `$env:NINFER_NATIVE_API_KEY` from
  `%ProgramData%\omp-ninfer-keys\api-key.txt`.

Never print the key in a diagnostic command, screenshot, issue, or shell trace.

### Tunnel connects but OMP cannot reach NInfer

Check each hop in order:

1. Keep `examples/manual-tunnel/open-tunnel.sh` running in its own terminal on the Mac.
2. Confirm that Mac port `18089` is not occupied by a stale SSH tunnel or another local process.
3. Confirm that the SSH destination reaches the host or WSL2 environment where Docker published
   `127.0.0.1:18089`.
4. Confirm that `omp-ninfer-beta` is running and that remote `127.0.0.1:18089` answers `/health`.
5. Confirm that `~/.omp/agent/models.yml` uses `http://127.0.0.1:18089/v1` and model ID
   `q38-ninfer`.

Do not point Oh My Pi at a remote LAN or tailnet IP address as a workaround.

## Client configuration

### OMP cannot resolve `ninfer-beta/q38-ninfer`

1. Confirm that `~/.omp/agent/models.yml` is valid YAML and contains a single `providers` mapping
   with your lane's provider entry:
   - `ninfer-beta` with model `q38-ninfer`, from `examples/manual-tunnel/models.fragment.yml` or
     `examples/windows-docker-local/models.fragment.yml`;
   - `ninfer-native-4090` with model `qwen3.8-27b`, from
     `examples/windows-native/models.fragment.yml`; or
   - `ninfer-native-3090` with model `q38-ninfer`, from
     `examples/windows-native/models-rtx3090.fragment.yml`.

   If `models.yml` existed before setup, merge the provider block rather than nesting a second
   `providers:` key or overwriting other providers.
2. Keep `compat.statefulResponses: true` under each NInfer model entry; stock Oh My Pi ignores the
   retired fork-only `ninferStatefulResponses` key. Unset `PI_OPENAI_STATEFUL` in the environment
   (`unset PI_OPENAI_STATEFUL` on POSIX, or
   `Remove-Item Env:PI_OPENAI_STATEFUL -ErrorAction SilentlyContinue` in PowerShell) so that an
   inherited `0` cannot disable Responses chaining.
3. Install the fail-closed configuration as `~/.omp/agent/config.yml`. As in
   [add the OMP provider](QUICKSTART.md#7-add-the-omp-provider), the block below leaves an
   identical file in place and refuses to replace a `config.yml` that differs. If it refuses,
   merge `examples/manual-tunnel/fail-closed.yml` into your file. On Windows, follow
   [Windows client setup](QUICKSTART.md#native-windows-omp) instead.

```sh
unset PI_OPENAI_STATEFUL
if [ ! -e "$HOME/.omp/agent/config.yml" ]; then
  install -m 600 examples/manual-tunnel/fail-closed.yml "$HOME/.omp/agent/config.yml"
elif ! cmp -s examples/manual-tunnel/fail-closed.yml "$HOME/.omp/agent/config.yml"; then
  echo 'existing ~/.omp/agent/config.yml differs; merge fail-closed.yml instead of overwriting it' >&2; false
fi
```

Then run the explicit provider and model route from the same shell:
`omp --model ninfer-beta/q38-ninfer`.

### Text works but image input fails

On a native lane this is by design. The native Windows RTX 4090 and RTX 3090 lanes run with
`vision: false` (`input: [text]` in their Oh My Pi model fragments) and reject image inputs.
Vision is qualified only on the RTX 5090 container lane, which launches `ninfer-serve` with
`--vision` and declares `input: [text, image]` in its fragments
([lanes and limits](FACTS.md#lanes-and-limits)).

On the RTX 5090 lane, verify three things:

- `/v1/ninfer/status` reports the `deployment_profile` and `config_sha256` of the
  [current release](FACTS.md#current-release);
- the image path is a readable local file; and
- no local Oh My Pi configuration overlay stripped `image` from the model's `input` list.

### A long RTX 5090 session fails when OMP compacts it

```text
400 only input_image detail 'auto' is supported
```

Oh My Pi compacts a 131,072-token session automatically at about 111,412 tokens. On vision-capable
models, its first compaction method archives earlier turns as images, and NInfer accepts only
`detail: "auto"` for them. Stock Oh My Pi defaults custom and local OpenAI Responses endpoints to
`detail: "auto"` for both live image turns and replayed compaction images (upstream
[#13687](https://github.com/can1357/oh-my-pi/pull/13687)), so the shipped model fragments need no
image-detail override.

If you see this error, verify that `omp --version` reports the client version of the
[current release](FACTS.md#current-release) ([client setup](QUICKSTART.md#omp-18186-client)) and
that your `models.yml` matches the shipped RTX 5090 fragment. The text-only native RTX 4090 and
RTX 3090 lanes never compact sessions into images. The workaround for older clients is in the
[notes at the end of this page](#measurements-and-incidents-behind-these-entries).

### A turn fails with `request_queue_timeout` late in a long session

```text
503 inference request expired while waiting for admission
```

A request that arrives when a lane is full waits at the server and expires if admission takes
longer than the lane's pending timeout. The RTX 5090 and RTX 3090 lanes serve two requests in
flight with a 180 s pending timeout (`--pending-timeout-ms 180000`); the RTX 4090 lane serves one
request at a time with a 30 s pending timeout ([lanes and limits](FACTS.md#lanes-and-limits)).

By default, Oh My Pi writes its compaction summary in a background request as a session approaches
the compaction threshold. Without a client-side concurrency cap, your next interactive turn queues
behind that background request at the server and expires there.

`examples/manual-tunnel/fail-closed.yml` caps every NInfer provider at its lane's concurrency, so
Oh My Pi holds any excess request locally, with no deadline, until an in-flight request completes
([EXP-074](measurements/2026-09-29-long-session-cache.json),
[EXP-077](measurements/2026-09-29-rtx5090-two-requests-in-flight.json)). If you merged an older
`~/.omp/agent/config.yml`, add the complete `providers.maxInFlightRequests` map:

```yaml
providers:
  maxInFlightRequests:
    ninfer-beta: 2
    ninfer-native-4090: 1
    ninfer-native-3090: 2
    ninfer-main: 2
    ninfer-heavy: 1
```

Include every provider ID you route to a NInfer lane; Oh My Pi leaves any provider omitted from
the map unlimited.

### Fail-closed check returns a cloud answer

Stop testing, and do not repeat the request. A cloud answer on an explicit local route violates
the qualified route contract. Keep the command, the explicit model ID, the local Oh My Pi
configuration that was in effect, and the provider and model name from content-safe output, then
report it as a release defect with [safe issue material](#safe-issue-material).

## Session recovery

### Follow-up replay is cold or resume loses the nonce

A follow-up turn prefills the whole prompt again, or a resumed session cannot recall the nonce
from an earlier turn. Separate transcript correctness from continuation acceleration: Oh My Pi's
transcript is the source of truth, and [retained state](FACTS.md#glossary) only speeds up the
next turn.

- **The transcript is present and a full replay succeeds:** Transcript correctness is intact, even
  when provider continuation state was not reused.
- **The transcript itself is missing:** Inspect Oh My Pi session selection and `--session-dir`
  storage rather than NInfer.
- **A native Windows RTX 4090 or RTX 3090 process restarted:** Inspect what its previous stop
  recorded before blaming the session.
  `& "$StateRoot\Control-Release.ps1" -Action Status -StateRoot $StateRoot` reports the live
  endpoint and identity, and `$StateRoot\last-stop.json` (`last_stop` in that status output)
  records the previous stop's mode (`stop-event`), whether it finished gracefully within the 900 s
  timeout, and how many live sessions it flushed to checkpoints or refused. On the RTX 3090 lane,
  a managed stop also restores the card's 370 W default power limit from its 350 W serving cap.
  `$StateRoot` is `%ProgramData%\NInfer\qwen38-4090-native` or
  `%ProgramData%\NInfer\qwen38-3090-native`.
- **The host rebooted or the server crashed:** That is not a managed stop. Work that was neither
  checkpointed automatically (past 32,768 frontier tokens) nor flushed by a graceful stop does not
  survive it, and Oh My Pi replays from its transcript on the next turn.
- **The session was saved under the historical fork client's `ninfer_session` naming:** Stock
  Oh My Pi's `prompt_cache_key` identity cannot address it. Each such session takes one cold first
  turn after the upgrade, and older generations age out under the checkpoint quota.
- **The endpoint, model, request shape, branch, or committed-turn identity changed:** Such a change
  invalidates a provider snapshot by design.

Report the transition (same turn, Oh My Pi resume, tunnel reconnect, or NInfer restart), not
private conversation content.

<a id="two-long-sessions-and-what-survives-a-restart"></a>

### A session re-prefills from scratch after a server restart

Checkpointing is best effort under live traffic, and a checkpoint restores only on the same
runtime, model, profile, and key ([durability](FACTS.md#durability)). After a restart, a session
prefills again from Oh My Pi's transcript in these cases:

- **A crash, power loss, or expired graceful stop:** Any of them can leave unpublished work
  unsaved. On native Windows, `$StateRoot\last-stop.json` records what the previous stop flushed
  ([cold replay](#follow-up-replay-is-cold-or-resume-loses-the-nonce)).
- **An upgrade that replaced the runtime:** The new runtime writes its own checkpoint store and
  does not restore an earlier one ([operating rules](FACTS.md#operating-rules)). Let Oh My Pi
  replay its transcript for a fresh session. Keep native `previous_release` roots untouched for
  `Control-Release.ps1 -Action Rollback -StateRoot $StateRoot`
  ([package selection and fallback](QUICKSTART.md#package-selection-and-fallback)).
- **The engine declined the restore on startup:** The declined session is not corrupted. The store
  remains intact and the session falls back to prefilling from Oh My Pi's transcript.

```sh
docker logs omp-ninfer-beta 2>&1 | grep 'restore declined'
# checkpoint restore declined for session <id>: the engine did not accept the checkpointed continuation
```

### A second long session evicts the first

Two requests run concurrently on the RTX 5090 and RTX 3090 lanes only while both prompts plus
their output reservations fit the lane's token pool; the RTX 4090 lane serves one request at a
time ([lanes and limits](FACTS.md#lanes-and-limits)). Under context pressure, admission saves a
session's newest turn before evicting it. It also gives up to 4 waiting new requests a bounded
turn window between eviction and restore operations, so that resumed and warm sessions are not
starved (upstream [#434](https://github.com/Neroued/ninfer/issues/434),
[ninfer#102](https://github.com/alphastorm/ninfer/issues/102)).

An evicted session returns through checkpoint restore or transcript replay; its Oh My Pi
transcript is intact. Single-session work and sessions that fit within the lane's pool are
unaffected.

### A checkpoint save is refused

NInfer waits for an active prefill or decode pass to finish before it prepares a checkpoint. When
the host RAM cache is full, it reclaims cache entries that are already checkpointed or falls back
to GPU-staged checkpoint export
([ninfer#89](https://github.com/alphastorm/ninfer/issues/89)). Each lane's checkpoint store has a
24,576 MiB quota.

- **Disk capacity, I/O error, or superseded session tag:** On the RTX 5090 and RTX 3090 lanes,
  these retryable memory-pressure refusals stop after six retries or 10 seconds. NInfer then logs
  one `pressure` / `abandoned` checkpoint record and releases the continuation
  ([ninfer#122](https://github.com/alphastorm/ninfer/pull/122)). The RTX 4090 package does not
  have that bound ([differences between lanes](FACTS.md#differences-between-lanes)).
- **Store quota:** A store-quota refusal settles on the first refusal, without retries.

Keep the 40 GiB free-disk margin on the volume that holds the install and the checkpoint store, so
that saves are not refused for disk capacity. When a continuation is released, Oh My Pi replays
its transcript on the next turn.

### Two long sessions alternate and each one re-prefills from scratch

When alternating long sessions repeatedly prefill from root, the cause is device or host pool
pressure, not a lost Oh My Pi session. Active requests share the lane's device KV pool, and
inactive resident continuations sit in the lane's shared Host budget
([lanes and limits](FACTS.md#lanes-and-limits)).

Inspect `cache.host_kv` and `cache.private_evictions` in `GET /v1/ninfer/status`. Occupancy near
capacity alongside rising eviction counts means that the alternating sessions exceed the pool and
evict each other between turns. Single-session workflows and sessions that fit within the lane's
pool are unaffected.

Do not change `--host-context-mib` or `--kv-dtype` on a published profile. Editing server flags
invalidates the release configuration SHA-256, which the launcher and controller refuse.

## Reporting safely

### Safe issue material

Include release and profile IDs, public component hashes, OS/GPU/driver/Docker/OMP versions, step
name, and a redacted error. Exclude API keys, SSH configuration, usernames, hostnames, IP
addresses, private paths, prompts, model output, raw JSONL, session files, and unredacted Docker or
host inspection dumps.

<a id="the-server-logs-that-it-is-listening-but-the-port-is-unreachable"></a>

## Measurements and incidents behind these entries

These dated notes explain why entries above read the way they do. They describe the releases they
name, not the current one.

- **Model byte count or SHA-256 mismatch:** Prior native releases through `v0.13.0` served
  `eec39564` at 18,210,531,328 bytes, which stays in `qwen3_8_27b.ninfer` for historical recovery.
- **`needs N MiB of runtime-host memory; this host offers M MiB`:** The refusal exists because an
  under-provisioned host does not degrade gracefully; in a 24 GiB WSL2 VM the server reached 24,006
  MiB and was OOM-killed mid-request. Do not lower `--host-context-mib` by hand or downgrade to
  `v0.6.10`: changing profile arguments invalidates the configuration SHA-256 and leaves the
  qualified envelope, and `v0.6.10` and earlier releases are unsupported.
- **The server logs that it is listening but the port is unreachable:** Fixed in `v0.6.3`, and
  worth knowing if you are inspecting an older clone. Up to `v0.6.2` the launcher ran its container
  with `--network host` and the server bound `127.0.0.1:18089`. On Docker Desktop that network
  namespace belongs to the utility VM, not to Windows or the WSL2 distro: the server is listening
  inside the VM, and neither Windows nor WSL2 can reach it
  ([EXP-031](measurements/2026-09-11-rtx5090-public-route-qualification.json),
  [#15](https://github.com/alphastorm/omp-ninfer/issues/15)).
- **A long RTX 5090 session fails when OMP compacts it:** **Legacy pre-18.8.7 clients only:** OMP
  compacts a 131,072-token session automatically at about 111,412 tokens. On vision-capable models,
  its first compaction method archives earlier turns as images and older OMP releases requested
  native image resolution (`detail: "original"`), which NInfer refuses. On historical pre-18.8.7
  releases (such as `v0.10.0` / OMP 18.4.10; see [release history](RELEASES.md#version-identities)),
  the workaround was setting `supportsImageDetailOriginal: false` under the RTX 5090 model's
  `compat` mapping.
- **A turn fails with `request_queue_timeout` late in a long session:** Without a client-side
  concurrency cap, your next interactive turn queued behind that background compaction at the
  server, expired repeatedly against the server's admission timeout, and failed once the summary
  outlasted OMP's resends (56-61 s per background handoff on RTX 4090 in
  [EXP-072](measurements/2026-09-28-omp-long-sessions.json)). Keep `ninfer-beta: 2` and
  `ninfer-main: 2` only against a `v0.9.0` or newer RTX 5090 server, and keep
  `ninfer-native-3090: 2` only against `v0.8.0-qwen38-3090-beta.1` (`v0.16.0`) or newer; against an
  older one-request-at-a-time server, a client limit of 2 queues the second request at the server's
  30 s timeout. If your `config.yml` still carries the legacy `v0.8.6`
  `compaction: asyncEnabled: false` setting, remove it once `maxInFlightRequests` is in place so
  compaction summaries run in the background while you read or type.
- **A session re-prefills from scratch after a server restart:** For the historical `v0.7.0`
  two-session restore-decline diagnosis (`EXP-041`) and the `v0.7.2` restore-reclaim update
  (`EXP-047`), see
  [`docs/RELEASES.md`](RELEASES.md#v070-public-release-two-long-sessions-keep-their-reuse) and
  [`v0.7.2`](RELEASES.md#v072-historical-public-release-bounded-checkpoint-backed-restore-reclaim).
- **Two long sessions alternate and each one re-prefills from scratch:** In the carried RTX 5090
  multisession control, 2 of 8 continuations and forks fell back to root prefill without server
  errors; universal warm reuse is not guaranteed. `v0.6.10` and earlier RTX 4090 packages are
  unsupported on the two-GPU host. For the historical 8 GiB Host KV pool diagnosis (`EXP-039`) and
  the `v0.7.0` move to the 16 GiB pool, see
  [`docs/RELEASES.md`](RELEASES.md#v070-public-release-two-long-sessions-keep-their-reuse).

Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.
