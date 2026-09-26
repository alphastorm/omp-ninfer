# Upstream watch

The runtime ships from forks; v0.8.2 uses an unmodified upstream OMP client. This page names
the upstreams we track, runtime fork points, and the current pull-in position. The watch manifest is
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

## Tracked upstreams and current position — v0.8.2

The unmodified upstream OMP 18.3.0 client and model artifact are unchanged from v0.8.1.
RTX 5090 advances to `v0.6.11-qwen38-5090-beta.1` (image `26813f56`, server `0d7e042b`,
source `32c21f73`). RTX 4090 remains `v0.6.8-qwen38-4090-beta.1` (package `46aa4110`,
server `32905865`, source `5a774841`), carrying its v0.8.1 lane receipt: 15 canonical
native phases and 130,048-token retrieval in **91.0 s**. RTX 3090 remains deferred.

The runtime adds `ninfer-serve --gpu-keep-warm-ms N`, off by default. After work and while
idle, a single-warp kernel touches no memory and spins 3.5 ms of every 10 ms on its own stream
for N ms, skips a launch while the previous spin runs, and stops when a request is pending.
RTX 5090 profile `qwen38-5090-v0.8.2` adds `--gpu-keep-warm-ms 60000`; host KV stays
16384 MiB and the host floor stays 28672 MiB. After 12-58 s idle, new sessions prefilled in
**0.155-0.157 s** (TTFT **0.173-0.181 s**), versus **0.253-0.304 s** (TTFT **0.316-0.366 s**)
without keep-warm. The 89-case role corpus was byte-identical to v0.8.1 on and off. Holding
clocks costs about **71 W**; a 60 s grace replayed over 62 h of logged v0.7.0 traffic would
cost about **2.3 W average**. [EXP-062](measurements/2026-09-26-engine-keep-warm.json).

The published RTX 5090 image recorded 130,048-token exact retrieval in **56.4 s**, decode at
**160.07 tok/s**, four sessions restored after restart, and passed publication-barrier,
fanout, warm-arrival, restore and multisession probes. None of 24 fresh sessions fell back to
a full prefill; median TTFT was **0.090-0.098 s**. Stock OMP 18.3.0 kept one session across
restarts on the RTX 5090. [Lane receipt](../releases/v0.8.2/qualification/rtx5090.json).

All four documented routes passed **24 steps** with unmodified OMP 18.3.0 on the published
v0.8.2 components: RTX 5090 container host 2, macOS client 10, Windows client 5 and RTX 4090
native Windows 7; both hosts were restored.
The upstream macOS arm64, Windows x64 and Linux x64 binaries each passed a typed tool turn,
an exact continuation and a fail-closed request against the published RTX 5090 image.
[Documented routes](../releases/v0.8.2/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.8.2/acceptance/composed-external-installation.json).

Checkpoints bind the exact server build: sessions saved by v0.8.1 do not restore on the new
RTX 5090 build in v0.8.2. OMP resends the full conversation and each session re-prefills once.
[Release notes](../releases/v0.8.2/NINFER_RELEASE_NOTES.md).

The upstream delta measurements below remain historical; keep-warm is not an upstream rebase.

## Historical position — v0.8.1

Runtime positions below retain the [2026-09-24 report](measurements/2026-09-24-upstream-watch.json);
they are not new upstream delta measurements. The upstream NInfer rebase remains future work.
The client remains the unmodified upstream OMP 18.3.0 release binary with the same SHA-256
pins as v0.8.0. All three client binaries passed live inference on the published RTX 5090
image (Linux under Ubuntu/WSL2), and the four documented routes passed all 24 steps on the
published v0.8.1 components, with both hosts restored.

The runtime change is decode kernels, not the upstream rebase: small-extent Q4/Q5 projections
share activation loads across weight rows, and Q4 gate/up staging avoids shared-memory bank
conflicts. RTX 5090 `v0.6.10-qwen38-5090-beta.1` (image `5ca6e416`, server `5b2f2471`,
source `8cc0810a`) decodes 10.3-11.0% faster with identical outputs. RTX 4090
`v0.6.8-qwen38-4090-beta.1` (package `46aa4110`, server `32905865`, source `5a774841`)
keeps one-row split2 kernels on native lanes; C1 decode is 157.89 vs 153.54 tok/s. Every
runtime gate was re-measured on published bytes, matching v0.8.0's behavior; client, model,
serving settings and floors are unchanged.
[EXP-055](measurements/2026-09-25-decode-kernel-schedules.json) ·
[EXP-054](measurements/2026-09-25-decode-roofline-attribution.json) ·
[Release notes](../releases/v0.8.1/NINFER_RELEASE_NOTES.md) ·
[Documented routes](../releases/v0.8.1/acceptance/documented-routes.json).

| Upstream | Fork point | Delta | Position |
|---|---|---|---|
| `Neroued/ninfer` (engine; both mainline lanes build from one fork source) | `6e8b2e2a` (mainline base) | 202 commits at `594930e7` (2026-09-23) | **Merge deferred on measurement.** 18 commits were taken in v0.6.7 ([ledger](measurements/2026-09-12-upstream-backport-ledger.json), [EXP-035](measurements/2026-09-13-upstream-backport-qualification.json)); on 2026-09-17 11 of 129 remaining candidates applied cleanly and none changed a shipped profile ([EXP-045](measurements/2026-09-17-upstream-applicability-triage.json)). On 2026-09-24 upstream head itself ran the RTX 5090 lane gates on the same appliance, weights and settings as the shipped runtime: prefill and decode rounds per second within noise, and less prefix reuse on this product's workloads (0 of 4 fanout branches, 4 of 8 two-session continuations re-prefilled) ([EXP-048](measurements/2026-09-24-engine-window-upstream-vs-shipped.json)). A merge is a re-architecture port - a trial merge leaves 111 paths to resolve, 40 of them fork features to re-express in upstream's restructured `src/models/qwen3_5`, `context_cache/` and serve layers - plus the v3 artifact and a new chat template, for no measured lane gain. Rerun `scripts/engine_window_compare.py` when an upstream change could move a lane gate. Tracked in omp-ninfer #33. |
| `UDPSendToFailed/ninfer-4090` (4090 port) | `11aae2d6` | 57 commits at `5c60b7c9` (unchanged since 2026-09-09) | 9 of 51 candidates apply cleanly, all kernel retunes (EXP-045). The fixes this lane wants - chunked KV snapshot staging, the MTP restore stride, publishing finished snapshot saves, WDDM residency budgeting, the D3D12 residency fence, the admission shortfall and `/health` - conflict in files the fork changed and are read against v0.7.1's durability work when taken. Upstream removed its NVFP4 path (`dabae909`). |
| `Don-Chad/ninfer-3090` (3090 port) | `ef6ecc3c` | 141 commits at `75d94eab` (unchanged since 2026-08-31) | Triage rides the RTX 3090 window when its host returns, expected around 2026-09-30. |
| `can1357/oh-my-pi` (client) | Upstream `62bc57be` (v18.3.0) | Unmodified upstream release binary | Adopted in v0.8.0; no fork build, archive, installer or cask. Provider fragments and `PI_OPENAI_STATEFUL=1` configure the client; stock OMP has no `omp appliance` commands. |

**Historical client position through v0.7.4.** `omp-18.2.3-cross-platform-beta-1` (source
`5ade242d`, since v0.7.3) carried 36 downstream commits on upstream `a2d83061` (v18.2.3),
including the NInfer provider and appliance lifecycle. The 2026-09-24 watch counted 681 upstream
commits to `62bc57be` (v18.3.0). At that time, the client plan was a rebase plus documented-route
acceptance rather than direct adoption
([EXP-046](measurements/2026-09-17-client-repin-evaluation.json)); v0.8.0 instead uses the stock
binary with the stock-client runtime.

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
- Through v0.7.4, the client fork point was the upstream tag commit onto which downstream
  patches rebased. v0.8.2 does not build or publish an OMP client; it keeps the upstream
  release binary instead.
