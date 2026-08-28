# Roadmap

This roadmap is a scope boundary, not a promise of dates. The current product wedge is OMP plus
NInfer plus Qwen3.8 on user-controlled RTX 5090 machines. Work outside that wedge needs a new
product decision rather than placeholder abstractions.

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

## v0.2 — managed appliance lifecycle

The next product release is expected to replace manual setup with the existing `omp appliance ...`
command family after the remote execution boundary is implemented and qualified. Target outcomes:

- transport owned by the appliance platform instead of a manually maintained tunnel;
- manifest-driven `doctor`, `plan`, `install`, `status`, `benchmark --quick`, `rollback`, and
  `support-bundle` against immutable published artifacts;
- exact candidate/incumbent identity and rollback receipts on the remote host;
- OMP exit/resume and, if separately qualified, NInfer process-restart continuation on top of the
  durable-session-checkpoint work in the runtime repositories;
- clean install, already-installed, upgrade, interrupted-install, and rollback acceptance from
  representative predecessor state;
- RTX 4090 beta support only after a fresh package, restart, protocol, long-context, and Golden
  lane passes on the fixed external-model installer;
- RTX 3090 beta support only after a reviewed current-architecture port from
  [`Don-Chad/ninfer-3090`](https://github.com/Don-Chad/ninfer-3090) and the same qualification on
  a representative RTX 3090 host; and
- one manifest authority mechanically checked against OMP's compiled profile registry and the
  Homebrew cask.

Status notes, kept honest:

- The RTX 5090 remote-side install/upgrade/rollback transitions are proven inputs from a
  state-faithful rehearsal, not a shipping managed CLI claim. A reviewed draft owns bounded
  read-only `doctor`/`status`; every mutating remote action stays fail-closed and unowned.
- The first fresh RTX 4090 package, fixed external-model install, and packaged restart passed on
  `sm_89` ([lane](https://github.com/alphastorm/ninfer-4090), upstream
  [UDPSendToFailed/ninfer-4090](https://github.com/UDPSendToFailed/ninfer-4090)), but its exact
  Golden-equivalent exhausted its output bound with two unclosed tool regions; the safe parser
  correctly returned text rather than fabricating arguments. Protocol, 100K+ restart-persistence,
  and performance gates remain blocked, so RTX 4090 support is still a non-claim. That lane has
  also measured disk-checkpoint session restores (a 105K-token session prepared in well under a
  second instead of a cold re-prefill); the receipt publishes with the lane.
- Fleet routing across two GPUs exists in source, but a two-machine performance claim is deferred
  until both hardware profiles are release-qualified and a fixed workload shows a real
  completed-work benefit without weakening sticky warm-session ownership or fail-closed routing.

## Upstreaming to Oh My Pi

The beta OMP client is a pinned fork build carrying the NInfer stateful-Responses provider
integration; running a fork was the fastest way to ship one exact qualified combination. The
standing intent is to upstream the reusable parts — provider semantics, stateful Responses
transaction, appliance profile plumbing — to
[can1357/oh-my-pi](https://github.com/can1357/oh-my-pi) so the integration stops requiring a fork
at all. Until then, publishing the exact integration source corresponding to the distributed binary
remains a broad-release gate below.

## Continuous — performance program

Kernel and schedule optimization runs alongside releases, in public, with an auditable experiment
ledger and an open ideas backlog: [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md). Candidate areas
include prefill, decode, MTP acceptance and verification cost, Vision, KV storage, weight paging,
and long-session continuation. No optimization result becomes part of a release until its exact
binary and profile are rebound through a new qualification receipt.

## Broad public release gate

Before marketing beyond invited testers:

- publish or otherwise make inspectable the exact OMP integration source corresponding to the
  distributed binary (or land the upstreaming above);
- finish managed remote install/upgrade/rollback or explicitly retain the manual topology as the
  supported product;
- close the highest-signal early-access installation and compatibility failures;
- define a support/compatibility matrix from observed machines rather than GPU-family inference;
- re-run external installation from public URLs and immutable digests;
- publish a concise security model and vulnerability-reporting route; and
- cut a new release candidate if any executable component, model, configuration, or support
  boundary changes.

## How to help right now

- **Own an RTX 5090 and use OMP?** Run the quickstart and file a
  [hardware report](https://github.com/alphastorm/omp-ninfer/issues/new/choose) — pass or fail,
  both move the matrix.
- **Measured something?** Submit the
  [benchmark report form](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml)
  for the [community results table](docs/BENCHMARKS.md#community-results).
- **CUDA/kernel work?** Claim an idea from the
  [performance backlog](docs/PERFORMANCE.md#ideas-backlog).
- **4090 owner?** The Golden typed-tool-call blocker is the single gate holding that lane; watch
  [alphastorm/ninfer-4090](https://github.com/alphastorm/ninfer-4090).
- **3090 owner?** The reviewed port from Don-Chad/ninfer-3090 has not started; interest expressed
  on an issue helps prioritize it.
