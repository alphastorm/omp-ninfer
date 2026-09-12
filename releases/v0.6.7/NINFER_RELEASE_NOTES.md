# OMP NInfer v0.6.6 - the pinned client stays on its channel

No component changed. The config every documented route installs now turns the client's startup
update check off. Until this release the pinned OMP 18.0.9 client advertised

    Update Available
    New version 18.1.x is available. Run: omp update

which is not an instruction for this channel: the client is a hash-pinned release asset bound
into the manifest, and `omp update` replaces it outside the release procedure. A reader who
followed the banner left the qualified combination while everything still looked supported
([#18](https://github.com/alphastorm/omp-ninfer/issues/18), open since 2026-08-29).

## What changed

- `examples/manual-tunnel/fail-closed.yml` - the one config file every client route copies to
  `~/.omp/agent/config.yml` - adds `startup: checkUpdate: false`. The pinned client reads that
  setting only in nested form; a dotted `startup.checkUpdate:` key parses as an unrelated
  setting and leaves the default on. A test refuses any other shape.
- The quickstart says what the config does instead of pointing at an open issue: upgrade by
  cloning the next tag and rerunning the install step.
- `scripts/hosts/run-documented-route.sh` refuses to start a tunnel on a port it does not own
  and releases its forward when a run fails. A forward left by an earlier failed run used to
  answer the readiness probe - the tunnel step passed without binding anything, and the stale
  listener then made the fail-closed check report a live route.

## Evidence route

`docs/measurements/2026-09-12-client-channel-contract-qualification.json` holds every run with
each block's hash: the macOS route 10/10 from an isolated HOME, the native Windows client route
5/5, the RTX 4090 native route 7/7, each ending by reading `startup.checkUpdate` back from the
client its own route installed. `acceptance/documented-routes.json` accepts them and
`acceptance/composed-external-installation.json` composes them with the carried component
acceptances.

## Correction of record

v0.6.5's receipts state that the RTX 5090 appliance's production container was serving again
after that window. It was not: production had been stopped for a route window on 2026-09-11 with
its restart policy pinned off, and was not restored until 2026-09-12. The claim had been read off
the route's own container on the route's port. No v0.6.5 measurement is affected - every route
there ran against the route container, which is what those routes install and use - but the
restored-incumbent statement was false. Published receipts are immutable, so the correction lives
in this release's qualification receipt.

## Upgrading

Nothing to reinstall: component bytes, profiles, and configuration are v0.6.3's. Re-clone the tag
and rerun the config install step to pick up the channel setting. Installed lanes and sessions
are unaffected.

## Known limitations

Unchanged from v0.6.3. Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or
NVIDIA.
