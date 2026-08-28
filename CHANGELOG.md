# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Benchmarks page with qualified results, upstream campaign attribution, model-quality table,
  community results leaderboard, and a planned-measurements list.
- Public performance program page: measured baseline, scripted profiling lane, auditable
  experiment ledger including rejected attempts, and an open ideas backlog.
- Benchmark-report issue form feeding the community results table.
- Qualified-results stat strip asset for the README and benchmarks page.
- Continuous-integration badge row and measured-value badges bound to the qualified numbers.

### Changed

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

[Unreleased]: https://github.com/alphastorm/omp-ninfer/compare/v0.1.0-beta.1...HEAD
[0.1.0-beta.1]: https://github.com/alphastorm/omp-ninfer/releases/tag/v0.1.0-beta.1
