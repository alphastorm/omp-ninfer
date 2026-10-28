# OMP NInfer v0.14.0 — one engine source across three lanes

**All three components staged; fresh product acceptance and review remain separate.**
This is not a published product release. The published product remains
[v0.13.1](../v0.13.1/NINFER_RELEASE_NOTES.md). All three beta.3 components bind engine source
`2c6f423bd817b6534158553e1b34ab4959c43165` (N). Component publication, runtime qualification,
candidate-bound external installation, independent review and product publication are distinct
gates. Predecessor product acceptance and review do not transfer to this composition.

Oh My Pi (coding-agent client) connects through OMP NInfer (qualified appliance and release layer)
to NInfer (inference engine) serving Qwen3.8 27B on one user-owned GPU.

## Composition

| Lane / client | Component | Serving shape |
| --- | --- | --- |
| RTX 5090 container | `v0.7.0-qwen38-5090-beta.3` | BF16 KV, DFlash2 K7, C2, vision; kept `qwen38-5090-v0.13.0` profile |
| RTX 4090 native Windows | Published `v0.7.0-qwen38-4090-beta.3` | INT8 KV, MTP3, C1, `Group64` A8 off |
| RTX 3090 native Windows | Published `v0.7.0-qwen38-3090-beta.3` | INT8 KV, MTP3, C1, `Group64` A8 off, 350 W cap |
| Oh My Pi | Unmodified upstream `18.12.6`, source `45c35e40` | Same three client binaries; fresh product acceptance still required |

The upstream base remains `64d10fbf9f8e6bfc79ab0570b94674c5b9997929`. The model remains the
published version 3 artifact `81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da`
(20,437,521,664 bytes, revision `1cbd84e7221e51186bd7f093a149912d2489625b`). No model or OMP
client rebuild is implied. Native packages use CUDA 13.3 (sm_89/sm_86); RTX 5090 uses CUDA 13.1
(sm_120a). The manifest and lane receipts bind the actual packages, binaries and configurations.

## What changes

- **Shared engine source:** native and container fixes now reach one frozen source rather than
  the v0.13.1 split between native `7a25cd72` and container `6d4d0a05`.
- **RTX 5090 decode:** round-tail retirement before response delivery and consumer-capture
  programmatic dependent launch scheduling; BF16 gated attention merge retains its explicit
  materialized-BF16 rounding seam. The TMA descriptor ABI fix is Blackwell-specific.
- **Native prefill:** sm_86/sm_89 specializations improve the measured long-prompt prefill path.
  `Group64` A8 is compiled off on both shipping lanes. Native DFlash2 loading work does not change
  the supported MTP3 profiles or qualify native DFlash2 serving.
- **Upstream picks:** libjpeg-turbo JPEG decoding, grammar/JSON-schema fixes and vision
  preprocessing identity. Native vision remains unsupported.
- **RTX 3090 power:** the qualification/serving cap is 350 W, not the predecessor's 300 W policy.
  Matched P14 measurement arms restored the prior 370 W limit after each arm; that restoration
  is not a promise about another operator's hardware.

## Measured P14 comparisons — not public-install acceptance

These matched A/B results use the checked first-build binaries at N against the shipped beta.2
controls. They are separate from each package's managed qualification benchmark. Native T1
compares retained output bytes; RTX 5090 T1 compares request/output SHA-256 hashes, not retained
byte streams. ABBA ordering and scope are recorded in the qualification receipts.

| Workload | RTX 4090 | RTX 3090 | RTX 5090 |
| --- | ---: | ---: | ---: |
| T1 role parity | 84/84 retained outputs | 84/84 retained outputs | 84/84 request/output hashes |
| Strict C1 median decode, control → candidate | 151.215 → 151.573 tok/s | 90.855 → 90.879 tok/s | Not this workload |
| Strict C1 decode ratio | ×1.00237 | ×1.000265 | Not this workload |
| Serial 84-role median decode, control → candidate | Not this statistic | Not this statistic | 342.04 → 347.57 tok/s (×1.0162) |
| Exact 130,048-token retrieval | 4/4 arms exact | 4/4 arms exact | 57.00 s on the published image; not matched A/B |
| Retrieval prefill, control arms → candidate arms | 85.70/85.62 → 81.48/81.55 s | 197.51/198.70 → 188.16/187.80 s | Not a matched retrieval comparison |

Native strict C1 is 4,541 freshly computed prompt tokens, 1,024 completion tokens, zero reuse,
seed 57004, temperature zero, warm ABBA. All arms finish at length with identical output hashes.
The native decode result is essentially flat; the roughly 5% long-prompt prefill gain is not a
universal decoding or end-to-end OMP speedup. The 5090 role comparison uses the EXP-097 fixed-KV
benchmark shape, not the automatic-KV production profile or a historical parallel-agent campaign.

## A8 remains off

The preregistered symmetric Application B screen used 200 pairs per native lane. RTX 4090 failed
its new-leak gate (five one-way changes, p=1/32). RTX 3090 passed its screen (four one-way changes,
p=1/16), but the founder selected off conservatively. The PASS verdict is retained rather than
rewritten as a failure. Measured PPL deltas match to six decimals across the cards (mean ΔNLL
−0.000742 at 1,024 tokens, +0.001453 at 2,048; worst domain +0.005949); that does not override the
behavioral screen. Investigate the shared new-leak prompt family, fix it and rescreen both cards
before enabling A8. No A8 performance or behavioral benefit is advertised for this release.

## Fresh managed native qualification

Both beta.3 components are published with separate exact 11-file sets, packaged public profiles,
SPDX file inventories and canonical CycloneDX dependency inventories. Both fresh installed
15-phase chains passed, including normal/pressure protocol, strict-origin restart, exact
retrieval, OMP typed-tool/result/final-answer, state security and restoration.

| Managed scratch qualification at N | RTX 4090 | RTX 3090 |
| --- | ---: | ---: |
| C1 decode, 4,541 prompt / 1,024 completion tokens | 151.54 tok/s | 90.64 tok/s |
| C1 prefill | 2,195.36 tok/s | 976.98 tok/s |
| Exact 130,048-token retrieval | 81.78 s | 187.88 s |
| Explicit save / graceful-stop cached tokens | 1,647 / 1,650 | 1,647 / 1,650 |
| Process restart | 34.06 s | 35.02 s |
| Owner power restored | 450 W | 370 W |

These are standalone managed-lane measurements, not the matched strict C1 medians above.
Public packages retain port 18082; installed scratch equivalents change only the listen port
to 18210/18211 and have distinct configuration/package hashes. The public packages were not
executed by these chains. Both lineages have no predecessor: rollback is `not_applicable`,
zero directions, not an inherited beta.2 upgrade/rollback result.

Eleven dependency DLLs reuse the published v0.13.1 builds at the same versions (FFmpeg 8.1.2#3,
hwloc 2.11.2, curl 8.21.0#1, pkgconf 3.0.3 and zlib 1.3.2#1); libjpeg-turbo 3.2.0 remains new.
This replaces private-path-bearing dependency builds, not engine source or checked EXEs.
Both neutral closures were rebuilt twice: all 34 EXE/DLL files matched raw bytes, every checked
EXE stayed identical, and fresh source/public/scratch privacy scans were clean. Source-N host
90/90 matrices per architecture, 78 package units and both Linux three-binary compiles retain
their actual pre-substitution scope rather than claiming they were rerun afterward.

## RTX 5090 exact bytes and reproducibility exception

Server `55f0b95a`, archive `b8f315bc`, source archive `1964794f` and SPDX `17b1c6bd` are the
checked first build at N. The published runtime image is
`ghcr.io/alphastorm/ninfer-runtime@sha256:760fb6bea925eb26d4fa53ab87a126494b69ba7bcfed515d23dee7afa65cdb2a`.
The dependency base `d4377ed0` is reused through `runtime-base-04b603aa-20261025`; its original
source remains `04b603aa`. Schema 4 runtime publication binds that base receipt and source ancestry.
The kept strict-origin configuration is `751d22dc`, not a new profile identity.

The exact shipping bytes passed 66/66 host tests, 11/11 dense real-model tests, 1/1 durable-pressure
overlap, four-boot restart, product shape, exact profile startup, product smokes, flag inventory
and the 84-role T1 comparison. RC attempt 1 was infrastructure-invalid before any workload ran;
its two help checks plus corrected attempt 2's nine workload phases form the recorded passing union.
Restart reused 20,926 cached tokens with 27 byte-identical continuation bytes. The strict profile
retains 146,368 automatic KV tokens and 21,881,405,440 Host context bytes.
The fresh published-image lane receipt records 57.00 s cold exact retrieval (56.416 s server
prefill), 182.49 tok/s server decode / 178.78 tok/s wall for 2,048 completion tokens, and passing
authenticated agent protocol across restart. Idle VRAM is 30,848 MiB. These lane-gate numbers are
not the 84-role median or an end-to-end client measurement.

**Founder-approved 5090-only reproducibility exception:** same-source second builds are not
bit-identical. The first pair differed in 249/574 ELF files; correcting PID-dependent temporary
names reduced the differences to 177/574 linked executables, while all 397 compared object/other
files matched. nvcc 13.1.115 cudafe++ random module-id suffixes were reproduced on individual
relocatable-device-code translation units. Attributing every remaining executable difference to
that cause is an inference, not a normalization proof over all 177 files. The corrected pair is
not the shipping pair and did not rerun RC/T1 after its byte-comparison failure. The founder chose
the already checked first build; deterministic module IDs remain a follow-up. Native shipping
closures independently passed 34/34 EXE/DLL second-build byte comparisons.

Independent source-level op suites passed 88 tests on each native architecture (one expected
nonshipping block-scaled-MoE skip each) and 104 on sm_120a. The 5090 op suite ran on the corrected
second build of N, not the shipping binary; it is not substituted for exact-byte RC/T1 proof.

## Profiles, state and support boundaries

Native profiles retain 131,072 context/KV, INT8 MTP3, one request, 30-second pending timeout,
640/768 MiB admission headroom, 2/4 extra device-state slots and shared Host budgets of
15,506,063,360/12,284,837,888 bytes (4090/3090). Strict checkpoint origin authentication remains
mandatory. Native stores use each immutable instance's own `session-checkpoints-v3`; keep older
roots untouched and replay authoritative OMP transcripts rather than importing generations.
The container retains its separate `/checkpoints-v013` mount. No cross-binary checkpoint migration
or compatible old-generation restore is inferred merely from keeping a deployment-profile name.
Windows NTFS `ntfs-write-through` is not POSIX `fsync` or a power-loss guarantee.

Within one API-key principal, prompt_cache_key names a session capability; use unique high-entropy
keys and do not share the principal among mutually untrusted clients. MACs authenticate origin
and content, not monotonic freshness. Saves are best effort and can lose unpublished state.
Native GPUs serve sequentially; no multi-GPU inference, simultaneous supported native serving,
new native vision/DFlash2, smaller-host support, universal warm reuse, multi-tenancy or silent
cloud fallback is claimed. macOS remains preview; Linux client evidence is WSL2-scoped.

## Upgrade and known issues

**RTX 3090 upgrade from v0.13.1: stop the running RTX 3090 lane before installing v0.14.0.**
A running v0.13.1 lane holds a 300 W GPU-owner lease. The v0.14.0 installer checks it against
the new 350 W cap and refuses before replacing it; the old lane keeps running unchanged.
A stopped lane upgrades normally. Tracked in
[#94](https://github.com/alphastorm/omp-ninfer/issues/94).

## Remaining gates and follow-ups

Fresh candidate-bound external-install acceptance (all five routes, three stock clients and both
native public installs), the product-tooling council, composed review/evidence pins and
founder-owned product publication remain separate. The current fork council closed with no
P0/P1; its binding waits for composition with the product-tooling council. Changed guide blocks require
`documented_routes.document_change`; the published QUICKSTART is not advanced by this stage.

Carried deferrals [#88](https://github.com/alphastorm/omp-ninfer/issues/88) and
[#89](https://github.com/alphastorm/omp-ninfer/issues/89) are still open when this stage is written.
The #88 tracked 5090-specific off-lock export/admission reproduction is not established by this
release's aggregate gates. #89 tracks installer failed-stop rollback/cleanup and checkpoint I/O
classification/stale-generation issues; the native qualification chain is not closure of every
fault-injection item. New deferred follow-ups are
[#95](https://github.com/alphastorm/omp-ninfer/issues/95) (retire engine state before delivering
error/cancel responses) and [#96](https://github.com/alphastorm/omp-ninfer/issues/96) (media decode
range checks). No issue closure or inherited council approval is claimed. Deterministic 5090
module IDs and a corrected, repeated native A8 screen are explicit follow-ups.
