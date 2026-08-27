# Roadmap

This roadmap is a scope boundary, not a promise of dates. The current product wedge is OMP plus
NInfer plus Qwen3.8 on user-controlled RTX 5090 machines. RTX 4090 runs in the separate deferred
`alphastorm/ninfer-4090` lane; work outside that wedge needs a new product decision rather than
placeholder abstractions.

## v0.1.0-beta.1 — invited RTX 5090 early access

The first release is complete when an invited tester can start from the published artifacts and,
without access to a developer workstation:

1. install the exact OMP beta on Apple-silicon macOS;
2. verify and start the exact NInfer image and Qwen3.8 artifact on a Linux or WSL2 RTX 5090 host;
3. open an authenticated local SSH forward to the remote loopback endpoint;
4. configure OMP's exact `openai-responses` provider without a cloud fallback;
5. complete text, tool, image, stateful follow-up, OMP exit/resume, and fail-closed tunnel checks; and
6. produce a redacted hardware or installation report without secrets or prompt content.

The beta ships only the manual-tunnel profile. Its release manifest must bind the OMP artifact,
NInfer image digest and SBOM, NInfer/model/config hashes, Homebrew beta cask, qualification summary,
and exact setup smoke. The 5090 runtime is already release-eligible; publication and a clean
external-install smoke remain separate gates. The exact release-source image, deterministic OCI
archive, binary package, and SPDX SBOM now exist locally and passed a state-faithful remote
doctor/install/status/quick-benchmark/rollback/support-bundle rehearsal; none is published.

### Explicit non-claims

- no `omp appliance install` remote lifecycle;
- no managed upgrade or appliance-level rollback;
- no automatic restart of the NInfer container;
- no NInfer process-restart continuation claim;
- no RTX 4090 support claim;
- no multi-GPU, multi-tenant, priority, or preemptive scheduling;
- no universal throughput, latency, or hardware claim;
- no silent cloud fallback; and
- no general-availability support commitment.

## v0.2 — managed appliance lifecycle

The next product release is expected to replace manual setup with the existing `omp appliance ...`
command family after the remote execution boundary is implemented and qualified. Target outcomes:

- Mac-to-remote-Linux/WSL transport owned by the appliance platform instead of a manually maintained
  tunnel;
- manifest-driven `doctor`, `plan`, `install`, `status`, `benchmark --quick`, `rollback`, and
  `support-bundle` against immutable published artifacts;
- exact candidate/incumbent identity and rollback receipts on the remote host;
- OMP exit/resume and, if separately qualified, NInfer process-restart continuation;
- clean install, already-installed, upgrade, interrupted-install, and rollback acceptance from
  representative predecessor state;
- RTX 4090 beta support only after a fresh package, restart, protocol, long-context, and Golden lane
  passes on the fixed external-model installer; and
- RTX 3090 beta support only after a reviewed current-architecture port from
  [`Don-Chad/ninfer-3090`](https://github.com/Don-Chad/ninfer-3090) and the same fresh package,
  restart, protocol, long-context, and Golden qualification on a representative RTX 3090 host; and
- one manifest authority mechanically checked against OMP's compiled profile registry and the
  Homebrew cask.

The RTX 5090 remote-side transitions above are proven inputs, not a shipping managed CLI claim. A
reviewed draft now owns bounded read-only Mac-to-SSH/WSL `doctor` and `status`; it rejects blank
destinations and every mutating remote action before SSH. Bootstrap/version attestation,
authenticated loopback forwarding, artifact transfer, install, rollback, and recovery remain
unowned, and the draft must be reconciled with the current OMP release series before merge.

The first fresh RTX 4090 package, fixed external-model install, and packaged restart passed on
`sm_89`, but its exact Golden-equivalent exhausted its output bound with two unclosed tool/function
regions. The safe parser correctly returned text rather than fabricating missing arguments.
Protocol, 100K+ restart-persistence, and performance gates therefore remain blocked, and RTX 4090
support is still a non-claim.

Fleet routing already exists in source, but a two-machine performance claim is deferred until both
hardware profiles are release-qualified and the fixed foreground/background workload shows a real
completed-work benefit without weakening sticky warm-session ownership or fail-closed routing.

## Later optimization work

Kernel and schedule optimization follows the first feedback release. Each optimization must preserve
the supported numerical and state contracts and demonstrate improvement at the scope claimed.
Candidate areas include prefill, decode, MTP acceptance/cost, Vision, KV storage, and long-session
continuation. No optimization result is part of `v0.1.0-beta.1` unless its exact binary and profile
are rebound through a new qualification receipt.

## Broad public release gate

Before marketing beyond invited testers:

- publish or otherwise make inspectable the exact OMP integration source corresponding to the
  distributed binary;
- finish managed remote install/upgrade/rollback or explicitly retain the manual topology as the
  supported product;
- close the highest-signal early-access installation and compatibility failures;
- define a support/compatibility matrix from observed machines rather than GPU-family inference;
- re-run external installation from public URLs and immutable digests;
- publish a concise security model and vulnerability-reporting route; and
- cut a new release candidate if any executable component, model, configuration, or support boundary
  changes.
