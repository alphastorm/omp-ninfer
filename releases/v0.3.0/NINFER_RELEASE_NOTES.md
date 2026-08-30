# OMP NInfer v0.3.0 — first public release

Three qualified GPU lanes in one ready manifest, public install authority with no access gate,
and durable session checkpoints on both native Windows lanes.

## Support boundary

One owner-operated machine per lane; one active request per qualified profile; the latest
published release and its exact manifest/profile receive fixes. The route is loopback-only,
bearer-authenticated, and fail-closed — an unreachable GPU produces an error, never a silent
cloud answer. Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.

## Lanes

| Lane | Topology | Decode | Highlights |
| --- | --- | ---: | --- |
| RTX 5090 (primary) | Windows 11 + Docker Desktop WSL2, digest-pinned container | 240.30 tok/s | Freshly requalified on the identical published bytes; 2,199.41 tok/s prefill at 130,048 tokens, exact retrieval; qualification-bound warm follow-up 0.191 s vs 36.651 s cold at an 89,022-token session |
| RTX 4090 (native) | Windows 11 x64, transactional package | 52.330 tok/s | 102,075-token restored continuation after process replacement; DirectStorage-backed durable checkpoints |
| RTX 3090 (native) | Windows 11 x64, transactional package | 90.17 tok/s | Promoted from the hash-bound parity campaign: 15/15 protocol, exact 64,512-token retrieval, durable restart, bidirectional rollback, 299.8 W observed peak at the 300 W cap |

Per-lane recovery semantics are explicit: the native Windows lanes restore sessions from disk
checkpoints across process restarts; the RTX 5090 container retains live-process warm continuation
and uses OMP transcript replay as its recovery path.

## Identities

The [manifest](manifest.json) is the authority: OMP 18.0.9 clients by checksum, NInfer image by
OCI digest with SPDX SBOM, model by SHA-256, native packages by SHA-256, and the
[qualification summary](qualification.json) binding every per-lane receipt. Verify a clone with
`python3 scripts/verify_release.py --require-ready`.

## Explicit non-claims

No stable/v1.0 support, SLAs, or upgrade commitments; no multi-GPU, multi-tenant, priority, or
preemptive scheduling; no structured JSON-schema output; the unattended RTX 3090 evidence role
stays disabled; no universal throughput, latency, or hardware claims — every number belongs to
its exact receipt.
