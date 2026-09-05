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
| EXP-005 | RTX 5090 agent-shaped MTP depth | MTP3 remains the best depth on agent-shaped work | K0/3/5/7: 81.57/172.94/149.47/130.19 decode tok/s; K5 and K7 lost to MTP3 in both repetitions | kept |
| EXP-006 | RTX 4090 agent-shaped MTP depth | MTP3 remains the best depth on agent-shaped work | K0/3/5/7: 51.46/110.95/102.87/88.57 decode tok/s; K5 and K7 lost to MTP3 in both repetitions | kept |
| EXP-007 | RTX 3090 agent-shaped MTP depth | MTP3 remains the best depth on agent-shaped work | K0/3/5/7: 36.18/65.36/57.95/50.68 decode tok/s; K5 and K7 lost to MTP3 in both repetitions | kept |
| EXP-008 | RTX 5090 `nvfp4` artifact | The NVFP4 Qwen3.8 artifact beats the pinned `groupwise-int` artifact on agent-shaped session time | Does not start with BF16 KV at 131,072 context (3.28 GB larger weights); with INT8 KV: prefill 6,089 vs 2,740 tok/s (2.22×), decode 168.23 vs 174.25 tok/s (−3.5%), modeled session time −15.5% to −28.7%; role-corpus screen: fewer canary leaks (4 vs 8) but evidence precision −2.4 pp and unsupported-claim rate +2.2 pp | rejected for v0.4; v0.5 RTX 5090 candidate |
| EXP-009 | RTX 5090 KV format and prefill chunk | INT8 KV or a 2,048-token prefill chunk improves the BF16/1,024 incumbent | INT8 KV: +0.0% to +0.8% session time, 4.2 GB lower peak VRAM, worse role-corpus screen on every metric; chunk 2,048: −0.1% to −0.9% | rejected |
| EXP-010 | RTX 4090 prefill chunk | A larger prefill chunk than the shipped 512 improves session time on `rk2v4-e8` | Chunk 512/1,024/2,048/4,096: prefill 1,605/1,877/1,971/1,974 tok/s, decode 110.69/111.82/112.92/108.37 tok/s; 2,048 clears the 5% margin in every repetition (+5.5% to +12.8%), 1,024 and 4,096 do not | kept — requalify at 2,048 |
| EXP-011 | RTX 3090 prefill chunk and context | The shipped INT8/1,024/65,536 profile leaves speed or capacity on the table | Chunk 512/2,048: −2.9% to −0.5%; `--max-context 131072` fits with automatic KV capacity 131,072 at 22,465 MiB peak and identical throughput (65.08 vs 65.69 decode tok/s) | kept — qualify 131,072 context |
| EXP-012 | Template-fork warm starts (all lanes) | Checkpointing a prefilled template and forking subagents from it starts them hot, including across a process restart | RTX 5090 (57.9K-token template): device-resident sibling forks alternate 1.3 s / 22.5 s (anchor / full re-prefill) while a 67.7K template gives four 1.3 s forks; after restart the 4.51 GB checkpoint restores in ≈23.6 s ≈ the 21.8 s cold prefill. RTX 4090: no sibling reuse (41–47 s per fork) and a 1.13 GB restore takes ≈130 s vs a 41 s prefill. RTX 3090: no sibling reuse (49–51 s) and restore ≈91 s vs 49 s | negative; hot forks only on the 5090 and only reliably ≥ ~64K tokens; restore never beats re-prefill |
| EXP-013 | RTX 5090 fanout anchor retention | The sub-64K alternation is a serve policy defect fixable in source | Capacity, not policy: private catalog 2 entries + 2 device-state slots; search-cap and marker source changes rejected on the probe; `--max-private-continuations 8 --device-state-slots 4 --host-state-slots 24` on the unchanged binary gives 12/12 anchor hits at 57.9K, 67.7K, and loaded 57.9K for 0.43 GiB slack | kept — v0.4.8 RTX 5090 candidate profile |
| EXP-014 | Native-lane checkpoint restore | The slow restore is a first-read effect that a second restore avoids | Second restore not faster (4090 132.8 → 149.0 s at 1.13 GB; 3090 91.8 → 92.2 s at 1.68 GB); status endpoint blocked for the whole restore; restore path is the cost | open — filed upstream |

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
  unchanged binary, model, corpus, seed, and greedy request configuration. MTP3 was fastest on all
  three lanes and in both repetitions. K5/K7 trailed it by 13.57%/24.72% on RTX 5090,
  7.29%/20.17% on RTX 4090, and 11.34%/22.46% on RTX 3090, so analysis revision 5 retains the
  qualified MTP3 incumbent and rejects deeper drafting for these artifacts. The v3 output
  projection also exposed baseline nondeterminism: MTP0 changed on 1/12 repeated steps on RTX 5090
  and 10/12 on RTX 4090, while RTX 3090 repeated exactly and its MTP3/5/7 outputs differed from
  MTP0 on 6/8/4 requests. Missing campaign and fresh-process controls leave that exact-output
  attribution unresolved; they do not erase the no-change throughput decision. No public profile
  changed. Receipts:
  [5090](measurements/2026-09-04-rtx5090-mtp-agent-ablation.json) ·
  [4090](measurements/2026-09-04-rtx4090-mtp-agent-ablation.json) ·
  [3090](measurements/2026-09-04-rtx3090-mtp-agent-ablation.json). The generated public corpus and
  frozen build identities are [recorded separately](measurements/2026-09-04-mtp-agent-corpus.json)
  ([builds](measurements/2026-09-04-mtp-ablation-builds.json)).
- **EXP-008–011 — per-lane runtime variant campaign (2026-09-04).** One campaign identity, one
  fresh server process per arm, the frozen 24-request agent corpus, and the shipped lane profile
  as an in-campaign incumbent (verified against each host's installed configuration). The primary
  metric is modeled session engine seconds from measured prefill and decode throughput against
  two recorded session shapes (573,956 prefill / 30,936 decode tokens and 1,543,555 prefill /
  193,440 decode tokens); both shapes come from RTX 5090 production logs and are applied to every
  lane, so the 4090 and 3090 figures weight 5090 token mixes with their own measured rates.
  Promotion needs a 5% improvement for every reference in every repetition, the lane's qualified
  context in automatic KV capacity, and a passing quality gate. Arms that change the artifact or
  KV format also ran the private 89-case role corpus against the incumbent's own run (84 effective
  cases: the five JSON-schema cases are rejected by contract on every arm), and a repeated screen
  reproduced every aggregate metric exactly across fresh processes
  ([repeatability](measurements/2026-09-04-rtx5090-quality-repeatability.json)), so its
  differences are systematic on this corpus; whether a two-case shift generalizes is a corpus-power
  question the screen cannot answer. Results: the RTX 5090 retains `groupwise-int`/BF16/MTP3. The
  causal chain for `nvfp4` is: the weights are 3.28 GB larger → BF16 KV at 131,072 context no
  longer fits in 32 GB (the engine refuses its 10.41 GB runtime reservation) → the only way to run
  it on this card is INT8 KV → INT8 KV alone (`gw-int8`, same artifact as the incumbent) regresses
  every screen criterion, while `nvfp4` on INT8 KV halves long-prefix TTFT (11.7 s → 5.1 s on a
  35K-token prefix) and lands better than `gw-int8` on every criterion but still two cases behind
  the BF16 incumbent on grounding. `nvfp4` was therefore never measured against a BF16 reference;
  the 2.22× prefill and 15.5–28.7% modeled session gain would be back on the table with more VRAM
  or a smaller NVFP4 artifact. The RTX 4090 promotes prefill chunk 2,048 (TTFT 21.9 s → 17.7 s on
  the same prefix, +270 MiB peak): the stable signal there is prefill (1,605 → 1,877 → 1,971 tok/s,
  reproducible to 0.3% within each arm), while decode on that lane varies about 4.7% between the
  incumbent's own repetitions, which is why chunk 1,024 (+4.2% minimum) fell short of the margin
  and 2,048 (+5.5% minimum) cleared it — larger chunks help this lane and 2,048 measured best,
  with 4,096 flat on prefill and lower on decode. The RTX 3090 keeps its profile and gains a
  measured 131,072-token capacity finding. INT8 KV on the RTX 4090 was faster (+8.8% to +13.3%)
  but peaks at 23,180 of 24,564 MiB and fails the same screen. Receipts:
  [5090](measurements/2026-09-04-rtx5090-variant-campaign.json) ·
  [4090](measurements/2026-09-04-rtx4090-variant-campaign.json) ·
  [3090](measurements/2026-09-04-rtx3090-variant-campaign.json); arm matrix, artifact facts, and
  the recorded gate amendment: [arms](measurements/2026-09-04-variant-campaign-arms.json). Runner:
  [`scripts/run_variant_campaign.py`](../scripts/run_variant_campaign.py) with host launchers in
  [`scripts/hosts/`](../scripts/hosts/).
- **EXP-012 — template-fork warm starts (2026-09-04).** [`scripts/fleet_probe.py`](../scripts/fleet_probe.py)
  now forks from the template id after the restart as well, verifies the restart through the
  lane's cumulative prefill counter, and waits for the RTX 4090's automatic save where no explicit
  save exists. Measured on the shipped lanes: the RTX 5090 (v0.4.6 container) prefills a
  57,853-token template in 21.8 s, saves it explicitly in 13.0 s (4,505,854,444 bytes), and serves
  stored sibling forks at 1.38 / 22.50 / 1.26 / 22.71 s — the server records `private_long_anchor`
  then `root` alternately, with `private_catalog capacity 2, occupied 2`; the same probe against
  the retained v0.4.4 container reproduces the alternation
  ([bisect](measurements/2026-09-04-template-fork-rtx5090-v044-bisect.json)), a 67,681-token
  template gives four anchor hits at 1.25–1.39 s
  ([67K](measurements/2026-09-04-template-fork-rtx5090-67k.json)), and unstored forks give three
  of four ([unstored](measurements/2026-09-04-template-fork-rtx5090-unstored-forks.json)), so the
  loss is a serve/engine anchor-retention policy below roughly 64K tokens, not an image
  regression. After a verified restart (57 s to ready) the first continuation restores the
  checkpoint before request timing starts (server TTFT 0.41 s, client wall 24.7 s ≈ 190 MB/s),
  which equals the cold prefill, and template forks alternate again. The RTX 4090 (durable v0.2
  service) saves automatically 6.5 s after the turn (1,130,468,708 bytes), serves every sibling
  fork as `full_reset` (41–47 s), and restores in ≈130 s of client wall (server TTFT 0.26 s) against
  a 41.2 s prefill; the RTX 3090 (38,215-token template) saves explicitly in 10.0 s, serves forks
  as `full_reset` (49–51 s), and restores in ≈91 s against a 49.3 s prefill. Warm starts therefore
  exist today only as device-resident forks on the RTX 5090; disk restore is slower than
  re-prefill on every lane and 10–15× slower per byte on the native lanes than in the container.
  Receipts: [5090](measurements/2026-09-04-template-fork-rtx5090.json) ·
  [4090](measurements/2026-09-04-template-fork-rtx4090.json) ·
  [3090](measurements/2026-09-04-template-fork-rtx3090.json).
- **EXP-013 — fanout anchor retention on the RTX 5090: diagnosis and configuration fix
  (2026-09-05).** The alternation in EXP-012 is capacity, not policy. Status counters sampled
  between forks show `private_evictions` rising by exactly one per completed stored fork against a
  private catalog of two entries (the default is 2 × concurrency) backed by two device-state slots,
  and the cold forks' planner diagnostics record a 477 s incumbent with the anchor subtree still
  queued at a 28 s lower bound. Two source changes were built and rejected on the same probe:
  raising the planner's 5 ms search cap to 50 ms only changed the stop reason
  (`value_of_next_expansion` after 354 targets, same decision), and marking only the inherited
  frontier on stored continuations only shifted the phase (cold / hot / cold / hot).
  `--max-private-continuations 8` alone fixed 57.9K and then lost all four forks of a following
  67.7K template in the same process (`host_state 8/8` saturated, predicted materialization
  ≈600 s). With the backing slots scaled — `--max-private-continuations 8 --device-state-slots 4
  --host-state-slots 24` on the unchanged shipped v0.4.6 binary — one container served 12/12
  anchor hits across 57.9K, 67.7K, and a loaded-catalog 57.9K (1.2–1.6 s per fork; one hit paid a
  4.27 s state materialization) for 0.43 GiB of startup slack (3.56 → 3.13 GiB, headroom kept at
  1.00 GiB) and 28,632 MiB after twelve forks vs 28,125–28,195 MiB on the shipped profile, with
  automatic KV capacity unchanged at 131,072. That configuration is the v0.4.8 RTX 5090 candidate
  profile; its acceptance receipt is this probe at both template sizes in one process. Filed as
  [alphastorm/ninfer#35](https://github.com/alphastorm/ninfer/issues/35). Receipt:
  [configuration sweep](measurements/2026-09-05-fanout-anchor-configuration-sweep-rtx5090.json).
- **EXP-014 — checkpoint restore path on the native lanes (2026-09-05).**
  [`scripts/restore_probe.py`](../scripts/restore_probe.py) restores one session across two
  verified restarts while polling the checkpoint status endpoint. The second restore is not
  faster (RTX 4090: 132.8 s then 149.0 s for 1.13 GB, ≈8.5 MB/s; RTX 3090: 91.8 s then 92.2 s for
  1.68 GB, ≈18.5 MB/s), so page cache and first-read effects are excluded and the restore path
  itself is the cost; the status endpoint stops answering for the whole restore on both lanes;
  neither train logs restore progress. The RTX 4090's own qualification recorded a 120K-token
  restore in 7.0–10.8 s on the same release identity, which is the first discrepancy to
  establish. No IO-path change was made; filed with the numbers as
  [alphastorm/ninfer#36](https://github.com/alphastorm/ninfer/issues/36). Receipts:
  [4090](measurements/2026-09-05-restore-probe-rtx4090.json) ·
  [3090](measurements/2026-09-05-restore-probe-rtx3090.json).

## Current order

The backlog below is a pool; the program's order is fixed in [`ROADMAP.md`](../ROADMAP.md). The
MTP campaign retains MTP3 and rejects K5/K7 for the current artifacts. The per-lane variant
campaign closed the `nvfp4` question for the v0.4 train (rejected on the RTX 5090 because the
card forces INT8 KV; NVFP4 W4A4 needs Blackwell tensor cores, so the `sm_89`/`sm_86` lanes are
out of scope and the 4090 upstream removed its NVFP4 path) and produced two configuration-only
lane changes to requalify: RTX 4090 prefill chunk 2,048 and RTX 3090 context 131,072. Each lane
now carries its own best measured stack rather than one shared configuration.

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
| MTP depth-and-corpus ablation for Qwen3.8 | Measured on 2026-09-04 with one binary and model per lane and a deterministic 24-request agent corpus; MTP3 won on every lane and repetition | completed; retain MTP3 |
| DFlash-style deeper drafting (k=7) on 27B | K7 completed on all lanes but trailed MTP3 by 20.17–24.72% | rejected for current artifacts |
| RTX 5090 `nvfp4` artifact swap | Measured on 2026-09-04: 2.22× prefill and −3.5% decode with INT8 KV, refuses to start with BF16 KV at 131,072 context; two-case grounding shift on the private screen | rejected for v0.4; v0.5 candidate with INT8 KV |
| RTX 4090 prefill chunk 2,048 | Measured on 2026-09-04: +22.8% prefill, +2.0% decode, +270 MiB peak, session time +5.5% to +12.8% against the shipped 512; 4,096 regresses decode | kept; requalify |
| RTX 3090 131,072-token context | Measured on 2026-09-04: automatic KV capacity 131,072 at 22,465 MiB peak with unchanged throughput on the shipped INT8 profile | kept; qualify |
| INT8 KV on the RTX 5090 and RTX 4090 lanes | No session-time gain on the RTX 5090 (4.2 GB VRAM headroom only); +8.8% to +13.3% on the RTX 4090 at 23,180 of 24,564 MiB peak; worse role-corpus screen on both | rejected |

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
