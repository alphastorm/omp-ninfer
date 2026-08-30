# Related work

Stateful model APIs, prefix/KV reuse, local model servers, and distributed inference all have strong
prior art. OMP NInfer's contribution is the exact product integration: OMP transcript and tool
semantics, transactional provider continuation, a target-specific NInfer/Qwen runtime, a private
client-to-GPU topology, and one release/qualification authority. It does not claim invention of
stateful Responses or persistent KV caching.

Sources below were reviewed on 2026-08-26, the NInfer family section on 2026-08-28, and the
local-server section on 2026-08-29. These
projects move quickly; consult their current documentation before making a deployment decision.

## The NInfer family

The runtime is not ours alone; it is one lane of a small ecosystem of single-GPU NInfer ports, and
the credit ordering matters:

- [Neroued/ninfer](https://github.com/Neroued/ninfer) is the original from-scratch C++20/CUDA
  engine for registered Qwen checkpoints on one RTX 5090 (`sm_120a`): the `.ninfer` artifact
  format, MTP speculative decoding, hybrid Gated DeltaNet execution, Vision, and the published
  performance and evaluation campaigns. Apache-2.0.
- [alphastorm/ninfer](https://github.com/alphastorm/ninfer) is this product's runtime fork of
  Neroued/ninfer. It adds the OMP-oriented pieces: stateful OpenAI Responses
  continuation/fork/delete semantics, authenticated status identity, the container/OCI/SBOM
  release packaging, and the qualification evidence bound into the product manifest — plus the
  qualified native RTX 4090 beta branch and the reviewed RTX 3090 preview branch shipped by v0.2.
- [UDPSendToFailed/ninfer-4090](https://github.com/UDPSendToFailed/ninfer-4090) ports the engine
  to RTX 4090 (`sm_89`) with E8-lattice KV quantization, DirectStorage weight DMA, and D3D12
  residency management. The qualified native RTX 4090 beta branch in `alphastorm/ninfer` forks it.
- [Don-Chad/ninfer-3090](https://github.com/Don-Chad/ninfer-3090) ports the engine to RTX 3090
  (`sm_86`) with ReplaySSM and RotorQuant KV compression; the reviewed, non-installable RTX 3090
  preview branch in `alphastorm/ninfer` forks it. A fresh downstream candidate now adds exact
  native-Windows package, durable restart, OMP, and bounded C1 evidence without changing that
  upstream lineage or the published v0.2 manifest.

Each repository publishes its own measurements on its own profiles and quantization schemes; the
README family table quotes their headlines with attribution, and only the RTX 5090 numbers in
[`BENCHMARKS.md`](BENCHMARKS.md) are qualified product claims.


## Closest semantic prior art

### [vLLM Agentic API](https://github.com/vllm-project/agentic-api)

A stateful gateway in front of stateless vLLM core. Its public design includes OpenAI-compatible
Responses, `previous_response_id`, tool-oriented request state, SSE/WebSocket transport, and
SQLite/Postgres persistence. It is the closest public prior art for stateful Responses semantics.
As of 2026-08 its [roadmap](https://github.com/vllm-project/agentic-api/blob/main/ROADMAP.md)
still lists reliable `previous_response_id` state hydration as active work.

OMP NInfer does not insert Agentic API because OMP already owns the authoritative transcript and
transactional provider snapshot while NInfer owns process-local response/cache state. Adding another
stateful gateway would create a second continuation and recovery owner without improving the first
manual-tunnel release. Agentic API remains a useful comparison if multi-client server-side durable
conversation storage becomes a product requirement.

### [Ollama](https://docs.ollama.com/api/openai-compatibility)

A widely used local model runtime with OpenAI-compatible endpoints and an accessible install UX.
Its documented Responses compatibility is not the same OMP-owned `previous_response_id` transaction
used here. Ollama is a better fit when broad model/hardware convenience matters more than the exact
qualified NInfer/Qwen/RTX route.

### [LM Studio](https://lmstudio.ai/docs)

The most polished desktop path to discovering and running local models, with a headless daemon,
OpenAI- and Anthropic-compatible local endpoints, tool calling, and structured output. Its
documented endpoints are stateless chat-style requests: cross-turn state lives in the client, and
no `previous_response_id` continuation contract is documented. A better fit when desktop model
management and catalog breadth matter more than one qualified stateful OMP route.

Adjacent single-machine servers with strong NVIDIA followings —
[TabbyAPI](https://github.com/theroyallab/tabbyAPI) (ExLlama-based) and
[mistral.rs](https://github.com/EricLBuehler/mistral.rs) — offer quant-focused OpenAI-compatible
serving under the same stateless per-request contract.

### [LocalAI](https://github.com/mudler/LocalAI)

A broad local OpenAI-compatible serving layer across multiple backends and modalities. OMP NInfer
chooses a narrower target-specific runtime and avoids a second translation/control layer. LocalAI's
breadth is a feature for a different product boundary, not a deficiency.

## Prefix and KV reuse

- [Neroued/ninfer](https://github.com/Neroued/ninfer) itself ships in-process prefix reuse
  (`prefix_reuse`, enabled in every profile this project ships): a live process avoids
  recomputing an append-only prefix with no OMP NInfer involvement.
- [vLLM Automatic Prefix Caching](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/)
  reuses matching prefix blocks inside vLLM.
- [LMCache](https://github.com/LMCache/LMCache) extends KV reuse and movement across inference
  instances and storage tiers.
- [SGLang HiCache](https://docs.sglang.ai/advanced_features/hicache_best_practices.html) manages
  hierarchical KV cache tiers.
- [llama.cpp server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server) exposes slots and
  cache-oriented local serving behavior.

Those systems establish extensive KV/prefix-cache prior art, and they fully cover the
live-process append-only case. OMP NInfer's relevant distinction is that continuation is
explicit, transactional, and durable rather than an implicit longest-prefix match: OMP publishes
the transcript before committing a provider baseline, lineage (forks, rollback) is addressable
through `previous_response_id`, and on the native Windows lanes the continuation is checkpointed
so it survives process death — which an in-process cache structurally cannot. The user-facing
claim is therefore “keep a long coding session durable and instantly resumable on a GPU you
own,” not “no re-prefill,” and not “invent persistent KV” or “make inference 100× faster.”

## Distributed inference control planes

- [NVIDIA Dynamo](https://github.com/ai-dynamo/dynamo) targets distributed inference serving and
  disaggregated runtime concerns.
- [llm-d](https://github.com/llm-d/llm-d) targets Kubernetes-native distributed inference.

They address materially broader multi-node/multi-tenant scheduling and serving problems. The current
OMP NInfer v0.2 contract is one GPU per qualified profile, one resident model, one trusted owner,
and one active request; a distributed control plane would add cost without satisfying the
public-release outcome.

## Why direct OMP to NInfer

The direct route is intentional:

- OMP already owns coding sessions, tools, branches, replay, and durable transcript publication;
- NInfer already owns Qwen execution, authenticated status, Responses state, and GPU cache lifetime;
- the managed adapters and SSH/local-loopback transports already supply the narrow private machine
  boundary for v0.2; and
- the product manifest binds exact bytes and support claims across both.

A new gateway or generic model framework should be introduced only if a named requirement cannot be
owned cleanly by those existing boundaries.
