# Roadmap

This roadmap is a scope boundary, not a promise of dates. Oh My Pi (coding-agent client) connects
through OMP NInfer (qualified appliance and release layer) to NInfer (inference engine) serving
Qwen3.8 27B (served model) on user-owned NVIDIA GPUs. Qualified on RTX 5090 · 4090 · 3090, each
release lane is bound to exact bytes and a qualification receipt. Work outside that wedge requires a
new product decision rather than placeholder abstractions, and no kernel, model, or configuration
change becomes part of a release until its exact binary and profile are rebound through a new
qualification receipt.

Standing support boundaries for the 0.x series: owner-operated exact profiles with no SLA or upgrade
commitment; two requests in flight on the RTX 5090 container lane and one active request on each
native Windows lane (RTX 4090 and RTX 3090, running one lane at a time on port 18082); enforced
JSON-schema structured output and 128-character tool names qualified across all three lanes while
vision and DFlash2 remain RTX 5090 container-only; the unattended RTX 3090 fleet scout role disabled;
no cloud hosting, multi-GPU inference, multi-tenant serving, priority or preemptive scheduling,
automatic container restart, or silent cloud fallback; and no support or performance claim outside
the exact recorded package, machine, and profile. Community project; not affiliated with or endorsed
by Oh My Pi, Qwen, or NVIDIA.

## Current release

**v0.15.0** (published 2026-10-30, GitHub `Latest`) pins unmodified upstream Oh My Pi **18.14.0**
(`31147f9d`, tree `9a63b5bf`, upstream binaries rebuilt with Bun 1.4.4 for CVE-2026-91403 and
CVE-2026-111497; `qwen3.8-27b` on native RTX 4090 defaults to stock `replace` edit-tool mode while
`q38-ninfer` on RTX 5090 and native RTX 3090 keeps `hashline`) across macOS arm64 (preview), Windows
x64, and Linux x64 (WSL2), while retaining the qualified `v0.14.0` GPU runtime packages, shared
published model container version 3 `81f924d4` (`qwen3_8_27b-v3.ninfer`, 20,437,521,664 bytes), and
serving profiles unchanged from `v0.14.0` (built from common engine source `2c6f423b`,
`2c6f423bd817b6534158553e1b34ab4959c43165`, on upstream `Neroued/ninfer` master `64d10fbf`) across
all three qualified GPU lanes:

- **RTX 5090 container (`v0.7.0-qwen38-5090-beta.3`, source `2c6f423b` on `64d10fbf`, image
  `760fb6be` on base `d4377ed0`, server `55f0b95a`, model `81f924d4`):** Windows 11 + Docker
  Desktop/WSL2 on loopback `127.0.0.1:18089`, profile `qwen38-5090-v0.13.0` (`751d22dc`), BF16 KV
  (146,368 automatic tokens), 131,072-token context, two requests in flight plus two extra
  device-state slots, DFlash2 draft window 7, schema 3 checkpoint store (`checkpoints-v013` with
  mandatory `--session-checkpoint-require-origin-auth` and non-blocking export), JSON-schema
  structured output, 128-character tool names, vision + tools + preserved thinking. Checked
  first-build bytes ship under an explicit founder-approved 5090-only reproducibility exception.
- **RTX 4090 (`v0.7.0-qwen38-4090-beta.3`) and RTX 3090 (`v0.7.0-qwen38-3090-beta.3`) native
  Windows (source `2c6f423b` on `64d10fbf`, model `81f924d4`):** loopback `127.0.0.1:18082`, INT8
  KV, `Group64` A8 compiled off, 131,072-token context, MTP3 (`--lm-head-draft`), one request at a
  time, JSON-schema structured output, 128-character tool names, text + tools, mandatory
  `--session-checkpoint-require-origin-auth`, release-isolated schema 3 checkpoint stores
  (`cache/<release-instance-id>/session-checkpoints-v3`, where `<release-instance-id>` is the
  installed release ID such as `qwen38-4090-native-v0.7.0-beta.3-2c6f423bd817`), and dual SPDX +
  CycloneDX 1.5 dependency SBOMs (14,787.734375 MiB / 15,506,063,360-byte shared Host budget, 640
  MiB admission headroom, and two extra device-state slots on RTX 4090; 11,715.734375 MiB /
  12,284,837,888-byte shared Host budget, 768 MiB admission headroom, four extra device-state slots,
  and 350 W serving cap on RTX 3090; stop a running v0.13.1 RTX 3090 lane before upgrading to
  v0.14.0 or v0.15.0 because its 300 W GPU-owner lease fails the new 350 W cap check before replacement,
  [#94](https://github.com/alphastorm/omp-ninfer/issues/94)). Both install on one two-GPU host bound
  by GPU UUID and run one lane at a time; both lineages record no supported rollback target
  (`not_applicable`, zero rollback directions; prior native roots stay preserved separately for
  historical recovery).

Stock OMP has no `omp appliance` lifecycle commands; container and native host scripts own runtime
lifecycle, and source-first native qualification is an established release procedure
([`docs/RELEASES.md#next-native-release-sequencing`](docs/RELEASES.md#next-native-release-sequencing)).
Full release authority: [`releases/v0.15.0/NINFER_RELEASE_NOTES.md`](releases/v0.15.0/NINFER_RELEASE_NOTES.md) ·
[`releases/v0.15.0/manifest.json`](releases/v0.15.0/manifest.json) ·
[`releases/v0.15.0/qualification.json`](releases/v0.15.0/qualification.json) ·
[`docs/RELEASES.md`](docs/RELEASES.md) · [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md).

## Remaining work

Items below remain open after `v0.15.0`; each names the current evidence showing the gap is still
unmet:

1. **Independent multi-owner clean-install, recovery, and rollback evidence.** All qualifications
   and 31-block documented-route acceptances through `v0.15.0` are maintainer-operated on owner
   hardware, and both native Windows lanes (`v0.7.0-qwen38-4090-beta.3` and
   `v0.7.0-qwen38-3090-beta.3`) have no supported rollback target (`not_applicable`, zero
   directions) on the two-GPU Windows host
   ([`releases/v0.15.0/qualification.json`](releases/v0.15.0/qualification.json),
   [`releases/v0.15.0/qualification/rtx4090.json`](releases/v0.15.0/qualification/rtx4090.json),
   [`releases/v0.15.0/qualification/rtx3090.json`](releases/v0.15.0/qualification/rtx3090.json),
   [`releases/v0.15.0/NINFER_RELEASE_NOTES.md`](releases/v0.15.0/NINFER_RELEASE_NOTES.md)).
2. **macOS managed lifecycle and native Linux OS qualification.** The macOS arm64 route remains a
   manual SSH tunnel preview without managed client installation or appliance lifecycle (`scripts/mac_tunnel.py`
   supervises only the local SSH forward), and the Linux x64 client is evidenced only under WSL2 on
   the Windows 11 container host rather than a native Linux OS
   ([`releases/v0.15.0/qualification.json`](releases/v0.15.0/qualification.json),
   [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md)).
3. **Hardware-independent public route qualification.** [`scripts/client_acceptance.py`](scripts/client_acceptance.py)
   and [`scripts/doctor.py`](scripts/doctor.py) provide host-free client rehearsals, live owner-lane
   checks, and named-cause WSL/Docker/loopback preflight, while full 31-block documented-route
   release qualification still requires live maintainer GPU-host windows
   ([`releases/v0.15.0/acceptance/documented-routes.json`](releases/v0.15.0/acceptance/documented-routes.json)).
   The earlier route-lifecycle tracker [#15](https://github.com/alphastorm/omp-ninfer/issues/15) is
   closed; it is historical context, not an open tracker for these additions.
4. **Distribution signing and notarization.**
   [`scripts/generate_native_sbom.py`](scripts/generate_native_sbom.py) generates CycloneDX 1.5
   dependency SBOMs and the verifier supports `sbom_dependency_url` / `sbom_dependency_sha256`,
   and both published beta.3 native components in
   [`releases/v0.15.0/manifest.json`](releases/v0.15.0/manifest.json) bind separate dependency
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
   disabled ([`releases/v0.15.0/NINFER_RELEASE_NOTES.md`](releases/v0.15.0/NINFER_RELEASE_NOTES.md)),
   and any fleet completed-work claim requires re-running the fixed multi-machine workload
   ([`scripts/fleet_dispatch.py`](scripts/fleet_dispatch.py), EXP-016 in
   [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md#experiment-ledger)).
6. **Deferred runtime, installer, and release-tooling residuals ([#88](https://github.com/alphastorm/omp-ninfer/issues/88)–[#90](https://github.com/alphastorm/omp-ninfer/issues/90), [#94](https://github.com/alphastorm/omp-ninfer/issues/94)–[#96](https://github.com/alphastorm/omp-ninfer/issues/96), [#116](https://github.com/alphastorm/omp-ninfer/issues/116), [#117](https://github.com/alphastorm/omp-ninfer/issues/117)).**
   In `v0.15.0`, the changed-scope product-tooling council (`CR-20261030T194208Z-af62e766-product`)
   closed by disposition with no in-scope residual P0/P1 after lead controls, and the carried
   runtime council retains its original `v0.14.0` common-engine fork subject
   (`CR-20261028T031911Z-2c6f423b`) in
   [`releases/v0.15.0/review/runtime-ledger.json`](releases/v0.15.0/review/runtime-ledger.json).
   Product-tooling residuals [#97](https://github.com/alphastorm/omp-ninfer/issues/97)–[#100](https://github.com/alphastorm/omp-ninfer/issues/100)
   are addressed in `v0.15.0` (ephemeral unit-test tunnel port, guide-derived `client_acceptance.py`
   model defaults, pre-window `corrections.json` enforcement, and ledger/restoration/route-status
   verifier checks plus idempotent key/config reruns and Windows command exit checks), while the new
   product-council P2/P3 residuals are tracked in
   [#117](https://github.com/alphastorm/omp-ninfer/issues/117) (including native-screen predecessor
   binding, rebind/stage evidence clearing, and full-corpus membership enforcement required before
   `v0.15.1` binds the RTX 3090 DFlash2 screen) and the fork-council residuals for the deferred,
   unshipped native-DFlash2 candidate (`alphastorm/ninfer` commits `5caa4a48` / `2af6b3de`) are
   tracked in [#116](https://github.com/alphastorm/omp-ninfer/issues/116). Because `v0.15.0` carries the
   `v0.14.0` runtime binaries unchanged, the `alphastorm/ninfer#48` installer upgrade/rollback and
   `#49` runtime/media/checkpoint fixes and prior runtime deferrals remain open for the next runtime
   cut in [#88](https://github.com/alphastorm/omp-ninfer/issues/88)–[#90](https://github.com/alphastorm/omp-ninfer/issues/90)
   and [#94](https://github.com/alphastorm/omp-ninfer/issues/94)–[#96](https://github.com/alphastorm/omp-ninfer/issues/96),
   alongside deterministic RTX 5090 `nvcc` module IDs and a corrected, repeated native `Group64` A8
   screen.
7. **Concurrency 2 on native lanes (in progress for the RTX 3090, gates pending; RTX 4090 requires
   a smaller KV format).** Published `v0.15.0` qualifies both native Windows lanes at one active
   request (`C1`, `--max-concurrency 1`, 30 s pending timeout) running sequentially on shared port
   `18082`
   ([`releases/v0.15.0/qualification/rtx4090.json`](releases/v0.15.0/qualification/rtx4090.json),
   [`releases/v0.15.0/qualification/rtx3090.json`](releases/v0.15.0/qualification/rtx3090.json),
   [`examples/manual-tunnel/fail-closed.yml`](examples/manual-tunnel/fail-closed.yml)). On the RTX
   3090, native `C2` (`--max-concurrency 2`, `2` extra / `4` total cached device-side session-state
   slots, `180,000 ms` pending timeout, `21,881,405,440` B Host context, `768 MiB` / `805,306,368` B
   headroom) on a shared `131,072`-token `INT8` KV pool is in progress with final `v0.16.0` (program
   `P16`) release qualification gates still running (EXP-105, EXP-106 in
   [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md#experiment-ledger)): after waiting for in-flight
   off-worker checkpoint exports in `alphastorm/ninfer`'s `EngineCore::reserve_resident_units()`
   (`ea2edc20` / `08257eec`, fixing the prior HTTP 500 `oldest resident cannot obtain its legal
   unit`) and releasing Device `StateImage` replicas to Host before durable export (`8c639fe0` /
   `80c0af77`, cutting first-fork source wait from `14.86–17.22 s` to `<= 0.033 s` and server time
   to first token (TTFT) from `15.4–17.8 s` to `0.33–0.76 s`), the RTX 3090 `INT8` `C2` candidate
   passed startup (`1,110,441,984` B available after startup above the `805,306,368` B floor,
   `22,584 MiB` peak), two-session `59,866`-token true-cold durability (restored checkpoint
   continuation matching a zero-reuse cold reference), calibrated two-concurrent `~60K`-token
   (`59,879 + 59,879` tokens) runs (`6/6` per trial, `18/18` across `3` trials, `0` HTTP 500s), and
   paired `2,048`-token decode (**1.385×** median summed aggregate decode `57.68 → 79.90 tok/s`,
   **0.722×** pair completion wall `71.01 → 51.26 s`). On the RTX 4090, `INT8` `C2` at `131,072`
   tokens (`chunk 2,048`, `640 MiB` headroom) does not fit 24 GB (`Device budget cannot hold the
   calibrated runtime and requested KV capacity` startup refusal; EXP-106) and requires a smaller
   KV format (see `rk4v4` follow-up below).
8. **Open kernel and schedule backlog (native `DFlash2 K=7` in progress; `rk4v4` / `262K` native
   context follow-up gated on the true-cold restore blocker).** Native `DFlash2 K=7` lane-profile
   qualification is in progress with `v0.16.0` (`P16`) release gates (`EXP-101` RTX 3090 and
   `EXP-102` RTX 4090 1,120-prompt powered screens in
   [`scripts/quality_screen.py`](scripts/quality_screen.py), whose published `v0.14.0` incumbent
   arms are completed and seal-verified while candidate arms and final package gates run; EXP-098,
   EXP-103–EXP-105,
   [`docs/measurements/2026-10-27-native-dflash2-gates-and-fit.json`](docs/measurements/2026-10-27-native-dflash2-gates-and-fit.json)):
   after fixing the `ResourceManager` checkpoint-owner replacement defect (`c3911a14`) and the
   export-State residency stall (`8c639fe0` / `08257eec`, EXP-105), RTX 4090 `DFlash2 K=7`
   (`fp32_head_logits: false`) now passes the `0.95` per-case floor on depth-0 case `log-024@0` on
   the `P16` engine (`0.9627–0.9635` on `31583e3f` and `0.96186–0.96294` on `08257eec`, vs `0.945889`
   on `v0.14.0`; EXP-104) and fits `131,072` `INT8` tokens (`1,449,132,032` B available after
   startup above the `671,088,640` B / `640 MiB` floor on `2c6f423b` with `0` extra slots in
   EXP-103; `1,056,964,608` B available with `2` extra slots on `08257eec`). As a **post-`v0.16.0`
   follow-up release item**, native **`rk4v4` 4-bit KV and `262,144`-token native context** (`17,920`
   B/token vs `INT8` `33,792` B/token, EXP-107) passed `FP64` op/graph/store controls (`7/7`) and
   held-out perplexity on both cards ($\Delta\text{NLL} = 0.00345 \le 0.02$) and fit `262,144`-token
   `C1` on the RTX 3090 (`1,097,859,072` B available after startup above the `805,306,368` B /
   `768 MiB` floor; exact `130,048`- and `250,062`-token diagnostic retrieval), but is blocked on
   the **exact true-cold restore oracle**, where restored continuation diverges from the zero-reuse
   cold reference at token `32` (`262,144`-token `C1`) and tokens `16–32` on the first of two
   concurrent sessions (`245,760`-token `C2` and `229,376`-token `C2`, cause unproven) and RTX 4090
   `chunk 2,048` startup capacity at `262,144`-token `C1` / `245,760`-token `C2`. Root-cause
   numerics localization for the rejected native `sm_86`/`sm_89` small-T tensor-core decode
   candidate (EXP-099,
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

- **Wholesale upstream engine merge — prior deferral superseded by v0.13.0–v0.15.0 (EXP-097).** Earlier upstream
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
- **Full upstream re-port from `64d10fbf` to `1882c6ad` — deferred in favor of targeted fix
  cherry-picks.** Upstream `Neroued/ninfer` master `1882c6ad`
  (`1882c6adbc98043fcf89f3589aa5addb3742777a`) is 215 commits ahead of the `v0.13.0`–`v0.15.0`
  merge base `64d10fbf` (`64d10fbf9f8e6bfc79ab0570b94674c5b9997929`), while `alphastorm/ninfer`
  is 518 commits ahead of `64d10fbf` at `2c6f423b` (and `main` tip `752dd887`, which merges
  `2c6f423b` plus `alphastorm/ninfer#48` installer upgrade/rollback and `#49` runtime/media/checkpoint
  fixes; see [`docs/UPSTREAM.md`](docs/UPSTREAM.md)). Classification of all 215 upstream commit
  subjects shows 177 on unrelated tracks (Spark/DGX Spark, `GLM5Next`, `TP2`/`EP2`, MoE,
  `qwen4_exp`, distributed, and bench/docs), 26 serving/context features or config refactors, 2
  marginal CPU-side latency commits (context admission/reclaim overhead and grammar
  terminal-automata compilation), and 10 serving/runtime/artifact/build fixes; zero commits touch
  `NINFER_SM86`/`NINFER_SM89` guards or improve Qwen3.8-27B dense decode, DFlash2, or MTP3 kernels
  (upstream's `docs/performance/qwen3.8-27b.md` remains the historical 2026-09-28 campaign at
  revision `7f6aafed`). Meanwhile, upstream restructured the exact seams the fork's 518-commit
  stack sits on: (1) in `src/models/qwen3_5`, upstream deleted
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
  `src/text/grammar.{cpp,h}`, and `src/text/json_schema.cpp`. Re-porting the fork's 26 modified
  `qwen3_5` files, 24 modified `src/runtime` files, durable checkpoint store, and native packaging
  contracts onto `1882c6ad` is deferred (estimated at 5–8 multi-agent days from the 4-day `v0.14.0`
  integration on a compatible base, with GPU-only bit-identity and resume risk); the next release
  cherry-picks self-contained bug fixes onto the `2c6f423b`/`752dd887` lineage instead.
- **No better primary model than `Qwen3.8-27B` (`groupwise-int` v3 `81f924d4`, `20,437,521,664`
  bytes / `19.03 GiB`) as of 2026-10-30; alternative upstream artifacts and `Qwen4-27B` (`qwen4_exp`)
  deferred or rejected.** A 2026-10-30 census of `neroued/*` and `Qwen/*` Hugging Face repositories
  confirms `neroued/Qwen3.8-27B-NInfer` remains at artifact blob `81f924d4` (Hugging Face commit
  `51630a0c`, 2026-09-15; repository commits through `18caef28` on 2026-10-29 are documentation
  only), and no candidate replaces it as the primary model across the qualified 32 GB and 24 GB
  single-GPU lanes:
  1. **`neroued/Qwen3.8-27B-nvfp4-NInfer` (`74d2c571`, `6a534f28`, 2026-09-15) — rejected:** the v3
     artifact grew to **`23,719,715,844` bytes (`22.09 GiB`)**, `+2,227,020,804` bytes (`+2.07 GiB`)
     over the `21,492,695,040`-byte (`bb336052`) v2 artifact measured in EXP-008 and `+3.06 GiB`
     over our shipped `19.03 GiB` `groupwise-int` container, so it still cannot fit the RTX 5090
     `DFlash2 K=7` `BF16` KV `131,072`-token `C2` profile.
  2. **`neroued/Qwen3.6-35B-A3B-NInfer` (`3e332976`, `22,790,484,480` bytes / `21.23 GiB`,
     `Qwen3.5` MoE `35B` total / `3B` active, `DFlash` block-8 + multi-token prediction `MTP`) —
     faster but lower-quality option, not a primary replacement:** while much faster on one RTX
     5090 (`677.2 tok/s` `MTP3` code decode, `620.6 tok/s` `DFlash K=7` code decode, `17,705 tok/s`
     `7.7K` prefill at `INT8` KV), its agentic-coding quality trails `Qwen3.8-27B` by a full
     generation (**SWE-bench Pro `44.6` vs `61.7`** for `Qwen3.8-27B`, **`NL2Repo` `20.5` vs
     `42.3`**) and its `21.23 GiB` container exceeds a zero-offload 24 GB native budget at `131,072`
     tokens (candidate only for a separate fast/auxiliary tier spike with partial expert offload).
     Older `Qwen3.6-27B` (`16.29 GiB` `groupwise-int` / `17.07 GiB` `nvfp4`) lacks `DFlash2` and
     trails on SWE-bench Pro (`53.5` vs `61.7`).
  3. **`neroued/Qwen3.8-Flash-Next-NInfer` (`57cf9cd0`, `108,445,200,388` bytes / `101.00 GiB`,
     `Qwen4Exp` MoE + per-layer-embedding `PLE`) and `neroued/GLM-5.3-Flash-NInfer` (`f1c4e21`,
     `191,484,328,832` bytes / `178.33 GiB`, `GLM5Next`) — infeasible on this hardware:**
     `Qwen3.8-Flash-Next` requires `~63.3 GiB` of Host-resident routed-expert (`Main-expert`)
     backing (exceeding the RTX 5090 container host's `47 GiB` physical / `~31 GiB` WSL2 RAM) plus
     `~37.7 GiB` of device-resident non-expert weights and KV/state (impossible on 24 GB
     `sm_89`/`sm_86`, where its `NVFP4`/`FP8`/block-scaled MoE routes are also unsupported), and
     `GLM-5.3-Flash` (`178.33 GiB`) requires two DGX Spark nodes.
  4. **`Qwen4-27B` (`qwen4_exp` dense 27B) — deferred (no public weights as of 2026-10-30; upstream
     27B ops unmerged on `feat/qwen4-27b-ops`):** no public `Qwen4-27B` weights, model card,
     license, context specification, or agentic-coding/tool-use benchmarks exist (`Qwen` and
     `nvidia` Hugging Face organizations publish no `Qwen4` checkpoints, and
     `IteraCompute/Qwen4-27B-NVFP4` remains an empty placeholder with no inference files). In
     Hugging Face `transformers` (`Qwen4ExpTextConfig`) and upstream `Neroued/ninfer` master
     (`src/models/qwen4_exp/config.cpp`, `docs/maintainer/qwen4_exp-model.md`), `qwen4_exp`
     currently implements only the `Qwen3.8-Flash-Next` MoE+PLE variant (`hidden_size = 2560`, 48
     layers, 512 experts, one PLE layer) and rejects the dense 27B variant (`hidden_size = 5120`, 64
     layers, dense SwiGLU FFN, no PLE, query-sparse attention (`QSA`) with 24 query heads and 4 KV
     heads, and a 4-bit `Q4` proposal head). Upstream `Neroued/ninfer` implements the 27B kernel
     checklist across 19 commits on unmerged feature branch `feat/qwen4-27b-ops` (tip `e1874e94`,
     2026-10-29, branched from 2026-10-27 master commit `04d0d15b`: RTX 5090 `NVFP4` `28672×5120` +
     fused SwiGLU and `5120×14336`, `FP8` `14976×5120` and `5120×5120`, `Q4` `248320×5120`
     vocabulary projection, hidden-size-5,120 (`H5120`) gated-residual norm/combine and `FP8`
     four-stream residual mixing, and four-KV-head `QSA` preparation and tuned sparse GQA across
     `BF16`, `INT8`, `NVFP4`, and 8-bit-key/4-bit-value (`K8V4`) KV caches), while upstream `master`
     (`04d0d15b`/`1882c6ad`) carries only unchecked design docs
     (`docs/designs/qwen4-27b-op-checklist.md`) and leaves the dense 27B model layer and converter
     recipes (`tools/convert/official_recipes.py`) unimplemented. `feat/qwen4-27b-ops` stays on
     watch until public weights and upstream model/converter support exist.
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
  (EXP-104) rejected; default `DFlash2 K=7` passes the `P16` floor and 131K fit while release
  gates run (EXP-098, EXP-103–EXP-105).**
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
  In `v0.16.0` (`P16`) diagnostics ([`EXP-103` and `EXP-104`](docs/PERFORMANCE.md#experiment-ledger)),
  config-only shorter draft windows on the `v0.14.0` RTX 4090 binary failed `log-024@0` against
  `MTP3` and were **rejected**: **`K=6` cross ratios `0.8625–0.8642`** (`116.98 / 116.97` vs `135.37
  / 135.63 tok/s`, median `0.8633`) and **`K=5` cross ratios `0.8668–0.8673`** (`117.61 / 117.63` vs
  `135.62 / 135.69 tok/s`, median `0.8671`; `K=3` was already rejected at `0.811526` with `13/84`
  misses), while the `K=7` `131,072`-token `INT8` `C1` fit on the `v0.14.0` RTX 4090 binary passed
  (`available_after_startup = 1,449,132,032` B above the `671,088,640` B / `640 MiB` floor,
  `22,265.0 MiB` peak, exact `32`-token / `114`-byte true-cold continuation SHA-256 `07b8db1f`,
  EXP-103). Opt-in **`FP32` vocabulary-head logits (`--fp32-head-logits`,
  `engine.fp32_head_logits: true`, `+8,442,880` persistent bytes at `K=7`/`C=2`) also failed
  `log-024@0` at `0.9016–0.9025`** (`122.29 / 122.26` vs `135.50 / 135.61 tok/s` on `P16` binary
  `31583e3f`, median `0.9021`, EXP-104) and is **rejected** (the option stays off in all profiles),
  whereas the default-off `DFlash2 K=7` control on the same `P16` binary (`31583e3f`) passed
  `log-024@0` at **`0.9627–0.9635`** (`130.53 / 130.56` vs `135.51 / 135.60 tok/s`) and passed again
  on the later `P16` integration build (`08257eec`) at **`0.96186–0.96294`** (`130.60 / 130.50` vs
  `135.62 / 135.68 tok/s`, EXP-104). Both published `v0.14.0` and `v0.15.0` retain MTP3 on the
  native profiles; native `DFlash2 K=7` (`EXP-101` / `EXP-102`) remains unshipped while release
  qualification gates run.
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
  `rk4v4` deferred to a follow-up release on the true-cold restore oracle (EXP-107); KV prefetch
  and E8/RotorQuant parked.** Native head-dim-256 (`D256`) `rk4v4`
  (`rk4v4_h256_lloyd_g64_s4_g32_v1`, ported from `ashalliants/ninfer-3090` `f5cec0a6`; `17,920`
  B/token vs `INT8` `33,792` B/token, `47.0%` smaller per-token KV) passed `7/7` `FP64`
  op/graph/store test executables and held-out perplexity on both `sm_86` and `sm_89` (`16,984`
  scored tokens across `32` windows at `1,024` context / `512` stride: mean NLL `1.643463 →
  1.646910`, **$\Delta\text{NLL} = 0.00345 \le 0.02$**, PPL `5.173052 → 5.190916`, max domain
  `+0.006273 <= 0.05`) and fit at **`262,144`-token `C1` on the RTX 3090** (`1,097,859,072` B
  available above the `805,306,368` B / `768 MiB` floor; exact `130,048`- and `250,062`-token
  diagnostic retrieval in `197.86` and `503.57 s`) as well as `245,760`-token `C2` (`1,135,607,808` B
  available) and `229,376`-token `C2` (`1,429,209,088` B available), while on the RTX 4090 (`chunk
  2,048`, `640 MiB` floor) `262,144`-token `C1` and `245,760`-token `C2` refused startup admission
  and `229,376`-token `C2` passed startup (`952,107,008` B available). However, **the exact
  true-cold restore oracle failed on the RTX 3090**: restored continuation diverged from the
  zero-reuse cold reference at **token 32** at `262,144`-token `C1` (`3,093` prompt / `3,066` cached
  tokens, cold token ID `48117` vs restored token ID `3635` despite byte-exact CPU page-layout
  inversion of the `55,050,240`-byte checkpoint payload, SHA-256 `53e8f8bc`) and at **tokens
  16–32** on the first of two `59,866`-token concurrent sessions (`59,840` cached tokens; second
  session `32/32` tokens equal) at `245,760`-token `C2` and `229,376`-token `C2`, with the cause
  unproven between GPU restore transport and width/schedule-dependent `rk4v4`
  quantization/attention between cold chunked prefill and speculative decode + restore. `rk4v4` and
  `262,144`-token native context are deferred to a follow-up release (`--kv-dtype rk4v4` stays off
  in shipped profiles; EXP-107 in [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md#experiment-ledger)),
  and paged host-to-device KV prefetch beyond 262K tokens and E8-lattice/RotorQuant ceiling work
  remain parked in [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md#ideas-backlog).

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
