# OMP NInfer v0.12.2 — Stock OMP 18.12.1 with unchanged GPU lanes

**Owner-operated, exact-profile 0.x release; no SLA.** This patch pins unmodified
upstream OMP **18.12.1** in place of 18.10.1. The RTX 5090 container and native
Windows RTX 3090/RTX 4090 component bytes, models, serving limits and profiles are
unchanged from v0.12.1. The native lanes remain UUID-bound on one two-GPU Windows
host; only one runs at a time on authenticated loopback port 18082. RTX 4090 has
no supported rollback target there. This is not multi-GPU inference or concurrent
native serving.

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Quickstart](../../docs/QUICKSTART.md) · [Compatibility](COMPATIBILITY.md)

## What changed

- **Stock OMP 18.12.1 replaces 18.10.1.** Source
  `291e055836c210f314af3f73f53244e8e9d09de8` replaces the three 18.10.1 binaries.
  No client is built, patched or published by this repository.
- **The native Windows client stops resolving `C:` against the wrong directory.**
  On Windows, 18.10.1's shell builtins resolved a drive-relative operand such as
  `C:` against the OMP process's start directory instead of the shell's working
  directory, so `cd /c/Temp/x && rm -rf C:` deleted the start directory
  ([#15511](https://github.com/can1357/oh-my-pi/issues/15511), fixed in 18.11.0 by
  [#15515](https://github.com/can1357/oh-my-pi/pull/15515)). Every v0.12.1 native
  Windows route installs that 18.10.1 binary.
- **`omp -p` no longer reports success for a failed run.** 18.10.1 exited 0 after
  length-stop recovery gave up ([#15732](https://github.com/can1357/oh-my-pi/pull/15732),
  fixed in 18.11.1) and after an uncompactable context overflow, with an earlier
  answer ([#15897](https://github.com/can1357/oh-my-pi/pull/15897), fixed in 18.11.3).
  The documented acceptance blocks decide by `omp -p` exit status.
- **Host-free review, not route acceptance.** The
  [client upgrade review](../../docs/measurements/2026-10-18-omp-18121-client-upgrade-review.json)
  records the fixes' inclusion and a loopback comparison of the stock macOS 18.10.1
  and 18.12.1 binaries under the documented fragment and fail-closed config: tool
  turn, image input, `--continue` and outage behaved identically, and requests
  differed only in user-agent and system prompt. The unavailable-endpoint error text
  changed; no check depends on it. Live tool, continuation, restart, outage and
  image-input behavior on real lanes still requires the authorized windows.

## Exact stock client identities

Upstream release `v18.12.1`, release ID `416123868`, source tree
`c9d897cc3f06d7cd80f7cacb5144c208efa70f62`; each raw binary hash equals its
published asset digest and the release's `SHA256SUMS.txt`.

| Platform | Asset | SHA-256 | Bytes |
| --- | --- | --- | ---: |
| macOS arm64 | `omp-darwin-arm64` | `fa41b27d434380e99b713e4f9ced0f73eb1fc0c409fdf23a57c119971d24bac5` | 195,462,176 |
| Windows x64 | `omp-windows-x64.exe` | `1ba0274b48e6d6d095727faf36ec55114f5a6ac05bde5b8714d1565b2b7477bb` | 222,742,016 |
| Linux x64 | `omp-linux-x64` | `16181401e616d7d895bae31fa97476f1513d4080807d60d3a1a04006191a1bb3` | 254,670,816 |

The [client descriptor](qualification/client-components.json) binds the exact
upstream asset URLs and IDs; the [Darwin preflight](qualification/client-preflight-darwin-arm64-18.12.1.json)
checks identity, version, help and argv in an isolated home. Per-model
`compat.statefulResponses: true`, custom-host auto image detail, fail-closed
configuration, concurrency and compaction settings are retained;
`PI_OPENAI_STATEFUL` must be absent.

## Unchanged runtime boundary

- RTX 5090: `v0.6.16-qwen38-5090-beta.1`, source `1302d639`, published image
  `6a02feba`, server `548fe239`, model `0634abb0`, profile `qwen38-5090-v0.11.0`
  and configuration `91a35670`. Windows 11 Docker Desktop/WSL2, local loopback or
  a manual macOS SSH tunnel; BF16 KV, DFlash2 draft window 7 and two device slots.
- RTX 3090: `v0.6.3-qwen38-3090-beta.1`, package SHA
  `74120de0e6b1037e3c994e21b299f5cf4b98d9a3afa4e137d1c2ce8b57bfc297`.
- RTX 4090: `v0.6.11-qwen38-4090-beta.1`, package SHA
  `526870444c71add22c3dff8beb0c767aab2cbbb98870ec060398e6b7243de3a2`.
- Both native components use source `cad1976764fded5fbe96930c36bed0570b3d3de7`
  and the unchanged native model SHA
  `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`.
  RTX 3090 retains its qualified two-direction rollback; RTX 4090 retains
  `not_applicable`, zero directions and no predecessor. v0.6.10 and earlier RTX 4090
  packages are unsupported on the two-GPU host.

Runtime measurements and package qualifications are carried v0.12.1 evidence,
not new performance measurements or proof of the changed client's behavior. Fresh
product acceptance requires the 5090 host/macOS/Windows routes in one window and
both native routes plus their public installs in sequential native windows.

## Support boundaries

Only documented exact profiles are supported. macOS remains preview; the Linux
client's live route is under WSL2, not a separately qualified native Linux OS.
No new GPU, native-lane vision, JSON-schema output, automatic container restart,
unattended RTX 3090 role, multi-tenancy, universal warm reuse, independent external-user
outcome or SLA is claimed. Checkpoints remain best effort. Publication is owner-only;
these notes do not authorize a host window, production upgrade, tag or release.
