# Quickstart

> **Versioned guide: v0.15.0 · stock Oh My Pi 18.14.0 · Qualified on RTX 5090 · 4090 · 3090**

OMP NInfer is the qualified local inference appliance and release layer connecting the
[Oh My Pi](https://github.com/can1357/oh-my-pi) (OMP) coding-agent client over authenticated
loopback to the NInfer inference engine serving Qwen3.8 27B on your GPU.

## Choose your lane

| GPU and host | Client route in v0.15.0 | Start here |
| --- | --- | --- |
| RTX 5090 container on Windows 11 + Docker Desktop / WSL2 | Native Windows x64 client over local loopback `127.0.0.1:18089` | [RTX 5090 Windows route](#ready-route-native-windows-and-docker-desktop-wsl2) |
| RTX 5090 container on Windows 11 / WSL2 or Linux | macOS arm64 client over a manual SSH tunnel (preview) | [macOS manual SSH route (preview)](#macos-client-over-a-manual-ssh-tunnel-preview) |
| RTX 4090 native Windows 11 (alone or beside RTX 3090) | Native Windows x64 client over local loopback `127.0.0.1:18082`; UUID-bound; unchanged beta.3 runtime, fresh client/route acceptance passed | [RTX 4090 native lane](#native-windows-rtx-4090-release-lane) |
| RTX 3090 native Windows 11 (alone or beside RTX 4090) | Native Windows x64 client over local loopback `127.0.0.1:18082`; UUID-bound; unchanged beta.3 MTP3 runtime, fresh client/route acceptance passed | [RTX 3090 native lane](#native-windows-rtx-3090-release-lane) |
| RTX 5090 container with Linux x64 client under WSL2 only | WSL2 shell client over local loopback `127.0.0.1:18089` (no native Linux OS qualification) | [WSL2 Linux client](#wsl2-linux-client-over-local-loopback) |
| Other GPU, non-WSL Linux client, or concurrent native serving | Unsupported | [Compatibility boundary](COMPATIBILITY.md) |

## Before you start

- **Clone the tag and run the ready gate:** start from a clean clone of `v0.15.0` and verify
  `python3 scripts/verify_release.py --require-ready` (`py -3 scripts\verify_release.py --require-ready`
  on Windows). Never install from a moving branch, an untagged archive, or a draft/candidate manifest.
- **Keep one release authority end to end:** stock OMP has no `omp appliance` commands, and
  `examples/manual-tunnel/fail-closed.yml` disables OMP's startup update check so `omp update`
  cannot replace the checksummed binary. Never mix current fragments with a legacy `v0.10.0` or
  `v0.7.2` route.
- **One GPU lane at a time per host:** both native Windows packages install on the same two-GPU
  host, but they share loopback port `127.0.0.1:18082` and serve sequentially — stop one lane and
  release its GPU lease before starting the other.
- **One shared model artifact (`huggingface.co/neroued/Qwen3.8-27B-NInfer`):** all three lanes
  bind published container version 3 `81f924d4` (`20,437,521,664` bytes, 20.4 GB), revision
  `1cbd84e7221e51186bd7f093a149912d2489625b`. Native routes use a separate
  `qwen3_8_27b-v3.ninfer` filename; keep the prior `eec39564` model untouched for historical
  recovery rather than resuming onto it.
- **Disk and memory prerequisites:** reserve at least 40 GiB of free disk space on the inference
  host plus a local filesystem for checkpoints (never a network share). RTX 5090 needs
  `28672 MiB` host RAM and a shared Host budget of `20867.734375 MiB` (21,881,405,440 bytes).
  Native RTX 4090 retains its `32768 MiB` host floor and shared Host budget `14787.734375 MiB`
  (15,506,063,360 bytes); RTX 3090 uses `11715.734375 MiB` (12,284,837,888 bytes).
  These replace separate host-slot/KV budgets; no smaller-host qualification is claimed.

## Contributor acceptance and preflight

You can exercise the stock client without a GPU: run
`python3 scripts/client_acceptance.py --omp ./omp-darwin-arm64 --omp-sha256 SHA256 --omp-version omp/18.14.0 --local-rehearsal --receipt rehearsal.json`,
substituting the binary and SHA-256 from the selected release's client descriptor (use
`omp-windows-x64.exe` or `omp-linux-x64` on those platforms). The runner creates a disposable
HOME and its own loopback Responses stub, checks a typed read-tool turn, continuation, a real
stub-process restart, client resume and fail-closed behavior, then removes its temporary state.
It never modifies your OMP configuration. No model download, Docker or GPU is needed.

The JSON receipt is explicitly `receipt_class: rehearsal`; the release verifier rejects it as
qualification evidence. It records the exact quickstart heading, block index and block SHA-256
for the semantic checks exercised, **not** a claim that the install commands or all 31 route
blocks ran verbatim. Stub restart proves the harness/client path, not NInfer durability or reuse.

For an owner-controlled live lane, omit `--local-rehearsal`, select `--lane`, provide `--endpoint`
and `--key-file`, and pass `--restart-cmd`, `--stop-cmd`, and `--start-cmd` as JSON argv arrays
(for example, `'["bash","restart-owned-lane.sh"]'`). Hooks must affect only your owned lane,
finish only when the route is ready/stopped, and run inside your approved maintenance window.
The stop test always attempts the start hook in a `finally` block. A live receipt is
`owner-live`, but does not replace runtime-identity, cache-hit, restoration or release qualification
gates. See `python3 scripts/client_acceptance.py --help` for options.

Measurement probes that previously assumed `q38-ninfer` now take their default from this guide's
RTX 5090 provider fragment. Run them from a complete product checkout, or pass `--model` explicitly
to a standalone copy. Their free-form `--lane` labels identify receipts, not model selection.
`client_acceptance.py --lane` instead follows the selected route's provider: the native RTX 3090
and RTX 5090 routes currently serve `q38-ninfer`, while native RTX 4090 serves `qwen3.8-27b`.
The native campaign launchers also resolve their model from the checkout before any host action;
their staged quality child requires that explicit model rather than keeping another default.

Before starting a container lane, run on its inference host:
`python3 scripts/doctor.py --lane rtx5090 --model MODEL --key-file KEY --omp OMP --client-platform linux-x64`.
Use `windows-x64` for a native Windows client, add `--hash-model` for the full model SHA-256,
or `--json` for machine-readable causes and remedies. Native lanes use `--lane rtx4090` or
`--lane rtx3090` plus `--profile server-config.json --release-spec release-spec.json` from the
verified package. `--running` checks reachability instead of a free port; `--container NAME`
also checks the actual container's publication. For a hardware-independent local check, run
`python3 scripts/doctor.py --offline --json`; skipped hardware checks are never passes.
Read the [doctor boundaries and remedies](TROUBLESHOOTING.md#named-cause-preflight) before
changing a running host.

## OMP 18.14.0 client

Release `v0.15.0` pins unmodified upstream
[Oh My Pi v18.14.0](https://github.com/can1357/oh-my-pi/releases/tag/v18.14.0) (source
`31147f9d1a76608549821c3759f8487b4d66c72d`, tree `9a63b5bfbb5971962c44fca660744b0d75dcd2c2`).
Exact binary URLs, sizes, and SHA-256 pins (`omp-windows-x64.exe` `620a5935…`,
`omp-linux-x64` `e7dd2b60…`, `omp-darwin-arm64` `60884395…`) are in
[`releases/v0.15.0/qualification/client-components.json`](../releases/v0.15.0/qualification/client-components.json).
The [upstream release comparison](https://github.com/can1357/oh-my-pi/compare/v18.12.6...v18.14.0)
covers every intervening stable release. The
[host-free review](measurements/2026-10-30-omp-18140-client-upgrade-review.json) records source
predicates and two macOS semantic stub rehearsals, not fresh live route acceptance. When migrating:

- **Per-model stateful Responses:** keep `compat.statefulResponses: true`,
  `compat.includeEncryptedReasoning: false`, and `compat.supportsReasoningSummary: false` on
  each NInfer model. These keys remain supported; no fragment migration is needed.
- **Remove `PI_OPENAI_STATEFUL`:** clear it from scripts, profiles, and environments
  (`unset PI_OPENAI_STATEFUL` or `Remove-Item Env:PI_OPENAI_STATEFUL -ErrorAction SilentlyContinue`);
  an inherited `0` overrides per-model `compat` and disables chaining.
- **Keep the image-detail default:** older RTX 5090 fragments should omit
  `compat.supportsImageDetailOriginal`; custom Responses endpoints default to `detail: "auto"`.
- **Use exact selectors:** provider-qualified model IDs no longer fuzzy-match a sibling.
  `ninfer-beta/q38-ninfer`, `ninfer-native-3090/q38-ninfer`, and
  `ninfer-native-4090/qwen3.8-27b` are exact IDs. The fleet worker's
  `ninfer-heavy/qwen3.8-27b:medium` is also valid: `:medium` selects effort, not a different model.
- **Edit defaults depend on the wire ID:** stock OMP recognizes `qwen3.8-27b` as Qwen 3.8 and
  now defaults it to the `replace` edit tool. The opaque `q38-ninfer` alias is not recognized
  by that family predicate and keeps `hashline`. No served model ID is renamed and this guide
  forces no edit override. An explicit `edit.modelVariants`, `edit.mode`, `PI_EDIT_VARIANT`,
  or `PI_STRICT_EDIT_MODE` remains an owner choice.
- **Leave the loop guard on:** `model.loopGuard` settings now reach custom `openai-responses`
  models too; the default exact-cycle detector covers these NInfer routes. No loop-guard
  disabling override is added by the fragments or acceptance runner.
- **Keep fail-closed config, concurrency limits, and default compaction:** install or merge
  [`examples/manual-tunnel/fail-closed.yml`](../examples/manual-tunnel/fail-closed.yml) so retries,
  cloud fallback, and startup update checks stay off, `providers.maxInFlightRequests` keeps
  `ninfer-beta` / `ninfer-main` at `2` and `ninfer-native-4090` / `ninfer-heavy` /
  `ninfer-native-3090` at `1`. The stock reserve still gives a 111,412-token threshold for a
  131,072-token window, with compaction triggered only above it; measured context includes the
  prompt and tools, not just the user's text. The compaction rework bounds retained history,
  ignores stale usage, and does not discard a completed summary if its optional short summary
  fails. These custom endpoints do not opt into an unsupported native remote-compaction API.
- **Use the rebuilt stock binaries:** upstream release builds now pin Bun 1.4.4, addressing
  CVE-2026-91403 (compromised certificate authorities) and CVE-2026-111497 (Brotli decoder write).
  Reusing the older client binary does not receive those bundled-runtime fixes.

## Acceptance evidence

**v0.15.0 fresh acceptance passed on 2026-10-30** on frozen candidate
`af62e7662fdc7195f7c1c88f2278b15f63130eba`: all three stock client platforms, all five
documented routes, both native public installs and independent restoration. Both initial windows
passed; no corrected attempt was needed. Runtime/model/profile bytes carry unchanged from v0.14.0,
but no predecessor client or product-route receipt is relabeled.

| Documented route | Fresh acceptance |
| --- | --- |
| RTX 5090 Windows 11 + Docker Desktop/WSL2 host | 2/2 blocks passed |
| macOS arm64 client over manual SSH tunnel | 10/10 passed; platform remains preview |
| Windows x64 client over RTX 5090 loopback | 5/5 accepted: 4 passed, 1 explicit pre-publication clone substitution |
| Native RTX 4090 on the two-GPU host | 7/7 blocks passed (19/19 route-behavior checks); first-release rollback `not_applicable` |
| Native RTX 3090 on the two-GPU host | 7/7 blocks passed (19/19 route-behavior checks); first-release rollback `not_applicable` |

All three newly downloaded stock OMP 18.14.0 clients passed runtime-bound typed tool/result, exact
continuation, and unavailable-route fail-closed checks. Linux ran under WSL2, not a separately
qualified native Linux OS. Image input passed on macOS and Windows against RTX 5090 only; there is
no native-lane or Linux vision claim. Both native documented routes performed fresh first-lineage
installs after temporarily preserving the canonical beta.3 roots and staging. The later public-URL checks
verified the exact assets and returned `already_installed` for
`qwen38-4090-native-v0.7.0-beta.3-2c6f423bd817` and
`qwen38-3090-native-v0.7.0-beta.3-2c6f423bd817`; both first-release lineages have no
predecessor and zero rollback directions. The WSL2 Linux client additionally passed documented
URL/hash installation and live/outage checks; it is not a sixth composer-addressed route.

Independent restoration passed for the RTX 5090 incumbent (image, mounts, health, restart policy,
checkout, key, and directory presence; 403.884 s hold) and for both sequential native baselines
(state, ACLs, tasks, holds, client files, power, directory presence, and documented staging).
The native driver windows were 371.326 s (RTX 4090) and 394.389 s (RTX 3090), restoring the same
canonical beta.3 stopped baselines at 450/370 W. No canonical promotion or production upgrade
was performed during acceptance.
[Documented routes](../releases/v0.15.0/acceptance/documented-routes.json) and
[composed acceptance](../releases/v0.15.0/acceptance/composed-external-installation.json) bind all
31 current executable route blocks; these subsequent acceptance-summary edits change prose only.
These are owner-operated
tester-equivalent observations, not independent external-user outcomes. Deferrals
[#88](https://github.com/alphastorm/omp-ninfer/issues/88)–[#90](https://github.com/alphastorm/omp-ninfer/issues/90)
and [#94](https://github.com/alphastorm/omp-ninfer/issues/94)–[#99](https://github.com/alphastorm/omp-ninfer/issues/99)
retain their historical dispositions in the [v0.14.0 notes](../releases/v0.14.0/NINFER_RELEASE_NOTES.md);
the [v0.15.0 notes](../releases/v0.15.0/NINFER_RELEASE_NOTES.md) distinguish shipped product-tooling
fixes from carried runtime limits. Council binding, final manifest pin, strict ready verification
and founder-owned publication are separate from acceptance. See [Releases](RELEASES.md).

## Current release at a glance

| Lane | Runtime component and source | Model artifact | Serving profile and limits |
| --- | --- | --- | --- |
| RTX 5090 container (`127.0.0.1:18089`) | `v0.7.0-qwen38-5090-beta.3`, source `2c6f423b` on upstream `64d10fbf`, server `55f0b95a`, image `760fb6be` | `81f924d4` (20,437,521,664 bytes) | Kept `qwen38-5090-v0.13.0` (config `751d22dc`): mandatory strict origin auth, DFlash2 K=7, BF16 KV (146,368 automatic tokens), 131,072 context, two active requests plus two extra device-state slots, shared Host budget, 180 s pending timeout; JSON-schema output, 128-character tool names, text, tools, vision, preserved thinking |
| RTX 4090 native Windows (`127.0.0.1:18082`) | `v0.7.0-qwen38-4090-beta.3`, source `2c6f423b` on upstream `64d10fbf`, package `87038cfb`, server `5caa7780` | `81f924d4` (20,437,521,664 bytes) | `qwen38-4090-native-v0.7.0-beta.3` (public config `b5cfbf50`): mandatory strict origin auth, MTP3/INT8, `Group64` A8 off, 131,072 context, C1, 30 s pending timeout, two extra slots, 2,048-token prefill, shared Host budget, 640 MiB admission headroom; JSON-schema output, 128-character tool names, text/tools (no vision or DFlash2) |
| RTX 3090 native Windows (`127.0.0.1:18082`) | `v0.7.0-qwen38-3090-beta.3`, source `2c6f423b` on upstream `64d10fbf`, package `a7637f66`, server `fedce425` | `81f924d4` (20,437,521,664 bytes) | `qwen38-3090-native-v0.7.0-beta.3` (public config `d08d262b`): mandatory strict origin auth, MTP3/INT8, `Group64` A8 off, 131,072 context, C1, 30 s pending timeout, four extra slots, 1,024-token prefill, shared Host budget, 768 MiB admission headroom, 350 W serving cap; JSON-schema output, 128-character tool names, text/tools (no vision or DFlash2) |

The exact RTX 5090 image is
`ghcr.io/alphastorm/ninfer-runtime@sha256:760fb6bea925eb26d4fa53ab87a126494b69ba7bcfed515d23dee7afa65cdb2a`,
and all three lanes bind engine source `2c6f423bd817b6534158553e1b34ab4959c43165`.
It ships checked first-build bytes under a founder-approved 5090-only reproducibility exception;
same-source second builds are not bit-identical. See the
[release notes](../releases/v0.15.0/NINFER_RELEASE_NOTES.md) and
[manifest](../releases/v0.15.0/manifest.json) for exact identities and scope.

- **Serving limits and compaction:** RTX 5090 admits two requests at once and holds a pending
  request for up to 180 s (`--pending-timeout-ms 180000`) when both prompts plus output reservations
  do not fit its 146,368-token automatic KV pool (upgrade an older one-at-a-time RTX 5090 server before
  raising its OMP limit). Native lanes serve one request at a time with a 30 s pending timeout;
  keeping their OMP limit at `1` lets turns wait in OMP during background compaction instead of
  expiring at the server
  ([troubleshooting](TROUBLESHOOTING.md#a-turn-fails-with-request_queue_timeout-late-in-a-long-session)).
- **Native two-GPU UUID topology and rollback:** Both native packages bind their GPU UUID and PCI
  address on a two-GPU Windows 11 host and serve sequentially on port `18082`. Both beta.3 runtime
  qualifications record no predecessor (`not_applicable`, zero rollback directions), not an
  inherited beta.2 upgrade/rollback result. Fresh v0.15.0 public-install and restoration
  acceptance passed with stock OMP 18.14.0. Preserve prior native release
  roots separately for historical recovery.
- **RTX 3090 power and upgrade:** the serving cap is now 350 W. Qualification restored the owner's
  370 W baseline on stop; this is not a promise about another operator's hardware. Stop a running
  v0.13.1 RTX 3090 lane before installing v0.14.0; its old 300 W lease otherwise fails the new
  cap check before replacement ([#94](https://github.com/alphastorm/omp-ninfer/issues/94)).
- **Checkpoints and legacy routes:** Stock OMP names each session with `prompt_cache_key`, which the
  authenticated runtime hashes into the session identity. Checkpoints restore across graceful
  restarts on all three lanes, but saves are best effort under traffic (a crash or expired wait can
  lose unsaved work; universal warm reuse is not promised) and restore requires the same runtime
  binary, model, profile, and bearer key. Single-GPU native owners staying on `v0.10.0` use the
  [immutable v0.10.0 guide](https://github.com/alphastorm/omp-ninfer/blob/v0.10.0/docs/QUICKSTART.md);
  the older RTX 3090 `v0.2` lineage on the OMP 18.0.9 fork client remains in the
  [historical v0.7.2 guide](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md).
- **Session capability boundary:** Within one API-key principal, prompt_cache_key names a session capability; use unique high-entropy keys and do not share that principal among mutually untrusted clients.
- **Native protocol and checkpoint gates:** Both beta.3 native runtime qualifications cover Chat and Responses
  JSON-schema structured output, 128-character tool names, status endpoint schema 2, and request-log
  schema 30. The package server-config (schema 4) uses
  `cache/<release-instance-id>/session-checkpoints-v3` (where `<release-instance-id>` is the
  installed release ID such as `qwen38-4090-native-v0.7.0-beta.3-2c6f423bd817`), not the old native
  root. Keep old native roots untouched; never migrate their generations. Replay OMP transcripts for
  a fresh prefill. Both native profiles require `--session-checkpoint-require-origin-auth` and a key
  of at least 32 bytes; the generated key below is 64 characters. Do not drop strict origin to
  accept old state.

## Ready route: native Windows and Docker Desktop WSL2

### Prerequisites

Windows 11 x64 with one RTX 5090, Docker Desktop (Linux containers, WSL2 Ubuntu 24.04, NVIDIA
container runtime), Git, PowerShell, Python 3 from python.org (`py` launcher, not the Microsoft
Store `python3` alias), 40 GiB free disk, and one trusted owner.

### Clone and verify the exact product release

Clone the tag in Windows and in the WSL2 distro that owns Docker (`Set-ExecutionPolicy` applies to
the current window only):

```powershell
git clone --branch v0.15.0 --depth 1 https://github.com/alphastorm/omp-ninfer.git
if ($LASTEXITCODE -ne 0) { throw 'release clone failed' }
Set-Location omp-ninfer
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
py -3 scripts\verify_release.py --require-ready
if ($LASTEXITCODE -ne 0) { throw 'ready gate failed' }
```

### Install the exact native Windows client

```powershell
$ErrorActionPreference = 'Stop'
$Url = 'https://github.com/can1357/oh-my-pi/releases/download/v18.14.0/omp-windows-x64.exe'
$Expected = '620a5935cdb6a9ed52d8b0c93892d6b5bb84155244a98f3be82af0455177bf29'
Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile omp-windows-x64.exe
if ((Get-FileHash omp-windows-x64.exe -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Expected) { throw 'OMP binary checksum mismatch' }
$Launcher = "$env:LOCALAPPDATA\OMP\omp.exe"
New-Item -ItemType Directory -Force -Path (Split-Path $Launcher) | Out-Null
Copy-Item .\omp-windows-x64.exe $Launcher -Force
Remove-Item Env:PI_OPENAI_STATEFUL -ErrorAction SilentlyContinue
& $Launcher --version
if ($LASTEXITCODE -ne 0) { throw 'OMP version check failed' }
```

The client version must be `omp/18.14.0` (to roll back, verify the previous pinned binary's
checksum before replacing `omp.exe`). Inside WSL2, run **3. Prepare the model and key** and
**4. Start NInfer** below, skip sections 5–6 (Docker Desktop exposes `127.0.0.1:18089` to native
Windows), then run **Native Windows OMP** in section 7 and **Native Windows command forms** in
section 8.

## Native Windows RTX 4090 release lane

Requires Windows 11 x64, one RTX 4090 (sm_89), a supported NVIDIA driver, Git, PowerShell, Python 3
(`py` launcher), and 40 GiB free disk. The installer binds the unique RTX 4090 UUID and PCI address
even beside an RTX 3090 (use `-GpuUuid` if multiple RTX 4090 cards exist; never hide a card). Stop
the other native lane on port `18082` first. The carried beta.3 runtime qualification records no
predecessor (`not_applicable`, zero rollback directions); fresh v0.15.0 public-install and product-route
acceptance passed with stock OMP 18.14.0. Keep prior native release
roots untouched for historical recovery.

```powershell
git clone --branch v0.15.0 --depth 1 https://github.com/alphastorm/omp-ninfer.git
if ($LASTEXITCODE -ne 0) { throw 'release clone failed' }
Set-Location omp-ninfer
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
py -3 scripts\verify_release.py --require-ready
if ($LASTEXITCODE -ne 0) { throw 'ready gate failed' }
```

```powershell
$VariantId = 'rtx4090-windows-native'
```

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
$ErrorActionPreference = 'Stop'
$Manifest = Get-Content .\releases\v0.15.0\manifest.json -Raw | ConvertFrom-Json
$Variant = @($Manifest.components.ninfer_variants | Where-Object { $_.id -ceq $VariantId })
if ($Variant.Count -ne 1 -or $Variant[0].status -cne 'qualified') {
  throw 'requested native runtime variant is not uniquely qualified'
}
$StateRootName = switch ($VariantId) {
  'rtx4090-windows-native' { 'qwen38-4090-native' }
  'rtx3090-windows-native' { 'qwen38-3090-native' }
  default { throw 'unknown native variant' }
}
$StateRoot = Join-Path $env:ProgramData (Join-Path 'NInfer' $StateRootName)
# Stage under ProgramData with an administrators-only ACL so no medium-integrity process
# under the same account can swap bytes between verification and elevated execution. Every
# step below is fail-closed: an ACL error stops the session before anything is downloaded.
$Stage = Join-Path $env:ProgramData ("omp-ninfer-stage-" + $VariantId)
if (Test-Path $Stage) { Remove-Item -Recurse -Force $Stage }
New-Item -ItemType Directory -Path $Stage | Out-Null
$Admins = New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-544')
$Acl = Get-Acl $Stage
$Acl.SetAccessRuleProtection($true, $false)
$Acl.SetOwner($Admins)
foreach ($Sid in @('S-1-5-32-544', 'S-1-5-18')) {
  $Rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    (New-Object System.Security.Principal.SecurityIdentifier($Sid)),
    'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
  $Acl.AddAccessRule($Rule)
}
Set-Acl $Stage $Acl
$Applied = Get-Acl $Stage
if (-not $Applied.AreAccessRulesProtected) { throw 'staging ACL protection did not apply' }
if (@($Applied.Access | Where-Object {
      $_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value -notin
      @('S-1-5-32-544', 'S-1-5-18') }).Count -ne 0) {
  throw 'staging ACL retains a non-administrator principal'
}
# The API key and the model live OUTSIDE the staging directory so reruns of this snippet never
# delete them, and the installer refuses a model stored inside the lane's own state root.
$KeyDir = Join-Path $env:ProgramData 'omp-ninfer-keys'
if (-not (Test-Path $KeyDir)) {
  New-Item -ItemType Directory -Path $KeyDir | Out-Null
  Set-Acl $KeyDir $Acl
}
$ApiKeyFile = Join-Path $KeyDir 'api-key.txt'
if (-not (Test-Path $ApiKeyFile)) {
  # Windows PowerShell runs on .NET Framework: no RandomNumberGenerator.Fill or Convert.ToHexString.
  $Secret = [byte[]]::new(32)
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($Secret)
  [IO.File]::WriteAllText($ApiKeyFile,
    ([BitConverter]::ToString($Secret).Replace('-', '').ToLowerInvariant() + "`n"),
    [Text.UTF8Encoding]::new($false))
}
$ModelDir = Join-Path $env:ProgramData 'omp-ninfer-model'
if (-not (Test-Path $ModelDir)) {
  New-Item -ItemType Directory -Path $ModelDir | Out-Null
  Set-Acl $ModelDir $Acl
}
$Model = Join-Path $ModelDir 'qwen3_8_27b-v3.ninfer'
# Both rebased native packages bind the published v3 primary model, not an old native override.
# Keep the prior v2 filename untouched so a resumed transfer cannot append incompatible bytes.
$NativeModel = $Manifest.components.model
if ($NativeModel.artifact_sha256 -cne $Variant[0].model_artifact_sha256) {
  throw 'native model artifact is not the variant''s bound model'
}
& curl.exe --fail --location --continue-at - --output $Model $NativeModel.artifact_url
# a rerun with a complete file gets HTTP 416 from the CDN; the byte-count and checksum below decide
if ($LASTEXITCODE -ne 0 -and (Get-Item $Model -ErrorAction SilentlyContinue).Length -ne [int64]$NativeModel.artifact_bytes) {
  throw 'model artifact download failed'
}
if ((Get-Item $Model).Length -ne [int64]$NativeModel.artifact_bytes) {
  throw 'model artifact byte count mismatch'
}
if ((Get-FileHash $Model -Algorithm SHA256).Hash.ToLowerInvariant() -cne
    $NativeModel.artifact_sha256) {
  throw 'model artifact checksum mismatch'
}
# A complete resumed transfer's HTTP 416 is accepted only after both identity checks.
$global:LASTEXITCODE = 0
foreach ($Asset in @(
  @{ Url = $Variant[0].package_url; Sha = $Variant[0].package_sha256 },
  @{ Url = $Variant[0].installer_url; Sha = $Variant[0].installer_sha256 },
  @{ Url = $Variant[0].controller_url; Sha = $Variant[0].controller_sha256 },
  @{ Url = $Variant[0].gpu_owner_controller_url; Sha = $Variant[0].gpu_owner_controller_sha256 },
  @{ Url = $Variant[0].state_protection_url; Sha = $Variant[0].state_protection_sha256 }
)) {
  $Name = [IO.Path]::GetFileName(([Uri]$Asset.Url).AbsolutePath)
  $Path = Join-Path $Stage $Name
  Invoke-WebRequest -UseBasicParsing -Uri $Asset.Url -OutFile $Path
  if ((Get-FileHash $Path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Asset.Sha) {
    throw "native runtime asset checksum mismatch: $Name"
  }
}
$Package = Join-Path $Stage ([IO.Path]::GetFileName(([Uri]$Variant[0].package_url).AbsolutePath))
if ((Get-Item $Package).Length -ne [int64]$Variant[0].package_bytes) {
  throw 'native runtime package byte count mismatch'
}
$Installer = Join-Path $Stage 'Install-Release.ps1'
& $Installer -PackagePath $Package -PackageSha256 $Variant[0].package_sha256 `
  -ModelArtifactPath $Model -ApiKeyFile $ApiKeyFile -StateRoot $StateRoot `
  -GpuOwnerControllerPath (Join-Path $Stage 'Control-GpuOwner.ps1')
```


## Operate the native lane

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
$Controller = Join-Path $StateRoot 'Control-Release.ps1'
& $Controller -Action Status -StateRoot $StateRoot   # the installed release, its identity, endpoint state
& $Controller -Action Stop -StateRoot $StateRoot     # checkpoints live sessions; inspect any refusals
& $Controller -Action Start -StateRoot $StateRoot    # the same command brings the lane back after a reboot
& $Controller -Action Status -StateRoot $StateRoot
```


## Point OMP at the native lane

Install the lane's fragment and the fail-closed config into `~/.omp/agent`, then load the key. A
rerun leaves identical files in place, and the block refuses to replace a `models.yml` or
`config.yml` that differs:

```powershell
$Provider = if ($VariantId -ceq 'rtx4090-windows-native') { 'ninfer-native-4090' } else { 'ninfer-native-3090' }
$Agent = Join-Path $HOME '.omp\agent'
New-Item -ItemType Directory -Force -Path $Agent | Out-Null
$env:NINFER_NATIVE_API_KEY = (Get-Content -Raw $ApiKeyFile).Trim()
Remove-Item Env:PI_OPENAI_STATEFUL -ErrorAction SilentlyContinue
$ModelsPath = Join-Path $Agent 'models.yml'
$ConfigPath = Join-Path $Agent 'config.yml'
$ModelsSource = '.\examples\windows-native\models.fragment.yml'
$ConfigSource = '.\examples\manual-tunnel\fail-closed.yml'
if ((Test-Path $ModelsPath) -and (Get-FileHash $ModelsPath).Hash -cne (Get-FileHash $ModelsSource).Hash) {
  throw "Existing $ModelsPath differs; merge providers.$Provider instead of overwriting it."
}
if ((Test-Path $ConfigPath) -and (Get-FileHash $ConfigPath).Hash -cne (Get-FileHash $ConfigSource).Hash) {
  throw "Existing $ConfigPath differs; merge fail-closed.yml instead of overwriting it."
}
if (-not (Test-Path $ModelsPath)) { Copy-Item $ModelsSource $ModelsPath }
if (-not (Test-Path $ConfigPath)) { Copy-Item $ConfigSource $ConfigPath }
```

The key and stateful setting are loaded before either merge refusal. If a file differs, merge
only the named provider or fail-closed settings, then continue in this same PowerShell process.


## Native lane acceptance

```powershell
$Launcher = "$env:LOCALAPPDATA\OMP\omp.exe"
$Smoke = Join-Path $env:TEMP ("omp-ninfer-native-" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $Smoke | Out-Null
Set-Content -NoNewline -Encoding ascii -Path (Join-Path $Smoke 'marker.txt') -Value 'OMP_NINFER_TOOL_OK'
Push-Location $Smoke
try {
  & $Launcher -p --no-session --auto-approve --model "$Provider/qwen3.8-27b" `
    'Use a file-reading tool to read marker.txt, then report its exact single line.'
  if ($LASTEXITCODE -ne 0) { throw 'text/tool acceptance failed' }

  $Session = Join-Path $Smoke 'sessions'
  & $Launcher -p --auto-approve --session-dir $Session --model "$Provider/qwen3.8-27b" `
    'Remember the nonce 493817-205361 for my next turn. Reply OK only.'
  if ($LASTEXITCODE -ne 0) { throw 'state setup failed' }
  & $Launcher -p --auto-approve --session-dir $Session --continue `
    'Return the exact nonce from the prior turn verbatim, character for character. Do not correct or change its spelling. Return nothing else.'
  if ($LASTEXITCODE -ne 0) { throw 'stateful resume failed' }
} finally { Pop-Location }

& $Controller -Action Stop -StateRoot $StateRoot | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'native stop failed' }
& $Launcher -p --no-session --auto-approve --max-time 20s `
  --model "$Provider/qwen3.8-27b" 'Return LOCAL_ONLY.'
if ($LASTEXITCODE -eq 0) { throw 'outage request unexpectedly succeeded' }
$global:LASTEXITCODE = 0
& $Controller -Action Start -StateRoot $StateRoot | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'native restart failed' }
```


## Native Windows RTX 3090 release lane

Requires Windows 11 x64, one RTX 3090 (sm_86), a supported NVIDIA driver, Git, PowerShell, Python 3
(`py` launcher), and 40 GiB free disk. The installer binds the card's UUID and PCI address even
beside an RTX 4090 (use `-GpuUuid` if multiple RTX 3090 cards exist). Stop the other native lane on
port `18082` first. The beta.3 runtime qualification records no predecessor (`not_applicable`,
zero rollback directions); prior beta.2 acceptance does not transfer.

This client-only release installs the same MTP3 runtime package as v0.14.0; it changes neither
the runtime profile nor the 350 W serving cap. The following upgrade warning applies only to the
historical v0.13.1-to-v0.14.0 transition.

**Upgrade from v0.13.1: stop the running RTX 3090 lane before installing v0.14.0.** Use the
installed controller's `Stop` action from [Operate the RTX 3090 native lane](#operate-the-rtx-3090-native-lane)
and inspect any refusal before continuing. A running v0.13.1 lane holds a 300 W GPU-owner lease;
the new installer checks it against the 350 W serving cap and refuses before replacement, leaving
the old lane running unchanged. A stopped lane upgrades normally
([#94](https://github.com/alphastorm/omp-ninfer/issues/94)). Keep prior roots for historical recovery;
this prerequisite is not a claim of qualified upgrade/rollback directions.

```powershell
git clone --branch v0.15.0 --depth 1 https://github.com/alphastorm/omp-ninfer.git
if ($LASTEXITCODE -ne 0) { throw 'release clone failed' }
Set-Location omp-ninfer
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
py -3 scripts\verify_release.py --require-ready
if ($LASTEXITCODE -ne 0) { throw 'ready gate failed' }
```

```powershell
$VariantId = 'rtx3090-windows-native'
```

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
$ErrorActionPreference = 'Stop'
$Manifest = Get-Content .\releases\v0.15.0\manifest.json -Raw | ConvertFrom-Json
$Variant = @($Manifest.components.ninfer_variants | Where-Object { $_.id -ceq $VariantId })
if ($Variant.Count -ne 1 -or $Variant[0].status -cne 'qualified') {
  throw 'requested native runtime variant is not uniquely qualified'
}
if ($VariantId -cne 'rtx3090-windows-native') { throw 'expected RTX 3090 native variant' }
$StateRootName = 'qwen38-3090-native'
$StateRoot = Join-Path $env:ProgramData (Join-Path 'NInfer' $StateRootName)
# Stage under ProgramData with an administrators-only ACL so no medium-integrity process
# under the same account can swap bytes between verification and elevated execution. Every
# step below is fail-closed: an ACL error stops the session before anything is downloaded.
$Stage = Join-Path $env:ProgramData ("omp-ninfer-stage-" + $VariantId)
if (Test-Path $Stage) { Remove-Item -Recurse -Force $Stage }
New-Item -ItemType Directory -Path $Stage | Out-Null
$Admins = New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-544')
$Acl = Get-Acl $Stage
$Acl.SetAccessRuleProtection($true, $false)
$Acl.SetOwner($Admins)
foreach ($Sid in @('S-1-5-32-544', 'S-1-5-18')) {
  $Rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    (New-Object System.Security.Principal.SecurityIdentifier($Sid)),
    'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
  $Acl.AddAccessRule($Rule)
}
Set-Acl $Stage $Acl
$Applied = Get-Acl $Stage
if (-not $Applied.AreAccessRulesProtected) { throw 'staging ACL protection did not apply' }
if (@($Applied.Access | Where-Object {
      $_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value -notin
      @('S-1-5-32-544', 'S-1-5-18') }).Count -ne 0) {
  throw 'staging ACL retains a non-administrator principal'
}
# The API key and the model live OUTSIDE the staging directory so reruns of this snippet never
# delete them, and the installer refuses a model stored inside the lane's own state root.
$KeyDir = Join-Path $env:ProgramData 'omp-ninfer-keys'
if (-not (Test-Path $KeyDir)) {
  New-Item -ItemType Directory -Path $KeyDir | Out-Null
  Set-Acl $KeyDir $Acl
}
$ApiKeyFile = Join-Path $KeyDir 'api-key.txt'
if (-not (Test-Path $ApiKeyFile)) {
  # Windows PowerShell runs on .NET Framework: no RandomNumberGenerator.Fill or Convert.ToHexString.
  $Secret = [byte[]]::new(32)
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($Secret)
  [IO.File]::WriteAllText($ApiKeyFile,
    ([BitConverter]::ToString($Secret).Replace('-', '').ToLowerInvariant() + "`n"),
    [Text.UTF8Encoding]::new($false))
}
$ModelDir = Join-Path $env:ProgramData 'omp-ninfer-model'
if (-not (Test-Path $ModelDir)) {
  New-Item -ItemType Directory -Path $ModelDir | Out-Null
  Set-Acl $ModelDir $Acl
}
$Model = Join-Path $ModelDir 'qwen3_8_27b-v3.ninfer'
# Both rebased native packages bind the published v3 primary model, not an old native override.
# Keep the prior v2 filename untouched so a resumed transfer cannot append incompatible bytes.
$NativeModel = $Manifest.components.model
if ($NativeModel.artifact_sha256 -cne $Variant[0].model_artifact_sha256) {
  throw 'native model artifact is not the variant''s bound model'
}
& curl.exe --fail --location --continue-at - --output $Model $NativeModel.artifact_url
# a rerun with a complete file gets HTTP 416 from the CDN; the byte-count and checksum below decide
if ($LASTEXITCODE -ne 0 -and (Get-Item $Model -ErrorAction SilentlyContinue).Length -ne [int64]$NativeModel.artifact_bytes) {
  throw 'model artifact download failed'
}
if ((Get-Item $Model).Length -ne [int64]$NativeModel.artifact_bytes) {
  throw 'model artifact byte count mismatch'
}
if ((Get-FileHash $Model -Algorithm SHA256).Hash.ToLowerInvariant() -cne
    $NativeModel.artifact_sha256) {
  throw 'model artifact checksum mismatch'
}
# A complete resumed transfer's HTTP 416 is accepted only after both identity checks.
$global:LASTEXITCODE = 0
foreach ($Asset in @(
  @{ Url = $Variant[0].package_url; Sha = $Variant[0].package_sha256 },
  @{ Url = $Variant[0].installer_url; Sha = $Variant[0].installer_sha256 },
  @{ Url = $Variant[0].controller_url; Sha = $Variant[0].controller_sha256 },
  @{ Url = $Variant[0].gpu_owner_controller_url; Sha = $Variant[0].gpu_owner_controller_sha256 },
  @{ Url = $Variant[0].state_protection_url; Sha = $Variant[0].state_protection_sha256 }
)) {
  $Name = [IO.Path]::GetFileName(([Uri]$Asset.Url).AbsolutePath)
  $Path = Join-Path $Stage $Name
  Invoke-WebRequest -UseBasicParsing -Uri $Asset.Url -OutFile $Path
  if ((Get-FileHash $Path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Asset.Sha) {
    throw "native runtime asset checksum mismatch: $Name"
  }
}
$Package = Join-Path $Stage ([IO.Path]::GetFileName(([Uri]$Variant[0].package_url).AbsolutePath))
if ((Get-Item $Package).Length -ne [int64]$Variant[0].package_bytes) {
  throw 'native runtime package byte count mismatch'
}
$Installer = Join-Path $Stage 'Install-Release.ps1'
& $Installer -PackagePath $Package -PackageSha256 $Variant[0].package_sha256 `
  -ModelArtifactPath $Model -ApiKeyFile $ApiKeyFile -StateRoot $StateRoot `
  -GpuOwnerControllerPath (Join-Path $Stage 'Control-GpuOwner.ps1')
```


## Operate the RTX 3090 native lane

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
$Controller = Join-Path $StateRoot 'Control-Release.ps1'
& $Controller -Action Status -StateRoot $StateRoot   # the installed release, its identity, endpoint state
& $Controller -Action Stop -StateRoot $StateRoot     # checkpoints live sessions; inspect any refusals
& $Controller -Action Start -StateRoot $StateRoot    # the same command brings the lane back after a reboot
& $Controller -Action Status -StateRoot $StateRoot
```


## Point OMP at the RTX 3090 native lane

Install the lane's fragment and the fail-closed config into `~/.omp/agent`, then load the key. A
rerun leaves identical files in place, and the block refuses to replace a `models.yml` or
`config.yml` that differs:

```powershell
$Provider = 'ninfer-native-3090'
$Agent = Join-Path $HOME '.omp\agent'
New-Item -ItemType Directory -Force -Path $Agent | Out-Null
$env:NINFER_NATIVE_API_KEY = (Get-Content -Raw $ApiKeyFile).Trim()
Remove-Item Env:PI_OPENAI_STATEFUL -ErrorAction SilentlyContinue
$ModelsPath = Join-Path $Agent 'models.yml'
$ConfigPath = Join-Path $Agent 'config.yml'
$ModelsSource = '.\examples\windows-native\models-rtx3090.fragment.yml'
$ConfigSource = '.\examples\manual-tunnel\fail-closed.yml'
if ((Test-Path $ModelsPath) -and (Get-FileHash $ModelsPath).Hash -cne (Get-FileHash $ModelsSource).Hash) {
  throw "Existing $ModelsPath differs; merge providers.$Provider instead of overwriting it."
}
if ((Test-Path $ConfigPath) -and (Get-FileHash $ConfigPath).Hash -cne (Get-FileHash $ConfigSource).Hash) {
  throw "Existing $ConfigPath differs; merge fail-closed.yml instead of overwriting it."
}
if (-not (Test-Path $ModelsPath)) { Copy-Item $ModelsSource $ModelsPath }
if (-not (Test-Path $ConfigPath)) { Copy-Item $ConfigSource $ConfigPath }
```

The key and stateful setting are loaded before either merge refusal. If a file differs, merge
only the named provider or fail-closed settings, then continue in this same PowerShell process.


## RTX 3090 native lane acceptance

```powershell
$Launcher = "$env:LOCALAPPDATA\OMP\omp.exe"
$Smoke = Join-Path $env:TEMP ("omp-ninfer-native-" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $Smoke | Out-Null
Set-Content -NoNewline -Encoding ascii -Path (Join-Path $Smoke 'marker.txt') -Value 'OMP_NINFER_TOOL_OK'
Push-Location $Smoke
try {
  & $Launcher -p --no-session --auto-approve --model "$Provider/q38-ninfer" `
    'Use a file-reading tool to read marker.txt, then report its exact single line.'
  if ($LASTEXITCODE -ne 0) { throw 'text/tool acceptance failed' }

  $Session = Join-Path $Smoke 'sessions'
  & $Launcher -p --auto-approve --session-dir $Session --model "$Provider/q38-ninfer" `
    'Remember the nonce 493817-205361 for my next turn. Reply OK only.'
  if ($LASTEXITCODE -ne 0) { throw 'state setup failed' }
  & $Launcher -p --auto-approve --session-dir $Session --continue `
    'Return the exact nonce from the prior turn verbatim, character for character. Do not correct or change its spelling. Return nothing else.'
  if ($LASTEXITCODE -ne 0) { throw 'stateful resume failed' }
} finally { Pop-Location }

& $Controller -Action Stop -StateRoot $StateRoot | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'native stop failed' }
& $Launcher -p --no-session --auto-approve --max-time 20s `
  --model "$Provider/q38-ninfer" 'Return LOCAL_ONLY.'
if ($LASTEXITCODE -eq 0) { throw 'outage request unexpectedly succeeded' }
$global:LASTEXITCODE = 0
& $Controller -Action Start -StateRoot $StateRoot | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'native restart failed' }
```

## WSL2 Linux client over local loopback

This is the Linux x64 client inside the same Ubuntu 24.04 WSL2 distro that owns the RTX 5090
container, not a separately qualified native Linux OS. In that distro, clone and verify the
release with [section 1](#1-clone-the-exact-release-on-both-machines), then complete
[host preparation](#3-prepare-the-model-and-key-on-the-inference-host) and
[runtime startup](#4-start-ninfer-on-the-inference-host). Skip the Mac installer and SSH tunnel:
this client reaches `127.0.0.1:18089` directly.

From the tagged clone, install the release's checksummed `omp-linux-x64` and copy the local key:

```sh
(
set -euo pipefail
CLIENT='releases/v0.15.0/qualification/client-components.json'
URL=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["platforms"]["linux-x64"]["asset_url"])' "$CLIENT")
EXPECTED=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["platforms"]["linux-x64"]["asset_sha256"])' "$CLIENT")
VERSION=$(python3 -c 'import json,sys; print("omp/" + json.load(open(sys.argv[1]))["omp"]["distribution_version"])' "$CLIENT")
curl --fail --location --output omp-linux-x64 "$URL"
test "$(sha256sum omp-linux-x64 | cut -d ' ' -f 1)" = "$EXPECTED"
install -d -m 700 "$HOME/.local/bin" "$HOME/.omp/agent"
install -m 755 omp-linux-x64 "$HOME/.local/bin/omp"
install -m 600 "$HOME/.config/omp-ninfer/api-key" "$HOME/.omp/agent/ninfer-beta.key"
unset PI_OPENAI_STATEFUL
test "$("$HOME/.local/bin/omp" --version)" = "$VERSION"
)
```

Add `$HOME/.local/bin` to `PATH`, then install or merge both
[section 7 shell config blocks](#7-add-the-omp-provider). Use the
[text/tool](#text-and-tool-turn) and [stateful follow-up](#stateful-follow-up-and-omp-resume)
checks in that shell, without a tunnel. The shared
[server-survival check](#session-survives-the-server-process) uses SSH only for the restart;
on this loopback route run `docker restart --timeout 60 omp-ninfer-beta` locally instead.
No Linux image-input qualification is claimed.

For fail-closed acceptance, stop this owned runtime rather than a nonexistent tunnel:

```sh
set -e
"$HOME/omp-ninfer/examples/manual-tunnel/stop-ninfer.sh"
if omp -p --no-session --max-time 20s --model ninfer-beta/q38-ninfer "Return LOCAL_ONLY."; then
  echo 'outage request unexpectedly succeeded' >&2; false
fi
```

Expected result: a connection failure and no model response. Any cloud-provider request is a
release failure. Restart NInfer with section 4 only after observing the failure.

## macOS client over a manual SSH tunnel (preview)

The macOS arm64 client is a preview platform (stock upstream binary over a manual OpenSSH loopback
tunnel, without a managed macOS installer or appliance service); fresh acceptance of all 10
executable blocks against the beta.3 RTX 5090 container lane passed. Sections 3 and 4 also serve as
the inference-host setup for the Windows and WSL2 Linux client routes.

### Prerequisites

- **Mac:** Apple silicon macOS supported by the pinned upstream binary, OpenSSH, `curl`, Python 3,
  and at least 1 GiB free disk.
- **Inference host:** a single-user Linux or WSL2 environment owning one RTX 5090, current NVIDIA
  driver, Docker with NVIDIA Container Toolkit, OpenSSH terminating in the same namespace, at least
  40 GiB free disk for the 20,437,521,664-byte model, image, and logs, and **at least 28 GiB of
  memory available to the container** for the shared 21,881,405,440-byte Host pool (`start-ninfer.sh`
  refuses smaller hosts before loading). On Docker Desktop, raise the WSL2 VM limit in
  `%UserProfile%\.wslconfig` and run `wsl --shutdown`:

  ```ini
  [wsl2]
  memory=32GB
  ```

The endpoint binds only to remote loopback (`127.0.0.1:18089`); never expose it on a LAN or public
interface. Both machines and local accounts must be controlled by one trusted owner.

## 1. Clone the exact release on both machines

Run the chain as one block. A failed clone stops before entering any existing `omp-ninfer`
directory; the ready gate explicitly names the release being installed.

```sh
git clone --branch v0.15.0 --depth 1 \
  https://github.com/alphastorm/omp-ninfer.git &&
cd omp-ninfer &&
python3 scripts/verify_release.py --release v0.15.0 --require-ready
```

## 2. Install the OMP beta on the Mac

Despite the retained heading, this installs the stock Oh My Pi 18.14.0 binary (`omp-darwin-arm64`):

```sh
(
set -euo pipefail
URL='https://github.com/can1357/oh-my-pi/releases/download/v18.14.0/omp-darwin-arm64'
EXPECTED='608843959ab34295d52460dd09dd7d548b6c903c08a83c67954c2d4c36fd1f5a'
curl --fail --location --output omp-darwin-arm64 "$URL"
test "$(shasum -a 256 omp-darwin-arm64 | cut -d ' ' -f 1)" = "$EXPECTED"
mkdir -p "$HOME/.local/bin"
cp omp-darwin-arm64 "$HOME/.local/bin/omp"
chmod 0755 "$HOME/.local/bin/omp"
unset PI_OPENAI_STATEFUL
"$HOME/.local/bin/omp" --version
)
```

The version must be `omp/18.14.0`; add `$HOME/.local/bin` to `PATH` before continuing.

## 3. Prepare the model and key on the inference host

```sh
ROOT="$HOME/.local/share/omp-ninfer"
STATE="$HOME/.config/omp-ninfer"
LOGS="$HOME/.local/state/omp-ninfer"
CHECKPOINTS="$ROOT/checkpoints-v013"
install -d -m 700 "$ROOT" "$STATE" "$LOGS" "$CHECKPOINTS"

MODEL_URL=$(python3 -c \
  'import json; print(json.load(open("releases/v0.15.0/manifest.json"))["components"]["model"]["artifact_url"])')
MODEL_BYTES=$(python3 -c \
  'import json; print(json.load(open("releases/v0.15.0/manifest.json"))["components"]["model"]["artifact_bytes"])')
MODEL_SHA256=$(python3 -c \
  'import json; print(json.load(open("releases/v0.15.0/manifest.json"))["components"]["model"]["artifact_sha256"])')
MODEL="$ROOT/qwen3_8_27b-v3.ninfer"

# a rerun with a complete file gets HTTP 416 from the CDN; the byte-count and checksum below decide
curl --fail --location --continue-at - --output "$MODEL" "$MODEL_URL" \
  || test "$(stat -c %s "$MODEL")" = "$MODEL_BYTES"
test "$(stat -c %s "$MODEL")" = "$MODEL_BYTES"
printf '%s  %s\n' "$MODEL_SHA256" "$MODEL" | sha256sum --check --strict

umask 077
# a rerun keeps the existing key: checkpoint MACs and every client's copy are bound to it
test -s "$STATE/api-key" || openssl rand -hex 32 > "$STATE/api-key"
chmod 600 "$STATE/api-key"
```

The artifact is pinned to one Hugging Face revision, byte count, and SHA-256. A checksum mismatch is
a hard stop; do not rename or reuse the partial file as a successful download. The separate
`qwen3_8_27b-v3.ninfer` path avoids appending a resumed download onto an older model container.

A rerun keeps an existing nonempty key, because checkpoint MACs and the copy each client holds are
bound to it. To rotate the key, stop NInfer, move the old key aside, rerun this block, and install
the new key on every client; checkpoints saved under the old key no longer load.

Keep the host directory `checkpoints-v013`, mounted at `/checkpoints-v013`; keep the v0.12.x
`checkpoints` store untouched for historical recovery. The retained profile/store names do not
establish cross-binary checkpoint compatibility. Never import prior generations; resume earlier
sessions by replaying the authoritative client transcript for a fresh prefill. New exact-runtime
checkpoints accelerate later continuations. All three beta.3 runtime qualifications cover
JSON-schema structured output and 128-character Chat/Responses tool names, and fresh v0.15.0
product-route acceptance passed across all five routes. See the [v0.15.0 compatibility matrix](../releases/v0.15.0/COMPATIBILITY.md).

## 4. Start NInfer on the inference host

```sh
./examples/manual-tunnel/start-ninfer.sh \
  --model "$MODEL" \
  --api-key-file "$STATE/api-key" \
  --log-dir "$LOGS" \
  --checkpoint-dir "$CHECKPOINTS"
```

The `qwen38-5090-v0.13.0` profile read by `start-ninfer.sh` passes `--session-checkpoint-require-origin-auth`
and config `751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47`.
The flag needs a configured checkpoint root and an API key of at least 32 bytes. The
`openssl rand -hex 32` step above generates 64 characters; the fresh schema 3 directory
has no MAC-less generations. Do not remove the flag to accept an unauthenticated import.

`start-ninfer.sh` verifies the ready manifest, profile configuration hash, digest-pinned image,
model, and `ninfer-serve` binary, probes the GPU inside the container, and starts `omp-ninfer-beta`
(`--restart no`, capabilities dropped, `no-new-privileges`, hash-pinned `io_uring` seccomp) on
`127.0.0.1:18089` with the model and API key mounted read-only (visible to root inside the trusted
host boundary). Sessions above 32,768 frontier tokens (or saved via `POST /v1/ninfer/checkpoints`)
persist in the local `O_DIRECT` checkpoint directory. A failed container stays for
`docker logs omp-ninfer-beta`. To stop the container (keeping the model, key, logs, and checkpoints)
or recover after a host reboot ([Troubleshooting](TROUBLESHOOTING.md#the-container-exists-but-will-not-start-after-a-host-reboot)),
run `stop-ninfer.sh` and then `start-ninfer.sh`:

```sh
./examples/manual-tunnel/stop-ninfer.sh
```

## 5. Open the tunnel from the Mac

```sh
./examples/manual-tunnel/open-tunnel.sh USER@RUNTIME_HOST
```

Use the inference host's SSH user and host (on Windows 11 with Docker Desktop, the Windows account
and stock OpenSSH server forwarding `127.0.0.1:18089`) and keep the process running.

**Optional managed tunnel (preview):** after completing the key and provider setup below,
close your manual tunnel and run `python3 scripts/mac_tunnel.py install --destination USER@RUNTIME_HOST`,
then `python3 scripts/mac_tunnel.py start`. This first-party helper replaces only the
foreground SSH process, not the client installer or inference-host service. It installs
`~/Library/LaunchAgents/com.alphastorm.omp-ninfer.tunnel.plist` and an owner-private helper/config
under `~/Library/Application Support/omp-ninfer/tunnel`. Install leaves the agent disabled;
start enables it now and at future GUI logins. A stable Python 3 installation must remain at
the interpreter path used during install. Reinstall after moving or upgrading that interpreter.

Use an explicit SSH user and hostname/IP, not a configuration alias. The helper deliberately
ignores SSH configuration to prevent inherited forwards or proxy commands. Verify the host
key interactively first using the same destination and ensure unattended public-key login works;
`--identity-file PATH` references an existing SSH private key without copying it. No passwords,
SSH keys or bearer tokens are placed in the plist, status or configuration JSON. The existing
`~/.omp/agent/ninfer-beta.key` is referenced only for doctor; `--key-file PATH` selects a different
existing bearer file. Host-key verification and batch authentication fail closed.

Run `python3 scripts/mac_tunnel.py status` for JSON launchd/listener state and
`python3 scripts/doctor.py --mac-tunnel --json` (or `python3 scripts/mac_tunnel.py doctor`)
for an authenticated loopback endpoint check. `--offline` on either doctor skips launchd and
network probes. Status snapshots are written to the private installation's `status.json`;
`runtime.json` records the supervisor's current attempt/backoff. Neither is release
qualification. SSH retries use 1–60 second exponential backoff, resetting after a connection
survives 60 seconds; launchd also restarts the supervisor. The endpoint can remain unavailable
while SSH is connected, for example while the model loads.

`python3 scripts/mac_tunnel.py stop` disables future login starts and unloads the owned agent.
`python3 scripts/mac_tunnel.py uninstall` also removes its installed files, leaving the existing
bearer, SSH identity and OMP configuration untouched. The documented client URL and fail-closed
configuration remain unchanged. Nondefault `--local-port`, `--remote-port` and `--ssh-port`
are for owner-controlled rehearsal/candidate endpoints, not a change to the documented route.
Managed lifecycle remains preview: a rehearsal stub proves wiring, not RTX 5090 inference,
Windows forwarding or release acceptance.

## 6. Install the same key on the Mac

In another Mac terminal, or the WSL2 Linux client's shell, stream the key over SSH from the login
shell or the `Ubuntu-24.04` WSL2 distro (on Windows, the first branch prints one harmless
`cannot find the path` line):

```sh
install -d -m 700 "$HOME/.omp/agent"
umask 077
ssh USER@RUNTIME_HOST 'sh -lc "cat ~/.config/omp-ninfer/api-key" 2>/dev/null || wsl.exe -d Ubuntu-24.04 -- sh -lc "cat ~/.config/omp-ninfer/api-key"' \
  | tr -d '\r' > "$HOME/.omp/agent/ninfer-beta.key"
chmod 600 "$HOME/.omp/agent/ninfer-beta.key"
test "$(wc -c < "$HOME/.omp/agent/ninfer-beta.key")" -gt 32
```

Do not paste the key into YAML, shell history, issues, or support bundles.

## 7. Add the OMP provider

Install the per-model fragment as `~/.omp/agent/models.yml`. A rerun leaves an identical file in
place, and the block refuses to replace a `models.yml` that differs:

```sh
unset PI_OPENAI_STATEFUL
if [ ! -e "$HOME/.omp/agent/models.yml" ]; then
  install -m 600 examples/manual-tunnel/models.fragment.yml "$HOME/.omp/agent/models.yml"
elif ! cmp -s examples/manual-tunnel/models.fragment.yml "$HOME/.omp/agent/models.yml"; then
  echo 'existing ~/.omp/agent/models.yml differs; merge providers.ninfer-beta instead of overwriting it' >&2; false
fi
```

The server hashes OMP's `prompt_cache_key` into the session identity, `compat.statefulResponses: true`
chains turns with `previous_response_id`, encrypted reasoning and summaries stay off, and effort
clamps within `low`, `medium`, and `xhigh`. If the block refused an existing `models.yml`, merge
only `providers.ninfer-beta` from
[`models.fragment.yml`](../examples/manual-tunnel/models.fragment.yml):

```yaml
apiKey: '!cat "$HOME/.omp/agent/ninfer-beta.key"'
```

For the macOS/Linux shell route, install the fail-closed default config the same way. If the block
refuses an existing `config.yml`, merge
[`fail-closed.yml`](../examples/manual-tunnel/fail-closed.yml) into it:

```sh
if [ ! -e "$HOME/.omp/agent/config.yml" ]; then
  install -m 600 examples/manual-tunnel/fail-closed.yml "$HOME/.omp/agent/config.yml"
elif ! cmp -s examples/manual-tunnel/fail-closed.yml "$HOME/.omp/agent/config.yml"; then
  echo 'existing ~/.omp/agent/config.yml differs; merge fail-closed.yml instead of overwriting it' >&2; false
fi
```

### Native Windows OMP

Native Windows OMP does not support `!cat`; copy or merge `providers.ninfer-beta` from
[`examples/windows-docker-local/models.fragment.yml`](../examples/windows-docker-local/models.fragment.yml),
install the fail-closed config, and load the key in the current PowerShell process. A rerun leaves
identical files in place, and the block refuses to replace a `models.yml` or `config.yml` that
differs:

```powershell
$Agent = Join-Path $HOME '.omp\agent'
New-Item -ItemType Directory -Force -Path $Agent | Out-Null
$KeyPath = Join-Path $Agent 'ninfer-beta.key'
$KeyText = (& wsl.exe -d Ubuntu-24.04 -- bash -lc 'cat "$HOME/.config/omp-ninfer/api-key"' | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($KeyText)) { throw 'NInfer key copy from WSL2 failed' }
[IO.File]::WriteAllText($KeyPath, $KeyText, [Text.UTF8Encoding]::new($false))
$Identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $KeyPath /inheritance:r /grant:r "${Identity}:(R,W)" | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'NInfer key ACL restriction failed' }

$env:NINFER_BETA_API_KEY = (Get-Content -Raw $KeyPath).Trim()
Remove-Item Env:PI_OPENAI_STATEFUL -ErrorAction SilentlyContinue
$ModelsPath = Join-Path $Agent 'models.yml'
$ConfigPath = Join-Path $Agent 'config.yml'
$ModelsSource = '.\examples\windows-docker-local\models.fragment.yml'
$ConfigSource = '.\examples\manual-tunnel\fail-closed.yml'
if ((Test-Path $ModelsPath) -and (Get-FileHash $ModelsPath).Hash -cne (Get-FileHash $ModelsSource).Hash) {
  throw "Existing $ModelsPath differs; merge providers.ninfer-beta instead of overwriting it."
}
if ((Test-Path $ConfigPath) -and (Get-FileHash $ConfigPath).Hash -cne (Get-FileHash $ConfigSource).Hash) {
  throw "Existing $ConfigPath differs; merge fail-closed.yml instead of overwriting it."
}
if (-not (Test-Path $ModelsPath)) { Copy-Item $ModelsSource $ModelsPath }
if (-not (Test-Path $ConfigPath)) { Copy-Item $ConfigSource $ConfigPath }
```

The key and stateful setting are loaded before either merge refusal. If a file differs, merge
only the named provider or fail-closed settings, then continue in this same PowerShell process.
The environment variable lives only in that PowerShell process (`& "$env:LOCALAPPDATA\OMP\omp.exe" --model ninfer-beta/q38-ninfer`
opens an interactive session). Always pass an explicit provider/model so outages fail closed.

## 8. Acceptance

### Native Windows command forms

Run from the tagged clone in the same PowerShell process that loaded `NINFER_BETA_API_KEY`:

```powershell
$Launcher = "$env:LOCALAPPDATA\OMP\omp.exe"
$Smoke = Join-Path $env:TEMP ("omp-ninfer-acceptance-" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $Smoke | Out-Null
Set-Content -NoNewline -Encoding ascii -Path (Join-Path $Smoke 'marker.txt') -Value 'OMP_NINFER_TOOL_OK'
Push-Location $Smoke
try {
  & $Launcher -p --no-session --auto-approve --model ninfer-beta/q38-ninfer `
    'Use a file-reading tool to read marker.txt, then report its exact single line.'
  if ($LASTEXITCODE -ne 0) { throw 'text/tool acceptance failed' }
} finally { Pop-Location }

$Image = (Resolve-Path .\assets\icon-512.png).Path
& $Launcher -p --no-session --auto-approve --model ninfer-beta/q38-ninfer `
  ("@" + $Image) 'Describe the visible image in one sentence.'
if ($LASTEXITCODE -ne 0) { throw 'Vision acceptance failed' }

$Session = Join-Path $Smoke 'sessions'
& $Launcher -p --auto-approve --session-dir $Session --model ninfer-beta/q38-ninfer `
  'Remember the nonce 493817-205361 for my next turn. Reply OK only.'
if ($LASTEXITCODE -ne 0) { throw 'state setup failed' }
& $Launcher -p --auto-approve --session-dir $Session --continue `
  'Return the exact nonce from the prior turn verbatim, character for character. Do not correct or change its spelling. Return nothing else.'
if ($LASTEXITCODE -ne 0) { throw 'stateful resume failed' }
```

For the fail-closed check, stop the owned runtime from the tagged WSL2 clone, then issue one
native Windows request:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc 'cd ~/omp-ninfer && ./examples/manual-tunnel/stop-ninfer.sh'
if ($LASTEXITCODE -ne 0) { throw 'NInfer stop failed' }
& $Launcher -p --no-session --auto-approve --max-time 20s `
  --model ninfer-beta/q38-ninfer 'Return LOCAL_ONLY.'
if ($LASTEXITCODE -eq 0) { throw 'outage request unexpectedly succeeded' }
$global:LASTEXITCODE = 0
```

Expected result: a connection/authentication failure and no model response. Any cloud-provider
request is a release failure. Restart NInfer with section 4 only after observing the failure.

### macOS/Linux command forms

Run these in the terminal that installed the per-model fragment in section 7, with the tunnel
from section 5 open in another for macOS. The [WSL2 loopback route](#wsl2-linux-client-over-local-loopback)
needs no tunnel and uses its own runtime-stop outage check instead of **Fail closed** below.
Every check is a `-p` (print) turn, so it exits on its own; the shell tests the outcome, and
`set -e` stops the sequence at the first failure.

### Text and tool turn

```sh
set -e
SMOKE=$(mktemp -d)
printf 'OMP_NINFER_TOOL_OK\n' > "$SMOKE/marker.txt"
cd "$SMOKE"
omp -p --no-session --auto-approve --model ninfer-beta/q38-ninfer \
  "Use a file-reading tool to read marker.txt, then report its exact single line." \
  | tee "$SMOKE/tool.txt"
grep -q OMP_NINFER_TOOL_OK "$SMOKE/tool.txt"
```

The turn must use the local model and execute the file-reading tool; the `grep` is the contract,
not the model's wording around it.

### Image input

The release clone ships a non-sensitive image; adjust the path to your clone:

```sh
omp -p --no-session --auto-approve --model ninfer-beta/q38-ninfer \
  @"$HOME/omp-ninfer/assets/icon-512.png" "Describe the visible image in one sentence." \
  | tee "$SMOKE/vision.txt"
test -s "$SMOKE/vision.txt"
```

A completed response proves the configured Vision route is reachable; this check belongs to the
RTX 5090 container lane only. Do not use private screenshots in an issue.

### Stateful follow-up and OMP resume

```sh
omp -p --auto-approve --session-dir "$SMOKE/sessions" --model ninfer-beta/q38-ninfer \
  "Remember the nonce 493817-205361 for my next turn. Reply OK only."
omp -p --auto-approve --session-dir "$SMOKE/sessions" --continue \
  "Return the exact nonce from the prior turn verbatim, character for character. Do not correct or change its spelling. Return nothing else." | tee "$SMOKE/resume.txt"
grep -q 493817-205361 "$SMOKE/resume.txt"
```

The transcript remains authoritative. This checks OMP exit and resume with NInfer stateful
Responses while the server process stays up; the next check takes it down.

### Session survives the server process

Sessions above 32,768 frontier tokens checkpoint automatically under OMP's `prompt_cache_key`
digest. This check seeds ~64,000 tokens from the first 200,000 ASCII bytes of the release docs
(above the 32,768-token gate and below OMP's 111,412-token auto-compaction threshold), strips lines
containing the nonce digits, restarts the container, and resumes:

```sh
cat "$HOME/omp-ninfer/docs/BENCHMARKS.md" "$HOME/omp-ninfer/README.md" \
    "$HOME/omp-ninfer/docs/ARCHITECTURE.md" "$HOME/omp-ninfer/docs/PERFORMANCE.md" \
    "$HOME/omp-ninfer/CHANGELOG.md" | LC_ALL=C tr -cd '\11\12\40-\176' | grep -v 493817 > "$SMOKE/docs.txt"
head -c 200000 "$SMOKE/docs.txt" > "$SMOKE/context.md"
omp -p --auto-approve --session-dir "$SMOKE/durable" --model ninfer-beta/q38-ninfer \
  @"$SMOKE/context.md" "Hold this material in context. Remember the nonce 493817-205361. Reply OK only."
ssh USER@RUNTIME_HOST docker restart --timeout 60 omp-ninfer-beta
until curl -sf -m 3 -o /dev/null http://127.0.0.1:18089/health; do sleep 3; done
omp -p --auto-approve --session-dir "$SMOKE/durable" --continue \
  "Return the exact nonce I asked you to remember verbatim, character for character. Do not correct or change its spelling. Return nothing else." | tee "$SMOKE/durable.txt"
grep -q 493817-205361 "$SMOKE/durable.txt"
```

Use the SSH destination from section 5. The restored checkpoint returns the planted nonce and
refuses altered payloads; unsaved turns below the 32,768-token gate or lost to a crash or power
loss are replayed from the OMP transcript.

### Fail closed

Stop the tunnel with `Ctrl-C` in its terminal, then run:

```sh
if omp -p --no-session --max-time 20s --model ninfer-beta/q38-ninfer "Return LOCAL_ONLY."; then
  echo 'outage request unexpectedly succeeded' >&2; false
fi
```

Expected result: a connection failure and no model response, so the block ends without the
message. Any cloud-provider request is a release failure. Restart the tunnel only after observing
the failure.

## Fleet: legacy multi-lane configuration

The RTX 5090/RTX 4090 single-GPU fleet recipe belongs to the
[immutable v0.10.0 guide](https://github.com/alphastorm/omp-ninfer/blob/v0.10.0/docs/QUICKSTART.md#fleet-the-two-qualified-lanes-in-one-omp-configuration)
and does not qualify a cross-release fleet or concurrent native serving in v0.15.0.

## Replicating sessions off the machine

Checkpoints are immutable, SHA-manifested generations under a local root (`O_DIRECT` and
DirectStorage require a local filesystem; a network share is a replica target only). Use
[`scripts/checkpoint_sync.py`](../scripts/checkpoint_sync.py) to export and import verified
generations across machines sharing the exact runtime binary, model, profile, and bearer key:

```sh
# on the inference host, with the checkpoint root the server was started with
python3 scripts/checkpoint_sync.py export --root <checkpoint-root> --destination <replica-root> --receipt export.json
# later, on the same profile (same binary and configuration identity), before the restore
python3 scripts/checkpoint_sync.py import --source <replica-root> --root <checkpoint-root> --receipt import.json
```

`checkpoint_sync.py` verifies every manifest-listed file by size and SHA-256, stages outside
runtime-scanned directories, and publishes the session's `current` pointer last. Each generation's
`manifest.mac` is an HMAC keyed by the lane's bearer key; pass `--allow-unauthenticated` only for
legacy local checkpoints, never to bypass the release policy. Both the `qwen38-5090-v0.13.0`
container profile and the `qwen38-4090-native-v0.7.0-beta.3` /
`qwen38-3090-native-v0.7.0-beta.3` native profiles start with
`--session-checkpoint-require-origin-auth` (32-byte bearer floor) so unauthenticated or altered
generations are refused at load. They do not migrate prior checkpoint stores.

For bulk transfer over high-latency or Windows-to-Windows links where single-stream `scp` stalls,
use [`scripts/hosts/pscp.py`](../scripts/hosts/pscp.py) (verifies whole-file SHA-256 on both ends):

```sh
# one end is not Windows: N ranged reads over independent ssh connections
python3 scripts/hosts/pscp.py pull --host <host> --platform posix --remote <path> --local <path>
# both ends are Windows: bearer-token ranged HTTP over the tailnet
python3 scripts/hosts/pscp.py serve --local <archive>            # prints port + token, then exits
python3 scripts/hosts/pscp.py fetch --url http://<host>:<port> --token <token> --local <archive>
```

When archiving out of WSL through `/mnt/c`, pass `tar -b 8192`. See
[Facts](FACTS.md#checkpoint-transport-and-nas-replication) for measured LAN NAS and cross-site
replication timings.

## 9. Send feedback

Report outcomes using the matching issue form —
[clean-install report](https://github.com/alphastorm/omp-ninfer/issues/new?template=clean-install-report.yml),
[hardware qualification report](https://github.com/alphastorm/omp-ninfer/issues/new?template=hardware-report.yml),
[installation failure](https://github.com/alphastorm/omp-ninfer/issues/new?template=installation-failure.yml),
or [performance result](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml).
Include release and profile IDs, OS, GPU, VRAM, driver, Docker, and OMP versions, install-to-first-turn
time and manual steps (for clean installs), the failing step and content-safe error, and whether the
route was fresh, resumed, or tunnel-disconnected. Never attach API keys, usernames, hostnames, IP
addresses, private paths, prompts, model output, raw request logs, or Docker inspection dumps; see
[Troubleshooting](TROUBLESHOOTING.md) first.
