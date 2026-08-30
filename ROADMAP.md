# Roadmap

This roadmap is a scope boundary, not a promise of dates. The current product wedge is OMP plus
NInfer plus Qwen3.8 on user-controlled RTX cards: qualified RTX 5090 and RTX 4090 lanes and a
qualified RTX 3090 candidate, each bound to exact bytes and a receipt. The published v0.2 manifest
still exposes the 3090 as a non-installable preview. Work outside that wedge needs
a new product decision rather than placeholder abstractions.

Want to move something here? The fastest ways to help are listed at the end of this page and in
[`CONTRIBUTING.md`](CONTRIBUTING.md); performance work has its own program page at
[`docs/PERFORMANCE.md`](docs/PERFORMANCE.md).

## v0.1.0-beta.1 — invited RTX 5090 early access (shipped)

The first release is out. Its ready manifest binds the native Windows OMP client, the digest-pinned
NInfer image and SBOM, the hash-pinned Qwen3.8 artifact, the RTX 5090 profile, the qualification
summary, and an owner-operated tester-equivalent clean install from public URLs
([receipts](releases/v0.1.0-beta.1/qualification.json)).

An invited tester starting from the published artifacts, without access to a developer workstation,
can:

1. verify the exact release contract (`python3 scripts/verify_release.py --require-ready`);
2. install the checksummed OMP client on native Windows (macOS/Linux are preview profiles);
3. start the exact NInfer image and Qwen3.8 artifact on a Docker Desktop WSL2 RTX 5090 host;
4. configure OMP's exact `openai-responses` provider with cloud fallback disabled; and
5. complete the text/tool, Vision, stateful follow-up, OMP exit/resume, and fail-closed checks,
   then file a redacted hardware or installation report.

### Explicit non-claims (still true after shipping)

- no `omp appliance install` remote lifecycle;
- no managed upgrade or appliance-level rollback;
- no automatic restart of the NInfer container;
- no NInfer process-restart continuation claim;
- no RTX 4090 or RTX 3090 support claim;
- no multi-GPU, multi-tenant, priority, or preemptive scheduling;
- no universal throughput, latency, or hardware claim;
- no silent cloud fallback; and
- no general-availability support commitment.

## v0.2.0-beta.1 — managed lifecycle and three GPU release lanes

The second invited-tester release closes the v0.2 roadmap:

- native OMP 18.0.9 clients for macOS arm64, Windows x64, and Linux x64, with the exact accepted
  source published at [`alphastorm/oh-my-pi`](https://github.com/alphastorm/oh-my-pi);
- manifest-driven `doctor`, `plan`, `install`, `status`, `benchmark --quick`, checkpoint,
  `rollback`, and `support-bundle` through the closed cross-platform appliance adapters;
- durable NInfer process-restart continuation on the native RTX 4090 variant, with authenticated
  session ownership and bounded checkpoint stores; RTX 3090 transaction tests pass but its current
  live restart gate remains `not_run`;
- state-faithful clean install, already-installed, interrupted-install repair, upgrade, and
  rollback coverage from representative predecessor state;
- the refreshed RTX 5090 BF16-KV/MTP3 runtime plus documentation-strengthening prefill and decode
  measurements;
- a beta-qualified native Windows RTX 4090 runtime plus a review-closed, non-installable RTX 3090
  preview whose live-model and fresh Windows package lifecycle gates were `not_run` at the
  v0.2 release cut while the validation rig was offline; and
- one product compatibility authority binding the three OMP clients, Homebrew cask, primary RTX
  5090 image, qualified RTX 4090 variant, and RTX 3090 preview.

The RTX 4090 gate uses a committed synthetic OMP Golden-equivalent because the historical private
corpus is unavailable. It was not reused, read, copied, hashed, or transmitted. The replacement
requires one typed tool call with exact primitive arguments, linked tool-result continuation, and an
exact visible final answer.

### v0.2 support boundaries

- prerelease/invited-tester support only; no stable or GA promotion;
- one active request per qualified product profile;
- JSON-schema structured output is unsupported and rejected;
- the RTX 3090 unattended evidence-role corpus did not pass, so that automatic route stays disabled;
- the RTX 3090 thermal claim is GPU-only at 300 W; CPU-heavy, mixed-load, and overnight behavior is
  outside the gate;
- no multi-GPU, multi-tenant, priority, or preemptive scheduling claim;
- no two-machine throughput claim from fleet routing; and
- no silent cloud fallback or production-route activation.

## v0.2.1-beta.1 candidate — RTX 3090 parity

The validation rig returned and the native RTX 3090 candidate now matches the expensive gates used
for the other qualified lanes:

- path-neutral `sm_86` Windows binaries and a deterministic, private-path-clean package;
- 15/15 authenticated protocol checks and exact 64,512-token retrieval;
- durable process replacement with disk-backed continuation and checkpoint deletion regressions;
- clean install, managed upgrade, bidirectional rollback, protected-state ACLs, and exact OMP
  read-tool acceptance; and
- managed C1 measurement at 90.17 decode tok/s, 893.41 prefill tok/s, 93.43% MTP3 acceptance,
  21,159 MiB peak VRAM, and 299.8 W peak power.

The [candidate receipt](docs/measurements/2026-08-30-rtx3090-parity.json) binds package
`e7642d7069e85de497731735bde92a0c9b23f5b486848ab8cbe5c4da222baf97`. It does not
change the immutable `v0.2.0-beta.1` manifest, activate an unattended route, or perform a stable
promotion. The next product release must publish that exact package or requalify changed bytes.

## v0.3 candidates

The next expensive-to-add-later items are now explicit rather than hidden release debt:

- adopt the shared native-Windows source-first qualification sequence in
  [the release process](docs/RELEASES.md#next-native-release-sequencing);
- notarized macOS distribution and a first-party Windows signing path;
- a public, hardware-independent acceptance runner shared by all client releases;
- JSON-schema constrained decoding only if the runtime can enforce rather than ignore the contract;
- concurrency-qualified 3090/4090 profiles after memory and latency gates exist for those exact
  packages;
- a dependency-level SBOM for the 4090 package beyond its complete file inventory;
- a doctor-level WSL networking-mode and loopback-reachability preflight for the Windows Docker
  profiles ([#15](https://github.com/alphastorm/omp-ninfer/issues/15)); and
- a fixed two-machine workload before any fleet completed-work or throughput claim.

## Upstreaming to Oh My Pi

The beta OMP client carries the NInfer stateful-Responses provider integration; running a fork was
the fastest way to ship one exact qualified combination. The exact accepted source is now public at
[alphastorm/oh-my-pi](https://github.com/alphastorm/oh-my-pi). The standing intent remains to
upstream the reusable provider semantics, stateful transaction, and appliance plumbing to
[can1357/oh-my-pi](https://github.com/can1357/oh-my-pi).

## Continuous — performance program

Kernel and schedule optimization runs alongside releases, in public, with an auditable experiment
ledger and an open ideas backlog: [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md). Candidate areas
include prefill, decode, MTP acceptance and verification cost, Vision, KV storage, weight paging,
and long-session continuation. No optimization result becomes part of a release until its exact
binary and profile are rebound through a new qualification receipt.

## Broad public release gate

Before marketing beyond invited testers:

- gather clean-install and rollback evidence from multiple independent owners for each claimed GPU
  profile;
- sign the Windows packages and notarize the macOS client, or retain the explicit unsigned beta
  boundary;
- close the highest-signal early-access installation and compatibility failures;
- define response times, supported upgrade windows, and rollback ownership for a broad support
  commitment;
- run a fixed two-machine workload before making any fleet completed-work claim; and
- cut a new release candidate if any executable component, model, configuration, or support
  boundary changes.

## How to help right now

- **Own an RTX 5090 and use OMP?** Run the quickstart and file a
  [hardware report](https://github.com/alphastorm/omp-ninfer/issues/new/choose) — pass or fail,
  both move the matrix.
- **Measured something?** Submit the
  [performance result form](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml)
  for the [community results table](docs/BENCHMARKS.md#community-results).
- **CUDA/kernel work?** Claim an idea from the
  [performance backlog](docs/PERFORMANCE.md#ideas-backlog).
- **RTX 3090, 4090, or 5090 owner?**
  [Request early access](https://github.com/alphastorm/omp-ninfer/issues/new?template=early-access.yml),
  run the matching published boundary, and file a content-safe report. Pass and fail reports both
  improve the observed matrix; candidate qualification never authorizes package substitution.
