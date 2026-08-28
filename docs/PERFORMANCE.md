# Performance program

The shipped profile is the floor, not the ceiling. This page is the public working surface for
kernel and schedule optimization on the qualified RTX 5090 runtime: the measured baseline, the
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

One RTX 5090 (`sm_120a`), shipped v0.1 profile — Qwen3.8-27B `groupwise-int`, BF16 KV, MTP3,
1,024-token prefill chunks, one active request
([receipts](../releases/v0.1.0-beta.1/qualification.json)):

| Metric | Value |
| --- | --- |
| Decode throughput | 209.04 tok/s |
| MTP3 acceptance | 77.0% (799/1,038) |
| 130,048-token prompt round trip | 58.5 s |
| Largest observed warm-request prefix hit | 37,591 tokens, zero recompute |

Hardware envelope, measured with the runtime repo's `hbm_bandwidth_probe`: **1,674.5 GB/s**
sustained pure-read HBM bandwidth on this RTX 5090 — 93.4% of the 1,792 GB/s theoretical peak.
Single-request decode of a memory-bound quantized model lives against that roofline; that is the
number kernel work is judged against.

## The profiling lane

Branch
[`perf/scripted-sm120-mtp3-profiling`](https://github.com/alphastorm/ninfer/tree/perf/scripted-sm120-mtp3-profiling)
in the runtime repo turns one-off profiling into reproducible packets:

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
refer to the runtime repositories. As of 2026-08.

| ID | Area | Hypothesis | Result | Verdict |
| --- | --- | --- | --- | --- |
| EXP-001 | Q4 SwiGLU decode/verify | A small-T MMA path can verify 4 speculative tokens for near-GEMV latency | `M=1` GEMV 76.77 µs at 1,258.7 GB/s; `M=4` MMA 94.21 µs at 1,026.8 GB/s; 1.227× latency for 4 tokens | kept |
| EXP-002 | Q5 linear+add post-mixer | A CTA-collective `mma-r64-c16` kernel beats SIMT split-2 | Candidate 190.46 µs vs production 51.20 µs — 3.72× slower | rejected |
| EXP-003 | GDN state under speculation | Caching gate activations (ReplaySSM) removes recurrent-state drift on MTP rollback | Bit-identical recurrent fold at 167.82 µs/layer; no drift across long contexts | kept |
| EXP-004 | Tensor-core prefill | W4A4 MMA prefill (NVFP4 artifacts) multiplies prefill throughput | 11,191 vs 3,218 tok/s at a 7,680-token prompt — 3.48× (upstream campaign, NVFP4 profile) | kept upstream |

Entry detail:

- **EXP-001 — MTP3 verification economics.** Nsight Compute packets on the `sm_120a` Q4 SwiGLU
  pair kernels show decode (`M=1`) already at 75.2% of the measured read peak, and the 4-token
  verification batch moving the same bytes. Conclusion: speculative verification is
  bandwidth-amortized; acceptance rate, not verify cost, is the lever. Packets:
  `profiles/` on the profiling branch.
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

## Ideas backlog

Open, unclaimed, or in-flight. Claim one by opening an issue in
[alphastorm/ninfer](https://github.com/alphastorm/ninfer/issues) titled `perf: <idea>` with your
hypothesis and method before writing code.

| Idea | Why it should work | Status |
| --- | --- | --- |
| Fuse Q4/Q5 GEMV/MMA epilogues with adjacent normalization | Removes a full activation round trip per layer at decode shapes | open |
| DirectStorage-style weight paging on the 5090 lane | The [ninfer-4090](https://github.com/UDPSendToFailed/ninfer-4090) port measured 10.1 GB/s cold weight DMA, cutting cold TTFT from 52.6 s to 1.86 s on its profile; a Linux/WSL2 analogue exists as branch `port/nyc-5090-directstorage` | in flight |
| Paged host-to-device KV prefetch beyond 262K tokens | Extends usable context past resident KV capacity without a quality change | open |
| Durable session checkpoints → process-restart continuation | The 4090 lane has measured disk-checkpoint restores of 105K-token sessions in well under a second of prepare time (receipt publishes with that lane); branch `feat/durable-session-checkpoints` tracks the 5090 runtime | in flight |
| MTP acceptance modelling for Qwen3.8 | Upstream measured 48.9% acceptance on `nvfp4` vs 77.0% qualified here on `groupwise-int`; understanding the quant/acceptance interaction could recover decode throughput on faster-prefill artifacts | open |
| DFlash-style deeper drafting (k=7) on 27B | Upstream measured 764–786 tok/s at 65–66% acceptance on 35B-A3B with DFlash; unknown economics on dense 27B | open |

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
the [benchmark report form](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml)
and the [community results table](BENCHMARKS.md#community-results).
