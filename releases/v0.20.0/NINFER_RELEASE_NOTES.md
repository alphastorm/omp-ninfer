# OMP NInfer v0.20.0 — tool-call delimiter recovery, split-free warm prefill, xgrammar fixes and stock OMP 18.20.2

> The RTX 5090 runtime beta.9 and the RTX 3090 and RTX 4090 native beta.5 recover tool calls whose argument values contain literal parameter tags, stop splitting warm-turn prefill at chat-template markers, and take the upstream xgrammar cache and token-boundary fixes. The RTX 4090 gains bounded pressure-save retries. Saved sessions from earlier releases are refused, so the first resumed turn of each session prefills again. The client is stock Oh My Pi **18.20.2**.
>
> Support boundary: one RTX 5090 container on Windows 11 with Docker Desktop and WSL2 serves a native Windows x64 client or a WSL2 Linux x64 client over local loopback `127.0.0.1:18089`; on Windows 11 with WSL2 or on Linux it also serves a macOS arm64 client over a manual SSH tunnel (preview). The RTX 4090 and RTX 3090 native Windows 11 lanes run alone or beside each other on one two-GPU host, serving one lane at a time on the shared loopback port `127.0.0.1:18082`. Other GPUs, non-WSL Linux clients and concurrent native serving are unsupported. See the [manifest](manifest.json), [qualification summary](qualification.json), [quickstart](../../docs/QUICKSTART.md), [security model](../../docs/SECURITY.md) and [limitations](#limitations).

## Selected identities

Runtime components: RTX 5090 container `v0.7.0-qwen38-5090-beta.9` re-cut for this release; RTX 3090 native Windows `v0.8.0-qwen38-3090-beta.5` re-cut for this release; RTX 4090 native Windows `v0.8.0-qwen38-4090-beta.5` re-cut for this release. They were built from 1 distinct NInfer source commits.

- NInfer source `ca4c39179921e85defa9141db5fff7c2b05d7136` is fork `main` `8d0018ac` plus forks [#131](https://github.com/alphastorm/ninfer/pull/131), [#132](https://github.com/alphastorm/ninfer/pull/132), [#133](https://github.com/alphastorm/ninfer/pull/133), [#134](https://github.com/alphastorm/ninfer/pull/134), [#135](https://github.com/alphastorm/ninfer/pull/135) and [#137](https://github.com/alphastorm/ninfer/pull/137).
- RTX 5090 container runtime: `v0.7.0-qwen38-5090-beta.9`, source tag `v0.7.0-qwen38-5090-source.9`, image receipt `v0.7.0-qwen38-5090-runtime-beta.9`. Server binary `06c73e9800b1911e89f0cbf825324f767dcdc4abfd4a497f51fc031b5e3d69b8`, image `sha256:dc89893b90db89fe44b9605c4adca76ec5eb2a9dd314c68f284fa2fcbbe47ca6`. It succeeds `v0.7.0-qwen38-5090-beta.8`.
- Runtime base: `runtime-base-a87de361-20261103`, `ghcr.io/alphastorm/ninfer@sha256:28857182859a8f4993090521899b11a3f8676cb174c59adc626485e9f01472a3`. A runtime base grants no runtime qualification.
- RTX 5090 deployment profile `qwen38-5090-v0.13.0` and configuration `751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47` are unchanged from v0.19.0. The host checkpoint store is `checkpoints-v020`; the container mount remains `/checkpoints-v013`.
- RTX 3090 native: `v0.8.0-qwen38-3090-beta.5`, selected profile `native-v0.8.0-beta.5-tc-rtx3090`, package `873bbba30f9d63f3d43e4e93222b846ee7a451d23eefadcee2838612de8753b9`. RTX 4090 native: `v0.8.0-qwen38-4090-beta.5`, default profile `native-v0.8.0-beta.5-rtx4090`, package `89f14b7b7b3b340c9afb7c37f97722b23f3dbbc122b809789c1685ff12fb111c`. No RTX 4090 beta.4 component was published; that name is retired.
- Stock unmodified Oh My Pi **18.20.2**, source `7c49c11aa5bbaf3f418406583096168ad5b8c6dc`, tree `bc176229265a781c3b502673566328bcb473466c`, upstream release `445558988`.
- The published Qwen3.8 27B v3 model is unchanged: `81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da`, 20,437,521,664 bytes.

## What changed for users

### Tool calls whose argument values contain parameter tags

Before this release, a tool-call argument value that contained a literal closing parameter tag (&lt;/parameter&gt;) or an unmatched parameter opener (&lt;parameter=NAME&gt;) made the unconstrained Qwen tool-call parser return the whole call as plain text, so the tool call was lost. Requests reach that parser only when they opt into unconstrained tool calls (top-level `tool_constraints:"auto"` with non-strict `tool_choice:"auto"`, or tools that come only from history); stock Oh My Pi requests use the grammar-constrained route. The parser keeps its balanced first pass byte for byte. Only when that pass fails structurally does it read the region again: a value then ends at the leftmost closing tag that is followed by a declared parameter opening, or by the closing function and tool-call tags at the end of the region or before the next call. The scan is linear, with no backtracking ([fork #135](https://github.com/alphastorm/ninfer/pull/135)). On that opt-in route the recovery pass can still split a string value that itself holds a complete tool call; that residual is tracked in [fork #138](https://github.com/alphastorm/ninfer/issues/138).

A repeated parameter name still falls back with its `duplicate_parameter` diagnostic, and an undeclared name refuses recovery, so a parameter the model emitted is never merged into the value before it. Recovered calls are published only when every call in the region normalizes; otherwise the earlier fallback content and diagnostics stand. Free-output continuation refuses a prefix that holds a call either pass completes. The grammar-constrained path is unchanged.

This change alters no generated tokens or streamed bytes, because the parser runs after generation. A differential fuzz of 300,000 generated regions against the previous parser found 44,815 identical parses, 227,710 identical fallbacks, 27,475 regions that previously fell back and now publish their recovered calls, and no continuation that the previous parser refused and this one accepts. The durable parser codec becomes `qwen-parser/2`.

### Warm turns without rewrite-only prefill splits

Chat-template markers (the assistant header, the thinking opener and the reasoning close) no longer force prefill or Replay chunk boundaries, and generated output no longer records a prefix execution split. Capture frontiers, chunk and pacing limits, prompt and media boundaries and MTP alignment still bound execution. Prefix reuse now matches on tokens, token types, MRoPE positions and Vision items only, in line with upstream `77418cfec` ([fork #134](https://github.com/alphastorm/ninfer/pull/134)). The durable identity codec becomes `qwen-identity/2`.

Prompt tokens do not change: the real Qwen frontend produced byte-identical token IDs, token types, MRoPE positions, rewrite checkpoints and reusability for 2,880 prompt preparations (960 multi-turn agent prompts under three bundled chat templates, 2,120,774 prompt tokens), and the 31,422 rewrite execution frontiers those preparations held before are gone. Generated tokens can differ from v0.19.0 by design, because chunk decomposition moves; the quality evidence below covers that.

### xgrammar cache and token-boundary fixes

The vendored xgrammar takes upstream NInfer commit `8e464812`: erased cache-list values release their allocation, a token that crosses into an excluded range mid-token is masked correctly, and grammar serialization metadata advances ([fork #137](https://github.com/alphastorm/ninfer/pull/137)). A golden test pins the token masks of the product's tool and JSON Schema grammars ([fork #133](https://github.com/alphastorm/ninfer/pull/133)). After the fix, all four product cases kept identical masks at all 244 greedy steps, with and without a three-token speculative continuation, across two compilations with forced cache eviction. This mask proof makes no model-output or performance claim.

### Saved sessions prefill once after the upgrade

Durable checkpoints now carry identity codec `qwen-identity/2` and parser codec `qwen-parser/2`. Checkpoints written by earlier releases are refused as `Incompatible/FingerprintMismatch` before any native import and without quarantine, so the first resumed turn of each saved session prefills again from the client's full history. An earlier binary refuses the new checkpoints the same way, so rolling back is safe, and it can still load its own generations until they are replaced or collected.

### RTX 4090 bounded pressure-save retries

The RTX 4090 package now has the bounded pressure-save behavior that the RTX 5090 and RTX 3090 components gained in v0.19.0 ([fork #122](https://github.com/alphastorm/ninfer/pull/122)). A pressure save refused for a retryable reason (filesystem capacity, an I/O outage or a stale tag) settles after six retries or 10 seconds with one `pressure` / `abandoned` receipt and releases its continuation, instead of keeping admission latched behind the outstanding save. A refusal from the store's own quota (`--session-checkpoint-quota-mib`, reason `quota`) settles at once, with only the ordinary `save` / `refused` / `quota` receipt; monitoring that counts abandonment receipts must count store-quota refusals separately. A refused save never becomes durable state, and authoritative OMP transcripts remain the recovery boundary.

### Stock OMP 18.20.2

The [client review](../../docs/measurements/2026-11-16-omp-18202-client-upgrade-review.json) covers 18.20.0 to 18.20.2, including 18.20.1, with a census of 552 upstream commits and probes of the published macOS arm64 executable against a local stub. It is not client execution on the documented routes. The six model and configuration files stay unchanged: explicit `qwen3` tokenizers on opaque aliases, effort clamps, stateful Responses settings, retry, fallback, update and setup opt-outs, and the C2/C1/C2 provider caps, each of which still queues excess requests in the client.

- The rendered system prompt is 119 bytes shorter (no RFC-2119 preamble or Role heading), and the wait and task-spawn texts changed, so the first turn after the upgrade prefills a cold prefix.
- The engine's complete HTTP 400 `context_length_exceeded` body is classified as context overflow through its structured code. Overflow and HTTP 413 recover by compaction and continuation on the same local provider and model, or fail visibly when nothing can be compacted. A provider outage must still fail visibly with no extra request. No provider or model switch and no cloud fallback is allowed.
- Upstream changed Windows `.exe` dispatch from `find -exec`, `xargs` and `env`, drive-root and pipe handling, shell state kept across timeouts, session storage and turn recovery. The Windows routes need fresh shell and session evidence in this release; no macOS probe stands in for them.
- Optional 18.20.x features (the antigravity-cli provider, auth, spotlight, commit and to-do helpers, shell policy) are not configured.

## Upgrade from v0.19.0

1. Clone tag `v0.20.0` and run `python3 scripts/verify_release.py --require-ready` (`py -3 scripts\verify_release.py --require-ready` on Windows). Install only from a clone that passes.
2. Install stock OMP 18.20.2 from the release's `qualification/client-components.json` and check its SHA-256 before replacing the binary. Keep your model fragments and `fail-closed.yml`, clear `PI_OPENAI_STATEFUL`, and do not run `omp update`.
3. RTX 5090: stop the v0.19.0 container with its own published stop script, then start this release's launcher with the new host store `checkpoints-v020`. Keep `checkpoints-v019`, `checkpoints-v018`, `checkpoints-v017`, `checkpoints-v013` and the legacy `checkpoints` store untouched, and import no generation.
4. Native lanes: stop the other native lane, then run the beta.5 installer from the lane's verified download steps. It stops a running incumbent with that incumbent's own controller and power policy and keeps it as the exact rollback target (RTX 3090 beta.4, RTX 4090 beta.3). Keep prior release roots, staging and checkpoint directories. If a stopped beta.2 incumbent refuses shutdown, follow the native upgrade recovery in the quickstart first.
5. Expect the first resumed turn of every saved session to prefill again; OMP transcripts replay the history. To roll back, use the previous release's own guide, binaries and stores.

## Qualification

### RTX 5090 beta.9 runtime

- The exact-source release-candidate batch at `ca4c3917` passed all 12 phases (`qualification/runtime-rc.json`). The packaged build identity binds that source and server binary (`qualification/runtime-build-identity.json`).
- On the published image, pulled anonymously by digest with the exact serving profile and a fresh checkpoint store, the lane gate passed (`qualification/rtx5090.json`). A cold 130,048-token prefill returned the exact expected output, decode measured 192.9 tok/s, and the agent-protocol and restart gates passed.
- Quality: identity-first did not hold, because only 1 of the 80 determinism outputs and 23 of the 84 counted-role outputs were byte-identical to the sealed beta.8 incumbent. The full 1,120-prompt EXP-085 screen and a fresh 80-prompt determinism rerun therefore ran: the screen passed with every primary metric inside its margin (secret-leak ratio 1.0386, upper 95% bound 1.0888 against 1.1), and the rerun found no determinism mismatch in either arm.
- Anonymous downloads of the binary archive, SPDX SBOM, checksum set, source archive, image receipt and runtime-base receipt matched the published digests (`qualification/runtime-artifacts.json`).

### Native beta.5 lanes

- RTX 3090 `native-v0.8.0-beta.5-tc-rtx3090` (`C2`): all 15 managed native phases passed on the exact shipping package; quality against the published beta.4 incumbent: none of the 80 determinism outputs was byte-identical, so the 1,120-prompt EXP-085 screen ran and passed with every primary metric inside its margin (secret-leak ratio 1.0365, upper 95% bound 1.0849 against 1.1) and no mismatch in the fresh 80-prompt determinism rerun; decode 155.8 tok/s weighted over the 84-case speed suite, 1.006 times the incumbent, with the 32 byte-identical cases at a minimum of 0.960; native probes green with no HTTP 503, card fit passed and card parity passed unwaived at 83 of 83 positions.
- RTX 4090 `native-v0.8.0-beta.5-rtx4090` (`C1`): all 15 managed native phases passed on the exact shipping package; identity-first found none of the 80 determinism outputs byte-identical to the published beta.3, so the 1,120-prompt EXP-085 screen ran and passed with every primary metric inside its margin (secret-leak ratio 0.9857, upper 95% bound 1.0265 against 1.1) and no mismatch in the fresh 80-prompt determinism rerun; decode 174.6 tok/s weighted over the 84-case speed suite, 0.999 times the incumbent, with the 38 byte-identical cases at a minimum of 0.970; card fit passed and card parity passed unwaived at 83 of 83 positions.

## Reviews

- The engine source review of `ca4c3917` (`CR-20261116T051524Z-ca4c3917`) closed with no confirmed P0 or P1 finding; the highest confirmed severity is P2. Its residuals, two P2 findings and one P3 finding about the recovery pass on the opt-in unconstrained tool route, are deferred to [fork #138](https://github.com/alphastorm/ninfer/issues/138).

## Limitations

- Stock upstream OMP 18.20.2 uses explicit qwen3 tokenizers for opaque aliases, supported effort clamps and disabled automatic update/setup. Explicit omp update remains an operator action.
- Retained RTX 5090 qwen38-5090-v0.13.0 configuration 751d22dc, 131072 context, BF16 auto KV, DFlash2 K7, C2 and 180-second pending timeout; optional pacing stays off. No fairness or general performance guarantee.
- Successor host checkpoints-v020 is isolated from predecessor checkpoints-v019, checkpoints-v018, checkpoints-v017 and checkpoints-v013; retained container mount/profile names do not establish cross-binary checkpoint compatibility. Preserve old stores and replay authoritative OMP transcripts.
- Durable sessions use identity codec qwen-identity/2 and parser codec qwen-parser/2; checkpoints written by earlier releases are refused, so a resumed session's first turn prefills again.
- Retryable pressure-save refusals (filesystem capacity, I/O outage, stale tag) settle after six retries or 10 seconds with one pressure/abandoned receipt; a refusal from the store's own quota (reason quota) settles at once with no pressure/abandoned receipt. Deferred coordinator residuals are tracked in https://github.com/alphastorm/ninfer/issues/123.
- No predecessor waiver, live-client acceptance, product review approval or public installation result grants this candidate a pass. Fresh five-route acceptance, restoration, composition and exact-subject reviews remain separate gates.
- macOS remains manual-SSH preview; Linux client evidence is WSL2-scoped. Image input is RTX 5090 macOS/Windows only. Publication and production promotion remain founder-owned.
