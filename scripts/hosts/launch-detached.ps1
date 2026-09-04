[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Script,
    [Parameter(Mandatory = $true)][string]$Log
)

# Launches a campaign runner outside the calling SSH session's job object. Windows OpenSSH
# kills every descendant of the session shell on disconnect, including `Start-Process`
# children; a process created through WMI is parented by WmiPrvSE and survives.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Script -PathType Leaf)) { throw "missing script: $Script" }
$command = 'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "& ''' + $Script + ''' *> ''' + $Log + '''"'
$result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $command }
if ($result.ReturnValue -ne 0) { throw "Win32_Process.Create returned $($result.ReturnValue)" }
$parent = (Get-CimInstance Win32_Process -Filter "ProcessId=$($result.ProcessId)").ParentProcessId
$parentName = (Get-CimInstance Win32_Process -Filter "ProcessId=$parent").Name
[ordered]@{ pid = $result.ProcessId; parent = $parentName; log = $Log } | ConvertTo-Json -Compress
