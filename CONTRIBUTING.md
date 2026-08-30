# Contributing

OMP NInfer has a public release for three exact qualified GPU lanes. High-signal installation
reports, reproducible integration defects, documentation corrections, benchmark submissions,
performance work through the
[performance program](docs/PERFORMANCE.md), and release-contract fixes are useful. Generic
model/runtime expansion and speculative abstractions are not current goals.

## Help close a real gate

- **Want to run an RTX 5090, 4090, or 3090 lane?**
  [`Get started`](docs/QUICKSTART.md) with the exact published lane, then use the
  [hardware qualification report](https://github.com/alphastorm/omp-ninfer/issues/new?template=hardware-report.yml),
  [performance result form](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml),
  or [clean-install report](https://github.com/alphastorm/omp-ninfer/issues/new?template=clean-install-report.yml)
  that matches the observation.
- **Own a qualified card and a published package?** Run a clean install and report
  [time-to-first-turn plus every manual step](https://github.com/alphastorm/omp-ninfer/issues/new?template=clean-install-report.yml).
- **Own an RTX 3090?** The qualified release package is public; independent content-safe hardware
  reports now test transferability rather than closing a missing maintainer-hardware gate.
- **Work on CUDA kernels?** Pick a measured bottleneck from the
  [performance program](docs/PERFORMANCE.md), then submit before/after receipts for the affected
  end-to-end workload with the
  [performance result form](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml).
- **Need a different model/profile?** Use the
  [model/profile request](https://github.com/alphastorm/omp-ninfer/issues/new?template=model-profile-request.yml)
  so a derivative cannot silently inherit the official artifact identity or qualification.

Every public form forbids keys, private identifiers and paths, prompts, source code, model output,
raw logs, and session data unless a reporter deliberately publishes content they own after
redaction. Security reports always stay private.

## Route the change to its owner

- Product manifest, profile, setup, qualification composition, benchmarks/leaderboard, and support
  docs: this repository.
- NInfer engine/server, CUDA kernels, numerical behavior, or container: `alphastorm/ninfer`
  (downstream of [Neroued/ninfer](https://github.com/Neroued/ninfer); kernel/perf work starts at
  [docs/PERFORMANCE.md](docs/PERFORMANCE.md)).
- OMP session/tool/provider semantics: upstream
  [Oh My Pi](https://github.com/can1357/oh-my-pi) where the change is general; the pinned client
  fork only carries the NInfer integration until those parts are upstreamed.
- Native RTX 4090 and RTX 3090 runtime variants: their reviewed branches in `alphastorm/ninfer`
  (upstream ports: [UDPSendToFailed/ninfer-4090](https://github.com/UDPSendToFailed/ninfer-4090),
  [Don-Chad/ninfer-3090](https://github.com/Don-Chad/ninfer-3090)).
- Homebrew cask behavior: `alphastorm/homebrew-omp`.

Do not duplicate implementation across repositories to make a local patch easier.

## Performance submissions

Use the
[performance result form](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml).
Entries land in the [community results table](docs/BENCHMARKS.md#community-results) after the
release identities check out. Content-safe values only; the measurement method is part of the
submission.

## Performance contributions

Read [docs/PERFORMANCE.md](docs/PERFORMANCE.md) first: it holds the measured baseline, the scripted
profiling lane, the experiment ledger (including rejected attempts, so you do not repeat them), and
the open ideas backlog. Claim an idea with a `perf: <idea>` issue in the runtime repository before
writing code; land results with preserved profiling packets and oracle tests.

## Before opening a pull request

1. Base the change on current `main`.
2. Keep release/profile identities exact; do not replace hashes with mutable tags or sample values.
3. Remove API keys, credentials, prompts, outputs, raw request logs, private paths, hostnames, IPs,
   and workstation-specific receipts.
4. Add or update a test only when it protects an observable release contract.
5. Record user-visible changes under `[Unreleased]` in `CHANGELOG.md` using
   [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).
6. Run:

   ```sh
   python3 scripts/verify_release.py
   python3 -m unittest discover -s tests -v
   bash -n examples/manual-tunnel/*.sh
   ```

A draft manifest is expected to pass the first command and fail `--require-ready`. A release-cut pull
request must make `python3 scripts/verify_release.py --require-ready` pass with real published
identities and a recorded external-install result.

Use Conventional Commits 1.0.0 subjects (`type(scope): lowercase imperative description`). Keep
release notes human-readable; the changelog is not a commit dump.

## Support reports

Use the issue forms rather than attaching raw bundles. Hardware diversity is useful only when the
observed OS/GPU/driver/runtime state and failing transition are clear. See
[`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) for safe fields.

## Security

Report vulnerabilities through [`SECURITY.md`](SECURITY.md), never a public issue.
