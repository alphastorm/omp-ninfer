# OMP NInfer — canonical facts

Updated: 2026-10-30 · Published release: v0.14.0 (2026-10-28) · stock Oh My Pi 18.12.6

Oh My Pi (coding-agent client) → OMP NInfer (qualified appliance and release layer) → NInfer
(inference engine) → Qwen3.8 27B (served model).

**Qualified on RTX 5090 · 4090 · 3090**, bound to the exact profiles in
[`releases/v0.14.0/manifest.json`](../releases/v0.14.0/manifest.json).
[Get started](QUICKSTART.md) ·
[Download v0.14.0](https://github.com/alphastorm/omp-ninfer/releases/tag/v0.14.0)

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

**Staged next: v0.15.0, not published.** The host-free draft pins stock Oh My Pi **18.14.0**
(`31147f9d`, tree `9a63b5bf`; Darwin `60884395`, Windows `620a5935`, Linux `e7dd2b60`) and
currently carries all three v0.14.0 runtime packages unchanged. RTX 4090 `v0.7.0-qwen38-4090-beta.3`
and RTX 5090 `v0.7.0-qwen38-5090-beta.3` remain carried in the final fast-track scope. RTX 3090
still binds MTP3 `v0.7.0-qwen38-3090-beta.3` here; its planned DFlash2 K7
`v0.8.0-qwen38-3090-beta.1` rebind awaits shipping-package gates. Fresh client/route acceptance,
changed-scope council, composition and immutable pins are separate. The root compatibility
authority stays v0.14.0 until the lead's lane pin. See the
[staged notes](../releases/v0.15.0/NINFER_RELEASE_NOTES.md),
[staged manifest](../releases/v0.15.0/manifest.json), and
[host-free client review](measurements/2026-10-30-omp-18140-client-upgrade-review.json).
The prepared guide is not an installation recommendation; the
[immutable published v0.14.0 guide](https://github.com/alphastorm/omp-ninfer/blob/v0.14.0/docs/QUICKSTART.md)
remains the install authority.

Published release **v0.14.0** (2026-10-28, GitHub `Latest`) binds unmodified upstream Oh My Pi
**18.12.6** (`45c35e40`, tree `8a90a1b4`), shared published model container version 3 `81f924d4`
(`qwen3_8_27b-v3.ninfer`, 20,437,521,664 bytes, revision `1cbd84e7`), and one frozen engine source
`2c6f423b` (`2c6f423bd817b6534158553e1b34ab4959c43165`) on upstream `Neroued/ninfer` master
`64d10fbf` across all three qualified GPU lanes: the RTX 5090 container runtime
(`v0.7.0-qwen38-5090-beta.3`, image `760fb6be` on base `d4377ed0`, server `55f0b95a`, strict-origin
profile `qwen38-5090-v0.13.0`, config `751d22dc`) and the native Windows RTX 4090
(`v0.7.0-qwen38-4090-beta.3`, profile `qwen38-4090-native-v0.7.0-beta.3`, public config `b5cfbf50`)
and RTX 3090 (`v0.7.0-qwen38-3090-beta.3`, profile `qwen38-3090-native-v0.7.0-beta.3`, public config
`d08d262b`, 350 W serving cap) packages, while carrying the stock OMP 18.12.6 client binaries
unchanged from v0.13.0 and v0.13.1. Release authority:
[`releases/v0.14.0/manifest.json`](../releases/v0.14.0/manifest.json) ·
[`releases/v0.14.0/NINFER_RELEASE_NOTES.md`](../releases/v0.14.0/NINFER_RELEASE_NOTES.md) ·
[`COMPATIBILITY.md`](COMPATIBILITY.md). The
[client upgrade review](measurements/2026-10-25-omp-18126-client-upgrade-review.json) records the
host-free checks across the Responses wire contract, image-aware snapcompact gate, and print-mode
slash dispatch.

| Component or lane | Form and transport | Release tag and source | Image or package | Serving profile | Context | Requests in flight | Speculative backend | Modalities |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
| Oh My Pi client | Unmodified upstream release binaries: macOS arm64 (preview), Windows x64, Linux x64 (WSL2 live evidence) | `v18.12.6`, source `45c35e40`, tree `8a90a1b4` | `omp-darwin-arm64` (`cfbb5e38`), `omp-windows-x64.exe` (`73d73c11`), `omp-linux-x64` (`85d9daf3`) in [`client-components.json`](../releases/v0.14.0/qualification/client-components.json) | Per-model `compat.statefulResponses: true`, fail-closed config | 131,072 | `2` on RTX 5090; `1` per native lane | Target lane | Coding agent, typed tools, branches, compaction |
| RTX 5090 | Windows 11 + Docker Desktop/WSL2 container on loopback `127.0.0.1:18089`; local Windows client or macOS client over manual SSH tunnel (preview) | `v0.7.0-qwen38-5090-beta.3`, source `2c6f423b` on `64d10fbf` | OCI image `760fb6be` (base `d4377ed0`), server `55f0b95a`, model `81f924d4` | `qwen38-5090-v0.13.0`, config `751d22dc`: BF16 KV (146,368 automatic KV tokens), shared Host budget 20,867.734375 MiB (21,881,405,440 B), 28,672 MiB host floor, 60,000 ms keep-warm, mandatory `--session-checkpoint-require-origin-auth`, `/checkpoints-v013` (schema 3); checked first build under founder-approved 5090-only reproducibility exception | 131,072 | 2 (plus 2 extra device-state slots, 180 s pending timeout) | DFlash2 draft window 7 | Vision, text, typed tools, JSON-schema output, preserved thinking |
| RTX 4090 native Windows 11 | Native Windows package on loopback `127.0.0.1:18082`, UUID-bound GPU on a two-GPU host | `v0.7.0-qwen38-4090-beta.3`, source `2c6f423b` on `64d10fbf` | Package `87038cfb` (954,798,284 B), server `5caa7780`, SPDX `e37f5620`, CycloneDX `02eb41f3`, model `81f924d4` | `qwen38-4090-native-v0.7.0-beta.3`, public config `b5cfbf50`: INT8 KV, `Group64` A8 off, shared Host budget 14,787.734375 MiB (15,506,063,360 B), 640 MiB admission headroom, 32,768 MiB host floor, 2,048-token prefill chunk, 60,000 ms keep-warm, mandatory `--session-checkpoint-require-origin-auth`, `session-checkpoints-v3` (schema 3) | 131,072 | 1 (plus 2 extra device-state slots, 30 s pending timeout) | MTP3 (3 draft tokens, `--lm-head-draft`) | Text, typed tools, JSON-schema output, preserved thinking (no vision) |
| RTX 3090 native Windows 11 | Native Windows package on loopback `127.0.0.1:18082`, UUID-bound GPU on the same two-GPU host | `v0.7.0-qwen38-3090-beta.3`, source `2c6f423b` on `64d10fbf` | Package `a7637f66` (971,496,678 B), server `fedce425`, SPDX `d3351740`, CycloneDX `ebbe9e1d`, model `81f924d4` | `qwen38-3090-native-v0.7.0-beta.3`, public config `d08d262b`: INT8 KV, `Group64` A8 off, shared Host budget 11,715.734375 MiB (12,284,837,888 B), 768 MiB admission headroom, 1,024-token prefill chunk, 350 W serving power cap (370 W restored on stop), keep-warm off, mandatory `--session-checkpoint-require-origin-auth`, `session-checkpoints-v3` (schema 3) | 131,072 | 1 (plus 4 extra device-state slots, 30 s pending timeout) | MTP3 (3 draft tokens, `--lm-head-draft`) | Text, typed tools, JSON-schema output, preserved thinking (no vision) |

- **Sequential native topology on one two-GPU host:** Both native Windows lanes install on the same
  two-GPU Windows 11 host (RTX 4090 at index 0, RTX 3090 at index 1), each bound to its own GPU
  UUID and PCI address. Only one native lane runs at a time on loopback port `18082`. This is not
  multi-GPU inference and not concurrent native serving.
- **First-of-lineage native rollback and RTX 3090 stop-before-upgrade:** Both native Windows lanes
  (`v0.7.0-qwen38-4090-beta.3` and `v0.7.0-qwen38-3090-beta.3`) record no supported rollback target
  (`not_applicable`, zero directions); neither the historical RTX 3090 `v0.6.2-beta.1` rollback
  result nor an inherited `beta.2` upgrade/rollback claim applies. Keep prior native release roots
  untouched for historical recovery. On RTX 3090, stop a running v0.13.1 lane before installing
  v0.14.0: a running v0.13.1 lane holds a 300 W GPU-owner lease that the v0.14.0 installer refuses
  against the new 350 W serving cap before replacement, leaving the old lane running unchanged; a
  stopped lane upgrades normally ([#94](https://github.com/alphastorm/omp-ninfer/issues/94)).
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
  own cache root (for example, `qwen38-4090-native-v0.7.0-beta.3-2c6f423bd817` or
  `qwen38-3090-native-v0.7.0-beta.3-2c6f423bd817`) with handle-anchored replacement, extended-length roots, and a current-parent
  publication fence (Windows `ntfs-write-through` is not POSIX `fsync` or a power-loss guarantee;
  physical disk exhaustion returns `capacity`, including HTTP 409 on DELETE without mutating
  surviving Responses objects). Keep prior checkpoint roots untouched; prior sessions resume by
  replaying authoritative OMP transcripts for a fresh prefill.
- **Dual native SBOMs and RTX 5090 reproducibility exception:** Each native outer asset set (10
  hashed entries plus `SHA256SUMS`, 11 files) ships both its SPDX file inventory
  (`<package-stem>.spdx.json`) and a separate canonical CycloneDX 1.5 dependency inventory
  (`<package-stem>.cdx.json`) covering resolved vcpkg dependencies, CUDA 13.3 DLLs, vendored
  sources, MSVC CRT, and DirectStorage redistributables, and passes 34/34 second-build EXE/DLL byte
  comparisons. The RTX 5090 container ships the checked first-build `55f0b95a` binary under an
  explicit founder-approved 5090-only reproducibility exception (same-source second builds differ in
  linked ELF executables under `nvcc` 13.1.115; deterministic module IDs remain a follow-up).
- **Fresh route and runtime acceptance:** Fresh v0.14.0 acceptance on frozen candidate `c81a8e7e`
  passed all five documented routes (31 blocks), all three stock 18.12.6 clients (typed tool turn,
  exact continuation, fail-closed request, plus macOS/Windows image input on RTX 5090), and both
  first-of-lineage beta.3 native public installs (7/7 blocks and 19/19 route-behavior checks on
  both RTX 4090 and RTX 3090; canonical roots freshly promoted from the documented blocks before
  idempotent `already_installed` public-URL checks), with independent host restoration (421.229 s
  corrected RTX 5090 hold after an initial same-Mac unit-suite tunnel-port collision failed closed
  and restored the incumbent, [#97](https://github.com/alphastorm/omp-ninfer/issues/97) /
  [#99](https://github.com/alphastorm/omp-ninfer/issues/99); 392.504 s RTX 4090 window; 393.945 s
  RTX 3090 window;
  [`documented-routes.json`](../releases/v0.14.0/acceptance/documented-routes.json),
  [`composed-external-installation.json`](../releases/v0.14.0/acceptance/composed-external-installation.json),
  [`2026-10-28-v0140-acceptance-restoration.json`](measurements/2026-10-28-v0140-acceptance-restoration.json)).
  All three lane runtime qualifications are fresh at `2c6f423b`, and both the common-engine fork
  (`CR-20261028T031911Z-2c6f423b`) and product-tooling (`CR-20261028T043650Z-c81a8e7e`) full
  councils closed without remediation in
  [`review/runtime-ledger.json`](../releases/v0.14.0/review/runtime-ledger.json), with deferred
  residuals tracked in [#88](https://github.com/alphastorm/omp-ninfer/issues/88)–[#90](https://github.com/alphastorm/omp-ninfer/issues/90)
  and [#94](https://github.com/alphastorm/omp-ninfer/issues/94)–[#100](https://github.com/alphastorm/omp-ninfer/issues/100).

## Models

v0.14.0 pins one shared registered NInfer conversion artifact (`qwen3_8_27b.ninfer`) from
[`neroued/Qwen3.8-27B-NInfer`](https://huggingface.co/neroued/Qwen3.8-27B-NInfer) across all three
lanes in [`releases/v0.14.0/manifest.json`](../releases/v0.14.0/manifest.json) (retaining the single
`components.model` binding introduced in v0.13.1):

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
  pinned in [`releases/v0.14.0/manifest.json`](../releases/v0.14.0/manifest.json).
- **Single trusted owner:** Designed for one trusted operator on owner-controlled hardware, not
  multi-tenant isolation. Full threat model: [`SECURITY.md`](SECURITY.md).

## Measured proof

Per-lane runtime qualification receipts bound in v0.14.0 (never transfer one lane's numbers or
capabilities to another):

| Lane | Long-context retrieval (130,048 tokens) | Decode measurement | Speculative acceptance | Receipt |
| --- | --- | --- | --- | --- |
| RTX 5090 (`v0.7.0-qwen38-5090-beta.3`, DFlash2 K=7, BF16 KV) | Exact in **57.00 s** cold (57.0 s, 2,281.5 tok/s wall; 56.416 s server) | **182.49 tok/s** server-side (**178.78 tok/s** wall) over 2,048 tokens | **0.244** DFlash2 acceptance, **2.71** tokens/round | [`rtx5090.json`](../releases/v0.14.0/qualification/rtx5090.json) (2026-10-28) |
| RTX 4090 native (`v0.7.0-qwen38-4090-beta.3`, MTP3, INT8 KV) | Exact in **81.78 s** (81.784 s) | **151.54 tok/s** C1 decode (4,541 prompt / 1,024 completion tokens); prefill **2,195.36 tok/s** | **87.59%** MTP3 acceptance | [`rtx4090.json`](../releases/v0.14.0/qualification/rtx4090.json) (2026-10-28) |
| RTX 3090 native (`v0.7.0-qwen38-3090-beta.3`, MTP3, INT8 KV, 350 W cap) | Exact in **187.88 s** (187.878 s) | **90.64 tok/s** C1 decode (4,541 prompt / 1,024 completion tokens); prefill **976.98 tok/s** | **92.96%** MTP3 acceptance | [`rtx3090.json`](../releases/v0.14.0/qualification/rtx3090.json) (2026-10-28) |

- **v0.14.0 native Windows schema 3 restart, protocol, and matched pre-cut gates:** On frozen source
  `2c6f423b` and published model `81f924d4`, both native lanes reused **1,647 cached tokens** after
  explicit save and **1,650 cached tokens** after graceful `stop-event` flush across process
  replacement (34.062 s on RTX 4090, 35.016 s on RTX 3090) with counters matching an independently
  measured cold-process baseline, and passed canonical schema 2 product protocol smokes at full and
  reduced (12,438.578125 MiB on RTX 4090; 9,366.578125 MiB on RTX 3090) shared Host budgets
  ([`rtx4090.json`](../releases/v0.14.0/qualification/rtx4090.json),
  [`rtx3090.json`](../releases/v0.14.0/qualification/rtx3090.json)). Separately, matched pre-cut
  A/B comparisons against shipped beta.2 controls passed 84/84 retained-output T1 role parity, 4/4
  exact 130,048-token retrieval arms (`85.70/85.62 → 81.48/81.55 s` prefill on RTX 4090;
  `197.51/198.70 → 188.16/187.80 s` on RTX 3090), and strict C1 median decode
  (`151.215 → 151.573 tok/s`, ×1.00237 on RTX 4090; `90.855 → 90.879 tok/s`, ×1.000265 on RTX 3090;
  [`native-integration.json`](../releases/v0.14.0/qualification/native-integration.json)).
- **v0.14.0 RTX 5090 schema 3 restart and T1 decode comparison:** On the shipped `55f0b95a`
  first-build binary (`2c6f423b`) and `81f924d4` model, the four-boot schema 3 restart gate reused
  **20,926 cached tokens** and produced **27 byte-identical continuation bytes** after an
  authenticated `fsync` save of **2,560,565,777 bytes**
  ([`durability.json`](../releases/v0.14.0/qualification/durability.json)), the 32 GB C2 durable
  pressure-overlap gate completed in **35.5524 s** with **1,074,790,400 bytes** headroom and
  **+2 MiB** graph growth
  ([`concurrency.json`](../releases/v0.14.0/qualification/concurrency.json)), and the 84-role ABBA
  fixed-KV T1 comparison matched all 84/84 request/output SHA-256 hashes (not retained-byte streams)
  with median decode **342.04 → 347.57 tok/s** (**×1.0162** / **101.62%** of the beta.2 control;
  [`decode-parity.json`](../releases/v0.14.0/qualification/decode-parity.json)). Earlier EXP-097
  measured **342.150 versus 338.448 tok/s** (**101.09%** of v0.12.2's `1302d639`,
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
  latest published release (`v0.14.0`) and its exact manifest and profiles.
- **No other GPUs or profiles:** Support does not extend outside the exact RTX 5090, RTX 4090, and
  RTX 3090 profiles bound by [`releases/v0.14.0/manifest.json`](../releases/v0.14.0/manifest.json).
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
- [`releases/v0.14.0/NINFER_RELEASE_NOTES.md`](../releases/v0.14.0/NINFER_RELEASE_NOTES.md) (and
  prior `releases/<tag>/NINFER_RELEASE_NOTES.md`) — immutable per-release notes and limitations.
- Immutable tagged guides (`https://github.com/alphastorm/omp-ninfer/blob/<tag>/docs/QUICKSTART.md`,
  such as [`v0.10.0`](https://github.com/alphastorm/omp-ninfer/blob/v0.10.0/docs/QUICKSTART.md) and
  [`v0.7.2`](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)) — complete
  setup instructions for operators remaining on a prior release.

Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.
