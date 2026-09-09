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
| EXP-013 | RTX 5090 fanout anchor retention | The sub-64K alternation is a serve policy defect fixable in source | Capacity, not policy: private catalog 2 entries + 2 device-state slots; search-cap and marker source changes rejected on the probe; `--max-private-continuations 8 --device-state-slots 4 --host-state-slots 24` on the unchanged binary keeps 12/12 forks on the anchor path at 57.9K, 67.7K, and loaded 57.9K for 0.43 GiB slack, at the cost of one 5.29 s (vs 1.39 s) first fork at 67.7K | kept — v0.4.8 RTX 5090 candidate profile, as a trade |
| EXP-014 | Native-lane checkpoint restore | The slow restore is a first-read effect that a second restore avoids | Second restore not faster (4090 132.8 → 149.0 s at 1.13 GB; 3090 91.8 → 92.2 s at 1.68 GB); status endpoint blocked for the whole restore; restore path is the cost | open — filed upstream |
| EXP-016 | Fleet routing (all lanes) | Splitting a fixed independent-job batch across lanes completes it faster than the RTX 5090 alone | 14-job frozen corpus: 5090 alone 66.8 s; 5090+4090 51.2 s naive / **43.4 s** cost-aware (1.54×); three lanes 47.2 s naive / **32.3 s** cost-aware (2.07×); role-pinned 100.3 s (0.66×). Long-prefill jobs are 3.3–6× more expensive off the 5090; short jobs cost the same everywhere | kept — measured boundary for the fleet configuration; cost-aware dispatch is the recommended policy |
| EXP-017 | Native-lane checkpoint restore path | The per-page-segment reader, not the disk, is the restore cost; one read per staging window closes it | Fix on both native lanes, same session shapes as EXP-014: RTX 4090 1.13 GB **146.6 → 5.6 s** and **133.4 → 5.6 s** (24–26×); RTX 3090 1.68 GB **91.8 → 10.8 s** and **92.2 → 10.7 s** (8.5×); planted ledger keys quoted exactly after every restart on both lanes and in-process | fixed at source — lane commits `d22ce3fd` (4090) and `3756db6e` (3090); shipped in `v0.4.9` (components `v0.2.2-qwen38-4090-durable.1`, `v0.2.4-qwen38-3090-beta.1`) |
| EXP-018 | Checkpoint replication (all lanes) | A checkpointed session survives the machine losing its local state, and a replica cannot be forged | Export, carry off, destroy the local copy with the server stopped, carry back, import, restart, exact retrieval of planted keys: RTX 5090 4.5 GB import 10.1 s / restored 24.8 s; RTX 4090 1.13 GB 4.2 s / 7.4 s; RTX 3090 1.69 GB 11.9 s / 11.5 s. Payload byte flip refused by the tool; manifest edit with consistent digests quarantined by the runtime's origin authentication (no resurrection) | delivered — roadmap v0.5 §1; origin authentication ported to both native lanes and requalified |
| EXP-019 | Replica transport (cross-site) | Moving a replica between owner sites is minutes, and the earlier 1.8–3.5 MB/s was the workstation's transpacific path plus single-stream ssh | Full round trip NYC→SF→NYC→restore on the 67 ms tailnet path: 1.13 GB out at **11.5 MB/s**, back at **56.3 MB/s**, imported in 2.6 s, planted keys exact after the return. Windows OpenSSH cannot carry bulk between two Windows hosts at all; a Linux receiver on the same link is 5× faster than a Windows one | fixed — `scripts/hosts/pscp.py` (ranged ssh reads, or bearer-token ranged HTTP for the Windows-to-Windows case); host ssh compression, the WSL sshd port collision, and fleet host-to-host trust corrected |
| EXP-020 | NAS replication target | A LAN-local NAS is a better replication target than another workstation, and a Synology's tailnet path is not | Same-site LAN, 2 GiB incompressible, raw unbuffered IO: the RTX 4090 host **115.8 MB/s** write / **117.6 MB/s** read, the RTX 3090 host 96.0 / 102.3 - about 1 GbE line rate. The same NAS over the tailnet from the other site does **6.4 MB/s** write / 22.7 MB/s read, worse than the direct host-to-host path (11.5 / 56.3). One published generation replicated and verified in place from each co-located lane | adopted as the replication target for the two co-located lanes; the remote lane keeps host-to-host transport |
| EXP-021 | Warm arrival after a restart (5090) | A restored session's first sibling fork reuses the template prefix instead of re-prefilling it | Two source defects found and fixed: a fanout fork left its long anchor on the parent, so every checkpoint taken after a fanout omitted it (payload 4,351,909,712 vs 4,505,864,319 bytes), and consuming a session endpoint double-charged a shared anchor to the entitlement (HTTP 500 on resume, now 1.19 s). With the fixes a fork issued as the first post-restart request hits `private_long_anchor` immediately; when an endpoint resume comes first, one fork still re-prefills (22.2 s) | partial - fixes proved on a candidate binary on branch `feat/warm-arrival`, not released; the resume-first path and the hash-bound 24 s restore remain open |
| EXP-022 | Warm arrival, resume-first (5090) | The remaining re-prefill after an endpoint resume is a candidate-admission defect | Not admission: anchor replacement. A continuation keeps two long anchors and every Responses request captures two (inherited and pre-generation frontier), so a continuing turn replaced both, and the victim rule (lowest frontier first) evicted the template anchor every sibling reuses; the resume at 67.9K left the next fork on `root` (28.5 s). Replacement now evicts the anchor whose loss costs the least re-prefill (smallest gap to its lower neighbour, ties to the newer). After a restart, resume then two forks: **4.2 s / 2.9 s / 1.3 s**, both forks `private_long_anchor`; fork first: 3.7 s / 1.3 s. Restore plus the sequence is 8.4 s and 6.7 s against 26.7 s for not checkpointing at all | fixed at source - branch `feat/warm-arrival` commit `fb9b35da`; roadmap v0.5 §2 holds on the candidate |
| EXP-023 | Checkpoint restore cost (5090) | Restore is hash-bound: two scalar SHA-256 passes over 5 GB at queue depth one | Scalar SHA-256 measured at 0.33 GB/s on the appliance's Zen 4 against 2.66 GB/s with the SHA extensions; the load pass was dropped (the streamed hash on the exact bytes the engine consumes is the single verification, `alphastorm/ninfer#21` closed by construction), the io_uring reader issues eight 4 MiB reads per batch on its own thread, and the next 32 MiB batch is on the device while the previous one hashes. A 5.2 GB session restores in **3.8 s / 3.8 s** (was 24-27 s), planted keys exact after both restarts; a flipped byte in the middle of the 4.4 GB KV payload is refused (404 `previous_response_not_found`, 2.8 s), the generation reports `corrupt`, then quarantines | fixed at source - commits `f841d42d`, `d956e6d6`; verified-or-refused re-proven live |
| EXP-024 | RTX 5090 requalification (v0.5.1 candidate) | The warm-arrival and restore changes hold under the lane's own qualification gates on the canonical build | Appliance-local build of `d956e6d6` (binary `71edc2f6`, 9/9 host tests, packaged with SBOM, published as `v0.5.1-qwen38-5090-beta.1` and wrapped by the runtime-image workflow into `12ef2d9e...`, whose binaries measure byte-identical) on the unchanged v0.4.8 arguments, started through the lifecycle tool from the published image (configuration `efacac23...`): exact 130,048-token retrieval at 2,180 tok/s cold (v0.4.8: 2,207), 2,048-token decode at 138.2 tok/s with 41.2% MTP acceptance (136.0), agent protocol with no resurrection across restart; fanout 24/24 forks on `private_long_anchor` across 57.9K, 67.7K, and 80.0K templates in-process and after a verified restart with the resume first (post-restart forks 1.25-1.41 s; v0.4.8 paid 22.2 s on the first); warm arrival in both orders with an in-process control; 4.5 GB explicit save 4.4 s (was 12.6 s, the writer's digest also runs on the SHA extensions) | passed - `v0.5.1` staged with the published component; external acceptance and the product cut remain |
| EXP-025 | Native lanes on mainline (4090, 3090) | The mainline runtime - context cache, warm arrival, streamed restore - serves the two native Windows lanes at least as well as their divergent branches | `port/native-lanes-on-mainline` built with MSVC 19.44 for `sm_89` and `sm_86`, 100/100 registered tests on each build on the Ada GPU (94 run; the six real-artifact and external-tokenizer suites skip), and served in candidate windows on both hosts. Same fixture, gates, host, and day as the installed releases: RTX 4090 130,048-token exact retrieval **86.8 s vs 97.5 s** (1,499 vs 1,333 tok/s), 2,048-token decode **103.8 vs 88.4 tok/s** wall; RTX 3090 **208.6 vs 219.5 s** and **60.3 vs 52.8 tok/s**. 67.7K template: four sibling forks hot at 1.8-2.0 s (4090) / 2.5-2.9 s (3090) before a restart and 1.8-1.9 s / 2.5-2.6 s after it, every fork `private_long_anchor`; warm arrival in both orders; a 2.9 GB checkpoint restores in 4.2-5.0 s (4090) and 16.6-17.1 s (3090) with a flipped byte refused and quarantined. Five source defects surfaced only on the hardware (cooperative grids sized for 170 SMs, an INT8 prompt-attention CTA that spilled 200 B/thread on `sm_89`, a serialising DirectStorage read queue that failed every streamed restore, an unlogged restore refusal, an unbounded residency query). The RTX 4090's WDDM budget at 131K INT8 leaves 169 MiB with four device-state slots and the driver pages: decode 47 tok/s and every fork 2.5× slower; two slots (463 MiB free) is the profile, one slot re-prefills the first fork | kept - both lanes' next candidates build from mainline; requalify each through its lifecycle tool before any release |
| EXP-026 | Native lane release qualification (4090, 3090) | The mainline-built native lanes pass their own lifecycle qualification end to end from a clean state | Five blockers in the release path found, reproduced, and fixed: the mainline bench had no `--version` arm the package's identity binding requires; `transfer_install` relayed the 0.6 GB package through the operator's Mac (0.33 MB/s, 900 s timeout) instead of host to host (**104.7 MB/s**, 16 ranged-HTTP streams); the staging root inherited `BUILTIN\Users` write access on the host whose qualification parent did not exist yet; the managed install splatted its arguments positionally; and mainline applied `X-NInfer-Session` only on the bodyless Responses routes, so the lane probe's identity conflict returned 200. Both lanes now pass preflight through install and reach `protocol`. The RTX 4090 lane's pinned pools are sized from measurement: 24 host state slots with the 8 GiB default Host KV is 13.3 GB pinned and failed `cudaMallocHost` on two managed starts (the controller's 18 GB pre-launch read empties the free list), 4 GiB is 9.2 GB and starts; 8 slots start but fail the protocol contract in 41 s | in flight - one open runtime invariant defect (a catalogued continuation's last state replica is evictable while admission plans reuse from it) and the RTX 3090 host offline |
| EXP-015 | Lane requalification (all lanes) | The three configuration-only changes hold their measured gains under each lane's own qualification gates | RTX 4090 chunk 2,048: 102,060-token session 68.0 s vs 84.9 s shipped, protocol/persistence/golden unchanged. RTX 3090 131,072 context: exact 130,048-token retrieval in 218 s, 90.2 decode / 890.7 prefill tok/s at 300.4 W, 22,548 MiB peak. RTX 5090 context-cache profile: 130,048-token prefill 2,207 tok/s cold, 136.0 decode tok/s at 41.2% MTP acceptance, 4/4 anchor hits at 57.9K and 67.7K, 4.5 GB save, verified restart; first post-restart fork re-prefills once | kept — `v0.4.8` draft staged; publication blocked on component releases and external acceptance |

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
  --host-state-slots 24` on the unchanged shipped v0.4.6 binary — one container kept 12/12 forks
  on the anchor path across 57.9K, 67.7K, and a loaded-catalog 57.9K (11 under 2 s; the first
  67.7K fork paid a 4.27 s state materialization for 5.29 s wall against 1.39 s on the shipped
  default at that size) for 0.43 GiB of startup slack (3.56 → 3.13 GiB, headroom kept at
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
- **EXP-015 — lane requalification of the three configuration changes (2026-09-05).** Each lane
  reran its own qualification tooling with the changed configuration. RTX 3090: the 14-phase
  orchestrator (`tools/qualification/qualify_rtx3090.py`, long-context stage rebound to the
  130,048-token `long_niah_128k` fixture) built `v0.2.3-beta.1` from commit `2ce6c9dc` on the
  builder host, packaged it deterministically, installed it beside the shipped release, and
  passed protocol 15/15, exact 128K retrieval in 218.2 s, restart (310,212,985-byte checkpoint,
  45 cached tokens, PID replaced), two-direction rollback, security, the OMP read-tool run, and
  managed C1 (90.23 decode / 890.72 prefill tok/s, 93.43% MTP, 300.38 W, 22,548 MiB), then
  restored the 370 W owner state. RTX 4090: commit `b9c4636b` rebuilt the code-identical binary
  with the new patch-stack identity in 40 s (incremental), `New-Package.ps1` assembled
  `v0.2.1` (`1c66f7d5`), the installer placed it beside `v0.2.0` with the inherited operator
  GPU-owner adapter, and `Invoke-Qualification.ps1 -Profile MTP3` passed protocol, the
  102,060-token session (68.0 s first turn vs 84.9 s shipped; post-restart 225.6 s, unchanged),
  persistence (`append_frontier`, 102,075 tokens), and the OMP golden run in 6m44s. RTX 5090:
  the lifecycle tool started the candidate with the canonical configuration `95765a38` on the
  shipped image; [`scripts/qualify_rtx5090_profile.py`](../scripts/qualify_rtx5090_profile.py)
  measured exact 130,048-token retrieval cold (58.9 s server prefill, 2,207 tok/s, 28,558 MiB
  used), 2,048-token decode at 136.0 tok/s (41.2% MTP acceptance, 2.24 tokens/round, byte-identical
  across five runs), and the fork/delete/no-resurrection arc across a `docker restart`;
  `fleet_probe.py` then held 4/4 anchor hits at 57.9K (1.36/1.22/1.22/1.20 s) and 67.7K
  (1.43/1.30/1.37/1.39 s) in one process with a 4.5 GB explicit save and a verified restart.
  After the restart the resumed template's first sibling fork re-prefilled once (22.2 s, `root`)
  before three hot forks: restored sessions carry their endpoint, not the base anchor. Receipts:
  [5090 gates](measurements/2026-09-05-rtx5090-v048-profile-gates.json) ·
  [5090 fanout 57.9K](measurements/2026-09-05-rtx5090-v048-fanout-57k.json) ·
  [5090 fanout 67.7K](measurements/2026-09-05-rtx5090-v048-fanout-67k.json) ·
  [lane receipts](../releases/v0.4.8/qualification/).
- **EXP-016 — fleet routing on a fixed workload (2026-09-05).**
  [`scripts/fleet_dispatch.py`](../scripts/fleet_dispatch.py) dispatches the frozen agent corpus
  (7 scenarios × 2 repetitions = 14 independent jobs, 24 requests) across one, two, or three
  lanes with one worker per lane, three policies, two batch repetitions per configuration, and
  per-lane output projections. Solo batches: RTX 5090 66.8 / 66.7 s, RTX 4090 154.9 / 156.0 s,
  RTX 3090 258.8 / 258.6 s. Measured per-scenario costs (5090 / 4090 / 3090): long replay
  14.9 / 48.6 / 91.0 s, medium branch 4.7 / 13.5 / 17.3 s, long decode 3.8 / 5.7 / 9.0 s, tool
  round trip 2.4 / 2.6 / 3.6 s, history p90 1.7 / 1.5 / 2.1 s, history p50 1.1 / 1.3 / 1.9 s,
  short 0.8 / 1.1 / 1.1 s. Naive longest-first dynamic dispatch is bounded by the biggest job
  landing on a slow lane: 5090+4090 51.2 / 52.5 s (the 4090 spends ~50 s on one long replay while
  the 5090 finishes 12 jobs in 42 s), three lanes 47.2 / 50.9 s. Static role pinning sends both
  long replays to the 4090 and loses outright: 100.3 / 101.5 s. Cost-aware assignment (longest
  processing time first over the measured per-lane costs; `--policy cost` fed by the solo
  receipts) lands within 4 s of its prediction: 5090+4090 43.4 / 43.9 s (predicted 39.5), three
  lanes 32.3 / 32.9 s (predicted 29.7) with lane busy times 29.9 / 28.2 / 29.4 s. Outputs are
  byte-identical across the two batch runs on the 5090 and 3090 lanes; the 4090 differs on 2-9
  steps between runs, matching the same-process variation its MTP3 arms recorded on 2026-09-04
  (17-22 of 24 requests). Receipts:
  [5090](measurements/2026-09-05-fleet-dispatch-main-solo.json) ·
  [4090](measurements/2026-09-05-fleet-dispatch-heavy-solo.json) ·
  [3090](measurements/2026-09-05-fleet-dispatch-scout-solo.json) ·
  [two-lane dynamic](measurements/2026-09-05-fleet-dispatch-main-heavy-dynamic.json) ·
  [two-lane cost](measurements/2026-09-05-fleet-dispatch-main-heavy-cost.json) ·
  [three-lane dynamic](measurements/2026-09-05-fleet-dispatch-three-lane-dynamic.json) ·
  [three-lane role](measurements/2026-09-05-fleet-dispatch-three-lane-role.json) ·
  [three-lane cost](measurements/2026-09-05-fleet-dispatch-three-lane-cost.json).
- **EXP-017 — native-lane restore path fixed at source (2026-09-05).** EXP-014 left the cost
  inside the restore path; a sequential read of the RTX 4090's real checkpoint files ran at
  2,248 MiB/s on the same NVMe, so the disk was excluded. The reader issued one request per KV
  page segment and, on Windows, every request was its own DirectStorage submit plus a fence
  wait; with `rk2v4-e8` pages that fixed cost per request held restores near 8.5 MB/s. Payload
  files are written contiguously in segment enumeration order, so the engine now plans one read
  per staging window and scatters each window to the device with asynchronous copies and one
  synchronization, and the store's Windows adapter submits a reader call as one bounded batch
  (`plan_continuation_checkpoint_reads`, `split_continuation_checkpoint_read` in the runtime
  contract; unit tests for the plan invariants and a 70 MiB batched read; lane commits `d22ce3fd`
  on the RTX 4090 and `3756db6e` on the RTX 3090; on-disk format unchanged).
  [`scripts/restore_probe.py`](../scripts/restore_probe.py) now also plants three run-specific
  ledger keys near the template's start, middle, and end and requires every restored
  continuation to quote them, with one in-process control, so a restore that scatters the wrong
  bytes cannot pass on timing alone. Same session shapes as EXP-014, shipped binary versus the
  candidate under the release's exact argv: RTX 4090 (57,889-token template, 1.13 GB)
  146.6 s → 5.6 s and 133.4 s → 5.6 s, the restored turn now costing less than the 7.7 s
  in-process control turn; RTX 3090 (38,251-token template, 1.68 GB) 91.8 s → 10.8 s and
  92.2 s → 10.7 s. All retrievals exact on both binaries and lanes. The RTX 5090 container has
  a different restore reader and is not affected. Receipts:
  [4090 shipped](measurements/2026-09-05-restore-probe-rtx4090-v0.2.1.json) ·
  [4090 candidate](measurements/2026-09-05-restore-probe-rtx4090-candidate.json) ·
  [3090 shipped (EXP-014)](measurements/2026-09-05-restore-probe-rtx3090.json) ·
  [3090 candidate](measurements/2026-09-05-restore-probe-rtx3090-candidate.json). Publication
  follows the lane rule: each lane requalifies its exact binary before a component release.
- **EXP-018 — checkpoint replication on all three lanes (2026-09-05).** Roadmap v0.5 §1, gated
  on EXP-017 (restores in seconds) and on the security gate it names: manifest origin
  authentication (ninfer#32) existed only on the RTX 5090 container, so it was ported to both
  native lanes first (every save publishes `manifest.mac`, an HMAC-SHA256 over the manifest keyed
  by material derived from the bearer key and held outside the checkpoint root; load and status
  verify origin before trusting manifest content; a present-but-wrong tag quarantines, an absent
  tag under `--session-checkpoint-require-origin-auth` refuses reversibly; RFC 4231 vectors and
  window/strict/transient-fault tests; lane commits `17e2f87d` and `7031893c`).
  [`scripts/checkpoint_sync.py`](../scripts/checkpoint_sync.py) replicates only verified,
  published generations (manifest-listed files by size and SHA-256, staged outside every scanned
  directory, one-rename publication, `current` last, unMAC'd generations refused by default).
  [`scripts/sync_probe.py`](../scripts/sync_probe.py) then proved the contract on each lane
  against the real store: checkpoint a 58K-token (5090, 4090) or 38K-token (3090) session,
  export, carry the replica to the macOS workstation over the tailnet, stop the server, delete
  the session directory, carry the replica back, import, restart, and the continuation restores
  from the imported generation and quotes three planted ledger keys exactly. The same replica
  with one payload byte flipped is refused by the tool at import (`does not match its manifest
  digest`); the same replica with a coherent manifest edit passes the tool and is quarantined by
  the runtime at load (`state: corrupt`, continuation `checkpoint_corrupt` on the native lanes
  and `previous_response_not_found` on the container; no resurrection). Timings: RTX 5090
  4.5 GB export 158 s, import 10.1 s, restored continuation 24.8 s; RTX 4090 1.13 GB export
  6.2 s, import 4.2 s, restored 7.4 s; RTX 3090 1.69 GB export 19.7 s, import 11.9 s, restored
  11.5 s. The off-machine hop's 1.8–3.5 MB/s was the workstation, not the fleet: it was in
  Japan that night, two transpacific tunnel crossings with one leg queueing to 900 ms RTT.
  EXP-019 measured and fixed the path the fleet actually uses. Cross-lane import is
  structurally unreachable: the session namespace binds the bearer key and the fingerprint
  binds binary and profile. Receipts:
  [5090](measurements/2026-09-05-sync-probe-rtx5090.json) ·
  [4090](measurements/2026-09-05-sync-probe-rtx4090.json) ·
  [3090](measurements/2026-09-05-sync-probe-rtx3090.json).
- **EXP-019 — replica transport, measured and fixed (2026-09-06).** EXP-018 moved its replicas
  through the macOS workstation, which was in Japan: every hop crossed the Pacific twice and one
  leg queued to 900 ms RTT, so its 1.8–3.5 MB/s said nothing about the fleet. Four real causes
  came out of the follow-up
  ([transfer paths](measurements/2026-09-06-replica-transfer-paths.json)): a single ssh stream is
  bound by the SSH channel window (≈1.6 MB in flight, so 8–14 MB/s at 67–190 ms whatever the
  link); the workstation's `ssh_config` set `Compression yes` globally, which made zero-filled
  test files look 10× faster than real payloads and put zlib in front of every real one;
  `tar`'s default 10 KiB records made the container host's 9p bounce look like the problem
  (`tar -b 8192` writes 2.6 GB to `/mnt/c` in 9.1 s against 72.8 s, and the export itself is
  4.9 s for 2.74 GB); and Windows OpenSSH cannot carry bulk between two Windows hosts at all —
  `ssh.exe` as a client inside an sshd session stalls on any large binary stream, whatever the
  sender, and `wsl.exe` stalls on binary stdout, so a WSL-resident file cannot be served through
  the Windows sshd either. [`scripts/hosts/pscp.py`](../scripts/hosts/pscp.py) therefore moves a
  file as N ranged reads over independent ssh connections where one end is not Windows
  (compression off, file-backed handles because pipes hang Windows `ssh.exe`, SHA-256 verified on
  both ends), and as bearer-token ranged HTTP over the tailnet where both ends are Windows —
  eight streams for ssh (a Windows sshd resets above roughly that) and sixteen for HTTP, where
  each connection is window-bound and more still scale. The end-to-end proof
  ([round trip](measurements/2026-09-06-cross-site-replication-rtx5090.json)) checkpoints a
  session on the RTX 5090, exports and archives it on ext4 (2.7 s + 0.5 s), serves it to the SF
  host at **11.5 MB/s**, destroys the local copy with the container stopped, fetches the replica
  back at **56.3 MB/s**, imports it in 2.6 s, and the restarted server's continuation quotes all
  three planted ledger keys exactly. A 4.35 GB replica measured 63.4 MB/s on the return leg. The
  asymmetry is the receiver, not the path: the same link and tool deliver 11.5 MB/s into a
  Windows host and 56–63 MB/s into WSL ext4, so replication targets should be Linux endpoints.
  Host-side corrections in the same pass: the global ssh compression, the WSL sshd's port
  collision with the Windows sshd (loopback :22 under mirrored networking, socket unit failed
  since July, now :2222 as documented), and per-host replica keys so any fleet host can address
  any other over the tailnet.
- **EXP-020 — a NAS is the right replication target for co-located lanes (2026-09-07).** The
  fleet's Synology (`ninfer-cache` share, a least-privilege SMB identity with no access to any
  other share) shares a LAN with two of the three lanes and reaches about 1 GbE line rate from
  both: 115.8 MB/s write and 117.6 MB/s read from the RTX 4090 host, 96.0 / 102.3 from the RTX
  3090 host, measured with raw unbuffered IO over 2 GiB of incompressible payload. Reaching the
  same appliance from the remote RTX 5090 host over the tailnet is the opposite story - 6.4 MB/s
  write, 22.7 MB/s read - because a DS918+ terminates WireGuard in userspace on a low-power CPU;
  that is worse than EXP-019's direct host-to-host path, so that lane keeps using it. One
  published generation per co-located lane is now replicated to the share and verified in place. Two
  operational facts worth keeping: the 4090 lane's replica is origin-authenticated while the
  3090 lane's surviving generations predate `manifest.mac` and replicate only under
  `--allow-unauthenticated`; and SMB from a non-interactive session on these hosts requires a
  registered SYSTEM scheduled task running `net use` with the credential as an argument -
  `New-SmbMapping` and `New-SmbGlobalMapping` both fail with Windows error 1312 ("a specified
  logon session does not exist"), even when spawned through `Win32_Process Create`. Receipt:
  [NAS replication](measurements/2026-09-07-nas-replication-sf-lanes.json).
- **EXP-021 — warm arrival: a restored session still re-prefills once (2026-09-07).** Roadmap
  v0.5 §2 promised that a checkpointed template makes subagent forks start hot. It does not yet
  hold across a restart, and the reason was not the restore path. Measured on the shipped v0.4.8
  profile at 57.9K tokens: four forks before a restart are hot (1.17-1.32 s, all
  `private_long_anchor`), and after a restart the resume costs 23.7 s while the first fork costs
  **22.1 s with reuse path `root` and zero reused tokens**. Restore + four forks is 49.3 s
  against 26.7 s for not checkpointing at all, so for the fanout pattern durable resume is
  currently a net loss. The control that isolated it: restoring a checkpoint taken *before* any
  fork serves four hot forks on the unmodified shipped binary, so restore reinstates anchors
  correctly - the anchor simply was not in the payload. A session's binding follows the newest
  continuation and a checkpoint serialises exactly one continuation, so a fork left its anchor
  behind on the parent; the byte counts show it directly (4,505,854,445 bytes saved before a
  fanout, 4,351,909,712 after, one StateImage fewer). Two fixes on branch `feat/warm-arrival`:
  a fork admitted through a long anchor now inherits a reference to that immutable anchor image,
  and consuming a session endpoint no longer charges a shared optional state to the new
  lineage's entitlement - a latent accounting bug that the first fix made reachable and that
  returned HTTP 500 on any resume of an anchor-carrying session. With both, the post-fanout
  checkpoint carries the anchor again and a fork issued as the first post-restart request is hot;
  an endpoint resume arriving first still leaves one 22.2 s re-prefill, with the anchor provably
  retained (a save right after that resume still carries two StateImages) and indexed, which
  puts the remaining defect in candidate admission for a just-consumed lineage. Device-state
  capacity is not the cause: 4 and 8 slots behave identically. Nothing was released; the
  candidate binary was built outside the appliance's canonical build. Receipt:
  [warm arrival](measurements/2026-09-07-warm-arrival-rtx5090.json).
- **EXP-022 — warm arrival holds: the anchor was evicted, not misjudged (2026-09-08).** The
  EXP-021 reading was wrong about where the loss sat. A catalog trace on the candidate showed the
  restored continuation carrying anchors at 67,762 and 67,780 before the resume and at 67,870 and
  67,908 after it: the two StateImages a post-resume save carried were the resume's own new
  anchors, not the template anchor. Every Responses request marks two private anchors (the
  inherited frontier, for its siblings, and its pre-generation frontier, for its children), a
  continuation retains two, and the replacement victim was the lowest frontier - the earliest
  anchor on the lineage, which is exactly the template boundary every sibling fork reuses. One
  continuing turn on a lineage was therefore enough to lose it, restart or not; the fanout
  patterns measured in EXP-013 and the v0.4.8 gates never took that turn. The victim is now the
  anchor whose loss costs the least re-prefill: the one with the smallest gap to its lower
  neighbour (root for the earliest), ties evicting the newer anchor, so the earliest recovery point
  survives for the life of the lineage and the retained set stays as widely spaced as possible.
  It is a pure function of frontiers, so it holds right after a restart when no hit history
  exists. Measured with the new `scripts/warm_arrival_probe.py` on the candidate at a 67.7K
  template across a verified restart: resume first, 4.2 s for restore plus resume, then sibling
  forks in **2.9 s and 1.3 s** on `private_long_anchor` (frontier 67,712); fork first, 3.7 s then
  1.3 s. Restore plus the whole post-restart sequence is 8.4 s and 6.7 s against 26.7 s for not
  checkpointing at all, so the v0.5 §2 promise holds on this candidate. Receipt:
  [warm arrival](measurements/2026-09-08-warm-arrival-rtx5090-candidate.json).
- **EXP-023 — restore is no longer hash-bound (2026-09-08).** The 24 s restore hashed every
  payload byte twice, at load and again as the engine streamed it, with a scalar SHA-256 that
  runs at 0.33 GB/s on the appliance's Zen 4, and read the disk at queue depth one both times.
  Three source changes on `feat/warm-arrival`: the bulk path of the hasher now uses the x86 SHA
  extensions when the CPU has them (2.66 GB/s on the same core, bit-exact against the scalar path
  for every length from 0 to 1,024 bytes, ragged multi-megabyte updates, and the "abc" vector);
  load no longer hashes engine payloads at all - the streamed hash on exactly the bytes the engine
  consumes is the single verification, which is what closed `alphastorm/ninfer#21` in the first
  place, and a mismatch still fails the import closed and quarantines on the next load; and the
  io_uring reader runs on its own thread issuing eight 4 MiB reads per batch while the serve-side
  reader keeps the next 32 MiB batch on the device as the previous one hashes. A 5.2 GB session
  restores in **3.8 s and 3.8 s** across two verified restarts with exact planted-key retrieval
  (was 24-27 s). Verified-or-refused was re-proven live with the new `--tamper-cmd` round of
  `scripts/restore_probe.py`: one byte flipped in the middle of the 4.4 GB KV payload while the
  lane was down, and the resume was refused with 404 `previous_response_not_found` in 2.8 s,
  status reported `corrupt`, a second attempt was refused, and the generation was quarantined.
  Receipt: [restore probe](measurements/2026-09-08-restore-probe-rtx5090-candidate.json).
- **EXP-025 — the native lanes serve mainline (2026-09-08).** The two native Windows lanes had
  drifted ~8K lines each from mainline, so they had no context cache, no warm arrival, and the
  restore path fixed in EXP-023 would have needed porting twice. Stage 1 compiled mainline for
  Ada; this entry is stages 2 and 3: the Windows platform code (D3D12 residency arena,
  DirectStorage read queue, MSVC 19.44 build of the host tree) and Ampere `sm_86`, then
  serving. Every kernel suite runs on the hardware now - the earlier Windows run had excluded
  them by name - and they pass 100/100 on both builds on the Ada GPU (the `sm_86` binaries run
  on `sm_89`; 94 suites execute, the five real-artifact suites and the external-tokenizer
  frontend suite skip). An activation path a build excludes (NVFP4 W4A4 on both, FP8 A8 and
  FP8-KV on Ampere) ends a test arm as excluded on the stub's refusal and the dedicated suites
  require that refusal, so a stub that quietly fell back to A16 would fail them. Five defects
  showed only on the hardware, none in the earlier builds: the BF16 GDN gating plan hard-coded
  the RTX 5090's cooperative-grid budgets (340/680 CTAs over 170 SMs), so on 128 SMs the first
  prompt longer than one tile died with `cudaErrorCooperativeLaunchTooLarge` - the budget is now
  the driver's occupancy for the exact instantiation times the SM count, with fall-through to
  the next split; its residency query defaulted a different warp count from the launchers; the
  INT8-cache prompt Attention kernel, shaped for Blackwell's allocator (16 warps at 120
  registers), spilled 200 B/thread under Ada's 128-register cap for a 512-thread CTA, so a 42K
  prompt ran at 390 tok/s and a 130K prompt did not finish in fourteen minutes at 130 W - on
  `sm_89`/`sm_86` it now covers 32 query rows with eight warps at up to 255 registers, zero
  spill; the streamed restore issued the next 32 MiB batch while the previous one hashed, which
  io_uring supports and the one-slot, one-fence DirectStorage queue does not, so every native
  restore was refused as `previous_response_not_found` while status said `available` - the
  read-queue contract now names whether a backend overlaps batches; and that refusal was never
  logged. Served in candidate windows against the installed releases with the same 130,048-token
  fixture, gate script, host, and day: the RTX 4090 retrieves exactly in **86.8 s (1,499 tok/s)
  against 97.5 s (1,333)** and decodes 2,048 tokens at **103.8 against 88.4 tok/s** wall; the
  RTX 3090 **208.6 s against 219.5 s** and **60.3 against 52.8 tok/s**; the agent protocol
  passes on both with no resurrection across a verified restart. The context cache arrives
  whole: on a 67.7K template four sibling forks take 1.8-2.0 s (4090) and 2.5-2.9 s (3090)
  device-resident, a 2.9 GB explicit save 4.0 s / 15.4 s, and after a restart the resume costs
  4.1 s / 16.4 s and the four forks 1.8-1.9 s / 2.5-2.6 s, every one on `private_long_anchor`;
  warm arrival holds in both orders (4090 resume-first 4.5 / 3.1 / 1.8 s, fork-first
  4.1 / 1.6 / 3.0 s; 3090 17.3 / 3.1 / 2.6 s and 16.5 / 3.3 / 2.7 s) with planted keys exact
  before and after; restore is 5.0 / 4.2 s on the 4090 and 17.1 / 16.6 s on the 3090 for
  2.9 GB, and a flipped payload byte is refused (404), marked `corrupt`, and quarantined on
  both. One sizing rule fell out: at 131K INT8 the RTX 4090 has 169 MiB of WDDM budget left
  with four device-state slots and the driver pages device memory - decode drops to 47 tok/s
  and every fork and resume is 2.5× slower - while two slots leave 463 MiB and full speed, and
  one slot re-prefills the first fork (38.6 s on reuse path `root`: one cached device state
  cannot hold both the template and the edit; the three forks after it are hot);
  the RTX 3090 keeps 835 MiB at four slots and is unaffected. Both hosts were returned to their
  found state (release serving on the 4090, stopped on the 3090). Every receipt is bound to the
  server's reported identity (binary, source, model, resolved configuration), captured at the
  start and checked after every restart; the probes gained that binding tonight, along with the
  slowest-fork fields that a median had hidden. Runtime branch `port/native-lanes-on-mainline`
  at `6fd9e135` (runtime through `8b3dd4a9`, tests after). Receipts, RTX 4090:
  [ladder](measurements/2026-09-08-rtx4090-mainline-device-state-ladder.json) ·
  [gates](measurements/2026-09-08-rtx4090-mainline-profile-gates.json) ·
  [release gates](measurements/2026-09-08-rtx4090-v0.2-profile-gates.json) ·
  [fanout](measurements/2026-09-08-rtx4090-mainline-fanout-57k.json) ·
  [one slot](measurements/2026-09-08-rtx4090-mainline-fanout-57k-slots1.json) ·
  [four slots](measurements/2026-09-08-rtx4090-mainline-fanout-57k-slots4.json) ·
  [warm arrival](measurements/2026-09-08-rtx4090-mainline-warm-arrival.json) ·
  [restore](measurements/2026-09-08-rtx4090-mainline-restore.json); RTX 3090:
  [ladder](measurements/2026-09-08-rtx3090-mainline-device-state-ladder.json) ·
  [gates](measurements/2026-09-08-rtx3090-mainline-profile-gates.json) ·
  [release gates](measurements/2026-09-08-rtx3090-v0.2.5-profile-gates.json) ·
  [fanout](measurements/2026-09-08-rtx3090-mainline-fanout-57k.json) ·
  [one slot](measurements/2026-09-08-rtx3090-mainline-fanout-57k-slots1.json) ·
  [two slots](measurements/2026-09-08-rtx3090-mainline-fanout-57k-slots2.json) ·
  [warm arrival](measurements/2026-09-08-rtx3090-mainline-warm-arrival.json) ·
  [restore](measurements/2026-09-08-rtx3090-mainline-restore.json).
- **EXP-026 — qualifying the mainline native lanes (2026-09-09).** EXP-025 proved the mainline
  runtime serves both native lanes; this is the release path around it, which had never run
  since the port. Five blockers, each reproduced before it was fixed. The package builder asks
  every shipped binary for `--version` to bind one build identity, and the mainline bench had
  no such arm (the lane branches did). `transfer_install` relayed the 0.6 GB package through
  the operator's Mac with `scp -3`: 297 of 592 MB in 900 s (**0.33 MB/s**) before the timeout,
  and the same-host lane stalled at zero bytes, because Windows OpenSSH carries no bulk between
  two Windows hosts (EXP-019). The package now copies locally on one host and otherwise travels
  as ranged HTTP served by the builder and fetched by the target: **104.7 MB/s**, 16 streams,
  SHA-256 verified on both ends and again by the installer. The staging root was created with
  `New-Item` under `ProgramData`, so on the host whose qualification parent did not exist yet
  it inherited `BUILTIN\Users` write access and the installer refused to create protected state
  beneath it; the candidate's own protection library now creates or checks the parent. The
  managed install passed its arguments as an array splat, which PowerShell binds positionally.
  And the lane's protocol probe sends the session credential on `X-NInfer-Session` alone and
  requires a header that disagrees with the body's `ninfer_session` to be refused: mainline
  applied the header only on the bodyless stored-response routes, so a header-scoped create was
  silently unscoped and the conflict returned 200. Both lanes now pass preflight, build, scan,
  package, and install, and reach `protocol`.
  Sizing the RTX 4090 lane's pinned pools took its own measurement. The managed start failed
  `cudaMallocHost` twice while three hand-launched starts with identical arguments succeeded:
  the controller reads the 18 GB model artifact through the file cache immediately before
  launch, and sampling a failing start showed the free-and-zero list going 13.1 → 0.0 GB with
  standby reserve at 5.2 GB. Pinned demand is the dial that matters — 24 slots plus the 8 GiB
  default Host KV is 13.3 GB, 4 GiB is **9.2 GB** and starts — but the slot count is not
  available to trade: at 8 slots the protocol's post-delete continuation fails in 41 s with a
  500 from a `std::logic_error`, because admission planned reuse from a catalogued continuation
  whose last state replica had been evicted. That invariant defect is open and capacity-
  triggered; both lanes carry 24 slots, and only the RTX 4090 lane's pool was halved. The
  RTX 3090 lane is blocked on its host, which went offline mid-window.
  Receipt: [qualification window](measurements/2026-09-09-native-lane-qualification-blockers.json).

## Current order

The backlog below is a pool; the program's order is fixed in [`ROADMAP.md`](../ROADMAP.md). The
MTP campaign retains MTP3 and rejects K5/K7 for the current artifacts. The per-lane variant
campaign closed the `nvfp4` question for the v0.4 train (rejected on the RTX 5090 because the
card forces INT8 KV; NVFP4 W4A4 needs Blackwell tensor cores, so the `sm_89`/`sm_86` lanes are
out of scope and the 4090 upstream removed its NVFP4 path) and produced two configuration-only
lane changes; those and the RTX 5090 context-cache profile were requalified on 2026-09-05 and
staged and cut as `v0.4.8` (EXP-015). Each lane carries its own best measured stack rather
than one shared configuration. The native-lane restore path is fixed at source (EXP-017:
RTX 4090 restores 24–26× faster, RTX 3090 8.5×); both lanes requalified it on 2026-09-05 and it
ships in `v0.4.9`. The native lanes now build from mainline (EXP-025): the next RTX 4090 and
RTX 3090 candidates come from `port/native-lanes-on-mainline`, with the RTX 4090 profile at
two device-state slots, 24 host state slots, and a 4 GiB Host KV pool, and each is requalified
through its own lifecycle tool (EXP-026) before a cut.

## Ideas backlog

Open, unclaimed, or in-flight. Claim one by opening an issue in
[alphastorm/ninfer](https://github.com/alphastorm/ninfer/issues) titled `perf: <idea>` with your
hypothesis and method before writing code.

| Idea | Why it should work | Status |
| --- | --- | --- |
| Fuse Q4/Q5 GEMV/MMA epilogues with adjacent normalization | Removes a full activation round trip per layer at decode shapes | open |
| Qualify a speculative (MTP) profile on the RTX 4090 lane | Shipped in v0.3.1: MTP3 promoted by the two-arm decision (+17.04% Golden-equivalent wall; 93.2–97.7 tok/s vs 52.330 baseline); exploratory sweep measured draft-3 > 4 > 5 on the fixed workload | shipped v0.3.1 |
| Durable RTX 5090 container (serve-layer session persistence) | Shipped in v0.4.0: transactional generational store + io_uring O_DIRECT restore; 109,589 tokens restored hot across a docker restart ([qualification](../docs/measurements/2026-08-30-rtx5090-durable-qualification.json)) | shipped v0.4.0 |
| Checkpoint replication to shared storage | Delivered 2026-09-05 (EXP-018): `scripts/checkpoint_sync.py` copies verified published generations out and back; origin authentication on every lane; same-profile-pair portability only | completed |
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
