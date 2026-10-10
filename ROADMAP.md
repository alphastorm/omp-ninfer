# Roadmap

This roadmap is a scope boundary, not a promise of dates. The product wedge is OMP plus NInfer
plus Qwen3.8 on user-controlled RTX cards: qualified RTX 5090, RTX 4090 and RTX 3090 release
lanes, each bound to exact bytes and a receipt. The `v0.10.0` release accepts only those
exact profiles. Work outside that wedge needs a new product decision rather than
placeholder abstractions, and nothing below becomes part
of a release until its exact binary and profile are rebound through a new qualification receipt.

Want to move something here? The fastest ways to help are listed at the end of this page and in
[`CONTRIBUTING.md`](CONTRIBUTING.md); performance work has its own program page at
[`docs/PERFORMANCE.md`](docs/PERFORMANCE.md).

## Where this is now — RTX 5090-only v0.11.0 candidate, accepted routes

The [v0.11.0 candidate](releases/v0.11.0/NINFER_RELEASE_NOTES.md) binds published
NInfer v0.6.16/source 1302d639 (EXP-092/094 without 3a2fadbd) to stock OMP 18.8.7,
source f261ed9f. Full sm_120a ctest 111 pass/7 skip/0 fail and all 15 local criteria
passed; superseded a59/red NVFP4 proof remains preserved. The real image 6a02feba/
server 548fe239/model 0634abb0/profile qwen38-5090-v0.11.0/config 91a35670 and the
BF16/DFlash2 K7/two-device-slot serving shape are bound unchanged.

All three retained 5090 routes passed on 5861712f: host 2/2, macOS 10/10, Windows 5/5.
Three stock clients passed live/fail-closed proof; macOS stays preview and Linux
is an observed WSL2 binary, not a native Linux OS qualification. Measured downtime
was 385.948 s with independent incumbent restoration. Composition and immutable
platform→acceptance→manifest pins consume existing proof, preserving all 17 executed
block bytes. The tag/live product publisher is still founder-only; no production upgrade.

The founder chooses **RTX 5090 only** because the replacement native host now has
both 3090/4090, while unmodified packages require exactly one visible GPU. Native
installer name/UUID/ordinal binding and unindexed power queries cannot support
that arrangement. No environment shim. Both native lanes are deferred to a later
multi-GPU-qualified release; owners remain on the whole immutable v0.10.0 guide,
OMP 18.4.10 and its manifest/fragments. Old 65b6c4263090 proof is not retargeted.

Current 5090 fragments use per-model `compat.statefulResponses: true`, custom-host
auto image detail and upstream fail-closed resume; compaction settings are unchanged.
The earlier [18.8.7 client rehearsals](docs/QUICKSTART.md#local-rehearsal-not-acceptance)
remain separate evidence against v0.10.0, not substitutes for the accepted window.
[Declared deferral and current qualification](releases/v0.11.0/qualification.json).

## Published baseline — v0.10.0

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

[Manifest](releases/v0.10.0/manifest.json) · [Route acceptance](docs/QUICKSTART.md#v0100-route-acceptance).
[Composed acceptance](releases/v0.10.0/acceptance/composed-external-installation.json).

## Where this was — v0.9.1

Install through the [quickstart](docs/QUICKSTART.md); eligibility is one RTX 5090, RTX 4090
or RTX 3090. **v0.9.1 — RTX 3090 on the native Windows runtime** was accepted on 2026-10-01.

The RTX 3090 joins with `v0.6.2-qwen38-3090-beta.1` (package `da1d62f2`, server
`11b3f93c`), deployment profile `qwen38-3090-native-v0.6.2-beta.1` and configuration
`0f700667`. Source `f08309da` is the RTX 5090 v0.6.14 source `e20060b6`, whose parent
is the RTX 4090's `cba7eb93`, plus one controller fix, built for **sm_86**. It has the
RTX 4090's native lifecycle: a managed scheduled task, protected state root, graceful stop
that saves live sessions, durable session checkpoints and rollback to the previous release.

The lane serves **one request at a time**, with a **30 s** pending timeout, **131,072 tokens
of INT8 KV**, MTP3, an **8192 MiB** host-KV pool and **24 host-state slots**. Keep-warm is off;
no host-memory floor is declared because it was qualified on one host. The GPU-owner
controller holds the card at **300 W** while serving and restores the owner's **370 W** limit
on stop. Both native lanes are text/tools; vision remains an RTX 5090 container capability.

The RTX 5090 and RTX 4090 components, profiles, model and memory floors are byte-identical to
v0.9.0. The RTX 5090 stays on `v0.6.14-qwen38-5090-beta.1` (image `4c816b0c`, server
`f62a570e`, source `e20060b6`), profile `qwen38-5090-v0.9.0` and configuration
`cf1de114`, with two requests in flight. The RTX 4090 stays on
`v0.6.10-qwen38-4090-beta.1` (package `a0ea4c81`, server `e0498fad`, source
`cba7eb93`), configuration `7a69481f`, with one request at a time. Existing owners change
nothing: the unmodified OMP 18.4.0 binary, `models.yml`, `PI_OPENAI_STATEFUL=1` and their
launch are unchanged. The RTX 3090 serves the same model artifact, `eec39564…`.

The [RTX 3090 lane qualification](releases/v0.9.1/qualification/rtx3090.json) passed **all
15 lifecycle phases** on the physical card:

- **130,048-token retrieval was exact in 221.0 s** at the 131,072-token ceiling.
- C1 decode reached **102.64 tok/s** with **93.43% MTP acceptance**, peaking at **299.92 W**
  under the 300 W cap. This trajectory-sensitive fixture has no like-for-like predecessor
  on this lane's runtime; it is not a speed-up claim against the historical v0.7.2 route.
- A **104.5 s restart** restored a previously unpublished session saved by the managed stop.
- Rollback passed in both directions against the lane's **unpublished v0.6.0-beta.1** package;
  that predecessor stops by termination because it predates the stop-event channel.
- Protected state denied two low-privilege reads; the 15-check agent protocol passed at the
  shipped host pool and with 8 host-state slots; unmodified upstream OMP 18.4.0 passed its
  typed tool call.

Three fixes shipped with the lane:

1. **Rollback reads the release's own configuration.** The first qualification window at
   `e20060b6` failed rollback before launching its predecessor: the shared Windows controller
   read `context_cache.host_kv_mib` directly under PowerShell strict mode, but v0.6.0 predates
   that field. Source `f08309da` passes `--host-kv-mib` only when the release declares it,
   as it already did for `gpu_keep_warm_ms`. Lifecycle tests now require that treatment for
   every configuration field newer than the shipped lineage. Every published RTX 4090
   package declares the field, so the unchanged RTX 4090 lane was never exposed.
2. **OMP sends the RTX 3090 one request at a time.** Change `4c5ba8d` adds
   `ninfer-native-3090: 1` under `providers.maxInFlightRequests` in
   [the route configuration](examples/manual-tunnel/fail-closed.yml). Merge that entry into
   `~/.omp/agent/config.yml` when following the RTX 3090 native quickstart. OMP leaves an
   unlisted provider unlimited; a request beyond the lane's one waits at the server and
   expires after 30 s.
3. **Acceptance judges scheduled tasks by definition and enabled state.** The first RTX 5090
   window passed every route, client probe and restoration check, but its summary refused a
   task snapshot: the five-minute container-host supervisor was `Running` at baseline and
   `Ready` afterwards, with an unchanged definition. Change `0073553` makes
   [the acceptance summary](scripts/hosts/accept-rtx5090-routes.py) require byte-identical hold
   markers and each OMP task present, identically defined and as enabled as before. The
   collected evidence passed the corrected summary; a test covers both state directions.

All **five documented routes passed 31 steps** on candidate `c55185dd`
(`c55185dd39cbdb440620721c2a9d0dc06de010f4`) with unmodified OMP 18.4.0 and the published
components: RTX 5090 container host 2, macOS client 10, Windows client 5, RTX 4090 native
Windows 7 and RTX 3090 native Windows 7; all three hosts were restored. The upstream macOS
arm64 (preview), Windows x64 and Linux x64 binaries each passed a typed tool turn, an exact
continuation and a fail-closed request against image `4c816b0c`. Linux ran under **WSL2**,
not a separately qualified Linux OS; macOS remains preview, without a managed installation
or appliance lifecycle.
[Documented routes](releases/v0.9.1/acceptance/documented-routes.json) ·
[Composed acceptance](releases/v0.9.1/acceptance/composed-external-installation.json).

Both native routes installed from public assets. The RTX 3090 route performed a fresh
canonical upgrade installation of the published package, then passed typed-tool,
continuation and fail-closed checks, with prior state restored; this is not an idempotent
reinstall claim ([public install](releases/v0.9.1/acceptance/rtx3090-public-install.json)).
The RTX 3090 console was signed out: a managed start refuses while any process holds at
least 1 GiB of GPU memory, and the signed-in desktop's compositor alone held about 1,070 MiB.

The RTX 5090 routes ran in **two production windows** from the maintainer's Apple silicon
workstation over the tailnet. Downtime was at most **408.4 s (6.8 min)** and **386.5 s
(6.4 min)**. After the first window's task-snapshot summary refusal, a corrected window on
the same candidate passed in fresh workspaces
([restoration](docs/measurements/2026-10-01-v091-acceptance-restoration.json)).

The historical v0.7.2 RTX 3090 route remains separate: its durable v0.2 lineage and OMP
18.0.9 fork client are not this lane, and its sessions do not carry over. The standalone
native lane is accepted; the **fleet RTX 3090 scout role stays deferred**, and the
**upstream engine merge remains open**.
[Release notes](releases/v0.9.1/NINFER_RELEASE_NOTES.md) ·
[Manifest](releases/v0.9.1/manifest.json) · [Qualification](releases/v0.9.1/qualification.json).

## Where this was — v0.9.0

Install through the [quickstart](docs/QUICKSTART.md); eligibility remains one RTX 5090 or RTX 4090.

The RTX 5090 serves **two requests at once** with `v0.6.14-qwen38-5090-beta.1`
(image `4c816b0c`, server `f62a570e`), deployment profile `qwen38-5090-v0.9.0` and
configuration `cf1de114`. The eight-token MTP3 verify round now uses the Q5 tensor-core route
instead of SIMT kernels. Two decoding requests reached **281.1-283.0 tok/s together**, against
166.7-167.1 one at a time (**1.68-1.70x**), up from v0.6.13's 190.0-191.1 with two requests.
The candidate answered the role corpus byte-identically to v0.6.13, two cases at a time and one
at a time (**89/89**); the published image matched both the candidate and v0.6.13 (**89/89**)
([EXP-077](docs/measurements/2026-09-29-rtx5090-two-requests-in-flight.json)).

The profile adds `--max-concurrency 2 --pending-timeout-ms 180000`. A request that cannot fit
beside the running one can wait **180 s**: the wait plus the longest root prefill, **130,048
tokens in 58.4 s** on the published image, stays inside OMP's **300 s** stream-idle watchdog.
The server ends a too-long wait and OMP resends. KV capacity auto-resolves to **160,256 tokens**;
VRAM after load is **30,242-30,244 MiB** of 32,607 MiB, against 28,144 MiB with one request.
Keep-warm, 16384 MiB host KV, the 24 GiB checkpoint quota, BF16 KV, MTP3, 131,072-token context
and the 28672 MiB runtime-host floor are unchanged.

The config every documented route installs,
[`examples/manual-tunnel/fail-closed.yml`](examples/manual-tunnel/fail-closed.yml), sets the RTX 5090
providers to two requests in flight and keeps the RTX 4090 providers at one:

```yaml
providers:
  maxInFlightRequests:
    ninfer-beta: 2
    ninfer-native-4090: 1
    ninfer-main: 2
    ninfer-heavy: 1
```

**Upgrade the RTX 5090 server first**, then merge these limits into `~/.omp/agent/config.yml`,
including any other NInfer provider id you declare. A limit of 2 against the old one-at-a-time
server queues requests at its 30 s deadline, where they can expire. RTX 5090 checkpoints saved
by v0.8.7 re-prefill once after the build change. RTX 4090 stays on
`v0.6.10-qwen38-4090-beta.1` (package `a0ea4c81`, server `e0498fad`, configuration
`7a69481f`), one request at a time with a 30 s pending timeout; its checkpoints carry over.
The unmodified OMP 18.4.0 binary, `models.yml`, `PI_OPENAI_STATEFUL=1` and model are unchanged.

The [final-profile lane evidence](releases/v0.9.0/qualification/rtx5090.json) was collected on the
candidate image with the same server binary and arguments as the published image:

- Stock OMP durable sessions passed. EXP-072 long sessions at limit 2 had no root prefill over
  60K tokens; the third planting run stopped at the same harness precondition as v0.8.7.
- With 35 short sessions filling the 24 GiB store, a 60,026-token session reused **60,057 cached
  tokens after a crash in 2.99 s**.
- EXP-050's workload and resume restored **4/4 stored sessions** from checkpoints; stop saved 1
  and refused 0. EXP-051's held turn resumed exactly, but deferred save before eviction did not
  arise at two requests: the evicting session was admitted beside the held one.
- Fanout, warm-arrival, restore and multisession probes passed; **2 of 8** multisession
  continuations/forks lost reuse, as in v0.8.7. None of **24 fresh agent sessions** fell back to
  root, with median time to first token **0.092-0.100 s**.
- Restarting with two requests in flight ended both streams with `response.incomplete`; both
  continuations reused **62,404 cached tokens**, with first output in **5.07-5.53 s** and no
  refused shutdown saves.

On the published image, **130,048-token retrieval was exact in 58.4 s**, decode reached
**169.79 tok/s over 2,048 tokens**, the agent protocol passed across a restart, and VRAM after
load was **30,242 MiB**. Lane qualification and documented-route acceptance are separate evidence.

The costs remain visible: decode beside a 71,641-token prefill ran at **30.4-30.6 tok/s**, and a
request arriving during a staged prefill waited **26.6-26.7 s**. Two sessions above about **47K
tokens each take turns** (inferred from the admission rule; not measured with OMP). Two
alternating 62.4K-token sessions re-prefilled some continuations from root at both limits.
Stock OMP wall time followed generated tokens, with one run per limit per window: **no claim
that OMP work finishes sooner**. The robust gain is aggregate decode. Checkpoints remain best
effort; after the concurrency probe's evictions, stop refused 7 saves at two requests and 5
at one because the newest turns were no longer resident.

All four documented routes passed **24 steps** on candidate `0d2a7468`
(`0d2a746814aaddca328af7bf2582e48dbf6ce950`) with unmodified OMP 18.4.0 and the published
components: RTX 5090 container host 2, macOS client 10, Windows client 5 and RTX 4090 native
Windows 7; both hosts were restored. The upstream macOS arm64
(preview), Windows x64 and Linux x64 binaries each passed a typed tool turn, an exact
continuation and a fail-closed request against image `4c816b0c`. Linux ran under **WSL2**, not
a separately qualified Linux OS.
[Documented routes](releases/v0.9.0/acceptance/documented-routes.json) ·
[Composed acceptance](releases/v0.9.0/acceptance/composed-external-installation.json).

The RTX 5090 routes ran in **three production windows** from the maintainer's Apple silicon
workstation over the tailnet. Downtime was at most **101.5 s (1.7 min)** and **324.3 s
(5.4 min)** in the two failed windows and **499.3 s (8.3 min)** in the accepted window; total
downtime was at most **925.0 s (15.4 min)**
([restoration](docs/measurements/2026-09-30-v090-acceptance-restoration.json)).

Candidate `54f1402e` passed the RTX 4090 route, but its RTX 5090 window failed at the
container-host route's start step: the launcher still required the server to report one request
in flight, and the v0.9.0 profile serves two. The launcher now checks the concurrency, context
and KV type its profile declares. Production was back within 101.5 s, but the window's Windows
hold stayed up 10 min longer, because its WSL-side release went through an interop relay that
cannot start Windows processes; the host script now picks a live relay. Candidate `9eca7bae`
passed the RTX 4090 route and the container-host route, but in its RTX 5090 window the Linux
client sent no request in 210 s: OMP 18.4.0's print mode reads piped stdin to EOF before it
starts, and the window's drivers had forwarded a terminal that never closes. Every acceptance
client now reads an empty stdin. Candidate `0d2a7468` passed the RTX 4090 route and a third
RTX 5090 window.

RTX 3090 remains deferred. [Release notes](releases/v0.9.0/NINFER_RELEASE_NOTES.md) ·
[Manifest](releases/v0.9.0/manifest.json) · [Qualification](releases/v0.9.0/qualification.json).

## Where this was — v0.8.7

Install through the [quickstart](docs/QUICKSTART.md); eligibility remains one RTX 5090 or RTX 4090.

Long sessions no longer re-prefill from root at compaction handoffs, near-capacity turns, crashes
after a compaction, or when short sessions fill the checkpoint store. Both lanes move to runtimes
with the same fixes: RTX 5090 `v0.6.13-qwen38-5090-beta.1` (image `d71e34c3`, server `b8ae62ae`)
and RTX 4090 `v0.6.10-qwen38-4090-beta.1` (package `a0ea4c81`, server `e0498fad`). The config every
documented route installs, [`examples/manual-tunnel/fail-closed.yml`](examples/manual-tunnel/fail-closed.yml),
limits each NInfer provider to one request in flight and leaves compaction at OMP's default, so OMP
compacts in the background again and the turn that meets a running summary waits in OMP instead of
expiring at the server ([EXP-074](docs/measurements/2026-09-29-long-session-cache.json)):

- RTX 4090 compaction handoffs reused **78.0-79.9K cached tokens** and reached the first token in
  **0.58-0.70 s**; v0.6.9 prefilled 97.4-97.5K tokens from root in 63.8-66.3 s.
- Near-capacity turns whose planner search runs out of time keep their continuation. In three
  stock OMP sessions on the RTX 5090, the three fallback turns reused **78.0-80.5K cached tokens**
  (12.4-12.5 s to the first token) and **no turn prefilled more than 60K tokens from root**;
  v0.6.12 production's log holds four such turns of 93.7-105.1K tokens, each prefilled from root.
- After a hard kill following a compaction, the next RTX 4090 turn reused **32,167 cached tokens
  in 2.9 s**; v0.6.9 prefilled 32,173 tokens from root in 29.2 s.
- With 35 short sessions filling the RTX 5090's 24 GiB checkpoint store, a 60,026-token session
  kept its checkpoint and after a crash reused **60,057 cached tokens in 2.9 s** (3.1 s on the
  RTX 4090); v0.6.9 had reclaimed that checkpoint first and failed the turn with
  `previous_response_not_found`.
- With the provider limit, three RTX 4090 handoff compactions and a restart ran **55 requests with
  none expired**, and 22 turns took **365.4 s** where v0.8.6's inline compaction took 678.2 s for
  24. The limit must name the route's own provider id: OMP leaves an unlisted provider unlimited.

The kernels are unchanged. The RTX 5090 candidate and published image answered the 89-case role
corpus byte-identically to v0.6.12, and the published image prefilled **130,048 tokens exactly in
58.3 s** and decoded **170.36 tok/s**. The RTX 4090 package passed all 15 canonical phases with
OMP 18.4.0: 130,048-token retrieval in 91.2 s and C1 decode at **157.91 tok/s** with 87.59% MTP
acceptance. Stock OMP 18.4.0 kept one session across graceful restarts on both runtimes, and every
turn after the seed reused its cache
([EXP-075](docs/measurements/2026-09-29-stock-omp-1840-durable-sessions.json)).

These are one run per configuration, with synthetic build-log filler, one seed and thinking
`low`. A restart of the OMP process still costs one prefill of a resumed session's context:
OMP 18.4.0's first request after resuming omits the session's reasoning (56,174 tokens from root,
32.0 s, in EXP-074). A server restart alone restores hot, so v0.8.6's stale-checkpoint account of
that cold turn was wrong. Both server builds change, so each saved session re-prefills once after
the upgrade. To upgrade from v0.8.6, follow the quickstart for your lane, remove
`compaction.asyncEnabled: false` from `~/.omp/agent/config.yml` and merge:

```yaml
providers:
  maxInFlightRequests:
    ninfer-beta: 1
    ninfer-native-4090: 1
    ninfer-main: 1
    ninfer-heavy: 1
```

The OMP binary, `models.yml` and `PI_OPENAI_STATEFUL=1` do not change. RTX 3090 remains deferred.

All four documented routes passed **24 steps** on candidate `a1e51a70`
(`a1e51a7064a1b0a5e862f9b77ae8815f8144012d`) with unmodified OMP 18.4.0 and the published
components: RTX 5090 container host 2, macOS client 10, Windows client 5 and RTX 4090 native
Windows 7; both hosts were restored. The upstream macOS arm64 (preview), Windows x64 and
Linux x64 binaries each passed a typed tool turn, an exact continuation and a fail-closed
request against image `d71e34c3`. Linux ran under **WSL2**, not a separately qualified Linux OS.
[Documented routes](releases/v0.8.7/acceptance/documented-routes.json) ·
[Composed acceptance](releases/v0.8.7/acceptance/composed-external-installation.json).

The RTX 5090 routes ran in **two production windows** from a separately hosted Apple silicon
Mac mini. Downtime was at most **264.5 s (4.4 min)** in the failed window and
**384.1 s (6.4 min)** in the accepted window; total downtime was at most
**648.6 s** ([restoration](docs/measurements/2026-09-29-v087-acceptance-restoration.json)).

Candidate `9474326f` passed the RTX 4090 route, but its RTX 5090 window failed at the macOS
restart step. That step seeds its session with the release's own documents, which quoted the
misspelled nonce copy from v0.8.6's first window, and after a hot restore (71,791 of 71,839
tokens reused) the model returned that quoted copy. The seed now drops every line holding the
nonce's digits: the RTX 4090 recall returned the quoted copy in 4 of 30 trials with the old seed
and in none of 30 with the new one ([EXP-076](docs/measurements/2026-09-29-restart-seed-decoy.json)). Candidate
`a1e51a70` passed the RTX 4090 route and a second RTX 5090 window.

[Release notes](releases/v0.8.7/NINFER_RELEASE_NOTES.md) ·
[Manifest](releases/v0.8.7/manifest.json) ·
[Qualification](releases/v0.8.7/qualification.json).

## Where this was — v0.8.6

Install through the [quickstart](docs/QUICKSTART.md); eligibility remains one RTX 5090 or RTX 4090.

Long sessions no longer fail a turn while OMP compacts them. The config every documented
route installs, [`examples/manual-tunnel/fail-closed.yml`](examples/manual-tunnel/fail-closed.yml),
sets `compaction.asyncEnabled: false`, so unmodified upstream OMP 18.4.0 compacts before
the turn instead of in the background. Both lanes admit one request at a time. On the RTX 4090,
the background handoff took 56-61 s; the next turn's attempts expired at the 30 s admission
deadline, and the third of three compactions ended in `503 request_queue_timeout`.

[EXP-072](docs/measurements/2026-09-28-omp-long-sessions.json), using the new
[`scripts/omp_long_session_proof.py`](scripts/omp_long_session_proof.py), measured repeated
automatic compaction with stock OMP 18.4.0 on both lanes:

- RTX 4090: three inline handoffs took **77.0-83.7 s** each with **no expired admission**.
  The newest identifier survived every compaction and a graceful restart; all three older
  identifiers were also recalled. The turn carrying a compaction took **91-101 s**.
- RTX 5090: two snapcompact compactions took **0.07-0.08 s** on the client. Both identifiers
  held only inside frames were recalled; `detail: "auto"` reaches the model at native resolution.
  The bounded archive dropped **76,832 and 192,080 characters** of older middle history.
- A single-admission mock reproduced the failure behind a 45 s handoff after six expired
  attempts with the old config; inline compaction expired none. OMP recognizes the runtime's
  `context_length_exceeded` response on both fragments, compacts and retries.

These are one run per configuration on each lane, with synthetic build-log filler, one seed
and thinking `low`; the failure rate is not measured. Older-identifier recall is recorded,
not gated. The RTX 5090 was not restarted after compaction. RTX 4090 handoffs re-prefill the
whole session because `tool_choice: none` omits the usual tool block; a second full replay
just below the threshold also re-prefills about 102,600 tokens (68 s). After compaction, its
first turn after a graceful restart re-prefills about 32,000 tokens (17 s); without compaction
the restore is hot. On the RTX 5090, one chained turn per run re-prefilled 93,696-105,066 tokens
from root (40-46 s), with cause unidentified. These remain runtime work, not fixes in this release.

The documented resume and restart checks now plant the nonce with an OK-only reply and ask for
a verbatim recall. On the RTX 5090 runtime, v0.8.5's plant made the model restate the nonce
visibly in 87 of 92 trials and v0.8.6's in none
([EXP-073](docs/measurements/2026-09-28-omp-acceptance-sampling.json)); a restated,
misspelled copy is what the first RTX 5090 window's recall returned.

The client, provider fragments, both runtimes, model, memory floors, serving configurations and
lane receipts are unchanged from v0.8.5. RTX 5090 keeps `v0.6.12-qwen38-5090-beta.1`, image
`cd9e10b1`; RTX 4090 keeps `v0.6.9-qwen38-4090-beta.1`, package `6492588e`. Checkpoints carry
across. To upgrade from v0.8.5, merge this into `~/.omp/agent/config.yml`:

```yaml
compaction:
  asyncEnabled: false
```

The OMP binary, `models.yml` and `PI_OPENAI_STATEFUL=1` do not change. The documented resume
and restart checks now plant the nonce with an OK-only reply and ask for a verbatim recall,
rather than asking the model to restate it in its acknowledgment. RTX 3090 remains deferred.

All four documented routes passed **24 steps** on candidate `4f49fce7`
(`4f49fce7d52c62422e4f67cf15a3fa3a63dd72d9`) with unmodified OMP 18.4.0 and the published
components: RTX 5090 container host 2, macOS client 10, Windows client 5 and RTX 4090 native
Windows 7; both hosts were restored. The upstream macOS arm64 (preview), Windows x64 and
Linux x64 binaries each passed a typed tool turn, an exact continuation and a fail-closed
request against image `cd9e10b1`. Linux ran under **WSL2**, not a separately qualified Linux OS.
[Documented routes](releases/v0.8.6/acceptance/documented-routes.json) ·
[Composed acceptance](releases/v0.8.6/acceptance/composed-external-installation.json).

The RTX 5090 routes ran in **two production windows** from a separately hosted Apple silicon
Mac mini. Downtime was at most **186.9 s (3.1 min)** in the failed window and
**392.1 s (6.5 min)** in the accepted window;
total downtime was at most **579.0 s**
([restoration](docs/measurements/2026-09-28-v086-acceptance-restoration.json)).

Candidate `be49962c` was refused by the RTX 4090 preflight before touching the lane: the lane
stage had left its manifest a draft; tooling was fixed. On `1fa202fd` the RTX 4090 route passed,
but the first RTX 5090 window failed at macOS resume: the acknowledgment wrote `COBOLT-493817`
and recall returned that copy. Production was restored after **186.9 s**; nonce checks were
hardened. On `60b5d82d` the documented RTX 4090 route passed, but its harness refused two
tool calls where it required exactly one. The harness now accounts each request to a documented
turn or tool call. Candidate `4f49fce7` passed the RTX 4090 route and a second RTX 5090 window.

[Release notes](releases/v0.8.6/NINFER_RELEASE_NOTES.md) ·
[Manifest](releases/v0.8.6/manifest.json) ·
[Qualification](releases/v0.8.6/qualification.json).

**The next step at v0.8.6** was to qualify the RTX 3090 on its hardware; v0.9.1 closes it
with the physical-card lane qualification and documented-route acceptance.

## Where this was — v0.8.5

Install through the [quickstart](docs/QUICKSTART.md); eligibility remains one RTX 5090 or RTX 4090.

OMP compacts a 131,072-token session automatically at 111,412 tokens. For an image-capable
model, its first usable method, snapcompact, archives earlier turns as PNGs at
`detail: "original"`. NInfer refuses that with HTTP 400 `image_detail_not_supported`, so
long RTX 5090 sessions on stock OMP 18.3.0-18.4.0 (releases v0.8.0-v0.8.4) failed at their
first compaction. The RTX 5090 fragments now declare `compat.supportsImageDetailOriginal: false`,
so OMP sends `auto`. On the RTX 5090 runtime, one compacted continuation completed with
26,075 input tokens and the exact nonce; `original` was refused in 9 ms
([EXP-071](docs/measurements/2026-09-28-omp-snapcompact-image-detail.json)). The text-only RTX 4090
model is never compacted into images. Readback beyond that nonce and repeated compactions
in one session were not measured in EXP-071; EXP-072 above adds those measurements.

The first v0.8.5 route candidate hit this at the macOS restart step when its seed, the
release's own documents, grew from 332,331 to 343,205 bytes. That step now seeds the first
200,000 ASCII bytes (about 64,000 tokens), keeping checkpoint restoration distinct from
compacted-prompt acceptance.

The v0.8.5 release also repins unmodified upstream OMP from 18.3.5 to
[18.4.0](https://github.com/can1357/oh-my-pi/releases/tag/v18.4.0). On Windows, 18.3.5
printed a false `ended before completing` line after finished `omp -p` turns and exited 1
after a complete `omp models` listing. Upstream fix `9d3e0d4975` resolves
[#13470](https://github.com/can1357/oh-my-pi/issues/13470).

[EXP-070](docs/measurements/2026-09-28-omp-1840-windows-completion-status.json) compared the
Windows x64 binaries with the documented RTX 4090 provider fragment against a local mock
Responses endpoint: 18.3.5 exited 1 after 5/5 complete listings and printed the false line
after 5/5 completed turns that exited 0; 18.4.0 exited 0 without that line in all 10 runs.
Both versions retain the existing `Working...` stderr indicator. This is client-status
proof on Windows x64, not a GPU inference or performance measurement. The RTX 4090 route
harness again requires exit 0 plus exactly the documented selector; the 18.3.5-only
exit-status tolerance and false-line troubleshooting entry are removed.

Both lanes carry the exact v0.8.4 runtime bytes. RTX 5090 keeps
`v0.6.12-qwen38-5090-beta.1`, image `cd9e10b1`, server `3ab266e5`, source `9d1ef748`,
profile `qwen38-5090-v0.8.2`, configuration `56878aed` and its carried v0.8.3 lane receipt.
RTX 4090 keeps `v0.6.9-qwen38-4090-beta.1`, package `6492588e`, server `65364401`, source
`5ac17674`, configuration `ccecfbe3` and 60000 ms keep-warm with the sm_89 50 ms/100 ms spin.
Its carried v0.8.4 lane receipt records qualification with OMP 18.3.5, not a new 18.4.0
runtime qualification. Model and memory floors are unchanged; no performance gain is claimed.

To upgrade from v0.8.4, install the checksummed 18.4.0 client binary and add
`supportsImageDetailOriginal: false` under the RTX 5090 model's `compat` in
`~/.omp/agent/models.yml`, as the updated fragments do. Other fragment fields and
`PI_OPENAI_STATEFUL=1` are unchanged. Neither server build changes, so checkpoints on both
lanes carry across.

All four documented routes passed **24 steps** on candidate `943063e7` with unmodified
OMP 18.4.0 and the published components: RTX 5090 container host 2, macOS client 10, Windows
client 5 and RTX 4090 native Windows 7; both hosts were restored. The upstream macOS arm64
(preview), Windows x64 and Linux x64 binaries each passed a typed tool turn, an exact
continuation and a fail-closed request against RTX 5090 image `cd9e10b1`. Linux ran under
WSL2, not a separately qualified Linux OS.
[Documented routes](releases/v0.8.5/acceptance/documented-routes.json) ·
[Composed acceptance](releases/v0.8.5/acceptance/composed-external-installation.json).

The RTX 5090 routes ran in one production window, with downtime at most
**381.2 s (6.4 min)**, from a separately hosted Apple silicon Mac mini on
macOS 26.6.1 over the tailnet, not the maintainer's workstation
([restoration](docs/measurements/2026-09-28-v085-acceptance-restoration.json)).

[EXP-067](docs/measurements/2026-09-27-stock-omp-1835-durable-sessions.json) (durable sessions)
and [EXP-068](docs/measurements/2026-09-28-omp-1835-live-steering.json) remain OMP 18.3.5
evidence. In 18.4.0, live steering remains Codex-WebSocket-only in
`openai-codex-responses.ts`, gated on `compat.supportsSteering`; these providers do not set it.
The upstream engine merge stays deferred
([EXP-065](docs/measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json)); the
sm_89 Q5 tensor-core route stays rejected
([EXP-069](docs/measurements/2026-09-28-rtx4090-q5-small-t-mma.json)). RTX 3090 remains deferred:
its `v0.6.2-beta.1` package is built and tested (99/105 tests) but unpublished; one
`qualify_native.py` window on its physical host remains
([preparedness](docs/measurements/2026-09-28-rtx3090-v062-build-preparedness.json)).

[Release notes](releases/v0.8.5/NINFER_RELEASE_NOTES.md) ·
[Qualification](releases/v0.8.5/qualification.json).

**The next step at v0.8.5** was to qualify the RTX 3090 on its hardware.

## Where this was — v0.8.4

The `v0.8.4` release brings every eligible lane current. Install through the
[quickstart](docs/QUICKSTART.md); RTX 3090 remains deferred.

RTX 4090 ships `v0.6.9-qwen38-4090-beta.1` (package `6492588e`, server `65364401`,
source `5ac17674`, configuration `ccecfbe3`). Its `engine.gpu_keep_warm_ms = 60000` uses an
sm_89-specific 50 ms spin every 100 ms: the RTX 5090's 3.5 ms/10 ms pattern did not hold this
card in P2. New sessions after 12-58 s idle prefilled in **0.146-0.148 s**, with time to first
token **0.167-0.178 s**; all 31 outputs were byte-identical. The hold costs about **72 W**
above idle, and a request arriving mid-spin can overlap one warp for up to 50 ms.
[EXP-064](docs/measurements/2026-09-27-rtx4090-engine-keep-warm.json) ·
[EXP-066](docs/measurements/2026-09-27-rtx4090-keep-warm-long-spin.json).

The published package passed all **15 canonical qualification phases**
([lane receipt](releases/v0.8.4/qualification/rtx4090.json)); this is not a decode-kernel speedup.
RTX 5090 keeps `v0.6.12-qwen38-5090-beta.1`, image `cd9e10b1`, profile `qwen38-5090-v0.8.2`,
configuration `56878aed` and its carried v0.8.3 lane receipt. The model and memory floors are
unchanged. RTX 4090 checkpoints from v0.6.8 re-prefill once on the changed server build;
RTX 5090 carries its v0.8.3 checkpoints.

The v0.8.4 client advanced to unmodified upstream **OMP 18.3.5**. Its macOS arm64 binary kept one
short session across graceful restarts on both lanes with the documented fragments unchanged
([EXP-067](docs/measurements/2026-09-27-stock-omp-1835-durable-sessions.json)). A steer submitted
mid-stream did not abort: OMP sent it **27 ms** after `response.completed` as a new request
chained by `previous_response_id`
([EXP-068](docs/measurements/2026-09-28-omp-1835-live-steering.json)).

All four documented routes passed **24 steps** on candidate `68302298` with unmodified OMP
18.3.5 and the published v0.8.4 components: RTX 5090 container host 2, macOS client 10, Windows
client 5 and RTX 4090 native Windows 7; both hosts were restored. The upstream macOS arm64
(preview), Windows x64 and Linux x64 binaries each passed a typed tool turn, an exact
continuation and a fail-closed request against RTX 5090 image `cd9e10b1`. Linux ran under WSL2,
not a separately qualified Linux OS.
[Documented routes](releases/v0.8.4/acceptance/documented-routes.json) ·
[Composed acceptance](releases/v0.8.4/acceptance/composed-external-installation.json).

The RTX 5090 routes ran in one production window, with downtime at most **421.5 s (7.0 min)**,
from a separately hosted Apple silicon Mac mini on macOS 26.6.1 over the tailnet, not the
maintainer's workstation
([restoration](docs/measurements/2026-09-28-v084-acceptance-restoration.json)). The RTX 4090
route's first candidate stopped at its no-effect preflight on OMP 18.3.5's `omp models` exit
status; judging the complete listing let candidate `68302298` pass the documented blocks.
[can1357/oh-my-pi#13470](https://github.com/can1357/oh-my-pi/issues/13470) is fixed in upstream
18.4.0, released 2026-09-28. v0.8.4 pinned 18.3.5; v0.8.5 repins to 18.4.0.

The upstream engine merge stays deferred: `e31bc99b` has about **18% slower decode** and
fanout **0/4 versus 4/4**
([EXP-065](docs/measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json)). The
RTX 4090 Q5 tensor-core route was rejected by its pre-registered rule: **+0.38% at 26K** and
**+0.40% at 60K**, below required **2.0%/1.0%** gains
([EXP-069](docs/measurements/2026-09-28-rtx4090-q5-small-t-mma.json)). RTX 3090's v0.6.2-beta.1
package built and tested at `5ac17674` remains unpublished, with hardware qualification pending
([preparedness](docs/measurements/2026-09-28-rtx3090-v062-build-preparedness.json)).

[Release notes](releases/v0.8.4/NINFER_RELEASE_NOTES.md) ·
[Qualification](releases/v0.8.4/qualification.json).

**The next step at v0.8.4** was to qualify the RTX 3090 on its hardware.

## Historical v0.8.3 — faster RTX 5090 decode

The `v0.8.3` release makes RTX 5090 decode faster with `v0.6.12-qwen38-5090-beta.1`
(image `cd9e10b1`, server `3ab266e5`, source `9d1ef748`). RTX 4090 native stays on
`v0.6.8-qwen38-4090-beta.1` (package `46aa4110`, server `32905865`, source `5a774841`)
and carries its v0.8.1 lane receipt. The unmodified OMP 18.3.0 client and model are unchanged.
Install through the [quickstart](docs/QUICKSTART.md); RTX 3090 remains deferred.

The four Q5 projections in the MTP3 verify pass use small-T tensor-core MMA on `sm_120`
at the four-token extent instead of SIMT row kernels; the route is compiled out for `sm_86`
and `sm_89` ([EXP-057](docs/measurements/2026-09-26-q5-small-t-tensor-core.json)).
Release-build A/B/B/A measurements against v0.8.2's source show decode **+4.4% at 26K**,
**+3.6% at 60K** and **+6.3% at 1,024 tokens**, with MTP3 rounds **3.5-4.9% shorter**
([EXP-063](docs/measurements/2026-09-27-powered-redaction-screen.json)). With no prompt, decode
was **0.5% slower**, with 0.423 of drafts accepted on the new build's own text versus 0.461.

Accumulation order changes; **58 of 89** role-corpus cases answer differently from v0.8.2.
The pre-registered [EXP-063](docs/measurements/2026-09-27-powered-redaction-screen.json)
redaction screen passed on **504 pairs**: 7 controls with 72 whitespace variants. Candidate
leaks were **561 vs 582** for v0.8.2 (ratio **0.964**, one-sided 95% upper bound **1.012**,
margin **1.10**). Pass rates were **53.2% vs 52.6%** (**+0.6 percentage points**, lower bound
**-1.2 points**, margin **-5 points**). All validity checks held. EXP-057's earlier 56-sample
point-estimate screen had rejected the route (**69 vs 61 leaks**); EXP-063 re-tested that
redaction regression with power. Other primary role-corpus measures were within 2.0 points
of v0.8.2 in one run per build. The published image matched the screened candidate on **89/89**.

Serving arguments, profile `qwen38-5090-v0.8.2`, configuration `56878aed`,
`--gpu-keep-warm-ms 60000`, 16384 MiB host KV and the 28672 MiB host floor are unchanged.
Gates were re-measured on the published RTX 5090 image: exact 130,048-token retrieval in
**58.7 s**, decode at **168.07 tok/s**, and the agent protocol across a restart. Four stored
sessions restored after restart; publication-barrier, fanout, warm-arrival, restore and
multisession probes passed. Root fallback remained 2 of 8 continuations/forks. None of 24
fresh sessions fell back to a full prefill; median TTFT was **0.093-0.100 s**. Stock OMP
18.3.0 kept one session across graceful restarts, restoring its checkpoint on the first request.

All four documented routes passed **24 steps** with unmodified OMP 18.3.0 on the published
v0.8.3 components: RTX 5090 container host 2, macOS client 10, Windows client 5 and RTX 4090
native Windows 7; both hosts were restored.
The upstream macOS arm64, Windows x64 and Linux x64 binaries each passed a typed tool turn,
an exact continuation and a fail-closed request against the published RTX 5090 image.
[Release notes](releases/v0.8.3/NINFER_RELEASE_NOTES.md) ·
[Qualification](releases/v0.8.3/qualification.json) ·
[RTX 5090 receipt](releases/v0.8.3/qualification/rtx5090.json) ·
[Documented routes](releases/v0.8.3/acceptance/documented-routes.json) ·
[Composed acceptance](releases/v0.8.3/acceptance/composed-external-installation.json).

Checkpoints bind the exact server build: sessions saved by v0.8.2 do not restore on the new
RTX 5090 build in v0.8.3. Each session re-prefills once.

**The next step at v0.8.3** was the RTX 3090's return; its lane remained deferred until its host was
available.

## Where this was — v0.8.2

The `v0.8.2` release added GPU keep-warm to RTX 5090 `v0.6.11-qwen38-5090-beta.1`
(image `26813f56`, server `0d7e042b`, source `32c21f73`). RTX 4090 native stays on
`v0.6.8-qwen38-4090-beta.1` (package `46aa4110`, server `32905865`, source `5a774841`)
and carries its v0.8.1 lane receipt. The unmodified OMP 18.3.0 client and model are unchanged.
Install through the [quickstart](docs/QUICKSTART.md); RTX 3090 remains deferred.

The RTX 5090 profile advances to `qwen38-5090-v0.8.2` with `--gpu-keep-warm-ms 60000`;
host KV stays 16384 MiB and the host floor stays 28672 MiB. The runtime option is off by default.
After work and while idle, a single-warp kernel touches no memory and spins 3.5 ms of every
10 ms on its own stream for the configured grace, skipping a launch while the previous spin runs
and stopping when a request is pending.

New sessions after 12-58 s idle prefilled in **0.155-0.157 s** (TTFT **0.173-0.181 s**),
the same as back to back, versus **0.253-0.304 s** (TTFT **0.316-0.366 s**) without it.
The 89-case role corpus was byte-identical to v0.8.1 on and off. Holding clocks costs about
**71 W**; replaying a 60 s grace over 62 h of logged v0.7.0 traffic would cover 84 of 138
requests after at least 5 s idle (74 of 103 new sessions) at about **2.3 W average**.
[EXP-062](docs/measurements/2026-09-26-engine-keep-warm.json).

The published RTX 5090 image recorded 130,048-token exact retrieval in **56.4 s**, decode at
**160.07 tok/s**, four sessions restored after a restart, and passed publication-barrier,
fanout, warm-arrival, restore and multisession probes. None of 24 fresh sessions fell back to
a full prefill; median TTFT was **0.090-0.098 s**. Stock OMP 18.3.0 kept one session across
restarts on the RTX 5090. The carried RTX 4090 receipt records 15 canonical native phases and
130,048-token retrieval in **91.0 s**.

All four documented routes passed **24 steps** with unmodified OMP 18.3.0 on the published
v0.8.2 components: RTX 5090 container host 2, macOS client 10, Windows client 5 and RTX 4090
native Windows 7; both hosts were restored.
The upstream macOS arm64, Windows x64 and Linux x64 binaries each passed a typed tool turn,
an exact continuation and a fail-closed request against the published RTX 5090 image.
[Release notes](releases/v0.8.2/NINFER_RELEASE_NOTES.md) ·
[Qualification](releases/v0.8.2/qualification.json) ·
[Documented routes](releases/v0.8.2/acceptance/documented-routes.json) ·
[Composed acceptance](releases/v0.8.2/acceptance/composed-external-installation.json).

Checkpoints bind the exact server build: sessions saved by v0.8.1 do not restore on the new
RTX 5090 build in v0.8.2. OMP resends the full conversation and each session re-prefills once.

**The next step at v0.8.2** was the RTX 3090's return; its lane stayed deferred until its
qualification host was available, and the historical v0.7.2 route stayed on OMP 18.0.9.

## Where this was — v0.8.1

The `v0.8.1` release made decode faster on both eligible lanes: RTX 5090
`v0.6.10-qwen38-5090-beta.1` (image `5ca6e416`, source `8cc0810a`) and RTX 4090 native
`v0.6.8-qwen38-4090-beta.1` (package `46aa4110`, source `5a774841`). The unmodified upstream
OMP 18.3.0 binaries and their SHA-256 pins, model, serving settings and memory floors are
unchanged from v0.8.0. Install through the [quickstart](docs/QUICKSTART.md).

The MTP3 verify pass shares activation loads across weight rows in small-extent Q4/Q5
projections, and the Q4 gate/up kernel avoids shared-memory bank conflicts. RTX 5090 decode
is **10.3-11.0% faster** with identical outputs. Native lanes retain one-row split2 kernels
for MLP down and mixer output; RTX 4090 C1 decode is **157.89 vs 153.54 tok/s**
([EXP-055](docs/measurements/2026-09-25-decode-kernel-schedules.json),
[EXP-054](docs/measurements/2026-09-25-decode-roofline-attribution.json)).

Every runtime gate was re-measured on the published bytes. The RTX 5090 durability workload,
publication barrier, fanout, warm-arrival, restore, multisession and shared-prefix probes
matched v0.8.0's behavior; the RTX 4090 package passed all 15 canonical native phases. Stock
OMP kept one session across restarts on both lanes. All four documented routes passed their
24 steps with both hosts restored. [Release notes](releases/v0.8.1/NINFER_RELEASE_NOTES.md) ·
[Qualification](releases/v0.8.1/qualification.json) ·
[Documented routes](releases/v0.8.1/acceptance/documented-routes.json).

Upgrading changes the server fingerprint: v0.8.0 checkpoints are incompatible, so OMP resends
the conversation and each session re-prefills once. Old checkpoints age out under the quota.
Automatic checkpoints remain best effort; universal warm reuse is not claimed.

**The next step at v0.8.1** was the RTX 3090's return; its lane stayed deferred until its
qualification host was available, and the historical v0.7.2 route stayed on OMP 18.0.9.

## Where this was — v0.8.0

The `v0.8.0` release used the unmodified upstream
[OMP 18.3.0 release binary](https://github.com/can1357/oh-my-pi/releases/tag/v18.3.0), not a
fork build, archive, installer or cask. Install and operate the RTX 5090 Windows 11 + Docker
Desktop/WSL2 container route or the RTX 4090 native Windows package through the
[quickstart](docs/QUICKSTART.md); stock OMP has no `omp appliance` commands. RTX 5090 shipped
`v0.6.9-qwen38-5090-beta.2` and RTX 4090 shipped `v0.6.7-qwen38-4090-beta.2`, with the model,
serving settings and memory floors unchanged from v0.7.4.

Authenticated stock clients get durable sessions through `prompt_cache_key`, with a returning
session's checkpoint restored on its first request after a restart. On both published lanes,
unmodified OMP 18.3.0 kept one session across graceful restarts, including a new process resuming
after a restart ([EXP-053](docs/measurements/2026-09-25-stock-omp-durable-sessions.json)). On the
published RTX 5090 image, none of 24 later fresh sessions fell back to a full prefill after each
of three agent types had prefilled its 11,887-14,199-token prefix; median time to first token was
0.095-0.102 s. The four documented routes passed on the published beta.2 components with the
stock client; both hosts were restored.
[Release notes](releases/v0.8.0/NINFER_RELEASE_NOTES.md) ·
[Documented routes](releases/v0.8.0/acceptance/documented-routes.json).

**The next step at v0.8.0** was the RTX 3090’s return as a separate release once its
qualification host was available again (expected around 2026-09-30).
Its [historical v0.7.2 route](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)
stays on OMP 18.0.9, not a v0.8.0 qualification claim. Rebasing the runtime onto upstream NInfer,
which the engine window deferred
([EXP-048](docs/measurements/2026-09-24-engine-window-upstream-vs-shipped.json)), remains future
work; v0.8.0 does not include it.

## Where this was — v0.7.4

The `v0.7.4` release rebound both lanes to the durable-session runtime from reviewed source
`1c17c3fa`: RTX 5090 `v0.6.8-qwen38-5090-beta.1` and RTX 4090 native `v0.6.6-qwen38-4090-beta.1`.
A graceful stop then kept every live session it could save
([#45](https://github.com/alphastorm/omp-ninfer/issues/45),
[#46](https://github.com/alphastorm/omp-ninfer/issues/46)). The OMP 18.2.3 client, model, serving
settings and memory floors were `v0.7.3`'s, and the four documented routes passed again on the
published components. The RTX 3090 lane was deferred until its host returned (expected around
2026-09-30); its [v0.7.2 route](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)
stays on OMP 18.0.9.

**How the fix was chosen.** The engine window measured first and deferred the merge
([EXP-048](docs/measurements/2026-09-24-engine-window-upstream-vs-shipped.json)).

On the RTX 5090 appliance, with the same weights and serving settings, upstream NInfer head
(`594930e7`, 202 commits past this fork's base) matches the shipped runtime on prefill (2,269 vs
2,242 tok/s at 130,048 tokens) and on decode rounds per second (61.2 vs 62.0), and keeps less
prefix reuse on this product's workloads: 0 of 4 fanout branches reuse their base (4 of 4 shipped)
and 4 of 8 two-session continuations re-prefill from root (2 of 8 shipped). Merging it means a
re-architecture port - 111 unmerged paths, 40 of them fork features re-expressed in upstream's
restructured model, context-cache and serve layers, plus the v3 artifact, a new chat template and a
new checkpoint format - for no measured lane gain. The same comparison
([`scripts/engine_window_compare.py`](scripts/engine_window_compare.py)) is rerun when an upstream
change could move a lane gate
([watch report](docs/measurements/2026-09-24-upstream-watch.json), [positions](docs/UPSTREAM.md),
[#33](https://github.com/alphastorm/omp-ninfer/issues/33)).

The same window reproduced the durability gap on the `v0.7.3` runtime: a graceful stop with four
stored sessions reported `saved 2, nothing to save 0, refused 2` and lost two sessions' state, with
the generic `program refused continuation export`. A diagnostic-only build that names every export
gate reproduced it and named it
([EXP-049](docs/measurements/2026-09-24-export-refusal-gates.json)): the two 126K-token sessions had
been evicted from the engine by the time anything tried to save them (`session is not indexed in the
engine`), and while they were resident every automatic save hit a transient gate and was dropped -
`catalogued checkpoint tag mismatch` 1 ms after the turn finished, before its continuation was
catalogued, then `resource transaction in progress` while the next request ran. The exporter itself
works when it gets a quiescent continuation (a 5.2 GB session saved in 4.3 s). The fix is in this
fork, not upstream ([#45](https://github.com/alphastorm/omp-ninfer/issues/45)), and is measured on
both lanes ([EXP-050](docs/measurements/2026-09-24-durable-session-eviction.json)): transient
automatic refusals retry when the engine quiesces, and admission saves a checkpoint-tagged session
before pressure evicts it. The same workload's stop now reports `saved 1, nothing to save 3,
refused 0` on both lanes, all four stored sessions resume after a restart, and a second stop
refuses nothing. Resuming exposed a third loss, fixed with them
([#46](https://github.com/alphastorm/omp-ninfer/issues/46)): re-saving one session under the
checkpoint quota deleted other sessions' only checkpoints. An independent review of those fixes
found two more losses, both fixed: save-before-evict gave a reply still streaming to its client two
seconds to reach the response store and then evicted the session unsaved, and a quota pass whose
cleanup failed kept deleting other sessions' only checkpoints. Holding one reply out of the store
for 6 s while another session's admission had to evict it, the reviewed candidate lost that turn
(404 after a restart) and the remediation saved it first and resumed it exactly
([EXP-051](docs/measurements/2026-09-24-publication-barrier.json)). Saving before eviction costs the
admitting request about 6.5 s per 126K-token session on the RTX 5090, where one such checkpoint is
8.6 GB. The RTX 4090 workload evicted no checkpoint-tagged session, so save-before-evict is
exercised on the RTX 5090 only; the published RTX 4090 package passed its 15 lane qualification
phases.

**The next step at v0.7.4** was the RTX 3090's return as a separate release on that runtime
and OMP 18.2.3 once its host was available again.

## Where this was — v0.7.3

The `v0.7.3` release repinned only the client, from OMP 18.0.9 to
`omp-18.2.3-cross-platform-beta-1`: the fork's NInfer compat layer rebased onto upstream
`v18.2.3`, closing the re-pin evaluated in
[#43](https://github.com/alphastorm/omp-ninfer/issues/43). The published macOS, Windows and Linux
clients passed live inference and a fresh 24-step documented-route acceptance passed on both
qualified lanes; the runtime images, model, serving settings and memory floors were `v0.7.2`'s.

`v0.7.2` before it closed the restore bound `v0.7.1` named: restore reclaims checkpoint-backed
resident sessions under host-KV pressure, so both RTX 5090 sessions at the 131,072-token ceiling
resume after a restart ([#40](https://github.com/alphastorm/omp-ninfer/issues/40)), and on the
RTX 4090 a pool sized for one ceiling session restored two
([EXP-047](docs/measurements/2026-09-17-restore-reclaim.json)). Automatic checkpoints stayed best
effort: EXP-047's combined process refused three automatic saves and, holding earlier sessions
too, three shutdown saves, with a refusal that does not name its gate.

## Where this was — v0.7.1

The `v0.7.1` release fixes a durability defect on the RTX 4090 native lane: its host-KV pool was
smaller than one ceiling-sized session, so a checkpoint could be reported saved and then refused at
restore, leaving the session unresumable. The pool is now sized to hold two such sessions, the lane
declares the host memory that pins, and the engine refuses an export whose checkpoint its own
configuration could not admit back - a reported save is a restorable save. The same bound explains
the RTX 5090's two-session restore boundary, which is now reported with a named reason rather than
an opaque one
([EXP-043](docs/measurements/2026-09-16-restore-bound-host-kv-pool.json)).

## Where this was — v0.7.0

The `v0.7.0` release keeps two sessions at the 131,072-token ceiling reusing their prefixes on
one card: the RTX 5090 Host KV pool moves from 8 GiB to 16 GiB, so alternating turns reuse about
125,900 cached tokens in 1.6-3.5 s where the shipped pool re-prefilled every one of them from
root in about 58 s. The component, image, model, client and KV dtype are unchanged, the
configuration identity is not, and the pool is pinned memory - so the profile declares the
28,672 MiB of runtime-host memory it needs and the documented launcher refuses a smaller host
rather than being OOM-killed mid-request. Both 8-bit KV dtypes fix the same loss and were
rejected on the private corpus' redaction and grounding criteria, re-measured on one runtime.
Durability is narrower than reuse and now bounded in writing: both sessions checkpoint and a
graceful stop saves both, but after a restart one of the two is declined and re-prefills
([EXP-041](docs/measurements/2026-09-16-two-long-session-capacity.json)).

**Client re-pin, evaluated 2026-09-17
([#43](https://github.com/alphastorm/omp-ninfer/issues/43)):** the pinned client is this fork's
build of upstream `v18.0.9`, and upstream is 3,521 commits ahead at `v18.2.2`. Run against the
production lane, the newer client is refused four ways - it sends `prompt_cache_key`, asks for
`include: ["reasoning.encrypted_content"]` and `reasoning.summary`, all of which the server refuses
as features it will not silently ignore, and it sent the local model alias instead of the mapped
`requestModelId`. The structural finding is that the upstream binary carries no `ninfer*` symbols at
all: the provider compat layer is the fork's, so a re-pin is a rebase rather than an adoption. With
those four closed at a proxy, the candidate drove the lane cleanly, including stateful resume
([EXP-046](docs/measurements/2026-09-17-client-repin-evaluation.json)). Closed by `v0.7.3`.

**Upstream campaigns, re-triaged 2026-09-17
([#33](https://github.com/alphastorm/omp-ninfer/issues/33)):** the forks are 194 / 57 / 141 commits
ahead, and applicability was measured rather than assumed - every recommended commit was
cherry-picked into a scratch worktree and reverted. On the RTX 5090, 11 of 129 apply cleanly and
none of them changes served behaviour on a shipped profile; the serve-layer fixes the 2026-08-30
plan named now conflict because `v0.6.9` implemented those semantics independently and upstream
restructured `src/serve` and moved to artifact v3. On the RTX 4090, 9 of 51 apply cleanly and every
fix this lane wants - chunked KV snapshot staging, the MTP restore stride, publishing finished
snapshot saves, WDDM residency, the D3D12 fence, the admission-shortfall and `/health` fixes -
conflicts in files this fork changed. Selective backporting is therefore closed on the 5090 and the
4090 item becomes a scoped rebase, read against `v0.7.1`'s durability work
([EXP-045](docs/measurements/2026-09-17-upstream-applicability-triage.json)). Followed on
2026-09-24 by EXP-048 above, which measured upstream head itself and deferred the merge.

**EXP-041's two follow-ups, both since closed:**

1. **Restore admission for a second full-ceiling session**
   ([#40](https://github.com/alphastorm/omp-ninfer/issues/40)). Two sessions at the
   131,072-token ceiling both checkpoint and a graceful stop saves both, but after the restart
   exactly one is accepted back; the other is declined with `the engine did not accept the
   checkpointed continuation` and re-prefills from its transcript. Reproduced three times on
   the shipped configuration. The refusal is safe - the store is untouched and nothing is
   served from a partially restored session - so this is an admission-capacity limit to find
   and raise, not a correctness defect. Closed by `v0.7.2`'s restore reclaim (EXP-047).
2. **RTX 4090 Host KV pool sizing**
   ([#41](https://github.com/alphastorm/omp-ninfer/issues/41)). The same two-session workload on
   the native lane loses every continuation to a 90 s re-prefill at its 4 GiB pool, and the
   server refuses automatic checkpoints while both sessions are live (`program refused
   continuation export`), so a managed stop saved one session and lost the other. Its INT8 KV
   makes the pool cheaper per session than the 5090's, so the sizing question is the same one
   this release answered on the container lane. Closed by `v0.7.1`'s 11264 MiB pool (EXP-043).

The `v0.6.10` release before it changed no component: it makes the documented container route
refuse a launch whose bind mounts the engine cannot stage, and names the two ways a reboot
breaks that route. The `v0.6.9` components it ships keep the two mainline lanes on one reviewed source
(`696e78c7`):
RTX 5090 runtime `v0.6.5-qwen38-5090-beta.1` and RTX 4090 native
`v0.6.3-qwen38-4090-beta.1`, both published and lane-qualified. It independently implements
the semantics of upstream Qwen tool-parser fixes `3b50962b` and `0c5d570c` without taking the
serve-adapter rebase: supported scalar unions, case-insensitive booleans, precise numeric
lexemes, mathematically integral values, duplicate parameters, and balanced embedded markup.
Custom raw input, history, opaque IDs, and stream ownership stay intact. Review remediation
prevents malformed-region rescans and recursive union traversal; bytewise regressions and an
8,192-deep union case pass. Model, serving settings, client, and RTX 3090 component are unchanged.
The 5090 candidate gates and 15/15 native lane phases are complete. RTX 4090 public-URL
already-installed acceptance and RTX 5090 host 2/2 / macOS 10/10 documented routes passed.
[Release notes](releases/v0.6.9/NINFER_RELEASE_NOTES.md) ·
[Composed acceptance](releases/v0.6.9/acceptance/composed-external-installation.json).

From `v0.6.8` both mainline lanes run one runtime source: the RTX 4090 native lane carries the
upstream engine tranche and the GDN capacity fix the 5090 took in `v0.6.7`, and a fork continued
while its sibling is alive no longer answers HTTP 500 on any lane (ninfer#43, EXP-036).
All three lanes install from public URLs with a durable session store on the route the
documentation gives you - from `v0.6.3` the published RTX 5090 launcher mounts one, which it did
not before ([EXP-031](docs/measurements/2026-09-11-rtx5090-public-route-qualification.json)).
From `v0.6.2` all three lanes are built from one runtime
tree: the RTX 5090 container lane moved off the branch head it had served from since `v0.4.4`
onto the mainline commit the native Windows lanes build from, requalified 7/7 on the owner
appliance and re-verified against the image pulled anonymously by digest, with throughput and
durability within run-to-run noise of `v0.5.1`
([receipt](releases/v0.6.2/qualification/rtx5090.json), EXP-030). Session state is durable and
restart-resumable on every lane and survives the machine losing its local copy
(`scripts/checkpoint_sync.py`, origin-authenticated, EXP-018); the two native Windows lanes
restore a checkpointed session in seconds rather than minutes (RTX 4090 1.13 GB in 5.6 s, was
133-149 s; RTX 3090 1.68 GB in 10.7 s, was 92 s), and the RTX 5090 lane reuses a session's base
prefill across sibling agent branches: four branches that replayed 67.7K tokens from scratch on
v0.4.1 (148.7 s) run in under 6 s of forks today
([receipts](docs/measurements/2026-08-31-fanout-probe-v043.json)). Since `v0.5.1` that reuse
also survives a restart on the RTX 5090: a restored template serves every sibling fork on the
shared anchor in either arrival order, and a 5.2 GB checkpoint restores in 3.6-4.0 s instead of
24 s ([receipt](docs/measurements/2026-09-10-restore-probe-rtx5090-v062.json)). A managed stop
of the RTX 4090 lane saves every live session (EXP-028/EXP-029). Since `v0.6.4` the route a
release accepts is the route the documentation prints: every documented route - the three Windows
routes and, from `v0.6.5`, the quickstart's primary macOS row - runs verbatim from its own blocks
with shell-decided outcomes (EXP-032, EXP-033). From `v0.6.7` the RTX 5090 runtime carries the
first tranche of upstream engine work - 18 of 158 commits, taken with reasons and requalified within
noise of the shipped runtime (EXP-035). The reuse loss measured when two long sessions alternate
turns is host KV capacity, not planner policy: it tracks pool size and KV footprint exactly, and
INT8 KV or a larger `--host-kv-mib` removes it on the same binary
([EXP-039](docs/measurements/2026-09-13-hostkv-capacity-multisession.json)), so the upstream
pressure-planner family is no longer what that finding waits on. A machine reboot does not return
either route by itself, and that is now documented rather than discovered: the container route is
created with `--restart no` and, on Docker Desktop, an existing container cannot be started again
once the WSL distro holding its paths has restarted, so recovery is recreation - which the
launcher now refuses to attempt against mounts the engine cannot stage, naming what a throwaway
container saw. The native route's documented `-Action Start` was exercised by a real reboot for
the first time: the lane served 114 s later and the session checkpointed beforehand resumed
exactly ([EXP-040](docs/measurements/2026-09-16-lane-reboot-survivability.json)). Details:
[`CHANGELOG.md`](CHANGELOG.md) · [release status](docs/RELEASES.md) ·
[benchmarks](docs/BENCHMARKS.md).

## 0.4.x campaign status

Sequenced by dependency; completed experiments remain visible because negative results constrain
what can ship next:

1. **Shared-page fanout — shipped in v0.4.3**
   ([ninfer#34](https://github.com/alphastorm/ninfer/issues/34)). Sibling branches reuse the
   anchored base prefill instead of cloning its private pages.
2. **RTX 3090 durable-and-fanout train — shipped in v0.4.5.** The 3090 lane joined the durable
   v0.2 lineage with restart qualification and the same MTP3 shipped profile.
3. **MTP depth-and-corpus ablation — completed post-v0.4.7; retain MTP3.**
   MTP0/3/5/7 ran against the same binary and model within each lane on 24 deterministic
   agent-shaped requests. MTP3 was fastest on every lane and in both repetitions. Against MTP3,
   K5/K7 were 13.57%/24.72% slower on RTX 5090, 7.29%/20.17% slower on RTX 4090, and
   11.34%/22.46% slower on RTX 3090. No alternative cleared the 5% promotion margin; keep the
   qualified MTP3 incumbent and reject deeper drafting for the current artifacts. Exact-output
   attribution remains unresolved because the original traces lack one shared campaign identity
   and a separate fresh-process MTP0 control, but that does not invalidate the no-change throughput
   decision. Public-safe receipts: [5090](docs/measurements/2026-09-04-rtx5090-mtp-agent-ablation.json) ·
   [4090](docs/measurements/2026-09-04-rtx4090-mtp-agent-ablation.json) ·
   [3090](docs/measurements/2026-09-04-rtx3090-mtp-agent-ablation.json). No public release profile
   changed.
4. **`nvfp4` artifact decision — completed post-v0.4.7; not adopted on 32 GB.** The per-lane
   variant campaign measured the artifact on the RTX 5090 with the same corpus and campaign
   identity as every other arm. The chain is conditional on the card, not on the artifact's
   numerics: the weights are 3.28 GB larger, so with the shipped BF16 KV the engine refuses its
   runtime reservation at 131,072 context; the only way to run it here is INT8 KV; and INT8 KV
   alone (same groupwise-int artifact) regresses every criterion of the private role-corpus
   screen. On INT8 KV, `nvfp4` prefills 2.22× faster (6,089 vs 2,740 tok/s), decodes 3.5%
   slower, cuts modeled session time by 15.5–28.7%, beats the INT8 control on every quality
   criterion, and still lands two cases behind the BF16 incumbent on grounding (evidence
   precision −2.4 pp, unsupported-claim rate +2.2 pp) while leaking fewer canaries (4 vs 8); the
   screen reproduces exactly across fresh processes. Two verdicts are recorded side by side: the
   campaign's executable gate says retain (the twelve-criterion screen fails on those two
   grounding criteria, and under the three criteria the frozen manifest originally named —
   leaks, schema validity, fact recall — the same arm would have passed; the amendment is
   recorded in the arms manifest), and the product judgment is that `nvfp4` with INT8 KV is a
   v0.5 RTX 5090 candidate if that grounding shift is accepted and the durable checkpoint train is
   requalified on INT8 pages. NVFP4 W4A4 needs Blackwell tensor cores, so the `sm_89`/`sm_86`
   lanes are out of scope (the 4090 upstream removed its NVFP4 path). The groupwise-int artifact
   stays pinned on all three lanes. Receipts:
   [5090](docs/measurements/2026-09-04-rtx5090-variant-campaign.json) ·
   [4090](docs/measurements/2026-09-04-rtx4090-variant-campaign.json) ·
   [3090](docs/measurements/2026-09-04-rtx3090-variant-campaign.json) ·
   [repeatability](docs/measurements/2026-09-04-rtx5090-quality-repeatability.json).
5. **Per-lane configuration changes from the same campaign — requalified 2026-09-05; shipped in
   `v0.4.8`.** Lanes are tuned independently: the goal is the best measured stack per card,
   not one shared configuration. Each lane reran its own qualification on its own rig with the
   changed configuration and a rebound identity:
   - RTX 4090 `v0.2.1` (`ninfer` commit `b9c4636b`, package `1c66f7d5`): prefill chunk 512 →
     2,048 on the rk2v4-e8/MTP3/131,072 stack; protocol 15/15, the 102,060-token session in
     68.0 s against 84.9 s shipped, persistence via `append_frontier`, OMP golden run exact
     ([receipt](releases/v0.4.8/qualification/rtx4090.json)).
   - RTX 3090 `v0.2.3-beta.1` (`ninfer` commit `2ce6c9dc`, package `96c9c37f`): context ceiling
     65,536 → 131,072 on the INT8/MTP3/1,024-chunk stack; the 14-phase orchestrator passed with
     exact 130,048-token retrieval, 90.2 decode tok/s under the 300 W cap at 22,548 MiB peak,
     restart, rollback, security, and OMP gates
     ([receipt](releases/v0.4.8/qualification/rtx3090.json)).
   - RTX 5090 `qwen38-5090-v0.4.8` (same image `876c7809`, configuration `95765a38`):
     `--max-private-continuations 8 --device-state-slots 4 --host-state-slots 24`; exact
     130,048-token retrieval at 2,207 tok/s cold, 136.0 decode tok/s, the fork/delete arc across a
     restart, 4/4 anchor hits at 57.9K and 67.7K, a 4.5 GB save and verified restart
     ([receipt](releases/v0.4.8/qualification/rtx5090.json),
     [gates](docs/measurements/2026-09-05-rtx5090-v048-profile-gates.json)). After a restart the
     first sibling fork of a restored template re-prefills once; the receipt records it.
   INT8 KV stays rejected on the RTX 5090 (no speed gain) and RTX 4090 (23,180 MiB peak, screen
   regression). The two native components are published (`v0.2.1-qwen38-4090-durable.1`,
   `v0.2.3-qwen38-3090-beta.1`; every manifest URL verified against its hash) and the composed
   external-installation acceptance was rerun from those URLs on 2026-09-05
   ([receipt](releases/v0.4.8/acceptance/composed-external-installation.json)).
   Cut as `v0.4.8` on 2026-09-05. The owner's RTX 5090 appliance promotes to the v0.4.8 profile
   through its own private role-corpus gate, separately from the product release.
6. **MTP exact-output attribution — focused, non-blocking follow-up.** If pursued, run only the
   missing fresh-process MTP0 controls and targeted K0/K3 first-divergence probes. Do not rerun the
   rejected K5/K7 arms without new evidence that could reverse their measured deficit.

## v0.5.x — sessions leave the machine

The 0.5 series is about one thing: a session stops being bound to the card that created it.

**Current boundary:** checkpoint export/import, off-machine transport, and NAS replication
are delivered. The records below distinguish transporting a replica from executing its session:
restore remains runtime/profile/credential-bound, and the transport receipts do not prove
cross-GPU or second-inference-host resume. See [current operator guidance](docs/FACTS.md#checkpoint-transport-and-nas-replication).

1. **Checkpoint sync — replicate, don't serve. Delivered 2026-09-05 (EXP-018).** The native IO
   paths are O_DIRECT/DirectStorage and require local filesystems, so network shares are never a
   checkpoint root; replication is a verified copy of published generations out and back.
   The security gate came first: manifest origin authentication
   ([ninfer#32](https://github.com/alphastorm/ninfer/issues/32)) existed only on the RTX 5090
   container and is now on both native lanes (`manifest.mac`, keyed off the bearer, held outside
   the root; strict `--session-checkpoint-require-origin-auth` posture for roots that receive
   imports). [`scripts/checkpoint_sync.py`](scripts/checkpoint_sync.py) copies only verified
   published generations, stages outside the runtime's scan, publishes with one rename and the
   `current` pointer last, and refuses unMAC'd generations by default.
   [`scripts/sync_probe.py`](scripts/sync_probe.py) proved on every lane that a session survives
   the machine losing its local state (export → carry off → delete with the server stopped →
   carry back → import → restart → exact retrieval of planted keys: 5090 4.5 GB restored in
   24.8 s, 4090 1.13 GB in 7.4 s, 3090 1.69 GB in 11.5 s) and that a replica cannot be forged (a
   payload flip is refused by the tool; a coherent manifest edit is quarantined by the runtime,
   no resurrection). Portability stays same-profile-pair only: the runtime fingerprint binds
   binary and profile and the session namespace binds the bearer key, so cross-lane resume
   (5090↔4090) is not even addressable. Receipts:
   [5090](docs/measurements/2026-09-05-sync-probe-rtx5090.json) ·
   [4090](docs/measurements/2026-09-05-sync-probe-rtx4090.json) ·
   [3090](docs/measurements/2026-09-05-sync-probe-rtx3090.json) ·
   [transport](docs/measurements/2026-09-06-replica-transfer-paths.json) ·
   [NAS](docs/measurements/2026-09-07-nas-replication-sf-lanes.json).
   Replication targets are now measured rather than assumed: a LAN-local NAS share carries about
   1 GbE line rate from the two co-located lanes (115.8 MB/s write from the RTX 4090 host), while
   the same appliance over the tailnet from the other site manages 6.4 MB/s - worse than direct
   host-to-host transport, so each lane replicates to whatever is closest to it (EXP-020).
2. **Template-fork warm starts — measured 2026-09-04; not yet a warm start.** Checkpoint a session
   immediately after the system prompt and repository context are prefilled, then fork every
   subagent from that generation so each one starts hot instead of paying a 30–90 s prefill. The
   probe ([`scripts/fleet_probe.py`](scripts/fleet_probe.py)) measured the pattern on all three
   shipped lanes: device-resident forks are hot only on the RTX 5090, and there only reliably for
   templates of roughly 64K tokens or more (a 57.9K template alternates 1.3 s / 22.5 s because
   the private anchor catalog holds two entries and evicts the shared base anchor; 67.7K gives four
   1.3 s forks); across a process restart the checkpoint restore is never faster than
   re-prefilling the template (5090: 24.7 s vs 21.8 s at 4.5 GB; 4090: 130 s vs 41 s at 1.13 GB;
   3090: 91 s vs 49 s on the shipped binaries; the native-lane restore path was fixed at source
   later the same day, see below), and the native lanes have no sibling reuse at all. The sub-64K loss was
   diagnosed on 2026-09-05 as capacity, not policy: the shipped context-cache defaults (private
   catalog 2, device-state slots 2) cannot hold a base anchor and one stored sibling. Two source
   changes were rejected on the probe; the unchanged shipped binary with
   `--max-private-continuations 8 --device-state-slots 4 --host-state-slots 24` kept 12/12 forks
   on the anchor path at 57.9K, 67.7K, and a loaded-catalog 57.9K in one process for 0.43 GiB of
   slack. It is a trade: it removes the two 22 s re-prefills per four forks at 57.9K and costs
   about 3.9 s once on the first 67.7K fork (5.29 s vs 1.39 s) while the anchor state materializes.
   That configuration is the v0.4.8 RTX 5090 candidate profile, gated by this probe at both
   template sizes in one process; it changes the profile identity, so existing session checkpoints
   do not carry across and the durable train requalifies with it
   ([ninfer#35](https://github.com/alphastorm/ninfer/issues/35)). Restore bandwidth on the
   native lanes was a runtime defect, not a disk limit: the reader issued one DirectStorage
   request per KV page segment; it now reads one staging window at a time and the same sessions
   restore in 5.6 s on the RTX 4090 (was 146.6 s / 133.4 s) and 10.7 s on the RTX 3090 (was
   91.8 s / 92.2 s), quoting planted ledger keys exactly after every restart
   ([ninfer#36](https://github.com/alphastorm/ninfer/issues/36); lane commits `d22ce3fd` and
   `3756db6e`; both lanes requalified on 2026-09-05 and shipped in `v0.4.9` with components
   `v0.2.2-qwen38-4090-durable.1` and `v0.2.4-qwen38-3090-beta.1`). Receipts:
   [5090](docs/measurements/2026-09-04-template-fork-rtx5090.json) ·
   [4090](docs/measurements/2026-09-04-template-fork-rtx4090.json) ·
   [3090](docs/measurements/2026-09-04-template-fork-rtx3090.json) ·
   [anchor sweep](docs/measurements/2026-09-05-fanout-anchor-configuration-sweep-rtx5090.json) ·
   [restore 4090](docs/measurements/2026-09-05-restore-probe-rtx4090.json) ·
   [restore 3090](docs/measurements/2026-09-05-restore-probe-rtx3090.json) ·
   [restore fix 4090](docs/measurements/2026-09-05-restore-probe-rtx4090-candidate.json) ·
   [restore fix 3090](docs/measurements/2026-09-05-restore-probe-rtx3090-candidate.json).
   **Warm arrival now holds on the candidate (measured 2026-09-08, EXP-022/EXP-023).** On the
   shipped v0.4.8 profile a restored template served its first sibling fork by re-prefilling the
   whole prompt (22.1 s, reuse path `root`), so restore plus four forks cost 49.3 s against 26.7 s
   for not checkpointing at all (EXP-021). Three source defects, all on the runtime fork's
   `feat/warm-arrival` branch: a fork left its long anchor on the parent so post-fanout
   checkpoints omitted it; consuming an endpoint double-charged a shared anchor (HTTP 500); and
   the anchor replacement rule evicted the lineage's earliest anchor - the template boundary
   every sibling reuses - on the first continuing turn, because each request captures two anchors
   into a set of two. Replacement now gives up the anchor whose loss costs the least re-prefill.
   Across a restart the candidate serves resume then two forks in 4.2 / 2.9 / 1.3 s and fork
   then resume in 3.7 / 1.3 s, every fork on `private_long_anchor`. Restore itself went from
   24 s to 3.8 s for 5.2 GB: the payload is hashed once, as the engine streams it, with the x86
   SHA extensions, and the reads run at queue depth eight overlapped with the hash; a flipped
   payload byte is still refused and quarantined. The candidate was rebuilt on the appliance's
   canonical route (clean tree `d956e6d6`, binary `71edc2f6`, packaged with its SBOM), published
   as component `v0.5.1-qwen38-5090-beta.1` with runtime image `12ef2d9e...`, and requalified
   from that image through the lifecycle tool on the unchanged v0.4.8 arguments: 24/24 fanout
   forks on the anchor path across 57.9K, 67.7K, and 80.0K templates in-process and after a
   restart, exact 130,048-token retrieval at 2,180 tok/s, 138.2 decode tok/s (EXP-024).
   Shipped as `v0.5.1` on 2026-09-08 after the composed external-installation acceptance from
   the published URLs.
   **The native lanes serve mainline (measured 2026-09-08, EXP-025).** Rather than porting the
   cache into two divergent branches, `port/native-lanes-on-mainline` builds mainline for Ada
   and Ampere with the Windows platform code (D3D12 residency arena, DirectStorage read queue,
   MSVC host tree); every registered suite passes on both builds on the hardware, and in
   candidate windows on the two hosts the mainline runtime beats each installed release on the
   same 130,048-token fixture (RTX 4090 86.8 s vs 97.5 s and 103.8 vs 88.4 decode tok/s;
   RTX 3090 208.6 vs 219.5 s and 60.3 vs 52.8 tok/s) while bringing the whole architecture:
   four hot sibling forks on a 67.7K template before and after a restart (1.8-2.0 s / 2.5-2.9 s),
   warm arrival in both orders, a 2.9 GB restore in 4.2-5.0 s / 16.6-17.1 s with a flipped byte
   refused. Five defects that only the hardware showed - cooperative grids sized for 170 SMs, a
   prompt-attention CTA that spilled under Ada's register cap, a DirectStorage queue that could
   not overlap streamed batches - are fixed at source. The RTX 4090 profile is two device-state
   slots (four leave 169 MiB of WDDM budget and the driver pages).
   **Qualifying those candidates is in flight (2026-09-09, EXP-026).** The release path around
   the port had never run: five blockers are fixed (the bench had no `--version` arm the
   package's identity binding needs; the package relayed through the operator's Mac at
   0.33 MB/s instead of host to host at 104.7 MB/s; the staging root inherited `BUILTIN\Users`
   write access; the managed install splatted positionally; and mainline applied
   `X-NInfer-Session` only on the bodyless Responses routes, so the lane probe's identity
   conflict returned 200), and both lanes now reach the protocol phase. The RTX 4090 lane's
   Host KV pool is halved to 4 GiB because the controller's 18 GB pre-launch read leaves no
   free pages for 13.3 GB of pinned memory; both lanes keep 24 host state slots because at 8
   the protocol's post-delete continuation hits a runtime invariant defect.
   **The RTX 4090 candidate is qualified (2026-09-10, EXP-027).** Running the phases past
   `protocol` for the first time exposed two more defects, both fixed and re-proven: admission
   refused a legitimate request whose only reuse source was a long anchor shared with a sibling,
   because the guard measured exclusive ownership rather than residency
   ([ninfer#37](https://github.com/alphastorm/ninfer/issues/37)); and the restart phase could
   not observe durability, because its seed session was below the 32,768-token automatic
   checkpoint gate and a Windows managed stop terminates the server instead of signalling it,
   so nothing was ever published. The candidate (`6912a15c`) then passed 15/15 phases: exact
   130,048-token retrieval in 91.6 s, C1 2,101.6 tok/s prefill and 159.0 tok/s decode at 93.0%
   MTP acceptance, bidirectional rollback, the state-security set, the OMP golden run exact, a
   310 MB checkpoint restored across a managed restart, and the same fifteen protocol checks at
   a third of the shipped Host StateImage pool. Running the registered suite with the artifact
   exported then found a third defect, fixed at `075d442e`: the engine delivered a result and
   woke its waiter before releasing the lane and republishing statistics, so a consumer
   returning from `wait()` could still see its own request as live
   ([ninfer#38](https://github.com/alphastorm/ninfer/issues/38)); red at the port base on a
   real rebuild, green after, 101/101 with the artifact. Shipped as `v0.6.0` on 2026-09-10.
   **The managed stop now flushes (2026-09-10, EXP-028; unreleased).** The finding EXP-027 left
   open was that a managed stop on Windows terminates the server, so a session that was never
   published did not survive a deliberate stop. The manager now mints one manual-reset kernel
   event per launch, the server creates it (refusing a squatted name, admitting only `SYSTEM`
   and `Administrators`) and stops on it: listener closed, in-flight requests finished, every
   live session saved. Measured on the RTX 4090 with a 43-token session and the automatic gate
   at its default 32,768: the candidate exits in 0.74 s having saved it and restores it exactly
   after a restart, where the shipped binary loses it and answers 404. The channel is a
   per-release capability, so a rollback to `v0.6.0` is still stopped by termination. **That
   candidate is qualified, reviewed, and shipped as `v0.6.1` (2026-09-10, EXP-029):** 15/15 lane phases
   at `63f28c95` and 103/103 registered tests, with a 45-token session that nothing ever
   published coming back exactly after a graceful managed restart, both rollback directions
   stopped the way their own records declare, and the shipped numbers unchanged (130,048-token
   retrieval in 91.4 s, 2,105 tok/s prefill, 159.1 tok/s decode). Seven candidate windows: the
   lane found six defects in the lifecycle handoff - the moment a gracefully exiting wrapper
   hands the lifecycle back, which never existed while stops were terminations - and two rounds
   of independent focused review confirmed eight more, the worst being an installer that
   silently stripped the capability from every existing record. Three recurring classes are
   closed with executable invariants. **The RTX 5090 lane's mainline candidate is qualified and
   shipped as `v0.6.2` (2026-09-11, EXP-030):** the same commit `63f28c95` built for the
   container lane holds 7/7 of that lane's gates on the owner appliance under the unchanged
   v0.4.8 context-cache arguments - 8/8 sibling forks on the shared anchor at 57.9K and 67.7K
   before and after a restart, warm arrival in both orders, a 5.2 GB restore in 3.6-4.0 s with a
   flipped byte refused - and every gate a published artifact can answer was re-run against the
   image pulled anonymously by digest (2,169.9 tok/s prefill, 132.53 tok/s decode, the agent
   protocol across a restart), so all three lanes now serve from one runtime tree.
   The RTX 3090 lane then waited for its host and a separate release; it is now qualified
   and accepted on the native runtime in v0.9.1
   ([lane qualification](releases/v0.9.1/qualification/rtx3090.json) ·
   [documented routes](releases/v0.9.1/acceptance/documented-routes.json)). The earlier receipts are
   ([EXP-028](docs/measurements/2026-09-10-native-managed-stop-flush.json) ·
   [EXP-029](docs/measurements/2026-09-10-rtx4090-graceful-stop-qualification.json) ·
   [EXP-030](docs/measurements/2026-09-10-rtx5090-v062-qualification.json) ·
   [published image](docs/measurements/2026-09-11-rtx5090-v062-public-image-gates.json)).
   Receipts:
   [qualification](docs/measurements/2026-09-08-rtx5090-v051-qualification.json) ·
   [warm arrival](docs/measurements/2026-09-08-warm-arrival-rtx5090-candidate.json) ·
   [restore](docs/measurements/2026-09-08-restore-probe-rtx5090-candidate.json) ·
   [EXP-021](docs/measurements/2026-09-07-warm-arrival-rtx5090.json) ·
   [4090 on mainline](docs/measurements/2026-09-08-rtx4090-mainline-profile-gates.json) ·
   [3090 on mainline](docs/measurements/2026-09-08-rtx3090-mainline-profile-gates.json) ·
   [lane qualification](docs/measurements/2026-09-09-native-lane-qualification-blockers.json) ·
   [4090 qualified](docs/measurements/2026-09-10-rtx4090-native-lane-qualification.json).
3. **Fleet routing — configuration published and the fixed workload measured 2026-09-05.**
   [`examples/fleet/`](examples/fleet/) is one OMP configuration spanning the three lanes with
   explicit roles (`local-main` on the RTX 5090, `local-heavy` on the RTX 4090, `local-scout` on
   the RTX 3090), fail-closed tunnels, and two role agents. The fixed workload is the frozen
   24-request agent corpus as 14 independent jobs, dispatched by
   [`scripts/fleet_dispatch.py`](scripts/fleet_dispatch.py) with one active request per lane.
   Measured boundary (batch completion, two repetitions each, all jobs completed): the RTX 5090
   alone 66.8 s; two machines (5090+4090) 51.2 s with naive longest-first dispatch and **43.4 s**
   (1.54×) with cost-aware assignment from the lanes' measured per-scenario costs; three machines
   47.2 s naive and **32.3 s** (2.07×) cost-aware, with all three lanes balanced within 2 s of
   busy time. Pinning jobs to lanes by role alone is a loss (100.3 s, 0.66×): the long-prefill
   jobs cost 14.9 s on the 5090 but 48.6 s on the 4090 and 91 s on the 3090, while short chat
   jobs cost about the same everywhere - so roles describe what a lane is for, and the cost model
   decides where work goes. No fleet claim beyond this workload; outputs are not comparable across
   lanes (different KV formats), and the 4090's same-process output variation recorded on
   2026-09-04 recurs here. Receipts: [`docs/measurements/2026-09-05-fleet-dispatch-*.json`](docs/measurements/)
   (EXP-016).

Parked until >131,072-token contexts matter: paged host-to-device KV prefetch and the
E8-lattice/RotorQuant ceiling work the family ports carry upstream.

## Path to v1.0

A public release does not imply a v1.0 or SLA commitment. v1.0 means the durability contract —
save is atomic and verified, restore is verified-or-refused, sessions survive process death, and
private state never crosses sessions — holds under independent eyes, not just owner receipts.
Before a v1.0 decision:

- gather clean-install and rollback evidence from multiple independent owners for each claimed
  GPU profile;
- sign the Windows packages and notarize the macOS client, or retain the explicit unsigned
  boundary;
- close the highest-signal public-release installation and compatibility failures;
- publish supported upgrade and security-fix windows, rollback ownership, and response-time
  expectations without implying an SLA;
- run the fixed two-machine workload before making any fleet completed-work claim; and
- cut a new release candidate if any executable component, model, configuration, or support
  boundary changes.

Explicitly not on this path (a new product decision, not a milestone): multi-tenant serving,
priority or preemptive scheduling, universal hardware claims, and silent cloud fallback.

## Shipped

Each release keeps its immutable manifest and receipts; summaries here, details in
[release status](docs/RELEASES.md) and [`CHANGELOG.md`](CHANGELOG.md).

| Release | What landed |
| --- | --- |
| `v0.9.1` | RTX 3090 native Windows lane: v0.6.2 component, source `f08309da`, all 15 lifecycle phases passed; exact 130,048-token retrieval in 221.0 s and C1 decode 102.64 tok/s at 93.43% MTP acceptance under 300 W; rollback reads older release configurations safely, OMP limits the RTX 3090 to one request, and acceptance compares scheduled-task definitions and enabled state; five documented routes passed 31 steps, all three hosts restored; RTX 5090 and RTX 4090 components, profiles, model and memory floors unchanged; fleet scout role and upstream engine merge remain deferred |
| `v0.8.3` | Faster RTX 5090 decode: v0.6.12 tensor-core Q5 verify route, +4.4% at 26K / +3.6% at 60K / +6.3% at 1,024 tokens; rounds 3.5-4.9% shorter; 58 of 89 role-corpus outputs differ; EXP-063 paired redaction screen passed (504 pairs); gates re-measured on the published image; RTX 4090, client, model, profile and configuration unchanged; all four documented routes passed (24 steps), both hosts restored; v0.8.2 checkpoints re-prefill once on the new RTX 5090 build; RTX 3090 deferred |
| `v0.8.2` | GPU keep-warm: RTX 5090 v0.6.11 and profile `qwen38-5090-v0.8.2` add `--gpu-keep-warm-ms 60000`; 0.155-0.157 s prefill after 12-58 s idle versus 0.253-0.304 s without it; about 71 W while held, about 2.3 W average over logged traffic (EXP-062); RTX 4090, client, model and memory floors unchanged; all four documented routes passed (24 steps), both hosts restored; v0.8.1 checkpoints re-prefill once on the new RTX 5090 build; RTX 3090 deferred |
| `v0.8.1` | Faster decode: RTX 5090 +10.3-11.0% with identical outputs; RTX 4090 native C1 157.89 vs 153.54 tok/s with one-row split2 kernels retained (EXP-055); every runtime gate re-measured on published components; all four documented routes accepted (24 steps); client, model, settings and floors unchanged; v0.8.0 checkpoints re-prefill once; RTX 3090 deferred |
| `v0.8.0` | Unmodified upstream OMP 18.3.0; durable stock-client sessions across graceful restarts (EXP-053); shared-prefix reuse for new sessions; RTX 5090 v0.6.9-beta.2 and RTX 4090 native v0.6.7-beta.2 qualified and accepted through the documented routes; model and settings unchanged; RTX 3090 deferred |
| `v0.7.4` | Durable sessions on both mainline lanes (source 1c17c3fa; RTX 5090 v0.6.8, RTX 4090 native v0.6.6): refused automatic saves retry, admission saves a session's newest turn before evicting it, and re-saving under the checkpoint quota no longer deletes other sessions' only checkpoints; the graceful-stop workload went from `refused 2` to `saved 1, nothing to save 3, refused 0` with all four sessions resumed (EXP-050/EXP-051); client, model and settings carried from v0.7.3; RTX 3090 still deferred |
| `v0.7.3` | Client-only repin to OMP 18.2.3 (`omp-18.2.3-cross-platform-beta-1`) for the RTX 5090 and RTX 4090 lanes: macOS, Windows and Linux clients passed live inference and a fresh 24-step documented-route acceptance; runtime, model and settings carried from v0.7.2; RTX 3090 deferred until its host returns |
| `v0.7.2` | Bounded restore reclaim on both mainline lanes (source d125ffff): restore saves and reclaims checkpoint-backed resident sessions under host-KV pressure, so both RTX 5090 ceiling sessions resume after a restart, and on the RTX 4090 a pool sized for one ceiling session restored two (EXP-047) |
| `v0.7.1` | The RTX 4090 native lane can restore its own ceiling-sized sessions (host-KV pool 4096 to 11264 MiB with a declared 32,768 MiB host floor), an export is refused when the configuration could not restore it, and a declined restore names its gate (EXP-043/EXP-044) |
| `v0.7.0` | Two sessions at the 131,072-token ceiling keep prefix reuse on one card (Host KV pool 8 to 16 GiB, KV dtype unchanged after both 8-bit dtypes were rejected on the private corpus); the profile declares and the launcher enforces the runtime-host memory that pool needs; the two-session restore boundary is measured and named (EXP-041) |
| `v0.6.10` | The documented container route refuses a launch whose bind mounts the engine cannot stage - proven inside a throwaway container before the 18 GB load - and both post-reboot failure signatures are named with recreation as the recovery; no component changed, both RTX 5090 routes re-run (EXP-040) |
| `v0.6.9` | Both mainline lanes on source 696e78c7: independent Qwen parser semantic port, malformed-region and deep-union remediation, preserved custom/history/stream contracts; both lane qualifications and published-component acceptance passed |
| `v0.6.8` | Both mainline lanes on source 68a0722f: RTX 5090 runtime v0.6.4 and RTX 4090 native v0.6.2-beta.1; the live-sibling continuation 500 fixed at source (ninfer#43); GDN gating grids partitioned by device residency; the 4090 C1 fixture's trajectory sensitivity measured and recorded (EXP-037) |
| `v0.6.7` | RTX 5090 runtime v0.6.3: selective backport of 18 upstream engine commits (MoE/GDN/vocab kernels, sparse-MoE and GDN record fixes, cpp-httplib 0.54.1), every lane gate within noise of v0.6.2; the deferred upstream families named with reasons |
| `v0.6.6` | The config every documented route installs keeps the pinned client on its channel: no out-of-channel `omp update` advice; every client-installing route re-run and the setting read back from the installed client; no component changed |
| `v0.6.5` | The quickstart's primary macOS route runs verbatim from its own blocks with shell-decided outcomes, including a server restart with the session continued; every documented route is now runner-covered; no component changed |
| `v0.6.4` | Every documented Windows route runs verbatim from its own quickstart blocks on a stock host; a clone yields the recorded bytes on every platform; no component changed |
| `v0.6.3` | The documented public RTX 5090 route mounts a durable session store and declares the identity of the configuration it runs; no component changed |
| `v0.6.2` | The RTX 5090 container lane on the mainline runtime: all three lanes built from one commit, requalified 7/7 on the owner appliance and re-verified against the anonymously pulled image, numbers within run-to-run noise of v0.5.1 |
| `v0.6.1` | A managed stop of the RTX 4090 native lane saves every live session: the manager signals a per-launch named kernel event, the server flushes and reports, the controller records a stop that lost state; the capability lives in each release's record so a rollback to v0.6.0 still terminates |
| `v0.6.0` | The RTX 4090 native lane on the mainline runtime: the RTX 5090's context-cache architecture built for Ada, requalified 15/15 through its own lifecycle tool |
| `v0.4.8` | Each lane on its own best measured configuration: RTX 5090 context-cache profile (sibling forks keep the base anchor), RTX 4090 prefill chunk 2,048, RTX 3090 131,072-token context; every lane requalified on its rig and accepted from public URLs |
| `v0.4.7` | Corrected immutable runtime asset URLs from v0.4.6; component bytes unchanged |
| `v0.4.6` | Checkpoint-origin authentication for future cross-machine replication; 4090/3090 components rebound unchanged |
| `v0.4.5` | RTX 3090 joined the durable train with automatic saves, explicit checkpoints, restart qualification, and fanout support |
| `v0.4.4` | RTX 5090 checkpoint export decoupled from the engine with bounded writes, sustained-idle saves, and lazy restore repair |
| `v0.4.3` | RTX 5090 fanout anchors (sibling branches reuse the base prefill), checkpoint-import integrity (streamed re-hash, fail-closed, quarantine), constant-time credential checks, session isolation hardening |
| `v0.4.2` | RTX 4090 lane moved to the durable v0.2 package: 102,075 tokens restored onto a fresh process, chunked KV restore, hardened D3D12 residency, MTP K=15 capacity (MTP3 shipped arm) |
| `v0.4.1` | RTX 5090 checkpoint-store hardening: health-gated quota transitions, named skip reasons, post-publish reclamation acknowledged |
| `v0.4.0` | Durable RTX 5090 container: transactional session checkpoints, 109,589 tokens restored hot across a docker restart, exact retrieval at 130,448 tokens |
| `v0.3.1` | RTX 4090 MTP3 promotion (+17.04% complete Golden-equivalent wall time) and the draft-depth sweep |
| `v0.3.0` | First public release: one exact install lane per qualified GPU profile, `Latest` on GitHub |
| `v0.2.x` | Managed lifecycle (doctor/plan/install/status/benchmark/checkpoint/rollback/support-bundle), native OMP 18.0.9 clients for macOS/Windows/Linux, durable native-Windows checkpoints, RTX 3090 parity campaign |
| `v0.1.0-beta.1` | Restricted RTX 5090 beta: exact manifest, external clean install from public URLs |

Standing support boundaries: owner-operated exact profiles with no SLA; two requests in flight
on the RTX 5090 and one on each RTX 4090 and RTX 3090 native lane; JSON-schema structured output
rejected rather than ignored; the unattended RTX 3090 evidence role disabled; no multi-GPU,
multi-tenant, priority, or preemptive scheduling claim; no universal throughput, latency, or
hardware claim; no silent cloud fallback; measured numbers apply only to the recorded package,
machine, and profile.

The remaining expensive-to-add-later items stay explicit rather than hidden release debt:

- adopt the shared native-Windows source-first qualification sequence in
  [the release process](docs/RELEASES.md#next-native-release-sequencing);
- notarized macOS distribution and a first-party Windows signing path;
- a public, hardware-independent acceptance runner shared by all client releases;
- JSON-schema constrained decoding only if the runtime can enforce rather than ignore the
  contract;
- concurrency-qualified 3090/4090 profiles after memory and latency gates exist for those exact
  packages;
- a dependency-level SBOM for the 4090 package beyond its complete file inventory;
- a doctor-level WSL networking-mode and loopback-reachability preflight for the Windows Docker
  profiles ([#15](https://github.com/alphastorm/omp-ninfer/issues/15)); and
- a fixed two-machine workload before any fleet completed-work or throughput claim.

## Upstreaming to Oh My Pi

Through v0.7.4, the pinned client carried the NInfer stateful-Responses provider integration
in the public [alphastorm/oh-my-pi](https://github.com/alphastorm/oh-my-pi) fork; the intent was
to upstream reusable provider semantics and appliance plumbing. v0.8.0 instead uses the
unmodified [upstream OMP 18.3.0 binary](https://github.com/can1357/oh-my-pi/releases/tag/v18.3.0).
This product no longer builds or publishes a client. Stock OMP has no `omp appliance` commands;
the documented container and native Windows routes own lifecycle.

## Continuous — performance program

Kernel and schedule optimization runs alongside releases, in public, with an auditable experiment
ledger and an open ideas backlog: [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md). Candidate areas
include prefill, decode, MTP acceptance and verification cost, Vision, KV storage, weight paging,
and long-session continuation. No optimization result becomes part of a release until its exact
binary and profile are rebound through a new qualification receipt.

Next engine campaign: DFlash2 on the RTX 5090. Upstream NInfer's DFlash2 backend decoded the role
corpus 28.2% faster than MTP3 on the same binary at one request, with prefill unchanged, for 1.65
GiB of weights ([EXP-078](docs/measurements/2026-09-30-dflash2-rtx5090.json)). Ported onto the
fork's runtime with upstream's verify attention route for the 27B's 24 query heads, it decodes the
corpus 21.4% faster than shipped v0.9.0 and 13.6% faster than upstream's DFlash2 at one request,
with MTP3 byte-identical ([EXP-081](docs/measurements/2026-09-30-dflash2-verify-route-rtx5090.json));
without that route the first port slowed with context
([EXP-079](docs/measurements/2026-09-30-dflash2-fork-spike-rtx5090.json)). With two requests'
16-column verify on the fork's Q5 tensor-core route, a pair decodes 420.86 tok/s together in
22.7 ms rounds, 8.4% above shipped's pair
([EXP-082](docs/measurements/2026-10-01-dflash2-pair-q5-tensor-cores-rtx5090.json)). DFlash2
sessions keep the durable store: the draft context ring rides every checkpoint, a restored
session decodes its next turn exactly as the exporting engine does, and 58K-token sessions
restore hot across restarts with MTP3 byte-identical
([EXP-083](docs/measurements/2026-10-01-dflash2-durable-store-rtx5090.json)). At two requests with
BF16 KV DFlash2 left 131,520 KV tokens and two device state slots where v0.9.0 has 160,256 and
four. Upstream's NVFP4 KV, ported with every BF16 path unchanged, gives the two-request DFlash2
profile four slots and 262,144 KV tokens, rounds 12-27% shorter behind 32K-120K tokens, hot
restores from 1.66 GB checkpoints and shipped's reuse, with MTP3 byte-identical
([EXP-084](docs/measurements/2026-10-01-dflash2-nvfp4-kv-rtx5090.json)). A pre-registered,
powered quality screen (1,120 paired prompts per arm against shipped MTP3) then passed DFlash2
with BF16 KV, whose outputs were 1,091 of 1,120 byte-identical to shipped's, and failed NVFP4 KV
on unsupported claims and secret leaks
([EXP-085](docs/measurements/2026-10-01-dflash2-powered-quality-screen-rtx5090.json)). The fork's
existing FP8 KV gives the profile four slots and 249,216 KV tokens with long-context rounds 7-18%
shorter and exact 130K retrieval
([EXP-087](docs/measurements/2026-10-01-dflash2-fp8-kv-precheck-rtx5090.json)), but it failed the
same screen on secret leaks, 604 against 561
([EXP-088](docs/measurements/2026-10-01-dflash2-fp8-kv-quality-screen-rtx5090.json)). The
quality-cleared DFlash2 profile is BF16 KV at two device state slots and 131,520 KV tokens, and
v0.10.0 adopts it on the RTX 5090. It passed v0.9.0's probes, but free-form reasoning decodes
2-5% slower than MTP3 at one request and 21-27% slower at two, and one of two sessions lost its
reuse across a restart
([EXP-086](docs/measurements/2026-10-01-dflash2-pre-acceptance-probes-rtx5090.json)); the
candidate's qualification window measures both. The RTX 4090 and RTX 3090 stay on MTP3: the port
does not link for their architectures and would not fit 131,072 tokens in 24 GB
([EXP-089](docs/measurements/2026-10-01-dflash2-native-lanes-feasibility.json)). After v0.10.0,
one verify attention pass per layer and the pair's mixer outputs on the tensor cores shorten
DFlash2 rounds 8-19% behind 32K-120K tokens and 8% in pairs with both role corpora byte-identical,
and K=15 drafting does not pay
([EXP-092](docs/measurements/2026-10-03-dflash2-round-costs-rtx5090.json)). The next round cost,
the SIMT query/key projections, has no faster byte-identical schedule
([EXP-093](docs/measurements/2026-10-03-q4-query-key-schedules-rtx5090.json)); on the tensor cores
they take another 0.8 ms off every one-request round and 1.9 ms off a pair's, and the outputs
they change pass the powered screen
([EXP-094](docs/measurements/2026-10-03-q4-query-key-tensor-cores-rtx5090.json)). Both await an
RTX 5090 candidate.

## How to help right now

- **Run OMP with subagents against a lane?** That fanout path is exactly what v0.4.3 changed —
  file a [hardware report](https://github.com/alphastorm/omp-ninfer/issues/new?template=hardware-report.yml)
  with what you observe, pass or fail.
- **Measured something?** Submit the
  [performance result form](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml)
  for the [community results table](docs/BENCHMARKS.md#community-results).
- **CUDA/kernel work?** Claim an idea from the
  [performance backlog](docs/PERFORMANCE.md#ideas-backlog).
- **RTX 3090, 4090, or 5090 owner?**
  [`Get started`](docs/QUICKSTART.md) with the matching published lane, then file a content-safe
  [hardware report](https://github.com/alphastorm/omp-ninfer/issues/new?template=hardware-report.yml)
  or [clean-install report](https://github.com/alphastorm/omp-ninfer/issues/new?template=clean-install-report.yml).
  Pass and fail reports both improve the observed matrix; one lane never authorizes package
  substitution in another.
