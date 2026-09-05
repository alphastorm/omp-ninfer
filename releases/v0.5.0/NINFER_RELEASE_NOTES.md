# OMP NInfer v0.5.0 - sessions leave the machine

The first v0.5 deliverable: a checkpointed session survives the machine that created it losing
its local state. Replication is a verified copy of published generations out to shared storage
and back before a restore; the security gate the roadmap named for it - manifest origin
authentication - now holds on all three lanes. The RTX 5090 runtime, its deployment profile
(`qwen38-5090-v0.4.8`), and the OMP client are unchanged and rebound.

## What changed

- **Origin-authenticated checkpoints on the native lanes**
  ([ninfer#32](https://github.com/alphastorm/ninfer/issues/32), ported from the RTX 5090
  container). Every save publishes `manifest.mac`, an HMAC-SHA256 over the exact manifest bytes
  keyed by material derived from the bearer key and held outside the checkpoint root; load and
  status verify origin before trusting manifest content. A present-but-wrong tag quarantines as
  tampering; a transient tag fault preserves `current` for retry; the default keeps the
  compatibility window for locally produced unMAC'd generations and
  `--session-checkpoint-require-origin-auth` (32-character bearer floor) is the strict,
  reversible import posture for roots that receive imports.
- **RTX 4090 durable v0.2.3** (`v0.2.3-qwen38-4090-durable.1`, qualified head `e186e04e`,
  packaging `ccdac145`): origin authentication on the unchanged rk2v4-e8 KV, MTP3,
  prefill-chunk-2,048, 131,072-context profile. Protocol 15/15, the 102,060-token session in
  68.0 s, persistence restoring 102,075 tokens with the post-restart continuation in 9.3 s, and
  the OMP Golden-equivalent run all passed; the qualification's own sessions carry `manifest.mac`.
- **RTX 3090 durable v0.2.5-beta.1** (`v0.2.5-qwen38-3090-beta.1`, commit `9719ea09`): origin
  authentication on the unchanged INT8 KV, MTP3, prefill-chunk-1,024, 131,072-context stack.
  The 14-phase orchestrator passed with exact 130,048-token retrieval, 310 MB durable restart
  with exact recall, 90.7 tok/s decode at 93.4% MTP acceptance under the 300 W envelope
  (300.15 W peak; the first benchmark sample peaked over the 301 W tolerance at the cap and the
  phase was rerun), rollback, security, and OMP gates.
- **`scripts/checkpoint_sync.py`** replicates only verified, published generations: each
  manifest-listed file by size and SHA-256, staged outside every directory the runtime scans,
  published with one rename, `current` last; unMAC'd generations refused unless
  `--allow-unauthenticated`. **`scripts/sync_probe.py`** proved the contract on every lane
  against the real store (EXP-018): checkpoint a session, export, carry the replica off the
  machine, stop the server, delete the session directory, carry the replica back, import,
  restart, and the continuation restores from the imported generation and quotes three planted
  ledger keys exactly - RTX 5090 4.5 GB import 10.1 s / restored 24.8 s, RTX 4090 1.13 GB
  4.2 s / 7.4 s, RTX 3090 1.69 GB 11.9 s / 11.5 s. A payload byte flip is refused by the tool
  before import; a coherent manifest edit passes the tool and is quarantined by the runtime at
  load (`checkpoint_corrupt` on the native lanes, `previous_response_not_found` on the
  container) - no resurrection.
- Portability stays same-profile-pair only: the runtime fingerprint binds binary and profile and
  the session namespace binds the bearer key, so a replica from another lane or key is not
  addressable.

## Evidence route

Lane receipts in `qualification/`; replication receipts in
`docs/measurements/2026-09-05-sync-probe-rtx{5090,4090,3090}.json`; the operator path is the
"Replicating sessions off the machine" section of `docs/QUICKSTART.md`. The composed
external-installation acceptance reruns against the published component URLs before the cut.

## Support boundary

Unchanged: one owner-operated machine per lane; one active request per qualified profile;
loopback-only, bearer-authenticated, fail-closed. Replication targets are storage, never a
checkpoint root. Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.
