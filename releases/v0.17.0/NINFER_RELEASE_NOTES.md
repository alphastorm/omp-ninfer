# OMP NInfer v0.17.0 — bounded resume admission, serving robustness and stock OMP 18.18.6

> Qualified successor composition — five documented routes and three stock clients passed;
> the RTX 3090 post-route compaction campaign is failed and founder-waived with disclosure.
> Product publication and production promotion are separate founder-only actions.

## Qualified successor scope

This runtime-and-client successor to published **v0.16.2** binds fresh acceptance on
2026-11-10 and a specific native-campaign waiver, not an authorization to publish.
Use the [immutable published guide](https://github.com/alphastorm/omp-ninfer/blob/v0.16.2/docs/QUICKSTART.md)
until founder-owned publication of `v0.17.0`.

The composition selects published RTX 5090 `v0.7.0-qwen38-5090-beta.6` from release source
F3 `e0971faf221204047d5a4ed834e4e298740cee17`, plus stock Oh My Pi **18.18.6**.
Both native lanes carry unchanged published beta.2 bytes from
`a87de3613c17bced777b446fb545f872d8395ec1`; they are not rebuilt from F3. Both fresh documented
routes passed against the new client; the subsequent RTX 3090 campaign failed as disclosed below.
No canonical native promotion was required. Integration base
`e6ac7b709a1a3f94fbbcd6529ce87e813d20cd09` is not the release source.
No predecessor route acceptance, client execution, review approval or waiver transfers.

The shared model and serving profile stay fixed. RTX 5090 uses host `checkpoints-v017`, preserving
predecessor `checkpoints-v013` for rollback, while retaining container target `/checkpoints-v013`.
A retained mount/profile name does not establish cross-binary checkpoint compatibility. Keep prior
roots/staging/model/keys untouched and replay authoritative OMP transcripts for a fresh prefill.
Stop a predecessor with its own immutable release controller, never a successor helper.

## Runtime changes since v0.16.2

F3 includes the integration slices and localized council remediations in
[fork PR #101](https://github.com/alphastorm/ninfer/pull/101):

- **Bounded resume/fresh admission:** service-rotation accounting, exact-frontier protection and
  a bounded fresh-admission window address upstream #434. An unsuccessful fresh window consumes
  its rotation allowance, preventing repeated admission windows before the rotation completes.
- **Wait for durable pressure work:** pending save/export, guarded capture/source and reclaim
  boundaries wait for their progress owner rather than skipping the victim, pausing an older
  resident or failing because a legal unit is temporarily unavailable.
- **Serving robustness:** malformed tool arguments no longer throw; enabled effort tiers normalize
  to the artifact template; contradictory thinking/effort is handled; numerical failures are
  request-local. Stop drains cancellation and final-save work before service destruction.
  These changes address upstream #446/#440/#441 within the selected serving contract.
- **Host-side NFC/frontend rendering:** CPU-render optimization, not a measured end-to-end TTFT gain.
- **Optional prefill pacing:** default off; the retained deployment profile does not enable it.
  The exact-F3 RC includes passing candidate/control help inventories. No pacing benefit is claimed.

F3 also corrects two native transaction test-fixture `advance_prefill` callers to pass cap zero,
retaining their prior planned-step behavior. That compile correction is not a native package
re-cut or serving feature. Final-source EngineCore **35/35** and Scheduler passed after retained
red proofs of the two pressure-wait failures and unsuccessful-window accounting.
The [RC](qualification/runtime-rc.json), [build identity](qualification/runtime-build-identity.json),
[public artifacts](qualification/runtime-artifacts.json), [image receipt](qualification/runtime-publication.json)
and [lane gates](qualification/rtx5090.json) bind exact F3. Diagnostic slice/proxy observations
below are not relabeled as F3 acceptance.

The native packages do not receive these fixes. Their retained-context admission/Stop residual
is disclosed without asserting a precise defect or client cause. Prefix-source-wait follow-up,
copy drafting, native `rk4v4`, keep-warm changes and a 2048-token native prefill chunk are excluded.
Model/backend/context/concurrency/speculative route and default async client compaction policy
are unchanged.

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

These investigative summaries are context, not qualification receipts or release performance
gates. Their slice/proxy/historical subjects remain explicit. Raw captures stay private rather
than exposing prompts, host identities or client output; none grants new-client/route acceptance.

Later source diagnostics retain their actual verdicts: F2 `bdc665a3` C1 parity matched production
on all three request/content/reasoning/finish-byte cases; F3 changes only the native test fixtures,
so equivalence is a lead assertion, not a second GPU execution. F2's pressure run was
`CONDITIONAL_HORIZON_CENSORED`: one long request completed 40,000 tokens and the other was
horizon-cancelled at 38,714 while still progressing; strict both-normal completion was false.
Fresh requests completed 54/54 with zero HTTP 503. The original failed/censored observations
remain, rather than becoming an unconditional starvation or performance pass.

Pacing's later partial run completed only one cold-valid off/on pair before the route fence:
all requests succeeded, but on-arm co-resident decode was unmeasured (zero eligible whole
intervals), token IDs differed for the long request, and four cells were not started.
Event-gap p99 was 614.801/307.031 ms; long wall 59.309/61.954 s (ratio 1.044605).
One pair is not qualification or a pacing gain; pacing remains default off.

| Preserved investigative source (content address only) | SHA-256 |
| --- | --- |
| RTX 5090 source parity/pressure summary | `d046c13ed3a840f7cbe68cfb9734b416fe05a602d8d5e49580e350de4d0a4657` |
| Serving robustness analysis | `0a225ba10e9b16cc8d56092da3d3923c3f305632d2763774ebfa2b323918e51b` |
| Frontend CPU report | `96819447174b8d81a9353ddc2162099b682abcdcdc151113c5b3816e5f1ac779` |
| Native configuration investigation | `293a10f5455909fcef1248be85ccb578d05399d01f3e8dcd9491c398daf20240` |
| Copyability investigation | `0aa575a59ba067626ee4df531c617cb7f989929d3cd70216ce6f0e4d17dd09f1` |
| Native `rk4v4` investigation | `ffc6399304a0d75af10f39267004e24b55c703ac9e0a294b9b1b77319e2cd38a` |
| Historical traffic investigation | `a0933fa949148db0a5bc1d41083a450d2124fc49828c9b4dc85d0fa236a4ac58` |
| Partial pacing summary | `535f58ae3d78c678b51411cd740f6093e57454a853fc6073dd028ddbdf8b1e52` |

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

The current component lane proves its named protocol gates, not a renewed numbered agent-position
parity campaign or a general request-census performance result. No predecessor failed parity
position is relabeled as an F3 pass or renewed waiver. The lane controller/probe exited zero;
its owned container exited zero without OOM and was removed, and its fresh checkpoint tree was
removed. RC SHA-256 is `bed3a245125001e30fee289bb6bd138e861952623a5661ce5587661f184ad443`;
lane SHA-256 is `11fde294fbaeb7711d8526ad35c65f9941ef2eb0a24d799cecf84711a0717152`.

## Exact-subject founder waiver — original failures retained

One new post-route native-campaign waiver applies: RTX 3090, product candidate
`076bbe4f5abd68c8a0a1ba2efa0d08e881970e11`, after all seven documented blocks passed.
The subsequent automatic-compaction probe failed its **900-second** completion boundary;
this is not a numbered agent-parity position. Its original `passed: false` remains. The founder
waived only this `native-probes` campaign failure with disclosure, not another gate or publication.
No predecessor waiver is renewed for F3, this candidate or this client.

| Binding | SHA-256 |
| --- | --- |
| Original founder decision | `9be501f5a2d147fd3e25cdaf93c083bd76d91158a6847f30182c5a8a668173ba` |
| [Content-safe public projection](qualification/rtx3090-route-waiver.json) | `19f2c0ef0f9bbf38b6debaacdbb84e8e219c1f03b1d26671ca3fdfcbf63943f0` |
| Original failed compaction receipt | `59163a126aaf47d0bdc3f8d92d5b0aae476b598c92b667eda82ee5690edd1721` |
| Original window-failure receipt | `a345d206bef2f13f8420151129f06e6e17702b03dba92055bd3312d3bcac2d07` |

The projection also binds the passed original route, failed driver, lead recovery, pre/post census
and telemetry digests. Machine identities, private paths and raw client captures are not published.

## Published native qualification and no-regression evidence

Both published beta.2 components are unchanged. Their component qualification is historical
same-byte evidence, not fresh F3 hardware qualification or a new-client result. Fresh documented
routes passed; RTX 4090 campaign passed and RTX 3090 campaign remains failed with its specific
waiver. No native requalification or canonical promotion was required.

| Lane | Decision / component / source | Package SHA-256 / bytes | Server SHA-256 | Configuration SHA-256 |
| --- | --- | --- | --- | --- |
| RTX 3090 | Carried `v0.8.0-qwen38-3090-beta.2`, source `a87de3613c17bced777b446fb545f872d8395ec1` | `97a8e6340397d6a925cbabc6ffbb6f219a4b00f19b2f5d8e4be6cd14d41f3ed9` / 1,008,989,809 | `15a4db46db09dce695f1c55a9996b30408fa93ed864d881872f9ae7306fbab0f` | `238ccad7ba6dca673d845c183b6c3de3a49bd2ce75090f20f669b2d6f83dda6f` |
| RTX 4090 | Carried `v0.8.0-qwen38-4090-beta.2`, source `a87de3613c17bced777b446fb545f872d8395ec1` | `d9b10b47f1e7fad8413dc95347dbdd11d91636aec11552c29c1dc94246ca6d5b` / 991,981,865 | `ffee91bf17c261ae9b85791fc52528f7f1ef5c985c4d55feb7ee65174c96c73d` | `ae27dc446634048cec913fd42efc5971fb0ad950eed154ecce6aaa981eec4c9b` |

The [receipt audit](qualification/receipt-audit.json) retains both checksum sets, 15-phase
qualification chains, quality/fit and speed receipts byte-for-byte; the manifest binds their exact
SHA-256s. These are historical beta.2 measurements, not produced by F3 or OMP 18.18.6.
The unchanged [historical speed decision](qualification/native-speed-decision.json), SHA-256
`5c09de6a54bfbc7f52a83eb333436bdf9e025b864a458c0541c882e7560ecc4d`, requires weighted decode
ratio **>=0.98**, every case **>=0.95** and byte-identical normalized output against published beta.1,
superseding the old 1.08 speedup floor. RTX 3090/4090 speed receipts retain `852e13ca`/`e48aba81`.

| Historical beta.2 component speed gate | Weighted decode ratio | Minimum case | Normalized-output identity |
| --- | --- | --- | --- |
| RTX 3090, 84 depth-0 role cases | 1.0003 | 0.9988 | 84/84 |
| RTX 4090, 108 role + 7 supplemental cases | 0.9996 | 0.9989 | 115/115 |

Separate historical running-upgrade, forced-start rollback and interrupted-install repair proofs
passed **3/3 scenarios per lane**. RTX 3090 used the original source harness; RTX 4090 used a
founder-authorized private copy changing only uncapped-power assertions, bound by
[the retained decision](qualification/rtx4090-rehearsal-harness-decision.json), SHA-256
`f1fcd1bb162e9107b528c239c6c6ec251d461fe2a7c14664f8d1ea9bd6257a19`.
These are not fresh route rollback proofs. Both current routes are temporary first-lineage installs
with zero-direction `not_applicable` rollback. The retired stop-first workaround is not restored.

## Stock OMP 18.18.6

Selected client: `can1357/oh-my-pi v18.18.6`, release **439766193**,
source `9058ab9d229663e229e2867824ba6df6f21e9e59`, tree
`fd379b65368a20c7648d97f2c2b99cc03e019254`. The reviewed checksum-set SHA-256 is
`3d11ad7277e7ad65ea76963b60c0db21d57ad7c0621a94a9379f2e851939f280`.
The composed [descriptor](qualification/client-components.json) SHA-256 is
`d840d5e5abd2d7cc29f1754458343aef092ad6f077d5a75143a1a178af4fbe4d`.
[PR #145](https://github.com/alphastorm/omp-ninfer/pull/145)'s source/download review landed at
`c2a646e`; [review receipt](qualification/stock-omp.json) SHA-256 is
`aad29cd65a31e3246fbf6eeb4a01ea33a368decc79fa6b169e5fc829ccd8c611`.
Source review and independently authenticated assets are not live acceptance; fresh observations
below bind the actual three platform binaries.

| Platform | Asset / ID | Bytes | SHA-256 |
| --- | --- | --- | --- |
| macOS arm64 | `omp-darwin-arm64` / `729375455` | 221867152 | `ed2e63eb43888eb76cb1409b245b1db4557c94dfad52dc545c9aaca01ebce82d` |
| Windows x64 | `omp-windows-x64.exe` / `729375449` | 249985024 | `dfb15c27cb2ea192a94761c26aa5cd4eed54b1e0a5a85c02938ab07d769bc8f7` |
| Linux x64 under WSL2 | `omp-linux-x64` / `729375448` | 286021808 | `a8059b95de5eaba0b3fb6f7182842d661feae29cb2931cdbeba2986db4751ecb` |

- Preserve explicit supported efforts and high→medium/off→low clamps, especially on carried native
  templates. Final F3 protocol and fresh route receipts do not imply general raw-tier coverage.
- Pin `tokenizer: qwen3` on opaque aliases; canonical Qwen IDs retain inferred tokenization.
  All five documented routes executed the selected fragments with the exact stock client.
- Keep the real exact-loop guard on, with the three selected Responses compatibility values.
  Source-derived guard limits are four repeats/1,024 characters for short whole-line/newline
  cycles, four/180 for short non-newline cycles, three/1,024 for long cycles. Uninduced loop
  boundaries are not executed passes; obsolete operator `compat.thinkingLoopGuard` stays removed.
- Retain default async compaction and provider concurrency. Source-derived reserve **19,660**,
  strict **>111,412** trigger and ordinary unset-reserve summary cap **13,107** stay selected.
  No synchronous-only comparison arm or sibling performance policy is imported.
- Retain explicit `retry.enabled=false`, `retry.modelFallback=false`, `fallbackRevertPolicy=never`,
  `update.auto=false`, `startup.checkUpdate=false`, `startup.setupWizard=false`.
  Explicit `omp update` can still replace the pinned binary.
- Fresh receipts prove linked tools, continuation and fail-closed behavior on the three clients;
  macOS also executed the persisted-session/server-restart nonce route. Native probe scope,
  including failed compaction, stays explicit below. Auxiliary credentials were isolated.
  Small-fanout acceptance does not qualify >=9-run worker threads or unrelated optional surfaces.

## Retained model, serving policy and upgrade boundary

Shared model: `qwen3_8_27b.ninfer` (native filename `qwen3_8_27b-v3.ninfer`), revision
`1cbd84e7221e51186bd7f093a149912d2489625b`, container version **3**, **20,437,521,664 bytes**,
SHA-256 `81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da`.

| Lane | Selected serving shape |
| --- | --- |
| RTX 5090 | BF16 KV, DFlash2 K7, 131,072 context, 146,368 automatic KV tokens, C2 plus two extra device-state slots, 21,881,405,440 B shared Host budget, 28,672 MiB host floor, 1,024-token prefill, 180 s admission timeout, 60,000 ms keep-warm, mandatory checkpoint origin auth; pacing default off |
| Native RTX 4090 | INT8 KV, DFlash2 K7/artifact-default, 131,072 context/pool, C1 plus two extra device-state slots, 16,512,696,320 B Host budget, 32,768 MiB host floor, 640 MiB admission headroom, 1,024-token prefill, 30 s timeout, 60,000 ms keep-warm, 450 W owner baseline, mandatory origin auth; config `ae27dc44` |
| Native RTX 3090 | INT8 KV, DFlash2 K7/artifact-default, C2 over one shared 131,072-token pool plus two extra device-state slots, 21,881,405,440 B Host budget, 768 MiB admission headroom, 1,024-token prefill, 180 s timeout, keep-warm off, 350 W serving cap / 370 W restored, mandatory origin auth; config `238ccad7` |

macOS transfers the bearer key through a same-directory temporary file, checks SSH/pipeline success
and length, then atomically renames it; failed transfer leaves the existing key unchanged. The fresh
host `prepare` and macOS `key` blocks passed at candidate `076bbe4f`, with matching executed
hashes `d0d81b6a` and `fdce8eb3`.
The staging audit records **44** subjects: **18 kept unchanged**, **11 replaced**, **12 dropped**,
**3 added**. Kept entries are same-byte native component/configuration/model/base evidence;
replacements bind current runtime/client identities. Predecessor external acceptance, four waivers
and review approval were dropped. New acceptance, the current waiver and ledger are separately bound.

## Fresh candidate-bound route and client acceptance

Acceptance date **2026-11-10**, frozen product candidate
`076bbe4f5abd68c8a0a1ba2efa0d08e881970e11` for all five routes. Executed guide SHA-256
`ec27840d6c19d1d964153acc9ef052e62401b1ab6e7553df6aab236ef64e2fcc`;
final prose-only guide SHA-256
`209cef84a9cc36325289b0c529946c7f4ea664873139f158b11e359470c6fa95`.
All **31 executable blocks** remain byte-identical; the composer re-derives current addresses.

| Route / additional acceptance | Actual result |
| --- | --- |
| RTX 5090 container host | **2/2 passed**, beta.6 image `7a19576b`, server `dc86e101`, config `751d22dc` |
| macOS arm64 over manual SSH | **10/10 passed**, linked tool, exact continuation/restart nonce, fail-closed outage, image input; preview |
| Native Windows x64 against RTX 5090 | **5/5 passed**, linked tool, exact continuation nonce, fail-closed outage, image input |
| Linux x64 against RTX 5090 | Structured tool, continuation and fail-closed passed; WSL2 only, no Linux vision claim |
| Native RTX 4090 (`rtx4090-win-a`) | **7/7 passed**, C1 fleet probe, structured behavior, anonymous public install, independent restoration/final audit passed |
| Native RTX 3090 (`rtx3090-win-a`) | **7/7 passed**; fleet/fanout/parallel passed, later compaction failed; campaign founder-waived, no structured outage/public install/passing wrapper audit |

[Documented routes](acceptance/documented-routes.json) bind **31/31** measured blocks and these
original receipt-byte hashes under `docs/measurements/2026-11-10-v0170-<lane>-run.json`:

| Lane | SHA-256 |
| --- | --- |
| `rtx5090-container-host` | `d3a3e537e17f1dfb82a396c5e9b415d0e9b039127f46d7d871b51c99ddd52e7d` |
| `rtx5090-macos-client` | `d62becce2d101b0c3bfd9614661dbe2fbf40ac7633e7fe5b0438d893225b1b71` |
| `rtx5090-windows-client` | `d1781a6843bfe5c5898e280609490e5f7487cd694aa83387886557df3963b7f1` |
| `rtx4090-native` | `9943d5d91fbe87a0494895ca5590b6504a02fd0b63f97da35f98a3ba34484c25` |
| `rtx3090-native` | `9f3d24a2447b1666277ae74018e82b7d9bd319befc4b5b4af7b1db1b3a475bc5` |

RTX 5090 accepted/all-attempt production hold **408.213 s**, one actual production window.
An earlier unresolved SSH launch stopped before backend effects and is not a second hold or pass.
RTX 4090 campaign **508.420 s**; failed RTX 3090 campaign **1727.696 s**. Both native routes were
temporary first-lineage installs with zero-direction `not_applicable` rollback, not running-lane
upgrade qualification. RTX 4090 public install/restoration/final audit passed. RTX 3090 failed
campaign/final audit and absent public install remain unchanged; later lead recovery restored
exact pre-window cross-lane census and holds/client bytes.

The same incumbent production container/image `a0cbb8a5`, HTTP 200 health, checkpoint mounts and
`unless-stopped` policy were observed after restoration, with Fleet healthy/unreserved. Route
key/checkout/directories and markers/tasks were restored, route container/hold removed, original
backend restored. The [restoration receipt](../../docs/measurements/2026-11-10-v0170-acceptance-restoration.json)
records `passed-with-founder-waiver`, not an unqualified all-native campaign pass.

### Failed RTX 3090 campaign and operator recovery

**RTX 3090 native limitation (founder-waived campaign):** All seven v0.17.0 documented-route blocks passed, but the subsequent automatic-compaction campaign failed under retained-context pressure: the compaction probe timed out after 900 seconds, with eight HTTP 503 `request_queue_timeout` responses and two HTTP 499 cancellations while no work was resident. The subsequent managed Stop refused three sessions. Lead recovery restored the stopped lane gracefully, with zero refused sessions, no runtime record or GPU-owner lease, the original 370 W limit, and an unchanged cross-lane census; it is not a passing campaign or wrapper restoration audit. Structured-outage and anonymous public-install acceptance were not reached. The founder waived this specific campaign failure with disclosure, not any failed documented block or other gate. RTX 3090 users should keep v0.16.2 or restart the lane after long sessions until a native re-cut is qualified. These observations do not establish a client regression or the precise native defect.

The failed Stop retained `graceful_incomplete_shutdown`, saved **2**, skipped **5**, refused **3**,
`shutdown_complete: false`, `forced: false`; durable save refusal reason was `capacity`.
All 58 original failed-evidence files stayed byte-identical. The failed candidate root/stage was
preserved untouched before restoring the originals and performing empty-session Start→ready→Stop.
Recovery is separately bound, never substituted for campaign success.

## Exact-subject review and publication boundary

The content-safe [review ledger](review/runtime-ledger.json) binds runtime full-council history
through exact F3 `e0971faf`, the product full council on `c4afc44f` with route stage `076bbe4f`,
and focused waiver-tooling review on `f85af622`. The qualification G4 binding records the final
ledger-byte SHA-256 `5f8d6e4a0d698f227237b1cf420a8da87182a7c0197ce05e3744fc2f485bce5f`
and closed approval; publication and public-route grants stay false. The focused review's one
fix-only round closes remediation `bf2a63a0`: bind the canonical failed-compaction projection
`bcdf026d9e68dd8aaf67e8999b411cddbf1ba785e9b370983ec4f1735ae69e02` separately from original
file bytes, and enforce the exact waived-lane non-claim sentence.
Preparation tests are not runtime qualification or independent review.

Product findings pre-existing in v0.16.2 are dispositioned with explicit lead checks: screen every
composed public receipt, prove ledger-stage/route-clone equality, re-derive current guide blocks
and document hash, and use only this window's native campaign/public-install evidence. The beta.5
compatibility label is corrected to beta.6. Deferred tooling residuals are tracked in
[#149](https://github.com/alphastorm/omp-ninfer/issues/149). Immutable lane, platform, acceptance
and manifest pins are separate from review approval.

Publication and production promotion are founder-only. This composition authorizes no tag,
GitHub release, host window or install. The delivery handoff requires strict ready+pins verification,
both full interpreter suites, pinned-URL byte checks and green PR CI on the pushed final head;
command results are delivery evidence, not inferred runtime or publication passes.
macOS remains manual-SSH preview; Linux remains WSL2-scoped. No native/Linux vision, checkpoint
migration, multi-owner proof, SLA or general performance claim is made.
