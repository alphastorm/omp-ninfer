# Quickstart

> **Versioned guide: v0.16.2 · stock Oh My Pi 18.15.0 · Qualified on RTX 5090 · 4090 · 3090**

OMP NInfer is the qualified local inference appliance and release layer connecting the
[Oh My Pi](https://github.com/can1357/oh-my-pi) (OMP) coding-agent client over authenticated
loopback to the NInfer inference engine serving Qwen3.8 27B on your GPU.

## Choose your lane

| GPU and host | Client route in v0.16.2 | Start here |
| --- | --- | --- |
| RTX 5090 container on Windows 11 + Docker Desktop / WSL2 | Native Windows x64 client over local loopback `127.0.0.1:18089` | [RTX 5090 Windows route](#ready-route-native-windows-and-docker-desktop-wsl2) |
| RTX 5090 container on Windows 11 / WSL2 or Linux | macOS arm64 client over a manual SSH tunnel (preview) | [macOS manual SSH route (preview)](#macos-client-over-a-manual-ssh-tunnel-preview) |
| RTX 4090 native Windows 11 (alone or beside RTX 3090) | Native Windows x64 client over local loopback `127.0.0.1:18082`; UUID-bound; `v0.8.0-qwen38-4090-beta.2` DFlash2 K=7, one request at a time (`C1`); route, native campaign and public install passed | [RTX 4090 native lane](#native-windows-rtx-4090-release-lane) |
| RTX 3090 native Windows 11 (alone or beside RTX 4090) | Native Windows x64 client over local loopback `127.0.0.1:18082`; UUID-bound; `v0.8.0-qwen38-3090-beta.2` DFlash2 K=7, two requests in flight (`C2`) over one shared 131,072-token pool; route passed, later native campaign failed and founder-waived; no anonymous public-install result | [RTX 3090 native lane](#native-windows-rtx-3090-release-lane) |
| RTX 5090 container with Linux x64 client under WSL2 only | WSL2 shell client over local loopback `127.0.0.1:18089` (no native Linux OS qualification) | [WSL2 Linux client](#wsl2-linux-client-over-local-loopback) |
| Other GPU, non-WSL Linux client, or concurrent native serving | Unsupported | [Compatibility boundary](COMPATIBILITY.md) |

## Before you start

- **Clone the tag and run the ready gate:** start from a clean clone of `v0.16.2` and verify
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
  Native RTX 4090 retains its `32768 MiB` host floor and shared Host budget `15747.734375 MiB`
  (16,512,696,320 bytes); RTX 3090 uses a shared Host budget of `20867.734375 MiB` (21,881,405,440 bytes).
  These replace separate host-slot/KV budgets; no smaller-host qualification is claimed.

## Contributor acceptance and preflight

You can exercise the stock client without a GPU: run
`python3 scripts/client_acceptance.py --omp ./omp-darwin-arm64 --omp-sha256 SHA256 --omp-version omp/18.15.0 --local-rehearsal --receipt rehearsal.json`,
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

## OMP 18.15.0 client

Release `v0.16.2` selects unmodified upstream
[Oh My Pi v18.15.0](https://github.com/can1357/oh-my-pi/releases/tag/v18.15.0), source
`3fedf8d53267e32a6d7521ce725fdcc4a36fdc67`, tree
`48bc72ba2418c0b78163d9769e91a0d8683e642b`, release `430630500`.
The [release notes](../releases/v0.16.2/NINFER_RELEASE_NOTES.md#stock-omp-18150) record Windows
`978846a8…`, Linux `6737ee24…` and Darwin `d36dfabf…`; the release-local
`qualification/client-components.json` descriptor binds those exact identities. The
[18.14.2 review](measurements/2026-11-01-omp-18142-client-upgrade-review.json) and
[18.15.0 review](measurements/2026-11-01-omp-18150-client-upgrade-review.json) cover the whole
source delta plus independent download integrity; they are not semantic or live acceptance.

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
  or per-call-model opt-in is introduced.
- **Keep exact-loop detection on:** short whole-line/newline-spanning cycles retain four repeats
  but now need 1024 repeated characters; short non-newline cycles remain four/180 and long cycles
  three/1024. A truly induced loop must still fail closed. Uninduced boundaries are not passes.
- **Keep default compaction:** reserve 19660 and strict >111412 trigger remain. The ordinary
  summary output cap is 15728, not the route's 32768. Length-stopped main, turn-prefix, handoff
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

## Acceptance evidence

Fresh **2026-11-04** acceptance on frozen candidate
`c6fc8465611a89fd85730f0653f670d2a314a721` passed all five documented routes:
RTX 5090 host **2/2**, macOS **10/10**, Windows **5/5**, RTX 4090 **7/7** and RTX 3090 **7/7**
(**31/31 executable blocks**), plus all three stock 18.15.0 clients and RTX 4090
public-install/probe/restoration acceptance. Receipts:
[documented routes](../releases/v0.16.2/acceptance/documented-routes.json),
[composed acceptance](../releases/v0.16.2/acceptance/composed-external-installation.json),
[restoration](measurements/2026-11-04-v0162-acceptance-restoration.json).
The RTX 5090 production hold was **418.529 s** accepted and all-attempt total (one window);
the same healthy production container, image, checkpoint mount and `unless-stopped` policy
were restored.

RTX 3090's later native campaign **failed** at the separate structured-outage managed Stop:
`graceful_incomplete_shutdown`, saved **1**, skipped **8**, refused **1**, final durable-save
reason **capacity**, reclaimed Host bytes **0**. The
[founder waiver](../releases/v0.16.2/qualification/rtx3090-route-waiver.json) preserves that failure.
It is a residual of fork #78 also present in published beta.1; v0.16.0 avoided it only by timing.
Behavior completion, a passing wrapper restoration audit and anonymous public-install acceptance
are **not claimed**. Fleet/fanout, both parallel-proof scenarios at limit 2 and two committed
automatic-compaction/control-recall epochs passed before the failure.
After preserving evidence, the operator recovered with `Control-Release.ps1 -Action Start`
then `-Action Stop` with no client sessions: graceful, zero refused, runtime record and owner
lease absent, **370 W**, tasks Ready, no server or port-18082 listener. A refused session
loses warm restore, not its authoritative OMP transcript; replay it for fresh prefill.
Follow-ups: [export residual #89](https://github.com/alphastorm/ninfer/issues/89) and
[owner restoration #90](https://github.com/alphastorm/ninfer/issues/90).

The exact-source runtime full council and focused product reviews closed by disposition;
their [ledger](../releases/v0.16.2/review/runtime-ledger.json) binds subjects and separate
composition controls. Product deferrals use [#138](https://github.com/alphastorm/omp-ninfer/issues/138).
Review control GE-R1 binds lane-distinct evidence-archive digests beside lane-agnostic scenario
summary receipts; GE-R4 binds the stock-client source and download-integrity review, not live acceptance.
Both native routes are first-lineage, rollback `not_applicable`, zero directions; the separate predecessor rehearsals are not route rollback.
macOS remains preview; Linux remains WSL2-only; vision remains macOS/Windows against RTX 5090 only.
No predecessor client, runtime, or product-route receipt is relabeled.
Composition binds only non-executable prose changes; every accepted executable block is unchanged.
See [Releases](RELEASES.md).

## Current release at a glance

| Lane | Runtime component and source | Model artifact | Serving profile and limits |
| --- | --- | --- | --- |
| RTX 5090 container (`127.0.0.1:18089`) | `v0.7.0-qwen38-5090-beta.5`, source `a87de361` on upstream `64d10fbf`, server `cc99a460`, image `a0cbb8a5`; current published-image lane receipt bound | `81f924d4` (20,437,521,664 bytes) | Kept `qwen38-5090-v0.13.0` (config `751d22dc`): strict origin auth, DFlash2 K7, BF16 KV, 146,368 automatic tokens, 131,072 context, C2 plus two extra device-state slots, shared Host budget, 180 s pending timeout |
| RTX 4090 native Windows (`127.0.0.1:18082`) | `v0.8.0-qwen38-4090-beta.2`, source `a87de361` on upstream `64d10fbf`; package `d9b10b47`, server `ffee91bf`, config `ae27dc44` | Same model v3 | `qwen38-4090-native-v0.8.0-beta.2`: INT8 DFlash2 K7, `Group64` A8 and FP32 head logits off, 131,072 context, C1, 30 s pending timeout, two extra slots, 1,024-token prefill, 16,512,696,320 B shared Host budget, 640 MiB headroom |
| RTX 3090 native Windows (`127.0.0.1:18082`) | `v0.8.0-qwen38-3090-beta.2`, source `a87de361` on upstream `64d10fbf`; package `97a8e634`, server `15a4db46`, config `238ccad7` | Same model v3 | `qwen38-3090-native-v0.8.0-beta.2`: INT8 DFlash2 K7, `Group64` A8 and FP32 head logits off, C2 over one 131,072-token pool, 180 s pending timeout, two extra slots, 1,024-token prefill, 21,881,405,440 B shared Host budget, 768 MiB headroom, 350 W serving cap |

The exact RTX 5090 image is
`ghcr.io/alphastorm/ninfer-runtime@sha256:a0cbb8a5f933ec8aeec9a7defa07d78a835c1093d1d98f5f842267287efa3f71`.
All three runtime components bind `a87de3613c17bced777b446fb545f872d8395ec1`, including the
[managed-Stop capacity fix #78](https://github.com/alphastorm/ninfer/issues/78).
The published component reports a bit-identical same-path double build; the v0.16.0
reproducibility exception is historical, not renewed. See the
[release notes](../releases/v0.16.2/NINFER_RELEASE_NOTES.md) and
[manifest](../releases/v0.16.2/manifest.json) for component evidence,
candidate-bound acceptance, exact-source reviews and exact identities.

Both native 15-phase chains, fit proofs, zero-difference 1,120-prompt powered quality screens
and 3/3 predecessor upgrade/rollback/repair scenarios are bound. The founder's no-regression
rule versus published beta.1 is weighted ≥0.98, every case ≥0.95 and byte-identical normalized
outputs, superseding the earlier 1.08 speedup floor: RTX 3090 weighted **1.0003** /
min **0.9988**, **84/84** identical; RTX 4090 **0.9996** / **0.9989**, **115/115**.
The notes disclose the original failed RTX 5090 `restore_0`, RTX 4090 `restore_1` and RTX 3090
sibling position 1 `base` measurements and exact-subject waivers, and RTX 4090's private
uncapped-power-assertion-only rehearsal fix. Raw failures are not passes; component follow-ups
[#87](https://github.com/alphastorm/ninfer/issues/87) /
[#88](https://github.com/alphastorm/ninfer/issues/88) do not replace product acceptance.

- **Serving limits and compaction:** RTX 5090 admits two requests at once and holds a pending
  request for up to 180 s (`--pending-timeout-ms 180000`) when both prompts plus output reservations
  do not fit its 146,368-token automatic KV pool (upgrade an older one-at-a-time RTX 5090 server before
  raising its OMP limit). RTX 3090 likewise admits two requests, sharing one 131,072-token INT8
  pool with a 180 s pending timeout and OMP limit `2`; this is not a fairness or per-request
  throughput guarantee. RTX 4090
  stays C1 with a 30 s pending timeout and OMP limit `1`; excess turns wait in OMP during
  background compaction rather than expiring at the server
  ([troubleshooting](TROUBLESHOOTING.md#a-turn-fails-with-request_queue_timeout-late-in-a-long-session)).
- **Native two-GPU UUID topology and rollback:** Both native packages bind their GPU UUID and PCI
  address on a two-GPU Windows 11 host and serve sequentially on port `18082`. Upgrading an
  existing install preserves its actual predecessor as `previous_release` for
  `Control-Release.ps1 -Action Rollback`. Separate beta.2 running-upgrade, forced-start-failure
  rollback and repair rehearsals passed on both lanes; candidate-bound public-URL installation
  passed on RTX 4090 but was not exercised on the failed, founder-waived RTX 3090 campaign.
  An isolated scratch qualification's `not_applicable` rollback is not a predecessor-upgrade proof.
- **RTX 3090 power and upgrade:** the serving cap is 350 W, with 370 W owner restoration on the
  qualified hardware. The new installer validates an incumbent's lease under its own policy
  and stops it through its own controller before the successor's policy takes ownership,
  fixing the historical stop-first restriction in
  [#94](https://github.com/alphastorm/omp-ninfer/issues/94). Inspect every refusal; do not bypass it.
- **Checkpoints and legacy routes:** Stock OMP names each session with `prompt_cache_key`, which the
  authenticated runtime hashes into the session identity. Checkpoints restore across graceful
  restarts on all three lanes, but saves are best effort under traffic (a crash or expired wait can
  lose unsaved work; universal warm reuse is not promised) and restore requires the same runtime
  binary, model, profile, and bearer key. Single-GPU native owners staying on `v0.10.0` use the
  [immutable v0.10.0 guide](https://github.com/alphastorm/omp-ninfer/blob/v0.10.0/docs/QUICKSTART.md);
  the older RTX 3090 `v0.2` lineage on the OMP 18.0.9 fork client remains in the
  [historical v0.7.2 guide](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md).
- **Session capability boundary:** Within one API-key principal, prompt_cache_key names a session capability; use unique high-entropy keys and do not share that principal among mutually untrusted clients.
- **Native protocol and checkpoint contract:** Both native lanes require Chat and Responses
  JSON-schema structured output, 128-character tool names, status endpoint schema 2, and request-log
  schema 30. The package server-config (schema 4) uses
  `cache/<release-instance-id>/session-checkpoints-v3` (where `<release-instance-id>` is the
  installed release ID such as `qwen38-4090-native-v0.8.0-beta.2-a87de3613c17`), not the old native
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
git clone --branch v0.16.2 --depth 1 https://github.com/alphastorm/omp-ninfer.git
if ($LASTEXITCODE -ne 0) { throw 'release clone failed' }
Set-Location omp-ninfer
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
py -3 scripts\verify_release.py --require-ready
if ($LASTEXITCODE -ne 0) { throw 'ready gate failed' }
```

### Install the exact native Windows client

```powershell
$ErrorActionPreference = 'Stop'
$Url = 'https://github.com/can1357/oh-my-pi/releases/download/v18.15.0/omp-windows-x64.exe'
$Expected = '978846a816cb77f44a55e32b16493375ca837fbf87e0aec35a9c1c934bff0cd0'
Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile omp-windows-x64.exe
if ((Get-FileHash omp-windows-x64.exe -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Expected) { throw 'OMP binary checksum mismatch' }
$Launcher = "$env:LOCALAPPDATA\OMP\omp.exe"
New-Item -ItemType Directory -Force -Path (Split-Path $Launcher) | Out-Null
Copy-Item .\omp-windows-x64.exe $Launcher -Force
Remove-Item Env:PI_OPENAI_STATEFUL -ErrorAction SilentlyContinue
& $Launcher --version
if ($LASTEXITCODE -ne 0) { throw 'OMP version check failed' }
```

The client version must be `omp/18.15.0` (to roll back, verify the previous pinned binary's
checksum before replacing `omp.exe`). Inside WSL2, run **3. Prepare the model and key** and
**4. Start NInfer** below, skip sections 5–6 (Docker Desktop exposes `127.0.0.1:18089` to native
Windows), then run **Native Windows OMP** in section 7 and **Native Windows command forms** in
section 8.

## Native Windows RTX 4090 release lane

Requires Windows 11 x64, one RTX 4090 (sm_89), a supported NVIDIA driver, Git, PowerShell, Python 3
(`py` launcher), and 40 GiB free disk. The installer binds the unique RTX 4090 UUID and PCI address
even beside an RTX 3090 (use `-GpuUuid` if multiple RTX 4090 cards exist; never hide a card). Stop
the other native lane on port `18082` first. Published `v0.8.0-qwen38-4090-beta.2` uses DFlash2 K=7, INT8 KV,
and C1, and preserves the actual prior install for rollback. Keep prior native release roots
and staging untouched for historical recovery; never import MTP3 checkpoints into the DFlash2
runtime.

```powershell
git clone --branch v0.16.2 --depth 1 https://github.com/alphastorm/omp-ninfer.git
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
$Manifest = Get-Content .\releases\v0.16.2\manifest.json -Raw | ConvertFrom-Json
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
port `18082` first. Published `v0.8.0-qwen38-3090-beta.2` uses DFlash2 K=7 and C2 sharing one 131,072-token
INT8 KV pool, with OMP provider limit `2` and a 180 s pending timeout. C2 is not simultaneous
native-lane serving. The installer stops a running incumbent with that incumbent's own controller
and power policy, so the historical stop-first workaround ([#94](https://github.com/alphastorm/omp-ninfer/issues/94))
is no longer required. Keep all predecessor roots, staging, and checkpoints for rollback; MTP3
checkpoints do not transfer into DFlash2.

```powershell
git clone --branch v0.16.2 --depth 1 https://github.com/alphastorm/omp-ninfer.git
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
$Manifest = Get-Content .\releases\v0.16.2\manifest.json -Raw | ConvertFrom-Json
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
CLIENT='releases/v0.16.2/qualification/client-components.json'
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
tunnel, without a managed macOS installer or appliance service); fresh v0.16.2 acceptance ran
all 10 executable blocks against the `v0.7.0-qwen38-5090-beta.5` RTX 5090 container lane. Sections 3 and 4 also serve as
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
git clone --branch v0.16.2 --depth 1 \
  https://github.com/alphastorm/omp-ninfer.git &&
cd omp-ninfer &&
python3 scripts/verify_release.py --release v0.16.2 --require-ready
```

## 2. Install the OMP beta on the Mac

Despite the retained heading, this installs the stock Oh My Pi 18.15.0 binary (`omp-darwin-arm64`):

```sh
(
set -euo pipefail
URL='https://github.com/can1357/oh-my-pi/releases/download/v18.15.0/omp-darwin-arm64'
EXPECTED='d36dfabf0ee52d6f08efadb59c46f0349545c6f6975522417adae29646e73e34'
curl --fail --location --output omp-darwin-arm64 "$URL"
test "$(shasum -a 256 omp-darwin-arm64 | cut -d ' ' -f 1)" = "$EXPECTED"
mkdir -p "$HOME/.local/bin"
cp omp-darwin-arm64 "$HOME/.local/bin/omp"
chmod 0755 "$HOME/.local/bin/omp"
unset PI_OPENAI_STATEFUL
"$HOME/.local/bin/omp" --version
)
```

The version must be `omp/18.15.0`; add `$HOME/.local/bin` to `PATH` before continuing.

## 3. Prepare the model and key on the inference host

```sh
ROOT="$HOME/.local/share/omp-ninfer"
STATE="$HOME/.config/omp-ninfer"
LOGS="$HOME/.local/state/omp-ninfer"
CHECKPOINTS="$ROOT/checkpoints-v013"
install -d -m 700 "$ROOT" "$STATE" "$LOGS" "$CHECKPOINTS"

MODEL_URL=$(python3 -c \
  'import json; print(json.load(open("releases/v0.16.2/manifest.json"))["components"]["model"]["artifact_url"])')
MODEL_BYTES=$(python3 -c \
  'import json; print(json.load(open("releases/v0.16.2/manifest.json"))["components"]["model"]["artifact_bytes"])')
MODEL_SHA256=$(python3 -c \
  'import json; print(json.load(open("releases/v0.16.2/manifest.json"))["components"]["model"]["artifact_sha256"])')
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
checkpoints accelerate later continuations. The retained serving contract includes JSON-schema
structured output and 128-character Chat/Responses tool names. Current v0.16.2 lane receipts
bind the runtime protocol, and fresh five-route acceptance passed on the frozen candidate. See the
[v0.16.2 compatibility matrix](../releases/v0.16.2/COMPATIBILITY.md).

## 4. Start NInfer on the inference host

For an upgrade from v0.16.0, stop the incumbent with its matching published v0.16.0 stop script before
using this release's launcher. This is a runtime rebuild, not the held client-only patch:
keeping a v0.16.0 container running does not activate `v0.7.0-qwen38-5090-beta.5`. Follow the immutable guide for
the incumbent, preserve its stores, and replay prior transcripts rather than importing them.

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
and does not qualify a cross-release fleet or concurrent native serving in v0.16.2.

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
container profile and the bound `qwen38-4090-native-v0.8.0-beta.2` /
`qwen38-3090-native-v0.8.0-beta.2` native profiles start with
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
