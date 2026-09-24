#!/usr/bin/env python3
"""Private structured live acceptance; never print credentials or raw model output.

Run preflight before opening a runtime window, live while reachable, then outage
with the same configured route unavailable. --dry-run has no filesystem effects.
Windows uses PowerShell's native argument dispatch, not a cmd.exe command string.
"""
import argparse
import base64
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import urllib.request

MARKER = "OMP_NINFER_TOOL_OK"
NONCE = "COBALT-493817"


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def summarize(text):
    events = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            events.append(event)
    messages = [e.get("message", {}) for e in events if e.get("type") == "message_end"]
    # agent_end is an independent source of final messages, not another turn.
    all_messages = messages + [m for e in events if e.get("type") == "agent_end" for m in e.get("messages", [])]
    calls, results, texts = [], [], []
    for message in messages:
        content = message.get("content", [])
        if not isinstance(content, list):
            content = []
        if message.get("role") == "assistant":
            texts.append("".join(c.get("text", "") for c in content if c.get("type") == "text"))
            calls.extend({"id": c.get("id"), "name": c.get("name")} for c in content if c.get("type") == "toolCall")
        if message.get("role") == "toolResult":
            results.append({"toolCallId": message.get("toolCallId"), "toolName": message.get("toolName"),
                            "isError": message.get("isError"), "marker_observed": MARKER in json.dumps(content)})
    linked = [r for r in results if not r["isError"] and r["marker_observed"] and any(c["id"] == r["toolCallId"] and c["name"] == "read" for c in calls)]
    errors = [m["errorMessage"] for m in all_messages if m.get("errorMessage")]
    errors.extend(str(e.get("error", e.get("message", ""))) for e in events if e.get("type") == "error")
    return {"event_counts": dict(collections.Counter(e.get("type", "untyped") for e in events)),
            "typed_tool_calls": calls, "typed_tool_results": results, "linked_tool_results": len(linked),
            "typed_read_tool_calls": sum(c["name"] == "read" for c in calls),
            "tool_result_marker": bool(linked), "final_text": texts[-1].strip() if texts else "",
            "assistant_response_observed": any(t.strip() for t in texts) or bool(calls),
            "providers": sorted({m["provider"] for m in all_messages if m.get("provider")}),
            "models": sorted({m["model"] for m in all_messages if m.get("model")}),
            "errors": sorted(set(errors)), "agent_end": any(e.get("type") == "agent_end" for e in events)}


def launch(argv, cwd, timeout):
    if os.name == "nt":
        # Avoid the historical cmd wrapper which split a prompt into multiple turns.
        quote = lambda s: "'" + str(s).replace("'", "''") + "'"
        arguments = ",".join(quote(s) for s in argv[1:])
        source = ("$ErrorActionPreference='Continue'; [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); "
                  "$a=@(" + arguments + "); & " + quote(argv[0]) + " @a; exit $LASTEXITCODE")
        argv = ["powershell.exe", "-NoProfile", "-EncodedCommand", base64.b64encode(source.encode("utf-16le")).decode()]
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("release", "candidate", "output", "binary", "clone", "platform", "profile"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--phase", choices=("preflight", "live", "outage"), required=True)
    parser.add_argument("--provider", default="ninfer-beta")
    parser.add_argument("--model", default="ninfer-beta/local-max")
    parser.add_argument("--endpoint", default="http://127.0.0.1:18089/v1")
    parser.add_argument("--key-file")
    parser.add_argument("--expected-runtime")
    parser.add_argument("--vision-image")
    parser.add_argument("--dry-run", action="store_true")
    a = parser.parse_args()
    if a.dry_run:
        print(json.dumps({"status": "dry-run", "phase": a.phase, "platform": a.platform,
                          "effects": "none", "output": a.output, "checks": ["typed read/result", "exact marker", "exact continuation nonce", "provider/model isolation", "served runtime identity"]}))
        return
    out, clone = Path(a.output), Path(a.clone)
    out.mkdir(parents=True, exist_ok=True)
    receipt_path = out / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.exists() else {
        "release": a.release, "candidate": a.candidate, "platform": a.platform, "started_utc": now(),
        "phases": {}, "live_acceptance": {}, "execution_context": {"kernel": platform.release(),
        "wsl_distro_name_present": bool(os.environ.get("WSL_DISTRO_NAME")),
        "wsl_interop_present": bool(os.environ.get("WSL_INTEROP")), "environment_erased": False,
        "native_linux_os_qualification_claimed": False}}
    def save():
        receipt["updated_utc"] = now()
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    def call(name, args, timeout=210):
        result = launch([a.binary, *args], out, timeout)
        (out / (name + ".jsonl")).write_text(result.stdout, encoding="utf-8")
        (out / (name + ".stderr")).write_text(result.stderr, encoding="utf-8")
        summary = summarize(result.stdout)
        summary["returncode"] = result.returncode
        receipt["phases"][name] = summary
        save()
        return summary
    def only_selected(result):
        return result["providers"] == [a.provider] and all(m in {"local-max", "q38-ninfer", a.model.split("/", 1)[-1]} for m in result["models"]) and bool(result["models"])
    def live_ok(result):
        assert result["returncode"] == 0 and not result["errors"] and result["agent_end"] and only_selected(result), "exit/events/error/provider/model acceptance failed"
    try:
        if a.phase == "preflight":
            result = launch([a.binary, "--version"], out, 30)
            receipt["omp_version"] = result.stdout.strip()
            assert result.returncode == 0 and receipt["omp_version"] == "omp/18.2.3", "client version mismatch"
            result = launch([a.binary, "--help"], out, 30)
            (out / "help.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
            assert result.returncode == 0 and "--mode" in result.stdout and "--session-dir" in result.stdout, "client help contract unavailable"
            args = ["-p", "--model", a.model, "Use the read tool to read marker.txt. Return only its exact single line."]
            result = launch([sys.executable, "-c", "import json,sys;print(json.dumps(sys.argv[1:]))", *args], out, 30)
            assert result.returncode == 0 and json.loads(result.stdout) == args, "prompt argv was split"
            receipt["preflight"] = {"status": "passed", "version": receipt["omp_version"], "argv_count": len(args), "argv_exact": True}
        elif a.phase == "outage":
            result = call("fail-closed", ["-p", "--no-session", "--mode", "json", "--max-time", "20s", "--model", a.model, "Return LOCAL_ONLY."], 45)
            assert result["returncode"] != 0 and not result["assistant_response_observed"] and result["errors"] and only_selected(result), "fail-closed exit/no-response/error/provider/model proof failed"
            receipt["live_acceptance"]["fail_closed"] = {"exit_code": result["returncode"], "no_model_response": True,
                "only_selected_local_provider_observed": True, "providers": result["providers"], "models": result["models"],
                "errors": result["errors"], "endpoint": a.endpoint, "method": "configured route unavailable; no provider configuration changes"}
        else:
            assert a.key_file, "live phase requires --key-file"
            key = Path(a.key_file).read_text(encoding="utf-8").strip()
            request = urllib.request.Request(a.endpoint.rstrip("/") + "/ninfer/status", headers={"Authorization": "Bearer " + key})
            with urllib.request.urlopen(request, timeout=15) as response:
                status = json.load(response)
            comp = clone / "compatibility.json"
            authority = json.loads(comp.read_text(encoding="utf-8"))
            expected = json.loads(Path(a.expected_runtime).read_text(encoding="utf-8")) if a.expected_runtime else next(p["runtime"] for p in authority["profiles"] if p["id"] == a.profile)
            identity = status["identity"]
            for actual, wanted in (("binary_sha256", "server_binary_sha256"), ("model_artifact_sha256", "model_sha256"), ("config_sha256", "configuration_sha256")):
                assert identity[actual] == expected[wanted], "served runtime identity mismatch: " + actual
            assert status["status"] == "ok" and identity.get("source_dirty") is False, "runtime not clean/healthy"
            receipt["runtime_identity_observed"] = identity
            diag = call("diagnostic", ["appliance", "doctor", "--json", "--compatibility", str(comp), "--compatibility-sha256", hashlib.sha256(comp.read_bytes()).hexdigest(), "--profile", a.profile], 60)
            raw = (out / "diagnostic.jsonl").read_text(encoding="utf-8")
            try:
                diagnostic = json.loads(raw)
            except ValueError:
                diagnostic = {"status": "explicit_remote_required" if "requires --remote" in (out / "diagnostic.stderr").read_text(encoding="utf-8") else "error", "error": (out / "diagnostic.stderr").read_text(encoding="utf-8").strip()}
            receipt["diagnostics"] = {"exit_code": diag["returncode"], "authority_sha256": hashlib.sha256(comp.read_bytes()).hexdigest(), "observed": diagnostic}
            (out / "marker.txt").write_text(MARKER + "\n", encoding="utf-8")
            base = ["-p", "--auto-approve", "--mode", "json", "--model", a.model, "--max-time", "180s"]
            tool = call("tool", [*base, "--no-session", "--tools", "read", "Use the read tool to read marker.txt. Return only its exact single line, without quotes or formatting."])
            live_ok(tool)
            assert tool["typed_read_tool_calls"] == 1 and tool["linked_tool_results"] == 1 and tool["final_text"] == MARKER, "typed read/linked result/exact final marker failed"
            state = call("state", [*base, "--session-dir", str(out / "sessions"), "Remember the nonce COBALT-493817 for my next turn. Reply OK only."])
            live_ok(state)
            continuation = call("continuation", ["-p", "--auto-approve", "--mode", "json", "--max-time", "180s", "--session-dir", str(out / "sessions"), "--continue", "Return the exact nonce from the prior turn verbatim, character for character. Do not correct or change its spelling. Return nothing else."])
            live_ok(continuation)
            assert continuation["final_text"] == NONCE, "continuation did not return exact nonce"
            live = receipt["live_acceptance"]
            live.update({"omp_version": receipt.get("omp_version", ""), "event_counts": tool["event_counts"],
                "typed_read_tool_calls": tool["typed_read_tool_calls"], "linked_tool_results": tool["linked_tool_results"],
                "tool_result_marker": tool["tool_result_marker"], "exact_visible_final_answer": tool["final_text"] == MARKER,
                "agent_end": tool["agent_end"], "continuation_exact_nonce": continuation["final_text"] == NONCE,
                "runtime_identity_bound": True, "runtime_server_binary_sha256": identity["binary_sha256"],
                "runtime_configuration_sha256": identity["config_sha256"], "model_sha256": identity["model_artifact_sha256"],
                "providers": tool["providers"], "models": tool["models"], "raw_transcript_included": False})
            if a.vision_image:
                vision = call("vision", [*base, "--no-session", "@" + a.vision_image, "Describe the visible image in one sentence."])
                live_ok(vision)
                assert vision["final_text"], "vision produced no visible answer"
                live["vision_observed"] = True
                live["vision_input_sha256"] = hashlib.sha256(Path(a.vision_image).read_bytes()).hexdigest()
            receipt["status"] = "passed" if live.get("fail_closed", {}).get("no_model_response") else "live-passed-awaiting-outage"
        if a.phase == "outage":
            receipt["status"] = "passed" if receipt["live_acceptance"].get("continuation_exact_nonce") else "outage-passed-awaiting-live"
    except BaseException as error:
        receipt["status"] = "failed"
        receipt["first_failing_boundary"] = str(error)
        raise
    finally:
        save()
    print(json.dumps({"status": receipt.get("status", "preflight-passed"), "phase": a.phase, "receipt": str(receipt_path)}))


if __name__ == "__main__":
    main()
