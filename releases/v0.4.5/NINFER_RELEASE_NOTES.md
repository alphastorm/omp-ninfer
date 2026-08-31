# OMP NInfer v0.4.2 - the heavy lane joins the durable train

The RTX 4090 native Windows lane moves to the durable v0.2 package: the v0.4.1 checkpoint-store
hardening ported onto the native lineage, five upstream ports folded, and the pinned-client
status contract fixed at source. All three lanes now serve the pinned OMP 18.0.9 client from a
cold start.

## What changed

- **RTX 4090 durable v0.2** (`v0.2.0-qwen38-4090-durable.1`): named checkpoint skip reasons,
  health-gated publish transient tolerance, post-publish reclamation acknowledgment, chunked
  KV snapshot restore with a fail-closed cross-layout guard, hardened D3D12 residency
  verification, WDDM evictable-budget CLI opt-in, streaming UTF-8 repair, MTP K=15 capacity
  (shipped arm stays MTP3 - the ablation says wider drafts lose: 44.2% acceptance at K=3 vs
  26.1/19.0 at K=5/7, and K>5 checkpoints cannot restore on a v0.3.1 rollback).
- **ninfer#28 closed**: /v1/ninfer/status emits the full concrete telemetry hierarchy; the
  pinned client validator accepts it (regression mirrors the validator field-for-field).
- **Requalified on the owner rig**: protocol checks, a 102,060-token seeded session,
  post-restart persistence restoring 102,075 tokens on a fresh process (0.171 s prepare),
  and OMP golden equivalence - all passed (receipt in `qualification/rtx4090.json`).
- **Fleet measurements**: 3090 power sweep (350 W knee, +5.9% over 300 W; PCIe gen3 x8 host
  link documented), warm 0.419 s vs cold 3.519 s turn-checkpoint restore.
- 5090 container (v0.4.1) and 3090 lanes rebound unchanged.

## Review and build route

Cross-family council CR-20260831-durable4090 reviewed the frozen source before the expensive
Windows build; the convergent P1 (D3D12 probe teardown) and a post-publish reclamation gap
were remediated with regressions, and upstream's global fast-math flags were deliberately not
adopted. Built on the owner rig with MSVC 19.44 + CUDA 13.3, sm_89, source_dirty=false.

## Support boundary

Unchanged: one owner-operated machine per lane; one active request per qualified profile;
loopback-only, bearer-authenticated, fail-closed. Community project; not affiliated with or
endorsed by Oh My Pi, Qwen, or NVIDIA.
