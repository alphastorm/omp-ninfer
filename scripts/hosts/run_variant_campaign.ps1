[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateSet('rtx5090', 'rtx4090', 'rtx3090')][string]$Lane,
    [Parameter(Mandatory = $true)][string]$Plan,
    [Parameter(Mandatory = $true)][string]$Output,
    [ValidateSet('c1', 'role', 'quality', 'retrieval', 'requests', 'command')][string]$Mode = 'c1',
    [string]$Python = 'python',
    [ValidateRange(-1, 3)][int]$ArmIndex = -1,
    [switch]$Nsys
)
# Run on the GPU host under the fleet's hostlock/gpu-lease. On WSL use the Python
# entrypoint directly, never invoke WSL/Docker through a Windows SSH session.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$runner = Join-Path $PSScriptRoot 'variant_campaign.py'
$arguments = @($runner, '--lane', $Lane, '--plan', $Plan, '--out', $Output, '--mode', $Mode)
if ($ArmIndex -ge 0) { $arguments += @('--arm-index', [string]$ArmIndex) }
if ($Nsys) { $arguments += '--nsys' }
$pythonCommand = Get-Command -Name $Python -CommandType Application -ErrorAction Stop
$global:LASTEXITCODE = 2
$ErrorActionPreference = 'Continue'
& $pythonCommand.Source @arguments
exit $LASTEXITCODE
