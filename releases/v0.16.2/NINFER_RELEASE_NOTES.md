# OMP NInfer v0.16.2 — durable-export Host reclaim and stock OMP 18.15.0

## Qualified successor scope

This is the qualified runtime-and-client successor to published **v0.16.0**, not a release of
the held v0.16.1 client-only candidate. Published installation remains **v0.16.0**; use its
[immutable guide](https://github.com/alphastorm/omp-ninfer/blob/v0.16.0/docs/QUICKSTART.md)
until founder-owned publication of this release.

The bound composition is RTX 5090 `v0.7.0-qwen38-5090-beta.5`, native Windows RTX 3090 and
RTX 4090 `v0.8.0-qwen38-{3090,4090}-beta.2`, and unmodified upstream **Oh My Pi 18.15.0**.
All runtime components bind source `a87de3613c17bced777b446fb545f872d8395ec1` on upstream
`64d10fbf9f8e6bfc79ab0570b94674c5b9997929`. All three components are published; both native
15-phase qualifications, quality screens, fit proofs, no-regression speed gates and separate
upgrade/rollback/repair rehearsals are bound to their actual subjects below. The three exact
founder-waived agent positions retain their failed measurements. No predecessor runtime,
client execution, product-route acceptance, review approval or waiver transfers to these bytes.

The shared published model v3 and serving shapes stay unchanged. The RTX 5090 keeps deployment
profile `qwen38-5090-v0.13.0`, configuration `751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47`
and `/checkpoints-v013`. Native version/instance identities advance to beta.2, without changing
the serving policy. A retained profile name is not cross-binary checkpoint compatibility: keep
old roots untouched and replay the authoritative OMP transcript for a fresh prefill.

## Runtime changes since v0.16.0

The [published RTX 5090 component notes](https://github.com/alphastorm/ninfer/releases/tag/v0.7.0-qwen38-5090-beta.5)
and [complete engine delta](https://github.com/alphastorm/ninfer/compare/26fa28d0e7834515508fc07ac503164a6effc820...a87de3613c17bced777b446fb545f872d8395ec1)
are the source authorities, not the v0.16.0 measurements.

- **Reclaim before refusing durable export.** When Host checkpoint capacity would refuse an
  export, reclaim redundant resident Host state only for generations byte-proven on durable
  storage and protected through publication. This addresses
  [the Host-capacity reclaim issue](https://github.com/alphastorm/ninfer/issues/78) through
  [the implementation and remediations](https://github.com/alphastorm/ninfer/pull/82)
  (`aa9023f5`), including the managed-Stop incomplete-shutdown failure after a capacity-refused
  final save. It does not promise that every save succeeds under pressure, or that a crash
  preserves work that was never saved.
- **Reserve export retirement before taking the export lease** (`aaf6c2d0`,
  [#68](https://github.com/alphastorm/ninfer/pull/68)).
- **Align the opt-in FP32 head's durable checkpoint identity with the runtime identity**
  (`382a15fa`, [#67](https://github.com/alphastorm/ninfer/pull/67)). FP32 head logits remain off
  in the release profiles; this is not an opt-in or performance claim.
- **Make bounded relocatable-device-code builds deterministic** (`49d268d4`,
  [#69](https://github.com/alphastorm/ninfer/pull/69)). The new exact-source double-build result
  below replaces, rather than inherits, the old RTX 5090 reproducibility exception.
- **Native repair and power ownership:** refuse unreadable repair-census executable images
  (`58a5b258`, [#63](https://github.com/alphastorm/ninfer/pull/63)) and restore a prior paused
  owner's power before uninstall (`f25ea97b`, [#65](https://github.com/alphastorm/ninfer/pull/65)).
  Both new native packages have current hardware qualification; product-route acceptance remains
  a separate obligation.
- **Use state-bound qualification and upgrade-rehearsal drivers**, including failure-ordering,
  cleanup-ownership and probe corrections ([#70](https://github.com/alphastorm/ninfer/pull/70),
  [#73](https://github.com/alphastorm/ninfer/pull/73),
  [#79](https://github.com/alphastorm/ninfer/pull/79),
  [#80](https://github.com/alphastorm/ninfer/pull/80)). The concurrent-endpoint protocol fix
  (`e2953135`, `f870491d`, [#62](https://github.com/alphastorm/ninfer/pull/62)) is now in the
  source; the historical RTX 3090 protocol-tool override is not carried forward.

The delta also labels bounded CTest host tests, pins CUDA CI to Ubuntu 24.04, adds packed-page
true-cold diagnostics and preregisters round-selective DFlash2 recovery research. These are not
adoption of `rk4v4`, a larger context, a changed speculative backend or a new serving feature.
Native package metadata advances to `0.8.0-beta.2` in `a87de361`
([#85](https://github.com/alphastorm/ninfer/pull/85)).

## Published RTX 5090 identity and component qualification

| Binding | Exact identity |
| --- | --- |
| Binary release | `v0.7.0-qwen38-5090-beta.5` |
| Source release | `v0.7.0-qwen38-5090-source.5` |
| Source | `a87de3613c17bced777b446fb545f872d8395ec1` |
| Binary archive SHA-256 | `26b5c1e2b2b9dc48007860ebefddafc4d37b5e264ba972f8b4902444a28a382d` |
| SPDX SHA-256 | `3ecc58adb355cc6790add313aa701da86d52df78103d4b7f5d3ab831dd0545de` |
| Source archive SHA-256 | `2f0b68e492c7e7e87c9c31311b7cae8085f5b2906c3705cade8692b8b7531e94` |
| `ninfer-serve` SHA-256 | `cc99a46097b6da5f9ec3ce671a7818d29754013ba520800f756110b9211bb06e` |
| Runtime image | `ghcr.io/alphastorm/ninfer-runtime@sha256:a0cbb8a5f933ec8aeec9a7defa07d78a835c1093d1d98f5f842267287efa3f71` |
| Image receipt release | `v0.7.0-qwen38-5090-runtime-beta.5` |
| Runtime-base receipt release | `runtime-base-a87de361-20261103` |

The component's published qualification reports CUDA 13.1 / GCC 13.3 / `sm_120a`, **66/66**
historical host tests, **11/11** dense real-model tests, **1/1** durable pressure overlap and
**44** current host contract tests, without failures or skips. It also reports the four-boot
restart restore, product-shape gate, exact release profile, product smokes and the help inventory
(**60 flags**, unchanged from beta.4), with **146,368** startup KV tokens. A separate same-path
double build matched **661 build artifacts and all 3 package outputs** bit for bit.

These are component-build/RC observations, not a published-image lane receipt, a reclaim-latency
measurement, native Windows qualification or product-route acceptance. These component reports
do not assert a new token-rate, restart-latency or reclaim-cost result.

The separate [published-image lane receipt](qualification/rtx5090.json), SHA-256
`bfd0ec1a76c323adf3f58a176112b0731694e7ce69b62aebbf05093cf59a2f22`, passed on the
published beta.5 image on 2026-11-03. It binds the source, server, model and retained
configuration above. The separate agent campaign judged **88/88 positions** (72 same-subject
carried positions and 16 corrected positions), accepted only under the exact `restore_0` waiver
below; strict parity remains failed. The stock checkpoint-request census completed with **0**
ordinary checkpoint POSTs, and cleanup/restoration were verified. The overall corrected-run
record still says failed because it retains an operator `PermissionError`; the bound
[observed gates](qualification.json) distinguish that record from probe judgment and do not
assert an overall-run or product-route pass.

## Exact-subject founder waivers — original failures retained

- **RTX 5090 first-request-after-restart TTFT (founder waiver on two-restart `restore`):**
  Position **3**, `restore_0`, on `v0.7.0-qwen38-5090-beta.5` exceeded the per-position
  TTFT bound `incumbent + max(0.25 s, 25%)`: **0.481856409 s** candidate versus
  **0.231568998 s** incumbent and a **0.481568998 s** bound, an excess of
  **0.000287411 s**. That measured failure was **waived by the founder with disclosure**
  ([waiver](qualification/rtx5090-restore-position-waiver.json)); it is not rewritten as a measured
  pass. Every oracle passed and `cached - prompt` was equal at **−48 / −48**.
  This waiver applies only to that one failing position with exactly these values.
  Every other gate remains binding; all 88 campaign positions have now been judged.
- **RTX 4090 restore cache-gap waiver:**
  On the now-authenticated and published `v0.8.0-qwen38-4090-beta.2` package, two-restart `restore` position
  **4**, `restore_1`, recorded `cached - prompt` **−52** candidate versus **−48**
  incumbent, below the rule `candidate >= incumbent`. Candidate prompt/cached tokens
  were **58,539 / 58,487**, versus incumbent **58,327 / 58,279**. Server TTFT was
  **0.642947 s** candidate versus **0.5589493 s** incumbent and stayed within its bound.
  The [founder waiver](qualification/rtx4090-restore-position-waiver.json) covers only this
  cache-gap failure: **82/83** positions measured pass, one failed and was waived. The original
  pre-cut measurement is bound to the identical subsequently published package, not relabeled
  as a public-URL install.
- **RTX 3090 sibling first-request TTFT waiver:**
  Sibling probe position **1**, labeled **`base`**, measured **0.4975294 s** candidate versus
  **0.2144353 s** incumbent, above the unchanged **0.4644353 s** bound by **0.0330941 s**.
  Both arms used **66 prompt / 0 cached tokens**. The
  [founder waiver](qualification/rtx3090-sibling-position-waiver.json) covers only that failure:
  **82/83** positions measured pass, one failed and was waived. The waiver record's
  `sibling1` shorthand denotes position 1, not the later position labeled `sibling_1`, which passed.

Both native comparisons use hash-proved reused captures from the published beta.1 incumbents,
not fresh paired incumbent runs. All original verdicts, thresholds and measured values remain
unchanged; a different failing set or value is outside these waivers. The content-safe projections
omit private execution identifiers and bind the original founder records by SHA-256:

| Founder record / public projection | Original record SHA-256 |
| --- | --- |
| [RTX 5090 restore waiver](qualification/rtx5090-restore-position-waiver.json) | `b8dac132b30d874a3112bdd2064f07dba961c234dec854ea430f8f4ca7b5a231` |
| [RTX 4090 restore waiver](qualification/rtx4090-restore-position-waiver.json) | `01168224aa581cc45cd4fc8505c247c8497180f3e1439e6607b497befed9ee44` |
| [RTX 3090 sibling waiver](qualification/rtx3090-sibling-position-waiver.json) | `edc7f2265c4b30348054cb5c960c4f43c4013ee6a90ac8ec9db4f67ba67c5f5e` |
| [Native no-regression speed decision](qualification/native-speed-decision.json) | `3d9f77cd5a7099b68ec59c8f7ca56765317a9ee7352c3a6705a755fe5902b104` |
| [RTX 4090 rehearsal-harness decision](qualification/rtx4090-rehearsal-harness-decision.json) | `c169000bc662526c7097e9ddd3fa38afd7d7db6a580aff2b5dd3108b4e09e0c7` |

## Published native beta.2 qualification and no-regression evidence

The [native publication receipt](qualification/native-publication.json) binds both published
beta.2 cuts, each with a closed **10-entry checksum set / 11 distribution files**:

| Lane | Package SHA-256 / bytes | Server SHA-256 | Public configuration SHA-256 |
| --- | --- | --- | --- |
| RTX 3090 | `97a8e6340397d6a925cbabc6ffbb6f219a4b00f19b2f5d8e4be6cd14d41f3ed9` / 1,008,989,809 | `15a4db46db09dce695f1c55a9996b30408fa93ed864d881872f9ae7306fbab0f` | `238ccad7ba6dca673d845c183b6c3de3a49bd2ce75090f20f669b2d6f83dda6f` |
| RTX 4090 | `d9b10b47f1e7fad8413dc95347dbdd11d91636aec11552c29c1dc94246ca6d5b` / 991,981,865 | `ffee91bf17c261ae9b85791fc52528f7f1ef5c985c4d55feb7ee65174c96c73d` | `ae27dc446634048cec913fd42efc5971fb0ad950eed154ecce6aaa981eec4c9b` |

Both [RTX 3090](qualification/rtx3090.json) and [RTX 4090](qualification/rtx4090.json)
completed their **15-phase native chain**. Those managed chains ran isolated packages differing
only in `listen.port`, not the public port-18082 packages; the scratch-lineage rollback remains
`not_applicable`. Separate quality and predecessor-upgrade scenarios used the public packaged
port. Neither proves the later candidate-bound public-URL product install.

The current **1,120-prompt powered quality screens**
([RTX 3090](qualification/rtx3090-windows-native.quality-screen.json),
[RTX 4090](qualification/rtx4090-windows-native.quality-screen.json)) pass all primary bounds
with **zero paired metric difference** against published beta.1, and both arms have **80/80**
fresh-cache determinism with no missing or errored samples. Zero difference is not a claim of
zero secret leakage. The authenticated release-local fit proofs are also bound.

The founder-selected speed rule is **no regression against published beta.1**:
role-weighted and all-case-weighted decode ratios **≥0.98**, **every case ≥0.95**, and
byte-identical normalized outputs in all required within-build and cross-build ABBA pairings.
This explicitly supersedes the earlier **1.08** weighted speedup floor inherited from the
prior MTP3-to-DFlash2 comparison; it is not a retroactive pass under that superseded rule.

| Current speed gate | Weighted decode ratio | Minimum case | Byte-identical normalized outputs |
| --- | ---: | ---: | ---: |
| [RTX 3090, 84 depth-0 role cases](qualification/rtx3090-speed.json) | **1.0003** (1.0002518490) | **0.9988** (0.9987703200) | **84/84** |
| [RTX 4090, 108 role + 7 supplemental cases](qualification/rtx4090-speed.json) | **0.9996** (role 0.9995778248; all 0.9996281435) | **0.9989** (0.9988670028) | **115/115** |

Both pass that rule without a speed waiver. These are same-backend no-regression results,
not a new speedup, reclaim-cost or general latency claim.

Separate **running-upgrade / forced-start rollback / interrupted-install repair** rehearsals
passed and restored on both native lanes (**3/3 scenarios each**), bound in
[observed gates](qualification.json). RTX 3090 used the unmodified source harness. RTX 4090 used
a founder-approved private `Invoke-UpgradeRehearsal.ps1` copy changing **only uncapped-power
assertions** to require `outer.qualified_power_limit_w == 0` and
`Power() == owner_power_limit_w`; every other assertion was unchanged. The original harness
SHA-256 is `0e673f07a9458d5b6440b8255d925141ab689cb0cdcd0cdb79f98680b7f4f710`.
This is a disclosed qualification-harness fix, not a change to the shipped runtime or a weakened
product gate. Follow-ups remain [runtime-council deferrals #87](https://github.com/alphastorm/ninfer/issues/87)
and [native tooling defects #88](https://github.com/alphastorm/ninfer/issues/88); neither issue
substitutes for the exact-subject review ledger or candidate-bound acceptance below.
The three per-scenario summary receipts are **lane-agnostic**, despite separate capture;
GE-R1 binds each lane's distinct running/rollback/repair evidence-archive digest for provenance.
It does not requalify archive contents or change raw verdicts.

## Stock OMP 18.15.0

The selected upstream release is
[`can1357/oh-my-pi v18.15.0`](https://github.com/can1357/oh-my-pi/releases/tag/v18.15.0),
release **430630500**, source `3fedf8d53267e32a6d7521ce725fdcc4a36fdc67`, tree
`48bc72ba2418c0b78163d9769e91a0d8683e642b`. Its raw asset and executable hashes are identical:

| Platform | Asset / ID | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| macOS arm64 | `omp-darwin-arm64` / `698539455` | 215295120 | `d36dfabf0ee52d6f08efadb59c46f0349545c6f6975522417adae29646e73e34` |
| Windows x64 | `omp-windows-x64.exe` / `698539443` | 243250176 | `978846a816cb77f44a55e32b16493375ca837fbf87e0aec35a9c1c934bff0cd0` |
| Linux x64 | `omp-linux-x64` / `698539441` | 276785328 | `6737ee2415555a3656cc7b89c14d1c25c18658ee4c0fd4f7309705149ccb7b0f` |

The [18.14.0→18.14.2 review](../../docs/measurements/2026-11-01-omp-18142-client-upgrade-review.json)
and [18.14.2→18.15.0 review](../../docs/measurements/2026-11-01-omp-18150-client-upgrade-review.json)
cover the client source delta and independent asset integrity, not new live acceptance.

- Keep Qwen exact-loop detection enabled. Short newline-spanning cycles require four repeats
  covering **1024** characters; short non-newline cycles retain four/**180**, long cycles
  three/**1024**. Remove obsolete operator `compat.thinkingLoopGuard`, not `model.loopGuard`.
  Clear `PI_NO_THINKING_LOOP_GUARD` and `PI_OPENAI_STATEFUL`.
- Keep the three supported per-model compatibility keys: `compat.statefulResponses: true`,
  `compat.includeEncryptedReasoning: false`, `compat.supportsReasoningSummary: false`.
  Preserve static selectors, high→medium/off→low effort clamps and `qwen3.8-27b` replace /
  `q38-ninfer` hashline edit defaults. No discovery, service-tier or per-call-model opt-in is added.
- Length-stopped main, turn-prefix, handoff and branch summaries fail visibly without committing
  partial context. A completed main summary survives a truncated display-only short summary.
  Default reserve stays **19660**, trigger strictly **>111412**, full-summary cap **15728**
  rather than the route's **32768** output limit. Manual compaction waits for persistence
  replacement before queued background results can start a turn; failure/cancellation and restart
  continuation still require their own observations.
- Replay transport copies strip only `internal_chat_message_metadata_passthrough`, preserving
  legal metadata, content and linked tool pairing without rewriting stored history. Snapcompact
  reader accounting adds no native/Linux vision scope or context expansion.
- Keep explicit `retry.enabled=false`, `retry.modelFallback=false`, `fallbackRevertPolicy=never`.
  The retry opt-out alone does not gate the new pre-prompt missing-key fallback. Selected-provider
  outage remains a failed turn, without model content/provider switch and with original request
  counts. Optional background captions can select smol credentials independently; acceptance
  requires isolated local-only auth and separately attributed optional side requests.

## Retained model, serving policy and upgrade boundary

The shared model remains published container v3, **20,437,521,664 bytes**, revision
`1cbd84e7221e51186bd7f093a149912d2489625b`, SHA-256
`81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da`.

| Lane | Retained serving shape |
| --- | --- |
| RTX 5090 | BF16 KV, DFlash2 K7, 131072 context, 146368 automatic KV tokens, C2 plus two extra device-state slots, 180 s pending timeout, strict-origin `/checkpoints-v013` |
| Native RTX 4090 | INT8 DFlash2 K7, 131072 context, C1, two extra slots, 640 MiB admission headroom, 16512696320 B shared Host budget, 30 s pending timeout |
| Native RTX 3090 | INT8 DFlash2 K7, C2 over one 131072-token pool, two extra slots, 768 MiB headroom, 21881405440 B shared Host budget, 180 s pending timeout, 350 W serving cap |

Native lanes remain UUID-bound and serve sequentially on port **18082**. `Group64` A8 and FP32
head logits stay off. Running-lane upgrade, forced-start rollback and interrupted-install repair
have current beta.2 evidence as scoped above; no historical stop-first workaround is reintroduced.
For the container upgrade, stop an incumbent with the matching published v0.16.0 stop script,
not a successor script whose product identity differs. The v0.16.1 client-only instruction to
keep the running container is inapplicable because this release changes the server binary.

The [v0.16.0 notes](../v0.16.0/NINFER_RELEASE_NOTES.md) retain their original measurements and
waivers: RTX 4090 `log-024@0` speed, two RTX 5090 first-request-after-restart latency misses and
the RTX 5090 second-build exception. None is renewed for v0.16.2 by copying its receipt.
The [receipt audit](qualification/receipt-audit.json) replaces the quarantined beta.1 native
subjects with authenticated current beta.2 bytes. Both native rows are qualified/installable for
the lane candidate; runtime eligibility does not grant public product acceptance or publication.

## Fresh candidate-bound route and client acceptance

On **2026-11-04**, frozen product candidate
`c6fc8465611a89fd85730f0653f670d2a314a721` passed all five documented routes and their
**31/31 executable blocks**. The composition retains the original passed route receipts,
including the narrowly declared candidate-instead-of-tag substitutions, without changing any
executed block. All three exact stock OMP **18.15.0** clients were freshly downloaded,
hash-checked and exercised against the rebuilt candidate runtime identities.

| Route / additional acceptance | Actual result |
| --- | --- |
| RTX 5090 container host | **2/2 blocks passed** |
| macOS arm64 over manual SSH | **10/10 blocks passed**, tool/continuation/restart/fail-closed and image input; preview |
| Native Windows x64 against RTX 5090 | **5/5 blocks passed**, tool/continuation/fail-closed and image input |
| Linux x64 against RTX 5090 | Fresh structured tool/continuation/fail-closed acceptance under **WSL2 only**; no native Linux OS or Linux vision claim |
| Native RTX 4090 | **7/7 blocks**, native campaign, C1 fleet probe, public-URL install and independent restoration **passed** |
| Native RTX 3090 | **7/7 blocks passed**; four-way fanout under C2, both stock OMP parallel-proof scenarios at limit 2 and two committed automatic-compaction/control-recall epochs passed; later campaign **failed**, founder-waived as disclosed below |

Receipts: [documented routes](acceptance/documented-routes.json),
[composed external installation](acceptance/composed-external-installation.json),
[RTX 4090 public install](acceptance/rtx4090-public-install.json), and
[independent restoration](../../docs/measurements/2026-11-04-v0162-acceptance-restoration.json).
The RTX 4090 public installer returned `already_installed`, accepted the exact current package,
server and configuration bytes, and changed no lifecycle pointers; its start/smoke/stop restored
the prior stopped state and **450 W**. Both native documented routes are first-lineage:
rollback `not_applicable`, zero directions, not the separate 3/3 predecessor rehearsals.

The RTX 5090 **accepted hold and all-attempt total are both 418.529 s** (one window).
Independent closure retained the same healthy production container and digest-pinned image,
`unless-stopped`, identical checkpoint mounts and healthy unreserved fleet service; temporary
route container, hold, key/checkout changes and documented directories were undone.
RTX 4090 campaign elapsed/hold time was **512.5491440296173 s**; the failed RTX 3090 campaign
elapsed **1294.0950541496277 s**, not a successful restored hold. The completed RTX 4090
cross-lane census matches its pre-window baseline; the subsequent RTX 3090 recovery has its own
binding, not an invented final campaign-wide census.

### RTX 3090 failed native campaign and operator recovery

After all seven documented blocks passed, the separate **structured-outage managed Stop**
returned **`graceful_incomplete_shutdown`**: **saved 1 / skipped 8 / refused 1**,
**shutdown complete false**, final durable-save reason **capacity**, **reclaimed Host bytes 0**.
The [founder waiver](qualification/rtx3090-route-waiver.json) binds the original failed driver,
window-failure, final audit and preserved shutdown evidence. The native campaign stays **failed**;
external installation is **waived-by-founder**, not passed. **Behavior completion, a passing
wrapper restoration audit and anonymous public-install acceptance are not claimed**; no RTX 3090
public-install receipt is authored.

This is the remaining export-side capacity residual of [fork #78](https://github.com/alphastorm/ninfer/issues/78)
after #82, also present in the published beta.1 runtime. Published v0.16.0 avoided it only by
timing, not by a stronger completion guarantee. The refused session loses only warm restore;
the authoritative OMP transcript remains replayable for a fresh prefill.

The operator preserved the failure evidence, then used **`Control-Release.ps1 -Action Start`**
followed by **`Control-Release.ps1 -Action Stop` with no client sessions**. That empty Stop was
**graceful**, refused **0**, removed the runtime record and GPU-owner lease, restored **370 W**,
left native tasks **Ready**, and left **no server process or port-18082 listener**.
This lead recovery is not a passing wrapper restoration audit or a rerun of acceptance.
Track [export-capacity residual #89](https://github.com/alphastorm/ninfer/issues/89) and
[incomplete-Stop owner restoration #90](https://github.com/alphastorm/ninfer/issues/90).

## Exact-subject review and publication boundary

The runtime **full council** `CR-20261103T055202Z-a87de361` closed on exact source
`a87de3613c17bced777b446fb545f872d8395ec1`. The **focused product-tooling review** closed by
accountable-lead disposition on frozen candidate `c6fc8465`; a separate focused review of the
waiver tooling on `ff0f3811` closed by lead verification of fixes in `3ad37ea8`.
These are not two full product councils, and no later executable subject is silently substituted.
The [review ledger](review/runtime-ledger.json) preserves original reviewer findings/severities,
resolver standing, source digests and distinct lead dispositions.

Composition applies **GE-R1** lane-distinct archive provenance beside lane-agnostic summary
receipts and **GE-R4** stock-client source/download-review and descriptor binding.
That source/integrity review is not live-client acceptance. Remaining product items use the
existing [product follow-up #138](https://github.com/alphastorm/omp-ninfer/issues/138);
runtime/native follow-ups remain fork [#87](https://github.com/alphastorm/ninfer/issues/87) and
[#88](https://github.com/alphastorm/ninfer/issues/88), alongside #89/#90 above.
Review approval is separate from the runtime finalization controls and immutable-pin checks.
No review, component publication or local qualification grants founder-owned product publication;
checked-in publication and independent public-user acceptance authority remain **false**.

macOS remains manual-SSH preview; Linux remains WSL2-scoped, not native Linux OS qualification.
Vision remains macOS/Windows against RTX 5090 only. No native/Linux vision, RTX 4090 C2, smaller
host, checkpoint migration, multi-owner proof, SLA or general performance claim is added.
