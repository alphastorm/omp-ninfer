# Contributing

OMP NInfer is in narrow invited early access. High-signal installation reports, reproducible
integration defects, documentation corrections, and release-contract fixes are useful. Generic
model/runtime expansion and speculative abstractions are not current goals.

## Route the change to its owner

- Product manifest, profile, setup, qualification composition, and support docs: this repository.
- NInfer engine/server, CUDA kernels, numerical behavior, or container: `alphastorm/ninfer`.
- OMP session/tool/provider semantics: the applicable OMP repository or upstream Oh My Pi.
- RTX 4090 runtime: `alphastorm/ninfer-4090`; it is not part of the first product release.
- Homebrew cask behavior: `alphastorm/homebrew-omp`.

Do not duplicate implementation across repositories to make a local patch easier.

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
