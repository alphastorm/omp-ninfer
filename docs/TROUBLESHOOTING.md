# Troubleshooting

Fix the first concrete mismatch. Do not rerun an unchanged install or replace an immutable identity
with a convenient local image.

## `release manifest is not installable`

No installable release exists yet. Wait for the `v0.1.0-beta.1` prerelease and use a clean clone of
that tag. The draft may bind the staged OMP asset and Homebrew revision while marking the asset
unpublished; NInfer OCI/SBOM and qualification publication fields remain null, and explicit
blockers enumerate every incomplete transition.

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
unexpected ownership labels. If labels do not match, do not stop or remove it through the beta
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
`open-tunnel.sh` exits because `ExitOnForwardFailure=yes`. V0.1 fixes port `18089`; do not silently
change one side because the profile/configuration identity and OMP provider would diverge.

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
`providers.ninfer-beta` mapping. If the file existed before beta setup, merge the fragment rather
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
- If the NInfer process restarted, v0.1 does not claim retained process state; OMP must remain able to
  replay its transcript.
- Endpoint, model, request-shape, branch, or committed-turn identity changes intentionally invalidate
  a provider snapshot.

Report the transition (same turn, OMP resume, tunnel reconnect, or NInfer restart), not private
conversation content.

## Fail-closed check returns a cloud answer

Stop testing. Preserve the command, explicit model ID, overlay identity, and provider/model name from
content-safe output. Do not repeat the request. This violates the beta route contract and blocks the
release until locally reproduced and fixed.

## Safe issue material

Include release/profile IDs, public component hashes, OS/GPU/driver/Docker/OMP versions, step name,
and a redacted error. Exclude API keys, SSH configuration, usernames, hostnames, IP addresses,
private paths, prompts, model output, raw JSONL, session files, and unredacted Docker inspection.
