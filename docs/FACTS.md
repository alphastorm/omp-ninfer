# OMP NInfer — canonical facts

Last verified: 2026-09-17 · Current stable release: **v0.7.2**

Public-release claims on this page are bound to the
[v0.7.2 release manifest](../releases/v0.7.2/manifest.json) and its qualification receipts.
Candidate lane measurements and published-route acceptance remain separately attributed below.

## What it is

OMP NInfer is **durable local inference for coding agents**: the qualified local inference
appliance for Oh My Pi. It runs Qwen3.8 27B through the NInfer engine on one NVIDIA RTX 5090,
4090, or 3090 and preserves explicit OpenAI Responses continuation state across process restarts.

## Entity relationships

```text
Oh My Pi     = the coding-agent client (github.com/can1357/oh-my-pi)
OMP NInfer   = this project: the qualified integration, release, and appliance layer
NInfer       = the C++/CUDA inference engine (Neroued/ninfer and its GPU ports)
Qwen3.8 27B  = the served model (registered NInfer artifact, hash-pinned per release)
```

## Best fit

All of these should be materially true:

- the operator uses, or intends to use, Oh My Pi;
- they own a qualified RTX 5090, 4090, or 3090 setup;
- Qwen3.8 27B is the model they want;
- sessions are long-lived and stateful, and restart recovery matters;
- privacy and owned hardware matter more than breadth or multi-user throughput.

## Not a fit

- A GUI-first local experience (use LM Studio).
- Broad model catalogs and quick experimentation (use Ollama or LM Studio).
- Unsupported hardware or maximum portability (use llama.cpp).
- Multi-user or high-concurrency serving (use vLLM).
- Generic OpenAI-compatible inference without the durability contract.

## Qualified hardware

| Lane | Form | Context ceiling | Release |
|---|---|---:|---|
| RTX 5090 | Linux container (Docker/WSL2) | 131,072 | v0.7.1 binds component `v0.6.5-qwen38-5090-beta.1`, public profile `qwen38-5090-v0.7.0`, 16384 MiB host KV and a 28672 MiB runtime-host floor; the historical two-session restore boundary is recorded below |
| RTX 4090 | native Windows service | 131,072 | v0.7.1 binds component `v0.6.4-qwen38-4090-beta.1` (sm_89; INT8 KV, MTP3, prefill chunk 2,048), 11264 MiB host KV, 24 host-state slots and a 32768 MiB runtime-host floor |
| RTX 3090 | native Windows service | 131,072 | unchanged durable `v0.2.5-qwen38-3090-beta.1` lane (origin-authenticated checkpoints, bound by v0.7.1) |

## v0.7.2 — bounded restore reclaim

- Published exact-profile product. Runtime qualification and public-route acceptance are
  recorded separately; the changed RTX 5090 and RTX 4090 components passed both.
- Both mainline lanes target reviewed source `d125ffffd87ef38d9a221f9830e19dfa274ddd34`: RTX 5090
  `v0.6.7-qwen38-5090-beta.1` and RTX 4090 native
  `v0.6.5-qwen38-4090-beta.1`. Restore can save and reclaim reproducible checkpoint-backed
  resident sessions, then retry with a fresh reader under bounded progress. A pool must still
  admit the session being restored; this is not unbounded capacity or universal durability.
- The final RTX 5090 candidate restored both target sessions (125,891 and 125,892 input tokens)
  in 5.96 s and 23.57 s, with 125,906 and 125,907 cached continuation tokens. Its combined
  process also reported three unsaved predecessor sessions at shutdown (`saved 2`, `refused 3`)
  and three automatic checkpoint refusals. The extra multisession control lost warm reuse on
  2 of 8 continuations/forks without server errors. Neither loss-free shutdown for all sessions
  nor universal warm reuse is established.
- The final RTX 4090 package passed 15 qualification phases with exact 130,048-token retrieval,
  153.431 tok/s decode and 2,113.995 tok/s prefill on the recorded fixture. Earlier smaller-pool
  experiments are not qualification of a smaller supported host or equivalent automatic durability.
- Public profile and serving knobs stay unchanged: RTX 5090 `qwen38-5090-v0.7.0`, 16384 MiB
  host KV, 28672 MiB runtime-host floor; RTX 4090 11264 MiB host KV, 24 host-state slots,
  32768 MiB floor. Scratch qualification settings do not replace those profiles. OMP remains
  18.0.9; RTX 3090 and the model are unchanged.
- [EXP-047 `final_reviewed_candidate`](measurements/2026-09-17-restore-reclaim.json) ·
  [release notes](../releases/v0.7.2/NINFER_RELEASE_NOTES.md). Earlier EXP-047 findings are attributed
  to their predecessor binaries and do not substitute for this final source-bound evidence.

## v0.7.1 — a reported save is a restorable save

- Restore materialises a continuation's KV into the host-KV pool, so that pool - not the device KV
  arena - bounds the largest session a configuration can admit back, and two sessions need their
  sum.
- The RTX 4090 native lane shipped a 4096 MiB pool against a 5.02 GiB ceiling-sized session. A
  125,888-token session's explicit checkpoint reported 4,834,325,255 B saved and the session
  answered HTTP 404 after a graceful stop and restart. The lane now ships 11264 MiB (component
  `v0.6.4-qwen38-4090-beta.1`): two ceiling sessions keep reuse, both checkpoint, a graceful stop
  reports `saved 2, nothing to save 0, refused 0`, and both resume exactly.
- That pool is pinned memory, so the lane declares `runtime_host.minimum_runtime_memory_mib`
  32,768; 12288 MiB fails `cudaMallocHost` on a 32.4 GiB host.
- An export is refused when the configuration could not admit the checkpoint back (HTTP 409,
  `checkpoint save refused: program refused continuation export`), a declined restore names its
  gate, and the startup line publishes `host-kv-restorable=<tokens>`.
- The RTX 5090's two-session restore boundary has the same cause: two BF16 ceiling sessions need
  about 18 GiB against that lane's 16 GiB pool. A 20 GiB pool restores both but reaches 28.28 GiB
  of a 31.34 GiB utility VM, so the lane keeps its pool and reports the boundary.
- [EXP-043](measurements/2026-09-16-restore-bound-host-kv-pool.json) ·
  [EXP-044](measurements/2026-09-16-rtx4090-v064-durability-requalification.json) ·
  [pool ladder](measurements/2026-09-16-rtx4090-host-kv-pool-ladder.json).

## v0.7.0 — two long sessions keep their reuse

- The RTX 5090 serving configuration advances to a 16 GiB Host KV pool (deployment profile
  `qwen38-5090-v0.7.0`); the component, image, model, client and KV dtype are unchanged.
- Two sessions at the 131,072-token ceiling keep prefix reuse on alternating turns: each
  continuation reuses about 125,900 cached tokens in 1.6-3.5 s. The shipped 8 GiB pool loses every
  one of them to a root re-prefill of about 58 s. Entering the steady state from a pool another
  long session occupies costs one re-prefill per session, once.
- The pool is pinned runtime-host memory, so the profile declares
  `runtime_host.minimum_runtime_memory_mib` 28,672 and the documented launcher refuses a smaller
  host. The same configuration in a 24 GiB WSL VM is OOM-killed mid-request (exit 137).
- Both 8-bit KV dtypes fix the same reuse loss and were rejected on quality, measured on one
  runtime: fp8 and int8 both drop the private corpus' redaction control pass rate from 0.750 to
  0.625 and add a secret leak, and int8 also adds unsupported claims and critical misses.
- Durability is narrower than reuse and the boundary is measured: both sessions checkpoint
  (9.24 GB each) and a graceful stop saves both, but after a restart one of the two is accepted
  back and the other's checkpoint is declined - refused, not corrupted.
- Configuration identity changes, so checkpoints written under `v0.6.10` do not carry across.
- [EXP-041](measurements/2026-09-16-two-long-session-capacity.json) ·
  [lane gates](measurements/2026-09-16-rtx5090-v070-profile-gates.json).

## v0.6.10 — the documented route refuses a launch the engine cannot stage

- No component, model, client, or serving configuration changed from `v0.6.9`; no lane
  requalification was required or performed.
- Docker Desktop stages a container's bind mounts once, at creation, from the filesystem those
  paths live on. After that filesystem's WSL distro restarts - which every host reboot does - an
  existing container either refuses to start (`not a directory` against the staging placeholder,
  recorded as exit `127` with `RestartCount 0`, which no restart policy retries) or starts with
  empty file mounts until the server rejects its own empty `--api-key`, prints usage and exits `1`.
- `examples/manual-tunnel/start-ninfer.sh` proves the mounts inside a throwaway container before
  loading the 18 GB artifact and refuses with what that container saw. Recovery on this route is
  recreation - `stop-ninfer.sh` then the same `start-ninfer.sh` - which the durable store makes a
  continuation rather than a loss.
- Acceptance re-ran both RTX 5090 documented routes from the candidate: host 2/2 blocks and macOS
  10/10 blocks against the unchanged published image
  ([routes](../releases/v0.6.10/acceptance/documented-routes.json)).
- [EXP-040](measurements/2026-09-16-lane-reboot-survivability.json) records the owner appliance's
  26 h 51 min outage from this cause, four authorised reboots recovering the lane unattended, and
  the first receipt of the RTX 4090 native lane's documented post-reboot start with its
  checkpointed session resuming exactly.

## v0.6.9 — Qwen parser semantic port

- Reviewed runtime source: `696e78c7b4e3ac28ffcffafc73acc1496e65ef03`. Published components:
  RTX 5090 `v0.6.5-qwen38-5090-beta.1` (image `5e3e1558…`) and RTX 4090 native
  `v0.6.3-qwen38-4090-beta.1`. Model, OMP client, RTX 3090 component, and serving settings
  are unchanged.
- Independently implemented semantic port of upstream Qwen parser fixes `3b50962b` and
  `0c5d570c`, not a serve-adapter rebase: supported scalar unions, case-insensitive booleans,
  precise numeric lexemes and mathematically integral values, duplicate parameters, and
  balanced embedded markup. Custom raw input, history, opaque IDs, and stream ownership
  are preserved. Malformed-region rescans and recursive union traversal are removed; bytewise
  regressions and an 8,192-deep union case pass.
- RTX 5090 lifecycle qualification: profile `qwen38-5090-v0.6.2` / configuration `5eb8a557`,
  unchanged. The public deployment profile remains `qwen38-5090-v0.6.3` / `622ab621`; its
  route passed separately: host 2/2 and macOS 10/10 documented blocks, exact 130,048-token
  retrieval at 2,153.6 tok/s and decode at 133.76 tok/s wall.
- Candidate measurements: RTX 5090 exact 130,048-token retrieval at 2,193.3 tok/s and
  2,048-token decode at 134.87 tok/s wall; RTX 4090 15/15 native phases, exact retrieval in
  91.2377 s and C1 decode 153.464 tok/s at 87.58865% MTP acceptance.
  [Measurement scope and receipts](BENCHMARKS.md#v069-candidate--qwen-tool-parser-semantic-port-2026-09-13) ·
  [Release notes](../releases/v0.6.9/NINFER_RELEASE_NOTES.md).
- RTX 4090 public-URL already-installed acceptance passed: exact bytes accepted, no pointer
  change or runtime start requested, authenticated status 200, anonymous status 401, completion
  marker accepted, stopped state and 450 W restored
  ([receipt](../releases/v0.6.9/acceptance/rtx4090-public-install.json)). No fresh-install claim.

## Current model and artifact

Registered NInfer conversion of Qwen3.8 27B (`qwen3_8_27b.ninfer`, groupwise-int weights,
18,210,531,328 bytes), artifact SHA-256 `eec39564…14bf3e`, pinned identically across all three
lanes by the release manifest.

## Supported APIs

OpenAI Responses (stateful continuation — the primary product surface), OpenAI chat completions,
and Anthropic Messages, all loopback-only and bearer-authenticated. Session checkpoint
save/status/delete under `/v1/ninfer/checkpoints`.

## The durable-state guarantee

Explicit, transactional continuation checkpoints that survive process death: sessions are
checkpointed to local NVMe (SHA-manifested, atomically published generations) and restored
exactly — the restored frontier is verified, and a wrong-profile checkpoint is rejected rather
than partially loaded. This is a stronger, explicit contract than in-process prefix caching.

As of v0.4.4 on the RTX 5090 lane, sibling agent branches of one `previous_response_id` reuse
the base prefill through the session's private long anchors, and checkpoint exports run off the
engine execution lock (four branches: 148.7 s → 3.84 s at a 67.7K-token base; warm follow-up
during checkpoint traffic 0.91 s; automatic saves debounce to sustained-idle and skip
already-catalogued frontiers). Measured on 2026-09-04, that sibling reuse holds for templates of
roughly 64K tokens or more; a 57.9K-token template alternated anchored and re-prefilled forks, and
restoring a checkpoint after a restart was no faster than re-prefilling it on any lane
([EXP-012](PERFORMANCE.md#experiment-ledger)); the sub-64K loss is context-cache capacity, and a larger
private catalog with scaled state slots removed it on the unchanged binary as the v0.4.8 candidate
profile ([EXP-013](PERFORMANCE.md#experiment-ledger)). As of `v0.5.1` the restored template also
arrives warm across a restart on the RTX 5090: every sibling fork is served on the shared anchor in
either arrival order, and a 5.2 GB restore takes 3.8 s
([EXP-022/EXP-023](PERFORMANCE.md#experiment-ledger)).

Operators may describe this problem as persistent KV cache, restartable context, session
checkpointing, stateful local inference, or avoiding cold re-prefill. The actual guarantee is
explicit restorable continuation state; it does **not** claim that new input avoids prefill.

## Checkpoint transport and NAS replication

**Available now, not roadmap-only:** [`checkpoint_sync.py`](../scripts/checkpoint_sync.py)
exports published checkpoint generations, verifies their file sizes and SHA-256 hashes, and
imports replicas into a local checkpoint root. Copies can be stored on another host or a NAS.
This is explicit export/import, not automatic failover or live session migration.

- **Recovery proved on all three lanes:** export → carry off-machine → remove local state with
  the server stopped → carry back → import → restart → exact retrieval of planted keys
  ([5090](measurements/2026-09-05-sync-probe-rtx5090.json),
  [4090](measurements/2026-09-05-sync-probe-rtx4090.json),
  [3090](measurements/2026-09-05-sync-probe-rtx3090.json)). These are the 2026-09-05 profiles,
  not a new sync qualification of every later runtime release.
- **Transport proved separately:** [cross-site host transport](measurements/2026-09-06-replica-transfer-paths.json)
  and [NAS replication](measurements/2026-09-07-nas-replication-sf-lanes.json). The NAS run
  copied and verified one published generation from each co-located native lane; it did not
  exercise runtime restore from the NAS or change the release lifecycle.
- **Restore compatibility:** the runtime fingerprint binds the binary, model artifact, and
  profile; the session namespace and origin authentication bind the bearer key. A remote
  storage destination need not have a GPU, but restoring the state needs the matching runtime
  environment and credentials. These receipts do not demonstrate running a 5090 session on a
  4090, cross-version conversion, or resuming on a second inference host.
- **Local runtime storage only:** O_DIRECT/DirectStorage require a local checkpoint root.
  Import from the replica before restore; do not point the server at a network share.
- **Integrity is not origin authentication or encryption:** sync checks payload hashes and
  requires `manifest.mac` by default; the runtime verifies that tag under
  `--session-checkpoint-require-origin-auth`. Protect replica access and transport as private
  session data. Do not use `--allow-unauthenticated` for imports across a trust boundary.

Use the sync tool's [export/import examples](../scripts/checkpoint_sync.py) and
`python3 scripts/checkpoint_sync.py --help`. Publish the intended checkpoint before export,
stop the destination runtime before import, and keep its matching profile and credentials.
The [roadmap](../ROADMAP.md#v05x--sessions-leave-the-machine) records the original experiments
and their limits.

## Security boundary

Loopback-only listeners; bearer authentication with a user-only key file; fail-closed instead of
cloud fallback; every byte (model, binary, image, config) hash-pinned by the release manifest;
remote lanes reached through authenticated SSH local forwards.

## Measured proof (v0.4.0, RTX 5090 lane)

- 109,589 tokens restored after a docker restart; **0.778 s** to first token from the durable
  checkpoint vs **47.920 s** fresh-process cold rebuild.
- **144.80 tok/s** decode on the agent-shaped qualification gate (44.10% MTP acceptance);
  152.2 tok/s at 83.3% acceptance on the retrieval workload.
- Exact needle retrieval at a **130,048-token** prompt (2,180.3 tok/s cold on the v0.5.1 runtime, 2,207.10 on v0.4.8;
  the v0.4.0 gate measured 2,186.30 tok/s at 130,448 tokens).
- **138.16 tok/s** decode at 41.2% MTP acceptance on the v0.5.1 technical-writing gate (136.03 on v0.4.8).
- Full receipts: [benchmarks](BENCHMARKS.md) · [release manifest](../releases/v0.4.0/manifest.json).

Warm/cold figures are always retained state versus fresh-process cold start — never versus an
ordinary in-process follow-up.

## Known limitations

- One model, one active request per lane (max concurrency 1); not a serving farm.
- Checkpoints are runtime-fingerprint-bound: they restore only on an identical lane
  (same binary, artifact, and profile) — not across GPU models.
- The 3090 lane's comfortable working envelope is the 64K class.
- Vision is available on the 5090 container profile; the native Windows lanes are text-only.

## Claims we do not make

- "No re-prefill" — in-process prefix caching is prior art and conceded as such.
- "Fastest local inference" — figures are one profile on one machine, receipt-bound.
- "First persistent KV cache" — prior art is credited in [Related work](RELATED_WORK.md).
- Production/GA/SLA claims beyond the qualified envelope of the current release.

## Primary evidence

[Public release manifest](../releases/v0.6.10/manifest.json) ·
[Benchmarks and method](BENCHMARKS.md) · [Compatibility](COMPATIBILITY.md) ·
[Security model](SECURITY.md) · [Quickstart](QUICKSTART.md) ·
[Decision guide](DECISION_GUIDE.md)
