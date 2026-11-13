# OMP NInfer — canonical facts

Updated: 2026-11-13 · Published release: v0.19.0 (2026-11-13) · stock Oh My Pi 18.20.0

Oh My Pi (coding-agent client) → OMP NInfer (qualified appliance and release layer) → NInfer
(inference engine) → Qwen3.8 27B (served model).

**Qualified on RTX 5090 · 4090 · 3090**, bound to the exact profiles in
[`releases/v0.19.0/manifest.json`](../releases/v0.19.0/manifest.json).
[Get started](QUICKSTART.md) ·
[Download v0.19.0](https://github.com/alphastorm/omp-ninfer/releases/tag/v0.19.0)

## What it is

OMP NInfer is **durable local inference for coding agents**: the qualified local inference
appliance for [Oh My Pi](https://github.com/can1357/oh-my-pi) (OMP). It runs Qwen3.8 27B through
NInfer on one user-owned RTX 5090, RTX 4090, or RTX 3090 and preserves checkpointed OpenAI
Responses state across server restarts within each profile's restore boundary.

- **Oh My Pi** ([`can1357/oh-my-pi`](https://github.com/can1357/oh-my-pi)) owns the client:
  authoritative transcript, typed tools, branches, subagents, compaction, and transcript replay.
- **NInfer** ([`Neroued/ninfer`](https://github.com/Neroued/ninfer),
  [`alphastorm/ninfer`](https://github.com/alphastorm/ninfer)) owns single-GPU execution, retained
  Responses state, and local NVMe checkpoints.
- **OMP NInfer** (`alphastorm/omp-ninfer`) owns setup routes, profiles, manifests, qualification
  receipts, security boundaries, and support scope, with no forked OMP binary or extra gateway.

## Best fit

All of these should be materially true:

- The operator uses, or intends to use, Oh My Pi on Qwen3.8 27B.
- They own an RTX 5090, RTX 4090, or RTX 3090 matching the exact release profile.
- Sessions are long-lived and resuming across inference-server restarts matters.
- Privacy and owned hardware matter more than model catalog breadth or multi-user throughput.

## Not a fit

- A GUI-first local experience (use LM Studio).
- Broad model catalogs and quick experimentation (use Ollama or LM Studio).
- Unsupported hardware or maximum portability (use llama.cpp).
- Multi-user or high-concurrency serving (use vLLM).
- Generic OpenAI-compatible inference without the explicit durability contract.

See the [decision guide](DECISION_GUIDE.md) for the side-by-side comparison.

## Current release

Published release **v0.19.0** (2026-11-13) is GitHub `Latest` and supersedes `v0.18.0`
(2026-11-12). It pins unmodified upstream Oh My Pi **18.20.0**
([18.18.7→18.20.0 review](measurements/2026-11-13-omp-18200-client-upgrade-review.json)) and one
shared model container (`qwen3_8_27b-v3.ninfer`, SHA-256 `81f924d4`) across all three lanes.
Release authority: [`releases/v0.19.0/manifest.json`](../releases/v0.19.0/manifest.json) ·
[`releases/v0.19.0/NINFER_RELEASE_NOTES.md`](../releases/v0.19.0/NINFER_RELEASE_NOTES.md) ·
[`COMPATIBILITY.md`](COMPATIBILITY.md).

### Components

| Component | Release tag | Source | Artifacts | Profile and configuration |
| --- | --- | --- | --- | --- |
| Oh My Pi client | `v18.20.0` (release `443638329`) | [`can1357/oh-my-pi`](https://github.com/can1357/oh-my-pi) `c308970263ae13744ea15ab67302e3dac840e266`, tree `ba890953dd69eb4bf73bb7233bbe50ccfacd6912` | Unmodified upstream binaries for macOS arm64 (preview), Windows x64, and Linux x64 (WSL2 live evidence) | Per-model `compat.statefulResponses: true`, `tokenizer: qwen3` on `q38-ninfer`, fail-closed config |
| RTX 5090 runtime | `v0.7.0-qwen38-5090-beta.8`; source tag `v0.7.0-qwen38-5090-source.8`; image receipt `v0.7.0-qwen38-5090-runtime-beta.8` (`ba41de50`) | [`alphastorm/ninfer`](https://github.com/alphastorm/ninfer) `41f89b310b443481db5917a01a2b45e49f85e723` on `Neroued/ninfer` `64d10fbf`: fork `main` `8b3f498f` with [fork #122](https://github.com/alphastorm/ninfer/pull/122), plus a test-only fixture correction and `v0.8.0-beta.4` version metadata | OCI image `c3ec151b` on base `28857182`, archive `1cff1d73` (580,050,352 B), server `147da36b`, SPDX `afc94d21`, source archive `79ca0fba` (12,891,890 B) | `qwen38-5090-v0.13.0`, config `751d22dc` |
| RTX 4090 runtime | `v0.8.0-qwen38-4090-beta.3` | [`alphastorm/ninfer`](https://github.com/alphastorm/ninfer) `48c8ac46` on `Neroued/ninfer` `64d10fbf` | Package `ac41700a` (992,131,123 B), server `a5266ae6`, SPDX `4ad1f5e8`, CycloneDX `60a1d35d` | `qwen38-4090-native-v0.8.0-beta.3`, build profile `native-v0.8.0-beta.3-rtx4090`, public config `b71a2cff` |
| RTX 3090 runtime | `v0.8.0-qwen38-3090-beta.4` | [`alphastorm/ninfer`](https://github.com/alphastorm/ninfer) `15c3e3959c0a6167f799e9383482ec4e03db9cad` on `Neroued/ninfer` `64d10fbf`: a descendant of `41f89b31` that adds only the native qualification managed-`C1` power-check fix and a corrected Windows store-quota note ([fork #126](https://github.com/alphastorm/ninfer/pull/126)); serve source identical to `41f89b31` | Package `62b9effd` (1,011,088,657 B), server `2c25588e`, SPDX `2c01ec37`, CycloneDX `dbce8372` | `qwen38-3090-native-v0.8.0-beta.4`, build profile `native-v0.8.0-beta.4-tc-rtx3090`, public config `6e4c6fc2` |
| Model | Container version 3 (`qwen3_8_27b-v3.ninfer`) | [`neroued/Qwen3.8-27B-NInfer`](https://huggingface.co/neroued/Qwen3.8-27B-NInfer) revision `1cbd84e7` | `81f924d4` (20,437,521,664 B) | Single `components.model` shared across all three lanes |

Client assets pinned in
[`client-components.json`](../releases/v0.19.0/qualification/client-components.json):

| Asset name | SHA-256 prefix | Byte count |
| --- | --- | ---: |
| `omp-darwin-arm64` | `2b1309b0` | 223,369,360 |
| `omp-windows-x64.exe` | `1b6c7bda` | 251,502,592 |
| `omp-linux-x64` | `c8694be8` | 287,484,080 |

### Lanes and limits

| Property | RTX 5090 container | RTX 4090 native | RTX 3090 native |
| --- | --- | --- | --- |
| Runs as | Windows 11 + Docker Desktop/WSL2 container | Native Windows 11 package, UUID-bound GPU (index 0) on a two-GPU host | Native Windows 11 package, UUID-bound GPU (index 1) on the same two-GPU host |
| Endpoint | Loopback `127.0.0.1:18089` | Loopback `127.0.0.1:18082` (one native lane at a time) | Loopback `127.0.0.1:18082` (one native lane at a time) |
| Client platforms | Windows (local), macOS over a manual SSH tunnel (preview), Linux under WSL2 | Windows (local) | Windows (local) |
| Oh My Pi provider and model id | `ninfer-beta` / `ninfer-main`, model `q38-ninfer` | `ninfer-native-4090` (fleet `ninfer-heavy`), model `qwen3.8-27b` | `ninfer-native-3090`, model `q38-ninfer` |
| Requests in flight | 2 (`--max-concurrency 2`) | 1 | 2 over one shared pool |
| Pending timeout | 180 s (`--pending-timeout-ms 180000`) | 30 s | 180 s |
| Extra device-state slots | 2 (`--device-state-slots 2`) | 2 | 2 |
| KV format and pool | BF16 KV; 131,072-token context (146,368 automatic KV tokens) | INT8 KV; 131,072-token context | INT8 KV; one shared 131,072-token pool |
| [Shared Host budget](#glossary) | 20,867.734375 MiB (21,881,405,440 B) | 15,747.734375 MiB (16,512,696,320 B) | 20,867.734375 MiB (21,881,405,440 B) |
| Admission headroom | — | 640 MiB (`--admission-headroom-mib`) | 768 MiB (`--admission-headroom-mib`) |
| Runtime-host memory floor | 28,672 MiB | 32,768 MiB | — |
| Prefill chunk | 1,024 tokens | 1,024 tokens | 1,024 tokens |
| Keep-warm | 60,000 ms | 60,000 ms | Off |
| Power | — | 450 W owner baseline | 350 W serving cap (370 W restored on stop) |
| Speculative decoding | DFlash2, draft window 7 (`K=7`, `--lm-head-draft`) | DFlash2, draft window 7 (`K=7`, `artifact-default` proposal, `Q4_G64_FP16` draft MLP, host-mapped token embedding; small-T tensor-core verify, `Group64` A8, and FP32 head logits off) | DFlash2, draft window 7 (`K=7`, `artifact-default` proposal, `Q4_G64_FP16` draft MLP, host-mapped token embedding; `sm_86` small-T tensor-core verify at `T=8/16`; `Group64` A8 and FP32 head logits off) |
| Modalities | Vision, text, typed tools, JSON-schema output, preserved thinking | Text, typed tools, JSON-schema output, preserved thinking (no vision) | Text, typed tools, JSON-schema output, preserved thinking (no vision) |
| Checkpoint store | Host `checkpoints-v019` mounted at `/checkpoints-v013` (schema 3, `--session-checkpoint-require-origin-auth`) | `cache/<release-instance-id>/session-checkpoints-v3` (`qwen38-4090-native-v0.8.0-beta.3-48c8ac464432`, schema 3, `--session-checkpoint-require-origin-auth`) | `cache/<release-instance-id>/session-checkpoints-v3` (`qwen38-3090-native-v0.8.0-beta.4-15c3e3959c0a`, schema 3, `--session-checkpoint-require-origin-auth`) |
| Checkpoint store quota | 24,576 MiB, with 256 MiB staging | 24,576 MiB, with 256 MiB staging | 24,576 MiB, with 256 MiB staging |
| Memory-pressure save bound | 6 retries or 10 s on retryable refusals ([ninfer#122](https://github.com/alphastorm/ninfer/pull/122)) | Not included in `v0.8.0-qwen38-4090-beta.3` | 6 retries or 10 s on retryable refusals ([ninfer#122](https://github.com/alphastorm/ninfer/pull/122)) |

### Differences between lanes

- **Vision is RTX 5090 only.** The native lanes serve text and tools and refuse image inputs with
  `vision_disabled`.
- **The RTX 4090 lane serves one request at a time.** The RTX 5090 and RTX 3090 lanes serve up to
  two requests in flight.
- **The RTX 3090 build enables the small-T tensor-core verify path** (`sm_86`, `T=8/16`) and serves
  under a 350 W cap; a managed stop restores the 370 W limit.
- **The RTX 4090 package does not include the bounded pressure-save retries** that the RTX 5090 and
  RTX 3090 runtimes have. `v0.8.0-qwen38-4090-beta.3` is the package `v0.18.0` shipped.

### Operating rules

- **Sequential native topology:** Both native lanes install on one two-GPU Windows 11 host (RTX
  4090 index 0, RTX 3090 index 1), each bound to its GPU UUID and PCI address. Only one runs at a
  time on `127.0.0.1:18082`; this is neither multi-GPU inference nor simultaneous serving.
- **Native upgrade and rollback:** On RTX 3090, `Install-Release.ps1` and `Control-Release.ps1`
  stop a running `v0.8.0-qwen38-3090-beta.3` install across power-cap transitions and keep
  `previous_release` for `Control-Release.ps1 -Action Rollback`; `Stop-ManagedRelease` restores the
  GPU lease on a thrown `Stop` error ([PR #107](https://github.com/alphastorm/ninfer/pull/107)).
  On RTX 4090, an existing `v0.18.0` install already matches this release and needs no runtime
  reinstall.
- **Memory-pressure checkpoint save refusals:** Two requests run together on RTX 5090 and RTX 3090
  only while both prompts and output reservations fit in the shared pool; excess requests wait
  for the pending timeout. A memory-pressure save is a checkpoint save triggered to free resident
  state under memory pressure. On RTX 5090 (`41f89b31`) and RTX 3090 (`15c3e395`),
  [fork #122](https://github.com/alphastorm/ninfer/pull/122) bounds an unsettled pressure save
  refused for `capacity` (a full volume or filesystem quota: `ENOSPC`, `EDQUOT`, or Windows errors
  `112`, `39`, `1295`), `io`, or `stale_tag` to six retries or 10 seconds. It then emits one
  `pressure` / `abandoned` checkpoint record and releases the continuation instead of keeping
  admission latched behind the outstanding save. A full-volume refusal whose prepared export
  retires re-arms on progress and can finish its six retries in about 3 s.
- **Store-quota refusals:** A refusal from the checkpoint store's own quota
  (`--session-checkpoint-quota-mib`, reason `quota`) is terminal on the first refusal. It emits
  only `save` / `refused` / `quota`, no `pressure` / `abandoned` record, and does not increment
  the status endpoint's `abandoned_total` counter.
- **Deferred pressure-save residuals:** Two narrow coordinator cases are deferred to
  [fork #123](https://github.com/alphastorm/ninfer/issues/123): an already-queued retry read as a
  refused deferral, and four or more continuously ready eviction-pressure saves starving a
  persistent deferral past 10 s.
- **RTX 4090 admission stack:** RTX 4090 (`48c8ac46`) keeps the `v0.18.0` admission stack without
  [fork #122](https://github.com/alphastorm/ninfer/pull/122): bounded resume and fresh admission
  ([#434](https://github.com/Neroued/ninfer/issues/434)), Device-staged durable `StateImage` saves
  ([PR #109](https://github.com/alphastorm/ninfer/pull/109)), operation-free prepare holding
  ([PR #111](https://github.com/alphastorm/ninfer/pull/111)), bounded `K = 4` fresh-admission
  priority ([PR #108](https://github.com/alphastorm/ninfer/pull/108)), and serving robustness.
- **Checkpoint stores per release:** All lanes use schema 3 checkpoints (fingerprint schema 2,
  status schema 2, request-log schema 30) with `--session-checkpoint-require-origin-auth` and at
  least a 32-byte key (64 characters as generated). RTX 5090 mounts `checkpoints-v019` at
  `/checkpoints-v013` with non-blocking export, leaving `checkpoints-v018` (`v0.18.0`),
  `checkpoints-v017` (`v0.17.0`), `checkpoints-v013` (`v0.16.2`), and `checkpoints` untouched for
  rollback. Native lanes use `cache/<release-instance-id>/session-checkpoints-v3` with
  handle-anchored replacement, extended-length roots, and a current-parent publication fence
  (`ntfs-write-through` is not POSIX `fsync` or a power-loss guarantee). Keep prior checkpoint
  roots untouched; earlier sessions resume by replaying Oh My Pi's transcript for a fresh prefill.
- **SBOMs and build identity:** Native outer asset sets (10 hashed entries plus `SHA256SUMS`, 11
  files) ship SPDX 2.3 (`<package-stem>.spdx.json`) and CycloneDX 1.5 (`<package-stem>.cdx.json`)
  inventories verified in
  [`native-publication.json`](../releases/v0.19.0/qualification/native-publication.json)
  (`ac4e5237`). RTX 5090 binds source `41f89b31` and server `147da36b` in
  [`runtime-build-identity.json`](../releases/v0.19.0/qualification/runtime-build-identity.json)
  (`6f9fc509`) and
  [`runtime-artifacts.json`](../releases/v0.19.0/qualification/runtime-artifacts.json) (`70b3bcf6`);
  recipe reproducibility is tracked in [fork #120](https://github.com/alphastorm/ninfer/issues/120).

### Evidence

| Evidence | Result | Receipt |
| --- | --- | --- |
| RTX 5090 release-candidate batch | `12/12` exact-source phases passed in `741.187 s` on `41f89b31` | [`runtime-rc.json`](../releases/v0.19.0/qualification/runtime-rc.json) (`3007e800`) |
| RTX 5090 lane receipt | **181.71 tok/s** server / **180.20 tok/s** wall decode; **56.67 s** (`56.668 s` wall, **56.55 s** / `56.548 s` server, **2,294.9 tok/s** wall) cold 130,048-token retrieval; `agent_protocol` passed across Docker restart; `30,398 MiB` idle/final VRAM; `0` retries | [`rtx5090.json`](../releases/v0.19.0/qualification/rtx5090.json) (`4873087e`) |
| RTX 4090 lane receipt | Byte-identical `v0.18.0` qualification on `v0.8.0-qwen38-4090-beta.3`: **253.71 tok/s** `C1` decode, **2,129.62 tok/s** prefill, **83.45 s** (`83.451 s`) retrieval | [`rtx4090.json`](../releases/v0.19.0/qualification/rtx4090.json) (`165999b9`), [`receipt-audit.json`](../releases/v0.19.0/qualification/receipt-audit.json) (`3162e66e`) |
| RTX 3090 lane receipt | 15-phase hardware chain passed on `15c3e395`: **227.19 tok/s** `C1` decode, **978.19 tok/s** prefill, **188.45 s** (`188.453 s`) retrieval, **1,647** explicit-save and **1,650** graceful-stop cached tokens across **46.95 s** restart, `350.0 W` enforced cap across `56` samples (`350.68 W` peak <= `355.0 W` envelope, [fork #126](https://github.com/alphastorm/ninfer/pull/126)) | [`rtx3090.json`](../releases/v0.19.0/qualification/rtx3090.json) (`9bddbdfd`) |
| Agent parity | RTX 3090 passed `83/83` raw positions | [`rtx3090-agent-parity.json`](../releases/v0.19.0/qualification/rtx3090-agent-parity.json) (`a0e0806f`) |
| Fit proof | RTX 3090 shipping-package memory fit passed | [`rtx3090-windows-native.fit.json`](../releases/v0.19.0/qualification/rtx3090-windows-native.fit.json) (`af95eadb`) |
| Upgrade, rollback, and repair rehearsals | `3/3` RTX 3090 scenarios passed from `v0.8.0-qwen38-3090-beta.3` `tc`: running upgrade, forced-start rollback, interrupted-install repair | [`rtx3090-upgrade.json`](../releases/v0.19.0/qualification/rtx3090-upgrade.json) (`40023601`) |
| Same-profile identity-first admission | RTX 3090 vs `v0.8.0-qwen38-3090-beta.3` `tc` ([#171](https://github.com/alphastorm/omp-ninfer/pull/171), [gate rule](PERFORMANCE.md#decision-authorized-identity-first-native-admission)): `84/84` `ABBA` and `80/80` sealed determinism byte-identical (1,120-prompt quality screen skipped); weighted speed **0.9997**, min **0.9975** | [`native-identity-decision.json`](../releases/v0.19.0/qualification/native-identity-decision.json) (`856ac8d2`), [`rtx3090-windows-native.identity-proof.json`](../releases/v0.19.0/qualification/rtx3090-windows-native.identity-proof.json) (`a0e9086b`), [`rtx3090-speed.json`](../releases/v0.19.0/qualification/rtx3090-speed.json) (`a9df66a1`), [`native-speed-decision.json`](../releases/v0.19.0/qualification/native-speed-decision.json) (`bba32162`) |
| Documented-route acceptance | All five documented routes (`31/31` blocks) and all three stock `18.20.0` clients passed on 2026-11-13 at `6b22f219c7298db4b8fa5c2bc7bb33eb7a37799f`; RTX 5090 hold **402.128 s**, RTX 4090 window **517.0 s**, RTX 3090 window **1,339.4 s**, plus independent restorations | [`documented-routes.json`](../releases/v0.19.0/acceptance/documented-routes.json) (`20dd5230`), [`composed-external-installation.json`](../releases/v0.19.0/acceptance/composed-external-installation.json) (`163a8027`), [restoration](measurements/2026-11-13-v0190-n41f89b31-acceptance-restoration.json) (`83d0c17f`) |
| Public installs | First-attempt RTX 4090 and RTX 3090 public installs and checkpoint retirements passed; RTX 3090 proof `9759ea5f` recorded `0` HTTP `503` responses, `0` queue timeouts, `0` checkpoint write errors, `0` refused `Stop` sessions, `5/5` HTTP `200` on four-way `C2` fanout, and `2/2` committed compactions | [`rtx4090-public-install.json`](../releases/v0.19.0/acceptance/rtx4090-public-install.json) (`2243cdff`), [`rtx3090-public-install.json`](../releases/v0.19.0/acceptance/rtx3090-public-install.json) (`d5d61388`) |
| Reviews | Runtime review `CR-20261113T063918Z-41f89b31` (`closed-without-remediation`, residuals in [fork #123](https://github.com/alphastorm/ninfer/issues/123)); native delta review on `15c3e395` (`closed-without-remediation`, diagnostic residuals in [fork #127](https://github.com/alphastorm/ninfer/issues/127)); product review `CR-20261113T192727Z-6b22f219-product` (`closed-by-disposition`, follow-ups in [#176](https://github.com/alphastorm/omp-ninfer/issues/176)) | [`review/runtime-ledger.json`](../releases/v0.19.0/review/runtime-ledger.json) (`2b43fc7a`) |

- Acceptance tooling ([#163](https://github.com/alphastorm/omp-ninfer/pull/163) to
  [#170](https://github.com/alphastorm/omp-ninfer/pull/170),
  [#174](https://github.com/alphastorm/omp-ninfer/pull/174)) enforces `60 GiB` window and `10 GiB`
  public-install free-space floors, and fails acceptance windows on HTTP `503`, checkpoint write
  errors, or an incomplete or refused `Stop`.
- Passed window checkpoint stores are retired with audited `retirement.json` records; recovery
  journals write atomically, restoration continues across evidence-write errors, `--checkpoint-dir`
  paths are revalidated, and RTX 5090 restoration is reported only when it ran.

### Publication record

The `publication` block of [`releases/v0.19.0/manifest.json`](../releases/v0.19.0/manifest.json)
and `publication_authorized` in
[`releases/v0.19.0/qualification.json`](../releases/v0.19.0/qualification.json) record the sealed
pre-publication state (`authorized: false` at commit `6b22f219`). That state captures passed
acceptance across all five routes, three stock clients, and both native campaigns and public
installs, and both JSON files stay immutable once sealed. The publication record is this section,
[`releases/v0.19.0/NINFER_RELEASE_NOTES.md`](../releases/v0.19.0/NINFER_RELEASE_NOTES.md),
[`docs/RELEASES.md`](RELEASES.md), and the
[GitHub release](https://github.com/alphastorm/omp-ninfer/releases/tag/v0.19.0).

## Models

v0.19.0 pins one shared NInfer conversion artifact from
[`neroued/Qwen3.8-27B-NInfer`](https://huggingface.co/neroued/Qwen3.8-27B-NInfer) under
`components.model` in [`releases/v0.19.0/manifest.json`](../releases/v0.19.0/manifest.json). The
repository publishes it as `qwen3_8_27b.ninfer`:

| Lane scope | Hugging Face revision | Bytes | SHA-256 | Notes |
| --- | --- | ---: | --- | --- |
| All qualified lanes (`components.model`: RTX 5090 container, native RTX 4090, native RTX 3090) | `1cbd84e7221e51186bd7f093a149912d2489625b` | 20,437,521,664 | `81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da` | Published model container version 3, stored as `qwen3_8_27b-v3.ninfer` on the host. Public model ID `q38-ninfer` on RTX 5090 and native RTX 3090, `qwen3.8-27b` on native RTX 4090 |

All routes download container version 3 (`81f924d4`) into `qwen3_8_27b-v3.ninfer`. Keep the
18,210,531,328-byte version 2 artifact `eec39564` (revision `18dfc887`, used on native releases
through `v0.13.0`) untouched on disk for historical recovery. On RTX 5090, all 1,184 tensor
payloads and all six frontend resources matched the `v0.12.2` model (`0634abb0`) upgraded locally,
while whole-container bytes differ.

## What the route provides

- **Protocols and endpoints:** OpenAI Responses (`/v1/responses`, the primary stateful surface),
  OpenAI Chat Completions (`/v1/chat/completions`), Anthropic Messages (`/v1/messages` and
  `/v1/messages/count_tokens`), authenticated runtime identity (`/v1/ninfer/status`), and session
  checkpoint save, status and delete (`/v1/ninfer/checkpoints`).
- **Explicit continuation and lineage:** Continuation uses `previous_response_id`, with session
  identity derived from `prompt_cache_key` under bearer authentication. The key is never stored
  raw, and a request that mixes it with legacy `ninfer_session` or `X-NInfer-Session` is rejected.
  Sibling forks, parent deletion without descendant loss, and cross-session isolation are
  qualified on all three lanes. Within one API-key principal, `prompt_cache_key` names a session
  capability: use unique high-entropy keys and do not share that principal among mutually
  untrusted clients.
- **Tools, vision, structured output, and preserved thinking:** Typed tools, content-part array tool
  outputs, JSON-schema output (`text.format` on Responses, `response_format` with `json_schema` on
  Chat), 128-character tool names, and preserved thinking (`reasoning_text` deltas with
  `summary: []`) are qualified on all lanes. Vision is RTX 5090 only, including image tool results
  and `snapcompact` archives (the Oh My Pi compaction method that stores earlier turns as images);
  native lanes refuse images with `vision_disabled`.
- **Stock Oh My Pi runtime behavior:** Stock Oh My Pi 18.20.0 has no `omp appliance` commands. On
  Windows it removes the emulated-bash guidance from the rendered `bash` tool description and
  advertises runtime builtins ahead of `PATH`. It also updates the system, `read`, `task`, and
  `edit` descriptions and carries the OpenAI Responses serializer and `qwen3` tokenizer.
  Length-stopped compaction summaries fail visibly without committing partial context (a completed
  main summary survives a truncated display-only `<=512`-token summary), manual compaction waits
  for persistence replacement before queued background results start a turn, and shared Responses
  replay copies strip only `internal_chat_message_metadata_passthrough`.
- **Oh My Pi client contract:**
  - `compat.statefulResponses: true`, `compat.includeEncryptedReasoning: false`, and
    `compat.supportsReasoningSummary: false` per model in `models.fragment.yml` (upstream
    [#13686](https://github.com/can1357/oh-my-pi/pull/13686)); `compat.thinkingLoopGuard` is
    retired while `model.loopGuard` keeps its 1,024-character floor on short newline cycles.
  - `tokenizer: qwen3` pinned on `q38-ninfer` (`qwen3.8-27b` infers `qwen3`), with explicit
    `[low, medium, xhigh]` effort lists (`high`→`medium`, `off`→`low`).
  - `PI_OPENAI_STATEFUL` and `PI_NO_THINKING_LOOP_GUARD` absent from the environment.
  - Default `auto` image detail on custom Responses hosts (upstream
    [#13687](https://github.com/can1357/oh-my-pi/pull/13687)).
  - Unavailable saved models fail closed (upstream
    [#13689](https://github.com/can1357/oh-my-pi/pull/13689)).
  - [`examples/manual-tunnel/fail-closed.yml`](../examples/manual-tunnel/fail-closed.yml): disables
    retries, model fallback (including pre-prompt missing-key fallback, through explicit
    `retry.modelFallback: false`), automatic updates (`update.auto: false`,
    `startup.checkUpdate: false`), and `startup.setupWizard: false`.
  - Async compaction stays at the OMP default (`19,660` reserve, strict `>111,412` trigger,
    `13,107` unset-reserve summary cap).
  - `providers.maxInFlightRequests` per provider ID: `ninfer-beta: 2`, `ninfer-main: 2`,
    `ninfer-native-4090: 1`, `ninfer-native-3090: 2`, `ninfer-heavy: 1`.

## Durability

- **Transcript is the source of truth:** Oh My Pi commits each turn locally before advancing the
  provider baseline; GPU and checkpointed state is an acceleration layer, never the sole copy.
- **What survives a server restart:** SHA-256-manifested NVMe checkpoints publish atomically and
  restore on the first matching request after restart on all three lanes. Sessions above 32,768
  frontier tokens checkpoint automatically; shorter sessions are saved by an explicit save
  (`POST /v1/ninfer/checkpoints`) or when a graceful stop flushes eligible unpublished sessions.
- **Best-effort saves and pool bounds:** Checkpointing under live traffic is best effort. Transient
  save refusals retry when the engine quiesces, admission saves a checkpoint-tagged session's
  newest turn before evicting it, and a crash or expired graceful wait can leave unpublished work
  unsaved. Restore loads state within each lane's shared Host budget (see
  [Lanes and limits](#lanes-and-limits) and [Operating rules](#operating-rules)); checkpoint
  exports that the configuration could not admit back are refused (`HTTP 409`).
- **Exact-identity restore:** A checkpoint restores only when the runtime binary hash, patch-stack
  SHA, model artifact, profile, and session credentials match; foreign-lane, older-build, or legacy
  `ninfer_session` checkpoints are refused.
- **Replay fallback and warm-reuse limits:** On missing, incompatible, or capacity-declined state,
  NInfer returns `previous_response_not_found` and Oh My Pi replays the transcript for one cold
  prefill (starting a new OMP process also costs one root prefill because the first resumed request
  omits prior reasoning tokens). Universal warm reuse is not promised (the RTX 5090 multisession
  control observed root fallback on 2 of 8 continuations or forks without server errors).

## Checkpoint transport and NAS replication

[`scripts/checkpoint_sync.py`](../scripts/checkpoint_sync.py) exports published checkpoint
generations, verifies file sizes, SHA-256 hashes, and `manifest.mac`, and imports verified replicas
into a local checkpoint root (`python3 scripts/checkpoint_sync.py --help`).

- **Replicas, never live roots:** O_DIRECT and DirectStorage require a local filesystem, so NAS and
  network shares hold replicas only; publish before export and stop the destination before import.
- **Same-lane restore:** Imported replicas require the identical runtime binary, model, profile, and
  bearer key (`--session-checkpoint-require-origin-auth`; never pass `--allow-unauthenticated`
  across trust boundaries). Transport is explicit export and import, not cross-GPU migration,
  cross-version conversion, or failover.
- **Historical transport receipts:** Verified on 2026-09-05 profiles
  ([RTX 5090](measurements/2026-09-05-sync-probe-rtx5090.json),
  [RTX 4090](measurements/2026-09-05-sync-probe-rtx4090.json),
  [RTX 3090](measurements/2026-09-05-sync-probe-rtx3090.json)), plus
  [cross-site transfer](measurements/2026-09-06-replica-transfer-paths.json) and
  [NAS replication](measurements/2026-09-07-nas-replication-sf-lanes.json).

## Privacy and security boundary

- **Loopback-only listeners:** Runtimes bind `127.0.0.1:18089` (RTX 5090 container) or
  `127.0.0.1:18082` (native lanes); macOS clients use an authenticated SSH local port forward.
- **Bearer authentication and protected state:** Every request requires a user-only bearer key;
  anonymous requests fail with `HTTP 401`. Native Windows state roots enforce Administrator-only
  DACLs verified by low-privilege read and write denial checks.
- **Fail-closed client and pinned bytes:** Oh My Pi disables retries and model fallback, so an
  unreachable or mismatched local runtime fails closed instead of falling back to cloud APIs.
  Every client binary, image digest, native package, model artifact, and configuration is SHA-256
  pinned in [`releases/v0.19.0/manifest.json`](../releases/v0.19.0/manifest.json).
- **Single trusted owner:** Built for one trusted operator on owned hardware, not multi-tenant
  isolation. Threat model: [`SECURITY.md`](SECURITY.md).

## Measured proof

Per-lane runtime qualification results for v0.19.0 apply only to the measured lane; never transfer
one lane's numbers or capabilities to another.

| Lane | Long-context retrieval (130,048 tokens) | Decode measurement | Speculative acceptance | Receipt |
| --- | --- | --- | --- | --- |
| RTX 5090 (`v0.7.0-qwen38-5090-beta.8`, DFlash2 `K=7`, BF16 KV, `C2`) | Exact in **56.67 s** cold (`56.668 s`, **2,294.9 tok/s** wall; **56.55 s** / `56.548 s` server) | **181.71 tok/s** server-side (**180.20 tok/s** wall) over 2,048 tokens | **0.244** DFlash2 acceptance, **2.71** tokens/round | [`rtx5090.json`](../releases/v0.19.0/qualification/rtx5090.json) (2026-11-13) |
| RTX 4090 native (`v0.8.0-qwen38-4090-beta.3`, DFlash2 `K=7`, INT8 KV, `C1`) | Exact in **83.45 s** (`83.451 s`) | **253.71 tok/s** `C1` decode (4,541 prompt / 1,024 completion tokens); prefill **2,129.62 tok/s** | **83.88%** DFlash2 acceptance | [`rtx4090.json`](../releases/v0.19.0/qualification/rtx4090.json) (2026-11-12) |
| RTX 3090 native (`v0.8.0-qwen38-3090-beta.4` `tc`, DFlash2 `K=7`, small-T tensor-core verify, INT8 KV, `C2` shared pool, 350 W cap) | Exact in **188.45 s** (`188.453 s`) | **227.19 tok/s** `C1` decode (4,541 prompt / 1,024 completion tokens); prefill **978.19 tok/s** | **84.04%** DFlash2 acceptance | [`rtx3090.json`](../releases/v0.19.0/qualification/rtx3090.json) (2026-11-13) |

Workload definitions and caption rules are in
[how to read these numbers](BENCHMARKS.md#how-to-read-these-numbers); measurements from earlier
releases are in [historical measurements](BENCHMARKS.md#historical-measurements) and
[release records](RELEASES.md#release-records).

## Non-claims

- **No SLA, stable or v1.0 support, or upgrade commitment:** The `0.x` series supports only the
  latest published release and its manifest and profiles in [Current release](#current-release).
- **No other GPUs or profiles:** Support covers only the exact RTX 5090, RTX 4090, and RTX 3090
  profiles bound by the current release manifest.
- **Client platform limits:** macOS (`darwin-arm64`) is preview without managed install or
  lifecycle; Linux (`linux-x64`) live evidence is WSL2 only, not native Linux OS qualification.
- **Native lanes are text and tools only:** Vision is RTX 5090 only; native lanes serve text,
  tools, and JSON-schema output under DFlash2 (`K=7`) and refuse images with `vision_disabled`.
- **Not multi-GPU inference or simultaneous native serving:** One UUID-bound native lane runs at a
  time on port `18082`; scratch 15-phase qualification reports `rollback: not_applicable` (zero
  directions), whereas upgrades keep `previous_release` for `Control-Release.ps1 -Action Rollback`.
- **Checkpoints are best effort:** Neither loss-free shutdown, universal warm reuse, cross-GPU
  migration, nor automatic container restart is claimed.
- **No "no re-prefill" or universal speed claims:** In-process prefix caching is prior art
  ([`RELATED_WORK.md`](RELATED_WORK.md)). Two requests in flight give neither preemption nor a
  guaranteed faster single-session wall time: on RTX 3090, overlapping per-request decode is
  `0.70–0.73×` of `C1` while aggregate decode is `1.385×`.
- **Not independent external-user outcomes:** Qualification and acceptance receipts are
  owner-operated measurements on retained hardware.

## Glossary

- **`lane`:** One qualified combination of GPU, runtime package or container, and serving profile
  in the release manifest. Numbers, checkpoints, and capabilities do not transfer across lanes.
- **`DFlash2`:** Speculative decoding backend (`--spec dflash2`). The five-layer block drafter
  bundled in the version 3 model artifact proposes seven candidate tokens (`K=7`) in one
  masked-block pass for the target model to verify. RTX 5090 uses `--lm-head-draft`; native lanes
  use the `artifact-default` proposal, `Q4_G64_FP16` draft MLP `gate`/`up` weights, and host-mapped
  `token_embedding`.
- **`MTP3`:** Retired multi-token prediction backend (`--spec mtp --draft-tokens 3` with
  `--lm-head-draft`, or `backend: "mtp"`, `draft_tokens: 3` in native server configurations). It
  drafts three candidate tokens per round, so the target verifies four tokens in one pass. Used on
  RTX 5090 before `v0.10.0` and on the native lanes through `v0.15.0`; superseded by `DFlash2 K=7`
  in `v0.16.0`.
- **`Group64 A8` (`A8 off`):** Native prefill 8-bit group-64 integer-activation route
  (`-DNINFER_NATIVE_PREFILL_GROUP64_A8`, `group64_a8`). Native packages compile it off (`A8 off`,
  guarded by `-a8` in `NINFER_BUILD_PROFILE`): the RTX 4090 failed its preregistered 200-pair
  new-leak behavioral screen (five one-way changes), and off was chosen conservatively for both
  cards.
- **`tc` (`small-T tensor-core verify`):** Native build-profile component (`NINFER_BUILD_PROFILE`
  containing hyphen-delimited `tc`, such as `native-v0.8.0-beta.4-tc-rtx3090`). It enables the
  `sm_86`/`sm_89` tensor-core verification kernel for `T=8` and `T=16` verify passes across `Q5`
  linear-add, `n7168` split, `SwiGLU`, and `GDN` record projections
  ([`alphastorm/ninfer#104`](https://github.com/alphastorm/ninfer/pull/104)). Enabled on the RTX
  3090 lane; off on the RTX 4090 lane (`native-v0.8.0-beta.3-rtx4090`).
- **`ABBA`:** Paired A/B/B/A run order used when a candidate build is compared against the shipped
  control.
- **`C1`:** Single-request serving (`max_concurrency` set to `1`) on native RTX 4090, versus
  two-request (`C2`) serving on RTX 5090 and native RTX 3090. The `benchmark_c1` gate generates
  1,024 completion tokens after 4,541 computed prompt tokens with no prefix-cache hit
  (`seed 57004`; temperature `0` in strict paired `ABBA` comparisons), recording prefill
  throughput, decode throughput, speculative acceptance, peak VRAM, and peak board power.
- **`T1`:** Pre-cut output-parity and serial decode gate over 84 frozen role-corpus cases (`336`
  role requests across four `ABBA` arms, a fixed 131,072-token KV pool, persistence disabled),
  comparing a candidate build against the shipped control. Native `T1` checks retained output
  bytes across all 84 cases; RTX 5090 `T1` checks request and output SHA-256 hashes (`84/84`).
  Neither replaces managed package qualification or a quality and leak screen.
- **`INT8 KV` / `BF16 KV`:** Attention KV cache storage formats (`--kv-dtype` / `kv_dtype`). The
  32 GB RTX 5090 profile uses 16-bit `BF16 KV` (`--kv-dtype bf16`, 146,368 automatic KV tokens
  across up to two requests in flight). The 24 GB native profiles use 8-bit `INT8 KV`
  (`kv_dtype: "int8"`), which halves the KV footprint relative to BF16 and holds the full
  131,072-token ceiling (`rk4v4` 4-bit KV is unshipped and off).
- **`shared Host budget`:** Host RAM that a lane's profile reserves for session state held off the
  GPU (`--host-context-mib` in the RTX 5090 container profile). Inactive resident continuations sit
  there between turns; sizes are in [lanes and limits](#lanes-and-limits).
- **`strict-origin profile`:** Profile requiring `--session-checkpoint-require-origin-auth`
  (`require_origin_auth: true`), a checkpoint root, and at least a 32-byte API key (64 characters
  as generated). It keys `manifest.mac` from that bearer key and refuses or quarantines modified or
  unauthenticated checkpoints.
- **`draft window`:** Draft tokens (`K`, `--draft-tokens` / `draft_tokens`, receipt fields
  `speculative_draft_window` or `draft_window`) proposed per decode round. All lanes use `7` under
  `DFlash2` (`K=7`; native profiles used `3` under `MTP3` through `v0.15.0`).
- **`schema 3 checkpoints`:** Checkpoint format (`checkpoint_schema_version: 3`, fingerprint schema
  2, status schema 2, request-log schema 30) at `/checkpoints-v013` on RTX 5090 (`checkpoints-v019`
  on host in `v0.19.0`) and `cache/<release-instance-id>/session-checkpoints-v3` natively.
  Generations publish atomically with SHA-256 digests and `manifest.mac` for exact-identity restore.
- **`retained state`:** Server-side Responses state (KV cache, device and host state images, draft
  context) held in memory or restored from a local NVMe checkpoint. It is addressed through
  `previous_response_id` with session identity derived from `prompt_cache_key`, and attested on
  reuse by `usage.input_tokens_details.cached_tokens`. When it is absent, evicted, or
  incompatible, NInfer returns `previous_response_not_found` and Oh My Pi replays its transcript.
- **`true-cold durability`:** Oracle checking that a checkpoint-restored continuation emits token
  IDs and UTF-8 bytes identical to a zero-reuse cold-process reference (`request_id = 1`, `0`
  cached tokens).
- **`source_wait`:** Server-side seconds (`requests.jsonl`) a forked or resumed request waits for
  its source state or an in-flight checkpoint export before prefill starts.

## Where the history lives

- [`CHANGELOG.md`](../CHANGELOG.md) — chronological product changes across releases.
- [`RELEASES.md`](RELEASES.md) — per-version component identities, acceptance summaries, and
  release cut procedures.
- [`releases/v0.19.0/NINFER_RELEASE_NOTES.md`](../releases/v0.19.0/NINFER_RELEASE_NOTES.md) (and
  prior `releases/<tag>/NINFER_RELEASE_NOTES.md`) — immutable per-release notes and limitations.
- Immutable tagged guides (`https://github.com/alphastorm/omp-ninfer/blob/<tag>/docs/QUICKSTART.md`,
  such as [`v0.10.0`](https://github.com/alphastorm/omp-ninfer/blob/v0.10.0/docs/QUICKSTART.md) and
  [`v0.7.2`](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)) — complete
  setup instructions for operators remaining on a prior release.

Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.
