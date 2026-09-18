# OMP NInfer v0.7.3 — OMP 18.2.3 client repin

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Quickstart](../../docs/QUICKSTART.md) · [Security model](../../docs/SECURITY.md)

## Client change

Native Windows x64, Linux x64, and macOS arm64 clients advance from OMP 18.0.9 to
`omp-18.2.3-cross-platform-beta-1`. All three use public source
`5ade242de59ac0f4606a1158bf564410c96918d4`, tree
`454d121cf221c1928de9503c71210cf015b048dc`. All seven public component assets were downloaded
anonymously and verified. Provider-free hosted qualification and live hardware acceptance are
recorded separately; neither is substituted for the other.

The source preserves the downstream NInfer request contract. Windows launcher/package portability
fixes and successful macOS qualification cleanup are included in the selected component evidence.
This release does not update a Homebrew cask or activate an installed client.

The authority uses OMP's existing `durable-checkpoint` capability. Its previous
`process-restart-continuation` spelling was rejected by the client's closed capability schema;
the product verifier now rejects unsupported capability names before installation.

## Two qualified GPU routes

- RTX 5090: unchanged `v0.6.7-qwen38-5090-beta.1`, image
  `sha256:74667e7334e51bb8d5eca99c6ae5994fef8b9e727885c89eef0812cd2bb15c24`.
- RTX 4090: unchanged `v0.6.5-qwen38-4090-beta.1`, package
  `b26643d735d58eafac33f1595c0588baf0e6682a69af73e8e82f96839f4b7646`.
- Unchanged model artifact:
  `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`.

RTX 3090 is deliberately omitted from this release pending access to its physical qualification
host. Its [v0.7.2 instructions](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)
and OMP 18.0.9 client remain a separate historical route, not a v0.7.3 qualification claim.

Focused review found the deferral incomplete: the fleet recipe still installed an RTX 3090
scout provider and agent, and the native-Windows fragment still declared an RTX 3090 provider.
Both are withdrawn here, together with the scout role map and its third SSH forward; the
three-lane form remains at the immutable v0.7.2 tag. The fleet's two-lane boundary is the same
EXP-016 receipt read for two lanes: 43.4 s cost-aware against 66.8 s on the RTX 5090 alone. The
24 accepted executable block bodies are unchanged by that edit, and release verification now
fails when any documented payload declares a lane this release does not bind.
[Dispositions](review/composition-ledger.json).

Runtime qualification is carried from [v0.7.2](../v0.7.2/qualification.json), not presented as
new performance evidence. RTX 5090 retains deployment `qwen38-5090-v0.7.0`, configuration
`762e6bf448b389cd6a8d08871a3df2c74080c5b1fbd7bbb95146030f1990eea8`, 16384 MiB host KV,
and a 28672 MiB host floor. RTX 4090 retains 11264 MiB host KV, 24 slots, and a 32768 MiB floor.

## Fresh client acceptance

All three client architectures passed authenticated local inference, a typed read/tool result,
the exact final marker, continuation, and fail-closed behavior against RTX 5090. macOS and native
Windows exercised vision; macOS also continued after the documented server restart. Linux live
inference ran under Ubuntu WSL2, not a newly qualified non-WSL Linux OS installation.

All four in-scope documented routes passed: container host (2 blocks), macOS client (10), Windows
client (5), and native RTX 4090 (7). All 24 executable block hashes survive the subsequent support
and prose edits unchanged. Pre-cut clone/SSH substitutions, Docker credential-helper isolation,
and native clean-install preparation are recorded in the
[route evidence](acceptance/documented-routes.json), not claimed as unmodified defaults.
The native RTX 4090 installation preserved an inactive package bound to another model path;
this is a fresh canonical-install qualification, not an idempotent-reinstall claim.

The RTX 5090 incumbent was restored healthy with its original image, restart policy, checkpoint
mount, checkout and key. RTX 4090 returned to its exact observed stopped predecessor state:
task Ready, no process/listener/lease, original state bytes, support files, task and ACLs, and
450 W power limit. Real client installations were not activated or replaced.

Client doctor blockers are retained in the platform receipts; these observations do not claim
successful automatic managed-appliance installation. All hardware observations were maintainer
operated, not independent external-user installations. Native RTX 4090's three unsupported-high
reasoning responses were followed by successful local compatibility retries, with no cloud fallback.

## Support boundaries

The v0.7.2 limitations stand: automatic checkpointing is best effort; the RTX 5090 combined
probe reported three unsaved predecessor sessions at shutdown, and the multisession control
recorded root fallback on 2 of 8 continuations/forks. No loss-free shutdown, universal warm reuse,
or new throughput claim is made. Owner-operated exact profiles only; no SLA, multi-GPU,
multi-tenant, priority/preemption, or silent cloud fallback. Native Windows RTX 4090 is text/tools;
vision remains an RTX 5090 container capability.
