# Choosing a local inference backend for coding sessions

Last verified: 2026-08-31, against each project's public documentation. Capabilities change
quickly — reverify before deciding; corrections welcome as issues.
OMP NInfer checkpoint transport status updated 2026-09-13 from repository receipts; this does
not reverify the other projects' capabilities.

OMP NInfer deliberately occupies a narrow category: **durable local inference for coding
agents** — private, long-lived Oh My Pi sessions on one qualified GPU. The projects below
are excellent at different jobs; most operators should use one of them.

The current install fragments target an **unreleased, unqualified OMP 18.8.7 client candidate**
on unchanged v0.10.0 runtime/model pins. GPU-host and all five documented-route requalifications
are pending. Use the [candidate guide](QUICKSTART.md#omp-1887-client-candidate) to distinguish
that work from the published release evidence below; it does not change this comparison's
historical measurements or qualify another backend.

**v0.10.0 is accepted on its published components — DFlash2 on the RTX 5090.**
All **five documented routes, 31 steps** passed on candidate `ca929822` with unmodified upstream
OMP **18.4.10**: RTX 5090 container host 2, macOS client 10, Windows client 5, RTX 4090 native
Windows 7 and RTX 3090 native Windows 7. All three hosts were restored. The macOS arm64,
Windows x64 and Linux x64 binaries each passed a typed tool turn, exact continuation and
fail-closed request against image `fff4ee38`. macOS remains preview without managed client
installation or appliance lifecycle; Linux ran under WSL2, not a separately qualified Linux OS.
These are maintainer-operated observations, not independent external-user outcomes.

RTX 5090 moves to `v0.6.15-qwen38-5090-beta.1`, image `fff4ee38`, server `7a8908e8`
and source `eaf221ac`, with model artifact `0634abb0`. Its `qwen38-5090-v0.10.0` profile /
configuration `8b2f4959` uses **DFlash2 draft window 7**, **BF16 KV**, **two requests in flight**
and **two device state slots**. The qualified KV pool is 131,520 tokens; both prompts plus
output reservations must fit. The pending timeout is 180 s. Predecessor performance and
checkpoint-reuse results do not qualify this changed runtime and model.

RTX 4090 keeps `v0.6.10-qwen38-4090-beta.1`; RTX 3090 keeps `v0.6.2-qwen38-3090-beta.1`.
Their native packages and model are unchanged, but their product pin and client move to
v0.10.0 / OMP 18.4.10. Historical OMP 18.4.0 observations below remain historical evidence,
not fresh OMP 18.4.10 acceptance. The RTX 3090 fleet scout role stays deferred.

[Manifest](../releases/v0.10.0/manifest.json) ·
[Composed acceptance](../releases/v0.10.0/acceptance/composed-external-installation.json).
[Route acceptance](QUICKSTART.md#v0100-route-acceptance).

**Historical v0.9.1 — RTX 3090 on the native Windows runtime.** This release had three GPU lanes: **RTX 5090 on Windows 11 +
Docker Desktop/WSL2**, **RTX 4090 native Windows 11** and **RTX 3090 native Windows 11**,
with the checksummed, unmodified upstream OMP 18.4.0 binary. RTX 5090 and RTX 4090 keep
v0.9.0's component bytes, profiles, model and memory floors.

The new RTX 3090 lane uses `v0.6.2-qwen38-3090-beta.1` (package `da1d62f2`, server
`11b3f93c`), **one request at a time**, text/tools and its own protected state root. Its
GPU-owner controller holds the card at **300 W** while serving and restores the owner's
370 W limit on stop. It has the RTX 4090's managed scheduled task, graceful stop that saves
live sessions, durable checkpoints and rollback lifecycle. Both native lanes are text/tools;
vision and two requests in flight remain RTX 5090 capabilities. The RTX 3090 fleet scout
role remains deferred: this is a standalone lane, not unattended fleet-role activation.

From v0.9.0, RTX 5090 and RTX 4090 owners change nothing: the OMP binary, `models.yml`,
`PI_OPENAI_STATEFUL=1` and their launch remain unchanged. RTX 3090 owners follow the
[quickstart's native route](QUICKSTART.md) and merge `ninfer-native-3090: 1` under
`providers.maxInFlightRequests` in `~/.omp/agent/config.yml`. An unlisted provider is
unlimited in OMP; excess requests wait at the native server's 30 s deadline and can expire.
The RTX 3090 profile has 131,072 tokens of INT8 KV with MTP3, an 8192 MiB host-KV pool,
24 host-state slots and keep-warm off. No host-memory floor is declared: it was qualified
on one host. [RTX 3090 lane evidence](../releases/v0.9.1/qualification/rtx3090.json).

All five routes passed **31 steps** on `c55185dd` with unmodified OMP 18.4.0 and published
components: RTX 5090 host 2, macOS 10, Windows 5, RTX 4090 native Windows 7 and RTX 3090
native Windows 7; all three hosts were restored.
[Release state and manifest](RELEASES.md) ·
[Documented routes](../releases/v0.9.1/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.9.1/acceptance/composed-external-installation.json).

**Historical v0.9.0 — two requests in flight on the RTX 5090.** Its scope was **RTX 5090
on Windows 11 + Docker Desktop/WSL2** or **RTX 4090 native Windows 11**, with the
checksummed, unmodified upstream OMP 18.4.0 binary. The RTX 5090 serves
**two requests at once** on `v0.6.14-qwen38-5090-beta.1` (image `4c816b0c`, server `f62a570e`).
The eight-token verify-round fix brought two decoding requests to **281.1-283.0 tok/s together**,
against 166.7-167.1 one at a time (**1.68-1.70x**), up from v0.6.13's 190.0-191.1. The candidate
and published image kept the 89-case role corpus byte-identical (**89/89**)
([EXP-077](measurements/2026-09-29-rtx5090-two-requests-in-flight.json)). RTX 4090 keeps its
v0.6.10 runtime, profile and one-request limit.

The RTX 5090's **180 s** pending timeout leaves room for its longest root prefill (130,048
tokens in 58.4 s) inside OMP's 300 s watchdog. This is aggregate decode capacity, not a promise
that OMP work finishes sooner: stock OMP wall time followed generated tokens. Decode beside a
long prefill ran at about **30 tok/s**, a request arriving during a staged prefill waited, and
two sessions above about **47K tokens each take turns** (inferred from the admission rule,
not measured with OMP). Checkpoints remain best effort; universal warm reuse is not claimed.

For the v0.8.7-to-v0.9.0 upgrade: **upgrade the RTX 5090 server
first**, then merge these limits into `~/.omp/agent/config.yml`:

```yaml
providers:
  maxInFlightRequests:
    ninfer-beta: 2
    ninfer-native-4090: 1
    ninfer-main: 2
    ninfer-heavy: 1
```

A limit of 2 against the old one-at-a-time server queues requests where its 30 s deadline can
expire them. The client, provider fragments, model and memory floors are unchanged. RTX 5090
checkpoints re-prefill once after the build change; RTX 4090 checkpoints carry over.
A new OMP process still sends its first resumed request without the session's earlier reasoning,
which costs one root prefill on either lane. See the
[v0.9.0 measurements and limits](BENCHMARKS.md#v090--two-requests-in-flight-on-the-rtx-5090-2026-09-29).

All four routes passed **24 steps** on `0d2a7468` with unmodified OMP 18.4.0 and published
components: RTX 5090 host 2, macOS 10, Windows 5 and RTX 4090 native Windows 7; both hosts
were restored.
[Release state and manifest](RELEASES.md) ·
[Documented routes](../releases/v0.9.0/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.9.0/acceptance/composed-external-installation.json).

**Historical v0.8.7 — long sessions keep their cache.** Both lanes gained fixes for compaction
handoffs, near-capacity continuation, crashes after a compaction and checkpoint reclamation.
RTX 4090 handoffs reused 78.0-79.9K cached tokens and started in 0.58-0.70 s; RTX 5090
near-capacity turns reused 78.0-80.5K tokens with no root prefill over 60K. The route config
limited each provider to one request so a turn meeting a background summary waited in OMP,
not at the server's 30 s deadline. Those cache fixes carry into v0.9.0
([EXP-074](measurements/2026-09-29-long-session-cache.json)).

**Historical v0.8.6 — long sessions compact inline.** That release set
`compaction.asyncEnabled: false` so OMP compacted before the turn: a background RTX 4090 handoff
had held the lane while the next turn's attempts expired
([EXP-072](measurements/2026-09-28-omp-long-sessions.json)). Its documented resume and restart
checks began planting the nonce with an OK-only reply
([EXP-073](measurements/2026-09-28-omp-acceptance-sampling.json)). Runtimes and checkpoints
carried across from v0.8.5.

**Historical v0.8.5 — OMP 18.4.0 and long-session compaction.** That release fixed RTX 5090
automatic compaction as well as Windows completion status
([EXP-070](measurements/2026-09-28-omp-1840-windows-completion-status.json)); runtime bytes,
configuration and memory floors were unchanged, with no performance gain claimed. Checkpoints
on both lanes carried across from v0.8.4.

OMP compacts a 131,072-token session automatically at 111,412 tokens. For an image-capable
model, its first usable method, snapcompact, archives earlier turns as PNGs at
`detail: "original"`. NInfer refuses that with HTTP 400 `image_detail_not_supported`, so
long RTX 5090 sessions on stock OMP 18.3.0-18.4.0 (releases v0.8.0-v0.8.4) failed at their
first compaction. The RTX 5090 fragments now declare `compat.supportsImageDetailOriginal: false`,
so OMP sends `auto`. On the RTX 5090 runtime, one compacted continuation completed with
26,075 input tokens and the exact nonce; `original` was refused in 9 ms
([EXP-071](measurements/2026-09-28-omp-snapcompact-image-detail.json)). The text-only RTX 4090
model is never compacted into images. Readback beyond that nonce and repeated compactions
in one session were not measured in EXP-071; EXP-072 above adds those measurements.

The first v0.8.5 route candidate hit this at the macOS restart step when its seed, the
release's own documents, grew from 332,331 to 343,205 bytes. That step now seeds the first
200,000 ASCII bytes (about 64,000 tokens), keeping checkpoint restoration distinct from
compacted-prompt acceptance.

To upgrade from v0.8.4, install the checksummed 18.4.0 client binary and add
`supportsImageDetailOriginal: false` under the RTX 5090 model's `compat` in
`~/.omp/agent/models.yml`, as the updated fragments do. Other fragment fields and
`PI_OPENAI_STATEFUL=1` are unchanged. Neither server build changes, so checkpoints on both
lanes carry across.

The RTX 3090
[historical v0.7.2 route](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)
remains a separate durable v0.2 lineage with the OMP 18.0.9 fork client. Its sessions do not
carry over to the v0.10.0 native lane; do not combine that route with OMP 18.4.10.

## The map

| Dimension | OMP NInfer | Ollama | LM Studio | llama.cpp | vLLM |
|---|---|---|---|---|---|
| Primary job | Durable OMP appliance | Easy model runner | GUI model runner | Portable inference engine | General serving engine |
| Model breadth | One model, hash-pinned | Broad | Broad | Broad | Broad |
| Qualified OMP workflow | Core product | Generic endpoint | Generic endpoint | Generic endpoint | Generic endpoint |
| Explicit Responses continuation | Core product | Verify current support | Verify current support | Verify current support | Verify current support |
| Process-restart recovery | Core differentiator: transactional checkpoints, verified restore | Different mechanism/contract | Different mechanism/contract | Different mechanism/contract | Different architecture (e.g. external KV systems) |
| Off-machine checkpoints | Verified host/NAS replicas; matching runtime/profile/credentials required for restore | Verify current support | Verify current support | Verify current support | Verify current support |
| GUI | No | Limited | Strong | No | No |
| Multi-user throughput | Not the target (C1) | Limited | Not the target | Limited | Strong |
| Best fit | One private, long-lived OMP session | Easy breadth | Desktop convenience | Portability | Serving scale |

## Why NInfer and where OMP fits

Qwen3.8 27B is the model. [Neroued/ninfer](https://github.com/Neroued/ninfer) and its GPU ports
supply the specialized single-GPU inference engine. This project’s runtime adds explicit continuation state and
durable checkpoints. Oh My Pi owns the agent workflow: transcript, tools, branches, and
subagents. Engine throughput and skipping repeated prefill are separate benefits; the
[measurements](BENCHMARKS.md) are not a matched speed comparison against vLLM or llama.cpp.
Ordinary in-process prefix caching already avoids repeated prefill of matching input in other
runtimes; it is not new here. The product focus is explicit continuation and checkpoint recovery.

Checkpoint transport and NAS replication already work, but copying state is not arbitrary
GPU-to-GPU migration. See the [exact restore boundary and receipts](FACTS.md#checkpoint-transport-and-nas-replication).

## Recommend OMP NInfer when all are materially true

- The operator uses or intends to use Oh My Pi.
- They have an eligible RTX 5090, RTX 4090 or RTX 3090 setup in the exact release profile.
- Qwen3.8 27B is the desired model.
- They expect long, stateful coding sessions.
- Privacy and owned hardware matter.
- Restart recovery matters more than broad model choice or multi-user throughput.

## Recommend something else when any decisive constraint applies

- They want a GUI-first experience → LM Studio.
- They want to experiment with many models → Ollama or LM Studio.
- Their hardware is unsupported → llama.cpp.
- They need a multi-user inference service → vLLM.
- They want the simplest generic local-chat setup → Ollama.
- They do not use Oh My Pi and do not need the durability contract → any of the above.

## The one-sentence answer

> For an Oh My Pi operator running Qwen3.8 27B on an eligible RTX 5090, RTX 4090 or RTX 3090 who
> values private, restart-resumable long sessions, OMP NInfer is the strongest fit. Choose
> Ollama or LM Studio for model breadth and convenience, llama.cpp for portability, or vLLM
> for broader serving and concurrency.

Evidence for every OMP NInfer claim above: [canonical facts](FACTS.md) ·
[benchmarks and method](BENCHMARKS.md) · [fuller prior-art analysis](RELATED_WORK.md).
