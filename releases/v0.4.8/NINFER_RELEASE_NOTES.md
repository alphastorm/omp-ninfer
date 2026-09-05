# OMP NInfer v0.4.8 - each lane on its own best measured configuration

Three configuration-only changes, one per lane, each requalified on its own rig on 2026-09-05
and accepted from the published URLs. No runtime source changed on the RTX 5090 lane; the two
native lanes rebuilt code-identical binaries under new patch-stack identities so that their
packaged configurations carry their own identity.

## What changed

- **RTX 5090 profile `qwen38-5090-v0.4.8`** (same `v0.4.5-qwen38-5090-beta.1` image, configuration
  `95765a38...`): `--max-private-continuations 8 --device-state-slots 4 --host-state-slots 24`.
  The shipped defaults (private catalog 2, device-state slots 2) evicted the shared base anchor
  once a stored sibling existed, so four sibling forks of a 57.9K-token template alternated
  1.3 s / 22.5 s; the new profile keeps all four on the anchor at 57,853 and 67,681 tokens
  (1.20-1.43 s each) for about 0.45 GiB of device memory. Measured through the lifecycle tool:
  exact 130,048-token retrieval at 2,207 tok/s cold, 136.03 tok/s decode at 41.20% MTP
  acceptance, the fork/delete/no-resurrection arc across a restart, a 4.5 GB explicit save and a
  verified restart. After a restart the first sibling fork of a restored template re-prefills
  once before its siblings run hot.
- **RTX 4090 durable v0.2.1** (`v0.2.1-qwen38-4090-durable.1`, commit `b9c4636b`): prefill chunk
  512 -> 2,048 on the unchanged rk2v4-e8 KV, MTP3, 131,072-context stack. Protocol 15/15, the
  102,060-token session in 68.0 s (84.9 s on v0.2.0), persistence restoring 102,075 tokens after a
  process restart, and the OMP Golden-equivalent run all passed.
- **RTX 3090 durable v0.2.3-beta.1** (`v0.2.3-qwen38-3090-beta.1`, commit `2ce6c9dc`): context
  ceiling 65,536 -> 131,072 on the unchanged INT8 KV, MTP3, prefill-chunk-1,024 stack. The
  14-phase orchestrator passed with exact 130,048-token retrieval in 218 s, 90.2 tok/s decode at
  93.4% MTP acceptance under the 300 W envelope (22,548 MiB peak), restart, rollback, security,
  and OMP gates.
- OMP client component unchanged (omp-18.0.9-cross-platform-beta-2, rebound).

## Evidence route

Lane receipts in `qualification/`; the composed external-installation acceptance in
`acceptance/` reruns the runtime-side steps (anonymous pull by digest, anonymous assets,
lifecycle launch identity, auth boundary, stateful resume, fail-closed delete) and adds
public-URL install acceptances on both native lanes. The fanout diagnosis behind the RTX 5090
profile is EXP-013 in `docs/PERFORMANCE.md`; two runtime follow-ups are filed upstream
(ninfer#35, ninfer#36).

## Support boundary

Unchanged: one owner-operated machine per lane; one active request per qualified profile;
loopback-only, bearer-authenticated, fail-closed. Community project; not affiliated with or
endorsed by Oh My Pi, Qwen, or NVIDIA.
