# Roadmap

This roadmap is a scope boundary, not a promise of dates. Oh My Pi (coding-agent client) connects
through OMP NInfer (qualified appliance and release layer) to NInfer (inference engine) serving
Qwen3.8 27B (served model) on user-owned NVIDIA GPUs. Qualified on RTX 5090 · 4090 · 3090, each
release lane is bound to exact bytes and a qualification receipt. Work outside that wedge requires a
new product decision rather than placeholder abstractions, and no kernel, model, or configuration
change becomes part of a release until its exact binary and profile are rebound through a new
qualification receipt.

Standing support boundaries for the 0.x series: owner-operated exact profiles with no SLA or upgrade
commitment; two requests in flight on the RTX 5090 container lane and on the native Windows RTX
3090 lane (sharing one 131,072-token INT8 pool) and one active request on the native Windows RTX
4090 lane (with native lanes running one lane at a time on port 18082); enforced JSON-schema
structured output, 128-character tool names, and DFlash2 draft window 7 (`K=7`) qualified across all
three lanes while vision remains RTX 5090 container-only; the unattended RTX 3090 fleet scout role
disabled; no cloud hosting, multi-GPU inference, multi-tenant serving, priority or preemptive
scheduling, automatic container restart, or silent cloud fallback; and no support or performance
claim outside the exact recorded package, machine, and profile. Community project; not affiliated
with or endorsed by Oh My Pi, Qwen, or NVIDIA.

## Current release

**v0.17.0** (published 2026-11-10, GitHub `Latest`; superseding `v0.16.2`, 2026-11-04) pins
unmodified upstream Oh My Pi **18.18.6** (`9058ab9d229663e229e2867824ba6df6f21e9e59`, tree
`fd379b65368a20c7648d97f2c2b99cc03e019254`, release `439766193`; `qwen3.8-27b` on native RTX 4090
defaults to stock `replace` edit-tool mode while `q38-ninfer` on RTX 5090 and native RTX 3090 keeps
`hashline` and pins explicit `tokenizer: qwen3`, explicit `[low, medium, xhigh]` effort lists keep
`high`→`medium` and `off`→`low` clamps, `examples/manual-tunnel/fail-closed.yml` explicitly disables
automatic updates and the setup wizard alongside retries and model fallback, Qwen's exact-loop guard
retains the 1,024-character floor on short newline-spanning cycles, and default async compaction
uses a `19,660`-token reserve, strict `>111,412` trigger, and `13,107`-token unset-reserve summary
cap) and shared published model container version 3 `81f924d4` (`qwen3_8_27b-v3.ninfer`,
20,437,521,664 bytes), rebuilds the RTX 5090 container runtime to `v0.7.0-qwen38-5090-beta.6` from
release source F3 `e0971faf` (`e0971faf221204047d5a4ed834e4e298740cee17`) on upstream
`Neroued/ninfer` master `64d10fbf` ([fork PR #101](https://github.com/alphastorm/ninfer/pull/101)),
and carries the published native Windows RTX 4090 and RTX 3090 `v0.8.0-qwen38-{4090,3090}-beta.2`
packages unchanged at source `a87de361` (`a87de3613c17bced777b446fb545f872d8395ec1` on
`64d10fbf`):

- **RTX 5090 container (`v0.7.0-qwen38-5090-beta.6`, source `e0971faf` on `64d10fbf`, image
  `7a19576b` on reused base `28857182`, server `dc86e101`, model `81f924d4`):** Windows 11 + Docker
  Desktop/WSL2 on loopback `127.0.0.1:18089`, kept profile `qwen38-5090-v0.13.0` (`751d22dc`), BF16
  KV (146,368 automatic tokens), 131,072-token context, two requests in flight plus two extra
  device-state slots, DFlash2 draft window 7 (`--lm-head-draft`), isolated host schema 3 checkpoint
  directory `checkpoints-v017` mounted at container path `/checkpoints-v013` (preserving predecessor
  host directory `checkpoints-v013` for rollback, with mandatory `--session-checkpoint-require-origin-auth`,
  bounded resume/fresh admission with per-rotation fresh-window accounting for upstream
  [#434](https://github.com/Neroued/ninfer/issues/434), durable pressure-work waits, byte-proven
  durable-generation Host reclaim [#78](https://github.com/alphastorm/ninfer/issues/78),
  export-retirement reservation [#68](https://github.com/alphastorm/ninfer/pull/68), and non-blocking
  export with Host `StateImage` materialization, `EXP-105`), serving robustness for malformed tool
  arguments, template-aware effort normalization, request-local numerical failures, and stop/drain
  final-save ordering (upstream
  [#440](https://github.com/Neroued/ninfer/issues/440)/[#441](https://github.com/Neroued/ninfer/issues/441)/[#446](https://github.com/Neroued/ninfer/issues/446)),
  host-side NFC/frontend rendering, deterministic bounded RDC builds (`664` build artifacts and all
  `3` package outputs matched bit for bit across a same-path double build; `12/12` exact-source RC
  phases passed in [`runtime-rc.json`](releases/v0.17.0/qualification/runtime-rc.json) `bed3a245`),
  `io_uring` owned completion buffers and CQE cancellation/drain barrier
  ([#116](https://github.com/alphastorm/omp-ninfer/issues/116)), per-position speculative metrics
  (schema `30`), JSON-schema structured output, 128-character tool names, vision + tools + preserved
  thinking (`181.92 tok/s` server / `180.40 tok/s` wall decode, `56.63 s` cold exact 130,048-token
  retrieval at `2,296.5 tok/s` wall / `56.53 s` server prefill in
  [`rtx5090.json`](releases/v0.17.0/qualification/rtx5090.json) `11fde294`).
- **RTX 4090 (`v0.8.0-qwen38-4090-beta.2`, package `d9b10b47`, server `ffee91bf`, config `ae27dc44`)
  and RTX 3090 (`v0.8.0-qwen38-3090-beta.2`, package `97a8e634`, server `15a4db46`, config
  `238ccad7`) native Windows (carried unchanged at source `a87de361` on `64d10fbf`, model
  `81f924d4`):** loopback `127.0.0.1:18082`, **DFlash2 draft window 7** (`Q4_G64_FP16` draft MLP,
  host-mapped `token_embedding`, `proposal: "artifact-default"`), INT8 KV, `Group64` A8 and FP32
  head logits off, 131,072-token context, 1,024-token prefill chunk, two extra device-state slots,
  JSON-schema structured output, 128-character tool names, text + tools (no vision), mandatory
  `--session-checkpoint-require-origin-auth`, release-isolated schema 3 checkpoint stores
  (`cache/<release-instance-id>/session-checkpoints-v3`, where `<release-instance-id>` is the
  installed release ID such as `qwen38-4090-native-v0.8.0-beta.2-a87de3613c17`), and dual SPDX 2.3 +
  CycloneDX 1.5 dependency SBOMs (`C1`, 30 s pending timeout, 15,747.734375 MiB /
  16,512,696,320-byte shared Host budget, 640 MiB admission headroom, and 450 W owner baseline on
  RTX 4090, `254.59 tok/s` C1 decode and `83.54 s` exact retrieval in
  [`rtx4090.json`](releases/v0.17.0/qualification/rtx4090.json) `254167f2`; **`C2` over one shared
  131,072-token pool**, 180 s pending timeout, `ninfer-native-3090: 2` in `fail-closed.yml`,
  20,867.734375 MiB / 21,881,405,440-byte shared Host budget, 768 MiB admission headroom, and 350 W
  serving cap / 370 W restored on RTX 3090, `148.70 tok/s` C1 decode and `188.94 s` exact retrieval
  in [`rtx3090.json`](releases/v0.17.0/qualification/rtx3090.json) `b742870e`). Both install on one
  two-GPU host bound by GPU UUID and run one lane at a time; their `a87de361` 15-phase
  qualification receipts, zero-difference 1,120-prompt quality screens (`80/80` determinism per arm),
  fit proofs, no-regression speed gates against published `beta.1`
  ([`native-speed-decision.json`](releases/v0.17.0/qualification/native-speed-decision.json)
  `5c09de6a`: RTX 3090 weighted **1.0003** / min **0.9988**, **84/84** identical; RTX 4090 weighted
  **0.9996** / min **0.9989**, **115/115** identical), and `3/3` `v0.8.0-beta.1`
  upgrade/rollback/repair rehearsals
  ([`rtx4090-rehearsal-harness-decision.json`](releases/v0.17.0/qualification/rtx4090-rehearsal-harness-decision.json)
  `f1fcd1bb`) are carried byte-for-byte in
  [`receipt-audit.json`](releases/v0.17.0/qualification/receipt-audit.json) (`c137388a`). On
  2026-11-10, candidate `076bbe4f` passed all five documented routes (`31/31` blocks across all three
  stock 18.18.6 clients; `408.213 s` RTX 5090 hold) and RTX 4090 native
  public-install/probe/restoration (`508.420 s` RTX 4090 campaign), while RTX 3090's post-route
  `native-probes` automatic-compaction campaign failed (`1,727.696 s` elapsed; `900 s` compaction
  timeout, `8` HTTP `503` queue timeouts, `2` HTTP `499` cancellations, `0` resident work; subsequent
  managed Stop `graceful_incomplete_shutdown` saved `2` / skipped `5` / refused `3`, reason
  `capacity`) under its
  [founder waiver](releases/v0.17.0/qualification/rtx3090-route-waiver.json) (`19f2c0ef`, with
  empty-session `Start`/`Stop` lead recovery `fabb50de` bound separately; no RTX 3090 behavior
  completion, structured outage, wrapper restoration audit pass, or anonymous public-install claim;
  RTX 3090 users should keep `v0.16.2` or restart the lane after long sessions until a native re-cut
  is qualified).

Stock OMP has no `omp appliance` lifecycle commands; container and native host scripts own runtime
lifecycle, and source-first native qualification is an established release procedure
([`docs/RELEASES.md#next-native-release-sequencing`](docs/RELEASES.md#next-native-release-sequencing)).
Full release authority: [`releases/v0.17.0/NINFER_RELEASE_NOTES.md`](releases/v0.17.0/NINFER_RELEASE_NOTES.md) ·
[`releases/v0.17.0/manifest.json`](releases/v0.17.0/manifest.json) ·
[`releases/v0.17.0/qualification.json`](releases/v0.17.0/qualification.json) ·
[`docs/RELEASES.md`](docs/RELEASES.md) · [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md).

## Remaining work

Items below remain open after `v0.17.0`; each names the current evidence showing the gap is still
unmet:

1. **Independent multi-owner clean-install, recovery, and rollback evidence.** All qualifications,
   native `v0.8.0-beta.1` → `v0.8.0-beta.2` upgrade/rollback rehearsals, and 31-block
   documented-route acceptances through `v0.17.0` are maintainer-operated on owner hardware rather
   than gathered across multiple independent owners
   ([`releases/v0.17.0/qualification.json`](releases/v0.17.0/qualification.json),
   [`releases/v0.17.0/qualification/rtx4090.json`](releases/v0.17.0/qualification/rtx4090.json),
   [`releases/v0.17.0/qualification/rtx3090.json`](releases/v0.17.0/qualification/rtx3090.json),
   [`releases/v0.17.0/NINFER_RELEASE_NOTES.md`](releases/v0.17.0/NINFER_RELEASE_NOTES.md)).
2. **macOS managed lifecycle and native Linux OS qualification.** The macOS arm64 route remains a
   manual SSH tunnel preview without managed client installation or appliance lifecycle (`scripts/mac_tunnel.py`
   supervises only the local SSH forward), and the Linux x64 client is evidenced only under WSL2 on
   the Windows 11 container host rather than a native Linux OS
   ([`releases/v0.17.0/qualification.json`](releases/v0.17.0/qualification.json),
   [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md)).
3. **Hardware-independent public route qualification.** [`scripts/client_acceptance.py`](scripts/client_acceptance.py)
   and [`scripts/doctor.py`](scripts/doctor.py) provide host-free client rehearsals, live owner-lane
   checks, and named-cause WSL/Docker/loopback preflight, while full 31-block documented-route
   release qualification still requires live maintainer GPU-host windows
   ([v0.17.0 documented-route acceptance](releases/v0.17.0/acceptance/documented-routes.json)).
   The earlier route-lifecycle tracker [#15](https://github.com/alphastorm/omp-ninfer/issues/15) is
   closed; it is historical context, not an open tracker for these additions.
4. **Distribution signing and notarization.**
   [`scripts/generate_native_sbom.py`](scripts/generate_native_sbom.py) generates CycloneDX 1.5
   dependency SBOMs and the verifier supports `sbom_dependency_url` / `sbom_dependency_sha256`,
   and both published `v0.8.0-beta.2` native components in
   [`releases/v0.17.0/manifest.json`](releases/v0.17.0/manifest.json) bind separate dependency
   inventories, including MSVC CRT and DirectStorage redistributables, beside their SPDX file
   inventories. Package signing and notarization remain unclaimed ([`docs/SECURITY.md`](docs/SECURITY.md)).
   OMP NInfer consumes unmodified upstream OMP binaries by
   SHA-256 without rebuilding or re-signing the client; only first-party Windows runtime package
   signing is in scope here.
5. **Same-profile second-machine recovery and fixed fleet workload gates.** Off-machine replication
   via [`scripts/checkpoint_sync.py`](scripts/checkpoint_sync.py) is proven for local-loss recovery
   on the originating host ([`docs/measurements/2026-09-05-sync-probe-rtx5090.json`](docs/measurements/2026-09-05-sync-probe-rtx5090.json),
   [`docs/FACTS.md#checkpoint-transport-and-nas-replication`](docs/FACTS.md#checkpoint-transport-and-nas-replication)),
   not restoration onto a second physical inference host. The RTX 3090 fleet scout role remains
   disabled ([`releases/v0.17.0/NINFER_RELEASE_NOTES.md`](releases/v0.17.0/NINFER_RELEASE_NOTES.md)),
   and any fleet completed-work claim requires re-running the fixed multi-machine workload
   ([`scripts/fleet_dispatch.py`](scripts/fleet_dispatch.py), EXP-016 in
   [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md#experiment-ledger)).
6. **Deferred runtime, installer, and release-tooling residuals ([#149](https://github.com/alphastorm/omp-ninfer/issues/149), [#138](https://github.com/alphastorm/omp-ninfer/issues/138), [#88](https://github.com/alphastorm/omp-ninfer/issues/88)–[#90](https://github.com/alphastorm/omp-ninfer/issues/90), `alphastorm/ninfer` [#87](https://github.com/alphastorm/ninfer/issues/87)–[#90](https://github.com/alphastorm/ninfer/issues/90)).**
   In `v0.16.2`, `alphastorm/ninfer` `#51`–`#55`, `#62`, `#63`, `#65`, `#67`–`#70`, `#73`, `#78`–`#80`,
   and `#82` were resolved across the `a87de361` runtime components, and subsequent tooling and CI
   merges closed [#138](https://github.com/alphastorm/omp-ninfer/issues/138) items 1–8
   ([#143](https://github.com/alphastorm/omp-ninfer/pull/143) `71b9b84f`, plus `checkpoints-v017`
   isolation and atomic macOS bearer-key transfer in `v0.17.0`),
   [#128](https://github.com/alphastorm/omp-ninfer/issues/128) rows `P5`, `P6`, `P8`–`P12`, `P14`,
   and Python `P7` ([#141](https://github.com/alphastorm/omp-ninfer/pull/141) `59452c73`), and
   [#109](https://github.com/alphastorm/omp-ninfer/issues/109)'s CI rows
   ([`alphastorm/ninfer#92`](https://github.com/alphastorm/ninfer/pull/92) `020655f1`). On the
   `a87de361` engine, EXP-109
   ([`docs/measurements/2026-11-05-p19-flash-next-and-starvation.json`](docs/measurements/2026-11-05-p19-flash-next-and-starvation.json),
   [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md#experiment-ledger)) reproduced upstream
   [`Neroued/ninfer#434`](https://github.com/Neroued/ninfer/issues/434) request starvation under
   context pressure (preregistered red: an admitted request with no token progress `>= 120 s` while
   others progress) on both `C2` lanes — on the native RTX 3090 `C2` lane (`rtx3090-win-a`,
   `v0.8.0-qwen38-3090-beta.2`), a `79,989`-token request paused `440.94 s` after `62,464` input
   tokens with zero output/restores while the prime request generated `16,150` tokens and `45` fresh
   requests completed, and on the RTX 5090 production image (`rtx5090-win-a`, image `a0cbb8a5`,
   production serving arguments except a `2 GiB` scratch checkpoint store), an admitted
   `79,989`-token request produced its first token `~398.8 s` after admission while the other long
   request streamed and `48` fresh `247`-token requests completed every `~10 s`, running only after
   the other request finished — while upstream
   [`Neroued/ninfer#378`](https://github.com/Neroued/ninfer/issues/378) Host placement was not
   reproduced on the native RTX 3090 lane (both Host-fill arms, fill `4` and fill `5`, preserved the
   conversation, at up to `99.995%` peak Host occupancy; the oldest conversation was evicted
   instead), was **inconclusive** on the RTX 5090 (`rtx5090-win-a`, production image `a0cbb8a5`: the
   client's adaptive fill did not converge within its `3,600 s` budget across `12` conversations of
   `~120K` tokens with fill steps lengthening to `~10 min`, so no preservation probe ran), and did
   **not** reproduce on either build on the RTX PRO 6000 proxy (`rtxpro6000-win-a`, `sm_120`,
   `NINFER_VRAM_BUDGET_MIB=31000`, `C2` / `BF16` / `131,072`-token KV, `20.4 GiB` Host, preregistered
   fixed fill `5`: peak Host occupancy `99.842%` baseline / `99.861%` candidate, with the preserved
   conversation keeping `119,985` of `119,992` / `119,981` of `119,988` cached tokens).
   [`alphastorm/ninfer#93`](https://github.com/alphastorm/ninfer/pull/93) (head `e6ac7b70`, CI green
   on all `8/8` jobs) ported the initial fix candidate (the `a754fcf3` failure-diagnostics subset,
   the `452c3f5f` recovery-loss formula, `#378` Host placement re-expressed from Saylek-ai
   `fix/378-host-placement`, and the `#434` scheduler pressure owner + bounded service rotation +
   deferred fresh admission, including a fix and regression test for a refusal-retry liveness defect
   on a queued fresh-admission notification found in the first scheduler port): on the
   `rtxpro6000-win-a` RTX PRO 6000 proxy (`a87de361` vs `e6ac7b70`), baseline `a87de361` was **RED**
   (an admitted request paused `362.3 s` without progress while `38` fresh requests completed),
   whereas `e6ac7b70` eliminated admitted-request starvation (maximum pause `1.28 s`, both long
   requests completed) and passed no-pressure parity (`3/3` greedy prompts byte-identical), **but**
   two fresh requests were refused with HTTP `503` queue timeouts (`180 s` pending timeout) while
   admission was deferred under sustained pressure. In `P20` (`EXP-112`, `EXP-121`), `E1`'s bounded
   fresh-admission rotation window
   ([`alphastorm/ninfer#97`](https://github.com/alphastorm/ninfer/pull/97)) removed those `503`s
   under pressure (RTX 5090: `0/51` fresh HTTP `503` at `E1` `375bb848` and `0/54` at `F2`
   `bdc665a3`, with max fully-paused intervals `3.0 s` and `2.59 s`), and `#93` (`e6ac7b70`) was
   marked merged on 2026-11-10 when fork `main` gained the `F3` merge `b871996a`. In `v0.17.0`, the
   RTX 5090 `v0.7.0-qwen38-5090-beta.6` component (`e0971faf`,
   [fork PR #101](https://github.com/alphastorm/ninfer/pull/101)) ships those bounded resume/fresh
   admission fixes with per-rotation fresh-window accounting for upstream
   [`Neroued/ninfer#434`](https://github.com/Neroued/ninfer/issues/434), durable
   pressure-work waits (`pause_reclaim_victim`, `reserve_resident_units`, pending save/export,
   guarded capture/source, and reclaim boundaries), serving robustness for malformed tool arguments,
   template-aware effort normalization, request-local numerical failures, and stop/drain final-save
   ordering (upstream
   [#440](https://github.com/Neroued/ninfer/issues/440)/[#441](https://github.com/Neroued/ninfer/issues/441)/[#446](https://github.com/Neroued/ninfer/issues/446)),
   and host-side NFC/frontend rendering, while the native Windows RTX 4090 and RTX 3090 packages stay
   carried at `v0.8.0-qwen38-{4090,3090}-beta.2` (`a87de361`) and do not yet receive the F3 runtime
   fixes. The `v0.17.0` runtime full council (`CR-20261110T083627Z-a3fa0550` remediated at F3
   `e0971faf`), product full council (`CR-20261110T121737Z-c4afc44f-product` on `c4afc44f` with route
   stage `076bbe4f`), and focused waiver-support review (`CR-20261110T144437Z-f85af622-waiver`
   remediated at `bf2a63a0`, [#150](https://github.com/alphastorm/omp-ninfer/pull/150)) closed by
   disposition in [`releases/v0.17.0/review/runtime-ledger.json`](releases/v0.17.0/review/runtime-ledger.json)
   (`5f8d6e4a0d698f227237b1cf420a8da87182a7c0197ce05e3744fc2f485bce5f`). Remaining open items are
   qualifying a native Windows re-cut with the F3 admission/Stop fixes (addressing RTX 3090's waived
   post-route `native-probes` compaction campaign timeout and subsequent `3`-session Stop refusal in
   [`rtx3090-route-waiver.json`](releases/v0.17.0/qualification/rtx3090-route-waiver.json)
   `19f2c0ef`), the excluded bounded prefix-source-wait follow-up on cold prefill/decode overlap
   ([`alphastorm/ninfer#102`](https://github.com/alphastorm/ninfer/issues/102), `EXP-118`),
   product tooling residuals in [#149](https://github.com/alphastorm/omp-ninfer/issues/149)
   (retaining `omp-ninfer` [#88](https://github.com/alphastorm/omp-ninfer/issues/88)–[#90](https://github.com/alphastorm/omp-ninfer/issues/90),
   [#109](https://github.com/alphastorm/omp-ninfer/issues/109), and
   [#128](https://github.com/alphastorm/omp-ninfer/issues/128)), `alphastorm/ninfer`
   [#87](https://github.com/alphastorm/ninfer/issues/87)–[#90](https://github.com/alphastorm/ninfer/issues/90),
   and a corrected repeated native `Group64` A8 screen.
7. **Concurrency 2 on the native RTX 4090 lane (shipped on RTX 3090 in `v0.16.0`; RTX 4090 requires
   a smaller KV format).** In `v0.16.0`–`v0.17.0`, the native RTX 3090 lane ships `C2`
   (`v0.8.0-qwen38-3090-beta.2`: `--max-concurrency 2`, `2` extra / `4` total device-state
   slots, `180,000 ms` pending timeout, `21,881,405,440` B Host budget, `768 MiB` headroom,
   `ninfer-native-3090: 2` in [`examples/manual-tunnel/fail-closed.yml`](examples/manual-tunnel/fail-closed.yml))
   sharing one `131,072`-token `INT8` KV pool (**1.385×** median aggregate decode `57.68 → 79.90
   tok/s`, **0.722×** pair completion wall `71.01 → 51.26 s`, `0.70–0.73×` concurrent per-request
   decode; EXP-105, EXP-106 in [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md#experiment-ledger)). On
   the RTX 4090 (`v0.8.0-qwen38-4090-beta.2`), `INT8` `C2` at `131,072` tokens (`chunk 2,048`,
   `640 MiB` headroom) does not fit 24 GB (`Device budget cannot hold the calibrated runtime and
   requested KV capacity` startup refusal; EXP-106), so RTX 4090 stays at `C1` until a smaller KV
   format such as `rk4v4` resolves its true-cold restore divergence (item 8).
8. **Open kernel and schedule backlog (`rk4v4` / `262K` native context follow-up gated on the
   true-cold restore blocker).** Native `DFlash2 K=7` shipped on both the RTX 3090 (`EXP-101`) and
   RTX 4090 (`EXP-102`, `EXP-104`, `EXP-105`) in `v0.16.0`. As a **post-`v0.16.0` follow-up release
   item**, native **`rk4v4` 4-bit KV and `262,144`-token native context** (`17,920` B/token vs `INT8`
   `33,792` B/token, EXP-107) passed `FP64` op/graph/store controls (`7/7`) and held-out perplexity
   on both cards ($\Delta\text{NLL} = 0.00345 \le 0.02$) and fit `262,144`-token `C1` on the RTX 3090
   (`1,097,859,072` B available after startup above the `805,306,368` B / `768 MiB` floor; exact
   `130,048`- and `250,062`-token diagnostic retrieval), but is blocked on the **exact true-cold
   restore oracle**, where restored continuation diverges from the zero-reuse cold reference at
   token `32` (`262,144`-token `C1`) and tokens `16–32` on the first of two concurrent sessions
   (`245,760`-token `C2` and `229,376`-token `C2`, cause unproven) and RTX 4090 `chunk 2,048` startup
   capacity at `262,144`-token `C1` / `245,760`-token `C2`. Root-cause numerics localization for the
   rejected native `sm_86`/`sm_89` small-T tensor-core decode candidate (EXP-099,
   [`docs/measurements/2026-10-27-native-small-t-tensor-core-decode.json`](docs/measurements/2026-10-27-native-small-t-tensor-core-decode.json))
   and `Group64` A8 prefill leak flips (EXP-100,
   [`docs/measurements/2026-10-27-native-group64-a8-prefill.json`](docs/measurements/2026-10-27-native-group64-a8-prefill.json)),
   verify-round host-commit idle time (EXP-058,
   [`docs/measurements/2026-09-26-decode-draft-source-and-launch-chain.json`](docs/measurements/2026-09-26-decode-draft-source-and-launch-chain.json);
   EXP-092,
   [`docs/measurements/2026-10-03-dflash2-round-costs-rtx5090.json`](docs/measurements/2026-10-03-dflash2-round-costs-rtx5090.json)),
   Q4/Q5 GEMV/MMA epilogue fusion (EXP-056), and warm-turn template fragment consolidation
   (EXP-059) remain open in [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md#ideas-backlog).

## Deferred and rejected decisions

Negative and deferred results stay visible in [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md#experiment-ledger)
so future work does not repeat closed experiments:

- **Wholesale upstream engine merge — prior deferral superseded by v0.13.0–v0.17.0 (EXP-097).** Earlier upstream
  NInfer (`594930e7`, `e31bc99b`, `81c8ce09`) trailed the fork by 18–19% on matched decode, lost
  sibling fanout reuse, overran the 32 GB automatic C2 BF16 budget by 561 MiB, and lacked the
  durable disk session store. `v0.13.0` re-ported the RTX 5090 durable/runtime families onto master
  `64d10fbf` (`6d4d0a05`), and `v0.13.1` re-ported both native Windows lanes (`7a25cd72`) onto
  `64d10fbf` with 640 / 768 MiB admission headroom. EXP-097 clears the founder-amended 96% median
  decode floor at 101.09% on RTX 5090, while retaining the structured-output p95 regression and
  continuation-depth caveats
  ([complete comparison](docs/measurements/2026-10-25-exp097-role-corpus.json)). Earlier observations remain historical
  ([`docs/UPSTREAM.md`](docs/UPSTREAM.md),
  [`docs/measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json`](docs/measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json),
  [`docs/measurements/2026-10-10-upstream-81c8ce09-rtx5090.json`](docs/measurements/2026-10-10-upstream-81c8ce09-rtx5090.json)).
- **Full upstream re-port from `64d10fbf` to `a754fcf3` / `77c2e5e2` — deferred in favor of targeted
  fix cherry-picks ([`alphastorm/ninfer#93`](https://github.com/alphastorm/ninfer/pull/93) `e6ac7b70`, marked merged on 2026-11-10 when fork `main` gained the `F3` merge `b871996a`; its ports are part of `F3` `e0971faf` and shipped in RTX 5090 `v0.7.0-qwen38-5090-beta.6` in `v0.17.0`).**
  As observed on 2026-11-04/05, upstream `Neroued/ninfer` master `a754fcf3` (2026-11-02; `dev` ==
  `master`) is 228 commits past the `v0.13.0`–`v0.17.0` merge base `64d10fbf`
  (`64d10fbf9f8e6bfc79ab0570b94674c5b9997929`), adding a native DGX Spark target (`sm_121a`),
  two-Spark `TP2`/`EP2`/attention-DP distributed execution, MoE routes (`NVFP4`/`FP8`) and CPU expert
  offload ("expert weight cache"), `Qwen3.8-Flash-Next` (`Qwen4Exp`) and `GLM-5.3-Flash` (`GLM5Next`)
  models, unified TOML startup configuration, and monitoring snapshots + dashboard (building on the
  earlier 215-commit delta at `1882c6ad` where 177 commits were on unrelated tracks, 26 were
  serving/context features or config refactors, 2 were marginal CPU-side latency commits, and 10 were
  serving/runtime/artifact/build fixes, with zero commits touching `NINFER_SM86`/`NINFER_SM89` guards
  or improving `Qwen3.8-27B` dense decode, DFlash2, or MTP3 kernels; see
  [`docs/UPSTREAM.md`](docs/UPSTREAM.md)). In a per-commit merge-tree probe against fork head
  `a87de361`, only `9/228` upstream commits apply cleanly (`2705a728` alone conflicts in `285` paths)
  because upstream restructured the exact seams the fork's stack sits on: (1) in
  `src/models/qwen3_5`, upstream deleted
  `program/transactions/{binding,capture,commit,context_operation,pause,reclaim,replay}.cpp`,
  `program/planning/{graph_profiles,request_plan,source}.cpp`,
  `program/storage/{checkpoints,sequence,draft_context}.cpp`,
  `program/speculative/{mtp,target_verification}.*`, and
  `program/{execution_context.h,prefill.cpp,program_impl.*,round_buffers.{cpp,h},runtime_types.h,grammar_masks.cpp,graph_execution.h}`,
  replacing them with `session/*` and
  `program/{commit,decision,draft_commit,execution,frames,graphs,lifecycle,mtp,observations,resources,scoring,inputs}.cpp`
  while both sides modified `load.cpp`, `model.{cpp,h}`, `startup.cpp`, `program/program.h`,
  `execution/{text,draft}.cpp`, `parameters.cpp`, and `profile.cpp`; (2) in `src/runtime/engine`,
  upstream split `engine.cpp` and `engine_core.h` into `engine_{execution,requests,schedule}.inl`,
  `startup.{cpp,h,inl}`, `context_capacity.{cpp,h}`, and `src/runtime/executor/*` while deleting
  `model_construction.{cpp,h}`, `model_instance.h`, `model_startup.h`, `kv_capacity.{cpp,h}`, and
  `contract/timing.h` under the fork's schema 3 durable checkpoint store (`io_uring` and
  `DirectStorage`); (3) in `src/serve`, upstream deleted `src/serve/serve_options.{cpp,h}`
  (modify/delete conflict on every lane's CLI and startup flags) and rewrote `http_server.cpp`,
  `openai_responses_*`, `request.h`, and `translate.cpp` under the fork's sibling-fanout and
  origin-authentication layer; and (4) both sides edited `src/ops/common/cuda/mma.cuh`,
  `src/ops/softmax_attention/dense/causal_cache/bf16/launch.{cu,h}`,
  `causal_softmax_attention.cpp`, `src/ops/weight_input.cpp`, `src/media/decode/decode.cpp`,
  `src/text/grammar.{cpp,h}`, and `src/text/json_schema.cpp`. For the `Qwen3.8-27B` product, `8`
  upstream fixes are already in the fork (`9822c38d`, `58733a86`, `4ec903a0`, `1e902680` subset,
  `d602894a`, `a062e016`, `704fa68d`, `45f74287`), and the `3` defects still present — upstream
  [`#434`](https://github.com/Neroued/ninfer/issues/434) request starvation under context pressure
  (`a754fcf3`, EXP-109 in
  [`docs/measurements/2026-11-05-p19-flash-next-and-starvation.json`](docs/measurements/2026-11-05-p19-flash-next-and-starvation.json)),
  upstream [`#378`](https://github.com/Neroued/ninfer/issues/378) Host placement (re-expressed from
  Saylek-ai `fix/378-host-placement`), and the `452c3f5f` recovery-loss formula — plus the `a754fcf3`
  failure-diagnostics subset were ported onto `a87de361` in
  [`alphastorm/ninfer#93`](https://github.com/alphastorm/ninfer/pull/93) (`e6ac7b70`, CI green on all
  `8/8` jobs; marked merged on 2026-11-10 when fork `main` gained the `F3` merge `b871996a`), whose
  ports are part of release source `F3` `e0971faf` (= integration `F` `a3fa0550`
  [`#95`](https://github.com/alphastorm/ninfer/pull/95)–[`#99`](https://github.com/alphastorm/ninfer/pull/99)
  + council remediation [`#101`](https://github.com/alphastorm/ninfer/pull/101)) and shipped in RTX
  5090 `v0.7.0-qwen38-5090-beta.6` in `omp-ninfer` `v0.17.0` on 2026-11-10 (where `#97` also
  replaced the `recovery_loss.h` survivor-loop `std::find` from
  [`#402`](https://github.com/Neroued/ninfer/issues/402)/[`#403`](https://github.com/Neroued/ninfer/pull/403)
  with an expected-$O(1)$ `unordered_set` removed-handle membership check cutting `32`-removed /
  `256`-survivor comparisons from `246,768` to `224`, while only the carried native `v0.8.0-beta.2`
  packages stay on `a87de361`). Everything else requires a full re-port estimated at
  **7–10 multi-agent days** at `a754fcf3` / `77c2e5e2` with low value for the dense 27B product
  today, so the deferral stands.
- **No better primary model than `Qwen3.8-27B` (`groupwise-int` v3 `81f924d4`, `20,437,521,664`
  bytes / `19.03 GiB`) as of 2026-11-10; alternative upstream and community artifacts, `FP4-Local`,
  and `Qwen4-27B` (`qwen4_exp`) deferred, rejected, or kept on watch.** Census checks through 2026-11-10 across the
  100-repo Hugging Face `library_name: ninfer` set confirm `neroued/*` artifacts are unchanged after
  2026-10-29 (`neroued/Qwen3.8-27B-NInfer` v3 `81f924d4` at commit `51630a0c`, 2026-09-15, with
  commits through `18caef28` on 2026-10-29 documentation-only; `neroued/Qwen3.8-Flash-Next-NInfer` at
  revision `001057dd`, 4 files, `108,445,200,388` bytes), `~75%` of the `ninfer` repositories
  touched in this window are for a different engine than ours (with `gguf_blocks_v1` carry-over
  targeting `iamwavecut/ninfer-all` as one cause), and no open-weight model resident in 24–32 GB
  beats `Qwen3.8-27B` on the published
  `Qwen3.8-27B` model-card agentic-coding benchmarks (**Terminal-Bench 2.1 `73.0`, SWE-bench Pro
  `61.7`, DeepSWE 1.1 `42.2`, SWE-bench Multilingual `73.8`, QwenSWEBench `79.0`**, Claude-Code
  harness at 256K context) across the qualified 32 GB and 24 GB single-GPU lanes:
  1. **`neroued/Qwen3.8-27B-nvfp4-NInfer` (`74d2c571`, `6a534f28`, 2026-09-15) — rejected:** the v3
     artifact grew to **`23,719,715,844` bytes (`22.09 GiB`)**, `+2,227,020,804` bytes (`+2.07 GiB`)
     over the `21,492,695,040`-byte (`bb336052`) v2 artifact measured in EXP-008 and `+3.06 GiB`
     over our shipped `19.03 GiB` `groupwise-int` container, so it still cannot fit the RTX 5090
     `DFlash2 K=7` `BF16` KV `131,072`-token `C2` profile.
  2. **`neroued/Qwen3.6-35B-A3B-NInfer` (`3e332976`, `qwen3_6_35b_a3b.ninfer`, `22,790,484,480`
     bytes / `21.23 GiB`, `Qwen3_5MoeForCausalLM` `35B` total / `3B` active, `256` experts with `8`
     routed + `1` shared, `q4_g64_fp16` ×95 / `q5_g64_fp16` ×91 / `q6_g64_fp16` ×5 / `q8_g32_fp16`
     ×195 / `bf16` ×487 / `fp32` ×60, text + vision + `MTP` + `DFlash` block-8, no `DFlash2`, minimum
     upstream engine revision `98dada0e` predating our `64d10fbf` merge base) — possible fast auxiliary/subagent tier on the 32 GB RTX 5090 lane,
     not a primary replacement:** delivers **`~4×` the single-stream decode of our dense 27B at
     concurrency 1 (`C1`)** and higher at concurrency 2–8 (`C2`–`C8`) on one RTX 5090 (upstream card
     claims `750.6 / 636.5 / 683.3 tok/s` `MTP3` and `866.8 / 641.6 / 732.6 tok/s` `DFlash K=7`
     across three long fixtures, `649.8 → 1,267.5 tok/s` corpus `C1 → C8`, and `437.7 / 5,510 /
     15,685 ms` TTFT at `7.7K / 64.5K / 130K`, alongside
     `677.2 tok/s` `MTP3` code decode, `620.6 tok/s` `DFlash K=7` code decode, and `17,705 tok/s`
     `7.7K` prefill at `INT8` KV; supported in the fork by `Architecture::Qwen3_5Moe` and SIMT
     `groupwise_int` MoE kernels), but its agentic-coding scores trail `Qwen3.8-27B` (**SWE-bench
     Pro `49.5` on the Qwen card / `44.6` in earlier NInfer card tables vs `61.7`** for `Qwen3.8-27B`,
     **Terminal-Bench 2.0 `51.5` vs Terminal-Bench 2.1 `73.0`**, **SWE-bench Verified `73.4`**,
     **SWE-bench Multilingual `67.2` vs `73.8`**, **`NL2Repo` `20.5` vs `42.3`**, `AIME25` `90.0`,
     `AIME26` `90.0`, `GPQA-D` `85.35`) and its `21.23 GiB` container exceeds a zero-offload 24 GB
     native budget at `131,072` tokens (`WaveCut/Qwen3.6-35B-A3B-NVFP4-NInfer-v3` at `21.04 GiB` also
     requires `sm_120a` `NVFP4` MoE kernels absent from the fork). Older `Qwen3.6-27B` (`16.29 GiB`
     `groupwise-int` / `17.07 GiB` `nvfp4`) lacks `DFlash2` and trails on SWE-bench Pro (`53.5` vs
     `61.7`).
  3. **`neroued/Qwen3.8-Flash-Next-NInfer` (revision `001057dd` / `57cf9cd0`, 4 files,
     `108,445,200,388` bytes / `101.00 GiB`, `Qwen4Exp` MoE + per-layer-embedding `PLE`),
     `neroued/GLM-5.3-Flash-NInfer` (`f1c4e21`, `191,484,328,832` bytes / `178.33 GiB`, `GLM5Next`),
     and upstream `FP4-Local` (`d49b9af7`, `7fdc0eca`) — rejected for product lanes after EXP-108
     (`Qwen3.8-Flash-Next` research screen and 32 GB offload probe):** `FP4-Local` is a
     checkpoint-ingestion and kernel family for `GLM-5.3-Flash` (`glm5_3_flash_fp4_local.ninfer`,
     `GLM5Next` native recipe preserving `NVFP4` multipliers, compressed Sparse Format (`CSF`)
     scales, `MXFP8` groups, `FP32` block scales, and per-expert activation calibration) targeting
     two-node DGX Spark `sm_121a` (`TP2` + `ADP2` two-way tensor and attention-data parallelism, with
     Spark kernel shapes under `dgx_spark/` not compiled into the RTX 5090 build and `block_scaled`
     MoE unsupported on `sm_89`/`sm_86`) and has no `Qwen3.5`/`Qwen3.8` dense 27B converter recipe or
     kernel path. `Qwen3.8-Flash-Next` requires
     `~63.3 GiB` of pinned Host-resident
     routed-expert (`Main-expert`) backing (exceeding the RTX 5090 container host's `47 GiB` physical
     / `~31 GiB` WSL2 RAM on `rtx5090-win-a`) plus `~37.7 GiB` of device-resident non-expert weights
     and KV/state (impossible on 24 GB `sm_89`/`sm_86`, where its `NVFP4`/`FP8`/block-scaled MoE
     routes are also unsupported; community fork `ashalliants/ninfer-3090` `d0ff0535` runs Flash-Next
     on one RTX 3090 with `33 GiB` host-pinned experts at `108–113 tok/s` `MTP`, recorded on watch
     while native lanes remain frozen), and `GLM-5.3-Flash` (`178.33 GiB`) requires two DGX Spark
     nodes. In **EXP-108**
     ([`docs/measurements/2026-11-05-p19-flash-next-and-starvation.json`](docs/measurements/2026-11-05-p19-flash-next-and-starvation.json),
     [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md#experiment-ledger)) on `rtxpro6000-win-a` (RTX PRO
     6000 Blackwell 96 GB, `sm_120`, same architecture class as the RTX 5090, WSL2; maintainer-private
     raw harness logs, public summary in the linked receipt), upstream NInfer `a754fcf3` (binary
     SHA-256 prefix `bcfba1b0`, artifact rev `001057dd`) was evaluated against stock Strata `v0.2.10`
     (engine `0.1.56`) + OMP `18.16.0` `IQ3_S` `262K` current RTX PRO 6000 profile under `omp-strata`'s
     preregistered rule-30 screen (`M1`–`M6`, `G24` guards): the formal NInfer resident (`N`) screen
     was **not entered** because one `W1` structured tool-call smoke emitted the tool call inside
     reasoning and ran to the length limit (a later `10×` smoke-frequency probe passed `10/10` on both
     engines; the formal verdict stands), with `W1` cold long-context TTFT across two runs at `64K`
     `4.99 / 4.87 s` vs Strata `7.02 / 7.31 s`, `200K` `15.79 / 16.47 s` vs `22.59 / 24.05 s`, and
     short `C1` (concurrency-1) decode `252–264` vs `311–323 tok/s`. Exploratory scorecard numbers
     (interleaved Strata `A1` / NInfer / Strata `A2` runs, non-gating because the formal screen was not
     entered) measured `M1` short `C4` (concurrency-4) aggregate `264.2 / 441.7 / 270.8 tok/s`
     (`1.63×`), `M2` `64K` `C4` wall `34.36 / 23.82 / 34.39 s` (`1.44×`), `M3` `200K` cold tool-turn
     TTFT `22.32 / 25.37 / 22.43 s` (`13.7%` slower), `M4` `200K` warm follow-up `2.64 / 2.22 /
     3.04 s` (unstable reference), `M5` interference stall `3.83 / 0.67 / 3.84 s` (`5.7×` lower), and
     `M6` `G24` verified passes/hour `115.6 / 95.0 / 118.9` (`20.1%` lower; `G24` NInfer `15/18` in
     `568.3 s` vs Strata `15/18` in `467.0 s` and `16/18` in `484.4 s`). When testing RTX 5090-class
     CPU expert offload (`NINFER_VRAM_BUDGET_MIB=31000` on `rtxpro6000-win-a`, forcing `HostExperts`
     with `~155 GiB` host memory available), every configuration refused at startup with `Device budget
     cannot hold the calibrated runtime and requested Context capacity` — including zero Host context
     and a minimal `C1` / `4K` / `BF16` / no-MTP / no-graphs diagnostic — and a `40,960 MiB` budget
     also refused, so no offload speed was measured. Decision: no Flash-Next lane; Strata stays the
     Flash-Next engine on the RTX PRO 6000 host (`rtxpro6000-win-a`); revisit only if upstream's
     offload planner starts on a 32 GB-class budget.
  4. **GGUF-block `Qwen3.8-27B` community tiers (`DAXZEIT/Qwen3.8-27B-UD-Q4_K_XL-NInfer-v3` `16.37 GiB`
     text+`MTP` / `16.65 GiB` +vision at `5.14` bits/weight, `WaveCut` `GSQ-RCO` `IQ3_S` `13.99 GiB`
     at `3.5` bits/weight, `funnygeeker` `UD-Q5_K_S` `17.68 GiB` / `UD-Q6_K` `20.77 GiB`, `haiping`
     `IQ3_XXS` `14.50 GiB` `_dflash2` / `16.01 GiB` `_a8`, `nerkyor` `Coder390` `12.64–27.34 GiB`
     `Q2R`..`Q8_0` tiers) and community 27B fine-tunes — GGUF-block tiers unloadable on our engine
     (upstream PR [`#282`](https://github.com/Neroued/ninfer/pull/282) closed unmerged); `Arete-27B`
     on watch:** although `DAXZEIT`'s model-card RTX 3090 `B6`/`R6` evaluation reports lower held-out
     suffix perplexity for `UD-Q4_K_XL` than the official `19.03 GiB` `groupwise-int` artifact
     (`5.750982` vs `5.844164`, and `5.828615` on `WarlaxZ/Qwen3.8-27B-NInfer-3090`; stored-weight
     99th-percentile Kullback–Leibler divergence `KLD99` `0.0738` vs `0.2105` and top-1 next-token
     agreement `96.817%` vs `94.196%` in `llama.cpp`), every GGUF-block `.ninfer` container uses
     `iamwavecut/ninfer-all`'s `gguf_blocks_v1` layout (`qwen3_8_27b_gguf`, pinned to `ninfer-all`
     `b2913b65`) carrying raw `ggml` superblocks (`Q2_K`..`Q6_K`, `IQ1_S`..`IQ4_XS`, `Q4_0`/`Q5_0`/`Q8_0`)
     that neither `alphastorm/ninfer` (release source `F3` `e0971faf` on RTX 5090 `v0.7.0-qwen38-5090-beta.6` in `v0.17.0`; `a87de361` on native `v0.8.0-beta.2`) nor upstream `Neroued/ninfer` master can load.
     Upstream PR [`Neroued/ninfer#282`](https://github.com/Neroued/ninfer/pull/282) (`convert: read
     GGUF (any ggml quant level) as a conversion source`) closed unmerged on 2026-11-02
     (`merged_at: null`), and adopting `gguf_blocks_v1` would require porting `18` block decoders
     across `src/artifact` and `sm_120`/`sm_89`/`sm_86` kernels plus full three-lane re-qualification
     and 1,120-prompt quality screens. Among newer open-weight coding models and 27B fine-tunes,
     `Arete-27B` (`Qwen3.8-27B` fine-tune, `~16.5 GB` in upstream `Q4_K_M` GGUF, convertible through
     the native `qwen3_5` recipe because it shares the `Qwen3.8-27B` architecture) and native-format
     community 27B conversions (`funnygeeker/Qwen3.8-27B-BaseQuant-V1-Ninfer-V3` `15.56 GiB`,
     `jgamboa/Qwen3.8-27B-NInfer-4090`, `WarlaxZ/Qwen3.8-27B-NInfer-3090`) stay on watch, while
     `Flint v1.0` (`40B` MoE, `23.38 GiB` `UD-Q4_K_XL`, SWE-bench Verified `74.2` but Terminal-Bench
     2.1 `54.9` vs `73.0`, `ninfer-all` `flint_gguf` only), `SWE-2 Flash` (`276B` total / `12B`
     active MoE, no public weights), `Nanbeige4.3-33B` (dense `33B`, published NInfer artifact uses
     unloadable `IQ3_XXS` GGUF blocks), `North Mini Code 1.0` (`30B` MoE, `2026-06-09`, no NInfer
     architecture support), `Nemotron 3.5 Bolt 74B` (`74B` / `9B` active MoE, no NInfer architecture
     support), `MiniMax-M3.1-Flash` (`23B` active MoE, `194–249 GB` GGUFs exceed 24–32 GB), and
     `DeepSeek-V4.1-Flash` (`106.7 GiB` experts exceed 24–32 GB, `ninfer-all` only) are rejected.
  5. **`Qwen4-27B` (`qwen4_exp` dense 27B) — deferred (still no public weights as of 2026-11-10;
     upstream `feat/qwen4-27b-ops` unchanged at `e1874e94`):** no public `Qwen4-27B` weights, model
     card, license, context specification, or agentic-coding/tool-use benchmarks exist (`Qwen` and
     `nvidia` Hugging Face organizations publish no `Qwen4` checkpoints, `IteraCompute/Qwen4-27B-NVFP4`
     remains an empty placeholder with no inference files, and `Chungulus/Qwen4-27B-*` repositories
     created on 2026-11-09 are tagged `placeholder`). In Hugging Face `transformers`
     (`Qwen4ExpTextConfig`) and upstream `Neroued/ninfer` master (`src/models/qwen4_exp/config.cpp`,
     `docs/maintainer/qwen4_exp-model.md`), `qwen4_exp` currently implements only the
     `Qwen3.8-Flash-Next` MoE+PLE variant (`hidden_size = 2560`, 48 layers, 512 experts, one PLE
     layer) and rejects the dense 27B variant (`hidden_size = 5120`, 64 layers, dense SwiGLU FFN, no
     PLE, query-sparse attention (`QSA`) with 24 query heads and 4 KV heads, and a 4-bit `Q4`
     proposal head). Upstream `Neroued/ninfer` implements the 27B kernel checklist across 19 commits
     on unmerged feature branch `feat/qwen4-27b-ops` (tip `e1874e94`, 2026-10-29, unchanged on
     2026-11-10 at `204` commits past `64d10fbf` in
     [`docs/measurements/2026-11-10-upstream-watch.json`](docs/measurements/2026-11-10-upstream-watch.json),
     branched from 2026-10-27 master commit `04d0d15b`: RTX 5090 `NVFP4` `28672×5120` + fused SwiGLU
     and `5120×14336`, `FP8` `14976×5120` and `5120×5120`, `Q4` `248320×5120` vocabulary projection,
     hidden-size-5,120 (`H5120`) gated-residual norm/combine and `FP8` four-stream residual mixing,
     and four-KV-head `QSA` preparation and tuned sparse GQA across `BF16`, `INT8`, `NVFP4`, and
     8-bit-key/4-bit-value (`K8V4`) KV caches), while upstream `master` (`04d0d15b`/`1882c6ad`/`77c2e5e2`)
     carries only unchecked design docs (`docs/designs/qwen4-27b-op-checklist.md`) and leaves the
     dense 27B model layer and converter recipes (`tools/convert/official_recipes.py`) unimplemented.
     `feat/qwen4-27b-ops` stays on watch until public weights and upstream model/converter support
     exist.
- **DGX Spark (`sm_121a`, 128 GB single-node and two-Spark distributed) — do not buy for this
  workload (decision support, not measured by us).** Third-party NInfer measurements on one 128 GB
  DGX Spark (`baristahaus/ninfer-gb10`) reach `31.5–32.6 tok/s` without speculation, `59.9 tok/s`
  `MTP3` `C1`, `121.4 tok/s` aggregate at `C4`, and `~2,500 tok/s` prefill; no published NInfer
  two-Spark numbers exist (upstream `docs/performance.md` reports none), and third-party vLLM,
  SGLang, and TensorFold two-Spark single-stream runs reach `47–89 tok/s`. By contrast, Strata on
  `rtxpro6000-win-a` (RTX PRO 6000 Blackwell 96 GB) delivers `318 tok/s` at a `212K` prompt and
  `9,366 tok/s` `100K` prefill. With a 128 GB Spark priced at `~$6,950` (October 2026), hourly cloud
  rental (`$0.79–1.90/h`) is the low-cost path if two-Spark-only `GLM-5.3-Flash` data is ever
  wanted.
- **Native `sm_86`/`sm_89` small-T tensor-core decode and `Group64` A8 prefill — rejected for
  `v0.14.0` (EXP-069, EXP-099, EXP-100).** Earlier `sm_89` small-T Q5 tensor-core verify measured
  only +0.38% decode at 26K and +0.40% at 60K on RTX 4090, below the 2.0% and 1.0% promotion
  margins
  ([`docs/measurements/2026-09-28-rtx4090-q5-small-t-mma.json`](docs/measurements/2026-09-28-rtx4090-q5-small-t-mma.json)).
  In the `v0.14.0` engine campaign, the `sm_86`/`sm_89` small-T tensor-core decode candidate
  (tested binary source `dce5cf06`, cleanly rebased to `e1c2f66f`, EXP-099) raised C1 decode
  (`4,541` fresh prompt tokens, `1,024` completion tokens, `0` reuse) by +39.8% on RTX 3090
  (`84.42 → 117.98 tok/s` at 300 W; `90.79 → 126.81 tok/s` at 350 W) and +8.3% on RTX 4090
  (`151.23 → 163.76 tok/s` at 450 W), but failed the T2 84-role output-divergence gate (`<= 8`
  divergent cases allowed for rounding-only promotion; `55/84` on RTX 3090 and `58/84` on RTX
  4090) and the 150-pair symmetric `Application A` one-sided binomial sign-test screen on RTX 3090
  added secret fingerprints (`a = 4` baseline-only vs `b = 12` candidate-only,
  `p = 0.0384 < 0.05`,
  [`docs/measurements/2026-10-27-native-small-t-tensor-core-decode.json`](docs/measurements/2026-10-27-native-small-t-tensor-core-decode.json)).
  Similarly, `Group64` A8 prefill (provisional campaign source `254a586a`, cleanly rebased to
  `7ee32e20`, EXP-100) sped up C1 prefill `×1.312` on RTX 4090 at 450 W and `×1.611` (300 W) /
  `×1.618` (350 W) on RTX 3090 and 130,048-token exact retrieval `×1.217` on RTX 4090 and `×1.366`
  on RTX 3090 at 300 W, but failed the 200-pair symmetric `Application B` leak-presence screen on
  RTX 4090 (`41` both, `a = 0` OFF-only, `b = 5` ON-only, `154` neither; `p = 1/32 = 0.03125 <
  0.05`), while RTX 3090 passed (`41` both, `a = 0`, `b = 4`, `155` neither; `p = 1/16 = 0.0625`)
  on four of the same five `worklog-007`/`worklog-014` prompts and was kept off by founder
  decision; `Group64` A8 stays compiled off on both native lanes in `v0.14.0` while the
  byte-identical attention prefill specializations (+4.96% on RTX 4090 at 450 W and +5.40% on RTX
  3090 at 300 W at 130,048 tokens) shipped
  ([`docs/measurements/2026-10-27-native-group64-a8-prefill.json`](docs/measurements/2026-10-27-native-group64-a8-prefill.json)).
- **DFlash2 on the native RTX 4090 and RTX 3090 lanes — initial unquantized port (EXP-089),
  shorter RTX 4090 draft windows `K=6`/`K=5` (EXP-103), and opt-in `FP32` vocabulary-head logits
  (EXP-104) rejected; default `DFlash2 K=7` shipped on both native lanes in `v0.16.0` (EXP-098,
  EXP-101–EXP-105).**
  The initial `alphastorm/ninfer` `c11b02f4` port failed `sm_89`/`sm_86` device link on three `W8`
  static shared-memory kernels (`49,664–50,176` B vs `49,152` B) and its unquantized `1.65 GiB`
  drafter did not fit the 131,072-token 24 GB budget
  ([`docs/measurements/2026-10-01-dflash2-native-lanes-feasibility.json`](docs/measurements/2026-10-01-dflash2-native-lanes-feasibility.json)).
  On the `64d10fbf` lineage (`2c6f423b`), the `W8` link blocker is gone and the `sm_86`/`sm_89`
  load-time fit seam (`Q4_G64_FP16` draft MLP `gate`/`up` + `1,350,860,800`-byte host-mapped
  `token_embedding`) is in the engine: on `v0.13.1` control binaries `7a25cd72` at `65,536` INT8
  KV, RTX 3090 passed the 108-role decode gate (`weighted >= 1.08`, every case `>= 0.95`) at
  `×1.29968` (minimum case `0.97987`) and then passed the 131,072-token INT8 fit and true-cold
  durability proof on source `e456af37b` (`21,968 MiB` peak, `768 MiB` headroom, `0` extra
  device-state slots), while RTX 4090 passed the aggregate bar (`×1.26362`) on `7a25cd72` but
  missed the `0.95` per-case floor on depth-0 case `log-024@0` (`0.945889`, reproduced at `0.9451`
  in isolated ABBA,
  [`docs/measurements/2026-10-27-native-dflash2-gates-and-fit.json`](docs/measurements/2026-10-27-native-dflash2-gates-and-fit.json)).
  In `v0.16.0` ([`EXP-101`–`EXP-105`](docs/PERFORMANCE.md#experiment-ledger)),
  config-only shorter draft windows on the `v0.14.0` RTX 4090 binary failed `log-024@0` against
  `MTP3` and were **rejected**: **`K=6` cross ratios `0.8625–0.8642`** (`116.98 / 116.97` vs `135.37
  / 135.63 tok/s`, median `0.8633`) and **`K=5` cross ratios `0.8668–0.8673`** (`117.61 / 117.63` vs
  `135.62 / 135.69 tok/s`, median `0.8671`; `K=3` was already rejected at `0.811526` with `13/84`
  misses), while the `K=7` `131,072`-token `INT8` `C1` fit passed (`1,449,132,032` B available on
  `2c6f423b` with `0` extra slots, `1,056,964,608` B on `26fa28d0` `06526bdb` with `+2` extra slots,
  EXP-103). Opt-in **`FP32` vocabulary-head logits (`--fp32-head-logits`,
  `engine.fp32_head_logits: true`, `+8,442,880` persistent bytes at `K=7`/`C=2`) also failed
  `log-024@0` at `0.9016–0.9025`** (`122.29 / 122.26` vs `135.50 / 135.61 tok/s` on `P16` binary
  `31583e3f`, median `0.9021`, EXP-104) and is **rejected** (the option stays off in all profiles),
  whereas `DFlash2 K=7` with `--fp32-head-logits` off (the default) on `P16` engine build
  `31583e3f` passed `log-024@0` at **`0.9627–0.9635`**, passed on build `08257eec` at
  **`0.96186–0.96294`**, reached **×1.2736** on the 108-case role corpus `role108` (`139.87 → 178.13
  tok/s`, all `115` cases **×1.2741**, `7` supplementals min **×1.0804**) in the final `26fa28d0`
  shipping-package (`06526bdb`) 115-case ABBA speed gate with `log-024@0` at **`0.934`** (`139.41 →
  130.19 tok/s`, below the `0.95` per-case decode ratio floor) waived by the founder with
  disclosure ([`rtx4090-speed.json`](releases/v0.16.0/qualification/rtx4090-speed.json) `32acdecc`,
  [`rtx4090-speed-waiver.json`](releases/v0.16.0/qualification/rtx4090-speed-waiver.json) `92b94c4a`),
  passed the RTX 3090 84-role depth-0 ABBA speed gate at **×1.2684** (`79.37 → 100.67 tok/s`, min
  **0.9764×** on `log-024@0`, zero waived cases, `84/84` within-engine and `36/84` cross-engine
  byte-identical in [`rtx3090-speed.json`](releases/v0.16.0/qualification/rtx3090-speed.json)
  `c904d341`), and passed `EXP-101` (**PASS** in
  [`rtx3090-windows-native.quality-screen.json`](releases/v0.16.0/qualification/rtx3090-windows-native.quality-screen.json)
  `671659f0`: `1,120` unique prompts, `672` gate + `504` redaction pairs overlapping on `56` control
  variants, both arms `80/80` deterministic with `0` missing/error samples, `771/1,120` paired
  outputs changed, **9/9** primary bounds passed: `recall` lower `-0.0073`, `precision` lower
  `-0.0070` vs `-0.02`; `unsupported` upper `+0.0089` vs `+0.03`;
  `schema`/`tool_selection`/`tool_argument` lower `0` vs `-0.02`; `duplicate` upper `+0.0059` vs
  `+0.02`; `redaction` lower `-0.0119` vs `-0.05`; `secret_leak` ratio `1.0294`, upper `1.0673 <
  1.10`, counts `545 → 561`, not zero) and `EXP-102` (**PASS** in
  [`rtx4090-windows-native.quality-screen.json`](releases/v0.16.0/qualification/rtx4090-windows-native.quality-screen.json)
  `6231dccd`: `1,120` unique prompts, `672` gate + `504` redaction pairs overlapping on `56` control
  variants, both arms `80/80` deterministic with `0` missing/error samples, `777/1,120` paired
  outputs changed, **9/9** primary bounds passed: `recall` lower `-0.0082`, `precision` lower
  `-0.0093` vs `-0.02`; `unsupported` upper `+0.0045` vs `+0.03`;
  `schema`/`tool_selection`/`tool_argument` lower `0` vs `-0.02`; `duplicate` upper `+0.0046` vs
  `+0.02`; `redaction` lower `-0.0139` vs `-0.05`; `secret_leak` ratio `1.0525`, upper `1.0985 <
  1.10`, counts `533 → 561`, not zero) on `26fa28d0`, shipping on both native lanes in `v0.16.0`
  (`v0.8.0-qwen38-{4090,3090}-beta.1`).
- **NVFP4 and FP8 KV caches with DFlash2 on the RTX 5090 — rejected by quality screen (EXP-084,
  EXP-085, EXP-087, EXP-088).** Raised KV capacity to four device state slots, but failed the
  1,120-prompt paired quality screen on unsupported claims or secret leaks; BF16 KV remains shipped
  ([`docs/measurements/2026-10-01-dflash2-powered-quality-screen-rtx5090.json`](docs/measurements/2026-10-01-dflash2-powered-quality-screen-rtx5090.json),
  [`docs/measurements/2026-10-01-dflash2-fp8-kv-quality-screen-rtx5090.json`](docs/measurements/2026-10-01-dflash2-fp8-kv-quality-screen-rtx5090.json)).
- **Deeper speculative drafting and 8-bit KV on RTX 5090/4090 — rejected (EXP-011..014, EXP-041,
  EXP-092).** MTP K=5 and K=7 trailed MTP3 by 7.3–24.7%
  ([`docs/measurements/2026-09-04-rtx5090-mtp-agent-ablation.json`](docs/measurements/2026-09-04-rtx5090-mtp-agent-ablation.json)),
  DFlash2 K=15 did not pay
  ([`docs/measurements/2026-10-03-dflash2-round-costs-rtx5090.json`](docs/measurements/2026-10-03-dflash2-round-costs-rtx5090.json)),
  and INT8/FP8 KV on the groupwise-int artifact regressed the private role-corpus screen
  ([`docs/measurements/2026-09-04-rtx5090-variant-campaign.json`](docs/measurements/2026-09-04-rtx5090-variant-campaign.json),
  [`docs/measurements/2026-09-16-two-long-session-capacity.json`](docs/measurements/2026-09-16-two-long-session-capacity.json)).
- **`rk4v4` 4-bit KV cache (`262,144`-token native context) and beyond-131,072-token extensions —
  [`alphastorm/ninfer#60`](https://github.com/alphastorm/ninfer/issues/60) token-32 mismatch
  reclassified as oracle prefill geometry (`EXP-116`); `rk4v4` deferred on a geometry-matched
  durability oracle decision (`EXP-107`, `EXP-116`); KV prefetch and E8/RotorQuant parked.** Native
  head-dim-256 (`D256`) `rk4v4` (`rk4v4_h256_lloyd_g64_s4_g32_v1`, ported from
  `ashalliants/ninfer-3090` `f5cec0a6`; `17,920` B/token vs `INT8` `33,792` B/token, `47.0%` smaller
  per-token KV) passed `7/7` `FP64` op/graph/store test executables and held-out perplexity on both
  `sm_86` and `sm_89` (`16,984` scored tokens across `32` windows at `1,024` context / `512` stride:
  mean NLL `1.643463 → 1.646910`, **$\Delta\text{NLL} = 0.00345 \le 0.02$**, PPL `5.173052 →
  5.190916`, max domain `+0.006273 <= 0.05`) and fit at **`262,144`-token `C1` on the RTX 3090**
  (`1,097,859,072` B available above the `805,306,368` B / `768 MiB` floor; exact `130,048`- and
  `250,062`-token diagnostic retrieval in `197.86` and `503.57 s`) as well as `245,760`-token `C2`
  (`1,135,607,808` B available) and `229,376`-token `C2` (`1,429,209,088` B available), while on the
  RTX 4090 (`chunk 2,048`, `640 MiB` floor) `262,144`-token `C1` and `245,760`-token `C2` refused
  startup admission and `229,376`-token `C2` passed startup (`952,107,008` B available). In
  `EXP-107`, the ordinary `chunk 1,024` zero-reuse true-cold restore oracle failed on the RTX 3090
  at **token 32** at `262,144`-token `C1` (`3,093` prompt / `3,066` cached tokens, cold token ID
  `48117` vs restored token ID `3635` despite byte-exact CPU page-layout inversion of the
  `55,050,240`-byte checkpoint payload, SHA-256 `53e8f8bc`) and at **tokens 16–32** on the first of
  two `59,866`-token concurrent sessions (`59,840` cached tokens; second session `32/32` tokens
  equal) at `245,760`-token `C2` and `229,376`-token `C2`. In **EXP-116** (`2026-11-10`,
  [`docs/measurements/2026-11-10-p20-overnight.json`](docs/measurements/2026-11-10-p20-overnight.json))
  on `rtx3090-win-a` (diagnostic source `f6ed4381`), a three-way geometry control proved that
  [`#60`](https://github.com/alphastorm/ninfer/issues/60) is **oracle prefill chunk geometry
  (`oracle_geometry_explains_token_mismatch`), not a checkpoint-transport or `rk4v4` kernel
  defect**: a cold `rk4v4` run (`3,093` computed, `0` cached) replaying the restored arm's `3,066`
  capture split and speculative suffix prefill chunks (`18, 2, 3, 4` tokens at bases `3066, 3084,
  3086, 3089`) matched the restored run **32/32 tokens** (both emitting token `32` = `3635`, whereas
  ordinary `chunk 1,024` cold matched `31/32` and emitted `48117` at token `32`), seed-to-restored
  canonical KV and continuation-selected `StateImage` transport were byte-exact, all three
  `3,093`-token prompt ledger hashes matched, and the `int8-group64` (`INT8`) control was **32/32
  three-way identical** (`48117` at token `32`). Adopting a geometry-matched true-cold durability
  oracle (followed by one non-instrumented RTX 3090 exact-token hold and RTX 4090 fit/quality/release
  qualification to unlock RTX 4090 `C2` and `262,144`-token native context) is deferred as a founder
  product-contract decision (`--kv-dtype rk4v4` stays off in shipped profiles; EXP-107, EXP-116 in
  [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md#experiment-ledger)), and paged host-to-device KV
  prefetch beyond 262K tokens and E8-lattice/RotorQuant ceiling work remain parked in
  [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md#ideas-backlog).
- **Own-prefix n-gram copy-drafting revival — declined and not shipped in `v0.17.0` (`EXP-111`;
  `E5` PR [`alphastorm/ninfer#94`](https://github.com/alphastorm/ninfer/pull/94) `d117bc17`
  closed).** In the earlier RTX 5090 own-prefix copy-drafting spike (slice `S1`, binary commit
  `60a95b0e`, `alphastorm/ninfer` worktree head `a05d6e77`), own-prefix 4/8/16-token hashed suffix
  copy drafting (`--ngram-draft-tokens 0|15`, default `0`, requires `DFlash2`, minimum match `12`,
  maximum copy `15` when `> K=7`) sped up synthetic edit turns by **+53.434%** (`+53%`), regressed
  short Read acknowledgements by **-4.205%** (`-4.2%`), and kept **15/23** outputs byte-identical
  (diverging on copy rounds where verify width is `16` vs `8` columns or on widened `C2` two-request
  partners). Under the [`EXP-085`](docs/PERFORMANCE.md#experiment-ledger) 1,120-prompt powered-screen
  rule, reviving copy drafting as a release feature required `>= 15%` (`×1.15`) pooled session decode
  speedup on real coding-agent output. In **EXP-111** (`2026-11-10`,
  [`docs/measurements/2026-11-10-p20-overnight.json`](docs/measurements/2026-11-10-p20-overnight.json)),
  replaying **3,000 nonempty assistant turns across 649 sessions** (`1,764,539` Qwen native-chat-format
  output tokens tokenized with pinned `Qwen/Qwen3.8-27B` revision `37561816`, `tokenizer.json`
  SHA-256 `0997f410...`, sampled from a 30-day census of `68,351` assistant records / `68,221`
  nonempty / `876` sessions where `0` local-Qwen/ninfer/Strata turns occurred, so cloud-model turns
  serve as structural proxies) measured **20.5413%** (`20.5%`, `362,459` tokens across `45,495`
  proposal rounds, `13.23%` zero-acceptance rounds, `14.6983%` in accepted runs `>= 12` tokens,
  `19.38%` payload-only excluding `11.87%` XML/JSON tool-call wrapper formatting) accepted copy share
  under fixed minimum `12` and **13.2531%** (`13.3%`, `233,857` tokens across `25,626` rounds,
  `10.14%` zero-acceptance, `10.3887%` in runs `>= 12`, `12.68%` payload-only) under adaptive `12 →
  24 → 36` backoff. Copy coverage was concentrated in edit/hashline/patch arguments (**39.76% fixed /
  31.52% backoff**, `115,315 / 290,045` tokens), Qwen/tool formatting (**29.20% / 17.49%**), other
  tool arguments (**23.87% / 11.24%**), bash/eval commands (**23.37% / 15.51%**), and
  write/file-content arguments (**17.00% / 10.24%**, `45,431 / 267,203`) versus visible reasoning
  (**3.61% / 1.70%**, `16,823 / 465,861`) and plain text (**2.87% / 2.06%**). At
  [`EXP-078`](docs/PERFORMANCE.md#experiment-ledger)'s `4.631` neural tokens/round and copy round cost
  `1.41 → 1.22` neural-round equivalents, pooled session decode speedup is **1.06664–1.09314×**
  (`+6.7–9.3%`) fixed and **1.05484–1.06928×** (`+5.5–6.9%`) with backoff (combined **×1.055–1.093**,
  or **1.02958–1.05425×** / **1.01476–1.02812×** with `S1`'s `-4.205%` short-Read lookup-toll
  sensitivity; median session ratio `1.03952×` / `1.02016×` at cost `1.41`, `87/649` and `59/649`
  sampled sessions `> +15%`), below the `>= 15%` bar. Revival was therefore declined for `v0.17.0`,
  and the rebased default-off `E5` branch in
  [`alphastorm/ninfer#94`](https://github.com/alphastorm/ninfer/pull/94) (`d117bc17`, CI green; a GPU
  token-identity golden test fixture was prepared and deferred) was closed unmerged and not shipped.
- **Native RTX 3090 `--gpu-keep-warm-ms 60000` (`sm_86`) and native RTX 4090 `--prefill-chunk 2048`
  (`sm_89`) configuration probes — rejected (`EXP-115`).** On the shipped `v0.16.2`–`v0.17.0`
  (`v0.8.0-beta.2`, source `a87de361`, model `81f924d4`) native binaries
  ([`docs/measurements/2026-11-10-p20-overnight.json`](docs/measurements/2026-11-10-p20-overnight.json)):
  (1) on `rtx3090-win-a` (`15a4db46`, `350 W` serving cap / `370 W` restored, `A/B/B/A` fresh servers,
  `6` post-idle observations per arm/delay on `163–226`-token prefix-cold prompts), config-only
  `--gpu-keep-warm-ms 60000` with the compiled `sm_86` `3.5/10 ms` single-warp spin pattern failed to
  hold NVIDIA performance state `P2` (dropping to **`P5` at `12 s`** with `7.4%` `P2` occupancy and
  `+37.9 W` / `34.7 → 72.6 W` held draw, and to **`P8` at `30 s` and `58 s`** with `1.8%` and `1.1%`
  `P2` occupancy and `+19.8 W` / `10.0 → 29.8 W` and `+15.4 W` / `9.8 → 25.2 W` held draw) and missed
  the `<= 1.10×` post-idle-to-back-to-back TTFT gate at every delay (median of the six
  per-observation paired ratios against adjacent back-to-back controls: **1.364×** at `12 s` with
  aggregate medians `0.5456 s` post-idle / `0.4173 s` back-to-back vs `0.6716 / 0.4181 s` without
  keep-warm; **1.362×** at `30 s` with aggregate medians `0.5667 / 0.4199 s` vs `0.6617 / 0.4219 s`;
  and **1.521×** at `58 s` with aggregate medians `0.6501 / 0.4212 s` vs `0.6435 / 0.4208 s`; `27/27`
  outputs byte-identical; holding `P2` on `sm_86` requires building a different spin pattern); and
  (2) on `rtx4090-win-a` (`ffee91bf`, `450 W`, `131,072` `INT8` `C1`, `+2` extra slots, `A/B/B/A`
  against shipped `chunk 1024`), `--prefill-chunk 2048` passed startup fit (**848.00 MiB** available
  vs `1,008.00 MiB` at `1,024`, `>= 640 MiB` floor), but gained only **×1.0236** (`2,122.99 →
  2,173.11 tok/s`) on `benchmark_c1` (`4,541` prompt / `1,024` completion tokens) prefill and
  **×1.0149** (`1,562.57 → 1,585.82 tok/s`) on `130,048`-token exact retrieval (both `< 1.04` gate),
  regressed `benchmark_c1` decode to **×0.8818** (`254.40 → 224.33 tok/s`, `< 0.98` gate; 84-prompt
  role corpus `role84` decode `174.67 → 174.85 tok/s`, `×1.0011`), and diverged on `40/84` `role84`
  cases (**44/84** cross-arm byte identity vs `84/84` within each arm, which would require a full
  1,120-prompt powered quality screen for `<= 2.36%` prefill gain). Both native `v0.8.0-beta.2`
  profiles remain unchanged in `v0.17.0` (where the RTX 3090 native post-route compaction campaign
  failed and was founder-waived with disclosure, tracked in
  [`alphastorm/ninfer#89`](https://github.com/alphastorm/ninfer/issues/89), with product tooling
  follow-ups in [`alphastorm/omp-ninfer#149`](https://github.com/alphastorm/omp-ninfer/issues/149)).
- **Low-acceptance `DFlash2 → MTP3` fallback ([`#58`](https://github.com/alphastorm/ninfer/issues/58))
  dropped (`EXP-110`); `C2` pair-round `K=6144` `T=16` Q5 mixer port (`EXP-092` `3a2fadbd`) already
  covered (`EXP-114`); Jinja `.strip()` edge decode and small-T module preload skipped (`EXP-117`);
  `E4` opt-in prefill pacing shipped default-off in `v0.17.0` (`EXP-119`,
  [`alphastorm/ninfer#95`](https://github.com/alphastorm/ninfer/pull/95)); first arrival source-wait
  fix closed unmerged and not shipped (`EXP-118`,
  [`alphastorm/ninfer#100`](https://github.com/alphastorm/ninfer/pull/100), tracked in
  [`alphastorm/ninfer#102`](https://github.com/alphastorm/ninfer/issues/102)); and 2026-11-10 RTX
  5090 runtime fixes and council
  [`CR-20261110T083627Z-a3fa0550`](releases/v0.17.0/review/runtime-ledger.json) remediation shipped in
  `v0.7.0-qwen38-5090-beta.6` (`F3` `e0971faf`, `omp-ninfer` `v0.17.0`, published 2026-11-10;
  `EXP-112`, `EXP-113`, `EXP-117`–`EXP-121`).** In the `2026-11-10` overnight measurement campaign
  ([`docs/measurements/2026-11-10-p20-overnight.json`](docs/measurements/2026-11-10-p20-overnight.json)):
  (1) across `9,430` completed requests in the maintainer-private `rtx5090-win-a` production request
  logs (`EXP-110`, `2026-08-25` to `2026-11-04`), low-acceptance `DFlash2` decode (`< 3`
  tokens/round) accounted for only **3.45%** of decode time (`324` of `7,317` requests with rounds,
  `1,340.01` of `38,864.83 s`, pooled `3.875` tokens/round) in `DFlash2 v0100p+` filtered (`v0.10.0+`
  logs excluding diagnostic/probe traffic) and **6.26%** (`11` of `176` requests, `5.98` of `95.57
  s`, pooled `4.124` tokens/round) in recent `v0.13–v0.16.2` filtered traffic, yielding
  **0.469%–0.851%** modelled decode-time recovery under `EXP-092` round costs (`14.03 ms` `MTP3` vs
  `16.24 ms` `DFlash2`, below the `>= 3%` trigger), so
  [`#58`](https://github.com/alphastorm/ninfer/issues/58) is **dropped** while recent traffic
  (`31.89%` decode / `50.21%` prefill / `8.16%` queue, `25.57%` request overlap with `1.560×` median
  matched elapsed decode slowdown on `8` requests overlapping a peer's pre-first-token window and
  `1.340×` on `14` decode-overlap requests, `0` `>= 60 s` global-decode stalls, `0`
  preemptions/replays across `180` recent completions, cached = strict-warm TTFT p50/p90/p99 `0.265 /
  0.357 / 1.466 s` dropping to `0.376 s` p99 when excluding `4` first-after-`server_start` host-KV
  restores that account for `84.0%` of recent top-decile TTFT above the cohort median) ranks `C2`
  prefill/decode interference as the top runtime lever; (2) an Nsight Systems `2026.3.2` trace on
  `rtxpro6000-win-a` (`e6ac7b70` `8235ada4`, `EXP-114`) confirmed that in a complete `C2` two-request
  decode round (`743` kernels, `17.838570 ms` summed) all **64** `K=6144`, `T=16` `LinearAdd`
  mixer-output calls already dispatch to `q5_a16_sliced_k_mma_kernel` (`320` CTAs) at **19.767594
  µs/call** (**1.265126 ms/round** vs `EXP-092`'s `1.41 ms` target), closing `EXP-092`'s open
  pair-mixer half without porting `3a2fadbd`; and (3) pre-cut slice, proxy, and integration
  measurements across fork PRs
  [`alphastorm/ninfer#95`](https://github.com/alphastorm/ninfer/pull/95)–[`#101`](https://github.com/alphastorm/ninfer/pull/101)
  — shipped on the RTX 5090 lane in `v0.7.0-qwen38-5090-beta.6` (`omp-ninfer` `v0.17.0`, published
  2026-11-10) from fork source `F3` `e0971faf` = integration `F` `a3fa0550`
  ([`#99`](https://github.com/alphastorm/ninfer/pull/99): `#97` `E1` `#434` starvation and bounded
  fresh-admission rotation window, `#98` `E2` serve robustness, `#96` `E3` host NFC boundary
  normalization, and `#95` `E4` opt-in prefill pacing shipped **default-off**) + council
  remediation [`#101`](https://github.com/alphastorm/ninfer/pull/101) (`F2` `bdc665a3` / `F3`
  `e0971faf`: pressure-save wait and fresh-window budget), while `E5` copy drafting (`#94`, declined
  and closed) and the arrival source-wait fix (`#100`, closed unmerged and tracked in
  [`alphastorm/ninfer#102`](https://github.com/alphastorm/ninfer/issues/102)) were not shipped —
  showed in **EXP-112** (slice `E1`,
  [`alphastorm/ninfer#97`](https://github.com/alphastorm/ninfer/pull/97)) that on `rtxpro6000-win-a`
  candidate `df7aeb52` (`c46c67d1`) reached **2.266069104 s** (`2.27 s < 5 s`) max admitted pause
  (`2.086055400 s` max fully-paused interval), **0** HTTP `503` (vs `6` on same-session `e6ac7b70`
  control), **2/2** long completions (vs `1/2`), and **3/3** `DFlash2` and `MTP3` greedy parity, and
  on `rtx5090-win-a` candidate `375bb848` (`7f988154`, built in `e7f34ca2`) reached **2.9986773779965006
  s** (`3.0 s`) max fully-paused interval (`3.2083587239976623 s` pause→recovery) with **2/2**
  `40,000`-token long completions and **0/51** fresh-arrival HTTP `503` (fresh TTFT p50/p95 `0.400092 /
  3.392509 s`) versus production `a87de361` (`cc99a460`) starving its second long request at
  **367.9977688699946 s** (`368.0 s` `paused_wait_s`, `368.62261531799595 s` max scheduler pause,
  `1/2` completed, `0/54` `503`, fresh TTFT p50/p95 `0.292190 / 0.535915 s`); in **EXP-113** and
  **EXP-118** that cold `130,084`-token `EXP-077` interference measured **6.375002 tok/s**
  co-resident decode (`350.6 / 470.0 ms` inter-output-event gap p50/p99, **46.49 s** long-request wall,
  **44.23 s** server prefill) and **0.803794 s** arrival-during-prefill TTFT on `rtxpro6000-win-a`
  (`e6ac7b70`), **5.109089 tok/s** (`a87de361` production, `430 / 619 ms` gap p50/p99, `23.071937 s`
  arrival TTFT, `~60 s` wall) / **5.127272 tok/s** (`375bb848` `E1` candidate, `405 / 618 ms` gap
  p50/p99, `20.999604 s` arrival TTFT) on `rtx5090-win-a` at the `2,048 MiB` scratch checkpoint quota,
  and **5.254542 tok/s** co-resident decode (`430.66 / 618.89 ms` gap p50/p99, `59.71 / 58.85 s`
  prefill-during-decode `PDD` / decode-during-prefill `DDP` long wall) with **23.073498 s** arrival TTFT (`+0.001561 s` delta) on `rtx5090-win-a`
  at the shipped `24,576 MiB` checkpoint quota (`production-exp077-q24-01`), proving the `20–25 s`
  arrival delay is a **19.49–23.72 s retained-preferred-source wait** (`preferred_reused_tokens=111`,
  `fallback_reason=none`), while the first source-wait candidate fix in stacked
  [`alphastorm/ninfer#100`](https://github.com/alphastorm/ninfer/pull/100) (`7f2c71fd`, GPU binary
  commit prefix `1c5`, binary `20782176...`, CPU `EngineCore` `31/31` + `ResourceManager` PASS,
  `0.0600276 s` wait at `60 ms` allowance, CI green) did **not** remove a `3`-pair warm-history GPU reproduction on
  `rtxpro6000-win-a` (base `source_wait` `44.750 / 44.859 / 44.877 s` vs candidate `44.740 / 44.776 /
  44.945 s`, candidate TTFT `44.942 / 44.973 / 45.144 s`) because `engine_core.h:2703` reserves
  resident units before the fresh scan and `try_admit_one:1893` refuses while reclaim occupies the
  `Native` context slot (closed unmerged and not shipped; tracked in
  [`alphastorm/ninfer#102`](https://github.com/alphastorm/ninfer/issues/102)); in **EXP-119** (slice
  `E4`, [`alphastorm/ninfer#95`](https://github.com/alphastorm/ninfer/pull/95)) that the `7`-arm cold
  prefill-pacing curve on `rtxpro6000-win-a` (`--decode-rounds-per-prefill` `k1`..`k32` and
  `--prefill-stall-budget-ms` `b250`/`b500`) raised co-resident decode from `6.375` (`e6ac7b70`) and
  `6.600` (`e4-b95f-off`) through `6.400` (`k1`), `12.025` (`k2`), `24.160` (`k4`), `47.901` (`k8`),
  and `73.400` (`b250-k16`) to **103.205 tok/s** (`b500-k32-v2`, `265.079 ms` gap p99, `0.628 / 0.654
  s` arrival TTFT, `49.658 / 45.701 s` `PDD`/`DDP` long wall, `1.068 / 1.005×` vs baseline), but corresponding-repeat
  `C2` outputs differed across repeats (shipped **default-off** at `0`); in **EXP-120** (slice `E2`,
  [`alphastorm/ninfer#98`](https://github.com/alphastorm/ninfer/pull/98), head `d191fb57` / binary
  `88bd2265...`, live GPU proof at commit `5e73453f` / binary `5fd3bdec...`) that `Neroued/ninfer` `#446`/`#440`/`#441`
  `numerical_failure` (GPU `--nonfinite-only` exit `0`), managed `Stop` completed in **2.570988 s**
  (`2.571 s`, `saved: 1`, `refused: 0`, `18` cached tokens restored vs `e6ac7b70` failing with
  `managed final-save deadline exceeded`), `MTP3` parity (`6fe9fe7e`) matched **5/5** byte-identical,
  and CI passed; in **EXP-117** (slice `E3`,
  [`alphastorm/ninfer#96`](https://github.com/alphastorm/ninfer/pull/96), `6f1ae8d2`) that NFC
  boundary normalization sped up a `507,749`-byte non-ASCII document **11.06×** (`5.147875 → 0.465583
  ms`, `-13.93%` on ASCII control `0.065500 → 0.056375 ms`, `100,000` random `utf8proc` reference
  texts and **65/65 serialized results (`56` prompts + `9` expected errors)** / `564,922` token IDs
  byte-identical), while Jinja `.strip()` edge decode (`21d8b947`) and small-T module preload
  (`79d657e0`, `<= 0.668558 ms` vs `20 ms` gate) were skipped; and in **EXP-121** that on
  `rtx5090-win-a` both integrated `F` (`a3fa0550`, binary `1afbb82d...`,
  [`alphastorm/ninfer#99`](https://github.com/alphastorm/ninfer/pull/99): **3/3** `C1` gating and
  **3/3** informational `C2`) and council-remediated `F2` (`bdc665a3`, binary `92f0f636...`: **3/3**
  `C1` gating, runtime-source-identical to shipped source `F3` `e0971faf` in
  [`alphastorm/ninfer#101`](https://github.com/alphastorm/ninfer/pull/101), which fixed council
  `CR-20261110T083627Z-a3fa0550`'s confirmed severity-`P1` defect where a resident pause hitting a `Pending` durable
  pressure save caused `pause_reclaim_victim`/`reserve_resident_units` to fail the `Engine` with
  `progress owner cannot obtain its legal unit` and severity-`P2` defect where a failed fresh window did not consume
  its rotation in `take_fresh_window()`, passing `EngineCore` `35/35`, `1,311/1,311` Ninja steps, and
  all CI) matched production `a87de361` (`cc99a460`) byte-for-byte on `DFlash2` `C1`.
- **2026-11-11 upstream, community, client, and external-research deferrals and rejections for
  `v0.18.0` ([`docs/UPSTREAM.md#2026-11-11-upstream-and-fork-watch`](docs/UPSTREAM.md#2026-11-11-upstream-and-fork-watch)):**
  1. *Upstream warm-turn prefill split removal (`Neroued/ninfer` `77418cfec`) — deferred to a
     stretch branch and a later release:* removes the chat-template rewrite-execution prefill splits
     (`rewrite_execution_boundaries`/`frontiers`, `PrefixExecutionTracker`,
     `prefix_execution_split_after`, `InputWindow::execution_splits`) that caused four `2–3`-token
     fragment passes costing `59–60 ms` (`115–130 ms` estimated when folding six passes into two on
     a `307 ms` warm turn at `~25K`–`29K` context in
     [`EXP-059`](docs/PERFORMANCE.md#experiment-ledger), or `-0.06` to `-0.13 s` / `-23%` to `-49%`
     `[derived]` against recent RTX 5090 strict-warm TTFT p50 `0.265 s` at `474` computed tokens in
     [`EXP-110`](docs/PERFORMANCE.md#experiment-ledger); native-lane savings in ms are probably
     larger `[INFERENCE, unmeasured]` and the `EXP-059` trace predates `DFlash2` draft-context
     materialization `[INFERENCE]`), but is **deferred** because
     removing the separate `2`-token `<|im_start|>assistant\n<think>\n` pass
     (`qwen3_8.jinja:177-183`, `prompt_layout.cpp:91-104`) and historical assistant splits changes
     output tokens (`output-changing`, requiring the `EXP-085` 1,120-prompt powered screen per lane)
     and invalidates durable schema 3 session identity (`DurableIdentity` serializes
     `execution_frontiers` in `checkpoint_codec.cpp:25-26,174-178`, re-injects them in
     `checkpoint_api.cpp:153-154`, and mixes them into the shortlist digest in
     `durable_checkpoint_set.h:58-62` and `prefix_identity.cpp:114-117`, requiring a
     `kIdentityCodec` `qwen-identity/1` bump in `prefix_identity.h:18` that makes sessions saved
     under `v0.17.0` or `v0.8.0-beta.2` load as incompatible and run a cold first turn).
  2. *Upstream malformed tool-call history rejection (`Neroued/ninfer` `4461c9683`) — error behavior
     rejected, bad-argument test vectors adopted:* `4461c9683` turns malformed or non-object
     historical tool `arguments` into `invalid_argument` / HTTP `400`, which is **rejected** because
     a stock Oh My Pi coding-agent client replays its full stored conversation history every turn,
     so one malformed historical tool call would cause every later turn to fail with HTTP `400`
     (moving [`Neroued/ninfer#446`](https://github.com/Neroued/ninfer/issues/446) from HTTP `500` to
     HTTP `400`); `alphastorm/ninfer` retains `F3`'s non-throwing `{"input": raw}` wrapping
     (`src/text/tool_arguments.cpp:5-12`,
     `src/models/common/qwen/frontend/chat_template.cpp:263-265`,
     `tests/models/common/qwen/test_frontend.cpp:2222`) and ports `4461c9683`'s bad-argument vectors
     (`{"x": nope}`, truncated JSON, `[]`, `null`, `1e99999`) as lenient-rendering regression tests.
  3. *Other `Neroued/ninfer` `77c2e5e2..13ebb92f6` commits (`33` total) and `feat/qwen4-27b-ops`
     (`e1874e94`) — deferred or rejected:* pressure-path commits `e8059c32b` (input-replay capture
     admission/retention, subset stretch) and `41da21f47` (resident unit reservation and prefill
     fallback) are **deferred** because they target upstream's `session/*` / `ContextDirectory`
     architecture rather than `F3`'s council-remediated durable-save/export waits
     (`engine_core.h:1412-1437,2266-2390`, `capture.cpp:38-68,141-147`,
     `resource_manager.h:733-764`), neither fixes
     [`alphastorm/ninfer#89`](https://github.com/alphastorm/ninfer/issues/89) (`0` resident
     requests, `2,032/2,048` KV page groups, `4/4` device state slots, `390 MiB` Host free) or
     [`alphastorm/ninfer#102`](https://github.com/alphastorm/ninfer/issues/102)
     (resident-reservation `DemoteOperation` holding the context-operation slot `[INFERENCE]`;
     whether `e8059c32b` reduces optional demotions is unproven `[INFERENCE]`), and neither defect
     appeared in `180/180` recent completions (`0` preemptions, `0` `paused_ns`); the Jinja chain
     (`52e7cd7e0`, `13ebb92f6`, and the `third_party/llama-jinja` hunks of `77418cfec`) is
     **deferred** because host rendering is `~1.16 ms` per `500K`-character render (`<= 1 ms` gain)
     and edge semantics change; `feat/qwen4-27b-ops` (`e1874e94`, unchanged since `2026-10-29`)
     remains **deferred** on watch without public `Qwen4-27B` weights or upstream model/converter
     support; and `9eff5314f` (`ninfer_bench`), `41da21f47`'s nullable-TTFT log change, and the
     remaining `26` Spark/distributed/`glm5next`/MoE commits (including `ad49b325d`, `6a753af33`,
     `b5008303b`, `dc4e789b2`, `d5d535956` `DFlash2` draft-op generalizations and `e871c41b1`,
     `12d5b72ab`, `4ac06e5ad`, `b5008303b` `BF16` sliced-K partial-reduction changes) are
     **rejected** because they do not help hidden-size-5,120 (`H5120`) on `sm_120`/`sm_89`/`sm_86`
     and risk `DFlash2` token identity.
  4. *Community fork candidates (`iamwavecut/ninfer-all` `8412e774..64bd1115` and
     `ashalliants/ninfer-3090` `2026-11-10`/`2026-11-11` branches) — deferred or rejected:* across
     `28` `iamwavecut/ninfer-all` commits (`0` with a dense-`Qwen3.8-27B` speed number), stop-string
     state holds (`52dfc488`, `9fbb8098`, `#307` `857d172`), in-pass prefix-cache taps (`458d8fb8`,
     `#308` `4d6327d`), and `bf16p` packed `BF16` KV rows (`cc65dbb3`, `#316` `6e71b0ed`, `392 B`
     vs `512 B` / `23%` fewer bytes, poison row decoding to `NaN` above six exponent escapes) are
     **deferred** because `F3` lacks their subsystems (`CommitDecision` hold/rewind in
     `execution.h:49-53` and whether OMP sends stop strings is unverified; `hybrid_program` /
     `tap_planner` absent in `F3`, which captures via `split_frontier` at
     `prefill.cpp:80-83,618-622`; packed `KvCacheStorage` absent in `include/ninfer/types.h:29-34`),
     while the remaining `21` lookup/multi-GPU/build/MoE/A6000 commits are **rejected** as
     inapplicable. On `ashalliants/ninfer-3090`, adaptive `DFlash2` `K=3`/`K=7` drafting
     (`perf/adaptive-dflash-k` `4ff617181` / `5dd329830` / `c385455b`, `58.9 / 53.2 / 46.1 tok/s` at
     `K=3/7/12` on a single-lane RTX 3090 low-acceptance workload, `"Nothing here has run on a GPU"`
     in `TODO.md` `[INFERENCE]`), `--relaxed-drafting` (`cd596378c`), and `--draft-context-rows`
     (`b654456b7` on `feat/basalt-learnings` `5ccab0c5c`, `docs/serving.md` figures unverified in
     the log-only bundle) are **rejected / deferred** for `v0.18.0` because low-acceptance decode is
     `<= 0.6%` of decode (`EXP-110`), `F3` has no `SpeculativeRoundShape` round-family machinery, a
     second CUDA-graph family costs VRAM, verify-width and relaxed-drafting changes alter outputs,
     and `--draft-context-rows` is refused above one lane; `feat/sensitivity-allocation`
     (`66e31f3b6`) is **deferred** as unvalidated (`"not yet measured with KLD or on a GPU"`) and
     requiring artifact re-quantization.
  5. *Client compaction workarounds, model watch, external techniques, and fork backlog — deferred
     or rejected:* RTX 3090 profile workarounds (`compaction.asyncEnabled: false`, local-first
     `compaction.methodOrder`, or a `~60K` `thresholdTokens` cap;
     `packages/agent/src/compaction/compaction.ts:328-330,379-381,394-421,1095-1155`,
     `speculation-lead.ts:1-24`) are **rejected / deferred** because they mask the
     [`alphastorm/ninfer#89`](https://github.com/alphastorm/ninfer/issues/89) Host-arena state-image
     export deadlock (`~196 MB` state images, fixed in `v0.18.0` by device-staged state-image export
     fallback) and `scripts/hosts/accept-rtx4090-route.ps1:356-359` forbids disabling async
     compaction to pass the gate (while stock OMP
     [`v18.18.7`](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.7)
     `e325ffc73ab86e03bdd20a91b77d8e2b3964c906` is adopted for `v0.18.0` by founder decision).
     Same-architecture 27B derivatives (`NousResearch/Arete-27B`, whose
     `DAXZEIT/Arete-27B-NInfer-v3` conversion uses unloadable GGUF blocks, and
     `ConceptCountry/qwen-concept-27b`) and external `DFlash` drafters
     (`nchapman/Qwen3.8-27B-DFlash2-W4A16-HGPTQ`, `amd/Qwen3.8-27B-Quark-DFlash2`,
     `StillDeadcode/qwen3.8-27b-iq8r-dflash`) are **deferred**, closing the `v0.18.0` model watch.
     While `v0.18.0` gates RTX 5090 cadence-only pacing (`0 / 32` via `--prefill-stall-budget-ms 0`
     and `--decode-rounds-per-prefill 32`), RTX 5090 and RTX 3090 `Group64` A8 prefill, and RTX
     3090/4090 tensor-core verify on preregistered bars (keeping RTX 4090 A8 off at its
     `1.0985 / 1.10` leak bound) and runs `rk4v4` cheap deciders (`~31` GPU-hours for full
     qualification on the single native host), tool-call-span copy-drafting replay,
     restore-preparation instrumentation
     ([`alphastorm/ninfer#59`](https://github.com/alphastorm/ninfer/issues/59)) / readiness
     attribution, byte-identical `pad16` / 2-stage native verify schedules (`~1–3%`), and RTX 3090
     locked-clocks screening in idle stretch slots, it **defers or rejects** 8-column token-tree
     verification (Medusa and EAGLE-2/3 use `32–64` verify nodes and EAGLE-3 `arXiv:2503.01840`
     abstract-level claims report `3.0–6.5×` with mean accepted length `7.5`, not verified for 8
     columns), typical acceptance (Medusa `arXiv:2401.10774`, gain unknown for an 8-column block
     drafter and inactive at temperature `0`), KIVI asymmetric KV (`arXiv:2402.02750`),
     CUDA-graph/launch-overhead reduction (`<= 1%` of a `17.7 ms` round, `EXP-054`/`EXP-058`),
     `cuBLAS` `INT8` prefill, the
     [`alphastorm/ninfer#50`](https://github.com/alphastorm/ninfer/issues/50) hold state machine
     ([`alphastorm/ninfer#66`](https://github.com/alphastorm/ninfer/pull/66) closed),
     [`alphastorm/ninfer#72`](https://github.com/alphastorm/ninfer/pull/72) (closed, no consumer
     since `#58` was dropped), RTX 3090 prefill pacing (no config key or baseline),
     [`alphastorm/omp-ninfer#28`](https://github.com/alphastorm/omp-ninfer/issues/28) (closed as not
     planned), and RTX 5080.

## Path to v1.0

A public release does not imply a v1.0 or SLA commitment. v1.0 means the durability contract —
save is atomic and verified, restore is verified-or-refused, sessions survive process death, and
private state never crosses sessions — holds under independent eyes, not just owner receipts.
Before a v1.0 decision:

- gather clean-install, recovery, and (where supported by the topology) rollback evidence from
  multiple independent owners for each claimed GPU profile;
- sign the first-party Windows runtime packages or retain the explicit unsigned and stock-client
  provenance boundary;
- close the highest-signal public-release installation and compatibility failures;
- publish supported upgrade and security-fix windows, rollback ownership, and response-time
  expectations without implying an SLA;
- run the fixed multi-machine workload before making any fleet completed-work claim; and
- cut a new release candidate if any executable component, model, configuration, or support
  boundary changes.

Explicitly not on this path (a new product decision, not a milestone): multi-tenant serving,
priority or preemptive scheduling, universal hardware claims, and silent cloud fallback.

## Shipped

Every release keeps its immutable manifest, qualification receipts, and release notes; full
per-version history lives in [`CHANGELOG.md`](CHANGELOG.md) and [`docs/RELEASES.md`](docs/RELEASES.md).

| Release | Date | Summary | Notes |
| --- | --- | --- | --- |
| `v0.17.0` | 2026-11-10 | Rebuild RTX 5090 container to `v0.7.0-qwen38-5090-beta.6` from release source F3 `e0971faf` on `64d10fbf` ([fork PR #101](https://github.com/alphastorm/ninfer/pull/101), image `7a19576b`, server `dc86e101`, 181.92 tok/s decode, 56.63 s cold retrieval, isolated host checkpoint directory `checkpoints-v017`, bit-identical 664-artifact / 3-package double build, 12/12 RC phases) with bounded resume/fresh admission ([#434](https://github.com/Neroued/ninfer/issues/434)), durable pressure-work waits, serving robustness ([#440](https://github.com/Neroued/ninfer/issues/440)/[#441](https://github.com/Neroued/ninfer/issues/441)/[#446](https://github.com/Neroued/ninfer/issues/446)), and host-side NFC/frontend rendering; carry native RTX 4090 and RTX 3090 `v0.8.0-qwen38-{4090,3090}-beta.2` unchanged at `a87de361`; and advance to stock OMP 18.18.6 (`9058ab9d`, release `439766193`, `tokenizer: qwen3` on opaque `q38-ninfer`, explicit update/setup-wizard opt-outs) across all five documented routes (`31/31` blocks, 408.213 s RTX 5090 hold, passing RTX 4090 campaign/public install/restoration; RTX 3090 post-route `native-probes` compaction campaign failed and founder-waived with disclosure and lead recovery; superseding `v0.16.2`) | [notes](releases/v0.17.0/NINFER_RELEASE_NOTES.md) |
| `v0.16.2` | 2026-11-04 | Rebuild all three GPU lanes at common engine source `a87de361` on `64d10fbf` — RTX 5090 `v0.7.0-qwen38-5090-beta.5` (`a0cbb8a5`, server `cc99a460`, 182.02 tok/s decode, 56.49 s cold retrieval, bit-identical 661-artifact / 3-package double build), native RTX 4090 `v0.8.0-qwen38-4090-beta.2` (`d9b10b47`, server `ffee91bf`, 254.59 tok/s C1 decode, 83.54 s retrieval), and native RTX 3090 `v0.8.0-qwen38-3090-beta.2` (`97a8e634`, server `15a4db46`, 148.70 tok/s C1 decode, 188.94 s retrieval) — with byte-proven durable-generation Host reclaim ([fork #78](https://github.com/alphastorm/ninfer/issues/78)), export-retirement reservation ([#68](https://github.com/alphastorm/ninfer/pull/68)), opt-in FP32 head identity alignment ([#67](https://github.com/alphastorm/ninfer/pull/67)), native repair/power/gate-driver fixes ([#63](https://github.com/alphastorm/ninfer/pull/63), [#65](https://github.com/alphastorm/ninfer/pull/65), [#70](https://github.com/alphastorm/ninfer/pull/70), [#73](https://github.com/alphastorm/ninfer/pull/73), [#79](https://github.com/alphastorm/ninfer/pull/79), [#80](https://github.com/alphastorm/ninfer/pull/80)), zero-difference 1,120-prompt quality screens, no-regression speed gates vs `beta.1` (`1.0003` / `0.9988` on RTX 3090; `0.9996` / `0.9989` on RTX 4090), three exact founder parity waivers, and stock OMP 18.15.0 (`3fedf8d5`, release `430630500`) across all five documented routes (`31/31` blocks; RTX 3090 post-route native campaign failed at structured-outage managed Stop under founder waiver with empty-session `Start`/`Stop` recovery; superseding `v0.16.0` while held `v0.16.1` stays unpublished) | [notes](releases/v0.16.2/NINFER_RELEASE_NOTES.md) |
| `v0.16.0` | 2026-11-01 | Ship native `DFlash2 K=7` on RTX 3090 (`v0.8.0-qwen38-3090-beta.1`, `C2` over one shared 131,072-token INT8 pool, 180 s timeout, `ninfer-native-3090: 2`, 350 W cap, 148.43 tok/s C1 decode, EXP-101, EXP-106) and RTX 4090 (`v0.8.0-qwen38-4090-beta.1`, `C1`, 1,024 prefill chunk, 254.27 tok/s C1 decode, EXP-102, EXP-104) and rebuild RTX 5090 (`v0.7.0-qwen38-5090-beta.4`, image `7a5a7bb8`, server `bab3fd77`) from common engine source `26fa28d0` on `64d10fbf` with Host export-State residency (`EXP-105`), `io_uring` lifetime fixes, running-lane installer handoff, and stock OMP 18.14.0 (`31147f9d`); close [#94](https://github.com/alphastorm/omp-ninfer/issues/94)–[#96](https://github.com/alphastorm/omp-ninfer/issues/96), [#116](https://github.com/alphastorm/omp-ninfer/issues/116), [#117](https://github.com/alphastorm/omp-ninfer/issues/117) (superseding `v0.15.1`) | [notes](releases/v0.16.0/NINFER_RELEASE_NOTES.md) |
| `v0.15.0` | 2026-10-30 | Repin stock OMP 18.14.0 (`31147f9d`, Bun 1.4.4 rebuild for CVE-2026-91403 and CVE-2026-111497; `qwen3.8-27b` replace-edit default) across all five documented routes (31 blocks) with unchanged v0.14.0 beta.3 GPU runtimes, shared model v3 (`81f924d4`), and serving profiles; ship native screen-arm capture (`scripts/native_screen_arm.py`), quality/fit/parity binding (`scripts/bind_native_variant.py`, `scripts/verify_release.py`), WSL2 client route, and idempotent guide reruns; defer native RTX 3090 DFlash2 to v0.15.1 ([#116](https://github.com/alphastorm/omp-ninfer/issues/116), [#117](https://github.com/alphastorm/omp-ninfer/issues/117)) | [notes](releases/v0.15.0/NINFER_RELEASE_NOTES.md) |
| `v0.14.0` | 2026-10-28 | Bind common engine source `2c6f423b` on upstream master `64d10fbf` across RTX 5090 (`v0.7.0-qwen38-5090-beta.3`), native RTX 4090 (`v0.7.0-qwen38-4090-beta.3`), and native RTX 3090 (`v0.7.0-qwen38-3090-beta.3`, 350 W cap, stop-before-upgrade [#94](https://github.com/alphastorm/omp-ninfer/issues/94), `Group64` A8 off) with shared model v3 (`81f924d4`) and stock OMP 18.12.6 re-accepted across all five routes (31 blocks) | [notes](releases/v0.14.0/NINFER_RELEASE_NOTES.md) |
| `v0.13.1` | 2026-10-26 | Rebase native Windows RTX 4090 (`v0.7.0-qwen38-4090-beta.2`) and RTX 3090 (`v0.7.0-qwen38-3090-beta.2`) onto upstream master `64d10fbf` (source `7a25cd72`) with shared model v3 (`81f924d4`), strict-origin schema 3 checkpoints (`session-checkpoints-v3`), shared Host budgets (640 / 768 MiB admission headroom), JSON-schema output, 128-character tool names, and CycloneDX dependency SBOMs; carry RTX 5090 `v0.7.0-qwen38-5090-beta.2` and stock OMP 18.12.6 re-accepted across all five routes | [notes](releases/v0.13.1/NINFER_RELEASE_NOTES.md) |
| `v0.13.0` | 2026-10-25 | Rebase RTX 5090 container (`v0.7.0-qwen38-5090-beta.2`, source `6d4d0a05`) onto upstream master `64d10fbf` with model v3 (`81f924d4`), schema 3 checkpoints (`checkpoints-v013`, strict origin auth, non-blocking export), JSON-schema output, 128-character tool names, and stock OMP 18.12.6; carry native RTX 4090 and RTX 3090 packages re-accepted with OMP 18.12.6 | [notes](releases/v0.13.0/NINFER_RELEASE_NOTES.md) |
| `v0.12.2` | 2026-10-18 | Repin stock OMP 18.12.1 (native Windows `C:` path fix, two `omp -p` exit-status fixes) across all five documented routes (31 blocks) with unchanged GPU runtimes, models, and profiles | [notes](releases/v0.12.2/NINFER_RELEASE_NOTES.md) |
| `v0.12.1` | 2026-10-12 | Repin stock OMP 18.10.1 across all five documented routes (31 blocks) with unchanged GPU runtimes, models, and profiles | [notes](releases/v0.12.1/NINFER_RELEASE_NOTES.md) |
| `v0.12.0` | 2026-10-11 | Restore native Windows RTX 4090 (`v0.6.11`) and RTX 3090 (`v0.6.3`) UUID-bound on one two-GPU host (one active lane on port 18082) | [notes](releases/v0.12.0/NINFER_RELEASE_NOTES.md) |
| `v0.11.0` | 2026-10-10 | Ship RTX 5090 `v0.6.16` (`1302d639`, EXP-092/EXP-094 DFlash2 round-cost reductions) and stock OMP 18.8.7 with per-model stateful Responses | [notes](releases/v0.11.0/NINFER_RELEASE_NOTES.md) |
| `v0.10.0` | 2026-10-02 | Adopt DFlash2 draft window 7 with BF16 KV (`v0.6.15`, model `0634abb0`) on RTX 5090 and repin all clients to stock OMP 18.4.10 | [notes](releases/v0.10.0/NINFER_RELEASE_NOTES.md) |
| `v0.9.1` | 2026-10-01 | Add RTX 3090 native Windows lane (`v0.6.2`, 300 W cap, one request in flight) on the mainline runtime; accept all five routes | [notes](releases/v0.9.1/NINFER_RELEASE_NOTES.md) |
| `v0.9.0` | 2026-09-30 | Qualify two requests in flight on RTX 5090 (`v0.6.14`, Q5 tensor-core 8-token MTP3 verify) with provider in-flight limits (EXP-077) | [notes](releases/v0.9.0/NINFER_RELEASE_NOTES.md) |
| `v0.8.7` | 2026-09-29 | Keep long-session prefix cache across compaction handoffs, near-capacity turns, and checkpoint-quota pressure on RTX 5090 and RTX 4090 (EXP-074) | [notes](releases/v0.8.7/NINFER_RELEASE_NOTES.md) |
| `v0.8.6` | 2026-09-28 | Compact long sessions inline (`compaction.asyncEnabled: false`) and harden documented nonce recall planting on stock OMP 18.4.0 (EXP-072, EXP-073) | [notes](releases/v0.8.6/NINFER_RELEASE_NOTES.md) |
| `v0.8.5` | 2026-09-28 | Repin to stock OMP 18.4.0 for Windows completion status and set `supportsImageDetailOriginal: false` on RTX 5090 (EXP-070, EXP-071) | [notes](releases/v0.8.5/NINFER_RELEASE_NOTES.md) |
| `v0.8.4` | 2026-09-28 | Ship `sm_89` 50 ms/100 ms GPU keep-warm on RTX 4090 (`v0.6.9`) and advance clients to stock OMP 18.3.5 (EXP-064, EXP-066) | [notes](releases/v0.8.4/NINFER_RELEASE_NOTES.md) |
| `v0.8.3` | 2026-09-27 | Speed up RTX 5090 decode with `sm_120` small-T tensor-core Q5 verify projections (`v0.6.12`) after 504-pair redaction screen (EXP-057, EXP-063) | [notes](releases/v0.8.3/NINFER_RELEASE_NOTES.md) |
| `v0.8.2` | 2026-09-26 | Add 60 s single-warp GPU keep-warm (`--gpu-keep-warm-ms 60000`) on RTX 5090 (`v0.6.11`) for idle agent arrivals (EXP-062) | [notes](releases/v0.8.2/NINFER_RELEASE_NOTES.md) |
| `v0.8.1` | 2026-09-25 | Speed up MTP3 verify decode on RTX 5090 (`v0.6.10`) and RTX 4090 (`v0.6.8`) with shared activation loads (EXP-055) | [notes](releases/v0.8.1/NINFER_RELEASE_NOTES.md) |
| `v0.8.0` | 2026-09-25 | Switch to unmodified upstream OMP 18.3.0 binaries with `prompt_cache_key` durable session routing (EXP-053) | [notes](releases/v0.8.0/NINFER_RELEASE_NOTES.md) |
| `v0.7.4` | 2026-09-24 | Retry transient automatic checkpoint refusals, save before eviction, and protect sibling checkpoints under quota (EXP-049..051) | [notes](releases/v0.7.4/NINFER_RELEASE_NOTES.md) |
| `v0.7.3` | 2026-09-18 | Repin client to `omp-18.2.3-cross-platform-beta-1` across macOS, Windows, and Linux with unchanged v0.7.2 runtimes (EXP-046) | [notes](releases/v0.7.3/NINFER_RELEASE_NOTES.md) |
| `v0.7.2` | 2026-09-17 | Reclaim checkpoint-backed resident sessions under host-KV pressure during restore on RTX 5090 and RTX 4090 (EXP-047) | [notes](releases/v0.7.2/NINFER_RELEASE_NOTES.md) |
| `v0.7.1` | 2026-09-16 | Raise RTX 4090 host-KV pool to 11,264 MiB so ceiling-sized checkpoints restore, and refuse unrestorable exports (EXP-043, EXP-044) | [notes](releases/v0.7.1/NINFER_RELEASE_NOTES.md) |
| `v0.7.0` | 2026-09-16 | Double RTX 5090 host-KV pool to 16 GiB (28 GiB host floor) so two alternating 131,072-token sessions keep prefix reuse (EXP-041) | [notes](releases/v0.7.0/NINFER_RELEASE_NOTES.md) |
| `v0.6.10` | 2026-09-16 | Refuse RTX 5090 container launch when bind mounts fail throwaway staging preflight and document reboot recovery (EXP-040) | [notes](releases/v0.6.10/NINFER_RELEASE_NOTES.md) |
| `v0.6.9` | 2026-09-13 | Port upstream Qwen tool-parser semantics and deep-union bounds onto shared source `696e78c7` for RTX 5090 and RTX 4090 | [notes](releases/v0.6.9/NINFER_RELEASE_NOTES.md) |
| `v0.6.8` | 2026-09-13 | Unify RTX 5090 and RTX 4090 on source `68a0722f` and fix HTTP 500 on live-sibling fork continuation (EXP-036, EXP-037) | [notes](releases/v0.6.8/NINFER_RELEASE_NOTES.md) |
| `v0.6.7` | 2026-09-13 | Backport 18 upstream NInfer engine commits into RTX 5090 runtime `v0.6.3` within noise of v0.6.2 (EXP-035) | [notes](releases/v0.6.7/NINFER_RELEASE_NOTES.md) |
| `v0.6.6` | 2026-09-12 | Disable out-of-channel client startup update checks in the documented route configuration | [notes](releases/v0.6.6/NINFER_RELEASE_NOTES.md) |
| `v0.6.5` | 2026-09-12 | Run the primary macOS-to-Windows container quickstart route verbatim from its documented fenced blocks (EXP-033) | [notes](releases/v0.6.5/NINFER_RELEASE_NOTES.md) |
| `v0.6.4` | 2026-09-11 | Run all documented Windows quickstart routes verbatim from their fenced blocks and enforce LF line endings (EXP-032) | [notes](releases/v0.6.4/NINFER_RELEASE_NOTES.md) |
| `v0.6.3` | 2026-09-11 | Mount a persistent session checkpoint directory on the documented public RTX 5090 container route (EXP-031) | [notes](releases/v0.6.3/NINFER_RELEASE_NOTES.md) |
| `v0.6.2` | 2026-09-11 | Move the RTX 5090 container lane onto mainline runtime commit `63f28c95` alongside the native Windows lanes (EXP-030) | [notes](releases/v0.6.2/NINFER_RELEASE_NOTES.md) |
| `v0.6.1` | 2026-09-10 | Flush and checkpoint every live session on graceful Windows managed stop on the RTX 4090 native lane (EXP-028, EXP-029) | [notes](releases/v0.6.1/NINFER_RELEASE_NOTES.md) |
| `v0.6.0` | 2026-09-10 | Port the RTX 4090 native Windows lane onto the mainline context-cache runtime (`075d442e`, EXP-025..027) | [notes](releases/v0.6.0/NINFER_RELEASE_NOTES.md) |
| `v0.5.1` | 2026-09-08 | Preserve shared-anchor sibling fanout across restarts (warm arrival) and overlap SHA-256 restore streaming on RTX 5090 (EXP-022..024) | [notes](releases/v0.5.1/NINFER_RELEASE_NOTES.md) |
| `v0.5.0` | 2026-09-05 | Ship origin-authenticated checkpoint manifests on all three lanes and verified off-machine replication (`scripts/checkpoint_sync.py`, EXP-018) | [notes](releases/v0.5.0/NINFER_RELEASE_NOTES.md) |
| `v0.4.9` | 2026-09-05 | Replace per-segment DirectStorage reads with windowed staging on RTX 4090 and RTX 3090, cutting restore to seconds (EXP-017) | [notes](releases/v0.4.9/NINFER_RELEASE_NOTES.md) |
| `v0.4.8` | 2026-09-05 | Requalify per-lane configurations: RTX 5090 4-slot fanout anchor catalog, RTX 4090 2,048-token chunk, RTX 3090 131,072-token context | [notes](releases/v0.4.8/NINFER_RELEASE_NOTES.md) |
| `v0.4.7` | 2026-09-01 | Correct immutable runtime asset URLs in the v0.4.6 manifest with unchanged component bytes | [notes](releases/v0.4.7/NINFER_RELEASE_NOTES.md) |
| `v0.4.6` | 2026-08-31 | Add HMAC checkpoint-origin authentication on the RTX 5090 container lane (`ninfer#32`) | [notes](releases/v0.4.6/NINFER_RELEASE_NOTES.md) |
| `v0.4.5` | 2026-08-31 | Bring the RTX 3090 native Windows lane onto the v0.2 durable checkpoint and fanout train | [notes](releases/v0.4.5/NINFER_RELEASE_NOTES.md) |
| `v0.4.4` | 2026-08-31 | Decouple RTX 5090 checkpoint export from the engine lock with bounded buffered writes and sustained-idle debounce | [notes](releases/v0.4.4/NINFER_RELEASE_NOTES.md) |
| `v0.4.3` | 2026-08-31 | Add shared-page sibling fanout anchors, streamed checkpoint-import hash verification, and session isolation hardening on RTX 5090 | [notes](releases/v0.4.3/NINFER_RELEASE_NOTES.md) |
| `v0.4.2` | 2026-08-31 | Move the RTX 4090 native Windows lane to the durable v0.2 runtime with 102,075-token checkpoint restore | [notes](releases/v0.4.2/NINFER_RELEASE_NOTES.md) |
| `v0.4.1` | 2026-08-31 | Harden RTX 5090 checkpoint store with health-gated quota transitions and post-publish reclamation | [notes](releases/v0.4.1/NINFER_RELEASE_NOTES.md) |
| `v0.4.0` | 2026-08-30 | Ship transactional session checkpoints on the RTX 5090 container lane (109,589 retained tokens restored across a Docker restart) | [notes](releases/v0.4.0/NINFER_RELEASE_NOTES.md) |
| `v0.3.2` | 2026-08-30 | Correct template residue in the v0.3.1 RTX 4090 qualification summary with unchanged component bytes | [notes](releases/v0.3.2/NINFER_RELEASE_NOTES.md) |
| `v0.3.1` | 2026-08-30 | Promote the MTP3 speculative decoding package on the RTX 4090 native Windows lane (+17.04% Golden-equivalent wall time) | [notes](releases/v0.3.1/NINFER_RELEASE_NOTES.md) |
| `v0.3.0` | 2026-08-30 | First public GitHub `Latest` release across the RTX 5090, RTX 4090, and RTX 3090 lanes | [notes](releases/v0.3.0/NINFER_RELEASE_NOTES.md) |
| `v0.2.0-beta.1` | 2026-08-29 | Add native Windows RTX 4090 beta and RTX 3090 preview lanes, durable native checkpoints, and cross-platform OMP 18.0.9 fork archives | [notes](releases/v0.2.0-beta.1/NINFER_RELEASE_NOTES.md) |
| `v0.1.0-beta.1` | 2026-08-28 | Initial restricted RTX 5090 beta with exact manifest pinning and clean install from public URLs | [notes](releases/v0.1.0-beta.1/NINFER_RELEASE_NOTES.md) |

## How to help

- **Run OMP with subagents against a lane?** That fanout path is what shared-anchor continuation
  serves — file a
  [hardware report](https://github.com/alphastorm/omp-ninfer/issues/new?template=hardware-report.yml)
  with what you observe, pass or fail.
- **Measured something?** Submit the
  [performance result form](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml)
  for the [community results table](docs/BENCHMARKS.md#community-results).
- **CUDA or kernel work?** Claim an idea from the
  [performance backlog](docs/PERFORMANCE.md#ideas-backlog) and see
  [`CONTRIBUTING.md`](CONTRIBUTING.md).
- **RTX 3090, RTX 4090, or RTX 5090 owner?**
  [Get started](docs/QUICKSTART.md) with the matching published lane, then file a content-safe
  [hardware report](https://github.com/alphastorm/omp-ninfer/issues/new?template=hardware-report.yml)
  or [clean-install report](https://github.com/alphastorm/omp-ninfer/issues/new?template=clean-install-report.yml).
  Pass and fail reports both improve the observed matrix; one lane never authorizes package
  substitution in another.
