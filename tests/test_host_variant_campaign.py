"""Host-free matched campaign contracts, including failure cleanup and trace attribution."""
from __future__ import annotations

from contextlib import closing
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/hosts"))
SPEC = importlib.util.spec_from_file_location("host_variant_campaign", ROOT / "scripts/hosts/variant_campaign.py")
assert SPEC and SPEC.loader
HOST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOST)


class CampaignTests(unittest.TestCase):
    def plan(self, root):
        binary, model = root / "server", root / "model"
        binary.write_bytes(b"binary")
        model.write_bytes(b"model")
        return {"lane": "rtx4090", "gpu_uuid": "GPU-selected", "model_path": str(model),
                "config": {"engine": {"max_context": 131072, "prefill_chunk": 2048},
                           "speculative": {"backend": "mtp", "draft_tokens": 3}},
                "arms": {label: {"binary": str(binary)} for label in ("A", "B")}}

    def identity(self):
        return {"binary_sha256": "b", "config_sha256": "c", "model_sha256": "m",
                "gpu": {"uuid": "GPU-selected", "driver": "driver", "power_limit_w": 450}}

    def arms(self):
        return [{"arm": label, "identity": self.identity(), "requests": [
                    {"id": "case", "completion_tokens": 100, "decode_seconds": 1 if label == "A" else 0.8,
                     "decode_tokens_per_second": 100 if label == "A" else 125, "output_sha256": "same",
                     "request_sha256": "request"}]}
                for label in HOST.ORDER]

    def test_abba_uses_weighted_rates_and_real_digest_equality(self):
        arms = self.arms()
        result = HOST.summarize_arms(arms)
        self.assertEqual(result["candidate_baseline_decode_ratio"], 1.25)
        self.assertTrue(result["per_case"]["case"]["all_output_digests_identical"])
        self.assertIsNone(result["all_output_bytes_identical"])
        arms[2]["requests"][0]["output_sha256"] = "different"
        self.assertFalse(HOST.summarize_arms(arms)["per_case"]["case"]["all_output_digests_identical"])

    def test_byte_identity_reads_actual_private_outputs_and_refuses_changed_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arms = self.arms()
            for index, arm in enumerate(arms):
                directory = root / f"{index}-{arm['arm']}"
                directory.mkdir()
                path = directory / "output.json"
                path.write_bytes(b"actual output")
                arm["requests"][0].update(output_file=path.name, output_sha256=HOST.sha256_file(path))
            self.assertTrue(HOST.summarize_arms(arms, root)["all_output_bytes_identical"])
            changed = root / "2-B/output.json"
            changed.write_bytes(b"different bytes")
            with self.assertRaisesRegex(HOST.CampaignError, "output evidence changed"):
                HOST.summarize_arms(arms, root)
            arms[2]["requests"][0]["output_sha256"] = HOST.sha256_file(changed)
            self.assertFalse(HOST.summarize_arms(arms, root)["all_output_bytes_identical"])

    def test_missing_case_or_changed_repeat_identity_is_refused(self):
        for mutation in (lambda arms: arms[2]["requests"].clear(),
                         lambda arms: arms[3]["identity"].update(binary_sha256="other"),
                         lambda arms: arms[2]["identity"]["gpu"].update(power_limit_w=350),
                         lambda arms: arms[1]["identity"].update(model_sha256="other"),
                         lambda arms: arms[3]["identity"].update(seccomp_profile_sha256="changed"),
                         lambda arms: arms[1]["requests"][0].update(request_sha256="other")):
            arms = self.arms()
            mutation(arms)
            with self.assertRaises(HOST.CampaignError):
                HOST.summarize_arms(arms)

    def test_plan_requires_uuid_and_two_real_binaries(self):
        with tempfile.TemporaryDirectory() as temp:
            plan = self.plan(Path(temp))
            HOST.validate_plan(plan, "rtx4090")
            plan["gpu_uuid"] = "0"
            with self.assertRaises(HOST.CampaignError):
                HOST.validate_plan(plan, "rtx4090")
            plan["gpu_uuid"] = "GPU-selected"
            plan["arms"]["C"] = plan["arms"]["A"]
            with self.assertRaises(HOST.CampaignError):
                HOST.validate_plan(plan, "rtx4090")

    def test_effective_config_deep_merges_without_mutating_baseline(self):
        with tempfile.TemporaryDirectory() as temp:
            plan = self.plan(Path(temp))
            arm = {"overrides": {"engine": {"prefill_chunk": 1024},
                                 "speculative": {"backend": "dflash2", "draft_tokens": 7}}}
            result = HOST.effective_config(plan, arm)
            self.assertEqual(result["engine"], {"max_context": 131072, "prefill_chunk": 1024})
            self.assertEqual(plan["config"]["engine"]["prefill_chunk"], 2048)

    def test_generated_argv_preserves_checkpoint_and_backend_profile(self):
        paths = {key: key for key in ("model", "port", "key_file", "model_id", "binary_sha256",
                                      "model_sha256", "log", "checkpoints")}
        config = {"engine": {"prefill_chunk": 1024, "prefix_reuse": False},
                  "speculative": {"backend": "dflash2", "draft_tokens": 7},
                  "context_cache": {"host_context_mib": "14787.734375", "device_state_slots": 2},
                  "session_checkpoint": {"enabled": True, "quota_mib": 24576, "staging_mib": 256,
                                         "require_origin_auth": True}}
        args = HOST.server_arguments(config, paths, {})
        self.assertIn("--no-prefix-reuse", args)
        self.assertEqual(args[args.index("--spec") + 1], "dflash2")
        self.assertEqual(args[args.index("--draft-tokens") + 1], "7")
        self.assertEqual(args[args.index("--session-checkpoint-dir") + 1], "checkpoints")
        self.assertIn("--session-checkpoint-require-origin-auth", args)
        self.assertEqual(args.count("--request-log-jsonl"), 1)

    def test_c1_is_the_qualification_prompt_and_exact_usage_is_required(self):
        self.assertEqual(len(HOST.C1_PROMPT.split("\nContinue")[0]), 28000)
        server = MagicMock(paths={"model_id": "qwen3.8-27b"})
        row = {"prompt_tokens": 4541, "computed_prefill_tokens": 4541, "completion_tokens": 1024,
               "prefix_cache_hit_tokens": 0}
        with patch.object(HOST, "request_metrics", return_value=row) as request:
            self.assertEqual(HOST.c1(server), [row])
            body = request.call_args.args[1]
            self.assertEqual((body["seed"], body["reasoning_effort"], body["max_tokens"]),
                             (57004, "medium", 1024))
            row["computed_prefill_tokens"] = 4539
            with self.assertRaises(HOST.CampaignError):
                HOST.c1(server)

    def test_capture_retains_exact_model_output_bytes_separately_from_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            server = MagicMock(directory=root, plan={}, root="http://127.0.0.1", key="key")
            record = {"event": "request_done",
                      "result": {"prompt_tokens": 7, "computed_prefill_tokens": 7, "completion_tokens": 5},
                      "timings_seconds": {"decode": 0.2, "prefill": 0.1},
                      "speculative": {"rounds": 2, "drafted_tokens": 6, "accepted_tokens": 3, "backend": "mtp"}}
            tool = {"id": "transport-only", "function": {"name": "read", "arguments": "{}"}}
            def respond(*unused, **kwargs):
                (root / "requests.jsonl").write_text(json.dumps(record) + "\n")
                return {"choices": [{"message": {"content": "exact\r\nfinal", "reasoning_content": None,
                                                  "reasoning": "a reason", "tool_calls": [tool]},
                                      "finish_reason": "length"}]}
            with patch.object(HOST, "http", side_effect=respond):
                row = HOST.request_metrics(server, {"model": "test"}, "case")
            path = root / row["output_file"]
            self.assertEqual(json.loads(path.read_bytes()),
                             ["exact\r\nfinal", "a reason", [{"function": tool["function"]}]])
            self.assertEqual(row["output_sha256"], HOST.sha256_file(path))
            self.assertNotIn("content", row)
            self.assertNotIn("reasoning", row)

    def test_power_and_owned_process_are_restored_on_workload_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.plan(root)
            plan["arms"]["A"]["power_limit_w"] = 300
            path = root / "plan.json"
            HOST.save(path, plan)
            current = [450]
            def selected_gpu(*unused):
                return {"uuid": "GPU-selected", "driver": "driver", "power_limit_w": current[0],
                        "memory_used_mib": 1}
            def power(unused, watts):
                current[0] = watts
            server = MagicMock(binary_sha="b", version="v", argv=["server"],
                               paths={"model_id": "model"}, root="http://127.0.0.1", key="key", seccomp_profile=None)
            sampler = MagicMock()
            sampler.rows = []
            with patch.object(HOST, "gpu", side_effect=selected_gpu), \
                 patch.object(HOST, "set_power", side_effect=power) as limits, \
                 patch.object(HOST, "Server", return_value=server), \
                 patch.object(HOST, "Sampler", return_value=sampler), \
                 patch.object(HOST, "http", return_value={}), \
                 patch.object(HOST, "c1", side_effect=HOST.CampaignError("workload failed")):
                with self.assertRaises(HOST.CampaignError):
                    HOST.run_campaign("rtx4090", path, root / "out", arm_index=0)
                self.assertEqual(current[0], 450)
                self.assertEqual([call.args[1] for call in limits.call_args_list], [300, 450])
                server.stop.assert_called_once()
                receipt = HOST.load(root / "out/0-A/receipt.json")
                self.assertEqual(receipt["status"], "failed")
                self.assertEqual(receipt["restored_power_limit_w"], 450)

    def test_changed_plan_and_failed_predecessor_cannot_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.plan(root)
            path = root / "plan.json"
            HOST.save(path, plan)
            out = root / "out"
            out.mkdir()
            HOST.save(out / "campaign.json", {"plan_sha256": "wrong", "mode": "c1"})
            with self.assertRaisesRegex(HOST.CampaignError, "different frozen plan"):
                HOST.run_campaign("rtx4090", path, out, arm_index=1)
            HOST.save(out / "campaign.json", {"plan_sha256": HOST.sha256_file(path), "mode": "c1",
                                            "runner_sha256": HOST.sha256_file(Path(HOST.__file__))})
            (out / "0-A").mkdir()
            HOST.save(out / "0-A/receipt.json", {"status": "failed"})
            with self.assertRaisesRegex(HOST.CampaignError, "failed preceding arm"):
                HOST.run_campaign("rtx4090", path, out, arm_index=1)
            HOST.save(out / "campaign.json", {"plan_sha256": HOST.sha256_file(path), "mode": "c1",
                                            "runner_sha256": "changed"})
            with self.assertRaisesRegex(HOST.CampaignError, "different frozen runner"):
                HOST.run_campaign("rtx4090", path, out, arm_index=1)

    def test_existing_endpoint_is_refused_before_process_launch(self):
        server = object.__new__(HOST.Server)
        server.paths = {"port": "18082"}
        with patch.object(HOST.socket, "socket") as socket_, patch.object(HOST.subprocess, "Popen") as popen:
            socket_.return_value.__enter__.return_value.connect_ex.return_value = 0
            with self.assertRaises(HOST.CampaignError):
                server.start()
            popen.assert_not_called()

    def test_container_identity_mounts_selected_driver_even_for_version(self):
        server = object.__new__(HOST.Server)
        server.container = "ov-Harness-identity"
        server.plan = {"gpu_uuid": "GPU-selected"}
        server.arm = {"image": "sha256:fixed"}
        server.docker_security_args = ["--security-opt", "seccomp=reviewed.json"]
        args = server.image_command(["/bin/server", "--version"])
        self.assertEqual(args[args.index("--gpus") + 1], "device=GPU-selected")
        self.assertEqual(args[args.index("--security-opt") + 1], "seccomp=reviewed.json")
        self.assertEqual(args[-2:], ["sha256:fixed", "--version"])

    def test_removed_lane_and_sampler_scripts_have_no_second_entrypoint(self):
        hosts = ROOT / "scripts/hosts"
        for name in ("run_variant_campaign_3090.ps1", "run_variant_campaign_4090.ps1",
                     "run_variant_campaign_5090.ps1", "vram-sampler.ps1", "vram-sampler.sh"):
            self.assertFalse((hosts / name).exists())
        text = (hosts / "run_variant_campaign.ps1").read_text()
        self.assertIn("[string]$Lane", text)
        self.assertNotIn("wsl.exe", text)

    def test_powered_failure_or_invalidity_is_not_a_successful_cli_exit(self):
        for verdict, expected in (("pass", 0), ("fail", 1), ("invalid", 2)):
            with patch.object(HOST, "run_campaign", return_value={"quality": {"verdict": verdict}}), \
                 patch("sys.stdout", new=io.StringIO()):
                self.assertEqual(HOST.main(["--lane", "rtx4090", "--plan", "plan.json",
                                            "--out", "out", "--mode", "quality"]), expected)


class TraceTests(unittest.TestCase):
    def test_gpu_work_is_attributed_by_launch_correlation_not_cpu_time_overlap(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.sqlite"
            with closing(sqlite3.connect(path)) as db:
                db.executescript('''
CREATE TABLE StringIds (id INTEGER, value TEXT);
INSERT INTO StringIds VALUES (1,'q5_linear'),(2,'cudaGraphLaunch_v12000');
CREATE TABLE CUPTI_ACTIVITY_KIND_KERNEL (demangledName INTEGER,start INTEGER,end INTEGER,correlationId INTEGER);
INSERT INTO CUPTI_ACTIVITY_KIND_KERNEL VALUES (1,100,150,7),(1,200,270,8);
CREATE TABLE CUPTI_ACTIVITY_KIND_RUNTIME (nameId INTEGER,start INTEGER,end INTEGER,correlationId INTEGER);
INSERT INTO CUPTI_ACTIVITY_KIND_RUNTIME VALUES (2,20,30,7),(2,60,80,8);
CREATE TABLE NVTX_EVENTS (start INTEGER,end INTEGER,text TEXT,textId INTEGER);
INSERT INTO NVTX_EVENTS VALUES (10,40,'decode.mtp.round',NULL),(50,90,'decode.dflash.round',NULL),(10,40,'prefill.chunk',NULL);
''')
            result = HOST.nsys_summary(path)
            self.assertEqual(result["cuda_graph_launch"][0]["cpu_ns"], 30)
            self.assertEqual(result["per_op"][0]["gpu_ns"], 120)
            self.assertEqual(result["per_op_by_round"]["decode.mtp.round"]["per_op"][0]["gpu_ns"], 50)
            self.assertEqual(result["per_op_by_round"]["decode.mtp.round"]["per_op"][0]["name"], "q5_linear")
            self.assertEqual(result["per_op_by_round"]["decode.dflash.round"]["per_op"][0]["gpu_ns"], 70)
            self.assertEqual(result["per_op_by_prefill_range"]["prefill.chunk"][0]["gpu_ns"], 50)
            self.assertEqual(result["per_op_by_prefill_range"]["prefill.chunk"][0]["per_op"][0]["gpu_share"], 1)

    def test_empty_or_non_cuda_capture_is_not_success(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "empty.sqlite"
            with closing(sqlite3.connect(path)) as db:
                db.execute("CREATE TABLE StringIds (id INTEGER,value TEXT)")
            with self.assertRaises(HOST.CampaignError):
                HOST.nsys_summary(path)


if __name__ == "__main__":
    unittest.main()
