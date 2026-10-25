# Roadmap

This roadmap is a scope boundary, not a promise of dates. Oh My Pi (coding-agent client) connects
through OMP NInfer (qualified appliance and release layer) to NInfer (inference engine) serving
Qwen3.8 27B (served model) on user-owned NVIDIA GPUs. Qualified on RTX 5090 · 4090 · 3090, each
release lane is bound to exact bytes and a qualification receipt. Work outside that wedge requires a
new product decision rather than placeholder abstractions, and no kernel, model, or configuration
change becomes part of a release until its exact binary and profile are rebound through a new
qualification receipt.

Standing support boundaries for the 0.x series: owner-operated exact profiles with no SLA or upgrade
commitment; two requests in flight on the RTX 5090 container lane and one active request on each
native Windows lane (RTX 4090 and RTX 3090, running one lane at a time on port 18082); carried-native
JSON-schema output rejected while the RTX 5090 container lane qualifies JSON-schema structured output;
the unattended RTX 3090 fleet scout role disabled;
no cloud hosting, multi-GPU inference, multi-tenant serving, priority or preemptive scheduling,
automatic container restart, or silent cloud fallback; and no support or performance claim outside
the exact recorded package, machine, and profile. Community project; not affiliated with or endorsed
by Oh My Pi, Qwen, or NVIDIA.

## Current release

**v0.13.0** (published 2026-10-25, GitHub `Latest`) pins unmodified upstream Oh My Pi **18.12.6**
(`45c35e40`) across macOS arm64 (preview), Windows x64, and Linux x64 (WSL2), rebases the RTX 5090
container runtime onto upstream `Neroued/ninfer` master `64d10fbf`, and carries the qualified
v0.12.2 native Windows runtime packages unchanged:

- **RTX 5090 container (`v0.7.0-qwen38-5090-beta.2`, source `6d4d0a05`, image `5d10a998`, model
  `81f924d4`):** Windows 11 + Docker Desktop/WSL2 on loopback `127.0.0.1:18089`, BF16 KV (146,368
  automatic tokens), 131,072-token context, two requests in flight plus two extra device-state
  slots, DFlash2 draft window 7, schema 3 checkpoint store (`checkpoints-v013` with mandatory
  `--session-checkpoint-require-origin-auth` and non-blocking export), JSON-schema structured
  output, 128-character tool names, vision + tools + preserved thinking.
- **RTX 4090 (`v0.6.11-qwen38-4090-beta.1`) and RTX 3090 (`v0.6.3-qwen38-3090-beta.1`) native
  Windows (source `cad19767`, model `eec39564`):** loopback `127.0.0.1:18082`, INT8 KV,
  131,072-token context, MTP3, one request at a time, text + tools (11,264 MiB host KV on RTX
  4090; 8,192 MiB host KV and 300 W cap on RTX 3090). Both install on one two-GPU host bound by
  GPU UUID (v0.12.0) and run one lane at a time; RTX 3090 retains two-direction rollback and RTX
  4090 rollback is `not_applicable` there.

Stock OMP has no `omp appliance` lifecycle commands; container and native host scripts own runtime
lifecycle, and source-first native qualification is an established release procedure
([`docs/RELEASES.md#next-native-release-sequencing`](docs/RELEASES.md#next-native-release-sequencing)).
Full release authority: [`releases/v0.13.0/NINFER_RELEASE_NOTES.md`](releases/v0.13.0/NINFER_RELEASE_NOTES.md) ·
[`releases/v0.13.0/manifest.json`](releases/v0.13.0/manifest.json) ·
[`releases/v0.13.0/qualification.json`](releases/v0.13.0/qualification.json) ·
[`docs/RELEASES.md`](docs/RELEASES.md) · [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md).

## Next release — v0.13.1 native rebase preparation

[Prepared notes](releases/v0.13.1/NINFER_RELEASE_NOTES.md) and
[gate prose](releases/v0.13.1/qualification.json) target native
`v0.7.0-qwen38-4090-beta.1` / `v0.7.0-qwen38-3090-beta.1` while carrying exact RTX 5090 beta.2
and stock OMP 18.12.6. This is not a new published or installable composition.
Native profiles now freeze the shared Host budgets (15,506,063,360 / 12,284,837,888 bytes),
extra slots 2/4, prefill 2,048/1,024, strict origin authentication and admission headroom
640/768 MiB. Pre-cut real-model C1 decode measured 137.35/78.33 tok/s at 131,072 INT8 MTP3;
final source/package qualification and Windows K6 evidence remain separate.

The native route moves to the published version 3 artifact `81f924d4` and fresh per-release
checkpoint roots; old native generations are not migrated. JSON-schema output remains a lane
qualification gate. Complete packages/dependency SBOMs, frozen N, actual review, fresh
route/client/public-install/rollback-lineage and independent restoration proof are still required.
Changed native model blocks require `documented_routes.document_change`; no prior 31-block
acceptance is relabelled. Published v0.13.0 authority/profiles remain untouched until a real lane pin.

## Remaining work

Items below remain open after `v0.13.0`; each names the current evidence showing the gap is still
unmet:

1. **Independent multi-owner clean-install, recovery, and rollback evidence.** All qualifications
   and 31-block documented-route acceptances through `v0.13.0` are maintainer-operated on owner
   hardware, and RTX 4090 has no rollback target (`not_applicable`) on the two-GPU Windows host
   ([`releases/v0.13.0/qualification.json`](releases/v0.13.0/qualification.json),
   [`releases/v0.13.0/qualification/rtx4090.json`](releases/v0.13.0/qualification/rtx4090.json),
   [`releases/v0.13.0/NINFER_RELEASE_NOTES.md`](releases/v0.13.0/NINFER_RELEASE_NOTES.md)).
2. **macOS managed lifecycle and native Linux OS qualification.** The macOS arm64 route remains a
   manual SSH tunnel preview without managed client installation or appliance lifecycle (`scripts/mac_tunnel.py`
   supervises only the local SSH forward), and the Linux x64 client is evidenced only under WSL2 on
   the Windows 11 container host rather than a native Linux OS
   ([`releases/v0.13.0/qualification.json`](releases/v0.13.0/qualification.json),
   [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md)).
3. **Hardware-independent public route qualification.** [`scripts/client_acceptance.py`](scripts/client_acceptance.py)
   and [`scripts/doctor.py`](scripts/doctor.py) provide host-free client rehearsals, live owner-lane
   checks, and named-cause WSL/Docker/loopback preflight, while full 31-block documented-route
   release qualification still requires live maintainer GPU-host windows
   ([`releases/v0.13.0/acceptance/documented-routes.json`](releases/v0.13.0/acceptance/documented-routes.json)).
   The earlier route-lifecycle tracker [#15](https://github.com/alphastorm/omp-ninfer/issues/15) is
   closed; it is historical context, not an open tracker for these additions.
4. **Distribution signing, notarization, and native dependency-level SBOM bindings.**
   [`scripts/generate_native_sbom.py`](scripts/generate_native_sbom.py) generates CycloneDX 1.5
   dependency SBOMs and the verifier supports `sbom_dependency_url` / `sbom_dependency_sha256`,
   while the carried Windows native runtime packages in
   [`releases/v0.13.0/manifest.json`](releases/v0.13.0/manifest.json) still ship unsigned with an
   SPDX file-inventory SBOM until rebased native packages are cut in `v0.13.1`
   ([`docs/SECURITY.md`](docs/SECURITY.md)). OMP NInfer consumes unmodified upstream OMP binaries by
   SHA-256 without rebuilding or re-signing the client; only first-party Windows runtime package
   signing is in scope here.
5. **Same-profile second-machine recovery and fixed fleet workload gates.** Off-machine replication
   via [`scripts/checkpoint_sync.py`](scripts/checkpoint_sync.py) is proven for local-loss recovery
   on the originating host ([`docs/measurements/2026-09-05-sync-probe-rtx5090.json`](docs/measurements/2026-09-05-sync-probe-rtx5090.json),
   [`docs/FACTS.md#checkpoint-transport-and-nas-replication`](docs/FACTS.md#checkpoint-transport-and-nas-replication)),
   not restoration onto a second physical inference host. The RTX 3090 fleet scout role remains
   disabled ([`releases/v0.13.0/NINFER_RELEASE_NOTES.md`](releases/v0.13.0/NINFER_RELEASE_NOTES.md)),
   and any fleet completed-work claim requires re-running the fixed multi-machine workload
   ([`scripts/fleet_dispatch.py`](scripts/fleet_dispatch.py), EXP-016 in
   [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md#experiment-ledger)).
6. **Rebased native Windows runtimes, JSON-schema output, and 128-character tool names (`v0.13.1`).**
   Enforced JSON-schema structured output (`text.format` and `response_format` `json_schema`) and
   128-character Chat/Responses tool names are qualified on the rebased RTX 5090 container lane in
   `v0.13.0` ([`releases/v0.13.0/qualification/protocol.json`](releases/v0.13.0/qualification/protocol.json),
   [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md)). The carried native RTX 4090 and RTX 3090
   packages still reject JSON-schema output with HTTP 400 and cap tool names at 64 characters;
   prepared rebased native profiles on `64d10fbf` add `--admission-headroom-mib` 640 MiB on RTX
   4090 and 768 MiB on RTX 3090 plus strict origin authentication. Frozen-source packages,
   dependency SBOMs, Windows K6/grammar/hardware qualification and fresh acceptance remain
   the `v0.13.1` gates, not claims established by the pre-cut decode experiment.
7. **Native-lane concurrency.** Both native Windows lanes are qualified at one active request
   (`--max-concurrency 1`, 30 s pending timeout) and run sequentially on shared port `18082`
   ([`releases/v0.13.0/qualification/rtx4090.json`](releases/v0.13.0/qualification/rtx4090.json),
   [`releases/v0.13.0/qualification/rtx3090.json`](releases/v0.13.0/qualification/rtx3090.json),
   [`examples/manual-tunnel/fail-closed.yml`](examples/manual-tunnel/fail-closed.yml)); concurrent
   native requests require memory and latency qualification on those exact packages.
8. **Open kernel and schedule backlog.** Verify-round host-commit idle time
   ([`docs/measurements/2026-10-03-dflash2-round-costs-rtx5090.json`](docs/measurements/2026-10-03-dflash2-round-costs-rtx5090.json),
   EXP-058 and EXP-092), Q4/Q5 GEMV/MMA epilogue fusion (EXP-056), and warm-turn template fragment
   consolidation (EXP-059) remain open in [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md#ideas-backlog).

## Deferred and rejected decisions

Negative and deferred results stay visible in [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md#experiment-ledger)
so future work does not repeat closed experiments:

- **Wholesale upstream engine merge — prior deferral superseded by v0.13.0 (EXP-097).** Earlier upstream
  NInfer (`594930e7`, `e31bc99b`, `81c8ce09`) trailed the fork by 18–19% on matched decode, lost
  sibling fanout reuse, overran the 32 GB automatic C2 BF16 budget by 561 MiB, and lacked the
  durable disk session store. The approved program re-ports the durable/runtime families onto
  master `64d10fbf`; default native packages carry unchanged if native rebases miss the window.
  EXP-097 clears the founder-amended 96% median decode floor at 101.09%, while retaining the
  structured-output p95 regression and continuation-depth caveats
  ([complete comparison](docs/measurements/2026-10-25-exp097-role-corpus.json)). Earlier observations remain historical
  ([`docs/UPSTREAM.md`](docs/UPSTREAM.md),
  [`docs/measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json`](docs/measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json),
  [`docs/measurements/2026-10-10-upstream-81c8ce09-rtx5090.json`](docs/measurements/2026-10-10-upstream-81c8ce09-rtx5090.json)).
- **Ada (`sm_89`) small-T Q5 tensor-core verify route — rejected (EXP-069).** Measured +0.38% decode
  at 26K and +0.40% at 60K on the RTX 4090, below the 2.0% and 1.0% promotion margins
  ([`docs/measurements/2026-09-28-rtx4090-q5-small-t-mma.json`](docs/measurements/2026-09-28-rtx4090-q5-small-t-mma.json)).
- **DFlash2 on the native RTX 4090 and RTX 3090 lanes — rejected for 24 GB profiles (EXP-089).**
  Does not link for `sm_89` or `sm_86` and its 1.65 GiB draft weights do not fit the 131,072-token
  24 GB budget; native lanes retain MTP3
  ([`docs/measurements/2026-10-01-dflash2-native-lanes-feasibility.json`](docs/measurements/2026-10-01-dflash2-native-lanes-feasibility.json)).
- **NVFP4 and FP8 KV caches with DFlash2 on the RTX 5090 — rejected by quality screen (EXP-084,
  EXP-085, EXP-087, EXP-088).** Raised KV capacity to four device state slots, but failed the
  1,120-prompt paired quality screen on unsupported claims or secret leaks; BF16 KV remains shipped
  ([`docs/measurements/2026-10-01-dflash2-powered-quality-screen-rtx5090.json`](docs/measurements/2026-10-01-dflash2-powered-quality-screen-rtx5090.json),
  [`docs/measurements/2026-10-01-dflash2-fp8-kv-quality-screen-rtx5090.json`](docs/measurements/2026-10-01-dflash2-fp8-kv-quality-screen-rtx5090.json)).
- **Deeper speculative drafting and 8-bit KV on RTX 5090/4090 — rejected (EXP-011..014, EXP-041,
  EXP-092).** MTP K=5 and K=7 trailed MTP3 by 7.3–24.7%
  ([`docs/measurements/2026-09-04-rtx5090-mtp-agent-ablation.json`](docs/measurements/2026-09-04-rtx5090-mtp-agent-ablation.json)),
  DFlash2 K=15 did not pay
  ([`docs/measurements/2026-10-03-dflash2-round-costs-rtx5090.json`](docs/measurements/2026-10-03-dflash2-round-costs-rtx5090.json)),
  and INT8/FP8 KV on the groupwise-int artifact regressed the private role-corpus screen
  ([`docs/measurements/2026-09-04-rtx5090-variant-campaign.json`](docs/measurements/2026-09-04-rtx5090-variant-campaign.json),
  [`docs/measurements/2026-09-16-two-long-session-capacity.json`](docs/measurements/2026-09-16-two-long-session-capacity.json)).
- **Beyond-131,072-token context extensions — parked.** Paged host-to-device KV prefetch and
  E8-lattice/RotorQuant ceiling work remain parked in
  [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md#ideas-backlog) until contexts above 131,072 tokens are
  in scope.

## Path to v1.0

A public release does not imply a v1.0 or SLA commitment. v1.0 means the durability contract —
save is atomic and verified, restore is verified-or-refused, sessions survive process death, and
private state never crosses sessions — holds under independent eyes, not just owner receipts.
Before a v1.0 decision:

- gather clean-install, recovery, and (where supported by the topology) rollback evidence from
  multiple independent owners for each claimed GPU profile;
- sign the first-party Windows runtime packages or retain the explicit unsigned and stock-client
  provenance boundary;
- close the highest-signal public-release installation and compatibility failures;
- publish supported upgrade and security-fix windows, rollback ownership, and response-time
  expectations without implying an SLA;
- run the fixed multi-machine workload before making any fleet completed-work claim; and
- cut a new release candidate if any executable component, model, configuration, or support
  boundary changes.

Explicitly not on this path (a new product decision, not a milestone): multi-tenant serving,
priority or preemptive scheduling, universal hardware claims, and silent cloud fallback.

## Shipped

Every release keeps its immutable manifest, qualification receipts, and release notes; full
per-version history lives in [`CHANGELOG.md`](CHANGELOG.md) and [`docs/RELEASES.md`](docs/RELEASES.md).

| Release | Date | Summary | Notes |
| --- | --- | --- | --- |
| `v0.13.0` | 2026-10-25 | Rebase RTX 5090 container (`v0.7.0-qwen38-5090-beta.2`, source `6d4d0a05`) onto upstream master `64d10fbf` with model v3 (`81f924d4`), schema 3 checkpoints (`checkpoints-v013`, strict origin auth, non-blocking export), JSON-schema output, 128-character tool names, and stock OMP 18.12.6; carry native RTX 4090 and RTX 3090 packages re-accepted with OMP 18.12.6 | [notes](releases/v0.13.0/NINFER_RELEASE_NOTES.md) |
| `v0.12.2` | 2026-10-18 | Repin stock OMP 18.12.1 (native Windows `C:` path fix, two `omp -p` exit-status fixes) across all five documented routes (31 blocks) with unchanged GPU runtimes, models, and profiles | [notes](releases/v0.12.2/NINFER_RELEASE_NOTES.md) |
| `v0.12.1` | 2026-10-12 | Repin stock OMP 18.10.1 across all five documented routes (31 blocks) with unchanged GPU runtimes, models, and profiles | [notes](releases/v0.12.1/NINFER_RELEASE_NOTES.md) |
| `v0.12.0` | 2026-10-11 | Restore native Windows RTX 4090 (`v0.6.11`) and RTX 3090 (`v0.6.3`) UUID-bound on one two-GPU host (one active lane on port 18082) | [notes](releases/v0.12.0/NINFER_RELEASE_NOTES.md) |
| `v0.11.0` | 2026-10-10 | Ship RTX 5090 `v0.6.16` (`1302d639`, EXP-092/EXP-094 DFlash2 round-cost reductions) and stock OMP 18.8.7 with per-model stateful Responses | [notes](releases/v0.11.0/NINFER_RELEASE_NOTES.md) |
| `v0.10.0` | 2026-10-02 | Adopt DFlash2 draft window 7 with BF16 KV (`v0.6.15`, model `0634abb0`) on RTX 5090 and repin all clients to stock OMP 18.4.10 | [notes](releases/v0.10.0/NINFER_RELEASE_NOTES.md) |
| `v0.9.1` | 2026-10-01 | Add RTX 3090 native Windows lane (`v0.6.2`, 300 W cap, one request in flight) on the mainline runtime; accept all five routes | [notes](releases/v0.9.1/NINFER_RELEASE_NOTES.md) |
| `v0.9.0` | 2026-09-30 | Qualify two requests in flight on RTX 5090 (`v0.6.14`, Q5 tensor-core 8-token MTP3 verify) with provider in-flight limits (EXP-077) | [notes](releases/v0.9.0/NINFER_RELEASE_NOTES.md) |
| `v0.8.7` | 2026-09-29 | Keep long-session prefix cache across compaction handoffs, near-capacity turns, and checkpoint-quota pressure on RTX 5090 and RTX 4090 (EXP-074) | [notes](releases/v0.8.7/NINFER_RELEASE_NOTES.md) |
| `v0.8.6` | 2026-09-28 | Compact long sessions inline (`compaction.asyncEnabled: false`) and harden documented nonce recall planting on stock OMP 18.4.0 (EXP-072, EXP-073) | [notes](releases/v0.8.6/NINFER_RELEASE_NOTES.md) |
| `v0.8.5` | 2026-09-28 | Repin to stock OMP 18.4.0 for Windows completion status and set `supportsImageDetailOriginal: false` on RTX 5090 (EXP-070, EXP-071) | [notes](releases/v0.8.5/NINFER_RELEASE_NOTES.md) |
| `v0.8.4` | 2026-09-28 | Ship `sm_89` 50 ms/100 ms GPU keep-warm on RTX 4090 (`v0.6.9`) and advance clients to stock OMP 18.3.5 (EXP-064, EXP-066) | [notes](releases/v0.8.4/NINFER_RELEASE_NOTES.md) |
| `v0.8.3` | 2026-09-27 | Speed up RTX 5090 decode with `sm_120` small-T tensor-core Q5 verify projections (`v0.6.12`) after 504-pair redaction screen (EXP-057, EXP-063) | [notes](releases/v0.8.3/NINFER_RELEASE_NOTES.md) |
| `v0.8.2` | 2026-09-26 | Add 60 s single-warp GPU keep-warm (`--gpu-keep-warm-ms 60000`) on RTX 5090 (`v0.6.11`) for idle agent arrivals (EXP-062) | [notes](releases/v0.8.2/NINFER_RELEASE_NOTES.md) |
| `v0.8.1` | 2026-09-25 | Speed up MTP3 verify decode on RTX 5090 (`v0.6.10`) and RTX 4090 (`v0.6.8`) with shared activation loads (EXP-055) | [notes](releases/v0.8.1/NINFER_RELEASE_NOTES.md) |
| `v0.8.0` | 2026-09-25 | Switch to unmodified upstream OMP 18.3.0 binaries with `prompt_cache_key` durable session routing (EXP-053) | [notes](releases/v0.8.0/NINFER_RELEASE_NOTES.md) |
| `v0.7.4` | 2026-09-24 | Retry transient automatic checkpoint refusals, save before eviction, and protect sibling checkpoints under quota (EXP-049..051) | [notes](releases/v0.7.4/NINFER_RELEASE_NOTES.md) |
| `v0.7.3` | 2026-09-18 | Repin client to `omp-18.2.3-cross-platform-beta-1` across macOS, Windows, and Linux with unchanged v0.7.2 runtimes (EXP-046) | [notes](releases/v0.7.3/NINFER_RELEASE_NOTES.md) |
| `v0.7.2` | 2026-09-17 | Reclaim checkpoint-backed resident sessions under host-KV pressure during restore on RTX 5090 and RTX 4090 (EXP-047) | [notes](releases/v0.7.2/NINFER_RELEASE_NOTES.md) |
| `v0.7.1` | 2026-09-16 | Raise RTX 4090 host-KV pool to 11,264 MiB so ceiling-sized checkpoints restore, and refuse unrestorable exports (EXP-043, EXP-044) | [notes](releases/v0.7.1/NINFER_RELEASE_NOTES.md) |
| `v0.7.0` | 2026-09-16 | Double RTX 5090 host-KV pool to 16 GiB (28 GiB host floor) so two alternating 131,072-token sessions keep prefix reuse (EXP-041) | [notes](releases/v0.7.0/NINFER_RELEASE_NOTES.md) |
| `v0.6.10` | 2026-09-16 | Refuse RTX 5090 container launch when bind mounts fail throwaway staging preflight and document reboot recovery (EXP-040) | [notes](releases/v0.6.10/NINFER_RELEASE_NOTES.md) |
| `v0.6.9` | 2026-09-13 | Port upstream Qwen tool-parser semantics and deep-union bounds onto shared source `696e78c7` for RTX 5090 and RTX 4090 | [notes](releases/v0.6.9/NINFER_RELEASE_NOTES.md) |
| `v0.6.8` | 2026-09-13 | Unify RTX 5090 and RTX 4090 on source `68a0722f` and fix HTTP 500 on live-sibling fork continuation (EXP-036, EXP-037) | [notes](releases/v0.6.8/NINFER_RELEASE_NOTES.md) |
| `v0.6.7` | 2026-09-13 | Backport 18 upstream NInfer engine commits into RTX 5090 runtime `v0.6.3` within noise of v0.6.2 (EXP-035) | [notes](releases/v0.6.7/NINFER_RELEASE_NOTES.md) |
| `v0.6.6` | 2026-09-12 | Disable out-of-channel client startup update checks in the documented route configuration | [notes](releases/v0.6.6/NINFER_RELEASE_NOTES.md) |
| `v0.6.5` | 2026-09-12 | Run the primary macOS-to-Windows container quickstart route verbatim from its documented fenced blocks (EXP-033) | [notes](releases/v0.6.5/NINFER_RELEASE_NOTES.md) |
| `v0.6.4` | 2026-09-11 | Run all documented Windows quickstart routes verbatim from their fenced blocks and enforce LF line endings (EXP-032) | [notes](releases/v0.6.4/NINFER_RELEASE_NOTES.md) |
| `v0.6.3` | 2026-09-11 | Mount a persistent session checkpoint directory on the documented public RTX 5090 container route (EXP-031) | [notes](releases/v0.6.3/NINFER_RELEASE_NOTES.md) |
| `v0.6.2` | 2026-09-11 | Move the RTX 5090 container lane onto mainline runtime commit `63f28c95` alongside the native Windows lanes (EXP-030) | [notes](releases/v0.6.2/NINFER_RELEASE_NOTES.md) |
| `v0.6.1` | 2026-09-10 | Flush and checkpoint every live session on graceful Windows managed stop on the RTX 4090 native lane (EXP-028, EXP-029) | [notes](releases/v0.6.1/NINFER_RELEASE_NOTES.md) |
| `v0.6.0` | 2026-09-10 | Port the RTX 4090 native Windows lane onto the mainline context-cache runtime (`075d442e`, EXP-025..027) | [notes](releases/v0.6.0/NINFER_RELEASE_NOTES.md) |
| `v0.5.1` | 2026-09-08 | Preserve shared-anchor sibling fanout across restarts (warm arrival) and overlap SHA-256 restore streaming on RTX 5090 (EXP-022..024) | [notes](releases/v0.5.1/NINFER_RELEASE_NOTES.md) |
| `v0.5.0` | 2026-09-05 | Ship origin-authenticated checkpoint manifests on all three lanes and verified off-machine replication (`scripts/checkpoint_sync.py`, EXP-018) | [notes](releases/v0.5.0/NINFER_RELEASE_NOTES.md) |
| `v0.4.9` | 2026-09-05 | Replace per-segment DirectStorage reads with windowed staging on RTX 4090 and RTX 3090, cutting restore to seconds (EXP-017) | [notes](releases/v0.4.9/NINFER_RELEASE_NOTES.md) |
| `v0.4.8` | 2026-09-05 | Requalify per-lane configurations: RTX 5090 4-slot fanout anchor catalog, RTX 4090 2,048-token chunk, RTX 3090 131,072-token context | [notes](releases/v0.4.8/NINFER_RELEASE_NOTES.md) |
| `v0.4.7` | 2026-09-01 | Correct immutable runtime asset URLs in the v0.4.6 manifest with unchanged component bytes | [notes](releases/v0.4.7/NINFER_RELEASE_NOTES.md) |
| `v0.4.6` | 2026-08-31 | Add HMAC checkpoint-origin authentication on the RTX 5090 container lane (`ninfer#32`) | [notes](releases/v0.4.6/NINFER_RELEASE_NOTES.md) |
| `v0.4.5` | 2026-08-31 | Bring the RTX 3090 native Windows lane onto the v0.2 durable checkpoint and fanout train | [notes](releases/v0.4.5/NINFER_RELEASE_NOTES.md) |
| `v0.4.4` | 2026-08-31 | Decouple RTX 5090 checkpoint export from the engine lock with bounded buffered writes and sustained-idle debounce | [notes](releases/v0.4.4/NINFER_RELEASE_NOTES.md) |
| `v0.4.3` | 2026-08-31 | Add shared-page sibling fanout anchors, streamed checkpoint-import hash verification, and session isolation hardening on RTX 5090 | [notes](releases/v0.4.3/NINFER_RELEASE_NOTES.md) |
| `v0.4.2` | 2026-08-31 | Move the RTX 4090 native Windows lane to the durable v0.2 runtime with 102,075-token checkpoint restore | [notes](releases/v0.4.2/NINFER_RELEASE_NOTES.md) |
| `v0.4.1` | 2026-08-31 | Harden RTX 5090 checkpoint store with health-gated quota transitions and post-publish reclamation | [notes](releases/v0.4.1/NINFER_RELEASE_NOTES.md) |
| `v0.4.0` | 2026-08-30 | Ship transactional session checkpoints on the RTX 5090 container lane (109,589 retained tokens restored across a Docker restart) | [notes](releases/v0.4.0/NINFER_RELEASE_NOTES.md) |
| `v0.3.2` | 2026-08-30 | Correct template residue in the v0.3.1 RTX 4090 qualification summary with unchanged component bytes | [notes](releases/v0.3.2/NINFER_RELEASE_NOTES.md) |
| `v0.3.1` | 2026-08-30 | Promote the MTP3 speculative decoding package on the RTX 4090 native Windows lane (+17.04% Golden-equivalent wall time) | [notes](releases/v0.3.1/NINFER_RELEASE_NOTES.md) |
| `v0.3.0` | 2026-08-30 | First public GitHub `Latest` release across the RTX 5090, RTX 4090, and RTX 3090 lanes | [notes](releases/v0.3.0/NINFER_RELEASE_NOTES.md) |
| `v0.2.0-beta.1` | 2026-08-29 | Add native Windows RTX 4090 beta and RTX 3090 preview lanes, durable native checkpoints, and cross-platform OMP 18.0.9 fork archives | [notes](releases/v0.2.0-beta.1/NINFER_RELEASE_NOTES.md) |
| `v0.1.0-beta.1` | 2026-08-28 | Initial restricted RTX 5090 beta with exact manifest pinning and clean install from public URLs | [notes](releases/v0.1.0-beta.1/NINFER_RELEASE_NOTES.md) |

## How to help

- **Run OMP with subagents against a lane?** That fanout path is what shared-anchor continuation
  serves — file a
  [hardware report](https://github.com/alphastorm/omp-ninfer/issues/new?template=hardware-report.yml)
  with what you observe, pass or fail.
- **Measured something?** Submit the
  [performance result form](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml)
  for the [community results table](docs/BENCHMARKS.md#community-results).
- **CUDA or kernel work?** Claim an idea from the
  [performance backlog](docs/PERFORMANCE.md#ideas-backlog) and see
  [`CONTRIBUTING.md`](CONTRIBUTING.md).
- **RTX 3090, RTX 4090, or RTX 5090 owner?**
  [Get started](docs/QUICKSTART.md) with the matching published lane, then file a content-safe
  [hardware report](https://github.com/alphastorm/omp-ninfer/issues/new?template=hardware-report.yml)
  or [clean-install report](https://github.com/alphastorm/omp-ninfer/issues/new?template=clean-install-report.yml).
  Pass and fail reports both improve the observed matrix; one lane never authorizes package
  substitution in another.
