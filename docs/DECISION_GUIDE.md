# Choosing a local inference backend for coding sessions

Last verified: 2026-08-31, against each project's public documentation. Capabilities change
quickly — reverify before deciding; corrections welcome as issues.
OMP NInfer checkpoint transport status updated 2026-09-13 from repository receipts; this does
not reverify the other projects' capabilities.

OMP NInfer deliberately occupies a narrow category: **durable local inference for coding
agents** — private, long-lived Oh My Pi sessions on one qualified GPU. The projects below
are excellent at different jobs; most operators should use one of them.

The v0.9.0 scope is **RTX 5090 on Windows 11 + Docker Desktop/WSL2** or **RTX 4090 native
Windows 11**, with the checksummed, unmodified upstream OMP 18.4.0 binary. The RTX 5090 serves
**two requests at once** on `v0.6.14-qwen38-5090-beta.1` (image `4c816b0c`, server `f62a570e`).
The eight-token verify-round fix brought two decoding requests to **281.1-283.0 tok/s together**,
against 166.7-167.1 one at a time (**1.68-1.70x**), up from v0.6.13's 190.0-191.1. The candidate
and published image kept the 89-case role corpus byte-identical (**89/89**)
([EXP-077](measurements/2026-09-29-rtx5090-two-requests-in-flight.json)). RTX 4090 keeps its
v0.6.10 runtime, profile and one-request limit.

The RTX 5090's **180 s** pending timeout leaves room for its longest root prefill (130,048
tokens in 58.4 s) inside OMP's 300 s watchdog. This is aggregate decode capacity, not a promise
that OMP work finishes sooner: stock OMP wall time followed generated tokens. Decode beside a
long prefill ran at about **30 tok/s**, a request arriving during a staged prefill waited, and
two sessions above about **47K tokens each take turns** (inferred from the admission rule,
not measured with OMP). Checkpoints remain best effort; universal warm reuse is not claimed.

Upgrade from v0.8.7 by following the quickstart for your lane: **upgrade the RTX 5090 server
first**, then merge these limits into `~/.omp/agent/config.yml`:

```yaml
providers:
  maxInFlightRequests:
    ninfer-beta: 2
    ninfer-native-4090: 1
    ninfer-main: 2
    ninfer-heavy: 1
```

A limit of 2 against the old one-at-a-time server queues requests where its 30 s deadline can
expire them. The client, provider fragments, model and memory floors are unchanged. RTX 5090
checkpoints re-prefill once after the build change; RTX 4090 checkpoints carry over.
A new OMP process still sends its first resumed request without the session's earlier reasoning,
which costs one root prefill on either lane. See the
[current measurements and limits](BENCHMARKS.md#v090--two-requests-in-flight-on-the-rtx-5090-2026-09-29).

All four routes passed **24 steps** on `0d2a7468` with unmodified OMP 18.4.0 and published
components: RTX 5090 host 2, macOS 10, Windows 5 and RTX 4090 native Windows 7; both hosts
were restored.
[Release state and manifest](RELEASES.md) ·
[Documented routes](../releases/v0.9.0/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.9.0/acceptance/composed-external-installation.json).

**Historical v0.8.7 — long sessions keep their cache.** Both lanes gained fixes for compaction
handoffs, near-capacity continuation, crashes after a compaction and checkpoint reclamation.
RTX 4090 handoffs reused 78.0-79.9K cached tokens and started in 0.58-0.70 s; RTX 5090
near-capacity turns reused 78.0-80.5K tokens with no root prefill over 60K. The route config
limited each provider to one request so a turn meeting a background summary waited in OMP,
not at the server's 30 s deadline. Those cache fixes carry into v0.9.0
([EXP-074](measurements/2026-09-29-long-session-cache.json)).

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
