# OMP NInfer v0.15.0 — stock OMP 18.14.0 with unchanged GPU lanes

**Staged client-only release, not published.** Stock Oh My Pi **18.14.0** replaces 18.12.6;
the RTX 5090 container and native Windows RTX 4090/RTX 3090 runtime components, model bytes,
serving profiles and limits remain unchanged from v0.14.0. This release also includes the
product tooling and documentation changes below; it does not rebuild an engine or switch a
native lane to DFlash2.

The published product remains [v0.14.0](../v0.14.0/NINFER_RELEASE_NOTES.md); use its
[immutable installation guide](https://github.com/alphastorm/omp-ninfer/blob/v0.14.0/docs/QUICKSTART.md)
until publication. The [prepared guide](../../docs/QUICKSTART.md) passed fresh acceptance on
candidate `af62e7662fdc7195f7c1c88f2278b15f63130eba`; it is not an installation recommendation
before publication. Client/platform, documented-route, public-install and restoration evidence
was re-executed, not inherited. Council approval remains a separate changed-scope gate.
Product publication remains founder-owned. Owner-operated, exact-profile 0.x release; no SLA.

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Compatibility](COMPATIBILITY.md)

Oh My Pi (coding-agent client) connects through OMP NInfer (qualified appliance and release layer)
to NInfer (inference engine) serving Qwen3.8 27B on one user-owned GPU.

## Composition — all three runtime lanes carried from v0.14.0

| Component | Exact identity | Serving boundary |
| --- | --- | --- |
| Oh My Pi | Unmodified upstream `v18.14.0`, source `31147f9d1a76608549821c3759f8487b4d66c72d`, tree `9a63b5bfbb5971962c44fca660744b0d75dcd2c2` | New stock client; fresh three-platform and five-route acceptance passed; macOS remains preview |
| RTX 5090 container | `v0.7.0-qwen38-5090-beta.3`; server `55f0b95a`, archive `b8f315bc`, image `760fb6be` on base `d4377ed0` | Unchanged BF16 KV, DFlash2 K7, two active requests, vision; kept `qwen38-5090-v0.13.0` profile |
| RTX 4090 native Windows | `v0.7.0-qwen38-4090-beta.3`; package `87038cfb`, server `5caa7780`, public config `b5cfbf50` | Unchanged INT8 KV, MTP3, one active request, `Group64` A8 off |
| RTX 3090 native Windows | `v0.7.0-qwen38-3090-beta.3`; package `a7637f66`, server `fedce425`, public config `d08d262b` | Unchanged INT8 KV, MTP3, one active request, `Group64` A8 off, 350 W serving cap |

All three runtime lanes retain source `2c6f423bd817b6534158553e1b34ab4959c43165` on upstream
`64d10fbf9f8e6bfc79ab0570b94674c5b9997929`. The model stays the published version 3 artifact
`81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da`
(20,437,521,664 bytes, revision `1cbd84e7221e51186bd7f093a149912d2489625b`). Native packages
retain CUDA 13.3 (sm_89/sm_86); RTX 5090 retains CUDA 13.1 (sm_120a). Runtime receipts retain
their original subjects and dates; they are not new performance measurements or acceptance of
the changed stock client.

## Stock Oh My Pi 18.14.0

The new client replaces 18.12.6 without a product fork, local client rebuild, compatibility shim,
or model-ID rename. Full upstream pins are in
[client-components.json](qualification/client-components.json).

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
  ignores stale usage, rejects non-reducing automatic candidates, preserves a completed main
  summary if an optional short summary fails (cancellation still throws), and carries split-turn
  extra context. These routes do not opt into native remote compaction. Compaction cut points and
  prompt bytes can change; production compaction quality and prefix-reuse equivalence are not inferred.
- **Loop guard:** configured `model.loopGuard` settings now reach custom Responses models. Leave
  the stock guard enabled; exact suffix-cycle detection and model-gated semantic heuristics are
  distinct. Long-loop cutoff behavior and false positives were not measured by the seven-check rehearsal.

## Product tooling and documentation since v0.14.0

These are product-side changes, not new runtime bytes or GPU qualification results.

- **Native screen arms:** `scripts/native_screen_arm.py` captures
  resumable, bounded scratch-install arms with isolated lifecycle state, empty-cache fresh starts,
  measured power, sealed shards and a complete `arm.json`. Production runs precede candidate runs;
  partial captures are not verdict inputs. Owner-controlled restoration remains a separate obligation.
- **Quality, fit and parity binding:** `scripts/bind_native_variant.py`
  and `scripts/verify_release.py` bind and validate native package,
  server, configuration and model identities before writing a replacement. A changed runtime needs
  a powered quality verdict, or 84/84 actual retained-output-byte comparisons for an unchanged-shape
  MTP rebuild. DFlash2 additionally needs a shipping-config 131K fit receipt and lane headroom.
  EXP-085's statistical rule is unchanged. The three carried runtime identities do not become new
  runtimes merely because these future-qualification tools ship.
- **Guide-derived client defaults:** measurement probes and native campaign launchers derive their
  omitted model selectors from the existing guide fragments instead of maintaining another alias.
  Explicit selectors remain usable by standalone probes; free-form receipt lane labels do not select
  a model. Client acceptance follows the selected route, including RTX 3090's `q38-ninfer`, and the
  campaign quality child requires the launcher's explicit selector.
- **Complete WSL2 instructions and safe reruns:** the guide includes the Linux client descriptor,
  checksum/version checks, local key, loopback route, fail-closed check and restoration direction.
  Key/config reruns preserve existing matching files and refuse differing files; Windows native
  failures stop the guide. Provider blocks load the key and clear `PI_OPENAI_STATEFUL` before a
  merged-config refusal. This adds no native Linux OS or Linux vision qualification.
- **Acceptance and release binding:** corrected RTX 5090 attempts need disclosure before effects;
  route-runner tests use an ephemeral tunnel port. Composer/verifier checks bind restoration and
  route status, G4 ledger agreement, runtime-base receipts and native dependency SBOMs. These checks
  do not manufacture acceptance or close every predecessor fault-injection follow-up.
- **Read-only upstream watch:** the [watch receipt](../../docs/measurements/2026-10-29-upstream-watch.json)
  records deltas from the shipped engine and client baselines and separately watches
  `Neroued/ninfer`'s `feat/qwen4-27b-ops` branch. Watching a branch does not adopt its code, change
  the served model or qualify Qwen 4.
- **Windows CI coverage:** P15 program and lane pushes run the product's CI jobs, including native
  Windows portable Python contracts and PowerShell parsing, alongside Ubuntu/macOS contracts and
  host-free acceptance dry-runs. GPU-free checks do not prove native CUDA compilation or live serving.

## P14 experiment ledger — historical results, not v0.15.0 acceptance

| Entry | Recorded result | Release boundary |
| --- | --- | --- |
| [EXP-098 — native DFlash2 gates and fit](../../docs/measurements/2026-10-27-native-dflash2-gates-and-fit.json) | On the v0.13.1 control lineage, RTX 3090 passed the 108-role speed gate at ×1.29968 (minimum 0.97987) and a separate 131K fit/true-cold durability proof at 21,968 MiB peak with 768 MiB headroom. RTX 4090's ×1.26362 aggregate missed the per-case floor on `log-024@0` (0.945889, reproduced at 0.9451). | These are historical experimental subjects, not the carried beta.3 MTP3 profile or a new shipping DFlash2 package. Both native lanes remain MTP3. |
| [EXP-099 — native small-T tensor-core decode](../../docs/measurements/2026-10-27-native-small-t-tensor-core-decode.json) | C1 decode improved +39.8% on RTX 3090 and +8.3% on RTX 4090, but 55/84 and 58/84 role outputs diverged against a maximum of eight. RTX 3090 also failed the 150-pair leak screen (4 baseline-only vs 12 candidate-only; p=0.0384). | Rejected candidate; no small-T tensor-core decode gain ships here. |
| [EXP-100 — native attention and `Group64` A8 prefill](../../docs/measurements/2026-10-27-native-group64-a8-prefill.json) | Byte-identical attention prefill specializations shipped in v0.14.0. The A8 candidate failed the RTX 4090 200-pair leak screen (five ON-only changes, p=1/32); RTX 3090 passed (four ON-only, p=1/16) but the founder kept it off. | The passing RTX 3090 verdict is retained, not rewritten as failure. `Group64` A8 stays off on both carried native lanes. |

## Unchanged runtime, state and upgrade boundaries

RTX 4090 keeps `qwen38-4090-native-v0.7.0-beta.3`, package
`87038cfb749e00c3af4e590ddcde03f1e7628c8a8c8793b7137f770213865437`, public configuration
`b5cfbf50d264831832fbe69458b56629a65b0d5b5295ec8bbbd4ea2d73002c38`, two extra device-state
slots and 640 MiB admission headroom. RTX 3090 keeps `qwen38-3090-native-v0.7.0-beta.3`, package
`a7637f6672d235e5abb4e54dbdb0689e43a96385b6200c647196aae66b7f42f3`, public configuration
`d08d262bfe939ed9aaa6f7053ab8a8304fb7e3fef50dad3cb9329e28fb4ece15`, four extra slots,
768 MiB admission headroom and its 350 W serving cap. Both remain 131,072-token INT8 MTP3,
one active request and a 30 s pending timeout. Their beta.3 qualification lineages have no
predecessor: rollback is `not_applicable`, zero directions, not an inherited beta.2 upgrade result.
The v0.13.1-to-v0.14.0 RTX 3090 stop-before-upgrade prerequisite remains relevant only to owners
still making that historical 300 W-to-350 W transition; this client-only release changes neither cap.
No installer fix from a later engine source is retroactively present in these packages.

RTX 5090 keeps `qwen38-5090-v0.13.0`, configuration
`751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47`, BF16 KV, DFlash2 K7,
two active requests, and the exact image
`ghcr.io/alphastorm/ninfer-runtime@sha256:760fb6bea925eb26d4fa53ab87a126494b69ba7bcfed515d23dee7afa65cdb2a`.
The v0.14.0 first-build reproducibility exception remains attached to those same bytes; this
release does not establish a reproducible rebuild. See the
[v0.14.0 qualification](../v0.14.0/qualification.json) for the carried runtime observations.

There is no new runtime/profile/store migration in this client-only release. Native stores remain
`session-checkpoints-v3` under each immutable component instance; the container retains
`/checkpoints-v013`. Keep historical roots untouched; do not import generations across different
runtime/model/profile identities. No new rollback direction or universal warm reuse is inferred.
Strict checkpoint origin authentication remains mandatory. Within one API-key principal,
`prompt_cache_key` names a session capability; use unique high-entropy keys and do not share the
principal among mutually untrusted clients. Saves remain best effort. Windows NTFS
`ntfs-write-through` is not POSIX `fsync` or a power-loss guarantee.

## Fresh client and route acceptance

Fresh acceptance passed on frozen candidate `af62e7662fdc7195f7c1c88f2278b15f63130eba` on
2026-10-30. Both initial windows passed and restored; no corrected attempt, canonical promotion
or production upgrade was performed. Runtime qualification carries unchanged, but these changed-client
observations were executed fresh. The receipts are owner-operated tester-equivalent evidence,
not independent external-user outcomes.

| Acceptance evidence | Observed result |
| --- | --- |
| Exact stock OMP 18.14.0 platform and live tool/continuation/restart/resume/fail-closed checks | All three freshly downloaded stock binaries matched their published asset hashes and `omp/18.14.0`. Typed read-tool/result, exact continuation and unavailable-route fail-closed checks passed on [macOS arm64](acceptance/darwin-arm64-18.14.0.json) (preview), [Windows x64](acceptance/windows-x64-18.14.0.json) and [Linux x64 under WSL2](acceptance/linux-x64-18.14.0.json). The macOS documented route also returned the exact nonce after server restart and client resume. Image input passed on macOS/Windows against RTX 5090 only. |
| Final-candidate guide execution: five routes/31 composer-addressed blocks plus WSL2 checks | [All five routes passed](acceptance/documented-routes.json): RTX 5090 host 2/2, macOS 10/10, Windows 5/5, native RTX 4090 7/7 and RTX 3090 7/7. Pre-publication candidate-clone substitutions are explicit. The WSL2 Linux client additionally passed documented URL/hash installation, typed tools, continuation and runtime-outage checks; this is not native Linux OS or Linux vision qualification. Subsequent guide edits are prose-only; executable blocks are unchanged. |
| RTX 4090 and RTX 3090 public-install identities and observed install outcomes | Both fresh first-lineage documented installs passed with the new stock Windows client after preserving the canonical roots and staging. Separate [RTX 4090](acceptance/rtx4090-public-install.json) and [RTX 3090](acceptance/rtx3090-public-install.json) public-URL checks verified all manifest asset hashes and served identities; both installers returned `already_installed` for the unchanged beta.3 packages (`87038cfb` / `a7637f66`), changed no lifecycle pointers and requested no runtime start. Both lineages have no predecessor: rollback `not_applicable`, zero directions. |
| Independent container/native restoration audits and observed hold durations | [Independent restoration passed](../../docs/measurements/2026-10-30-v0150-acceptance-restoration.json). RTX 5090 restored the same digest-pinned `760fb6be` image, healthy and `unless-stopped`, checkpoint mount, checkout, key, directories and Windows markers/tasks; the route container and hold were removed after **403.884 s**. Both native restoration/final audits passed, including state/ACL/task/power/holds/client files/directories/staging, with cross-lane census unchanged; driver windows were **371.326 s** (RTX 4090) and **394.389 s** (RTX 3090). Canonical beta.3 tasks returned Ready/stopped at owner baselines 450/370 W, without a process, listener or lease. |

The [composed acceptance](acceptance/composed-external-installation.json) binds these fresh
observations separately from carried runtime qualification. Root compatibility authority, profiles
and launchers were lane-pinned to this candidate. The changed-scope product council and carried
fork-council binding, final manifest evidence pin, strict ready verification and founder-owned
publication remain separate gates; acceptance grants no publication authority.

## Support boundaries and next work

macOS remains preview; Linux client evidence is WSL2-scoped. Native lanes serve sequentially on
port `18082`. Native vision or DFlash2 serving, concurrent native serving, multi-GPU inference,
multi-tenancy, silent cloud fallback and independent external-user outcomes are not qualified.
The [v0.14.0 review ledger](../v0.14.0/review/runtime-ledger.json) retains its original subjects,
reproducibility exception and P2 deferrals; it is not council approval for this composition.
The `alphastorm/ninfer#48/#49` engine/installer fixes are not present in any of the three carried
runtime components. RTX 4090 DFlash2 K6/K5 exploration and its failing floor case remain deferred.

**Next:** native RTX 3090 DFlash2 is deferred to **v0.15.1** after a found runtime defect:
fork-after-resume fails with `Native could not release an unreferenced checkpoint owner`.
The fix and shipping-package qualification remain required; no delivery date or unmeasured
performance, quality or durability outcome is claimed.
