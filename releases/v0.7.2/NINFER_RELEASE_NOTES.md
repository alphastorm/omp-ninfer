# OMP NInfer v0.7.2 — bounded checkpoint-backed restore reclaim

**Owner-operated, exact-profile 0.x release; no SLA.** RTX 5090 uses the manual Docker/SSH
route; RTX 4090 and RTX 3090 use separate native Windows packages. Both changed mainline
components passed runtime qualification and exact-component documented-route acceptance.

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Quickstart](../../docs/QUICKSTART.md) · [Security model](../../docs/SECURITY.md) ·
[Acceptance](acceptance/composed-external-installation.json) · [Limitations](#release-and-support-boundaries)

## What changes

A restore previously needed enough free host-KV capacity on top of every resident session. This
runtime can save a resident session whose checkpoint is behind, reclaim only sessions it can
reproduce from current checkpoints, and retry import with a fresh reader. Restore still needs a
pool large enough for the target session; reclaim is not unlimited capacity or a promise that
every checkpoint succeeds.

The final reviewed source bounds retries under sustained republishing to at most 17 import
attempts and 16 reclaims. Regression evidence also covers refusing ResponseStore restore on
capacity exhaustion before commit while preserving unrelated sessions. Both regressions fail
on the immediate parent. These are the final reviewed fixes, not only the earlier experiment
that first demonstrated reclaim.

## Exact components

Both changed components target source `d125ffffd87ef38d9a221f9830e19dfa274ddd34`.

- RTX 5090 container **`v0.6.7-qwen38-5090-beta.1`** (component-published): image
  `sha256:74667e7334e51bb8d5eca99c6ae5994fef8b9e727885c89eef0812cd2bb15c24`; server
  `83547bc6118478a0813b4259605709645584cbf2fae816ee1a474ede11c004f0`.
- RTX 4090 native **`v0.6.5-qwen38-4090-beta.1`**: package
  `b26643d735d58eafac33f1595c0588baf0e6682a69af73e8e82f96839f4b7646`; server
  `e121084557c342398fb57411c088238d5745d0d5bcfc6bea6084786473fe506f`.
- RTX 3090 native `v0.2.5-qwen38-3090-beta.1` and OMP client
  `omp-18.0.9-cross-platform-beta-2` — unchanged. The later OMP client cut is not part of this release.
- Model artifact `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e` — unchanged.

## Final reviewed candidate evidence

The source-linked [EXP-047 receipt](../../docs/measurements/2026-09-17-restore-reclaim.json),
specifically `final_reviewed_candidate`, records the final d125 bytes. Its older findings remain
historical evidence for predecessor candidates, not qualification of the final binaries.

- **RTX 5090: both target 126K-token sessions resumed.** The sessions had 125,891 / 125,892
  input tokens; continuations reused 125,906 / 125,907 cached tokens. Resume wall times were
  **5.96 s and 23.57 s**. Profile, 57K/67K fanout, warm-arrival, restore, multisession and
  durability probes all exited 0.
- **The combined process was not a globally loss-free shutdown.** It contained predecessor
  sessions; shutdown reported `saved 2`, `refused 3`, with three unsaved live sessions. Automatic
  checkpoint counts were saved 13, refused 3. The evidence proves restoration of the two target
  sessions, not successful shutdown persistence of every session in that process.
- **Zero exit status is not universal warm reuse.** The extra multisession control recorded
  root fallback on 2 of 8 continuations/forks without server errors
  ([lane receipt](qualification/rtx5090.json)). Automatic checkpointing remains best effort
  under traffic; no zero-refusal or zero-fallback guarantee is made.
- **RTX 4090: the exact final native package passed 15 qualification phases**, including exact
  130,048-token retrieval. Recorded decode was **153.431 tok/s**, prefill **2,113.995 tok/s** on
  its qualification fixture. These are runtime-lane results, not published-route acceptance
  or a reclaim-driven throughput improvement.

## Public serving configuration stays unchanged

- RTX 5090 deployment profile **`qwen38-5090-v0.7.0`**, configuration
  `762e6bf448b389cd6a8d08871a3df2c74080c5b1fbd7bbb95146030f1990eea8`: 16384 MiB host KV,
  24 host-state slots, BF16 KV, MTP3, and a 28672 MiB runtime-host memory floor. The remaining
  serving knobs, transport and checkpoint-store settings do not change.
- RTX 4090 native: **11264 MiB host KV, 24 host-state slots, 32768 MiB runtime-host memory
  floor**, with the existing INT8 KV, MTP3 and serving settings.
- Qualification scratch profiles remain separate. Earlier 6144 MiB native-pool experiments
  did not qualify a smaller host or establish equivalent automatic durability, and are not a
  supported-default change. No host floor is reduced.

## Release and support boundaries

The documented commands target v0.7.2 and retain `--require-ready`. The RTX 5090 host
(2 blocks), macOS client (10), Windows client (5), and RTX 4090 native route (7) passed against
the published components. Pre-cut clone substitutions and SSH host parameterization are
recorded in the receipts. Both host windows restored their incumbent state. Unchanged client
platform receipts and the RTX 3090 lane are carried, not presented as fresh runs. Do not mix
a predecessor manifest with these commands.

Unchanged: prerelease support only with no SLA; one owner-operated machine per lane; one active
request per qualified profile; no multi-GPU, multi-tenant, priority, or preemptive scheduling
claim; no universal durability, warm-reuse, throughput, latency, or hardware claim; no silent
cloud fallback. Measurements apply only to the recorded bytes, machine and configuration.
