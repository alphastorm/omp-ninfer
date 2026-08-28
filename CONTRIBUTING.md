# Contributing

OMP NInfer is in narrow invited early access. High-signal installation reports, reproducible
integration defects, documentation corrections, benchmark submissions, performance work through the
[performance program](docs/PERFORMANCE.md), and release-contract fixes are useful. Generic
model/runtime expansion and speculative abstractions are not current goals.

## Route the change to its owner

- Product manifest, profile, setup, qualification composition, benchmarks/leaderboard, and support
  docs: this repository.
- NInfer engine/server, CUDA kernels, numerical behavior, or container: `alphastorm/ninfer`
  (downstream of [Neroued/ninfer](https://github.com/Neroued/ninfer); kernel/perf work starts at
  [docs/PERFORMANCE.md](docs/PERFORMANCE.md)).
- OMP session/tool/provider semantics: upstream
  [Oh My Pi](https://github.com/can1357/oh-my-pi) where the change is general; the beta client
  fork only carries the NInfer integration until those parts are upstreamed.
- RTX 4090 runtime: `alphastorm/ninfer-4090`; it is not part of the first product release.
- Homebrew cask behavior: `alphastorm/homebrew-omp`.

Do not duplicate implementation across repositories to make a local patch easier.

## Benchmark submissions

Use the
[benchmark report form](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml).
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
