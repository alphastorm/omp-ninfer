# Roadmap

This roadmap is a scope boundary, not a promise of dates. The product wedge is OMP plus NInfer
plus Qwen3.8 on user-controlled RTX cards: qualified RTX 5090, RTX 4090, and RTX 3090 release
lanes, each bound to exact bytes and a receipt. The `v0.4.8` public release exposes only those
exact installable profiles. Work outside that wedge needs a new product decision rather than
placeholder abstractions, and nothing below becomes part of a release until its exact binary and
profile are rebound through a new qualification receipt.

Want to move something here? The fastest ways to help are listed at the end of this page and in
[`CONTRIBUTING.md`](CONTRIBUTING.md); performance work has its own program page at
[`docs/PERFORMANCE.md`](docs/PERFORMANCE.md).

## Where this is now — v0.4.9

All three lanes install from public URLs with durable, restart-resumable session state; the two
native Windows lanes now restore a checkpointed session in seconds rather than minutes (RTX 4090
1.13 GB in 5.6 s, was 133-149 s; RTX 3090 1.68 GB in 10.7 s, was 92 s), and the
RTX 5090 lane reuses a session's base prefill across sibling agent branches: four branches
that replayed 67.7K tokens from scratch on v0.4.1 (148.7 s) run in 47.9 s, and a branch whose
anchor is still device-resident starts generating in 0.40 s
([receipts](docs/measurements/2026-08-31-fanout-probe-v043.json)). Details:
[`CHANGELOG.md`](CHANGELOG.md) · [release status](docs/RELEASES.md) ·
[benchmarks](docs/BENCHMARKS.md).

## 0.4.x campaign status

Sequenced by dependency; completed experiments remain visible because negative results constrain
what can ship next:

1. **Shared-page fanout — shipped in v0.4.3**
   ([ninfer#34](https://github.com/alphastorm/ninfer/issues/34)). Sibling branches reuse the
   anchored base prefill instead of cloning its private pages.
2. **RTX 3090 durable-and-fanout train — shipped in v0.4.5.** The 3090 lane joined the durable
   v0.2 lineage with restart qualification and the same MTP3 shipped profile.
3. **MTP depth-and-corpus ablation — completed post-v0.4.7; retain MTP3.**
   MTP0/3/5/7 ran against the same binary and model within each lane on 24 deterministic
   agent-shaped requests. MTP3 was fastest on every lane and in both repetitions. Against MTP3,
   K5/K7 were 13.57%/24.72% slower on RTX 5090, 7.29%/20.17% slower on RTX 4090, and
   11.34%/22.46% slower on RTX 3090. No alternative cleared the 5% promotion margin; keep the
   qualified MTP3 incumbent and reject deeper drafting for the current artifacts. Exact-output
   attribution remains unresolved because the original traces lack one shared campaign identity
   and a separate fresh-process MTP0 control, but that does not invalidate the no-change throughput
   decision. Public-safe receipts: [5090](docs/measurements/2026-09-04-rtx5090-mtp-agent-ablation.json) ·
   [4090](docs/measurements/2026-09-04-rtx4090-mtp-agent-ablation.json) ·
   [3090](docs/measurements/2026-09-04-rtx3090-mtp-agent-ablation.json). No public release profile
   changed.
4. **`nvfp4` artifact decision — completed post-v0.4.7; not adopted on 32 GB.** The per-lane
   variant campaign measured the artifact on the RTX 5090 with the same corpus and campaign
   identity as every other arm. The chain is conditional on the card, not on the artifact's
   numerics: the weights are 3.28 GB larger, so with the shipped BF16 KV the engine refuses its
   runtime reservation at 131,072 context; the only way to run it here is INT8 KV; and INT8 KV
   alone (same groupwise-int artifact) regresses every criterion of the private role-corpus
   screen. On INT8 KV, `nvfp4` prefills 2.22× faster (6,089 vs 2,740 tok/s), decodes 3.5%
   slower, cuts modeled session time by 15.5–28.7%, beats the INT8 control on every quality
   criterion, and still lands two cases behind the BF16 incumbent on grounding (evidence
   precision −2.4 pp, unsupported-claim rate +2.2 pp) while leaking fewer canaries (4 vs 8); the
   screen reproduces exactly across fresh processes. Two verdicts are recorded side by side: the
   campaign's executable gate says retain (the twelve-criterion screen fails on those two
   grounding criteria, and under the three criteria the frozen manifest originally named —
   leaks, schema validity, fact recall — the same arm would have passed; the amendment is
   recorded in the arms manifest), and the product judgment is that `nvfp4` with INT8 KV is a
   v0.5 RTX 5090 candidate if that grounding shift is accepted and the durable checkpoint train is
   requalified on INT8 pages. NVFP4 W4A4 needs Blackwell tensor cores, so the `sm_89`/`sm_86`
   lanes are out of scope (the 4090 upstream removed its NVFP4 path). The groupwise-int artifact
   stays pinned on all three lanes. Receipts:
   [5090](docs/measurements/2026-09-04-rtx5090-variant-campaign.json) ·
   [4090](docs/measurements/2026-09-04-rtx4090-variant-campaign.json) ·
   [3090](docs/measurements/2026-09-04-rtx3090-variant-campaign.json) ·
   [repeatability](docs/measurements/2026-09-04-rtx5090-quality-repeatability.json).
5. **Per-lane configuration changes from the same campaign — requalified 2026-09-05; shipped in
   `v0.4.8`.** Lanes are tuned independently: the goal is the best measured stack per card,
   not one shared configuration. Each lane reran its own qualification on its own rig with the
   changed configuration and a rebound identity:
   - RTX 4090 `v0.2.1` (`ninfer` commit `b9c4636b`, package `1c66f7d5`): prefill chunk 512 →
     2,048 on the rk2v4-e8/MTP3/131,072 stack; protocol 15/15, the 102,060-token session in
     68.0 s against 84.9 s shipped, persistence via `append_frontier`, OMP golden run exact
     ([receipt](releases/v0.4.8/qualification/rtx4090.json)).
   - RTX 3090 `v0.2.3-beta.1` (`ninfer` commit `2ce6c9dc`, package `96c9c37f`): context ceiling
     65,536 → 131,072 on the INT8/MTP3/1,024-chunk stack; the 14-phase orchestrator passed with
     exact 130,048-token retrieval, 90.2 decode tok/s under the 300 W cap at 22,548 MiB peak,
     restart, rollback, security, and OMP gates
     ([receipt](releases/v0.4.8/qualification/rtx3090.json)).
   - RTX 5090 `qwen38-5090-v0.4.8` (same image `876c7809`, configuration `95765a38`):
     `--max-private-continuations 8 --device-state-slots 4 --host-state-slots 24`; exact
     130,048-token retrieval at 2,207 tok/s cold, 136.0 decode tok/s, the fork/delete arc across a
     restart, 4/4 anchor hits at 57.9K and 67.7K, a 4.5 GB save and verified restart
     ([receipt](releases/v0.4.8/qualification/rtx5090.json),
     [gates](docs/measurements/2026-09-05-rtx5090-v048-profile-gates.json)). After a restart the
     first sibling fork of a restored template re-prefills once; the receipt records it.
   INT8 KV stays rejected on the RTX 5090 (no speed gain) and RTX 4090 (23,180 MiB peak, screen
   regression). The two native components are published (`v0.2.1-qwen38-4090-durable.1`,
   `v0.2.3-qwen38-3090-beta.1`; every manifest URL verified against its hash) and the composed
   external-installation acceptance was rerun from those URLs on 2026-09-05
   ([receipt](releases/v0.4.8/acceptance/composed-external-installation.json)).
   Cut as `v0.4.8` on 2026-09-05. The owner's RTX 5090 appliance promotes to the v0.4.8 profile
   through its own private role-corpus gate, separately from the product release.
6. **MTP exact-output attribution — focused, non-blocking follow-up.** If pursued, run only the
   missing fresh-process MTP0 controls and targeted K0/K3 first-divergence probes. Do not rerun the
   rejected K5/K7 arms without new evidence that could reverse their measured deficit.

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
2. **Template-fork warm starts — measured 2026-09-04; not yet a warm start.** Checkpoint a session
   immediately after the system prompt and repository context are prefilled, then fork every
   subagent from that generation so each one starts hot instead of paying a 30–90 s prefill. The
   probe ([`scripts/fleet_probe.py`](scripts/fleet_probe.py)) measured the pattern on all three
   shipped lanes: device-resident forks are hot only on the RTX 5090, and there only reliably for
   templates of roughly 64K tokens or more (a 57.9K template alternates 1.3 s / 22.5 s because
   the private anchor catalog holds two entries and evicts the shared base anchor; 67.7K gives four
   1.3 s forks); across a process restart the checkpoint restore is never faster than
   re-prefilling the template (5090: 24.7 s vs 21.8 s at 4.5 GB; 4090: 130 s vs 41 s at 1.13 GB;
   3090: 91 s vs 49 s on the shipped binaries; the native-lane restore path was fixed at source
   later the same day, see below), and the native lanes have no sibling reuse at all. The sub-64K loss was
   diagnosed on 2026-09-05 as capacity, not policy: the shipped context-cache defaults (private
   catalog 2, device-state slots 2) cannot hold a base anchor and one stored sibling. Two source
   changes were rejected on the probe; the unchanged shipped binary with
   `--max-private-continuations 8 --device-state-slots 4 --host-state-slots 24` kept 12/12 forks
   on the anchor path at 57.9K, 67.7K, and a loaded-catalog 57.9K in one process for 0.43 GiB of
   slack. It is a trade: it removes the two 22 s re-prefills per four forks at 57.9K and costs
   about 3.9 s once on the first 67.7K fork (5.29 s vs 1.39 s) while the anchor state materializes.
   That configuration is the v0.4.8 RTX 5090 candidate profile, gated by this probe at both
   template sizes in one process; it changes the profile identity, so existing session checkpoints
   do not carry across and the durable train requalifies with it
   ([ninfer#35](https://github.com/alphastorm/ninfer/issues/35)). Restore bandwidth on the
   native lanes was a runtime defect, not a disk limit: the reader issued one DirectStorage
   request per KV page segment; it now reads one staging window at a time and the same sessions
   restore in 5.6 s on the RTX 4090 (was 146.6 s / 133.4 s) and 10.7 s on the RTX 3090 (was
   91.8 s / 92.2 s), quoting planted ledger keys exactly after every restart
   ([ninfer#36](https://github.com/alphastorm/ninfer/issues/36); lane commits `d22ce3fd` and
   `3756db6e`; both lanes requalified on 2026-09-05 and shipped in `v0.4.9` with components
   `v0.2.2-qwen38-4090-durable.1` and `v0.2.4-qwen38-3090-beta.1`). Receipts:
   [5090](docs/measurements/2026-09-04-template-fork-rtx5090.json) ·
   [4090](docs/measurements/2026-09-04-template-fork-rtx4090.json) ·
   [3090](docs/measurements/2026-09-04-template-fork-rtx3090.json) ·
   [anchor sweep](docs/measurements/2026-09-05-fanout-anchor-configuration-sweep-rtx5090.json) ·
   [restore 4090](docs/measurements/2026-09-05-restore-probe-rtx4090.json) ·
   [restore 3090](docs/measurements/2026-09-05-restore-probe-rtx3090.json) ·
   [restore fix 4090](docs/measurements/2026-09-05-restore-probe-rtx4090-candidate.json) ·
   [restore fix 3090](docs/measurements/2026-09-05-restore-probe-rtx3090-candidate.json).
3. **Fleet routing — configuration published and the fixed workload measured 2026-09-05.**
   [`examples/fleet/`](examples/fleet/) is one OMP configuration spanning the three lanes with
   explicit roles (`local-main` on the RTX 5090, `local-heavy` on the RTX 4090, `local-scout` on
   the RTX 3090), fail-closed tunnels, and two role agents. The fixed workload is the frozen
   24-request agent corpus as 14 independent jobs, dispatched by
   [`scripts/fleet_dispatch.py`](scripts/fleet_dispatch.py) with one active request per lane.
   Measured boundary (batch completion, two repetitions each, all jobs completed): the RTX 5090
   alone 66.8 s; two machines (5090+4090) 51.2 s with naive longest-first dispatch and **43.4 s**
   (1.54×) with cost-aware assignment from the lanes' measured per-scenario costs; three machines
   47.2 s naive and **32.3 s** (2.07×) cost-aware, with all three lanes balanced within 2 s of
   busy time. Pinning jobs to lanes by role alone is a loss (100.3 s, 0.66×): the long-prefill
   jobs cost 14.9 s on the 5090 but 48.6 s on the 4090 and 91 s on the 3090, while short chat
   jobs cost about the same everywhere - so roles describe what a lane is for, and the cost model
   decides where work goes. No fleet claim beyond this workload; outputs are not comparable across
   lanes (different KV formats), and the 4090's same-process output variation recorded on
   2026-09-04 recurs here. Receipts: [`docs/measurements/2026-09-05-fleet-dispatch-*.json`](docs/measurements/)
   (EXP-016).

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
| `v0.4.8` | Each lane on its own best measured configuration: RTX 5090 context-cache profile (sibling forks keep the base anchor), RTX 4090 prefill chunk 2,048, RTX 3090 131,072-token context; every lane requalified on its rig and accepted from public URLs |
| `v0.4.7` | Corrected immutable runtime asset URLs from v0.4.6; component bytes unchanged |
| `v0.4.6` | Checkpoint-origin authentication for future cross-machine replication; 4090/3090 components rebound unchanged |
| `v0.4.5` | RTX 3090 joined the durable train with automatic saves, explicit checkpoints, restart qualification, and fanout support |
| `v0.4.4` | RTX 5090 checkpoint export decoupled from the engine with bounded writes, sustained-idle saves, and lazy restore repair |
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
