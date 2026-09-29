# Quickstart

> **v0.9.0: RTX 5090 · RTX 4090; two requests in flight on the RTX 5090**

**Get started with the exact lane for your GPU and runtime.**

> [!IMPORTANT]
> **v0.9.0 is a candidate until its four documented routes pass on the published components.**
> The scope is RTX 5090 container host, macOS client, Windows client, and RTX 4090
> native Windows. RTX 3090 is deferred and is not a v0.9.0 install lane.
> The commands below require the published v0.9.0 release and its readiness check.
> Do not bypass `--require-ready` or mix one release's manifest with another
> release's commands. See [route acceptance](#v090-route-acceptance) for its status.

## Choose your lane

Choose by GPU and runtime before downloading anything. Client-platform qualification is separate
from GPU-runtime qualification.

| I have | Status | Start here | What success produces |
| --- | --- | --- | --- |
| RTX 5090 + Windows 11 / Docker Desktop WSL2 | **v0.9.0 candidate; route acceptance pending** | [RTX 5090 container lane](#ready-route-native-windows-and-docker-desktop-wsl2) | A first OMP turn plus the documented pass/fail acceptance observations |
| RTX 4090 + native Windows | **v0.9.0 candidate; route acceptance pending** | [RTX 4090 native lane](#native-windows-rtx-4090-release-lane) | The documented acceptance checks on the exact published package |
| Any other GPU or deployment | **unsupported** | [Compatibility boundary](COMPATIBILITY.md) | No install attempt; the exact current support policy |

RTX 3090 qualification is **deferred** until its host returns (expected around September 30).
For that GPU, use only the immutable
[v0.7.2 legacy RTX 3090 instructions](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md#native-windows-rtx-4090-and-rtx-3090-release-lanes)
with the v0.7.2 manifest and OMP 18.0.9. Do not combine them with v0.9.0 or OMP 18.4.0.

The current native lane is installable only through its exact qualified manifest variant. Do not
substitute GPU family names, package URLs, component tags, or variant IDs between releases.

## v0.9.0 route acceptance

The four documented routes - RTX 5090 container host, macOS client, Windows client, and RTX 4090
native Windows - are pending on the published v0.6.14 RTX 5090 image `4c816b0c` and the unchanged
v0.6.10 RTX 4090 package, with upstream OMP 18.4.0 and fresh client-platform acceptance. Until
they pass, v0.9.0 stays a candidate and `--require-ready` refuses it. The v0.8.7 routes'
[accepted receipts](../releases/v0.8.7/acceptance/documented-routes.json) cover the previous
RTX 5090 runtime and config, not these.

## Verify the release before setup

The `v0.9.0` candidate composes native Windows OMP over authenticated local loopback
to the exact runtime for the selected qualified lane. RTX 5090 uses
the digest-pinned image in the manifest through Docker Desktop WSL2; the macOS and Linux client
routes reach the same image. RTX 4090 uses its exact native Windows package. Every route runs the
unmodified upstream OMP 18.4.0 client. The RTX 5090 now admits two requests at once, so subagents
or a second session can run beside the first. Its eight-token MTP3 verify round now uses tensor
cores: two decoding requests reached 281.1-283.0 tok/s together against 166.7-167.1 one at a time
(1.68-1.70x). The candidate answered the 89-case role corpus byte-identically to v0.6.13, two
cases at a time and one at a time, and the published image answered it byte-identically to the
candidate; every measured decode pair and fanout branch also matched
([EXP-077](measurements/2026-09-29-rtx5090-two-requests-in-flight.json)). Stock OMP 18.4.0 at its
limit of 2 overlapped a parent's two scout subagents for 15.7-17.7 s, but the turn's wall time
moved with what the subagents generated (23.9 and 25.2 s at 2 against 22.6 and 32.7 s at 1), and
two short sessions started together finished later at 2 in both runs.

The route config sets `providers.maxInFlightRequests` to `ninfer-beta: 2` and `ninfer-main: 2`
for the RTX 5090, and keeps `ninfer-native-4090: 1` and `ninfer-heavy: 1` for the RTX 4090. Upgrade
the RTX 5090 server before raising its OMP limit. A limit of 2 against the old one-at-a-time
server queues the second request at its 30 s deadline, where it can expire. The new profile sets
`--pending-timeout-ms 180000`: a request that does not fit waits up to 180 s, leaving time for
the longest root prefill (130,048 tokens in 58.4 s on the published image) inside OMP's 300 s
stream-idle watchdog. The server ends a too-long wait and OMP resends.

Two requests do not double every workload's speed. Decode beside a 71,641-token prefill ran at
30.4-30.5 tok/s, and a request arriving during a staged prefill waited for it (26.7 s in the
probe). Both prompts and output reservations must fit the 160,256-token KV pool. With OMP's
32,768-token output reservation, two sessions above about 47K tokens each take turns (inferred
from the admission rule; not measured with OMP).

On the unchanged RTX 4090, the limit of 1 lets OMP compact in the background, and a turn meeting a
running summary waits in OMP, which has no deadline, instead of expiring behind it at the
runtime's 30 s admission deadline. In v0.8.7, three handoff compactions and a restart ran
55 requests with none expired, and 22 turns took 365.4 s where v0.8.6's inline compaction took
678.2 s for 24 ([EXP-074](measurements/2026-09-29-long-session-cache.json)).

v0.8.7 fixed the session-cache losses where v0.8.6 prefilled from root. RTX 4090
compaction handoffs reused 78.0-79.9K cached tokens and started in 0.58-0.70 s instead of
prefilling 97.4-97.5K tokens in 63.8-66.3 s. A near-capacity turn whose planner search runs out
of time keeps its continuation: on the RTX 5090 such turns reused 78.0-80.5K cached tokens, where
v0.6.12 prefilled 93.7-105.1K tokens from root. A crash after a compaction restores the compacted
session, and short sessions filling the 24 GiB checkpoint store no longer delete long sessions'
checkpoints ([lane receipt](../releases/v0.8.7/qualification/rtx5090.json)).

On Windows, OMP 18.3.5 printed a false `ended before completing` line after every finished `omp -p`
turn and exited 1 after a complete `omp models` listing. OMP 18.4.0 exited 0 with no false line in
all ten runs of the same commands
([EXP-070](measurements/2026-09-28-omp-1840-windows-completion-status.json)).

OMP compacts a 131,072-token session on its own at 111,412 tokens. For a model that accepts
images, its first method archives earlier turns as images at native resolution, which NInfer
refuses, so every long RTX 5090 session on stock OMP 18.3.0-18.4.0 failed at its first
compaction. The RTX 5090 fragments now declare `supportsImageDetailOriginal: false`, so OMP sends
`detail: "auto"`: the lane served that compacted continuation and returned the exact nonce, and
refused the native-resolution request in 9 ms
([EXP-071](measurements/2026-09-28-omp-snapcompact-image-detail.json)). The text-only RTX 4090
model is never compacted into images.

RTX 5090 moves to the published `v0.6.14-qwen38-5090-beta.1` from source
`e20060b6a152a11fd72450549592527e126b035e`, image `4c816b0c`, with the two-request profile below.
The published image retrieved 130,048 tokens exactly in 58.4 s and decoded 169.79 tok/s over
2,048 tokens ([lane receipt](../releases/v0.9.0/qualification/rtx5090.json)).
RTX 4090 keeps the published `v0.6.10-qwen38-4090-beta.1` from source
`cba7eb932724c99a4faffd6b7b47256015c9b969`. The exact [native package](https://github.com/alphastorm/ninfer/releases/download/v0.6.10-qwen38-4090-beta.1/ninfer-rtx4090-native-v0.6.10-beta.1-windows-x86_64-cuda13.3-rtx4090.tar.gz) is
574,717,115 bytes, SHA-256 `a0ea4c81a3a70239fa350f2bbbfff9cd088de6d0028c4e73cff5581afa09cc6b`.
The manifest-driven native steps below download and verify that package, not a substitute.

The RTX 4090's `engine.gpu_keep_warm_ms = 60000`
uses a single-warp spin of 50 ms every 100 ms: the RTX 5090's 3.5 ms/10 ms pattern did not hold
this card in P2 ([EXP-064](measurements/2026-09-27-rtx4090-engine-keep-warm.json)). New sessions
after 12-58 s idle prefilled in 0.146-0.148 s (time to first token 0.167-0.178 s), with all 31
outputs byte-identical and about 72 W above idle while held
([EXP-066](measurements/2026-09-27-rtx4090-keep-warm-long-spin.json)). A request arriving mid-spin
can overlap one warp for up to 50 ms. The v0.6.10 package passed all 15 canonical qualification
phases, including 130,048-token exact retrieval in 91.2 s, C1 decode at 157.91 tok/s and 87.59%
MTP acceptance (v0.6.9: 157.90 tok/s), managed-stop flush, security, both rollback directions and
an OMP 18.4.0 typed tool call ([lane receipt](../releases/v0.9.0/qualification/rtx4090.json)). The
controller passes `--gpu-keep-warm-ms` only when the release's own packaged configuration declares
a positive value, so rollback does not pass the new flag to older servers.

Stock OMP names each session with `prompt_cache_key`, which the runtime hashes into the session
identity under API authentication. The OMP 18.4.0 macOS arm64 binary kept one session across
graceful server restarts on both v0.8.7 runtimes, including a new OMP process resuming after a
restart, whose first request the runtime restored from the session's checkpoint
([EXP-075](measurements/2026-09-29-stock-omp-1840-durable-sessions.json)). That one-platform,
short-session proof is separate from the documented-route and client-platform acceptance above.
The fragments' other fields and `PI_OPENAI_STATEFUL=1` are unchanged: live steering is Codex-WebSocket-only and
gated on `compat.supportsSteering`, which these providers do not set, and cache warming does not
warm a model without a declared `promptCache`.

On the v0.9.0 profile none of 24 fresh agent sessions fell back to a full prefill, and median
time to first token was 0.092-0.100 s
([lane receipt](../releases/v0.9.0/qualification/rtx5090.json)). Its durability workload with two
126K-token sessions, a fanout and the agent protocol stopped with
`saved 1, nothing to save 3, refused 0`, and all four stored sessions resumed from checkpoints.
Saving before eviction costs the admitting request about 6.5 s per 126K-token session on the
RTX 5090, and that request waits while a victim's reply is still reaching its client, bounded
by its own queue deadline. Automatic checkpoints remain best effort under traffic: a crash or
an expired graceful wait can still leave unpublished work unsaved. The carried multisession
control recorded root fallback on 2 of 8 continuations/forks without server errors; universal
warm reuse is not claimed.

A checkpoint is bound to the exact server build. RTX 5090 checkpoints saved by v0.8.7 report
`incompatible`: OMP resends the full conversation and each session re-prefills once. RTX 4090
checkpoints carry over because its runtime is unchanged. When upgrading from v0.8.7, first
upgrade the RTX 5090 server, then merge the new `providers.maxInFlightRequests` values from
`examples/manual-tunnel/fail-closed.yml` into `~/.omp/agent/config.yml`, adding any other NInfer
provider id you declare. The OMP binary, `models.yml` and `PI_OPENAI_STATEFUL=1` are unchanged.

The model and memory floors are unchanged from v0.8.7. The RTX 5090 deployment profile is
`qwen38-5090-v0.9.0` / configuration `cf1de114`, adding `--max-concurrency 2` and
`--pending-timeout-ms 180000`. It keeps `--gpu-keep-warm-ms 60000`, 16384 MiB host KV and the
28672 MiB runtime-host floor. KV capacity auto-resolves to 160,256 tokens; VRAM after load is
30,244 MiB of 32,607 MiB, against 28,144 MiB with one request. The native RTX 4090 keeps release
identity `qwen38-4090-native-v0.6.10-beta.1` / configuration `7a69481f`, its serving arguments,
11264 MiB host KV, 24 host-state slots and the 32768 MiB host floor.

A managed RTX 4090 start could fail when the driver refused to pin the host-KV pool
([#48](https://github.com/alphastorm/omp-ninfer/issues/48)); since v0.8.0 the runtime commits and
releases each pinned allocation's size plus 1/64 before pinning it. The field start from the
refusing memory state passed with the published v0.6.8 package (3.5 GiB free, 22.6 GiB standby;
[EXP-064, `issue_48_field_start`](measurements/2026-09-27-rtx4090-engine-keep-warm.json)), and every
managed start in the new package's canonical qualification pinned the pool. A refusal that still
occurs reports the commit limit, available commit and available memory.
Qualification scratch settings do not replace either public profile.

The client is an unmodified executable from the upstream
[Oh My Pi v18.4.0 release](https://github.com/can1357/oh-my-pi/releases/tag/v18.4.0), not an archive
or installer. The exact binary identities are:

| Client binary | Bytes | SHA-256 |
| --- | --- | --- |
| [`omp-windows-x64.exe`](https://github.com/can1357/oh-my-pi/releases/download/v18.4.0/omp-windows-x64.exe) | 239,441,408 | `5e8637d7f0e86819eb17238f297b4cef07f5239a4f59e2b26f8b4584a9ea95fe` |
| [`omp-linux-x64`](https://github.com/can1357/oh-my-pi/releases/download/v18.4.0/omp-linux-x64) | 285,148,640 | `fbcdb8f5033c9bf81435f5803d8f0493c53d524a638658d2b8811474a332200f` |
| [`omp-darwin-arm64`](https://github.com/can1357/oh-my-pi/releases/download/v18.4.0/omp-darwin-arm64) | 214,917,008 | `90111c710fb861b03e5ef6fd3257319001acdd77ff7d06d3a6207996f2777709` |

Start only from the product tag and require its ready contract:

```sh
python3 scripts/verify_release.py --require-ready
```

That gate binds the Windows client binary, compatibility authority, NInfer image/SBOM,
model, configuration, qualification summary, and clean-install acceptance receipt.

> [!WARNING]
> Stay on the exact upstream OMP 18.4.0 binary pinned by this release. The config every route below
> installs (`examples/manual-tunnel/fail-closed.yml`) turns the client's startup update check
> off: a generic `omp update` would replace the client outside the release procedure and move it
> away from the checksummed bytes. Upgrade by cloning the next tag and rerunning the install step.

> [!NOTE]
> The same config lets OMP send the RTX 5090 two requests at once and the RTX 4090 one at a
> time. The RTX 5090 uses snapcompact without a model request. On the RTX 4090, OMP writes a
> long session's compaction summary in the background, so a turn you send meanwhile waits in
> OMP for it instead of expiring at the server
> ([troubleshooting](TROUBLESHOOTING.md#a-turn-fails-with-request_queue_timeout-late-in-a-long-session)).

## Ready route: native Windows and Docker Desktop WSL2

### Prerequisites

- Windows 11 x64 and a single NVIDIA GeForce RTX 5090;
- Docker Desktop using Linux containers, WSL2 Ubuntu 24.04, and the NVIDIA container runtime;
- Git, PowerShell, Python 3 from python.org (its `py` launcher; the `python3` name Windows
  ships is a Microsoft Store shortcut, not Python), and at least 40 GiB free for the model,
  image, client, and logs; and
- one trusted owner for Windows and the WSL2 runtime.

### Clone and verify the exact product release

Clone the tag in Windows and in the WSL2 namespace that owns Docker. Windows ships with script
execution disabled; the `Set-ExecutionPolicy` line enables the release's hash-pinned scripts for
this window only and changes nothing on the machine - repeat it in any new window that runs one.

```powershell
git clone --branch v0.9.0 --depth 1 https://github.com/alphastorm/omp-ninfer.git
Set-Location omp-ninfer
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
py -3 scripts\verify_release.py --require-ready
```

### Install the exact native Windows client

```powershell
$ErrorActionPreference = 'Stop'
$Url = 'https://github.com/can1357/oh-my-pi/releases/download/v18.4.0/omp-windows-x64.exe'
$Expected = '5e8637d7f0e86819eb17238f297b4cef07f5239a4f59e2b26f8b4584a9ea95fe'
Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile omp-windows-x64.exe
if ((Get-FileHash omp-windows-x64.exe -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Expected) { throw 'OMP binary checksum mismatch' }
$Launcher = "$env:LOCALAPPDATA\OMP\omp.exe"
New-Item -ItemType Directory -Force -Path (Split-Path $Launcher) | Out-Null
Copy-Item .\omp-windows-x64.exe $Launcher -Force
$env:PI_OPENAI_STATEFUL = '1'
& $Launcher --version
if ($LASTEXITCODE -ne 0) { throw 'OMP version check failed' }
```

The version must be `omp/18.4.0`. To roll back, re-download the previous pinned binary and verify
its checksum before replacing `omp.exe`.

Inside WSL2, continue with **3. Prepare the model and key** and **4. Start NInfer** below. Skip
the macOS tunnel sections: Docker Desktop exposes the WSL2 loopback service to native
Windows at `127.0.0.1:18089`. Then use the **Native Windows OMP** provider instructions in
section 7 and the **Native Windows command forms** at the start of section 8.

## Native Windows RTX 4090 release lane

This native NInfer package is not a substitution for the RTX 5090 image. Before installation,
the ready manifest must publish `rtx4090-windows-native` as qualified. The ready product
manifest remains authoritative for every download URL and hash; no absent or unqualified
variant may be deployed.

Prerequisites: Windows 11 x64, a single RTX 4090 with a current driver, Git, PowerShell,
Python 3 from python.org (its `py` launcher; the `python3` name Windows ships is a Microsoft
Store shortcut, not Python), and at least 40 GiB free. Install the OMP client first with
**Install the exact native Windows client** above; the lane's own steps follow. RTX 4090
requires at least 32768 MiB of runtime-host memory for its unchanged 11264 MiB pinned host-KV
pool and 24 host-state slots. Start from an
elevated PowerShell. Windows ships with script execution disabled; the `Set-ExecutionPolicy`
line enables the release's hash-pinned scripts for this window only and changes nothing on the
machine - repeat it in any new window that runs one:

```powershell
git clone --branch v0.9.0 --depth 1 https://github.com/alphastorm/omp-ninfer.git
Set-Location omp-ninfer
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
py -3 scripts\verify_release.py --require-ready
```

Use this lane's installed state root, served request model id, and loopback endpoint;
these values are not interchangeable with a historical release's variants:

| Variant id | Installed state root | Request model id | Endpoint |
| --- | --- | --- | --- |
| `rtx4090-windows-native` | `%ProgramData%\NInfer\qwen38-4090-native` | `qwen3.8-27b` | `http://127.0.0.1:18082/v1` |

The RTX 4090 native lane is text and tools only: Vision belongs to the RTX 5090 container
profile ([`docs/FACTS.md`](FACTS.md)). Set `$VariantId` once:

```powershell
$VariantId = 'rtx4090-windows-native'
```

Then let the manifest supply every URL and hash. The shared native blocks and provider fragment
retain historical RTX 3090 identifiers, but those are not a current install route: the manifest
guard below refuses a missing or unqualified variant before downloading or installing it.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
$ErrorActionPreference = 'Stop'
$Manifest = Get-Content .\releases\v0.9.0\manifest.json -Raw | ConvertFrom-Json
$Variant = @($Manifest.components.ninfer_variants | Where-Object { $_.id -ceq $VariantId })
if ($Variant.Count -ne 1 -or $Variant[0].status -cne 'qualified') {
  throw 'requested native runtime variant is not uniquely qualified'
}
$StateRootName = switch ($VariantId) {
  'rtx4090-windows-native' { 'qwen38-4090-native' }
  'rtx3090-windows-native' { 'qwen38-3090-omp-v0.2' }
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
$Model = Join-Path $ModelDir 'qwen3_8_27b.ninfer'
& curl.exe --fail --location --continue-at - --output $Model $Manifest.components.model.artifact_url
# a rerun with a complete file gets HTTP 416 from the CDN; the byte-count and checksum below decide
if ($LASTEXITCODE -ne 0 -and (Get-Item $Model -ErrorAction SilentlyContinue).Length -ne [int64]$Manifest.components.model.artifact_bytes) {
  throw 'model artifact download failed'
}
if ((Get-Item $Model).Length -ne [int64]$Manifest.components.model.artifact_bytes) {
  throw 'model artifact byte count mismatch'
}
if ((Get-FileHash $Model -Algorithm SHA256).Hash.ToLowerInvariant() -cne
    $Manifest.components.model.artifact_sha256) {
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

The install prints one JSON receipt and leaves the server running. The package controller binds
loopback/Tailscale-only listening, mandatory bearer authentication, the external model hash,
process-restart checkpoints, and active/previous rollback. Do not mix assets across variants or
infer install authority from GPU-family names. RTX 4090 uses its exact MTP3 profile.
Structured JSON-schema output remains unsupported and fails closed.

### Operate the native lane

The installed controller is the only supported lifecycle surface, and every action needs the
lane's state root. Run these in the window that installed the lane; in a new elevated window,
first set `$StateRoot` to the lane's state root from the table above. `-Action Restart` does the
stop and the start in one step:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
$Controller = Join-Path $StateRoot 'Control-Release.ps1'
& $Controller -Action Status -StateRoot $StateRoot   # the installed release, its identity, endpoint state
& $Controller -Action Stop -StateRoot $StateRoot     # checkpoints live sessions; inspect any refusals
& $Controller -Action Start -StateRoot $StateRoot    # the same command brings the lane back after a reboot
& $Controller -Action Status -StateRoot $StateRoot
```

`Status` is the success criterion: it must report the installed release id, the served binary and
configuration identity, and a ready endpoint. A machine reboot is not a managed stop - the
scheduled task starts the release again, but a session that was never published (automatically
above 32,768 frontier tokens, or explicitly through `POST /v1/ninfer/checkpoints`) does not
survive it. A deliberate `-Action Stop` does save it.

### Point OMP at the native lane

Native Windows OMP does not support the POSIX `!cat` secret reference, so the key is loaded into
the launching process. Copy the native fragment, then set `$Provider` to the lane you installed:

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
$env:PI_OPENAI_STATEFUL = '1'
```

Stock OMP names each session with `prompt_cache_key`. With API authentication configured, the
server hashes that key into the session identity without storing the raw key; this enables
automatic checkpoints and restore. `PI_OPENAI_STATEFUL=1` makes OMP chain turns with
`previous_response_id`. Encrypted reasoning and reasoning summaries are disabled because the
server refuses fields it does not implement. The fragment's effort list keeps OMP within the
template's `low`, `medium`, and `xhigh` levels (`off` clamps to `low`, `high` to `medium`).

The environment-backed value exists only in that PowerShell process and its children. Do not put
the key itself in YAML, command arguments, shell history, or support bundles. In that process,
`& "$env:LOCALAPPDATA\OMP\omp.exe" --model "$Provider/qwen3.8-27b"` opens an interactive session on
the lane; run the acceptance below first, it uses the same process without opening one.

### Native lane acceptance

Run these in the same PowerShell process that loaded `NINFER_NATIVE_API_KEY`:

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
    'Remember the nonce COBALT-493817 for my next turn. Reply OK only.'
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

Expected result: the first three turns succeed locally, the outage request fails with a
connection error and no model response, and the lane serves again after `-Action Start`. Any
cloud-provider request is a release failure. Skip the Vision check in section 8: these lanes are
text and tools only. Report the outcome with the
[clean-install report](https://github.com/alphastorm/omp-ninfer/issues/new?template=clean-install-report.yml).

## Managed macOS SSH qualified route

### Prerequisites

**Mac**

- Apple silicon macOS supported by the pinned upstream binary;
- OpenSSH, curl, and Python 3; and
- at least 1 GiB free for OMP and local state.

**Inference host**

- a single-user Linux or WSL2 environment owning one NVIDIA GeForce RTX 5090;
- a current NVIDIA driver, Docker with Linux host-network support, and NVIDIA Container Toolkit;
- OpenSSH access terminating in the same Linux/WSL namespace as Docker;
- at least 40 GiB free for the 18,210,531,328-byte model, image, and logs; and
- **at least 28 GiB of memory available to the container.** From `v0.7.0` the profile's Host KV
  pool holds two sessions at the 131,072-token ceiling instead of one, and that pool is pinned
  runtime-host memory. On Docker Desktop the container sees the WSL2 utility VM, which takes half
  the machine's RAM by default - a 48 GB machine offers 24 GiB, which is not enough. Raise it in
  `%UserProfile%\.wslconfig` and run `wsl --shutdown`:

  ```ini
  [wsl2]
  memory=32GB
  ```

  `start-ninfer.sh` reads the floor from the profile and refuses before loading the artifact if
  the host is smaller, because a pool the host cannot back is OOM-killed mid-request rather than
  degraded. A host that cannot give the container this much memory runs `v0.6.10`, whose 8 GiB
  pool holds one session at the ceiling and two of about 75,000 tokens.

The NInfer endpoint binds only to remote loopback. Never publish port `18089` on a LAN or public
interface. This release assumes both machines and local accounts are controlled by one trusted
owner.

## 1. Clone the exact release on both machines

Once v0.9.0 is published and ready, run this on the Mac and inference host:

```sh
git clone --branch v0.9.0 --depth 1 \
  https://github.com/alphastorm/omp-ninfer.git
cd omp-ninfer
python3 scripts/verify_release.py --require-ready
```

Do not install from moving `main`, an untagged archive, or a manifest whose status is
`draft` or `candidate`.

## 2. Install the OMP beta on the Mac

```sh
(
set -euo pipefail
URL='https://github.com/can1357/oh-my-pi/releases/download/v18.4.0/omp-darwin-arm64'
EXPECTED='90111c710fb861b03e5ef6fd3257319001acdd77ff7d06d3a6207996f2777709'
curl --fail --location --output omp-darwin-arm64 "$URL"
test "$(shasum -a 256 omp-darwin-arm64 | cut -d ' ' -f 1)" = "$EXPECTED"
mkdir -p "$HOME/.local/bin"
cp omp-darwin-arm64 "$HOME/.local/bin/omp"
chmod 0755 "$HOME/.local/bin/omp"
export PI_OPENAI_STATEFUL=1
"$HOME/.local/bin/omp" --version
)
```

The version must be `omp/18.4.0`. To roll back, re-download the previous pinned binary and verify
its checksum before replacing `~/.local/bin/omp`. Every later step calls bare `omp`, so put
`$HOME/.local/bin` on `PATH` (`export PATH="$HOME/.local/bin:$PATH"`, and in your shell profile
if you want it to persist) before continuing.

## 3. Prepare the model and key on the inference host

From the release clone:

```sh
ROOT="$HOME/.local/share/omp-ninfer"
STATE="$HOME/.config/omp-ninfer"
LOGS="$HOME/.local/state/omp-ninfer"
CHECKPOINTS="$ROOT/checkpoints"
install -d -m 700 "$ROOT" "$STATE" "$LOGS" "$CHECKPOINTS"

MODEL_URL=$(python3 -c \
  'import json; print(json.load(open("releases/v0.9.0/manifest.json"))["components"]["model"]["artifact_url"])')
MODEL_BYTES=$(python3 -c \
  'import json; print(json.load(open("releases/v0.9.0/manifest.json"))["components"]["model"]["artifact_bytes"])')
MODEL_SHA256=$(python3 -c \
  'import json; print(json.load(open("releases/v0.9.0/manifest.json"))["components"]["model"]["artifact_sha256"])')
MODEL="$ROOT/qwen3_8_27b.ninfer"

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
a hard stop; do not rename or reuse the partial file as a successful download.

## 4. Start NInfer on the inference host

```sh
./examples/manual-tunnel/start-ninfer.sh \
  --model "$MODEL" \
  --api-key-file "$STATE/api-key" \
  --log-dir "$LOGS" \
  --checkpoint-dir "$CHECKPOINTS"
```

The launcher:

- refuses a draft manifest;
- refuses to launch unless the configuration identity it computes for this profile equals the one
  the profile declares and the manifest records, so the identity the server reports describes the
  server you are running;
- pulls the digest-pinned image and checks the model and `ninfer-serve` binary hashes;
- probes the GPU inside that image, which is what has to work - the host needs no `nvidia-smi`;
- starts one owned `omp-ninfer-beta` container with restart policy `no`, as your own user, with
  every capability dropped, `no-new-privileges`, and the repository's io_uring seccomp profile
  pinned by hash;
- mounts the model and API key read-only, and the log and checkpoint directories private to you;
- publishes the container's port on `127.0.0.1:18089` of the inference host - a container that
  binds the "host" network on Docker Desktop binds the engine VM, which neither Windows nor the
  WSL2 distro can reach; and
- waits for authenticated status to match source, binary, model, configuration, profile, and runtime
  fields.

The checkpoint directory is the durable session store: sessions saved there - automatically above
32,768 frontier tokens, or explicitly through `POST /v1/ninfer/checkpoints` - survive the server
process. Keep it on a local filesystem (the IO path is O_DIRECT) and out of the log directory.

It deliberately leaves a failed container in place for `docker logs omp-ninfer-beta`. Stop and
remove only the correctly labelled beta container with:

```sh
./examples/manual-tunnel/stop-ninfer.sh
```

That removes the container and retains the model, key, request logs, and checkpoints, so the next
`start-ninfer.sh` continues the sessions the store holds.

A machine reboot is not a managed stop for this route either. The container is created with
`--restart no`, and on Docker Desktop an existing container cannot be started again once the WSL
distro holding these paths has restarted, which a reboot always does. Bring the lane back by
recreating it - `stop-ninfer.sh`, then the same `start-ninfer.sh` command - and the checkpoint
store makes that a continuation rather than a loss. The exact failure signature, including the
quiet variant where the container starts with empty mounts, is in
[Troubleshooting](TROUBLESHOOTING.md#the-container-exists-but-will-not-start-after-a-host-reboot).

The server receives the key through a read-only secret mount, so the key is not embedded in the
Docker configuration or host shell history. The resulting server process argument is visible to
root inside the trusted container/host boundary; this is not a multi-tenant secret-isolation
design.

## 5. Open the tunnel from the Mac

In a dedicated terminal inside the Mac release clone:

```sh
./examples/manual-tunnel/open-tunnel.sh USER@RUNTIME_HOST
```

Replace the destination with the SSH user and host of the inference machine. On a Linux host that
is the account that ran section 4; on Windows 11 with Docker Desktop it is the Windows account
and the stock Windows OpenSSH server - the container publishes its port on the machine's own
loopback, which that server forwards. Keep this process running. `ExitOnForwardFailure` prevents
a false-green tunnel when local port `18089` is occupied; keepalive options make a dead route
observable.

## 6. Install the same key on the Mac

In another Mac terminal. The key lives in the shell that ran section 4: on Linux the SSH login
shell, on Windows the WSL2 distro behind the Windows OpenSSH server, which `wsl.exe` reaches.
The command below tries the login shell first and falls back to the distro; on a Windows
destination the first attempt prints one harmless `cannot find the path` line:

```sh
install -d -m 700 "$HOME/.omp/agent"
umask 077
ssh USER@RUNTIME_HOST 'sh -lc "cat ~/.config/omp-ninfer/api-key" 2>/dev/null || wsl.exe -d Ubuntu-24.04 -- sh -lc "cat ~/.config/omp-ninfer/api-key"' \
  | tr -d '\r' > "$HOME/.omp/agent/ninfer-beta.key"
chmod 600 "$HOME/.omp/agent/ninfer-beta.key"
test "$(wc -c < "$HOME/.omp/agent/ninfer-beta.key")" -gt 32
```

This streams the secret inside SSH and does not print it. Use the exact destination from the
tunnel. Do not paste the key into YAML, shell history, an issue, or a support bundle.

## 7. Add the OMP provider

In every shell that launches OMP, export `PI_OPENAI_STATEFUL=1`. If
`~/.omp/agent/models.yml` does not exist, install the fragment:

```sh
export PI_OPENAI_STATEFUL=1
install -m 600 examples/manual-tunnel/models.fragment.yml \
  "$HOME/.omp/agent/models.yml"
```

Stock OMP names each session with `prompt_cache_key`. With API authentication configured, the
server hashes that key into the session identity without storing the raw key; this enables
automatic checkpoints and restore. `PI_OPENAI_STATEFUL=1` makes OMP chain turns with
`previous_response_id`. Encrypted reasoning and reasoning summaries are disabled because the
server refuses fields it does not implement. The fragment's effort list keeps OMP within the
template's `low`, `medium`, and `xhigh` levels (`off` clamps to `low`, `high` to `medium`).

If the file already exists, run the export above and merge only the `providers.ninfer-beta` mapping from
[`models.fragment.yml`](../examples/manual-tunnel/models.fragment.yml). Do not overwrite existing
providers or model definitions. The key remains an executable secret reference:

```yaml
apiKey: '!cat "$HOME/.omp/agent/ninfer-beta.key"'
```

For the macOS/Linux shell route, install the fail-closed default config:

```sh
install -m 600 examples/manual-tunnel/fail-closed.yml \
  "$HOME/.omp/agent/config.yml"
```

### Native Windows OMP

The POSIX `!cat` secret reference is not supported by native Windows OMP. Copy
[`examples/windows-docker-local/models.fragment.yml`](../examples/windows-docker-local/models.fragment.yml)
to `$HOME\.omp\agent\models.yml`, or merge only its `providers.ninfer-beta` mapping.
Install the fail-closed default config and load the key without printing it before every OMP launch:

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
$env:PI_OPENAI_STATEFUL = '1'
```

The environment-backed value exists only in that PowerShell process and its children. Do not put
the key itself in YAML, command arguments, shell history, or support bundles. The block refuses to
overwrite an existing OMP configuration; merge only `providers.ninfer-beta` and the `retry` mapping
when those files already exist. In that process,
`& "$env:LOCALAPPDATA\OMP\omp.exe" --model ninfer-beta/q38-ninfer` opens an interactive session;
the **Native Windows command forms** in section 8 use the same process without opening one.

The default config disables retries and model fallback. Select the explicit provider/model on
every new session: a tunnel or runtime failure must be an error, not a switch to a cloud model.

## 8. Acceptance

Run these checks in order and record only pass/fail plus the content-safe identities from the NInfer
launcher.

### Native Windows command forms

Run from the tagged product clone in the same PowerShell process that loaded
`NINFER_BETA_API_KEY`:

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
  'Remember the nonce COBALT-493817 for my next turn. Reply OK only.'
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

Run these in the terminal that exported `PI_OPENAI_STATEFUL=1` in section 7, with the tunnel
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
  "Remember the nonce COBALT-493817 for my next turn. Reply OK only."
omp -p --auto-approve --session-dir "$SMOKE/sessions" --continue \
  "Return the exact nonce from the prior turn verbatim, character for character. Do not correct or change its spelling. Return nothing else." | tee "$SMOKE/resume.txt"
grep -q COBALT-493817 "$SMOKE/resume.txt"
```

The transcript remains authoritative. This checks OMP exit and resume with NInfer stateful
Responses while the server process stays up; the next check takes it down.

### Session survives the server process

A session is written to the durable store automatically once it passes 32,768 frontier tokens,
or on an explicit `POST /v1/ninfer/checkpoints` for its session digest. The authenticated server
derives that digest from OMP's `prompt_cache_key`, so this check uses the automatic path: it
seeds a session past the gate with the first 200,000 ASCII bytes of the release's own
documentation, restarts the server container on the inference host, and continues. The seed is
about 64,000 tokens: past the gate, and well below the 111,412 tokens at which OMP compacts a
131,072-token session on its own. A compacted continuation sends a different prompt, so the
runtime could not restore the saved session. The seed drops every line that contains the nonce's
digits: the documentation quotes earlier runs of this check, and a quoted variant such as the
misspelled `COBOLT` copy from v0.8.6 is what the model returned in place of the planted nonce.

```sh
cat "$HOME/omp-ninfer/docs/BENCHMARKS.md" "$HOME/omp-ninfer/README.md" \
    "$HOME/omp-ninfer/docs/ARCHITECTURE.md" "$HOME/omp-ninfer/docs/PERFORMANCE.md" \
    "$HOME/omp-ninfer/CHANGELOG.md" | LC_ALL=C tr -cd '\11\12\40-\176' | grep -v 493817 > "$SMOKE/docs.txt"
head -c 200000 "$SMOKE/docs.txt" > "$SMOKE/context.md"
omp -p --auto-approve --session-dir "$SMOKE/durable" --model ninfer-beta/q38-ninfer \
  @"$SMOKE/context.md" "Hold this material in context. Remember the nonce COBALT-493817. Reply OK only."
ssh USER@RUNTIME_HOST docker restart --timeout 60 omp-ninfer-beta
until curl -sf -m 3 -o /dev/null http://127.0.0.1:18089/health; do sleep 3; done
omp -p --auto-approve --session-dir "$SMOKE/durable" --continue \
  "Return the exact nonce I asked you to remember verbatim, character for character. Do not correct or change its spelling. Return nothing else." | tee "$SMOKE/durable.txt"
grep -q COBALT-493817 "$SMOKE/durable.txt"
```

Use the SSH destination from section 5; `docker` answers there on Linux and on Windows alike, and
the loop waits through the tunnel for the server to come back. The nonce comes back from the restored generation - the
RTX 5090 lane restores a 5 GB session in 3.6-4.0 s and a small one in about a second - and a
checkpoint whose payload was altered is refused rather than served
([EXP-031](measurements/2026-09-11-rtx5090-public-route-qualification.json)). A session below
the gate that was never saved explicitly, a crash, or a power loss still loses what was never
written.

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

## Fleet: the two qualified lanes in one OMP configuration

If you own both qualified lanes, [`examples/fleet/`](../examples/fleet/) binds them into
one configuration with explicit roles: `ninfer-main/q38-ninfer` (RTX 5090) for the interactive
lead session and `ninfer-heavy/qwen3.8-27b` (RTX 4090) for long-context background workers.
Every lane stays loopback-only on its own machine. RTX 5090 serves two active requests; RTX 4090
serves one. The fleet's RTX 3090 scout role is deferred with its GPU: it is not a v0.9.0 install
lane, so neither the fragment nor this recipe declares it. Its three-lane form stays at the
immutable v0.7.2 tag with the legacy OMP 18.0.9 instructions for that lane.

Export `PI_OPENAI_STATEFUL=1` in every shell that launches a fleet agent; the fragment uses the
same session identity, thinking efforts, and reasoning compatibility settings as section 7.

```sh
export PI_OPENAI_STATEFUL=1
# two authenticated forwards; pass - to skip a lane you do not own
./examples/fleet/open-tunnels.sh USER@MAIN_HOST USER@HEAVY_HOST
install -m 600 examples/fleet/models.fragment.yml ~/.omp/agent/models.fleet.yml   # merge by hand
install -m 600 examples/fleet/agents/fleet-heavy.md ~/.omp/agent/agents/
```

The fleet is not a throughput claim. Its measured boundary is EXP-016 in
[`PERFORMANCE.md`](PERFORMANCE.md): on a fixed 14-job batch, cost-aware dispatch across these
two lanes completed the batch 1.54× faster than the RTX 5090 alone (43.4 s against 66.8 s),
naive dispatch 1.30×, and pinning jobs by role alone 0.66×. That receipt's faster 2.07× figure
used a third RTX 3090 lane this release does not qualify. Roles describe what a lane is for;
where a job runs should follow measured per-lane cost (`scripts/fleet_dispatch.py --policy cost`).

## Replicating sessions off the machine

Every lane's session checkpoints are immutable, SHA-manifested generations published under one
local checkpoint root. The native IO paths (O_DIRECT, DirectStorage) need a local filesystem, so
a network share is never a checkpoint root; replication is a verified copy out to shared storage
and a verified copy back before a restore. [`scripts/checkpoint_sync.py`](../scripts/checkpoint_sync.py)
does exactly that with the standard library:

```sh
# on the inference host, with the checkpoint root the server was started with
python3 scripts/checkpoint_sync.py export --root <checkpoint-root> --destination <replica-root> --receipt export.json
# later, on the same profile (same binary and configuration identity), before the restore
python3 scripts/checkpoint_sync.py import --source <replica-root> --root <checkpoint-root> --receipt import.json
```

What the tool guarantees: only the current generation of each session is copied, only after
every manifest-listed file verifies by size and SHA-256; the copy stages outside every directory
the runtime scans and publishes with one rename, the session's `current` pointer last; a
generation without an origin tag (`manifest.mac`) is refused unless you pass
`--allow-unauthenticated` for a locally produced legacy checkpoint. What the runtime guarantees on
top: `manifest.mac` is an HMAC over the exact manifest bytes keyed by material derived from the
lane's bearer key and held outside the checkpoint root, so a coherent rewrite of an imported
generation is quarantined at load (`checkpoint_corrupt` on the native lanes,
`previous_response_not_found` on the container) and never restored. Start the server with
`--session-checkpoint-require-origin-auth` (32-character bearer floor) to refuse unMAC'd
generations outright — the posture for roots that receive imports.

Portability is same-profile-pair only: the runtime fingerprint binds binary and profile, and the
session namespace binds the bearer key, so a replica from another lane or another key is not even
addressable, let alone restorable. Measured on 2026-09-05 with
[`scripts/sync_probe.py`](../scripts/sync_probe.py) (export, carry off the machine, destroy the
local copy with the server stopped, carry back, import, restart, exact retrieval of planted
keys): RTX 5090 4.5 GB import 10.1 s and restored continuation 24.8 s; RTX 4090 1.13 GB import
4.2 s, restored 7.4 s; RTX 3090 1.69 GB import 11.9 s, restored 11.5 s — receipts in
[`docs/measurements/`](measurements/) (`2026-09-05-sync-probe-*.json`).

Moving the replica is the slow part only when the transport is wrong for the latency. A single
`scp`/`rsync`-over-ssh stream carries about 1.6 MB in flight, so it tops out near 8–14 MB/s on
any 70–190 ms path regardless of link speed, and between two Windows hosts ssh cannot carry bulk
at all. [`scripts/hosts/pscp.py`](../scripts/hosts/pscp.py) covers both cases:

```sh
# one end is not Windows: N ranged reads over independent ssh connections
python3 scripts/hosts/pscp.py pull --host <host> --platform posix --remote <path> --local <path>
# both ends are Windows: bearer-token ranged HTTP over the tailnet
python3 scripts/hosts/pscp.py serve --local <archive>            # prints port + token, then exits
python3 scripts/hosts/pscp.py fetch --url http://<host>:<port> --token <token> --local <archive>
```

Both directions verify the whole file by SHA-256 on both ends and need only the standard library
plus ssh. A file share on the same LAN is the better target where you have one: the
fleet's NAS carries about 1 GbE line rate from the two lanes that share its network (115.8 MB/s
write, 117.6 MB/s read, measured over 2 GiB of incompressible payload) while reaching the same
appliance across the internet manages 6.4 MB/s - slower than the direct host-to-host path - so
replicate to whatever storage is closest to each machine, and remember a share is a replication
target, never a checkpoint root ([NAS](measurements/2026-09-07-nas-replication-sf-lanes.json)). Measured between the two owner sites over the tailnet (67 ms): 11.5 MB/s into a Windows
host, 56–63 MB/s into a Linux one — so prefer a Linux replication target. A full round trip of a
1.13 GB checkpoint, out and back and restored with its planted keys intact, takes about 3 minutes
([round trip](measurements/2026-09-06-cross-site-replication-rtx5090.json) ·
[transfer paths](measurements/2026-09-06-replica-transfer-paths.json)). If a replica leaves WSL
through `/mnt/c`, write the archive with `tar -b 8192` — the default 10 KiB records cost 8×.

## 9. Send feedback

Choose the structured form that matches the result:

- a successful qualified-lane setup: [clean-install report](https://github.com/alphastorm/omp-ninfer/issues/new?template=clean-install-report.yml);
- RTX 3090 validation or another hardware observation: [hardware qualification report](https://github.com/alphastorm/omp-ninfer/issues/new?template=hardware-report.yml);
- a first failed setup step: [installation failure](https://github.com/alphastorm/omp-ninfer/issues/new?template=installation-failure.yml); or
- reproducible throughput/latency work: [performance result](https://github.com/alphastorm/omp-ninfer/issues/new?template=benchmark-report.yml).

Include:

- release and profile IDs;
- OS, GPU name, VRAM, driver, Docker, and OMP versions;
- install-to-first-turn time and every manual step for a clean-install report;
- the failing step and content-safe error; and
- whether the route was fresh, resumed, or tunnel-disconnected.

Exclude API keys, usernames, hostnames, IP addresses, private paths, prompts, model output, raw
request logs, and Docker inspection dumps. See [Troubleshooting](TROUBLESHOOTING.md) before attaching
anything.
