# OMP NInfer v0.9.1 — RTX 3090 on the native Windows runtime

**Owner-operated, exact-profile 0.x candidate; no SLA.** The RTX 3090 returns as a native
Windows lane on the mainline runtime, with the unmodified upstream OMP 18.4.0 client and one
request at a time. The RTX 5090 and RTX 4090 components, profiles, model and memory floors are
unchanged from v0.9.0. The five documented routes must pass on the published components before
v0.9.1 is a release. The upstream engine merge remains deferred.

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Quickstart](../../docs/QUICKSTART.md) · [Security model](../../docs/SECURITY.md) ·
[Known limitations](#support-boundaries)

## What changed

### The RTX 3090 runs the native Windows runtime

v0.9.0 omitted the RTX 3090 while its host was offline; its last route was v0.7.2's durable v0.2
lineage with the OMP 18.0.9 fork client. v0.9.1 adds RTX 3090 native Windows
`v0.6.2-qwen38-3090-beta.1`: the RTX 5090 v0.6.14 runtime source (`e20060b6`, whose parent is
the RTX 4090's `cba7eb93`) plus one controller fix, built for sm_86. It has the RTX 4090's
lifecycle: a managed scheduled task, a protected state root, a graceful stop that saves live
sessions, durable session checkpoints and rollback to the previous release.

On the physical RTX 3090 its package passed all 15 canonical qualification phases: 130,048-token
retrieval exactly in 221.0 s, restart with a managed-stop flush of an unpublished session,
rollback in both directions against the lane's unpublished v0.6.0-beta.1 package, protected
state, the 15-check agent protocol at the shipped host pool and with 8 host-state slots, the
unmodified upstream OMP 18.4.0 client's typed tool call, and the C1 benchmark at 102.64 tok/s with
93.43% MTP acceptance under the lane's 300 W cap ([lane receipt](qualification/rtx3090.json)).

### A rollback can launch a release older than the controller

The shared Windows controller read `context_cache.host_kv_mib` directly under PowerShell strict
mode. The RTX 3090's v0.6.0 configuration predates that field, so the first qualification
window, at `e20060b6`, failed its rollback phase: the managed wrapper exited before it launched
the predecessor. `f08309da` passes `--host-kv-mib` only when a release's own configuration
declares it, as it already did for `gpu_keep_warm_ms`, and the runtime's lifecycle tests now
require every configuration field newer than the shipped lineage to be read that way. Every
published RTX 4090 package declares the field, so the unchanged RTX 4090 lane was not exposed.

### OMP sends the RTX 3090 one request at a time

`examples/manual-tunnel/fail-closed.yml` now lists `ninfer-native-3090: 1` under
`providers.maxInFlightRequests`. OMP leaves an unlisted provider unlimited, and a request beyond
the lane's one waits at the server, which expires it after 30 s.

## Three qualified GPU routes

- Unchanged RTX 5090: `v0.6.14-qwen38-5090-beta.1`, image
  `sha256:4c816b0c1c75c2f40cfb7e2ae289fc984f5235b6a417dbdc012d636cdd4d65f7`, server
  `f62a570e49275d6be9445276f81da6960a64d792a59f017362b132864e423193`, source
  `e20060b6a152a11fd72450549592527e126b035e`.
- Unchanged RTX 4090: `v0.6.10-qwen38-4090-beta.1`, package
  `a0ea4c81a3a70239fa350f2bbbfff9cd088de6d0028c4e73cff5581afa09cc6b` (574,717,115 bytes), server
  `e0498fad39bcb69d21bf7a6124c900be7229e2542c8c7ca72e19b32c606a51d3`, source
  `cba7eb932724c99a4faffd6b7b47256015c9b969`.
- New RTX 3090: `v0.6.2-qwen38-3090-beta.1`, package
  `da1d62f2d7d9ddcb3907db2baa55ceeac6a678c44e4db43c8848837f1c8162d3` (595,676,373 bytes), server
  `11b3f93c0b05a307423668d55daaae6062afd76229614215701e0ebd10080bd3`, source
  `f08309da3cc1d4226d127b7c9ce22267d12070cc`.
- Unchanged model artifact, which the RTX 3090 serves too:
  `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`.
- Unchanged client: unmodified upstream OMP 18.4.0.

RTX 5090 keeps deployment profile `qwen38-5090-v0.9.0`, configuration
`cf1de114d4cec0daa75b9734cfeceef572fa63224e5edbaffc1ea9deebf3aa32`, with
`--max-concurrency 2 --pending-timeout-ms 180000`: two requests in flight, a 160,256-token KV
pool, 60 s keep-warm, 16384 MiB host KV, the 24 GiB checkpoint quota, BF16 KV, MTP3,
131,072-token context and the 28672 MiB host floor ([lane receipt](qualification/rtx5090.json)).

RTX 4090 keeps deployment profile `qwen38-4090-native-v0.6.10-beta.1`, configuration
`7a69481f205c3f211d9dab13347d16589eb22ce3c404b1d555d788c39f72a7d4`, one request at a time and
its 30 s pending timeout, with 60 s keep-warm, 11264 MiB host KV, 24 host-state slots and the
32768 MiB floor ([lane receipt](qualification/rtx4090.json)).

RTX 3090 uses deployment profile `qwen38-3090-native-v0.6.2-beta.1`, configuration
`0f70066736b0d48f453a4e036e5640244f048184d28e36aa0e6d0e12aa07f3a2`: one request at a time with a
30 s pending timeout, 131,072 tokens of INT8 KV with MTP3, an 8192 MiB host-KV pool, 24
host-state slots and keep-warm off. It declares no host-memory floor; it was qualified on one
host. While it serves, its GPU-owner controller holds the card at 300 W and restores the owner's
370 W limit on stop.

## Documented routes and clients

Route acceptance is pending. The five documented routes - RTX 5090 container host, macOS
client, Windows client, RTX 4090 native Windows and RTX 3090 native Windows - must run on the
published v0.6.14 RTX 5090 image `4c816b0c`, the unchanged v0.6.10 RTX 4090 package and the new
v0.6.2 RTX 3090 package with upstream OMP 18.4.0, and both native lanes must install from their
public assets. Fresh client-platform acceptance is also pending. Until those runs pass, v0.9.1
stays a candidate and `--require-ready` refuses it. v0.9.0's accepted routes are not carried.
The macOS profile stays `preview`: the upstream client has no managed installation or appliance
lifecycle. Prior Linux acceptance ran under WSL2, not a separately qualified Linux OS.

## Upgrading from v0.9.0

RTX 5090 and RTX 4090 owners change nothing: the image, packages, profiles, OMP binary and
`models.yml` are v0.9.0's. To add the RTX 3090, follow the quickstart's RTX 3090 native route and
merge its provider into `~/.omp/agent/config.yml` with the lane's limit:

```yaml
providers:
  maxInFlightRequests:
    ninfer-native-3090: 1
```

The RTX 3090 native lane has its own state root and runtime, so sessions from the v0.7.2 RTX
3090 route do not carry over; its v0.7.2 instructions and OMP 18.0.9 client remain a separate
historical route. Do not use a generic `omp update` to move outside the release's pinned bytes.

## Support boundaries

A managed RTX 3090 or RTX 4090 start refuses while any process holds 1 GiB or more of GPU
memory, the desktop compositor included. On the RTX 3090 qualification host a signed-in
desktop's compositor alone held about 1,070 MiB after its applications were closed, so the
window ran with the console signed out. The RTX 3090 rollback was proven against the lane's
unpublished v0.6.0-beta.1 package, whose stop is a termination because it predates the
stop-event channel; its C1 rate is the lane's first, with no like-for-like predecessor.

A decode beside another request's 71,641-token prefill on the RTX 5090 ran at 30.4-30.5 tok/s,
with output gaps up to 479-481 ms. A request arriving while another prefill is staged waits for
it. Two requests in flight do not provide preemption or universal warm reuse (EXP-077).

A restart of the OMP process costs one prefill of a resumed session's context on every lane.
OMP 18.4.0's first request after resuming omits the session's reasoning, so it cannot match the
restored checkpoint: in v0.8.7's EXP-074 that request prefilled 56,174 tokens from root (32.0 s
to the first token). The next request carries the reasoning again and caches. A server restart
alone restores hot. This is an upstream OMP item
([EXP-074](../../docs/measurements/2026-09-29-long-session-cache.json)).

Automatic checkpointing remains best effort under live traffic: a crash or an expired graceful
wait can still leave unpublished work unsaved. Saving before eviction delays the admitting
request - about 6.5 s per 126K-token session on the RTX 5090 in v0.8.7 - and that request waits
while a victim's reply is still reaching its client, bounded by its own queue deadline.
Prefill, decode and power figures apply only to the recorded packages, machines and profiles.
Owner-operated exact profiles only; no SLA, multi-GPU, multi-tenant, priority/preemption or
silent cloud fallback. Native Windows RTX 4090 and RTX 3090 are text/tools; vision remains an
RTX 5090 container capability. Do not mix a predecessor manifest with these commands.
