# OMP NInfer v0.11.0 — installable candidate, not a released product

Founder-selected RTX 5090 component **v0.6.16**, source
`1302d63929e400a05e1c9cdb0fc8003a70269825` (option **c**), combined with unmodified
upstream OMP **18.8.7**. The founder published the component at13:46Z; its real OCI
digest is `sha256:6a02feba4163d992cc6a46baf28e0ece2ffe6a2ead91939e566c1b3080f5bc02`.
The product is not released: documented-route acceptance is incomplete and production
promotion is unperformed. The authorized lane rebind advances root pins to this candidate;
the manifest stays candidate with its external-install acceptance blocker.

## Founder decisions — 2026-10-10

- **Select option(c).** The candidate is shipped v0.6.15 `eaf221ac` plus EXP-092
  `b72daad6` and EXP-094 `a59c13d0`, **without** pair-Q5 change `3a2fadbd`.
  The exact-a59 proposal is a **superseded alternative**, not the selected source.
  Its independently red NVFP4 ctest and original assets remain preserved.
- **Source publication and preflight completed, as reported by the lead.** Main
  reports pushing `exp/v0616-without-3a2fadbd` to alphastorm/ninfer with origin
  containing exact commit `1302d63929e400a05e1c9cdb0fc8003a70269825`, then a passing
  cutter **--dry-run**, exit0: “preflight ok ... archive bed8c8d4”. No tag, release or
  workflow was created by that preflight. The founder subsequently ran the live cut
  at13:46Z: binary/source tags name1302d639 and runtime-image workflow38057050899
  succeeded. Main verified an anonymous pull with exact serve548fe239. This worker
  did not repeat those checks or push runtime source. The earlier origin refusal
  remains history. [Actual publisher receipt](qualification/runtime-publication.json).
- **Retain native RTX 4090 in v0.11.0.** The founder will install the card today on
  the replacement native host; its OMP18.8.7 qualification is pending on that host.
  This supersedes the former retire-versus-hold decision, rather than dropping the
  lane or holding the release for that decision. Planned installation is not proof
  of hardware presence or qualification.
- **Harden the probe now, new candidate.** At approximately17:25Z the founder
  authorized the all-numeric nonce `493817-205361` after the registered diagnostic
  below. Runtime source, binary, image, sampling and exact-answer comparisons do
  not change. Fresh acceptance must bind the new pushed class-closure commit.
- **RTX3090 scope awaits a founder decision.** The successful native OMP18.8.7
  acceptance on predecessor `65b6c4264b3bdf8f3ed793fdd138a1a9da31804b` is preserved
  as evidence only and **not composed**. The founder is replacing that hardware
  with the RTX4090. The current decision is reinstall/re-accept with a3090 versus
  drop that lane from v0.11.0. No scope reduction is made here: while retained,
  the lane cannot ship without acceptance on5861712f; no old receipt is retargeted.

Current selection/status is in [founder sequence](qualification/founder-sequence.json)
and the [selected C qualification summary](qualification/option-c-lane.json).
Frozen source/build/benchmark receipts retain their contemporaneous experiment
labels; those historical labels do not override this founder selection.

## Acceptance nonce diagnostic and new candidate

The first published-image window on `65b6c4264b3bdf8f3ed793fdd138a1a9da31804b`
passed preflight and the host2/2 documented steps, then failed the Linux structured
exact-continuation check: expected `COBALT-493817`, returned `COBOLT-493817`. The
misspelling was already in the state turn generated thinking; its visible answer
was OK. Mac0/10 and Windows0/5 steps were not reached. Independent restoration
passed. This failed window remains diagnostic-red; no accepted platform receipts
were promoted and no causal runtime/client/backend attribution is made.

The registered diagnostic plan SHA-256
`8e97924e1437b433b1d76356c1030b954116e44709384bf7c43bd2120888037e`
preceded the17:06–17:18Z experiment. It used OMP18.8.7, one fresh isolated session
per trial, the unchanged structured probe plant/recall, per-model stateful compat
and sampled runtime defaults (temperature1,top_p≈0.95,top_k20), without added
sampling, seed, thinking or tool restrictions. The fixed-N rule and exact image,
binary, model and profile identities are in the content-safe
[diagnostic receipt](../../docs/measurements/2026-10-10-omp-acceptance-nonce-diagnostic.json).

| Cohort | Exact recall | Misspelled / all assistant nonce copies |
| --- | --- | --- |
| Published v0.10.0, `COBALT-493817` |50/50|0/163|
| Published v0.6.16, `COBALT-493817` |50/50|0/165|
| Published v0.6.16, `493817-205361` |50/50|0/152|

The pre-registered verdict is **no material difference**, one-sided Fisher p=1,
**hardened green**. All150 unique sessions and302 requests were accounted for;
hardened trial3 added two read-only bash tool rounds and still recalled exactly.
This is bounded diagnostic evidence, not a guarantee of deterministic recall or
route acceptance. The 2026-09-28 EXP-073 precedent separately had91/92 exact
recalls for the same OK-only/verbatim pair; its hidden misspelling was correctly
recalled, while its exact failure was a quoted nonce/refusal. Do not conflate it
with the present failure or the six historical canonical-probe passes. S1 ran
zero canonical probes; its two Juniper RPC proofs are different evidence.

All active plants, greps and driver constants now use the numeric nonce. The probe
plant interpolates NONCE; the exact continuation/restart checks are not widened.
The executable documented-route invariant was red against the unchanged drivers
and docs, then green after cutover; the context filter `grep -v 493817` remains.
Historical measurement receipts and the ORCHID/COLOR long-context fixture are
untouched. The new40hex candidate and exact-head CI URL are delivered in PR78
and the worker handoff, not self-referentially embedded in this commit.

RTX3090 predecessor acceptance is not composable. The RTX5090 full window below
passed on the hardened candidate; RTX4090 hardware/acceptance and the RTX3090
founder decision remain pending. This does not establish composed readiness.

## Published RTX5090 route acceptance — frozen5861712f

Acceptance owner Accept5090 ran one full **initial** window against candidate
`5861712f561ff0b3100dd4350e02d777a3f5007e`. Preflight, window, collect and summarize
all passed. The published image6a02feba served the unchanged548fe239 binary.

| Documented route | Passed steps | Byte-preserved runner |
| --- | --- | --- |
| RTX5090 container host |2/2|[runner](../../docs/measurements/2026-10-10-v0110-rtx5090-container-host-run.json)|
| RTX5090 macOS client |10/10|[runner](../../docs/measurements/2026-10-10-v0110-rtx5090-macos-client-run.json)|
| RTX5090 Windows client |5/5|[runner](../../docs/measurements/2026-10-10-v0110-rtx5090-windows-client-run.json)|

All three stock OMP18.8.7 clients passed the structured live and fail-closed proofs:
[macOS arm64](acceptance/darwin-arm64-18.8.7.json),
[Windows x64](acceptance/windows-x64-18.8.7.json) and
[Linux x64 under WSL2](acceptance/linux-x64-18.8.7.json). These existing-producer
receipts retain their candidate preview statuses; no platform posture is promoted.

[Measured restoration](../../docs/measurements/2026-10-10-v0110-acceptance-restoration.json)
records **385.948s observed downtime** (about385.9s), bounds384.444–386.451s,
distinct from the387.738s driver hold envelope. Independent health/identity checks
measured restoration of the incumbent image/profile/arguments (except the request-log
timestamp), four mounts,
port/restart policy, route key/checkout, hold markers, task definitions/enabled
states and execution policies. The designed restore recreated the container; its
old/new IDs are retained, not silently treated as equal. Production was not upgraded.

The [producer input capsule](acceptance/rtx5090-acceptance-evidence.json) retains
all phase stream-isolation/hash audits and explicitly claims no native3090/4090
evidence. Its [original checksums](acceptance/rtx5090-evidence-checksums.json), three
runners, three platform receipts and restoration are copied without serialization;
the source sizes and SHA256s match. The failed65b6c426 window and nonce diagnostic
remain separate preserved evidence, not relabelled.

This is an **evidence-only follow-on**, not a new acceptance candidate. Every
remaining acceptance still binds5861712f, not this evidence commit. Do not compose
yet: RTX4090 waits for hardware and the founder must decide the RTX3090 lane.
The old65b6c4263090 pass is non-composable evidence; manifest candidate/external
acceptance blockers remain and no production promotion or product cut is authorized.

## Exact selected component and build

The conflict-free mechanical replay is `eaf221ac` → b72 replay
`344850b3e9e3c8f5855f6a979a630d1c4eada4a8` → a59 replay `1302d639…`.
No manual runtime fix was introduced. This differs from the original a59 target;
its clean rebuild, serial-output binding and A/B/B/A cost measurement are real C
receipts, not an assumption that changing source preserves EXP-092/094 behavior.
The appliance-local Release build used `ninfer-dflash2-build-env:20261001`, CUDA
**13.1.115**, GNU **13.3.0** and **sm_120a**. Its version reports the exact selected
commit and **source_dirty=false**.

- Serve SHA-256: `548fe239a3f2f97c98d864b4a7b9c6beb1263788633f1a4bf13c101f2beecace`.
- Local image: `ninfer-overnight:S1-1302d639-option-c-package-local`; local ID
  `sha256:9e1b9a8a8f435b35bd32f252d4756bf0dc50d3e2512371d97553ea398df4f8e3`.
  This is **not an OCI publication digest**.
- Model `0634abb07024221de141456cf04a42ab74b18bc38e1b781c6eb2e062a467eec3`,
  20,437,336,576 bytes.
- Profile `qwen38-5090-v0.11.0`; configuration identity
  `91a3567002a43025876e811597353764b20e32f0818bcb6c582a5072c96d7e11`.
- Unchanged v0.10.0 serving shape: DFlash2 K=7, BF16 KV, two in flight, two device
  slots,131,520 KV tokens,131,072-token context ceiling,180-second pending timeout.

### Selected assets and founder preflight

Mac handoff: `$HOME/Desktop/ninfer-v0.6.16-option-c-release/`. All runtime asset
hashes were verified on the Mac; candidate selection changes only the notes, not
those assets. The source archive equals the exact commit's Mac `git archive`.

| Asset | SHA-256 |
| --- | --- |
| ninfer-qwen38-rtx5090-v0.6.16-linux-x86_64-cuda13.1.tar.gz | bed8c8d4f8ccb8fcf8276248d772c0b9c0f98b1e51c58820ff1f698b66d6fcbd |
| ninfer-qwen38-rtx5090-v0.6.16-linux-x86_64-cuda13.1.spdx.json | e91bc5e96e76e71b306ba9436a1829ffc241dc0f64330a16ac169dac33f20bf1 |
| ninfer-qwen38-rtx5090-v0.6.16-linux-x86_64-cuda13.1.SHA256SUMS | 080ae7b0ffbf51ce99e198e13b99405f0a8c38826b3ba4eae837f8354403e146 |
| runtime-source-1302d639.tar.gz | dbf5a221d99fdcfa315ae880f2fe58744e90f44d139bfc5ab1ded5d8b83c37b2 |

`RTX5090_QUALIFICATION.json` in that directory is the actual content-safe profile
receipt extracted from `option-c-lane-evidence.json.profile`, not an authored gate
substitute. SHA-256: `53800731ac70fcf2a0b1bce5491924bbd4d8d8eb0d464ce34e20589d34afc7fe`.
Selected component-notes SHA-256, recorded after the lead's dry-run:
`a8ddab13e9434abc5e89073f0d1fb85d300dc8be2a8e381a623539c9c0b6dc45`. The notes-only update records the founder's decisions;
the cutter checks notes-file existence, not its prose. Main's preflight pass is
reported separately from this worker's measured Mac notes hash.
[Source](qualification/option-c-source.json) · [Build](qualification/option-c-build.json) ·
[Preflight history and exact commands](qualification/founder-sequence.json).

## Selected qualification — all15 local criteria pass

Full sm_120a ctest: **111 passed, seven skipped, zero failed**,118 total,exit0,861s.
The NVFP4 real batch/serial oracle passes28.7297s; BF16 head0b1/head1b1/head0b2 all
exit0. No failing test was suppressed. The superseded a59 all-green-ctest exception
is **not needed for the selected C source**. This is local lane qualification, not
published-component or documented-route acceptance.

### Exact-binary serial quality binding

An uninterrupted lease compared the same frozen89-case role corpus on C and a59:
**89/89 output signatures and request bodies match**,84 counted cases with0 errors
per arm, five preregistered vacuous fixture errors excluded per the unchanged
EXP-085 rule. This binds C serve `548fe239…` through a59 serve `675e72e6…` to the
measured EXP-094 serve `884e5a43…` serial powered-screen pass. The compared signature
contains content,reasoning,tool calls,finish reason,error and prompt/completion
usage, excluding tool-call IDs only; it is not a whole-HTTP-response identity claim.
No new full powered screen or solo/pair output-invariance claim is made.
[Selected binding](qualification/option-c-output-identity.json) ·
[Original a59→EXP094 binding](qualification/output-identity.json).

### Criteria1–15

| Criterion | Verdict | Unchanged requirement | Exercised C evidence |
| --- | --- | --- | --- |
| 1 | PASS | Clean exact source/build/model/image/config identity; unchanged supported serving shape | source_dirty=false; all13 stage identities match; BF16 K7,131520 KV tokens,2 in flight/2 device slots,180000ms pending |
| 2 | PASS | Precedent-selected CPU/oracle/BF16 tests | 118 total:111 pass/7 skip/0 fail,exit0; NVFP4 oracle passes28.7297s; three direct BF16 checks exit0 |
| 3 | PASS | Quality evidence bound to the exact packaged binary | 89/89 serial signatures and request bodies match a59;84 counted cases,0 errors each;5 preregistered vacuous errors excluded each; no new powered screen |
| 4 | PASS | MTP3 control matches the frozen v0.9.0 production corpus | 89 signatures and request bodies match the frozen v0.9.0 MTP3 control;0 differences |
| 5 | PASS | Exact 130,048-token retrieval, exact 2,048-token decode, agent protocol across restart | 130048-token exact retrieval58.890s;2048 output tokens,179.79server/177.96wall tok/s; deleted descendant404 after restart,no resurrection,survivor restored;VRAM29468/29470MiB |
| 6 | PASS | Actual stock OMP macOS arm64 proof exits 0 | Actual OMP18.8.7, binary cf0227bd…; six checks pass,exit0 |
| 7 | PASS | No chained root prefill above 60K; each long run succeeds or stops at the documented predecessor harness precondition | Three runs:two succeed,plant3 retains documented predecessor precondition; six committed compactions; max root prefill58190;0 roots above60000 |
| 8 | PASS | Quota reclamation and post-crash long continuation retains at least 60K cached tokens | 35 short records;25769803776-byte quota reclaimed;crash exit0;continuation60079 input/60057 cached tokens,2.39s; separate corrected own-container monitor passes |
| 9 | PASS | No workload errors, all stored sessions restored from checkpoints, first shutdown refused 0 | 0 workload errors;4/4 stored sessions restored;8 continuations,0 reuse losses;first shutdown0;ancillary D1=true/D2=false remains non-gate evidence |
| 10 | PASS | Held publication barrier exact restore; shutdown refused0 | Six-second publication barrier hit;resume exact;shutdown refused0 |
| 11 | PASS | Fanout57k/67k,warm-arrival,restore pass; multisession reuse loss≤2/8 | Fanout,restore,warm-arrival and multisession all exit0;reuse loss2/8 within unchanged limit;hot medians0.669/0.790s;restore2.880/2.937s |
| 12 | PASS | Agent mix measured fresh roots0/24 | Fresh roots0/24;continuation roots0/24;errors0 |
| 13 | PASS | Seven C2 scenarios twice all pass; three restart pairs retain≥62404cached each | Seven C2 scenarios × two repeats,14/14 pass;three restart pairs/six sessions each retain62404 cached tokens;0 failed requests |
| 14 | PASS | Actual OMP18.8.7 limits1 then2, same server, amendedPR74 | Actual OMP18.8.7,amended PR74;limits1 and2 naturally dispatch[2],no recovered dispatch;one server;all children/codes/parent checks pass;limit2 overlaps13.614s subagents/4.976s sessions;0 errors |
| 15 | PASS | Server request errors0; shutdown refused≤7 C2probe,0others | All13 stages:0 server request errors;C2probe shutdown refusals7,all others0 |

The selected matrix uses completed C jobs
`20261010T105001Z-S1-option-c-lane-criteria-1-15-1382427` (exit0,4150s) and the
separately frozen criterion8 correction
`20261010T114641Z-S1-option-c-criterion8-own-container-monitor-1418823`
(exit0,325s). Both ended without leftover or unowned containers.
[All15 matrix](qualification/option-c-lane.json) ·
[Numeric evidence](qualification/option-c-lane-evidence.json) ·
[Actual OMP client](qualification/option-c-omp-client.json) ·
[Server logs](qualification/option-c-lane-logs.json).

Retained non-green outcomes are not relabelled green:

- Initial criterion8 exited1 because its frozen disk monitor named the original
  container, not C's own container. A separate frozen own-container correction and
  fresh isolated checkpoint replay passed; the first attempt remains invalid.
  [Harness attribution](qualification/option-c-criterion8-harness.json).
- The Mac bridge exited255 after stock/long completion. Only the unfinished
  parallel phase was resumed and passed; its underlying bridge failure mechanism
  is unmeasured. [Interruption](qualification/option-c-client-bridge-interruption.json).
- Plant3 exited1 at the byte-identical documented predecessor harness precondition
  admitted by the unchanged gate. Six compactions committed across the three runs;
  max computed root prefill58,190,0 above60K.
  [Precondition](qualification/option-c-long-session-precondition.json).
- Ancillary restored desk-code recall is D1=true/D2=false, outside the formal
  durability gate. Multisession reuse losses2/8 meet the unchanged≤2/8 limit;
  seven permitted C2probe shutdown refusals meet the unchanged log gate.

The real macOS arm64 upstream OMP18.8.7 binary is
`cf0227bdefca0c486bd2aed1771de3ab98930266883eb69d341caf5665caee14`.
S2 final follow-on `b622cbda514ce381658f631cdf1ad61b4b89b7bd` is incorporated as
`eaee6d0`, following the rebase onto S2 `38a81628e2fb9e35d5b831610489133a5f5c35e7`.
Its descriptor/hash and candidate provider/client pins are unchanged by selection.

### Measured performance and the cost of omitting3a

C exact retrieval **58.890s** versus v0.10.0 **58.738s**: +0.152s/+0.259%.
Exact2048-token decode **179.79server tok/s** versus **161.39**: +11.40%; wall
**177.96tok/s**. Original a59 measured58.917s/179.79server tok/s. Idle/retrieval VRAM
is29,468/29,470MiB.

Frozen A/B/B/A against a59 measures pair round cost
**19.40783737→21.2215144973ms (+9.3451%)** and aggregate paired wall throughput
**505.40→462.33tok/s (−8.5220%)**. Single-request per-round changes across
0/32K/64K/120K are −0.1409% to−0.0044%; nonce-dependent decode-rate swings are not
attributed to the omission. This does not reproduce EXP-094's traffic-weighted
+9.6% prediction for the original source or promise its original pair speedup on C.
[ABBA receipt](qualification/option-c-abba.json).

## Superseded a59 alternative — red evidence preserved

Exact `a59c13d00492d47dc58bf822533688c90c5d1f6a` is **not selected**. Its original
`$HOME/Desktop/ninfer-v0.6.16-release/` assets and numerical receipts are untouched.
Do not execute its historical cut/stage sequence: both alternatives share the
v0.6.16 component tags. No a59 ctest-policy exception was approved or is required
for C. The following attribution describes the original a59 qualification:

The full sm_120a ctest run returned **8**: **110 passed, seven skipped, one failed**
(118 tests; 865.41 seconds). The failed NVFP4 graph/serial test reports:
“NVFP4 graph batch row differs from its serial NVFP4 oracle.” All direct supported BF16
K=7 checks passed. The earlier eaf221ac release logs did not build that NVFP4 target,
so a shipped-baseline pass or failure could not be inferred from them. Fresh exact
eaf221ac built and passed; fresh exact3a2fadbd built and failed the same assertion.
The first red is therefore3a, before EXP092/094. This is strict generated-TokenId
vector equality, not a floating tolerance. The test does not identify the first
divergent op,row or token. Its ordinary eager C1/T1 oracle differs from graph-enabled
DFlash2K7/C2/T8–16 in more than scheduling. The sole3a runtime change routes
K6144/T16 from MmaResidualR64C16 to Split2ExactResidual; intermediate numerical
mechanism is unmeasured. [Source attribution](qualification/nvfp4-source-attribution.json)
retains both test exits/log hashes and the precise contract. No source fix or
unchanged-test rerun was made.
The Q5 resolver keys the tensor shape, not KV storage; T1 uses residual GEMV while
T8/T16 use the small-T MMA on sm120. The new T16 route matching T8 is not an exact
T1-oracle guarantee. Different arithmetic paths changing greedy TokenIds is an
inference, not a measured first-op mechanism or evidence of cross-row state corruption.

All15 original predecessor lane gates passed separately from that full-suite red;
[original build](qualification/build.json) and [original lane](qualification/lane.json)
retain their own source/binary, numbers and failure disposition. The initial original
criteria10–14 were invalidated by the lead's external Docker stop, not a candidate
fault; the corrected lease exit0 and invalid attempt remain preserved in
[external-stop attribution](qualification/external-interruption.json).

Five-case BF16 solo/pair controls on a59 and shipped eaf221ac both found1/5 signatures
identical and4/5 different, with real two-row execution and0 errors. Supported-profile
scheduling dependence pre-exists EXP094; this neither proves the NVFP4 numerical
mechanism nor makes a solo/pair-invariance claim for C.
[Shipped control](qualification/bf16-solo-pair-shipped.json) ·
[a59 control](qualification/bf16-solo-pair-candidate.json).

## Release tooling

- Enumerate exactly v0.6.16, not a wildcard, in the runtime-tag verifier. The focused
  allowlist regression passed.
- The promote_root bug was real: upstream root clients all received the primary
  Windows asset. The new per-platform selection preserves full Darwin/Windows
  distribution metadata; the regression was observed red before and green after.
- The verifier now checks the same platform-specific archive pins. Its six focused
  upstream tests passed; legacy fork archive checks are intentionally unchanged.
- Staging's sole obsolete diagnostic consumer was migrated; a public-root draft
  regression was red before and green after. The candidate-relabelling security
  regression also passed. Full repository verification belongs to the existing
  Ubuntu/Python 3.11 draft-PR CI.
The initial draft commit a1379e45b66abb4016f4a63eb097bc34d3cefe94 passed the
full workflow in [CI38042843797](https://github.com/alphastorm/omp-ninfer/actions/runs/38042843797).
That result precedes the final S2 follow-on and is not a final-head substitution.
The follow-on exposed the staging regression fixture's legacy OMP18.3 descriptor
with a modern per-model provider contract; CI38043597806 retained that failure.
The fixture now uses its real legacy environment and explicitly asserts both
platform draft-pin diagnostics, without weakening the provider verifier. The
corrected code/test head d7e32dd0908fb1b16ace1e0ac5dec1108740b936 passed all
workflow steps in [CI38043955727](https://github.com/alphastorm/omp-ninfer/actions/runs/38043955727).

The post-cut root-marker regression was red only on the two unbound-client markers
before the fix and green after (five focused rebind tests). The actual root lane cut
and full v0.11.0 `--require-installable` CLI pass. The local full suite exercised347
tests twice: initial17failures/2errors, then4Mac timing failures/1obsolete fixture
error; that duplicate fixture setup was removed and its focused test passed. Main
reports the same timing failures for S2 on untouched Mac code with Ubuntu/Python3.11
CI passing: no timing threshold or probe was changed. Final-head CI is authority.
[Complete local failure disposition and lane cut](qualification/root-lane-cut.json).

## Founder sequence — selection/cut/stage/lane/5090 complete → native/composition pending

C selection, source publication and the founder's live component cut are complete.
Staging and lane rebind are now authorized agent steps; only the product live
publisher remains founder-only. **RTX5090 routes passed; native/composed acceptance
remains pending.** Evidence-only follow-ons do not change the5861712f candidate.
The exact selected-source sequence and historical refusals are in
[founder-sequence.json](qualification/founder-sequence.json).

### 1. Founder-only live component cut

This completed founder-only command is **not to be rerun by an agent**. Main reports
the live cut at13:46Z and successful image workflow. Selected C inputs were:

```bash
PATH="/opt/homebrew/opt/python@3.13/libexec/bin:$PATH" \
NINFER_RUNTIME_DIR="$HOME/Development/ninfer-S1" \
bash scripts/hosts/cut-ninfer-5090-component.sh \
  --version v0.6.16 \
  --commit 1302d63929e400a05e1c9cdb0fc8003a70269825 \
  --assets "$HOME/Desktop/ninfer-v0.6.16-option-c-release" \
  --archive-sha bed8c8d4f8ccb8fcf8276248d772c0b9c0f98b1e51c58820ff1f698b66d6fcbd \
  --sbom-sha e91bc5e96e76e71b306ba9436a1829ffc241dc0f64330a16ac169dac33f20bf1 \
  --source-archive-sha dbf5a221d99fdcfa315ae880f2fe58744e90f44d139bfc5ab1ded5d8b83c37b2 \
  --beta 1 \
  --notes-file "$HOME/Desktop/ninfer-v0.6.16-option-c-release/NINFER_RELEASE_NOTES.md"
```

The published [runtime receipt](qualification/runtime-publication.json) supplies the
real image digest below. Main independently pulled it anonymously and checked serve
SHA548fe239; this worker did not repeat that measurement. Never use the local image ID.

### 2. Stage with the verified OMP18.8.7 descriptor

The following staging command was executed under Main authorization, after preserving
the complete draft outside `releases/`. Its actual selected C profile gate receipt is
not the authored15-criterion wrapper. Initial exit1 was the missing supplemental
option-C link; restoring supplements and draft rebinding resolved it (exit0). Do not
restage this existing destination. [Staging receipt](qualification/staging.json):

```bash
V011_DRAFT_BACKUP="$(mktemp -d "${TMPDIR:-/tmp}/omp-ninfer-v011-draft.XXXXXX")/v0.11.0"
mv releases/v0.11.0 "$V011_DRAFT_BACKUP"
/opt/homebrew/bin/python3.13 scripts/stage_release.py \
  --from v0.10.0 --release v0.11.0 \
  --release-tag v0.6.16-qwen38-5090-beta.1 \
  --source-tag v0.6.16-qwen38-5090-source.1 \
  --source-commit 1302d63929e400a05e1c9cdb0fc8003a70269825 \
  --binary-sha 548fe239a3f2f97c98d864b4a7b9c6beb1263788633f1a4bf13c101f2beecace \
  --archive-sha bed8c8d4f8ccb8fcf8276248d772c0b9c0f98b1e51c58820ff1f698b66d6fcbd \
  --source-archive-sha dbf5a221d99fdcfa315ae880f2fe58744e90f44d139bfc5ab1ded5d8b83c37b2 \
  --sbom-sha e91bc5e96e76e71b306ba9436a1829ffc241dc0f64330a16ac169dac33f20bf1 \
  --image-digest "sha256:6a02feba4163d992cc6a46baf28e0ece2ffe6a2ead91939e566c1b3080f5bc02" \
  --runtime-receipt-release v0.6.16-qwen38-5090-runtime-beta.1 \
  --config-sha 91a3567002a43025876e811597353764b20e32f0818bcb6c582a5072c96d7e11 \
  --lane-receipt "$HOME/Desktop/ninfer-v0.6.16-option-c-release/RTX5090_QUALIFICATION.json" \
  --omp-component docs/measurements/2026-10-10-omp-1887-client-components.json
```

Descriptor SHA-256:
`728f6c4486ae7ebf5d7d7b6033b1307d55edc1fbc4f8748de6e689aadb4bd4e9`.
Merge selected-source notes and supplemental receipts without overwriting generated
manifest/qualification/compatibility bindings. Freeze and publish the lane evidence
commit, then bind it:

```bash
/opt/homebrew/bin/python3.13 scripts/rebind_release.py --release v0.11.0 --stage lane --pin "${V011_LANE_COMMIT:?published frozen selected-source lane commit}"
```

The root `status:candidate` marker denotes a client not bound by the release it
names. The lane stage consumes it only after an upstream-release manifest replaces
that profile's client wholesale from its release compatibility copy. Non-promoted
markers still refuse installation. The manifest itself stays candidate, with the
external-install blocker and no acceptance claim until the real ready transition.

### 3. Published-image acceptance window

This step completed on frozen5861712f with green candidate CI and actual measured
rollback inputs. The following controller template is retained for audit, not a
request to rerun the accepted window. S1 copied evidence only and ran no acceptance
action. Never resume/relabel the failed65b6c426 window or attach its3090 pass to
the accepted candidate. All remaining native acceptance continues to bind5861712f:

```bash
acceptance=(
  /opt/homebrew/bin/python3.13 scripts/hosts/accept-rtx5090-routes.py
  --release v0.11.0
  --candidate 5861712f561ff0b3100dd4350e02d777a3f5007e
  --workspace "${V011_MAC_ACCEPTANCE_DIR:?fresh private Mac evidence directory}"
  --wsl-workspace "${V011_WSL_ACCEPTANCE_DIR:?fresh absolute private POSIX evidence directory}"
  --windows-workspace "${V011_WINDOWS_ACCEPTANCE_DIR:?fresh absolute C:/ private evidence directory}"
  --production-image "${RTX5090_INCUMBENT_OCI_IMAGE:?actual measured incumbent rollback image}"
  --wsl-host "${RTX5090_WSL_SSH:?verified POSIX SSH destination, not an assumed alias}"
  --windows-host "${RTX5090_WINDOWS_SSH:?verified Windows SSH destination}"
  --route-ssh-destination "${RTX5090_DOCUMENTED_SSH_DESTINATION:?actual documented route destination}"
)
"${acceptance[@]}" --action preflight
"${acceptance[@]}" --action window
```

The independent watchdog/restoration measured the completed founder-controlled
window; no restoration action is repeated here. **Do not compose yet.** After
RTX4090 acceptance and the explicit RTX3090 scope/acceptance decision, Main may
compose receipts for every retained route on5861712f, then platform/acceptance/
manifest pins and `--require-ready --check-pins` before the founder-only product cut.

### Explicit remaining blockers

1. **Product acceptance:** the component is published and Main's anonymous pull
   binds the exact548fe239 binary. The5090 routes/clients now passed on5861712f,
   but native/composed readiness and permission to publish are still absent.
2. **Native RTX4090:** retained in v0.11.0, pending fresh OMP18.8.7 qualification
   on the founder-designated replacement host after today's planned installation.
   The former no-host retire/hold decision is superseded, not a release-scope cut.
3. **Native RTX3090:** the predecessor65b6c426 pass is preserved but not composable.
   Await the founder's decision: reinstall/re-accept on5861712f versus drop the
   lane from v0.11.0. No drop is implemented in this evidence-only commit.
4. **Composition:** deferred until the remaining retained native routes qualify
   on5861712f. An evidence-only commit does not become a new subject. Current
   candidate/external-install blockers remain; no platform/acceptance/manifest
   promotion is performed merely because the5090 slice passed.

The selected C source has no unresolved ctest-disposition gate. Historical a59 red
and invalid outcomes remain preserved, not hidden or relabelled. Public receipts
omit raw prompts, generated content, secrets, private hostnames and absolute private
paths; lease identifiers and exact identity hashes are retained.
