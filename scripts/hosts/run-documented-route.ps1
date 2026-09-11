<#
.SYNOPSIS
Execute a documented route's PowerShell blocks exactly as the quickstart prints them.

.DESCRIPTION
Launch without -ExecutionPolicy Bypass, as text, so the host's real policy is what the route
meets: powershell -NoProfile -Command "& ([scriptblock]::Create((Get-Content -Raw run-documented-route.ps1))) -Bundle ... -WorkDir ... -Receipt ..."
Runs every step file of a bundle written by scripts/documented_route.py, in reading order, in
this one PowerShell session - so variables one block defines ($VariantId, $StateRoot, $Provider,
NINFER_NATIVE_API_KEY ...) are visible to the next, as they are for a reader pasting block after
block into one elevated window. Each step's bytes are hashed before execution and compared with
the bundle manifest; a step that fails ends the run, and the receipt records every step's
outcome either way. The receipt is content-safe by construction: it carries hashes, timings,
exit states and error messages, never output.

.PARAMETER Bundle
Directory holding manifest.json and the NN-<slug>.ps1 step files.

.PARAMETER WorkDir
The directory a reader starts in. A route whose first block clones the tag changes into the
clone itself; the runner records the commit it ends up in.

.PARAMETER Receipt
Where to write the JSON receipt.

.PARAMETER CloneOverride
A commit to clone in place of the tag the route's clone-and-verify block names. Used only for
the qualification run that precedes a cut - the tag is created from the commit this run
accepts, so it cannot exist yet. The substituted step is recorded as such, verifies the
candidate as installable rather than ready, and every other block runs verbatim.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Bundle,
    [Parameter(Mandatory = $true)][string]$WorkDir,
    [Parameter(Mandatory = $true)][string]$Receipt,
    [string]$CloneOverride = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$manifest = Get-Content -LiteralPath (Join-Path $Bundle 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$result = [ordered]@{
    artifact_type    = 'omp_ninfer_documented_route_run'
    schema_version   = 1
    lane             = [string]$manifest.lane
    document         = [string]$manifest.document
    document_sha256  = [string]$manifest.document_sha256
    started_utc      = [DateTime]::UtcNow.ToString('o')
    host_os          = [string](Get-CimInstance Win32_OperatingSystem).Caption
    powershell       = $PSVersionTable.PSVersion.ToString()
    elevated         = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    clone_commit     = ''
    steps            = @()
    status           = 'running'
}
Set-Location -LiteralPath $WorkDir

function Write-Receipt {
    $result.completed_utc = [DateTime]::UtcNow.ToString('o')
    $json = $result | ConvertTo-Json -Depth 8
    [IO.File]::WriteAllText($Receipt, $json + "`n", [Text.UTF8Encoding]::new($false))
}

$failed = $false
foreach ($step in $manifest.steps) {
    $path = Join-Path $Bundle ([string]$step.file)
    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    $record = [ordered]@{
        position = [int]$step.position; slug = [string]$step.slug; heading = [string]$step.heading
        index = [int]$step.index; block_sha256 = [string]$step.sha256; executed_sha256 = $actual
        started_utc = [DateTime]::UtcNow.ToString('o'); status = 'skipped'; elapsed_seconds = 0.0
        error = $null; substitution = $null
    }
    if ($failed) {
        $result.steps += $record
        continue
    }
    if ($actual -cne [string]$step.sha256) {
        $record.status = 'refused'
        $record.error = 'step file bytes do not match the documented block'
        $result.steps += $record
        $failed = $true
        continue
    }
    $stopwatch = [Diagnostics.Stopwatch]::StartNew()
    try {
        Write-Host ("== step {0}: {1} ({2} [{3}])" -f $step.position, $step.slug, $step.heading, $step.index)
        if ($CloneOverride -and [string]$step.slug -eq 'clone-and-verify') {
            $record.substitution = "cloned commit $CloneOverride in place of the tag this run's acceptance creates; verified as installable, not ready"
            & git clone -q https://github.com/alphastorm/omp-ninfer.git omp-ninfer 2>$null
            & git -C omp-ninfer checkout -q $CloneOverride 2>$null
            Set-Location -LiteralPath omp-ninfer
            Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
            $named = [regex]::Match([IO.File]::ReadAllText($path), '--branch (v[0-9][0-9.]*)').Groups[1].Value
            & py -3 scripts\verify_release.py --release $named --require-installable
            if ($LASTEXITCODE -ne 0) { throw "candidate $named is not installable (exit $LASTEXITCODE)" }
            $record.status = 'substituted'
            continue
        }
        # Run the block as pasted text in this scope: its variables persist into the next block, and
        # the machine's execution policy applies exactly where it applies for a reader - to the
        # .ps1 files the block itself invokes, never to the pasted commands.
        Invoke-Expression ([IO.File]::ReadAllText($path, [Text.UTF8Encoding]::new($false)))
        # A block that ends on a native command with a non-zero exit is a failed step too.
        if ((Test-Path variable:LASTEXITCODE) -and $LASTEXITCODE -ne 0) {
            throw "block ended with native exit code $LASTEXITCODE"
        }
        $record.status = 'passed'
    } catch {
        $record.status = 'failed'
        $record.error = ($_ | Out-String).Trim()
        $failed = $true
    } finally {
        $stopwatch.Stop()
        $record.elapsed_seconds = [Math]::Round($stopwatch.Elapsed.TotalSeconds, 3)
        $result.steps += $record
        Write-Receipt
    }
}
$result.status = if ($failed) { 'failed' } else { 'passed' }
if (Test-Path -LiteralPath '.git') { $result.clone_commit = (& git rev-parse HEAD 2>$null | Out-String).Trim() }
Write-Receipt
Write-Host ("route {0}: {1}" -f $result.lane, $result.status)
if ($failed) { exit 1 }
