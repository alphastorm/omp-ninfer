# OMP NInfer — canonical facts

Last verified: 2026-08-31 · Current stable release: **v0.4.6**

Everything on this page is bound to the [v0.4.6 release manifest](../releases/v0.4.6/manifest.json)
and its qualification receipts; the test suite rejects drift between these claims and the receipts.

## What it is

OMP NInfer is **durable local inference for coding agents**: the qualified local inference
appliance for Oh My Pi. It runs Qwen3.8 27B through the NInfer engine on one NVIDIA RTX 5090,
4090, or 3090 and preserves explicit OpenAI Responses continuation state across process restarts.

## Entity relationships

```text
Oh My Pi     = the coding-agent client (github.com/can1357/oh-my-pi)
OMP NInfer   = this project: the qualified integration, release, and appliance layer
NInfer       = the C++/CUDA inference engine (Neroued/ninfer and its GPU ports)
Qwen3.8 27B  = the served model (registered NInfer artifact, hash-pinned per release)
```

## Best fit

All of these should be materially true:

- the operator uses, or intends to use, Oh My Pi;
- they own a qualified RTX 5090, 4090, or 3090 setup;
- Qwen3.8 27B is the model they want;
- sessions are long-lived and stateful, and restart recovery matters;
- privacy and owned hardware matter more than breadth or multi-user throughput.

## Not a fit

- A GUI-first local experience (use LM Studio).
- Broad model catalogs and quick experimentation (use Ollama or LM Studio).
- Unsupported hardware or maximum portability (use llama.cpp).
- Multi-user or high-concurrency serving (use vLLM).
- Generic OpenAI-compatible inference without the durability contract.

## Qualified hardware

| Lane | Form | Context ceiling | Release |
|---|---|---:|---|
| RTX 5090 | Linux container (Docker/WSL2) | 131,072 | v0.4.6 durable container with fanout, decoupled export, and origin-authenticated checkpoints |
| RTX 4090 | native Windows service | 131,072 | durable v0.2 lane (native Windows, MTP3, bound by v0.4.6) |
| RTX 3090 | native Windows service | 65,536 | durable v0.2.2 lane (bound by v0.4.6) |

## Current model and artifact

Registered NInfer conversion of Qwen3.8 27B (`qwen3_8_27b.ninfer`, groupwise-int weights,
18,210,531,328 bytes), artifact SHA-256 `eec39564…14bf3e`, pinned identically across all three
lanes by the release manifest.

## Supported APIs

OpenAI Responses (stateful continuation — the primary product surface), OpenAI chat completions,
and Anthropic Messages, all loopback-only and bearer-authenticated. Session checkpoint
save/status/delete under `/v1/ninfer/checkpoints`.

## The durable-state guarantee

Explicit, transactional continuation checkpoints that survive process death: sessions are
checkpointed to local NVMe (SHA-manifested, atomically published generations) and restored
exactly — the restored frontier is verified, and a wrong-profile checkpoint is rejected rather
than partially loaded. This is a stronger, explicit contract than in-process prefix caching.

As of v0.4.4 on the RTX 5090 lane, sibling agent branches of one `previous_response_id` reuse
the base prefill through the session's private long anchors, and checkpoint exports run off the
engine execution lock (four branches: 148.7 s → 3.84 s at a 67.7K-token base; warm follow-up
during checkpoint traffic 0.91 s; automatic saves debounce to sustained-idle and skip
already-catalogued frontiers).

Operators may describe this problem as persistent KV cache, restartable context, session
checkpointing, stateful local inference, or avoiding cold re-prefill. The actual guarantee is
explicit restorable continuation state; it does **not** claim that new input avoids prefill.

## Security boundary

Loopback-only listeners; bearer authentication with a user-only key file; fail-closed instead of
cloud fallback; every byte (model, binary, image, config) hash-pinned by the release manifest;
remote lanes reached through authenticated SSH local forwards.

## Measured proof (v0.4.0, RTX 5090 lane)

- 109,589 tokens restored after a docker restart; **0.778 s** to first token from the durable
  checkpoint vs **47.920 s** fresh-process cold rebuild.
- **144.80 tok/s** decode on the agent-shaped qualification gate (44.10% MTP acceptance);
  152.2 tok/s at 83.3% acceptance on the retrieval workload.
- Exact needle retrieval at a **130,448-token** prompt.
- Full receipts: [benchmarks](BENCHMARKS.md) · [release manifest](../releases/v0.4.0/manifest.json).

Warm/cold figures are always retained state versus fresh-process cold start — never versus an
ordinary in-process follow-up.

## Known limitations

- One model, one active request per lane (max concurrency 1); not a serving farm.
- Checkpoints are runtime-fingerprint-bound: they restore only on an identical lane
  (same binary, artifact, and profile) — not across GPU models.
- The 3090 lane's comfortable working envelope is the 64K class.
- Vision is available on the 5090 container profile; the native Windows lanes are text-only.

## Claims we do not make

- "No re-prefill" — in-process prefix caching is prior art and conceded as such.
- "Fastest local inference" — figures are one profile on one machine, receipt-bound.
- "First persistent KV cache" — prior art is credited in [Related work](RELATED_WORK.md).
- Production/GA/SLA claims beyond the qualified envelope of the current release.

## Primary evidence

[Release manifest](../releases/v0.4.4/manifest.json) ·
[Benchmarks and method](BENCHMARKS.md) · [Compatibility](COMPATIBILITY.md) ·
[Security model](SECURITY.md) · [Quickstart](QUICKSTART.md) ·
[Decision guide](DECISION_GUIDE.md)
