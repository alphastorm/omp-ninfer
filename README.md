![OMP NInfer](assets/banner.png)

<div align="center">

# OMP NInfer

**Private Qwen coding appliance for RTX 5090**

Run a stateful Qwen3.8 coding model on your own NVIDIA GPU and use it from
[Oh My Pi](https://github.com/can1357/oh-my-pi) on native Windows, Linux, or a Mac.

**[Early-access setup](docs/QUICKSTART.md)** · **[Release status](docs/RELEASES.md)** ·
**[Architecture](docs/ARCHITECTURE.md)** · **[Security](docs/SECURITY.md)** ·
**[Troubleshooting](docs/TROUBLESHOOTING.md)** · **[Changelog](CHANGELOG.md)**

</div>

> [!IMPORTANT]
> The tracked `v0.1.0-beta.1` manifest is a technically **ready** invited-tester release.
> The primary accepted route is native Windows OMP with Docker Desktop WSL2 on one RTX 5090; the
> published macOS and Linux clients remain preview profiles. Every component is immutable and bound.
> Use only the tagged quickstart and checksums; this is not a general-availability support claim.

OMP NInfer is the product and release layer joining OMP, NInfer, and one qualified Qwen3.8 artifact.
It owns the supported topology, versioned profile, release manifest, installation path, qualification
summary, and support boundary. It does not copy the OMP agent or NInfer runtime into a third
implementation.

## First release

`v0.1.0-beta.1` is intentionally narrow so a handful of invited testers can provide useful feedback
without turning an early package into a broad support claim. The versioned
[`compatibility.json`](compatibility.json) is the platform/profile authority; the public
[`compatibility matrix`](docs/COMPATIBILITY.md) is generated from it. `preview` and `blocked` rows
are not support claims, even when they reference the shared qualified RTX 5090 runtime.
The ready primary profile is `qwen38-rtx5090-windows-docker-local`; it passed a clean public-asset
install, tools, Vision, stateful resume, fail-closed outage behavior, and exact runtime restoration.

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
compatibility. Native Windows is the accepted local client/runtime topology; managed macOS SSH and
native Linux remain preview profiles. See [`ROADMAP.md`](ROADMAP.md).

## Repository ownership

![OMP NInfer architecture](assets/architecture.png)

- [`alphastorm/omp-ninfer`](https://github.com/alphastorm/omp-ninfer): product front door, release
  authority, install/support documentation, profiles, and qualification summaries.
- [`alphastorm/ninfer`](https://github.com/alphastorm/ninfer): RTX 5090 inference engine, server,
  container, and numerical/runtime evidence.
- [`alphastorm/ninfer-4090`](https://github.com/alphastorm/ninfer-4090): RTX 4090 runtime work,
  deferred from the first beta.
- [`alphastorm/homebrew-omp`](https://github.com/alphastorm/homebrew-omp): published native client
  component archives plus stable and beta Homebrew casks.

The user-facing command remains `omp`. “Appliance” names the install/operate concept and command
surface; **OMP NInfer** names this integration and repository.

## Release integrity

The release manifest is the authority for component identity. A release is ready only when:

```sh
python3 scripts/verify_release.py --require-ready
python3 -m unittest discover -s tests -v
```

Both commands pass on the tagged release. The ready manifest binds the accepted Windows archive,
compatibility authority, NInfer image/SBOM, model, qualification summary, and owner-operated
tester-equivalent acceptance receipt. Published product tags and release notes must use those exact
bytes.

## Feedback

Use the hardware-report or installation-failure issue forms. Remove API keys, hostnames, usernames,
private prompts, model outputs, and raw request logs before attaching anything. The support boundary
assumes a single trusted owner on both machines; this beta is not a multi-tenant service.

OMP NInfer is a community project; it is not affiliated with or endorsed by Oh My Pi, Qwen, or
NVIDIA.

## License

MIT. NInfer and the Qwen artifact retain their own licenses and notices.
