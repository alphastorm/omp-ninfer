# OMP 18.16.0 tokenizer verification

Date: 2026-11-05. Scope: host-free stock-client source/counting experiment, not NInfer or live route qualification.

## Verdict and delivery boundary

**The alias asymmetry and explicit override are real; a large universal 18.16.0 compaction regression is not established.** On the same synthetic code/tool transcript, stock 18.15.0 counts an unclassified `q38-ninfer` at **565,505** tokens in its default mode; stock 18.16.0 counts it at **579,220** (`o200k`, **+2.43%**). The correct locally embedded `qwen3` counter returns **656,832** (**+16.15%** versus bytes/4; **+13.40%** versus o200k). Explicit `tokenizer: qwen3` gives that identical result in both releases. Unmodified `qwen3.8-27b` already receives qwen3 in both releases.

These measurements do **not** reproduce the research report's quoted 11–48% fallback-version increase on this corpus. The measured default-version increase is modest, while choosing the actual Qwen tokenizer materially changes the **local estimate**. This supports proposing the key deliberately, not claiming that every live session compacts earlier or that a new client is qualified.

**Held proposal only.** No root profile, compatibility authority, QUICKSTART, live model fragment, release descriptor, acceptance receipt or published release record is repinned by this evidence change. Live five-route / **31-block** acceptance waits for a release decision. The proposed fragment patch below is documentation, not an applied model configuration.

## Method and reproducibility

- Read the immutable local Git tags without changing the upstream checkout: v18.15.0 = `3fedf8d53267e32a6d7521ce725fdcc4a36fdc67`; v18.16.0 = `650f3a108229ee11bf68ba3377f4e8c3391cd424` (tree `3cccceb37ddce426b454d0abd6ede4e32e02e97f`).
- The upstream checkout had no installed dependencies. A disposable Bun 1.4.4 harness instead imported the released `@oh-my-pi/pi-agent-core`, `pi-catalog` and `pi-natives` packages at **both exact versions**. Native addons reported build versions `18.15.0` and `18.16.0`. No tokenizer was reimplemented or substituted.
- SHA-256 equality assertions matched each installed package's `tokenizer.ts`, `compaction/compaction.ts`, `build.ts`, `model-tokenizer.ts` and `compat/taxonomy.ts` to its Git tag's source bytes. The Qwen/o200k native tokenizer sources have no diff between the two tags.
- Both `NODE_ENV` and `PI_TOKENIZER_ACCURATE` were absent. This matters: test mode deliberately avoids native counting in non-strict modes; enabling the old accuracy environment variable would hide the stock 18.15.0 default fallback.
- The deterministic, secret-free corpus has **180 synthetic code-review turns, 720 messages, 1,080 counted fragments and 2,260,632 content bytes**. Each turn contains a user request, assistant text plus typed `read` call, numbered TypeScript code with synthetic test output, and an assistant explanation. Transcript JSON SHA-256: `0342b07eefed719697d9f23fc87ad236d6e6f12832a1221f09ea1d098cb28724`.
- Calls used the stock `buildModel`, `classifyModel`, `resolveModelTokenizer`, `Tokenizer.countMessages(..., {excludeEncryptedReasoning: true})`, all three `countTokens` modes, and stock compaction helpers. The explicit-key model passed `tokenizer: qwen3` to `buildModel`; YAML schema and custom-model loader propagation were independently inspected at both tags.
- This is a **message-content corpus**, not a server token-count measurement: no images, encrypted reasoning, message-frame overhead, system prompt or tool-schema prefix is included. The full corpus is larger than one configured context; prefix threshold checks are hypothetical decisions on un-compacted prefixes, not a claim that the engine accepted the entire corpus.

Private lane artifacts: `harness/verify.ts`, `harness/bun.lock`, `transcript.synthetic.json`, `counts.json`, tagged source extracts and execution logs. The command was `env -u NODE_ENV -u PI_TOKENIZER_ACCURATE bun verify.ts`. Throwaway code/dependencies and the synthetic transcript are not committed.

## Classification, models.yml precedence and count modes

The models.yml schema permits per-model `tokenizer: qwen3` in **both** versions. `custom-models.ts` copies `modelDef.tokenizer` into the overlay and forwards `resolvedModel.tokenizer` into `buildModel`; `build.ts:531` selects `spec.tokenizer ?? resolveModelTokenizer(...)`. Thus the explicit key outranks classification; it does **not** rename the served model or change its taxonomy identity.

| Stock release | Served ID | Explicit key | Catalog class / resolved tokenizer | Approximate (default) | Strict | Upperbound |
| --- | --- | --- | --- | ---: | ---: | ---: |
| 18.15.0 | `q38-ninfer` | absent | unknown / unset | 565,505 | 579,220 | 2,260,632 |
| 18.15.0 | `q38-ninfer` | `qwen3` | unknown / qwen3 | 656,832 | 656,832 | 656,832 |
| 18.15.0 | `qwen3.8-27b` | absent | qwen 3.8 / qwen3 | 656,832 | 656,832 | 656,832 |
| 18.15.0 | `qwen3.8-27b` | `qwen3` | qwen 3.8 / qwen3 | 656,832 | 656,832 | 656,832 |
| 18.16.0 | `q38-ninfer` | absent | unknown / unset (native default o200k) | 579,220 | 579,220 | 579,220 |
| 18.16.0 | `q38-ninfer` | `qwen3` | unknown / qwen3 | 656,832 | 656,832 | 656,832 |
| 18.16.0 | `qwen3.8-27b` | absent | qwen 3.8 / qwen3 | 656,832 | 656,832 | 656,832 |
| 18.16.0 | `qwen3.8-27b` | `qwen3` | qwen 3.8 / qwen3 | 656,832 | 656,832 | 656,832 |

The byte heuristic sums `ceil(UTF8_bytes(fragment)/4)` per fragment, not one rounded count over concatenated transcript JSON. In 18.15.0, strict already uses native o200k for an unknown model; default approximate uses bytes/4 and upperbound uses bytes. Known families use their native encoding. In 18.16.0 all modes normally use the resolved native encoding, falling back to o200k when unset. Only an unsupported encoding in a loaded addon falls back to bytes/4 (approximate) or raw bytes (strict/upperbound); that fallback was not exercised here.

**Canonical-ID decision:** leave `qwen3.8-27b` inferred in the proposed patch. Both releases classify it as Qwen 3.8 and select qwen3; an explicit key changed **zero** counts in every mode. The opaque alias is the proven mismatch, so only its four declared model entries need the key. No stateful Responses, reasoning, concurrency, limits, edit-mode or fallback policy changes are proposed.

## Which count actually triggers compaction

For **both versions**, with `contextWindow: 131072`, `maxTokens: 32768`, and untouched compaction settings:

| Quantity | Result, with or without the tokenizer key |
| --- | ---: |
| Configured absolute default reserve (when unset) | 16,384 |
| Effective/budget reserve `max(floor(0.15 × window), default)` | **19,660** |
| Default trigger threshold `window − budget_reserve` | **111,412** |
| `shouldCompact(111412, ...)` | false |
| `shouldCompact(111413, ...)` | true |
| Ordinary full-summary output cap with configured reserve unset | **13,107** |

The strict-greater-than comparator above is **not** `TokenCountMode = "strict"`. Stored-conversation counting calls `countMessages`, whose text path uses **approximate/default** mode. It includes non-message overhead plus the full live transcript and pending messages, excluding opaque encrypted-reasoning payloads. The trigger uses:

```text
max(max(0, provider_context_tokens), max(0, local_stored_conversation_estimate))
    > 111412
```

Provider usage is therefore a **lower bound on the trigger's effective count**, not a value that the new tokenizer overrides. Trustworthy settled usage normally covers system prompt, tool schemas and the already-sent prefix; unaccounted tail content is counted locally. Aborted/error usage is not a trustworthy transcript anchor, and stale pre-rewrite usage is excluded. Separately, the local stored-conversation floor is recomputed independently of the anchor, so payload-shrinking extensions cannot suppress compaction.

**Precise operational impact:** when correct NInfer/Qwen usage already covers a settled prefix and dominates its local estimate, replacing bytes/4 or o200k with qwen3 does **not** add another charge or guarantee an earlier compaction. It corrects estimates where trustworthy provider accounting is absent or does not yet cover the content: imported/resumed history without usable usage; the first request after compaction while old usage is stale; newly queued input; and large tool outputs appended before the next provider response. It can also affect the full-history floor behind a request-compressing extension. Ordinary resume **with** a valid usage anchor is not itself proof of a counting gap. Accurate local counting does not prove a prior live context overflow occurred.

### Prefix decisions without provider usage or non-message overhead

| Counting choice | First synthetic turn above 111,412 | 35-turn local count | Would compact at turn 35? |
| --- | ---: | ---: | --- |
| 18.15.0 `q38-ninfer`, no key (bytes/4) | **36** | 109,495 | no |
| 18.16.0 `q38-ninfer`, no key (o200k) | **35** | 111,755 | yes |
| Either release with explicit qwen3; canonical ID with or without key | **32** | 125,780 | yes |

These turn numbers characterize this fixed corpus only. With provider context 110,000 at turn 35, the same three effective counts are 110,000 / 111,755 / 125,780. If provider context is already at least 125,780, all three decisions agree; any accurate current provider count above 111,412 triggers regardless of local choice.

### Correction to the prior research summary

The reserve/trigger values **19,660 / 111,412** are confirmed. The reported **15,728** ordinary summary cap is not the stock unset-reserve execution path. `compact()` passes `settings.reserveTokens ?? DEFAULT_RESERVE_TOKENS` = 16,384 to the ordinary summarizer, which caps output at `min(floor(0.8 × 16384), 16384)` = **13,107**. The coding-agent method/model wrappers preserve the unset reserve rather than replacing it with the effective reserve. **15,728** would follow if an operator explicitly passed 19,660 as `reserveTokens`; the documented fragments do not do that. This is unchanged between the two tags.

## Stock 18.16.0 release assets (proposal inputs only)

Source: the [GitHub v18.16.0 release API](https://api.github.com/repos/can1357/oh-my-pi/releases/tags/v18.16.0), release **431898253**, published **2026-11-02T19:49:20Z**. These are GitHub's sizes/digests, not new platform qualification.

| Platform / asset ID | Bytes | SHA-256 | Exact asset URL |
| --- | ---: | --- | --- |
| windows-x64 / 702972270 | 243,591,168 | `c249a9ed0a57c748fb1247d8ee9e2d0fe1b13229266ce74d8810a76a591e21fc` | [omp-windows-x64.exe](https://github.com/can1357/oh-my-pi/releases/download/v18.16.0/omp-windows-x64.exe) |
| darwin-arm64 / 702972282 | 215,642,256 | `d4a10d97488d6054d2b18198bd24f461079952c7e0fb75ba66336ca0df0cb99e` | [omp-darwin-arm64](https://github.com/can1357/oh-my-pi/releases/download/v18.16.0/omp-darwin-arm64) |
| linux-x64 / 702972275 | 277,002,416 | `6498ed785bab00d2926e0387e0ec02362d6d45f1c3d0d1b57c1618b7f95c9264` | [omp-linux-x64](https://github.com/can1357/oh-my-pi/releases/download/v18.16.0/omp-linux-x64) |

## Staging precedent and why root remains unchanged

The preceding 18.14.x → 18.15.0 client bump separates staging from promotion:

1. [`b5bd3f8`](https://github.com/alphastorm/omp-ninfer/commit/b5bd3f8c9f1011e2e5ee0be23c1e853e29e75553), `chore(release): stage v0.16.1 with stock omp 18.15.0`, added the release-local `qualification/client-components.json`, manifest, compatibility and profile snapshots. It changed **39 files / 11,148 insertions** and carried extensive runtime/review evidence. At this stage the release-local manual-tunnel snapshot still identified the predecessor v0.16.0 / OMP 18.14.0, while the client descriptor selected 18.15.0.
2. [`cf7a76b`](https://github.com/alphastorm/omp-ninfer/commit/cf7a76b6f5ad9217b8acbde4c276e007de8946a1), `chore(release): pin v0.16.1 client candidate`, performed the separate root compatibility/profile promotion and updated release-local snapshots/pins (**11 files**).

This is release-preparation machinery, not an existing isolated candidate-descriptor feature. Recreating it would require a chosen successor product release and release records beyond this slice's no-release-artifact boundary. The current ready v0.16.2 profile snapshots must byte-equal root profiles (`validate_release_identity_snapshots`), and client-pin tests bind those profiles to the immutable release descriptor. Repinning only root would rightly fail those gates; this proposal does not weaken or bypass them.

Per the conservative delivery decision, the PR therefore contains this evidence and the unapplied fragment proposal only. It does not claim a staged/installable 18.16.0 product. Published v0.16.2 continues to pin stock OMP 18.15.0.

## Proposed fragment patch (not applied)

Apply only with the separately authorized candidate stage and fresh acceptance. The field is valid in 18.15.0 too; it does not depend on upgrading first.

```diff
--- a/examples/fleet/models.fragment.yml
+++ b/examples/fleet/models.fragment.yml
@@
       - id: q38-ninfer
         name: Qwen3.8 27B NInfer RTX 5090 (fleet main, durable, fanout)
+        tokenizer: qwen3
         api: openai-responses
--- a/examples/manual-tunnel/models.fragment.yml
+++ b/examples/manual-tunnel/models.fragment.yml
@@
       - id: q38-ninfer
         name: Qwen3.8 27B NInfer RTX 5090 beta
+        tokenizer: qwen3
         api: openai-responses
--- a/examples/windows-docker-local/models.fragment.yml
+++ b/examples/windows-docker-local/models.fragment.yml
@@
       - id: q38-ninfer
         name: Qwen3.8 27B NInfer RTX 5090 beta
+        tokenizer: qwen3
         api: openai-responses
--- a/examples/windows-native/models-rtx3090.fragment.yml
+++ b/examples/windows-native/models-rtx3090.fragment.yml
@@
       - id: q38-ninfer
         name: Qwen3.8 27B NInfer RTX 3090 native
+        tokenizer: qwen3
         api: openai-responses
```

## Host-free product contract checks

Both Darwin raw binaries were downloaded into disposable storage and independently measured:

| Version | Observed bytes | Observed SHA-256 |
| --- | ---: | --- |
| 18.15.0 | 215,295,120 | `d36dfabf0ee52d6f08efadb59c46f0349545c6f6975522417adae29646e73e34` |
| 18.16.0 | 215,642,256 | `d4a10d97488d6054d2b18198bd24f461079952c7e0fb75ba66336ca0df0cb99e` |

Both match their release pins. Initial downloads reached the 300-second deadline while incomplete; bounded HTTP range continuations completed them before hashing or execution. No partial binary was executed. Windows/Linux metadata above was read from GitHub; those binaries were not downloaded or run.

The unchanged root pin authority passed `python3 scripts/verify_release.py`: **valid v0.16.2 manifest (ready)**.

The client acceptance, stock-client harness, fleet-example and release identity-snapshot suites passed **66 tests**. The same invocation included an incorrectly addressed `VerifyReleaseTests` class and therefore exited nonzero on that **discovery error**, not a product assertion. Only that missing test was retried with its actual address, `tests.test_verify_release.ReleaseContractTest.test_client_candidate_matches_the_verified_upstream_descriptor`, and it passed (**1 test**). Total exercised: **67 real passing tests**; no successful test was rerun to hide the invocation error. Interpreter: Python 3.13.

```sh
python3 -m unittest tests.test_client_acceptance tests.test_stock_client_harness \
  tests.test_fleet_example tests.test_verify_release.ReleaseIdentitySnapshotTests \
  tests.test_verify_release.VerifyReleaseTests.test_client_candidate_matches_the_verified_upstream_descriptor -v
# Discovery correction only:
python3 -m unittest \
  tests.test_verify_release.ReleaseContractTest.test_client_candidate_matches_the_verified_upstream_descriptor -v
python3 scripts/verify_release.py
```

These tests preserve the published pins and rehearsal/qualification boundary. They do not test an applied product repin; no repin is present.

### Real stock-binary local rehearsals

All three host-free Darwin rehearsals passed **all seven** runner checks: typed tool turn, seed, continuation, synthetic server-restart survival, client resume, same session, and fail-closed outage. Each receipt has `receipt_class: rehearsal`, `qualification_claimed: false`, `status: passed`. They bind the unchanged QUICKSTART hash `d94b36399c5ce3d8ec858ea8c3e9e23a897cc12a921f52e3f2f9b3e88a9d3c` only for semantic-check attribution, not verbatim 31-block execution.

| Stock client / generated models.yml | Execution | Result / private receipt |
| --- | --- | --- |
| 18.16.0 / no tokenizer key | Unmodified `scripts/client_acceptance.py --local-rehearsal` | 7/7; `rehearsal-18.16.0-default.json` |
| 18.15.0 / `tokenizer: qwen3` | Same runner imported by a throwaway wrapper; only the disposable generated models.yml gains the key | 7/7; `rehearsal-18.15.0-qwen3.json` |
| 18.16.0 / `tokenizer: qwen3` | Same disposable-config wrapper | 7/7; `rehearsal-18.16.0-qwen3.json` |

The explicit-key wrapper additionally observed the active model through the **real stock RPC `get_state` response** on both initial and resumed client launches. All four observations were `id: q38-ninfer`, `tokenizer: qwen3`. This proves actual models.yml loading in both binaries, beyond the source/schema/buildModel checks. No client or product runner file was modified. Launch environments were allowlisted, with disposable HOME, isolated native-addon cache and owned ephemeral loopback stub; no operator credentials, private sessions, GPU, NInfer service or production route was used.

The unmodified-runner command, using the exact candidate binary and its pin, was:

```sh
python3 scripts/client_acceptance.py --omp ./omp-18.16.0-darwin-arm64 \
  --omp-sha256 d4a10d97488d6054d2b18198bd24f461079952c7e0fb75ba66336ca0df0cb99e \
  --omp-version omp/18.16.0 --local-rehearsal --receipt rehearsal-18.16.0-default.json
```

These synthetic Responses-server rehearsals do not exercise near-limit live compaction, NInfer checkpoint durability, Windows/Linux client execution, or the documented install blocks. Those are not imported from predecessor acceptance.

## Primary source anchors

All anchors below refer to immutable upstream tag commits. The same precedence, propagation and compaction accounting were inspected at both tags.

- [18.15.0 model tokenizer resolution](https://github.com/can1357/oh-my-pi/blob/3fedf8d53267e32a6d7521ce725fdcc4a36fdc67/packages/catalog/src/model-tokenizer.ts#L36-L83) and [18.16.0 resolution](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/catalog/src/model-tokenizer.ts#L27-L84).
- [18.16.0 bounded taxonomy matching](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/catalog/src/compat/taxonomy.ts#L56-L76), plus [Qwen taxonomy](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/catalog/src/compat/rules/taxonomy/qwen.kdl).
- [Explicit build precedence](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/catalog/src/build.ts#L518-L533), [custom-model propagation](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/coding-agent/src/config/custom-models.ts#L81-L145), and [per-model schema](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/coding-agent/src/config/models-config-schema-bundle.ts#L181-L225).
- [18.15.0 count modes](https://github.com/can1357/oh-my-pi/blob/3fedf8d53267e32a6d7521ce725fdcc4a36fdc67/packages/agent/src/tokenizer.ts#L271-L278) and [18.16.0 count modes](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/agent/src/tokenizer.ts#L283-L285).
- [Reserve, threshold and provider/local maximum](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/agent/src/compaction/compaction.ts#L324-L424); [full-history/pending floor](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/coding-agent/src/session/session-maintenance.ts#L2676-L2716); [post-turn decision](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/coding-agent/src/session/session-maintenance.ts#L3498-L3524).
- [Provider-anchored prefix/tail accounting](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/agent/src/compaction/transcript-tokens.ts#L1-L172).
- [Ordinary summary budget](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/agent/src/compaction/compaction.ts#L911-L919), [unset reserve passed to summaries](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/agent/src/compaction/compaction.ts#L1748-L1750), and [method settings preserve reserve](https://github.com/can1357/oh-my-pi/blob/650f3a108229ee11bf68ba3377f4e8c3391cd424/packages/coding-agent/src/session/compaction-methods.ts#L94-L105).
