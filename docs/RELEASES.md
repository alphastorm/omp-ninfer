# Releases

OMP NInfer versions the integrated product. Component repositories keep their own versions and tags;
the product manifest binds the exact combination.

## Channels

| Channel | Meaning | Current state |
| --- | --- | --- |
| Public release | Published exact profiles with stated limitations and non-claims | `v0.8.1`, GitHub `Latest` |

Prereleases never take GitHub `Latest`; `Latest` always points at the current public release.
The historical fork client used separate `omp-beta` and stable `omp` Homebrew casks through
v0.7.4. v0.8.1 keeps the upstream OMP binaries adopted in v0.8.0 and uses no client cask.

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

### v0.8.1 public release — faster decode

- Status: published exact-profile product. [Manifest](../releases/v0.8.1/manifest.json) ·
  [guide](QUICKSTART.md) · [qualification](../releases/v0.8.1/qualification.json).
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
   receipt URLs, and reruns the chain. Flip the manifest to `ready`; commit.
4. `--pin <that commit> --stage acceptance`; commit. `--pin <that commit> --stage manifest`;
   commit. The manifest stage runs `verify_release.py --require-ready --check-pins`, which
   reads every pinned evidence URL out of local git history and requires it to serve exactly
   the recorded SHA-256; CI repeats it on the release tag with full history.

## Release notes

The OMP client is not built or published here. From v0.8.0 a release pins an unmodified upstream
Oh My Pi release binary per platform: `scripts/stage_release.py --omp-component` stages the
upstream provenance and the darwin-arm64, windows-x64 and linux-x64 binaries, whose raw hashes must
equal their asset hashes, and `scripts/verify_release.py` checks every binding. Client acceptance
is never inherited from a predecessor release.

RTX 4090 native runtime components use `scripts/hosts/cut-ninfer-4090-component.sh` after the
lane's canonical native qualification (`tools/qualification/qualify_native.py` in the runtime
fork). The default mode checks that the outer `SHA256SUMS` closes and verifies the asset
directory, that the package build receipt and the lane specification at the commit name the same
release and source, that the source archive's tar stream is byte-identical to `git archive` of
the commit, and that neither the tag nor the release exists. `--publish` is founder-only: it
pushes the component tag and creates one prerelease with the closed set; binding it into a
product release stays `scripts/bind_native_variant.py`.

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
