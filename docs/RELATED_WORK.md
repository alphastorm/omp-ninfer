# Related work

Stateful model APIs, prefix/KV reuse, local model servers, and distributed inference all have strong
prior art. OMP NInfer's contribution is the exact product integration: OMP transcript and tool
semantics, transactional provider continuation, a target-specific NInfer/Qwen runtime, a private
Mac-to-GPU topology, and one release/qualification authority. It does not claim invention of
stateful Responses or persistent KV caching.

Sources below were reviewed on 2026-08-26. These projects move quickly; consult their current
documentation before making a deployment decision.

## Closest semantic prior art

### [vLLM Agentic API](https://github.com/vllm-project/agentic-api)

A stateful gateway in front of stateless vLLM core. Its public design includes OpenAI-compatible
Responses, `previous_response_id`, tool-oriented request state, SSE/WebSocket transport, and
SQLite/Postgres persistence. It is the closest public prior art for stateful Responses semantics.

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

### [LocalAI](https://github.com/mudler/LocalAI)

A broad local OpenAI-compatible serving layer across multiple backends and modalities. OMP NInfer
chooses a narrower target-specific runtime and avoids a second translation/control layer. LocalAI's
breadth is a feature for a different product boundary, not a deficiency.

## Prefix and KV reuse

- [vLLM Automatic Prefix Caching](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/)
  reuses matching prefix blocks inside vLLM.
- [LMCache](https://github.com/LMCache/LMCache) extends KV reuse and movement across inference
  instances and storage tiers.
- [SGLang HiCache](https://docs.sglang.ai/advanced_features/hicache_best_practices.html) manages
  hierarchical KV cache tiers.
- [llama.cpp server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server) exposes slots and
  cache-oriented local serving behavior.

Those systems establish extensive KV/prefix-cache prior art. OMP NInfer's relevant distinction is
ownership and commit ordering: OMP publishes the transcript before committing a provider baseline;
NInfer's retained state is an acceleration that may be discarded without losing the conversation.
The user-facing claim is therefore “stop re-prefilling the same long coding session every turn,” not
“invent persistent KV” or “make inference 100× faster.”

## Distributed inference control planes

- [NVIDIA Dynamo](https://github.com/ai-dynamo/dynamo) targets distributed inference serving and
  disaggregated runtime concerns.
- [llm-d](https://github.com/llm-d/llm-d) targets Kubernetes-native distributed inference.

They address materially broader multi-node/multi-tenant scheduling and serving problems. The current
OMP NInfer v0.1 contract is one GPU, one resident model, one trusted owner, and one active request; a
distributed control plane would add cost without satisfying the early-access outcome.

## Why direct OMP to NInfer

The direct route is intentional:

- OMP already owns coding sessions, tools, branches, replay, and durable transcript publication;
- NInfer already owns Qwen execution, authenticated status, Responses state, and GPU cache lifetime;
- SSH already supplies the narrow private machine transport for v0.1; and
- the product manifest binds exact bytes and support claims across both.

A new gateway or generic model framework should be introduced only if a named requirement cannot be
owned cleanly by those existing boundaries.
