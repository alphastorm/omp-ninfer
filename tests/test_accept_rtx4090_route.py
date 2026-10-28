"""Native route acceptance binds the selected lane and accounts for every documented request."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import documented_route
SPEC = importlib.util.spec_from_file_location("accept_rtx4090_route",
                                              ROOT / "scripts" / "hosts" / "accept-rtx4090-route.py")
assert SPEC is not None and SPEC.loader is not None
DRIVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER)


def completed(*tool_calls: int) -> list[dict]:
    return [{"result": {"tool_call_count": count}} for count in tool_calls]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def served_model_ids(checkout: Path) -> dict[str, str]:
    """Each native lane's served model ID: the model_id of the server config its release variant
    binds. Server-side identities only, never a client provider fragment."""
    release = json.loads((checkout / "compatibility.json").read_text(encoding="utf-8"))["product_release"]
    tree = checkout / "releases" / release
    configurations = {hashlib.sha256(path.read_bytes()).hexdigest(): json.loads(path.read_bytes())["model_id"]
                      for path in (tree / "profiles").glob("*/server-config.json")}
    variants = json.loads((tree / "manifest.json").read_text(encoding="utf-8"))["components"]["ninfer_variants"]
    return {variant["id"].removesuffix("-windows-native"): configurations[variant["configuration_sha256"]]
            for variant in variants}


def renamed_candidate(root: Path) -> Path:
    """A successor candidate that renamed each native model: its native server configs serve, and its
    guide's provider fragments configure, the current ID plus "-next"."""
    clone = root / "candidate"
    tree = Path("releases") / json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))["product_release"]
    for relative in (Path("compatibility.json"), Path("docs/QUICKSTART.md"), tree / "manifest.json"):
        (clone / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / relative, clone / relative)
    shutil.copytree(ROOT / "examples/windows-native", clone / "examples/windows-native")
    for fragment in (clone / "examples/windows-native").glob("*.fragment.yml"):
        fragment.write_text(re.sub(r"(?m)^(      - id: \S+)$", r"\1-next", fragment.read_text(encoding="utf-8")),
                            encoding="utf-8")
    renamed = {}
    for source in (ROOT / tree / "profiles").glob("*/server-config.json"):
        config = json.loads(source.read_bytes())
        config["model_id"] += "-next"
        target = clone / source.relative_to(ROOT)
        write_json(target, config)
        renamed[hashlib.sha256(source.read_bytes()).hexdigest()] = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest = json.loads((clone / tree / "manifest.json").read_text(encoding="utf-8"))
    for variant in manifest["components"]["ninfer_variants"]:
        variant["configuration_sha256"] = renamed[variant["configuration_sha256"]]
    write_json(clone / tree / "manifest.json", manifest)
    return clone


def rtx3090_window(root: Path, model: str) -> dict:
    """The collected evidence of a passing RTX 3090 window, its candidate clone and the documented
    bundle it ran. The bundle's provider step installs the clone's RTX 3090 fragment, whose one model
    is ``model``; every documented request and local client response names it."""
    evidence, clone, bundle = root / "evidence", root / "clone", root / "bundle"
    candidate = "1" * 40
    identity = {"binary_sha256": "a" * 64, "config_sha256": "b" * 64,
                "model_artifact_sha256": "c" * 64, "patch_stack_sha": "d" * 40,
                "source_dirty": False}
    variant = {"id": "rtx3090-windows-native", "server_binary_sha256": "a" * 64,
               "configuration_sha256": "b" * 64, "model_artifact_sha256": "c" * 64,
               "source_commit": "d" * 40, "package_sha256": "e" * 64}
    write_json(clone / "releases/v0.9.1/manifest.json", {"components": {"ninfer_variants": [variant]}})
    fragment = Path("examples/windows-native/models-rtx3090.fragment.yml")
    (clone / fragment).parent.mkdir(parents=True)
    (clone / fragment).write_text(re.sub(r"(?m)^      - id: \S+$", "      - id: " + model,
                                         (ROOT / fragment).read_text(encoding="utf-8")), encoding="utf-8")
    blocks = documented_route.bundle(ROOT / "docs/QUICKSTART.md", "rtx3090-native", bundle)
    steps = [{"slug": step["slug"], "status": "passed", "block_sha256": step["sha256"],
              "executed_sha256": step["sha256"],
              "substitution": candidate if step["slug"] == "clone-and-verify" else None} for step in blocks["steps"]]
    route = {"lane": "rtx3090-native", "status": "passed", "clone_commit": candidate,
             "document_sha256": blocks["document_sha256"], "steps": steps, "completed_utc": "2026-01-01T01:00:00Z"}
    write_json(evidence / "route.json", route)
    write_json(evidence / "recovery-health.json", {"status_code": 200})
    write_json(evidence / "recovery-status.json", {"process_state": "running", "endpoint_state": "ready",
                                                   "server": {"status": "ok", "identity": identity}})
    write_json(evidence / "installed-identity.json", {"package_sha256": "e" * 64})
    for name in ("restoration", "final-audit"):
        write_json(evidence / f"{name}.json", {"status": "passed"})
    live = {"typed_read_tool_calls": 1, "linked_tool_results": 1,
            **{key: True for key in ("tool_result_marker", "exact_visible_final_answer", "agent_end",
                                     "continuation_exact_nonce", "runtime_identity_bound")},
            "fail_closed": {"exit_code": 1, "no_model_response": True, "only_selected_local_provider_observed": True}}
    write_json(evidence / "structured/receipt.json", {"status": "passed", "live_acceptance": live})
    (evidence / "route.stdout.log").write_text("OMP_NINFER_TOOL_OK\n493817-205361\n")
    requests = [{"event": "request_done", "request": {"request_id": str(i), "model": model,
                 "has_tool_history": i == 1}, "result": {"tool_call_count": int(i == 0)}} for i in range(4)]
    (evidence / "documented-requests.jsonl").write_text("\n".join(map(json.dumps, requests)))
    logs = [{"timestamp": "2026-01-01T00:00:00Z", "provider": "ninfer-native-3090", "model": model,
             "message": "agent_end maintenance routing", "stopReason": "error", "contentBlocks": 0,
             "hasText": False, "hasToolCalls": False},
            {"timestamp": "2026-01-01T00:00:00Z", "message": "agent turn ended with provider error"}]
    (evidence / "route-client-logs").mkdir()
    (evidence / "route-client-logs/client.log").write_text("\n".join(map(json.dumps, logs)))
    return {"evidence": evidence, "clone": clone, "bundle": bundle, "variant": variant, "route": route,
            "requests": requests}


class RequestShapeTests(unittest.TestCase):
    def test_extra_tool_calls_pass_and_unexplained_requests_fail(self) -> None:
        """v0.8.6's second RTX 4090 run made two tool calls: five requests and a passing documented
        route, which the driver refused as not exactly one call. A request that no tool call
        explains is a hidden retry or a duplicate and still fails."""
        cases = {
            (1, 0, 0, 0): True,      # read, answer, nonce plant, nonce recall
            (1, 1, 0, 0, 0): True,   # glob, then read
            (1, 0, 0, 0, 0): False,  # one request too many
            (1, 0, 0): False,        # one request missing
            (0, 0, 0): False,        # no tool call
        }
        for calls, passed in cases.items():
            with self.subTest(calls=calls):
                self.assertEqual(all(DRIVER.request_shape(completed(*calls)).values()), passed)


class NativeLaneTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for the native baseline contract")
    def test_powershell_baseline_enforces_lane_power_and_operator_holds(self) -> None:
        # Execute the production declarations/functions, stopping before any host operation.
        # C: is a temporary filesystem drive; no ScheduledTask, GPU or network call runs.
        proof = r'''
param($Source, $Scratch)
$ErrorActionPreference='Stop'
New-PSDrive -Name C -PSProvider FileSystem -Root $Scratch | Out-Null
$text=[IO.File]::ReadAllText($Source)
$tokens=$null;$errors=$null
$null=[Management.Automation.Language.Parser]::ParseInput($text,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
$definitions=$text.Substring(0,$text.IndexOf('# Child isolation happens'))
New-Item -ItemType Directory -Force C:/window|Out-Null
Copy-Item (Join-Path (Split-Path $Source) 'native-gpu.ps1') C:/window/native-gpu.ps1
$assertions=@'
$p=@{state_sha256=$ExpectedStateSha256;prepared_release=$null;task_state='Ready';processes=@();listeners=@();lease_present=$false;lease_entries=@();power_limit_w=$ownerPowerLimit}
New-Item -ItemType Directory -Force $StateRoot|Out-Null
@{active_release='active';previous_release='previous';prepared_release=$null;releases=@{older=@{}}}|ConvertTo-Json -Depth 5|Set-Content "$StateRoot/state.json"
if(@($RequiredHoldPaths).Count) {
  $rejected=$false;try{AssertBaseline $p}catch{$rejected=$true}
  if(-not $rejected){throw 'accepted missing operator-required holds'}
  foreach($hold in $RequiredHoldPaths){
    New-Item -ItemType Directory -Force (Split-Path $hold)|Out-Null
    New-Item -ItemType File -Force $hold|Out-Null
  }
}
AssertBaseline $p
if(Test-Path $HostState){throw 'baseline created appliance state'}
function Start-Process {
  param($FilePath,$ArgumentList,[switch]$PassThru,$RedirectStandardOutput,$RedirectStandardError)
  $script:childCommand=[Text.Encoding]::Unicode.GetString([Convert]::FromBase64String($ArgumentList[-1]))
  $process=[pscustomobject]@{Handle=1;ExitCode=0}
  $process|Add-Member ScriptMethod WaitForExit {param($milliseconds) if($null -ne $milliseconds){$true}}
  $process|Add-Member ScriptMethod Refresh {}
  return $process
}
if((Child Route 1) -ne 0){throw 'child argument transport failed'}
$expected='-RequiredHoldPaths @('+((@($RequiredHoldPaths|ForEach-Object {Quote $_})) -join ',')+')'
if(-not $script:childCommand.Contains($expected)){throw 'child lost the operator hold array'}
function Resolve-NativeGpuUuid {param($root) 'fixture-card'}
function Get-NativeGpuPowerLimit {param($uuid) $ownerPowerLimit}
function Get-ScheduledTask {param($TaskName) @{State='Ready'}}
function Get-Acl {param($Path,$LiteralPath) @{Sddl='fixture-acl'}}
function Get-CimInstance {param($ClassName,$Filter) @()}
function Get-NetTCPConnection {param($State,$ErrorAction) @()}
New-Item -ItemType Directory -Force "$realClient/local-other-supervisor"|Out-Null
New-Item -ItemType File -Force "$realClient/local-other-supervisor/paused"|Out-Null
$probe=Probe
if(@($probe.lease_entries).Count){throw 'absent owner-state directory is not an empty lease census'}
if(@($probe.holds|Where-Object path -Like '*local-other-supervisor*').Count -ne 1){throw 'existing unrelated supervisor hold was not audited'}
$FirstRelease=$true;$TemporaryPrevious=''
@{active_release='active';previous_release='';releases=@{active=@{}}}|ConvertTo-Json -Depth 5|Set-Content "$StateRoot/state.json"
AssertBaseline $p
foreach($bad in @(@{active_release='active';previous_release='old';releases=@{active=@{}}},
                 @{active_release='active';previous_release='';releases=@{active=@{};old=@{}}})) {
  $bad|ConvertTo-Json -Depth 5|Set-Content "$StateRoot/state.json"
  $rejected=$false;try{AssertBaseline $p}catch{$rejected=$true}
  if(-not $rejected){throw 'first release accepted a retained predecessor'}
}
$FirstRelease=$false;$TemporaryPrevious='older'
@{active_release='active';previous_release='previous';releases=@{older=@{}}}|ConvertTo-Json -Depth 5|Set-Content "$StateRoot/state.json"
$p.power_limit_w=if($Lane -eq 'rtx3090'){450}else{370}
$rejected=$false;try{AssertBaseline $p}catch{$rejected=$true}
if(-not $rejected){throw 'other lane power limit was accepted'}
@{lane=$Lane;root=$StateRoot;task=$TaskName;power=$ownerPowerLimit}
'@
$results=@(foreach($lane in @('rtx3090','rtx4090')) {
  & ([scriptblock]::Create($definitions+$assertions)) -Lane $lane -Release v0.9.1 -Candidate ('1'*40) -Workspace C:/window -Bundle C:/bundle -Clone C:/clone -ExpectedStateSha256 ('2'*64) -TemporaryPrevious older -RealHome C:/home
  $holds=@("C:/operator/$lane-first-hold","C:/operator/$lane-owner's-hold")
  & ([scriptblock]::Create($definitions+$assertions)) -Lane $lane -Release v0.9.1 -Candidate ('1'*40) -Workspace C:/window -Bundle C:/bundle -Clone C:/clone -ExpectedStateSha256 ('2'*64) -TemporaryPrevious older -RealHome C:/home -RequiredHoldPaths $holds
})
$results|ConvertTo-Json -Compress
'''
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "baseline.ps1"
            script.write_text(proof)
            result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(script),
                                     str(ROOT / "scripts/hosts/accept-rtx4090-route.ps1"), directory],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            rows = {row["lane"]: row for row in json.loads(result.stdout)}
            self.assertEqual(rows["rtx3090"]["power"], 370)
            self.assertEqual(rows["rtx3090"]["task"], "NInfer-Qwen38-3090-Native")
            self.assertTrue(rows["rtx3090"]["root"].endswith("qwen38-3090-native"))
            self.assertEqual(rows["rtx4090"]["power"], 450)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for directory preservation")
    def test_optional_native_directories_preserve_presence_in_both_lineage_modes(self) -> None:
        # Execute the production AST directory statements. Host calls are fixtures; the
        # support enumerator supplies Windows FullNames on the temporary C: provider drive.
        proof = r'''
param($Source,$Scratch)
$ErrorActionPreference='Stop'
New-PSDrive -Name C -PSProvider FileSystem -Root $Scratch|Out-Null
$text=[IO.File]::ReadAllText($Source);$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseInput($text,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
$definitions=$text.Substring(0,$text.IndexOf('# Child isolation happens'))
New-Item -ItemType Directory -Force C:/window|Out-Null
Copy-Item (Join-Path (Split-Path $Source) 'native-gpu.ps1') C:/window/native-gpu.ps1
function Statements($Name,$Predicate) {
    $function=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $Name},$false)
    (($function.Body.EndBlock.Statements|Where-Object $Predicate|ForEach-Object {$_.Extent.Text}) -join "`n")
}
$snapshot=Statements Snapshot {$_ -is [Management.Automation.Language.ForEachStatementAst] -and $_.Variable.VariablePath.UserPath -in @('dir','sub','kind')}
$snapshot='$files=@();$directories=@();'+$snapshot
$snapshot+="`n"+(Statements Snapshot {$_ -is [Management.Automation.Language.PipelineAst] -and $_.Extent.Text.StartsWith('SaveJson ')})
$restoration=Statements Restore {$_ -is [Management.Automation.Language.ForEachStatementAst] -and $_.Variable.VariablePath.UserPath -in @('m','d')}
$audit=Statements Audit {$_ -is [Management.Automation.Language.ForEachStatementAst] -and $_.Variable.VariablePath.UserPath -eq 'd'}
$prepare=$text.Substring($text.IndexOf('$prep=[ordered]'),$text.IndexOf('$failure=$null;$routeExit=')-$text.IndexOf('$prep=[ordered]'))
$begin=$ast.Find({param($node) $node -is [Management.Automation.Language.TryStatementAst] -and $node.Body.Extent.Text.Contains('AssertBaseline (Probe);SaveJson $journal $prep')},$false)
$beginDirectories=(($begin.Body.Statements|Where-Object {
    ($_ -is [Management.Automation.Language.ForEachStatementAst] -and $_.Variable.VariablePath.UserPath -eq 'm') -or
    ($_.Extent.Text -match '^New-Item .*\$Stage')
}|ForEach-Object {$_.Extent.Text}) -join "`n")
$assertions=@'
function Get-Acl {param($Path,$LiteralPath)
    $p=if($LiteralPath){$LiteralPath}else{$Path}
    if(-not (Test-Path -LiteralPath $p)){throw "ACL queried for absent path: $p"}
    @{Sddl='fixture-acl'}
}
function SetExactAcl($path,$sddl) {
    if(-not (Test-Path -LiteralPath $path)){throw "ACL restored onto absent path: $path"}
}
function SupportDirectories {
    @{FullName=$StateRoot}
    foreach($sub in @('gpu-owner','gpu-owner-state','receipts','releases','secrets','cache')) {
        if(Test-Path "$StateRoot\$sub"){@{FullName="$StateRoot\$sub"}}
    }
}
function SaveJson($path,$value){$script:savedSnapshot=$value}
$instance='active';$state=[pscustomobject]@{active_release=$instance;previous_release=$(if($FirstRelease){$null}else{'previous'})}
New-Item -ItemType Directory -Force $StateRoot,"$StateRoot\releases\$instance","$StateRoot\secrets\$instance","$Workspace\preserved","$Workspace\qualified-artifacts"|Out-Null
Set-Content "$StateRoot\releases\$instance\original.txt" 'qualified bytes'
if($StageWasPresent){New-Item -ItemType Directory -Force $Stage|Out-Null;Set-Content "$Stage\original.txt" 'original stage'}
$observable=@{};$files=@();$directories=@();$destination='C:/unused'
& ([scriptblock]::Create($snapshot))
$b=$script:savedSnapshot
foreach($relative in @('gpu-owner','gpu-owner-state','receipts','cache','cache\active')) {
    $d=@($b.directories|Where-Object relative -EQ $relative)
    if($d.Count -ne 1 -or $d[0].exists -ne $false){throw "missing absence snapshot: $relative"}
}
if($b.documented_stage.exists -ne $StageWasPresent){throw 'stage presence not snapshotted'}
$started=[DateTime]::UtcNow
Invoke-Expression $prepare
$stageMove=@($prep.moves|Where-Object kind -EQ 'documented-stage')
if($stageMove.Count -ne 1 -or $stageMove[0].exists -ne $StageWasPresent){throw 'stage absence not journaled'}
if(-not $FirstRelease -and @($prep.moves|Where-Object {$_.kind -eq 'cache' -and -not $_.exists}).Count -ne 1){throw 'absent cache was not journaled'}
Invoke-Expression $beginDirectories
if(-not (Test-Path $Stage)){throw 'window stage not created at begin'}
New-Item -ItemType Directory -Force $StateRoot,"$StateRoot\cache\$instance","$StateRoot\gpu-owner-state","$StateRoot\receipts"|Out-Null
Set-Content "$Stage\window.txt" 'private window state'
Invoke-Expression $restoration
if((Test-Path $Stage) -ne $StageWasPresent){throw 'original stage presence not restored'}
if($StageWasPresent -and (Get-Content "$Stage\original.txt") -ne 'original stage'){throw 'original stage content lost'}
if(-not (Test-Path "$Workspace\qualified-artifacts\documented-stage\window.txt")){throw 'window artifacts not retained privately'}
if((Get-Content "$StateRoot\releases\$instance\original.txt") -ne 'qualified bytes'){throw 'qualified lineage not restored'}
$checks=@{directory_presence_identical=$true;directory_acls_identical=$true}
Invoke-Expression $audit
if(-not $checks.directory_presence_identical -or -not $checks.directory_acls_identical){throw 'directory restoration audit failed'}
@{lane=$Lane;first_release=[bool]$FirstRelease;stage_was_present=$StageWasPresent;passed=$true}
'@
$results=@(foreach($lane in @('rtx3090','rtx4090')) {
    foreach($first in @($false,$true)) {
        foreach($StageWasPresent in @($false,$true)) {
            $case="$lane-$first-$StageWasPresent"
            $root="C:\qualified-$case";$stage="C:\stage-$case"
            try {
                $lineage=@{FirstRelease=$first}
                if(-not $first){$lineage.TemporaryPrevious='older'}
                & ([scriptblock]::Create($definitions+$assertions)) -Lane $lane -Release v0.12.0 -Candidate ('1'*40) -Workspace C:/window -Bundle C:/bundle -Clone C:/clone -ExpectedStateSha256 ('2'*64) -StateRoot $root -Stage $stage -RealHome C:/home @lineage
            } catch {throw "$case`: $($_.Exception.Message)`n$($_.ScriptStackTrace)"}
            Remove-Item C:/window/preserved,C:/window/qualified-artifacts -Recurse -Force
        }
    }
})
$results|ConvertTo-Json -Compress
'''
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "directories.ps1"
            script.write_text(proof)
            result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(script),
                                     str(ROOT / "scripts/hosts/accept-rtx4090-route.ps1"), directory],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            rows = json.loads(result.stdout)
            self.assertEqual(len(rows), 8)
            self.assertTrue(all(row["passed"] for row in rows))

    def test_first_release_mode_is_explicit_exclusive_and_offline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "not-created"
            command = [sys.executable, str(ROOT / "scripts/hosts/accept-rtx4090-route.py"),
                       "--release", "v0.12.0", "--candidate", "1" * 40, "--host", "fixture-host",
                       "--workspace", str(workspace), "--remote-workspace", "C:/acceptance",
                       "--expected-state-sha256", "2" * 64, "--mode", "dry-run"]
            first = subprocess.run(command + ["--first-release"], capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(json.loads(first.stdout)["plan"]["lineage_mode"], "first_release")
            self.assertFalse(workspace.exists())
            for args in ([], ["--first-release", "--temporary-previous", "older"]):
                self.assertEqual(subprocess.run(command + args, capture_output=True, text=True).returncode, 2)

    def test_first_release_preserves_real_state_not_an_invalid_empty_record(self) -> None:
        source = (ROOT / "scripts/hosts/accept-rtx4090-route.ps1").read_text()
        self.assertIn("first release requires exactly one active release and no predecessor", source)
        self.assertIn("kind='lineage-root';path=$StateRoot", source)
        self.assertIn("if($FirstRelease){Unregister-ScheduledTask", source)
        self.assertIn("if(-not $FirstRelease) {\n        $state.releases", source)
        self.assertIn("elseif(-not $FirstRelease){throw 'restoration requires an active lifecycle record'}", source)
        install = (ROOT / "scripts/hosts/accept-native-public-install.ps1").read_text()
        self.assertIn("reason='first release of the lineage'", install)
        self.assertIn("status='not_applicable'; directions=0", install)
        self.assertIn("public-install acceptance is not a rollback test", install)

    def test_dry_run_requires_an_operator_host_for_both_lanes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "not-created"
            command = [sys.executable, str(ROOT / "scripts/hosts/accept-rtx4090-route.py"),
                       "--release", "v0.9.1", "--candidate", "1" * 40, "--workspace", str(workspace),
                       "--remote-workspace", "C:/acceptance", "--expected-state-sha256", "2" * 64,
                       "--temporary-previous", "previous", "--mode", "dry-run"]
            default = subprocess.run(command + ["--host", "fixture-host"], capture_output=True, text=True)
            explicit = subprocess.run(command + ["--lane", "rtx4090", "--host", "fixture-host"], capture_output=True, text=True)
            self.assertEqual(default.returncode, 0, default.stderr)
            self.assertEqual(default.stdout, explicit.stdout)
            for lane in ("rtx3090", "rtx4090"):
                missing_host = subprocess.run(command + ["--lane", lane], capture_output=True, text=True)
                self.assertEqual(missing_host.returncode, 2, lane)
            selected = subprocess.run(command + ["--lane", "rtx3090", "--host", "fixture-host"],
                                      capture_output=True, text=True)
            self.assertEqual(selected.returncode, 0, selected.stderr)
            self.assertEqual(json.loads(selected.stdout)["plan"]["client_install"]["lane"], "rtx3090-native")
            self.assertFalse(workspace.exists())
            unknown = subprocess.run(command + ["--lane", "rtx5090"], capture_output=True, text=True)
            self.assertEqual(unknown.returncode, 2)

    def test_required_holds_are_repeatable_explicit_and_offline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "not-created"
            command = [sys.executable, str(ROOT / "scripts/hosts/accept-rtx4090-route.py"),
                       "--release", "v0.12.0", "--candidate", "1" * 40, "--host", "fixture-host",
                       "--workspace", str(workspace), "--remote-workspace", "C:/acceptance",
                       "--expected-state-sha256", "2" * 64, "--first-release", "--mode", "dry-run"]
            for lane in ("rtx3090", "rtx4090"):
                for holds in ([], ["C:/operator/first-hold", "C:/operator/owner's-hold"]):
                    args = [argument for hold in holds for argument in ("--require-hold", hold)]
                    result = subprocess.run(command + ["--lane", lane] + args, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout)["plan"]["required_hold_paths"], holds)
                    self.assertFalse(workspace.exists())

    def test_required_hold_array_reaches_the_powershell_driver(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            command = ["accept-rtx4090-route.py", "--release", "v0.12.0", "--candidate", "1" * 40,
                       "--host", "fixture-host", "--workspace", directory, "--remote-workspace", "C:/acceptance",
                       "--expected-state-sha256", "2" * 64, "--first-release", "--mode", "restore",
                       "--require-hold", "C:/operator/first-hold", "--require-hold", "C:/operator/owner's-hold"]
            completed_process = subprocess.CompletedProcess([], 0, "", "")
            with mock.patch.object(sys, "argv", command), \
                    mock.patch.object(DRIVER, "ssh", return_value=completed_process) as ssh, \
                    mock.patch.object(DRIVER, "run", return_value=completed_process):
                try:
                    self.assertEqual(DRIVER.main(), 0)
                except SystemExit as error:
                    self.fail(f"operator holds were refused by the argument parser: {error}")
            self.assertIn("-RequiredHoldPaths @('C:/operator/first-hold','C:/operator/owner''s-hold')",
                          ssh.call_args_list[0].args[1])

    def test_native_host_contract_is_not_derived_from_the_lane(self) -> None:
        source = (ROOT / "scripts/hosts/accept-rtx4090-route.ps1").read_text()
        parameters = source[:source.index("Set-StrictMode")]
        self.assertIn("[string[]]$RequiredHoldPaths=@()", parameters)
        self.assertNotIn("$RequiredHoldPaths=", source[source.index("Set-StrictMode"):])
        self.assertNotIn("local-$gpu-supervisor", source)
        self.assertIn("-Filter 'local-*-supervisor'", source)
        for other_host_port in ("18088", "18089", "18099"):
            self.assertNotIn(other_host_port, source)
        self.assertIn("-RequiredHoldPaths @(", source)
        public = (ROOT / "scripts/hosts/accept-native-public-install.ps1").read_text()
        self.assertIn('$base = "http://$($rel.host):$($rel.port)"', public)
        self.assertNotIn("container-host-paused", public)

    def test_driver_model_default_is_the_file_the_documented_route_creates(self) -> None:
        source = (ROOT / "scripts/hosts/accept-rtx4090-route.ps1").read_text()
        default = re.search(r"\[string\]\$Model='([^']+)'", source).group(1)
        spec = importlib.util.spec_from_file_location("model_route", ROOT / "scripts/documented_route.py")
        route = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = route
        spec.loader.exec_module(route)
        for lane in ("rtx4090-native", "rtx3090-native"):
            text = "\n".join(block.text for _, block in route.lane_blocks(ROOT / "docs/QUICKSTART.md", lane))
            directory = re.search(r"^\$ModelDir = Join-Path \$env:ProgramData '([^']+)'$", text, re.M).group(1)
            name = re.search(r"^\$Model = Join-Path \$ModelDir '([^']+)'$", text, re.M).group(1)
            self.assertEqual(default, "C:\\ProgramData\\" + directory + "\\" + name, lane)

    def test_assessor_binds_3090_model_route_and_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            window = rtx3090_window(Path(directory), "q38-ninfer")
            evidence, clone, bundle, variant = (window[key] for key in ("evidence", "clone", "bundle", "variant"))
            candidate = "1" * 40
            result = DRIVER.assess_evidence(evidence, clone, bundle, "v0.9.1", candidate, "rtx3090")
            self.assertEqual(result["status"], "passed", result["checks"])
            variant["qualification"] = {"summary": "qualification/first.json"}
            write_json(clone / "releases/v0.9.1/manifest.json", {"components": {"ninfer_variants": [variant]}})
            write_json(clone / "releases/v0.9.1/qualification/first.json", {"rollback": {"status": "not_applicable",
                "directions": 0, "reason": "first release of the lineage"}})
            preparation = {"lineage_mode": "first_release", "previous_release_present": False,
                           "temporary_active": None, "temporary_previous": ""}
            write_json(evidence / "preparation.json", preparation)
            result = DRIVER.assess_evidence(evidence, clone, bundle, "v0.9.1", candidate, "rtx3090")
            self.assertEqual(result["status"], "passed", result["checks"])
            preparation["temporary_previous"] = "unsupported"
            write_json(evidence / "preparation.json", preparation)
            result = DRIVER.assess_evidence(evidence, clone, bundle, "v0.9.1", candidate, "rtx3090")
            self.assertFalse(result["checks"]["first_release_preparation_has_no_predecessor"])
            del variant["qualification"]
            write_json(clone / "releases/v0.9.1/manifest.json", {"components": {"ninfer_variants": [variant]}})
            route, requests = window["route"], window["requests"]
            route["lane"] = "rtx4090-native"
            write_json(evidence / "route.json", route)
            requests[0]["request"]["model"] = "qwen3.8-27b"
            (evidence / "documented-requests.jsonl").write_text("\n".join(map(json.dumps, requests)))
            write_json(evidence / "installed-identity.json", {"package_sha256": "9" * 64})
            result = DRIVER.assess_evidence(evidence, clone, bundle, "v0.9.1", candidate, "rtx3090")
            self.assertEqual(result["status"], "failed")
            self.assertFalse(result["checks"]["runner_passed"])
            self.assertFalse(result["checks"]["only_expected_server_model"])
            self.assertFalse(result["checks"]["installed_package_bound"])


class DocumentedModelTests(unittest.TestCase):
    """The route asks for the model its candidate's documented provider step configures, which is the
    model that candidate's native server serves. It keeps no lane table of its own (omp-ninfer#98):
    the scripts run from the operator's checkout against a frozen candidate."""

    LIVE = r'''
param($Source,$Workspace,$Bundle,$Clone,$Lane)
$ErrorActionPreference='Stop'
# py records the structured probe's arguments instead of running it; the Live phase exits with it.
function py {[Console]::Out.WriteLine((ConvertTo-Json -Compress @($args)));$global:LASTEXITCODE=0}
New-Item -ItemType File -Force (Join-Path $Workspace 'route-home\AppData\Local\OMP\omp.exe')|Out-Null
& ([scriptblock]::Create([IO.File]::ReadAllText($Source))) -Mode Live -Lane $Lane -Release v0.14.0 -Candidate ('1'*40) -Workspace $Workspace -Bundle $Bundle -Clone $Clone -ExpectedStateSha256 ('2'*64) -TemporaryPrevious older -StateRoot (Join-Path $Workspace 'state') -KeyFile (Join-Path $Workspace 'key.txt') -RealHome (Join-Path $Workspace 'home')
'''

    def live_model(self, lane: str, clone: Path) -> str:
        """The --model of the Live phase's structured probe against ``clone`` and the bundle of its
        documented route: the model the window asks the candidate's server for."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace, bundle = root / "window", root / "bundle"
            workspace.mkdir()
            shutil.copy(ROOT / "scripts/hosts/native-gpu.ps1", workspace)
            (workspace / "key.txt").write_text("synthetic-test-key\n")
            documented_route.bundle(clone / "docs/QUICKSTART.md", f"{lane}-native", bundle)
            (root / "live.ps1").write_text(self.LIVE)
            result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(root / "live.ps1"),
                                     str(ROOT / "scripts/hosts/accept-rtx4090-route.ps1"), str(workspace),
                                     str(bundle), str(clone), lane], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        probe = json.loads(result.stdout)
        return probe[probe.index("--model") + 1]

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed to run the route's live phase")
    def test_each_lane_asks_for_the_model_its_server_serves(self) -> None:
        served = served_model_ids(ROOT)
        self.assertEqual(sorted(served), ["rtx3090", "rtx4090"])
        for lane, model in served.items():
            with self.subTest(lane=lane):
                self.assertEqual(self.live_model(lane, ROOT), f"ninfer-native-{lane[3:]}/{model}")

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed to run the route's live phase")
    def test_a_candidate_that_renames_its_models_is_asked_for_the_new_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            clone = renamed_candidate(Path(directory))
            for lane, model in served_model_ids(clone).items():
                with self.subTest(lane=lane):
                    self.assertTrue(model.endswith("-next"))
                    self.assertEqual(self.live_model(lane, clone), f"ninfer-native-{lane[3:]}/{model}")

    def test_revalidation_probes_the_model_the_candidate_serves(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            clone, bundle, workspace = renamed_candidate(root), root / "bundle", root / "workspace"
            documented_route.bundle(clone / "docs/QUICKSTART.md", "rtx3090-native", bundle)
            write_json(workspace / "driver-preflight.json",
                       {"plan": {"candidate": "1" * 40, "client_install": {"lane": "rtx3090-native"}}})
            command = ["accept-rtx4090-route.py", "--lane", "rtx3090", "--release", "v0.14.0",
                       "--candidate", "1" * 40, "--host", "fixture-host", "--workspace", str(workspace),
                       "--remote-workspace", "C:/acceptance", "--clone", str(clone), "--bundle", str(bundle),
                       "--expected-state-sha256", "2" * 64, "--temporary-previous", "older", "--mode", "validate"]
            completed_process = subprocess.CompletedProcess([], 0, "", "")
            with mock.patch.object(sys, "argv", command), \
                    mock.patch.object(DRIVER, "ssh", return_value=completed_process) as ssh, \
                    mock.patch.object(DRIVER, "run", return_value=completed_process), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(DRIVER.main(), 0)
            model = served_model_ids(clone)["rtx3090"]
        self.assertIn("--model " + DRIVER.quote(f"ninfer-native-3090/{model}"), ssh.call_args_list[0].args[1])

    def test_assessor_expects_the_model_the_candidate_documents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            window = rtx3090_window(Path(directory), "q38-ninfer-next")
            def assess() -> dict:
                return DRIVER.assess_evidence(window["evidence"], window["clone"], window["bundle"], "v0.9.1",
                                              "1" * 40, "rtx3090")
            result = assess()
            self.assertEqual(result["status"], "passed", result["checks"])
            for row in window["requests"]:
                row["request"]["model"] = "q38-ninfer"
            (window["evidence"] / "documented-requests.jsonl").write_text("\n".join(map(json.dumps, window["requests"])))
            self.assertFalse(assess()["checks"]["only_expected_server_model"])


if __name__ == "__main__":
    unittest.main()
