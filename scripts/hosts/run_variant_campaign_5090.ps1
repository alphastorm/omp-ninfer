[CmdletBinding()]
param([switch]$Preflight)

# RTX 5090 lane runner for scripts/run_variant_campaign.py. Runs on the Windows host of the
# WSL2/Docker appliance. Every arm is one fresh container started from the frozen experiment
# image; the production container is stopped for the campaign and restored in `finally`.
# Arms whose quality gate is `role-corpus`, plus the incumbent reference, run the private
# role corpus inside the live container (campaign-root quality.sh) before the container is
# removed, so the quality screen never needs a second stop/restore cycle.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$lane = 'rtx5090'
$incumbent = 'ninfer-5090-v046p'
$image = 'ninfer-mtp-ablation-5090:ce51ccb6'
$campaignRoot = '/home/sunil/services/variant-5090'
$runner = "$campaignRoot/run_variant_campaign.py"
$corpusRunner = "$campaignRoot/run_mtp_ablation.py"
$arms = "$campaignRoot/variant-campaign-arms.json"
$campaignIdFile = "$campaignRoot/campaign-id.txt"
$qualityScript = "$campaignRoot/quality.sh"
$models = @{
    'groupwise-int' = '/home/sunil/builds/models/qwen3_8_27b.ninfer'
    'nvfp4' = '/home/sunil/builds/models/qwen3_8_27b_nvfp4.ninfer'
}
$apiKeyFile = '/home/sunil/services/ninfer-5090/secrets/api_key'
$modelId = 'q38-ninfer'
$sourceCommit = 'ce51ccb689521cadcff541f4bd4cdea9998b7cd5'
$binarySha256 = '989e2b7155bb6b49a0e012a6f0daee5c7eb82320e167ab2de0700bacdcc24fea'
$corpusSha256 = '9bf5957482dc5f86d6cb04d4c82a55c2d0c9ad01f1f3595dc54727e44b896623'
$deadline = [DateTime]::UtcNow.AddHours(7)

function Invoke-Wsl([string[]]$Arguments) {
    $output = @(& wsl.exe -d Ubuntu-24.04 -e @Arguments 2>&1)
    if ($LASTEXITCODE -ne 0) { throw "WSL command failed: $($output -join ' ')" }
    return $output
}

function Invoke-Docker([string[]]$Arguments) {
    return Invoke-Wsl (@('docker') + $Arguments)
}

function Remove-ContainerQuietly([string]$Name) {
    if ([string]::IsNullOrEmpty($Name)) { return }
    try { Invoke-Docker @('rm', '-f', $Name) | Out-Null } catch {}
}

function Save-ContainerLogs([string]$Name, [string]$Label) {
    try {
        Invoke-Wsl @('bash', '-c', "docker logs $Name > $campaignRoot/logs/server-$Label.stdout.log 2> $campaignRoot/logs/server-$Label.stderr.log") | Out-Null
    } catch {}
}

function Write-WslText([string]$Path, [string]$Text) {
    $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Text))
    Invoke-Wsl @('bash', '-c', "echo $encoded | base64 -d > $Path") | Out-Null
}

function Test-WslFile([string]$Path) {
    try { Invoke-Wsl @('test', '-f', $Path) | Out-Null; return $true } catch { return $false }
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

function Invoke-InContainer([string]$Name, [string[]]$Command, [string]$Label, [string]$Stage) {
    $wslArgs = @('-d', 'Ubuntu-24.04', '-e', 'docker', 'exec', $Name) + $Command
    Invoke-BoundedProcess 'wsl.exe' $wslArgs `
        (Join-Path $env:USERPROFILE "variant-5090-$Stage-$Label.stdout.log") `
        (Join-Path $env:USERPROFILE "variant-5090-$Stage-$Label.stderr.log")
}

function Wait-Health([string]$ExpectedContainer) {
    $limit = [DateTime]::UtcNow.AddMinutes(20)
    while ([DateTime]::UtcNow -lt $limit -and [DateTime]::UtcNow -lt $deadline) {
        $running = ((Invoke-Docker @('inspect', '--format', '{{.State.Running}}', $ExpectedContainer)) -join '').Trim()
        if ($running -ne 'true') { throw "container exited before health: $ExpectedContainer" }
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:18088/health' -TimeoutSec 3
            if ($health.status -eq 'ok') { return }
        }
        catch {}
        Start-Sleep -Seconds 2
    }
    throw "server did not become healthy within 20 minutes: $ExpectedContainer"
}

function Get-Contract {
    $json = Invoke-Wsl @('python3', $runner, 'contract', '--arms', $arms, '--lane', $lane)
    return (($json -join [Environment]::NewLine) | ConvertFrom-Json)
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
    foreach ($path in @($runner, $corpusRunner, $arms, $apiKeyFile, $campaignIdFile, $qualityScript,
            "$campaignRoot/qualification/scripts/run_qualification.py",
            "$campaignRoot/qualification/scripts/score_qualification.py")) {
        if (-not (Test-WslFile $path)) { throw "missing campaign file: $path" }
    }
    $contract = Get-Contract
    if ($contract.corpus_sha256 -ne $corpusSha256 -or [int]$contract.request_count -ne 24) {
        throw 'runner corpus contract mismatch'
    }
    if ($contract.source_commit -ne $sourceCommit -or $contract.binary_sha256 -ne $binarySha256) {
        throw 'arms manifest lane identity mismatch'
    }
    foreach ($weights in $models.Keys) {
        $expected = $contract.artifacts.$weights
        if ($null -eq $expected) { throw "arms manifest has no artifact $weights" }
        $path = $models[$weights]
        if (-not (Test-WslFile "$path.done")) { throw "artifact not verified: $path" }
        $bytes = [int64]((Invoke-Wsl @('stat', '-c', '%s', $path)) -join '').Trim()
        if ($bytes -ne [int64]$expected.bytes) { throw "artifact byte length changed: $path" }
    }
    $campaignId = ((Invoke-Wsl @('cat', $campaignIdFile)) -join '').Trim()
    if ($campaignId -notmatch '^[0-9a-f]{64}$') { throw 'campaign id must be a lowercase SHA-256' }
    $running = ((Invoke-Docker @('inspect', '--format', '{{.State.Running}}', $incumbent)) -join '').Trim()
    if ($running -ne 'true') { throw 'incumbent RTX5090 container is not running' }
    Invoke-Docker @('image', 'inspect', $image) | Out-Null
    $actualBinary = (((Invoke-Docker @('run', '--rm', '--entrypoint', 'sha256sum', $image, '/build/apps/ninfer-serve')) -join ' ') -split '\s+')[0]
    if ($actualBinary -ne $binarySha256) { throw 'experiment binary SHA-256 changed' }
    $identity = @(Invoke-Docker @('run', '--rm', '--entrypoint', 'cat', $image, '/build/generated/ninfer_build_info_config.h')) -join [Environment]::NewLine
    if ($identity -notmatch $sourceCommit -or $identity -notmatch 'NINFER_BUILD_SOURCE_DIRTY 0') {
        throw 'experiment build identity mismatch'
    }
    $health = Invoke-RestMethod -Uri 'http://127.0.0.1:18088/health' -TimeoutSec 5
    if ($health.status -ne 'ok') { throw 'incumbent RTX5090 endpoint is not healthy' }
    return [ordered]@{
        status = 'passed'
        lane = $lane
        campaign_id = $campaignId
        incumbent_container = $incumbent
        binary_sha256 = $actualBinary
        source_commit = $sourceCommit
        corpus_sha256 = $contract.corpus_sha256
        arms = @($contract.arms | ForEach-Object { $_.label })
        quality_arms = @($contract.arms | Where-Object { $_.quality_gate -eq 'role-corpus' -and $_.role -eq 'candidate' } | ForEach-Object { $_.label })
        request_count_per_arm = [int]$contract.request_count
        max_live_seconds = 25200
        restore = 'docker start of the unchanged incumbent container followed by health check'
    }
}

$preflightResult = Invoke-Preflight
if ($Preflight) {
    $preflightResult | ConvertTo-Json -Compress
    exit 0
}

$campaignId = $preflightResult.campaign_id
$contract = Get-Contract
$incumbentStopped = $false
$experimentName = $null
$samplerName = $null
try {
    Invoke-Docker @('stop', '--time', '60', $incumbent) | Out-Null
    $incumbentStopped = $true

    foreach ($arm in $contract.arms) {
        if ([DateTime]::UtcNow -ge $deadline) { throw 'campaign deadline expired before next arm' }
        $label = [string]$arm.label
        $receipt = "$campaignRoot/receipts/arm-$label.json"
        if (Test-WslFile $receipt) { continue }
        $needsQuality = ($arm.quality_gate -eq 'role-corpus' -and $arm.role -eq 'candidate') -or ($label -eq [string]$contract.incumbent)
        $experimentName = "ninfer-variant-5090-$label"
        Remove-ContainerQuietly $experimentName
        $serverLog = "$campaignRoot/logs/requests-$label.jsonl"
        $trace = "$campaignRoot/traces/run-$label.json"
        $memorySamples = "$campaignRoot/logs/vram-$label.jsonl"
        $model = $models[[string]$arm.weights_id]
        $serverArgs = @(
            'run', '--detach', '--name', $experimentName, '--gpus', 'all',
            '--publish', '18088:8080',
            '--volume', "${model}:/models/model.ninfer:ro",
            '--volume', "${campaignRoot}:/campaign",
            '--volume', "${apiKeyFile}:/run/secrets/ninfer_api_key:ro",
            $image, '/build/apps/ninfer-serve', '/models/model.ninfer',
            '--host', '0.0.0.0', '--port', '8080',
            '--api-key-file', '/run/secrets/ninfer_api_key',
            '--model-id', $modelId,
            '--binary-sha256', $binarySha256,
            '--artifact-sha256', [string]$contract.artifacts.($arm.weights_id).sha256,
            '--deployment-profile', "variant-campaign-rtx5090-$label",
            '--device', '0', '--max-context', [string]$arm.max_context, '--kv-capacity', 'auto',
            '--prefill-chunk', [string]$arm.prefill_chunk, '--kv-dtype', [string]$arm.kv_dtype,
            '--max-concurrency', '1',
            '--response-store-max-records', '1024', '--response-store-max-mib', '256',
            '--request-log-jsonl', "/campaign/logs/requests-$label.jsonl",
            '--log-stats-interval-ms', '0', '--vision', '--preserve-thinking', '--greedy'
        )
        if ($arm.speculative_backend -eq 'mtp') {
            $serverArgs += @('--spec', 'mtp', '--draft-tokens', [string]$arm.speculative_draft_window, '--lm-head-draft')
        }
        if (-not (Test-WslFile $trace)) {
            Invoke-Wsl @(
                'python3', $runner, 'init', '--arms', $arms, '--lane', $lane, '--arm', $label,
                '--model', $modelId, '--campaign-id', $campaignId, '--output', $trace
            ) | Out-Null
        }
        $failureCode = $null
        $failureEvidence = $null
        $samplerName = "ninfer-variant-5090-vram-$label"
        Remove-ContainerQuietly $samplerName
        try {
            Invoke-Docker $serverArgs | Out-Null
            try {
                Invoke-Docker @(
                    'run', '--detach', '--name', $samplerName, '--gpus', 'all',
                    '--volume', "${campaignRoot}:/campaign", '--entrypoint', 'bash', $image,
                    '/campaign/vram-sampler.sh', $label
                ) | Out-Null
            } catch {
                $samplerName = $null
            }
            try {
                Wait-Health $experimentName
            }
            catch {
                $failureCode = 'server_start'
                $failureEvidence = "$campaignRoot/logs/server-$label.stderr.log"
                Save-ContainerLogs $experimentName $label
                if (-not (Test-WslFile $failureEvidence)) { Write-WslText $failureEvidence $_.Exception.Message }
                try { Invoke-Wsl @('bash', '-c', "test -s $failureEvidence") | Out-Null }
                catch { Write-WslText $failureEvidence $_.Exception.Message }
            }
            if ($null -eq $failureCode) {
                $runArgs = @(
                    'python3', '/campaign/run_variant_campaign.py',
                    'run', '--arms', '/campaign/variant-campaign-arms.json', '--lane', $lane, '--arm', $label,
                    '--base-url', 'http://127.0.0.1:8080',
                    '--api-key-file', '/run/secrets/ninfer_api_key', '--model', $modelId,
                    '--campaign-id', $campaignId,
                    '--output', "/campaign/traces/run-$label.json", '--timeout', '1200', '--resume'
                )
                try {
                    Invoke-InContainer $experimentName $runArgs $label 'runner'
                }
                catch {
                    $failureCode = 'runner_error'
                    $failureEvidence = "$campaignRoot/logs/runner-$label.stderr.log"
                    $localErr = Join-Path $env:USERPROFILE "variant-5090-runner-$label.stderr.log"
                    $text = if (Test-Path -LiteralPath $localErr) { Get-Content -LiteralPath $localErr -Raw } else { '' }
                    if ([string]::IsNullOrWhiteSpace($text)) { $text = $_.Exception.Message }
                    Write-WslText $failureEvidence $text
                }
            }
            if ($null -eq $failureCode -and $needsQuality -and -not (Test-WslFile "$campaignRoot/quality/$label/scores.json")) {
                Invoke-InContainer $experimentName @('bash', '/campaign/quality.sh', $lane, $label, $campaignId) $label 'quality'
            }
        }
        finally {
            Remove-ContainerQuietly $samplerName
            $samplerName = $null
            if ($null -eq $failureCode) { Save-ContainerLogs $experimentName $label }
            try { Invoke-Docker @('stop', '--time', '30', $experimentName) | Out-Null } catch {}
            Remove-ContainerQuietly $experimentName
            $experimentName = $null
        }
        $summaryArgs = @(
            '-d', 'Ubuntu-24.04', '-e', 'python3', $runner, 'summarize',
            '--arms', $arms, '--lane', $lane,
            '--trace', $trace, '--server-log', $serverLog,
            '--output', $receipt
        )
        if (Test-WslFile $memorySamples) { $summaryArgs += @('--memory-samples', $memorySamples) }
        if ($null -ne $failureCode) {
            $failedStep = ((Invoke-Wsl @('python3', $runner, 'next-step', '--trace', $trace)) -join '').Trim()
            $summaryArgs += @('--failure-code', $failureCode, '--failed-step-id', $failedStep, '--failure-evidence', $failureEvidence)
        }
        Invoke-BoundedProcess 'wsl.exe' $summaryArgs `
            (Join-Path $env:USERPROFILE "variant-5090-summary-$label.stdout.log") `
            (Join-Path $env:USERPROFILE "variant-5090-summary-$label.stderr.log")
    }

    $incumbentLabel = [string]$contract.incumbent
    $incumbentReceipt = "$campaignRoot/receipts/arm-$incumbentLabel.json"
    $qualityReceipts = @()
    foreach ($arm in $contract.arms) {
        $label = [string]$arm.label
        if (-not ($arm.quality_gate -eq 'role-corpus' -and $arm.role -eq 'candidate')) { continue }
        $candidateScores = "$campaignRoot/quality/$label/scores.json"
        $referenceScores = "$campaignRoot/quality/$incumbentLabel/scores.json"
        if (-not (Test-WslFile $candidateScores) -or -not (Test-WslFile $referenceScores)) { continue }
        $qualityReceipt = "$campaignRoot/receipts/quality-$label.json"
        $qualityArgs = @(
            '-d', 'Ubuntu-24.04', '-e', 'python3', $runner, 'quality', '--arms', $arms, '--lane', $lane,
            '--arm-receipt', "$campaignRoot/receipts/arm-$label.json",
            '--reference-receipt', $incumbentReceipt,
            '--candidate-run', "$campaignRoot/quality/$label",
            '--reference-run', "$campaignRoot/quality/$incumbentLabel",
            '--output', $qualityReceipt
        )
        Invoke-BoundedProcess 'wsl.exe' $qualityArgs `
            (Join-Path $env:USERPROFILE "variant-5090-qualityreceipt-$label.stdout.log") `
            (Join-Path $env:USERPROFILE "variant-5090-qualityreceipt-$label.stderr.log")
        $qualityReceipts += "$label=$qualityReceipt"
    }

    $laneReceipt = "$campaignRoot/receipts/lane.json"
    $combineArgs = @('-d', 'Ubuntu-24.04', '-e', 'python3', $runner, 'combine', '--arms', $arms, '--lane', $lane)
    foreach ($arm in $contract.arms) {
        $combineArgs += @('--arm-receipt', "$campaignRoot/receipts/arm-$($arm.label).json")
    }
    foreach ($item in $qualityReceipts) { $combineArgs += @('--quality-receipt', $item) }
    $combineArgs += @('--output', $laneReceipt)
    Invoke-BoundedProcess 'wsl.exe' $combineArgs `
        (Join-Path $env:USERPROFILE 'variant-5090-combine.stdout.log') `
        (Join-Path $env:USERPROFILE 'variant-5090-combine.stderr.log')
    $decisionJson = Invoke-Wsl @(
        'python3', '-c',
        "import json; print(json.dumps(json.load(open('$laneReceipt'))['decision']))"
    )
    $decision = (($decisionJson -join [Environment]::NewLine) | ConvertFrom-Json)
    [ordered]@{
        status = 'passed'
        lane = $lane
        campaign_id = $campaignId
        selected_arm = $decision.selected_arm
        action = $decision.action
        quality_receipts = $qualityReceipts
        receipt = $laneReceipt
    } | ConvertTo-Json -Compress
}
finally {
    Remove-ContainerQuietly $samplerName
    Remove-ContainerQuietly $experimentName
    if ($incumbentStopped) {
        Invoke-Docker @('start', $incumbent) | Out-Null
        Wait-Health $incumbent
        $running = ((Invoke-Docker @('inspect', '--format', '{{.State.Running}}', $incumbent)) -join '').Trim()
        if ($running -ne 'true') { throw 'RTX5090 incumbent container is not running after restore' }
    }
}
