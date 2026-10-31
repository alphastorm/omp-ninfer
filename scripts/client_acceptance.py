#!/usr/bin/env python3
"""Run stock OMP tool/continuation/restart/fail-closed checks, without a GPU in rehearsal.

--local-rehearsal starts an owned loopback Responses stub; never qualification evidence.
Live mode requires --endpoint, --key-file and owner-supplied --restart-cmd, --stop-cmd,
--start-cmd JSON argv arrays. Hooks must block until ready/stopped. No shell is implied.
Only synthetic prompts are used. The receipt binds quickstart block addresses, not a
claim that install blocks or their literal shell commands were executed.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import hashlib
import http.server
import importlib.util
import json
import os
from pathlib import Path
import secrets
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse

from documented_route import DEFAULT_DOC, LANES, extract, lane_blocks, provider_model_id
from omp_client_environment import client_environment
from stock_omp_session_proof import Omp, SEED, RECALL_BUILD, RECALL_BOTH, BUILD, NAME, recalls

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("client_probe", ROOT / "scripts/hosts/omp-client-probe.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def receipt_class(local_rehearsal):
    return "rehearsal" if local_rehearsal else "owner-live"


def block_addresses(lane, doc=DEFAULT_DOC):
    selected = {"tool", "resume", "survives-restart", "fail-closed", "acceptance"}
    blocks = [{"slug": step.slug, "heading": block.heading, "index": block.index,
               "sha256": block.sha256, "language": block.language}
              for step, block in lane_blocks(doc, lane) if step.slug in selected]
    # The native acceptance blocks link to the shared server-survival procedure.
    if not any(b["slug"] == "survives-restart" for b in blocks):
        block = extract(doc, "Session survives the server process")
        blocks.append({"slug": "survives-restart", "heading": block.heading, "index": block.index,
                       "sha256": block.sha256, "language": block.language})
    return blocks


def documented_model_id(lane):
    """The model ID the lane's documented provider step configures: the ID the lane's OMP turns
    request."""
    (block,) = [block for step, block in lane_blocks(DEFAULT_DOC, lane) if step.slug == "provider"]
    return provider_model_id(block.text, ROOT)


def command_json(value):
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not parsed or not all(isinstance(s, str) and s for s in parsed):
        raise argparse.ArgumentTypeError("use a nonempty JSON argv array")
    return parsed


def prepare_home(home, endpoint, key, model_id, *, context_window=131072, concurrency=1):
    agent = home / ".omp/agent"
    agent.mkdir(parents=True)
    # JSON is YAML-compatible. No private settings, extensions or cloud credentials are copied.
    models = {"providers": {"ninfer-acceptance": {"baseUrl": endpoint, "apiKey": key,
        "api": "openai-responses", "authHeader": True, "models": [{"id": model_id,
        "name": "Local acceptance", "reasoning": True, "input": ["text"],
        "contextWindow": context_window, "maxTokens": 4096,
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        "compat": {"statefulResponses": True, "includeEncryptedReasoning": False,
                   "supportsReasoningSummary": False}}]}}}
    (agent / "models.yml").write_text(json.dumps(models), encoding="utf-8")
    (agent / "models.yml").chmod(0o600)
    (agent / "config.yml").write_text(json.dumps({"retry": {"enabled": False, "modelFallback": False},
        "startup": {"checkUpdate": False}, "providers": {"maxInFlightRequests": {"ninfer-acceptance": concurrency}}}),
        encoding="utf-8")
    (home / "work").mkdir()
    (home / "work/marker.txt").write_text(probe.MARKER + "\n", encoding="utf-8")


class StubHandler(http.server.BaseHTTPRequestHandler):
    """Synthetic Responses wire; disk-backed response IDs survive the owned child restart."""
    def log_message(self, *_):
        pass

    def do_POST(self):
        if self.path != "/v1/responses" or self.headers.get("Authorization") != "Bearer " + self.server.key:
            self.send_error(401)
            return
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        with self.server.lock:
            saved = json.loads(self.server.store.read_text()) if self.server.store.exists() else {}
            previous = payload.get("previous_response_id")
            if previous and previous not in saved:
                self.send_error(404)
                return
            history = saved.get(previous, []) + payload.get("input", [])
            encoded = json.dumps(history)
            latest = json.dumps(payload.get("input", [])[-1:])
            response_id = "resp_" + secrets.token_hex(12)
            tool_result = any(item.get("type") == "function_call_output" for item in payload.get("input", [])
                              if isinstance(item, dict))
            tool = "marker.txt" in latest and not tool_result
            if tool:
                item = {"id": "fc_" + secrets.token_hex(8), "type": "function_call", "name": "read",
                        "call_id": "call_" + secrets.token_hex(8), "arguments": json.dumps({"path": "marker.txt"}),
                        "status": "completed"}
            else:
                if tool_result:
                    answer = probe.MARKER
                elif "What build number" in latest:
                    answer = BUILD if BUILD in encoded else "unknown"
                elif "What is the release called" in latest:
                    answer = NAME + " " + BUILD if NAME in encoded and BUILD in encoded else "unknown"
                else:
                    answer = "OK"
                item = {"id": "msg_" + secrets.token_hex(8), "type": "message", "role": "assistant",
                        "status": "completed", "content": [{"type": "output_text", "text": answer, "annotations": []}]}
            saved[response_id] = history + [item]
            self.server.store.write_text(json.dumps(saved), encoding="utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Connection", "close")
        self.end_headers()
        sequence = 0
        def event(kind, **fields):
            nonlocal sequence
            body = {"type": kind, "sequence_number": sequence, **fields}
            sequence += 1
            self.wfile.write(("event: " + kind + "\ndata: " + json.dumps(body) + "\n\n").encode())
            self.wfile.flush()
        response = {"id": response_id, "object": "response", "created_at": int(time.time()),
                    "status": "in_progress", "output": [], "error": None, "incomplete_details": None}
        event("response.created", response=response)
        event("response.output_item.added", output_index=0,
              item={**item, **({"arguments": ""} if tool else {"content": []}), "status": "in_progress"})
        if tool:
            event("response.function_call_arguments.delta", output_index=0, item_id=item["id"], delta=item["arguments"])
            event("response.function_call_arguments.done", output_index=0, item_id=item["id"], arguments=item["arguments"])
        else:
            event("response.content_part.added", output_index=0, item_id=item["id"], content_index=0,
                  part={"type": "output_text", "text": "", "annotations": []})
            event("response.output_text.delta", output_index=0, item_id=item["id"], content_index=0, delta=answer)
            event("response.output_text.done", output_index=0, item_id=item["id"], content_index=0, text=answer)
        event("response.output_item.done", output_index=0, item=item)
        event("response.completed", response={**response, "status": "completed", "output": [item],
              "usage": {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110,
                        "input_tokens_details": {"cached_tokens": 0}, "output_tokens_details": {"reasoning_tokens": 0}}})
        self.close_connection = True


class LoopbackHTTPServer(http.server.ThreadingHTTPServer):
    def server_bind(self):
        # HTTPServer.server_bind performs reverse DNS before publishing readiness.
        # This synthetic server is loopback-only; DNS is not a lifecycle prerequisite.
        socketserver.TCPServer.server_bind(self)
        self.server_name = "localhost"
        self.server_port = self.server_address[1]


def stub_main(store, port):
    server = LoopbackHTTPServer(("127.0.0.1", int(port)), StubHandler)
    server.key = os.environ["OMP_ACCEPTANCE_STUB_KEY"]
    server.store = Path(store) / "responses.json"
    server.lock = threading.Lock()
    (Path(store) / "ready.json").write_text(json.dumps({"port": server.server_port}), encoding="utf-8")
    server.serve_forever()


class Stub:
    def __init__(self, directory, key):
        self.directory, self.key, self.port, self.proc = directory, key, 0, None

    def start(self):
        ready = self.directory / "ready.json"
        ready.unlink(missing_ok=True)
        self.proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "_stub",
            str(self.directory), str(self.port)], env=dict(os.environ, OMP_ACCEPTANCE_STUB_KEY=self.key),
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if ready.exists():
                try:
                    self.port = json.loads(ready.read_text())["port"]
                    return
                except json.JSONDecodeError:
                    pass
            if self.proc.poll() is not None:
                break
            time.sleep(0.05)
        raise RuntimeError("loopback stub did not become ready")

    def stop(self):
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
            self.proc = None

    def restart(self):
        self.stop()
        self.start()


def run_checks(args, home, lifecycle, receipt):
    environment = dict(client_environment(args.omp_version), HOME=str(home), USERPROFILE=str(home), NO_COLOR="1")
    environment.pop("OMP_ACCEPTANCE_STUB_KEY", None)
    def call(arguments):
        result = probe.launch([str(args.omp), *arguments], home / "work", args.turn_timeout, environment)
        return result.returncode, probe.summarize(result.stdout)
    base = ["-p", "--auto-approve", "--mode", "json", "--model", args.model, "--max-time", "60s"]
    code, tool = call([*base, "--no-session", "--tools", "read",
                       "Use the read tool to read marker.txt. Return only its exact single line."])
    receipt["checks"]["tool_turn"] = (code == 0 and tool["typed_read_tool_calls"] == 1
        and tool["linked_tool_results"] == 1 and tool["final_text"] == probe.MARKER and not tool["errors"]
        and tool["providers"] == ["ninfer-acceptance"] and tool["models"] == [args.model.split("/", 1)[1]])
    args.home = home
    sessions = []
    # Preserve a live stock process across the server restart, then resume its disk transcript.
    for label, cont in (("same-process", False), ("new-process", True)):
        omp = Omp.__new__(Omp)
        try:
            omp.__init__(args, label, cont)
            omp.command("set_thinking_level", level="low")
            if not cont:
                seed = omp.prompt(SEED, args.turn_timeout)
                receipt["checks"]["seed"] = seed["stop"] == "stop" and bool(seed["answer"])
                receipt["checks"]["continuation"] = recalls(omp.prompt(RECALL_BUILD, args.turn_timeout), BUILD)
                try:
                    lifecycle("restart")
                except BaseException:
                    lifecycle("start")  # A failed restart hook may already have stopped the lane.
                    raise
            receipt["checks"]["restart_survival" if not cont else "client_resume"] = recalls(
                omp.prompt(RECALL_BOTH, args.turn_timeout), NAME, BUILD)
            sessions.append(omp.state()["session_id"])
        finally:
            if hasattr(omp, "stdin"):
                omp.close()
            elif hasattr(omp, "proc"):
                omp.proc.kill()
                omp.proc.wait()
    receipt["checks"]["same_session"] = bool(sessions[0]) and len(set(sessions)) == 1
    # Restore even if a stop hook partially fails. Never rewrite the provider to fake an outage.
    try:
        lifecycle("stop")
        code, outage = call([*base, "--no-session", "Return LOCAL_ONLY."])
        receipt["checks"]["fail_closed"] = (code != 0 and not outage["assistant_response_observed"]
            and bool(outage["errors"]) and outage["providers"] == ["ninfer-acceptance"]
            and outage["models"] == [args.model.split("/", 1)[1]])
    finally:
        lifecycle("start")


@contextlib.contextmanager
def isolated_windows_home(home):
    """The shared RPC driver sets HOME; Windows also resolves its profile via USERPROFILE."""
    previous = os.environ.get("USERPROFILE")
    os.environ["USERPROFILE"] = str(home)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("USERPROFILE", None)
        else:
            os.environ["USERPROFILE"] = previous


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--omp", required=True, type=Path)
    parser.add_argument("--omp-sha256", required=True)
    parser.add_argument("--omp-version", required=True, help="exact stock version, e.g. omp/18.14.0")
    parser.add_argument("--lane", choices=[v for v in LANES if v != "rtx5090-container-host"], default="rtx5090-macos-client")
    parser.add_argument("--release", help="native candidate release; defaults to the checkout's compatibility authority")
    parser.add_argument("--local-rehearsal", action="store_true")
    parser.add_argument("--endpoint")
    parser.add_argument("--model-id", help="served model ID; defaults to the model the selected lane's documented provider step configures")
    parser.add_argument("--key-file", type=Path)
    for action in ("restart", "stop", "start"):
        parser.add_argument("--" + action + "-cmd", type=command_json)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--turn-timeout", type=int, default=120)
    parser.add_argument("--lifecycle-timeout", type=int, default=1800)
    args = parser.parse_args(argv)
    if not args.local_rehearsal and not all((args.endpoint, args.key_file, args.restart_cmd, args.stop_cmd, args.start_cmd)):
        parser.error("live mode requires endpoint, key-file and all three lifecycle argv hooks")
    if args.local_rehearsal and any((args.endpoint, args.key_file, args.restart_cmd, args.stop_cmd, args.start_cmd)):
        parser.error("rehearsal owns its loopback endpoint and lifecycle; do not supply live options")
    if args.endpoint:
        endpoint = urllib.parse.urlsplit(args.endpoint)
        if (endpoint.scheme != "http" or endpoint.hostname not in ("127.0.0.1", "localhost", "::1")
                or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment
                or endpoint.path.rstrip("/") != "/v1"):
            parser.error("use the documented http://loopback:port/v1 route, not a remote or credential-bearing URL")
    args.omp = args.omp.resolve()
    model_id = args.model_id or documented_model_id(args.lane)
    context_window, concurrency = 131072, 1  # Serial synthetic rehearsal, not a shipping-policy claim.
    native_configuration = None
    if args.lane in ("rtx3090-native", "rtx4090-native") and not args.local_rehearsal:
        from verify_release import native_profile, product_version
        release = args.release or json.loads((ROOT / "compatibility.json").read_text())["product_release"]
        manifest = json.loads((ROOT / "releases" / release / "manifest.json").read_text())
        variant = next(row for row in manifest["components"]["ninfer_variants"]
                       if row["id"] == args.lane.removesuffix("-native") + "-windows-native")
        errors = []
        if (product_version(release) or (0, 0, 0)) >= (0, 16, 0):
            native_configuration = native_profile(ROOT, release, variant, errors)
        else:
            # Published predecessors bind these original config bytes, without P16's spec reference.
            path = ROOT / "releases" / release / "profiles" / args.lane.removesuffix("-native") / "server-config.json"
            if not path.is_file() or sha256(path) != variant["configuration_sha256"]:
                parser.error("historical native config must match its manifest hash")
            config = json.loads(path.read_text())
            native_configuration = {"max_context": config["engine"]["max_context"],
                                    "concurrency": config["engine"]["max_concurrency"],
                                    "public_model_id": config["model_id"]}
        if errors or native_configuration is None:
            parser.error("native acceptance requires the exact bound candidate profile: " + "; ".join(errors))
        context_window, concurrency = native_configuration["max_context"], native_configuration["concurrency"]
    args.model = "ninfer-acceptance/" + model_id
    receipt = {"artifact_type": "omp_ninfer_client_acceptance", "schema_version": 1,
               "receipt_class": receipt_class(args.local_rehearsal), "qualification_claimed": False,
               "lane": args.lane, "synthetic_prompts_only": True,
               "document": "docs/QUICKSTART.md", "document_sha256": sha256(DEFAULT_DOC),
               "block_addresses": block_addresses(args.lane),
               "execution": "semantic client checks; not verbatim install-route execution",
               "checks": {}, "error": None, "started_utc": datetime.datetime.now(datetime.UTC).isoformat()}
    if native_configuration is not None:
        receipt["runtime_configuration"] = native_configuration
    try:
        actual = sha256(args.omp)
        if actual != args.omp_sha256.lower():
            raise RuntimeError("stock client SHA-256 mismatch")
        receipt["omp"] = {"sha256": actual, "version": args.omp_version}
        with tempfile.TemporaryDirectory(prefix="omp-client-acceptance-") as temporary:
            home = Path(temporary)
            version = probe.launch([str(args.omp), "--version"], home, 60,
                                   dict(client_environment(args.omp_version), HOME=str(home), USERPROFILE=str(home)))
            if version.returncode or version.stdout.strip() != args.omp_version:
                raise RuntimeError("stock client version mismatch")
            key = secrets.token_hex(32) if args.local_rehearsal else args.key_file.read_text().strip()
            if not key:
                raise RuntimeError("bearer file is empty")
            stub = Stub(home, key) if args.local_rehearsal else None
            try:
                if stub:
                    stub.start()
                endpoint = f"http://127.0.0.1:{stub.port}/v1" if stub else args.endpoint
                prepare_home(home, endpoint, key, model_id, context_window=context_window, concurrency=concurrency)
                def lifecycle(action):
                    if stub:
                        getattr(stub, action)()
                    else:
                        outcome = subprocess.run(getattr(args, action + "_cmd"), stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=args.lifecycle_timeout)
                        if outcome.returncode:
                            raise RuntimeError(action + " hook failed; inspect owner-local logs")
                with isolated_windows_home(home):
                    run_checks(args, home, lifecycle, receipt)
            finally:
                if stub:
                    stub.stop()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        # Raw RPC errors and hook output may contain private paths or credentials.
        receipt["error"] = type(error).__name__ + ": acceptance did not complete; inspect the first false check or local prerequisites"
    receipt["passed"] = not receipt["error"] and bool(receipt["checks"]) and all(receipt["checks"].values())
    receipt["status"] = "passed" if receipt["passed"] else "failed"
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "_stub":
        stub_main(*sys.argv[2:])
    else:
        raise SystemExit(main())
