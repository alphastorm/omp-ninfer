<# Private acceptance orchestration. Invoke as text so documented-route policy is real.
   -DryRun never changes the filesystem, host markers, tasks, or processes. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('Preflight','Inventory','Hold','Release','Route','Live','Outage')][string]$Action,
    [Parameter(Mandatory=$true)][string]$Workspace,
    [Parameter(Mandatory=$true)][string]$Release,
    [Parameter(Mandatory=$true)][string]$Candidate,
    [string]$ControlRoot='C:\ProgramData\OMP\windows-hosts',
    [switch]$DryRun
)
$ErrorActionPreference='Stop'
if ($DryRun) { @{status='dry-run';action=$Action;workspace=$Workspace;effects='none'} | ConvertTo-Json -Compress; return }
$RealLocal=$env:LOCALAPPDATA
$Clone=Join-Path $Workspace 'candidate'
$Bundle=Join-Path $Workspace 'windows-bundle'
$Hold=Join-Path $ControlRoot 'state\lane-container-paused'
function Save-Json($Name,$Value) { [IO.File]::WriteAllText((Join-Path $Workspace $Name),($Value|ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false)) }
function Snapshot {
    $markers=@()
    foreach($root in @((Join-Path $ControlRoot 'state'),(Join-Path $RealLocal 'OMP'))) {
        if(Test-Path $root) {
            $markers+=@(Get-ChildItem -LiteralPath $root -Recurse -Force -File | Where-Object {$_.Name -match 'paused|hold'} | Sort-Object FullName | ForEach-Object {
                @{path=$_.FullName;sha256=(Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant();sddl=(Get-Acl $_.FullName).Sddl;bytes=$_.Length}
            })
        }
    }
    $tasks=@(Get-ScheduledTask | Where-Object {$_.TaskName -like 'OMP*'} | Sort-Object TaskPath,TaskName | ForEach-Object {
        $xml=Export-ScheduledTask -TaskName $_.TaskName -TaskPath $_.TaskPath
        $hash=[Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($xml))
        @{name=$_.TaskName;path=$_.TaskPath;state=$_.State.ToString();definition_sha256=([BitConverter]::ToString($hash)).Replace('-','').ToLowerInvariant()}
    })
    $response=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:18088/health' -TimeoutSec 10
    if([int]$response.StatusCode -ne 200){throw 'Windows production health did not return HTTP 200'}
    $health=$response.Content|ConvertFrom-Json
    return @{timestamp=[DateTime]::UtcNow.ToString('o');markers=$markers;tasks=$tasks;windows_health18088=$health;windows_http_status=[int]$response.StatusCode;execution_policies=@(Get-ExecutionPolicy -List|ForEach-Object {@{scope=$_.Scope.ToString();policy=$_.ExecutionPolicy.ToString()}})}
}
function Isolate($Name) {
    $NewHome=Join-Path $Workspace $Name
    New-Item -ItemType Directory -Force -Path $NewHome | Out-Null
    Set-Variable -Name HOME -Value $NewHome -Scope Global -Force
    $env:HOME=$NewHome; $env:USERPROFILE=$NewHome
    $env:LOCALAPPDATA=Join-Path $NewHome 'AppData\Local'; $env:APPDATA=Join-Path $NewHome 'AppData\Roaming'
    $env:TEMP=Join-Path $NewHome 'tmp'; $env:TMP=$env:TEMP
    New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
}
function Probe($Phase) {
    $args2=@('-3',(Join-Path $Workspace 'omp-client-probe.py'),'--release',$Release,'--candidate',$Candidate,'--phase',$Phase,
        '--output',(Join-Path $Workspace 'windows-structured'),'--binary',(Join-Path $env:LOCALAPPDATA 'OMP\omp.cmd'),
        '--clone',$Clone,'--platform','windows-x64','--profile','windows-docker-local','--key-file',(Join-Path $HOME '.omp\agent\ninfer-beta.key'),
        '--vision-image',(Join-Path $Clone 'assets\icon-512.png'))
    & py @args2
    if($LASTEXITCODE -ne 0){throw "structured probe $Phase failed (exit $LASTEXITCODE)"}
}
if($Action -eq 'Inventory') { Snapshot | ConvertTo-Json -Depth 20; return }
if($Action -eq 'Hold') {
    if(Test-Path $Hold){throw 'lane hold already exists; refusing ownership'}
    $baseline=Snapshot
    Save-Json 'windows-baseline.json' $baseline
    . (Join-Path $ControlRoot 'bin\windows-host-common.ps1')
    New-Item -ItemType File -Path $Hold | Out-Null
    Set-OmpAdminOnlyFile -Path $Hold
    Save-Json 'own-hold.json' @{created_utc=[DateTime]::UtcNow.ToString('o');path=$Hold}
    Write-Output 'own lane hold acquired'; return
}
if($Action -eq 'Release') {
    $health=Invoke-RestMethod -Uri 'http://127.0.0.1:18088/health' -TimeoutSec 10
    if($health.status -ne 'ok'){throw 'refusing hold release before Windows production health'}
    if(!(Test-Path (Join-Path $Workspace 'own-hold.json'))){throw 'no ownership receipt'}
    if(Test-Path $Hold){Remove-Item -LiteralPath $Hold -Force}
    $final=Snapshot; Save-Json 'windows-final.json' $final
    $before=Get-Content -Raw (Join-Path $Workspace 'windows-baseline.json')|ConvertFrom-Json
    # Hashes, ACLs, definitions, and task states are compared structurally by the collector.
    if($final.markers.Count -ne @($before.markers).Count){throw 'marker inventory count changed'}
    Write-Output 'own lane hold removed after Windows production health'; return
}
if($Action -eq 'Preflight') {
    New-Item -ItemType Directory -Force -Path $Workspace | Out-Null
    if(!(Test-Path $Clone)) { & git clone -q https://github.com/alphastorm/omp-ninfer.git $Clone; if($LASTEXITCODE -ne 0){throw 'candidate clone failed'}; & git -C $Clone checkout -q $Candidate; if($LASTEXITCODE -ne 0){throw 'candidate checkout failed'} }
    if((& git -C $Clone rev-parse HEAD).Trim() -cne $Candidate){throw 'wrong candidate checkout'}
    if((& git -C $Clone status --porcelain | Out-String).Trim()){throw 'candidate clone is dirty'}
    if(!(Test-Path (Join-Path $Bundle 'manifest.json'))) { & py -3 (Join-Path $Clone 'scripts\documented_route.py') bundle --lane rtx5090-windows-client --output $Bundle; if($LASTEXITCODE -ne 0){throw 'bundle failed'} }
    $Tokens=$null;$ParseErrors=$null
    Get-ChildItem $Bundle -Filter '*.ps1' | ForEach-Object { [Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$Tokens,[ref]$ParseErrors)|Out-Null; if($ParseErrors.Count){throw $ParseErrors} }
    $compat=Get-Content -Raw (Join-Path $Clone 'compatibility.json')|ConvertFrom-Json
    $dist=($compat.profiles|Where-Object {$_.id -eq 'windows-docker-local'}).client_distribution
    $Archive=Join-Path $Workspace ([IO.Path]::GetFileName($dist.asset_url))
    if(!(Test-Path $Archive)) { & curl.exe --fail --location --silent --show-error --output $Archive $dist.asset_url; if($LASTEXITCODE -ne 0){throw 'anonymous client download failed'} }
    $archiveHash=(Get-FileHash $Archive -Algorithm SHA256).Hash.ToLowerInvariant()
    if($archiveHash -cne $dist.archive_sha256){throw 'published archive checksum mismatch'}
    $Package=Join-Path $Workspace ([IO.Path]::GetFileName($Archive).Replace('.tar.gz',''))
    if(!(Test-Path $Package)){& tar.exe -xzf $Archive -C $Workspace;if($LASTEXITCODE -ne 0){throw 'archive extraction failed'}}
    Isolate 'structured-home'
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
    if(!(Test-Path (Join-Path $env:LOCALAPPDATA 'OMP\omp.cmd'))) { & (Join-Path $Package 'install.ps1') }
    $binary=@(Get-ChildItem (Join-Path $env:LOCALAPPDATA 'OMP\releases') -Recurse -Filter omp.exe)[0]
    $binaryHash=(Get-FileHash $binary.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    if($binaryHash -cne $dist.binary_sha256){throw 'installed binary checksum mismatch'}
    Probe 'preflight'
    Save-Json 'windows-preflight.json' @{status='passed';candidate=$Candidate;archive_sha256=$archiveHash;binary_sha256=$binaryHash;source_commit=$dist.source_commit;archive_bytes=(Get-Item $Archive).Length;completed_utc=[DateTime]::UtcNow.ToString('o')}
    return
}
if($Action -eq 'Route') {
    $work=Join-Path $Workspace 'route-work'
    if(Test-Path $work){throw 'route workspace already exists; no implicit retry'}
    New-Item -ItemType Directory -Path $work | Out-Null
    Isolate 'documented-home'
    & ([scriptblock]::Create([IO.File]::ReadAllText((Join-Path $Clone 'scripts\hosts\run-documented-route.ps1')))) -Bundle $Bundle -WorkDir $work -Receipt (Join-Path $Workspace 'windows-route.json') -CloneOverride $Candidate
    exit $LASTEXITCODE
}
Isolate 'structured-home'
Set-Location $Clone
$key=Join-Path $HOME '.omp\agent\ninfer-beta.key'
if(!(Test-Path $key)) { Invoke-Expression ([IO.File]::ReadAllText((Join-Path $Bundle '03-provider.ps1'))) }
$env:NINFER_BETA_API_KEY=(Get-Content -Raw $key).Trim()
if($Action -eq 'Live') { Probe 'live' } else { Probe 'outage' }
