# Upstream watch

Oh My Pi (coding-agent client) connects through OMP NInfer (qualified appliance and release layer)
to NInfer (inference engine) serving Qwen3.8 27B (served model). The runtime ships from downstream
forks; published release **v0.18.0** (2026-11-12) pins unmodified upstream OMP 18.18.7 (`e325ffc7`) and runs all three qualified GPU lanes - the RTX 5090 container runtime (`v0.7.0-qwen38-5090-beta.7`), native Windows RTX 4090 (`v0.8.0-qwen38-4090-beta.3`), and native Windows RTX 3090 (`v0.8.0-qwen38-3090-beta.3`, selected `tc` tensor-core draft-verification build profile) - from one frozen fork engine source `F4` `48c8ac46` (`48c8ac4644322f024b5c3bd5b657af5874567251`, stacked on fork `main` `b871996a` / `F3` `e0971faf`) on upstream `Neroued/ninfer` master `64d10fbf`.
This page names the upstreams we track, runtime fork points, and the current pull-in position. The
watch manifest is [`upstream-watch.json`](../upstream-watch.json); the watch tool is
[`scripts/upstream_watch.py`](../scripts/upstream_watch.py); dated reports land in
[`docs/measurements/`](measurements/).

## Current positions

| Component / upstream | Current position (v0.18.0) | Upstream base / watch head | Evidence and notes |
| --- | --- | --- | --- |
| `can1357/oh-my-pi` (client) | Unmodified upstream **OMP 18.18.7**, source `e325ffc73ab86e03bdd20a91b77d8e2b3964c906`, tree `9ba2abe1f1dd7c64b8d3f99dc0e41d689d96886c`, release `440868478` | Upstream release [`v18.18.7`](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.7) (2026-11-10) | Carries all six `v0.17.0` model and fail-closed fragments unchanged (`tokenizer: qwen3` on opaque `q38-ninfer`, `[low, medium, xhigh]` effort lists, explicit update/setup-wizard opt-outs, exact-loop guard, default async compaction; on Windows, updates the rendered `bash` tool description and `cmd`/MSYS path resolution while keeping JSON tool schemas and the Responses serializer byte-identical to `18.18.6`); accepted across all five `v0.18.0` routes (`PASS 31/31 blocks on 2a735da0, 2026-11-12`); see [client setup](QUICKSTART.md#omp-18187-client), [release notes](../releases/v0.18.0/NINFER_RELEASE_NOTES.md), and [18.18.7 review](measurements/2026-11-11-omp-18187-client-upgrade-review.json). |
| `alphastorm/ninfer` (RTX 5090 container runtime) | `v0.7.0-qwen38-5090-beta.7`, frozen engine source `F4` `48c8ac4644322f024b5c3bd5b657af5874567251` | `Neroued/ninfer` master `64d10fbf9f8e6bfc79ab0570b94674c5b9997929` | Image `496195ec` (reused base `28857182`), server `804ef8ac`, archive `823d9357` (`580,020,196` B), model `81f924d4`, kept profile `qwen38-5090-v0.13.0` (`751d22dc`), DFlash2 draft window 7 (`--lm-head-draft`), BF16 KV (146,368 automatic tokens), two requests in flight, isolated host schema 3 checkpoint directory `checkpoints-v018` mounted at `/checkpoints-v013` (strict origin auth, Device-staged durable `StateImage` saves when Host is full [#89](https://github.com/alphastorm/ninfer/issues/89) / [PR #109](https://github.com/alphastorm/ninfer/pull/109), operation-free prepare holding [PR #111](https://github.com/alphastorm/ninfer/pull/111), bounded `K = 4` fresh-admission priority [#102](https://github.com/alphastorm/ninfer/issues/102) / [PR #108](https://github.com/alphastorm/ninfer/pull/108), bounded resume/fresh admission [#434](https://github.com/Neroued/ninfer/issues/434), byte-proven durable-generation Host reclaim [#78](https://github.com/alphastorm/ninfer/issues/78), export-retirement reservation [#68](https://github.com/alphastorm/ninfer/pull/68), non-blocking export `EXP-105`), serving robustness and inverted malformed tool-history vectors ([#440](https://github.com/Neroued/ninfer/issues/440)/[#441](https://github.com/Neroued/ninfer/issues/441)/[#446](https://github.com/Neroued/ninfer/issues/446), [PR #106](https://github.com/alphastorm/ninfer/pull/106)), host-side NFC rendering, `12/12` `RC2` phases in [`runtime-rc.json`](../releases/v0.18.0/qualification/runtime-rc.json) `ca172838` (separate RDC double build matched `664` artifacts + `3` packages; `RC1`/`RC2` digest difference in [ninfer#120](https://github.com/alphastorm/ninfer/issues/120)), JSON-schema output, 128-character tool names ([receipt](../releases/v0.18.0/qualification/rtx5090.json) `763178cb`). |
| `alphastorm/ninfer` (RTX 4090 and RTX 3090 native Windows runtimes) | Rebuilt RTX 4090 `v0.8.0-qwen38-4090-beta.3` (`ac41700a`, server `a5266ae6`, `native-v0.8.0-beta.3-rtx4090`, config `b71a2cff`, `C1`); rebuilt RTX 3090 `v0.8.0-qwen38-3090-beta.3` (`bf1ceaa9`, server `e5713286`, selected `native-v0.8.0-beta.3-tc-rtx3090`, config `674d5260`, `C2` over one shared 131,072-token pool, 350 W cap); shared source `F4` `48c8ac4644322f024b5c3bd5b657af5874567251` | `Neroued/ninfer` master `64d10fbf9f8e6bfc79ab0570b94674c5b9997929` | Shared published model v3 `81f924d4`, **DFlash2 draft window 7** (`Q4_G64_FP16` draft MLP, host-mapped `token_embedding`, `proposal: "artifact-default"`), `sm_86` small-T tensor-core verify at `T=8/16` enabled on RTX 3090 `tc` ([PR #104](https://github.com/alphastorm/ninfer/pull/104); default-off on RTX 4090), INT8 KV, `Group64` A8 and FP32 head logits off ([PR #112](https://github.com/alphastorm/ninfer/pull/112)), 1,024-token prefill chunk, two extra device-state slots, shared Host budgets (`15,747.734375 MiB` / `20,867.734375 MiB`), `640` / `768 MiB` admission headroom, `30 s` / `180 s` pending timeouts, all `F3` and `F4` engine fixes, native GPU-owner lease restoration on refused `Stop` and exact-byte archiving ([PR #107](https://github.com/alphastorm/ninfer/pull/107), [#91](https://github.com/alphastorm/ninfer/pull/91)), strict-origin schema 3 checkpoints (`session-checkpoints-v3`), CycloneDX 1.5 dependency SBOMs, powered 1,120-prompt `EXP-085` screens (`531c5ed1` / `466586d9`), ABBA speed gates vs published `beta.2` (`1.5373` / `1.3503` on RTX 3090 `tc`; `1.0000` / `0.9992` on RTX 4090), and `3/3` `v0.8.0-beta.2` upgrade/rollback/repair rehearsals per lane ([RTX 4090](../releases/v0.18.0/qualification/rtx4090.json) `165999b9`, [RTX 3090](../releases/v0.18.0/qualification/rtx3090.json) `e7ac3ab7`, [`receipt-audit.json`](../releases/v0.18.0/qualification/receipt-audit.json) `46cf2997`; in `v0.18.0` acceptance on `2a735da0`, both RTX 4090 and RTX 3090 campaigns, public installs and restorations passed without a waiver — RTX 3090 passed every phase in its third execution with a `60 GiB` free-space floor after attempt-1 malformed subagent tool arguments and attempt-2 host disk exhaustion, with `0` HTTP `503` responses in compaction proof `cfa89628`). |
| `Neroued/ninfer` (engine watch) | Shipped container and native runtime base `64d10fbf` in `v0.13.0`–`v0.18.0` (unified across all three GPU lanes at `F4` `48c8ac46` in `v0.18.0`; `F3` `e0971faf` on RTX 5090 and carried `a87de361` native `beta.2` in `v0.17.0`; unified at `a87de361` in `v0.16.2`) | Master `13ebb92f6` (2026-11-11, 33 commits after `77c2e5e2` on 2026-11-07, 291 commits after `64d10fbf` at `77c2e5e2`; `dev` == `master`; [2026-11-10 watch](measurements/2026-11-10-upstream-watch.json), earlier `a754fcf3` on 2026-11-02 and `1882c6ad` / `b57eaddc` in the [2026-10-29 watch](measurements/2026-10-29-upstream-watch.json)) | **Full re-port to `a754fcf3` / `77c2e5e2` / `13ebb92f6` remains deferred** (`9/228` commits apply cleanly in a per-commit merge-tree probe against `a87de361` at `a754fcf3`, estimated 7–10 multi-agent days, low value for dense 27B today); targeted ports for `#434` (`#97`, `#108`), `#446`/`#440`/`#441` (`#98`, plus `4461c9683` malformed tool-history test vectors inverted in `#106`), `#402`/`#403` (`#97`), host NFC (`#96`), default-off prefill pacing (`#95`), and `#89`/`#84` Device-staged saves + `#111` prepare holding ship across all three lanes in `F4` `48c8ac46` (`v0.18.0`). Downstream qualification is bound in [`releases/v0.18.0/qualification.json`](../releases/v0.18.0/qualification.json) (and [`releases/v0.17.0/qualification.json`](../releases/v0.17.0/qualification.json)). |
| `Neroued/ninfer` (Qwen 4 feature watch) | Research only; no source adoption | `feat/qwen4-27b-ops` at `e1874e94` (2026-10-29; unchanged on 2026-11-10), 204 commits after shipped base `64d10fbf` | [2026-11-10 watch](measurements/2026-11-10-upstream-watch.json) and [2026-10-29 watch](measurements/2026-10-29-upstream-watch.json) list all 204 commits (`unknown-truncated` at 300 files). `Qwen4-27B` has no public weights as of 2026-11-11; this branch watch does not change the shipped Qwen3.8 model or engine pins. |
| `sergiuszm/ninfer-4090` (engine watch) | `upgrade-available`; active `sm_89` reference | `rtx4090-port` at `7f47a622` (2026-10-24, 172 commits after 2026-10-07 upstream baseline `81c8ce09`); `master` at `07811ec5` (2026-08-08); side branch `catchup4b` at `4a22fae7` (2026-10-31) | Replaces the inactive `UDPSendToFailed` watch (`5c60b7c9`, 2026-09-09); its old `11aae2d6` fork point remains in the manifest as provenance. Side branch `catchup4b` (`4a22fae7`) ports upstream `Qwen4Exp`/`GLM5Next`/expert cache to Ada (`sm_89`), plus PR `#15` `INT8` group-64 activation prefill (`--prefill-activations a16|int8`, already declined in [EXP-100](PERFORMANCE.md#experiment-ledger)) and `--tolerant-tool-calls` / `tool_constraints=auto`. Watch only; no community runtime is adopted. |
| `ashalliants/ninfer-3090` (active `sm_86` fork watch; supersedes `Don-Chad/ninfer-3090`) | `upgrade-available`; tracked `sm_86` community line | Master `aa6566fc` (2026-11-09, 2,141 commits past `81c8ce09` in the [2026-11-10 watch](measurements/2026-11-10-upstream-watch.json); releases through `v0.17.2-rtx3090` 2026-11-07 on upstream base `f76e19c0`; earlier `d0ff0535` on 2026-11-02 and `f5cec0a6` / `477b2ddc`) | **Supersedes `Don-Chad/ninfer-3090`** (master `115dee6b` on 2026-10-31, 1,912 commits past `ef6ecc3c`, adds only an optional web dashboard since `d8c29253` after [PR #30](https://github.com/Don-Chad/ninfer-3090/pull/30) / `1418aca3`). Apache-2.0 provenance source (`4a178c4b1fd78555b5efd9b07d10d5b1946ca3ad`) for the `sm_86`/`sm_89` small-T tensor-core verify kernel shipped on RTX 3090 `tc` in `v0.18.0` ([`#104`](https://github.com/alphastorm/ninfer/pull/104)) and the default-off `Group64` `A8` prefill kernel guard ([`#112`](https://github.com/alphastorm/ninfer/pull/112)), plus the native head-dim-256 (`D256`) `rk4v4` 4-bit KV codec (`0b4f9588`, `2ba10da2`) evaluated in [EXP-107](PERFORMANCE.md#experiment-ledger). Shipped `v0.18.0` source `F4` `48c8ac46` keeps `--kv-dtype rk4v4` and `Group64` `A8` off in all shipped profiles and adopts no community binary. |
| `iamwavecut/ninfer-all` (consolidation hub watch) | Watch; idea and kernel reference only | Master `64bd1115` (2026-11-11; earlier `8412e774` on 2026-11-10 and `c87b836d` on 2026-10-30) | Multi-architecture consolidation hub (`sm_70`/`sm_75`/`sm_80`/`sm_86`/`sm_89`/`sm_120a`, `sm_86` default build) integrating work from `ashalliants/ninfer-3090`, `UDPSendToFailed/ninfer-4090`, `TertiumOrganum1/ninfer-3090`, `Wallawalla47/infernix`, `13thblade/ninfer-all-nvfp4`, and `IMGillusion/ninfer-disk-kv`. Source of the opt-in `FP32` vocabulary-head logits idea (`2013d01f`) ported into `alphastorm/ninfer` and rejected on RTX 4090 depth-0 case `log-024@0` (`0.9016–0.9025` decode ratio vs `MTP3`, below the `0.95` floor; [EXP-104](PERFORMANCE.md#experiment-ledger)), plus concurrent prefill pacing (`--prefill-stall-budget-ms` / `--decode-rounds-per-prefill`, PR `#195` `c87b836d` / `6152a3fb`, shipped **default-off** in `v0.17.0`–`v0.18.0` via [`#95`](https://github.com/alphastorm/ninfer/pull/95)), host-side TTFT micro-fixes (NFC boundary normalization `4f8d324a` shipped across all three lanes in `v0.18.0` via [`#96`](https://github.com/alphastorm/ninfer/pull/96); `21d8b947`, `79774084`, `51917102`, `f76b614c`, `79d657e0` not adopted), request-scoped non-finite logit faults (PR `#299` `d82ccb4a` / `c8849f1c`, shipped across all three lanes in `v0.18.0` via [`#98`](https://github.com/alphastorm/ninfer/pull/98)), online-softmax history rescaling (PR `#302` `fc884ec5` / `48783e2a`), and `gguf_blocks_v1` conversion. |
| `13thblade/ninfer-all-nvfp4` (non-Blackwell `NVFP4` watch) | Watch; not adopted | Master `9b4b8a00` (2026-11-02; README-only after `245f3ad2` on 2026-10-30) | Implements `NVFP4` 4-bit weights with `FP16` activations (`W4A16`, `--nvfp4-w4a16`) on `sm_75`/`sm_86`/`sm_89`/`sm_120` and 8-bit integer activations (`W4A8-int`, `--nvfp4-w4a8-int`) on `sm_70`/`sm_75`/`sm_80`/`sm_86`/`sm_89`/`sm_120` for GPUs without Blackwell `FP4` tensor cores; any adoption requires independent artifact fit and 1,120-prompt powered quality screening. |
| `IMGillusion/ninfer-disk-kv` / `IMGillusion/ninfer-engine` (disk KV tier watch) | Watch; design reference only | `IMGillusion/ninfer-engine` `main` `ae1ba85a` (2026-11-02; earlier `82e5e826` on 2026-10-30; also `--disk-kv-path` in `troyliu0105/ninfer-all` `81bf00d0` on 2026-11-02, earlier `76940895` / `43c2e163`) | Host/disk L3 KV tier with phased read/write worker pools (`767e67e2`, `92bac11c`), two materialization slots (`8d9b28cb`), device-to-host (`D2H`) spill settlement before staging reuse (`a0e2d900`), and persisting only matchable states. Tracked as a design reference alongside our authenticated schema 3 checkpoint store. |
| `eagle-hq/EAGLE-4` / `EAGLE-Corp/Qwen3.8-27B-EAGLE4` (drafter watch) | Watch; not implemented in NInfer | `eagle-hq/EAGLE-4` `0.1.1` (2026-10-21); `EAGLE-Corp/Qwen3.8-27B-EAGLE4` `f58a5985` (2026-10-19; [Neroued/ninfer#413](https://github.com/Neroued/ninfer/issues/413)) | Autoregressive tree drafter for `Qwen3.8-27B` (`3,089,075,200` BF16 params / `6.18 GB` vs `z-lab/Qwen3.8-27B-DFlash2` `50307d4c` at `1,924,404,480` params / `3.85 GB`, unchanged since 2026-08-19; Hugging Face license field `other` / `eagle-4`, non-Apache-2.0). Watch only until license terms, an engine tree-verify path, and 24 GB fit are established. |

The [2026-11-10 read-only receipt](measurements/2026-11-10-upstream-watch.json) (and earlier
[2026-10-29 receipt](measurements/2026-10-29-upstream-watch.json)) records `Neroued/ninfer`
`master` at `77c2e5e2` (`291` commits past `64d10fbf`, `250` listed), `feat/qwen4-27b-ops`
unchanged at `e1874e94` (`204` commits), `sergiuszm/ninfer-4090` `rtx4090-port` unchanged at
`7f47a622` (`172` commits), `Don-Chad/ninfer-3090` at `115dee6b` (`1,912` commits, superseded by
`ashalliants/ninfer-3090` at `aa6566fc`, `2,141` commits past `81c8ce09`), and client `main` at
`f0200abf28e8`, `4,472` commits after the `v0.14.0` stock OMP 18.12.6 baseline `45c35e40` (before
`v0.15.0` advanced the client pin to `v18.14.0` at `31147f9d`, `v0.16.2` advanced it to
`v18.15.0` at `3fedf8d5`, `v0.17.0` advanced it to `v18.18.6` at `9058ab9d` on 2026-11-10, and `v0.18.0` advanced it to `v18.18.7` at `e325ffc7` on 2026-11-12). Commit and file lists are cut at the GitHub API caps (250 commits /
300 files); no watched client, engine, or fork-network head is an adopted release pin.
Recommendations are commit-subject/path heuristics, not a security assessment or a qualification
result.

## v0.18.0 runtime and client binding

Published release **v0.18.0** (2026-11-12, [release notes](../releases/v0.18.0/NINFER_RELEASE_NOTES.md),
superseding `v0.17.0`) binds all three GPU runtime lanes to one frozen fork engine source `F4`
`48c8ac4644322f024b5c3bd5b657af5874567251` (stacked on fork `main` `b871996a` / `F3` `e0971faf`) on
upstream `64d10fbf` — RTX 5090 `v0.7.0-qwen38-5090-beta.7` (image `496195ec`, server `804ef8ac`,
isolated host checkpoint directory `checkpoints-v018` mounted at `/checkpoints-v013`), native
Windows RTX 4090 `v0.8.0-qwen38-4090-beta.3` (`ac41700a`, server `a5266ae6`,
`native-v0.8.0-beta.3-rtx4090`), and native Windows RTX 3090 `v0.8.0-qwen38-3090-beta.3`
(`bf1ceaa9`, server `e5713286`, selected `native-v0.8.0-beta.3-tc-rtx3090` enabling `sm_86` small-T
tensor-core verify at `T=8/16` in [#104](https://github.com/alphastorm/ninfer/pull/104)) — and
advances the client to unmodified upstream
[`v18.18.7`](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.7) (commit
`e325ffc73ab86e03bdd20a91b77d8e2b3964c906`, tree `9ba2abe1f1dd7c64b8d3f99dc0e41d689d96886c`,
release `440868478`; [18.18.6→18.18.7 review](measurements/2026-11-11-omp-18187-client-upgrade-review.json)).
The runtime delta delivers `v0.17.0`'s `F3` bounded resume/fresh admission, pressure-work waits,
serving robustness, and host-NFC rendering to both native Windows lanes and adds Device-staged
durable `StateImage` checkpoint saves when Host capacity is full
([ninfer#89](https://github.com/alphastorm/ninfer/issues/89),
[PR #109](https://github.com/alphastorm/ninfer/pull/109)), operation-free checkpoint prepare holding
with budget-free `>= 100 ms`-spaced pressure-busy retries
([PR #111](https://github.com/alphastorm/ninfer/pull/111)), bounded `K = 4` fresh-admission priority
at context-operation boundaries
([ninfer#102](https://github.com/alphastorm/ninfer/issues/102),
[PR #108](https://github.com/alphastorm/ninfer/pull/108)), native GPU-owner lease restoration on
refused `Stop` and exact-byte archiving
([PR #107](https://github.com/alphastorm/ninfer/pull/107),
[#91](https://github.com/alphastorm/ninfer/pull/91)), inverted `4461c9683` malformed tool-history
vectors ([PR #106](https://github.com/alphastorm/ninfer/pull/106)), and the `Group64` `A8`
configure guard and Apache-2.0 attribution ([PR #112](https://github.com/alphastorm/ninfer/pull/112)).
Fresh `2026-11-12` acceptance on candidate `2a735da0` passed all five documented routes (`31/31`
blocks), three stock `18.18.7` clients, the **406.876 s** RTX 5090 hold, initial-window RTX 4090
(**509.857 s**), and third-execution RTX 3090 (**`1,439.367` s**) native campaigns,
public-installs, and independent restoration checks without a waiver (on RTX 3090, attempt 1 failed
its post-route subagent check on malformed `task` tool arguments and restored; attempt 2 ran on a
full system drive with `27` OS disk-full error-`112` checkpoint write failures, `capacity` save
refusals, `4` HTTP `503` `deferred by a pending checkpoint save` timeouts, and a `900 s` compaction
timeout before empty-session `Start`/`Stop` recovery; the founder-authorized third execution in
fresh workspaces with an enforced `60 GiB` free-space floor in shared native driver `accept-rtx4090-route.py`'s single
`--attempt 2` rerun slot (the frozen driver accepts only `--attempt 1|2`) passed every phase with `2` committed
compactions in `747.00` s, zero HTTP `503` responses, compaction receipt
`cfa89628`, showing `#89`'s request-level `503` half reproduced in
acceptance only under disk exhaustion). Closed runtime and product councils
are bound in [`review/runtime-ledger.json`](../releases/v0.18.0/review/runtime-ledger.json)
(`05c6b207`; deferred items in [#161](https://github.com/alphastorm/omp-ninfer/issues/161) and
`alphastorm/ninfer` [#115](https://github.com/alphastorm/ninfer/issues/115)–[#118](https://github.com/alphastorm/ninfer/issues/118),
[#120](https://github.com/alphastorm/ninfer/issues/120),
[#121](https://github.com/alphastorm/ninfer/issues/121)).

## 2026-11-11 upstream and fork watch

Observed on 2026-11-11 against fork release source `F3` `e0971faf` (`main` `b871996a`), product
`main` `ea639bb`, and published `v0.17.0` (tag `97dea2f0`):

- **`Neroued/ninfer` master `77c2e5e2..13ebb92f6` (`33` commits since `77c2e5e2` on 2026-11-10):**
  - `77418cfec`: removes `rewrite_execution_boundaries`/`frontiers`, `PrefixExecutionTracker`,
    `prefix_execution_split_after`, `InputWindow::execution_splits`, the rewrite digest domain, and
    the frontier comparison in `matches`/`prefix_equals` (`inspect_prompt_layout` boundaries,
    `encode_rendered_chat` frontier mapping,
    `ResidentPrefixIdentity::{assign, append_generated, truncate, matches, prefix_equals}` frontier
    handling, `append_digest` rewrite mixing, `initialize_forward`'s `next_split`, `validate_work`
    split checks, `input_window`/`window_end` replay splits, `start_control`'s `splits`, and the
    `CommitDecision`/`OutputDecision` field and `Engine` validation), so prefill splits only at
    `prefill_chunk`, capture reservation, prompt end, and vision. It renames
    `rewrite_segments_share_prefill_unit` to `chat_markers_share_prefill_unit` (asserting a chat
    prompt no longer than one chunk completes in one prefill step with
    `processed_prompt_tokens == tokens`), deletes tests asserting that a different Gated DeltaNet
    (`GDN`) decomposition blocks reuse (`test_runtime_mechanisms.cpp` and `GLM` `identities()`), and
    rewrites Jinja scoping (scope chain instead of copying variables) with a lazy `range`.
  - `52e7cd7e0` and `13ebb92f6`: Jinja runtime updates where statements render into one string, loop
    flow uses flags instead of exceptions, and literal constants are cached (`52e7cd7e0`), followed
    by capture-lifetime and iteration fixes, reserved loop-target rejection, and divisor/modulo edge
    cases (`13ebb92f6`; live iteration over a list mutated during the loop visits appended items, and
    `d[1]` vs `d[true]` dictionary-key edge semantics change).
  - `e8059c32b`: admits input-replay captures against cold history, protects other active owners'
    `InputReplay` points (`protected_points`), reserves replacement capacity before retiring old
    snapshots, adds `retry_capture` at committed boundaries and `share_capture` snapshot
    deduplication, and stops skipping a capture on `ContextStart::Deferred`.
  - `41da21f47`: reserves `Control`/`Decode` units before optional capture preparation, falls back to
    another runnable prefill when one prefill's capture waits, frees an unused device reservation in
    `directory.cpp` before the Host fallback, and makes TTFT optional (`null`) in request logs.
  - `4461c9683`: turns malformed or non-object historical tool-call `arguments` into
    `invalid_argument` / HTTP `400` with message, call, and byte position.
  - `9eff5314f`: warms all `C` concurrent inputs instead of `C-1` in `ninfer_bench`.
  - `26` other commits: Spark ops, distributed backends (`src/distributed`), `glm5next` `DFlash2`,
    MoE `FP4`, and `runtime/executor`, including `5` commits (`ad49b325d`, `6a753af33`, `b5008303b`,
    `dc4e789b2`, `d5d535956`) that turn constants (`H4096`, `eps`/`theta`) into
    parameters in upstream `qwen3_5/execution/draft.cpp`, `planning/startup.cpp`, and shared ops
    (`rmsnorm_pack_tail`, `rmsnorm_rope`, `context_kv_materialize`, `candidate_selector`,
    `dynamic_grouped_conv`) for the `GLM` drafter, and `4` commits (`e871c41b1`, `12d5b72ab`,
    `4ac06e5ad`, `b5008303b`) that change pairwise partial-reduction storage in the shared `BF16`
    sliced-K kernel (`src/ops/linear/kernels/bf16`). Upstream test results, blob-level pre-image
    identity, and upstream issue [`#446`](https://github.com/Neroued/ninfer/issues/446)'s text were
    not verified in the read-only clone; commit messages for `77418cfec`, `52e7cd7e0`, `41da21f47`,
    and `9eff5314f` are empty so upstream states no numbers for them, and the `26` other patches
    were inspected through the stat file and their `src/models/qwen3_5`,
    `src/ops/linear/kernels/bf16`, and `src/runtime` hunks only.
- **Classification of `77c2e5e2..13ebb92f6` and `v0.18.0` runtime dispositions (adopt now, defer,
  reject):**
  - *Adopt now:* only `4461c9683`'s bad-argument vectors (`{"x": nope}`, truncated JSON, `[]`,
    `null`, `1e99999`) are adopted, inverted as regression tests in
    `tests/models/common/qwen/test_frontend.cpp` and `test_serve_resilience.cpp` asserting `F3`'s
    lenient `{"input": raw}` rendering and ordered-object preservation. Because nothing in the `33`
    upstream commits fixes the RTX 3090 compaction dead-end
    ([`alphastorm/ninfer#89`](https://github.com/alphastorm/ninfer/issues/89)) or the arrival wait
    ([`alphastorm/ninfer#102`](https://github.com/alphastorm/ninfer/issues/102)), `v0.18.0` builds
    all three lanes (native Windows `v0.8.0-qwen38-{3090,4090}-beta.3` and RTX 5090
    `v0.7.0-qwen38-5090-beta.7`) from one planned common fork engine source `F4` carrying
    fork-owned fixes: device-staged state-image export fallback when the Host arena is full
    (`~196 MB` state images, with save-refusal reasons recorded in receipts, folding
    [`alphastorm/ninfer#84`](https://github.com/alphastorm/ninfer/issues/84)) for
    [`#89`](https://github.com/alphastorm/ninfer/issues/89), a bounded fresh-admission attempt at
    context-operation boundaries for [`#102`](https://github.com/alphastorm/ninfer/issues/102),
    native controller GPU-owner lease restoration after a proven-stopped incomplete shutdown plus
    uninstall task absence and junction containment
    ([`alphastorm/ninfer#87`](https://github.com/alphastorm/ninfer/issues/87) items 1 and 3),
    exact-byte package digest archiving
    ([`alphastorm/ninfer#91`](https://github.com/alphastorm/ninfer/pull/91)), product release-tooling
    fixes ([`alphastorm/omp-ninfer#149`](https://github.com/alphastorm/omp-ninfer/issues/149) items
    `T1`–`T6`, `T8`, `T10`, `T12`), stock Oh My Pi
    [`v18.18.7`](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.7)
    (`e325ffc73ab86e03bdd20a91b77d8e2b3964c906`), and gated performance levers that ship default-on
    only if they pass preregistered bars (RTX 5090 cadence-only prefill pacing `0 / 32` via
    `--prefill-stall-budget-ms 0` and `--decode-rounds-per-prefill 32`, RTX 5090 `Group64` A8
    prefill at a `512`-token minimum pass width, RTX 3090 tensor-core verify at verify width
    `T=8/16`, RTX 3090 `Group64` A8 prefill for passes above `32` tokens, and an RTX 4090
    tensor-core verify prescreen).
  - *Defer and why:*
    - `77418cfec` (warm-turn prefill split removal): `F3` records an execution boundary after every
      assistant opener, after `<think>\n`, and after the canonical reasoning close
      (`prompt_layout.cpp:91-104`, `prefill.cpp:627-637`, `replay.cpp:49-50,196-200`,
      `output_session.cpp:119,520,658`, `commit.cpp:120-146`, `engine_core.h:1223-1233,2501-2519`),
      which in [EXP-059](PERFORMANCE.md#experiment-ledger) split a `~400`-token warm turn at
      `~25K`–`29K` context into six passes across `283–307 ms` where the four `2–3`-token fragments
      cost `59–60 ms` and folding six passes into two was estimated at `115–130 ms` (`-0.06` to
      `-0.13 s`, or `-23%` to `-49%` `[derived]` against recent RTX 5090 strict-warm TTFT p50
      `0.265 s` at `474` computed tokens in [EXP-110](PERFORMANCE.md#experiment-ledger); the
      `EXP-059` trace predates `DFlash2` draft-context materialization so the saving may be larger
      `[INFERENCE]`, and native-lane savings in ms are probably larger `[INFERENCE, unmeasured]`).
      Adopting `77418cfec` is **deferred** to a non-gating stretch branch and a later release
      because (1) removing the separate `2`-token `<|im_start|>assistant\n<think>\n` final pass
      (`qwen3_8.jinja:177-183`) and historical assistant splits changes output tokens
      (`output-changing`, requiring the `EXP-085` 1,120-prompt powered quality screen per lane) and
      (2) `DurableIdentity` serializes `execution_frontiers` in schema 3 checkpoints
      (`checkpoint_codec.cpp:25-26,174-178`), re-injects them on import
      (`checkpoint_api.cpp:153-154`), and mixes them into the shortlist digest
      (`durable_checkpoint_set.h:58-62`, `prefix_identity.cpp:114-117`), so removing them requires
      bumping `kIdentityCodec` (`qwen-identity/1` in `prefix_identity.h:18`), which invalidates the
      durable identity of every session saved under `v0.17.0` or `beta.2` and forces a cold
      first turn on upgrade ([`alphastorm/ninfer#46`](https://github.com/alphastorm/ninfer/issues/46)
      is untouched, and [`#60`](https://github.com/alphastorm/ninfer/issues/60)'s
      checkpoint-boundary vs `1,024`-chunk mismatch remains even though the restored arm's
      `18/2/3/4`-token suffix fragments in `EXP-116` collapse to one pass).
    - `e8059c32b` and `41da21f47` (pressure-path capture retention and prefill fallback):
      **deferred** (`e8059c32b` subset as stretch; `41da21f47` deferred) because both target
      upstream's `session/*` and `ContextDirectory` architecture (`F3` has no `ReclaimSelection`,
      `CaptureStorage`, `ContextStart`, or context maintenance, and the corresponding `F3` functions
      `prepare_semantic_capture`, `reserve_active_capture`, `capture.cpp`,
      `resource_manager.h::recycle_input/capture_admission`, and `reserve_resident_units` sit next
      to council-remediated `F2`/`F3` durable-save and export-wait code), neither fixes
      [`#89`](https://github.com/alphastorm/ninfer/issues/89) (which had `0` running, prefilling, or
      paused requests, `2,032/2,048` KV page groups, `4/4` device state slots, and `390 MiB` Host
      free) or [`#102`](https://github.com/alphastorm/ninfer/issues/102) (whose leading inferred
      gate is a resident-reservation `DemoteOperation` holding the single context-operation slot
      with no fresh-admission retry `[INFERENCE]`; whether `e8059c32b`'s
      `preserve_capture`/`capture_victims` reduces optional demotions is unproven `[INFERENCE]`),
      and neither defect appeared in recent production logs (`180/180` completions with `0`
      preemptions and `0` `paused_ns`).
    - Jinja runtime chain (`52e7cd7e0`, `13ebb92f6`, and the `third_party/llama-jinja` hunks of
      `77418cfec`): **deferred** because host-side template rendering takes `~1.16 ms` per
      `500K`-character render on this base (worth `~1 ms` or less per render), `13ebb92f6` must
      travel with the first two commits to fix capture-lifetime bugs they introduce, and edge
      semantics (`d[1]` vs `d[true]`, live iteration over mutated lists) change.
    - `feat/qwen4-27b-ops` (`e1874e94`): **deferred** (kept on watch) because the branch has not
      moved since `2026-10-29`, no public `Qwen4-27B` weights exist, upstream has no dense model
      layer or converter, and its `K8V4` KV kernel is tied to query-sparse attention (`QSA`).
  - *Reject and why:*
    - `4461c9683` (returning `invalid_argument` / HTTP `400` on malformed or non-object historical
      tool `arguments`): **rejected** because a stock Oh My Pi client resends the whole stored
      conversation history every turn, so one malformed historical tool call makes every later turn
      return HTTP `400` until the user rewrites history (moving
      [`Neroued/ninfer#446`](https://github.com/Neroued/ninfer/issues/446) from HTTP `500` to HTTP
      `400`); `F3` retains non-throwing `{"input": raw}` wrapping (`src/text/tool_arguments.cpp:5-12`)
      and its `Custom`-tool branch (`src/models/common/qwen/frontend/chat_template.cpp:263-265`,
      `tests/models/common/qwen/test_frontend.cpp:2222`).
    - `9eff5314f` (`ninfer_bench` warming `C` inputs instead of `C-1`): **rejected** because `F3`'s
      `ninfer_bench` has a different design (`bench/inference/ninfer_bench.cpp:263`) and product
      scripts do not call it.
    - `41da21f47`'s nullable-TTFT request-log change: **rejected** unless product log reducers are
      updated with it.
    - Remaining `26` commits (Spark ops, distributed backends, `glm5next` `DFlash2`, MoE `FP4`, the
      `5` `DFlash2` draft-path op generalizations `ad49b325d`, `6a753af33`, `b5008303b`,
      `dc4e789b2`, `d5d535956`, and the `4` `BF16` sliced-K partial-reduction commits `e871c41b1`,
      `12d5b72ab`, `4ac06e5ad`, `b5008303b`): **rejected** because `F3` has no `src/distributed`,
      `glm5next`, or `runtime/executor`, and the draft-op and `BF16` sliced-K refactors do not help
      `H5120` on `sm_120`/`sm_89`/`sm_86` while risking `DFlash2` token
      identity.
- **Community fork deltas (`iamwavecut/ninfer-all`, `ashalliants/ninfer-3090`, and other watched
  forks):**
  - `iamwavecut/ninfer-all` `8412e774..64bd1115` (`28` commits: `16` non-merge, `12` merges
    `#307`–`#318`; `0` commits carry a measured dense-`Qwen3.8-27B` speed number, with the only
    benchmark in the range in `31171f52` for Flash-Next/DeepSeek on an RTX A6000):
    - *Stop-string state hold (`52dfc488`, test `9fbb8098`, docs `6464c9de`, merge `#307`
      `857d172`):* folds one extra `StateImage` per request (`C` extra device state images across
      `C` concurrent requests) ahead of the round's normal fold and rewinds on a stop-string cut
      (`stop_hold_rewind`) when a stop string spans decode rounds; `F3` commits only to
      `match.committed_tokens` (`src/models/common/qwen/frontend/output_session.cpp:560-566`,
      `src/runtime/engine/engine_core.h:1221-1233`, `src/runtime/contract/execution.h:49-53`) with
      no hold or rewind `[INFERENCE: the consequence is a lost endpoint and a re-prefill of the tail,
      not wrong output]`. Deferred: no measured numbers are published, it costs `C` extra device
      state images, and whether stock OMP emits `stop_string`/`stop_sequences` is unverified.
    - *Exact in-pass prefix-cache tap (`458d8fb8`, docs `a1f37fbd`, merge `#308` `4d6327d`):* splits
      each Gated DeltaNet layer's convolution and recurrence at up to four tap columns per chunk
      (`TextContext::gdn_mix`) instead of ending the chunk at the tap; **deferred** (stretch)
      because `F3` has no hybrid cache (`hybrid_program`, `tap_planner`, `TapPlacement`,
      `hybrid_lane`, `use_alt_prefix` absent) and captures checkpoints by chunk split
      (`src/models/qwen3_5/program/prefill.cpp:80-83,618-622`), and no speed numbers are published.
    - *`bf16p` lossless packed `BF16` KV rows (`cc65dbb3`, merge `#316` `6e71b0ed`):* packs a
      `512 B` `D256` `BF16` KV row into `392 B` (`256 B` sign+mantissa, `128 B` 4-bit exponent
      offsets, `8 B` side record; `23%` fewer KV bytes, capacity only with no speed claim) and turns
      a row needing more than six exponent escapes into a poison row decoding to `NaN` that ends the
      request; **deferred** because `F3`'s `KvCacheStorage` (`include/ninfer/types.h:29-34`) has
      five values and no packed form, every `BF16` attention decode path (`prompt_bf16`,
      `small_t_bf16`, `sparse_attention`) would need the codec, and the poison-row escape case is
      output-changing.
    - *Remaining `19` commits:* lookup copy cursor (`e813b68d`, merge `#314` `ceefc03f`), multi-GPU
      hybrid prefix cache (`af60c489`, `38a10aa4`, merge `#309` `06e54f66`), build-graph changes
      (`95d58aee` merge `#311` `7d9ef4a5`, `092893a9` merge `#312` `faf65e4f`), DeepSeek and
      Flash-Next MoE (`a8cc8401` `#310` `8b792715`, `283072a1` `#313` `6ed13c35`, `05c4d195` `#315`
      `a4149d2f`, `31171f52` `#317` `53dd1936`), and the built-in RTX A6000 device profile
      (`9538a2dc` `#318` `64bd1115`) are **rejected** as inapplicable (`F3` has no lookup drafting,
      hybrid prefix cache, multi-GPU pipeline/TP, `ninfer_core_device`, `NINFER_WINDOWS_KERNEL_DLL`,
      or RTX A6000 lane; the `--use-alt-prefix-caching` hybrid cache itself, which reports an RTX
      3090 27B `rk4v4` `131K` agentic replay at `55.6 s` vs `97.9 s` average TTFT, `84%` vs `46%`
      cached prompt tokens, `43.6` vs `60.2` minutes, one history-edit turn at `389 s` vs `183 s`,
      and `1.4%` slower decode against the catalog, is an XL subsystem not scoped for `v0.18.0`).
  - `ashalliants/ninfer-3090` branches (`2026-11-10` / `2026-11-11`):
    - *`perf/adaptive-dflash-k` (`4ff617181`, `5dd329830`, `c385455b`):* captures a second `DFlash2`
      round family at `K=3` beside `K=7` with a per-round acceptance/cost policy
      (`speculative/draft_window_policy.h`, `5%` margin / `8`-round dwell hysteresis; single-lane
      RTX 3090 27B `DFlash2` low-acceptance basis `24.1 / 26.8 / 31.0 ms` rounds and
      `58.9 / 53.2 / 46.1 tok/s` at `K=3/7/12`, geometric model crossover near `55%` acceptance and
      `~10%` gain at `30%`, while `TODO.md` states `"Nothing here has run on a GPU"` `[INFERENCE]`).
      **Rejected / deferred** for `v0.18.0` because low-acceptance decode is `<= 0.6%` of decode
      time (`EXP-110`), `F3` has no `SpeculativeRoundShape` round-family machinery, a second
      CUDA-graph family is charged like the wide family (`startup.cpp`), and changing verify width
      alters batch arithmetic (`output-changing`).
    - *`feat/basalt-learnings` (`5ccab0c5c`, `2026-11-11`; doc commits `d734acd4b`, `a94fc0783`,
      `7fb902d91`, `52b131553`, `5ccab0c5c`, plus `b654456b7` and `cd596378c`):* **rejected /
      deferred** for `v0.18.0` because `--relaxed-drafting` (`cd596378c`) changes the output
      distribution (`<= 0.6%` of decode) and `--draft-context-rows` (`b654456b7`) is refused above
      one lane (its `docs/serving.md` figures were not in the log-only bundle and are unverified).
    - *`feat/sensitivity-allocation` (`66e31f3b6`):* `allocation.py` and
      `allocation_activations.py` Q4/Q5 layer assignment for the `128` `attention/output`,
      `gdn/output`, and `mlp/down` projections (`4.641 / 4.640 GB` vs `4.643 GB`); **deferred**
      because both candidates are explicitly unvalidated (`"not yet measured with KLD or on a GPU"`)
      and require artifact re-quantization and re-qualification.
    - *`feat/numeric-tripwire` + `fix/tripwire-fp16-bits` (`235061874`, `1f4dffba2`, `2855914c7`,
      `bd97f346e`, `e6bcb8df7`), `fix/engine-scheduling-context-store-tests` (`83ea5e315`), and
      `perf/expert-cache-windowed-policy` (`4e576c094`):* diagnostic/test or MoE-only (`dense 27B`
      has no expert cache).
  - *Other community forks (commit subjects only; diffs were not materialized and are unverified):*
    `IMGillusion/ninfer-engine` (`ae1ba85a6` single-pass probe walk, `f9ba4cc98`, `658138370`,
    `a42934545`, `767e67e26`, `28aa9e2d9` L3 disk KV), `troyliu0105/ninfer-all` (`81bf00d09` device
    KV pool usage log), `13thblade/ninfer-all-nvfp4` (`9b4b8a007`, `269d3b193`, `7d7ca4877`,
    `a677ba59b`, `75bffc0b2` `NVFP4` `W4A16`/`W4A8-int` and tensor parallelism),
    `Don-Chad/ninfer-3090` (`115dee6b4` Studio dashboard and Windows launcher), and
    `Saylek-ai/ninfer` (`a754fcf3b`, `c5627cdd5`, `45f742877`, `2cf044529`).
- **Oh My Pi [`v18.18.7`](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.7)
  (`2026-11-10T20:23Z`) and client compaction audit:**
  - `v18.18.7` (`e325ffc73ab86e03bdd20a91b77d8e2b3964c906`, `64` commits ahead of `v18.18.6`
    `9058ab9d`, `behind_by: 0`) touches no path under `packages/ai/src/providers/`, `compaction/`,
    `tokenizer.ts`, `session-maintenance.ts`, `session-migrations.ts`, retry classifiers, or
    edit/write/read tool prompts (`packages/catalog/src/compat/resolve.ts` and `hosts.ts` add
    `x-session-id` for Morph only; `taxonomy/meta.kdl` and `models.json` add `muse-ember`;
    `prompts/tools/bash.md` and `crates/pi-shell/src/cmd_dialect.rs` add a Windows-only bash prompt
    sentence and `cmd`-dialect `System32` resolver; remaining commits cover LiteLLM usage budgets,
    per-window saved-reset redemption, `session_before_shutdown`, collab backpressure, `grep`
    0-match rendering, and an Antigravity login warning). While the initial client review
    recommended keeping `18.18.6` (`9058ab9d`, tree `fd379b65`) to avoid a full re-pin cycle,
    founder decision adopts stock OMP `18.18.7` for `v0.18.0`.
  - Compaction audit on `18.18.6`: `contextTokens = max(billed provider context, local stored
    estimate)` (`packages/agent/src/compaction/compaction.ts:379-381`, called at
    `session-maintenance.ts:3570`) triggers at `resolveThresholdTokens = 131,072 - max(15%, 16,384)
    = 111,412` (`compaction.ts:328-330,394-421`), and `maybeStartSpeculativeCompaction`
    (`session-maintenance.ts:2298-2345`) fires inside the pre-threshold band `[97,486, 111,412)`
    where `lead = clamp(threshold * 0.125, 8,192, 32,000) = 13,926`
    (`packages/coding-agent/src/session/speculation-lead.ts:1-24`), selecting `handoff`
    (`toolChoice: "none"`, output budget `32,768`, `compaction.ts:1095-1155`) from
    `compaction.methodOrder` (`["remote","snapcompact","handoff","shake","soft"]`,
    `compaction-methods.ts:49-55,119-140`). The `37,277 → 78,107` local-estimate jump between
    `18.15.0` and `18.18.6` on opaque `q38-ninfer` (`2.10×`) was the `bytes/4` → `o200k_base`
    fallback change (`packages/agent/src/tokenizer.ts:87-94,283-285`; whether `qwen3` counting on
    the opaque alias would raise or lower `78,107` is unmeasured `[INFERENCE]`, and the `18.15.0`
    `#estimateStoredContextTokens` body was read from derived diffs rather than a source tree),
    which cannot move a `max(billed, stored)` trigger when billed context was `~79K` (`79,164` at
    the last completed turn, below `97,486`; rejected-request prompt sizes and arrival timestamps
    are unlogged `[INFERENCE]`). Profile workarounds on the RTX 3090 (`compaction.asyncEnabled:
    false`, local-first `compaction.methodOrder`, or a `~60K` `thresholdTokens` cap) are
    **rejected / deferred** because they mask the
    [`alphastorm/ninfer#89`](https://github.com/alphastorm/ninfer/issues/89) durability cycle (`0`
    resident requests, `2,032/2,048` device page groups, `21,872,391,168 / 21,881,405,440` Host
    bytes / `390 MiB` Host free across `179` samples) and
    `scripts/hosts/accept-rtx4090-route.ps1:356-359` forbids disabling async compaction to pass the
    gate.
- **Hugging Face artifacts, models, and external serving techniques:**
  - `neroued/*` Hugging Face artifacts remain at `lastModified 2026-10-29T09:22Z` (`Qwen3.8-27B` v3
    `81f924d4` unchanged), `Neroued/ninfer` GitHub releases return `[]`, and the `Qwen`
    organization's newest update is a `2026-11-07` metadata refresh of the `3.8` family with no
    public `Qwen4-27B` weights or repository. Same-architecture 27B derivatives
    `NousResearch/Arete-27B` (SFT-only, `apache-2.0`, model card reports Terminal-Bench 2.1
    `67% → 70%` and Hermes `65.77 → 65.60` with `"we do not take credit for any seeming
    improvement"`, published NInfer conversion `DAXZEIT/Arete-27B-NInfer-v3` /
    `Arete-27B-Q4_K_M-text-vision-Q8-mtp-Q6_K*` in unloadable GGUF blocks) and
    `ConceptCountry/qwen-concept-27b` (weight-edited, `apache-2.0`, `59K` downloads, no published
    coding benchmarks), plus new `DFlash` drafters in compressed-tensors / Quark / ROCm formats
    (`nchapman/Qwen3.8-27B-DFlash2-W4A16-HGPTQ`, `amd/Qwen3.8-27B-Quark-DFlash2`,
    `StillDeadcode/qwen3.8-27b-iq8r-dflash` vs our `Q4_G64_FP16` draft MLP), are **deferred**,
    closing the model replacement watch for `v0.18.0`.
  - Recent `v0.13`–`v0.16.2` filtered traffic (`n=176`, [EXP-110](PERFORMANCE.md#experiment-ledger))
    is `50.21%` prefill, `31.89%` decode, `8.16%` queue, and `3.65%` prepare (against `69.42%`
    decode / `28.58%` prefill in the `v0.10.0+` cohort), with decode at `~77%` of the weight-read
    floor and prefill at `74%` of the dense `BF16` FLOP floor (`MLP` `gate`/`up` at `81.7%`,
    [EXP-059](PERFORMANCE.md#experiment-ledger)). `v0.18.0` gates `Group64` A8 prefill on RTX 3090
    and RTX 5090 (SmoothQuant `arXiv:2211.10438` reports up to `1.56×`, and QServe
    `arXiv:2405.04532` reports `1.2–1.4×` at 8B and `2.4–3.5×` at 72B over TensorRT-LLM on
    A100/L40S, not verified on our engine or a dense 27B model; RTX 4090 A8 stays off at its
    `1.0985 / 1.10` leak bound) and two-request (`C2`) cadence-only prefill pacing (`0 / 32` via
    `--prefill-stall-budget-ms 0` and `--decode-rounds-per-prefill 32`; Sarathi-Serve
    `arXiv:2403.02310` reports `2.6×` capacity on Mistral-7B/A100 and `3.5×` at a `100 ms` SLO on
    Yi-34B) on preregistered bars, runs tool-call-span copy-drafting replay (SuffixDecoding
    `arXiv:2411.04975` reports up to `5.3×` on AgenticSQL, `~2.5×` on SWE-Bench, `2.8×` over
    EAGLE-2/3, and `6.3–7.8` mean accepted tokens/step from its abstract and project page, not
    verified against a neural block drafter on our corpus), restore-preparation instrumentation
    ([`alphastorm/ninfer#59`](https://github.com/alphastorm/ninfer/issues/59)) and readiness
    attribution (`cuCheckpointProcess*` is Linux-only in NVIDIA driver docs and untested in our
    WSL2/Docker lane `[INFERENCE]`), `rk4v4` cheap deciders (`~31` GPU-hours for full qualification
    on the single native host), byte-identical `pad16` / 2-stage native verify schedules (`~1–3%`),
    and RTX 3090 locked-clocks screening (`nvidia-smi` persistence mode is Linux-only and GeForce
    `-lgc`/`-lmc` `P2` hold is not verified at vendor source) in non-gating stretch slots, and
    **defers or rejects** token-tree verification in 8 columns (Medusa and EAGLE-2/3 use `32–64`
    verify nodes and EAGLE-3 `arXiv:2503.01840` abstract-level claims report `3.0–6.5×` over vanilla
    with mean accepted length `7.5`, not verified for 8 columns), typical acceptance (Medusa
    `arXiv:2401.10774`, gain unknown for an 8-column block drafter and reduces to greedy at
    temperature `0`), KIVI-style asymmetric KV compression (`arXiv:2402.02750`, `2.35–3.47×`
    throughput and `2.6×` memory reduction at `<= 2%` LM-Eval drop), CUDA-graph/launch-overhead
    reduction (`815` kernel boundaries at `0.21 µs` = `169.5 µs` of a `17.7 ms` round, `<= 1%`
    decode, `99.2%` GPU busy, PDL `4.7–6.2%` slower in `EXP-054`/`EXP-058`), prefill/decode
    disaggregation, SGLang RadixAttention (`arXiv:2312.07104`; our cached token share is already
    `91.32%`), EAGLE-3 trained drafters, `cuBLAS` `INT8` prefill, the
    [`alphastorm/ninfer#50`](https://github.com/alphastorm/ninfer/issues/50) hold state machine
    ([`alphastorm/ninfer#66`](https://github.com/alphastorm/ninfer/pull/66) closed),
    [`alphastorm/ninfer#72`](https://github.com/alphastorm/ninfer/pull/72) (closed, no consumer
    since `#58` was dropped), RTX 3090 prefill pacing (no config key or baseline),
    [`alphastorm/omp-ninfer#28`](https://github.com/alphastorm/omp-ninfer/issues/28) (closed as not
    planned), and RTX 5080; see [`ROADMAP.md`](../ROADMAP.md#deferred-and-rejected-decisions).

## 2026-11-10 upstream and fork watch

Observed on 2026-11-10 (companion watch receipt:
[`2026-11-10-upstream-watch.json`](measurements/2026-11-10-upstream-watch.json)):

- **`Neroued/ninfer` master `77c2e5e2` (2026-11-07):** `291` commits past our merge base `64d10fbf`
  (`250` listed before the GitHub API cap) and `63` commits after `a754fcf3` (`compare/a754fcf3...77c2e5e2`
  reports `ahead_by: 63` and returns `62` commit objects; `dev` equals `master`). Upstream
  [`#434`](https://github.com/Neroued/ninfer/issues/434) (request starvation under context pressure)
  was closed on 2026-11-07 by `77c2e5e2` (`fix(runtime): recover preempted requests without stalling`,
  `+818`/`-154` across `34` files, validated upstream on RTX 5090 / `Qwen3.8-27B` `NVFP4` for `none`,
  `MTP`, and `DFlash2`) and PR [`#443`](https://github.com/Neroued/ninfer/pull/443)
  (`src/models/qwen3_5/session/binding.cpp`, `+4`/`-1`): `plan_binding` drops the `source &&`
  conjunct (`resume_without_replay = resume && actual->reused_tokens == resume->frontier()`) and
  `install_binding` enforces `tx.reuse_frontier < saved.frontier`, so a request paused at frontier `0`
  with no reused prefix resumes directly into its saved `Prefill`/`Decode`/`Control` lifecycle
  (`RecoveryProgress` routes `None`/`Direct`/`Snapshot`/`Replay`) instead of entering an
  unsatisfiable `[0, 0)` `Lifecycle::Replaying` loop that pins `recovery_pending` forever and blocks
  fresh admission. `77c2e5e2` also splits `Engine::request_stop()` and `HttpServer::stop()` worker
  joining (moving `SIGINT`/`SIGTERM` to a `10 ms` `std::jthread` polling an `atomic<bool>`) and adds
  recovery observability (`direct_restores`, `replayed_tokens`, `last_progress_ns`, `progress_owner`,
  `| replay <tok/s>`, request-log schema `31` → `32`).
- **Classification of `a754fcf3..77c2e5e2` for the dense `Qwen3.8-27B` product:** only `77c2e5e2`
  (+ PR [`#443`](https://github.com/Neroued/ninfer/pull/443)) is **adopt-now** (zero-frontier
  direct resume and bounded fresh-admission rotation in
  [`alphastorm/ninfer#97`](https://github.com/alphastorm/ninfer/pull/97) plus graceful shutdown
  stop/join split in [`alphastorm/ninfer#98`](https://github.com/alphastorm/ninfer/pull/98),
  integrated in `F` `a3fa0550` [`#99`](https://github.com/alphastorm/ninfer/pull/99) and
  council-remediated in `F3` `e0971faf` [`#101`](https://github.com/alphastorm/ninfer/pull/101),
  shipped in RTX 5090 `v0.7.0-qwen38-5090-beta.6` in `omp-ninfer` `v0.17.0`, published 2026-11-10;
  the separate arrival source-wait probe [`#100`](https://github.com/alphastorm/ninfer/pull/100) was
  closed unmerged and is tracked in [`alphastorm/ninfer#102`](https://github.com/alphastorm/ninfer/issues/102));
  `5` architecture-neutral `BF16` linear kernel retunes (`a1ac2ae3`, `a18bb379`, `b3902de4`,
  `6321a8f3`, `9f274245` in `src/ops/linear/kernels/bf16/*` and `projection/bf16`, gated on a
  one-off artifact `BF16` tensor-shape audit) and `1` `Q4_G64_FP16` draft-head staging commit
  (`5ea2ce50` under `projection/q4/dgx_spark/shapes/n77440_k4096.cu`, absent from the fork's `q4`
  shape family) stay on **watch**; the remaining `55` commits in the `62`-object compare payload —
  `2` native `FP4-Local` checkpoint import and inference-kernel commits (`d49b9af7`, `7fdc0eca` for
  `GLM5Next` on DGX Spark `sm_121a`), `6` MoE commits, `5` `NVFP4` linear commits, `18` `MXFP8`
  linear/split commits, `6` `Block-FP8` linear/split commits, `4` `SwiGLU` `fp8_block`/`A8` commits,
  `13` vision/`KDA`/clamped-`A8`/`kpool`/`mhc`/Spark commits, and `1` formatting commit — are **not
  applicable** to our dense `groupwise-int` `Qwen3.8-27B` runtime (per-commit path inspection
  confirms none touch the `q4`/`q5`/`q8` groupwise kernels our main linears use, whereas the
  `64d10fbf...77c2e5e2` watch receipt truncates aggregate file lists at GitHub's 300-file cap).
- **Shipped-fork defects audited on `a87de361` (remedies for `#446`, `#440`, `#441`, and
  `#402`/`#403` all shipped on the RTX 5090 lane in `v0.7.0-qwen38-5090-beta.6` / `F3` `e0971faf` in
  `omp-ninfer` `v0.17.0`, published 2026-11-10, via
  [`alphastorm/ninfer#97`](https://github.com/alphastorm/ninfer/pull/97) and
  [`#98`](https://github.com/alphastorm/ninfer/pull/98); only the carried native `v0.8.0-beta.2`
  runtimes remain on `a87de361`):**
  - [`Neroued/ninfer#446`](https://github.com/Neroued/ninfer/issues/446) (open):
    `src/models/common/qwen/frontend/chat_template.cpp:225-231` on `a87de361` re-renders historical
    assistant `tool_calls` with a throwing `Json::parse(call.arguments_json)`, so one malformed
    tool-call argument string emitted on an earlier turn throws `nlohmann` `parse_error.101` and
    returns HTTP `500` on every subsequent turn in the conversation (and
    `src/serve/anthropic_messages_response.cpp:37-41` throws `std::logic_error` on non-object
    Anthropic tool input); non-throwing raw-input preservation shipped in
    [`alphastorm/ninfer#98`](https://github.com/alphastorm/ninfer/pull/98) (`F3` `e0971faf`, RTX
    5090 `v0.7.0-qwen38-5090-beta.6` in `v0.17.0`).
  - [`Neroued/ninfer#440`](https://github.com/Neroued/ninfer/issues/440) and
    [`#441`](https://github.com/Neroued/ninfer/issues/441) (both closed upstream on 2026-11-07):
    `tools/chat_templates/qwen3_8.jinja:54` (and the template embedded in model v3 `81f924d4`)
    accepts only `('xhigh', 'medium', 'low')` and returns HTTP `400` (`invalid prompt`) on `a87de361`
    when a client sends `reasoning_effort` values `high`, `none`, `minimal`, or `max` (`#440`), while
    `src/models/common/qwen/frontend/chat_template.cpp:91-93` throws
    `reasoning_effort conflicts with enable_thinking` when Anthropic-style
    `thinking: {type: "disabled"}` is combined with `output_config.effort` (`#441`);
    artifact-template-aware effort normalization (mapping `minimal → low` and `high`/`max → xhigh`)
    and ignoring effort when thinking is explicitly disabled shipped in
    [`alphastorm/ninfer#98`](https://github.com/alphastorm/ninfer/pull/98) (`F3` `e0971faf`, RTX
    5090 `v0.7.0-qwen38-5090-beta.6` in `v0.17.0`).
  - [`Neroued/ninfer#402`](https://github.com/Neroued/ninfer/issues/402) /
    [`#403`](https://github.com/Neroued/ninfer/pull/403) (closed upstream on 2026-10-29/30 as
    superseded by `452c3f5f` on 2026-10-17, after our `64d10fbf` merge base): in
    [`alphastorm/ninfer#93`](https://github.com/alphastorm/ninfer/pull/93) commit `8d7397bd5`
    (ported without upstream's unified-storage `RecoveryIndex`),
    `src/models/common/context/recovery_loss.h:23-46` initially called
    `std::find(ordered.begin(), ordered.end(), retained)` inside the survivor loop ($O(n^2 \cdot m)$,
    causing `~0.75 s` serving-thread stalls every `~1 s` at `~370` retained checkpoints / `81 GiB`
    Host context); [`alphastorm/ninfer#97`](https://github.com/alphastorm/ninfer/pull/97) (`E1`,
    shipped in `F3` `e0971faf`, RTX 5090 `v0.7.0-qwen38-5090-beta.6` in `omp-ninfer` `v0.17.0`)
    replaced that `std::find` with an expected-$O(1)$ `unordered_set` removed-handle membership check
    (`src/models/common/context/recovery_loss.h`, CPU proof at `32` removed / `256` survivors:
    `246,768 → 224` comparisons), leaving the old lookup only in the carried native `v0.8.0-beta.2`
    packages (`a87de361`).
  - Other upstream issues audited: [`#396`](https://github.com/Neroued/ninfer/issues/396)
    (`128`-character tool names) is already in `a87de361` and `F3` `e0971faf`;
    [`#439`](https://github.com/Neroued/ninfer/issues/439) (`sm_120a` RTX 5090D startup crash in
    `decode_graph.cpp:19` `cudaGraphAddChildGraphNode` at `a754fcf3`) is absent from `a87de361` and
    `F3` `e0971faf`; [`#445`](https://github.com/Neroued/ninfer/issues/445)
    (event-driven CUDA completion wakeups reducing `12.63M` `cudaEventQuery` calls / `~4.36 s` CPU API
    and `~100% → ~3%` process CPU), [`#436`](https://github.com/Neroued/ninfer/pull/436) (Anthropic
    `thinking.display: "updates"`), and [`#430`](https://github.com/Neroued/ninfer/pull/430)/[`#415`](https://github.com/Neroued/ninfer/issues/415)
    (flag-gated prefix-cache inspection/eviction) stay on watch; [`#437`](https://github.com/Neroued/ninfer/issues/437)
    (`NVFP4` `Compact64-T6` attention) and [`#431`](https://github.com/Neroued/ninfer/issues/431)
    (GPU utilization ceiling) do not apply.
- **`ashalliants/ninfer-3090` master `aa6566fc` (2026-11-09; `2,141` commits past `81c8ce09`;
  release `v0.17.2-rtx3090` on 2026-11-07):**
  - *n-gram copy drafting beside DFlash2 (`--ngram-draft-tokens 15`, 16-column verify, copy-miss
    backoff `12 → 24 → 36`, `C2` partner-balance ledger):* reports `+42%` whole-session output
    (`174.6 → 248.0 tok/s`, wall `786 → 677 s` across `4` RTX 3090 agent sessions at 350 W; `+76%`
    file rewrite, `+73%` apply change, `+53%` function edit, `+22%` explore, `-0.1%` revert diff,
    `-4.8%` explain, `95%` copy acceptance `117,476 / 124,280`, `+15%` two-lane batch output/s). Our
    `sm_120` RTX 5090 `C2` ABBA evaluation on model v3 `81f924d4` reproduced the copy-turn gain (`+53.43%`
    synthetic full-file edit, `+48.78%` concurrent copy request, `+41.46%` constrained copy request,
    `+0.21%` role controls, `+0.27%` depth sweep), but regressed short Read turns (`-4.21%`) and free
    partners (`-0.68%`) and preserved greedy byte identity on only `15/23` requests because 16-column
    verification changes batch reductions; **no-go retained** under the byte-identical qualification
    gate (and copy-drafting slice `E5` in [`alphastorm/ninfer#94`](https://github.com/alphastorm/ninfer/pull/94)
    was declined, closed, and not shipped in `v0.17.0` after 3,000-turn coding-agent replay
    projected `×1.055–1.093 < 1.15`).
  - *`sm_86` `Q4`/`Q5`/`Q8` linear shape-table retune:* cold L2-flushed microbenchmarks
    (`bench/ops/linear_schedule_bench.cu`) report `1.30×` to `3.84×` across `18` shapes (peak `3.84×`
    on `q4 131072×5120` at `T=12`, `2.72×` on `q8 34816×5120` at `T=56`, `1.95×` on `q4 1024×5120`),
    but no end-to-end decode figure is published, cold margins invert in situ (`GDN` width `7`
    `+5.9%` cold → `-0.78%` in situ; `q5_linear_add` `T=10` `+8.0%` cold → `+13.59%` in situ), and our
    shipped `DFlash2 K=7` (`8` columns, `v0.16.0`–`v0.17.0`) and prior `MTP3` (`4` columns,
    `v0.3.1`–`v0.15.0`) profiles stay inside the `t <= 8` `launch_q4_draft_head_small_t` branch
    (`watch`, RTX 3090 in-situ A/B only).
  - *Tooling and `v0.17.2-rtx3090` robustness:* GPU-free byte/bandwidth performance model
    (`tools/perf_model.py`, PR `#438` `d248479f`, and nsys capture validation PR `#439` `853377de`,
    predicting 27B `MTP3` decode at `112.7` vs `107.1 tok/s` measured and `131K` prefill at `1,650` vs
    `1,644 tok/s`), rented-GPU power-cap guard (`cae63825`), and request-scoped out-of-vocabulary
    token fault handling (PR `#412` `2ac892d1` / `437a40cb`, matching upstream
    [`#426`](https://github.com/Neroued/ninfer/issues/426) so an invalid token ends one request with
    HTTP `500` `numerical_failure` instead of stopping the engine; request-local `numerical_failure`
    retirement shipped on RTX 5090 `beta.6` in `v0.17.0` via
    [`alphastorm/ninfer#98`](https://github.com/alphastorm/ninfer/pull/98)).
- **`iamwavecut/ninfer-all` master `8412e774` (2026-11-10):** ranks the highest-leverage portable
  candidates across the community fork network:
  - *Concurrent prefill pacing (`--prefill-stall-budget-ms` / `--decode-rounds-per-prefill`, PR `#195`
    `c87b836d` / `6152a3fb`):* cuts per-step decode pause on a generating stream beside a
    `15.6K`-token prefill from `0.83 s` to `0.35–0.36 s` at a `250 ms` budget (`0.59–0.62 s` at
    `500 ms`, `+11%` / `+2%` new-prompt TTFT) on RTX 3090 `Qwen3.8-27B` `DFlash2` (`chunk 2,048`), and
    cuts worst inter-token gap behind four streams from `1,043 ms` (`chunk 1,024`) to `515 ms` (`512`)
    / `312 ms` (`256`) against an `82 ms` median decode interval while prefill rate moves only
    `1,135 → 1,130 → 1,110 tok/s` (prefill-pacing slice `E4` in
    [`alphastorm/ninfer#95`](https://github.com/alphastorm/ninfer/pull/95) shipped **default-off**
    in RTX 5090 `v0.7.0-qwen38-5090-beta.6` / `F3` `e0971faf` in `v0.17.0`).
  - *Output-identical host-side TTFT micro-fixes:* Jinja `string::strip` boundary-only decoding
    (`21d8b947`, `~14 ms` per `500K`-character render, skipped because our base validates interior
    UTF-8 by contract), NFC boundary-scoped normalization (`4f8d324a`, `13.2 → 0.44 ms` on `507,749`
    bytes; shipped as host-NFC slice `E3` in [`alphastorm/ninfer#96`](https://github.com/alphastorm/ninfer/pull/96)
    in RTX 5090 `v0.7.0-qwen38-5090-beta.6` / `F3` `e0971faf` in `v0.17.0`), word-at-a-time
    prefix-shortlist FNV digest mixing (`79774084`, `~23 ms` of a `30 ms` admission at `156K`
    tokens), background n-gram index construction and zero/huge-page allocation (`51917102`,
    `f76b614c`, `15–22 → 1.0–1.9 ms` / `-13 ms` TTFT at `3.6K`), and startup small-T attention module
    preload (`79d657e0`, skipped as `<= 0.67 ms` on our shared `INT8` launch module).
  - *In-situ RTX 3090 route calibration (`ninfer-calibrate`, PR `#191` `3fda3165` / `cdf5456c`):*
    `1.28–1.49 ms` small-T MMA vs `2.21–2.51 ms` sliced-K (`~1.7×`) on the `Q6` head at `3–16` tokens
    at 350 W, plus `Q4` output/down-projection boundary retunes.
  - *Engine resilience and long-context attention numerics:* request-scoped non-finite logit faults
    (PR `#299` `d82ccb4a` / `c8849f1c`; shipped in serving-robustness slice `E2`
    [`alphastorm/ninfer#98`](https://github.com/alphastorm/ninfer/pull/98) in RTX 5090
    `v0.7.0-qwen38-5090-beta.6` / `F3` `e0971faf` in `v0.17.0`) and online-softmax history rescaling
    by the difference of rounded tile maxima (PR `#302` `fc884ec5` / `48783e2a`), while
    `--fast-prefill-kernel` changes perplexity and requires the 1,120-prompt quality screen.
- **`sergiuszm/ninfer-4090` (`master` `07811ec5` on 2026-08-08, `rtx4090-port` `7f47a622` on
  2026-10-24, `catchup4b` `4a22fae7` on 2026-10-31):** no un-taken `sm_89` dense-27B decode or
  prefill gain; PR `#15` `INT8` group-64 activation prefill (`--prefill-activations a16|int8`,
  default `a16`, no end-to-end gain reported) is the same axis as our declined `Group64` A8 prefill
  ([EXP-100](PERFORMANCE.md#experiment-ledger)), `rk8v4`/`rk4v4`/`rk4v4-e8`/`rk2v4-e8` KV storages
  overlap our [EXP-107](PERFORMANCE.md#experiment-ledger) evaluation, and `--tolerant-tool-calls` /
  `tool_constraints=auto` (recovering raw string arguments that quote `</parameter>`) stays on watch.
  Other watched forks — `13thblade/ninfer-all-nvfp4` (`9b4b8a00`, 2026-11-02),
  `IMGillusion/ninfer-engine` (`ae1ba85a`, 2026-11-02; phase-separated L3 disk KV reads/writes, two
  materialization slots, and persisting only matchable states), `troyliu0105/ninfer-all` (`81bf00d0`,
  2026-11-02), and `Saylek-ai/ninfer` (`fe84e749`, pushed 2026-11-03; Host `FreeExtents` placement and
  duplicate-tool-parameter coalescing) — carry no dense-27B decode or prefill win.
- **Oh My Pi releases after `v18.16.0` through `v18.18.6` (2026-11-09):** eight upstream releases
  followed [`v18.16.0`](https://github.com/can1357/oh-my-pi/releases/tag/v18.16.0) (`650f3a10`,
  2026-11-02): [`v18.17.0`](https://github.com/can1357/oh-my-pi/releases/tag/v18.17.0) (`75e7801e`,
  2026-11-06), [`v18.18.0`](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.0) (`b5a6b2f7`,
  2026-11-07), [`v18.18.1`](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.1) (`24439066`,
  2026-11-08), [`v18.18.2`](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.2) (`cb4801a7`,
  2026-11-08), [`v18.18.3`](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.3) (`21f1188c`,
  2026-11-09), [`v18.18.4`](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.4) (`0920fabe`,
  2026-11-09), [`v18.18.5`](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.5) (`1891f380`,
  2026-11-09), and [`v18.18.6`](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.6) (`9058ab9d`,
  2026-11-09), with `main` at `f0200abf28e8` (`4,472` commits past `45c35e40`). Across `18.16.0 →
  18.18.x`, changes are agent-surface rather than HTTP-wire changes: native-family token counting
  (`qwen3.8-*` classifies to `qwen3`; unclassified IDs fall back to `o200k_base`), opt-in
  `update.auto` and setup wizard v3 in `18.17.0` (`update: {auto: false}` and
  `startup: {checkUpdate: false, setupWizard: false}` pins), `discarded-turn` usage journaling, Bash
  5.3 semantics with `LANG`/`LC_ALL=C.UTF-8` and isolated Windows consoles, the
  `5 / 10 / 30 / 60 / 300 s` `wait` idle ladder, nine-worker subagent threads, `qwen3.8` delegation
  fallback moving from `eager` to `balanced` in `18.18.3`, and "Read small files whole; ranges only
  for large files" prompt guidance. Published `v0.17.0` (2026-11-10) adopts stock OMP `18.18.6`
  (`9058ab9d`, superseding `v0.16.2`'s `18.15.0` pin `3fedf8d5`; see the
  [18.15.0→18.18.6 client review](measurements/2026-11-10-omp-18186-client-upgrade-review.json) and
  [v0.17.0 release notes](../releases/v0.17.0/NINFER_RELEASE_NOTES.md)).
- **Hugging Face `neroued/*` artifacts and model census:** `neroued/*` artifacts remain unchanged
  since 2026-10-29 (`neroued/Qwen3.8-27B-NInfer` v3 `81f924d4` at `19.03 GiB` / `20,437,521,664`
  bytes stands; `neroued/Qwen3.8-27B-nvfp4-NInfer` at `22.09 GiB`,
  `neroued/Qwen3.6-35B-A3B-NInfer` at `21.23 GiB`, `neroued/Qwen3.8-Flash-Next-NInfer` at revision
  `001057dd`, and `neroued/GLM-5.3-Flash-NInfer` at `f1c4e21` are unchanged). Across the 100-repo
  Hugging Face `library_name: ninfer` census, `~75%` of the `ninfer` repositories touched in this
  window are for a different engine than ours, with `iamwavecut/ninfer-all`'s `gguf_blocks_v1`
  layout (`qwen3_8_27b_gguf`) as one cause (unloadable on `F3` `e0971faf` in RTX 5090 `beta.6` /
  `v0.17.0`, `a87de361` in native `beta.2`, and upstream `Neroued/ninfer` master; upstream PR
  [`#282`](https://github.com/Neroued/ninfer/pull/282) closed unmerged on 2026-11-02); see
  [`ROADMAP.md`](../ROADMAP.md#deferred-and-rejected-decisions).

## v0.17.0 runtime and client binding

Published release **v0.17.0** (2026-11-10, [release notes](../releases/v0.17.0/NINFER_RELEASE_NOTES.md),
superseding `v0.16.2`) binds RTX 5090 `v0.7.0-qwen38-5090-beta.6` from frozen engine source
`e0971faf221204047d5a4ed834e4e298740cee17` ([fork PR #101](https://github.com/alphastorm/ninfer/pull/101))
on upstream `64d10fbf`, carries published native `v0.8.0-qwen38-{3090,4090}-beta.2` unchanged from
`v0.16.2` at source `a87de3613c17bced777b446fb545f872d8395ec1`, and advances the client to
unmodified upstream [`v18.18.6`](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.6) (commit
`9058ab9d229663e229e2867824ba6df6f21e9e59`, tree `fd379b65368a20c7648d97f2c2b99cc03e019254`,
release `439766193`; [18.15.0→18.18.6 review](measurements/2026-11-10-omp-18186-client-upgrade-review.json)
`aad29cd6`). The RTX 5090 runtime delta adds bounded resume/fresh admission with per-rotation
fresh-window accounting (upstream [#434](https://github.com/Neroued/ninfer/issues/434)), durable
pressure-work waits, serving robustness for malformed tool arguments, template-aware effort
normalization, request-local numerical failures, and stop/drain final-save ordering (upstream
[#440](https://github.com/Neroued/ninfer/issues/440)/[#441](https://github.com/Neroued/ninfer/issues/441)/[#446](https://github.com/Neroued/ninfer/issues/446)),
and host-side NFC/frontend rendering, using isolated host checkpoint directory `checkpoints-v017`
mounted at `/checkpoints-v013`. Fresh `2026-11-10` acceptance on candidate `076bbe4f` passed all
five documented routes (`31/31` blocks), three stock `18.18.6` clients, the **408.213 s** RTX 5090
hold, and RTX 4090 native campaign (**508.420 s**), public-install, and restoration checks, while
RTX 3090's post-route `native-probes` compaction campaign failed (`900 s` timeout, `3` sessions
refused at subsequent Stop) and is waived in
[`rtx3090-route-waiver.json`](../releases/v0.17.0/qualification/rtx3090-route-waiver.json)
(`19f2c0ef`) with separate lead recovery (`fabb50de`). Closed runtime/product/waiver councils are
bound in [`review/runtime-ledger.json`](../releases/v0.17.0/review/runtime-ledger.json) (`5f8d6e4a`;
deferred tooling items in [#149](https://github.com/alphastorm/omp-ninfer/issues/149)).

## 2026-11-05 upstream and fork watch

Observed on 2026-11-04/05 after `v0.16.2` publication (companion experiment receipt:
[`2026-11-05-p19-flash-next-and-starvation.json`](measurements/2026-11-05-p19-flash-next-and-starvation.json)):

- **`Neroued/ninfer` master `a754fcf3` (2026-11-02):** `228` commits past our merge base `64d10fbf`;
  `dev` equals `master`. New since `64d10fbf`: native DGX Spark target (`sm_121a`), two-Spark
  `TP2`/`EP2`/attention-DP distributed execution, MoE routes (`NVFP4`/`FP8`) and CPU expert offload
  ("expert weight cache"), `Qwen3.8-Flash-Next` (`Qwen4Exp`) and `GLM-5.3-Flash` (`GLM5Next`) models,
  unified TOML startup configuration, and monitoring snapshots + dashboard. In a per-commit
  merge-tree probe against fork head `a87de361`, only `9/228` commits apply cleanly (upstream
  restructured `qwen3_5/program/*`, the runtime engine, and context storage; `2705a728` alone
  conflicts in `285` paths).
- **Classification for the `Qwen3.8-27B` product:** `8` upstream fixes are already in the fork
  (`9822c38d`, `58733a86`, `4ec903a0`, `1e902680` subset, `d602894a`, `a062e016`, `704fa68d`,
  `45f74287`); `3` upstream source defects remain unported on `a87de361` and are ported in draft
  [`alphastorm/ninfer#93`](https://github.com/alphastorm/ninfer/pull/93) (head `e6ac7b70`, CI green
  on all `8/8` jobs) — upstream [`#434`](https://github.com/Neroued/ninfer/issues/434) request
  starvation under context pressure (`a754fcf3`, reproduced at runtime on both shipped `C2` lanes and
  the `rtxpro6000-win-a` proxy in [EXP-109](PERFORMANCE.md#experiment-ledger), where `e6ac7b70` cuts
  the maximum admitted-request pause from `362.3 s` to `1.28 s` while trading indefinite silent stalls
  for bounded HTTP `503` queue timeouts on deferred fresh arrivals), upstream
  [`#378`](https://github.com/Neroued/ninfer/issues/378) Host placement (re-expressed from Saylek-ai
  `fix/378-host-placement`; not reproduced on native RTX 3090 or on the `rtxpro6000-win-a` fixed-fill-5
  proxy and inconclusive on RTX 5090 within its `3,600 s` adaptive-fill budget in EXP-109), and the
  `452c3f5f` recovery-loss formula — plus the `a754fcf3` failure-diagnostics subset. Everything else
  requires a full re-port estimated at **7–10 multi-agent days** at `a754fcf3`, with low value for
  the dense 27B product today (deferral stands).
- **`sergiuszm/ninfer-4090`:** `rtx4090-port` is unchanged at `7f47a622` (2026-10-24); side branch
  `catchup4b` at `4a22fae7` (2026-10-31) ports upstream `Qwen4Exp`, `GLM5Next`, and the expert weight
  cache to Ada (`sm_89`, watch only).
- **`ashalliants/ninfer-3090`:** master `d0ff0535` (2026-11-02; releases through `v0.17.1-rtx3090` on
  2026-10-29; upstream base `f76e19c0`, older than `64d10fbf`) adds an `sm_86` `Q4`/`Q5`/`Q8` linear
  shape-table retune (up to `3.84×` on the DFlash2 draft-head width), n-gram copy drafting beside
  DFlash2 (`+42%` on an agent replay), vision with overlay residency, reasoning-effort `xhigh`, and
  `Qwen3.8-Flash-Next` on one RTX 3090 with `33 GiB` host-pinned experts (`108–113 tok/s` `MTP`).
  Native lanes are frozen (founder decision, 2026-11-04), so these items are recorded, not adopted.
- **`Don-Chad/ninfer-3090`:** master `115dee6b` (2026-10-31) adds only an optional web dashboard
  since `d8c29253`.
- **Oh My Pi:** only [`v18.16.0`](https://github.com/can1357/oh-my-pi/releases/tag/v18.16.0)
  (2026-11-02) has been published after our pinned `18.15.0`. As measured in
  [`2026-11-05-omp-18160-tokenizer-VERIFY.md`](measurements/2026-11-05-omp-18160-tokenizer-VERIFY.md)
  ([#142](https://github.com/alphastorm/omp-ninfer/pull/142)), the unclassified served ID
  `q38-ninfer` is counted by `bytes/4` (`18.15.0`) or `o200k` (`18.16.0`) instead of the Qwen
  tokenizer, whereas an explicit `tokenizer: qwen3` selects `qwen3` in both releases (`qwen3.8-27b`
  already resolves to `qwen3` in both). Candidate for the next client bump; not adopted in this
  research cycle.
- **Strata and Hugging Face artifacts:** no Strata release after `v0.2.10`. Hugging Face `neroued/*`
  artifacts are unchanged after 2026-10-29 (`Qwen3.8-27B` v3 `81f924d4` stands;
  `neroued/Qwen3.8-Flash-Next-NInfer` revision `001057dd`, 4 files, `108,445,200,388` bytes,
  evaluated in [EXP-108](PERFORMANCE.md#experiment-ledger)).

## v0.16.2 runtime and client binding

Published release **v0.16.2** (2026-11-04, [release notes](../releases/v0.16.2/NINFER_RELEASE_NOTES.md),
superseding `v0.16.0` while the held `v0.16.1` client-only candidate remains unpublished) binds
runtime source `a87de3613c17bced777b446fb545f872d8395ec1` on upstream `64d10fbf` across published
RTX 5090 `v0.7.0-qwen38-5090-beta.5` and published native `v0.8.0-qwen38-{3090,4090}-beta.2`.
The delta includes byte-proven durable-generation Host reclaim and the
[managed-Stop capacity fix #78](https://github.com/alphastorm/ninfer/issues/78), export retirement, opt-in FP32
identity repair, deterministic RDC builds and native repair/power/qualification-driver fixes.
Model and serving shapes are retained, not runtime bytes. Current lane/native qualification,
both 1,120-prompt zero-difference quality screens, fit proofs, published native cuts and
3/3 upgrade/rollback/repair rehearsals per native lane are bound. The founder's native speed
decision is no regression versus published beta.1 (weighted ≥0.98, every case ≥0.95,
byte-identical normalized outputs), superseding the earlier 1.08 speedup floor: RTX 3090
**1.0003** weighted / **0.9988** min / **84/84** identical; RTX 4090 **0.9996** /
**0.9989** / **115/115**. New exact-subject waivers preserve the failed RTX 5090 `restore_0`,
RTX 4090 `restore_1` and RTX 3090 sibling position 1 `base` results.
The [notes](../releases/v0.16.2/NINFER_RELEASE_NOTES.md) disclose the original founder-record
hashes and RTX 4090's private uncapped-power-only rehearsal fix. Follow-ups are
[runtime-council deferrals #87](https://github.com/alphastorm/ninfer/issues/87) and
[native tooling defects #88](https://github.com/alphastorm/ninfer/issues/88).
Fresh **2026-11-04** acceptance on `c6fc8465` passed five routes (**31/31 blocks**), three stock
clients, and RTX 4090 public-install/probe/restoration checks
([routes](../releases/v0.16.2/acceptance/documented-routes.json) ·
[composition](../releases/v0.16.2/acceptance/composed-external-installation.json)).
RTX 3090's seven route blocks passed; the later native campaign failed at structured-outage
managed Stop (`graceful_incomplete_shutdown`, saved 1 / skipped 8 / refused 1, `capacity`, reclaimed 0),
founder-waived as a residual of #78 also present on published beta.1. Behavior completion,
wrapper restoration audit and anonymous public install are not claimed. The notes bind empty-session
`Control-Release.ps1 -Action Start` then `-Action Stop` recovery; fork
[#89](https://github.com/alphastorm/ninfer/issues/89) / [#90](https://github.com/alphastorm/ninfer/issues/90)
track residual export capacity and incomplete-Stop owner restoration.
The exact-source runtime full council and focused product reviews closed by disposition;
the [closed, approved ledger](../releases/v0.16.2/review/runtime-ledger.json) separates their subjects.
Composition verified task absence after native/rehearsal cleanups, both full native-state/finish
digest pairs, attempt names (maximum 12, bound 23), and measured small-fixture reclaim/Stop
times below 900 s. GE-R1 summary receipts are lane-agnostic, with lane-distinct archive provenance;
GE-R4 binds source/download review rather than live acceptance. Product deferrals use
[#138](https://github.com/alphastorm/omp-ninfer/issues/138). Review approval and immutable evidence
pins are separate from founder-owned publication.
The held v0.16.1 manifest and v0.16.0 execution results are not carried as current proof.

Chosen upstream: [`v18.15.0`](https://github.com/can1357/oh-my-pi/releases/tag/v18.15.0),
commit `3fedf8d53267e32a6d7521ce725fdcc4a36fdc67`, tree
`48bc72ba2418c0b78163d9769e91a0d8683e642b`, release `430630500`.
The [18.15.0 review](measurements/2026-11-01-omp-18150-client-upgrade-review.json) composes with
the preceding [18.14.2 review](measurements/2026-11-01-omp-18142-client-upgrade-review.json),
not with old-client acceptance. Shared replay metadata sanitization and manual-compaction result
delivery changed even though core Responses/state blobs match. Explicit `retry.modelFallback=false`
keeps the new missing-primary-key fallback branch off; optional widget captions resolve credentials
separately. Keep static provider fragments, working compat keys, effort clamps, guard enabled and
all original live gates. Remove obsolete operator `compat.thinkingLoopGuard`, not the detector.

## v0.16.0 native DFlash2, RTX 3090 C2, and common-engine composition

Published release **v0.16.0** (2026-11-01, [release notes](../releases/v0.16.0/NINFER_RELEASE_NOTES.md), superseding the planned
`v0.15.1` patch) binds all three runtime components — `v0.7.0-qwen38-5090-beta.4` (image `7a5a7bb8`
on base `d4377ed0`, server `bab3fd77`, kept profile `qwen38-5090-v0.13.0` / config `751d22dc`),
`v0.8.0-qwen38-4090-beta.1` (package `06526bdb`, server `c6f59e9e`, profile
`qwen38-4090-native-v0.8.0-beta.1` / config `f00cfac9`, DFlash2 `K=7`, INT8 KV, `C1`, `1,024`
prefill chunk, `16,512,696,320` B Host), and `v0.8.0-qwen38-3090-beta.1` (package `040d5923`,
server `72cd776b`, profile `qwen38-3090-native-v0.8.0-beta.1` / config `cbe67aae`, DFlash2 `K=7`,
INT8 KV, `C2` over one shared 131,072-token pool, `180 s` timeout, `21,881,405,440` B Host,
350 W serving cap) — to frozen engine source `26fa28d0e7834515508fc07ac503164a6effc820` on
upstream `Neroued/ninfer` master `64d10fbf`, while retaining unmodified upstream OMP **18.14.0**
(`31147f9d`) and shared model v3 `81f924d4` (`v18.14.1` and `v18.14.2` are deferred to `v0.16.1`).
It ships counted Host `StateImage` materialization before off-worker checkpoint export (`EXP-105`),
shared-pool export-pin liveness and post-calibration startup headroom enforcement (`EXP-106`),
checkpoint-owner replacement and state-retirement response ordering (`c3911a14`,
`alphastorm/ninfer#49` `e517dab8`, [#95](https://github.com/alphastorm/omp-ninfer/issues/95),
[#96](https://github.com/alphastorm/omp-ninfer/issues/96)), Linux `io_uring` owned completion
buffers and CQE cancellation/drain barrier (`40a1b2d0`,
[#116](https://github.com/alphastorm/omp-ninfer/issues/116)), native installer/controller GPU-owner
lease handoff across running-lane upgrades and power-cap transitions (`577fecba`,
`alphastorm/ninfer#48` `9cb741dc`, closing [#94](https://github.com/alphastorm/omp-ninfer/issues/94)
and [#116](https://github.com/alphastorm/omp-ninfer/issues/116)), per-position speculative metrics
(request-log schema `30`), and closure of all 13 `v0.15.0` product-council residuals in
[#117](https://github.com/alphastorm/omp-ninfer/issues/117). Both native packages passed `43/43`
second-build EXE/DLL raw-byte comparisons, `EXP-101` (`671659f0` on RTX 3090) and `EXP-102`
(`6231dccd` on RTX 4090) 1,120-prompt quality screens, RTX 3090 84-role (`c904d341`) and RTX 4090
115-case (`32acdecc`, with founder waiver `92b94c4a` on `log-024@0` at `0.934`) ABBA speed gates,
`3/3` `v0.7.0-beta.3` running-upgrade, forced-rollback, and repair/reinstall rehearsals (`38a3a380`
and `631428b5`), and `15/15` managed hardware phases (`rtx4090.json` `69ebf60c`; `rtx3090.json`
public `48c7f635` / raw `038fe713` under the founder-approved `agent_protocol.py` `C2`
precondition override `317b98ee`, [alphastorm/ninfer#56](https://github.com/alphastorm/ninfer/pull/56)),
while RTX 5090 `beta.4` passed `rtx5090.json` (`2200fa44`) and the `p16-agent-parity/2` probe
campaign (with founder waiver `66ba8104` on two-restart `restore`). The G4 fork council
(`CR-20261031T162716Z-26fa28d0`, ledger `b2871c36`, 4/4 seats) closed by disposition in round 1 with
five deferred `alphastorm/ninfer` P2/P3 issues
([#50](https://github.com/alphastorm/ninfer/issues/50)–[#54](https://github.com/alphastorm/ninfer/issues/54)),
while the G4 product-tooling council (`CR-20261101T123454Z-56899320-product`,
sequence `omp-ninfer-v0.16.0-product-56899320`, subject `56899320`,
4/4 seats completed, 0 missing or aborted) closed by disposition in round 1 with no in-scope
residual P0/P1. Its P2/P3 residuals are deferred in
[#128](https://github.com/alphastorm/omp-ninfer/issues/128), retaining
[#109](https://github.com/alphastorm/omp-ninfer/issues/109). The combined ledger SHA-256 is
`ab195970955c58b584ddbcf2143072b56ced28e714251e975c0f67986722e627` in
[`review/runtime-ledger.json`](../releases/v0.16.0/review/runtime-ledger.json).
Fresh five-route / three-platform candidate acceptance (**PASS** on
`56899320d416bafda5c15d7e454e9b593badc0a6`, **2026-11-01**, 31/31 blocks and both native public installs)
is recorded separately in
[composed acceptance](../releases/v0.16.0/acceptance/composed-external-installation.json);
neither acceptance nor G4 approval authorizes publication.

## v0.15.0 client-only composition

Published release **v0.15.0** (2026-10-30, [release notes](../releases/v0.15.0/NINFER_RELEASE_NOTES.md))
pins unmodified upstream OMP **18.14.0** (`31147f9d`, tree `9a63b5bf`) in place of 18.12.6 while
carrying all three `v0.14.0` beta.3 runtime components, shared model container version 3 `81f924d4`,
and serving profiles byte-identical at common engine source `2c6f423b` on upstream `Neroued/ninfer`
master `64d10fbf`. Fresh acceptance on frozen candidate `af62e766` passed all three client
platforms, all five routes (31 exact blocks), both native public installs, and independent host
restoration on 2026-10-30 (both initial acceptance windows passed and restored without a corrected
attempt or production upgrade: 403.884 s RTX 5090 acceptance-window hold, 371.326 / 394.389 s native
driver windows;
[composed acceptance](../releases/v0.15.0/acceptance/composed-external-installation.json);
[client source review](measurements/2026-10-30-omp-18140-client-upgrade-review.json)). macOS remains
preview, Linux evidence is WSL2-only, and both native lanes stay MTP3. The changed-scope
product-tooling council (`CR-20261030T194208Z-af62e766-product`) closed by disposition and the
carried runtime council retains its original `v0.14.0` subject (`CR-20261028T031911Z-2c6f423b`) in
[`review/runtime-ledger.json`](../releases/v0.15.0/review/runtime-ledger.json), with deferred
residuals in [#117](https://github.com/alphastorm/omp-ninfer/issues/117) and fork-council residuals
for the deferred, unshipped native-DFlash2 candidate in
[#116](https://github.com/alphastorm/omp-ninfer/issues/116). Native RTX 3090 DFlash2 was deferred at
the time to `v0.15.1` after fork-after-resume failed with `Native could not release an unreferenced
checkpoint owner` (subsequently fixed in `c3911a14` and shipped across both native lanes in
`v0.16.0`, superseding `v0.15.1`).

## v0.14.0 common-engine composition

Published release **v0.14.0** (2026-10-28, [release notes](../releases/v0.14.0/NINFER_RELEASE_NOTES.md))
binds all three published beta.3 components (`v0.7.0-qwen38-5090-beta.3`,
`v0.7.0-qwen38-4090-beta.3`, and `v0.7.0-qwen38-3090-beta.3`) to one frozen engine source
`2c6f423bd817b6534158553e1b34ab4959c43165` on upstream `Neroued/ninfer` master `64d10fbf`, with the
shared v3 model (`81f924d4`) and stock OMP 18.12.6 unchanged. It brings RTX 5090 round-tail
retirement and consumer-capture scheduling, the materialized-BF16 gated-attention seam, the
Blackwell TMA descriptor ABI fix, `sm_86` / `sm_89` long-prompt prefill specializations, and
upstream `libjpeg-turbo` / grammar / JSON-schema / vision-identity picks onto one common tree.
Native MTP3 keeps `Group64` A8 off, and RTX 3090 serves at 350 W with the 370 W owner baseline
restored on stop (stop a running v0.13.1 RTX 3090 lane before upgrading,
[#94](https://github.com/alphastorm/omp-ninfer/issues/94)). Checked first-build RTX 5090 bytes
(`55f0b95a`, image `760fb6be`) ship under an explicit founder-approved 5090-only reproducibility
exception; both native closures pass 34/34 second-build EXE/DLL byte comparisons and fresh 15-phase
installed hardware chains (151.54 / 90.64 tok/s C1 decode; 81.78 / 187.88 s exact 130,048-token
retrieval; 1,647 / 1,650-token restart reuse).

Both the common-engine fork (`CR-20261028T031911Z-2c6f423b`) and product-tooling
(`CR-20261028T043650Z-c81a8e7e`) full councils closed without remediation
([review ledger](../releases/v0.14.0/review/runtime-ledger.json); deferred residuals in
[#88](https://github.com/alphastorm/omp-ninfer/issues/88)–[#90](https://github.com/alphastorm/omp-ninfer/issues/90)
and [#94](https://github.com/alphastorm/omp-ninfer/issues/94)–[#100](https://github.com/alphastorm/omp-ninfer/issues/100)).
Fresh acceptance on frozen candidate `c81a8e7e` passed all five routes (31 exact blocks), three
stock 18.12.6 clients, and both first-of-lineage beta.3 native public installs with independent
restoration (421.229 s corrected RTX 5090 hold after an initial same-Mac test's real tunnel-port
collision failed closed and restored the incumbent, #97 / #99; 392.504 / 393.945 s native driver
windows; [composed acceptance](../releases/v0.14.0/acceptance/composed-external-installation.json)).
Canonical beta.3 promotions preserved beta.2 roots; subsequent public checks were
`already_installed`, not upgrade/rollback proof.

## v0.13.1 native runtime composition

Published release **v0.13.1** (2026-10-26, [release notes](../releases/v0.13.1/NINFER_RELEASE_NOTES.md))
ports `sm_89` / `sm_86` and Windows onto the same upstream master `64d10fbf` foundation as the
carried RTX 5090 beta.2 component. Both native lanes move to published model version 3 `81f924d4`,
INT8 KV, MTP3, 131,072 context, one active request, shared Host budgets, and 640/768 MiB admission
headroom. This is a downstream Windows/architecture port, not new upstream Windows support, a
dev-pool adoption, native DFlash2 qualification, or an adopted community runtime.

The Windows durable-file path preserves existing handle-anchored publication and adds the missing current-parent failure
handling/extended-root coverage. Physical disk exhaustion retains its first cause and returns
`capacity` without deleting surviving Responses objects; prepared off-worker exports are finite
admission progress, with lease destruction before wakeup. Native roots remain isolated from
predecessor generations, and the separate dependency CycloneDX includes real CRT/DirectStorage
provenance without replacing SPDX.

The first native beta.1 component prereleases at `eecb437f` are published but unused after a fork CI fixture defect.
Frozen beta.2 source `7a25cd72` has exact-head CI, Windows 90/90 per architecture, 75 package units,
both Linux builds, and both fresh full hardware chains (150.94/84.06 tok/s C1 decode;
85.71/208.78 s exact 130,048-token retrieval; 1,647/1,650-token restart reuse). Both actual beta.2
prereleases, inventories, and byte-mirrored qualification/profile receipts are bound. Both
native-runtime and product-tooling councils closed without remediation
([review ledger](../releases/v0.13.1/review/runtime-ledger.json); deferred items in
[#88](https://github.com/alphastorm/omp-ninfer/issues/88),
[#89](https://github.com/alphastorm/omp-ninfer/issues/89), and
[#90](https://github.com/alphastorm/omp-ninfer/issues/90)). Fresh candidate `92dfb132` acceptance
passed all five routes (31 blocks), three client platforms, and both first-of-lineage native public
installs with independent restoration
([composed acceptance](../releases/v0.13.1/acceptance/composed-external-installation.json)). Neither
old native proof nor the carried RTX 5090 review ledger transfers to the v0.13.1 native qualification.

## v0.13.0 sync program

Published release **v0.13.0** (2026-10-25) moves the RTX 5090 container onto upstream master
**`64d10fbf`** (`v0.7.0-qwen38-5090-beta.2`, source `6d4d0a05`) with stock OMP **18.12.6**
(`45c35e40`), published model container version 3 (`81f924d4`), and strict-origin profile
`qwen38-5090-v0.13.0` (`751d22dc`), while carrying the native `cad19767` packages and model
`eec39564` unchanged and re-accepting all five documented routes (31 blocks), three stock 18.12.6
clients, and both native public installs on frozen candidate `b1a54dc9`
([composed acceptance](../releases/v0.13.0/acceptance/composed-external-installation.json)).
Rebased native packages in `v0.13.1` bind the 24 GB `--admission-headroom-mib` amendment
(640 MiB on RTX 4090 / 768 MiB on RTX 3090), packaging, dependency SBOMs and fresh Windows
hardware/public-route qualification. The
[content-safe plan](measurements/2026-10-25-upstream-sync-plan.json) records the port scope and
gates:

- Master adds JSON-schema constrained decoding, preemption, rewritten context ownership and
  CUDA-graph startup calibration. It has **no disk-durable sessions** and its Responses store is
  still process-local. The port must preserve restart-surviving Responses, isolation, HMAC policy,
  Qwen parser semantics, DFlash2, kernel routes, keep-warm, concurrency, GPU-UUID selection and
  Windows packaging/controller and qualification tooling.
- Dev `a522cfef` is 172 commits beyond master and replaces the context substrate again with the
  unified pool. The program freezes master rather than following that churn; grammar whitespace
  (`9822c38d`), direct-I/O alignment (`4ec903a0`) and container dependencies (`1e902680`) are
  isolated backport candidates. The native persistence bridge stays behind a Program-level
  contract so a later dev port is bounded.
- The 5090 fork has roughly 236 original commits across 21 families; the native source roughly
  161. This is not a file-copy merge. Upstream's DFlash2, scheduler, grammar and context stores stay
  authoritative. Unshipped NVFP4 KV, reverted standby-pinning retries and the unshipped
  `3a2fadbd` pair-mixer change are excluded. The [performance ledger](PERFORMANCE.md#experiment-ledger)
  distinguishes that experimental mixer result from source `1302d639`.
- A pinned-source check of upstream's tool parser shows that master already has
  declared-string/scalar-union handling, case-insensitive booleans, exact integer classification
  and unconstrained duplicate-parameter fallback. The remaining audit concerns atomic mismatch
  fallback, constrained duplicate semantics and deeply nested unions, not a second parser.
- Don-Chad's checkpoint-set codec and content-addressed disk tier are design references, not
  equivalents of our session contract: their integrity check is non-cryptographic and Responses
  objects remain process-local. The community DFlash2 and compact-KV measurements use different
  artifacts, power and context settings; they do not replace our quality/leak screens.
- EXP-089's observed native W8 static-shared-memory link failure is fork-local, not proof that
  DFlash2 cannot run on sm_86/sm_89: upstream Q8 already uses dynamic shared memory. Windows and
  architecture enablement nevertheless remain real build and qualification work, not a flag flip.
- Published predecessor Chat/Responses reject names over 64 characters; Anthropic already
  accepts 128. The rebased RTX 5090 container unifies the bound at 128; carried natives retain 64. Upstream
  [#395](https://github.com/Neroued/ninfer/issues/395) and
  [#396](https://github.com/Neroued/ninfer/pull/396) are tracked; contribution text remains
  local drafts, subject to upstream's issue-first scope confirmation.

**Release qualification:** Four-boot production schema 3 restart reused **20,926 cached tokens**
with **27 byte-identical continuation bytes** ([`durability.json`](../releases/v0.13.0/qualification/durability.json)).
EXP-097 compared v0.12.2's `1302d639` with the rebased RTX 5090 runtime at configured concurrency
two, DFlash2 K=7, BF16 KV, and 131,072 context, measuring **101.09%** median decode across 84
serial role cases (`342.150` vs `338.448 tok/s`, above the 96% floor; structured-output p95 ratio
**1.126** and 64K continuation `335.332 → 290.781 tok/s` are attributed in
[`2026-10-25-exp097-role-corpus.json`](measurements/2026-10-25-exp097-role-corpus.json)).
Canonical sorted-key tool serialization `0abe7c8e5` is integrated with host byte pins; the full
role-corpus comparison was not rerun after it. On the shipped `6d4d0a05` binary, host 66/66 (with
13 restore/pressure/quota/freshness regressions), dense 11/11, loader, canonical shared MTP/FP8,
32 GB C2 restore-overlap (38.0356 s, 1,074,790,400 bytes headroom), grammar/product smokes, and
lane gates (179.86 tok/s server decode, 56.994 s exact 130,048-token retrieval) all passed
([`qualification.json`](../releases/v0.13.0/qualification.json)). Powered quality/leak and
historical OMP parallel/fanout workloads were not re-measured for v0.13.0.

### Qualification log readers

The [ablation reducer](../scripts/run_mtp_ablation.py) and
[variant campaign](../scripts/run_variant_campaign.py) distinguish the request-log schema from
the status endpoint's schema 2. Startup configuration classification supports the historical fork
schema 17, upstream schemas 27–29 and the provenance-bearing schema 30. Known upstream artifact
and context fields and `gpu_keep_warm_ms` participate in comparison; unknown fields are rejected.
Template-inherited thinking/preservation defaults stay `null`, not a fabricated `false`.

Historical startup records without an identity block can be classified without inventing
attestation. They cannot satisfy the campaign's existing binary, source and model identity checks.
For schema 30, `identity.weights_id` is the verified artifact SHA-256, not the campaign manifest's
logical weights label; both the artifact digest and architecture remain bound. Status schema 2
is not accepted as a substitute startup record. The checked-in schema fixtures use synthetic
values and source-grounded field sets, not claimed live inference receipts.

### v0.18.0 client binding — OMP 18.18.7

Published release **v0.18.0** (2026-11-12) pins unmodified upstream
[`v18.18.7`](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.7), source
`e325ffc73ab86e03bdd20a91b77d8e2b3964c906`, tree
`9ba2abe1f1dd7c64b8d3f99dc0e41d689d96886c` (published upstream 2026-11-10T20:23:32Z, release ID
`440868478`); see [client setup](QUICKSTART.md#omp-18187-client). The
[18.18.6→18.18.7 incremental review](measurements/2026-11-11-omp-18187-client-upgrade-review.json)
(landed in [#154](https://github.com/alphastorm/omp-ninfer/pull/154) at `44590ad`, bound at
[`stock-omp.json`](../releases/v0.18.0/qualification/stock-omp.json) `98a1e24d` and
[`client-components.json`](../releases/v0.18.0/qualification/client-components.json) `210660f4`)
inventories all `64` commits and `145` changed paths across `v18.18.6...v18.18.7` and verifies
independent downloads of the Darwin arm64, Windows x64, and Linux x64 binaries and `SHA256SUMS.txt`
(`9a33908b`). All six model and fail-closed fragments under `examples/` and `26` route-sensitive
upstream Git objects carry byte-for-byte unchanged, while on Windows `18.18.7` updates the rendered
`bash` tool description and `cmd`/MSYS path resolution (disclosed in the release notes because
`scripts/hosts/omp-client-probe.py` invokes `omp` with `--tools read`); fresh live acceptance across
all five documented routes (`31/31` blocks) and all three stock 18.18.7 binaries passed on frozen
candidate `2a735da0` on 2026-11-12
([v0.18.0 composed acceptance](../releases/v0.18.0/acceptance/composed-external-installation.json)).

### v0.17.0 client binding — OMP 18.18.6

Published release **v0.17.0** (2026-11-10) pins unmodified upstream
[`v18.18.6`](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.6), source
`9058ab9d229663e229e2867824ba6df6f21e9e59`, tree
`fd379b65368a20c7648d97f2c2b99cc03e019254` (published upstream 2026-11-09T23:30:49Z, release ID
`439766193`); see [immutable v0.17.0 client guide](https://github.com/alphastorm/omp-ninfer/blob/v0.17.0/docs/QUICKSTART.md#omp-18186-client). The
[18.15.0→18.18.6 incremental review](measurements/2026-11-10-omp-18186-client-upgrade-review.json)
(`aad29cd6`, landed in [#145](https://github.com/alphastorm/omp-ninfer/pull/145)) inventories all
`2,051` commits in `v18.15.0...v18.18.6` and the uncapped `3,461`-path tagged-tree diff with
route-sensitive source inspection and independent downloads of the Darwin arm64, Windows x64, and
Linux x64 binaries and `SHA256SUMS.txt`. Model fragments pin `tokenizer: qwen3` on opaque
`q38-ninfer` entries while canonical `qwen3.8-27b` entries retain inferred `qwen3`, keep explicit
`[low, medium, xhigh]` effort lists, and `examples/manual-tunnel/fail-closed.yml` explicitly
disables `update.auto`, `startup.checkUpdate`, and `startup.setupWizard` alongside retries and
model fallback; fresh live acceptance across all five documented routes (`31/31` blocks) and all
three stock 18.18.6 binaries passed on frozen candidate `076bbe4f` on 2026-11-10
([v0.17.0 composed acceptance](../releases/v0.17.0/acceptance/composed-external-installation.json)).

### v0.16.2 client binding — OMP 18.15.0 (and 18.14.2 review)

Published release **v0.16.2** (2026-11-04) pins unmodified upstream
[`v18.15.0`](https://github.com/can1357/oh-my-pi/releases/tag/v18.15.0), source
`3fedf8d53267e32a6d7521ce725fdcc4a36fdc67`, tree
`48bc72ba2418c0b78163d9769e91a0d8683e642b` (published upstream 2026-11-01T14:17:08Z, release ID
`430630500`); see [immutable v0.16.2 client guide](https://github.com/alphastorm/omp-ninfer/blob/v0.16.2/docs/QUICKSTART.md#omp-18150-client). The
[18.15.0 incremental review](measurements/2026-11-01-omp-18150-client-upgrade-review.json)
originally evaluated `v18.15.0` for the held client-only `v0.16.1` candidate (unpublished) and is
bound into `v0.16.2`. All 235 commits in `v18.14.2...v18.15.0` and the uncapped 257-path
tagged-tree diff were inventoried, with focused source inspection. Independent downloads of the
Darwin arm64, Windows x64 and Linux x64 binaries and `SHA256SUMS.txt` match API byte counts/digests;
the three executable hashes also match the checksum rows. The source review distinguishes carried
provider/state/schema/Qwen guard blobs from changed shared replay sanitization, missing-credential
fallback, manual-compaction delivery and optional background-caption requests; fresh live acceptance
across all five documented routes (31 blocks) and all three stock 18.15.0 binaries then passed on
frozen candidate `c6fc8465` on 2026-11-04
([v0.16.2 composed acceptance](../releases/v0.16.2/acceptance/composed-external-installation.json)).

The [earlier 18.14.2 review](measurements/2026-11-01-omp-18142-client-upgrade-review.json)
rechecks upstream stable `v18.14.2` (`7efd7721`) against `v18.14.0`, including all 394 comparison
commits and the uncapped tagged-tree diff. It records published asset identities, carried Responses
provider/state and models-schema blobs, conditional header/retry changes, the Qwen exact-loop guard's
new line-repetition floor, and rejection of length-truncated compaction summaries. It claims no
executable rehearsal or NInfer qualification. [Issue #123](https://github.com/alphastorm/omp-ninfer/issues/123)
tracked the held client-only `v0.16.1` candidate; `v0.16.2` shipped `18.15.0` alongside the
`a87de361` runtime rebuild instead. Never adopt `18.14.1` alone.

### v0.15.0–v0.16.0 client binding — OMP 18.14.0

Published releases **v0.15.0** (2026-10-30) and **v0.16.0** (2026-11-01) pin unmodified upstream
[v18.14.0](https://github.com/can1357/oh-my-pi/releases/tag/v18.14.0), source
`31147f9d1a76608549821c3759f8487b4d66c72d`, tree
`9a63b5bfbb5971962c44fca660744b0d75dcd2c2` (published upstream 2026-10-29T18:25:10Z, release ID
`428242783`); see [immutable v0.16.0 client guide](https://github.com/alphastorm/omp-ninfer/blob/v0.16.0/docs/QUICKSTART.md#omp-18140-client). Upstream release binaries are
rebuilt with Bun 1.4.4 (fixing CVE-2026-91403 and CVE-2026-111497 documented in upstream 18.13.0),
`qwen3.8-27b` defaults to the `replace` edit tool while opaque `q38-ninfer` stays `hashline`,
provider-qualified selectors require exact matches, `model.loopGuard` settings reach custom
Responses models, and compaction bounds retained history and preserves a completed main summary if
an optional short summary fails. The
[client upgrade review](measurements/2026-10-30-omp-18140-client-upgrade-review.json) hashes all
three assets against upstream `SHA256SUMS.txt` and API digests and records two seven-check macOS
stub rehearsals; fresh live acceptance across all five documented routes (31 blocks), all three
stock 18.14.0 binaries, and both native public installs passed on frozen candidate `af62e766` in
`v0.15.0` ([v0.15.0 composed acceptance](../releases/v0.15.0/acceptance/composed-external-installation.json))
and on frozen candidate `56899320` in `v0.16.0`
([v0.16.0 composed acceptance](../releases/v0.16.0/acceptance/composed-external-installation.json)).

### v0.13.0–v0.14.0 client binding — OMP 18.12.6

Published releases **v0.13.0** (2026-10-25), **v0.13.1** (2026-10-26), and **v0.14.0** (2026-10-28)
pin unmodified upstream [v18.12.6](https://github.com/can1357/oh-my-pi/releases/tag/v18.12.6),
source `45c35e40c46166dc726ccc52f5d27f40f2449f99`, tree
`8a90a1b48b370649bd3f026d5f609e500626785c` (published upstream 2026-10-21); see
[immutable v0.14.0 client guide](https://github.com/alphastorm/omp-ninfer/blob/v0.14.0/docs/QUICKSTART.md#omp-18126-client). The
[client upgrade review](measurements/2026-10-25-omp-18126-client-upgrade-review.json) hashes all
three assets against upstream `SHA256SUMS.txt` and API digests, compares 18.12.6 against 18.12.1
on a loopback stub under the documented fragment and fail-closed config, and verifies image-aware
`snapcompact` gating and `omp -p` slash dispatch. Fresh live acceptance across all five documented
routes (31 blocks), all three stock 18.12.6 binaries, and both native public installs passed on
frozen candidate `b1a54dc9` in `v0.13.0`
([v0.13.0 composed acceptance](../releases/v0.13.0/acceptance/composed-external-installation.json)),
on frozen candidate `92dfb132` in `v0.13.1`
([v0.13.1 composed acceptance](../releases/v0.13.1/acceptance/composed-external-installation.json)),
and on frozen candidate `c81a8e7e` in `v0.14.0`
([v0.14.0 composed acceptance](../releases/v0.14.0/acceptance/composed-external-installation.json)).

### v0.12.2 client binding — OMP 18.12.1

Published release **v0.12.2** (2026-10-18) pins unmodified upstream
[v18.12.1](https://github.com/can1357/oh-my-pi/releases/tag/v18.12.1), source
`291e055836c210f314af3f73f53244e8e9d09de8`, tree `c9d897cc3f06d7cd80f7cacb5144c208efa70f62`
(published upstream 2026-10-17T23:14:21Z). All NInfer runtime, model, and profile pins carry
unchanged from v0.12.1; see the [immutable v0.12.2 client guide](https://github.com/alphastorm/omp-ninfer/blob/v0.12.2/docs/QUICKSTART.md#omp-18121-client).

This pull-in fixes defects on documented client paths rather than adding currency for its own
sake: 18.10.1's native Windows shell builtins resolved a drive-relative operand such as `C:`
against the process start directory, so `rm -rf C:` deleted that directory
([#15511](https://github.com/can1357/oh-my-pi/issues/15511), fixed in 18.11.0 by
[#15515](https://github.com/can1357/oh-my-pi/pull/15515)), and `omp -p` exited 0 after a failed run
([#15732](https://github.com/can1357/oh-my-pi/pull/15732) in 18.11.1,
[#15897](https://github.com/can1357/oh-my-pi/pull/15897) in 18.11.3). The
[client upgrade review](measurements/2026-10-18-omp-18121-client-upgrade-review.json) confirms each
merge commit is in 18.12.1 and absent from 18.10.1, hashes all three assets against the upstream
digests and `SHA256SUMS.txt`, and compares stock macOS 18.10.1 and 18.12.1 against a loopback stub
that emits NInfer-shaped Responses events under the documented fragment and fail-closed config:
tool turn, image input, `--continue`, and outage behave identically, and requests differ only in
user-agent and system prompt. It is not live route qualification; fresh live acceptance of all five
routes and both native public installs then passed on frozen `d7ed4a65`
([composed acceptance](../releases/v0.12.2/acceptance/composed-external-installation.json)).

### v0.12.1 client binding — OMP 18.10.1

Published release **v0.12.1** (2026-10-12) pins unmodified upstream
[v18.10.1](https://github.com/can1357/oh-my-pi/releases/tag/v18.10.1), source
`5d0aaffaf1f987503ce129a642fb6e30339615af` (published upstream 2026-10-12T05:55:11Z), as routine
upstream currency. All NInfer runtime, model, and profile pins carry unchanged from v0.12.0; see
[`QUICKSTART.md#omp-18101-client`](https://github.com/alphastorm/omp-ninfer/blob/v0.12.1/docs/QUICKSTART.md#omp-18101-client).

Two evidence records stay separate:

- **Host-free 18.8.7/18.10.0 Responses applicability review:** The
  [compatibility review receipt](measurements/2026-10-12-omp-18101-responses-compatibility-review.json)
  inspected both released NInfer emitter source pins (`1302d639` and `cad19767`,
  `src/serve/responses_schema.cpp`) and ran host-free loopback reproductions with stock OMP 18.8.7
  and 18.10.0 binaries against upstream commit `d95845494b`
  ([can1357/oh-my-pi#11863](https://github.com/can1357/oh-my-pi/pull/11863)). Because NInfer emits
  raw `reasoning_text` deltas with explicit `content_index` and `summary: []` and retains the
  identical full argument/input snapshot in `done`, `item-done`, and final response events, neither
  the 18.9.0 lossy-summary nor empty-terminal-input trigger occurs. That review is a specific
  non-applicability finding on 18.8.7 and 18.10.0, not live 18.10.1 route qualification.
- **Fresh 18.10.1 route and client acceptance:** Authorized-window acceptance ran separately on
  frozen candidate `780b0639` across all five documented routes (31 unchanged blocks), all three
  stock 18.10.1 binaries (macOS arm64 preview, Windows x64, Linux x64 under WSL2), and both native
  public installs, with independent restoration
  ([documented routes](../releases/v0.12.1/acceptance/documented-routes.json),
  [composed acceptance](../releases/v0.12.1/acceptance/composed-external-installation.json)).

## Running the watch

```bash
python3 scripts/upstream_watch.py --receipt docs/measurements/$(date +%F)-upstream-watch.json
# per-commit overlap scoring (one extra API call per upstream commit):
python3 scripts/upstream_watch.py --only ninfer-4090 --per-commit-files
```

Read-only: the tool only queries the GitHub API and writes the report file you name. Verdicts
are `up-to-date`, `upgrade-available`, or `error`; every upstream commit gets a class
(`fix`/`perf`/`feature`/`security`/`docs`/`test`/`chore`) and a recommendation
(`pull-candidate`, `next-release`, `review-now`, `ignore`). Recommendations are triage, not
decisions - a human owns every pull.

GitHub's compare endpoint lists at most 250 commits and 300 changed files and cuts a larger delta
without an error. The report records `commits_truncated` and `files_truncated`, and a cut file
list scores overlap as `unknown-truncated` rather than `no-direct-path-overlap` - before
2026-09-24 a cut list read as no overlap and marked every commit of a 1,387-file engine delta a
`pull-candidate`. For a delta that large, measure applicability against the fork itself (a
scratch cherry-pick or trial merge) instead of reading the overlap score.

## Historical engine watch — 2026-10-10

The [read-only watch receipt](measurements/2026-10-10-upstream-watch.json) records the
engine heads below. These are source-watch positions, not adopted runtimes or route acceptance.

| Engine upstream | Recorded head | Delta from recorded fork point | Evidence boundary |
| --- | --- | --- | --- |
| `Neroued/ninfer` | `81c8ce09` (2026-10-07) | 285 commits after `6e8b2e2a`; 250 listed | The API cuts both commits (250/285) and files (300); path overlap is **unknown-truncated**, not evidence of a clean merge. |
| `UDPSendToFailed/ninfer-4090` | `5c60b7c9` (2026-09-09) | 57 commits after `11aae2d6` | All 57 commits and 238 files listed; **high-review-overlap**. The head is unchanged; no native-lane adoption or fresh qualification is implied. |
| `Don-Chad/ninfer-3090` | `d7277e88` (2026-09-26) | 240 commits after `ef6ecc3c` | All 240 commits listed, but the 300-file list is cut; path overlap is **unknown-truncated**. The shipped native lane remains the separately qualified fork source. |

Upstream `81c8ce09` builds unmodified for **sm_120a** with **CUDA 13.1.115**
(`ninfer-serve` SHA-256 `31cc09a0…`, package-local image ID `c353844f…`).
Its README and model card require the v3 artifact container. The
documented `tools/upgrade_ninfer_v2_to_v3.py` path produced a separate v3 artifact
(`fc92d5e6…`) from the product's read-only `dc370fb6` v2 artifact (`0634abb0…`); it
installs the maintained chat template. This local build and upgrade are not a component cut,
published image, profile adoption, or acceptance run.

The [EXP-095 receipt](measurements/2026-10-10-upstream-81c8ce09-rtx5090.json)
preserves the production-contract sizing refusal: at DFlash2 K=7, BF16 KV, 131,072
context, concurrency two and two extra Device StateImages, upstream needs
11,971,039,745 bytes plus 1 GiB automatic headroom against 12,456,034,304 bytes
available after weights (**561.47 MiB short**). Explicit KV sizing removes that automatic
headroom, but concurrency four with two extra images (six total) still needs
14,030,279,169 bytes (**1,501.32 MiB short**). These are measured startup refusals,
not zero-throughput successes. The initial fork failure was the experiment launcher
omitting the repo-owned io_uring seccomp policy; it is not a fork engine regression.

Upstream's `b9114396` context-cache and preemptive-scheduling architecture remains
an in-process implementation, without the fork's durable disk session store. Its
`--host-context-mib` budget combines StateImages, KV and pause snapshots; the fork's
16 GiB Host KV pool plus 24 Host StateImage slots is a different backing policy.
Logical concurrency, extra cache images and persistence must not be conflated.
Removing both optional extra images does not rescue the requested C4 shape:
four total images still require **13,638,484,481 runtime bytes**, **1,127.67 MiB
short**. Both C4 attempts stop before any request, so there is **no C4 throughput
number** here; a smaller K/precision/context/chunk would be a different arm.

### Measured engine comparison — EXP-095

These are **local fixed-KV rehearsals**, not an installable profile or route
acceptance. The common arms explicitly allocate 131,072 KV tokens, bypassing the
automatic-headroom refusal above; they retain K=7/BF16/131,072/chunk-1,024/C2. The
fork's keep-warm and Host KV/StateImage backing are not identical to upstream's.

| Measurement | Fork `a59c13d0` | Upstream `81c8ce09` |
| --- | --- | --- |
| One-request low-reasoning corpus, 84 matched server-completed cases | **299.71 tok/s**, 15.12 ms/round | **251.29 tok/s**, 18.39 ms/round |
| A/B/B/A single-request decode at 0 / 32K / 64K / 120K | **367.72 / 356.67 / 344.49 / 290.96 tok/s** | **317.14 / 262.22 / 265.06 / 239.74 tok/s** |
| Same-input two-client pairs at 0 / 32K / 64K / 120K; client wall includes prefill/queue | **516.56 / 76.91 / 38.16 / 17.80 tok/s** | **437.44 / 76.11 / 38.26 / 15.58 tok/s** |
| Stored Responses 32K-root follow-up TTFT, two turns | **128.22 / 125.03 ms**; 41 / 34 tokens computed | **306.55 / 77.21 ms**; 558 / 34 tokens computed |
| JSON-schema controls, five schema families | Not a fork schema test; five corpus requests return HTTP 400 | **5/5 constrained and 5/5 unconstrained correct**; weighted decode time/token +2.51% |
| Durable disk session store | Product capability retained; restart not exercised in EXP-095 | No counterpart; context cache is in-process |

All 89 role input-case hashes match, but the matched decode set includes
reasoning-only client verdicts: fork has 10 plus five HTTP failures; upstream has
11. Full channels are byte-identical on **29/84** common server-completed cases
and **28/72** cases with non-error answers in both. Pair output identity is **0/8**
across engines; seeded within-engine repetitions match only **6/8 fork, 5/8
upstream**. The maintained v3 chat template differs even though all 1,184 tensor
payloads match, so this is not a same-tokenized-prompt or powered-quality claim.
At 120K, both pair arms observe an average decode batch of **1.0**; upstream logs
two preemptions and 108,544 replayed tokens, not always two-way GPU batching. The
five schema pairs have different token counts; the tiny 9/7-token tuple's
**+281.51%** time/token ratio must not be hidden by the +2.51% weighted aggregate.

**Historical EXP-095 verdict: continue selective backport, rather than re-port the fork's product
features onto upstream wholesale.** The fork is **19.27% faster** on the common
role decode set and has shorter rounds at every sampled context. Upstream gains
schema enforcement and preemption, but warm cache performance is mixed and the
common automatic BF16 shape refuses this card. Neither those individual features
nor a local counterfactual replaces the missing **durable disk session store**.
No upstream adoption, source modification, release, or profile promotion follows
from this comparison; the [full method and counters](PERFORMANCE.md#experiment-ledger)
and [content-safe receipt](measurements/2026-10-10-upstream-81c8ce09-rtx5090.json)
retain the exact limitations.

## Fork-network and upstream code watch — 2026-10-30

Read-only fork-network and upstream-code census as of 2026-10-30 against our `v0.14.0`–`v0.18.0`
engine base `64d10fbf`:

| Repository / artifact | Observed head (2026-10-30) | Scope and relation to `64d10fbf` | Position |
| --- | --- | --- | --- |
| `Neroued/ninfer` (`master` / `dev`) | `master` `1882c6ad` (2026-10-29, +215 commits over `64d10fbf`); `dev` `b57eaddc` (2026-10-30, +10 over `master`) | Zero commits in `64d10fbf..1882c6ad` or `1882c6ad..b57eaddc` touch the `NINFER_SM86`/`NINFER_SM89` architecture guards, Windows, or `Qwen3.5`-dense (`Qwen3.8-27B`) decode, `DFlash2`, or `MTP3` kernels (`docs/performance/qwen3.8-27b.md` remains the 2026-09-28 `7f6aafed` campaign), while upstream rewrote `src/models/qwen3_5/program/*`, `src/runtime/engine/*`, and `src/serve/*` | **Re-port onto `1882c6ad` not planned** (estimated 5–8 multi-agent days for `master`, 7–10 for `dev`). Take self-contained fixes and fork-local observability/checkpoint-reclaim ideas on the `64d10fbf` source lineage instead. |
| `ashalliants/ninfer-3090` (supersedes `Don-Chad/ninfer-3090`) | `master` `f5cec0a6` (2026-10-30, `v0.17.1-rtx3090`, PRs through `#408`); `Don-Chad/ninfer-3090` dormant at `d8c29253` (2026-10-16) | `Don-Chad/ninfer-3090` adopted `ashalliants/ninfer-3090` commit `931bd49b` in `1418aca3` ([PR #30](https://github.com/Don-Chad/ninfer-3090/pull/30)) and has no newer commits; `ashalliants/ninfer-3090` is the active `sm_86` fork (`rk4v4` 4-bit KV in `0b4f9588` / `2ba10da2`, `ReplaySSM` gate-caching state transactions, `--host-context-mib`, `--prefill-stall-budget-ms`, and its own `17.68 GiB` importance-matrix quantized artifact) | **Track `ashalliants/ninfer-3090` in place of `Don-Chad/ninfer-3090`.** Head-dim-256 (`D256`) `rk4v4` was ported into `alphastorm/ninfer` from `f5cec0a6` and deferred after restored continuation diverged from the zero-reuse cold reference at token 32 (`C1`) and tokens 16–32 (`C2`) on the RTX 3090 ([EXP-107](PERFORMANCE.md#experiment-ledger)). |
| `iamwavecut/ninfer-all` | `master` `c87b836d` (2026-10-30) | Consolidation hub (`sm_70`/`sm_75`/`sm_80`/`sm_86`/`sm_89`/`sm_120a`, `sm_86` default build) merging work from `ashalliants/ninfer-3090`, `UDPSendToFailed/ninfer-4090`, `TertiumOrganum1/ninfer-3090`, `Wallawalla47/infernix`, `13thblade/ninfer-all-nvfp4`, and `IMGillusion/ninfer-disk-kv`, including `FP32` vocabulary-head logits (`2013d01f`) | **Watch as the fork-network consolidation hub.** Opt-in `--fp32-head-logits` (`2013d01f`) was ported into `alphastorm/ninfer` and rejected on RTX 4090 depth-0 case `log-024@0` (`0.9016–0.9025` decode ratio vs `MTP3`, below `0.95`; [EXP-104](PERFORMANCE.md#experiment-ledger)). |
| `13thblade/ninfer-all-nvfp4` | `master` `245f3ad2` (2026-10-30) | `NVFP4` `W4A16` (`--nvfp4-w4a16`) on `sm_75`/`sm_86`/`sm_89`/`sm_120` and `W4A8-int` (`--nvfp4-w4a8-int`) on `sm_70`/`sm_75`/`sm_80`/`sm_86`/`sm_89`/`sm_120`, plus tensor-parallel partition fixes (`9ed54e1f`, `5e6ef4cb`, `b17f41aa`, `1069d4d7`) | **Watch item** for non-Blackwell `NVFP4` weight execution on `sm_86`/`sm_89`, subject to artifact fit and 1,120-prompt powered quality gates. |
| `IMGillusion/ninfer-disk-kv` and `IMGillusion/ninfer-engine` | `IMGillusion/ninfer-engine` `main` `82e5e826` (2026-10-30); also `troyliu0105/ninfer-all` `43c2e163` (`--disk-kv-path` commit `76940895`, low-precision `GGUF` `DFlash2`/`MTP` commit `d5889b2f`) | Host/disk L3 KV tier with read/write worker pool separation (`767e67e2`, `92bac11c`), two materialization slots (`8d9b28cb`), and device-to-host (`D2H`) spill settlement before staging reuse (`a0e2d900`) | **Watch item** for disk-backed KV tiering and staging-reuse invariants alongside our schema 3 checkpoint store. |
| `eagle-hq/EAGLE-4` and `EAGLE-Corp/Qwen3.8-27B-EAGLE4` | `eagle-hq/EAGLE-4` `0.1.1` (2026-10-21); `EAGLE-Corp/Qwen3.8-27B-EAGLE4` `f58a5985` (2026-10-19; upstream [#413](https://github.com/Neroued/ninfer/issues/413)) | `EAGLE-Corp/Qwen3.8-27B-EAGLE4` drafter for `Qwen3.8-27B` (`3,089,075,200` BF16 params / `6.18 GB` vs `z-lab/Qwen3.8-27B-DFlash2` `50307d4c` at `1,924,404,480` params / `3.85 GB`, unchanged since 2026-08-19; license field `other` / `eagle-4`) | **Watch item.** Requires license review, an autoregressive tree-verify engine path, and 24 GB fit analysis before any prototype branch. |

## Tracked upstream delta — 2026-09-28

| Upstream | Fork point | Delta | Position |
|---|---|---|---|
| `Neroued/ninfer` (engine; both mainline lanes build from one fork source) | `6e8b2e2a` (mainline base) | `d44ab584`, measured 2026-09-30 | **DFlash2 is worth taking, by port.** On `d44ab584` and the published v3 artifact, DFlash2 K=7 decoded the role corpus 28.2% faster than MTP3 on the same binary and 6.9% faster than the shipped runtime, at one request; it needs 1.65 GiB more weights and two fewer device state slots at two requests ([EXP-078](measurements/2026-09-30-dflash2-rtx5090.json)). Ported onto the fork's runtime (52 of upstream's 79 DFlash2-program commits, including `4b0eb36c`'s verify attention route for 24 query heads), it decodes the corpus 21.4% faster than shipped and 13.6% faster than upstream's DFlash2 at one request, with MTP3 byte-identical ([EXP-081](measurements/2026-09-30-dflash2-verify-route-rtx5090.json)); without that route its round grew with context ([EXP-079](measurements/2026-09-30-dflash2-fork-spike-rtx5090.json)). Two requests' rounds reached upstream's through the fork's own Q5 tensor-core route extended to 16 columns, not upstream's 16-column routes: a pair decodes 8.4% faster than shipped's ([EXP-082](measurements/2026-10-01-dflash2-pair-q5-tensor-cores-rtx5090.json)). Upstream has no durable session store; the fork carries DFlash2's draft context ring through its own checkpoints, with exact restores ([EXP-083](measurements/2026-10-01-dflash2-durable-store-rtx5090.json)). Upstream's NVFP4 KV, ported as final files from `d44ab584` behind the fork's storage identity, gives the two-request DFlash2 profile four device state slots and 262,144 KV tokens with rounds 12-27% shorter behind 32K-120K tokens ([EXP-084](measurements/2026-10-01-dflash2-nvfp4-kv-rtx5090.json)), but it failed the fork's powered quality screen against shipped MTP3 on unsupported claims and secret leaks, where DFlash2 with BF16 KV passed with 1,091 of 1,120 outputs byte-identical to shipped ([EXP-085](measurements/2026-10-01-dflash2-powered-quality-screen-rtx5090.json)). Upstream's MTP3 decode rounds are still 16-18% slower than the shipped runtime's and its fanout reuse is 0/4 against 4/4, so a merge alone is not the win ([EXP-065](measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json), [prior EXP-048](measurements/2026-09-24-engine-window-upstream-vs-shipped.json)). |
| `UDPSendToFailed/ninfer-4090` (4090 port) | `11aae2d6` | 57 commits at `5c60b7c9` (unchanged since 2026-09-09) | 9 of 51 candidates apply cleanly, all kernel retunes (EXP-045). The fixes this lane wants - chunked KV snapshot staging, the MTP restore stride, publishing finished snapshot saves, WDDM residency budgeting, the D3D12 residency fence, the admission shortfall and `/health` - conflict in files the fork changed and are read against v0.7.1's durability work when taken. Upstream removed its NVFP4 path (`dabae909`). |
| `Don-Chad/ninfer-3090` (3090 port; later superseded by `ashalliants/ninfer-3090` `f5cec0a6`, 2026-10-30) | `ef6ecc3c` | 141 commits at `75d94eab` (unchanged since 2026-08-31; final repo commit `d8c29253` on 2026-10-16 after adopting `ashalliants/ninfer-3090`) | At this 2026-09-28 report, triage awaited the RTX 3090 host. v0.9.1 accepts the standalone native lane from mainline source `f08309da`; active 3090 fork tracking moved to `ashalliants/ninfer-3090` above. |
| `can1357/oh-my-pi` (client) | Upstream v18.4.0 (`401778d0cd30020ce0f9198f751b13c68850562f`) | Unmodified upstream release binary; published 2026-09-28T03:33:34Z | v0.8.6 pins 18.4.0; all four documented routes passed. Fix `9d3e0d4975` resolves the Windows completion-status defect ([#13470](https://github.com/can1357/oh-my-pi/issues/13470), [EXP-070](measurements/2026-09-28-omp-1840-windows-completion-status.json)). RTX 5090 fragments now set `compat.supportsImageDetailOriginal: false` for automatic compaction ([EXP-071](measurements/2026-09-28-omp-snapcompact-image-detail.json)). The route config now sets `compaction.asyncEnabled: false`: three RTX 4090 handoffs took 77.0-83.7 s each with no expired admission; RTX 5090 snapcompact took 0.07-0.08 s ([EXP-072](measurements/2026-09-28-omp-long-sessions.json)); provider fields and `PI_OPENAI_STATEFUL=1` are unchanged; no fork build, archive, installer or cask. |

**Historical client position through v0.7.4.** `omp-18.2.3-cross-platform-beta-1` (source
`5ade242d`, since v0.7.3) carried 36 downstream commits on upstream `a2d83061` (v18.2.3),
including the NInfer provider and appliance lifecycle. The 2026-09-24 watch counted 681 upstream
commits to `62bc57be` (v18.3.0). At that time, the client plan was a rebase plus documented-route
acceptance rather than direct adoption
([EXP-046](measurements/2026-09-17-client-repin-evaluation.json)); v0.8.0 instead uses the stock
binary with the stock-client runtime.

### v0.6.9: parser semantics without the serve-adapter rebase

The [2026-09-12 backport ledger](measurements/2026-09-12-upstream-backport-ledger.json) and the
2026-09-13 delta counts it was read against are historical evidence for this release. The ledger
deferred `3b50962b` and `0c5d570c` because their extracted parser files do not exist on this
tree. The v0.6.9 release instead implements their semantics independently in the downstream
parser: supported scalar unions, case-insensitive
booleans, precise numeric lexemes, mathematically integral values, duplicate parameters, and
balanced embedded markup. It does not import the wholesale serve-adapter rebase or change the
fork point; custom raw input, history, opaque IDs, and stream ownership are preserved.

Reviewed source `696e78c7b4e3ac28ffcffafc73acc1496e65ef03` includes remediation against
malformed-region rescans and recursive union traversal; bytewise regressions and an 8,192-deep
union case pass. It builds the published RTX 5090 `v0.6.5-qwen38-5090-beta.1` and native
RTX 4090 `v0.6.3-qwen38-4090-beta.1` components. Both lanes are qualified and RTX 4090
public-URL already-installed acceptance passed; the RTX 5090 documented host 2/2 and macOS
10/10 routes passed against the published image.
[Release notes](../releases/v0.6.9/NINFER_RELEASE_NOTES.md).
The old backport ledger is intentionally unchanged: its deferred parser entry describes that
earlier campaign, not the candidate's current parser coverage. The deferred pressure-planner
family is separate; the alternating-session finding is already attributed to host KV capacity
([EXP-039](measurements/2026-09-13-hostkv-capacity-multisession.json)), not proof that this
product needs that planner rebase.

## Why the fork points are what they are

- Since `v0.13.0`, the RTX 5090 container lane builds from upstream `Neroued/ninfer` master
  `64d10fbf` (selected source `48c8ac46` in `v0.18.0`; `e0971faf` in `v0.17.0`; `a87de361` in `v0.16.2`; `26fa28d0` in `v0.16.0`; `2c6f423b` in `v0.14.0`–`v0.15.0`; `6d4d0a05` in `v0.13.0`–`v0.13.1`). From
  v0.6.2 through v0.12.2, it built from the mainline runtime whose upstream base was `6e8b2e2a`
  (selected source `1302d639` in v0.11.0–v0.12.2). The retired container mirror point `4eef14a7`
  was the lineage's base before v0.6.2 and made the delta read 17 commits larger than it was.
- The RTX 4090 and RTX 3090 native Windows lanes originally vendored their upstreams at the
  recorded commits (`11aae2d6` and `ef6ecc3c`). In `v0.18.0`, both share frozen source `48c8ac46`
  with the RTX 5090 container on upstream `Neroued/ninfer` master `64d10fbf`
  (`v0.8.0-qwen38-4090-beta.3` default and `v0.8.0-qwen38-3090-beta.3` `tc`), after building from
  `a87de361` in `v0.16.2`–`v0.17.0` (`v0.8.0-qwen38-4090-beta.2` and `v0.8.0-qwen38-3090-beta.2`,
  carried unchanged in `v0.17.0` while RTX 5090 advanced to `e0971faf`), sharing `26fa28d0`
  (`v0.8.0-qwen38-4090-beta.1` and `v0.8.0-qwen38-3090-beta.1`) in `v0.16.0`, `2c6f423b`
  (`v0.7.0-qwen38-4090-beta.3` and `v0.7.0-qwen38-3090-beta.3`) in `v0.14.0`–`v0.15.0`, and initial
  `64d10fbf` rebases at `7a25cd72` (`v0.7.0-qwen38-4090-beta.2` and `v0.7.0-qwen38-3090-beta.2`) in `v0.13.1`. From
  v0.12.0 through v0.13.0 they shipped from the mainline fork runtime (`cad19767` on `6e8b2e2a`,
  adding explicit `--gpu-uuid` device selection on the two-GPU Windows host; earlier v0.9.1 retained
  RTX 4090 source `cba7eb93`, RTX 5090 child `e20060b6`, and RTX 3090 `f08309da`). The
  durable-checkpoint, security, and packaging work remains downstream.
- Through v0.7.4, the client fork point was the upstream tag commit onto which downstream patches
  rebased. Since v0.8.0 (and in v0.18.0 with stock OMP 18.18.7 at `e325ffc7`; v0.17.0 with stock OMP 18.18.6 at `9058ab9d`; v0.16.2 with stock OMP 18.15.0 at `3fedf8d5`; v0.15.0–v0.16.0 with stock OMP 18.14.0 at `31147f9d`), this
  repository does not build or publish an OMP client; it binds the unmodified upstream release
  binary instead.

## History

### Published baseline client — OMP 18.8.7

Historical v0.11.0 and v0.12.0 client baseline (superseded by OMP 18.10.1 in v0.12.1).

| Upstream | Client pin | State | Why pull it in |
| --- | --- | --- | --- |
| `can1357/oh-my-pi` (client) | Unmodified upstream v18.8.7 (`f261ed9faf16b61880b544f599876bface4ded0d`), published upstream 2026-10-09T13:45:03Z | Published in RTX 5090-only v0.11.0 and three-lane v0.12.0 (2026-10-11); superseded by 18.10.1 in v0.12.1 | [#14334](https://github.com/can1357/oh-my-pi/pull/14334) releases completed one-shot routing state without clearing the main Responses chain; [#14952](https://github.com/can1357/oh-my-pi/pull/14952) adds optional per-model compaction thresholds. |

The previous unqualified 18.8.3 candidate first brought in #13686 (`429352901c`),
#13687 (`01822b63d0`) and #13689 (`8aaf115b8e`): per-model stateful Responses,
custom-host auto image detail and fail-closed unavailable-model resume. Those changes remain
in 18.8.7 and 18.10.1. Keep `compat.statefulResponses: true` in every NInfer model, remove
`PI_OPENAI_STATEFUL` from the launch environment, and do not restore the image-detail override.
The [schema](https://github.com/can1357/oh-my-pi/blob/f261ed9faf16b61880b544f599876bface4ded0d/packages/coding-agent/src/config/models-config-schema-bundle.ts#L74)
still admits the field. The [Responses handler](https://github.com/can1357/oh-my-pi/blob/f261ed9faf16b61880b544f599876bface4ded0d/packages/ai/src/providers/openai-responses.ts#L503-L514)
still gives a call option and then the environment precedence over per-model compat.

#### 18.8.4–18.8.7 source review

The release notes were read for [18.8.4](https://github.com/can1357/oh-my-pi/releases/tag/v18.8.4),
[18.8.5](https://github.com/can1357/oh-my-pi/releases/tag/v18.8.5),
[18.8.6](https://github.com/can1357/oh-my-pi/releases/tag/v18.8.6) and
[18.8.7](https://github.com/can1357/oh-my-pi/releases/tag/v18.8.7).
Between the 18.8.3 and 18.8.7 tags, the custom-model schema, `openai-shared.ts`,
`ai/src/stream.ts` and `settings-stream-fn.ts` have identical Git blobs. The fragments'
`includeEncryptedReasoning: false`, `supportsReasoningSummary: false`, effort list,
`openai-responses` API and custom-host auto image-detail contract are unchanged.
The Windows rust-analyzer/lspmux fix in 18.8.5 and native-addon packaging change in 18.8.7
are not Responses protocol changes. In the 2026-10-10 local rehearsals on
`c007286eee280d0a98ff912dc04ebe2e7dd9eb77` against v0.10.0 image `fff4ee38…`, the macOS arm64,
Windows x64, and Linux x64 (WSL2) binaries passed bounded local rehearsal checks rather than route
qualification:
[macOS arm64 rehearsal](measurements/2026-10-10-omp-1887-darwin-arm64-local-rehearsal.json) ·
[Windows x64 rehearsal](measurements/2026-10-10-omp-1887-windows-x64-local-rehearsal.json) ·
[Linux x64 WSL2 rehearsal](measurements/2026-10-10-omp-1887-linux-x64-wsl2-local-rehearsal.json) ·
[client release review](measurements/2026-10-10-omp-1887-client-release-review.json).

**#14334 and chaining.** [Provider state](https://github.com/can1357/oh-my-pi/blob/f261ed9faf16b61880b544f599876bface4ded0d/packages/ai/src/providers/openai-responses.ts#L429-L450)
now implements `releaseSession`: it normalizes the supplied routing-session id and deletes
only chain/effort entries for that id. Chain lookup is still keyed by base URL, model and
routing-session id, and unchanged append-prefix logic sends `previous_response_id` plus delta
input with `store: true`; changed history or a stale response id still causes full replay.
[AgentSession](https://github.com/can1357/oh-my-pi/blob/f261ed9faf16b61880b544f599876bface4ded0d/packages/coding-agent/src/session/agent-session.ts#L11009-L11086)
releases a one-shot side request in `finally` only when it has no `conversationKey`.
The main conversation and keyed side-conversation lineages are retained. **[inference]** This
cleanup preserves the fragments' stateful-chaining contract; source inspection alone is not
route acceptance or a long-session proof.

**Compaction finding.** The [async default](https://github.com/can1357/oh-my-pi/blob/f261ed9faf16b61880b544f599876bface4ded0d/packages/coding-agent/src/session/context-settings.ts#L207-L223)
is still `true`; [the background gates](https://github.com/can1357/oh-my-pi/blob/f261ed9faf16b61880b544f599876bface4ded0d/packages/coding-agent/src/session/session-maintenance.ts#L2077)
still stop when `asyncEnabled === false`. #14952 routes these checks through
[resolveModelCompactionSettings](https://github.com/can1357/oh-my-pi/blob/f261ed9faf16b61880b544f599876bface4ded0d/packages/coding-agent/src/session/model-compaction-threshold.ts#L20-L30).
The new map defaults empty and changes only threshold token/percentage fields when an entry
matches (exact `provider/model-id` first, then longest trailing-`*` prefix); no match returns
the existing settings object. It does not turn async compaction on or off.
The [provider in-flight gate](https://github.com/can1357/oh-my-pi/blob/f261ed9faf16b61880b544f599876bface4ded0d/packages/ai/src/stream.ts#L637-L654)
still waits before dispatch until a slot or caller cancellation, not the server's pending
admission deadline. Keep the settings in `examples/manual-tunnel/fail-closed.yml` unchanged: two requests for
RTX 5090 providers, one for native providers, no `asyncEnabled` override. This retains the
client-side waiting contract motivated by [EXP-072](measurements/2026-09-28-omp-long-sessions.json).
No `compaction.modelThresholds` setting is recommended or applied: 18.8.7 long-session or
threshold tuning was not measured, and #14952 alone supplies no evidence for a safer numeric
limit. The 18.8.6 pruning changes target Anthropic cache lookback, not a new NInfer threshold.

In historical v0.11.0, the three RTX 5090 documented routes passed with OMP 18.8.7 while the
native RTX 3090/4090 lanes were deferred to v0.12.0 (where all five routes passed with 18.8.7).
Local client rehearsals remain separate evidence and do not inherit v0.10.0's OMP 18.4.10
acceptance. The [2026-10-10 source review and receipts](measurements/2026-10-10-omp-1887-client-release-review.json)
bind the observed image, three binary hashes and pass/fail checks. Shared proof environment
selection also retains the per-model contract after a profile is qualified, while the
historical 18.4.x driver behavior is unchanged.
See the [prepared client guide](QUICKSTART.md#omp-18126-client).

The v0.11.0 release bound this upstream client to published runtime source `1302d639` and image
`6a02feba`, with the retained client and route proofs accepted. EXP-095 above compares the
superseded `a59c13d0` EXP-094 arm, **not** the selected `1302d639` binary; its counterfactual
labels and verdicts are not silently rebound.

### Published upstream position — v0.10.0

In v0.10.0 (2026-10-02, unmodified upstream OMP 18.4.10), RTX 5090 moved to
`v0.6.15-qwen38-5090-beta.1`, image `fff4ee38`, server `7a8908e8` and source `eaf221ac`, with model
artifact `0634abb0`. Its `qwen38-5090-v0.10.0` profile / configuration `8b2f4959` uses **DFlash2
draft window 7**, **BF16 KV**, **two requests in flight** and **two device state slots**. The
qualified KV pool is 131,520 tokens; both prompts plus output reservations must fit. The pending
timeout is 180 s. Predecessor performance and checkpoint-reuse results do not qualify this changed
runtime and model.

RTX 4090 kept `v0.6.10-qwen38-4090-beta.1`; RTX 3090 kept `v0.6.2-qwen38-3090-beta.1`. Their
native packages and model were unchanged, while their product pin and client moved to v0.10.0 /
OMP 18.4.10. Historical OMP 18.4.0 observations below remain historical evidence, not fresh OMP
18.4.10 acceptance. The RTX 3090 fleet scout role stayed deferred. Full v0.10.0 acceptance details
live in [`RELEASES.md`](RELEASES.md#v0100-public-release--dflash2-on-the-rtx-5090).

[Manifest](../releases/v0.10.0/manifest.json) ·
[Route acceptance](../releases/v0.10.0/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.10.0/acceptance/composed-external-installation.json).

### Historical upstream position — v0.9.1

Install through the [quickstart](QUICKSTART.md); eligibility is one RTX 5090, RTX 4090
or RTX 3090. **v0.9.1 — RTX 3090 on the native Windows runtime** was accepted on 2026-10-01.

The RTX 3090 joins with `v0.6.2-qwen38-3090-beta.1` (package `da1d62f2`, server
`11b3f93c`), deployment profile `qwen38-3090-native-v0.6.2-beta.1` and configuration
`0f700667`. Source `f08309da` is the RTX 5090 v0.6.14 source `e20060b6`, whose parent
is the RTX 4090's `cba7eb93`, plus one controller fix, built for **sm_86**. It has the
RTX 4090's native lifecycle: a managed scheduled task, protected state root, graceful stop
that saves live sessions, durable session checkpoints and rollback to the previous release.

The lane serves **one request at a time**, with a **30 s** pending timeout, **131,072 tokens
of INT8 KV**, MTP3, an **8192 MiB** host-KV pool and **24 host-state slots**. Keep-warm is off;
no host-memory floor is declared because it was qualified on one host. The GPU-owner
controller holds the card at **300 W** while serving and restores the owner's **370 W** limit
on stop. Both native lanes are text/tools; vision remains an RTX 5090 container capability.

The RTX 5090 and RTX 4090 components, profiles, model and memory floors are byte-identical to
v0.9.0. The RTX 5090 stays on `v0.6.14-qwen38-5090-beta.1` (image `4c816b0c`, server
`f62a570e`, source `e20060b6`), profile `qwen38-5090-v0.9.0` and configuration
`cf1de114`, with two requests in flight. The RTX 4090 stays on
`v0.6.10-qwen38-4090-beta.1` (package `a0ea4c81`, server `e0498fad`, source
`cba7eb93`), configuration `7a69481f`, with one request at a time. Existing owners change
nothing: the unmodified OMP 18.4.0 binary, `models.yml`, `PI_OPENAI_STATEFUL=1` and their
launch are unchanged. The RTX 3090 serves the same model artifact, `eec39564…`.

The [RTX 3090 lane qualification](../releases/v0.9.1/qualification/rtx3090.json) passed **all
15 lifecycle phases** on the physical card:

- **130,048-token retrieval was exact in 221.0 s** at the 131,072-token ceiling.
- C1 decode reached **102.64 tok/s** with **93.43% MTP acceptance**, peaking at **299.92 W**
  under the 300 W cap. This trajectory-sensitive fixture has no like-for-like predecessor
  on this lane's runtime; it is not a speed-up claim against the historical v0.7.2 route.
- A **104.5 s restart** restored a previously unpublished session saved by the managed stop.
- Rollback passed in both directions against the lane's **unpublished v0.6.0-beta.1** package;
  that predecessor stops by termination because it predates the stop-event channel.
- Protected state denied two low-privilege reads; the 15-check agent protocol passed at the
  shipped host pool and with 8 host-state slots; unmodified upstream OMP 18.4.0 passed its
  typed tool call.

Three fixes shipped with the lane:

1. **Rollback reads the release's own configuration.** The first qualification window at
   `e20060b6` failed rollback before launching its predecessor: the shared Windows controller
   read `context_cache.host_kv_mib` directly under PowerShell strict mode, but v0.6.0 predates
   that field. Source `f08309da` passes `--host-kv-mib` only when the release declares it,
   as it already did for `gpu_keep_warm_ms`. Lifecycle tests now require that treatment for
   every configuration field newer than the shipped lineage. Every published RTX 4090
   package declares the field, so the unchanged RTX 4090 lane was never exposed.
2. **OMP sends the RTX 3090 one request at a time.** Change `4c5ba8d` adds
   `ninfer-native-3090: 1` under `providers.maxInFlightRequests` in
   [the route configuration](../examples/manual-tunnel/fail-closed.yml). Merge that entry into
   `~/.omp/agent/config.yml` when following the RTX 3090 native quickstart. OMP leaves an
   unlisted provider unlimited; a request beyond the lane's one waits at the server and
   expires after 30 s.
3. **Acceptance judges scheduled tasks by definition and enabled state.** The first RTX 5090
   window passed every route, client probe and restoration check, but its summary refused a
   task snapshot: the five-minute container-host supervisor was `Running` at baseline and
   `Ready` afterwards, with an unchanged definition. Change `0073553` makes
   [the acceptance summary](../scripts/hosts/accept-rtx5090-routes.py) require byte-identical hold
   markers and each OMP task present, identically defined and as enabled as before. The
   collected evidence passed the corrected summary; a test covers both state directions.

All **five documented routes passed 31 steps** on candidate `c55185dd`
(`c55185dd39cbdb440620721c2a9d0dc06de010f4`) with unmodified OMP 18.4.0 and the published
components: RTX 5090 container host 2, macOS client 10, Windows client 5, RTX 4090 native
Windows 7 and RTX 3090 native Windows 7; all three hosts were restored. The upstream macOS
arm64 (preview), Windows x64 and Linux x64 binaries each passed a typed tool turn, an exact
continuation and a fail-closed request against image `4c816b0c`. Linux ran under **WSL2**,
not a separately qualified Linux OS; macOS remains preview, without a managed installation
or appliance lifecycle.
[Documented routes](../releases/v0.9.1/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.9.1/acceptance/composed-external-installation.json).

Both native routes installed from public assets. The RTX 3090 route performed a fresh
canonical upgrade installation of the published package, then passed typed-tool,
continuation and fail-closed checks, with prior state restored; this is not an idempotent
reinstall claim ([public install](../releases/v0.9.1/acceptance/rtx3090-public-install.json)).
The RTX 3090 console was signed out: a managed start refuses while any process holds at
least 1 GiB of GPU memory, and the signed-in desktop's compositor alone held about 1,070 MiB.

The RTX 5090 routes ran in **two production windows** from the maintainer's Apple silicon
workstation over the tailnet. Downtime was at most **408.4 s (6.8 min)** and **386.5 s
(6.4 min)**. After the first window's task-snapshot summary refusal, a corrected window on
the same candidate passed in fresh workspaces
([restoration](measurements/2026-10-01-v091-acceptance-restoration.json)).

The historical v0.7.2 RTX 3090 route remains separate: its durable v0.2 lineage and OMP
18.0.9 fork client are not this lane, and its sessions do not carry over. The standalone
native lane is accepted; the **fleet RTX 3090 scout role stays deferred**, and the
**upstream engine merge remains open**.
[Release notes](../releases/v0.9.1/NINFER_RELEASE_NOTES.md) ·
[Manifest](../releases/v0.9.1/manifest.json) · [Qualification](../releases/v0.9.1/qualification.json).

**Upstream item: controller compatibility across rollback.** The `f08309da` fix belongs to
shared Windows lifecycle code, not an sm_86 kernel retune: a newer controller must launch
an older release using that release's declared configuration, without requiring fields
introduced later. The optional-field rule and its lifecycle regression coverage are the
reusable change. This release does not take the deferred upstream engine merge.

### Historical position — v0.9.0

The RTX 5090 serves **two requests at once** with `v0.6.14-qwen38-5090-beta.1`
(image `4c816b0c`, server `f62a570e`), deployment profile `qwen38-5090-v0.9.0` and
configuration `cf1de114`. The eight-token MTP3 verify round now uses the Q5 tensor-core route
instead of SIMT kernels. Two decoding requests reached **281.1-283.0 tok/s together**, against
166.7-167.1 one at a time (**1.68-1.70x**), up from v0.6.13's 190.0-191.1 with two requests.
The candidate answered the role corpus byte-identically to v0.6.13, two cases at a time and one
at a time (**89/89**); the published image matched both the candidate and v0.6.13 (**89/89**)
([EXP-077](measurements/2026-09-29-rtx5090-two-requests-in-flight.json)).

The profile adds `--max-concurrency 2 --pending-timeout-ms 180000`. A request that cannot fit
beside the running one can wait **180 s**: the wait plus the longest root prefill, **130,048
tokens in 58.4 s** on the published image, stays inside OMP's **300 s** stream-idle watchdog.
The server ends a too-long wait and OMP resends. KV capacity auto-resolves to **160,256 tokens**;
VRAM after load is **30,242-30,244 MiB** of 32,607 MiB, against 28,144 MiB with one request.
Keep-warm, 16384 MiB host KV, the 24 GiB checkpoint quota, BF16 KV, MTP3, 131,072-token context
and the 28672 MiB runtime-host floor are unchanged.

The config every documented route installs,
[`examples/manual-tunnel/fail-closed.yml`](../examples/manual-tunnel/fail-closed.yml), sets the RTX 5090
providers to two requests in flight and keeps the RTX 4090 providers at one:

```yaml
providers:
  maxInFlightRequests:
    ninfer-beta: 2
    ninfer-native-4090: 1
    ninfer-main: 2
    ninfer-heavy: 1
```

**Upgrade the RTX 5090 server first**, then merge these limits into `~/.omp/agent/config.yml`,
including any other NInfer provider id you declare. A limit of 2 against the old one-at-a-time
server queues requests at its 30 s deadline, where they can expire. RTX 5090 checkpoints saved
by v0.8.7 re-prefill once after the build change. RTX 4090 stays on
`v0.6.10-qwen38-4090-beta.1` (package `a0ea4c81`, server `e0498fad`, configuration
`7a69481f`), one request at a time with a 30 s pending timeout; its checkpoints carry over.
The unmodified OMP 18.4.0 binary, `models.yml`, `PI_OPENAI_STATEFUL=1` and model are unchanged.

The [final-profile lane evidence](../releases/v0.9.0/qualification/rtx5090.json) was collected on the
candidate image with the same server binary and arguments as the published image:

- Stock OMP durable sessions passed. EXP-072 long sessions at limit 2 had no root prefill over
  60K tokens; the third planting run stopped at the same harness precondition as v0.8.7.
- With 35 short sessions filling the 24 GiB store, a 60,026-token session reused **60,057 cached
  tokens after a crash in 2.99 s**.
- EXP-050's workload and resume restored **4/4 stored sessions** from checkpoints; stop saved 1
  and refused 0. EXP-051's held turn resumed exactly, but deferred save before eviction did not
  arise at two requests: the evicting session was admitted beside the held one.
- Fanout, warm-arrival, restore and multisession probes passed; **2 of 8** multisession
  continuations/forks lost reuse, as in v0.8.7. None of **24 fresh agent sessions** fell back to
  root, with median time to first token **0.092-0.100 s**.
- Restarting with two requests in flight ended both streams with `response.incomplete`; both
  continuations reused **62,404 cached tokens**, with first output in **5.07-5.53 s** and no
  refused shutdown saves.

On the published image, **130,048-token retrieval was exact in 58.4 s**, decode reached
**169.79 tok/s over 2,048 tokens**, the agent protocol passed across a restart, and VRAM after
load was **30,242 MiB**. Lane qualification and documented-route acceptance are separate evidence.

The costs remain visible: decode beside a 71,641-token prefill ran at **30.4-30.6 tok/s**, and a
request arriving during a staged prefill waited **26.6-26.7 s**. Two sessions above about **47K
tokens each take turns** (inferred from the admission rule; not measured with OMP). Two
alternating 62.4K-token sessions re-prefilled some continuations from root at both limits.
Stock OMP wall time followed generated tokens, with one run per limit per window: **no claim
that OMP work finishes sooner**. The robust gain is aggregate decode. Checkpoints remain best
effort; after the concurrency probe's evictions, stop refused 7 saves at two requests and 5
at one because the newest turns were no longer resident.

All four documented routes passed **24 steps** on candidate `0d2a7468`
(`0d2a746814aaddca328af7bf2582e48dbf6ce950`) with unmodified OMP 18.4.0 and the published
components: RTX 5090 container host 2, macOS client 10, Windows client 5 and RTX 4090 native
Windows 7; both hosts were restored. The upstream macOS arm64
(preview), Windows x64 and Linux x64 binaries each passed a typed tool turn, an exact
continuation and a fail-closed request against image `4c816b0c`. Linux ran under **WSL2**, not
a separately qualified Linux OS.
[Documented routes](../releases/v0.9.0/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.9.0/acceptance/composed-external-installation.json).

The RTX 5090 routes ran in **three production windows** from the maintainer's Apple silicon
workstation over the tailnet. Downtime was at most **101.5 s (1.7 min)** and **324.3 s
(5.4 min)** in the two failed windows and **499.3 s (8.3 min)** in the accepted window; total
downtime was at most **925.0 s (15.4 min)**
([restoration](measurements/2026-09-30-v090-acceptance-restoration.json)).

Candidate `54f1402e` passed the RTX 4090 route, but its RTX 5090 window failed at the
container-host route's start step: the launcher still required the server to report one request
in flight, and the v0.9.0 profile serves two. The launcher now checks the concurrency, context
and KV type its profile declares. Production was back within 101.5 s, but the window's Windows
hold stayed up 10 min longer, because its WSL-side release went through an interop relay that
cannot start Windows processes; the host script now picks a live relay. Candidate `9eca7bae`
passed the RTX 4090 route and the container-host route, but in its RTX 5090 window the Linux
client sent no request in 210 s: OMP 18.4.0's print mode reads piped stdin to EOF before it
starts, and the window's drivers had forwarded a terminal that never closes. Every acceptance
client now reads an empty stdin. Candidate `0d2a7468` passed the RTX 4090 route and a third
RTX 5090 window.

RTX 3090 remains deferred. [Release notes](../releases/v0.9.0/NINFER_RELEASE_NOTES.md) ·
[Manifest](../releases/v0.9.0/manifest.json) · [Qualification](../releases/v0.9.0/qualification.json).

**Upstream item: resumed sessions' first request.** OMP 18.4.0 still omits earlier reasoning
on the first request from a resumed OMP process, so that request re-prefills from root even
when the server restored a current checkpoint. The next request carries reasoning again and
caches. The v0.8.7 measurement below remains the evidence; two requests in flight do not fix
client replay ([EXP-074](measurements/2026-09-29-long-session-cache.json)).

### Historical position — v0.8.7

Long sessions no longer re-prefill from root at compaction handoffs, near-capacity turns, crashes
after a compaction, or when short sessions fill the checkpoint store. Both lanes move to runtimes
with the same fixes: RTX 5090 `v0.6.13-qwen38-5090-beta.1` (image `d71e34c3`, server `b8ae62ae`)
and RTX 4090 `v0.6.10-qwen38-4090-beta.1` (package `a0ea4c81`, server `e0498fad`). The config every
documented route installs, [`examples/manual-tunnel/fail-closed.yml`](../examples/manual-tunnel/fail-closed.yml),
limits each NInfer provider to one request in flight and leaves compaction at OMP's default, so OMP
compacts in the background again and the turn that meets a running summary waits in OMP instead of
expiring at the server ([EXP-074](measurements/2026-09-29-long-session-cache.json)):

- RTX 4090 compaction handoffs reused **78.0-79.9K cached tokens** and reached the first token in
  **0.58-0.70 s**; v0.6.9 prefilled 97.4-97.5K tokens from root in 63.8-66.3 s.
- Near-capacity turns whose planner search runs out of time keep their continuation. In three
  stock OMP sessions on the RTX 5090, the three fallback turns reused **78.0-80.5K cached tokens**
  (12.4-12.5 s to the first token) and **no turn prefilled more than 60K tokens from root**;
  v0.6.12 production's log holds four such turns of 93.7-105.1K tokens, each prefilled from root.
- After a hard kill following a compaction, the next RTX 4090 turn reused **32,167 cached tokens
  in 2.9 s**; v0.6.9 prefilled 32,173 tokens from root in 29.2 s.
- With 35 short sessions filling the RTX 5090's 24 GiB checkpoint store, a 60,026-token session
  kept its checkpoint and after a crash reused **60,057 cached tokens in 2.9 s** (3.1 s on the
  RTX 4090); v0.6.9 had reclaimed that checkpoint first and failed the turn with
  `previous_response_not_found`.
- With the provider limit, three RTX 4090 handoff compactions and a restart ran **55 requests with
  none expired**, and 22 turns took **365.4 s** where v0.8.6's inline compaction took 678.2 s for
  24. The limit must name the route's own provider id: OMP leaves an unlisted provider unlimited.

The kernels are unchanged. The RTX 5090 candidate and published image answered the 89-case role
corpus byte-identically to v0.6.12, and the published image prefilled **130,048 tokens exactly in
58.3 s** and decoded **170.36 tok/s**. The RTX 4090 package passed all 15 canonical phases with
OMP 18.4.0: 130,048-token retrieval in 91.2 s and C1 decode at **157.91 tok/s** with 87.59% MTP
acceptance. Stock OMP 18.4.0 kept one session across graceful restarts on both runtimes, and every
turn after the seed reused its cache
([EXP-075](measurements/2026-09-29-stock-omp-1840-durable-sessions.json)).

These are one run per configuration, with synthetic build-log filler, one seed and thinking
`low`. A restart of the OMP process still costs one prefill of a resumed session's context:
OMP 18.4.0's first request after resuming omits the session's reasoning (56,174 tokens from root,
32.0 s, in EXP-074). A server restart alone restores hot, so v0.8.6's stale-checkpoint account of
that cold turn was wrong. Both server builds change, so each saved session re-prefills once after
the upgrade. To upgrade from v0.8.6, follow the quickstart for your lane, remove
`compaction.asyncEnabled: false` from `~/.omp/agent/config.yml` and merge:

```yaml
providers:
  maxInFlightRequests:
    ninfer-beta: 1
    ninfer-native-4090: 1
    ninfer-main: 1
    ninfer-heavy: 1
```

The OMP binary, `models.yml` and `PI_OPENAI_STATEFUL=1` do not change. RTX 3090 remains deferred.

All four documented routes passed **24 steps** on candidate `a1e51a70`
(`a1e51a7064a1b0a5e862f9b77ae8815f8144012d`) with unmodified OMP 18.4.0 and the published
components: RTX 5090 container host 2, macOS client 10, Windows client 5 and RTX 4090 native
Windows 7; both hosts were restored. The upstream macOS arm64 (preview), Windows x64 and
Linux x64 binaries each passed a typed tool turn, an exact continuation and a fail-closed
request against image `d71e34c3`. Linux ran under **WSL2**, not a separately qualified Linux OS.
[Documented routes](../releases/v0.8.7/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.8.7/acceptance/composed-external-installation.json).

The RTX 5090 routes ran in **two production windows** from a separately hosted Apple silicon
Mac mini. Downtime was at most **264.5 s (4.4 min)** in the failed window and
**384.1 s (6.4 min)** in the accepted window; total downtime was at most
**648.6 s** ([restoration](measurements/2026-09-29-v087-acceptance-restoration.json)).

Candidate `9474326f` passed the RTX 4090 route, but its RTX 5090 window failed at the macOS
restart step. That step seeds its session with the release's own documents, which quoted the
misspelled nonce copy from v0.8.6's first window, and after a hot restore (71,791 of 71,839
tokens reused) the model returned that quoted copy. The seed now drops every line holding the
nonce's digits: the RTX 4090 recall returned the quoted copy in 4 of 30 trials with the old seed
and in none of 30 with the new one ([EXP-076](measurements/2026-09-29-restart-seed-decoy.json)). Candidate
`a1e51a70` passed the RTX 4090 route and a second RTX 5090 window.

[Release notes](../releases/v0.8.7/NINFER_RELEASE_NOTES.md) ·
[Manifest](../releases/v0.8.7/manifest.json) ·
[Qualification](../releases/v0.8.7/qualification.json).

**Upstream item: resumed sessions' first request.** OMP 18.4.0 replays native reasoning only once
a provider session is warmed (`nativeHistoryReplayWarmed` in
`packages/ai/src/providers/openai-responses.ts` starts false), so a new OMP process resuming a
session sends its first request without the reasoning of any earlier turn. The runtime preserves
thinking, so that request no longer matches the session it continues and prefills it from root:
56,174 tokens and 32.0 s to the first token in EXP-074, though the server had restored a current
checkpoint. The next request carries the reasoning again and caches. Treating a resumed session's
own reasoning as replayable on its first request would remove that prefill on either lane.

### Historical position — v0.8.6

Long sessions no longer fail a turn while OMP compacts them. The config every documented
route installs, [`examples/manual-tunnel/fail-closed.yml`](../examples/manual-tunnel/fail-closed.yml),
sets `compaction.asyncEnabled: false`, so unmodified upstream OMP 18.4.0 compacts before
the turn instead of in the background. Both lanes admit one request at a time. On the RTX 4090,
the background handoff took 56-61 s; the next turn's attempts expired at the 30 s admission
deadline, and the third of three compactions ended in `503 request_queue_timeout`.

[EXP-072](measurements/2026-09-28-omp-long-sessions.json), using the new
[`scripts/omp_long_session_proof.py`](../scripts/omp_long_session_proof.py), measured repeated
automatic compaction with stock OMP 18.4.0 on both lanes:

- RTX 4090: three inline handoffs took **77.0-83.7 s** each with **no expired admission**.
  The newest identifier survived every compaction and a graceful restart; all three older
  identifiers were also recalled. The turn carrying a compaction took **91-101 s**.
- RTX 5090: two snapcompact compactions took **0.07-0.08 s** on the client. Both identifiers
  held only inside frames were recalled; `detail: "auto"` reaches the model at native resolution.
  The bounded archive dropped **76,832 and 192,080 characters** of older middle history.
- A single-admission mock reproduced the failure behind a 45 s handoff after six expired
  attempts with the old config; inline compaction expired none. OMP recognizes the runtime's
  `context_length_exceeded` response on both fragments, compacts and retries.

These are one run per configuration on each lane, with synthetic build-log filler, one seed
and thinking `low`; the failure rate is not measured. Older-identifier recall is recorded,
not gated. The RTX 5090 was not restarted after compaction. RTX 4090 handoffs re-prefill the
whole session because `tool_choice: none` omits the usual tool block; a second full replay
just below the threshold also re-prefills about 102,600 tokens (68 s). After compaction, its
first turn after a graceful restart re-prefills about 32,000 tokens (17 s); without compaction
the restore is hot. On the RTX 5090, one chained turn per run re-prefilled 93,696-105,066 tokens
from root (40-46 s), with cause unidentified. These remain runtime work, not fixes in this release.

The client, provider fragments, both runtimes, model, memory floors, serving configurations and
lane receipts are unchanged from v0.8.5. RTX 5090 keeps `v0.6.12-qwen38-5090-beta.1`, image
`cd9e10b1`; RTX 4090 keeps `v0.6.9-qwen38-4090-beta.1`, package `6492588e`. Checkpoints carry
across. To upgrade from v0.8.5, merge this into `~/.omp/agent/config.yml`:

```yaml
compaction:
  asyncEnabled: false
```

The OMP binary, `models.yml` and `PI_OPENAI_STATEFUL=1` do not change.
Documented resume/restart checks now plant with an OK-only reply and recall verbatim.
RTX 3090 remains deferred.

All four documented routes passed **24 steps** on candidate `4f49fce7`
(`4f49fce7d52c62422e4f67cf15a3fa3a63dd72d9`) with unmodified OMP 18.4.0 and the published
components: RTX 5090 container host 2, macOS client 10, Windows client 5 and RTX 4090 native
Windows 7; both hosts were restored. The upstream macOS arm64 (preview), Windows x64 and
Linux x64 binaries each passed a typed tool turn, an exact continuation and a fail-closed
request against image `cd9e10b1`. Linux ran under **WSL2**, not a separately qualified Linux OS.
[Documented routes](../releases/v0.8.6/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.8.6/acceptance/composed-external-installation.json).

The RTX 5090 routes ran in **two production windows** from a separately hosted Apple silicon
Mac mini. Downtime was at most **186.9 s (3.1 min)** in the failed window and
**392.1 s (6.5 min)** in the accepted window;
total downtime was at most **579.0 s**
([restoration](measurements/2026-09-28-v086-acceptance-restoration.json)).

Candidate `be49962c` was refused by the RTX 4090 preflight before touching the lane: the lane
stage had left its manifest a draft; tooling was fixed. On `1fa202fd` the RTX 4090 route passed,
but the first RTX 5090 window failed at macOS resume: the acknowledgment wrote `COBOLT-493817`
and recall returned that copy. Production was restored after **186.9 s**; nonce checks were
hardened. On `60b5d82d` the documented RTX 4090 route passed, but its harness refused two
tool calls where it required exactly one. The harness now accounts each request to a documented
turn or tool call. Candidate `4f49fce7` passed the RTX 4090 route and a second RTX 5090 window.

[Release notes](../releases/v0.8.6/NINFER_RELEASE_NOTES.md) ·
[Manifest](../releases/v0.8.6/manifest.json) ·
[Qualification](../releases/v0.8.6/qualification.json).

### Historical position — v0.8.5

OMP compacts a 131,072-token session automatically at 111,412 tokens. For an image-capable
model, its first usable method, snapcompact, archives earlier turns as PNGs at
`detail: "original"`. NInfer refuses that with HTTP 400 `image_detail_not_supported`, so
long RTX 5090 sessions on stock OMP 18.3.0-18.4.0 (releases v0.8.0-v0.8.4) failed at their
first compaction. The RTX 5090 fragments now declare `compat.supportsImageDetailOriginal: false`,
so OMP sends `auto`. On the RTX 5090 runtime, one compacted continuation completed with
26,075 input tokens and the exact nonce; `original` was refused in 9 ms
([EXP-071](measurements/2026-09-28-omp-snapcompact-image-detail.json)). The text-only RTX 4090
model is never compacted into images. Readback beyond that nonce and repeated compactions
in one session were not measured in EXP-071; EXP-072 above adds those measurements.

The first v0.8.5 route candidate hit this at the macOS restart step when its seed, the
release's own documents, grew from 332,331 to 343,205 bytes. That step now seeds the first
200,000 ASCII bytes (about 64,000 tokens), keeping checkpoint restoration distinct from
compacted-prompt acceptance.

The v0.8.5 release also repins unmodified upstream OMP from 18.3.5 to
[18.4.0](https://github.com/can1357/oh-my-pi/releases/tag/v18.4.0). On Windows, 18.3.5
printed a false `ended before completing` line after finished `omp -p` turns and exited 1
after a complete `omp models` listing. Upstream fix `9d3e0d4975` resolves
[#13470](https://github.com/can1357/oh-my-pi/issues/13470).

[EXP-070](measurements/2026-09-28-omp-1840-windows-completion-status.json) compared the
Windows x64 binaries with the documented RTX 4090 provider fragment against a local mock
Responses endpoint: 18.3.5 exited 1 after 5/5 complete listings and printed the false line
after 5/5 completed turns that exited 0; 18.4.0 exited 0 without that line in all 10 runs.
Both versions retain the existing `Working...` stderr indicator. This is client-status
proof on Windows x64, not a GPU inference or performance measurement. The RTX 4090 route
harness again requires exit 0 plus exactly the documented selector; the 18.3.5-only
exit-status tolerance and false-line troubleshooting entry are removed.

Both lanes carry the exact v0.8.4 runtime bytes. RTX 5090 keeps
`v0.6.12-qwen38-5090-beta.1`, image `cd9e10b1`, server `3ab266e5`, source `9d1ef748`,
profile `qwen38-5090-v0.8.2`, configuration `56878aed` and its carried v0.8.3 lane receipt.
RTX 4090 keeps `v0.6.9-qwen38-4090-beta.1`, package `6492588e`, server `65364401`, source
`5ac17674`, configuration `ccecfbe3` and 60000 ms keep-warm with the sm_89 50 ms/100 ms spin.
Its carried v0.8.4 lane receipt records qualification with OMP 18.3.5, not a new 18.4.0
runtime qualification. Model and memory floors are unchanged; no performance gain is claimed.

To upgrade from v0.8.4, install the checksummed 18.4.0 client binary and add
`supportsImageDetailOriginal: false` under the RTX 5090 model's `compat` in
`~/.omp/agent/models.yml`, as the updated fragments do. Other fragment fields and
`PI_OPENAI_STATEFUL=1` are unchanged. Neither server build changes, so checkpoints on both
lanes carry across.

All four documented routes passed **24 steps** on candidate `943063e7` with unmodified
OMP 18.4.0 and the published components: RTX 5090 container host 2, macOS client 10, Windows
client 5 and RTX 4090 native Windows 7; both hosts were restored. The upstream macOS arm64
(preview), Windows x64 and Linux x64 binaries each passed a typed tool turn, an exact
continuation and a fail-closed request against RTX 5090 image `cd9e10b1`. Linux ran under
WSL2, not a separately qualified Linux OS.
[Documented routes](../releases/v0.8.5/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.8.5/acceptance/composed-external-installation.json).

The RTX 5090 routes ran in one production window, with downtime at most
**381.2 s (6.4 min)**, from a separately hosted Apple silicon Mac mini on
macOS 26.6.1 over the tailnet, not the maintainer's workstation
([restoration](measurements/2026-09-28-v085-acceptance-restoration.json)).

[EXP-067](measurements/2026-09-27-stock-omp-1835-durable-sessions.json) (durable sessions)
and [EXP-068](measurements/2026-09-28-omp-1835-live-steering.json) remain OMP 18.3.5
evidence. In 18.4.0, live steering remains Codex-WebSocket-only in
`openai-codex-responses.ts`, gated on `compat.supportsSteering`; these providers do not set it.
The upstream engine merge stays deferred
([EXP-065](measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json)); the
sm_89 Q5 tensor-core route stays rejected
([EXP-069](measurements/2026-09-28-rtx4090-q5-small-t-mma.json)). RTX 3090 remains deferred:
its `v0.6.2-beta.1` package is built and tested (99/105 tests) but unpublished; one
`qualify_native.py` window on its physical host remains
([preparedness](measurements/2026-09-28-rtx3090-v062-build-preparedness.json)).

[Release notes](../releases/v0.8.5/NINFER_RELEASE_NOTES.md) ·
[Qualification](../releases/v0.8.5/qualification.json).

### Historical position — v0.8.4

RTX 4090 ships `v0.6.9-qwen38-4090-beta.1` (package `6492588e`, server `65364401`,
source `5ac17674`, configuration `ccecfbe3`). Its `engine.gpu_keep_warm_ms = 60000` uses an
sm_89-specific 50 ms spin every 100 ms: the RTX 5090's 3.5 ms/10 ms pattern did not hold this
card in P2. New sessions after 12-58 s idle prefilled in **0.146-0.148 s**, with time to first
token **0.167-0.178 s**; all 31 outputs were byte-identical. The hold costs about **72 W**
above idle, and a request arriving mid-spin can overlap one warp for up to 50 ms.
[EXP-064](measurements/2026-09-27-rtx4090-engine-keep-warm.json) ·
[EXP-066](measurements/2026-09-27-rtx4090-keep-warm-long-spin.json).

The published package passed all **15 canonical qualification phases**
([lane receipt](../releases/v0.8.4/qualification/rtx4090.json)); this is not a decode-kernel speedup.
RTX 5090 keeps `v0.6.12-qwen38-5090-beta.1`, image `cd9e10b1`, profile `qwen38-5090-v0.8.2`,
configuration `56878aed` and its carried v0.8.3 lane receipt. The model and memory floors are
unchanged. RTX 4090 checkpoints from v0.6.8 re-prefill once on the changed server build;
RTX 5090 carries its v0.8.3 checkpoints.

The v0.8.4 client advanced to unmodified upstream **OMP 18.3.5**. Its macOS arm64 binary kept one
short session across graceful restarts on both lanes with the documented fragments unchanged
([EXP-067](measurements/2026-09-27-stock-omp-1835-durable-sessions.json)). A steer submitted
mid-stream did not abort: OMP sent it **27 ms** after `response.completed` as a new request
chained by `previous_response_id`
([EXP-068](measurements/2026-09-28-omp-1835-live-steering.json)).

All four documented routes passed **24 steps** on candidate `68302298` with unmodified OMP
18.3.5 and the published v0.8.4 components: RTX 5090 container host 2, macOS client 10, Windows
client 5 and RTX 4090 native Windows 7; both hosts were restored. The upstream macOS arm64
(preview), Windows x64 and Linux x64 binaries each passed a typed tool turn, an exact
continuation and a fail-closed request against RTX 5090 image `cd9e10b1`. Linux ran under WSL2,
not a separately qualified Linux OS.
[Documented routes](../releases/v0.8.4/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.8.4/acceptance/composed-external-installation.json).

OMP 18.3.5 on Windows exits 1 after a complete `omp models` listing. That stopped the RTX 4090
route's first candidate, `0315c5d4`, at its no-effect preflight; that release's corrected check judged the
listing and candidate `68302298` passed. Upstream 18.4.0, released 2026-09-28, fixes
[can1357/oh-my-pi#13470](https://github.com/can1357/oh-my-pi/issues/13470). v0.8.4 pinned 18.3.5;
v0.8.5 repins to 18.4.0.

The upstream engine merge stays deferred: `e31bc99b` has about **18% slower decode** and
fanout **0/4 versus 4/4**
([EXP-065](measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json)). The
RTX 4090 Q5 tensor-core route was rejected by its pre-registered rule: **+0.38% at 26K** and
**+0.40% at 60K**, below required **2.0%/1.0%** gains
([EXP-069](measurements/2026-09-28-rtx4090-q5-small-t-mma.json)). RTX 3090's v0.6.2-beta.1
package built and tested at `5ac17674` remains unpublished, with hardware qualification pending
([preparedness](measurements/2026-09-28-rtx3090-v062-build-preparedness.json)).

[Release notes](../releases/v0.8.4/NINFER_RELEASE_NOTES.md) ·
[Qualification](../releases/v0.8.4/qualification.json).

### Historical position — v0.8.3

The unmodified upstream OMP 18.3.0 client and model artifact are unchanged from v0.8.2.
RTX 5090 advances to `v0.6.12-qwen38-5090-beta.1` (image `cd9e10b1`, server `3ab266e5`,
source `9d1ef748`). RTX 4090 remains `v0.6.8-qwen38-4090-beta.1` (package `46aa4110`,
server `32905865`, source `5a774841`), carrying its v0.8.1 lane receipt. RTX 3090 remains
deferred. Serving arguments, profile `qwen38-5090-v0.8.2`, configuration `56878aed`,
`--gpu-keep-warm-ms 60000`, 16384 MiB host KV and the 28672 MiB host floor are unchanged.

The runtime source is v0.8.2's `32c21f73` plus the EXP-057 route: the MTP3 verify pass's
four Q5 projections (GDN value/z, attention gate/value, mixer/attention output and MLP down)
use small-T tensor-core MMA at the four-token extent on `sm_120` instead of SIMT row kernels.
The route is compiled out for `sm_86` and `sm_89`. Release-build A/B/B/A measurements show
decode **+4.4% at 26K**, **+3.6% at 60K** and **+6.3% at 1,024 tokens**, with MTP3 rounds
**3.5-4.9% shorter**. With no prompt, decode was **0.5% slower**: the new build accepted
0.423 of drafts on its own text versus 0.461.
Route: [EXP-057](measurements/2026-09-26-q5-small-t-tensor-core.json); measurements:
[EXP-063](measurements/2026-09-27-powered-redaction-screen.json).

Accumulation order changes; **58 of 89** role-corpus cases answer differently from v0.8.2.
The pre-registered [EXP-063](measurements/2026-09-27-powered-redaction-screen.json)
redaction screen passed on **504 pairs** (7 controls with 72 whitespace variants).
Candidate leaks were **561 vs 582** for v0.8.2: ratio **0.964**, one-sided 95% upper bound
**1.012**, margin **1.10**. Pass rates were **53.2% vs 52.6%**: **+0.6 percentage points**,
lower bound **-1.2 points**, margin **-5 points**. All validity checks held. The earlier
EXP-057 56-sample point-estimate screen had rejected the route (**69 vs 61 leaks**);
EXP-063 re-tested the redaction regression with power. Other primary role-corpus measures
were within 2.0 points of v0.8.2 in one run per build. The published image matched the
screened candidate byte-for-byte on **89/89** cases.

Gates were re-measured on the published RTX 5090 image: 130,048-token exact retrieval in
**58.7 s**, decode at **168.07 tok/s**, and the agent protocol across a restart. Four sessions
restored after restart; publication-barrier, fanout, warm-arrival, restore and multisession
probes passed. Root fallback remained 2 of 8 continuations/forks. None of 24 fresh sessions
fell back to a full prefill; median TTFT was **0.093-0.100 s**. Stock OMP 18.3.0 kept one
session across graceful restarts; the first request restored from checkpoint.
[Lane receipt](../releases/v0.8.3/qualification/rtx5090.json) ·
[Qualification](../releases/v0.8.3/qualification.json).

All four documented routes passed **24 steps** with unmodified OMP 18.3.0 on the published
v0.8.3 components: RTX 5090 container host 2, macOS client 10, Windows client 5 and RTX 4090
native Windows 7; both hosts were restored.
The upstream macOS arm64, Windows x64 and Linux x64 binaries each passed a typed tool turn,
an exact continuation and a fail-closed request against the published RTX 5090 image.
[Documented routes](../releases/v0.8.3/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.8.3/acceptance/composed-external-installation.json).

Checkpoints bind the exact server build: sessions saved by v0.8.2 do not restore on the new
RTX 5090 build in v0.8.3. Each session re-prefills once.
[Release notes](../releases/v0.8.3/NINFER_RELEASE_NOTES.md).

The preceding v0.8.3 measurements are historical; the tracked-upstream table below records the
current EXP-065 engine decision and the v0.8.6 client pin.

### Historical position — v0.8.2

The unmodified upstream OMP 18.3.0 client and model artifact are unchanged from v0.8.1.
RTX 5090 advances to `v0.6.11-qwen38-5090-beta.1` (image `26813f56`, server `0d7e042b`,
source `32c21f73`). RTX 4090 remains `v0.6.8-qwen38-4090-beta.1` (package `46aa4110`,
server `32905865`, source `5a774841`), carrying its v0.8.1 lane receipt: 15 canonical
native phases and 130,048-token retrieval in **91.0 s**. RTX 3090 remains deferred.

The runtime adds `ninfer-serve --gpu-keep-warm-ms N`, off by default. After work and while
idle, a single-warp kernel touches no memory and spins 3.5 ms of every 10 ms on its own stream
for N ms, skips a launch while the previous spin runs, and stops when a request is pending.
RTX 5090 profile `qwen38-5090-v0.8.2` adds `--gpu-keep-warm-ms 60000`; host KV stays
16384 MiB and the host floor stays 28672 MiB. After 12-58 s idle, new sessions prefilled in
**0.155-0.157 s** (TTFT **0.173-0.181 s**), versus **0.253-0.304 s** (TTFT **0.316-0.366 s**)
without keep-warm. The 89-case role corpus was byte-identical to v0.8.1 on and off. Holding
clocks costs about **71 W**; a 60 s grace replayed over 62 h of logged v0.7.0 traffic would
cost about **2.3 W average**. [EXP-062](measurements/2026-09-26-engine-keep-warm.json).

The published RTX 5090 image recorded 130,048-token exact retrieval in **56.4 s**, decode at
**160.07 tok/s**, four sessions restored after restart, and passed publication-barrier,
fanout, warm-arrival, restore and multisession probes. None of 24 fresh sessions fell back to
a full prefill; median TTFT was **0.090-0.098 s**. Stock OMP 18.3.0 kept one session across
restarts on the RTX 5090. [Lane receipt](../releases/v0.8.2/qualification/rtx5090.json).

All four documented routes passed **24 steps** with unmodified OMP 18.3.0 on the published
v0.8.2 components: RTX 5090 container host 2, macOS client 10, Windows client 5 and RTX 4090
native Windows 7; both hosts were restored.
The upstream macOS arm64, Windows x64 and Linux x64 binaries each passed a typed tool turn,
an exact continuation and a fail-closed request against the published RTX 5090 image.
[Documented routes](../releases/v0.8.2/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.8.2/acceptance/composed-external-installation.json).

Checkpoints bind the exact server build: sessions saved by v0.8.1 do not restore on the new
RTX 5090 build in v0.8.2. OMP resends the full conversation and each session re-prefills once.
[Release notes](../releases/v0.8.2/NINFER_RELEASE_NOTES.md).

The upstream delta measurements below remain historical; keep-warm is not an upstream rebase.

### Historical position — v0.8.1

Runtime positions below retain the [2026-09-24 report](measurements/2026-09-24-upstream-watch.json);
they are not new upstream delta measurements. The upstream NInfer rebase remains future work.
The client remains the unmodified upstream OMP 18.3.0 release binary with the same SHA-256
pins as v0.8.0. All three client binaries passed live inference on the published RTX 5090
image (Linux under Ubuntu/WSL2), and the four documented routes passed all 24 steps on the
published v0.8.1 components, with both hosts restored.

The runtime change is decode kernels, not the upstream rebase: small-extent Q4/Q5 projections
share activation loads across weight rows, and Q4 gate/up staging avoids shared-memory bank
conflicts. RTX 5090 `v0.6.10-qwen38-5090-beta.1` (image `5ca6e416`, server `5b2f2471`,
source `8cc0810a`) decodes 10.3-11.0% faster with identical outputs. RTX 4090
`v0.6.8-qwen38-4090-beta.1` (package `46aa4110`, server `32905865`, source `5a774841`)
keeps one-row split2 kernels on native lanes; C1 decode is 157.89 vs 153.54 tok/s. Every
runtime gate was re-measured on published bytes, matching v0.8.0's behavior; client, model,
serving settings and floors are unchanged.
[EXP-055](measurements/2026-09-25-decode-kernel-schedules.json) ·
[EXP-054](measurements/2026-09-25-decode-roofline-attribution.json) ·
[Release notes](../releases/v0.8.1/NINFER_RELEASE_NOTES.md) ·
[Documented routes](../releases/v0.8.1/acceptance/documented-routes.json).

