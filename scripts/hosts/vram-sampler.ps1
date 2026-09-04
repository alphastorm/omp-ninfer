[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$Output)
while ($true) {
    $lines = @(& nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
    if ($LASTEXITCODE -eq 0 -and $lines.Count -gt 0) {
        $line = '{"utc":"' + [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ') + '","memory_used_mib":' + ([string]$lines[0]).Trim() + '}'
        [IO.File]::AppendAllText($Output, $line + "`n")
    }
    Start-Sleep -Seconds 5
}
