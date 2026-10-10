# Upstream watch

The runtime ships from forks; v0.10.0 uses an unmodified upstream OMP client. This page names
the upstreams we track, runtime fork points, and the current pull-in position. The watch manifest is
[`upstream-watch.json`](../upstream-watch.json); the watch tool is
[`scripts/upstream_watch.py`](../scripts/upstream_watch.py); dated reports land in
[`docs/measurements/`](measurements/).

## Running the watch

```bash
python3 scripts/upstream_watch.py --receipt docs/measurements/$(date +%F)-upstream-watch.json
# per-commit overlap scoring (one extra API call per upstream commit):
python3 scripts/upstream_watch.py --only ninfer-4090 --per-commit-files
```

Read-only: the tool only queries the GitHub API and writes the report file you name. Verdicts
are `up-to-date`, `upgrade-available`, or `error`; every upstream commit gets a class
(`fix`/`perf`/`feature`/`security`/`docs`/`test`/`chore`) and a recommendation
(`pull-candidate`, `next-release`, `review-now`, `ignore`). Recommendations are triage, not
decisions - a human owns every pull.

GitHub's compare endpoint lists at most 250 commits and 300 changed files and cuts a larger delta
without an error. The report records `commits_truncated` and `files_truncated`, and a cut file
list scores overlap as `unknown-truncated` rather than `no-direct-path-overlap` - before
2026-09-24 a cut list read as no overlap and marked every commit of a 1,387-file engine delta a
`pull-candidate`. For a delta that large, measure applicability against the fork itself (a
scratch cherry-pick or trial merge) instead of reading the overlap score.

## Current client candidate — OMP 18.8.7

| Upstream | Client pin | State | Why pull it in |
| --- | --- | --- | --- |
| `can1357/oh-my-pi` (client) | Unmodified upstream v18.8.7 (`f261ed9faf16b61880b544f599876bface4ded0d`), published upstream 2026-10-09T13:45:03Z | OMP NInfer candidate only; not yet published or GPU-host requalified | [#14334](https://github.com/can1357/oh-my-pi/pull/14334) releases completed one-shot routing state without clearing the main Responses chain; [#14952](https://github.com/can1357/oh-my-pi/pull/14952) adds optional per-model compaction thresholds. |

The previous unqualified 18.8.3 candidate first brought in #13686 (`429352901c`),
#13687 (`01822b63d0`) and #13689 (`8aaf115b8e`): per-model stateful Responses,
custom-host auto image detail and fail-closed unavailable-model resume. Those changes remain
in 18.8.7. Keep `compat.statefulResponses: true` in every NInfer model, remove
`PI_OPENAI_STATEFUL` from the launch environment, and do not restore the image-detail override.
The [schema](https://github.com/can1357/oh-my-pi/blob/f261ed9faf16b61880b544f599876bface4ded0d/packages/coding-agent/src/config/models-config-schema-bundle.ts#L74)
still admits the field. The [Responses handler](https://github.com/can1357/oh-my-pi/blob/f261ed9faf16b61880b544f599876bface4ded0d/packages/ai/src/providers/openai-responses.ts#L503-L514)
still gives a call option and then the environment precedence over per-model compat.

### 18.8.4–18.8.7 source review

The release notes were read for [18.8.4](https://github.com/can1357/oh-my-pi/releases/tag/v18.8.4),
[18.8.5](https://github.com/can1357/oh-my-pi/releases/tag/v18.8.5),
[18.8.6](https://github.com/can1357/oh-my-pi/releases/tag/v18.8.6) and
[18.8.7](https://github.com/can1357/oh-my-pi/releases/tag/v18.8.7).
Between the 18.8.3 and 18.8.7 tags, the custom-model schema, `openai-shared.ts`,
`ai/src/stream.ts` and `settings-stream-fn.ts` have identical Git blobs. The fragments'
`includeEncryptedReasoning: false`, `supportsReasoningSummary: false`, effort list,
`openai-responses` API and custom-host auto image-detail contract are unchanged.
The Windows rust-analyzer/lspmux fix in 18.8.5 and native-addon packaging change in 18.8.7
are not Responses protocol changes. The native Windows client passed the bounded
[local rehearsal](measurements/2026-10-10-omp-1887-windows-x64-local-rehearsal.json), not route qualification.

**#14334 and chaining.** [Provider state](https://github.com/can1357/oh-my-pi/blob/f261ed9faf16b61880b544f599876bface4ded0d/packages/ai/src/providers/openai-responses.ts#L429-L450)
now implements `releaseSession`: it normalizes the supplied routing-session id and deletes
only chain/effort entries for that id. Chain lookup is still keyed by base URL, model and
routing-session id, and unchanged append-prefix logic sends `previous_response_id` plus delta
input with `store: true`; changed history or a stale response id still causes full replay.
[AgentSession](https://github.com/can1357/oh-my-pi/blob/f261ed9faf16b61880b544f599876bface4ded0d/packages/coding-agent/src/session/agent-session.ts#L11009-L11086)
releases a one-shot side request in `finally` only when it has no `conversationKey`.
The main conversation and keyed side-conversation lineages are retained. **[inference]** This
cleanup preserves the fragments' stateful-chaining contract; source inspection alone is not
route acceptance or a long-session proof.

**Compaction finding.** The [async default](https://github.com/can1357/oh-my-pi/blob/f261ed9faf16b61880b544f599876bface4ded0d/packages/coding-agent/src/session/context-settings.ts#L207-L223)
is still `true`; [the background gates](https://github.com/can1357/oh-my-pi/blob/f261ed9faf16b61880b544f599876bface4ded0d/packages/coding-agent/src/session/session-maintenance.ts#L2077)
still stop when `asyncEnabled === false`. #14952 routes these checks through
[resolveModelCompactionSettings](https://github.com/can1357/oh-my-pi/blob/f261ed9faf16b61880b544f599876bface4ded0d/packages/coding-agent/src/session/model-compaction-threshold.ts#L20-L30).
The new map defaults empty and changes only threshold token/percentage fields when an entry
matches (exact `provider/model-id` first, then longest trailing-`*` prefix); no match returns
the existing settings object. It does not turn async compaction on or off.
The [provider in-flight gate](https://github.com/can1357/oh-my-pi/blob/f261ed9faf16b61880b544f599876bface4ded0d/packages/ai/src/stream.ts#L637-L654)
still waits before dispatch until a slot or caller cancellation, not the server's pending
admission deadline. Keep the settings in `examples/manual-tunnel/fail-closed.yml` unchanged: two requests for
RTX 5090 providers, one for native providers, no `asyncEnabled` override. This retains the
client-side waiting contract motivated by [EXP-072](measurements/2026-09-28-omp-long-sessions.json).
No `compaction.modelThresholds` setting is recommended or applied: 18.8.7 long-session or
threshold tuning was not measured, and #14952 alone supplies no evidence for a safer numeric
limit. The 18.8.6 pruning changes target Anthropic cache lookback, not a new NInfer threshold.

Fresh requalification remains pending for each documented route: RTX 5090 container host,
macOS client, Windows client, RTX 4090 native Windows and RTX 3090 native Windows. Local
client rehearsals do not inherit or replace v0.10.0's OMP 18.4.10 acceptance.
The [2026-10-10 source review and receipts](measurements/2026-10-10-omp-1887-client-release-review.json)
bind the observed image, three binary hashes and pass/fail checks. Shared proof environment
selection also retains the per-model contract after a profile is qualified, while the
historical 18.4.x driver behavior is unchanged.
See the [candidate guide](QUICKSTART.md#omp-1887-client-candidate).

## Published upstream position — v0.10.0

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

[Manifest](../releases/v0.10.0/manifest.json) · [Route acceptance](QUICKSTART.md#v0100-route-acceptance).
[Composed acceptance](../releases/v0.10.0/acceptance/composed-external-installation.json).

## Historical upstream position — v0.9.1

Install through the [quickstart](QUICKSTART.md); eligibility is one RTX 5090, RTX 4090
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

The [RTX 3090 lane qualification](../releases/v0.9.1/qualification/rtx3090.json) passed **all
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
   [the route configuration](../examples/manual-tunnel/fail-closed.yml). Merge that entry into
   `~/.omp/agent/config.yml` when following the RTX 3090 native quickstart. OMP leaves an
   unlisted provider unlimited; a request beyond the lane's one waits at the server and
   expires after 30 s.
3. **Acceptance judges scheduled tasks by definition and enabled state.** The first RTX 5090
   window passed every route, client probe and restoration check, but its summary refused a
   task snapshot: the five-minute container-host supervisor was `Running` at baseline and
   `Ready` afterwards, with an unchanged definition. Change `0073553` makes
   [the acceptance summary](../scripts/hosts/accept-rtx5090-routes.py) require byte-identical hold
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
[Documented routes](../releases/v0.9.1/acceptance/documented-routes.json) ·
[Composed acceptance](../releases/v0.9.1/acceptance/composed-external-installation.json).

Both native routes installed from public assets. The RTX 3090 route performed a fresh
canonical upgrade installation of the published package, then passed typed-tool,
continuation and fail-closed checks, with prior state restored; this is not an idempotent
reinstall claim ([public install](../releases/v0.9.1/acceptance/rtx3090-public-install.json)).
The RTX 3090 console was signed out: a managed start refuses while any process holds at
least 1 GiB of GPU memory, and the signed-in desktop's compositor alone held about 1,070 MiB.

The RTX 5090 routes ran in **two production windows** from the maintainer's Apple silicon
workstation over the tailnet. Downtime was at most **408.4 s (6.8 min)** and **386.5 s
(6.4 min)**. After the first window's task-snapshot summary refusal, a corrected window on
the same candidate passed in fresh workspaces
([restoration](measurements/2026-10-01-v091-acceptance-restoration.json)).

The historical v0.7.2 RTX 3090 route remains separate: its durable v0.2 lineage and OMP
18.0.9 fork client are not this lane, and its sessions do not carry over. The standalone
native lane is accepted; the **fleet RTX 3090 scout role stays deferred**, and the
**upstream engine merge remains open**.
[Release notes](../releases/v0.9.1/NINFER_RELEASE_NOTES.md) ·
[Manifest](../releases/v0.9.1/manifest.json) · [Qualification](../releases/v0.9.1/qualification.json).

**Upstream item: controller compatibility across rollback.** The `f08309da` fix belongs to
shared Windows lifecycle code, not an sm_86 kernel retune: a newer controller must launch
an older release using that release's declared configuration, without requiring fields
introduced later. The optional-field rule and its lifecycle regression coverage are the
reusable change. This release does not take the deferred upstream engine merge.

## Historical position — v0.9.0

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

RTX 3090 remains deferred. [Release notes](../releases/v0.9.0/NINFER_RELEASE_NOTES.md) ·
[Manifest](../releases/v0.9.0/manifest.json) · [Qualification](../releases/v0.9.0/qualification.json).

**Upstream item: resumed sessions' first request.** OMP 18.4.0 still omits earlier reasoning
on the first request from a resumed OMP process, so that request re-prefills from root even
when the server restored a current checkpoint. The next request carries reasoning again and
caches. The v0.8.7 measurement below remains the evidence; two requests in flight do not fix
client replay ([EXP-074](measurements/2026-09-29-long-session-cache.json)).

## Historical position — v0.8.7

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

**Upstream item: resumed sessions' first request.** OMP 18.4.0 replays native reasoning only once
a provider session is warmed (`nativeHistoryReplayWarmed` in
`packages/ai/src/providers/openai-responses.ts` starts false), so a new OMP process resuming a
session sends its first request without the reasoning of any earlier turn. The runtime preserves
thinking, so that request no longer matches the session it continues and prefills it from root:
56,174 tokens and 32.0 s to the first token in EXP-074, though the server had restored a current
checkpoint. The next request carries the reasoning again and caches. Treating a resumed session's
own reasoning as replayable on its first request would remove that prefill on either lane.

## Historical position — v0.8.6

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

The client, provider fragments, both runtimes, model, memory floors, serving configurations and
lane receipts are unchanged from v0.8.5. RTX 5090 keeps `v0.6.12-qwen38-5090-beta.1`, image
`cd9e10b1`; RTX 4090 keeps `v0.6.9-qwen38-4090-beta.1`, package `6492588e`. Checkpoints carry
across. To upgrade from v0.8.5, merge this into `~/.omp/agent/config.yml`:

```yaml
compaction:
  asyncEnabled: false
```

The OMP binary, `models.yml` and `PI_OPENAI_STATEFUL=1` do not change.
Documented resume/restart checks now plant with an OK-only reply and recall verbatim.
RTX 3090 remains deferred.

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

## Historical position — v0.8.5

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

[Release notes](../releases/v0.8.5/NINFER_RELEASE_NOTES.md) ·
[Qualification](../releases/v0.8.5/qualification.json).

## Historical position — v0.8.4

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

OMP 18.3.5 on Windows exits 1 after a complete `omp models` listing. That stopped the RTX 4090
route's first candidate, `0315c5d4`, at its no-effect preflight; that release's corrected check judged the
listing and candidate `68302298` passed. Upstream 18.4.0, released 2026-09-28, fixes
[can1357/oh-my-pi#13470](https://github.com/can1357/oh-my-pi/issues/13470). v0.8.4 pinned 18.3.5;
v0.8.5 repins to 18.4.0.

The upstream engine merge stays deferred: `e31bc99b` has about **18% slower decode** and
fanout **0/4 versus 4/4**
([EXP-065](measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json)). The
RTX 4090 Q5 tensor-core route was rejected by its pre-registered rule: **+0.38% at 26K** and
**+0.40% at 60K**, below required **2.0%/1.0%** gains
([EXP-069](measurements/2026-09-28-rtx4090-q5-small-t-mma.json)). RTX 3090's v0.6.2-beta.1
package built and tested at `5ac17674` remains unpublished, with hardware qualification pending
([preparedness](measurements/2026-09-28-rtx3090-v062-build-preparedness.json)).

[Release notes](../releases/v0.8.4/NINFER_RELEASE_NOTES.md) ·
[Qualification](../releases/v0.8.4/qualification.json).

## Historical position — v0.8.3

The unmodified upstream OMP 18.3.0 client and model artifact are unchanged from v0.8.2.
RTX 5090 advances to `v0.6.12-qwen38-5090-beta.1` (image `cd9e10b1`, server `3ab266e5`,
source `9d1ef748`). RTX 4090 remains `v0.6.8-qwen38-4090-beta.1` (package `46aa4110`,
server `32905865`, source `5a774841`), carrying its v0.8.1 lane receipt. RTX 3090 remains
deferred. Serving arguments, profile `qwen38-5090-v0.8.2`, configuration `56878aed`,
`--gpu-keep-warm-ms 60000`, 16384 MiB host KV and the 28672 MiB host floor are unchanged.

The runtime source is v0.8.2's `32c21f73` plus the EXP-057 route: the MTP3 verify pass's
four Q5 projections (GDN value/z, attention gate/value, mixer/attention output and MLP down)
use small-T tensor-core MMA at the four-token extent on `sm_120` instead of SIMT row kernels.
The route is compiled out for `sm_86` and `sm_89`. Release-build A/B/B/A measurements show
decode **+4.4% at 26K**, **+3.6% at 60K** and **+6.3% at 1,024 tokens**, with MTP3 rounds
**3.5-4.9% shorter**. With no prompt, decode was **0.5% slower**: the new build accepted
0.423 of drafts on its own text versus 0.461.
Route: [EXP-057](measurements/2026-09-26-q5-small-t-tensor-core.json); measurements:
[EXP-063](measurements/2026-09-27-powered-redaction-screen.json).

Accumulation order changes; **58 of 89** role-corpus cases answer differently from v0.8.2.
The pre-registered [EXP-063](measurements/2026-09-27-powered-redaction-screen.json)
redaction screen passed on **504 pairs** (7 controls with 72 whitespace variants).
Candidate leaks were **561 vs 582** for v0.8.2: ratio **0.964**, one-sided 95% upper bound
**1.012**, margin **1.10**. Pass rates were **53.2% vs 52.6%**: **+0.6 percentage points**,
lower bound **-1.2 points**, margin **-5 points**. All validity checks held. The earlier
EXP-057 56-sample point-estimate screen had rejected the route (**69 vs 61 leaks**);
EXP-063 re-tested the redaction regression with power. Other primary role-corpus measures
were within 2.0 points of v0.8.2 in one run per build. The published image matched the
screened candidate byte-for-byte on **89/89** cases.

Gates were re-measured on the published RTX 5090 image: 130,048-token exact retrieval in
**58.7 s**, decode at **168.07 tok/s**, and the agent protocol across a restart. Four sessions
restored after restart; publication-barrier, fanout, warm-arrival, restore and multisession
probes passed. Root fallback remained 2 of 8 continuations/forks. None of 24 fresh sessions
fell back to a full prefill; median TTFT was **0.093-0.100 s**. Stock OMP 18.3.0 kept one
session across graceful restarts; the first request restored from checkpoint.
[Lane receipt](../releases/v0.8.3/qualification/rtx5090.json) ·
[Qualification](../releases/v0.8.3/qualification.json).

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

The preceding v0.8.3 measurements are historical; the tracked-upstream table below records the
current EXP-065 engine decision and the v0.8.6 client pin.

## Historical position — v0.8.2

The unmodified upstream OMP 18.3.0 client and model artifact are unchanged from v0.8.1.
RTX 5090 advances to `v0.6.11-qwen38-5090-beta.1` (image `26813f56`, server `0d7e042b`,
source `32c21f73`). RTX 4090 remains `v0.6.8-qwen38-4090-beta.1` (package `46aa4110`,
server `32905865`, source `5a774841`), carrying its v0.8.1 lane receipt: 15 canonical
native phases and 130,048-token retrieval in **91.0 s**. RTX 3090 remains deferred.

The runtime adds `ninfer-serve --gpu-keep-warm-ms N`, off by default. After work and while
idle, a single-warp kernel touches no memory and spins 3.5 ms of every 10 ms on its own stream
for N ms, skips a launch while the previous spin runs, and stops when a request is pending.
RTX 5090 profile `qwen38-5090-v0.8.2` adds `--gpu-keep-warm-ms 60000`; host KV stays
16384 MiB and the host floor stays 28672 MiB. After 12-58 s idle, new sessions prefilled in
**0.155-0.157 s** (TTFT **0.173-0.181 s**), versus **0.253-0.304 s** (TTFT **0.316-0.366 s**)
without keep-warm. The 89-case role corpus was byte-identical to v0.8.1 on and off. Holding
clocks costs about **71 W**; a 60 s grace replayed over 62 h of logged v0.7.0 traffic would
cost about **2.3 W average**. [EXP-062](measurements/2026-09-26-engine-keep-warm.json).

The published RTX 5090 image recorded 130,048-token exact retrieval in **56.4 s**, decode at
**160.07 tok/s**, four sessions restored after restart, and passed publication-barrier,
fanout, warm-arrival, restore and multisession probes. None of 24 fresh sessions fell back to
a full prefill; median TTFT was **0.090-0.098 s**. Stock OMP 18.3.0 kept one session across
restarts on the RTX 5090. [Lane receipt](../releases/v0.8.2/qualification/rtx5090.json).

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

The upstream delta measurements below remain historical; keep-warm is not an upstream rebase.

## Historical position — v0.8.1

Runtime positions below retain the [2026-09-24 report](measurements/2026-09-24-upstream-watch.json);
they are not new upstream delta measurements. The upstream NInfer rebase remains future work.
The client remains the unmodified upstream OMP 18.3.0 release binary with the same SHA-256
pins as v0.8.0. All three client binaries passed live inference on the published RTX 5090
image (Linux under Ubuntu/WSL2), and the four documented routes passed all 24 steps on the
published v0.8.1 components, with both hosts restored.

The runtime change is decode kernels, not the upstream rebase: small-extent Q4/Q5 projections
share activation loads across weight rows, and Q4 gate/up staging avoids shared-memory bank
conflicts. RTX 5090 `v0.6.10-qwen38-5090-beta.1` (image `5ca6e416`, server `5b2f2471`,
source `8cc0810a`) decodes 10.3-11.0% faster with identical outputs. RTX 4090
`v0.6.8-qwen38-4090-beta.1` (package `46aa4110`, server `32905865`, source `5a774841`)
keeps one-row split2 kernels on native lanes; C1 decode is 157.89 vs 153.54 tok/s. Every
runtime gate was re-measured on published bytes, matching v0.8.0's behavior; client, model,
serving settings and floors are unchanged.
[EXP-055](measurements/2026-09-25-decode-kernel-schedules.json) ·
[EXP-054](measurements/2026-09-25-decode-roofline-attribution.json) ·
[Release notes](../releases/v0.8.1/NINFER_RELEASE_NOTES.md) ·
[Documented routes](../releases/v0.8.1/acceptance/documented-routes.json).

## Tracked upstream delta — 2026-09-28

| Upstream | Fork point | Delta | Position |
|---|---|---|---|
| `Neroued/ninfer` (engine; both mainline lanes build from one fork source) | `6e8b2e2a` (mainline base) | `d44ab584`, measured 2026-09-30 | **DFlash2 is worth taking, by port.** On `d44ab584` and the published v3 artifact, DFlash2 K=7 decoded the role corpus 28.2% faster than MTP3 on the same binary and 6.9% faster than the shipped runtime, at one request; it needs 1.65 GiB more weights and two fewer device state slots at two requests ([EXP-078](measurements/2026-09-30-dflash2-rtx5090.json)). Ported onto the fork's runtime (52 of upstream's 79 DFlash2-program commits, including `4b0eb36c`'s verify attention route for 24 query heads), it decodes the corpus 21.4% faster than shipped and 13.6% faster than upstream's DFlash2 at one request, with MTP3 byte-identical ([EXP-081](measurements/2026-09-30-dflash2-verify-route-rtx5090.json)); without that route its round grew with context ([EXP-079](measurements/2026-09-30-dflash2-fork-spike-rtx5090.json)). Two requests' rounds reached upstream's through the fork's own Q5 tensor-core route extended to 16 columns, not upstream's 16-column routes: a pair decodes 8.4% faster than shipped's ([EXP-082](measurements/2026-10-01-dflash2-pair-q5-tensor-cores-rtx5090.json)). Upstream has no durable session store; the fork carries DFlash2's draft context ring through its own checkpoints, with exact restores ([EXP-083](measurements/2026-10-01-dflash2-durable-store-rtx5090.json)). Upstream's NVFP4 KV, ported as final files from `d44ab584` behind the fork's storage identity, gives the two-request DFlash2 profile four device state slots and 262,144 KV tokens with rounds 12-27% shorter behind 32K-120K tokens ([EXP-084](measurements/2026-10-01-dflash2-nvfp4-kv-rtx5090.json)), but it failed the fork's powered quality screen against shipped MTP3 on unsupported claims and secret leaks, where DFlash2 with BF16 KV passed with 1,091 of 1,120 outputs byte-identical to shipped ([EXP-085](measurements/2026-10-01-dflash2-powered-quality-screen-rtx5090.json)). Upstream's MTP3 decode rounds are still 16-18% slower than the shipped runtime's and its fanout reuse is 0/4 against 4/4, so a merge alone is not the win ([EXP-065](measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json), [prior EXP-048](measurements/2026-09-24-engine-window-upstream-vs-shipped.json)). |
| `UDPSendToFailed/ninfer-4090` (4090 port) | `11aae2d6` | 57 commits at `5c60b7c9` (unchanged since 2026-09-09) | 9 of 51 candidates apply cleanly, all kernel retunes (EXP-045). The fixes this lane wants - chunked KV snapshot staging, the MTP restore stride, publishing finished snapshot saves, WDDM residency budgeting, the D3D12 residency fence, the admission shortfall and `/health` - conflict in files the fork changed and are read against v0.7.1's durability work when taken. Upstream removed its NVFP4 path (`dabae909`). |
| `Don-Chad/ninfer-3090` (3090 port) | `ef6ecc3c` | 141 commits at `75d94eab` (unchanged since 2026-08-31) | At this report, triage awaited the RTX 3090 host. v0.9.1 accepts the standalone native lane from mainline source `f08309da`; it does not update this historical upstream delta or take the deferred engine merge. |
| `can1357/oh-my-pi` (client) | Upstream v18.4.0 (`401778d0cd30020ce0f9198f751b13c68850562f`) | Unmodified upstream release binary; published 2026-09-28T03:33:34Z | v0.8.6 pins 18.4.0; all four documented routes passed. Fix `9d3e0d4975` resolves the Windows completion-status defect ([#13470](https://github.com/can1357/oh-my-pi/issues/13470), [EXP-070](measurements/2026-09-28-omp-1840-windows-completion-status.json)). RTX 5090 fragments now set `compat.supportsImageDetailOriginal: false` for automatic compaction ([EXP-071](measurements/2026-09-28-omp-snapcompact-image-detail.json)). The route config now sets `compaction.asyncEnabled: false`: three RTX 4090 handoffs took 77.0-83.7 s each with no expired admission; RTX 5090 snapcompact took 0.07-0.08 s ([EXP-072](measurements/2026-09-28-omp-long-sessions.json)); provider fields and `PI_OPENAI_STATEFUL=1` are unchanged; no fork build, archive, installer or cask. |

**Historical client position through v0.7.4.** `omp-18.2.3-cross-platform-beta-1` (source
`5ade242d`, since v0.7.3) carried 36 downstream commits on upstream `a2d83061` (v18.2.3),
including the NInfer provider and appliance lifecycle. The 2026-09-24 watch counted 681 upstream
commits to `62bc57be` (v18.3.0). At that time, the client plan was a rebase plus documented-route
acceptance rather than direct adoption
([EXP-046](measurements/2026-09-17-client-repin-evaluation.json)); v0.8.0 instead uses the stock
binary with the stock-client runtime.

### v0.6.9: parser semantics without the serve-adapter rebase

The [2026-09-12 backport ledger](measurements/2026-09-12-upstream-backport-ledger.json) and the
2026-09-13 delta counts it was read against are historical evidence for this release. The ledger
deferred `3b50962b` and `0c5d570c` because their extracted parser files do not exist on this
tree. The v0.6.9 release instead implements their semantics independently in the downstream
parser: supported scalar unions, case-insensitive
booleans, precise numeric lexemes, mathematically integral values, duplicate parameters, and
balanced embedded markup. It does not import the wholesale serve-adapter rebase or change the
fork point; custom raw input, history, opaque IDs, and stream ownership are preserved.

Reviewed source `696e78c7b4e3ac28ffcffafc73acc1496e65ef03` includes remediation against
malformed-region rescans and recursive union traversal; bytewise regressions and an 8,192-deep
union case pass. It builds the published RTX 5090 `v0.6.5-qwen38-5090-beta.1` and native
RTX 4090 `v0.6.3-qwen38-4090-beta.1` components. Both lanes are qualified and RTX 4090
public-URL already-installed acceptance passed; the RTX 5090 documented host 2/2 and macOS
10/10 routes passed against the published image.
[Release notes](../releases/v0.6.9/NINFER_RELEASE_NOTES.md).
The old backport ledger is intentionally unchanged: its deferred parser entry describes that
earlier campaign, not the candidate's current parser coverage. The deferred pressure-planner
family is separate; the alternating-session finding is already attributed to host KV capacity
([EXP-039](measurements/2026-09-13-hostkv-capacity-multisession.json)), not proof that this
product needs that planner rebase.

## Why the fork points are what they are

- The 5090 lane builds from the mainline runtime whose upstream base is `6e8b2e2a` (since v0.6.2);
  later upstream movement is tracked separately from the reviewed backports and semantic ports
  named above. The retired container mirror point `4eef14a7`
  was the lineage's base before v0.6.2 and made the delta read 17 commits larger than it is.
- The 4090/3090 native Windows lanes originally vendored their upstreams at the recorded
  commits. Both now ship from the mainline runtime: v0.9.1 retains RTX 4090 source
  `cba7eb93`; RTX 5090 source `e20060b6` is its child, and the RTX 3090 v0.6.2 component
  builds that source plus the controller rollback fix at `f08309da` for sm_86. The
  durable-checkpoint, security and packaging work remains downstream.
- Through v0.7.4, the client fork point was the upstream tag commit onto which downstream
  patches rebased. v0.9.1 does not build or publish an OMP client; it uses the upstream
  release binary instead.
