# Quickstart

> **Versioned guide: v0.18.0 · stock Oh My Pi 18.18.7 · Qualified on RTX 5090 · 4090 · 3090**
>
> All 31 documented install and verification blocks passed, and both native post-route campaigns and public installs passed (on RTX 3090, in the third execution after reclaiming host disk space; [release notes](../releases/v0.18.0/NINFER_RELEASE_NOTES.md) · [acceptance evidence](#acceptance-evidence)).

OMP NInfer is the qualified local inference appliance and release layer connecting the
[Oh My Pi](https://github.com/can1357/oh-my-pi) (OMP) coding-agent client over authenticated
loopback to the NInfer inference engine serving Qwen3.8 27B on your GPU.

## Choose your lane

| GPU and host | Client route in v0.18.0 | Start here |
| --- | --- | --- |
| RTX 5090 container on Windows 11 + Docker Desktop / WSL2 | Native Windows x64 client over local loopback `127.0.0.1:18089` | [RTX 5090 Windows route](#ready-route-native-windows-and-docker-desktop-wsl2) |
| RTX 5090 container on Windows 11 / WSL2 or Linux | macOS arm64 client over a manual SSH tunnel (preview) | [macOS manual SSH route (preview)](#macos-client-over-a-manual-ssh-tunnel-preview) |
| RTX 4090 native Windows 11 (alone or beside RTX 3090) | Native Windows x64 client over local loopback `127.0.0.1:18082`; UUID-bound; `v0.8.0-qwen38-4090-beta.3`, DFlash2 K=7, one request at a time (`C1`); component qualification, seven documented blocks, campaign, public install and restoration passed | [RTX 4090 native lane](#native-windows-rtx-4090-release-lane) |
| RTX 3090 native Windows 11 (alone or beside RTX 4090) | Native Windows x64 client over local loopback `127.0.0.1:18082`; UUID-bound; `v0.8.0-qwen38-3090-beta.3`, DFlash2 K=7, two requests in flight (`C2`) over one shared 131,072-token pool; component qualification, seven documented blocks, post-route C2 campaign, public install and restoration passed in the third execution after reclaiming host disk space (see [Acceptance evidence](#acceptance-evidence)) | [RTX 3090 native lane](#native-windows-rtx-3090-release-lane) |
| RTX 5090 container with Linux x64 client under WSL2 only | WSL2 shell client over local loopback `127.0.0.1:18089` (no native Linux OS qualification) | [WSL2 Linux client](#wsl2-linux-client-over-local-loopback) |
| Other GPU, non-WSL Linux client, or concurrent native serving | Unsupported | [Compatibility boundary](COMPATIBILITY.md) |

## Before you start

- **Clone the tag and run the ready gate:** start from a clean clone of `v0.18.0` and verify
  `python3 scripts/verify_release.py --require-ready` (`py -3 scripts\verify_release.py --require-ready`
  on Windows). Never install from a moving branch, an untagged archive, or a manifest that has not
  passed the ready gate.
- **Keep one release authority end to end:** stock OMP has no `omp appliance` commands, and
  `examples/manual-tunnel/fail-closed.yml` pins `update.auto=false`, `startup.checkUpdate=false`
  and `startup.setupWizard=false`. Do not run `omp update`: an explicit operator command can
  still replace the checksummed binary. Never mix current fragments with a legacy `v0.10.0` or
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
  Native RTX 4090 retains its `32768 MiB` host floor and shared Host budget `15747.734375 MiB`
  (16,512,696,320 bytes); RTX 3090 uses a shared Host budget of `20867.734375 MiB` (21,881,405,440 bytes).
  These replace separate host-slot/KV budgets; no smaller-host qualification is claimed.

## Contributor acceptance and preflight

You can exercise the stock client without a GPU: run
`python3 scripts/client_acceptance.py --omp ./omp-darwin-arm64 --omp-sha256 SHA256 --omp-version omp/18.18.7 --local-rehearsal --receipt rehearsal.json`,
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
their model files must be supplied explicitly with `-GroupwiseIntModel` (and `-Nvfp4Model` on
the RTX 5090 launcher). Their staged quality child requires the selected model ID rather than
keeping another default.

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

<a id="omp-18186-client"></a>

## OMP 18.18.7 client

Release `v0.18.0` selects unmodified upstream
[Oh My Pi v18.18.7](https://github.com/can1357/oh-my-pi/releases/tag/v18.18.7), source
`e325ffc73ab86e03bdd20a91b77d8e2b3964c906`, tree
`9ba2abe1f1dd7c64b8d3f99dc0e41d689d96886c`, release `440868478`.
The [release notes](../releases/v0.18.0/NINFER_RELEASE_NOTES.md) and release-local
`qualification/client-components.json` bind the exact platform assets. The
[18.18.6→18.18.7 review](measurements/2026-11-11-omp-18187-client-upgrade-review.json)
covers source behavior and independent public-download integrity, not client execution or live acceptance.

| Platform | Published binary | SHA-256 |
| --- | --- | --- |
| Windows x64 | `omp-windows-x64.exe` (250,108,928 bytes) | `4a6e39ea34633e03d07a1543ba30842362311f920341378433aa31b6c1404491` |
| macOS arm64 | `omp-darwin-arm64` (221,982,864 bytes) | `0cecaac781d3c37f32ff7ecf3b6ba94842e7f058358e4748d5071d772f0aa4df` |
| Linux x64 under WSL2 | `omp-linux-x64` (286,136,496 bytes) | `ea6c216feb260a3766a591760aad06bdc608efd5c632912603f5ccb41b0a4bb1` |

- **Keep the three working compat keys:** per model, `compat.statefulResponses: true`,
  `compat.includeEncryptedReasoning: false`, `compat.supportsReasoningSummary: false`.
  Remove obsolete operator `compat.thinkingLoopGuard`; the current schema/catalog does not use
  that operator key. Leave the actual guard enabled and clear `PI_NO_THINKING_LOOP_GUARD`.
- **Clear `PI_OPENAI_STATEFUL`** from environments and scripts; an inherited `0` disables chaining.
  Omit old `compat.supportsImageDetailOriginal` overrides; custom Responses image detail stays auto.
- **Preserve exact selectors and effort:** `ninfer-beta/q38-ninfer`,
  `ninfer-native-3090/q38-ninfer`, `ninfer-native-4090/qwen3.8-27b`, and the worker's
  `ninfer-heavy/qwen3.8-27b:medium`. Keep high→medium/off→low clamps, the stock
  `qwen3.8-27b` replace / opaque `q38-ninfer` hashline edit defaults, declared 131072/32768 limits,
  static fragments and existing concurrency limits. No discovery, service tiers, /fast, effortMap
  or per-call-model opt-in is introduced. The stock default `high` is clamped to `medium` by
  these explicit effort lists; do not remove them or send raw `high` to the shipped Qwen
  template. Pin `tokenizer: qwen3` on the four opaque `q38-ninfer` model entries; the
  canonical `qwen3.8-27b` entries already infer qwen3 and need no tokenizer override.
- **Keep exact-loop detection on:** short whole-line/newline-spanning cycles retain four repeats
  but now need 1024 repeated characters; short non-newline cycles remain four/180 and long cycles
  three/1024. A truly induced loop must still fail closed. Uninduced boundaries are not passes.
- **Keep default compaction:** reserve 19660 and strict >111412 trigger remain. The ordinary
  summary output cap with an unset reserve is 13107, not the route's 32768. Length-stopped main, turn-prefix, handoff
  and branch summaries fail visibly without committing partial context; a completed main summary
  survives a truncated display-only short summary. Manual compaction now waits for persistence
  replacement before delivering queued background results. Failure/cancellation and restart
  continuation remain separate checks; snapcompact reader accounting adds no new vision scope.
- **Keep explicit fail-closed settings:** install or merge
  [fail-closed.yml](../examples/manual-tunnel/fail-closed.yml), including `retry.enabled=false`,
  `retry.modelFallback=false` and `fallbackRevertPolicy=never`. `retry.enabled=false` alone does
  not block the new missing-key pre-prompt fallback. Selected-provider outage must remain a failed
  turn with no model content/provider switch and the original request-count oracle.
- **Isolate auxiliary credentials:** ordinary file-read/nonce/outage routes do not request job
  captions or optional auto-learn capture. A separately exercised eligible >15 s background job
  can request a widget caption, whose role resolver may use smol credentials independently of
  modelFallback. Use local-only auth for acceptance; separately attribute optional side requests.
  Do not silently enable optional features or inherit cloud credentials to obtain coverage.
- **Replay stays transcript-owned:** shared transport cleanup removes only
  `internal_chat_message_metadata_passthrough` from replay copies, preserving legal metadata,
  content and tool pairing without rewriting stored history. Native remote compaction is not
  opted into. Repeat real continuation, tool/nonce, exit and checkpoint-owner restart gates with
  the exact new platform binaries; source equality is not binary qualification.
- **Windows shell behavior:** the stock bash tool describes Windows command forms and resolves
  cmd-style and MSYS drive paths. Use the native Windows instructions below; a file-reading tool
  check alone does not establish that bash commands or edits behaved correctly.

## Acceptance evidence

On 2026-11-12, frozen candidate `2a735da0367214b35a325f61865fb47f0ce872c7` passed the documented
blocks on all five routes: RTX 5090 host **2/2**, macOS **10/10**, Windows **5/5**, RTX 4090
**7/7** and RTX 3090 **7/7** (**31/31 executable blocks**). All three stock OMP 18.18.7 client
platform checks passed. The RTX 5090 incumbent was restored after a **406.876 s** hold.
RTX 4090 passed its post-route campaign, public install and independent restoration on its initial
window, and RTX 3090 passed every phase on its third execution without a waiver. See
[route receipts](../releases/v0.18.0/acceptance/documented-routes.json) and
[composition](../releases/v0.18.0/acceptance/composed-external-installation.json).

**RTX 3090 acceptance history (three executions, no waiver):** attempt 1 passed all seven
documented install and verification blocks, failed its post-route stock OMP subagent check on
malformed `task` tool arguments (five calls rejected for a missing `context` argument), and
restored the installed lane. Attempt 2 passed the seven documented blocks and subagent/session
checks, but ran while the host's system drive was full (`0.39 GiB` free when measured afterwards): `27` checkpoint writes
failed with the operating system's disk-full error (Windows error `112`), checkpoint saves were
refused for `capacity`, admission waited behind an outstanding checkpoint save across `4` HTTP
`503` `request_queue_timeout` responses before a **900 s** compaction timeout,
`Control-Release.ps1 -Action Stop` refused **9** sessions, and empty-session `Start`/`Stop`
recovery restored the installed lane with an unchanged two-GPU host state. After reclaiming free
disk space, the founder authorized a third execution on the unchanged candidate in fresh workspaces
with an enforced **60 GiB** test-host free-space floor (`63.08` GiB free before
acceptance; operators need at least `40 GiB` free on the install/checkpoint volume), recorded in
`scripts/hosts/accept-rtx4090-route.py`'s single `--attempt 2` rerun slot because the frozen
candidate driver accepts only `--attempt 1` or `--attempt 2`. Attempt 3 passed every phase (`7/7`
documented blocks, sequential multi-branch, two-request concurrent fanout, parallel-session and
subagent checks, `2` committed automatic compactions in
`747.00` s with zero HTTP `503` responses (compaction receipt `cfa89628`), anonymous public
install, and independent restoration in `1,439.367` s). The request-level HTTP `503`
half of [#89](https://github.com/alphastorm/ninfer/issues/89) reproduced in acceptance only under
disk exhaustion in attempt 2 and did not reproduce with free space in attempt 3, while its
pressure-save deferral path remains tracked in `#89`.
No prior native campaign failure is relabeled as a pass, and no predecessor waiver is renewed.

macOS stays preview; Linux is WSL2-only; image input covers macOS/Windows against RTX 5090 only.
Native component qualification remains separate from product-route acceptance. Previous client,
runtime and route results do not qualify these new bytes. The
[immutable v0.17.0 guide](https://github.com/alphastorm/omp-ninfer/blob/v0.17.0/docs/QUICKSTART.md)
retains that release's results and limitations. See [Releases](RELEASES.md).

## Current release at a glance

The following identities bind the selected component bytes; the ready gate remains install authority.

| Lane | Runtime component and source | Model artifact | Serving profile and limits |
| --- | --- | --- | --- |
| RTX 5090 container (`127.0.0.1:18089`) | `v0.7.0-qwen38-5090-beta.7`; tag commit `48c8ac4644322f024b5c3bd5b657af5874567251`; source `48c8ac4644322f024b5c3bd5b657af5874567251`; server `804ef8ac6d062dc8da8784ba3f52e5cece2178a5f5bc46cb2c7bc1d3e8937fe3`; archive `823d9357f90051564068a8504695a0ec57eb4016681bfd83097f453fcf9eb6ae` (`580020196` bytes) | Published v3 `81f924d4` (20,437,521,664 bytes) | `qwen38-5090-v0.13.0` / config `751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47`; strict origin auth, DFlash2 K7, BF16 KV, 131,072 context, C2, two extra device-state slots, 180 s pending timeout; host store `checkpoints-v018` |
| RTX 4090 native Windows (`127.0.0.1:18082`) | `v0.8.0-qwen38-4090-beta.3`; tag commit `48c8ac4644322f024b5c3bd5b657af5874567251`; source `48c8ac4644322f024b5c3bd5b657af5874567251`; package `ac41700ac2bb9fb171188f35e73481cfd9f1140c5781320b1e6304ee760d7166` (`992131123` bytes); server `a5266ae676305cc56086df6d3b8dc8968be110b3cf0eb7b18147adafc2f66d22`; config `b71a2cff25d671703106474d86fe6a808dc803db28703b6fd7740013fcfee278` | Same model v3 | INT8 DFlash2 K7, 131,072 context, C1, 30 s pending timeout, two extra slots, 1,024-token prefill, 640 MiB admission headroom |
| RTX 3090 native Windows (`127.0.0.1:18082`) | `v0.8.0-qwen38-3090-beta.3`; tag commit `48c8ac4644322f024b5c3bd5b657af5874567251`; source `48c8ac4644322f024b5c3bd5b657af5874567251`; package `bf1ceaa9eb522a8c8d9372bec475d6e4e4666e6a995302cd20035e80ae3e5edd` (`1011087765` bytes); server `e571328699be41d90eff8743d94da26e8f587e48bc32f618013625af7ad0bfe0`; config `674d52609e22de54a5db20001e25fdd97cd600d498551ecfe48efa53964fc3ac` | Same model v3 | INT8 DFlash2 K7, C2 over one 131,072-token pool, 180 s pending timeout, two extra slots, 1,024-token prefill, 768 MiB headroom, 350 W serving cap |

The RTX 5090 image is
`ghcr.io/alphastorm/ninfer-runtime@sha256:496195ecd6cf1f50fcd9dc62cf7b51787f599cc2b196e194baf050c4b149e119`.
The [manifest](../releases/v0.18.0/manifest.json) binds all three rebuilt components to one
exact engine source and the published v3 model. Use its selected configuration and packaged
launcher without adding experimental flags. New source bytes alone do not imply a performance
gain or checkpoint compatibility; acceptance applies only to the exact bound bytes and routes.

- **Sequential native ownership:** both native lanes are UUID/PCI-bound on a two-GPU Windows host
  and share port 18082. Stop the other lane first; C2 means two requests within the one active
  RTX 3090 lane, not concurrent native-lane serving. Keep prior roots/staging/checkpoints for rollback.
- **Checkpoint boundary:** restore requires the same binary, model, profile and bearer key. Saves
  are best effort under traffic; authoritative OMP transcripts remain replayable. The new container
  host store `checkpoints-v018` is separate from predecessor `checkpoints-v017`, while the
  container mount stays `/checkpoints-v013`. Never import prior generations or write into the
  predecessor store.
- **Session capability:** `prompt_cache_key` names a session within one authenticated API-key
  principal. Use high-entropy unique keys; do not share that principal among mutually untrusted clients.
- **Native durability:** the native schema-3 store is
  `cache/<release-instance-id>/session-checkpoints-v3`, such as
  `qwen38-4090-native-v0.8.0-beta.3-48c8ac464432`. Both native profiles require strict origin auth
  and a bearer key of at least 32 bytes. Preserve legacy generations without migration.
- **Legacy owners:** use the immutable [v0.10.0 guide](https://github.com/alphastorm/omp-ninfer/blob/v0.10.0/docs/QUICKSTART.md)
  or [v0.7.2 guide](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md) for those lineages;
  do not mix their clients/fragments with this route.

## Ready route: native Windows and Docker Desktop WSL2

### Prerequisites

Windows 11 x64 with one RTX 5090, Docker Desktop (Linux containers, WSL2 Ubuntu 24.04, NVIDIA
container runtime), Git, PowerShell, Python 3 from python.org (`py` launcher, not the Microsoft
Store `python3` alias), 40 GiB free disk, and one trusted owner.

### Clone and verify the exact product release

Clone the tag in Windows and in the WSL2 distro that owns Docker (`Set-ExecutionPolicy` applies to
the current window only):

```powershell
git clone --branch v0.18.0 --depth 1 https://github.com/alphastorm/omp-ninfer.git
if ($LASTEXITCODE -ne 0) { throw 'release clone failed' }
Set-Location omp-ninfer
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
py -3 scripts\verify_release.py --require-ready
if ($LASTEXITCODE -ne 0) { throw 'ready gate failed' }
```

### Install the exact native Windows client

```powershell
$ErrorActionPreference = 'Stop'
$Url = 'https://github.com/can1357/oh-my-pi/releases/download/v18.18.7/omp-windows-x64.exe'
$Expected = '4a6e39ea34633e03d07a1543ba30842362311f920341378433aa31b6c1404491'
Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile omp-windows-x64.exe
if ((Get-FileHash omp-windows-x64.exe -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Expected) { throw 'OMP binary checksum mismatch' }
$Launcher = "$env:LOCALAPPDATA\OMP\omp.exe"
New-Item -ItemType Directory -Force -Path (Split-Path $Launcher) | Out-Null
Copy-Item .\omp-windows-x64.exe $Launcher -Force
Remove-Item Env:PI_OPENAI_STATEFUL -ErrorAction SilentlyContinue
& $Launcher --version
if ($LASTEXITCODE -ne 0) { throw 'OMP version check failed' }
```

The client version must be `omp/18.18.7` (to roll back, verify the previous pinned binary's
checksum before replacing `omp.exe`). Inside WSL2, run **3. Prepare the model and key** and
**4. Start NInfer** below, skip sections 5–6 (Docker Desktop exposes `127.0.0.1:18089` to native
Windows), then run **Native Windows OMP** in section 7 and **Native Windows command forms** in
section 8.

## Native Windows RTX 4090 release lane

Requires Windows 11 x64, one RTX 4090 (sm_89), a supported NVIDIA driver, Git, PowerShell, Python 3
(`py` launcher), and 40 GiB free disk. The installer binds the unique RTX 4090 UUID and PCI address
even beside an RTX 3090 (use `-GpuUuid` if multiple RTX 4090 cards exist; never hide a card). Stop
the other native lane on port `18082` first. The v0.18.0 route selects
`v0.8.0-qwen38-4090-beta.3`, with DFlash2 K=7, INT8 KV and C1; fresh component qualification passed.
The installer preserves the actual prior install for rollback. Keep prior native release roots
and staging untouched for historical recovery; never import MTP3 checkpoints into the DFlash2
runtime. If a stopped beta.2 incumbent refuses shutdown, follow the
[native upgrade recovery](#upgrading-after-a-beta2-incomplete-shutdown) before attempting the installer.

```powershell
git clone --branch v0.18.0 --depth 1 https://github.com/alphastorm/omp-ninfer.git
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
$Manifest = Get-Content .\releases\v0.18.0\manifest.json -Raw | ConvertFrom-Json
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

Inspect a refused Stop before proceeding. `Restart` first runs Stop and can refuse before
starting anything; a deliberate `Start` accepts the loss of unsaved sessions and begins a new
launch. Do not delete an owner lease or discard checkpoints. See
[shared native operation and fallback](#shared-native-operation-and-fallback).

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
$Controller = Join-Path $StateRoot 'Control-Release.ps1'
& $Controller -Action Status -StateRoot $StateRoot   # the installed release, its identity, endpoint state
if ($LASTEXITCODE -ne 0) { throw 'native status failed' }
& $Controller -Action Stop -StateRoot $StateRoot     # checkpoints live sessions; inspect any refusals
if ($LASTEXITCODE -ne 0) { throw 'native stop failed; do not restart after a refusal' }
& $Controller -Action Start -StateRoot $StateRoot    # the same command brings the lane back after a reboot
if ($LASTEXITCODE -ne 0) { throw 'native start failed' }
& $Controller -Action Status -StateRoot $StateRoot
if ($LASTEXITCODE -ne 0) { throw 'native status failed' }
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
port `18082` first. The v0.18.0 route selects `v0.8.0-qwen38-3090-beta.3`, with DFlash2 K=7
and C2 sharing one 131,072-token INT8 KV pool, OMP provider limit `2` and a 180 s pending
timeout; fresh component qualification, route, `C2` campaign, public install and restoration passed
(keep that `40 GiB` free-disk margin on the volume holding the install and checkpoint store so
saves are not refused for disk capacity; pressure-save admission deferral remains tracked in
[#89](https://github.com/alphastorm/ninfer/issues/89)). C2 is not simultaneous native-lane serving.
The installer stops a running incumbent with that incumbent's own controller
and power policy, so the historical stop-first workaround ([#94](https://github.com/alphastorm/omp-ninfer/issues/94))
is no longer required. Keep all predecessor roots, staging, and checkpoints for rollback; MTP3
checkpoints do not transfer into DFlash2. If a stopped beta.2 incumbent refuses shutdown, follow
the [native upgrade recovery](#upgrading-after-a-beta2-incomplete-shutdown) before attempting the installer.

```powershell
git clone --branch v0.18.0 --depth 1 https://github.com/alphastorm/omp-ninfer.git
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
$Manifest = Get-Content .\releases\v0.18.0\manifest.json -Raw | ConvertFrom-Json
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

Inspect a refused Stop before proceeding. `Restart` first runs Stop and can refuse before
starting anything; a deliberate `Start` accepts the loss of unsaved sessions and begins a new
launch. Do not delete an owner lease or discard checkpoints. See
[shared native operation and fallback](#shared-native-operation-and-fallback).

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
$Controller = Join-Path $StateRoot 'Control-Release.ps1'
& $Controller -Action Status -StateRoot $StateRoot   # the installed release, its identity, endpoint state
if ($LASTEXITCODE -ne 0) { throw 'native status failed' }
& $Controller -Action Stop -StateRoot $StateRoot     # checkpoints live sessions; inspect any refusals
if ($LASTEXITCODE -ne 0) { throw 'native stop failed; do not restart after a refusal' }
& $Controller -Action Start -StateRoot $StateRoot    # the same command brings the lane back after a reboot
if ($LASTEXITCODE -ne 0) { throw 'native start failed' }
& $Controller -Action Status -StateRoot $StateRoot
if ($LASTEXITCODE -ne 0) { throw 'native status failed' }
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

## Native upgrade recovery

This guidance applies to both native GPU lanes. Use the variables from the selected lane's
verified download/install steps above, not those of the other lane.

### Upgrading after a beta.2 incomplete shutdown

If the native beta.2 lane is stopped, every `Stop` reports `incomplete shutdown`, and the
installer reports `non-running incumbent retains a GPU-owner lease`, do not delete the lease,
runtime files, or checkpoints. Keep the diagnostic receipts and your OMP transcripts. Unsaved
server-side session state from that shutdown is lost; continue only when you accept restarting
from saved state or replaying the transcript.

Using the same state root, first **Start the installed beta.2 release**, then run the normal
beta.3 installer **while it is running**. Use the package, model, key and stage variables from
this lane's verified download/install steps, with the existing state root and key. Run in an
elevated PowerShell session:

```powershell
$ErrorActionPreference = 'Stop'
$Controller = Join-Path $StateRoot 'Control-Release.ps1'
$StartResult = @(& $Controller -Action Start -StateRoot $StateRoot)
if ($LASTEXITCODE -ne 0) { throw 'native start failed' }
$Lifecycle = (($StartResult -join "`n") | ConvertFrom-Json)
if ([string]$Lifecycle.process_state -cne 'running' -or
    [string]$Lifecycle.task_state -cne 'Running' -or
    [string]$Lifecycle.endpoint_state -cne 'ready') {
  throw 'native start did not report a ready release'
}

$Installer = Join-Path $Stage 'Install-Release.ps1'
& $Installer -PackagePath $Package -PackageSha256 $Variant[0].package_sha256 `
  -ModelArtifactPath $Model -ApiKeyFile $ApiKeyFile -StateRoot $StateRoot `
  -GpuOwnerControllerPath (Join-Path $Stage 'Control-GpuOwner.ps1')
if ($LASTEXITCODE -ne 0) { throw 'native install failed' }
```

The block requires Start to succeed and return lifecycle JSON with
`process_state: "running"`, `task_state: "Running"` and
`endpoint_state: "ready"`. The installer stops beta.2 with its own controller, preserves it as
the previous release, and returns an install receipt with `status: "passed"` and the new
release ready. The block stops if Start fails, the lane is not ready, or the installer fails.
If the next shutdown also refuses, stop and inspect that new refusal; do not bypass it by
editing ownership files.
Keep all predecessor release, key and checkpoint directories for exact rollback.

## Shared native operation and fallback

These rules apply to both native GPU lanes.

### What an explicit Start means after a refusal

An explicit `Start` after an incomplete shutdown starts a new launch and clears the previous
launch's shutdown refusal. It does not retry the failed saves: sessions not saved at that
shutdown are lost. Previously saved checkpoints and the OMP transcript remain available under
their existing compatibility rules. The old `last_stop` diagnostic can still show the
incomplete shutdown until another Stop replaces it. `Restart` is not equivalent: it first
runs Stop and can refuse before starting anything.

### What blocks rollback

For shutdown-save failures, rollback is blocked by a valid report tied to the last launch that
says shutdown was incomplete or that sessions were refused. A missing or unreadable report, a
nonzero server exit, or a timeout-killed shutdown does **not by itself** block rollback. These
are not proof that sessions were saved; inspect the last-stop receipt before proceeding.
Other safety checks still apply, including proving that the server has stopped and that a
previous release exists.

### Package selection and fallback

Each native GPU lane publishes **one selected package per component tag**. The fallback from
native beta.3 is exact rollback to that lane's retained `v0.8.0-qwen38-3090-beta.2` or
`v0.8.0-qwen38-4090-beta.2` installation, using
`Control-Release.ps1 -Action Rollback -StateRoot $StateRoot`. It is not an in-place switch to
another build profile of the same source. Keep the previous release, its key and its
checkpoint directories; a fresh install without a retained previous release has no exact
rollback target. Do not uninstall to change profiles: uninstall removes the retained state
needed for rollback.

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
CLIENT='releases/v0.18.0/qualification/client-components.json'
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
tunnel, without a managed macOS installer or appliance service). Its **10/10** executable blocks
passed fresh v0.18.0 acceptance against the `v0.7.0-qwen38-5090-beta.7` RTX 5090 container lane. Sections 3 and 4 also serve as
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
git clone --branch v0.18.0 --depth 1 \
  https://github.com/alphastorm/omp-ninfer.git &&
cd omp-ninfer &&
python3 scripts/verify_release.py --release v0.18.0 --require-ready
```

## 2. Install the OMP beta on the Mac

Despite the retained heading, this installs the stock Oh My Pi 18.18.7 binary (`omp-darwin-arm64`):

```sh
(
set -euo pipefail
URL='https://github.com/can1357/oh-my-pi/releases/download/v18.18.7/omp-darwin-arm64'
EXPECTED='0cecaac781d3c37f32ff7ecf3b6ba94842e7f058358e4748d5071d772f0aa4df'
curl --fail --location --output omp-darwin-arm64 "$URL"
test "$(shasum -a 256 omp-darwin-arm64 | cut -d ' ' -f 1)" = "$EXPECTED"
mkdir -p "$HOME/.local/bin"
cp omp-darwin-arm64 "$HOME/.local/bin/omp"
chmod 0755 "$HOME/.local/bin/omp"
unset PI_OPENAI_STATEFUL
"$HOME/.local/bin/omp" --version
)
```

The version must be `omp/18.18.7`; add `$HOME/.local/bin` to `PATH` before continuing.

## 3. Prepare the model and key on the inference host

```sh
ROOT="$HOME/.local/share/omp-ninfer"
STATE="$HOME/.config/omp-ninfer"
LOGS="$HOME/.local/state/omp-ninfer"
CHECKPOINTS="$ROOT/checkpoints-v018"
install -d -m 700 "$ROOT" "$STATE" "$LOGS" "$CHECKPOINTS"

MODEL_URL=$(python3 -c \
  'import json; print(json.load(open("releases/v0.18.0/manifest.json"))["components"]["model"]["artifact_url"])')
MODEL_BYTES=$(python3 -c \
  'import json; print(json.load(open("releases/v0.18.0/manifest.json"))["components"]["model"]["artifact_bytes"])')
MODEL_SHA256=$(python3 -c \
  'import json; print(json.load(open("releases/v0.18.0/manifest.json"))["components"]["model"]["artifact_sha256"])')
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

Release `v0.18.0` uses the separate host directory `checkpoints-v018`, still mounted at the profile's
`/checkpoints-v013` container path. Keep `v0.17.0`'s `checkpoints-v017`, `v0.16.2`'s
`checkpoints-v013` and older `checkpoints` stores untouched for rollback; never mount them
read-write into `v0.18.0` or import their
generations. Retained profile/mount names do not establish cross-binary checkpoint compatibility.
Resume earlier sessions by replaying the authoritative client transcript for a fresh prefill.
New exact-runtime checkpoints accelerate later continuations. The retained serving contract includes
JSON-schema structured output and 128-character Chat/Responses tool names. Current v0.18.0 lane
receipts qualify the selected bytes; fresh documented-route acceptance is recorded above.
See the [v0.18.0 compatibility matrix](../releases/v0.18.0/COMPATIBILITY.md).

## 4. Start NInfer on the inference host

For an upgrade from v0.17.0, stop the incumbent with its matching published v0.17.0
stop script before using this release's launcher. Keeping a v0.17.0 container running
does not activate `v0.7.0-qwen38-5090-beta.7`. Follow the immutable guide for the incumbent, preserve its
stores, and replay prior transcripts rather than importing them.

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
(
set -euo pipefail
install -d -m 700 "$HOME/.omp/agent"
umask 077
KEY_TMP=$(mktemp "$HOME/.omp/agent/.ninfer-beta.key.XXXXXX")
trap 'rm -f "$KEY_TMP"' EXIT
ssh USER@RUNTIME_HOST 'sh -lc "cat ~/.config/omp-ninfer/api-key" 2>/dev/null || wsl.exe -d Ubuntu-24.04 -- sh -lc "cat ~/.config/omp-ninfer/api-key"' \
  | tr -d '\r' > "$KEY_TMP"
test "$(wc -c < "$KEY_TMP")" -gt 32
chmod 600 "$KEY_TMP"
mv -f "$KEY_TMP" "$HOME/.omp/agent/ninfer-beta.key"
)
```

The SSH transfer and key-length check must succeed before the same-directory atomic rename replaces
an existing key. A failed transfer leaves the previous key intact and removes the temporary file.
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
and does not qualify a cross-release fleet or concurrent native serving in v0.18.0.

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
container profile and the bound `qwen38-4090-native-v0.8.0-beta.3` /
`qwen38-3090-native-v0.8.0-beta.3` native profiles start with
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
