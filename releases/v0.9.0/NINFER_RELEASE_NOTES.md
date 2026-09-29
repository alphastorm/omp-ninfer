# OMP NInfer v0.9.0 — Two requests in flight on the RTX 5090

**Owner-operated, exact-profile 0.x candidate; no SLA.** The RTX 5090 serves two requests at
once, so subagents or a second session can run beside the first. The eight-token MTP3 verify
round uses tensor cores, and the profile gives a request that cannot fit 180 s to wait. The
RTX 4090 runtime, client, provider fragments, model and memory floors are unchanged from
v0.8.7. The four documented routes must pass on the published components before v0.9.0 is a
release. RTX 3090 and the upstream engine merge remain deferred.

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Quickstart](../../docs/QUICKSTART.md) · [Security model](../../docs/SECURITY.md) ·
[Known limitations](#support-boundaries)

## What changed

### Two decoding requests use the tensor cores

With two requests, the MTP3 verify round carries eight tokens. v0.6.13's Q5 projections left the
four-token tensor-core route for SIMT kernels: 12.8 ms of a 23.9 ms round, against 5.2 ms with
one request. Two decoding requests reached 190.0-191.1 tok/s together, only 1.14x the
166.7-167.1 tok/s one-at-a-time baseline.

v0.6.14 uses tensor cores at eight tokens. Two decoding requests reached 282.0-282.8 tok/s together
in the candidate window and 281.1-283.0 on the final profile (1.68-1.70x), or 143.5-152.8 tok/s
each. The output-event gap p50 was 15.6-15.7 ms against 13.7 ms alone. One request alone decoded
at 164.6-165.6 tok/s across the windows
([EXP-077](../../docs/measurements/2026-09-29-rtx5090-two-requests-in-flight.json)).

The candidate answered all 89 role-corpus cases byte-identically to the published v0.6.13 image,
run two at a time and one at a time on the final profile, and the published v0.6.14 image
answered all 89 byte-identically to the candidate. Both requests of every decode pair, the decode
beside a prefill and every fanout branch matched their one-at-a-time outputs. A continuation that
another request's timing sends down a different reuse path, such as root re-prefill instead of
replayed continuation, can still differ, as it can one at a time.

### OMP can send two requests to the RTX 5090

`examples/manual-tunnel/fail-closed.yml` sets `providers.maxInFlightRequests` to 2 for
`ninfer-beta` and `ninfer-main`, and keeps `ninfer-native-4090` and `ninfer-heavy` at 1. The
RTX 5090 uses snapcompact without a model request. On the RTX 4090, a turn that meets a
background compaction summary still waits in OMP, not at the server's 30 s admission deadline.
The limit must name the route's own provider id: OMP leaves an unlisted provider unlimited.

Stock OMP 18.4.0 at limit 2 kept two requests in flight for 15.7-17.7 s of a parent turn fanning
out two scout subagents, but the turn's wall time followed what the subagents generated: 25.2 and
23.9 s at limit 2 in two windows, against 32.7 and 22.6 s at limit 1. Two short OMP sessions
started together took 7.3 and 8.2 s at limit 2 against 6.5 and 5.6 s at limit 1. One run per limit
per window; these are workload measurements, not a promise that parallel work finishes sooner
(EXP-077).

### A request that does not fit can wait 180 seconds

Two requests share the 160,256-token KV pool only while both prompts and their output
reservations fit. A request that does not fit waits at the server. At the default 30 s it
expired with `503 request_queue_timeout`. The final profile sets `--pending-timeout-ms 180000`:
the wait plus the longest root prefill, 130,048 tokens in 58.4 s on the published image, stays inside
OMP 18.4.0's 300 s stream-idle watchdog. The server ends a too-long wait and OMP resends.

The reservation is `prompt + max_output_tokens - 1`. OMP sends `max_output_tokens: 32768`, so
two OMP sessions above about 47K tokens each take turns. This is inferred from the admission
rule, not measured with OMP. Raising concurrency does not raise how many long sessions keep
their cache: two alternating 62.4K-token sessions re-prefilled 2 of 4 continuations from root
at both one and two requests in flight.

### The v0.8.7 lane gates hold at two requests

The final-profile candidate passed stock OMP durable sessions, EXP-072's long-session gate at
limit 2, checkpoint reclamation, EXP-050's workload plus resume, EXP-051's barrier, the fanout,
warm-arrival, restore and multisession probes and the agent mix. No long-session turn prefilled
more than 60K tokens from root; the third planting run stopped at the same harness precondition
as v0.8.7. With 35 short sessions filling the 24 GiB store, a 60,026-token session reused 60,057
cached tokens after a crash in 2.99 s. All four stored workload sessions resumed from their
checkpoints, and none of 24 fresh agent sessions fell back to a full prefill
([lane receipt](qualification/rtx5090.json)). At two requests the barrier's evicting session was
admitted beside the held one, so the deferred save before eviction did not arise; the held turn
was saved after publication and resumed exactly.

A restart with two requests in flight ended both interrupted streams with `response.incomplete`.
Both continuations reused 62,404 cached tokens after restart, with first output in 5.07-5.53 s.
Graceful shutdown refused no saves (EXP-077).

## Two qualified GPU routes

- RTX 5090: `v0.6.14-qwen38-5090-beta.1`, image
  `sha256:4c816b0c1c75c2f40cfb7e2ae289fc984f5235b6a417dbdc012d636cdd4d65f7`, server
  `f62a570e49275d6be9445276f81da6960a64d792a59f017362b132864e423193`, source
  `e20060b6a152a11fd72450549592527e126b035e`.
- Unchanged RTX 4090: `v0.6.10-qwen38-4090-beta.1`, package
  `a0ea4c81a3a70239fa350f2bbbfff9cd088de6d0028c4e73cff5581afa09cc6b` (574,717,115 bytes), server
  `e0498fad39bcb69d21bf7a6124c900be7229e2542c8c7ca72e19b32c606a51d3`, source
  `cba7eb932724c99a4faffd6b7b47256015c9b969`.
- Unchanged model artifact:
  `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`.
- Unchanged client: unmodified upstream OMP 18.4.0.

RTX 5090 moves to deployment profile `qwen38-5090-v0.9.0`, configuration
`cf1de114d4cec0daa75b9734cfeceef572fa63224e5edbaffc1ea9deebf3aa32`, with
`--max-concurrency 2 --pending-timeout-ms 180000`. KV capacity auto-resolves to 160,256 tokens,
and VRAM after load is 30,244 MiB of 32,607 MiB, against 28,144 MiB with one request. It keeps
60 s keep-warm, 16384 MiB host KV, the 24 GiB checkpoint quota, BF16 KV, MTP3, 131,072-token
context and the 28672 MiB host floor. On this profile the published image retrieved 130,048
tokens exactly in 58.4 s, decoded 169.79 tok/s over 2,048 tokens and passed the agent protocol
across a restart ([lane receipt](qualification/rtx5090.json)).

RTX 4090 keeps deployment profile `qwen38-4090-native-v0.6.10-beta.1`, configuration
`7a69481f205c3f211d9dab13347d16589eb22ce3c404b1d555d788c39f72a7d4`, one request at a time and
its 30 s pending timeout. Its serving arguments remain 60 s keep-warm with the sm_89 spin of
50 ms every 100 ms, 11264 MiB host KV, 24 host-state slots and the 32768 MiB floor. The carried
[lane receipt](qualification/rtx4090.json) records the 15 canonical qualification phases,
including an OMP 18.4.0 typed tool call: 130,048-token retrieval in 91.2 s and decode at
157.91 tok/s with 87.59% MTP acceptance.

RTX 3090 is omitted while its physical host is offline. Its built and tested `v0.6.2-beta.1`
package ([build preparedness](../../docs/measurements/2026-09-28-rtx3090-v062-build-preparedness.json))
is unpublished and absent from the manifest; one `qualify_native.py` window on the physical
RTX 3090 remains before inclusion. Its
[v0.7.2 instructions](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)
and OMP 18.0.9 client remain a separate historical route, not a v0.9.0 qualification claim.

## Documented routes and clients

Route acceptance is pending. The four documented routes - RTX 5090 container host, macOS
client, Windows client and RTX 4090 native Windows - must run on the published v0.6.14
RTX 5090 image `4c816b0c` and the unchanged v0.6.10 RTX 4090 package with upstream OMP 18.4.0.
Fresh client-platform acceptance is also pending. Until those runs pass, v0.9.0 stays a
candidate and `--require-ready` refuses it. v0.8.7's accepted routes cover the previous
RTX 5090 runtime and config, not these. The macOS profile stays `preview`: the upstream client
has no managed installation or appliance lifecycle. Prior Linux acceptance ran under WSL2,
not a separately qualified Linux OS.

## Upgrading from v0.8.7

Once v0.9.0 is published and ready, clone its tag and follow the quickstart. Upgrade the
RTX 5090 server to the new image and profile first. Only then merge these values into
`~/.omp/agent/config.yml`:

```yaml
providers:
  maxInFlightRequests:
    ninfer-beta: 2
    ninfer-native-4090: 1
    ninfer-main: 2
    ninfer-heavy: 1
```

Add any other NInfer provider id you declare with its lane's limit. A limit of 2 against the
old one-at-a-time server queues requests at its 30 s deadline, where they can expire. The
RTX 4090 package, OMP binary, `models.yml` and `PI_OPENAI_STATEFUL=1` are unchanged. Do not use
a generic `omp update` to move outside the release's pinned bytes.

A session checkpoint is bound to the exact server build. RTX 5090 checkpoints saved by v0.8.7
report `incompatible` and are not restored: OMP resends the full conversation, each session
re-prefills once and the old checkpoints age out under the checkpoint quota. RTX 4090
checkpoints carry over because its runtime is unchanged.

## Support boundaries

A decode beside another request's 71,641-token prefill ran at 30.4-30.5 tok/s, with output gaps
up to 479-481 ms. A request arriving while another prefill is staged waits for it (26.7 s in
the probe). Two requests in flight do not provide preemption or universal warm reuse (EXP-077).

A restart of the OMP process costs one prefill of a resumed session's context on either lane.
OMP 18.4.0's first request after resuming omits the session's reasoning, so it cannot match the
restored checkpoint: in v0.8.7's EXP-074 that request prefilled 56,174 tokens from root (32.0 s
to the first token). The next request carries the reasoning again and caches. A server restart
alone restores hot. This is an upstream OMP item
([EXP-074](../../docs/measurements/2026-09-29-long-session-cache.json)).

Automatic checkpointing remains best effort under live traffic: a crash or an expired graceful
wait can still leave unpublished work unsaved. After the concurrency probe's evictions, the
graceful stop refused sessions whose newest turn was no longer resident: 7 at two requests and 5
at one request with the same runtime (EXP-077). Saving before eviction delays the admitting
request - about 6.5 s per 126K-token session on the RTX 5090 in v0.8.7 - and that request waits
while a victim's reply is still reaching its client, bounded by its own queue deadline.
Prefill, decode and power figures apply only to the recorded packages, machines and profiles.
Owner-operated exact profiles only; no SLA, multi-GPU, multi-tenant, priority/preemption or
silent cloud fallback. Native Windows RTX 4090 is text/tools; vision remains an RTX 5090
container capability. Do not mix a predecessor manifest with these commands.
