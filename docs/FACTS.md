# OMP NInfer — canonical facts

Updated: 2026-10-26 · Published release: v0.13.1 (2026-10-26) · stock Oh My Pi 18.12.6

Oh My Pi (coding-agent client) → OMP NInfer (qualified appliance and release layer) → NInfer
(inference engine) → Qwen3.8 27B (served model).

**Qualified on RTX 5090 · 4090 · 3090**, bound to the exact profiles in
[`releases/v0.13.1/manifest.json`](../releases/v0.13.1/manifest.json).
[Get started](QUICKSTART.md) ·
[Download v0.13.1](https://github.com/alphastorm/omp-ninfer/releases/tag/v0.13.1)

## What it is

OMP NInfer is **durable local inference for coding agents**: the qualified local inference
appliance for [Oh My Pi](https://github.com/can1357/oh-my-pi) (OMP). It runs Qwen3.8 27B through
the NInfer engine on one user-owned NVIDIA RTX 5090, RTX 4090, or RTX 3090 and preserves explicitly
checkpointed OpenAI Responses continuation state across inference-server restarts within each
profile's restore boundary.

- **Oh My Pi** ([`can1357/oh-my-pi`](https://github.com/can1357/oh-my-pi)) owns the coding-agent
  client: the authoritative conversation transcript, typed tools, branches, subagents, compaction,
  and transcript replay.
- **NInfer** ([`Neroued/ninfer`](https://github.com/Neroued/ninfer) and
  [`alphastorm/ninfer`](https://github.com/alphastorm/ninfer)) owns single-GPU Qwen3.8 27B
  execution, retained OpenAI Responses continuation state, and local NVMe checkpoint storage.
- **OMP NInfer** (`alphastorm/omp-ninfer`) owns the integration and release layer: setup routes,
  hardware profiles, release manifests, qualification receipts, security boundaries, and support
  scope. It ships no forked OMP binary and inserts no extra gateway between OMP and NInfer.

## Best fit

All of these should be materially true:

- The operator uses, or intends to use, Oh My Pi.
- They own an eligible RTX 5090, RTX 4090, or RTX 3090 setup matching the exact release profile.
- Qwen3.8 27B is the model they want to run.
- Sessions are long-lived and stateful, and resuming across inference-server restarts matters.
- Privacy and owned hardware matter more than model catalog breadth or multi-user throughput.

## Not a fit

- A GUI-first local experience (use LM Studio).
- Broad model catalogs and quick experimentation (use Ollama or LM Studio).
- Unsupported hardware or maximum portability (use llama.cpp).
- Multi-user or high-concurrency serving (use vLLM).
- Generic OpenAI-compatible inference without the explicit durability contract.

See the [decision guide](DECISION_GUIDE.md) for the side-by-side comparison.

## Current release

Published release **v0.13.1** (2026-10-26, GitHub `Latest`) binds unmodified upstream Oh My Pi
**18.12.6** (`45c35e40`, tree `8a90a1b4`) and shared published model container version 3 `81f924d4`
(`qwen3_8_27b-v3.ninfer`, 20,437,521,664 bytes, revision `1cbd84e7`) across all three qualified GPU
lanes: it rebases the native Windows RTX 4090 (`v0.7.0-qwen38-4090-beta.2`, profile
`qwen38-4090-native-v0.7.0-beta.2`, public config `b21cdaf8`) and RTX 3090
(`v0.7.0-qwen38-3090-beta.2`, profile `qwen38-3090-native-v0.7.0-beta.2`, public config `b49aad99`)
lanes onto upstream `Neroued/ninfer` master `64d10fbf` at frozen source `7a25cd72`, while carrying
the qualified v0.13.0 RTX 5090 container runtime (`v0.7.0-qwen38-5090-beta.2`, source `6d4d0a05` on
`64d10fbf`, strict-origin profile `qwen38-5090-v0.13.0`, config `751d22dc`) and stock OMP 18.12.6
client binaries unchanged. Release authority:
[`releases/v0.13.1/manifest.json`](../releases/v0.13.1/manifest.json) ·
[`releases/v0.13.1/NINFER_RELEASE_NOTES.md`](../releases/v0.13.1/NINFER_RELEASE_NOTES.md) ·
[`COMPATIBILITY.md`](COMPATIBILITY.md). The
[client upgrade review](measurements/2026-10-25-omp-18126-client-upgrade-review.json) records the
host-free checks across the Responses wire contract, image-aware snapcompact gate, and print-mode
slash dispatch.

| Component or lane | Form and transport | Release tag and source | Image or package | Serving profile | Context | Requests in flight | Speculative backend | Modalities |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
| Oh My Pi client | Unmodified upstream release binaries: macOS arm64 (preview), Windows x64, Linux x64 (WSL2 live evidence) | `v18.12.6`, source `45c35e40`, tree `8a90a1b4` | `omp-darwin-arm64` (`cfbb5e38`), `omp-windows-x64.exe` (`73d73c11`), `omp-linux-x64` (`85d9daf3`) in [`client-components.json`](../releases/v0.13.1/qualification/client-components.json) | Per-model `compat.statefulResponses: true`, fail-closed config | 131,072 | `2` on RTX 5090; `1` per native lane | Target lane | Coding agent, typed tools, branches, compaction |
| RTX 5090 | Windows 11 + Docker Desktop/WSL2 container on loopback `127.0.0.1:18089`; local Windows client or macOS client over manual SSH tunnel (preview) | `v0.7.0-qwen38-5090-beta.2`, source `6d4d0a05` on `64d10fbf` | OCI image `5d10a998` (base `d4377ed0`), server `9790a004`, model `81f924d4` | `qwen38-5090-v0.13.0`, config `751d22dc`: BF16 KV (146,368 automatic KV tokens), shared Host budget 20,867.734375 MiB (21,881,405,440 B), 28,672 MiB host floor, 60,000 ms keep-warm, mandatory `--session-checkpoint-require-origin-auth`, `/checkpoints-v013` (schema 3) | 131,072 | 2 (plus 2 extra device-state slots, 180 s pending timeout) | DFlash2 draft window 7 | Vision, text, typed tools, JSON-schema output, preserved thinking |
| RTX 4090 native Windows 11 | Native Windows package on loopback `127.0.0.1:18082`, UUID-bound GPU on a two-GPU host | `v0.7.0-qwen38-4090-beta.2`, source `7a25cd72` on `64d10fbf` | Package `ffaa410a` (950,981,452 B), server `cfc3e066`, SPDX `d6314fc1`, CycloneDX `c5d9141e`, model `81f924d4` | `qwen38-4090-native-v0.7.0-beta.2`, public config `b21cdaf8`: INT8 KV, shared Host budget 14,787.734375 MiB (15,506,063,360 B), 640 MiB admission headroom, 32,768 MiB host floor, 2,048-token prefill chunk, 60,000 ms keep-warm, mandatory `--session-checkpoint-require-origin-auth`, `session-checkpoints-v3` (schema 3) | 131,072 | 1 (plus 2 extra device-state slots, 30 s pending timeout) | MTP3 (3 draft tokens, `--lm-head-draft`) | Text, typed tools, JSON-schema output, preserved thinking (no vision) |
| RTX 3090 native Windows 11 | Native Windows package on loopback `127.0.0.1:18082`, UUID-bound GPU on the same two-GPU host | `v0.7.0-qwen38-3090-beta.2`, source `7a25cd72` on `64d10fbf` | Package `626ba6ff` (967,836,157 B), server `cdd24c5e`, SPDX `4021054d`, CycloneDX `fc28d50e`, model `81f924d4` | `qwen38-3090-native-v0.7.0-beta.2`, public config `b49aad99`: INT8 KV, shared Host budget 11,715.734375 MiB (12,284,837,888 B), 768 MiB admission headroom, 1,024-token prefill chunk, 300 W serving power cap (370 W restored on stop), keep-warm off, mandatory `--session-checkpoint-require-origin-auth`, `session-checkpoints-v3` (schema 3) | 131,072 | 1 (plus 4 extra device-state slots, 30 s pending timeout) | MTP3 (3 draft tokens, `--lm-head-draft`) | Text, typed tools, JSON-schema output, preserved thinking (no vision) |

- **Sequential native topology on one two-GPU host:** Both native Windows lanes install on the same
  two-GPU Windows 11 host (RTX 4090 at index 0, RTX 3090 at index 1), each bound to its own GPU
  UUID and PCI address. Only one native lane runs at a time on loopback port `18082`. This is not
  multi-GPU inference and not concurrent native serving.
- **First-of-lineage native rollback:** Both rebased native Windows lanes
  (`v0.7.0-qwen38-4090-beta.2` and `v0.7.0-qwen38-3090-beta.2`) are the first release of their
  `64d10fbf` / model v3 lineage on the two-GPU host and have no supported rollback target
  (`not_applicable`, zero directions); the historical RTX 3090 two-direction rollback result
  against `v0.6.2-beta.1` does not transfer across the model and runtime rebase. Keep prior native
  release roots untouched for historical recovery.
- **Admission on the RTX 5090 and 24 GB native lanes:** Two requests run together on the RTX 5090
  only while both prompts plus output reservations fit inside its 146,368-token automatic BF16 KV
  pool; excess requests wait up to 180 s. Native RTX 4090 and RTX 3090 profiles set
  `--admission-headroom-mib` to 640 MiB and 768 MiB respectively at the full 131,072-token
  context/KV ceiling (retaining the 32,768 MiB RTX 4090 host RAM floor; no smaller-host
  qualification is claimed), and admission waits for prepared off-worker export leases when
  capacity can become available, releasing leases before waking admission.
- **Schema 3 checkpoint stores and Windows durability:** All three lanes use schema 3
  checkpoints (fingerprint schema 2, status schema 2, request-log schema 30) with mandatory
  `--session-checkpoint-require-origin-auth` (requiring a configured checkpoint root and at least a
  32-byte API key; the documented generated key is 64 characters). The RTX 5090 container mounts
  host directory `checkpoints-v013` at `/checkpoints-v013` with non-blocking export; native lanes
  use `cache/<release-instance-id>/session-checkpoints-v3` under each immutable component release's
  own cache root (for example, `qwen38-4090-native-v0.7.0-beta.2-7a25cd72f490` or
  `qwen38-3090-native-v0.7.0-beta.2-7a25cd72f490`) with handle-anchored replacement, extended-length roots, and a current-parent
  publication fence (Windows `ntfs-write-through` is not POSIX `fsync` or a power-loss guarantee;
  physical disk exhaustion returns `capacity`, including HTTP 409 on DELETE without mutating
  surviving Responses objects). Keep prior checkpoint roots untouched; prior sessions resume by
  replaying authoritative OMP transcripts for a fresh prefill.
- **Dual native SBOMs:** Each native outer asset set (10 hashed entries plus `SHA256SUMS`, 11
  files) ships both its SPDX file inventory (`<package-stem>.spdx.json`) and a separate canonical
  CycloneDX 1.5 dependency inventory (`<package-stem>.cdx.json`) covering resolved vcpkg
  dependencies, CUDA 13.3 DLLs, vendored sources, MSVC CRT, and DirectStorage redistributables.
- **Fresh route and native runtime acceptance:** Fresh v0.13.1 acceptance on frozen candidate
  `92dfb132` passed all five documented routes (31 blocks), all three stock 18.12.6 clients (typed
  tool turn, exact continuation, fail-closed request, plus macOS/Windows image input on RTX 5090),
  and both first-of-lineage beta.2 native public installs (7/7 blocks and 19/19 route-behavior
  checks on both RTX 4090 and RTX 3090; canonical roots freshly promoted from the documented blocks
  before idempotent `already_installed` public-URL checks), with independent host restoration
  (429.388 s RTX 5090 hold, 370.64 s RTX 4090 window, 398.01 s RTX 3090 window;
  [`documented-routes.json`](../releases/v0.13.1/acceptance/documented-routes.json),
  [`composed-external-installation.json`](../releases/v0.13.1/acceptance/composed-external-installation.json),
  [`2026-10-26-v0131-acceptance-restoration.json`](measurements/2026-10-26-v0131-acceptance-restoration.json)).
  Native runtime qualifications are fresh at `7a25cd72` (both native-runtime and product-tooling
  full councils closed without remediation in
  [`review/runtime-ledger.json`](../releases/v0.13.1/review/runtime-ledger.json), with deferred
  residuals tracked in [#88](https://github.com/alphastorm/omp-ninfer/issues/88),
  [#89](https://github.com/alphastorm/omp-ninfer/issues/89), and
  [#90](https://github.com/alphastorm/omp-ninfer/issues/90)); RTX 5090 runtime qualification carries
  unchanged from v0.13.0 (`6d4d0a05`).

## Models

v0.13.1 pins one shared registered NInfer conversion artifact (`qwen3_8_27b.ninfer`) from
[`neroued/Qwen3.8-27B-NInfer`](https://huggingface.co/neroued/Qwen3.8-27B-NInfer) across all three
lanes in [`releases/v0.13.1/manifest.json`](../releases/v0.13.1/manifest.json) (removing the
redundant `components.native_model` override):

| Lane scope | Hugging Face revision | Bytes | SHA-256 | Notes |
| --- | --- | ---: | --- | --- |
| All qualified lanes (`components.model`: RTX 5090 container, native RTX 4090, native RTX 3090) | `1cbd84e7221e51186bd7f093a149912d2489625b` | 20,437,521,664 | `81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da` | Published model container version 3 (`qwen3_8_27b-v3.ninfer` on host); serves public model ID `q38-ninfer` on RTX 5090 (DFlash2 draft window 7, MTP, text, vision), `qwen3.8-27b` on native RTX 4090, and `q38-ninfer` on native RTX 3090 (MTP3 `--lm-head-draft`, text and tools, vision disabled) |

All routes download the published container version 3 artifact `81f924d4` directly into
`qwen3_8_27b-v3.ninfer`; prior native releases through v0.13.0 used the 18,210,531,328-byte version
2 artifact `eec39564` (revision `18dfc887`), kept untouched on disk for historical recovery. On RTX
5090, all 1,184 tensor payloads and all six frontend resources matched the v0.12.2 model
(`0634abb0`) upgraded locally, while whole-container bytes differ.

## What the route provides

- **Protocols and endpoints:** OpenAI Responses (`/v1/responses`, primary stateful surface), OpenAI
  Chat Completions (`/v1/chat/completions`), Anthropic Messages (`/v1/messages` and
  `/v1/messages/count_tokens`), authenticated runtime identity (`/v1/ninfer/status`), and session
  checkpoint save/status/delete (`/v1/ninfer/checkpoints`).
- **Explicit continuation and lineage:** Continuation is addressed through `previous_response_id`
  with session identity derived from `prompt_cache_key` under bearer authentication (never stored
  raw; rejected if mixed with legacy `ninfer_session` or `X-NInfer-Session`). Sibling forks, parent
  deletion without descendant loss, and cross-session isolation are qualified on all three lanes.
  Within one API-key principal, `prompt_cache_key` names a session capability; use unique
  high-entropy keys and do not share that principal among mutually untrusted clients.
- **Tools, vision, structured output, and preserved thinking:** Typed tool calling, content-part
  array tool outputs, enforced JSON-schema structured output (`text.format` on Responses and
  `response_format` with `json_schema` on Chat Completions), 128-character Chat/Responses tool
  names, and preserved thinking (`reasoning_text` deltas with `summary: []`) are qualified on all
  three lanes. Vision inputs (including image tool results and `snapcompact` image archives) are
  qualified on the RTX 5090 container lane only; native RTX 4090 and RTX 3090 lanes refuse image
  inputs with `vision_disabled`.
- **Oh My Pi client contract:** Stock Oh My Pi 18.12.6 has no `omp appliance` commands. Model
  fragments set `compat.statefulResponses: true` per model (upstream
  [#13686](https://github.com/can1357/oh-my-pi/pull/13686)), and `PI_OPENAI_STATEFUL` must be
  absent from the environment. Custom Responses hosts default to `auto` image detail upstream
  ([#13687](https://github.com/can1357/oh-my-pi/pull/13687)), removing the old
  `supportsImageDetailOriginal` override, and unavailable saved models fail closed
  ([#13689](https://github.com/can1357/oh-my-pi/pull/13689)).
  [`examples/manual-tunnel/fail-closed.yml`](../examples/manual-tunnel/fail-closed.yml) disables
  retries, model fallback, and `checkUpdate`, leaves compaction at the OMP default, and sets
  `providers.maxInFlightRequests` per provider ID (`ninfer-beta: 2`, `ninfer-main: 2`,
  `ninfer-native-4090: 1`, `ninfer-native-3090: 1`, `ninfer-heavy: 1`).

## Durability

- **Transcript is the source of truth:** Oh My Pi commits each turn to its local transcript before
  advancing the provider continuation baseline. GPU-resident and checkpointed state is an
  acceleration layer, never the sole copy of the conversation.
- **What survives a server restart:** Checkpoints are written to local NVMe as SHA-256-manifested,
  atomically published generations and restore on the first matching request after an
  inference-server restart on all three lanes. Graceful managed stops flush eligible unpublished
  sessions before exit.
- **Best-effort saves and pool bounds:** Checkpointing under live traffic is best effort. Transient
  automatic save refusals retry when the engine quiesces, and admission saves a checkpoint-tagged
  session's newest turn before evicting it, but a crash or expired graceful wait can leave
  unpublished work unsaved. Restore materializes continuation state into the host store (shared
  20,867.734375 MiB / 21,881,405,440-byte Host context budget on RTX 5090, 14,787.734375 MiB /
  15,506,063,360-byte shared Host budget on RTX 4090, 11,715.734375 MiB / 12,284,837,888-byte
  shared Host budget on RTX 3090), and exports that the configuration
  could not admit back are refused (`HTTP 409`).
- **Exact-identity restore requirements:** A checkpoint restores only when the runtime binary
  hash, patch-stack SHA, model artifact, deployment profile, and session credentials match.
  Checkpoints from another GPU lane, an earlier server build, or the legacy fork client's
  `ninfer_session` names are refused rather than partially loaded.
- **Replay fallback and warm-reuse limits:** When a checkpoint is missing, incompatible, or
  declined for capacity, the server returns `previous_response_not_found` and Oh My Pi resends the
  full conversation for one cold root prefill. Starting a new Oh My Pi process to resume a session
  also costs one root prefill because the first resumed request omits prior reasoning tokens.
  Universal warm reuse is not promised (the RTX 5090 multisession control observed root fallback on
  2 of 8 continuations/forks without server errors).

## Checkpoint transport and NAS replication

[`scripts/checkpoint_sync.py`](../scripts/checkpoint_sync.py) exports published checkpoint
generations, verifies file sizes, SHA-256 hashes, and `manifest.mac`, and imports verified
replicas into a local checkpoint root (`python3 scripts/checkpoint_sync.py --help`).

- **Replicas, never live checkpoint roots:** Native O_DIRECT and DirectStorage paths require a
  local filesystem. Network shares and NAS mounts are replica storage only; never point a running
  server at a network share. Publish the checkpoint before export and stop the destination runtime
  before import.
- **Same-lane restore contract:** Restoring an imported replica requires the identical runtime
  binary, model artifact, deployment profile, and bearer key (`--session-checkpoint-require-origin-auth`;
  do not use `--allow-unauthenticated` across trust boundaries). Transport is explicit export and
  import, not cross-GPU migration, cross-version conversion, or automatic failover.
- **Historical transport receipts:** Off-machine export, local wipe, import, and post-restart
  retrieval were verified on the 2026-09-05 profiles
  ([RTX 5090](measurements/2026-09-05-sync-probe-rtx5090.json),
  [RTX 4090](measurements/2026-09-05-sync-probe-rtx4090.json),
  [RTX 3090](measurements/2026-09-05-sync-probe-rtx3090.json)), with separate receipts for
  [cross-site transfer](measurements/2026-09-06-replica-transfer-paths.json) and
  [NAS replication](measurements/2026-09-07-nas-replication-sf-lanes.json).

## Privacy and security boundary

- **Loopback-only listeners:** The runtime binds `127.0.0.1:18089` (RTX 5090 container) or
  `127.0.0.1:18082` (native Windows lanes). Remote macOS clients reach the RTX 5090 host through
  an authenticated SSH local port forward.
- **Bearer authentication and protected state:** Every request requires a user-only bearer key;
  anonymous requests fail with `HTTP 401`. Native Windows state roots enforce Administrator-only
  DACLs verified by low-privilege read and write denial checks.
- **Fail-closed client and pinned bytes:** Oh My Pi disables retries and model fallback so an
  unreachable or mismatched local runtime fails closed instead of falling back to cloud APIs.
  Every client binary, image digest, native package, model artifact, and configuration is SHA-256
  pinned in [`releases/v0.13.1/manifest.json`](../releases/v0.13.1/manifest.json).
- **Single trusted owner:** Designed for one trusted operator on owner-controlled hardware, not
  multi-tenant isolation. Full threat model: [`SECURITY.md`](SECURITY.md).

## Measured proof

Per-lane runtime qualification receipts bound in v0.13.1 (never transfer one lane's numbers or
capabilities to another):

| Lane | Long-context retrieval (130,048 tokens) | Decode measurement | Speculative acceptance | Receipt |
| --- | --- | --- | --- | --- |
| RTX 5090 (`v0.7.0-qwen38-5090-beta.2`, DFlash2 K=7, BF16 KV) | Exact in **56.994 s** cold (57.0 s, 2,281.8 tok/s wall; 56.411 s server) | **179.86 tok/s** server-side (**176.27 tok/s** wall) over 2,048 tokens | **0.244** DFlash2 acceptance, **2.71** tokens/round | [`rtx5090.json`](../releases/v0.13.1/qualification/rtx5090.json) (carried, 2026-10-25) |
| RTX 4090 native (`v0.7.0-qwen38-4090-beta.2`, MTP3, INT8 KV) | Exact in **85.71 s** (85.707 s) | **150.94 tok/s** C1 decode (4,541 prompt / 1,024 completion tokens); prefill **2,190.89 tok/s** | **87.59%** MTP3 acceptance | [`rtx4090.json`](../releases/v0.13.1/qualification/rtx4090.json) (2026-10-26) |
| RTX 3090 native (`v0.7.0-qwen38-3090-beta.2`, MTP3, INT8 KV, 300 W cap) | Exact in **208.78 s** (208.781 s) | **84.06 tok/s** C1 decode (4,541 prompt / 1,024 completion tokens); prefill **921.63 tok/s** | **92.96%** MTP3 acceptance | [`rtx3090.json`](../releases/v0.13.1/qualification/rtx3090.json) (2026-10-26) |

- **v0.13.1 native Windows schema 3 restart and protocol gates:** On frozen native source
  `7a25cd72` and published model `81f924d4`, both native lanes reused **1,647 cached tokens** after
  explicit save and **1,650 cached tokens** after graceful `stop-event` flush across process
  replacement (36.063 s on RTX 4090, 37.203 s on RTX 3090) with counters matching an independently
  measured cold-process baseline, and passed canonical schema 2 product protocol smokes at full and
  reduced (12,438.578125 MiB on RTX 4090; 9,366.578125 MiB on RTX 3090) shared Host budgets
  ([`rtx4090.json`](../releases/v0.13.1/qualification/rtx4090.json),
  [`rtx3090.json`](../releases/v0.13.1/qualification/rtx3090.json)).
- **v0.13.0 RTX 5090 schema 3 restart and provider decode comparison (carried in v0.13.1):** On the
  shipped `6d4d0a05` binary and `81f924d4` model, the four-boot schema 3 restart gate reused
  **20,926 cached tokens** and produced **27 byte-identical continuation bytes** after an
  authenticated `fsync` save of **2,164,056,150 bytes**
  ([`durability.json`](../releases/v0.13.1/qualification/durability.json)), and the 32 GB C2
  restore-overlap gate completed in **38.0356 s** with **1,074,790,400 bytes** headroom and
  **+2 MiB** graph growth
  ([`concurrency.json`](../releases/v0.13.1/qualification/concurrency.json)). Separately, EXP-097's
  A/B/B/A provider comparison (`c2dbcbae` / locally upgraded model `facba3bd`, persistence disabled,
  fixed 131,072-token KV) across 84 serial role cases measured a median **342.150 versus
  338.448 tok/s** (**101.09%** of v0.12.2's `1302d639`,
  [`2026-10-25-exp097-role-corpus.json`](measurements/2026-10-25-exp097-role-corpus.json)).
- **Historical v0.4.0 restart proof (one RTX 5090, 2026-08-30, not a current-release timing or
  restart speedup ratio):** **109,589 retained tokens** served after a Docker restart; **24.8 s
  end-to-end** including first-touch restoration of a **7.95 GB** checkpoint; **56.6 s model
  reload** measured separately; **0.778 s server-side time to first token** after restoration
  ([`2026-08-30-rtx5090-durable-qualification.json`](measurements/2026-08-30-rtx5090-durable-qualification.json)).
  A separate v0.4.0 request pair measured **47.920 s cold wall time versus 1.790 s warm follow-up
  wall time** at 109,594 tokens
  ([`2026-08-30-warm-vs-cold-v04.json`](measurements/2026-08-30-warm-vs-cold-v04.json)),
  captioned retained state versus fresh-process cold start rather than an ordinary in-process
  follow-up.
- Full methodology, workload definitions, and historical series: [`BENCHMARKS.md`](BENCHMARKS.md).

## Non-claims

- **No SLA, stable/v1.0 support, or upgrade commitment:** The `0.x` series supports only the
  latest published release (`v0.13.1`) and its exact manifest and profiles.
- **No other GPUs or profiles:** Support does not extend outside the exact RTX 5090, RTX 4090, and
  RTX 3090 profiles bound by [`releases/v0.13.1/manifest.json`](../releases/v0.13.1/manifest.json).
- **Client platform limits:** macOS (`darwin-arm64`) is preview without managed client installation
  or appliance lifecycle; Linux (`linux-x64`) live evidence is under WSL2 only, not a separately
  qualified native Linux OS.
- **Native lanes are text and tools only:** Vision and DFlash2 are qualified only on the RTX 5090
  container lane; native Windows RTX 4090 and RTX 3090 lanes serve text, typed tools, and
  JSON-schema structured output under MTP3 (`--lm-head-draft`) and refuse image inputs with
  `vision_disabled`.
- **Not multi-GPU inference or concurrent native serving:** Only one UUID-bound native lane runs at
  a time on port `18082`. Both rebased native lanes are the first release of their `64d10fbf`
  lineage on the two-GPU host (`not_applicable`, zero rollback directions), and the historical RTX
  3090 `v0.6.2` rollback result does not transfer across the model and runtime rebase.
- **Checkpoints are best effort:** Neither globally loss-free shutdown, universal warm reuse,
  cross-GPU checkpoint migration, nor automatic container restart is claimed.
- **No "no re-prefill" or universal speed claims:** In-process prefix caching is conceded prior art
  ([`RELATED_WORK.md`](RELATED_WORK.md)), and two requests in flight on the RTX 5090 do not
  provide preemption or guaranteed faster single-session wall time.
- **Not independent external-user outcomes:** All qualification and acceptance receipts are
  owner-operated measurements on retained hardware.

## Where the history lives

- [`CHANGELOG.md`](../CHANGELOG.md) — chronological product changes across releases.
- [`RELEASES.md`](RELEASES.md) — per-version component identities, acceptance summaries, and
  release cut procedures.
- [`releases/v0.13.1/NINFER_RELEASE_NOTES.md`](../releases/v0.13.1/NINFER_RELEASE_NOTES.md) (and
  prior `releases/<tag>/NINFER_RELEASE_NOTES.md`) — immutable per-release notes and limitations.
- Immutable tagged guides (`https://github.com/alphastorm/omp-ninfer/blob/<tag>/docs/QUICKSTART.md`,
  such as [`v0.10.0`](https://github.com/alphastorm/omp-ninfer/blob/v0.10.0/docs/QUICKSTART.md) and
  [`v0.7.2`](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)) — complete
  setup instructions for operators remaining on a prior release.

Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.
