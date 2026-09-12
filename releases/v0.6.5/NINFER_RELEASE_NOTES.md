# OMP NInfer v0.6.5 - the macOS route, as a stranger runs it

No component changed. This release changes what a Mac reader executes: the quickstart's primary
route - macOS client, Windows 11 + Docker Desktop inference host - now runs end to end from its
own blocks, every outcome decided by the shell, including a session that survives the server
process. Every documented route in the quickstart is now covered by the same runner.

## What was wrong

v0.6.4 covered the three Windows routes; the macOS row, which is the first thing the quickstart
prints, was still the one route no runner had executed. Running it block by block from a Mac
with the owner's client state moved aside found (EXP-033):

- **The key-copy block was wrong for the documented destination.** Against a Windows 11 host the
  SSH server's default shell is `cmd.exe`, where `$HOME` and `2>/dev/null` mean nothing: a reader
  got an empty key file and a `cannot find the path` error. The restart block ran `sleep` on the
  same remote shell.
- **The acceptance was interactive prose** - open OMP, ask, look - so no runner could score it,
  and a reader had nothing to check against.

## What changed

- The key copy and the server restart use forms measured byte-identical against a Linux and a
  Windows destination; the survival check waits for `/health` through the tunnel instead of
  sleeping remotely.
- The macOS acceptance is a sequence of `-p` turns, each ending in a shell test of what the turn
  produced: tool marker, image description, nonce on `--continue`, nonce again after the server
  container is restarted from the Mac, and a fail-closed check with the tunnel stopped.
- `scripts/hosts/run-documented-route.sh` runs on macOS's system Python, keeps a foreground
  tunnel block open where the prose says "in another terminal", stops the `ssh` it exec'd - not
  just its wrapper - where the prose says Ctrl-C, and treats a run that executed fewer steps than
  the bundle lists as a failure. Each of those was a defect this route exposed and is now a
  regression test that fails on the previous runner.

## Evidence route

`docs/measurements/2026-09-12-macos-client-route-qualification.json` holds every run, red to
green, with each block's hash; `acceptance/documented-routes.json` accepts the macOS route and
carries the three Windows routes from v0.6.4 by hash, and
`acceptance/composed-external-installation.json` composes them with the carried component
acceptances. The post-cut verbatim run in the receipt executes the tagged blocks unchanged.

## Upgrading

Nothing to reinstall: component bytes, profiles, and configuration are v0.6.3's. Re-clone the tag
to get the corrected blocks. Installed lanes and sessions are unaffected.

## Known limitations

Unchanged from v0.6.3. Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or
NVIDIA.
