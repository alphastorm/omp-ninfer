# Quickstart

> **Versioned guide: v0.13.1 · stock Oh My Pi 18.12.6 · Qualified on RTX 5090 · 4090 · 3090**

OMP NInfer is the qualified local inference appliance and release layer connecting the
[Oh My Pi](https://github.com/can1357/oh-my-pi) (OMP) coding-agent client over authenticated
loopback to the NInfer inference engine serving Qwen3.8 27B on your GPU.

## Choose your lane

| GPU and host | Client route in v0.13.1 | Start here |
| --- | --- | --- |
| RTX 5090 container on Windows 11 + Docker Desktop / WSL2 | Native Windows x64 client over local loopback `127.0.0.1:18089` | [RTX 5090 Windows route](#ready-route-native-windows-and-docker-desktop-wsl2) |
| RTX 5090 container on Windows 11 / WSL2 or Linux | macOS arm64 client over a manual SSH tunnel (preview) | [macOS manual SSH route (preview)](#macos-client-over-a-manual-ssh-tunnel-preview) |
| RTX 4090 native Windows 11 (alone or beside RTX 3090) | Native Windows x64 client over local loopback `127.0.0.1:18082`; UUID-bound; first-of-lineage rollback `not_applicable` | [RTX 4090 native lane](#native-windows-rtx-4090-release-lane) |
| RTX 3090 native Windows 11 (alone or beside RTX 4090) | Native Windows x64 client over local loopback `127.0.0.1:18082`; UUID-bound; first-of-lineage rollback `not_applicable` | [RTX 3090 native lane](#native-windows-rtx-3090-release-lane) |
| RTX 5090 container with Linux x64 client under WSL2 only | WSL2 shell client over local loopback `127.0.0.1:18089` (no native Linux OS qualification) | [Host setup](#3-prepare-the-model-and-key-on-the-inference-host), [OMP provider](#7-add-the-omp-provider), and [shell checks](#macoslinux-command-forms) |
| Other GPU, non-WSL Linux client, or concurrent native serving | Unsupported | [Compatibility boundary](COMPATIBILITY.md) |

## Before you start

- **Clone the tag and run the ready gate:** start from a clean clone of `v0.13.1` and verify
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
`python3 scripts/client_acceptance.py --omp ./omp-darwin-arm64 --omp-sha256 SHA256 --omp-version omp/18.12.6 --local-rehearsal --receipt rehearsal.json`,
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

## OMP 18.12.6 client

Release `v0.13.1` pins unmodified upstream
[Oh My Pi v18.12.6](https://github.com/can1357/oh-my-pi/releases/tag/v18.12.6) (source
`45c35e40c46166dc726ccc52f5d27f40f2449f99`, tree `8a90a1b48b370649bd3f026d5f609e500626785c`),
carried unchanged from `v0.13.0`.
Exact binary URLs, sizes, and SHA-256 pins (`omp-windows-x64.exe` `73d73c11…`,
`omp-linux-x64` `85d9daf3…`, `omp-darwin-arm64` `cfbb5e38…`) are in the
[v0.13.1 release notes](../releases/v0.13.1/NINFER_RELEASE_NOTES.md) and
[`releases/v0.13.1/qualification/client-components.json`](../releases/v0.13.1/qualification/client-components.json).
The [client upgrade review](measurements/2026-10-25-omp-18126-client-upgrade-review.json) records
the host-free checks across the Responses wire contract, image-aware snapcompact gate, and
print-mode slash dispatch.
When migrating from an earlier client:

- **Per-model stateful Responses:** set `compat.statefulResponses: true` on each NInfer model in
  `~/.omp/agent/models.yml`.
- **Remove `PI_OPENAI_STATEFUL`:** clear it from scripts, profiles, and environments
  (`unset PI_OPENAI_STATEFUL` or `Remove-Item Env:PI_OPENAI_STATEFUL -ErrorAction SilentlyContinue`);
  an inherited `0` overrides per-model `compat` and disables chaining.
- **Remove the image-detail override:** delete `compat.supportsImageDetailOriginal: false` from
  older RTX 5090 fragments; stock OMP defaults custom Responses endpoints to `detail: "auto"`.
- **Keep fail-closed config, concurrency limits, and default compaction:** install or merge
  [`examples/manual-tunnel/fail-closed.yml`](../examples/manual-tunnel/fail-closed.yml) so retries,
  cloud fallback, and startup update checks stay off, `providers.maxInFlightRequests` keeps
  `ninfer-beta` / `ninfer-main` at `2` and `ninfer-native-4090` / `ninfer-heavy` /
  `ninfer-native-3090` at `1`, and compaction stays at OMP's default.

## Acceptance evidence

Fresh client, route, native public-install and independent restoration acceptance passed on
frozen candidate `92dfb13285994f1527711cf464847f07e44613dd`. Client acceptance is never
inherited; no predecessor product receipt is relabeled.

| Documented route | Fresh acceptance |
| --- | --- |
| RTX 5090 Windows 11 + Docker Desktop/WSL2 host | 2/2 blocks passed |
| macOS arm64 client over manual SSH tunnel | 10/10 passed; platform remains preview |
| Windows x64 client over RTX 5090 loopback | 5/5 passed |
| Native RTX 4090 on the two-GPU host | 7/7 blocks passed (19/19 route-behavior checks); first-release rollback `not_applicable` |
| Native RTX 3090 on the two-GPU host | 7/7 blocks passed (19/19 route-behavior checks); first-release rollback `not_applicable` |

All three newly downloaded stock clients passed runtime-bound typed tool/result, exact
continuation, and unavailable-route fail-closed checks. Linux ran under WSL2, not a separately
qualified native Linux OS. Image input passed on macOS and Windows against RTX 5090 only; there is
no native-lane or Linux vision claim. Both canonical beta.2 native roots were freshly installed
from the documented blocks after preserving their old lineages. The later public-URL checks
verified the exact assets and returned `already_installed`; both rebased lineages have no
predecessor and zero rollback directions.

Independent restoration passed for the RTX 5090 incumbent (image, mounts, health, restart policy,
checkout, key, and directory presence; 429.388 s window) and for both sequential native baselines
(state, ACLs, tasks, holds, client files, power, directory presence, and documented staging).
Production was not upgraded during the acceptance window.
[Documented routes](../releases/v0.13.1/acceptance/documented-routes.json) and
[composed acceptance](../releases/v0.13.1/acceptance/composed-external-installation.json) bind all
31 executable route blocks; only guide prose changed after execution. These are
owner-operated tester-equivalent observations, not independent external-user outcomes. See
[Releases](RELEASES.md).

## Current release at a glance

| Lane | Runtime component and source | Model artifact | Serving profile and limits |
| --- | --- | --- | --- |
| RTX 5090 container (`127.0.0.1:18089`) | `v0.7.0-qwen38-5090-beta.2`, source `6d4d0a05` on upstream `64d10fbf`, server `9790a004`, image `5d10a998` | `81f924d4` (20,437,521,664 bytes) | `qwen38-5090-v0.13.0` (config `751d22dc`): mandatory strict origin auth, DFlash2 K=7, BF16 KV (146,368 automatic tokens), 131,072 context, two active requests plus two extra device-state slots, shared Host budget, 180 s pending timeout; JSON-schema output, 128-character tool names, text, tools, vision, preserved thinking |
| RTX 4090 native Windows (`127.0.0.1:18082`) | `v0.7.0-qwen38-4090-beta.2`, source `7a25cd72` on upstream `64d10fbf`, package `ffaa410a`, server `cfc3e066` | `81f924d4` (20,437,521,664 bytes) | `qwen38-4090-native-v0.7.0-beta.2` (public config `b21cdaf8`): mandatory strict origin auth, MTP3/INT8, 131,072 context, C1, 30 s pending timeout, two extra slots, 2,048-token prefill, shared Host budget, 640 MiB admission headroom; JSON-schema output, 128-character tool names, text/tools (no vision or DFlash2) |
| RTX 3090 native Windows (`127.0.0.1:18082`) | `v0.7.0-qwen38-3090-beta.2`, source `7a25cd72` on upstream `64d10fbf`, package `626ba6ff`, server `cdd24c5e` | `81f924d4` (20,437,521,664 bytes) | `qwen38-3090-native-v0.7.0-beta.2` (public config `b49aad99`): mandatory strict origin auth, MTP3/INT8, 131,072 context, C1, 30 s pending timeout, four extra slots, 1,024-token prefill, shared Host budget, 768 MiB admission headroom, 300 W policy; JSON-schema output, 128-character tool names, text/tools (no vision or DFlash2) |


- **Serving limits and compaction:** RTX 5090 admits two requests at once and holds a pending
  request for up to 180 s (`--pending-timeout-ms 180000`) when both prompts plus output reservations
  do not fit its 146,368-token automatic KV pool (upgrade an older one-at-a-time RTX 5090 server before
  raising its OMP limit). Native lanes serve one request at a time with a 30 s pending timeout;
  keeping their OMP limit at `1` lets turns wait in OMP during background compaction instead of
  expiring at the server
  ([troubleshooting](TROUBLESHOOTING.md#a-turn-fails-with-request_queue_timeout-late-in-a-long-session)).
- **Native two-GPU UUID topology and rollback:** Both native packages bind their GPU UUID and PCI
  address on a two-GPU Windows 11 host and serve sequentially on port `18082`. Both rebased native
  lineages (`v0.7.0-qwen38-4090-beta.2` and `v0.7.0-qwen38-3090-beta.2`) are the first release of
  their `64d10fbf` / model v3 lineage (`not_applicable`, zero rollback directions); the old RTX
  3090 `v0.6.2` two-direction result does not transfer across the model and runtime rebase.
  Preserve prior native release roots separately for historical recovery.
- **Checkpoints and legacy routes:** Stock OMP names each session with `prompt_cache_key`, which the
  authenticated runtime hashes into the session identity. Checkpoints restore across graceful
  restarts on all three lanes, but saves are best effort under traffic (a crash or expired wait can
  lose unsaved work; universal warm reuse is not promised) and restore requires the same runtime
  binary, model, profile, and bearer key. Single-GPU native owners staying on `v0.10.0` use the
  [immutable v0.10.0 guide](https://github.com/alphastorm/omp-ninfer/blob/v0.10.0/docs/QUICKSTART.md);
  the older RTX 3090 `v0.2` lineage on the OMP 18.0.9 fork client remains in the
  [historical v0.7.2 guide](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md).
- **Session capability boundary:** Within one API-key principal, prompt_cache_key names a session capability; use unique high-entropy keys and do not share that principal among mutually untrusted clients.
- **Native protocol and checkpoint gates:** Both rebased native lanes qualify Chat and Responses
  JSON-schema structured output, 128-character tool names, status endpoint schema 2, and request-log
  schema 30. The package server-config (schema 4) uses
  `cache/<release-instance-id>/session-checkpoints-v3` (where `<release-instance-id>` is the
  installed release ID such as `qwen38-4090-native-v0.7.0-beta.2-7a25cd72f490`), not the old native
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
git clone --branch v0.13.1 --depth 1 https://github.com/alphastorm/omp-ninfer.git
Set-Location omp-ninfer
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
py -3 scripts\verify_release.py --require-ready
```

### Install the exact native Windows client

```powershell
$ErrorActionPreference = 'Stop'
$Url = 'https://github.com/can1357/oh-my-pi/releases/download/v18.12.6/omp-windows-x64.exe'
$Expected = '73d73c11dc8821cf939441a964992aefc9c5b0d5a4418e9e8985a46439b60eef'
Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile omp-windows-x64.exe
if ((Get-FileHash omp-windows-x64.exe -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Expected) { throw 'OMP binary checksum mismatch' }
$Launcher = "$env:LOCALAPPDATA\OMP\omp.exe"
New-Item -ItemType Directory -Force -Path (Split-Path $Launcher) | Out-Null
Copy-Item .\omp-windows-x64.exe $Launcher -Force
Remove-Item Env:PI_OPENAI_STATEFUL -ErrorAction SilentlyContinue
& $Launcher --version
if ($LASTEXITCODE -ne 0) { throw 'OMP version check failed' }
```

The client version must be `omp/18.12.6` (to roll back, verify the previous pinned binary's
checksum before replacing `omp.exe`). Inside WSL2, run **3. Prepare the model and key** and
**4. Start NInfer** below, skip sections 5–6 (Docker Desktop exposes `127.0.0.1:18089` to native
Windows), then run **Native Windows OMP** in section 7 and **Native Windows command forms** in
section 8.

## Native Windows RTX 4090 release lane

Requires Windows 11 x64, one RTX 4090 (sm_89), a supported NVIDIA driver, Git, PowerShell, Python 3
(`py` launcher), and 40 GiB free disk. The installer binds the unique RTX 4090 UUID and PCI address
even beside an RTX 3090 (use `-GpuUuid` if multiple RTX 4090 cards exist; never hide a card). Stop
the other native lane on port `18082` first. This rebased package is the first release of its
lineage on `64d10fbf` (`not_applicable`, zero rollback directions); keep prior native release roots
untouched for historical recovery.

```powershell
git clone --branch v0.13.1 --depth 1 https://github.com/alphastorm/omp-ninfer.git
Set-Location omp-ninfer
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
py -3 scripts\verify_release.py --require-ready
```

```powershell
$VariantId = 'rtx4090-windows-native'
```

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
$ErrorActionPreference = 'Stop'
$Manifest = Get-Content .\releases\v0.13.1\manifest.json -Raw | ConvertFrom-Json
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

```powershell
$Provider = if ($VariantId -ceq 'rtx4090-windows-native') { 'ninfer-native-4090' } else { 'ninfer-native-3090' }
$Agent = Join-Path $HOME '.omp\agent'
New-Item -ItemType Directory -Force -Path $Agent | Out-Null
$ModelsPath = Join-Path $Agent 'models.yml'
$ConfigPath = Join-Path $Agent 'config.yml'
if ((Test-Path $ModelsPath) -or (Test-Path $ConfigPath)) {
  throw "Existing OMP models/config found; merge providers.$Provider and the retry mapping instead of overwriting them."
}
Copy-Item .\examples\windows-native\models.fragment.yml $ModelsPath
Copy-Item .\examples\manual-tunnel\fail-closed.yml $ConfigPath
$env:NINFER_NATIVE_API_KEY = (Get-Content -Raw $ApiKeyFile).Trim()
Remove-Item Env:PI_OPENAI_STATEFUL -ErrorAction SilentlyContinue
```


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
& $Launcher -p --no-session --auto-approve --max-time 20s `
  --model "$Provider/qwen3.8-27b" 'Return LOCAL_ONLY.'
if ($LASTEXITCODE -eq 0) { throw 'outage request unexpectedly succeeded' }
& $Controller -Action Start -StateRoot $StateRoot | Out-Null
```


## Native Windows RTX 3090 release lane

Requires Windows 11 x64, one RTX 3090 (sm_86), a supported NVIDIA driver, Git, PowerShell, Python 3
(`py` launcher), and 40 GiB free disk. The installer binds the card's UUID and PCI address even
beside an RTX 4090 (use `-GpuUuid` if multiple RTX 3090 cards exist). Stop the other native lane on
port `18082` first. This rebased package is the first release of its lineage on `64d10fbf`
(`not_applicable`, zero rollback directions); the old `v0.6.2` rollback result does not carry to
the new model and runtime.

```powershell
git clone --branch v0.13.1 --depth 1 https://github.com/alphastorm/omp-ninfer.git
Set-Location omp-ninfer
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
py -3 scripts\verify_release.py --require-ready
```

```powershell
$VariantId = 'rtx3090-windows-native'
```

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
$ErrorActionPreference = 'Stop'
$Manifest = Get-Content .\releases\v0.13.1\manifest.json -Raw | ConvertFrom-Json
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

```powershell
$Provider = 'ninfer-native-3090'
$Agent = Join-Path $HOME '.omp\agent'
New-Item -ItemType Directory -Force -Path $Agent | Out-Null
$ModelsPath = Join-Path $Agent 'models.yml'
$ConfigPath = Join-Path $Agent 'config.yml'
if ((Test-Path $ModelsPath) -or (Test-Path $ConfigPath)) {
  throw "Existing OMP models/config found; merge providers.$Provider and the retry mapping instead of overwriting them."
}
Copy-Item .\examples\windows-native\models-rtx3090.fragment.yml $ModelsPath
Copy-Item .\examples\manual-tunnel\fail-closed.yml $ConfigPath
$env:NINFER_NATIVE_API_KEY = (Get-Content -Raw $ApiKeyFile).Trim()
Remove-Item Env:PI_OPENAI_STATEFUL -ErrorAction SilentlyContinue
```


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
& $Launcher -p --no-session --auto-approve --max-time 20s `
  --model "$Provider/q38-ninfer" 'Return LOCAL_ONLY.'
if ($LASTEXITCODE -eq 0) { throw 'outage request unexpectedly succeeded' }
& $Controller -Action Start -StateRoot $StateRoot | Out-Null
```

## macOS client over a manual SSH tunnel (preview)

The macOS arm64 client is a preview platform (stock upstream binary over a manual OpenSSH loopback
tunnel, without a managed macOS installer or appliance service); all 10 executable blocks in this
route are accepted against the qualified RTX 5090 container lane. Sections 3 and 4 also serve as
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

```sh
git clone --branch v0.13.1 --depth 1 \
  https://github.com/alphastorm/omp-ninfer.git
cd omp-ninfer
python3 scripts/verify_release.py --require-ready
```

## 2. Install the OMP beta on the Mac

Despite the retained heading, this installs the stock Oh My Pi 18.12.6 binary (`omp-darwin-arm64`):

```sh
(
set -euo pipefail
URL='https://github.com/can1357/oh-my-pi/releases/download/v18.12.6/omp-darwin-arm64'
EXPECTED='cfbb5e38cd8f8a3be55e710700be587d287deaacdc58c9b0a661c5086bccfe58'
curl --fail --location --output omp-darwin-arm64 "$URL"
test "$(shasum -a 256 omp-darwin-arm64 | cut -d ' ' -f 1)" = "$EXPECTED"
mkdir -p "$HOME/.local/bin"
cp omp-darwin-arm64 "$HOME/.local/bin/omp"
chmod 0755 "$HOME/.local/bin/omp"
unset PI_OPENAI_STATEFUL
"$HOME/.local/bin/omp" --version
)
```

The version must be `omp/18.12.6`; add `$HOME/.local/bin` to `PATH` before continuing.

## 3. Prepare the model and key on the inference host

```sh
ROOT="$HOME/.local/share/omp-ninfer"
STATE="$HOME/.config/omp-ninfer"
LOGS="$HOME/.local/state/omp-ninfer"
CHECKPOINTS="$ROOT/checkpoints-v013"
install -d -m 700 "$ROOT" "$STATE" "$LOGS" "$CHECKPOINTS"

MODEL_URL=$(python3 -c \
  'import json; print(json.load(open("releases/v0.13.1/manifest.json"))["components"]["model"]["artifact_url"])')
MODEL_BYTES=$(python3 -c \
  'import json; print(json.load(open("releases/v0.13.1/manifest.json"))["components"]["model"]["artifact_bytes"])')
MODEL_SHA256=$(python3 -c \
  'import json; print(json.load(open("releases/v0.13.1/manifest.json"))["components"]["model"]["artifact_sha256"])')
MODEL="$ROOT/qwen3_8_27b-v3.ninfer"

# a rerun with a complete file gets HTTP 416 from the CDN; the byte-count and checksum below decide
curl --fail --location --continue-at - --output "$MODEL" "$MODEL_URL" \
  || test "$(stat -c %s "$MODEL")" = "$MODEL_BYTES"
test "$(stat -c %s "$MODEL")" = "$MODEL_BYTES"
printf '%s  %s\n' "$MODEL_SHA256" "$MODEL" | sha256sum --check --strict

umask 077
openssl rand -hex 32 > "$STATE/api-key"
chmod 600 "$STATE/api-key"
```

The artifact is pinned to one Hugging Face revision, byte count, and SHA-256. A checksum mismatch is
a hard stop; do not rename or reuse the partial file as a successful download. The separate
`qwen3_8_27b-v3.ninfer` path avoids appending a resumed download onto an older model container.

Use the fresh host directory `checkpoints-v013`, mounted at `/checkpoints-v013`; keep the
v0.12.x `checkpoints` store untouched for rollback. Never import or upgrade its sessions into the
new store. The schema 3 loader refuses legacy generations without mutation; prior sessions resume
by replaying the client transcript for a fresh prefill. New exact-runtime checkpoints accelerate
later continuations. All three lanes in v0.13.1 qualify JSON-schema structured output and
128-character Chat/Responses tool names; see the
[compatibility matrix](COMPATIBILITY.md).

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

In another Mac terminal, stream the key over SSH from the login shell or the `Ubuntu-24.04` WSL2
distro (on Windows, the first branch prints one harmless `cannot find the path` line):

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

If `~/.omp/agent/models.yml` does not exist, install the per-model fragment:

```sh
unset PI_OPENAI_STATEFUL
install -m 600 examples/manual-tunnel/models.fragment.yml \
  "$HOME/.omp/agent/models.yml"
```

The server hashes OMP's `prompt_cache_key` into the session identity, `compat.statefulResponses: true`
chains turns with `previous_response_id`, encrypted reasoning and summaries stay off, and effort
clamps within `low`, `medium`, and `xhigh`. If `models.yml` already exists, unset `PI_OPENAI_STATEFUL`
and merge only `providers.ninfer-beta` from
[`models.fragment.yml`](../examples/manual-tunnel/models.fragment.yml):

```yaml
apiKey: '!cat "$HOME/.omp/agent/ninfer-beta.key"'
```

For the macOS/Linux shell route, install the fail-closed default config:

```sh
install -m 600 examples/manual-tunnel/fail-closed.yml \
  "$HOME/.omp/agent/config.yml"
```

### Native Windows OMP

Native Windows OMP does not support `!cat`; copy or merge `providers.ninfer-beta` from
[`examples/windows-docker-local/models.fragment.yml`](../examples/windows-docker-local/models.fragment.yml),
install the fail-closed config, and load the key in the current PowerShell process:

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

$ModelsPath = Join-Path $Agent 'models.yml'
$ConfigPath = Join-Path $Agent 'config.yml'
if ((Test-Path $ModelsPath) -or (Test-Path $ConfigPath)) {
  throw 'Existing OMP models/config found; merge providers.ninfer-beta and retry mappings instead of overwriting them.'
}
Copy-Item .\examples\windows-docker-local\models.fragment.yml $ModelsPath
Copy-Item .\examples\manual-tunnel\fail-closed.yml $ConfigPath
$env:NINFER_BETA_API_KEY = (Get-Content -Raw $KeyPath).Trim()
Remove-Item Env:PI_OPENAI_STATEFUL -ErrorAction SilentlyContinue
```

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
& $Launcher -p --no-session --auto-approve --max-time 20s `
  --model ninfer-beta/q38-ninfer 'Return LOCAL_ONLY.'
if ($LASTEXITCODE -eq 0) { throw 'outage request unexpectedly succeeded' }
```

Expected result: a connection/authentication failure and no model response. Any cloud-provider
request is a release failure. Restart NInfer with section 4 only after observing the failure.

### macOS/Linux command forms

Run these in the terminal that installed the per-model fragment in section 7, with the tunnel
from section 5 open in another. Every check is a `-p` (print) turn, so it exits on its own; the
shell tests the outcome, and `set -e` stops the sequence at the first failure.

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
and does not qualify a cross-release fleet or concurrent native serving in v0.13.1.

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
container profile and the `qwen38-4090-native-v0.7.0-beta.2` /
`qwen38-3090-native-v0.7.0-beta.2` native profiles start with
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
