[CmdletBinding()]
param([switch]$Preflight)

# RTX 4090 lane runner for scripts/run_variant_campaign.py on the native Windows host.
# Every arm is one fresh ninfer-serve.exe process from the shipped v0.2 release binary; the
# incumbent Control-Release.ps1 service is stopped for the campaign and restored in `finally`.
# Arms whose quality gate is `role-corpus` (plus the incumbent reference) run the private role
# corpus against the live process before it is stopped.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$lane = 'rtx4090'
$stateRoot = 'C:\ProgramData\NInfer\qwen38-4090'
$controller = Join-Path $stateRoot 'Control-Release.ps1'
$releaseRoot = Join-Path $stateRoot 'releases\qwen38-4090-v0.2-32aa589982c4'
$binary = Join-Path $releaseRoot 'bin\ninfer-serve.exe'
$models = @{
    'groupwise-int' = 'C:\Users\sunil\local-4090-data\sf-long-persistent\models\qwen3_8_27b.ninfer'
}
$apiKeyFile = Join-Path $stateRoot 'secrets\qwen38-4090-v0.2-32aa589982c4\api-key.txt'
$root = Join-Path $env:USERPROFILE 'variant-4090'
$runner = Join-Path $root 'run_variant_campaign.py'
$corpusRunner = Join-Path $root 'run_mtp_ablation.py'
$arms = Join-Path $root 'variant-campaign-arms.json'
$campaignIdFile = Join-Path $root 'campaign-id.txt'
$qualification = Join-Path $root 'qualification'
$logs = Join-Path $root 'logs'
$traces = Join-Path $root 'traces'
$receipts = Join-Path $root 'receipts'
$quality = Join-Path $root 'quality'
$modelId = 'qwen3.8-27b'
$sourceCommit = '32aa589982c49d540a68a831d2c89aa83247f5c7'
$binarySha256 = 'a5b501ecdcf00031945bddac0732ba302aa2250d529076a41f592e7038aff4a2'
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
    [string]$StderrPath,
    [hashtable]$Environment = @{}
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
    foreach ($key in $Environment.Keys) { $startInfo.Environment[$key] = [string]$Environment[$key] }
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
    foreach ($path in @($controller, $binary, $apiKeyFile, $runner, $corpusRunner, $arms, $campaignIdFile,
            (Join-Path $root 'vram-sampler.ps1'),
            (Join-Path $qualification 'scripts\run_qualification.py'),
            (Join-Path $qualification 'scripts\score_qualification.py'))) { Assert-File $path }
    $contract = Get-Contract
    if ($contract.corpus_sha256 -ne $corpusSha256 -or [int]$contract.request_count -ne 24) {
        throw 'runner corpus contract mismatch'
    }
    if ($contract.source_commit -ne $sourceCommit -or $contract.binary_sha256 -ne $binarySha256) {
        throw 'arms manifest lane identity mismatch'
    }
    foreach ($arm in $contract.arms) {
        if (-not $models.ContainsKey([string]$arm.weights_id)) { throw "no staged artifact for $($arm.weights_id)" }
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
    if ($actualBinary -ne $binarySha256) { throw 'incumbent binary SHA-256 changed' }
    $version = @(& $binary --version 2>&1) -join ' '
    if ($LASTEXITCODE -ne 0 -or $version -notmatch "patch_stack_sha=$sourceCommit" -or
        $version -notmatch 'source_dirty=false') { throw 'binary build identity mismatch' }
    $statusJson = @(& $controller -Action Status -StateRoot $stateRoot)
    $status = (($statusJson -join [Environment]::NewLine) | ConvertFrom-Json)
    if ($status.process_state -ne 'running' -or $status.endpoint_state -ne 'ready') {
        throw 'incumbent RTX4090 service is not healthy'
    }
    return [ordered]@{
        status = 'passed'
        lane = $lane
        campaign_id = $campaignId
        incumbent_release = $status.release_id
        binary_sha256 = $actualBinary
        source_commit = $sourceCommit
        corpus_sha256 = $contract.corpus_sha256
        arms = @($contract.arms | ForEach-Object { $_.label })
        quality_arms = @($contract.arms | Where-Object { $_.quality_gate -eq 'role-corpus' -and $_.role -eq 'candidate' } | ForEach-Object { $_.label })
        request_count_per_arm = [int]$contract.request_count
        max_live_seconds = 25200
        restore = 'Control-Release.ps1 Start for the unchanged active release'
    }
}

$preflightResult = Invoke-Preflight
if ($Preflight) {
    $preflightResult | ConvertTo-Json -Compress
    exit 0
}

$campaignId = $preflightResult.campaign_id
$contract = Get-Contract
New-Item -ItemType Directory -Force -Path $logs, $traces, $receipts, $quality | Out-Null
$serviceStopped = $false
$experiment = $null
$sampler = $null
try {
    & $controller -Action Stop -StateRoot $stateRoot | Out-Null
    $serviceStopped = $true
    if (Get-CimInstance Win32_Process -Filter "Name='ninfer-serve.exe'") {
        throw 'incumbent server remained after controller stop'
    }

    foreach ($arm in $contract.arms) {
        if ([DateTime]::UtcNow -ge $deadline) { throw 'campaign deadline expired before next arm' }
        $label = [string]$arm.label
        $receipt = Join-Path $receipts "arm-$label.json"
        if (Test-Path -LiteralPath $receipt -PathType Leaf) { continue }
        $needsQuality = ($arm.quality_gate -eq 'role-corpus' -and $arm.role -eq 'candidate') -or ($label -eq [string]$contract.incumbent)
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
            '--deployment-profile', "variant-campaign-rtx4090-$label",
            '--device', '0', '--max-context', [string]$arm.max_context, '--kv-capacity', [string]$arm.max_context,
            '--prefill-chunk', [string]$arm.prefill_chunk, '--kv-dtype', [string]$arm.kv_dtype,
            '--max-concurrency', '1', '--max-pending-requests', '16',
            '--pending-timeout-ms', '30000', '--reasoning-effort', 'xhigh',
            '--response-store-max-records', '1024', '--response-store-max-mib', '256',
            '--request-log-jsonl', $serverLog, '--log-stats-interval-ms', '0',
            '--no-ui', '--preserve-thinking', '--greedy'
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
            if ($null -eq $failureCode -and $needsQuality -and -not (Test-Path -LiteralPath (Join-Path $quality "$label\scores.json"))) {
                $qualityOut = Join-Path $quality $label
                if (Test-Path -LiteralPath $qualityOut) { Remove-Item -LiteralPath $qualityOut -Recurse -Force }
                $apiKey = (Get-Content -LiteralPath $apiKeyFile -Raw).Trim()
                $qualityArgs = @(
                    (Join-Path $qualification 'scripts\run_qualification.py'),
                    '--model', $modelId, '--base-url', "http://127.0.0.1:$port/v1",
                    '--cases', (Join-Path $qualification 'cases'),
                    '--fixtures', (Join-Path $qualification 'fixtures'),
                    '--out', $qualityOut, '--concurrency', '1',
                    '--reasoning-mode', 'low', '--reasoning-wire', 'top-level',
                    '--reasoning-token-headroom', '8192', '--timeout', '900', '--no-ssh',
                    '--label', "$lane/$label/$campaignId"
                )
                Invoke-BoundedProcess 'python' $qualityArgs `
                    (Join-Path $logs "quality-$label.stdout.log") `
                    (Join-Path $logs "quality-$label.stderr.log") `
                    @{ LOCAL_5090_API_KEY = $apiKey }
                Invoke-BoundedProcess 'python' @(
                    (Join-Path $qualification 'scripts\score_qualification.py'),
                    '--run', $qualityOut, '--cases', (Join-Path $qualification 'cases')
                ) (Join-Path $logs "score-$label.stdout.log") (Join-Path $logs "score-$label.stderr.log")
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

    $incumbentLabel = [string]$contract.incumbent
    $qualityReceipts = @()
    foreach ($arm in $contract.arms) {
        $label = [string]$arm.label
        if (-not ($arm.quality_gate -eq 'role-corpus' -and $arm.role -eq 'candidate')) { continue }
        $candidateRun = Join-Path $quality $label
        $referenceRun = Join-Path $quality $incumbentLabel
        if (-not (Test-Path -LiteralPath (Join-Path $candidateRun 'scores.json')) -or
            -not (Test-Path -LiteralPath (Join-Path $referenceRun 'scores.json'))) { continue }
        $qualityReceipt = Join-Path $receipts "quality-$label.json"
        Invoke-BoundedProcess 'python' @(
            $runner, 'quality', '--arms', $arms, '--lane', $lane,
            '--arm-receipt', (Join-Path $receipts "arm-$label.json"),
            '--reference-receipt', (Join-Path $receipts "arm-$incumbentLabel.json"),
            '--candidate-run', $candidateRun, '--reference-run', $referenceRun,
            '--output', $qualityReceipt
        ) (Join-Path $logs "qualityreceipt-$label.stdout.log") (Join-Path $logs "qualityreceipt-$label.stderr.log")
        $qualityReceipts += "$label=$qualityReceipt"
    }

    $laneReceipt = Join-Path $receipts 'lane.json'
    $combineArgs = @($runner, 'combine', '--arms', $arms, '--lane', $lane)
    foreach ($arm in $contract.arms) {
        $combineArgs += @('--arm-receipt', (Join-Path $receipts "arm-$($arm.label).json"))
    }
    foreach ($item in $qualityReceipts) { $combineArgs += @('--quality-receipt', $item) }
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
        quality_receipts = $qualityReceipts
        receipt = $laneReceipt
    } | ConvertTo-Json -Compress
}
finally {
    Stop-Quietly $sampler
    Stop-Quietly $experiment
    if ($serviceStopped) {
        # `Start` launches the scheduled task and waits for readiness; `Run` is the task's own
        # foreground action and would block here forever with the server as a child process.
        & $controller -Action Start -StateRoot $stateRoot | Out-Null
        $restoredJson = @(& $controller -Action Status -StateRoot $stateRoot)
        $restored = (($restoredJson -join [Environment]::NewLine) | ConvertFrom-Json)
        if ($restored.process_state -ne 'running' -or $restored.endpoint_state -ne 'ready') {
            throw 'RTX4090 incumbent service restoration failed'
        }
    }
}
