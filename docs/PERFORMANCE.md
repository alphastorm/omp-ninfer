# Performance program

The shipped profile is the floor, not the ceiling. This page is the public working surface for
kernel and schedule optimization on the three qualified RTX runtime lanes: measured baselines, the
profiling lane, an auditable ledger of what has been tried, and the open ideas backlog.

Ground rules:

1. **Contracts before speed.** Every optimization must preserve the numerical and state contracts
   of the supported profile (exact-output oracles, stateful Responses semantics, Vision, thinking
   preservation).
2. **Receipts before claims.** A result exists when its profiling packet or benchmark report is
   preserved with the exact source identity that produced it.
3. **No silent rebinding.** No optimization result becomes a product claim until its exact binary
   and profile are rebound through a new release qualification
   (see [`RELEASES.md`](RELEASES.md)).

Kernel and runtime changes land in [alphastorm/ninfer](https://github.com/alphastorm/ninfer)
(a downstream fork of [Neroued/ninfer](https://github.com/Neroued/ninfer)); this page tracks the
program so contributors can see the state of play in one place.

## v0.19.0 — bounded pressure saves, RTX 3090 `beta.4`, and stock OMP 18.20.0

Published release **v0.19.0** (2026-11-13) rebuilds the RTX 5090 container runtime
(`v0.7.0-qwen38-5090-beta.8`, image `c3ec151b` on reused base `28857182`, server `147da36b`,
isolated host checkpoint directory `checkpoints-v019`) from frozen fork source `41f89b31`
(`41f89b310b443481db5917a01a2b45e49f85e723`: fork `main` `8b3f498f` bounded pressure saves in
[fork #122](https://github.com/alphastorm/ninfer/pull/122) plus a test-only fixture correction and
native `v0.8.0-beta.4` version metadata on upstream `64d10fbf`), rebuilds native Windows RTX 3090
(`v0.8.0-qwen38-3090-beta.4`, package `62b9effd`, server `2c25588e`, selected build profile
`native-v0.8.0-beta.4-tc-rtx3090`, public config `6e4c6fc2`) from descendant source `15c3e395`
(`15c3e3959c0a6167f799e9383482ec4e03db9cad`, adding only the native qualification managed-`C1`
power-check fix and corrected Windows store-quota note in
[fork #126](https://github.com/alphastorm/ninfer/pull/126) with identical serve source), carries
native Windows RTX 4090 `v0.8.0-qwen38-4090-beta.3` unchanged from `v0.18.0` (`48c8ac46`, package
`ac41700a`, server `a5266ae6`, [`receipt-audit.json`](../releases/v0.19.0/qualification/receipt-audit.json)
`3162e66e`, without bounded pressure saves until the next engine freeze), and pins unmodified stock
OMP **18.20.0** (`c3089702`, release `443638329`). In the RTX 5090 and RTX 3090 engines, fork #122
bounds an unsettled pressure save refused for a retryable reason (`capacity`, `io`, `stale_tag`) to
six retries or 10 seconds, emitting one `pressure` / `abandoned` receipt and releasing its
continuation instead of latching admission behind the outstanding save (store-quota refusals under
`--session-checkpoint-quota-mib`, reason `quota`, settle immediately without retries or a
`pressure` / `abandoned` receipt; narrow coordinator residuals are deferred to
[fork #123](https://github.com/alphastorm/ninfer/issues/123)). On `41f89b31`, the exact-source RTX
5090 release-candidate (`RC`) batch
([`runtime-rc.json`](../releases/v0.19.0/qualification/runtime-rc.json) `3007e800`) passed all
`12/12` phases in `741.187 s` and the published-image lane receipt
([`rtx5090.json`](../releases/v0.19.0/qualification/rtx5090.json) `4873087e`) passed at **181.71
tok/s** server / **180.20 tok/s** wall decode and **56.67 s** / `56.668 s` cold exact 130,048-token
retrieval at **2,294.9 tok/s** wall / **56.55 s** server. On `15c3e395`, RTX 3090 `beta.4` `tc`
passed its 15-phase hardware chain ([`rtx3090.json`](../releases/v0.19.0/qualification/rtx3090.json)
`9bddbdfd`: **227.19 tok/s** `C1` decode, **978.19 tok/s** prefill, **188.45 s** retrieval, `350.0 W`
enforced cap across all `56` samples with `350.68 W` peak <= `355.0 W` envelope), `83/83` raw
agent-parity positions without waiver
([`rtx3090-agent-parity.json`](../releases/v0.19.0/qualification/rtx3090-agent-parity.json) `a0e0806f`),
shipping-package `C2` fit
([`rtx3090-windows-native.fit.json`](../releases/v0.19.0/qualification/rtx3090-windows-native.fit.json) `af95eadb`),
`3/3` `beta.3` upgrade/rollback/repair rehearsals
([`rtx3090-upgrade.json`](../releases/v0.19.0/qualification/rtx3090-upgrade.json) `40023601`), and
[same-profile identity-first admission](#decision-authorized-identity-first-native-admission)
against published `beta.3` `tc` ([#171](https://github.com/alphastorm/omp-ninfer/pull/171),
[`native-identity-decision.json`](../releases/v0.19.0/qualification/native-identity-decision.json)
`856ac8d2`, [`rtx3090-windows-native.identity-proof.json`](../releases/v0.19.0/qualification/rtx3090-windows-native.identity-proof.json)
`a0e9086b`, [`rtx3090-speed.json`](../releases/v0.19.0/qualification/rtx3090-speed.json) `a9df66a1`:
weighted **0.9997** / min **0.9975**, `84/84` ABBA and `80/80` sealed determinism byte-identical).
Fresh **2026-11-13** [route acceptance](../releases/v0.19.0/acceptance/documented-routes.json)
(`20dd5230`) on frozen `omp-ninfer` candidate `6b22f219` passed all five routes (`31/31` blocks),
three stock `18.20.0` clients, the **402.128 s** RTX 5090 hold, and both RTX 4090 (**517.0 s**) and
RTX 3090 (**`1,339.4` s**) native campaigns, public installs
([RTX 4090](../releases/v0.19.0/acceptance/rtx4090-public-install.json) `2243cdff` /
[RTX 3090](../releases/v0.19.0/acceptance/rtx3090-public-install.json) `d5d61388`), audited
checkpoint-store retirement ([#165](https://github.com/alphastorm/omp-ninfer/pull/165)), and
independent restorations on their first attempts without a waiver (on RTX 3090: `0` HTTP `503`
responses, `0` queue timeouts, `0` checkpoint write errors, complete managed `Stop` with `0` refused
sessions, `5/5` HTTP `200` on four-way `C2` fanout, and `2/2` committed compactions in proof
`9759ea5f` inside `rtx3090-public-install.json`).

## v0.18.0 unified F4 runtime re-cut, RTX 3090 `tc` selection, and acceptance boundary

Published release **v0.18.0** (2026-11-12) rebuilds all three GPU runtime lanes from frozen fork
engine source `F4` `48c8ac46` (`48c8ac4644322f024b5c3bd5b657af5874567251` on upstream `64d10fbf`):
RTX 5090 `v0.7.0-qwen38-5090-beta.7` (image `496195ec` on reused base `28857182`, server
`804ef8ac`), native Windows RTX 4090 `v0.8.0-qwen38-4090-beta.3` (package `ac41700a`, server
`a5266ae6`, build profile `native-v0.8.0-beta.3-rtx4090`), and native Windows RTX 3090
`v0.8.0-qwen38-3090-beta.3` (package `bf1ceaa9`, server `e5713286`, selected build profile
`native-v0.8.0-beta.3-tc-rtx3090` enabling `sm_86` small-T tensor-core verify at `T=8/16`,
[`rtx3090-profile-selection.json`](../releases/v0.18.0/qualification/rtx3090-profile-selection.json)
`f7611ba5`), and pins unmodified stock OMP **18.18.7** (`e325ffc7`). On `48c8ac46`, the exact-source
RTX 5090 `RC2` batch ([`runtime-rc.json`](../releases/v0.18.0/qualification/runtime-rc.json)
`ca172838`) passed all `12/12` phases in `723.968 s` (`66` historical host, `54` current host, `11`
dense, `1` overlap), passed its `1,120`-prompt quality screen and `80`-prompt determinism against
sealed `beta.6` (zero deltas, leak ratio `1.0`), and passed the published-image lane receipt
([`rtx5090.json`](../releases/v0.18.0/qualification/rtx5090.json) `763178cb`: **181.52 tok/s**
server / **180.01 tok/s** wall decode, **56.90 s** / `56.896 s` cold exact 130,048-token retrieval
at **2,285.7 tok/s** wall / **56.80 s** server; separate same-path RDC double build matched `664`
graph artifacts and `3` packages byte-for-byte while `RC1`/`RC2` digest divergence is disclosed in
[ninfer#120](https://github.com/alphastorm/ninfer/issues/120)). Both rebuilt `beta.3` native lanes
passed 15-phase chains ([`rtx4090.json`](../releases/v0.18.0/qualification/rtx4090.json) `165999b9`:
**253.71 tok/s** `C1` decode, **83.45 s** retrieval;
[`rtx3090.json`](../releases/v0.18.0/qualification/rtx3090.json) `e7ac3ab7`: **227.17 tok/s** `C1`
decode, **189.12 s** retrieval), `83/83` raw agent-parity positions without waiver, fit proofs
(`cf77a595` / `9bd9fd74`), `3/3` `beta.2` upgrade/rollback/repair rehearsals (`a97ae3fa` /
`483a8395`), powered `1,120`-prompt [`EXP-085`](#experiment-ledger) quality screens (`531c5ed1` / `466586d9`, `80/80`
determinism per arm), and paired A/B/B/A (`ABBA`) speed gates against published `beta.2` under
[`native-speed-decision.json`](../releases/v0.18.0/qualification/native-speed-decision.json)
(`26ce10a3`: RTX 3090 `tc` weighted **1.5373** / min **1.3503**, `84/84` within-engine and `35/84`
cross-engine identical in [`rtx3090-speed.json`](../releases/v0.18.0/qualification/rtx3090-speed.json)
`a7bf3903`; RTX 4090 weighted **1.0000** / min **0.9992**, `115/115` identical in
[`rtx4090-speed.json`](../releases/v0.18.0/qualification/rtx4090-speed.json) `fb8b62ad`). Fresh
**2026-11-12** [route acceptance](../releases/v0.18.0/acceptance/documented-routes.json)
(`9eefb58d`) on `2a735da0` passed all five routes (`31/31` blocks),
three stock `18.18.7` clients, the **406.876 s** RTX 5090 hold, initial-window RTX 4090
(**509.857 s**), and third-execution RTX 3090 (**`1,439.367` s**) native campaigns,
public-installs, and independent restoration checks without a waiver: RTX 3090 attempt 1 failed its
post-route subagent check on malformed `task` tool arguments and restored; attempt 2 ran while the
host's system drive was full (`0.39 GiB` free when measured afterwards; `27` checkpoint writes failed with Windows error
`112`, checkpoint saves were refused for `capacity`, admission waited behind an unsettled checkpoint
save across `4` HTTP `503` `deferred by a pending checkpoint save` timeouts before a `900 s`
compaction timeout across a `1,618.414 s` failed window, and managed `Stop` refused `9` sessions
before empty-session `Start`/`Stop` recovery); the founder-authorized third execution in fresh
workspaces with an enforced `60 GiB` free-space floor (`63.08` GiB free, recorded in shared native
driver `accept-rtx4090-route.py`'s single `--attempt 2` rerun slot because the frozen driver accepts only `--attempt 1|2`) passed every phase with zero
disk-full errors (`2` committed compactions in
`747.00` s, zero HTTP `503` responses, compaction receipt `cfa89628`, showing the request-level
HTTP `503` half of [ninfer#89](https://github.com/alphastorm/ninfer/issues/89) reproduced in
acceptance only under
disk exhaustion). Pre-cut proxy-GPU engineering evidence and excluded
candidates (`sm_120` `Group64` `A8` prefill killed at `0.784860×` / `0.983623×` vs baseline, restricted
tool-argument copy drafting `< +15%` session-decode bar, RTX 5090 cadence-only prefill pacing kept default-off at
`92.26 tok/s < 100 tok/s` co-resident decode, and experimental `rk4v4` 4-bit KV screening) remain diagnostic context in the
[release notes](../releases/v0.18.0/NINFER_RELEASE_NOTES.md#pre-cut-proxy-host-engineering-evidence-and-excluded-candidates--not-release-qualification).

## v0.17.0 RTX 5090 F3 runtime, carried native `beta.2`, and acceptance boundary

Published release **v0.17.0** (2026-11-10) rebuilds the RTX 5090 container runtime to
`v0.7.0-qwen38-5090-beta.6` from release source F3 `e0971faf`
([fork PR #101](https://github.com/alphastorm/ninfer/pull/101), image `7a19576b`, server `dc86e101`)
on upstream `64d10fbf`, carries both native Windows `v0.8.0-qwen38-{4090,3090}-beta.2` packages
unchanged at `a87de361` ([`receipt-audit.json`](../releases/v0.17.0/qualification/receipt-audit.json)
`c137388a`, retaining their `v0.16.2` speed decision
[`native-speed-decision.json`](../releases/v0.17.0/qualification/native-speed-decision.json)
`5c09de6a` and ABBA reductions [`rtx3090-speed.json`](../releases/v0.17.0/qualification/rtx3090-speed.json)
`852e13ca` and [`rtx4090-speed.json`](../releases/v0.17.0/qualification/rtx4090-speed.json)
`e48aba81`), and pins stock OMP **18.18.6** (`9058ab9d`). On `e0971faf`, the exact-source RC
([`runtime-rc.json`](../releases/v0.17.0/qualification/runtime-rc.json) `bed3a245`) passed all
`12/12` phases (`66` historical host, `54` current host including `35/35` EngineCore and Scheduler
regressions, `11` dense, `1` overlap), matched `664` build artifacts and all `3` package outputs bit
for bit across a same-path double build, and passed the published-image lane receipt
([`rtx5090.json`](../releases/v0.17.0/qualification/rtx5090.json) `11fde294`: **181.92 tok/s**
server / **180.40 tok/s** wall decode, **56.63 s** cold exact 130,048-token retrieval at **2,296.5
tok/s** wall / **56.53 s** server). Fresh **2026-11-10**
[route acceptance](../releases/v0.17.0/acceptance/documented-routes.json) on `076bbe4f` passed all
five routes (`31/31` blocks), three stock `18.18.6` clients, the **408.213 s** RTX 5090 hold, and
RTX 4090 native campaign (**508.420 s**), public-install, and restoration checks, while RTX 3090's
post-route `native-probes` automatic-compaction campaign failed (`1,727.696 s` elapsed; `900 s`
timeout, `8` HTTP `503` queue timeouts, `2` HTTP `499` cancellations, `0` resident work; subsequent
managed Stop `graceful_incomplete_shutdown` saved `2` / skipped `5` / refused `3`, reason
`capacity`) under its [founder waiver](../releases/v0.17.0/qualification/rtx3090-route-waiver.json)
(`19f2c0ef`, with separate empty-session `Start`/`Stop` lead recovery `fabb50de`; no RTX 3090
behavior completion, structured outage, wrapper restoration audit pass, or anonymous public-install
claim). Pre-cut slice/proxy investigations in the
[release notes](../releases/v0.17.0/NINFER_RELEASE_NOTES.md#pre-cut-investigative-measurements--not-published-image-or-product-acceptance)
remain diagnostic context, and optional prefill pacing stays default off.

## v0.16.2 no-regression and acceptance boundary

Published release **v0.16.2** (2026-11-04) uses the explicit
[founder speed decision](../releases/v0.16.2/qualification/native-speed-decision.json), not the
historical reducer's 1.08 speedup floor below: against **published beta.1**, role/all-case
weighted decode **≥0.98**, every case **≥0.95**, normalized outputs byte-identical in every
required within/cross-build ABBA pair. RTX 3090 measured **1.0002518490206602** weighted /
**0.9987703200333666** minimum, **84/84** identical; RTX 4090 measured
**0.9995778248449502** role / **0.9996281434580012** all / **0.9988670027551729** minimum,
**115/115** identical. Both pass no-regression without a speed waiver or a new speedup claim.
Parameterizing the older product reducer is deferred in
[#138](https://github.com/alphastorm/omp-ninfer/issues/138); this release binds the actual native reduction.

The [notes](../releases/v0.16.2/NINFER_RELEASE_NOTES.md#exact-subject-founder-waivers--original-failures-retained)
retain all three parity exceptions with measured values: RTX 5090 `restore_0` TTFT
**0.481856409 / 0.231568998 s**, bound **0.481568998 s**; RTX 4090 `restore_1` cache gap
**−52 / −48**, TTFT **0.642947 / 0.5589493 s** within bound; RTX 3090 position 1 `base`
TTFT **0.4975294 / 0.2144353 s**, bound **0.4644353 s**. Native parity is **82/83** measured
passes each; RTX 5090 has **88/88 judged**, not a strict or overall-run pass.
Both predecessor rehearsal sets passed 3/3; RTX 4090 used only the disclosed founder-approved
uncapped-power assertion fix, not a runtime change.

Fresh **2026-11-04** [route acceptance](../releases/v0.16.2/acceptance/documented-routes.json)
on `c6fc8465` passed five routes / 31 blocks, three stock clients and RTX 4090 native acceptance.
The later RTX 3090 campaign failed, founder-waived, at structured-outage managed Stop:
`graceful_incomplete_shutdown`, saved 1 / skipped 8 / refused 1, `capacity`, reclaimed 0.
This #78 residual also exists on published beta.1; v0.16.0 avoided it by timing. Empty-session
Start/Stop recovery does not establish behavior completion, wrapper restoration or anonymous
public install. Fork [#89](https://github.com/alphastorm/ninfer/issues/89) /
[#90](https://github.com/alphastorm/ninfer/issues/90) track the residuals.
Route completion and the 418.529 s production hold are **not throughput or reclaim-latency benchmarks**.

## Gate-bound native speed comparisons

[`scripts/speed_gate.py`](../scripts/speed_gate.py) owns the host-free reduction of the
native ABBA speed gate. Its thresholds come from the release's recorded decision,
not a fixed speedup floor. The
[v0.16.2 decision](../releases/v0.16.2/qualification/native-speed-decision.json)
requires **weighted decode ratio `>= 0.98`, every case `>= 0.95`, and byte-identical
normalized outputs** against the published beta.1 incumbent, while the
[v0.18.0 decision](../releases/v0.18.0/qualification/native-speed-decision.json) (`26ce10a3`)
applies the `>= 0.98` weighted / `>= 0.95` every-case floors against published `beta.2` and selects
within-engine output identity plus decision-bound `EXP-085` quality-screen admission for
cross-engine output differences, and the
[v0.19.0 decision](../releases/v0.19.0/qualification/native-speed-decision.json) (`bba32162`)
applies the same `>= 0.98` / `>= 0.95` floors on RTX 3090 `beta.4` `tc` against published `beta.3`
`tc` alongside [`native-identity-decision.json`](../releases/v0.19.0/qualification/native-identity-decision.json)
(`856ac8d2`). The earlier v0.16.0 speedup-claim rule remains expressible by
recording `1.08` / `0.95` instead.
Both role-only and combined role-plus-supplemental weighted ratios must clear the
recorded weighted floor; the every-case floor covers the combined suite.
The default output rule requires identity within **and across** engines. A second,
explicitly decision-selected rule requires identity **within each engine**
(`A0/A3`, `B1/B2`) and admits cross-engine differences only with that decision's
SHA-256-bound passing EXP-085 verdict for the exact lane, incumbent and candidate.
Neither a screen for another lane/build nor a release waiver supplies that permission.
There is no separate threshold override: a waiver does not turn a failed reduction into a pass.

Before collecting candidate data, freeze one `gate.json` declaration:

- `artifact_type: "omp_ninfer_speed_gate"` and integer `schema_version: 1`.
- `release`: the product release being judged.
- `decision`: the complete recorded `omp_ninfer_founder_gate_decision` schema-1
  object for that same release, copied from the file bound by
  `releases/<release>/qualification.json` → `observed_gates.native_speed_decision`.
  Both commands verify that binding's `repository_path` and file SHA-256, then
  require the embedded decision to equal the bound file's content; a self-written
  threshold or freshly regenerated plan cannot substitute for that record.
  Its `rule` contains positive finite
  `weighted_decode_ratio_minimum` and `every_case_ratio_minimum`,
  `byte_identical_normalized_outputs:
  "required for every case (A0/A3, B1/B2, A0/B1)"`, and `applies_to` selecting
  `"role weighted"`, `"all-cases weighted"`, and `"every case"`. The complete
  decision is included in the declaration digest; changing it invalidates the
  recorded pre-screen plan.
- To select the second output rule, the decision instead records
  `byte_identical_normalized_outputs:
  "required within each engine (A0/A3, B1/B2); cross-engine differences require a bound passing EXP-085 verdict"`.
  The declaration must name `lane: "rtx3090"` or `"rtx4090"`. The decision's
  `quality_screens` array contains `{lane, repository_path, sha256}` bindings.
  Each admitted verdict must pass and be valid under EXP-085, bind the frozen
  1,120/80 prompt sets and four native screen/determinism arms, and match both
  measured binary/configuration identities. Missing, failed, foreign or rehashed
  evidence cannot authorize differences. Byte-identical cross-engine outputs
  need no screen under either output rule; within-engine differences always fail.
- `comparator`: `binary_sha256` of the shipped incumbent executable and
  `configuration_sha256` of its measured configuration. A candidate executable
  configured for MTP3 is **not** the shipped-incumbent comparator.
- `request_suite`: the complete list of `{id, request_sha256}` objects, including
  every role/depth and any required supplemental request. Hash the exact request
  payload used by the capture runner, not case source text or a list of case IDs.
- `request_suite_sha256`: SHA-256 of that list sorted by `id`, serialized as UTF-8
  JSON with sorted object keys, `separators=(",", ":")`, `ensure_ascii=False`, and no
  trailing newline. The reducer recomputes this identity from each arm's requests;
  a caller-supplied suite hash cannot substitute for those requests.
- `role_case_ids`: unique IDs selecting the role suite within the full request
  list; remaining requests are supplementals. For the v0.16.0 forms, that means
  84 depth-0 roles, or 108 roles (84 at depth 0 plus 12 each at 32K/64K) and seven
  supplementals. Declare the exact campaign form before measurement.

Configuration identities use the same canonical JSON encoding above, over the
capture's `identity.config` object. They are not the byte hash of a formatted
configuration file. The declaration's binary identity should be obtained from the
published incumbent package, not inferred from a source commit or version string.
The EXP-097 [role-corpus measurement](measurements/2026-10-25-exp097-role-corpus.json)
retains historical role request identities, but it is not interchangeable with a
native gate's request suite: context depth, token limits, reasoning, and request
construction are part of request identity.

### Use one declaration for the pre-screen and gate

`candidate.json` contains only the candidate's `binary_sha256` and canonical
`configuration_sha256`. Generate the pre-screen plan:

```sh
python3 scripts/speed_gate.py prescreen \
  --gate gate.json --candidate candidate.json --out prescreen-plan.json
```

The plan's `A` arm and complete request suite come **only** from `gate.json`; there
is no comparator argument. `B` comes from `candidate.json`, and the order is ABBA.
This command writes an identity plan, not a hardware launcher. A campaign operator
must resolve those hashes to the actual files, check startup identities, and retain
the plan with the measured captures. It does not authorize a hardware run.
Both `prescreen` and `reduce` read qualification from this checkout by default;
pass `--root PATH` to use another repository root containing the release and its
hash-bound decision. Neither command contacts a host.

Collect four passed captures with `arm` (`A`, `B`, `B`, `A`), `index` (`0`..`3`),
`status: "passed"`, measured `identity.binary_sha256`, and either `identity.config`
or a measured canonical `identity.configuration_sha256`. Each `requests` entry
contains `id`, `request_sha256`, positive integer `completion_tokens`, and positive
finite `decode_seconds`, plus a `normalized_output` string containing the retained
normalized UTF-8 output. For native captures, attach the canonical JSON serialization
of each retained output's `projection`: sorted keys, `ensure_ascii=False`,
`separators=(",", ":")`, and no trailing newline. This preserves content, reasoning,
ordered tool calls and their raw argument strings; only transport tool IDs are
excluded by the capture's projection. A claimed `output_sha256` or matching-output
boolean is not a substitute for retained normalized bytes.
Reduce the pre-screen or final gate against the **same** declaration and recorded plan:

```sh
python3 scripts/speed_gate.py reduce --gate gate.json --plan prescreen-plan.json \
  --capture A0.json --capture B1.json --capture B2.json --capture A3.json \
  --out speed-result.json
```

Repeat `--capture` for disjoint depth/supplemental shards at each ABBA index.
Every position must contain exactly the same unique case IDs, with no duplicate
shards and one binary/configuration identity per position. Raw captures may remain
private: the result retains only case IDs, measurement values and digests, including
each arm's binary, configuration and recomputed request-suite identities and the
capture digests. It does not copy configurations, prompts, outputs, paths, or GPU
identifiers. The recorded plan is required: the result binds its canonical `plan_sha256`
and `plan_gate_sha256` alongside the declaration's `gate_sha256` and `role_case_ids`.
It also records the release and canonical `decision_sha256` (not the formatted
decision file's byte hash), numerical `thresholds_passed`, `normalized_outputs_identical`,
and `output_mismatch_case_ids`. Output comparisons use the actual UTF-8 bytes at
all four ABBA positions; safe arm receipts retain only normalized-output hashes.
The second rule additionally records `output_rule_passed`,
`within_engine_outputs_identical`, `within_engine_output_mismatch_case_ids` and
the authorizing `quality_screen_sha256` (null when no screen authorizes differences).
`normalized_outputs_identical` still describes all four arms, even when an
authorized cross-engine difference passes. The default result shape and v0.16.2
decision remain unchanged.

Weighted throughput is pooled completion tokens divided by pooled decode seconds
for each arm, then candidate divided by comparator. Each case's ratio uses the
median of its two candidate rates divided by the median of its two comparator
rates. These are the v0.16.0 reduction formulas, not averages of case ratios.

`gate_predictive: true` means identities match the declared comparator binary,
configuration, complete request suite, and recorded plan; it does **not** mean the thresholds
passed or that hardware/release qualification is complete. Any comparator binary,
configuration or arm's suite mismatch produces `status: "DIAGNOSTIC"`,
`gate_predictive: false`, `gate_passed: false`, and field-specific
`diagnostic_reasons`, even if `thresholds_passed` is true. Candidate-repeat identity
drift is also diagnostic. A changed plan/declaration digest, role/supplemental partition,
request suite, ABBA order, or planned arm identity is diagnostic through the same
mechanism, even when captures match the comparator and complete request list.
The declaration remains the campaign authority; the reducer does not hardcode a corpus.
Thus the v0.16.0 same-binary MTP3 pre-screen cannot claim
to predict the shipped-incumbent gate; an isolated subset cannot claim the full
role-suite gate either. Missing normalized output bytes are invalid input; differing
bytes fail unless the selected output rule explicitly admits that cross-engine
difference. Properly bound
historical v0.16.0 final RTX 4090 measurements still fail
the `log-024@0` floor at `0.933832`, rather than inheriting the historical waiver.
Exit status is `0` for a gate pass, `1` for a failure or diagnostic, and `2` for
invalid/incomplete inputs.

### Decision-authorized identity-first native admission

A release may bind `observed_gates.native_identity_decision` to a schema-1
`omp_ninfer_founder_gate_decision` whose `rule.quality_admission` is
`"speed-ABBA byte identity and 80/80 sealed incumbent determinism byte identity"`.
Its `lanes` selects the permitted native lanes. For each lane,
`sealed_incumbent_determinism[lane]` records the incumbent's
`package_sha256`, `server_binary_sha256`, `configuration_sha256` and
`model_artifact_sha256` under `identity`, plus the sealed `responses_sha256`,
`prompt_count: 80` and frozen `prompt_ids_sha256`.
Draft decisions are not admission records.

Generate a content-safe proof from retained speed captures and the native
determinism run directories (`arm.json` and `responses.jsonl`):

```sh
python3 scripts/speed_gate.py identity-proof --gate gate.json --plan prescreen-plan.json \
  --capture A0.json --capture B1.json --capture B2.json --capture A3.json \
  --incumbent-determinism sealed-incumbent --candidate-determinism fresh-candidate \
  --release-spec candidate-release-spec.json --out native-identity-proof.json
```

Every declared speed-ABBA case must match the incumbent, and all frozen 80
determinism prompts must match its sealed outputs. Determinism normalization
retains content, reasoning and ordered tool calls with their raw argument strings;
only transport tool IDs are removed. The producer compares those UTF-8 bytes,
not pass flags. The public `omp-ninfer.native-identity-proof` schema-1 receipt
retains the decision file hash, exact native identities, authenticated build profile,
speed declaration/plan/arm digests and per-prompt output digests; it includes no
raw output text.

`bind_native_variant.py --identity-proof native-identity-proof.json` selects this
admission path instead of `--quality-screen` or `--t1-parity`. Binder/verifier
validation rechecks the release decision, all speed cases, sealed membership and
all 80 pairs. By default, the authenticated package must use the standard
`native-vX.Y.Z[-beta.N]-rtx3090` or `...-rtx4090` build profile; under
[#171](https://github.com/alphastorm/omp-ninfer/pull/171), a non-default profile (`-tc`, `-a8`, or
`-tc-a8`) is admitted only when the hash-bound decision sets `rule.build_variant =
"default-or-same-profile-published-incumbent"` and seals the latest ready product's published
incumbent of that same lane and build-profile variant (as used for RTX 3090
`native-v0.8.0-beta.4-tc-rtx3090` against published `native-v0.8.0-beta.3-tc-rtx3090` in `v0.19.0`).
Different build-profile variants or differing outputs still require a powered-screen verdict.
Identity-first does not waive native fit, speed floors, durability, parity or release acceptance.

## Current state

Oh My Pi (coding-agent client) connects through OMP NInfer (qualified appliance and release layer)
to NInfer (inference engine) serving Qwen3.8 27B (served model). Published release **v0.19.0**
(2026-11-13; superseding `v0.18.0`, 2026-11-12) pins unmodified upstream OMP 18.20.0 (`c3089702`) and
shared model container version 3 `81f924d4`, rebuilds the RTX 5090 container runtime
(`v0.7.0-qwen38-5090-beta.8`, source `41f89b31`) and native Windows RTX 3090 package
(`v0.8.0-qwen38-3090-beta.4`, `native-v0.8.0-beta.4-tc-rtx3090`, descendant source `15c3e395` with
identical serve source) on upstream `Neroued/ninfer` master `64d10fbf` with bounded retryable
pressure-save refusals ([ninfer#122](https://github.com/alphastorm/ninfer/pull/122): six retries or
10 seconds before emitting `pressure` / `abandoned` and releasing the continuation, while
store-quota refusals settle immediately without retries), and carries native Windows RTX 4090
`v0.8.0-qwen38-4090-beta.3` unchanged from `v0.18.0` (`48c8ac46`, without bounded pressure saves
until the next engine freeze), building on `v0.18.0`'s `48c8ac46` Device-staged durable
`StateImage` saves ([PR #109](https://github.com/alphastorm/ninfer/pull/109)), operation-free
checkpoint prepare holding ([PR #111](https://github.com/alphastorm/ninfer/pull/111)), bounded `K =
4` fresh-admission priority ([PR #108](https://github.com/alphastorm/ninfer/pull/108)), RTX 3090
`sm_86` small-T tensor-core verify at `T=8/16`
([PR #104](https://github.com/alphastorm/ninfer/pull/104)), and `v0.17.0`'s `e0971faf`
bounded resume/fresh admission ([#434](https://github.com/Neroued/ninfer/issues/434)) and serving
robustness, while retaining **DFlash2 draft window 7 (`K=7`)** across all three lanes (`BF16` KV and
`C2` on the RTX 5090 container lane; `INT8` KV and `C1` on native RTX 4090; `INT8` KV and `C2` over
one shared 131,072-token pool on native RTX 3090; see [`FACTS.md`](FACTS.md) and
[`BENCHMARKS.md`](BENCHMARKS.md)).

- **Current runtimes:**
  - **RTX 5090 container (`sm_120a`):** `v0.7.0-qwen38-5090-beta.8` (source `41f89b31` on upstream
    master `64d10fbf`, image `c3ec151b` on reused base `28857182`, server `147da36b`, model
    `81f924d4`, profile `qwen38-5090-v0.13.0`, configuration `751d22dc`, isolated host checkpoint
    directory `checkpoints-v019` mounted at `/checkpoints-v013`) with DFlash2 draft window 7
    (`--lm-head-draft`), BF16 KV (146,368 automatic KV tokens), 131,072-token context, bounded
    retryable pressure-save refusals, and two requests in flight
    ([qualification receipt](../releases/v0.19.0/qualification/rtx5090.json)).
  - **RTX 4090 and RTX 3090 native Windows (`sm_89` / `sm_86`):** carried
    `v0.8.0-qwen38-4090-beta.3` (unchanged from `v0.18.0` at source `48c8ac46`, package `ac41700a`,
    server `a5266ae6`, build profile `native-v0.8.0-beta.3-rtx4090`, profile
    `qwen38-4090-native-v0.8.0-beta.3`, configuration `b71a2cff`, DFlash2 `K=7`, INT8 KV, `C1`, 30 s
    pending timeout, two extra device-state slots, 1,024-token prefill chunk, `15,747.734375 MiB` /
    `16,512,696,320` B shared Host budget, `640 MiB` admission headroom, 450 W owner baseline;
    without bounded pressure saves until the next engine freeze) and re-cut
    `v0.8.0-qwen38-3090-beta.4` (source `15c3e395` with identical serve source to RTX 5090
    `41f89b31`, package `62b9effd`, server `2c25588e`, selected build profile
    `native-v0.8.0-beta.4-tc-rtx3090` enabling `sm_86` small-T tensor-core verify at `T=8/16`,
    profile `qwen38-3090-native-v0.8.0-beta.4`, configuration `6e4c6fc2`, DFlash2 `K=7`, INT8 KV,
    `C2` sharing one 131,072-token pool, 180 s pending timeout, two extra device-state slots,
    1,024-token prefill chunk, `20,867.734375 MiB` / `21,881,405,440` B shared Host budget, `768 MiB`
    admission headroom, 350 W serving cap / 370 W restored, bounded retryable pressure-save
    refusals) on upstream master `64d10fbf` and shared model `81f924d4`, with `Q4_G64_FP16` draft
    MLP weights, host-mapped token embedding, and `Group64` A8 and FP32 head logits off, serving one
    native lane at a time on port `18082` on a UUID-bound two-GPU host
    ([RTX 4090 receipt](../releases/v0.19.0/qualification/rtx4090.json),
    [RTX 3090 receipt](../releases/v0.19.0/qualification/rtx3090.json)).
- **Shipped from the ledger:** DFlash2 K=7 with BF16 KV shipped on the RTX 5090 in v0.10.0
  (EXP-078 to EXP-086, EXP-090). Single-launch 8-column verify attention (the shipped subset of
  EXP-092) plus small-T tensor-core Q4 query/key projections at 8 and 16 verify columns
  (EXP-094) shipped in v0.11.0 (`v0.6.16`, source `1302d639`, carried through v0.12.2), were ported
  onto upstream master `64d10fbf` in v0.13.0 (`v0.7.0-qwen38-5090-beta.2`, source `6d4d0a05`), and
  shipped from common engine source `2c6f423b` in v0.14.0–v0.15.0 (`v0.7.0-qwen38-5090-beta.3`,
  101.62% serial 84-role median decode vs beta.2 in
  [`decode-parity.json`](../releases/v0.15.0/qualification/decode-parity.json)). EXP-095 compared
  the superseded fork candidate `a59c13d0` against upstream `81c8ce09` in a local fixed-KV
  rehearsal, and EXP-097 measured **101.09%** median decode parity across 84 serial role cases for
  the rebased RTX 5090 runtime against v0.12.2's `1302d639`
  ([`UPSTREAM.md#v0130-sync-program`](UPSTREAM.md#v0130-sync-program),
  [`2026-10-25-exp097-role-corpus.json`](measurements/2026-10-25-exp097-role-corpus.json)).
  Byte-identical `sm_86`/`sm_89` attention prefill specializations (+4.96% on RTX 4090 and +5.40%
  on RTX 3090 at 130,048 tokens, EXP-100) and the native DFlash2 load-time fit seam (EXP-098)
  shipped in `v0.14.0`. In `v0.16.0` (frozen source `26fa28d0`), native **DFlash2 `K=7`** ships on
  both the RTX 3090 (`v0.8.0-qwen38-3090-beta.1`, EXP-098, EXP-101) and RTX 4090
  (`v0.8.0-qwen38-4090-beta.1`, EXP-098, EXP-102, EXP-103, EXP-104; `254.27 tok/s` managed `C1`
  decode vs `151.54 tok/s` under MTP3 in `v0.14.0`, and **×1.2736** 108-role / **×1.2741** 115-case
  ABBA weighted decode vs `v0.14.0` MTP3 with depth-0 case `log-024@0` at **0.934** / `139.41 →
  130.19 tok/s` waived by the founder with disclosure), **native `C2` (`--max-concurrency 2`)** over
  one shared 131,072-token `INT8` pool ships on the RTX 3090 (`1.385×` paired aggregate decode,
  `0.722×` pair completion wall, EXP-106), and **counted Host `StateImage` materialization before
  off-worker checkpoint export** (`StateImageStore::prepare_host_export`, cutting post-resume
  first-fork TTFT from `5.03 s` to `0.11 s` on RTX 5090 and from `15.4–17.8 s` to `0.33–0.76 s` on
  RTX 3090, EXP-105) plus `io_uring`, checkpoint-owner, installer, and per-position speculative
  metric fixes ship across all three lanes (`84/84` role-corpus output hashes at `347.20 → 346.95
  tok/s`, `×0.999282`, on RTX 5090 `v0.7.0-qwen38-5090-beta.4`), while `Group64` A8 and opt-in
  `--fp32-head-logits` stay off (EXP-089, EXP-099, EXP-100, EXP-103, EXP-104). In `v0.16.2` (frozen
  source `a87de361`), all three lanes rebuild (`v0.7.0-qwen38-5090-beta.5` and
  `v0.8.0-qwen38-{4090,3090}-beta.2`) with byte-proven durable-generation Host reclaim before export
  refusal ([fork #78](https://github.com/alphastorm/ninfer/issues/78),
  [#82](https://github.com/alphastorm/ninfer/pull/82)), export-retirement reservation
  ([#68](https://github.com/alphastorm/ninfer/pull/68)), deterministic bounded RDC builds
  ([#69](https://github.com/alphastorm/ninfer/pull/69); `661` build artifacts and all `3` package
  outputs bit-identical on RTX 5090), zero-difference 1,120-prompt powered quality screens, and
  founder-approved no-regression ABBA speed gates against published `beta.1` (RTX 3090 weighted
  `1.0003` / min `0.9988`, `84/84` identical; RTX 4090 weighted `0.9996` / min `0.9989`, `115/115`
  identical). In `v0.17.0` (release source F3 `e0971faf`,
  [fork PR #101](https://github.com/alphastorm/ninfer/pull/101)), RTX 5090 rebuilds to
  `v0.7.0-qwen38-5090-beta.6` (`664` build artifacts and all `3` package outputs bit-identical across
  a same-path double build; `12/12` RC phases) with bounded resume/fresh admission and per-rotation
  fresh-window accounting (addressing upstream
  [`Neroued/ninfer#434`](https://github.com/Neroued/ninfer/issues/434), EXP-109, EXP-112), durable
  pressure-work waits, serving robustness
  ([#440](https://github.com/Neroued/ninfer/issues/440)/[#441](https://github.com/Neroued/ninfer/issues/441)/[#446](https://github.com/Neroued/ninfer/issues/446),
  EXP-120), and host-side NFC/frontend rendering (EXP-117), while native `beta.2` packages stay
  carried at `a87de361`. In `v0.18.0` (frozen source `F4` `48c8ac46`), all three lanes rebuild
  (`v0.7.0-qwen38-5090-beta.7` and `v0.8.0-qwen38-{4090,3090}-beta.3`), delivering `F3` plus
  Device-staged durable `StateImage` checkpoint saves ([ninfer#89](https://github.com/alphastorm/ninfer/issues/89),
  [PR #109](https://github.com/alphastorm/ninfer/pull/109)), operation-free prepare holding
  ([PR #111](https://github.com/alphastorm/ninfer/pull/111)), bounded `K = 4` fresh-admission
  priority ([ninfer#102](https://github.com/alphastorm/ninfer/issues/102),
  [PR #108](https://github.com/alphastorm/ninfer/pull/108)), and `sm_86` small-T tensor-core verify
  at `T=8/16` on the selected RTX 3090 `tc` profile ([PR #104](https://github.com/alphastorm/ninfer/pull/104);
  **1.5373×** weighted ABBA decode vs `beta.2`, **227.17 tok/s** `C1` decode, passing `1,120`-prompt
  `EXP-085` screen `466586d9`), while RTX 5090 cadence-only prefill pacing stays default-off
  (`92.26 < 100 tok/s` co-resident decode), `sm_120` `Group64` `A8` prefill
  ([PR #105](https://github.com/alphastorm/ninfer/pull/105)) is killed at `0.784860×` / `0.983623×`,
  and restricted tool-argument copy drafting (`+5.24%` to `+10.12%`) is excluded. In `v0.19.0`, RTX
  5090 (`v0.7.0-qwen38-5090-beta.8`, source `41f89b31`) and native RTX 3090
  (`v0.8.0-qwen38-3090-beta.4`, `native-v0.8.0-beta.4-tc-rtx3090`, descendant source `15c3e395` with
  identical serve source) ship bounded retryable pressure-save refusals
  ([ninfer#122](https://github.com/alphastorm/ninfer/pull/122): six retries or 10 seconds, `80/80`
  sealed determinism and `84/84` ABBA byte identity on RTX 3090 `tc` vs published `beta.3` `tc`, and
  first-attempt RTX 3090 `C2` acceptance with `0` HTTP `503` responses and `2/2` committed
  compactions), while native RTX 4090 `beta.3` stays carried unchanged at `48c8ac46`.
- **Open work:** re-cutting native RTX 4090 with bounded pressure saves at the next engine freeze,
  deferred pressure-save coordinator residuals
  ([`alphastorm/ninfer#123`](https://github.com/alphastorm/ninfer/issues/123)) and broader load
  shapes under [`alphastorm/ninfer#89`](https://github.com/alphastorm/ninfer/issues/89),
  per-rotation fresh-window consumption under pending pressure saves
  ([`alphastorm/ninfer#103`](https://github.com/alphastorm/ninfer/issues/103)),
  single-op prepare-ordering bounds ([`alphastorm/ninfer#115`](https://github.com/alphastorm/ninfer/issues/115)),
  deterministic RTX 5090 RC-recipe builds ([`alphastorm/ninfer#120`](https://github.com/alphastorm/ninfer/issues/120)),
  founder disposition of a geometry-matched true-cold durability oracle for `rk4v4` 4-bit KV
  (`262,144`-token native context and RTX 4090 `C2`, EXP-106, EXP-107, EXP-116), `Group64` A8
  prefill leak-flip localization (EXP-100), selective upstream kernel/feature backports,
  verify-round boundary pipelining (EXP-058, EXP-092), Q4/Q5 epilogue fusion (EXP-056), warm-turn
  fragment consolidation (EXP-059), template-fork warm starts, and paged host-to-device KV prefetch
  beyond 262K tokens.

## Measured baseline

Historical v0.2 baseline on one RTX 5090 (`sm_120a`), shipped `v0.2.0-beta.1` profile — Qwen3.8-27B
`groupwise-int`, BF16 KV, MTP3, 1,024-token prefill chunks, one active request
([receipts](../releases/v0.2.0-beta.1/qualification.json)):

| Metric | Value |
| --- | --- |
| Decode throughput | 235.02 tok/s over 2,048 completion tokens |
| MTP3 acceptance | 99.87% (1,534/1,536) on the fixed decode workload |
| 130,048-token exact prefill | 2,180.87 tok/s; 59.80 s server round trip |
| Stateful Responses | passed; the predecessor v0.1 37,591-token prefix hit is not rebound as a v0.2 numeric claim |
| Warm follow-up TTFT | 0.375 s at an 89,216-token session vs 36.697 s cold ([labeled maintainer measurement](BENCHMARKS.md#maintainer-measurement--warm-vs-cold-follow-up-turn-2026-08-29)) |

Hardware envelope, measured with the runtime repo's `hbm_bandwidth_probe`: **1,674.5 GB/s**
sustained pure-read HBM bandwidth on this RTX 5090 — 93.4% of the 1,792 GB/s theoretical peak.
Single-request decode of a memory-bound quantized model lives against that roofline; that is the
number kernel work is judged against.

### RTX 3090 candidate reference

Historical 2026-08-30 native Windows candidate reference (promoted in v0.3.0), recorded as a bounded
transferability point rather than an architecture-normalized comparison: MTP3, INT8 KV, C1, 4,541
computed prefill tokens, and an exact 1,024-token completion at the 300 W profile cap.

| Metric | Value |
| --- | ---: |
| Decode throughput | **90.17 tok/s** |
| Prefill throughput | **893.41 tok/s** |
| MTP3 acceptance | **93.43%** |
| End-to-end wall time | **16.48 s** |
| Peak VRAM | **21,159 MiB** |
| Peak power / temperature | **299.8 W / 47 °C** |

Exact package, source, and phase hashes:
[`2026-08-30-rtx3090-parity.json`](measurements/2026-08-30-rtx3090-parity.json). These numbers are
historical v0.3.0 candidate evidence; current RTX 3090 qualification is in
[`releases/v0.18.0/qualification/rtx3090.json`](../releases/v0.18.0/qualification/rtx3090.json).

## The profiling lane

Runtime mainline commit
[`7c1c1936`](https://github.com/alphastorm/ninfer/tree/7c1c1936d1fd8b645bc7a30cdcbe35cc6b12c206/tools/bench)
turns one-off profiling into reproducible packets without a long-lived controller branch:

- `tools/bench/run_sm120_mtp3_profile.sh` — orchestrates Nsight Compute, Nsight Systems, and
  timing captures for the MTP3 decode loop with container isolation and performance-counter
  checks.
- `tools/bench/run_sm120_q4_mtp3_profile.sh` — profiles the Q4 SwiGLU kernels at decode (`M=1`)
  and MTP3 verification (`M=4`) shapes.
- `tools/bench/summarize_ncu_q4.py` — reduces wide NCU reports to DRAM-bytes and duration ratios.
- `tests/test_sm120_mtp3_profile.py`, `tests/test_sm120_q4_profile.py` — regression checks on
  packet structure, so a captured packet is machine-comparable, not a screenshot.

Packets (NCU/NSYS reports, timing summaries) are preserved in-tree under `profiles/` on that
branch. Current findings from the scripted captures:

- Mean MTP3 round duration: **15.34 ms** with **2.8 accepted tokens per round** on the profiled
  corpus (workload-dependent; the qualification task measured 77.0% acceptance).
- MTP3's verification batch is nearly free relative to its payoff: processing `M=4` tokens costs
  **1.227×** the latency of `M=1` with effectively identical DRAM traffic (96.7 MB vs 96.6 MB per
  layer pass). That asymmetry is why drafting 3 tokens per round wins.

## Agent-probe parity gate

`python3 scripts/agent_parity.py comparison.json --out verdict.json` replays the
retained agent-probe parity rules offline; it does not contact an inference server.
Every input and output names `contract_version` and `rule` explicitly:

| Contract | Accepted input shape | Supported rules and behavior |
| --- | --- | --- |
| `1` | `jobs.<probe>.positions[]` with `position` and the six metrics below; labels optional | `p16-agent-parity/1`: compare the incumbent/candidate metrics already paired on each row. |
| `2` | The same rows, each with a nonempty semantic `label`; optional `concurrent_receipts` naming incumbent/candidate receipt JSON files relative to the comparison | `/1` keeps positional comparisons; `p16-agent-parity/2` pairs sequential positions by label and simultaneous phase members by admission rank. |

The six finite numeric metrics are `{incumbent,candidate}_{prompt_tokens,cached_tokens,server_ttft_seconds}`.
Contract `2` requires unique positions (integer or nonempty string identifiers) and unique
nonempty string labels. Receipt scenarios, requests, phases, summaries and phase members
must have their declared object/array shapes, with nonempty string names and labels;
an optional scenario `repeat` must be an integer.
Both rules keep the same bounds: candidate `(cached − prompt)` ≥ incumbent's, and
candidate server TTFT ≤ incumbent TTFT + max(0.25 s, 25% of incumbent TTFT).
Rule `/2` derives simultaneous membership from receipt `scenarios[].requests[].phase`,
`phases[].summary.per_request`, and submission/first-output timestamps. It uses a common
server admission/start timestamp field when every member of both arms has it; otherwise
both arms use client first-output order. Tied server timestamps use client first-output
order; indistinguishable ranks are invalid. Completion times and engine request IDs
are never ordering evidence. Verdict rows retain the chosen labels, rank, source and bounds.
Every receipt submission/first-output timestamp, and every declared server admission/start
timestamp, must be a finite real number before phase classification, including sequential
phases. Booleans, strings, null, NaN and infinities are invalid, not missing evidence.
Absent server timestamps (or an absent/empty `server_request_done` array) retain the
client-order fallback; malformed event containers or declared timestamps do not.

To replay a legacy unlabeled comparison, explicitly add `"contract_version": 1` and
`"rule": "p16-agent-parity/1"`. There is **no inferred-label compatibility path**:
requesting `/2` with contract `1`, or merely stamping contract `2` onto unlabeled rows,
fails with an explicit `contract-version` error. To use `/2`, recover the semantic labels
and any concurrent phase evidence from retained receipts, then declare contract `2`.
Missing/unsupported versions or rules, invalid pairing evidence, and empty position
arrays fail with exit `2` and an error document, never an empty or partial judgement.
Valid comparisons exit `0` for parity pass or `1` for parity failure. A driver-only job
omits both `positions` and `concurrent_receipts` and is reported as unjudged; its driver
verdict still applies. In contract `2`, a present `concurrent_receipts` must contain
exactly `incumbent` and `candidate`, each naming a nonempty relative receipt path, and
requires nonempty `positions`. Empty, null, false or wrong-shaped declarations are
contract errors (exit `2`), never an implicit switch to label-only or driver-only judging.
Omitting `concurrent_receipts` keeps the documented label-only comparison shape.

This judge is only the numerical parity gate. Every probe oracle must also pass with
no errors/timeouts; the probe drivers retain that responsibility. A parity pass alone
does not qualify a lane. Sanitized replay fixtures and contract regressions live in
`tests/test_agent_parity.py` and `tests/fixtures/agent_parity/`.

## Experiment ledger

The auditable history: what was tried, the exact method, the measured result, and the verdict.
Entries are append-only; verdicts are `kept`, `rejected`, `inconclusive`, or `open`. Evidence paths
refer to the runtime repositories. As of 2026-10-31.

| ID | Area | Hypothesis | Result | Verdict |
| --- | --- | --- | --- | --- |
| EXP-001 | Q4 SwiGLU decode/verify | A small-T MMA path can verify 4 speculative tokens for near-GEMV latency | `M=1` GEMV 76.77 µs at 1,258.7 GB/s; `M=4` MMA 94.21 µs at 1,026.8 GB/s; 1.227× latency for 4 tokens | kept |
| EXP-002 | Q5 linear+add post-mixer | A CTA-collective `mma-r64-c16` kernel beats SIMT split-2 | Candidate 190.46 µs vs production 51.20 µs — 3.72× slower | rejected |
| EXP-003 | GDN state under speculation | Caching gate activations (ReplaySSM) removes recurrent-state drift on MTP rollback | Bit-identical recurrent fold at 167.82 µs/layer; no drift across long contexts | kept |
| EXP-004 | Tensor-core prefill | W4A4 MMA prefill (NVFP4 artifacts) multiplies prefill throughput | 11,191 vs 3,218 tok/s at a 7,680-token prompt — 3.48× (upstream campaign, NVFP4 profile) | kept upstream |
| EXP-005 | RTX 5090 agent-shaped MTP depth | MTP3 remains the best depth on agent-shaped work | K0/3/5/7: 81.57/172.94/149.47/130.19 decode tok/s; K5 and K7 lost to MTP3 in both repetitions | kept |
| EXP-006 | RTX 4090 agent-shaped MTP depth | MTP3 remains the best depth on agent-shaped work | K0/3/5/7: 51.46/110.95/102.87/88.57 decode tok/s; K5 and K7 lost to MTP3 in both repetitions | kept |
| EXP-007 | RTX 3090 agent-shaped MTP depth | MTP3 remains the best depth on agent-shaped work | K0/3/5/7: 36.18/65.36/57.95/50.68 decode tok/s; K5 and K7 lost to MTP3 in both repetitions | kept |
| EXP-008 | RTX 5090 `nvfp4` artifact | The NVFP4 Qwen3.8 artifact beats the pinned `groupwise-int` artifact on agent-shaped session time | Does not start with BF16 KV at 131,072 context (3.28 GB larger weights); with INT8 KV: prefill 6,089 vs 2,740 tok/s (2.22×), decode 168.23 vs 174.25 tok/s (−3.5%), modeled session time −15.5% to −28.7%; role-corpus screen: fewer canary leaks (4 vs 8) but evidence precision −2.4 pp and unsupported-claim rate +2.2 pp | rejected for v0.4; v0.5 RTX 5090 candidate |
| EXP-009 | RTX 5090 KV format and prefill chunk | INT8 KV or a 2,048-token prefill chunk improves the BF16/1,024 incumbent | INT8 KV: +0.0% to +0.8% session time, 4.2 GB lower peak VRAM, worse role-corpus screen on every metric; chunk 2,048: −0.1% to −0.9% | rejected |
| EXP-010 | RTX 4090 prefill chunk | A larger prefill chunk than the shipped 512 improves session time on `rk2v4-e8` | Chunk 512/1,024/2,048/4,096: prefill 1,605/1,877/1,971/1,974 tok/s, decode 110.69/111.82/112.92/108.37 tok/s; 2,048 clears the 5% margin in every repetition (+5.5% to +12.8%), 1,024 and 4,096 do not | kept — requalify at 2,048 |
| EXP-011 | RTX 3090 prefill chunk and context | The shipped INT8/1,024/65,536 profile leaves speed or capacity on the table | Chunk 512/2,048: −2.9% to −0.5%; `--max-context 131072` fits with automatic KV capacity 131,072 at 22,465 MiB peak and identical throughput (65.08 vs 65.69 decode tok/s) | kept — qualify 131,072 context |
| EXP-012 | Template-fork warm starts (all lanes) | Checkpointing a prefilled template and forking subagents from it starts them hot, including across a process restart | RTX 5090 (57.9K-token template): device-resident sibling forks alternate 1.3 s / 22.5 s (anchor / full re-prefill) while a 67.7K template gives four 1.3 s forks; after restart the 4.51 GB checkpoint restores in ≈23.6 s ≈ the 21.8 s cold prefill. RTX 4090: no sibling reuse (41–47 s per fork) and a 1.13 GB restore takes ≈130 s vs a 41 s prefill. RTX 3090: no sibling reuse (49–51 s) and restore ≈91 s vs 49 s | negative; hot forks only on the 5090 and only reliably ≥ ~64K tokens; restore never beats re-prefill |
| EXP-013 | RTX 5090 fanout anchor retention | The sub-64K alternation is a serve policy defect fixable in source | Capacity, not policy: private catalog 2 entries + 2 device-state slots; search-cap and marker source changes rejected on the probe; `--max-private-continuations 8 --device-state-slots 4 --host-state-slots 24` on the unchanged binary keeps 12/12 forks on the anchor path at 57.9K, 67.7K, and loaded 57.9K for 0.43 GiB slack, at the cost of one 5.29 s (vs 1.39 s) first fork at 67.7K | kept — v0.4.8 RTX 5090 candidate profile, as a trade |
| EXP-014 | Native-lane checkpoint restore | The slow restore is a first-read effect that a second restore avoids | Second restore not faster (4090 132.8 → 149.0 s at 1.13 GB; 3090 91.8 → 92.2 s at 1.68 GB); status endpoint blocked for the whole restore; restore path is the cost | open — filed upstream |
| EXP-016 | Fleet routing (all lanes) | Splitting a fixed independent-job batch across lanes completes it faster than the RTX 5090 alone | 14-job frozen corpus: 5090 alone 66.8 s; 5090+4090 51.2 s naive / **43.4 s** cost-aware (1.54×); three lanes 47.2 s naive / **32.3 s** cost-aware (2.07×); role-pinned 100.3 s (0.66×). Long-prefill jobs are 3.3–6× more expensive off the 5090; short jobs cost the same everywhere | kept — measured boundary for the fleet configuration; cost-aware dispatch is the recommended policy |
| EXP-017 | Native-lane checkpoint restore path | The per-page-segment reader, not the disk, is the restore cost; one read per staging window closes it | Fix on both native lanes, same session shapes as EXP-014: RTX 4090 1.13 GB **146.6 → 5.6 s** and **133.4 → 5.6 s** (24–26×); RTX 3090 1.68 GB **91.8 → 10.8 s** and **92.2 → 10.7 s** (8.5×); planted ledger keys quoted exactly after every restart on both lanes and in-process | fixed at source — lane commits `d22ce3fd` (4090) and `3756db6e` (3090); shipped in `v0.4.9` (components `v0.2.2-qwen38-4090-durable.1`, `v0.2.4-qwen38-3090-beta.1`) |
| EXP-018 | Checkpoint replication (all lanes) | A checkpointed session survives the machine losing its local state, and a replica cannot be forged | Export, carry off, destroy the local copy with the server stopped, carry back, import, restart, exact retrieval of planted keys: RTX 5090 4.5 GB import 10.1 s / restored 24.8 s; RTX 4090 1.13 GB 4.2 s / 7.4 s; RTX 3090 1.69 GB 11.9 s / 11.5 s. Payload byte flip refused by the tool; manifest edit with consistent digests quarantined by the runtime's origin authentication (no resurrection) | delivered — roadmap v0.5 §1; origin authentication ported to both native lanes and requalified |
| EXP-019 | Replica transport (cross-site) | Moving a replica between owner sites is minutes, and the earlier 1.8–3.5 MB/s was the workstation's transpacific path plus single-stream ssh | Full round trip NYC→SF→NYC→restore on the 67 ms tailnet path: 1.13 GB out at **11.5 MB/s**, back at **56.3 MB/s**, imported in 2.6 s, planted keys exact after the return. Windows OpenSSH cannot carry bulk between two Windows hosts at all; a Linux receiver on the same link is 5× faster than a Windows one | fixed — `scripts/hosts/pscp.py` (ranged ssh reads, or bearer-token ranged HTTP for the Windows-to-Windows case); host ssh compression, the WSL sshd port collision, and fleet host-to-host trust corrected |
| EXP-020 | NAS replication target | A LAN-local NAS is a better replication target than another workstation, and a Synology's tailnet path is not | Same-site LAN, 2 GiB incompressible, raw unbuffered IO: the RTX 4090 host **115.8 MB/s** write / **117.6 MB/s** read, the RTX 3090 host 96.0 / 102.3 - about 1 GbE line rate. The same NAS over the tailnet from the other site does **6.4 MB/s** write / 22.7 MB/s read, worse than the direct host-to-host path (11.5 / 56.3). One published generation replicated and verified in place from each co-located lane | adopted as the replication target for the two co-located lanes; the remote lane keeps host-to-host transport |
| EXP-021 | Warm arrival after a restart (5090) | A restored session's first sibling fork reuses the template prefix instead of re-prefilling it | Two source defects found and fixed: a fanout fork left its long anchor on the parent, so every checkpoint taken after a fanout omitted it (payload 4,351,909,712 vs 4,505,864,319 bytes), and consuming a session endpoint double-charged a shared anchor to the entitlement (HTTP 500 on resume, now 1.19 s). With the fixes a fork issued as the first post-restart request hits `private_long_anchor` immediately; when an endpoint resume comes first, one fork still re-prefills (22.2 s) | partial - fixes proved on a candidate binary on branch `feat/warm-arrival`, not released; the resume-first path and the hash-bound 24 s restore remain open |
| EXP-022 | Warm arrival, resume-first (5090) | The remaining re-prefill after an endpoint resume is a candidate-admission defect | Not admission: anchor replacement. A continuation keeps two long anchors and every Responses request captures two (inherited and pre-generation frontier), so a continuing turn replaced both, and the victim rule (lowest frontier first) evicted the template anchor every sibling reuses; the resume at 67.9K left the next fork on `root` (28.5 s). Replacement now evicts the anchor whose loss costs the least re-prefill (smallest gap to its lower neighbour, ties to the newer). After a restart, resume then two forks: **4.2 s / 2.9 s / 1.3 s**, both forks `private_long_anchor`; fork first: 3.7 s / 1.3 s. Restore plus the sequence is 8.4 s and 6.7 s against 26.7 s for not checkpointing at all | fixed at source - branch `feat/warm-arrival` commit `fb9b35da`; roadmap v0.5 §2 holds on the candidate |
| EXP-023 | Checkpoint restore cost (5090) | Restore is hash-bound: two scalar SHA-256 passes over 5 GB at queue depth one | Scalar SHA-256 measured at 0.33 GB/s on the appliance's Zen 4 against 2.66 GB/s with the SHA extensions; the load pass was dropped (the streamed hash on the exact bytes the engine consumes is the single verification, `alphastorm/ninfer#21` closed by construction), the io_uring reader issues eight 4 MiB reads per batch on its own thread, and the next 32 MiB batch is on the device while the previous one hashes. A 5.2 GB session restores in **3.8 s / 3.8 s** (was 24-27 s), planted keys exact after both restarts; a flipped byte in the middle of the 4.4 GB KV payload is refused (404 `previous_response_not_found`, 2.8 s), the generation reports `corrupt`, then quarantines | fixed at source - commits `f841d42d`, `d956e6d6`; verified-or-refused re-proven live |
| EXP-024 | RTX 5090 requalification (v0.5.1 candidate) | The warm-arrival and restore changes hold under the lane's own qualification gates on the canonical build | Appliance-local build of `d956e6d6` (binary `71edc2f6`, 9/9 host tests, packaged with SBOM, published as `v0.5.1-qwen38-5090-beta.1` and wrapped by the runtime-image workflow into `12ef2d9e...`, whose binaries measure byte-identical) on the unchanged v0.4.8 arguments, started through the lifecycle tool from the published image (configuration `efacac23...`): exact 130,048-token retrieval at 2,180 tok/s cold (v0.4.8: 2,207), 2,048-token decode at 138.2 tok/s with 41.2% MTP acceptance (136.0), agent protocol with no resurrection across restart; fanout 24/24 forks on `private_long_anchor` across 57.9K, 67.7K, and 80.0K templates in-process and after a verified restart with the resume first (post-restart forks 1.25-1.41 s; v0.4.8 paid 22.2 s on the first); warm arrival in both orders with an in-process control; 4.5 GB explicit save 4.4 s (was 12.6 s, the writer's digest also runs on the SHA extensions) | passed - `v0.5.1` staged with the published component; external acceptance and the product cut remain |
| EXP-025 | Native lanes on mainline (4090, 3090) | The mainline runtime - context cache, warm arrival, streamed restore - serves the two native Windows lanes at least as well as their divergent branches | `port/native-lanes-on-mainline` built with MSVC 19.44 for `sm_89` and `sm_86`, 100/100 registered tests on each build on the Ada GPU (94 run; the six real-artifact and external-tokenizer suites skip), and served in candidate windows on both hosts. Same fixture, gates, host, and day as the installed releases: RTX 4090 130,048-token exact retrieval **86.8 s vs 97.5 s** (1,499 vs 1,333 tok/s), 2,048-token decode **103.8 vs 88.4 tok/s** wall; RTX 3090 **208.6 vs 219.5 s** and **60.3 vs 52.8 tok/s**. 67.7K template: four sibling forks hot at 1.8-2.0 s (4090) / 2.5-2.9 s (3090) before a restart and 1.8-1.9 s / 2.5-2.6 s after it, every fork `private_long_anchor`; warm arrival in both orders; a 2.9 GB checkpoint restores in 4.2-5.0 s (4090) and 16.6-17.1 s (3090) with a flipped byte refused and quarantined. Five source defects surfaced only on the hardware (cooperative grids sized for 170 SMs, an INT8 prompt-attention CTA that spilled 200 B/thread on `sm_89`, a serialising DirectStorage read queue that failed every streamed restore, an unlogged restore refusal, an unbounded residency query). The RTX 4090's WDDM budget at 131K INT8 leaves 169 MiB with four device-state slots and the driver pages: decode 47 tok/s and every fork 2.5× slower; two slots (463 MiB free) is the profile, one slot re-prefills the first fork | kept - both lanes' next candidates build from mainline; requalify each through its lifecycle tool before any release |
| EXP-026 | Native lane release qualification (4090, 3090) | The mainline-built native lanes pass their own lifecycle qualification end to end from a clean state | Five blockers in the release path found, reproduced, and fixed: the mainline bench had no `--version` arm the package's identity binding requires; `transfer_install` relayed the 0.6 GB package through the operator's Mac (0.33 MB/s, 900 s timeout) instead of host to host (**104.7 MB/s**, 16 ranged-HTTP streams); the staging root inherited `BUILTIN\Users` write access on the host whose qualification parent did not exist yet; the managed install splatted its arguments positionally; and mainline applied `X-NInfer-Session` only on the bodyless Responses routes, so the lane probe's identity conflict returned 200. Both lanes now pass preflight through install and reach `protocol`. The RTX 4090 lane's pinned pools are sized from measurement: 24 host state slots with the 8 GiB default Host KV is 13.3 GB pinned and failed `cudaMallocHost` on two managed starts (the controller's 18 GB pre-launch read empties the free list), 4 GiB is 9.2 GB and starts; 8 slots start but fail the protocol contract in 41 s | in flight - one open runtime invariant defect (a catalogued continuation's last state replica is evictable while admission plans reuse from it) and the RTX 3090 host offline |
| EXP-015 | Lane requalification (all lanes) | The three configuration-only changes hold their measured gains under each lane's own qualification gates | RTX 4090 chunk 2,048: 102,060-token session 68.0 s vs 84.9 s shipped, protocol/persistence/golden unchanged. RTX 3090 131,072 context: exact 130,048-token retrieval in 218 s, 90.2 decode / 890.7 prefill tok/s at 300.4 W, 22,548 MiB peak. RTX 5090 context-cache profile: 130,048-token prefill 2,207 tok/s cold, 136.0 decode tok/s at 41.2% MTP acceptance, 4/4 anchor hits at 57.9K and 67.7K, 4.5 GB save, verified restart; first post-restart fork re-prefills once | kept — `v0.4.8` draft staged; publication blocked on component releases and external acceptance |
| EXP-054 | RTX 5090 MTP3 decode round attribution | The verify pass's Q4/Q5 projections, not launch overhead, hold the round above the bandwidth floor | 26K-context round 17.23 ms (production 17.1 ms), GPU busy 99.2%; W8 LM head, MTP layer and Q4 draft head at 97–104% of 1,674.5 GB/s; Q4 gate/up 82.5%, Q5 down 75.8%, Q5 mixer outputs 68.0%, GDN value/z 66.2%, GDN query/key 39.7%; 2.6 ms (15.1%) recoverable at 90% | kept |
| EXP-055 | RTX 5090 and RTX 4090 MTP3 decode kernels | Row-blocking the small-T Q4/Q5 projections and removing the Q4 gate/up bank conflicts recover a material share of the round with bit-identical outputs | RTX 5090 packaged `v0.6.10`: 26K-context round 17.75 → 16.08 ms and decode +10.3% to +11.0% from a seed context to 31K (A/B/B/A); 32/32 kernel points byte-identical, 89/89 role-corpus cases identical, 130,048-token retrieval exact; Q4 gate/up 82.5% → 92.6% of the floor. RTX 4090: the split2 row pair ran 19% slower at T=4 and C1 decode fell 2.7%; with one-row split2 on the native lanes, 157.89 tok/s (+2.8%) | kept |
| EXP-056 | RTX 5090 and RTX 4090 MTP3 decode remainder | Warp, register, prefetch and L2 hand-off schedules that keep every output byte recover part of the round EXP-055 left above 90% of the floor | 1,631 (RTX 5090) and 449 (RTX 4090) private-launcher rows per pass byte-identical; no T=4 projection or GDN record/fold schedule beats production beyond noise, and an L2 hand-off prefetch only speeds a cold consumer (the mixer takes 16.4 µs with its whole weight in L2 and 16.6 µs in the production graph). Two-warp BF16 attention above the 16K split tier: in-graph attention partial −6.1% at 26K, decode +0.28% to +0.91% from 26K to 60K, public op 3.7–5.4% slower at 16,387–20,000 keys. Exclusive-time remainder 1.15 ms (7.2%) | rejected — no `v0.8.2` |
| EXP-057 | RTX 5090 MTP3 Q5 verify projections | A small-T tensor-core route for the T=4 Q5 projections recovers the remainder that byte-identical schedules could not, with output changes the role corpus cannot tell from production's | Round −4.4% to −5.4% at every context and decode +5.05% at 26K, +4.64% at 60K, +6.73% at 1,024 (A/B/B/A); MLP down −13.5% per call in graph. 27 of 118,784 isolated T=4 outputs differ from production's by one bf16 ulp, closer to FP64; 58 of 89 role-corpus cases differ from `v0.8.1` (a 16-warp control: 54). Quality aggregates within the range of production and four earlier precision variants except the candidate's redaction controls (0.500 against a 0.625 floor), its evidence precision (0.994, above the range) and one unanswered control case; 130,048-token retrieval exact. Paired redaction screen (8 controls × 8 whitespace variants on fresh servers): pass 30/56 vs 32/56 (Fisher p = 0.42), synthetic-secret leaks 69 vs 61 | rejected — more leaks; no `v0.8.2` |
| EXP-058 | RTX 5090 MTP3 decode draft source and launch chain | Changing where drafts come from (the full LM-head proposal head, prompt-lookup drafts), or chaining the round's kernels with programmatic dependent launch, speeds decode without changing an output byte | Full LM-head proposal head: 89/89 role-corpus cases identical to `v0.8.1`, 3.397 against 3.336 tokens per round, decode 9.2% slower. Prompt lookup (simulated, three-token window): 3.086 against MTP's 3.206 tokens per round on the role corpus, +2.6% on agent sessions. PDL chain: decode −4.7% to −6.2% (MLP down 46.1 → 62.2 µs behind the draining gate/up projection); early release from single-wave kernels only: +0.13% to +0.45% (A/B/B/A), inside drift, 24/24 oracle tests, identical speculative statistics. Round boundary: 476–494 µs per 26K round, 174 µs of it the replay fold and 235–239 µs `cudaGraphLaunch` CPU time | rejected — no `v0.8.2` |
| EXP-059 | RTX 5090 prefill attribution on agent traffic | Part of production's prefill runs far from its hardware floor, and a change that keeps output bytes could shorten it | Prefill is 37.8% of agent GPU time (446 v0.7.0 requests). Cold starts (27 requests, 64% of prefill) run at 74% of the dense BF16 FLOP floor: projection GEMMs at 76–82% of the 209.5 TFLOPS peak, attention 70%, attention input 51%. A production-shaped warm turn (about 400 computed tokens at 29K context) took 283–307 ms of GPU in six passes split at chat-template boundaries: four 2–3-token fragments 59–60 ms, prompt attention about 27 ms per larger pass (91–95% of one SM's peak on 24–144 of 170 SMs), projections 155–178 ms against an 89–94 ms floor. Byte-keeping ceiling about 27 ms per extra prompt pass; fewer passes (an estimated 115–130 ms) and FP8/NVFP4 change bytes | open — measure only |
| EXP-060 | RTX 5090 new agent sessions after idle | Production's new sessions (the shared-stable-prefix warm turns) are slow for a reason that a change keeping output bytes could remove | 103 of 106 v0.7.0 new sessions (138 of 446 agent requests) arrived 5 s or more after the previous request finished: prefill 0.317 s (TTFT 0.361 s) against 0.171 s (0.199 s) for the three that arrived sooner. After the last response the GPU steps P1 → P3 (about 2.0 s) → P5 (7.4 s) → P8 (9.2 s). Served on production's binary, new sessions after 12–30 s idle took 0.253–0.334 s against 0.156–0.160 s back to back, their prompt pass 205–287 ms against 123–127 ms. A 1 Hz 0.4 ms keep-alive kernel changed nothing | open — measure only |
| EXP-061 | RTX 5090 keep-warm load between agent requests | A light GPU load run only while the engine is idle keeps the card out of its slow idle P-states and brings new sessions after idle back to back-to-back latency | A single-warp kernel spinning 30 ms of every 100 ms holds P1 (memory 13,801 MHz); 25% reaches P8 after 13.7 s, 1–20% within 3.4–7.4 s, and all-SM spins at 10–20% and 64–256 MiB copies do not hold. The 30% load drew 88.8–91.6 W beside production's binary against 29.0 W idle. As a grace period it held P1 through 12 s and 60 s gaps: new sessions prefilled in 0.155 and 0.180 s (TTFT 0.173 and 0.201 s) against 0.155–0.159 s back to back and 0.353 s (TTFT 0.417 s) after 30 s without it | open — measure only |
| EXP-062 | RTX 5090 engine keep-warm grace period | Built into ninfer-serve, a grace-period keep-warm brings new sessions after idle back to back-to-back latency without changing outputs or slowing the requests that arrive while it runs | `--gpu-keep-warm-ms N` (off by default): once the Engine goes idle, a single-warp kernel spins 3.5 ms of every 10 ms on its own stream until a request is pending or N ms pass. It held P1 at 99.5–102.7 W against 29.3–29.8 W idle. New sessions after 12–58 s idle prefilled in 0.155–0.157 s (TTFT 0.173–0.181 s), as back to back, against 0.253–0.304 s (TTFT 0.316–0.366 s) with it off. All 89 role-corpus cases stayed byte-identical with it on and off. The 80 back-to-back corpus requests: paired TTFT median −0.1 ms, worst +4.4 ms. In v0.7.0 traffic a 60 s grace catches 84 of 138 idle arrivals at about 2.3 W average | kept — shipped in v0.8.2 |
| EXP-063 | RTX 5090 redaction screen for the EXP-057 route | With enough paired samples to tell a worse route from noise, and its rule fixed before any candidate data, the EXP-057 Q5 small-T tensor-core route is not worse than production at redaction | Rebased onto v0.8.2's source, the route reproduced EXP-057's candidate outputs on all 89 role-corpus cases. On 504 paired prompts (7 redaction controls x 72 whitespace variants, fresh servers) it leaked 561 synthetic secrets against production's 582 (ratio 0.964, one-sided 95% upper bound 1.012 against a 1.10 margin) and passed 53.2% of prompts against 52.6% (lower bound −1.2 pp against −5 pp); both arms reproduced their determinism prompts and EXP-057's 64 shared prompts byte for byte. Release builds A/B/B/A: MTP3 round −3.5% to −4.9%, decode +4.4% at 26K, +3.6% at 60K, +6.3% at 1,024 | kept — shipped in v0.8.3 |
| EXP-064 | RTX 4090 idle-to-new-session latency | The RTX 5090 keep-warm pattern also holds sm_89 at its working P-state | New sessions after 12-58 s idle prefilled in 0.29-0.47 s versus 0.146 s back to back; the 3.5 ms/10 ms spin did not hold P2. The later sweep motivated EXP-066 ([receipt](measurements/2026-09-27-rtx4090-engine-keep-warm.json)) | rejected — RTX 5090 spin pattern on sm_89 |
| EXP-065 | Upstream engine window against the shipped RTX 5090 runtime | Upstream e31bc99b improves the shipped lane enough to justify merging | Decode about 18% slower, fanout 0/4 versus 4/4; its 1.5% single-run prefill lead was already present in EXP-048 ([receipt](measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json)) | rejected — merge deferred |
| EXP-066 | RTX 4090 long-spin engine keep-warm | An sm_89-specific 50 ms/100 ms spin restores post-idle prefill to back-to-back speed | With a 60 s grace, new sessions after 12-58 s idle prefilled in 0.146-0.148 s (TTFT 0.167-0.178 s); all 31 outputs byte-identical, about 72 W above idle while held. A request arriving mid-spin can overlap one warp for up to 50 ms ([receipt](measurements/2026-09-27-rtx4090-keep-warm-long-spin.json)) | kept — shipped in v0.8.4 RTX 4090 v0.6.9 |
| EXP-069 | RTX 4090 Q5 small-T tensor-core route | The sm_89 route clears the pre-registered decode-gain thresholds of 2.0% at 26K and 1.0% at 60K | Measured +0.38% at 26K and +0.40% at 60K; rejected by the fixed rule, so the published v0.6.9 package keeps its decode kernels ([receipt](measurements/2026-09-28-rtx4090-q5-small-t-mma.json)) | rejected |
| EXP-077 | RTX 5090 two requests in flight | With `--max-concurrency 2` and OMP's limit at 2, the lane serves two requests with more aggregate decode and without losing outputs, reuse or durability | The shipped v0.6.13 image paired two decodes at 190.0-191.1 tok/s against 166.7-167.1 one at a time (1.14×): eight-token verify rounds left the Q5 tensor-core route, 12.8 ms of a 23.9 ms round. Runtime v0.6.14 (`e20060b6`) runs them on it: **281.1-283.0 tok/s (1.68-1.70×)**, 143.5-152.8 each, 89/89 role-corpus cases byte-identical to one at a time on the candidate and the published image. A request that does not fit waits at the server; `--pending-timeout-ms 180000` replaces the 30 s default that expired it. The v0.8.7 lane set passed on the final profile. A decode beside a 71,641-token prefill still slows to about 30 tok/s, and stock OMP's wall time at limit 2 followed what its subagents generated rather than the overlap ([receipt](measurements/2026-09-29-rtx5090-two-requests-in-flight.json)) | kept — v0.9.0 |
| EXP-078 | RTX 5090 DFlash2 speculative backend | DFlash2 K=7 (Z-Lab's five-layer block drafter) decodes this lane's workload faster than MTP3 at the shipped BF16 KV, 131,072-token and 1,024-chunk settings | Upstream `d44ab584` on the published v3 artifact, one request: role corpus **253.63 vs 197.80 tok/s (+28.2%)**, 4.631 vs 3.332 tokens per round, all 84 cases faster; a code answer +27.0%/+20.8%/+56.4% behind 32K/64K/120K tokens; prefill unchanged. Costs 1.65 GiB of weights; two requests need two fewer device state slots and leave 131,520 KV tokens against MTP3's 160,256, pair 453.95 vs 374.94 tok/s. Upstream with DFlash2 decoded the corpus 6.9% faster than shipped v0.9.0 ([receipt](measurements/2026-09-30-dflash2-rtx5090.json)) | open: port campaign |
| EXP-079 | RTX 5090 DFlash2 ported onto the fork | Upstream's DFlash2, ported onto the shipped runtime's source (`e20060b6`), decodes the role corpus at least 15% faster than shipped v0.9.0 and leaves MTP3 byte-identical | MTP3 on the spike binary: 89/89 byte-identical to shipped, 238.41 vs 237.37 tok/s. DFlash2 K=7: role corpus **228.90 tok/s (-3.6%)**, 61 of 84 cases faster (median x1.24), 4.596 tokens per round against upstream's 4.631. Its round cost grows with context: a code answer at 355.15/126.78/83.74/44.54 tok/s behind 0/32K/64K/120K tokens against shipped 250.71/229.84/212.09/180.11, rounds 16.2 to 126.3 ms (about 16 ms plus 0.92 ms per 1K tokens of context) where upstream's DFlash2 rounds go 17.7 to 23.0 ms; prefill unchanged ([receipt](measurements/2026-09-30-dflash2-fork-spike-rtx5090.json)) | rejected by rule: profile the long-context round |
| EXP-080 | RTX 5090 NVFP4 and K8V4 KV under DFlash2 ([#71](https://github.com/alphastorm/omp-ninfer/issues/71)) | A 4-bit KV payload returns the capacity DFlash2's weights take from the two-request profile without costing speed or screened quality | Upstream `d44ab584`, DFlash2 K=7: both formats start two requests with four device state slots and **262,144 KV tokens** (BF16: two slots, 131,520; shipped v0.9.0: 160,256). One request: KV payload 8.00 → 2.25/3.14 GiB, VRAM 29,594 → 23,706/24,618 MiB, role corpus 253.63 → 256.48/253.12 tok/s, rounds behind 120K tokens 23.0 → 21.2/20.4 ms, K8V4 prefill +15.3% at 120K. Evidence precision 0.993 → 0.979 for both, unsupported claims 0.225 → 0.225/0.214, leaks 10 → 9/7 (one unpowered run each). K8V4's 120K answer decoded 3.55% slower through fewer tokens per round, past the 3% bound ([receipt](measurements/2026-09-30-kv-nvfp4-k8v4-rtx5090.json)) | NVFP4 kept as a profile candidate; K8V4 inconclusive |
| EXP-081 | RTX 5090 DFlash2 fork port with upstream's 24-head verify route | The port's context-dependent round cost is the target attention route of one request's 8-token verify; with upstream's route the port decodes the role corpus at least 15% faster than shipped v0.9.0 and leaves MTP3 byte-identical | One cherry-pick (upstream `4b0eb36c`, which EXP-079's port skipped as 35B retuning) sends one request's 7-8-column verify on the 27B's 24 query heads to ChunkedSmallT above 320 keys instead of the Prompt kernel, which does not split the KV sequence. Round slope 0.917 → **0.085 ms per 1K tokens** (upstream 0.044). Role corpus **288.09 tok/s (+21.4% over shipped)**, +13.6% over upstream's DFlash2, 83 of 84 cases faster; a code answer +46.7%/+31.9%/+37.0%/+23.8% over shipped behind 0/32K/64K/120K tokens; prefill unchanged. MTP3 89/89 byte-identical; DFlash2 86/89 identical to shipped (EXP-079: 41). Two requests unchanged: pair 269.17 vs shipped 388.42 and upstream 453.95 tok/s, rounds 37.1 vs 22.0-22.4 ms ([receipt](measurements/2026-09-30-dflash2-verify-route-rtx5090.json)) | go by rule: integration campaign, two-request rounds first |
| EXP-082 | RTX 5090 two requests' DFlash2 verify on the Q5 tensor-core route | Two requests' K=7 verify is 16 columns and leaves the fork's Q5 tensor-core route, which accepted only 4 and 8; with 16 columns on it, a pair closes most of its round gap to upstream with MTP3 byte-identical | The kernel takes 16 columns with a second m16n8k16 MMA per k16 step; MLP down, GDN value/z and attention gate/value route 16 columns to it (spike `7e4d120a`), per-column arithmetic unchanged. Pair rounds **37.1 → 22.7 ms** (upstream 22.0-22.4, 97% of the gap closed); pair **420.86 tok/s** against shipped 388.42 (+8.4%) and upstream DFlash2 453.95 (-7.3%, its outputs drafted 5.22-5.63 tokens per round against 5.02-5.10); solo 369.64. MTP3 89/89 byte-identical; 6/6 op tests and the DFlash2 real-model test at one and two requests passed ([receipt](measurements/2026-10-01-dflash2-pair-q5-tensor-cores-rtx5090.json)) | kept by rule |
| EXP-083 | RTX 5090 DFlash2 sessions on the durable store | With the draft context ring carried through checkpoints, a DFlash2 session survives export, restart and restore exactly, and sibling fanout and multi-session pressure keep their reuse, with MTP3 unchanged | The ring already lived in every StateImage; spike `03212c9d` keys the backend-KV file on the paged backend cache DFlash2 lacks and refuses an export whose ring lags its frontier. Engine round trip: the restored next turn matched in tokens, 13 rounds and per-position acceptance (82 of 89 drafts); a ring-zeroed restore drafted 14 rounds, 81 of 95. Two container restarts restored a 57,889-token session hot (52 and 260 tokens computed), keys exact, **5.47/6.67 tokens per round** against 5.10 in process; checkpoint 4.41 GB in 3.29 s (shipped MTP3 4.51 GB). Multisession reuse lost 2 of 12, the same two steps as shipped v0.9.0; one 140-token sibling re-prefilled under two-slot device-state pressure where shipped reused a 61-token anchor. MTP3 89/89 byte-identical ([receipt](measurements/2026-10-01-dflash2-durable-store-rtx5090.json)) | ring kept; the rule as written said reject on reuse, a bar set without the incumbent's value |
| EXP-084 | RTX 5090 NVFP4 paged KV on the fork's DFlash2 port | Upstream's NVFP4 KV, ported with every BF16, INT8 and FP8 path unchanged, gives the two-request DFlash2 profile four device state slots and at least 262,144 KV tokens at no more than 3% round cost, with the durable store intact and MTP3 byte-identical | Spike `008a7781` ports NVFP4-G16 storage, append and causal attention from upstream `d44ab584` behind an explicit storage identity, dispatched before the unchanged legacy router. Two requests start with four slots and **262,144 KV tokens** (BF16: two, 131,520; shipped v0.9.0: four, 160,256); KV payload 8.03 → 4.50 GiB. Rounds equal BF16 at short context and in the pair and are **12%/19%/27% shorter** behind 32K/64K/120K tokens (25.89 → 18.82 ms at 120K). A 57,889-token session restored hot after two restarts (214 and 236 tokens computed) from a 1.66 GB checkpoint (BF16 DFlash2: 4.41 GB); sibling reuse matches shipped's and multisession lost none (shipped: 2 of 12). MTP3 89/89 byte-identical. One unpowered corpus run: decode +24.0% over MTP3, evidence precision 0.951 against 0.994 ([receipt](measurements/2026-10-01-dflash2-nvfp4-kv-rtx5090.json)) | kept; attention tests passed in a second window after a test-only fix; powered quality screen next |
| EXP-085 | RTX 5090 powered role-corpus quality screen for DFlash2 | The DFlash2 K=7 NVFP4 two-request profile is no worse than shipped v0.9.0 MTP3 on every primary gate metric, by fixed margins; if not, DFlash2 with BF16 KV is | [`scripts/quality_screen.py`](../scripts/quality_screen.py), fixed before any data: 84 counted cases × 8 whitespace variants and 7 redaction controls × 72 (1,120 prompts per arm), paired bootstrap bounds. NVFP4: recall +0.2 points, evidence precision -0.3 (lower bound -1.2; the single run's -4.3 was noise), but unsupported claims +1.8 (upper bound **3.7** against 3.0) and leaks 561 → 609 (ratio upper bound **1.141** against 1.10). BF16 DFlash2: **1,091 of 1,120 outputs byte-identical to shipped**, every bound inside (leaks 561 → 561). Both decoded ~17% faster on the screen; every arm deterministic ([receipt](measurements/2026-10-01-dflash2-powered-quality-screen-rtx5090.json)) | NVFP4 fails, BF16 DFlash2 passes |
| EXP-087 | RTX 5090 FP8 KV under DFlash2 (pre-check) | The fork's existing FP8 E4M3 row-256 KV gives the two-request DFlash2 profile four device state slots and at least 160,256 KV tokens at no more than 3% round cost, with exact long-context retrieval, and so earns the powered screen | Same spike binary, `--kv-dtype fp8`: **four slots and 249,216 KV tokens** in 7.66 GiB (BF16: two, 131,520 in 8.03 GiB). Rounds equal BF16's at short context and in the pair and **7%/12%/18% shorter** behind 32K/64K/120K tokens (25.90 → 21.35 ms). Exact 130,048-token retrieval in 57.0 s, agent protocol with restart passed, decode_2048 172.3 tok/s. Corpus: 27 of 89 outputs match shipped; one unpowered run at or above MTP3's aggregates (leaks 7 vs 10) ([receipt](measurements/2026-10-01-dflash2-fp8-kv-precheck-rtx5090.json)) | earns the powered screen (EXP-088) |
| EXP-088 | RTX 5090 powered quality screen for DFlash2 with FP8 KV | Under EXP-085's unchanged rule, against its shipped v0.9.0 MTP3 runs, the DFlash2 K=7 FP8 KV two-request profile is no worse than shipped on every primary gate metric | 1,120 paired prompts, 924 outputs changed. Recall -0.05 points, evidence precision +0.02, unsupported claims +1.2 (upper bound **2.8** against 3.0), redaction pass rate +0.8: all inside. Secret leaks 561 → 604, ratio 1.077 with upper bound **1.135** against 1.10: outside. Every validity check held ([receipt](measurements/2026-10-01-dflash2-fp8-kv-quality-screen-rtx5090.json)) | fails on secret leaks |
| EXP-086 | RTX 5090 pre-acceptance probes on the adopted DFlash2 BF16 profile | The DFlash2 K=7 BF16 two-request profile with the durable store passes v0.9.0's profile gates, two-requests-in-flight matrix and restart, fanout, warm-arrival and agent-mix probes | Every probe passed: 130,048-token retrieval exact in 58.4 s, agent protocol across a restart, near-capacity pair taking turns, fanout and warm arrival at or above v0.9.0, 0 of 24 fresh sessions at root. The written refused-0 clause failed: the matrix's stop refused 6 saves, where v0.9.0's refused 7. Free-form reasoning decoded **2-5% slower solo and 21-27% slower in pairs** (207.5-222.1 against 281.1-283.0 tok/s): 2.5 tokens per round against MTP3's 2.3, in 23.1 against 15.6 ms pair rounds. One of two sessions resumed from root after a restart (27.0 s against 5.5 s) ([receipt](measurements/2026-10-01-dflash2-pre-acceptance-probes-rtx5090.json)) | fails the written rule on a clause v0.9.0 also fails; costs reported |
| EXP-089 | DFlash2 on the RTX 4090 and RTX 3090 native lanes | The fork's DFlash2 port, built for sm_89 and sm_86, starts at the lanes' 131,072-token INT8 profile and decodes the role corpus at least 10% faster than MTP3 | Both builds fail at device link: three DFlash2 W8 kernels hold 49,664-50,176 bytes of static shared memory against sm_89's and sm_86's 49,152 (sm_120a links them). No window ran; both lanes unchanged. The RTX 4090's MTP3 profile leaves 5.82 GiB after weights for a 5.22 GiB runtime, and the drafter adds 1.65 GiB, so about 85K tokens would fit [inference] ([receipt](measurements/2026-10-01-dflash2-native-lanes-feasibility.json)) | no-go as ported; native lanes stay on MTP3 |
| EXP-090 | RTX 5090 DFlash2 under stock OMP's sampling | Under OMP's sampling (temperature 1.0, top_k 20, top_p 0.95), DFlash2 K=7's role-corpus quality is not grossly worse than MTP3's on the same binary, and stock OMP's two-subagent proof at OMP's limit 1 fails no more often on DFlash2 | One sampled corpus run per arm: recall -0.3 points (95% interval -3.6 to +3.2), unsupported claims +2.2 (-4.5 to +9.0), evidence precision +1.8 (0.0 to +4.3), schema validity equal. Same-seed outputs diverge by design: the verifier accepts a draft with probability p(d) and otherwise samples the residual. Proof: **2 of 10 failed on DFlash2, 3 of 10 on MTP3**. Three (one DFlash2, two MTP3) were the proof's code reader, which missed exact codes after an escaped newline in a scout's JSON result (fixed); one MTP3 parent's first task call was refused by OMP and reissued; one DFlash2 run saw two requests at limit 1 because a cancelled background request stayed open 0.83 s into the next one, its cancel registered in the same millisecond as a pre-eviction checkpoint save ([receipt](measurements/2026-10-01-dflash2-sampled-behavior-rtx5090.json)) | no gross degradation; no DFlash2-specific proof effect |
| EXP-092 | RTX 5090 DFlash2 round costs | One 24-head BF16 small-T attention launch per layer for an 8-column verify, instead of 6- and 2-column chunks that each read the layer's whole KV, and the pair's 16-column K=6144 mixer outputs on the small-T tensor cores make the one-request 64K round and the pair round each at least 5% shorter, with both role corpora byte-identical | Fork `b72daad6` (A `3a2fadbd`, B `b72daad6`) on v0.10.0's source. A/B/B/A: one-request rounds **15.62 → 15.49 / 18.68 → 17.17 / 21.40 → 18.54 / 25.95 → 20.91 ms** at 0/32K/64K/120K tokens (−0.8% to −19.4%), pair **23.30 → 21.42 ms** (−8.1%, 424.2 → 454.3 tok/s), each within 0.3 ms of the prediction. DFlash2 and MTP3 corpora 89/89 byte-identical; DFlash2 corpus 288.1 → 293.0 tok/s. 64K trace: attention partial 5,735 µs in 32 launches → 2,959 µs in 16; the pair's mixer outputs 3.43 → 1.41 ms. K=15 drafting: positions 8–15 accepted in 20.5% down to 3.5% of rounds, but 23.4 ms short-context rounds and 53–134 ms behind 32K; corpus 188.5 against 288.1 tok/s. Production since v0.10.0: 338 agent requests, one at a time, 77% of decode seconds below 16K; modelled gain 4.2% of decode time [inference] ([receipt](measurements/2026-10-03-dflash2-round-costs-rtx5090.json)) | kept experimentally; h24 verify only shipped as `344850b3` in `1302d639`; `3a2fadbd` Q5 mixer did not ship; K=15 rejected |
| EXP-093 | RTX 5090 byte-identical Q4 query/key schedules at verify widths | A schedule of the staged Q4 SIMT query/key kernel, or EXP-055's direct rows kernel, keeps every output bit and runs the 8- and 16-column projections faster; they take 1.68 ms of a one-request round at 28–31% of DRAM bandwidth | Microbench on production headers, GDN 4,096 rows and attention 7,168 rows, cold L2: all 18 candidates bitwise-equal to production. The rows kernel spills under its 64-register bound and runs 14–59% slower at 8 columns and 77–126% at 16; fifteen staged schedules land at −3.3% to +10.7%, and the register caps that admit more CTAs spill and run 33–55% slower ([receipt](measurements/2026-10-03-q4-query-key-schedules-rtx5090.json)) | rejected; the tensor-core route needs a powered screen |
| EXP-094 | RTX 5090 Q4 query/key projections on the small-T tensor cores | Sending exactly 8 and 16 columns of the GDN and attention Q4 query/key projections to the Q4 small-T tensor-core kernel makes the one-request round at short context and the pair round each at least 3% shorter than EXP-092's candidate, and the outputs it changes pass EXP-085's powered screen under the unchanged rule | Fork `a59c13d0` on EXP-092's `b72daad6`. 64K trace: projections 1,675 → 823 µs per round (2,670 → 1,091 µs in a pair). A/B/B/A: one-request rounds **15.47 → 14.68 / 17.10 → 16.35 / 18.56 → 17.74 / 20.89 → 20.06 ms** at 0/32K/64K/120K tokens (−4.0% to −5.1%), pair **21.40 → 19.48 ms** (−9.0%, 453.1 → 504.0 tok/s); against shipped v0.10.0 −6.0% to −22.7% at one request and −16.4% in a pair. DFlash2 corpus 33/89 byte-identical to shipped at 307.2 against 288.1 tok/s; MTP3 89/89. Screen, registered in `0082901` before its data: 692 of 1,120 outputs changed; recall −0.23 points (bound −0.55), evidence precision −0.75 (−1.57), unsupported claims +0.30 (+1.79), redaction −0.40 (−1.98), leaks 561 → 583 (ratio bound **1.090** against 1.10), every validity check held; it also passes against EXP-085's BF16 DFlash2 runs. With EXP-092, modelled −8.8% of production decode time [inference] ([receipt](measurements/2026-10-03-q4-query-key-tensor-cores-rtx5090.json)) | kept |
| EXP-095 | RTX 5090 current upstream architecture versus the next fork candidate | Upstream `81c8ce09` at the common DFlash2 K=7/BF16/131,072/chunk-1,024 shape earns re-porting the fork's product features | Unmodified CUDA 13.1.115/sm_120a build; documented v2→v3 upgrade preserves **1,184/1,184 tensor payloads**. Automatic sizing refuses C2 by **561.47 MiB**; the labelled fixed-KV counterfactual completes A/B/B/A. Common 84 server-completed role cases: fork `a59c13d0` **299.71** versus upstream **251.29 tok/s** (+19.27% fork), rounds **15.12 vs 18.39 ms**; 29/84 channel payloads byte-identical (28/72 valid answers). Stored 32K follow-ups: **128/125 vs 307/77 ms**, mixed rather than a uniform cache win. Upstream JSON-schema **5/5 correct**, weighted decode time/token +2.51%; the seven-token tuple has +281.51% relative overhead. C4 with six total StateImages refuses by **1,501.32 MiB** ([receipt](measurements/2026-10-10-upstream-81c8ce09-rtx5090.json)) | rejected — architecture rebase; continue selective backport |

| EXP-096 | Clean v0.6.16 RTX 5090 package and supported-profile rehearsal | Unchanged a59c13d0 can be packaged cleanly, tied to EXP-094's quality evidence and qualified under v0.10.0's fifteen criteria without changing the serving shape | Clean CUDA 13.1.115/sm_120a archive and cutter dry-run; 89/89 serial role signatures match EXP-094. Retrieval 58.917 s versus 58.738 s; 2048 decode 179.79 versus 161.39 tok/s. All 15 unchanged criteria pass, six restart sessions each cached 62404, amended OMP 18.8.7 parallel proof passes. Full ctest 110 pass/7 skip/1 fail; exact NVFP4 baseline eaf passes and 3a fails. BF16 solo/pair: 1/5 identical on both sources. External initial stop preserved; replacement is separate ([receipt](measurements/2026-10-10-v0616-rtx5090-package-local.json)) | qualified except ctest disposition; no publication |
| EXP-098 | Native DFlash2 K=7 gates, 131K fit, and true-cold durability (`sm_86`, `sm_89`) | Removing the W8 static shared-memory link blocker and adding a load-time `sm_86`/`sm_89` DFlash2 fit seam (`Q8_G32_FP16` to `Q4_G64_FP16` draft MLP gate/up requantization plus host-mapped `token_embedding`) lets DFlash2 K=7 clear the 108-role decode gate (`>= 1.08` weighted, every case `>= 0.95`) and fit 131,072 INT8 tokens with true-cold checkpoint durability | On frozen `7a25cd72` controls (65,536 INT8 KV, C1, chunk 1,024, extra slots 0): RTX 3090 at 350 W passes the 108-role gate at **78.94 → 102.60 tok/s (×1.29968, min case 0.97987 on `log-024@0`)** and the 7 supplementals at **74.58 → 95.10 tok/s (×1.27512, min 1.10042)**; RTX 4090 at 450 W reaches **138.37 → 174.85 tok/s (×1.26362)** and **131.16 → 164.12 tok/s (×1.25136, min 1.05885)** on the 7 supplementals, but fails the `0.95` case floor on **`log-024@0` at 0.945889** (`135.03 → 127.73 tok/s`), reproduced in an isolated 4-arm ABBA at **0.9451** (`0.945090`, range `0.945011–0.945169`). On fit source `e456af37b` (rebased to `059e73b6`, parent of `2c6f423b`), RTX 3090 passes the mapped-loading GPU test (`17,852,965,376` B device weights, `1,350,860,800` B host-mapped embedding) and the **131,072-token INT8 fit and true-cold durability proof** at **21,968 MiB** peak VRAM (`376` samples) with **768 MiB** (`805,306,368` B) retained headroom, `0` extra device state slots, and byte-identical 32-token / 114-byte continuation (`07b8db1f`) across a 3,066-token authenticated checkpoint vs a zero-reuse cold process ([receipt](measurements/2026-10-27-native-dflash2-gates-and-fit.json)) | kept — fit seam merged in `2c6f423b`; after `c3911a14` fixed the fork-after-resume checkpoint-owner defect and `26fa28d0` resolved `log-024@0` and first-fork export waits (`EXP-104`, `EXP-105`), native DFlash2 K=7 ships on both RTX 3090 and RTX 4090 in `v0.16.0` (superseding `v0.15.1`) |
| EXP-099 | Native `sm_86` and `sm_89` small-T tensor-core decode | Routing the native MTP3 decode/verify projections through the small-T tensor-core kernels clears the C1 decode bars and stays within the T2 rounding-only role-divergence bound (`<= 8` of 84) or passes the T3 behavioral screen | Candidate `dce5cf06` (rebased `e1c2f66f`) vs `v0.13.1` `7a25cd72`: FP64 op oracles `4/4` pass on both cards. Warm ABBA C1 decode (`4,541` prompt / `1,024` completion, `0` reuse): RTX 3090 **84.42 → 117.98 tok/s (×1.39764)** at 300 W and **90.79 → 126.81 tok/s (×1.39671)** at 350 W (all 4 arms byte-identical); RTX 4090 **151.23 → 163.76 tok/s (×1.08286)** at 450 W. Fails T2 84-role divergence on both cards (**55/84** on RTX 3090, **58/84** on RTX 4090 vs `<= 8`) and the 50-pair T3 early look (`4` new secret-leak cases each). On the 150-pair symmetric Application A retest (shards 1–3), RTX 4090 passes, but RTX 3090 fails added secret fingerprints (`a = 4`, `b = 12`, exact **p = 0.0384 < 0.05**); held T8 DFlash2 + tensor-core plans cancelled ([receipt](measurements/2026-10-27-native-small-t-tensor-core-decode.json)) | rejected — fails T2 on both cards and symmetric T3 on RTX 3090 |
| EXP-100 | Native `sm_86` and `sm_89` attention prefill and `Group64` A8 prefill | Byte-identical `sm_86`/`sm_89` attention specializations and the opt-in `Group64` A8 prefill path (`NINFER_NATIVE_PREFILL_GROUP64_A8`) clear the C1 prefill bars, 130,048-token exact retrieval, held-out perplexity, and the 200-pair symmetric Application B screen | Source `254a586a` (rebased `7ee32e20`, merged into `2c6f423b`). With `Group64` A8 off, attention prefill gains **+4.96%** on RTX 4090 (`1,520.95 → 1,596.39 tok/s`, `85.50 → 81.46 s`) and **+5.40%** on RTX 3090 at 300 W (`622.63 → 656.24 tok/s`, `208.87 → 198.17 s`) on exact 130,048-token retrieval with byte-identical outputs. With `Group64` A8 on vs off: RTX 4090 C1 prefill **2,178.65 → 2,857.95 tok/s (×1.312)** and 130K retrieval **1,595.35 → 1,942.07 tok/s (×1.217, 81.52 → 66.96 s)**; RTX 3090 C1 prefill **919.37 → 1,480.76 tok/s (×1.611)** at 300 W, **978.27 → 1,582.48 tok/s (×1.618)** at 350 W, and 130K retrieval **657.05 → 897.39 tok/s (×1.366, 197.93 → 144.92 s)** at 300 W, all 4/4 retrieval arms exact and byte-identical. Held-out PPL matches to 6 decimals across `sm_89`/`sm_86` (`ΔNLL` `−0.000742` at 1,024, `+0.001453` at 2,048, worst domain `+0.005949`). On the 200-pair symmetric Application B screen at `2c6f423b`, RTX 4090 **fails** leak presence (`41/0/5/154`, `a = 0`, `b = 5`, **p = 1/32 = 0.03125**); RTX 3090 passes (`41/0/4/155`, `a = 0`, `b = 4`, **p = 1/16 = 0.0625**) on 4 of the same 5 `worklog-007`/`worklog-014` prompts ([receipt](measurements/2026-10-27-native-group64-a8-prefill.json)) | attention prefill kept and shipped in `v0.14.0`; `Group64` A8 rejected for `v0.14.0` (compiled off on both lanes) |
| EXP-101 | RTX 3090 `DFlash2 K=7` 1,120-prompt powered quality screen and 80-prompt determinism (`sm_86`) | On the shipping `v0.8.0-qwen38-3090-beta.1` package (`26fa28d0`, package `040d5923`, server `72cd776b`, config `cbe67aae`, `DFlash2 K=7`, `INT8` KV, `350 W`, port `18082`, 50-prompt shards at 1 request), the changed outputs against the sealed `v0.14.0` `MTP3` production arm (`fedce425` / `d08d262b`, 25 sealed holds, state `9a9213cf`) pass `EXP-085`'s preregistered non-inferiority bounds (`recall`, `precision`, `schema`, `tool_selection`, `tool_argument >= -0.02`; `unsupported <= +0.03`; `duplicate <= +0.02`; `redaction >= -0.05`; `secret_leak_ratio <= 1.10`) and 80-prompt fresh-cache determinism | **PASS** ([receipt](../releases/v0.16.0/qualification/rtx3090-windows-native.quality-screen.json), `671659f0`): `1,120` unique prompts (`672` gate + `504` redaction pairs, overlapping on `56` control variants), both arms **80/80** deterministic with `0` missing/error samples, `771/1,120` paired content/reasoning outputs changed, and all **9/9** primary bounds passed (`recall` lower `-0.0073` and `precision` lower `-0.0070` vs `-0.02`; `unsupported` upper `+0.0089` vs `+0.03`; `schema`/`tool_selection`/`tool_argument` lower `0` vs `-0.02`; `duplicate` upper `+0.0059` vs `+0.02`; `redaction` lower `-0.0119` vs `-0.05`; `secret_leak` ratio `1.0294`, upper `1.0673 < 1.10`, counts `545 → 561`, not zero); `v0.8.0-qwen38-3090-beta.1` also passes 84-role depth-0 ABBA speed ([`rtx3090-speed.json`](../releases/v0.16.0/qualification/rtx3090-speed.json) `c904d341`: weighted **×1.2684** / `1.268360×` at **79.37 → 100.67 tok/s**, min **0.9764×** / `0.976442× >= 0.95` on `log-024@0`, no waived case, **84/84** within-engine and **36/84** cross-engine byte-identical), 131,072-token `INT8` `C2` fit/true-cold ([`rtx3090-windows-native.fit.json`](../releases/v0.16.0/qualification/rtx3090-windows-native.fit.json) `662619d7`: `1,110,441,984` B / `1,059 MiB` available >= `805,306,368` B / `768 MiB` floor, `22,584 MiB` peak, `1,742 MiB` min free, two `59,866`-token true-cold sessions restored at `59,840 + 26` tokens with `32/32` token IDs and UTF-8 bytes identical), `83/83` agent-probe parity under `p16-agent-parity/2` (`0` cache-gap deltas, min TTFT bound margin `0.169 s`, `fanout-concurrency 4` `5/5` HTTP 200, calibrated `2 × 59,879`-token test `18/18` HTTP 200 across 3 trials, `0` HTTP 500; summary `8218925c`), `3/3` `v0.7.0-beta.3` upgrade/rollback/repair rehearsals (`631428b5`: `1c` running-lane upgrade `220.32 s`, `2c` forced first-`Start` rollback `206.96 s`, `3c` interrupted-install repair and reinstall `322.25 s`, `370 W` restored), and `15/15` managed qualification phases in [`rtx3090.json`](../releases/v0.16.0/qualification/rtx3090.json) (public sanitized `48c7f635`, raw `038fe713`: `148.43 tok/s` `C1` decode, `974.15 tok/s` prefill, `83.88%` DFlash2 acceptance, `188.99 s` 130,048-token retrieval, `1,647` explicit-save and `1,650` graceful-stop cached tokens across `46.88 s` restart, schema 2 normal and `17,878.578125 MiB` pressure protocol under `agent_protocol.py` `C2` override `317b98ee` in [alphastorm/ninfer#56](https://github.com/alphastorm/ninfer/pull/56), `state_security` `898 ms`, isolated rollback `not_applicable`, `370 W` restored) | kept — shipped in `v0.16.0` (`v0.8.0-qwen38-3090-beta.1`) |
| EXP-102 | RTX 4090 `DFlash2 K=7` 1,120-prompt powered quality screen and 80-prompt determinism (`sm_89`) | On the shipping `v0.8.0-qwen38-4090-beta.1` package (`26fa28d0`, package `06526bdb`, server `c6f59e9e`, config `f00cfac9`, `DFlash2 K=7`, `INT8` KV, `450 W`, port `18082`, 50-prompt shards at 1 request), the changed outputs against the sealed `v0.14.0` `MTP3` production arm (`5caa7780` / `b5cfbf50`, 25 sealed holds, state `cc48a776`) pass `EXP-085`'s preregistered non-inferiority bounds and 80-prompt fresh-cache determinism | **PASS** ([receipt](../releases/v0.16.0/qualification/rtx4090-windows-native.quality-screen.json), `6231dccd`): `1,120` unique prompts (`672` gate + `504` redaction pairs, overlapping on `56` control variants), both arms **80/80** deterministic with `0` missing/error samples, `777/1,120` paired content/reasoning outputs changed, and all **9/9** primary bounds passed (`recall` lower `-0.0082` and `precision` lower `-0.0093` vs `-0.02`; `unsupported` upper `+0.0045` vs `+0.03`; `schema`/`tool_selection`/`tool_argument` lower `0` vs `-0.02`; `duplicate` upper `+0.0046` vs `+0.02`; `redaction` lower `-0.0139` vs `-0.05`; `secret_leak` ratio `1.0525`, upper `1.0985 < 1.10`, counts `533 → 561`, not zero); `v0.8.0-qwen38-4090-beta.1` passes 131,072-token `INT8` `C1` fit/true-cold ([`rtx4090-windows-native.fit.json`](../releases/v0.16.0/qualification/rtx4090-windows-native.fit.json) `44c50008`: `1,056,964,608` B / `1,008 MiB` available >= `671,088,640` B floor, `22,639 MiB` peak, `32/32` tokens identical), `83/83` agent-probe parity, `3/3` `v0.7.0-beta.3` upgrade/rollback/repair rehearsals (`38a3a380`: `1c` running-lane upgrade `211.93 s`, `2c` forced first-`Start` rollback `211.37 s`, `3c` interrupted-install repair and reinstall `309.80 s`, `450 W` restored), `15/15` managed qualification (`254.27 tok/s` `C1` decode, `2,139.14 tok/s` prefill, `83.88%` acceptance, `83.35 s` 130,048-token retrieval in [`rtx4090.json`](../releases/v0.16.0/qualification/rtx4090.json) `69ebf60c`), and 108-role + 7-supplemental ABBA speed vs `v0.14.0` `MTP3` at `450 W` ([`rtx4090-speed.json`](../releases/v0.16.0/qualification/rtx4090-speed.json) `32acdecc`, [`rtx4090-speed-waiver.json`](../releases/v0.16.0/qualification/rtx4090-speed-waiver.json) `92b94c4a`: **×1.2736** on the 108-case role corpus `role108` at **139.87 → 178.13 tok/s**, **×1.2741** across all `115` cases at **138.94 → 177.02 tok/s**, **×1.2778** / min **×1.0804** on the `7` supplementals, **115/115** repeats per engine and **43/115** cross-engine byte-identical; depth-0 case `log-024@0` decoded at **0.934** / **139.41 → 130.19 tok/s**, below the `0.95` every-case floor, and was **waived by the founder with disclosure**) | kept — shipped in `v0.16.0` (`v0.8.0-qwen38-4090-beta.1`) |
| EXP-103 | RTX 4090 DFlash2 floor windows (`K=6`, `K=5`) and `K=7` 131K `INT8` fit (`sm_89`) | Under unchanged-prefix truncation of the recorded `K=7` per-position accepted-draft histogram `[197, 157, 121, 87, 68, 55, 47]` (positions 1..7) on depth-0 case `log-024@0`, config-only `DFlash2` draft windows `K=6` (`>= 5.09%` round-cost reduction required) or `K=5` (`>= 10.44%` required) lift `log-024@0` from `0.945889` (`0.9451` isolated) to the `>= 0.95` floor vs `MTP3`, while `DFlash2 K=7` fits `131,072` `INT8` KV tokens on the `v0.14.0` binary with `>= 640 MiB` (`671,088,640` B) headroom and exact true-cold checkpoint continuation | Isolated 4-arm `ABBA` on `log-024@0` (`4,536` prompt / `1,024` completion tokens, `0` cached, `450 W`, `v0.14.0` `2c6f423b` `sm_89` binary): **`K=6`** decodes at `116.98 / 116.97 tok/s` vs `MTP3` `135.37 / 135.63 tok/s`, candidate/control cross ratios **0.8625–0.8642** (`0.862462–0.864185`, median `0.863323`); **`K=5`** decodes at `117.61 / 117.63 tok/s` vs `MTP3` `135.62 / 135.69 tok/s`, cross ratios **0.8668–0.8673** (`0.866774–0.867336`, median `0.867055`), candidate arms byte-identical in both. Separate **`K=7` 131,072-token `INT8` `C1` fit** (`chunk 1,024`, `0` extra slots, `17,179,869,184` B Host) passes all 7 server launches with **`available_after_startup` = 1,449,132,032 B** (`>= 671,088,640` B RTX 4090 floor), `22,265.0 MiB` peak VRAM, `119,305`-token long prefill, and byte-identical `32`-token / `114`-byte true-cold vs `3,066`-token restored continuation (SHA-256 `07b8db1f`), and the shipping `26fa28d0` package (`06526bdb`, `+2` extra slots, `16,512,696,320` B Host) passes with **`1,056,964,608` B** available (`22,639 MiB` peak, `32/32` tokens identical) | rejected for `K=6` and `K=5`; kept for `DFlash2 K=7` 131K `INT8` fit — shipped in `v0.16.0` |
| EXP-104 | Opt-in `FP32` vocabulary-head logits (`--fp32-head-logits`) and RTX 4090 `DFlash2 K=7` floor on the `P16` engine | Retaining Qwen3.5-architecture (`Qwen3.8-27B`) target vocabulary-head logits in `FP32` (`engine.fp32_head_logits: true`, `+8,442,880` persistent bytes across `248,320` vocab × `8` verify columns × `2` requests plus `248,320 × 1` step logits) avoids `BF16` near-tie rounding during speculative draft acceptance and lifts RTX 4090 `DFlash2 K=7` above the `0.95` floor on `log-024@0` | On `P16` `sm_89` binary `31583e3f` (`70ec6fb6`, `450 W`, `65,536` `INT8` KV, `C1`, `chunk 1,024`), `ninfer_fp32_logits_test` and `ninfer_qwen3_5_head_logits_test` (`83` `FP32` reductions, max rel L2 `0.001722`) pass on both native cards. With **`fp32_head_logits: true`**, `DFlash2 K=7` decodes `log-024@0` at `122.29 / 122.26 tok/s` (`310` rounds, `713` accepted of `2,169` drafted tokens, output SHA-256 `1c50e039`) vs `MTP3` `135.50 / 135.61 tok/s` (`314` speculative rounds + `1` non-speculative fallback step, `708` accepted of `942` drafted, output `0fdce53c`), cross ratios **0.9016–0.9025** (`0.901591–0.902538`, median `0.902065`, FAIL). With **`fp32_head_logits: false`** (the default) on the same `31583e3f` binary, `DFlash2 K=7` decodes at `130.53 / 130.56 tok/s` (`291` rounds, `732` accepted of `2,032` drafted, output `bbe977b9`) vs `MTP3` `135.51 / 135.60 tok/s`, passing with cross ratios **0.9627–0.9635** (`0.962668–0.963492`, median `0.963080`; `v0.14.0` measured `0.945889`), and passes again on the later `P16` integration build (`08257eec`, server `0412e97c`) at **0.96186–0.96294** (`130.60 / 130.50` vs `135.62 / 135.68 tok/s`, median `0.962401`); in the final `26fa28d0` shipping-package (`06526bdb`) 115-case ABBA speed gate at `131,072` `INT8` KV (`+2` extra slots), the 108-case role corpus (`role108`) reached **×1.2736** (`139.87 → 178.13 tok/s`, all `115` cases **×1.2741**) while `log-024@0` measured **0.934** (`139.41 → 130.19 tok/s`, below the `0.95` every-case floor) and was waived by the founder with disclosure | rejected for `--fp32-head-logits` (stays off in all profiles); kept for default `DFlash2 K=7` on RTX 4090 — shipped in `v0.16.0` (`26fa28d0`) |
| EXP-105 | Export-State residency fix (`StateImageStore::prepare_host_export`) | Materializing immutable `StateImage` replicas into the counted Host arena and dropping their Device replicas before acquiring off-worker durable checkpoint export `ReadLease`s (`ReadLease::host_view()`, `8c639fe0` / `80c0af77`) eliminates the multi-second first-fork admission wait on export-pinned Device states where adding two extra device-state slots alone failed | Before the fix, an off-worker durable export pinned all Device `StateImage` replicas through disk serialization: on RTX 3090 `DFlash2 K=7` (`131,072` `INT8` `C1`), adding **two extra device-state slots (`3` total at `31583e3f`, `21,881,405,440` B Host) alone did not help**, with all `3` Device states pinned (`source_wait` `14.86–17.22 s`) and first-fork/continuation server TTFT **15.4–17.8 s** (`15.388–17.771 s` with `2` extra slots, `14.345–17.731 s` with `0` extra slots on `c3911a14`); on RTX 5090 (`DFlash2 K=7`, `BF16`, `C2`, `2` extra / `4` total states), `resume-first` `fork_after_resume` measured **5.03 s TTFT / 4.85 s source wait** (`5.026 s` / `4.850 s` on `c3911a14`, `4.903 s` / `4.738 s` on `31583e3f`). After the fix (`08257eec`, frozen in `26fa28d0`), RTX 3090 `131,072` `INT8` `C1` (`12/12` `warm_arrival` restart-and-fork requests) waits **<= 0.033 s** (`max 0.0327743 s`) with fork server TTFT **0.33–0.76 s** (`0.333701–0.759395 s`; `endpoint_resume_after_fork` `0.550 s`) and passes all `83/83` `C1` and `63/63` `C2` agent-probe requests (`0` cached-token delta across all `51/51` `agent_mix` turns; RTX 4090 `26fa28d0` shipping package `06526bdb` passes `83/83` with max `source_wait` `<= 0.0178 s`); RTX 5090 `fork_after_resume` drops to **0.106 s TTFT** (`0.105796 s`, `source_wait` `0.00461 s`, client wall `5.450 → 0.637 s`) with `11/11` `26fa28d0` release-candidate phases, `84/84` role-corpus output hashes (`347.20 → 346.95 tok/s`, ratio `0.999282`), published-image [`rtx5090.json`](../releases/v0.16.0/qualification/rtx5090.json) (`2200fa44`, `181.78 tok/s` server / `180.25 tok/s` wall decode at `2.71 tokens/round`, `56.62 s` wall / `56.51 s` server `130,048`-token prefill at `2,297.0 tok/s`, `agent_protocol` passed), and N16 agent probes (`warm_arrival` 12/12 with `fork_after_resume` `5.159 → 0.278 s`, `agent_mix` 51/51, `sibling_continue` 5/5, `fanout` 11/11 with `post_restart_branch_0` `5.437 → 0.300 s`, 4-way concurrent fanout 5/5 under rule `p16-agent-parity/2` — a judge correction pairing simultaneously submitted concurrent branches by server admission order — and two-restart `restore` waived at `0.526 vs 0.491 s` and `0.520 vs 0.492 s` with disclosure) | kept — shipped in `v0.16.0` (`26fa28d0`) across all three lanes |
| EXP-106 | Native `C2` (`--max-concurrency 2`) on the RTX 3090 (`INT8` shared `131,072`-token pool) and RTX 4090 `INT8` `C2` fit | Enforcing physical and configured-budget headroom at final readiness (`startup_memory.cpp`) and waiting for in-flight off-worker checkpoint exports in `EngineCore::reserve_resident_units()` (`ea2edc20`) lets native `C2` (`2` extra / `4` total device states, `180,000 ms` pending timeout) serve two concurrent `~60K`-token requests on a shared `131,072`-token `INT8` pool | Before the export-pin liveness fix (`31583e3f`), two concurrent `75,063`-token requests on the RTX 3090 `INT8` `C2` `131,072`-token shared pool hit **HTTP 500 `oldest resident cannot obtain its legal unit`** when a completed sibling's off-worker export pinned `1,008` Device KV pages while the resumed resident (`1,040` pages at `66,560` tokens) needed `16` pages (`34,603,008` B) despite `19,114,072,064` B free Host capacity. After the fix (`08257eec`, frozen in `26fa28d0` RTX 3090 `DFlash2 K=7`, `INT8`, `C2`, shared `131,072` KV, `2` extra slots, `21,881,405,440` B Host, `768 MiB` / `805,306,368` B RTX 3090 headroom, `350 W`), startup (`1,110,441,984` B available, `22,584 MiB` peak) and two-session `59,866`-token true-cold durability pass (`32/32` tokens identical); calibrated two-concurrent `~60K` (`59,879 + 59,879` tokens) runs pass **6/6** requests per trial (**18/18** across `3` trials, `0` HTTP 500s); and `2,048`-token two-request decode vs `C1` (`pending_timeout_ms = 180000`) reaches **1.385×** summed aggregate decode (`57.68 → 79.90 tok/s`, `1.38515×`) and **0.722×** two-request completion wall (`71.01 → 51.26 s`, `0.72195×`; per-request concurrent `40.18 / 42.81` vs `57.58 / 58.26 tok/s`). On the **RTX 4090**, `INT8` `C2` at `131,072` tokens (`chunk 2,048`, `640 MiB` headroom) **does not fit 24 GB**: startup refused before readiness (`Device budget cannot hold the calibrated runtime and requested KV capacity`) | kept for RTX 3090 `INT8` `C2` (`v0.8.0-qwen38-3090-beta.1` shipped in `v0.16.0`); rejected for RTX 4090 `INT8` `C2` at `131,072` tokens (startup refused; needs a smaller KV format) |
| EXP-107 | Native `rk4v4` 4-bit KV cache (`sm_86`, `sm_89`) | Porting head-dim-256 (`D256`) `rk4v4` (`rk4v4_h256_lloyd_g64_s4_g32_v1` from `ashalliants/ninfer-3090` `f5cec0a6`; `17,920` B/token vs `INT8` `33,792` B/token, `47.0%` smaller per-token KV) clears `FP64` op oracles, held-out perplexity (`ΔNLL <= 0.02`), `262,144`-token `C1` / `245,760`–`229,376`-token `C2` fit, and exact true-cold checkpoint durability on 24 GB native lanes | On `08257eec`, all `7/7` numerical/graph/store test executables (`44` `rk4v4` cases, `16` graph cases, `180` `FP64` reductions, max rel L2 `0.007773`) and held-out perplexity (`16,984` tokens, `32` windows at `1,024/512`: mean NLL `1.643463 → 1.646910`, **$\Delta\text{NLL} = 0.00345 \le 0.02$**, PPL `5.173052 → 5.190916`, max domain `+0.006273 <= 0.05`) pass on both `sm_86` and `sm_89`. On RTX 3090, `rk4v4` **fits at `262,144`-token `C1`** (`1,097,859,072` B available above the `805,306,368` B / `768 MiB` RTX 3090 floor; exact `130,048`- and `250,062`-token diagnostic retrieval in `197.86` and `503.57 s`), `245,760`-token `C2` (`1,135,607,808` B available), and `229,376`-token `C2` (`1,429,209,088` B available), while RTX 4090 (`chunk 2,048`, `640 MiB` floor) refuses `262,144`-token `C1` and `245,760`-token `C2` at startup and fits `229,376`-token `C2` (`952,107,008` B available). **The exact true-cold restore oracle fails on RTX 3090**: at `262,144`-token `C1` (`3,093` prompt, `3,066` cached) continuation diverges at **token 32** (cold token ID `48117` vs restored `3635` despite byte-exact `55,050,240`-byte CPU page-layout inversion, SHA-256 `53e8f8bc`), and at `245,760`- and `229,376`-token `C2` (`59,866` prompt, `59,840` cached) the first concurrent session diverges at **tokens 16–32** (second session `32/32` equal); cause unproven between GPU restore transport and width-dependent `rk4v4` prefill vs decode+restore numerics | open — deferred to a follow-up release; `--kv-dtype rk4v4` stays off in shipped profiles |
| EXP-108 | `Qwen3.8-Flash-Next` (`Qwen4Exp` MoE + per-layer-embedding `PLE`) on upstream NInfer `a754fcf3` vs Strata `v0.2.10` (`sm_120`, research only, not a product lane) | Under `omp-strata`'s preregistered rule-30 screen (`M1`–`M6`, `G24` guards) on `rtxpro6000-win-a` (RTX PRO 6000 Blackwell 96 GB, `sm_120`, WSL2; maintainer-private raw harness logs), upstream NInfer `a754fcf3` (binary SHA-256 `bcfba1b0...`, `neroued/Qwen3.8-Flash-Next-NInfer` rev `001057dd`, 4 files, `108,445,200,388` B) clears the `W1` entry smoke and `M1`–`M6` resident screen against stock Strata `v0.2.10` (engine `0.1.56`) + OMP `18.16.0` `IQ3_S` `262K` current RTX PRO 6000 profile, and starts under an RTX 5090-class `NINFER_VRAM_BUDGET_MIB=31000` device budget with CPU expert offload (`HostExperts`) | **Formal verdict: NInfer resident (`N`) not entered** ([receipt](measurements/2026-11-05-p19-flash-next-and-starvation.json)): one `W1` structured tool-call smoke emitted the tool call inside reasoning and ran to the length limit (a later `10×` smoke-frequency probe passed `10/10` on both engines; the formal verdict stands). `W1` cold long-context TTFT across two runs: `64K` **4.99 / 4.87 s** vs Strata **7.02 / 7.31 s**; `200K` **15.79 / 16.47 s** vs **22.59 / 24.05 s**; short `C1` decode **252–264** vs **311–323 tok/s**. **Exploratory scorecard (interleaved Strata `A1` / NInfer / Strata `A2`, non-gating):** `M1` short `C4` (concurrency-4) aggregate **264.2 / 441.7 / 270.8 tok/s (1.63×)**; `M2` `64K` `C4` wall **34.36 / 23.82 / 34.39 s (1.44×)**; `M3` `200K` cold tool-turn TTFT **22.32 / 25.37 / 22.43 s (13.7% slower)**; `M4` `200K` warm follow-up **2.64 / 2.22 / 3.04 s** (unstable reference); `M5` interference stall **3.83 / 0.67 / 3.84 s (5.7× lower)**; `M6` `G24` verified passes/hour **115.6 / 95.0 / 118.9 (20.1% lower**; `G24` NInfer `15/18` in `568.3 s` vs Strata `15/18` in `467.0 s` and `16/18` in `484.4 s`). **RTX 5090-class CPU expert offload (`NINFER_VRAM_BUDGET_MIB=31000` on `rtxpro6000-win-a`, forcing `HostExperts`):** every configuration refused at startup with `Device budget cannot hold the calibrated runtime and requested Context capacity` (including zero Host context and a minimal `C1` / `4K` / `BF16` / no-MTP / no-graphs diagnostic, with `~155 GiB` host memory available; a `40,960 MiB` budget also refused); no offload speed was measured, and upstream needs `~63.3 GiB` pinned host RAM for routed experts vs `47 GiB` on `rtx5090-win-a` | rejected for product lanes (formal verdict `not entered`; 31,000 and 40,960 MiB `HostExperts` budgets refused at startup) — Strata stays the Flash-Next engine on the RTX PRO 6000 host (`rtxpro6000-win-a`); revisit if upstream's offload planner starts on a 32 GB-class budget |
| EXP-109 | Upstream [`#434`](https://github.com/Neroued/ninfer/issues/434) request starvation under context pressure and [`#378`](https://github.com/Neroued/ninfer/issues/378) Host placement on shipped engine source `a87de361` | Under the preregistered red condition (an admitted request making no token progress `>= 120 s` while concurrent requests progress), the shipped `v0.16.2` engine (fork source `a87de361` on upstream base `64d10fbf`) exhibits upstream `#434` request starvation on the `C2` lanes or `#378` active-conversation Host eviction, and targeted cherry-picks in [`alphastorm/ninfer#93`](https://github.com/alphastorm/ninfer/pull/93) (`e6ac7b70`) eliminate admitted-request starvation under the strict no-failure criterion without a full re-port to `a754fcf3` | **Upstream `#434` starvation REPRODUCED on both shipped `C2` lanes and on the RTX PRO 6000 proxy** ([receipt](measurements/2026-11-05-p19-flash-next-and-starvation.json)): on the **native RTX 3090 `C2` lane** (`rtx3090-win-a`, installed `v0.8.0-qwen38-3090-beta.2`, source `a87de361`), a `79,989`-token request paused **440.94 s** after `62,464` input tokens with zero output or restores while the prime (first admitted long) request generated `16,150` tokens and `45` fresh requests completed; on the **RTX 5090 production image** (`rtx5090-win-a`, image `a0cbb8a5`, source `a87de361`, production serving args except a `2 GiB` scratch checkpoint store), an admitted `79,989`-token request produced its first token **~398.8 s** after admission while the other long request streamed and `48` fresh `247`-token requests completed every `~10 s`, running only after the other request finished. **Upstream `#378` Host placement:** not reproduced on the native RTX 3090 lane (both Host-fill arms, fill `4` and fill `5`, preserved the conversation, at up to `99.995%` peak Host occupancy; the oldest conversation was evicted instead); **INCONCLUSIVE** on the RTX 5090 (`rtx5090-win-a`, production image `a0cbb8a5`: the client's adaptive fill did not converge within its `3,600 s` budget across `12` conversations of `~120K` tokens with fill steps lengthening to `~10 min`, so no preservation probe ran); and **not reproduced on either build** on the RTX PRO 6000 proxy (`rtxpro6000-win-a`, `sm_120`, `NINFER_VRAM_BUDGET_MIB=31000`, `C2` / `BF16` / `131,072`-token KV, `20.4 GiB` Host, preregistered fixed fill `5`: peak Host occupancy **99.842%** baseline / **99.861%** candidate, and the preserved conversation kept **119,985 / 119,992** and **119,981 / 119,988** cached tokens). **Fix candidate (`alphastorm/ninfer#93`, head `e6ac7b70`, `8/8` CI jobs green):** ports the `a754fcf3` failure-diagnostics subset, the `452c3f5f` recovery-loss formula, `#378` Host placement (re-expressed from Saylek-ai `fix/378-host-placement`), and the `#434` scheduler pressure owner + bounded service rotation + deferred fresh admission (plus a fix and regression test for a refusal-retry liveness defect on a queued fresh-admission notification found in the first scheduler port). On the `rtxpro6000-win-a` RTX PRO 6000 proxy (same geometry, Linux `sm_120a` builds of `a87de361` and `e6ac7b70`, clean build provenance), baseline `a87de361` was **RED** (an admitted request paused **362.3 s** without progress while `38` fresh requests completed); candidate `e6ac7b70` eliminated admitted-request starvation (maximum pause **1.28 s**, both long requests completed) and passed **no-pressure parity** (`3/3` greedy prompts, output fields and finish reasons byte-identical), **but** two fresh requests were refused with HTTP `503` queue timeouts (`180 s` pending timeout) while admission was deferred under sustained pressure, so the strict no-failure criterion is **not** met (the fix trades indefinite silent stalls for bounded, visible `503`s on new requests during long pressure) | reproduced on shipped `a87de361`; [`alphastorm/ninfer#93`](https://github.com/alphastorm/ninfer/pull/93) (`e6ac7b70`) eliminated admitted-request starvation (`362.3 s → 1.28 s` max pause) with HTTP `503` queue timeouts that `EXP-112` (`E1` `#97`, `0/51` `503` at `375bb848` and `0/54` at `F2` `bdc665a3`, max fully-paused `3.0 s` / `2.59 s`) subsequently resolved; `#93` merged in `b871996a` and shipped in `F3` `e0971faf` (`v0.7.0-qwen38-5090-beta.6`, `v0.17.0`) |
| EXP-110 | RTX 5090 real-traffic profile, cached/warm TTFT tail attribution, and [`#58`](https://github.com/alphastorm/ninfer/issues/58) low-acceptance `DFlash2` fallback trigger (`rtx5090-win-a`) | Across the retained `rtx5090-win-a` production request logs (`9,430` completed requests, `2026-08-25` to `2026-11-04`), low-acceptance `DFlash2` decode (`< 3` tokens/round) recovers `>= 3%` of all decode seconds if switched to `MTP3` (`14.03 ms` vs `16.24 ms`/round, `#58`), while phase shares, request overlap, and warm-TTFT tail buckets identify the highest-leverage runtime bottleneck | Snapshot `20261110T063534Z` (`253` files, `77,842,633` B, archive SHA-256 `bbd8bb7b...`; `34,152` events, `9,430` completions across `543` server instances; [receipt](measurements/2026-11-10-p20-overnight.json)). **`DFlash2 v0100p+` filtered** (`v0.10.0+` production logs with `DFlash2`, excluding diagnostic filenames, deterministic `<= 256`-token or explicit-digest probes, the historical greedy `8,192–10,240`-token no-tool corpus signature, and acceptance-window overlaps; `7,318` of `7,323` requests, `55,988.14 s` wall): decode **69.42%**, prefill **28.58%**, queue **1.43%**; peer overlap **1.31%** (`96` requests) with **1.612×** matched decode-overlap and **1.995×** peer pre-first-token slowdown p50; cached (`n=7,177`) TTFT p50/p90/p99 **0.750 / 2.583 / 50.392 s**, strict-warm (`<= 1,024` computed tokens, `n=3,440`) **0.508 / 0.706 / 1.923 s**, cold (`n=141`) **3.457 / 10.414 / 50.606 s**. **Recent `v0.13–v0.16.2` filtered (`176` of `180` requests, `299.64 s` wall):** decode **31.89%** (`31.9%`), prefill **50.21%** (`50.2%`), queue **8.16%** (`8.2%`), prepare **3.65%**; peer overlap **25.57%** (`45/176`, `25.6%`) with **1.560×** (`1.56×`, `8` matched) elapsed decode slowdown beside a peer's pre-first-token window (**1.340×** on decode overlap, `14` matched; raw `307.37 tok/s` solo vs `171.75` / `204.62 tok/s`); **0** global-decode stalls `>= 60 s` (one historical `15.00 s` intersection on `2026-10-04`), **0** preemptions/restores/replays across all `180` recent completions; cached (`= strict-warm`, `n=112`) TTFT p50/p90/p99 **0.265 / 0.357 / 1.466 s**, cold (`n=64`) **3.451 / 4.821 / 5.939 s**. **Warm-TTFT tail:** `DFlash2` cached top decile (`n=718`) is **94.42%** prefill (`673/718` compute `> 4,096` new tokens); strict-warm top `1%` (`n=35`) is **79.33%** queue; recent top-decile excess is **84.0%** driven by `4` first-after-`server_start` Host-KV restores (`0.874–1.130 s` unlabelled added prepare vs `117.3–119.9 ms` for `632–652 MiB` KV + `186.8 MiB` state H2D; excluding them drops recent p99 from `1.466 s` to **0.376 s**). **`#58` low-acceptance trigger:** low-acceptance decode is **3.45%** (`1,340.01 / 38,864.83 s`, `324/7,317` requests, pooled `3.875` tok/round) in `DFlash2 v0100p+` and **6.26%** (`5.98 / 95.57 s`, `11/176` requests, pooled `4.124` tok/round) recently; modelled round-cost recovery is **0.469%–0.851%** (`0.017%–0.169%` first-three-position proxy, `1.307%–2.525%` perfect 4-tok/round `MTP3`), all `< 3%` | `#58` low-acceptance fallback dropped (`<= 0.851% < 3%` bar); `C2` prefill/decode interference ranked #1 recent real-traffic runtime lever |
| EXP-111 | Copyable share of real coding-agent output and own-prefix n-gram copy-drafting revival (copy-drafting spike `S1` `a05d6e77` / `60a95b0e`, `E5` [`alphastorm/ninfer#94`](https://github.com/alphastorm/ninfer/pull/94) `d117bc17` declined and closed) | Replaying the `S1` copy-drafting spike's exact 4/8/16-token hashed suffix proposer (`--ngram-draft-tokens 0\|15`, min match `12`, max copy `15` when `> K=7`, plus an adaptive `12 → 24 → 36` backoff variant) over a 30-day coding-agent session sample reaches the `>= 15%` (`×1.15`) pooled session decode speedup bar required to justify a powered quality screen and release qualification | 30-day census ending `2026-11-10T06:07:32.162009Z` (`68,351` assistant records, `68,221` nonempty across `876` sessions; **0** local-Qwen/ninfer/Strata turns on the workstation, so `3,000` sampled cloud-model turns / `649` sessions / **1,764,539** `Qwen3.8-27B`-tokenized native-format output tokens serve as structural proxies; tokenizer rev `37561816`, `tokenizer.json` SHA-256 `0997f410...`; [receipt](measurements/2026-11-10-p20-overnight.json)). **Accepted copy share:** **20.5413%** (`20.5%`, `362,459` tokens across `45,495` copy rounds, `13.23%` zero-acceptance, `14.6983%` in runs `>= 12`, `19.38%` payload-only excluding `11.87%` formatting) under fixed min-12, and **13.2531%** (`13.3%`, `233,857` tokens across `25,626` rounds, `10.14%` zero-acceptance, `12.68%` payload-only) with adaptive backoff. **By output kind (fixed / backoff):** edit/hashline/patch **39.76% / 31.52%** (`115,315 / 290,045`), formatting **29.20% / 17.49%**, other tool args **23.87% / 11.24%**, bash/eval **23.37% / 15.51%**, write **17.00% / 10.24%**, visible reasoning **3.61% / 1.70%** (`16,823 / 465,861`), plain text **2.87% / 2.06%**. **Pooled decode ratio** (at `4.631` neural tok/round from EXP-078 and copy round cost `C = 1.41 → 1.22` neural rounds): **1.06664–1.09314×** (`+6.7–9.3%`) fixed and **1.05484–1.06928×** (`+5.5–6.9%`) backoff (combined **×1.055–1.093**; **1.02958–1.05425×** / **1.01476–1.02812×** with `S1`'s `-4.205%` short-Read lookup-toll sensitivity; median session ratio `1.03952×` / `1.02016×` at `C = 1.41`; `87/649` and `59/649` sessions `> +15%`). On the `S1` RTX 5090 build (`60a95b0e`), synthetic edits gained `+53.434%`, short Reads lost `-4.205%`, and output identity was `15/23` | revival declined and not shipped in `v0.17.0` (`×1.055–1.093 < 1.15` bar; output-changing on copy rounds; `E5` PR [`alphastorm/ninfer#94`](https://github.com/alphastorm/ninfer/pull/94) `d117bc17` closed) |
| EXP-112 | Upstream [`#434`](https://github.com/Neroued/ninfer/issues/434) context-pressure starvation on `rtxpro6000-win-a` and `rtx5090-win-a`: production controls vs E1 ([`alphastorm/ninfer#97`](https://github.com/alphastorm/ninfer/pull/97)) | Adopting upstream `77c2e5e2` / `Neroued/ninfer#443` resume-without-replay semantics plus a bounded fresh-admission rotation window in [`alphastorm/ninfer#97`](https://github.com/alphastorm/ninfer/pull/97) (slice `E1`, integrated into `F3` `e0971faf`) keeps admitted-request pauses `< 5 s`, completes `2/2` long requests within `600 s`, eliminates the fresh-request HTTP `503` queue timeouts seen on `#93` (`e6ac7b70`), and preserves `3/3` byte-identical no-pressure greedy parity on both `DFlash2` and `MTP3` | **Pre-cut slice measurements on fork PR [`alphastorm/ninfer#97`](https://github.com/alphastorm/ninfer/pull/97) ([receipt](measurements/2026-11-10-p20-overnight.json)).** **RTX PRO 6000 proxy (`rtxpro6000-win-a`, `31,000 MiB` budget, `C2` `BF16` `131,072` KV, `24,576 MiB` checkpoint store, client `46dc58d4`):** same-session control `e6ac7b70` (`8235ada4`) had **1.618474534 s** max admitted pause (`1.327120366 s` fully paused), **6** HTTP `503` timeouts, and **1/2** long completions (`40,000` `output_limit` vs `27,288` `cancelled`); candidate `df7aeb52` (`c46c67d1`) achieved **2.266069104 s** (`2.27 s < 5 s`) max admitted pause (`2.086055400 s` fully paused), **0** HTTP `503`, **2/2** normal long completions (`40,000` `output_limit` and `36,190` `stop_token`), **3/3** byte-identical greedy parity on both `DFlash2` and `MTP3`, `512`-output real-preemption suite pass (`none` `56.326 s`, `MTP` `33.091 s`, `DFlash2` `35.466 s`, ELF `dd9dbbe6`), and all CI green (`Linux 45/45`, `MSVC 24/24`, `sm_86`/`sm_89`, `RDC`). **RTX 5090 real card (`rtx5090-win-a`, `146,368` auto `BF16` KV, `chunk 1,024`, `2,048 MiB` scratch quota):** production control `a87de361` (`cc99a460`, image `a0cbb8a5`) paused **367.9977688699946 s** (`368.0 s`; max scheduler pause `368.62261531799595 s`) and starved the second long request (**1/2** complete: `40,000` `output_limit` vs `19,392` `cancelled`; `0/54` fresh `503`, fresh TTFT p50/p95 **0.292190 / 0.535915 s**); E1 candidate `375bb848` (`7f988154`, built in pinned release builder `e7f34ca2`) passed with **2.9986773779965006 s** (`3.0 s`) max fully-paused interval (**3.2083587239976623 s** pause→recovery across `234` pauses), **2/2** `40,000`-token long completions inside `600 s` (`337.50` and `112.69 tok/s`), **0/51** fresh HTTP `503` (`50` completed before horizon), and fresh TTFT p50/p95 **0.400092 / 3.392509 s** (`0.40 / 3.39 s`) | **PASS** on both `rtxpro6000-win-a` (`df7aeb52`) and `rtx5090-win-a` (`375bb848`) — shipped in RTX 5090 `v0.7.0-qwen38-5090-beta.6` (`F3` `e0971faf`, `omp-ninfer` `v0.17.0`, published 2026-11-10) via [`alphastorm/ninfer#97`](https://github.com/alphastorm/ninfer/pull/97) and [`#101`](https://github.com/alphastorm/ninfer/pull/101) |
| EXP-113 | Cold `130K` prefill/decode interference (`EXP-077`) on `rtxpro6000-win-a` and `rtx5090-win-a` | Under `EXP-077`'s two-request `C2` interference scenarios (`130,084` cold prompt tokens, `0` cached, long fixture `8dcece52`, `chunk 1,024`, `DFlash2 K=7`), co-resident decode stays `>= 100 tok/s` and a short decode request arriving during an admitted long prefill achieves `TTFT <= 5 s` without prefill pacing | **Design trigger (`< 100 tok/s` co-resident decode OR `> 5 s` arrival TTFT) is TRUE on both hosts** ([receipt](measurements/2026-11-10-p20-overnight.json)). **RTX PRO 6000 proxy (`rtxpro6000-win-a`, `e6ac7b70` `8235ada4`, config `f8d99fb9`, `4,096 MiB` scratch quota, `3` fresh-server cold repeats/scenario):** prefill-during-decode median strict-overlap co-resident decode **6.375002 tok/s** (`6.375 tok/s`; full-A **20.387571 tok/s**), inter-output-event gap p50/p99 **350.569854 / 469.988615 ms** (`350.6 / 470.0 ms`), `130K` long TTFT / wall **46.349826 / 46.491205 s** (`44.226679 s` server prefill); decode-during-prefill (gated at `running/prefilling + 1.000 s`) median arrival TTFT **0.803794 s** (`0.804 s`, queue wait `0.210–0.222 s`, `3/3` admitted before long first token), long TTFT / wall **45.514373 / 45.637334 s**. **RTX 5090 real card (`rtx5090-win-a`, `146,368` auto `BF16` KV, `2,048 MiB` scratch quota, reducer `5da11604`):** production `a87de361` (`cc99a460`, `6/6` valid cold, arrival submitted at admission `+ ~5.15 s` offsets `5.148507 / 5.148274 / 5.149912 s`) measured **5.109089 tok/s** (`5.11 tok/s`) co-resident decode (full-A **16.116528 tok/s**), gap p50/p99 **430.325104 / 618.715558 ms** (`430 / 619 ms`), arrival-during-prefill TTFT **23.071937 s** (`23.07 s`), and long wall **59.960177 / 59.473603 s** (`~60 s`); E1 candidate `375bb848` (`7f988154`, `5/6` valid cold — `2/3` valid arrival samples `20.341783` and `21.657426 s` plus `1` invalid late sample `52.519997 s` retained without retry) measured **5.127272 tok/s** co-resident decode (full-A **16.186026 tok/s**), gap p50/p99 **405.190917 / 618.392636 ms**, qualified arrival TTFT **20.999604 s** (`21.00 s`), and long wall **59.891799 / 59.165644 s** | interference trigger **TRUE** (`5.11–6.38 tok/s` co-resident decode); `EXP-118` subsequently proved the `23.07 s` RTX 5090 arrival wait persists at the shipped `24,576 MiB` quota (`23.073498 s`, `19.49–23.72 s` retained-preferred-source wait), and `EXP-119` measured the opt-in pacing curve in [`alphastorm/ninfer#95`](https://github.com/alphastorm/ninfer/pull/95) |
| EXP-114 | `C2` pair-round `K=6144`, `T=16` Q5 mixer-output kernel attribution on `rtxpro6000-win-a`, closing `EXP-092`'s open half | On the `64d10fbf`-based fork (`e6ac7b70`), the `64` `K=6144`, aggregate-`T=16` `LinearAdd` mixer-output projections in a two-request `DFlash2 K=7` round still fall back to the historical `~80`-CTA prompt GEMM (`53.6 µs/call`, `3.43 ms/round`), justifying porting `EXP-092`'s unmerged `3a2fadbd` commit (`22.1 µs/call`, `1.41 ms/round` target) | Nsight Systems `2026.3.2.476` capture on `rtxpro6000-win-a` (`e6ac7b70` `8235ada4`, config `f8d99fb9`, `sm_120a`, CUDA `13.4.92`; [receipt](measurements/2026-11-10-p20-overnight.json)): a complete `C2` NVTX `decode` range (membership payload `2`, CUDA graph `71`) launches **743** kernels across `47` specializations (**17.838570 ms** summed kernel time, **17.835578 ms** GPU span, **18.353995 ms** host range). All **64** `K=6144`, `T=16` residual-add mixer calls already dispatch to the small-T tensor-core sliced-K kernel `q5_a16_sliced_k_mma_kernel<Q5A16SlicedKMmaSchedule<16,16,8,2,...,6144,16,...>,...,LinearResidualAddEpilogue,...>` (`320×1×1` CTAs, `256×1×1` threads) at mean **19.767594 µs/call** (median **19.776 µs**, range `19.264–20.223 µs`), totaling **1.265126 ms/round** (`1.27 ms` vs `EXP-092`'s `1.41 ms` target); zero `80`-CTA prompt-GEMM mixer calls occur | closed — already on small-T tensor-core sliced-K (`19.77 µs/call`, `1.27 ms/round`); porting `3a2fadbd` is unnecessary |
| EXP-115 | Native configuration probes on shipped `v0.16.2` (`a87de361`): RTX 3090 `--gpu-keep-warm-ms 60000` (`sm_86`) and RTX 4090 `--prefill-chunk 2048` (`sm_89`) | On installed `v0.8.0-beta.2` (`a87de361`, model `81f924d4`), config-only `--gpu-keep-warm-ms 60000` on `rtx3090-win-a` (`15a4db46`, `350 W` cap) holds `P2` across `12/30/58 s` idle and keeps post-idle TTFT `<= 1.10×` back-to-back controls (addressing the waived `0.4975294 s` vs `0.2144353 s` sibling `base` position), and config-only `--prefill-chunk 2048` on `rtx4090-win-a` (`ffee91bf`, `450 W`) clears `>= 640 MiB` startup headroom, `>= 1.04×` prefill (`benchmark_c1` and `retrieval130048`), `>= 0.98×` decode, and `84/84` byte identity | **Both rejected** ([receipt](measurements/2026-11-10-p20-overnight.json)). **RTX 3090 keep-warm (`rtx3090-win-a`, ABBA fresh servers, `6` post-idle observations/arm/delay on `163–226`-token cold prompts):** the compiled `sm_86` `3.5/10 ms` spin pattern falls to **`P5` at `12 s`** (`P2` occupancy `7.4%`, held `34.7 → 72.6 W`, `+37.9 W`) and **`P8` at `30 s` and `58 s`** (`P2` occupancy `1.8%` and `1.1%`, held `10.0 → 29.8 W` / `+19.8 W` and `9.8 → 25.2 W` / `+15.4 W`); post-idle TTFT / back-to-back is **0.5456 / 0.4173 s** at `12 s` (paired ratio **1.364×** vs A `0.6716 / 0.4181 s`), **0.5667 / 0.4199 s** at `30 s` (**1.362×** vs A `0.6617 / 0.4219 s`), and **0.6501 / 0.4212 s** at `58 s` (**1.521×** vs A `0.6435 / 0.4208 s`), failing `<= 1.10×` at every delay (`27/27` outputs identical, peak `328.02 W <= 350 W`). **RTX 4090 `chunk 2048` vs shipped `1024` (`rtx4090-win-a`, `131,072` `INT8` `C1`, `+2` extra slots, ABBA):** fits with **848.00 MiB** available (`1,008.00 MiB` at `1,024`, `>= 640 MiB` pass), but `benchmark_c1` prefill is **2,122.99 → 2,173.11 tok/s (`×1.0236 < 1.04`)**, `retrieval130048` prefill is **1,562.57 → 1,585.82 tok/s (`×1.0149 < 1.04`)**, `benchmark_c1` decode regresses **254.40 → 224.33 tok/s (`×0.8818 < 0.98`)** (`role84` decode `174.67 → 174.85 tok/s`, `×1.0011`), and cross-arm `role84` byte identity is **44/84** (`84/84` within each arm) | both **rejected (`DO NOT PROMOTE`)** — RTX 3090 needs a different `sm_86` spin pattern build; RTX 4090 `chunk 2048` gains `<= 2.36%` prefill while changing `40/84` `role84` outputs (would require a powered quality screen) |
| EXP-116 | Native `rk4v4` ([`#60`](https://github.com/alphastorm/ninfer/issues/60)) true-cold restore geometry control on `rtx3090-win-a` (`sm_86`) | Replaying the restored arm's exact `3,066`-token capture split and speculative suffix prefill chunk geometry (`18, 2, 3, 4` tokens at bases `3066, 3084, 3086, 3089`) in a zero-reuse cold `rk4v4` run on `rtx3090-win-a` isolates whether `EXP-107`'s token-32 mismatch (`3635` restored vs `48117` ordinary `chunk 1,024` cold) is a checkpoint-transport / `rk4v4` kernel defect or an oracle prefill-geometry difference | On `rtx3090-win-a` (diagnostic source `f6ed4381`, `3,093` prompt tokens; [receipt](measurements/2026-11-10-p20-overnight.json)): ordinary `chunk 1,024` cold (`3,093` computed, `0` cached) vs restored (`3,066` cached + `27` computed) reproduced the `EXP-107` divergence at **31/32** tokens (token 32: **48117** cold vs **3635** restored), whereas **geometry-matched cold** (`3,093` computed, `0` cached, split at `3,066` plus suffix chunks `18, 2, 3, 4` at bases `3066, 3084, 3086, 3089`) matched the restored run **32/32** tokens (both emit token 32 = **3635**). Seed-to-restored canonical KV and continuation-selected `StateImage` transport are **byte-exact**, all three `3,093`-token prompt ledger hashes match, and the `int8-group64` (`INT8`) control is **32/32 three-way identical** across restored, ordinary cold, and matched-geometry cold (token 32 = `48117`) | reclassified as **oracle prefill geometry** (`oracle_geometry_explains_token_mismatch`), not a restore transport or `rk4v4` kernel defect; adopting a geometry-matched true-cold durability oracle (plus a non-instrumented RTX 3090 hold and RTX 4090 qualification) is deferred to a founder decision |
| EXP-117 | Host-side TTFT probes: NFC boundary normalization ([`alphastorm/ninfer#96`](https://github.com/alphastorm/ninfer/pull/96)), Jinja `.strip()` edge decode, and small-T CUDA module preload | Porting community (`iamwavecut/ninfer-all`) host-side TTFT commits — NFC boundary-segmented normalization (`4f8d324a`, tree `2523523c`), Jinja `.strip()` edge-only UTF-8 decode (`21d8b947`, tree `9811c30e`), and startup preload of small-T attention modules (`79d657e0`, tree `f3e8420e`) — reduces host/first-use latency on base `e6ac7b70` while preserving exact UTF-8 validation and byte-identical prompt rendering/tokenization | **Pre-cut slice measurements on fork PR [`alphastorm/ninfer#96`](https://github.com/alphastorm/ninfer/pull/96) (`6f1ae8d2` on `e6ac7b70`; [receipt](measurements/2026-11-10-p20-overnight.json)).** **(1) NFC boundary normalization (`src/text/unicode.cpp`, ported):** on Apple M5 Max (`arm64`, AppleClang 21 `-O3 -DNDEBUG`, `31` timed samples/arm, ABBA), a `507,749`-byte technical document (`39,469` non-ASCII bytes) normalizes in **0.465583 ms** (`[0.456584..0.470833]`, `0.47 ms`) vs **5.147875 ms** (`[4.865750..5.370875]`, `5.15 ms`) on base (**-90.96%**, **11.06×** faster; local combining sequence maps `3` bytes vs `500,003` on base), and a `507,749`-byte ASCII control runs in **0.056375 ms** vs **0.065500 ms** (**-13.93%** with `std::find_if` ASCII prefix scan; `500,000`-char conversation render within `1.71%` at `1.182208` vs `1.162375 ms`, `+1.71%`). Agrees with whole-text `utf8proc_map(STABLE\|COMPOSE)` on **100,000** random texts, passes `test_frontend.cpp` and `9/9` Python template tests, and matches byte-for-byte across all **65/65** serialized render results (`56` successful prompts + `9` expected errors, SHA-256 `a9e3f2d2...`) and all **564,922/564,922** token IDs (SHA-256 `e6ff96c6...`). **(2) Jinja `.strip()` (`21d8b947`, skipped):** base `e6ac7b70` already removed the character-vector allocation (`500,004` decodes for `500,002` chars) and validates interior UTF-8 by contract. **(3) Small-T module preload (`79d657e0`, skipped as `N/A`):** base compiles one shared `INT8` `launch.cu`; Nsight Systems tracing from startup (`CUDA_MODULE_LOADING=LAZY`, `164,093` CUDA API events across `33` requests / `31` prefix hits spanning widths `11..25` on `rtxpro6000-win-a`, binary `8235ada4`) measured `<= 0.054462 ms` single and **`<= 0.668558 ms`** (`<= 0.67 ms`) cumulative per-request module/lookup API time (`<= 0.226192 ms` attention launch API), below the `20 ms` gate | NFC boundary normalization (`11.06×`, `5.15 → 0.47 ms`, `65/65` serialized results and `564,922` token IDs identical) shipped in RTX 5090 `v0.7.0-qwen38-5090-beta.6` (`F3` `e0971faf`, `omp-ninfer` `v0.17.0`, published 2026-11-10) via [`alphastorm/ninfer#96`](https://github.com/alphastorm/ninfer/pull/96); Jinja `.strip()` and small-T module preload skipped |
| EXP-118 | RTX 5090 shipped-quota (`24,576 MiB`) `EXP-077` arrival-wait control (`rtx5090-win-a`) and retained-preferred-source-wait root cause with [`alphastorm/ninfer#100`](https://github.com/alphastorm/ninfer/pull/100) (`rtxpro6000-win-a`) | Raising `--session-checkpoint-quota-mib` from `2,048` to the shipped `24,576 MiB` on `rtx5090-win-a` (`a87de361` `cc99a460`) eliminates the `23.07 s` `EXP-077` arrival wait; if the wait is instead a retained-preferred-source wait inside `EngineCore`, bounding source-wait deferral in stacked [`alphastorm/ninfer#100`](https://github.com/alphastorm/ninfer/pull/100) (`7f2c71fd` / `1c5` on `df7aeb52`) removes the `~45 s` warm-history proxy reproduction | **Arrival wait persists at `24,576 MiB`; root cause is retained-preferred-source wait; first candidate fix `#100` did NOT remove the `~45 s` GPU proxy reproduction** ([receipt](measurements/2026-11-10-p20-overnight.json)). **RTX 5090 `24,576 MiB` control (`rtx5090-win-a`, `production-exp077-q24-01`, `a87de361` `cc99a460`, `ext4`, `6/6` valid cold, `3/3` valid arrivals, min free `C:` `313.54 GiB`):** median arrival-during-prefill TTFT is **23.073498 s** (`23.07 s` vs `23.071937 s` at `2,048 MiB`, delta **+0.001561 s**), co-resident decode **5.254542 tok/s** (full-A **16.166105 tok/s**), gap p50/p99 **430.661417 / 618.893977 ms**, prefill-during-decode (`PDD`) long TTFT / wall **59.611182 / 59.710807 s**, decode-during-prefill (`DDP`) long TTFT / wall **58.620706 / 58.846915 s** (`130,110` cold tokens). In all `3` arrival repeats, `preferred_reused_tokens=111`, `fallback_reason=none`, `revoked_checkpoints=0`, `queue_wait_s` **19.613795 / 23.927980 / 22.396278 s**, and `source_wait_seconds` **19.492952 / 23.722483 / 22.305462 s** (`~19–24 s`). **Candidate [`alphastorm/ninfer#100`](https://github.com/alphastorm/ninfer/pull/100) (`p20/e1-source-wait`, head `7f2c71fd` on `df7aeb52`; CPU red `4d62c6996`, GPU `sm_120a` binary at `1c5` `20782176...`):** CPU `EngineCore` `31/31` + `ResourceManager` PASS (`source_wait` `0.0600276 s` at `60 ms` allowance, preferred `3` / root compute `4`), CI green (`42795274259`, `42795274400`, `42795274269`), and serial solo digest parity `3/3`, but on a `3`-pair warm-history GPU reproduction on `rtxpro6000-win-a` (`C2`/`BF16`/`DFlash2 K=7`/`chunk 1,024`/`KV 131,072`/`Host 20,867.734375 MiB`/`quota 4,096 MiB`, `B` computed `130,084` / cached `0`, `preferred/actual 111`, `computed 7`, `fallback none`, `State H2D 0`), base `source_wait` was **44.750 / 44.859 / 44.877 s** and candidate `1c5` was **44.740 / 44.776 / 44.945 s** (candidate TTFT **44.942 / 44.973 / 45.144 s**; binding `42 ms`, transfer `4 ms` vs `44.85 s` queue) because `engine_core.h:2703` reserves resident units before the fresh scan and `try_admit_one:1893` refuses while reclaim occupies the `Native` context slot (`poll` `2720–2722` then `refresh` `2723–2725` does not retry fresh before running resident work) | `2,048 MiB` scratch-quota hypothesis falsified (`23.073498 s` at `24,576 MiB`); root cause localized to retained-preferred-source wait (`19.49–23.72 s` on 5090, `~45 s` on proxy); [`alphastorm/ninfer#100`](https://github.com/alphastorm/ninfer/pull/100) closed unmerged and not shipped (`F`/`F2`/`F3` untouched; tracked in [`alphastorm/ninfer#102`](https://github.com/alphastorm/ninfer/issues/102)) |
| EXP-119 | `E4` opt-in prefill-pacing curve on `rtxpro6000-win-a` ([`alphastorm/ninfer#95`](https://github.com/alphastorm/ninfer/pull/95)) | Sweeping opt-in prefill-pacing parameters (`k1`..`k32`, `b250`/`b500`) in [`alphastorm/ninfer#95`](https://github.com/alphastorm/ninfer/pull/95) (`p20/e4-pacing`) on `rtxpro6000-win-a` (`3` fresh-server cold `130,084`-token repeats/scenario) lifts co-resident decode to `>= 100 tok/s` while keeping arrival TTFT `< 2 s`, long wall `<= 1.15×`, and byte-identical outputs | **Pre-cut proxy measurements on fork PR [`alphastorm/ninfer#95`](https://github.com/alphastorm/ninfer/pull/95) ([receipt](measurements/2026-11-10-p20-overnight.json)).** Against `e6ac7b70` cold baseline (**6.375 tok/s** co-resident decode, **469.989 ms** overlap gap p99, **0.619 s** `B-submit+1s` arrival TTFT, **46.491 / 45.484 s** prefill-during-decode `PDD` / decode-during-prefill `DDP` long wall): `e4-b95f-off` **6.600 tok/s**, gap p99 **469.881 ms**, arrival **0.618 / 0.626 s** (median/worst), long wall **46.400 / 45.358 s** (`0.998 / 0.997×`); `e4-b95f-k1-v2` **6.400 tok/s**, **469.524 ms**, **0.631 / 0.633 s**, **46.247 / 45.809 s** (`0.995 / 1.007×`); `e4-b95f-k2-v2` **12.025 tok/s**, **471.308 ms** (gap p50 **16.123 ms**), **0.634 / 0.637 s**, **48.561 / 45.930 s** (`1.045 / 1.010×`); `e4-b95f-k4-v2` **24.160 tok/s**, **395.725 ms** (p50 **14.530 ms**), **0.639 / 0.658 s**, **49.825 / 45.974 s** (`1.072 / 1.011×`); `e4-b95f-k8-v2` **47.901 tok/s**, **320.931 ms** (p50 **14.530 ms**), **0.639 / 0.670 s**, **49.703 / 45.892 s** (`1.069 / 1.009×`); `e4-b95f-b250-k16-v2` **73.400 tok/s**, **249.307 ms** (p50 **14.519 ms**), **0.641 / 0.651 s**, **49.945 / 45.821 s** (`1.074 / 1.007×`); and `e4-b95f-b500-k32-v2` **103.205 tok/s** (full-A **122.222 tok/s**, clears `>= 100 tok/s`), **265.079 ms** (p50 **14.467 ms**), **0.628 / 0.654 s**, **49.658 / 45.701 s** (`1.068 / 1.005×`). Corresponding-repeat `C2` outputs `DIFFERS` on every arm (the base itself varies across `C2` repetitions) | **shipped default-off (`0`)** in RTX 5090 `v0.7.0-qwen38-5090-beta.6` (`F3` `e0971faf`, `omp-ninfer` `v0.17.0`, published 2026-11-10; not enabled in shipped RTX 5090 or native `C2` profiles) |
| EXP-120 | `E2` serve robustness (`#446`, `#440`, `#441`, `numerical_failure`, `shutdown` stop/join split) in [`alphastorm/ninfer#98`](https://github.com/alphastorm/ninfer/pull/98) (`rtxpro6000-win-a`) | [`alphastorm/ninfer#98`](https://github.com/alphastorm/ninfer/pull/98) (`p20/e2-serve`, head `d191fb57` on `e6ac7b70`, binary `88bd2265...`; live GPU proof at `5e73453f`, binary `5fd3bdec...`) resolves upstream `Neroued/ninfer` `#446`/`#440`/`#441`, isolates non-finite row generation (`NaN`/`Inf`/`OOV`) to request-local HTTP `500` `numerical_failure`, and fixes managed final-save shutdown timeouts while preserving `MTP3` byte parity | **Pre-cut slice measurements on fork PR [`alphastorm/ninfer#98`](https://github.com/alphastorm/ninfer/pull/98) ([receipt](measurements/2026-11-10-p20-overnight.json)).** **(1) `#446` (`tool_arguments.cpp:5`, `chat_template.cpp:265`, `anthropic_messages_response.cpp`):** malformed tool-call history preserves raw input instead of throwing (live HTTP **200**). **(2) `#440` (`chat_template.cpp:148,185`):** all `7` reasoning-effort tiers accepted against the unchanged embedded artifact template (`81f924d4`, tiers `low`/`medium`/`xhigh`, mapping `minimal → low`, `high → xhigh`, `max → xhigh`; live `high` HTTP **200**). **(3) `#441` (`chat_template.cpp:103`, `translate.cpp`):** explicit disabled thinking ignores effort (live `disabled+max` HTTP **200**). **(4) `numerical_failure` (`execution.h`, `engine_core.h:1184`, `generation_errors.cpp:101`):** invalid generated row retires only that request as HTTP `500` `numerical_failure` while sibling/following requests remain serviceable (CPU `NaN`/`Inf`/`OOV` regression + GPU `ninfer_sampling_test --nonfinite-only` `6d5358c8...` exit **0**). **(5) `shutdown` (`engine_core.h:161,2612`, `http_server.cpp:710`, `main.cpp:103`):** generation cancellation precedes HTTP worker join and live catalog stays exportable until final save completes — on `rtxpro6000-win-a`, baseline `e6ac7b70` (`8235ada4`) with a resident request at stop failed with `managed final-save deadline exceeded` (exit `1`), whereas candidate `5e73453f` (`5fd3bdec`) completed `Stop` in **2.570988 s** (`2.571 s`, `complete: true`, `saved: 1`, `refused: 0`, `skipped: 0`) and restored **18** cached tokens. CPU `ctest` `3/3` passed (`15.14 s`); `MTP3` parity (`6fe9fe7e`, config `08223401...`) **5/5** byte-identical (`parity-0..2`, `pair-0..1`); CI on `d191fb57` all green (`42777721394`, `42777721650`, `42777721269`, Windows job `129700052085`) | **PASS** on CPU, live HTTP/GPU resilience, `5/5` `MTP3` parity, and CI — shipped in RTX 5090 `v0.7.0-qwen38-5090-beta.6` (`F3` `e0971faf`, `omp-ninfer` `v0.17.0`, published 2026-11-10) via [`alphastorm/ninfer#98`](https://github.com/alphastorm/ninfer/pull/98) (real-card `DFlash2` parity in `EXP-121`; carried native `v0.8.0-beta.2` runtimes remain at `a87de361`) |
| EXP-121 | RTX 5090 `DFlash2` `C1` greedy byte-identity oracle on integrated `F` (`a3fa0550`, [`alphastorm/ninfer#99`](https://github.com/alphastorm/ninfer/pull/99)) and council-remediated `F2` (`bdc665a3` / `F3` `e0971faf`, [`alphastorm/ninfer#101`](https://github.com/alphastorm/ninfer/pull/101)) vs production (`rtx5090-win-a`) | On `rtx5090-win-a` (runtime image `a0cbb8a5`, pinned release builder `e7f34ca2`, `sm_120a`), integrated `F` (`a3fa0550`) and post-council remediated `F2` (`bdc665a3`, runtime-source-identical to `F3` `e0971faf`) match shipped production `a87de361` (`cc99a460`) byte-for-byte across all `3/3` `DFlash2 K=7` `C1` greedy parity prompts (`parity-0`, `parity-1`, `parity-2`) | **Integration and council-remediation parity on [`alphastorm/ninfer#99`](https://github.com/alphastorm/ninfer/pull/99) and [`alphastorm/ninfer#101`](https://github.com/alphastorm/ninfer/pull/101) ([receipt](measurements/2026-11-10-p20-overnight.json)).** **Integrated candidate `F` (`f-parity-01`, source `a3fa0550cfb67b5dc706359ebca0ed02eb722b7c`, tree `73d0f8a9...`, binary `1afbb82d0131a507da77ebc372d95596fc2ce6835a1ee35da0e5d7987610131c`):** `C1` gating (`f-parity-01-pc1` vs `f-parity-01-fc1`) **PASS, 3/3 byte-identical** across `request`, `content`, `reasoning_content`, `reasoning`, and `finish` (`63` prompt / `34` completion tokens on `parity-0`, `content` SHA-256 `c2e3ac47...`, `reasoning_content` `e99ed7ff...`, `finish` `6f2be2fe...`); informational `C2` (`f-parity-01-pc2` vs `fc2`) also **3/3 byte-identical**. **Council `CR-20261110T083627Z-a3fa0550` (`4/4` seats on `a3fa0550` vs `a87de361`, `94` paths, `+4530/-1032`) and remediation `F2`/`F3` ([`alphastorm/ninfer#101`](https://github.com/alphastorm/ninfer/pull/101)):** council found a `P1` (`gemini-argon-R1`: a resident pause hitting an in-flight durable pressure save causes `pause_reclaim_victim`/`reserve_resident_units` to fail the `Engine` with `progress owner cannot obtain its legal unit`; this shape also exists in shipped source `a87de361`, where the `180` recent production completions that carry scheduling counters show zero preemptions; older requests lack those counters) and a `P2` (`daybreak-blue-R1` = `gpt-astra-R1`: failed fresh window not consuming its rotation in `take_fresh_window()`), both fixed in `bdc665a3` (`F2`, red test commit `538f6d92`, test-only `advance_prefill` fixture fix in `e0971faf` `F3`; `EngineCore` `35/35`, `Scheduler` PASS, `1,311/1,311` Ninja steps, CI runs `42792113220`, `42792113216`, `42792113378` all green). **Remediated candidate `F2` (`f2-parity-01`, source `bdc665a338dc0ea08478c566db3d1e5514eb0d7c`, tree `cc473d29...`, binary `92f0f636009ab824627084cd724c2eff57e814d40c857772206375083ff4a284`):** `C1` gating (`f2-parity-01-pc1` vs `f2-parity-01-fc1`) **PASS, 3/3 byte-identical** across all fields (informational `C2` waived at `F3` freeze) | **PASS (`3/3` byte-identical `DFlash2` `C1` parity)** on both `F` (`a3fa0550`, `1afbb82d`) and council-remediated `F2` (`bdc665a3`, `92f0f636`, runtime-identical to `F3` `e0971faf`) — shipped as RTX 5090 `v0.7.0-qwen38-5090-beta.6` (`F3` `e0971faf`) in `omp-ninfer` `v0.17.0` (published 2026-11-10) |

Entry detail:

- **EXP-001 — MTP3 verification economics.** Nsight Compute packets on the `sm_120a` Q4 SwiGLU
  pair kernels show decode (`M=1`) already at 75.2% of the measured read peak, and the 4-token
  verification batch moving the same bytes. Conclusion: speculative verification is
  bandwidth-amortized; acceptance rate, not verify cost, is the lever. Packets:
  [`profiles/`](https://github.com/alphastorm/ninfer/tree/7c1c1936d1fd8b645bc7a30cdcbe35cc6b12c206/profiles)
  at the integrated mainline commit.
- **EXP-002 — negative result, kept on the record.** The MMA candidate for the Q5 post-mixer was
  triaged `more-than-50-percent-slower` and rejected; SIMT split-2 remains production. Negative
  results are part of the ledger so the next contributor does not re-run the same dead end.
- **EXP-003 — correctness enabler.** ReplaySSM-style gate caching (idea lineage: Tri Dao's
  "cache SSM inputs, not state"; see also the
  [ninfer-3090](https://github.com/Don-Chad/ninfer-3090) port) is what lets MTP3 speculate over
  hybrid GDN/attention layers without state divergence — a precondition for every speculative
  speedup on this architecture.
- **EXP-004 — prefill headroom.** The upstream NVFP4 campaign proves the prefill ceiling moves
  ~3.5× with tensor-core-native weights. The shipped artifact is `groupwise-int`; an NVFP4-profile
  product lane would need its own qualification pass (quality table in
  [`BENCHMARKS.md`](BENCHMARKS.md)).
- **EXP-005–007 — frozen agent-shaped MTP depth campaign.** Each lane ran MTP0/3/5/7 with one
  unchanged binary, model, corpus, seed, and greedy request configuration. MTP3 was fastest on all
  three lanes and in both repetitions. K5/K7 trailed it by 13.57%/24.72% on RTX 5090,
  7.29%/20.17% on RTX 4090, and 11.34%/22.46% on RTX 3090, so analysis revision 5 retains the
  qualified MTP3 incumbent and rejects deeper drafting for these artifacts. The v3 output
  projection also exposed baseline nondeterminism: MTP0 changed on 1/12 repeated steps on RTX 5090
  and 10/12 on RTX 4090, while RTX 3090 repeated exactly and its MTP3/5/7 outputs differed from
  MTP0 on 6/8/4 requests. Missing campaign and fresh-process controls leave that exact-output
  attribution unresolved; they do not erase the no-change throughput decision. No public profile
  changed. Receipts:
  [5090](measurements/2026-09-04-rtx5090-mtp-agent-ablation.json) ·
  [4090](measurements/2026-09-04-rtx4090-mtp-agent-ablation.json) ·
  [3090](measurements/2026-09-04-rtx3090-mtp-agent-ablation.json). The generated public corpus and
  frozen build identities are [recorded separately](measurements/2026-09-04-mtp-agent-corpus.json)
  ([builds](measurements/2026-09-04-mtp-ablation-builds.json)).
- **EXP-008–011 — per-lane runtime variant campaign (2026-09-04).** One campaign identity, one
  fresh server process per arm, the frozen 24-request agent corpus, and the shipped lane profile
  as an in-campaign incumbent (verified against each host's installed configuration). The primary
  metric is modeled session engine seconds from measured prefill and decode throughput against
  two recorded session shapes (573,956 prefill / 30,936 decode tokens and 1,543,555 prefill /
  193,440 decode tokens); both shapes come from RTX 5090 production logs and are applied to every
  lane, so the 4090 and 3090 figures weight 5090 token mixes with their own measured rates.
  Promotion needs a 5% improvement for every reference in every repetition, the lane's qualified
  context in automatic KV capacity, and a passing quality gate. Arms that change the artifact or
  KV format also ran the private 89-case role corpus against the incumbent's own run (84 effective
  cases: the five JSON-schema cases are rejected by contract on every arm), and a repeated screen
  reproduced every aggregate metric exactly across fresh processes
  ([repeatability](measurements/2026-09-04-rtx5090-quality-repeatability.json)), so its
  differences are systematic on this corpus; whether a two-case shift generalizes is a corpus-power
  question the screen cannot answer. Results: the RTX 5090 retains `groupwise-int`/BF16/MTP3. The
  causal chain for `nvfp4` is: the weights are 3.28 GB larger → BF16 KV at 131,072 context no
  longer fits in 32 GB (the engine refuses its 10.41 GB runtime reservation) → the only way to run
  it on this card is INT8 KV → INT8 KV alone (`gw-int8`, same artifact as the incumbent) regresses
  every screen criterion, while `nvfp4` on INT8 KV halves long-prefix TTFT (11.7 s → 5.1 s on a
  35K-token prefix) and lands better than `gw-int8` on every criterion but still two cases behind
  the BF16 incumbent on grounding. `nvfp4` was therefore never measured against a BF16 reference;
  the 2.22× prefill and 15.5–28.7% modeled session gain would be back on the table with more VRAM
  or a smaller NVFP4 artifact. The RTX 4090 promotes prefill chunk 2,048 (TTFT 21.9 s → 17.7 s on
  the same prefix, +270 MiB peak): the stable signal there is prefill (1,605 → 1,877 → 1,971 tok/s,
  reproducible to 0.3% within each arm), while decode on that lane varies about 4.7% between the
  incumbent's own repetitions, which is why chunk 1,024 (+4.2% minimum) fell short of the margin
  and 2,048 (+5.5% minimum) cleared it — larger chunks help this lane and 2,048 measured best,
  with 4,096 flat on prefill and lower on decode. The RTX 3090 keeps its profile and gains a
  measured 131,072-token capacity finding. INT8 KV on the RTX 4090 was faster (+8.8% to +13.3%)
  but peaks at 23,180 of 24,564 MiB and fails the same screen. Receipts:
  [5090](measurements/2026-09-04-rtx5090-variant-campaign.json) ·
  [4090](measurements/2026-09-04-rtx4090-variant-campaign.json) ·
  [3090](measurements/2026-09-04-rtx3090-variant-campaign.json); arm matrix, artifact facts, and
  the recorded gate amendment: [arms](measurements/2026-09-04-variant-campaign-arms.json). Runner:
  [`scripts/run_variant_campaign.py`](../scripts/run_variant_campaign.py) with host launchers in
  [`scripts/hosts/`](../scripts/hosts/).
- **EXP-012 — template-fork warm starts (2026-09-04).** [`scripts/fleet_probe.py`](../scripts/fleet_probe.py)
  now forks from the template id after the restart as well, verifies the restart through the
  lane's cumulative prefill counter, and waits for the RTX 4090's automatic save where no explicit
  save exists. Measured on the shipped lanes: the RTX 5090 (v0.4.6 container) prefills a
  57,853-token template in 21.8 s, saves it explicitly in 13.0 s (4,505,854,444 bytes), and serves
  stored sibling forks at 1.38 / 22.50 / 1.26 / 22.71 s — the server records `private_long_anchor`
  then `root` alternately, with `private_catalog capacity 2, occupied 2`; the same probe against
  the retained v0.4.4 container reproduces the alternation
  ([bisect](measurements/2026-09-04-template-fork-rtx5090-v044-bisect.json)), a 67,681-token
  template gives four anchor hits at 1.25–1.39 s
  ([67K](measurements/2026-09-04-template-fork-rtx5090-67k.json)), and unstored forks give three
  of four ([unstored](measurements/2026-09-04-template-fork-rtx5090-unstored-forks.json)), so the
  loss is a serve/engine anchor-retention policy below roughly 64K tokens, not an image
  regression. After a verified restart (57 s to ready) the first continuation restores the
  checkpoint before request timing starts (server TTFT 0.41 s, client wall 24.7 s ≈ 190 MB/s),
  which equals the cold prefill, and template forks alternate again. The RTX 4090 (durable v0.2
  service) saves automatically 6.5 s after the turn (1,130,468,708 bytes), serves every sibling
  fork as `full_reset` (41–47 s), and restores in ≈130 s of client wall (server TTFT 0.26 s) against
  a 41.2 s prefill; the RTX 3090 (38,215-token template) saves explicitly in 10.0 s, serves forks
  as `full_reset` (49–51 s), and restores in ≈91 s against a 49.3 s prefill. Warm starts therefore
  exist today only as device-resident forks on the RTX 5090; disk restore is slower than
  re-prefill on every lane and 10–15× slower per byte on the native lanes than in the container.
  Receipts: [5090](measurements/2026-09-04-template-fork-rtx5090.json) ·
  [4090](measurements/2026-09-04-template-fork-rtx4090.json) ·
  [3090](measurements/2026-09-04-template-fork-rtx3090.json).
- **EXP-013 — fanout anchor retention on the RTX 5090: diagnosis and configuration fix
  (2026-09-05).** The alternation in EXP-012 is capacity, not policy. Status counters sampled
  between forks show `private_evictions` rising by exactly one per completed stored fork against a
  private catalog of two entries (the default is 2 × concurrency) backed by two device-state slots,
  and the cold forks' planner diagnostics record a 477 s incumbent with the anchor subtree still
  queued at a 28 s lower bound. Two source changes were built and rejected on the same probe:
  raising the planner's 5 ms search cap to 50 ms only changed the stop reason
  (`value_of_next_expansion` after 354 targets, same decision), and marking only the inherited
  frontier on stored continuations only shifted the phase (cold / hot / cold / hot).
  `--max-private-continuations 8` alone fixed 57.9K and then lost all four forks of a following
  67.7K template in the same process (`host_state 8/8` saturated, predicted materialization
  ≈600 s). With the backing slots scaled — `--max-private-continuations 8 --device-state-slots 4
  --host-state-slots 24` on the unchanged shipped v0.4.6 binary — one container kept 12/12 forks
  on the anchor path across 57.9K, 67.7K, and a loaded-catalog 57.9K (11 under 2 s; the first
  67.7K fork paid a 4.27 s state materialization for 5.29 s wall against 1.39 s on the shipped
  default at that size) for 0.43 GiB of startup slack (3.56 → 3.13 GiB, headroom kept at
  1.00 GiB) and 28,632 MiB after twelve forks vs 28,125–28,195 MiB on the shipped profile, with
  automatic KV capacity unchanged at 131,072. That configuration is the v0.4.8 RTX 5090 candidate
  profile; its acceptance receipt is this probe at both template sizes in one process. Filed as
  [alphastorm/ninfer#35](https://github.com/alphastorm/ninfer/issues/35). Receipt:
  [configuration sweep](measurements/2026-09-05-fanout-anchor-configuration-sweep-rtx5090.json).
- **EXP-014 — checkpoint restore path on the native lanes (2026-09-05).**
  [`scripts/restore_probe.py`](../scripts/restore_probe.py) restores one session across two
  verified restarts while polling the checkpoint status endpoint. The second restore is not
  faster (RTX 4090: 132.8 s then 149.0 s for 1.13 GB, ≈8.5 MB/s; RTX 3090: 91.8 s then 92.2 s for
  1.68 GB, ≈18.5 MB/s), so page cache and first-read effects are excluded and the restore path
  itself is the cost; the status endpoint stops answering for the whole restore on both lanes;
  neither train logs restore progress. The RTX 4090's own qualification recorded a 120K-token
  restore in 7.0–10.8 s on the same release identity, which is the first discrepancy to
  establish. No IO-path change was made; filed with the numbers as
  [alphastorm/ninfer#36](https://github.com/alphastorm/ninfer/issues/36). Receipts:
  [4090](measurements/2026-09-05-restore-probe-rtx4090.json) ·
  [3090](measurements/2026-09-05-restore-probe-rtx3090.json).
- **EXP-015 — lane requalification of the three configuration changes (2026-09-05).** Each lane
  reran its own qualification tooling with the changed configuration. RTX 3090: the 14-phase
  orchestrator (`tools/qualification/qualify_rtx3090.py`, long-context stage rebound to the
  130,048-token `long_niah_128k` fixture) built `v0.2.3-beta.1` from commit `2ce6c9dc` on the
  builder host, packaged it deterministically, installed it beside the shipped release, and
  passed protocol 15/15, exact 128K retrieval in 218.2 s, restart (310,212,985-byte checkpoint,
  45 cached tokens, PID replaced), two-direction rollback, security, the OMP read-tool run, and
  managed C1 (90.23 decode / 890.72 prefill tok/s, 93.43% MTP, 300.38 W, 22,548 MiB), then
  restored the 370 W owner state. RTX 4090: commit `b9c4636b` rebuilt the code-identical binary
  with the new patch-stack identity in 40 s (incremental), `New-Package.ps1` assembled
  `v0.2.1` (`1c66f7d5`), the installer placed it beside `v0.2.0` with the inherited operator
  GPU-owner adapter, and `Invoke-Qualification.ps1 -Profile MTP3` passed protocol, the
  102,060-token session (68.0 s first turn vs 84.9 s shipped; post-restart 225.6 s, unchanged),
  persistence (`append_frontier`, 102,075 tokens), and the OMP golden run in 6m44s. RTX 5090:
  the lifecycle tool started the candidate with the canonical configuration `95765a38` on the
  shipped image; [`scripts/qualify_rtx5090_profile.py`](../scripts/qualify_rtx5090_profile.py)
  measured exact 130,048-token retrieval cold (58.9 s server prefill, 2,207 tok/s, 28,558 MiB
  used), 2,048-token decode at 136.0 tok/s (41.2% MTP acceptance, 2.24 tokens/round, byte-identical
  across five runs), and the fork/delete/no-resurrection arc across a `docker restart`;
  `fleet_probe.py` then held 4/4 anchor hits at 57.9K (1.36/1.22/1.22/1.20 s) and 67.7K
  (1.43/1.30/1.37/1.39 s) in one process with a 4.5 GB explicit save and a verified restart.
  After the restart the resumed template's first sibling fork re-prefilled once (22.2 s, `root`)
  before three hot forks: restored sessions carry their endpoint, not the base anchor. Receipts:
  [5090 gates](measurements/2026-09-05-rtx5090-v048-profile-gates.json) ·
  [5090 fanout 57.9K](measurements/2026-09-05-rtx5090-v048-fanout-57k.json) ·
  [5090 fanout 67.7K](measurements/2026-09-05-rtx5090-v048-fanout-67k.json) ·
  [lane receipts](../releases/v0.4.8/qualification/).
- **EXP-016 — fleet routing on a fixed workload (2026-09-05).**
  [`scripts/fleet_dispatch.py`](../scripts/fleet_dispatch.py) dispatches the frozen agent corpus
  (7 scenarios × 2 repetitions = 14 independent jobs, 24 requests) across one, two, or three
  lanes with one worker per lane, three policies, two batch repetitions per configuration, and
  per-lane output projections. Solo batches: RTX 5090 66.8 / 66.7 s, RTX 4090 154.9 / 156.0 s,
  RTX 3090 258.8 / 258.6 s. Measured per-scenario costs (5090 / 4090 / 3090): long replay
  14.9 / 48.6 / 91.0 s, medium branch 4.7 / 13.5 / 17.3 s, long decode 3.8 / 5.7 / 9.0 s, tool
  round trip 2.4 / 2.6 / 3.6 s, history p90 1.7 / 1.5 / 2.1 s, history p50 1.1 / 1.3 / 1.9 s,
  short 0.8 / 1.1 / 1.1 s. Naive longest-first dynamic dispatch is bounded by the biggest job
  landing on a slow lane: 5090+4090 51.2 / 52.5 s (the 4090 spends ~50 s on one long replay while
  the 5090 finishes 12 jobs in 42 s), three lanes 47.2 / 50.9 s. Static role pinning sends both
  long replays to the 4090 and loses outright: 100.3 / 101.5 s. Cost-aware assignment (longest
  processing time first over the measured per-lane costs; `--policy cost` fed by the solo
  receipts) lands within 4 s of its prediction: 5090+4090 43.4 / 43.9 s (predicted 39.5), three
  lanes 32.3 / 32.9 s (predicted 29.7) with lane busy times 29.9 / 28.2 / 29.4 s. Outputs are
  byte-identical across the two batch runs on the 5090 and 3090 lanes; the 4090 differs on 2-9
  steps between runs, matching the same-process variation its MTP3 arms recorded on 2026-09-04
  (17-22 of 24 requests). Receipts:
  [5090](measurements/2026-09-05-fleet-dispatch-main-solo.json) ·
  [4090](measurements/2026-09-05-fleet-dispatch-heavy-solo.json) ·
  [3090](measurements/2026-09-05-fleet-dispatch-scout-solo.json) ·
  [two-lane dynamic](measurements/2026-09-05-fleet-dispatch-main-heavy-dynamic.json) ·
  [two-lane cost](measurements/2026-09-05-fleet-dispatch-main-heavy-cost.json) ·
  [three-lane dynamic](measurements/2026-09-05-fleet-dispatch-three-lane-dynamic.json) ·
  [three-lane role](measurements/2026-09-05-fleet-dispatch-three-lane-role.json) ·
  [three-lane cost](measurements/2026-09-05-fleet-dispatch-three-lane-cost.json).
- **EXP-017 — native-lane restore path fixed at source (2026-09-05).** EXP-014 left the cost
  inside the restore path; a sequential read of the RTX 4090's real checkpoint files ran at
  2,248 MiB/s on the same NVMe, so the disk was excluded. The reader issued one request per KV
  page segment and, on Windows, every request was its own DirectStorage submit plus a fence
  wait; with `rk2v4-e8` pages that fixed cost per request held restores near 8.5 MB/s. Payload
  files are written contiguously in segment enumeration order, so the engine now plans one read
  per staging window and scatters each window to the device with asynchronous copies and one
  synchronization, and the store's Windows adapter submits a reader call as one bounded batch
  (`plan_continuation_checkpoint_reads`, `split_continuation_checkpoint_read` in the runtime
  contract; unit tests for the plan invariants and a 70 MiB batched read; lane commits `d22ce3fd`
  on the RTX 4090 and `3756db6e` on the RTX 3090; on-disk format unchanged).
  [`scripts/restore_probe.py`](../scripts/restore_probe.py) now also plants three run-specific
  ledger keys near the template's start, middle, and end and requires every restored
  continuation to quote them, with one in-process control, so a restore that scatters the wrong
  bytes cannot pass on timing alone. Same session shapes as EXP-014, shipped binary versus the
  candidate under the release's exact argv: RTX 4090 (57,889-token template, 1.13 GB)
  146.6 s → 5.6 s and 133.4 s → 5.6 s, the restored turn now costing less than the 7.7 s
  in-process control turn; RTX 3090 (38,251-token template, 1.68 GB) 91.8 s → 10.8 s and
  92.2 s → 10.7 s. All retrievals exact on both binaries and lanes. The RTX 5090 container has
  a different restore reader and is not affected. Receipts:
  [4090 shipped](measurements/2026-09-05-restore-probe-rtx4090-v0.2.1.json) ·
  [4090 candidate](measurements/2026-09-05-restore-probe-rtx4090-candidate.json) ·
  [3090 shipped (EXP-014)](measurements/2026-09-05-restore-probe-rtx3090.json) ·
  [3090 candidate](measurements/2026-09-05-restore-probe-rtx3090-candidate.json). Publication
  follows the lane rule: each lane requalifies its exact binary before a component release.
- **EXP-018 — checkpoint replication on all three lanes (2026-09-05).** Roadmap v0.5 §1, gated
  on EXP-017 (restores in seconds) and on the security gate it names: manifest origin
  authentication (ninfer#32) existed only on the RTX 5090 container, so it was ported to both
  native lanes first (every save publishes `manifest.mac`, an HMAC-SHA256 over the manifest keyed
  by material derived from the bearer key and held outside the checkpoint root; load and status
  verify origin before trusting manifest content; a present-but-wrong tag quarantines, an absent
  tag under `--session-checkpoint-require-origin-auth` refuses reversibly; RFC 4231 vectors and
  window/strict/transient-fault tests; lane commits `17e2f87d` and `7031893c`).
  [`scripts/checkpoint_sync.py`](../scripts/checkpoint_sync.py) replicates only verified,
  published generations (manifest-listed files by size and SHA-256, staged outside every scanned
  directory, one-rename publication, `current` last, unMAC'd generations refused by default).
  [`scripts/sync_probe.py`](../scripts/sync_probe.py) then proved the contract on each lane
  against the real store: checkpoint a 58K-token (5090, 4090) or 38K-token (3090) session,
  export, carry the replica to the macOS workstation over the tailnet, stop the server, delete
  the session directory, carry the replica back, import, restart, and the continuation restores
  from the imported generation and quotes three planted ledger keys exactly. The same replica
  with one payload byte flipped is refused by the tool at import (`does not match its manifest
  digest`); the same replica with a coherent manifest edit passes the tool and is quarantined by
  the runtime at load (`state: corrupt`, continuation `checkpoint_corrupt` on the native lanes
  and `previous_response_not_found` on the container; no resurrection). Timings: RTX 5090
  4.5 GB export 158 s, import 10.1 s, restored continuation 24.8 s; RTX 4090 1.13 GB export
  6.2 s, import 4.2 s, restored 7.4 s; RTX 3090 1.69 GB export 19.7 s, import 11.9 s, restored
  11.5 s. The off-machine hop's 1.8–3.5 MB/s was the workstation, not the fleet: it was in
  Japan that night, two transpacific tunnel crossings with one leg queueing to 900 ms RTT.
  EXP-019 measured and fixed the path the fleet actually uses. Cross-lane import is
  structurally unreachable: the session namespace binds the bearer key and the fingerprint
  binds binary and profile. Receipts:
  [5090](measurements/2026-09-05-sync-probe-rtx5090.json) ·
  [4090](measurements/2026-09-05-sync-probe-rtx4090.json) ·
  [3090](measurements/2026-09-05-sync-probe-rtx3090.json).
- **EXP-019 — replica transport, measured and fixed (2026-09-06).** EXP-018 moved its replicas
  through the macOS workstation, which was in Japan: every hop crossed the Pacific twice and one
  leg queued to 900 ms RTT, so its 1.8–3.5 MB/s said nothing about the fleet. Four real causes
  came out of the follow-up
  ([transfer paths](measurements/2026-09-06-replica-transfer-paths.json)): a single ssh stream is
  bound by the SSH channel window (≈1.6 MB in flight, so 8–14 MB/s at 67–190 ms whatever the
  link); the workstation's `ssh_config` set `Compression yes` globally, which made zero-filled
  test files look 10× faster than real payloads and put zlib in front of every real one;
  `tar`'s default 10 KiB records made the container host's 9p bounce look like the problem
  (`tar -b 8192` writes 2.6 GB to `/mnt/c` in 9.1 s against 72.8 s, and the export itself is
  4.9 s for 2.74 GB); and Windows OpenSSH cannot carry bulk between two Windows hosts at all —
  `ssh.exe` as a client inside an sshd session stalls on any large binary stream, whatever the
  sender, and `wsl.exe` stalls on binary stdout, so a WSL-resident file cannot be served through
  the Windows sshd either. [`scripts/hosts/pscp.py`](../scripts/hosts/pscp.py) therefore moves a
  file as N ranged reads over independent ssh connections where one end is not Windows
  (compression off, file-backed handles because pipes hang Windows `ssh.exe`, SHA-256 verified on
  both ends), and as bearer-token ranged HTTP over the tailnet where both ends are Windows —
  eight streams for ssh (a Windows sshd resets above roughly that) and sixteen for HTTP, where
  each connection is window-bound and more still scale. The end-to-end proof
  ([round trip](measurements/2026-09-06-cross-site-replication-rtx5090.json)) checkpoints a
  session on the RTX 5090, exports and archives it on ext4 (2.7 s + 0.5 s), serves it to the SF
  host at **11.5 MB/s**, destroys the local copy with the container stopped, fetches the replica
  back at **56.3 MB/s**, imports it in 2.6 s, and the restarted server's continuation quotes all
  three planted ledger keys exactly. A 4.35 GB replica measured 63.4 MB/s on the return leg. The
  asymmetry is the receiver, not the path: the same link and tool deliver 11.5 MB/s into a
  Windows host and 56–63 MB/s into WSL ext4, so replication targets should be Linux endpoints.
  Host-side corrections in the same pass: the global ssh compression, the WSL sshd's port
  collision with the Windows sshd (loopback :22 under mirrored networking, socket unit failed
  since July, now :2222 as documented), and per-host replica keys so any fleet host can address
  any other over the tailnet.
- **EXP-020 — a NAS is the right replication target for co-located lanes (2026-09-07).** The
  fleet's Synology (`ninfer-cache` share, a least-privilege SMB identity with no access to any
  other share) shares a LAN with two of the three lanes and reaches about 1 GbE line rate from
  both: 115.8 MB/s write and 117.6 MB/s read from the RTX 4090 host, 96.0 / 102.3 from the RTX
  3090 host, measured with raw unbuffered IO over 2 GiB of incompressible payload. Reaching the
  same appliance from the remote RTX 5090 host over the tailnet is the opposite story - 6.4 MB/s
  write, 22.7 MB/s read - because a DS918+ terminates WireGuard in userspace on a low-power CPU;
  that is worse than EXP-019's direct host-to-host path, so that lane keeps using it. One
  published generation per co-located lane is now replicated to the share and verified in place. Two
  operational facts worth keeping: the 4090 lane's replica is origin-authenticated while the
  3090 lane's surviving generations predate `manifest.mac` and replicate only under
  `--allow-unauthenticated`; and SMB from a non-interactive session on these hosts requires a
  registered SYSTEM scheduled task running `net use` with the credential as an argument -
  `New-SmbMapping` and `New-SmbGlobalMapping` both fail with Windows error 1312 ("a specified
  logon session does not exist"), even when spawned through `Win32_Process Create`. Receipt:
  [NAS replication](measurements/2026-09-07-nas-replication-sf-lanes.json).
- **EXP-021 — warm arrival: a restored session still re-prefills once (2026-09-07).** Roadmap
  v0.5 §2 promised that a checkpointed template makes subagent forks start hot. It does not yet
  hold across a restart, and the reason was not the restore path. Measured on the shipped v0.4.8
  profile at 57.9K tokens: four forks before a restart are hot (1.17-1.32 s, all
  `private_long_anchor`), and after a restart the resume costs 23.7 s while the first fork costs
  **22.1 s with reuse path `root` and zero reused tokens**. Restore + four forks is 49.3 s
  against 26.7 s for not checkpointing at all, so for the fanout pattern durable resume is
  currently a net loss. The control that isolated it: restoring a checkpoint taken *before* any
  fork serves four hot forks on the unmodified shipped binary, so restore reinstates anchors
  correctly - the anchor simply was not in the payload. A session's binding follows the newest
  continuation and a checkpoint serialises exactly one continuation, so a fork left its anchor
  behind on the parent; the byte counts show it directly (4,505,854,445 bytes saved before a
  fanout, 4,351,909,712 after, one StateImage fewer). Two fixes on branch `feat/warm-arrival`:
  a fork admitted through a long anchor now inherits a reference to that immutable anchor image,
  and consuming a session endpoint no longer charges a shared optional state to the new
  lineage's entitlement - a latent accounting bug that the first fix made reachable and that
  returned HTTP 500 on any resume of an anchor-carrying session. With both, the post-fanout
  checkpoint carries the anchor again and a fork issued as the first post-restart request is hot;
  an endpoint resume arriving first still leaves one 22.2 s re-prefill, with the anchor provably
  retained (a save right after that resume still carries two StateImages) and indexed, which
  puts the remaining defect in candidate admission for a just-consumed lineage. Device-state
  capacity is not the cause: 4 and 8 slots behave identically. Nothing was released; the
  candidate binary was built outside the appliance's canonical build. Receipt:
  [warm arrival](measurements/2026-09-07-warm-arrival-rtx5090.json).
- **EXP-022 — warm arrival holds: the anchor was evicted, not misjudged (2026-09-08).** The
  EXP-021 reading was wrong about where the loss sat. A catalog trace on the candidate showed the
  restored continuation carrying anchors at 67,762 and 67,780 before the resume and at 67,870 and
  67,908 after it: the two StateImages a post-resume save carried were the resume's own new
  anchors, not the template anchor. Every Responses request marks two private anchors (the
  inherited frontier, for its siblings, and its pre-generation frontier, for its children), a
  continuation retains two, and the replacement victim was the lowest frontier - the earliest
  anchor on the lineage, which is exactly the template boundary every sibling fork reuses. One
  continuing turn on a lineage was therefore enough to lose it, restart or not; the fanout
  patterns measured in EXP-013 and the v0.4.8 gates never took that turn. The victim is now the
  anchor whose loss costs the least re-prefill: the one with the smallest gap to its lower
  neighbour (root for the earliest), ties evicting the newer anchor, so the earliest recovery point
  survives for the life of the lineage and the retained set stays as widely spaced as possible.
  It is a pure function of frontiers, so it holds right after a restart when no hit history
  exists. Measured with the new `scripts/warm_arrival_probe.py` on the candidate at a 67.7K
  template across a verified restart: resume first, 4.2 s for restore plus resume, then sibling
  forks in **2.9 s and 1.3 s** on `private_long_anchor` (frontier 67,712); fork first, 3.7 s then
  1.3 s. Restore plus the whole post-restart sequence is 8.4 s and 6.7 s against 26.7 s for not
  checkpointing at all, so the v0.5 §2 promise holds on this candidate. Receipt:
  [warm arrival](measurements/2026-09-08-warm-arrival-rtx5090-candidate.json).
- **EXP-023 — restore is no longer hash-bound (2026-09-08).** The 24 s restore hashed every
  payload byte twice, at load and again as the engine streamed it, with a scalar SHA-256 that
  runs at 0.33 GB/s on the appliance's Zen 4, and read the disk at queue depth one both times.
  Three source changes on `feat/warm-arrival`: the bulk path of the hasher now uses the x86 SHA
  extensions when the CPU has them (2.66 GB/s on the same core, bit-exact against the scalar path
  for every length from 0 to 1,024 bytes, ragged multi-megabyte updates, and the "abc" vector);
  load no longer hashes engine payloads at all - the streamed hash on exactly the bytes the engine
  consumes is the single verification, which is what closed `alphastorm/ninfer#21` in the first
  place, and a mismatch still fails the import closed and quarantines on the next load; and the
  io_uring reader runs on its own thread issuing eight 4 MiB reads per batch while the serve-side
  reader keeps the next 32 MiB batch on the device as the previous one hashes. A 5.2 GB session
  restores in **3.8 s and 3.8 s** across two verified restarts with exact planted-key retrieval
  (was 24-27 s). Verified-or-refused was re-proven live with the new `--tamper-cmd` round of
  `scripts/restore_probe.py`: one byte flipped in the middle of the 4.4 GB KV payload while the
  lane was down, and the resume was refused with 404 `previous_response_not_found` in 2.8 s,
  status reported `corrupt`, a second attempt was refused, and the generation was quarantined.
  Receipt: [restore probe](measurements/2026-09-08-restore-probe-rtx5090-candidate.json).
- **EXP-025 — the native lanes serve mainline (2026-09-08).** The two native Windows lanes had
  drifted ~8K lines each from mainline, so they had no context cache, no warm arrival, and the
  restore path fixed in EXP-023 would have needed porting twice. Stage 1 compiled mainline for
  Ada; this entry is stages 2 and 3: the Windows platform code (D3D12 residency arena,
  DirectStorage read queue, MSVC 19.44 build of the host tree) and Ampere `sm_86`, then
  serving. Every kernel suite runs on the hardware now - the earlier Windows run had excluded
  them by name - and they pass 100/100 on both builds on the Ada GPU (the `sm_86` binaries run
  on `sm_89`; 94 suites execute, the five real-artifact suites and the external-tokenizer
  frontend suite skip). An activation path a build excludes (NVFP4 W4A4 on both, FP8 A8 and
  FP8-KV on Ampere) ends a test arm as excluded on the stub's refusal and the dedicated suites
  require that refusal, so a stub that quietly fell back to A16 would fail them. Five defects
  showed only on the hardware, none in the earlier builds: the BF16 GDN gating plan hard-coded
  the RTX 5090's cooperative-grid budgets (340/680 CTAs over 170 SMs), so on 128 SMs the first
  prompt longer than one tile died with `cudaErrorCooperativeLaunchTooLarge` - the budget is now
  the driver's occupancy for the exact instantiation times the SM count, with fall-through to
  the next split; its residency query defaulted a different warp count from the launchers; the
  INT8-cache prompt Attention kernel, shaped for Blackwell's allocator (16 warps at 120
  registers), spilled 200 B/thread under Ada's 128-register cap for a 512-thread CTA, so a 42K
  prompt ran at 390 tok/s and a 130K prompt did not finish in fourteen minutes at 130 W - on
  `sm_89`/`sm_86` it now covers 32 query rows with eight warps at up to 255 registers, zero
  spill; the streamed restore issued the next 32 MiB batch while the previous one hashed, which
  io_uring supports and the one-slot, one-fence DirectStorage queue does not, so every native
  restore was refused as `previous_response_not_found` while status said `available` - the
  read-queue contract now names whether a backend overlaps batches; and that refusal was never
  logged. Served in candidate windows against the installed releases with the same 130,048-token
  fixture, gate script, host, and day: the RTX 4090 retrieves exactly in **86.8 s (1,499 tok/s)
  against 97.5 s (1,333)** and decodes 2,048 tokens at **103.8 against 88.4 tok/s** wall; the
  RTX 3090 **208.6 s against 219.5 s** and **60.3 against 52.8 tok/s**; the agent protocol
  passes on both with no resurrection across a verified restart. The context cache arrives
  whole: on a 67.7K template four sibling forks take 1.8-2.0 s (4090) and 2.5-2.9 s (3090)
  device-resident, a 2.9 GB explicit save 4.0 s / 15.4 s, and after a restart the resume costs
  4.1 s / 16.4 s and the four forks 1.8-1.9 s / 2.5-2.6 s, every one on `private_long_anchor`;
  warm arrival holds in both orders (4090 resume-first 4.5 / 3.1 / 1.8 s, fork-first
  4.1 / 1.6 / 3.0 s; 3090 17.3 / 3.1 / 2.6 s and 16.5 / 3.3 / 2.7 s) with planted keys exact
  before and after; restore is 5.0 / 4.2 s on the 4090 and 17.1 / 16.6 s on the 3090 for
  2.9 GB, and a flipped payload byte is refused (404), marked `corrupt`, and quarantined on
  both. One sizing rule fell out: at 131K INT8 the RTX 4090 has 169 MiB of WDDM budget left
  with four device-state slots and the driver pages device memory - decode drops to 47 tok/s
  and every fork and resume is 2.5× slower - while two slots leave 463 MiB and full speed, and
  one slot re-prefills the first fork (38.6 s on reuse path `root`: one cached device state
  cannot hold both the template and the edit; the three forks after it are hot);
  the RTX 3090 keeps 835 MiB at four slots and is unaffected. Both hosts were returned to their
  found state (release serving on the 4090, stopped on the 3090). Every receipt is bound to the
  server's reported identity (binary, source, model, resolved configuration), captured at the
  start and checked after every restart; the probes gained that binding tonight, along with the
  slowest-fork fields that a median had hidden. Runtime branch `port/native-lanes-on-mainline`
  at `6fd9e135` (runtime through `8b3dd4a9`, tests after). Receipts, RTX 4090:
  [ladder](measurements/2026-09-08-rtx4090-mainline-device-state-ladder.json) ·
  [gates](measurements/2026-09-08-rtx4090-mainline-profile-gates.json) ·
  [release gates](measurements/2026-09-08-rtx4090-v0.2-profile-gates.json) ·
  [fanout](measurements/2026-09-08-rtx4090-mainline-fanout-57k.json) ·
  [one slot](measurements/2026-09-08-rtx4090-mainline-fanout-57k-slots1.json) ·
  [four slots](measurements/2026-09-08-rtx4090-mainline-fanout-57k-slots4.json) ·
  [warm arrival](measurements/2026-09-08-rtx4090-mainline-warm-arrival.json) ·
  [restore](measurements/2026-09-08-rtx4090-mainline-restore.json); RTX 3090:
  [ladder](measurements/2026-09-08-rtx3090-mainline-device-state-ladder.json) ·
  [gates](measurements/2026-09-08-rtx3090-mainline-profile-gates.json) ·
  [release gates](measurements/2026-09-08-rtx3090-v0.2.5-profile-gates.json) ·
  [fanout](measurements/2026-09-08-rtx3090-mainline-fanout-57k.json) ·
  [one slot](measurements/2026-09-08-rtx3090-mainline-fanout-57k-slots1.json) ·
  [two slots](measurements/2026-09-08-rtx3090-mainline-fanout-57k-slots2.json) ·
  [warm arrival](measurements/2026-09-08-rtx3090-mainline-warm-arrival.json) ·
  [restore](measurements/2026-09-08-rtx3090-mainline-restore.json).
- **EXP-026 — qualifying the mainline native lanes (2026-09-09).** EXP-025 proved the mainline
  runtime serves both native lanes; this is the release path around it, which had never run
  since the port. Five blockers, each reproduced before it was fixed. The package builder asks
  every shipped binary for `--version` to bind one build identity, and the mainline bench had
  no such arm (the lane branches did). `transfer_install` relayed the 0.6 GB package through
  the operator's Mac with `scp -3`: 297 of 592 MB in 900 s (**0.33 MB/s**) before the timeout,
  and the same-host lane stalled at zero bytes, because Windows OpenSSH carries no bulk between
  two Windows hosts (EXP-019). The package now copies locally on one host and otherwise travels
  as ranged HTTP served by the builder and fetched by the target: **104.7 MB/s**, 16 streams,
  SHA-256 verified on both ends and again by the installer. The staging root was created with
  `New-Item` under `ProgramData`, so on the host whose qualification parent did not exist yet
  it inherited `BUILTIN\Users` write access and the installer refused to create protected state
  beneath it; the candidate's own protection library now creates or checks the parent. The
  managed install passed its arguments as an array splat, which PowerShell binds positionally.
  And the lane's protocol probe sends the session credential on `X-NInfer-Session` alone and
  requires a header that disagrees with the body's `ninfer_session` to be refused: mainline
  applied the header only on the bodyless stored-response routes, so a header-scoped create was
  silently unscoped and the conflict returned 200. Both lanes now pass preflight, build, scan,
  package, and install, and reach `protocol`.
  Sizing the RTX 4090 lane's pinned pools took its own measurement. The managed start failed
  `cudaMallocHost` twice while three hand-launched starts with identical arguments succeeded:
  the controller reads the 18 GB model artifact through the file cache immediately before
  launch, and sampling a failing start showed the free-and-zero list going 13.1 → 0.0 GB with
  standby reserve at 5.2 GB. Pinned demand is the dial that matters — 24 slots plus the 8 GiB
  default Host KV is 13.3 GB, 4 GiB is **9.2 GB** and starts — but the slot count is not
  available to trade: at 8 slots the protocol's post-delete continuation fails in 41 s with a
  500 from a `std::logic_error`, because admission planned reuse from a catalogued continuation
  whose last state replica had been evicted. That invariant defect is open and capacity-
  triggered; both lanes carry 24 slots, and only the RTX 4090 lane's pool was halved. The
  RTX 3090 lane is blocked on its host, which went offline mid-window.
  Receipt: [qualification window](measurements/2026-09-09-native-lane-qualification-blockers.json).
- **EXP-054 — where a decode round goes (2026-09-25).** Production decodes at 58.5 rounds/s,
  17.1 ms per round, with 99.4% of decode time waiting on the device. A release-configured
  `ninfer_bench` whose 2,897 device functions are instruction-identical to production's
  `ninfer-serve` reproduced it: **17.23 ms** per round at a 26,000-token context and 15.62 ms at
  a seed context, against 18.78 ms eager, so CUDA graph decode already removes 1.55 ms of launch
  overhead and the GPU is busy 99.2% of a round. Nsight Systems graph-node traces, mapped to each
  kernel's weight bytes, put the W8 kernels at the floor (LM head, MTP layer and Q4 draft head
  at 97–104% of 1,674.5 GB/s) and the verify pass's Q4/Q5 projections below it: Q4 gate/up
  82.5% (4.39 ms per round), Q5 down 75.8% (2.95 ms), Q5 mixer outputs 68.0% (1.16 ms), GDN
  value/z 66.2% (1.79 ms), and the two small Q4 query/key projections 39.7% (GDN, 0.81 ms) and
  47.7% (attention). Bringing every mapped kernel to 90% of the floor recovers **2.6 ms per
  round (15.1%)**. The GDN input projection launches its 4,096-row Q4 query/key and 12,288-row
  Q5 value/z as two kernels over the same activations; one launch keeps each row's arithmetic
  and recovers about 0.8 ms at 85%. Tooling: the sm120 profiling image's `nsys` is Nsight
  Compute's target-only copy with no importer, so the earlier packet never produced a report.
  Receipt: [attribution](measurements/2026-09-25-decode-roofline-attribution.json).
- **EXP-055 — decode kernels (2026-09-25).** Nsight Compute on the EXP-054 kernels found the
  small-T projections issue-bound: widening each bf16 activation cost as much as its FMA, and the
  Q4 gate/up MMA stalled on 8-way shared-memory bank conflicts over unpadded 256-byte code rows.
  The runtime now runs its Q5 split4 (T=3–6), Q5 split2 (T=2–5) and Q4 query/key (T=2–4)
  projections two rows per warp (GDN query/key one row, with direct loads), so each activation
  load and widen serves both rows while every row keeps its FMA order, and it pads and
  double-buffers the Q4 gate/up staging. A private-launcher sweep against the production kernels
  found output bytes identical at all 32 kernel/extent points. On the packaged release build an
  A/B/B/A of `ninfer_bench` cut a 26K-context round from **17.75 to 16.08 ms** (+10.3% to +11.0%
  decode tok/s from a seed context to 31K), the 89-case role corpus answered identically and
  130,048-token retrieval stayed exact; the packaged binaries then passed the full RTX 5090 lane
  evidence set. The RTX 4090 disagreed: its canonical qualification passed, but C1 decode read
  149.38 tok/s against 153.33–153.56 for six earlier runtimes, and the card's op curves put the
  loss in the split2 row pair (MLP down +19% at T=4). The native lanes keep one row per warp for
  split2; requalified, the RTX 4090 decodes at **157.89 tok/s (+2.8%)**. At 90% of the floor,
  1.40 ms (8.7%) of the RTX 5090 round remains recoverable, led by MLP down, GDN query/key and
  attention decode. Receipt: [kernel schedules](measurements/2026-09-25-decode-kernel-schedules.json).
- **EXP-056 — the rest of the decode round (2026-09-25).** EXP-055 left 1.40 ms (8.7%) of the
  26K RTX 5090 round above 90% of the bandwidth floor. Nsight Compute put the attention partial
  at 255 registers per thread and 10.8% achieved occupancy on 0.76 waves, and the recurrent
  record on 0.32 waves. Private launchers of the production kernels then swept register
  double-buffering, L2 prefetch, exact dequantization and relaxed launch bounds for every T=4
  projection, warp splits and prefetch for the GDN record and fold, the attention CTA's warp
  count, and an L2 hand-off prefetch between kernels. All 1,631 rows per pass matched
  production's bytes. No projection or GDN record/fold schedule beat production at the
  production extent by more than its own run-to-run spread, and the hand-off prefetch only speeds
  a cold consumer: with its whole weight resident in L2 the mixer still takes 16.4 µs, and in the
  production graph it already runs in 16.6 µs, so the projections are issue-bound and prefetch
  has nothing left to hide. The attention CTA's warp count survived: two warps for the 27B's BF16
  attention at T=2–4 above the 16K split tier ran 6.2% faster in isolation at 26K. It failed
  requalification. The in-graph partial fell 6.1%, but decode moved only +0.3% to +0.9% from 26K
  to 60K, and the public op ran 3.7–5.4% slower between 16,387 and 20,000 keys, a band the decode
  graph routes with the envelope of its 16,385–32,762 bucket. Exclusive time also corrects the
  remainder: PDL lets GDN query/key overlap value/z by 4.4 µs per call, so the projections'
  recoverable share is **1.15 ms (7.2%)**, led by MLP down (0.36 ms), attention decode (0.30 ms),
  GDN value/z (0.15 ms) and the mixer (0.14 ms). Closing it needs a different accumulation order
  (a Q5 small-T tensor-core route), which changes output bits. Outside the projections, the traced
  round spends 0.47 ms in 297 small normalization and gating kernels, 0.17 ms in 815
  kernel-boundary gaps and 0.34 ms in host round trips around the verify result (profiled); those
  keep every byte but are fusion and serving-loop work. The harnesses ported to `sm_89` on the
  RTX 4090 (449 rows per pass, all byte-identical) found only one- and two-tick leads at the
  1.024 µs timer resolution, and reconfirmed that the split2 row pair slows MLP down 13.9% at T=4.
  Nothing ships. Receipt: [decode remainder](measurements/2026-09-25-decode-round-remainder.json).
- **EXP-057 — a tensor-core route for the Q5 verify projections (2026-09-26).** EXP-056 found
  no schedule that keeps production's bytes and recovers the T=4 projections' share of the round.
  A small-T MMA for the Q5 projections, built like the Q4 gate/up MMA (16-row CTAs, per-warp K
  groups, 5-bit codes widened to exact bf16 integers, fp16 group scales applied in fp32), beat
  production in a cold-L2 harness at eight warps and three stages: MLP down −13.3%, attention
  gate/value −5.8%, GDN value/z and the mixer within 2%. Routed at T=4 on `sm_120` for all four
  projections, it passed the five public op tests and shortened the MTP3 round 4.4–5.4% at every
  measured context (A/B/B/A: 16.01 → 15.24 ms at 26K, 17.57 → 16.79 ms at 60K); decode rose
  5.05% at 26K and 4.64% at 60K, where MTP acceptance does not move, and 6.73% at 1,024. MLP
  down carries 0.40 ms of the 26K round, and the unchanged GDN query/key kernel loses 0.22 ms of
  exclusive time to overlap with the tensor-core value/z. The output bits move. In isolation 27
  of 118,784 outputs (0.023%) differ from production's, each by one bf16 ulp, and sit closer to
  an FP64 reference (max 0.50–0.60 ulp against production's 0.50–1.21). That is enough to change
  generated text: 58 of 89 role-corpus cases differ from `v0.8.1`, and a 16-warp, two-stage
  control of the same route differs from production in 54 and from the candidate in 59. With no
  prompt the candidate accepted fewer drafts on its own text (0.423 against 0.461), so decode
  there moved +0.1% on a 5.4% shorter round. Both samples' quality aggregates stay within the
  range of production and four earlier runs at other weight or KV precisions, with three
  exceptions: the candidate fails two more redaction controls than production (0.500 against a
  0.625 floor), each one that also fails under FP8 or INT8 KV; the control leaves one log-triage
  case unanswered after 3,957 reasoning tokens; and the candidate's evidence precision (0.994)
  is above the 0.979 ceiling. The candidate passed exact 130,048-token retrieval, decode_2048
  and the agent protocol. Production's automatic-use gate then failed both samples of the route
  on the redaction-control pass rate (more than 2.0 pp below production), so the owner set a
  rule before a paired screen: adopt the route only if its redaction behaviour was not worse.
  Every redaction control ran in eight whitespace variants on fresh production and candidate
  servers. A first run was invalid, because the server trims each message's outer whitespace
  and every variant rendered the same prompt; the counted run put the whitespace inside the user
  content. The candidate passed 30 of 56 samples against production's 32 (one-sided Fisher
  p = 0.42) but leaked 69 synthetic secrets against 61, which the rule forbade. EXP-057 is
  rejected: no `v0.8.2`, and production stays on `v0.8.1`. Varied prompts also put production's
  own redaction pass rate at 57% (32 of 56), against 75% in the single corpus run. Receipt:
  [Q5 tensor-core route](measurements/2026-09-26-q5-small-t-tensor-core.json).
- **EXP-058 — draft source and a launch chain for decode (2026-09-26).** After EXP-057's
  output-changing route failed the redaction rule, this experiment kept every output byte.
  Draft-source changes cannot change outputs, because the target verifies every draft: serving the
  full LM-head proposal head instead of `--lm-head-draft` left all 89 role-corpus cases identical
  to `v0.8.1` and raised acceptance from 3.336 to 3.397 tokens per round, but its larger GEMV made
  decode 9.2% slower (392.3 s against 359.3 s over 84 requests). Replayed offline with MTP
  modelled at production's per-position acceptance, prompt-lookup drafts at the same three-token
  window trail MTP on the role corpus (3.086 against 3.206 tokens per round) and gain 2.6% on
  coding-agent session outputs (2.782 against 2.711); longer lookup drafts reach +9.9% only by
  verifying 6.41 columns a round. Programmatic dependent launch (PDL) was the byte-identical lever
  left: each kernel waits for its predecessor, then releases the next launch. Chaining RMSNorm,
  the Q5 split2 projections and the Q4 small-T MMA made decode 4.7–6.2% slower (A/B/B/A), and the
  MLP down projection alone accounts for it: launched while the multi-wave gate/up projection
  drained, it ran 46.1 → 62.2 µs after release. Releasing early only from single-wave kernels
  (norms, gating, conv, recurrent record, RoPE, small-T attention), keeping the projections
  wait-only and the GDN pair as production, and extending the chain across the round removed the
  regression and passed 24 oracle tests with identical speculative statistics, but moved decode
  only +0.13% to +0.45%, inside the window's drift. In the CUDA graph the 815 kernel boundaries
  per round already cost 0.21 µs each (169.5 µs of a 16.6 ms round). The idle time that remains is
  the round boundary: 476–494 µs per round from the verify pass's device-to-host copy to the next
  pass's first kernel, of which 174 µs is the replay fold and 235–239 µs is `cudaGraphLaunch`'s
  CPU time on this WSL2 appliance. Overlapping the fold with the next launch needs the host to
  stop waiting for it, but the state-pressure demotion copies continuation state to host on the
  transfer stream with no compute-stream fence of its own, so that is an engine contract change.
  EXP-058 is rejected: no `v0.8.2`, and production stays on `v0.8.1`. Receipt: [draft source and
  launch chain](measurements/2026-09-26-decode-draft-source-and-launch-chain.json).
- **EXP-059 — where prefill time goes (2026-09-26).** Prefill is 37.8% of agent GPU time on the
  RTX 5090 (446 v0.7.0 agent requests), in two regimes. Cold starts of 16K or more computed tokens
  are 27 requests but 64% of it. They run at 74% of their dense BF16 FLOP floor (209.5 TFLOPS with
  FP32 accumulate, the only BF16 MMA mode on this card), both in a 26K production-kernel trace and
  in production's served 28.9K request: the MLP gate/up and Q5 down/mixer GEMMs at 81–82% of peak,
  the GDN input at 76%, attention at 70%, and only the attention input projection lower, at 51% on
  32x64 tiles (6.4% of busy time). Warm turns are 411 requests with a median of 421 computed
  tokens on a 24.8K-token context and a 0.273 s TTFT. Two probe windows served production's image
  and binary under Nsight Systems and replayed agent-shaped turns on a 29K context. A turn that
  returns the full previous assistant message, as an agent client does, took 283–307 ms of GPU for
  about 400 computed tokens in six separate full-model passes: the chat template marks
  rewrite-execution boundaries after each assistant opener and think line so that resumed and root
  execution split the same way, and each boundary ends a pass. The four 2–3-token fragments ran on
  the small-T routes in 59–60 ms. The reasoning block (33–66 tokens) and the body plus new
  messages (340–351 tokens) each paid about 27 ms of prompt attention: every 64-row query tile
  scans the whole context on one SM at 91–95% of that SM's rated peak, and a pass this small fills
  24–144 of 170 SMs. Their projections took 155–178 ms against an 89–94 ms FLOP floor, the
  reasoning-block pass at 20–25% of peak. No large lever keeps output bytes. Running one request's
  consecutive fragments through each layer together, each with its own projection route and GDN
  decomposition, would merge their prompt attention into one launch and save about 27 ms per extra
  prompt pass; keys are tiled from absolute position 0, so each row's arithmetic should not
  change, which is unproven. Folding the passes (six to two between captures, an estimated 115–130
  ms of a 307 ms turn) changes bytes: the boundaries keep resumed and cold execution
  bit-identical, and no projection route promises rows that do not depend on pass width. The
  chunked small-T attention route, which would take a 7–16-token pass from about 27 ms of
  attention to a few, is enabled only for 16-head geometry. FP8 or NVFP4 projections remain the
  only large cold lever. The shared-stable-prefix turns (26% of warm turns, 0.314 s median for 140
  computed tokens) were not traced. EXP-059 is open and changed nothing. Receipt: [prefill
  attribution](measurements/2026-09-26-prefill-attribution.json).
- **EXP-060 — new sessions wait on the GPU's idle state (2026-09-26).** EXP-059 left the
  shared-stable-prefix warm turns untraced: production's new agent sessions took 0.315 s of
  prefill for 140 computed tokens. They start on an idle GPU. In the v0.7.0 agent traffic, 103 of
  106 new sessions and 138 of 446 agent requests arrived 5 s or more after the previous request
  finished. New sessions arriving that late took 0.317 s of prefill (TTFT 0.361 s); the three that
  arrived sooner took 0.171 s (TTFT 0.199 s). After the last response the RTX 5090 steps from P1
  to P3 at about 2.0 s, to P5 at about 7.4 s and to P8 (270 MHz SM, 405 MHz memory) at about 9.2
  s. Three probe windows served production's image and binary under Nsight Systems with a
  30.2K-token shared prefix. New sessions of 159–230 computed tokens sent back to back prefilled
  in 0.156–0.160 s: about 5–15 ms of state bookkeeping, one 123–127 ms prompt pass and two small-T
  fragments. Sent after 12–30 s idle, the same sessions took 0.253–0.334 s (TTFT 0.317–0.393 s):
  the prompt pass ran 205–287 ms with every kernel family slower, while the fragments after it ran
  at normal speed once the clocks had ramped. A side process launching a 0.4 ms kernel every
  second changed neither the P-state steps nor the slowdown. The lever keeps output bytes, since
  clock state does not change arithmetic: a GPU held out of its low idle states when a request
  arrives would bring new-session TTFT from about 0.36 s to about 0.19 s. Neither route was tried:
  a host clock floor (locked clocks on the Windows host, a global setting with an idle-power cost)
  or a keep-warm load for a grace period after each request, which needs more than the 1 Hz
  kernel. EXP-060 is open and changed nothing. Receipt: [idle GPU and new
  sessions](measurements/2026-09-26-idle-gpu-new-sessions.json).
- **EXP-061 — the lightest keep-warm load (2026-09-26).** EXP-060 found new agent sessions waiting
  on the RTX 5090's idle P-states. Two sweeps ran keep-warm loads alone on the card, with
  production held, each for 30 s after a 3 s full-GPU burst. A single-warp kernel spinning 30 ms
  of every 100 ms (30% GPU utilization) holds P1 with the memory clock at 13,801 MHz. At 25% the
  card reaches P8 after 13.7 s, and at 1–20% within 3.4–7.4 s. All-SM spins at 10–20% and
  device-to-device copies of 64–256 MiB every 20–100 ms do not hold it either. The 30% load drew
  87.3 W alone and 88.8–91.6 W beside production's binary served without Nsight Systems, against
  29.0 W idle in P8; 40% draws 117–118 W. Run as a grace period (resumed as each response
  returned, paused 0.1 s before the next request) it held P1 through 12 s and 60 s gaps. New
  sessions then prefilled in 0.155 s and 0.180 s (TTFT 0.173 s and 0.201 s), against 0.155–0.159 s
  back to back and 0.353 s (TTFT 0.417 s) for the same session after 30 s without it. That control
  gap also confirms EXP-060's step schedule without Nsight Systems: P3 at 1.9 s, P5 at 6.7 s and
  P8 at 8.5 s. The lever keeps output bytes. Its engineering form is an engine-side grace period:
  after a request completes, ninfer-serve runs a single-warp spin for 30–35 ms of every 100 ms on
  its own stream until the grace period ends or a request is admitted. A side process would
  contend with requests for the GPU. It costs about 60 W above idle while held, about 1 Wh per
  minute of grace. EXP-061 is open and changed nothing. Receipt: [keep-warm
  load](measurements/2026-09-26-keep-warm-load.json).
- **EXP-062 — the engine keep-warm prototype (2026-09-26).** A local runtime branch builds
  EXP-061's lever into ninfer-serve as `--gpu-keep-warm-ms N`, off by default. Once the Engine
  worker has run work and nothing is pending, materializing or active, it launches a single-warp
  kernel that spins 3.5 ms of every 10 ms on its own non-blocking stream. It stops when a request
  is pending, the Engine stops, or N ms pass, and nothing on the request path waits for it. Two
  windows served the candidate in production's image with production's arguments. With a 30 s
  grace, new sessions after 12 s and 25 s idle prefilled in 0.155 s (TTFT 0.174 s and 0.176 s).
  With the flag at 0 they took 0.278 s and 0.304 s (TTFT 0.337 s and 0.366 s). With a 60 s grace,
  sessions after 38, 53 and 58 s idle prefilled in 0.155–0.157 s (TTFT 0.173–0.181 s), the same
  as back to back (0.156–0.160 s). Holds up to 58 s did not slow the next session, as EXP-061's
  side-process load had after 60 s. The card held P1 (SM about 2,680 MHz, memory 13,801 MHz) at
  99.5–102.7 W, against 29.3–29.8 W idle in P8, about 71 W more. When the 30 s grace ended it
  reached P8 2.9 s later, and a session at 45 s was cold again (0.352 s). All 89 role-corpus cases
  were byte-identical to v0.8.1 with the flag on and at 0. The 80 corpus requests that arrived
  1–5 ms after the previous response, while a spin could still be running, lost nothing
  measurable: paired TTFT median −0.1 ms, worst +4.4 ms. In production's v0.7.0 traffic, agent
  requests that arrived after 5 s or more of idle had waited a median 52.7 s. A 30 s grace would
  have caught 11 of those 138; 60 s would have caught 84 (74 of 103 new sessions), holding the card
  for 3.2% of the logged 62 h, about 2.3 W on average. The measured build is `c6bd1674`; `0e996b3d`
  adds a guard that skips a launch while the previous spin still runs, and `32c21f73` a device test
  that fails without it. `32c21f73` shipped in v0.8.2 as runtime `v0.6.11-qwen38-5090-beta.1`, with
  `--gpu-keep-warm-ms 60000` in the RTX 5090 profile; its published image passed the lane's full
  evidence set and the four documented routes, and production has run it since 2026-09-26.
  Receipt: [engine keep-warm](measurements/2026-09-26-engine-keep-warm.json); release:
  [v0.8.2 lane receipt](../releases/v0.8.2/qualification/rtx5090.json).
- **EXP-063 — a redaction screen that can say "not worse" (2026-09-27).** EXP-057's route failed
  the owner's rule on a 56-sample screen whose leak rule was a point estimate: candidate total at
  most production's, which an equivalent route fails about half the time. EXP-063 keeps the rule
  and gives it power. [`scripts/redaction_screen.py`](../scripts/redaction_screen.py) writes every
  redaction control in 72 whitespace variants (v0-v7 are EXP-057's prompts) and decides by a rule
  committed before any candidate data (`554ac56`, 04:12Z; the candidate arm began 05:24Z): pass
  only if the one-sided 95% upper bound of the candidate's leak total over production's is below
  1.10 and the lower bound of the paired pass-rate difference is above −5 pp, both from a paired
  bootstrap within controls. It is invalid if a counted prompt is missing, errors exceed 1%, fewer
  than half the controls change output across variants, or either arm's determinism re-run
  differs. The route was rebased onto v0.8.2's source as `9d1ef748` and built as the v0.6.12
  release package. Its eight Q4/Q5 op tests passed, and its 89 role-corpus outputs equal EXP-057's
  candidate's (58 differ from production's). The screen served 576 prompts per arm on fresh
  servers with production v0.8.2's image and arguments; 504 counted pairs, no errors, all seven
  counted controls changed output across variants, and both arms reproduced their 14 determinism
  prompts. The candidate leaked 561 secrets against 582, fewer in four controls and as many in
  three, and passed 53.2% against 52.6%; the bounds were 1.012 and −1.2 pp. On v0-v7 both arms
  matched EXP-057's outputs on all 64 prompts, so EXP-057's +8 leak excess sits inside this sample.
  The candidate then passed the profile gates: exact 130,048-token retrieval in 59.2 s, decode_2048
  at 168.81 tok/s, and the agent protocol. Release build against release build, A/B/B/A, the MTP3
  round was 4.2% shorter at 26K and 3.5% at 60K, and decode rose 4.4% and 3.6% there, where MTP
  acceptance does not move; with no prompt the candidate accepted fewer drafts on its own text
  (0.423 against 0.461), so decode moved −0.5% on a 4.9% shorter round. Two controls fail in
  every sample in both arms and carry 465 of production's 582 leaks, and the screen bounds the
  route on these seven controls, not on redaction in general. `9d1ef748` shipped in v0.8.3 as
  runtime `v0.6.12-qwen38-5090-beta.1` on the unchanged deployment profile `qwen38-5090-v0.8.2`;
  its published image passed the lane's full evidence set and the four documented routes, and
  production has run it since 2026-09-27. Receipt:
  [powered redaction screen](measurements/2026-09-27-powered-redaction-screen.json); release:
  [v0.8.3 lane receipt](../releases/v0.8.3/qualification/rtx5090.json).
- **EXP-064 — the RTX 4090 waits on its idle state too (2026-09-27).** The RTX 4090 native lane
  had never been measured idle. After its last response the card steps P2 → P3 at about 2.3 s, P5
  at 3.3-4.3 s and P8 (210 MHz SM, 405 MHz memory) at 5.4-6.2 s. A rule committed before either
  arm ran compared one `sm_89` build of the v0.8.3 source with and without
  `--gpu-keep-warm-ms 60000`, each serving a 15K-token stable prefix and 30 new sessions of about
  100 computed tokens after gaps of 0-58 s. Without keep-warm every session after 12-58 s idle
  started in P8 and prefilled in 0.29-0.47 s against 0.146 s back to back (medians +225 to +288
  ms). With it the RTX 5090's spin ran, 3.5 ms of every 10 ms at 34.9% measured utilization, but
  the card still reached P8 about 9.5 s after the last response, and every session after a gap
  again started in P8. Outputs were byte-identical between the arms, so by the rule the RTX 4090
  would ship 0. A sweep after the rule decided found that a single-warp spin of 40 ms or more every
  100 ms held P2 at 73-79 W (4.5 W idle), while spins of 3.5-6 ms every 10 ms never did, even at
  60% nominal duty: on this card the pattern's period matters, not only its utilization. The same
  window reproduced #48's memory state (3.5 GiB free, 22.6 GiB standby) and the published v0.6.8
  package started and pinned its 11 GiB host-KV pool. Receipt:
  [RTX 4090 keep-warm](measurements/2026-09-27-rtx4090-engine-keep-warm.json).
- **EXP-066 — a long spin holds the RTX 4090 (2026-09-27).** EXP-064's sweep chose the pattern;
  a new rule, committed before either arm ran, judged it inside the engine. `7fa2f80a` makes the
  `sm_89` build spin 50 ms of every 100 ms and leaves every other architecture on the RTX 5090's
  pattern. With `--gpu-keep-warm-ms 60000` the card held P2 through every gap of up to 58 s at
  77.5 W, about 72 W above idle, and all 15 sessions after 12-58 s idle prefilled in 0.146-0.148 s
  (TTFT 0.167-0.178 s), the same as back to back; without it they took 0.26-0.43 s. All 31 outputs
  matched between the arms and EXP-064's run of the v0.8.3 source. The RTX 4090 lane's
  `v0.6.9-qwen38-4090-beta.1` from `5ac17674` sets `engine.gpu_keep_warm_ms` to 60000. Receipt:
  [RTX 4090 long spin](measurements/2026-09-27-rtx4090-keep-warm-long-spin.json).
- **EXP-065 — upstream still does not earn a merge (2026-09-27).** Upstream engine
  `e31bc99b` was measured against the shipped RTX 5090 runtime. Its 1.5% single-run prefill
  lead was already present in EXP-048; decode was about 18% slower and fanout reuse was
  0/4 versus 4/4. The merge stays deferred. Receipt:
  [upstream versus shipped](measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json).
- **EXP-069 — the RTX 4090 keeps its SIMT Q5 route (2026-09-28).** The pre-registered rule
  required at least 2.0% decode gain at 26K tokens and 1.0% at 60K before adopting the small-T
  tensor-core route on `sm_89`. Measured gains were only 0.38% and 0.40%; the rule rejected
  it. The published v0.6.9 package is unchanged. Receipt:
  [RTX 4090 Q5 small-T MMA](measurements/2026-09-28-rtx4090-q5-small-t-mma.json).
- **EXP-077 — two requests in flight on the RTX 5090 (2026-09-29).** With `--max-concurrency 2`
  the published v0.6.13 image fits two requests (KV auto-resolves to 160,256 tokens; 30,244 MiB of
  32,607) and keeps fanout reuse and a graceful restart with two sessions decoding, but two decodes
  together reached only 1.14× one at a time. Nsight Systems placed the gap in the verify pass: with
  two requests it carries eight tokens, and the Q5 projections fell off the four-token small-T MMA
  onto SIMT kernels (12.8 ms of a 23.9 ms round, against 5.2 ms). `e20060b6` templates that MMA on
  eight tokens: the pair decodes at 281.1-283.0 tok/s, and outputs match one-at-a-time wherever
  the prompt and reuse path match. The server's default 30 s pending timeout expired a request
  queued behind a running one; 180 s keeps the wait plus the longest root prefill inside OMP
  18.4.0's 300 s stream watchdog. Stock OMP at limit 2 overlapped a parent's two scout subagents
  for 15.7-17.7 s, but the turn took 25.2 and 23.9 s against 32.7 and 22.6 s at limit 1 in two
  windows, following what the subagents generated, and two short sessions started together
  finished later at limit 2 both times. On the final profile the v0.8.7 lane set passed: role
  corpus, profile gates, stock OMP durable sessions, long sessions, reclamation, workload and
  resume, barrier (whose deferred save did not arise at two requests), probes and agent mix; the
  third window's run ended when the appliance's C: drive filled and its WSL disk went read-only,
  and a fourth finished it. The published v0.6.14 image then passed the role corpus and profile
  gates (130,048 tokens exact in 58.4 s, 169.79 tok/s). Receipt:
  [two requests in flight](measurements/2026-09-29-rtx5090-two-requests-in-flight.json).
- **EXP-078 — DFlash2 earns a port (2026-09-30).** Upstream `d44ab584` served the published v3
  artifact, whose DFlash2 companion is Z-Lab's five-layer block drafter, in two arms that differ
  only in the speculative backend: MTP3, and DFlash2 drafting seven tokens in one masked-block
  pass, both at one request with BF16 KV and 131,072-token context. DFlash2 decoded the 84
  runnable role-corpus cases at 253.63 against 197.80 tok/s (+28.2%, every case faster): 4.631
  against 3.332 tokens per round, with rounds 8.4% longer. A 2,048-token code answer gained
  27.0%, 20.8% and 56.4% behind 32K, 64K and 120K tokens of unrelated context, and 45.9% on a
  continuation that reused 64,222 cached tokens; prefill did not move. It costs 1.65 GiB of
  weights. At two requests the four extra device state slots no longer fit (343 MiB short); two
  slots leave 131,520 KV tokens for both requests against MTP3's 160,256, and a pair reached
  453.95 against 374.94 tok/s. Outputs change (34 of 84 answers identical between the arms), so
  adoption needs its own quality screen. The pre-registered rule said go: the next engine
  campaign ports DFlash2 onto the fork's durable runtime. Receipt:
  [DFlash2 on the RTX 5090](measurements/2026-09-30-dflash2-rtx5090.json).
- **EXP-079 — the fork port drafts like upstream but slows with context (2026-09-30).** A spike
  branch cherry-picked 51 of upstream's 79 DFlash2 commits onto the shipped runtime's source
  (`e20060b6`), hand-ported the pieces that would have changed the target path (FP16 V only in
  the draft's cyclic cache; target V stays BF16), and served the v2 DFlash2 artifact: the pinned
  `eec39564` tensors plus 66 `dflash2/*` ones. MTP3 on that binary answered all 89 role-corpus
  cases byte-identically to shipped v0.9.0 and v0.8.7. DFlash2 K=7 drafted as well as upstream's
  (4.596 tokens per round on the corpus against 4.631) and decoded a code answer with no context
  at 355.15 tok/s, 10.6% above upstream's DFlash2 and 41.7% above shipped. Its round cost grows
  with context, though: 16.2, 45.6, 75.0 and 126.3 ms behind 0, 32K, 64K and 120K tokens (about
  16 ms plus 0.92 ms per thousand tokens), against 17.7 to 23.0 ms on upstream. Behind 120K tokens
  the answer decoded at 44.54 tok/s against shipped 180.11, and the corpus came out 3.6% below
  shipped (228.90 tok/s): its long-prompt cases lost more than its 61 faster cases gained. The
  pre-registered rule said no-go. Two candidates fit, neither measured: the fork's target
  attention for one request's 8-token verify, a shape the fork had not run at long context (MTP3
  verifies 4 tokens; EXP-077's 8-row rounds were two 4-token requests), or a draft-side operation
  that scales with the prefix instead of the 2,048-token draft window. A kernel timeline of one
  round at 64K comes next. The port's GPU tests passed except `kv_cache_append`, whose cyclic
  fixtures fed BF16 NaN patterns that the host oracle and the device convert differently; the
  branch now feeds finite values, as upstream does. Receipt:
  [DFlash2 fork spike](measurements/2026-09-30-dflash2-fork-spike-rtx5090.json).
- **EXP-080 — under DFlash2, the KV format is the capacity lever (2026-09-30, #71).** Asked
  whether NVFP4 KV had been tried, #71 expected little: BF16 KV already fits 131,072 tokens, and
  NVFP4 KV stores 4-bit values without making attention 4-bit. That holds under MTP3. Under
  DFlash2, 1.65 GiB of drafter weights cost the two-request profile two device state slots and
  28,736 KV tokens (EXP-078). On the same upstream binary and artifact, `--kv-dtype nvfp4` and
  `--kv-dtype k8v4` both started two requests with all four slots and resolved 262,144 KV tokens:
  two full 131,072-token contexts, against 160,256 on shipped v0.9.0. At one request the KV
  payload shrank from 8.00 GiB to 2.25 (NVFP4) and 3.14 (K8V4), and the formats cost nothing
  measurable. Role-corpus decode was 256.48 and 253.12 against 253.63 tok/s, and decode rounds
  were shorter behind long context (21.2 and 20.4 ms against 23.0 ms at 120K). NVFP4 prefill was
  within 1.5%, and K8V4 prefill ran 15.3% faster at 120K. The one role-corpus screen per format
  kept both inside the pre-registered bounds: evidence precision 0.979 against 0.993, unsupported
  claims 0.225 and 0.214 against 0.225, secret leaks 9 and 7 against 10. Outputs diverge early
  under lossy KV (12 and 19 of 89 identical), so those counts rest on a few cases each. By rule,
  NVFP4 is kept as a profile candidate. K8V4 is inconclusive: its answer behind 120K tokens drafted
  4.82 tokens per round against 5.63 and decoded 3.55% slower, past the 3% bound, although its
  rounds were faster. Neither format exists on the fork, whose durable checkpoints store raw KV
  pages, so adopting one is a profile advance with its own checkpoint format. NVFP4 therefore joins
  the DFlash2 port campaign as its two-request capacity plan, gated on a powered quality screen.
  Receipt:
  [KV formats under DFlash2](measurements/2026-09-30-kv-nvfp4-k8v4-rtx5090.json).
- **EXP-081 — the context cost was the verify's attention route (2026-09-30).** The 27B's full
  attention has 24 query and 4 KV heads. EXP-079's port resolved one request's 7- or 8-column
  call on that geometry to the Prompt kernel, which runs one CTA per query head per 64 query rows
  and does not split the KV sequence, so each of the 16 full-attention layers paid a cost that
  grew with context. MTP3 never issues that call: it verifies 4 tokens per request. Upstream
  routes it through ChunkedSmallT above 320 visible keys (`4b0eb36c`), a commit the port had
  skipped as 35B retuning; the 35B-A3B has 16 query heads. With that one commit added and nothing
  else changed, the DFlash2 round's slope fell from 0.917 to 0.085 ms per thousand context
  tokens, against upstream's 0.044. DFlash2 K=7 decoded the role corpus at 288.09 tok/s: 21.4%
  above shipped v0.9.0, 25.9% above EXP-079's port and 13.6% above upstream's DFlash2, with 83
  of 84 cases faster than shipped. Behind 0, 32K, 64K and 120K tokens a code answer decoded
  46.7%, 31.9%, 37.0% and 23.8% faster than shipped; prefill was unchanged. MTP3 on the same
  binary stayed 89/89 byte-identical to shipped, and DFlash2's answers matched shipped MTP3 on 86
  of 89 cases where EXP-079's port matched 41, so most of that divergence was the Prompt route's
  arithmetic. The pre-registered rule said go. Two requests in flight did not move: a pair
  decoded 269.17 tok/s together, against shipped 388.42 and upstream DFlash2's 453.95, in 37.1 ms
  rounds against upstream's 22.0-22.4 ms. Read from source, the two-request verify is 16 columns
  wide and the fork's Q5 tensor-core route covers only 4 and 8, so the MLP-down, GDN value/z and
  attention gate/value projections fall back to SIMT; upstream's 16-column routes come next, then
  the durable context ring. The window's driver ran on the appliance itself, so the operator's
  in-flight link could drop without stopping a step. Receipt:
  [DFlash2 verify route](measurements/2026-09-30-dflash2-verify-route-rtx5090.json).
- **EXP-082 — two requests' verify was off the tensor cores (2026-10-01).** With two requests in
  flight, DFlash2 K=7 verifies 16 columns per round. The fork's Q5 small-T tensor-core route,
  added for MTP3's 4-column verify (EXP-057) and two requests' 8 columns (EXP-077), accepted only
  4 and 8, so a two-request round ran the MLP-down, GDN value/z and attention gate/value Q5
  projections on SIMT row kernels while a one-request round kept them on the tensor cores:
  EXP-077's cliff again, one width up. The kernel now takes 16 columns with a second m16n8k16 MMA
  per k16 step and two pipeline stages, and the three call sites route 16 columns to it. Each
  column's arithmetic is unchanged, so a 16-column pass computes every column as an 8-column pass
  over the same tokens would. A pair of requests then decoded 420.86 tok/s together in 22.7 ms
  rounds, against 269.17 tok/s in 37.1 ms rounds before, upstream DFlash2's 453.95 in 22.0-22.4
  ms and shipped MTP3's 388.42: 97% of the round gap to upstream closed, and the pair now beats
  shipped by 8.4%. The rest of upstream's lead is drafting on different outputs (5.02-5.10 tokens
  per round against 5.22-5.63). MTP3 on the binary stayed 89/89 byte-identical to shipped, and
  every op test with 16-column cases and the DFlash2 real-model test at one and two requests
  passed. The pre-registered rule said keep. Durability, NVFP4 KV capacity and a powered quality
  screen remain before a profile. Receipt:
  [DFlash2 pair on the tensor cores](measurements/2026-10-01-dflash2-pair-q5-tensor-cores-rtx5090.json).
- **EXP-083 — DFlash2 sessions keep the durable store (2026-10-01).** Every shipped RTX 5090
  profile since v0.4.0 keeps sessions across restarts, and the DFlash2 spike refused
  `--session-checkpoint-dir`. The draft context ring turned out to need no new payload: each
  DFlash2 StateImage already held the five-layer, 2,048-position draft K/V (40 MiB), and every
  path that moves StateImages copies whole images. What blocked it was the export and import
  treating "speculation enabled" as "a paged backend-KV file exists", which DFlash2 has none of.
  Spike `03212c9d` keys that file on the paged backend cache, refuses an export whose ring lags
  the continuation's frontier, and accepts DFlash2 import metadata only with the ring at the
  frontier. A new real-model test exports a 3.3K-token session from one engine, restores it into
  a fresh one and requires the next turn to match the exporting engine's: it did, in 96 tokens,
  13 rounds and per-position acceptance (82 of 89 drafts), and a throwaway copy that zeroed the
  ring before the restore drafted 14 rounds with 81 of 95 accepted, so the test sees a lost ring.
  At serve level, a 57,889-token session restored hot after each of two container restarts
  (52 and 260 tokens computed), quoted three planted keys exactly and drafted 5.47 and 6.67
  tokens per round against 5.10 in process; its checkpoint was 4.41 GB, saved in 3.29 s, against
  4.51 GB for shipped MTP3's checkpoint of the same template. No export was refused, no request
  failed, and MTP3 on the binary stayed 89/89 byte-identical to shipped. The pre-registered rule
  said reject on one criterion: the multi-session probe lost reuse on 2 of 12 continuations
  against a bar of zero that had been set without the incumbent's value. On the identical
  sequence shipped v0.9.0 lost the same two steps, continuations of an older turn evicted under
  catalog pressure; the one difference was a 140-token sibling that DFlash2 re-prefilled while
  its planner was under device-state pressure with two extra slots, where shipped's four served
  it from a 61-token anchor. The ring is kept; the two-slot pressure joins the NVFP4 step, which
  restores four slots. Receipt:
  [DFlash2 durable store](measurements/2026-10-01-dflash2-durable-store-rtx5090.json).
- **EXP-084 — NVFP4 KV gives DFlash2 the shipped profile's slots (2026-10-01).** With BF16 KV
  the two-request DFlash2 profile had two device state slots and 131,520 KV tokens, and EXP-083
  caught its planner re-prefilling a sibling under that pressure. Spike `008a7781` ports
  upstream's NVFP4-G16 paged KV as final files from `d44ab584`: four byte planes per layer (E2M1
  codes and E4M3 group-16 scales for K and V, Hadamard-rotated), its append, and its Grouped,
  ParallelGrouped and Tiled causal attention. A storage identity rides planning, views, workspace
  sizing, graph captures and checkpoints, and NVFP4 dispatches before the fork's legacy router,
  whose kernels and route resolver are byte-identical. At two requests the profile started with
  four slots and 262,144 KV tokens in 4.50 GiB of KV, against 131,520 in 8.03 GiB with BF16,
  and left 5.07 GiB free after startup. Verify rounds cost the same as BF16 at short context and
  in the pair, and 12%, 19% and 27% less behind 32K, 64K and 120K tokens, because each round
  reads 3.6 times fewer KV bytes. EXP-083's durable sequence passed with shipped v0.9.0's reuse:
  hot restores after two restarts from a 1.66 GB checkpoint (BF16 DFlash2: 4.41 GB), the
  sibling EXP-083 re-prefilled served from its anchor, and no multi-session reuse lost (shipped:
  2 of 12). MTP3 stayed 89/89 byte-identical. In the first window the attention tests aborted on
  a ported test that asked the workspace API for two-request intervals wider than the 16 columns
  batched verify carries; after a test-only fix every NVFP4 and legacy attention case passed in
  a second window. One unpowered role-corpus run of the profile decoded 24.0% faster than MTP3
  and scored evidence precision 0.951 against 0.994, so a powered quality screen comes next.
  Receipt: [DFlash2 NVFP4 KV](measurements/2026-10-01-dflash2-nvfp4-kv-rtx5090.json).
- **EXP-085 — DFlash2 keeps shipped quality; NVFP4 KV does not (2026-10-01).** A single
  role-corpus run cannot judge a candidate that rewrites most outputs, so
  [`scripts/quality_screen.py`](../scripts/quality_screen.py) extends EXP-063's redaction screen
  to every primary metric of the automatic-use gate. Every counted case runs in eight whitespace
  variants and every redaction control in EXP-063's 72, on fresh servers, and pairs prompt by
  prompt. The rule was committed before any data: one-sided 95% bounds of a paired bootstrap
  within each case, 2.0-point margins (3.0 for unsupported claims, EXP-063's for redaction).
  Shipped v0.9.0 MTP3 ran first. The DFlash2 NVFP4 profile changed 1,029 of 1,120 outputs and
  failed: evidence precision held (-0.3 points, lower bound -1.2, so the single run's -4.3 was
  prompt noise) and critical misses fell from 79 to 63, but unsupported claims rose 1.8 points
  (upper bound 3.7) and secret leaks went from 561 to 609 (upper bound 1.141 against 1.10).
  Because it failed, the same binary with BF16 KV ran under the same rule and passed with every
  bound inside, because it barely changed anything: 1,091 of 1,120 outputs were byte-identical to
  shipped MTP3's, the 29 others long log-triage and work-log answers. Speculative decoding
  verifies every draft against the same BF16 target, so DFlash2 alone is close to
  output-preserving; NVFP4 changes the target's attention. Every arm reproduced its first 80
  prompts exactly on a fresh server, and both DFlash2 arms decoded about 17% faster than MTP3
  over the screen. BF16 DFlash2 clears the quality step with two device state slots and 131,520
  KV tokens; restoring the slots now needs a KV format that keeps quality. Receipt:
  [powered quality screen](measurements/2026-10-01-dflash2-powered-quality-screen-rtx5090.json).
- **EXP-087 — FP8 KV earns a screen (2026-10-01).** The fork already carries FP8 E4M3 row-256
  KV: one byte per element plus an FP16 scale per 256-element row, half BF16's bytes with far
  less error than NVFP4's 4-bit codes. With `--kv-dtype fp8` the two-request DFlash2
  profile started with four device state slots and 249,216 KV tokens, where BF16 has two slots
  and 131,520, with the same 1.91 GiB free after startup. Rounds matched BF16 at short context
  and in the pair and were 7%, 12% and 18% shorter behind 32K, 64K and 120K tokens, about two
  thirds of NVFP4's gain. The 130,048-token retrieval stayed exact, the agent protocol passed
  with a restart, and the role corpus had no errors beyond the five vacuous cases; 27 of its 89
  outputs matched shipped's, and its one unpowered run scored at or above MTP3's aggregates.
  Every pre-registered criterion held, so FP8 runs the powered screen's candidate arm against
  EXP-085's production arm. Receipt:
  [FP8 KV pre-check](measurements/2026-10-01-dflash2-fp8-kv-precheck-rtx5090.json).
- **EXP-088 — FP8 KV fails on secret leaks (2026-10-01).** FP8's candidate arm ran EXP-085's
  1,120 prompts under the unchanged rule against EXP-085's production runs, registered before its
  data. It changed 924 outputs and sat inside every margin but one: recall, evidence precision,
  redaction pass rate and unsupported claims (+1.2 points, upper bound 2.8 against 3.0) held,
  but secret leaks went from 561 to 604, a ratio of 1.077 whose upper bound, 1.135, is above
  1.10. Both quantized formats moved leaks the same way (NVFP4 +8.6%, FP8 +7.7%), concentrated
  in the two log controls that fail in most samples and in repo-029, while BF16 DFlash2 left
  them at exactly 561. DFlash2 with BF16 KV remains the only quality-cleared DFlash2 profile, at
  two device state slots and 131,520 KV tokens. Receipt:
  [FP8 KV quality screen](measurements/2026-10-01-dflash2-fp8-kv-quality-screen-rtx5090.json).
- **EXP-086 — the adopted profile passes v0.9.0's probes, at a reasoning-decode cost (2026-10-01).**
  The founder chose to adopt DFlash2 with BF16 KV after EXP-088. Its two-request profile with the
  durable store passed every probe v0.9.0 qualified with. The rule as written still failed, on a
  clause v0.9.0 fails too: the concurrency matrix's stop refused 6 saves, and v0.9.0's refused 7.
  The probes exposed two costs the role corpus hides. On free-form reasoning text DFlash2 drafts
  2.46-2.65 tokens per round against MTP3's 2.27-2.39, while a two-request round costs 23.1 ms
  against 15.6 ms, so two requests decode 21-27% slower together and one 2-5% slower. And after a
  graceful restart one of two stored sessions re-prefilled from root, where v0.9.0 restored both.
  The release candidate's window repeats that restart three times. Receipt:
  [pre-acceptance probes](measurements/2026-10-01-dflash2-pre-acceptance-probes-rtx5090.json).
- **EXP-089 — DFlash2 does not port to the 24 GB lanes as written (2026-10-01).** Built for sm_89
  and sm_86 on the RTX 4090 host, the port fails at device link: two DFlash2 W8 SwiGLU schedules and the W8
  small-T projection under the dynamic grouped convolution each declare 49,664-50,176 bytes of
  static shared memory, over those architectures' 49,152-byte limit. The founder asked whether a
  kernel port and fit measurement had a realistic path. They do not at the lanes' contract. The
  RTX 4090's MTP3 profile already uses its memory with zero headroom: 5.82 GiB after weights for
  a 5.22 GiB runtime at 131,072 INT8 tokens. The drafter's 1.65 GiB would leave about 85K tokens
  [inference], and 131,072 would then need a smaller KV format or a smaller drafter. Receipt:
  [native lanes](measurements/2026-10-01-dflash2-native-lanes-feasibility.json).
- **EXP-090 — DFlash2 behaves like MTP3 under OMP's sampling; the proof misread codes
  (2026-10-01).** The second v0.10.0 candidate failed stock OMP's two-subagent proof at OMP's
  limit 1 in two of two runs, so both arms of the candidate binary ran the role corpus once at
  OMP's sampling and the proof ten times, recording every task tool outcome. A same-seed identity
  test was dropped before the window: the verifier accepts a draft with probability p(d) and
  otherwise samples the residual, which preserves the target distribution but ties each sampled
  token to the draft, so lossless arms still diverge. The corpus showed no gross change. The
  proof failed 2 of 10 runs on DFlash2 and 3 of 10 on MTP3. Three failures were the proof's code
  reader: scouts returned the exact code as JSON text after an escaped newline, whose `n` the
  code pattern's lookbehind read as a word character. One MTP3 parent's first task call named read
  and grep as eval tools, OMP refused it, and the parent reissued it. One DFlash2 run counted two
  requests at limit 1: OMP cancelled a background request, and the engine registered the cancel
  0.98 s after the request began, in the same millisecond it logged a stored session's checkpoint
  save before eviction.
  Receipt: [sampled behavior](measurements/2026-10-01-dflash2-sampled-behavior-rtx5090.json).
- **EXP-092 — the verify read its KV twice, and pairs left the tensor cores once more
  (2026-10-03).** v0.10.0's production log (338 agent requests since its cut) spends 85% of request
  wall time in decode, one request at a time, with 77% of decode seconds below 16K tokens; its
  largest prefills were probe traffic. A one-request 64K round of 21.3 ms spent 5.7 ms in the
  small-T attention partial: an 8-column verify ran as chunks of 6 and 2 columns, so each of the
  16 attention layers read its KV twice. One launch per layer now serves both chunks' rows, in one
  pass when their split partitions coincide and as the two old phases in sequence when they do
  not, and reduces each column over its old window, so every output is bitwise the two chunks'
  (46 boundary cases in the op test). In a pair, the 64 mixer-output LinearAdds at K=6144 still
  ran 16 columns on an 80-CTA prompt GEMM, 53.6 µs each; they now take the small-T tensor-core
  kernel that K=17408 already used, 22.1 µs. One A/B/B/A on the appliance: one-request rounds
  8.1%, 13.4% and 19.4% shorter at 32K, 64K and 120K and unchanged at short context, pair rounds
  8.1% shorter (424.2 → 454.3 tok/s), each within 0.3 ms of the prediction from source; both role
  corpora 89/89 byte-identical to shipped, DFlash2's at 293.0 against 288.1 tok/s. The
  pre-registered rule said keep both. The 64K attention now streams BF16 KV at about 1.4 TB/s
  [inference], so long contexts gain further only from fewer KV bytes, which FP8 and NVFP4 did not
  deliver at quality. The same windows rejected K=15 drafting: positions 8–15 are accepted in 20.5%
  down to 3.5% of rounds, but one request's 16-column verify costs 23.4 ms at short context and
  leaves the small-T attention route behind 32K, so the corpus decoded 188.5 tok/s against K=7's
  288.1. Receipt: [DFlash2 round costs](measurements/2026-10-03-dflash2-round-costs-rtx5090.json).
  **Shipped subset:** these are measurements of the experimental stack, not all of v0.11.0.
  Selected source `1302d639` contains the h24 BF16 verify change as `344850b3` and EXP-094, but
  does not contain `3a2fadbd` (the T=16 Q5 pair-mixer change). Git ancestry from `eaf221ac` to
  `1302d639` contains exactly `344850b3` and `1302d639`; the Q5 mixer directory is unchanged.
  The pair-mixer result remains experimental and must not be credited to the shipped runtime.
- **EXP-093 — no byte-identical schedule speeds the Q4 query/key projections (2026-10-03).** After
  EXP-092 the GDN and attention query/key projections are the furthest from bandwidth in every
  round: 1.68 ms at 28–31% of DRAM bandwidth, where the Q4 tensor-core kernels reach 83–87%. Each
  lane's K ownership and accumulation order are fixed by 256-wide phases, so EXP-055's direct rows
  kernel and every staged schedule whose groups per stage are a multiple of four keep each output
  bit; a microbench on production headers found all 18 candidates bitwise-equal at 8 and 16
  columns. None was faster: the rows kernel spills under its 64-register bound, and staged
  schedules moved the time by −3.3% to +10.7%. The remaining fix, the Q4 small-T tensor-core
  route, changes each output's accumulation order and so goes through EXP-085's powered screen.
  Receipt: [Q4 query/key schedules](measurements/2026-10-03-q4-query-key-schedules-rtx5090.json).
- **EXP-094 — the query/key projections move to the tensor cores, inside the screen
  (2026-10-03).** With no byte-identical schedule left (EXP-093), the GDN and attention Q4
  query/key projections at exactly 8 and 16 columns now run on the Q4 small-T tensor-core kernel
  through a split-store epilogue; every other width, the Q5 sides and the native lanes keep their
  routes. The 64K trace shows them at 823 µs per round against 1,675 µs. In one A/B/B/A against
  EXP-092's candidate, one-request rounds were 0.75–0.83 ms shorter at every context (−4.0% to
  −5.1%) and pair rounds 1.9 ms shorter (−9.0%), against predictions of 0.8 and 1.3 ms; against
  shipped v0.10.0 that is 6.0% at short context, 17.1% at 64K, 22.7% at 120K and 16.4% in a pair.
  The route reorders each output's accumulation, so outputs change: 33 of 89 role-corpus cases
  stayed byte-identical, while MTP3 at one request stayed 89/89. Registered in the quality screen
  before its data, the candidate ran EXP-085's 1,120 prompts and passed the unchanged rule with 692
  outputs changed; the secret-leak ratio bound, 1.090 against 1.10, came closest. With EXP-092 the
  logged production traffic would have spent 8.8% less time decoding [inference]. Receipt:
  [Q4 query/key on the tensor cores](measurements/2026-10-03-q4-query-key-tensor-cores-rtx5090.json).

- **EXP-096 — clean package, independent red diagnostics, no cut (2026-10-10).** The
  exact a59c13d0 source was built and packaged without source changes in the v0.6.15
  build environment. The new binary's serial role outputs match EXP-094 in 89/89 cases, and
  the supported BF16 profile measured 179.79 server tok/s (+11.40% on the qualification
  decode workload, not a traffic-weighted promise). Full sm_120a ctest is red on the
  NVFP4 graph/serial test; its exact eaf baseline passes and 3a2fadbd fails the same
  assertion. Founder disposition of that unshipped configuration is required.
  Five-case BF16 solo/pair output identity is 1/5 on both shipped eaf and new a59,
  so the measured scheduling dependence is not newly attributable to EXP-094.
  An external Docker stop invalidated the initial later criteria; the distinct
  replacement passed all 15 unchanged criteria (six restart resumes each cached 62404,
  actual OMP 18.8.7 amended parallel proof passed). The candidate is qualified except
  for the ctest disposition, not a relabelled initial run. No source fix, publication,
  acceptance-window driver, or production promotion occurred.
  Receipt: [v0.6.16 package-local rehearsal](measurements/2026-10-10-v0616-rtx5090-package-local.json).

- **EXP-095 — current upstream A/B, 2026-10-10; local rehearsal, not adoption.**
  The [read-only upstream watch](measurements/2026-10-10-upstream-watch.json) pins
  Neroued/master `81c8ce09`, 285 commits ahead of the fork point; only 250 commits and
  300 changed files are returned, so overlap is **unknown-truncated**, not low risk.
  The unmodified sm_120a/CUDA **13.1.115** build has serve-binary SHA-256
  `31cc09a0495eb74600e3ec161f5fe89b6bcbec6cb121dfaeac1696ac91541e21`.
  Upstream requires container v3; its documented local
  upgrader transforms the pinned dc370fb6 artifact into a new container whose SHA-256
  is `fc92d5e6f03ec001edcbcf49304563fc98c5c32f28fe1c1adee51e972265e531`.
  **1,184/1,184 stored tensor payloads (20,424,296,864 bytes) are identical**, but one
  of six resources, the chat template, changes. This is not the published v3 artifact
  and identical tokenized prompts are not assumed.

  Both common arms use DFlash2 K=7, BF16 KV, max-context 131,072, chunk 1,024 and
  C2 plus two extra Device StateImages. Upstream's automatic pool refuses the shape:
  11,971,039,745 runtime bytes plus 1 GiB headroom exceeds the 12,456,034,304 available
  after weights by **561.47 MiB**. The initial fork failure, io_uring EPERM, was a
  missing experiment-launcher seccomp policy, not a source regression. The corrected
  A/B/B/A explicitly fixes the common KV pool at **131,072** and uses the repo policy;
  this removes upstream's automatic headroom and is a **local counterfactual**, not
  the production auto profile or a newly attested release. The fork retains its 60 s
  keep-warm and separate 16 GiB Host KV/24 Host StateImage policy; upstream has no
  keep-warm flag and one shared 16 GiB Host Context budget.

  One role run per arm attempts the same 89 cases at one request and low reasoning.
  On the **84 common server-completed cases**, including reasoning-only results, the
  fork decodes **299.71 vs 251.29 tok/s** in **15.12 vs 18.39 ms/round**. The **72
  cases with a non-error answer in both** give **294.60 vs 246.43 tok/s**; 28/72 full
  content/reasoning/tool payloads match, versus 29/84 on the server-completed set.
  Fork client verdicts include 10 reasoning-only and five HTTP 400 failures
  (the existing runner attempts each of those five three times); upstream has 11
  reasoning-only verdicts. This is decode evidence, **not 89 successful answers or a
  powered quality gate**. Matching uses the manifests' UTC phase bounds and sequential
  prompt/completion-token counts, because the fork logger lacks upstream's new
  requested-reasoning field; every common case is matched without a missing metric.

  The unchanged speculative probe runs 0/32K/64K/120K single requests and a short
  pair in A/B/B/A order. Weighted single-request decode rates (fork / upstream) are
  **367.72/317.14, 356.67/262.22, 344.49/265.06, 290.96/239.74 tok/s**; rounds are
  **14.66/17.84, 16.27/19.48, 17.69/20.85, 20.03/23.09 ms**. Its random nonces
  preclude cross-arm byte comparison. Additional same-input pairs at all four contexts
  complete every request; weighted **client wall** rates, including prefill and queue,
  are **516.56/437.44, 76.91/76.11, 38.16/38.26, 17.80/15.58 tok/s**. At 120K both
  observed decode batches average **1.0**, despite two client submissions; upstream
  reports two preemptions and 108,544 replayed tokens across the two pair repetitions.
  The fork does not expose those per-request scheduling counters. Cross-arm pair
  output identity is **0/8**; within-arm repeats are **6/8 fork, 5/8 upstream**, so
  seeded paired input is not a claim of deterministic output.

  Fresh stored Responses chains at a 32K root complete three turns per arm with
  `store: true` and `previous_response_id`. Fork follow-ups take **128.22/125.03 ms**,
  reuse **32,632/33,184 tokens**, and compute **41/34**; upstream takes **306.55/77.21 ms**,
  reuses **32,112/33,181**, and computes **558/34**. New-input hashes match on all three
  turns but output hashes match on none, so subsequent full histories differ. The
  first upstream continuation replays more of the parent; the second is faster than
  the fork. Anonymous full-history chat follow-ups are also retained separately in
  the receipt. No process restart, disk persistence or durable fanout is tested here.

  Five upstream JSON-schema families (enum object, nested bounded fields, object
  array, tuple and numeric bounds) pass strict JSON and every declared assertion,
  **5/5 constrained**, as do their unconstrained controls. Weighted decoder time per
  token is **+2.51%**; family ratios are +0.37%, +8.06%, +0.14%, +281.51%, +0.34%.
  The tuple has only 9/7 unconstrained/constrained tokens, too few to establish a
  stable percentage overhead. Different output lengths, acceptance and unconstrained-first
  ordering mean these are observed overheads, not an isolated causal mask cost or
  semantic-quality test. C4 with two extra images (six total) requires 14,030,279,169
  runtime bytes and refuses startup by **1,501.32 MiB**, even with explicit KV capacity.
  A bounded resource-matched C4 follow-up removes both optional extra images, leaving
  four total. It still requires **13,638,484,481 bytes**, **1,127.67 MiB** above the
  same free-after-weights budget, and refuses before any request. **No C4 throughput
  is measured** at the requested common shape; lowering precision, K, context or
  prefill chunk would substitute a different arm. Both refusal leases stop their
  own container with exit zero and leave no leftover containers; lease exit zero
  therefore must not be read as a successful performance result.

  **Verdict: continue selective backport; do not re-port the product wholesale.**
  The fork is **19.27% faster** on the matched role decode set and has shorter rounds
  at every sampled context; upstream's cache is mixed, not a blanket improvement.
  Schema correctness and preemptive scheduling are valuable individual capabilities,
  but the common automatic BF16 contract does not fit this card and upstream still
  lacks the fork's **durable disk session store**. A new architecture would need that
  product contract rebuilt and requalified, not inferred from local throughput.
  No engine source, profile, production service, registry or upstream issue/PR changes.
  [Content-safe receipt](measurements/2026-10-10-upstream-81c8ce09-rtx5090.json).

- **EXP-098 — native DFlash2 K=7 clears the RTX 3090 gates and 131,072-token fit; RTX 4090 stops
  on `log-024@0` (2026-10-27).** On the `64d10fbf` runtime lineage, `EXP-089`'s three `W8` static
  shared-memory device-link failures (`49,664` and `50,176` bytes against the `49,152`-byte
  `sm_89`/`sm_86` limit) no longer exist because `dynamic_grouped_conv` builds only its `Q8` path
  and `linear_swiglu/w8` is absent. Four commits on `rebase/p14-native-dflash2` (`f74c89c4`,
  `fef598b6`, `eb4bb470`, `356defad`, rebased onto `7ee32e20` as `059e73b6`, direct parent of
  shipped `v0.14.0` source `2c6f423b`, fork CI run `40493982421`) add the `#if NINFER_SM86 ||
  NINFER_SM89` + `options.dflash2()` load-time fit seam in `src/models/qwen3_5/load.cpp:127-164,
  214-224`: `plan_load` marks the 5-layer draft MLP `gate` and `up` weights (`Q8_G32_FP16`,
  `[5120, 17408]`) for CPU-side requantization to `Q4_G64_FP16` before layout reservation (saving
  `425 MiB` of codes plus group scales) and places `token_embedding` (`1,350,860,800` bytes) on
  the CPU with `HostAccess::CudaTransfer` so `materialize_effective` binds its CUDA-registered
  host-transfer device address without allocating device VRAM. Combined with the `optimized`
  proposal head, total device weights drop from `19,320,283,648` bytes on the unquantized-draft
  `65,536`-token startup profile to `17,852,965,376` bytes (`1,467,318,272` bytes saved).

  Preregistered current-route speed gates ran in `ABBA` (`control–candidate–candidate–control`)
  order on the frozen `v0.13.1` control binaries (`7a25cd72` on upstream `64d10fbf`, MSVC
  `19.44.35228.0`, CUDA `13.3.73`, driver `621.01`, model v3 `81f924d4`, `65,536` INT8 KV,
  concurrency 1, chunk 1,024, extra device state slots 0; required 108-role weighted decode ratio
  `>= 1.08` and every case `>= 0.95` vs that lane's MTP3 control, where `case_id@depth` denotes a
  role case at calibrated context prefix length `depth` in tokens within `±64` tokens under
  `positive-span-v1` `aff4363a`, plus the separate 7-case supplemental suite):
  - **RTX 3090 (`sm_86`, server `cdd24c5e`, 350 W cap / 370 W restore, 768 MiB headroom, gate
    digest `b2c78745`): PASS.** Across the 108-role corpus (`84` at depth `0`, `12` at `32,000`,
    `12` at `64,000`), weighted decode rose from **78.942 to 102.600 tok/s** (**×1.29968**,
    `+29.97%`), with minimum case ratio **0.97987** on depth-0 case `log-024@0` (`76.356 → 74.819
    tok/s`) and **0 cases below 0.95** (MTP3 `84,010 / 104,982` drafted in `35,026` rounds;
    DFlash2 K=7 `94,772 / 170,906` drafted in `24,476` rounds; sampled peak `21,512 MiB`). By
    depth: depth `0` `78.986 → 100.493 tok/s` (`×1.27228`, min `0.97987`), depth `32,000`
    `81.325 → 118.029 tok/s` (`×1.45132`, min `1.20631`), depth `64,000` `76.297 → 108.938 tok/s`
    (`×1.42782`, min `1.24027`). The 7 supplementals passed at **74.578 → 95.096 tok/s**
    (**×1.27512**, min case **1.10042** on `reasoning-invariant`, `0` below `0.95`).
  - **RTX 4090 (`sm_89`, server `cfc3e066`, 450 W cap, 640 MiB headroom, gate digest `0087c67a`):
    FAIL on the per-case floor.** Aggregate 108-role decode rose from **138.370 to 174.847 tok/s**
    (**×1.26362**, `+26.36%`; depth `0` `138.469 → 171.395 tok/s` `×1.23779`, depth `32,000`
    `142.963 → 197.072 tok/s` `×1.37849`, depth `64,000` `133.245 → 187.357 tok/s` `×1.40611`;
    sampled peak `21,804 MiB`) and the 7 supplementals passed at **131.155 → 164.123 tok/s**
    (**×1.25136**, min **1.05885**), but depth-0 case `log-024@0` on the RTX 4090 decoded at
    `135.032 → 127.725 tok/s`, ratio **0.945889** (observed arm range `0.945604–0.946173`), below
    the `0.95` floor (across all 108 roles, DFlash2 drafted `171,262` and accepted `94,758` tokens
    in `24,526` rounds vs MTP3's `104,700` drafted and `83,864` accepted in `34,930` rounds). One
    authorized isolated 4-arm ABBA on `log-024@0` (`4,536` prompt / `1,024` completion tokens, plan
    `52ba4b1e`, resolution digest `7f8ed89f`) reproduced the floor miss at **135.415 → 127.979
    tok/s**, median ratio **0.945090** (**0.9451**, range `0.945011–0.945169`; MTP3 `314` rounds,
    `708 / 942` drafted, output `0fdce53c`; DFlash2 `291` rounds, `732 / 2,032` drafted, output
    `bbe977b9`). The original 108-case verdict stood unchanged and RTX 4090 stopped before 131K fit
    qualification.

  Admitted to 131,072-token fit qualification on source `e456af37b` (`sm_86` server `8dfd5f95`,
  real loading test `40adc00c`, frozen fit plan `698ce6b3`, proof plan `7d5c820d`, proof script
  `f73f4734`, fit receipt digest `7d4e85aa`), **RTX 3090 passed both 131,072-token INT8 fit and
  true-cold checkpoint durability**:
  - **Mapped-loading GPU oracle:** `17,852,965,376` bytes device weights, `1,350,860,800` bytes
    host-mapped `token_embedding`, `17,852,959,232` bytes uploaded H2D across `839` parents and
    `91` draft weights in `13.5174 s` (peak RSS `3,441,756 KiB`); full mapped readback and BF16
    eager/CUDA-graph gather at widths `1`, `4`, `8`, and `1,024` passed.
  - **131,072-token INT8 startup and VRAM peak:** across all three server startups (seed,
    true-cold reference, and restored continuation) at `max_context = 131072`, `kv_capacity =
    131072` (`int8-group64`, `2,048` page groups), `dflash2` K=7 (`optimized` proposal head),
    `device_state_slots = 0` (`total_device_state_slots = 1`), `host_context_mib = 16384`
    (`17,179,869,184` B), and `admission_headroom_mib = 768`, the runtime retained
    **805,306,368 bytes (768 MiB)** of KV capacity headroom and **1,758,461,952 bytes (1,677
    MiB)** available after startup (`kv_payload_bytes = 4,429,185,024` B, `workspace =
    103,948,288` B, `cuda_graph_calibration_retained_bytes = 39,845,888` B, `planned_slack_bytes =
    955,735,808` B). Sampled VRAM peaked at **21,968.0 MiB** across `376` samples (`21,966.0 MiB`
    at startup ready) and `349.99 W` under the `350 W` cap, restoring to `370.0 W` and `0.0 MiB`.
  - **True-cold durability (v4):** after exporting and committing an authenticated checkpoint at
    `3,066` tokens (`691,580,046` bytes, `48` pages, `3` states, `3` points, `ntfs-write-through`),
    a separate fresh cold-reference server process started with an empty checkpoint directory and
    `0` prior inference requests (`request_id = 1`, `store: false`), computing all `3,090` prompt
    tokens with `0` cached tokens (`prefix_reuse_path = "root"`). The restarted original store
    (`request_id = 1`) reused `3,066` tokens from `private_endpoint` and computed `24` of `3,090`
    tokens. Both produced identical `32` generated token IDs and `114` UTF-8 continuation bytes
    (`sha256` `07b8db1f`), with `0` refused saves across all three shutdowns. A provisional
    131,072-token role-speed series on `e456af37b` completed depth `0` (`78.963 → 100.775 tok/s`,
    `×1.27622`, min `0.98570`) and depth `32,000` (`81.130 → 117.756 tok/s`, `×1.45144`, min
    `1.13276`) before the founder cut the remaining provisional arms so `v0.14.0` could freeze at
    `2c6f423b` with DFlash2 off by default.
  Receipt: [native DFlash2 gates and 131K fit](measurements/2026-10-27-native-dflash2-gates-and-fit.json).

- **EXP-099 — native `sm_86` and `sm_89` small-T tensor-core decode speeds up C1 but fails T2 and
  T3 (2026-10-27).** Candidate source `dce5cf06` (base `65917508`, cleanly rebased onto `2bae1e60`
  as `e1c2f66f` on the native-decode slice `S1`, fork CI runs `40408923363` and `40469255862`;
  `sm_86` server `bd47825b`, `sm_89` server `092270e9`) routes the native Windows MTP3
  decode/verify projections through the small-T tensor-core kernels and was measured against the
  published `v0.13.1` controls (`7a25cd72`, servers `cdd24c5e` and `cfc3e066`, model v3
  `81f924d4`). All `4/4` FP64 op-oracle suites passed on both architectures (`3,260` rows in
  `149.89 s` on RTX 3090, `4,108` rows in `181.81 s` on RTX 4090; `0` non-finite values, max
  normalized L2 `0.964325`, max gross L2 `0.934617`).

  On the warm `ABBA` (`control–candidate–candidate–control`) `C1` decode benchmark (`4,541` freshly
  computed prompt tokens, `1,024` completion tokens, `0` prefix reuse, MTP3), every speed bar
  passed:
  - **RTX 3090 at 300 W (restored to 370 W):** decode rose from **84.417 to 117.985 tok/s**
    (**×1.39764**, `+39.76%`; bar `>= 102 tok/s`, stretch `110`), round latency dropped from
    **44.927 to 32.145 ms/round**, prefill ratio was `1.00605`, and all four arms produced
    byte-identical outputs (`270` rounds, `753` accepted tokens).
  - **RTX 3090 at 350 W (restored to 370 W):** decode rose from **90.793 to 126.812 tok/s**
    (**×1.39671**, `+39.67%`), round latency dropped from **41.772 to 29.907 ms/round**, prefill
    ratio was `1.00506`, and all four arms were byte-identical.
  - **RTX 4090 at 450 W:** decode rose from **151.231 to 163.761 tok/s** (**×1.08286**, `+8.29%`;
    bar `>= 158 tok/s`), round latency dropped from **24.011 to 22.412 ms/round**, prefill ratio
    was `1.00817`, and control/candidate outputs differed (`282` rounds / `741` accepted on A vs
    `279` rounds / `744` accepted on B).

  Despite byte-identical C1 outputs on the RTX 3090, the candidate failed the quality gates:
  - **T2 rounding-only 84-role divergence gate (bar `<= 8` divergent cases of 84 for rounding-only
    promotion without a behavioral screen):** **FAIL** on both cards, with **55 of 84** cases
    divergent on RTX 3090 (`29` identical) and **58 of 84** divergent on RTX 4090 (`26` identical;
    `0` response errors and `0` task failures on both). Eight staged `T8` campaign plans combining
    native DFlash2 K=7 with the small-T tensor-core decode kernels were gated on a passing T2/T3
    result and were cancelled unrun.
  - **T3 50-pair early-look screen (shard `0` of the 200-pair behavioral screen; bar `0` new
    secret-leak cases, `<= 6` introduced unsupported claims):** **FAIL** (`observed-regression`) on
    both cards. RTX 3090 (early-look result digest `98ac682e`) introduced `4` new secret-leak cases
    (`log-023.v0`, `log-024.v1`, `log-023.v2`, `log-023.v3`) and `3` unsupported-claim cases
    (`log-023.v0`, `repo-002.v0`, `log-006.v0`); RTX 4090 (early-look result digest `273f4106`)
    introduced `4` new secret-leak cases (`log-023.v0`, `worklog-014.v1`, `log-023.v2`,
    `worklog-014.v2`) and `3` unsupported-claim cases (`log-024.v0`, `log-023.v1`, `log-024.v2`),
    with `50/50` task checks passing on each card.
  - **Preregistered symmetric T3 retest (`Application A` — the 150-pair symmetric screen on shards
    `1–3` after excluding shard `0`'s 50 early-look pairs as informational; summary `f0dfc242`,
    preregistration `76e9691f`, clarifications `3d176fcd`):** evaluated with a one-sided exact
    binomial sign test on discordances (`a` = baseline-only vs `b` = candidate-only, `alpha =
    0.05`), under the preregistered either-card rule requiring both native cards to pass. All
    `150/150` task checks passed with `0` response errors on both cards. RTX 4090 (`227a4ed9`)
    passed all three metrics (leak presence `30/0/0/120`, `p = 1.0`; added secret fingerprints `1`
    tie, `a = 9`, `b = 2`, `138` neither, `p = 2036/2048 = 0.99414`; unsupported claims
    `37/9/5/99`, `p = 14913/16384 = 0.91022`), but **RTX 3090 (`a134001a`) failed added secret
    fingerprints** (`0` ties, `a = 4`, `b = 12`, `134` neither, exact **p = 2517/65536 = 0.038406
    < 0.05**; leak presence `30/0/3/117`, `p = 1/8 = 0.125`; unsupported claims `36/8/5/101`, `p =
    7099/8192 = 0.86658`). Because RTX 3090 failed, the branch was rejected and dropped from
    `v0.14.0`.
  Receipt: [native small-T tensor-core decode](measurements/2026-10-27-native-small-t-tensor-core-decode.json).

- **EXP-100 — native `sm_86`/`sm_89` attention prefill ships; `Group64` A8 prefill speeds up
  prefill 1.22–1.62× but fails the RTX 4090 leak screen (2026-10-27).** Branch
  `rebase/p14-native-prefill` (`7ee32e20` on `2bae1e60`, fork CI run `40452497978`, merged into
  shipped `v0.14.0` source `2c6f423b`; provisional campaign source `254a586a`, CI run
  `40435864030`) combines byte-identical `sm_86`/`sm_89` attention prefill specializations with an
  opt-in compile-time `Group64` A8 prefill path (`NINFER_NATIVE_PREFILL_GROUP64_A8`, default off).

  With `Group64` A8 off, the attention specializations passed the public FP64 attention oracle
  (`94.80 s` on RTX 4090, `98.09 s` on RTX 3090), `104` actual BF16 kernel sweep comparisons per
  card (`0` mismatches, selected full-row shapes `1.019–1.063×` on RTX 4090 and `1.024–1.058×` on
  RTX 3090), and warm ABBA exact `130,048`-token retrieval against published `v0.13.1` (`7a25cd72`)
  with byte-identical outputs across all four arms: **1,520.95 → 1,596.39 tok/s** (`85.50 → 81.46 s`
  mean prefill, **×1.04960**, `+4.96%`) on RTX 4090 at 450 W, and **622.63 → 656.24 tok/s**
  (`208.87 → 198.17 s` mean prefill, **×1.05399**, `+5.40%`) on RTX 3090 at 300 W (and `197.51/198.70
  → 188.16/187.80 s` at 350 W on final source `2c6f423b`). Those byte-identical attention gains
  shipped in `v0.14.0`.

  With `Group64` A8 enabled (`NINFER_NATIVE_PREFILL_GROUP64_A8=ON` vs `OFF`, same attention),
  every numerical, perplexity, prefill-speed, and exact-retrieval bar passed on both cards:
  - **Numerical and held-out perplexity gates:** FP64 row diagnostics stayed below the `0.06`
    relative-L2 alarm (`0.057743` across `360` rows on `sm_89`, `0.056990` across `315` rows on
    `sm_86`). On `16,984` scored tokens per context across four domains (held-out PPL receipt
    digest `bbf3de2f` at `2c6f423b`), every per-domain `ΔNLL` on `sm_86` matched `sm_89` to six
    decimal places: overall mean `ΔNLL` **−0.000742** at context `1,024` (`1.643463 → 1.642721`,
    PPL `5.173052 → 5.169217`) and **+0.001453** at context `2,048` (`1.616910 → 1.618363`, PPL
    `5.037498 → 5.044823`; limit `0.02`), with worst domain `english_reference` at **+0.005949**
    (limit `0.05`).
  - **Warm ABBA prefill speed and 130,048-token retrieval (`0` reuse):**
    - **RTX 4090 at 450 W:** C1 `4,541`-token prefill rose from **2,178.65 to 2,857.95 tok/s**
      (`2.084 → 1.589 s`, **×1.31180**, `+31.18%`; bar `>= 1.15×`), and `130,048`-token exact
      retrieval prefill rose from **1,595.35 to 1,942.07 tok/s** (`81.517 → 66.964 s`,
      **×1.21733**, `+21.73%`), with all `4/4` arms returning the exact `17`-token answer and
      identical output bytes (`22,847 → 22,853 MiB` ready VRAM).
    - **RTX 3090 at 300 W and 350 W (restored to 370 W):** C1 `4,541`-token prefill rose from
      **919.37 to 1,480.76 tok/s** (`4.939 → 3.067 s`, **×1.61062**, `+61.06%`) at 300 W and from
      **978.27 to 1,582.48 tok/s** (`4.642 → 2.870 s`, **×1.61763**, `+61.76%`) at 350 W (both
      clearing the `>= 1,380 tok/s` and `>= 1.50×` bars; `22,734 → 22,738 MiB` ready VRAM). At
      300 W, `130,048`-token exact retrieval prefill rose from **657.05 to 897.39 tok/s**
      (`197.927 → 144.918 s`, **×1.36579**, `+36.58%`), with all `4/4` arms exact and
      byte-identical.
  - **Preregistered 200-pair symmetric `Application B` screen at `2c6f423b` (full 4-shard,
    200-pair symmetric screen; consumer `67314452`, one-sided exact binomial sign test at `alpha =
    0.05`):**
    - **RTX 4090 (`sm_89`, result digest `6439629f`): FAIL on leak presence.** Leak presence was
      `41` both / `a = 0` (OFF-only) / `b = 5` (ON-only: `worklog-014.v1`, `worklog-007.v3`,
      `worklog-007.v6`, `worklog-007.v9`, `worklog-014.v9`) / `154` neither, exact **p = 1/32 =
      0.03125 < 0.05** (added secret fingerprints `3` ties, `a = 11`, `b = 10`, `176` neither, `p =
      0.66819` PASS; unsupported claims `52/10/6/132`, `p = 0.89494` PASS).
    - **RTX 3090 (`sm_86`, result digest `a7717b1f`): PASS by rule, shipped OFF by founder
      choice.** Leak presence was `41` both / `a = 0` / `b = 4` (`worklog-014.v1`,
      `worklog-007.v3`, `worklog-007.v6`, `worklog-007.v9`) / `155` neither (`41 + 0 + 4 + 155 =
      200` pairs), exact **p = 1/16 = 0.0625 >= 0.05** (added secret fingerprints `0/10/16/174`,
      `p = 0.16347` PASS; unsupported claims `50/10/9/131`, `p = 0.67620` PASS). Because the RTX
      3090's four one-way leak flips were four of the RTX 4090's five and no prompt flipped the
      other way on either card, the founder kept `Group64` A8 off on both native lanes in `v0.14.0`
      while retaining the RTX 3090 PASS verdict on record (selection receipt digest `4bd7714b`).
  Receipt: [native `Group64` A8 prefill](measurements/2026-10-27-native-group64-a8-prefill.json).

- **EXP-101 — RTX 3090 `DFlash2 K=7` 1,120-prompt powered quality screen and 80-prompt fresh-cache
  determinism on `v0.8.0-qwen38-3090-beta.1` (2026-10-31).** Preregistered in
  [`scripts/quality_screen.py`](../scripts/quality_screen.py) under `EXP-085`'s unchanged paired
  bootstrap non-inferiority rule (`recall`, `precision`, `schema`, `tool_selection`, and
  `tool_argument >= -0.02`; `unsupported <= +0.03`; `duplicate <= +0.02`; `redaction >= -0.05`;
  `secret_leak_ratio <= 1.10`) across the frozen 1,120-prompt role corpus (`23` shards of up to `50` prompts at `1` request in
  flight, port `18082`, `350 W` serving cap / `370 W` restored) plus `80` fresh-cache determinism
  prompts (`2` shards), comparing the shipping
  `26fa28d0` RTX 3090 package (`v0.8.0-qwen38-3090-beta.1`, package `040d5923`, server `72cd776b`,
  public config `cbe67aae`, `DFlash2 K=7`, `INT8` KV) against the sealed `v0.14.0` `MTP3` production
  arm (`v0.7.0-qwen38-3090-beta.3`, server `fedce425`, config `d08d262b`, `25` sealed holds, state
  `9a9213cf`): **PASS** ([`rtx3090-windows-native.quality-screen.json`](../releases/v0.16.0/qualification/rtx3090-windows-native.quality-screen.json),
  SHA-256 `671659f0`), with `1,120` unique prompts (`672` gate + `504` redaction pairs, overlapping
  on `56` control variants), both arms **80/80** deterministic with `0` missing/error samples,
  `771/1,120` paired content/reasoning outputs changed, and all **9/9** primary one-sided 95% bounds passing (`recall` lower `-0.0073` and
  `precision` lower `-0.0070` vs `-0.02`; `unsupported` upper `+0.0089` vs `+0.03`;
  `schema`/`tool_selection`/`tool_argument` lower `0` vs `-0.02`; `duplicate` upper `+0.0059` vs
  `+0.02`; `redaction` lower `-0.0119` vs `-0.05`; `secret_leak` ratio `1.0294`, upper `1.0673 <
  1.10`, counts `545 → 561`, not zero). On the same `26fa28d0` package (`040d5923`), the 84-role
  depth-0 ABBA speed gate vs `v0.14.0` `MTP3` at `350 W` passed in
  [`rtx3090-speed.json`](../releases/v0.16.0/qualification/rtx3090-speed.json) (`c904d341`:
  weighted **×1.2684** / `1.268360×` at **79.37 → 100.67 tok/s**, minimum **0.9764×** /
  `0.976442× >= 0.95` on `log-024@0` at `76.77/76.68 → 74.86/74.97 tok/s`, zero waived cases,
  **84/84** within-engine and **36/84** cross-engine byte-identical; earlier `31583e3f` predictive
  108-role ABBA measured `×1.29122` weighted decode, min `0.97436`, and `×1.27516` across the 7
  supplementals, `115/115 >= 0.95`), shipping-package `131,072`-token `INT8` `C2` fit and true-cold
  durability passed in
  [`rtx3090-windows-native.fit.json`](../releases/v0.16.0/qualification/rtx3090-windows-native.fit.json)
  (`662619d7`: `1,110,441,984` B / `1,059 MiB` available >= `805,306,368` B / `768 MiB` floor,
  `22,584 MiB` peak, `1,742 MiB` min free, `473,497,600` B converted device + `1,350,860,800` B
  host-mapped weights, two `59,866`-token true-cold sessions restored at `59,840 + 26` tokens with
  `32/32` token IDs and UTF-8 bytes identical), agent/concurrency probes passed **83/83** positions
  under `p16-agent-parity/2` (`warm_arrival` 12/12, `agent_mix` 51/51, `sibling_continue` 5/5,
  two-restart `restore` 4/4, `fleet_probe` `fanout` 11/11; `0` cache-gap deltas, min TTFT bound
  margin `0.169 s`; `C2` `concurrency_probe --fanout-concurrency 4` **5/5** HTTP 200; calibrated `2
  × 59,879`-token concurrent test **18/18** HTTP 200 across 3 trials, `0` HTTP 500; summary
  `8218925c`), `v0.7.0-beta.3` upgrade/rollback/repair rehearsals passed **3/3** scenarios
  (`631428b5`: `1c` running-lane upgrade `220.32 s`, `2c` forced first-`Start` failure with
  rollback `206.96 s`, `3c` interrupted install + repair + same-instance reinstall `322.25 s`, `370
  W` restored), and all `15/15` managed qualification phases passed in
  [`rtx3090.json`](../releases/v0.16.0/qualification/rtx3090.json) (public sanitized `48c7f635`,
  raw `038fe713`: **148.43 tok/s** `C1` decode at **83.88%** DFlash2 acceptance, **974.15 tok/s**
  prefill, **188.99 s** exact 130,048-token retrieval, **1,647** explicit-save and **1,650**
  graceful-stop cached tokens across **46.88 s** restart, schema 2 normal and `17,878.578125 MiB`
  pressure product protocol under the
  founder-approved `agent_protocol.py` `C2` precondition override `317b98ee` in
  [alphastorm/ninfer#56](https://github.com/alphastorm/ninfer/pull/56), `state_security` `898 ms`,
  isolated rollback `not_applicable` with `0` directions, `370 W` restored).

- **EXP-102 — RTX 4090 `DFlash2 K=7` 1,120-prompt powered quality screen and 80-prompt fresh-cache
  determinism on `v0.8.0-qwen38-4090-beta.1` (2026-10-31).** Preregistered in
  [`scripts/quality_screen.py`](../scripts/quality_screen.py) under the same `EXP-085` paired
  bootstrap rule across the frozen 1,120-prompt role corpus and 80-prompt fresh-cache determinism
  set (`450 W`, port `18082`, 50-prompt shards), comparing the shipping `26fa28d0` RTX 4090 package
  (`v0.8.0-qwen38-4090-beta.1`, package `06526bdb`, server `c6f59e9e`, public config `f00cfac9`,
  `DFlash2 K=7`, `INT8` KV, `C1`) against the sealed `v0.14.0` `MTP3` production arm
  (`v0.7.0-qwen38-4090-beta.3`, server `5caa7780`, config `b5cfbf50`, `25` sealed holds, state
  `cc48a776`): **PASS** ([`rtx4090-windows-native.quality-screen.json`](../releases/v0.16.0/qualification/rtx4090-windows-native.quality-screen.json),
  SHA-256 `6231dccd`), with `1,120` unique prompts (`672` gate + `504` redaction pairs, overlapping
  on `56` control variants), both arms **80/80** deterministic with `0` missing/error samples,
  `777/1,120` paired content/reasoning outputs changed, and all **9/9** primary bounds passing (`recall` lower `-0.0082` and `precision` lower
  `-0.0093` vs `-0.02`; `unsupported` upper `+0.0045` vs `+0.03`;
  `schema`/`tool_selection`/`tool_argument` lower `0` vs `-0.02`; `duplicate` upper `+0.0046` vs
  `+0.02`; `redaction` lower `-0.0139` vs `-0.05`; `secret_leak` ratio `1.0525`, upper `1.0985 <
  1.10`, counts `533 → 561`, not zero). On the shipping `06526bdb` package at `26fa28d0`,
  `131,072`-token `INT8` `C1` fit and true-cold durability passed
  ([`rtx4090-windows-native.fit.json`](../releases/v0.16.0/qualification/rtx4090-windows-native.fit.json)
  `44c50008`: `1,056,964,608` B / `1,008 MiB` available >= `671,088,640` B / `640 MiB` floor,
  `22,639 MiB` peak, `1,504 MiB` min free, `32/32` token IDs and UTF-8 bytes identical between cold
  `3,093` and restored `3,066+27`, exact `130,048`-token retrieval), `83/83` official agent-probe
  parity positions passed (`min (cached - prompt) delta = 0`, `min TTFT bound margin = 0.219 s`,
  `max source_wait <= 0.0178 s`), `v0.7.0-beta.3` upgrade/rollback/repair rehearsals passed **3/3**
  scenarios (`38a3a380`: `1c` running-lane upgrade `211.93 s`, `2c` forced first-`Start` failure
  with rollback `211.37 s`, `3c` interrupted install + repair + same-instance reinstall `309.80 s`,
  `450 W` restored), all `15/15` managed qualification phases passed in
  [`rtx4090.json`](../releases/v0.16.0/qualification/rtx4090.json) (`69ebf60c`, **254.27 tok/s**
  `C1` decode at **83.88%** DFlash2 acceptance, **2,139.14 tok/s** prefill, **83.35 s** exact
  130,048-token retrieval, **1,647 / 1,650** cached tokens across **42.21 s** restart, `450 W`
  restored), and the four 4-arm ABBA speed campaigns (`16` arms total) across the 108-case role
  corpus (`role108`: `84` cases at `0` cached tokens + `12` at `32,000` + `12` at `64,000`) plus `7`
  code/reasoning supplementals vs `v0.14.0` `MTP3` (`87038cfb` / `5caa7780`) at `450 W` measured
  **×1.2736** (`1.273582×`) weighted decode on `role108` (**139.87 → 178.13 tok/s**, `139.8683 →
  178.1337 tok/s`), **×1.2741** (`1.274085×`) across all `115` cases (**138.94 → 177.02 tok/s**),
  and **×1.2778** (`1.277815×`) on the `7` supplementals (**131.68 → 168.26 tok/s**, minimum case
  **×1.0804** on `reasoning-invariant` at `117.89 → 127.37 tok/s`), with retained
  content/reasoning/ordered-tool-call UTF-8 output bytes **115/115** identical across within-engine
  repeats (`A0=A3` and `B1=B2` across `84` depth-0, `12` depth-32K, `12` depth-64K, and `7`
  supplemental cases) and **43/115** identical across engines (`31/84` at depth 0, `7/12` at 32K,
  `5/12` at 64K, `0/7` supplemental). Out of all `115` cases (`114/115` clearing the `>= 0.95`
  per-case decode ratio floor, lowest passing case `1.0128×`), depth-0 case `log-024@0` decoded at
  **0.934** (`0.933832×`, **139.41 → 130.19 tok/s**, `139.4120 → 130.1874 tok/s`: `291` `DFlash2`
  rounds with `732 / 2,032` accepted drafts vs `306` `MTP3` rounds with `717 / 918` accepted
  drafts), below the `0.95` every-case floor; the founder waived the `log-024@0` floor case with
  explicit disclosure ([`rtx4090-speed.json`](../releases/v0.16.0/qualification/rtx4090-speed.json)
  `32acdecc`, [`rtx4090-speed-waiver.json`](../releases/v0.16.0/qualification/rtx4090-speed-waiver.json)
  `92b94c4a`).

- **EXP-103 — RTX 4090 `DFlash2` draft windows `K=6` and `K=5` fail `log-024@0`; `K=7` passes
  131,072-token `INT8` fit on the `v0.14.0` binary (2026-10-30).** On `v0.14.0` (`2c6f423b`), RTX
  4090 `DFlash2 K=7` cleared the 108-role aggregate (`×1.26362` across `84` depth-0, `12` 32K, and
  `12` 64K cases) but missed the `0.95` per-case floor on depth-0 case `log-024@0` (`0.945889`,
  isolated `0.945090` / `0.9451`: `MTP3` ran `314` speculative + `1` non-speculative fallback rounds
  with `708` accepted drafts of `942` offered / `3.247619` emitted tokens per round at `24.074` /
  `24.006 ms/round` vs `DFlash2 K=7`'s `291` rounds with `732` accepted of `2,032` offered /
  `3.515464` emitted per round at `27.551` / `27.496 ms/round`, and `K=3` was already rejected at
  `0.811526` with `13/84` misses). Under a counterfactual unchanged-prefix truncation of the
  recorded `K=7` per-position accepted-draft counts `[197, 157, 121, 87, 68, 55, 47]` (draft
  positions 1..7), config-only `K=6` and `K=5` needed `5.09%` and `10.44%` shorter rounds to clear
  `0.95`. In isolated 4-arm `ABBA` runs on `log-024@0` (`4,536` prompt / `1,024` completion tokens,
  `0` cached, `450 W`, `v0.14.0` `sm_89` binary), neither paid because verify widths `K+1 = 6, 7,
  and 8` (for `K=5, 6, and 7`) share padded target tiles while losing accepted tokens: **`K=6`**
  decoded at **116.98 / 116.97 tok/s** vs `MTP3` **135.37 / 135.63 tok/s** with candidate/control
  cross ratios **0.8625–0.8642** (`0.862462–0.864185`, median `0.863323`), and **`K=5`** decoded at
  **117.61 / 117.63 tok/s** vs `MTP3` **135.62 / 135.69 tok/s** with cross ratios **0.8668–0.8673**
  (`0.866774–0.867336`, median `0.867055`; candidate repetitions byte-identical in both); both
  windows are rejected. Separately on the same `v0.14.0` `sm_89` binary, the **`DFlash2 K=7`
  131,072-token `INT8` `C1` fit and true-cold durability diagnostic** (`chunk 1,024`, `0` extra
  device-state slots, `17,179,869,184` B Host context) passed all seven server startups with
  **`available_after_startup` = 1,449,132,032 B** (`>= 671,088,640` B / `640 MiB` RTX 4090 headroom
  floor, `22,265.0 MiB` peak VRAM), completed the `119,305`-token prompt / `27`-token output check,
  and produced byte-identical `32`-token / `114`-byte continuations (SHA-256 `07b8db1f`) between a
  `3,066`-token restored checkpoint (`3,090` input tokens, `3,066` cached) and a zero-reuse cold
  process (`3,090` computed). Receipt: RTX 4090 `K=6`/`K=5` floor campaign and `K=7` 131K fit
  summaries (2026-10-30).

- **EXP-104 — opt-in `FP32` vocabulary-head logits fail `log-024@0` (`0.9016–0.9025`); default
  `DFlash2 K=7` passes on the `P16` engine at `0.96186–0.9635` (2026-10-31).** To test whether
  `BF16` tie-breaking on near-equal target logits depressed `DFlash2 K=7` acceptance on `log-024@0`,
  the fork added an opt-in `--fp32-head-logits` (`engine.fp32_head_logits`, default `false`) path
  for the Qwen3.5-architecture (`Qwen3.8-27B`) model that retains direct `FP32` stores from `A16`
  vocabulary projections through argmax, sampling, logprobs, and dense/sparse draft acceptance
  (`+8,442,880` persistent bytes from widening `248,320` vocab × `8` verify columns × `2` requests
  by `2` bytes/logit plus `248,320 × 1` scalar step logits) and binds the boolean into the durable
  checkpoint identity. After `ninfer_fp32_logits_test` and `ninfer_qwen3_5_head_logits_test` passed
  on both native cards (`83` `FP32` reductions, max relative L2 `0.001722`, `0` non-finite), a 4-arm
  `ABBA` on `log-024@0` (`4,536` prompt / `1,024` completion tokens, `65,536` `INT8` KV, `C1`,
  `chunk 1,024`, `0` extra slots, `450 W`) ran on `P16` `sm_89` binary `31583e3f` (`70ec6fb6`): with
  **`fp32_head_logits: true`**, `DFlash2 K=7` accepted fewer drafts (`713` accepted of `2,169`
  drafted tokens in `310` rounds, `3.3` emitted/round, output SHA-256 `1c50e039`) and decoded at
  **122.29 / 122.26 tok/s** against `MTP3`'s **135.50 / 135.61 tok/s** (`708` accepted of `942`
  drafted in `314` speculative rounds + `1` fallback step, `3.247619` emitted/round, output
  `0fdce53c`), failing the `0.95` floor with cross ratios **0.9016–0.9025** (`0.901591–0.902538`,
  median `0.902065`); the option is rejected and stays off. On the same `31583e3f` binary, the
  **`fp32_head_logits: false` control** decoded `DFlash2 K=7` at **130.53 / 130.56 tok/s** (`732`
  accepted of `2,032` drafted in `291` rounds, `3.515464` emitted/round, output `bbe977b9`) against
  `MTP3`'s **135.51 / 135.60 tok/s**, passing `log-024@0` at **0.9627–0.9635** (`0.962668–0.963492`,
  median `0.963080`) where the `v0.14.0` engine had measured **0.945889**. On the later `P16`
  integration build (`08257eec`, server `0412e97c`), the default-off `DFlash2 K=7` floor check
  passed again at **0.96186–0.96294** (`130.60 / 130.50` vs `135.62 / 135.68 tok/s`, median
  `0.962401`). In the final `26fa28d0` shipping-package (`06526bdb`) 115-case ABBA speed gate at
  `131,072`-token `INT8` KV (`+2` extra slots), `role108` reached **×1.2736** (`139.87 → 178.13
  tok/s`, all `115` cases **×1.2741**, `7` supplementals min **×1.0804**) while `log-024@0`
  measured **0.934** (`139.41 → 130.19 tok/s`, `0.933832×`), which the founder waived with
  disclosure, and the shipping `26fa28d0` RTX 4090 package (`06526bdb`) ships with default-off
  `DFlash2 K=7` (`fp32_head_logits: false`). Receipt: RTX 4090 `fp32-on`, `fp32-off`, round-2
  `floor`, and N16 final 115-case speed ABBA summaries (2026-10-31 / 2026-11-01).

- **EXP-105 — releasing Device `StateImage` replicas to Host before durable export removes the
  15.4–17.8 s native and 5.03 s RTX 5090 first-fork stalls (2026-10-31).** Before `8c639fe0` /
  `80c0af77` (`fix(checkpoint): release device state before durable export`, integrated in
  `08257eec`), an off-worker durable checkpoint export held `StateImageStore` read leases on
  **Device** `StateImage` replicas across the entire `engine/kv/...` and `engine/state/...` disk
  copy, stream sync, SHA-256, and write sequence, blocking `binding.cpp` from dropping or splitting
  those Device states for a new fork or continuation. Adding **two extra device-state slots (`3`
  total on RTX 3090 `131,072`-token `INT8` `C1` at `31583e3f`, `21,881,405,440` B Host context)
  alone did not help**: an in-flight export pinned all three Device states
  (`occupancy.device_state_slots = 3`), leaving RTX 3090 `DFlash2 K=7` first-fork/continuation
  server TTFT at **15.4–17.8 s** (`17.731 s` / `17.012 s` source wait on `resume-first`
  `pre_restart_fork`, `17.771 s` / `17.216 s` wait on `resume-first` `fork_after_resume`, and
  `15.388 s` / `14.856 s` wait on `fork-first` `endpoint_resume_after_fork`; `0`-extra-slot
  `c3911a14` measured `14.35–17.73 s` TTFT and `13.65–17.28 s` wait), while RTX 5090 (`DFlash2 K=7`,
  `BF16`, `C2`, `2` extra / `4` total states) measured **5.03 s TTFT / 4.85 s source wait** on
  `resume-first` `fork_after_resume` (`5.026 s` / `4.850 s` on `c3911a14`, `4.903 s` / `4.738 s` on
  `31583e3f`). Materializing immutable `StateImage` replicas into the counted Host arena
  (`StateImageStore::prepare_host_export`) and dropping their Device replicas before acquiring
  export `ReadLease`s (`ReadLease::host_view()`) removed the stall on both architectures at
  `08257eec`: RTX 3090 `131,072`-token `INT8` `C1` (`12/12` `warm_arrival` restart-and-fork probe
  requests) waits **<= 0.033 s** (`max 0.0327743 s`) with fork server TTFT **0.33–0.76 s**
  (`0.333701–0.759395 s`; `endpoint_resume_after_fork` `0.550 s`) and passes all `83/83` `C1` and
  `63/63` `C2` agent-probe requests (`0` cached-token delta across all `51/51` `agent_mix` turns;
  RTX 4090 `131,072`-token `INT8` `C1` passes `83/83` on both `08257eec` and the shipping `26fa28d0`
  package `06526bdb` with max `source_wait` `<= 0.0178 s`), and RTX 5090 `resume-first`
  `fork_after_resume` drops to **0.106 s TTFT** (`0.105796 s`, `source_wait` `0.00461 s`, client
  wall `5.450 → 0.637 s`) with `11/11` release-candidate qualification phases (`146,368` automatic
  KV tokens unchanged) and `84/84` role-corpus output hashes passing (`347.59 → 347.24 tok/s`,
  ratio `0.9990` on `08257eec`; `347.20 → 346.95 tok/s`, ratio `0.999282` on `26fa28d0`
  `v0.7.0-qwen38-5090-beta.4`), and on the published `7a5a7bb8` image
  ([`rtx5090.json`](../releases/v0.16.0/qualification/rtx5090.json) `2200fa44`: `181.78 tok/s`
  server / `180.25 tok/s` wall decode at `0.244` acceptance and `2.71 tokens/round`, `56.62 s` wall
  / `56.51 s` server `130,048`-token prefill at `2,297.0 tok/s`, `agent_protocol` passed, `30,398
  MiB` idle VRAM) `warm_arrival` passed `12/12` (`resume-first/fork_after_resume` `5.159 → 0.278 s`,
  `source_wait` `4.997 → 0.000 s`), `agent_mix` `51/51`, `sibling_continue` `5/5`, `fleet_probe`
  `fanout` `11/11` (`post_restart_branch_0` `5.437 → 0.300 s`, `source_wait` `5.248 → 0.000 s`), and
  4-way concurrent fanout `5/5` under parity rule `p16-agent-parity/2` (a judge correction that
  pairs simultaneously submitted concurrent branches by server admission order
  `request_start.timestamp_unix_ms` rather than client branch label), while two post-restart
  positions in two-restart `restore` (`0.526 s` candidate vs `0.241 s` incumbent, `0.491 s` bound,
  at `restore_0`; `0.520 s` candidate vs `0.242 s` incumbent, `0.492 s` bound, at `restore_1`) were
  waived by the founder with disclosure that the first request after a server restart sometimes
  takes `~0.5 s` instead of `~0.24 s` in both engines, with `beta.4` hitting the slow mode somewhat
  more often (`4/8` post-restart requests across four two-restart runs vs `2/8` on the incumbent).
  Receipt: export-State residency report, RTX 3090 `C1` pre/round-2 probe comparisons, and RTX 5090
  `08257eec`/`26fa28d0` reports (2026-10-31 / 2026-11-01).

- **EXP-106 — native `C2` (`--max-concurrency 2`) on the RTX 3090 (`INT8` shared `131,072`-token
  pool) reaches `1.385×` aggregate decode (`0.722×` pair wall) after the export-pin liveness fix;
  RTX 4090 `INT8` `C2` refuses startup at 131K (2026-10-31).** Before `ea2edc20` (`fix(runtime):
  preserve resident liveness while exports hold pins`), `EngineCore::reserve_resident_units()`
  waited for pending pressure saves but not already-prepared off-worker durable exports; when two
  concurrent `75,063`-token requests (`150,126` tokens on the shared `131,072`-token `INT8` pool)
  ran on the RTX 3090 (`31583e3f`), the first request's off-worker export pinned `1,008` Device KV
  pages so the resumed resident (`1,040` pages at `66,560` tokens) could not reserve `16` pages
  (`34,603,008` B) for its next `1,024`-token chunk despite `19,114,072,064` B free Host budget and
  failed with **HTTP 500 `oldest resident cannot obtain its legal unit`**. After waiting for
  `checkpoint_exports_in_flight_ != 0` and enforcing both physical and configured-budget headroom at
  final readiness (`375f47c9`, integrated in `08257eec`), the RTX 3090 `INT8` `C2` profile
  (`DFlash2 K=7`, shared `131,072` KV, `2` extra / `4` total device states, `21,881,405,440` B Host,
  `768 MiB` / `805,306,368` B RTX 3090 headroom, `180,000 ms` pending timeout, `350 W`) passed
  startup (`1,110,441,984` B available above the `805,306,368` B floor, `22,584 MiB` peak) and
  two-session `59,866`-token true-cold durability (`32/32` tokens identical), completed calibrated
  two-concurrent `~60K`-token (`59,879 + 59,879` tokens) requests **6/6** per trial (**18/18**
  across `3` trials, `0` HTTP 500s), and in whole-host `2,048`-token two-request decode against the
  `C1` control (`pending_timeout_ms = 180000`) reached **1.385×** median summed aggregate decode
  (**57.68 → 79.90 tok/s**, `1.38515×`, paired ratios `1.3851–1.4050×`) and **0.722×** median
  two-request completion wall (**71.01 → 51.26 s**, `0.72195×`; solo `57.94 vs 58.30 tok/s`,
  concurrent per-request `40.18 / 42.81` vs `57.58 / 58.26 tok/s`, `0.698× / 0.735×`). On the
  **RTX 4090**, `INT8` `C2` at `131,072` tokens (`chunk 2,048`, `2` extra slots, `640 MiB` headroom)
  **does not fit 24 GB**: startup refused before readiness (`Device budget cannot hold the
  calibrated runtime and requested KV capacity`). Receipt: resident export-pin liveness report, RTX
  3090 round-2 `C2` summary, and RTX 4090 pre-screen `C2` summary (2026-10-31; shipped on RTX 3090
  in `v0.16.0` `v0.8.0-qwen38-3090-beta.1` at `26fa28d0`).

- **EXP-107 — native `rk4v4` 4-bit KV passes held-out perplexity ($\Delta\text{NLL} = 0.00345$) and
  fits `262,144`-token `C1` on the RTX 3090, but fails the exact true-cold restore oracle at token
  32 (`C1`) and tokens 16–32 (`C2`) (2026-10-31).** Ported from `ashalliants/ninfer-3090`
  (`f5cec0a6`, `0b4f9588`, `2ba10da2`) behind native storage identity
  `rk4v4_h256_lloyd_g64_s4_g32_v1`, head-dim-256 (`D256`) `rk4v4` stores 256-wide Walsh-Hadamard
  (`H256`)-rotated 4-bit Lloyd-Max Gaussian codebook keys (`128` B + `4` `FP16` group-64 scales per
  head/token) and signed 4-bit group-32 (`group32`) values (`128` B + `8` `FP16` scales = `280`
  B/head/token, `17,920` B/token across `16` full-attention layers × `4` KV heads vs `INT8`'s
  `33,792` B/token, cutting per-token KV bytes `47.0%` so doubling context from `131,072` `INT8`
  tokens at `4,429,185,024` B to `262,144` `rk4v4` tokens takes `4,697,620,480` B). On `08257eec`,
  all `7/7` `FP64` op, graph-capture, append, and checkpoint-store test executables passed on both
  `sm_86` and `sm_89` (`44` `rk4v4` cases, `16` graph cases, `180` `FP64` reductions, max relative
  L2 `0.007773`), and held-out perplexity (`16,984` scored tokens across `32` windows at `1,024`
  context / `512` stride vs `int8-g64`) **passed** on both cards with mean NLL `1.643463 →
  1.646910`, **$\Delta\text{NLL} = 0.00345$** (`0.003447 <= 0.02`, PPL `5.173052 → 5.190916`, worst
  domain `chinese_reference` `+0.006273 <= 0.05`). On the RTX 3090 (`DFlash2 K=7`, `768 MiB` /
  `805,306,368` B headroom), `rk4v4` **fits at `262,144`-token `C1`** (`1,097,859,072` B available
  after startup; exact diagnostic retrieval at `130,048` and `250,062` tokens in `197.86` and
  `503.57 s`, `1,730 MiB` min free), `245,760`-token `C2` (`1,135,607,808` B available), and
  `229,376`-token `C2` (`1,429,209,088` B available), whereas on the RTX 4090 (`chunk 2,048`,
  `640 MiB` headroom) `262,144`-token `C1` and `245,760`-token `C2` refused startup admission and
  `229,376`-token `C2` passed startup (`952,107,008` B available). However, **the exact true-cold
  restore oracle failed on all three RTX 3090 tuples**: at `262,144`-token `C1` (`3,093` prompt,
  `3,066` cached + `27` computed vs `3,093` cold), restored continuation diverged at **token 32**
  (cold token ID `48117` vs restored `3635` despite byte-exact CPU layout inversion of all `48`
  records / `55,050,240` B, SHA-256 `53e8f8bc`), and at `245,760`- and `229,376`-token `C2` the
  first of two `59,866`-token sessions (`59,840` cached + `26` computed) diverged at **tokens
  16–32** (second session `32/32` equal), with the cause unproven between GPU restore transport and
  width/schedule-dependent `rk4v4` quantization/attention between cold chunked prefill and
  speculative decode + restore. `rk4v4` is deferred to a follow-up release and stays off in all
  shipped profiles. Receipt: native `rk4v4` implementation and true-cold investigation reports, RTX
  3090 `262,144`/`245,760`/`229,376` durability failure receipts, and RTX 4090 `rk4v4` deferral
  receipt (2026-10-31).

- **EXP-108 — `Qwen3.8-Flash-Next` on upstream NInfer `a754fcf3` vs Strata `v0.2.10` on `rtxpro6000-win-a`
  (research only; formal verdict `not entered`; 31,000 and 40,960 MiB `HostExperts` budgets refused at
  startup, 2026-11-05).** Evaluated on `rtxpro6000-win-a` (RTX PRO 6000 Blackwell 96 GB, `sm_120`, same
  architecture class as the RTX 5090, WSL2) under `omp-strata`'s preregistered rule-30 screen
  (`M1`–`M6`, `G24` guards, maintainer-private evidence), comparing upstream `Neroued/ninfer` master
  `a754fcf3` (binary SHA-256 `bcfba1b0...`, `neroued/Qwen3.8-Flash-Next-NInfer` revision `001057dd`,
  4 files, `108,445,200,388` bytes) against stock Strata `v0.2.10` (engine `0.1.56`) + OMP `18.16.0`
  `IQ3_S` `262K` current PRO profile:
  - **Formal verdict (`not entered`):** NInfer resident (`N`) was **not entered** into the formal
    resident comparison because one `W1` structured tool-call smoke emitted the tool call inside
    reasoning and ran to the length limit (a later `10×` smoke-frequency probe passed `10/10` on both
    engines; the formal verdict stands). In `W1`, cold long-context TTFT measured **4.99 / 4.87 s** on
    NInfer vs **7.02 / 7.31 s** on Strata at `64K` and **15.79 / 16.47 s** vs **22.59 / 24.05 s** at
    `200K`, while short `C1` decode measured **252–264 tok/s** on NInfer vs **311–323 tok/s** on
    Strata.
  - **Exploratory scorecard (Strata `A1` / NInfer / Strata `A2`, non-gating diagnostics):** `M1`
    short `C4` aggregate decode **264.2 / 441.7 / 270.8 tok/s (`1.63×`)**; `M2` `64K` `C4` wall
    **34.36 / 23.82 / 34.39 s (`1.44×`)**; `M3` `200K` cold tool-turn TTFT **22.32 / 25.37 / 22.43 s
    (`13.7%` slower)**; `M4` `200K` warm follow-up **2.64 / 2.22 / 3.04 s** (unstable reference); `M5`
    interference stall **3.83 / 0.67 / 3.84 s (`5.7×` lower)**; and `M6` `G24` verified passes/hour
    **115.6 / 95.0 / 118.9 (`20.1%` lower**; `G24` NInfer `15/18` in `568.3 s` vs Strata `15/18` in
    `467.0 s` and `16/18` in `484.4 s`).
  - **RTX 5090-class CPU expert offload (`NINFER_VRAM_BUDGET_MIB=31000` on `rtxpro6000-win-a`, forcing
    `HostExperts`):** every configuration refused at startup with `Device budget cannot hold the
    calibrated runtime and requested Context capacity`, including zero Host context and a minimal
    `C1` / `4K` / `BF16` / no-MTP / no-graphs diagnostic, with `~155 GiB` host memory available; a
    `40,960 MiB` budget also refused, so no offload speed was measured. Upstream needs `~63.3 GiB`
    pinned host RAM for the routed experts, whereas the RTX 5090 host (`rtx5090-win-a`) has `47 GiB`.
    Decision: no Flash-Next lane in `omp-ninfer`; Strata remains the Flash-Next engine on the RTX PRO
    6000 host (`rtxpro6000-win-a`); revisit if upstream's offload planner starts on a 32 GB-class
    budget. Receipt:
    [`2026-11-05-p19-flash-next-and-starvation.json`](measurements/2026-11-05-p19-flash-next-and-starvation.json).

- **EXP-109 — upstream [`#434`](https://github.com/Neroued/ninfer/issues/434) request starvation under
  context pressure reproduced on shipped source `a87de361` across the native RTX 3090 `C2` lane and
  RTX 5090 production image; targeted fix candidate staged in draft
  [`alphastorm/ninfer#93`](https://github.com/alphastorm/ninfer/pull/93) (2026-11-05).** Under the
  preregistered red condition — an admitted request making no token progress for `>= 120 s` while
  concurrent requests progress — the shipped `v0.16.2` engine (`a87de361` on `64d10fbf`) reproduced
  upstream `#434` on both `C2` lanes:
  - **Native RTX 3090 `C2` lane (`rtx3090-win-a`, installed `v0.8.0-qwen38-3090-beta.2`, source
    `a87de361`):** **REPRODUCED** — a `79,989`-token request paused **440.94 s** after `62,464` input
    tokens with zero output or restores while the prime request generated `16,150` tokens and `45`
    fresh requests completed.
  - **RTX 5090 production image (`rtx5090-win-a`, image `a0cbb8a5`, source `a87de361`, production
    serving arguments except a `2 GiB` scratch checkpoint store):** **REPRODUCED** — an admitted
    `79,989`-token request produced its first token **~398.8 s** after admission while the other long
    request streamed and `48` fresh `247`-token requests completed every `~10 s`; it ran only after
    the other request finished.
  - **Upstream [`#378`](https://github.com/Neroued/ninfer/issues/378) Host placement:** not reproduced
    on the native RTX 3090 lane (both Host-fill arms, fill `4` and fill `5`, preserved the conversation,
    at up to `99.995%` peak Host occupancy; the oldest conversation was evicted instead); **INCONCLUSIVE** on the RTX 5090
    (`rtx5090-win-a`, production image `a0cbb8a5`: the client's adaptive fill did not converge within
    its `3,600 s` budget across `12` conversations of `~120K` tokens with fill steps lengthening to
    `~10 min`, so no preservation probe ran); and **not reproduced on either build** on the RTX PRO
    6000 proxy (`rtxpro6000-win-a`, `sm_120`, `NINFER_VRAM_BUDGET_MIB=31000`, `C2` / `BF16` /
    `131,072`-token KV, `20.4 GiB` Host, preregistered fixed fill `5`: peak Host occupancy **99.842%**
    baseline / **99.861%** candidate, and the preserved conversation kept **119,985 of 119,992** /
    **119,981 of 119,988** cached tokens).
  - **Fix candidate and RTX PRO 6000 proxy red/green:** draft
    [`alphastorm/ninfer#93`](https://github.com/alphastorm/ninfer/pull/93) (head `e6ac7b70`, CI green
    on all `8/8` jobs) ports the `a754fcf3` failure-diagnostics subset, the `452c3f5f` recovery-loss
    formula, `#378` Host placement (re-expressed from Saylek-ai `fix/378-host-placement`), and the
    `#434` scheduler pressure owner + bounded service rotation + deferred fresh admission; a real
    liveness defect found in the first scheduler port (refusal retry on a queued fresh-admission
    notification) was fixed with a regression test. On the `rtxpro6000-win-a` RTX PRO 6000 proxy (same
    geometry, Linux `sm_120a` builds of `a87de361` and `e6ac7b70`, clean build provenance), baseline
    `a87de361` was **RED** (an admitted request paused **362.3 s** without progress while `38` fresh
    requests completed); candidate `e6ac7b70` eliminated admitted-request starvation (maximum pause
    **1.28 s**, both long requests completed) and passed **no-pressure parity** (`3/3` greedy prompts,
    output fields and finish reasons byte-identical), **but** two fresh requests were refused with
    HTTP `503` queue timeouts (`180 s` pending timeout) while admission was deferred under sustained
    pressure, so the strict no-failure criterion is **not** met: the fix trades indefinite silent
    stalls for bounded, visible `503`s on new requests during long pressure. Status: in `EXP-112`
    (`E1` [`alphastorm/ninfer#97`](https://github.com/alphastorm/ninfer/pull/97)), the bounded
    fresh-admission rotation window removed those `503`s under pressure (RTX 5090: `0/51` fresh HTTP
    `503` at `E1` `375bb848` and `0/54` at `F2` `bdc665a3`; max fully-paused `3.0 s` / `2.59 s`), and
    `#93` (`e6ac7b70`) was marked merged on 2026-11-10 when fork `main` gained the `F3` merge
    `b871996a` and shipped in `F3` `e0971faf` (`v0.7.0-qwen38-5090-beta.6`, `omp-ninfer` `v0.17.0`).
    Receipt:
    [`2026-11-05-p19-flash-next-and-starvation.json`](measurements/2026-11-05-p19-flash-next-and-starvation.json).

- **EXP-110 — RTX 5090 real-traffic profile, cached/warm TTFT tail causes, and `#58` low-acceptance
  `DFlash2` fallback dropped (`rtx5090-win-a`, 2026-11-10).** Parsed the retained `rtx5090-win-a`
  production request logs (snapshot `20261110T063534Z`: `253` files, `77,842,633` bytes, archive
  SHA-256 `bbd8bb7bca3310e695f79f11b6be5095cfb87cf9d0f17fc46cdf8f0a56ec7c27`; `34,152` events,
  `9,430` completed requests across `543` server instances from `2026-08-25T20:26:22.873Z` to
  `2026-11-09T19:18:39.820Z`, with completions ending `2026-11-04T22:11:53.905Z`; zero overlaps with
  `105` documented RTX 5090 acceptance windows):
  - **Request-wall split and concurrency shift:** in the full `DFlash2 v0100p+` filtered cohort
    (production request logs from runtime `v0.10.0` onward with `DFlash2` speculative decoding,
    excluding diagnostic filenames, deterministic `<= 256`-token or explicit-request-digest probes,
    the historical greedy `8,192–10,240`-token no-tool corpus signature, and acceptance-window
    overlaps: `7,318` of `7,323` requests across `203` recorded client-session digests and `436`
    sessionless requests, `55,988.14 s` summed request wall; `2026-10-04` contributes `5,993/7,318 =
    81.89%`), wall time is **69.42%
    decode**, **28.58% prefill**, **1.43% queue**, **0.18% prepare**, and **0.40% residual**, with
    prompt tokens p50/p90/p99 `48,905 / 94,703 / 109,306.66`, computed tokens `1,129 / 6,027.30 /
    94,973.96` (`91.32%` cached token share), and `>= 1,024`-token outputs (`1,311` requests)
    consuming **77.62%** of decode time (`93.43%` ending in tool calls). In the recent
    `v0.13–v0.16.2` filtered subset (`176` of `180` requests across `4` UTC days, `127` in `v0140p`
    and `49` in `v0160p`, `299.64 s` summed wall), shorter outputs (`p50 / p90 / p99 / max`
    `111.5 / 261.0 / 620.0 / 966` tokens, `0` outputs `>= 1,024`) shift request wall to **31.89%
    decode** (`31.9%`), **50.21% prefill** (`50.2%`), **8.16% queue** (`8.2%`), **3.65% prepare**,
    and **6.09% residual** (prompt p50/p90/p99 `11,801 / 12,932.5 / 19,766.5`, computed `477 /
    11,622.5 / 17,102.5`, `74.58%` cached share).
  - **Overlap, interference slowdown, and stalls:** peer overlap rose from **1.31%** (`96/7,318`
    requests, `0.23%` active wall at `>= 2` requests, `1.612×` matched decode-overlap slowdown p50
    on `60` requests and `1.995×` peer pre-first-token slowdown p50 on `31` requests) in
    `DFlash2 v0100p+` to **25.57%** (`45/176` requests, `25.6%`; `9.80%` active wall at `>= 2`
    requests, `24.44%` decode-window overlap share, `35` requests exposed to a peer's
    pre-first-token window) in `v0.13–v0.16.2`, where raw elapsed decode dropped from **307.37
    tok/s** solo (`130` requests) to **204.62 tok/s** (`18` decode-overlap requests, matched
    elapsed slowdown p50 **1.340×**, active-round **1.230×**, `14` matched) and **171.75 tok/s**
    (`11` peer pre-first-token exposed requests, matched elapsed slowdown p50 **1.560×** / `1.56×`,
    active-round **1.228×**, `8` matched). Zero requests in any cohort intersected a `>= 60 s`
    zero-global-decode window (one historical `15.00 s` intersection occurred on `2026-10-04`), and
    all **180/180** recent completions recorded **0** preemptions, **0** snapshot restores, **0**
    replay restores, **0** replayed tokens, and **0** `paused_ns`.
  - **TTFT distributions and warm-tail attribution:** in `DFlash2 v0100p+` filtered, TTFT
    p50/p90/p99 is **0.750 / 2.583 / 50.392 s** on any cached turn (`n=7,177`), **0.508 / 0.706 /
    1.923 s** on strict-warm turns (`<= 1,024` computed tokens, `n=3,440`), and **3.457 / 10.414 /
    50.606 s** on cold turns (`n=141`). In recent `v0.13–v0.16.2` filtered, cached (`= strict-warm`,
    `n=112`, computed p50 `474`) TTFT p50/p90/p99 is **0.265 / 0.357 / 1.466 s** and cold (`n=64`,
    computed p50 `8,702`) is **3.451 / 4.821 / 5.939 s** (`3.45 / 4.82 / 5.94 s`). In the broad
    `DFlash2` cached top decile (`n=718`, `10,450.752 s` summed TTFT), **94.42%** (`94.4%`) of TTFT
    is logged prefill (`673/718` compute `> 4,096` new tokens: large tool outputs); in the
    historical strict-warm top `1%` (`n=35`, `99.690 s`), **79.33%** (`79%`) is queue/admission
    wait; and in the recent cached/strict-warm top decile (`n=12`, `8.284 s`), **4
    first-after-`server_start` Host-KV restores** (`9.03–35.63 s` after startup, `102–111` computed
    tokens, `632–652 MiB` KV + `186.8 MiB` state H2D in `117.3–119.9 ms`, plus `0.874–1.130 s`
    unlabelled added preparation) account for **84.0%** (`84%`) of top-decile TTFT above the cohort
    median — excluding those four restart restores lowers recent cached TTFT p99 from `1.466 s` to
    **0.376 s**.
  - **`#58` low-acceptance `DFlash2` fallback dropped:** requests averaging `< 3` tokens/round
    (`1 + accepted_tokens / rounds`) account for `324/7,317` requests and **3.45%** of decode time
    (`1,340.01 / 38,864.83 s`; pooled `3.875` tokens/round across `1,798,989` rounds) in `DFlash2
    v0100p+` filtered and `11/176` requests / **6.26%** of decode time (`5.98 / 95.57 s`; pooled
    `4.124` tokens/round across `5,977` rounds) in the recent slice. Under EXP-092's round-cost
    assumption (`MTP3` `14.03 ms` vs `DFlash2` `16.24 ms`, zero switching cost), modelled all-decode
    recovery is **0.469%** (`0.017%` first-three-position proxy, `1.307%` perfect 4-tokens/round
    `MTP3`) in `DFlash2 v0100p+` and **0.851%** (`0.85%`; `0.169%` proxy, `2.525%` perfect `MTP3`)
    recently, below the `>= 3%` design trigger. Decision: drop [`#58`](https://github.com/alphastorm/ninfer/issues/58).
    Receipt: [`2026-11-10-p20-overnight.json`](measurements/2026-11-10-p20-overnight.json).

- **EXP-111 — copyable share of coding-agent output and own-prefix n-gram copy-drafting revival
  declined (`S1` `a05d6e77` / `60a95b0e`, `E5` [`alphastorm/ninfer#94`](https://github.com/alphastorm/ninfer/pull/94)
  `d117bc17` closed and not shipped, 2026-11-10).** Earlier own-prefix copy-drafting spike (`S1`) measurements on the RTX
  5090 (`60a95b0e`, `alphastorm/ninfer` worktree head `a05d6e7790aabb8c7831541ac6aa66422c423575`) showed `+53.434%` (`+53%`) decode on
  synthetic edit turns, `-4.205%` (`-4.2%`) on short Read acknowledgements, and `15/23` byte-identical
  outputs (diverging where copy rounds verified `16` tokens vs `8` neural verify columns, or on
  widened `C2` partners). Under the `EXP-085` powered-screen rule, reviving copy drafting as a
  release feature required `>= 15%` (`×1.15`) pooled session decode speedup on real coding-agent
  transcripts:
  - **Corpus and exact proposer replay:** from a 30-day workstation session census ending
    `2026-11-10T06:07:32.162009Z` (`68,351` assistant records, `68,221` nonempty across `876`
    sessions; **0** local-Qwen/ninfer/Strata turns occurred in the census, so cloud-model turns are
    evaluated as structural proxies), a deterministic sample of **3,000 nonempty assistant turns
    across 649 sessions** (`1,764,539` native-format output tokens tokenized with pinned
    `Qwen/Qwen3.8-27B` revision `37561816e66b5b9153b1b64c10968c18c1e6f4a0`, `tokenizer.json`
    SHA-256 `0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3`) was replayed
    through `S1`'s exact 4-entry/bucket 16/8/4-token hashed suffix proposer (backward extension up
    to `64` tokens, initial minimum match `12`, maximum proposal `15` when `> K=7`, `131,072`-token
    tail-capped prompt capacity) and an adaptive `12 → 24 → 36` backoff variant (raising the minimum
    match after `< 4` accepted copies).
  - **Copyable share and breakdown by kind:** accepted copied tokens cover **20.5413%** (`20.5%`,
    `362,459 / 1,764,539` tokens across `45,495` proposal rounds; `39,475` positive, `6,020` /
    `13.23%` zero-acceptance, `34.48%` `< 4` copies, mean `9.182` positive / `7.967` all; `17.3827%`
    in runs `>= 8` and **14.6983%** in runs `>= 12`; **19.38%** payload-only excluding `11.87%`
    wrapper formatting; 1,000-replicate session-cluster bootstrap 95% CI `18.36–23.11%`) under fixed
    minimum `12`, and **13.2531%** (`13.3%`, `233,857` tokens across `25,626` rounds; `10.14%`
    zero-acceptance, **10.3887%** in runs `>= 12`, **12.68%** payload-only) with adaptive backoff.
    By output kind (fixed / backoff): edit/hashline/patch arguments **39.76% / 31.52%** (`115,315 /
    290,045`), Qwen/tool formatting **29.20% / 17.49%** (`61,147 / 209,423`), other tool arguments
    **23.87% / 11.24%** (`60,264 / 252,429`), bash/eval commands **23.37% / 15.51%** (`63,218 /
    270,486`), write/file-content arguments **17.00% / 10.24%** (`45,431 / 267,203`), visible
    reasoning **3.61% / 1.70%** (`16,823 / 465,861`), and plain text **2.87% / 2.06%** (`261 /
    9,092`).
  - **Pooled session decode projection and decision:** at `EXP-078`'s `4.631` neural tokens/round
    and copy round cost `C = 1.41 → 1.22` neural rounds, pooled decode speedup is
    **1.06664–1.09314×** (`+6.7–9.3%`; bootstrap 95% CI `1.05274–1.08520×` at `1.41` and
    `1.07705–1.11458×` at `1.22`) for fixed min-12 and **1.05484–1.06928×** (`+5.5–6.9%`) for
    backoff (combined **×1.055–1.093**; **1.02958–1.05425×** and **1.01476–1.02812×** with `S1`'s
    `-4.205%` short-Read lookup-toll sensitivity; median session ratio `1.03952×` fixed / `1.02016×`
    backoff at `C = 1.41`, with `87/649` and `59/649` sampled sessions `> +15%`; warm-service
    total-time gain `+5.88–8.81%` fixed / `+4.85–6.56%` backoff, or `+4.04–5.60%` / `+3.34–4.20%`
    under `EXP-059`'s `62.2%` historical agent GPU decode share). Because `×1.055–1.093` is below
    the `15%` bar and copy rounds change outputs (requiring the 1,120-prompt powered screen),
    copy-drafting revival was **declined** and not shipped in `v0.17.0`; the rebased default-off
    `E5` branch (`--ngram-draft-tokens 0|15`, default `0`) in
    [`alphastorm/ninfer#94`](https://github.com/alphastorm/ninfer/pull/94) (`d117bc17`, CI green; a GPU
    token-identity golden test fixture was prepared and deferred) was closed unmerged. Receipt:
    [`2026-11-10-p20-overnight.json`](measurements/2026-11-10-p20-overnight.json).

- **EXP-112 — upstream [`#434`](https://github.com/Neroued/ninfer/issues/434) request starvation on
  `rtxpro6000-win-a` and `rtx5090-win-a`: production controls vs E1 in
  [`alphastorm/ninfer#97`](https://github.com/alphastorm/ninfer/pull/97) (shipped in RTX 5090
  `v0.7.0-qwen38-5090-beta.6` / `F3` `e0971faf` in `omp-ninfer` `v0.17.0`, 2026-11-10).** In `EXP-109`, draft
  [`alphastorm/ninfer#93`](https://github.com/alphastorm/ninfer/pull/93) (`e6ac7b70`) eliminated
  admitted-request starvation on the `rtxpro6000-win-a` proxy (`362.3 s → 1.28 s` max pause) but kept
  fresh admission closed under sustained rotation, causing HTTP `503` pending-timeout refusals (`180 s`
  timeout). PR [`alphastorm/ninfer#97`](https://github.com/alphastorm/ninfer/pull/97)
  (slice `E1` of the `2026-11-10` `P20` runtime family across fork PRs
  [`alphastorm/ninfer#95`](https://github.com/alphastorm/ninfer/pull/95)–[`#101`](https://github.com/alphastorm/ninfer/pull/101):
  `#95` `E4` opt-in prefill pacing shipped **default-off**, `#96` `E3` host NFC boundary
  normalization, `#97` `E1` `#434` starvation and bounded fresh-admission rotation window, `#98`
  `E2` serve robustness, `#99` integration `F` `a3fa0550`, `#100` `E1` source-wait probe closed
  unmerged and tracked in [`alphastorm/ninfer#102`](https://github.com/alphastorm/ninfer/issues/102),
  and `#101` council-remediated `F2` `bdc665a3` / `F3` `e0971faf`, shipped as RTX 5090
  `v0.7.0-qwen38-5090-beta.6` in `omp-ninfer` `v0.17.0` on 2026-11-10) was measured against
  same-window controls on both `sm_120` hosts (model `81f924d4`, unchanged `EXP-109` client harness
  `46dc58d4d7eee545e3df46785c9f3a7261c38a6e6062a068f36d7b699e8d2d74`):
  - **RTX PRO 6000 proxy (`rtxpro6000-win-a`, Release `sm_120a`, GNU `13.3` / NVCC `13.4.92`, `C2`,
    `BF16`, `131,072` KV, `21,881,405,440` B Host, `chunk 1,024`, `31,000 MiB` VRAM budget,
    `180,000 ms` pending timeout, `24,576 MiB` checkpoint store):** same-session control `e6ac7b70`
    (`e6ac7b709a1a3f94fbbcd6529ce87e813d20cd09`, binary SHA-256 `8235ada432dda4f2a6b8a65c308ed7b23d28260b06a5f10689b2d5805a5de79c`)
    recorded **1.327120366 s** max fully-paused interval, **1.618474534 s** max subsequent output gap /
    max admitted pause, **6** fresh HTTP `503` queue timeouts, and only **1/2** long holders
    completing normally within `600 s` (`holder0`:
    `79,992` prompt / `40,000` output tokens, `output_limit`; `holder1`: `79,997` prompt / `27,288`
    output tokens, `cancelled` at the observation horizon). Candidate `df7aeb52`
    (`df7aeb526ad344ea9bc9fbba0e7bd719aa5dab3b`, binary SHA-256 `c46c67d1381e1a6a322297f533a7b413adb0c2d7e94f5e4e1532dfde00ed616e`)
    passed all gates: **2.086055400 s** max fully-paused interval, **2.266069104 s** (`2.27 s < 5 s`)
    max admitted pause, **0** HTTP `503` timeouts, **2/2** long holders completing normally within
    `600 s` (`holder0`: `79,993` prompt / `40,000` output tokens, `output_limit`; `holder1`: `79,998`
    prompt / `36,190` output tokens, `stop_token`), **3/3** byte-identical no-pressure greedy parity
    on both `DFlash2` and `MTP3`, `512`-output real-preemption test suite passing across `none`
    (`56.326 s`), `MTP` (`33.091 s`), and `DFlash2` (`35.466 s`, test ELF SHA-256 `dd9dbbe6...`), and
    CI green across `Linux 45/45`, `MSVC 24/24`, `sm_86`/`sm_89`, and `RDC`.
  - **RTX 5090 real card (`rtx5090-win-a`, production serving vector `62dba03b`: `C2`, `BF16`,
    `131,072` context, `146,368` automatic KV tokens, `chunk 1,024`, `DFlash2 K=7`, `20,867.734375
    MiB` Host, `2,048 MiB` isolated scratch checkpoint quota):** production control `a87de361`
    (image `a0cbb8a5`, binary SHA-256 `cc99a46097b6da5f9ec3ce671a7818d29754013ba520800f756110b9211bb06e`,
    run `production-exp109-01`) recorded **367.9977688699946 s** (`368.0 s`) admitted `paused_wait_s`
    (**368.62261531799595 s** `max_admitted_scheduler_pause_s`), **1/2** long requests completing
    (`80,000` prompt / `40,000` completion tokens `output_limit` vs `79,991` prompt / `19,392`
    completion tokens starved and `cancelled` at `600 s`), **0/54** fresh HTTP `503` (`54/54`
    completed), and fresh TTFT p50/p95/p99/max **0.292190 / 0.535915 / 38.336270 / 43.863092 s**
    (`0.29 / 0.54 s` p50/p95). E1 candidate `375bb848` (`375bb8483790ce6271e957318967f9a16b8c9833`,
    tree `2bb7b6022eefaf71286c672aba4718220f068fd8`, built in pinned release builder `e7f34ca2` with
    CUDA `13.1.2` / cuBLAS `13.2.2.2-1` ABI match, binary SHA-256 `7f9881546d541f7a39e72351ee60d78db47b7a358ff658f2984296d869c96ae0`,
    run `e1-exp109-01`) **PASSED**: max fully-paused interval **2.9986773779965006 s** (`3.0 s <
    5 s`), max pause-to-recovery **3.2083587239976623 s** (`3.2 s` across `234` scheduler pauses),
    **2/2** long requests completing all `40,000` tokens (`output_limit` on `79,987`- and
    `79,992`-token prompts at `337.50` and `112.69 tok/s` server decode; max post-first progress gap
    `3.616254 s` and `1.543345 s`), **0/51** fresh HTTP `503` (`50` completed before horizon), and
    fresh TTFT p50/p95/p99/max **0.400092 / 3.392509 / 42.073154 / 45.226411 s** (`0.40 / 3.39 s`
    p50/p95 — fresh arrivals wait for a bounded rotation window instead of starving admitted long
    requests or failing with HTTP `503`). Status: shipped in RTX 5090 `v0.7.0-qwen38-5090-beta.6`
    (`F3` `e0971faf`, `omp-ninfer` `v0.17.0`, published 2026-11-10) via
    [`alphastorm/ninfer#97`](https://github.com/alphastorm/ninfer/pull/97) and
    [`#101`](https://github.com/alphastorm/ninfer/pull/101). Receipt:
    [`2026-11-10-p20-overnight.json`](measurements/2026-11-10-p20-overnight.json).

- **EXP-113 — cold `130K` prefill/decode interference (`EXP-077`) on `rtxpro6000-win-a` and
  `rtx5090-win-a` (production `a87de361` and E1 candidate `375bb848`, 2026-11-10).** Re-evaluated
  `EXP-077`'s two-request `C2` interference scenarios (`130,084` cold prompt tokens, `0` cached, long
  fixture SHA-256 `8dcece5215805293490baa0d8204d59a899d8bc3f9d010b0c142ed6624260a9a`, `chunk 1,024`,
  `DFlash2 K=7`; historical `v0.9` `MTP3` `71,641`-token baseline was `30.3 tok/s` co-resident
  decode, `479 ms` gap p99, and `26.7 s` arrival TTFT) under the preregistered pacing design trigger
  (`co-resident decode < 100 tok/s OR arrival-during-prefill TTFT > 5 s`):
  - **RTX PRO 6000 proxy (`rtxpro6000-win-a`, `e6ac7b70` `8235ada4`, config `f8d99fb9`, `31,000 MiB`
    budget, `4,096 MiB` scratch checkpoint quota, `3` fresh-server cold repeats per scenario):** in
    prefill-arriving-during-decode (`PDD`), median strict-overlap co-resident decode is **6.375002
    tok/s** (`6.375 tok/s`; repeats `6.375002 / 6.325025 / 6.649358 tok/s`; full-A decode
    **20.387571 tok/s**), inter-output-event gap p50/p99 is **350.569854 / 469.988615 ms** (`350.6 /
    470.0 ms`), and `130K` long TTFT / total wall is **46.349826 / 46.491205 s** (`46.5 s`; server
    prefill **44.226679 s**). In decode-arriving-during-prefill (`DDP`, gated at first published
    `running/prefilling` status `+ 1.000 s`), median arrival TTFT is **0.803794 s** (`0.804 s`;
    repeats `0.806369 / 0.801931 / 0.803794 s`, engine queue wait `0.222255 / 0.209529 / 0.219058
    s`, `3/3` HTTP admission proven before long first output), with long TTFT / wall **45.514373 /
    45.637334 s**. Trigger on proxy: **TRUE** on co-resident decode (`6.375 < 100 tok/s`), **FALSE**
    on arrival TTFT (`0.804 < 5 s`).
  - **RTX 5090 real card (`rtx5090-win-a`, `146,368` auto `BF16` KV, `2,048 MiB` isolated scratch
    checkpoint quota, frozen reducer `5da11604`):** on production `a87de361` (`cc99a460`, `6/6`
    valid cold rows, `production-exp077-cold-01`, with arrival submitted at long HTTP admission `+
    ~5.15 s` offsets `5.148507 / 5.148274 / 5.149912 s`), median co-resident decode is **5.109089
    tok/s** (`5.11 tok/s`; full-A **16.116528 tok/s**), overlapping gap p50/p99 is **430.325104 /
    618.715558 ms** (`430 / 619 ms`), staged-prefill arrival TTFT is **23.071937 s** (`23.07 s`),
    `PDD` long TTFT / wall is **59.675320 / 59.960177 s**, and `DDP` long TTFT / wall is **59.136636 /
    59.473603 s** (`~60 s`; trigger **TRUE** on both rate and arrival). On E1 candidate `375bb848`
    (`7f988154`, `5/6` valid cold rows in `e1-exp077-cold-01` — `2/3` valid arrival samples
    `20.341783 s` and `21.657426 s` plus `1` invalid late sample `52.519997 s` retained without
    retry), median co-resident decode is **5.127272 tok/s** (full-A **16.186026 tok/s**), gap
    p50/p99 is **405.190917 / 618.392636 ms**, qualified arrival TTFT is **20.999604 s** (`21.00 s`),
    and `PDD` / `DDP` long wall is **59.891799 / 59.165644 s**. Follow-up `EXP-118` subsequently
    verified that the `23.07 s` arrival wait persists at the shipped `24,576 MiB` checkpoint quota
    (`23.073498 s`, `19.49–23.72 s` retained-preferred-source wait), while `EXP-119` measured the
    opt-in prefill-pacing curve in fork PR
    [`alphastorm/ninfer#95`](https://github.com/alphastorm/ninfer/pull/95). Receipt:
    [`2026-11-10-p20-overnight.json`](measurements/2026-11-10-p20-overnight.json).

- **EXP-114 — `C2` pair-round `K=6144`, `T=16` Q5 mixer outputs already run on small-T tensor-core
  sliced-K, closing `EXP-092`'s open half (`rtxpro6000-win-a`, 2026-11-10).** In `EXP-092`, `v0.11.0`
  (`1302d639`) shipped the single-launch 24-head `BF16` 8-column verify attention (`344850b3`) but
  omitted experimental commit `3a2fadbd` (which moved a two-request `DFlash2 K=7` pair's `64`
  `K=6144`, aggregate-`T=16` `LinearAdd` mixer-output calls from an `80`-CTA prompt GEMM at
  `53.6 µs/call` / `3.43 ms/round` to the small-T tensor-core kernel at `22.1 µs/call` / `1.41
  ms/round`). An Nsight Systems `2026.3.2.476` capture on `rtxpro6000-win-a` (`e6ac7b70` `8235ada4`,
  config `f8d99fb9`, `sm_120a`, CUDA `13.4.92`) of a complete `C2` NVTX `decode` range (membership
  payload `2`, CUDA graph `71`, **743** kernel launches across `47` specializations, **17.838570 ms**
  summed kernel time, **17.835578 ms** GPU span, **18.353995 ms** host range) showed that on the
  `64d10fbf` rebase lineage all **64** `K=6144`, `T=16` residual-add mixer calls already dispatch to
  `q5_a16_sliced_k_mma_kernel<Q5A16SlicedKMmaSchedule<16,16,8,2,...,6144,16,...>,...,LinearResidualAddEpilogue,...>`
  (`320×1×1` CTAs, `256×1×1` threads) at mean **19.767594 µs/call** (`19.77 µs`, median **19.776
  µs**, range `19.264–20.223 µs`), totaling **1.265126 ms/round** (`1.27 ms/round` vs `EXP-092`'s
  `1.41 ms` target), with zero `80`-CTA prompt-GEMM mixer calls remaining. Decision: no `3a2fadbd`
  port needed; `EXP-092`'s open pair-mixer half is closed. Receipt:
  [`2026-11-10-p20-overnight.json`](measurements/2026-11-10-p20-overnight.json).

- **EXP-115 — native configuration probes rejected on `v0.16.2` (`a87de361`): RTX 3090
  `--gpu-keep-warm-ms 60000` (`rtx3090-win-a`) and RTX 4090 `--prefill-chunk 2048` (`rtx4090-win-a`,
  2026-11-10).** Tested two configuration-only candidates on the installed `v0.8.0-beta.2` native
  Windows binaries (`a87de3613c17bced777b446fb545f872d8395ec1`, model `81f924d4`):
  - **RTX 3090 `--gpu-keep-warm-ms 60000` (`rtx3090-win-a`, binary SHA-256
    `15a4db46db09dce695f1c55a9996b30408fa93ed864d881872f9ae7306fbab0f`, `350 W` serving cap / `370 W`
    restored, ABBA fresh servers, `6` post-idle observations per arm/delay across `163–226`-token
    prefix-cold prompts with immediate controls on both sides):** probed whether enabling keep-warm
    with the compiled `sm_86` `3.5/10 ms` spin pattern holds `P2` and keeps post-idle TTFT within
    `<= 1.10×` of back-to-back controls (to address the waived `v0.16.2` sibling position 1 `base`
    `0.4975294 s` vs `0.2144353 s` incumbent TTFT). With keep-warm on (`B`) vs off (`A`), the card
    still stepped down from NVIDIA performance state `P2` to **`P5` at `12 s`** (`B` `P2` occupancy
    `7.4%`, held watts `34.7 → 72.6 W`, `+37.9 W`) and **`P8` at `30 s` and `58 s`** (`B` `P2`
    occupancy `1.8%` and `1.1%`, held watts `10.0 → 29.8 W` / `+19.8 W` and `9.8 → 25.2 W` / `+15.4
    W`), and aggregate median post-idle TTFT / back-to-back measured **0.5456 / 0.4173 s** at `12 s`
    (`B` median per-observation paired ratio against adjacent back-to-back controls **1.364×** vs `A`
    `0.6716 / 0.4181 s`, prefill `0.4425` vs `0.5067 s`), **0.5667 / 0.4199 s** at `30 s` (**1.362×**
    vs `A` `0.6617 / 0.4219 s`, prefill `0.4044` vs `0.4914 s`), and **0.6501 / 0.4212 s** at `58 s`
    (**1.521×** vs `A` `0.6435 / 0.4208 s`, prefill `0.4817` vs `0.4697 s`), failing the `<= 1.10×`
    gate at every delay (`27/27` matched positions byte-identical, peak board draw `328.02 W <= 350
    W`). Holding `P2` on `sm_86` requires building and qualifying a different spin pattern.
  - **RTX 4090 `--prefill-chunk 2048` (`rtx4090-win-a`, binary SHA-256
    `ffee91bf17c261ae9b85791fc52528f7f1ef5c985c4d55feb7ee65174c96c73d`, `450 W`, `131,072` `INT8`
    `C1`, `+2` extra slots, ABBA fresh servers against shipped `chunk 1024`):** `chunk 2048` fits
    with **848.00 MiB** available after startup (`1,008.00 MiB` at `1,024`, passing `>= 640 MiB`),
    but `benchmark_c1` (`4,541` prompt / `1,024` completion) prefill rose only **2,122.99 → 2,173.11
    tok/s (`×1.0236 < 1.04`)**, `retrieval130048` (`130,048` tokens, exact in both) prefill rose only
    **1,562.57 → 1,585.82 tok/s (`×1.0149 < 1.04`)**, `benchmark_c1` decode regressed **254.40 →
    224.33 tok/s (`×0.8818 < 0.98`)** (`role84` decode `174.67 → 174.85 tok/s`, `×1.0011`), and
    cross-arm `role84` byte identity was **44/84** (`84/84` within each arm; `40` `role84` cases plus
    `benchmark_c1` changed outputs, which would require a full 1,120-prompt powered quality screen
    for `<= 2.36%` prefill gain). Decision: reject both; shipped native profiles remain unchanged.
    Receipt: [`2026-11-10-p20-overnight.json`](measurements/2026-11-10-p20-overnight.json).

- **EXP-116 — native `rk4v4` ([`#60`](https://github.com/alphastorm/ninfer/issues/60)) true-cold
  restore token-32 divergence reclassified as oracle prefill geometry on `rtx3090-win-a`
  (2026-11-10).** In `EXP-107`, native `rk4v4` 4-bit KV on the RTX 3090 (`262,144`-token `C1`,
  `3,093` prompt tokens: `3,066` cached + `27` computed) diverged from an ordinary `chunk 1,024`
  zero-reuse cold run at **token 32** (`3635` restored vs `48117` cold) despite byte-exact CPU page
  inversion (`55,050,240` B, SHA-256 `53e8f8bc`). On `rtx3090-win-a` (diagnostic source `f6ed4381`,
  `f6ed4381a991aee0b9c3db6aa3a7a4012e2393fb`), a three-way geometry control compared (1) `rk4v4`
  restored (`3,066` cached + `27` computed), (2) ordinary `chunk 1,024` cold (`3,093` computed, `0`
  cached), and (3) **geometry-matched cold** (`3,093` computed, `0` cached, replaying the restored
  arm's `3,066` capture split and speculative suffix prefill chunks of **18, 2, 3, and 4 tokens** at
  bases `3066, 3084, 3086, 3089`), alongside the same three arms on `int8-group64` (`INT8`):
  - **Result:** `rk4v4` restored vs ordinary `chunk 1,024` cold reproduced the `31/32` mismatch at
    token `32` (`3635` vs `48117`), whereas **`rk4v4` geometry-matched cold matched the restored run
    `32/32` tokens** (both emitting token `32` = `3635`, with tokens `1..31` identical across all six
    `rk4v4` and `INT8` arms). Seed-to-restored GPU transport is **byte-exact** for canonical KV and
    the continuation-selected `StateImage`, all three `3,093`-token prompt ledger hashes match, and
    the `INT8` control is **32/32 three-way identical** (`48117` at token `32`).
  - **Disposition:** `#60` is **oracle prefill geometry** (`oracle_geometry_explains_token_mismatch`),
    not a checkpoint-transport or `rk4v4` kernel defect. Adopting a geometry-matched true-cold
    durability oracle (followed by one non-instrumented RTX 3090 exact-token hold and RTX 4090
    fit/quality/release qualification to unlock RTX 4090 `C2` and `262,144`-token native context) is
    deferred to a founder product-contract decision; `--kv-dtype rk4v4` remains off in shipped
    profiles. Receipt:
    [`2026-11-10-p20-overnight.json`](measurements/2026-11-10-p20-overnight.json).

- **EXP-117 — host-side TTFT probes: `11.06×` NFC boundary normalization in
  [`alphastorm/ninfer#96`](https://github.com/alphastorm/ninfer/pull/96) (shipped in RTX 5090
  `v0.7.0-qwen38-5090-beta.6` / `F3` `e0971faf` in `v0.17.0`), Jinja `.strip()` skipped,
  and small-T module preload measured `N/A` (2026-11-10).** Evaluated three community
  (`iamwavecut/ninfer-all`) host/startup TTFT candidates on fork base `e6ac7b70`
  (`e6ac7b709a1a3f94fbbcd6529ce87e813d20cd09`), landing the accepted change in
  [`alphastorm/ninfer#96`](https://github.com/alphastorm/ninfer/pull/96) (`6f1ae8d26bbd5c6120cf2a2a7be087481b3d5d82`,
  slice `E3`, shipped in RTX 5090 `v0.7.0-qwen38-5090-beta.6` from fork source `F3` `e0971faf` in
  `omp-ninfer` `v0.17.0` on 2026-11-10):
  - **NFC boundary-segmented normalization (`4f8d324ab78219fb7174a740170ea18a80d1b23a`, tree
    `2523523c`) — ported in candidate `6f1ae8d2`:** normalizes UTF-8 text only between NFC boundary
    properties (`src/text/unicode.cpp`) while preserving Hangul V/T exclusions, bundled `utf8proc`
    flags (`STABLE|COMPOSE`), and `std::find_if` fast ASCII prefix search. In preregistered ABBA host
    microbenchmarks (Apple M5 Max, 36 GiB, `arm64`, AppleClang 21 `-O3 -DNDEBUG`, `5` warmups + `31`
    timed samples/arm), NFC normalization over a `507,749`-byte technical document (`39,469`
    non-ASCII bytes) dropped from **5.147875 ms** (`[4.865750..5.370875]`, `5.15 ms`) to **0.465583
    ms** (`[0.456584..0.470833]`, `0.47 ms`, **-90.96% / 11.06×** faster; a single local combining
    sequence maps `3` bytes vs `500,003` on base), and a `507,749`-byte ASCII control dropped from
    **0.065500 ms** (`[0.065333..0.066417]`) to **0.056375 ms** (`[0.056291..0.056417]`, **-13.93%**;
    `500,000`-char conversation render within `1.71%` at `1.162375` vs `1.182208 ms`, `+1.71%`). Matches whole-text
    `utf8proc_map(STABLE|COMPOSE)` on **100,000** deterministic random texts plus fixed
    composition/reordering/singleton/Hangul/NUL cases, passes `test_frontend.cpp` and `9/9` Python
    frontend tests, and agrees byte-for-byte across all **65/65** serialized render results (`56`
    successful prompts + `9` expected errors, SHA-256 `a9e3f2d28cbeede6a22eaba784713c1e675747e383ea7f35bca8fa75039c2f24`)
    and all **564,922/564,922** C++ tokenizer token IDs (SHA-256
    `e6ff96c6a9c7663a00e46b8bdfc9f82b5a9192a46bd061dc3a829f82207efd3a`).
  - **Jinja `.strip()` edge-only decode (`21d8b94757d2ecf0c964f32dab891023a1a0f174`, tree `9811c30e`)
    — skipped:** base `e6ac7b70` already removed the character-vector allocation (`500,004` UTF-8
    decodes for `500,002` characters) and requires complete interior UTF-8 validation by contract
    (rejecting malformed interior sequences).
  - **Small-T attention CUDA module preload (`79d657e0e0f3e0abd27e3d47929349c35110560c`, tree
    `f3e8420e`) — skipped (`N/A`):** base `src/ops/softmax_attention/sources.cmake` compiles one
    shared `INT8` `launch.cu` rather than per-width `small_t_i8_w<N>_h<H>_<input>.cu` modules. In an
    Nsight Systems startup-to-first-use capture on `rtxpro6000-win-a` (`e6ac7b70` `8235ada4`, config
    `f8d99fb9`, `CUDA_MODULE_LOADING=LAZY`, `164,093` CUDA API events across `33` greedy
    `max_tokens=1` requests with `31` proven prefix hits covering every computed width `11..25`), the
    largest single module/lookup API call (`cuLibraryGetKernel` / `cuKernelGetName`) was **0.054462
    ms**, the largest cumulative per-request module/lookup time was **0.668558 ms** (`<= 0.67 ms`,
    below the `>= 20 ms` adoption threshold), and the largest attention launch API call was
    **0.226192 ms** (`0.032022 ms` first-seen). Receipt:
    [`2026-11-10-p20-overnight.json`](measurements/2026-11-10-p20-overnight.json).

- **EXP-118 — RTX 5090 shipped-quota (`24,576 MiB`) `EXP-077` arrival-wait control (`rtx5090-win-a`)
  and retained-preferred-source-wait root cause with
  [`alphastorm/ninfer#100`](https://github.com/alphastorm/ninfer/pull/100) (`rtxpro6000-win-a`,
  2026-11-10).** Tested whether the `23.07 s` RTX 5090 `EXP-077` arrival-during-prefill wait in
  `EXP-113` was an artifact of the `2,048 MiB` isolated scratch checkpoint quota, then localized the
  engine root cause and evaluated the first candidate fix in stacked PR
  [`alphastorm/ninfer#100`](https://github.com/alphastorm/ninfer/pull/100):
  - **Shipped `24,576 MiB` checkpoint quota control on `rtx5090-win-a` (`production-exp077-q24-01`,
    `2026-11-10T09:02:43Z`, production `a87de361` `cc99a460`, `--session-checkpoint-quota-mib 24576`
    on `ext4` as the sole serving-vector change from `production-exp077-cold-01`, `130,110` cold
    prompt tokens, `0` cached, `6/6` valid cold rows, `3/3` valid arrivals, minimum sampled `C:` free
    `313.538410 GiB`):** the arrival wait **persists unchanged** at the shipped quota — median
    arrival-during-prefill TTFT is **23.073498 s** (`23.07 s` vs `23.071937 s` at `2,048 MiB`, delta
    **+0.001561 s**), median co-resident decode is **5.254542 tok/s** (full-A **16.166105 tok/s**),
    overlapping inter-output gap p50/p99 is **430.661417 / 618.893977 ms**, `PDD` long TTFT / wall is
    **59.611182 / 59.710807 s**, and `DDP` long TTFT / wall is **58.620706 / 58.846915 s**. Across all
    `3` arrival repeats, `admission_aggregates` recorded `preferred_reused_tokens = 111`,
    `fallback_reason = "none"`, `revoked_checkpoints = 0`, `queue_wait_s` **19.613795 / 23.927980 /
    22.396278 s**, and `source_wait_seconds` **19.492952 / 23.722483 / 22.305462 s** (`~19–24 s`),
    proving the delay is a **retained-preferred-source wait** rather than a `2,048 MiB` scratch-quota
    artifact.
  - **Candidate fix [`alphastorm/ninfer#100`](https://github.com/alphastorm/ninfer/pull/100)
    (`p20/e1-source-wait`, final head `7f2c71fddb264e2f615c4b5e1425bbe20eaa6d96` stacked on
    `df7aeb526`; CPU red test commit `4d62c6996`; GPU `sm_120a` binary built at `1c5`, SHA-256
    `20782176939d51dfd853cf94ce9f01b69b12c8950079928641a5004de37edaa6`):** in CPU unit tests, busy
    source-wait expired at the `60 ms` allowance (`source_wait` **0.0600276 s**, preferred `3` / root
    compute `4`, `EngineCore` `31/31` + `ResourceManager` PASS) and all CI workflows succeeded
    (`42795274259`, `42795274400`, `42795274269`). On `rtxpro6000-win-a` (`C2`/`BF16`/`DFlash2
    K=7`/`chunk 1,024`/`KV 131,072`/`Host 20,867.734375 MiB`/`quota 4,096 MiB`), however, a `3`-pair
    warm-history GPU reproduction (prior `PDD` with a distinct-system warm fixture followed by cold
    `DDP` on the same server cache, `B` computed `130,084` / cached `0`, `preferred/actual 111`,
    `computed 7`, `fallback none`, `State H2D 0`) measured base `source_wait` **44.750 / 44.859 /
    44.877 s** and candidate `1c5` `source_wait` **44.740 / 44.776 / 44.945 s** (candidate TTFT
    **44.942 / 44.973 / 45.144 s**; binding `42 ms`, transfer `4 ms` vs `44.85 s` queue; serial solo
    digest parity `3/3`). Structural diagnosis: `engine_core.h:2703` reserves resident units before
    the fresh scan; reclaim may occupy the `Native` context slot so `try_admit_one:1893` refuses even
    a re-armed scan, and `poll` (`2720–2722`) then `refresh` (`2723–2725`) does not retry fresh
    admission before running resident work (`alarm` `2631–2640` only sets a flag while earlier
    no-lane/`Pending`/async-reclaim exits bypass budget `2074–2076`). Decision: PR `#100` was closed
    unmerged and not shipped in `v0.17.0` (`F` and `F2`/`F3` untouched), with the structural arrival
    source-wait fix tracked in
    [`alphastorm/ninfer#102`](https://github.com/alphastorm/ninfer/issues/102) to budget every
    retained fresh deferral and retry an expired next/root quote at a context-completion safe
    boundary before another resident reclaim. Receipt:
    [`2026-11-10-p20-overnight.json`](measurements/2026-11-10-p20-overnight.json).

- **EXP-119 — `E4` opt-in prefill-pacing curve on `rtxpro6000-win-a` in
  [`alphastorm/ninfer#95`](https://github.com/alphastorm/ninfer/pull/95) (shipped default-off in
  RTX 5090 `v0.7.0-qwen38-5090-beta.6` / `F3` `e0971faf` in `v0.17.0`, 2026-11-10).** Measured seven
  cold `C2` prefill-pacing arms from
  [`alphastorm/ninfer#95`](https://github.com/alphastorm/ninfer/pull/95) (`p20/e4-pacing`, slice
  `E4`, shipped **default-off** in `F3` `e0971faf` in `omp-ninfer` `v0.17.0`) on `rtxpro6000-win-a`
  (`3` fresh-server
  early-`A`-output proof) against the `e6ac7b70` cold baseline (**6.375002 tok/s** / `6.375 tok/s`
  co-resident decode, **20.387571 tok/s** full-A decode, **350.570 / 469.989 ms** overlap gap
  p50/p99, **0.618558 s** / `0.619 s` arrival TTFT, **46.491205 / 45.483616 s** `PDD` / `DDP` long
  wall):
  - `e4-b95f-off` (pacing flags `0`): co-resident **6.600 tok/s** (`6.599977`, full-A `20.382849`),
    gap p50/p99 **353.964 / 469.881 ms**, arrival TTFT median/worst **0.618 / 0.626 s** (`0.618249 /
    0.626390`), `PDD` / `DDP` long wall **46.400 / 45.358 s** (wall ratios **0.998 / 0.997×**), output
    identity `DIFFERS`, not promoted.
  - `e4-b95f-k1-v2`: co-resident **6.400 tok/s** (`6.399997`, full-A `20.430984`), gap p50/p99
    **352.910 / 469.524 ms**, arrival **0.631 / 0.633 s** (`0.631050 / 0.633349`), long wall **46.247
    / 45.809 s** (**0.995 / 1.007×**), `DIFFERS`, not promoted.
  - `e4-b95f-k2-v2`: co-resident **12.025 tok/s** (`12.024975`, full-A `20.198862`), gap p50/p99
    **16.123 / 471.308 ms**, arrival **0.634 / 0.637 s** (`0.634079 / 0.637384`), long wall **48.561
    / 45.930 s** (**1.045 / 1.010×**), `DIFFERS`, not promoted.
  - `e4-b95f-k4-v2`: co-resident **24.160 tok/s** (`24.159987`, full-A `31.724513`), gap p50/p99
    **14.530 / 395.725 ms**, arrival **0.639 / 0.658 s** (`0.639274 / 0.657990`), long wall **49.825
    / 45.974 s** (**1.072 / 1.011×**), `DIFFERS`, not promoted.
  - `e4-b95f-k8-v2`: co-resident **47.901 tok/s** (`47.900624`, full-A `58.488993`), gap p50/p99
    **14.530 / 320.931 ms**, arrival **0.639 / 0.670 s** (`0.638553 / 0.669607`), long wall **49.703
    / 45.892 s** (**1.069 / 1.009×**), `DIFFERS`, not promoted.
  - `e4-b95f-b250-k16-v2`: co-resident **73.400 tok/s** (`73.399995`, full-A `90.252235`), gap p50/p99
    **14.519 / 249.307 ms**, arrival **0.641 / 0.651 s** (`0.640691 / 0.650999`), long wall **49.945
    / 45.821 s** (**1.074 / 1.007×**), `DIFFERS`, not promoted.
  - `e4-b95f-b500-k32-v2`: co-resident **103.205 tok/s** (`103.204801`, full-A `122.221689`, clearing
    the `>= 100 tok/s` rate bar), gap p50/p99 **14.467 / 265.079 ms**, arrival **0.628 / 0.654 s**
    (`0.627937 / 0.653894`), long wall **49.658 / 45.701 s** (**1.068 / 1.005×**, within `<= 1.15×`),
    `DIFFERS`, not promoted.
  Because corresponding-repeat `C2` outputs differ on every arm (the `e6ac7b70` base itself varies
  across `C2` repetitions) and proxy data alone does not qualify native `C2`, both pacing flags
  shipped **default-off (`0`)** in RTX 5090 `v0.7.0-qwen38-5090-beta.6` (`F3` `e0971faf`, `v0.17.0`)
  and remain off in all shipped profiles. Receipt:
  [`2026-11-10-p20-overnight.json`](measurements/2026-11-10-p20-overnight.json).

- **EXP-120 — `E2` serve robustness (`#446`, `#440`, `#441`, `numerical_failure`, `shutdown`
  stop/join split) in [`alphastorm/ninfer#98`](https://github.com/alphastorm/ninfer/pull/98)
  (`rtxpro6000-win-a`, shipped in RTX 5090 `v0.7.0-qwen38-5090-beta.6` / `F3` `e0971faf` in
  `v0.17.0`, 2026-11-10).** Evaluated
  [`alphastorm/ninfer#98`](https://github.com/alphastorm/ninfer/pull/98) (`p20/e2-serve` on base
  `e6ac7b709a1a3f94fbbcd6529ce87e813d20cd09`, final head `d191fb5738c4df358e7613cd39c8b5b6d13473e2`,
  `apps/ninfer-serve` SHA-256 `88bd22655b461c2f173d5698246309d49c89e5c9360375c807f8dc1b4f7814bc`; CPU
  and live GPU functional proofs executed at `5e73453f218917983fb893541e18a081a6f43392`, serve binary
  `5fd3bdec57eb584d96d9e187076f451a050a53ba67df95a35936a1e7cf4afe13`; slice `E2`, shipped in RTX
  5090 `v0.7.0-qwen38-5090-beta.6` from fork source `F3` `e0971faf` in `omp-ninfer` `v0.17.0` on
  2026-11-10):
  - **Frontend and protocol fixes (`Neroued/ninfer` `#446`, `#440`, `#441`):** (1) `#446`
    (`src/text/tool_arguments.cpp:5`, `src/models/common/qwen/frontend/chat_template.cpp:265`,
    `src/serve/anthropic_messages_response.cpp`) preserves raw input on malformed tool-call history
    and Anthropic tool arguments instead of throwing (`malformed_history_http_status = 200`); (2)
    `#440` (`chat_template.cpp:148,185`) accepts all `7` reasoning-effort tiers against the unchanged
    embedded artifact template (`81f924d4`, tiers `low`, `medium`, `xhigh`, mapping `minimal → low`,
    `high → xhigh`, `max → xhigh`; `high_http_status = 200`); and (3) `#441`
    (`chat_template.cpp:103`, `src/serve/translate.cpp`) ignores effort when thinking is explicitly
    disabled (`disabled_effort_http_status = 200`).
  - **Request-local `numerical_failure` and shutdown stop/join split:** (4) invalid generated rows
    (`NaN`/`Inf`/`OOV` in `src/runtime/contract/execution.h`, `src/runtime/engine/engine_core.h:1184`,
    `src/serve/generation_errors.cpp:101`) retire only the affected request as HTTP `500`
    `numerical_failure` while sibling and subsequent requests remain serviceable (verified by CPU
    regression and GPU `tests/ninfer_sampling_test --nonfinite-only`, ELF `6d5358c8...`, exit `0`);
    and (5) `shutdown` (`engine_core.h:161,2612`, `src/serve/http_server.cpp:710`,
    `apps/serve/main.cpp:103`) cancels active generation before joining HTTP workers and keeps the
    live catalog exportable until final save completes — on `rtxpro6000-win-a`, baseline `e6ac7b70`
    (`8235ada4`) with a resident request at stop failed with `managed final-save deadline exceeded`
    (exit `1`), whereas candidate `5e73453f` (`5fd3bdec`) completed `Stop` in **2.570988 s**
    (`2.571 s`, `complete: true`, `saved: 1`, `refused: 0`, `skipped: 0`) and restored **18** cached
    tokens on restart.
  - **Parity and CI:** CPU `ctest` (`ninfer_engine_core_test`, `ninfer_serve_resilience_test`,
    `ninfer_stop_event_test`) passed `3/3` in `15.14 s`; `MTP3` greedy parity (`6fe9fe7e`, config
    `08223401...`) matched byte-for-byte across all **5/5** cases (`parity-0..2` and `C2`
    `pair-0..1`); and all CI runs on `d191fb57` succeeded (`42777721394`, `42777721650`,
    `42777721269`, Windows job `129700052085`). Receipt:
    [`2026-11-10-p20-overnight.json`](measurements/2026-11-10-p20-overnight.json).

- **EXP-121 — RTX 5090 `DFlash2` `C1` greedy byte-identity oracle on integrated `F`
  (`a3fa0550`, [`alphastorm/ninfer#99`](https://github.com/alphastorm/ninfer/pull/99)) and
  council-remediated `F2` (`bdc665a3` / `F3` `e0971faf`,
  [`alphastorm/ninfer#101`](https://github.com/alphastorm/ninfer/pull/101), shipped as RTX 5090
  `v0.7.0-qwen38-5090-beta.6` in `omp-ninfer` `v0.17.0`) vs production (`rtx5090-win-a`,
  2026-11-10).** Verified exact `DFlash2 K=7` greedy output parity on
  `rtx5090-win-a` (runtime image `a0cbb8a5`, pinned release builder `e7f34ca2`, `sm_120a`, model
  `81f924d4`, production serving vector `62dba03b` excluding binary/config digests) against shipped
  production `a87de361` (`cc99a460`):
  - **Integrated candidate `F` (`f-parity-01`, `2026-11-10T08:40:53Z`,
    [`alphastorm/ninfer#99`](https://github.com/alphastorm/ninfer/pull/99), source
    `a3fa0550cfb67b5dc706359ebca0ed02eb722b7c`, tree `73d0f8a94861be55ed82a41f5256b3c60ed25341`,
    binary SHA-256 `1afbb82d0131a507da77ebc372d95596fc2ce6835a1ee35da0e5d7987610131c`):** `C1` gating
    (`f-parity-01-pc1` vs `f-parity-01-fc1`) **PASSED 3/3 byte-identical** across `request`,
    `content`, `reasoning_content`, `reasoning`, and `finish` on `parity-0`, `parity-1`, and
    `parity-2` (`all_fields_identical: true`); informational `C2` (`f-parity-01-pc2` vs
    `f-parity-01-fc2`, `c2_failure_can_fail_gate: false`) also matched **3/3 byte-identical**.
  - **Council `CR-20261110T083627Z-a3fa0550` and localized remediation in
    [`alphastorm/ninfer#101`](https://github.com/alphastorm/ninfer/pull/101) (`F2` `bdc665a3` / `F3`
    `e0971faf`):** a four-seat critical-review council (`daybreak-blue`, `gemini-argon`, `gpt-astra`,
    `claude-mythos`; packet `b264c256...`, record `9e1ce834...`, subject digest `4a9f56e7...`, ledger
    `48bfa68c...`) reviewed `F` (`a3fa0550`) against shipped `a87de361` (`94` paths, `+4530/-1032`)
    and confirmed one `P1` (`gemini-argon-R1`: a resident pause can trigger a `Pending` durable
    pressure save through the release guard, after which `pause_reclaim_victim` pauses older residents
    and `reserve_resident_units` throws `progress owner cannot obtain its legal unit`, failing the
    `Engine`; this defect shape also exists in shipped `v0.16.2` `a87de361`, where the `180` recent
    production completions that carry scheduling counters show zero preemptions; older requests lack
    those counters) and one `P2` (`daybreak-blue-R1` = `gpt-astra-R1`: a failed
    fresh-admission window did not consume its per-rotation window in `take_fresh_window()`). On
    branch `p20/remediation-r1` ([`alphastorm/ninfer#101`](https://github.com/alphastorm/ninfer/pull/101),
    `5` files, `+142/-7` from `F`), `538f6d92` (`538f6d922`) added red regression tests (`EngineCore`
    `33` pass / `2` new fail with `progress owner cannot obtain its legal unit` + `Scheduler`
    unsuccessful-window regression fail on `F`), `bdc665a3`
    (`bdc665a338dc0ea08478c566db3d1e5514eb0d7c`, `F2`) fixed pending-aware
    `pause_reclaim_victim`/`reserve_resident_units` and `take_fresh_window()` (`EngineCore` `35/35`
    pass, `Scheduler` pass), and `e0971faf` (`e0971faf221204047d5a4ed834e4e298740cee17`, `F3`) added
    explicit `max_tokens` cap `0` to two test-only `advance_prefill` calls in
    `tests/models/qwen3_5/test_native_transactions.cpp:1996,2152` (full RC-shaped build `1,311/1,311`
    Ninja steps in `740.3 s` with apps/tests/benchmarks `ON`; all PR `#101` CI runs `42792113220`,
    `42792113216`, and `42792113378` green; council closed as verified localized remediation at
    `2026-11-10T10:20Z`).
  - **Remediated `F2` (`f2-parity-01`, `2026-11-10T09:42:16Z`, source
    `bdc665a338dc0ea08478c566db3d1e5514eb0d7c`, tree `cc473d295188cfbceac4587623bfd655bb21d334`,
    binary SHA-256 `92f0f636009ab824627084cd724c2eff57e814d40c857772206375083ff4a284`,
    runtime-source-identical to `F3` `e0971faf`):** `C1` gating (`f2-parity-01-pc1` vs
    `f2-parity-01-fc1`) **PASSED 3/3 byte-identical** across all fields on `parity-0..2`
    (`all_fields_identical: true`; informational `C2` waived at `F3` freeze), and `F3` `e0971faf`
    shipped as RTX 5090 `v0.7.0-qwen38-5090-beta.6` in `omp-ninfer` `v0.17.0` (published 2026-11-10).
    Receipt:
    [`2026-11-10-p20-overnight.json`](measurements/2026-11-10-p20-overnight.json).

## Current order

The backlog below is a pool; product sequencing lives in [`ROADMAP.md`](../ROADMAP.md). On the
RTX 5090 lane, DFlash2 K=7 with BF16 KV and two requests in flight replaced MTP3 in v0.10.0, and
the round-cost reductions from EXP-092 (single-launch 8-column verify attention in `1302d639`; EXP-114
later confirmed the `64d10fbf` rebase lineage also dispatches the `C2` pair's `64` `K=6144`, `T=16` Q5
mixer outputs on small-T tensor-core sliced-K at `19.77 µs/call` / `1.27 ms/round`) and EXP-094 (small-T tensor-core Q4 query/key projections) shipped in v0.11.0
(`v0.6.16-qwen38-5090-beta.1`, source `1302d639`, carried through v0.12.2), were ported onto
upstream master `64d10fbf` in v0.13.0 (`v0.7.0-qwen38-5090-beta.2`, source `6d4d0a05`, EXP-097),
shipped from common engine source `2c6f423b` in v0.14.0–v0.15.0 (`v0.7.0-qwen38-5090-beta.3`), and
ship from `26fa28d0` in `v0.16.0` (`v0.7.0-qwen38-5090-beta.4`, `84/84` role-corpus output hashes at
`×0.999282` and post-resume first-fork TTFT cut from `5.03 s` to `0.11 s`, EXP-105) and from
`a87de361` in `v0.16.2` (`v0.7.0-qwen38-5090-beta.5`, bit-identical `661`-artifact / `3`-package
same-path double build and byte-proven durable-generation Host reclaim), `e0971faf` in `v0.17.0`
(`v0.7.0-qwen38-5090-beta.6`, bit-identical `664`-artifact / `3`-package double build, bounded
resume/fresh admission, durable pressure-work waits, serving robustness, and host-side NFC/frontend
rendering), `48c8ac46` in `v0.18.0` (`v0.7.0-qwen38-5090-beta.7`, Device-staged durable
`StateImage` export, operation-free prepare holding, and bounded `K = 4` fresh-admission priority),
and `41f89b31` in `v0.19.0` (`v0.7.0-qwen38-5090-beta.8`, bounded retryable pressure-save refusals in
[`alphastorm/ninfer#122`](https://github.com/alphastorm/ninfer/pull/122)).
On the RTX 4090 and RTX 3090 native Windows lanes, `v0.16.0` (`v0.8.0-qwen38-4090-beta.1` and
`v0.8.0-qwen38-3090-beta.1`, source `26fa28d0` on `64d10fbf`), `v0.16.2`–`v0.17.0`
(`v0.8.0-qwen38-4090-beta.2` and `v0.8.0-qwen38-3090-beta.2`, source `a87de361` on `64d10fbf`),
`v0.18.0` (`v0.8.0-qwen38-4090-beta.3` default and `v0.8.0-qwen38-3090-beta.3` `tc` with `sm_86`
small-T tensor-core verify at `T=8/16`, source `48c8ac46` on `64d10fbf`), and `v0.19.0` (carried
`v0.8.0-qwen38-4090-beta.3` at `48c8ac46` and re-cut `v0.8.0-qwen38-3090-beta.4` `tc` at `15c3e395`
with bounded retryable pressure-save refusals) switch both 24 GB profiles
from MTP3 to **DFlash2 `K=7`** with `INT8` KV, `Q4_G64_FP16` draft MLP `gate`/`up` weights,
host-mapped `token_embedding`, `1,024`-token prefill chunks, two extra device-state slots, and
`Group64` A8 and `FP32` head logits off, while carrying the byte-identical `sm_86`/`sm_89` attention
prefill specializations (+4.96% and +5.40% on 130,048-token retrieval, EXP-100):
- **RTX 4090 (`qwen38-4090-native-v0.8.0-beta.1`, `C1`):** Shorter draft windows `K=6` (`0.8625–0.8642`) and `K=5`
  (`0.8668–0.8673`, EXP-103) and opt-in `--fp32-head-logits` (`0.9016–0.9025`, EXP-104) failed
  `log-024@0` and were rejected, while default `DFlash2 K=7` passed `log-024@0` on the `P16` engine
  (`0.9627–0.9635` on `31583e3f`, `0.96186–0.96294` on `08257eec`), passed 131,072-token `INT8` `C1`
  fit/true-cold (`1,056,964,608` B available, `22,639 MiB` peak, `32/32` tokens), passed `83/83`
  agent-probe parity (`max source_wait <= 0.0178 s`), and passed `15/15` managed qualification
  phases (`254.27 tok/s` `C1` decode vs `151.54 tok/s` in `v0.14.0`, `2,139.14 tok/s` prefill,
  `83.88%` acceptance, `83.35 s` 130,048-token retrieval in `rtx4090.json`, EXP-102).
- **RTX 3090 (`qwen38-3090-native-v0.8.0-beta.1`, `C2`):** Releasing Device `StateImage` replicas to Host before durable export
  (EXP-105) cut first-fork waits from `15.4–17.8 s` TTFT to `<= 0.033 s` wait / `0.33–0.76 s` TTFT,
  and waiting for in-flight exports in `reserve_resident_units()` (EXP-106) resolved the `C2` HTTP
  500 (`oldest resident cannot obtain its legal unit`), allowing RTX 3090 to ship `C2` over one
  shared 131,072-token `INT8` pool (`1.385×` aggregate decode `57.68 → 79.90 tok/s`, `0.722×` pair
  wall `71.01 → 51.26 s`, `0.70–0.73×` concurrent per-request decode, EXP-101, EXP-106), whereas RTX
  4090 `INT8` `C2` at 131,072 tokens was refused at startup.
Native `rk4v4` 4-bit KV (EXP-107) passed held-out perplexity ($\Delta\text{NLL} = 0.00345$) and fit
`262,144`-token `C1` on RTX 3090 (`197.86 / 503.57 s` exact retrieval at `130,048 / 250,062` tokens)
but was deferred after true-cold restore diverged at token 32 (`C1`) and tokens `16–32` (`C2`);
EXP-116 reclassified the RTX 3090 `C1` token-32 divergence (`#60`) as oracle prefill chunk geometry
(`32/32` matched when a cold run replays the `3,066` capture split and suffix chunks `18/2/3/4`,
with byte-exact KV/`StateImage` transport and `32/32` three-way `INT8` control parity), leaving a
geometry-matched durability oracle as a founder decision.
Native `sm_86`/`sm_89` small-T tensor-core decode (`+39.8%` on RTX 3090, `+8.3%` on RTX 4090,
EXP-099) failed the T2 role-divergence gate on both cards and the 150-pair symmetric screen on RTX
3090 (`p = 0.0384`), and `Group64` A8 prefill (`×1.312` / `×1.618` C1, `×1.217` / `×1.366` 130K,
EXP-100) failed the 200-pair symmetric leak screen on RTX 4090 (`p = 1/32 = 0.03125`; RTX 3090
passed at `p = 1/16 = 0.0625` on four of the same five prompts and was kept off by founder
decision); both routes stay compiled off. EXP-095 compared the superseded fork candidate `a59c13d0`
against upstream `81c8ce09` in a local fixed-KV rehearsal — not the selected `1302d639` runtime —
before the [v0.13.0–v0.14.0 rebases](UPSTREAM.md#v0130-sync-program) re-ported the durable store
and kernel routes onto `64d10fbf` (EXP-097: 101.09% median role-corpus decode vs `1302d639` on RTX
5090; all three lanes unified at `2c6f423b` in `v0.14.0`, `26fa28d0` in `v0.16.0`, and `a87de361` in
`v0.16.2`). In post-`v0.16.2` research (EXP-108, EXP-109 in
[`2026-11-05-p19-flash-next-and-starvation.json`](measurements/2026-11-05-p19-flash-next-and-starvation.json)),
`Qwen3.8-Flash-Next` on upstream `a754fcf3` did not enter the formal rule-30 screen on
`rtxpro6000-win-a` and refused `31,000` / `40,960 MiB` `HostExperts` budgets at startup, while
upstream `#434` context-pressure starvation reproduced on both shipped `C2` lanes (`440.94 s` pause
on native RTX 3090 and `~398.8 s` TTFT on RTX 5090) and on the `rtxpro6000-win-a` proxy (`362.3 s`
pause), where draft [`alphastorm/ninfer#93`](https://github.com/alphastorm/ninfer/pull/93)
(`e6ac7b70`) eliminated admitted-request starvation (`1.28 s` max pause) while trading indefinite
silent stalls for bounded HTTP `503` queue timeouts (`180 s` pending timeout) on deferred fresh
arrivals. In the 2026-11-10 overnight measurement campaign (`EXP-110`–`EXP-121` in
[`2026-11-10-p20-overnight.json`](measurements/2026-11-10-p20-overnight.json)), production-log analysis
on `rtx5090-win-a` (`9,430` completions, EXP-110) dropped the [`#58`](https://github.com/alphastorm/ninfer/issues/58)
low-acceptance `DFlash2 → MTP3` fallback (`0.469%–0.851% < 3%` decode recovery) and identified `C2`
prefill/decode interference (`25.57%` overlap, `1.560×` median matched decode slowdown on `8`
requests overlapping a peer's pre-first-token window in recent `v0.13–v0.16.2` traffic)
as the top real-traffic runtime lever; a 3,000-turn coding-agent replay (EXP-111) declined reviving
own-prefix n-gram copy drafting (`20.5413%` fixed / `13.2531%` backoff copyable output share,
`×1.055–1.093` pooled session decode `< 1.15` bar; `E5` copy-drafting PR
[`alphastorm/ninfer#94`](https://github.com/alphastorm/ninfer/pull/94), `d117bc17`, declined,
closed, and not shipped); runtime changes across fork PRs `alphastorm/ninfer#95`–`#99` and `#101`
— shipped in RTX 5090 `v0.7.0-qwen38-5090-beta.6` (`omp-ninfer` `v0.17.0`, published 2026-11-10)
from fork source `F3` `e0971faf` = integration `F` `a3fa0550` (`#99`: `#97` `E1` `#434` bounded
fresh admission, `#98` `E2` serve robustness, `#96` `E3` NFC, and `#95` `E4` prefill pacing shipped
**default-off**) + council remediation `#101` (`F2` `bdc665a3` / `F3` `e0971faf`), while carried
native `v0.8.0-beta.2` packages stayed at `a87de361` (with RTX 3090's native post-route compaction
campaign failure founder-waived with disclosure in `v0.17.0`, tracked in
[`alphastorm/ninfer#89`](https://github.com/alphastorm/ninfer/issues/89), and product tooling
follow-ups in [`alphastorm/omp-ninfer#149`](https://github.com/alphastorm/omp-ninfer/issues/149)) —
verified that `E1` ([`alphastorm/ninfer#97`](https://github.com/alphastorm/ninfer/pull/97), EXP-112)
resolves both `#434` starvation and fresh-request `503` timeouts on `rtxpro6000-win-a` (`df7aeb52`:
`2.27 s` max pause, `0` HTTP `503` vs `6` on `e6ac7b70` control, `2/2` long complete, `3/3`
`DFlash2` and `MTP3` greedy parity) and `rtx5090-win-a` (`375bb848`: `3.0 s` max fully-paused
interval vs `368.0 s` production control, `2/2` long complete, `0/51` HTTP `503`), that `E2`
([`alphastorm/ninfer#98`](https://github.com/alphastorm/ninfer/pull/98), `d191fb57` / `5e73453f`,
EXP-120) resolves `#446`/`#440`/`#441`, request-local HTTP `500` `numerical_failure` recovery, and
managed final-save shutdown (`2.571 s` `Stop`, `18` cached tokens restored vs base deadline timeout;
`5/5` `MTP3` parity), that `E3`
([`alphastorm/ninfer#96`](https://github.com/alphastorm/ninfer/pull/96), `6f1ae8d2`, EXP-117) speeds
up `507,749`-byte non-ASCII NFC normalization `11.06×` (`5.15 → 0.47 ms`, `65/65` serialized results
and `564,922` token IDs identical; Jinja `.strip()` and small-T module preload `<= 0.67 ms` skipped),
that `E4` ([`alphastorm/ninfer#95`](https://github.com/alphastorm/ninfer/pull/95), EXP-119) scales
proxy co-resident decode from `6.375` to `103.205 tok/s` (`--prefill-stall-budget-ms 500
--decode-rounds-per-prefill 32`, `b500-k32-v2`, `1.068×` prefill-during-decode `PDD` long wall)
with changed `C2` outputs (shipped **default-off** at `0`), and that integrated `F` (`a3fa0550`,
`1afbb82d`) and council-remediated `F2` (`bdc665a3`, `92f0f636`, runtime-identical to `F3`
`e0971faf` after fixing council
[`CR-20261110T083627Z-a3fa0550`](../releases/v0.17.0/review/runtime-ledger.json)'s severity-`P1`
pending-pressure-save `pause_reclaim_victim`/`reserve_resident_units` engine failure and
severity-`P2` `take_fresh_window()` rotation consumption in
[`alphastorm/ninfer#101`](https://github.com/alphastorm/ninfer/pull/101)) both pass `3/3`
byte-identical `DFlash2` `C1` greedy parity against production on `rtx5090-win-a` (EXP-121); cold
`130K` `EXP-077` runs (EXP-113, EXP-118) measured `6.375 tok/s` (`rtxpro6000-win-a`) and `5.11` /
`5.13` / `5.25 tok/s` (`rtx5090-win-a` `2,048 MiB` production / E1 / `24,576 MiB` production)
co-resident decode, confirmed the `23.07 s` RTX 5090 arrival wait persists at the shipped
`24,576 MiB` quota (`23.073498 s`) as a `19.49–23.72 s` retained-preferred-source wait, and showed
stacked [`alphastorm/ninfer#100`](https://github.com/alphastorm/ninfer/pull/100) (`7f2c71fd`, GPU
binary commit prefix `1c5`) did not remove the `~45 s` warm-history GPU proxy reproduction (closed
unmerged and not shipped; tracked in
[`alphastorm/ninfer#102`](https://github.com/alphastorm/ninfer/issues/102)); EXP-114 closed EXP-092's
pair-mixer backlog item; EXP-115 rejected config-only RTX 3090 keep-warm and RTX 4090 `chunk 2048`;
and EXP-116 reclassified `rk4v4` `#60` as oracle prefill geometry. `v0.18.0` (`F4` `48c8ac46`)
subsequently re-cut all three GPU lanes (`v0.7.0-qwen38-5090-beta.7` and
`v0.8.0-qwen38-{4090,3090}-beta.3`), shipping `F3` (`e0971faf`) across both native lanes alongside
Device-staged durable saves ([`alphastorm/ninfer#109`](https://github.com/alphastorm/ninfer/pull/109)),
operation-free prepare holding ([`#111`](https://github.com/alphastorm/ninfer/pull/111)), bounded
`K = 4` fresh-admission priority ([`#108`](https://github.com/alphastorm/ninfer/pull/108) for
[`#102`](https://github.com/alphastorm/ninfer/issues/102)), and `sm_86` small-T tensor-core verify
at `T=8/16` on the RTX 3090 `tc` profile ([`#104`](https://github.com/alphastorm/ninfer/pull/104),
`1.5373×` ABBA decode vs `beta.2`, passing [`EXP-085`](#experiment-ledger) screen `466586d9`), and
`v0.19.0` rebuilt RTX 5090 (`41f89b31`, `beta.8`) and native RTX 3090 (`15c3e395`, `beta.4` `tc`,
identical serve source) with bounded retryable pressure-save refusals
([`#122`](https://github.com/alphastorm/ninfer/pull/122), passing first-attempt RTX 3090 `C2`
acceptance with `0` HTTP `503` responses) while carrying RTX 4090 `beta.3` unchanged from `v0.18.0`.
Open kernel and runtime work targets re-cutting RTX 4090 with bounded pressure saves at the next
engine freeze, deferred pressure-save coordinator residuals
([`alphastorm/ninfer#123`](https://github.com/alphastorm/ninfer/issues/123)) and broader load shapes
under [`alphastorm/ninfer#89`](https://github.com/alphastorm/ninfer/issues/89) (plus `#103`, `#115`,
and `#120`), founder disposition of a geometry-matched true-cold durability oracle for `rk4v4` 4-bit
KV (`262,144`-token native context and RTX 4090 `C2`, EXP-106, EXP-107, EXP-116), `Group64` A8
prefill leak-flip localization (EXP-100), verify-round host-commit idle time (EXP-058, EXP-092),
Q4/Q5 epilogue fusion (EXP-056), warm-turn fragment consolidation (EXP-059), and host-to-device KV
prefetch.

## Ideas backlog

Open, unclaimed, or in-flight. Claim one by opening an issue in
[alphastorm/ninfer](https://github.com/alphastorm/ninfer/issues) titled `perf: <idea>` with your
hypothesis and method before writing code.

| Idea | Why it should work | Status |
| --- | --- | --- |
| Current upstream architecture versus selective backport | Upstream adds schema decoding and preemption, but the matched BF16 role corpus on `81c8ce09` was 251.29 versus the fork's 299.71 tok/s and the automatic C2 budget refused by 561.47 MiB; re-porting the kernel routes and schema 3 durable store onto master `64d10fbf` reached 101.09% median role-corpus decode against `1302d639` (EXP-097) | EXP-095 closed; RTX 5090 rebase shipped in v0.13.0 (`v0.7.0-qwen38-5090-beta.2`, source `6d4d0a05`, EXP-097), native Windows rebase shipped in v0.13.1 (`v0.7.0-qwen38-4090-beta.2` / `v0.7.0-qwen38-3090-beta.2`, source `7a25cd72`), all three lanes ship from common source `2c6f423b` in v0.14.0–v0.15.0, `26fa28d0` in v0.16.0 (`v0.7.0-qwen38-5090-beta.4`, `v0.8.0-qwen38-{4090,3090}-beta.1`), `a87de361` in v0.16.2 (`v0.7.0-qwen38-5090-beta.5`, `v0.8.0-qwen38-{4090,3090}-beta.2`), `e0971faf` on RTX 5090 `beta.6` alongside carried `a87de361` native `beta.2` in v0.17.0, unified `48c8ac46` across RTX 5090 `beta.7` and native `beta.3` in v0.18.0, and `41f89b31` / `15c3e395` on RTX 5090 `beta.8` and native RTX 3090 `beta.4` `tc` alongside carried `48c8ac46` RTX 4090 `beta.3` in v0.19.0 |
| Fuse Q4/Q5 GEMV/MMA epilogues with adjacent normalization | Removes a full activation round trip per layer at decode shapes; EXP-056 measured the target at 297 normalization and gating kernels, 0.47 ms of a 26K RTX 5090 MTP3 round (1.4–1.7 µs each) | open |
| Keep the next MTP3 verify round queued ahead of the host commit | At the round boundary the RTX 5090 idles 302–320 µs per 26K round (1.8–1.9%) while the host commits the round, launches the replay fold, waits for it and spends 235–239 µs of CPU in `cudaGraphLaunch` (EXP-058); the state-pressure demotion needs a compute-stream fence before the host may stop waiting for the fold. DFlash2 K=7 rounds idle 324–350 µs each, 1.4–2.2% of a round (EXP-092) | open |
| Q4 query/key projections on the tensor cores at verify widths | The GDN and attention query/key projections took 1.68 ms of every one-request DFlash2 round (2.67 ms in a pair) on SIMT at 28–31% of DRAM bandwidth, and no byte-identical schedule is faster (EXP-093). On the Q4 small-T tensor-core kernel they take 0.82 ms, rounds are 0.8 ms shorter (1.9 ms in a pair), and the changed outputs pass EXP-085's powered screen (EXP-094) | shipped RTX 5090 v0.11.0 (`v0.6.16`, source `1302d639`; ported into v0.13.0 `v0.7.0-qwen38-5090-beta.2`, source `6d4d0a05`) |
| Run a request's consecutive prefill fragments through each layer together | A production-shaped warm turn runs six full-model passes split at chat-template boundaries; merging the fragments' prompt attention into one launch per layer saves about 27 ms per extra prompt pass at 29K context while each fragment keeps its projection route and GDN decomposition (EXP-059) | open |
| Fold warm-turn template fragments into fewer passes | Four 2–3-token fragments cost 59–60 ms of a 283–307 ms warm turn and the reasoning-block pass runs its projections at 20–25% of peak; six passes to two would take an estimated 115–130 ms off, but needs per-row arithmetic that does not depend on pass width so resumed and cold execution stay bit-identical (EXP-059) | open |
| Hold the RTX 5090 out of its idle P-states when agent requests arrive | 138 of 446 agent requests, including 103 of 106 new sessions, arrive 5 s or more after the previous one, when the card has stepped toward P8; their first prefill pass runs 1.6–2.3× slower and new-session TTFT is 0.36 s against about 0.19 s on a busy card (EXP-060). A single-warp spin holds P1 (EXP-061). Prototyped in the engine as `--gpu-keep-warm-ms` (EXP-062): new sessions after 12–58 s idle at 0.173–0.181 s TTFT, outputs byte-identical, about 71 W above idle while held; a 60 s grace catches 84 of 138 idle arrivals at about 2.3 W average. Shipped in v0.8.2 with a 60 s grace in the RTX 5090 profile | shipped RTX 5090 v0.8.2; RTX 4090 v0.8.4 with sm_89 50 ms/100 ms keep-warm (EXP-066); native RTX 3090 (`sm_86`) config-only keep-warm with the compiled `3.5/10 ms` spin rejected in EXP-115 (`P5`/`P8` drop, `1.362–1.521×` post-idle TTFT ratio; needs a different `sm_86` spin pattern build) |
| Qualify a speculative (MTP) profile on the RTX 4090 lane | Shipped in v0.3.1: MTP3 promoted by the two-arm decision (+17.04% Golden-equivalent wall; 93.2–97.7 tok/s vs 52.330 baseline); exploratory sweep measured draft-3 > 4 > 5 on the fixed workload | shipped v0.3.1 |
| Durable RTX 5090 container (serve-layer session persistence) | Shipped in v0.4.0: transactional generational store + io_uring O_DIRECT restore; 109,589 tokens restored hot across a docker restart ([qualification](../docs/measurements/2026-08-30-rtx5090-durable-qualification.json)) | shipped v0.4.0 |
| Checkpoint replication to shared storage | Delivered 2026-09-05 (EXP-018): `scripts/checkpoint_sync.py` copies verified published generations out and back; origin authentication on every lane; same-profile-pair portability only | completed |
| Template-fork warm starts | Checkpoint immediately after system-prompt+context prefill and fork subagents from that generation for hot starts; operational pattern over the qualified fork contract | open |
| Paged host-to-device KV prefetch beyond 262K tokens | Extends usable context past resident KV capacity without a quality change | open |
| Durable session checkpoints → process-restart continuation | All three lanes bind passing restart evidence: 102K restored continuation on RTX 4090, 310 MB checkpoint restoration on RTX 3090, and a 109K-token hot restore across an RTX 5090 container restart | released on all three lanes |
| MTP depth-and-corpus ablation for Qwen3.8 | Measured on 2026-09-04 with one binary and model per lane and a deterministic 24-request agent corpus; MTP3 won on every lane and repetition | completed; retain MTP3 |
| Deeper MTP drafting (K=7) on 27B | K7 completed on all lanes but trailed MTP3 by 20.17–24.72% | rejected for current artifacts |
| DFlash2 block drafting (K=7) on 27B | One masked-block pass drafts seven tokens. EXP-078 on the RTX 5090: +28.2% role-corpus decode over MTP3 on the same upstream binary, +20.8% to +56.4% at 32K–120K context, prefill unchanged; 1.65 GiB of weights, and two fewer device state slots at two requests. Ported onto the fork: +21.4% role-corpus decode over shipped v0.9.0 at one request (EXP-081), a two-request pair 8.4% above shipped's (EXP-082), sessions on the durable store with exact restores (EXP-083), MTP3 byte-identical. With BF16 KV DFlash2 passed the powered quality screen, 1,091 of 1,120 outputs byte-identical to shipped (EXP-085); NVFP4 KV (four slots, 262,144 tokens, EXP-084) failed it on unsupported claims and secret leaks (EXP-085), and FP8 KV (four slots, 249,216 tokens, EXP-087) on secret leaks (EXP-088). The BF16 profile passed v0.9.0's probes but decodes free-form reasoning 2-5% slower solo and 21-27% slower in pairs, and lost one session's reuse across a restart (EXP-086). One verify attention pass per layer (and, in the experimental stack only, the pair's mixer outputs on the tensor cores) shortens RTX 5090 rounds 8–19% behind 32K–120K tokens and 8% in pairs, byte-identical; K=15 drafting does not pay (EXP-092), and EXP-114 later confirmed the `64d10fbf` rebase lineage already runs the `C2` pair's `64` `K=6144`, `T=16` Q5 mixer outputs on small-T tensor-core sliced-K (`19.77 µs/call`, `1.27 ms/round`), closing EXP-092's open half. The 8- and 16-column Q4 query/key projections on the tensor cores take another 0.8 ms off every one-request round and 1.9 ms off a pair's, with outputs changed but inside EXP-085's powered screen (EXP-094). On the 24 GB native lanes, `EXP-089`'s `W8` link failure is gone on `64d10fbf` and `2c6f423b` carries the `sm_86`/`sm_89` load-time fit seam (`Q4_G64_FP16` draft MLP gate/up + host-mapped `token_embedding`, EXP-098): RTX 3090 passed the 108-role gate on `7a25cd72` (`×1.29968`, min `0.97987`) and the 131,072-token INT8 fit and true-cold durability proof on `e456af37b` (`21,968 MiB` peak, `768 MiB` headroom); RTX 4090 reached `×1.26362` aggregate on `7a25cd72` but failed the `0.95` floor on `log-024@0` (`0.945889`, reproduced at `0.9451`), and shorter windows `K=6` (`0.8625–0.8642`) and `K=5` (`0.8668–0.8673`, EXP-103) plus opt-in `--fp32-head-logits` (`0.9016–0.9025`, EXP-104) were rejected while default `DFlash2 K=7` passed `log-024@0` on the `P16` engine (`0.9627–0.9635` on `31583e3f`, `0.96186–0.96294` on `08257eec`, EXP-104), `K=7` 131K `INT8` fit passed on RTX 4090 (`1,449,132,032` B available on `2c6f423b`, `1,056,964,608` B on `26fa28d0`, EXP-103), and Host export-State materialization removed the 15.4–17.8 s native and 5.03 s RTX 5090 first-fork stalls (`<= 0.033 s` wait / `0.33–0.76 s` TTFT on RTX 3090, `0.106 s` TTFT on RTX 5090, EXP-105) | shipped RTX 5090 v0.10.0 (BF16, two device state slots, 131,520 KV tokens); the single-launch 8-column verify attention subset of EXP-092 plus EXP-094 shipped in v0.11.0 (`v0.6.16`, source `1302d639`, with EXP-092's pair-mixer half confirmed already covered on `64d10fbf` in EXP-114); native `DFlash2 K=7` shipped on both RTX 3090 (`v0.8.0-qwen38-3090-beta.1`, EXP-101) and RTX 4090 (`v0.8.0-qwen38-4090-beta.1`, EXP-102) in `v0.16.0` (`26fa28d0`), and `#58` low-acceptance `DFlash2 → MTP3` fallback was dropped in EXP-110 (`0.469%–0.851% < 3%` decode recovery) |
| Native `C2` shared-pool concurrency and `rk4v4` 4-bit KV (`sm_86`, `sm_89`) | Waiting for in-flight checkpoint exports in `reserve_resident_units()` (`ea2edc20`) resolves the `oldest resident cannot obtain its legal unit` HTTP 500 under shared-pool pressure: on RTX 3090 (`08257eec`, frozen in `26fa28d0`), `INT8` `C2` on a shared `131,072`-token pool (`2` extra device states) passes calibrated two-concurrent `~60K` runs (`6/6` per trial across `3` trials) and reaches `1.385×` aggregate decode (`0.722×` pair wall vs `C1`), while RTX 4090 `INT8` `C2` at `131,072` tokens is refused at startup (EXP-106). Native `rk4v4` 4-bit KV (`17,920` B/token, `47.0%` smaller than `INT8`) passes held-out perplexity ($\Delta\text{NLL} = 0.00345$) and fits `262,144` `C1` on RTX 3090, and EXP-116 proved that its `C1` token-32 true-cold restore divergence (`#60`, EXP-107) is oracle prefill chunk geometry (`32/32` matched when cold replays split `3,066` + suffix `18/2/3/4`, with byte-exact KV/`StateImage` transport and `32/32` three-way `INT8` parity) rather than a restore or kernel defect | shipped RTX 3090 `INT8` `C2` in `v0.16.0` (`v0.8.0-qwen38-3090-beta.1`, `26fa28d0`); RTX 4090 `INT8` `C2` at 131K rejected (needs smaller KV format); `rk4v4` `#60` reclassified as oracle geometry in EXP-116 (geometry-matched durability oracle pending founder decision) |
| Native `sm_86` and `sm_89` small-T tensor-core decode numerics | Small-T tensor-core decode raised C1 decode by +39.8% on RTX 3090 (`84.42 → 117.98 tok/s` at 300 W; `90.79 → 126.81 tok/s` at 350 W) and +8.3% on RTX 4090 (`151.23 → 163.76 tok/s` at 450 W), but diverged on 55/84 and 58/84 role cases (T2 bar `<= 8`) and failed the 150-pair symmetric screen on RTX 3090 added secret fingerprints (`p = 0.0384`, EXP-099); in v0.18.0 (`alphastorm/ninfer#104`), `sm_86`/`sm_89` small-T tensor-core verify at `T=8/16` under DFlash2 K=7 passed the full 1,120-prompt EXP-085 screen on RTX 3090 (`466586d9`, `1.5373×` weighted ABBA decode, `227.17 tok/s` C1 decode) and re-cut as `native-v0.8.0-beta.4-tc-rtx3090` in v0.19.0 (`227.19 tok/s` C1 decode, `80/80` + `84/84` byte-identical to `beta.3` `tc`) | rejected for v0.14.0 MTP3 (EXP-099); shipped on RTX 3090 `tc` (`native-v0.8.0-beta.3-tc-rtx3090` in v0.18.0, `native-v0.8.0-beta.4-tc-rtx3090` in v0.19.0); default-off on RTX 4090 |
| Native `sm_86` and `sm_89` `Group64` A8 prefill leak-flip localization | `Group64` A8 prefill speeds up C1 prefill `×1.312` on RTX 4090 and `×1.611`/`×1.618` on RTX 3090 and 130,048-token exact retrieval `×1.217` and `×1.366` with matching held-out perplexity, but flips secret-leak presence one way on five `worklog-007`/`worklog-014` prompts on RTX 4090 (`p = 1/32 = 0.03125`) and four of the same five on RTX 3090 (`p = 1/16 = 0.0625`, EXP-100) | byte-identical attention prefill shipped in v0.14.0; `Group64` A8 compiled off (EXP-100), leak-flip root-cause investigation open |
| RTX 5090 `nvfp4` artifact swap | Measured on 2026-09-04 (`bb336052`, `21,492,695,040` B): 2.22× prefill and −3.5% decode with INT8 KV, refuses to start with BF16 KV at 131,072 context; two-case grounding shift on the private screen. Upstream's 2026-09-15 v3 republish (`74d2c571`) grew to `23,719,715,844` B (`22.09 GiB`, `+2.07 GiB` over v2 and `+3.06 GiB` over shipped `81f924d4`), which still does not fit the RTX 5090 `DFlash2 K=7` `BF16` `C2` profile | rejected |
| RTX 4090 prefill chunk 2,048 | Measured on 2026-09-04 (`MTP3`): +22.8% prefill, +2.0% decode, +270 MiB peak, session time +5.5% to +12.8% against the shipped 512; 4,096 regresses decode. Re-probed on `v0.16.2` `DFlash2 K=7` (`131,072` `INT8` `C1`, shipped `chunk 1,024`) in EXP-115: fits (`848.00 MiB` available), but gains only `×1.0236` `C1` / `×1.0149` `130K` prefill (`< 1.04`), regresses `benchmark_c1` decode `×0.8818` (`254.40 → 224.33 tok/s`), and diverges on `40/84` `role84` cases (`44/84` cross-arm identity) | shipped v0.4.8 (`MTP3`); rejected for `v0.16.0+` `DFlash2 K=7` (`chunk 1,024` retained, EXP-115) |
| RTX 3090 131,072-token context | Measured on 2026-09-04: automatic KV capacity 131,072 at 22,465 MiB peak with unchanged throughput on the shipped INT8 profile | shipped v0.4.8 |
| INT8 KV on the RTX 5090 and RTX 4090 lanes | No session-time gain on the RTX 5090 (4.2 GB VRAM headroom only); +8.8% to +13.3% on the RTX 4090 at 23,180 of 24,564 MiB peak; worse role-corpus screen on both | rejected |

## Contributing a result

1. **Claim** the idea in an issue (`perf: <idea>`), with hypothesis and measurement plan.
2. **Measure** with the scripted lane or the runtime bench harness (`ninfer_bench`,
   `run_serve_corpus.py`, `run_serve_concurrency.py`, `ninfer_linear_bench` — see the runtime
   repo's bench documentation). Fixed seeds, warm-up, and repetitions are part of the method.
3. **Preserve the packet.** NCU/NSYS/timing outputs plus a summary with exact source commit,
   artifact hash, and settings.
4. **Prove the contract.** Ops follow the runtime repo's admission rules: central `ops/` layer,
   semantically closed contracts, FP64 oracles, and roofline calibration. An optimization PR
   without an oracle test is not reviewable.
5. **Report honestly.** Negative and inconclusive results are ledger entries too; they are how a
   distributed group avoids repeating dead ends.

Product-level throughput submissions (whole-appliance numbers rather than kernel work) go through
the [performance result form](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml)
and the [community results table](BENCHMARKS.md#community-results).
