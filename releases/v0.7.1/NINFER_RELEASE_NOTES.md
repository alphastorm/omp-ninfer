# OMP NInfer v0.7.1 - a reported save is a restorable save

The RTX 4090 native lane could report a successful checkpoint for a session at the context ceiling
and then fail to restore it. This release fixes that lane and makes the underlying bound visible
and enforced across the product.

## The defect

Restore materialises a continuation's KV into the host-KV pool, so that pool - not the device KV
arena - bounds the largest session a configuration can admit back. The RTX 4090 lane shipped
`context_cache.host_kv_mib` 4096: below the 5.02 GiB a 131,072-token session needs, and half the
engine's own 8192 MiB default.

Measured on the shipped component:

- one 125,888-token session: explicit checkpoint reported **4,834,325,255 B saved**, and after a
  graceful stop and restart the session answered **HTTP 404 `previous_response_not_found`**;
- two such sessions: all four continuations lost prefix reuse to ~90 s root re-prefills, one
  explicit checkpoint was refused with HTTP 409, automatic checkpoints were refused three times,
  the managed stop reported `saved 1 ... refused 1`, and **both** sessions answered 404 after the
  restart.

Earlier qualification passed because it restored small sessions (1.13 GB), never ceiling-sized ones.

## Exact components

- RTX 4090 native: **`v0.6.4-qwen38-4090-beta.1`** (new), source
  `736ac43a0a5d9eef17df60bcc417be566c9d8395`, package
  `05685402e647ece45810ad9f90c2c457ec1e3421cc0f72e0f0619825d810c088`, server
  `9f41e1e97eec4ccb1a866d07b52f6abb5818ffc1223be22ef8d09dde4461c51d`, configuration
  `cbebe3a6639143fcc8498ef0dba990d6763fb4a6f7a0adf6de4ba91384085096`.
- RTX 5090 container: `v0.6.5-qwen38-5090-beta.1`, image `5e3e1558`, deployment profile
  `qwen38-5090-v0.7.0` - unchanged from v0.7.0.
- RTX 3090 native and the pinned OMP client `omp-18.0.9-cross-platform-beta-2` - unchanged.
- Model artifact `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e` - unchanged.

## What changed

- **RTX 4090 host-KV pool 4096 to 11264 MiB.** Two sessions at the 131,072-token ceiling now keep
  prefix reuse (125,906 cached tokens in 1.97 s), both checkpoint (4.99 GB each), a graceful stop
  reports `saved 2, nothing to save 0, refused 0`, and both resume exactly after a restart in
  5.63 s and 7.78 s.
- **The lane declares what that pool needs.** `runtime_host.minimum_runtime_memory_mib` is 32,768:
  the pool is pinned memory, and on a 32.4 GiB host 11264 MiB pins with 11.6 GiB free while
  12288 MiB fails `cudaMallocHost`.
- **An export is refused when this configuration could not admit it back.** The restore admission
  check now runs at save time, so a too-small pool answers HTTP 409 with
  `checkpoint save refused: program refused continuation export` instead of writing a checkpoint
  that cannot be restored.
- **A refused restore names its gate**: `program refused continuation import (host KV pool capacity
  exhausted)` replaces `the engine did not accept the checkpointed continuation`.
- **The bound is disclosed at startup.** The capacity line carries
  `host-kv-restorable=<tokens>` and the request log carries `host_kv_restorable_tokens`.

## The RTX 5090 boundary this explains

`v0.7.0` recorded that with two sessions at the ceiling, one is declined at restore. The same
mechanism explains it: two BF16 ceiling sessions need about 18 GiB of pool and the lane ships 16
GiB. A 20 GiB pool restores both (5.75 s and 9.22 s) but pushes the container to 28.28 GiB of a
31.34 GiB utility VM, which would raise the runtime-host floor to roughly 40 GiB - so the lane keeps
its pool and now reports the boundary instead of implying it. Removing the bound means letting
restore stream KV without full pool residency, which is tracked and not in this release.

## Support boundaries

Unchanged: prerelease support only with no SLA; one owner-operated machine per lane; one active
request per qualified profile; no multi-GPU, multi-tenant, priority, or preemptive scheduling
claim; no universal throughput, latency, or hardware claim; no silent cloud fallback; measured
numbers apply only to the recorded package, machine, and profile.
