# OMP NInfer — canonical facts

Updated: 2026-11-10 · Published release: v0.17.0 (2026-11-10) · stock Oh My Pi 18.18.6

Oh My Pi (coding-agent client) → OMP NInfer (qualified appliance and release layer) → NInfer
(inference engine) → Qwen3.8 27B (served model).

**Qualified on RTX 5090 · 4090 · 3090**, bound to the exact profiles in
[`releases/v0.17.0/manifest.json`](../releases/v0.17.0/manifest.json).
[Get started](QUICKSTART.md) ·
[Download v0.17.0](https://github.com/alphastorm/omp-ninfer/releases/tag/v0.17.0)

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

Published release **v0.17.0** (2026-11-10, GitHub `Latest`; superseding `v0.16.2`, 2026-11-04) pins
unmodified upstream Oh My Pi **18.18.6** (`9058ab9d229663e229e2867824ba6df6f21e9e59`, tree
`fd379b65368a20c7648d97f2c2b99cc03e019254`, release `439766193`;
[18.15.0→18.18.6 review](measurements/2026-11-10-omp-18186-client-upgrade-review.json)) and shared
published model container version 3 `81f924d4` (`qwen3_8_27b-v3.ninfer`, 20,437,521,664 bytes,
revision `1cbd84e7`), rebuilds the RTX 5090 container runtime to `v0.7.0-qwen38-5090-beta.6` from
frozen engine source `e0971faf` (`e0971faf221204047d5a4ed834e4e298740cee17` on upstream
`Neroued/ninfer` master `64d10fbf`, [fork PR #101](https://github.com/alphastorm/ninfer/pull/101),
image `7a19576b` on reused base `28857182`, server `dc86e101`, archive `d7f1ca4f` / 580,026,014 B,
SPDX `d9ea727c`, source archive `73749f93` / 12,820,073 B, kept strict-origin profile
`qwen38-5090-v0.13.0`, config `751d22dc`, isolated host checkpoint directory `checkpoints-v017`
mounted at `/checkpoints-v013`; bit-identical 664-artifact / 3-package same-path double build), and
carries the `v0.16.2` published native Windows RTX 4090 (`v0.8.0-qwen38-4090-beta.2`, package
`d9b10b47` / 991,981,865 B, server `ffee91bf`, SPDX `e4be92e4`, CycloneDX `a341bb61`, profile
`qwen38-4090-native-v0.8.0-beta.2`, public config `ae27dc44`, DFlash2 `K=7`, INT8 KV, `C1`,
`1,024`-token prefill chunk, `15,747.734375 MiB` / `16,512,696,320` B shared Host budget, `640 MiB`
headroom, 450 W owner baseline) and RTX 3090 (`v0.8.0-qwen38-3090-beta.2`, package `97a8e634` /
1,008,989,809 B, server `15a4db46`, SPDX `051a81e2`, CycloneDX `255874bf`, profile
`qwen38-3090-native-v0.8.0-beta.2`, public config `238ccad7`, DFlash2 `K=7`, INT8 KV, `C2` over one
shared 131,072-token pool, `180 s` pending timeout, `1,024`-token prefill chunk, `20,867.734375 MiB`
/ `21,881,405,440` B shared Host budget, `768 MiB` headroom, 350 W serving cap / 370 W restored)
packages unchanged at engine source `a87de361` (`a87de3613c17bced777b446fb545f872d8395ec1` on
`64d10fbf`). Release authority:
[`releases/v0.17.0/manifest.json`](../releases/v0.17.0/manifest.json) ·
[`releases/v0.17.0/NINFER_RELEASE_NOTES.md`](../releases/v0.17.0/NINFER_RELEASE_NOTES.md) ·
[`COMPATIBILITY.md`](COMPATIBILITY.md). Native `rk4v4` 4-bit KV (`262,144`-token context) remains
deferred to a follow-up release on the true-cold restore oracle (`EXP-107`).

The tagged [`releases/v0.17.0/NINFER_RELEASE_NOTES.md`](../releases/v0.17.0/NINFER_RELEASE_NOTES.md)
header and the `publication` block of
[`releases/v0.17.0/manifest.json`](../releases/v0.17.0/manifest.json) record the composition's
freeze-time state (qualified successor, fresh acceptance passed across all five documented routes
with RTX 3090's post-route native compaction campaign waived, product publication a separate gate)
and are immutable after the freeze, and the publication record is this section,
[`docs/RELEASES.md`](RELEASES.md), and the
[GitHub release](https://github.com/alphastorm/omp-ninfer/releases/tag/v0.17.0).

| Component or lane | Form and transport | Release tag and source | Image or package | Serving profile | Context | Requests in flight | Speculative backend | Modalities |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
| Oh My Pi client | Unmodified upstream release binaries: macOS arm64 (preview), Windows x64, Linux x64 (WSL2 live evidence) | `v18.18.6`, source `9058ab9d`, tree `fd379b65`, release `439766193` | `omp-darwin-arm64` (`ed2e63eb`, 221,867,152 B), `omp-windows-x64.exe` (`dfb15c27`, 249,985,024 B), `omp-linux-x64` (`a8059b95`, 286,021,808 B) in [`client-components.json`](../releases/v0.17.0/qualification/client-components.json) | Per-model `compat.statefulResponses: true`, explicit `tokenizer: qwen3` on opaque `q38-ninfer`, fail-closed config | 131,072 | `2` on RTX 5090 and native RTX 3090 (`C2` shared 131,072-token pool); `1` on native RTX 4090 (`C1`) | Target lane | Coding agent, typed tools, branches, compaction |
| RTX 5090 | Windows 11 + Docker Desktop/WSL2 container on loopback `127.0.0.1:18089`; local Windows client or macOS client over manual SSH tunnel (preview) | `v0.7.0-qwen38-5090-beta.6`, source `e0971faf` on `64d10fbf` | OCI image `7a19576b` (base `28857182`), server `dc86e101`, archive `d7f1ca4f` (580,026,014 B), SPDX `d9ea727c`, model `81f924d4` | `qwen38-5090-v0.13.0`, config `751d22dc`: BF16 KV (146,368 automatic KV tokens), shared Host budget 20,867.734375 MiB (21,881,405,440 B), 28,672 MiB host floor, 1,024-token prefill chunk, 60,000 ms keep-warm, mandatory `--session-checkpoint-require-origin-auth`, host `checkpoints-v017` mounted at `/checkpoints-v013` (schema 3); bit-identical 664-artifact / 3-package same-path double build | 131,072 | 2 (plus 2 extra device-state slots, 180 s pending timeout) | DFlash2 draft window 7 (`--lm-head-draft`) | Vision, text, typed tools, JSON-schema output, preserved thinking |
| RTX 4090 native Windows 11 | Native Windows package on loopback `127.0.0.1:18082`, UUID-bound GPU on a two-GPU host | Carried `v0.8.0-qwen38-4090-beta.2`, source `a87de361` on `64d10fbf` | Package `d9b10b47` (991,981,865 B), server `ffee91bf`, SPDX `e4be92e4`, CycloneDX `a341bb61`, model `81f924d4` | `qwen38-4090-native-v0.8.0-beta.2`, public config `ae27dc44`: INT8 KV, `Q4_G64_FP16` draft MLP + host-mapped token embedding, `Group64` A8 and FP32 head logits off, shared Host budget 15,747.734375 MiB (16,512,696,320 B), 640 MiB admission headroom, 32,768 MiB host floor, 1,024-token prefill chunk, 60,000 ms keep-warm, 450 W owner baseline, mandatory `--session-checkpoint-require-origin-auth`, `session-checkpoints-v3` (schema 3) | 131,072 | 1 (plus 2 extra device-state slots, 30 s pending timeout) | DFlash2 draft window 7 (`artifact-default` proposal) | Text, typed tools, JSON-schema output, preserved thinking (no vision) |
| RTX 3090 native Windows 11 | Native Windows package on loopback `127.0.0.1:18082`, UUID-bound GPU on the same two-GPU host | Carried `v0.8.0-qwen38-3090-beta.2`, source `a87de361` on `64d10fbf` | Package `97a8e634` (1,008,989,809 B), server `15a4db46`, SPDX `051a81e2`, CycloneDX `255874bf`, model `81f924d4` | `qwen38-3090-native-v0.8.0-beta.2`, public config `238ccad7`: INT8 KV, `Q4_G64_FP16` draft MLP + host-mapped token embedding, `Group64` A8 and FP32 head logits off, shared Host budget 20,867.734375 MiB (21,881,405,440 B), 768 MiB admission headroom, 1,024-token prefill chunk, 350 W serving power cap (370 W restored on stop), keep-warm off, mandatory `--session-checkpoint-require-origin-auth`, `session-checkpoints-v3` (schema 3) | 131,072 | 2 over one shared 131,072-token pool (plus 2 extra device-state slots, 180 s pending timeout) | DFlash2 draft window 7 (`artifact-default` proposal) | Text, typed tools, JSON-schema output, preserved thinking (no vision) |

- **Sequential native topology on one two-GPU host:** Both native Windows lanes install on the same
  two-GPU Windows 11 host (RTX 4090 at index 0, RTX 3090 at index 1), each bound to its own GPU
  UUID and PCI address. Only one native lane runs at a time on loopback port `127.0.0.1:18082`; within the
  active RTX 3090 lane, up to two requests run concurrently (`C2`) sharing one 131,072-token INT8
  KV pool. This is not multi-GPU inference and not simultaneous RTX 4090 and RTX 3090 serving.
- **Native upgrade, rollback to `v0.8.0-beta.1`, and checkpoint boundary:** With
  `Install-Release.ps1` in `v0.8.0-qwen38-{4090,3090}-beta.2` (including unreadable repair-census
  executable image refusal in `58a5b258`, [#63](https://github.com/alphastorm/ninfer/pull/63), and
  prior paused owner power restoration before uninstall in `f25ea97b`,
  [#65](https://github.com/alphastorm/ninfer/pull/65)), a running incumbent lane stops through its
  own controller across power-cap transitions and remains preserved as `previous_release` for
  `Control-Release.ps1 -Action Rollback` (**PASS 3/3 scenarios on both native lanes** from
  published `v0.8.0-qwen38-{4090,3090}-beta.1`: running-lane upgrade, forced first-`Start`
  rollback, and interrupted-install repair; RTX 3090 used the unmodified source harness while RTX
  4090 used a founder-approved private `Invoke-UpgradeRehearsal.ps1` copy changing only
  uncapped-power assertions `outer.qualified_power_limit_w == 0` and `Power() == owner_power_limit_w`,
  [`rtx4090-rehearsal-harness-decision.json`](../releases/v0.17.0/qualification/rtx4090-rehearsal-harness-decision.json)
  `f1fcd1bb`; GE-R1 binds each lane's distinct running/rollback/repair evidence-archive digest
  beside the lane-agnostic scenario summaries; each package's isolated 15-phase scratch
  qualification runs in a fresh scratch root with no predecessor and records
  `rollback: not_applicable`, `0` directions). Keep prior checkpoint roots untouched; replay
  authoritative OMP transcripts for a fresh prefill.
- **Admission, bounded resume/fresh rotation, durable pressure-work waits, and serving robustness:**
  Two requests run together on the RTX 5090 (`146,368`-token automatic BF16 KV pool) and on the
  native RTX 3090 (`131,072`-token shared INT8 KV pool) only while both prompts plus output
  reservations fit inside the shared pool; excess requests wait up to 180 s (`30 s` on `C1` RTX
  4090). Native RTX 4090 and RTX 3090 profiles set `--admission-headroom-mib` to 640 MiB and 768 MiB
  respectively. On RTX 5090 `beta.6` (`e0971faf`,
  [fork PR #101](https://github.com/alphastorm/ninfer/pull/101)), bounded resume/fresh admission
  rotates service across active sessions under context pressure and limits fresh-request admission
  windows to one attempt per complete rotation so resumed long sessions are not starved
  (upstream [#434](https://github.com/Neroued/ninfer/issues/434)); resident eviction and unit
  reservation wait for in-flight checkpoint saves and exports rather than skipping the youngest
  eviction candidate, pausing an older resident session, or failing the engine; malformed tool
  arguments no longer throw, enabled effort tiers normalize to the model artifact's chat template,
  contradictory thinking/effort fields are handled, numerical failures are isolated to the failing
  request, and graceful shutdown drains cancellation and final-save work before stopping the service
  (upstream
  [#440](https://github.com/Neroued/ninfer/issues/440)/[#441](https://github.com/Neroued/ninfer/issues/441)/[#446](https://github.com/alphastorm/ninfer/issues/446));
  and optional prefill pacing remains default off. Both RTX 5090 (`e0971faf`) and carried native
  `beta.2` (`a87de361`) include byte-proven durable-generation Host reclaim before export refusal
  ([fork #78](https://github.com/alphastorm/ninfer/issues/78),
  [#82](https://github.com/alphastorm/ninfer/pull/82) `aa9023f5`) and export-retirement reservation
  ([#68](https://github.com/alphastorm/ninfer/pull/68) `aaf6c2d0`) on top of `v0.16.0`'s counted
  Host `StateImage` materialization (`EXP-105`) and export-wait admission (`EXP-106`).
- **Schema 3 checkpoint stores and Windows durability:** All three lanes use schema 3
  checkpoints (fingerprint schema 2, status schema 2, request-log schema 30) with mandatory
  `--session-checkpoint-require-origin-auth` (requiring a configured checkpoint root and at least a
  32-byte API key; the documented generated key is 64 characters). In `v0.17.0`, the RTX 5090
  container mounts isolated host directory `checkpoints-v017` at `/checkpoints-v013` with
  non-blocking export, leaving predecessor `checkpoints-v013` and older `checkpoints` stores
  untouched for rollback; native lanes use
  `cache/<release-instance-id>/session-checkpoints-v3` under each immutable component release's
  own cache root (for example, `qwen38-4090-native-v0.8.0-beta.2-a87de3613c17` or
  `qwen38-3090-native-v0.8.0-beta.2-a87de3613c17`) with handle-anchored replacement, extended-length
  roots, and a current-parent publication fence (Windows `ntfs-write-through` is not POSIX `fsync`
  or a power-loss guarantee). Keep prior checkpoint roots untouched; prior sessions resume by
  replaying authoritative OMP transcripts for a fresh prefill.
- **Dual native SBOMs and deterministic RTX 5090 RDC build:** Each native outer asset set (10
  hashed entries plus `SHA256SUMS`, 11 files) ships both its SPDX 2.3 file inventory
  (`<package-stem>.spdx.json`) and a separate canonical CycloneDX 1.5 dependency inventory
  (`<package-stem>.cdx.json`). On RTX 5090 `beta.6` (`e0971faf`), a separate same-path double build
  matched **664 build artifacts and all 3 package outputs** bit for bit (`661` artifacts and `3`
  packages on `v0.16.2` `a87de361`, [#69](https://github.com/alphastorm/ninfer/pull/69)).
- **Fresh RTX 5090 qualification, carried native `beta.2` evidence, route acceptance, waiver, and G4 reviews:**
  On `e0971faf`, the exact-source RC ([`runtime-rc.json`](../releases/v0.17.0/qualification/runtime-rc.json)
  `bed3a245`) passed all `12/12` phases (`66` historical host, `54` current host including `35/35`
  EngineCore and Scheduler regressions, `11` dense real-model tests, `1` overlap test, restart,
  product-shape, exact-profile, and PRODUCT protocol phases), and the published-image lane receipt
  ([`rtx5090.json`](../releases/v0.17.0/qualification/rtx5090.json) `11fde294`) passed at **181.92
  tok/s** server / **180.40 tok/s** wall decode, **56.63 s** wall / **56.53 s** server cold exact
  130,048-token retrieval (**2,296.5 tok/s** wall), `agent_protocol` passed across Docker restart,
  `30,398 MiB` idle/final VRAM, and `0` transient retries. Both carried native `beta.2` components
  retain their `a87de361` 15-phase qualification receipts
  ([RTX 4090](../releases/v0.17.0/qualification/rtx4090.json) `254167f2`,
  [RTX 3090](../releases/v0.17.0/qualification/rtx3090.json) `b742870e`), zero-difference
  1,120-prompt powered quality screens (`20332928` / `f6e5a913`), fit proofs (`c1c3d0aa` /
  `b22956aa`), and no-regression ABBA speed receipts against published `beta.1`
  ([`native-speed-decision.json`](../releases/v0.17.0/qualification/native-speed-decision.json)
  `5c09de6a`: RTX 3090 weighted **1.0003** / min **0.9988**, **84/84** identical in
  [`rtx3090-speed.json`](../releases/v0.17.0/qualification/rtx3090-speed.json) `852e13ca`; RTX 4090
  weighted **0.9996** / min **0.9989**, **115/115** identical in
  [`rtx4090-speed.json`](../releases/v0.17.0/qualification/rtx4090-speed.json) `e48aba81`)
  byte-for-byte in [`receipt-audit.json`](../releases/v0.17.0/qualification/receipt-audit.json)
  (`c137388a`). On **2026-11-10**, frozen candidate `076bbe4f5abd68c8a0a1ba2efa0d08e881970e11`
  passed all five documented routes (host `2/2`, macOS `10/10`, Windows `5/5`, native `7/7` each;
  **31/31 blocks**), all three stock `18.18.6` clients, and RTX 4090 native public-install
  (`already_installed`, exact bytes, unchanged pointers), `C1` fleet probe, and independent
  restoration (**408.213 s** RTX 5090 accepted and all-attempt hold, **508.420 s** RTX 4090
  campaign; [documented routes](../releases/v0.17.0/acceptance/documented-routes.json),
  [composed acceptance](../releases/v0.17.0/acceptance/composed-external-installation.json),
  [RTX 4090 public install](../releases/v0.17.0/acceptance/rtx4090-public-install.json),
  [restoration](measurements/2026-11-10-v0170-acceptance-restoration.json)). On RTX 3090, after all
  seven documented route blocks, four-way `C2` fleet/fanout, and parallel stock OMP overlap at limit
  2 passed, the subsequent post-route `native-probes` automatic-compaction campaign failed
  (**1,727.696 s** elapsed; `compaction` probe timed out after `900 s` with `8` HTTP `503`
  `request_queue_timeout` responses, `2` HTTP `499` cancellations, `0` resident work; subsequent
  managed Stop `graceful_incomplete_shutdown` saved `2` / skipped `5` / refused `3`, reason
  `capacity`) and was waived by the founder with disclosure
  ([route waiver](../releases/v0.17.0/qualification/rtx3090-route-waiver.json) `19f2c0ef`); native
  behavior completion, structured-outage acceptance, a passing wrapper restoration audit, and
  anonymous public-install acceptance are not claimed, lead recovery via empty-session `Start` to
  ready then `Stop` (`graceful`, `0` refused, `370 W` restored, tasks `Ready`, `0` listeners,
  identical canonical cross-lane census `db1634a7`; evidence `fabb50de`) is bound separately, and
  RTX 3090 users should keep `v0.16.2` or restart the lane after long sessions until a native re-cut
  is qualified. The pre-release runtime, product-tooling, and waiver-support code reviews closed by
  disposition in [`review/runtime-ledger.json`](../releases/v0.17.0/review/runtime-ledger.json)
  (`5f8d6e4a`); deferred tooling items are tracked in
  [#149](https://github.com/alphastorm/omp-ninfer/issues/149).

## Models

v0.17.0 pins one shared registered NInfer conversion artifact (`qwen3_8_27b.ninfer`) from
[`neroued/Qwen3.8-27B-NInfer`](https://huggingface.co/neroued/Qwen3.8-27B-NInfer) across all three
lanes in [`releases/v0.17.0/manifest.json`](../releases/v0.17.0/manifest.json) (retaining the single
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
- **Oh My Pi client contract:** Stock Oh My Pi 18.18.6 has no `omp appliance` commands. Model
  fragments set `compat.statefulResponses: true`, `compat.includeEncryptedReasoning: false`, and
  `compat.supportsReasoningSummary: false` per model (upstream
  [#13686](https://github.com/can1357/oh-my-pi/pull/13686); obsolete operator
  `compat.thinkingLoopGuard` stays retired while `model.loopGuard` remains enabled with the
  1,024-character floor on short newline-spanning cycles), pin `tokenizer: qwen3` on the
  non-versioned `q38-ninfer` model alias in each `models.fragment.yml` (while canonical `qwen3.8-27b`
  entries infer `qwen3` from the model name), and declare explicit `[low, medium, xhigh]` effort
  lists (`high`→`medium`, `off`→`low`); `PI_OPENAI_STATEFUL` and
  `PI_NO_THINKING_LOOP_GUARD` must be absent from the environment. Custom
  Responses hosts default to `auto` image detail upstream
  ([#13687](https://github.com/can1357/oh-my-pi/pull/13687)), unavailable saved models fail closed
  ([#13689](https://github.com/can1357/oh-my-pi/pull/13689)), length-stopped compaction summaries
  fail visibly without committing partial context (a completed main summary survives a truncated
  display-only `<=512`-token summary), manual compaction waits for persistence replacement before
  queued background results start a turn, and shared Responses replay copies strip only
  `internal_chat_message_metadata_passthrough`.
  [`examples/manual-tunnel/fail-closed.yml`](../examples/manual-tunnel/fail-closed.yml) disables
  retries, model fallback (including pre-prompt missing-key fallback via explicit
  `retry.modelFallback: false`), automatic updates (`update.auto: false`,
  `startup.checkUpdate: false`), and `startup.setupWizard: false`, leaves async compaction at the
  OMP default (`19,660` reserve, strict `>111,412` trigger, `13,107` unset-reserve summary cap), and
  sets `providers.maxInFlightRequests` per provider ID (`ninfer-beta: 2`, `ninfer-main: 2`,
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
  pinned in [`releases/v0.17.0/manifest.json`](../releases/v0.17.0/manifest.json).
- **Single trusted owner:** Designed for one trusted operator on owner-controlled hardware, not
  multi-tenant isolation. Full threat model: [`SECURITY.md`](SECURITY.md).

## Measured proof

Per-lane runtime qualification receipts in v0.17.0 (never transfer one lane's numbers or
capabilities to another):

| Lane | Long-context retrieval (130,048 tokens) | Decode measurement | Speculative acceptance | Receipt |
| --- | --- | --- | --- | --- |
| RTX 5090 (`v0.7.0-qwen38-5090-beta.6`, DFlash2 K=7, BF16 KV, `C2`) | Exact in **56.63 s** cold (**2,296.5 tok/s** wall; **56.53 s** / `56.529 s` server) | **181.92 tok/s** server-side (**180.40 tok/s** wall) over 2,048 tokens | **0.244** DFlash2 acceptance, **2.71** tokens/round | [`rtx5090.json`](../releases/v0.17.0/qualification/rtx5090.json) (2026-11-10) |
| RTX 4090 native (`v0.8.0-qwen38-4090-beta.2`, DFlash2 K=7, INT8 KV, `C1`) | Exact in **83.54 s** (83.538 s) | **254.59 tok/s** C1 decode (4,541 prompt / 1,024 completion tokens); prefill **2,133.04 tok/s** | **83.88%** DFlash2 acceptance | [`rtx4090.json`](../releases/v0.17.0/qualification/rtx4090.json) (2026-11-03) |
| RTX 3090 native (`v0.8.0-qwen38-3090-beta.2`, DFlash2 K=7, INT8 KV, `C2` shared pool, 350 W cap) | Exact in **188.94 s** (188.941 s) | **148.70 tok/s** C1 decode (4,541 prompt / 1,024 completion tokens); prefill **978.72 tok/s** | **83.88%** DFlash2 acceptance | [`rtx3090.json`](../releases/v0.17.0/qualification/rtx3090.json) (2026-11-04) |

- **v0.17.0 (`e0971faf` on RTX 5090 `beta.6`, carried `a87de361` native `beta.2`) bounded resume/fresh admission, serving robustness, and stock OMP 18.18.6 route acceptance:**
  On frozen engine source `e0971faf` and shared model `81f924d4`, RTX 5090
  (`v0.7.0-qwen38-5090-beta.6`, server `dc86e101`, image `7a19576b`) matched **664 build artifacts
  and all 3 package outputs** bit for bit across a same-path double build, passed all `12/12`
  exact-source RC phases (`66/66` historical host, `54/54` current host including `35/35` EngineCore
  and Scheduler regressions, `11/11` dense real-model tests, `1/1` durable pressure overlap,
  four-boot schema 3 restart, product-shape, exact-profile, and PRODUCT protocol in
  [`runtime-rc.json`](../releases/v0.17.0/qualification/runtime-rc.json) `bed3a245`), and passed the
  published-image lane receipt ([`rtx5090.json`](../releases/v0.17.0/qualification/rtx5090.json)
  `11fde294`: **181.92 tok/s** server / **180.40 tok/s** wall decode, **56.63 s** wall / **56.53 s**
  server cold exact 130,048-token retrieval at **2,296.5 tok/s**, `agent_protocol` passed across
  Docker restart, `30,398 MiB` idle/final VRAM, `0` transient retries). Both carried `beta.2` native
  packages retain their `a87de361` qualification, quality, fit, and speed receipts byte-for-byte
  ([`receipt-audit.json`](../releases/v0.17.0/qualification/receipt-audit.json) `c137388a`), while
  fresh `2026-11-10` acceptance on candidate commit `076bbe4f` passed all five documented routes
  (`31/31` blocks), all three stock `18.18.6` clients, the **408.213 s** RTX 5090 hold, and RTX 4090
  native campaign (**508.420 s**), public-install, `C1` fleet-probe, and independent restoration
  checks; RTX 3090's post-route `native-probes` compaction campaign timed out after `900 s` and was
  waived in [`rtx3090-route-waiver.json`](../releases/v0.17.0/qualification/rtx3090-route-waiver.json)
  (`19f2c0ef`) alongside separate empty-session `Start`/`Stop` operator recovery (`fabb50de`).
- **v0.16.2 (`a87de361`) durable-export Host reclaim, deterministic RDC build, and native `beta.2` no-regression:**
  On frozen source `a87de361` and shared model `81f924d4`, RTX 5090 (`v0.7.0-qwen38-5090-beta.5`,
  server `cc99a460`, image `a0cbb8a5`) matched **661 build artifacts and all 3 package outputs** bit
  for bit across a same-path double build, passed `66/66` historical host, `11/11` dense, `1/1`
  durable pressure overlap, and `44` current host contract tests, and passed the published-image
  lane receipt ([`rtx5090.json`](../releases/v0.16.2/qualification/rtx5090.json) `bfd0ec1a`:
  **182.02 tok/s** server / **180.50 tok/s** wall decode, **56.49 s** wall / **56.38 s** server
  exact 130,048-token retrieval at **2,302.3 tok/s**, `agent_protocol` passed, `30,398 MiB` idle
  VRAM), with `88/88` agent-probe positions judged under the founder waiver on position 3
  `restore_0` (`0.481856409 s` vs `0.481568998 s` bound). Native RTX 4090 (`d9b10b47`, server
  `ffee91bf`) and RTX 3090 (`97a8e634`, server `15a4db46`) passed their 15-phase managed chains
  ([`rtx4090.json`](../releases/v0.16.2/qualification/rtx4090.json) `254167f2`: **254.59 tok/s**
  `C1` decode, **2,133.04 tok/s** prefill, **83.54 s** retrieval, **1,647 / 1,650** cached tokens
  across **42.52 s** restart; [`rtx3090.json`](../releases/v0.16.2/qualification/rtx3090.json)
  `b742870e`: **148.70 tok/s** `C1` decode, **978.72 tok/s** prefill, **188.94 s** retrieval,
  **1,647 / 1,650** cached tokens across **56.73 s** restart), fit proofs
  ([RTX 4090](../releases/v0.16.2/qualification/rtx4090-windows-native.fit.json) `b22956aa`,
  [RTX 3090](../releases/v0.16.2/qualification/rtx3090-windows-native.fit.json) `c1c3d0aa`),
  zero-difference 1,120-prompt powered quality screens (`80/80` determinism per arm;
  [RTX 4090](../releases/v0.16.2/qualification/rtx4090-windows-native.quality-screen.json) `f6e5a913`,
  [RTX 3090](../releases/v0.16.2/qualification/rtx3090-windows-native.quality-screen.json) `20332928`),
  `82/83` measured agent-probe parity positions per lane (waiving RTX 4090 `restore_1` cache gap
  `-52` vs `-48` and RTX 3090 position 1 `base` TTFT `0.4975294 s` vs `0.4644353 s` bound), `3/3`
  predecessor upgrade/rollback/repair rehearsals per lane, and the founder-approved **no-regression
  speed gates against published `beta.1`** (RTX 3090 weighted **1.0003** / min **0.9988**, **84/84**
  byte-identical in [`rtx3090-speed.json`](../releases/v0.16.2/qualification/rtx3090-speed.json)
  `852e13ca`; RTX 4090 weighted **0.9996** / min **0.9989**, **115/115** byte-identical in
  [`rtx4090-speed.json`](../releases/v0.16.2/qualification/rtx4090-speed.json) `e48aba81`).
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
  latest published release (`v0.17.0`) and its exact manifest and profiles.
- **No other GPUs or profiles:** Support does not extend outside the exact RTX 5090, RTX 4090, and
  RTX 3090 profiles bound by [`releases/v0.17.0/manifest.json`](../releases/v0.17.0/manifest.json).
- **Client platform limits:** macOS (`darwin-arm64`) is preview without managed client installation
  or appliance lifecycle; Linux (`linux-x64`) live evidence is under WSL2 only, not a separately
  qualified native Linux OS.
- **Native lanes are text and tools only:** Vision is qualified only on the RTX 5090 container
  lane; while DFlash2 (`K=7`) is qualified across all three lanes, native Windows RTX 4090 and
  RTX 3090 lanes serve text, typed tools, and JSON-schema structured output under DFlash2 `K=7` and
  refuse image inputs with `vision_disabled`.
- **Not multi-GPU inference or simultaneous two-lane native serving:** Only one UUID-bound native
  lane runs at a time on port `18082` (within the active RTX 3090 lane, `C2` serves up to two
  concurrent requests over one shared 131,072-token INT8 pool). Each native package's isolated
  15-phase scratch qualification runs in a fresh scratch root (`rollback: not_applicable`, zero
  directions), while upgrading an existing install preserves its actual predecessor as
  `previous_release` for `Control-Release.ps1 -Action Rollback` (keep prior checkpoint roots
  untouched and replay OMP transcripts for fresh sessions).
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
  masked-block pass for target verification. In `v0.16.0`–`v0.17.0`, `DFlash2` (`K=7`) is the qualified
  speculative backend across all three lanes (`qwen38-5090-v0.13.0` on the RTX 5090 container lane
  with `--lm-head-draft`, and `qwen38-4090-native-v0.8.0-beta.2` and
  `qwen38-3090-native-v0.8.0-beta.2` on the 24 GB native Windows lanes using `proposal:
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
  Windows lanes. All `v0.14.0`–`v0.17.0` native Windows packages compile it off (`A8 off`) after the
  RTX 4090 failed its preregistered 200-pair new-leak behavioral screen (five one-way changes) and
  the founder selected off conservatively across both cards.
- **`C1`:** Single-request (`concurrency: 1`) serving posture on the native Windows RTX 4090 lane
  (`qwen38-4090-native-v0.8.0-beta.2`), in contrast to two-request (`C2`) serving on the RTX 5090
  container lane (`qwen38-5090-v0.13.0`) and the native Windows RTX 3090 lane
  (`qwen38-3090-native-v0.8.0-beta.2`). As the serial `benchmark_c1` qualification gate (and
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
  config `751d22dc`, `qwen38-4090-native-v0.8.0-beta.2` config `ae27dc44`, and
  `qwen38-3090-native-v0.8.0-beta.2` config `238ccad7`) that enforces mandatory checkpoint origin
  authentication (`--session-checkpoint-require-origin-auth` / `require_origin_auth: true`). It
  requires a configured checkpoint root and a bearer API key of at least 32 bytes (64 characters as
  documented), keys each published checkpoint generation's `manifest.mac` HMAC from material
  derived from that bearer key, and refuses or quarantines unauthenticated or modified checkpoints
  at load.
- **`draft window`:** The number of candidate tokens (`K`, configured via `--draft-tokens` /
  `draft_tokens` and recorded in receipts as `speculative_draft_window` or `draft_window`) that the
  speculative drafter proposes in each decode round for the target model to verify in a single pass.
  In `v0.16.0`–`v0.17.0`, all three qualified lanes use a draft window of `7` under DFlash2 (`K=7`; native
  profiles used `3` under MTP3 through `v0.15.0`).
- **`schema 3 checkpoints`:** The current on-disk session-checkpoint format
  (`checkpoint_schema_version: 3`, paired with fingerprint schema 2, status schema 2, and
  request-log schema 30) stored under `/checkpoints-v013` (`checkpoints-v017` on the host in
  `v0.17.0`, `checkpoints-v013` in `v0.13.0`–`v0.16.2`) on the RTX 5090 container lane and
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
- [`releases/v0.17.0/NINFER_RELEASE_NOTES.md`](../releases/v0.17.0/NINFER_RELEASE_NOTES.md) (and
  prior `releases/<tag>/NINFER_RELEASE_NOTES.md`) — immutable per-release notes and limitations.
- Immutable tagged guides (`https://github.com/alphastorm/omp-ninfer/blob/<tag>/docs/QUICKSTART.md`,
  such as [`v0.10.0`](https://github.com/alphastorm/omp-ninfer/blob/v0.10.0/docs/QUICKSTART.md) and
  [`v0.7.2`](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)) — complete
  setup instructions for operators remaining on a prior release.

Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.
