[![OMP NInfer — durable local inference for coding agents. Your coding session should survive the process. Durable session state on your GPU. Qualified on RTX 5090 · 4090 · 3090.](assets/banner.png)](docs/QUICKSTART.md)

<div align="center">

[Oh My Pi](https://github.com/can1357/oh-my-pi) is the coding agent. [NInfer](https://github.com/Neroued/ninfer)
keeps your session's continuation state resident on your GPU. **OMP NInfer** is the qualified release
that binds them with one hash-pinned Qwen3.8 27B model on an RTX 5090, 4090, or 3090 you own.

Every install route in the guide was run end to end on **v0.17.0** with unmodified
[Oh My Pi 18.18.6](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.6) — 31 steps,
three client platforms, both native lanes
([receipt](releases/v0.17.0/acceptance/composed-external-installation.json)).

### [Get started →](docs/QUICKSTART.md)

[![CI][ci-badge]][ci] [![Release][release-badge]][releases] [![RTX 5090 decode][decode-badge]][benchmarks] [![Context][context-badge]][benchmarks] [![License][license-badge]][license]

[Download v0.17.0](https://github.com/alphastorm/omp-ninfer/releases/tag/v0.17.0) · [Lanes](docs/QUICKSTART.md#choose-your-lane) ·
[Facts](docs/FACTS.md) · [Compare](docs/DECISION_GUIDE.md) · [Benchmarks](docs/BENCHMARKS.md) ·
[Architecture](docs/ARCHITECTURE.md) · [Security](docs/SECURITY.md) · [Troubleshooting](docs/TROUBLESHOOTING.md) ·
[Roadmap](ROADMAP.md) · [Changelog](CHANGELOG.md)

</div>

[ci]: https://github.com/alphastorm/omp-ninfer/actions/workflows/ci.yml
[ci-badge]: https://img.shields.io/github/actions/workflow/status/alphastorm/omp-ninfer/ci.yml?branch=main&label=CI&labelColor=0B0E11
[releases]: https://github.com/alphastorm/omp-ninfer/releases
[release-badge]: https://img.shields.io/github/v/release/alphastorm/omp-ninfer?filter=v*&label=release&color=8E7BE8&labelColor=0B0E11
[benchmarks]: docs/BENCHMARKS.md
[decode-badge]: https://img.shields.io/badge/RTX%205090%20decode-181.92%20tok%2Fs-8E7BE8?labelColor=0B0E11
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

All three lanes share a 131,072-token context, DFlash2 speculative decoding with draft window 7,
JSON-schema output, and the same 20.4 GB Qwen3.8 27B artifact (`81f924d4`).

| Lane | Runs as | Serves | Decode | Exact&nbsp;retrieval, 130,048&nbsp;tokens |
| --- | --- | --- | --- | --- |
| **RTX&nbsp;5090** | Docker Desktop/WSL2 container on Windows 11; clients: Windows (local), macOS over a manual SSH tunnel (preview), Linux under WSL2 | Two requests in flight; vision, tools, and preserved thinking | [181.92&nbsp;tok/s](releases/v0.17.0/qualification/rtx5090.json) | [56.63&nbsp;s](releases/v0.17.0/qualification/rtx5090.json) |
| **RTX&nbsp;4090** | Native Windows 11 package; Windows client (local) | One request at a time; text and tools | [254.59&nbsp;tok/s](releases/v0.17.0/qualification/rtx4090.json) | [83.54&nbsp;s](releases/v0.17.0/qualification/rtx4090.json) |
| **RTX&nbsp;3090** | Native Windows 11 package; Windows client (local) | Two requests in flight over one shared 131,072-token pool, under a 350 W serving cap; text and tools | [148.70&nbsp;tok/s](releases/v0.17.0/qualification/rtx3090.json) | [188.94&nbsp;s](releases/v0.17.0/qualification/rtx3090.json) |

Each number links to its qualification receipt. RTX 5090 retrieval is from a cold start; native
decode is measured with one request at a time (`C1`).

Both native lanes install on one two-GPU host, each bound to its GPU UUID, and run one at a time on
port 18082. Checkpoints are best effort and restore only on the same runtime, model, profile, and
credentials. Exact component, source, and model identities: [facts](docs/FACTS.md#current-release) ·
[glossary](docs/FACTS.md#glossary) · [manifest](releases/v0.17.0/manifest.json).

<a id="rtx-3090-known-limitation"></a>

> [!WARNING]
> **RTX 3090 known limitation.** Every documented install step passed on `v0.17.0`, but the
> automatic-compaction campaign that follows them failed under retained-context pressure and
> was waived by the project founder with disclosure. If you run long sessions on an RTX 3090,
> stay on `v0.16.2` or restart the lane after long sessions until a native re-cut is
> qualified. Details: [release notes](releases/v0.17.0/NINFER_RELEASE_NOTES.md) ·
> [route waiver](releases/v0.17.0/qualification/rtx3090-route-waiver.json) ·
> [#149](https://github.com/alphastorm/omp-ninfer/issues/149).

## Get started

1. **[Choose your lane](docs/QUICKSTART.md#choose-your-lane)** and check its prerequisites.
2. **Clone tag `v0.17.0`** and run `python3 scripts/verify_release.py --require-ready`.
3. **[Install the stock Oh My Pi 18.18.6 client](docs/QUICKSTART.md#omp-18186-client)** with the
   fail-closed config and per-model fragment.
4. **Run the acceptance checks** at the end of your lane's route: tool turn, continuation, restart
   survival, fail closed.

### Upgrading from v0.16.2

`v0.17.0` updates the client to Oh My Pi 18.18.6 and rebuilds the RTX 5090 container runtime. The
native packages and the model are unchanged.

- **Client.** [Install the stock Oh My Pi 18.18.6 client](docs/QUICKSTART.md#omp-18186-client) with
  this release's fail-closed config and per-model fragment
  ([18.18.6 review](docs/measurements/2026-11-10-omp-18186-client-upgrade-review.json)). The
  fragments pin `tokenizer: qwen3` on the `q38-ninfer` model alias in each `models.fragment.yml`,
  and [`examples/manual-tunnel/fail-closed.yml`](examples/manual-tunnel/fail-closed.yml) disables
  automatic updates and the setup wizard explicitly.
- **RTX 5090.** Stop an existing `v0.16.2` RTX 5090 container with
  `examples/manual-tunnel/stop-ninfer.sh` from your `v0.16.2` checkout before starting the rebuilt
  `v0.7.0-qwen38-5090-beta.6` container runtime. The new runtime writes checkpoints to its own host
  directory, `checkpoints-v017`; keep the prior `checkpoints-v013` untouched for rollback.
- **RTX 4090 and RTX 3090.** The native Windows packages (`v0.8.0-qwen38-4090-beta.2` and
  `v0.8.0-qwen38-3090-beta.2`) are carried unchanged from `v0.16.2`; keep native checkpoint roots
  untouched for rollback. RTX 3090 owners: read the
  [known limitation](#rtx-3090-known-limitation) first.
- **Sessions.** After the upgrade, Oh My Pi replays its authoritative transcripts for a fresh
  prefill.

What the rebuilt RTX 5090 runtime changes: bounded resume/fresh admission, so resumed long sessions
are not starved under context pressure (addressing upstream
[#434](https://github.com/Neroued/ninfer/issues/434)), and serving robustness for malformed tool
arguments, effort normalization, request-local numerical failures, and stop/drain final-save
ordering (addressing upstream
[#440](https://github.com/Neroued/ninfer/issues/440)/[#441](https://github.com/Neroued/ninfer/issues/441)/[#446](https://github.com/Neroued/ninfer/issues/446)).
Everything else: [release notes](releases/v0.17.0/NINFER_RELEASE_NOTES.md) ·
[changelog](CHANGELOG.md).

Native owners staying on `v0.10.0` keep the
[v0.10.0 guide](https://github.com/alphastorm/omp-ninfer/blob/v0.10.0/docs/QUICKSTART.md).

### Next on main — prepared v0.18.0

**Prepared next: v0.18.0 / stock OMP 18.18.7.** Re-cuts all three GPU runtime
lanes from one frozen fork engine commit `F4` (`48c8ac4644322f024b5c3bd5b657af5874567251` in `alphastorm/ninfer` on
upstream `64d10fbf`): RTX 5090 `v0.7.0-qwen38-5090-beta.7` (image
`ghcr.io/alphastorm/ninfer-runtime@sha256:496195ecd6cf1f50fcd9dc62cf7b51787f599cc2b196e194baf050c4b149e119`, server
`804ef8ac6d062dc8da8784ba3f52e5cece2178a5f5bc46cb2c7bc1d3e8937fe3`, isolated host checkpoint directory `checkpoints-v018` mounted at
container path `/checkpoints-v013`), native Windows RTX 4090 `v0.8.0-qwen38-4090-beta.3` (package
`ac41700ac2bb9fb171188f35e73481cfd9f1140c5781320b1e6304ee760d7166`, server `a5266ae676305cc56086df6d3b8dc8968be110b3cf0eb7b18147adafc2f66d22`, build profile
`native-v0.8.0-beta.3-rtx4090`), and native Windows RTX 3090 `v0.8.0-qwen38-3090-beta.3`
(package `bf1ceaa9eb522a8c8d9372bec475d6e4e4666e6a995302cd20035e80ae3e5edd`, server `e571328699be41d90eff8743d94da26e8f587e48bc32f618013625af7ad0bfe0`, build
profile `native-v0.8.0-beta.3-tc-rtx3090`), with unmodified upstream
[Oh My Pi v18.18.7](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.7)
(`e325ffc73ab86e03bdd20a91b77d8e2b3964c906`, release `440868478`) and the unchanged
`20,437,521,664`-byte Qwen3.8 27B container version 3 model (`81f924d4`).

- **Engine changes (`F4`):** Device-staged durable checkpoint saves when the Host arena is full
  ([fork #89](https://github.com/alphastorm/ninfer/issues/89), folding
  [#84](https://github.com/alphastorm/ninfer/issues/84);
  [PR #109](https://github.com/alphastorm/ninfer/pull/109) `3213508fe`), off-worker export/import
  prepares held to an operation-free boundary with budget-free `>= 100 ms`-spaced pressure-busy
  retries ([PR #111](https://github.com/alphastorm/ninfer/pull/111) `33088ad2c`), bounded `K = 4`
  fresh-admission priority at context-operation boundaries
  ([fork #102](https://github.com/alphastorm/ninfer/issues/102);
  [PR #108](https://github.com/alphastorm/ninfer/pull/108) `6ec05f211`), native controller
  GPU-owner lease restoration on a refused `Stop`, removal postconditions, junction containment,
  exact-byte package archiving, and the four-key `beta.3` variant allowlist
  ([PR #107](https://github.com/alphastorm/ninfer/pull/107) `2454c0629`,
  [#91](https://github.com/alphastorm/ninfer/pull/91),
  [#87](https://github.com/alphastorm/ninfer/issues/87),
  [#90](https://github.com/alphastorm/ninfer/issues/90)), upstream malformed tool-history
  regression vectors ([PR #106](https://github.com/alphastorm/ninfer/pull/106) `92209112`), and the
  `Group64` `A8` build-profile configure guard and Apache-2.0 kernel attribution
  ([PR #112](https://github.com/alphastorm/ninfer/pull/112) `fd95455df`).
- **Variant-dependent selections (release stage keeps only the selected option per axis):**
  - Native `sm_86`/`sm_89` small-T tensor-core verify ([PR #104](https://github.com/alphastorm/ninfer/pull/104),
    `T=8/16`) is in `F4`, enabled only by the RTX 3090 `tc` profile
    ([release notes](releases/v0.18.0/NINFER_RELEASE_NOTES.md)).
  - Selected native profiles `native-v0.8.0-beta.3-tc-rtx3090` (RTX 3090) and
    `native-v0.8.0-beta.3-rtx4090` (RTX 4090) ship under the bound selection decision and a
    passing `1,120`-prompt `EXP-085` quality screen
    ([release notes](releases/v0.18.0/NINFER_RELEASE_NOTES.md)).
  - RTX 5090 cadence-only prefill pacing stays default-off (`--prefill-stall-budget-ms 0
    --decode-rounds-per-prefill 0`) in `qwen38-5090-v0.13.0` (configuration SHA-256 `751d22dc`)
    after failing 3 of 6 preregistered bars
    ([release notes](releases/v0.18.0/NINFER_RELEASE_NOTES.md)).
- **Excluded candidates and disclosed residuals:** `sm_120` `Group64` `A8` prefill
  ([PR #105](https://github.com/alphastorm/ninfer/pull/105) `93348eb9`, closed unmerged) was killed
  at the `K1` cold-L2 prefill-speed prescreen (`0.784860×` at `512`-token pass width and `0.983623×`
  at `1,024`-token pass width, below the `1.00×` kill bar); restricted tool-argument copy drafting
  (`+5.24%` to `+10.12%` across `2,998` turns, below the `+15%` session-decode bar) is not shipped.
  On Windows, stock OMP `18.18.7` changes the `bash` tool description sent to the model when `bash`
  is advertised; `scripts/hosts/omp-client-probe.py` invokes `omp` with `--tools read` and does not
  separately probe `bash` or `edit` beyond the `31`-block route acceptance
  ([18.18.7 review](docs/measurements/2026-11-11-omp-18187-client-upgrade-review.json)). The
  request-level HTTP `503` half of `#89` did not reproduce on the proxy host (`3` fixtures) and is
  settled only by the RTX 3090 acceptance run (**pending**; [release notes](releases/v0.18.0/NINFER_RELEASE_NOTES.md));
  the [Neroued/ninfer#434](https://github.com/Neroued/ninfer/issues/434) per-rotation fresh-window
  consumption when a pressure save is pending (`checkpoints_.pending()`) or no lane is free remains
  tracked in [fork #103](https://github.com/alphastorm/ninfer/issues/103). Component cuts,
  qualification receipts, five-route (`31`-block) and three-client-platform acceptance, review
  councils, immutable pins, and founder-owned publication are pending (staged notes path
  `releases/v0.18.0/NINFER_RELEASE_NOTES.md`).
  Published install authority stays `v0.17.0`
  ([immutable v0.17.0 guide](https://github.com/alphastorm/omp-ninfer/blob/v0.17.0/docs/QUICKSTART.md)).

## How it works

![How OMP NInfer works. Oh My Pi, the coding-agent client, owns the truth: transcript, tools, branches, and replay, written to disk before provider state advances. An authenticated loopback route (127.0.0.1, bearer token) connects it to NInfer, the inference engine on your GPU, which owns the continuation: Qwen3.8 27B and the session's Responses state stay resident, checkpointed to local disk. OMP NInfer is the qualified release: one manifest pins client, runtime, model, and profile. When the server restarts, the session resumes from its checkpoint (best effort; same runtime, model, profile, and credentials). With no usable checkpoint, Oh My Pi replays the transcript: a fresh prefill, never a broken session. When the GPU is unreachable, the turn fails and is never answered by a cloud model.](assets/architecture.png)

Oh My Pi (coding-agent client) → OMP NInfer (qualified appliance and release layer) → NInfer
(inference engine) → Qwen3.8 27B (served model).

- **Oh My Pi owns the truth.** A turn advances provider state only after a complete stream and a
  durable transcript write.
- **NInfer owns inference and retained state.** The C++/CUDA engine from
  [Neroued/ninfer](https://github.com/Neroued/ninfer) and its GPU ports, plus this project's
  explicit Responses state and checkpoints. Retained state accelerates; it is never the source of truth.
- **The manifest owns identity.** [`releases/v0.17.0/manifest.json`](releases/v0.17.0/manifest.json)
  binds client, runtime, model, profile, and receipts; `ready` requires composed external acceptance.

[Architecture](docs/ARCHITECTURE.md) · [Security model](docs/SECURITY.md) ·
[Release lifecycle](docs/RELEASES.md)

## Measured, not estimated

![Qualification receipts for v0.17.0, each lane on its own gate, not a ranking. RTX 5090: 181.92 tok/s decode and exact 130,048-token retrieval in 56.63 s from a cold start. RTX 4090: 254.59 tok/s decode and exact retrieval in 83.54 s. RTX 3090: 148.70 tok/s decode and exact retrieval in 188.94 s.](assets/benchmarks.png)

Each lane is measured on its own gate, machine, and profile; the figure is not a ranking. Method,
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
| [Performance](docs/PERFORMANCE.md) | Kernel and schedule experiment ledger |
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
- **Contributing without a GPU?** No GPU is needed for
  [contributor acceptance and doctor](docs/QUICKSTART.md#contributor-acceptance-and-preflight),
  which run in rehearsal/offline mode; rehearsal receipts never qualify a release.

Routing rules: [CONTRIBUTING.md](CONTRIBUTING.md). Strip keys, hostnames, prompts, outputs, and raw
logs before filing. Support covers `v0.17.0` and its exact profiles for a single local owner; no SLA.
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
