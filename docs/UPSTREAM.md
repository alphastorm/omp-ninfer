# Upstream watch

The product ships from forks. This page names every upstream we track, the exact fork points,
how the watch runs, and the current pull-in position. The machine-readable manifest is
[`upstream-watch.json`](../upstream-watch.json); the watch tool is
[`scripts/upstream_watch.py`](../scripts/upstream_watch.py); dated reports land in
[`docs/measurements/`](measurements/).

## Running the watch

```bash
python3 scripts/upstream_watch.py --receipt docs/measurements/$(date +%F)-upstream-watch.json
# per-commit overlap scoring (one extra API call per upstream commit):
python3 scripts/upstream_watch.py --only ninfer-4090 --per-commit-files
```

Read-only: the tool only queries the GitHub API and writes the report file you name. Verdicts
are `up-to-date`, `upgrade-available`, or `error`; every upstream commit gets a class
(`fix`/`perf`/`feature`/`security`/`docs`/`test`/`chore`) and a recommendation
(`pull-candidate`, `next-release`, `review-now`, `ignore`). Recommendations are triage, not
decisions - a human owns every pull.

## Tracked upstreams and current position (2026-08-30)

| Upstream | Fork point | Delta | Position |
|---|---|---|---|
| `Neroued/ninfer` (5090 engine) | `4eef14a7` (vendor mirror) | 51 commits | Selective backport next engine release: 11 low-risk kernel/frontend fixes (GDN prefill convolution into QKV, widened MoE staging, fused TMA SwiGLU widths, w8 rowsplit decode, fp8 w8a16 vocab GEMM, CUDA device binding, streaming UTF-8 repair, control-token provenance, media enum validation, tool-message names, sparse-MoE scan sync). The serve-layer protocol-adapter rework is a dedicated future rebase campaign; the new pressure planner stays out while upstream issue #121 (planner crashes) is open. |
| `UDPSendToFailed/ninfer-4090` (4090 port) | `11aae2d6` | 15 commits | Fold into the durable-4090 roadmap campaign: MTP draft capacity K=15 + GQA decode kernels (feeds the MTP ablation), chunked KV snapshot staging + MTP restore stride fix (durability correctness), WDDM evictable-budgeting CLI toggle (desktop-shared GPUs - exactly our 4090 host), D3D12 residency fence fixes, streaming UTF-8 repair. Upstream also removed its NVFP4 path entirely (`dabae909`), consistent with our finding that nvfp4 is not a VRAM reduction (omp-ninfer #28). |
| `Don-Chad/ninfer-3090` (3090 port) | `ef6ecc3c` | 0 | Up to date. |
| `can1357/oh-my-pi` (client) | `cc14e04f` (v18.0.9 tag) | 222 commits | Stay pinned. The NInfer provider, status validators, and checkpoint endpoints are downstream patches; upstream movement since 18.0.9 is client UX (18.0.10/18.0.11: autocomplete acceptance, status timer, composer/gallery filters). Re-pin evaluation rides the next client cycle together with the update-banner suppression (omp-ninfer #18). |

## Why the fork points are what they are

- The 5090 container lineage (`feat/unified-durable-resume`, shipped in v0.4.0) incorporates the
  vendor mirror at `4eef14a7`; everything past it is unreviewed upstream movement.
- The 4090/3090 native Windows lanes vendored their upstreams at the recorded commits and carry
  the durable-checkpoint, security, and packaging work downstream.
- The client fork point is the upstream tag commit of the pinned release; downstream patches
  rebase onto it (see the omp-monorepo patch-stack lane for the mechanics this watch borrows).
