# Troubleshooting

Fix the first concrete mismatch. Do not rerun an unchanged install or replace an immutable identity
with a convenient local image.

## `release manifest is not installable`

Use a clean clone of the current public release tag and run
`python3 scripts/verify_release.py --require-ready`. Moving `main`, an older tag, or a partially
published candidate is not installable. A draft/candidate intentionally retains explicit blockers;
do not fill missing component identities from a local cache.

## Model byte count or SHA-256 mismatch

The only supported artifact is the URL, revision, byte count, and hash in the ready manifest.

1. Keep the failed file out of the final model path.
2. Check available disk space and whether the download was interrupted.
3. Resume the same pinned URL with `curl --continue-at -`.
4. Re-run both byte-count and SHA-256 checks.

Do not select a file by modification time or use another Qwen/NInfer artifact with the same display
name.

## NInfer image or binary mismatch

The image reference must contain `@sha256:`. A binary mismatch means the image bytes do not match the
qualified release, even if its mutable tag looks correct. Preserve the expected/actual hashes,
remove no unrelated images, and report the release/profile plus those two content-safe values.

## `container already exists: omp-ninfer-beta`

Inspect the existing container before changing it:

```sh
docker ps -a --filter name='^/omp-ninfer-beta$'
docker logs --tail 100 omp-ninfer-beta
```

If it was created by this release, use `examples/manual-tunnel/stop-ninfer.sh`; that script refuses
unexpected ownership labels. If labels do not match, do not stop or remove it through the release
script.

## GPU is unavailable inside Docker

Establish the failure at the smallest boundary:

```sh
nvidia-smi
docker run --rm --gpus all nvidia/cuda:13.1.2-runtime-ubuntu24.04 nvidia-smi
```

The first command checks the host driver. The second checks Docker/NVIDIA Container Toolkit. Fix that
boundary before starting the 18.2 GB model. Do not infer RTX 5090 support from a host-only
`nvidia-smi` result.

## Port `18089` is occupied

On the inference host, identify the loopback listener before stopping anything. On the Mac,
`open-tunnel.sh` exits because `ExitOnForwardFailure=yes`. The primary profile fixes port `18089`;
do not silently change one side because the profile/configuration identity and OMP provider would
diverge.

## NInfer never becomes ready

Model load can take several minutes. The launcher waits up to 900 seconds, then leaves the owned
container for diagnosis:

```sh
docker ps -a --filter name='^/omp-ninfer-beta$'
docker logs --tail 200 omp-ninfer-beta
```

Common first failures are insufficient GPU memory, the NVIDIA runtime not being available, model
mount/permission errors, or an identity mismatch. Do not restart unchanged input. Correct the named
cause, stop the owned container, then start once.

## The server logs that it is listening but the port is unreachable

Fixed in `v0.6.3`, and worth knowing if you are on an older clone. Up to `v0.6.2` the launcher
ran its container with `--network host` and the server bound `127.0.0.1:18089`. On Docker Desktop
that namespace belongs to the engine VM, not to your machine: the server really is listening, and
neither Windows nor the WSL2 distro can reach it. The launcher named this
`wsl-mirrored-loopback-unavailable` and told you to run `wsl --shutdown` and restart Docker
Desktop, which does not change the outcome - measured twice on the maintainer host on 2026-09-11,
with a second host-network container reaching the same port from inside the VM
([EXP-031](measurements/2026-09-11-rtx5090-public-route-qualification.json),
[#15](https://github.com/alphastorm/omp-ninfer/issues/15)).

The route now publishes the container's port on the inference host's loopback, which is reachable
from both. Update to the current release rather than changing ports or bind addresses by hand:
the profile's identity covers them, and the launcher refuses a configuration that is not the one
the release records.

## Docker credential helper fails over non-interactive SSH

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

## Authenticated status returns `401`

The Mac and inference host must contain the same single-line key. Check file existence and mode
without printing content:

```sh
stat -c '%a %s %n' "$HOME/.config/omp-ninfer/api-key"   # inference host
stat -f '%Lp %z %N' "$HOME/.omp/agent/ninfer-beta.key" # macOS
```

Both files must deny group/other access. Re-copy through SSH if their sizes differ. Never include the
key in a diagnostic command, screenshot, issue, or shell trace.

## Tunnel connects but OMP cannot reach NInfer

- Keep `open-tunnel.sh` running on the Mac.
- Confirm the SSH destination terminates in the Linux/WSL namespace owning Docker.
- Confirm the container status is healthy and remote `127.0.0.1:18089` is listening.
- Confirm Mac port `18089` is not occupied by another process.
- Confirm `models.yml` uses `http://127.0.0.1:18089/v1` and `q38-ninfer`.

Do not point OMP at a remote LAN address as a workaround.

## OMP cannot resolve `ninfer-beta/local-max`

Validate that `~/.omp/agent/models.yml` remains valid YAML and contains exactly one
`providers.ninfer-beta` mapping. If the file existed before setup, merge the fragment rather
than nesting a second `providers:` key or overwriting other providers. Keep both provider- and
model-level `ninferStatefulResponses: true` fields.

Install or merge the fail-closed `retry` mapping into the launcher-owned default config, then run
the exact route:

```sh
install -m 600 examples/manual-tunnel/fail-closed.yml "$HOME/.omp/agent/config.yml"
omp --model ninfer-beta/local-max
```

## Text works but image input fails

The ready status must identify the qualified profile, and the launch arguments must include
`--vision`. NInfer rejects media when Vision was omitted at process start; it cannot be enabled by a
later request. Also check that the image is a supported, readable local file and that OMP did not
block images in another config overlay.

## Follow-up replay is cold or resume loses the nonce

Separate correctness from acceleration:

- If the OMP transcript is present and a full replay succeeds, transcript correctness is intact but
  provider state was not reused.
- If the transcript itself is missing, inspect OMP session selection/storage rather than NInfer.
- If a qualified native Windows RTX 3090 or RTX 4090 process restarted, inspect what its stop
  recorded before blaming the session: `& "$StateRoot\Control-Release.ps1" -Action Status
  -StateRoot $StateRoot` reports the live endpoint and identity on both lanes, and on the RTX 4090
  lane `$StateRoot\last-stop.json` (`last_stop` in that status) records the previous stop's mode,
  whether it was graceful, and how many sessions it saved or refused. `$StateRoot` is the lane's
  state root under `%ProgramData%\NInfer`. A reboot or a crash is not a managed stop: a session
  that was never published does not survive one. OMP must still remain able to replay its
  transcript when acceleration state is unavailable or invalid.
- Endpoint, model, request-shape, branch, or committed-turn identity changes intentionally invalidate
  a provider snapshot.

Report the transition (same turn, OMP resume, tunnel reconnect, or NInfer restart), not private
conversation content.

## Two long sessions alternate and each one re-prefills from scratch

This is the Host KV pool, not a lost session. Every session that stays resident holds its KV in
that pool; when the pool cannot hold them all, a turn on one session evicts the other's endpoint
and the next continuation re-prefills from root. Measured on the RTX 5090 container profile: two
126,000-token `bf16` sessions lose half their continuations at a 12 GiB pool and all of them at
the shipped 8 GiB pool, while two 75,000-token sessions at 8 GiB lose none
([EXP-039](measurements/2026-09-13-hostkv-capacity-multisession.json)).

Check `cache.host_kv` and `cache.private_evictions` in `GET /v1/ninfer/status`: occupancy near
capacity with a rising eviction count is this, and a single session is unaffected either way.
Budget roughly 4.2 GB per 126K-token session on `bf16` and about 2.5 GB on `--kv-dtype int8`, then
either raise `--host-kv-mib` until the pool holds every session you keep open, or run the profile
on INT8 KV. Both are launch-time changes to a profile you build yourself: the published profiles
ship the qualified values, and changing either one leaves the qualified envelope.

## Fail-closed check returns a cloud answer

Stop testing. Preserve the command, explicit model ID, overlay identity, and provider/model name from
content-safe output. Do not repeat the request. This violates the qualified route contract and blocks the
release until locally reproduced and fixed.

## Safe issue material

Include release/profile IDs, public component hashes, OS/GPU/driver/Docker/OMP versions, step name,
and a redacted error. Exclude API keys, SSH configuration, usernames, hostnames, IP addresses,
private paths, prompts, model output, raw JSONL, session files, and unredacted Docker inspection.
