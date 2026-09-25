# OMP NInfer v0.8.1 — faster decode

**Owner-operated, exact-profile 0.x release; no SLA.** RTX 5090 uses the manual Docker/SSH
route; RTX 4090 uses the native Windows package. The client is the unmodified upstream Oh My Pi
v18.3.0 release binary, unchanged from v0.8.0. Both GPU components advance to runtimes with faster
MTP3 decode; the model artifact and every serving setting are unchanged. RTX 3090 is deferred.

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Quickstart](../../docs/QUICKSTART.md) · [Security model](../../docs/SECURITY.md) ·
[Known limitations](#support-boundaries)

## Faster decode

Each decode round drafts three tokens and verifies them in one pass over the model's weights.
Measured against the memory-bandwidth floor, that verify pass's small quantized projections ran
at 40-83% of the floor
([EXP-054](../../docs/measurements/2026-09-25-decode-roofline-attribution.json)): widening each
activation cost as much as the multiply it fed, and the Q4 MLP gate/up kernel stalled on
shared-memory bank conflicts. The runtime now has the Q4 and Q5 projections share each activation
load across weight rows, and pads the gate/up kernel's staged weight rows so its reads no
longer conflict. Every row keeps its arithmetic order, so outputs do not change.

On the RTX 5090, decode is 10.3-11.0% faster from a seed context to 31K tokens: a decode round at
a 26K-token context takes 16.08 ms instead of 17.75 ms. The changed kernels' outputs are
byte-identical to v0.8.0's at every measured extent, the 89-case role corpus answers identically
at temperature 0, and 130,048-token retrieval stays exact. On the published image, the lane's
2,048-token decode gate ran at 151.33 tok/s against 138.03 for v0.8.0.

On the RTX 4090 the same load sharing made the MLP down and mixer output projections 2-22% slower,
and a first candidate that used it decoded 2.7% slower than v0.8.0. The native lanes keep one
weight row per warp for those two projections; with that, the lane's C1 benchmark decodes at
157.89 tok/s against 153.54 for v0.8.0
([EXP-055](../../docs/measurements/2026-09-25-decode-kernel-schedules.json)).

## Two qualified GPU routes

- RTX 5090: `v0.6.10-qwen38-5090-beta.1`, image
  `sha256:5ca6e416bf896e73696e04b9324dc279e22104e0c325e0b4d1989d1a41df02e8`, server
  `5b2f24719625c4746443dc92a50a3c6152120196ef46056f14feb4cb035ccd15`, source
  `8cc0810acc296bac482187da171afddd93df7fb9`.
- RTX 4090: `v0.6.8-qwen38-4090-beta.1`, package
  `46aa411071901b0b080eafb64062baf78fa3f941e2451f91dc8d5b01e9aceab1`, server
  `32905865168182296cd8f3a6cfb4d053de95b6464f936b7165873a5f52684833`, source
  `5a774841c29bdf2ee6b7efba135aed0a47e80447`.
- Unchanged model artifact:
  `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`.

Every runtime gate was measured on the published bytes. On the RTX 5090, the image was pulled
anonymously by digest and passed the profile gates (130,048-token exact retrieval, decode, the
agent protocol across a restart), the EXP-050 durability workload - four saves before eviction, a
stop with `saved 1, nothing to save 3, refused 0`, all four stored sessions restored from their
checkpoints after a restart, and a second stop refusing nothing - EXP-051's publication barrier,
the fanout, warm-arrival, restore and multisession probes, and the agent mix, in which none of 24
fresh agent sessions fell back to a full prefill
([lane receipt](qualification/rtx5090.json)). The RTX 4090 package passed all 15 canonical native
phases, including 130,048-token retrieval, the managed-stop flush of an unpublished session,
rollback in both directions, protected state, and the OMP 18.3.0 tool call
([lane receipt](qualification/rtx4090.json)).

On both lanes, unmodified OMP 18.3.0 configured only by the documented fragment again kept one
session across graceful server restarts: one OMP process across a restart, a new process with the
server up, and a new process after a restart all recalled the seeded facts under one OMP session
id, and each lane restored the resuming process's first request from the session's checkpoint.

RTX 5090 retains deployment `qwen38-5090-v0.7.0`, configuration
`762e6bf448b389cd6a8d08871a3df2c74080c5b1fbd7bbb95146030f1990eea8`, 16384 MiB host KV,
and a 28672 MiB host floor. RTX 4090 retains 11264 MiB host KV, 24 slots, and a 32768 MiB floor;
its release identity and configuration hash advance with the lane version.

RTX 3090 is omitted from this release pending access to its physical qualification host. Its
[v0.7.2 instructions](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)
and OMP 18.0.9 client remain a separate historical route, not a v0.8.1 qualification claim.

## Upgrading from v0.8.0

Clone the v0.8.1 tag and follow the quickstart for your lane: RTX 5090 runs the new image digest,
and RTX 4090 installs the new package. The OMP binary, provider fragments and
`PI_OPENAI_STATEFUL=1` are unchanged. A session checkpoint is bound to the exact server build, so
checkpoints saved by v0.8.0 report `incompatible` and are not restored: OMP falls back to sending
the full conversation, each session re-prefills once, and the old checkpoints age out under the
checkpoint quota.

## Support boundaries

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
continuations/forks; universal warm reuse is not claimed. Decode speeds are single-request
measurements on the owner's RTX 5090 and RTX 4090; they apply only to these packages, machines
and profiles. Owner-operated exact profiles only; no SLA, multi-GPU, multi-tenant,
priority/preemption, or silent cloud fallback. Native Windows RTX 4090 is text/tools; vision
remains an RTX 5090 container capability. Do not mix a predecessor manifest with these commands.
