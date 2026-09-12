# Quickstart

> **Qualified on RTX 5090 · 4090 · 3090**

**Get started with the exact lane for your GPU and runtime.**

## Choose your lane

Choose by GPU and runtime before downloading anything. Client-platform qualification is separate
from GPU-runtime qualification.

| I have | Status | Start here | What success produces |
| --- | --- | --- | --- |
| RTX 5090 + Windows 11 / Docker Desktop WSL2 | **qualified release** | [RTX 5090 container lane](#ready-route-native-windows-and-docker-desktop-wsl2) | A first OMP turn plus the documented pass/fail acceptance observations |
| RTX 4090 + native Windows | **qualified release** | [RTX 4090 native lane](#native-windows-rtx-4090-and-rtx-3090-release-lanes) | The documented acceptance checks on the exact published package |
| RTX 3090 + native Windows | **qualified release** | [RTX 3090 native lane](#native-windows-rtx-4090-and-rtx-3090-release-lanes) | The documented acceptance checks on the exact published package |
| Any other GPU or deployment | **unsupported** | [Compatibility boundary](COMPATIBILITY.md) | No install attempt; the exact current support policy |

Each native lane is installable only through its exact manifest variant. Do not substitute GPU
family names, package URLs, component tags, or variant IDs between lanes.

## Verify the release before setup

The ready `v0.6.5` public release connects native Windows OMP over authenticated local loopback
to the exact runtime for the selected qualified lane. RTX 5090 uses
the digest-pinned image in the manifest through Docker Desktop WSL2. Managed macOS SSH and
native Linux clients are qualified client profiles under the same compatibility authority; RTX 4090
and RTX 3090 use separate native Windows packages.

Start only from the product tag and require its ready contract:

```sh
python3 scripts/verify_release.py --require-ready
```

That gate binds the Windows client archive and binary, compatibility authority, NInfer image/SBOM,
model, configuration, qualification summary, and clean-install acceptance receipt.

> [!WARNING]
> Stay on the exact OMP 18.0.9 beta archive pinned by this release. The config every route below
> installs (`examples/manual-tunnel/fail-closed.yml`) turns the client's startup update check
> off: a generic `omp update` would replace the client outside the release procedure and move it
> away from the checksummed bytes. Upgrade by cloning the next tag and rerunning the install step.

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
git clone --branch v0.6.5 --depth 1 https://github.com/alphastorm/omp-ninfer.git
Set-Location omp-ninfer
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
py -3 scripts\verify_release.py --require-ready
```

### Install the exact native Windows client

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
$Url = 'https://github.com/alphastorm/homebrew-omp/releases/download/omp-18.0.9-cross-platform-beta-2/omp-18.0.9-windows-x64.tar.gz'
$Expected = '0256dc25174766c5cdaca23e4e4361e0b95295cd05a075089a6bbf10de170ef9'
Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile omp-18.0.9-windows-x64.tar.gz
if ((Get-FileHash omp-18.0.9-windows-x64.tar.gz -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Expected) { throw 'OMP archive checksum mismatch' }
tar -xzf omp-18.0.9-windows-x64.tar.gz
& .\omp-18.0.9-windows-x64\install.ps1
& "$env:LOCALAPPDATA\OMP\omp.cmd" --version
```

The version must be `omp/18.0.9`. The installer retains the previous client pointer when one exists.

Inside WSL2, continue with **3. Prepare the model and key** and **4. Start NInfer** below. Skip
the macOS tunnel sections: Docker Desktop exposes the WSL2 loopback service to native
Windows at `127.0.0.1:18089`. Then use the **Native Windows OMP** provider instructions in
section 7 and the **Native Windows command forms** at the start of section 8.

## Native Windows RTX 4090 and RTX 3090 release lanes

These are separate native NInfer packages, not substitutions for the RTX 5090 image. The ready
manifest publishes exactly `rtx4090-windows-native` and `rtx3090-windows-native` as
qualified native lanes.

The RTX 3090 package identity is:

- filename: `ninfer-rtx3090-omp-v0.2.5-beta.1-windows-x86_64-cuda13.3-rtx3090.tar.gz`;
- SHA-256: `dbcd27c498d012d468f2eb757a34c085bacf597fa9ac0871ad61053dc72655e8`;
- byte count: `573,344,205`; and
- source commit: `9719ea0995c3100471bd2a21d1dfcc8453dd8e75`.

Its component-release slot is
[`alphastorm/ninfer@v0.2.5-qwen38-3090-beta.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.2.5-qwen38-3090-beta.1).
That URL must resolve at release cut; the ready product manifest remains authoritative for every
download URL and hash.

Prerequisites: Windows 11 x64, the matching single GPU with a current driver, Git, PowerShell,
Python 3 from python.org (its `py` launcher; the `python3` name Windows ships is a Microsoft
Store shortcut, not Python), and at least 40 GiB free. Install the OMP client first with
**Install the exact native Windows client** above; the lane's own steps follow. Start from an
elevated PowerShell. Windows ships with script execution disabled; the `Set-ExecutionPolicy`
line enables the release's hash-pinned scripts for this window only and changes nothing on the
machine - repeat it in any new window that runs one:

```powershell
git clone --branch v0.6.5 --depth 1 https://github.com/alphastorm/omp-ninfer.git
Set-Location omp-ninfer
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
py -3 scripts\verify_release.py --require-ready
```

Each lane has its own installed state root, its own served request model id, and one shared
loopback port. These values are the lane's, not interchangeable:

| Variant id | Installed state root | Request model id | Endpoint |
| --- | --- | --- | --- |
| `rtx4090-windows-native` | `%ProgramData%\NInfer\qwen38-4090-native` | `qwen3.8-27b` | `http://127.0.0.1:18082/v1` |
| `rtx3090-windows-native` | `%ProgramData%\NInfer\qwen38-3090-omp-v0.2` | `q38-ninfer` | `http://127.0.0.1:18082/v1` |

Both native lanes are text and tools only: Vision belongs to the RTX 5090 container profile
([`docs/FACTS.md`](FACTS.md)). Set `$VariantId` once for the matching GPU:

```powershell
$VariantId = 'rtx4090-windows-native'
```

or:

```powershell
$VariantId = 'rtx3090-windows-native'
```

Then let the manifest supply every URL and hash:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
$ErrorActionPreference = 'Stop'
$Manifest = Get-Content .\releases\v0.6.5\manifest.json -Raw | ConvertFrom-Json
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
if ($LASTEXITCODE -ne 0) { throw 'model artifact download failed' }
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
infer install authority from GPU-family names. RTX 4090 and RTX 3090 each use their exact
MTP3 profile. Structured JSON-schema output remains unsupported and fails closed.

### Operate the native lane

The installed controller is the only supported lifecycle surface, and every action needs the
lane's state root. Run these in the window that installed the lane; in a new elevated window,
first set `$StateRoot` to the lane's state root from the table above. `-Action Restart` does the
stop and the start in one step:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
$Controller = Join-Path $StateRoot 'Control-Release.ps1'
& $Controller -Action Status -StateRoot $StateRoot   # the installed release, its identity, endpoint state
& $Controller -Action Stop -StateRoot $StateRoot     # saves every live session, then exits
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
```

The environment-backed value exists only in that PowerShell process and its children. Do not put
the key itself in YAML, command arguments, shell history, or support bundles. In that process,
`& "$env:LOCALAPPDATA\OMP\omp.cmd" --model "$Provider/local-max"` opens an interactive session on
the lane; run the acceptance below first, it uses the same process without opening one.

### Native lane acceptance

Run these in the same PowerShell process that loaded `NINFER_NATIVE_API_KEY`:

```powershell
$Launcher = "$env:LOCALAPPDATA\OMP\omp.cmd"
$Smoke = Join-Path $env:TEMP ("omp-ninfer-native-" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $Smoke | Out-Null
Set-Content -NoNewline -Encoding ascii -Path (Join-Path $Smoke 'marker.txt') -Value 'OMP_NINFER_TOOL_OK'
Push-Location $Smoke
try {
  & $Launcher -p --no-session --auto-approve --model "$Provider/local-max" `
    'Use a file-reading tool to read marker.txt, then report its exact single line.'
  if ($LASTEXITCODE -ne 0) { throw 'text/tool acceptance failed' }

  $Session = Join-Path $Smoke 'sessions'
  & $Launcher -p --auto-approve --session-dir $Session --model "$Provider/local-max" `
    'Remember the nonce COBALT-493817 for my next turn. Acknowledge briefly.'
  if ($LASTEXITCODE -ne 0) { throw 'state setup failed' }
  & $Launcher -p --auto-approve --session-dir $Session --continue `
    'Return only the nonce from the prior turn.'
  if ($LASTEXITCODE -ne 0) { throw 'stateful resume failed' }
} finally { Pop-Location }

& $Controller -Action Stop -StateRoot $StateRoot | Out-Null
& $Launcher -p --no-session --auto-approve --max-time 20s `
  --model "$Provider/local-max" 'Return LOCAL_ONLY.'
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

- Apple silicon running the macOS version declared by the `omp-beta` cask;
- Homebrew and OpenSSH; and
- at least 1 GiB free for OMP and local state.

**Inference host**

- a single-user Linux or WSL2 environment owning one NVIDIA GeForce RTX 5090;
- a current NVIDIA driver, Docker with Linux host-network support, and NVIDIA Container Toolkit;
- OpenSSH access terminating in the same Linux/WSL namespace as Docker; and
- at least 40 GiB free for the 18,210,531,328-byte model, image, and logs.

The NInfer endpoint binds only to remote loopback. Never publish port `18089` on a LAN or public
interface. This release assumes both machines and local accounts are controlled by one trusted
owner.

## 1. Clone the exact release on both machines

From the public release tag, run this on the Mac and inference host:

```sh
git clone --branch v0.6.5 --depth 1 \
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
URL='https://github.com/alphastorm/homebrew-omp/releases/download/omp-18.0.9-cross-platform-beta-2/omp-18.0.9-macos-arm64.tar.gz'
EXPECTED='ba85e7aba6a6dba7d734e58d741c09798e8b3323f8abda0485bedafebc6c00c7'
curl --fail --location --output omp-18.0.9-macos-arm64.tar.gz "$URL"
test "$(shasum -a 256 omp-18.0.9-macos-arm64.tar.gz | cut -d ' ' -f 1)" = "$EXPECTED"
tar -xzf omp-18.0.9-macos-arm64.tar.gz
./omp-18.0.9-macos-arm64/install.sh
"${XDG_BIN_HOME:-$HOME/.local/bin}/omp" --version
)
```

The version must be `omp/18.0.9`. This native beta package uses the same current/previous client
pointer contract as Windows and Linux; it does not change the stable Homebrew cask. The installer
places the launcher in `${XDG_BIN_HOME:-$HOME/.local/bin}`; every later step in this guide calls
bare `omp`, so put that directory on `PATH` (`export PATH="$HOME/.local/bin:$PATH"`, and in your
shell profile if you want it to persist) before continuing.

## 3. Prepare the model and key on the inference host

From the release clone:

```sh
ROOT="$HOME/.local/share/omp-ninfer"
STATE="$HOME/.config/omp-ninfer"
LOGS="$HOME/.local/state/omp-ninfer"
CHECKPOINTS="$ROOT/checkpoints"
install -d -m 700 "$ROOT" "$STATE" "$LOGS" "$CHECKPOINTS"

MODEL_URL=$(python3 -c \
  'import json; print(json.load(open("releases/v0.6.5/manifest.json"))["components"]["model"]["artifact_url"])')
MODEL_BYTES=$(python3 -c \
  'import json; print(json.load(open("releases/v0.6.5/manifest.json"))["components"]["model"]["artifact_bytes"])')
MODEL_SHA256=$(python3 -c \
  'import json; print(json.load(open("releases/v0.6.5/manifest.json"))["components"]["model"]["artifact_sha256"])')
MODEL="$ROOT/qwen3_8_27b.ninfer"

curl --fail --location --continue-at - --output "$MODEL" "$MODEL_URL"
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

If `~/.omp/agent/models.yml` does not exist:

```sh
install -m 600 examples/manual-tunnel/models.fragment.yml \
  "$HOME/.omp/agent/models.yml"
```

If it already exists, merge only the `providers.ninfer-beta` mapping from
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
```

The environment-backed value exists only in that PowerShell process and its children. Do not put
the key itself in YAML, command arguments, shell history, or support bundles. The block refuses to
overwrite an existing OMP configuration; merge only `providers.ninfer-beta` and the `retry` mapping
when those files already exist. In that process,
`& "$env:LOCALAPPDATA\OMP\omp.cmd" --model ninfer-beta/local-max` opens an interactive session;
the **Native Windows command forms** in section 8 use the same process without opening one.

The sealed launcher owns config selection and deliberately rejects `--config`; the default config plus
the explicit provider/model disable model fallback. A tunnel or runtime failure must be an error, not a
switch to a cloud model.

## 8. Acceptance

Run these checks in order and record only pass/fail plus the content-safe identities from the NInfer
launcher.

### Native Windows command forms

Run from the tagged product clone in the same PowerShell process that loaded
`NINFER_BETA_API_KEY`:

```powershell
$Launcher = "$env:LOCALAPPDATA\OMP\omp.cmd"
$Smoke = Join-Path $env:TEMP ("omp-ninfer-acceptance-" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $Smoke | Out-Null
Set-Content -NoNewline -Encoding ascii -Path (Join-Path $Smoke 'marker.txt') -Value 'OMP_NINFER_TOOL_OK'
Push-Location $Smoke
try {
  & $Launcher -p --no-session --auto-approve --model ninfer-beta/local-max `
    'Use a file-reading tool to read marker.txt, then report its exact single line.'
  if ($LASTEXITCODE -ne 0) { throw 'text/tool acceptance failed' }
} finally { Pop-Location }

$Image = (Resolve-Path .\assets\icon-512.png).Path
& $Launcher -p --no-session --auto-approve --model ninfer-beta/local-max `
  ("@" + $Image) 'Describe the visible image in one sentence.'
if ($LASTEXITCODE -ne 0) { throw 'Vision acceptance failed' }

$Session = Join-Path $Smoke 'sessions'
& $Launcher -p --auto-approve --session-dir $Session --model ninfer-beta/local-max `
  'Remember the nonce COBALT-493817 for my next turn. Acknowledge briefly.'
if ($LASTEXITCODE -ne 0) { throw 'state setup failed' }
& $Launcher -p --auto-approve --session-dir $Session --continue `
  'Return only the nonce from the prior turn.'
if ($LASTEXITCODE -ne 0) { throw 'stateful resume failed' }
```

For the fail-closed check, stop the owned runtime from the tagged WSL2 clone, then issue one
native Windows request:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc 'cd ~/omp-ninfer && ./examples/manual-tunnel/stop-ninfer.sh'
& $Launcher -p --no-session --auto-approve --max-time 20s `
  --model ninfer-beta/local-max 'Return LOCAL_ONLY.'
if ($LASTEXITCODE -eq 0) { throw 'outage request unexpectedly succeeded' }
```

Expected result: a connection/authentication failure and no model response. Any cloud-provider
request is a release failure. Restart NInfer with section 4 only after observing the failure.

### macOS/Linux command forms

Run these in one terminal on the Mac, with the tunnel from section 5 open in another. Every check
is a `-p` (print) turn, so it exits on its own; the shell tests the outcome, and `set -e` stops
the sequence at the first failure.

### Text and tool turn

```sh
set -e
SMOKE=$(mktemp -d)
printf 'OMP_NINFER_TOOL_OK\n' > "$SMOKE/marker.txt"
cd "$SMOKE"
omp -p --no-session --auto-approve --model ninfer-beta/local-max \
  "Use a file-reading tool to read marker.txt, then report its exact single line." \
  | tee "$SMOKE/tool.txt"
grep -q OMP_NINFER_TOOL_OK "$SMOKE/tool.txt"
```

The turn must use the local model and execute the file-reading tool; the `grep` is the contract,
not the model's wording around it.

### Image input

The release clone ships a non-sensitive image; adjust the path to your clone:

```sh
omp -p --no-session --auto-approve --model ninfer-beta/local-max \
  @"$HOME/omp-ninfer/assets/icon-512.png" "Describe the visible image in one sentence." \
  | tee "$SMOKE/vision.txt"
test -s "$SMOKE/vision.txt"
```

A completed response proves the configured Vision route is reachable; this check belongs to the
RTX 5090 container lane only. Do not use private screenshots in an issue.

### Stateful follow-up and OMP resume

```sh
omp -p --auto-approve --session-dir "$SMOKE/sessions" --model ninfer-beta/local-max \
  "Remember the nonce COBALT-493817 for my next turn. Acknowledge briefly."
omp -p --auto-approve --session-dir "$SMOKE/sessions" --continue \
  "Return only the nonce from the prior turn." | tee "$SMOKE/resume.txt"
grep -q COBALT-493817 "$SMOKE/resume.txt"
```

The transcript remains authoritative. This checks OMP exit and resume with NInfer stateful
Responses while the server process stays up; the next check takes it down.

### Session survives the server process

A session is written to the durable store automatically once it passes 32,768 frontier tokens,
or on an explicit `POST /v1/ninfer/checkpoints` for its session digest. OMP derives that digest
from its own session identity, so this check uses the automatic path: it seeds a session past
the gate with the release's own documentation, restarts the server container on the inference
host, and continues.

```sh
cat "$HOME/omp-ninfer/docs/BENCHMARKS.md" "$HOME/omp-ninfer/README.md" \
    "$HOME/omp-ninfer/docs/ARCHITECTURE.md" "$HOME/omp-ninfer/docs/PERFORMANCE.md" \
    "$HOME/omp-ninfer/CHANGELOG.md" > "$SMOKE/context.md"
omp -p --auto-approve --session-dir "$SMOKE/durable" --model ninfer-beta/local-max \
  @"$SMOKE/context.md" "Hold this material in context. Remember the nonce COBALT-493817. Reply OK only."
ssh USER@RUNTIME_HOST docker restart --timeout 60 omp-ninfer-beta
until curl -sf -m 3 -o /dev/null http://127.0.0.1:18089/health; do sleep 3; done
omp -p --auto-approve --session-dir "$SMOKE/durable" --continue \
  "Return only the nonce I asked you to remember." | tee "$SMOKE/durable.txt"
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
if omp -p --no-session --max-time 20s --model ninfer-beta/local-max "Return LOCAL_ONLY."; then
  echo 'outage request unexpectedly succeeded' >&2; false
fi
```

Expected result: a connection failure and no model response, so the block ends without the
message. Any cloud-provider request is a release failure. Restart the tunnel only after observing
the failure.

## Fleet: three lanes in one OMP configuration

If you own more than one qualified lane, [`examples/fleet/`](../examples/fleet/) binds them into
one configuration with explicit roles: `ninfer-main/local-main` (RTX 5090) for the interactive
lead session, `ninfer-heavy/local-heavy` (RTX 4090) for long-context background workers, and
`ninfer-scout/local-scout` (RTX 3090) for bounded read-only scouting. Every lane stays
loopback-only on its own machine and serves one active request.

```sh
# three authenticated forwards; pass - to skip a lane you do not own
./examples/fleet/open-tunnels.sh USER@MAIN_HOST USER@HEAVY_HOST USER@SCOUT_HOST
install -m 600 examples/fleet/models.fragment.yml ~/.omp/agent/models.fleet.yml   # merge by hand
install -m 600 examples/fleet/agents/fleet-scout.md examples/fleet/agents/fleet-heavy.md ~/.omp/agent/agents/
```

The fleet is not a throughput claim. Its measured boundary is EXP-016 in
[`PERFORMANCE.md`](PERFORMANCE.md): on a fixed 14-job batch, cost-aware dispatch across the
three lanes completed the batch 2.07× faster than the RTX 5090 alone, naive dispatch 1.41×, and
pinning jobs by role alone 0.66×. Roles describe what a lane is for; where a job runs should
follow measured per-lane cost (`scripts/fleet_dispatch.py --policy cost`).

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
