# OMP NInfer v0.8.2 — GPU keep-warm

**Owner-operated, exact-profile 0.x release; no SLA.** RTX 5090 uses the manual Docker/SSH
route; RTX 4090 uses the native Windows package. The client is the unmodified upstream Oh My Pi
v18.3.0 release binary, unchanged from v0.8.1. The RTX 5090 runtime keeps the GPU at full clocks
for a minute after each request, so a new agent session that arrives after a pause starts as fast
as one that arrives back to back. The RTX 4090 package, the model artifact and the memory floors
are unchanged. RTX 3090 is deferred.

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Quickstart](../../docs/QUICKSTART.md) · [Security model](../../docs/SECURITY.md) ·
[Known limitations](#support-boundaries)

## GPU keep-warm

After its last work the RTX 5090 steps down its clocks within seconds - P3 after about 2 s, P5
after about 7 s and its lowest idle state, 270 MHz SM and 405 MHz memory, after about 9 s - and the
first prefill after that ran up to 2.3x slower while the clocks ramped
([EXP-060](../../docs/measurements/2026-09-26-idle-gpu-new-sessions.json)). In production's agent
traffic most new sessions arrive after such a pause: 103 of 106 new sessions came 5 s or more
after the previous request finished.

The v0.6.11 runtime adds `ninfer-serve --gpu-keep-warm-ms N`, off by default. After the server
has run work and gone idle, it launches a single-warp kernel that spins 3.5 ms of every 10 ms on
its own stream for N ms; the kernel reads and writes no memory, a launch is skipped while the
previous spin still runs, and the worker stops launching the moment a request is pending. The
driver steps down on time-based GPU utilization: a single-warp spin 30 ms of every 100 ms held the
top P-state where 25% fell to the lowest after 13.7 s
([EXP-061](../../docs/measurements/2026-09-26-keep-warm-load.json)), and 35% leaves a margin.
The RTX 5090 profile sets 60000.

Measured on production's arguments
([EXP-062](../../docs/measurements/2026-09-26-engine-keep-warm.json)): new sessions after 12, 25,
38, 53 and 58 s of idle prefilled in 0.155-0.157 s (time to first token 0.173-0.181 s), the same
as back to back, against 0.253-0.304 s (0.316-0.366 s) without the argument. The 89-case role
corpus answered byte-identically to v0.8.1 with it on and off, and requests that arrived 1-5 ms
after the previous one, while a spin could still run, changed time to first token by a median of
-0.1 ms (worst +4.4 ms). Holding the clocks draws 99.5-102.7 W against 29.3-29.8 W in the lowest
idle state, so about 71 W while it runs; replayed over 62 h of production's v0.7.0 request logs, a
60 s grace would have covered 84 of the 138 agent requests that arrived after 5 s or more of idle
(74 of 103 new sessions) at about 2.3 W on average. A 30 s grace would have covered 11 of them,
because those requests had waited a median of 52.7 s. After the grace ends the card again reaches
its lowest idle state within about 3 s, and a session that arrives later starts slow as before.

Every runtime gate was measured again on the published bytes. On the RTX 5090, the image was
pulled anonymously by digest and passed the profile gates (130,048-token exact retrieval in
56.4 s, decode at 160.07 tok/s, the agent protocol across a restart), the EXP-050 durability
workload - four saves before eviction, a stop with `saved 1, nothing to save 3, refused 0`, all
four stored sessions restored from their checkpoints after a restart, and a second stop refusing
nothing - EXP-051's publication barrier, the fanout, warm-arrival, restore and multisession probes,
and the agent mix, in which none of 24 fresh agent sessions fell back to a full prefill and their
median time to first token was 0.090-0.098 s ([lane receipt](qualification/rtx5090.json)). The
durability workload ran in a second window on the same image, because the first window lost the
resumed server's stop to a transport failure. The runtime's keep-warm device test fails on the
feature without its one-spin guard, where a second launch queued a second spin, and passes on the
release build. The unchanged RTX 4090 package carries its v0.8.1 lane receipt: all 15 canonical
native phases, including 130,048-token retrieval, the managed-stop flush of an unpublished
session, rollback in both directions, protected state, and the OMP 18.3.0 tool call
([lane receipt](qualification/rtx4090.json)).

On the RTX 5090, unmodified OMP 18.3.0 configured only by the documented fragment again kept one
session across graceful server restarts: one OMP process across a restart, a new process with the
server up, and a new process after a restart all recalled the seeded facts under one OMP session
id, and the lane restored the resuming process's first request from the session's checkpoint.

## Two qualified GPU routes

- RTX 5090: `v0.6.11-qwen38-5090-beta.1`, image
  `sha256:26813f5661e9bab7093349a216543d9391d310c08a207fee4d389d763dd36930`, server
  `0d7e042bca2956bbbe9bd68e8d1dcfaeea2666e326acdcea2d34d9b75d7c31d8`, source
  `32c21f73a7605f76480a6139de0488a14ed1aa48`.
- RTX 4090: `v0.6.8-qwen38-4090-beta.1`, package
  `46aa411071901b0b080eafb64062baf78fa3f941e2451f91dc8d5b01e9aceab1`, server
  `32905865168182296cd8f3a6cfb4d053de95b6464f936b7165873a5f52684833`, source
  `5a774841c29bdf2ee6b7efba135aed0a47e80447`, unchanged from v0.8.1.
- Unchanged model artifact:
  `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`.

RTX 5090 adds `--gpu-keep-warm-ms 60000` to its serving arguments, so its deployment profile
advances to `qwen38-5090-v0.8.2`, configuration
`56878aed92e8f3fb4101884fa889c98d1da75914573ebd167305ca0b4aa83e98`; host KV stays 16384 MiB and the
host floor 28672 MiB. RTX 4090 keeps its v0.8.1 identity, configuration, 11264 MiB host KV, 24
slots and 32768 MiB floor.

RTX 3090 is omitted from this release pending access to its physical qualification host. Its
[v0.7.2 instructions](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)
and OMP 18.0.9 client remain a separate historical route, not a v0.8.2 qualification claim.

## Upgrading from v0.8.1

Clone the v0.8.2 tag and follow the quickstart for your lane: RTX 5090 runs the new image digest
with the new profile, and RTX 4090 is unchanged. The OMP binary, provider fragments and
`PI_OPENAI_STATEFUL=1` are unchanged. A session checkpoint is bound to the exact server build, so
checkpoints saved by v0.8.1 report `incompatible` and are not restored: OMP falls back to sending
the full conversation, each session re-prefills once, and the old checkpoints age out under the
checkpoint quota. To run the v0.8.2 image without the keep-warm, omit the argument; the deployment
profile and configuration identity then no longer match this release's.

## Support boundaries

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
