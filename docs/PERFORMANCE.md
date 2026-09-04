# Performance program

The shipped profile is the floor, not the ceiling. This page is the public working surface for
kernel and schedule optimization on the three qualified RTX runtime lanes: measured baselines, the
profiling lane, an auditable ledger of what has been tried, and the open ideas backlog.

Ground rules:

1. **Contracts before speed.** Every optimization must preserve the numerical and state contracts
   of the supported profile (exact-output oracles, stateful Responses semantics, Vision, thinking
   preservation).
2. **Receipts before claims.** A result exists when its profiling packet or benchmark report is
   preserved with the exact source identity that produced it.
3. **No silent rebinding.** No optimization result becomes a product claim until its exact binary
   and profile are rebound through a new release qualification
   (see [`RELEASES.md`](RELEASES.md)).

Kernel and runtime changes land in [alphastorm/ninfer](https://github.com/alphastorm/ninfer)
(a downstream fork of [Neroued/ninfer](https://github.com/Neroued/ninfer)); this page tracks the
program so contributors can see the state of play in one place.

## Measured baseline

One RTX 5090 (`sm_120a`), shipped v0.2 profile — Qwen3.8-27B `groupwise-int`, BF16 KV, MTP3,
1,024-token prefill chunks, one active request
([receipts](../releases/v0.2.0-beta.1/qualification.json)):

| Metric | Value |
| --- | --- |
| Decode throughput | 235.02 tok/s over 2,048 completion tokens |
| MTP3 acceptance | 99.87% (1,534/1,536) on the fixed decode workload |
| 130,048-token exact prefill | 2,180.87 tok/s; 59.80 s server round trip |
| Stateful Responses | passed; the predecessor v0.1 37,591-token prefix hit is not rebound as a v0.2 numeric claim |
| Warm follow-up TTFT | 0.375 s at an 89,216-token session vs 36.697 s cold ([labeled maintainer measurement](BENCHMARKS.md#maintainer-measurement--warm-vs-cold-follow-up-turn-2026-08-29)) |

Hardware envelope, measured with the runtime repo's `hbm_bandwidth_probe`: **1,674.5 GB/s**
sustained pure-read HBM bandwidth on this RTX 5090 — 93.4% of the 1,792 GB/s theoretical peak.
Single-request decode of a memory-bound quantized model lives against that roofline; that is the
number kernel work is judged against.

### RTX 3090 candidate reference

The fresh native Windows candidate adds a bounded transferability point, not an
architecture-normalized comparison: MTP3, INT8 KV, C1, 4,541 computed prefill tokens, and an exact
1,024-token completion at the 300 W profile cap.

| Metric | Value |
| --- | ---: |
| Decode throughput | **90.17 tok/s** |
| Prefill throughput | **893.41 tok/s** |
| MTP3 acceptance | **93.43%** |
| End-to-end wall time | **16.48 s** |
| Peak VRAM | **21,159 MiB** |
| Peak power / temperature | **299.8 W / 47 °C** |

Exact package, source, and phase hashes:
[`2026-08-30-rtx3090-parity.json`](measurements/2026-08-30-rtx3090-parity.json). These numbers
remain candidate evidence until a new product manifest binds the package.

## The profiling lane

Runtime mainline commit
[`7c1c1936`](https://github.com/alphastorm/ninfer/tree/7c1c1936d1fd8b645bc7a30cdcbe35cc6b12c206/tools/bench)
turns one-off profiling into reproducible packets without a long-lived controller branch:

- `tools/bench/run_sm120_mtp3_profile.sh` — orchestrates Nsight Compute, Nsight Systems, and
  timing captures for the MTP3 decode loop with container isolation and performance-counter
  checks.
- `tools/bench/run_sm120_q4_mtp3_profile.sh` — profiles the Q4 SwiGLU kernels at decode (`M=1`)
  and MTP3 verification (`M=4`) shapes.
- `tools/bench/summarize_ncu_q4.py` — reduces wide NCU reports to DRAM-bytes and duration ratios.
- `tests/test_sm120_mtp3_profile.py`, `tests/test_sm120_q4_profile.py` — regression checks on
  packet structure, so a captured packet is machine-comparable, not a screenshot.

Packets (NCU/NSYS reports, timing summaries) are preserved in-tree under `profiles/` on that
branch. Current findings from the scripted captures:

- Mean MTP3 round duration: **15.34 ms** with **2.8 accepted tokens per round** on the profiled
  corpus (workload-dependent; the qualification task measured 77.0% acceptance).
- MTP3's verification batch is nearly free relative to its payoff: processing `M=4` tokens costs
  **1.227×** the latency of `M=1` with effectively identical DRAM traffic (96.7 MB vs 96.6 MB per
  layer pass). That asymmetry is why drafting 3 tokens per round wins.

## Experiment ledger

The auditable history: what was tried, the exact method, the measured result, and the verdict.
Entries are append-only; verdicts are `kept`, `rejected`, `inconclusive`, or `open`. Evidence paths
refer to the runtime repositories. As of 2026-09.

| ID | Area | Hypothesis | Result | Verdict |
| --- | --- | --- | --- | --- |
| EXP-001 | Q4 SwiGLU decode/verify | A small-T MMA path can verify 4 speculative tokens for near-GEMV latency | `M=1` GEMV 76.77 µs at 1,258.7 GB/s; `M=4` MMA 94.21 µs at 1,026.8 GB/s; 1.227× latency for 4 tokens | kept |
| EXP-002 | Q5 linear+add post-mixer | A CTA-collective `mma-r64-c16` kernel beats SIMT split-2 | Candidate 190.46 µs vs production 51.20 µs — 3.72× slower | rejected |
| EXP-003 | GDN state under speculation | Caching gate activations (ReplaySSM) removes recurrent-state drift on MTP rollback | Bit-identical recurrent fold at 167.82 µs/layer; no drift across long contexts | kept |
| EXP-004 | Tensor-core prefill | W4A4 MMA prefill (NVFP4 artifacts) multiplies prefill throughput | 11,191 vs 3,218 tok/s at a 7,680-token prompt — 3.48× (upstream campaign, NVFP4 profile) | kept upstream |
| EXP-005 | RTX 5090 agent-shaped MTP depth | A deeper draft beats MTP3 without changing normalized output | MTP3 was fastest observed at 172.94 decode tok/s; MTP0 changed on 1/12 within-process repeats, and campaign/cross-process controls are absent | inconclusive |
| EXP-006 | RTX 4090 agent-shaped MTP depth | A speculative arm beats output-identical MTP0 | MTP3 was fastest observed at 110.95 tok/s; MTP0 changed on 10/12 within-process repeats, and campaign/cross-process controls are absent | inconclusive |
| EXP-007 | RTX 3090 agent-shaped MTP depth | A deeper draft beats MTP3 without changing normalized output | All arms repeated within process; MTP3/5/7 differed from MTP0 on 6/8/4 outputs, but campaign/cross-process controls are absent | inconclusive |

Entry detail:

- **EXP-001 — MTP3 verification economics.** Nsight Compute packets on the `sm_120a` Q4 SwiGLU
  pair kernels show decode (`M=1`) already at 75.2% of the measured read peak, and the 4-token
  verification batch moving the same bytes. Conclusion: speculative verification is
  bandwidth-amortized; acceptance rate, not verify cost, is the lever. Packets:
  [`profiles/`](https://github.com/alphastorm/ninfer/tree/7c1c1936d1fd8b645bc7a30cdcbe35cc6b12c206/profiles)
  at the integrated mainline commit.
- **EXP-002 — negative result, kept on the record.** The MMA candidate for the Q5 post-mixer was
  triaged `more-than-50-percent-slower` and rejected; SIMT split-2 remains production. Negative
  results are part of the ledger so the next contributor does not re-run the same dead end.
- **EXP-003 — correctness enabler.** ReplaySSM-style gate caching (idea lineage: Tri Dao's
  "cache SSM inputs, not state"; see also the
  [ninfer-3090](https://github.com/Don-Chad/ninfer-3090) port) is what lets MTP3 speculate over
  hybrid GDN/attention layers without state divergence — a precondition for every speculative
  speedup on this architecture.
- **EXP-004 — prefill headroom.** The upstream NVFP4 campaign proves the prefill ceiling moves
  ~3.5× with tensor-core-native weights. The shipped artifact is `groupwise-int`; an NVFP4-profile
  product lane would need its own qualification pass (quality table in
  [`BENCHMARKS.md`](BENCHMARKS.md)).
- **EXP-005–007 — frozen agent-shaped MTP depth campaign.** Each lane ran MTP0/3/5/7 with one
  unchanged binary, model, corpus, seed, and greedy request configuration. The v3 output projection
  hashes client-visible answer, reasoning, reasoning-summary, and tool-call content. Analysis
  revision 3 requires exact within-arm repetition, one shared non-null campaign identity, and a
  separate fresh-process MTP0 control before cross-arm attribution. The original traces predate the
  latter two controls, so all three lane decisions are inconclusive. Within-process observations
  remain: MTP0 changed on 1/12 repeated steps on RTX 5090 and 10/12 on RTX 4090; RTX 3090 arms
  repeated exactly, while MTP3/5/7 differed from MTP0 on 6/8/4 outputs. These observations do not
  establish a draft-depth effect. No public profile changed. Receipts:
  [5090](measurements/2026-09-04-rtx5090-mtp-agent-ablation.json) ·
  [4090](measurements/2026-09-04-rtx4090-mtp-agent-ablation.json) ·
  [3090](measurements/2026-09-04-rtx3090-mtp-agent-ablation.json). The generated public corpus and
  frozen build identities are [recorded separately](measurements/2026-09-04-mtp-agent-corpus.json)
  ([builds](measurements/2026-09-04-mtp-ablation-builds.json)).

## Current order

The backlog below is a pool; the program's order is fixed in [`ROADMAP.md`](../ROADMAP.md). The
MTP campaign is measured, but no lane can support a depth decision until a campaign-bound rerun
includes a separate fresh-process MTP0 control. Stable lanes then need first-divergence inspection,
especially RTX 3090. Only after that exact-output boundary closes does the `nvfp4` artifact swap
become the next v0.4-class requalification decision.

## Ideas backlog

Open, unclaimed, or in-flight. Claim one by opening an issue in
[alphastorm/ninfer](https://github.com/alphastorm/ninfer/issues) titled `perf: <idea>` with your
hypothesis and method before writing code.

| Idea | Why it should work | Status |
| --- | --- | --- |
| Fuse Q4/Q5 GEMV/MMA epilogues with adjacent normalization | Removes a full activation round trip per layer at decode shapes | open |
| Qualify a speculative (MTP) profile on the RTX 4090 lane | Shipped in v0.3.1: MTP3 promoted by the two-arm decision (+17.04% Golden-equivalent wall; 93.2–97.7 tok/s vs 52.330 baseline); exploratory sweep measured draft-3 > 4 > 5 on the fixed workload | shipped v0.3.1 |
| Durable RTX 5090 container (serve-layer session persistence) | Shipped in v0.4.0: transactional generational store + io_uring O_DIRECT restore; 109,589 tokens restored hot across a docker restart ([qualification](../docs/measurements/2026-08-30-rtx5090-durable-qualification.json)) | shipped v0.4.0 |
| Checkpoint replication to shared storage | Native IO paths require local filesystems; replicate immutable SHA-manifested generations (copy out, copy back before restore); same-profile-pair portability only | open |
| Template-fork warm starts | Checkpoint immediately after system-prompt+context prefill and fork subagents from that generation for hot starts; operational pattern over the qualified fork contract | open |
| Paged host-to-device KV prefetch beyond 262K tokens | Extends usable context past resident KV capacity without a quality change | open |
| Durable session checkpoints → process-restart continuation | All three lanes bind passing restart evidence: 102K restored continuation on RTX 4090, 310 MB checkpoint restoration on RTX 3090, and a 109K-token hot restore across an RTX 5090 container restart | released on all three lanes |
| MTP depth-and-corpus ablation for Qwen3.8 | Measured on 2026-09-04 with one binary and model per lane and a deterministic 24-request agent corpus. All decisions are inconclusive until a shared campaign ID and fresh-process MTP0 control bind every lane | measured; controlled rerun next |
| DFlash-style deeper drafting (k=7) on 27B | K7 completed on all lanes. Observed K7/K3 raw decode rates were 130.19/172.94, 88.57/110.95, and 50.68/65.36 tok/s on RTX 5090/4090/3090; absent campaign/cross-process controls, these comparisons do not establish a depth effect | inconclusive |

## Contributing a result

1. **Claim** the idea in an issue (`perf: <idea>`), with hypothesis and measurement plan.
2. **Measure** with the scripted lane or the runtime bench harness (`ninfer_bench`,
   `run_serve_corpus.py`, `run_serve_concurrency.py`, `ninfer_linear_bench` — see the runtime
   repo's bench documentation). Fixed seeds, warm-up, and repetitions are part of the method.
3. **Preserve the packet.** NCU/NSYS/timing outputs plus a summary with exact source commit,
   artifact hash, and settings.
4. **Prove the contract.** Ops follow the runtime repo's admission rules: central `ops/` layer,
   semantically closed contracts, FP64 oracles, and roofline calibration. An optimization PR
   without an oracle test is not reviewable.
5. **Report honestly.** Negative and inconclusive results are ledger entries too; they are how a
   distributed group avoids repeating dead ends.

Product-level throughput submissions (whole-appliance numbers rather than kernel work) go through
the [performance result form](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml)
and the [community results table](BENCHMARKS.md#community-results).
