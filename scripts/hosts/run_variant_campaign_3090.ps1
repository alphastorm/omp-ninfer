[CmdletBinding()]
param([switch]$Preflight)

# RTX 3090 lane runner for scripts/run_variant_campaign.py on the native Windows host.
# The lane's NInfer service is owner-managed and normally stopped; the campaign takes the GPU
# owner lease, runs one fresh ninfer-serve.exe process per arm from the frozen experiment
# binary, and releases the lease in `finally`. No arm on this lane needs the role corpus.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$lane = 'rtx3090'
$stateRoot = 'C:\ProgramData\NInfer\qwen38-3090-omp-v0.2'
$ownerController = Join-Path $stateRoot 'gpu-owner\Control-GpuOwner.ps1'
$ownerState = Join-Path $stateRoot 'gpu-owner-state'
$taskName = 'NInfer-Qwen38-3090-OMP-v0.2'
$root = Join-Path $env:USERPROFILE 'variant-3090'
$binary = Join-Path (Join-Path $env:USERPROFILE 'mtp-ablation-3090-3e37b03e') 'bin\ninfer-serve.exe'
$models = @{
    'groupwise-int' = 'C:\Users\sunil\OMP\qualification\ninfer-3090-v020\qwen3_8_27b.ninfer'
}
$apiKeyFile = Join-Path $stateRoot 'secrets\qwen38-3090-omp-v0.2.2-beta.1-72d34b706f18\api-key.txt'
$runner = Join-Path $root 'run_variant_campaign.py'
$corpusRunner = Join-Path $root 'run_mtp_ablation.py'
$arms = Join-Path $root 'variant-campaign-arms.json'
$campaignIdFile = Join-Path $root 'campaign-id.txt'
$logs = Join-Path $root 'logs'
$traces = Join-Path $root 'traces'
$receipts = Join-Path $root 'receipts'
$modelId = 'q38-ninfer'
$sourceCommit = '3e37b03eac5633fe434afd84c45c54c2078f1556'
$binarySha256 = '13fd2c551e5fd6a0a1377420de72ca0b33620edcfed55ecdaad24c8583fd3a53'
$corpusSha256 = '9bf5957482dc5f86d6cb04d4c82a55c2d0c9ad01f1f3595dc54727e44b896623'
$port = 18082
$deadline = [DateTime]::UtcNow.AddHours(7)

function Assert-File([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "missing file: $Path" }
}

function Get-RemainingSeconds {
    $seconds = [int][Math]::Floor(($deadline - [DateTime]::UtcNow).TotalSeconds)
    if ($seconds -lt 1) { throw 'campaign deadline expired' }
    return $seconds
}

function Invoke-BoundedProcess(
    [string]$FilePath,
    [string[]]$ArgumentList,
    [string]$StdoutPath,
    [string]$StderrPath
) {
    if (@($ArgumentList | Where-Object { $_ -match '[\s"]' }).Count -ne 0) {
        throw 'bounded process arguments must not contain whitespace or quotes'
    }
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = $ArgumentList -join ' '
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    try {
        if (-not $process.Start()) { throw "failed to start bounded process: $FilePath" }
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit((Get-RemainingSeconds) * 1000)) {
            $process.Kill()
            $process.WaitForExit()
            throw "bounded process timed out: $FilePath"
        }
        $process.WaitForExit()
        $stdoutText = $stdoutTask.Result
        $stderrText = $stderrTask.Result
        $exitCode = $process.ExitCode
    }
    finally {
        $process.Dispose()
    }
    [IO.File]::WriteAllText($StdoutPath, $stdoutText)
    [IO.File]::WriteAllText($StderrPath, $stderrText)
    if ($exitCode -ne 0) {
        $tail = (($stderrText -split "`r?`n") | Select-Object -Last 40) -join [Environment]::NewLine
        throw "process failed with exit $($exitCode): $FilePath`n$tail"
    }
}

function Wait-Health([System.Diagnostics.Process]$Process) {
    $limit = [DateTime]::UtcNow.AddMinutes(20)
    while ([DateTime]::UtcNow -lt $limit -and [DateTime]::UtcNow -lt $deadline) {
        if ($Process.HasExited) { throw "experiment server exited with $($Process.ExitCode) before health" }
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$port/health" -TimeoutSec 3
            if ($health.status -eq 'ok') { return }
        }
        catch {}
        Start-Sleep -Seconds 2
    }
    throw 'experiment server did not become healthy within 20 minutes'
}

function Stop-Quietly([System.Diagnostics.Process]$Process) {
    if ($null -eq $Process) { return }
    try {
        if (-not $Process.HasExited) {
            Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
            Wait-Process -Id $Process.Id -Timeout 30 -ErrorAction SilentlyContinue
        }
    } catch {}
}

function Get-Contract {
    $json = @(& python $runner contract --arms $arms --lane $lane 2>&1)
    if ($LASTEXITCODE -ne 0) { throw "runner contract failed: $($json -join ' ')" }
    return (($json -join [Environment]::NewLine) | ConvertFrom-Json)
}

function Start-VramSampler([string]$Label) {
    $script = Join-Path $root 'vram-sampler.ps1'
    $out = Join-Path $logs "vram-$Label.jsonl"
    return Start-Process -FilePath 'powershell.exe' -ArgumentList @(
        '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', $script, '-Output', $out
    ) -PassThru -WindowStyle Hidden
}

function Invoke-Preflight {
    $probeOut = [IO.Path]::GetTempFileName()
    $probeErr = [IO.Path]::GetTempFileName()
    try {
        Invoke-BoundedProcess $env:ComSpec @('/d', '/c', 'exit', '0') $probeOut $probeErr
    }
    finally {
        Remove-Item -LiteralPath $probeOut, $probeErr -Force -ErrorAction SilentlyContinue
    }
    foreach ($path in @($ownerController, $binary, $apiKeyFile, $runner, $corpusRunner, $arms, $campaignIdFile,
            (Join-Path $root 'vram-sampler.ps1'))) { Assert-File $path }
    $contract = Get-Contract
    if ($contract.corpus_sha256 -ne $corpusSha256 -or [int]$contract.request_count -ne 24) {
        throw 'runner corpus contract mismatch'
    }
    if ($contract.source_commit -ne $sourceCommit -or $contract.binary_sha256 -ne $binarySha256) {
        throw 'arms manifest lane identity mismatch'
    }
    foreach ($arm in $contract.arms) {
        if (-not $models.ContainsKey([string]$arm.weights_id)) { throw "no staged artifact for $($arm.weights_id)" }
        if ($arm.quality_gate -ne 'byte-equivalent') { throw "lane $lane has no role-corpus runner for $($arm.label)" }
    }
    foreach ($weights in $models.Keys) {
        $expected = $contract.artifacts.$weights
        $path = $models[$weights]
        Assert-File $path
        if ((Get-Item -LiteralPath $path).Length -ne [int64]$expected.bytes) { throw "artifact byte length changed: $path" }
    }
    $campaignId = (Get-Content -LiteralPath $campaignIdFile -Raw).Trim()
    if ($campaignId -notmatch '^[0-9a-f]{64}$') { throw 'campaign id must be a lowercase SHA-256' }
    $actualBinary = (Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualBinary -ne $binarySha256) { throw 'experiment binary SHA-256 changed' }
    $version = @(& $binary --version 2>&1) -join ' '
    if ($LASTEXITCODE -ne 0 -or $version -notmatch "patch_stack_sha=$sourceCommit" -or
        $version -notmatch 'source_dirty=false') { throw 'binary build identity mismatch' }
    if (Get-CimInstance Win32_Process -Filter "Name='ninfer-serve.exe'") {
        throw 'RTX3090 service is not in its stopped owner state'
    }
    $task = Get-ScheduledTask -TaskName $taskName
    if ([string]$task.State -ne 'Ready') { throw 'RTX3090 scheduled task is not stopped' }
    $ownerJson = @(& $ownerController -Action status -StateRoot $ownerState)
    $owner = (($ownerJson -join [Environment]::NewLine) | ConvertFrom-Json)
    if ([bool]$owner.paused -or [int]$owner.power_limit_w -ne 370) {
        throw 'RTX3090 owner power state changed'
    }
    if ([int]$owner.interactive_gpu_workload_count -ne 0) {
        throw 'RTX3090 currently has an interactive GPU workload'
    }
    return [ordered]@{
        status = 'passed'
        lane = $lane
        campaign_id = $campaignId
        incumbent_process = 'stopped'
        owner_power_limit_w = [int]$owner.power_limit_w
        binary_sha256 = $actualBinary
        source_commit = $sourceCommit
        corpus_sha256 = $contract.corpus_sha256
        arms = @($contract.arms | ForEach-Object { $_.label })
        request_count_per_arm = [int]$contract.request_count
        max_live_seconds = 25200
        restore = 'no NInfer process, scheduled task Ready, GPU-owner lease released, 370 W owner limit'
    }
}

$preflightResult = Invoke-Preflight
if ($Preflight) {
    $preflightResult | ConvertTo-Json -Compress
    exit 0
}

$campaignId = $preflightResult.campaign_id
$contract = Get-Contract
New-Item -ItemType Directory -Force -Path $logs, $traces, $receipts | Out-Null
$ownerHeld = $false
$experiment = $null
$sampler = $null
try {
    & $ownerController -Action stop -StateRoot $ownerState | Out-Null
    $ownerHeld = $true
    foreach ($arm in $contract.arms) {
        if ([DateTime]::UtcNow -ge $deadline) { throw 'campaign deadline expired before next arm' }
        $label = [string]$arm.label
        $receipt = Join-Path $receipts "arm-$label.json"
        if (Test-Path -LiteralPath $receipt -PathType Leaf) { continue }
        $serverLog = Join-Path $logs "requests-$label.jsonl"
        $trace = Join-Path $traces "run-$label.json"
        $memorySamples = Join-Path $logs "vram-$label.jsonl"
        $stdout = Join-Path $logs "server-$label.stdout.log"
        $stderr = Join-Path $logs "server-$label.stderr.log"
        $model = $models[[string]$arm.weights_id]
        $serverArgs = @(
            $model,
            '--host', '127.0.0.1', '--port', [string]$port,
            '--api-key-file', $apiKeyFile,
            '--model-id', $modelId,
            '--binary-sha256', $binarySha256,
            '--artifact-sha256', [string]$contract.artifacts.($arm.weights_id).sha256,
            '--deployment-profile', "variant-campaign-rtx3090-$label",
            '--device', '0', '--max-context', [string]$arm.max_context, '--kv-capacity', 'auto',
            '--prefill-chunk', [string]$arm.prefill_chunk, '--kv-dtype', [string]$arm.kv_dtype,
            '--max-concurrency', '1', '--max-pending-requests', '16',
            '--pending-timeout-ms', '30000', '--reasoning-effort', 'xhigh',
            '--response-store-max-records', '1024', '--response-store-max-mib', '256',
            '--request-log-jsonl', $serverLog, '--log-stats-interval-ms', '0',
            '--preserve-thinking', '--greedy'
        )
        if ($arm.speculative_backend -eq 'mtp') {
            $serverArgs += @('--spec', 'mtp', '--draft-tokens', [string]$arm.speculative_draft_window, '--lm-head-draft')
        }
        if (-not (Test-Path -LiteralPath $trace -PathType Leaf)) {
            $initOut = @(& python $runner init --arms $arms --lane $lane --arm $label --model $modelId --campaign-id $campaignId --output $trace 2>&1)
            if ($LASTEXITCODE -ne 0) { throw "runner init failed: $($initOut -join ' ')" }
        }
        $failureCode = $null
        $failureEvidence = $null
        try {
            $experiment = Start-Process -FilePath $binary -ArgumentList $serverArgs -PassThru -NoNewWindow `
                -RedirectStandardOutput $stdout -RedirectStandardError $stderr
            try { $sampler = Start-VramSampler $label } catch { $sampler = $null }
            try {
                Wait-Health $experiment
            }
            catch {
                $failureCode = 'server_start'
                $failureEvidence = $stderr
                Stop-Quietly $experiment
                if (-not (Test-Path -LiteralPath $stderr) -or (Get-Item -LiteralPath $stderr).Length -eq 0) {
                    [IO.File]::WriteAllText($stderr, $_.Exception.Message)
                }
            }
            if ($null -eq $failureCode) {
                $runArgs = @(
                    $runner, 'run', '--arms', $arms, '--lane', $lane, '--arm', $label,
                    '--base-url', "http://127.0.0.1:$port",
                    '--api-key-file', $apiKeyFile, '--model', $modelId,
                    '--campaign-id', $campaignId,
                    '--output', $trace, '--timeout', '1200', '--resume'
                )
                try {
                    Invoke-BoundedProcess 'python' $runArgs `
                        (Join-Path $logs "runner-$label.stdout.log") `
                        (Join-Path $logs "runner-$label.stderr.log")
                }
                catch {
                    $failureCode = 'runner_error'
                    $failureEvidence = Join-Path $logs "runner-$label.stderr.log"
                    if (-not (Test-Path -LiteralPath $failureEvidence) -or (Get-Item -LiteralPath $failureEvidence).Length -eq 0) {
                        [IO.File]::WriteAllText($failureEvidence, $_.Exception.Message)
                    }
                }
            }
        }
        finally {
            Stop-Quietly $sampler
            $sampler = $null
            Stop-Quietly $experiment
            $experiment = $null
        }
        $summaryArgs = @(
            $runner, 'summarize', '--arms', $arms, '--lane', $lane,
            '--trace', $trace, '--server-log', $serverLog, '--output', $receipt
        )
        if (Test-Path -LiteralPath $memorySamples -PathType Leaf) { $summaryArgs += @('--memory-samples', $memorySamples) }
        if ($null -ne $failureCode) {
            $failedStep = (@(& python $runner next-step --trace $trace 2>&1) -join '').Trim()
            if ($LASTEXITCODE -ne 0) { throw "next-step failed: $failedStep" }
            $summaryArgs += @('--failure-code', $failureCode, '--failed-step-id', $failedStep, '--failure-evidence', $failureEvidence)
        }
        Invoke-BoundedProcess 'python' $summaryArgs `
            (Join-Path $logs "summarize-$label.stdout.log") `
            (Join-Path $logs "summarize-$label.stderr.log")
    }

    $laneReceipt = Join-Path $receipts 'lane.json'
    $combineArgs = @($runner, 'combine', '--arms', $arms, '--lane', $lane)
    foreach ($arm in $contract.arms) {
        $combineArgs += @('--arm-receipt', (Join-Path $receipts "arm-$($arm.label).json"))
    }
    $combineArgs += @('--output', $laneReceipt)
    Invoke-BoundedProcess 'python' $combineArgs `
        (Join-Path $logs 'combine.stdout.log') (Join-Path $logs 'combine.stderr.log')
    $decision = Get-Content -LiteralPath $laneReceipt -Raw | ConvertFrom-Json
    [ordered]@{
        status = 'passed'
        lane = $lane
        campaign_id = $campaignId
        selected_arm = $decision.decision.selected_arm
        action = $decision.decision.action
        receipt = $laneReceipt
    } | ConvertTo-Json -Compress
}
finally {
    Stop-Quietly $sampler
    Stop-Quietly $experiment
    if ($ownerHeld) {
        & $ownerController -Action start -StateRoot $ownerState | Out-Null
    }
    $ownerJson = @(& $ownerController -Action status -StateRoot $ownerState)
    $owner = (($ownerJson -join [Environment]::NewLine) | ConvertFrom-Json)
    $task = Get-ScheduledTask -TaskName $taskName
    if ([bool]$owner.paused -or [int]$owner.power_limit_w -ne 370 -or
        [string]$task.State -ne 'Ready' -or
        (Get-CimInstance Win32_Process -Filter "Name='ninfer-serve.exe'")) {
        throw 'RTX3090 owner-state restoration failed'
    }
}
