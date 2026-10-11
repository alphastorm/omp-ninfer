# OMP NInfer v0.12.0 — Native RTX 3090 and RTX 4090 on one two-GPU Windows host

**Owner-operated, exact-profile 0.x release; no SLA.** Native Windows RTX 3090 and
RTX 4090 lanes return on one Windows host with both GPUs installed. Each lane binds
its own card by GPU UUID. **Only one native lane runs at a time**: both use authenticated
loopback port 18082. The RTX 4090 has no supported rollback target on this topology.
This is not multi-GPU inference, concurrent native serving or an automatic lane switch.

The RTX 5090 Windows 11 Docker Desktop/WSL2 runtime, its model and serving profile,
and unmodified upstream **OMP 18.8.7** are unchanged from v0.11.0. The container route
uses authenticated local loopback or a manual macOS SSH tunnel. All five documented
routes, three stock clients and both native public installs passed fresh acceptance.

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Quickstart](../../docs/QUICKSTART.md) · [Security model](../../docs/SECURITY.md) ·
[Known limitations](#support-boundaries)

## What changed

- **Native lanes return with explicit GPU ownership.** Lifecycle scripts resolve the
  installed release's UUID to the current device. GPU-owner, acceptance and VRAM
  queries and power changes address only that card. A legacy record without a UUID
  fails closed when more than one GPU is visible; hiding a card with
  `CUDA_VISIBLE_DEVICES` is unsupported.
- **The RTX 4090 starts a new supported lineage on this host.** Its rollback result is
  `not_applicable`, zero directions, `first release of the lineage`. v0.6.10 and earlier
  RTX 4090 packages use single-visible-GPU lifecycle operations and are unsupported
  here. Acceptance uses `--first-release`, not a fabricated predecessor or rollback pass.
  The RTX 3090 retains its actual two-direction qualification against v0.6.2-beta.1.
- **The separate native model binding returns.** v0.11.0 removed it when deferring
  both native lanes. Restoring v0.10.0's exact native artifact avoids binding these
  packages to the different RTX 5090 model; neither model is changed.
- **Fresh product proof, unchanged client.** Native qualification used OMP 18.0.9.
  Product acceptance separately exercised the pinned stock OMP 18.8.7 binaries;
  no previous product-route or platform-client proof is carried forward.

## Exact component identities

Both published native components use source
`cad1976764fded5fbe96930c36bed0570b3d3de7` and CUDA 13.3 lifecycle packages.

| Native lane | Component tag | Package SHA-256 / bytes |
| --- | --- | --- |
| RTX 3090 | `v0.6.3-qwen38-3090-beta.1` | `74120de0e6b1037e3c994e21b299f5cf4b98d9a3afa4e137d1c2ce8b57bfc297` / 595,697,859 |
| RTX 4090 | `v0.6.11-qwen38-4090-beta.1` | `526870444c71add22c3dff8beb0c767aab2cbbb98870ec060398e6b7243de3a2` / 574,770,447 |

The native model is the 18,210,531,328-byte artifact at revision
`18dfc887423fa5aabf3cb56fac41490e462b3fab`, SHA-256
`eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`.
The manifest binds each package, source archive, checksum set and build receipt.

The unchanged RTX 5090 component is `v0.6.16-qwen38-5090-beta.1`, source `1302d639`,
server `548fe239`, published image `6a02feba`, model `0634abb0` and deployment profile
`qwen38-5090-v0.11.0` / configuration `91a35670`. Stock OMP 18.8.7 remains pinned to
source `f261ed9faf16b61880b544f599876bface4ded0d` and the same three upstream binaries.
Full identities and serving limits are in the manifest and [compatibility matrix](COMPATIBILITY.md).

## Qualification and acceptance

The public [RTX 3090](qualification/rtx3090.json) and
[RTX 4090](qualification/rtx4090.json) receipts bind the measured packages and profiles.
These measurements are not a performance improvement claim or universal GPU figures.

| Native qualification workload | RTX 3090 | RTX 4090 |
| --- | ---: | ---: |
| Exact 130,048-token retrieval | 220.5 s | 91.0 s |
| C1 decode | 102.4 tok/s | 158.7 tok/s |

The RTX 3090's explicit 42-token checkpoint and previously unpublished 45-token
session survived a graceful managed restart. Checkpointing remains best effort;
these short controls do not prove globally loss-free shutdown. The RTX 4090's
no-target rollback result remains visible in both qualification and acceptance.

All five [documented routes](acceptance/documented-routes.json), **31 blocks** and
three stock OMP 18.8.7 clients passed on frozen candidate
`7713ceb956eee79f4c3e232ca020d385baff89be`. Native routes ran sequentially. Both
public URL installs passed with the verified model path derived from the active
installed release record. [Composed acceptance](acceptance/composed-external-installation.json)
binds the public-install receipts and behavior/restoration proof.

The native windows restored their measured state, pointers, release counts, tasks,
ACLs/secrets, holds and UUID-selected power. The RTX 5090 window restored its retained
incumbent image, mounts, health, key and checkout baseline in 389.939 s; production
was not upgraded. Platform, acceptance and manifest pins bind the final evidence
bytes without advancing the executable subject or changing any executed block.

## Support boundaries

- Only the documented exact profiles are qualified; no smaller-host native profile
  or unattended RTX 3090 role activation is claimed.
- RTX 4090 rollback is unavailable on this two-GPU host until a real supported
  predecessor exists. RTX 3090's two-direction result does not transfer to it.
- macOS remains preview. The Linux client ran under WSL2, not a separately qualified
  native Linux OS. Stock macOS/Windows image-input checks do not establish native-lane
  vision support, structured JSON-schema output or a new client feature.
- No automatic container restart, multi-tenancy, universal warm reuse, independent
  external-user outcome, support response-time guarantee or SLA is claimed.
- Acceptance restores the recorded baselines; it does not prove restoration of
  originally absent mutable directories. That successor correction remains separate
  and must not merge before this candidate is published.

The candidate is technically ready, not yet a published product. Only the owner may
tag/publish v0.12.0; normal install blocks require that ready product tag. No release
date is assigned here, and no product publication is authorized by these notes.
