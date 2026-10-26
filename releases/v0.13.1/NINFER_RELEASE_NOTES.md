# OMP NInfer v0.13.1 — rebased native Windows lanes

**Prepared composition: fresh candidate acceptance passed; product publication is separate.**
The published product remains [v0.13.0](../v0.13.0/NINFER_RELEASE_NOTES.md). Native beta.1 cuts
at `eecb437f` were published but are superseded after a fork CI test-fixture failure; they are not
the accepted v0.13.1 subject. The successor `7a25cd72` has exact-head fork CI, actual beta.2
packages and both fresh full native hardware chains. Both native beta.2 component prereleases,
exact 11-file sets and byte-mirrored qualification/profile bindings are recorded.
The native council closed without remediation, and fresh public-route/client acceptance passed
on candidate `92dfb132`. Product-tooling council binding and final evidence pins remain separate;
no earlier native measurement or product acceptance is relabelled.

Oh My Pi (coding-agent client) connects through OMP NInfer (qualified appliance and release layer)
to NInfer (inference engine) serving Qwen3.8 27B on one user-owned GPU.

## Draft composition

| Lane / client | Component | Qualification boundary |
| --- | --- | --- |
| RTX 4090 native Windows | `v0.7.0-qwen38-4090-beta.2` | Published, fresh source/package/profile qualification and candidate-bound public-install acceptance |
| RTX 3090 native Windows | `v0.7.0-qwen38-3090-beta.2` | Same source; separate package, profile, dependency inventory and qualification |
| RTX 5090 container | Unchanged `v0.7.0-qwen38-5090-beta.2`, source `6d4d0a05` | Carry exact v0.13.0 runtime/model/profile; no new container performance measurement claimed |
| Oh My Pi | Unmodified upstream `18.12.6`, source `45c35e40` | Same three upstream client binaries; fresh three-platform/live/route acceptance passed |

The new native line uses upstream master `64d10fbf9f8e6bfc79ab0570b94674c5b9997929`.
The frozen native source is `7a25cd72f490183e4113f1e84e68e36d653ddd28`; a moving branch or
superseded experiment is not its identity. Component tags, exact public configuration and scratch
equivalence remain distinct bindings. CUDA architecture is sm_89 for RTX 4090 and sm_86 for
RTX 3090; native packages use CUDA 13.3.

## What changes on the native lanes

- **Published model container version 3:** both native lanes move from `eec39564` to the same
  published `81f924d4` artifact already used by RTX 5090. All lanes then bind `components.model`;
  the staged manifest removes the redundant `components.native_model` override.
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
- **Windows durability:** K6 uses handle-anchored replacement, extended-length roots and a
  current-parent publication fence. A failed replacement/flush cannot acknowledge a save or
  delete a possibly visible generation. The native starting source was already handle-anchored;
  this is not a second application of the earlier RTX 5090 pathname finding. Windows NTFS
  `ntfs-write-through` is not POSIX `fsync` or a power-loss guarantee.
- **Capacity and finite exports:** physical disk exhaustion returns the existing `capacity`
  refusal, including HTTP 409 on DELETE without mutating surviving Responses objects. The first
  I/O cause and possibly visible generation survive error propagation. Admission waits for
  prepared off-worker export leases when capacity can become available; completion releases
  those leases before waking admission. Genuine impossibility, queue expiry and reclaim policy
  are unchanged; no global serialization, sleep retry or fabricated progress is introduced.
- **Two distinct SBOMs:** retain the package's existing SPDX file inventory. Each native outer
  asset set also carries a dependency-level CycloneDX inventory generated from the actual build's
  resolved dependencies, CUDA DLLs, vendored sources, CRT and DirectStorage redistributables.
  The canonical `<package-stem>.cdx.json` has its own URL/hash and outer checksum entry:
  10 hashed entries plus `SHA256SUMS` make 11 files. It does not rename or replace the SPDX.

| Actual beta.2 public profile | RTX 4090 | RTX 3090 |
| --- | --- | --- |
| Deployment profile | `qwen38-4090-native-v0.7.0-beta.2` | `qwen38-3090-native-v0.7.0-beta.2` |
| Public config SHA-256 | `b21cdaf8b5edeed4e7d498edf5dbfae77a993145f1d511a8e1aa1b7bdab42950` | `b49aad9915dd333f14cc7a3f0bb269aec124b38112e8ea984af3f569fe2dac75` |
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
Native config hashes bind the exact UTF-8/LF bytes in the actual beta.2 packages at `7a25cd72`;
they are not beta.1 hashes, scratch overrides or the container's semantic config digest.

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

Native schema 4 configuration selects `cache/<release-instance-id>/session-checkpoints-v3`,
a new schema 3 checkpoint directory under each immutable component release's own cache root.
Keep prior native release roots untouched for historical recovery;
never scan, copy, migrate or import their generations into the rebased store. Prior native sessions
resume by replaying authoritative OMP transcripts for a fresh prefill. Saves remain best effort.
The unchanged RTX 5090 keeps its existing `/checkpoints-v013` mount and exact restore identity;
this native transition does not migrate or invalidate that separate lane's compatible store.

Within one API-key principal, prompt_cache_key names a session capability; use unique high-entropy keys and do not share that principal among mutually untrusted clients.

## Fresh native measurements at the frozen source

| `7a25cd72` workload | RTX 4090 | RTX 3090 | Scope |
| --- | ---: | ---: | --- |
| C1 decode, 4,541 prompt / 1,024 completion tokens | 150.94 tok/s | 84.06 tok/s | Actual final-source INT8 MTP3 recipe |
| Exact 130,048-token retrieval | 85.71 s | 208.78 s | Cold-process needle oracle |
| C1 prefill | 2,190.89 tok/s | 921.63 tok/s | 4,541 computed prompt tokens |
| C1 wall / peak VRAM | 8.944 s / 22,847 MiB | 17.202 s / 22,734 MiB | Whole request, not decode timing |
| Process restart | 36.063 s | 37.203 s | Model restart, not a warm-turn speedup |

Both fresh lane receipts record 1,647 cached tokens after explicit save and 1,650 after graceful
stop flush, a replaced process and exact output sentinels. Counters match the independently
measured cold-process baseline; they are not asserted to be absolute zero. These are two short
sessions, not the RTX 5090's 16,384-token G1 frontier or a loss-free-shutdown promise.
Both native lanes are the first of their rebased lineage: rollback is `not_applicable`, zero
directions. The old RTX 3090 two-direction result is not inherited. Native C1 decode is below the
historical 158.66/102.41 tok/s predecessor observations; model/profile changed and no matched A/B,
native speedup/parity, powered quality or end-to-end OMP performance claim is made.
Public profiles use port `18082`; any port-only scratch qualification uses its own config/package
hash and explicit equivalence evidence. A scratch installation is not a public-package execution.

Both fresh canonical schema 2 product smokes passed Chat and Responses JSON-schema output,
authenticated identity, private same-session replay, isolated private-state miss and Responses
lifecycle, at full and reduced shared Host budgets. `shared_stable_prefix` on an isolated session
is permitted public-prefix reuse, not private-state leakage. The rebased natives support
JSON-schema output, 128-character tool names, status schema 2 and request-log schema 30.
Published v0.13.0 natives retain HTTP 400 schema refusal and 64-character names until upgraded.
Actual OMP 18.12.6 typed-tool/result/final-answer oracles and state-security/restoration passed.
Separate fresh candidate-bound public-route/client acceptance also passed; it is not inferred
from these runtime qualification fixtures.

## Unchanged RTX 5090 and client

The carried container binds server `9790a004`, archive `52dd3be7`, image
`ghcr.io/alphastorm/ninfer-runtime@sha256:5d10a998a42ba927dd8bbe54d928128e0d97ec7bd55d8dec2846d8681f79a4cd`,
base `d4377ed0`, profile `qwen38-5090-v0.13.0` and strict-origin configuration `751d22dc`.
Its 179.86 tok/s server decode, 56.994 s exact retrieval and 20,926-token/27-byte restart result
remain v0.13.0 observations of those unchanged bytes, not new v0.13.1 measurements.
Stock OMP 18.12.6 source/tree/assets and per-model `compat.statefulResponses` remain unchanged.

## Remaining release gates and support boundaries

The native council dispositions are bound; product-tooling council closure remains to be bound
before the final manifest pin. The stage and lane pin are complete. Fresh acceptance on candidate
`92dfb13285994f1527711cf464847f07e44613dd` passed all five documented routes (31 exact blocks),
three stock OMP 18.12.6 clients and both native public installs, with independent restoration.
Both canonical native roots were freshly installed from the documented beta.2 blocks after
preserving their old lineages; both rebased lineages have no predecessor and zero rollback
directions. The later public-URL checks returned `already_installed`, not another promotion.
Changed native package/model-download blocks have an explicit `documented_routes.document_change`;
the current guide's later edits are prose only. Final evidence pins, tests and CI precede product
publication by the lead. No product release date is assigned here.

macOS remains preview; Linux client evidence remains WSL2-scoped. No new native vision, DFlash2,
smaller-host support, universal warm reuse, loss-free shutdown, cross-owner recovery, SLA, signing,
notarization, multi-tenancy or silent fallback claim is made. Rollback may only use a real supported
predecessor and its own model/binary/config/root; no predecessor or successful direction is invented.
The coordinator does not distinguish disk capacity from native capacity for bounded rearm:
external disk reclamation alone does not trigger it; Engine/admission progress or explicit client
retry is still required. MACs authenticate content/origin, not monotonic freshness; an authorized
filesystem writer can replay an older authentic generation.
The unchanged RTX 5090 retains its deferred owner/session-gate metadata churn, stale-publication
orphan work and workflow base-receipt cross-checking gaps; this native port does not claim to fix them.
The carried RTX 5090 runtime also predates the native export-lease admission fix
(`5ecb96fb5`): an isolated request arriving while a durable checkpoint export writes off the
execution lock can fail that engine until restart. Reachability on the RTX 5090 lane has not been
reproduced ([#88](https://github.com/alphastorm/omp-ninfer/issues/88)).
Native installer rollback after a failed candidate stop still removes candidate targets and the
candidate GPU-owner lease before repair, unchanged from v0.12.2. Recovery is process exit or
reboot plus `-RepairInterruptedInstall`
([#89](https://github.com/alphastorm/omp-ninfer/issues/89)).
