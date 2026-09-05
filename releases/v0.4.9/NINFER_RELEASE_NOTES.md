# OMP NInfer v0.4.9 - native-lane checkpoint restore fixed at source

One runtime change, applied to both native Windows lanes and requalified on each lane's own
rig on 2026-09-05: the checkpoint restore path. The RTX 5090 lane, its deployment profile
(`qwen38-5090-v0.4.8`), and the OMP client component are unchanged and rebound.

## What changed

- **Restore path on the native lanes** ([ninfer#36](https://github.com/alphastorm/ninfer/issues/36),
  EXP-017 in `docs/PERFORMANCE.md`). The reader issued one `read_file` per KV page segment, and
  on Windows each became its own single-request DirectStorage submit plus a fence wait; with
  `rk2v4-e8` pages that fixed per-request cost pinned restores near 8.5 MB/s on an NVMe that
  reads the same files at 2.2 GiB/s. The engine now plans one read per staging window
  (`plan_continuation_checkpoint_reads`) and scatters each window to the device with
  asynchronous copies and one synchronization; the store's Windows adapter submits a reader call
  as one bounded batch (`split_continuation_checkpoint_read`). On-disk checkpoint format,
  profiles, and configurations are unchanged. Restore probe on the same sessions as EXP-014,
  shipped binary versus candidate: RTX 4090 (57,889-token template, 1.13 GB) 146.6 s / 133.4 s
  -> 5.6 s / 5.6 s; RTX 3090 (38,251-token template, 1.68 GB) 91.8 s / 92.2 s -> 10.8 s / 10.7 s;
  planted ledger keys quoted exactly after every restart on both lanes.
- **RTX 4090 durable v0.2.2** (`v0.2.2-qwen38-4090-durable.1`, qualified head `9834bf58`,
  packaging `e16fa354`): the fix on the unchanged rk2v4-e8 KV, MTP3, prefill-chunk-2,048,
  131,072-context profile. Protocol 15/15, the 102,060-token session in 68.1 s, persistence
  restoring 102,075 tokens after a process restart with the post-restart continuation in
  9.5 s (225.6 s on v0.2.1), and the OMP Golden-equivalent run all passed.
- **RTX 3090 durable v0.2.4-beta.1** (`v0.2.4-qwen38-3090-beta.1`, commit `cd06e782`): the fix
  on the unchanged INT8 KV, MTP3, prefill-chunk-1,024, 131,072-context stack. The 14-phase
  orchestrator passed with exact 130,048-token retrieval in 219 s, 310 MB durable restart with
  exact recall, 90.6 tok/s decode at 93.4% MTP acceptance under the 300 W envelope (22,548 MiB
  peak), rollback, security, and OMP gates.
- RTX 5090 runtime component unchanged (`v0.4.5-qwen38-5090-beta.1`, profile
  `qwen38-5090-v0.4.8`, rebound); its restore reader is a different implementation and is not
  affected.
- OMP client component unchanged (omp-18.0.9-cross-platform-beta-2, rebound).

## Evidence route

Lane receipts in `qualification/`; the restore probe receipts for shipped and candidate
binaries are in `docs/measurements/2026-09-05-restore-probe-rtx{4090,3090}-*.json`. The
composed external-installation acceptance reruns against the published component URLs before
the cut.

## Support boundary

Unchanged: one owner-operated machine per lane; one active request per qualified profile;
loopback-only, bearer-authenticated, fail-closed. Community project; not affiliated with or
endorsed by Oh My Pi, Qwen, or NVIDIA.
