# Upstream watch

Oh My Pi (coding-agent client) connects through OMP NInfer (qualified appliance and release layer)
to NInfer (inference engine) serving Qwen3.8 27B (served model). The runtime ships from downstream
forks; published release **v0.15.0** (2026-10-30) pins an unmodified upstream OMP 18.14.0 client and runs all three qualified GPU lanes — the RTX 5090 container runtime (`v0.7.0-qwen38-5090-beta.3`) and the native Windows RTX 4090 (`v0.7.0-qwen38-4090-beta.3`) and RTX 3090 (`v0.7.0-qwen38-3090-beta.3`) runtime packages — from one common engine source `2c6f423b` (`2c6f423bd817b6534158553e1b34ab4959c43165`) on upstream `Neroued/ninfer` master `64d10fbf` (carried unchanged from `v0.14.0`).
This page names the upstreams we track, runtime fork points, and the current pull-in position. The
watch manifest is [`upstream-watch.json`](../upstream-watch.json); the watch tool is
[`scripts/upstream_watch.py`](../scripts/upstream_watch.py); dated reports land in
[`docs/measurements/`](measurements/).

## Current positions

| Component / upstream | Current position (v0.15.0) | Upstream base / watch head | Evidence and notes |
| --- | --- | --- | --- |
| `can1357/oh-my-pi` (client) | Unmodified upstream **OMP 18.14.0**, source `31147f9d1a76608549821c3759f8487b4d66c72d`, tree `9a63b5bfbb5971962c44fca660744b0d75dcd2c2` | Upstream release [`v18.14.0`](https://github.com/can1357/oh-my-pi/releases/tag/v18.14.0) (2026-10-29) | Upstream binaries rebuilt with Bun 1.4.4 (CVE-2026-91403, CVE-2026-111497); `qwen3.8-27b` defaults to stock `replace` edit while `q38-ninfer` stays `hashline`; accepted across all five v0.15.0 routes; see [client setup](QUICKSTART.md#omp-18140-client), [release notes](../releases/v0.15.0/NINFER_RELEASE_NOTES.md), and [host-free review](measurements/2026-10-30-omp-18140-client-upgrade-review.json). |
| `alphastorm/ninfer` (RTX 5090 container runtime) | `v0.7.0-qwen38-5090-beta.3`, source `2c6f423bd817b6534158553e1b34ab4959c43165` | `Neroued/ninfer` master `64d10fbf9f8e6bfc79ab0570b94674c5b9997929` | Carried unchanged from v0.14.0: image `760fb6be` (base `d4377ed0`), server `55f0b95a`, model `81f924d4`, profile `qwen38-5090-v0.13.0` (`751d22dc`), DFlash2 draft window 7, BF16 KV (146,368 automatic tokens), two requests in flight, schema 3 checkpoints (`/checkpoints-v013`, strict origin auth, non-blocking export), JSON-schema output, 128-character tool names, founder-approved 5090-only first-build reproducibility exception ([receipt](../releases/v0.15.0/qualification/rtx5090.json)). |
| `alphastorm/ninfer` (RTX 4090 and RTX 3090 native Windows runtimes) | RTX 4090 `v0.7.0-qwen38-4090-beta.3` (`87038cfb`, server `5caa7780`, config `b5cfbf50`); RTX 3090 `v0.7.0-qwen38-3090-beta.3` (`a7637f66`, server `fedce425`, config `d08d262b`, 350 W cap); shared source `2c6f423bd817b6534158553e1b34ab4959c43165` | `Neroued/ninfer` master `64d10fbf9f8e6bfc79ab0570b94674c5b9997929` | Carried unchanged from v0.14.0: shared published model v3 `81f924d4`, MTP3 (`--lm-head-draft`), INT8 KV, `Group64` A8 off, one request at a time, shared Host budgets (`14,787.734375 MiB` / `11,715.734375 MiB`), `640` / `768 MiB` admission headroom, strict-origin schema 3 checkpoints (`session-checkpoints-v3`), JSON-schema output, 128-character tool names, CycloneDX dependency SBOMs, UUID-bound on one two-GPU Windows host (sequential on port 18082; first-of-lineage rollback `not_applicable`; stop running v0.13.1 RTX 3090 before upgrade `#94`; [RTX 4090](../releases/v0.15.0/qualification/rtx4090.json), [RTX 3090](../releases/v0.15.0/qualification/rtx3090.json)). |
| `Neroued/ninfer` (engine watch) | Shipped container and native runtime base `64d10fbf` in `v0.14.0`–`v0.15.0` | Master `1882c6ad` (2026-10-29, 215 commits after `64d10fbf`); `dev` `b57eaddc` (2026-10-30, +10 over master) | **No RTX 3090 (`sm_86`) / RTX 4090 (`sm_89`) / Windows or Qwen3.5-dense (`Qwen3.8-27B`) speed work since `64d10fbf`; re-porting our fork onto `1882c6ad` is not planned** (estimated 5–8 multi-agent days for master, 7–10 for `dev`; upstream's `docs/performance/qwen3.8-27b.md` remains the historical 2026-09-28 `7f6aafed` campaign). [Dated watch](measurements/2026-10-29-upstream-watch.json) lists all 215 master commits (`unknown-truncated` at the 300-file API cap); downstream qualification remains bound in [`releases/v0.15.0/qualification.json`](../releases/v0.15.0/qualification.json). |
| `Neroued/ninfer` (Qwen 4 feature watch) | Research only; no source adoption | `feat/qwen4-27b-ops` at `e1874e94` (2026-10-29), 204 commits after shipped base `64d10fbf` | [Dated watch](measurements/2026-10-29-upstream-watch.json) lists all 204 commits (`unknown-truncated` at 300 files). `Qwen4-27B` has no public weights as of 2026-10-30; this branch watch does not change the shipped Qwen3.8 model or engine pins. |
| `sergiuszm/ninfer-4090` (engine watch) | `upgrade-available`; active `sm_89` reference | `rtx4090-port` at `7f47a622` (2026-10-24), 172 commits after 2026-10-07 upstream baseline `81c8ce09` | Replaces the inactive `UDPSendToFailed` watch (`5c60b7c9`, 2026-09-09); its old `11aae2d6` fork point remains in the manifest as provenance. No community runtime is adopted. |
| `ashalliants/ninfer-3090` (active `sm_86` fork watch; supersedes `Don-Chad/ninfer-3090`) | `upgrade-available`; tracked `sm_86` community line | Master `f5cec0a6` (2026-10-30, tag `v0.17.1-rtx3090`; earlier `477b2ddc` in the [2026-10-29 watch](measurements/2026-10-29-upstream-watch.json)) | **Supersedes `Don-Chad/ninfer-3090`** (dormant at `d8c29253` since 2026-10-16 after [PR #30](https://github.com/Don-Chad/ninfer-3090/pull/30) / `1418aca3` adopted `ashalliants/ninfer-3090` commit `931bd49b`). Provenance source for the native head-dim-256 (`D256`) `rk4v4` 4-bit KV codec (`0b4f9588`, `2ba10da2`) evaluated in [EXP-107](PERFORMANCE.md#experiment-ledger); shipped `v0.14.0`–`v0.15.0` native source remains `2c6f423b` on upstream master `64d10fbf` and adopts no community binary. |
| `iamwavecut/ninfer-all` (consolidation hub watch) | Watch; idea and kernel reference only | Master `c87b836d` (2026-10-30) | Multi-architecture consolidation hub (`sm_70`/`sm_75`/`sm_80`/`sm_86`/`sm_89`/`sm_120a`, `sm_86` default build) integrating work from `ashalliants/ninfer-3090`, `UDPSendToFailed/ninfer-4090`, `TertiumOrganum1/ninfer-3090`, `Wallawalla47/infernix`, `13thblade/ninfer-all-nvfp4`, and `IMGillusion/ninfer-disk-kv`. Source of the opt-in `FP32` vocabulary-head logits idea (`2013d01f`) ported into `alphastorm/ninfer` and rejected on RTX 4090 depth-0 case `log-024@0` (`0.9016–0.9025` decode ratio vs `MTP3`, below the `0.95` floor; [EXP-104](PERFORMANCE.md#experiment-ledger)). |
| `13thblade/ninfer-all-nvfp4` (non-Blackwell `NVFP4` watch) | Watch; not adopted | Master `245f3ad2` (2026-10-30) | Implements `NVFP4` 4-bit weights with `FP16` activations (`W4A16`, `--nvfp4-w4a16`) on `sm_75`/`sm_86`/`sm_89`/`sm_120` and 8-bit integer activations (`W4A8-int`, `--nvfp4-w4a8-int`) on `sm_70`/`sm_75`/`sm_80`/`sm_86`/`sm_89`/`sm_120` for GPUs without Blackwell `FP4` tensor cores; any adoption requires independent artifact fit and 1,120-prompt powered quality screening. |
| `IMGillusion/ninfer-disk-kv` / `IMGillusion/ninfer-engine` (disk KV tier watch) | Watch; design reference only | `IMGillusion/ninfer-engine` `main` `82e5e826` (2026-10-30; also `--disk-kv-path` in `troyliu0105/ninfer-all` `76940895` / `43c2e163`) | Host/disk L3 KV tier with phased read/write worker pools (`767e67e2`, `92bac11c`), two materialization slots (`8d9b28cb`), and device-to-host (`D2H`) spill settlement before staging reuse (`a0e2d900`). Tracked as a design reference alongside our authenticated schema 3 checkpoint store. |
| `eagle-hq/EAGLE-4` / `EAGLE-Corp/Qwen3.8-27B-EAGLE4` (drafter watch) | Watch; not implemented in NInfer | `eagle-hq/EAGLE-4` `0.1.1` (2026-10-21); `EAGLE-Corp/Qwen3.8-27B-EAGLE4` `f58a5985` (2026-10-19; [Neroued/ninfer#413](https://github.com/Neroued/ninfer/issues/413)) | Autoregressive tree drafter for `Qwen3.8-27B` (`3,089,075,200` BF16 params / `6.18 GB` vs `z-lab/Qwen3.8-27B-DFlash2` `50307d4c` at `1,924,404,480` params / `3.85 GB`, unchanged since 2026-08-19; Hugging Face license field `other` / `eagle-4`, non-Apache-2.0). Watch only until license terms, an engine tree-verify path, and 24 GB fit are established. |

The [2026-10-29 read-only receipt](measurements/2026-10-29-upstream-watch.json) also records
the `sergiuszm/ninfer-4090` (`7f47a622`) and `Don-Chad/ninfer-3090` (`d8c29253`, superseded by
`ashalliants/ninfer-3090`) heads and client `main` at `338d2ce6`, 1,826 commits after the `v0.14.0`
stock OMP 18.12.6 baseline `45c35e40` (before `v0.15.0` advanced the client pin to `v18.14.0` at
`31147f9d`). Client commit/file lists are cut at the GitHub API caps (250 commits / 300 files); no
watched client, engine, or fork-network head is an adopted release pin. Recommendations are
commit-subject/path heuristics, not a security assessment or a qualification result.

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
[#116](https://github.com/alphastorm/omp-ninfer/issues/116). Native RTX 3090 DFlash2 is deferred to
`v0.15.1` after fork-after-resume failed with `Native could not release an unreferenced checkpoint
owner` (fixed in `alphastorm/ninfer`, awaiting shipping-package rebuild and requalification).

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

### v0.15.0 client binding — OMP 18.14.0

Published release **v0.15.0** (2026-10-30) pins unmodified upstream
[v18.14.0](https://github.com/can1357/oh-my-pi/releases/tag/v18.14.0), source
`31147f9d1a76608549821c3759f8487b4d66c72d`, tree
`9a63b5bfbb5971962c44fca660744b0d75dcd2c2` (published upstream 2026-10-29T18:25:10Z, release ID
`428242783`); see [client setup](QUICKSTART.md#omp-18140-client). Upstream release binaries are
rebuilt with Bun 1.4.4 (fixing CVE-2026-91403 and CVE-2026-111497 documented in upstream 18.13.0),
`qwen3.8-27b` defaults to the `replace` edit tool while opaque `q38-ninfer` stays `hashline`,
provider-qualified selectors require exact matches, `model.loopGuard` settings reach custom
Responses models, and compaction bounds retained history and preserves a completed main summary if
an optional short summary fails. The
[client upgrade review](measurements/2026-10-30-omp-18140-client-upgrade-review.json) hashes all
three assets against upstream `SHA256SUMS.txt` and API digests and records two seven-check macOS
stub rehearsals; fresh live acceptance across all five documented routes (31 blocks), all three
stock 18.14.0 binaries, and both native public installs then passed on frozen candidate `af62e766`
([v0.15.0 composed acceptance](../releases/v0.15.0/acceptance/composed-external-installation.json)).

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

Read-only fork-network and upstream-code census as of 2026-10-30 against our `v0.14.0`–`v0.15.0`
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
  `64d10fbf` (selected source `2c6f423b` in `v0.14.0`–`v0.15.0`; `6d4d0a05` in `v0.13.0`–`v0.13.1`). From
  v0.6.2 through v0.12.2, it built from the mainline runtime whose upstream base was `6e8b2e2a`
  (selected source `1302d639` in v0.11.0–v0.12.2). The retired container mirror point `4eef14a7`
  was the lineage's base before v0.6.2 and made the delta read 17 commits larger than it was.
- The RTX 4090 and RTX 3090 native Windows lanes originally vendored their upstreams at the
  recorded commits (`11aae2d6` and `ef6ecc3c`). In `v0.14.0` and `v0.15.0`, both share frozen source `2c6f423b`
  with the RTX 5090 container on upstream `Neroued/ninfer` master `64d10fbf`
  (`v0.7.0-qwen38-4090-beta.3` and `v0.7.0-qwen38-3090-beta.3`), after initial `64d10fbf` rebases at
  `7a25cd72` (`v0.7.0-qwen38-4090-beta.2` and `v0.7.0-qwen38-3090-beta.2`) in `v0.13.1`. From
  v0.12.0 through v0.13.0 they shipped from the mainline fork runtime (`cad19767` on `6e8b2e2a`,
  adding explicit `--gpu-uuid` device selection on the two-GPU Windows host; earlier v0.9.1 retained
  RTX 4090 source `cba7eb93`, RTX 5090 child `e20060b6`, and RTX 3090 `f08309da`). The
  durable-checkpoint, security, and packaging work remains downstream.
- Through v0.7.4, the client fork point was the upstream tag commit onto which downstream patches
  rebased. Since v0.8.0 (and in v0.15.0 with stock OMP 18.14.0 at `31147f9d`), this
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

