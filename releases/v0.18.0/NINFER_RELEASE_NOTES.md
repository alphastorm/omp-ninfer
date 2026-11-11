# OMP NInfer v0.18.0 — unified engine native re-cut, checkpoint/admission liveness, and stock OMP 18.18.7

> Prepared successor composition — all three GPU lanes target one frozen fork engine source `F4`
> (`48c8ac4644322f024b5c3bd5b657af5874567251` in `alphastorm/ninfer`) with stock Oh My Pi **18.18.7**. Native
> component cuts and hardware qualification, five-route (`31`-block) and three-client-platform acceptance,
> product review, immutable evidence pins, and founder-owned product publication remain pending.
> The F4 runtime source council is closed without remediation; the selected RTX 5090 RC batch
> passed. The RTX 5090 beta.7 component and image are published and its selected-profile lane gate passed;
> package-specific native observations below are not promoted to full release qualification.
> Values marked `__V0180_…__` are stage/composition tokens filled from authenticated receipts before
> publication, not completed passes; in each `[VARIANT …]` / `[NATIVE QUALITY ADMISSION …]` /
> `[PARITY WAIVER …]` block below, the release stage keeps only the selected option and removes the
> bracketed wrapper and unselected alternative.

## Qualified successor scope

This prepared runtime-and-client successor to published **v0.17.0** (`2026-11-10`, `alphastorm/omp-ninfer`
annotated tag `v0.17.0` → `97dea2f00bce385e7fb80c4fddeb38a8f5897385`, GitHub release `440594229`)
re-cuts all three GPU lanes from one frozen fork engine source `F4` (`48c8ac4644322f024b5c3bd5b657af5874567251`) and
advances the client to unmodified upstream **Oh My Pi 18.18.7**
(`e325ffc73ab86e03bdd20a91b77d8e2b3964c906`). Until founder-owned publication of `v0.18.0`,
published installation remains **v0.17.0**; use the
[immutable published v0.17.0 guide](https://github.com/alphastorm/omp-ninfer/blob/v0.17.0/docs/QUICKSTART.md).

The target composition binds:

- **RTX 5090 container runtime:** `v0.7.0-qwen38-5090-beta.7` (companion source archive release tag
  `v0.7.0-qwen38-5090-source.7`), succeeding `v0.7.0-qwen38-5090-beta.6`
  (`e0971faf221204047d5a4ed834e4e298740cee17`).
- **Native Windows RTX 4090 and RTX 3090 runtimes:** `v0.8.0-qwen38-4090-beta.3` and
  `v0.8.0-qwen38-3090-beta.3`, rebuilt from the same frozen source `F4` (`48c8ac4644322f024b5c3bd5b657af5874567251`),
  succeeding `v0.8.0-qwen38-{4090,3090}-beta.2` (`a87de3613c17bced777b446fb545f872d8395ec1`).
  Re-cutting both native lanes from `F4` delivers the `v0.17.0` (`F3` `e0971faf`) bounded
  resume/fresh admission, pressure-work wait, serving robustness, and host-NFC changes alongside the
  `F4` checkpoint, admission, and controller fixes below.
- **Coding-agent client:** unmodified upstream
  [Oh My Pi v18.18.7](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.7) (commit
  `e325ffc73ab86e03bdd20a91b77d8e2b3964c906`, tree `9ba2abe1f1dd7c64b8d3f99dc0e41d689d96886c`,
  release `440868478`).
- **Served model:** unchanged shared published container version 3 `qwen3_8_27b.ninfer` (native
  filename `qwen3_8_27b-v3.ninfer`, `20,437,521,664` bytes, revision
  `1cbd84e7221e51186bd7f093a149912d2489625b`, SHA-256
  `81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da`).

Frozen source `F4` (`48c8ac4644322f024b5c3bd5b657af5874567251`) stacks on fork `main`
`b871996a994ee376dcab9ab290f7af5d768d8a23` (whose tree equals `v0.17.0` release source `F3`
`e0971faf221204047d5a4ed834e4e298740cee17`, on upstream `Neroued/ninfer` master
`64d10fbf9f8e6bfc79ab0570b94674c5b9997929`). On the fork integration branch, PR #106 merged at
`a9fad34c2` and PR #107 merged at `9fd081218`, and the liveness stack (`#109` → `#111` → `#108`)
plus `#112` stack directly on `9fd081218` (`H0` `4b9ef65a728215185948deeb58b64f09b35a4188`), followed
by the accepted default-OFF tensor-core source in [PR #104](https://github.com/alphastorm/ninfer/pull/104),
which is F4. Exact-F4 PR CI and the all-target build passed before the freeze. Integrated H0
proofs (four of four) carry by the recorded default-OFF source/token identity on `sm_120a`,
`sm_86` and `sm_89`; native variant admission is separate. No predecessor route acceptance, client execution, review
approval, or waiver transfers to `v0.18.0`.

RTX 5090 uses release-isolated host checkpoint directory `checkpoints-v018`, preserving predecessor
`checkpoints-v017` and `checkpoints-v013` untouched for rollback, while retaining container mount
path `/checkpoints-v013` to match the container server's `--session-checkpoint-dir` argument.
Native lanes use release-isolated schema 3 stores under
`cache/<release-instance-id>/session-checkpoints-v3`, where `<release-instance-id>` is
`<lane>-native-<version>-<source-sha12>` (such as
`qwen38-4090-native-v0.8.0-beta.3-48c8ac464432` and
`qwen38-3090-native-v0.8.0-beta.3-48c8ac464432`), preserving `beta.2` roots and
staging for rollback. Stop the RTX 5090 predecessor with that checkout's own
`examples/manual-tunnel/stop-ninfer.sh`. A running native predecessor is stopped by its installed
controller during normal upgrade; for a stopped beta.2 lane stuck after an incomplete shutdown,
use the explicit Start-then-install procedure below, not another refused Stop or a newer
controller against the old state. Replay authoritative OMP transcripts for a fresh prefill.

## Runtime changes since v0.17.0

`F4` (`48c8ac4644322f024b5c3bd5b657af5874567251`) adds the following fork changes on top of `F3` (`e0971faf`,
fork `main` `b871996a`), in landing order:

- **Device-staged durable saves without Host-arena room ([fork #89](https://github.com/alphastorm/ninfer/issues/89), folds [#84](https://github.com/alphastorm/ninfer/issues/84); [fork PR #109](https://github.com/alphastorm/ninfer/pull/109), head `3213508fea673789044597746f8bcc64ec605a73`: `bb69c3e74` tests-only red → `9dd6091c9` fix → `3213508fe` reduced-Host harness):**
  When the CPU Host context arena cannot stage a durable checkpoint export after exhausting the
  normal Host copy route and its resident-reclaim tiers, the engine stages `StateImage` recurrent
  state snapshots (`~196 MB` each) directly from GPU Device memory through the existing pinned
  staging buffer rather than refusing the save with `capacity`. Save-refusal reasons and reclaim
  summaries are recorded in checkpoint receipts ([#84](https://github.com/alphastorm/ninfer/issues/84)).
  All `11/11` CPU host test suites (`13` new export/checkpoint cases) and `6/6` single-request
  greedy parity cases (`3` `MTP3` + `3` `DFlash2 K=7`) passed. On the `rtxpro6000-win-a` proxy
  (`913,612,800`-byte reduced Host arena, `3` device-state slots, `DFlash2`), the paired fixture
  where an older occupant session's on-disk checkpoint was deleted went from `Stop` refusing `1`
  session (`capacity`, `0` reclaimed) on base `b871996a` to `Stop` refusing `0` and saving `1`
  session via a Device-staged final save (`device_staged_states: 2`, `device_staged_hold_ms: 1332`
  in final-harness run 4 / `1310` in initial run 1, `host_shortage: host_capacity`), with `State`
  digests (`5ed1d134…`, `8bd4f2b8…`, `fc493f91…`) identical to the base Host route (when the
  occupant remained covered on disk) and `0` `transaction_busy` receipts across all runs (`9`
  initial runs + run 4).
  **Known residual (request-level `503` half of `#89`):** the request-level HTTP `503` queue-timeout
  half of `#89` did not reproduce on the proxy host across three fixtures (in fixture 1 with `4`
  device slots the continuation forked into a free slot; in fixtures 2 and 3 with `3` slots the
  admission planner released the occupant once its pressure save settled). Deterministic admission
  deferral is covered by `EngineCore` `e89_pending_capacity_save_defers_fresh_request`, while
  request-level behavior now has real-card evidence on the **F4 default RTX 3090 package**
  (`2d7ae439…`, server `3b2bbe88…`): NativeProbes completed two committed handoffs with
  **HTTP 503 = 0**, queue timeouts **0**, managed Stop exit **0**, refused sessions **0** and
  `complete=true`; the owner lease was absent, the card returned to **370 W**, and canonical
  restoration was exact. This pre-cut acceptance-class probe does not qualify the different
  `tc` package or replace fresh product-route/campaign acceptance.
- **Durable checkpoint prepares held to an operation-free boundary ([fork PR #111](https://github.com/alphastorm/ninfer/pull/111), head `33088ad2cd023dce85201618516a3ce7b895bcd8`: `a8230894e` → `611e4821a` → `7ca395f47` → `9c6394077` → `33088ad2c`):**
  Off-worker checkpoint export and import prepares that arrive while a context operation is in
  flight are held in `checkpoint_held_commands_` and serviced immediately after the top-of-turn
  completion poll (or at the next operation-free runner pass), ahead of capture restart,
  fresh-window admission, restore, priority admission, and resident unit reservation. Every
  mid-turn operation-start site (capture start, capture preparation, fresh admission, priority
  admission, and resident reclaim) checks the held list so a prepare already on that list runs
  before a new context operation starts (verified by per-site `EngineCore` ordering traces
  `wDBIp` for resident reclaim and `wDBEb` for admission, where releasing the held operation `w`
  completes after decode `D` at mid-turn poll `B` and runs the held import `I` or export `E`
  prepare before resident pause `p` or admission binding `b`; `10/10` CPU suites and `EngineCore`
  `45/45` passed), while export retirements are never held. A prepare newly enqueued after the
  turn's incoming-command snapshot can still wait behind one subsequently started context
  operation; the council retained that bounded ordering residual in
  [fork #115](https://github.com/alphastorm/ninfer/issues/115), without a remediation to F4.
  In the automatic checkpoint coordinator,
  `transaction_busy` refusals on pressure saves spend no retry budget and space retries by at least
  `100 ms` (`kBusyPressureRetrySpacing`, `<= 10/s`), preventing transient busy refusals from parking
  a pressure save (`completed && !settled`).
- **Bounded fresh-admission priority at context-operation boundaries ([fork #102](https://github.com/alphastorm/ninfer/issues/102); [fork PR #108](https://github.com/alphastorm/ninfer/pull/108), head `6ec05f211435f1c26d3d015c50add52ab2a574c6`: `43c859ebe` → `57e231875` → `3b576af88` → `6ec05f211`):**
  When a fresh arrival's admission scan is blocked by an in-flight context operation (or starts its
  own `FreshAdmission` demotion), the engine arms a single bounded priority slot (`K = 4` maximum
  charged attempts per arrival) serviced at three operation-free boundaries (before resident unit
  reservation and after both mid-turn completion polls) so a warm arrival does not wait behind a
  co-resident long prefill's entire chain of per-chunk demotions. Priority service yields without
  charging an attempt while a pressure save is pending, a prepare is held
  (`operation_boundary_taken()`), or an export lease is in flight
  (`checkpoint_exports_in_flight_ != 0`). When a queued request expires while a pressure save is
  latched, the HTTP `503` message appends `(deferred by a pending checkpoint save)`. `EngineCore`
  `56/56` and all `10` companion host suites passed after `9` expected red cases at `57e231875`.
  **Known residual ([Neroued/ninfer#434](https://github.com/Neroued/ninfer/issues/434) fresh-window accounting in [fork #103](https://github.com/alphastorm/ninfer/issues/103)):**
  `Scheduler::advance_service` sets `fresh_window_` only under `!has_context_operation()` and
  `take_fresh_window()` consumes it in the same turn, so a per-rotation fresh-admission window
  cannot be spent while a context operation is in flight; however, the window is still consumed
  without an admission attempt when a pressure checkpoint save is pending (`checkpoints_.pending()`)
  or no serving lane is free, which remains recorded in
  [fork #103](https://github.com/alphastorm/ninfer/issues/103).
- **Native controller lease restoration, removal postconditions, junction containment, exact-byte package archiving, and `beta.3` variant allowlist ([fork PR #107](https://github.com/alphastorm/ninfer/pull/107), head `2454c0629368f3a956b038d3427a9b9139302a71`, merged into the integration base at `9fd081218`; cherry-picks [#91](https://github.com/alphastorm/ninfer/pull/91) `01c706d2b`, addresses [#87](https://github.com/alphastorm/ninfer/issues/87) items 1 and 3 and [#90](https://github.com/alphastorm/ninfer/issues/90)):**
  `Stop-ManagedRelease` in `Control-Release.ps1` attempts guarded GPU-owner lease restoration on
  every thrown `Stop` error (including `graceful_incomplete_shutdown` and post-quiescence
  report/retirement errors) and rethrows the original refusal (attaching any restore error as
  `Data['gpu_owner_restore_failure']`); the refused-stop launch record stays in place so a repeated
  `Stop` still reports the refusal while `Start` (new launch ID) can proceed, and `Rollback` /
  `Uninstall` remain refused after an incomplete `Stop` (the full shutdown-hold state machine
  remains deferred in [fork #50](https://github.com/alphastorm/ninfer/issues/50)). Scheduled-task
  removal (`Uninstall` and `Restore-ReleaseTask`), `Restore-GpuOwnerLease`, `runtime.json`
  retirement, and `Restore-PersistedFileSnapshot` verify absence and propagate removal errors. Both
  `Test-PathWithinRoot` implementations resolve ancestor junctions, symbolic links, and relative
  link targets through `Resolve-NInferFinalPath` in `Protect-StateRoot.ps1`. `New-Package.ps1`
  archives the exact bytes whose digests are recorded ([#91](https://github.com/alphastorm/ninfer/pull/91)),
  advances native metadata to `0.8.0-beta.3`, and validates `-BuildProfile` against the lane's
  committed four-key `build_profiles` allowlist (`default`, `a8`, `tc`, `tc-a8`).
- **Upstream malformed tool-history regression vectors ([fork PR #106](https://github.com/alphastorm/ninfer/pull/106), head `922091123d122795e6e1f6cdcdb36b2c99f4ea6a`, merged into the integration base at `a9fad34c2`):**
  Ports the five malformed/non-object historical tool-call argument vectors from upstream
  `Neroued/ninfer` commit `4461c9683` (`{"x": nope}`, `{"x":`, `[]`, `null`, `{"x":1e99999}`),
  inverted in `tests/models/common/qwen/test_frontend.cpp` and
  `tests/serve/test_serve_resilience.cpp` to assert the fork's non-throwing `{"input": raw}`
  wrapping and ordered-object preservation (whereas `Neroued/ninfer` `4461c9683` returns HTTP `400`
  `invalid_argument`, which would fail every subsequent turn when stock OMP replays stored history).
- **`Group64` `A8` build-profile guard and third-party kernel attributions ([fork PR #112](https://github.com/alphastorm/ninfer/pull/112), head `fd95455df931b3790db410bc083d733e77eddf90`, squashed into `H0` `4b9ef65a728215185948deeb58b64f09b35a4188`):**
  Adds the CMake configure guard (`CMakeLists.txt:29-36`) requiring
  `NINFER_ENABLE_GROUP64_A8_PREFILL=ON` to pair with a hyphen-delimited `a8` component in
  `NINFER_BUILD_PROFILE` on `sm_86`/`sm_89` and refusing `a8` when `OFF` (`13/13` configure matrix
  cases passed; `650` translation units and `1,564` other runtime inputs token-identical to base),
  plus the `THIRD_PARTY_NOTICES.md` attribution section and `src/ops/linear/kernels/group64_a8/mma.cuh:7`
  pointer for the `Group64` `A8` prefill kernel adapted from `ashalliants/ninfer-3090` at commit
  `4a178c4b1fd78555b5efd9b07d10d5b1946ca3ad` under Apache License 2.0 (`src/ops/common/rowsplit_a8_mma.cuh`,
  `src/ops/linear_swiglu/q4a8/a8_linear_add.cu`, `src/ops/linear_swiglu/q4a8/q4a8_linear_swiglu.cu`,
  `src/ops/gdn_input_proj/q4_q5/q4_q5_gdn_input_a8.cu`, and
  `src/ops/attn_input_proj/q4_q5/q4_q5_attn_input_a8.cu`).

### Included tensor-core source and current native selection boundary

- **Native `sm_86`/`sm_89` small-T tensor-core verify included ([fork PR #104](https://github.com/alphastorm/ninfer/pull/104)):**
  `F4` includes the default-`OFF` `sm_86`/`sm_89` small-T tensor-core verify kernel (preview head
  `d534923c66e7ef6c78194734736ce4d49bd55e54`, attribution head
  `03b477c33a41e2aa894eadc94b3dad7c58c1b25e`) for `T=8` and `T=16` verify passes across `Q5`
  linear-add, `n7168` split, `SwiGLU`, and `GDN` record projections, guarded by a hyphen-delimited
  `tc` component in `NINFER_BUILD_PROFILE` (`native-v0.8.0-beta.3-tc-rtx{3090,4090}` or
  `native-v0.8.0-beta.3-tc-a8-rtx{3090,4090}`; `32/32` profile/architecture guard combinations
  passed; `7` touched `OFF` translation units preprocess identically per architecture) and
  attributed in `THIRD_PARTY_NOTICES.md` (`src/ops/linear/kernels/small_t/q45_small_t_mma.cuh:7`) to
  `ashalliants/ninfer-3090` commit `4a178c4b1fd78555b5efd9b07d10d5b1946ca3ad` (`src/ops/linear/q4/q4_ksplit_mma.cuh`,
  `src/ops/linear/q5/q5_small_t_mma.cuh`, `src/ops/common/small_t_layout.cuh`, Apache License 2.0).
  Six FP64 oracle programs passed on each card; kernel source is unchanged between the tested
  preview and F4. Both role-84 preview prescreens used the authenticated published beta.2
  comparator, not candidate-default versus candidate-variant:

  | Card / preview | Weighted decode, incumbent → candidate | Ratio / minimum case | Output identity boundary |
  | --- | --- | --- | --- |
  | RTX 3090, `d534923c`, server `5a8e9561…` | 100.9243 → 155.0738 tok/s | **1.5365362118×** / **1.3496416015×** | Both within-engine repeat pairs identical; **49/84** cross-engine cases differ |
  | RTX 4090, `d534923c`, server `abd7bf19…` | 174.5982 → 206.7878 tok/s | **1.1843643166×** / **0.9939140028×** | Both within-engine repeat pairs identical; **52/84** cross-engine cases differ |

  Both clear the `1.15×` source-inclusion prescreen, not the powered release-quality gate.
- **Exact F4 RTX 3090 tc two-request check:** the corrected check on package `bf1ceaa9…`,
  server `e5713286…`, passed at **1.6532592015×**, **16** verify columns, **134.2372 vs
  81.1955 tok/s** aggregate. The earlier preview-only attempt stopped at installer profile
  validation before candidate decode; it is a metadata/harness failure, not a numerical
  tensor-core failure. The corrected check proves the installer path on the intended tc package.
- **RTX 3090 selection is conditional, not complete:** the lead selected `tc`
  (`native-v0.8.0-beta.3-tc-rtx3090`) for the formal arm. No running A8 estimate exists, so
  `tc-a8` is ineligible under the preregistered rule. The first **504** binding prompts must clear
  secret-leak ratio upper bound **< 1.10** and redaction-difference lower bound **> -0.05**;
  only then does the arm continue to the full **1,120**-prompt EXP-085 verdict. Either
  checkpoint failure falls back to the preserved default package. Checkpoint:
  `__V0180_RTX3090_TC_504_CHECKPOINT__`; full verdict:
  `__V0180_RTX3090_TC_SCREEN_VERDICT__`; final profile/selection binding:
  `__V0180_NATIVE3090_BUILD_PROFILE__` / `__V0180_NATIVE_SELECTION_DECISION_SUMMARY__`.
  No current passing powered screen or final cut is claimed.
- **Default fallback and RTX 4090:** both default packages were built and staged before the
  variant. The F4 RTX 3090 default package matched sealed beta.2 on **84/84** speed cases and
  **80/80** determinism prompts, with zero mismatches and exact restoration; it remains the
  identity-first fallback, not an in-place profile swap after tc installation. RTX 4090 selects
  `native-v0.8.0-beta.3-rtx4090` (tensor-core, A8 and FP32 head logits OFF); its current identity
  result remains `__V0180_RTX4090_DEFAULT_IDENTITY_RESULT__`. Release-bound identity proofs,
  final speed reductions, fit, hardware and route gates remain separate.

### RTX 5090 serving selection

- **RTX 5090 cadence-only prefill pacing remains default-off:** Cadence-only prefill pacing
  (`--prefill-stall-budget-ms 0 --decode-rounds-per-prefill 32`, evaluated against the six
  preregistered bars: on/off single-request byte identity, `80`-prompt determinism, `EXP-077`
  co-resident decode throughput and inter-token gap, long-decoder throughput, and `EXP-109`
  context-pressure pause and HTTP `503` bounds) remains default-off (`--prefill-stall-budget-ms 0
  --decode-rounds-per-prefill 0`) in the retained deployment profile `qwen38-5090-v0.13.0`
  (configuration SHA-256 `751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47`):
  pacing-on co-resident decode measured **92.26 tok/s**, below **100 tok/s**. Single-request
  vectors and determinism passed; the long-decoder capture-join and censored pressure bars
  failed and remain failed, without retry or waiver. Shipping-OFF pressure acceptance passed:
  maximum admitted pause **3.7169 s**, zero HTTP `503`, and both holders completed **40,000** tokens.

### Pre-cut proxy-host engineering evidence and excluded candidates — not release qualification

The observations below come from pre-cut proxy-host (`rtxpro6000-win-a`, `NINFER_VRAM_BUDGET_MIB=31000`,
CUDA `13.4`) and offline CPU runs. They are engineering evidence for the fork changes and exclusions
above, never `v0.18.0` component qualification or product-route acceptance:

| Investigation / subject | Observed baseline | Observed result and boundary |
| --- | --- | --- |
| Warm-history arrival wait under long prefill ([fork #102](https://github.com/alphastorm/ninfer/issues/102)), `rtxpro6000-win-a` proxy, `3` interleaved pairs (`DFlash2 K=7`, `131,072` context, `C2`, `1,024` chunk, `180 s` timeout) | Base `b871996a` (server `962559a5`): arrival `A` source wait **44.576 / 45.030 / 44.999 s**, queue wait **44.797 / 45.127 / 45.097 s**, client TTFT **44.970 / 45.219 / 45.190 s**; long-request `B` wall **46.102 / 46.349 / 46.320 s** (server prefill **44.954 / 45.652 / 45.627 s**) | Candidate `e6d6c667` (server `e38a7508`, source-equivalent to pre-rebase `5af279271` outside `#106` test files and the `#89` queue-expiry suffix; subsequently rebased onto `#111` as `6ec05f211`): arrival `A` source wait **0.000 / 0.000 / 0.000 s**, queue wait **0.096 / 0.097 / 0.212 s**, client TTFT **0.131 / 0.133 / 0.288 s** (**3/3 < 2 s**); **111/111** preferred-and-actual reused tokens in **3/3**; **0** HTTP `503`; **1** priority attempt per arrival (**2** refused scans each, **0** own-demote rounds, `K = 4` never exhausted); long-request `B` wall **47.258 / 47.328 / 47.531 s** (ratios **1.0251× / 1.0211× / 1.0261×**, bar `<= 1.05×`). Single-request greedy parity **6/6** byte-identical (`3` `MTP3` + `3` `DFlash2`). Proxy engineering evidence only; exact-F4 RC2 passed separately below, while full native qualification and selected-profile published-image acceptance remain pending. |
| Reduced-Host durable save at `Stop` ([fork #89](https://github.com/alphastorm/ninfer/issues/89) + [PR #111](https://github.com/alphastorm/ninfer/pull/111)), `rtxpro6000-win-a` proxy (`913,612,800` B Host, `3` device-state slots, `DFlash2`, `15 s` timeout) | Base `b871996a` (server `f5100de7`), deleted occupant: continuation HTTP **200**, managed `Stop` **refused 1** session (`capacity`, **0** reclaimed); covered occupant: `Stop` saved **1**, refused **0** via Host reclaim | Head `3213508fe` (server `860f68a1`) and `#111` `611e4821a`, deleted occupant: continuation HTTP **200**, managed `Stop` **refused 0**, saved **1** via Device-staged final save (`device_staged_states: 2`, `device_staged_hold_ms: 1332` in run 4 / `1310` in run 1, `host_shortage: host_capacity`); `State` digests (`5ed1d134…`, `8bd4f2b8…`, `fc493f91…`) match the base Host route; **0** `transaction_busy` receipts across all runs (`9` initial runs + run 4). Request-level HTTP `503` half did not reproduce on the proxy in **3** fixtures. The exact-F4 default RTX 3090 NativeProbes observation now records two committed handoffs, **0 HTTP 503**, **0 queue timeouts**, complete managed Stop with **0 refusals**, and exact restoration; the distinct tc package and fresh product routes are not covered by it. |
| Malformed historical tool-call vectors ([fork PR #106](https://github.com/alphastorm/ninfer/pull/106)), `rtxpro6000-win-a` proxy (`92209112`, server `0898c280`) | Upstream `Neroued/ninfer` `4461c9683` rejects malformed/non-object historical `arguments` with HTTP **400** `invalid_argument` | All **5** vectors (`{"x": nope}`, `{"x":`, `[]`, `null`, `{"x":1e99999}`) returned HTTP **200** on the initial 3-message request and on the replayed 5-message turn (**10/10** HTTP `200`), preserving `{"input": raw}` wrapping and ordered-object keys (`2/2` CTest targets in **1.27 s**). |
| `sm_120` `Group64` `A8` prefill ([fork PR #105](https://github.com/alphastorm/ninfer/pull/105)), `rtxpro6000-win-a` proxy (`93348eb9`) | Default-`OFF` build (`b871996a`): **15/15** affected shipped translation units token-identical across `sm_86`/`sm_89`/`sm_120a`; default prefill signature `cf336425…` (**132,636** bytes) identical; `K0` mathematical/GPU correctness oracles **8/8** (**344.45 s**) | **`K1` prefill-speed prescreen KILL — excluded from `v0.18.0`:** cold-L2 complete-op weighted prefill speedup **0.784860×** at `512`-token pass width and **0.983623×** at `1,024`-token pass width (below the `1.00×` kill bar and `1.15×` continuation go bar; `SwiGLU` **1.269767× / 1.300676×**, residual `k17408+k6144` **0.569991× / 0.953988×**, `GDN` **0.719792× / 0.745151×**, attention **0.503593× / 0.607777×**). Later end-to-end (`K2`) and quality-screen (`K3`) stages were not executed; [fork PR #105](https://github.com/alphastorm/ninfer/pull/105) closed unmerged. |
| Restricted tool-argument copy drafting, offline CPU replay | Unrestricted retained control (`2,998` turns / `648` sessions / `1,760,181` decode tokens, excluding `1` rewritten live source `b41d66cd…` / `2` turns): **20.5548%** fixed-`12` (12-token minimum n-gram match) / **13.2623%** `12→24→36` copy-miss backoff coverage; modeled decode gain **+5.4889% to +9.3212%** at `m = 4.631` baseline committed tokens per neural round (**+7.2442% to +12.2459%** at rebased `m = 3.875`) across `C = 1.41` to `1.22` relative 16-column copy-round cost | **Below `+15%` session-decode bar — excluded from `v0.18.0`:** `Mode A` (copy rounds restricted to tool-call argument value spans, minimum match `12`: `15.3941%` fixed-`12` / `11.3099%` `12→24→36` backoff coverage) projects **+5.2439% to +7.6563%** at `m = 4.631` (**+6.6167% to +9.6008%** at `m = 3.875`); `Mode B` (same span restriction with minimum match `8` and frequency ranking across distinct source ends: `18.6963%` fixed-`8` / `11.5312%` `8→24→36` backoff coverage) projects **+4.7949% to +7.3278%** at `m = 4.631` (**+6.4980% to +10.1177%** at `m = 3.875`). Neither reaches `+15%` or beats the unrestricted control (`-1.6649` / `-2.1283` percentage points at `C = 1.22`). |
| Experimental RTX 4090 `rk4v4` (`4-bit KV codec, 17,920 B/token vs INT8 33,792 B/token`) screening runs on `beta.2` (`131,072` tokens, `1,024` chunk) | Shipped `INT8` KV (`beta.2`): `1` request at `131,072` tokens (**149.21 tok/s** in the paired screening run); `2` requests refused for capacity | `rk4v4` fits `2` requests at `131,072` tokens (**2.64 GB** spare) and `229,376` tokens (**0.88 GB** spare; `1×262,144` and `2×245,760` refused), measures **150.07 tok/s** `C1` and **285.98 tok/s** `C2` aggregate decode at `131,072` tokens, and matches **32/32** token IDs and UTF-8 under a geometry-matched restore oracle (cold replay split at the saved checkpoint's prefill chunk boundary, `EXP-116`). Experimental only; `rk4v4` remains outside `v0.18.0`. |

## RTX 5090 published component identity

The component and companion source tags resolve to F4. Public release API sizes and digests,
anonymous small-asset downloads, the accepted exact-F4 RC2 asset set and its independent mirror
authenticate the values below. The binary archive was re-hashed locally against the public API
digest and independent mirror; it was not downloaded again. Product-route acceptance remains pending.

| Binding | Exact identity |
| --- | --- |
| Binary release / tag commit | `v0.7.0-qwen38-5090-beta.7` / `48c8ac4644322f024b5c3bd5b657af5874567251` |
| Source release | `v0.7.0-qwen38-5090-source.7` |
| Release source `F4` | `48c8ac4644322f024b5c3bd5b657af5874567251`; fork base `b871996a994ee376dcab9ab290f7af5d768d8a23` (`F3` `e0971faf221204047d5a4ed834e4e298740cee17`) on upstream `64d10fbf9f8e6bfc79ab0570b94674c5b9997929` |
| Binary archive / bytes / SHA-256 | `ninfer-qwen38-rtx5090-v0.7.0-linux-x86_64-cuda13.1.tar.gz` / **580,020,196** / `823d9357f90051564068a8504695a0ec57eb4016681bfd83097f453fcf9eb6ae` |
| SPDX SHA-256 | `1f935ae2ad4ad9ca139b6d50f9ea6db6d186e80921f96c6be5808500e2011e25` |
| Checksum set SHA-256 | `32403769f7cf9dec221124f84e12a7a60b0e0e1495c6c88a61986e0a09af3b04` |
| Source archive / bytes / SHA-256 | `runtime-source-48c8ac46.tar.gz` / **12,877,499** / `7ced9ab1d163e7ac7220752790cc09a53e6863ecbb2fdaf81e4f1d422a67b33d` |
| `ninfer-serve` bytes / SHA-256 | **327,065,128** / `804ef8ac6d062dc8da8784ba3f52e5cece2178a5f5bc46cb2c7bc1d3e8937fe3` |
| Runtime image | `ghcr.io/alphastorm/ninfer-runtime@sha256:496195ecd6cf1f50fcd9dc62cf7b51787f599cc2b196e194baf050c4b149e119` |
| Image receipt release | `v0.7.0-qwen38-5090-runtime-beta.7` |
| Runtime-base receipt / image | `runtime-base-a87de361-20261103` / `ghcr.io/alphastorm/ninfer@sha256:28857182859a8f4993090521899b11a3f8676cb174c59adc626485e9f01472a3` |
| Build profile | `rtx5090` (Release, `sm_120a`, CUDA 13.1, A8 OFF) |
| Deployment profile / configuration SHA-256 | `qwen38-5090-v0.13.0` / `751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47` |
| Published-image lane receipt | `qualification/rtx5090.json` (`763178cbcee0aa999b4647fe52f9879603891d6211a13c264b7f78bf70e71d17`) |

The corrected exact-source RC batch passed **12/12 phases** in **723.968 s**: host, current host,
dense-real, loader, shared MTP/fp8, overlap, four-boot restart, product shape, exact release
profile, PRODUCT smokes and both help inventories. JUnit recorded **66** host, **11** dense-real
and **1** overlap tests with zero failures/skips, plus **54** current host tests. Its authentic
RC receipt SHA-256 is `ca17283887cfad131374fefe6c27488bfcfc171de2a114d17aa97e8b30b8567d`.
The first attempt failed before server launch in the exact-profile phase because the harness
input was a stale release profile; that attempt is retained, and only the corrected RC2 batch
qualifies these tested bytes.

**RC-repeat reproducibility disclosure:** two RC builds of F4 produced different receipt hashes,
`d4b8442df49c6882dfcfc049a79cf04abd8caf3c76b8c3f665d9c0736c2c8eb9` versus
`804ef8ac6d062dc8da8784ba3f52e5cece2178a5f5bc46cb2c7bc1d3e8937fe3`, both **327,065,128 B**.
The first executable was not retained, so the locations and cause of that difference are
unrecoverable; a benign timestamp/build-ID-only explanation is not proven. Section-level
differences in `.text`, `.rodata`, CUDA payloads and build ID were measured **only RC2 versus
the different RDC-recipe binary**, not RC1 versus RC2. The release's reproducibility evidence
remains the separate same-path RDC double build: **664 graph artifacts + three package outputs**
byte-identical, including `ninfer-serve`
`f68279dc72fca47a9daf1e91bb4a0c641e2e10e5acbb9e9b36ff56bad3dca04e`.
The published runtime binary is the **single tested RC2 build**; its different RC recipe
is not claimed run-to-run reproducible. Follow-up to make the RC recipe deterministic or
publish the RDC-recipe binary: [fork #120](https://github.com/alphastorm/ninfer/issues/120).

The package's exact build-identity bytes are available. Public artifact inventory
(`qualification/runtime-artifacts.json`), image publication receipt
(`qualification/runtime-publication.json`) and the selected-profile published-image lane gate
(`qualification/rtx5090.json`, SHA-256 `763178cbcee0aa999b4647fe52f9879603891d6211a13c264b7f78bf70e71d17`:
decode **181.52** tok/s server / **180.01** tok/s wall, cold exact 130,048-token retrieval
**56.896 s** wall / **2,285.7** tok/s wall, and `agent_protocol` across Docker restart) are
installed for this runtime-only stage. Anonymous digest pull, exact image-member binary identity,
agent/restart/no-resurrection gates passed, with zero retries. The incumbent
`v0.7.0-qwen38-5090-beta.6` `1,120`-prompt quality screen capture completed `1,120/1,120` rows with
`0` errors or retries, and its `80`-prompt determinism seal is complete. The RC2 candidate's
full quality screen and fresh-80 determinism passed against that sealed incumbent: all primary
deltas zero, leak ratio **1.0**, and zero determinism mismatches. Pacing remains OFF as described
above; the failed pacing bars are not relabeled as passes.

## Published native beta.3 qualification, quality admission, and speed evidence

Both native Windows lanes (`v0.8.0-qwen38-3090-beta.3` and `v0.8.0-qwen38-4090-beta.3`) are rebuilt
from frozen source `F4` (`48c8ac4644322f024b5c3bd5b657af5874567251`). Both default packages and
the separate unused RTX 3090 tc package have authenticated closed asset sets and packaged
release-spec/server-config bytes. Two native build rounds matched **34/34** tracked artifacts
for each package, and retained scans reported zero findings. The immutable package-build
receipts remain `hardware-pending`; no qualification status is edited into them.
Component cuts, full 15-phase hardware
qualification chains, quality admission (`identity-first` or `powered` `1,120`-prompt `EXP-085`
screen), fit proofs, decision-scoped ABBA speed gates, and upgrade/rollback/repair rehearsals are
**pending**:

| Lane | Component / tag commit / build profile | Package SHA-256 / bytes | Server SHA-256 | Configuration SHA-256 | SPDX / CycloneDX SHA-256 |
| --- | --- | --- | --- | --- | --- |
| RTX 3090 | `v0.8.0-qwen38-3090-beta.3` / `__V0180_NATIVE3090_TAG_COMMIT__` / `__V0180_NATIVE3090_BUILD_PROFILE__` | `__V0180_NATIVE3090_PACKAGE_SHA256__` / `__V0180_NATIVE3090_PACKAGE_BYTES__` | `__V0180_NATIVE3090_BINARY_SHA256__` | `674d52609e22de54a5db20001e25fdd97cd600d498551ecfe48efa53964fc3ac` | `__V0180_NATIVE3090_SPDX_SHA256__` / `__V0180_NATIVE3090_CDX_SHA256__` |
| RTX 4090 | `v0.8.0-qwen38-4090-beta.3` / `__V0180_NATIVE4090_TAG_COMMIT__` / `native-v0.8.0-beta.3-rtx4090` | `ac41700ac2bb9fb171188f35e73481cfd9f1140c5781320b1e6304ee760d7166` / **992,131,123** | `a5266ae676305cc56086df6d3b8dc8968be110b3cf0eb7b18147adafc2f66d22` | `b71a2cff25d671703106474d86fe6a808dc803db28703b6fd7740013fcfee278` | `4ad1f5e8fcd610f2a7246e8284b8eb7870c4ec62a587f938d9bdfb564ae49a70` / `60a1d35df6d328a9699a223d7bb8e19a3067967e80f6965f5e4278f72486df85` |

The RTX 3090 final row deliberately remains unbound until the formal-arm decision. The already
real alternatives are:

| RTX 3090 pre-cut package | Package SHA-256 / bytes | Server SHA-256 | Config / outer SHA256SUMS |
| --- | --- | --- | --- |
| Default identity-first fallback, `native-v0.8.0-beta.3-rtx3090` | `2d7ae439da95fb79c380b3852de1012b8529add483d5163c40410b50905ab26a` / **1,009,126,671** | `3b2bbe88c6aa66af871a4f1d1e11aec9863b71a06870ec7c6a35569f5bacbc63` | `674d52609e22de54a5db20001e25fdd97cd600d498551ecfe48efa53964fc3ac` / `2533a5bc8c564ca0ac309baefb46b4cea1995db31ccb1cdd572a49c6b65a7dc9` |
| Conditional tc formal-arm subject, `native-v0.8.0-beta.3-tc-rtx3090` | `bf1ceaa9eb522a8c8d9372bec475d6e4e4666e6a995302cd20035e80ae3e5edd` / **1,011,087,765** | `e571328699be41d90eff8743d94da26e8f587e48bc32f618013625af7ad0bfe0` | `674d52609e22de54a5db20001e25fdd97cd600d498551ecfe48efa53964fc3ac` / `74d33ed824008e5279b9ad2709a56e95e92d99b700c1c39b06026b90ef9c29e9` |

Only the final selected package may be cut and promoted for the lane/tag. The default's
NativeProbes and 84/84 + 80/80 identity observations above are not claims about the tc subject.

The bound `qualification/native-publication.json` (`__V0180_NATIVE_PUBLICATION_SHA256__`), 15-phase
lane receipts (`qualification/rtx3090.json` `__V0180_RTX3090_RECEIPT_SHA256__` at
`__V0180_RTX3090_DECODE_TOK_S__` tok/s `C1` decode and `__V0180_RTX3090_RETRIEVAL_S__` s exact
130,048-token retrieval; `qualification/rtx4090.json` `__V0180_RTX4090_RECEIPT_SHA256__` at
`__V0180_RTX4090_DECODE_TOK_S__` tok/s `C1` decode and `__V0180_RTX4090_RETRIEVAL_S__` s exact
retrieval), and fit proofs (`qualification/rtx3090-windows-native.fit.json`
`__V0180_RTX3090_FIT_SHA256__`; `qualification/rtx4090-windows-native.fit.json`
`__V0180_RTX4090_FIT_SHA256__`) replace the carried `v0.16.2` / `v0.17.0` `beta.2` evidence. No
historical `beta.2` qualification receipt is reused as a `beta.3` proof.

The founder-selected speed rule (`qualification/native-speed-decision.json`, SHA-256
`__V0180_NATIVE_SPEED_DECISION_SHA256__`, quoting the `2026-11-11` founder gate decision record,
`provenance.source_sha256` `ffb302ff3e923088fed85ebcf662328e4cb2387c18e290c30b7bf3a490fe0736`)
compares each `beta.3` candidate against published `v0.8.0-qwen38-{3090,4090}-beta.2`:
role-weighted and all-case-weighted decode ratios **>= 0.98**, every case **>= 0.95**, within-engine
(`A0/A3`, `B1/B2`) byte-identical normalized outputs always required, and cross-engine (`A/B`)
output differences admitted only on a lane with a decision-bound passing `1,120`-prompt `EXP-085`
quality screen in `quality_screens`:

| Current `beta.3` speed gate vs published `beta.2` | Receipt SHA-256 | Weighted decode ratio | Minimum case | Normalized-output identity and quality admission |
| --- | --- | --- | --- | --- |
| RTX 3090 (`qualification/rtx3090-speed.json`) | `__V0180_RTX3090_SPEED_SHA256__` | `__V0180_RTX3090_SPEED_WEIGHTED__` | `__V0180_RTX3090_SPEED_MIN__` | `__V0180_RTX3090_SPEED_IDENTITY__` (`__V0180_RTX3090_QUALITY_ADMISSION_MODE__`, `__V0180_RTX3090_QUALITY_ADMISSION_SHA256__`) |
| RTX 4090 (`qualification/rtx4090-speed.json`) | `__V0180_RTX4090_SPEED_SHA256__` | `__V0180_RTX4090_SPEED_WEIGHTED__` | `__V0180_RTX4090_SPEED_MIN__` | `__V0180_RTX4090_SPEED_IDENTITY__` (`__V0180_RTX4090_QUALITY_ADMISSION_MODE__`, `__V0180_RTX4090_QUALITY_ADMISSION_SHA256__`) |

Keep the applicable quality-admission paragraph(s) below at staging (both may be kept if one native
lane uses `identity-first` and the other uses `powered`):

- `[NATIVE QUALITY ADMISSION — OPTION A (keep for each default-profile native lane bound with scripts/bind_native_variant.py --identity-proof; remove wrapper):`
  **Identity-first admission (`qualification/native-identity-decision.json`, SHA-256
  `__V0180_NATIVE_IDENTITY_DECISION_SHA256__`):** Under the founder `identity_first` rule (restricted
  to the default `native-v0.8.0-beta.3-rtx{3090,4090}` build profile), the lane matched published
  `beta.2` byte-for-byte on every speed-ABBA case (`A0/B1/B2/A3`) and on all `80/80` sealed
  incumbent determinism prompts (`qualification/rtx{3090,4090}-windows-native.identity-proof.json`,
  SHA-256 `__V0180_RTX3090_QUALITY_ADMISSION_SHA256__` /
  `__V0180_RTX4090_QUALITY_ADMISSION_SHA256__`), skipping the `1,120`-prompt arm. `]`
- `[NATIVE QUALITY ADMISSION — OPTION B (keep for each native lane bound with scripts/bind_native_variant.py --quality-screen; remove wrapper):`
  **Powered `1,120`-prompt `EXP-085` quality screen (`qualification/rtx{3090,4090}-windows-native.quality-screen.json`,
  SHA-256 `__V0180_RTX3090_QUALITY_ADMISSION_SHA256__` /
  `__V0180_RTX4090_QUALITY_ADMISSION_SHA256__`):** The lane passed all primary `EXP-085` bounds
  against published `beta.2` (including the `< 1.10` secret-leak ratio and `> -0.05` redaction
  bound) with `80/80` fresh-cache determinism per arm (`__V0180_NATIVE_QUALITY_SCREEN_SUMMARY__`). `]`

Separate running-upgrade, forced-start rollback, and interrupted-install repair rehearsals from
published `v0.8.0-qwen38-{3090,4090}-beta.2` (`3/3` scenarios per lane) are **pending**:
`__V0180_NATIVE_REHEARSAL_SUMMARY__`.

## Exact-subject founder decisions and waivers

No `v0.17.0` or `v0.16.2` waiver is renewed for `v0.18.0`, including the `v0.17.0` RTX 3090
`native-probes` compaction campaign waiver (`19f2c0ef0f9bbf38b6debaacdbb84e8e219c1f03b1d26671ca3fdfcbf63943f0`).
The three `v0.18.0` founder gate decision records in `releases/v0.18.0/qualification/` quote the
`2026-11-11` founder gate decision record (`provenance.source_sha256`
`ffb302ff3e923088fed85ebcf662328e4cb2387c18e290c30b7bf3a490fe0736`):

| Founder decision record / public projection | Bound file SHA-256 | Scope |
| --- | --- | --- |
| `qualification/native-speed-decision.json` | `__V0180_NATIVE_SPEED_DECISION_SHA256__` | `v0.18.0` native speed rule vs published `beta.2`: weighted decode `>= 0.98`, every case `>= 0.95`, within-engine (`A0/A3`, `B1/B2`) byte identity, cross-engine differences only with a bound passing `EXP-085` screen |
| `qualification/native-identity-decision.json` | `__V0180_NATIVE_IDENTITY_DECISION_SHA256__` | `v0.18.0` default-profile native identity-first rule: complete speed-ABBA byte identity + `80/80` sealed incumbent determinism skips the `1,120`-prompt arm |
| `qualification/slow-first-request-parity-waiver-class.json` | `__V0180_PARITY_WAIVER_DECISION_SHA256__` | Class rule only: slow-first-request parity misses on the `restore` or `sibling` probes (known two-mode Host-restore class) may be waived with exact-subject disclosure; grants no pass by itself |

Keep one parity-waiver paragraph at staging/composition:

- `[PARITY WAIVER — OPTION A (keep if no slow-first-request parity miss occurred; remove wrapper and OPTION B):`
  No slow-first-request parity waiver (`rtx{5090,4090,3090}_{restore,sibling}_waiver`) or
  route-campaign waiver was applied in `v0.18.0`; all judged parity positions and route campaigns
  passed without a waiver application. `]`
- `[PARITY WAIVER — OPTION B (keep if one or more known-class slow-first-request parity misses occurred and were bound; remove wrapper and OPTION A):`
  Exact-subject slow-first-request parity waiver applications (`raw_passed: false` retained in
  every underlying receipt): `__V0180_APPLIED_PARITY_WAIVERS_SUMMARY__`. `]`

## Stock OMP 18.18.7

Selected client: unmodified upstream
[`can1357/oh-my-pi v18.18.7`](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.7), published
`2026-11-10T20:23:32Z`, release **440868478**, source commit
`e325ffc73ab86e03bdd20a91b77d8e2b3964c906`, tree
`9ba2abe1f1dd7c64b8d3f99dc0e41d689d96886c` (`64` commits and `145` changed paths after `v18.18.6`
`9058ab9d229663e229e2867824ba6df6f21e9e59`). `SHA256SUMS.txt` is asset `732828898` (`844` bytes,
SHA-256 `9a33908bc535d1fdc28997cd26f3056fb581558f8b0e812988ffd486f0112606`). The
[18.18.6→18.18.7 client upgrade review](../../docs/measurements/2026-11-11-omp-18187-client-upgrade-review.json)
([PR #154](https://github.com/alphastorm/omp-ninfer/pull/154), landed at `44590ad`) is staged at
`qualification/stock-omp.json` (SHA-256 `98a1e24d7e3d0ec03e6ffcc9c44ed7aad2e40dcaf923ead83b66d4ea5a216f38`), and the platform
descriptor is `qualification/client-components.json` (SHA-256
`__V0180_CLIENT_COMPONENTS_SHA256__`). Source review and independent download verification do not
substitute for live client acceptance.

| Platform | Asset / ID | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| macOS arm64 | `omp-darwin-arm64` / `732828892` | 221,982,864 | `0cecaac781d3c37f32ff7ecf3b6ba94842e7f058358e4748d5071d772f0aa4df` |
| Windows x64 | `omp-windows-x64.exe` / `732828893` | 250,108,928 | `4a6e39ea34633e03d07a1543ba30842362311f920341378433aa31b6c1404491` |
| Linux x64 under WSL2 | `omp-linux-x64` / `732828896` | 286,136,496 | `ea6c216feb260a3766a591760aad06bdc608efd5c632912603f5ccb41b0a4bb1` |

- **Windows `bash` tool-description wire change and probe boundary (disclosed):** On Windows
  (`process.platform === "win32"` — the native RTX 4090, native RTX 3090, and Windows-client RTX
  5090 routes), stock OMP `18.18.7` changes the rendered `bash` tool description sent to the model
  whenever `bash` is advertised (`prompts/tools/bash.md`), adds `cmd`-dialect `find`/`sort`/
  `timeout`/`whoami` and `/c/...` / `/mnt/c/...` MSYS drive-path resolution (`crates/pi-shell`),
  and flushes cached command lookups on `PATH` reassignment across all platforms (`PATHEXT` on
  Windows). The JSON tool parameter schemas and OpenAI Responses serializer are byte-identical to
  `18.18.6`. Because `scripts/hosts/omp-client-probe.py` invokes the `omp` client binary with
  `--tools read`, the changed Windows `bash` tool description and shell/edit dispatch are not
  separately probed by that harness beyond route acceptance
  (`__V0180_CLIENT_SUPPLEMENTARY_PROBES_SUMMARY__`).
- **Unchanged model/config fragments and carried route-sensitive source objects:** All six `v0.17.0`
  fragment files under `examples/` (five `models*.fragment.yml` files plus
  `examples/manual-tunnel/fail-closed.yml`) and `26` route-sensitive upstream Git trees/blobs
  across `v18.18.6..v18.18.7` carry byte-for-byte unchanged: `compat.statefulResponses: true`,
  `compat.includeEncryptedReasoning: false`, and `compat.supportsReasoningSummary: false` per model;
  explicit `tokenizer: qwen3` on opaque `q38-ninfer` aliases (canonical `qwen3.8-27b` infers
  `qwen3`); explicit `[low, medium, xhigh]` effort lists with `high`→`medium` and `off`→`low`
  clamps; `model.loopGuard` enabled (`4` repeats / `1,024` characters for short newline-spanning
  cycles, `4` / `180` for short non-newline cycles, `3` / `1,024` for long cycles; obsolete
  `compat.thinkingLoopGuard` absent); default async compaction (`19,660`-token reserve, strict
  `> 111,412`-token trigger, `13,107`-token unset-reserve summary cap); and explicit
  `retry.enabled: false`, `retry.modelFallback: false`, `fallbackRevertPolicy: never`,
  `update.auto: false`, `startup.checkUpdate: false`, and `startup.setupWizard: false`.

## Retained model, serving policy and upgrade boundary

Shared model: `qwen3_8_27b.ninfer` (native filename `qwen3_8_27b-v3.ninfer`), revision
`1cbd84e7221e51186bd7f093a149912d2489625b`, container version **3**, **20,437,521,664 bytes**,
SHA-256 `81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da`.

| Lane | Selected serving shape |
| --- | --- |
| RTX 5090 | BF16 KV, DFlash2 `K=7` (`--lm-head-draft`), 131,072 context, 146,368 automatic KV tokens, `C2` plus two extra device-state slots, 21,881,405,440 B shared Host budget, 28,672 MiB host floor, 1,024-token prefill chunk, 180 s admission timeout, 60,000 ms keep-warm, mandatory `--session-checkpoint-require-origin-auth`, host `checkpoints-v018` mounted at `/checkpoints-v013`; profile `qwen38-5090-v0.13.0`, config `751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47` |
| Native RTX 4090 | INT8 KV, DFlash2 `K=7` (`Q4_G64_FP16` draft MLP, host-mapped token embedding, `artifact-default` proposal), 131,072 context/pool, `C1` plus two extra device-state slots, 16,512,696,320 B shared Host budget, 32,768 MiB host floor, 640 MiB admission headroom, 1,024-token prefill chunk, 30 s pending timeout, 60,000 ms keep-warm, 450 W owner baseline, mandatory origin auth; build profile `native-v0.8.0-beta.3-rtx4090`, config `b71a2cff25d671703106474d86fe6a808dc803db28703b6fd7740013fcfee278` |
| Native RTX 3090 | INT8 KV, DFlash2 `K=7` (`Q4_G64_FP16` draft MLP, host-mapped token embedding, `artifact-default` proposal), `C2` over one shared 131,072-token pool plus two extra device-state slots, 21,881,405,440 B shared Host budget, 768 MiB admission headroom, 1,024-token prefill chunk, 180 s pending timeout, keep-warm off, 350 W serving cap / 370 W restored, mandatory origin auth; build profile `__V0180_NATIVE3090_BUILD_PROFILE__`, config `674d52609e22de54a5db20001e25fdd97cd600d498551ecfe48efa53964fc3ac` |

In `docs/QUICKSTART.md` ([PR #155](https://github.com/alphastorm/omp-ninfer/pull/155), commit
`c74cb2c25d2e709bd63ebb2b0023a10b478b482e`), both native `Operate` executable code blocks
(`rtx4090-native/operate` and `rtx3090-native/operate`) check `Status`, `Stop`, `Start`, and final
`Status` individually so a refused `Stop` cannot be hidden by a later successful `Status` (changing
both extracted block SHA-256 digests from `7cae194b…` to `4ea38c9b…`), and the three campaign
launchers (`scripts/hosts/run_variant_campaign_{3090,4090,5090}.ps1`) require an explicit
`-GroupwiseIntModel` file path (plus `-Nvfp4Model`, `-CampaignRoot`, and `-ApiKeyFile` on
`run_variant_campaign_5090.ps1`). The staging receipt audit (`qualification/receipt-audit.json`,
SHA-256 `__V0180_RECEIPT_AUDIT_SHA256__`) records `__V0180_RECEIPT_AUDIT_SUMMARY__`.

### Native upgrade, shutdown and exact fallback disclosures

**(a) A beta.2 installation stuck after an incomplete shutdown.** If the lane is stopped,
every managed Stop reports an incomplete shutdown, and the installer refuses a non-running
incumbent that retains a GPU-owner lease, do not delete the lease, runtime files or checkpoints.
Keep the diagnostic receipts and OMP transcripts. Unsaved server-side sessions from that shutdown
are lost. Once the operator accepts restarting from saved state or replaying the transcript,
**Start the installed beta.2 controller using the same state root, then run the normal beta.3
installer while beta.2 is running**, using this lane's verified package/model/key/stage inputs.
Do not add another preliminary Stop, Restart, `-NoStart`, interrupted-install repair, or a staged
newer controller against the old state. Start must return running/ready; the installer then stops
the incumbent with its own controller and preserves it as the previous release. If Start or the
next Stop refuses, stop and inspect the new refusal rather than editing ownership state.

**(b) Explicit Start is not Restart or save recovery.** Start creates a new launch and clears the
previous launch's shutdown refusal. It does not retry failed saves; unsaved sessions are lost.
Saved checkpoints and authoritative OMP transcripts remain subject to their existing compatibility
rules, and `last_stop` may retain the old incomplete-shutdown diagnostic until a later Stop.
Restart first runs Stop and can refuse before starting anything. Start reuses the ownership
lease; it does not hand-delete it or guarantee that the next shutdown succeeds.

**(c) The rollback refusal is launch-report-bound.** For shutdown-save failures, only a valid
report tied to the last launch that records incomplete shutdown or refused sessions blocks
rollback. A missing/unreadable report, nonzero server exit or timeout-killed shutdown does not
by itself block rollback, and is not proof that sessions were saved. Inspect the last-stop
receipt; the other stopped-process and retained-predecessor safety checks still apply.

**(d) One package per native lane/tag; fallback is exact beta.2 rollback.** Promote only the final
selected package. An installed tc/a8/default package cannot be replaced in place by another build
profile of the same F4 source. Post-install fallback is
`Control-Release.ps1 -Action Rollback -StateRoot $StateRoot` to the exact retained native beta.2
installation, not a swap to the preserved but uninstalled F4 default package. Keep the predecessor
release, key and checkpoint directories. A fresh install without a retained predecessor has no
exact rollback target; uninstalling removes state needed for rollback and is not a profile switch.

The Start-then-install procedure and rollback-policy distinctions were checked against the
published 0.8.0-beta.2 controller and F4 installer in the release fixture. That is lifecycle
decision evidence with OS adapters, not an additional real-Windows or GPU qualification.

## Fresh candidate-bound route and client acceptance

Fresh candidate-bound route, client, campaign, public-install, and restoration acceptance are
**pending**: acceptance date `__V0180_ACCEPTANCE_DATE__`, frozen product candidate
`__V0180_CANDIDATE_COMMIT__` across all five documented routes (`31` executable blocks:
`rtx5090-container-host` `2`, `rtx5090-macos-client` `10`, `rtx5090-windows-client` `5`,
`rtx4090-native` `7`, `rtx3090-native` `7`) plus the three stock-client platform receipts
(`acceptance/{darwin-arm64,windows-x64,linux-x64}-18.18.7.json`, where `omp-linux-x64` under WSL2
is a client-platform acceptance check rather than a sixth documented route), executed guide SHA-256
`__V0180_EXECUTED_GUIDE_SHA256__`, and final prose-only guide SHA-256
`__V0180_FINAL_GUIDE_SHA256__`.

| Documented route or client-platform check | Actual result (pending execution) |
| --- | --- |
| RTX 5090 container host (`rtx5090-container-host`, `2` blocks) | `__V0180_ROUTE_HOST_VERDICT__` |
| macOS arm64 over manual SSH (`rtx5090-macos-client`, `10` blocks + `acceptance/darwin-arm64-18.18.7.json`, preview) | `__V0180_ROUTE_MACOS_VERDICT__` |
| Native Windows x64 against RTX 5090 (`rtx5090-windows-client`, `5` blocks + `acceptance/windows-x64-18.18.7.json`) | `__V0180_ROUTE_WINDOWS_VERDICT__` |
| Linux x64 under WSL2 against RTX 5090 (client-platform check `acceptance/linux-x64-18.18.7.json`, not a sixth route) | `__V0180_ROUTE_WSL2_VERDICT__` |
| Native RTX 4090 (`rtx4090-native`, `7` blocks + `C1` campaign + public install + restoration) | `__V0180_ROUTE_RTX4090_VERDICT__` |
| Native RTX 3090 (`rtx3090-native`, `7` blocks + `C2` fanout/parallel/compaction campaign + public install + restoration) | `__V0180_ROUTE_RTX3090_VERDICT__` |

`acceptance/documented-routes.json` (`__V0180_DOCUMENTED_ROUTES_SHA256__`) and
`acceptance/composed-external-installation.json` (`__V0180_COMPOSED_ACCEPTANCE_SHA256__`) will bind
the five route run receipts under
`docs/measurements/__V0180_ACCEPTANCE_DATE__-v0180-{rtx5090-container-host,rtx5090-macos-client,rtx5090-windows-client,rtx4090-native,rtx3090-native}-run.json`:

| Lane | Run receipt SHA-256 |
| --- | --- |
| `rtx5090-container-host` | `__V0180_ROUTE_HOST_SHA256__` |
| `rtx5090-macos-client` | `__V0180_ROUTE_MACOS_SHA256__` |
| `rtx5090-windows-client` | `__V0180_ROUTE_WINDOWS_SHA256__` |
| `rtx4090-native` | `__V0180_ROUTE_RTX4090_SHA256__` |
| `rtx3090-native` | `__V0180_ROUTE_RTX3090_SHA256__` |

Measured hold and campaign durations (pending): RTX 5090 production hold `__V0180_RTX5090_HOLD_S__` s;
RTX 4090 campaign `__V0180_RTX4090_CAMPAIGN_S__` s (`acceptance/rtx4090-public-install.json`
`__V0180_RTX4090_PUBLIC_INSTALL_SHA256__`); RTX 3090 campaign `__V0180_RTX3090_CAMPAIGN_S__` s
(`acceptance/rtx3090-public-install.json` `__V0180_RTX3090_PUBLIC_INSTALL_SHA256__`). Independent
restoration receipt `docs/measurements/__V0180_ACCEPTANCE_DATE__-v0180-acceptance-restoration.json`
(`__V0180_RESTORATION_RECEIPT_SHA256__`): `__V0180_RESTORATION_SUMMARY__`.

## Exact-subject review and publication boundary

Runtime full-council review on exact frozen F4
`48c8ac4644322f024b5c3bd5b657af5874567251` **closed without remediation**: all **nine** finding
rows are dispositioned, with **no in-scope residual P0/P1** and no change to the frozen subject.
Three reviewers completed; the fourth was missing after a provider transport/credential failure
and its permitted retry, not silently counted as an approval. The final epoch recheck reported
no drift. Deferred follow-ups are the bounded prepare-ordering residual
([#115](https://github.com/alphastorm/ninfer/issues/115)), unreported-shutdown Stop policy
([#116](https://github.com/alphastorm/ninfer/issues/116)), native instance identity omitting
build profile ([#117](https://github.com/alphastorm/ninfer/issues/117)), and Linux packaging
stage-and-revalidate ([#118](https://github.com/alphastorm/ninfer/issues/118)). The state-image
pinning concern closed by source lifetime/reachability analysis, not a blocked-writer GPU test.
The four operator disclosures above are retained; council closure is not a hardware or route pass.

Product council review on `__V0180_PRODUCT_REVIEW_COMMIT__` with
`product_tooling.stage_commit == __V0180_CANDIDATE_COMMIT__`, the content-safe combined
`review/runtime-ledger.json` binding (`__V0180_REVIEW_LEDGER_SHA256__`), and final publication
admission remain **pending**. Additional pre-publication follow-ups still need their actual
issue URLs: deterministic RC recipe or publishing the RDC-recipe binary
(`__V0180_RC_REPRODUCIBILITY_FOLLOWUP_URL__`), and preserving the initiating installer error when
rollback itself is incomplete (`__V0180_INSTALLER_ROLLBACK_ERROR_FOLLOWUP_URL__`).

The lead-admitted product tooling head is `71af1df2f5acc977eb1acc5b9550ea05b1d86fe3`.
Product release-tooling changes landed on `main` ahead of staging close the
[#149](https://github.com/alphastorm/omp-ninfer/issues/149) verifier, composer, staging, hold, and
profile-variant gaps:

- **[PR #156](https://github.com/alphastorm/omp-ninfer/pull/156) (`24f7195`):** stamps release-local
  profile snapshots at staging (`scripts/stage_release.py`) and mirrors them byte-for-byte at
  promotion (`scripts/rebind_release.py`); reconciles Windows client holds by ownership marker with
  `HoldStatus` and guarded `Release` (`scripts/hosts/accept-windows-client.ps1`,
  `scripts/hosts/accept-rtx5090-routes.py`); writes verified sibling temporary files in
  `scripts/hosts/pscp.py` before atomic replacement; resolves the RTX 4090 campaign model from the
  documented route (`scripts/hosts/run_variant_campaign_4090.ps1`); and adds decision-scoped native
  speed (`scripts/speed_gate.py`) and default-only `--identity-proof`
  (`scripts/bind_native_variant.py`) gates.
- **[PR #157](https://github.com/alphastorm/omp-ninfer/pull/157) (`806ec4e`):** reconciles the
  frozen product-review stage (`g4_review.product_tooling.stage_commit`) and every route clone in
  `v0.18.0+` ready checks (`scripts/verify_release.py`); re-derives the `docs/QUICKSTART.md` guide
  hash and block addresses; authenticates native observed client/package records against the
  candidate manifest; checks and serializes all composed public artifacts before writing
  (`scripts/compose_route_acceptance.py`); projects captured observations through explicit public
  allowlists; scans all shipped scripts for private markers; requires explicit model paths on
  `scripts/hosts/run_variant_campaign_{3090,4090,5090}.ps1` and `-CandidateClone` / `-ClientBinary`
  on `scripts/hosts/accept-native-public-install.ps1`; and admits decision-authorized native
  identity proofs in `scripts/verify_release.py`.
- **[PR #158](https://github.com/alphastorm/omp-ninfer/pull/158) (`22a1d03`):** validates native
  build-profile variants against the source-committed `release-spec.json` `build_profiles`
  allowlist in `scripts/hosts/cut-ninfer-4090-component.sh` and native qualification/binding/
  rebind/verification/composition scripts, and compares arm `build_profile` values when both records
  carry one while keeping default-only restrictions on `identity-first` proofs.

Product publication and production promotion remain separate founder-only actions. `macOS` remains a
manual-SSH tunnel preview; `Linux` remains `WSL2`-scoped; vision inputs remain `RTX 5090`
container-only. No native/Linux vision, concurrent native-lane serving, `rk4v4` adoption,
checkpoint migration, multi-owner proof, SLA, or general performance claim is made.
