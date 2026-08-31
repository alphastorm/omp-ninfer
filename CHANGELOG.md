# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.4] - 2026-08-31

### Changed

- Checkpoint export no longer blocks the engine: exporter writes flow through a bounded
  in-memory queue (`--session-checkpoint-write-buffer-mib`, default 6144) drained to disk off
  the engine execution lock, with a deferred write failure still failing the save before
  anything publishes. Warm follow-up during checkpoint traffic 15.26 s → **0.91 s**, explicit
  save 31.6 s → **13.8 s**, and all four sibling fanout branches at **0.90-1.01 s** with
  automatic saves enabled at defaults
  ([acceptance receipt](docs/measurements/2026-08-31-fanout-probe-v044c.json),
  [ninfer#34](https://github.com/alphastorm/ninfer/issues/34)).
- Automatic checkpoint saves yield to live traffic: they start only after the engine stays
  quiet for consecutive samples (bounded at 60 s) and skip entirely when the catalogued
  checkpoint already covers the session's newest stored response. Explicit `POST` saves keep
  their synchronous crash-test contract.

### Fixed

- Lazy restore repairs partially resident sessions: restoring a checkpoint replaces the
  target session's complete stored lineage (partial overlap repaired, stale records removed)
  while any cross-session ID collision still fails closed, and restoring onto an exact live
  endpoint is an idempotent no-op instead of a refusal.

## [0.4.3] - 2026-08-31

### Added

- Same-lane agent fanout on the RTX 5090 container: sibling branches of one
  `previous_response_id` reuse the base prefill through private long anchors instead of
  replaying it from scratch. Measured at a 67.7K-token base: four branches 148.7 s → 47.9 s,
  and 0.40 s to first token when the anchor is still device-resident
  ([probe receipt](docs/measurements/2026-08-31-fanout-probe-v043.json), with the
  [v0.4.1 baseline](docs/measurements/2026-08-31-fanout-probe-v041-baseline.json) and a
  [device-state-slots null result](docs/measurements/2026-08-31-fanout-probe-v043-slots4.json)
  pinning the remaining sibling KV-clone ceiling,
  [ninfer#34](https://github.com/alphastorm/ninfer/issues/34)).
- Checkpoint refusal diagnostics carry the attempted response id in manual and automatic
  refusal log lines, populated without allocation on the refusal path.

### Fixed

- Private continuations never cross sessions: the session-isolation set proven on the 4090
  durable train (preserve private session ownership, isolate private cache sessions, harden
  session publication invariants) now ships on the 5090 lane, where the agent-protocol smoke
  exposed the latent cross-session private reuse.
- Anchored continuations no longer fail their first turn or restart restore: continuation
  summaries self-reserve anchor backing at the single populate chokepoint.
- Streaming UTF-8 repair and explicit invalid media-enum rejection (upstream parity picks).

### Security

- Checkpoint imports are bound to their load-time digests end to end: the reader re-hashes
  every streamed chunk with strict front-to-back single-pass coverage and fails closed, the
  `responses.cbor` reopen is digest-gated, and a divergence marks the generation corrupt so
  status stops advertising it and the next load quarantines it (closes
  [ninfer#21](https://github.com/alphastorm/ninfer/issues/21)).
- Checkpoint export writes refuse symlinks and reparse points and verify every staging
  directory component is a real directory, so a checkpoint-root writer cannot redirect
  server-authority writes (council CR-20260831-fanout43).
- Bearer, `x-api-key`, and stored-response session-ownership comparisons are constant-time
  digest-then-compare (closes [ninfer#22](https://github.com/alphastorm/ninfer/issues/22)).
- Checkpoint export copies are explicitly fenced behind in-flight compute-stream work via a
  recorded CUDA event (closes [ninfer#24](https://github.com/alphastorm/ninfer/issues/24)).

## [0.4.2] - 2026-08-31

### Added

- The RTX 4090 native Windows lane moves to the durable v0.2 package
  (`alphastorm/ninfer@v0.2.0-qwen38-4090-durable.1`): v0.4.1 checkpoint-store hardening on the
  native lineage, chunked KV snapshot restore with a fail-closed cross-layout guard, hardened
  D3D12 residency verification, WDDM evictable-budget CLI opt-in, streaming UTF-8 repair, and
  MTP K=15 draft capacity (shipped arm remains MTP3 per the width ablation).
- 4090 requalification receipts: protocol, 102,060-token seeded session, post-restart
  persistence restoring 102,075 tokens on a fresh process, OMP golden equivalence.
- Fleet measurements: RTX 3090 power sweep (350 W knee, +5.9% decode over the 300 W baseline;
  host PCIe link documented as gen3 x8) and the MTP draft-width ablation.

### Fixed

- The pinned OMP 18.0.9 client now completes cold-start sessions on the RTX 4090 lane: the
  native serve emits the full concrete status telemetry hierarchy (ninfer#28), with a
  regression mirroring the client validator field-for-field.

### Security

- Cross-family council review (CR-20260831-durable4090) at source freeze, before the Windows
  build: the convergent D3D12 probe-teardown P1 and a post-publish reclamation gap were
  remediated with regressions; upstream's global fast-math device flags were rejected to
  preserve the lane's numeric contract.

## [0.4.1] - 2026-08-31

### Fixed

- Post-publish checkpoint reclamation can no longer fail an acknowledged save: once the
  current pointer durably swaps, cleanup trouble is absorbed, the pass is marked unhealthy,
  and the next save refuses fail-closed until reclamation recovers (council
  CR-20260831-v041delta, convergent P1, remediated in alphastorm/ninfer#30 with a
  regression covering outage -> acknowledged save -> refusal -> recovery).
- A throwing tombstone-cleanup hook now degrades to an unhealthy reclamation pass instead of
  propagating; refusing an invalid engine stats export names `ProgramRejected` instead of
  leaving the skip reason empty.

### Added

- Health-gated publish transient tolerance (alphastorm/ninfer#27): a session whose checkpoint
  exceeds half the disk quota can still save its successor; the superseded generation is
  reclaimed under quota pressure only while every attempted reclamation succeeds.
- Named checkpoint skip reasons with response-id-correlated server logs
  (alphastorm/ninfer#26); HTTP refusal bodies keep the released closed vocabulary.
- v0.4.1 requalification on the owner appliance: explicit 316.8 MB checkpoint restored warm
  after `docker restart` (`reuse=private_endpoint`, 1.52 s), fork/delete arc with no
  resurrection through the reworked reclamation layer, decode 134.8 tok/s at temperature 0.

### Changed

- Release bytes were built in the pinned CI container on the owner appliance after three
  RunPod SECURE ssh-allocation failures; the route is documented in the component-release
  receipt and the build profile is stamped `appliance-local`.

## [0.4.0] - 2026-08-30

### Added

- Durable session checkpoints on the RTX 5090 container lane: transactional generational store
  (fsync-disciplined, corruption-quarantining, quota-evicting), automatic checkpoint queue, native
  io_uring O_DIRECT restore backend under a sha-pinned seccomp profile, and authenticated
  `/v1/ninfer/checkpoints` endpoints speaking the released 18.0.9 client's path addressing.
  Qualified live: automatic 7.95 GB checkpoint at a 109,725-token frontier; docker-restart
  continuation restored **109,589 tokens hot** on a rotated server instance (0.778 s serve-side
  first token); exact retrieval at 130,448 tokens; decode 143.0-144.8 tok/s.
- Durability now ships on **all three GPU lanes** - the RTX 5090 container joins the native
  Windows 4090/3090 DirectStorage lanes.
- Serve startup re-hashes the model artifact against its declared identity and refuses mismatch;
  lifecycle tooling is loopback-only; cross-family review CR-20260830 dispositions land with the
  candidate (9 mitigations, receipts in the component release).
- `examples/fleet/`: one provider fragment per qualified lane plus a role mapping for running
  three model-bound agents against the fleet.

### Changed

- The RTX 5090 container image moves to
  `ghcr.io/alphastorm/ninfer-runtime@sha256:8de5efdf...` (source `1ceaeebd`, binary `7eb66643`);
  the previous digest remains published as the rollback target.

## [0.3.2] - 2026-08-30

### Fixed

- Corrected the RTX 4090 qualification summary: the v0.3.1 copy carried its v0.2 template's
  limitations ("MTP0 qualified", "MTP3 performance not claimed") in direct contradiction of the
  MTP3 receipts it fronts, plus a stale beta classification. No component bytes, receipts, or
  measured numbers changed; v0.3.1 remains immutable with this defect on record.

## [0.3.1] - 2026-08-30

### Added

- Qualified MTP3 speculative profile on the RTX 4090 native Windows lane: identical released
  binary and model bytes with only the speculative configuration changed, promoted by the
  recorded two-arm MTP0-versus-MTP3 decision (+17.04% complete Golden-equivalent wall time;
  decode 93.2–97.7 tok/s vs the 52.330 tok/s MTP0 baseline; 107,851-token restored continuation
  with server-instance rotation).
- Exploratory draft-depth sweep (4 and 5 measured slower than 3 on the fixed decode workload),
  recorded as the first datapoint for the MTP depth-and-corpus ablation.
- Deterministic MTP3 arm package (+4 bytes over the baseline zip) with finalized qualification
  sidecar, SBOM, and SHA256SUMS published as a component release.

### Fixed

- Disclosed and patched two latent defects in the published qualification tooling (PowerShell 5.1
  serializer incompatibility; post-restart restore gate expecting a lazy restore label while the
  released engine restores checkpoints eagerly); the patched gate is strictly stronger, proving
  server-instance rotation plus at-least-100,000-token restoration.

## [0.3.0] - 2026-08-30

### Added
- Fresh RTX 5090 qualification on the identical published runtime bytes: 240.30 tok/s decode
  (MTP3, 99.87% acceptance), a 3,193.77-through-2,199.41 tok/s exact-retrieval prefill curve to
  130,048 tokens, a qualification-bound warm/cold pair (0.191 s vs 36.651 s at an 89,022-token
  session), and an in-process deletion/no-resurrection probe.
- Public-URL external installation acceptance for the RTX 3090 lane: verified download set,
  exact-bytes installer acceptance, authenticated smoke, and appliance-state restoration
  (GPU lease, scheduled task, endpoint, and power limit; console sign-out disclosed).
- Ready `v0.3.0` manifest binding three qualified GPU lanes, the composed external acceptance,
  and every per-lane receipt; `verify_release.py --require-ready` passes on the tree.

- Hash-bound RTX 3090 `v0.2.1-beta.1` parity candidate: deterministic path-neutral package,
  15/15 protocol checks, exact 64K retrieval, durable restart, bidirectional rollback, protected
  state, exact OMP acceptance, and managed 300 W performance evidence.
- One idempotent, checkpointed RTX 3090 qualification command covering preflight, neutral build,
  disclosure scan, package, install, acceptance, benchmark, receipt, and guaranteed GPU/task restore.
- Public early-access request form and one primary conversion action across first-screen surfaces.
- Launch-safe social MP4, animated GIF fallback, poster, and scoped evidence card with public
  checksums/provenance, plus clean-install and model/profile report forms.
- Launcher fail-fast diagnosis `wsl-mirrored-loopback-unavailable` when the runtime logs a
  loopback listener that the invoking namespace cannot reach, with troubleshooting entries for
  the WSL loopback-drift signature and the non-interactive-SSH Docker credential-helper failure
  ([#15](https://github.com/alphastorm/omp-ninfer/issues/15)).
- Test guards binding the published warm-vs-cold follow-up numbers to their committed receipt and
  covering the launcher's drift preflight.
- Community results row for the qualified native RTX 4090 variant, sourced from its committed
  qualification receipt, and GitHub Discussions linked from the issue chooser.
- Real-session README demo (GIF, MP4, poster) recorded against the exact released v0.2.0-beta.1
  RTX 5090 runtime, with provenance notes under `docs/media/`.
- Labeled maintainer warm-vs-cold follow-up-turn latency measurement on the released runtime.
- Receipt-bound benchmark charts (warm-vs-cold TTFT, RTX 5090 prefill curve, per-lane decode)
  rendered through the deterministic asset pipeline and embedded in the benchmarks page.
- Crisp 2x README demo derivatives (GIF, MP4, poster) rendered directly from the canonical cast
  with a brand-exact terminal palette, replacing the upscaled social fallback in the README.
- RTX 3090 qualified component release `v0.3.0-qwen38-3090.1` publishing the exact parity
  package bytes, source archive, SBOM, lifecycle scripts, and closed checksum set.
- Cross-session eviction hygiene invariant test pinned in the runtime after the v0.3 source
  freeze review; the review ledger dispositions are archived with the release evidence.

### Changed

- Rebuilt the campaign banner, architecture graphic, social preview, and benchmark story around one
  editorial hierarchy; the benchmark asset now leads with the measured warm-continuation outcome.
- Advanced public status copy from two qualified lanes plus a preview to three qualified candidates,
  while keeping the published v0.2 install authority explicit and immutable.
- Led the README and rendered social/benchmark surfaces with the long-session outcome, added a
  pre-command GPU lane chooser, and standardized qualified/preview/invited-beta status grammar.
- Sharpened the README hero around the measured value proposition and explicit lane status, and
  added LM Studio to the runtime comparison and related-work review.
- Replaced the former validation-hardware blocker copy after the returned RTX 3090 rig completed
  the full candidate gate; access copy now distinguishes qualified bytes from published authority.
- Refreshed stale v0.1-era statements in the contributing router, related-work family section,
  roadmap wedge, security policy support table, brand canon, and benchmark issue form.
- Cut every public surface over from invited-tester beta to first-public-release posture:
  BRAND status grammar and primary action, README front door, quickstart lanes, roadmap,
  security support table, contributing router, release channels, issue forms, profiles, and
  launcher pins now describe three qualified GPU lanes with public install authority.
- Promoted the RTX 3090 lane to qualified/installable in the compatibility authority and
  scaffolded the `v0.3.0` draft manifest with explicit publication blockers.

## [0.2.0-beta.1] - 2026-08-29

### Added

- Public, auditable OMP 18.0.9 source and native macOS arm64, Windows x64, and Linux x64 clients,
  each bound to immutable release assets and platform receipts.
- Managed cross-platform appliance lifecycle for exact `doctor`, `plan`, `install`, `status`, quick
  benchmark, durable checkpoint, rollback, and sanitized support receipts.
- Beta-qualified native Windows RTX 4090 support plus a public non-installable RTX 3090 preview;
  each binds exact source, package, SBOM, checksums, scripts, and qualification status.
- Durable process-restart continuation and checkpoint-aware response deletion on the qualified RTX
  4090 runtime; RTX 3090 live-model and Windows-package gates were `not_run` at the release cut.
- RTX 5090 documentation-strengthening prefill curve from 7,680 through 130,048 tokens and a new
  2,048-token decode measurement.

- Benchmarks page with qualified results, upstream campaign attribution, model-quality table,
  community results leaderboard, and a planned-measurements list.
- Public performance program page: measured baseline, scripted profiling lane, auditable
  experiment ledger including rejected attempts, and an open ideas backlog.
- Benchmark-report issue form feeding the community results table.
- Qualified-results stat strip asset for the README and benchmarks page.
- Continuous-integration badge row and measured-value badges bound to the qualified numbers.
- Release-verifier validation of every checked-in hardware profile against the manifest identity,
  transport, server, and provider contract, with a drift test.
- Published RTX 4090 lane qualification receipt (content-safe, prior evidence) linked from the
  performance program and roadmap.

### Changed

- Replaced the unavailable historical RTX 4090 private corpus with a committed synthetic OMP
  Golden-equivalent: typed primitive arguments, linked tool-result continuation, and an exact
  visible final-answer oracle. The historical corpus was not reused.
- Graduated all three native OMP clients from preview after hosted clean-install checks and live
  authenticated read-tool continuation.
- Made the product compatibility authority distinguish OMP client adapters from separately
  qualified native GPU runtime variants.

- Integrated the scripted SM120/MTP3 profiler and its retained experiment packets into NInfer
  mainline together with the latest direct upstream runtime changes.
- Rewrote the README around the product value proposition: stateful GPU-resident sessions,
  fail-closed privacy, verifiable release identity, a runtime comparison table, and the NInfer
  family lineage.
- Credited upstream projects explicitly and in order: Oh My Pi (can1357), NInfer (Neroued), the
  Qwen team, UDPSendToFailed/ninfer-4090, and Don-Chad/ninfer-3090.
- Documented the OMP client as a pinned fork build of Oh My Pi with upstreaming intent and the
  source-publication broad-release gate.
- Reframed the roadmap around shipped v0.1, the managed v0.2 lifecycle, the continuous performance
  program, and concrete ways to help.
- Extended contributing and related-work documentation with benchmark, performance, and NInfer
  family lanes; refreshed the architecture illustration for the Windows-primary topology.

### Security

- Added package/archive contract checks that bind the Homebrew cask to the installer actually
  present in the uploaded client archive, including bounded uninstall behavior.
- Recorded qualification-harness dirty state so an uncommitted runner cannot masquerade as its
  recorded Git commit.
- Made the packaged RTX 5090 build identity authoritative after rejecting one unresolvable source
  field in a benchmark sidecar; the measured binary/model/configuration hashes still match exactly.
- Removed private fleet projections from public qualification artifacts and kept stable promotion,
  production route activation, unattended-role activation, and silent cloud fallback disabled.

## [0.1.0-beta.1] - 2026-08-28

### Added

- Canonical OMP NInfer product repository and naming.
- Ready `v0.1.0-beta.1` manifest binding the native Windows OMP component, NInfer, Qwen3.8,
  the RTX 5090 profile, qualification summary, compatibility authority, and acceptance receipt.
- Ready native Windows quickstart plus managed macOS SSH and native Linux preview routes.
- Digest- and hash-verifying NInfer launcher, owned-container stop path, OMP provider fragment, and
  fail-closed OMP overlay.
- Runtime qualification summary covering exact long context, serving protocols, Vision, stateful
  Responses, cache reuse, Golden behavior, measured decode throughput, and explicit lifecycle
  non-claims.
- Architecture, security, release, troubleshooting, related-work, roadmap, contribution, and support
  documentation.
- Hardware-report and installation-failure issue forms.
- Standard-library release-contract verifier and CI checks, including a truthful
  `draft` → installable `candidate` → externally accepted `ready` transition.
- OMP NInfer brand system with source SVG/HTML, rendered README and architecture artwork, social
  preview, lockups, and icon/favicon variants.
- Deterministic local RTX 5090 binary package, OCI archive, and SPDX SBOM identities, plus a
  state-faithful remote lifecycle rehearsal; publication remains a separate gate.
- Fresh RTX 4090 package/install/restart evidence with an explicit Golden typed-tool-call blocker;
  no RTX 4090 support claim was added.
- Reviewed draft OMP transport for read-only remote `doctor`/`status`, with mutating operations and
  later lifecycle ownership still fail-closed.
- Published and bound the exact OMP, Homebrew, NInfer OCI, binary-package, SPDX, and checksum
  identities; advanced the product manifest through installable candidate to externally accepted
  ready release.
- Owner-operated tester-equivalent Windows clean install from public URLs, including tools, Vision,
  stateful exit/resume, fail-closed outage behavior, and exact runtime restoration.

### Security

- Restricted both NInfer and tunnel listeners to loopback in the supported profile.
- Required a user-only NInfer bearer-key file and disabled OMP model fallback for beta acceptance.
- Required immutable model, binary, image, SBOM, OMP artifact, qualification-summary, and component
  identities before a release can move from `draft` to `ready`.
- Excluded secrets, private host identifiers, prompts, model output, and raw logs from support
  material.

[Unreleased]: https://github.com/alphastorm/omp-ninfer/compare/v0.4.4...HEAD
[0.4.4]: https://github.com/alphastorm/omp-ninfer/compare/v0.4.3...v0.4.4
[0.4.3]: https://github.com/alphastorm/omp-ninfer/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/alphastorm/omp-ninfer/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/alphastorm/omp-ninfer/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/alphastorm/omp-ninfer/compare/v0.3.2...v0.4.0
[0.3.2]: https://github.com/alphastorm/omp-ninfer/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/alphastorm/omp-ninfer/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/alphastorm/omp-ninfer/compare/v0.2.0-beta.1...v0.3.0
[0.2.0-beta.1]: https://github.com/alphastorm/omp-ninfer/compare/v0.1.0-beta.1...v0.2.0-beta.1
[0.1.0-beta.1]: https://github.com/alphastorm/omp-ninfer/releases/tag/v0.1.0-beta.1
