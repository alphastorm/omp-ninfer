[![OMP NInfer — your coding session should survive the process. Qualified on RTX 5090 · 4090 · 3090, v0.15.0.](assets/banner.png)](docs/QUICKSTART.md)

<div align="center">

[Oh My Pi](https://github.com/can1357/oh-my-pi) is the coding agent. [NInfer](https://github.com/Neroued/ninfer)
keeps your session's continuation state resident on your GPU. **OMP NInfer** is the qualified release
that binds them with one hash-pinned Qwen3.8 27B model on an RTX 5090, 4090, or 3090 you own.

Every install route in the guide was run end to end on **v0.15.0** with unmodified
[Oh My Pi 18.14.0](https://github.com/can1357/oh-my-pi/releases/tag/v18.14.0) — 31 steps,
three client platforms, both native lanes
([receipt](releases/v0.15.0/acceptance/composed-external-installation.json)).

### [Get started →](docs/QUICKSTART.md)

[![CI][ci-badge]][ci] [![Release][release-badge]][releases] [![RTX 5090 decode][decode-badge]][benchmarks] [![Context][context-badge]][benchmarks] [![License][license-badge]][license]

[Download v0.15.0](https://github.com/alphastorm/omp-ninfer/releases/tag/v0.15.0) · [Lanes](docs/QUICKSTART.md#choose-your-lane) ·
[Facts](docs/FACTS.md) · [Compare](docs/DECISION_GUIDE.md) · [Benchmarks](docs/BENCHMARKS.md) ·
[Architecture](docs/ARCHITECTURE.md) · [Security](docs/SECURITY.md) · [Troubleshooting](docs/TROUBLESHOOTING.md) ·
[Roadmap](ROADMAP.md) · [Changelog](CHANGELOG.md)

</div>

[Contributor acceptance and doctor](docs/QUICKSTART.md#contributor-acceptance-and-preflight) run without GPU hardware in rehearsal/offline mode; rehearsal receipts never qualify a release.

[ci]: https://github.com/alphastorm/omp-ninfer/actions/workflows/ci.yml
[ci-badge]: https://img.shields.io/github/actions/workflow/status/alphastorm/omp-ninfer/ci.yml?branch=main&label=CI&labelColor=0B0E11
[releases]: https://github.com/alphastorm/omp-ninfer/releases
[release-badge]: https://img.shields.io/github/v/release/alphastorm/omp-ninfer?filter=v*&label=release&color=8E7BE8&labelColor=0B0E11
[benchmarks]: docs/BENCHMARKS.md
[decode-badge]: https://img.shields.io/badge/RTX%205090%20decode-182.49%20tok%2Fs-8E7BE8?labelColor=0B0E11
[context-badge]: https://img.shields.io/badge/context-130%2C048%20tokens%20exact-1C232B?labelColor=0B0E11
[license]: LICENSE
[license-badge]: https://img.shields.io/github/license/alphastorm/omp-ninfer?color=1C232B&labelColor=0B0E11

## What it does

A long coding session is 100K tokens of transcript, thinking, tool calls, and images. Sent to a
cloud provider, every token is metered and every file leaves your machine. Sent to a stateless
local server, every turn re-sends the whole transcript. A live NInfer, llama.cpp, or vLLM process
already avoids recomputing an unchanged prefix while it stays up; that is prior art, and this
project does not claim it. What OMP NInfer adds is continuation you can rely on:

- **Explicit and durable.** Oh My Pi drives NInfer through stateful OpenAI Responses
  (`previous_response_id`); forks and rollback are qualified, and checkpoints restore after a server
  restart. Oh My Pi commits the transcript first, so losing retained state degrades to a replay,
  never a broken session.
- **Private and fail-closed.** Both endpoints bind loopback only, every request is
  bearer-authenticated, and model fallback is off: an unreachable GPU fails the turn instead of
  answering from a cloud model. This is acceptance-tested, not configured.
- **Exact and verifiable.** Model SHA-256, container digest and SBOM, native package and client
  checksums, and every qualification receipt are bound in one manifest;
  `python3 scripts/verify_release.py --require-ready` proves your clone is the qualified release.

<div align="center">

<img src="docs/media/omp-ninfer-demo-v14.gif" alt="Oh My Pi on OMP NInfer (v0.14.0 recording, RTX 5090): finds one failing LRU-cache test and fixes the bug in lru.py, reruns the tests to green, restarts the ninfer-serve container mid-session, and answers a follow-up from the restored session, with idle gaps and the reload compressed." width="900">

<sub>Recorded on v0.14.0 (RTX 5090): LRU bug fixed, tests green, ninfer-serve restarted
mid-session, follow-up answered reusing 10,375 retained prompt tokens. 32 s, idle gaps and the
36 s reload compressed · <a href="docs/media/omp-ninfer-demo-v14.mp4">MP4</a> · <a href="docs/media/README.md#canonical-files">provenance</a></sub>

</div>

## Is it for you

**Use OMP NInfer when** you run Oh My Pi, own an RTX 5090, 4090, or 3090 on Windows 11, want
Qwen3.8 27B, and care about long private sessions that survive a server restart.

**Use something else when** you want a broad model catalog ([Ollama](https://ollama.com)), a
desktop GUI ([LM Studio](https://lmstudio.ai)), the widest hardware reach or Apple silicon
([llama.cpp](https://github.com/ggml-org/llama.cpp)), or multi-user throughput
([vLLM](https://github.com/vllm-project/vllm)). Candid comparison: [decision guide](docs/DECISION_GUIDE.md).

## Qualified lanes

| Lane | Host and client | What you get | Measured |
| --- | --- | --- | --- |
| **RTX 5090** | Windows 11 + Docker Desktop/WSL2 container; Windows client local, macOS over a manual SSH tunnel (preview), Linux client under WSL2 | 131,072-token context, two requests in flight, DFlash2 draft window 7, JSON-schema output, vision + tools + preserved thinking | 182.49 tok/s decode; exact 130,048-token retrieval in 57.00 s cold ([receipt](releases/v0.15.0/qualification/rtx5090.json)) |
| **RTX 4090** | Native Windows 11 package; Windows client local | 131,072-token context, one request at a time, MTP3, JSON-schema output, text + tools | 151.54 tok/s C1 decode; exact 130,048-token retrieval in 81.78 s ([receipt](releases/v0.15.0/qualification/rtx4090.json)) |
| **RTX 3090** | Native Windows 11 package; Windows client local | 131,072-token context, one request at a time, MTP3, 350 W serving cap, JSON-schema output, text + tools | 90.64 tok/s C1 decode; exact 130,048-token retrieval in 187.88 s ([receipt](releases/v0.15.0/qualification/rtx3090.json)) |

Both native lanes install on one two-GPU host, each bound to its GPU UUID, and run one at a time on
port 18082; all three lanes serve the same 20.4 GB Qwen3.8 27B model container version 3 artifact
(`81f924d4`). Checkpoints are best effort and restore only on the same runtime, model, profile, and
credentials. Exact component, source, and model identities: [facts](docs/FACTS.md#current-release) ·
[manifest](releases/v0.15.0/manifest.json).

## Get started

1. **[Choose your lane](docs/QUICKSTART.md#choose-your-lane)** and check its prerequisites.
2. **Clone tag `v0.15.0`** and run `python3 scripts/verify_release.py --require-ready`.
3. **[Install the stock Oh My Pi 18.14.0 client](docs/QUICKSTART.md#omp-18140-client)** with the
   fail-closed config and per-model fragment.
4. **Run the acceptance checks** at the end of your lane's route: tool turn, continuation, restart
   survival, fail closed.

Upgrading from v0.14.0 updates only the stock Oh My Pi client to **18.14.0** (upstream release
binaries rebuilt with Bun 1.4.4 for CVE-2026-91403 and CVE-2026-111497). The RTX 5090 container
(`v0.7.0-qwen38-5090-beta.3`, image `760fb6be`, server `55f0b95a`, profile `qwen38-5090-v0.13.0`,
checkpoint directory `checkpoints-v013`) and both native Windows RTX 4090
(`v0.7.0-qwen38-4090-beta.3`) and RTX 3090 (`v0.7.0-qwen38-3090-beta.3`) packages (checkpoint
stores `session-checkpoints-v3` with mandatory strict origin authentication; keep prior roots
untouched and replay OMP transcripts), along with the shared published model container version 3
(`qwen3_8_27b-v3.ninfer`, `81f924d4`) and common engine source `2c6f423b` on upstream
`Neroued/ninfer` master `64d10fbf`, remain unchanged from v0.14.0. **RTX 3090 upgrade from
v0.13.1: stop the running RTX 3090 lane (`Control-Release.ps1 -Action Stop`) before installing
v0.14.0 or v0.15.0** — a running v0.13.1 lane holds a 300 W GPU-owner lease that the `beta.3`
installer refuses against the 350 W serving cap, leaving the old lane running unchanged; a stopped
lane upgrades normally ([#94](https://github.com/alphastorm/omp-ninfer/issues/94)). Native owners
staying on v0.10.0 keep the
[v0.10.0 guide](https://github.com/alphastorm/omp-ninfer/blob/v0.10.0/docs/QUICKSTART.md).

## How it works

![OMP NInfer architecture: Oh My Pi keeps the truth, an authenticated loopback route, NInfer keeps the continuation](assets/architecture.png)

Oh My Pi (coding-agent client) → OMP NInfer (qualified appliance and release layer) → NInfer
(inference engine) → Qwen3.8 27B (served model).

- **Oh My Pi owns the truth.** Transcript, tools, branches, and replay. A turn advances provider
  state only after a complete stream and a durable transcript write.
- **NInfer owns inference and retained state.** The C++/CUDA engine from
  [Neroued/ninfer](https://github.com/Neroued/ninfer) and its GPU ports, plus this project's
  explicit Responses state and checkpoints. Retained state accelerates; it is never the source of truth.
- **The manifest owns identity.** [`releases/v0.15.0/manifest.json`](releases/v0.15.0/manifest.json)
  binds client, runtime, model, profile, and receipts; `ready` requires composed external acceptance.

[Architecture](docs/ARCHITECTURE.md) · [Security model](docs/SECURITY.md) ·
[Release lifecycle](docs/RELEASES.md)

## Measured, not estimated

![Qualification receipts for v0.15.0: RTX 5090 182.49 tok/s and 57.00 s exact retrieval; RTX 4090 151.54 tok/s and 81.78 s; RTX 3090 90.64 tok/s and 187.88 s](assets/benchmarks.png)

Each lane is measured on its own gate, machine, and profile; the strip is not a ranking. Method,
per-lane charts, the warm-versus-cold boundary rules, model quality, and the community table:
[benchmarks](docs/BENCHMARKS.md).

## Release integrity

```sh
python3 scripts/verify_release.py --require-ready
python3 -m unittest discover -s tests -v
```

Both pass on a tagged release. A `ready` manifest binds the upstream Oh My Pi binaries,
compatibility matrix, container digest and SBOM or native package checksums, lane-specific model
SHA-256, per-lane qualification receipts, and owner-operated acceptance of every documented route.
Lifecycle and cut rules: [releases](docs/RELEASES.md).

## Documentation

| Document | What it answers |
| --- | --- |
| [Quickstart](docs/QUICKSTART.md) | Which lane, prerequisites, exact install, acceptance checks |
| [Facts](docs/FACTS.md) | Current identities, limits, and non-claims in one place |
| [Decision guide](docs/DECISION_GUIDE.md) | This versus Ollama, LM Studio, llama.cpp, vLLM |
| [Compatibility](docs/COMPATIBILITY.md) | Qualified client and runtime combinations (generated) |
| [Architecture](docs/ARCHITECTURE.md) | State ownership, loopback topology, identity chain |
| [Benchmarks](docs/BENCHMARKS.md) | Receipts, method, charts, model quality, community results |
| [Performance](docs/PERFORMANCE.md) | Kernel and schedule experiment ledger (`EXP-001`..`EXP-097`) |
| [Security](docs/SECURITY.md) | Threat model and boundaries |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Failure signatures and recovery |
| [Related work](docs/RELATED_WORK.md) | Prior art and the NInfer port family |
| [Upstream](docs/UPSTREAM.md) | Upstream watch and fork points |
| [Releases](docs/RELEASES.md) | Version history and how a release is cut |
| [Roadmap](ROADMAP.md) | Remaining work and explicit non-promises |
| [Changelog](CHANGELOG.md) | What changed, per release |
| [Media provenance](docs/media/README.md) | Checksums and capture notes for every recording |

## Help make it better

- **Ran a clean install?** Report
  [time-to-first-turn and every manual step](https://github.com/alphastorm/omp-ninfer/issues/new?template=clean-install-report.yml);
  install friction is a bug.
- **Measured your card?** Submit the
  [performance result form](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml)
  after the acceptance checks pass.
- **Work on CUDA kernels?** Pick a bottleneck from the [performance program](docs/PERFORMANCE.md)
  and send before/after receipts.
- **Need another model or profile?** File a
  [model/profile request](https://github.com/alphastorm/omp-ninfer/issues/new?template=model-profile-request.yml).

Routing rules: [CONTRIBUTING.md](CONTRIBUTING.md). Strip keys, hostnames, prompts, outputs, and raw
logs before filing. Support covers `v0.15.0` and its exact profiles for a single local owner; no SLA.
Vulnerabilities: [private reporting](SECURITY.md), never a public issue.

## Credits

- **[Oh My Pi](https://github.com/can1357/oh-my-pi)** by [can1357](https://x.com/_can1357), built
  on [Pi](https://github.com/badlogic/pi-mono) by Mario Zechner (MIT). The coding agent this
  appliance serves; since v0.8.0 the client is the unmodified upstream binary and this project
  publishes no client.
- **[NInfer](https://github.com/Neroued/ninfer)** by Neroued (Apache-2.0). The C++/CUDA engine,
  `.ninfer` format, MTP and DFlash2 speculative decoding, and evaluation campaigns. Public runtime
  source for all three lanes: [alphastorm/ninfer](https://github.com/alphastorm/ninfer).
- **The Qwen team** (Apache-2.0). Qwen3.8 27B, served from the registered conversions at
  [neroued/Qwen3.8-27B-NInfer](https://huggingface.co/neroued/Qwen3.8-27B-NInfer).
- **[UDPSendToFailed/ninfer-4090](https://github.com/UDPSendToFailed/ninfer-4090)** and
  **[Don-Chad/ninfer-3090](https://github.com/Don-Chad/ninfer-3090)** (Apache-2.0). The RTX 4090 and
  RTX 3090 ports the native lanes build on.
- Gated DeltaNet ([arXiv: 2412.06464](https://arxiv.org/abs/2412.06464)), Tri Dao's ReplaySSM note,
  Z-Lab's DFlash, Unsloth's NVFP4 weights, and vendored `utf8proc`, `nlohmann/json`, and
  `cpp-httplib`; tracked in [upstream](docs/UPSTREAM.md).

Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.

## License

MIT. NInfer and the Qwen artifacts retain their own licenses and notices.
