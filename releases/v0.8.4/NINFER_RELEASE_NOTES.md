# OMP NInfer v0.8.4 — every lane current

**Owner-operated, exact-profile 0.x candidate; no SLA.** RTX 5090 keeps its published runtime
and carried qualification. RTX 4090 advances to `v0.6.9-qwen38-4090-beta.1`: the same decode
kernels, with a 60 s GPU keep-warm that brings new sessions after idle back to back-to-back
prefill speed. The unmodified upstream Oh My Pi client advances from 18.3.0 to 18.3.5. The model
and memory floors are unchanged. RTX 3090 and the upstream engine merge remain deferred.
The RTX 4090 component is not yet published; documented-route and client-platform acceptance
are pending.

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Quickstart](../../docs/QUICKSTART.md) · [Security model](../../docs/SECURITY.md) ·
[Known limitations](#support-boundaries)

## What changed

The RTX 4090 steps down to P8 about 5-6 s after its last response. In
[EXP-064](../../docs/measurements/2026-09-27-rtx4090-engine-keep-warm.json), new sessions after
12-58 s idle prefilled in 0.29-0.47 s against 0.146 s back to back. The RTX 5090's single-warp
spin of 3.5 ms every 10 ms did not hold this card in P2, so that pattern was rejected.

The RTX 4090 component instead compiles an sm_89-specific spin of 50 ms every 100 ms, and its
packaged configuration sets `engine.gpu_keep_warm_ms` to 60000. In
[EXP-066](../../docs/measurements/2026-09-27-rtx4090-keep-warm-long-spin.json), every new session
after 12-58 s idle started in P2 and prefilled in 0.146-0.148 s (time to first token
0.167-0.178 s). All 31 outputs were byte-identical between the arms and to EXP-064's OFF arm.
The hold costs about 72 W above idle while it runs; a request arriving mid-spin can overlap one
warp for up to 50 ms.

The exact RTX 4090 package passed all 15 canonical qualification phases
([lane receipt](qualification/rtx4090.json)):
- 130,048-token exact retrieval in 91.0 s;
- C1 decode at 157.90 tok/s and 87.59% MTP acceptance, against v0.6.8's 157.89 tok/s; the sm_89
  decode kernels are unchanged;
- managed-stop flush, restart, security, and a typed tool call with OMP 18.3.5;
- rollback in both directions against the published v0.6.8 package, with graceful stops and no
  forced termination. The controller passes `--gpu-keep-warm-ms` only when the release being
  started declares a positive `engine.gpu_keep_warm_ms` in its own packaged configuration, so
  it does not pass the new flag to older servers.

The RTX 4090 field start from the memory state that refused v0.6.6 passed: with 3.5 GiB free and
22.6 GiB standby, the published v0.6.8 package started and pinned its 11264 MiB host-KV pool
([EXP-064, `issue_48_field_start`](../../docs/measurements/2026-09-27-rtx4090-engine-keep-warm.json)).
This is a field check of the existing commit-precharge fix, not a new v0.6.9 memory fix.

The OMP 18.3.5 macOS arm64 binary, configured only by the documented fragments and fail-closed
config, kept one session across graceful restarts on each lane, including a new OMP process
resuming after a restart. Each lane restored the session's checkpoint on that process's first
request without a previous response id
([EXP-067](../../docs/measurements/2026-09-27-stock-omp-1835-durable-sessions.json)). This is
one short session per lane with one client platform, not documented-route or platform acceptance.
The fragments need no change: 18.3.1-18.3.5 live steering is Codex-WebSocket-only and gated on
`compat.supportsSteering`, which these custom providers do not set; cache warming does not warm
models without a declared `promptCache`.

The RTX 5090 runtime is unchanged. Its
[lane receipt](qualification/rtx5090.json) is byte-identical to v0.8.3's; the stock OMP 18.3.5
proof above is separate evidence. Upstream engine head `e31bc99b` was measured against this
shipped runtime: prefill led by 1.5% in one run, the same small lead seen in EXP-048, but decode
was 59.2 versus 72.5 rounds/s (about 18% slower), fanout reuse was 0/4 versus 4/4, and two-session
root fallbacks were 4/8 versus 2/8. The merge stays deferred
([EXP-065](../../docs/measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json)).

## Two qualified GPU routes

- RTX 5090: `v0.6.12-qwen38-5090-beta.1`, image
  `sha256:cd9e10b115bbf38df011b201dfdd37ec3b56613da39b2f1701334c8157236b78`, server
  `3ab266e5cd82398be98c2baee6a41a123ce1a4b0d38bd9ddcda75044dcd5dcb1`, source
  `9d1ef7485d9c741c2830fa3d55218f3242cec5d7`, unchanged from v0.8.3.
- RTX 4090: `v0.6.9-qwen38-4090-beta.1`, package
  `6492588ea9b62a02a5b83434c653c61ea709c7d1609eb9de9d1c0eaf7ae23e87` (574,751,101 bytes), server
  `65364401fb1adb66e903f96ed6553f8b70042d4a7b2360ec88fb68049afb9aa4`, source
  `5ac17674e8e0b6ecd2bdc56a8eb6f9c397c2c1f4`; qualified bytes, component publication pending.
- Unchanged model artifact:
  `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`.

RTX 5090 keeps deployment profile `qwen38-5090-v0.8.2`, configuration
`56878aed92e8f3fb4101884fa889c98d1da75914573ebd167305ca0b4aa83e98`, 60 s keep-warm,
16384 MiB host KV and a 28672 MiB host floor. RTX 4090 uses deployment profile
`qwen38-4090-native-v0.6.9-beta.1`, configuration
`ccecfbe3946e8cfea761fd1ad2187e92f04483c85a358122ca89dcaa3092672f`, 60 s keep-warm,
11264 MiB host KV, 24 host-state slots and the unchanged 32768 MiB floor.

RTX 3090 is omitted while its physical host is offline. Its sm_86 runtime advanced to
`v0.6.2-beta.1` at source `5ac17674` and built on the RTX 4090 host: 99 of 105 registered tests
passed; six real-engine/frontend suites skipped without the artifact and a matching device.
That is not RTX 3090 qualification. The component is unpublished and absent from the manifest;
one `qualify_native.py` window on the physical RTX 3090 remains before inclusion. Its
[v0.7.2 instructions](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)
and OMP 18.0.9 client remain a separate historical route, not a v0.8.4 qualification claim.

## Documented routes and clients

Acceptance is pending. After the founder publishes the RTX 4090 component and the lane stage
promotes the v0.8.4 authority, run the four documented routes with unmodified OMP 18.3.5:
RTX 5090 container host, macOS client, Windows client and RTX 4090 native Windows
(`acceptance/documented-routes.json`, pending). The upstream macOS arm64, Windows x64 and
Linux x64 binaries must also pass platform acceptance against the unchanged RTX 5090 image
(`acceptance/composed-external-installation.json`, pending). Neither
v0.8.3's acceptance nor EXP-067 substitutes for those runs. Until they pass, v0.8.4 stays a
candidate and `--require-ready` refuses it. The macOS profile stays `preview`: the upstream
client has no managed installation or appliance lifecycle. Linux under WSL2 is not a separately
qualified Linux OS.

## Upgrading from v0.8.3

Once v0.8.4 is published and ready, clone its tag and follow the quickstart for your lane.
Replace the OMP executable with the checksummed upstream 18.3.5 binary for your platform;
provider fragments and `PI_OPENAI_STATEFUL=1` are unchanged. Do not use a generic `omp update`
to move outside the release's pinned bytes.

RTX 4090 installs the new native package. Checkpoints saved by v0.6.8 are bound to its server
build and report `incompatible` on v0.6.9: OMP resends the full conversation, each session
re-prefills once, and the old checkpoints age out under the checkpoint quota. RTX 5090 keeps the
same server build, image, arguments and profile, so its v0.8.3 checkpoints remain valid across
this upgrade; it does not require that re-prefill.

## Support boundaries

The keep-warm results apply to the owner's RTX 4090 under Windows driver 610.88. Other drivers
or GPUs may step down on a different schedule. The RTX 5090 keeps its already-qualified
3.5 ms/10 ms pattern; the sm_89 pattern is not a change to that lane. Both holds cost board power
only while running. The C1 fixture is trajectory-sensitive, so its matching result is not a
claim of a general decode speedup.

On Windows, OMP 18.3.5 prints a false `` `omp launch` ended before completing`` line after a
finished `omp -p` turn; its answer and zero exit status are correct. `omp models` exits 1 after
printing its complete listing. The documented routes never run `omp models`, and their `omp -p`
exit checks held when the RTX 4090 route's acceptance block ran against the lane. Upstream's fix
is in 18.4.0 ([can1357/oh-my-pi#13470](https://github.com/can1357/oh-my-pi/issues/13470)).

Since v0.8.0 the RTX 4090 server commits and releases each pinned allocation's size plus 1/64
before pinning it. The refusing memory state's field start passed, and every managed start in
the new package's canonical qualification pinned the pool
([#48](https://github.com/alphastorm/omp-ninfer/issues/48), [lane receipt](qualification/rtx4090.json)).
A refusal that still occurs reports the commit limit, available commit and available memory.

Automatic checkpointing remains best effort under live traffic: a crash or an expired graceful
wait can still leave unpublished work unsaved. Saving before eviction delays the admitting
request - about 6.5 s per 126K-token session on the RTX 5090 - and that request waits while a
victim's reply is still reaching its client, bounded by its own queue deadline. Ceiling-class
save-before-evict was exercised on the RTX 5090; the RTX 4090 lane runs its own phases. The carried
multisession control recorded root fallback on 2 of 8 continuations/forks; universal warm reuse
is not claimed. Prefill, decode and power figures apply only to the recorded packages, machines
and profiles. Owner-operated exact profiles only; no SLA, multi-GPU, multi-tenant,
priority/preemption, or silent cloud fallback. Native Windows RTX 4090 is text/tools; vision
remains an RTX 5090 container capability. Do not mix a predecessor manifest with these commands.
