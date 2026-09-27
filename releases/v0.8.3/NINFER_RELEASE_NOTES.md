# OMP NInfer v0.8.3 — faster RTX 5090 decode

**Owner-operated, exact-profile 0.x release; no SLA.** RTX 5090 uses the manual Docker/SSH
route; RTX 4090 uses the native Windows package. The client is the unmodified upstream Oh My Pi
v18.3.0 release binary, unchanged from v0.8.2. The RTX 5090 runtime runs part of each speculative
decoding round on the tensor cores, so decode at 1K-60K-token contexts is 3.6-6.3% faster; generated
text changes, and a
pre-registered redaction screen found the change not worse. The RTX 5090 serving arguments, the
RTX 4090 package, the model artifact and the memory floors are unchanged. RTX 3090 is deferred.

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Quickstart](../../docs/QUICKSTART.md) · [Security model](../../docs/SECURITY.md) ·
[Known limitations](#support-boundaries)

## Faster decode, different text

Every MTP3 decoding round verifies four tokens at once. In that verify pass, the four Q5
projections - GDN value/z, attention gate/value, mixer/attention output and MLP down - ran on SIMT
row kernels that no schedule keeping their output bytes could speed up. The v0.6.12 runtime runs
them on a small-T tensor-core MMA
([EXP-057](../../docs/measurements/2026-09-26-q5-small-t-tensor-core.json)):
- each CTA owns 16 output rows, and each of its warps owns one 64-value group of every K step;
- Q5 codes enter the MMA as exact bf16 integers;
- each group's fp16 scale is applied in fp32.

The route is compiled out for the RTX 4090 and RTX 3090 architectures.

Release build against release build, alternating A/B/B/A on the RTX 5090, the round was 4.2%
shorter at a 26K-token context and 3.5% shorter at 60K. Decode rose 4.4% and 3.6% there, where MTP
acceptance does not move, and 6.3% at 1,024 tokens. With no prompt the round was 4.9% shorter, but
the new build accepted fewer drafts on its own text (0.423 against 0.461), so decode moved -0.5%.

The accumulation order changes. In isolation, 27 of 118,784 projection outputs moved by one bf16
ulp, and the new outputs sit closer to an FP64 reference. That is enough to change generated text:
58 of the 89 role-corpus cases answer differently from v0.8.2. A single corpus run cannot tell such
a change from a worse model, so the change was screened before adoption
([EXP-063](../../docs/measurements/2026-09-27-powered-redaction-screen.json)). The rule, fixed and
committed before any candidate data, was that redaction behaviour must not get worse. Every
redaction control ran in 72 whitespace variants on fresh v0.8.2 and v0.8.3 servers, paired prompt
by prompt. Over 504 pairs the new runtime:
- leaked 561 synthetic secrets against v0.8.2's 582 (one-sided 95% upper bound of the ratio 1.012,
  against a 1.10 margin);
- passed 53.2% of prompts against 52.6% (lower bound of the difference -1.2 pp, against -5 pp).

Both servers reproduced their determinism prompts byte for byte.

Every runtime gate was measured again on the published bytes
([lane receipt](qualification/rtx5090.json)). On the RTX 5090, the image was pulled anonymously by
digest, and its role-corpus answers were byte-identical to the screened candidate's. It passed:
- the profile gates: 130,048-token exact retrieval in 58.7 s, decode at 168.07 tok/s, and the
  agent protocol across a restart;
- the EXP-050 durability workload: four saves before eviction, a stop with `saved 1, nothing to
  save 3, refused 0`, all four stored sessions restored after a restart, and a second stop
  refusing nothing;
- EXP-051's publication barrier, and the fanout, warm-arrival, restore and multisession probes;
- the agent mix: none of 24 fresh agent sessions fell back to a full prefill, and their median
  time to first token was 0.093-0.100 s.

The unchanged RTX 4090 package carries its v0.8.1 lane receipt
([lane receipt](qualification/rtx4090.json)).

On the RTX 5090, unmodified OMP 18.3.0 configured only by the documented fragment again kept one
session across graceful server restarts, and the lane restored the resuming process's first request
from the session's checkpoint.

## Two qualified GPU routes

- RTX 5090: `v0.6.12-qwen38-5090-beta.1`, image
  `sha256:cd9e10b115bbf38df011b201dfdd37ec3b56613da39b2f1701334c8157236b78`, server
  `3ab266e5cd82398be98c2baee6a41a123ce1a4b0d38bd9ddcda75044dcd5dcb1`, source
  `9d1ef7485d9c741c2830fa3d55218f3242cec5d7`.
- RTX 4090: `v0.6.8-qwen38-4090-beta.1`, package
  `46aa411071901b0b080eafb64062baf78fa3f941e2451f91dc8d5b01e9aceab1`, server
  `32905865168182296cd8f3a6cfb4d053de95b6464f936b7165873a5f52684833`, source
  `5a774841c29bdf2ee6b7efba135aed0a47e80447`, unchanged since v0.8.1.
- Unchanged model artifact:
  `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`.

RTX 5090 keeps v0.8.2's serving arguments, deployment profile `qwen38-5090-v0.8.2` and
configuration `56878aed92e8f3fb4101884fa889c98d1da75914573ebd167305ca0b4aa83e98`, including the
60 s GPU keep-warm. Host KV stays 16384 MiB and the host floor 28672 MiB. RTX 4090 keeps its v0.8.1
identity, configuration, 11264 MiB host KV, 24 slots and 32768 MiB floor.

RTX 3090 is omitted from this release pending access to its physical qualification host. Its
[v0.7.2 instructions](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)
and OMP 18.0.9 client remain a separate historical route, not a v0.8.3 qualification claim.

## Upgrading from v0.8.2

Clone the v0.8.3 tag and follow the quickstart for your lane. RTX 5090 runs the new image digest
with the same arguments and profile; RTX 4090 is unchanged. The OMP binary, provider fragments and
`PI_OPENAI_STATEFUL=1` are unchanged.

A session checkpoint is bound to the exact server build, so checkpoints saved by v0.8.2 report
`incompatible` and are not restored. OMP falls back to sending the full conversation, each session
re-prefills once, and the old checkpoints age out under the checkpoint quota. The same prompt can
produce different text than it did on v0.8.2.

## Support boundaries

The decode figures are single-request measurements on the owner's RTX 5090. The redaction screen
bounds the new runtime's behaviour on the corpus's seven redaction controls under prompt
variation. It does not add redaction tasks, and two of those controls leak in every sample on both
builds. The other primary role-corpus measures come from one run per build and stay within 2.0
points of v0.8.2.

The keep-warm costs board power only while held, and its benefit is measured on the owner's RTX
5090 under Windows driver 610.88 through WSL2 and Docker Desktop, whose idle P-state schedule it
answers; other drivers or GPUs may step down on a different schedule. The RTX 4090 lane does not
use it.

An RTX 4090 start could fail when the driver refused to pin the host-KV pool
([#48](https://github.com/alphastorm/omp-ninfer/issues/48)). Since v0.8.0 the server commits and
releases each pinned allocation's size plus 1/64 before pinning it, and every managed start in this
package's canonical qualification pinned the pool. The issue stays open until field confirmation,
and a refusal that still occurs reports the commit limit, available commit and available memory.

Automatic checkpointing remains best effort under live traffic: a crash or an expired graceful
wait can still leave unpublished work unsaved. Saving before eviction delays the admitting
request - about 6.5 s per 126K-token session on the RTX 5090 - and that request waits while a
victim's reply is still reaching its client, bounded by its own queue deadline. Ceiling-class
save-before-evict was exercised on the RTX 5090; the RTX 4090 lane runs the same serving runtime
through its own phases. The multisession control again recorded root fallback on 2 of 8
continuations/forks; universal warm reuse is not claimed. Prefill, decode and power figures are
single-request measurements on the owner's RTX 5090 and RTX 4090; they apply only to these
packages, machines and profiles. Owner-operated exact profiles only; no SLA, multi-GPU,
multi-tenant, priority/preemption, or silent cloud fallback. Native Windows RTX 4090 is
text/tools; vision remains an RTX 5090 container capability. Do not mix a predecessor manifest with
these commands.
