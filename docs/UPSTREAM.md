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

GitHub's compare endpoint lists at most 250 commits and 300 changed files and cuts a larger delta
without an error. The report records `commits_truncated` and `files_truncated`, and a cut file
list scores overlap as `unknown-truncated` rather than `no-direct-path-overlap` - before
2026-09-24 a cut list read as no overlap and marked every commit of a 1,387-file engine delta a
`pull-candidate`. For a delta that large, measure applicability against the fork itself (a
scratch cherry-pick or trial merge) instead of reading the overlap score.

## Tracked upstreams and current position (2026-09-24, v0.7.3)

[Report](measurements/2026-09-24-upstream-watch.json).

| Upstream | Fork point | Delta | Position |
|---|---|---|---|
| `Neroued/ninfer` (engine; both mainline lanes build from one fork source) | `6e8b2e2a` (mainline base) | 202 commits at `594930e7` (2026-09-23) | **Merge deferred on measurement.** 18 commits were taken in v0.6.7 ([ledger](measurements/2026-09-12-upstream-backport-ledger.json), [EXP-035](measurements/2026-09-13-upstream-backport-qualification.json)); on 2026-09-17 11 of 129 remaining candidates applied cleanly and none changed a shipped profile ([EXP-045](measurements/2026-09-17-upstream-applicability-triage.json)). On 2026-09-24 upstream head itself ran the RTX 5090 lane gates on the same appliance, weights and settings as the shipped runtime: prefill and decode rounds per second within noise, and less prefix reuse on this product's workloads (0 of 4 fanout branches, 4 of 8 two-session continuations re-prefilled) ([EXP-048](measurements/2026-09-24-engine-window-upstream-vs-shipped.json)). A merge is a re-architecture port - a trial merge leaves 111 paths to resolve, 40 of them fork features to re-express in upstream's restructured `src/models/qwen3_5`, `context_cache/` and serve layers - plus the v3 artifact and a new chat template, for no measured lane gain. Rerun `scripts/engine_window_compare.py` when an upstream change could move a lane gate. Tracked in omp-ninfer #33. |
| `UDPSendToFailed/ninfer-4090` (4090 port) | `11aae2d6` | 57 commits at `5c60b7c9` (unchanged since 2026-09-09) | 9 of 51 candidates apply cleanly, all kernel retunes (EXP-045). The fixes this lane wants - chunked KV snapshot staging, the MTP restore stride, publishing finished snapshot saves, WDDM residency budgeting, the D3D12 residency fence, the admission shortfall and `/health` - conflict in files the fork changed and are read against v0.7.1's durability work when taken. Upstream removed its NVFP4 path (`dabae909`). |
| `Don-Chad/ninfer-3090` (3090 port) | `ef6ecc3c` | 141 commits at `75d94eab` (unchanged since 2026-08-31) | Triage rides the RTX 3090 window when its host returns, expected around 2026-09-30. |
| `can1357/oh-my-pi` (client) | `a2d83061` (v18.2.3 tag) | 681 commits at `62bc57be` (v18.3.0, 2026-09-24) | Pinned client `omp-18.2.3-cross-platform-beta-1` (source `5ade242d`, v0.7.3) carries 36 downstream commits on the tag, including the NInfer provider and the appliance lifecycle. The upstream binary carries no NInfer provider, so a re-pin is a rebase plus every documented route, not an adoption ([EXP-046](measurements/2026-09-17-client-repin-evaluation.json)). Next client cycle. |

### v0.6.9: parser semantics without the serve-adapter rebase

The [2026-09-12 backport ledger](measurements/2026-09-12-upstream-backport-ledger.json) and the
2026-09-13 delta counts it was read against are historical evidence for this release. The ledger
deferred `3b50962b` and `0c5d570c` because their extracted parser files do not exist on this
tree. The v0.6.9 release instead implements their semantics independently in the downstream
parser: supported scalar unions, case-insensitive
booleans, precise numeric lexemes, mathematically integral values, duplicate parameters, and
balanced embedded markup. It does not import the wholesale serve-adapter rebase or change the
fork point; custom raw input, history, opaque IDs, and stream ownership are preserved.

Reviewed source `696e78c7b4e3ac28ffcffafc73acc1496e65ef03` includes remediation against
malformed-region rescans and recursive union traversal; bytewise regressions and an 8,192-deep
union case pass. It builds the published RTX 5090 `v0.6.5-qwen38-5090-beta.1` and native
RTX 4090 `v0.6.3-qwen38-4090-beta.1` components. Both lanes are qualified and RTX 4090
public-URL already-installed acceptance passed; the RTX 5090 documented host 2/2 and macOS
10/10 routes passed against the published image.
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
