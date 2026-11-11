"""Lost Hold acknowledgements reconcile only the receipt-owning Windows window."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "hold_routes", ROOT / "scripts/hosts/accept-rtx5090-routes.py")
DRIVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER)


class LostAcknowledgementTests(unittest.TestCase):
    def test_lost_acknowledgement_probes_ownership_before_continuing(self):
        win = mock.Mock(side_effect=[TimeoutError("lost acknowledgement"), '{"status":"owned"}'])
        DRIVER.acquire_windows_hold(win)
        self.assertEqual(win.call_args_list, [
            mock.call("Hold"), mock.call("HoldStatus", capture=True)])

    def test_absent_foreign_or_unreachable_hold_never_authorizes_restoration(self):
        for probe in ('{"status":"absent"}', '{"status":"foreign"}', TimeoutError("unreachable")):
            with self.subTest(probe=probe):
                win = mock.Mock(side_effect=[TimeoutError("lost acknowledgement"), probe])
                with self.assertRaisesRegex(TimeoutError, "lost acknowledgement"):
                    DRIVER.acquire_windows_hold(win)
                self.assertFalse(any(call.args[0] == "Release" for call in win.call_args_list))

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for Windows hold reconciliation")
    def test_repeated_hold_and_release_refuse_replaced_or_foreign_ownership(self):
        proof = r'''
param($Source,$Scratch)
$ErrorActionPreference='Stop'
$script=[scriptblock]::Create([IO.File]::ReadAllText($Source))
function Get-ScheduledTask {@()}
function Invoke-WebRequest {param([switch]$UseBasicParsing,$Uri,$TimeoutSec) @{StatusCode=200;Content='{"status":"ok"}'}}
function Invoke-RestMethod {param($Uri,$TimeoutSec) @{status='ok'}}
function Get-ExecutionPolicy {param([switch]$List) @()}
function Get-Acl {param($Path,$LiteralPath) @{Sddl='fixture-acl'}}
$root=Join-Path $Scratch 'control';$workspace=Join-Path $Scratch 'window'
New-Item -ItemType Directory -Force "$root/bin",$workspace|Out-Null
Set-Content "$root/bin/windows-host-common.ps1" 'function Set-OmpAdminOnlyFile {param($Path)}'
$env:LOCALAPPDATA=Join-Path $Scratch 'client'
$arguments=@{Workspace=$workspace;Release='v0.18.0';Candidate=('1'*40);ControlRoot=$root}
$null=& $script -Action Hold @arguments
$baseline=[IO.File]::ReadAllText("$workspace/windows-baseline.json")
$ownership=[IO.File]::ReadAllText("$workspace/own-hold.json")
$null=& $script -Action Hold @arguments
if([IO.File]::ReadAllText("$workspace/windows-baseline.json") -cne $baseline){throw 'repeated Hold rewrote baseline'}
if([IO.File]::ReadAllText("$workspace/own-hold.json") -cne $ownership){throw 'repeated Hold rewrote ownership'}
$probe=(& $script -Action HoldStatus @arguments)|ConvertFrom-Json
if($probe.status -cne 'owned'){throw 'own hold was not reconciled'}
$hold=Join-Path $root 'state/lane-container-paused'
[IO.File]::WriteAllText($hold,'foreign replacement')
$probe=(& $script -Action HoldStatus @arguments)|ConvertFrom-Json
if($probe.status -cne 'foreign'){throw 'foreign replacement claimed as owned'}
foreach($action in @('Hold','Release')){
    $refused=$false
    try {$null=& $script -Action $action @arguments} catch {$refused=$true}
    if(-not $refused){throw "foreign $action was accepted"}
    if([IO.File]::ReadAllText($hold) -cne 'foreign replacement'){throw 'foreign hold was touched'}
}
'passed'
'''
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "proof.ps1"
            script.write_text(proof, encoding="utf-8")
            result = subprocess.run(
                [shutil.which("pwsh"), "-NoProfile", "-File", str(script),
                 str(ROOT / "scripts/hosts/accept-windows-client.ps1"), directory],
                capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.strip(), "passed")


if __name__ == "__main__":
    unittest.main()
