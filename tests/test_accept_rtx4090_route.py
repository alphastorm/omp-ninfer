"""Native route acceptance binds the selected lane and accounts for every documented request."""

from __future__ import annotations

import ast
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
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
    (evidence / "server-requests.jsonl").write_text("\n".join(map(json.dumps, requests)))
    (evidence / "server-stderr.log").write_text("synthetic server ready\n")
    write_json(evidence / "shutdown.json", {"artifact_type": "ninfer_serve_shutdown_report",
               "schema_version": 1, "complete": True, "saved": 1, "refused": 0, "skipped": 0})
    write_json(evidence / "window.json", {"status": "passed_and_restored",
               "first_failing_boundary": None, "restoration_status": "passed"})
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
    def test_assessor_retains_observed_subject_instead_of_relabelling_from_cli(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            window = rtx3090_window(Path(directory), "q38-ninfer")
            observed = {"candidate_commit": "2" * 40, "release": "v0.18.0",
                        "client": {"version": "omp/18.18.7", "binary_sha256": "f" * 64},
                        "installed": {"source_commit": "d" * 40, "package_sha256": "e" * 64,
                                      "binary_sha256": "a" * 64, "config_sha256": "b" * 64}}
            write_json(window["evidence"] / "route.json", {**window["route"], **observed})
            result = DRIVER.assess_evidence(
                window["evidence"], window["clone"], window["bundle"], "v0.9.1", "1" * 40,
                "rtx3090")
            for field, expected in observed.items():
                self.assertEqual(result[field], expected)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for native observed identities")
    def test_route_observes_executed_clone_client_and_installed_record_and_preserves_exit(self):
        proof = r'''
param($Source,$Scratch,$ExitCode)
$ErrorActionPreference='Stop'
$text=[IO.File]::ReadAllText($Source)
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseInput($text,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
foreach($name in @('Hash','ReadJson','SaveJson')){
    $node=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name},$true)
    Invoke-Expression $node.Extent.Text
}
$utf8=[Text.UTF8Encoding]::new($false)
function SetIsolation {param($Name)}
function observed-client {$global:LASTEXITCODE=0;'omp/18.18.7'}
function Join-Path {
    param($Path,$ChildPath)
    if($ChildPath -ceq 'OMP\omp.exe'){return 'observed-client'}
    Microsoft.PowerShell.Management\Join-Path $Path $ChildPath
}
$Workspace=Join-Path $Scratch 'window';$StateRoot=Join-Path $Scratch 'installed'
$Release='v0.18.0';$Candidate='1'*40;$Bundle='unused'
$env:LOCALAPPDATA='unused';$runner=Join-Path $Scratch 'runner.ps1'
$node=$ast.Find({param($n) $n -is [Management.Automation.Language.IfStatementAst] -and
    $n.Clauses[0].Item1.Extent.Text -ceq "`$Mode -eq 'Route'"},$true)
$body=$node.Clauses[0].Item2.Extent.Text
$env:FIXTURE_EXECUTED_CLONE=Join-Path $Scratch 'executed'
$env:FIXTURE_ROUTE_EXIT=$ExitCode
Invoke-Expression $body.Substring(1,$body.Length-2)
'''
        for original_exit in (0, 23):
            with self.subTest(original_exit=original_exit), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                clone = root / "executed"
                write_json(clone / "releases/v0.18.0/manifest.json", {"release": "v0.18.0"})
                binary = clone / "observed-client"
                binary.write_bytes(b"observed stock client bytes")
                for command in (["init", "-q"], ["add", "."],
                                ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                                 "commit", "-qm", "test: freeze executed route"]):
                    subprocess.run(["git", "-C", str(clone), *command], check=True, capture_output=True)
                candidate = subprocess.check_output(["git", "-C", str(clone), "rev-parse", "HEAD"],
                                                    text=True, encoding="utf-8").strip()
                installed = {"patch_stack_sha": "a" * 40, "package_sha256": "b" * 64,
                             "binary_sha256": "c" * 64, "config_sha256": "d" * 64}
                write_json(root / "installed/state.json", {
                    "active_release": "actual", "releases": {"actual": installed}})
                (root / "window").mkdir()
                (root / "runner.ps1").write_text(r'''
param($Bundle,$WorkDir,$Receipt,$CloneOverride)
Set-Location $env:FIXTURE_EXECUTED_CLONE
@{clone_commit=((& git rev-parse HEAD|Out-String).Trim());status='passed'}|ConvertTo-Json|Set-Content -LiteralPath $Receipt -Encoding UTF8
$global:LASTEXITCODE=[int]$env:FIXTURE_ROUTE_EXIT
''', encoding="utf-8")
                script = root / "proof.ps1"
                script.write_text(proof, encoding="utf-8")
                result = subprocess.run(
                    [shutil.which("pwsh"), "-NoProfile", "-File", str(script),
                     str(ROOT / "scripts/hosts/accept-rtx4090-route.ps1"), directory, str(original_exit)],
                    capture_output=True, text=True, encoding="utf-8", timeout=30)
                self.assertEqual(result.returncode, original_exit, result.stdout + result.stderr)
                # .NET file APIs use Windows backslashes literally on the Unix test host.
                receipt = json.loads(Path(str(root / "window") + "\\route.json").read_text(encoding="utf-8"))
                self.assertEqual(receipt["clone_commit"], candidate)
                self.assertIn("candidate_commit", receipt, result.stdout + result.stderr)
                self.assertEqual(receipt["candidate_commit"], candidate)
                self.assertEqual(receipt["release"], "v0.18.0")
                self.assertEqual(receipt["client"], {"version": "omp/18.18.7",
                    "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest()})
                self.assertEqual(receipt["installed"], {
                    "source_commit": installed["patch_stack_sha"],
                    **{key: installed[key] for key in ("package_sha256", "binary_sha256", "config_sha256")}})

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for fail-closed parameter binding")
    def test_private_paths_are_explicit_required_launcher_and_install_inputs(self):
        scripts = {
            "accept-native-public-install.ps1": {
                "Lane": "rtx4090", "ManifestPath": "unused", "ExpectedSums": "unused",
                "StateRoot": "unused", "Workspace": "unused", "ReceiptPath": "unused",
                "CandidateClone": "unused", "ClientBinary": "unused"},
            "run_variant_campaign_5090.ps1": {
                "CampaignRoot": "/operator/window", "GroupwiseIntModel": "/operator/int.ninfer",
                "Nvfp4Model": "/operator/nvfp4.ninfer", "ApiKeyFile": "/operator/key"},
        }
        for name, parameters in scripts.items():
            source = ROOT / "scripts/hosts" / name
            declarations = source.read_text(encoding="utf-8").split("Set-StrictMode")[0]
            required = ("CandidateClone", "ClientBinary") if name.startswith("accept-") else tuple(parameters)
            for parameter in required:
                with self.subTest(script=name, missing=parameter):
                    self.assertRegex(declarations, r"\[Parameter\(Mandatory\s*=\s*\$true\)\]"
                                     r"[^\n]*\$" + parameter + r"\b")
                    arguments = [argument for key, value in parameters.items() if key != parameter
                                 for argument in ("-" + key, value)]
                    result = subprocess.run(
                        [shutil.which("pwsh"), "-NoProfile", "-NonInteractive", "-File", str(source),
                         *arguments], capture_output=True, text=True, encoding="utf-8", timeout=30)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(parameter, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for required native model paths")
    def test_native_campaign_model_paths_refuse_absence_and_missing_files_before_effects(self):
        for lane in ("3090", "4090"):
            source = ROOT / "scripts/hosts" / f"run_variant_campaign_{lane}.ps1"
            declarations = source.read_text(encoding="utf-8").split("# RTX")[0]
            self.assertIn("[Parameter(Mandatory=$true)]", declarations)
            self.assertIn("[string]$GroupwiseIntModel", declarations)
            for arguments in ([], ["-GroupwiseIntModel", "missing-model-file.ninfer"]):
                with self.subTest(lane=lane, arguments=arguments):
                    result = subprocess.run(
                        [shutil.which("pwsh"), "-NoProfile", "-NonInteractive", "-File", str(source),
                         *arguments], capture_output=True, text=True, encoding="utf-8", timeout=30)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("GroupwiseIntModel", result.stdout + result.stderr)
                    if arguments:
                        self.assertIn("must name an existing model file", result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for public-install subject observations")
    def test_public_install_observes_clone_and_installed_sources_separately(self):
        proof = r'''
param($Source,$Scratch)
$ErrorActionPreference='Stop'
$text=[IO.File]::ReadAllText($Source)
$start=$text.IndexOf('    $observedCandidate =')
$end=$text.IndexOf('    # 1. Closed checksum',$start)
$subject=$text.Substring($start,$end-$start)
$record=($text.Split("`n")|Where-Object {$_.StartsWith('    $receipt.installed =')}) -join "`n"
$CandidateClone=Join-Path $Scratch 'clone';$ClientBinary='observed-client'
Set-Location $Scratch
function observed-client {'omp/18.18.7'}
function Sha {param($Path) (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
$manifest=@{release='v0.18.0'};$v=@{release_tag='component'};$baseUrl='https://example.invalid'
$receipt=[ordered]@{};$active='installed';$installedBinary='c'*64;$installedConfig='d'*64
$rel=@{patch_stack_sha='a'*40;package_sha256='b'*64;binary_sha256='c'*64;config_sha256='d'*64}
Invoke-Expression $subject
Invoke-Expression $record
$receipt|ConvertTo-Json -Depth 8 -Compress
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            clone = root / "clone"
            write_json(clone / "releases/v0.18.0/manifest.json", {"release": "v0.18.0"})
            for command in (["init", "-q"], ["add", "."],
                            ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                             "commit", "-qm", "test: freeze public install candidate"]):
                subprocess.run(["git", "-C", str(clone), *command], check=True, capture_output=True)
            candidate = subprocess.check_output(["git", "-C", str(clone), "rev-parse", "HEAD"],
                                                text=True, encoding="utf-8").strip()
            binary = root / "observed-client"
            binary.write_bytes(b"observed stock client bytes")
            script = root / "proof.ps1"
            script.write_text(proof, encoding="utf-8")
            result = subprocess.run(
                [shutil.which("pwsh"), "-NoProfile", "-File", str(script),
                 str(ROOT / "scripts/hosts/accept-native-public-install.ps1"), directory],
                capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            receipt = json.loads(result.stdout)
            self.assertEqual(receipt["source"]["candidate_commit"], candidate)
            self.assertEqual(receipt["source"]["product_release"], "v0.18.0")
            self.assertEqual(receipt["installed"]["source_commit"], "a" * 40)
            self.assertEqual(receipt["installed"]["package_sha256"], "b" * 64)
            self.assertEqual(receipt["client"]["version"], "omp/18.18.7")
            self.assertEqual(receipt["client"]["binary_sha256"], hashlib.sha256(binary.read_bytes()).hexdigest())

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


class FreeSpaceFloorTests(unittest.TestCase):
    def test_linux_host_imports_are_skipped_on_windows(self):
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        expected = ast.dump(ast.parse(
            'unittest.skipIf(os.name == "nt", '
            '"the RTX 5090 host driver runs under Linux and imports fcntl")', mode="eval").body)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue
            if any(isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                   and call.func.attr == "spec_from_file_location"
                   and any(isinstance(value, ast.Constant) and isinstance(value.value, str)
                           and value.value.endswith("accept-rtx5090-host.py") for value in ast.walk(call))
                   for call in ast.walk(node)):
                with self.subTest(test=node.name):
                    self.assertIn(expected, [ast.dump(decorator) for decorator in node.decorator_list])

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for failed public-install receipts")
    def test_public_install_refusal_creates_the_receipt_parent(self):
        proof = r'''
param($Source,$Scratch)
$ErrorActionPreference='Stop'
$text=[IO.File]::ReadAllText($Source)
$start=$text.IndexOf('function Sha(')
$Workspace=Join-Path $Scratch 'absent';$StateRoot=$Scratch
$ReceiptPath=Join-Path $Workspace 'evidence/receipt.json';$Lane='rtx4090';$MinimumFreeGiB=10
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseInput($text,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
$free=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'FreeBytes'},$true)
$text=$text.Remove($free.Extent.StartOffset,$free.Extent.Text.Length).Insert($free.Extent.StartOffset,'function FreeBytes($path){1}')
& ([scriptblock]::Create($text.Substring($start)))
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "public-refusal.ps1"
            script.write_text(proof, encoding="utf-8")
            result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(script),
                                     str(ROOT / "scripts/hosts/accept-native-public-install.ps1"), directory],
                                    capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            receipt = root / "absent/evidence/receipt.json"
            self.assertTrue(receipt.is_file(), result.stdout + result.stderr)
            value = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(value["status"], "failed")
            self.assertIn("insufficient free space", value["error"])
            self.assertEqual(list((root / "absent").rglob("*")), [receipt.parent, receipt])

    @unittest.skipIf(os.name == "nt", "the RTX 5090 host driver runs under Linux and imports fcntl")
    def test_space_action_is_read_only_for_each_volume(self):
        spec = importlib.util.spec_from_file_location("read_only_space_host", ROOT / "scripts/hosts/accept-rtx5090-host.py")
        host = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(host)
        floor = 60 * 1024 ** 3
        for existing in (False, True):
            for refusal in ("workspace", "checkpoints", "docker", None):
                with self.subTest(existing=existing, refusal=refusal), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    workspace = root / "window"
                    if existing:
                        workspace.mkdir()
                    before = set(root.rglob("*"))
                    args = ["accept-rtx5090-host.py", "--action", "space", "--workspace", str(workspace),
                            "--release", "v0.18.0", "--candidate", "1" * 40,
                            "--windows-workspace", "C:/fixture", "--production-image", "fixture-image",
                            "--window-dir", "/fixture/window"]
                    def measurement(path, minimum):
                        self.assertEqual(minimum, 60)
                        volume = "workspace" if path == workspace.resolve() else "checkpoints"
                        if volume == refusal:
                            raise RuntimeError("insufficient free space")
                        return {"free_bytes": floor, "minimum_free_bytes": floor}
                    output = f"Filesystem 1024-blocks Used Available Capacity Mounted on\noverlay 200000000 0 {floor // 1024 - int(refusal == 'docker')} 0% /\n"
                    with mock.patch.object(sys, "argv", args), mock.patch.dict(os.environ), \
                            mock.patch.object(host.Path, "home", return_value=root / "home"), \
                            mock.patch.object(host, "free_space_record", side_effect=measurement) as measure, \
                            mock.patch.object(host, "windows_environment") as interop, \
                            mock.patch.object(host.subprocess, "run", return_value=
                                subprocess.CompletedProcess([], 0, output, "")) as command, \
                            contextlib.redirect_stdout(io.StringIO()):
                        if refusal:
                            with self.assertRaisesRegex(RuntimeError, "free space"):
                                host.main()
                        else:
                            host.main()
                        interop.assert_not_called()
                    self.assertEqual(set(root.rglob("*")), before)
                    if refusal not in ("workspace", "checkpoints"):
                        self.assertEqual(measure.call_count, 2)
                        self.assertEqual(command.call_args.args[0],
                                         ["docker", "exec", "ninfer-5090-v070p", "df", "-Pk", "/"])

    def test_space_refusal_leaves_every_attempt_unspent_and_no_hold_acquired(self):
        spec = importlib.util.spec_from_file_location("space_routes", ROOT / "scripts/hosts/accept-rtx5090-routes.py")
        routes = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(routes)
        for attempt in ("initial", "corrected", "completion"):
            with self.subTest(attempt=attempt), tempfile.TemporaryDirectory() as directory:
                root, prior = Path(directory) / "window", Path(directory) / "prior"
                write_json(root / "preflight.json", {"status": "passed"})
                write_json(prior / "window-attempt.json", {"attempt": "initial"})
                write_json(prior / "corrections.json", [{"route": "host", "change": "corrected fixture"}])
                write_json(prior / "restoration.json", {"window_seconds": 1, **{field: True for field in
                           ("checkout_restored", "documented_key_restored", "beta_absent", "documented_directories_restored")}})
                for label in ("host", "mac", "windows"):
                    write_json(prior / (label + "-route.json"), {"status": "passed"})
                args = ["accept-rtx5090-routes.py", "--action", "windows-live-only" if attempt == "completion" else "window",
                        "--workspace", str(root), "--prior-workspace", str(prior),
                        "--release", "v0.18.0", "--candidate", "1" * 40,
                        "--wsl-workspace", "/fixture/window", "--windows-workspace", "C:/fixture",
                        "--wsl-host", "fixture-wsl", "--windows-host", "fixture-windows",
                        "--route-ssh-destination", "fixture-route", "--production-image", "fixture-image",
                        "--window-dir", "/fixture/window"]
                if attempt == "corrected":
                    args += ["--attempt", "corrected"]
                with mock.patch.object(sys, "argv", args), \
                        mock.patch.object(routes, "documented_model", return_value="fixture-model"), \
                        mock.patch.object(routes.socket, "socket"), \
                        mock.patch.object(routes, "acquire_windows_hold") as hold, \
                        mock.patch.object(routes.subprocess, "run", return_value=
                            subprocess.CompletedProcess([], 1, "", "insufficient free space")) as command:
                    with self.assertRaises(RuntimeError):
                        routes.main()
                self.assertFalse((root / "window-attempt.json").exists())
                self.assertFalse((prior / "corrected-attempt.json").exists())
                self.assertFalse((prior / "windows-completion-attempt.json").exists())
                hold.assert_not_called()
                self.assertEqual(command.call_count, 1)
                self.assertIn("--action space", command.call_args.args[0][-1])

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for the free-space floor")
    def test_floor_refuses_before_effects_and_accepts_exactly_the_floor(self):
        proof = r'''
param($Source,$Scratch)
$ErrorActionPreference='Stop'
$text=[IO.File]::ReadAllText($Source);$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseInput($text,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
foreach($name in @('FreeBytes','AssertFreeSpace')){
    $node=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name},$true)
    if(-not $node){throw "missing floor function: $name"}
    Invoke-Expression $node.Extent.Text
}
$Workspace=Join-Path $Scratch 'absent';$StateRoot=$Scratch;$MinimumFreeGiB=60
$script:bytes=60GB-1;$script:records=@()
function FreeBytes($path){if($path -cne $StateRoot){throw 'wrong checkpoint volume'};$script:bytes}
function SaveJson($path,$value){$script:records+=@{path=$path;value=$value}}
$rejected=$false;try{AssertFreeSpace 'accept'}catch{$rejected=$true}
if(-not $rejected){throw 'accepted below the floor'}
if(Test-Path $Workspace){throw 'floor refusal created a directory'}
if($script:records.Count){throw 'floor refusal spent evidence before refusing'}
$script:bytes=60GB
AssertFreeSpace 'accept'
if($script:records.Count -ne 1){throw 'floor did not record its observation'}
$record=$script:records[0].value
if($record.free_bytes -ne 60GB -or $record.minimum_free_bytes -ne 60GB -or -not $record.utc){throw 'invalid free-space record'}
$script:bytes=1
AssertFreeSpace 'restored' -ObserveOnly
if($script:records[-1].value.free_bytes -ne 1){throw 'restoration observation enforced the floor'}
# Execute the production acceptance prefix: refusal must precede Snapshot's mkdir,
# preserved/qualified-artifacts directories, the journal, and every move.
$start=$text.IndexOf('# One window per workspace.')
$end=$text.IndexOf('$started=[DateTime]::UtcNow;$b=Snapshot',$start)
if($end -lt 0){throw 'acceptance prefix not found'}
$prefix=$text.Substring($start,$end-$start)
function ReadJson($path){@{status='passed'}}
function Test-Path {param($LiteralPath,$Path) $p=if($LiteralPath){$LiteralPath}else{$Path};$p -like '*omp-client-probe.py'}
$journal='unused';$script:records=@();$script:bytes=60GB-1
$rejected=$false;try{Invoke-Expression $prefix}catch{$rejected=$true}
if(-not $rejected){throw 'acceptance reached snapshot before checking the floor'}
foreach($mode in @('DryRun','Preflight')) {
    $node=$ast.Find({param($n) $n -is [Management.Automation.Language.IfStatementAst] -and
        $n.Clauses[0].Item1.Extent.Text -ceq ("`$Mode -eq '"+$mode+"'")},$true)
    if(-not $node.Extent.Text.Contains('AssertFreeSpace')){throw "$mode omitted the floor"}
}
'FLOOR_OK'
'''
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "floor.ps1"
            script.write_text(proof, encoding="utf-8")
            result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(script),
                                     str(ROOT / "scripts/hosts/accept-rtx4090-route.ps1"), directory],
                                    capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("FLOOR_OK", result.stdout)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for the public-install floor")
    def test_public_install_default_admits_post_window_free_space(self):
        proof = r'''
param($Source,$Scratch)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
$parameter=$ast.ParamBlock.Parameters|Where-Object {$_.Name.VariablePath.UserPath -ceq 'MinimumFreeGiB'}
$MinimumFreeGiB=$parameter.DefaultValue.SafeGetValue()
foreach($name in @('Utc','FreeBytes','FreeSpaceRecord')){
    $node=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name},$true)
    if(-not $node){throw "missing free-space function: $name"}
    Invoke-Expression $node.Extent.Text
}
function FreeBytes($path){[int64]36.5GB}
FreeSpaceRecord $Scratch|ConvertTo-Json -Compress
'''
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "public-floor.ps1"
            script.write_text(proof, encoding="utf-8")
            result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(script),
                                     str(ROOT / "scripts/hosts/accept-native-public-install.ps1"), directory],
                                    capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            record = json.loads(result.stdout)
            self.assertEqual(record["free_bytes"], int(36.5 * 1024 ** 3))
            self.assertEqual(record["minimum_free_bytes"], 10 * 1024 ** 3)

    def test_accept_refusing_dry_run_does_not_spend_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root / "driver-preflight.json", {"plan": {"candidate": "1" * 40,
                       "client_install": {"lane": "rtx4090-native"}},
                       **{key: "a" * 64 for key in
                          ("orchestrator_sha256", "health_reducer_sha256", "probe_sha256", "gpu_helper_sha256")}})
            command = ["accept-rtx4090-route.py", "--release", "v0.18.0", "--candidate", "1" * 40,
                       "--host", "fixture-host", "--workspace", directory,
                       "--remote-workspace", "C:/acceptance", "--expected-state-sha256", "2" * 64,
                       "--first-release", "--mode", "accept"]
            calls = []

            def refusing(host, code, **kwargs):
                calls.append(code)
                raise RuntimeError("free space below floor")

            with mock.patch.object(sys, "argv", command), mock.patch.object(DRIVER, "sha", return_value="a" * 64), \
                    mock.patch.object(DRIVER, "ssh", side_effect=refusing):
                with self.assertRaisesRegex(RuntimeError, "free space below floor"):
                    DRIVER.main()
            self.assertFalse((root / "driver-window.json").exists())
            self.assertEqual(len(calls), 1)
            self.assertIn("-Mode 'DryRun'", calls[0])
            self.assertIn("-MinimumFreeGiB '60'", calls[0])

    @unittest.skipIf(os.name == "nt", "the RTX 5090 host driver runs under Linux and imports fcntl")
    def test_docker_space_errors_name_the_exact_read_only_command_and_fail_closed(self):
        spec = importlib.util.spec_from_file_location("docker_space_host", ROOT / "scripts/hosts/accept-rtx5090-host.py")
        host = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(host)
        docker = ["docker", "exec", "ninfer-5090-v070p", "df", "-Pk", "/"]
        for fault in ("unavailable", "parse", "below", "at"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                window = root / "window"
                args = ["accept-rtx5090-host.py", "--action", "preflight", "--workspace", str(window),
                        "--release", "v0.18.0", "--candidate", "1" * 40,
                        "--windows-workspace", "C:/fixture", "--production-image", "fixture-image",
                        "--window-dir", "/fixture/window", "--model-id", "fixture-model"]

                def command(argv, **kwargs):
                    if argv != docker:
                        raise RuntimeError("past-floor")
                    free_kib = 60 * 1024 ** 2 - int(fault == "below")
                    text = ("not a filesystem record" if fault == "parse" else
                            f"Filesystem 1024-blocks Used Available Capacity Mounted on\n"
                            f"overlay 209715200 104857600 {free_kib} 50% /\n")
                    return subprocess.CompletedProcess(argv, int(fault == "unavailable"), text, "")

                environment = dict(os.environ)
                with mock.patch.dict(os.environ, clear=False), mock.patch.object(sys, "argv", args), \
                        mock.patch.object(host.Path, "home", return_value=root), \
                        mock.patch.object(host, "windows_environment", return_value={}), \
                        mock.patch.object(host.shutil, "disk_usage", return_value=shutil._ntuple_diskusage(
                            100 * 1024 ** 3, 40 * 1024 ** 3, 60 * 1024 ** 3)), \
                        mock.patch.object(host.subprocess, "run", side_effect=command):
                    message = ("docker exec ninfer-5090-v070p df -Pk /" if fault in ("unavailable", "parse")
                               else "past-floor" if fault == "at" else "insufficient Docker free space")
                    with self.assertRaisesRegex(RuntimeError, re.escape(message)):
                        host.main()
                self.assertEqual(dict(os.environ), environment)
                self.assertEqual(window.exists(), fault == "at")

    def test_minimum_free_gib_is_recorded_offline(self):
        command = [sys.executable, str(ROOT / "scripts/hosts/accept-rtx4090-route.py"),
                   "--release", "v0.18.0", "--candidate", "1" * 40, "--host", "fixture-host",
                   "--workspace", "unused", "--remote-workspace", "C:/acceptance",
                   "--expected-state-sha256", "2" * 64, "--first-release", "--minimum-free-gib", "72"]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["plan"]["minimum_free_gib"], 72)

    @unittest.skipIf(os.name == "nt", "the RTX 5090 host driver runs under Linux and imports fcntl")
    def test_large_write_sweep_checks_wsl_and_docker_volumes(self):
        spec = importlib.util.spec_from_file_location("space_host", ROOT / "scripts/hosts/accept-rtx5090-host.py")
        host = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(host)
        with tempfile.TemporaryDirectory() as directory:
            floor = 60 * 1024 ** 3
            usage = shutil._ntuple_diskusage(100 * floor, floor, floor - 1)
            with mock.patch.object(host.shutil, "disk_usage", return_value=usage):
                with self.assertRaisesRegex(RuntimeError, "free space"):
                    host.free_space_record(Path(directory) / "absent", 60)
            with mock.patch.object(host.shutil, "disk_usage", return_value=usage._replace(free=floor)):
                self.assertEqual(host.free_space_record(Path(directory), 60)["free_bytes"], floor)
        source = (ROOT / "scripts/hosts/accept-rtx5090-host.py").read_text(encoding="utf-8")
        self.assertIn("['docker', 'exec', a.production, 'df', '-Pk', '/']", source)
        self.assertLess(source.index("check_free_space()"), source.index("root.mkdir(mode=0o700"))
        public = (ROOT / "scripts/hosts/accept-native-public-install.ps1").read_text(encoding="utf-8")
        self.assertLess(public.index("$receipt.free_space ="), public.index("New-Item -ItemType Directory"))


class ServerHealthTests(unittest.TestCase):
    RESTORE_CAPTURE = r'''
param($Source,$Scratch,$Case)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
foreach($name in @('SaveJson','ReadJson','Hash','Describe','BestEffortWrite','SaveServerLogs','Restore','Audit')){
    $node=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true)
    if($null -eq $node -and $name -eq 'BestEffortWrite'){continue}
    Invoke-Expression $node.Extent.Text
}
$production=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'SaveJson'},$true).Extent.Text
Invoke-Expression ('function ProductionSaveJson'+$production.Substring('function SaveJson'.Length))
$utf8=[Text.UTF8Encoding]::new($false)
$Workspace=Join-Path $Scratch 'evidence';$StateRoot=Join-Path $Scratch 'state'
$baseline=Join-Path $Scratch 'baseline';$Stage=Join-Path $Scratch 'stage'
$journal=Join-Path $Workspace 'preparation.json';$TaskName='fixture-task';$FirstRelease=$false
New-Item -ItemType Directory -Force $Workspace,$StateRoot,$Stage,"$Workspace/preserved","$Workspace/qualified-artifacts","$baseline/files"|Out-Null
$script:armed=$false
function SaveJson($path,$value){
    if($Case -eq 'journal-interrupted' -and $path -ceq $journal){$script:journalValue=$value;ProductionSaveJson $path $value;return}
    if($Case -eq 'receipt-failure' -and $path.EndsWith('server-log-capture.json')){throw 'injected receipt failure'}
    if($script:armed -and
       (($Case -eq 'restoration-receipt-failure' -and $path.EndsWith('restoration.json')) -or
        ($Case -eq 'journal-failure' -and $path.EndsWith('preparation.json')))){
        throw [Exception]::new('outer private path',[IO.IOException]::new('inner private path',-2147024784))
    }
    [IO.File]::WriteAllText($path.Replace('\','/'),($value|ConvertTo-Json -Depth 50),$utf8)
}
function Get-Acl {param($Path,$LiteralPath) @{Sddl='fixture-acl'}}
function SetExactAcl($path,$sddl){if(-not (Test-Path -LiteralPath $path)){throw 'restoring absent path'}}
function EnableExactAcl {}
function Get-ScheduledTask {param($TaskName,$ErrorAction) @{State='Ready'}}
function Export-ScheduledTask {param($TaskName) '<Task/>'}
function Get-CimInstance {param($ClassName,$Filter)}
function Get-NetTCPConnection {param($State,$ErrorAction)}
function Resolve-NativeGpuUuid($root){'fixture-gpu'}
function Get-NativeGpuPowerLimit($uuid){450}
function SupportFiles {[pscustomobject]@{FullName="$StateRoot\state.json"}}
function SupportDirectories {[pscustomobject]@{FullName=$StateRoot}}
function AssertFreeSpace($phase,[switch]$ObserveOnly){
    $script:spaceObserved=$true
    if($script:armed -and $Case -eq 'space-receipt-failure'){throw 'injected free-space receipt failure'}
}
function Probe {
    $s=ReadJson "$StateRoot/state.json"
    @{state_sha256=(Hash "$StateRoot/state.json");state_sddl='fixture-acl';root_sddl='fixture-acl'
      task_state='Ready';processes=@();listeners=@();lease_present=$false;lease_entries=@()
      power_limit_w=450;active_release=$s.active_release;previous_release=$s.previous_release
      prepared_release=$s.prepared_release;holds=@();client_files=@()}
}
$candidate=[pscustomobject]@{release_root=(Join-Path $Scratch 'candidate')}
$incumbent=[pscustomobject]@{release_root=(Join-Path $Scratch 'incumbent')}
foreach($record in @($candidate,$incumbent)){New-Item -ItemType Directory -Force (Join-Path $record.release_root 'logs')|Out-Null}
$original=[pscustomobject]@{active_release='candidate';previous_release='incumbent';prepared_release=$null
    releases=[pscustomobject]@{candidate=$candidate;incumbent=$incumbent}}
SaveJson "$StateRoot/state.json" $original
Copy-Item "$StateRoot/state.json" "$baseline/files/state.json"
[IO.File]::WriteAllText("$baseline\task.xml",'<Task/>')
[IO.File]::WriteAllText((Join-Path $Stage 'original.txt'),'original stage')
$script:snapshot=@{observable=(Probe);files=@(@{relative='state.json';sha256=(Hash "$StateRoot/state.json");sddl='fixture-acl'})
    directories=@(@{relative='';exists=$true;sddl='fixture-acl'});documented_stage=(Describe $Stage)}
function ValidateSnapshot($path){$script:snapshot}
Move-Item $Stage "$Workspace/preserved/stage"
New-Item -ItemType Directory $Stage|Out-Null
[IO.File]::WriteAllText((Join-Path $Stage 'window.txt'),'window stage')
SaveJson $journal @{status=$(if($Case -eq 'journal-interrupted'){'preparing'}else{'prepared'});moves=@(@{kind='documented-stage';path=$Stage;preserved="$Workspace/preserved/stage";exists=$true})}
if($Case -eq 'incumbent'){
    SaveJson "$StateRoot/state.json" @{active_release='incumbent';previous_release='older';prepared_release=$null;releases=@{incumbent=$incumbent}}
}else{
    $original.previous_release='older';SaveJson "$StateRoot/state.json" $original
}
$script:stops=0;$script:copyNames=@();$script:spaceObserved=$false
function Control($action,$file,[switch]$BestEffort){
    $script:stops++
    $s=ReadJson "$StateRoot/state.json";$root=$s.releases.([string]$s.active_release).release_root
    [IO.File]::WriteAllText((Join-Path $root 'logs/requests.jsonl'),"{`"event`":`"stop_$script:stops`"}")
    [IO.File]::WriteAllText((Join-Path $root 'logs/stderr.log'),"stop $script:stops")
    [IO.File]::WriteAllText((Join-Path $root 'logs/stderr.log.previous'),"previous $script:stops")
    SaveJson (Join-Path $root 'logs/shutdown.json') @{complete=$true;refused=0;saved=$script:stops;skipped=0}
}
if($Case -eq 'stop-receipt-failure'){
    Remove-Item Function:\Control
    $node=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Control'},$true)
    Invoke-Expression $node.Extent.Text
    function Get-ExecutionPolicy {param($Scope) 'Unrestricted'}
    function Set-ExecutionPolicy {param($Scope,$ExecutionPolicy,[switch]$Force)}
    function Out-File {
        [CmdletBinding()]
        param([Parameter(Position=0)][string]$FilePath,
              [Parameter(ValueFromPipeline=$true)]$InputObject,[string]$Encoding)
        begin {
            if($FilePath -match '(restoration-stop|recovery-status)\.json$'){
                throw [IO.IOException]::new('private output path',-2147024784)
            }
        }
        process {$InputObject|Microsoft.PowerShell.Utility\Out-File -FilePath $FilePath -Encoding $Encoding -Append}
    }
    $controller=Join-Path $Scratch 'controller.ps1'
    [IO.File]::WriteAllText($controller,@'
param($Action,$StateRoot)
if($Action -eq 'Stop'){
    [IO.File]::WriteAllText((Join-Path $StateRoot 'stop-ran'),'true')
    $state=Get-Content (Join-Path $StateRoot 'state.json') -Raw|ConvertFrom-Json
    $logs=Join-Path $state.releases.([string]$state.active_release).release_root 'logs'
    [IO.File]::WriteAllText((Join-Path $logs 'requests.jsonl'),'{"event":"stop_1"}')
    [IO.File]::WriteAllText((Join-Path $logs 'stderr.log'),'stop 1')
    [IO.File]::WriteAllText((Join-Path $logs 'stderr.log.previous'),'previous 1')
    [IO.File]::WriteAllText((Join-Path $logs 'shutdown.json'),'{"complete":true,"refused":0,"saved":1,"skipped":0}')
}
'{"status":"stopped"}'
'@)
}
function Copy-Item {
    param($LiteralPath,$Path,$Destination,[switch]$Force,$ErrorAction)
    $source=if($LiteralPath){$LiteralPath}else{$Path}
    if($source -match '[\\/]logs[\\/]'){
        $script:copyNames+=([IO.Path]::GetFileName($source))
        if($Case -in @('copy-failure','outage-copy-failure') -and $source.EndsWith('stderr.log')){throw 'injected log copy failure'}
    }
    Microsoft.PowerShell.Management\Copy-Item -LiteralPath $source -Destination $Destination -Force:$Force
}
$outageContinued=$false
if($Case -in @('captured-outage','outage-copy-failure')){
    $installed=$candidate
    $outage=$ast.Find({param($n) $n -is [Management.Automation.Language.TryStatementAst] -and
        $n.Extent.Text.StartsWith("try{Control Stop 'outage-stop.json'}")},$true)
    if(-not $outage){throw 'missing production outage capture'}
    Invoke-Expression $outage.Extent.Text
    $outageContinued=$true
}
$interruption=$null
if($Case -eq 'journal-interrupted'){
    # Accept's rewrite after the lineage moves fails once the journal is open, like a full volume:
    # a strict encoder refuses an unpaired surrogate.
    $previous=[Convert]::ToBase64String([IO.File]::ReadAllBytes($journal))
    $prep=ReadJson $journal;$prep.status='prepared'
    $prep|Add-Member -NotePropertyName temporary_state_sha256 -NotePropertyValue ([string][char]0xD800)
    $utf8=[Text.UTF8Encoding]::new($false,$true);$interruption=[ordered]@{thrown=$false}
    try{SaveJson $journal $prep}catch{$interruption.thrown=$true}
    $utf8=[Text.UTF8Encoding]::new($false)
    $interruption.journal_unchanged=([Convert]::ToBase64String([IO.File]::ReadAllBytes($journal)) -ceq $previous)
    $interruption.partials=@(Get-ChildItem $Workspace -Filter '*.partial' -Force).Count
}
$script:armed=$true
$result=Restore
if($result.status -cne 'passed'){throw 'production restoration audit failed'}
if((Get-Content (Join-Path $Stage 'original.txt')) -cne 'original stage'){throw 'stage not restored'}
if((Get-Content "$Workspace/qualified-artifacts/documented-stage/window.txt") -cne 'window stage'){throw 'window evidence lost'}
if($Case -eq 'journal-interrupted'){
    # Restore's own rewrite to 'restored' must be byte-identical to the former in-place write.
    $today=Join-Path $Scratch 'today.json'
    [IO.File]::WriteAllText($today,($script:journalValue|ConvertTo-Json -Depth 50)+"`n",$utf8)
    $interruption.rewrite_matches_today=([Convert]::ToBase64String([IO.File]::ReadAllBytes($journal)) -ceq
        [Convert]::ToBase64String([IO.File]::ReadAllBytes($today)))
    $interruption.partials_after_restore=@(Get-ChildItem $Workspace -Filter '*.partial' -Force).Count
}
$strictRejected=$false
if($Case -eq 'stop-receipt-failure'){
    if(-not (Test-Path (Join-Path $StateRoot 'stop-ran'))){throw 'managed Stop did not run'}
    try{Control Status 'recovery-status.json'}catch{$strictRejected=$true}
}
@{restoration=$result;copy_names=@($script:copyNames);outage_continued=$outageContinued;stops=$script:stops
  journal_status=(ReadJson $journal).status;space_observed=$script:spaceObserved;interruption=$interruption
  restoration_receipt_exists=(Test-Path "$Workspace/restoration.json");strict_rejected=$strictRejected}|ConvertTo-Json -Depth 20 -Compress
'''

    def restored_log_capture(self, case):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "restore-capture.ps1"
            script.write_text(self.RESTORE_CAPTURE, encoding="utf-8")
            result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(script),
                                     str(ROOT / "scripts/hosts/accept-rtx4090-route.ps1"), directory, case],
                                    capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            value = json.loads(result.stdout.splitlines()[-1])
            self.assertEqual(value["restoration"]["status"], "passed")
            self.assertTrue(all(value["restoration"]["checks"].values()))
            evidence = root / "evidence"
            capture = evidence / "server-log-capture.json"
            value["capture"] = json.loads(capture.read_text()) if capture.exists() else None
            value["logs"] = {name: (evidence / name).read_text() for name in
                             ("server-requests.jsonl", "server-stderr.log", "server-stderr.previous.log", "shutdown.json")
                             if (evidence / name).is_file()}
            value["health"] = DRIVER.assess_server_health(evidence)
            value["candidate_shutdown"] = json.loads((root / "candidate/logs/shutdown.json").read_text()) \
                if (root / "candidate/logs/shutdown.json").exists() else None
            if case not in ("stop-receipt-failure", "restoration-receipt-failure",
                            "journal-failure", "space-receipt-failure"):
                self.assertEqual(value["journal_status"], "restored")
                self.assertTrue(value["space_observed"])
            return value

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for capture failure restoration")
    def test_restore_completes_and_audits_when_log_copy_or_receipt_fails(self):
        for case in ("copy-failure", "outage-copy-failure", "receipt-failure"):
            with self.subTest(case=case):
                value = self.restored_log_capture(case)
                if case == "receipt-failure":
                    self.assertIsNone(value["capture"])
                else:
                    self.assertEqual(value["capture"]["failed"], ["server-stderr.log"])
                    self.assertEqual(value["capture"]["missing"], [])
                    names = {"server-requests.jsonl", "server-stderr.previous.log", "shutdown.json"}
                    if case == "outage-copy-failure":
                        self.assertEqual(value["capture"]["copied"], [])
                        self.assertEqual(set(value["capture"]["retained"]), names)
                    else:
                        self.assertEqual(set(value["capture"]["copied"]), names)
                    self.assertEqual(value["health"]["status"], "failed")
                    self.assertFalse(value["health"]["checks"]["stderr_log_present"])
                if case == "outage-copy-failure":
                    self.assertTrue(value["outage_continued"])

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for candidate-only log capture")
    def test_restore_does_not_copy_incumbent_logs(self):
        value = self.restored_log_capture("incumbent")
        self.assertEqual(value["logs"], {})
        self.assertEqual(value["copy_names"], [])
        self.assertEqual(value["capture"]["copied"], [])
        self.assertEqual(value["capture"]["failed"], [])
        self.assertEqual(set(value["capture"]["missing"]),
                         {"server-requests.jsonl", "server-stderr.log", "server-stderr.previous.log", "shutdown.json"})
        self.assertEqual(value["health"]["status"], "failed")

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for write-once log capture")
    def test_restore_preserves_logs_captured_after_outage(self):
        value = self.restored_log_capture("captured-outage")
        self.assertTrue(value["outage_continued"])
        self.assertEqual(value["stops"], 2)
        self.assertEqual(len(value["copy_names"]), 4)
        self.assertEqual(value["logs"]["server-requests.jsonl"], '{"event":"stop_1"}')
        self.assertEqual(value["logs"]["server-stderr.log"], "stop 1")
        self.assertEqual(value["logs"]["server-stderr.previous.log"], "previous 1")
        self.assertEqual(json.loads(value["logs"]["shutdown.json"])["saved"], 1)
        self.assertEqual(value["candidate_shutdown"]["saved"], 2)
        self.assertEqual(value["capture"]["failed"], [])
        self.assertEqual(value["capture"]["missing"], [])
        self.assertEqual(value["capture"]["copied"], [])
        self.assertEqual(set(value["capture"]["retained"]), set(value["logs"]))

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for restoration write failures")
    def test_restore_keeps_canonical_restoration_independent_of_evidence_writes(self):
        cases = {
            "stop-receipt-failure": ("restoration-stop.json", True, True),
            "restoration-receipt-failure": ("restoration.json", False, False),
            "journal-failure": ("preparation.json", True, False),
            "space-receipt-failure": ("free-space-restored.json", True, True),
        }
        for case, (label, receipt_written, journal_restored) in cases.items():
            with self.subTest(case=case):
                value = self.restored_log_capture(case)
                restored = value["restoration"]
                self.assertEqual([row["write"] for row in restored["write_failures"]], [label])
                self.assertEqual(restored["restoration_receipt_written"], receipt_written)
                self.assertEqual(restored["journal_restored"], journal_restored)
                self.assertEqual(value["restoration_receipt_exists"], receipt_written)
                self.assertEqual(value["journal_status"], "restored" if journal_restored else "prepared")
                self.assertTrue(value["space_observed"])
                if case != "space-receipt-failure":
                    failure = restored["write_failures"][0]
                    self.assertEqual(failure["error_type"], "System.IO.IOException")
                    self.assertEqual(failure["hresult"], "0x80070070")
                    self.assertTrue(failure["utc"])
                    self.assertNotIn("private", json.dumps(failure))
                if case == "stop-receipt-failure":
                    self.assertTrue(value["strict_rejected"])
                    self.assertEqual(len(value["capture"]["copied"]), 4)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for the interrupted journal rewrite")
    def test_interrupted_journal_rewrite_keeps_the_previous_journal_for_restoration(self):
        value = self.restored_log_capture("journal-interrupted")
        interruption = value["interruption"]
        self.assertTrue(interruption["thrown"])
        self.assertTrue(interruption["journal_unchanged"])
        self.assertEqual(interruption["partials"], 0)
        # restored_log_capture already proved the stage, the audit and the 'restored' journal.
        self.assertTrue(interruption["rewrite_matches_today"])
        self.assertEqual(interruption["partials_after_restore"], 0)

    def test_health_failures_fail_behavior_and_the_collected_window(self):
        for fault in ("queue", "write", "incomplete", "refused", "missing"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                window = rtx3090_window(Path(directory), "q38-ninfer")
                evidence = window["evidence"]
                if fault == "queue":
                    (evidence / "server-requests.jsonl").write_text(json.dumps({
                        "artifact_type": "ninfer_serve_request_log", "event": "request_rejected",
                        "error": {"status": 503, "code": "request_queue_timeout",
                                  "message": "synthetic private path must not be published"}}) + "\n")
                elif fault == "write":
                    (evidence / "server-stderr.log").write_text(json.dumps({
                        "schema": "ninfer-checkpoint-io-error/1", "operation": "payload_write",
                        "error_code": 112, "reason": "capacity", "path": "private synthetic path"}) + "\n")
                elif fault == "missing":
                    (evidence / "shutdown.json").unlink()
                else:
                    write_json(evidence / "shutdown.json", {"complete": fault != "incomplete",
                               "saved": 0, "refused": int(fault == "refused"), "skipped": 1})
                result = DRIVER.assess_evidence(evidence, window["clone"], window["bundle"],
                                                "v0.9.1", "1" * 40, "rtx3090")
                self.assertEqual(result["status"], "failed")
                self.assertFalse(result["checks"]["server_health_passed"])
                self.assertNotIn("private", json.dumps(result["server_health"]))
                host_window = json.loads((evidence / "window.json").read_text(encoding="utf-8"))
                self.assertEqual(host_window["status"], "failed")
                self.assertEqual(host_window["first_failing_boundary"], "behavior-evidence")

    def test_capacity_stale_client_cancel_and_non_503_rejections_are_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory)
            rows = [{"event": "request_rejected", "error": {"status": status, "code": code}}
                    for status, code in ((499, "client_disconnected"), (400, "reasoning_effort_not_supported"))]
            (evidence / "server-requests.jsonl").write_text("\n".join(map(json.dumps, rows)), encoding="utf-8")
            (evidence / "server-stderr.log").write_text(
                "synthetic req#1 response failed during transport | HTTP 499 | client disconnected\n" + "\n".join(map(json.dumps, [
                {"schema": "ninfer-durable-operation/1", "operation": "save", "state": "refused",
                 "reason": "capacity", "host_shortage": "busy"},
                {"schema": "ninfer-durable-operation/1", "operation": "save", "state": "stale",
                 "reason": "stale_publication"}])), encoding="utf-8")
            write_json(evidence / "shutdown.json", {"complete": True, "refused": 0, "saved": 2, "skipped": 1})
            health = DRIVER.assess_server_health(evidence)
            self.assertEqual(health["status"], "passed")
            self.assertEqual(health["capacity_save_receipts"], 1)
            self.assertEqual(health["stale_save_receipts"], 1)
            self.assertEqual(health["client_disconnections"], 1)
            self.assertEqual(health["http_499_transport_errors"], 1)
            # A prior launch's retained stderr must count too.
            (evidence / "server-stderr.previous.log").write_text(json.dumps({
                "schema": "ninfer-checkpoint-io-error/1", "operation": "payload_write", "error_code": 112}))
            health = DRIVER.assess_server_health(evidence)
            self.assertEqual(health["checkpoint_write_errors"], 1)
            self.assertEqual(health["status"], "failed")
            command = [sys.executable, str(ROOT / "scripts/hosts/accept-rtx4090-route.py"),
                       "server-health", "--evidence", str(evidence)]
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(json.loads((evidence / "server-health.json").read_text())["status"], "failed")

    def test_host_captures_health_after_stop_and_gates_its_window(self):
        source = (ROOT / "scripts/hosts/accept-rtx4090-route.ps1").read_text(encoding="utf-8")
        self.assertIn("finally{SaveServerLogs", source)
        self.assertIn("server-stderr.previous.log", source)
        self.assertIn("AssertServerHealth", source)
        self.assertLess(source.rindex("AssertServerHealth"), source.index('SaveJson "$Workspace\\window.json"'))
        self.assertIn("initial install launch covered by requests only", source)
        accept = source[source.index("$started=[DateTime]::UtcNow;$b=Snapshot $baseline"):]
        self.assertLess(accept.index("EnableExactAcl"), accept.index("$effect=$true"))
        self.assertIn("restoration_write_failures", accept[accept.index('SaveJson "$Workspace\\window.json"'):])
        driver = (ROOT / "scripts/hosts/accept-rtx4090-route.py").read_text(encoding="utf-8")
        self.assertIn('str(orchestrator.with_suffix(".py"))', driver)
        self.assertIn('sync_window_failure', driver)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for stopped-server log capture")
    def test_stopped_server_capture_copies_only_the_four_named_logs(self):
        proof = r'''
param($Source,$Scratch)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
$utf8=[Text.UTF8Encoding]::new($false)
foreach($name in @('SaveJson','SaveServerLogs')){
    $node=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name},$true)
    if(-not $node){throw 'missing log capture'}
    Invoke-Expression $node.Extent.Text
}
$Workspace=Join-Path $Scratch 'evidence'
SaveServerLogs @{release_root=(Join-Path $Scratch 'candidate')}
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            logs = root / "candidate/logs"
            logs.mkdir(parents=True)
            (root / "evidence").mkdir()
            names = {"requests.jsonl": "server-requests.jsonl", "stderr.log": "server-stderr.log",
                     "stderr.log.previous": "server-stderr.previous.log", "shutdown.json": "shutdown.json"}
            for name in (*names, "private-key.txt"):
                (logs / name).write_text("synthetic " + name, encoding="utf-8")
            script = root / "capture.ps1"
            script.write_text(proof, encoding="utf-8")
            result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(script),
                                     str(ROOT / "scripts/hosts/accept-rtx4090-route.ps1"), directory],
                                    capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual({p.name for p in (root / "evidence").iterdir()},
                             set(names.values()) | {"server-log-capture.json"})
            capture = json.loads((root / "evidence/server-log-capture.json").read_text())
            self.assertEqual(capture, {"copied": list(names.values()), "retained": [], "missing": [], "failed": []})
            for source, destination in names.items():
                self.assertEqual((root / "evidence" / destination).read_bytes(), (logs / source).read_bytes())

    def log_capture_case(self, case):
        proof = r'''
param($Source,$Scratch,$Case)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
foreach($name in @('SaveJson','ReadJson','SaveServerLogs')){
    $node=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true)
    Invoke-Expression $node.Extent.Text
}
$utf8=[Text.UTF8Encoding]::new($false)
$Workspace=Join-Path $Scratch 'evidence';$installed=@{release_root=(Join-Path $Scratch 'candidate')}
$destination=Join-Path $Workspace 'server-stderr.log'
$script:interrupt=$Case -eq 'interrupted'
function Copy-Item {
    param($LiteralPath,$Destination,[switch]$Force,$ErrorAction)
    if($script:interrupt){
        $script:interrupt=$false
        [IO.File]::WriteAllText($Destination,'truncated')
        throw 'injected interrupted copy'
    }
    Microsoft.PowerShell.Management\Copy-Item -LiteralPath $LiteralPath -Destination $Destination -Force:$Force
}
SaveServerLogs $installed
$first=@{capture=(ReadJson (Join-Path $Workspace 'server-log-capture.json'))
    destination_exists=(Test-Path $destination);partial_count=@(Get-ChildItem $Workspace -Filter '*.partial').Count}
SaveServerLogs $installed
@{first=$first;second=(ReadJson (Join-Path $Workspace 'server-log-capture.json'))
    bytes=[IO.File]::ReadAllText($destination);partial_count=@(Get-ChildItem $Workspace -Filter '*.partial').Count}|ConvertTo-Json -Depth 10 -Compress
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            logs = root / "candidate/logs"
            logs.mkdir(parents=True)
            (logs / "stderr.log").write_text("complete log bytes", encoding="utf-8")
            (root / "evidence").mkdir()
            if case == "retained":
                (root / "evidence/server-stderr.log").write_text("earlier", encoding="utf-8")
            script = root / "capture.ps1"
            script.write_text(proof, encoding="utf-8")
            result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(script),
                                     str(ROOT / "scripts/hosts/accept-rtx4090-route.ps1"), directory, case],
                                    capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads(result.stdout.splitlines()[-1])

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for retained log capture")
    def test_existing_destination_is_retained_not_copied(self):
        value = self.log_capture_case("retained")
        self.assertEqual(value["first"]["capture"]["copied"], [])
        self.assertEqual(value["first"]["capture"]["retained"], ["server-stderr.log"])
        self.assertEqual(value["bytes"], "earlier")
        self.assertEqual(value["partial_count"], 0)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for atomic log capture")
    def test_interrupted_copy_leaves_no_destination(self):
        value = self.log_capture_case("interrupted")
        self.assertFalse(value["first"]["destination_exists"])
        self.assertEqual(value["first"]["partial_count"], 0)
        self.assertEqual(value["first"]["capture"]["failed"], ["server-stderr.log"])
        self.assertEqual(value["second"]["copied"], ["server-stderr.log"])
        self.assertEqual(value["bytes"], "complete log bytes")
        self.assertEqual(value["partial_count"], 0)


class AtomicRecordWriteTests(unittest.TestCase):
    """Native records read back during recovery are swapped in whole, never truncated in place."""

    WRITERS = r'''
param($Root,$Scratch)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Bytes($path){[Convert]::ToBase64String([IO.File]::ReadAllBytes($path))}
function Load($file,$name){
    $tokens=$null;$errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $Root $file),[ref]$tokens,[ref]$errors)
    if($errors.Count){throw ($errors|Out-String)}
    $text=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true).Extent.Text
    # Route each writer's encoder through $utf8, so a strict encoder can fail it mid-write.
    $inline='[Text.UTF8Encoding]::new($false)'
    if($file -cne 'accept-rtx4090-route.ps1' -and ([regex]::Matches($text,[regex]::Escape($inline))).Count -ne 1){throw "$name must construct its encoder once"}
    $text.Replace($inline,'$utf8')
}
Invoke-Expression (Load 'accept-rtx4090-route.ps1' 'SaveJson')
Invoke-Expression (Load 'accept-windows-client.ps1' 'Save-Json')
Invoke-Expression (Load 'accept-native-public-install.ps1' 'Finish')
function Utc {'2026-11-13T00:00:00.0000000Z'}
$normal=[Text.UTF8Encoding]::new($false);$strict=[Text.UTF8Encoding]::new($false,$true)
# Each writer, and the bytes its former in-place write produced for the value it was given.
$writers=[ordered]@{
    journal=@{write={param($path,$value) SaveJson $path $value};today={param($value) ($value|ConvertTo-Json -Depth 50)+"`n"}}
    hold=@{write={param($path,$value) $Workspace=Split-Path $path -Parent;Save-Json (Split-Path $path -Leaf) $value}
        today={param($value) $value|ConvertTo-Json -Depth 20}}
    public=@{write={param($path,$value) $ReceiptPath=$path;$receipt=$value;Finish 'passed'};today={param($value) $value|ConvertTo-Json -Depth 8}}
}
$rows=[ordered]@{}
foreach($name in $writers.Keys){
    $w=$writers[$name];$directory=Join-Path $Scratch $name;$null=New-Item -ItemType Directory $directory
    $path=Join-Path $directory 'record.json';$today=Join-Path $Scratch "$name-today.json";$row=[ordered]@{}
    $utf8=$normal
    foreach($step in @('created','rewritten')){
        $value=[ordered]@{status=$step;path='C:\fixture';note=('na'+[char]0xEF+'ve')}
        & $w.write $path $value
        [IO.File]::WriteAllText($today,(& $w.today $value),$normal)
        $row["${step}_matches_today"]=((Bytes $path) -ceq (Bytes $today))
    }
    # A strict encoder refuses an unpaired surrogate once the file is open, like a full volume.
    $previous=Bytes $path;$utf8=$strict
    $value=[ordered]@{status='interrupted';path='C:\fixture';note=[string][char]0xD800}
    try{& $w.write $path $value;$row.rewrite_thrown=$false}catch{$row.rewrite_thrown=$true}
    $row.rewrite_kept_previous=((Bytes $path) -ceq $previous)
    $fresh=Join-Path $directory 'fresh.json'
    try{& $w.write $fresh $value;$row.create_thrown=$false}catch{$row.create_thrown=$true}
    $row.create_left_nothing=-not (Test-Path -LiteralPath $fresh)
    $utf8=$normal
    $row.partials=@(Get-ChildItem -LiteralPath $directory -Force|Where-Object Name -like '*.partial').Count
    $rows[$name]=$row
}
$rows|ConvertTo-Json -Compress
'''

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for native record writers")
    def test_interrupted_writes_keep_previous_records_and_writes_keep_their_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "writers.ps1"
            script.write_text(self.WRITERS, encoding="utf-8")
            scratch = Path(directory) / "scratch"
            scratch.mkdir()
            result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(script),
                                     str(ROOT / "scripts/hosts"), str(scratch)],
                                    capture_output=True, text=True, encoding="utf-8", timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            rows = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(list(rows), ["journal", "hold", "public"])
        for name, row in rows.items():
            with self.subTest(writer=name):
                self.assertEqual(row, {"created_matches_today": True, "rewritten_matches_today": True,
                                       "rewrite_thrown": True, "rewrite_kept_previous": True,
                                       "create_thrown": True, "create_left_nothing": True, "partials": 0})


class RetirementTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for checkpoint retirement")
    def test_retire_requires_passed_collected_audited_baseline_and_contains_deletion(self):
        self.retirement_cases(("none", "failed", "boundary", "uncollected", "audit", "baseline", "public", "link"))

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for drifted checkpoint layouts")
    def test_retire_refuses_uninventoried_files_before_receipt_or_deletion(self):
        self.retirement_cases(("drift-root", "drift-session", "drift-generations",
                               "drift-layout", "drift-pointer", "drift-current"))

    def retirement_cases(self, faults):
        proof = r'''
param($Source,$Scratch,$Fault)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
foreach($name in @('Hash','ReadJson','SaveJson','Retire')){
    $node=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name},$true)
    if(-not $node){throw "missing retirement function: $name"}
    Invoke-Expression $node.Extent.Text
}
$utf8=[Text.UTF8Encoding]::new($false)
$Workspace=Join-Path $Scratch 'window';$baseline='unused';$journal=Join-Path $Workspace 'preparation.json'
$PublicInstallReceipt=Join-Path $Scratch 'public-install/receipt.json'
$Release='v0.18.1';$Candidate='1'*40;$Lane='rtx3090';$StateRoot=Join-Path $Scratch 'canonical'
function ValidateSnapshot($path){@{observable=@{active_release='instance'}}}
function Probe {@{}}
function AssertBaseline($value){if($Fault -eq 'baseline'){throw 'baseline differs'}}
$script:reads=0
function FreeBytes($path){$script:reads++;1000+$script:reads}
function Remove-Item {
    param($LiteralPath,[switch]$Recurse,[switch]$Force)
    $receipt=Join-Path $Workspace 'retirement.json'
    if(-not (Test-Path -LiteralPath $receipt)){throw 'deletion preceded the inventory'}
    $record=ReadJson $receipt
    if($record.status -cne 'recorded' -or @($record.generations).Count -ne 1 -or
       -not $record.generations[0].manifest_json -or -not $record.generations[0].checksums_json){
        throw 'deletion preceded generation metadata'
    }
    if(-not $LiteralPath.EndsWith('session-checkpoints-v3')){throw 'deletion escaped the checkpoint store'}
    Microsoft.PowerShell.Management\Remove-Item -LiteralPath $LiteralPath -Recurse:$Recurse -Force:$Force
}
try {
    Retire
    if($Fault -ne 'none'){throw 'unsafe retirement accepted'}
    'RETIRED'
} catch {
    if($Fault -eq 'none'){throw}
    if($_.Exception.Message -ceq 'unsafe retirement accepted'){throw}
    'REFUSED'
}
'''
        for first in (True, False):
            for fault in faults:
                with self.subTest(first=first, fault=fault), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    w = root / "window"
                    store = w / ("qualified-artifacts/lineage-root/cache/instance/session-checkpoints-v3"
                                 if first else "qualified-artifacts/cache/session-checkpoints-v3")
                    generation = store / "sessions" / ("a" * 64) / "generations/123456-1"
                    write_json(generation / "manifest.json", {"schema_version": 3, "synthetic": True})
                    write_json(generation / "checksums.json", {"engine/state/0.bin": "b" * 64})
                    (generation / "engine/state").mkdir(parents=True)
                    (generation / "engine/state/0.bin").write_bytes(b"synthetic checkpoint payload")
                    session = generation.parent.parent
                    (session / "current").write_text(generation.name, encoding="utf-8")
                    drift = {"drift-root": store / "untracked.bin",
                             "drift-session": session / "untracked.bin",
                             "drift-generations": generation.parent / "untracked.bin",
                             "drift-layout": store / "replacement-layout/payload.bin",
                             "drift-pointer": store / "sessions/not-a-digest/current",
                             "drift-current": store / "current"}.get(fault)
                    if fault == "drift-layout":
                        shutil.rmtree(store / "sessions")
                    if drift:
                        drift.parent.mkdir(parents=True, exist_ok=True)
                        drift.write_bytes(b"uninventoried checkpoint bytes")
                    before = {path.relative_to(store): path.read_bytes()
                              for path in store.rglob("*") if path.is_file()}
                    protected = root / "canonical/cache/instance/session-checkpoints-v3/untouched.bin"
                    protected.parent.mkdir(parents=True)
                    protected.write_bytes(b"canonical bytes")
                    unrelated = w / "qualified-artifacts/other/untouched.bin"
                    unrelated.parent.mkdir(parents=True)
                    unrelated.write_bytes(b"unrelated bytes")
                    write_json(w / "preparation.json", {"status": "restored", "lineage_mode": "first_release" if first else "upgrade"})
                    write_json(w / "window.json", {"status": "failed" if fault == "failed" else "passed_and_restored",
                               "first_failing_boundary": "native-probes" if fault == "boundary" else None,
                               "release": "v0.18.1", "candidate": "1" * 40, "restoration_status": "passed"})
                    write_json(w / "restoration.json", {"status": "passed"})
                    write_json(w / "final-audit.json", {"status": "failed" if fault == "audit" else "passed",
                               "checks": {"all_restored": fault != "audit"}})
                    if fault != "uncollected":
                        write_json(w / "collection.json", {"status": "collected", "release": "v0.18.1",
                                   "candidate": "1" * 40, "archive_sha256": "f" * 64,
                                   **{key + "_sha256": hashlib.sha256((w / name).read_bytes()).hexdigest()
                                      for key, name in (("window", "window.json"), ("final_audit", "final-audit.json"),
                                                        ("restoration", "restoration.json"))}})
                    write_json(root / "public-install/receipt.json", {
                        "artifact_type": "omp_ninfer_native_public_install_acceptance",
                        "status": "failed" if fault == "public" else "passed", "lane": "rtx3090",
                        "source": {"product_release": "v0.18.1", "candidate_commit": "1" * 40}})
                    if fault == "link":
                        (generation / "outside").symlink_to(protected.parent, target_is_directory=True)
                    script = root / "retire.ps1"
                    script.write_text(proof, encoding="utf-8")
                    result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(script),
                                             str(ROOT / "scripts/hosts/accept-rtx4090-route.ps1"), directory, fault],
                                            capture_output=True, text=True, encoding="utf-8", timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(protected.read_bytes(), b"canonical bytes")
                    self.assertEqual(unrelated.read_bytes(), b"unrelated bytes")
                    self.assertEqual(store.exists(), fault != "none")
                    receipt = w / "retirement.json"
                    if fault == "none":
                        record = json.loads(receipt.read_text(encoding="utf-8"))
                        self.assertEqual(record["status"], "retired")
                        self.assertEqual(record["free_bytes_before"], 1001)
                        self.assertEqual(record["free_bytes_after"], 1002)
                        self.assertEqual(len(record["generations"]), 1)
                        observed = record["generations"][0]
                        self.assertEqual(json.loads(observed["manifest_json"])["schema_version"], 3)
                        self.assertIn("engine/state/0.bin", json.loads(observed["checksums_json"]))
                        self.assertGreater(observed["bytes"], 0)
                        self.assertTrue(observed["path"].endswith("/generations/123456-1"))
                    else:
                        self.assertFalse(receipt.exists())
                        self.assertEqual({path.relative_to(store): path.read_bytes()
                                          for path in store.rglob("*") if path.is_file()}, before)

    def test_retire_cli_requires_collected_passed_window_before_host_contact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = ["accept-rtx4090-route.py", "--release", "v0.18.1", "--candidate", "1" * 40,
                       "--host", "fixture-host", "--workspace", directory, "--remote-workspace", "C:/acceptance",
                       "--expected-state-sha256", "2" * 64, "--first-release", "--mode", "retire",
                       "--public-install-receipt", "C:/public-install/receipt.json"]
            for status in ("failed", "passed_and_restored"):
                write_json(root / "driver-window.json", {"status": status})
                with mock.patch.object(sys, "argv", command), mock.patch.object(DRIVER, "ssh") as ssh:
                    with self.assertRaisesRegex(RuntimeError, "retire|collection"):
                        DRIVER.main()
                ssh.assert_not_called()

    def test_retire_cli_forwards_separate_public_install_receipt_and_collects_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "evidence"
            write_json(evidence / "window.json", {"status": "passed_and_restored"})
            write_json(evidence / "final-audit.json", {"status": "passed", "checks": {"restored": True}})
            write_json(evidence / "restoration.json", {"status": "passed"})
            write_json(evidence / "behavior-evidence.json", {"status": "passed", "checks": {"server_health_passed": True}})
            write_json(root / "driver-window.json", {"status": "passed_and_restored", "behavior_status": "passed",
                       "accept_exit": 0, "restoration_exit": 0, "audit_exit": 0})
            (root / "evidence.tar.gz").write_bytes(b"synthetic collected archive")
            write_json(root / "driver-collection.json", {"status": "collected", "release": "v0.18.1",
                       "candidate": "1" * 40, "archive_sha256": DRIVER.sha(root / "evidence.tar.gz"),
                       **{key + "_sha256": DRIVER.sha(evidence / name) for key, name in
                          (("window", "window.json"), ("final_audit", "final-audit.json"),
                           ("restoration", "restoration.json"))}})
            command = ["accept-rtx4090-route.py", "--release", "v0.18.1", "--candidate", "1" * 40,
                       "--host", "fixture-host", "--workspace", directory, "--remote-workspace", "C:/acceptance",
                       "--expected-state-sha256", "2" * 64, "--first-release", "--mode", "retire",
                       "--public-install-receipt", "C:/public-install/receipt.json"]
            result = subprocess.CompletedProcess([], 0, "", "")
            with mock.patch.object(sys, "argv", command), mock.patch.object(DRIVER, "ssh", return_value=result) as ssh, \
                    mock.patch.object(DRIVER, "run", return_value=result), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(DRIVER.main(), 0)
            self.assertIn("-Mode 'Retire'", ssh.call_args_list[0].args[1])
            self.assertIn("-PublicInstallReceipt 'C:/public-install/receipt.json'", ssh.call_args_list[0].args[1])
            self.assertEqual(len(ssh.call_args_list), 3)  # retire, collect, collection acknowledgement


class DocumentedModelTests(unittest.TestCase):
    """The route asks for the model its candidate's documented provider step configures, which is the
    model that candidate's native server serves. It keeps no lane table of its own (omp-ninfer#98):
    the scripts run from the operator's checkout against a frozen candidate."""

    def assert_request_log_command(self, command: str, request_log: Path) -> None:
        match = re.fullmatch(r"Get-Content -LiteralPath '((?:[^']|'')*)' -Encoding UTF8", command)
        self.assertIsNotNone(match, "Keep the exact log command, quoting and UTF8 encoding")
        actual = Path(match.group(1).replace("''", "'"))
        self.assertTrue(actual.is_absolute(), "The log command must use an absolute path")
        # resolve() expands Windows 8.3 aliases (and macOS /tmp) before comparing paths.
        self.assertEqual(actual.resolve(strict=True), request_log.resolve(strict=True))

    def test_request_log_command_normalizes_absolute_paths_without_weakening_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request_log = root / "operator's checkout with spaces" / "requests.jsonl"
            request_log.parent.mkdir()
            request_log.write_text("")
            (root / "alias").mkdir()
            alias = root / "alias" / ".." / request_log.parent.name / request_log.name
            for path in (request_log, request_log.resolve(), alias):
                escaped = str(path).replace("'", "''")
                self.assert_request_log_command(
                    f"Get-Content -LiteralPath '{escaped}' -Encoding UTF8", request_log
                )
            wrong_log = request_log.with_name("other.jsonl")
            wrong_log.write_text("")
            escaped = str(request_log).replace("'", "''")
            valid = f"Get-Content -LiteralPath '{escaped}' -Encoding UTF8"
            invalid = (
                valid.replace("Get-Content", "Get-Item"),
                valid.replace("-LiteralPath", "-Path"),
                valid.replace("UTF8", "ASCII"),
                valid + " -Raw",
                valid + "; Write-Output 'extra command'",
                valid.replace(escaped, str(wrong_log).replace("'", "''")),
                valid.replace(escaped, request_log.name),
            )
            for command in invalid:
                with self.subTest(command=command), self.assertRaises(AssertionError):
                    self.assert_request_log_command(command, request_log)

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

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for native probe dispatch")
    def test_native_probe_dispatch_keeps_c1_fleet_and_adds_c2_acceptance_and_stock_proofs(self):
        from test_native_candidate_policy import candidate_profile
        proof = r'''
param($Source,$Workspace,$Bundle,$Clone,$Lane,$Configuration)
$ErrorActionPreference='Stop'
$script:configuration=Get-Content -LiteralPath $Configuration -Raw
function py {
    if($args[1] -eq '-c') {Write-Output $script:configuration}
    else {[Console]::Out.WriteLine((ConvertTo-Json -Compress @($args|ForEach-Object {[string]$_})))}
    $global:LASTEXITCODE=0
}
& ([scriptblock]::Create([IO.File]::ReadAllText($Source))) -Mode NativeProbes -Lane $Lane -Release v0.16.0 -Candidate ('1'*40) -Workspace $Workspace -Bundle $Bundle -Clone $Clone -ExpectedStateSha256 ('2'*64) -TemporaryPrevious older -StateRoot (Join-Path $Workspace 'state') -KeyFile (Join-Path $Workspace 'key.txt') -RealHome (Join-Path $Workspace 'home')
'''
        for lane in ("rtx3090", "rtx4090"):
            with self.subTest(lane=lane), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                workspace, clone, bundle = root / "window", root / "clone", root / "bundle"
                workspace.mkdir()
                shutil.copy(ROOT / "scripts/hosts/native-gpu.ps1", workspace)
                (workspace / "key.txt").write_text("synthetic-key\n")
                (workspace / "route-home/.omp/agent").mkdir(parents=True)
                (workspace / "installed").mkdir()
                (workspace / "installed/requests.jsonl").write_text("")
                write_json(workspace / "state/state.json",
                           {"active_release": "candidate", "releases": {
                               "candidate": {"release_root": str(workspace / "installed")}}})
                _, _, configuration = candidate_profile(lane)
                write_json(root / "configuration.json", configuration)
                write_json(clone / "releases/v0.16.0/manifest.json",
                           {"components": {"omp": {"binary_sha256": "a" * 64, "distribution_version": "18.14.0"}}})
                shutil.copytree(ROOT / "examples/windows-native", clone / "examples/windows-native")
                documented_route.bundle(ROOT / "docs/QUICKSTART.md", f"{lane}-native", bundle)
                (root / "proof.ps1").write_text(proof)
                result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(root / "proof.ps1"),
                    str(ROOT / "scripts/hosts/accept-rtx4090-route.ps1"), str(workspace), str(bundle),
                    str(clone), lane, str(root / "configuration.json")],
                    capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                calls = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
                self.assertEqual(len(calls), 4 if lane == "rtx3090" else 1)
                self.assertTrue(calls[0][1].endswith("fleet_probe.py"))
                self.assertEqual(calls[0][calls[0].index("--branches") + 1], "4")
                self.assertEqual(calls[0][calls[0].index("--model") + 1], configuration["public_model_id"])
                log_command = calls[0][calls[0].index("--log-cmd") + 1]
                self.assertNotIn('"', log_command, "Windows PowerShell 5.1 strips native argv double quotes")
                self.assertTrue(log_command.startswith("powershell.exe -NoProfile -NonInteractive -EncodedCommand "))
                log_code = base64.b64decode(log_command.rsplit(" ", 1)[1]).decode("utf-16-le")
                self.assert_request_log_command(log_code, workspace / "installed/requests.jsonl")
                if lane == "rtx3090":
                    self.assertIn("accept-concurrency", calls[1])
                    self.assertEqual(calls[2][calls[2].index("--max-in-flight") + 1], "2")
                    self.assertEqual(calls[2][calls[2].index("--log-cmd") + 1], log_command)
                    self.assertEqual(calls[3][calls[3].index("--compactions") + 1], "2")


@unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed to run the orchestrator's statements")
class NativeCommandStatusTests(unittest.TestCase):
    """The orchestrator checks each native command's exit status (the omp-ninfer#100 item 7 class).
    Production statements run against PowerShell function fakes of git, the client and taskkill."""

    def run_proof(self, proof: str) -> object:
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "proof.ps1"
            script.write_text(proof)
            shutil.copy(ROOT / "scripts/hosts/native-gpu.ps1", directory)
            result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(script),
                                     str(ROOT / "scripts/hosts/accept-rtx4090-route.ps1"), directory],
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_preflight_refuses_an_unreadable_clone_or_a_failing_client(self) -> None:
        """A failed `git status --porcelain` printed nothing, which read as a clean candidate, and the
        client's --version and --help exit statuses were never read."""
        rows = self.run_proof(r'''
param($Source,$Scratch)
$ErrorActionPreference='Stop'
$text=[IO.File]::ReadAllText($Source)
function Statements($from,$to) {$start=$text.IndexOf($from);$text.Substring($start,$text.IndexOf($to,$start)-$start)}
$cloneCheck=Statements '    if(-not (Test-Path "$Clone\.git"))' '    $manifest=ReadJson'
$clientCheck=Statements '    $version=' '    $agent=Join-Path'
$Candidate='1'*40;$Clone=Join-Path $Scratch 'clone';$Workspace=$Scratch;$binary='omp-fixture'
New-Item -ItemType Directory -Force (Join-Path $Clone '.git')|Out-Null
function git {$global:LASTEXITCODE=0;if($args[2] -ceq $failing){$global:LASTEXITCODE=128}elseif($args[2] -ceq 'rev-parse'){$Candidate}}
function omp-fixture {$global:LASTEXITCODE=0;if($args[0] -ceq $failing){$global:LASTEXITCODE=1}else{'omp/0.0.0'}}
$rows=[ordered]@{}
foreach($failing in @('nothing','rev-parse','status','--version','--help')) {
  $rows[$failing]=@(foreach($check in @($cloneCheck,$clientCheck)) {
    try{Invoke-Expression $check;'accepted'}catch{'refused'}
  })
}
$rows|ConvertTo-Json -Compress
''')
        self.assertEqual(rows, {"nothing": ["accepted", "accepted"], "rev-parse": ["refused", "accepted"],
                                "status": ["refused", "accepted"], "--version": ["accepted", "refused"],
                                "--help": ["accepted", "refused"]})

    def test_a_timed_out_child_that_survives_taskkill_is_reported_running(self) -> None:
        """taskkill's exit status was ignored: a timed-out child it failed to stop was reported only as
        a timeout while the window went on to restore the host under it."""
        messages = self.run_proof(r'''
param($Source,$Scratch)
$ErrorActionPreference='Stop'
$text=[IO.File]::ReadAllText($Source)
$definitions=$text.Substring(0,$text.IndexOf('# Child isolation happens'))
$assertions=@'
function Start-Process {
  param($FilePath,$ArgumentList,[switch]$PassThru,$RedirectStandardOutput,$RedirectStandardError)
  # The child outlives its window; after taskkill it has exited only when $exits.
  $process=[pscustomobject]@{Handle=1;Id=4242;ExitCode=$null;Waits=0}
  $process|Add-Member ScriptMethod WaitForExit {param($milliseconds) $this.Waits++;$this.Waits -gt 1 -and $exits}
  $process|Add-Member ScriptMethod Refresh {}
  return $process
}
function taskkill.exe {$global:LASTEXITCODE=$killExit}
foreach($case in @(@(0,$true),@(128,$true),@(1,$false))) {
  $killExit,$exits=$case
  try{Child Route 1|Out-Null;'returned'}catch{$_.Exception.Message}
}
'@
$messages=@(& ([scriptblock]::Create($definitions+$assertions)) -Lane rtx3090 -Release v0.12.0 -Candidate ('1'*40) -Workspace $Scratch -Bundle $Scratch -Clone $Scratch -ExpectedStateSha256 ('2'*64) -TemporaryPrevious older -StateRoot (Join-Path $Scratch 'state') -RealHome (Join-Path $Scratch 'home'))
ConvertTo-Json -Compress $messages
''')
        # Stopped by taskkill, or already gone when it ran (taskkill exit 128): a plain timeout.
        self.assertEqual(messages[:2], ["Route child timeout; restore now"] * 2)
        self.assertIn("still runs", messages[2])


@unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for native install restoration")
class NativePublicInstallRestorationTests(unittest.TestCase):
    """Run the production smoke/finalization statements against an isolated controller."""

    def test_failed_stop_or_smoke_never_claims_restoration_or_leaks_an_owned_start(self) -> None:
        source = (ROOT / "scripts/hosts/accept-native-public-install.ps1").read_text()
        proof = r'''
param($Source,$Scratch,$Case)
$ErrorActionPreference='Stop'
$controller=Join-Path $Scratch 'controller.ps1'
$state=Join-Path $Scratch 'state.json'
$running=$Case -in @('running-smoke-failure','stale-native-exit')
[IO.File]::WriteAllText($state,(@{running=$running;case=$Case;calls=@()}|ConvertTo-Json))
[IO.File]::WriteAllText($controller,@'
param($Action,$StateRoot)
$path=Join-Path $StateRoot 'state.json'
$state=Get-Content $path -Raw|ConvertFrom-Json
$state.calls=@($state.calls)+$Action
if($Action -eq 'Start'){$state.running=$true}
if($Action -eq 'Stop'){
    if($state.case -eq 'failed-stop'){throw 'injected Stop failure'}
    if($state.case -ne 'stop-returns-running'){$state.running=$false}
}
[IO.File]::WriteAllText($path,($state|ConvertTo-Json))
if($Action -eq 'Stop') {
    $global:LASTEXITCODE=if($state.case -eq 'stop-native-exit'){7}else{0}
}
if($Action -eq 'Status') {
    @{process_state=$(if($state.running){'running'}else{'stopped'});endpoint_state=$(if($state.running){'ready'}else{'unavailable'});release_id='candidate'}|ConvertTo-Json -Compress
}
'@)
$StateRoot=$Scratch
$ReceiptPath=Join-Path $Scratch 'receipt.json'
$key=Join-Path $Scratch 'key'
$config=Join-Path $Scratch 'config.json'
[IO.File]::WriteAllText($key,'synthetic-key')
[IO.File]::WriteAllText($config,'{"model_id":"fixture-model"}')
$rel=@{api_key_file=$key;config_file=$config;host='127.0.0.1';port=18082}
$nativeModel=@{artifact_sha256='c'*64}
$installedBinary='a'*64;$installedConfig='b'*64;$gpuUuid='fixture-gpu'
function Get-NativeGpuPowerLimit {param($Uuid) 450}
function Invoke-RestMethod {
    param($Method,$Uri,$Headers,$TimeoutSec,[switch]$UseBasicParsing,$ContentType,$Body)
    if($Case -in @('throw-after-start','running-smoke-failure')){throw 'injected smoke failure'}
    if($Method -eq 'Get'){return @{identity=@{binary_sha256='a'*64;config_sha256='b'*64;model_artifact_sha256='c'*64};runtime=@{speculative_backend='dflash2'}}}
    return @{choices=@(@{message=@{content='ACCEPTED'}});usage=@{completion_tokens=1}}
}
function Invoke-WebRequest {
    param($Method,$Uri,$TimeoutSec,[switch]$UseBasicParsing)
    $error=[Exception]::new('anonymous refusal')
    $error|Add-Member NoteProperty Response ([pscustomobject]@{StatusCode=401})
    throw $error
}
$text=[IO.File]::ReadAllText($Source)
$start=$text.IndexOf('function Sha(')
$end=$text.IndexOf("`ntry {`n",$start)+1
$definitions=$text.Substring($start,$end-$start)
$smoke=$text.Substring($text.IndexOf('    # 5. Smoke'))
Remove-Variable LASTEXITCODE -Scope Global -ErrorAction SilentlyContinue
if($Case -eq 'stale-native-exit'){$global:LASTEXITCODE=7}
& ([scriptblock]::Create($definitions+"try {`n"+$smoke))
'''
        self.assertIn("# 5. Smoke", source)
        for case in ("failed-stop", "stop-returns-running", "stop-native-exit", "throw-after-start",
                     "running-smoke-failure", "passed", "stale-native-exit"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                script = root / "proof.ps1"
                script.write_text(proof)
                result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(script),
                                         str(ROOT / "scripts/hosts/accept-native-public-install.ps1"),
                                         directory, case], capture_output=True, text=True, timeout=30)
                receipt = json.loads((root / "receipt.json").read_text())
                state = json.loads((root / "state.json").read_text())
                if case in ("passed", "stale-native-exit"):
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(receipt["status"], "passed")
                    self.assertEqual(state["running"], case == "stale-native-exit")
                    self.assertTrue(receipt["restoration"]["prior_state_restored"])
                    if case == "stale-native-exit":
                        self.assertNotIn("Stop", state["calls"])
                elif case in ("failed-stop", "stop-returns-running", "stop-native-exit"):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(receipt["status"], "failed")
                    self.assertFalse(receipt["restoration"]["prior_state_restored"])
                    message = {"failed-stop": "injected Stop failure",
                               "stop-returns-running": "baseline was not restored",
                               "stop-native-exit": "public-install controller Stop failed"}[case]
                    self.assertIn(message, receipt["restoration_error"])
                    if case == "stop-native-exit":
                        self.assertFalse(state["running"])
                        self.assertEqual(state["calls"][-1], "Stop")
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(receipt["status"], "failed")
                    self.assertEqual(state["running"], case == "running-smoke-failure")
                    if case == "running-smoke-failure":
                        self.assertNotIn("Stop", state["calls"], "an incumbent start is never ours to stop")
                    else:
                        self.assertIn("Stop", state["calls"])


if __name__ == "__main__":
    unittest.main()
