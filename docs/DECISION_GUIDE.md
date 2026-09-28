# Choosing a local inference backend for coding sessions

Last verified: 2026-08-31, against each project's public documentation. Capabilities change
quickly — reverify before deciding; corrections welcome as issues.
OMP NInfer checkpoint transport status updated 2026-09-13 from repository receipts; this does
not reverify the other projects' capabilities.

OMP NInfer deliberately occupies a narrow category: **durable local inference for coding
agents** — one private, long-lived Oh My Pi session on one qualified GPU. The projects below
are excellent at different jobs; most operators should use one of them.

The v0.8.6 scope is **RTX 5090 on Windows 11 + Docker Desktop/WSL2** or **RTX 4090 native
Windows 11**, with the checksummed, unmodified upstream OMP 18.4.0 binary.
The config every route installs now sets `compaction.asyncEnabled: false`: OMP compacts before
the turn rather than in the background, so a turn no longer times out behind the RTX 4090's
handoff. [EXP-072](measurements/2026-09-28-omp-long-sessions.json), measured with the new
[long-session proof](../scripts/omp_long_session_proof.py), recorded three inline handoffs at
**77.0-83.7 s** each with no expired admission and exact newest-identifier recall after each
compaction and a graceful restart. The turn carrying compaction takes **91-101 s**. RTX 5090
snapcompact took **0.07-0.08 s** on the client and recalled both identifiers held only in frames;
its bounded archive dropped **76,832 and 192,080 characters** of older middle history.

This is one run per configuration on each lane with synthetic filler, one seed and thinking
`low`, not a measured failure rate. Older-identifier recall is recorded, not gated. RTX 5090
post-compaction restart was not measured. RTX 4090's first turn after a post-compaction restart
re-prefills about 32,000 tokens (17 s), rather than restoring hot state. See the other
[long-session limits](BENCHMARKS.md#v086--long-sessions-compact-inline-2026-09-28).

Upgrade from v0.8.5 by merging this into `~/.omp/agent/config.yml`:

```yaml
compaction:
  asyncEnabled: false
```

The client, provider fragments, runtimes, model, serving configurations, memory floors and lane
receipts are unchanged from v0.8.5; checkpoints carry across. RTX 5090 keeps image `cd9e10b1`
(`v0.6.12-qwen38-5090-beta.1`); RTX 4090 keeps package `6492588e`
(`v0.6.9-qwen38-4090-beta.1`). Documented resume/restart checks now plant with an OK-only
reply and recall verbatim. All four routes passed **24 steps** on `4f49fce7` with unmodified
OMP 18.4.0 and published components: RTX 5090 host 2, macOS 10, Windows 5 and RTX 4090 native
Windows 7; both hosts were restored. [Release state and manifest](RELEASES.md) ·
[documented routes](../releases/v0.8.6/acceptance/documented-routes.json).

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

RTX 3090 is deferred for v0.8.6; its
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
