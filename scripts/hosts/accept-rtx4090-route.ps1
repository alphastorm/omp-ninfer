<#
.SYNOPSIS
Accept a frozen documented native route in an isolated child, then restore the exact host.
.DESCRIPTION
Invoke as text (not with ExecutionPolicy Bypass), like run-documented-route.ps1.
Preflight changes only Workspace. DryRun validates its snapshot without host mutations.
Accept requires a successful Preflight and a fresh attempt workspace. Restore is independently
callable after transport loss. Never collect the preserved secrets directory off this host.
The published runtime is installed fresh after moving its existing instance aside; this is
not an idempotent-reinstall qualification. No older instance data is modified.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Release,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{40}$')][string]$Candidate,
    [Parameter(Mandatory=$true)][string]$Workspace,
    [Parameter(Mandatory=$true)][string]$Bundle,
    [Parameter(Mandatory=$true)][string]$Clone,
    [Parameter(Mandatory=$true)][string]$ExpectedStateSha256,
    [Parameter(Mandatory=$true)][string]$TemporaryPrevious,
    [ValidateSet('DryRun','Preflight','Accept','Restore','Audit','Route','Live','Offline')][string]$Mode='DryRun',
    [string]$StateRoot='C:\ProgramData\NInfer\qwen38-4090-native',
    [string]$TaskName='NInfer-Qwen38-4090-Native',
    [string]$Stage='C:\ProgramData\omp-ninfer-stage-rtx4090-windows-native',
    [string]$Model='C:\ProgramData\omp-ninfer-model\qwen3_8_27b.ninfer',
    [string]$KeyFile='C:\ProgramData\omp-ninfer-keys\api-key.txt',
    [string]$HostState='C:\ProgramData\OMP\windows-hosts\state',
    [string]$RealHome=$env:USERPROFILE,
    [ValidateRange(1,2)][int]$Attempt=1,
    [ValidateRange(1,45)][int]$WindowMinutes=45
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$utf8=[Text.UTF8Encoding]::new($false)
$controller=Join-Path $StateRoot 'Control-Release.ps1'
$self=Join-Path $Workspace 'accept-rtx4090-route.ps1'
$runner=Join-Path $Workspace 'run-documented-route.ps1'
$baseline=Join-Path $Workspace 'baseline'
$journal=Join-Path $Workspace 'preparation.json'
$realClient=Join-Path $RealHome 'AppData\Local\OMP'
function SaveJson($path,$value) { [IO.File]::WriteAllText($path,($value|ConvertTo-Json -Depth 50)+"`n",$utf8) }
function ReadJson($path) { Get-Content -LiteralPath $path -Raw -Encoding UTF8|ConvertFrom-Json }
function Hash($path) { if(Test-Path -LiteralPath $path -PathType Leaf){(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}else{$null} }
function Quote($value) { "'"+([string]$value).Replace("'","''")+"'" }
function Describe($path) {
    $exists=Test-Path -LiteralPath $path
    [ordered]@{path=$path;exists=$exists;sha256=(Hash $path);sddl=$(if($exists){(Get-Acl -LiteralPath $path).Sddl}else{$null})}
}
function Probe {
    $state=ReadJson "$StateRoot\state.json"
    $holdPaths=@("$HostState\container-host-paused","$HostState\lane-container-paused","$realClient\local-4090-supervisor\paused")
    if(Test-Path $HostState){$holdPaths+=@(Get-ChildItem $HostState -File|Where-Object Name -Match 'paused|hold'|ForEach-Object FullName)}
    $holds=@($holdPaths|Sort-Object -Unique|ForEach-Object {Describe $_})
    $pointers=@('current.txt','previous.txt','omp.cmd')|ForEach-Object {Describe (Join-Path $realClient $_)}
    [ordered]@{
        utc=[DateTime]::UtcNow.ToString('o');state_sha256=(Hash "$StateRoot\state.json")
        state_sddl=(Get-Acl "$StateRoot\state.json").Sddl;root_sddl=(Get-Acl $StateRoot).Sddl
        active_release=$state.active_release;previous_release=$state.previous_release;prepared_release=$state.prepared_release
        task_state=[string](Get-ScheduledTask -TaskName $TaskName).State
        processes=@(Get-CimInstance Win32_Process -Filter "Name='ninfer-serve.exe'"|Select-Object ProcessId,ExecutablePath)
        listeners=@(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue|Where-Object LocalPort -in @(18082,18088,18089,18099)|Select-Object LocalAddress,LocalPort,OwningProcess)
        lease_present=(Test-Path "$StateRoot\gpu-owner-state\lease.json")
        lease_entries=@(Get-ChildItem "$StateRoot\gpu-owner-state" -Force|ForEach-Object Name)
        power_limit_w=[double]((& nvidia-smi --query-gpu=power.limit --format=csv,noheader,nounits|Out-String).Trim())
        holds=$holds;client_pointers=@($pointers)
    }
}
function AssertBaseline($p) {
    if($p.state_sha256 -cne $ExpectedStateSha256 -or $null -ne $p.prepared_release -or
       $p.task_state -cne 'Ready' -or @($p.processes).Count -ne 0 -or @($p.listeners).Count -ne 0 -or
       $p.lease_present -or @($p.lease_entries).Count -ne 0 -or $p.power_limit_w -ne 450 -or
       -not (Test-Path "$HostState\container-host-paused")){throw 'baseline differs from authorized stopped state'}
    $s=ReadJson "$StateRoot\state.json"
    if(-not $s.releases.PSObject.Properties[$TemporaryPrevious]){throw 'temporary previous release missing'}
    if($s.active_release -eq $s.previous_release -or $s.active_release -eq $TemporaryPrevious){throw 'invalid temporary lineage'}
}
function SupportFiles {
    @(Get-ChildItem $StateRoot -File -Force)
    foreach($sub in @('gpu-owner','gpu-owner-state','receipts')) {
        if(Test-Path "$StateRoot\$sub"){ @(Get-ChildItem "$StateRoot\$sub" -File -Recurse -Force) }
    }
}
function SupportDirectories {
    Get-Item $StateRoot
    foreach($sub in @('gpu-owner','gpu-owner-state','receipts')) {
        if(Test-Path "$StateRoot\$sub"){Get-Item "$StateRoot\$sub";Get-ChildItem "$StateRoot\$sub" -Directory -Recurse -Force}
    }
}
function Snapshot($destination) {
    if(Test-Path $destination){throw "snapshot already exists: $destination"}
    New-Item -ItemType Directory -Path "$destination\files" -Force|Out-Null
    $observable=Probe;AssertBaseline $observable
    [IO.File]::WriteAllText("$destination\task.xml",[string](Export-ScheduledTask -TaskName $TaskName),$utf8)
    $files=@();$directories=@()
    foreach($file in @(SupportFiles)) {
        $relative=$file.FullName.Substring($StateRoot.Length).TrimStart('\')
        $copy=Join-Path "$destination\files" $relative
        New-Item -ItemType Directory -Force (Split-Path $copy -Parent)|Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $copy
        $files+=@{relative=$relative;sha256=(Hash $file.FullName);sddl=(Get-Acl $file.FullName).Sddl}
    }
    foreach($dir in @(SupportDirectories)) {
        $directories+=@{relative=$dir.FullName.Substring($StateRoot.Length).TrimStart('\');sddl=(Get-Acl $dir.FullName).Sddl}
    }
    SaveJson "$destination\snapshot.json" @{observable=$observable;files=$files;directories=$directories;task_xml_sha256=(Hash "$destination\task.xml")}
    return ReadJson "$destination\snapshot.json"
}
function EnableExactAcl {
    if(-not ('NInferAcceptanceExactAcl' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class NInferAcceptanceExactAcl {
 [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
 [return: MarshalAs(UnmanagedType.Bool)]
 public static extern bool SetFileSecurity(string path, uint information, byte[] descriptor);
}
'@
    }
}
function SetExactAcl($path,$sddl) {
    if((Get-Acl -LiteralPath $path).Sddl -ceq $sddl){return}
    $sd=[Security.AccessControl.RawSecurityDescriptor]::new([string]$sddl)
    $bytes=[byte[]]::new($sd.BinaryLength);$sd.GetBinaryForm($bytes,0)
    if(-not [NInferAcceptanceExactAcl]::SetFileSecurity($path,7,$bytes)){throw "SetFileSecurity failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())"}
    if((Get-Acl -LiteralPath $path).Sddl -cne $sddl){throw "exact SDDL not retained: $path"}
}
function ValidateSnapshot($destination) {
    $b=ReadJson "$destination\snapshot.json"
    foreach($f in $b.files){if((Hash (Join-Path "$destination\files" $f.relative)) -cne $f.sha256){throw "snapshot corrupt: $($f.relative)"}}
    if((Hash "$destination\task.xml") -cne $b.task_xml_sha256){throw 'task snapshot corrupt'}
    if([IO.Path]::GetPathRoot($StateRoot) -cne [IO.Path]::GetPathRoot($Workspace) -or
       [IO.Path]::GetPathRoot($Stage) -cne [IO.Path]::GetPathRoot($Workspace)){throw 'preservation requires same-volume workspace'}
    return $b
}
function SetIsolation($name) {
    $h=Join-Path $Workspace ($name+'-home')
    Set-Variable -Name HOME -Value $h -Scope Global -Force
    $env:HOME=$h;$env:USERPROFILE=$h;$env:LOCALAPPDATA="$h\AppData\Local";$env:APPDATA="$h\AppData\Roaming"
    $env:TEMP=Join-Path $Workspace ($name+'-temp');$env:TMP=$env:TEMP
    New-Item -ItemType Directory -Force $h,$env:TEMP,$env:LOCALAPPDATA,$env:APPDATA|Out-Null
}
function Child($childMode,$seconds) {
    $values=@{Release=$Release;Candidate=$Candidate;Workspace=$Workspace;Bundle=$Bundle;Clone=$Clone;
        ExpectedStateSha256=$ExpectedStateSha256;TemporaryPrevious=$TemporaryPrevious;Mode=$childMode;
        StateRoot=$StateRoot;TaskName=$TaskName;Stage=$Stage;Model=$Model;KeyFile=$KeyFile;HostState=$HostState;RealHome=$RealHome;Attempt=$Attempt;WindowMinutes=$WindowMinutes}
    $command='& ([scriptblock]::Create([IO.File]::ReadAllText('+ (Quote $self) +')))'
    foreach($k in $values.Keys){$command+=' -'+$k+' '+(Quote $values[$k])}
    $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
    $name=$childMode.ToLowerInvariant()
    $p=Start-Process -FilePath "$PSHOME\powershell.exe" -ArgumentList @('-NoProfile','-NonInteractive','-EncodedCommand',$encoded) -PassThru -RedirectStandardOutput "$Workspace\$name.stdout.log" -RedirectStandardError "$Workspace\$name.stderr.log"
    $handle=$p.Handle # Required: WaitForExit(timeout) otherwise loses the exit code on Windows PowerShell.
    if(-not $p.WaitForExit($seconds*1000)){& taskkill.exe /PID $p.Id /T /F|Out-Null;throw "$childMode child timeout; restore now"}
    $p.WaitForExit();$p.Refresh();$code=$p.ExitCode
    if($null -eq $code){throw "$childMode child exit code unavailable"}
    return [int]$code
}
function Control($action,$file) {
    # The installed controller resolves support files through PSScriptRoot. Only the
    # documented runner is pasted as text; lifecycle helpers must retain their file scope.
    $priorPolicy=Get-ExecutionPolicy -Scope Process
    try {
        Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
        & $controller -Action $action -StateRoot $StateRoot | Out-File -Encoding UTF8 (Join-Path $Workspace $file)
    } finally { Set-ExecutionPolicy -Scope Process -ExecutionPolicy $priorPolicy -Force }
}
function Audit($b) {
    $after=Probe;$checks=[ordered]@{
        state_bytes_identical=($after.state_sha256 -ceq $b.observable.state_sha256)
        state_acl_identical=($after.state_sddl -ceq $b.observable.state_sddl)
        root_acl_identical=($after.root_sddl -ceq $b.observable.root_sddl)
        task_xml_identical=([string](Export-ScheduledTask -TaskName $TaskName) -ceq [IO.File]::ReadAllText("$baseline\task.xml"))
        task_ready=($after.task_state -ceq 'Ready');no_process=(@($after.processes).Count -eq 0)
        no_listener=(@($after.listeners).Count -eq 0);no_lease=(-not $after.lease_present -and @($after.lease_entries).Count -eq 0)
        power_identical=($after.power_limit_w -eq $b.observable.power_limit_w)
        pointers_identical=($after.active_release -ceq $b.observable.active_release -and $after.previous_release -ceq $b.observable.previous_release -and $null -eq $after.prepared_release)
        holds_identical=(($after.holds|ConvertTo-Json -Depth 8 -Compress) -ceq ($b.observable.holds|ConvertTo-Json -Depth 8 -Compress))
        client_pointers_identical=(($after.client_pointers|ConvertTo-Json -Depth 8 -Compress) -ceq ($b.observable.client_pointers|ConvertTo-Json -Depth 8 -Compress))
        support_identical=$true;support_inventory_identical=$true;directory_acls_identical=$true;pending_preserved_moves=(@(Get-ChildItem "$Workspace\preserved" -Force -ErrorAction SilentlyContinue).Count -eq 0)
    }
    foreach($f in $b.files){$p=Join-Path $StateRoot $f.relative;if((Hash $p) -cne $f.sha256 -or (Get-Acl $p).Sddl -cne $f.sddl){$checks.support_identical=$false}}
    $current=@(SupportFiles|ForEach-Object {$_.FullName.Substring($StateRoot.Length).TrimStart('\')}|Sort-Object)
    if(($current -join "`n") -cne ((@($b.files.relative|Sort-Object)) -join "`n")){$checks.support_inventory_identical=$false}
    foreach($d in $b.directories){if((Get-Acl (Join-Path $StateRoot $d.relative)).Sddl -cne $d.sddl){$checks.directory_acls_identical=$false}}
    $ok=@($checks.Values|Where-Object {$_ -ne $true}).Count -eq 0
    return @{status=$(if($ok){'passed'}else{'failed'});completed_utc=[DateTime]::UtcNow.ToString('o');checks=$checks;after=$after}
}
function Restore {
    $started=[DateTime]::UtcNow;$b=ValidateSnapshot $baseline;EnableExactAcl
    $prep=ReadJson $journal
    if($prep.status -eq 'restored'){return Audit $b}
    Control Stop 'restoration-stop.json'
    if(@(Get-CimInstance Win32_Process -Filter "Name='ninfer-serve.exe'").Count -ne 0 -or
       [string](Get-ScheduledTask -TaskName $TaskName).State -ceq 'Running'){throw 'stop incomplete: refusing pointer restoration'}
    # Never relocate the route-created secret outside the protected on-host workspace.
    foreach($m in $prep.moves) {
        if(Test-Path -LiteralPath $m.preserved) {
            if(Test-Path -LiteralPath $m.path){Move-Item -LiteralPath $m.path -Destination (Join-Path "$Workspace\qualified-artifacts" $m.kind)}
            Move-Item -LiteralPath $m.preserved -Destination $m.path
        }
    }
    foreach($file in @(SupportFiles)) {
        $relative=$file.FullName.Substring($StateRoot.Length).TrimStart('\')
        if($relative -notin @($b.files.relative)) {
            $dst=Join-Path "$Workspace\qualified-artifacts\support" $relative
            New-Item -ItemType Directory -Force (Split-Path $dst -Parent)|Out-Null
            Move-Item -LiteralPath $file.FullName -Destination $dst
        }
    }
    foreach($f in $b.files) {
        $path=Join-Path $StateRoot $f.relative
        if((Hash $path) -cne $f.sha256){Copy-Item -LiteralPath (Join-Path "$baseline\files" $f.relative) -Destination $path -Force}
        SetExactAcl $path $f.sddl
    }
    foreach($d in @(SupportDirectories|Sort-Object {$_.FullName.Length} -Descending)) {
        $relative=$d.FullName.Substring($StateRoot.Length).TrimStart('\')
        if($relative -notin @($b.directories.relative) -and @(Get-ChildItem $d.FullName -Force).Count -eq 0){Remove-Item -LiteralPath $d.FullName -Force}
    }
    foreach($d in $b.directories){SetExactAcl (Join-Path $StateRoot $d.relative) $d.sddl}
    $xml=[IO.File]::ReadAllText("$baseline\task.xml")
    if([string](Export-ScheduledTask -TaskName $TaskName) -cne $xml){Register-ScheduledTask -TaskName $TaskName -Xml $xml -Force|Out-Null}
    $power=[double]((& nvidia-smi --query-gpu=power.limit --format=csv,noheader,nounits|Out-String).Trim())
    if($power -ne $b.observable.power_limit_w){& nvidia-smi -pl $b.observable.power_limit_w|Out-Null;if($LASTEXITCODE -ne 0){throw 'power restoration failed'}}
    $result=Audit $b;$result.started_utc=$started.ToString('o');$result.elapsed_seconds=([DateTime]::UtcNow-$started).TotalSeconds
    SaveJson "$Workspace\restoration.json" $result
    if($result.status -ceq 'passed'){$prep.status='restored';SaveJson $journal $prep}
    return $result
}
# Child isolation happens before any OMP invocation; none of these modes write real client pointers.
if($Mode -eq 'Route') {
    SetIsolation 'route';$work=Join-Path $Workspace 'route-work'
    if(Test-Path $work){throw 'route work already exists; use a new attempt workspace'}
    New-Item -ItemType Directory -Path $work|Out-Null
    & ([scriptblock]::Create([IO.File]::ReadAllText($runner))) -Bundle $Bundle -WorkDir $work -Receipt "$Workspace\route.json" -CloneOverride $Candidate
    exit $LASTEXITCODE
}
if($Mode -in @('Live','Offline')) {
    SetIsolation 'route';$env:NINFER_NATIVE_API_KEY=[IO.File]::ReadAllText($KeyFile).Trim()
    $binary=@(Get-ChildItem "$env:LOCALAPPDATA\OMP" -Filter omp.exe -File -Recurse)
    if($binary.Count -ne 1){throw 'isolated installed client binary ambiguous'}
    $phase=if($Mode -eq 'Live'){'live'}else{'outage'}
    & py -3 "$Workspace\omp-client-probe.py" --release $Release --candidate $Candidate --phase $phase --output "$Workspace\structured" --binary $binary[0].FullName --clone $Clone --platform windows-x64 --profile windows-docker-local --provider ninfer-native-4090 --model ninfer-native-4090/local-max --endpoint http://127.0.0.1:18082/v1 --key-file $KeyFile --expected-runtime "$Workspace\expected-runtime.json"
    exit $LASTEXITCODE
}
if($Mode -eq 'DryRun') {
    $p=Probe;AssertBaseline $p
    Control Status 'dryrun-controller-status.json'
    $status=ReadJson "$Workspace\dryrun-controller-status.json"
    if($status.process_state -cne 'stopped' -or $status.task_state -cne 'Ready'){throw 'controller dry-run state drift'}
    $snapshot=if(Test-Path "$baseline\snapshot.json"){$baseline}else{Join-Path $Workspace 'preflight-snapshot'}
    $b=ValidateSnapshot $snapshot
    [ordered]@{status='passed';mode='dry-run';release=$Release;candidate=$Candidate;canonical_mutations=0;restoration_snapshot=$snapshot;validated_support_files=@($b.files).Count;baseline=$p}|ConvertTo-Json -Depth 8
    return
}
if($Mode -eq 'Preflight') {
    $started=[DateTime]::UtcNow;AssertBaseline (Probe)
    if(Test-Path "$Workspace\preflight.json"){throw 'preflight receipt exists; do not repeat successful setup'}
    # Protect private snapshots and moved originals with the already-installed trusted helper.
    . ([scriptblock]::Create([IO.File]::ReadAllText("$StateRoot\Protect-StateRoot.ps1")))
    Set-NInferProtectedRootAcl $Workspace
    New-Item -ItemType Directory -Force "$Workspace\assets","$Workspace\preflight-work"|Out-Null
    if(-not (Test-Path "$Clone\.git")) {
        & git clone -q https://github.com/alphastorm/omp-ninfer.git $Clone
        if($LASTEXITCODE -ne 0){throw 'preflight clone failed'}
        & git -C $Clone checkout -q $Candidate
        if($LASTEXITCODE -ne 0){throw 'preflight checkout failed'}
    }
    if((& git -C $Clone rev-parse HEAD|Out-String).Trim() -cne $Candidate -or (& git -C $Clone status --porcelain|Out-String).Trim()){throw 'candidate clone is not clean and exact'}
    $manifest=ReadJson "$Clone\releases\$Release\manifest.json"
    $variant=@($manifest.components.ninfer_variants|Where-Object id -CEQ 'rtx4090-windows-native')[0]
    $bundleManifest=ReadJson "$Bundle\manifest.json"
    if((Hash "$Clone\docs\QUICKSTART.md") -cne $bundleManifest.document_sha256){throw 'bundle document mismatch'}
    foreach($step in $bundleManifest.steps){if((Hash (Join-Path $Bundle $step.file)) -cne $step.sha256){throw 'bundle block mismatch'};$tokens=$null;$errors=$null;[Management.Automation.Language.Parser]::ParseFile((Join-Path $Bundle $step.file),[ref]$tokens,[ref]$errors)|Out-Null;if($errors.Count){throw "bundle parse failed: $($step.slug)"}}
    if((Hash $runner) -cne (Hash "$Clone\scripts\hosts\run-documented-route.ps1")){throw 'runner not from candidate'}
    Push-Location $Clone
    try{& py -3 scripts\verify_release.py --release $Release --require-installable;if($LASTEXITCODE -ne 0){throw 'candidate not installable'}}finally{Pop-Location}
    $assets=@()
    foreach($name in @('package','installer','controller','gpu_owner_controller','state_protection')) {
        $url=[string]$variant.($name+'_url');$path=Join-Path "$Workspace\assets" ([IO.Path]::GetFileName(([Uri]$url).AbsolutePath))
        if(-not (Test-Path $path)){Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $path}
        $actual=Hash $path;if($actual -cne [string]$variant.($name+'_sha256')){throw "published asset mismatch: $name"}
        $assets+=@{name=$name;url=$url;sha256=$actual;bytes=(Get-Item $path).Length}
    }
    SetIsolation 'preflight';Set-Location "$Workspace\preflight-work"
    Invoke-Expression ([IO.File]::ReadAllText("$Bundle\01-client-install.ps1"))
    if($LASTEXITCODE -ne 0){throw 'isolated client install failed'}
    $binary=@(Get-ChildItem "$env:LOCALAPPDATA\OMP" -Filter omp.exe -File -Recurse)
    if($binary.Count -ne 1 -or (Hash $binary[0].FullName) -cne $manifest.components.omp.binary_sha256){throw 'client binary mismatch'}
    & py -3 "$Workspace\omp-client-probe.py" --release $Release --candidate $Candidate --phase preflight --output "$Workspace\structured" --binary $binary[0].FullName --clone $Clone --platform windows-x64 --profile windows-docker-local --provider ninfer-native-4090 --model ninfer-native-4090/local-max --endpoint http://127.0.0.1:18082/v1
    if($LASTEXITCODE -ne 0){throw 'structured probe preflight failed'}
    $version=(& $binary[0].FullName --version|Out-String).Trim()
    & $binary[0].FullName --help > "$Workspace\client-help.txt"
    $agent=Join-Path $HOME '.omp\agent';New-Item -ItemType Directory -Force $agent|Out-Null
    Copy-Item "$Clone\examples\windows-native\models.fragment.yml" "$agent\models.yml"
    Copy-Item "$Clone\examples\manual-tunnel\fail-closed.yml" "$agent\config.yml"
    & $binary[0].FullName models ninfer-native-4090 --json > "$Workspace\parser-models.json"
    if($LASTEXITCODE -ne 0){throw 'provider parser failed'}
    $modelSha=Hash $Model;if($modelSha -cne $manifest.components.model.artifact_sha256 -or (Get-Item $Model).Length -ne $manifest.components.model.artifact_bytes){throw 'documented model identity mismatch'}
    if(-not (Test-Path $KeyFile)){throw 'documented key missing'}
    $b=Snapshot "$Workspace\preflight-snapshot";EnableExactAcl
    $probe="$Workspace\acl-probe.txt";[IO.File]::WriteAllText($probe,'private ACL proof',$utf8)
    SetExactAcl $probe $b.observable.state_sddl
    $null=ValidateSnapshot "$Workspace\preflight-snapshot"
    SaveJson "$Workspace\expected-runtime.json" @{server_binary_sha256=$variant.server_binary_sha256;configuration_sha256=$variant.configuration_sha256;model_sha256=$variant.model_artifact_sha256;source_commit=$variant.source_commit;package_sha256=$variant.package_sha256}
    SaveJson "$Workspace\preflight.json" @{status='passed';started_utc=$started.ToString('o');completed_utc=[DateTime]::UtcNow.ToString('o');elapsed_seconds=([DateTime]::UtcNow-$started).TotalSeconds;candidate=$Candidate;release=$Release;document_sha256=$bundleManifest.document_sha256;block_hashes=@($bundleManifest.steps.sha256);published_assets=$assets;client_version=$version;client_binary_sha256=(Hash $binary[0].FullName);client_archive_sha256=(Hash (Join-Path "$Workspace\preflight-work" $manifest.components.omp.artifact_name));model_sha256=$modelSha;exact_acl_restore_probe=$true;baseline=$b.observable}
    Write-Output 'PREFLIGHT_OK';return
}
if($Mode -eq 'Restore'){$r=Restore;$r|ConvertTo-Json -Depth 10;if($r.status -ne 'passed'){exit 1};return}
if($Mode -eq 'Audit'){$r=Audit (ValidateSnapshot $baseline);SaveJson "$Workspace\final-audit.json" $r;$r|ConvertTo-Json -Depth 10;if($r.status -ne 'passed'){exit 1};return}
# One window per workspace. Retain the original failure and always restore before returning it.
if((ReadJson "$Workspace\preflight.json").status -cne 'passed'){throw 'successful preflight required'}
if(Test-Path $journal){throw 'attempt already spent; never repeat acceptance in this workspace'}
if(-not (Test-Path "$Workspace\omp-client-probe.py")){throw 'shared structured probe missing'}
$started=[DateTime]::UtcNow;$b=Snapshot $baseline
$null=ValidateSnapshot $baseline
$state=ReadJson "$StateRoot\state.json";$instance=[string]$state.active_release
$variant=@((ReadJson "$Clone\releases\$Release\manifest.json").components.ninfer_variants|Where-Object id -CEQ 'rtx4090-windows-native')[0]
if($state.releases.$instance.package_sha256 -cne $variant.package_sha256){throw 'active instance is not the candidate published package'}
New-Item -ItemType Directory -Force "$Workspace\preserved","$Workspace\qualified-artifacts"|Out-Null
$prep=[ordered]@{status='preparing';release=$Release;candidate=$Candidate;attempt=$Attempt;started_utc=$started.ToString('o');moves=@();reason='fresh canonical install from preserved differently-bound active instance; not idempotent reinstall';temporary_active=$state.previous_release;temporary_previous=$TemporaryPrevious}
foreach($kind in @('releases','secrets','cache')){$prep.moves+=@{kind=$kind;path="$StateRoot\$kind\$instance";preserved="$Workspace\preserved\$kind"}}
if(Test-Path $Stage){$prep.moves+=@{kind='documented-stage';path=$Stage;preserved="$Workspace\preserved\documented-stage"}}
$failure=$null;$routeExit=$null;$restored=$null;$boundary='preparation';$effect=$false
try {
    AssertBaseline (Probe);SaveJson $journal $prep;$effect=$true
    foreach($m in $prep.moves){Move-Item -LiteralPath $m.path -Destination $m.preserved}
    $state.releases.PSObject.Properties.Remove($instance);$state.active_release=$prep.temporary_active;$state.previous_release=$TemporaryPrevious
    SaveJson "$StateRoot\state.json" $state
    $prep.status='prepared';$prep.temporary_state_sha256=Hash "$StateRoot\state.json";SaveJson $journal $prep
    $boundary='documented-route';$routeExit=Child Route ([Math]::Min(23*60,($WindowMinutes-10)*60))
    $route=ReadJson "$Workspace\route.json"
    if($route.status -cne 'passed' -or @($route.steps).Count -ne 7 -or $routeExit -ne 0){throw 'documented runner failed'}
    foreach($step in $route.steps){if($step.block_sha256 -cne $step.executed_sha256 -or $step.status -notin @('passed','substituted')){throw 'documented block execution mismatch'}}
    $boundary='recovery';Control Status 'recovery-status.json'
    $health=Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 http://127.0.0.1:18082/health
    SaveJson "$Workspace\recovery-health.json" @{status_code=[int]$health.StatusCode;body=[string]$health.Content;utc=[DateTime]::UtcNow.ToString('o')}
    $recovered=ReadJson "$Workspace\recovery-status.json"
    if($recovered.process_state -cne 'running' -or $recovered.endpoint_state -cne 'ready'){throw 'recovery endpoint not ready'}
    $current=ReadJson "$StateRoot\state.json";$installed=$current.releases.$instance
    SaveJson "$Workspace\installed-identity.json" ($installed|Select-Object package_sha256,patch_stack_sha,binary_sha256,config_sha256,model_artifact,model_reference,server_executable)
    if($installed.package_sha256 -cne $variant.package_sha256 -or $installed.config_sha256 -cne $variant.configuration_sha256 -or $installed.binary_sha256 -cne $variant.server_binary_sha256){throw 'installed runtime identity mismatch'}
    # Preserve the four documented inference requests before adding the separate structured probe.
    foreach($file in @(Get-ChildItem $installed.release_root -Filter requests.jsonl -Recurse -File)){Copy-Item $file.FullName "$Workspace\documented-requests.jsonl"}
    $boundary='structured-live';$remaining=[Math]::Floor((($WindowMinutes-10)*60)-([DateTime]::UtcNow-$started).TotalSeconds)
    if($remaining -lt 120){throw 'window reserve reached before live probe'}
    if((Child Live ([Math]::Min(8*60,$remaining))) -ne 0){throw 'structured live probe failed'}
    $boundary='structured-outage';Control Stop 'outage-stop.json'
    if((Child Offline 90) -ne 0){throw 'structured fail-closed probe failed'}
    $boundary='behavior-evidence';$logs=@(Get-ChildItem "$Workspace\route-home\.omp" -File -Recurse|Where-Object {$_.Name -like '*.log' -or $_.Name -like '*.jsonl'})
    New-Item -ItemType Directory -Force "$Workspace\client-logs"|Out-Null
    foreach($f in $logs){$rel=$f.FullName.Substring(("$Workspace\route-home\.omp").Length).TrimStart('\');$dst=Join-Path "$Workspace\client-logs" $rel;New-Item -ItemType Directory -Force (Split-Path $dst -Parent)|Out-Null;Copy-Item $f.FullName $dst}
    $boundary='complete'
} catch {$failure=$_.Exception.Message;SaveJson "$Workspace\window-failure.json" @{boundary=$boundary;error=$failure;utc=[DateTime]::UtcNow.ToString('o')}}
finally {
    if($effect){$restored=Restore}
    else{$restored=Audit $b;SaveJson "$Workspace\restoration.json" $restored}
    SaveJson "$Workspace\window.json" @{status=$(if($failure -or $restored.status -ne 'passed'){'failed'}else{'passed_and_restored'});release=$Release;candidate=$Candidate;attempt=$Attempt;started_utc=$started.ToString('o');completed_utc=[DateTime]::UtcNow.ToString('o');elapsed_seconds=([DateTime]::UtcNow-$started).TotalSeconds;route_exit=$routeExit;first_failing_boundary=$(if($failure){$boundary}else{$null});error=$failure;restoration_status=$restored.status}
}
if($restored.status -ne 'passed'){throw 'restoration audit failed'}
if($failure){throw $failure}
Write-Output 'WINDOW_RESTORED'
