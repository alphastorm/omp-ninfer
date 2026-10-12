# OMP NInfer v0.12.1 — Stock OMP 18.10.1 with unchanged GPU lanes

**Owner-operated, exact-profile 0.x release; no SLA.** This patch pins unmodified
upstream OMP **18.10.1** in place of 18.8.7. The RTX 5090 container and native
Windows RTX 3090/RTX 4090 component bytes, models, serving limits and profiles are
unchanged from v0.12.0. The native lanes remain UUID-bound on one two-GPU Windows
host; only one runs at a time on authenticated loopback port 18082. RTX 4090 has
no supported rollback target there. This is not multi-GPU inference or concurrent
native serving.

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Quickstart](../../docs/QUICKSTART.md) · [Compatibility](COMPATIBILITY.md)

## What changed

- **Routine upstream client currency.** Stock OMP 18.10.1, source
  `5d0aaffaf1f987503ce129a642fb6e30339615af`, replaces the three 18.8.7 binaries.
  No client is built, patched or published by this repository.
- **No demonstrated NInfer fix from the OMP 18.9.0 Responses-stream change.** The
  [host-free applicability report](../../docs/measurements/2026-10-12-omp-18101-responses-compatibility-review.json)
  checked both released NInfer emitter source pins and loopback reproductions with
  stock 18.8.7 and 18.10.0. NInfer emits raw `reasoning_text` deltas with `summary: []`
  and full tool-argument snapshots, so neither lossy-summary nor empty-terminal-input
  trigger occurs. This is a specific non-applicability result, not a claim about
  every intervening OMP change or fresh 18.10.1 inference qualification.
- **Fresh client and route evidence stays separate from carried runtime proof.**
  Version/checksum/CLI preflight can run without an inference host. Live tool,
  continuation, unavailable-route behavior, documented routes and native public
  installs require their separately authorized windows. Product readiness is
  determined by the manifest and verifier, not by predecessor acceptance.

## Exact stock client identities

Upstream release `v18.10.1`, release ID `410230586`, source tree
`93ac9a4a82e57ca56fa31f393747e5a4117f9ceb`; each raw binary hash equals its
published asset digest.

| Platform | Asset | SHA-256 | Bytes |
| --- | --- | --- | ---: |
| macOS arm64 | `omp-darwin-arm64` | `74d920b72e7af01dbe258b41bb0684da7e747af63628eee41e98b5e74e2f21ac` | 216,762,400 |
| Windows x64 | `omp-windows-x64.exe` | `2ab55ace7787cd9471282859b4eabfd5d0960868a3c6165cbc1b518a02d3a2fb` | 243,885,056 |
| Linux x64 | `omp-linux-x64` | `9798d22d518b23342b4cadf57672b276ef09e756c1832adc6571b04b26ad4f1b` | 275,634,144 |

The [client descriptor](qualification/client-components.json) binds the exact
upstream asset URLs and IDs. Per-model `compat.statefulResponses: true`, custom-host
auto image detail, fail-closed configuration, concurrency and compaction settings
are retained; `PI_OPENAI_STATEFUL` must be absent.

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

Runtime measurements and package qualifications are carried v0.12.0 evidence,
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
