# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Harden every active documented and structured acceptance check to nonce
  `493817-205361`, with the probe plant interpolating its checked constant and
  a red-before/green-after invariant across all three drivers, route plants and
  greps. Keep OK-only planting, verbatim recall and exact answers unchanged. The
  pre-registered diagnostic found no material A/B difference: each old-nonce
  cohort and the hardened cohort passed50/50. Preserve the first failed window.
  The founder requires a new candidate: the RTX3090 pass on65b6c426 is evidence
  only, not composable; that lane cannot ship until hardware is reinstalled and
  re-accepted. RTX5090 and replacement-host RTX4090 acceptance remain pending
  ([diagnostic](docs/measurements/2026-10-10-omp-acceptance-nonce-diagnostic.json)).
- Select founder-approved `1302d639` for the v0.11.0 / RTX 5090 v0.6.16 candidate:
  EXP-092/094 without `3a2fadbd`, with full sm_120a ctest 111 pass/7 skip/0 fail and
  all 15 local lane criteria passing. Preserve superseded `a59c13d0` and its red
  NVFP4 evidence. Record the lead-reported source publication and passing cutter
  dry-run, subsequent founder component publication and exact anonymous binary pull.
  Stage image6a02feba and cut the candidate lane; route acceptance/product publication
  remain pending. Retain native RTX 4090 for OMP 18.8.7 requalification on the replacement
  host; RTX 3090 still needs fresh acceptance and continued GPU-presence confirmation.
  Root authority/profile/launcher pins advance to v0.11.0; production is not promoted.
- Consume a root client-candidate marker only when lane promotion replaces its client
  wholesale from an upstream-release compatibility copy. Non-promoted and legacy-fork
  markers still refuse installation; the manifest stays candidate with external acceptance
  pending. The v0.11.0 CLI regression was red before and green after the narrow fix.
- Enumerate exactly runtime v0.6.16 in the release verifier, without accepting arbitrary
  future tags. Root promotion and verification bind upstream clients to their platform's
  compatibility distribution, not the manifest's primary Windows asset; legacy fork
  archive pins remain unchanged. Staging's draft-residue consumer uses the same
  platform-specific diagnostics. Focused regressions cover the allowlist and cut-blocking
  Mac/Windows archive bindings.

- Target unmodified upstream OMP **18.8.7** in current install instructions and root profiles,
  pinned to source `f261ed9faf16b61880b544f599876bface4ded0d` and the upstream binary checksums.
  This is an **unreleased v0.11.0 product candidate**, bound to published components;
  fresh acceptance of all five documented routes remains pending.
  Published release records and historical measurements are unchanged.
  Content-safe 2026-10-10 local rehearsal receipts record passing typed-tool, exact-continuation
  and fail-closed checks on macOS arm64, native Windows x64 and WSL2 Linux x64 against the
  published v0.10.0 image; these do not qualify any route.
- Retarget the previous unreleased 18.8.3 candidate from #76; 18.8.4–18.8.7 release/source
  review keeps the request compat and async-compaction/provider-limit contract unchanged.
  #14334 releases one-shot side-session state without clearing the main Responses chain;
  #14952's optional per-model thresholds are not enabled without long-session evidence.
- Client probes use the verified component descriptor for local rehearsals. Per-model clients
  omit the global stateful override in both rehearsal and future acceptance paths; the
  published v0.10.0 / 18.4.10 probe contract is retained. A shared version-aware helper also
  governs stock restart, parallel and long-session proof launches and their environment
  receipts; the per-model contract survives profile qualification instead of reverting to =1.
  Parallel proof identity comes from a descriptor platform row or explicit version/SHA-256
  arguments, not a hardcoded historical binary; mismatches stop before the workload.
  Non-candidate profile stateful contracts derive from the manifest's OMP version, not an
  optional profile tag. Resumed host-probe phases retain preflight's expected client version
  and projected environment and refuse changes before launching or rewriting evidence.
- Set `compat.statefulResponses: true` on every NInfer model instead of requiring process-wide
  `PI_OPENAI_STATEFUL=1` ([upstream #13686](https://github.com/can1357/oh-my-pi/pull/13686)).
  Remove the RTX 5090 `compat.supportsImageDetailOriginal: false` override because unknown/custom
  Responses hosts now default to auto image detail
  ([upstream #13687](https://github.com/can1357/oh-my-pi/pull/13687)). Compaction settings are unchanged.
- Include upstream's fail-closed resume behavior when a saved model is unavailable
  ([#13689](https://github.com/can1357/oh-my-pi/pull/13689)); no additional configuration is needed.
- Validate candidate profile identities locally without attributing v0.10.0's qualification to
  the new client. Unbound root candidates still refuse installation; lane-bound product
  candidates pass installability but not readiness before fresh acceptance.
  Staging's predecessor-pin check distinguishes those pins from a current-profile candidate warning.
- Retire current-client references to the historical fork, Homebrew client casks and
  `omp appliance` lifecycle. Troubleshooting uses the current model id and upstream per-model
  `compat.statefulResponses`, not the fork-only `ninferStatefulResponses` key.

## [0.10.0] - 2026-10-02

### Changed

- RTX 5090 advances to runtime `v0.6.15-qwen38-5090-beta.1` (source `eaf221ac`, image
  `fff4ee38`, server `7a8908e8`), DFlash2 K=7 with BF16 KV, and model `0634abb0`.
  Profile `qwen38-5090-v0.10.0` / configuration `8b2f4959` has 131,520 KV tokens,
  two device state slots and two requests in flight. The fourth candidate passed all fifteen
  window criteria after the founder-approved criterion-14 proof amendment (#74) and rerun;
  the two failed original limit-2 runs remain preserved. Both sessions restored 62,404 cached
  tokens in each of three restart repeats. Predecessor checkpoint reuse is not claimed.
- All clients move to unmodified upstream OMP **18.4.10**, not the downstream OMP archive.
  RTX 3090 and RTX 4090 retain their runtime packages and predecessor model. All five documented
  routes passed **31 steps** on candidate `ca929822`, and the macOS arm64 (preview), Windows
  x64 and Linux x64 binaries each passed a typed tool turn, exact continuation and fail-closed
  request against the published RTX 5090 image. Linux ran under WSL2, not a separately qualified
  Linux OS. Both native lanes installed from public assets; all hosts were restored
  ([routes](releases/v0.10.0/acceptance/documented-routes.json),
  [composed acceptance](releases/v0.10.0/acceptance/composed-external-installation.json)).
  The RTX 5090 window passed on its first attempt (c2), with downtime at most **387.499 s**.
  RTX 4090 passed at c4 after staged-model timestamp and interactive-GPU-owner refusals;
  RTX 3090 passed at c5 after NVIDIA Overlay refusals. The earlier `20a75bd5` native-model
  failure and these refusals preceded any install effect; every attempt restored its host
  ([restoration](docs/measurements/2026-10-02-v0100-acceptance-restoration.json)).
  These are maintainer-operated observations, not independent external-user outcomes.
  [Release notes](releases/v0.10.0/NINFER_RELEASE_NOTES.md).

### Added

- EXP-083 receipt: on the fork's DFlash2 spike, sessions keep the durable store. The draft
  context ring already rode every StateImage; runtime `03212c9d` stops requiring a backend-KV
  file DFlash2 does not have and refuses an export whose ring lags its frontier. A session
  restored into a fresh engine decoded its next turn exactly as the exporting engine did, and a
  57,889-token session restored hot across two container restarts with MTP3 byte-identical. On
  the same probe sequence shipped v0.9.0 lost the same multi-session reuse; DFlash2's two-slot
  profile re-prefilled one short sibling under device-state pressure
  ([EXP-083](docs/measurements/2026-10-01-dflash2-durable-store-rtx5090.json)).
- EXP-084 receipt: upstream's NVFP4 paged KV, ported onto the fork's DFlash2 spike (`008a7781`)
  with every BF16, INT8 and FP8 path unchanged, gives the two-request DFlash2 profile four device
  state slots and 262,144 KV tokens (BF16: two and 131,520; v0.9.0: four and 160,256). Rounds
  match BF16 at short context and in the pair and are 12-27% shorter behind 32K-120K tokens.
  The durable sequence keeps hot restores from 1.66 GB checkpoints and shipped's reuse, and MTP3
  stays byte-identical. One unpowered role-corpus run decoded 24.0% faster than MTP3 with
  evidence precision 0.951 against 0.994, which a powered quality screen now tests
  ([EXP-084](docs/measurements/2026-10-01-dflash2-nvfp4-kv-rtx5090.json)).
- `scripts/quality_screen.py`: a paired role-corpus quality screen for runtime candidates that
  change output bits. It extends EXP-063's redaction screen to every primary metric of the
  automatic-use gate: every counted case runs in eight whitespace variants of its task, and every
  redaction control in EXP-063's 72, on fresh production and candidate servers. The arms pair
  prompt by prompt, and the tool decides by one-sided 95% bounds of a paired bootstrap against
  margins fixed before any candidate data (EXP-085).
- EXP-085 receipt: the powered quality screen against shipped v0.9.0 MTP3 passes DFlash2 K=7 with
  BF16 KV, whose outputs were 1,091 of 1,120 byte-identical to shipped's. It fails NVFP4 KV:
  evidence precision held (-0.3 points, lower bound -1.2), but unsupported claims rose 1.8
  points (upper bound 3.7 against 3.0) and secret leaks went from 561 to 609 (ratio upper bound
  1.141 against 1.10)
  ([EXP-085](docs/measurements/2026-10-01-dflash2-powered-quality-screen-rtx5090.json)).
- EXP-087 receipt: the fork's existing FP8 KV gives the two-request DFlash2 profile four device
  state slots and 249,216 KV tokens, with long-context rounds 7-18% shorter than BF16's and
  exact 130,048-token retrieval, so it earns the powered screen
  ([EXP-087](docs/measurements/2026-10-01-dflash2-fp8-kv-precheck-rtx5090.json)).
- EXP-088 receipt: under EXP-085's unchanged rule, DFlash2 with FP8 KV held every gate metric
  inside its margin except secret leaks, 604 against shipped's 561 (ratio upper bound 1.135
  against 1.10), so FP8 KV fails as NVFP4 did and BF16 DFlash2 remains the quality-cleared
  profile ([EXP-088](docs/measurements/2026-10-01-dflash2-fp8-kv-quality-screen-rtx5090.json)).
- EXP-086 receipt: the adopted DFlash2 BF16 two-request profile passed every probe v0.9.0 qualified
  its RTX 5090 profile with, but decodes free-form reasoning 2-5% slower than MTP3 at one request
  and 21-27% slower at two, and one of two sessions resumed from root after a restart
  ([EXP-086](docs/measurements/2026-10-01-dflash2-pre-acceptance-probes-rtx5090.json)).
- EXP-089 receipt: the DFlash2 port does not link for the RTX 4090 (sm_89) or RTX 3090 (sm_86):
  three W8 kernels exceed the 48 KiB static shared-memory limit. The 24 GB lanes would not fit it
  at 131,072 tokens either, so both stay on MTP3
  ([EXP-089](docs/measurements/2026-10-01-dflash2-native-lanes-feasibility.json)).
- EXP-090 receipt: under stock OMP's sampling, one role-corpus run per arm found no gross quality
  change from MTP3 to DFlash2 K=7 on the same binary (recall -0.3 points, interval -3.6 to +3.2),
  and stock OMP's two-subagent proof failed 2 of 10 runs on DFlash2 against 3 of 10 on MTP3.
  Three of those failures were the proof's code reader, now fixed
  ([EXP-090](docs/measurements/2026-10-01-dflash2-sampled-behavior-rtx5090.json)).
- Release manifests can bind the native Windows lanes to their own model artifact. An optional
  `components.native_model` names the native lanes' model while `components.model` names the
  RTX 5090's; without it both read `components.model`, as before. `verify_release.py`,
  `rebind_release.py`, `bind_native_variant.py`, `compose_route_acceptance.py` and the native
  route acceptance scripts check the native lanes against it, and the compatibility page lists
  each native lane's model. `stage_release.py` changes the RTX 5090's model with
  `--model-revision`, `--model-sha256` and `--model-bytes` and keeps the native lanes on their
  predecessor's model in `components.native_model`, so a release can ship DFlash2's artifact on
  the RTX 5090 while the native lanes keep MTP3's.

### Fixed

- `scripts/omp_parallel_proof.py` failed subagent runs whose scout returned the exact code line:
  a structured result arrives as JSON text, and the escaped newline before a code read as a word
  character, so the code went unseen. Codes are now read from each decoded string value. Three of
  EXP-090's twenty runs, on both arms, had failed this way. The receipt also records each
  subagent's outcome, task calls that returned no subagent results, and client-cancelled
  requests with the overlap measured without them.

## [0.9.1] - 2026-10-01

### Fixed

- A rollback can launch a release older than the controller. The shared Windows controller read
  `context_cache.host_kv_mib` directly under PowerShell strict mode, and the RTX 3090's v0.6.0
  configuration predates that field, so the lane's first qualification window, at `e20060b6`,
  failed its rollback phase: the managed wrapper exited before it launched the predecessor.
  Runtime `f08309da` passes `--host-kv-mib` only when a release's own configuration declares it,
  as it already did for `gpu_keep_warm_ms`, and the runtime's lifecycle tests require every
  configuration field newer than the shipped lineage to be read that way. Every published RTX
  4090 package declares the field, so the RTX 4090 lane was not exposed.
- OMP sends the RTX 3090 one request at a time. `examples/manual-tunnel/fail-closed.yml` lists
  `ninfer-native-3090: 1` under `providers.maxInFlightRequests`; OMP leaves an unlisted provider
  unlimited, and a request beyond the lane's one waits at the server, which expires it after
  30 s. The test that binds each provider's limit to its lane's concurrency now reads every
  `*/models*.fragment.yml`.
- The RTX 5090 acceptance window judges the Windows host's OMP scheduled tasks by definition and
  enabled state. v0.9.1's first window passed every route, client probe and restoration check,
  then its summary refused the task snapshot: the baseline caught the five-minute container-host
  supervisor mid-run (`Running`) and the final snapshot idle (`Ready`), with an unchanged
  definition. `scripts/hosts/accept-rtx5090-routes.py` now requires the hold markers
  byte-identical and each OMP task present, identically defined and as enabled as before; a test
  passes a mid-run supervisor and refuses a disabled, redefined or removed task.

### Added

- RTX 3090 native Windows lane `v0.6.2-qwen38-3090-beta.1` (package `da1d62f2`, 595,676,373
  bytes; server `11b3f93c`; source `f08309da`: the RTX 5090 v0.6.14 source `e20060b6` plus the
  controller fix above, built for sm_86) with deployment profile
  `qwen38-3090-native-v0.6.2-beta.1` / configuration `0f700667`: one request at a time with a
  30 s pending timeout, 131,072 tokens of INT8 KV with MTP3, an 8192 MiB host-KV pool, 24
  host-state slots and keep-warm off, held at 300 W while it serves. It has the RTX 4090's
  lifecycle: a managed scheduled task, a protected state root, a graceful stop that saves live
  sessions, durable checkpoints and rollback. On the physical RTX 3090 it passed all 15
  lifecycle phases: 130,048-token retrieval exactly in 221.0 s, restart with a managed-stop flush
  of an unpublished session, rollback in both directions against the lane's unpublished
  v0.6.0-beta.1 package, protected state, the 15-check agent protocol, the unmodified upstream
  OMP 18.4.0 client's typed tool call, and the C1 benchmark at 102.64 tok/s with 93.43% MTP
  acceptance ([lane receipt](releases/v0.9.1/qualification/rtx3090.json)). The quickstart's RTX
  3090 route uses the published assets and stock OMP 18.4.0; the v0.7.2 RTX 3090 route remains
  separate history.
- RTX 3090 release tooling: closed component admission for the v0.6.2 tag family, explicit
  receipt-verified native-row insertion (`scripts/bind_native_variant.py --add`), one
  lane-parameterized component cutter and route harness whose RTX 4090 entrypoints and defaults
  are unchanged, and five-route acceptance with separate native public-install receipts.
- Fresh acceptance on candidate `c55185dd` with unmodified OMP 18.4.0 and the published
  components: all five documented routes passed **31 steps** (RTX 5090 container host 2, macOS
  client 10, Windows client 5, RTX 4090 native Windows 7 and RTX 3090 native Windows 7); all
  three hosts were restored, and both native lanes installed from their public assets
  ([routes](releases/v0.9.1/acceptance/documented-routes.json),
  [composed acceptance](releases/v0.9.1/acceptance/composed-external-installation.json)). The
  upstream macOS arm64 (preview), Windows x64 and Linux x64 binaries each passed a typed tool
  turn, an exact continuation and a fail-closed request against image `4c816b0c`; Linux ran
  under WSL2, not a separately qualified Linux OS. The RTX 5090 routes ran from the maintainer's
  Apple silicon workstation over the tailnet, in two production windows with downtime at most
  **408.4 s (6.8 min)** and **386.5 s (6.4 min)**
  ([restoration](docs/measurements/2026-10-01-v091-acceptance-restoration.json)). The first
  window's summary refused its task snapshot, fixed above; the corrected window ran on the same
  candidate.
- `scripts/speculative_decode_probe.py` measures decode rate and draft acceptance for one code
  answer behind 0 to about 120K tokens of context, a continuation that reuses its prefix, and an
  optional pair of requests decoding together. It sends plain Chat Completions, which the shipped
  runtime and upstream NInfer both accept, and reads timings from the server's request log.
  EXP-078 used it with the role corpus: on upstream `d44ab584`, DFlash2 K=7 decoded the corpus
  28.2% faster than MTP3 at one request, for 1.65 GiB more weights
  ([EXP-078](docs/measurements/2026-09-30-dflash2-rtx5090.json)). On a first port of DFlash2 onto
  the fork's runtime it showed the port's decode round growing with context: 355.15 tok/s with no
  context, 44.54 behind 120K tokens against shipped 180.11
  ([EXP-079](docs/measurements/2026-09-30-dflash2-fork-spike-rtx5090.json)). Under DFlash2 it
  measured NVFP4 and K8V4 KV against BF16: both start two requests with four device state slots
  and 262,144 KV tokens, with role-corpus decode within 1.1% of BF16
  ([EXP-080](docs/measurements/2026-09-30-kv-nvfp4-k8v4-rtx5090.json)). With upstream's attention
  route for the port's 8-token verify on the 27B's 24 query heads, it measured 222.95 tok/s behind
  120K tokens, and the port decoded the corpus 21.4% faster than shipped with MTP3 byte-identical
  ([EXP-081](docs/measurements/2026-09-30-dflash2-verify-route-rtx5090.json)). With two requests'
  16-column verify on the fork's Q5 tensor-core route, its pair step measured 420.86 tok/s
  together against shipped 388.42, MTP3 still byte-identical
  ([EXP-082](docs/measurements/2026-10-01-dflash2-pair-q5-tensor-cores-rtx5090.json)).

## [0.9.0] - 2026-09-30

### Fixed

- The RTX 5090 launcher checks its server against the concurrency its profile declares.
  `examples/manual-tunnel/start-ninfer.sh` still required the served scheduler to report one
  request in flight after the profile moved to two, so v0.9.0's first RTX 5090 route window
  refused its own server at the container-host route's start step
  (`max_concurrency: expected 1, got 2`). The launcher now takes the expected concurrency,
  context and KV type from the profile it launches, and a test serves it both the declared value
  and another one.
- The RTX 5090 acceptance window releases its Windows hold through a live WSL interop relay. A
  distro started by a boot-time scheduled task keeps a root relay that cannot start Windows
  processes ([microsoft/WSL#8643](https://github.com/microsoft/WSL/issues/8643)), and the
  window's WSL-side restore runs outside every `wsl.exe` session. In the first window it
  restored production and then failed to release the hold, which stayed up 10 min longer.
  `scripts/hosts/accept-rtx5090-host.py` now uses the first relay that starts a Windows process.
- Acceptance tooling never lends a client the operator's terminal. OMP 18.4.0's print mode reads
  piped stdin to EOF before its first request (startup phase `readPipedInput`). The second RTX
  5090 window ran its drivers from a terminal that never closes, and `ssh` forwarded that stdin
  to the Linux client probe: the client sent no request in 210 s. The client probe
  (`scripts/hosts/omp-client-probe.py`), the documented-route runner's blocks and every child
  of the route drivers now read `/dev/null`, and two tests run the probe and the runner with a
  stdin that never ends.

### Added

- `scripts/concurrency_probe.py` measures one RTX 5090 engine-window arm with one or two
  requests in flight: solo and paired decode, a long prefill beside a decode, two stored sessions,
  sibling fanout, near-capacity admission, and a graceful restart while two stored sessions
  decode. Its receipt records each request's time to first output, output-event gaps, VRAM, and
  the prefix-reuse path the server logged, without prompt, output or credential text.
- `scripts/omp_parallel_proof.py` runs stock OMP 18.4.0 against one lane with one and then two
  requests in flight: a parent turn that fans out two scout subagents, and two OMP sessions
  started together. It records the requests' overlap from the server's request log and each
  scenario's wall time against the one-in-flight baseline.
- Two invariants in `tests/test_manual_tunnel_scripts.py` keep each provider's limit equal to
  its lane's concurrency and require a two-request lane's pending timeout to exceed 30 s while
  leaving 60 s under OMP's 300 s stream-idle watchdog.
- Fresh acceptance on candidate `0d2a7468` with unmodified OMP 18.4.0 and the published
  components: all four documented routes passed **24 steps** (RTX 5090 container host 2,
  macOS client 10, Windows client 5 and RTX 4090
  native Windows 7); both hosts were restored
  ([routes](releases/v0.9.0/acceptance/documented-routes.json),
  [composed acceptance](releases/v0.9.0/acceptance/composed-external-installation.json)).
  The upstream macOS arm64 (preview), Windows x64 and Linux x64 binaries each passed a typed
  tool turn, an exact continuation and a fail-closed request against image `4c816b0c`;
  Linux ran under WSL2, not a separately qualified Linux OS. The RTX 5090 routes ran from the
  maintainer's Apple silicon workstation over the tailnet, in three production windows with
  downtime at most **101.5 s**, **324.3 s** and **499.3 s (8.3 min)**
  ([restoration](docs/measurements/2026-09-30-v090-acceptance-restoration.json)). The first
  window, on candidate `54f1402e`, failed at the container-host start step fixed above, and the
  second, on candidate `9eca7bae`, at the Linux client's stdin, also fixed above.

### Changed

- RTX 5090 serves two requests at once with runtime `v0.6.14-qwen38-5090-beta.1` (published image
  `4c816b0c`, source `e20060b6`), deployment profile `qwen38-5090-v0.9.0` / configuration
  `cf1de114`. The profile adds `--max-concurrency 2 --pending-timeout-ms 180000`. KV capacity
  auto-resolves to 160,256 tokens, and VRAM after load is 30,244 MiB of 32,607 MiB, against
  28,144 MiB with one request. The 28672 MiB host floor, model, OMP 18.4.0 client and RTX 4090
  runtime and profile are unchanged.
- The eight-token MTP3 verify round uses tensor cores instead of SIMT Q5 projections. Two
  decoding requests reached 281.1-283.0 tok/s together against 166.7-167.1 one at a time
  (1.68-1.70x), up from v0.6.13's 190.0-191.1 tok/s with two requests. The candidate answered the
  89-case role corpus byte-identically to v0.6.13, two cases at a time and one at a time, and
  the published image answered it byte-identically to the candidate; every measured decode pair
  and fanout branch matched one request at a time
  ([EXP-077](docs/measurements/2026-09-29-rtx5090-two-requests-in-flight.json)).
- The RTX 5090 pending timeout is 180 s. A request that does not fit beside the running one
  waits at the server; the 30 s default expired with `request_queue_timeout`. The new deadline
  plus the longest root prefill (130,048 tokens in 58.4 s on the published image) stays inside
  OMP's 300 s stream-idle watchdog, so the server ends a too-long wait and OMP resends.
- `examples/manual-tunnel/fail-closed.yml` sets `providers.maxInFlightRequests` to 2 for
  `ninfer-beta` and `ninfer-main` (RTX 5090), and keeps `ninfer-native-4090` and `ninfer-heavy`
  at 1 (RTX 4090). Upgrade the RTX 5090 server before merging these limits into OMP's config;
  two requests against the old one-at-a-time server can expire at its 30 s deadline. RTX 5090
  sessions saved by v0.8.7 re-prefill once after the build change; RTX 4090 checkpoints carry
  over ([qualification](releases/v0.9.0/qualification.json),
  [release notes](releases/v0.9.0/NINFER_RELEASE_NOTES.md)).

## [0.8.7] - 2026-09-29

### Fixed

- An RTX 4090 compaction handoff no longer re-prefills the whole session. OMP asks for the
  summary with `tool_choice: none`, and the runtime rendered that request without the tool block
  every other turn starts with. Runtimes `v0.6.10-qwen38-4090-beta.1` and
  `v0.6.13-qwen38-5090-beta.1` render the declared tools and end the turn at the template's
  tool-call token: handoffs of 78.4-80.4K tokens reused 78.0-79.9K cached tokens and reached the
  first token in 0.58-0.70 s, where v0.6.9 prefilled 97.4-97.5K tokens from root in 63.8-66.3 s
  ([EXP-074](docs/measurements/2026-09-29-long-session-cache.json)).
- A near-capacity turn whose planner search runs out of time keeps its session's continuation.
  The maximal fallback seeded only from the root candidate, which evicts the admitting session's
  own continuation: the RTX 4090 re-prefilled about 102,600 tokens (68 s), and this was the
  RTX 5090 chained turn of 93.7-105.1K tokens that v0.8.6 listed with an unidentified cause. The
  fallback now seeds from every candidate that keeps its source. In three stock OMP sessions on
  the RTX 5090 the three fallback turns reused 78.0-80.5K cached tokens (12.4-12.5 s to the first
  token), and no turn prefilled more than 60K tokens from root.
- A crash after a compaction restores the compacted session. Automatic saves start at 32,768
  tokens, so the shorter, compacted lineage stayed unsaved and a crash restored the
  pre-compaction checkpoint. A session with a checkpoint on disk now keeps it current at any
  size, and an unstored Responses turn leaves its lineage alone: after a hard kill the next
  RTX 4090 turn reused 32,167 cached tokens in 2.9 s, where v0.6.9 prefilled 32,173 tokens from
  root (29.2 s).
- Short sessions no longer delete long sessions' checkpoints. Oldest-first reclamation let about
  26 short OMP sessions fill the RTX 5090's 24 GiB checkpoint store and delete every long
  session's checkpoint. Reclamation now takes checkpoints below `--session-checkpoint-min-tokens`
  first. With 35 short sessions filling the store, a 60,026-token session kept its checkpoint and
  after a crash reused 60,057 cached tokens (2.9 s on the RTX 5090, 3.1 s on the RTX 4090), where
  v0.6.9 failed the turn with `previous_response_not_found`.
- The RTX 4090 controller no longer fails an action when the server writes a checkpoint while the
  controller walks the state tree.
- v0.8.6 attributed the cold first turn after a graceful restart to a stale checkpoint. A graceful
  server restart restores hot on both runtimes; the cold turn comes from restarting the OMP
  process, listed under Known limitations (EXP-074).
- The documented restart check no longer seeds its session with a misspelled copy of its own
  nonce. The check seeds from the release's own documents, and v0.8.6's notes quote the
  misspelled copy its first window wrote. In v0.8.7's first RTX 5090 window the session restored
  hot (71,791 of 71,839 tokens reused) and the model returned that quoted copy instead of the
  planted nonce. The seed now drops every line that contains the nonce's digits, and a test holds
  the documented seed to that. On the RTX 4090 the recall returned the quoted copy in 4 of 30
  trials with the old seed and in none of 30 with the new one
  ([EXP-076](docs/measurements/2026-09-29-restart-seed-decoy.json)).

### Changed

- `examples/manual-tunnel/fail-closed.yml` limits each NInfer provider to one request in flight
  (`providers.maxInFlightRequests`) and leaves compaction at OMP's default, replacing v0.8.6's
  `compaction.asyncEnabled: false`. OMP compacts in the background again, and the turn that meets
  a running summary waits in OMP, which has no deadline, instead of expiring at the runtime's 30 s
  admission deadline. On the RTX 4090, three handoff compactions and a restart ran 55 requests
  with none expired, and 22 turns took 365.4 s where inline compaction took 678.2 s for 24. The
  limit names every provider id a documented route or the fleet declares: OMP leaves an unlisted
  provider unlimited, and on a mock endpoint with only `ninfer-beta` limited the RTX 4090 route's
  turn failed after six expired attempts.
- Upgrade from v0.8.6 by following the quickstart for your lane: RTX 5090 runs the new image
  digest with the same arguments and profile, and RTX 4090 installs the new native package. In
  `~/.omp/agent/config.yml`, remove `compaction.asyncEnabled: false` and merge
  `providers.maxInFlightRequests`. Both server builds change, so each saved session re-prefills
  once.

### Added

- EXP-074 measured the provider limit and the runtime changes on the RTX 4090, with the RTX 5090
  production log as the red case; the RTX 5090 lane receipt records the same changes on its
  runtime. EXP-075 reran the stock OMP 18.4.0 durable-session proof on both new runtimes: one
  session across graceful restarts, and every turn after the seed cached
  ([EXP-075](docs/measurements/2026-09-29-stock-omp-1840-durable-sessions.json)).
- Fresh acceptance on candidate `a1e51a70` with unmodified OMP 18.4.0 and the published
  components: all four documented routes passed **24 steps** (RTX 5090 container host 2,
  macOS client 10, Windows client 5 and RTX 4090 native Windows 7); both hosts were restored
  ([routes](releases/v0.8.7/acceptance/documented-routes.json),
  [composed acceptance](releases/v0.8.7/acceptance/composed-external-installation.json)).
  The upstream macOS arm64 (preview), Windows x64 and Linux x64 binaries each passed a typed
  tool turn, an exact continuation and a fail-closed request against image `d71e34c3`;
  Linux ran under WSL2, not a separately qualified Linux OS. The RTX 5090 routes ran from a
  separately hosted Apple silicon Mac mini on macOS 26.6.1 over the tailnet, in two production
  windows with downtime at most **264.5 s** and **384.1 s (6.4 min)**
  ([restoration](docs/measurements/2026-09-29-v087-acceptance-restoration.json)). The first
  window, on candidate `9474326f`, failed at the macOS restart step on the seeded quote above.
  [Qualification](releases/v0.8.7/qualification.json) ·
  [Release notes](releases/v0.8.7/NINFER_RELEASE_NOTES.md).

### Known limitations

- A restart of the OMP process costs one prefill of a resumed session's context on either lane:
  OMP 18.4.0's first request after resuming omits the session's reasoning, so it cannot match
  the restored checkpoint (56,174 tokens from root, 32.0 s to the first token, in EXP-074). The
  next request caches again. This is an upstream OMP item.

## [0.8.6] - 2026-09-28

### Fixed

- A long session no longer fails a turn while OMP compacts it. OMP 18.4.0 starts its compaction
  summary in the background as a session nears its threshold, and both lanes admit one request at
  a time, so the user's next turn waited behind that request. Each attempt expired at the
  runtime's 30 s admission deadline and OMP resent it. On the RTX 4090 the background handoff
  took 56-61 s, and in the third of three compactions it outlasted the resends and the turn
  failed with `503 request_queue_timeout`. The config every route installs
  (`examples/manual-tunnel/fail-closed.yml`) now sets `compaction.asyncEnabled: false`, so OMP
  compacts before the turn: three consecutive RTX 4090 compactions took 77-84 s each with no
  expired admission, and the session recalled its newest identifier after each compaction and
  after a graceful restart
  ([EXP-072](docs/measurements/2026-09-28-omp-long-sessions.json)). The RTX 5090's snapcompact
  runs on the client in under 0.1 s and is unaffected.
- Upgrade from v0.8.5 by merging `compaction: asyncEnabled: false` into
  `~/.omp/agent/config.yml`. The client, provider fragments, both runtimes, models and serving
  configurations are unchanged, and checkpoints carry across.
- The documented resume and restart checks no longer ask the model to restate the nonce. Both
  lanes sample at temperature 1.0, so every copy of the nonce the model writes can change it. In
  the first v0.8.6 RTX 5090 window, the macOS route's acknowledgment wrote `COBOLT-493817` and the
  recall returned that copy instead of the planted `COBALT-493817`. v0.7.4's structured probe had
  failed the same way, and only the probe was corrected then. Every documented check now plants
  the nonce with an OK-only reply and asks for a verbatim recall, as the probe does, and a test
  holds the routes and the probe to that. In 92 alternating trials per prompt pair on the
  RTX 5090 runtime, v0.8.5's plant restated the nonce visibly in 87 turns and v0.8.6's in none;
  the one misspelled copy seen (1 in 785) stayed in thinking, and the recall returned the planted
  nonce ([EXP-073](docs/measurements/2026-09-28-omp-acceptance-sampling.json)).
- The RTX 4090 route harness no longer refuses a passing documented route because the model made
  a second tool call. The route's prompt asks for a file-reading tool, and in 1 of 20
  reproductions the model globbed for `marker.txt` before reading it. v0.8.6's second RTX 4090
  run made two tool calls and was refused as not exactly one call. The harness now requires the
  completed requests to equal the three documented turns plus one per tool call, so a hidden
  retry or a duplicate request still fails (EXP-073).
- Release tooling: the lane stage turns a staged draft manifest into a candidate, which v0.8.5
  and v0.8.6 needed by hand (the RTX 4090 route refused the first v0.8.6 candidate as not
  installable), and staging names the staged release as its GitHub publication target rather
  than the predecessor's.
- EXP-070 to EXP-072 declared `schema_version` as `"1"` and
  `raw_prompts_outputs_or_secrets_included` as the string `"False"`, which a reader testing the
  flag takes as true. They now use an integer and a boolean like every other measurement record,
  and a test holds all records to that.

### Added

- `scripts/omp_long_session_proof.py` drives one stock OMP session through repeated automatic
  compactions, and optionally a server restart after the last, on one lane. It gates on every
  turn completing, the expected method committing every compaction, the newest identifier
  surviving each compaction and the restart, and one OMP session id. It records, without gating,
  whether older identifiers survive: snapcompact drops part of the older middle by design.
- EXP-072 measured both lanes with it. The RTX 5090 read back both identifiers that existed only
  inside snapcompact frames, which reach the model at native resolution under `detail: "auto"`.
  The RTX 4090 kept all three older identifiers through three handoffs.
- EXP-073 measured the two acceptance checks that failed during v0.8.6's acceptance under the
  lanes' temperature-1.0 sampling: nonce restatement on the RTX 5090 and the documented tool
  turn's calls on the RTX 4090.
- Fresh acceptance on candidate `4f49fce7` with unmodified OMP 18.4.0 and the published
  components: all four documented routes passed **24 steps** (RTX 5090 container host 2,
  macOS client 10, Windows client 5 and RTX 4090 native Windows 7); both hosts were restored
  ([routes](releases/v0.8.6/acceptance/documented-routes.json),
  [composed acceptance](releases/v0.8.6/acceptance/composed-external-installation.json)).
  The upstream macOS arm64 (preview), Windows x64 and Linux x64 binaries each passed a typed
  tool turn, an exact continuation and a fail-closed request against image `cd9e10b1`;
  Linux ran under WSL2, not a separately qualified Linux OS. The RTX 5090 routes ran from a
  separately hosted Apple silicon Mac mini on macOS 26.6.1 over the tailnet, in two production
  windows with downtime at most **186.9 s** and **392.1 s (6.5 min)**
  ([restoration](docs/measurements/2026-09-28-v086-acceptance-restoration.json)). The first
  window, on candidate `1fa202fd`, failed at the macOS resume step on the restated nonce above;
  candidate `60b5d82d`'s documented RTX 4090 route passed but its harness refused the second
  tool call. [Qualification](releases/v0.8.6/qualification.json) ·
  [Release notes](releases/v0.8.6/NINFER_RELEASE_NOTES.md).

### Known limitations

- On the RTX 4090 the turn that carries a compaction takes 91-101 s: the handoff re-prefills the
  whole session, because the runtime renders OMP's `tool_choice: none` summary request without
  the tool block every other turn starts with, and the compacted context is prefilled once more
  after it. A turn sent just below the threshold can also re-prefill about 102,600 tokens
  (68 s): OMP replays the whole session there, and the runtime reuses no cache for the second
  replay in a row.
- After a compaction, a graceful restart restores a checkpoint that reuses nothing, so the first
  turn re-prefills the compacted context once (about 32,000 tokens, 17 s on the RTX 4090).
  Without compaction the restore is hot. These are runtime items for a later release.

## [0.8.5] - 2026-09-28

### Changed

- Repin the unmodified upstream Oh My Pi client from 18.3.5 to
  [18.4.0](https://github.com/can1357/oh-my-pi/releases/tag/v18.4.0), source
  `401778d0cd30020ce0f9198f751b13c68850562f` (published 2026-09-28T03:33:34Z).
  The RTX 5090 provider fragments also fix automatic compaction; both lanes retain the
  exact v0.8.4 runtime bytes, model, serving
  configurations and memory floors. RTX 5090 keeps `v0.6.12-qwen38-5090-beta.1`, image
  `cd9e10b1`, server `3ab266e5`, source `9d1ef748`, profile `qwen38-5090-v0.8.2`,
  configuration `56878aed` and its carried v0.8.3 lane receipt. RTX 4090 keeps
  `v0.6.9-qwen38-4090-beta.1`, package `6492588e`, server `65364401`, source `5ac17674`,
  configuration `ccecfbe3` and 60000 ms keep-warm with the sm_89 50 ms/100 ms spin. Its
  carried v0.8.4 lane receipt records OMP 18.3.5 qualification, not a new 18.4.0 runtime run.
- Upgrade from v0.8.4 by swapping the client binary and adding
  `supportsImageDetailOriginal: false` under the RTX 5090 model's `compat` in
  `~/.omp/agent/models.yml`. Other fragment fields and `PI_OPENAI_STATEFUL=1` are unchanged;
  neither server build changes, so checkpoints on both lanes carry across. No performance
  gain is claimed.

### Fixed

- Long RTX 5090 sessions survive OMP's automatic compaction with the corrected provider
  fragments. OMP compacts at 111,412 tokens of a 131,072-token session; snapcompact archives
  earlier turns as PNGs at `detail: "original"`, which NInfer refuses with HTTP 400
  `image_detail_not_supported`. This broke the first compaction on stock OMP 18.3.0-18.4.0
  (releases v0.8.0-v0.8.4). The fragments now declare
  `compat.supportsImageDetailOriginal: false`, so OMP sends `auto`. One compacted continuation
  on the RTX 5090 runtime completed with 26,075 input tokens and the exact nonce; `original`
  was refused in 9 ms
  ([EXP-071](docs/measurements/2026-09-28-omp-snapcompact-image-detail.json)). Readback beyond
  that nonce and repeated compactions were not measured. The text-only RTX 4090 model is
  never compacted into images. The first v0.8.5 candidate hit the failure at the macOS route
  restart step as its document seed grew from 332,331 to 343,205 bytes; the step now seeds
  the first 200,000 ASCII bytes (about 64,000 tokens) to test restoration, not compaction.
- Windows one-shot completion status through upstream fix `9d3e0d4975`
  ([#13470](https://github.com/can1357/oh-my-pi/issues/13470)). In
  [EXP-070](docs/measurements/2026-09-28-omp-1840-windows-completion-status.json), using the
  documented RTX 4090 provider fragment against a local mock Responses endpoint, OMP 18.3.5
  exited 1 after 5/5 complete `omp models` listings and printed a false
  `ended before completing` line after 5/5 completed `omp -p` turns that exited 0. OMP 18.4.0
  exited 0 without the false line in all 10 runs. Both retain the existing `Working...`
  stderr indicator. This is Windows x64 client-status evidence, not an inference measurement.

### Removed

- The RTX 4090 route harness's 18.3.5-only exit-status tolerance (`c8824f1`) and the
  troubleshooting entry for the false completion line. The provider-parser check again
  requires exit 0 plus exactly the documented selector.

### Added

- Fresh acceptance on candidate `943063e7` with unmodified OMP 18.4.0 and the published
  components: all four documented routes passed **24 steps** (RTX 5090 container host 2,
  macOS client 10, Windows client 5 and RTX 4090 native Windows 7); both hosts were restored
  ([routes](releases/v0.8.5/acceptance/documented-routes.json),
  [composed acceptance](releases/v0.8.5/acceptance/composed-external-installation.json)).
  The upstream macOS arm64 (preview), Windows x64 and Linux x64 binaries each passed a typed
  tool turn, an exact continuation and a fail-closed request against image `cd9e10b1`;
  Linux ran under WSL2, not a separately qualified Linux OS. The RTX 5090 routes ran in one
  production window, with downtime at most **381.2 s (6.4 min)**, from a
  separately hosted Apple silicon Mac mini on macOS 26.6.1 over the tailnet, not the
  maintainer's workstation
  ([restoration](docs/measurements/2026-09-28-v085-acceptance-restoration.json)).
  [Qualification](releases/v0.8.5/qualification.json) ·
  [Release notes](releases/v0.8.5/NINFER_RELEASE_NOTES.md).

## [0.8.4] - 2026-09-28

### Every lane current

- RTX 4090 advances to `v0.6.9-qwen38-4090-beta.1` (package
  `6492588ea9b62a02a5b83434c653c61ea709c7d1609eb9de9d1c0eaf7ae23e87`, source
  `5ac17674e8e0b6ecd2bdc56a8eb6f9c397c2c1f4`). RTX 5090 keeps
  `v0.6.12-qwen38-5090-beta.1`, its image, server, serving arguments, deployment profile
  `qwen38-5090-v0.8.2` and carried v0.8.3 lane receipt. The model and memory floors are unchanged.
- RTX 4090 enables `engine.gpu_keep_warm_ms = 60000` with an sm_89-specific spin of 50 ms every
  100 ms. The RTX 5090's 3.5 ms/10 ms pattern did not hold this card in P2
  ([EXP-064](docs/measurements/2026-09-27-rtx4090-engine-keep-warm.json)). New sessions after
  12-58 s idle prefilled in 0.146-0.148 s (time to first token 0.167-0.178 s); all 31 outputs were
  byte-identical, at about 72 W above idle while held. A request arriving mid-spin can overlap
  one warp for up to 50 ms
  ([EXP-066](docs/measurements/2026-09-27-rtx4090-keep-warm-long-spin.json)).
- The RTX 4090 package passed all 15 canonical qualification phases: 130,048-token exact
  retrieval in 91.0 s, C1 decode 157.90 tok/s at 87.59% MTP acceptance (v0.6.8: 157.89), managed
  stop, security, an OMP 18.3.5 typed tool turn and rollback in both directions versus v0.6.8
  ([lane receipt](releases/v0.8.4/qualification/rtx4090.json)). Its decode kernels are unchanged.
  The controller passes the keep-warm flag only when the release's own packaged config declares
  a positive value, so older servers still start on rollback.
- The field start from the memory state that refused v0.6.6 passed with the published v0.6.8
  package (3.5 GiB free, 22.6 GiB standby; EXP-064's `issue_48_field_start`). A recurrence still
  reports the commit limit, available commit and available memory
  ([#48](https://github.com/alphastorm/omp-ninfer/issues/48)).
- Repin the unmodified upstream Oh My Pi client to 18.3.5. Its macOS arm64 binary kept one short
  session across graceful restarts on both lanes with the documented fragments unchanged
  ([EXP-067](docs/measurements/2026-09-27-stock-omp-1835-durable-sessions.json)). The four
  documented routes passed on candidate `68302298` with the published components: RTX 5090
  container host (2 steps), macOS client (10), Windows client (5) and RTX 4090 native Windows
  (7), with both hosts restored. The upstream macOS arm64 (preview), Windows x64 and Linux x64
  binaries each passed a typed tool turn, an exact continuation and a fail-closed request against
  image `cd9e10b1`; Linux ran under WSL2, not a separately qualified Linux OS
  ([routes](releases/v0.8.4/acceptance/documented-routes.json),
  [composed acceptance](releases/v0.8.4/acceptance/composed-external-installation.json)).
  The RTX 5090 ran in one production window, with downtime at most 421.5 s (7.0 min), from a
  separately hosted Apple silicon Mac mini on macOS 26.6.1 over the tailnet, not the maintainer's
  workstation ([restoration](docs/measurements/2026-09-28-v084-acceptance-restoration.json)).
- On Windows, OMP 18.3.5 prints a false `ended before completing` line after finished `omp -p`
  turns and exits 1 after a complete `omp models` listing
  ([can1357/oh-my-pi#13470](https://github.com/can1357/oh-my-pi/issues/13470), fixed in 18.4.0).
  The RTX 4090 route's first candidate, `0315c5d4`, stopped at its no-effect preflight because
  the provider-parser check read only that exit status. That release changed the check to judge the listing;
  candidate `68302298` passed the literal documented blocks on the published v0.6.9 package,
  with original state restored byte for byte. v0.8.4 pinned 18.3.5; v0.8.5 repins to 18.4.0.
  The v0.8.4 route tolerated that exact completion line only from 18.3.5.
  [Route receipt](releases/v0.8.4/acceptance/documented-routes.json).
- A steer submitted mid-stream does not abort the response: OMP sent it 27 ms after
  `response.completed` as a new request chained by `previous_response_id`
  ([EXP-068](docs/measurements/2026-09-28-omp-1835-live-steering.json)).
- RTX 4090 checkpoints saved by v0.6.8 are incompatible with v0.6.9's changed server build, so
  each session re-prefills once. RTX 5090 keeps its server build and carries v0.8.3 checkpoints.
- The upstream engine merge stays deferred: e31bc99b's 1.5% single-run prefill lead was already
  present in EXP-048, while decode rounds are about 18% slower and reuse is weaker
  ([EXP-065](docs/measurements/2026-09-27-engine-window-upstream-e31bc99b-vs-shipped.json)).
  The RTX 4090 Q5 tensor-core route was rejected by its pre-registered rule: +0.38% at 26K and
  +0.40% at 60K against required 2.0%/1.0% gains
  ([EXP-069](docs/measurements/2026-09-28-rtx4090-q5-small-t-mma.json)).
  RTX 3090's unpublished v0.6.2-beta.1 package built and tested at `5ac17674` is not in the
  manifest; hardware qualification remains pending
  ([preparedness](docs/measurements/2026-09-28-rtx3090-v062-build-preparedness.json)).

## [0.8.3] - 2026-09-27

### Faster decode (RTX 5090)

- Rebind RTX 5090 to `v0.6.12-qwen38-5090-beta.1` (image
  `sha256:cd9e10b115bbf38df011b201dfdd37ec3b56613da39b2f1701334c8157236b78`, source
  `9d1ef7485d9c741c2830fa3d55218f3242cec5d7`). Its serving arguments, deployment profile
  `qwen38-5090-v0.8.2` and configuration `56878aed` are unchanged; RTX 4090 stays on
  `v0.6.8-qwen38-4090-beta.1`, and the model, memory floors and the upstream OMP 18.3.0 client are
  unchanged.
- The MTP3 verify pass runs its four Q5 projections on a small-T tensor-core MMA
  ([EXP-057](docs/measurements/2026-09-26-q5-small-t-tensor-core.json)). Release build against
  release build, the round is 3.5-4.9% shorter and decode 4.4% faster at a 26K-token context, 3.6%
  at 60K and 6.3% at 1,024 tokens (EXP-063's A/B/B/A). Generated text changes: 58 of 89
  role-corpus cases answer differently from v0.8.2.
- A pre-registered paired screen of 504 redaction prompts found the new runtime's redaction
  behaviour not worse than v0.8.2's: 561 synthetic secrets leaked against 582, and 53.2% of prompts
  passed against 52.6% ([EXP-063](docs/measurements/2026-09-27-powered-redaction-screen.json)).
  `scripts/redaction_screen.py` runs the screen and decides it by its fixed rule.
- Every RTX 5090 runtime gate was measured again on the published image: profile gates
  (130,048-token exact retrieval in 58.7 s, decode 168.07 tok/s), the durability workload with
  both stops, the publication barrier, the probes, the agent mix (none of 24 fresh sessions fell
  back to a full prefill; median time to first token 0.093-0.100 s) and the stock OMP 18.3.0
  session proof; its role-corpus answers were byte-identical to the screened candidate's. The
  unchanged RTX 4090 package carries its v0.8.1 lane receipt. The four documented routes passed
  with the unmodified OMP 18.3.0 client: RTX 5090 container host (2 steps), macOS client (10),
  Windows client (5) and RTX 4090 native Windows (7), with both hosts restored; the upstream macOS
  arm64, Windows x64 and Linux x64 binaries each passed a typed tool turn, an exact continuation
  and a fail-closed request against the RTX 5090 image
  ([composed acceptance](releases/v0.8.3/acceptance/composed-external-installation.json)).
- Checkpoints are bound to the exact server build, so sessions saved by v0.8.2 are not restored on
  v0.8.3: OMP resends the full conversation and each session re-prefills once.

### Release tooling

- `verify_release.py` checks launch identity for every installable release, not only ready ones.
  Each profile must hash to the configuration identity it declares, and the RTX 5090 lane
  receipt's recorded deployment profile, configuration, server and model must equal the
  manifest's. `stage_release.py` refuses a renamed deployment profile that keeps its source's
  configuration identity. v0.8.3's first candidate had exactly that mismatch: it passed the old
  check, and the documented route's launcher refused it.

## [0.8.2] - 2026-09-26

### GPU keep-warm (RTX 5090)

- Rebind RTX 5090 to `v0.6.11-qwen38-5090-beta.1` (image
  `sha256:26813f5661e9bab7093349a216543d9391d310c08a207fee4d389d763dd36930`, source
  `32c21f73a7605f76480a6139de0488a14ed1aa48`). RTX 4090 stays on `v0.6.8-qwen38-4090-beta.1`, and
  the model, memory floors and the upstream OMP 18.3.0 client are unchanged.
- New RTX 5090 sessions that arrive after idle start at back-to-back speed. After its last work the
  card steps down to its lowest idle clocks within about 9 s, and the first prefill after that ran
  up to 2.3x slower
  ([EXP-060](docs/measurements/2026-09-26-idle-gpu-new-sessions.json)). The runtime's new
  `--gpu-keep-warm-ms N` (off by default) spins a single-warp kernel that touches no memory for
  3.5 ms of every 10 ms on its own stream for N ms after the server goes idle, and stops when a
  request is admitted. The RTX 5090 profile sets 60000, so its deployment profile advances to
  `qwen38-5090-v0.8.2` (configuration `56878aed`). New sessions after 12-58 s of idle prefilled in
  0.155-0.157 s instead of 0.253-0.304 s (time to first token 0.173-0.181 s instead of
  0.316-0.366 s), and the 89-case role corpus stayed byte-identical. Requests that arrived 1-5 ms
  after the previous one, while a spin could still run, changed time to first token by a median of
  -0.1 ms (worst +4.4 ms). The hold draws about 71 W above idle while it runs; over production's
  recorded agent traffic a 60 s grace would have covered 84 of the 138 requests that arrived after
  5 s or more of idle, at about 2.3 W on average
  ([EXP-062](docs/measurements/2026-09-26-engine-keep-warm.json)).
- Every RTX 5090 runtime gate was measured again on the published image: profile gates
  (130,048-token exact retrieval in 56.4 s, decode 160.07 tok/s), the durability workload with
  both stops, the publication barrier, the probes, the agent mix (none of 24 fresh sessions fell
  back to a full prefill; median time to first token 0.090-0.098 s) and the stock OMP 18.3.0
  session proof; the unchanged RTX 4090 package carries its v0.8.1 lane receipt. The four
  documented routes passed with the unmodified OMP 18.3.0 client: RTX 5090 container host (2
  steps), macOS client (10), Windows client (5) and RTX 4090 native Windows (7), with both hosts
  restored; the upstream macOS arm64, Windows x64 and Linux x64 binaries each passed a typed tool
  turn, an exact continuation and a fail-closed request against the RTX 5090 image
  ([composed acceptance](releases/v0.8.2/acceptance/composed-external-installation.json)).
- Checkpoints are bound to the exact server build, so sessions saved by v0.8.1 are not restored on
  v0.8.2: OMP resends the full conversation and each session re-prefills once.

## [0.8.1] - 2026-09-25

### Faster decode (both lanes)

- Rebind RTX 5090 to `v0.6.10-qwen38-5090-beta.1` (image
  `sha256:5ca6e416bf896e73696e04b9324dc279e22104e0c325e0b4d1989d1a41df02e8`, source
  `8cc0810acc296bac482187da171afddd93df7fb9`) and RTX 4090 to `v0.6.8-qwen38-4090-beta.1` (source
  `5a774841c29bdf2ee6b7efba135aed0a47e80447`). The model, serving settings, memory floors and the
  upstream OMP 18.3.0 client are unchanged.
- MTP3 decode is faster. The verify pass's small-extent Q4 and Q5 projections share each
  activation load across weight rows, and the Q4 MLP gate/up kernel pads its staged weight rows so
  its shared-memory reads no longer conflict; every row keeps its arithmetic order. On the RTX
  5090, decode is 10.3-11.0% faster from a seed context to 31K tokens (a 26K-context decode round
  takes 16.08 ms instead of 17.75 ms), the 89-case role corpus answers identically at temperature
  0, and 130,048-token retrieval stays exact. On the RTX 4090 the MLP down and mixer output
  projections keep one row per warp, because sharing loads made them slower there; its C1
  benchmark decodes at 157.89 tok/s instead of 153.54
  ([EXP-055](docs/measurements/2026-09-25-decode-kernel-schedules.json); attribution in
  [EXP-054](docs/measurements/2026-09-25-decode-roofline-attribution.json)).
- Every runtime gate was measured again on the published components: the RTX 5090 image's
  durability workload, publication barrier, probes, shared-prefix capacity and stock OMP 18.3.0
  session proof match v0.8.0, and the RTX 4090 package passed its 15 canonical phases. The four
  documented routes passed with the unmodified OMP 18.3.0 client: RTX 5090 container host (2
  steps), macOS client (10), Windows client (5) and RTX 4090 native Windows (7), with both hosts
  restored; the upstream macOS arm64, Windows x64 and Linux x64 binaries each passed a typed tool
  turn, an exact continuation and a fail-closed request against the RTX 5090 image
  ([composed acceptance](releases/v0.8.1/acceptance/composed-external-installation.json)).
- Checkpoints are bound to the exact server build, so sessions saved by v0.8.0 are not restored on
  v0.8.1: OMP resends the full conversation and each session re-prefills once.

## [0.8.0] - 2026-09-25

### Bring your own OMP

- The documented client is the unmodified upstream
  [Oh My Pi v18.3.0](https://github.com/can1357/oh-my-pi/releases/tag/v18.3.0) release binary for
  Windows x64, Linux x64 and macOS arm64, downloaded and checked against its SHA-256; there is no
  fork build, archive or installer. The provider fragments keep thinking within the template's
  `low`, `medium` and `xhigh` efforts and turn off encrypted reasoning and reasoning summaries,
  and every route exports `PI_OPENAI_STATEFUL=1`.
- Rebind RTX 5090 to `v0.6.9-qwen38-5090-beta.2` (image
  `sha256:049dc788f6e5353b159edaece53afbabb219bc6e49f1e8ce8675338fada521a6`, source
  `86733c0e93fceccf9af3fa345ca9c8b6754f7abb`) and RTX 4090 to `v0.6.7-qwen38-4090-beta.2` (source
  `b0e8c2fa732e3a84eeb356c5e586879f3563c70c`, the same runtime plus the Windows-only commit margin
  below). The model, serving settings and memory floors are unchanged.
- Stock clients get durable sessions. With API authentication the runtime hashes a request's
  `prompt_cache_key` into the session identity, never storing the raw key, and refuses it together
  with `ninfer_session` or `X-NInfer-Session`; a returning session's checkpoint is restored on its
  first request after a restart. On both published lanes, unmodified OMP 18.3.0 kept one session
  across graceful restarts, including a new OMP process resuming after a restart
  ([EXP-053](docs/measurements/2026-09-25-stock-omp-durable-sessions.json)). The runtime diff passed
  an independent four-model council and four remediation epochs (council
  `CR-20260925-ninfer-stock-client`).
- Responses tool outputs may be content parts. Stock OMP returns an image read as an `input_text`
  and `input_image` array; the RTX 5090 passes the image to the model inside the tool turn, and
  the text-only RTX 4090 refuses the image as `vision_disabled` instead of rejecting the request as
  malformed.
- New sessions start faster: the shared-prefix catalog holds one owner per active request or per
  cache marker, whichever is larger (four at one active request). With 11.9-14.2K-token agent
  prefixes on the RTX 5090, fresh sessions that fell back to a full prefill dropped from 24 of 24
  to 0 of 24, and time to first token from 3.78-4.52 s to 0.092-0.100 s
  ([EXP-052](docs/measurements/2026-09-25-agent-mix-shared-prefix.json)).
- RTX 4090: a start could fail when the driver refused to pin the host-KV pool
  ([#48](https://github.com/alphastorm/omp-ninfer/issues/48)). The server now commits and releases
  each pinned allocation's size plus 1/64 before pinning it, so the pin no longer races the
  system-managed pagefile extension; the qualified package passed its first managed start after a
  fresh install, where the candidate without that margin was refused. #48 stays open until field
  confirmation.
- Sessions saved under the fork client's `ninfer_session` names are not reachable from stock OMP:
  each takes one cold first turn after the upgrade, and the old checkpoints age out under the
  checkpoint quota.
- The four documented routes passed on the published components with the unmodified OMP 18.3.0
  client: RTX 5090 container host (2 steps), macOS client (10), Windows client (5) and RTX 4090
  native Windows (7), with both hosts restored; the upstream macOS arm64, Windows x64 and Linux x64
  binaries each passed a typed tool turn, an exact continuation and a fail-closed request against
  the RTX 5090 image ([composed acceptance](releases/v0.8.0/acceptance/composed-external-installation.json)).
  The macOS profile stays `preview`: the upstream client has no managed installation.

### Added

- `scripts/stock_omp_session_proof.py` proves that an unmodified upstream OMP binary keeps one
  NInfer session across graceful server restarts: one process across a restart, a new process
  with the server up, and a new process after a restart must all recall the seeded facts under one
  OMP session id.
- `scripts/agent_mix_probe.py` measures shared-prefix reuse for a three-agent mix, one capacity
  arm at a time, joining every request to the server's request log.
- `scripts/stage_release.py --omp-component` stages an upstream-release client, and
  `scripts/verify_release.py` validates its provenance, per-platform binaries and bindings.

### Changed

- The documented-route acceptance harness installs the stock client the way the quickstart does,
  checks the installed binary against each profile's pinned upstream binary, binds the expected
  client version to the tested release manifest, and launches OMP with `PI_OPENAI_STATEFUL=1`.
  The composer builds client identity from the current release's upstream component only.
- The RTX 5090 Windows route's acceptance summary requires the documented tool marker as a token,
  as the macOS route and RTX 4090 harness do, and records whether it was a bare line; it refused a
  passing route whose model reported the marker inside a sentence. The structured probe still
  requires its whole answer exactly.

### Removed

- The product no longer builds or publishes an OMP client:
  `scripts/hosts/cut-omp-client-component.sh` is gone, and the documented routes no longer use the
  fork's `omp appliance` commands, which stock OMP does not have.

## [0.7.4] - 2026-09-24

### Durable-session runtime (both lanes)

- Rebind RTX 5090 to `v0.6.8-qwen38-5090-beta.1` (image
  `sha256:f193b7469d062fc923b93ba72dbb4f8bb871912b505b529a062db50f65de2447`) and RTX 4090 to
  `v0.6.6-qwen38-4090-beta.1` (package `cd9ab90f`), both from source
  `1c17c3facfbfd1243cf7711a412119302e6dbd74`. The OMP 18.2.3 client, model, serving settings and
  memory floors are unchanged.
- Live sessions survive a graceful stop
  ([#45](https://github.com/alphastorm/omp-ninfer/issues/45),
  [#46](https://github.com/alphastorm/omp-ninfer/issues/46)): transient automatic checkpoint
  refusals retry once the engine quiesces; admission saves a session's newest turn before
  evicting it, waiting while that turn's reply is still being stored; re-saving a session under
  the disk quota keeps other sessions' only checkpoints, including when a cleanup fails; and a
  graceful stop counts a session already on disk as nothing to save. On the published RTX 5090
  image the EXP-050 workload stopped with `saved 1, nothing to save 3, refused 0` and all four
  stored sessions resumed from their checkpoints
  ([EXP-050](docs/measurements/2026-09-24-durable-session-eviction.json),
  [EXP-051](docs/measurements/2026-09-24-publication-barrier.json)).
- Saving before eviction delays the admitting request, about 6.5 s per 126K-token session on the
  RTX 5090; automatic checkpoints remain best effort.

### Added

- `scripts/engine_window_compare.py` records every session's newest stored response, and
  `--resume-from` continues each of them once after a restart of the same arm, recording whether
  the server restored it from its checkpoint. A desk-code answer cut off by the output limit now
  scores inconclusive instead of wrong.
- `scripts/hosts/cut-ninfer-4090-component.sh` publishes an RTX 4090 native runtime component
  after its canonical qualification. It defaults to a no-effect preflight that closes and verifies
  the asset set against its outer `SHA256SUMS`, matches the package build receipt and the lane
  specification at the commit, compares the source archive's tar stream byte for byte with
  `git archive` of the commit, and refuses an existing tag or release; `--publish` is
  founder-only.
- `scripts/hosts/publish-product-release.sh` publishes a product release. Its default no-effect
  preflight proves the commit is the release pull request's head with every check green, that main
  fast-forwards to it and the remote would accept the main and tag pushes, that neither the tag nor
  the GitHub release exists, and that a clean checkout of exactly that commit passes the ready
  verifier with its immutable pins. `--publish` (founder-only) fast-forwards main to the commit,
  which merges the pull request without rewriting the commits the evidence pins name, tags it and
  creates the release as Latest with the release's own notes.
- `scripts/hosts/accept-rtx5090-routes.py` runs the RTX 5090 documented routes (container host,
  macOS client, Windows client) and the three published clients' structured live acceptance in
  held production windows whose restoration runs in `finally` and under a watchdog, with
  `accept-rtx5090-host.py`, `accept-windows-client.ps1` and `omp-client-probe.py` on the hosts.
  `scripts/hosts/accept-rtx4090-route.py` with `accept-rtx4090-route.ps1` runs the native RTX 4090
  route in a child process and restores the lane's exact state bytes, task, support files and
  ACLs. Every action has a no-effect dry run, and no acceptance step retries automatically.
- `scripts/compose_route_acceptance.py` composes a release's route acceptance from the four
  documented-route runner receipts and the published clients' live evidence: the runner receipts
  byte for byte, one platform receipt per client profile, the RTX 4090 public-install receipt, the
  documented-route and composed external-installation receipts, and the ready posture. It refuses
  a route with a failed or missing step, a block executed with other bytes than bundled, a run from
  another commit, a live run against another runtime identity or without its tool, continuation or
  fail-closed observations, and a client binary other than the published one.
- `scripts/rebind_release.py --stage platform` pins each client profile's platform receipt to the
  commit holding its final bytes and refuses a commit whose bytes differ from the working tree.

### Changed

- The compatibility authority's `darwin-remote-ssh` profile is `preview` instead of `qualified`.
  It has been qualified but not installable since v0.3.0, and the pinned OMP 18.2.3 client reads a
  qualified profile as a released, installable one, so it rejects the whole authority: against the
  published v0.7.3 authority, `omp appliance doctor` fails with `Qualified profile lacks complete
  acceptance or GPU qualification evidence` for all three profiles. The documented macOS client
  route over the manual tunnel is unaffected and stays accepted. Release verification now refuses
  an installable release whose authority the client would reject, and the acceptance composer
  promotes only installable profiles to `qualified`.

### Fixed

- The RTX 5090 Windows Docker-local profile (`profiles/qwen38-rtx5090-windows-docker-local.json`)
  still named v0.7.2's client archive (`omp-18.0.9-cross-platform-beta-2`, its URL and hashes) after
  v0.7.3 repinned the client; it now names the manifest's `omp-18.2.3-cross-platform-beta-1`
  Windows archive. No documented route read that block, so no installation was affected. Release
  verification now rejects a profile whose client archive differs from the manifest's client.
- The upstream watch no longer reports an API-truncated delta as having no path overlap: GitHub's
  compare endpoint lists at most 250 commits and 300 files, and a cut list now scores
  `unknown-truncated` instead of recommending every commit as a pull candidate.
- The native qualification composer recorded every OMP golden run as `openai-completions`. It now
  reads the API the run's assistant messages used from the transcript and refuses a transcript
  that names none or more than one; OMP 18.2.3 reaches NInfer over `openai-responses`.

## [0.7.3] - 2026-09-18

### OMP 18.2.3 client repin

- Add a founder-run, checksum-bound native client component publisher that defaults to a
  no-effect preflight for the qualified archives, source/tree identities, and authentication
  routes. Live publication requires explicit `--publish`; final server-side authorization is
  evaluated by the intended live operations.
  Component publication does not update casks, installed clients, or product compatibility.

- Repin macOS arm64, Windows x64 and Linux x64 clients from OMP 18.0.9 to
  `omp-18.2.3-cross-platform-beta-1` at public source
  `5ade242de59ac0f4606a1158bf564410c96918d4`. All three client archives and provider-free
  hosted qualifications are public, and each client passed live inference.
- Fresh documented-route acceptance passed **24 steps**: RTX 5090 host 2, macOS client 10,
  Windows client 5, RTX 4090 native 7, on frozen product source
  `096c8b889eef4bc89ee2dc316694b847bdf8a39d`. The additional Linux live-client run used
  **Ubuntu under WSL2**; it is not non-WSL Linux OS qualification. Pre-cut substitutions are
  recorded and all hosts were restored. [Routes](releases/v0.7.3/acceptance/documented-routes.json) ·
  [qualification](releases/v0.7.3/qualification.json).
- Fix capability vocabulary to the client's existing `durable-checkpoint` rather than the
  rejected `process-restart-continuation` spelling; reject unsupported names in release verification.
- Limit v0.7.3 eligibility to RTX 5090 on Windows 11 + Docker Desktop/WSL2 and RTX 4090 native
  Windows 11. **RTX 3090 is deferred** until its host returns for new-client qualification.
  Its [historical v0.7.2 route](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)
  remains on OMP 18.0.9 and is not qualification with the new client.
- Carry the exact v0.7.2 RTX 5090 image and RTX 4090 package, model, serving arguments and
  memory floors. Runtime performance is carried evidence, not remeasured throughput.
  Automatic checkpoints remain best effort; the three unsaved predecessor sessions and
  two root fallbacks among eight continuations/forks remain limitations.
- Withdraw the RTX 3090 scout lane from every v0.7.3 install surface: the fleet recipe, model
  fragment, role map and tunnel script now bind only the two qualified lanes, the scout agent
  and its provider fragment are gone, and the native-Windows fragment drops the RTX 3090
  provider it declared on the RTX 4090 port. The three-lane form stays at the immutable
  [v0.7.2 tag](https://github.com/alphastorm/omp-ninfer/tree/v0.7.2/examples/fleet).
  The fleet's measured boundary is restated for two lanes: cost-aware dispatch of the fixed
  14-job batch in 43.4 s against 66.8 s on the RTX 5090 alone; the faster three-lane figure in
  EXP-016 used the deferred GPU. All 24 accepted executable step bodies are unchanged.
- Extend release verification after focused review: acceptance and native qualification receipt
  URLs must name this product release, a qualified profile must declare the core client
  capabilities and the continuation capability its own receipt observed, the product
  qualification date must be the aggregate cutoff of its evidence, and manifest prose may name
  only component tags the release binds. Install surfaces are covered too: every payload a
  documented block installs must declare only qualified lanes.
  [Review dispositions](releases/v0.7.3/review/composition-ledger.json).

## [0.7.2] - 2026-09-17

### Bounded restore reclaim

- Both mainline lanes use reviewed runtime source
  `d125ffffd87ef38d9a221f9830e19dfa274ddd34`: RTX 5090 component
  `v0.6.7-qwen38-5090-beta.1` and RTX 4090 native component
  `v0.6.5-qwen38-4090-beta.1`, both published and accepted through their documented routes.
- Restore can reclaim reproducible checkpoint-backed resident sessions under host-KV pressure,
  saving a resident session first when its checkpoint is behind and retrying import with a fresh
  reader. The reviewed candidate bounds retry/reclaim progress; regression evidence covers
  capacity refusal before commit and preservation of unrelated sessions.
- [EXP-047 `final_reviewed_candidate`](docs/measurements/2026-09-17-restore-reclaim.json): both
  RTX 5090 target 126K-token sessions resumed (5.96 s and 23.57 s); all seven named probe families
  exited 0. The combined process also reported three unsaved predecessor sessions at shutdown
  (`saved 2`, `refused 3`) and three automatic checkpoint refusals. This is not proof of loss-free
  shutdown for every session or zero automatic refusals. The extra multisession control recorded
  root fallback on 2 of 8 continuations/forks without server errors: zero exit status does not
  establish universal warm reuse. The exact RTX 4090 package passed
  15 qualification phases, including exact 130,048-token retrieval; measured decode was
  153.431 tok/s and prefill 2,113.995 tok/s on its recorded fixture.
- Serving settings and floors stay unchanged: public RTX 5090 profile `qwen38-5090-v0.7.0`
  retains 16384 MiB host KV and the 28672 MiB runtime-host floor; native RTX 4090 retains
  11264 MiB host KV, 24 host-state slots, and the 32768 MiB floor. Scratch qualification
  settings and earlier smaller-pool experiments are not new supported defaults.
- OMP remains `omp-18.0.9-cross-platform-beta-2`; the RTX 3090 component and model are unchanged.
  The RTX 5090 host (2 blocks), macOS client (10), Windows client (5), and RTX 4090 native
  route (7) passed against the published components. Pre-cut clone substitutions are recorded;
  the final product retains the ready gate. Both host windows restored their incumbent state.

## [0.7.1] - 2026-09-16

The RTX 4090 native lane could report a successful checkpoint for a session at the context ceiling
and then fail to restore it. This release fixes that lane and makes the bound behind it visible and
enforced ([EXP-043](docs/measurements/2026-09-16-restore-bound-host-kv-pool.json)).

### Fixed

- **RTX 4090 native component `v0.6.4-qwen38-4090-beta.1`.** Restore materialises a continuation's
  KV into the host-KV pool, so that pool bounds the largest session a configuration can admit back.
  The lane shipped 4096 MiB - below the 5.02 GiB a 131,072-token session needs. Measured on the
  shipped component: a 125,888-token session's explicit checkpoint reported 4,834,325,255 B saved
  and the session answered HTTP 404 after a graceful stop and restart; with two such sessions all
  four continuations lost reuse, the stop reported `saved 1 ... refused 1`, and both sessions
  answered 404. The pool is now 11264 MiB: two ceiling sessions keep reuse (125,906 cached tokens
  in 1.97 s), both checkpoint, the stop reports `saved 2, nothing to save 0, refused 0`, and both
  resume exactly in 5.63 s and 7.78 s.
- **An export can no longer outlive its own restorability.** The restore admission check now runs
  at save time: a pool that could not re-admit the checkpoint answers HTTP 409 with
  `checkpoint save refused: program refused continuation export` instead of writing it.

### Changed

- The RTX 4090 lane declares `runtime_host.minimum_runtime_memory_mib` 32,768. The pool is pinned
  memory: 11264 MiB pins on a 32.4 GiB host with 11.6 GiB free, and 12288 MiB fails
  `cudaMallocHost` there.
- A refused restore names its gate - `program refused continuation import (host KV pool capacity
  exhausted)` - instead of `the engine did not accept the checkpointed continuation`.
- The startup capacity line publishes `host-kv-restorable=<tokens>` and the request log publishes
  `host_kv_restorable_tokens`, so a pool that cannot restore the configured ceiling is visible
  before any session exists.

### Measured

- **The RTX 5090 two-session restore boundary recorded in v0.7.0 has the same cause.** Two BF16
  ceiling sessions need about 18 GiB of pool against the lane's 16 GiB. A 20 GiB pool restores both
  (5.75 s and 9.22 s) but takes 28.28 GiB of a 31.34 GiB utility VM, which would raise that lane's
  runtime-host floor to roughly 40 GiB - so the lane keeps its pool and now reports the boundary
  with a named reason instead of an opaque one.

### Unchanged

RTX 5090 component `v0.6.5-qwen38-5090-beta.1` (image `5e3e1558`, deployment profile
`qwen38-5090-v0.7.0`), the RTX 3090 component, the pinned client
`omp-18.0.9-cross-platform-beta-2`, and the model artifact.

## [0.7.0] - 2026-09-16

The RTX 5090 serving configuration advances to a 16 GiB Host KV pool so two sessions at the
131,072-token ceiling keep their prefix reuse. The component, image, model, client, and KV dtype
are unchanged; the configuration identity is not, so checkpoints written under `v0.6.10` do not
carry across ([EXP-041](docs/measurements/2026-09-16-two-long-session-capacity.json)).

### Changed

- RTX 5090 deployment profile `qwen38-5090-v0.7.0`: Host KV pool 8 GiB to 16 GiB. Two 126K
  sessions alternating turns lose 0 of 8 continuations and forks, against 4 of 4 lost on the
  shipped pool; each continuation reuses about 125,900 cached tokens in 1.6-3.5 s instead of
  re-prefilling from root in about 58 s. Lane gates re-measured on the new configuration: exact
  130,048-token retrieval at 2,203.0 tok/s, 2,048-token decode at 133.03 tok/s wall, the agent
  protocol across a restart, four hot sibling forks at 67.7K and 80.0K templates before and after
  a restart, warm arrival in both orders, and a 4.51 GB checkpoint restored in 3.5-3.7 s.
- The profile declares `runtime_host.minimum_runtime_memory_mib` 28,672 and
  `examples/manual-tunnel/start-ninfer.sh` refuses a host that cannot back the pool, naming the
  `.wslconfig` remedy. This is a new host requirement: the pool is pinned memory, and the same
  configuration in a 24 GiB WSL utility VM is OOM-killed mid-request (container exit 137). A host
  that cannot give the container 28 GiB runs `v0.6.10`.

### Measured

- **Both 8-bit KV dtypes fix the same reuse loss and are rejected on quality.** Re-scored on one
  runtime against the private role corpus (89 deterministic cases), fp8 and int8 both drop the
  redaction control pass rate from 0.750 to 0.625 and add a secret leak (8 to 9); fp8 loses 2.1
  points of required fact recall, int8 loses 1.7 and adds unsupported claims (0.225 to 0.247) and
  critical misses (10 to 12). Throughput is within noise. fp8 holds two long sessions even in the
  shipped 8 GiB pool and halves device KV (5.91 GiB of runtime against 10.12 GiB), so it stays the
  lever to revisit if an artifact closes the grounding gap.
- **Two long sessions are a durability boundary, not only a latency one.** On the shipped RTX 4090
  native lane (INT8 KV, 4 GiB pool) two 126K sessions lose every continuation to a 90 s
  re-prefill, the server refuses every automatic checkpoint while both are live
  (`program refused continuation export`), and its managed stop saved one session and lost the
  other. On the v0.7.0 RTX 5090 configuration both sessions checkpoint and a graceful stop saves
  both, but after a restart one of the two is declined
  (`the engine did not accept the checkpointed continuation`) and re-prefills from its transcript.
  Sessions below the ceiling are unaffected. The RTX 4090 pool change and the restore-admission
  work are follow-ups, not part of this release.

## [0.6.10] - 2026-09-16

No component, model, client, or serving configuration changed. Both RTX 5090 documented routes
were re-run against the unchanged published image: host 2/2 blocks and macOS 10/10 blocks
([composed receipt](releases/v0.6.10/acceptance/composed-external-installation.json),
[routes](releases/v0.6.10/acceptance/documented-routes.json)).

### Fixed

- `examples/manual-tunnel/start-ninfer.sh` proves the route's bind mounts inside a throwaway
  container before loading the 18 GB artifact: the model byte count seen inside the container
  must match the host's, the key file must be non-empty, and the store must be a directory.
  Docker Desktop stages a container's bind mounts once, at creation, from the filesystem those
  paths live on; after that filesystem's WSL distro restarts, a container created against the
  old staging either refuses to start (`not a directory`, recorded as exit 127 with
  `RestartCount 0`) or starts with empty mounts, whereupon the server rejects its own empty
  `--api-key`, prints usage, and exits 1. The launcher now refuses with what the probe container
  saw instead of leaving either shape to an operator
  ([EXP-040](docs/measurements/2026-09-16-lane-reboot-survivability.json)).

### Documentation

- Name both post-reboot failure signatures in the troubleshooting guide, including the quiet one
  where the container runs with empty mounts, and state that recovery on this route is
  recreation (`stop-ninfer.sh` then `start-ninfer.sh`) rather than `docker start`; the durable
  store makes that a continuation. The quickstart now says the container route does not return by
  itself after a machine reboot and links that entry.
- Correct the README, decision guide, architecture, and website: checkpoint export/import,
  host-to-host transport, and NAS replication are implemented, not future-only. Link the
  existing receipts and distinguish replica storage from runtime restore, which remains
  binary/model/profile/credential-bound; no cross-GPU or second-inference-host resume claim.
- Refresh website release status and current benchmark scopes for v0.6.9, retaining the
  historical measurements under their original versions. Credit the NInfer engine and GPU
  ports separately from the durable-state work and OMP agent layer.

### Measured

- **EXP-040 - a host reboot no longer takes the owner appliance's lane down, and the native
  lane's documented recovery is receipted.** The RTX 5090 appliance lane was exited for 26 h
  51 min from 2026-09-15 because nothing starts the WSL distro holding its bind sources at boot,
  and the five-minute supervisor written after the same class in 2026-09-09 retried
  `docker start` throughout while logging an empty reason (it joined stdout; docker writes
  failures to stderr) and exiting 30 where nothing watched. Four consecutive authorised reboots
  after the appliance-side fix recovered the lane unattended in 282 s, 646 s, 442 s, and 158 s;
  the second and third exposed a restart limiter that carried across a reboot and a supervisor
  that refused instead of waiting for its substrate, both fixed before the fourth. On the RTX
  4090 native lane a real reboot confirmed the documented claim: the lane does not return by
  itself (correct for that route), `Control-Release.ps1 -Action Start` had it serving 114 s
  later, and the session checkpointed before the reboot resumed with its planted canary exact.
  Appliance supervision lives in the private appliance repository; no release component, model,
  or serving configuration changed.

## [0.6.9] - 2026-09-13

Both mainline runtime components advance to reviewed source
`696e78c7b4e3ac28ffcffafc73acc1496e65ef03`: RTX 5090
`v0.6.5-qwen38-5090-beta.1` (image `5e3e1558…`) and RTX 4090 native
`v0.6.3-qwen38-4090-beta.1`. Both components are published. The model, OMP client, RTX 3090
component, and serving settings are unchanged. The RTX 5090 public deployment remains
`qwen38-5090-v0.6.3` / configuration `622ab621`; its lifecycle qualification uses the unchanged
`qwen38-5090-v0.6.2` / `5eb8a557` candidate profile. Published-component acceptance passed:
RTX 5090 host 2/2 and macOS 10/10 blocks; RTX 4090 public-URL already-installed path
([composed receipt](releases/v0.6.9/acceptance/composed-external-installation.json)).

### Fixed

- Independently ported the semantics of upstream Qwen tool-parser fixes `3b50962b` and
  `0c5d570c`: supported scalar unions, case-insensitive booleans, precise numeric lexemes,
  mathematically integral values, duplicate parameters, and balanced embedded markup. This is
  not a wholesale serve-adapter rebase; custom raw input, history, opaque IDs, and stream
  ownership remain intact.
- Review remediation prevents repeated rescanning of malformed regions and replaces recursive
  union traversal with bounded-work traversal. Bytewise regressions and an 8,192-deep union
  case pass on the frozen source.

### Measured

- RTX 5090 lifecycle candidate: exact 130,048-token retrieval at 2,193.3 tok/s; 2,048-token
  decode at 134.87 tok/s wall; fanout 4/4 hot at each of 57K and 67K tokens (medians
  1.401 / 1.520 s), warm arrival hot in both orders; exact 5.201 GB restores in
  4.155 / 3.886 s; payload tamper refused; live sibling continuation HTTP 200 and deleted
  continuation HTTP 404 before and after restart
  ([receipt](releases/v0.6.9/qualification/rtx5090.json)).
- RTX 4090 native: 15/15 qualification phases; exact 130,048-token retrieval in 91.2377 s;
  C1 decode 153.464 tok/s at 87.58865% MTP acceptance; explicitly saved and never-published
  sessions restored across managed stop/flush; rollback with the `68a0722f` predecessor
  graceful in both directions ([receipt](releases/v0.6.9/qualification/rtx4090.json)).
- Appliance focused suites 13/13; Windows parser/wire suites 4/4; Blackwell CI 95 passed,
  7 skipped, 0 failed out of 102 registered. These are not public-route acceptance results.
- RTX 4090 public-URL installer acceptance passed on the already-installed path: exact bytes
  accepted, no lifecycle pointer change or runtime start requested; authenticated status 200,
  anonymous status 401, completion marker accepted, stopped state and 450 W restored
  ([receipt](releases/v0.6.9/acceptance/rtx4090-public-install.json)). This is not a fresh-install
  observation. The published RTX 5090 image was pulled with an empty Docker configuration and
  its binary hash matched `b8a0a2c3`. The documented public profile separately measured exact
  130,048-token retrieval at 2,153.6 tok/s and decode at 133.76 tok/s wall; host 2/2 and
  macOS 10/10 blocks passed, including image input, restart continuation, and fail-closed.

## [0.6.8] - 2026-09-13

Both mainline runtime components advance to source `68a0722f`: the RTX 5090 component to
`v0.6.4-qwen38-5090-beta.1` (image `d346174a…`) and the RTX 4090 native component to
`v0.6.2-qwen38-4090-beta.1`. The 5090 deployment profile and configuration, the RTX 3090
component, and the OMP client are unchanged from v0.6.7. Composed external-installation
acceptance ran on 2026-09-13 from the published URLs and image
([receipt](releases/v0.6.8/acceptance/composed-external-installation.json)).

### Fixed

- Continuing a fork while its sibling is still alive answered HTTP 500 (`sequence StateImage
  entitlement is inconsistent`) on every release since v0.6.2, unqualified because the
  agent-protocol gate deleted one sibling before continuing the other
  ([ninfer#43](https://github.com/alphastorm/ninfer/issues/43)). Found by the multi-session
  pressure probe, reduced to a 40-second deterministic reproduction
  (`scripts/sibling_continue_probe.py`), fixed at source: a sequence's entitlement is charged for
  the device slots it alone owns. Green across six fork shapes; the gate now continues a live
  sibling and records `live_sibling_continuation_status` (EXP-036).
- The BF16 GDN gating launcher partitions a cooperative grid the device cannot keep resident over
  disjoint token-tile intervals instead of falling through to a narrower split, and the fused
  fallback and residency budget stay inside the capacity contract (the two P2 findings of the
  candidate's independent review). Exact within 1.5e-6 relative-L2 of the double-precision
  reference on sm_89, sm_120a and the RunPod small-SM class.

### Changed

- The RTX 4090 native lane takes the upstream-2026-09 backport (18 commits) that v0.6.7 shipped
  on the 5090, byte-identical on the lane's fixed C1 fixture. Its published C1 number moves to
  153.4 tok/s at 87.6% MTP3 acceptance (from 159.1 at 93.0%) with the
  launcher partition's summation order; bisected on the lane host, exact on the 4090 itself,
  byte-identical on five diverse prompts, and the fixture (28,000 characters of one repeated
  sentence) swings 52-87% on the same binary with a 1% change in its own length (EXP-037,
  `docs/measurements/2026-09-13-rtx4090-c1-fixture-sensitivity.json`).
- RTX 5090 gates on the candidate: 130,048-token retrieval exact at 2,178.8 tok/s, decode
  134.80 tok/s wall, 5.2 GB restore in 3.85/3.65 s, fanout 4/4 hot after a verified restart at 57K
  and 67K, warm arrival both orders, tampered restore refused; 2,177.7 tok/s again on the
  published image through the documented tunnel, macOS client route 10 of 10.
- `scripts/compose_native_qualification.py` composes a native lane's release receipt from the
  orchestrator window's own artifacts (it reproduces the shipped v0.6.1 receipt byte-for-byte)
  instead of the hand composition every native cut used until now.

## [0.6.7] - 2026-09-13

The RTX 5090 runtime component advances to `v0.6.3-qwen38-5090-beta.1` (source `8818b88b`,
image `fc244576`): the mainline runtime plus a selective backport of 18 upstream Neroued/ninfer
commits and one downstream adaptation ([ledger](docs/measurements/2026-09-12-upstream-backport-ledger.json)).
Deployment profile `qwen38-5090-v0.6.3`, configuration `622ab621`, the native components and the
OMP client are unchanged. Lane qualification on 2026-09-13
([receipt](releases/v0.6.7/qualification/rtx5090.json)); route acceptance against the published image
on 2026-09-13 ([receipt](releases/v0.6.7/acceptance/composed-external-installation.json)).

### Changed

- RTX 5090 runtime: MoE prefill and decode kernel work, GDN prefill convolution into q/k/v, fp8
  w8a16 vocabulary GEMM, sparse-MoE gather lifetimes and S2 CTA-per-token, GDN record snapshot bits,
  host uploads completed before returning, ASCII NFC skip and a flat BPE merge table, cpp-httplib
  0.54.1 with the serve layer following its disconnect (`is_connection_closed`) and lifetime
  (`Response::user_data`) APIs. Every applied commit carries `cherry-pick -x` provenance.
- `docs/QUICKSTART.md`: both model download blocks survive a rerun with a complete file (curl 8.5
  turns the CDN's HTTP 416 into exit 22); the byte count and checksum decide.
- `scripts/upstream_watch.py` records its manifest repo-relative; `upstream-watch.json` records the
  5090 fork point as the mainline base `6e8b2e2a` (the retired container mirror point had made the
  delta read 175 instead of 158).
- `scripts/verify_release.py` allowlists the `v0.6.3-qwen38-5090-beta.N` runtime tag.

### Measured

- Lane: 130,048-token retrieval exact at 2,174.5 tok/s, decode 134.15 tok/s wall, 5.2 GB restore in
  3.89/3.86 s, fanout 4/4 hot at 57K and 67K after a verified restart, warm arrival both orders,
  tampered restore refused, agent protocol 200/404/404 - all within noise of v0.6.2. Full 102-test
  suite on an ephemeral sm_120a GPU. Documented route on the published image: exact at 2,172.5 tok/s;
  macOS client route 10/10.
- Review: one full council on the frozen subject; supplement zero findings; strong critic missing
  (harness selector no longer resolves on OMP 18.1.18); closed on disposition with no P0/P1.

## [0.6.6] - 2026-09-12

No component changed. The config every documented client route installs now turns the pinned
client's startup update check off, so it no longer advertises an out-of-channel `omp update`
([#18](https://github.com/alphastorm/omp-ninfer/issues/18)); every client-installing route was
re-run from its own blocks and reads the setting back from the client it installed (EXP-034,
[receipt](docs/measurements/2026-09-12-client-channel-contract-qualification.json)). Component
bytes, profiles and configuration are v0.6.3's and carry by hash; route acceptance ran on
2026-09-12 ([receipt](releases/v0.6.6/acceptance/composed-external-installation.json)).

### Changed

- `examples/manual-tunnel/fail-closed.yml` adds `startup: checkUpdate: false`. The pinned
  18.0.9 client reads the setting only in nested form - a dotted `startup.checkUpdate:` key
  leaves the default on - and a test refuses any other shape. `docs/QUICKSTART.md` now states
  what the config does and how to upgrade instead of pointing at an open issue.
- `scripts/hosts/run-documented-route.sh`: a run refuses to start its tunnel on a port it does
  not own and releases its forward on the error path. A forward left by an earlier failed run
  answered the readiness probe, so the tunnel step passed without binding anything and the stale
  listener made the fail-closed check report a live route.

### Fixed

- Evidence correction: v0.6.5's receipts claimed the appliance's production lane had been
  restored after that window. It had been stopped for a route window with its restart policy
  pinned off and stayed down through the v0.6.5 cut; the claim had been read off the route's own
  container. No v0.6.5 measurement is affected. Production was restored on 2026-09-12 and the
  correction is recorded in this release's qualification receipt.

### Measured

- EXP-034: macOS client route 10/10 from an isolated HOME (including a server restart with the
  session continued), native Windows client route 5/5, RTX 4090 native route 7/7; the installed
  client reports `startup.checkUpdate` false on all three hosts and every fail-closed check
  still fails its outage request.

## [0.6.5] - 2026-09-12

No component changed. The quickstart's primary route - macOS client, Windows 11 + Docker Desktop
inference host - now runs end to end from its own blocks with every outcome decided by the shell,
so every documented route is covered by the runner (EXP-033,
[receipt](docs/measurements/2026-09-12-macos-client-route-qualification.json)). Component bytes,
profiles and configuration are v0.6.3's and carry by hash; route acceptance ran on 2026-09-12
([receipt](releases/v0.6.5/acceptance/composed-external-installation.json)).

### Changed

- `docs/QUICKSTART.md`: the key-copy block used `$HOME` and `2>/dev/null`, which the Windows
  OpenSSH default shell (`cmd.exe`) does not interpret - a reader got an empty key file; the
  restart block ran `sleep` remotely. Both now use forms measured byte-identical on a Linux and a
  Windows destination, and the survival check waits for `/health` through the tunnel. The macOS
  acceptance is non-interactive: `-p` turns that each end in a shell test - tool marker, image
  description, nonce on `--continue`, nonce after the server container is restarted from the Mac,
  and fail-closed with the tunnel stopped.
- `scripts/hosts/run-documented-route.sh`: runs on macOS's system Python; reads the step list up
  front so a block that backgrounds a process cannot end the run early (a partial run had read
  as a pass); keeps the tunnel block open where the prose says "in another terminal" and stops
  the `ssh` it exec'd, not just its wrapper, before the fail-closed block; a run that executed
  fewer steps than the bundle lists fails; records the host OS on macOS.
- `scripts/stage_release.py`: a kept deployment profile is the one the source manifest records,
  not one derived from the source release number (v0.6.4 itself kept v0.6.3's).

### Measured

- EXP-033: the macOS client route passed 10 of 10 steps in 158 s from a Mac with the owner's
  client state moved aside - client install from the public URL, tunnel, key, provider,
  fail-closed configuration, tool, Vision, resume, a server restart from the Mac with the session
  continued (110 s), and fail-closed. Three documentation defects and three runner defects fixed
  at source, each red first.

## [0.6.4] - 2026-09-11

No component changed. Every documented Windows route now runs end to end from its own quickstart
blocks on a stock Windows 11 host, and a Git clone yields the recorded bytes on every platform
(EXP-032, [receipt](docs/measurements/2026-09-11-documented-routes-qualification.json)). Component
bytes, profiles and configuration are v0.6.3's and carry by hash; route acceptance ran on
2026-09-11 ([receipt](releases/v0.6.4/acceptance/composed-external-installation.json)).

### Changed

- `.gitattributes` pins `* -text`: Git for Windows installs with `core.autocrlf=true`, which
  rewrote the hash-chained receipts at checkout and failed `verify_release.py` on every hash of a
  stock clone. The verifier now names that cause first and once.
- `docs/QUICKSTART.md`: every Windows block that invokes a script opens with a process-scope
  `Set-ExecutionPolicy` (Windows' default `Restricted` policy blocked the first `.ps1`); Windows
  blocks call `py -3` (the `python3` name is the Microsoft Store shortcut); the native section
  opens with a clone-and-verify block, generates the key with .NET Framework APIs (the .NET 5
  calls failed in Windows PowerShell), operates the lane as a pasteable sequence, and keeps the
  interactive OMP launch out of the blocks the next section runs in the same process.
- `scripts/documented_route.py` and `scripts/hosts/run-documented-route.{ps1,sh}`: a route's
  blocks are extracted by heading and executed in one shell under the host's real execution
  policy, every block hashed before it runs; tests refuse blocks that would break a paste.

### Measured

- EXP-032: the RTX 4090 native route from an uninstalled host - client install, clone and verify,
  stage and install from public URLs with the 18 GB artifact pulled from Hugging Face, operate,
  provider, acceptance - passed on the first-install and the rerun path; the RTX 5090 container
  route's inference-host half and native Windows client half passed including Vision and the
  fail-closed check. Six documentation defects fixed at source, each red first.

## [0.6.3] - 2026-09-11

The documented RTX 5090 container route mounts a durable session store. Until this release the
published launcher passed no `--session-checkpoint-dir`, so on the route the quickstart tells a
reader to run, `POST /v1/ninfer/checkpoints` answered 404 and a continuation after a container
restart answered `previous_response_not_found` - while the server reported configuration identity
`5eb8a557`, the identity of the checkpointed configuration qualified through the lifecycle tool.
Both native Windows lanes and the maintainer's production already ran with the store enabled. No
component changed: image `a62dd5b8`, binary `6ab904d7`, model and client are v0.6.2's bytes. The
deployment profile advances to `qwen38-5090-v0.6.3` (configuration `622ab621`) because the
configuration does. Route acceptance ran on 2026-09-11
([receipt](releases/v0.6.3/acceptance/composed-external-installation.json)).

### Changed

- `examples/manual-tunnel/start-ninfer.sh` takes `--checkpoint-dir`, prepares it private to the
  invoking user, mounts it at `/checkpoints` under `examples/manual-tunnel/ninfer_io_uring_seccomp.json`
  (pinned by hash, the same profile identity the runtime fork's lifecycle tool pins), and passes
  the session-store arguments. It runs the container as the invoking uid/gid with `--cap-drop ALL`
  and `no-new-privileges`, publishes the container port on the runtime host's `127.0.0.1:18089`
  instead of binding a host network, and probes the GPU inside the pinned image so the host needs
  no `nvidia-smi` on `PATH`.
- Both container profiles record the published endpoint, the store mount, and the seccomp
  identity, claim `process-restart-continuation`, and declare configuration `622ab621`.
- `scripts/verify_release.py` computes the configuration identity a profile launches exactly as
  the lifecycle tool does - pinned by a cross-repository test vector to the appliance's
  `5eb8a557` - and a ready release must record that value for every profile. The launcher refuses
  to start when the computed, declared and recorded identities disagree.
- `docs/TROUBLESHOOTING.md` replaces the `wsl-mirrored-loopback-unavailable` entry: the cause was
  never WSL networking drift, and `wsl --shutdown` never fixed it.

### Measured

- EXP-031: the documented route, run from a clean clone on the owner appliance, saved a session
  explicitly (302 MB in 1.3 s), survived a full container stop with the store owned by the
  operator at mode 700, came back in 25.5 s, and returned the planted marker exactly in 1.17 s
  with 122 cached input tokens; 5.2 GB restored in 3.9 s and 3.7 s across two verified restarts
  with a flipped payload byte refused; exact 130,048-token retrieval at 2,160.6 tok/s and
  2,048-token decode at 131.1 tok/s; the agent-protocol battery across a restart. The same
  sequence on the predecessor configuration answered 404 twice
  ([receipt](docs/measurements/2026-09-11-rtx5090-public-route-qualification.json)).
- Recorded appliance finding, closed by taking a hold instead of racing it: the lane supervisor
  reconciles declared containers every five minutes and started production into the window, which
  OOM-killed the candidate (two 18 GB servers do not fit) and then production in turn. The window
  now takes the supervisor's admin-only maintenance hold for its duration and pins the incumbent's
  restart policy off while it runs.

## [0.6.2] - 2026-09-11

All three lanes now serve from one runtime tree. The RTX 5090 container lane moves off the
branch head it had served from since v0.4.4 onto the mainline runtime at `63f28c95` - the commit
the RTX 4090 lane shipped as v0.6.1 and the RTX 3090 mainline candidate builds from. The runtime
component `v0.6.2-qwen38-5090-beta.1` (server binary `6ab904d7`, archive `05aa9c4b`, image
`a62dd5b8`) carries deployment profile `qwen38-5090-v0.6.2` (configuration `5eb8a557`) with the
v0.4.8 argument set unchanged: BF16 KV, MTP3, prefill chunk 1,024, 131,072-token context, four
device-state slots, 24 host-state slots, eight private continuations. The RTX 4090 component,
the RTX 3090 component, their profiles, and the OMP client are byte-identical to v0.6.1.
Composed external-installation acceptance ran on 2026-09-11 from the published URLs
([receipt](releases/v0.6.2/acceptance/composed-external-installation.json)); the RTX 3090
mainline candidate still ships separately when its host returns.

### Changed

- `scripts/verify_release.py` admits the `v0.6.2` RTX 5090 runtime tag.
- The documented public install path for the native Windows lanes is completable as written:
  the RTX 4090/3090 section derives every installer input from the ready manifest (including the
  mandatory state root and the model artifact it passes), names each lane's request model id and
  `18082` endpoint, ships `examples/windows-native/models.fragment.yml`, documents
  `Control-Release.ps1` `Status`/`Start`/`Stop`/`Restart` including after a reboot, and runs its
  own text/tool, stateful and fail-closed acceptance. The macOS route states the `PATH` the
  installer uses and names an image file that exists; troubleshooting points at the lane's own
  status and last-stop record.

### Measured

- EXP-030: the RTX 5090 mainline candidate passes 7/7 of the lane's gates on the owner
  appliance under the unchanged argument set - exact 130,048-token retrieval, 8/8 sibling forks
  on the shared anchor at 57.9K and 67.7K templates before and after a verified restart, warm
  arrival hot in both orders, and a 5.2 GB session restored in 3.6-4.0 s with a flipped payload
  byte refused ([receipt](docs/measurements/2026-09-10-rtx5090-v062-qualification.json)). Every
  gate a published artifact can answer was then re-run against the image pulled anonymously by
  digest: 2,169.9 tok/s prefill, 132.53 tok/s decode, the agent protocol across a restart
  ([receipt](docs/measurements/2026-09-11-rtx5090-v062-public-image-gates.json)). Both are
  within run-to-run noise of v0.5.1 (2,180.3 / 133.13 / 3.8-4.4 s), which is what the shared
  tree had to produce.
- The full 102-test suite ran on an ephemeral RunPod RTX PRO 4000 (Blackwell, `sm_120a`) before
  the appliance window, so the owner rig's GPU time went only to gates.
- The runtime fork's GDN gating workspace query sizes what the current device resolves
  ([ninfer#42](https://github.com/alphastorm/ninfer/issues/42), fixed in `29caaf34`): it had
  sized every route at its preferred cooperative split, so a device whose resident-CTA budget
  makes that split fall through executed with a smaller high-water than the query declared -
  over-provisioned, never unsafe, and latent on the three shipped SM counts. Proven on the
  pod class that found it: 101/102 at `63f28c95`, 102/102 at `29caaf34`
  ([receipt](docs/measurements/2026-09-11-runpod-ci-small-sm-29caaf34.json)); RTX 4090
  103/103 unchanged. Not in this release's bytes; it rides the next runtime cut.
- `scripts/run_runpod_ci.py` probes the built server's identity only when the requested target
  set built it, so a focused kernel-test run no longer records a passing suite as a failed run.
- Recorded appliance fault, closed with an invariant: `docker start` brought the production
  container up with no network attachment at all - `docker ps` read `Up` and the server logged
  that it was listening, while `NetworkSettings.Networks` was empty and no host port was
  published - and neither `restart` nor `stop`+`start` repaired it. The container was recreated
  from its own promote path with no state loss (all lane state is in bind mounts). The
  acceptance window's restore path now asserts a published port and recreates the incumbent
  when a start comes up network-less: a container-state check is not a restore check.

## [0.6.1] - 2026-09-10

A managed stop of the RTX 4090 native Windows lane now saves every live session. The runtime
component `v0.6.1-qwen38-4090-beta.1` (runtime fork `63f28c95`) replaces v0.6.0's on the
same engine and profile: the manager signals the server through a per-launch named kernel
event instead of terminating it, the server saves every live session and reports what it
saved, and the controller records a stop that lost state instead of calling it graceful.
Deployment profile `qwen38-4090-native-v0.6.1-beta.1` keeps the v0.6.0 tuning. The RTX 5090
runtime, its deployment profile, the RTX 3090 component, and the OMP client are unchanged from
v0.6.0. Composed external-installation acceptance ran on 2026-09-10 from the published URLs
([receipt](releases/v0.6.1/acceptance/composed-external-installation.json)).

### Changed

- `packaging/windows/Control-Release.ps1` and `Install-Release.ps1` (in the component): a
  release record declares `managed_stop` and `graceful_stop_timeout_seconds`, the controller
  passes the channel's flags only to a release that declares them, every mutating action runs
  under an action lock, the GPU-owner lease has exactly one restorer per stop, and no lifecycle
  decision reads a child exit code - which a parent with redirected streams cannot observe on
  this host. `last-stop.json` records every stop; the lifecycle status exposes it as
  `last_stop`.
- `scripts/render_compatibility.py` admits the `0.6.1` native component tag and package shapes.

### Measured

- EXP-028: the open EXP-027 finding is fixed at source and proven red-to-green on the RTX 4090
  host. A managed stop on Windows terminated the server, so the shutdown flush that
  saves every live session after the listener closes was unreachable and a session below the
  32,768-token automatic gate that was never saved explicitly did not survive a deliberate stop.
  The manager now mints one manual-reset kernel event per launch, passes it as `--stop-event`,
  and signals it to stop: the server creates the object itself - refusing a name that already
  exists, with a DACL admitting only `SYSTEM` and `Administrators` - closes its listener, lets
  in-flight requests finish, then saves every live session. `HttpServer::stop()` is sticky and
  the watcher re-asserts it, so a stop that lands while the model is still loading returns from
  `listen()` without ever serving instead of being lost to cpp-httplib's pre-listen no-op.
  Measured with a 43-token session and the gate at its default: signalled, the candidate exits in
  **0.74 s** logging `shutdown: saved 1 of 1 live sessions`, publishes a 10-file generation, and
  after a restart the continuation quotes the marker exactly with 43 cached input tokens; the
  shipped v0.6.0 binary, stopped the way the managed stop stops it today, publishes nothing and
  its continuation returns 404. The shipped binary also refuses `--stop-event` (`unknown
  argument`), so the channel is a per-release capability: the installer copies
  `lifecycle.managed_stop` into the release record and the shared controller - always the newest
  installed one, including after a rollback - passes the flag only to a release that declares it,
  signals it, waits out the declared bound, and only then stops the task and forces the process,
  recording the outcome in `last-stop.json` (`last_stop` in the lifecycle status). Both lanes'
  specifications advance to `0.6.1-beta.1` and remain uncut; the lane qualification's restart
  phase now proves the unsaved session survives a managed restart and its rollback phase proves
  each direction's stop mode against what that release declares
  ([receipt](docs/measurements/2026-09-10-native-managed-stop-flush.json)).
- EXP-029: the graceful-stop candidate passes the RTX 4090 lane's own lifecycle qualification
  and two rounds of independent focused review. Final candidate runtime fork
  `63f28c95`: 15/15 phases, 103/103 registered tests. The two new assertions hold on the managed
  path: the restart phase's second session - 45 tokens, never published, `missing` before the
  stop - comes back `available` quoting its marker with 45 cached input tokens after a
  **graceful** managed stop, and the rollback phase records each direction's stop against what
  that release declares. Unchanged where it should be: exact 130,048-token retrieval in
  **91.4 s**, C1 **2,104.9 tok/s** prefill and **159.1 tok/s** decode at 93.0% MTP acceptance
  and 22,814 MiB peak, the 15-check protocol at both pool sizes, the state-security set, the
  OMP golden run exact, the host restored to 450 W with the incumbent untouched. Getting there
  took seven candidate windows in one day: the lane found six defects in the lifecycle handoff
  that no unit test or foreground probe could see, because they live in the moment a
  gracefully exiting wrapper hands the lifecycle back to the controller - a moment that never
  existed while stops were terminations - and the reviewer confirmed eight more. Three classes
  recurred and were closed with executable invariants rather than patched per instance: two
  owners converging on one piece of shared state (the GPU-owner lease has one restorer per
  stop, decided by an action lock), deciding on a value the host did not expose (`Start-Process
  -PassThru` with redirected streams reads `ExitCode` as `$null` for a child that exited 0, so
  the server now writes a `--shutdown-report` bound to its launch and no shared script compares
  an exit code), and an argument an older binary refuses (the set of flags newer than the
  shipped parser is derived from git and required inside the capability gate). The worst
  finding was the reviewer's: the installer rebuilt every existing release record from a field
  list that predates the channel, so installing the *next* release would have silently turned
  every 0.6.1 incumbent's stop back into a termination - proven on the host, where every record
  installed before the fix had already lost its capability
  ([receipt](docs/measurements/2026-09-10-rtx4090-graceful-stop-qualification.json)).

## [0.6.0] - 2026-09-10

The RTX 4090 native Windows lane moves onto the mainline runtime. The runtime component
`v0.6.0-qwen38-4090-beta.1` (runtime fork `075d442e`, built for Ada with the Windows platform
code) replaces the divergent `v0.2.x` lane branch and brings the whole context-cache
architecture the RTX 5090 container ships; deployment profile `qwen38-4090-native-v0.6.0-beta.1`
(INT8 KV, MTP3, prefill chunk 2,048, 131,072-token context, two device-state slots, 24
host-state slots, 4 GiB Host KV). The RTX 5090 runtime, its deployment profile, the RTX 3090
component, and the OMP client are unchanged from v0.5.1. Composed external-installation
acceptance ran on 2026-09-10 from the published URLs
([receipt](releases/v0.6.0/acceptance/composed-external-installation.json)); the RTX 3090
mainline candidate ships separately when its host returns.

### Measured

- EXP-025: the two native Windows lanes serve the mainline runtime. Native-lane convergence
  stages 2 and 3 on the runtime fork's `port/native-lanes-on-mainline` (`6fd9e135`): the
  Windows platform code (D3D12 residency arena, DirectStorage read queue) and the host tree
  build with MSVC 19.44 for Ada and Ampere, and every registered test suite runs on the
  hardware, 100/100 on both builds (the five real-artifact suites and the external-tokenizer
  frontend suite skip). Five defects showed only on the hardware and were fixed at source:
  cooperative GDN gating grids sized for the RTX 5090's 170 SMs (fatal on the first prompt
  longer than one tile on 128), an INT8 prompt-attention CTA that spilled 200 B/thread under
  Ada's register cap (390 tok/s at 42K; 130K did not finish), a serialising DirectStorage read
  queue that failed every streamed restore, that refusal going unlogged, and an unbounded
  residency query. Same 130,048-token fixture, gate script, host, and day as the installed
  releases: RTX 4090 exact retrieval **86.8 s vs 97.5 s** and 2,048-token decode **103.8 vs
  88.4 tok/s**; RTX 3090 **208.6 vs 219.5 s** and **60.3 vs 52.8 tok/s**. A 67.7K template
  serves four sibling forks in 1.8-2.0 s (4090) / 2.5-2.9 s (3090) before a restart and
  1.8-1.9 s / 2.5-2.6 s after it, all on `private_long_anchor`; warm arrival holds in both
  orders; a 2.9 GB checkpoint restores in 4.2-5.0 s / 16.6-17.1 s and a flipped byte is refused
  and quarantined. RTX 4090 profile: two device-state slots at 131K INT8 - four leave 169 MiB of
  WDDM budget and the driver pages (47 tok/s decode, forks 2.5× slower), one re-prefills the
  first fork. No release changed; each lane's next candidate builds from this branch and is
  requalified through its lifecycle tool
  ([EXP-025 receipts](docs/measurements/) prefixed `2026-09-08-rtx4090-mainline-` and
  `2026-09-08-rtx3090-mainline-`, release baselines
  [4090](docs/measurements/2026-09-08-rtx4090-v0.2-profile-gates.json) ·
  [3090](docs/measurements/2026-09-08-rtx3090-v0.2.5-profile-gates.json)).
- EXP-026: qualifying the mainline native lanes. The release path around the port had never
  run; five blockers were reproduced and fixed on the runtime fork (`4447fe93`): the mainline
  bench had no `--version` arm the package's identity binding requires; `transfer_install`
  relayed the 0.6 GB package through the operator's Mac with `scp -3` (297 of 592 MB in 900 s,
  **0.33 MB/s**, then a timeout) and now moves it host to host as 16-stream ranged HTTP at
  **104.7 MB/s**, SHA-256 verified on both ends; the staging root inherited `BUILTIN\Users`
  write access on the host whose qualification parent did not exist yet, so the installer
  refused to create protected state beneath it; the managed install splatted its arguments
  positionally; and mainline applied `X-NInfer-Session` only on the bodyless Responses routes,
  so the lane probe's identity conflict returned 200 instead of 400. Both lanes now pass
  preflight, build, private-path scan, package, and install and reach the protocol phase. The
  RTX 4090 lane's Host KV pool is halved to 4 GiB (**9.2 GB** pinned, starts) because 24 slots
  with the 8 GiB default is 13.3 GB and failed `cudaMallocHost` on two managed starts, where
  the controller's 18 GB pre-launch read empties the free-and-zero list; both lanes keep 24
  host state slots because at 8 the protocol's post-delete continuation fails in 41 s against
  an open runtime invariant defect. No release changed; the RTX 3090 lane is blocked on its
  host being offline
  ([receipt](docs/measurements/2026-09-09-native-lane-qualification-blockers.json)).
- EXP-027: the RTX 4090 mainline candidate passes its own lifecycle qualification end to end
  (15/15 phases at runtime fork `6912a15c`, then again at `075d442e`). Running the phases past
  `protocol` for the first time exposed two defects, both reproduced before the fix.
  **Admission refused a legitimate request under Host StateImage pressure**: at eight host
  state slots the protocol's post-delete continuation returned HTTP 500, because the guard asked
  `resident_resources(source)` - which reports only what an owner holds *exclusively* - whether
  the planned source still had state, and a long anchor a sibling continuation also references
  measures as zero while being perfectly resident (instrumented: endpoint retired, one anchor
  `HostOnly` with two checkpoint references against one owned). It now asks the question the
  planner asks, and the same 8-slot run passes 15/15 with `reuse=private_long_anchor`
  ([ninfer#37](https://github.com/alphastorm/ninfer/issues/37)). **The restart phase could not
  observe durability**: it seeded a ~40-token session, which is below the 32,768-token
  automatic-checkpoint gate, and a managed stop on Windows terminates the server rather than
  signalling it, so nothing was ever published and the continuation returned 404. The phase now
  publishes through `POST /v1/ninfer/checkpoints`, verifies the generation, and requires the
  post-restart continuation to quote the marker with a nonzero cached-token count; it also
  drops five regression fields its receipt had asserted without exercising them. Measured on
  the candidate: exact 130,048-token retrieval in **91.6 s**, C1 **2,101.6 tok/s** prefill and
  **159.0 tok/s** decode at 93.0% MTP acceptance and 22,814 MiB peak, bidirectional rollback,
  state-security gates, the OMP golden run exact, and a 310 MB checkpoint restored across a
  managed restart. Running the registered suite with the artifact exported - which EXP-025's
  "every suite passes" had not - found a third defect: after `wait()` returned for every one
  of eight staggered rows, `runtime_stats()` still counted one as `running`/`terminal_pending`.
  Not a leaked slot: the engine delivered a result and woke its waiter before it released the
  lane and republished, so the consumer read the previous snapshot. Completion is now split
  into finalize and deliver and a lane is retired finalize → release → publish → deliver
  ([ninfer#38](https://github.com/alphastorm/ninfer/issues/38)). Red at the port base
  `f3dacba8` and at `4447fe93` on real rebuilds, green at `075d442e`, and the full sm_89 set
  passes 101/101 with the artifact. An earlier three-commit A/B is retracted on the issue: its
  nested `powershell -Command` line was split on `&` by cmd and never rebuilt. One finding
  stays open and unfixed: a managed stop does not flush unsaved sessions on either native lane
  ([receipt](docs/measurements/2026-09-10-rtx4090-native-lane-qualification.json)).

### Changed

- `scripts/fleet_probe.py`, `scripts/warm_arrival_probe.py`, `scripts/restore_probe.py`
  (receipt schema 3): every receipt carries the lane's self-reported identity - deployment
  profile, model and artifact digests, binary, upstream and patch-stack commits, build profile,
  resolved configuration digest - captured before the first request; a verified restart now
  also requires the lane to come back as the same identity, so a launcher that swaps binaries or
  arguments mid-probe fails the probe instead of mixing subjects. The fanout summary adds
  `hot_fork_max_s` and `warm_start_fork_max_s`: one fork re-prefilling from root hid behind the
  median.
- `scripts/bind_native_variant.py`: a native lane's manifest row is now derived from the two
  files its packager already produces - the closed outer `SHA256SUMS` and
  `package-build-receipt.json` - plus the component tag. It refuses a set that does not carry
  every bound asset, a package hash the receipt disputes, a receipt that does not hash to its
  own entry, and a receipt from another lane, and it checks the distribution set into the
  release tree where the verifier expects it. Transcribing those fifteen hashes and URLs by
  hand is the drift class v0.5.1 had to correct with a whole release.

## [0.5.1] - 2026-09-08

Warm arrival across a restart on the RTX 5090. The runtime component
`v0.5.1-qwen38-5090-beta.1` ships the three context-cache fixes and the streamed, SHA-extension
restore path measured below; deployment profile `qwen38-5090-v0.5.1` keeps the `qwen38-5090-v0.4.8`
context-cache arguments. The RTX 4090 and RTX 3090 components and the OMP client are unchanged
from v0.5.0. Composed external-installation acceptance reran on 2026-09-08 from the published
URLs ([receipt](releases/v0.5.1/acceptance/composed-external-installation.json)).

### Changed

- The compatibility authority, root profiles, and qualification summary are now derived from
  the release manifest and verified against it. Through v0.5.0 the authority's native variant
  rows still named the v0.2.2/v0.2.0 components with a 65,536-token RTX 3090 ceiling, the
  profiles' `--binary-sha256`/`--config-sha256` launch arguments named the v0.4.3 runtime, the
  qualification summary's runtime identity carried a stale upstream commit and source-archive
  hash, and the RTX 5090 receipt URLs pinned a commit that never contained them; the manifests
  were exact, the copies had drifted. `scripts/verify_release.py` refuses a ready release whose
  derived records disagree with its manifest and, with `--check-pins` (run by the pin dance and
  by CI on release tags), a pinned evidence URL that does not serve its recorded bytes.
  `scripts/rebind_release.py` derives every copy from the manifest, owns the cut
  (`--stage lane`), and `scripts/stage_release.py` stages a draft without touching the root
  authority.
- `scripts/render_compatibility.py` validates native variant tags and package names by lane
  shape instead of a frozen v0.2.x value, which is what had kept the authority's rows stale.

### Measured

- `scripts/verify_release.py` now applies the private-marker rule to `docs/measurements/*.json`,
  and the four dated receipts that carried a hostname or a Windows user path were rewritten to
  lane-relative identities. Receipts are published next to the docs that cite them, so they were
  the one public surface the content-safety check did not cover.
- EXP-020: the fleet NAS is the replication target for the two lanes on its LAN (115.8 MB/s write
  from the RTX 4090 host against 6.4 MB/s for the same appliance across the internet), with one
  published generation replicated and verified in place per lane
  ([receipt](docs/measurements/2026-09-07-nas-replication-sf-lanes.json)).
- EXP-021: a restored session's first sibling fork still re-prefills the template on the shipped
  RTX 5090 profile (22.1 s, reuse path `root`), so durable resume is a net loss for the fanout
  pattern. Two fixes on the runtime fork's `feat/warm-arrival` branch put the long anchor back
  into post-fanout checkpoints and repair a latent entitlement-accounting bug that returned
  HTTP 500 on any resume of an anchor-carrying session. Not released, not qualified; the
  resume-first ordering and the hash-bound 24 s restore remain open
  ([receipt](docs/measurements/2026-09-07-warm-arrival-rtx5090.json)).
- EXP-022: the remaining resume-first re-prefill was anchor replacement, not admission. Every
  Responses request captures two private anchors into a per-continuation set of two, and the
  victim rule (lowest frontier) evicted the template anchor every sibling fork reuses on the
  first continuing turn. The runtime fork's replacement rule now evicts the anchor whose loss
  costs the least re-prefill; across a restart the candidate serves resume then two forks in
  4.2 / 2.9 / 1.3 s, every fork on `private_long_anchor`
  ([receipt](docs/measurements/2026-09-08-warm-arrival-rtx5090-candidate.json)).
- EXP-023: a 5.2 GB checkpoint restores in 3.8 s on the candidate (was 24-27 s): payloads are
  hashed once, as the engine streams them, with the x86 SHA extensions (2.66 vs 0.33 GB/s), and
  the io_uring reads run eight deep overlapped with the hash. A flipped payload byte is still
  refused (404) and quarantined
  ([receipt](docs/measurements/2026-09-08-restore-probe-rtx5090-candidate.json)).
- EXP-024: the RTX 5090 component `v0.5.1-qwen38-5090-beta.1` (`ninfer` `d956e6d6`,
  appliance-local binary `71edc2f6`, archive `c0189387...` with its SBOM, source archive
  `4359c814...`, runtime image `12ef2d9e...` whose binaries measure byte-identical) passed the
  lane's profile gates on the unchanged v0.4.8 arguments, started through the lifecycle tool
  from the published image under deployment profile `qwen38-5090-v0.5.1` (configuration
  `efacac23...`): 130,048-token exact retrieval at 2,180 tok/s, 138.2 decode tok/s, agent
  protocol with no resurrection, 24/24 fanout forks on the anchor path across 57.9K / 67.7K /
  80.0K templates in-process and after a restart, warm arrival in both orders, restore in
  3.3-4.0 s
  ([qualification](docs/measurements/2026-09-08-rtx5090-v051-qualification.json) ·
  [gates](docs/measurements/2026-09-08-rtx5090-v051-profile-gates.json) ·
  [57.9K](docs/measurements/2026-09-08-rtx5090-v051-fanout-57k.json) ·
  [67.7K](docs/measurements/2026-09-08-rtx5090-v051-fanout-67k.json) ·
  [80.0K](docs/measurements/2026-09-08-rtx5090-v051-fanout-80k.json)).
- Native-lane convergence, stage 1: the runtime fork's `port/native-lanes-on-mainline` branch
  builds the mainline runtime - context cache, warm arrival, and the restore path included - for
  Ada (`CMAKE_CUDA_ARCHITECTURES=89`) with the 4090 lane's architecture guards applied to
  mainline (NVFP4 W4A4 excluded behind rejecting launchers, Ada's FP8 MMA spelling, W8 split-K
  schedules that fit 48 KiB of static shared memory, ordinary launches in place of programmatic
  dependent launch), and still builds for sm_120a. Porting the cache into the two divergent
  native branches (~8K lines each) was rejected in favour of building both native lanes from
  mainline; Ampere (sm_86) follows once its FP8 A8 and FP8-KV attention kernels are excluded,
  and the Windows platform code (D3D12 residency arena, DirectStorage read queue, MSVC build)
  is the next stage.

### Added

- `scripts/hosts/pscp.py`: parallel file transfer for high-latency links, either as N ranged
  reads over independent ssh connections (compression forced off, file-backed handles, SHA-256
  verified on both ends) or as bearer-token ranged HTTP over the tailnet for the Windows-to-
  Windows case, where ssh cannot carry bulk at all. EXP-019: the EXP-018 hop's 1.8–3.5 MB/s was
  a transpacific workstation path plus single-stream ssh, not the fleet's; a 1.13 GB checkpoint
  now leaves the RTX 5090 at 11.5 MB/s, returns at 56.3 MB/s, imports in 2.6 s and restores with
  its planted keys intact ([round trip](docs/measurements/2026-09-06-cross-site-replication-rtx5090.json) ·
  [transfer paths](docs/measurements/2026-09-06-replica-transfer-paths.json)).
- `scripts/warm_arrival_probe.py`: template → fork → save → restart → {resume, fork} in both
  orders, recording the lane's server-reported reuse decision for every request and the planted
  ledger keys for every resume, so a re-prefill is a reuse path rather than a timing guess.
- `scripts/restore_probe.py --tamper-cmd` (with `--stop-cmd`/`--start-cmd`): a third round
  that flips one byte in an engine payload while the lane is down and requires the resume to be
  refused and the generation quarantined.

## [0.5.0] - 2026-09-05

### Added

- `scripts/checkpoint_sync.py` (roadmap v0.5 §1): replicate a checkpoint root's published
  session generations to shared storage and import them back before a restore. Only the current
  generation of each session is copied, only after every manifest-listed file verifies by size
  and SHA-256; the copy stages outside every directory the runtime scans, publishes with one
  rename, and replaces `current` last; generations without an origin tag are refused unless
  `--allow-unauthenticated`. `scripts/sync_probe.py` proves the contract against a live lane
  (export, carry off the machine, destroy the local copy, carry back, import, restart, exact
  retrieval of planted keys; payload tamper refused by the tool; manifest forgery quarantined by
  the runtime). Receipts for all three lanes (EXP-018).
- Manifest origin authentication on both native Windows lanes
  ([ninfer#32](https://github.com/alphastorm/ninfer/issues/32), ported from the RTX 5090
  container): every save publishes `manifest.mac`, loads and status verify origin before
  trusting manifest content, and `--session-checkpoint-require-origin-auth` is the strict,
  reversible import posture. RTX 4090 v0.2.3 (head `e186e04e`) and RTX 3090 v0.2.5-beta.1
  requalified on their own rigs; the `docs/QUICKSTART.md` "Replicating sessions off the machine"
  section documents the operator path.

## [0.4.9] - 2026-09-05

### Added

- `scripts/restore_probe.py` plants three run-specific ledger keys in its template and requires
  every restored continuation to quote them (with one in-process control), so a restore that
  scatters the wrong bytes cannot pass on timing alone (receipt schema 2, exit 1 on a failed
  restored retrieval, exit 2 when the control is inconclusive).

### Fixed

- Native-lane checkpoint restore path (EXP-017, [ninfer#36](https://github.com/alphastorm/ninfer/issues/36); shipped in `v0.4.9` with requalified components `v0.2.2-qwen38-4090-durable.1` and `v0.2.4-qwen38-3090-beta.1`):
  the reader issued one DirectStorage request per KV page segment; it now reads one staging
  window per request and submits a reader call as one bounded batch. Same sessions as EXP-014:
  RTX 4090 146.6 s / 133.4 s → 5.6 s / 5.6 s (1.13 GB), RTX 3090 91.8 s / 92.2 s → 10.8 s / 10.7 s
  (1.68 GB), retrievals exact throughout. Lane commits `d22ce3fd` (RTX 4090) and `3756db6e`
  (RTX 3090); both lanes requalified their exact release binaries on 2026-09-05 (RTX 4090
  post-restart continuation of the 102,060-token session 225.6 s -> 9.5 s inside the gate);
  no published profile changed.
- `examples/fleet/`: one OMP configuration spanning the three qualified lanes with explicit
  roles (`local-main` RTX 5090, `local-heavy` RTX 4090, `local-scout` RTX 3090), a fail-closed
  three-lane tunnel opener, and two role agents. `scripts/fleet_dispatch.py` dispatches the frozen
  agent corpus as 14 independent jobs across lanes with dynamic, role-pinned, or cost-aware
  assignment and records batch completion, per-lane completed work, and output repeatability.
  Measured on 2026-09-05 (EXP-016): cost-aware dispatch completes the batch 1.54× faster than the
  RTX 5090 alone on two machines and 2.07× on three; naive dispatch 1.30× / 1.41×; role pinning
  alone is a 0.66× loss. Documentation and receipts only; no release profile changed.

## [0.4.8] - 2026-09-05

### Added

- A deterministic, public-text agent corpus and stdlib-only MTP ablation runner now measure
  MTP0/3/5/7 against one frozen binary and model per RTX 5090, RTX 4090, and RTX 3090 lane.
  Public receipts retain only structural metrics and normalized hashes of client-visible answer,
  reasoning, reasoning-summary, and tool-call content. Review hardened the runner to reject
  unbound configuration fields and unknown response items, require a shared campaign identity and
  fresh-process MTP0 control, bind per-repetition promotion margins, and publish no process
  fingerprints. Campaign-scoped request and session identities are re-derived during reduction;
  receipts must carry the exact frozen corpus step inventory; unknown nested response content and
  non-canonical digest strings fail closed. Analysis revision 5 preserves the conclusive no-change
  result when no candidate clears the 5% margin in either repetition: MTP3 remains the fastest arm
  on all three lanes, while missing campaign and cross-process controls limit only exact-output
  attribution and faster-arm promotion. No release profile changed.
- A per-lane runtime variant campaign (`scripts/run_variant_campaign.py`, host launchers in
  `scripts/hosts/`) reuses the frozen agent corpus to compare artifact, KV-format, prefill-chunk,
  and context arms as fresh processes under one campaign identity, scores them by modeled session
  time against two recorded session shapes, and binds a relative private role-corpus screen to
  arms that change the artifact or KV format. Measured on 2026-09-04: the RTX 5090 retains
  `groupwise-int`/BF16/MTP3 (`nvfp4` refuses to start with BF16 KV at 131,072 context and, with
  INT8 KV, trades 2.22× prefill for a two-case grounding shift), the RTX 4090 promotes prefill
  chunk 2,048 for requalification, and the RTX 3090 measures 131,072-token capacity on its shipped
  profile. No release profile changed.
- `scripts/fleet_probe.py` now forks from the template id after the restart, verifies the restart
  through the lane's cumulative prefill counter, sends the session header the native lanes
  require, and waits for the RTX 4090's automatic save. Measured on 2026-09-04: template-fork warm
  starts are hot only as device-resident forks on the RTX 5090 (reliably at ≥ ~64K tokens; a 57.9K
  template alternates hot/cold forks), and checkpoint restore is slower than re-prefill on every
  lane (5090 24.7 s vs 21.8 s, 4090 130 s vs 41 s, 3090 91 s vs 49 s). Receipts published; no
  release profile changed.
- The RTX 5090 fork alternation was diagnosed as context-cache capacity, not planner policy:
  two source changes were rejected on the probe, and the unchanged shipped binary with
  `--max-private-continuations 8 --device-state-slots 4 --host-state-slots 24` kept 12/12 forks on
  the anchor path at 57.9K, 67.7K, and a loaded-catalog 57.9K for 0.43 GiB of slack — a trade
  (the first 67.7K fork pays 5.29 s vs 1.39 s while its anchor state materializes) and the v0.4.8
  RTX 5090 candidate profile. `scripts/restore_probe.py` shows a second restore of the same
  session is no faster on the native lanes (4090 132.8 → 149.0 s, 3090 91.8 → 92.2 s) and that the
  status endpoint blocks for the restore; both findings are filed upstream (ninfer#35, #36).
- All three lane configuration changes were requalified on their own rigs on 2026-09-05 and
  staged as the `v0.4.8` draft (`releases/v0.4.8/`, root authority still `v0.4.7`). RTX 3090
  `v0.2.3-beta.1` raises the C1 context ceiling to 131,072 on the unchanged INT8/MTP3/1,024-chunk
  stack and passed the 14-phase orchestrator with exact 130,048-token retrieval (218 s), 90.2
  decode tok/s at 300 W, 22,548 MiB peak, restart, rollback, security, and OMP gates
  (`tools/qualification/qualify_rtx3090.py` now binds the 128K fixture). RTX 4090 `v0.2.1` moves
  prefill chunk to 2,048 on a rebuilt but code-identical binary and passed protocol 15/15,
  the 102,060-token session in 68.0 s (84.9 s shipped), persistence, and the OMP golden run.
  RTX 5090 `qwen38-5090-v0.4.8` keeps the shipped image and adds
  `--max-private-continuations 8 --device-state-slots 4 --host-state-slots 24`; measured through
  the lifecycle tool: exact 130,048-token retrieval at 2,207 tok/s cold, 136.0 decode tok/s at
  41.2% MTP acceptance, the fork/delete/no-resurrection arc across a restart, 4/4 anchor hits at
  57.9K and 67.7K in one process, a 4.5 GB explicit save and verified restart (new
  `scripts/qualify_rtx5090_profile.py`). After a restart the first sibling fork of a restored
  template re-prefills once before its siblings run hot, which the receipt records as a scope
  note. Both native components are published and hash-verified, and the composed
  external-installation acceptance was rerun from the public URLs (new
  `scripts/hosts/accept-native-public-install.ps1`); the draft now waits only on the cut. No
  public profile changed.

## [0.4.7] - 2026-09-01

### Fixed

- v0.4.6's manifest bound product-versioned runtime asset names that 404 (the runtime version
  now trails the product version); v0.4.7 ships identical components with corrected URLs and
  `stage_release.py` derives asset names from the runtime tag.

## [0.4.6] - 2026-08-31

### Security

- Checkpoint manifests are now ORIGIN-authenticated on the RTX 5090 lane
  ([`ninfer@v0.4.5-qwen38-5090-beta.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.4.5-qwen38-5090-beta.1),
  closes [ninfer#32](https://github.com/alphastorm/ninfer/issues/32)): every save publishes
  `manifest.mac` - an HMAC-SHA256 over the exact manifest bytes, keyed by material derived from
  the bearer key and held outside the checkpoint root - and loads verify origin before trusting
  manifest content. Transient tag faults preserve `current` for retry; the compatibility window
  keeps locally-produced legacy generations loading; `--session-checkpoint-require-origin-auth`
  is the strict, reversible posture required before checkpoints are ever imported from remote
  storage (NAS/S3). Rollback-safe additive design - prior binaries read the same store, proven
  live during qualification. Independent council CRS-origin-auth closed with all 7 findings
  resolved. 4090/3090 components rebound unchanged.

## [0.4.5] - 2026-08-31

### Changed

- The RTX 3090 native Windows lane joins the durable train
  ([`ninfer@v0.2.2-qwen38-3090-beta.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.2.2-qwen38-3090-beta.1)):
  buffered checkpoint export off the engine execution lock (fail-before-publication preserved),
  every-turn automatic saves with sustained-idle debounce and redundant-frontier skip, explicit
  `POST /v1/ninfer/checkpoints` as the synchronous durability boundary, lineage-aware
  lazy-restore freshness guard, idempotent exact-endpoint restore, and constant-time
  session-ownership comparisons. Qualified 14/14 on the owner rig: **90.0 tok/s** decode at
  93.4% MTP acceptance under the 300 W managed envelope, exact 64K retrieval, **310 MB durable
  restart** with exact recall, bidirectional rollback, and real OMP client acceptance
  (council CRS-durable-3090, all 15 findings resolved).
- RTX 5090 and 4090 components rebound unchanged from v0.4.4.

## [0.4.4] - 2026-08-31

### Changed

- Checkpoint export no longer blocks the engine: exporter writes flow through a bounded
  in-memory queue (`--session-checkpoint-write-buffer-mib`, default 6144) drained to disk off
  the engine execution lock, with a deferred write failure still failing the save before
  anything publishes. Warm follow-up during checkpoint traffic 15.26 s → **0.91 s**, explicit
  save 31.6 s → **13.8 s**, and all four sibling fanout branches at **0.90-1.01 s** with
  automatic saves enabled at defaults
  ([acceptance receipt](docs/measurements/2026-08-31-fanout-probe-v044c.json),
  [ninfer#34](https://github.com/alphastorm/ninfer/issues/34)).
- Automatic checkpoint saves yield to live traffic: they start only after the engine stays
  quiet for consecutive samples (bounded at 60 s) and skip entirely when the catalogued
  checkpoint already covers the session's newest stored response. Explicit `POST` saves keep
  their synchronous crash-test contract.

### Fixed

- Lazy restore repairs partially resident sessions: restoring a checkpoint replaces the
  target session's complete stored lineage (partial overlap repaired, stale records removed)
  while any cross-session ID collision still fails closed, and restoring onto an exact live
  endpoint is an idempotent no-op instead of a refusal.

## [0.4.3] - 2026-08-31

### Added

- Same-lane agent fanout on the RTX 5090 container: sibling branches of one
  `previous_response_id` reuse the base prefill through private long anchors instead of
  replaying it from scratch. Measured at a 67.7K-token base: four branches 148.7 s → 47.9 s,
  and 0.40 s to first token when the anchor is still device-resident
  ([probe receipt](docs/measurements/2026-08-31-fanout-probe-v043.json), with the
  [v0.4.1 baseline](docs/measurements/2026-08-31-fanout-probe-v041-baseline.json) and a
  [device-state-slots null result](docs/measurements/2026-08-31-fanout-probe-v043-slots4.json)
  pinning the remaining sibling KV-clone ceiling,
  [ninfer#34](https://github.com/alphastorm/ninfer/issues/34)).
- Checkpoint refusal diagnostics carry the attempted response id in manual and automatic
  refusal log lines, populated without allocation on the refusal path.

### Fixed

- Private continuations never cross sessions: the session-isolation set proven on the 4090
  durable train (preserve private session ownership, isolate private cache sessions, harden
  session publication invariants) now ships on the 5090 lane, where the agent-protocol smoke
  exposed the latent cross-session private reuse.
- Anchored continuations no longer fail their first turn or restart restore: continuation
  summaries self-reserve anchor backing at the single populate chokepoint.
- Streaming UTF-8 repair and explicit invalid media-enum rejection (upstream parity picks).

### Security

- Checkpoint imports are bound to their load-time digests end to end: the reader re-hashes
  every streamed chunk with strict front-to-back single-pass coverage and fails closed, the
  `responses.cbor` reopen is digest-gated, and a divergence marks the generation corrupt so
  status stops advertising it and the next load quarantines it (closes
  [ninfer#21](https://github.com/alphastorm/ninfer/issues/21)).
- Checkpoint export writes refuse symlinks and reparse points and verify every staging
  directory component is a real directory, so a checkpoint-root writer cannot redirect
  server-authority writes (council CR-20260831-fanout43).
- Bearer, `x-api-key`, and stored-response session-ownership comparisons are constant-time
  digest-then-compare (closes [ninfer#22](https://github.com/alphastorm/ninfer/issues/22)).
- Checkpoint export copies are explicitly fenced behind in-flight compute-stream work via a
  recorded CUDA event (closes [ninfer#24](https://github.com/alphastorm/ninfer/issues/24)).

## [0.4.2] - 2026-08-31

### Added

- The RTX 4090 native Windows lane moves to the durable v0.2 package
  (`alphastorm/ninfer@v0.2.0-qwen38-4090-durable.1`): v0.4.1 checkpoint-store hardening on the
  native lineage, chunked KV snapshot restore with a fail-closed cross-layout guard, hardened
  D3D12 residency verification, WDDM evictable-budget CLI opt-in, streaming UTF-8 repair, and
  MTP K=15 draft capacity (shipped arm remains MTP3 per the width ablation).
- 4090 requalification receipts: protocol, 102,060-token seeded session, post-restart
  persistence restoring 102,075 tokens on a fresh process, OMP golden equivalence.
- Fleet measurements: RTX 3090 power sweep (350 W knee, +5.9% decode over the 300 W baseline;
  host PCIe link documented as gen3 x8) and the MTP draft-width ablation.

### Fixed

- The pinned OMP 18.0.9 client now completes cold-start sessions on the RTX 4090 lane: the
  native serve emits the full concrete status telemetry hierarchy (ninfer#28), with a
  regression mirroring the client validator field-for-field.

### Security

- Cross-family council review (CR-20260831-durable4090) at source freeze, before the Windows
  build: the convergent D3D12 probe-teardown P1 and a post-publish reclamation gap were
  remediated with regressions; upstream's global fast-math device flags were rejected to
  preserve the lane's numeric contract.

## [0.4.1] - 2026-08-31

### Fixed

- Post-publish checkpoint reclamation can no longer fail an acknowledged save: once the
  current pointer durably swaps, cleanup trouble is absorbed, the pass is marked unhealthy,
  and the next save refuses fail-closed until reclamation recovers (council
  CR-20260831-v041delta, convergent P1, remediated in alphastorm/ninfer#30 with a
  regression covering outage -> acknowledged save -> refusal -> recovery).
- A throwing tombstone-cleanup hook now degrades to an unhealthy reclamation pass instead of
  propagating; refusing an invalid engine stats export names `ProgramRejected` instead of
  leaving the skip reason empty.

### Added

- Health-gated publish transient tolerance (alphastorm/ninfer#27): a session whose checkpoint
  exceeds half the disk quota can still save its successor; the superseded generation is
  reclaimed under quota pressure only while every attempted reclamation succeeds.
- Named checkpoint skip reasons with response-id-correlated server logs
  (alphastorm/ninfer#26); HTTP refusal bodies keep the released closed vocabulary.
- v0.4.1 requalification on the owner appliance: explicit 316.8 MB checkpoint restored warm
  after `docker restart` (`reuse=private_endpoint`, 1.52 s), fork/delete arc with no
  resurrection through the reworked reclamation layer, decode 134.8 tok/s at temperature 0.

### Changed

- Release bytes were built in the pinned CI container on the owner appliance after three
  RunPod SECURE ssh-allocation failures; the route is documented in the component-release
  receipt and the build profile is stamped `appliance-local`.

## [0.4.0] - 2026-08-30

### Added

- Durable session checkpoints on the RTX 5090 container lane: transactional generational store
  (fsync-disciplined, corruption-quarantining, quota-evicting), automatic checkpoint queue, native
  io_uring O_DIRECT restore backend under a sha-pinned seccomp profile, and authenticated
  `/v1/ninfer/checkpoints` endpoints speaking the released 18.0.9 client's path addressing.
  Qualified live: automatic 7.95 GB checkpoint at a 109,725-token frontier; docker-restart
  continuation restored **109,589 tokens hot** on a rotated server instance (0.778 s serve-side
  first token); exact retrieval at 130,448 tokens; decode 143.0-144.8 tok/s.
- Durability now ships on **all three GPU lanes** - the RTX 5090 container joins the native
  Windows 4090/3090 DirectStorage lanes.
- Serve startup re-hashes the model artifact against its declared identity and refuses mismatch;
  lifecycle tooling is loopback-only; cross-family review CR-20260830 dispositions land with the
  candidate (9 mitigations, receipts in the component release).
- `examples/fleet/`: one provider fragment per qualified lane plus a role mapping for running
  three model-bound agents against the fleet.

### Changed

- The RTX 5090 container image moves to
  `ghcr.io/alphastorm/ninfer-runtime@sha256:8de5efdf...` (source `1ceaeebd`, binary `7eb66643`);
  the previous digest remains published as the rollback target.

## [0.3.2] - 2026-08-30

### Fixed

- Corrected the RTX 4090 qualification summary: the v0.3.1 copy carried its v0.2 template's
  limitations ("MTP0 qualified", "MTP3 performance not claimed") in direct contradiction of the
  MTP3 receipts it fronts, plus a stale beta classification. No component bytes, receipts, or
  measured numbers changed; v0.3.1 remains immutable with this defect on record.

## [0.3.1] - 2026-08-30

### Added

- Qualified MTP3 speculative profile on the RTX 4090 native Windows lane: identical released
  binary and model bytes with only the speculative configuration changed, promoted by the
  recorded two-arm MTP0-versus-MTP3 decision (+17.04% complete Golden-equivalent wall time;
  decode 93.2–97.7 tok/s vs the 52.330 tok/s MTP0 baseline; 107,851-token restored continuation
  with server-instance rotation).
- Exploratory draft-depth sweep (4 and 5 measured slower than 3 on the fixed decode workload),
  recorded as the first datapoint for the MTP depth-and-corpus ablation.
- Deterministic MTP3 arm package (+4 bytes over the baseline zip) with finalized qualification
  sidecar, SBOM, and SHA256SUMS published as a component release.

### Fixed

- Disclosed and patched two latent defects in the published qualification tooling (PowerShell 5.1
  serializer incompatibility; post-restart restore gate expecting a lazy restore label while the
  released engine restores checkpoints eagerly); the patched gate is strictly stronger, proving
  server-instance rotation plus at-least-100,000-token restoration.

## [0.3.0] - 2026-08-30

### Added
- Fresh RTX 5090 qualification on the identical published runtime bytes: 240.30 tok/s decode
  (MTP3, 99.87% acceptance), a 3,193.77-through-2,199.41 tok/s exact-retrieval prefill curve to
  130,048 tokens, a qualification-bound warm/cold pair (0.191 s vs 36.651 s at an 89,022-token
  session), and an in-process deletion/no-resurrection probe.
- Public-URL external installation acceptance for the RTX 3090 lane: verified download set,
  exact-bytes installer acceptance, authenticated smoke, and appliance-state restoration
  (GPU lease, scheduled task, endpoint, and power limit; console sign-out disclosed).
- Ready `v0.3.0` manifest binding three qualified GPU lanes, the composed external acceptance,
  and every per-lane receipt; `verify_release.py --require-ready` passes on the tree.

- Hash-bound RTX 3090 `v0.2.1-beta.1` parity candidate: deterministic path-neutral package,
  15/15 protocol checks, exact 64K retrieval, durable restart, bidirectional rollback, protected
  state, exact OMP acceptance, and managed 300 W performance evidence.
- One idempotent, checkpointed RTX 3090 qualification command covering preflight, neutral build,
  disclosure scan, package, install, acceptance, benchmark, receipt, and guaranteed GPU/task restore.
- Public early-access request form and one primary conversion action across first-screen surfaces.
- Launch-safe social MP4, animated GIF fallback, poster, and scoped evidence card with public
  checksums/provenance, plus clean-install and model/profile report forms.
- Launcher fail-fast diagnosis `wsl-mirrored-loopback-unavailable` when the runtime logs a
  loopback listener that the invoking namespace cannot reach, with troubleshooting entries for
  the WSL loopback-drift signature and the non-interactive-SSH Docker credential-helper failure
  ([#15](https://github.com/alphastorm/omp-ninfer/issues/15)).
- Test guards binding the published warm-vs-cold follow-up numbers to their committed receipt and
  covering the launcher's drift preflight.
- Community results row for the qualified native RTX 4090 variant, sourced from its committed
  qualification receipt, and GitHub Discussions linked from the issue chooser.
- Real-session README demo (GIF, MP4, poster) recorded against the exact released v0.2.0-beta.1
  RTX 5090 runtime, with provenance notes under `docs/media/`.
- Labeled maintainer warm-vs-cold follow-up-turn latency measurement on the released runtime.
- Receipt-bound benchmark charts (warm-vs-cold TTFT, RTX 5090 prefill curve, per-lane decode)
  rendered through the deterministic asset pipeline and embedded in the benchmarks page.
- Crisp 2x README demo derivatives (GIF, MP4, poster) rendered directly from the canonical cast
  with a brand-exact terminal palette, replacing the upscaled social fallback in the README.
- RTX 3090 qualified component release `v0.3.0-qwen38-3090.1` publishing the exact parity
  package bytes, source archive, SBOM, lifecycle scripts, and closed checksum set.
- Cross-session eviction hygiene invariant test pinned in the runtime after the v0.3 source
  freeze review; the review ledger dispositions are archived with the release evidence.

### Changed

- Rebuilt the campaign banner, architecture graphic, social preview, and benchmark story around one
  editorial hierarchy; the benchmark asset now leads with the measured warm-continuation outcome.
- Advanced public status copy from two qualified lanes plus a preview to three qualified candidates,
  while keeping the published v0.2 install authority explicit and immutable.
- Led the README and rendered social/benchmark surfaces with the long-session outcome, added a
  pre-command GPU lane chooser, and standardized qualified/preview/invited-beta status grammar.
- Sharpened the README hero around the measured value proposition and explicit lane status, and
  added LM Studio to the runtime comparison and related-work review.
- Replaced the former validation-hardware blocker copy after the returned RTX 3090 rig completed
  the full candidate gate; access copy now distinguishes qualified bytes from published authority.
- Refreshed stale v0.1-era statements in the contributing router, related-work family section,
  roadmap wedge, security policy support table, brand canon, and benchmark issue form.
- Cut every public surface over from invited-tester beta to first-public-release posture:
  BRAND status grammar and primary action, README front door, quickstart lanes, roadmap,
  security support table, contributing router, release channels, issue forms, profiles, and
  launcher pins now describe three qualified GPU lanes with public install authority.
- Promoted the RTX 3090 lane to qualified/installable in the compatibility authority and
  scaffolded the `v0.3.0` draft manifest with explicit publication blockers.

## [0.2.0-beta.1] - 2026-08-29

### Added

- Public, auditable OMP 18.0.9 source and native macOS arm64, Windows x64, and Linux x64 clients,
  each bound to immutable release assets and platform receipts.
- Managed cross-platform appliance lifecycle for exact `doctor`, `plan`, `install`, `status`, quick
  benchmark, durable checkpoint, rollback, and sanitized support receipts.
- Beta-qualified native Windows RTX 4090 support plus a public non-installable RTX 3090 preview;
  each binds exact source, package, SBOM, checksums, scripts, and qualification status.
- Durable process-restart continuation and checkpoint-aware response deletion on the qualified RTX
  4090 runtime; RTX 3090 live-model and Windows-package gates were `not_run` at the release cut.
- RTX 5090 documentation-strengthening prefill curve from 7,680 through 130,048 tokens and a new
  2,048-token decode measurement.

- Benchmarks page with qualified results, upstream campaign attribution, model-quality table,
  community results leaderboard, and a planned-measurements list.
- Public performance program page: measured baseline, scripted profiling lane, auditable
  experiment ledger including rejected attempts, and an open ideas backlog.
- Benchmark-report issue form feeding the community results table.
- Qualified-results stat strip asset for the README and benchmarks page.
- Continuous-integration badge row and measured-value badges bound to the qualified numbers.
- Release-verifier validation of every checked-in hardware profile against the manifest identity,
  transport, server, and provider contract, with a drift test.
- Published RTX 4090 lane qualification receipt (content-safe, prior evidence) linked from the
  performance program and roadmap.

### Changed

- Replaced the unavailable historical RTX 4090 private corpus with a committed synthetic OMP
  Golden-equivalent: typed primitive arguments, linked tool-result continuation, and an exact
  visible final-answer oracle. The historical corpus was not reused.
- Graduated all three native OMP clients from preview after hosted clean-install checks and live
  authenticated read-tool continuation.
- Made the product compatibility authority distinguish OMP client adapters from separately
  qualified native GPU runtime variants.

- Integrated the scripted SM120/MTP3 profiler and its retained experiment packets into NInfer
  mainline together with the latest direct upstream runtime changes.
- Rewrote the README around the product value proposition: stateful GPU-resident sessions,
  fail-closed privacy, verifiable release identity, a runtime comparison table, and the NInfer
  family lineage.
- Credited upstream projects explicitly and in order: Oh My Pi (can1357), NInfer (Neroued), the
  Qwen team, UDPSendToFailed/ninfer-4090, and Don-Chad/ninfer-3090.
- Documented the OMP client as a pinned fork build of Oh My Pi with upstreaming intent and the
  source-publication broad-release gate.
- Reframed the roadmap around shipped v0.1, the managed v0.2 lifecycle, the continuous performance
  program, and concrete ways to help.
- Extended contributing and related-work documentation with benchmark, performance, and NInfer
  family lanes; refreshed the architecture illustration for the Windows-primary topology.

### Security

- Added package/archive contract checks that bind the Homebrew cask to the installer actually
  present in the uploaded client archive, including bounded uninstall behavior.
- Recorded qualification-harness dirty state so an uncommitted runner cannot masquerade as its
  recorded Git commit.
- Made the packaged RTX 5090 build identity authoritative after rejecting one unresolvable source
  field in a benchmark sidecar; the measured binary/model/configuration hashes still match exactly.
- Removed private fleet projections from public qualification artifacts and kept stable promotion,
  production route activation, unattended-role activation, and silent cloud fallback disabled.

## [0.1.0-beta.1] - 2026-08-28

### Added

- Canonical OMP NInfer product repository and naming.
- Ready `v0.1.0-beta.1` manifest binding the native Windows OMP component, NInfer, Qwen3.8,
  the RTX 5090 profile, qualification summary, compatibility authority, and acceptance receipt.
- Ready native Windows quickstart plus managed macOS SSH and native Linux preview routes.
- Digest- and hash-verifying NInfer launcher, owned-container stop path, OMP provider fragment, and
  fail-closed OMP overlay.
- Runtime qualification summary covering exact long context, serving protocols, Vision, stateful
  Responses, cache reuse, Golden behavior, measured decode throughput, and explicit lifecycle
  non-claims.
- Architecture, security, release, troubleshooting, related-work, roadmap, contribution, and support
  documentation.
- Hardware-report and installation-failure issue forms.
- Standard-library release-contract verifier and CI checks, including a truthful
  `draft` → installable `candidate` → externally accepted `ready` transition.
- OMP NInfer brand system with source SVG/HTML, rendered README and architecture artwork, social
  preview, lockups, and icon/favicon variants.
- Deterministic local RTX 5090 binary package, OCI archive, and SPDX SBOM identities, plus a
  state-faithful remote lifecycle rehearsal; publication remains a separate gate.
- Fresh RTX 4090 package/install/restart evidence with an explicit Golden typed-tool-call blocker;
  no RTX 4090 support claim was added.
- Reviewed draft OMP transport for read-only remote `doctor`/`status`, with mutating operations and
  later lifecycle ownership still fail-closed.
- Published and bound the exact OMP, Homebrew, NInfer OCI, binary-package, SPDX, and checksum
  identities; advanced the product manifest through installable candidate to externally accepted
  ready release.
- Owner-operated tester-equivalent Windows clean install from public URLs, including tools, Vision,
  stateful exit/resume, fail-closed outage behavior, and exact runtime restoration.

### Security

- Restricted both NInfer and tunnel listeners to loopback in the supported profile.
- Required a user-only NInfer bearer-key file and disabled OMP model fallback for beta acceptance.
- Required immutable model, binary, image, SBOM, OMP artifact, qualification-summary, and component
  identities before a release can move from `draft` to `ready`.
- Excluded secrets, private host identifiers, prompts, model output, and raw logs from support
  material.

[Unreleased]: https://github.com/alphastorm/omp-ninfer/compare/v0.10.0...HEAD
[0.10.0]: https://github.com/alphastorm/omp-ninfer/compare/v0.9.1...v0.10.0
[0.9.1]: https://github.com/alphastorm/omp-ninfer/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/alphastorm/omp-ninfer/compare/v0.8.7...v0.9.0
[0.8.7]: https://github.com/alphastorm/omp-ninfer/compare/v0.8.6...v0.8.7
[0.8.6]: https://github.com/alphastorm/omp-ninfer/compare/v0.8.5...v0.8.6
[0.8.5]: https://github.com/alphastorm/omp-ninfer/compare/v0.8.4...v0.8.5
[0.8.4]: https://github.com/alphastorm/omp-ninfer/compare/v0.8.3...v0.8.4
[0.8.3]: https://github.com/alphastorm/omp-ninfer/compare/v0.8.2...v0.8.3
[0.8.2]: https://github.com/alphastorm/omp-ninfer/compare/v0.8.1...v0.8.2
[0.8.1]: https://github.com/alphastorm/omp-ninfer/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/alphastorm/omp-ninfer/compare/v0.7.4...v0.8.0
[0.7.4]: https://github.com/alphastorm/omp-ninfer/compare/v0.7.3...v0.7.4
[0.7.3]: https://github.com/alphastorm/omp-ninfer/compare/v0.7.2...v0.7.3
[0.7.2]: https://github.com/alphastorm/omp-ninfer/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/alphastorm/omp-ninfer/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/alphastorm/omp-ninfer/compare/v0.6.10...v0.7.0
[0.6.10]: https://github.com/alphastorm/omp-ninfer/compare/v0.6.9...v0.6.10
[0.6.9]: https://github.com/alphastorm/omp-ninfer/compare/v0.6.8...v0.6.9
[0.6.8]: https://github.com/alphastorm/omp-ninfer/compare/v0.6.7...v0.6.8
[0.6.7]: https://github.com/alphastorm/omp-ninfer/compare/v0.6.6...v0.6.7
[0.6.6]: https://github.com/alphastorm/omp-ninfer/compare/v0.6.5...v0.6.6
[0.6.5]: https://github.com/alphastorm/omp-ninfer/compare/v0.6.4...v0.6.5
[0.6.4]: https://github.com/alphastorm/omp-ninfer/compare/v0.6.3...v0.6.4
[0.6.3]: https://github.com/alphastorm/omp-ninfer/compare/v0.6.2...v0.6.3
[0.6.2]: https://github.com/alphastorm/omp-ninfer/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/alphastorm/omp-ninfer/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/alphastorm/omp-ninfer/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/alphastorm/omp-ninfer/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/alphastorm/omp-ninfer/compare/v0.4.9...v0.5.0
[0.4.9]: https://github.com/alphastorm/omp-ninfer/compare/v0.4.8...v0.4.9
[0.4.8]: https://github.com/alphastorm/omp-ninfer/compare/v0.4.7...v0.4.8
[0.4.7]: https://github.com/alphastorm/omp-ninfer/compare/v0.4.6...v0.4.7
[0.4.6]: https://github.com/alphastorm/omp-ninfer/compare/v0.4.5...v0.4.6
[0.4.5]: https://github.com/alphastorm/omp-ninfer/compare/v0.4.4...v0.4.5
[0.4.4]: https://github.com/alphastorm/omp-ninfer/compare/v0.4.3...v0.4.4
[0.4.3]: https://github.com/alphastorm/omp-ninfer/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/alphastorm/omp-ninfer/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/alphastorm/omp-ninfer/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/alphastorm/omp-ninfer/compare/v0.3.2...v0.4.0
[0.3.2]: https://github.com/alphastorm/omp-ninfer/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/alphastorm/omp-ninfer/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/alphastorm/omp-ninfer/compare/v0.2.0-beta.1...v0.3.0
[0.2.0-beta.1]: https://github.com/alphastorm/omp-ninfer/compare/v0.1.0-beta.1...v0.2.0-beta.1
[0.1.0-beta.1]: https://github.com/alphastorm/omp-ninfer/releases/tag/v0.1.0-beta.1
