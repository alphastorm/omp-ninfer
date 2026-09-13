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

## Tracked upstreams and current position (2026-09-13, v0.6.9 candidate)

| Upstream | Fork point | Delta | Position |
|---|---|---|---|
| `Neroued/ninfer` (5090 engine) | `6e8b2e2a` (mainline base) | 158 commits at `d4929686`; 18 taken in `v0.6.7`, on both mainline lanes from `v0.6.8` | **First tranche shipped in v0.6.7, on the RTX 4090 lane in v0.6.8** (runtime `v0.6.3-qwen38-5090-beta.1`): 18 commits taken with reasons - MoE/GDN/vocabulary kernel work, sparse-MoE and GDN record fixes, host-upload completion, frontend perf, cpp-httplib 0.54.1 - every lane gate within noise of v0.6.2 ([ledger](measurements/2026-09-12-upstream-backport-ledger.json), [EXP-035](measurements/2026-09-13-upstream-backport-qualification.json)). **Deferred engine family:** the runtime materialization/pressure fix family including upstream #229 (this product's fanout workload), unreachable without `099d9032` value-aware shared prefix scheduling, which pulls the serve-adapter campaign - a dedicated rebase with the `pressure_protocol` and fanout phases as arbiter. Also queued: upstream's GDN cooperative-capacity fix `e51b585c`, which overlaps our `29caaf34` (#42) and needs its own merge window; the Qwen tool-parser semantics are independently ported for the v0.6.9 candidate without that campaign (see below). Excluded as product decisions: dflash2, nvfp4/k8v4 kv-cache formats, spdlog. |
| `UDPSendToFailed/ninfer-4090` (4090 port) | `11aae2d6` | 15 commits | Fold into the durable-4090 roadmap campaign: MTP draft capacity K=15 + GQA decode kernels (feeds the MTP ablation), chunked KV snapshot staging + MTP restore stride fix (durability correctness), WDDM evictable-budgeting CLI toggle (desktop-shared GPUs - exactly our 4090 host), D3D12 residency fence fixes, streaming UTF-8 repair. Upstream also removed its NVFP4 path entirely (`dabae909`), consistent with our finding that nvfp4 is not a VRAM reduction (omp-ninfer #28). |
| `Don-Chad/ninfer-3090` (3090 port) | `ef6ecc3c` | 141 commits (was 0 on 2026-08-30) | Upstream resumed; triage rides the 3090 mainline candidate's window on host return (~21 Sept). |
| `can1357/oh-my-pi` (client) | `cc14e04f` (v18.0.9 tag) | 222 commits | Stay pinned. The NInfer provider, status validators, and checkpoint endpoints are downstream patches; upstream movement since 18.0.9 is client UX (18.0.10/18.0.11: autocomplete acceptance, status timer, composer/gallery filters). Re-pin evaluation rides the next client cycle together with the update-banner suppression (omp-ninfer #18). |

### v0.6.9: parser semantics without the serve-adapter rebase

The dated delta counts above and the
[2026-09-12 backport ledger](measurements/2026-09-12-upstream-backport-ledger.json) are
historical evidence, not a new watch run. The ledger deferred `3b50962b` and `0c5d570c` because
their extracted parser files do not exist on this tree. The v0.6.9 candidate instead implements
their semantics independently in the downstream parser: supported scalar unions, case-insensitive
booleans, precise numeric lexemes, mathematically integral values, duplicate parameters, and
balanced embedded markup. It does not import the wholesale serve-adapter rebase or change the
fork point; custom raw input, history, opaque IDs, and stream ownership are preserved.

Reviewed source `696e78c7b4e3ac28ffcffafc73acc1496e65ef03` includes remediation against
malformed-region rescans and recursive union traversal; bytewise regressions and an 8,192-deep
union case pass. It builds the published RTX 5090 `v0.6.5-qwen38-5090-beta.1` and native
RTX 4090 `v0.6.3-qwen38-4090-beta.1` components. Both lanes are qualified and RTX 4090
public-URL already-installed acceptance passed; the RTX 5090 host/macOS routes remain pending.
[Release notes](../releases/v0.6.9/NINFER_RELEASE_NOTES.md).
The old backport ledger is intentionally unchanged: its deferred parser entry describes that
earlier campaign, not the candidate's current parser coverage. The deferred pressure-planner
family is separate; the alternating-session finding is already attributed to host KV capacity
([EXP-039](measurements/2026-09-13-hostkv-capacity-multisession.json)), not proof that this
product needs that planner rebase.

## Why the fork points are what they are

- The 5090 lane builds from the mainline runtime whose upstream base is `6e8b2e2a` (since v0.6.2);
  later upstream movement is tracked separately from the reviewed backports and semantic ports
  named above. The retired container mirror point `4eef14a7`
  was the lineage's base before v0.6.2 and made the delta read 17 commits larger than it is.
- The 4090/3090 native Windows lanes vendored their upstreams at the recorded commits and carry
  the durable-checkpoint, security, and packaging work downstream.
- The client fork point is the upstream tag commit of the pinned release; downstream patches
  rebase onto it (see the omp-monorepo patch-stack lane for the mechanics this watch borrows).
