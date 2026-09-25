#!/usr/bin/env python3
"""Stage, preflight, run and collect a bounded Windows native-route acceptance.

Dry-run performs no network or filesystem mutations. Preflight changes only private
workspaces, anonymously downloads pinned assets, and tests the on-host restoration
snapshot. Accept requires that preflight; its independent SSH restoration leg runs
in finally even when the acceptance child or the original transport fails. Never
collect preserved secrets, runtime caches, or credential files from the host.
"""
from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def quote(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(argv: list[str], *, cwd: Path | None = None, timeout: int = 120,
        log: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    if log:
        with log.open("w", encoding="utf-8") as output:
            result = subprocess.run(argv, cwd=cwd, stdout=output, stderr=subprocess.STDOUT,
                                    text=True, timeout=timeout)
    else:
        result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f"{argv[0]} failed ({result.returncode}); inspect {log or 'private command output'}")
    return result


def ssh(host: str, code: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
    encoded = base64.b64encode(code.encode("utf-16le")).decode("ascii")
    return run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", host,
                "powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded], **kwargs)


def private_text(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Earlier native Windows probes used the platform default for private captures.
        # Preserve those bytes and decode losslessly, never silently replace characters.
        return data.decode("cp1252")


def assess_evidence(evidence: Path, clone: Path, bundle: Path, release: str, candidate: str) -> dict[str, object]:
    def load(name: str) -> dict:
        return json.loads(private_text(evidence / name))

    def rows(path: Path) -> list[dict]:
        parsed = []
        for line in private_text(path).splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict):
                parsed.append(row)
        return parsed

    manifest = json.loads((clone / "releases" / release / "manifest.json").read_text())
    expected = next(v for v in manifest["components"]["ninfer_variants"] if v["id"] == "rtx4090-windows-native")
    blocks = json.loads((bundle / "manifest.json").read_text())
    route = load("route.json")
    health, recovery, installed = load("recovery-health.json"), load("recovery-status.json"), load("installed-identity.json")
    identity = recovery["server"]["identity"]
    output = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", private_text(evidence / "route.stdout.log"))
    lines = [line.strip() for line in output.splitlines()]
    requests = rows(evidence / "documented-requests.jsonl")
    completed = [row for row in requests if row.get("event") == "request_done"]
    rejected = [row for row in requests if row.get("error")]
    logs = [row for path in (evidence / "route-client-logs").rglob("*.log") for row in rows(path)]
    route_end = datetime.datetime.fromisoformat(route["completed_utc"].replace("Z", "+00:00"))
    # Exclude the additional structured probe from documented-route observations.
    logs = [row for row in logs if row.get("timestamp") and
            datetime.datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")) <= route_end]
    responses = [row for row in logs if row.get("message") == "agent_end maintenance routing"]
    offline = [row for row in responses if row.get("stopReason") == "error"]
    provider_errors = [row for row in logs if row.get("message") == "agent turn ended with provider error"]
    structured = load("structured/receipt.json")
    live = structured["live_acceptance"]
    checks = {
        "runner_passed": route["status"] == "passed" and route["clone_commit"] == candidate,
        "document_hash_matched": route["document_sha256"] == blocks["document_sha256"],
        "seven_steps_hash_matched": len(route["steps"]) == 7 and all(
            r["block_sha256"] == r["executed_sha256"] == b["sha256"] and
            r["status"] in ("passed", "substituted") for r, b in zip(route["steps"], blocks["steps"])),
        "clone_override_recorded": candidate in (route["steps"][1]["substitution"] or ""),
        # The documented prompt asks to report the line, not to omit surrounding prose.
        # The separate structured probe requires the entire visible final answer exactly.
        "exact_tool_marker": bool(re.search(r"(?<![A-Z0-9_])OMP_NINFER_TOOL_OK(?![A-Z0-9_])", output)),
        "exact_continuation_nonce": "COBALT-493817" in lines,
        "one_server_tool_call": sum(row["result"].get("tool_call_count", 0) for row in completed) == 1,
        "linked_tool_history": any(row["request"].get("has_tool_history") for row in completed),
        "four_completed_requests": len(completed) == 4,
        "only_expected_server_model": bool(completed) and all(row["request"]["model"] == "qwen3.8-27b" for row in completed),
        "only_local_client_responses": bool(responses) and all(
            row.get("provider") == "ninfer-native-4090" and row.get("model") == "qwen3.8-27b" for row in responses),
        "offline_failed_without_response": bool(offline) and bool(provider_errors) and all(
            row.get("contentBlocks") == 0 and row.get("hasText") is False and row.get("hasToolCalls") is False for row in offline),
        "only_known_local_compatibility_errors": all(row["error"].get("code") == "reasoning_effort_not_supported" for row in rejected),
        "recovered_healthy": health["status_code"] == 200 and recovery["process_state"] == "running" and recovery["endpoint_state"] == "ready" and recovery["server"]["status"] == "ok",
        "served_identity_bound": identity["binary_sha256"] == expected["server_binary_sha256"] and
            identity["config_sha256"] == expected["configuration_sha256"] and
            identity["model_artifact_sha256"] == expected["model_artifact_sha256"] and
            identity["patch_stack_sha"] == expected["source_commit"] and identity["source_dirty"] is False,
        "installed_package_bound": installed["package_sha256"] == expected["package_sha256"],
        "structured_live_and_outage_passed": structured["status"] == "passed" and
            live["typed_read_tool_calls"] == 1 and live["linked_tool_results"] == 1 and
            all(live[key] for key in ("tool_result_marker", "exact_visible_final_answer", "agent_end", "continuation_exact_nonce", "runtime_identity_bound")) and
            live["fail_closed"]["exit_code"] != 0 and live["fail_closed"]["no_model_response"] and live["fail_closed"]["only_selected_local_provider_observed"],
        "restoration_passed": load("restoration.json")["status"] == "passed" and load("final-audit.json")["status"] == "passed",
    }
    behavior = {"status": "passed" if all(checks.values()) else "failed", "checks": checks,
                "document_sha256": blocks["document_sha256"], "served_identity": identity,
                "package_sha256": installed["package_sha256"],
                "documented_marker_bare_line": "OMP_NINFER_TOOL_OK" in lines,
                "request_summaries": [{"request_id": row["request"]["request_id"],
                    "model": row["request"]["model"], "has_tool_history": row["request"]["has_tool_history"],
                    "tool_call_count": row["result"]["tool_call_count"],
                    "prefix_reuse_path": row["result"].get("prefix_reuse_path")} for row in completed],
                "local_compatibility_errors": [row["error"] for row in rejected],
                "offline_provider_errors": [{key: row.get(key) for key in ("provider", "model", "errorMessage")} for row in provider_errors],
                "live_acceptance": live}
    (evidence / "behavior-evidence.json").write_text(json.dumps(behavior, indent=2) + "\n")
    return behavior


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--release", required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--remote-workspace", required=True)
    p.add_argument("--host", default="sf-pc")
    p.add_argument("--clone", type=Path)
    p.add_argument("--bundle", type=Path)
    p.add_argument("--expected-state-sha256", required=True)
    p.add_argument("--temporary-previous", required=True)
    p.add_argument("--attempt", type=int, choices=(1, 2), default=1)
    p.add_argument("--window-minutes", type=int, choices=range(15, 46), default=45)
    p.add_argument("--mode", choices=("dry-run", "preflight", "validate", "accept", "restore", "collect"), default="dry-run")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", a.candidate):
        p.error("candidate must be an exact commit")
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", a.release):
        p.error("release must be vX.Y.Z")
    if not re.fullmatch(r"[0-9a-f]{64}", a.expected_state_sha256):
        p.error("expected state must be a SHA-256")
    w = a.workspace.resolve()
    clone = (a.clone or w / "candidate").resolve()
    bundle = (a.bundle or w / "bundle").resolve()
    remote = a.remote_workspace.rstrip("\\/")
    if not re.match(r"^[A-Za-z]:[\\/]", remote):
        p.error("remote workspace must be an absolute Windows path")
    scripts = Path(__file__).resolve().parent
    orchestrator = scripts / "accept-rtx4090-route.ps1"
    probe = scripts / "omp-client-probe.py"
    plan = {"release": a.release, "candidate": a.candidate, "mode": a.mode,
            "host": a.host, "workspace": str(w), "remote_workspace": remote,
            "clone": str(clone), "bundle": str(bundle), "attempt": a.attempt,
            "window_minutes": a.window_minutes,
            "client_install": {"lane": "rtx4090-native", "step": "client-install",
                               "launcher": r"$env:LOCALAPPDATA\OMP\omp.exe",
                               "distribution_kind": "upstream-release"},
            "restoration": "on-host finally plus independent SSH Restore leg",
            "collection_excludes": ["preserved", "qualified-artifacts", "*-home", "*-temp", "assets", "baseline/files"],
            "scripts": [str(orchestrator), str(probe)]}
    if a.mode == "dry-run" or a.dry_run:
        print(json.dumps({"status": "passed", "canonical_mutations": 0, "plan": plan}, indent=2))
        return 0
    os.umask(0o077)
    w.mkdir(parents=True, exist_ok=True)
    os.chmod(w, 0o700)
    remote_clone = remote + "\\candidate"
    params = {"Release": a.release, "Candidate": a.candidate, "Workspace": remote,
              "Bundle": remote + "\\bundle", "Clone": remote_clone,
              "ExpectedStateSha256": a.expected_state_sha256, "TemporaryPrevious": a.temporary_previous,
              "Attempt": a.attempt, "WindowMinutes": a.window_minutes}

    def invoke(mode: str, name: str, timeout: int, check: bool = True) -> subprocess.CompletedProcess[str]:
        arguments = " ".join("-" + key + " " + quote(value) for key, value in {**params, "Mode": mode}.items())
        code = "$ProgressPreference='SilentlyContinue'; & ([scriptblock]::Create([IO.File]::ReadAllText(" + quote(remote + "\\accept-rtx4090-route.ps1") + "))) " + arguments
        return ssh(a.host, code, log=w / name, timeout=timeout, check=check)

    def collect() -> None:
        # Only explicit public-identity receipts and private prompt/output logs. Never export
        # arbitrary workspace trees: preserved original and newly installed keys stay on-host.
        code = r"""$ErrorActionPreference='Stop';$w=WORKSPACE;$out=Join-Path $w 'collected';
New-Item -ItemType Directory -Force $out|Out-Null;
foreach($f in @(Get-ChildItem $w -File|Where-Object {$_.Extension -in @('.json','.jsonl','.log','.txt')})) {Copy-Item $f.FullName $out -Force};
foreach($name in @('structured','client-logs')) {if(Test-Path (Join-Path $w $name)){Copy-Item (Join-Path $w $name) $out -Recurse -Force}};
if(Test-Path (Join-Path $w 'route-home\.omp\logs')) {Copy-Item (Join-Path $w 'route-home\.omp\logs') (Join-Path $out 'route-client-logs') -Recurse -Force};
foreach($name in @('baseline','preflight-snapshot')) {if(Test-Path (Join-Path $w ($name+'\snapshot.json'))){Copy-Item (Join-Path $w ($name+'\snapshot.json')) (Join-Path $out ($name+'-snapshot.json')) -Force}};
& tar.exe -czf (Join-Path $w 'evidence.tar.gz') -C $out .;if($LASTEXITCODE -ne 0){throw 'evidence archive failed'}
""".replace("WORKSPACE", quote(remote))
        ssh(a.host, code, log=w / "collection.log", timeout=120)
        run(["scp", "-q", a.host + ":" + remote.replace("\\", "/") + "/evidence.tar.gz", str(w / "evidence.tar.gz")], timeout=120)
        destination = w / "evidence"
        destination.mkdir(exist_ok=True)
        run(["tar", "-xzf", str(w / "evidence.tar.gz"), "-C", str(destination)], timeout=60)

    if a.mode == "preflight":
        if not clone.exists():
            run(["git", "clone", "--quiet", "https://github.com/alphastorm/omp-ninfer.git", str(clone)], timeout=180)
            run(["git", "-C", str(clone), "checkout", "--quiet", a.candidate])
        if run(["git", "-C", str(clone), "rev-parse", "HEAD"]).stdout.strip() != a.candidate:
            raise RuntimeError("clone commit differs from frozen candidate")
        if run(["git", "-C", str(clone), "status", "--porcelain"]).stdout.strip():
            raise RuntimeError("candidate clone must be clean")
        if not bundle.exists():
            run([sys.executable, str(clone / "scripts/documented_route.py"), "bundle", "--lane", "rtx4090-native", "--output", str(bundle)])
        manifest = json.loads((bundle / "manifest.json").read_text())
        if manifest["document_sha256"] != sha(clone / manifest["document"]):
            raise RuntimeError("bundle document differs from clean clone")
        if len(manifest["steps"]) != 7 or any(sha(bundle / step["file"]) != step["sha256"] for step in manifest["steps"]):
            raise RuntimeError("documented block bytes differ")
        ssh(a.host, "$ErrorActionPreference='Stop';New-Item -ItemType Directory -Force " + quote(remote) + "|Out-Null", timeout=30)
        run(["scp", "-q", str(orchestrator), str(probe), str(clone / "scripts/hosts/run-documented-route.ps1"),
             a.host + ":" + remote.replace("\\", "/") + "/"], timeout=60)
        run(["scp", "-qr", str(bundle), a.host + ":" + remote.replace("\\", "/") + "/"], timeout=60)
        parse = "$t=$null;$e=$null;[Management.Automation.Language.Parser]::ParseFile(" + quote(remote + "\\accept-rtx4090-route.ps1") + ",[ref]$t,[ref]$e)|Out-Null;if($e.Count){$e|ConvertTo-Json;exit 1};'PARSE_OK'"
        ssh(a.host, parse, log=w / "powershell-parse.log", timeout=30)
        invoke("Preflight", "preflight-driver.log", 1200)
        invoke("DryRun", "restoration-dry-run.json", 120)
        collect()
        (w / "driver-preflight.json").write_text(json.dumps({"status": "passed", "plan": plan,
            "orchestrator_sha256": sha(orchestrator), "probe_sha256": sha(probe),
            "document_sha256": manifest["document_sha256"], "steps": manifest["steps"]}, indent=2) + "\n")
    elif a.mode == "validate":
        # Revalidate changed orchestration without repeating a successful installation/download.
        preflight = json.loads((w / "driver-preflight.json").read_text())
        if preflight["plan"]["candidate"] != a.candidate:
            raise RuntimeError("candidate changed since preflight")
        run(["scp", "-q", str(orchestrator), str(probe),
             a.host + ":" + remote.replace("\\", "/") + "/"], timeout=60)
        code = r"""$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';$w=WORKSPACE;
$t=$null;$e=$null;[Management.Automation.Language.Parser]::ParseFile((Join-Path $w 'accept-rtx4090-route.ps1'),[ref]$t,[ref]$e)|Out-Null;if($e.Count){throw 'orchestrator parse failed'};
$h=Join-Path $w 'preflight-home';Set-Variable HOME $h -Scope Global -Force;$env:HOME=$h;$env:USERPROFILE=$h;$env:LOCALAPPDATA=Join-Path $h 'AppData\Local';$env:APPDATA=Join-Path $h 'AppData\Roaming';
$binary=Join-Path $env:LOCALAPPDATA 'OMP\omp.exe';if(-not (Test-Path $binary -PathType Leaf)){throw 'isolated binary missing'};
& py -3 (Join-Path $w 'omp-client-probe.py') --release RELEASE --candidate CANDIDATE --phase preflight --output (Join-Path $w 'structured') --binary $binary --clone (Join-Path $w 'candidate') --platform windows-x64 --profile windows-docker-local --provider ninfer-native-4090 --model ninfer-native-4090/qwen3.8-27b --endpoint http://127.0.0.1:18082/v1;exit $LASTEXITCODE
""".replace("WORKSPACE", quote(remote)).replace("RELEASE", quote(a.release)).replace("CANDIDATE", quote(a.candidate))
        ssh(a.host, code, log=w / "preflight-revalidation.log", timeout=120)
        invoke("DryRun", "restoration-dry-run.json", 120)
        preflight["orchestrator_sha256"] = sha(orchestrator)
        preflight["probe_sha256"] = sha(probe)
        (w / "driver-preflight.json").write_text(json.dumps(preflight, indent=2) + "\n")
        collect()
    elif a.mode == "accept":
        preflight = json.loads((w / "driver-preflight.json").read_text())
        if preflight["plan"]["candidate"] != a.candidate or preflight["orchestrator_sha256"] != sha(orchestrator) or preflight["probe_sha256"] != sha(probe):
            raise RuntimeError("preflighted script or candidate changed; stage and exercise preflight again before acceptance")
        if (w / "driver-window.json").exists():
            raise RuntimeError("acceptance attempt already spent; use a new workspace for one authorized correction")
        start = time.time()
        result: dict[str, object] = {"status": "running", "started_unix": start, "plan": plan}
        (w / "driver-window.json").write_text(json.dumps(result, indent=2) + "\n")
        try:
            accepted = invoke("Accept", "window-driver.log", a.window_minutes * 60, check=False)
            result["accept_exit"] = accepted.returncode
        except Exception as exc:
            result["transport_error"] = str(exc)
        finally:
            try:
                restored = invoke("Restore", "independent-restoration.log", 600, check=False)
                result["restoration_exit"] = restored.returncode
                audited = invoke("Audit", "final-audit-driver.log", 120, check=False)
                result["audit_exit"] = audited.returncode
            finally:
                collect()
                try:
                    behavior = assess_evidence(w / "evidence", clone, bundle, a.release, a.candidate)
                    result["behavior_status"] = behavior["status"]
                except Exception as exc:
                    result["behavior_error"] = str(exc)
                result["completed_unix"] = time.time()
                result["elapsed_seconds"] = time.time() - start
                result["status"] = "passed_and_restored" if all(result.get(key) == 0 for key in ("accept_exit", "restoration_exit", "audit_exit")) and result.get("behavior_status") == "passed" else "failed"
                (w / "driver-window.json").write_text(json.dumps(result, indent=2) + "\n")
        if result["status"] != "passed_and_restored":
            print(json.dumps({"status": result["status"], "evidence": str(w / "evidence"), "detail": str(w / "driver-window.json")}))
            return 1
    elif a.mode == "restore":
        result = invoke("Restore", "independent-restoration.log", 600, check=False)
        collect()
        return result.returncode
    else:
        collect()
        if (w / "evidence" / "route.json").exists():
            behavior = assess_evidence(w / "evidence", clone, bundle, a.release, a.candidate)
            if behavior["status"] != "passed":
                return 1
    print(json.dumps({"status": "passed", "mode": a.mode, "evidence": str(w / "evidence")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
