# Roadmap

This roadmap is a scope boundary, not a promise of dates. The product wedge is OMP plus NInfer
plus Qwen3.8 on user-controlled RTX cards: qualified RTX 5090, RTX 4090, and RTX 3090 release
lanes, each bound to exact bytes and a receipt. The `v0.4.3` public release exposes only those
exact installable profiles. Work outside that wedge needs a new product decision rather than
placeholder abstractions, and nothing below becomes part of a release until its exact binary and
profile are rebound through a new qualification receipt.

Want to move something here? The fastest ways to help are listed at the end of this page and in
[`CONTRIBUTING.md`](CONTRIBUTING.md); performance work has its own program page at
[`docs/PERFORMANCE.md`](docs/PERFORMANCE.md).

## Where this is now — v0.4.3

All three lanes install from public URLs with durable, restart-resumable session state, and the
RTX 5090 lane now reuses a session's base prefill across sibling agent branches: four branches
that replayed 67.7K tokens from scratch on v0.4.1 (148.7 s) run in 47.9 s, and a branch whose
anchor is still device-resident starts generating in 0.40 s
([receipts](docs/measurements/2026-08-31-fanout-probe-v043.json)). Details:
[`CHANGELOG.md`](CHANGELOG.md) · [release status](docs/RELEASES.md) ·
[benchmarks](docs/BENCHMARKS.md).

## Next in 0.4.x

Sequenced by dependency, each a receipt-gated campaign:

1. **Shared-page fanout — every sibling branch sub-second**
   ([ninfer#34](https://github.com/alphastorm/ninfer/issues/34)). Today the first branch from a
   parked base is fast (0.40 s to first token) and siblings re-materialize ~4.4 GB of KV from
   host RAM (~15 s at 67.7K tokens) because private forks clone their pages. Publishing the
   anchored frontier as refcounted shared pages lets every branch attach without cloning — the
   milestone where "fan four subagents out of one warm base" costs seconds total, not a minute.
2. **RTX 3090 durable-and-fanout train.** The 3090 lane ships the qualified v0.2-lineage parity
   package; porting the durable checkpoint store and fanout anchors (the same lineage the 4090
   took on 2026-08-31) closes the last capability gap between the three lanes. Ends at a staged
   candidate and receipts, not an automatic cut.
3. **MTP depth-and-corpus ablation.** One unchanged artifact, MTP0/3/5/7, measured on an
   agent-shaped corpus (tool calls, thinking, long turns) that now accumulates for free from real
   per-lane session request logs. The 99.87% v0.3 acceptance is a fixed-workload artifact; this
   ablation decides the draft depth every lane ships next.
4. **`nvfp4` artifact decision.** The upstream campaign shows 3.48× groupwise-int prefill and a
   higher GPQA row for `nvfp4`; adopting it swaps the pinned model artifact and forces
   requalification of all three lanes. Decided with the ablation data in hand; until then the
   groupwise-int artifact stays pinned.

## v0.5.x — sessions leave the machine

The 0.5 series is about one thing: a session stops being bound to the card that created it.

1. **Checkpoint sync — replicate, don't serve.** The native IO paths are O_DIRECT/DirectStorage
   and require local filesystems, so network shares are never a checkpoint root. Generations are
   immutable, SHA-manifested, and atomically published, so replication is a crash-consistent copy
   of `sessions/` to shared storage (NAS/S3) and a copy-back to local NVMe before restore.
   Security gate first: checkpoints that cross a trust boundary need manifest origin
   authentication ([ninfer#32](https://github.com/alphastorm/ninfer/issues/32)) — a keyed MAC
   with a compatibility window — before any import path opens. Portability stays
   same-profile-pair only: the runtime fingerprint binds binary and profile, so identical-lane
   machine pairs can resume and cross-lane resume (5090↔4090) structurally cannot.
2. **Template-fork warm starts.** Checkpoint a session immediately after the system prompt and
   repository context are prefilled, then fork every subagent from that generation: each one
   starts hot instead of paying a 30–90 s prefill. Fork lineage is already a qualified contract
   and shared-page fanout (0.4.x) makes the forks cheap; this receipts the operational pattern.
3. **Fleet routing.** One OMP configuration spanning the 3090/4090/5090 lanes with explicit
   per-lane roles. A fixed two-machine workload gets measured before any fleet completed-work or
   throughput claim — that boundary stands until the receipt exists.

Parked until >131,072-token contexts matter: paged host-to-device KV prefetch and the
E8-lattice/RotorQuant ceiling work the family ports carry upstream.

## Path to v1.0

A public release does not imply a v1.0 or SLA commitment. v1.0 means the durability contract —
save is atomic and verified, restore is verified-or-refused, sessions survive process death, and
private state never crosses sessions — holds under independent eyes, not just owner receipts.
Before a v1.0 decision:

- gather clean-install and rollback evidence from multiple independent owners for each claimed
  GPU profile;
- sign the Windows packages and notarize the macOS client, or retain the explicit unsigned
  boundary;
- close the highest-signal public-release installation and compatibility failures;
- publish supported upgrade and security-fix windows, rollback ownership, and response-time
  expectations without implying an SLA;
- run the fixed two-machine workload before making any fleet completed-work claim; and
- cut a new release candidate if any executable component, model, configuration, or support
  boundary changes.

Explicitly not on this path (a new product decision, not a milestone): multi-tenant serving,
priority or preemptive scheduling, universal hardware claims, and silent cloud fallback.

## Shipped

Each release keeps its immutable manifest and receipts; summaries here, details in
[release status](docs/RELEASES.md) and [`CHANGELOG.md`](CHANGELOG.md).

| Release | What landed |
| --- | --- |
| `v0.4.3` | RTX 5090 fanout anchors (sibling branches reuse the base prefill), checkpoint-import integrity (streamed re-hash, fail-closed, quarantine), constant-time credential checks, session isolation hardening |
| `v0.4.2` | RTX 4090 lane moved to the durable v0.2 package: 102,075 tokens restored onto a fresh process, chunked KV restore, hardened D3D12 residency, MTP K=15 capacity (MTP3 shipped arm) |
| `v0.4.1` | RTX 5090 checkpoint-store hardening: health-gated quota transitions, named skip reasons, post-publish reclamation acknowledged |
| `v0.4.0` | Durable RTX 5090 container: transactional session checkpoints, 109,589 tokens restored hot across a docker restart, exact retrieval at 130,448 tokens |
| `v0.3.1` | RTX 4090 MTP3 promotion (+17.04% complete Golden-equivalent wall time) and the draft-depth sweep |
| `v0.3.0` | First public release: one exact install lane per qualified GPU profile, `Latest` on GitHub |
| `v0.2.x` | Managed lifecycle (doctor/plan/install/status/benchmark/checkpoint/rollback/support-bundle), native OMP 18.0.9 clients for macOS/Windows/Linux, durable native-Windows checkpoints, RTX 3090 parity campaign |
| `v0.1.0-beta.1` | Restricted RTX 5090 beta: exact manifest, external clean install from public URLs |

Standing support boundaries (unchanged since v0.2, restated with every release): prerelease
support only with no SLA; one active request per qualified profile; JSON-schema structured output
rejected rather than ignored; the unattended RTX 3090 evidence role disabled; no multi-GPU,
multi-tenant, priority, or preemptive scheduling claim; no universal throughput, latency, or
hardware claim; no silent cloud fallback; measured numbers apply only to the recorded package,
machine, and profile.

The remaining expensive-to-add-later items stay explicit rather than hidden release debt:

- adopt the shared native-Windows source-first qualification sequence in
  [the release process](docs/RELEASES.md#next-native-release-sequencing);
- notarized macOS distribution and a first-party Windows signing path;
- a public, hardware-independent acceptance runner shared by all client releases;
- JSON-schema constrained decoding only if the runtime can enforce rather than ignore the
  contract;
- concurrency-qualified 3090/4090 profiles after memory and latency gates exist for those exact
  packages;
- a dependency-level SBOM for the 4090 package beyond its complete file inventory;
- a doctor-level WSL networking-mode and loopback-reachability preflight for the Windows Docker
  profiles ([#15](https://github.com/alphastorm/omp-ninfer/issues/15)); and
- a fixed two-machine workload before any fleet completed-work or throughput claim.

## Upstreaming to Oh My Pi

The pinned OMP client carries the NInfer stateful-Responses provider integration; running a fork
was the fastest way to ship one exact qualified combination. The exact accepted source is public
at [alphastorm/oh-my-pi](https://github.com/alphastorm/oh-my-pi). The standing intent remains to
upstream the reusable provider semantics, stateful transaction, and appliance plumbing to
[can1357/oh-my-pi](https://github.com/can1357/oh-my-pi).

## Continuous — performance program

Kernel and schedule optimization runs alongside releases, in public, with an auditable experiment
ledger and an open ideas backlog: [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md). Candidate areas
include prefill, decode, MTP acceptance and verification cost, Vision, KV storage, weight paging,
and long-session continuation. No optimization result becomes part of a release until its exact
binary and profile are rebound through a new qualification receipt.

## How to help right now

- **Run OMP with subagents against a lane?** That fanout path is exactly what v0.4.3 changed —
  file a [hardware report](https://github.com/alphastorm/omp-ninfer/issues/new?template=hardware-report.yml)
  with what you observe, pass or fail.
- **Measured something?** Submit the
  [performance result form](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml)
  for the [community results table](docs/BENCHMARKS.md#community-results).
- **CUDA/kernel work?** Claim an idea from the
  [performance backlog](docs/PERFORMANCE.md#ideas-backlog).
- **RTX 3090, 4090, or 5090 owner?**
  [`Get started`](docs/QUICKSTART.md) with the matching published lane, then file a content-safe
  [hardware report](https://github.com/alphastorm/omp-ninfer/issues/new?template=hardware-report.yml)
  or [clean-install report](https://github.com/alphastorm/omp-ninfer/issues/new?template=clean-install-report.yml).
  Pass and fail reports both improve the observed matrix; one lane never authorizes package
  substitution in another.
