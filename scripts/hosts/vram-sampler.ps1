[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Output,
    [Parameter(Mandatory = $true)][string]$StateRoot
)
$ErrorActionPreference = 'Stop'
. ([scriptblock]::Create([IO.File]::ReadAllText((Join-Path $PSScriptRoot 'native-gpu.ps1'))))
$gpuUuid = Resolve-NativeGpuUuid $StateRoot
while ($true) {
    $lines = @(& nvidia-smi -i $gpuUuid --query-gpu=memory.used --format=csv,noheader,nounits)
    if ($LASTEXITCODE -eq 0 -and $lines.Count -eq 1) {
        $line = '{"utc":"' + [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ') + '","memory_used_mib":' + ([string]$lines[0]).Trim() + '}'
        [IO.File]::AppendAllText($Output, $line + "`n")
    }
    Start-Sleep -Seconds 5
}
