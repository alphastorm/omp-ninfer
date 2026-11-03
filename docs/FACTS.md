# OMP NInfer — canonical facts

Updated: 2026-11-01 · Published release: v0.16.0 (2026-11-01) · stock Oh My Pi 18.14.0

Oh My Pi (coding-agent client) → OMP NInfer (qualified appliance and release layer) → NInfer
(inference engine) → Qwen3.8 27B (served model).

**Qualified on RTX 5090 · 4090 · 3090**, bound to the exact profiles in
[`releases/v0.16.0/manifest.json`](../releases/v0.16.0/manifest.json).
[Get started](QUICKSTART.md) ·
[Download v0.16.0](https://github.com/alphastorm/omp-ninfer/releases/tag/v0.16.0)

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

## Prepared next — v0.16.2 / Host reclaim and OMP 18.15.0

**Prepared next: v0.16.2 / stock OMP 18.15.0.** This successor to published v0.16.0 rebuilds
all three runtimes at `a87de3613c17bced777b446fb545f872d8395ec1`: published RTX 5090
`v0.7.0-qwen38-5090-beta.5` (server `cc99a460`, image `a0cbb8a5`) and planned native
`v0.8.0-qwen38-{3090,4090}-beta.2`. It includes byte-proven durable-generation Host reclaim
before export refusal, export-retirement reservation, opt-in FP32 identity repair, deterministic
bounded RDC builds and native repair/power/qualification-driver fixes. The model and serving
shapes stay unchanged, including RTX 5090 deployment profile `qwen38-5090-v0.13.0`.
Native version/instance identities advance; checkpoint compatibility is not inferred.

The published 5090 component reports a same-path double-build match (661 artifacts / 3 package
outputs), not a renewed v0.16.0 reproducibility exception. Its published-image lane receipt,
both native qualifications/cuts, all fresh product/client/restore observations, exact-subject
reviews, immutable pins and founder-owned product publication remain separate gates. No v0.16.0
runtime proof, acceptance or waiver is relabeled. The held v0.16.1 client-only candidate is not
the staging base.

The selected upstream release is `v18.15.0` (release `430630500`, source
`3fedf8d53267e32a6d7521ce725fdcc4a36fdc67`, tree
`48bc72ba2418c0b78163d9769e91a0d8683e642b`). The proposed
[prepared notes](../releases/v0.16.2/NINFER_RELEASE_NOTES.md#stock-omp-18150) record:

| Client platform | Raw asset / ID | Bytes | Asset = binary SHA-256 |
| --- | --- | ---: | --- |
| macOS arm64 (preview) | `omp-darwin-arm64` / `698539455` | 215295120 | `d36dfabf0ee52d6f08efadb59c46f0349545c6f6975522417adae29646e73e34` |
| Windows x64 | `omp-windows-x64.exe` / `698539443` | 243250176 | `978846a816cb77f44a55e32b16493375ca837fbf87e0aec35a9c1c934bff0cd0` |
| Linux x64 (WSL2-scoped) | `omp-linux-x64` / `698539441` | 276785328 | `6737ee2415555a3656cc7b89c14d1c25c18658ee4c0fd4f7309705149ccb7b0f` |

The [review](measurements/2026-11-01-omp-18150-client-upgrade-review.json) distinguishes carried
Responses/state/schema and Qwen policy blobs from changed replay utilities and session maintenance.
Retire only operator `compat.thinkingLoopGuard`; keep stateful Responses, encrypted-reasoning
opt-out and reasoning-summary opt-out. Preserve default guard/compaction settings and the existing
high→medium/off→low effort clamps. Explicit `retry.modelFallback=false` also gates the new
missing-key fallback branch; it does not govern optional auxiliary widget-role credential selection.
Isolated local-only auth and separately attributed optional requests remain necessary acceptance
boundaries. No native/Linux vision or native Linux OS qualification is added.

## Current release

Published release **v0.16.0** (2026-11-01, GitHub `Latest`; superseding `v0.15.0` and the
planned `v0.15.1` patch) retains unmodified upstream
Oh My Pi **18.14.0** (`31147f9d`, tree `9a63b5bf`, upstream binaries rebuilt with Bun 1.4.4 for
CVE-2026-91403 and CVE-2026-111497; upstream `18.14.1` and `18.14.2` are deferred to a separate
`v0.16.1` client patch) and shared published model container version 3 `81f924d4`
(`qwen3_8_27b-v3.ninfer`, 20,437,521,664 bytes, revision `1cbd84e7`), while rebuilding all three
runtime packages from common engine source `26fa28d0`
(`26fa28d0e7834515508fc07ac503164a6effc820`, tag `rebase/ckpt-native-n16`) on upstream
`Neroued/ninfer` master `64d10fbf`: the RTX 5090 container runtime (`v0.7.0-qwen38-5090-beta.4`,
image `7a5a7bb8` on base `d4377ed0`, server `bab3fd77`, kept strict-origin profile
`qwen38-5090-v0.13.0`, config `751d22dc`), the native Windows RTX 4090 package
(`v0.8.0-qwen38-4090-beta.1`, package `06526bdb`, server `c6f59e9e`, profile
`qwen38-4090-native-v0.8.0-beta.1`, public config `f00cfac9`, DFlash2 `K=7`, INT8 KV, `C1`,
`1,024`-token prefill chunk, `15,747.734375 MiB` / `16,512,696,320` B shared Host budget, `640 MiB`
headroom, 450 W owner baseline), and the native Windows RTX 3090 package
(`v0.8.0-qwen38-3090-beta.1`, package `040d5923`, server `72cd776b`, profile
`qwen38-3090-native-v0.8.0-beta.1`, public config `cbe67aae`, DFlash2 `K=7`, INT8 KV, `C2` over one
shared 131,072-token pool, `180 s` pending timeout, `1,024`-token prefill chunk, `20,867.734375 MiB`
/ `21,881,405,440` B shared Host budget, `768 MiB` headroom, 350 W serving cap / 370 W restored).
Release authority: [`releases/v0.16.0/manifest.json`](../releases/v0.16.0/manifest.json) ·
[`releases/v0.16.0/NINFER_RELEASE_NOTES.md`](../releases/v0.16.0/NINFER_RELEASE_NOTES.md) ·
[`COMPATIBILITY.md`](COMPATIBILITY.md). Native `rk4v4` 4-bit KV (`262,144`-token context) is
deferred to a follow-up release on the true-cold restore oracle (`EXP-107`).

The tagged [`releases/v0.16.0/NINFER_RELEASE_NOTES.md`](../releases/v0.16.0/NINFER_RELEASE_NOTES.md)
header and the `publication` block of
[`releases/v0.16.0/manifest.json`](../releases/v0.16.0/manifest.json) record the composition's
freeze-time state (prepared, fresh acceptance passed, product publication a separate gate) and are
immutable after the freeze, and the publication record is this section,
[`docs/RELEASES.md`](RELEASES.md), and the
[GitHub release](https://github.com/alphastorm/omp-ninfer/releases/tag/v0.16.0).

| Component or lane | Form and transport | Release tag and source | Image or package | Serving profile | Context | Requests in flight | Speculative backend | Modalities |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
| Oh My Pi client | Unmodified upstream release binaries: macOS arm64 (preview), Windows x64, Linux x64 (WSL2 live evidence) | `v18.14.0`, source `31147f9d`, tree `9a63b5bf` | `omp-darwin-arm64` (`60884395`), `omp-windows-x64.exe` (`620a5935`), `omp-linux-x64` (`e7dd2b60`) in [`client-components.json`](../releases/v0.16.0/qualification/client-components.json) | Per-model `compat.statefulResponses: true`, fail-closed config | 131,072 | `2` on RTX 5090 and native RTX 3090 (`C2` shared 131,072-token pool); `1` on native RTX 4090 (`C1`) | Target lane | Coding agent, typed tools, branches, compaction |
| RTX 5090 | Windows 11 + Docker Desktop/WSL2 container on loopback `127.0.0.1:18089`; local Windows client or macOS client over manual SSH tunnel (preview) | `v0.7.0-qwen38-5090-beta.4`, source `26fa28d0` on `64d10fbf` | OCI image `7a5a7bb8` (base `d4377ed0`), server `bab3fd77`, archive `f3a35cdb` (579,765,099 B), SPDX `b09ad9a7`, model `81f924d4` | `qwen38-5090-v0.13.0`, config `751d22dc`: BF16 KV (146,368 automatic KV tokens), shared Host budget 20,867.734375 MiB (21,881,405,440 B), 28,672 MiB host floor, 1,024-token prefill chunk, 60,000 ms keep-warm, mandatory `--session-checkpoint-require-origin-auth`, `/checkpoints-v013` (schema 3); checked first build under founder-approved 5090-only reproducibility exception | 131,072 | 2 (plus 2 extra device-state slots, 180 s pending timeout) | DFlash2 draft window 7 (`--lm-head-draft`) | Vision, text, typed tools, JSON-schema output, preserved thinking |
| RTX 4090 native Windows 11 | Native Windows package on loopback `127.0.0.1:18082`, UUID-bound GPU on a two-GPU host | `v0.8.0-qwen38-4090-beta.1`, source `26fa28d0` on `64d10fbf` | Package `06526bdb` (991,969,490 B), server `c6f59e9e`, SPDX `825a8d30`, CycloneDX `b8c8efcb`, model `81f924d4` | `qwen38-4090-native-v0.8.0-beta.1`, public config `f00cfac9`: INT8 KV, `Q4_G64_FP16` draft MLP + host-mapped token embedding, `Group64` A8 and FP32 head logits off, shared Host budget 15,747.734375 MiB (16,512,696,320 B), 640 MiB admission headroom, 32,768 MiB host floor, 1,024-token prefill chunk, 60,000 ms keep-warm, 450 W owner baseline, mandatory `--session-checkpoint-require-origin-auth`, `session-checkpoints-v3` (schema 3) | 131,072 | 1 (plus 2 extra device-state slots, 30 s pending timeout) | DFlash2 draft window 7 (`artifact-default` proposal) | Text, typed tools, JSON-schema output, preserved thinking (no vision) |
| RTX 3090 native Windows 11 | Native Windows package on loopback `127.0.0.1:18082`, UUID-bound GPU on the same two-GPU host | `v0.8.0-qwen38-3090-beta.1`, source `26fa28d0` on `64d10fbf` | Package `040d5923` (1,008,976,979 B), server `72cd776b`, SPDX `6f78e190`, CycloneDX `3b217f69`, model `81f924d4` | `qwen38-3090-native-v0.8.0-beta.1`, public config `cbe67aae`: INT8 KV, `Q4_G64_FP16` draft MLP + host-mapped token embedding, `Group64` A8 and FP32 head logits off, shared Host budget 20,867.734375 MiB (21,881,405,440 B), 768 MiB admission headroom, 1,024-token prefill chunk, 350 W serving power cap (370 W restored on stop), keep-warm off, mandatory `--session-checkpoint-require-origin-auth`, `session-checkpoints-v3` (schema 3) | 131,072 | 2 over one shared 131,072-token pool (plus 2 extra device-state slots, 180 s pending timeout) | DFlash2 draft window 7 (`artifact-default` proposal) | Text, typed tools, JSON-schema output, preserved thinking (no vision) |

- **Sequential native topology on one two-GPU host:** Both native Windows lanes install on the same
  two-GPU Windows 11 host (RTX 4090 at index 0, RTX 3090 at index 1), each bound to its own GPU
  UUID and PCI address. Only one native lane runs at a time on loopback port `18082`; within the
  active RTX 3090 lane, up to two requests run concurrently (`C2`) sharing one 131,072-token INT8
  KV pool. This is not multi-GPU inference and not simultaneous RTX 4090 and RTX 3090 serving.
- **Native upgrade, rollback to `v0.7.0-beta.3`, and MTP-to-DFlash2 checkpoint boundary:** With
  `alphastorm/ninfer#48` (`9cb741dc`) and the `v0.16.0` installer handoff fixes (`577fecba`) in
  `v0.8.0-qwen38-{4090,3090}-beta.1`, `Install-Release.ps1` stops a running incumbent lane through
  its own controller and hands off the GPU-owner lease across equal or changed power caps, closing
  [#94](https://github.com/alphastorm/omp-ninfer/issues/94) (the `v0.14.0`–`v0.15.0` RTX 3090
  stop-before-upgrade prerequisite is dropped) and retaining `v0.7.0-qwen38-{4090,3090}-beta.3` as
  `previous_release` for `Control-Release.ps1 -Action Rollback`
  (**PASS 3/3 scenarios on both native lanes** from published `v0.14.0`
  `v0.7.0-qwen38-{4090,3090}-beta.3`: RTX 4090 `87038cfb` → `06526bdb`, summary `38a3a380`, passed
  `1c` running-lane upgrade in `211.93 s`, `2c` forced post-activation first-`Start`
  port-ownership refusal with rollback in `211.37 s` deleting `4/4` transaction-created targets,
  and `3c` interrupted install then `-RepairInterruptedInstall` deleting `4/4` targets and
  same-instance reinstall in `309.80 s` with `450 W` restored; RTX 3090 `a7637f66` → `040d5923`,
  summary `631428b5`, passed `1c` running-lane upgrade at 350 W in `220.32 s`, `2c` forced
  post-activation first-`Start` failure with rollback in `206.96 s` deleting `4/4` targets, and
  `3c` interrupted install then repair deleting `4/4` targets and same-instance reinstall in
  `322.25 s` with `370 W` restored; canonical states unchanged; each package's isolated 15-phase
  scratch qualification runs in a fresh scratch root with no predecessor and records
  `rollback: not_applicable`, `0` directions). Prior MTP3 checkpoints are
  not imported into DFlash2; keep prior checkpoint roots untouched for rollback and replay
  authoritative OMP transcripts for fresh sessions.
- **Admission on the RTX 5090 and 24 GB native lanes:** Two requests run together on the RTX 5090
  (`146,368`-token automatic BF16 KV pool) and on the native RTX 3090 (`131,072`-token shared INT8
  KV pool; while two 2,048-token decode requests overlap on RTX 3090, per-request decode is
  `0.70–0.73×` of `C1` while combined throughput is `1.385×` and pair completion wall is `0.722×`)
  only while both prompts plus output reservations fit inside the shared pool; excess requests wait
  up to 180 s (`30 s` on `C1` RTX 4090). Native RTX 4090 and RTX 3090 profiles set
  `--admission-headroom-mib` to 640 MiB and 768 MiB respectively (`StartupMemoryBudget::fits()` in
  `375f47c9` enforces both physical free memory and configured-budget headroom after CUDA graph
  initialization, retaining the 32,768 MiB RTX 4090 host RAM floor). `StateImageStore::prepare_host_export`
  (`8c639fe0` / `80c0af77`, `EXP-105`) materializes immutable `StateImage` replicas into the counted
  Host arena and releases device state replicas before off-worker disk serialization begins, and
  `EngineCore::reserve_resident_units()` (`ea2edc20`, `EXP-106`) waits when in-flight exports can
  release pinned device KV pages.
- **Schema 3 checkpoint stores and Windows durability:** All three lanes use schema 3
  checkpoints (fingerprint schema 2, status schema 2, request-log schema 30 with additive optional
  `request_done.speculative.attempted_per_position` and Prometheus
  `ninfer_spec_decode_position_tokens_total`) with mandatory `--session-checkpoint-require-origin-auth`
  (requiring a configured checkpoint root and at least a 32-byte API key; the documented generated
  key is 64 characters). The RTX 5090 container mounts host directory `checkpoints-v013` at
  `/checkpoints-v013` with non-blocking export; native lanes use
  `cache/<release-instance-id>/session-checkpoints-v3` under each immutable component release's own
  cache root (for example, `qwen38-4090-native-v0.8.0-beta.1-26fa28d0e783` or
  `qwen38-3090-native-v0.8.0-beta.1-26fa28d0e783`) with handle-anchored replacement, extended-length
  roots, and a current-parent publication fence (Windows `ntfs-write-through` is not POSIX `fsync`
  or a power-loss guarantee; physical disk exhaustion returns `capacity`, including HTTP 409 on
  DELETE without mutating surviving Responses objects). Keep prior checkpoint roots untouched; prior
  sessions resume by replaying authoritative OMP transcripts for a fresh prefill.
- **Dual native SBOMs and RTX 5090 reproducibility exception:** Each native outer asset set (10
  hashed entries plus `SHA256SUMS`, 11 files) ships both its SPDX 2.3 file inventory
  (`<package-stem>.spdx.json`) and a separate canonical CycloneDX 1.5 dependency inventory
  (`<package-stem>.cdx.json`) covering 12 resolved vcpkg packages with 13 DLL associations, CUDA
  13.3 DLLs, vendored sources, MSVC CRT, and DirectStorage redistributables, and passes **43/43**
  second-build EXE/DLL byte comparisons (`17` EXEs and `26` DLLs per architecture). The RTX 5090
  container ships the checked first-build `bab3fd77` binary under an explicit founder-approved
  5090-only reproducibility exception (`502/1,242` ELF files differed across two clean WSL2 builds
  under `nvcc` 13.1.115; deterministic module IDs remain a follow-up).
- **Fresh runtime qualification, route acceptance, and G4 councils:** Fresh `v0.16.0` acceptance on
  frozen candidate `56899320d416bafda5c15d7e454e9b593badc0a6` passed on **2026-11-01**:
  all five documented routes (host `2/2`, macOS `10/10`, Windows `5/5`, native `7/7` each;
  **31/31 blocks**), all three stock 18.14.0 clients, and both
  `v0.8.0-beta.1` native public installs (including RTX 3090 `C2` fanout, parallel stock OMP
  overlap at limit 2, and two automatic-compaction/control-recall epochs), with independent host
  restoration. Both native lanes passed **22/22 behavior gates**, their public installers returned
  `already_installed` with exact qualified bytes and unchanged pointers, and each passed
  **18/18 Restore plus 18/18 final Audit checks**. First-lineage rollback is `not_applicable`,
  zero directions. RTX 5090 hold **412.552 s**; RTX 4090 / RTX 3090 driver windows
  **499.977 / 1,225.308 s**, stopped **450 / 370 W** restored
  ([documented routes](../releases/v0.16.0/acceptance/documented-routes.json),
  [composed acceptance](../releases/v0.16.0/acceptance/composed-external-installation.json),
  [restoration](measurements/2026-11-01-v0160-acceptance-restoration.json)).
  The G4 fork council (`CR-20261031T162716Z-26fa28d0`, ledger `b2871c36`, 4/4 seats) and G4
  product-tooling council (`CR-20261101T123454Z-56899320-product`,
  sequence `omp-ninfer-v0.16.0-product-56899320`, subject `56899320`,
  4/4 seats completed, 0 missing or aborted) closed by disposition in round 1, with no in-scope
  residual P0/P1. The combined
  [`review/runtime-ledger.json`](../releases/v0.16.0/review/runtime-ledger.json) SHA-256 is
  `ab195970955c58b584ddbcf2143072b56ced28e714251e975c0f67986722e627`;
  product P2/P3 residuals are deferred in [#128](https://github.com/alphastorm/omp-ninfer/issues/128),
  retaining [#109](https://github.com/alphastorm/omp-ninfer/issues/109). The earlier
  `omp-ninfer` [#94](https://github.com/alphastorm/omp-ninfer/issues/94)–[#96](https://github.com/alphastorm/omp-ninfer/issues/96),
  [#116](https://github.com/alphastorm/omp-ninfer/issues/116), and
  [#117](https://github.com/alphastorm/omp-ninfer/issues/117) are closed, with other deferrals tracked
  in [#88](https://github.com/alphastorm/omp-ninfer/issues/88)–[#90](https://github.com/alphastorm/omp-ninfer/issues/90)
  and `alphastorm/ninfer`
  [#50](https://github.com/alphastorm/ninfer/issues/50)–[#54](https://github.com/alphastorm/ninfer/issues/54).

## Models

v0.16.0 pins one shared registered NInfer conversion artifact (`qwen3_8_27b.ninfer`) from
[`neroued/Qwen3.8-27B-NInfer`](https://huggingface.co/neroued/Qwen3.8-27B-NInfer) across all three
lanes in [`releases/v0.16.0/manifest.json`](../releases/v0.16.0/manifest.json) (retaining the single
`components.model` binding introduced in v0.13.1):

| Lane scope | Hugging Face revision | Bytes | SHA-256 | Notes |
| --- | --- | ---: | --- | --- |
| All qualified lanes (`components.model`: RTX 5090 container, native RTX 4090, native RTX 3090) | `1cbd84e7221e51186bd7f093a149912d2489625b` | 20,437,521,664 | `81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da` | Published model container version 3 (`qwen3_8_27b-v3.ninfer` on host); serves public model ID `q38-ninfer` on RTX 5090 (DFlash2 draft window 7, `--lm-head-draft`, text, vision), `qwen3.8-27b` on native RTX 4090, and `q38-ninfer` on native RTX 3090 (both DFlash2 draft window 7, `artifact-default` proposal, text and tools, vision disabled) |

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
- **Oh My Pi client contract:** Stock Oh My Pi 18.14.0 has no `omp appliance` commands. Model
  fragments set `compat.statefulResponses: true` per model (upstream
  [#13686](https://github.com/can1357/oh-my-pi/pull/13686)), and `PI_OPENAI_STATEFUL` must be
  absent from the environment. Custom Responses hosts default to `auto` image detail upstream
  ([#13687](https://github.com/can1357/oh-my-pi/pull/13687)), removing the old
  `supportsImageDetailOriginal` override, and unavailable saved models fail closed
  ([#13689](https://github.com/can1357/oh-my-pi/pull/13689)).
  [`examples/manual-tunnel/fail-closed.yml`](../examples/manual-tunnel/fail-closed.yml) disables
  retries, model fallback, and `checkUpdate`, leaves compaction at the OMP default, and sets
  `providers.maxInFlightRequests` per provider ID (`ninfer-beta: 2`, `ninfer-main: 2`,
  `ninfer-native-4090: 1`, `ninfer-native-3090: 2`, `ninfer-heavy: 1`).

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
  20,867.734375 MiB / 21,881,405,440-byte Host context budget on RTX 5090, 15,747.734375 MiB /
  16,512,696,320-byte shared Host budget on RTX 4090, 20,867.734375 MiB / 21,881,405,440-byte
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
  pinned in [`releases/v0.16.0/manifest.json`](../releases/v0.16.0/manifest.json).
- **Single trusted owner:** Designed for one trusted operator on owner-controlled hardware, not
  multi-tenant isolation. Full threat model: [`SECURITY.md`](SECURITY.md).

## Measured proof

Per-lane runtime qualification receipts in v0.16.0 (never transfer one lane's numbers or
capabilities to another):

| Lane | Long-context retrieval (130,048 tokens) | Decode measurement | Speculative acceptance | Receipt |
| --- | --- | --- | --- | --- |
| RTX 5090 (`v0.7.0-qwen38-5090-beta.4`, DFlash2 K=7, BF16 KV, `C2`) | Exact in **56.62 s** cold (`56.617 s`, **2,297.0 tok/s** wall; **56.51 s** / `56.505 s` server) | **181.78 tok/s** server-side (**180.25 tok/s** wall) over 2,048 tokens | **0.244** DFlash2 acceptance, **2.71** tokens/round | [`rtx5090.json`](../releases/v0.16.0/qualification/rtx5090.json) (2026-11-01) |
| RTX 4090 native (`v0.8.0-qwen38-4090-beta.1`, DFlash2 K=7, INT8 KV, `C1`) | Exact in **83.35 s** (83.352 s) | **254.27 tok/s** C1 decode (4,541 prompt / 1,024 completion tokens); prefill **2,139.14 tok/s** | **83.88%** DFlash2 acceptance | [`rtx4090.json`](../releases/v0.16.0/qualification/rtx4090.json) (2026-10-31) |
| RTX 3090 native (`v0.8.0-qwen38-3090-beta.1`, DFlash2 K=7, INT8 KV, `C2` shared pool, 350 W cap) | Exact in **188.99 s** (188.994 s) | **148.43 tok/s** C1 decode (4,541 prompt / 1,024 completion tokens); prefill **974.15 tok/s** | **83.88%** DFlash2 acceptance | [`rtx3090.json`](../releases/v0.16.0/qualification/rtx3090.json) (2026-11-01) |

- **v0.16.0 (`26fa28d0`) native DFlash2 K=7, RTX 3090 `C2`, and first-fork export-State residency:**
  On frozen source `26fa28d0` and shared model `81f924d4`, RTX 4090 (`06526bdb`) passed 131,072-token
  INT8 `C1` fit/true-cold ([`rtx4090-windows-native.fit.json`](../releases/v0.16.0/qualification/rtx4090-windows-native.fit.json)
  `44c50008`: `1,056,964,608` B / `1,008 MiB` available >= `671,088,640` B floor, `22,639 MiB` peak,
  `32/32` tokens identical), `83/83` agent-probe parity (`max source_wait <= 0.0178 s`), `15/15`
  managed qualification phases (**254.27 tok/s** `C1` decode, **2,139.14 tok/s** prefill, **83.88%**
  acceptance, **83.35 s** retrieval, **1,647** explicit-save and **1,650** graceful-stop cached
  tokens across **42.21 s** restart, `450 W` restored in
  [`rtx4090.json`](../releases/v0.16.0/qualification/rtx4090.json) `69ebf60c`), `3/3`
  `v0.7.0-beta.3` upgrade/rollback/repair rehearsals (`38a3a380`: `1c` running-lane upgrade `211.93
  s`, `2c` forced first-`Start` rollback `211.37 s`, `3c` interrupted-install repair and reinstall
  `309.80 s`, `450 W` restored), the 1,120-prompt `EXP-102` powered quality screen
  ([`rtx4090-windows-native.quality-screen.json`](../releases/v0.16.0/qualification/rtx4090-windows-native.quality-screen.json)
  `6231dccd`: `1,120` prompts, both arms `80/80` deterministic with `0` missing/error samples,
  `777/1,120` paired outputs changed, **9/9** primary bounds passed: `recall` lower `-0.0082`,
  `precision` lower `-0.0093` vs `-0.02`; `unsupported` upper `+0.0045` vs `+0.03`;
  `schema`/`tool_selection`/`tool_argument` lower `0` vs `-0.02`; `duplicate` upper `+0.0046` vs
  `+0.02`; `redaction` lower `-0.0139` vs `-0.05`; `secret_leak` ratio `1.0525`, upper `1.0985 <
  1.10`, counts `533 → 561`, not zero), and the 108-role + 7-supplemental ABBA speed gate vs
  `v0.14.0` MTP3 ([`rtx4090-speed.json`](../releases/v0.16.0/qualification/rtx4090-speed.json)
  `32acdecc`, [`rtx4090-speed-waiver.json`](../releases/v0.16.0/qualification/rtx4090-speed-waiver.json)
  `92b94c4a`: 108-case role corpus `role108` weighted **×1.2736** at `139.87 → 178.13 tok/s`, all
  `115` cases **×1.2741** at `138.94 → 177.02 tok/s`, `7` supplementals **×1.2778** / min
  **×1.0804**, `115/115` repeats per build and `43/115` cross-build byte-identical, with depth-0
  case `log-024@0` at **0.934** / `139.41 → 130.19 tok/s` below the `0.95` per-case decode ratio
  floor waived by the founder with disclosure). RTX 3090 (`040d5923`, `C2` over one shared
  131,072-token INT8 pool) passed the `EXP-101` 1,120-prompt powered screen
  ([`rtx3090-windows-native.quality-screen.json`](../releases/v0.16.0/qualification/rtx3090-windows-native.quality-screen.json)
  `671659f0`: `1,120` prompts, both arms `80/80` deterministic with `0` missing/error samples,
  `771/1,120` paired outputs changed, **9/9** primary bounds passed: `recall` lower `-0.0073`,
  `precision` lower `-0.0070` vs `-0.02`; `unsupported` upper `+0.0089` vs `+0.03`;
  `schema`/`tool_selection`/`tool_argument` lower `0` vs `-0.02`; `duplicate` upper `+0.0059` vs
  `+0.02`; `redaction` lower `-0.0119` vs `-0.05`; `secret_leak` ratio `1.0294`, upper `1.0673 <
  1.10`, counts `545 → 561`, not zero), 84-role depth-0 ABBA speed
  ([`rtx3090-speed.json`](../releases/v0.16.0/qualification/rtx3090-speed.json) `c904d341`: 84
  depth-0 cases at 350 W, weighted **×1.2684** / `1.268360×` at `79.37 → 100.67 tok/s`, minimum
  **0.9764×** / `0.976442×` on `log-024@0 >= 0.95`, zero waived cases, `84/84` within-engine and
  `36/84` cross-engine byte-identical), shipping-package `C2` fit/true-cold
  ([`rtx3090-windows-native.fit.json`](../releases/v0.16.0/qualification/rtx3090-windows-native.fit.json)
  `662619d7`: `1,110,441,984` B / `1,059 MiB` available >= `805,306,368` B / `768 MiB` floor,
  `22,584 MiB` peak, `1,742 MiB` min free, two `59,866`-token true-cold sessions restored at
  `59,840 + 26` tokens with `32/32` token IDs and UTF-8 bytes identical), `83/83` agent-probe
  parity positions under `p16-agent-parity/2` (`0` cache-gap deltas, min TTFT bound margin `0.169
  s`, `C2` `fanout-concurrency 4` `5/5` HTTP 200, calibrated `2 × 59,879`-token test `18/18` HTTP
  200 across 3 trials, `0` HTTP 500; summary `8218925c`), `3/3` `v0.7.0-beta.3`
  upgrade/rollback/repair rehearsals (`631428b5`: `1c` running-lane upgrade `220.32 s`, `2c` forced
  first-`Start` rollback `206.96 s`, `3c` interrupted-install repair and reinstall `322.25 s`, `370
  W` restored), and `15/15` managed qualification phases in
  [`rtx3090.json`](../releases/v0.16.0/qualification/rtx3090.json) (public sanitized `48c7f635`,
  raw `038fe713`: **148.43 tok/s** `C1` decode, **974.15 tok/s** prefill, **83.88%** DFlash2
  acceptance, **188.99 s** exact 130,048-token retrieval, **1,647** explicit-save and **1,650**
  graceful-stop cached tokens across **46.88 s** restart, schema 2 normal and `17,878.578125 MiB`
  pressure product protocol under the
  founder-approved `agent_protocol.py` `C2` precondition override `317b98ee` in
  [alphastorm/ninfer#56](https://github.com/alphastorm/ninfer/pull/56), `state_security` `898 ms`,
  isolated rollback `not_applicable` with `0` directions, `370 W` restored),
  with paired 2,048-token `C2` vs `C1` decode reaching **1.385×** median aggregate (`57.68 → 79.90
  tok/s`), **0.722×** pair completion wall (`71.01 → 51.26 s`), and **0.70–0.73×** concurrent
  per-request decode (`EXP-106`), and post-resume first-fork TTFT dropping from **15.4–17.8 s** to
  **0.33–0.76 s** (`source_wait <= 0.033 s`, `EXP-105`). On RTX 5090 (`bab3fd77` / image `7a5a7bb8`),
  all `11/11` exact-source RC phases (`146,368` automatic BF16 KV tokens unchanged) and `84/84` `T1`
  request/output SHA-256 hashes passed at **347.20 → 346.95 tok/s** (**×0.999282**), with post-resume
  first-fork TTFT dropping from **5.03 s** to **0.11 s** (`source_wait` `4.850 s → 0.005 s`,
  `EXP-105`), the published-image lane gate passed in
  [`rtx5090.json`](../releases/v0.16.0/qualification/rtx5090.json) (`2200fa44`, **181.78 tok/s**
  server / **180.25 tok/s** wall decode at **0.244** DFlash2 acceptance and **2.71 tokens/round**,
  **56.62 s** wall / **56.51 s** server 130,048-token retrieval at **2,297.0 tok/s**,
  `agent_protocol` passed, `30,398 MiB` idle VRAM, extracted executable `bab3fd77`), and the
  `26fa28d0` agent-probe campaign vs `v0.14.0` passed `warm_arrival` 12/12
  (`resume-first/fork_after_resume` `5.159 → 0.278 s`, `source_wait` `4.997 → 0.000 s`), `agent_mix`
  51/51, `sibling_continue` 5/5, `fleet_probe` `fanout` 11/11 (`post_restart_branch_0` `5.437 →
  0.300 s`), and 4-way concurrent fanout 5/5 under rule `p16-agent-parity/2` (a judge correction
  pairing simultaneously submitted concurrent branches by server admission order; two post-restart
  `restore` positions — `0.526 s` candidate vs `0.491 s` bound at `restore_0` and `0.520 s`
  candidate vs `0.492 s` bound at `restore_1` — were waived by the founder with disclosure that the
  first request after a server restart sometimes takes `~0.5 s` instead of `~0.24 s` in both
  engines, and `v0.7.0-qwen38-5090-beta.4` hits the slow mode somewhat more often, `4/8`
  post-restart requests across four two-restart runs vs `2/8` on the incumbent).
- **v0.14.0 native Windows schema 3 restart, protocol, and matched pre-cut gates:** On frozen source
  `2c6f423b` and published model `81f924d4`, both native lanes reused **1,647 cached tokens** after
  explicit save and **1,650 cached tokens** after graceful `stop-event` flush across process
  replacement (34.062 s on RTX 4090, 35.016 s on RTX 3090) with counters matching an independently
  measured cold-process baseline, and passed canonical schema 2 product protocol smokes at full and
  reduced (12,438.578125 MiB on RTX 4090; 9,366.578125 MiB on RTX 3090) shared Host budgets
  ([`rtx4090.json`](../releases/v0.15.0/qualification/rtx4090.json),
  [`rtx3090.json`](../releases/v0.15.0/qualification/rtx3090.json)). Separately, matched pre-cut
  A/B comparisons against shipped beta.2 controls passed 84/84 retained-output T1 role parity, 4/4
  exact 130,048-token retrieval arms (`85.70/85.62 → 81.48/81.55 s` prefill on RTX 4090;
  `197.51/198.70 → 188.16/187.80 s` on RTX 3090), and strict C1 median decode
  (`151.215 → 151.573 tok/s`, ×1.00237 on RTX 4090; `90.855 → 90.879 tok/s`, ×1.000265 on RTX 3090;
  [`native-integration.json`](../releases/v0.15.0/qualification/native-integration.json)).
- **v0.14.0 RTX 5090 schema 3 restart and T1 decode comparison:** On the shipped `55f0b95a`
  first-build binary (`2c6f423b`) and `81f924d4` model, the four-boot schema 3 restart gate reused
  **20,926 cached tokens** and produced **27 byte-identical continuation bytes** after an
  authenticated `fsync` save of **2,560,565,777 bytes**
  ([`durability.json`](../releases/v0.15.0/qualification/durability.json)), the 32 GB C2 durable
  pressure-overlap gate completed in **35.5524 s** with **1,074,790,400 bytes** headroom and
  **+2 MiB** graph growth
  ([`concurrency.json`](../releases/v0.15.0/qualification/concurrency.json)), and the 84-role ABBA
  fixed-KV T1 comparison matched all 84/84 request/output SHA-256 hashes (not retained-byte streams)
  with median decode **342.04 → 347.57 tok/s** (**×1.0162** / **101.62%** of the beta.2 control;
  [`decode-parity.json`](../releases/v0.15.0/qualification/decode-parity.json)). Earlier EXP-097
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
  latest published release (`v0.16.0`) and its exact manifest and profiles.
- **No other GPUs or profiles:** Support does not extend outside the exact RTX 5090, RTX 4090, and
  RTX 3090 profiles bound by [`releases/v0.16.0/manifest.json`](../releases/v0.16.0/manifest.json).
- **Client platform limits:** macOS (`darwin-arm64`) is preview without managed client installation
  or appliance lifecycle; Linux (`linux-x64`) live evidence is under WSL2 only, not a separately
  qualified native Linux OS.
- **Native lanes are text and tools only:** Vision is qualified only on the RTX 5090 container
  lane; while DFlash2 (`K=7`) is now qualified across all three lanes, native Windows RTX 4090 and
  RTX 3090 lanes serve text, typed tools, and JSON-schema structured output under DFlash2 `K=7` and
  refuse image inputs with `vision_disabled`.
- **Not multi-GPU inference or simultaneous two-lane native serving:** Only one UUID-bound native
  lane runs at a time on port `18082` (within the active RTX 3090 lane, `C2` serves up to two
  concurrent requests over one shared 131,072-token INT8 pool). Each native package's isolated
  15-phase scratch qualification runs in a fresh scratch root (`rollback: not_applicable`, zero
  directions), while upgrading an existing `v0.7.0-beta.3` install preserves `v0.7.0-beta.3` for
  `Control-Release.ps1 -Action Rollback` (prior MTP3 checkpoints are not imported into DFlash2).
- **Checkpoints are best effort:** Neither globally loss-free shutdown, universal warm reuse,
  cross-GPU checkpoint migration, nor automatic container restart is claimed.
- **No "no re-prefill" or universal speed claims:** In-process prefix caching is conceded prior art
  ([`RELATED_WORK.md`](RELATED_WORK.md)), and two requests in flight on the RTX 5090 (`146,368`-token
  BF16 pool) or native RTX 3090 (`131,072`-token shared INT8 pool, where individual overlapping
  decode is `0.70–0.73×` of `C1` while aggregate decode is `1.385×`) do not provide preemption or
  guaranteed faster single-session wall time.
- **Not independent external-user outcomes:** All qualification and acceptance receipts are
  owner-operated measurements on retained hardware.

## Glossary

- **`DFlash2`:** Speculative decoding backend (`--spec dflash2`) that uses the five-layer block
  drafter bundled in the version 3 model artifact to propose seven candidate tokens (`K=7`) in one
  masked-block pass for target verification. In `v0.16.0`, `DFlash2` (`K=7`) is the qualified
  speculative backend across all three lanes (`qwen38-5090-v0.13.0` on the RTX 5090 container lane
  with `--lm-head-draft`, and `qwen38-4090-native-v0.8.0-beta.1` and
  `qwen38-3090-native-v0.8.0-beta.1` on the 24 GB native Windows lanes using `proposal:
  "artifact-default"`, `Q4_G64_FP16` draft MLP `gate`/`up` weights, and host-mapped
  `token_embedding`).
- **`MTP3`:** Multi-token prediction speculative decoding backend (`--spec mtp --draft-tokens 3`
  with `--lm-head-draft`, or `backend: "mtp"`, `draft_tokens: 3` in native server configs) that
  drafts three candidate tokens per round so the target model verifies four tokens (the active
  token plus three drafts) in a single pass. It served the RTX 5090 lane prior to `v0.10.0` and the
  native Windows RTX 4090 and RTX 3090 lanes through `v0.15.0` (superseded by `DFlash2 K=7` in
  `v0.16.0`).
- **`Group64 A8` (`A8 off`):** Native prefill 8-bit group-64 integer-activation route
  (`-DNINFER_NATIVE_PREFILL_GROUP64_A8`, `group64_a8`) for the quantized model body on the native
  Windows lanes. All `v0.14.0`–`v0.16.0` native Windows packages compile it off (`A8 off`) after the
  RTX 4090 failed its preregistered 200-pair new-leak behavioral screen (five one-way changes) and
  the founder selected off conservatively across both cards.
- **`C1`:** Single-request (`concurrency: 1`) serving posture on the native Windows RTX 4090 lane
  (`qwen38-4090-native-v0.8.0-beta.1`), in contrast to two-request (`C2`) serving on the RTX 5090
  container lane (`qwen38-5090-v0.13.0`) and the native Windows RTX 3090 lane
  (`qwen38-3090-native-v0.8.0-beta.1`). As the serial `benchmark_c1` qualification gate (and
  matched strict `C1` / role-corpus speed-gate posture on both native lanes), it generates 1,024
  completion tokens after 4,541 computed prompt tokens with no prefix-cache hit (`seed 57004`,
  temperature `0` in strict ABBA comparisons), recording prefill throughput, decode throughput,
  speculative acceptance, peak VRAM, and peak board power.
- **`T1`:** Pre-cut output-parity and serial decode gate over 84 frozen role-corpus cases (`336`
  role requests across four `ABBA` arms with a fixed 131,072-token KV pool and persistence
  disabled), comparing a candidate build against the shipped control. Native Windows `T1` checks
  retained output bytes across all 84 cases, while RTX 5090 `T1` checks request and output SHA-256
  hashes (`84/84`) rather than retained byte streams; neither substitutes for managed package
  qualification or a global quality and leak screen.
- **`INT8 KV` / `BF16 KV`:** Key-value (`KV`) attention cache storage formats (`--kv-dtype` /
  `kv_dtype`) bound by each lane's profile. The 32 GB RTX 5090 container profile uses 16-bit
  `BF16 KV` (`--kv-dtype bf16`, 146,368 automatic KV tokens across up to two requests in flight),
  while the 24 GB native Windows RTX 4090 (`C1`) and RTX 3090 (`C2`, shared across up to two
  concurrent requests) profiles use 8-bit `INT8 KV` (`kv_dtype: "int8"`, halving the KV footprint
  relative to BF16) to hold the full 131,072-token context ceiling on 24 GB cards (`rk4v4` 4-bit KV
  remains unshipped and off).
- **`strict-origin profile`:** A deployment profile and runtime configuration (`qwen38-5090-v0.13.0`
  config `751d22dc`, `qwen38-4090-native-v0.8.0-beta.1` config `f00cfac9`, and
  `qwen38-3090-native-v0.8.0-beta.1` config `cbe67aae`) that enforces mandatory checkpoint origin
  authentication (`--session-checkpoint-require-origin-auth` / `require_origin_auth: true`). It
  requires a configured checkpoint root and a bearer API key of at least 32 bytes (64 characters as
  documented), keys each published checkpoint generation's `manifest.mac` HMAC from material
  derived from that bearer key, and refuses or quarantines unauthenticated or modified checkpoints
  at load.
- **`draft window`:** The number of candidate tokens (`K`, configured via `--draft-tokens` /
  `draft_tokens` and recorded in receipts as `speculative_draft_window` or `draft_window`) that the
  speculative drafter proposes in each decode round for the target model to verify in a single pass.
  In `v0.16.0`, all three qualified lanes use a draft window of `7` under DFlash2 (`K=7`; native
  profiles used `3` under MTP3 through `v0.15.0`).
- **`schema 3 checkpoints`:** The current on-disk session-checkpoint format
  (`checkpoint_schema_version: 3`, paired with fingerprint schema 2, status schema 2, and
  request-log schema 30) stored under `/checkpoints-v013` on the RTX 5090 container lane and
  `cache/<release-instance-id>/session-checkpoints-v3` on the native Windows lanes. Each generation
  is atomically published to local NVMe with SHA-256 file digests and a bearer-key-derived
  `manifest.mac` HMAC (`--session-checkpoint-require-origin-auth`), and restores only when the
  runtime binary hash, patch-stack SHA, model artifact, deployment profile, and session credentials
  match.
- **`retained state`:** Server-side OpenAI Responses continuation state (KV cache, device and host
  state images, and draft context) held in GPU/host memory or restored from a local NVMe checkpoint
  and addressed through `previous_response_id` with session identity derived from `prompt_cache_key`
  (attested on reuse by `usage.input_tokens_details.cached_tokens`). It serves as an acceleration
  layer rather than the sole copy of the conversation: when retained state is absent, evicted, or
  incompatible, the server returns `previous_response_not_found` and Oh My Pi replays its
  authoritative local transcript for a cold root prefill.
- **`true-cold durability`:** A checkpoint-durability oracle that verifies that a continuation
  restored from an on-disk checkpoint produces generated token IDs and UTF-8 bytes identical to a
  zero-reuse cold-process reference that prefills the full prompt from scratch (`request_id = 1`,
  `0` cached tokens).
- **`source_wait`:** Server-side time (in seconds, recorded in `requests.jsonl`) that a forked or
  resumed request spends waiting for its source state or an in-flight checkpoint export before
  prefill begins.

## Where the history lives

- [`CHANGELOG.md`](../CHANGELOG.md) — chronological product changes across releases.
- [`RELEASES.md`](RELEASES.md) — per-version component identities, acceptance summaries, and
  release cut procedures.
- [`releases/v0.16.0/NINFER_RELEASE_NOTES.md`](../releases/v0.16.0/NINFER_RELEASE_NOTES.md) (and
  prior `releases/<tag>/NINFER_RELEASE_NOTES.md`) — immutable per-release notes and limitations.
- Immutable tagged guides (`https://github.com/alphastorm/omp-ninfer/blob/<tag>/docs/QUICKSTART.md`,
  such as [`v0.10.0`](https://github.com/alphastorm/omp-ninfer/blob/v0.10.0/docs/QUICKSTART.md) and
  [`v0.7.2`](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)) — complete
  setup instructions for operators remaining on a prior release.

Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.
