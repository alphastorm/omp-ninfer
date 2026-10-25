# OMP NInfer v0.13.0

**Staged beta.2 draft; not a published product or accepted public-install composition.** The
runtime is cut and lane-qualified at `6d4d0a05`. The actual council ledger closes the initial
review plus verified localized remediation; fresh RTX 5090 client/public-route acceptance and
final pins remain separate. The published product remains
[v0.12.2](../v0.12.2/NINFER_RELEASE_NOTES.md). No upgrade or publication is authorized here.

Oh My Pi (coding-agent client) connects through OMP NInfer (qualified appliance and release
layer) to NInfer (inference engine) serving Qwen3.8 27B on one user-owned GPU.

## What changes

- **Rebased RTX 5090 runtime:** component `v0.7.0-qwen38-5090-beta.2`, source
  `6d4d0a05aded2a1b353b8998e7b08b0f2fb34bff`, branch `rebase/rc2-5090`, on upstream master
  `64d10fbf9f8e6bfc79ab0570b94674c5b9997929`. Upstream owns scheduling, grammar, context caches
  and DFlash2; the product carries authenticated durable sessions, retained Responses and kernel routes.
- **Schema 3 durable store:** checkpoint schema 3, fingerprint schema 2, status schema 2 and
  request-log schema 30 are separate contracts. Compatible native checkpoints accelerate restart;
  saved OMP transcripts remain authoritative.
- **JSON-schema output is supported on RTX 5090:** exact-source real grammar and product smokes
  cover Responses `text.format` and Chat Completions `response_format` with `json_schema`.
  Chat/Responses tool names support 128 characters. Carried natives retain HTTP 400 schema refusal
  and 64-character names; container capabilities do not transfer to them.
- **Non-blocking export:** capture is serialized, but bulk transfer/hash/write runs outside the
  execution lock with epoch-checked publication. This addresses the export lock hold, not all queueing
  or native import/victim-validation I/O on the worker.
- **Published model container version 3:** direct upstream artifact `81f924d4`, not a local
  conversion. All 1,184 tensor payloads and six frontend resources matched the production model
  upgraded locally; whole-container bytes differ. Text, vision, MTP and DFlash2 are present.
- **Stock OMP 18.12.6:** unmodified upstream assets on three client platforms. The
  [host-free review](../../docs/measurements/2026-10-25-omp-18126-client-upgrade-review.json)
  covers checksums, Responses wire invariants, image-aware snapcompact and print-mode slash dispatch.
  Stub/client-source checks are not fresh beta.2 live inference or memory proof.

## Fixed in beta.2 — durable/restore council remediation

Council `CR-20261025T085950Z-04b603aa` reviewed the initial source, then closed by verified
localized remediation at the exact source above. The unchanged
[review ledger](review/runtime-ledger.json) preserves the original findings, dispositions and
residual risks; the [remediation receipt](qualification/remediation.json) binds all 13 named
regressions within **66/66 host executables**, not 13 additional CTest executables.

- **Restore/pressure lock order:** the worker callback only consults bounded bookkeeping and
  enqueues Pending; the checkpoint thread performs Responses/catalog/save work. K4 atomic commit
  remains intact. Regression: `pressure_callback_does_not_wait_for_restore_commit`.
- **Automatic-save retry/progress:** every completion notifies progress, including retryable
  refusal. Six bounded retries require matching Engine/publication/storage progress; unrelated or
  unchanged progress cannot spin. Regressions: `automatic_retry_requires_matching_progress`,
  `automatic_retry_budget_and_terminal_refusal`, `publication_abandonment_completes_pressure`.
- **Gate-tag timing and native owners:** submission advances capture epoch without replacing the
  committed tag. Only completed native state acknowledged after Responses publication promotes
  the endpoint; abandoned/queued turns preserve the prior owner. Unfinished paused work may settle
  by native replay. Regressions: `queued_expiry_preserves_committed_tag`,
  `test_abandoned_turn_preserves_committed_owner`, `paused_request_settles_by_native_replay`.
- **Per-record delete durability:** publish undeleted RAM/disk-only survivors before acknowledgement.
  An unavailable/deleted native endpoint uses authenticated responses-only replay survivors, never
  fabricated native state, native eviction authority or a new leaf-delete 409. Regressions:
  `durable_record_delete_preserves_survivors`, `durable_delete_retains_disk_only_records`,
  `test_replay_only_survivors_are_durable_without_native_authority`.
- **Restore freshness:** reject incompatible live lineage or a live record absent from the loaded
  generation before native commit, even when the newer unsaved turn predates guard capture.
  Regression: `test_restore_guard_captured_after_newer_turn`.
- **Quota preservation:** planning is non-destructive; only an acknowledged new current permits
  victim deletion, with one quota-bounded incoming transient. Stale/refused publication preserves
  unrelated currents. Regression: `test_quota_stale_publication_preserves_unrelated_currents`.
- **Victim payload validation:** ordinary destructive pressure validates native metadata and all
  delivered bytes, pins/rechecks the current index and retains proof pins through the worker turn.
  Regression: `test_ordinary_pressure_preserves_same_size_corrupt_victim`.

**Strict origin authentication** is mandatory in both product profiles:
`--session-checkpoint-require-origin-auth` (finding 8; K1 section 103–114). Exact-profile startup
reports `require_origin_auth=true`; the binary accepts all **25** profile flags. The flag needs a
checkpoint root and API key of at least 32 bytes; the documented generated key is 64 characters.
The new schema 3 root has no supported MAC-less producer. Unauthenticated imports refuse without
mutation. Generic non-strict CLI compatibility is outside this product profile.

Within one API-key principal, prompt_cache_key names a session capability; use unique high-entropy keys and do not share that principal among mutually untrusted clients.

## Exact component bindings

| Subject | Identity |
| --- | --- |
| Binary archive | `ninfer-qwen38-rtx5090-v0.7.0-linux-x86_64-cuda13.1.tar.gz`, 547,088,535 bytes |
| Archive SHA-256 | `52dd3be726a1ea05f81e142a11e75ac984359ecafdf42aeeb8c192356214b43d` |
| `ninfer-serve` SHA-256 | `9790a00467c4351929ab9a3e68347ab0436357a956f845efc5b4475f75718c55` |
| Source archive | `runtime-source-6d4d0a05.tar.gz`, 12,229,537 bytes; source tag `v0.7.0-qwen38-5090-source.2` |
| Source archive SHA-256 | `d6bde7844abc6db5c9c9cd857b25a104049339fd5801bd40b1b245bd11e85631` |
| SPDX SHA-256 | `0d360628359f4b554cec0393c5c088265e3454d271fc633bbf2af044c9d69670` |
| SHA256SUMS SHA-256 | `e88aa68a5d0e11a4f561247534440641d0a6a6f8bbc2312d9895c15a4fb546f8` |
| Runtime image | `ghcr.io/alphastorm/ninfer-runtime@sha256:5d10a998a42ba927dd8bbe54d928128e0d97ec7bd55d8dec2846d8681f79a4cd` |
| Unchanged runtime base | `ghcr.io/alphastorm/ninfer@sha256:d4377ed01a5be949a90d3b403a3be2c5867a083cb1669379f60b25969ab7f22e` |
| Image receipt release | `v0.7.0-qwen38-5090-runtime-beta.2` |
| Original base receipt release | `runtime-base-04b603aa-20261025`; unchanged Dockerfile/workflows, not a new base cut |
| Model revision / bytes | `1cbd84e7221e51186bd7f093a149912d2489625b` / 20,437,521,664 |
| Model SHA-256 | `81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da` |
| Deployment profile | `qwen38-5090-v0.13.0` |
| Configuration SHA-256 | `751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47` |
| Rendered profile SHA-256 | `a0edfcaac2f5bff648b7b677be33fb25e6e9b3bda08f84c2117f540df2fcfb35` |

The [manifest](manifest.json), [qualification](qualification.json) and
[compatibility matrix](COMPATIBILITY.md) bind these bytes. Publication alone does not prove fresh
anonymous download or client/public-install acceptance. Initial candidate `86e5c0b9` remains
historical; neither its runtime measurements nor its RTX 5090 acceptance is relabelled as beta.2.

## Serving profile and upgrade

131,072-token context; automatic BF16 KV **146,368 tokens**; DFlash2 K=7; optimized proposal head;
vision and preserved thinking; two active requests plus two extra device-state slots; 1,024-token
prefill chunks; 180-second pending timeout; 24,576 MiB checkpoint quota; 256 MiB staging;
60,000 ms keep-warm. Shared Host budget `20867.734375 MiB` is exactly **21,881,405,440 bytes**.
The 28,672 MiB host floor is unchanged. K5 removes `--max-private-continuations` without an alias
or a fixed eight-session guarantee.

Use host directory `checkpoints-v013` mounted at `/checkpoints-v013`. Never mount, scan, copy,
upgrade or migrate v0.12.x generations into it. Keep old roots untouched for rollback; prior
sessions resume by replaying authoritative OMP transcripts for a fresh prefill. Legacy load refusal
is not a promise that quota GC preserves an unsupported operator-selected old root.

## Fresh beta.2 qualification

| Gate | Observed result | Scope |
| --- | --- | --- |
| Full RC | 270 incremental edges / 122 s; host **66/66**, dense **11/11**, zero skips/failures; lease exit 0 / 794 s | Exact F2; loader and canonical shared MTP/fp8 also pass |
| G1 / explicit save | Four boots; **20,926 cached tokens / 27 identical continuation bytes**; authenticated `fsync` save **2,164,056,150 bytes**, four points/states, 329 pages | Actual HTTP/Engine/store, not tracer or predecessor proof |
| E2 / 32 GB | Restore-overlap **38.0356 s**; headroom **1,074,790,400 bytes**; graph growth **+2 MiB** | KV at least context; headroom at least 768 MiB and baseline minus 32 MiB; graph growth at most 64 MiB |
| Keep-warm idle TTFT | Three-sample medians **0.724723 s off / 0.587234 s on**, after 12 s idle | Descriptive only, not powered significance or end-to-end OMP speed |
| Cold exact retrieval | **130,048 tokens**, **56.994 s wall / 56.411 s server**, **2,281.8 tok/s wall** | Zero prefix hit; exact output on strict final profile |
| Decode | **179.86 tok/s server / 176.27 wall**, 2,048 tokens; acceptance 0.244, 2.71 tokens/round | Exact final profile; 30,954 MiB idle VRAM |
| Agent protocol | Authenticated identity, two forks, delete/no-resurrection and surviving sibling pass across `docker restart` | Separate from fresh OMP platform/public-route acceptance |

### G2 provider comparison, not a new final-runtime aggregate

EXP-097's A/B/B/A median across 84 serial role cases is **342.150 versus 338.448 tok/s**,
**101.09%** of shipped, above the founder-amended **96%** floor. All 336 role and 48 depth requests
returned HTTP 200. Configured concurrency two and overlapping depth pairs are not constant-batch-two
throughput. [Full evidence](../../docs/measurements/2026-10-25-exp097-role-corpus.json) preserves the
original strict-tail **FAIL** and amended **PASS**, structured-output p95 ratio **1.126**, and
64K continuation **335.332 → 290.781 tok/s** / **338 → 392 rounds**.
The [canonical-tool counterfactual](../../docs/measurements/2026-10-25-exp097-canonical-tools-diagnostic.json)
was **diagnostic-only and reverted** in that measurement branch; integration later landed sorted-key
serialization `0abe7c8e5` with host byte pins. No full G2 after that fix or F2 remediation is claimed.
Measured source/model remain `c2dbcbae` / locally upgraded `facba3bd`, persistence disabled,
fixed 131,072 KV tokens. [Benchmarks](../../docs/BENCHMARKS.md) keeps these workloads separate.

## Carried natives and known gaps

| Lane | Unchanged component | Source / model | Boundary |
| --- | --- | --- | --- |
| RTX 4090 | `v0.6.11-qwen38-4090-beta.1` | `cad19767` / `eec39564` | MTP3, INT8 KV, 131,072 context, one request, text/tools |
| RTX 3090 | `v0.6.3-qwen38-3090-beta.1` | `cad19767` / `eec39564` | MTP3, INT8 KV, 131,072 context, one request, text/tools |

Both remain GPU-UUID-bound and sequential on port `18082`. Unchanged-package qualifications carry;
Main reports their OMP 18.12.6 public-install windows remain valid, but actual evidence/pins must be
bound. RTX 4090 has no supported rollback target on the two-GPU lineage; RTX 3090 retains its
qualified predecessor. Rebased natives target **v0.13.1**, requiring the 24 GB admission-headroom
amendment (**640 MiB RTX 4090 / 768 MiB RTX 3090**), packages/dependency SBOMs and native hardware/K6
qualification. Linux proof does not qualify new Windows durability semantics.

- **Accepted/deferred council residuals:** worker import/proof I/O can delay decode; superseded
  durable-owner metadata and authenticated gate churn can retain capacity/metadata; stale saves
  can leave bounded orphan work. Strict MACs prove origin/content, not monotonic anti-replay.
  Workflow base selection remains digest-pinned but is not automatically cross-checked with the
  selected source's base receipt. Full dispositions remain in the ledger; these are not erased fixes.
- **Not re-measured:** powered quality/leak/global output parity, historical eight-session fanout,
  warm-arrival/long OMP compaction, actual OMP parallel/agent-mix latency, and full G2 after F2.
- **Remaining release gates:** lead lane pin, fresh beta.2 RTX 5090 three-platform/client/public-route
  evidence and restoration, unchanged-native evidence binding, then platform/composed acceptance/
  manifest pins and require-ready/check-pins. The founder alone publishes the product tag/release.
- Saves remain best effort; no universal warm reuse, loss-free shutdown, zero queueing, multi-tenant,
  multi-GPU, simultaneous native serving, silent fallback, SLA or new signing claim. macOS is preview;
  Linux evidence is WSL2-scoped, not independent native Linux OS qualification.
