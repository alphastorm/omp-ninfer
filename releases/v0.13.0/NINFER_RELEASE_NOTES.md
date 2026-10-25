# OMP NInfer v0.13.0

**Release preparation, not a published or installable candidate.** Runtime cut identities,
qualification and fresh route acceptance are not yet bound. The published release remains
[v0.12.2](../v0.12.2/NINFER_RELEASE_NOTES.md). These notes accompany the prepared profile;
they do not authorize publication or a production upgrade.

Oh My Pi (coding-agent client) connects through OMP NInfer (qualified appliance and release
layer) to NInfer (inference engine) serving Qwen3.8 27B on one user-owned GPU.

## What changes

- **RTX 5090 upstream-base move:** runtime component `v0.7.0-qwen38-5090-beta.1` targets
  Neroued/ninfer master `64d10fbf9f8e6bfc79ab0570b94674c5b9997929`, replacing the fork base
  `6e8b2e2a` used by source `1302d639` in v0.12.2. The frozen downstream source, binary,
  archives, SBOM and image digest come from the component cut; no moving branch is an
  install identity. Upstream owns scheduling, grammar, context caches and DFlash2 execution.
- **Durable store schema 3:** authenticated checkpoint sets preserve Responses lineage and
  engine continuation state on the new context substrate. Runtime fingerprint schema 2,
  checkpoint schema 3, status schema 2 and request-log schema 30 are distinct contracts.
  A checkpoint restores only into the exact compatible binary, model, frontend and profile.
- **JSON-schema structured output:** the rebased RTX 5090 runtime implements upstream
  xgrammar constrained decoding through Responses `text.format` and Chat Completions
  `response_format` with `json_schema`. The compatibility authority marks this
  **acceptance pending**, not supported, until live positive/negative schema gates pass.
  Carried native packages still reject these requests with HTTP 400.
- **Tool names:** the rebased runtime accepts names up to 128 characters; boundary
  acceptance must cover both Chat Completions and Responses. Carried native packages retain
  their existing 64-character limit. No native capability is inferred from the RTX 5090 port.
- **Non-blocking checkpoint export:** engine state is captured under serialization, then
  transfers, hashing and bulk writes run outside the engine execution lock. Final publication
  still checks the session epoch so an older export cannot replace newer state. This closes
  the long engine-lock hold behind `alphastorm/ninfer#34`; it does not promise zero queueing.
- **Published model container version 3:** use the upstream artifact, not a local conversion:
  `neroued/Qwen3.8-27B-NInfer` revision `1cbd84e7221e51186bd7f093a149912d2489625b`,
  `qwen3_8_27b.ninfer`, **20,437,521,664 bytes**, SHA-256
  `81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da`.
  Components are text, vision, MTP and DFlash2. Infrastructure compared all 1,184 tensor
  payloads and all six frontend resources with the production model upgraded locally:
  byte-identical payloads/resources, not byte-identical whole containers.
- **Stock Oh My Pi 18.12.6:** all three platforms use unmodified upstream release assets.
  The [host-free review](../../docs/measurements/2026-10-25-omp-18126-client-upgrade-review.json)
  covers the Responses client, image-aware snapcompact gate and print-mode slash dispatch.
  It is not live runtime acceptance.

## Serving profile and upgrade behavior

The prepared `qwen38-5090-v0.13.0` profile keeps 131,072-token context, automatic KV sizing,
BF16 KV, DFlash2 with seven draft tokens and optimized proposal head, vision, preserved
thinking, two active requests, 1,024-token prefill chunks, 180-second pending timeout,
24,576 MiB checkpoint quota, 256 MiB checkpoint staging and 60,000 ms GPU keep-warm.
Automatic KV capacity must be recorded from the frozen runtime, not copied from the predecessor.

- **New checkpoint root:** host directory `checkpoints-v013` mounts at `/checkpoints-v013`.
  Do not mount the v0.12.x `checkpoints` directory, copy its generations into the new root,
  run a schema upgrader, or scan/import the old store. Keep the old root untouched for rollback.
  The loader refuses legacy outer schemas without mutation, even with an invalid legacy MAC.
- **Prior sessions:** v0.12.x server-side checkpoint state is not carried forward. Resume
  the saved Oh My Pi transcript; the client replays it for a fresh prefill on the new runtime.
  The transcript remains the source of truth. Within the new exact-runtime boundary,
  eligible checkpoints accelerate subsequent graceful-restart continuations.
- **Unified Host budget:** `--host-context-mib 20867.734375` is exactly 21,881,405,440 bytes,
  replacing 24 host-state slots plus 16,384 MiB host KV for this shape. Device-state slots
  remain `2` extra beyond active lanes (four total), not two total. The 28,672 MiB host
  floor is unchanged; the byte-equivalent translation is not a new memory tuning experiment.
- **Removed catalog flag:** K5 deliberately rejects `--max-private-continuations 8`;
  upstream resource-budgeted retention is authoritative, with fanout and warm-arrival
  qualification checking behavior. It has no replacement alias or fixed eight-session promise.
- **Keep-warm integration:** the profile retains `--gpu-keep-warm-ms 60000`. Candidate freeze
  requires the integrated binary's accepted-flag inventory and the keep-warm provider/proof;
  an unmerged parser is not permission to drop the tuning value.
- **No in-place production change:** qualification installs only an owned temporary route,
  then independently restores the incumbent image, restart policy, directories and keys.

Saves remain best effort under live traffic. A crash or an expired graceful-stop wait may
lose unsaved acceleration state. Cross-version/GPU checkpoint migration, universal warm reuse,
loss-free shutdown and automatic container restart are not claimed.

## Native Windows posture

The default v0.13.0 staging variant carries the v0.12.2 native packages unchanged:

| Lane | Component | Source | Model | Serving boundary |
| --- | --- | --- | --- | --- |
| RTX 4090 | `v0.6.11-qwen38-4090-beta.1` | `cad19767` | `eec39564` | MTP3, INT8 KV, one active request, text/tools only |
| RTX 3090 | `v0.6.3-qwen38-3090-beta.1` | `cad19767` | `eec39564` | MTP3, INT8 KV, one active request, text/tools only |

Both public native installations must be accepted again with OMP 18.12.6. Carrying package
qualification does not carry client, route or public-install acceptance. Both lanes remain
UUID-bound and sequential on shared port `18082`. The RTX 4090 two-GPU lineage has no supported
rollback target; the RTX 3090 retains its actual qualified predecessor.

An alternative staging variant may bind `v0.7.0-qwen38-4090-beta.1` and
`v0.7.0-qwen38-3090-beta.1` only after their own frozen source, published assets, dependency
SBOMs, model bindings and hardware qualifications arrive. Their capabilities and performance
come from those receipts, not from the container lane. If they miss the release, they follow
in v0.13.1; the unchanged native variant is the authorized fallback.

## Performance and limitations

**EXP-097:** matched A/B/B/A role-corpus median decode is **342.150 tok/s**
for the rebased runtime versus **338.448 tok/s** shipped (**101.09%**), 84 cases,
fixed 131,072-token KV capacity, configured concurrency two, DFlash2 K=7 and BF16 KV.
Role requests run serially; supplemental pairs overlap prefill/decode, not constant-batch-two decode.
This clears the 96% release floor; there is no aggregate decode-gap claim to hide.
The structured-output workload's p95 ratio is **1.126** (12.6% slower), attributed in the
runtime receipt to tool-definition serialization order. A throughput aggregate does not erase
that workload regression or establish faster end-to-end OMP work.

The [complete product evidence copy](../../docs/measurements/2026-10-25-exp097-role-corpus.json)
preserves the original strict-tail **FAIL** alongside the founder-amended **PASS**.
At 64K continuation depth, decode regresses **335.332 → 290.781 tok/s** as rounds rise
**338 → 392**, despite faster rounds. The
[tool-order counterfactual](../../docs/measurements/2026-10-25-exp097-canonical-tools-diagnostic.json)
is diagnostic-only and reverted, not a shipped fix. Performance source is `c2dbcbae`, with
persistence disabled and locally upgraded model `facba3bd`; tensor/frontend equivalence supports
the comparison, not a relabelled public-artifact or final-runtime acceptance claim.
[Benchmarks](../../docs/BENCHMARKS.md) separates predecessor results from the candidate.

## Qualification and cut gates

The prepared [qualification gate prose](qualification.json) resets predecessor observations:

1. Freeze the integrated source and accepted CLI inventory; bind the component archive,
   source archive, SBOM, binary hash and published image digest.
2. Bind real restart, restore-failure, pressure/concurrency, 32 GB startup, schema-output,
   tool-name and quality/leak receipts. G1 requires byte-identical continuation with at least
   16K checkpoint-hit tokens after a real restart; EXP-097 supplies the separate G2 comparison.
3. Complete the frozen-candidate critical-review council and its remediation epoch.
4. Stage and commit exact bytes, then lane-pin a candidate. Re-run all five documented
   routes, three stock-client platforms and both native public installs in approved windows,
   with independent restoration. The changed route blocks cannot reuse v0.12.2 block hashes.
5. Compose actual acceptance; mark JSON-schema supported only after its live gate passes.
   Pin platform, acceptance and manifest evidence in order. The founder alone publishes
   the product tag and GitHub release; post-publication docs flip separately.

## Client assets

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `omp-darwin-arm64` | 197,245,984 | `cfbb5e38cd8f8a3be55e710700be587d287deaacdc58c9b0a661c5086bccfe58` |
| `omp-windows-x64.exe` | 224,254,976 | `73d73c11dc8821cf939441a964992aefc9c5b0d5a4418e9e8985a46439b60eef` |
| `omp-linux-x64` | 256,702,432 | `85d9daf3a05fc76e8cd425ae1904eb576af8d21cc85fcf4690742626e07ccfa4` |

Source `45c35e40c46166dc726ccc52f5d27f40f2449f99`, tree
`8a90a1b48b370649bd3f026d5f609e500626785c`; descriptor:
[`2026-10-25-omp-18126-client-components.json`](../../docs/measurements/2026-10-25-omp-18126-client-components.json).
macOS remains preview. Linux live evidence remains scoped to WSL2, not a separate native Linux
OS qualification. No signing/notarization, SLA, multi-tenant or multi-GPU inference claim is added.
