![OMP NInfer](assets/banner.png)

<div align="center">

# OMP NInfer

**Private Qwen coding appliance for RTX 5090**

Run a stateful Qwen3.8 coding model on your own NVIDIA GPU and use it from
[Oh My Pi](https://github.com/can1357/oh-my-pi) on a Mac.

**[Early-access setup](docs/QUICKSTART.md)** · **[Release status](docs/RELEASES.md)** ·
**[Architecture](docs/ARCHITECTURE.md)** · **[Security](docs/SECURITY.md)** ·
**[Troubleshooting](docs/TROUBLESHOOTING.md)** · **[Changelog](CHANGELOG.md)**

</div>

> [!IMPORTANT]
> The tracked `v0.1.0-beta.1` release candidate is **not published yet**. Its manifest is deliberately
> `draft` and the verifier refuses release mode until the immutable OMP artifact, NInfer image,
> SBOM, Homebrew beta cask, and external-install smoke are bound. Do not substitute an unpinned
> image or an older local package.

OMP NInfer is the product and release layer joining OMP, NInfer, and one qualified Qwen3.8 artifact.
It owns the supported topology, versioned profile, release manifest, installation path, qualification
summary, and support boundary. It does not copy the OMP agent or NInfer runtime into a third
implementation.

## First release

`v0.1.0-beta.1` is intentionally narrow so a handful of invited testers can provide useful feedback
without turning an early package into a broad support claim.

| Boundary | `v0.1.0-beta.1` |
| --- | --- |
| OMP client | Apple-silicon macOS, installed from the `omp-beta` Homebrew cask |
| Inference host | One user-controlled Linux or WSL2 host with one NVIDIA GeForce RTX 5090 |
| Model | Exact Qwen3.8 27B NInfer artifact pinned in the release manifest |
| Runtime | NInfer, BF16 KV, MTP3, Vision enabled, one active request, 131,072-token ceiling |
| Connection | Authenticated NInfer on remote loopback through a local SSH port forward |
| OMP integration | Custom `openai-responses` provider with NInfer stateful continuation enabled |
| Audience | Invited early-access testers; no general-availability promise |

The runtime qualification recorded an exact 130,048-token retrieval, OpenAI/Anthropic/Responses
protocol behavior, image input, stateful continuation and forks, cache reuse, an exact Golden task,
and 209.04 decode tokens/second on the measured RTX 5090 profile. Those measurements belong to the
recorded candidate and machine; they are not universal GPU or end-to-end latency claims. The later
clean-source candidate proof re-established the exact source, binary, model, and configuration
identity without re-running the benchmark. See
[`releases/v0.1.0-beta.1/qualification.json`](releases/v0.1.0-beta.1/qualification.json).

## What is deliberately deferred

The first beta does **not** claim automated remote appliance installation, managed upgrade or
rollback, process-restart continuation, RTX 4090 support, multi-GPU scheduling, or broad hardware
compatibility. OMP's `omp appliance ...` source work remains the long-term command surface, but the
first beta uses a manual tunnel and a custom provider while that remote lifecycle is finished and
qualified. See [`ROADMAP.md`](ROADMAP.md).

## Repository ownership

![OMP NInfer architecture](assets/architecture.png)

- [`alphastorm/omp-ninfer`](https://github.com/alphastorm/omp-ninfer): product front door, release
  authority, install/support documentation, profiles, and qualification summaries.
- [`alphastorm/ninfer`](https://github.com/alphastorm/ninfer): RTX 5090 inference engine, server,
  container, and numerical/runtime evidence.
- [`alphastorm/ninfer-4090`](https://github.com/alphastorm/ninfer-4090): RTX 4090 runtime work,
  deferred from the first beta.
- [`alphastorm/homebrew-omp`](https://github.com/alphastorm/homebrew-omp): stable and beta Homebrew
  casks for the macOS OMP client.

The user-facing command remains `omp`. “Appliance” names the install/operate concept and command
surface; **OMP NInfer** names this integration and repository.

## Release integrity

The release manifest is the authority for component identity. A release is ready only when:

```sh
python3 scripts/verify_release.py --require-ready
python3 -m unittest discover -s tests -v
```

The first command currently fails by design while the candidate is a draft. The manifest must move
through an installable `candidate` only after every executable artifact is immutable; maintainers
then run the clean external-install gate with `--require-installable`. It moves to `ready` only after
that result and the final qualification publication are exact. Published tags and release assets
must use the same ready manifest bytes.

## Feedback

Use the hardware-report or installation-failure issue forms. Remove API keys, hostnames, usernames,
private prompts, model outputs, and raw request logs before attaching anything. The support boundary
assumes a single trusted owner on both machines; this beta is not a multi-tenant service.

OMP NInfer is a community project; it is not affiliated with or endorsed by Oh My Pi, Qwen, or
NVIDIA.

## License

MIT. NInfer and the Qwen artifact retain their own licenses and notices.
