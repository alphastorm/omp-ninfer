# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/alphastorm/omp-ninfer/compare/v0.6.6...HEAD
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
