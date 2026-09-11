# OMP NInfer v0.6.4 - the documented routes, as a stranger runs them

No component changed. This release changes what a reader executes: every documented Windows
route now runs end to end from its own quickstart blocks on a stock Windows 11 host, and a Git
clone yields the recorded bytes on every platform. Neither was true before, on any Windows route.

## What was wrong

Every release so far was accepted through scripts that bypassed what a reader meets. Running the
RTX 4090 native route from its own blocks on an uninstalled host, and the RTX 5090 container
route's inference-host and native Windows client halves, found six defects (EXP-032):

- **Windows' default execution policy** (`Restricted`) blocked the first `.ps1` every block
  invokes - the client installer, the lane installer, the controller.
- **`python3` on Windows is the Microsoft Store shortcut**, not Python, even with python.org's
  Python installed; the verify step never ran.
- **Git for Windows installs with `core.autocrlf=true`**, which rewrote the hash-chained receipts
  at checkout: `verify_release.py --require-ready` failed on every hash of a stock clone. Only a
  tag carrying a `.gitattributes` fixes a stranger's clone, which is why this is a release.
- **The native route's key generation used .NET 5 APIs** that Windows PowerShell 5.1 lacks.
- The operate block was a menu that a paste runs as a sequence; both provider blocks ended by
  opening the interactive OMP session the next section asks you to run in the same process.

## What changed

- Every block that invokes a script opens with `Set-ExecutionPolicy -Scope Process
  -ExecutionPolicy Bypass -Force`, explained once: this window only, nothing on the machine.
- Windows blocks call `py -3`; the prerequisites name python.org's Python and its launcher.
- `.gitattributes` pins `* -text`, and `verify_release.py` names a checkout that rewrote line
  endings as the cause, first and once, instead of a page of mismatches.
- The native section opens with a real clone-and-verify block, generates the key with .NET
  Framework APIs, and operates the lane as a sequence; interactive launches live in prose.
- `scripts/documented_route.py` extracts a route's blocks by heading, and
  `scripts/hosts/run-documented-route.{ps1,sh}` execute them in one shell under the host's real
  policy, hashing every block before it runs. Tests refuse blocks that would break a paste. The
  route a release accepts is the route the documentation prints.

## Evidence route

`docs/measurements/2026-09-11-documented-routes-qualification.json` holds every run, red to green,
with each block's hash; `acceptance/documented-routes.json` accepts the three routes and
`acceptance/composed-external-installation.json` composes them with the carried component
acceptances. The RTX 4090 host now runs exactly what the route installs from public URLs.

## Upgrading

Re-clone the tag: a clone made with `core.autocrlf=true` before this release carries rewritten
receipts and cannot pass verification. Installed lanes and sessions are unaffected.

## Known limitations

Unchanged from v0.6.3. Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or
NVIDIA.
