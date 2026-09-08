# OMP NInfer v0.5.1 - warm arrival across a restart

The second v0.5 deliverable on the RTX 5090: a checkpointed template arrives warm across a
restart. Every sibling fork of a restored template is served on the shared base anchor whether an
endpoint resume or a fork arrives first, and a 5 GB checkpoint restores in about 4 s instead of
24 s. The RTX 4090 and RTX 3090 components and the OMP client are byte-identical to v0.5.0 and
carry their receipts.

## What changed

- **RTX 5090 runtime `v0.5.1-qwen38-5090-beta.1`**
  ([component](https://github.com/alphastorm/ninfer/releases/tag/v0.5.1-qwen38-5090-beta.1),
  source `d956e6d6`, binary `71edc2f6`, runtime image `12ef2d9e...`), under deployment profile
  `qwen38-5090-v0.5.1` (configuration `efacac23...`), which keeps the `qwen38-5090-v0.4.8`
  context-cache arguments. Three context-cache fixes: a sibling fork inherits the long anchor it
  forks from, so checkpoints taken after a fanout carry it; consuming a session endpoint no longer
  double-charges a shared anchor against the entitlement (it returned HTTP 500 on any resume of an
  anchor-carrying session); and anchor replacement evicts the anchor whose loss costs the least
  re-prefill instead of the lowest frontier, which was the template boundary every sibling reuses
  (EXP-021, EXP-022).
- **Restore is no longer hash-bound** (EXP-023). Checkpoint payloads are hashed once, as the
  engine streams them, with the x86 SHA extensions when the CPU has them (2.66 GB/s against
  0.33 GB/s scalar), and the io_uring reads run eight deep overlapped with the hash. A 5.2 GB
  session restores in 3.8-4.4 s across two verified restarts (24.0 s on v0.4.8); a flipped payload
  byte is still refused (`previous_response_not_found`) and the generation quarantined.
- **Qualified from the published image** (EXP-024). The candidate was started through the
  lifecycle tool from `ghcr.io/alphastorm/ninfer-runtime@sha256:12ef2d9e...` with the manifest
  identities bound at preflight: exact 130,048-token retrieval at 2,180.30 tok/s (28,245 MiB),
  138.16 tok/s decode at 41.20% MTP acceptance, agent protocol with no resurrection across a
  restart, 4/4 sibling forks on the anchor path at 57,853 and 67,681 tokens in-process and 4/4
  again after a verified restart (resume 3.35 / 3.96 s, forks 1.25-1.41 s), warm arrival in both
  post-restart orders, explicit saves of 4.5 GB in 4.4 s.
- **Derived records rebound to the manifests.** Through v0.5.0 the compatibility authority's
  native variant rows still named the v0.2.2/v0.2.0 components with a 65,536-token RTX 3090
  ceiling, the profiles' `--binary-sha256`/`--config-sha256` launch arguments named the v0.4.3
  runtime, the qualification summary's runtime identity carried a stale upstream commit and
  source-archive hash, and the RTX 5090 receipt URLs pinned a commit that never contained them.
  The manifests were exact; the copies had drifted. Every derived record is now rebound from the
  manifest, `scripts/verify_release.py` refuses a ready release whose derived records disagree
  with it, and `--check-pins` requires every pinned evidence URL to serve its recorded bytes.

## Evidence route

Lane receipt in `qualification/rtx5090.json`; warm-arrival, restore, fanout, and profile-gate
receipts in `docs/measurements/2026-09-08-*.json`; the composed external-installation acceptance
in `acceptance/composed-external-installation.json` (anonymous pull by digest, lifecycle launch
bound to the manifest identities, anonymous status refused, identity re-read, one authenticated
completion; the native public-URL install acceptances carry by hash from v0.5.0). The RTX 4090
and RTX 3090 receipts are the v0.5.0 receipts for the unchanged components.

## Support boundary

Unchanged: one owner-operated machine per lane; one active request per qualified profile;
loopback-only, bearer-authenticated, fail-closed. Checkpoints from an older runtime fingerprint
replay once from the OMP transcript. Community project; not affiliated with or endorsed by
Oh My Pi, Qwen, or NVIDIA.
