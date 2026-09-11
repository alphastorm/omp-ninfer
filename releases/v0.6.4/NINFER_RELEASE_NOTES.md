# OMP NInfer v0.6.3 - your session survives the process on the route you actually run

The documented RTX 5090 container route now mounts a durable session store. Until this release it
did not: the launcher passed no `--session-checkpoint-dir`, so on the route the quickstart tells
you to run, the explicit save endpoint answered 404 and a continuation after a container restart
answered `previous_response_not_found` - while the server reported the configuration identity of
the checkpointed configuration that had been qualified elsewhere. Both native Windows lanes and
the maintainer's own production already ran with the store enabled; the published route did not.
No component changed: the runtime image, server binary, model and client are v0.6.2's exact bytes.

## What changed

- **The route is durable.** `examples/manual-tunnel/start-ninfer.sh` takes `--checkpoint-dir`,
  prepares it private to you, mounts it at `/checkpoints` under the repository's io_uring seccomp
  profile (pinned by hash), and passes the session-store arguments the qualified configuration
  uses. Measured on the owner appliance: an explicitly saved session survived a full container
  stop - the store held 48 files and 1.74 GB owned by the invoking user at mode 700 with no server
  running - and the continuation returned its marker exactly in 1.17 s with 122 cached input
  tokens, 25.5 s after the server came back. A 5.2 GB session restored in 3.9 s and 3.7 s across
  two verified restarts, and a flipped payload byte was refused.
- **The identity a server reports is the identity of what it is running.** Deployment profile
  `qwen38-5090-v0.6.3`, configuration `622ab621...`. `scripts/verify_release.py` computes that
  identity from the profile exactly as the runtime fork's lifecycle tool computes it, a ready
  release must record it, and the launcher refuses to start when the computed, declared and
  recorded values disagree.
- **The route is reachable.** The container runs on a bridge network and publishes its port on the
  inference host's `127.0.0.1:18089`. A `--network host` bind on Docker Desktop lives in the engine
  VM: the server logs that it is listening and neither Windows nor the WSL2 distro can reach it.
  That is what the old `wsl-mirrored-loopback-unavailable` diagnosis misattributed to WSL
  networking drift; `wsl --shutdown` never fixed it.
- **The route runs as you, with less.** Your own uid/gid, every capability dropped,
  `no-new-privileges`, and the GPU probed inside the pinned image - so the host no longer needs
  `nvidia-smi` on `PATH`, which a WSL2 distro reached over ssh does not have.
- **The profiles say so.** Both container profiles now claim `process-restart-continuation` and
  record the store mount and seccomp identity that make the claim true.

## Evidence route

`docs/measurements/2026-09-11-rtx5090-public-route-qualification.json` holds the window, including
the same sequence measured on the predecessor configuration for comparison; the route's acceptance
is in `acceptance/rtx5090-public-route.json` and the composed acceptance in
`acceptance/composed-external-installation.json`. The component's own anonymous public-URL
acceptance is v0.6.2's, unchanged and carried by hash.

## Upgrading from v0.6.2

Stop the old container with `examples/manual-tunnel/stop-ninfer.sh`, then start the new route with
`--checkpoint-dir` pointing at a local directory you own. Sessions from the old route were never
saved, so there is nothing to migrate; from here they are.

## Known limitations

Unchanged from v0.6.2 otherwise. A crash, a power loss, or a host reboot still loses whatever was
never saved - automatically above 32,768 frontier tokens, or explicitly through
`POST /v1/ninfer/checkpoints`. The RTX 3090 lane keeps the v0.2.5 behaviour, where a managed stop
terminates, until its mainline candidate ships. Sibling branches beyond the first re-materialize
the shared base from host KV.

## Support boundary

Unchanged: one owner-operated machine per lane; one active request per qualified profile;
loopback-only, bearer-authenticated, fail-closed. Checkpoints bind the runtime fingerprint.
Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.
