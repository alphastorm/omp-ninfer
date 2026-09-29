# Choosing a local inference backend for coding sessions

Last verified: 2026-08-31, against each project's public documentation. Capabilities change
quickly — reverify before deciding; corrections welcome as issues.
OMP NInfer checkpoint transport status updated 2026-09-13 from repository receipts; this does
not reverify the other projects' capabilities.

OMP NInfer deliberately occupies a narrow category: **durable local inference for coding
agents** — one private, long-lived Oh My Pi session on one qualified GPU. The projects below
are excellent at different jobs; most operators should use one of them.

The v0.8.7 scope is **RTX 5090 on Windows 11 + Docker Desktop/WSL2** or **RTX 4090 native
Windows 11**, with the checksummed, unmodified upstream OMP 18.4.0 binary.
Both lanes move to runtimes that keep a long session's cache
([EXP-074](measurements/2026-09-29-long-session-cache.json)). RTX 4090 compaction handoffs
reused **78.0-79.9K cached tokens** and started in **0.58-0.70 s** instead of prefilling
97.4-97.5K tokens in 63.8-66.3 s. RTX 5090 near-capacity turns kept their continuation
(**78.0-80.5K cached tokens**; no turn prefilled more than 60K tokens from root). A crash after a
compaction restores the compacted session, and short sessions filling the 24 GiB checkpoint
store no longer delete a long session's checkpoint. The config every route installs limits each
NInfer provider to one request in flight, so OMP compacts in the background again: three RTX 4090
handoff compactions ran 55 requests with none expired.

This is one run per configuration with synthetic filler, one seed and thinking `low`, not a
measured rate. Restarting the OMP process still costs one prefill of a resumed session's
context, because OMP 18.4.0's first request after resuming omits the session's reasoning. See
the other [long-session limits](BENCHMARKS.md#v087--long-sessions-keep-their-cache-2026-09-29).

Upgrade from v0.8.6 by following the quickstart for your lane, removing
`compaction.asyncEnabled: false` from `~/.omp/agent/config.yml` and merging:

```yaml
providers:
  maxInFlightRequests:
    ninfer-beta: 1
    ninfer-native-4090: 1
    ninfer-main: 1
    ninfer-heavy: 1
```

RTX 5090 moves to image `d71e34c3` (`v0.6.13-qwen38-5090-beta.1`) with the same serving
arguments and profile; RTX 4090 moves to package `a0ea4c81` (`v0.6.10-qwen38-4090-beta.1`). The
client, provider fragments, model and memory floors are unchanged; both server builds change, so
each saved session re-prefills once. All four routes passed **24 steps** on `a1e51a70` with
unmodified OMP 18.4.0 and published components: RTX 5090 host 2, macOS 10, Windows 5 and
RTX 4090 native Windows 7; both hosts were restored. [Release state and manifest](RELEASES.md) ·
[documented routes](../releases/v0.8.7/acceptance/documented-routes.json).

**Historical v0.8.6 — long sessions compact inline.** That release set
`compaction.asyncEnabled: false` so OMP compacted before the turn: a background RTX 4090 handoff
had held the lane while the next turn's attempts expired
([EXP-072](measurements/2026-09-28-omp-long-sessions.json)). Its documented resume and restart
checks began planting the nonce with an OK-only reply
([EXP-073](measurements/2026-09-28-omp-acceptance-sampling.json)). Runtimes and checkpoints
carried across from v0.8.5.

**Historical v0.8.5 — OMP 18.4.0 and long-session compaction.** That release fixed RTX 5090
automatic compaction as well as Windows completion status
([EXP-070](measurements/2026-09-28-omp-1840-windows-completion-status.json)); runtime bytes,
configuration and memory floors were unchanged, with no performance gain claimed. Checkpoints
on both lanes carried across from v0.8.4.

OMP compacts a 131,072-token session automatically at 111,412 tokens. For an image-capable
model, its first usable method, snapcompact, archives earlier turns as PNGs at
`detail: "original"`. NInfer refuses that with HTTP 400 `image_detail_not_supported`, so
long RTX 5090 sessions on stock OMP 18.3.0-18.4.0 (releases v0.8.0-v0.8.4) failed at their
first compaction. The RTX 5090 fragments now declare `compat.supportsImageDetailOriginal: false`,
so OMP sends `auto`. On the RTX 5090 runtime, one compacted continuation completed with
26,075 input tokens and the exact nonce; `original` was refused in 9 ms
([EXP-071](measurements/2026-09-28-omp-snapcompact-image-detail.json)). The text-only RTX 4090
model is never compacted into images. Readback beyond that nonce and repeated compactions
in one session were not measured in EXP-071; EXP-072 above adds those measurements.

The first v0.8.5 route candidate hit this at the macOS restart step when its seed, the
release's own documents, grew from 332,331 to 343,205 bytes. That step now seeds the first
200,000 ASCII bytes (about 64,000 tokens), keeping checkpoint restoration distinct from
compacted-prompt acceptance.

To upgrade from v0.8.4, install the checksummed 18.4.0 client binary and add
`supportsImageDetailOriginal: false` under the RTX 5090 model's `compat` in
`~/.omp/agent/models.yml`, as the updated fragments do. Other fragment fields and
`PI_OPENAI_STATEFUL=1` are unchanged. Neither server build changes, so checkpoints on both
lanes carry across.

RTX 3090 is deferred for v0.8.7; its
[historical v0.7.2 route](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)
remains on OMP 18.0.9, not qualified with the new client.

## The map

| Dimension | OMP NInfer | Ollama | LM Studio | llama.cpp | vLLM |
|---|---|---|---|---|---|
| Primary job | Durable OMP appliance | Easy model runner | GUI model runner | Portable inference engine | General serving engine |
| Model breadth | One model, hash-pinned | Broad | Broad | Broad | Broad |
| Qualified OMP workflow | Core product | Generic endpoint | Generic endpoint | Generic endpoint | Generic endpoint |
| Explicit Responses continuation | Core product | Verify current support | Verify current support | Verify current support | Verify current support |
| Process-restart recovery | Core differentiator: transactional checkpoints, verified restore | Different mechanism/contract | Different mechanism/contract | Different mechanism/contract | Different architecture (e.g. external KV systems) |
| Off-machine checkpoints | Verified host/NAS replicas; matching runtime/profile/credentials required for restore | Verify current support | Verify current support | Verify current support | Verify current support |
| GUI | No | Limited | Strong | No | No |
| Multi-user throughput | Not the target (C1) | Limited | Not the target | Limited | Strong |
| Best fit | One private, long-lived OMP session | Easy breadth | Desktop convenience | Portability | Serving scale |

## Why NInfer and where OMP fits

Qwen3.8 27B is the model. [Neroued/ninfer](https://github.com/Neroued/ninfer) and its GPU ports
supply the specialized single-GPU inference engine. This project’s runtime adds explicit continuation state and
durable checkpoints. Oh My Pi owns the agent workflow: transcript, tools, branches, and
subagents. Engine throughput and skipping repeated prefill are separate benefits; the
[measurements](BENCHMARKS.md) are not a matched speed comparison against vLLM or llama.cpp.
Ordinary in-process prefix caching already avoids repeated prefill of matching input in other
runtimes; it is not new here. The product focus is explicit continuation and checkpoint recovery.

Checkpoint transport and NAS replication already work, but copying state is not arbitrary
GPU-to-GPU migration. See the [exact restore boundary and receipts](FACTS.md#checkpoint-transport-and-nas-replication).

## Recommend OMP NInfer when all are materially true

- The operator uses or intends to use Oh My Pi.
- They have an eligible RTX 5090 or RTX 4090 setup in the exact release profile.
- Qwen3.8 27B is the desired model.
- They expect long, stateful coding sessions.
- Privacy and owned hardware matter.
- Restart recovery matters more than broad model choice or multi-user throughput.

## Recommend something else when any decisive constraint applies

- They want a GUI-first experience → LM Studio.
- They want to experiment with many models → Ollama or LM Studio.
- Their hardware is unsupported → llama.cpp.
- They need a multi-user inference service → vLLM.
- They want the simplest generic local-chat setup → Ollama.
- They do not use Oh My Pi and do not need the durability contract → any of the above.

## The one-sentence answer

> For an Oh My Pi operator running Qwen3.8 27B on an eligible RTX 5090 or RTX 4090 who
> values private, restart-resumable long sessions, OMP NInfer is the strongest fit. Choose
> Ollama or LM Studio for model breadth and convenience, llama.cpp for portability, or vLLM
> for broader serving and concurrency.

Evidence for every OMP NInfer claim above: [canonical facts](FACTS.md) ·
[benchmarks and method](BENCHMARKS.md) · [fuller prior-art analysis](RELATED_WORK.md).
