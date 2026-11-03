# OMP NInfer v0.16.2 — durable-export Host reclaim and stock OMP 18.15.0

## Prepared release scope

This is the prepared runtime-and-client successor to published **v0.16.0**, not a release of
the held v0.16.1 client-only candidate. Published installation remains **v0.16.0**; use its
[immutable guide](https://github.com/alphastorm/omp-ninfer/blob/v0.16.0/docs/QUICKSTART.md)
until founder-owned publication of this release.

The target composition is RTX 5090 `v0.7.0-qwen38-5090-beta.5`, native Windows RTX 3090 and
RTX 4090 `v0.8.0-qwen38-{3090,4090}-beta.2`, and unmodified upstream **Oh My Pi 18.15.0**.
All runtime components target source `a87de3613c17bced777b446fb545f872d8395ec1` on upstream
`64d10fbf9f8e6bfc79ab0570b94674c5b9997929`. The RTX 5090 component is published; the native
component cuts and exact-source native qualification are not complete. No predecessor runtime,
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
  (`aa9023f5`). It does not promise that every save succeeds under pressure, or that a crash
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
  Hardware qualification of the new native packages remains a separate obligation.
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
configuration above; it does not complete the remaining agent probes or product routes.

### Restore-position founder waivers and pending native binding

- **RTX 5090 first-request-after-restart TTFT (founder waiver on two-restart `restore`):**
  Position **3**, `restore_0`, on `v0.7.0-qwen38-5090-beta.5` exceeded the per-position
  TTFT bound `incumbent + max(0.25 s, 25%)`: **0.481856409 s** candidate versus
  **0.231568998 s** incumbent and a **0.481568998 s** bound, an excess of
  **0.000287411 s**. That measured failure was **waived by the founder with disclosure**
  ([waiver](qualification/rtx5090-restore-position-waiver.json)); it is not rewritten as a measured
  pass. Every oracle passed and `cached - prompt` was equal at **−48 / −48**.
  This waiver applies only to that one failing position with exactly these values.
  Every other gate remains binding, and the remaining corrected probes are still pending.
- **RTX 4090 restore cache-gap waiver — pending exact-package evidence binding:**
  For the `v0.8.0-qwen38-4090-beta.2` candidate package, two-restart `restore` position
  **4**, `restore_1`, recorded `cached - prompt` **−52** candidate versus **−48**
  incumbent, below the rule `candidate >= incumbent`. Candidate prompt/cached tokens
  were **58,539 / 58,487**, versus incumbent **58,327 / 58,279**. Server TTFT was
  **0.642947 s** candidate versus **0.5589493 s** incumbent and stayed within its bound.
  The founder waived only this cache-gap failure with disclosure; the incumbent
  capture is hash-proved reused evidence for the published beta.1 package, not a fresh
  paired run. **Native qualification completion, publication and authenticated beta.2
  receipt binding remain pending.** No native gate pass or published-package acceptance
  is inferred from this marker; any other failure or changed value fails closed.

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
must be re-exercised with the new packages; no historical stop-first workaround is reintroduced.
For the container upgrade, stop an incumbent with the matching published v0.16.0 stop script,
not a successor script whose product identity differs. The v0.16.1 client-only instruction to
keep the running container is inapplicable because this release changes the server binary.

The [v0.16.0 notes](../v0.16.0/NINFER_RELEASE_NOTES.md) retain their original measurements and
waivers: RTX 4090 `log-024@0` speed, two RTX 5090 first-request-after-restart latency misses and
the RTX 5090 second-build exception. None is renewed for v0.16.2 by copying its receipt.
The native beta.1 files retained in this draft are explicitly quarantined predecessor
material in the [receipt audit](qualification/receipt-audit.json), not current beta.2
qualification. Both native rows remain preview and non-installable until fresh binding.

## Outstanding qualification and release gates

No result placeholders are embedded: the route composer writes structured acceptance records,
not prose substitutions in these notes. Before final composition, the release author must add
the actual new evidence and remove the corresponding outstanding-gate disclosure only when
its bound receipt exists:

- Remaining current-incumbent parity/probes, reclaim-path timing and stock-client
  checkpoint-request observations on the published beta.5 image; the lane receipt
  itself has passed and the single restore-position waiver is disclosed above.
- Both exact-source beta.2 native 15-phase qualifications, powered quality screens, fit/probe/
  concurrency and speed evidence, running-upgrade/rollback/repair, independent restoration,
  published component cuts and authenticated package identities.
- One frozen product candidate running all **five routes / 31 executable blocks**, all three
  exact stock OMP clients and both native public-URL installs. Keep C1 RTX 4090 fleet and C2
  RTX 3090 fanout/parallel/compaction obligations; an uninduced boundary is unexercised.
- Exact-subject runtime and product-tooling reviews, complete receipt/binding audit, immutable
  evidence pins, both full interpreter suites and strict ready/pin verification.
- Founder-owned product publication. No prepared text or component publication grants it.

macOS remains manual-SSH preview; Linux remains WSL2-scoped, not native Linux OS qualification.
Vision remains macOS/Windows against RTX 5090 only. No native/Linux vision, RTX 4090 C2, smaller
host, checkpoint migration, multi-owner proof, SLA or general performance claim is added.
