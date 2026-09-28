# OMP NInfer — canonical facts

Updated: 2026-09-28 · **Current public release: v0.8.6.**

The [v0.8.6 manifest](../releases/v0.8.6/manifest.json) binds the stock-client runtime on
two eligible GPU routes with unmodified upstream OMP 18.4.0. Each lane's runtime was qualified
on its published component; fresh client/route acceptance is separate evidence. The immutable
[v0.7.2 manifest](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/releases/v0.7.2/manifest.json)
retains the historical three-GPU / OMP 18.0.9 combination.

## What it is

OMP NInfer is **durable local inference for coding agents**: the qualified local inference
appliance for Oh My Pi. Its v0.8.6 scope runs Qwen3.8 27B through the NInfer engine on one
NVIDIA RTX 5090 or RTX 4090 and preserves explicitly checkpointed OpenAI Responses
continuation state across process restarts, within the profile’s restore limits.

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
- they own an eligible RTX 5090 or RTX 4090 setup in the exact release profile;
- Qwen3.8 27B is the model they want;
- sessions are long-lived and stateful, and restart recovery matters;
- privacy and owned hardware matter more than breadth or multi-user throughput.

## Not a fit

- A GUI-first local experience (use LM Studio).
- Broad model catalogs and quick experimentation (use Ollama or LM Studio).
- Unsupported hardware or maximum portability (use llama.cpp).
- Multi-user or high-concurrency serving (use vLLM).
- Generic OpenAI-compatible inference without the durability contract.

## v0.8.6 eligible hardware

| Lane | Form | Context ceiling | Release |
|---|---|---:|---|
| RTX 5090 | Windows 11 + Docker Desktop/WSL2 Linux container | 131,072 | OMP 18.4.0 with component `v0.6.12-qwen38-5090-beta.1`, unchanged profile `qwen38-5090-v0.8.2` and configuration `56878aed` with `--gpu-keep-warm-ms 60000`, 16384 MiB host KV and a 28672 MiB runtime-host floor; measured restore limits are recorded below |
| RTX 4090 | native Windows 11 service | 131,072 | OMP 18.4.0 with component `v0.6.9-qwen38-4090-beta.1` (sm_89; INT8 KV, MTP3, prefill chunk 2,048), configuration `ccecfbe3` with `engine.gpu_keep_warm_ms = 60000`, 11264 MiB host KV, 24 host-state slots and a 32768 MiB runtime-host floor |

**RTX 3090 is deferred for v0.8.6**, not qualified with OMP 18.4.0. The separately linked
[historical v0.7.2 route](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)
retains OMP 18.0.9 and component `v0.2.5-qwen38-3090-beta.1`. New-client qualification
waits for that host’s return.

## v0.8.6 — long sessions compact inline

Long sessions no longer fail a turn while OMP compacts them. The config every documented
route installs, [`examples/manual-tunnel/fail-closed.yml`](../examples/manual-tunnel/fail-closed.yml),
sets `compaction.asyncEnabled: false`, so unmodified upstream OMP 18.4.0 compacts before
the turn instead of in the background. Both lanes admit one request at a time. On the RTX 4090,
the background handoff took 56-61 s; the next turn's attempts expired at the 30 s admission
deadline, and the third of three compactions ended in `503 request_queue_timeout`.

[EXP-072](measurements/2026-09-28-omp-long-sessions.json), using the new
[`scripts/omp_long_session_proof.py`](../scripts/omp_long_session_proof.py), measured repeated
automatic compaction with stock OMP 18.4.0 on both lanes:

- RTX 4090: three inline handoffs took **77.0-83.7 s** each with **no expired admission**.
  The newest identifier survived every compaction and a graceful restart; all three older
  identifiers were also recalled. The turn carrying a compaction took **91-101 s**.
- RTX 5090: two snapcompact compactions took **0.07-0.08 s** on the client. Both identifiers
  held only inside frames were recalled; `detail: "auto"` reaches the model at native resolution.
  The bounded archive dropped **76,832 and 192,080 characters** of older middle history.
- A single-admission mock reproduced the failure behind a 45 s handoff after six expired
  attempts with the old config; inline compaction expired none. OMP recognizes the runtime's
  `context_length_exceeded` response on both fragments, compacts and retries.

These are one run per configuration on each lane, with synthetic build-log filler, one seed
and thinking `low`; the failure rate is not measured. Older-identifier recall is recorded,
not gated. The RTX 5090 was not restarted after compaction. RTX 4090 handoffs re-prefill the
whole session because `tool_choice: none` omits the usual tool block; a second full replay
just below the threshold also re-prefills about 102,600 tokens (68 s). After compaction, its
first turn after a graceful restart re-prefills about 32,000 tokens (17 s); without compaction
the restore is hot. On the RTX 5090, one chained turn per run re-prefilled 93,696-105,066 tokens
from root (40-46 s), with cause unidentified. These remain runtime work, not fixes in this release.

The documented resume and restart checks now plant the nonce with an OK-only reply and ask for
a verbatim recall. On the RTX 5090 runtime, v0.8.5's plant made the model restate the nonce
visibly in 87 of 92 trials and v0.8.6's in none
([EXP-073](measurements/2026-09-28-omp-acceptance-sampling.json)); a restated,
misspelled copy is what the first RTX 5090 window's recall returned.

The client, provider fragments, both runtimes, model, memory floors, serving configurations and
lane receipts are unchanged from v0.8.5. RTX 5090 keeps `v0.6.12-qwen38-5090-beta.1`, image
`cd9e10b1`; RTX 4090 keeps `v0.6.9-qwen38-4090-beta.1`, package `6492588e`. Checkpoints carry
across. To upgrade from v0.8.5, merge this into `~/.omp/agent/config.yml`:

```yaml
compaction:
  asyncEnabled: false
```

The OMP binary, `models.yml` and `PI_OPENAI_STATEFUL=1` do not change. The documented resume
and restart checks now plant the nonce with an OK-only reply and ask for a verbatim recall,
rather than asking the model to restate it in its acknowledgment. RTX 3090 remains deferred.

All four documented routes passed **24 steps** on candidate `4f49fce7`
(`4f49fce7d52c62422e4f67cf15a3fa3a63dd72d9`) with unmodified OMP 18.4.0 and the published
components: RTX 5090 container host 2, macOS client 10, Windows client 5 and RTX 4090 native
Windows 7; both hosts were restored. The upstream macOS arm64 (preview), Windows x64 and
Linux x64 binaries each passed a typed tool turn, an exact continuation and a fail-closed
request against image `cd9e10b1`. Linux ran under **WSL2**, not a separately qualified Linux OS.
[Documented routes](../releases/v0.8.6/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.8.6/acceptance/composed-external-installation.json).

The RTX 5090 routes ran in **two production windows** from a separately hosted Apple silicon
Mac mini. Downtime was at most **186.9 s (3.1 min)** in the failed window and
**392.1 s (6.5 min)** in the accepted window;
total downtime was at most **579.0 s**
([restoration](measurements/2026-09-28-v086-acceptance-restoration.json)).

Candidate `be49962c` was refused by the RTX 4090 preflight before touching the lane: the lane
stage had left its manifest a draft; tooling was fixed. On `1fa202fd` the RTX 4090 route passed,
but the first RTX 5090 window failed at macOS resume: the acknowledgment wrote `COBOLT-493817`
and recall returned that copy. Production was restored after **186.9 s**; nonce checks were
hardened. On `60b5d82d` the documented RTX 4090 route passed, but its harness refused two
tool calls where it required exactly one. The harness now accounts each request to a documented
turn or tool call. Candidate `4f49fce7` passed the RTX 4090 route and a second RTX 5090 window.

[Release notes](../releases/v0.8.6/NINFER_RELEASE_NOTES.md) ·
[Manifest](../releases/v0.8.6/manifest.json) ·
[Qualification](../releases/v0.8.6/qualification.json).

## Historical v0.8.5 — OMP 18.4.0 and long-session compaction

OMP compacts a 131,072-token session automatically at 111,412 tokens. For an image-capable
model, its first usable method, snapcompact, archives earlier turns as PNGs at
`detail: "original"`. NInfer refuses that with HTTP 400 `image_detail_not_supported`, so
long RTX 5090 sessions on stock OMP 18.3.0-18.4.0 (releases v0.8.0-v0.8.4) failed at their
first compaction. The RTX 5090 fragments now declare `compat.supportsImageDetailOriginal: false`,
so OMP sends `auto`. On the RTX 5090 runtime, one compacted continuation completed with
26,075 input tokens and the exact nonce; `original` was refused in 9 ms
([EXP-071](measurements/2026-09-28-omp-snapcompact-image-detail.json)). The text-only RTX 4090
model is never compacted into images. Readback beyond that nonce and repeated compactions
in one session were not measured in EXP-071; EXP-072 above adds those measurements.

The first v0.8.5 route candidate hit this at the macOS restart step when its seed, the
release's own documents, grew from 332,331 to 343,205 bytes. That step now seeds the first
200,000 ASCII bytes (about 64,000 tokens), keeping checkpoint restoration distinct from
compacted-prompt acceptance.

The v0.8.5 release also repins unmodified upstream OMP from 18.3.5 to
[18.4.0](https://github.com/can1357/oh-my-pi/releases/tag/v18.4.0). On Windows, 18.3.5
printed a false `ended before completing` line after finished `omp -p` turns and exited 1
after a complete `omp models` listing. Upstream fix `9d3e0d4975` resolves
[#13470](https://github.com/can1357/oh-my-pi/issues/13470).

[EXP-070](measurements/2026-09-28-omp-1840-windows-completion-status.json) compared the
Windows x64 binaries with the documented RTX 4090 provider fragment against a local mock
Responses endpoint: 18.3.5 exited 1 after 5/5 complete listings and printed the false line
after 5/5 completed turns that exited 0; 18.4.0 exited 0 without that line in all 10 runs.
Both versions retain the existing `Working...` stderr indicator. This is client-status
proof on Windows x64, not a GPU inference or performance measurement. The RTX 4090 route
harness again requires exit 0 plus exactly the documented selector; the 18.3.5-only
exit-status tolerance and false-line troubleshooting entry are removed.

Both lanes carry the exact v0.8.4 runtime bytes. RTX 5090 keeps
`v0.6.12-qwen38-5090-beta.1`, image `cd9e10b1`, server `3ab266e5`, source `9d1ef748`,
profile `qwen38-5090-v0.8.2`, configuration `56878aed` and its carried v0.8.3 lane receipt.
RTX 4090 keeps `v0.6.9-qwen38-4090-beta.1`, package `6492588e`, server `65364401`, source
`5ac17674`, configuration `ccecfbe3` and 60000 ms keep-warm with the sm_89 50 ms/100 ms spin.
Its carried v0.8.4 lane receipt records qualification with OMP 18.3.5, not a new 18.4.0
runtime qualification. Model and memory floors are unchanged; no performance gain is claimed.

To upgrade from v0.8.4, install the checksummed 18.4.0 client binary and add
`supportsImageDetailOriginal: false` under the RTX 5090 model's `compat` in
`~/.omp/agent/models.yml`, as the updated fragments do. Other fragment fields and
`PI_OPENAI_STATEFUL=1` are unchanged. Neither server build changes, so checkpoints on both
lanes carry across.

All four documented routes passed **24 steps** on candidate `943063e7` with unmodified
OMP 18.4.0 and the published components: RTX 5090 container host 2, macOS client 10, Windows
client 5 and RTX 4090 native Windows 7; both hosts were restored. The upstream macOS arm64
(preview), Windows x64 and Linux x64 binaries each passed a typed tool turn, an exact
continuation and a fail-closed request against RTX 5090 image `cd9e10b1`. Linux ran under
WSL2, not a separately qualified Linux OS.
[Documented routes](../releases/v0.8.5/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.8.5/acceptance/composed-external-installation.json).

The RTX 5090 routes ran in one production window, with downtime at most
**381.2 s (6.4 min)**, from a separately hosted Apple silicon Mac mini on
macOS 26.6.1 over the tailnet, not the maintainer's workstation
([restoration](measurements/2026-09-28-v085-acceptance-restoration.json)).

[EXP-067](measurements/2026-09-27-stock-omp-1835-durable-sessions.json) (durable sessions)
and [EXP-068](measurements/2026-09-28-omp-1835-live-steering.json) remain OMP 18.3.5
evidence. In 18.4.0, live steering remains Codex-WebSocket-only in
`openai-codex-responses.ts`, gated on `compat.supportsSteering`; these providers do not set it.
The upstream engine merge stays deferred
([EXP-065](measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json)); the
sm_89 Q5 tensor-core route stays rejected
([EXP-069](measurements/2026-09-28-rtx4090-q5-small-t-mma.json)). RTX 3090 remains deferred:
its `v0.6.2-beta.1` package is built and tested (99/105 tests) but unpublished; one
`qualify_native.py` window on its physical host remains
([preparedness](measurements/2026-09-28-rtx3090-v062-build-preparedness.json)).

[Release notes](../releases/v0.8.5/NINFER_RELEASE_NOTES.md) ·
[Qualification](../releases/v0.8.5/qualification.json).

## Historical v0.8.4 — every lane current

RTX 4090 ships `v0.6.9-qwen38-4090-beta.1` (package `6492588e`, server `65364401`,
source `5ac17674`, configuration `ccecfbe3`). Its `engine.gpu_keep_warm_ms = 60000` uses an
sm_89-specific 50 ms spin every 100 ms: the RTX 5090's 3.5 ms/10 ms pattern did not hold this
card in P2. New sessions after 12-58 s idle prefilled in **0.146-0.148 s**, with time to first
token **0.167-0.178 s**; all 31 outputs were byte-identical. The hold costs about **72 W**
above idle, and a request arriving mid-spin can overlap one warp for up to 50 ms.
[EXP-064](measurements/2026-09-27-rtx4090-engine-keep-warm.json) ·
[EXP-066](measurements/2026-09-27-rtx4090-keep-warm-long-spin.json).

The published package passed all **15 canonical qualification phases**
([lane receipt](../releases/v0.8.4/qualification/rtx4090.json)); this is not a decode-kernel speedup.
RTX 5090 keeps `v0.6.12-qwen38-5090-beta.1`, image `cd9e10b1`, profile `qwen38-5090-v0.8.2`,
configuration `56878aed` and its carried v0.8.3 lane receipt. The model and memory floors are
unchanged. RTX 4090 checkpoints from v0.6.8 re-prefill once on the changed server build;
RTX 5090 carries its v0.8.3 checkpoints.

The v0.8.4 client advanced to unmodified upstream **OMP 18.3.5**. Its macOS arm64 binary kept one
short session across graceful restarts on both lanes with the documented fragments unchanged
([EXP-067](measurements/2026-09-27-stock-omp-1835-durable-sessions.json)). A steer submitted
mid-stream did not abort: OMP sent it **27 ms** after `response.completed` as a new request
chained by `previous_response_id`
([EXP-068](measurements/2026-09-28-omp-1835-live-steering.json)).

All four documented routes passed **24 steps** on candidate `68302298` with unmodified OMP
18.3.5 and the published v0.8.4 components: RTX 5090 container host 2, macOS client 10, Windows
client 5 and RTX 4090 native Windows 7; both hosts were restored. The upstream macOS arm64
(preview), Windows x64 and Linux x64 binaries each passed a typed tool turn, an exact
continuation and a fail-closed request against RTX 5090 image `cd9e10b1`. Linux ran under WSL2,
not a separately qualified Linux OS.
[Documented routes](../releases/v0.8.4/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.8.4/acceptance/composed-external-installation.json).

The upstream engine merge stays deferred: `e31bc99b` has about **18% slower decode** and
fanout **0/4 versus 4/4**
([EXP-065](measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json)). The
RTX 4090 Q5 tensor-core route was rejected by its pre-registered rule: **+0.38% at 26K** and
**+0.40% at 60K**, below required **2.0%/1.0%** gains
([EXP-069](measurements/2026-09-28-rtx4090-q5-small-t-mma.json)). RTX 3090's v0.6.2-beta.1
package built and tested at `5ac17674` remains unpublished, with hardware qualification pending
([preparedness](measurements/2026-09-28-rtx3090-v062-build-preparedness.json)).

[Release notes](../releases/v0.8.4/NINFER_RELEASE_NOTES.md) ·
[Qualification](../releases/v0.8.4/qualification.json).

## Historical v0.8.3 — faster RTX 5090 decode

- The unmodified upstream OMP 18.3.0 client and model artifact (`eec39564`) are unchanged
  from v0.8.2. Install through the [quickstart](QUICKSTART.md).
- RTX 5090 ships `v0.6.12-qwen38-5090-beta.1`, image
  `sha256:cd9e10b115bbf38df011b201dfdd37ec3b56613da39b2f1701334c8157236b78`, server
  `3ab266e5cd82398be98c2baee6a41a123ce1a4b0d38bd9ddcda75044dcd5dcb1`, source
  `9d1ef7485d9c741c2830fa3d55218f3242cec5d7` (v0.8.2's `32c21f73` plus the EXP-057 route).
  Runtime-image workflow run: `36301090709`. Serving arguments and deployment profile
  `qwen38-5090-v0.8.2`, configuration
  `56878aed92e8f3fb4101884fa889c98d1da75914573ebd167305ca0b4aa83e98`, are unchanged.
  The profile keeps `--gpu-keep-warm-ms 60000`, 16384 MiB host KV and a 28672 MiB host floor.
- RTX 4090 remains `v0.6.8-qwen38-4090-beta.1` (package `46aa4110`, server `32905865`,
  source `5a774841`), unchanged since v0.8.1 and carrying its
  [v0.8.1 lane receipt](../releases/v0.8.1/qualification/rtx4090.json).
- The MTP3 verify pass's four Q5 projections (GDN value/z, attention gate/value,
  mixer/attention output and MLP down) use small-T tensor-core MMA at the four-token extent
  on `sm_120` instead of SIMT row kernels. The route is compiled out for `sm_86` and `sm_89`.
  Release-build A/B/B/A measurements show decode **+4.4% at 26K**, **+3.6% at 60K** and
  **+6.3% at 1,024 tokens**. MTP3 rounds are **4.2%**, **3.5%**, **4.4%** and **4.9%** shorter
  at 26K, 60K, 1,024 tokens and no prompt respectively (range **3.5-4.9%**). With no prompt,
  decode is **0.5% slower**; the new build accepted 0.423 of drafts on its own text versus
  0.461. MTP acceptance was unchanged at 26K and 60K.
  Route: [EXP-057](measurements/2026-09-26-q5-small-t-tensor-core.json); measurements:
  [EXP-063](measurements/2026-09-27-powered-redaction-screen.json).
- Accumulation order changes: in isolation, 27 of 118,784 projection outputs moved by one
  bf16 ulp, closer to an FP64 reference. Generated text differs from v0.8.2 on **58 of 89**
  role-corpus cases (31 identical). The published image matched the screened candidate
  byte-for-byte on **89/89**. Other primary role-corpus measures were within 2.0 points of
  v0.8.2 in one run per build; the only criterion-6 regression was redaction-control pass rate.
- The pre-registered EXP-063 paired redaction screen passed. The rule was committed before
  candidate data (`554ac56`, `scripts/redaction_screen.py`); 7 counted redaction controls
  with 72 whitespace variants gave **504 pairs** on fresh v0.8.2 and candidate servers.
  Candidate leaks were **561 vs 582** for v0.8.2 (ratio **0.964**, one-sided 95% upper bound
  **1.012**, below the **1.10** margin). Pass rates were **53.2% vs 52.6%**: difference
  **+0.6 percentage points**, lower bound **-1.2 points** against a **-5-point** margin.
  All validity checks held; both arms reproduced 14 determinism prompts and matched
  EXP-057's outputs on 64 shared prompts. EXP-057's earlier 56-sample point-estimate screen
  had rejected the route (**69 vs 61 leaks**); EXP-063 re-tested the redaction regression
  with power. [EXP-063](measurements/2026-09-27-powered-redaction-screen.json).
- Gates were re-measured on the published RTX 5090 image: 130,048-token exact retrieval in
  **58.7 s**, `decode_2048` at **168.07 tok/s**, and the agent protocol across a restart.
  EXP-050 recorded four saves before eviction, first stop
  `saved 1, nothing to save 3, refused 0`, all four stored sessions restored after restart,
  and second stop `saved 0, nothing to save 4, refused 0`. EXP-051's held publication-barrier
  turn resumed exactly. Fanout (57K/67K), warm-arrival, restore and multisession probes
  passed; root fallback remained 2 of 8 continuations/forks. None of 24 fresh sessions fell
  back to a full prefill; median TTFT was **0.093-0.100 s**. Stock OMP 18.3.0 kept one
  session across graceful restarts; the first request restored from checkpoint.
  [RTX 5090 receipt](../releases/v0.8.3/qualification/rtx5090.json).

All four documented routes passed **24 steps** with unmodified OMP 18.3.0 on the published
v0.8.3 components: RTX 5090 container host 2, macOS client 10, Windows client 5 and RTX 4090
native Windows 7; both hosts were restored.
The upstream macOS arm64, Windows x64 and Linux x64 binaries each passed a typed tool turn,
an exact continuation and a fail-closed request against the published RTX 5090 image.
[Routes](../releases/v0.8.3/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.8.3/acceptance/composed-external-installation.json).

Checkpoints bind the exact server build: sessions saved by v0.8.2 do not restore on the new
RTX 5090 build in v0.8.3. Each session re-prefills once.
[Release notes](../releases/v0.8.3/NINFER_RELEASE_NOTES.md) ·
[Qualification](../releases/v0.8.3/qualification.json).

## Historical v0.8.2 — GPU keep-warm

- The unmodified upstream OMP 18.3.0 client and model artifact are unchanged from v0.8.1.
  Install through the [quickstart](QUICKSTART.md).
- RTX 5090 ships `v0.6.11-qwen38-5090-beta.1`, image
  `sha256:26813f5661e9bab7093349a216543d9391d310c08a207fee4d389d763dd36930`, server
  `0d7e042bca2956bbbe9bd68e8d1dcfaeea2666e326acdcea2d34d9b75d7c31d8`, source
  `32c21f73a7605f76480a6139de0488a14ed1aa48`. Its profile advances to
  `qwen38-5090-v0.8.2`, configuration
  `56878aed92e8f3fb4101884fa889c98d1da75914573ebd167305ca0b4aa83e98`, adding
  `--gpu-keep-warm-ms 60000`. Host KV stays 16384 MiB and the runtime-host floor 28672 MiB.
- RTX 4090 remains `v0.6.8-qwen38-4090-beta.1` (package `46aa4110`, server `32905865`,
  source `5a774841`), carrying its v0.8.1 lane receipt: 15 canonical native phases and
  130,048-token retrieval in **91.0 s**.
- After work, the RTX 5090 stepped down to P3 at about 2 s, P5 at about 7 s and its lowest
  idle state at about 9 s; the next prefill ran up to 2.3x slower. In logged v0.7.0 traffic,
  103 of 106 new sessions arrived at least 5 s after the previous request finished.
  [EXP-060](measurements/2026-09-26-idle-gpu-new-sessions.json).
- The runtime's `--gpu-keep-warm-ms N` option is off by default. After work and while idle,
  a single-warp kernel touches no memory and spins 3.5 ms of every 10 ms on its own stream
  for N ms, skips a launch while the previous spin runs, and stops when a request is pending.
  A 30% duty held the top P-state where 25% did not.
  [EXP-061](measurements/2026-09-26-keep-warm-load.json).
- After 12-58 s idle, new sessions prefilled in **0.155-0.157 s** (TTFT **0.173-0.181 s**),
  the same as back to back, versus **0.253-0.304 s** (TTFT **0.316-0.366 s**) without it.
  The 89-case role corpus was byte-identical to v0.8.1 on and off; requests arriving 1-5 ms
  after the previous one changed TTFT by a median **-0.1 ms**, worst **+4.4 ms**.
  Board power was **99.5-102.7 W** while held versus **29.3-29.8 W** idle (about **71 W**
  extra). Over 62 h of logged v0.7.0 traffic, a 60 s grace would cover 84 of 138 requests
  after at least 5 s idle (74 of 103 new sessions) at about **2.3 W average**; a 30 s grace
  would cover only 11 requests (median wait 52.7 s).
  [EXP-062](measurements/2026-09-26-engine-keep-warm.json).
- The published RTX 5090 image recorded 130,048-token exact retrieval in **56.4 s** and
  decode at **160.07 tok/s** (MTP acceptance 0.412, 2.24 tokens per round). Durability recorded
  four saves before eviction, stop `saved 1, nothing to save 3, refused 0`, all four sessions
  restored after restart, and second stop `saved 0, nothing to save 4, refused 0`.
  Publication-barrier, fanout, warm-arrival, restore and multisession probes passed. None of
  24 fresh sessions fell back to a full prefill; median TTFT was **0.090-0.098 s**. Stock
  OMP 18.3.0 kept one session across restarts on the RTX 5090; the role corpus was 89/89
  identical to production v0.8.1.
  [5090 receipt](../releases/v0.8.2/qualification/rtx5090.json) ·
  [4090 receipt](../releases/v0.8.2/qualification/rtx4090.json).

All four documented routes passed **24 steps** with unmodified OMP 18.3.0 on the published
v0.8.2 components: RTX 5090 container host 2, macOS client 10, Windows client 5 and RTX 4090
native Windows 7; both hosts were restored.
The upstream macOS arm64, Windows x64 and Linux x64 binaries each passed a typed tool turn,
an exact continuation and a fail-closed request against the published RTX 5090 image.
[Routes](../releases/v0.8.2/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.8.2/acceptance/composed-external-installation.json).

Checkpoints bind the exact server build: sessions saved by v0.8.1 do not restore on the new
RTX 5090 build in v0.8.2. OMP resends the full conversation and each session re-prefills once.
[Release notes](../releases/v0.8.2/NINFER_RELEASE_NOTES.md).

## Historical v0.8.1 — faster decode

- The unmodified upstream [OMP 18.3.0 binaries](https://github.com/can1357/oh-my-pi/releases/tag/v18.3.0)
  and their SHA-256 pins are unchanged from v0.8.0, as are the model, serving settings and
  memory floors. Install through the [quickstart](QUICKSTART.md).
- RTX 5090 ships `v0.6.10-qwen38-5090-beta.1` (image `5ca6e416`, server `5b2f2471`, source
  `8cc0810a`); RTX 4090 ships `v0.6.8-qwen38-4090-beta.1` (package `46aa4110`, server
  `32905865`, source `5a774841`).
- The MTP3 verify pass shares activation loads across weight rows in small-extent Q4/Q5
  projections, and Q4 gate/up staging avoids shared-memory bank conflicts without changing
  arithmetic order. RTX 5090 decode is **10.3-11.0% faster** with identical outputs from a
  seed context to 31K tokens. RTX 4090 keeps one-row split2 kernels for MLP down and mixer
  output; C1 decode is **157.89 vs 153.54 tok/s**.
  [EXP-055](measurements/2026-09-25-decode-kernel-schedules.json) ·
  [EXP-054](measurements/2026-09-25-decode-roofline-attribution.json).
- Every runtime gate was re-measured on the published bytes, matching v0.8.0's behavior.
  The anonymously pulled RTX 5090 image passed exact 130,048-token retrieval in **59.1 s**,
  the 2,048-token decode gate at **151.33 tok/s**, the EXP-050 durability workload,
  EXP-051 publication barrier, fanout, warm-arrival, restore and multisession probes. All
  four stored sessions restored after a restart; multisession root fallback remained 2 of 8,
  with no server errors. None of 24 fresh sessions fell back to a full prefill; median time
  to first token was **0.094-0.101 s**. The RTX 4090 package passed all 15 canonical native
  phases, including exact long-context retrieval in **91.0 s** and managed-stop flush of an
  unpublished session; no start refused. Stock OMP kept one session across restarts on both
  lanes, with first-request restore logged.
  [5090 receipt](../releases/v0.8.1/qualification/rtx5090.json) ·
  [4090 receipt](../releases/v0.8.1/qualification/rtx4090.json).
- All four documented routes passed **24 steps**: RTX 5090 container host 2, macOS client 10,
  Windows client 5 and RTX 4090 native 7; both hosts were restored. The upstream macOS arm64,
  Windows x64 and Linux x64 binaries passed typed tools, exact continuation and fail-closed
  checks on the published RTX 5090 image. Linux ran in Ubuntu WSL2, not a separately
  qualified non-WSL OS; macOS remains preview because the upstream client has no managed
  installation. [Routes](../releases/v0.8.1/acceptance/documented-routes.json) ·
  [Composed acceptance](../releases/v0.8.1/acceptance/composed-external-installation.json).
- Checkpoints are bound to the exact server build, including `patch_stack_sha` and
  `binary_sha256`. v0.8.0 checkpoints report `incompatible` and are not restored on
  v0.8.1. OMP treats `previous_response_not_found` as a stale chain and resends the full
  conversation, so each session re-prefills once; old checkpoints age out under the quota.
  [Release notes](../releases/v0.8.1/NINFER_RELEASE_NOTES.md).
- Automatic checkpoints remain best effort, and universal warm reuse is not claimed.
  [#48](https://github.com/alphastorm/omp-ninfer/issues/48) remains open for field confirmation.

## Historical v0.8.0 — bring your own OMP

- The client is the unmodified upstream
  [OMP 18.3.0 binary](https://github.com/can1357/oh-my-pi/releases/tag/v18.3.0), checked against
  its SHA-256. No fork build, archive, installer or cask; stock OMP has no `omp appliance`
  commands. Install and operate each lane through the [quickstart](QUICKSTART.md).
- Provider fragments keep thinking within `low`, `medium` and `xhigh`, disable encrypted
  reasoning and reasoning summaries, and every route exports `PI_OPENAI_STATEFUL=1`.
- RTX 5090 ships `v0.6.9-qwen38-5090-beta.2` (image `049dc788…`, server `d90079e8…`,
  source `86733c0e`); RTX 4090 ships `v0.6.7-qwen38-4090-beta.2` (package `888a5859…`,
  server `e4688dda…`, source `b0e8c2fa`, the same runtime plus a Windows-only commit margin).
  The model, serving settings and memory floors are unchanged from v0.7.4.
- With API authentication, `prompt_cache_key` becomes the session identity, hashed in its own
  domain and never stored raw; it is refused together with `ninfer_session` or
  `X-NInfer-Session`. A returning session's checkpoint is restored on its first request after
  a restart. On both published lanes, unmodified OMP 18.3.0 kept one session across graceful
  restarts, including a new process resuming after a restart
  ([EXP-053](measurements/2026-09-25-stock-omp-durable-sessions.json)).
- On the published RTX 5090 image, each of three agent types first prefilled its
  11,887-14,199-token prefix in 3.8-4.4 s; none of the 24 later fresh sessions fell back to a
  full prefill, and median time to first token was 0.095-0.102 s.
- Responses tool outputs accept content-part arrays: image tool results reach the model on
  RTX 5090, while the text-only RTX 4090 refuses them as `vision_disabled`.
- The RTX 4090 server commits and releases each pinned allocation's size plus 1/64 before
  pinning it. The published package passed its first managed start after a fresh install;
  [#48](https://github.com/alphastorm/omp-ninfer/issues/48) remains open for field confirmation.
- RTX 5090 passed its profile gates, EXP-050 durability workload, EXP-051 publication barrier,
  fanout, warm-arrival, restore and multisession probes on the published image. RTX 4090 passed
  all 15 canonical native phases. Save-before-evict with ceiling-class sessions was exercised
  on RTX 5090 only. [5090 receipt](../releases/v0.8.0/qualification/rtx5090.json) ·
  [4090 receipt](../releases/v0.8.0/qualification/rtx4090.json).
- The upstream macOS arm64, Windows x64 and Linux x64 binaries passed live inference against
  the published RTX 5090 image; Linux ran in Ubuntu under WSL2, not a separately qualified
  non-WSL OS. Windows and Linux client profiles are qualified; macOS remains preview, not a
  support claim, because stock OMP has no managed installation or appliance lifecycle.
  All four documented routes passed (host 2 blocks, macOS 10, Windows 5, RTX 4090 native 7),
  with both hosts restored. [Routes](../releases/v0.8.0/acceptance/documented-routes.json).
- Upgrading replaces the provider fragment and client. Fork-client `ninfer_session`
  checkpoints are not reachable from stock OMP: each session takes one cold first turn, and
  the old checkpoints age out under the quota. [Release notes](../releases/v0.8.0/NINFER_RELEASE_NOTES.md).

## Historical v0.7.4 — durable sessions on both lanes

- Both lanes run reviewed source `1c17c3facfbfd1243cf7711a412119302e6dbd74`: RTX 5090 image
  `ghcr.io/alphastorm/ninfer-runtime@sha256:f193b7469d062fc923b93ba72dbb4f8bb871912b505b529a062db50f65de2447`
  and RTX 4090 native package `v0.6.6-qwen38-4090-beta.1`. Closes
  [#45](https://github.com/alphastorm/omp-ninfer/issues/45) and
  [#46](https://github.com/alphastorm/omp-ninfer/issues/46).
- An automatic checkpoint refused at a transient gate retries when the engine quiesces;
  admission saves a checkpoint-tagged session's newest turn before evicting it, waiting while
  that turn's reply is still being stored; re-saving a session under the checkpoint quota no
  longer deletes other sessions' only checkpoints.
- On the published RTX 5090 image, the graceful-stop workload (two 126K-token sessions, a fanout
  and the agent protocol) stopped with `saved 1, nothing to save 3, refused 0` and all four
  stored sessions resumed from their checkpoints after a restart; the v0.7.3 runtime refused two
  and lost their state. A held reply was saved before eviction and resumed exactly.
  [Lane receipt](../releases/v0.7.4/qualification/rtx5090.json) ·
  [EXP-050](measurements/2026-09-24-durable-session-eviction.json) ·
  [EXP-051](measurements/2026-09-24-publication-barrier.json).
- Saving before eviction costs the admitting request about **6.5 s per 126K-token session** on
  the RTX 5090. Automatic checkpoints remain best effort: a crash or an expired graceful wait can
  still leave unsaved work.
- The RTX 4090 package passed 15 lane qualification phases on its host. Its workload evicted no
  checkpoint-tagged session, so save-before-evict is exercised on the RTX 5090 only.
- Client, model, serving arguments and memory floors are v0.7.3's; no throughput gain is claimed.
  Fresh route acceptance passed **24 documented steps** (RTX 5090 host 2, macOS client 10,
  Windows client 5, RTX 4090 native 7) and all three published clients passed live inference
  against the new RTX 5090 image. [Routes](../releases/v0.7.4/acceptance/documented-routes.json) ·
  [qualification](../releases/v0.7.4/qualification.json).

## Historical v0.7.3 — client-only OMP 18.2.3 repin

- Exact client component: `omp-18.2.3-cross-platform-beta-1`, public source
  `5ade242de59ac0f4606a1158bf564410c96918d4`. The macOS arm64, Windows x64 and Linux x64
  archives and all three provider-free hosted qualification receipts are public.
- All three clients passed live inference. Linux live proof ran in **Ubuntu under WSL2**;
  it does not qualify a non-WSL Linux OS or establish managed-install readiness from diagnostics.
- Fresh route acceptance passed **24 documented steps**: RTX 5090 host 2, macOS client 10,
  Windows client 5, RTX 4090 native 7. The run used frozen product source
  `096c8b889eef4bc89ee2dc316694b847bdf8a39d` with pre-cut substitutions recorded; all hosts
  were restored. [Routes](../releases/v0.7.3/acceptance/documented-routes.json) ·
  [qualification](../releases/v0.7.3/qualification.json).
- The authority uses OMP’s existing `durable-checkpoint` capability instead of the rejected
  `process-restart-continuation` name. This vocabulary correction adds no runtime capability.
- Runtime image/package bytes, model, serving arguments and memory floors remain v0.7.2.
  Runtime measurements are **carried evidence, not fresh measurements**; no throughput gain
  or stronger durability guarantee is claimed.

## Historical v0.7.2 — bounded restore reclaim

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
18,210,531,328 bytes), artifact SHA-256 `eec39564…14bf3e`, pinned identically across both
v0.8.6 lanes and unchanged from the historical three-GPU v0.7.2 manifest.

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

- **Historical recovery proved on the three 2026-09-05 profiles:** export → carry off-machine → remove local state with
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

## Historical measured proof (RTX 5090, single-machine samples)

- **v0.4.0 restart receipt:** 109,589 retained tokens served after a Docker restart;
  **0.778 s server-side time to first token after restoration**, not restore or restart time.
  **24.8 s end-to-end** includes first-touch restoration of the **7.95 GB** checkpoint;
  **56.6 s model reload** was recorded separately
  ([receipt](measurements/2026-08-30-rtx5090-durable-qualification.json)).
- **Separate v0.4.0 request pair:** **47.920 s cold wall time vs 1.790 s warm follow-up wall time**,
  at a 109,594-token session ([receipt](measurements/2026-08-30-warm-vs-cold-v04.json)).
  Comparing the cold wall time to the post-restoration TTFT would mix timing boundaries;
  neither receipt demonstrates a subsecond reboot or a 61× restart speedup.
- **v0.4.0: 144.80 tok/s** decode on the agent-shaped qualification gate (44.10% MTP acceptance);
  152.2 tok/s at 83.3% acceptance on the retrieval workload.
- Exact needle retrieval at a **130,048-token** prompt (2,180.3 tok/s cold on the v0.5.1 runtime, 2,207.10 on v0.4.8;
  the v0.4.0 gate measured 2,186.30 tok/s at 130,448 tokens).
- **138.16 tok/s** decode at 41.2% MTP acceptance on the v0.5.1 technical-writing gate (136.03 on v0.4.8).
- Full receipts: [benchmarks](BENCHMARKS.md) · [release manifest](../releases/v0.4.0/manifest.json).

The warm/cold request pair compares retained state with a fresh cold build, not restart
duration or a speed comparison against another runtime’s ordinary in-process prefix cache.

## Known limitations

- One model, one active request per lane (max concurrency 1); not a serving farm.
- Checkpoints are runtime-fingerprint-bound: they restore only on an identical lane
  (same binary, artifact, and profile) — not across GPU models.
- RTX 3090 is deferred for v0.8.6; its historical v0.7.2 lane's comfortable working envelope
  is the 64K class.
- Vision is available on the 5090 container profile; native Windows RTX 4090 is text-only.
- Automatic checkpoints remain best effort: a crash or an expired graceful wait can still leave
  unsaved work, and the v0.8.1 multisession control recorded two root fallbacks among eight
  continuations/forks. Neither universal warm reuse nor loss-free shutdown is claimed.

## Claims we do not make

- "No re-prefill" — in-process prefix caching is prior art and conceded as such.
- "Fastest local inference" — figures are one profile on one machine, receipt-bound.
- "First persistent KV cache" — prior art is credited in [Related work](RELATED_WORK.md).
- Production/GA/SLA claims beyond the qualified envelope of the current release.

## Primary evidence

[v0.8.6 manifest](../releases/v0.8.6/manifest.json) · [release state](RELEASES.md) ·
[Benchmarks and method](BENCHMARKS.md) · [Compatibility](COMPATIBILITY.md) ·
[Security model](SECURITY.md) · [v0.8.6 guide](QUICKSTART.md) ·
[Decision guide](DECISION_GUIDE.md)
