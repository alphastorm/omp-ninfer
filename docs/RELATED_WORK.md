# Related work

Oh My Pi (coding-agent client) → OMP NInfer (qualified appliance and release layer) → NInfer
(inference engine) → Qwen3.8 27B (served model).

Stateful model APIs, prefix/KV reuse, local model servers, and distributed inference all have
strong prior art. OMP NInfer's contribution is the exact product integration:
[Oh My Pi](https://github.com/can1357/oh-my-pi) (OMP) transcript and tool semantics, transactional
provider continuation, a target-specific NInfer/Qwen runtime, a private client-to-GPU topology,
and one release and qualification authority. It does not claim invention of stateful Responses or
persistent KV caching.

## The NInfer family

The runtime is not ours alone; it rides an ecosystem of single-GPU NInfer ports, and the credit
ordering matters:

- [Neroued/ninfer](https://github.com/Neroued/ninfer) is the original from-scratch C++20/CUDA
  engine for registered Qwen checkpoints on one RTX 5090 (`sm_120a`): the `.ninfer` artifact
  format, multi-token prediction (MTP) and [DFlash2](FACTS.md#glossary) speculative decoding,
  hybrid Gated DeltaNet execution, vision, and the published performance and evaluation
  campaigns. Apache-2.0.
- [alphastorm/ninfer](https://github.com/alphastorm/ninfer) is this product's runtime fork of
  `Neroued/ninfer`. It adds stateful OpenAI Responses continuation, fork, and delete semantics;
  durable local NVMe checkpoints; authenticated status identity; container, OCI, SBOM, and native
  Windows release packaging; and the qualification evidence. The qualified components for the
  RTX 5090 container lane and the GPU-UUID-bound native Windows RTX 4090 and RTX 3090 lanes are
  bound in [the current release](FACTS.md#current-release).
- [UDPSendToFailed/ninfer-4090](https://github.com/UDPSendToFailed/ninfer-4090) ports the engine to
  RTX 4090 (`sm_89`) with E8-lattice KV quantization, DirectStorage weight DMA, and D3D12 residency
  management. It originated the native Windows RTX 4090 lineage before the mainline native runtime
  converged in `alphastorm/ninfer`.
- [Don-Chad/ninfer-3090](https://github.com/Don-Chad/ninfer-3090) ports the engine to RTX 3090
  (`sm_86`) with ReplaySSM and RotorQuant KV compression. It originated the first RTX 3090
  lineage; native Windows RTX 3090 releases build from the mainline `alphastorm/ninfer` native
  runtime for `sm_86` ([fork-point rationale](UPSTREAM.md#why-the-fork-points-are-what-they-are)).

Numbers below for `Neroued/ninfer`, `UDPSendToFailed/ninfer-4090`, and `Don-Chad/ninfer-3090` come
from each repository's maintainers on their own profiles, models, and quantization schemes; they
are not cross-comparable or claims of this product. OMP NInfer claims are bound in
[the current release](FACTS.md#current-release) and measured in
[current qualified results](BENCHMARKS.md#current-qualified-results).

| Repository | GPU | Published highlights | Relationship |
| --- | --- | --- | --- |
| [Neroued/ninfer](https://github.com/Neroued/ninfer) | RTX 5090 (`sm_120a`) | 1,313.8 aggregate tok/s at C=8 (35B-A3B); 15,544 tok/s prefill at 7,680 tokens (maintainer-reported) | The original engine; everything below forks or derives from it |
| [alphastorm/ninfer](https://github.com/alphastorm/ninfer) | RTX 5090, RTX 4090, RTX 3090 | Per-lane qualification receipts in [current qualified results](BENCHMARKS.md#current-qualified-results) | This product's public runtime source and qualified component releases |
| [UDPSendToFailed/ninfer-4090](https://github.com/UDPSendToFailed/ninfer-4090) | RTX 4090 (`sm_89`) | 229.9 tok/s MTP7 deep-context decode; 10.1 GB/s DirectStorage cold weight DMA; E8-lattice KV to 567K-token ceilings (maintainer-reported) | Upstream of the original native RTX 4090 port |
| [Don-Chad/ninfer-3090](https://github.com/Don-Chad/ninfer-3090) | RTX 3090 (`sm_86`) | 165.3 tok/s decode at C=8; RotorQuant KV to 247,872-token contexts; ReplaySSM (maintainer-reported) | Upstream of the original RTX 3090 port |

## Closest semantic prior art

### [vLLM Agentic API](https://github.com/vllm-project/agentic-api)

A stateful gateway in front of stateless vLLM core. Its public design includes OpenAI-compatible
Responses, `previous_response_id`, tool-oriented request state, SSE/WebSocket transport, and
SQLite/Postgres persistence. It is the closest public prior art for stateful Responses semantics.
When reviewed in 2026-08, its
[roadmap](https://github.com/vllm-project/agentic-api/blob/main/ROADMAP.md) listed reliable
`previous_response_id` state hydration as active work.

OMP NInfer does not insert Agentic API because OMP already owns the authoritative transcript and
transactional provider snapshot while NInfer owns local response and checkpoint state. Adding
another stateful gateway would create a second continuation and recovery owner without improving
the local single-owner routes. Agentic API remains a useful comparison if multi-client server-side
durable conversation storage becomes a product requirement.

### [Ollama](https://docs.ollama.com/api/openai-compatibility)

A widely used local runtime with OpenAI-compatible endpoints and accessible install UX. Its
documented Responses compatibility is not the OMP-owned `previous_response_id` transaction here;
choose Ollama when model and hardware breadth matter more than one qualified NInfer/Qwen/RTX route.

### [LM Studio](https://lmstudio.ai/docs)

A polished desktop path to discovering and running local models, with a headless daemon, OpenAI-
and Anthropic-compatible local endpoints, tool calling, and structured output. Its documented
endpoints are stateless chat-style requests: the client holds cross-turn state, and no
`previous_response_id` continuation contract is documented. LM Studio is a better fit when desktop
model management and catalog breadth matter more than one qualified stateful OMP route.

Adjacent single-machine servers with strong NVIDIA followings —
[TabbyAPI](https://github.com/theroyallab/tabbyAPI) (ExLlama-based) and
[mistral.rs](https://github.com/EricLBuehler/mistral.rs) — also serve quant-focused
OpenAI-compatible endpoints as stateless per-request calls.

### [LocalAI](https://github.com/mudler/LocalAI)

A broad local OpenAI-compatible serving layer across multiple backends and modalities. OMP NInfer
chooses a narrower target-specific runtime and avoids a second translation/control layer. LocalAI's
breadth is a feature for a different product boundary, not a deficiency.

## Prefix and KV reuse

- [Neroued/ninfer](https://github.com/Neroued/ninfer) itself ships in-process prefix reuse (its
  `prefix_reuse` engine setting, enabled in every lane profile here): a live process avoids
  recomputing an append-only prefix with no OMP NInfer involvement.
- [vLLM Automatic Prefix Caching](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/)
  reuses matching prefix blocks inside vLLM.
- [LMCache](https://github.com/LMCache/LMCache) extends KV reuse and movement across inference
  instances and storage tiers.
- [SGLang HiCache](https://docs.sglang.ai/advanced_features/hicache_best_practices.html) manages
  hierarchical KV cache tiers.
- [llama.cpp server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)
  exposes slots and cache-oriented local serving behavior.

Those systems establish extensive KV and prefix-cache prior art and cover the live-process
append-only case. OMP NInfer differs because continuation is explicit, transactional, and durable
rather than an implicit longest-prefix match. OMP commits the transcript before advancing the
provider baseline, and `previous_response_id` addresses forks and rollback. Across all three
qualified lanes, local NVMe checkpoints preserve continuation across server restarts within each
lane's [durability boundary](FACTS.md#durability) (same runtime, model, profile, and credentials),
which an in-process cache cannot do. The product claim is a long coding session that survives
process restarts on a GPU you own — not "no re-prefill", not inventing persistent KV, and not
universal speedups.

## Distributed inference control planes

- [NVIDIA Dynamo](https://github.com/ai-dynamo/dynamo) targets disaggregated distributed serving.
- [llm-d](https://github.com/llm-d/llm-d) targets Kubernetes-native distributed inference.

Both address multi-node and multi-tenant scheduling and serving. The OMP NInfer contract is one
active GPU lane per host, one resident Qwen3.8 27B model per lane, one trusted owner, and at most
two requests in flight on a lane ([lanes and limits](FACTS.md#lanes-and-limits)). A distributed
control plane would add cost without serving this local single-owner workflow.

## Why direct OMP to NInfer

The direct route is intentional:

- OMP already owns coding sessions, tools, branches, replay, and durable transcript publication;
- NInfer already owns Qwen execution, authenticated status, Responses state, and local checkpoint
  and GPU cache lifetime;
- the documented launchers, native controllers, and SSH/local-loopback transports already supply
  the narrow private machine boundary; and
- the release manifest in [the current release](FACTS.md#current-release) binds exact bytes and
  support claims across client and runtime.

Add a gateway or generic framework only when existing boundaries cannot own a named requirement.

## Review dates

External sources were reviewed on 2026-08-26, the NInfer family section on 2026-08-28, and the
local-server section on 2026-08-29. These projects move quickly; consult their current
documentation before making a deployment decision.

[Canonical facts](FACTS.md) · [Decision guide](DECISION_GUIDE.md) ·
[Benchmarks](BENCHMARKS.md) · [Quickstart](QUICKSTART.md)

Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.
