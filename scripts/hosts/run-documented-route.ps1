#Requires -Version 5.1
<#
.SYNOPSIS
Execute a documented route's PowerShell blocks exactly as the quickstart prints them.

.DESCRIPTION
Runs every step file of a bundle written by scripts/documented_route.py, in reading order, in
this one PowerShell session - so variables one block defines ($VariantId, $StateRoot, $Provider,
NINFER_NATIVE_API_KEY ...) are visible to the next, as they are for a reader pasting block after
block into one elevated window. Each step's bytes are hashed before execution and compared with
the bundle manifest; a step that fails ends the run, and the receipt records every step's
outcome either way. The receipt is content-safe by construction: it carries hashes, timings,
exit states and error messages, never output.

.PARAMETER Bundle
Directory holding manifest.json and the NN-<slug>.ps1 step files.

.PARAMETER Clone
The product clone the blocks run from (the quickstart's "tagged product clone").

.PARAMETER Receipt
Where to write the JSON receipt.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Bundle,
    [Parameter(Mandatory = $true)][string]$Clone,
    [Parameter(Mandatory = $true)][string]$Receipt
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
Set-Location -LiteralPath $Clone
$result.clone_commit = (& git rev-parse HEAD 2>$null | Out-String).Trim()

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
        error = $null
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
        # Dot-source so the block's variables persist into the next block, as in a reader's shell.
        . $path
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
Write-Receipt
Write-Host ("route {0}: {1}" -f $result.lane, $result.status)
if ($failed) { exit 1 }
