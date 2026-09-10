# OMP NInfer v0.6.1 - a managed stop saves your session

A deliberate stop of the RTX 4090 native Windows lane now saves every live session before the
server exits. Since v0.2 a managed stop on Windows terminated the server: a session that was
never published - automatically above 32,768 frontier tokens, or explicitly through
`POST /v1/ninfer/checkpoints` - did not survive it. It does now. The RTX 5090 runtime, its
deployment profile, the RTX 3090 component, and the OMP client are byte-identical to v0.6.0
and carry their receipts.

## What changed

- **RTX 4090 runtime `v0.6.1-qwen38-4090-beta.1`**
  ([component](https://github.com/alphastorm/ninfer/releases/tag/v0.6.1-qwen38-4090-beta.1),
  runtime fork `63f28c95`, server binary `39490a44...`, package `4390a8cb...`,
  573,795,974 bytes), under deployment profile `qwen38-4090-native-v0.6.1-beta.1`
  (configuration `a938aaa1...`): the same INT8 KV, MTP3, prefill chunk 2,048, 131,072-token
  context, two device-state slots, 24 host-state slots, 4 GiB Host KV, one active request as
  v0.6.0. The engine is unchanged; the change is the stop.
- **The managed stop is a signal, not a termination.** The manager mints one manual-reset
  kernel event per launch and passes it as `--stop-event`; the server creates the object
  itself - refusing a name that already exists, admitting only `SYSTEM` and `Administrators` -
  and on its signal closes the listener, lets in-flight requests finish, saves every live
  session, and writes what it saved to `--shutdown-report`. A stop that lands while the model is
  still loading exits without serving. The controller signals, waits out the release's
  declared bound (900 s), and only then stops the task and forces the process; every outcome
  is recorded in `last-stop.json` (`last_stop` in the lifecycle status), and a stop that lost
  state is recorded as such rather than called graceful.
- **The channel is a per-release capability.** The installer copies `lifecycle.managed_stop`
  from the lane specification into the release record and carries it through every rewrite of
  an existing record; the shared controller - always the newest installed one, including after
  a rollback - passes the new flags only to a release that declares them. A rollback to v0.6.0
  is stopped by termination, as before; that binary refuses the flags as unknown arguments.
- **Qualified through the lane's own lifecycle tool, 15/15 phases** (EXP-029): the restart
  phase's second session - 45 tokens, never published, `missing` before the stop - comes back
  `available` quoting its marker with 45 cached input tokens after a graceful managed restart;
  the rollback phase records each direction's stop against what that release declares; exact
  130,048-token retrieval in 91.4 s; C1 2,104.9 tok/s prefill and 159.1 tok/s decode at 93.0%
  MTP acceptance and 22,814 MiB peak; the 15-check protocol at the shipped pool and at a third
  of it; the Windows state-security regression set; the OMP golden run exact; 103/103
  registered tests.
- **Two rounds of independent focused review** of the new control surface closed eight
  confirmed findings before the cut, the worst an installer that rebuilt every existing release
  record without the capability - which would have turned the next upgrade's incumbent stop
  back into a termination. Seven candidate windows on the owner rig found six more defects in
  the lifecycle handoff, the moment a gracefully exiting wrapper hands the lifecycle back to
  the controller, which never existed while stops were terminations. Each is closed with an
  executable invariant in the lifecycle contract tests.

## Evidence route

Lane receipt in `qualification/rtx4090.json`; the window record in
`docs/measurements/2026-09-10-rtx4090-graceful-stop-qualification.json` and the runtime probe
that first proved the flush in `docs/measurements/2026-09-10-native-managed-stop-flush.json`;
the public-URL install acceptance in `acceptance/rtx4090-public-install.json`; the composed
acceptance in `acceptance/composed-external-installation.json`. The RTX 5090 and RTX 3090
receipts are the v0.6.0 receipts for the unchanged components.

## Known limitation

A managed stop now saves every live session. A crash, a power loss, or a stop whose graceful
wait expires still loses what was never published, and the stop receipt records which
happened. The RTX 3090 lane keeps the v0.2.5 behaviour - a managed stop terminates - until its
mainline candidate ships.

## Support boundary

Unchanged: one owner-operated machine per lane; one active request per qualified profile;
loopback-only, bearer-authenticated, fail-closed. Checkpoints from an older runtime fingerprint
replay once from the OMP transcript. Community project; not affiliated with or endorsed by Oh
My Pi, Qwen, or NVIDIA.
