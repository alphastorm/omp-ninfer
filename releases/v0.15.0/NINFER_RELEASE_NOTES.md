# OMP NInfer v0.15.0 — stock OMP 18.14.0 and the RTX 3090 DFlash2 K7 candidate

**Staged, not published.** The published product remains
[v0.14.0](../v0.14.0/NINFER_RELEASE_NOTES.md); use its
[immutable installation guide](https://github.com/alphastorm/omp-ninfer/blob/v0.14.0/docs/QUICKSTART.md)
for a published installation. This stage prepares the stock client and the exact F2 RTX 3090
component, with completed package qualification, fit/durability and transaction rehearsals.
The [manifest](manifest.json) still carries the v0.14.0 RTX 3090 MTP3 row: its replacement is
**not yet published or bound**. The lead cuts and binds it only after the remaining quality,
speed and probe gates pass, then freezes and accepts the final candidate. No predecessor
platform, public-install or documented-route approval transfers. The fork council is closed
within its stated scope; final product-tooling review and publication remain separate.

Oh My Pi (coding-agent client) connects through OMP NInfer (qualified appliance and release layer)
to NInfer (inference engine) serving Qwen3.8 27B on one user-owned GPU.

## Staged composition and fast-track scope

| Component | Exact identity in this host-free stage | Final v0.15.0 scope |
| --- | --- | --- |
| Oh My Pi | Unmodified upstream `v18.14.0`, source `31147f9d1a76608549821c3759f8487b4d66c72d`, tree `9a63b5bfbb5971962c44fca660744b0d75dcd2c2` | New stock client; fresh platform and live route acceptance required |
| RTX 5090 container | Carried `v0.7.0-qwen38-5090-beta.3`, source `2c6f423bd817b6534158553e1b34ab4959c43165`; server `55f0b95a`, archive `b8f315bc`, image `760fb6be` on base `d4377ed0` | Unchanged from v0.14.0; no runtime rebuild or new engine fixes |
| RTX 4090 native Windows | Carried `v0.7.0-qwen38-4090-beta.3`, source `2c6f423b`; package `87038cfb`, server `5caa7780`, public config `b5cfbf50` | Unchanged MTP3 from v0.14.0; no DFlash2 or engine rebuild |
| RTX 3090 native Windows | Prepared replacement `v0.8.0-qwen38-3090-beta.1`, F2 source `2af6b3dec467e61d284889c69e903eef464bda97`; package `8536cdff` (971,617,000 bytes), server `05cb97e4`, public config `55788a64`; receipt staged, manifest row still carried until gated rebind | DFlash2 K7, INT8 KV, C1, zero extra device-state slots, 768 MiB admission headroom, 350 W |

The model stays the published version 3 artifact
`81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da`
(20,437,521,664 bytes, revision `1cbd84e7221e51186bd7f093a149912d2489625b`).
The carried runtime bytes and their qualification receipts retain their original subjects and
dates; they are not measurements of the F2 RTX 3090 build. After the gated rebind, this release
will deliberately have different engine sources on RTX 3090 versus the two carried lanes.

## Stock Oh My Pi 18.14.0

The new client replaces 18.12.6 without a fork, rebuild, compatibility shim, or model-ID rename.
Full pins are in [client-components.json](qualification/client-components.json).

| Platform | Upstream raw asset | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| macOS arm64 (preview) | [omp-darwin-arm64](https://github.com/can1357/oh-my-pi/releases/download/v18.14.0/omp-darwin-arm64) | 214,816,912 | `608843959ab34295d52460dd09dd7d548b6c903c08a83c67954c2d4c36fd1f5a` |
| Windows x64 | [omp-windows-x64.exe](https://github.com/can1357/oh-my-pi/releases/download/v18.14.0/omp-windows-x64.exe) | 242,797,056 | `620a5935cdb6a9ed52d8b0c93892d6b5bb84155244a98f3be82af0455177bf29` |
| Linux x64 (WSL2 route) | [omp-linux-x64](https://github.com/can1357/oh-my-pi/releases/download/v18.14.0/omp-linux-x64) | 276,244,656 | `e7dd2b606c4ebe9d1a7bcfad1b8820db968cd6b05409fed1c6bc8db0b6a95a8f` |

The [host-free client-upgrade review](../../docs/measurements/2026-10-30-omp-18140-client-upgrade-review.json)
records the source predicates, all three downloaded asset identities, and two seven-check macOS
stub rehearsals. Those rehearsals demonstrate client semantics, not GPU inference, editing quality,
real NInfer checkpoint survival, or acceptance of this prepared guide.

- **Bundled-runtime security:** upstream release binaries are rebuilt with **Bun 1.4.4**. The
  [18.13.0 release](https://github.com/can1357/oh-my-pi/releases/tag/v18.13.0) records the fixes for
  **CVE-2026-91403** (compromised eMudhra intermediate certificates) and **CVE-2026-111497** (Brotli
  decoder out-of-bounds write); 18.14.0 retains the build pin. Changing YAML or a version label
  does not update the old executable. No independent reproducible client rebuild or extraction
  of an embedded Bun runtime version is claimed.
- **Qwen 3.8 replace-edit asymmetry:** stock family classification recognizes `qwen3.8-27b`, so
  native RTX 4090 and the `ninfer-heavy/qwen3.8-27b` selector get the `replace` default. The opaque
  `q38-ninfer` alias used by RTX 3090 and RTX 5090 remains `hashline`. This is source-reviewed,
  not an exercised editing benchmark. Keep exact IDs; do not rename a server or force an edit
  policy to trigger family detection. Explicit model variants and strict edit-mode controls remain
  owner choices; a settings-derived `hashline` alone is not necessarily a pin.
- **Exact model selection:** retain `ninfer-beta/q38-ninfer`, `ninfer-native-3090/q38-ninfer`,
  `ninfer-native-4090/qwen3.8-27b`, and `ninfer-heavy/qwen3.8-27b:medium`. The suffix selects effort;
  mistyped provider-qualified IDs now fail rather than fuzzy-matching a sibling.
- **Responses and compaction:** retain per-model `statefulResponses: true`,
  `includeEncryptedReasoning: false`, and `supportsReasoningSummary: false`, and clear inherited
  `PI_OPENAI_STATEFUL`. Default compaction for a 131,072-token window triggers strictly above
  111,412 tokens, including prompt/tool overhead. The client rework bounds retained history,
  ignores stale usage, preserves a completed main summary if an optional short summary fails,
  and carries split-turn extra context. These routes do not opt into native remote compaction.
- **Loop guard:** configured `model.loopGuard` settings now reach custom Responses models. Leave
  the stock guard enabled. Long-loop false positives and production compaction quality were not
  measured by the seven-check rehearsal.

## RTX 3090 DFlash2 K7 — gate results to bind before the lane pin

The prepared native component is `v0.8.0-qwen38-3090-beta.1` from frozen F2 source
`2af6b3dec467e61d284889c69e903eef464bda97`. Its measured profile is INT8 KV, 131,072-token
context/KV, one active request, DFlash2 draft window 7 with the optimized proposal head, zero extra
device-state slots (four under the predecessor MTP3 profile), 768 MiB admission headroom, and a 350 W
serving cap. The native fit seam uses `Q4_G64_FP16` draft MLP `gate`/`up` weights and a host-mapped
token embedding. `Group64` A8 prefill and native small-T tensor-core decode remain off.
The exact shared Host budget is **13,291,470,848 bytes / 12,675.734375 MiB**:
8,192 MiB plus 24 predecessor Host state slots at the measured **195,897,344 bytes** each.
Startup and authenticated status agree on **473,497,600 converted-device bytes** and
**1,350,860,800 host-mapped bytes**.

Only the screen verdict/bounds, speed ratios/byte counts and probe results remain placeholders:

| Shipping-package gate | Measured result or remaining receipt | Fixed pass rule |
| --- | --- | --- |
| Powered EXP-101 quality screen and determinism | `<RTX3090_SCREEN_VERDICT_AND_BOUNDS>` | Unchanged EXP-085 statistical rule; 1,120 prompts per arm plus the 80-prompt determinism subset, production MTP3 arm first, both at 350 W |
| Depth-0 84-role ABBA decode vs v0.14.0 MTP3 | `<RTX3090_SPEED_RATIO_MIN_AND_BYTE_IDENTITY_COUNTS>` | Weighted speed ratio at least 1.08; every case at least 0.95; retain output-byte identity counts, not a parity assumption |
| 131K fit and true-cold durability | **PASS**: 131,072 context/KV; zero extra slots; 768 MiB admission headroom; 21,968 MiB peak used / 2,358 MiB minimum free across 920 samples; exact 130,048-token retrieval. True-cold cached tokens **0**, restored **3,066**; all **32** generated token IDs and retained output bytes identical. Explicit save and managed-stop restore passed. | At least 768 MiB admission headroom; exact retained-byte continuation, not digest-only parity |
| Agent fanout, warm arrival, agent mix, and restart probes | `<RTX3090_AGENT_PROBE_RESULTS>` | Each probe at or above the v0.14.0 baseline; the reduction from four extra slots to zero is explicitly exercised |

**All 15 frozen managed qualification phases passed**, and both clean native builds have
complete-byte identity across **34/34 EXE/DLL files**. The
[qualification receipt](qualification/rtx3090.json) is
`48e517c8a794217e4d4d1164d445ea3b8bf59d4c8c203fe54416547d39f57c2b`;
the [fit receipt](qualification/rtx3090-windows-native.fit.json) is
`1716e71d1bbcecdc2fbc758747653579d63443fcb2bfb9c372985951d267eebf`.
The 15-phase run used an isolated port-only equivalent config (18210 versus public 18082);
it did not activate the production route. Its first-scratch-lineage rollback remains
`not_applicable`, zero directions. The separate actual-predecessor rehearsal below is the
upgrade evidence. Frozen C1 decode was **148.142689 tok/s** (4,541 computed prefill / 1,024
completion tokens); that single-candidate result is not an ABBA speed ratio or screen verdict.

The cut script will publish these exact mirrored assets under
[`v0.8.0-qwen38-3090-beta.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.8.0-qwen38-3090-beta.1):

| Asset | Prepared publication URL | SHA-256 |
| --- | --- | --- |
| Native package | [ninfer-rtx3090-native-v0.8.0-beta.1-windows-x86_64-cuda13.3-rtx3090.tar.gz](https://github.com/alphastorm/ninfer/releases/download/v0.8.0-qwen38-3090-beta.1/ninfer-rtx3090-native-v0.8.0-beta.1-windows-x86_64-cuda13.3-rtx3090.tar.gz) | `8536cdff395be30e91ae8b2b10c1f338b88bff9bc450d7d22a0f1e4eff52dd0a` |
| Closed outer checksums (ten assets plus this file) | [SHA256SUMS](https://github.com/alphastorm/ninfer/releases/download/v0.8.0-qwen38-3090-beta.1/SHA256SUMS) | `684df9cf44f2559b1f650106ec9966722e86a2ab9b73d0c5ca5c4c7c88932a5f` |
| Source archive | [ninfer-rtx3090-native-v0.8.0-beta.1-source.tar.gz](https://github.com/alphastorm/ninfer/releases/download/v0.8.0-qwen38-3090-beta.1/ninfer-rtx3090-native-v0.8.0-beta.1-source.tar.gz) | `777013ec7dfedc3512c317db235023fdc88cc209382f6630d362c1899bb3a1bf` |
| SPDX 2.3 | [package-stem.spdx.json](https://github.com/alphastorm/ninfer/releases/download/v0.8.0-qwen38-3090-beta.1/ninfer-rtx3090-native-v0.8.0-beta.1-windows-x86_64-cuda13.3-rtx3090.spdx.json) | `0d3f5db9e412709f75877e052567dee9ef5c98075024800c55020c764211d17b` |
| Dependency CycloneDX 1.5 | [package-stem.cdx.json](https://github.com/alphastorm/ninfer/releases/download/v0.8.0-qwen38-3090-beta.1/ninfer-rtx3090-native-v0.8.0-beta.1-windows-x86_64-cuda13.3-rtx3090.cdx.json) | `373f2adc7724c05034b3e0b1b1ce4929df399a328c9fd7401cab173f13442695` |

Server SHA-256 is `05cb97e446a1c872005c875f0b214a99553888ac40f021e6f99a6df9a9a0672d`;
the exact [packaged config](profiles/rtx3090/server-config.json) is
`55788a647fb250a37754076a2d8f28d542119fb88191428bbaeb7be076ee43aa`.
Cut preflight passed without publication. Historical native DFlash2 experiments do not replace
shipping-package gates; no RTX 4090 EXP-102 or RTX 5090 build/T1 campaign is in scope.
The final candidate still needs fresh stock-client and documented-route/public-install acceptance,
restoration evidence, product-tooling review, composition and immutable pins.

## Fork council disposition

Fork sequence `omp-ninfer-v0.15.0-fork-5caa4a48` is **closed by lead verification** through
`CR-20261030T122157Z-2af6b3de-lead-fix`, preserving the initial full council on F and the
F2 Host-layout data/test correction. All **11/11** rows are final: **2 accept / 8 defer /
1 mitigate**, no in-scope residual P0/P1. Closed ledger SHA-256:
`c7e4eb50f7707126540a865f33abd5e6b9b0f9c947611e6ce0fa2b805c427926`;
content-safe runtime summary:
`9fd8185ac06eb7159f8beda5c80ee52ac10d6cac44292c45235927f8d9025d56`.
[Issue #116](https://github.com/alphastorm/omp-ninfer/issues/116) records the residuals for
v0.15.1; the Linux io_uring items must close before the next RTX 5090 rebuild.
This closes fork dispositions only, not product-tooling review, route acceptance or publication.

## Carried RTX 4090 and RTX 5090 boundaries

RTX 4090 keeps `qwen38-4090-native-v0.7.0-beta.3`, INT8 KV, MTP3, one active request, two extra
device-state slots, 640 MiB admission headroom, and public configuration
`b5cfbf50d264831832fbe69458b56629a65b0d5b5295ec8bbbd4ea2d73002c38`.
RTX 5090 keeps `qwen38-5090-v0.13.0`, configuration
`751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47`, BF16 KV, DFlash2 K7,
two active requests, and the exact image
`ghcr.io/alphastorm/ninfer-runtime@sha256:760fb6bea925eb26d4fa53ab87a126494b69ba7bcfed515d23dee7afa65cdb2a`.
The v0.14.0 RTX 5090 first-build reproducibility exception remains attached to those same bytes;
this release does not establish a reproducible rebuild. See the
[v0.14.0 qualification](../v0.14.0/qualification.json) for the carried runtime observations.
A new stock client still requires fresh acceptance on both unchanged lanes.

## Upgrade and rollback

- **RTX 3090 upgrade from v0.14.0 is equal-cap, 350 W to 350 W.** The older v0.13.1-to-v0.14.0
  300 W-to-350 W stop-before-upgrade restriction is not this transition. The F2 component contains
  `alphastorm/ninfer#48`'s installer upgrade/rollback changes. Actual shipped beta.3 predecessor
  rehearsals **passed** running-lane upgrade, forced post-activation first-Start refusal with
  rollback to the healthy incumbent, and durable-activation interruption with repair followed by
  successful same-instance reinstall. Summary SHA-256:
  `b107c3287c560ab102eacb287bec1c7ec5c801617087055dbf5fb5156dc83974`.
  All three restored 370 W with no scratch process/task/lease and canonical state unchanged.
  The forced failure happened before candidate lease acquisition/server launch; the interruption
  was after durable activation, before task registration. Neither proves `prior_paused=true`,
  failed live-candidate Stop/final-save/Kill containment or mkdir-before-journal repair
  ([#116](https://github.com/alphastorm/omp-ninfer/issues/116)). Keep prior roots and inspect stop refusals.
- **MTP durable sessions do not carry across the RTX 3090 upgrade to DFlash2.** The new immutable
  instance has its own `cache/<release-instance-id>/session-checkpoints-v3` store, and the durable
  engine fingerprint binds the speculative backend. Never copy MTP3 generations into a DFlash2
  store. Preserve old roots and replay authoritative OMP transcripts for a fresh prefill.
- **Carried RTX 4090/RTX 5090:** runtime/model/profile bytes stay unchanged. Fresh client and route
  acceptance is separate from that carry-forward; no new rollback direction or checkpoint
  migration is inferred. Keep the documented fail-closed config and per-provider limits.

Strict checkpoint origin authentication remains mandatory. Within one API-key principal,
`prompt_cache_key` names a session capability; use unique high-entropy keys and do not share the
principal among mutually untrusted clients. Saves remain best effort. Windows NTFS
`ntfs-write-through` is not POSIX `fsync` or a power-loss guarantee. macOS remains preview; Linux
client evidence is WSL2-scoped. Native lanes serve sequentially on port `18082`; native vision,
concurrent native serving, multi-GPU inference, multi-tenancy, and silent cloud fallback remain
unsupported.

## Deferred to v0.15.1

- RTX 4090 DFlash2 exploration at K6/K5, including its failing floor case; no RTX 4090 DFlash2
  performance or quality result is advertised in v0.15.0.
- `alphastorm/ninfer#48` and `#49` engine/installer fixes for the **RTX 4090 and RTX 5090** carried
  components. They are not retroactively present in source `2c6f423b`. The prepared F2 RTX 3090 source
  contains that fix train; the remaining screen/speed/probe gates and final binding are still required.
- Council P2 deferrals, including the existing checkpoint/admission, tooling, and reproducibility
  residuals disclosed in the [v0.14.0 review ledger](../v0.14.0/review/runtime-ledger.json). The
  fork council is closed as stated above, with its additional residuals in #116. Final
  product-tooling review remains separate.
