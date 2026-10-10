# OMP NInfer v0.11.0 — Faster decode and unmodified OMP 18.8.7 on the RTX 5090

**Owner-operated, exact-profile 0.x release; RTX 5090 only; no SLA.** The runtime runs
in a Windows 11 Docker Desktop/WSL2 container, reached by authenticated local loopback
or a manual macOS SSH tunnel. This release combines the published NInfer v0.6.16
runtime with unmodified upstream OMP 18.8.7. The supported profile decodes the
2,048-token qualification workload at 179.79 server tok/s, versus 161.39 in v0.10.0
(+11.40%). All three documented RTX 5090 routes and the three stock clients passed.
These are measurements of the recorded machine and profile, not universal GPU claims.

**RTX 3090 and RTX 4090 owners stay on the
[complete v0.10.0 guide](https://github.com/alphastorm/omp-ninfer/blob/v0.10.0/docs/QUICKSTART.md)**,
including its OMP 18.4.10 client, manifest and provider fragments. Neither native lane
is included in v0.11.0. Do not combine current client fragments with legacy native routes.

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Quickstart](../../docs/QUICKSTART.md) · [Security model](../../docs/SECURITY.md) ·
[Known limitations](#support-boundaries)

## What changed

- **Faster RTX 5090 decode.** The selected source includes the attention and Q4
  projection changes measured in EXP-092 and EXP-094, without the pair-Q5 change
  `3a2fadbd`. The model, DFlash2 K=7, BF16 KV and serving limits are unchanged.
  The selected binary has its own qualification and performance measurements.
- **Unmodified OMP 18.8.7.** The release pins the upstream macOS arm64, Windows x64
  and Linux x64 binaries rather than a downstream client build. Platform-specific
  distribution metadata is preserved during release staging and verification.
- **Per-model stateful Responses.** Current provider fragments set
  `compat.statefulResponses: true`. Remove the old `PI_OPENAI_STATEFUL` environment
  override; it still takes precedence over per-model configuration. Compaction,
  provider limits, retry/fallback and sampling settings are otherwise unchanged.
- **Stock image-detail and resume behavior.** Upstream defaults custom Responses
  endpoints to automatic image detail, replacing the RTX 5090 override. An unavailable
  saved model fails closed on resume without an additional configuration setting.
- **Hardened acceptance probe.** Active checks use the numeric nonce `493817-205361`
  while retaining exact continuation/restart comparisons. The diagnostic and the
  failed earlier window remain separate from the accepted route evidence.
- **Narrower release scope.** Native RTX 3090/4090 support is deferred until multi-GPU
  support and fresh native acceptance are qualified. Existing native packages require
  exactly one visible NVIDIA GPU; co-installed GPUs are not supported.

## Exact component identities

The runtime tag is `v0.6.16-qwen38-5090-beta.1`, with source tag
`v0.6.16-qwen38-5090-source.1`. The published image contains the selected server binary;
its OCI digest is not a package-local Docker image ID.

| Component | Committed identity |
| --- | --- |
| Runtime source | `1302d63929e400a05e1c9cdb0fc8003a70269825` |
| Server SHA-256 | `548fe239a3f2f97c98d864b4a7b9c6beb1263788633f1a4bf13c101f2beecace` |
| Published image | `ghcr.io/alphastorm/ninfer-runtime@sha256:6a02feba4163d992cc6a46baf28e0ece2ffe6a2ead91939e566c1b3080f5bc02` |
| Deployment profile | `qwen38-5090-v0.11.0` |
| Configuration SHA-256 | `91a3567002a43025876e811597353764b20e32f0818bcb6c582a5072c96d7e11` |

The model remains the 20,437,336,576-byte Qwen3.8 27B artifact, SHA-256
`0634abb07024221de141456cf04a42ab74b18bc38e1b781c6eb2e062a467eec3`, at public revision
`dc370fb6295ae8b786e1af4f90d7142a16255c35`. The profile has 131,520 BF16 KV tokens,
a 131,072-token context ceiling, two device state slots, two requests in flight and
a 180-second pending timeout. Both prompts plus output reservations must fit the KV pool.

The client is upstream `can1357/oh-my-pi` v18.8.7, source
`f261ed9faf16b61880b544f599876bface4ded0d`, tree
`39226066f2d37044581fe4dbbb2903039d2072b5`. Each raw asset hash is also its binary hash:

| Client platform | Asset / binary SHA-256 |
| --- | --- |
| macOS arm64 | `cf0227bdefca0c486bd2aed1771de3ab98930266883eb69d341caf5665caee14` |
| Windows x64 | `3fee68733791b3d0b2816e8c7b5987813afd103762f8cfd7239d57ed213286dc` |
| Linux x64 | `b87f9835a0acdbb81bbbad8273aa2d999b608a208598421a9584cffeb3139a8a` |

The [runtime publication receipt](qualification/runtime-publication.json),
[build receipt](qualification/option-c-build.json) and
[client descriptor](../../docs/measurements/2026-10-10-omp-1887-client-components.json)
record the package, SBOM, source archive, build environment and upstream asset provenance.

## Measured performance

The exact selected binary was measured on the unchanged supported serving shape.
The v0.10.0 comparison is its recorded qualification workload, not production traffic.

| Qualification workload | v0.10.0 | v0.11.0 |
| --- | ---: | ---: |
| Exact 130,048-token retrieval | 58.738 s | 58.890 s |
| 2,048-token server decode | 161.39 tok/s | 179.79 tok/s |
| 2,048-token completion, wall-clock | 159.92 tok/s | 177.96 tok/s |

Server decode is 11.40% faster; retrieval takes 0.152 s longer. Idle/retrieval VRAM
was 29,468/29,470 MiB. These figures do not establish a traffic-weighted speedup,
faster end-to-end OMP work or an improvement on every workload.
[Selected measurements](qualification/option-c-lane.json) ·
[v0.10.0 profile receipt](../v0.10.0/qualification/rtx5090.json).

Omitting `3a2fadbd` has a measured pair cost **against the superseded `a59c13d0`
alternative**, not against v0.10.0. In one frozen A/B/B/A cycle, mean pair-round time
rose from 19.408 to 21.222 ms (+9.35%), while aggregate paired wall throughput fell
from 505.40 to 462.33 tok/s (−8.52%). The experiment used fresh processes and nonces;
per-round time is the primary comparison, and token rates also depend on acceptance
and output length. It is not a production-traffic or kernel-trace measurement.
The original alternative's blanket pair-speedup prediction does not apply to this source.
[Pair comparison and bounds](qualification/option-c-abba.json).

## Qualification and durability

The selected source passed all 15 local lane criteria. Its full sm_120a ctest run
recorded **111 passed, seven skipped, zero failed** out of 118 tests. The NVFP4
batch/serial oracle and direct supported BF16 checks passed; no failed test was suppressed.
Local numerical/lifecycle qualification and published-component route acceptance are
separate evidence.

The frozen serial role corpus matched the superseded alternative in **89/89 output
signatures and request bodies**. There were 84 counted cases with zero errors per arm;
five preregistered vacuous fixture errors per arm were excluded under the unchanged
screening rule. Signatures include content, reasoning, tool calls, finish reason,
errors and token usage, excluding tool-call IDs. This is not whole-HTTP-response
identity, a new powered quality screen or a solo/pair output-invariance claim.
[Exact-binary quality binding](qualification/option-c-output-identity.json).

| Durability / client gate | Recorded result |
| --- | --- |
| Checkpoint workload | 4/4 stored sessions restored; zero workload errors and first-shutdown refusals |
| Held publication barrier | Exact resume after the six-second barrier; zero shutdown refusals |
| Quota/crash continuation | 60,057 cached tokens retained from 60,079 input tokens; 2.39 s |
| Two-request scenarios | 14/14 scenario runs passed; six restart sessions each retained at least 62,404 cached tokens |
| Multisession control | Reuse lost on 2/8 continuations/forks, within the unchanged limit |
| OMP parallel proof | Limits one and two passed the amended criterion; no recovered dispatch at limit two |
| Server logs | Zero request errors across 13 stages; seven allowed shutdown refusals in the two-request probe, zero elsewhere |

Long-session qualification had two successful runs and one stop at the documented
predecessor harness precondition, with six committed compactions and no computed root
prefill above 60,000 tokens (maximum 58,190). The stopped run configured planting
after three filler turns per epoch; it is not a new successful long-session result.
[Long-session precondition](qualification/option-c-long-session-precondition.json).

Ancillary restored desk-code recall was exact for one session but not the other,
outside the formal durability gate. The original quota monitor named the wrong
container; a separately recorded own-container correction and replay passed. Neither
that invalid attempt nor the interrupted client-bridge run is relabelled as a pass.
[Qualification matrix](qualification/option-c-lane.json) ·
[Numeric evidence](qualification/option-c-lane-evidence.json) ·
[Client proof](qualification/option-c-omp-client.json).

## Documented routes and clients

All **three documented routes, 17 steps** passed on
`5861712f561ff0b3100dd4350e02d777a3f5007e` with the published runtime image and
unmodified OMP 18.8.7. Subsequent prose and metadata changes preserve the executed blocks.

| Route | Passed steps | Receipt |
| --- | ---: | --- |
| RTX 5090 container host | 2/2 | [run](../../docs/measurements/2026-10-10-v0110-rtx5090-container-host-run.json) |
| macOS arm64 client over manual SSH | 10/10 | [run](../../docs/measurements/2026-10-10-v0110-rtx5090-macos-client-run.json) |
| Windows x64 client over local loopback | 5/5 | [run](../../docs/measurements/2026-10-10-v0110-rtx5090-windows-client-run.json) |

The [macOS](acceptance/darwin-arm64-18.8.7.json),
[Windows](acceptance/windows-x64-18.8.7.json) and
[Linux](acceptance/linux-x64-18.8.7.json) clients each passed an authenticated typed
tool turn, exact continuation and an unavailable-route fail-closed request. Vision
passed on the macOS and Windows clients. macOS remains preview without managed client
installation or appliance lifecycle. Linux ran under WSL2, not a separately qualified
non-WSL Linux OS. All observations are owner-operated, not independent external-user outcomes.

The first published-image window failed an exact nonce comparison and restored the
incumbent independently; no accepted platform receipts were promoted from it. A
registered diagnostic then recorded **50/50 exact recalls in each of three cohorts**,
with no material A/B difference. The numeric nonce hardens the probe without widening
its exact comparisons; it does not guarantee deterministic recall or establish a
runtime/client cause for the earlier failure.
[Nonce diagnostic](../../docs/measurements/2026-10-10-omp-acceptance-nonce-diagnostic.json).

The accepted window's independently measured downtime was **385.948 s**, with bounds
**384.444–386.451 s**; the distinct driver hold envelope was 387.738 s. Restoration
checked incumbent health and identity, mounts, port/restart policy, route credentials
and checkout, hold markers, task definitions/enabled states and execution policies.
The container was recreated, not assumed to retain its ID. Production was not upgraded.
[Restoration receipt](../../docs/measurements/2026-10-10-v0110-acceptance-restoration.json).

[Documented-route acceptance](acceptance/documented-routes.json) ·
[Composed installation acceptance](acceptance/composed-external-installation.json) ·
[Original producer evidence](acceptance/rtx5090-acceptance-evidence.json) ·
[Original checksums](acceptance/rtx5090-evidence-checksums.json).

## Upgrading from v0.10.0

Use the exact [v0.11.0 manifest](manifest.json) and
[quickstart](../../docs/QUICKSTART.md) together for a fresh install or RTX 5090 upgrade.

1. Install the pinned v0.6.16 runtime image and `qwen38-5090-v0.11.0` configuration.
   The model is unchanged; retain the matching `0634abb0` artifact. Preserve the
   documented DFlash2 K=7/BF16 profile, two device state slots and serving limits.
2. Install the checksummed upstream OMP 18.8.7 binary for your client platform.
   This release does not use the downstream OMP/Homebrew archive. A generic
   `omp update` is not a substitute for installing the release's pinned bytes.
3. Merge the matching current provider fragments, enable per-model
   `compat.statefulResponses`, remove `PI_OPENAI_STATEFUL`, and remove the old
   RTX 5090 `compat.supportsImageDetailOriginal: false` override.
4. Keep compaction, fail-closed retry/fallback and provider limits unchanged. Upgrade
   the server before increasing concurrency on any older one-at-a-time installation.
   Predecessor checkpoint reuse across the changed runtime is not claimed.

Native RTX 3090/4090 owners must instead use the entire immutable
[v0.10.0 installation path](https://github.com/alphastorm/omp-ninfer/blob/v0.10.0/docs/QUICKSTART.md).
That remains a single-visible-GPU route, not a workaround for a multi-GPU host.

## Support boundaries

- Automatic checkpointing is best effort under live traffic. A crash or an expired
  graceful wait can leave unpublished work unsaved; a passing restart workload does
  not guarantee that every live checkpoint save succeeds.
- Concurrent prefill can delay peer decode. Two requests in flight do not provide
  preemption or universal warm reuse; the multisession control lost reuse on 2/8 turns.
- Serial quality binding does not establish identical solo/pair outputs. The superseded
  alternative and shipped predecessor each had only 1/5 identical signatures in their
  separate BF16 solo/pair controls; that is not a new selected-source control.
- No structured JSON-schema output, multi-GPU, multi-tenant, priority/preemption,
  automatic container restart, silent cloud fallback or support response-time guarantee
  is included. Native-lane or current-upstream experiment results do not expand this scope.
- Measurements apply only to the recorded packages, machine and profile. Historical
  client observations do not qualify OMP 18.8.7 beyond the fresh receipts above.

## Evidence and retained qualification history

Detailed build, selection and failed-attempt records remain available without turning
installation instructions into a release-operation transcript:

- [Source selection](qualification/option-c-source.json) and
  [selection/publication history](qualification/founder-sequence.json).
- [Superseded build](qualification/build.json),
  [NVFP4 source attribution](qualification/nvfp4-source-attribution.json) and
  [original lane qualification](qualification/lane.json); none qualifies the selected source.
- [Quota-monitor attribution](qualification/option-c-criterion8-harness.json) and
  [client-bridge interruption](qualification/option-c-client-bridge-interruption.json).
- [Predecessor solo/pair control](qualification/bf16-solo-pair-shipped.json) and
  [superseded alternative control](qualification/bf16-solo-pair-candidate.json).
- [Staging](qualification/staging.json), [release-tooling qualification](qualification/root-lane-cut.json)
  and [release procedure](../../docs/RELEASES.md).

Public receipts exclude raw prompts, generated content, secrets and private host paths.
Earlier failed windows and deferred native evidence are preserved separately, not
retargeted to the accepted RTX 5090 subject or presented as new passes.
