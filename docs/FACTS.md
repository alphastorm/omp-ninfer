# OMP NInfer — canonical facts

Updated: 2026-10-25 · Published release: v0.12.2 (2026-10-18) · v0.13.0 staged draft below

Oh My Pi (coding-agent client) → OMP NInfer (qualified appliance and release layer) → NInfer
(inference engine) → Qwen3.8 27B (served model).

**Qualified on RTX 5090 · 4090 · 3090**, bound to the exact profiles in
[`releases/v0.12.2/manifest.json`](../releases/v0.12.2/manifest.json).
[Get started](QUICKSTART.md) ·
[Download v0.12.2](https://github.com/alphastorm/omp-ninfer/releases/tag/v0.12.2)

## What it is

OMP NInfer is **durable local inference for coding agents**: the qualified local inference
appliance for [Oh My Pi](https://github.com/can1357/oh-my-pi) (OMP). It runs Qwen3.8 27B through
the NInfer engine on one user-owned NVIDIA RTX 5090, RTX 4090, or RTX 3090 and preserves explicitly
checkpointed OpenAI Responses continuation state across inference-server restarts within each
profile's restore boundary.

- **Oh My Pi** ([`can1357/oh-my-pi`](https://github.com/can1357/oh-my-pi)) owns the coding-agent
  client: the authoritative conversation transcript, typed tools, branches, subagents, compaction,
  and transcript replay.
- **NInfer** ([`Neroued/ninfer`](https://github.com/Neroued/ninfer) and
  [`alphastorm/ninfer`](https://github.com/alphastorm/ninfer)) owns single-GPU Qwen3.8 27B
  execution, retained OpenAI Responses continuation state, and local NVMe checkpoint storage.
- **OMP NInfer** (`alphastorm/omp-ninfer`) owns the integration and release layer: setup routes,
  hardware profiles, release manifests, qualification receipts, security boundaries, and support
  scope. It ships no forked OMP binary and inserts no extra gateway between OMP and NInfer.

## Best fit

All of these should be materially true:

- The operator uses, or intends to use, Oh My Pi.
- They own an eligible RTX 5090, RTX 4090, or RTX 3090 setup matching the exact release profile.
- Qwen3.8 27B is the model they want to run.
- Sessions are long-lived and stateful, and resuming across inference-server restarts matters.
- Privacy and owned hardware matter more than model catalog breadth or multi-user throughput.

## Not a fit

- A GUI-first local experience (use LM Studio).
- Broad model catalogs and quick experimentation (use Ollama or LM Studio).
- Unsupported hardware or maximum portability (use llama.cpp).
- Multi-user or high-concurrency serving (use vLLM).
- Generic OpenAI-compatible inference without the explicit durability contract.

See the [decision guide](DECISION_GUIDE.md) for the side-by-side comparison.

## Current release

Published release **v0.12.2** (2026-10-18, GitHub `Latest`) binds unmodified upstream Oh My Pi
**18.12.1** to unchanged runtime components and serving profiles from v0.12.0 and v0.11.0. Release
authority: [`releases/v0.12.2/manifest.json`](../releases/v0.12.2/manifest.json) ·
[`releases/v0.12.2/NINFER_RELEASE_NOTES.md`](../releases/v0.12.2/NINFER_RELEASE_NOTES.md) ·
[`COMPATIBILITY.md`](COMPATIBILITY.md). Relative to v0.12.1 only the client changed: 18.12.1 stops
the native Windows client from resolving a drive-relative operand such as `C:` against its start
directory ([#15511](https://github.com/can1357/oh-my-pi/issues/15511)) and fixes two `omp -p`
false-success exits; the [client upgrade review](measurements/2026-10-18-omp-18121-client-upgrade-review.json)
records the host-free checks.

| Component or lane | Form and transport | Release tag and source | Image or package | Serving profile | Context | Requests in flight | Speculative backend | Modalities |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
| Oh My Pi client | Unmodified upstream release binaries: macOS arm64 (preview), Windows x64, Linux x64 (WSL2 live evidence) | `v18.12.1`, source `291e0558`, tree `c9d897cc` | `omp-darwin-arm64` (`fa41b27d`), `omp-windows-x64.exe` (`1ba0274b`), `omp-linux-x64` (`16181401`) in [`client-components.json`](../releases/v0.12.2/qualification/client-components.json) | Per-model `compat.statefulResponses: true`, fail-closed config | 131,072 | `2` on RTX 5090; `1` per native lane | Target lane | Coding agent, typed tools, branches, compaction |
| RTX 5090 | Windows 11 + Docker Desktop/WSL2 container on loopback `127.0.0.1:18089`; local Windows client or macOS client over manual SSH tunnel (preview) | `v0.6.16-qwen38-5090-beta.1`, source `1302d639` | OCI image `6a02feba`, server `548fe239`, model `0634abb0` | `qwen38-5090-v0.11.0`, config `91a35670`: BF16 KV (131,520 KV tokens), 16,384 MiB host KV, 28,672 MiB host floor, 60,000 ms keep-warm | 131,072 | 2 (2 device slots, 180 s pending timeout) | DFlash2 draft window 7 | Vision, text, typed tools, preserved thinking |
| RTX 4090 native Windows 11 | Native Windows package on loopback `127.0.0.1:18082`, UUID-bound GPU on a two-GPU host | `v0.6.11-qwen38-4090-beta.1`, source `cad19767` | Package `52687044` (574,770,447 B), server `76f35b74`, model `eec39564` | `qwen38-4090-native-v0.6.11-beta.1`, config `1971cd29`: INT8 KV, 11,264 MiB host KV, 24 host-state slots, 32,768 MiB host floor, 60,000 ms keep-warm | 131,072 | 1 (2 device slots, 30 s pending timeout) | MTP3 (3 draft tokens) | Text, typed tools, preserved thinking (no vision) |
| RTX 3090 native Windows 11 | Native Windows package on loopback `127.0.0.1:18082`, UUID-bound GPU on the same two-GPU host | `v0.6.3-qwen38-3090-beta.1`, source `cad19767` | Package `74120de0` (595,697,859 B), server `bca236e5`, model `eec39564` | `qwen38-3090-native-v0.6.3-beta.1`, config `93bc3fd6`: INT8 KV, 8,192 MiB host KV, 24 host-state slots, 300 W serving power cap (370 W restored on stop), keep-warm off | 131,072 | 1 (4 device slots, 30 s pending timeout) | MTP3 (3 draft tokens) | Text, typed tools, preserved thinking (no vision) |

- **Sequential native topology on one two-GPU host:** Both native Windows lanes install on the same
  two-GPU Windows 11 host (RTX 4090 at index 0, RTX 3090 at index 1), each bound to its own GPU
  UUID and PCI address. Only one native lane runs at a time on loopback port `18082`. This is not
  multi-GPU inference and not concurrent native serving.
- **Lane-specific native rollback:** The RTX 3090 lane retains qualified two-direction rollback
  against its `v0.6.2-beta.1` predecessor on the two-GPU host. The RTX 4090 lane is the first
  release of its lineage on that topology and has no supported rollback target (`not_applicable`,
  zero directions); `v0.6.10` and earlier RTX 4090 packages are unsupported on the two-GPU host.
- **Admission on the RTX 5090:** Two requests run together on the RTX 5090 only while both prompts
  plus output reservations fit inside its 131,520-token BF16 KV pool; excess requests wait up to
  180 s. Upgrade the RTX 5090 server before raising an OMP provider limit to `2`.
- **Fresh route acceptance, carried runtime qualification:** Fresh v0.12.2 acceptance on frozen
  candidate `d7ed4a65` passed all five documented routes (31 blocks), all three stock 18.12.1
  clients (typed tool turn, exact continuation, fail-closed request), and both native public
  installs, with independent host restoration
  ([`documented-routes.json`](../releases/v0.12.2/acceptance/documented-routes.json),
  [`composed-external-installation.json`](../releases/v0.12.2/acceptance/composed-external-installation.json)).
  Runtime and package qualifications carry unchanged from v0.12.0 (native) and v0.11.0 (RTX 5090).

## Models

### v0.13.0 beta.2 restage preparation — qualification pending

The [staged notes](../releases/v0.13.0/NINFER_RELEASE_NOTES.md) and
[candidate protocol matrix](../releases/v0.13.0/COMPATIBILITY.md) describe the next release.
The published product remains v0.12.2. Council found durable/restore defects in beta.1:
candidate `86e5c0b9`, source `04b603aa`, server `48d736aa` and image `e0419f48` are historical.
The root files retain that historical candidate until a new lane pin; F2 source/assets/lane
qualification are not yet bound. Prepared strict-origin config `751d22dc` is not beta.1 proof.

| Boundary | Rebased RTX 5090 candidate | Default carried native RTX 4090 / RTX 3090 |
| --- | --- | --- |
| Runtime base | Neroued/ninfer master `64d10fbf`; target `v0.7.0-qwen38-5090-beta.2`, F2 identities pending | Existing `v0.6.11` / `v0.6.3` components, source `cad19767` |
| Stock client | OMP 18.12.6, source `45c35e40`; fresh acceptance required | Same client; native public-install acceptance reruns |
| Model | Published container version 3 `81f924d4`, 20,437,521,664 bytes, revision `1cbd84e7221e51186bd7f093a149912d2489625b`; text/vision/MTP/DFlash2 | Unchanged `eec39564`, 18,210,531,328 bytes |
| Structured output | **Runtime-supported:** xgrammar, real grammar and product-smoke evidence for `text.format` / `response_format` `json_schema`; OMP/public-route acceptance is separate | Rejected with HTTP 400 |
| Tool names (Chat/Responses) | 128 characters on the rebased boundary | 64 characters |
| Status / request log | Status schema 2 / request-log schema 30 | Status schema 1 / request-log schema 17 |
| Host store | Shared State/KV budget 21,881,405,440 bytes; 2 extra device slots beyond the 2 active lanes | Existing separate state-slot and host-KV budgets |
| Disk sessions | New schema 3 directory `checkpoints-v013` at `/checkpoints-v013`; fingerprint schema 2 | Existing lane stores, unchanged |

The published model is downloaded directly; no local model upgrader runs in the release route.
All 1,184 tensor payloads and all six frontend resources matched the production model upgraded
locally. Whole-container hashes differ, so only the exact published `81f924d4` artifact is pinned.
The prepared strict-origin configuration identity is
`751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47`, adding
`--session-checkpoint-require-origin-auth` for council finding 8 and K1 section 103–114.
The flag needs a checkpoint root and a key of at least 32 bytes; the documented key has 64
characters. The historical beta.1 measurements (146,368 KV tokens, 180.06 tok/s server decode,
56.921 s exact retrieval and 20,926-token/27-byte restart reuse) do not qualify this new shape.
All other tuning stays unchanged apart from K5's unified host
mapping and explicit removal of the obsolete `--max-private-continuations` catalog flag.

The new loader never reads or mutates v0.12.x checkpoint roots. Keep them for rollback; prior
sessions replay from the authoritative OMP transcript for a fresh prefill. Non-blocking export
captures state under serialization and performs bulk transfer/hash/write outside the execution
lock, with an epoch-checked final publication. It does not promise loss-free saves or zero latency.
Rebased native components target v0.13.1, not this release. The 24 GB shapes need
`--admission-headroom-mib` (640 MiB RTX 4090 / 768 MiB RTX 3090) and are not yet packaged or
qualified. Container capabilities never transfer by assumption. Council, new client/public
acceptance and final pins remain pending; historical powered quality/leak and OMP parallel/fanout
workloads are not re-measured for v0.13.0.

Within one API-key principal, prompt_cache_key names a session capability; use unique high-entropy keys and do not share that principal among mutually untrusted clients.

### Published v0.12.2 model bindings

v0.12.2 pins two registered NInfer conversion artifacts (`qwen3_8_27b.ninfer`) from
[`neroued/Qwen3.8-27B-NInfer`](https://huggingface.co/neroued/Qwen3.8-27B-NInfer) in
[`releases/v0.12.2/manifest.json`](../releases/v0.12.2/manifest.json):

| Lane scope | Hugging Face revision | Bytes | SHA-256 | Notes |
| --- | --- | ---: | --- | --- |
| RTX 5090 container (`components.model`) | `dc370fb6295ae8b786e1af4f90d7142a16255c35` | 20,437,336,576 | `0634abb07024221de141456cf04a42ab74b18bc38e1b781c6eb2e062a467eec3` | Serves public model ID `q38-ninfer` with DFlash2 draft window 7 and vision |
| Native RTX 4090 and RTX 3090 (`components.native_model`) | `18dfc887423fa5aabf3cb56fac41490e462b3fab` | 18,210,531,328 | `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e` | Groupwise-int weights with MTP3 heads for native text/tools profiles |

## What the route provides

- **Protocols and endpoints:** OpenAI Responses (`/v1/responses`, primary stateful surface), OpenAI
  Chat Completions (`/v1/chat/completions`), Anthropic Messages (`/v1/messages` and
  `/v1/messages/count_tokens`), authenticated runtime identity (`/v1/ninfer/status`), and session
  checkpoint save/status/delete (`/v1/ninfer/checkpoints`).
- **Explicit continuation and lineage:** Continuation is addressed through `previous_response_id`
  with session identity derived from `prompt_cache_key` under bearer authentication (never stored
  raw; rejected if mixed with legacy `ninfer_session` or `X-NInfer-Session`). Sibling forks, parent
  deletion without descendant loss, and cross-session isolation are qualified on all three lanes.
- **Tools, vision, and preserved thinking:** Typed tool calling, content-part array tool outputs,
  and preserved thinking (`reasoning_text` deltas with `summary: []`) are qualified on all three
  lanes. Vision inputs (including image tool results and `snapcompact` image archives) are
  qualified on the RTX 5090 lane only; native RTX 4090 and RTX 3090 lanes refuse image inputs with
  `vision_disabled`. Published v0.12.2 rejects enforced JSON-schema output; the v0.13.0
  rebased-container runtime support and its separate OMP/public-route acceptance are distinguished above.
- **Oh My Pi client contract:** Stock Oh My Pi 18.12.1 has no `omp appliance` commands. Model
  fragments set `compat.statefulResponses: true` per model (upstream
  [#13686](https://github.com/can1357/oh-my-pi/pull/13686)), and `PI_OPENAI_STATEFUL` must be
  absent from the environment. Custom Responses hosts default to `auto` image detail upstream
  ([#13687](https://github.com/can1357/oh-my-pi/pull/13687)), removing the old
  `supportsImageDetailOriginal` override, and unavailable saved models fail closed
  ([#13689](https://github.com/can1357/oh-my-pi/pull/13689)).
  [`examples/manual-tunnel/fail-closed.yml`](../examples/manual-tunnel/fail-closed.yml) disables
  retries, model fallback, and `checkUpdate`, leaves compaction at the OMP default, and sets
  `providers.maxInFlightRequests` per provider ID (`ninfer-beta: 2`, `ninfer-main: 2`,
  `ninfer-native-4090: 1`, `ninfer-native-3090: 1`, `ninfer-heavy: 1`).

## Durability

- **Transcript is the source of truth:** Oh My Pi commits each turn to its local transcript before
  advancing the provider continuation baseline. GPU-resident and checkpointed state is an
  acceleration layer, never the sole copy of the conversation.
- **What survives a server restart:** Checkpoints are written to local NVMe as SHA-256-manifested,
  atomically published generations and restore on the first matching request after an
  inference-server restart on all three lanes. Graceful managed stops flush eligible unpublished
  sessions before exit.
- **Best-effort saves and pool bounds:** Checkpointing under live traffic is best effort. Transient
  automatic save refusals retry when the engine quiesces, and admission saves a checkpoint-tagged
  session's newest turn before evicting it, but a crash or expired graceful wait can leave
  unpublished work unsaved. Restore materializes continuation KV into the host-KV pool (16,384 MiB
  on RTX 5090, 11,264 MiB on RTX 4090, 8,192 MiB on RTX 3090), and exports that the configuration
  could not admit back are refused (`HTTP 409`).
- **Exact-identity restore requirements:** A checkpoint restores only when the runtime binary
  hash, patch-stack SHA, model artifact, deployment profile, and session credentials match.
  Checkpoints from another GPU lane, an earlier server build, or the legacy fork client's
  `ninfer_session` names are refused rather than partially loaded.
- **Replay fallback and warm-reuse limits:** When a checkpoint is missing, incompatible, or
  declined for capacity, the server returns `previous_response_not_found` and Oh My Pi resends the
  full conversation for one cold root prefill. Starting a new Oh My Pi process to resume a session
  also costs one root prefill because the first resumed request omits prior reasoning tokens.
  Universal warm reuse is not promised (the RTX 5090 multisession control observed root fallback on
  2 of 8 continuations/forks without server errors).

## Checkpoint transport and NAS replication

[`scripts/checkpoint_sync.py`](../scripts/checkpoint_sync.py) exports published checkpoint
generations, verifies file sizes, SHA-256 hashes, and `manifest.mac`, and imports verified
replicas into a local checkpoint root (`python3 scripts/checkpoint_sync.py --help`).

- **Replicas, never live checkpoint roots:** Native O_DIRECT and DirectStorage paths require a
  local filesystem. Network shares and NAS mounts are replica storage only; never point a running
  server at a network share. Publish the checkpoint before export and stop the destination runtime
  before import.
- **Same-lane restore contract:** Restoring an imported replica requires the identical runtime
  binary, model artifact, deployment profile, and bearer key (`--session-checkpoint-require-origin-auth`;
  do not use `--allow-unauthenticated` across trust boundaries). Transport is explicit export and
  import, not cross-GPU migration, cross-version conversion, or automatic failover.
- **Historical transport receipts:** Off-machine export, local wipe, import, and post-restart
  retrieval were verified on the 2026-09-05 profiles
  ([RTX 5090](measurements/2026-09-05-sync-probe-rtx5090.json),
  [RTX 4090](measurements/2026-09-05-sync-probe-rtx4090.json),
  [RTX 3090](measurements/2026-09-05-sync-probe-rtx3090.json)), with separate receipts for
  [cross-site transfer](measurements/2026-09-06-replica-transfer-paths.json) and
  [NAS replication](measurements/2026-09-07-nas-replication-sf-lanes.json).

## Privacy and security boundary

- **Loopback-only listeners:** The runtime binds `127.0.0.1:18089` (RTX 5090 container) or
  `127.0.0.1:18082` (native Windows lanes). Remote macOS clients reach the RTX 5090 host through
  an authenticated SSH local port forward.
- **Bearer authentication and protected state:** Every request requires a user-only bearer key;
  anonymous requests fail with `HTTP 401`. Native Windows state roots enforce Administrator-only
  DACLs verified by low-privilege read and write denial checks.
- **Fail-closed client and pinned bytes:** Oh My Pi disables retries and model fallback so an
  unreachable or mismatched local runtime fails closed instead of falling back to cloud APIs.
  Every client binary, image digest, native package, model artifact, and configuration is SHA-256
  pinned in [`releases/v0.12.2/manifest.json`](../releases/v0.12.2/manifest.json).
- **Single trusted owner:** Designed for one trusted operator on owner-controlled hardware, not
  multi-tenant isolation. Full threat model: [`SECURITY.md`](SECURITY.md).

## Measured proof

Per-lane runtime qualification receipts carried in v0.12.2 (never transfer one lane's numbers or
capabilities to another):

| Lane | Long-context retrieval (130,048 tokens) | Decode measurement | Speculative acceptance | Receipt |
| --- | --- | --- | --- | --- |
| RTX 5090 (`v0.6.16-qwen38-5090-beta.1`, DFlash2 K=7, BF16 KV) | Exact in **58.89 s** cold (2,208.3 tok/s wall) | **179.79 tok/s** server-side (**177.96 tok/s** wall) over 2,048 tokens | **0.239** DFlash2 acceptance, **2.67** tokens/round | [`rtx5090.json`](../releases/v0.12.2/qualification/rtx5090.json) (2026-10-10) |
| RTX 4090 native (`v0.6.11-qwen38-4090-beta.1`, MTP3, INT8 KV) | Exact in **91.03 s** | **158.66 tok/s** C1 decode (4,541 prompt / 1,024 completion tokens); prefill **2,109 tok/s** | **87.59%** MTP3 acceptance | [`rtx4090.json`](../releases/v0.12.2/qualification/rtx4090.json) (2026-10-11) |
| RTX 3090 native (`v0.6.3-qwen38-3090-beta.1`, MTP3, INT8 KV, 300 W cap) | Exact in **220.52 s** | **102.41 tok/s** C1 decode (4,541 prompt / 1,024 completion tokens); prefill **892 tok/s** | **93.43%** MTP3 acceptance | [`rtx3090.json`](../releases/v0.12.2/qualification/rtx3090.json) (2026-10-11) |

- **Historical v0.4.0 restart proof (one RTX 5090, 2026-08-30, not a current-release timing or
  restart speedup ratio):** **109,589 retained tokens** served after a Docker restart; **24.8 s
  end-to-end** including first-touch restoration of a **7.95 GB** checkpoint; **56.6 s model
  reload** measured separately; **0.778 s server-side time to first token** after restoration
  ([`2026-08-30-rtx5090-durable-qualification.json`](measurements/2026-08-30-rtx5090-durable-qualification.json)).
  A separate v0.4.0 request pair measured **47.920 s cold wall time versus 1.790 s warm follow-up
  wall time** at 109,594 tokens
  ([`2026-08-30-warm-vs-cold-v04.json`](measurements/2026-08-30-warm-vs-cold-v04.json)),
  captioned retained state versus fresh-process cold start rather than an ordinary in-process
  follow-up.
- Full methodology, workload definitions, and historical series: [`BENCHMARKS.md`](BENCHMARKS.md).

## Non-claims

- **No SLA, stable/v1.0 support, or upgrade commitment:** The `0.x` series supports only the
  latest published release (`v0.12.2`) and its exact manifest and profiles.
- **No other GPUs or profiles:** Support does not extend outside the exact RTX 5090, RTX 4090, and
  RTX 3090 profiles bound by [`releases/v0.12.2/manifest.json`](../releases/v0.12.2/manifest.json).
- **Client platform limits:** macOS (`darwin-arm64`) is preview without managed client installation
  or appliance lifecycle; Linux (`linux-x64`) live evidence is under WSL2 only, not a separately
  qualified native Linux OS.
- **Carried native lanes are text and tools only:** Vision is qualified only on the RTX 5090
  container lane. Carried native JSON-schema output remains rejected; the rebased container's
  implemented support becomes a release claim only after fresh live acceptance.
- **Not multi-GPU inference or concurrent native serving:** Only one UUID-bound native lane runs at
  a time on port `18082`. RTX 4090 has no supported rollback target on the two-GPU host, and
  `v0.6.10` or earlier RTX 4090 packages are unsupported there.
- **Checkpoints are best effort:** Neither globally loss-free shutdown, universal warm reuse,
  cross-GPU checkpoint migration, nor automatic container restart is claimed.
- **No "no re-prefill" or universal speed claims:** In-process prefix caching is conceded prior art
  ([`RELATED_WORK.md`](RELATED_WORK.md)), and two requests in flight on the RTX 5090 do not
  provide preemption or guaranteed faster single-session wall time.
- **Not independent external-user outcomes:** All qualification and acceptance receipts are
  owner-operated measurements on retained hardware.

## Where the history lives

- [`CHANGELOG.md`](../CHANGELOG.md) — chronological product changes across releases.
- [`RELEASES.md`](RELEASES.md) — per-version component identities, acceptance summaries, and
  release cut procedures.
- [`releases/v0.12.2/NINFER_RELEASE_NOTES.md`](../releases/v0.12.2/NINFER_RELEASE_NOTES.md) (and
  prior `releases/<tag>/NINFER_RELEASE_NOTES.md`) — immutable per-release notes and limitations.
- Immutable tagged guides (`https://github.com/alphastorm/omp-ninfer/blob/<tag>/docs/QUICKSTART.md`,
  such as [`v0.10.0`](https://github.com/alphastorm/omp-ninfer/blob/v0.10.0/docs/QUICKSTART.md) and
  [`v0.7.2`](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)) — complete
  setup instructions for operators remaining on a prior release.

Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.
