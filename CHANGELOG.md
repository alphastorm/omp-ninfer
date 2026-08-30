# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

[Unreleased]: https://github.com/alphastorm/omp-ninfer/compare/v0.2.0-beta.1...HEAD
[0.2.0-beta.1]: https://github.com/alphastorm/omp-ninfer/compare/v0.1.0-beta.1...v0.2.0-beta.1
[0.1.0-beta.1]: https://github.com/alphastorm/omp-ninfer/releases/tag/v0.1.0-beta.1
