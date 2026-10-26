# Matched runtime campaigns

## Risk-scaled quality gates

Use `scripts/quality_gates.py` for ordinary admission. Gate **one combined candidate
per lane**, not each output-changing slice separately. The full EXP-085 screen
below is an escalation after a real problem, not the default or a full null-pair
machinery check.

All gates use the existing private qualification executor/scorer, temperature 0,
low reasoning and the same frozen corpus/model/profile on the same selected GPU.
Capture the shipped 84-case role baseline once per lane, then reuse its sealed
bytes for T1/T2. For example, repeat each bounded command with `--resume` in a new
external hold until it reports completion:

```sh
python3 scripts/quality_gates.py cache --kind role --lane rtx4090 \
  --plan PLAN.json --out ROLE_BASELINE --shard-size 42 --max-shards 1
python3 scripts/quality_gates.py t1 --lane rtx4090 --plan PLAN.json \
  --baseline ROLE_BASELINE --out BYTE_GATE --shard-size 42 --max-shards 1
```

Plans use the format below: A is the shipped baseline, B is the integrated candidate.
Both role arms must have exactly the same effective configuration, GPU, driver and
power. A stored cache is accepted only after reopening its prompt files, capture
seals, raw responses, scored samples, actual output bytes and actual token traces,
with matching binary/model/profile/sampling/corpus/tool identities.
Each capture is a fresh owned server and restores its found power limit.

- **T1, output-identical changes:** pass only when all **84/84 retained outputs
  compare byte for byte** and neither arm has a response error. The result lists
  identical/differing cases and per-case first divergent byte/token indices.
  Raw tool-argument strings are preserved; only nondeterministic tool IDs are
  excluded. The projection also includes content, reasoning and finish reason.
- **T2, rounding-only changes:** require the bound per-kernel FP64 proof, no more
  than **10% divergent role cases (at most 8/84)**, zero candidate task-check
  failures and the exact **130,048-token retrieval** answer. JSON outputs validate
  against their full declared schema; tool calls must name declared/required tools
  and parse into schema-valid JSON argument objects. Token indices come from the
  server's retained `generated_token_ids`, never bytes relabelled as tokens or a
  retokenization approximation. Captures refuse retries/extra requests that would
  make response-to-token ordering ambiguous.

Bind the four native small-T op tests' real verbose CTest log to the candidate:

```sh
python3 scripts/quality_gates.py fp64 --log CTEST_LOG \
  --server-binary IMMUTABLE_BIN/ninfer-serve.exe --out FP64.json
python3 scripts/quality_gates.py t2 --lane rtx4090 --plan PLAN.json \
  --baseline ROLE_BASELINE --numerics FP64.json --out ROUNDING_GATE \
  --shard-size 42 --max-shards 1
```

The log must contain exactly the four named Q5-add, Q4-SwiGLU, two-output and
multi-output linear tests, their reduction-error statistics and a complete
successful CTest summary. Test binaries must belong to the same immutable binary
set as the server. The proof records/rechecks source, executable and log hashes;
non-finite or out-of-limit errors cannot pass. T2's plan additionally supplies
`retrieval_fixture`, the existing long-NIAH messages. After the role shards, repeat
with `--resume` for the separately bounded retrieval capture. The gate reopens the
actual retained retrieval bytes instead of trusting an `exact` flag.

**T3, deliberate math changes:** first run the frozen held-out perplexity ON/OFF
pair at contexts 1,024/2,048 and strides 512/1,024, INT8 KV:

```sh
python3 scripts/quality_gates.py ppl --plan PPL_PLAN.json --out PPL_RUN
```

The private PPL plan supplies `model_path`, `model_sha256`, `gpu_uuid`, optional
`power_limit_w`, `candidate_server_binary`, `corpus_manifest`,
`corpus_manifest_sha256`, `corpus_provenance_sha256`, optional `runtime_paths`
(DLL directories), and `arms: {off: {binary, binary_sha256}, on: {...}}`.
Use ON/OFF PPL binaries from the frozen candidate build; never regenerate the
held-out streams. The runner uses the real `ninfer-perplexity` schema-2 reports,
verifies scored-token/domain/configuration equality and finite, consistent NLL.
**Any aggregate Δmean-NLL above 0.02 nats or domain above 0.05 nats fails:
the math route stays OFF.** Build provenance remains a separate admission gate.

Only after PPL passes, capture the targeted baseline once and run the candidate:

```sh
python3 scripts/quality_gates.py cache --kind math --lane rtx4090 \
  --plan PLAN.json --ppl PPL_RUN/result.json --out MATH_BASELINE \
  --shard-size 50 --max-shards 1
python3 scripts/quality_gates.py t3 --lane rtx4090 --plan PLAN.json \
  --baseline MATH_BASELINE --ppl PPL_RUN/result.json --out MATH_GATE \
  --shard-size 50 --max-shards 1
```

The deterministic 200-prompt plan has 100 grounded claim probes (two whitespace
variants of 50 class-balanced cases with forbidden-claim/support-span oracles) and
100 variants of the secret controls. Fifty-prompt shards alternate the categories;
the first 100 prompts cover every selected case/control. Every scored look is
retained. The pre-registered finite risk rule is:

1. Stop **invalid** on a response error, or **fail** on any task-check failure,
   newly leaked secret relative to its paired baseline (including a different
   secret at an unchanged leak count), or more than six introduced unsupported
   claims. Improvements never cancel an introduced regression.
2. Stop **pass** after at least 100 paired prompts only if all selected cases are
   covered and all their retained output bytes are identical, with PPL already
   passed.
3. Otherwise finish all 200 and pass only with zero newly leaked secret cases,
   at most six introduced unsupported claims (3% of the planned pairs), and no
   task/response failures.

This is a bounded, pre-registered risk screen, **not** EXP-085, a powered
non-inferiority estimate, or an optional-stopping p-value claim. A reported issue
can justify escalation; do not automatically spend a full 1,120-prompt pair.
DFlash2 draft quantization needs its target-verified speed gate, not a quality screen.

Gate commands return 0 for pass or a bounded partial capture, 1 for fail and 2 for
invalid evidence. A partial capture has no passing verdict; release/reacquire the
external lock and repeat with `--resume`. Completed early T3 decisions never start
more shards on resume. Use per-GPU locks for non-timing correctness gates; retain
the whole-host timing lock for throughput/latency measurements. Keep raw evidence
private and keep the complete deployment frozen while a cache/candidate uses it.

## Campaign runner

Use `scripts/hosts/run_variant_campaign.ps1 -Lane rtx4090 -Plan plan.json -Output runs/c1`
on native Windows, or `python3 scripts/hosts/variant_campaign.py --lane rtx5090 --plan plan.json
--out runs/c1` on Linux. These replace the three historical lane-specific scripts and
both standalone VRAM samplers. The older `scripts/run_variant_campaign.py` remains the
separate frozen variant-matrix reducer, not a host lifecycle driver.
When staging a subset, retain `scripts/hosts/{variant_campaign,common}.py` and
`scripts/{quality_screen,redaction_screen}.py` with their directory hierarchy.
Add `scripts/quality_gates.py` for the risk-tier commands.
Quality mode also needs the private qualification root's `manifest.schema.json`,
`scripts/{run_qualification,score_qualification,_qual}.py`, cases and fixtures.
Keep that whole input set frozen, not just the public runner.

## Ownership and measurement

- Run on the GPU host under the fleet's external GPU lock/lease. Do not run two cards
  on one shared host concurrently. The runner does not acquire a second lock domain.
- Servers must already be stopped through their owners. A listening campaign port is
  an error, never permission to kill it. Only the runner's processes/containers stop.
- The arm order is **A/B/B/A**, each a fresh server. The same model bytes, request
  construction and GPU UUID are used throughout. Every arm records binary/model SHA-256,
  version, effective configuration and its SHA-256, GPU UUID, driver and power limit.
  The exact launch argv is also recorded, including explicit port/model-ID overrides
  and scratch checkpoint locations; its hash is not a substitute for those private bytes.
- Sampling is built in (default 0.2 seconds) and mandatory. VRAM/power/temperature/GPU
  utilization samples and maxima include load, warmup and measured requests. A sampling
  failure invalidates the arm. `ready_memory_mib` separates loaded memory from peak.
- A requested per-arm power limit is applied only to the selected UUID. The found limit
  is restored in `finally`, including failures. The runner never installs a service,
  edits a release root, changes a driver or touches a production container.
- Evidence roots are private: logs, model paths, API key files and quality responses
  are not public receipts. Do not commit the plan or raw results to this repository.
- C1/role/custom output projections are retained in private `outputs/*.json` files:
  content, reasoning and tool calls, excluding transport/tool-call IDs. Final reduction
  reopens and compares those actual UTF-8 bytes, with a digest integrity check.
  A digest-only reduction is explicitly not reported as a byte comparison.

## Plan

A private JSON plan has this shape (use real paths/UUIDs, not these examples):

```json
{
  "lane": "rtx4090",
  "gpu_uuid": "GPU-REPLACE-WITH-SELECTED-UUID",
  "model_path": "E:/models/model.ninfer",
  "model_sha256": "REPLACE-WITH-FULL-MODEL-SHA256",
  "model_id": "qwen3.8-27b",
  "config_path": "E:/scratch/server-config.json",
  "arms": {
    "A": {"binary": "E:/baseline/bin/ninfer-serve.exe"},
    "B": {
      "binary": "E:/candidate/bin/ninfer-serve.exe",
      "overrides": {"engine": {"prefill_chunk": 2048}},
      "power_limit_w": 450
    }
  }
}
```

`config_path` uses the native packaged server configuration. `config` can instead hold
that object inline. Per-arm `config_path` and deep-merged `overrides` allow backend,
KV, chunk, slots and context experiments without changing installed files. Optional
`binary_sha256` freezes each arm's binary. `server_args` appends exact argv entries;
use configuration fields for flags already generated by the runner. Checkpoint stores
are scratch per-arm directories, never the installed store. Device selection uses
`CUDA_VISIBLE_DEVICES=<UUID>` and device 0 within that selected device set.

For Docker, each arm additionally supplies `image` (prefer an immutable digest) and
`binary` as its path **inside** that image. The Linux host runs Docker directly, using
loopback-only published ports, the selected GPU, a read-only model mount and per-arm scratch mounts.
The server binds `0.0.0.0` inside its container; publishing `127.0.0.1:PORT:PORT`
works with Docker Desktop/WSL as well as native Linux without host-networking settings.
Containers are named `ov-<holder>-*`; `holder` defaults to `harness`. No incumbent image
or container is stopped, removed or renamed. Port defaults: native 18082, Docker 18089;
`port` and `model_id` override them. The container image must include `sha256sum` and
support its server's `--version`.
If the lane requires reviewed io_uring syscalls, supply `seccomp_profile` (globally
or per arm) as the host path to its existing reviewed Docker seccomp JSON. Its SHA-256
and exact Docker argv are recorded. The runner never edits that shared policy or
substitutes an unconfined policy. Driver mounts are selected by UUID even for
`--version`, because the CUDA-linked ELF loader needs `libcuda.so.1`.
Checkpoint-enabled containers must use an **ext4 output root** (WSL's Linux filesystem),
not a DrvFS/9p Windows-drive mount. The per-arm `/campaign/checkpoints` store shares that
mount. The runner checks its host filesystem with `findmnt` before launching any
container and records it; it never tries to put an O_DIRECT checkpoint store on DrvFS.
Checkpoint-disabled smoke evidence can stay on a Windows-drive mount.

## Modes

`-Mode MODE` / `--mode MODE` selects:

- **c1** (default): the qualification `benchmark_c1` recipe: the same 28,000-character
  paragraph prompt, medium reasoning, seed 57004, temperature 0 and 1,024-token cap.
  After the qualification's 32-token warmup, the runner requires **4,541 prompt and
  computed-prefill tokens and exactly 1,024 completion tokens**, with no prefix hit.
  Server-reported prefill/decode times are bound to the request log. Non-matching
  counts fail instead of quietly becoming a different benchmark.
- **role**: uses the existing private qualification runner's prompt builder and case
  schema. Supply `qualification` (root with `scripts/`), `cases`, `fixtures` and optional
  `case_ids` (JSON array of frozen IDs). Defaults exclude only EXP-085's vacuous cases.
  `role_reasoning` defaults to `low`, `role_max_tokens` to 1024; authored smaller caps
  remain smaller. Optional `role_depths: [0,32000,64000]` pads each role case using the
  C1 paragraph. Two one-token chat requests calibrate the padding on **each** arm;
  measured chat-template prompt counts must be within 64 tokens of the target. This
  does not rely on nonexistent tokenizer endpoints. Use identical depth/cap settings,
  leave completion room below maximum context, and inspect measured prefix reuse.
  This is a decode performance/byte comparison, **not** the powered quality verdict.
- **retrieval**: supply `retrieval_fixture`, the engine's long-NIAH JSON messages. Requires
  130,048 prompt tokens and the exact expected answer, recording wall time and digest.
- **command**: `workload_command` is an argv array for an existing workload driver.
  Entries can use `{base_url}`, `{model_id}`, `{key_file}`, `{log}` and `{arm_dir}`.
  Its stdout/stderr go to `workload.log`; nonzero exit fails the arm. This lets the
  warm-turn/checkpoint and engine bench drivers retain their existing contracts.
- **requests**: `requests` is an array of `{ "id": "...", "body": {...} }` chat
  requests, sent identically in every arm (the served model ID is injected).
  Freeform reasoning and code probes use this without inventing corpus classes.
- **quality**: creates EXP-085's unmodified whitespace variants and first-80 determinism
  subset. A runs the screen, B the screen, B the subset on a fresh server, A the subset
  on a fresh server. Each is executed/scored by the private qualification tooling at
  concurrency 1, temperature 0, low reasoning, top-level reasoning wire and 8192 token
  headroom. Requires `qualification`, `cases`, `fixtures`. `result.json` contains the
  original powered verdict plus an actual model-output byte comparison. It never
  relaxes completeness, perturbation, determinism or primary metric margins.
  The sampler also records SM and memory clocks in MHz.

For lock fairness, run `--arm-index 0`, `1`, `2`, `3` (`-ArmIndex`) separately against
the same output root, releasing the external lock between arms. Arm N requires the
preceding receipt; existing arm directories are never silently overwritten/skipped.
Only a complete successful ABBA set yields a matched result. Freeze the plan before
starting: later arm invocations refuse changed plan or runner bytes. Failed arms are evidence; use a
new output root after changing inputs, not an unchanged retry.

## Endpoint-only quality capture

`scripts/quality_screen.py run --base-url http://127.0.0.1:18082 --model qwen3.8-27b
--api-key-file KEY --qualification ROOT --cases CASES --fixtures FIXTURES --out NEW_RUN`
accepts a server root or `/v1`, any HTTP(S) lane endpoint and either served native ID
(`qwen3.8-27b`, `q38-ninfer`) or container `q38-ninfer`. The requested ID must actually
be advertised by `/v1/models`; there is no lane-specific fallback. It records/scorers
one capture, not freshness. The caller owns restart and isolation.

`quality_screen.py pair --lane rtx4090 --plan PLAN --out NEW_ROOT` runs the managed
fresh-server sequence above. Existing `variants` and `verdict` commands and EXP-085's
statistical rule are unchanged. A self-pair passes only if the real outputs/validity
checks pass; binary identity alone is not evidence of output identity.
The managed `pair` and runner `--mode quality` return 0 for pass, 1 for a failed
primary gate and 2 for invalid evidence; a partial `--arm-index` capture is not a verdict.
The historical report-only `verdict` command retains its existing exit behavior.

### Bounded, resumable powered captures

Use a fixed shard size and limit each external lock hold explicitly:

```sh
python3 scripts/quality_screen.py pair --lane rtx4090 --plan PLAN.json \
  --out PRIVATE_RUN --shard-size 100 --max-shards 1
# Release/reacquire the external GPU lock, then repeat until result.json exists:
python3 scripts/quality_screen.py pair --lane rtx4090 --plan PLAN.json \
  --out PRIVATE_RUN --shard-size 100 --max-shards 1 --resume
```

The host runner accepts the same `--shard-size`, `--max-shards` and `--resume`
arguments with `--mode quality`. Its PowerShell wrapper exposes `-ShardSize`,
`-MaxShards` and `-Resume`. Do not combine sharding with `--arm-index` or profiling.
Without shard controls, the original whole-arm sequence remains available.

`shards.json` freezes a deterministic contiguous plan over the original prompt order:
A's full screen, B's full screen, B's fresh first-80 subset, A's fresh first-80 subset.
Both arms use identical boundaries; subset boundaries match the screen boundaries.
Every shard starts and stops its own server. A 1,120-prompt screen at size 100 needs
12 A captures, 12 B captures and two 80-prompt fresh captures: **26 captures, 2,400
requests**, with no reduction of EXP-085's statistical sample.

Resume first verifies every sealed capture and its identities, not just the next one.
It rejects changed plan, runner/helpers, qualification files, cases/fixtures, model,
binary/version, configuration, GPU/driver/power limit, prompt files, or retained
response/score/manifest bytes. Each shard retains a lifecycle receipt and an atomic
`complete.json` seal. An interrupted attempt without a receipt is preserved in its
own `attempt-*` directory; resume starts that shard again on a fresh owned server.
A finished/failed but unsealed capture is not silently retried: preserve it and use
a new campaign root. Never modify a frozen deployment while its campaign is active.

A bounded invocation returns `status: shard-complete` and no verdict while any
capture is missing. Only the complete verified set is merged and passed to the
unchanged EXP-085 reducer. `result.json` includes direct retained-byte comparison
of A versus B and both fresh determinism subsets, plus each shard's wall seconds
and wall seconds per 100 prompts (server startup/capture/cleanup included; manifest
and runtime identity preflight are additional hold overhead).
Choose a smaller fixed size before starting when a shard would exceed the host's
hold limit; a per-request timeout is not a whole-hold watchdog. The external worker
must enforce its own hold deadline and owned-process/power cleanup.

### Capture the shipped baseline once

When several output-changing changes will be screened as one integrated candidate,
do not run a full null pair. Capture the shipped baseline and its fresh first-80
subset once per lane:

```sh
python3 scripts/quality_screen.py baseline --lane rtx4090 --plan PLAN.json \
  --out PRIVATE_BASELINE --shard-size 100 --max-shards 1
# Repeat in separate per-GPU quality holds:
python3 scripts/quality_screen.py baseline --lane rtx4090 --plan PLAN.json \
  --out PRIVATE_BASELINE --shard-size 100 --max-shards 1 --resume
```

The plan's A arm is the shipped baseline; B is not captured by this command.
At size 100 the complete baseline is 12 screen shards plus one fresh 80-prompt
shard, **1,200 requests**, ending with `PRIVATE_BASELINE/baseline/baseline.json`
and `status: baseline-complete`. This is baseline evidence, not a paired verdict.
An existing sharded campaign's complete A screen and fresh A subset can be
exported without rerunning either:

```sh
python3 scripts/quality_screen.py baseline --from-campaign EXISTING_CAMPAIGN \
  --out PRIVATE_BASELINE_EXPORT
```

Then capture only the integrated candidate and its fresh subset:

```sh
python3 scripts/quality_screen.py pair --lane rtx4090 --plan PLAN.json \
  --baseline PRIVATE_BASELINE/baseline --out PRIVATE_CANDIDATE \
  --shard-size 100 --max-shards 1
# Repeat with --resume, releasing the external lock between captures.
```

`--baseline` accepts the exported directory or its `baseline.json`; the host
runner and PowerShell wrapper expose the same option (`-Baseline`). Keep plan A
pointing to the exact shipped baseline bytes/profile. Plan B may name the
intentionally changed candidate binary/profile. Baseline reuse refuses a mismatch
in A's binary/version, model, effective configuration, GPU/driver/power, prompt
set/order/shard boundaries, qualification/corpus/fixture bytes, or sampling/model
contract. It reopens the source shard seals and capture files and reconstructs
the merged bytes; editing a cached digest does not bless changed evidence.
Candidate resume additionally freezes its own runner, plan, baseline binding and
runtime identities. Never overwrite a frozen baseline or candidate deployment.

Only a full baseline plus full candidate plus both fresh 80-prompt subsets can
produce EXP-085's unchanged powered verdict. Missing/errored model responses are
reported in byte comparisons, not silently presented as successful identical
outputs; the registered one-percent error bound remains the quality validity rule.

## Nsight Systems

`--nsys` / `-Nsys` prefixes the server with Nsight Systems CUDA/NVTX tracing and CUDA
Graph node tracing, then exports SQLite per-op GPU totals, launch-correlated
MTP/DFlash round attribution, individual prefill ranges/payloads/per-op GPU shares,
and `cudaGraphLaunch` CPU calls/mean time. Set `nsys_path` globally or per-arm when it
is not on PATH; for Docker it is a path inside the image. Profiling is optional, but
if requested a missing tool/capture/activity table is an error, not an empty success.
The diagnostic trace includes startup and warmup. Do not compare its timings as
release throughput, equate CPU NVTX spans with GPU time, or add graph-launch CPU time
to overlapped GPU execution. For a bench that brackets its measured repetition, use
its existing `--profile-measured`/cudaProfilerApi contract through command mode rather
than labeling the whole server capture measured-only.

## Checks

Run focused host-free units with `python3 -m unittest discover -s tests -p
 'test_host_variant_campaign.py'`, plus `test_quality_screen.py` and `test_native_gpu.py`.
The product suite remains `python3 -m unittest discover -s tests` followed by
`python3 scripts/verify_release.py --require-ready`. Real-host evidence is separate
from mocked lifecycle/SQLite tests; neither is a substitute for the other.
