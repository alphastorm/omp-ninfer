![OMP NInfer](assets/banner.png)

<div align="center">

<sub>DURABLE LOCAL INFERENCE FOR CODING AGENTS</sub>

# OMP NInfer

**Your coding session should survive the process.**

Durable session state on your GPU.

[Oh My Pi](https://github.com/can1357/oh-my-pi) (coding-agent client) → **OMP NInfer** (qualified
appliance and release layer) → [NInfer](https://github.com/Neroued/ninfer) (inference engine) →
[Qwen3.8 27B](https://huggingface.co/neroued/Qwen3.8-27B-NInfer) (served model).

**Qualified on RTX 5090 · 4090 · 3090 — v0.12.1, stock Oh My Pi 18.10.1 (published 2026-10-12)**

Fresh v0.12.1 acceptance: five documented routes, 31 steps, three stock clients, and both native
public installs passed with independent restoration (owner-operated;
[composed receipt](releases/v0.12.1/acceptance/composed-external-installation.json)).

**[Get started](docs/QUICKSTART.md)** ·
**[Download v0.12.1](https://github.com/alphastorm/omp-ninfer/releases/tag/v0.12.1)**

[Lanes](docs/QUICKSTART.md#choose-your-lane) · [Facts](docs/FACTS.md) ·
[Compare](docs/DECISION_GUIDE.md) · [Benchmarks](docs/BENCHMARKS.md) ·
[Architecture](docs/ARCHITECTURE.md) · [Security](docs/SECURITY.md) ·
[Troubleshooting](docs/TROUBLESHOOTING.md) · [Roadmap](ROADMAP.md) ·
[Changelog](CHANGELOG.md)

[![CI][ci-badge]][ci]
[![Release][release-badge]][releases]
[![RTX 5090 decode][decode-badge]][benchmarks]
[![Context][context-badge]][benchmarks]
[![License][license-badge]][license]

[ci]: https://github.com/alphastorm/omp-ninfer/actions/workflows/ci.yml
[ci-badge]: https://img.shields.io/github/actions/workflow/status/alphastorm/omp-ninfer/ci.yml?branch=main&label=CI&labelColor=0B0E11
[releases]: https://github.com/alphastorm/omp-ninfer/releases
[release-badge]: https://img.shields.io/github/v/release/alphastorm/omp-ninfer?filter=v*&label=release&color=8E7BE8&labelColor=0B0E11
[benchmarks]: docs/BENCHMARKS.md
[decode-badge]: https://img.shields.io/badge/RTX%205090%20decode-179.79%20tok%2Fs-8E7BE8?labelColor=0B0E11
[context-badge]: https://img.shields.io/badge/context-130%2C048%20tokens%20exact-1C232B?labelColor=0B0E11
[license]: LICENSE
[license-badge]: https://img.shields.io/github/license/alphastorm/omp-ninfer?color=1C232B&labelColor=0B0E11

<sub><strong>Private by design:</strong> loopback-only endpoints · bearer-authenticated ·
fail-closed instead of cloud fallback · every byte hash-pinned</sub>

<sub>Historical v0.3.0 RTX 5090 coding demo: bug fixed, tests rerun to green, then a
stateful follow-up. Not a restart demonstration or proof of the current release.
Idle gaps longer than 1.75 s are compressed; the unchanged MP4 is 15.3 s.</sub>

<img src="docs/media/omp-ninfer-demo-v3.gif" alt="Historical v0.3.0 RTX 5090 recording: OMP fixes a ring-buffer bug, passes the tests, then answers a stateful follow-up. Idle waits compressed; no server restart is shown." width="900">

<sub><a href="docs/media/omp-ninfer-demo-v3.mp4">MP4</a> · <a href="docs/media/omp-ninfer-demo-v3-poster.png">poster</a> · <a href="docs/media/README.md#canonical-files">provenance and checksums</a></sub>

</div>

## What it does

Long Oh My Pi coding sessions carry 100K-token transcripts, thinking, tool calls, and images:
routed to a cloud provider, every token is metered and every file leaves your machine; routed to a
stateless local server, each turn re-sends the whole transcript. A live
[NInfer](https://github.com/Neroued/ninfer), llama.cpp, or vLLM process with in-process prefix
caching (`prefix_reuse`) already avoids recomputing an append-only prefix while the server stays up
— that is prior art, not what this project claims to invent. OMP NInfer adds explicit,
transactional continuation that survives process restarts on three qualified single-GPU lanes:

1. **Explicit, durable continuation.** OMP drives NInfer through stateful OpenAI Responses
   (`previous_response_id`), with forks and rollback qualified and checkpoints restored after a
   server restart within each profile's restore limits. OMP commits its transcript before advancing
   provider state, so losing retained state degrades to a replay rather than a broken session.
   [`scripts/checkpoint_sync.py`](docs/FACTS.md#checkpoint-transport-and-nas-replication) exports
   and imports verified generations across hosts or a NAS replica when runtime, model, profile, and
   session credentials match.
2. **Private and fail-closed.** Both endpoints bind loopback only, every request is
   bearer-authenticated, and the shipped OMP configuration disables model fallback — when your GPU
   is unreachable, the turn fails closed with an error rather than falling back to cloud
   (acceptance-tested).
3. **Exact and verifiable.** Model SHA-256, container OCI digest and SPDX SBOM, native package and
   stock client SHA-256 checksums, and qualification receipts are bound in one manifest and checked
   by `python3 scripts/verify_release.py --require-ready`.

## Is it for you

**Use OMP NInfer when:**

- You run [Oh My Pi](https://github.com/can1357/oh-my-pi) and want long, stateful Qwen3.8 27B
  coding sessions on your own GPU.
- You own an NVIDIA RTX 5090, RTX 4090, or RTX 3090 host matching the documented Windows 11 +
  Docker Desktop/WSL2 or native Windows 11 profile.
- You want explicit Responses continuation (`previous_response_id`, forks, rollback) and local
  checkpoints that restore after a server restart.
- You require a loopback-only, bearer-authenticated, fail-closed route where code stays on your
  hardware.

**Use something else when:**

- You want a broad model catalog and one-command local model switching — [Ollama](https://ollama.com).
- You want a polished desktop GUI for browsing and running local models — [LM Studio](https://lmstudio.ai).
- You need the widest hardware reach, CPU or Apple silicon execution, or arbitrary GGUF
  quantizations — [llama.cpp](https://github.com/ggml-org/llama.cpp).
- You need high-throughput multi-user or multi-tenant serving across a broad model and GPU matrix —
  [vLLM](https://github.com/vllm-project/vllm).

## Qualified lanes

| Lane | Host and client | Runtime | What you get | Measured |
| --- | --- | --- | --- | --- |
| RTX 5090 | Windows 11 + Docker Desktop/WSL2 container (`127.0.0.1:18089`); stock OMP 18.10.1 on Windows x64 local, Linux x64 in WSL2, or macOS arm64 over a manual SSH tunnel (preview) | `v0.6.16-qwen38-5090-beta.1`, source `1302d639`, image `6a02feba`, server `548fe239`, model `0634abb0` (20,437,336,576 bytes) | Profile `qwen38-5090-v0.11.0` (config `91a35670`): 131,072-token context, BF16 KV, two requests in flight, DFlash2 draft window 7, vision + tools + preserved thinking | Exact 130,048-token retrieval in 58.89 s cold; 2,048-token decode 179.79 tok/s server-side (177.96 tok/s wall), DFlash2 acceptance 0.239, 2.67 tokens/round ([`rtx5090.json`](releases/v0.12.1/qualification/rtx5090.json)) |
| RTX 4090 native Windows 11 | Native Windows 11 package (`127.0.0.1:18082`, UUID-bound GPU on a two-GPU host); stock OMP 18.10.1 on Windows x64 | `v0.6.11-qwen38-4090-beta.1`, source `cad19767`, server `76f35b74`, package `52687044`, model `eec39564` (18,210,531,328 bytes) | 131,072-token context, INT8 KV (11,264 MiB host KV), one request at a time, MTP3, text + tools (no vision) | Exact 130,048-token retrieval in 91.03 s; C1 decode 158.66 tok/s at 87.59% MTP3 acceptance, prefill 2,109 tok/s ([`rtx4090.json`](releases/v0.12.1/qualification/rtx4090.json)) |
| RTX 3090 native Windows 11 | Native Windows 11 package (`127.0.0.1:18082`, UUID-bound GPU on the same two-GPU host); stock OMP 18.10.1 on Windows x64 | `v0.6.3-qwen38-3090-beta.1`, source `cad19767`, server `bca236e5`, package `74120de0`, model `eec39564` (18,210,531,328 bytes) | 131,072-token context, INT8 KV (8,192 MiB host KV), one request at a time, MTP3, 300 W power cap while serving, text + tools (no vision) | Exact 130,048-token retrieval in 220.52 s; C1 decode 102.41 tok/s at 93.43% MTP3 acceptance ([`rtx3090.json`](releases/v0.12.1/qualification/rtx3090.json)) |

- **Native two-GPU topology:** Both native Windows lanes install on one two-GPU host with each
  package bound to its GPU UUID; only one runs at a time on loopback port `18082` (not multi-GPU
  inference or concurrent native serving). The RTX 5090 lane serves model `0634abb0` (20.4 GB) and
  both native lanes serve `eec39564` (18.2 GB) from
  [`neroued/Qwen3.8-27B-NInfer`](https://huggingface.co/neroued/Qwen3.8-27B-NInfer).
- **Rollback facts:** On the two-GPU native host, RTX 3090 retains qualified two-direction
  rollback, while RTX 4090 has no supported rollback target (`not_applicable`; `v0.6.10` and
  earlier RTX 4090 packages are unsupported there). Checkpoints are best effort and restore only on
  the same runtime binary, model, profile, and session credentials.
- **Client platform scope:** macOS arm64 is a preview route over a manual SSH tunnel, and live
  Linux x64 client evidence is under WSL2 on the RTX 5090 host rather than a separately qualified
  native Linux OS ([`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md), [`docs/FACTS.md`](docs/FACTS.md)).

## Get started

1. **[Choose your lane](docs/QUICKSTART.md#choose-your-lane)** — match your GPU and client OS to
   one of the five documented routes and check its memory, disk, and driver prerequisites.
2. **Clone `v0.12.1` and verify the release** — check out tag `v0.12.1` and run
   `python3 scripts/verify_release.py --require-ready` before starting a runtime or downloading
   weights.
3. **[Install the exact stock Oh My Pi 18.10.1 client](docs/QUICKSTART.md#omp-18101-client)** —
   verify the upstream binary SHA-256 and apply
   [`examples/manual-tunnel/fail-closed.yml`](examples/manual-tunnel/fail-closed.yml) plus the
   per-model `compat.statefulResponses: true` fragment (`PI_OPENAI_STATEFUL` must be absent).
4. **Run the documented acceptance checks** — execute the route's health, tool, continuation,
   restart recovery, and fail-closed verification blocks in [`docs/QUICKSTART.md`](docs/QUICKSTART.md).

- **Upgrading from v0.12.0 is client-only:** Runtime components, models, and profiles are unchanged
  from v0.12.0; update only the stock OMP 18.10.1 binary per
  [`docs/QUICKSTART.md#omp-18101-client`](docs/QUICKSTART.md#omp-18101-client).
- **Legacy v0.10.0 native installs:** Single-GPU native owners staying on v0.10.0 keep the
  [immutable v0.10.0 guide](https://github.com/alphastorm/omp-ninfer/blob/v0.10.0/docs/QUICKSTART.md),
  manifest, and OMP 18.4.10 pins.

## How it works

![OMP NInfer architecture](assets/architecture.png)

- **OMP owns the truth.** Transcript, tools, branches, and replay live in Oh My Pi. A turn advances
  provider state only after a complete valid stream and durable local transcript publication.
- **NInfer owns inference and retained state.** The C++/CUDA engine comes from
  [Neroued/ninfer](https://github.com/Neroued/ninfer) and its GPU ports; this project's runtime
  adds explicit Responses state and durable local checkpoints scoped by authenticated client and
  session identity. Retained state is an acceleration, never the source of truth.
- **The manifest owns identity.** [`releases/v0.12.1/manifest.json`](releases/v0.12.1/manifest.json)
  binds the exact client binaries, container digest or native package checksums, model SHA-256,
  profile config, and qualification receipts; `ready` status requires composed external acceptance.

Deep dive: [Architecture](docs/ARCHITECTURE.md) · [Security model](docs/SECURITY.md) ·
[Release lifecycle](docs/RELEASES.md).

## Measured, not estimated

![Historical v0.4.0 RTX 5090 evidence strip](assets/benchmarks.png)

<sub>Historical v0.4.0 strip, one RTX 5090, one sample per point. 0.778 s is server-side time to
first token after checkpoint restoration; 47.92 s is the cold wall time of a separate request pair at
a 109,594-token session (1.79 s warm) — different timing boundaries, not a restart speed-up ratio
(<a href="docs/measurements/2026-08-30-warm-vs-cold-v04.json">warm/cold receipt</a>). The decode and
prompt figures are v0.4.0 values; current gates are in the lanes table above.</sub>

Current per-lane qualification gates and their receipts are in [Qualified lanes](#qualified-lanes)
above (v0.12.1 is a client-only update carrying runtime qualification from v0.12.0 and v0.11.0). In
the historical v0.4.0 RTX 5090 restart receipt (2026-08-30,
[`2026-08-30-rtx5090-durable-qualification.json`](docs/measurements/2026-08-30-rtx5090-durable-qualification.json)),
**109,589 retained tokens** were served after a Docker restart in **24.8 s** end-to-end including
first-touch restoration of a **7.95 GB** checkpoint, with a **56.6 s** model reload measured
separately and **0.778 s** server-side time to first token after restoration — recorded on one
machine, not a current-release timing or a restart speed-up ratio. See
[`docs/BENCHMARKS.md`](docs/BENCHMARKS.md) for measurement methodology, warm-vs-cold and per-lane
charts, upstream model-quality evaluations, and the community results table.

## How it compares

| | OMP NInfer (v0.12.1) | [Ollama](https://ollama.com) | [LM Studio](https://lmstudio.ai) | [llama.cpp server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server) | [vLLM](https://github.com/vllm-project/vllm) |
| --- | --- | --- | --- | --- | --- |
| What it is | Closed set of three qualified OMP + NInfer + Qwen3.8 27B single-GPU lanes with receipts | General local runtime with a large model library | Desktop application and headless daemon with a large model catalog | General GGUF server with the broadest hardware reach | High-throughput general serving engine |
| Session state across turns | Stateful OpenAI Responses (`previous_response_id`, forks, rollback); transcript commits in OMP before GPU state advances | Stateless per request; in-process prefix cache reuses matching prefixes | Stateless per request; chat state lives in the client | Stateless per request; per-slot prefix cache reuses matching prefixes | Stateless core with automatic prefix caching; separate Agentic API gateway adds server state |
| Restart and off-machine checkpoints | Best-effort local checkpoints restored across server restarts on all three lanes; verified host/NAS export and import ([scope](docs/FACTS.md#checkpoint-transport-and-nas-replication)) | In-memory prefix cache lost on process exit; verify current docs | In-memory cache; verify current docs | Prompt cache save/restore flags; different contract | External KV cache connectors available; different architecture |
| Speculative decoding | Profile-specific: DFlash2 draft window 7 on RTX 5090; MTP3 on native RTX 4090 and RTX 3090 | Model and configuration dependent | Optional draft-model settings | Optional draft and ngram setups | Optional draft, MTP, and ngram setups |
| Breadth | Two pinned Qwen3.8 27B artifacts across three exact RTX lanes (two requests in flight on 5090; one per native lane) | Thousands of models across broad hardware | Large catalog with llama.cpp and MLX backends | Any GGUF across CPU, Apple silicon, and GPUs | Broad model and multi-GPU datacenter/consumer support |

Where each shines: **Ollama** is the easiest way to run many models locally, **LM Studio** is the
most polished desktop GUI for browsing and running them, **llama.cpp** has the broadest hardware
and quantization reach, and **vLLM** is the multi-user throughput reference — while **OMP NInfer**
is built for one job: long, stateful Oh My Pi coding sessions on a qualified RTX card with privacy
and release identity verified as invariants. Full comparison and prior-art sources (including the
NInfer port family): [`docs/DECISION_GUIDE.md`](docs/DECISION_GUIDE.md) and
[`docs/RELATED_WORK.md`](docs/RELATED_WORK.md#the-ninfer-family).

## Release integrity

```sh
python3 scripts/verify_release.py --require-ready
python3 -m unittest discover -s tests -v
```

Both commands pass on a tagged release. A `ready` manifest binds the exact upstream Oh My Pi
release binaries, compatibility matrix, runtime container digest and SBOM or native package
checksums, lane-specific model SHA-256, per-lane qualification receipts, and composed
owner-operated external acceptance across all five documented routes. Lifecycle and cut rules:
[`docs/RELEASES.md`](docs/RELEASES.md).

## Documentation

| Document | Purpose |
| --- | --- |
| [`docs/QUICKSTART.md`](docs/QUICKSTART.md) | Lane selection, prerequisites, exact v0.12.1 installation, and executable acceptance checks |
| [`docs/FACTS.md`](docs/FACTS.md) | Canonical current product facts, lane and model identities, durability limits, and non-claims |
| [`docs/DECISION_GUIDE.md`](docs/DECISION_GUIDE.md) | When to choose OMP NInfer versus Ollama, LM Studio, llama.cpp, vLLM, or cloud providers |
| [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md) | Generated compatibility matrix for qualified GPU lanes and stock Oh My Pi client platforms |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Transcript ownership, loopback topology, Responses state lifecycle, and identity chain |
| [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md) | Per-lane qualification receipts, measurement methodology, charts, model quality, and community table |
| [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md) | Append-only CUDA/runtime profiling program and experiment ledger (`EXP-001`..`EXP-095`) |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Threat model, loopback and bearer boundaries, checkpoint storage, and secret redaction |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | Failure signatures, recovery commands, and safe diagnostic fields |
| [`docs/RELATED_WORK.md`](docs/RELATED_WORK.md) | Prior art, the NInfer single-GPU port family, and why no extra gateway sits in the route |
| [`docs/UPSTREAM.md`](docs/UPSTREAM.md) | Upstream watch operation, client applicability reviews, and runtime fork-point ledger |
| [`docs/RELEASES.md`](docs/RELEASES.md) | Living release history (`Version identities`) and maintainer release-cut procedure |
| [`ROADMAP.md`](ROADMAP.md) | Remaining work toward v1.0, deferred research, and explicit non-promises |
| [`CHANGELOG.md`](CHANGELOG.md) | User-visible release and repository change log |
| [`docs/media/README.md`](docs/media/README.md) | Provenance, capture environment, and SHA-256 checksums for recorded demos and cards |

## Help make it better

- **Ran a clean install?** Report
  [time-to-first-turn and every manual step](https://github.com/alphastorm/omp-ninfer/issues/new?template=clean-install-report.yml)
  — install friction is a bug.
- **Measured your card?** Submit numbers with the
  [performance result form](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml)
  after the acceptance checks pass; verified rows join the community table.
- **Work on CUDA kernels?** Pick a measured bottleneck from the
  [performance program](docs/PERFORMANCE.md) and submit before/after receipts with the same form.
- **Need a different model or profile?** File a
  [model/profile request](https://github.com/alphastorm/omp-ninfer/issues/new?template=model-profile-request.yml)
  so artifact identity and qualification scope stay explicit.

Routing and PR rules live in [`CONTRIBUTING.md`](CONTRIBUTING.md). Strip API keys, hostnames,
usernames, prompts, outputs, and raw logs before filing any public issue. The 0.x support boundary
covers only `v0.12.1` and its exact manifest profiles for a single local owner (no SLA or
multi-tenant claim). Report vulnerabilities privately via [`SECURITY.md`](SECURITY.md).

## Credits

1. **[Oh My Pi](https://github.com/can1357/oh-my-pi)** by [can1357](https://x.com/_can1357) — the
   coding agent this appliance serves, building on [Pi](https://github.com/badlogic/pi-mono) by
   Mario Zechner (MIT).
2. **[NInfer](https://github.com/Neroued/ninfer)** by Neroued — the C++/CUDA engine, `.ninfer`
   format, MTP and DFlash2 speculative decoding, hybrid GDN runtime, and evaluation campaigns
   (Apache-2.0).
3. **The Qwen team** — the Qwen3.8 model family, served from the registered NInfer conversions at
   [`neroued/Qwen3.8-27B-NInfer`](https://huggingface.co/neroued/Qwen3.8-27B-NInfer) (Apache-2.0).
4. **[UDPSendToFailed/ninfer-4090](https://github.com/UDPSendToFailed/ninfer-4090)** — the RTX 4090
   port: E8-lattice KV quantization and DirectStorage weight DMA (Apache-2.0).
5. **[Don-Chad/ninfer-3090](https://github.com/Don-Chad/ninfer-3090)** — the RTX 3090 port:
   ReplaySSM and RotorQuant (Apache-2.0).
6. **Algorithm and library lineage** — Gated DeltaNet ([arXiv: 2412.06464](https://arxiv.org/abs/2412.06464)),
   Tri Dao's ReplaySSM note, Z-Lab's DFlash, Unsloth's NVFP4 weights, and vendored `utf8proc`,
   `nlohmann/json`, and `cpp-httplib` ([upstream tracking](docs/UPSTREAM.md)).

Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.

| Repository | Owns |
| --- | --- |
| [`alphastorm/omp-ninfer`](https://github.com/alphastorm/omp-ninfer) | Product front door: release manifests, profiles, quickstart, qualification composition, support boundary |
| [`alphastorm/ninfer`](https://github.com/alphastorm/ninfer) | Public tagged RTX 5090, RTX 4090, and RTX 3090 runtime source and component releases |
| [`can1357/oh-my-pi`](https://github.com/can1357/oh-my-pi) | Upstream Oh My Pi release binaries, pinned by SHA-256 in each release manifest |

Since v0.8.0 the client has been unmodified upstream Oh My Pi, and this project builds or publishes
no client (`omp` is the upstream CLI; **OMP NInfer** names this integration and release layer).

## License

MIT. NInfer and the Qwen artifacts retain their own licenses and notices.
