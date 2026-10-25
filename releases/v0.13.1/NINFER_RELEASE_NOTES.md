# OMP NInfer v0.13.1 — rebased native Windows lanes

**Preparation only: no installable manifest, frozen native cut or accepted candidate exists here.**
The published product remains [v0.13.0](../v0.13.0/NINFER_RELEASE_NOTES.md). This notes-only tree
is input to `stage_release.py --from v0.13.0 --release v0.13.1 --prepared-draft`, not authorization
to install, change production or publish. Source and package identities arrive from the real cut;
no previous native qualification or product acceptance is relabelled as new-runtime evidence.

Oh My Pi (coding-agent client) connects through OMP NInfer (qualified appliance and release layer)
to NInfer (inference engine) serving Qwen3.8 27B on one user-owned GPU.

## Intended composition

| Lane / client | Component | Preparation boundary |
| --- | --- | --- |
| RTX 4090 native Windows | `v0.7.0-qwen38-4090-beta.1` | Rebased native source N, package/binary/configuration hashes, qualification and public-install acceptance must be bound |
| RTX 3090 native Windows | `v0.7.0-qwen38-3090-beta.1` | Same source freeze; separate lane package, profile, dependency inventory and qualification |
| RTX 5090 container | Unchanged `v0.7.0-qwen38-5090-beta.2`, source `6d4d0a05` | Carry exact v0.13.0 runtime/model/profile; no new container performance measurement claimed |
| Oh My Pi | Unmodified upstream `18.12.6`, source `45c35e40` | Same three upstream client binaries; new composition/route acceptance remains separate |

The new native line uses upstream master `64d10fbf9f8e6bfc79ab0570b94674c5b9997929`.
The frozen downstream source N will be declared by the integration owner; a moving branch or
pre-cut experiment is not the package source identity. Each native component's own release ID,
deployment profile and build profile retain the `v0.7.0-beta.1` component version, not the product
version. CUDA architecture is sm_89 for RTX 4090 and sm_86 for RTX 3090; native packages use CUDA 13.3.

## What changes on the native lanes

- **Published model container version 3:** both native lanes move from `eec39564` to the same
  published `81f924d4` artifact already used by RTX 5090. All lanes then bind `components.model`;
  remove the redundant `components.native_model` override only when binding both actual packages.
- **K5 shared Host budget:** separate host-state and host-KV budgets become one byte-exact shared
  budget. `--device-state-slots` counts extra slots, not total concurrent requests. The obsolete
  `--max-private-continuations` flag is absent; no compatibility alias or fixed eight-session
  retention promise is introduced.
- **24 GB admission margin:** `--admission-headroom-mib 640` on RTX 4090 and `768` on RTX 3090.
  These are deliberate release-shape amendments, not a smaller-host qualification or silent
  reduction of the advertised 131,072-token context.
- **Strict checkpoint origin:** both product profiles require
  `--session-checkpoint-require-origin-auth`. The configured checkpoint directory and bearer key
  of at least 32 bytes are mandatory; documented key generation produces 64 characters. Do not
  remove the flag to accept unauthenticated state.
- **Windows durability:** the K6 durable-rename fix is reported by its native implementation
  owner. Exact-source Windows refusal/crash/restore proof and final package qualification remain
  gates; Linux persistence or the RTX 5090 council alone cannot qualify Windows filesystem behavior.
- **Two distinct SBOMs:** retain the package's existing SPDX file inventory. Each native outer
  asset set also carries a dependency-level CycloneDX inventory generated from the actual build's
  resolved dependencies, CUDA DLLs and vendored sources; its own URL/hash and checksum entry are bound.

| Native profile | RTX 4090 | RTX 3090 |
| --- | --- | --- |
| Deployment profile | `qwen38-4090-native-v0.7.0-beta.1` | `qwen38-3090-native-v0.7.0-beta.1` |
| Public config SHA-256 | `9774e70154007aa2e803f7d31766e2edb274209b5b2d48f00429472cea6af4fe` | `73a33e63db44ecb15bb0a64a39b7f77783c14285543c72977ac0a0675bc00c7d` |
| Context / KV capacity | 131,072 / 131,072 tokens | 131,072 / 131,072 tokens |
| KV / speculation | INT8, MTP3 with `--lm-head-draft`; no DFlash2 | INT8, MTP3 with `--lm-head-draft`; no DFlash2 |
| Requests / pending timeout | One / 30 s | One / 30 s |
| Extra device-state slots | 2 | 4 |
| Prefill chunk | 2,048 tokens | 1,024 tokens |
| Shared Host budget | 15,506,063,360 bytes (`14787.734375 MiB`) | 12,284,837,888 bytes (`11715.734375 MiB`) |
| Admission headroom | 640 MiB | 768 MiB |
| Keep-warm | 60,000 ms | Disabled (`0`) |
| Endpoint | Authenticated `127.0.0.1:18082` | Authenticated `127.0.0.1:18082` |
| Vision | Disabled; no native vision claim | Disabled; no native vision claim |

Both lanes remain UUID-bound and run sequentially on one two-GPU Windows host. No multi-GPU
inference, simultaneous native serving or automatic lane switching is added. Retain the existing
RTX 4090 32,768 MiB host-memory floor; the budget translation does not qualify a smaller host.
The RTX 3090 serving power policy remains 300 W, subject to actual package/owner-restoration proof.
Native config hashes bind exact UTF-8/LF file bytes frozen at native-ops commit
`e899c7296cec78d71aad5fc8b7d14decc7ff8773`; they are not the container's semantic config digest.

## Model download and checkpoint transition

Download the published artifact directly; do not locally upgrade or resume a version 3 download
onto an old version 2 model file. Native route blocks now select `components.model`, verify each
variant binds it, and store it separately as `qwen3_8_27b-v3.ninfer`.

| Model binding | Exact value |
| --- | --- |
| Repository | `https://huggingface.co/neroued/Qwen3.8-27B-NInfer` |
| Revision | `1cbd84e7221e51186bd7f093a149912d2489625b` |
| Artifact | `qwen3_8_27b.ninfer`, 20,437,521,664 bytes |
| SHA-256 | `81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da` |

Native schema 4 configuration selects a new schema 3 checkpoint directory under each immutable
component release's own cache root. Keep prior native release roots untouched for rollback;
never scan, copy, migrate or import their generations into the rebased store. Prior native sessions
resume by replaying authoritative OMP transcripts for a fresh prefill. Saves remain best effort.
The unchanged RTX 5090 keeps its existing `/checkpoints-v013` mount and exact restore identity;
this native transition does not migrate or invalidate that separate lane's compatible store.

Within one API-key principal, prompt_cache_key names a session capability; use unique high-entropy keys and do not share that principal among mutually untrusted clients.

## Measurements available before the cut

| Program-owner real-model workload | RTX 4090 | RTX 3090 | Scope |
| --- | ---: | ---: | --- |
| Native C1 decode, 131,072 context/capacity, INT8 KV, MTP3 | 137.35 tok/s | 78.33 tok/s | Pre-cut experiment, not yet bound to final source/package/profile receipt |

These numbers are not a like-for-like speedup, powered quality screen, end-to-end OMP result or
final-package qualification. Exact-context retrieval, restart byte identity, refusal/security,
Windows K6 failure cases, grammar and public-route/client acceptance must bind actual lane receipts.
Public profiles use port `18082`; any port-only scratch qualification uses its own config/package
hash and explicit equivalence evidence. A scratch installation is not a public-package execution.

**JSON-schema support on natives remains gated:** real grammar plus Chat/Responses product tests
and lane qualification must establish `text.format` / `response_format` `json_schema` before the
matrix advertises support. The new runtime targets 128-character tool names and status schema 2 /
request-log schema 30; those are prepared contracts, not inherited support claims. Published
v0.13.0 native packages retain their HTTP 400 schema refusal and 64-character names until upgraded.

## Unchanged RTX 5090 and client

The carried container binds server `9790a004`, archive `52dd3be7`, image
`ghcr.io/alphastorm/ninfer-runtime@sha256:5d10a998a42ba927dd8bbe54d928128e0d97ec7bd55d8dec2846d8681f79a4cd`,
base `d4377ed0`, profile `qwen38-5090-v0.13.0` and strict-origin configuration `751d22dc`.
Its 179.86 tok/s server decode, 56.994 s exact retrieval and 20,926-token/27-byte restart result
remain v0.13.0 observations of those unchanged bytes, not new v0.13.1 measurements.
Stock OMP 18.12.6 source/tree/assets and per-model `compat.statefulResponses` remain unchanged.

## Remaining release gates and support boundaries

1. Freeze native N and byte-exact public profiles; reconcile any scratch port-only config/package
   projections explicitly. Bind both real package/build/checksum sets and dependency SBOMs.
2. Bind actual native lane qualification, exact-context/restart/refusal/Windows K6 evidence and
   changed-source review dispositions. Neither earlier native receipts nor Linux-only proof transfers.
3. Stage the prepared tree, remove the old native-model override, audit inherited evidence by
   unchanged subject, rebind the real manifest, and commit/pin the candidate without promoting roots early.
4. Fresh client/platform, all five documented routes, both native public installs, rollback/upgrade
   lineage where actually supported, and independent host restoration. Changed native model-download
   blocks require an explicit `documented_routes.document_change`, not a claim of byte-identical prose-only editing.
5. Compose and pin platform, acceptance and manifest evidence; require-ready/check-pins, tests and
   CI before founder-only product publication. No product release date is assigned here.

macOS remains preview; Linux client evidence remains WSL2-scoped. No new native vision, DFlash2,
smaller-host support, universal warm reuse, loss-free shutdown, cross-owner recovery, SLA, signing,
notarization, multi-tenancy or silent fallback claim is made. Rollback may only use a real supported
predecessor and its own model/binary/config/root; no predecessor or successful direction is invented.
