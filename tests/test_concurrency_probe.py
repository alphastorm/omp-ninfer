"""Consumer-visible streaming, interference, reuse, restart, and failure receipts."""
from __future__ import annotations

import contextlib
import hashlib
import http.server
import importlib.util
import io
import json
import shlex
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("concurrency_probe", ROOT / "scripts" / "concurrency_probe.py")
assert SPEC is not None and SPEC.loader is not None
PROBE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PROBE
SPEC.loader.exec_module(PROBE)
KEY = 'mock-private-key-"never-persist'
TEXT = "mock-answer-private-"
REASONING = "mock-reasoning-private-"


class MockResponsesServer(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, directory: Path, plan=None):
        super().__init__(("127.0.0.1", 0), MockHandler)
        self.directory = directory
        self.plan = plan or (lambda payload, index: {})
        self.lock = threading.Lock()
        self.calls = []
        self.saved = {}
        self.active = 0
        self.peak_active = 0
        self.epoch = 0
        self.seed_at_interrupt = None
        self.log = directory / "requests.jsonl"
        self.log.write_text("\n".join(json.dumps(record) for record in (
            {"event": "request_done", "timestamp_unix_ms": 0, "outside": "before"},
            {"event": "request_done", "timestamp_unix_ms": int(time.time() * 1000) + 86400000, "outside": "after"},
            {"event": "request_start", "timestamp_unix_ms": int(time.time() * 1000)},
        )) + "\n", encoding="utf-8")
        self.worker = threading.Thread(target=self.serve_forever, daemon=True)
        self.worker.start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_port}"

    def close(self):
        self.shutdown()
        self.server_close()
        self.worker.join()


class MockHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def send_json(self, status, document):
        body = json.dumps(document).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"status": "ok"})
        elif self.path == "/v1/ninfer/status":
            self.send_json(200, {"identity": {"runtime_git_commit": "mock-runtime", "api_key": KEY},
                                 "runtime": {"max_concurrency": 2}})
        elif self.path == "/interrupt":
            with self.server.lock:
                self.server.epoch += 1
                self.server.seed_at_interrupt = json.loads((self.server.directory / "receipt.json").read_text())
            self.send_json(200, {"status": "restarted"})
        else:
            self.send_json(404, {"error": "not found"})

    def event(self, name, fields):
        # The fork sends event: plus JSON data with type and sequence_number.
        event = {"type": name, "sequence_number": self.sequence, **fields}
        self.sequence += 1
        self.wfile.write(f"event: {name}\ndata: {json.dumps(event)}\n\n".encode())
        self.wfile.flush()

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path != "/v1/responses" or self.headers.get("Authorization") != f"Bearer {KEY}":
            self.send_json(401, {"error": {"code": "unauthorized"}})
            return
        if self.headers.get("X-NInfer-Session") != payload.get("ninfer_session"):
            self.send_json(400, {"error": {"code": "invalid_session"}})
            return
        if payload.get("stream") is not True:
            self.send_json(400, {"error": {"code": "stream_required"}})
            return
        with self.server.lock:
            call = {"payload": payload, "received": time.monotonic(), "deltas": [], "epoch": self.server.epoch}
            self.server.calls.append(call)
            index = len(self.server.calls)
            self.server.active += 1
            self.server.peak_active = max(self.server.peak_active, self.server.active)
        try:
            self.respond(payload, index, call)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass  # Deliberate disconnect and deadline tests close a live stream.
        finally:
            with self.server.lock:
                self.server.active -= 1
            self.close_connection = True

    def respond(self, payload, index, call):
        plan = self.server.plan(payload, index)
        if plan.get("reset"):
            self.connection.shutdown(socket.SHUT_RDWR)
            return
        if plan.get("http_error"):
            self.send_json(plan["http_error"], {"error": {"code": "capacity_exceeded", "message": f"capacity exceeded; {KEY}"},
                                                "input": payload["input"]})
            return
        previous = payload.get("previous_response_id")
        with self.server.lock:
            parent = self.server.saved.get(previous)
        if previous and (parent is None or parent["session"] != payload["ninfer_session"]):
            self.send_json(404, {"error": {"code": "previous_response_not_found"}})
            return
        prompt = parent["frontier"] + 16 if parent else 1000
        cached = parent["frontier"] if parent else 0
        response_id = f"resp_mock_{index}"
        call["response_id"] = response_id
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Connection", "close")
        self.end_headers()
        self.sequence = 0
        doc = {"id": response_id, "object": "response", "status": "in_progress", "usage": None,
               "output": [], "completed_at": None, "error": None, "incomplete_details": None}
        self.event("response.created", {"response": doc})
        self.event("response.in_progress", {"response": doc})
        sleeps = plan.get("sleeps", [.012, .008, .008, .008])
        reasoning, text = "", ""
        for delta_index, delay in enumerate(sleeps):
            time.sleep(delay)
            if call["epoch"] != self.server.epoch:
                self.connection.shutdown(socket.SHUT_RDWR)
                return
            kind = "reasoning_text" if delta_index == 0 else "output_text"
            item_id = "rs_mock" if delta_index == 0 else "msg_mock"
            output_index = 0 if delta_index == 0 else 1
            fragment = REASONING if delta_index == 0 else f"{TEXT}{delta_index}"
            if delta_index in (0, 1):
                if delta_index == 1:
                    self.event("response.reasoning_text.done", {"item_id": "rs_mock", "output_index": 0,
                                                               "content_index": 0, "text": reasoning})
                item = {"id": item_id, "type": "reasoning" if delta_index == 0 else "message",
                        "status": "in_progress", "content": []}
                if delta_index == 0:
                    item["summary"] = []
                else:
                    item["role"] = "assistant"
                self.event("response.output_item.added", {"output_index": output_index, "item": item})
                self.event("response.content_part.added", {"item_id": item_id, "output_index": output_index,
                                                          "content_index": 0, "part": {"type": kind, "text": ""}})
            fields = {"item_id": item_id, "output_index": output_index, "content_index": 0, "delta": fragment}
            if delta_index:
                fields["logprobs"] = []
                text += fragment
            else:
                reasoning += fragment
            call["deltas"].append(time.monotonic())
            self.event(f"response.{kind}.delta", fields)
        tokens = plan.get("tokens", 60)
        status = plan.get("status", "completed")
        doc = {**doc, "status": status, "completed_at": int(time.time()),
               "usage": {"input_tokens": prompt, "input_tokens_details": {"cached_tokens": cached},
                         "output_tokens": tokens, "output_tokens_details": {"reasoning_tokens": 10},
                         "total_tokens": prompt + tokens},
               "output": [{"id": "rs_mock", "type": "reasoning", "summary": [],
                           "content": [{"type": "reasoning_text", "text": reasoning}]},
                          {"id": "msg_mock", "type": "message", "role": "assistant",
                           "content": [{"type": "output_text", "text": text, "annotations": []}]}]}
        if status == "incomplete":
            doc["incomplete_details"] = {"reason": "max_output_tokens"}
        elif status == "failed":
            doc["error"] = {"code": "server_error", "message": "planned failure"}
        if payload.get("store") and status in ("completed", "incomplete"):
            with self.server.lock:
                self.server.saved[response_id] = {"session": payload["ninfer_session"], "frontier": prompt + tokens}
        log_record = {"event": "request_done", "timestamp_unix_ms": int(time.time() * 1000),
                      "server_instance_id": f"mock-{self.server.epoch}", "schema_version": 17,
                      "request": {"request_id": index, "client_identity": {
                          "request_sha256": payload["ninfer_request_id"], "session_sha256": payload["ninfer_session"]}},
                      "result": {"prompt_tokens": prompt, "completion_tokens": tokens,
                                 "prefix_cache_hit_tokens": cached, "prefix_reuse_path": "private_endpoint" if cached else "root"},
                      "timings_seconds": {"ttft": call["deltas"][0] - call["received"]}}
        with self.server.lock, self.server.log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(log_record) + "\n")
        self.event("response.output_text.done", {"item_id": "msg_mock", "output_index": 1,
                                                "content_index": 0, "text": text, "logprobs": []})
        self.event(f"response.{status}", {"response": doc})
        call["finished"] = time.monotonic()


class ConcurrencyProbeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.key = self.directory / "key"
        self.key.write_text(KEY)
        self.receipt = self.directory / "receipt.json"

    def server(self, plan=None):
        server = MockResponsesServer(self.directory, plan)
        self.addCleanup(server.close)
        return server

    def run_probe(self, server, *options):
        argv = ["--base-url", server.url, "--api-key-file", str(self.key), "--receipt", str(self.receipt),
                "--timeout", "5", "--session-tokens", "80", "--prefill-tokens", "80",
                "--fanout-base-tokens", "80", "--large-tokens", "80", *options]
        with contextlib.redirect_stdout(io.StringIO()):
            code = PROBE.main(argv)
        receipt = json.loads(self.receipt.read_text())
        return code, receipt

    def test_metrics_count_reasoning_and_measure_concurrent_makespan(self):
        def plan(payload, _):
            return {"sleeps": [.06, .02, .09, .03] if payload["input"] == PROBE.DECODE_PROMPT else [.10, .10, .12, .08]}
        server = self.server(plan)
        code, receipt = self.run_probe(server, "--scenario", "decode_pair")
        self.assertEqual(code, 0)
        result = receipt["scenarios"][0]
        a, b = result["requests"]
        self.assertEqual(server.peak_active, 2)
        self.assertLess(abs(a["submitted_monotonic_s"] - b["submitted_monotonic_s"]), .04)
        self.assertAlmostEqual(a["ttft_s"], .06, delta=.035)
        self.assertAlmostEqual(a["itl_ms"]["max"], 90, delta=30)
        self.assertAlmostEqual(a["itl_ms"]["p50"], 30, delta=25)
        self.assertAlmostEqual(a["itl_ms"]["p95"], 84, delta=30)
        self.assertAlmostEqual(a["itl_ms"]["p99"], 88.8, delta=30)
        self.assertEqual([d["kind"] for d in a["output_deltas"]], ["reasoning", "text", "text", "text"])
        self.assertAlmostEqual(a["decode_tok_s"], 60 / .14, delta=95)
        self.assertAlmostEqual(b["decode_tok_s"], 60 / .30, delta=40)
        self.assertAlmostEqual(result["summary"]["aggregate_tok_s"], 120 / .40, delta=55)
        self.assertAlmostEqual(result["summary"]["fairness"], .14 / .30, delta=.13)
        self.assertAlmostEqual(result["summary"]["makespan_s"], .40, delta=.06)
        self.assertEqual(a["reasoning_tokens"], 10)
        self.assertEqual(a["output_text_sha256"], hashlib.sha256("".join(f"{TEXT}{i}" for i in (1, 2, 3)).encode()).hexdigest())
        self.assertEqual(a["reasoning_text_sha256"], hashlib.sha256(REASONING.encode()).hexdigest())
        serialized = json.dumps(receipt)
        for secret in (KEY, PROBE.DECODE_PROMPT, PROBE.SECOND_DECODE_PROMPT, TEXT, REASONING):
            self.assertNotIn(secret, serialized)
        self.assertEqual(receipt["identity"]["server_before"]["body"]["identity"]["runtime_git_commit"], "mock-runtime")

    def test_prefill_overlap_reports_the_decode_gap_not_created_event_ttft(self):
        server = self.server(lambda payload, _: {"sleeps": [.03, .05, .18, .02]
                                                if payload["input"] == PROBE.DECODE_PROMPT else [.08, .005, .005]})
        code, receipt = self.run_probe(server, "--scenario", "prefill_during_decode", "--stall-after", "2")
        self.assertEqual(code, 0)
        result = receipt["scenarios"][0]
        a, b = result["requests"]
        self.assertGreaterEqual(b["submitted_monotonic_s"], a["output_deltas"][1]["monotonic_s"])
        gaps = result["interference"]["a_gaps_overlapping_b_prefill"]
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0]["gap_ms"], 180, delta=35)
        self.assertAlmostEqual(gaps[0]["overlap_ms"], 80, delta=35)
        self.assertAlmostEqual(result["interference"]["a_itl_max_ms"], 180, delta=35)
        self.assertAlmostEqual(result["interference"]["b_ttft_s"], .08, delta=.035)

    def test_short_decode_is_submitted_one_second_into_prefill_with_vram_samples(self):
        server = self.server(lambda payload, _: {"sleeps": [.03, .01, .01]
                                                if isinstance(payload["input"], str) else [1.25, .01, .01]})
        vram = f"{shlex.quote(sys.executable)} -c 'print(1234)'"
        code, receipt = self.run_probe(server, "--scenario", "decode_during_prefill", "--vram-cmd", vram)
        self.assertEqual(code, 0)
        result = receipt["scenarios"][0]
        b, a = result["requests"]
        self.assertAlmostEqual(a["submitted_monotonic_s"] - b["submitted_monotonic_s"], 1, delta=.06)
        self.assertLess(a["completed_monotonic_s"], b["first_output_monotonic_s"])
        self.assertAlmostEqual(result["interference"]["a_ttft_s"], .03, delta=.04)
        self.assertLess(result["interference"]["a_total_s"], .15)
        self.assertEqual(result["vram"]["peak_mib"], 1234)
        samples = result["vram"]["samples"]
        self.assertGreaterEqual(len(samples), 2)
        self.assertAlmostEqual(samples[1]["monotonic_s"] - samples[0]["monotonic_s"], 1, delta=.10)

    def test_session_turns_preserve_both_lineages_and_join_only_run_window_logs(self):
        server = self.server(lambda payload, _: {"status": "incomplete" if not payload.get("previous_response_id") else "completed"})
        code, receipt = self.run_probe(server, "--scenario", "two_sessions", "--turns", "2",
                                       "--log-cmd", f"cat {shlex.quote(str(server.log))}")
        self.assertEqual(code, 0)
        result = receipt["scenarios"][0]
        seeds, turn1, turn2 = (result["requests"][offset:offset + 2] for offset in (0, 2, 4))
        self.assertEqual([r["cached_tokens"] for r in seeds], [0, 0])
        self.assertEqual([r["cached_tokens"] for r in turn1], [1060, 1060])
        self.assertEqual([r["cached_tokens"] for r in turn2], [1136, 1136])
        self.assertEqual({r["previous_response_id"] for r in turn1}, {r["response_id"] for r in seeds})
        self.assertEqual({r["previous_response_id"] for r in turn2}, {r["response_id"] for r in turn1})
        self.assertEqual(len(receipt["request_done"]), 6)
        self.assertTrue(all(r["prefix_reuse_path"] == "private_endpoint" for r in turn1 + turn2))
        self.assertTrue(all(r["ttft_s"] >= .01 for r in turn1 + turn2))
        self.assertTrue(all("outside" not in r for r in receipt["request_done"]))

    def test_fanout_branches_from_base_and_bounds_concurrency(self):
        server = self.server()
        code, receipt = self.run_probe(server, "--scenario", "fanout", "--branches", "5", "--fanout-concurrency", "2")
        self.assertEqual(code, 0)
        base, *branches = receipt["scenarios"][0]["requests"]
        self.assertEqual([r["cached_tokens"] for r in branches], [1060] * 5)
        self.assertEqual({r["previous_response_id"] for r in branches}, {base["response_id"]})
        self.assertEqual(server.peak_active, 2)
        self.assertTrue(all(r["ttft_s"] >= .01 for r in branches))

    def test_restart_interrupts_streams_but_resumes_last_completed_heads(self):
        def plan(payload, _):
            return {"sleeps": [.003] * 200} if payload["input"] == PROBE.DECODE_PROMPT else {}
        server = self.server(plan)
        command = (f"{shlex.quote(sys.executable)} -c " + shlex.quote(
            f"import urllib.request; urllib.request.urlopen('{server.url}/interrupt').read()"))
        code, receipt = self.run_probe(server, "--scenario", "restart", "--kill-during-decode", command)
        self.assertEqual(code, 0)
        records = receipt["scenarios"][0]["requests"]
        seeds, interrupted, resumed = (records[offset:offset + 2] for offset in (0, 2, 4))
        self.assertTrue(all(not r["ok"] and r["expected_interruption"] for r in interrupted))
        self.assertTrue(all(len(r["output_deltas"]) >= 32 for r in interrupted))
        self.assertEqual({r["previous_response_id"] for r in resumed}, {r["response_id"] for r in seeds})
        self.assertEqual([r["cached_tokens"] for r in resumed], [1060, 1060])
        saved = server.seed_at_interrupt["sessions"]
        self.assertEqual({s["newest_response_id"] for s in saved.values()}, {r["response_id"] for r in seeds})
        self.assertTrue(all(len(r["attempts"]) == 1 for r in interrupted))
        self.assertTrue(all(r["ttft_s"] >= .01 for r in resumed))

    def test_separate_restart_resume_continues_receipt_sessions(self):
        server = self.server()
        code, seeded = self.run_probe(server, "--scenario", "restart", "--phase", "seed")
        self.assertEqual(code, 0)
        seed_path = self.directory / "seed.json"
        seed_path.write_text(json.dumps(seeded))
        code, resumed = self.run_probe(server, "--scenario", "restart", "--phase", "resume", "--resume-from", str(seed_path))
        self.assertEqual(code, 0)
        records = resumed["scenarios"][0]["requests"]
        self.assertEqual([r["cached_tokens"] for r in records], [1060, 1060])
        self.assertEqual({r["previous_response_id"] for r in records},
                         {s["newest_response_id"] for s in seeded["sessions"].values()})

    def test_http_failure_retains_sanitized_body_and_other_requests_unless_fail_fast(self):
        def plan(payload, _):
            return {"http_error": 413} if isinstance(payload["input"], list) and "desk D1" in json.dumps(payload["input"]) else {}
        server = self.server(plan)
        options = ("--scenario", "near_capacity", "--scenario", "solo")
        code, receipt = self.run_probe(server, *options)
        self.assertEqual(code, 1)
        error, served = receipt["scenarios"][0]["requests"]
        self.assertEqual(error["http_status"], 413)
        self.assertIn("capacity_exceeded", error["http_error_body"])
        self.assertNotIn("Operations ledger", error["http_error_body"])
        self.assertNotIn(KEY, json.dumps(receipt))
        self.assertTrue(served["ok"])
        self.assertTrue(receipt["scenarios"][1]["ok"])
        self.assertFalse(receipt["scenarios"][0]["summary"]["token_accounting_complete"])
        code, receipt = self.run_probe(server, *options, "--fail-fast")
        self.assertEqual(code, 1)
        self.assertEqual([s["name"] for s in receipt["scenarios"]], ["near_capacity"])
        self.assertTrue(receipt["scenarios"][0]["requests"][1]["ok"])

    def test_one_pre_stream_reset_retry_keeps_submit_latency(self):
        server = self.server(lambda _, index: {"reset": True} if index == 1 else {})
        code, receipt = self.run_probe(server, "--scenario", "solo")
        self.assertEqual(code, 0)
        request = receipt["scenarios"][0]["requests"][0]
        self.assertEqual(len(request["attempts"]), 2)
        self.assertGreaterEqual(request["ttft_s"], 2)
        self.assertAlmostEqual(request["decode_tok_s"], 60 / .024, delta=700)

    def test_total_timeout_bounds_a_continuously_streaming_request(self):
        server = self.server(lambda *_: {"sleeps": [.02] * 100})
        code, receipt = self.run_probe(server, "--scenario", "solo", "--timeout", ".12")
        self.assertEqual(code, 1)
        request = receipt["scenarios"][0]["requests"][0]
        self.assertEqual(request["finish_status"], "timeout")
        self.assertGreaterEqual(request["total_s"], .10)
        self.assertLess(request["total_s"], .30)
        self.assertIsNone(request["output_tokens"])
        self.assertIsNone(request["decode_tok_s"])

    def test_terminal_failure_is_not_a_successful_http_request(self):
        server = self.server(lambda *_: {"status": "failed"})
        code, receipt = self.run_probe(server, "--scenario", "solo")
        self.assertEqual(code, 1)
        record = receipt["scenarios"][0]["requests"][0]
        self.assertEqual(record["http_status"], 200)
        self.assertEqual(record["finish_status"], "failed")
        self.assertEqual(record["error"]["code"], "server_error")


if __name__ == "__main__":
    unittest.main()
