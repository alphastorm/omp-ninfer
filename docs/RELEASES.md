# Releases

OMP NInfer versions the integrated product. Component repositories keep their own versions and tags;
the product manifest binds the exact combination.

## Channels

| Channel | Meaning | Current state |
| --- | --- | --- |
| Public release | Published exact profiles with stated limitations and non-claims | `v0.10.0`, GitHub `Latest` |

Prereleases never take GitHub `Latest`; `Latest` always points at the current public release.
The historical fork client used separate `omp-beta` and stable `omp` Homebrew casks through
v0.7.4. v0.10.0 uses upstream OMP 18.4.10 binaries and no client cask.
All five documented routes and fresh platform-client acceptance passed on the published
components; see [route acceptance](QUICKSTART.md#v0100-route-acceptance).

### Post-v0.4.7 development evidence (shipped in v0.4.8 where noted)

The corrected 2026-09-04 agent-shaped MTP0/3/5/7 campaign changes no released component or
profile. MTP3 was fastest on every lane and in both repetitions; K5/K7 were 13.57%/24.72% slower
on RTX 5090, 7.29%/20.17% slower on RTX 4090, and 11.34%/22.46% slower on RTX 3090. Analysis
revision 5 therefore retains the qualified MTP3 incumbent and rejects deeper drafting for the
current artifacts. Missing campaign and fresh-process MTP0 controls leave exact-output attribution
unresolved, but do not invalidate this no-change throughput decision. Public receipts:
[5090](measurements/2026-09-04-rtx5090-mtp-agent-ablation.json) ·
[4090](measurements/2026-09-04-rtx4090-mtp-agent-ablation.json) ·
[3090](measurements/2026-09-04-rtx3090-mtp-agent-ablation.json).

## Version identities

### v0.11.0 ready candidate — RTX 5090 only, product publication pending

The [release notes](../releases/v0.11.0/NINFER_RELEASE_NOTES.md) select runtime source
`1302d63929e400a05e1c9cdb0fc8003a70269825` by the founder's 2026-10-10 decision:
EXP-092/094 without `3a2fadbd`. Full sm_120a ctest is 111 pass/7 skip/0 fail and
[all 15 local lane criteria](../releases/v0.11.0/qualification/option-c-lane.json) pass.
The superseded `a59c13d0` alternative, its red NVFP4 oracle and invalid attempts
remain evidence, not hidden exceptions. The client is unmodified upstream OMP 18.8.7.
The founder completed the live component cut at 13:46Z; workflow 38057050899 succeeded,
and Main measured anonymous image `6a02feba` / server `548fe239`. The real OCI digest
is recorded in the published runtime receipt; no local image ID was substituted.

All three retained RTX 5090 routes, 17 documented steps and three stock clients passed
on `5861712f561ff0b3100dd4350e02d777a3f5007e`, with 385.948 s measured downtime and
independent restoration. Composition and immutable pins bind that existing proof;
metadata/prose commits do not advance the subject or alter the executed blocks.
Product publication remains founder-only; production was not upgraded.

Both native lanes are deferred. Owners use the complete immutable v0.10.0 guide,
OMP 18.4.10 and its manifest/fragments; the co-installed RTX 3090/RTX 4090 host is
unsupported by unmodified single-visible-GPU packages. Both lanes require multi-GPU
support and fresh acceptance in a later release, without an environment shim.
The notes retain the completed cut → staging → acceptance sequence and the remaining
founder-only product publication command.

### v0.10.0 public release — DFlash2 on the RTX 5090

The 2026-10-02 release changes the RTX 5090 runtime, model and profile and moves every client
platform to unmodified upstream OMP **18.4.10**. RTX 4090 and RTX 3090 keep their runtime
packages, native model and serving profiles; their client and product pins change.

| Lane | Component tag | Bytes | Server | Source | Profile / configuration |
| --- | --- | --- | --- | --- | --- |
| RTX 5090 | `v0.6.15-qwen38-5090-beta.1` | image `sha256:fff4ee38…` | `7a8908e8` | `eaf221ac` | `qwen38-5090-v0.10.0` / `8b2f4959`; two requests in flight |
| RTX 4090 (runtime unchanged) | `v0.6.10-qwen38-4090-beta.1` | package `a0ea4c81` (574,717,115 bytes) | `e0498fad` | `cba7eb93` | `qwen38-4090-native-v0.6.10-beta.1` / `7a69481f`; one request |
| RTX 3090 (runtime unchanged) | `v0.6.2-qwen38-3090-beta.1` | package `da1d62f2` (595,676,373 bytes) | `11b3f93c` | `f08309da` | `qwen38-3090-native-v0.6.2-beta.1` / `0f700667`; one request |

RTX 5090 uses DFlash2 K=7, BF16 KV, **131,520 KV tokens**, a **131,072-token context ceiling**
and **two device state slots**. Both prompts plus output reservations must fit; the pending
timeout is 180 s. Model `0634abb0` is 20,437,336,576 bytes at revision
`dc370fb6295ae8b786e1af4f90d7142a16255c35`; the native lanes retain model `eec39564`.
The RTX 5090 runtime fingerprint and model change, so predecessor checkpoint reuse is not
claimed. Use the new manifest and quickstart together, not a generic `omp update`.

The [RTX 5090 profile receipt](../releases/v0.10.0/qualification/rtx5090.json) records exact
**130,048-token retrieval in 58.738 s** and **161.39 decode tok/s** (159.92 completion tok/s
wall-clock for 2,048 output tokens). The fourth candidate restored both 62,404-token sessions
in all three restart repeats. Criterion 14 passed under the founder-approved
[proof amendment #74](https://github.com/alphastorm/omp-ninfer/pull/74) and a fresh rerun;
the two failed original limit-2 runs remain failures, preserved in the lane record. The profile
window used a package-local build and stock OMP 18.4.0; fresh published-image/OMP 18.4.10
acceptance is distinct evidence, not a relabeling of that window.

All **five documented routes, 31 steps** passed on candidate
`ca9298222ed09f84e3c0e15ff6ef75218d942fb0` with unmodified upstream OMP **18.4.10**, published
RTX 5090 image `fff4ee38`, RTX 4090 package `a0ea4c81` and RTX 3090 package `da1d62f2`.
The receipts record the pre-cut substitution of that commit for the not-yet-created tag and
an installable check for the ready check; the executable blocks are otherwise bound by hash.

| Route | Steps | Sum of step elapsed seconds | Recorded environment | Receipt |
| --- | ---: | ---: | --- | --- |
| RTX 5090 container host | 2 | 54.869 | Ubuntu 24.04.4 LTS under Windows Docker Desktop/WSL2 | [run](measurements/2026-10-02-v0100-rtx5090-container-host-run.json) |
| RTX 5090 macOS client | 10 | 108.626 | macOS 27.0.1 arm64 | [run](measurements/2026-10-02-v0100-rtx5090-macos-client-run.json) |
| RTX 5090 Windows client | 5 | 48.258 | Windows 11 Pro | [run](measurements/2026-10-02-v0100-rtx5090-windows-client-run.json) |
| RTX 4090 native Windows | 7 | 418.322 | Windows 11 Pro | [run](measurements/2026-10-02-v0100-rtx4090-native-run.json) |
| RTX 3090 native Windows | 7 | 1,142.220 | Windows 11 Pro | [run](measurements/2026-10-02-v0100-rtx3090-native-run.json) |

These are sums of the recorded step timers, not end-to-end installation durations. Both native
routes performed fresh canonical upgrade installations after preserving the active published
instances; they do not establish an idempotent-reinstall claim.
[Documented routes](../releases/v0.10.0/acceptance/documented-routes.json) ·
[RTX 4090 public install](../releases/v0.10.0/acceptance/rtx4090-public-install.json) ·
[RTX 3090 public install](../releases/v0.10.0/acceptance/rtx3090-public-install.json).

The upstream macOS arm64, Windows x64 and Linux x64 binaries each passed an authenticated typed
tool turn, exact continuation and fail-closed request against the published RTX 5090 image
([composed acceptance](../releases/v0.10.0/acceptance/composed-external-installation.json)). macOS remains preview:
the upstream client has no managed installation or appliance lifecycle. Linux ran under Ubuntu
WSL2, not a separately qualified non-WSL Linux OS. Vision passed on the RTX 5090; native lanes
remain text/tools. All observations are maintainer-operated, not independent external-user
installation or repeat-use outcomes.

The RTX 5090 window passed on its **first attempt**, in the c2 workspace, from the maintainer's
Apple silicon workstation over the tailnet, with production downtime at most **387.499 s
(6.5 min)**. The earlier candidate `20a75bd5` failed both native routes on the native-model
block before any install effect. On the accepted candidate, RTX 4090 passed in **attempt c4**
after two refusals before any install effect: staged-model timestamps changed by the first
candidate's resumed download, then an interactive GPU owner (Desktop Window Manager above
1 GiB, with nobody signed in). RTX 3090 passed in **attempt c5**, with the console signed out,
after refusals for an interactive GPU owner (NVIDIA Overlay on the signed-in console).
All hosts were restored after every attempt; the accepted runs' receipt records the original
RTX 5090 runtime healthy, native state and task definitions unchanged, and no production upgrade
activated ([restoration](measurements/2026-10-02-v0100-acceptance-restoration.json)).

Checkpoint saves remain best effort under traffic, and the multisession control lost warm reuse
on 2/8 continuations/forks. Two requests in flight provide neither preemption nor universal warm
reuse; predecessor performance is not a speed-up baseline for this runtime/model. Native starts
refuse any GPU owner holding at least 1 GiB. RTX 3090 rollback remains proven against its
**unpublished v0.6.0-beta.1** predecessor, whose stop is a termination. Native lanes are
text/tools; vision remains RTX 5090 only. The fleet RTX 3090 scout role and upstream engine
merge remain deferred. Owner-operated exact profiles only; no SLA.

[Release notes](../releases/v0.10.0/NINFER_RELEASE_NOTES.md) ·
[Manifest](../releases/v0.10.0/manifest.json) · [Qualification](../releases/v0.10.0/qualification.json).

### v0.9.1 historical public release — RTX 3090 on the native Windows runtime

The 2026-10-01 lane release adds **RTX 3090 native Windows** with the unmodified upstream
OMP 18.4.0 client. RTX 5090 and RTX 4090 components, profiles, model and memory floors are
byte-identical to v0.9.0. The three runtime identities are:

| Lane | Component tag | Bytes | Server | Source | Profile / configuration |
| --- | --- | --- | --- | --- | --- |
| RTX 5090 (unchanged) | `v0.6.14-qwen38-5090-beta.1` | image `sha256:4c816b0c…` | `f62a570e` | `e20060b6` | `qwen38-5090-v0.9.0` / `cf1de114`; two requests in flight |
| RTX 4090 (unchanged) | `v0.6.10-qwen38-4090-beta.1` | package `a0ea4c81` (574,717,115 bytes) | `e0498fad` | `cba7eb93` | `qwen38-4090-native-v0.6.10-beta.1` / `7a69481f`; one request |
| RTX 3090 (new) | `v0.6.2-qwen38-3090-beta.1` | package `da1d62f2` (595,676,373 bytes) | `11b3f93c` | `f08309da` | `qwen38-3090-native-v0.6.2-beta.1` / `0f700667`; one request |

RTX 3090 source `f08309da` is the RTX 5090 runtime's `e20060b6` plus one controller fix,
built for sm_86. Its managed scheduled task, protected state root, graceful stop that saves
live sessions, durable checkpoints and rollback follow the RTX 4090 lifecycle. The profile
serves **one request at a time**, with a **30 s** pending timeout, **131,072 tokens of INT8
KV with MTP3**, an **8192 MiB** host-KV pool and **24 host-state slots**. Keep-warm is off;
no host-memory floor is declared because the lane was qualified on one host. While serving,
the GPU-owner controller holds the card at **300 W**, restoring the owner's **370 W** limit
on stop. Both native lanes are text/tools; vision remains an RTX 5090 container capability.

The [RTX 3090 lane receipt](../releases/v0.9.1/qualification/rtx3090.json) records the
qualified package on the physical RTX 3090:

- **130,048-token retrieval was exact in 221.0 s** at the 131,072-token ceiling.
- C1 reached **102.64 tok/s decode** and **93.43% MTP acceptance**, with peak power
  **299.92 W** under the 300 W cap. This trajectory-sensitive fixture has no like-for-like
  predecessor on this lane; no speed-up over the historical v0.7.2 RTX 3090 route is claimed.
- Restart took **104.5 s**, including a managed-stop flush of an unpublished session.
- Rollback passed in both directions against the lane's **unpublished v0.6.0-beta.1** package.
  That predecessor predates the stop-event channel, so its stop is a termination.
- Protected state refused two low-privilege reads; the 15-check agent protocol passed at the
  shipped host pool and with 8 host-state slots, as did the unmodified OMP 18.4.0 typed tool call.

The first qualification window, on `e20060b6`, failed rollback because the shared Windows
controller read `context_cache.host_kv_mib` under PowerShell strict mode from a predecessor
configuration that did not declare it. Source `f08309da` passes `--host-kv-mib` only when
the release's own configuration declares the field. Every published RTX 4090 package declares
it, so the unchanged RTX 4090 lane was never exposed.

From v0.9.0, RTX 5090 and RTX 4090 owners change nothing: the OMP binary, `models.yml`,
`PI_OPENAI_STATEFUL=1` and their launch remain unchanged. RTX 3090 owners follow the
[quickstart](QUICKSTART.md) and merge `ninfer-native-3090: 1` under
`providers.maxInFlightRequests` in `~/.omp/agent/config.yml`, as the shared
[fail-closed config](../examples/manual-tunnel/fail-closed.yml) now does. OMP leaves an
unlisted provider unlimited; excess requests wait at the server and can expire after 30 s.
All three lanes serve the unchanged model artifact `eec39564…`.

All five documented routes passed **31 steps** on candidate `c55185dd`
(`c55185dd39cbdb440620721c2a9d0dc06de010f4`) with unmodified OMP 18.4.0 and the published
components: RTX 5090 container host 2, macOS client 10, Windows client 5, RTX 4090 native
Windows 7 and RTX 3090 native Windows 7; all three hosts were restored. The upstream macOS
arm64 (preview), Windows x64 and Linux x64 binaries each passed a typed tool turn, an exact
continuation and a fail-closed request against image `4c816b0c`. Linux ran under **WSL2**,
not a separately qualified Linux OS. macOS remains preview without a managed installation
or appliance lifecycle.
[Documented routes](../releases/v0.9.1/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.9.1/acceptance/composed-external-installation.json).

Both native lanes installed from their public assets. The RTX 3090 documented route performed
a **fresh canonical upgrade installation** of the published package after preserving the active
qualified instance; all moved originals were restored. This is not an idempotent-reinstall
claim. A separate pre-route public-asset probe downloaded every manifest-bound asset, verified
the closed checksum set, had the downloaded installer accept the installed qualified bytes
(`already_installed`), started, served, refused an anonymous status request with HTTP 401
and stopped the release.
[RTX 3090 public install](../releases/v0.9.1/acceptance/rtx3090-public-install.json) ·
[RTX 4090 public install](../releases/v0.9.1/acceptance/rtx4090-public-install.json).

The RTX 5090 routes ran in **two production windows** from the maintainer's Apple silicon
workstation over the tailnet. Downtime was at most **408.4 s (6.8 min)** and **386.5 s
(6.4 min)** ([restoration](measurements/2026-10-01-v091-acceptance-restoration.json)).
The first window passed every route, client probe and restoration check, but its summary
refused an unchanged Windows scheduled task that was `Running` at baseline and `Ready`
at the end. The summary now requires byte-identical hold markers and tasks with unchanged
definitions and enabled states; that window's evidence passed the corrected summary. One
corrected window on the same candidate passed in fresh workspaces.

The RTX 3090 route ran with its console signed out: managed start refuses while any process
holds at least 1 GiB of GPU memory, and the signed-in desktop's compositor alone held about
1,070 MiB. The standalone lane does not activate the deferred RTX 3090 fleet scout role.
The historical v0.7.2 RTX 3090 route remains a separate durable v0.2 lineage with the OMP
18.0.9 fork client; its sessions do not carry over. The upstream engine merge remains deferred.

[Release notes](../releases/v0.9.1/NINFER_RELEASE_NOTES.md) ·
[Manifest](../releases/v0.9.1/manifest.json) · [Qualification](../releases/v0.9.1/qualification.json).

### v0.9.0 historical public release — two requests in flight on the RTX 5090

The RTX 5090 serves **two requests at once** with `v0.6.14-qwen38-5090-beta.1`
(image `4c816b0c`, server `f62a570e`), deployment profile `qwen38-5090-v0.9.0` and
configuration `cf1de114`. The eight-token MTP3 verify round now uses the Q5 tensor-core route
instead of SIMT kernels. Two decoding requests reached **281.1-283.0 tok/s together**, against
166.7-167.1 one at a time (**1.68-1.70x**), up from v0.6.13's 190.0-191.1 with two requests.
The candidate answered the role corpus byte-identically to v0.6.13, two cases at a time and one
at a time (**89/89**); the published image matched both the candidate and v0.6.13 (**89/89**)
([EXP-077](measurements/2026-09-29-rtx5090-two-requests-in-flight.json)).

The profile adds `--max-concurrency 2 --pending-timeout-ms 180000`. A request that cannot fit
beside the running one can wait **180 s**: the wait plus the longest root prefill, **130,048
tokens in 58.4 s** on the published image, stays inside OMP's **300 s** stream-idle watchdog.
The server ends a too-long wait and OMP resends. KV capacity auto-resolves to **160,256 tokens**;
VRAM after load is **30,242-30,244 MiB** of 32,607 MiB, against 28,144 MiB with one request.
Keep-warm, 16384 MiB host KV, the 24 GiB checkpoint quota, BF16 KV, MTP3, 131,072-token context
and the 28672 MiB runtime-host floor are unchanged.

The config every documented route installs,
[`examples/manual-tunnel/fail-closed.yml`](../examples/manual-tunnel/fail-closed.yml), sets the RTX 5090
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

The [final-profile lane evidence](../releases/v0.9.0/qualification/rtx5090.json) was collected on the
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
[Documented routes](../releases/v0.9.0/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.9.0/acceptance/composed-external-installation.json).

The RTX 5090 routes ran in **three production windows** from the maintainer's Apple silicon
workstation over the tailnet. Downtime was at most **101.5 s (1.7 min)** and **324.3 s
(5.4 min)** in the two failed windows and **499.3 s (8.3 min)** in the accepted window; total
downtime was at most **925.0 s (15.4 min)**
([restoration](measurements/2026-09-30-v090-acceptance-restoration.json)).

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

RTX 3090 was deferred in v0.9.0. [Release notes](../releases/v0.9.0/NINFER_RELEASE_NOTES.md) ·
[Manifest](../releases/v0.9.0/manifest.json) · [Qualification](../releases/v0.9.0/qualification.json).

### v0.8.7 historical public release — long sessions keep their cache

Long sessions no longer re-prefill from root at compaction handoffs, near-capacity turns, crashes
after a compaction, or when short sessions fill the checkpoint store. Both lanes move to runtimes
with the same fixes: RTX 5090 `v0.6.13-qwen38-5090-beta.1` (image `d71e34c3`, server `b8ae62ae`)
and RTX 4090 `v0.6.10-qwen38-4090-beta.1` (package `a0ea4c81`, server `e0498fad`). The config every
documented route installs, [`examples/manual-tunnel/fail-closed.yml`](../examples/manual-tunnel/fail-closed.yml),
limits each NInfer provider to one request in flight and leaves compaction at OMP's default, so OMP
compacts in the background again and the turn that meets a running summary waits in OMP instead of
expiring at the server ([EXP-074](measurements/2026-09-29-long-session-cache.json)):

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
([EXP-075](measurements/2026-09-29-stock-omp-1840-durable-sessions.json)).

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
[Documented routes](../releases/v0.8.7/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.8.7/acceptance/composed-external-installation.json).

The RTX 5090 routes ran in **two production windows** from a separately hosted Apple silicon
Mac mini. Downtime was at most **264.5 s (4.4 min)** in the failed window and
**384.1 s (6.4 min)** in the accepted window; total downtime was at most
**648.6 s** ([restoration](measurements/2026-09-29-v087-acceptance-restoration.json)).

Candidate `9474326f` passed the RTX 4090 route, but its RTX 5090 window failed at the macOS
restart step. That step seeds its session with the release's own documents, which quoted the
misspelled nonce copy from v0.8.6's first window, and after a hot restore (71,791 of 71,839
tokens reused) the model returned that quoted copy. The seed now drops every line holding the
nonce's digits: the RTX 4090 recall returned the quoted copy in 4 of 30 trials with the old seed
and in none of 30 with the new one ([EXP-076](measurements/2026-09-29-restart-seed-decoy.json)). Candidate
`a1e51a70` passed the RTX 4090 route and a second RTX 5090 window.

[Release notes](../releases/v0.8.7/NINFER_RELEASE_NOTES.md) ·
[Manifest](../releases/v0.8.7/manifest.json) ·
[Qualification](../releases/v0.8.7/qualification.json).

### v0.8.6 historical public release — long sessions compact inline

- Status: accepted exact-profile product, 2026-09-28.
  [Manifest](../releases/v0.8.6/manifest.json) · [guide](QUICKSTART.md) ·
  [qualification](../releases/v0.8.6/qualification.json).
- Eligibility: RTX 5090 on Windows 11 + Docker Desktop/WSL2, or RTX 4090 native Windows 11.
  RTX 3090 remains deferred. Owner-operated exact profiles only; no SLA or silent cloud fallback.

Long sessions no longer fail a turn while OMP compacts them. The config every documented
route installs, [`examples/manual-tunnel/fail-closed.yml`](../examples/manual-tunnel/fail-closed.yml),
sets `compaction.asyncEnabled: false`, so unmodified upstream OMP 18.4.0 compacts before
the turn instead of in the background. Both lanes admit one request at a time. On the RTX 4090,
the background handoff took 56-61 s; the next turn's attempts expired at the 30 s admission
deadline, and the third of three compactions ended in `503 request_queue_timeout`.

[EXP-072](measurements/2026-09-28-omp-long-sessions.json), using the new
[`scripts/omp_long_session_proof.py`](../scripts/omp_long_session_proof.py), measured repeated
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
([EXP-073](measurements/2026-09-28-omp-acceptance-sampling.json)); a restated,
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
[Documented routes](../releases/v0.8.6/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.8.6/acceptance/composed-external-installation.json).

The RTX 5090 routes ran in **two production windows** from a separately hosted Apple silicon
Mac mini. Downtime was at most **186.9 s (3.1 min)** in the failed window and
**392.1 s (6.5 min)** in the accepted window;
total downtime was at most **579.0 s**
([restoration](measurements/2026-09-28-v086-acceptance-restoration.json)).

Candidate `be49962c` was refused by the RTX 4090 preflight before touching the lane: the lane
stage had left its manifest a draft; tooling was fixed. On `1fa202fd` the RTX 4090 route passed,
but the first RTX 5090 window failed at macOS resume: the acknowledgment wrote `COBOLT-493817`
and recall returned that copy. Production was restored after **186.9 s**; nonce checks were
hardened. On `60b5d82d` the documented RTX 4090 route passed, but its harness refused two
tool calls where it required exactly one. The harness now accounts each request to a documented
turn or tool call. Candidate `4f49fce7` passed the RTX 4090 route and a second RTX 5090 window.

[Release notes](../releases/v0.8.6/NINFER_RELEASE_NOTES.md) ·
[Manifest](../releases/v0.8.6/manifest.json) ·
[Qualification](../releases/v0.8.6/qualification.json).

Individual route receipts: [RTX 5090 host](measurements/2026-09-28-v086-rtx5090-container-host-run.json),
[macOS client](measurements/2026-09-28-v086-rtx5090-macos-client-run.json),
[Windows client](measurements/2026-09-28-v086-rtx5090-windows-client-run.json), and
[RTX 4090 native](measurements/2026-09-28-v086-rtx4090-native-run.json).

### v0.8.5 historical public release — OMP 18.4.0 and long-session compaction

- Status: superseded accepted exact-profile product, 2026-09-28.
  [Manifest](../releases/v0.8.5/manifest.json) · [guide](QUICKSTART.md) ·
  [qualification](../releases/v0.8.5/qualification.json).
- Eligibility: RTX 5090 on Windows 11 + Docker Desktop/WSL2, or RTX 4090 native Windows 11.
  RTX 3090 remains deferred. Owner-operated exact profiles only; no SLA or silent cloud fallback.

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

The v0.8.5 release also repins unmodified upstream OMP from 18.3.5 to
[18.4.0](https://github.com/can1357/oh-my-pi/releases/tag/v18.4.0). On Windows, 18.3.5
printed a false `ended before completing` line after finished `omp -p` turns and exited 1
after a complete `omp models` listing. Upstream fix `9d3e0d4975` resolves
[#13470](https://github.com/can1357/oh-my-pi/issues/13470).

[EXP-070](measurements/2026-09-28-omp-1840-windows-completion-status.json) compared the
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
[Documented routes](../releases/v0.8.5/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.8.5/acceptance/composed-external-installation.json).

The RTX 5090 routes ran in one production window, with downtime at most
**381.2 s (6.4 min)**, from a separately hosted Apple silicon Mac mini on
macOS 26.6.1 over the tailnet, not the maintainer's workstation
([restoration](measurements/2026-09-28-v085-acceptance-restoration.json)).

[EXP-067](measurements/2026-09-27-stock-omp-1835-durable-sessions.json) (durable sessions)
and [EXP-068](measurements/2026-09-28-omp-1835-live-steering.json) remain OMP 18.3.5
evidence. In 18.4.0, live steering remains Codex-WebSocket-only in
`openai-codex-responses.ts`, gated on `compat.supportsSteering`; these providers do not set it.
The upstream engine merge stays deferred
([EXP-065](measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json)); the
sm_89 Q5 tensor-core route stays rejected
([EXP-069](measurements/2026-09-28-rtx4090-q5-small-t-mma.json)). RTX 3090 remains deferred:
its `v0.6.2-beta.1` package is built and tested (99/105 tests) but unpublished; one
`qualify_native.py` window on its physical host remains
([preparedness](measurements/2026-09-28-rtx3090-v062-build-preparedness.json)).

Upstream tag `v18.4.0` points to `401778d0cd30020ce0f9198f751b13c68850562f` and was
published 2026-09-28T03:33:34Z. The pinned binaries are:

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `omp-windows-x64.exe` | 239,441,408 | `5e8637d7f0e86819eb17238f297b4cef07f5239a4f59e2b26f8b4584a9ea95fe` |
| `omp-linux-x64` | 285,148,640 | `fbcdb8f5033c9bf81435f5803d8f0493c53d524a638658d2b8811474a332200f` |
| `omp-darwin-arm64` | 214,917,008 | `90111c710fb861b03e5ef6fd3257319001acdd77ff7d06d3a6207996f2777709` |

Individual route receipts: [RTX 5090 host](measurements/2026-09-28-v085-rtx5090-container-host-run.json),
[macOS client](measurements/2026-09-28-v085-rtx5090-macos-client-run.json),
[Windows client](measurements/2026-09-28-v085-rtx5090-windows-client-run.json), and
[RTX 4090 native](measurements/2026-09-28-v085-rtx4090-native-run.json).

[Release notes](../releases/v0.8.5/NINFER_RELEASE_NOTES.md) ·
[Qualification](../releases/v0.8.5/qualification.json).

### v0.8.4 historical public release — every lane current

- Status: superseded accepted exact-profile product, 2026-09-28.
  [Manifest](../releases/v0.8.4/manifest.json) · [guide](https://github.com/alphastorm/omp-ninfer/blob/v0.8.4/docs/QUICKSTART.md) ·
  [qualification](../releases/v0.8.4/qualification.json).
- Client: unmodified upstream OMP 18.3.5. The model and memory floors are unchanged; eligibility
  remains one RTX 5090 or RTX 4090, with RTX 3090 deferred.

RTX 4090 ships `v0.6.9-qwen38-4090-beta.1` (package `6492588e`, server `65364401`,
source `5ac17674`, configuration `ccecfbe3`). Its `engine.gpu_keep_warm_ms = 60000` uses an
sm_89-specific 50 ms spin every 100 ms: the RTX 5090's 3.5 ms/10 ms pattern did not hold this
card in P2. New sessions after 12-58 s idle prefilled in **0.146-0.148 s**, with time to first
token **0.167-0.178 s**; all 31 outputs were byte-identical. The hold costs about **72 W**
above idle, and a request arriving mid-spin can overlap one warp for up to 50 ms.
[EXP-064](measurements/2026-09-27-rtx4090-engine-keep-warm.json) ·
[EXP-066](measurements/2026-09-27-rtx4090-keep-warm-long-spin.json).

The published package passed all **15 canonical qualification phases**
([lane receipt](../releases/v0.8.4/qualification/rtx4090.json)); this is not a decode-kernel speedup.
RTX 5090 keeps `v0.6.12-qwen38-5090-beta.1`, image `cd9e10b1`, profile `qwen38-5090-v0.8.2`,
configuration `56878aed` and its carried v0.8.3 lane receipt. The model and memory floors are
unchanged. RTX 4090 checkpoints from v0.6.8 re-prefill once on the changed server build;
RTX 5090 carries its v0.8.3 checkpoints.

The v0.8.4 client advanced to unmodified upstream **OMP 18.3.5**. Its macOS arm64 binary kept one
short session across graceful restarts on both lanes with the documented fragments unchanged
([EXP-067](measurements/2026-09-27-stock-omp-1835-durable-sessions.json)). A steer submitted
mid-stream did not abort: OMP sent it **27 ms** after `response.completed` as a new request
chained by `previous_response_id`
([EXP-068](measurements/2026-09-28-omp-1835-live-steering.json)).

All four documented routes passed **24 steps** on candidate `68302298` with unmodified OMP
18.3.5 and the published v0.8.4 components: RTX 5090 container host 2, macOS client 10, Windows
client 5 and RTX 4090 native Windows 7; both hosts were restored. The upstream macOS arm64
(preview), Windows x64 and Linux x64 binaries each passed a typed tool turn, an exact
continuation and a fail-closed request against RTX 5090 image `cd9e10b1`. Linux ran under WSL2,
not a separately qualified Linux OS.
[Documented routes](../releases/v0.8.4/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.8.4/acceptance/composed-external-installation.json).

The RTX 5090 routes ran in one production window, with downtime at most **421.5 s (7.0 min)**,
from a separately hosted Apple silicon Mac mini on macOS 26.6.1 over the tailnet, not the
maintainer's workstation
([restoration](measurements/2026-09-28-v084-acceptance-restoration.json)).

The RTX 4090 route's first candidate, `0315c5d4`, stopped at its no-effect preflight because
the harness judged the provider-parser check only by `omp models`'s exit status. OMP 18.3.5 on
Windows exits 1 after a complete listing
([can1357/oh-my-pi#13470](https://github.com/can1357/oh-my-pi/issues/13470)). That release judged
the listing; `68302298` passed the literal documented blocks with the published v0.6.9 package
and original state restored byte for byte. Upstream 18.4.0, released 2026-09-28, fixes #13470;
v0.8.4 pinned 18.3.5; v0.8.5 repins to 18.4.0.

The upstream engine merge stays deferred: `e31bc99b` has about **18% slower decode** and
fanout **0/4 versus 4/4**
([EXP-065](measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json)). The
RTX 4090 Q5 tensor-core route was rejected by its pre-registered rule: **+0.38% at 26K** and
**+0.40% at 60K**, below required **2.0%/1.0%** gains
([EXP-069](measurements/2026-09-28-rtx4090-q5-small-t-mma.json)). RTX 3090's v0.6.2-beta.1
package built and tested at `5ac17674` remains unpublished, with hardware qualification pending
([preparedness](measurements/2026-09-28-rtx3090-v062-build-preparedness.json)).

[Release notes](../releases/v0.8.4/NINFER_RELEASE_NOTES.md).

### v0.8.3 historical public release — faster RTX 5090 decode

- Status: superseded published exact-profile product, 2026-09-27.
  [Manifest](../releases/v0.8.3/manifest.json) ·
  [guide](https://github.com/alphastorm/omp-ninfer/blob/v0.8.3/docs/QUICKSTART.md) ·
  [qualification](../releases/v0.8.3/qualification.json).
- Client and model: unmodified upstream OMP 18.3.0 and the model artifact (`eec39564`) are
  unchanged from v0.8.2. Eligibility remains one RTX 5090 or RTX 4090; RTX 3090 is deferred.
- RTX 5090 ships `v0.6.12-qwen38-5090-beta.1`, image
  `sha256:cd9e10b115bbf38df011b201dfdd37ec3b56613da39b2f1701334c8157236b78`, server
  `3ab266e5cd82398be98c2baee6a41a123ce1a4b0d38bd9ddcda75044dcd5dcb1`, source
  `9d1ef7485d9c741c2830fa3d55218f3242cec5d7` (v0.8.2's `32c21f73` plus the EXP-057 route).
  Runtime-image workflow run: `36301090709`. Serving arguments and deployment profile
  `qwen38-5090-v0.8.2`, configuration
  `56878aed92e8f3fb4101884fa889c98d1da75914573ebd167305ca0b4aa83e98`, are unchanged.
  The profile keeps `--gpu-keep-warm-ms 60000`, 16384 MiB host KV and a 28672 MiB host floor.
- The MTP3 verify pass's four Q5 projections (GDN value/z, attention gate/value,
  mixer/attention output and MLP down) use small-T tensor-core MMA at the four-token extent
  on `sm_120` instead of SIMT row kernels. The route is compiled out for `sm_86` and `sm_89`.
  Release-build A/B/B/A measurements show decode **+4.4% at 26K**, **+3.6% at 60K** and
  **+6.3% at 1,024 tokens**. MTP3 rounds are **4.2%**, **3.5%**, **4.4%** and **4.9%** shorter
  at 26K, 60K, 1,024 tokens and no prompt respectively (range **3.5-4.9%**). With no prompt,
  decode is **0.5% slower**; the new build accepted 0.423 of drafts on its own text versus
  0.461. MTP acceptance was unchanged at 26K and 60K.
  Route: [EXP-057](measurements/2026-09-26-q5-small-t-tensor-core.json); measurements:
  [EXP-063](measurements/2026-09-27-powered-redaction-screen.json).
- Accumulation order changes: in isolation, 27 of 118,784 projection outputs moved by one
  bf16 ulp, closer to an FP64 reference. Generated text differs from v0.8.2 on **58 of 89**
  role-corpus cases (31 identical). The published image matched the screened candidate
  byte-for-byte on **89/89**. Other primary role-corpus measures were within 2.0 points of
  v0.8.2 in one run per build; the only criterion-6 regression was redaction-control pass rate.
- The pre-registered EXP-063 paired redaction screen passed. The rule was committed before
  candidate data (`554ac56`, `scripts/redaction_screen.py`); 7 counted redaction controls
  with 72 whitespace variants gave **504 pairs** on fresh v0.8.2 and candidate servers.
  Candidate leaks were **561 vs 582** for v0.8.2 (ratio **0.964**, one-sided 95% upper bound
  **1.012**, below the **1.10** margin). Pass rates were **53.2% vs 52.6%**: difference
  **+0.6 percentage points**, lower bound **-1.2 points** against a **-5-point** margin.
  All validity checks held; both arms reproduced 14 determinism prompts and matched
  EXP-057's outputs on 64 shared prompts. EXP-057's earlier 56-sample point-estimate screen
  had rejected the route (**69 vs 61 leaks**); EXP-063 re-tested the redaction regression
  with power. [EXP-063](measurements/2026-09-27-powered-redaction-screen.json).
- Gates were re-measured on the published RTX 5090 image: 130,048-token exact retrieval in
  **58.7 s**, `decode_2048` at **168.07 tok/s**, and the agent protocol across a restart.
  EXP-050 recorded four saves before eviction, first stop
  `saved 1, nothing to save 3, refused 0`, all four stored sessions restored after restart,
  and second stop `saved 0, nothing to save 4, refused 0`. EXP-051's held publication-barrier
  turn resumed exactly. Fanout (57K/67K), warm-arrival, restore and multisession probes
  passed; root fallback remained 2 of 8 continuations/forks. None of 24 fresh sessions fell
  back to a full prefill; median TTFT was **0.093-0.100 s**. Stock OMP 18.3.0 kept one
  session across graceful restarts; the first request restored from checkpoint.
  [RTX 5090 receipt](../releases/v0.8.3/qualification/rtx5090.json).
- RTX 4090 remains `v0.6.8-qwen38-4090-beta.1` (package `46aa4110`, server `32905865`,
  source `5a774841`), unchanged since v0.8.1 and carrying its
  [v0.8.1 lane receipt](../releases/v0.8.1/qualification/rtx4090.json).

All four documented routes passed **24 steps** with unmodified OMP 18.3.0 on the published
v0.8.3 components: RTX 5090 container host 2, macOS client 10, Windows client 5 and RTX 4090
native Windows 7; both hosts were restored.
The upstream macOS arm64, Windows x64 and Linux x64 binaries each passed a typed tool turn,
an exact continuation and a fail-closed request against the published RTX 5090 image.
[Documented routes](../releases/v0.8.3/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.8.3/acceptance/composed-external-installation.json).

Checkpoints bind the exact server build: sessions saved by v0.8.2 do not restore on the new
RTX 5090 build in v0.8.3. Each session re-prefills once.
[Release notes](../releases/v0.8.3/NINFER_RELEASE_NOTES.md).

### v0.8.2 historical public release — GPU keep-warm

- Status: superseded published exact-profile product, 2026-09-26.
  [Manifest](../releases/v0.8.2/manifest.json) ·
  [guide](https://github.com/alphastorm/omp-ninfer/blob/v0.8.2/docs/QUICKSTART.md) ·
  [qualification](../releases/v0.8.2/qualification.json).
- Client and model: unmodified upstream OMP 18.3.0 and the model artifact are unchanged from
  v0.8.1. Eligibility remains one RTX 5090 or RTX 4090; RTX 3090 is deferred.
- RTX 5090: `v0.6.11-qwen38-5090-beta.1`, image
  `sha256:26813f5661e9bab7093349a216543d9391d310c08a207fee4d389d763dd36930`, server
  `0d7e042bca2956bbbe9bd68e8d1dcfaeea2666e326acdcea2d34d9b75d7c31d8`, source
  `32c21f73a7605f76480a6139de0488a14ed1aa48`. The profile advances to
  `qwen38-5090-v0.8.2`, configuration
  `56878aed92e8f3fb4101884fa889c98d1da75914573ebd167305ca0b4aa83e98`, adding
  `--gpu-keep-warm-ms 60000`. Host KV stays 16384 MiB and the host floor stays 28672 MiB.
- Runtime: `ninfer-serve --gpu-keep-warm-ms N` is off by default. After work and while idle,
  a single-warp kernel that touches no memory spins 3.5 ms of every 10 ms on its own stream
  for N ms, skips a launch while the previous spin runs, and stops when a request is pending.
  Idle clock step-down and up to 2.3x slower first prefill were measured in
  [EXP-060](measurements/2026-09-26-idle-gpu-new-sessions.json); a 30% duty held the top
  P-state where 25% did not in [EXP-061](measurements/2026-09-26-keep-warm-load.json).
- Measured effect and cost: new sessions after 12-58 s idle prefilled in **0.155-0.157 s**
  (TTFT **0.173-0.181 s**), the same as back to back, versus **0.253-0.304 s**
  (TTFT **0.316-0.366 s**) without it. The 89-case role corpus was byte-identical to v0.8.1
  on and off. Requests arriving 1-5 ms after the previous one changed TTFT by a median
  **-0.1 ms**, worst **+4.4 ms**. Holding clocks drew **99.5-102.7 W** versus **29.3-29.8 W**
  idle (about **71 W** extra); a 60 s grace replayed over 62 h of logged v0.7.0 traffic
  would cover 84 of 138 requests after at least 5 s idle (74 of 103 new sessions) at about
  **2.3 W average**. A 30 s grace would cover only 11 requests (median wait 52.7 s).
  [EXP-062](measurements/2026-09-26-engine-keep-warm.json).
- RTX 5090 lane receipt on the published image: 130,048-token exact retrieval in **56.4 s**,
  decode **160.07 tok/s** (MTP acceptance 0.412, 2.24 tokens per round), four saves before
  eviction, stop `saved 1, nothing to save 3, refused 0`, all four sessions restored after
  restart, and second stop `saved 0, nothing to save 4, refused 0`. Publication-barrier,
  fanout, warm-arrival, restore and multisession probes passed. None of 24 fresh sessions
  fell back to a full prefill; median TTFT was **0.090-0.098 s**. Stock OMP 18.3.0 kept one
  session across restarts on the RTX 5090; the role corpus was 89/89 identical to production
  v0.8.1. [Lane receipt](../releases/v0.8.2/qualification/rtx5090.json).
- RTX 4090: unchanged `v0.6.8-qwen38-4090-beta.1` (package `46aa4110`, server `32905865`,
  source `5a774841`), carrying its v0.8.1 lane receipt: 15 canonical native phases and
  130,048-token retrieval in **91.0 s**.
  [Lane receipt](../releases/v0.8.2/qualification/rtx4090.json).

All four documented routes passed **24 steps** with unmodified OMP 18.3.0 on the published
v0.8.2 components: RTX 5090 container host 2, macOS client 10, Windows client 5 and RTX 4090
native Windows 7; both hosts were restored.
The upstream macOS arm64, Windows x64 and Linux x64 binaries each passed a typed tool turn,
an exact continuation and a fail-closed request against the published RTX 5090 image.
[Documented routes](../releases/v0.8.2/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.8.2/acceptance/composed-external-installation.json).

Checkpoints bind the exact server build: sessions saved by v0.8.1 do not restore on the new
RTX 5090 build in v0.8.2. OMP resends the full conversation and each session re-prefills once.
[Release notes](../releases/v0.8.2/NINFER_RELEASE_NOTES.md).

### v0.8.1 historical public release — faster decode

- Status: superseded published exact-profile product. [Manifest](../releases/v0.8.1/manifest.json) ·
  [guide](https://github.com/alphastorm/omp-ninfer/blob/v0.8.1/docs/QUICKSTART.md) ·
  [qualification](../releases/v0.8.1/qualification.json).
- Client: unmodified upstream [OMP 18.3.0](https://github.com/can1357/oh-my-pi/releases/tag/v18.3.0)
  binaries with the same SHA-256 pins as v0.8.0. The model, serving settings and memory
  floors are unchanged too.
- Runtime: the MTP3 verify pass's small-extent Q4/Q5 projections share each activation load
  across weight rows, and the Q4 MLP gate/up kernel pads staged weight rows to avoid
  shared-memory bank conflicts. Arithmetic order is unchanged. RTX 5090 decode is
  **10.3-11.0% faster** from a seed context to 31K tokens with identical outputs. Native
  lanes keep one-row Q5 split2 kernels for MLP down and mixer output, where load sharing
  measured slower; RTX 4090 C1 decode is **157.89 vs 153.54 tok/s**.
  [EXP-055](measurements/2026-09-25-decode-kernel-schedules.json) ·
  [EXP-054 attribution](measurements/2026-09-25-decode-roofline-attribution.json).
- RTX 5090 `v0.6.10-qwen38-5090-beta.1` (image `5ca6e416`, server `5b2f2471`, source
  `8cc0810a`) passed its profile gates on the anonymously pulled published image: exact
  130,048-token retrieval in **59.1 s**, 2,048-token decode at **151.33 tok/s**, and the
  agent protocol across a restart. EXP-050 durability recorded four
  saves before eviction, stop `saved 1, nothing to save 3, refused 0`, all four stored
  sessions restored, and second stop `saved 0, nothing to save 4, refused 0`. EXP-051's
  held publication-barrier turn resumed exactly `V-9241`. Fanout (57K/67K), warm-arrival,
  restore and multisession probes passed; root fallback remained 2 of 8 with no server errors.
  None of 24 fresh sessions fell back to a full prefill; median TTFT was **0.094-0.101 s**.
  [Lane receipt](../releases/v0.8.1/qualification/rtx5090.json).
- RTX 4090 `v0.6.8-qwen38-4090-beta.1` (package `46aa4110`, server `32905865`, source
  `5a774841`; release identity `qwen38-4090-native-v0.6.8-beta.1`) passed all 15 canonical
  native phases on the published package, including exact long-context retrieval in
  **91.0 s**, managed-stop flush of an unpublished session, rollback both directions,
  security, the OMP 18.3.0 typed tool call and C1 benchmark; no start refused.
  [Lane receipt](../releases/v0.8.1/qualification/rtx4090.json).
- Every runtime gate was re-measured on published bytes, matching v0.8.0's behavior. Stock
  OMP kept one session across restarts on both lanes; both restarts exited 0 and
  first-request restore was logged. Automatic checkpoints remain best effort; universal warm
  reuse is not claimed. [#48](https://github.com/alphastorm/omp-ninfer/issues/48) stays open
  for field confirmation.
- All four documented routes passed **24 steps**: RTX 5090 container host 2, macOS client 10,
  Windows client 5 and RTX 4090 native 7. The executed blocks matched the quickstart bytes;
  both hosts were restored. The upstream macOS arm64, Windows x64 and Linux x64 binaries
  passed typed tools, exact continuation and fail-closed checks against the published
  RTX 5090 image. Linux ran in **Ubuntu under WSL2**, not a separate non-WSL OS qualification;
  macOS remains preview because the upstream client has no managed installation.
  [Documented routes](../releases/v0.8.1/acceptance/documented-routes.json) ·
  [composed acceptance](../releases/v0.8.1/acceptance/composed-external-installation.json).
- Eligibility: **RTX 5090 Windows 11 + Docker Desktop/WSL2 container route** and **RTX 4090
  native Windows**. **RTX 3090 remains deferred**; its historical v0.7.2 route stays on OMP
  18.0.9, not a qualification claim for this release.
- Upgrade: checkpoints bind the exact server build (`patch_stack_sha` and `binary_sha256`
  are in the runtime fingerprint). v0.8.0 checkpoints report `incompatible` and do not
  restore on v0.8.1. OMP 18.3.0 treats `previous_response_not_found` as a stale chain and
  resends the full conversation, so each session re-prefills once. Old checkpoints age out
  under the quota.

### v0.8.0 historical public release — bring your own OMP

- Status: superseded published exact-profile product. [Manifest](../releases/v0.8.0/manifest.json) ·
  [guide](https://github.com/alphastorm/omp-ninfer/blob/v0.8.0/docs/QUICKSTART.md) ·
  [qualification](../releases/v0.8.0/qualification.json).
- Client: unmodified upstream [OMP 18.3.0](https://github.com/can1357/oh-my-pi/releases/tag/v18.3.0)
  binaries, checked against their SHA-256. No fork build, archive, installer or cask. Provider
  fragments keep thinking within `low`, `medium` and `xhigh`, disable encrypted reasoning
  and summaries, and every route exports `PI_OPENAI_STATEFUL=1`. Stock OMP has no
  `omp appliance` commands; lifecycle follows the documented routes.
- Stock clients get durable sessions: with API authentication, `prompt_cache_key` becomes a
  hashed session identity, refused together with `ninfer_session` or `X-NInfer-Session`;
  a returning session's checkpoint is restored on its first request after a restart. Both
  lanes passed stock OMP restart/resume proof ([EXP-053](measurements/2026-09-25-stock-omp-durable-sessions.json)).
  The runtime passed an independent four-model council and four remediation epochs
  ([dispositions](../releases/v0.8.0/review/runtime-ledger.json)).
- RTX 5090 `v0.6.9-qwen38-5090-beta.2` (image `049dc788`, server `d90079e8`, source
  `86733c0e`) passed profile gates, EXP-050 durability (four saves before eviction, stop
  `saved 1, nothing to save 3, refused 0`, all four stored sessions restored), EXP-051's
  publication barrier, and fanout, warm-arrival, restore and multisession probes on the
  anonymously pulled published image. RTX 4090 `v0.6.7-qwen38-4090-beta.2` (package `888a5859`,
  server `e4688dda`, source `b0e8c2fa`) passed all 15 native phases, including the first
  managed start after a fresh install and the OMP 18.3.0 typed tool call.
- New-session shared-prefix reuse on the published RTX 5090 image: three agent types first
  prefilled their 11,887-14,199-token prefixes in 3.8-4.4 s; none of the 24 later fresh
  sessions fell back to a full prefill, and median time to first token was 0.095-0.102 s.
  Content-part image tool outputs reach the model on RTX 5090; text-only RTX 4090 refuses
  the image as `vision_disabled`. The RTX 4090 pinning fix commits and releases each pinned
  allocation's size plus 1/64 before pinning; [#48](https://github.com/alphastorm/omp-ninfer/issues/48)
  remains open for field confirmation.
- Model, serving settings and memory floors are unchanged from v0.7.4. Automatic checkpoints
  remain best effort; saving before eviction costs about 6.5 s per 126K-token session on the
  RTX 5090. The multisession control recorded two root fallbacks among eight continuations/forks;
  universal warm reuse is not claimed. Ceiling-class save-before-evict was exercised on RTX 5090 only.
- The macOS arm64, Windows x64 and Linux x64 upstream binaries passed live inference against
  the published RTX 5090 image (Linux in **Ubuntu under WSL2**). All four documented routes
  passed: RTX 5090 host 2 blocks, macOS client 10, Windows client 5 and RTX 4090 native 7;
  both hosts were restored. [Documented routes](../releases/v0.8.0/acceptance/documented-routes.json) ·
  [composed acceptance](../releases/v0.8.0/acceptance/composed-external-installation.json).
- Eligibility: **RTX 5090 Windows 11 + Docker Desktop/WSL2 container route** and **RTX 4090
  native Windows**. **RTX 3090 remains deferred**; its historical v0.7.2 route stays on OMP
  18.0.9. Upgrade by installing the upstream binary and replacing the provider fragment.
  Fork-client `ninfer_session` checkpoints are not reachable from stock OMP: each session takes
  one cold first turn, and old checkpoints age out under the quota.

### v0.7.4 historical public release — live sessions survive a graceful stop

- Status: superseded published exact-profile product. [Manifest](../releases/v0.7.4/manifest.json) ·
  [guide](https://github.com/alphastorm/omp-ninfer/blob/v0.7.4/docs/QUICKSTART.md) ·
  [qualification](../releases/v0.7.4/qualification.json).
- Runtime rebind on both lanes to source `1c17c3facfbfd1243cf7711a412119302e6dbd74`: runtime
  `a4d26ccb` plus a packaging-only RTX 4090 lane version bump. Transient automatic checkpoint
  refusals retry, admission saves a session's newest turn before evicting it (waiting while its
  reply is still being stored), and quota re-saves keep other sessions' checkpoints
  ([#45](https://github.com/alphastorm/omp-ninfer/issues/45),
  [#46](https://github.com/alphastorm/omp-ninfer/issues/46)). An independent four-model council
  and a remediation epoch reviewed the runtime delta
  ([dispositions](../releases/v0.7.4/review/runtime-ledger.json)).
- RTX 5090 `v0.6.8-qwen38-5090-beta.1` (image `f193b746`, server `72aa57dd`) passed its profile
  gates, the EXP-050 durability workload (stop `saved 1, nothing to save 3, refused 0`; all four
  stored sessions restored after a restart), EXP-051's publication barrier, and the fanout,
  warm-arrival, restore and multisession probes, all on the anonymously pulled published image.
  RTX 4090 `v0.6.6-qwen38-4090-beta.1` (package `cd9ab90f`, server `7a923c21`) passed all 15
  canonical native phases with the OMP 18.2.3 client.
- OMP 18.2.3 client, model, serving arguments and memory floors are unchanged from v0.7.3.
  Automatic checkpoints remain best effort; saving before eviction delays the admitting request;
  the multisession control recorded two root fallbacks among eight continuations/forks. The
  RTX 4090 workload evicted no checkpoint-tagged session, so save-before-evict is exercised on the
  RTX 5090 only.
- The published macOS arm64, Windows x64 and Linux x64 clients passed live inference against the
  new RTX 5090 image (Linux in **Ubuntu under WSL2**), and RTX 5090 host (2), macOS client (10),
  Windows client (5) and RTX 4090 native (7) passed **24 documented steps** on the published
  components, with pre-cut substitutions recorded and all hosts restored.
  [Documented routes](../releases/v0.7.4/acceptance/documented-routes.json).
- Eligibility: **RTX 5090 on Windows 11 + Docker Desktop/WSL2** and **RTX 4090 native Windows 11**.
  **RTX 3090 remains deferred**; its immutable v0.7.2 guide and manifest stay on OMP 18.0.9.

### v0.7.3 — OMP 18.2.3 client repin

- Status: superseded published exact-profile product. [Manifest](../releases/v0.7.3/manifest.json) ·
  [guide](https://github.com/alphastorm/omp-ninfer/blob/v0.7.3/docs/QUICKSTART.md) · [qualification](../releases/v0.7.3/qualification.json).
- Client-only change from OMP 18.0.9 to `omp-18.2.3-cross-platform-beta-1`, built from public
  source `5ade242de59ac0f4606a1158bf564410c96918d4`. The macOS arm64, Windows x64 and Linux x64
  archives and all three provider-free hosted qualification receipts are public; hosted proof
  and live inference are distinct, and both passed for these clients.
- Fresh live Linux-client proof ran in **Ubuntu under WSL2**, not on a separately qualified
  non-WSL Linux OS. RTX 5090 host (2), macOS client (10), Windows client (5), and RTX 4090 native
  (7) passed **24 documented steps** on frozen product source
  `096c8b889eef4bc89ee2dc316694b847bdf8a39d`, with pre-cut substitutions recorded and all
  hosts restored. [Documented routes](../releases/v0.7.3/acceptance/documented-routes.json).
- Eligibility: **RTX 5090 on Windows 11 + Docker Desktop/WSL2** and **RTX 4090 native Windows 11**.
  **RTX 3090 is deferred**, not qualified with OMP 18.2.3. Its immutable
  [v0.7.2 guide](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md) and
  [manifest](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/releases/v0.7.2/manifest.json)
  remain separately available with OMP 18.0.9; new-client qualification waits for its host’s return.
- Capability vocabulary uses OMP’s existing `durable-checkpoint`; the old
  `process-restart-continuation` name was rejected by the closed client schema. This fixes
  authority vocabulary, not runtime behavior; the verifier rejects unsupported names.
- RTX 5090 `v0.6.7-qwen38-5090-beta.1` and RTX 4090 `v0.6.5-qwen38-4090-beta.1` remain
  the exact v0.7.2 image/package bytes. Model, serving arguments and memory floors are unchanged.
  Runtime measurements are **carried v0.7.2 evidence, not fresh measurements**. Automatic
  checkpoints remain best effort; three unsaved predecessor sessions and two root fallbacks
  among eight continuations/forks remain disclosed limitations. No throughput gain is claimed.

### v0.7.2 historical public release (bounded checkpoint-backed restore reclaim)

- Status: published exact-profile product. Both changed components and their documented routes
  passed acceptance; unchanged client-platform and RTX 3090 qualification are explicitly carried.
  [Release notes](../releases/v0.7.2/NINFER_RELEASE_NOTES.md).
- Both mainline components target exact reviewed source
  `d125ffffd87ef38d9a221f9830e19dfa274ddd34`: RTX 5090 `v0.6.7-qwen38-5090-beta.1`,
  image `sha256:74667e7334e51bb8d5eca99c6ae5994fef8b9e727885c89eef0812cd2bb15c24`;
  RTX 4090 native `v0.6.5-qwen38-4090-beta.1`, package
  `b26643d735d58eafac33f1595c0588baf0e6682a69af73e8e82f96839f4b7646`.
- Restore can save and reclaim reproducible resident sessions when host-KV capacity is occupied,
  then retry with a fresh reader. Bounded progress and refusal before commit preserve the
  capacity/admission contract rather than promising that every save or restore succeeds.
- [EXP-047 `final_reviewed_candidate`](measurements/2026-09-17-restore-reclaim.json) restored
  both target 126K-token RTX 5090 sessions in 5.96 s and 23.57 s. The combined probe process
  reported `shutdown_saved=2`, `shutdown_refused=3`: three unsaved predecessor sessions remain
  a measured limitation, not a loss-free-shutdown result. Automatic checkpoints remain best
  effort. The extra multisession control recorded root fallback on 2 of 8 continuations/forks
  without server errors; a zero probe exit code is not proof of universal warm reuse. The final
  native RTX 4090 package passed 15 qualification phases.
- No public serving knobs or floors change: RTX 5090 keeps `qwen38-5090-v0.7.0`, configuration
  `762e6bf4…`, 16384 MiB host KV and a 28672 MiB runtime-host floor; RTX 4090 keeps 11264 MiB
  host KV, 24 host-state slots and its 32768 MiB floor. Scratch qualification settings are
  separate. RTX 3090, the model and `omp-18.0.9-cross-platform-beta-2` remain unchanged.
- The quickstart targets v0.7.2. RTX 5090 host/macOS/Windows and RTX 4090 native routes passed
  24 documented steps, with pre-cut clone substitutions recorded. Both host windows restored
  their incumbent state. Do not bypass the ready gate or relabel carried receipts as new runs.

### v0.7.1 public release (a reported save is a restorable save)

- Product release: `alphastorm/omp-ninfer@v0.7.1`, GitHub `Latest`. Published-component
  [composed acceptance](../releases/v0.7.1/acceptance/composed-external-installation.json) passed;
  the RTX 4090 route downloaded and installed the newly published component from its public URLs
  (7/7 blocks) and both RTX 5090 routes were re-run
  ([routes](../releases/v0.7.1/acceptance/documented-routes.json)).
- Fixes a durability defect on the RTX 4090 native lane. Restore materialises a continuation's KV
  into the host-KV pool, and the lane shipped 4096 MiB against the 5.02 GiB a 131,072-token session
  needs: an explicit checkpoint reported 4,834,325,255 B saved and the session answered HTTP 404
  after a graceful stop and restart. New component `v0.6.4-qwen38-4090-beta.1` ships an 11264 MiB
  pool, a declared `runtime_host.minimum_runtime_memory_mib` of 32,768, and an export that is
  refused when the configuration could not admit the checkpoint back
  ([requalification](../releases/v0.7.1/qualification/rtx4090.json)).
- Two ceiling-sized sessions on that lane now keep reuse (125,906 cached tokens in 1.97 s), both
  checkpoint (4.99 GB each), the graceful stop reports `saved 2, nothing to save 0, refused 0`, and
  both resume exactly in 5.63 s and 7.78 s.
- RTX 5090 component, image `5e3e1558` and deployment profile `qwen38-5090-v0.7.0` unchanged; its
  two-session restore boundary is the same bound and is now reported with a named reason
  ([EXP-043](measurements/2026-09-16-restore-bound-host-kv-pool.json)).
- Support boundary unchanged: prerelease, no SLA, one owner-operated machine per lane, one active
  request per qualified profile, no silent cloud fallback.

### v0.7.0 public release (two long sessions keep their reuse)

- Product release: `alphastorm/omp-ninfer@v0.7.0`, superseded by v0.7.1. Published-component
  [composed acceptance](../releases/v0.7.0/acceptance/composed-external-installation.json)
  passed; both RTX 5090 documented routes were re-run on the new serving configuration
  ([routes](../releases/v0.7.0/acceptance/documented-routes.json)).
- No component, image, model, client, or KV dtype changed from `v0.6.9`; the RTX 5090 serving
  configuration did. Deployment profile `qwen38-5090-v0.7.0`, configuration identity
  `762e6bf4…` (was `5eb8a557…` from v0.6.2 through v0.6.10), Host KV pool 8 GiB to 16 GiB.
  Checkpoints written under the previous identity do not carry across.
- Two sessions at the 131,072-token ceiling keep prefix reuse: 0 of 8 continuations and forks
  lost, each reusing about 125,900 cached tokens in 1.6-3.5 s, against 4 of 4 lost to a 58 s root
  re-prefill on the shipped pool. Entering the steady state from an occupied pool costs one
  re-prefill per session, once
  ([EXP-041](measurements/2026-09-16-two-long-session-capacity.json)).
- The lane was requalified on the new configuration rather than carried
  ([receipt](../releases/v0.7.0/qualification/rtx5090.json)): exact 130,048-token retrieval at
  2,203.0 tok/s, 2,048-token decode at 133.03 tok/s wall, the agent protocol across a restart,
  hot sibling forks at two template sizes before and after a restart, warm arrival in both
  orders, and a 4.51 GB checkpoint restored in 3.5-3.7 s. VRAM 28,144 MiB.
- New host requirement: the profile declares `runtime_host.minimum_runtime_memory_mib` 28,672
  and `examples/manual-tunnel/start-ninfer.sh` refuses a host that cannot back the pool, naming
  the `.wslconfig` remedy. The same configuration in a 24 GiB WSL utility VM is OOM-killed
  mid-request (container exit 137). A host that cannot meet the floor runs `v0.6.10`.
- Both 8-bit KV dtypes fix the same reuse loss and were rejected on quality, re-scored on one
  runtime against the private role corpus: fp8 and int8 each drop the redaction control pass
  rate from 0.750 to 0.625 and add a secret leak; int8 also adds unsupported claims and critical
  misses. fp8 remains the lever to revisit if an artifact closes the grounding gap.
- Stated boundary, not a passing gate: with two sessions at the ceiling both checkpoint
  (9.24 GB each) and a graceful stop saves both, but after a restart one of the two is declined -
  `the engine did not accept the checkpointed continuation` - and re-prefills from its
  transcript. Sessions below the ceiling are unaffected. On the RTX 4090 native lane the same
  workload loses every continuation and its automatic checkpoints are refused while both sessions
  are live; that pool change and the restore-admission work are follow-ups.
- Support boundary unchanged: prerelease, no SLA, one owner-operated machine per lane, one active
  request per qualified profile, no silent cloud fallback.

### v0.6.10 public release (the documented route refuses a launch the engine cannot stage)

- Product release: `alphastorm/omp-ninfer@v0.6.10`, superseded by v0.7.0. Published-component
  [composed acceptance](../releases/v0.6.10/acceptance/composed-external-installation.json)
  passed; both RTX 5090 documented routes were re-run
  ([routes](../releases/v0.6.10/acceptance/documented-routes.json)).
- No component, model, client, or serving configuration changed from `v0.6.9`, so no lane
  requalification was required: RTX 5090 `v0.6.5-qwen38-5090-beta.1` (image
  `sha256:5e3e1558…`), RTX 4090 native `v0.6.3-qwen38-4090-beta.1`, and the RTX 3090 component
  all stand under their v0.6.9 identities and receipts.
- `examples/manual-tunnel/start-ninfer.sh` proves the route's bind mounts inside a throwaway
  container before loading the 18 GB artifact and refuses a route the engine has staged
  incompletely. Docker Desktop stages those mounts once, at creation, so after the WSL distro
  holding them restarts - which every reboot does - an existing container either refuses to start
  (`not a directory`, exit `127` with `RestartCount 0`) or starts with empty mounts until the
  server rejects its own empty `--api-key` and a restart policy loops on it.
- Recovery on this route is recreation, not `docker start`: `stop-ninfer.sh` then the same
  `start-ninfer.sh`, which the durable store makes a continuation. Both signatures and the
  recovery are in [troubleshooting](TROUBLESHOOTING.md#the-container-exists-but-will-not-start-after-a-host-reboot).
- Acceptance on 2026-09-16: documented host route 2/2 blocks
  ([receipt](measurements/2026-09-16-rtx5090-v0610-host-route-run.json)) and the macOS client
  route 10/10 blocks from an isolated HOME
  ([receipt](measurements/2026-09-16-rtx5090-v0610-macos-route-run.json)) - pinned client
  18.0.9, tool turn, image input, nonce resume, the same nonce after a container restart, and an
  authenticated request refused with the tunnel closed. The Windows client and RTX 4090 native
  routes carry explicitly attributed v0.6.9 evidence; their blocks are byte-identical.
- Field evidence for the class: [EXP-040](measurements/2026-09-16-lane-reboot-survivability.json)
  records the owner appliance's 26 h 51 min outage, four authorised reboots recovering the lane
  unattended (282 s, 646 s, 442 s, 158 s), and the first receipt of the RTX 4090 native lane's
  documented post-reboot start with its checkpointed session resuming exactly.

### v0.6.9 public release (Qwen tool-parser semantic port)

- Product release: `alphastorm/omp-ninfer@v0.6.9`, superseded by v0.6.10. Published-component
  [composed acceptance](../releases/v0.6.9/acceptance/composed-external-installation.json) passed.
- Published components: RTX 5090 `v0.6.5-qwen38-5090-beta.1`, image
  `sha256:5e3e15581cb44a2dff5e1be0c64cad206f3048e9f01c98b04ef13f61195a9bb8`; RTX 4090
  native `v0.6.3-qwen38-4090-beta.1`. Both build from reviewed source
  `696e78c7b4e3ac28ffcffafc73acc1496e65ef03`.
- Independently implemented semantics from upstream `3b50962b` / `0c5d570c`, not a wholesale
  serve-adapter rebase: supported scalar unions, case-insensitive booleans, precise numeric
  lexemes and mathematically integral values, duplicate parameters, balanced embedded markup.
  Custom raw input, history, opaque IDs, and stream ownership are preserved. Review remediation
  prevents malformed-region rescans and recursive union traversal; bytewise regressions and an
  8,192-deep union case pass.
- The model, OMP client, RTX 3090 component, and serving settings are unchanged. The RTX 5090
  public profile stays `qwen38-5090-v0.6.3` / configuration `622ab621`; candidate lifecycle
  qualification uses `qwen38-5090-v0.6.2` / `5eb8a557`, unchanged. These identities are not
  interchangeable evidence of route acceptance.
- Lane qualification on 2026-09-13 ([5090](../releases/v0.6.9/qualification/rtx5090.json) ·
  [4090](../releases/v0.6.9/qualification/rtx4090.json)): exact 130,048-token retrieval on
  each; 5090 prefill 2,193.3 tok/s and decode 134.87 tok/s wall; 4090 retrieval 91.2377 s,
  C1 decode 153.464 tok/s at 87.58865% MTP acceptance, 15/15 native phases, saved and
  never-published sessions restored across managed stop/flush, graceful rollback with the
  `68a0722f` predecessor in both directions.
- Build verification: appliance focused suites 13/13, Windows parser/wire suites 4/4; Blackwell
  CI 95 passed, 7 skipped, 0 failed out of 102 registered. See the
  [release notes](../releases/v0.6.9/NINFER_RELEASE_NOTES.md) for the complete measurement
  boundary and upgrade intent.
- RTX 4090 public-URL acceptance passed
  ([receipt](../releases/v0.6.9/acceptance/rtx4090-public-install.json)): downloaded installer
  accepted the exact already-installed bytes, changed no lifecycle pointers, and requested no
  runtime start; authenticated status 200, anonymous status 401, completion marker accepted;
  stopped state and 450 W restored. This does not claim a fresh install. The published RTX
  5090 image was pulled with an empty Docker configuration and its binary hash matched
  `b8a0a2c3`. Its separate public-profile run retrieved 130,048 tokens exactly at 2,153.6 tok/s
  and decoded at 133.76 tok/s wall. Documented host 2/2 and macOS 10/10 blocks passed
  ([routes](../releases/v0.6.9/acceptance/documented-routes.json)).

### v0.6.8 public release (both mainline lanes on one runtime, and a fork bug fixed)

- Product release: `alphastorm/omp-ninfer@v0.6.8`, superseded by v0.6.9. Both mainline runtime
  components advance to source `68a0722f`: RTX 5090 `v0.6.4-qwen38-5090-beta.1` (image
  `d346174a…`), RTX 4090 native `v0.6.2-qwen38-4090-beta.1` - v0.6.3 plus the live-sibling
  entitlement fix (ninfer#43), the GDN gating launcher partition and its review remediation;
  deployment profile `qwen38-5090-v0.6.3` and configuration `622ab621` unchanged; the RTX 3090
  component and the client unchanged.
- Lane qualification on 2026-09-13 ([5090](../releases/v0.6.8/qualification/rtx5090.json) ·
  [4090](../releases/v0.6.8/qualification/rtx4090.json)): every 5090 gate within noise of v0.6.7
  and the live sibling at 200; 15/15 orchestrated phases on the 4090 lane host; full 102-test suite
  on an ephemeral sm_120a GPU. The 4090 C1 fixture's shift is bisected and explained (EXP-037).
- Route acceptance on 2026-09-13 ([receipt](../releases/v0.6.8/acceptance/documented-routes.json) ·
  [composed](../releases/v0.6.8/acceptance/composed-external-installation.json)): the published
  image by digest on the documented host route, profile gates through the documented tunnel, macOS
  client route 10 of 10, the RTX 4090 component accepted from its public URLs through the
  documented installer; Windows client route carried with reasons.
- Review: two councils on frozen subjects; two P2 findings on the GDN capacity contract closed
  by `68a0722f` before the cut; the strong critic's selector resolves again.
- Upgrade: RTX 5090 - re-clone the tag and rerun the inference-host start block; RTX 4090 -
  install the new component with its `Install-Release.ps1`; sessions and checkpoints carry.

### v0.6.7 public release (the RTX 5090 runtime takes the upstream engine work)

- Product release: `alphastorm/omp-ninfer@v0.6.7` (superseded by v0.6.8). The RTX 5090 runtime component
  advances to `v0.6.3-qwen38-5090-beta.1` (source `8818b88b`, image `fc244576…`): the mainline
  runtime plus a selective backport of 18 upstream commits and one downstream adaptation; deployment
  profile `qwen38-5090-v0.6.3` and configuration `622ab621` unchanged; native components and the
  client unchanged.
- Lane qualification on 2026-09-13 ([receipt](../releases/v0.6.7/qualification/rtx5090.json)): every
  gate within noise of v0.6.2; full 102-test suite on an ephemeral sm_120a GPU.
- Route acceptance on 2026-09-13 ([receipt](../releases/v0.6.7/acceptance/documented-routes.json) ·
  [composed](../releases/v0.6.7/acceptance/composed-external-installation.json)): the published image
  by digest on the documented host route, profile gates through the documented tunnel, macOS client
  route 10 of 10; Windows client and RTX 4090 routes carried with reasons.
- Review: one full council on the frozen subject; the cross-family supplement completed with zero
  findings; the strong critic is recorded missing (harness selector regression) - see the release notes.
- Upgrade: re-clone the tag and rerun the inference-host start block; sessions and checkpoints carry.

### v0.6.6 public release (the pinned client stays on its channel)

- Product release: `alphastorm/omp-ninfer@v0.6.6` (superseded by v0.6.7). No component changed; the
  config every documented route installs turns the pinned client's startup update check off, so
  it no longer advertises an out-of-channel `omp update` (#18, EXP-034).
- Component bytes, deployment profile `qwen38-5090-v0.6.3` and configuration `622ab621...` are
  byte-identical to v0.6.3.
- Route acceptance on 2026-09-12 ([receipt](../releases/v0.6.6/acceptance/documented-routes.json) ·
  [composed](../releases/v0.6.6/acceptance/composed-external-installation.json)): the macOS route
  10 of 10 from an isolated HOME, the native Windows client route 5 of 5, the RTX 4090 native
  route 7 of 7, each reading `startup.checkUpdate` back from the client its own route installed,
  and each fail-closed check still failing its outage request.
- Correction of record: v0.6.5's receipts claimed the appliance's production lane had been
  restored after that window; it had been stopped for a route window with its restart policy
  pinned off and stayed down through the v0.6.5 cut. No v0.6.5 measurement is affected. See
  [the v0.6.6 qualification receipt](../docs/measurements/2026-09-12-client-channel-contract-qualification.json).
- Nothing to reinstall; re-clone the tag and rerun the config install step.

### v0.6.5 public release (the macOS route, as a stranger runs it)

- Product release: `alphastorm/omp-ninfer@v0.6.5` (superseded by v0.6.6). No component changed; the
  quickstart's primary macOS route runs from its own blocks on a Mac with every outcome decided
  by the shell, so every documented route is covered by the runner (EXP-033).
- Component bytes, deployment profile `qwen38-5090-v0.6.3` and configuration `622ab621...` are
  byte-identical to v0.6.3; the three Windows routes carry their v0.6.4 acceptance by hash.
- Route acceptance on 2026-09-12 ([receipt](../releases/v0.6.5/acceptance/documented-routes.json) ·
  [composed](../releases/v0.6.5/acceptance/composed-external-installation.json)): client install
  from the public URL, tunnel, key, provider, fail-closed configuration, tool, Vision, resume, a
  server restart from the Mac with the session continued, fail-closed with the tunnel stopped -
  10 of 10 steps.
- Three documentation defects fixed at source (the key copy and restart blocks against a Windows
  OpenSSH destination; an interactive acceptance no runner could score) and three runner defects
  (a backgrounded block ending the run early as a pass, an inherited ERR trap, a tunnel whose
  exec'd `ssh` outlived its wrapper), each a regression test.
- Nothing to reinstall; re-clone the tag for the corrected blocks.

### v0.6.4 public release (the documented routes, as a stranger runs them)

- Product release: `alphastorm/omp-ninfer@v0.6.4` (superseded by v0.6.5). No component changed; every
  documented Windows route runs from its own quickstart blocks on a stock host, and a clone
  yields the recorded bytes on every platform (EXP-032).
- Component bytes (RTX 5090 image `a62dd5b8...`, RTX 4090 `v0.6.1-qwen38-4090-beta.1`, RTX 3090
  `v0.2.5-qwen38-3090-beta.1`, the model, the OMP client), deployment profile
  `qwen38-5090-v0.6.3` and configuration `622ab621...` are byte-identical to v0.6.3.
- Route acceptance on 2026-09-11 ([receipt](../releases/v0.6.4/acceptance/documented-routes.json) ·
  [composed](../releases/v0.6.4/acceptance/composed-external-installation.json)): RTX 4090 native
  from an uninstalled host through acceptance, twice (first install with the 18 GB artifact from
  Hugging Face, then the rerun path); RTX 5090 host and client halves including Vision and the
  fail-closed check.
- Six documentation defects fixed at source: Windows' Restricted execution policy, the Store's
  `python3` shortcut, `core.autocrlf` rewriting the hash chain, .NET 5 APIs in Windows
  PowerShell, a menu block run as a sequence, provider blocks opening the interactive session.
- Re-clone the tag if an earlier clone was made with `core.autocrlf=true`; installed lanes and
  sessions are unaffected.

### v0.6.3 public release (the documented route is durable)

- Product release: `alphastorm/omp-ninfer@v0.6.3` (superseded by v0.6.4). The documented RTX 5090
  container route mounts a durable session store, and the identity its server reports is the
  identity of the configuration it runs (EXP-031).
- No component changed. The RTX 5090 runtime `v0.6.2-qwen38-5090-beta.1` (image `a62dd5b8...`,
  binary `6ab904d7...`), the RTX 4090 component `v0.6.1-qwen38-4090-beta.1`, the RTX 3090
  component `v0.2.5-qwen38-3090-beta.1`, the model and the OMP client are byte-identical to
  v0.6.2 and carry their receipts by hash.
- Deployment profile `qwen38-5090-v0.6.3` (configuration `622ab621...`): the v0.4.8 tuning plus
  the session store the published route now mounts at `/checkpoints`, under the repository's
  io_uring seccomp profile.
- What the predecessor route did instead, measured on the same host and bytes: `POST
  /v1/ninfer/checkpoints` answered 404, a continuation after a container restart answered
  `previous_response_not_found`, and the server reported configuration `5eb8a557` - the identity
  of a checkpointed configuration it was not running. Its host-network bind was also unreachable
  from both Windows and the WSL2 distro.
- Route acceptance on 2026-09-11 from a clean clone
  ([route receipt](../releases/v0.6.3/acceptance/rtx5090-public-route.json) ·
  [composed](../releases/v0.6.3/acceptance/composed-external-installation.json)): explicit save
  302 MB in 1.3 s, full container stop with the store intact and operator-owned, ready again in
  25.5 s, continuation exact in 1.17 s with 122 cached input tokens, 5.2 GB restored in 3.9 s and
  3.7 s, flipped payload byte refused, anonymous status 401, host restored.
- Upgrading from v0.6.2: stop the old container and start the route with `--checkpoint-dir`.
  Sessions on the old route were never saved, so there is nothing to migrate.

### v0.6.2 public release (three cards, one runtime tree)

- Product release: `alphastorm/omp-ninfer@v0.6.2` (superseded by v0.6.3). The RTX 5090 container lane
  moves onto the mainline runtime, so all three lanes are built from one commit (EXP-030).
- RTX 5090 runtime component `ninfer@v0.6.2-qwen38-5090-beta.1` (runtime fork `63f28c95`,
  archive `05aa9c4b...`, 319,416,469 bytes, server binary `6ab904d7...`, image `a62dd5b8...`),
  deployment profile `qwen38-5090-v0.6.2` (configuration `5eb8a557...`): the v0.4.8 argument set
  unchanged - BF16 KV, MTP3, prefill chunk 1,024, 131,072-token context, four device-state
  slots, 24 host-state slots, eight private continuations. Qualified on the owner appliance
  7/7 gates ([receipt](../releases/v0.6.2/qualification/rtx5090.json), EXP-030), then every gate
  a published artifact can answer re-run against the anonymously pulled image.
- The RTX 4090 component `v0.6.1-qwen38-4090-beta.1`, the RTX 3090 component
  `v0.2.5-qwen38-3090-beta.1`, their profiles, and the OMP client are unchanged from v0.6.1 and
  carry by hash. The RTX 3090 mainline candidate ships separately when its host returns.
- Composed external-installation acceptance on 2026-09-11 from the published URLs
  ([receipt](../releases/v0.6.2/acceptance/composed-external-installation.json)): all four RTX
  5090 assets downloaded anonymously and hashed exactly, the closed checksum set matched, the
  image pulled anonymously by digest with an empty credential store, and the lane's own
  acceptance ([receipt](../releases/v0.6.2/acceptance/rtx5090-public-image.json)) matched the
  served identity, refused anonymous status (401), completed exactly, held the lane's gates on
  the published bytes, and restored the host.
- Numbers are within run-to-run noise of v0.5.1: 2,169.9 tok/s prefill at 130,048 tokens,
  132.53 tok/s decode, a 5.2 GB session restored in 3.6-4.0 s, 8/8 sibling forks on the shared
  anchor across a verified restart.
- Known limitations are v0.6.1's, unchanged. Sessions checkpointed under the v0.5.1 runtime
  replay once from the OMP transcript on this upgrade: checkpoints bind the runtime fingerprint.

### v0.6.1 public release (a managed stop saves your session)

- Product release: `alphastorm/omp-ninfer@v0.6.1` (superseded by v0.6.2). A managed stop of the RTX
  4090 native lane now reaches the server's graceful shutdown (EXP-028, EXP-029).
- RTX 4090 native component `ninfer@v0.6.1-qwen38-4090-beta.1` (runtime fork `63f28c95`,
  package `4390a8cb...`, 573,795,974 bytes, configuration `a938aaa1...`, server binary
  `39490a44...`): the same engine and profile as v0.6.0 with the manager-signalled stop, the
  per-release capability record, the shutdown report, and the fail-closed controller. Qualified
  on the owner rig through the lane's own lifecycle tool, 15/15 phases and 103/103 registered
  tests, after two rounds of independent focused review
  ([receipt](../releases/v0.6.1/qualification/rtx4090.json), EXP-029).
- RTX 5090 runtime `v0.5.1-qwen38-5090-beta.1`, deployment profile `qwen38-5090-v0.5.1`, the
  RTX 3090 component `v0.2.5-qwen38-3090-beta.1`, and the OMP client are unchanged from v0.6.0
  and carry by hash. The RTX 3090 mainline candidate ships separately when its host returns.
- Composed external-installation acceptance on 2026-09-10 from the published URLs
  ([receipt](../releases/v0.6.1/acceptance/composed-external-installation.json)): all ten RTX
  4090 assets downloaded anonymously and hashed exactly; the lane's public-URL install
  acceptance ([receipt](../releases/v0.6.1/acceptance/rtx4090-public-install.json)) had the
  downloaded installer accept the installed release as the exact qualified bytes, matched the
  served identity, refused anonymous status (401), completed, and restored the host.
- Known limitation, RTX 4090: a crash, a power loss, or a stop whose graceful wait expires still
  loses what was never published; the stop receipt records which happened. The RTX 3090 lane
  keeps the v0.2.5 behaviour - a managed stop terminates - until its mainline candidate ships.
- A rollback to v0.6.0 is stopped by termination as before: the capability lives in each
  release's record, and the shared controller passes the new flags only to a release that
  declares them. Do not delete `release/v0.2.0-beta.1-final` from origin; the tag gate reads
  pinned client receipts from it.

### v0.6.0 public release (RTX 4090 on the mainline runtime)

- Product release: `alphastorm/omp-ninfer@v0.6.0` (superseded by v0.6.1). The RTX 4090 native lane
  moves off its divergent `v0.2.x` branch onto the mainline runtime (EXP-025 to EXP-027).
- RTX 4090 native component `ninfer@v0.6.0-qwen38-4090-beta.1` (runtime fork `075d442e`,
  package `da343d64...`, 573,714,539 bytes, configuration `5ee3fb71...`, server binary
  `b3f9374f...`): the mainline runtime built for Ada with the Windows platform code, replacing
  the divergent `v0.2.x` lane branch. Qualified on the owner rig through the lane's own
  lifecycle tool, 15/15 phases, and 101/101 registered tests with the artifact exported
  ([receipt](../releases/v0.6.0/qualification/rtx4090.json), EXP-027).
- RTX 5090 runtime `v0.5.1-qwen38-5090-beta.1`, deployment profile `qwen38-5090-v0.5.1`, and
  the OMP client are unchanged and carry by hash. The RTX 3090 lane stays on
  `v0.2.5-qwen38-3090-beta.1`: its host is unavailable until about 2026-09-21, so its mainline
  candidate is neither built nor cut here. Precedent for a single-lane release: v0.4.2 (RTX
  4090 alone) and v0.4.5 (RTX 3090 alone).
- Composed external-installation acceptance on 2026-09-10 from the published URLs
  ([receipt](../releases/v0.6.0/acceptance/composed-external-installation.json)): all ten RTX
  4090 assets downloaded anonymously and hashed exactly; the lane's public-URL install
  acceptance ([receipt](../releases/v0.6.0/acceptance/rtx4090-public-install.json)) had the
  downloaded installer accept the installed release as the exact qualified bytes, matched the
  served identity, refused anonymous status (401), completed, and restored the host; the RTX
  5090 lane's served identity was re-read live and every RTX 5090 and RTX 3090 asset URL
  answers.
- Known limitation carried on both native lanes: a managed stop on Windows terminates the
  server, so a session that was never published - automatically above 32,768 frontier tokens,
  or explicitly through `POST /v1/ninfer/checkpoints` - does not survive a deliberate stop.

### v0.5.1 public release (warm arrival across a restart)

- Product release: `alphastorm/omp-ninfer@v0.5.1` (superseded by v0.6.0). The second v0.5 deliverable
  on the RTX 5090: a checkpointed template arrives warm across a restart (EXP-022 to EXP-024).
  - RTX 5090 runtime component
    [`ninfer@v0.5.1-qwen38-5090-beta.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.5.1-qwen38-5090-beta.1)
    (source `d956e6d6`, archive `c0189387...`, SBOM `9f965373...`,
    [source archive](https://github.com/alphastorm/ninfer/releases/tag/v0.5.1-qwen38-5090-source.1)
    `4359c814...`), runtime image `ghcr.io/alphastorm/ninfer-runtime@sha256:12ef2d9e...` from the
    [runtime receipt release](https://github.com/alphastorm/ninfer/releases/tag/v0.5.1-qwen38-5090-runtime-beta.1);
    the binaries inside the published image measure byte-identical to the qualified candidate
    (`71edc2f6`). Deployment profile `qwen38-5090-v0.5.1` (configuration `efacac23...`) keeps the
    `qwen38-5090-v0.4.8` context-cache arguments.
  - RTX 4090 `ninfer@v0.2.3-qwen38-4090-durable.1` and RTX 3090 `ninfer@v0.2.5-qwen38-3090-beta.1`
    are byte-identical to v0.5.0; their receipts and public-URL install acceptances carry by hash.
- RTX 5090 requalified on 2026-09-08 through the lifecycle tool from the published image: exact
  130,048-token retrieval at 2,180 tok/s, 138.2 decode tok/s, agent protocol with no
  resurrection, 4/4 fanout forks on the anchor path at 57.9K and 67.7K in-process and again after
  a verified restart, warm arrival in both post-restart orders, 5.2 GB restore in 3.8-4.4 s and a
  tampered payload refused ([receipt](../releases/v0.5.1/qualification/rtx5090.json)).
- Composed external-installation acceptance on 2026-09-08 from the published URLs: anonymous pull
  by digest, lifecycle launch bound to the manifest identities, anonymous status refused (401),
  identity re-read, one authenticated completion
  ([receipt](../releases/v0.5.1/acceptance/composed-external-installation.json)); the five RTX 5090
  assets and the runtime-image receipt downloaded anonymously and hashed exactly, and every native
  asset URL answers.
- Correction carried in this release: through v0.5.0 the compatibility authority's native
  variant rows still named the v0.2.2/v0.2.0 components (and a 65,536-token RTX 3090 ceiling), the
  root profiles' `--binary-sha256`/`--config-sha256` launch arguments named the v0.4.3 runtime,
  the qualification summary's runtime identity carried a stale upstream commit and source-archive
  hash, and the RTX 5090 receipt URLs pinned a commit that never contained them. The manifests
  themselves were exact; the derived records had drifted. v0.5.1 rebinds every derived record
  from the manifest and `scripts/verify_release.py` now refuses a ready release whose derived
  records disagree with it, and (with `--check-pins`) whose pinned URLs do not serve their
  recorded bytes.
- The owner's appliance promotes to `qwen38-5090-v0.5.1` through its own gate after the product
  release.

### v0.5.0 public release (sessions leave the machine)

- Product release: `alphastorm/omp-ninfer@v0.5.0`, GitHub `Latest`. The first v0.5 deliverable
  (EXP-018): origin-authenticated checkpoints on every lane and verified replication out and
  back, each native lane requalified on its own rig on 2026-09-05:
  - RTX 4090: `ninfer@v0.2.3-qwen38-4090-durable.1` (qualified head `e186e04e`, packaging
    `ccdac145`), origin-authenticated checkpoint manifests, qualified on the owner rig
    ([receipt](../releases/v0.5.0/qualification/rtx4090.json)).
  - RTX 3090: `ninfer@v0.2.5-qwen38-3090-beta.1` (commit `9719ea09`), origin-authenticated
    checkpoint manifests, 14/14 orchestrator phases
    ([receipt](../releases/v0.5.0/qualification/rtx3090.json)).
  - RTX 5090 runtime, profile `qwen38-5090-v0.4.8`, and the OMP client are unchanged.
- Replication proof on all three lanes with `scripts/sync_probe.py`
  ([5090](measurements/2026-09-05-sync-probe-rtx5090.json) ·
  [4090](measurements/2026-09-05-sync-probe-rtx4090.json) ·
  [3090](measurements/2026-09-05-sync-probe-rtx3090.json)).
- Composed external-installation acceptance rerun on 2026-09-05 from the published component URLs
  ([receipt](../releases/v0.5.0/acceptance/composed-external-installation.json)) with native
  public-URL install acceptances on the
  [RTX 3090](../releases/v0.5.0/acceptance/rtx3090-public-install.json) and
  [RTX 4090](../releases/v0.5.0/acceptance/rtx4090-public-install.json).

### v0.4.9 public release (native-lane restore path fixed; superseded by v0.5.0)

- Product release: `alphastorm/omp-ninfer@v0.4.9`, GitHub `Latest`. The checkpoint restore path on
  both native Windows lanes is fixed at source (EXP-017,
  [ninfer#36](https://github.com/alphastorm/ninfer/issues/36)) and each lane requalified its exact
  release binary on its own rig on 2026-09-05:
  - RTX 4090: `ninfer@v0.2.2-qwen38-4090-durable.1` (qualified head `9834bf58`, packaging
    `e16fa354`, package `d6f162cb...`), qualified on the owner rig with the post-restart
    continuation of the 102,060-token session in 9.5 s (225.6 s on v0.2.1)
    ([receipt](../releases/v0.4.9/qualification/rtx4090.json)).
  - RTX 3090: `ninfer@v0.2.4-qwen38-3090-beta.1` (commit `cd06e782`, package `e4fbbfca...`),
    14/14 orchestrator phases ([receipt](../releases/v0.4.9/qualification/rtx3090.json)).
  - RTX 5090 runtime, profile `qwen38-5090-v0.4.8`, and the OMP client are unchanged.
- Restore probe, shipped versus candidate on the same sessions: RTX 4090 146.6 s / 133.4 s ->
  5.6 s / 5.6 s ([shipped](measurements/2026-09-05-restore-probe-rtx4090-v0.2.1.json) ·
  [candidate](measurements/2026-09-05-restore-probe-rtx4090-candidate.json)); RTX 3090
  91.8 s / 92.2 s -> 10.8 s / 10.7 s ([shipped](measurements/2026-09-05-restore-probe-rtx3090.json) ·
  [candidate](measurements/2026-09-05-restore-probe-rtx3090-candidate.json)).
- Composed external-installation acceptance rerun on 2026-09-05 from the published component URLs
  ([receipt](../releases/v0.4.9/acceptance/composed-external-installation.json)) with native
  public-URL install acceptances on the
  [RTX 3090](../releases/v0.4.9/acceptance/rtx3090-public-install.json) and
  [RTX 4090](../releases/v0.4.9/acceptance/rtx4090-public-install.json).

### v0.4.8 public release (requalified lane configurations; superseded by v0.4.9)

- Product release: `alphastorm/omp-ninfer@v0.4.8`, GitHub `Latest`. Each lane ships on its own
  best measured configuration, requalified on its own rig on 2026-09-05 and accepted from the
  published URLs:
  - RTX 5090: same runtime component (`v0.4.5-qwen38-5090-beta.1`, image `876c7809...`) under
    the new deployment profile `qwen38-5090-v0.4.8` (configuration `95765a38...`:
    `--max-private-continuations 8 --device-state-slots 4 --host-state-slots 24`, so sibling forks
    of a stored template keep the shared base anchor) - measured through the lifecycle tool
    ([receipt](../releases/v0.4.8/qualification/rtx5090.json)).
  - RTX 4090: [`ninfer@v0.2.1-qwen38-4090-durable.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.2.1-qwen38-4090-durable.1)
    (commit `b9c4636b`, package `1c66f7d5...`), prefill chunk 2,048
    ([receipt](../releases/v0.4.8/qualification/rtx4090.json)).
  - RTX 3090: [`ninfer@v0.2.3-qwen38-3090-beta.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.2.3-qwen38-3090-beta.1)
    (commit `2ce6c9dc`, package `96c9c37f...`), 131,072-token context
    ([receipt](../releases/v0.4.8/qualification/rtx3090.json)).
- Composed external-installation acceptance rerun on 2026-09-05
  ([receipt](../releases/v0.4.8/acceptance/composed-external-installation.json)) with native
  public-URL install acceptances on the
  [RTX 3090](../releases/v0.4.8/acceptance/rtx3090-public-install.json) and
  [RTX 4090](../releases/v0.4.8/acceptance/rtx4090-public-install.json), driven by
  [`scripts/hosts/accept-native-public-install.ps1`](../scripts/hosts/accept-native-public-install.ps1).

### v0.4.7 public release (corrects v0.4.6 asset URLs)

- Product release: `alphastorm/omp-ninfer@v0.4.7`, GitHub `Latest`. Identical components to
  v0.4.6; the v0.4.6 manifest bound product-versioned runtime asset names that 404 (tags are
  immutable, so the correction ships as a new release).

### v0.4.6 public release (superseded)

- Product release: `alphastorm/omp-ninfer@v0.4.6`, GitHub `Latest`.
- The RTX 5090 durable container moves to
  [`ninfer@v0.4.5-qwen38-5090-beta.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.4.5-qwen38-5090-beta.1)
  (image digest `876c7809...`): checkpoint manifest ORIGIN authentication (closes
  [ninfer#32](https://github.com/alphastorm/ninfer/issues/32)) - every save publishes an HMAC
  tag keyed outside the checkpoint root, loads verify before trusting manifest content, and
  `--session-checkpoint-require-origin-auth` is the strict posture for future NAS/S3 import
  (council CRS-origin-auth). Rollback-safe additive design: prior binaries read the same store.
  4090/3090 components rebound unchanged.

### v0.4.5 public release

- Product release: `alphastorm/omp-ninfer@v0.4.5`, GitHub `Latest`.
- The RTX 3090 native Windows lane joins the durable train at
  [`ninfer@v0.2.2-qwen38-3090-beta.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.2.2-qwen38-3090-beta.1):
  buffered checkpoint export off the engine lock, every-turn automatic saves with sustained-idle
  debounce and redundant-frontier skip, explicit `POST /v1/ninfer/checkpoints`, lineage-aware
  lazy-restore freshness guard, idempotent exact-endpoint restore, and constant-time
  session-ownership comparisons (council CRS-durable-3090, 14/14 rig qualification: 90.0 tok/s
  at 93.4% MTP under 300 W, 310 MB durable restart with exact recall). 5090/4090 components
  rebound unchanged.

### v0.4.4 public release

- Product release: `alphastorm/omp-ninfer@v0.4.4`, GitHub `Latest`.
- The RTX 5090 durable container moves to
  [`ninfer@v0.4.4-qwen38-5090-beta.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.4.4-qwen38-5090-beta.1)
  (image digest `546bb6a8...`): checkpoint export decoupled from the engine through a bounded
  buffered writer (fail-before-publication preserved), automatic saves debounced to
  sustained-idle with a redundant-frontier skip, and lazy restore repairing partially resident
  sessions (council CR-20260831-ckptdecouple). Warm follow-up during checkpoint traffic
  15.26 s → 0.91 s; explicit save 31.6 s → 13.8 s; four fanout branches 0.90-1.01 s with
  automatic saves at defaults. 4090/3090 components rebound unchanged.

### v0.4.3 public release

- Product release: `alphastorm/omp-ninfer@v0.4.3`, GitHub `Latest`.
- The RTX 5090 durable container moves to
  [`ninfer@v0.4.3-qwen38-5090-beta.2`](https://github.com/alphastorm/ninfer/releases/tag/v0.4.3-qwen38-5090-beta.2)
  (image digest `f66708f5...`): same-lane agent fanout through private long anchors,
  checkpoint-import integrity (streamed re-hash, fail-closed coverage, corrupt-generation
  quarantine), symlink-refusing export writes, constant-time credential equality, an explicit
  compute-to-transfer export fence, and the session-isolation set proven on the 4090 durable
  train (council CR-20260831-fanout43). 4090/3090 components rebound unchanged.

### v0.4.2 public release

- Product release: `alphastorm/omp-ninfer@v0.4.2`, GitHub `Latest`.
- The RTX 4090 native Windows lane moves to the durable v0.2 package
  ([`ninfer@v0.2.0-qwen38-4090-durable.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.2.0-qwen38-4090-durable.1)):
  the durable-train rebase (council CR-20260831-durable4090), the ninfer#28 pinned-client
  status fix, and five upstream ports. Requalified on the owner rig; the pinned client now
  cold-starts on every lane. 5090/3090 components rebound unchanged.

### v0.4.1 public release

- Product release: `alphastorm/omp-ninfer@v0.4.1`, GitHub `Latest`.
- The RTX 5090 durable container moves to
  [`ninfer@v0.4.1-qwen38-5090-beta.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.4.1-qwen38-5090-beta.1)
  (image digest `ce3cd215...`): health-gated checkpoint quota transition, post-publish
  reclamation that never fails an acknowledged save, and named skip reasons in server logs
  (council CR-20260831-v041delta). 4090/3090 components rebound unchanged.
- Release bytes were built in the pinned CI container on the owner appliance after a RunPod
  SECURE allocation outage; the route is documented in the component-release receipt.

### v0.4.0 public release

- Product release: `alphastorm/omp-ninfer@v0.4.0`, GitHub `Latest`.
- The RTX 5090 container lane moves to a new durable runtime image
  ([`ninfer@v0.4.0-qwen38-5090-beta.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.4.0-qwen38-5090-beta.1),
  image digest `8de5efdf...`): transactional session checkpoints restored across docker restarts.
  Durability now ships on all three lanes. 4090/3090 components unchanged.

### v0.3.2 public release

- Product release: `alphastorm/omp-ninfer@v0.3.2`, GitHub `Latest`.
- Corrective release: fixes the v0.3.1 RTX 4090 qualification summary whose limitations block
  contradicted its own MTP3 receipts (template residue). Component bytes and receipts unchanged.

### v0.3.1 public release

- Product release: `alphastorm/omp-ninfer@v0.3.1`, GitHub `Latest`.
- Change over v0.3.0: the RTX 4090 lane moves to its qualified MTP3 package
  ([`alphastorm/ninfer@v0.3.1-qwen38-4090-mtp3.2`](https://github.com/alphastorm/ninfer/releases/tag/v0.3.1-qwen38-4090-mtp3.2)),
  promoted by the recorded two-arm comparison decision; all other component identities unchanged.

### v0.3.0 public release

- Product release: `alphastorm/omp-ninfer@v0.3.0`.
- OMP source/client: `alphastorm/oh-my-pi@omp-v18.0.9-ninfer-beta.2`; the unchanged native archives
  remain at `alphastorm/homebrew-omp@omp-18.0.9-cross-platform-beta-2`.
- RTX 3090 runtime component: release-cut slot
  [`alphastorm/ninfer@v0.3.0-qwen38-3090.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.3.0-qwen38-3090.1),
  which must resolve before cut; package
  `ninfer-rtx3090-omp-v0.2.1-beta.1-windows-x86_64-cuda13.3-rtx3090.tar.gz`, SHA-256
  `e7642d7069e85de497731735bde92a0c9b23f5b486848ab8cbe5c4da222baf97`,
  `573,355,399` bytes, source commit `872ee508c1f9c46fa38f4170c7e21f254a79e21f`, and
  [qualification receipt](measurements/2026-08-30-rtx3090-parity.json).
- RTX 4090 runtime component: rebinds the published
  `alphastorm/ninfer@v0.2.0-qwen38-4090-beta.1` component without changing its bytes.
- RTX 5090 runtime component: source `alphastorm/ninfer@6efa06505` from
  `vendor/neroued-dev`; OCI digest, SBOM identity, and qualification receipt are pending publication
  and remain release blockers until the product manifest binds them.

### Prior release record: v0.2.0-beta.1

- Product prerelease: `alphastorm/omp-ninfer@v0.2.0-beta.1`.
- RTX 5090 runtime component: `alphastorm/ninfer@v0.2.0-qwen38-5090-beta.2`.
- Native client component: `alphastorm/homebrew-omp@omp-18.0.9-cross-platform-beta-2`.
- Public OMP source/client mirror: `alphastorm/oh-my-pi@omp-v18.0.9-ninfer-beta.2`.
- Native runtime components: RTX 3090 preview at
  `alphastorm/ninfer@v0.2.0-qwen38-3090-beta.1` and qualified RTX 4090 beta at
  `alphastorm/ninfer@v0.2.0-qwen38-4090-beta.1`.

A component tag does not make the product release ready. The product tag must carry the exact ready
manifest and qualification summary.

## Release state transition

Each `releases/<version>/manifest.json` has three valid states:

### `draft`

- incomplete external artifact fields may be null;
- `publication.blockers` must be non-empty;
- installation scripts validate the static contract but refuse to start a release; and
- no README may describe it as installable.

### `candidate`

- every upstream OMP binary, NInfer OCI/SBOM, model, source, and configuration identity required
  for installation is immutable and published;
- the upstream OMP release provenance and per-platform binary hashes are verified by
  `scripts/verify_release.py`;
- `publication.blockers` remains non-empty and the qualification still records that external
  installation has not passed;
- `python3 scripts/verify_release.py --require-installable` passes; and
- maintainers may run the external-install acceptance from that exact commit, but no product tag
  or public-release readiness claim exists yet.

### `ready`

- exact upstream OMP release version, source commit, and per-platform binary URL/size/hash;
- digest-pinned NInfer OCI reference, manifest digest, SBOM URL/hash, source, and binary hash;
- exact Qwen artifact URL/revision/size/hash;
- qualification summary URL/hash matching checked-in bytes;
- external installation passed from public URLs on the supported topology;
- no remaining publication blockers; and
- `python3 scripts/verify_release.py --require-ready` passes.

`ready` means the package is technically cuttable. It does not grant authority to create repositories,
push commits/tags, upload images/assets, publish a GitHub release, or modify the Homebrew tap.
Authorization for those external effects remains separate and bounded.

## Candidate freeze

Before the final external-install smoke, freeze these bytes together:

1. upstream OMP release binaries for Windows x64, Linux x64 and macOS arm64;
2. NInfer OCI manifest and every referenced platform blob;
3. NInfer SBOM;
4. Qwen artifact revision;
5. profile JSON and fail-closed/provider fragments;
6. product qualification summary;
7. every declared native runtime package, source archive, SBOM, installer/controller, and
   qualification receipt; and
8. product manifest.

Changing executable code, the model, server arguments, OMP state semantics, transport, security
boundary, or support claim invalidates dependent evidence and requires a new candidate. Editing a
mutable tag or rebinding an old qualification to new bytes is prohibited.

## Next native release sequencing

For the next release after v0.2, close shared native-Windows correctness before variant-specific
builds or GPU leases:

1. land checkpoint deletion, protected state, bearer-secret ACLs, GPU ownership, packaging, and
   receipt logic once on a shared native-Windows base branch;
2. freeze and independently review that source candidate before compiling, and close every P1/P2
   finding at source level;
3. run the shared failure matrix up front: cross-session LRU during DELETE, quota GC, NULL DACL,
   raced/precreated/reparse roots, retained-secret ACL after real upgrade/rollback, non-default state
   roots, malformed nvidia-smi output, and SPDX inclusion in SHA256SUMS;
4. make every generated fault harness enumerate its substituted components; security claims require
   exact shipped scripts and real Windows effective-access tests;
5. schema-validate qualification receipts and prove package, SPDX SBOM, scripts, checksums, and final
   sidecar form one closed identity set; and
6. only then derive 3090/4090 packages and run hardware once, in this order: neutral build, package
   and security verification, GPU protocol/restart/performance/OMP gates, then receipt-only closure
   review.

The RTX 3090 parity candidate exercised this sequence end to end with one checkpointed command:
preflight, neutral build, private-path scan, deterministic package, managed install, protocol,
64K, restart, rollback, security, OMP, C1, receipt, and 370 W restoration. The sequence prevents
shared correctness classes from being discovered after variant binaries and hardware evidence are
already frozen.

## External-install acceptance

The v0.2 final gate used clean isolated macOS arm64, Windows x64, and Linux x64 client roots plus
the separately qualified runtime identities. It downloaded the public clients and compatibility
authority, then bound the result into the `ready` manifest and qualification summary before the
product tag. The gate proved:

- all three published client archive and installed binary checksums plus exact OMP version;
- exact served model artifact hash;
- digest-pinned NInfer image, binary hash, and authenticated identity;
- Windows local-loopback, Linux local-loopback, and managed macOS SSH client paths;
- explicit fail-closed OMP provider resolution;
- text/tool, image, stateful follow-up, and OMP exit/resume;
- disconnected-tunnel failure with no cloud answer;
- clean owned-runtime stop/restore while retaining user data; and
- exact native 3090/4090 package and qualification bindings without activating those routes.

The external smoke qualifies the installation composition; it does not repeat CUDA numerical or
performance qualification without a concrete runtime change.

## Cut procedure

The release tree is staged as a draft and cut with the pin dance; every step is a script and
the verifier decides what remains:

1. `scripts/stage_release.py --from <previous> --release <new> ...` copies the tree, rewrites
   the component and identity pins (including `--config-sha`, the lifecycle configuration
   identity of the new deployment profile), and recomputes the chain with
   `scripts/rebind_release.py --draft`. The root authority and profiles stay on the previous
   release: that is the checked-in draft posture.
2. Author the evidence: install the lane receipt, write the composed acceptance, rewrite the
   qualification summary's gates and prose, CHANGELOG/RELEASES/BENCHMARKS/FACTS/README, and the
   drift-test pins. Rerun `--draft` after every edit; commit.
3. Cut: `scripts/rebind_release.py --release <new> --pin <commit containing the final lane
   receipts> --stage lane` promotes the release's compatibility copy to the root authority,
   rewrites the root profiles and launcher examples from the manifest, pins the authority's
   receipt URLs, and reruns the chain. A draft manifest becomes `candidate`, not `ready`.
   An upstream-release client is copied wholesale from its platform row before consuming
   a root `status:candidate` marker (which means client-unbound-by-named-release). Fork
   and non-promoted markers remain. Verify `--require-installable`; commit the candidate
   for the accountable lead's published-image acceptance window. Do not hand-clear guards.
4. Only after fresh platform/documented-route acceptance, bind the real receipts and
   ready/external-acceptance transition. `--pin <that commit> --stage acceptance`; commit.
   `--pin <that commit> --stage manifest`;
   commit. The manifest stage runs `verify_release.py --require-ready --check-pins`, which
   reads every pinned evidence URL out of local git history and requires it to serve exactly
   the recorded SHA-256; CI repeats it on the release tag with full history.

## Release notes

The OMP client is not built or published here. From v0.8.0 a release pins an unmodified upstream
Oh My Pi release binary per platform: `scripts/stage_release.py --omp-component` stages the
upstream provenance and the darwin-arm64, windows-x64 and linux-x64 binaries, whose raw hashes must
equal their asset hashes, and `scripts/verify_release.py` checks every binding. Client acceptance
is never inherited from a predecessor release.

Both native runtime lanes use `scripts/hosts/cut-ninfer-4090-component.sh --lane rtx3090|rtx4090` after the
lane's canonical native qualification (`tools/qualification/qualify_native.py` in the runtime
fork). The default mode checks that the outer `SHA256SUMS` closes and verifies the asset
directory, that the package build receipt and the lane specification at the commit name the same
release and source, that the source archive's tar stream is byte-identical to `git archive` of
the commit, and that neither the tag nor the release exists. `--publish` is founder-only: it
pushes the component tag and creates one prerelease with the closed set; binding it into a
product release stays `scripts/bind_native_variant.py`.

The historical cutter and `accept-rtx4090-route.{py,ps1}` filenames each remain the single
implementation for both native lanes. Omit `--lane` / `-Lane` for unchanged RTX 4090 behavior;
RTX 3090 requires an explicit lane and the Python route driver also requires its `--host`.
It uses state root `C:/ProgramData/NInfer/qwen38-3090-native`, task
`NInfer-Qwen38-3090-Native` and a stopped 370 W owner baseline, not the RTX 4090's 450 W
and container-host pause prerequisite. Existing hold files are snapshotted and audited on both
lanes. Do not run a window with inference processes, listeners or an outstanding GPU lease.

### Completed v0.9.1 RTX 3090 addition and future lane procedure

The RTX 3090 addition is complete: v0.9.1 accepted all five documented routes on candidate
`c55185dd`, with the published package `da1d62f2` and all three hosts restored.
[Lane qualification](../releases/v0.9.1/qualification/rtx3090.json) ·
[Documented routes](../releases/v0.9.1/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.9.1/acceptance/composed-external-installation.json).

The commands below retain the completed v0.9.0-to-v0.9.1 cut as a worked example, not an
instruction to republish it. For a future lane, substitute its release, candidate, lane,
component identities, state root and fresh workspaces while preserving the composer, rebind
and verification sequence. Obtain real qualification and package-build receipts plus the
complete asset directory for that lane; never infer a package hash or hardware result.
The v0.9.1 component uses source
`f08309da3cc1d4226d127b7c9ce22267d12070cc` (v0.9.0's RTX 5090 source `e20060b6` plus the
controller fix that lets a rollback launch a predecessor whose config predates
`context_cache.host_kv_mib`), tag `v0.6.2-qwen38-3090-beta.1` and package
`ninfer-rtx3090-native-v0.6.2-beta.1-windows-x86_64-cuda13.3-rtx3090.tar.gz`.
`ASSETS` must name a verified local copy of the complete component asset directory.

```sh
export NINFER_RUNTIME_DIR=/path/to/ninfer-checkout
export ASSETS=/path/to/verified-package-a NOTES=/path/to/component-notes.txt
SUMS_SHA=$(shasum -a 256 "$ASSETS/SHA256SUMS" | cut -d' ' -f1)
bash scripts/hosts/cut-ninfer-4090-component.sh --lane rtx3090 --version v0.6.2 \
  --commit f08309da3cc1d4226d127b7c9ce22267d12070cc --assets "$ASSETS" \
  --checksums-sha "$SUMS_SHA" --notes-file "$NOTES" --dry-run
# FOUNDER-ONLY / AGENT MUST NOT EXECUTE: repeat that command with --publish instead of --dry-run.
```

After founder publication, stage the next product release with the existing lanes' component
pins and deployment profiles intact. In the worked example, v0.9.0 is the predecessor, not
the current release. Passing the existing stock-client descriptor resets client/route acceptance
without changing the OMP binary. Its predecessor-pin warnings are expected because OMP remains
18.4.0; do not use `--require-clean-client` to demand a different client identity.

```sh
python3 - <<'PY'
import json, subprocess, sys
from pathlib import Path
n = json.loads(Path('releases/v0.9.0/manifest.json').read_text())['components']['ninfer']
flags = {
    '--release-tag': n['release_tag'], '--source-tag': n['source_archive_url'].split('/')[-2],
    '--source-commit': n['source_commit'], '--binary-sha': n['server_binary_sha256'],
    '--archive-sha': n['binary_archive_sha256'], '--source-archive-sha': n['source_archive_sha256'],
    '--sbom-sha': n['sbom_sha256'], '--image-digest': n['oci_manifest_digest'],
    '--runtime-receipt-release': n['runtime_receipt_release'],
    '--archive-name': n['binary_archive_url'].split('/')[-1],
}
subprocess.run([sys.executable, 'scripts/stage_release.py', '--from', 'v0.9.0', '--release', 'v0.9.1',
                '--keep-deployment-profile', '--omp-component',
                'releases/v0.9.0/qualification/client-components.json',
                *[arg for pair in flags.items() for arg in pair]], check=True)
PY
cp "$QUALIFICATION_RECEIPT" releases/v0.9.1/qualification/rtx3090.json
git add releases/v0.9.1
git commit -m 'chore(release): stage v0.9.1 with native 3090 qualification'
python3 scripts/bind_native_variant.py --release v0.9.1 --lane rtx3090 --add \
  --maximum-context-tokens 131072 --qualification-commit "$(git rev-parse HEAD)" \
  --tag v0.6.2-qwen38-3090-beta.1 --checksums "$ASSETS/SHA256SUMS" \
  --receipt "$ASSETS/package-build-receipt.json"
python3 scripts/rebind_release.py --release v0.9.1 --draft
```

`--add` creates the manifest, release compatibility and qualification-composition rows in
canonical order only after the existing verifier accepts the real qualification receipt.
Without it a missing row remains an error. The root authority and existing lanes are untouched.
Commit the bindings, then run `rebind_release.py --release v0.9.1 --pin <receipt-commit> --stage lane`.
At that cut update the existing routes' product pins to v0.9.1 and the current-release prose;
do not change their component pins. Freeze the candidate only after those edits are committed.

On the authorized RTX 3090 host, run the public-asset check with the candidate clone:

```powershell
.\scripts\hosts\accept-native-public-install.ps1 -Lane rtx3090 `
  -ManifestPath .\releases\v0.9.1\manifest.json `
  -ExpectedSums .\releases\v0.9.1\qualification\rtx3090-windows-native.SHA256SUMS `
  -StateRoot C:/ProgramData/NInfer/qwen38-3090-native `
  -Workspace C:/acceptance/rtx3090-public-install -ReceiptPath C:/acceptance/rtx3090-public-install.json
```

For documented acceptance, use a fresh same-volume remote workspace and the exact state hash and
temporary previous-release id from the stopped hardware qualification baseline. Run the same
driver arguments with `--mode dry-run`, then `preflight`, then once with `accept`:

```sh
python3 scripts/hosts/accept-rtx4090-route.py --lane rtx3090 --release v0.9.1 \
  --candidate "$CANDIDATE" --host "$RTX3090_HOST" --workspace "$LOCAL_WINDOW" \
  --remote-workspace C:/acceptance/rtx3090-route \
  --expected-state-sha256 "$STATE_SHA" --temporary-previous "$PREVIOUS_RELEASE" --mode dry-run
```

Run all five documented routes fresh; no predecessor-route acceptance is carried forward.
`compose_route_acceptance.py --release v0.9.1 --candidate "$CANDIDATE" --as-of "$AS_OF"`
also takes `--measurement-prefix "$PREFIX" --evidence "$EVIDENCE"` and five `--route LANE=PATH`
arguments: `rtx5090-container-host`, `rtx5090-macos-client`, `rtx5090-windows-client`,
`rtx4090-native` and `rtx3090-native`. Evidence needs separate `rtx4090` and `rtx3090`
preparation/observations/limitations, with real public-install and behavior/restoration results.
It writes both native public-install receipts and refuses missing lanes or an accepted route
also listed as deferred. Commit the acceptance, then perform the existing `--stage platform`,
`--stage acceptance` and `--stage manifest` pin dance, committing between stages and taking
each pin from the commit containing that stage's input evidence. Finish with:

```sh
python3 scripts/verify_release.py --release v0.9.1 --require-ready --check-pins
```

At cut time, move the applicable human-readable entries from `[Unreleased]` in
[`CHANGELOG.md`](../CHANGELOG.md) into the exact version heading, using the actual ISO 8601
release date, and add comparison/tag links as defined by
[Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/). Never date an unpublished version.

Release notes must lead with the exact support boundary and manual topology, then link the manifest,
qualification summary, quickstart, security model, and known limitations. Do not claim:

- “first stateful Responses” or “first persistent KV cache”;
- automatic container restart, multi-GPU, or multi-tenant support;
- structured JSON-schema output or unattended RTX 3090 role activation;
- support response-time guarantees or other SLAs;
- universal GPU performance; or
- benchmark values not present in the public qualification summary.

Use “OMP NInfer” for the product and repository.
