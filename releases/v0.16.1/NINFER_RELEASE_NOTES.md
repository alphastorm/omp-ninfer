# OMP NInfer v0.16.1 — stock OMP 18.15.0, unchanged GPU runtimes

## Prepared release scope

This is the prepared client-only successor to published **v0.16.0**. It selects unmodified
upstream **Oh My Pi 18.15.0** for macOS arm64, Windows x64 and Linux x64. It does not rebuild,
promote or change any NInfer runtime package, model, serving profile or checkpoint format.
The published release remains **v0.16.0** until founder-owned publication of this release.

For the manual-tunnel route, this client-only patch keeps the running v0.16.0 container; if a restart is needed, stop it with the v0.16.0 stop script.

The source and asset-integrity reviews are complete. Fresh candidate-bound platform execution,
five documented routes, both native public installs, independent restoration, product review,
immutable evidence pins and strict ready verification are separate release gates. This prepared
text does not claim that those gates have passed or transfer v0.16.0 client acceptance.

## Stock client identity

- Upstream: [`can1357/oh-my-pi v18.15.0`](https://github.com/can1357/oh-my-pi/releases/tag/v18.15.0),
  release **430630500**, published **2026-11-01T14:17:08Z**, non-draft/non-prerelease.
- Commit: `3fedf8d53267e32a6d7521ce725fdcc4a36fdc67`.
- Tree: `48bc72ba2418c0b78163d9769e91a0d8683e642b`.
- Descriptor: [`qualification/client-components.json`](qualification/client-components.json).
  Each asset is a raw executable, so its asset and binary SHA-256 are identical.

| Platform | Asset / ID | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| macOS arm64 | `omp-darwin-arm64` / `698539455` | 215295120 | `d36dfabf0ee52d6f08efadb59c46f0349545c6f6975522417adae29646e73e34` |
| Windows x64 | `omp-windows-x64.exe` / `698539443` | 243250176 | `978846a816cb77f44a55e32b16493375ca837fbf87e0aec35a9c1c934bff0cd0` |
| Linux x64 | `omp-linux-x64` / `698539441` | 276785328 | `6737ee2415555a3656cc7b89c14d1c25c18658ee4c0fd4f7309705149ccb7b0f` |

The independently downloaded `SHA256SUMS.txt` (asset `698539453`, **844 bytes**, SHA-256
`c866af8cc5c8f04d0baee8b5a836b63419b6fa6095061685588af3a3cbe52f72`) matches its API digest;
the three executable hashes match both API digests and its rows. The checksum file has no
self-checksum row. Integrity is not executable, security-audit or reproducible-build qualification.

## Changes relevant to the documented local routes

The [18.14.0→18.14.2 review](../../docs/measurements/2026-11-01-omp-18142-client-upgrade-review.json)
and [18.14.2→18.15.0 review](../../docs/measurements/2026-11-01-omp-18150-client-upgrade-review.json)
cover the whole client change from the published product. The latter inventories all **235**
incremental commits and the uncapped **257-path** tagged-tree diff. Unchanged provider files
are not a claim of whole-route wire equivalence: shared replay utilities and session maintenance
also participate in the route.

- **Exact loop guard stays enabled.** Qwen and opaque local aliases retain exact-cycle detection.
  Short cycles spanning a newline need four repeats covering at least **1024** characters,
  avoiding the prior short whole-line false positives. Short non-newline cycles retain four
  repeats/**180** characters; long cycles retain three repeats/**1024** characters. Remove obsolete
  operator `compat.thinkingLoopGuard`; it is not an operator key in the current sparse compat
  schema. Do not disable `model.loopGuard` or inherit `PI_NO_THINKING_LOOP_GUARD=1`.
  The three working keys remain `compat.statefulResponses: true`,
  `compat.includeEncryptedReasoning: false`, and `compat.supportsReasoningSummary: false`.
- **Incomplete summaries fail visibly.** Main, turn-prefix, handoff and branch summaries stopped
  for length are rejected instead of committing partial context. A completed full summary remains
  usable when only its optional display-only short summary truncates. Default reserve stays
  **19660**, the trigger remains strictly **>111412** for the **131072** context, and the local
  full-summary output cap is **15728**, distinct from the route's **32768** output limit.
- **Manual compaction waits for replacement.** Background/IRC/custom-message result delivery now
  waits through manual as well as idle compaction cleanup and persistence reconnection before
  starting a turn. Exactly-once persisted delivery, cancellation/failure and restarted continuation
  need separate evidence; the source fix alone is not that evidence.
- **Responses replay strips backend-only metadata on transport copies.**
  `internal_chat_message_metadata_passthrough` is removed without deleting ordinary metadata,
  content or linked function call/output pairing, and without mutating stored history. The static
  local fragments do not opt into a remote-compaction API.
- **Missing-key fallback has its own gate.** Keep explicit `retry.enabled=false`,
  `retry.modelFallback=false` and `fallbackRevertPolicy=never`. Disabling ordinary retry alone
  does not disable the new pre-prompt missing-credential fallback walk. Keep the selected-provider
  outage and request-count gates; never reinterpret a fallback as successful local inference.
- **Snapcompact reader accounting changes.** Text-only readers can recover retained archive text,
  fitted to the reader window with explicit lost-middle accounting; reconstructable persisted frame
  blobs affect the replacement baseline. This does not add native-lane or Linux vision support,
  expand the model context or change the ordinary summary stop rules.
- **Selectors and effort remain exact.** Keep `ninfer-beta/q38-ninfer`,
  `ninfer-native-3090/q38-ninfer`, `ninfer-native-4090/qwen3.8-27b` and
  `ninfer-heavy/qwen3.8-27b:medium`. The stock high→medium/off→low clamps and the
  `qwen3.8-27b` replace / `q38-ninfer` hashline edit defaults remain. No discovery,
  `serviceTiers`, `/fast`, `effortMap` or per-call-model opt-in is added.
- **Optional background captions/capture are separate requests.** An eligible background bash
  job older than 15 seconds may request a caption when inspected through a widget/job view or
  `/jobs full`; widget-role selection can consider usable built-in smol credentials independently
  of `retry.modelFallback`. Use isolated selected-local-only auth for release acceptance. Keep
  ordinary route request counts unchanged and account for any separately authorized auxiliary
  feature explicitly; no universal no-cloud/no-extra-request claim applies to inherited auth.
  Optional auto-learn capture remains tool-restricted and must preserve main history. Early fleet
  messages must not displace the worker's shared context and initial assignment.

## Runtime, model and profile bytes carried unchanged

All lanes keep common source `26fa28d0e7834515508fc07ac503164a6effc820` on upstream
`64d10fbf9f8e6bfc79ab0570b94674c5b9997929` and shared published model v3 SHA-256
`81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da`
(**20437521664 bytes**, revision `1cbd84e7221e51186bd7f093a149912d2489625b`).

| Lane | Carried component | Serving boundary |
| --- | --- | --- |
| RTX 5090 | `v0.7.0-qwen38-5090-beta.4`, image `7a5a7bb8`, server `bab3fd77`, config `751d22dc` | Kept `qwen38-5090-v0.13.0`, BF16 KV, DFlash2 K7, C2, strict-origin `/checkpoints-v013` |
| Native RTX 4090 | `v0.8.0-qwen38-4090-beta.1`, package `06526bdb`, server `c6f59e9e`, config `f00cfac9` | INT8 KV, DFlash2 K7, C1, 131072 context, 640 MiB admission headroom, 16512696320 B shared Host budget, 30 s pending timeout |
| Native RTX 3090 | `v0.8.0-qwen38-3090-beta.1`, package `040d5923`, server `72cd776b`, config `cbe67aae` | INT8 KV, DFlash2 K7, C2 over one 131072-token pool, 768 MiB headroom, 21881405440 B shared Host budget, 180 s timeout, 350 W serving cap |

Native profiles retain two extra device-state slots; `Group64` A8 and FP32 head logits remain off.
Both native lanes serve sequentially on port **18082**. No native promotion, runtime build,
model import, checkpoint migration or new performance result is part of this client patch.

The [v0.16.0 notes](../v0.16.0/NINFER_RELEASE_NOTES.md) remain the authority for runtime
measurements, original subjects and founder waivers: the RTX 4090 `log-024@0` speed-floor waiver,
the two RTX 5090 first-request-after-restart latency misses and the RTX 5090-only second-build
reproducibility exception. These disclosures are not converted into 18.15.0 observations or
new waivers. Existing lifecycle and multi-owner limitations are not closed by a client bump.

## Qualification and support boundary

Fresh acceptance must bind one frozen candidate, all **five routes / 31 executable blocks**, all
three exact stock binaries, both native public-URL installs, native candidate-profile probes and
complete restoration evidence. Preserve fleet on C1 RTX 4090 and fleet/fanout/parallel/compaction
on C2 RTX 3090. No changed-client result is inherited from v0.16.0. A real probe that does not
induce its preregistered boundary is unexercised, not passed.

macOS arm64 remains manual-SSH preview. Linux x64 evidence remains WSL2-scoped, not native Linux
OS qualification. Image input is limited to macOS and Windows clients against RTX 5090; neither
native lane nor Linux gains vision qualification. Results are owner-operated tester-equivalent,
not independent multi-owner outcomes, a security audit, an SLA or a general performance promise.

Founder-only publication follows exact-head review/CI, immutable URL/hash checks and
`verify_release.py --release v0.16.1 --require-ready --check-pins`. Public install entry points
continue to name published v0.16.0 until that publication is verified.
