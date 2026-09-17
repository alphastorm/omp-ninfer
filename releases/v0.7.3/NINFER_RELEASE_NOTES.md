# OMP NInfer v0.7.3 — OMP 18.2.3 client repin

**Candidate: live client and documented-route acceptance pending. Not a published product release.**

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Quickstart](../../docs/QUICKSTART.md) · [Security model](../../docs/SECURITY.md)

## Client change

Native Windows x64, Linux x64, and macOS arm64 clients advance from OMP 18.0.9 to
`omp-18.2.3-cross-platform-beta-1`. All three are built from public source
`5ade242de59ac0f4606a1158bf564410c96918d4`, tree
`454d121cf221c1928de9503c71210cf015b048dc`. The component archives and provider-free hosted
qualification receipts are published. Hosted qualification is not hardware acceptance.

The source preserves the downstream NInfer request contract. Windows launcher and package
portability fixes, and successful macOS qualification cleanup, are included in the selected
component evidence. This release does not update a Homebrew cask or activate an installed client.

## Unchanged runtimes

- RTX 5090: `v0.6.7-qwen38-5090-beta.1`, image
  `sha256:74667e7334e51bb8d5eca99c6ae5994fef8b9e727885c89eef0812cd2bb15c24`.
- RTX 4090: `v0.6.5-qwen38-4090-beta.1`, package
  `b26643d735d58eafac33f1595c0588baf0e6682a69af73e8e82f96839f4b7646`.
- RTX 3090: `v0.2.5-qwen38-3090-beta.1`, package
  `dbcd27c498d012d468f2eb757a34c085bacf597fa9ac0871ad61053dc72655e8`.
- Model artifact `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`.

Runtime qualification is carried from [v0.7.2](../v0.7.2/qualification.json), not presented as
new performance evidence. RTX 5090 keeps deployment `qwen38-5090-v0.7.0`, configuration
`762e6bf448b389cd6a8d08871a3df2c74080c5b1fbd7bbb95146030f1990eea8`, 16384 MiB host KV,
and a 28672 MiB host floor. RTX 4090 keeps 11264 MiB host KV, 24 slots, and a 32768 MiB floor.

## Acceptance and support boundaries

Before publication, the new client must pass authenticated inference on all three client platforms,
and all five documented lanes must run against the exact published components. The RTX 3090
route is included even though its runtime bytes are unchanged. Each window must restore its
observed predecessor state. Reader commands retain `--require-ready`; pre-cut substitutions are
recorded separately and are not a public installation instruction.

The v0.7.2 limitations stand: automatic checkpointing is best effort; the RTX 5090 combined
probe reported three unsaved predecessor sessions at shutdown, and the multisession control
recorded root fallback on 2 of 8 continuations/forks. No loss-free shutdown, universal warm reuse,
or new throughput claim is made. Owner-operated exact profiles only; no SLA, multi-GPU,
multi-tenant, priority/preemption, or silent cloud fallback. Native Windows GPU lanes are text/tools;
vision remains an RTX 5090 container capability.
