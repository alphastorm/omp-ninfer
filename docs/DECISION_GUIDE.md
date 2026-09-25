# Choosing a local inference backend for coding sessions

Last verified: 2026-08-31, against each project's public documentation. Capabilities change
quickly — reverify before deciding; corrections welcome as issues.
OMP NInfer checkpoint transport status updated 2026-09-13 from repository receipts; this does
not reverify the other projects' capabilities.

OMP NInfer deliberately occupies a narrow category: **durable local inference for coding
agents** — one private, long-lived Oh My Pi session on one qualified GPU. The projects below
are excellent at different jobs; most operators should use one of them.

The v0.8.0 scope is **RTX 5090 on Windows 11 + Docker Desktop/WSL2** or **RTX 4090 native
Windows 11**, with the checksummed, unmodified upstream OMP 18.3.0 binary.
[Release state and manifest](RELEASES.md).
RTX 3090 is deferred for v0.8.0; its [historical v0.7.2 route](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)
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
