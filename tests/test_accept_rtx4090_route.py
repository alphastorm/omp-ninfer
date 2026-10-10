"""Native route acceptance binds the selected lane and accounts for every documented request."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("accept_rtx4090_route",
                                              ROOT / "scripts" / "hosts" / "accept-rtx4090-route.py")
assert SPEC is not None and SPEC.loader is not None
DRIVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER)


def completed(*tool_calls: int) -> list[dict]:
    return [{"result": {"tool_call_count": count}} for count in tool_calls]


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
    def test_powershell_baseline_enforces_each_lanes_power_and_hold(self) -> None:
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
$assertions=@'
$p=@{state_sha256=$ExpectedStateSha256;prepared_release=$null;task_state='Ready';processes=@();listeners=@();lease_present=$false;lease_entries=@();power_limit_w=$ownerPowerLimit}
New-Item -ItemType Directory -Force $StateRoot|Out-Null
@{active_release='active';previous_release='previous';releases=@{older=@{}}}|ConvertTo-Json -Depth 5|Set-Content "$StateRoot/state.json"
if($Lane -eq 'rtx4090') {
  $rejected=$false;try{AssertBaseline $p}catch{$rejected=$true}
  if(-not $rejected){throw '4090 accepted a missing required hold'}
  New-Item -ItemType Directory -Force $HostState|Out-Null
  New-Item -ItemType File -Force "$HostState/container-host-paused"|Out-Null
}
AssertBaseline $p
$p.power_limit_w=if($Lane -eq 'rtx3090'){450}else{370}
$rejected=$false;try{AssertBaseline $p}catch{$rejected=$true}
if(-not $rejected){throw 'other lane power limit was accepted'}
@{lane=$Lane;root=$StateRoot;task=$TaskName;power=$ownerPowerLimit;selector=$selector}
'@
$results=@(foreach($lane in @('rtx3090','rtx4090')) {
  & ([scriptblock]::Create($definitions+$assertions)) -Lane $lane -Release v0.9.1 -Candidate ('1'*40) -Workspace C:/window -Bundle C:/bundle -Clone C:/clone -ExpectedStateSha256 ('2'*64) -TemporaryPrevious older -RealHome C:/home
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
            self.assertEqual(rows["rtx3090"]["selector"], "ninfer-native-3090/q38-ninfer")
            self.assertEqual(rows["rtx4090"]["power"], 450)
            self.assertEqual(rows["rtx4090"]["selector"], "ninfer-native-4090/qwen3.8-27b")

    def test_dry_run_preserves_4090_default_and_requires_3090_host(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "not-created"
            command = [sys.executable, str(ROOT / "scripts/hosts/accept-rtx4090-route.py"),
                       "--release", "v0.9.1", "--candidate", "1" * 40, "--workspace", str(workspace),
                       "--remote-workspace", "C:/acceptance", "--expected-state-sha256", "2" * 64,
                       "--temporary-previous", "previous", "--mode", "dry-run"]
            default = subprocess.run(command, capture_output=True, text=True)
            explicit = subprocess.run(command + ["--lane", "rtx4090"], capture_output=True, text=True)
            self.assertEqual(default.returncode, 0, default.stderr)
            self.assertEqual(default.stdout, explicit.stdout)
            missing_host = subprocess.run(command + ["--lane", "rtx3090"], capture_output=True, text=True)
            self.assertEqual(missing_host.returncode, 2)
            selected = subprocess.run(command + ["--lane", "rtx3090", "--host", "fixture-host"],
                                      capture_output=True, text=True)
            self.assertEqual(selected.returncode, 0, selected.stderr)
            self.assertEqual(json.loads(selected.stdout)["plan"]["client_install"]["lane"], "rtx3090-native")
            self.assertFalse(workspace.exists())
            unknown = subprocess.run(command + ["--lane", "rtx5090"], capture_output=True, text=True)
            self.assertEqual(unknown.returncode, 2)

    def test_assessor_binds_3090_model_route_and_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence, clone, bundle = root / "evidence", root / "clone", root / "bundle"
            def save(path, value):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value))
            candidate = "1" * 40
            identity = {"binary_sha256": "a" * 64, "config_sha256": "b" * 64,
                        "model_artifact_sha256": "c" * 64, "patch_stack_sha": "d" * 40,
                        "source_dirty": False}
            variant = {"id": "rtx3090-windows-native", "server_binary_sha256": "a" * 64,
                       "configuration_sha256": "b" * 64, "model_artifact_sha256": "c" * 64,
                       "source_commit": "d" * 40, "package_sha256": "e" * 64}
            save(clone / "releases/v0.9.1/manifest.json", {"components": {"ninfer_variants": [variant]}})
            slugs = ["client-install", "clone-and-verify", "variant", "stage-and-install", "operate", "provider", "acceptance"]
            steps = [{"slug": slug, "status": "passed", "sha256": "f" * 64,
                      "block_sha256": "f" * 64, "executed_sha256": "f" * 64,
                      "substitution": candidate if slug == "clone-and-verify" else None} for slug in slugs]
            route = {"lane": "rtx3090-native", "status": "passed", "clone_commit": candidate,
                     "document_sha256": "0" * 64, "steps": steps, "completed_utc": "2026-01-01T01:00:00Z"}
            save(bundle / "manifest.json", {"lane": "rtx3090-native", "document_sha256": "0" * 64, "steps": steps})
            save(evidence / "route.json", route)
            save(evidence / "recovery-health.json", {"status_code": 200})
            save(evidence / "recovery-status.json", {"process_state": "running", "endpoint_state": "ready",
                                                       "server": {"status": "ok", "identity": identity}})
            save(evidence / "installed-identity.json", {"package_sha256": "e" * 64})
            for name in ("restoration", "final-audit"):
                save(evidence / f"{name}.json", {"status": "passed"})
            live = {"typed_read_tool_calls": 1, "linked_tool_results": 1,
                    **{key: True for key in ("tool_result_marker", "exact_visible_final_answer", "agent_end",
                                             "continuation_exact_nonce", "runtime_identity_bound")},
                    "fail_closed": {"exit_code": 1, "no_model_response": True, "only_selected_local_provider_observed": True}}
            save(evidence / "structured/receipt.json", {"status": "passed", "live_acceptance": live})
            (evidence / "route.stdout.log").write_text("OMP_NINFER_TOOL_OK\n493817-205361\n")
            requests = [{"event": "request_done", "request": {"request_id": str(i), "model": "q38-ninfer",
                         "has_tool_history": i == 1}, "result": {"tool_call_count": int(i == 0)}} for i in range(4)]
            (evidence / "documented-requests.jsonl").write_text("\n".join(map(json.dumps, requests)))
            logs = [{"timestamp": "2026-01-01T00:00:00Z", "provider": "ninfer-native-3090", "model": "q38-ninfer",
                     "message": "agent_end maintenance routing", "stopReason": "error", "contentBlocks": 0,
                     "hasText": False, "hasToolCalls": False},
                    {"timestamp": "2026-01-01T00:00:00Z", "message": "agent turn ended with provider error"}]
            log_dir = evidence / "route-client-logs"
            log_dir.mkdir()
            (log_dir / "client.log").write_text("\n".join(map(json.dumps, logs)))
            result = DRIVER.assess_evidence(evidence, clone, bundle, "v0.9.1", candidate, "rtx3090")
            self.assertEqual(result["status"], "passed", result["checks"])
            route["lane"] = "rtx4090-native"
            save(evidence / "route.json", route)
            requests[0]["request"]["model"] = "qwen3.8-27b"
            (evidence / "documented-requests.jsonl").write_text("\n".join(map(json.dumps, requests)))
            save(evidence / "installed-identity.json", {"package_sha256": "9" * 64})
            result = DRIVER.assess_evidence(evidence, clone, bundle, "v0.9.1", candidate, "rtx3090")
            self.assertEqual(result["status"], "failed")
            self.assertFalse(result["checks"]["runner_passed"])
            self.assertFalse(result["checks"]["only_expected_server_model"])
            self.assertFalse(result["checks"]["installed_package_bound"])


if __name__ == "__main__":
    unittest.main()
