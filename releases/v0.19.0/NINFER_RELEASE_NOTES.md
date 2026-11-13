# OMP NInfer v0.19.0 — bounded pressure saves, RTX 3090 beta.4, and stock OMP 18.20.0

> The RTX 5090 runtime beta.8 and the RTX 3090 native beta.4 carry the bounded pressure-save change
> ([fork #122](https://github.com/alphastorm/ninfer/pull/122)); the RTX 4090 native beta.3 is carried unchanged from
> v0.18.0; the client is stock Oh My Pi **18.20.0**. Component cuts, current hardware qualification, all **31/31**
> documented blocks, three stock-client platform checks, both native campaigns and public installs, independent
> restoration and the release reviews passed on candidate `6b22f219`.

## Selected identities

- Two fork sources, one serving codebase, plus one carried native component:
  - RTX 5090 runtime: `41f89b310b443481db5917a01a2b45e49f85e723`, which is fork `main` `8b3f498f` (bounded pressure saves) plus a test-only fixture correction and the native beta.4 identity bump.
  - RTX 3090 native beta.4: `15c3e3959c0a6167f799e9383482ec4e03db9cad`, a descendant of `41f89b31` that adds only the RTX 3090 qualification power-check fix and the corrected Windows release note ([fork #126](https://github.com/alphastorm/ninfer/pull/126)). Its diff from `41f89b31` touches the native qualification tool and its test, the RTX 3090 release spec's managed power envelope and `packaging/windows/RELEASE_NOTES.md`; no serving source changed, so the RTX 5090 and RTX 3090 components run identical serve code.
  - RTX 4090 native: **carried unchanged** from v0.18.0 at `v0.8.0-qwen38-4090-beta.3`, source `48c8ac4644322f024b5c3bd5b657af5874567251`, package `ac41700ac2bb9fb171188f35e73481cfd9f1140c5781320b1e6304ee760d7166`, with its byte-identical v0.18.0 component qualification. It does **not** include the bounded pressure saves (fork #122) in this release; it never showed the [fork #89](https://github.com/alphastorm/ninfer/issues/89) class on its C1 lane, and it re-cuts with the next engine freeze.
- RTX 5090 container runtime (published): `v0.7.0-qwen38-5090-beta.8`, source `v0.7.0-qwen38-5090-source.8`, image receipt `v0.7.0-qwen38-5090-runtime-beta.8`. Server binary `147da36b05c2795fb50bb0a38f9756f782f0b05ae08e4fed34a3f58b56c2eec0`, image `sha256:c3ec151b992b4989c850a856aebaa463b5bf5728a60aa084906888ce40db6b71`. It succeeds `v0.7.0-qwen38-5090-beta.7`.
- RTX 5090 deployment profile `qwen38-5090-v0.13.0` and configuration `751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47` are unchanged from v0.18.0: the same serving vector, including origin authentication, with the new server binary.
- RTX 5090 host checkpoint store: `checkpoints-v019`; the container mount remains `/checkpoints-v013`. Keep `checkpoints-v018`, `checkpoints-v017`, `checkpoints-v013` and the legacy `checkpoints` store untouched; no generation is imported.
- RTX 3090 native: `v0.8.0-qwen38-3090-beta.4`, selected profile `native-v0.8.0-beta.4-tc-rtx3090`, cut from `15c3e395`. RTX 4090 native: `v0.8.0-qwen38-4090-beta.3`, default profile, carried from v0.18.0 (no new cut).
- Stock unmodified Oh My Pi **18.20.0**, source `c308970263ae13744ea15ab67302e3dac840e266`, tree `ba890953dd69eb4bf73bb7233bbe50ccfacd6912`, upstream release `443638329`.
- The published Qwen3.8 27B v3 model is unchanged: `81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da`, 20,437,521,664 bytes.
- Reused runtime base: `runtime-base-a87de361-20261103`, `ghcr.io/alphastorm/ninfer@sha256:28857182859a8f4993090521899b11a3f8676cb174c59adc626485e9f01472a3`. The beta.8 image receipt binds this base and its unchanged receipt (`cf0fe8e668920eb54f8c724d9607ef8b7b2861c778330be6a8d13887cc9268ca`). Reusing the base carries no runtime qualification.

## RTX 5090 beta.8 runtime evidence

- The exact-source release-candidate batch at `41f89b31` passed all 12 phases (`qualification/runtime-rc.json`). The packaged build identity binds that source and server binary (`qualification/runtime-build-identity.json`).
- On the published image, pulled anonymously by digest with the exact serving profile and a fresh checkpoint store, the lane gate passed (`qualification/rtx5090.json`). A cold 130,048-token prefill returned the exact expected output, decode measured 181.71 tok/s, and the agent-protocol and restart gates passed.
- Anonymous downloads of the binary archive, SPDX SBOM, checksum set, source archive, image receipt and runtime-base receipt matched the published digests (`qualification/runtime-artifacts.json`).

## Reviews

- The runtime source review of `41f89b31` closed with no confirmed P0 or P1 finding. Its residuals are deferred to [fork #123](https://github.com/alphastorm/ninfer/issues/123) and listed below.
- A focused review of the native power-check change at `15c3e395` found no P0 or P1 finding. Two diagnostic-evidence gaps in the native qualification harness are deferred to [fork #127](https://github.com/alphastorm/ninfer/issues/127): a telemetry poll error drops the managed-C1 failure receipt, and a passing receipt omits an explicit empty failure list. Neither weakens the gate, which stays fail-closed.
- The RTX 3090 managed C1 power check now proves the 350 W cap on every sample and bounds the 1-second reading at 355 W ([fork #126](https://github.com/alphastorm/ninfer/pull/126)). The packaged Windows release note at `15c3e395` states the store-quota behavior correctly.

## Bounded pressure-save refusal

[Fork #122](https://github.com/alphastorm/ninfer/pull/122) bounds an unsettled pressure save to six retries or 10 seconds. A pressure save refused for a retryable reason emits one `pressure` / `abandoned` receipt and releases its continuation instead of keeping admission latched behind the outstanding save. Retryable reasons are filesystem capacity, an I/O outage and a stale tag. Filesystem capacity covers a full volume or a filesystem quota (`ENOSPC`, `EDQUOT`, Windows errors 112, 39 and 1295), reported as `capacity`. This does not turn a refused save into durable state or promise successful shutdown saves. Authoritative OMP transcripts remain the recovery boundary.

**The store's own quota is not on this path.** A refusal from the checkpoint store quota (`--session-checkpoint-quota-mib`, reason `quota`) is terminal. It settles on the first refusal, without retries, and emits only the ordinary `save` / `refused` / `quota` receipt: no `pressure` / `abandoned` receipt and no `abandoned_total` increment. Monitoring that counts abandonment receipts to detect turns released without a durable copy must count store-quota refusals separately.

A full-volume refusal whose prepared export retires re-arms itself on that progress, so its six retries can finish in about 3 seconds rather than at fallback pace (one real-process run recorded 7 attempts in 2,937 ms). That is within the bounded policy.

Known residuals, deferred to the next engine change in [fork #123](https://github.com/alphastorm/ninfer/issues/123):

1. **An already-queued retry can be read as a refused deferral.** An enqueue for the same session can land between the queue pop and the coordinator lock. A retryable refusal of that run then records `deferral_refused`. A pressure victim settles early, with an abandonment receipt, although a retry is already queued; an automatic entry loses that one retry.
2. **Busy retries can starve a persistent deferral.** With at least four continuously ready Busy pressure victims ahead of it, a persistently refused save can stay pending beyond its 10-second window, retaining its continuation.

Neither residual affects the bounded-settlement path that fork #122 proved. Each needs a narrow interleaving or load shape, and neither fabricates a durable acknowledgement. Fork #123 also tracks a pre-existing matching-tag overwrite in `enqueue` and two evidence gaps.

The pressure-save HTTP 503 failure tracked in [fork #89](https://github.com/alphastorm/ninfer/issues/89) passed exact-lane acceptance on the RTX 3090 in this release (see Acceptance); these notes do not claim it is closed for every load shape. RTX 3090 component-chain evidence from `15c3e395`: GREEN; 2 committed handoffs, 0 HTTP 503 events, 0 queue timeouts; restored 370 W, owner leases absent. The fixture-only fix, the qualification check fix and the identity bump do not waive release-candidate, native-chain or route gates.

## Stock OMP 18.20.0 client and Windows wire changes

The [source intake review](../../docs/measurements/2026-11-13-omp-18200-client-upgrade-review.json) covers the v0.18.0 client to 18.20.0. All three exact upstream executable identities come from the authenticated current client descriptor. Source review and download integrity are not client execution or live qualification.

The rendered bash description removes the Windows emulated-bash/not-cmd-or-PowerShell guidance and its Windows path/environment reminders. The common description now advertises runtime builtins ahead of PATH. Native Windows command/path/PATHEXT behavior and the changed system/read/task/edit descriptions require typed-call, rendered-body and linked-result observations on both native routes and the RTX 5090 Windows route. A read-only marker probe does not qualify bash, edits or tasks.

The carried Responses serializer, tokenizer and local fragments do not establish equality of the entire tool, compaction or storage trees. Preserve explicit `tokenizer: qwen3` on opaque model IDs, `[low, medium, xhigh]` effort clamps, stateful Responses settings, retry/fallback/update/setup opt-outs and C2/C1/C2 provider caps. Fresh continuation, fail-closed, compaction and control-recall evidence remains required. No hosted model, cloud fallback or optional secret/browser feature is newly qualified.

## Native same-profile identity rule

[#171](https://github.com/alphastorm/omp-ninfer/pull/171) lets a non-default native profile use identity-first only against the **published incumbent of that same profile**: RTX 3090 tc beta.4 versus the published beta.3 tc package. The carried RTX 4090 beta.3 is not re-measured in this release, so no identity, speed or parity decision applies to it. The sealed 80-prompt determinism subset must have byte-identical outputs and the complete speed declaration/ABBA still runs. Any output difference requires the powered EXP-085 fallback; a matching source label or counts-only receipt is not identity evidence. RTX 3090 tc beta.4 passed identity-first: all 80 sealed determinism outputs and all 84 complete-ABBA speed cases are byte-identical to the published beta.3 tc package, and the complete ABBA measured 1.000× role-weighted (minimum case 0.997×).

## Acceptance tooling and #161 follow-ups

- [#163](https://github.com/alphastorm/omp-ninfer/pull/163): native and RTX 5090 window free-space floors before spending an attempt; native public-install checks retain their separate floor.
- [#164](https://github.com/alphastorm/omp-ninfer/pull/164): native windows fail on HTTP 503, checkpoint I/O errors, or incomplete/refusing managed Stop; a wrapper exit alone cannot erase server evidence.
- [#165](https://github.com/alphastorm/omp-ninfer/pull/165): only a collected passed native window with its candidate/lane-bound public-install receipt can retire that window's inventoried checkpoint generations. Preserve `retirement.json`; canonical and predecessor stores are not cleanup targets.
- [#161](https://github.com/alphastorm/omp-ninfer/issues/161) follow-ups are merged. [#170](https://github.com/alphastorm/omp-ninfer/pull/170) keeps native restoration running when evidence writes fail and copies server logs atomically. [#168](https://github.com/alphastorm/omp-ninfer/pull/168) revalidates the resolved checkpoint directory in the launcher. [#169](https://github.com/alphastorm/omp-ninfer/pull/169) reports RTX 5090 restoration only when it ran. [#174](https://github.com/alphastorm/omp-ninfer/pull/174) writes the native acceptance recovery records atomically. The v0.19.0 windows exercised live restoration under these changes and passed.
- [#171](https://github.com/alphastorm/omp-ninfer/pull/171): the same-profile identity rule above.

## Acceptance

Owner-operated, tester-equivalent acceptance of frozen candidate `6b22f219c7298db4b8fa5c2bc7bb33eb7a37799f` closed on 2026-11-13. It is not independent external-user acceptance.

| Documented route | Executable blocks | Result |
| --- | --- | --- |
| RTX 5090 container host | 2 | passed |
| macOS arm64 client over a manual SSH tunnel (preview) | 10 | passed |
| Native Windows x64 client | 5 | passed |
| RTX 4090 native, carried `v0.8.0-qwen38-4090-beta.3` | 7 | passed |
| RTX 3090 native, `v0.8.0-qwen38-3090-beta.4` (`C2`) | 7 | passed |

- Stock OMP 18.20.0 platform checks: macOS arm64 passed (preview), Windows x64 passed and WSL2 Linux x64 passed ([macOS](acceptance/darwin-arm64-18.20.0.json), [Windows](acceptance/windows-x64-18.20.0.json), [Linux](acceptance/linux-x64-18.20.0.json)).
- The RTX 5090 window held the production lane for 402.128 s; the native windows held their lanes for 517.0 s (RTX 4090) and 1339.4 s (RTX 3090). Independent restoration passed: the incumbent RTX 5090 service and both native lanes were restored and their canonical state compared identical.
- RTX 3090 `C2`, the [fork #89](https://github.com/alphastorm/ninfer/issues/89) acceptance class: on `native-v0.8.0-beta.4-tc-rtx3090` from source `15c3e395`, the post-route long-session probe committed 2 compactions in one session with every turn completed and no failed compaction, the fanout probe returned HTTP 200 for 5 of 5 requests, and the subagent and session proofs passed. The anonymous public install passed. This is exact-lane acceptance evidence for the bounded pressure-save build; it does not claim #89 closed for every load shape.
- Carried RTX 4090: `v0.8.0-qwen38-4090-beta.3` (source `48c8ac46`, package `sha256:ac41700ac2bb9fb171188f35e73481cfd9f1140c5781320b1e6304ee760d7166`) is the published v0.18.0 component, unchanged. It does not include the bounded pressure-save change (fork #122) and keeps its v0.18.0 component qualification; it re-cuts with the next engine freeze. Its fresh v0.19.0 documented route and campaign ran on those exact bytes, and its anonymous public install passed.
- Reviews: the runtime council on `41f89b31` and the focused review of the native delta to `15c3e395` closed as listed above. Product council CR-20261113T192727Z-6b22f219-product (closed-by-disposition) reviewed `6b22f219` and binds route candidate `6b22f219`. Deferred product residuals are tracked in https://github.com/alphastorm/omp-ninfer/issues/176. The combined content-safe ledger is [review/runtime-ledger.json](review/runtime-ledger.json).

The final receipt audit, the platform → acceptance → manifest pins and the strict ready check bind these receipts. No predecessor acceptance receipt, waiver, transcript or review approval is renewed. macOS remains preview, Linux evidence stays WSL2-scoped, vision remains RTX 5090 container-only, and native lanes remain sequential on their shared port. Promoting an existing production deployment to these components is a separate operator decision.
