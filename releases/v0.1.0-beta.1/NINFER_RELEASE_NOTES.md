# NInfer `v0.1.0-qwen38-5090` release notes

These notes are prepared for the RTX 5090 component release used by OMP NInfer
`v0.1.0-beta.1`. Publish them only with the exact tag and immutable OCI/SBOM identities recorded in
the ready product manifest.

## Exact source

| Field | Value |
| --- | --- |
| Repository | `alphastorm/ninfer` |
| Tag | `v0.1.0-qwen38-5090` |
| Release source | `da2b6b6c8e129d182370feee657b7d8b9b9bbbf5` |
| Upstream base | `4eef14a7560d87a3ba717898e1d488a4c4c7246d` |
| Deterministic source archive SHA-256 | `31eda87bf64caf7152b71d8cfe976b30661c02347decef9935437cc76af464bd` |
| `ninfer-serve` SHA-256 | `af557e9b146c68b051bd29e9e7a7d172e908f4b12df4e6d3bd83c54ce58b2399` |
| Model SHA-256 | `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e` |
| Model bytes | `18,210,531,328` |
| Canonical config SHA-256 | `c6b635ccab19fd712ba503cd051b5359bb9c355068706b17372860baa0de49b6` |
| Deployment profile | `qwen38-5090-v0.1.0` |

The OCI reference, OCI manifest digest, SBOM URL/hash, and product qualification URL/hash come only
from the ready
[`manifest.json`](manifest.json). A mutable image tag or a locally retained pre-remediation archive
is not a release asset.

## Qualified profile

- NVIDIA GeForce RTX 5090, `sm_120a`;
- Qwen3.8 27B groupwise-int NInfer artifact;
- public model ID `q38-ninfer`;
- BF16 KV, 131,072-token context ceiling, `--kv-capacity auto`;
- one active request and 1,024-token prefill chunks;
- MTP with three draft tokens and optimized draft LM head;
- Vision and thinking preservation enabled;
- loopback HTTP with bearer authentication; and
- container restart policy `no`.

The preserved behavioral qualification at source
`70868c658f5bd412ead5b105ec76939997bd6ca9` passed exact 130,048-token retrieval,
OpenAI/Anthropic/Responses behavior, image input, stateful continuation/forks/delete behavior, cache
reuse, Golden t01, 209.04 decode tokens/second, 0.76975 MTP acceptance, explicit re-promotion, and
exact incumbent restoration. The later release-source proof at `da2b6b6…` closed build-provenance
identity and re-established exact source/binary/model/config health; it did not repeat or silently
rebind the benchmark.

Public composition and limitations:
[`qualification.json`](qualification.json).

## Non-claims

- Results apply to one recorded RTX 5090 and exact profile, not every 5090 or deployment.
- No automatic container restart was observed or claimed.
- Explicit NInfer lifecycle restoration is not OMP appliance-level rollback.
- NInfer process-restart continuation is not part of this component release.
- RTX 4090 uses a separate runtime/release lane and is not qualified by this tag.
- Publication, installation, route promotion, and product readiness are controlled by the OMP NInfer
  manifest rather than this component tag alone.

## Historical assets

The older qualification record contains a pre-remediation image ID, server hash, local tarball, and
SBOM identity. Retain those values as behavioral-evidence provenance only. Do not upload, rename, or
attach those bytes to this release tag.
