# OMP NInfer v0.12.0 — draft, preparation only

This minor release prepares the return of native Windows RTX 3090 and RTX 4090 lanes on
one host with two NVIDIA GPUs. Each installed lane binds its own card by GPU UUID; the
RTX 4090 was at installation index 0 and the RTX 3090 at index 1. **Only one native lane
runs at a time**: both listen on loopback port 18082. This is not multi-GPU inference,
simultaneous native serving, multi-tenancy or an automatic lane switch.

Nothing here authorizes a component or product publication, a production upgrade, or
acceptance on a host. No v0.12.0 tag or public product release has been created.
The root compatibility authority, root profiles and documented install routes remain on
their existing pins until a separately authorized lane cut.

[Draft manifest](manifest.json) · [Draft qualification summary](qualification.json) ·
[Release compatibility](COMPATIBILITY.md) · [Current quickstart](../../docs/QUICKSTART.md) ·
[Security model](../../docs/SECURITY.md). The current quickstart is not a v0.12.0 install guide.

## Component scope

- **RTX 5090 is unchanged from v0.11.0:** NInfer `v0.6.16-qwen38-5090-beta.1`, source
  `1302d63929e400a05e1c9cdb0fc8003a70269825`, server `548fe239`, OCI image `6a02feba`,
  DFlash2 model `0634abb0` and deployment profile `qwen38-5090-v0.11.0` / configuration
  `91a35670`. The existing model, server arguments and two-request serving shape are retained.
- **Product client is unchanged stock OMP 18.8.7:** source
  `f261ed9faf16b61880b544f599876bface4ded0d`, with the same three upstream platform binaries.
  Passing the predecessor client descriptor deliberately retains these pins and clears product
  acceptance; predecessor-pin warnings are expected, not a request to select another client.
- **Native source is `cad1976764fded5fbe96930c36bed0570b3d3de7`:** lifecycle scripts record
  the selected UUID, GPU name, installation-time index and canonical PCI address. Start resolves
  that binding to the current device; GPU-owner queries and power changes are UUID-indexed.
  Hiding a card with `CUDA_VISIBLE_DEVICES` is unsupported.
- **Native model is restored byte-for-byte from v0.10.0:** revision
  `18dfc887423fa5aabf3cb56fac41490e462b3fab`, 18,210,531,328 bytes, SHA-256
  `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`.
  v0.11.0 removed `components.native_model` when it deferred both native lanes; preserving that
  absence would incorrectly bind the returned lanes to the RTX 5090's different model. Restoring
  the existing separate native-model contract does not alter the RTX 5090 model.

| Native lane | Prepared component | Package SHA-256 / bytes | Draft state |
| --- | --- | --- | --- |
| RTX 3090 | `v0.6.3-qwen38-3090-beta.1` | `74120de0e6b1037e3c994e21b299f5cf4b98d9a3afa4e137d1c2ce8b57bfc297` / 595,697,859 | Bound to the committed qualification; component publication and product acceptance pending |
| RTX 4090 | `v0.6.11-qwen38-4090-beta.1` | `526870444c71add22c3dff8beb0c767aab2cbbb98870ec060398e6b7243de3a2` / 574,770,447 | Unbound: first-release rollback contract refuses composition |

The owner still publishes both component prereleases. Prepared URLs do not establish that
those components are publicly available.

## Qualification and its boundary

The [RTX 3090 public receipt](qualification/rtx3090.json) is emitted by
`compose_native_qualification.py` from the completed orchestrator window, copied host evidence,
package build receipt and checksum set, installed `server_start` record and exact lane specs.
It records 130,048-token exact retrieval in 220.5 s, C1 decode at 102.4 tok/s, an explicit
42-token checkpoint and previously unpublished 45-token session surviving a graceful managed
restart, protocol at shipped/reduced host pools, protected state and rollback in both directions
against the retained v0.6.2-beta.1 package. UUID binding let that card run while the signed-in
desktop used the other GPU. This does not make old packages safe to install on an unprepared
multi-GPU host.

The qualification client was **OMP 18.0.9**, installed as
`18.0.9-hosted-windows-f4dcba581e4a`; the read-only installed-client record confirms that identity.
That typed-tool proof is distinct from pending product acceptance with stock OMP 18.8.7.
No previous product-route or platform-client acceptance is carried forward.

The RTX 4090 window completed its applicable phases, but its rollback receipt is
`status: not_applicable`, `directions: 0`, `reason: first release of the lineage`.
Before the separate first-release change, the composer refused it verbatim:

```text
error: phase rollback did not pass
```

No RTX 4090 public qualification receipt or manifest variant is fabricated or bound. The lane
has no rollback target on this two-GPU host: v0.6.10 and earlier RTX 4090 packages use
single-visible-GPU lifecycle operations and are unsupported there. The first-release
change permits only the explicit zero-direction `not_applicable` result,
never a passed rollback. After composing and binding that receipt, owner-authorized route
acceptance must use `--first-release`, exercise the fresh install/start/stop/tool/session and
fail-closed blocks without a predecessor, and restore the preserved original lineage/task/
ACLs/secrets/UUID power. No installed rollback target or bidirectional test is claimed.

## Host-script closure

Public native-install acceptance, native-route power probes/restoration and Windows VRAM
sampling use the active installed release's UUID. Legacy records without a UUID are allowed
only after enumeration proves there is exactly one GPU; multiple GPUs fail closed.
The shared helper travels with the native-route driver and is bound into its preflight hashes.
The sampler's two native campaign callers pass their state roots; the historical campaigns'
server launch ordinals are not a product acceptance or public install path.

`tests/test_windows_host_gpu.py` scans all Windows host PowerShell scripts and Python drivers,
including embedded PowerShell. Its invariant was **red before the fix** on five operations:
public-install power query, native-route power query, restoration power query and unindexed
power set, and VRAM memory query. It is **green after the fix**. The sole unindexed enumeration
exception is pinned to the legacy single-card resolver's exact query/function and can be used
only once. Shell samplers are explicitly outside this Windows invariant because they run in
the single-GPU RTX 5090 container/WSL lane.

## Remaining release gates

1. Owner publishes the exact prepared RTX 3090 and RTX 4090 components.
2. Decide the RTX 4090 first-release proposal, compose its honest not-applicable rollback
   receipt, commit the receipt, then bind the lane; do not invent a predecessor.
3. Separately authorize the lane pin and freeze the new candidate. Update the applicable
   v0.12.0 documented routes, without changing the unchanged RTX 5090 runtime or OMP client.
4. Accept every documented route fresh: RTX 5090 container host, macOS client, Windows client,
   RTX 3090 native and, after the decision/binding, RTX 4090 native. Collect separate native
   public-install and behavior/restoration evidence, plus all platform-client receipts.
   Exercise native lanes sequentially on their shared port.
5. Compose acceptance, then perform platform, acceptance and manifest pin stages, committing
   between stages. Finish with `verify_release.py --release v0.12.0 --require-ready --check-pins`.
6. Product publication remains owner-only. Date the changelog version only at an actual cut.

## Non-claims

Checkpointing remains best effort; the two short restart controls do not prove globally
loss-free shutdown. Numbers apply only to the measured package, machine and serving profile.
No smaller-host native profile, new vision support on native lanes, independent external-user
outcome, automatic restart, simultaneous native serving, universal warm reuse, SLA or performance
improvement is claimed. RTX 4090 rollback is unavailable on this topology until a real supported
predecessor exists; RTX 3090's two-direction result must not be transferred to it.
