"""Hardware-independent receipt, live lifecycle and real Responses stub contracts."""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
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


class DocumentedModelTests(unittest.TestCase):
    """A live lane selected without --model-id requests the model its own server serves."""

    @staticmethod
    def served_model_ids():
        # Server-side identities of the current release, never the client's own provider fragments:
        # the container runtime's public model ID and each native variant's bound server config.
        release = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))["product_release"]
        tree = ROOT / "releases" / release
        manifest = json.loads((tree / "manifest.json").read_text(encoding="utf-8"))
        configurations = {hashlib.sha256(path.read_bytes()).hexdigest(): json.loads(path.read_bytes())["model_id"]
                          for path in (tree / "profiles").glob("*/server-config.json")}
        native = {variant["id"]: configurations[variant["configuration_sha256"]]
                  for variant in manifest["components"]["ninfer_variants"]}
        container = manifest["runtime_identity"]["public_model_id"]
        return {"rtx4090-native": native["rtx4090-windows-native"],
                "rtx3090-native": native["rtx3090-windows-native"],
                "rtx5090-macos-client": container, "rtx5090-windows-client": container}

    def configured(self, *selection):
        """Run a live acceptance up to its first client turn; return the provider models it wrote
        into the disposable OMP home and the selector its turns use. No hook or client runs."""
        seen = {}
        def first_turn(args, home, lifecycle, receipt):
            models = json.loads((home / ".omp/agent/models.yml").read_text(encoding="utf-8"))
            seen["models"] = [model["id"] for model in models["providers"]["ninfer-acceptance"]["models"]]
            seen["selector"] = args.model
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary, key = root / "omp", root / "key"
            binary.write_bytes(b"fixture client")
            key.write_text("synthetic-test-key\n")
            version = argparse.Namespace(returncode=0, stdout="omp/18.12.6\n")
            with patch.object(runner.probe, "launch", return_value=version), \
                 patch.object(runner, "run_checks", side_effect=first_turn), \
                 contextlib.redirect_stdout(io.StringIO()):
                runner.main(["--omp", str(binary), "--omp-sha256", runner.sha256(binary),
                             "--omp-version", "omp/18.12.6", "--endpoint", "http://127.0.0.1:9/v1",
                             "--key-file", str(key), "--restart-cmd", '["true"]', "--stop-cmd", '["true"]',
                             "--start-cmd", '["true"]', "--receipt", str(root / "receipt.json"), *selection])
        return seen

    def test_each_lane_defaults_to_the_model_its_server_serves(self):
        served = self.served_model_ids()
        lanes = [lane for lane in runner.LANES if lane != "rtx5090-container-host"]
        self.assertEqual(sorted(served), sorted(lanes))
        for lane in lanes:
            with self.subTest(lane=lane):
                seen = self.configured("--lane", lane)
                self.assertEqual(seen["models"], [served[lane]])
                self.assertEqual(seen["selector"], "ninfer-acceptance/" + served[lane])

    def test_an_explicit_model_id_replaces_the_lane_default(self):
        seen = self.configured("--lane", "rtx3090-native", "--model-id", "owner-model")
        self.assertEqual(seen, {"models": ["owner-model"], "selector": "ninfer-acceptance/owner-model"})

    def test_native_defaults_follow_a_candidates_renamed_provider_fragments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = candidate_checkout(Path(directory))
            with patch.object(runner, "ROOT", root), patch.object(runner, "DEFAULT_DOC", root / "docs/QUICKSTART.md"):
                for lane, model in (("rtx3090-native", "candidate-3090"), ("rtx4090-native", "candidate-4090")):
                    with self.subTest(lane=lane):
                        seen = self.configured("--lane", lane)
                        self.assertEqual(seen, {"models": [model], "selector": "ninfer-acceptance/" + model})


def candidate_checkout(root):
    """The candidate's guide, provider fragments and hash-bound native configs; no host state."""
    guide = root / "docs/QUICKSTART.md"
    guide.parent.mkdir(parents=True)
    guide.write_bytes(runner.DEFAULT_DOC.read_bytes())
    for fragment, model in (
        ("manual-tunnel/models.fragment.yml", "candidate-5090"),
        ("windows-docker-local/models.fragment.yml", "candidate-5090"),
        ("windows-native/models.fragment.yml", "candidate-4090"),
        ("windows-native/models-rtx3090.fragment.yml", "candidate-3090"),
    ):
        target = root / "examples" / fragment
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(re.sub(r"(?m)^      - id: \S+$", "      - id: " + model,
                                (ROOT / "examples" / fragment).read_text()), encoding="utf-8")
    release = json.loads((ROOT / "compatibility.json").read_text())["product_release"]
    (root / "compatibility.json").write_text(json.dumps({"product_release": release}))
    manifest = json.loads((ROOT / "releases" / release / "manifest.json").read_text())
    for variant in manifest["components"]["ninfer_variants"]:
        lane = variant["id"].split("-")[0]
        source = ROOT / "releases" / release / "profiles" / lane / "server-config.json"
        config = json.loads(source.read_text())
        config["model_id"] = "candidate-" + lane[3:]
        target = root / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(config))
        variant["configuration_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
        qualification = variant.get("qualification", {})
        if "server_config" in qualification:
            qualification["server_config"]["sha256"] = variant["configuration_sha256"]
        if "release_spec" in qualification:
            reference = qualification["release_spec"]["path"]
            destination = root / reference
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((ROOT / reference).read_bytes())
    (root / "releases" / release / "manifest.json").write_text(json.dumps(manifest))
    return root


class ProbeModelDefaultsTests(unittest.TestCase):
    PROBES = {
        "agent_mix_probe": ["--dry-run"],
        "concurrency_probe": ["--api-key-file", "unused-key", "--receipt", "unused.json", "--scenario", "solo"],
        "engine_window_compare": ["--arm", "fixture", "--wire", "fork", "--base-url", "http://127.0.0.1:9",
                                  "--api-key-file", "unused-key", "--long-fixture", "unused-fixture",
                                  "--log-cmd", "true", "--receipt", "unused.json"],
        "fleet_probe": ["--lane", "measurement-label", "--base-url", "http://127.0.0.1:9",
                        "--api-key-file", "unused-key"],
        "multisession_probe": ["--lane", "measurement-label", "--base-url", "http://127.0.0.1:9",
                               "--api-key-file", "unused-key", "--log-cmd", "true", "--receipt", "unused.json"],
        "restore_probe": ["--lane", "measurement-label", "--base-url", "http://127.0.0.1:9",
                          "--api-key-file", "unused-key", "--restart-cmd", "true"],
        "sibling_continue_probe": ["--lane", "measurement-label", "--base-url", "http://127.0.0.1:9",
                                   "--api-key-file", "unused-key", "--receipt", "unused.json"],
        "omp_parallel_proof": ["--omp", "unused", "--omp-sha256", "a" * 64, "--omp-version", "omp/18.14.0",
                               "--home", "unused-home", "--log-cmd", "true", "--receipt", "unused.json"],
    }

    def parsed_model(self, name, extra):
        spec = importlib.util.spec_from_file_location("model_default_" + name, ROOT / "scripts" / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        captured = []
        parse = argparse.ArgumentParser.parse_args
        read_text = Path.read_text

        class BeforeWork(Exception):
            pass

        def record(parser, *args, **kwargs):
            result = parse(parser, *args, **kwargs)
            captured.append(result)
            return result

        def before_key(path, *args, **kwargs):
            if path.name == "unused-key":
                raise BeforeWork
            return read_text(path, *args, **kwargs)

        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(argparse.ArgumentParser, "parse_args", record))
            stack.enter_context(patch.object(Path, "read_text", before_key))
            stack.enter_context(patch.object(sys, "argv", [name, *self.PROBES[name], *extra]))
            if name == "agent_mix_probe":
                stack.enter_context(patch.object(module, "build_agents", side_effect=BeforeWork))
            if name == "omp_parallel_proof":
                stack.enter_context(patch.object(module, "expected_client_identity", side_effect=BeforeWork))
            with self.assertRaises(BeforeWork):
                module.main()
        return captured[0].model

    def test_every_probe_default_follows_the_guides_candidate_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = candidate_checkout(Path(directory))
            with patch.object(runner, "ROOT", root), patch.object(runner, "DEFAULT_DOC", root / "docs/QUICKSTART.md"):
                for name in self.PROBES:
                    with self.subTest(probe=name):
                        expected = "ninfer-beta/candidate-5090" if name == "omp_parallel_proof" else "candidate-5090"
                        self.assertEqual(self.parsed_model(name, []), expected)

    def test_explicit_probe_models_do_not_require_a_guide(self):
        with patch.object(runner, "documented_model_id", side_effect=AssertionError("explicit model read the guide")):
            for name in self.PROBES:
                with self.subTest(probe=name):
                    model = "ninfer-beta/owner-model" if name == "omp_parallel_proof" else "owner-model"
                    self.assertEqual(self.parsed_model(name, ["--model", model]), model)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for campaign model lookup")
    def test_campaign_launchers_resolve_their_candidates_model_before_host_work(self):
        with tempfile.TemporaryDirectory() as directory:
            root = candidate_checkout(Path(directory))
            for relative in ("client_acceptance.py", "documented_route.py", "omp_client_environment.py",
                             "stock_omp_session_proof.py", "hosts/omp-client-probe.py"):
                target = root / "scripts" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / "scripts" / relative).read_bytes())
            for gpu, expected in (("3090", "candidate-3090"), ("5090", "candidate-5090")):
                source = (ROOT / "scripts/hosts" / f"run_variant_campaign_{gpu}.ps1").read_text()
                lookup = source[source.index("$modelId ="):source.index("$sourceCommit =")]
                quote = lambda value: "'" + str(value).replace("'", "''") + "'"
                command = ("$ErrorActionPreference = 'Stop'\n"
                           f"$PSScriptRoot = {quote(root / 'scripts/hosts')}\n"
                           f"function python {{ & {quote(sys.executable)} @args }}\n"
                           + lookup + "\nWrite-Output $modelId\n")
                with self.subTest(gpu=gpu):
                    result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-Command", command],
                                            capture_output=True, text=True, timeout=60)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.strip(), expected)

    @unittest.skipIf(os.name == "nt", "executes the staged POSIX quality child")
    def test_quality_child_refuses_an_implicit_model_before_any_work(self):
        result = subprocess.run(["bash", str(ROOT / "scripts/hosts/quality.sh"),
                                 "rtx5090", "fixture", "campaign", "http://127.0.0.1:9/v1", "unused-key"],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn("<model-id>", result.stderr)


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
