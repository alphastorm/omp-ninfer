# OMP NInfer v0.8.7 — Long sessions keep their cache

**Owner-operated, exact-profile 0.x release; no SLA.** Long sessions no longer re-prefill from
root at compaction handoffs, near-capacity turns, crashes after a compaction or when short
sessions fill the checkpoint store. Both GPU lanes move to runtimes that keep the session's cache
in those cases, and the config every route installs limits each NInfer provider to one request in
flight, so OMP compacts in the background again. The client, the provider fragments, the kernels,
the serving arguments, the model and the memory floors are unchanged from v0.8.6. RTX 3090 and the
upstream engine merge remain deferred.

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Quickstart](../../docs/QUICKSTART.md) · [Security model](../../docs/SECURITY.md) ·
[Known limitations](#support-boundaries)

## What changed

### OMP compacts in the background again

v0.8.6 turned OMP's async compaction off, because the background summary request held the
runtime's only admission slot and the user's next turn expired behind it at the 30 s admission
deadline. `examples/manual-tunnel/fail-closed.yml` now limits each NInfer provider to one request
in flight and leaves compaction at OMP's default. The turn that meets a running summary waits in
OMP, which has no deadline, and the summary still runs while you read or type. On the RTX 4090,
three handoff compactions and a graceful restart ran 55 requests with none expired; the three
turns that met a running handoff took 34.2-56.3 s, and 22 turns took 365.4 s where v0.8.6's
inline compaction took 678.2 s for 24
([EXP-074](../../docs/measurements/2026-09-29-long-session-cache.json)).

The limit must name the route's own provider id: OMP leaves an unlisted provider unlimited. On a
mock endpoint with only `ninfer-beta` limited, the RTX 4090 route's `ninfer-native-4090` turn
failed after six expired attempts. The config lists every provider id a documented route or the
fleet declares.

### The RTX 4090 compaction handoff reuses the session's cache

OMP's handoff asks for its summary with `tool_choice: none`. The runtime rendered that request
without the tool block every other turn starts with, so the handoff re-prefilled the whole
session. It now renders the declared tools and ends the turn at the template's tool-call token.
Handoffs of 78.4-80.4K tokens reused 78.0-79.9K cached tokens and reached the first token in
0.58-0.70 s; v0.6.9 prefilled 97.4-97.5K tokens from root in 63.8-66.3 s.

### Near-capacity turns keep their continuation

When the materialization planner's search runs out of time near capacity, it falls back to a
maximal plan. That fallback seeded only from the root candidate, which evicts the admitting
session's own continuation, so the turn re-prefilled from root: about 102,600 tokens (68 s) on
the RTX 4090, and on the RTX 5090 the chained turn of 93.7-105.1K tokens (40-46 s) that v0.8.6
listed with an unidentified cause. The fallback now seeds from every candidate that keeps its
source. In three stock OMP 18.4.0 sessions with two compactions each on the RTX 5090, the three
fallback turns reused 78.0-80.5K cached tokens and reached the first token in 12.4-12.5 s, and no
turn prefilled more than 60K tokens from root ([lane receipt](qualification/rtx5090.json)).

### A crash after a compaction restores the compacted session

The runtime saves a checkpoint automatically only for sessions of at least 32,768 tokens
(`--session-checkpoint-min-tokens`). A compacted session is shorter, so its new lineage was never
saved, and after a crash the server restored the pre-compaction checkpoint and the next turn
prefilled from root. A session with a checkpoint on disk now keeps it current at any size, and an
unstored Responses turn leaves the session's lineage alone. After a hard kill following a
compaction, the next RTX 4090 turn reused 32,167 cached tokens in 2.9 s; v0.6.9 prefilled 32,173
tokens from root (29.2 s).

v0.8.6 attributed the cold first turn after a graceful restart to a stale checkpoint. A graceful
server restart restores hot on both runtimes, because the stop saves every unsaved session; that
cold turn came from restarting the OMP process with the server ([Support
boundaries](#support-boundaries)).

### Long sessions keep their checkpoints when short sessions fill the store

The checkpoint store has a 24 GiB quota, and reclamation deleted the oldest checkpoints first. On
the RTX 5090, about 26 short OMP sessions of about 930 MiB each filled it and deleted every long
session's checkpoint. Reclamation now takes checkpoints below `--session-checkpoint-min-tokens`
first, oldest first, and then longer ones. With 35 sessions of 11.9K tokens (checkpoints of about
1,085 MiB) filling the RTX 5090 store, a 60,026-token session kept its 4.19 GiB checkpoint, and
after a crash its next turn reused 60,057 cached tokens in 2.9 s. On the RTX 4090, v0.6.9
reclaimed the long session's checkpoint first and its continuation failed with
`previous_response_not_found`; v0.6.10 reused 60,057 cached tokens in 3.1 s.

### Stock OMP keeps one session across restarts on both runtimes

With unmodified OMP 18.4.0 and each route's documented fragment and this config, one OMP process
across a server restart, a new process with the server up and a new process after a restart all
recalled both seeded facts under one OMP session id on both lanes. Every turn after the seed
reused the session's cache, and after the second restart each lane restored the session's
checkpoint on the new process's first request
([EXP-075](../../docs/measurements/2026-09-29-stock-omp-1840-durable-sessions.json)).

## Two qualified GPU routes

- RTX 5090: `v0.6.13-qwen38-5090-beta.1`, image
  `sha256:d71e34c30b0f9f6d5037ab5d524977d45da2e576d954a6c59407c2332769fbf6`, server
  `b8ae62ae2454e4df1df5a84950cdd30b3ffb7ffd60d7299761eaf3f653479ec3`, source
  `423f5b1dd9cbe0c6b0e14df0cfa33719d205e667`.
- RTX 4090: `v0.6.10-qwen38-4090-beta.1`, package
  `a0ea4c81a3a70239fa350f2bbbfff9cd088de6d0028c4e73cff5581afa09cc6b` (574,717,115 bytes), server
  `e0498fad39bcb69d21bf7a6124c900be7229e2542c8c7ca72e19b32c606a51d3`, source
  `cba7eb932724c99a4faffd6b7b47256015c9b969`.
- Unchanged model artifact:
  `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`.
- Unchanged client: unmodified upstream OMP 18.4.0.

Both lanes run the same runtime code. The RTX 4090 source adds its packaging and a controller fix:
an action no longer fails when the server writes a checkpoint while the controller walks the state
tree.

RTX 5090 keeps deployment profile `qwen38-5090-v0.8.2`, configuration
`56878aed92e8f3fb4101884fa889c98d1da75914573ebd167305ca0b4aa83e98`, 60 s keep-warm,
16384 MiB host KV and a 28672 MiB host floor. The candidate and the published image answered the
89-case role corpus byte-identically to v0.6.12, and the published image prefilled 130,048 tokens
exactly in 58.3 s and decoded 170.36 tokens/s ([lane receipt](qualification/rtx5090.json)).
RTX 4090 moves to deployment profile `qwen38-4090-native-v0.6.10-beta.1`, configuration
`7a69481f205c3f211d9dab13347d16589eb22ce3c404b1d555d788c39f72a7d4`, with v0.6.9's serving
arguments: 60 s keep-warm with its sm_89 spin of 50 ms every 100 ms, 11264 MiB host KV, 24
host-state slots and the 32768 MiB floor. Its [lane receipt](qualification/rtx4090.json) records
the 15 canonical qualification phases, including a typed tool call with OMP 18.4.0: 130,048-token
retrieval in 91.2 s and C1 decode at 157.91 tokens/s with 87.59% MTP acceptance, as v0.6.9.

RTX 3090 is omitted while its physical host is offline. Its built and tested `v0.6.2-beta.1`
package ([build preparedness](../../docs/measurements/2026-09-28-rtx3090-v062-build-preparedness.json))
is unpublished and absent from the manifest; one `qualify_native.py` window on the physical
RTX 3090 remains before inclusion. Its
[v0.7.2 instructions](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)
and OMP 18.0.9 client remain a separate historical route, not a v0.8.7 qualification claim.

## Documented routes and clients

The four documented routes - RTX 5090 container host, macOS client, Windows client and RTX 4090
native Windows - run against this candidate's published components with unmodified OMP 18.4.0
before the release is cut, with fresh client-platform acceptance.

## Upgrading from v0.8.6

Clone the v0.8.7 tag and follow the quickstart for your lane: RTX 5090 runs the new image digest
with the same arguments and profile, and RTX 4090 installs the new native package. In
`~/.omp/agent/config.yml`, remove

```yaml
compaction:
  asyncEnabled: false
```

and merge

```yaml
providers:
  maxInFlightRequests:
    ninfer-beta: 1
    ninfer-native-4090: 1
    ninfer-main: 1
    ninfer-heavy: 1
```

adding any other NInfer provider id you declare. The OMP binary, `models.yml` and
`PI_OPENAI_STATEFUL=1` are unchanged. Do not use a generic `omp update` to move outside the
release's pinned bytes.

A session checkpoint is bound to the exact server build, and both lanes' builds change: checkpoints
saved by v0.8.6 report `incompatible` and are not restored. OMP resends the full conversation,
each session re-prefills once, and the old checkpoints age out under the checkpoint quota.

## Support boundaries

A restart of the OMP process costs one prefill of a resumed session's context on either lane. OMP
18.4.0's first request after resuming omits the session's reasoning, so it cannot match the
restored checkpoint: in EXP-074 that request prefilled 56,174 tokens from root (32.0 s to the
first token). The next request carries the reasoning again and caches. A server restart alone
restores hot. This is an upstream OMP item.

EXP-074 and the RTX 5090 long-session gate are one run per configuration with synthetic build-log
filler, one seed and thinking `low`. One of the three RTX 5090 sessions stopped at the proof's own
planting check - OMP compacted before both identifiers were planted - and its requests are in the
gate.

Since v0.8.0 the RTX 4090 server commits and releases each pinned allocation's size plus 1/64
before pinning it ([#48](https://github.com/alphastorm/omp-ninfer/issues/48),
[lane receipt](qualification/rtx4090.json)). A refusal that still occurs reports the commit
limit, available commit and available memory.

Automatic checkpointing remains best effort under live traffic: a crash or an expired graceful
wait can still leave unpublished work unsaved. Saving before eviction delays the admitting
request - about 6.5 s per 126K-token session on the RTX 5090 - and that request waits while a
victim's reply is still reaching its client, bounded by its own queue deadline. The carried
multisession control recorded root fallback on 2 of 8 continuations/forks; universal warm reuse
is not claimed. Prefill, decode and power figures apply only to the recorded packages, machines
and profiles. Owner-operated exact profiles only; no SLA, multi-GPU, multi-tenant,
priority/preemption, or silent cloud fallback. Native Windows RTX 4090 is text/tools; vision
remains an RTX 5090 container capability. Do not mix a predecessor manifest with these commands.
