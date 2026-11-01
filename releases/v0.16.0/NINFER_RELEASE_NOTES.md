# OMP NInfer v0.16.0 — native DFlash2 K7, RTX 3090 concurrency 2, and unified engine fixes

**Prepared composition: final hardware qualification, candidate route acceptance, and product-tooling four-seat critical-review council (`G4`, `review/runtime-ledger.json`) in progress; not published.**
This is not a published product release. All three runtime components in **v0.16.0**
build from one frozen engine release-candidate source `26fa28d0e7834515508fc07ac503164a6effc820`
(`26fa28d0`, referred to below as `N16`, tag `rebase/ckpt-native-n16` in `alphastorm/ninfer`) on
upstream `Neroued/ninfer` master `64d10fbf9f8e6bfc79ab0570b94674c5b9997929`: the native Windows
**RTX 3090** lane (`v0.8.0-qwen38-3090-beta.1`, profile `qwen38-3090-native-v0.8.0-beta.1`) moves
to **DFlash2 draft window 7 (`K=7`)** with **INT8 KV** and **concurrency 2 (`C2`)** over one shared
131,072-token pool, the native Windows **RTX 4090** lane (`v0.8.0-qwen38-4090-beta.1`, profile
`qwen38-4090-native-v0.8.0-beta.1`) moves to **DFlash2 `K=7`** with **INT8 KV** and **concurrency 1
(`C1`)** at 131,072 tokens, and the **RTX 5090** container lane (`v0.7.0-qwen38-5090-beta.4`)
rebuilds from the same source with runtime, checkpoint-export, `io_uring`, installer, and
observability fixes while retaining its `qwen38-5090-v0.13.0` serving profile (with only
`--binary-sha256` updated to the `N16` server `bab3fd77`). Stock Oh My Pi
**18.14.0** and the shared version 3 model artifact (`81f924d4`) carry unchanged from `v0.15.0`.
Because this release combines both native DFlash2 transitions, native `C2` on the RTX 3090, and the
three-lane engine rebuild, `v0.16.0` supersedes the `v0.15.1` patch previously referenced in the
`v0.15.0` release notes and roadmap.

The published product remains [v0.15.0](../v0.15.0/NINFER_RELEASE_NOTES.md); use its
[immutable installation guide](https://github.com/alphastorm/omp-ninfer/blob/v0.15.0/docs/QUICKSTART.md)
until publication. The [prepared guide](../../docs/QUICKSTART.md) is bound to frozen candidate
`⟦PENDING: v0.16.0 frozen product candidate commit SHA, releases/v0.16.0/acceptance/composed-external-installation.json⟧`;
it is not an installation recommendation before publication. Component publication, runtime
qualification, candidate-bound external installation, independent G4 review, and founder-owned
product publication are distinct gates; no predecessor hardware or client-route receipt is relabeled.
Owner-operated, exact-profile 0.x release; no SLA.

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Compatibility](COMPATIBILITY.md) · [Glossary](../../docs/FACTS.md#glossary)

Oh My Pi (coding-agent client) connects through OMP NInfer (qualified appliance and release layer)
to NInfer (inference engine) serving Qwen3.8 27B on one user-owned GPU.

## Composition — one engine source (`26fa28d0`) across all three lanes

| Component | Exact identity | Serving boundary |
| --- | --- | --- |
| Oh My Pi | Unmodified upstream `v18.14.0`, source `31147f9d1a76608549821c3759f8487b4d66c72d`, tree `9a63b5bfbb5971962c44fca660744b0d75dcd2c2` | Carried stock client (`omp-darwin-arm64` `60884395`, `omp-windows-x64.exe` `620a5935`, `omp-linux-x64` `e7dd2b60`); fresh three-platform and five-route acceptance `⟦PENDING: v0.16.0 three-platform and five-route acceptance status, releases/v0.16.0/acceptance/documented-routes.json⟧`; macOS remains preview |
| RTX 5090 container | `v0.7.0-qwen38-5090-beta.4` (`v0.7.0-qwen38-5090-runtime-beta.4`, `v0.7.0-qwen38-5090-source.4`); server `bab3fd77`, archive `f3a35cdb`, SPDX `b09ad9a7`, checksums `cca65f0d`, source archive `1ef87d52`, image `sha256:7a5a7bb88966512bcab2f711c1a7515bf0b8b834aaf0abd5456643493babb016` on base `d4377ed0` | Kept `qwen38-5090-v0.13.0` (config `751d22dc`, only `--binary-sha256` changed from `55f0b95a` to `bab3fd77`): BF16 KV (146,368 automatic tokens), 131,072 context, DFlash2 K7 (`--lm-head-draft`), two active requests (`C2`) + 2 extra device-state slots, 1,024-token prefill chunk, 180 s (`180000 ms`) pending timeout, 20,867.734375 MiB (`21,881,405,440` B) shared Host budget, 28,672 MiB host RAM floor, 60,000 ms keep-warm, `/checkpoints-v013` (`24,576 MiB` quota, `256 MiB` staging, mandatory `--session-checkpoint-require-origin-auth`), vision + tools + JSON-schema output + preserved thinking; checked-first-build reproducibility exception remains specific to this lane |
| RTX 4090 native Windows | `v0.8.0-qwen38-4090-beta.1`; package `06526bdb` (`991,969,490` B), server `c6f59e9e`, public config `f00cfac9`, release-spec `aab7a74d`, SPDX `825a8d30`, CycloneDX `b8c8efcb`, outer `SHA256SUMS` `bf1650eb` | Profile `qwen38-4090-native-v0.8.0-beta.1`: INT8 KV, DFlash2 K7 (`Q4_G64_FP16` draft MLP, host-mapped token embedding, `proposal: "artifact-default"`), one active request (`C1`) + 2 extra device-state slots, 131,072 context/KV, 1,024-token prefill chunk, 30 s (`30000 ms`) pending timeout, 15,747.734375 MiB (`16,512,696,320` B) shared Host budget, 640 MiB admission headroom, 32,768 MiB host RAM floor, `Group64` A8 and FP32 head logits off, 60,000 ms keep-warm, 450 W owner baseline, text + tools + JSON-schema output (no vision) |
| RTX 3090 native Windows | `v0.8.0-qwen38-3090-beta.1`; package `040d5923` (`1,008,976,979` B), server `72cd776b`, public config `cbe67aae`, release-spec `7d2406a3`, SPDX `6f78e190`, CycloneDX `3b217f69`, outer `SHA256SUMS` `0fd18a35` | Profile `qwen38-3090-native-v0.8.0-beta.1`: INT8 KV, DFlash2 K7 (`Q4_G64_FP16` draft MLP, host-mapped token embedding, `proposal: "artifact-default"`), two active requests (`C2`) over one shared 131,072-token KV pool + 2 extra device-state slots, 1,024-token prefill chunk, 180 s (`180000 ms`) pending timeout, 20,867.734375 MiB (`21,881,405,440` B) shared Host budget, 768 MiB admission headroom, `Group64` A8 and FP32 head logits off, keep-warm off, 350 W serving cap (370 W restored on stop), text + tools + JSON-schema output (no vision) |

All three runtime lanes bind frozen source `26fa28d0e7834515508fc07ac503164a6effc820` on upstream
`Neroued/ninfer` master `64d10fbf9f8e6bfc79ab0570b94674c5b9997929` (short 8-hex identifiers are
SHA-256 prefixes for artifacts/configs or Git commit prefixes in `alphastorm/ninfer` unless
otherwise noted). The model remains the published
container version 3 artifact `81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da`
(`20,437,521,664` bytes, revision `1cbd84e7221e51186bd7f093a149912d2489625b`, downloaded to
`qwen3_8_27b-v3.ninfer`). Native packages use CUDA 13.3 (`nvcc 13.3.73`, `sm_89`/`sm_86`) and MSVC
`14.44.35207` (`cl 19.44.35229`); the RTX 5090 container uses CUDA 13.1 (`nvcc 13.1.115`, `sm_120a`)
and GCC `13.3`.

## What changes in v0.16.0

- **Native DFlash2 K=7 on RTX 3090 and RTX 4090:** Both native Windows lanes retain 8-bit `INT8` KV
  (`33,792` bytes/token) and a 131,072-token context ceiling while switching their speculative
  decoding backend from MTP3 (`K=3`, `proposal: "lm-head-draft"` / `lm_head_draft: true`) to
  DFlash2 draft window 7 (`K=7`, using the model artifact's bundled 5-layer block drafter with
  `proposal: "artifact-default"` in `release-spec.json` and no `lm_head_draft` override in
  `server-config.json`; the kept RTX 5090 CLI profile continues to pass `--spec dflash2
  --draft-tokens 7 --lm-head-draft`). To fit 24 GB cards with the required admission headroom
  (`768 MiB` on RTX 3090, `640 MiB` on RTX 4090), both native profiles use the `sm_86`/`sm_89`
  load-time fit seam: `Q4_G64_FP16` conversion of the draft MLP `gate`/`up` weights (`473,497,600`
  converted device bytes) and host-mapped `token_embedding` (`1,350,860,800` host-mapped bytes).
  Each native DFlash2 `StateImage` is `195,897,344` bytes (`40 MiB` larger than MTP3's
  `153,954,304`-byte image because it carries the local cyclic draft KV ring). On RTX 4090
  (`qwen38-4090-native-v0.8.0-beta.1`), the prefill chunk changes from `2,048` to `1,024`
  tokens, the shared Host budget updates from `15,506,063,360` bytes (`14787.734375 MiB`) to
  `16,512,696,320` bytes (`15747.734375 MiB`, retaining `11,264 MiB` of Host KV plus 24 DFlash2
  state images and the `32,768 MiB` host RAM floor), and concurrency stays at one active request
  (`C1`, 30 s pending timeout, two extra / three total device-state slots).
- **RTX 3090 concurrency 2 over one shared 131,072-token pool (`qwen38-3090-native-v0.8.0-beta.1`):**
  The RTX 3090 native profile advances from one active request (`C1`, 30 s pending
  timeout, four extra device-state slots, `12,284,837,888`-byte / `11715.734375 MiB` shared Host
  budget) to two active requests (`C2`, `engine.max_concurrency: 2`, `180,000 ms` pending timeout,
  two extra / four total device-state slots) sharing one 131,072-token `INT8` KV pool, and raises
  its Host KV portion from `8,192` to `16,384 MiB` plus 24 DFlash2 state images for a
  `21,881,405,440`-byte (`20867.734375 MiB`) shared Host budget (matching the `20867.734375 MiB`
  Host budget already used by `qwen38-5090-v0.13.0` on the RTX 5090). In
  [`examples/manual-tunnel/fail-closed.yml`](../../examples/manual-tunnel/fail-closed.yml),
  `providers.maxInFlightRequests.ninfer-native-3090` changes from `1` to `2` (`ninfer-native-4090`
  and `ninfer-heavy` stay `1`). Only one native lane runs at a time on shared loopback port `18082`;
  `C2` means two concurrent requests sharing one 131,072-token KV pool inside the active RTX 3090
  lane, not two independent full-size KV pools or simultaneous RTX 4090 and RTX 3090 serving.
- **First-fork export-State residency (`8c639fe0` / `80c0af77`, EXP-105):** Previously, an
  off-worker durable checkpoint export held `ReadLease` pins on device `StateImage` slots throughout
  disk serialization, blocking the first post-export or post-resume fork until the write retired.
  `StateImageStore::prepare_host_export` now materializes immutable state images into the counted
  Host arena and releases device state replicas before off-worker disk serialization begins. On the
  RTX 5090 (`08257eec`), post-resume first-fork server time to first token (TTFT) dropped from
  **5.03 s** (`5.026 s` with `4.850 s` `source_wait` on `c3911a14`; `4.903 s` / `4.738 s` on
  `31583e3f`) to **0.11 s** (`0.106 s` TTFT, `0.005 s` `source_wait`). On the RTX 3090 (`08257eec`),
  first-fork server TTFT dropped from **15.4–17.8 s** (`14.86–17.22 s` `source_wait`) to
  **0.33–0.76 s** (`source_wait <= 0.033 s`).
- **Shared-pool export-pin liveness and startup headroom (`ea2edc20`, `375f47c9`, EXP-106):**
  `EngineCore::reserve_resident_units()` now waits when `checkpoints_.pending()` or
  `checkpoint_exports_in_flight_ != 0` can release pinned device KV pages instead of failing a
  resumed concurrent resident with HTTP 500 `oldest resident cannot obtain its legal unit`.
  `StartupMemoryBudget::fits()` now enforces both physical free memory and configured-budget
  headroom after CUDA graph initialization so startup replans or refuses rather than spending the
  declared reserve.
- **Checkpoint-owner, delivery-ordering, and `io_uring` lifetime fixes (`c3911a14`, `e517dab8`,
  `40a1b2d0`):**
  - *Checkpoint owner replacement (`c3911a14` and `alphastorm/ninfer#49` `e517dab8`):* Fixes the
    `Native could not release an unreferenced checkpoint owner` failure on fork-after-resume that
    deferred native RTX 3090 DFlash2 out of `v0.15.0`, retains binding waiters on failed state
    adoption, orders error and cancellation response delivery after engine-state retirement
    ([#95](https://github.com/alphastorm/omp-ninfer/issues/95)), and adds media-decode range checks
    ([#96](https://github.com/alphastorm/omp-ninfer/issues/96)).
  - *Linux `io_uring` owned completion buffers and teardown barrier (`40a1b2d0`,
    [#116](https://github.com/alphastorm/omp-ninfer/issues/116) handle-allocation and ring-teardown
    lifetime items `GA-R2` / `GA-U1`; reaches the Linux RTX 5090 container lane, not Windows native
    execution):* Allocates the completion handle before publishing a checkpoint read batch to the
    worker so a failed allocation cannot leave a worker writing retired caller buffers, and on fatal
    ring reset retracts unconsumed submission queue entries (SQEs), issues `IORING_OP_ASYNC_CANCEL`
    per outstanding request, and drains both cancellation and original completion queue entries
    (CQEs) — aborting fail-closed on a 30 s deadline if retirement cannot be proved — before
    releasing memory.
- **Native Windows installer and controller recovery (`577fecba`, `alphastorm/ninfer#48` `9cb741dc`,
  [#116](https://github.com/alphastorm/omp-ninfer/issues/116)):** Hands off the GPU-owner lease
  across running-lane upgrades and rollbacks (including power-cap transitions, closing
  [#94](https://github.com/alphastorm/omp-ninfer/issues/94) and removing the historical stop-first
  prerequisite), journals directory-creation cleanup intent before `mkdir`, refuses a non-running
  incumbent's retained inner GPU lease before cutover, publishes pre-spawn launch attribution with a
  process-image census guard before GPU-owner restoration, and blocks destructive transaction
  rollback when a launch-bound shutdown report is explicitly incomplete or records refused saves.
- **Per-position speculative decoding metrics (`f6668a5d`, request-log schema 30):** Prometheus
  `/metrics` exposes `ninfer_spec_decode_position_tokens_total{position,kind}` (`attempted` and
  `accepted` across zero-based draft positions, with startup warmup subtracted), and `requests.jsonl`
  emits additive optional `request_done.speculative.attempted_per_position` while retaining
  request-log schema `30`.
- **Product tooling and residual closures (`3de36942`, `fa96e486`, `a376ffd7`,
  [#117](https://github.com/alphastorm/omp-ninfer/issues/117)):** `scripts/verify_release.py`,
  `scripts/bind_native_variant.py`, `scripts/compose_native_qualification.py`, and
  `scripts/compose_route_acceptance.py` consume authenticated packaged native policy
  (`release-spec.json` schema 5 and `server-config.json` schema 4), keep serial speed-gate campaigns
  at `C1` while adding a separate `C2` acceptance arm (`concurrency_probe.py --scenario fanout
  --fanout-concurrency 4`, stock OMP subagent/session overlap at limit 2, and two
  automatic-compaction/control-recall epochs), and close all 13 `v0.15.0` product-council residual
  items in [#117](https://github.com/alphastorm/omp-ninfer/issues/117) (`P15-R01`..`P15-R13` in
  [`CHANGELOG.md`](../../CHANGELOG.md)), including predecessor-variant binding for native quality
  screens, exact 1,120-screen / 80-determinism prompt membership seals, mandatory G4 ledger binding
  in ready mode, recursive `repository_path`/`sha256` verification, and normalized public `.cast`
  files plus re-rendered GIF/MP4/poster demo assets (`3,676` OCR-inspected frames with zero
  private-path markers).

## Stock Oh My Pi 18.14.0 retained; 18.14.1 and 18.14.2 not adopted

`v0.16.0` retains the unmodified upstream Oh My Pi **18.14.0** binaries (`31147f9d`, tree
`9a63b5bf`, rebuilt with Bun 1.4.4 for CVE-2026-91403 and CVE-2026-111497) pinned in
[client-components.json](qualification/client-components.json). Upstream `v18.14.1` and `v18.14.2`
(`7efd7721`, published 2026-10-31) are deliberately not adopted in this runtime release:

- **Unchanged wire and compatibility contract:** Across the 394 commits in `v18.14.0...v18.14.2`,
  zero commits touched `packages/ai/src/providers/openai-responses.ts`,
  `packages/ai/src/providers/openai-responses-state.ts`, the `models.yml` schema bundle,
  `authHeader`, `compat.statefulResponses`, `compat.includeEncryptedReasoning`,
  `compat.supportsReasoningSummary`, or transport retry policy.
- **No security advisory:** Neither `18.14.1` nor `18.14.2` contains a security fix; the bundled
  Bun 1.4.4 CVE fixes already shipped in `18.14.0`.
- **Deferred behavior changes:** `18.14.2` moves `thinking-loop-guard` to a catalog axis (`exact`
  for Qwen with a 1,024-character floor on line-spanning cycles, removing `compat.thinkingLoopGuard`)
  and rejects local compaction summaries that end with `stopReason: "length"`. Neither addresses an
  observed defect on the qualified NInfer routes; adopting a new client binary will follow as a
  separate client-patch candidate (`v0.16.1`, targeting `18.14.2` rather than `18.14.1` alone).

## v0.16.0 experiment ledger and deferred or rejected candidates

Full narrative and historical context are in [`docs/PERFORMANCE.md`](../../docs/PERFORMANCE.md#experiment-ledger)
and [`ROADMAP.md`](../../ROADMAP.md#deferred-and-rejected-decisions).

| Entry | Recorded result | Release boundary |
| --- | --- | --- |
| EXP-101 — RTX 3090 DFlash2 K7 powered quality screen | Preregistered 1,120-prompt screen and 80-prompt fresh-cache determinism run on `v0.8.0-qwen38-3090-beta.1` (`26fa28d0`, package `040d5923`, server `72cd776b`, config `cbe67aae`, 350 W, port 18082, 50-prompt shards at 1 request) vs the sealed `v0.14.0` MTP3 production arm (`fedce425` / `d08d262b`, state `9a9213cf`): `PASS: 1,120 prompts; both arms 80/80 deterministic with 0 missing/error samples; 771/1,120 paired content/reasoning outputs changed. All 9 primary bounds passed: recall lower -0.0073 and precision lower -0.0070 (margin -0.02); unsupported upper 0.0089 (0.03); schema/tool-selection/tool-argument lower 0 (each -0.02); duplicate upper 0.0059 (0.02); redaction lower -0.0119 (-0.05); secret-leak ratio upper 1.0673 (1.10), counts 545 to 561, not zero`. | Governing quality gate for the shipping RTX 3090 DFlash2 K7 `C2` package. |
| EXP-102 — RTX 4090 DFlash2 K7 powered quality screen | Preregistered 1,120-prompt screen and 80-prompt fresh-cache determinism run on `v0.8.0-qwen38-4090-beta.1` (`26fa28d0`, package `06526bdb`, server `c6f59e9e`, config `f00cfac9`, 450 W, port 18082, 50-prompt shards) vs the sealed `v0.14.0` MTP3 production arm (`5caa7780` / `b5cfbf50`, 25 sealed holds, state `cc48a776`): `PASS: 1,120 prompts; both arms 80/80 deterministic, 0 missing/error samples; 777/1,120 paired content/reasoning outputs changed. All 9 primary bounds passed: recall lower -0.0082 and precision lower -0.0093 (margin -0.02); unsupported upper 0.0045 (0.03); schema/tool-selection/tool-argument lower 0 (each -0.02); duplicate upper 0.0046 (0.02); redaction lower -0.0139 (-0.05); secret-leak ratio upper 1.0985 (1.10), counts 533 to 561, not zero`. | Governing quality gate for the shipping RTX 4090 DFlash2 K7 `C1` package. |
| EXP-103 — RTX 4090 `K=6`/`K=5` draft windows and `K=7` 131K INT8 fit | On `v0.14.0` binary `5caa7780`, config-only `K=6` (`0.8625–0.8642` cross ratios, median `0.8633`) and `K=5` (`0.8668–0.8673`, median `0.8671`) failed the `>= 0.95` floor on depth-0 case `log-024@0` vs MTP3. `DFlash2 K=7` 131,072-token INT8 `C1` fit passed (`1,449,132,032` B available >= `671,088,640` B floor, `22,265.0 MiB` peak, 32-token / 114-byte true-cold continuation `07b8db1f`). | `K=6` and `K=5` rejected; RTX 4090 uses `K=7`. |
| EXP-104 — Opt-in FP32 head logits (`--fp32-head-logits`) and RTX 4090 floor | `--fp32-head-logits` (`+8,442,880` persistent bytes at `K=7`/`C=2`) passed `2/2` numerical tests on `sm_86`/`sm_89` (`83` FP32 reductions, max rel L2 `0.001722`), but `fp32_head_logits: true` failed `log-024@0` on `31583e3f` at `0.9016–0.9025` (median `0.9021`). With `--fp32-head-logits` off (the default), `DFlash2 K=7` passed `log-024@0` at `0.9627–0.9635` (`31583e3f`) and `0.96186–0.96294` (`08257eec`); in the final `26fa28d0` shipping-package (`06526bdb`) 115-case ABBA speed gate at 131,072-token INT8 KV (`+2` extra slots), the 108-case role corpus (`role108`) reached **×1.2736** (`139.87 → 178.13 tok/s`, all 115 cases **×1.2741**) while `log-024@0` measured **0.934** (`139.41 → 130.19 tok/s`) and was waived by the founder with disclosure. | `--fp32-head-logits` rejected for shipping profiles and stays opt-in and off (`false`); default `DFlash2 K=7` adopted on RTX 4090. |
| EXP-105 — Export-State residency (`prepare_host_export`) | Materializing immutable device `StateImage` replicas to Host before off-worker disk serialization cut first-fork `source_wait` on RTX 3090 (`08257eec`) from `14.86–17.22 s` (`15.4–17.8 s` TTFT) to `<= 0.033 s` (`0.33–0.76 s` TTFT) and on RTX 5090 (`08257eec`) from `4.85 s` (`5.03 s` TTFT) to `0.005 s` (`0.106 s` TTFT). | Shipped in `26fa28d0` across all three lanes. |
| EXP-106 — Native `C2` on RTX 3090 and RTX 4090 `C2` refusal | Waiting for in-flight exports in `reserve_resident_units()` (`ea2edc20`) resolved the `oldest resident cannot obtain its legal unit` HTTP 500. On RTX 3090 (`08257eec`), `INT8` `C2` over one shared 131,072-token pool passed startup (`1,110,441,984` B available, `22,584 MiB` peak), two-session `59,866`-token true-cold durability, calibrated `59,879 + 59,879`-token concurrent runs (`18/18` HTTP 200 across 3 trials), and paired 2,048-token decode (**1.385×** median aggregate `57.68 → 79.90 tok/s`, **0.722×** pair wall `71.01 → 51.26 s`; concurrent per-request `0.698× / 0.735×` of `C1`). RTX 4090 `INT8` `C2` at 131,072 tokens refused startup admission. | RTX 3090 ships `C2` (`qwen38-3090-native-v0.8.0-beta.1`); RTX 4090 stays `C1` (`qwen38-4090-native-v0.8.0-beta.1`). |
| EXP-107 — Native `rk4v4` 4-bit KV (`262,144`-token context) | Ported head-dimension-256 (`D256`) `rk4v4` (`17,920` B/token, `47.0%` smaller than `INT8`) passed `7/7` FP64 op/graph/store executables (max rel L2 `0.007773`) and held-out perplexity on `sm_86`/`sm_89` (`ΔNLL = 0.00345 <= 0.02`), and on RTX 3090 fit `262,144`-token `C1` (`1,097,859,072` B available; exact 130,048/250,062-token retrieval in `197.86 / 503.57 s`), `245,760` `C2`, and `229,376` `C2`. However, true-cold restore failed on all three RTX 3090 tuples (token 32 on `262,144` `C1`, cold `48117` vs restored `3635`; tokens 16–32 on session 1 of `245,760`/`229,376` `C2`). RTX 4090 refused `262,144` `C1` and `245,760` `C2` at startup. | Deferred to a follow-up release; `--kv-dtype rk4v4` stays off and unqualified in all shipped profiles. |

## Native Windows qualification at `26fa28d0`

Both `v0.8.0-qwen38-4090-beta.1` (`06526bdb`) and `v0.8.0-qwen38-3090-beta.1` (`040d5923`) are
built from frozen commit `26fa28d0e7834515508fc07ac503164a6effc820` with separate closed 11-file
outer distribution sets (10 checksummed entries plus `SHA256SUMS`), packaged schema 5
`release-spec.json` and schema 4 `server-config.json` files, SPDX 2.3 file inventories, and
canonical CycloneDX 1.5 dependency inventories (12 resolved vcpkg packages with 13 DLL associations,
CUDA 13.3 runtime, vendored sources, MSVC CRT, and DirectStorage redistributables). In two clean
compile rounds per architecture on the Windows 11 build host, **all 43/43 EXE/DLL binaries matched
raw bytes** (17 EXEs and 26 DLLs per architecture), raw-runtime and package private-marker scans
reported 0 findings, and component cut preflight exited 0. Each outer distribution's immutable
`package-build-receipt.json` (`b0f94a57` on RTX 4090, `9e194b8f` on RTX 3090) retains its pre-hardware
`hardware-pending` status; subsequent hardware qualification receipts are distinct and copied
unchanged.

### Pre-cut and shipping-package native gates

| Gate at `26fa28d0` | RTX 4090 (`v0.8.0-qwen38-4090-beta.1`, `C1`) | RTX 3090 (`v0.8.0-qwen38-3090-beta.1`, `C2`) |
| --- | --- | --- |
| Deterministic 2-round build & scans | **43/43 EXE/DLL byte-identical**; 0 private markers | **43/43 EXE/DLL byte-identical**; 0 private markers |
| Shipping-package 131,072-token INT8 fit & true-cold durability | **PASS** (`1,056,964,608` B available >= `671,088,640` B / `640 MiB` floor; `22,639 MiB` peak, `1,504 MiB` min free; `473,497,600` B converted device + `1,350,860,800` B host-mapped weights; cold `3,093` vs restored `3,066+27` **32/32 token IDs & UTF-8 bytes identical**; exact 130,048-token retrieval) | `PASS: 131,072-token INT8 C2, 1,110,441,984 B (1,059 MiB) available after startup >= 805,306,368 B (768 MiB); 22,584 MiB peak / 1,742 MiB min free. Two 59,866-token true-cold sessions restored at 59,840 cached + 26 computed tokens with 32/32 generated token IDs and UTF-8 bytes identical; converted device / host-mapped weights 473,497,600 / 1,350,860,800 B` |
| Role-corpus ABBA speed gate vs `v0.14.0` MTP3 | **PASS with founder waiver on `log-024@0`**: 108-case role corpus (`role108`: `84` cases at `0` cached tokens + `12` at `32,000` + `12` at `64,000`) weighted **×1.2736** (`139.87 → 178.13 tok/s`), all `115` cases (`108` role + `7` code/reasoning supplementals) weighted **×1.2741** (`138.94 → 177.02 tok/s`), `7` supplementals weighted **×1.2778** (`131.68 → 168.26 tok/s`, min **×1.0804** on `reasoning-invariant`); `114/115` cases clear the `>= 0.95` per-case decode ratio floor (lowest passing case `1.0128×`), while depth-0 case `log-024@0` measured **0.934** (`139.41 → 130.19 tok/s`, `0.933832×`) below `0.95` and was **waived by the founder with disclosure**; retained content/reasoning/tool-call UTF-8 output bytes are **115/115** identical across within-engine repeats (`A0=A3`, `B1=B2`) and **43/115** identical across engines (`31/84` at depth 0, `7/12` at 32K, `5/12` at 64K, `0/7` supplemental) | `PASS: 84 depth-0 ABBA cases at 350 W; weighted 1.2683598277 (79.37 to 100.67 tok/s), minimum 0.9764424319 >= 0.95, no waived case; both within-engine repeats 84/84 identical, cross-engine 36/84 identical` |
| Powered 1,120-prompt quality screen (EXP-102 / EXP-101) | `PASS: 1,120 prompts; both arms 80/80 deterministic, 0 missing/error samples; 777/1,120 paired content/reasoning outputs changed. All 9 primary bounds passed: recall lower -0.0082 and precision lower -0.0093 (margin -0.02); unsupported upper 0.0045 (0.03); schema/tool-selection/tool-argument lower 0 (each -0.02); duplicate upper 0.0046 (0.02); redaction lower -0.0139 (-0.05); secret-leak ratio upper 1.0985 (1.10), counts 533 to 561, not zero` | `PASS: 1,120 prompts; both arms 80/80 deterministic with 0 missing/error samples; 771/1,120 paired content/reasoning outputs changed. All 9 primary bounds passed: recall lower -0.0073 and precision lower -0.0070 (margin -0.02); unsupported upper 0.0089 (0.03); schema/tool-selection/tool-argument lower 0 (each -0.02); duplicate upper 0.0059 (0.02); redaction lower -0.0119 (-0.05); secret-leak ratio upper 1.0673 (1.10), counts 545 to 561, not zero` |
| Agent-probe parity vs `v0.14.0` (`p16-agent-parity/1` / `/2`: all probe oracles pass with 0 errors/timeouts, per-position `cached - prompt` >= incumbent, fork/resume server TTFT <= incumbent + `max(0.25 s, 25%)`) | **PASS 83/83 positions** (`warm_arrival` 12/12 both orders, `agent_mix` 51/51, `sibling_continue` 5/5, two-restart `restore` 4/4, `fleet_probe` `fanout` 11/11 across two 4-branch fanout rounds; min `(cached - prompt)` delta `0`, min TTFT bound margin `0.219 s`, max `source_wait` `<= 0.0178 s`) | `PASS: 83/83 positions (arrival 12, mix 51, sibling 5, two-restart restore 4, fleet 11) under p16-agent-parity/2, cache-gap deltas 0. Fanout-concurrency 4: 5/5 HTTP 200; calibrated 2 x 59,879-token test: 18/18 HTTP 200 across 3 trials; 0 HTTP 500` |
| Upgrade, rollback, and repair rehearsal from `v0.14.0` `v0.7.0-qwen38-{4090,3090}-beta.3` | `⟦PENDING: N16 FINAL RTX 4090 upgrade rehearsal from v0.7.0-qwen38-4090-beta.3 (running-lane upgrade, forced post-activation first-Start failure with rollback, interrupted install then repair and same-instance reinstall), window/final-4090/⟧` | `PASS: 1c running-lane upgrade, 2c forced post-activation first-Start failure with rollback, 3c interrupted install/repair/same-instance reinstall from true v0.14.0 beta.3; all 3 scenarios passed once, candidate transaction-created targets removed, canonical states unchanged, 370 W restored; no product-route acceptance is inferred` |

### Managed 15-phase native qualification

Each native package runs the 15-phase hardware qualification chain (`tools/qualification/qualify_native.py` in `alphastorm/ninfer`: (1) `preflight`, (2) `neutral_build`, (3) `private_path_scan`, (4) `package`, (5) `transfer_install`, (6) normal `protocol` and (7) pool-pressure `pressure_protocol` authenticated schema 2 smokes, (8) `context_128k` exact 130,048-token retrieval, (9) `restart` explicit-save and graceful-stop process restart, (10) `rollback`, (11) `security` state-root ACL regression, (12) `omp` stock client end-to-end turn, (13) `benchmark_c1` at the qualified power cap, (14) `receipt` binding, and (15) `restore` owner power restoration); the table below summarizes the primary measured phase outputs in `rtx4090.json` (`69ebf60c`, qualified `2026-10-31T21:22:21Z`) and `rtx3090.json`:

| Managed scratch qualification at `26fa28d0` | RTX 4090 (`rtx4090.json`) | RTX 3090 (`rtx3090.json`) |
| --- | ---: | ---: |
| C1 decode, 4,541 prompt / 1,024 completion tokens (DFlash2 K7) | **254.27 tok/s** (`83.88%` DFlash2 acceptance, `6.21 s` wall, `22,639 MiB` peak) | `148.43 tok/s; 83.88% DFlash2 acceptance` |
| C1 prefill | **2,139.14 tok/s** | `974.15 tok/s` |
| Exact 130,048-token retrieval | **83.35 s** (`83.352 s`, exact `ORCHID=493817; COLOR=COBALT`) | `188.99 s` |
| Explicit save / graceful-stop cached tokens | **1,647 / 1,650** (`643,966,448` B save; `6.315 s` stop-event flush) | `1,647 / 1,650 tokens` |
| Process restart | **42.21 s** (`42.213 s`, `10` files / `643,998,587` B) | `46.88 s` |
| Normal / pressure schema 2 protocol & state security | **passed / passed** (`12,758.578125 MiB` pressure Host; `910 ms` populated-root status, DACL protected) | `PASS: schema-2 product protocol in both arms and schema-2 state_security` |
| Rollback directions & owner power restored | **`not_applicable` (`0` directions, isolated scratch lineage) / 450 W** (`0` processes, lease inactive, task `Ready`) | `not_applicable, 0 directions (first scratch lineage); 370 W restored` |

Public native packages retain port `18082`; installed scratch qualification equivalents change only
`listen.port` (`18210` and pressure `18200` on RTX 4090, yielding scratch config `418687a4` and
scratch package `1f23e5d2`; `18211` and pressure `18201` on RTX 3090) and do not execute or
activate the canonical public route. On RTX
4090, two pre-GPU setup attempts were infrastructure-invalid (the initial CPU hold lacked a private
host-lock environment marker before any phase ran, and the initial package step omitted the
referenced `installed/` license/SPDX input tree) and each was corrected once in a fresh output root
without repeating any passed phase or GPU workload. The isolated 15-phase chain installs into a
fresh scratch root with no predecessor (`rollback: not_applicable`, `0` directions), so predecessor
upgrade/rollback against `v0.7.0-beta.3` is proven separately by the upgrade rehearsal and
public-install promotion gates. Both `v0.8.0-beta.1` native packages bind their packaged
`release-spec.json` and `server-config.json` in `releases/v0.16.0/profiles/rtx{4090,3090}/`.

## RTX 5090 exact bytes, reproducibility exception, and lane gates

Server `bab3fd77e8b5cafb792d0e4648e5e2b0d935105557a0b08fb2541799a25ffce7` (`bab3fd77`,
`326,828,656` B), binary archive
`f3a35cdb7859a576fa2ff7b474dfbd7ce5db37c7c756094cfd736d47fd284de0` (`579,765,099` B), SPDX
`b09ad9a7d06607f25600349f9e3aec751aaa5fe7387d9a756270abbcda47f7d7` (`3,596` B), checksums
`cca65f0d3d3b3f0da14ebce077dbc7e31a2402059c86e6f5e86238a2304eada6` (`251` B), and source archive
`1ef87d525976b770ae3ba9794587750bd2ba926dccc64e86d7cc2081d2674737` (`12,656,433` B, release
`v0.7.0-qwen38-5090-source.4`) are the checked first build at `26fa28d0` (`v0.7.0-qwen38-5090-beta.4`).
The published runtime image is
`ghcr.io/alphastorm/ninfer-runtime@sha256:7a5a7bb88966512bcab2f711c1a7515bf0b8b834aaf0abd5456643493babb016`
(receipt release `v0.7.0-qwen38-5090-runtime-beta.4`). Runtime dependency base `d4377ed0` is reused
through `runtime-base-04b603aa-20261025` (original source `04b603aa`, ancestor of `26fa28d0`;
`Dockerfile` and runtime-image publication workflows are byte-identical to `v0.14.0`). The kept
strict-origin deployment profile is `qwen38-5090-v0.13.0`, configuration
`751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47`.

The exact shipping bytes (`bab3fd77`) passed all **11/11** exact-source RC phases (`639.894 s`, zero
failures or skips): (1) `host` (`66/66` host tests), (2) `dense_real` (`11/11` dense real-model
tests), (3) `loader` (`1/1`), (4) `shared_mtp_fp8` (`1/1`), (5) `overlap` (`1/1` 32 GB `C2`
durable-pressure overlap), (6) `four_boot_restart` (four-boot schema 3 restart), (7) `product_shape`,
(8) `exact_release_profile` (exact release profile startup), (9) `product_smokes`
(`serve_contract.py` and `agent_protocol.py --contract product`), (10) `help_candidate`, and
(11) `help_control` (`60` flags vs `v0.7.0-qwen38-5090-beta.3`'s `59`, adding opt-in
`--fp32-head-logits`, default off). Startup KV capacity is unchanged across all three RC profile
starts at **146,368** automatic KV tokens (`1,074,790,400` B available against `1,073,741,824` B
reserve, `1,048,576` B margin) and `21,881,405,440` Host context bytes. In the isolated 84-role
ABBA `T1` output-parity and serial decode comparison against `v0.14.0`
`v0.7.0-qwen38-5090-beta.3` (`2c6f423b` / image `760fb6be`),
**84/84 request SHA-256 hashes and 84/84 output SHA-256 hashes matched** across all four arms
(`336/336` HTTP 200), with median decode **347.20 → 346.95 tok/s** (ratio **×0.999282**, per-case
`0.9963–1.0019`, passing the `>= 0.99` fixes-only parity bar).

Published-image lane qualification (`qualify_rtx5090_profile.py` on digest `7a5a7bb8`) and the full
N16 agent-probe campaign against the `v0.14.0` incumbent (`v0.7.0-qwen38-5090-beta.3`, image
`760fb6be`, server `55f0b95a`):
- **Published-image lane receipt ([`releases/v0.16.0/qualification/rtx5090.json`](qualification/rtx5090.json), SHA-256 `2200fa44`, `2026-11-01T00:15:14Z`):**
  **PASS** (`0` transient retries). Anonymous OCI digest-chain verification and an isolated
  empty-`DOCKER_CONFIG` pull of `ghcr.io/alphastorm/ninfer-runtime@sha256:7a5a7bb88966512bcab2f711c1a7515bf0b8b834aaf0abd5456643493babb016`
  passed, and the `/usr/local/bin/ninfer-serve` binary extracted from the image matched
  `bab3fd77e8b5cafb792d0e4648e5e2b0d935105557a0b08fb2541799a25ffce7`. Startup reported BF16 KV with
  automatic capacity **146,368** tokens (`131,072` max context, DFlash2 `K=7`, optimized
  `--lm-head-draft` proposal head) and **30,398 MiB** idle/final VRAM. Cold `prefill_curve` at
  **130,048 prompt tokens** (`17` completion tokens, `0` prefix-cache hits) returned the exact
  planted `ORCHID=493817; COLOR=COBALT` needle in **56.62 s** wall (`56.617 s`, **2,297.0 tok/s**
  wall, **56.51 s** / `56.505 s` server prefill, `30,400 MiB` post-gate VRAM). Single-request
  `decode` (`118` prompt / **2,048** completion tokens) measured **181.78 tok/s** server decode
  (`11.267 s` server) and **180.25 tok/s** wall (`11.362 s` wall) at **0.244** DFlash2 acceptance
  (`1,291 / 5,281` drafted tokens across `756` verify rounds, `0` non-speculative fallback steps,
  per-position accepted draft tokens `[510, 312, 190, 118, 75, 49, 37]` across draft positions
  `1..7`) and **2.71 tokens/round**. The `agent_protocol` gate **passed** (authenticated session
  identity, stateful continuation, `2` forks, parent delete `200`, deleted continuation `404`
  `previous_response_not_found` before and after Docker restart with no resurrection, surviving
  descendant continuation, and live sibling continuation `200`).
- **N16 agent-probe campaign vs `v0.14.0` incumbent (`p16-agent-parity/2`):**
  Every probe oracle and exact planted-key retrieval passed across both published images with `0`
  errors, timeouts, or retries and `0` `(cached - prompt)` deficit on every paired position.
  `warm_arrival` passed **12/12** positions across both orders (`resume-first` and `fork-first`, min
  TTFT bound margin `0.084 s`; on `resume-first/fork_after_resume`, server TTFT dropped from
  **5.159 s** with `4.997 s` `source_wait` on the `v0.14.0` incumbent to **0.278 s** with `0.000 s`
  `source_wait` on `beta.4`, and `fork-first/fork_after_resume` measured `0.119 → 0.113 s`),
  `agent_mix` passed **51/51** (min TTFT margin `0.249 s`), `sibling_continue` passed **5/5** (min
  TTFT margin `0.250 s`), and `fleet_probe` `fanout` passed **11/11** (`post_restart_branch_0` server
  TTFT dropped from **5.437 s** with `5.248 s` `source_wait` on the incumbent to **0.300 s** with
  `0.000 s` `source_wait` on `beta.4`; min TTFT margin `0.243 s`). Four-way concurrent fanout
  (`concurrency_probe.py --scenario fanout --fanout-concurrency 4`) passed **5/5** positions under
  founder-approved parity rule **`p16-agent-parity/2`**, a judge correction that pairs
  simultaneously submitted concurrent branches by server admission order
  (`request_start.timestamp_unix_ms`) while keeping label pairing for sequential positions: under
  `C2` (two active slots), two of the four concurrent branches are admitted immediately (`0.232 vs
  0.234 s` rank 1 and `0.286 vs 0.288 s` rank 2, `29` computed tokens from the private endpoint) and
  two wait for a slot (`1.003 vs 1.001 s` rank 3 and `1.165 vs 1.188 s` rank 4, `23` computed tokens
  from the long anchor), whereas client-label pairing in `/1` read a `C2` admission-order swap
  between `branch-1` and `branch-3` as failures. In two-restart `restore`, two post-restart
  positions exceeded the per-position TTFT bound `incumbent + max(0.25 s, 25%)` (`0.526 s` candidate
  vs `0.241 s` incumbent, `0.491 s` bound, at `restore_0` in the initial run; `0.520 s` candidate vs
  `0.242 s` incumbent, `0.492 s` bound, at `restore_1` in run 0 of the corrected three-run capture,
  while runs 1 and 2 passed `4/4` positions each) and were **waived by the founder with
  disclosure**: the first request after a server restart sometimes takes `~0.5 s` (`0.39–0.53 s`)
  instead of `~0.24 s` (`0.21–0.24 s`) in both engines, and the `beta.4` runtime hits the slow case
  somewhat more often (`4/8` post-restart `restore_0`/`restore_1` requests across four two-restart
  runs vs `2/8` on the incumbent). Both qualification runs restored the production `v0.14.0`
  container (image `760fb6be`), external health HTTP `200`, `30,398 MiB` GPU memory, and healthy
  open fleet admission within the window cap (`1,904.680 s` initial run, `1,243.615 s` corrected
  run; an earlier release-candidate probe run was invalidated after `6/12` `warm_arrival` requests
  when unpruned WSL2 build trees filled the host backing drive, after which VHDX compaction
  reclaimed `282.8 GB` and added a 150 GiB host-free-disk preflight floor).

**Founder-approved 5090-only reproducibility exception:** As in `v0.14.0`, two clean fixed-path WSL2
builds of `26fa28d0` (`nvcc 13.1.115`, `GCC 13.3`, `sm_120a`) are not bit-identical: across `1,242`
captured ELF files (`56,881,590,888` bytes per set), `740` matched and `502` differed (`665/962`
object files and `75/280` other ELF files matched; all three application binaries differed). The
founder-approved reproducibility exception applies to the RTX 5090 container binaries, which ship the
exact preserved first-build `bab3fd77` ELF set that passed the 11-phase RC and 84/84 `T1` comparison
above. Native Windows `sm_86`/`sm_89` shipping closures independently passed `43/43` second-build
EXE/DLL byte comparisons.

## Profiles, state, upgrade notes, and known issues

### Profiles and checkpoint stores

RTX 4090 uses `qwen38-4090-native-v0.8.0-beta.1` (public config `f00cfac9`, 131,072-token INT8 KV,
DFlash2 K7, `C1`, 30 s pending timeout, two extra device-state slots, 1,024-token prefill chunk,
`16,512,696,320`-byte / `15747.734375 MiB` shared Host budget, 640 MiB admission headroom, 32,768 MiB
host RAM floor, 60,000 ms keep-warm, 450 W owner baseline). RTX 3090 uses
`qwen38-3090-native-v0.8.0-beta.1` (public config `cbe67aae`, shared 131,072-token INT8 KV, DFlash2
K7, `C2`, 180 s pending timeout, two extra device-state slots, 1,024-token prefill chunk,
`21,881,405,440`-byte / `20867.734375 MiB` shared Host budget, 768 MiB admission headroom, keep-warm
off, 350 W serving cap with 370 W restored on stop). RTX 5090 keeps `qwen38-5090-v0.13.0` (config
`751d22dc`, 146,368 automatic BF16 KV tokens, 131,072 context, DFlash2 K7 with `--lm-head-draft`,
`C2`, 180 s pending timeout, two extra device-state slots, 1,024-token prefill chunk,
`21,881,405,440`-byte / `20867.734375 MiB` shared Host budget, 28,672 MiB host RAM floor, 60,000 ms
keep-warm).

Native stores use `cache/<release-instance-id>/session-checkpoints-v3` under each immutable component
instance (`qwen38-4090-native-v0.8.0-beta.1-26fa28d0e783` and
`qwen38-3090-native-v0.8.0-beta.1-26fa28d0e783`); the container retains `/checkpoints-v013`.
**MTP3 durable sessions on either native lane (and prior `v0.7.0-qwen38-5090-beta.3` container checkpoints) do not
carry across the `v0.16.0` runtime and backend upgrade.** Keep prior checkpoint roots untouched for
rollback; never import generations across different runtime binaries, speculative backends, or
profiles. Resumed OMP sessions replay the authoritative local transcript for a fresh prefill. Strict
checkpoint origin authentication (`--session-checkpoint-require-origin-auth`) remains mandatory.
Within one API-key principal, `prompt_cache_key` names a session capability; use unique high-entropy
keys and do not share the principal among mutually untrusted clients. Saves remain best effort, and
Windows NTFS `ntfs-write-through` is not POSIX `fsync` or a power-loss guarantee.

### Upgrade notes

- **Running native lanes upgrade directly (the `v0.14.0` RTX 3090 stop-before-upgrade prerequisite
  is dropped):** With `alphastorm/ninfer#48` (`9cb741dc`) and the P16 installer handoff fixes
  (`577fecba`) in `v0.8.0-qwen38-{3090,4090}-beta.1`, `Install-Release.ps1` stops a running
  incumbent lane through its own controller and hands off the GPU-owner lease across equal or
  changed power caps, retaining the `v0.7.0-qwen38-{3090,4090}-beta.3` release as `previous_release` for
  `Control-Release.ps1 -Action Rollback`. Operators no longer need to manually stop a running RTX
  3090 lane before upgrading.
- **Update `fail-closed.yml` for RTX 3090 concurrency 2:** When upgrading an existing
  `~/.omp/agent/config.yml`, update `providers.maxInFlightRequests.ninfer-native-3090` from `1` to
  `2` to match [`examples/manual-tunnel/fail-closed.yml`](../../examples/manual-tunnel/fail-closed.yml)
  (`ninfer-beta: 2`, `ninfer-main: 2`, `ninfer-native-3090: 2`, `ninfer-native-4090: 1`,
  `ninfer-heavy: 1`). Keep `ninfer-native-3090: 2` only against `v0.8.0-qwen38-3090-beta.1` or newer
  (`max_concurrency: 2`, `180 s` pending timeout).

### Known issues and operating trade-offs

- **RTX 5090 first-request latency after a server restart (founder waiver on two-restart `restore`):**
  In both `v0.14.0` (`v0.7.0-qwen38-5090-beta.3`) and `v0.16.0` (`v0.7.0-qwen38-5090-beta.4`), the
  first request against a checkpointed session after a server restart sometimes takes `~0.5 s`
  (`0.39–0.53 s` server TTFT) instead of `~0.24 s` (`0.21–0.24 s` server TTFT), and the `beta.4`
  runtime hits the slow case somewhat more often (`4/8` post-restart `restore_0`/`restore_1`
  requests across four two-restart runs vs `2/8` on the `v0.14.0` incumbent). Two positions in the
  two-restart `restore` probe exceeded the per-position TTFT parity bound `incumbent + max(0.25 s,
  25%)` (`0.526 s` candidate vs `0.241 s` incumbent, `0.491 s` bound, at `restore_0`; `0.520 s`
  candidate vs `0.242 s` incumbent, `0.492 s` bound, at `restore_1`, while all probe checks and
  exact planted-key retrievals passed) and were waived by the founder with this disclosure.
- **RTX 4090 single-case decode floor waiver on `log-024@0` (`0.934` vs `v0.14.0` MTP3):** Across
  the four 4-arm ABBA speed campaigns (`16` arms total at 450 W) on `v0.8.0-qwen38-4090-beta.1`
  (`06526bdb`), DFlash2 `K=7` raised weighted decode throughput to **×1.2736** on the 108-case role
  corpus (`role108`: `84` cases at `0` cached tokens + `12` at `32,000` + `12` at `64,000`, `139.87
  → 178.13 tok/s`), **×1.2741** across all 115 cases (`138.94 → 177.02 tok/s`), and **×1.2778** on
  the 7 code/reasoning supplementals (min **×1.0804**), with `114/115` cases clearing the `>= 0.95`
  per-case decode ratio floor (lowest passing case `1.0128×`) and **115/115** within-engine repeats
  (**43/115** cross-engine) byte-identical. Depth-0 case `log-024@0` decoded at **0.934** (`139.41 →
  130.19 tok/s`, `0.933832×`), below the `0.95` every-case floor (`291` DFlash2 rounds with `732 /
  2,032` accepted drafts vs `306` MTP3 rounds with `717 / 918` accepted drafts), and was waived by
  the founder with this disclosure.
- **RTX 3090 `C2` shared-pool capacity and per-request decode trade-off:** The two concurrent
  requests on `v0.8.0-qwen38-3090-beta.1` share one 131,072-token `INT8` KV pool
  (`kv_capacity: 131072`), not 131,072 resident tokens per request (two ~60K-token requests fit
  concurrently in device KV; two 120K-token requests exceed device KV and require host spill or
  replay). While two 2,048-token decode requests overlap, each individual request decodes at
  **0.70–0.73×** of single-request `C1` speed (`40.18` and `42.81 tok/s` vs `57.58` and
  `58.26 tok/s`, ratios `0.6979×` and `0.7349×`), while combined throughput rises to **1.385×**
  (`79.90` vs `57.68 tok/s`) and two-request pair completion wall drops to **0.722×** (`51.26` vs
  `71.01 s`; solo decode on the `C2` profile is unchanged at `57.94` vs `58.30 tok/s`, `0.9938×`).
- **Deferred fork-council residuals (`alphastorm/ninfer`
  [#50](https://github.com/alphastorm/ninfer/issues/50)–[#54](https://github.com/alphastorm/ninfer/issues/54)):**
  The `26fa28d0` G4 fork council (`CR-20261031T162716Z-26fa28d0`) closed in round 1 with zero
  in-scope P0/P1 residuals after lead controls; its six merged disposition rows (`L1`–`L6` in
  `review/runtime-ledger.json`) are deferred to the next runtime release across five `alphastorm/ninfer`
  bug issues (`#50` tracks both `L1` and `L2`; `#51`–`#54` track `L3`–`L6`):
  1. **[alphastorm/ninfer#50](https://github.com/alphastorm/ninfer/issues/50) (P2, L1 + L2) —
     Unreported or forced-stop shutdown during an unfinished install rollback:** In
     `Control-Release.ps1`, `Stop-ManagedProcess` throws only when a launch-bound shutdown report
     explicitly states `complete: false` or `refused > 0`. If the report is missing or unreadable
     (`graceful_unreported`), if `Stop` falls back to forced process termination
     (`graceful_wait_expired`, `graceful_nonzero_exit`, `terminated`, `signal_failed`), or if a
     later clean `Start`/`Stop` clears a prior refused-save stop, `Stop` returns success. Because
     controller `Rollback` only swaps release pointers without deleting files and destructive
     cleanup in `Install-Release.ps1` is confined to an unfinished install transaction's own
     candidate directories, the only reachable loss is the candidate's recomputable checkpoint cache
     inside an install that never completed; the incumbent's checkpoints and the OMP client
     transcript are never deleted.
  2. **[alphastorm/ninfer#51](https://github.com/alphastorm/ninfer/issues/51) (P3, L3) — Installer
     repair quiescence census skips blank `ExecutablePath`:** During `Install-Release.ps1 -Repair`,
     when state no longer names the candidate release, the process census filters by readable
     `ExecutablePath` and drops entries whose path is blank. Windows executable file locks and
     port-ownership checks still cause cleanup and incumbent restart to fail visibly if a candidate
     server process is still alive.
  3. **[alphastorm/ninfer#52](https://github.com/alphastorm/ninfer/issues/52) (P3, L4) — Checkpoint
     export retirement under host memory exhaustion:** In `engine_checkpoint.inl`, if allocating the
     small retirement command node throws `std::bad_alloc` during process-wide host OOM, the
     in-flight export counter is not decremented inline; the server is already failing under host
     memory exhaustion and the controller's stop timeout terminates the process.
  4. **[alphastorm/ninfer#53](https://github.com/alphastorm/ninfer/issues/53) (P3, L5) — Opt-in FP32
     head-logit flag omitted from `engine_identity()`:** `engine.cpp` omits `fp32_head_logits` from
     `engine_identity()` while `session_checkpoint_service.cpp` includes it, so enabling
     `--fp32-head-logits` would cause checkpoint restore to fail closed with a fingerprint mismatch
     and re-prefill from the transcript. Every shipped profile keeps `fp32_head_logits` off
     (`false`), and packaged configs are hash-asserted at startup.
  5. **[alphastorm/ninfer#54](https://github.com/alphastorm/ninfer/issues/54) (P3, L6) — Uninstall
     power-limit record when `prior_paused` is true:** Running `Uninstall` removes the inner
     GPU-owner lease record while the outer lease has `prior_paused=true`, losing the recorded
     pre-serving power limit and leaving the card at its safe qualified cap (`350 W` on RTX 3090);
     operators can restore the default limit after uninstall with `nvidia-smi -i <gpu> -pl 370`.

The RTX 3090 normal and pressure protocol phases used the founder-approved C2 session-isolation precondition correction (`agent_protocol.py`, SHA-256 `317b98ee0fe110dbefd59b50a4508c2a27da5e7b457f2b819ad98ecd48868913`); quiescence and request-correlated token-delta checks were unchanged. Its raw lane receipt SHA-256 `038fe7132d3188ec4b1259c2933f3dacb23ec066345e723ce1b9baad873fef53` remains private. The public receipt SHA-256 `48c7f63572e38b279dcc941c9f1a2acbf858ec95f1ffe3f0eb8bbc20a8111702` removes the 15 host-lock resource names and replaces both qualification-tool path fields with the basename `agent_protocol.py`; all other JSON values, tool reason/hash, phase outcomes, thresholds and identities are unchanged.

## Fresh candidate acceptance and G4 review

Fresh acceptance is pending; it will run on frozen candidate
`⟦PENDING: v0.16.0 frozen product candidate commit SHA, releases/v0.16.0/acceptance/composed-external-installation.json⟧`
on `⟦PENDING: v0.16.0 acceptance completion date UTC, releases/v0.16.0/acceptance/composed-external-installation.json⟧`.
Runtime qualifications name the current component cuts. Client/route acceptance must still be
executed on the frozen `v0.16.0` product candidate, not inherited from `v0.15.0`. The table below
is the acceptance plan, not a claim that its pending receipts exist. Owner-operated receipts
are tester-equivalent evidence, not independent external-user outcomes.

| Acceptance evidence | Observed result |
| --- | --- |
| Exact stock OMP 18.14.0 platform and live tool/continuation/restart/resume/fail-closed checks | All three newly downloaded stock binaries must match their published asset hashes and `omp/18.14.0`. Typed read-tool/result, exact continuation, and unavailable-route fail-closed checks on macOS arm64 (planned `acceptance/darwin-arm64-18.14.0.json`; pending) (preview), Windows x64 (planned `acceptance/windows-x64-18.14.0.json`; pending), and Linux x64 under WSL2 (planned `acceptance/linux-x64-18.14.0.json`; pending): `⟦PENDING: v0.16.0 platform acceptance details and macOS server-restart nonce resume confirmation, releases/v0.16.0/acceptance/{darwin-arm64,windows-x64,linux-x64}-18.14.0.json⟧`. Image input must be checked on macOS/Windows against RTX 5090 only. |
| Final-candidate guide execution: five routes / 31 executable quickstart blocks plus WSL2 checks | All five routes (planned `acceptance/documented-routes.json`; pending): `⟦PENDING: v0.16.0 documented-route block counts (RTX 5090 host 2/2, macOS 10/10, Windows 5/5, native RTX 4090 7/7, native RTX 3090 7/7) and WSL2 Linux client checks, releases/v0.16.0/acceptance/documented-routes.json⟧`. Pre-publication candidate-clone substitutions are explicit. Subsequent guide edits are prose-only; executable blocks are unchanged. |
| RTX 4090 and RTX 3090 public-install identities, upgrade/rollback, and RTX 3090 `C2` route probes | Separate RTX 4090 (planned `acceptance/rtx4090-public-install.json`; pending) and RTX 3090 (planned `acceptance/rtx3090-public-install.json`; pending) public-URL checks verify all manifest asset hashes and served identities (`06526bdb` / `040d5923`): `⟦PENDING: v0.16.0 native public-install, canonical promotion, rollback-direction, and RTX 3090 C2 fanout/parallel-OMP/compaction probe outcomes, releases/v0.16.0/acceptance/rtx{4090,3090}-public-install.json⟧`. |
| Independent container and native restoration audits and observed hold durations | Independent restoration (`../../docs/measurements/<date>-v0160-acceptance-restoration.json`): `⟦PENDING: v0.16.0 acceptance restoration filename, RTX 5090 container restoration digest and hold duration s, and RTX 4090 / RTX 3090 native driver window durations s and restored power baselines 450/370 W, docs/measurements/*-v0160-acceptance-restoration.json⟧`. |

The composed acceptance (planned `acceptance/composed-external-installation.json`; pending) will bind fresh
observations alongside the `26fa28d0` runtime qualifications. The
[bound review ledger](review/runtime-ledger.json) records:
- **G4 fork council (`CR-20261031T162716Z-26fa28d0`, sequence `omp-ninfer-v0.16.0-fork-26fa28d0`,
  base `2af6b3de` → `26fa28d0`):** All four selected seats (`daybreak-blue`, `gemini-argon`,
  `gpt-astra`, `claude-mythos`) completed in round 1 with zero aborts or truncations; closed without
  remediation by accountable-lead disposition (ledger SHA-256
  `b2871c3664a0c4434dedc3aa2b3f2fdd7f5b301c9d3cecc7d1ce463c835aabe6`, record SHA-256 `cbb0c780`,
  subject digest `42d8473c`), with no in-scope residual P0/P1 and six deferred P2/P3 rows (`L1`–`L6`)
  filed across five issues in `alphastorm/ninfer` ([#50](https://github.com/alphastorm/ninfer/issues/50)
  for `L1` + `L2`, and [#51](https://github.com/alphastorm/ninfer/issues/51)–[#54](https://github.com/alphastorm/ninfer/issues/54)
  for `L3`–`L6`).
- **G4 product-tooling council:** `⟦PENDING: v0.16.0 product-tooling G4 council review ID, sequence ID, frozen candidate commit, seat completion counts, ledger SHA-256, and any deferred product issues, releases/v0.16.0/review/runtime-ledger.json⟧`.

Final manifest evidence pins, strict ready verification, and founder-owned publication are separate
controls; acceptance and G4 approval grant no publication authority.

## Support boundaries and next work

macOS remains preview; Linux client evidence is WSL2-scoped. Native lanes serve sequentially on
port `18082` (two concurrent requests on RTX 3090 run within the single active RTX 3090 lane, never
simultaneously with the RTX 4090 lane). Native vision, RTX 4090 `C2`, `rk4v4` 4-bit KV or
262,144-token native context, `--fp32-head-logits`, `Group64` A8 prefill, small-T tensor-core native
decode, multi-GPU inference, multi-tenancy, silent cloud fallback, and independent external-user
outcomes are not qualified.

This release closes `omp-ninfer` [#94](https://github.com/alphastorm/omp-ninfer/issues/94),
[#95](https://github.com/alphastorm/omp-ninfer/issues/95),
[#96](https://github.com/alphastorm/omp-ninfer/issues/96),
[#116](https://github.com/alphastorm/omp-ninfer/issues/116), and
[#117](https://github.com/alphastorm/omp-ninfer/issues/117) (and incorporates `alphastorm/ninfer`
`#48` and `#49` across all three shipped runtime components). Carried runtime/tooling deferrals
[#88](https://github.com/alphastorm/omp-ninfer/issues/88)–[#90](https://github.com/alphastorm/omp-ninfer/issues/90),
deterministic RTX 5090 `nvcc` module IDs, a corrected repeated native `Group64` A8 screen, and the
new fork-council P2/P3 deferrals in `alphastorm/ninfer`
[#50](https://github.com/alphastorm/ninfer/issues/50)–[#54](https://github.com/alphastorm/ninfer/issues/54)
remain open.

**Next:** root-cause the `rk4v4` 4-bit KV true-cold restore divergence (preregistered
`restored-input-3066` / `prefill-3093` / `generated-step-32` KV, `StateImage`, and logit capture on
diagnostic branch `6e980a5c`, EXP-107) for a 262,144-token native-context follow-up release, and
evaluate stock Oh My Pi **18.14.2** (`7efd7721`) in a separate client-patch release (`v0.16.1`).
