"""Hardware-independent receipt, live lifecycle and real Responses stub contracts."""
import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import client_acceptance as runner
import verify_release as verify


class ReceiptClassTests(unittest.TestCase):
    def test_class_is_selected_by_execution_mode(self):
        self.assertEqual(runner.receipt_class(True), "rehearsal")
        self.assertEqual(runner.receipt_class(False), "owner-live")

    def test_all_client_routes_bind_real_quickstart_blocks(self):
        for lane in runner.LANES:
            if lane == "rtx5090-container-host":
                continue
            with self.subTest(lane=lane):
                blocks = runner.block_addresses(lane)
                self.assertTrue(blocks)
                for block in blocks:
                    actual = runner.extract(runner.DEFAULT_DOC, block["heading"], block["index"])
                    self.assertEqual(actual.sha256, block["sha256"])
                self.assertIn("survives-restart", [b["slug"] for b in blocks])

    def test_verifier_rejects_nested_rehearsal_without_rejecting_legacy(self):
        for value, errors_count in (({"receipt_class": "owner-live"}, 0), ({"status": "passed"}, 0),
                                    ({"children": [{"receipt_class": "rehearsal", "status": "passed"}]}, 1)):
            errors = []
            verify.validate_receipt_classes(ROOT, ROOT, [value], errors)
            self.assertEqual(len(errors), errors_count)
            if errors:
                self.assertIn("rehearsal receipt is not qualification evidence", errors[0])

    def test_verifier_follows_bound_children_and_cycles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "child.json").write_text(json.dumps({"receipt_class": "rehearsal", "path": "child.json"}))
            errors = []
            verify.validate_receipt_classes(root, root, [{"receipt": {"repository_path": "child.json"}}], errors)
            self.assertEqual(len(errors), 1)

    def test_verifier_follows_platform_lists_and_pinned_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "child.json").write_text(json.dumps({"receipt_class": "rehearsal"}))
            for document in ({"platform_receipts": ["child.json"]}, {"acceptance_receipt": {
                    "url": "https://raw.githubusercontent.com/alphastorm/omp-ninfer/" + "a" * 40 + "/child.json"}}):
                errors = []
                verify.validate_receipt_classes(root, root, [document], errors)
                self.assertEqual(len(errors), 1)

    def test_hash_mismatch_emits_failed_rehearsal_without_launching(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "omp"
            binary.write_bytes(b"not stock")
            output = root / "receipt.json"
            with patch.object(runner.probe, "launch") as launch, contextlib.redirect_stdout(io.StringIO()):
                code = runner.main(["--omp", str(binary), "--omp-sha256", "a" * 64,
                    "--omp-version", "omp/18.12.1", "--local-rehearsal", "--receipt", str(output)])
            self.assertEqual(code, 1)
            launch.assert_not_called()
            receipt = json.loads(output.read_text())
            self.assertEqual(receipt["receipt_class"], "rehearsal")
            self.assertFalse(receipt["passed"])
            self.assertNotIn(directory, output.read_text())

    def test_live_hooks_are_required_and_rehearsal_cannot_take_hooks(self):
        base = ["--omp", "unused", "--omp-sha256", "a" * 64,
                "--omp-version", "omp/18.12.1", "--receipt", "unused.json"]
        with contextlib.redirect_stderr(io.StringIO()):
            for extra in ([], ["--local-rehearsal", "--stop-cmd", '["true"]']):
                with self.assertRaises(SystemExit) as raised:
                    runner.main(base + extra)
                self.assertEqual(raised.exception.code, 2)

    def test_lifecycle_failures_still_restore(self):
        class FakeOmp:
            def __init__(self, args, label, cont):
                self.stdin = True
            def command(self, *args, **kwargs):
                pass
            def prompt(self, prompt, timeout):
                return {"stop": "stop", "answer": runner.NAME + " " + runner.BUILD}
            def state(self):
                return {"session_id": "one"}
            def close(self):
                pass
        tool = {"typed_read_tool_calls": 1, "linked_tool_results": 1, "final_text": runner.probe.MARKER,
                "errors": [], "providers": ["ninfer-acceptance"], "models": ["q38-ninfer"]}
        args = argparse.Namespace(omp=Path("omp"), omp_version="omp/18.12.1", model="ninfer-acceptance/q38-ninfer", turn_timeout=5)
        for failing_action, expected in (("stop", ["restart", "stop", "start"]), ("restart", ["restart", "start"])):
            calls = []
            def lifecycle(action):
                calls.append(action)
                if action == failing_action:
                    raise RuntimeError("partial hook failure")
            with self.subTest(action=failing_action), tempfile.TemporaryDirectory() as directory, \
                 patch.object(runner, "Omp", FakeOmp), \
                 patch.object(runner.probe, "launch", return_value=argparse.Namespace(returncode=0, stdout="")), \
                 patch.object(runner.probe, "summarize", return_value=tool):
                with self.assertRaisesRegex(RuntimeError, "partial hook"):
                    runner.run_checks(args, Path(directory), lifecycle, {"checks": {}})
            self.assertEqual(calls, expected)


class StubTests(unittest.TestCase):
    def test_loopback_bind_does_not_depend_on_reverse_dns(self):
        with patch("socket.getfqdn", side_effect=AssertionError("reverse DNS must not run")):
            server = runner.LoopbackHTTPServer(("127.0.0.1", 0), runner.StubHandler)
            try:
                self.assertEqual(server.server_name, "localhost")
                self.assertGreater(server.server_port, 0)
            finally:
                server.server_close()

    def test_real_child_restart_restores_response_ids_from_disk(self):
        with tempfile.TemporaryDirectory() as directory:
            stub = runner.Stub(Path(directory), "synthetic-test-key")
            def request(payload):
                req = urllib.request.Request(f"http://127.0.0.1:{stub.port}/v1/responses", data=json.dumps(payload).encode(),
                    headers={"Authorization": "Bearer synthetic-test-key", "Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    events = [json.loads(line[6:]) for line in response.read().decode().splitlines() if line.startswith("data: ")]
                return events[-1]["response"]
            try:
                stub.start()
                first_pid = stub.proc.pid
                first = request({"stream": True, "input": [{"role": "user", "content": runner.SEED}]})
                stub.restart()
                self.assertNotEqual(stub.proc.pid, first_pid)
                second = request({"stream": True, "previous_response_id": first["id"],
                                  "input": [{"role": "user", "content": runner.RECALL_BOTH}]})
                self.assertEqual(second["output"][0]["content"][0]["text"], runner.NAME + " " + runner.BUILD)
            finally:
                stub.stop()


if __name__ == "__main__":
    unittest.main()
