# Contributing

[Oh My Pi](https://github.com/can1357/oh-my-pi) (coding-agent client) → OMP NInfer (qualified
appliance and release layer) → NInfer (inference engine) → Qwen3.8 27B (served model). Qualified on
RTX 5090 · 4090 · 3090. Installation reports, reproducible integration defects, documentation
corrections, benchmark submissions, kernel work through the
[performance program](docs/PERFORMANCE.md), and release-contract fixes are welcome. Generic model
or runtime expansion and speculative abstractions are out of scope.

<a id="help-close-a-real-gate"></a>
## Ways to help

- **Want to run an RTX 5090, RTX 4090, or RTX 3090 [lane](docs/FACTS.md#glossary)?**
  [Get started](docs/QUICKSTART.md) with the published lane, then file the matching
  [hardware qualification report](https://github.com/alphastorm/omp-ninfer/issues/new?template=hardware-report.yml),
  [performance result form](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml),
  or [clean-install report](https://github.com/alphastorm/omp-ninfer/issues/new?template=clean-install-report.yml).
- **Own a qualified card and a published package?** Run a clean install and report
  [time-to-first-turn plus every manual step](https://github.com/alphastorm/omp-ninfer/issues/new?template=clean-install-report.yml).
- **Own an RTX 3090?** The qualified release package is public; independent redacted
  [hardware reports](https://github.com/alphastorm/omp-ninfer/issues/new?template=hardware-report.yml)
  test transferability across owner machines.
- **Work on CUDA kernels?** Pick a measured bottleneck from the
  [performance program](docs/PERFORMANCE.md), then submit before/after receipts for the affected
  end-to-end workload with the
  [performance result form](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml).
- **Need a different model or profile?** Use the
  [model/profile request](https://github.com/alphastorm/omp-ninfer/issues/new?template=model-profile-request.yml)
  so a derivative cannot silently inherit the official artifact identity or qualification.

Every public form forbids keys, private identifiers and paths, prompts, source code, model output,
raw logs, and session data unless a reporter deliberately publishes redacted content they own.
Security reports stay private ([`SECURITY.md`](SECURITY.md)).

## Route the change to its owner

- Product manifest, profile, setup, qualification composition, benchmarks/leaderboard, and support
  docs: `alphastorm/omp-ninfer` (this repository).
- NInfer engine/server, CUDA kernels, numerical behavior, or container:
  [`alphastorm/ninfer`](https://github.com/alphastorm/ninfer) (downstream of
  [Neroued/ninfer](https://github.com/Neroued/ninfer); kernel/perf work starts at
  [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md)).
- Oh My Pi (OMP) session/tool/provider semantics: upstream
  [Oh My Pi](https://github.com/can1357/oh-my-pi). OMP NInfer pins unmodified upstream release
  binaries by SHA-256 and carries no client fork.
- Native Windows RTX 4090 and RTX 3090 runtime components:
  [`alphastorm/ninfer`](https://github.com/alphastorm/ninfer) (upstream port lineage:
  [UDPSendToFailed/ninfer-4090](https://github.com/UDPSendToFailed/ninfer-4090),
  [Don-Chad/ninfer-3090](https://github.com/Don-Chad/ninfer-3090)).

Do not duplicate implementation across repositories to make a local patch easier.

<a id="performance-submissions"></a>
<a id="performance-contributions"></a>
## Performance work

- **Benchmark submissions:** use the
  [performance result form](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml)
  with redacted values and the measurement method. Entries land in the
  [community results table](docs/BENCHMARKS.md#community-results) after their release identities
  check out.
- **Kernel and runtime changes:** read [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md) for the
  measured baseline, [profiling lane](docs/PERFORMANCE.md#the-profiling-lane),
  [experiment ledger](docs/PERFORMANCE.md#experiment-ledger),
  [ideas backlog](docs/PERFORMANCE.md#ideas-backlog), and
  [submission rules](docs/PERFORMANCE.md#contributing-a-result). Claim a `perf: <idea>` issue in
  [`alphastorm/ninfer`](https://github.com/alphastorm/ninfer) before writing code, and submit
  results with preserved profiling packets and oracle tests.

## Where each fact lives

| Fact class | Owner |
| --- | --- |
| Current release identities and lane limits | [`docs/FACTS.md`](docs/FACTS.md) |
| Measured results and method | [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md) |
| Install steps | [`docs/QUICKSTART.md`](docs/QUICKSTART.md) |
| Upgrade steps, release procedure, and release records | [`docs/RELEASES.md`](docs/RELEASES.md) |
| Failure recovery | [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) |
| Security boundary (reporting policy: [`SECURITY.md`](SECURITY.md)) | [`docs/SECURITY.md`](docs/SECURITY.md) |
| Experiments and kernel backlog | [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md) |
| Upstream positions | [`docs/UPSTREAM.md`](docs/UPSTREAM.md) |
| Open work and decisions | [`ROADMAP.md`](ROADMAP.md) |

- Link to the owner instead of restating a fact on another page.
- A heading's anchor is an interface; keep `<a id="old-slug"></a>` above any renamed heading.
- Text below a `## Records` heading is append-only; add new records without editing old ones.
- Never edit `docs/QUICKSTART.md`, `docs/COMPATIBILITY.md`, `releases/`, or `docs/measurements/` by
  hand (updated via the [release procedure](docs/RELEASES.md#how-a-release-is-cut)).
- Reference pages (`CONTRIBUTING.md`, `SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md`,
  `docs/DECISION_GUIDE.md`, `docs/RELATED_WORK.md`, `docs/TROUBLESHOOTING.md`, and
  `examples/fleet/README.md`) name no current release, client version, or component tag;
  `tests/test_docs.py` checks anchors and release-neutral pages.

## Before opening a pull request

1. Base the change on `main`.
2. Keep release/profile identities exact; do not replace hashes with mutable tags or sample values.
3. Remove API keys, credentials, prompts, outputs, raw request logs, private paths, hostnames, IPs,
   and workstation-specific receipts.
4. Add or update a test only when it protects an observable release contract.
5. Record user-visible changes under `[Unreleased]` in `CHANGELOG.md` using
   [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).
6. Run:

   ```sh
   python3 scripts/verify_release.py
   python3 scripts/run_tests.py
   bash -n examples/manual-tunnel/*.sh
   ```

The test runner defaults to one worker per CPU. Modules measured above 60 seconds are split
into isolated chunks of sorted test ids; class and module fixtures run once per chunk. Use
`--jobs N` to cap concurrency, `--shard I/N` for one duration-balanced shard, or `--durations K`
to change the chunk and module-total timing summaries. `--list` shows chunks and estimated
seconds; `--list-tests` shows their exact test ids. On native Windows, run
`python scripts/run_tests.py --windows-skips` to use the same fixture exclusions as CI; Linux
and macOS still run those POSIX fixtures.

A draft manifest is expected to pass the first command and fail `--require-ready`. A release-cut
pull request ([how a release is cut](docs/RELEASES.md#how-a-release-is-cut)) must make
`python3 scripts/verify_release.py --require-ready` pass with real published identities and a
recorded external-install result.

Use Conventional Commits 1.0.0 subjects (`type(scope): lowercase imperative description`). Keep
release notes human-readable; the changelog is not a commit dump.

## Support reports

Use the issue forms, including the
[installation-failure form](https://github.com/alphastorm/omp-ninfer/issues/new?template=installation-failure.yml),
rather than attaching raw log archives. Include the observed OS, GPU, driver, runtime state, and
failing step; see [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md#reporting-safely) for safe
fields.

## Security

Report vulnerabilities through [`SECURITY.md`](SECURITY.md), never a public issue.
