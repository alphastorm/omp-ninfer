# OMP NInfer v0.13.0

**Staged draft; not a published product or an accepted public-install candidate.** The runtime
components are published and their exact bytes are bound below. Council disposition, lane pin,
stock-client acceptance and public-route pins remain explicit gates. The published product remains
[v0.12.2](../v0.12.2/NINFER_RELEASE_NOTES.md); these notes do not authorize an upgrade or publication.

Oh My Pi (coding-agent client) connects through OMP NInfer (qualified appliance and release
layer) to NInfer (inference engine) serving Qwen3.8 27B on one user-owned GPU.

## What changes

- **Rebased RTX 5090 runtime:** `v0.7.0-qwen38-5090-beta.1`, frozen downstream source
  `04b603aae4e9ce3c26f4175cf808180c0f05b5fe`, on Neroued/ninfer master
  `64d10fbf9f8e6bfc79ab0570b94674c5b9997929`. This replaces v0.12.2's `1302d639` source
  and `6e8b2e2a` base. Upstream owns scheduling, grammar, context caches and DFlash2 execution;
  the product carries authenticated durable sessions, retained Responses and measured kernel routes.
- **Schema 3 durable store:** authenticated checkpoint sets preserve Responses lineage and native
  continuation state on the new context substrate. Fingerprint schema 2, checkpoint schema 3,
  status schema 2 and request-log schema 30 are separate contracts, not interchangeable versions.
- **JSON-schema structured output is supported on the RTX 5090 lane:** upstream xgrammar,
  the frozen-source real grammar test and product `serve_contract` / `agent_product` smokes
  qualify Responses `text.format` and Chat Completions `response_format` with `json_schema`.
  This is runtime feature evidence, not fresh OMP platform/public-route acceptance. Carried native
  packages still reject these requests with HTTP 400.
- **Tool names:** the rebased Chat/Responses boundary accepts up to 128 characters. Carried
  native packages retain their 64-character limit. Container capabilities do not transfer to natives.
- **Non-blocking checkpoint export:** capture runs under execution serialization; bulk transfers,
  hashing and writes run outside the execution lock. Epoch-checked publication prevents stale
  exports replacing newer state. This addresses `alphastorm/ninfer#34`, not all queueing latency.
- **Published model container version 3:** use upstream artifact `81f924d4`, not a local
  conversion. All 1,184 tensor payloads and six frontend resources matched the production model
  upgraded locally; whole-container bytes differ. Text, vision, MTP and DFlash2 are present.
- **Stock Oh My Pi 18.12.6:** unmodified upstream assets on all three client platforms. The
  [host-free review](../../docs/measurements/2026-10-25-omp-18126-client-upgrade-review.json)
  covers asset checksums, Responses wire invariants, the image-aware snapcompact gate and print-mode
  slash dispatch. A loopback stub is not live inference or memory proof.

## Exact component bindings

| Subject | Identity |
| --- | --- |
| Binary archive | `ninfer-qwen38-rtx5090-v0.7.0-linux-x86_64-cuda13.1.tar.gz`, 547,027,462 bytes |
| Archive SHA-256 | `ede7a6c95bf0a4950b7703fd46e8d085afe208818d808421368f7bd80bdb6944` |
| `ninfer-serve` SHA-256 | `48d736aae65a7b2edfb8c4cfea547b97af1671e0e443d78499ba4b66833d3232` |
| Source archive SHA-256 | `98a33db050c6145eae02bdc1c126180be34e62acde9fdb5550976ffcacbd4e95` |
| SPDX SHA-256 | `de8a9e65194e4732a82c5cdd0b542e67b6407f1b311a38714e47114d426dc0fc` |
| Runtime image | `ghcr.io/alphastorm/ninfer-runtime@sha256:e0419f48a50946d862959d6bdf586efc0ef6e36c8685638b7bf7ff68fc30a605` |
| Runtime base | `ghcr.io/alphastorm/ninfer@sha256:d4377ed01a5be949a90d3b403a3be2c5867a083cb1669379f60b25969ab7f22e` |
| Image receipt release | `v0.7.0-qwen38-5090-runtime-beta.1` |
| Base receipt release | `runtime-base-04b603aa-20261025` |
| Model revision | `1cbd84e7221e51186bd7f093a149912d2489625b`, 20,437,521,664 bytes |
| Model SHA-256 | `81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da` |
| Deployment profile | `qwen38-5090-v0.13.0` |
| Configuration SHA-256 | `c73eb8fbe14a7fdbfbbd20aaeb13b7fec5783ca53f077a7b757f2f706ab3205f` |

The [manifest](manifest.json), [qualification summary](qualification.json) and release-local
[compatibility matrix](COMPATIBILITY.md) bind the composition. Published runtime base/image
receipts do not establish anonymous public download or product installation acceptance.

## Serving profile and upgrade behavior

The profile keeps 131,072-token context, automatic BF16 KV, DFlash2 with seven draft tokens,
optimized proposal head, vision, preserved thinking, two active requests, 1,024-token prefill
chunks, 180-second pending timeout, 24,576 MiB checkpoint quota, 256 MiB staging and
60,000 ms GPU keep-warm. Frozen-runtime automatic capacity is **146,368 KV tokens**.

- **Isolated checkpoint root:** host directory `checkpoints-v013` mounts at `/checkpoints-v013`.
  Never mount, scan, copy or migrate the v0.12.x `checkpoints` generations into this root.
  Preserve the old root untouched for rollback. Legacy outer schemas are refused without mutation.
- **Prior sessions replay:** v0.12.x server-side state is not carried. Resume the saved OMP
  transcript for a fresh prefill. The transcript remains authoritative; new compatible checkpoints
  accelerate later restarts but never replace it.
- **Shared Host budget:** `--host-context-mib 20867.734375` is 21,881,405,440 bytes, replacing
  24 host-state slots plus 16,384 MiB host KV. `--device-state-slots 2` means two extra slots
  beyond the two active lanes, four total. The 28,672 MiB host floor is unchanged.
- **Removed control:** K5 rejects `--max-private-continuations`; upstream resource-budgeted
  retention has no replacement alias or fixed eight-session guarantee. The exact binary accepts
  all 24 staged profile flags, including the integrated keep-warm worker.
- Saves remain best effort. A crash or expired graceful-stop wait can lose unpublished acceleration
  state. Cross-version/GPU checkpoint migration, universal warm reuse, zero queueing and loss-free
  shutdown are not promised. Qualification does not activate a production upgrade.

## Measured qualification

| Gate | Observed result | Scope |
| --- | --- | --- |
| Build and integrated tests | 172 incremental build steps / 109 s; host **65/65**, dense **11/11**, zero skips/failures | Frozen source; explicit loader and canonical shared MTP/fp8 also pass |
| G1 production restart | **20,926 cached tokens**, **27 byte-identical continuation bytes**, four boots | Actual HTTP/Engine/authenticated store, not the historical tracer |
| Explicit durable save | **2,164,056,150 bytes**, four points/four states/329 pages, 20,993 restored frontier tokens | Authenticated origin and `fsync`; deleted ancestor stays 404, descendant 200 |
| Pressure/C2 | Frozen-source E2 passes in **29.4234 s** | Separately identified provider proof restores before sibling decode finishes; no weakened overlap assertion |
| 32 GB startup | **146,368 KV tokens**; **1,074,790,400 bytes** headroom; graph reservation **+2 MiB** versus vanilla | Amended policy: KV at least context, headroom at least 768 MiB and baseline minus 32 MiB, graph growth at most 64 MiB |
| Keep-warm idle TTFT | Three-sample medians **0.747845 s off / 0.586125 s on** after 12 s idle | Descriptive, not a powered significance claim; C2 siblings exercise both arms |
| Long retrieval | Exact **130,048-token** NIAH in **56.921 s wall / 56.334 s server**, **2,284.7 tok/s wall** | Cold, zero prefix hit, exact final release profile |
| Decode | **180.06 tok/s server / 176.49 tok/s wall**, 2,048 tokens | Final profile; DFlash2 acceptance 0.244, 2.71 tokens/round; 30,954 MiB idle VRAM |
| Agent protocol | Authenticated session, two forks, delete/no-resurrection and surviving sibling pass across `docker restart` | Exact release configuration; three stock-client platform acceptances remain separate |

[Benchmarks](../../docs/BENCHMARKS.md) separates these gates from predecessor results and
EXP-097's different workload. No v0.12.2 runtime observation is relabelled as new-runtime proof.

### G2 matched decode comparison

EXP-097's A/B/B/A median across 84 role cases is **342.150 tok/s** rebased versus
**338.448 tok/s** shipped, **101.09%**, clearing the founder-amended **96%** floor.
All 336 role and 48 supplemental depth requests returned HTTP 200. Role calls are serial;
configured concurrency two and overlapping depth pairs are not constant-batch-two throughput.

The [full evidence copy](../../docs/measurements/2026-10-25-exp097-role-corpus.json) retains
original strict-tail **FAIL** and amended **PASS**. Structured-output p95 is **1.126** of
shipped (12.6% slower), attributed to tool-definition serialization order. The
[counterfactual](../../docs/measurements/2026-10-25-exp097-canonical-tools-diagnostic.json) was
**diagnostic-only and reverted** in that measurement branch. Integration subsequently landed
canonical sorted-key serialization `0abe7c8e5` with host byte pins; the full corpus was not rerun.
At 64K continuation depth the measured decode remains **335.332 → 290.781 tok/s**, with
**338 → 392 rounds**. Neither the aggregate nor the later fix erases that measured gap.

G2 source is `c2dbcbae`, binary `2f8498d9`, locally upgraded model `facba3bd`, persistence disabled,
fixed 131,072 KV tokens. It is a provider comparison, not a new final-binary/public-model benchmark.
Full-model output/acceptance identity and fresh powered quality/leak screening are not proven.

## Carried native Windows lanes and v0.13.1 gap

| Lane | Unchanged component | Source / model | Boundary |
| --- | --- | --- | --- |
| RTX 4090 | `v0.6.11-qwen38-4090-beta.1` | `cad19767` / `eec39564` | MTP3, INT8 KV, 131,072 context, one request, text/tools |
| RTX 3090 | `v0.6.3-qwen38-3090-beta.1` | `cad19767` / `eec39564` | MTP3, INT8 KV, 131,072 context, one request, text/tools |

Package qualification and SHA256SUMS carry because those subjects are unchanged. Public installs
and client acceptance must run again with OMP 18.12.6. Both lanes remain GPU-UUID-bound and
sequential on port `18082`; native schema output and vision remain unsupported. The RTX 4090
has no supported rollback target on the two-GPU lineage; RTX 3090 retains its qualified predecessor.

Rebased natives target **v0.13.1**, not this release. The new 24 GB shapes require K5's
`--admission-headroom-mib` amendment (**640 MiB RTX 4090 / 768 MiB RTX 3090**). Engineering
real-model decode passes do not constitute released packages: rebased source/package/dependency
SBOM/hardware qualification and public-install acceptance are not yet bound or claimed here.

## Remaining gates and known gaps

- **G4 council:** `review/runtime-ledger.json` is an explicit pending binding for the lead's
  actual frozen-source ledger/dispositions, not a predecessor approval.
- **Lane and acceptance pins:** the lead pins this clean stage before fresh three-platform
  OMP 18.12.6 acceptance, all five routes/31 blocks, both native public installs and independent
  incumbent/native restoration; then pins platform, composed acceptance and manifest in order.
- **Not re-measured for v0.13.0:** powered quality/leak and global output parity; historical
  eight-session fanout/warm-arrival, long OMP sessions/compaction, actual OMP parallel-dispatch and
  agent-mix latency; full G2 after canonical serialization. Scoped current tests do not replace them.
- macOS stays preview; Linux live evidence is scoped to WSL2, not native Linux OS qualification.
  No multi-tenant, multi-GPU, simultaneous native serving, silent cloud fallback, SLA or new signing
  claim is added. The founder alone publishes the product tag and GitHub release.
