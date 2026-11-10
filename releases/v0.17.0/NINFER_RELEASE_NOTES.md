# OMP NInfer v0.17.0 — bounded resume admission, serving robustness and stock OMP 18.18.6

> Prepared product candidate — runtime beta.6 is published; fresh product-route/client acceptance
> and founder-owned product publication remain separate gates. Remaining `TODO` fields are not passes.

## Qualified successor scope

This is preparation for the runtime-and-client successor to published **v0.16.2**, not a
qualified release. Use the [immutable published guide](https://github.com/alphastorm/omp-ninfer/blob/v0.16.2/docs/QUICKSTART.md)
until founder-owned publication of `v0.17.0`.

The composition is published RTX 5090 `v0.7.0-qwen38-5090-beta.6`
from release source F3 `e0971faf221204047d5a4ed834e4e298740cee17`, plus stock Oh My Pi `18.18.6`.
Both native lanes carry their published beta.2 bytes from source
`a87de3613c17bced777b446fb545f872d8395ec1`; they are not rebuilt from F. They still need
fresh product-route/client acceptance against the selected new client, but no canonical promotion.
The integration base is `alphastorm/ninfer` `e6ac7b709a1a3f94fbbcd6529ce87e813d20cd09`;
it is not the final source.
No predecessor runtime qualification, client execution, route acceptance, review or waiver
becomes current merely by copying a receipt.

The shared model and serving profile remain unchanged. The prepared RTX 5090 route uses
host `checkpoints-v017`, keeping predecessor `checkpoints-v013` untouched for rollback. The
container mount target remains `/checkpoints-v013` under the retained qualified profile.
A retained profile or mount name never establishes cross-binary checkpoint compatibility.
Replay the authoritative OMP transcript for a fresh prefill; never import prior generations.

## Runtime changes since v0.16.2

The release source F3 contains the integration slices plus the localized council remediations
below ([fork PR #101](https://github.com/alphastorm/ninfer/pull/101)).
The exact-source RC batch and published-image lane gates passed; new-client/product-route
acceptance and final review/composition bindings remain separate.

- Resume/starvation correction for upstream #434, including a bounded fresh-admission window.
  TODO: bind the final implementation and matched scheduler/continuation regression evidence.
- Serving robustness for upstream #446/#440/#441, numerical-failure isolation and graceful Stop.
  TODO: name exact semantics, failure isolation and shutdown results from the final source/tests.
- Host-side NFC/frontend rendering optimization. Its CPU-render measurement is scoped below;
  it is not a measured end-to-end TTFT speedup.
- Optional prefill pacing, default off. TODO: bind the final help/default inventory;
  no default-on pacing or measured pacing benefit is claimed.
- **Wait for pending durable pressure work instead of failing the Engine.** When pausing a
  resident creates a pending durable save/export, the pressure progress owner waits for that
  work rather than skipping the victim, pausing an older resident or failing because it cannot
  obtain its legal unit. The same wait semantics cover guarded capture/source/reclaim boundaries.
- **Charge unsuccessful fresh-admission windows to the rotation budget.** Taking a pressure
  fresh window consumes its per-rotation allowance even when admission fails or is skipped;
  failure does not grant repeated fresh windows before the service rotation completes.

F3 also corrects two native transaction test-fixture callers of `advance_prefill` to pass the
new token cap explicitly as zero, retaining their prior planned-step behavior. That fixture-only
compile correction is not an additional serving feature, native package re-cut or performance
result. TODO: bind exact-F3 RC, review dispositions and published-image evidence; diagnostic
predecessor measurements below are not re-labeled as F3 acceptance.

TODO: disclose exclusions and any unresolved engine/native residuals. Do not silently adopt a new
model backend, context size, serving concurrency, speculative route or client compaction policy.

### Pre-cut investigative measurements — not published-image or product acceptance

The overnight report records these observations on the named subjects. Measurements on a slice
build, a proxy GPU or historical production logs are not relabeled as beta.6/F release qualification.
The E4 pacing result's after column is empty in that report; no pacing improvement is filled in here.

| Investigation / subject | Observed baseline | Observed result and boundary |
| --- | --- | --- |
| C2 starvation, RTX 5090, same-window EXP-109 | Production `a87de361`: maximum admitted pause **368.0 s**; second long request starved and was cancelled at the **600 s** horizon; fresh HTTP 503 **0/54**, fresh TTFT p50/p95 **0.29/0.54 s** | E1 runtime build `375bb848`: maximum fully-paused **3.0 s**, pause→recovery **3.2 s**; both long requests completed **40,000 tokens each** inside **600 s**; fresh HTTP 503 **0/51**, TTFT p50/p95 **0.40/3.39 s**. Fresh requests can wait for a rotation window: the worse fresh-request tail is retained, not hidden. |
| C2 starvation, RTX PRO 6000 proxy, EXP-109 | Earlier `a87de361` measurement **362.3 s**; overnight `e6ac7b70` control: **36** fresh HTTP 503, **1/2** long requests complete | E1: maximum pause **2.27 s**, **0** HTTP 503, **2/2** long requests complete; no-pressure greedy parity **3/3** each for MTP3 and DFlash2. Proxy/slice proof, not final RTX 5090 qualification. |
| Serving robustness, E2 | Historical malformed tool arguments yield HTTP **500** on later turns; unsupported enabled-thinking effort tiers and contradictory thinking/effort produce HTTP **400** | The report records no-throw tool arguments, artifact-template-aware effort normalization, request-local numerical failure and stop/drain retaining final save. SIGTERM **2.571 s**, saved **1**, refused **0**; native resume **18 cached tokens**, MTP3 parity byte-identical. This is the E2 probe subject, not the carried native beta.2 release. |
| Host-side NFC/frontend render, E3 | **507 KB** non-ASCII document: **5.15 ms** per render | **0.47 ms**, reported **11×** CPU-render speedup; **65** renders / **564,922** token IDs identical. Jinja strip was not ported because the base validates interior UTF-8 by contract; first-use preload was not selected (**≤0.67 ms**). No end-to-end TTFT claim. |
| Cold prefill/decode overlap, RTX PRO 6000 proxy, `e6ac7b70` | **3** valid cold repeats: co-resident decode **6.375 tok/s**, gap p50/p99 **350.6/470.0 ms**, arrival TTFT **0.804 s**, long-prefill wall **46.5 s** | Baseline only; no candidate pacing after result is recorded. |
| Cold prefill/decode overlap, production RTX 5090 `a87de361` | **6/6** valid cold captures: co-resident decode **5.11 tok/s**, gap p50/p99 **430/619 ms**, staged-prefill arrival TTFT **23.07 s**, long wall approximately **60 s** | Baseline only. The separate bounded prefix-source-wait fix is excluded from F; do not present this pre-existing wait as fixed by pacing or the starvation correction. |

The rejected/deferred investigations explain why the model, native packages and serving policy
do not change:

- **RTX 3090 keep-warm not promoted:** post-idle TTFT **0.546/0.567/0.650 s** after
  **12/30/58 s**, versus **0.417–0.421 s** back-to-back; the card still reaches P5/P8 with
  the compiled sm_86 pattern, consuming **25–73 W** more while held. Outputs were **27/27**
  identical; this does not establish the desired keep-warm result.
- **RTX 4090 prefill chunk 2048 not promoted:** the report records a fit observation of **848 MiB**;
  prefill ratios **1.024 / 1.015**, qualification decode ratio **0.882**, cross-arm identity
  **44/84**. The published chunk **1024** stays; the powered-screen-only result is not a release gain.
- **Copy drafting excluded from F:** **20.5%** of **1.76 million** observed output tokens were
  copyable (**13.3%** with backoff); edit/hashline **39.8%**, write **17%**, reasoning **3.6%**.
  The projected session decode ratio **1.055–1.093** is a model, below the **15%** selection bar,
  not measured local-Qwen performance: the sample is **3,000 cloud-model turns**, no local-Qwen
  turns on the sampled Mac. The separate default-off draft remains unselected.
- **`rk4v4` remains outside this release:** on RTX 3090 the restored arm and geometry-matched cold
  replay agree **32/32**, whereas ordinary 1024-chunk cold differs only at token **32**
  (**48117** versus **3635**). The matched split was **3066**, suffix **18/2/3/4**; transport
  was byte-exact and INT8 control **32/32**. A changed durability oracle and native adoption need
  a separate product-contract decision and hardware proof; this is not a new F restore claim.

Historical production-traffic analysis is context, not a before/after F benchmark: **9,430**
requests from **2026-08-25 through 2026-11-04**; the recent **176** show wall decode/prefill/queue
shares **31.9% / 50.2% / 8.2%**, overlap **25.6%** (earlier **1.3%**) and **1.56×**
interference slowdown. No stall **≥60 s**, preemption or replay was observed. Cached TTFT
p50/p90/p99 is **0.265/0.357/1.466 s**, cold **3.45/4.82/5.94 s**; the modeled low-acceptance
recovery opportunity is **≤0.85%**, not a shipped optimization.

The same log analysis attributes **94.4%** of the cached-TTFT top decile to prefill
(**673/718** compute requests have **>4,096** new tokens). **Four** first-after-server-start
Host-KV restores account for **84%** of recent top-decile excess; excluding those observations
gives p99 **0.376 s**, not a measured F improvement. Restore preparation was not instrumented;
the strict-warm top **1%** is **79%** queue.

TODO: bind public-safe investigative measurement projections/content hashes before product
publication; none of these observations grants new-client or product-route qualification.

## Published RTX 5090 identity and component qualification

| Binding | Exact identity |
| --- | --- |
| Binary release | `v0.7.0-qwen38-5090-beta.6` |
| Source release | `v0.7.0-qwen38-5090-source.6` |
| Release source F3 | `e0971faf221204047d5a4ed834e4e298740cee17`; integration base `e6ac7b709a1a3f94fbbcd6529ce87e813d20cd09` |
| Binary archive / bytes / SHA-256 | `ninfer-qwen38-rtx5090-v0.7.0-linux-x86_64-cuda13.1.tar.gz` / 580026014 / `d7f1ca4fdca2555a2e36ce84121737e9910e559f4519e24a848f0451214ea180` |
| SPDX SHA-256 | `d9ea727c7d415c8189f0c76708fa665ebd4df4c025764906f8e7c48cb6356a4e` |
| Checksum set SHA-256 | `beb70158323695ac2bc562e0c2f0ae6c55ee5fb6e8270c1df5cfb09a0d9f994b` |
| Source archive / bytes / SHA-256 | `runtime-source-e0971faf.tar.gz` / 12820073 / `73749f93241ff6990873b8d18a9c7d5687dee101af94683076d9c077795ce478` |
| `ninfer-serve` SHA-256 | `dc86e101c2c6a0fb03875e746448c4008d5dfce0633a0c8e3e830b61ac820c29` |
| Runtime image | `ghcr.io/alphastorm/ninfer-runtime@sha256:7a19576b334b54f8bfca0e022626969bd47ca376ac600a93eb6117dcafd89233` |
| Image receipt release | `v0.7.0-qwen38-5090-runtime-beta.6` |
| Runtime-base receipt / image | Reused `runtime-base-a87de361-20261103` / `ghcr.io/alphastorm/ninfer@sha256:28857182859a8f4993090521899b11a3f8676cb174c59adc626485e9f01472a3` |
| Deployment profile / configuration SHA-256 | `qwen38-5090-v0.13.0` / `751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47` |
| Published-image lane receipt | [`qualification/rtx5090.json`](qualification/rtx5090.json) |

The packaged build identity records GNU 13.3.0 / NVIDIA CUDA 13.1.115 / `sm_120a`, clean F3
source. The exact-source RC batch passed all 12 phases: 66 historical host, 54 current host,
11 dense real-model tests and one overlap test, with no recorded failures or skips; restart,
product-shape, exact-profile and PRODUCT protocol phases passed. The source-bound release
double build matched 664 artifacts and all three package outputs bit for bit.

The separate published-image lane receipt records 146368 automatic BF16 KV tokens. Its cold
130048-token prefill completed in 56.63 s (2296.5 tokens/s wall), with exact fixture output;
decode recorded 181.92 tokens/s server time (180.4 wall) over 2048 completion tokens. Agent
protocol gates passed, including authenticated identity, stateful continuation and deletion
non-resurrection after restart; transient retries were zero. These bounded lane observations
are not a general throughput/latency guarantee or fresh stock-client/product-route acceptance.
No pacing benefit is inferred from the investigative measurements above.

TODO: record judged agent positions, actual strict parity verdicts, request census counts,
cleanup/restoration results and content-addressed receipts. Preserve every failed measurement.

## Exact-subject founder waivers — original failures retained

TODO: determine whether any *new exact-subject* founder waiver exists. None is assumed.
Predecessor waivers are not renewed for the rebuilt source, new product candidate or new client.
For each actual waiver, include the lane/subject, numbered probe job/position, metric values,
threshold, original failed verdict, founder disposition, scope and both original/public hashes.
If none exists, state that only after all applicable gates have completed.

| Founder record / public projection | Original record SHA-256 |
| --- | --- |
| TODO: exact-subject decisions, or remove table if none | TODO: record digest |

## Published native qualification and no-regression evidence

Both lanes carry their published beta.2 components unchanged. Their component qualification is
historical same-byte evidence, not fresh source-F hardware qualification; new client/product-route
acceptance remains required. No canonical promotion is needed.

| Lane | Decision / component / source | Package SHA-256 / bytes | Server SHA-256 | Configuration SHA-256 |
| --- | --- | --- | --- | --- |
| RTX 3090 | Carried `v0.8.0-qwen38-3090-beta.2`, source `a87de3613c17bced777b446fb545f872d8395ec1` | `97a8e6340397d6a925cbabc6ffbb6f219a4b00f19b2f5d8e4be6cd14d41f3ed9` / 1,008,989,809 | `15a4db46db09dce695f1c55a9996b30408fa93ed864d881872f9ae7306fbab0f` | `238ccad7ba6dca673d845c183b6c3de3a49bd2ce75090f20f669b2d6f83dda6f` |
| RTX 4090 | Carried `v0.8.0-qwen38-4090-beta.2`, source `a87de3613c17bced777b446fb545f872d8395ec1` | `d9b10b47f1e7fad8413dc95347dbdd11d91636aec11552c29c1dc94246ca6d5b` / 991,981,865 | `ffee91bf17c261ae9b85791fc52528f7f1ef5c985c4d55feb7ee65174c96c73d` | `ae27dc446634048cec913fd42efc5971fb0ad950eed154ecce6aaa981eec4c9b` |

TODO: bind the carried checksum/chain/quality/fit receipts byte-for-byte and label every retained
number as historical beta.2 evidence. Do not reuse those measurements as if F or the new client
produced them, and do not schedule native component requalification or promotion merely to carry
the unchanged package.

The historical beta.2 speed comparator was published beta.1 under the founder-selected
no-regression rule: weighted ratios at least 0.98, every case at least 0.95, and byte-identical
normalized outputs. These are carried component results, not new F/client measurements.
TODO: authenticate the historical decision and receipts in the successor audit.

| Historical beta.2 component speed gate | Weighted decode ratio | Minimum case | Normalized-output identity |
| --- | --- | --- | --- |
| RTX 3090, 84 depth-0 role cases | 1.0003 | 0.9988 | 84/84 |
| RTX 4090, 108 role + 7 supplemental cases | 0.9996 | 0.9989 | 115/115 |

Both historical beta.2 packages have separate running-upgrade, forced-start rollback and
interrupted-install repair evidence (3/3 scenarios per lane). TODO: retain the exact historical
scope, including the RTX 4090 uncapped-power-assertion-only harness correction and its authorization;
do not relabel those rehearsals as v0.17.0 route rollback or repeat them merely for a client change.
First-lineage product-route rollback is not that predecessor proof.
Do not restore the retired stop-first workaround or assume the predecessor's native failure recurs.

## Stock OMP 18.18.6

Selected client: `can1357/oh-my-pi v18.18.6`, release **439766193**,
source `9058ab9d229663e229e2867824ba6df6f21e9e59`, tree
`fd379b65368a20c7648d97f2c2b99cc03e019254`. The reviewed checksum-set SHA-256 is
`3d11ad7277e7ad65ea76963b60c0db21d57ad7c0621a94a9379f2e851939f280`.
TODO: reconfirm the selected upstream release at staging and bind the reviewed descriptor.
Source/download-integrity review authority is [draft PR #145](https://github.com/alphastorm/omp-ninfer/pull/145),
not live acceptance; TODO: bind its landed immutable receipt and SHA-256.

| Platform | Asset / ID | Bytes | SHA-256 |
| --- | --- | --- | --- |
| macOS arm64 | `omp-darwin-arm64` / `729375455` | 221867152 | `ed2e63eb43888eb76cb1409b245b1db4557c94dfad52dc545c9aaca01ebce82d` |
| Windows x64 | `omp-windows-x64.exe` / `729375449` | 249985024 | `dfb15c27cb2ea192a94761c26aa5cd4eed54b1e0a5a85c02938ab07d769bc8f7` |
| Linux x64 under WSL2 | `omp-linux-x64` / `729375448` | 286021808 | `a8059b95de5eaba0b3fb6f7182842d661feae29cb2931cdbeba2986db4751ecb` |

- Keep the explicit supported effort lists and high→medium/off→low clamps; do not send raw
  unsupported tiers to the Qwen template. TODO: bind final engine/client wire evidence.
- Pin `tokenizer: qwen3` on opaque aliases; canonical Qwen model IDs retain inferred tokenization.
  TODO: confirm all selected fragments against the final stock client.
- Keep exact-loop detection enabled and the supported per-model Responses compatibility values.
  TODO: record configured numerical guard limits from the selected client, not an old receipt.
- Retain default async compaction, reserve/trigger policy and provider concurrency. Correct the
  ordinary unset-reserve summary cap to `13,107` (source-derived client policy); do not silently select the
  separate synchronous-only comparison arm or import Strata's performance policy.
- Keep explicit retry/fallback opt-outs, `update.auto=false`, `startup.checkUpdate=false` and
  `startup.setupWizard=false`. An explicit `omp update` can still replace the pinned binary.
- Re-prove linked tools, continuation, cold replay, persisted session/restart, fail-closed request
  counts and real compaction/control recall. Isolate auxiliary credentials. Worker-thread coverage
  and unrelated optional surfaces must not be inferred from small-fanout routes.

## Retained model, serving policy and upgrade boundary

Shared model: TODO: artifact name/revision/container version/bytes/SHA-256.

| Lane | Selected serving shape |
| --- | --- |
| RTX 5090 | TODO: KV/backend/draft/context/automatic tokens/concurrency/slots/budgets/timeouts/origin auth; pacing default off if included |
| Native RTX 4090 | TODO: exact selected packaged configuration and all limits |
| Native RTX 3090 | TODO: exact selected packaged configuration and all limits/power policy |

Stop the predecessor with its matching immutable release's controller/stop script, never a
successor helper whose identity differs. Preserve its checkpoint roots, staging, model and keys
for rollback. Use `checkpoints-v017` for the successor host path; never write new-binary state
into `checkpoints-v013`. macOS copies the bearer key to a same-directory temporary file, requires
SSH/pipeline success and length validation, then atomically renames it; failed transfers leave
an existing key unchanged. TODO: bind fresh execution of both changed documented blocks.

TODO: record the receipt audit's kept/replaced/dropped subjects and reasons. Carried native
component qualification does not grant a new client/product route acceptance or publication.

## Fresh candidate-bound route and client acceptance

TODO: acceptance date, frozen product CANDIDATE commit, executed guide hash and final prose-only
guide hash. All routes must bind the same final candidate; no predecessor receipt is relabeled.

| Route / additional acceptance | Actual result |
| --- | --- |
| RTX 5090 container host | TODO: block counts/verdict and candidate/runtime bindings |
| macOS arm64 over manual SSH | TODO: block counts, tool/continuation/restart/outage/image; preview |
| Native Windows x64 against RTX 5090 | TODO: block counts, tool/continuation/outage/image |
| Linux x64 against RTX 5090 | TODO: structured tool/continuation/outage; WSL2 only |
| Native RTX 4090 | TODO: blocks, campaign/probes/public install/independent restoration |
| Native RTX 3090 | TODO: blocks, campaign/probes/public install/independent restoration |

TODO: exact executable-block count (expected route inventory `31`, not a measured pass), route
receipt paths/hashes, compaction/fleet/fanout results, public-install verdicts, lineage/rollback
scope, native audits/census equality and actual hold/elapsed durations per lane and all attempts.
TODO: verify the same healthy incumbent production container/image, restart policy and checkpoint
mounts; no owned route container/hold/key/checkout/directories or backend override remains.

### Failed campaign and operator recovery, if any

TODO: replace with actual failure/recovery evidence or remove after completed clean acceptance.
Preserve failed Stop/save counts, reasons and original verdicts; recovery is not a passing wrapper
or an anonymous public-install result. No historical RTX 3090 waiver is assumed to carry.

## Exact-subject review and publication boundary

TODO: bind exact frozen runtime/product review subjects, resolver-selected assurance, closed
findings/dispositions/controls and content-safe ledger SHA-256. Preparation tests are not runtime
qualification or independent review. TODO: reconcile guide retargeting and final notes before
composition, then bind lane/platform/acceptance/manifest stages and verify immutable pins.

Publication and production promotion remain founder-only. This draft does not authorize a tag,
GitHub release, host window or install. TODO: final strict ready+pins verification, both full
interpreter suites, pinned-URL byte checks, PR CI and founder publication handoff.

macOS remains manual-SSH preview and Linux remains WSL2-scoped unless new evidence explicitly
changes that support boundary. No new native/Linux vision, checkpoint migration, multi-owner
proof, SLA or general performance claim is made. TODO: confirm final limitations against actual
qualification and acceptance before removing the draft warning.
