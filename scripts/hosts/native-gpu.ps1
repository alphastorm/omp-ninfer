# Bind host-side probes to the installed active release, never the server's CUDA ordinal.
function Resolve-NativeGpuUuid([string]$StateRoot) {
    $state = Get-Content -LiteralPath (Join-Path $StateRoot 'state.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $active = [string]$state.active_release
    $property = $state.releases.PSObject.Properties[$active]
    if (-not $active -or $null -eq $property) { throw 'installed active release is missing' }
    $binding = $property.Value.PSObject.Properties['gpu_uuid']
    if ($null -ne $binding -and -not [string]::IsNullOrWhiteSpace([string]$binding.Value)) {
        return [string]$binding.Value
    }
    # Historical records have no UUID. Enumerate only to prove there is exactly one card;
    # never guess index 0 on a multi-GPU host or use CUDA_VISIBLE_DEVICES as a shim.
    $cards = @(& nvidia-smi.exe --query-gpu=uuid --format=csv,noheader)
    if ($LASTEXITCODE -ne 0 -or $cards.Count -ne 1 -or [string]::IsNullOrWhiteSpace([string]$cards[0])) {
        throw 'installed release has no gpu_uuid; exactly one GPU is required for a legacy record'
    }
    return ([string]$cards[0]).Trim()
}

function Get-NativeGpuPowerLimit([string]$GpuUuid) {
    $values = @(& nvidia-smi.exe -i $GpuUuid --query-gpu=power.limit --format=csv,noheader,nounits)
    if ($LASTEXITCODE -ne 0 -or $values.Count -ne 1) { throw 'lane power query failed' }
    return [double]$values[0]
}
