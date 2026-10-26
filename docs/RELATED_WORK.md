# Related work

Oh My Pi (coding-agent client) → OMP NInfer (qualified appliance and release layer) → NInfer
(inference engine) → Qwen3.8 27B (served model).

Stateful model APIs, prefix/KV reuse, local model servers, and distributed inference all have
strong prior art. OMP NInfer's contribution is the exact product integration:
[Oh My Pi](https://github.com/can1357/oh-my-pi) (OMP) transcript and tool semantics, transactional
provider continuation, a target-specific NInfer/Qwen runtime, a private client-to-GPU topology,
and one release and qualification authority. It does not claim invention of stateful Responses or
persistent KV caching.

External sources below were reviewed on 2026-08-26, the NInfer family section on 2026-08-28, and
the local-server section on 2026-08-29; OMP NInfer self-descriptions were updated on 2026-10-26
for published release **v0.13.1** (2026-10-26). These projects move quickly; consult their current
documentation before making a deployment decision.

## The NInfer family

The runtime is not ours alone; it rides an ecosystem of single-GPU NInfer ports, and the credit
ordering matters:

- [Neroued/ninfer](https://github.com/Neroued/ninfer) is the original from-scratch C++20/CUDA
  engine for registered Qwen checkpoints on one RTX 5090 (`sm_120a`): the `.ninfer` artifact
  format, MTP and DFlash2 speculative decoding, hybrid Gated DeltaNet execution, vision, and the
  published performance and evaluation campaigns. Apache-2.0.
- [alphastorm/ninfer](https://github.com/alphastorm/ninfer) is this product's runtime fork of
  `Neroued/ninfer`. It adds the OMP-oriented pieces: stateful OpenAI Responses
  continuation/fork/delete semantics, durable local NVMe checkpoints, authenticated status
  identity, container/OCI/SBOM and native Windows release packaging, and the qualification
  evidence bound into the [`v0.13.1` manifest](../releases/v0.13.1/manifest.json) across the
  RTX 5090 container lane (`v0.7.0-qwen38-5090-beta.2`, source `6d4d0a05` on `64d10fbf`) and the UUID-bound
  native Windows RTX 4090 (`v0.7.0-qwen38-4090-beta.2`) and RTX 3090
  (`v0.7.0-qwen38-3090-beta.2`) lanes (source `7a25cd72` on `64d10fbf`).
- [UDPSendToFailed/ninfer-4090](https://github.com/UDPSendToFailed/ninfer-4090) ports the engine
  to RTX 4090 (`sm_89`) with E8-lattice KV quantization, DirectStorage weight DMA, and D3D12
  residency management. It originated the native Windows RTX 4090 lineage before the mainline
  native runtime converged in `alphastorm/ninfer`.
- [Don-Chad/ninfer-3090](https://github.com/Don-Chad/ninfer-3090) ports the engine to RTX 3090
  (`sm_86`) with ReplaySSM and RotorQuant KV compression. It originated the historical v0.7.2
  RTX 3090 lineage; current native Windows RTX 3090 releases build from the mainline
  `alphastorm/ninfer` native runtime for `sm_86`.

Numbers in the table below for `Neroued/ninfer`, `UDPSendToFailed/ninfer-4090`, and
`Don-Chad/ninfer-3090` are published by each repository's maintainers on their own profiles,
models, and quantization schemes; they are not cross-comparable and are not claims of this
product. Product claims for OMP NInfer are bound to the per-lane qualification receipts in
[`releases/v0.13.1/manifest.json`](../releases/v0.13.1/manifest.json) and detailed in
[`BENCHMARKS.md`](BENCHMARKS.md).

| Repository | GPU | Published highlights | Relationship |
| --- | --- | --- | --- |
| [Neroued/ninfer](https://github.com/Neroued/ninfer) | RTX 5090 (`sm_120a`) | 1,313.8 aggregate tok/s at C=8 (35B-A3B); 15,544 tok/s prefill at 7,680 tokens (maintainer-reported) | The original engine; everything below forks or derives from it |
| [alphastorm/ninfer](https://github.com/alphastorm/ninfer) | RTX 5090, RTX 4090, RTX 3090 | v0.13.1 runtime receipts: RTX 5090 179.86 server / 176.27 wall tok/s (2,048-token decode, DFlash2 K=7, BF16 KV, carried from v0.13.0); native RTX 4090 150.94 tok/s C1 decode (87.59% MTP3 acceptance, INT8 KV); native RTX 3090 84.06 tok/s C1 decode (92.96% MTP3 acceptance, INT8 KV, 300 W cap) | This product's public runtime source and qualified component releases |
| [UDPSendToFailed/ninfer-4090](https://github.com/UDPSendToFailed/ninfer-4090) | RTX 4090 (`sm_89`) | 229.9 tok/s MTP7 deep-context decode; 10.1 GB/s DirectStorage cold weight DMA; E8-lattice KV to 567K-token ceilings (maintainer-reported) | Upstream of the original native RTX 4090 port |
| [Don-Chad/ninfer-3090](https://github.com/Don-Chad/ninfer-3090) | RTX 3090 (`sm_86`) | 165.3 tok/s decode at C=8; RotorQuant KV to 247,872-token contexts; ReplaySSM (maintainer-reported) | Upstream of the historical v0.7.2 RTX 3090 lineage |

## Closest semantic prior art

### [vLLM Agentic API](https://github.com/vllm-project/agentic-api)

A stateful gateway in front of stateless vLLM core. Its public design includes OpenAI-compatible
Responses, `previous_response_id`, tool-oriented request state, SSE/WebSocket transport, and
SQLite/Postgres persistence. It is the closest public prior art for stateful Responses semantics.
As of 2026-08 its [roadmap](https://github.com/vllm-project/agentic-api/blob/main/ROADMAP.md)
still lists reliable `previous_response_id` state hydration as active work.

OMP NInfer does not insert Agentic API because OMP already owns the authoritative transcript and
transactional provider snapshot while NInfer owns local response and checkpoint state. Adding
another stateful gateway would create a second continuation and recovery owner without improving
the local single-owner routes. Agentic API remains a useful comparison if multi-client server-side
durable conversation storage becomes a product requirement.

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

Those systems establish extensive KV and prefix-cache prior art, and they fully cover the
live-process append-only case. OMP NInfer's relevant distinction is that continuation is
explicit, transactional, and durable rather than an implicit longest-prefix match: OMP publishes
the transcript before committing a provider baseline, lineage (forks, rollback) is addressable
through `previous_response_id`, and across all three qualified lanes the continuation is
checkpointed to local NVMe so it survives inference-server restarts within each profile's restore
boundary — which an in-process cache structurally cannot. The user-facing claim is therefore to
keep a long coding session durable and resumable across process restarts on a GPU you own, not
"no re-prefill," not "invent persistent KV," and not universal speedups.

## Distributed inference control planes

- [NVIDIA Dynamo](https://github.com/ai-dynamo/dynamo) targets distributed inference serving and
  disaggregated runtime concerns.
- [llm-d](https://github.com/llm-d/llm-d) targets Kubernetes-native distributed inference.

They address materially broader multi-node and multi-tenant scheduling and serving problems. The
OMP NInfer v0.13.1 contract is one active GPU lane per host, one resident Qwen3.8 27B artifact per
lane, one trusted owner, and bounded local concurrency (two requests in flight on the RTX 5090
container lane; one request at a time on each native Windows lane, with only one native lane
running at a time on port `18082`); a distributed control plane would add cost without serving the
local single-owner workflow.

## Why direct OMP to NInfer

The direct route is intentional:

- OMP already owns coding sessions, tools, branches, replay, and durable transcript publication;
- NInfer already owns Qwen execution, authenticated status, Responses state, and local checkpoint
  and GPU cache lifetime;
- the documented launchers, native controllers, and SSH/local-loopback transports already supply
  the narrow private machine boundary; and
- the product manifest binds exact bytes and support claims across both.

A new gateway or generic model framework should be introduced only if a named requirement cannot be
owned cleanly by those existing boundaries.

[Canonical facts](FACTS.md) · [Decision guide](DECISION_GUIDE.md) ·
[Benchmarks](BENCHMARKS.md) · [Quickstart](QUICKSTART.md)

Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.
