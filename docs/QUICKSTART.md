# Early-access quickstart

The ready `v0.2.0-beta.1` route is native Windows OMP connected over authenticated local loopback
to the exact NInfer container in Docker Desktop WSL2 on one user-controlled RTX 5090. Managed
macOS SSH and native Linux clients are qualified profiles under the same compatibility authority.

Start only from the product tag and require its ready contract:

```sh
python3 scripts/verify_release.py --require-ready
```

That gate binds the Windows client archive and binary, compatibility authority, NInfer image/SBOM,
model, configuration, qualification summary, and clean-install acceptance receipt.

## Ready route: native Windows and Docker Desktop WSL2

### Prerequisites

- Windows 11 x64 and a single NVIDIA GeForce RTX 5090;
- Docker Desktop using Linux containers, WSL2 Ubuntu 24.04, and the NVIDIA container runtime;
- Git, PowerShell, and at least 40 GiB free for the model, image, client, and logs; and
- one trusted owner for Windows and the WSL2 runtime.

### Clone and verify the exact product release

Clone the tag in Windows and in the WSL2 namespace that owns Docker:

```powershell
git clone --branch v0.2.0-beta.1 --depth 1 https://github.com/alphastorm/omp-ninfer.git
Set-Location omp-ninfer
python3 scripts/verify_release.py --require-ready
```

### Install the exact native Windows client

```powershell
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

## Native Windows RTX 4090 beta and RTX 3090 preview

These are separate native NInfer packages, not substitutions for the primary RTX 5090 image. The
installable path accepts only `rtx4090-windows-native`. The RTX 3090 package is built and reviewed,
but its live-model and fresh-package gates still await validation hardware, so its manifest status
is `preview` and this script must refuse it; it stays published for inspection and hardware
reports. Start from an elevated PowerShell in the tagged product clone and let the manifest supply
every URL and hash:

```powershell
$VariantId = 'rtx4090-windows-native'
$Manifest = Get-Content .\releases\v0.2.0-beta.1\manifest.json -Raw | ConvertFrom-Json
$Variant = @($Manifest.components.ninfer_variants | Where-Object { $_.id -ceq $VariantId })
if ($Variant.Count -ne 1 -or $Variant[0].status -cne 'qualified') {
  throw 'requested native runtime variant is not uniquely qualified'
}
$Stage = Join-Path $env:TEMP ("omp-ninfer-" + $VariantId)
New-Item -ItemType Directory -Force -Path $Stage | Out-Null
foreach ($Asset in @(
  @{ Url = $Variant[0].package_url; Sha = $Variant[0].package_sha256 },
  @{ Url = $Variant[0].installer_url; Sha = $Variant[0].installer_sha256 },
  @{ Url = $Variant[0].controller_url; Sha = $Variant[0].controller_sha256 },
  @{ Url = $Variant[0].gpu_owner_controller_url; Sha = $Variant[0].gpu_owner_controller_sha256 }
)) {
  $Name = [IO.Path]::GetFileName(([Uri]$Asset.Url).AbsolutePath)
  $Path = Join-Path $Stage $Name
  Invoke-WebRequest -UseBasicParsing -Uri $Asset.Url -OutFile $Path
  if ((Get-FileHash $Path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Asset.Sha) {
    throw "native runtime asset checksum mismatch: $Name"
  }
}
$Package = Join-Path $Stage ([IO.Path]::GetFileName(([Uri]$Variant[0].package_url).AbsolutePath))
$Installer = Join-Path $Stage 'Install-Release.ps1'
$Model = Resolve-Path .\models\qwen3_8_27b.ninfer
$Key = Join-Path $Stage 'api-key.txt'
if (-not (Test-Path $Key)) {
  throw "create one random non-empty line at $Key, then rerun; never paste it into an issue"
}
& $Installer -PackagePath $Package -PackageSha256 $Variant[0].package_sha256 `
  -ModelArtifactPath $Model -ApiKeyFile $Key `
  -GpuOwnerControllerPath (Join-Path $Stage 'Control-GpuOwner.ps1')
```

The package controller binds loopback/Tailscale-only listening, mandatory bearer authentication,
the external model hash, process-restart checkpoints, and active/previous rollback. Do not mix
assets across variants or infer support from GPU-family names. RTX 3090 remains non-installable
until a later passing receipt closes its deferred live-model and fresh Windows package gates —
if you own a 3090, running the published acceptance boundary and filing a
[hardware report](https://github.com/alphastorm/omp-ninfer/issues/new/choose) is exactly the
evidence that closes them. RTX 4090 uses its exact MTP0 profile. Run the ordinary acceptance in
section 8 after installation. Structured JSON-schema output remains unsupported and fails closed.

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
interface. The first beta assumes both machines and local accounts are controlled by one trusted
owner.

## 1. Clone the exact release on both machines

After the prerelease is published, run this on the Mac and inference host:

```sh
git clone --branch v0.2.0-beta.1 --depth 1 \
  https://github.com/alphastorm/omp-ninfer.git
cd omp-ninfer
python3 scripts/verify_release.py --require-ready
```

Do not invite testers from moving `main`, an untagged archive, or a manifest whose status is
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
pointer contract as Windows and Linux; it does not change the stable Homebrew cask.

## 3. Prepare the model and key on the inference host

From the release clone:

```sh
ROOT="$HOME/.local/share/omp-ninfer"
STATE="$HOME/.config/omp-ninfer"
LOGS="$HOME/.local/state/omp-ninfer"
install -d -m 700 "$ROOT" "$STATE" "$LOGS"

MODEL_URL=$(python3 -c \
  'import json; print(json.load(open("releases/v0.2.0-beta.1/manifest.json"))["components"]["model"]["artifact_url"])')
MODEL_BYTES=$(python3 -c \
  'import json; print(json.load(open("releases/v0.2.0-beta.1/manifest.json"))["components"]["model"]["artifact_bytes"])')
MODEL_SHA256=$(python3 -c \
  'import json; print(json.load(open("releases/v0.2.0-beta.1/manifest.json"))["components"]["model"]["artifact_sha256"])')
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
  --log-dir "$LOGS"
```

The launcher:

- refuses a draft manifest;
- pulls the digest-pinned image;
- checks the model and `ninfer-serve` binary hashes;
- starts one owned `omp-ninfer-beta` container with restart policy `no`;
- mounts the model and API key read-only;
- shares the Linux/WSL2 host network namespace and binds `127.0.0.1:18089` only; and
- waits for authenticated status to match source, binary, model, configuration, profile, and runtime
  fields.

It deliberately leaves a failed container in place for `docker logs omp-ninfer-beta`. Stop and
remove only the correctly labelled beta container with:

```sh
./examples/manual-tunnel/stop-ninfer.sh
```

The server receives the key through a read-only secret mount and an in-container shell expansion,
so the key is not embedded in the Docker configuration or host shell history. The resulting server
process argument is visible to root inside the trusted container/host boundary; this is not a
multi-tenant secret-isolation design.

## 5. Open the tunnel from the Mac

In a dedicated terminal inside the Mac release clone:

```sh
./examples/manual-tunnel/open-tunnel.sh USER@RUNTIME_HOST
```

Replace the destination with the SSH user and host that terminate in the Linux/WSL namespace owning
Docker. Keep this process running. `ExitOnForwardFailure` prevents a false-green tunnel when local
port `18089` is occupied; keepalive options make a dead route observable.

## 6. Install the same key on the Mac

In another Mac terminal:

```sh
install -d -m 700 "$HOME/.omp/agent"
umask 077
ssh USER@RUNTIME_HOST 'cat "$HOME/.config/omp-ninfer/api-key"' \
  > "$HOME/.omp/agent/ninfer-beta.key"
chmod 600 "$HOME/.omp/agent/ninfer-beta.key"
```

This streams the secret inside SSH and does not print it. Use the exact destination from the tunnel.
Do not paste the key into YAML, shell history, an issue, or a support bundle.

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
& "$env:LOCALAPPDATA\OMP\omp.cmd" --model ninfer-beta/local-max
```

The environment-backed value exists only in that PowerShell process and its children. Do not put
the key itself in YAML, command arguments, shell history, or support bundles. The block refuses to
overwrite an existing OMP configuration; merge only `providers.ninfer-beta` and the `retry` mapping
when those files already exist.

The sealed launcher owns config selection and deliberately rejects `--config`; the default config plus
the explicit provider/model disable model fallback. A tunnel or runtime failure must be an error, not a
switch to a cloud model.

## 8. Early-access acceptance

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

### Text and tool turn

```sh
SMOKE=$(mktemp -d)
printf 'OMP_NINFER_TOOL_OK\n' > "$SMOKE/marker.txt"
cd "$SMOKE"
omp --model ninfer-beta/local-max \
  "Use a file-reading tool to read marker.txt, then report its exact single line."
```

The turn must use the local model and successfully execute the file-reading tool. Model wording is
not a numerical oracle; the observed tool result is the contract.

### Image input

From a directory containing a non-sensitive PNG or JPEG:

```sh
omp --model ninfer-beta/local-max \
  @sample.png "Describe the visible image in one sentence."
```

A completed response proves the configured Vision route is reachable. Do not use private screenshots
in an issue.

### Stateful follow-up and OMP resume

Start an interactive session:

```sh
omp --model ninfer-beta/local-max \
  "Remember the nonce COBALT-493817 for my next turn."
```

In the same session, ask for the nonce. Exit OMP normally, then resume that session:

```sh
omp --model ninfer-beta/local-max --continue \
  "Return the nonce from the prior turn."
```

The transcript remains authoritative. This checks ordinary OMP exit/resume with NInfer stateful
Responses while the NInfer process remains alive; it does **not** claim NInfer process-restart
continuation.

### Fail closed

For the managed macOS route, stop the tunnel with `Ctrl-C`, then run:

```sh
omp --no-session --max-time 20s \
  --model ninfer-beta/local-max \
  "Return LOCAL_ONLY."
```

Expected result: a connection failure and no model response. Any cloud-provider request is a release
failure. Restart the tunnel only after observing the failure.

## 9. Send feedback

Use the repository issue forms. Include:

- release and profile IDs;
- OS, GPU name, VRAM, driver, Docker, and OMP versions;
- the failing step and content-safe error; and
- whether the route was fresh, resumed, or tunnel-disconnected.

Exclude API keys, usernames, hostnames, IP addresses, private paths, prompts, model output, raw
request logs, and Docker inspection dumps. See [Troubleshooting](TROUBLESHOOTING.md) before attaching
anything.
