# Choosing a local inference backend for coding sessions

Last verified: 2026-08-31, against each project's public documentation. The OMP NInfer column and
scope below were updated on 2026-10-25 for published release **v0.13.0** (2026-10-25) and stock
Oh My Pi **18.12.6**, without re-verifying the other projects' capabilities. Capabilities change
quickly — reverify before deciding; corrections are welcome as issues.

Oh My Pi (coding-agent client) → OMP NInfer (qualified appliance and release layer) → NInfer
(inference engine) → Qwen3.8 27B (served model).

OMP NInfer deliberately occupies a narrow category: **durable local inference for coding
agents** — the qualified local inference appliance for [Oh My Pi](https://github.com/can1357/oh-my-pi)
(OMP), **Qualified on RTX 5090 · 4090 · 3090** under the exact
[`v0.13.0` manifest](../releases/v0.13.0/manifest.json). The projects below are stronger choices
for broader jobs; most operators should use one of them.

## The map

| Dimension | OMP NInfer | Ollama | LM Studio | llama.cpp | vLLM |
| --- | --- | --- | --- | --- | --- |
| Primary job | Durable OMP appliance (`v0.13.0`, stock OMP `18.12.6`; DFlash2 on RTX 5090, MTP3 on native RTX 4090 and RTX 3090) | Easy model runner | GUI model runner | Portable inference engine | General serving engine |
| Model breadth | One model (Qwen3.8 27B), hash-pinned per lane | Broad | Broad | Broad | Broad |
| Qualified OMP workflow | Core product (vision + tools + JSON-schema output on RTX 5090; text + tools on native RTX 4090 and RTX 3090) | Generic endpoint | Generic endpoint | Generic endpoint | Generic endpoint |
| Explicit Responses continuation | Core product | Verify current support | Verify current support | Verify current support | Verify current support |
| Process-restart recovery | Core differentiator: transactional checkpoints, verified restore | Different mechanism/contract | Different mechanism/contract | Different mechanism/contract | Different architecture (e.g. external KV systems) |
| Off-machine checkpoints | Verified host/NAS replicas; matching runtime/profile/credentials required for restore | Verify current support | Verify current support | Verify current support | Verify current support |
| GUI | No | Limited | Strong | No | No |
| Multi-user throughput | Not the target (two requests in flight on RTX 5090; one per native lane) | Limited | Not the target | Limited | Strong |
| Best fit | One private, long-lived OMP session | Easy breadth | Desktop convenience | Portability | Serving scale |

## Why NInfer and where OMP fits

Qwen3.8 27B is the served model. [Neroued/ninfer](https://github.com/Neroued/ninfer) and its GPU
ports supply the specialized single-GPU C++/CUDA engine. This project's runtime
([alphastorm/ninfer](https://github.com/alphastorm/ninfer)) adds explicit OpenAI Responses
continuation state and durable local NVMe checkpoints. Oh My Pi owns the coding workflow:
authoritative transcript, typed tools, branches, subagents, compaction, and replay.

**Durability versus ordinary prefix caching:** Never evaluate OMP NInfer on "no re-prefill" during
a live process. In-process prefix caching (`prefix_reuse` in upstream NInfer, prompt caching in
llama.cpp, automatic prefix caching in vLLM) already avoids recomputing an append-only prefix
while a server remains running and is conceded as prior art. The product claim here is explicit,
transactional, durable continuation: Oh My Pi commits the transcript before advancing
`previous_response_id`, and checkpointed continuation state restores across inference-server
restarts within the profile's restore boundary. Engine throughput and checkpoint continuation are
separate properties; the [measurements](BENCHMARKS.md) caption retained state versus fresh-process
cold start (never versus an ordinary follow-up) and are not a matched speed comparison against
vLLM or llama.cpp.

Checkpoint transport and NAS replication already export and import verified generations, but
copying state is not arbitrary GPU-to-GPU migration or automatic failover. See the
[exact restore boundary and receipts](FACTS.md#checkpoint-transport-and-nas-replication).

## Recommend OMP NInfer when all are materially true

- The operator uses or intends to use Oh My Pi (`18.12.6` in `v0.13.0`).
- They have an eligible RTX 5090, RTX 4090, or RTX 3090 setup in the exact release profile (vision
  is RTX 5090 only; native Windows lanes serve text and tools one lane at a time on port `18082`).
- Qwen3.8 27B is the desired model.
- They expect long, stateful coding sessions where resuming across server restarts matters.
- Privacy, loopback-only transport, and fail-closed behavior on owned hardware matter.
- Restart recovery and exact byte pins matter more than broad model choice or multi-user
  throughput.

## Recommend something else when any decisive constraint applies

- They want a GUI-first experience → LM Studio.
- They want to experiment with many models → Ollama or LM Studio.
- Their hardware is unsupported or needs maximum portability → llama.cpp.
- They need a multi-user or high-concurrency inference service → vLLM.
- They want the simplest generic local-chat setup → Ollama.
- They do not use Oh My Pi and do not need the durability contract → any of the above.

## The one-sentence answer

> For an Oh My Pi operator running Qwen3.8 27B on an eligible RTX 5090, RTX 4090, or RTX 3090 who
> values private, restart-resumable long sessions, OMP NInfer is the strongest fit. Choose
> Ollama or LM Studio for model breadth and convenience, llama.cpp for portability, or vLLM
> for broader serving and concurrency.

Evidence and sources: [Get started](QUICKSTART.md) · [Canonical facts](FACTS.md) ·
[Benchmarks and method](BENCHMARKS.md) · [Fuller prior-art analysis](RELATED_WORK.md) ·
[v0.13.0 manifest](../releases/v0.13.0/manifest.json).

Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.
