# OMP NInfer v0.4.1 — durable checkpoints hardened

Correctness release on the RTX 5090 durable container lane. The checkpoint store's quota
transition is now health-gated and publish-safe; every refusal names its gate in the server
log. The RTX 4090 and RTX 3090 native Windows lanes are rebound unchanged.

## What changed

- **Publish transient tolerance (alphastorm/ninfer#27):** a session whose checkpoint exceeds
  half the disk quota can still save its successor. The superseded generation is tolerated as
  a publish transient and reclaimed under quota pressure - while reclamation stays healthy.
- **Post-publish acknowledgment (alphastorm/ninfer#30, council CR-20260831-v041delta):** once
  the current pointer durably swaps, cleanup trouble can no longer fail the acknowledged save.
  Reclamation is best effort after publish; while it keeps failing, the next save refuses
  fail-closed instead of letting usage creep past the cap.
- **Named skip reasons (alphastorm/ninfer#26):** every checkpoint refusal logs exactly one
  named gate (store disabled, no stored responses, quota exceeded, tag mismatch, ...) with the
  response id; HTTP bodies keep the released closed vocabulary. Replay-selected successor
  sessions retag correctly.

## Requalification (2026-08-31, owner appliance)

- Explicit 316.8 MB checkpoint -> `docker restart` -> warm continuation restored
  (`reuse=private_endpoint`, 1.52 s wall, codeword recalled verbatim).
- Fork x2 -> parent delete -> 404 before and after restart (no resurrection through the
  reworked reclamation layer); surviving descendant continues warm.
- Decode 134.8 tok/s at temperature 0 (2,048-token technical generation, completion-line
  bound); prefill curve inherited from the v0.4.0 receipt - the delta touches no kernel or
  prefill path (labeled in `qualification/rtx5090.json`).
- 9/9 release test suites green on the exact release source; council review with cross-family
  panel; the convergent P1 remediated and regression-pinned before publication.

## Build route

RunPod SECURE never allocated SSH across three attempts, so the release bytes were built in
the pinned `runpod/pytorch:1.1.0-cu1300-torch291-ubuntu2404` container on the owner appliance
(same GPU class as production). Identities are stamped and hash-bound end to end; the route
is documented in the component-release receipt.

## Support boundary

Unchanged from v0.4.0: one owner-operated machine per lane; one active request per qualified
profile; loopback-only, bearer-authenticated, fail-closed. Community project; not affiliated
with or endorsed by Oh My Pi, Qwen, or NVIDIA.
