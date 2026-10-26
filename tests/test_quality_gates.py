"""Risk gates bind real capture files, compare bytes/tokens, and refuse incomplete evidence."""
from __future__ import annotations

import copy
import importlib.util
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("quality_gates", ROOT / "scripts/quality_gates.py")
assert SPEC and SPEC.loader
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)
H = GATE.host
Q = GATE.quality
SOURCE = "a" * 40
VERSION = "ninfer-serve patch_stack_sha=" + SOURCE + " build_profile=native-test"


class RiskGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cases = self.root / "cases"
        self.cases.mkdir()
        self.qualification = self.root / "qualification"
        (self.qualification / "scripts").mkdir(parents=True)
        # A fixture for the private validator interface; production imports the frozen full validator.
        (self.qualification / "scripts/_qual.py").write_text(
            "def validate_schema_instance(schema, value):\n"
            " if not isinstance(value, dict): return ['not object']\n"
            " errors=[]\n"
            " for key in schema.get('required', []):\n"
            "  if key not in value: errors.append('missing:'+key)\n"
            " for key, rule in schema.get('properties', {}).items():\n"
            "  if key in value and rule.get('type')=='integer' and type(value[key]) is not int: errors.append('wrong type:'+key)\n"
            " return errors\n")
        self.case_rows = []
        classes = ["log-triage", "repository-evidence", "work-log-extraction", "regression-contract", "structured-output"]
        for index in range(84):
            row = {"case_id": f"case-{index:03d}", "class": classes[index % len(classes)],
                   "input": {"context": "fixture evidence", "task": "Answer."},
                   "oracle": {"forbidden_claims": ["fabricated fact"]},
                   "safety": {"contains_synthetic_secret": index < 7}}
            if index == 0:
                row["response_format"] = {"type": "json_schema", "json_schema": {"schema": {
                    "type": "object", "required": ["value"], "properties": {"value": {"type": "integer"}}}}}
            if index == 1:
                row["tools"] = [{"type": "function", "function": {"name": "lookup", "parameters": {
                    "type": "object", "required": ["x"], "properties": {"x": {"type": "integer"}}}}}]
                row["oracle"]["expected_tool"] = "lookup"
            self.case_rows.append(row)
        (self.cases / "cases.jsonl").write_text("".join(json.dumps(row) + "\n" for row in self.case_rows))
        binary, model = self.root / "server", self.root / "model"
        binary.write_bytes(b"server")
        model.write_bytes(b"model")
        fixture = self.root / "long.json"
        fixture.write_text("[]")
        self.plan_data = {"lane": "rtx4090", "gpu_uuid": "GPU-selected", "model_path": str(model),
                          "model_sha256": H.sha256_file(model), "model_id": "qwen3.8-27b",
                          "cases": str(self.cases), "qualification": str(self.qualification),
                          "fixtures": str(self.root), "retrieval_fixture": str(fixture),
                          "config": {}, "arms": {name: {"binary": str(binary)} for name in ("A", "B")}}
        self.plan = self.root / "plan.json"
        H.save(self.plan, self.plan_data)
        self.identity = {"binary_sha256": H.sha256_file(binary), "binary_version": VERSION,
                         "model_sha256": H.sha256_file(model), "config_sha256": "config", "image": None,
                         "seccomp_profile_sha256": None,
                         "gpu": {"uuid": "GPU-selected", "driver": "driver", "power_limit_w": 450}}
        self.fingerprint = {"lane": "rtx4090", "arms": {"A": self.identity, "B": self.identity},
                            "inputs": {"frozen": "bytes"}, "preregistration_sha256": "rule", "tools": {"tool": "bytes"},
                            "capture_contract": dict(Q.CAPTURE_CONTRACT, model_id="qwen3.8-27b")}
        self.mutate = lambda row, score, values, index: None
        self.fp_patch = patch.object(Q, "pair_fingerprint", return_value=self.fingerprint)
        self.fp_patch.start()
        self.addCleanup(self.fp_patch.stop)
        self.capture_patch = patch.object(H, "capture_arm", side_effect=self.capture)
        self.capture_mock = self.capture_patch.start()
        self.addCleanup(self.capture_patch.stop)
        self.command_patch = patch.object(H, "command", return_value=types.SimpleNamespace(stdout=VERSION))
        self.command_patch.start()
        self.addCleanup(self.command_patch.stop)
        self.baseline = self.root / "baseline"

    def capture(self, lane, plan, model_sha, key, index, directory, mode, **kwargs):
        directory.mkdir()
        identity = self.fingerprint["arms"]["A" if index == 0 else "B"]
        if mode == "retrieval":
            output = directory / "answer.json"
            output.write_text(json.dumps([GATE.ROLE_RULE["retrieval_answer"], "", []], separators=(",", ":")))
            receipt = {"status": "passed", "identity": identity, "wall_seconds": 10,
                       "requests": [{"prompt_tokens": 130048, "exact": True, "output_file": output.name,
                                     "output_sha256": H.sha256_file(output)}]}
            H.save(directory / "receipt.json", receipt)
            return receipt
        cases = GATE.records(kwargs["quality_cases"])
        run = directory / "quality"
        run.mkdir()
        responses, scores, events = [], [], []
        for request_id, case in enumerate(cases, 1):
            base = Q.base_id(case["case_id"])
            row = {"case_id": case["case_id"], "content": '{"value":1}' if base == "case-000" else "answer",
                   "reasoning": "reason", "tool_calls": [], "finish_reason": "stop", "error": None,
                   "attempt": 1, "usage": {"completion_tokens": 3}}
            if base == "case-001":
                row["content"] = ""
                row["tool_calls"] = [{"id": "transport-" + str(index), "index": 0, "name": "lookup", "arguments": '{"x":1}'}]
            score = {"case_id": case["case_id"], "class": case["class"],
                     "is_redaction_control": bool(case["safety"]["contains_synthetic_secret"]),
                     "unsupported_claim": False, "secret_leaks": [], "schema_valid": True,
                     "required_facts_found": 1, "required_facts_total": 1}
            values = [request_id, 11, 12]
            self.mutate(row, score, values, index)
            responses.append(row)
            scores.append(score)
            events.append({"event": "request_done", "request": {"request_id": request_id},
                           "result": {"generated_token_ids": values, "completion_tokens": 3}})
        (run / "responses.jsonl").write_text("".join(json.dumps(row) + "\n" for row in responses))
        (directory / "requests.jsonl").write_text("".join(json.dumps(row) + "\n" for row in events))
        H.save(run / "scores.json", {"per_case": scores, "corpus_sha256": "corpus"})
        H.save(run / "manifest.json", {**self.fingerprint["capture_contract"], "corpus_sha256": "corpus",
                                       "case_files": [{"sha256": H.sha256_file(kwargs["quality_cases"])}], "case_count": len(cases)})
        receipt = {"status": "passed", "identity": identity, "wall_seconds": len(cases) * 2, "requests": []}
        H.save(directory / "receipt.json", receipt)
        return receipt

    def cache(self, kind="role", **kwargs):
        with patch.object(GATE, "verify_ppl", return_value={"verdict": "pass"}):
            return GATE.run_gate("cache", "rtx4090", self.plan, self.baseline, kind=kind,
                                  ppl=Path("ppl"), **kwargs)

    def test_role_and_math_plans_are_deterministic_complete_and_balanced(self):
        role, _ = GATE.sample_plan(self.cases, "role", 84)
        self.assertEqual(len(role["jobs"][0]["prompt_ids"]), 84)
        layout, files = GATE.sample_plan(self.cases, "math", 50)
        self.assertEqual((layout, files), GATE.sample_plan(self.cases, "math", 50))
        self.assertEqual(len(layout["jobs"]), 4)
        self.assertEqual(len(layout["categories"]), 200)
        first = [sample for job in layout["jobs"][:2] for sample in job["prompt_ids"]]
        self.assertEqual({Q.base_id(sample) for sample in first}, set(layout["selected_cases"]))
        for job in layout["jobs"]:
            self.assertEqual(sum(layout["categories"][sample] == "secrets" for sample in job["prompt_ids"]), 25)
        with self.assertRaises(Q.ScreenError):
            GATE.sample_plan(self.cases, "role", 0)

    def test_t1_self_pair_compares_actual_bytes_and_freezes_baseline(self):
        self.cache()
        self.capture_mock.reset_mock()
        result = GATE.run_gate("t1", "rtx4090", self.plan, self.root / "t1", baseline=self.baseline)
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["byte_comparison"]["identical"], 84)
        self.assertEqual(result["byte_comparison"]["differing_cases"], [])
        self.assertEqual(self.capture_mock.call_count, 1)
        self.assertEqual(self.capture_mock.call_args.args[4], 1)

    def test_t1_lists_raw_argument_byte_changes_and_exact_token_index(self):
        self.cache()
        def change(row, score, values, index):
            if index == 1 and row["case_id"] == "case-001":
                row["tool_calls"][0]["arguments"] = '{"x": 1}'
                values[1] = 99
        self.mutate = change
        result = GATE.run_gate("t1", "rtx4090", self.plan, self.root / "t1", baseline=self.baseline)
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(result["byte_comparison"]["differing_cases"], ["case-001"])
        case = next(row for row in result["byte_comparison"]["per_case"] if row["case_id"] == "case-001")
        self.assertEqual(case["first_divergent_token_index"], 1)

    def test_baseline_model_profile_prompt_sampling_or_retained_bytes_cannot_change(self):
        self.cache()
        self.capture_mock.reset_mock()
        for field, value in (("model_sha256", "other"), ("config_sha256", "other"), ("binary_sha256", "other")):
            changed = copy.deepcopy(self.fingerprint)
            changed["arms"]["A"][field] = value
            changed["arms"]["B"][field] = value
            with patch.object(Q, "pair_fingerprint", return_value=changed), self.assertRaises(Q.ScreenError):
                GATE.run_gate("t1", "rtx4090", self.plan, self.root / "t1", baseline=self.baseline)
        output = self.baseline / "capture-0000/attempt-0000/output-bytes.json"
        output.write_text("{}")
        with self.assertRaises(Q.ScreenError):
            GATE.run_gate("t1", "rtx4090", self.plan, self.root / "t1", baseline=self.baseline)
        self.capture_mock.assert_not_called()

    def test_missing_token_artifacts_are_refused_not_recreated(self):
        self.cache()
        (self.baseline / "capture-0000/attempt-0000/token-ids.json").unlink()
        self.capture_mock.reset_mock()
        with self.assertRaises(Q.ScreenError):
            GATE.run_gate("t1", "rtx4090", self.plan, self.root / "t1", baseline=self.baseline)
        self.capture_mock.assert_not_called()

    def test_token_binding_refuses_retries_counts_and_extra_server_requests(self):
        self.cache()
        capture = self.baseline / "capture-0000/attempt-0000"
        responses = GATE.records(capture / "quality/responses.jsonl")
        changed = copy.deepcopy(responses)
        changed[0]["attempt"] = 2
        with self.assertRaises(Q.ScreenError):
            GATE.token_ids(capture, changed)
        events = GATE.records(capture / "requests.jsonl")
        (capture / "requests.jsonl").write_text("".join(json.dumps(row) + "\n" for row in reversed(events)))
        bound = GATE.token_ids(capture, responses)
        self.assertEqual(bound["case-000"][0], 1)
        self.assertEqual(bound["case-083"][0], 84)
        changed = copy.deepcopy(responses)
        changed[0]["usage"]["completion_tokens"] = 4
        with self.assertRaises(Q.ScreenError):
            GATE.token_ids(capture, changed)
        with (capture / "requests.jsonl").open("a") as file:
            file.write(json.dumps({"event": "request_error"}) + "\n")
        with self.assertRaises(Q.ScreenError):
            GATE.token_ids(capture, responses)

    def test_task_checks_validate_full_schema_and_tool_argument_types(self):
        rows = {
            "case-000": {"content": '{"value":"wrong type"}'},
            "case-001": {"content": "", "tool_calls": [{"name": "lookup", "arguments": '{"x":"wrong type"}'}]},
        }
        result = GATE.task_checks(self.cases, rows, self.qualification)
        self.assertEqual(result["failure_count"], 2)
        self.assertEqual(result["json_schema_cases"], 1)
        self.assertEqual(result["tool_cases"], 1)
        for bad in (["bad"], [{"function": "bad"}], [{"name": "lookup", "arguments": "not JSON"}]):
            rows["case-001"]["tool_calls"] = bad
            self.assertEqual(GATE.task_checks(self.cases, rows, self.qualification)["failure_count"], 2)

    def test_t2_requires_numerics_and_retrieval_then_reports_one_complete_verdict(self):
        self.cache()
        out = self.root / "t2"
        proof = {"passed": True, "source_sha": SOURCE}
        with patch.object(GATE, "verify_numerics", return_value=proof):
            first = GATE.run_gate("t2", "rtx4090", self.plan, out, baseline=self.baseline, numerics=Path("proof"))
            self.assertNotIn("verdict", first)
            self.assertEqual(first["status"], "role-complete-awaiting-retrieval")
            result = GATE.run_gate("t2", "rtx4090", self.plan, out, baseline=self.baseline,
                                   numerics=Path("proof"), resume=True)
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["task_checks"]["failure_count"], 0)
        self.assertEqual(result["retrieval"]["prompt_tokens"], 130048)
        self.assertTrue(result["retrieval"]["exact"])
        (out / "retrieval/answer.json").write_text("wrong")
        with patch.object(GATE, "verify_numerics", return_value=proof), self.assertRaises(Q.ScreenError):
            GATE.run_gate("t2", "rtx4090", self.plan, out, baseline=self.baseline,
                           numerics=Path("proof"), resume=True)

    def test_t2_nine_changed_cases_fail_the_preregistered_ten_percent_bar(self):
        self.cache()
        def change(row, score, values, index):
            if index == 1 and int(row["case_id"].split("-")[1]) >= 75:
                row["content"] += " changed"
        self.mutate = change
        with patch.object(GATE, "verify_numerics", return_value={"passed": True}):
            result = GATE.run_gate("t2", "rtx4090", self.plan, self.root / "t2", baseline=self.baseline,
                                   numerics=Path("proof"), max_shards=2)
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(len(result["byte_comparison"]["differing_cases"]), 9)

    def test_math_baseline_requires_ppl_then_t3_stops_after_100_identical_pairs(self):
        with self.assertRaises(Q.ScreenError):
            GATE.run_gate("cache", "rtx4090", self.plan, self.baseline, kind="math")
        self.cache("math", max_shards=4)
        self.capture_mock.reset_mock()
        out = self.root / "t3"
        with patch.object(GATE, "verify_ppl", return_value={"verdict": "pass"}):
            first = GATE.run_gate("t3", "rtx4090", self.plan, out, baseline=self.baseline, ppl=Path("proof"))
            self.assertEqual(first["verdict"], "continue")
            result = GATE.run_gate("t3", "rtx4090", self.plan, out, baseline=self.baseline,
                                   ppl=Path("proof"), resume=True)
            self.assertEqual(result["verdict"], "pass")
            self.assertEqual(result["paired_prompts"], 100)
            self.assertEqual(result["reason"], "early-identical-covered-pairs")
            calls = self.capture_mock.call_count
            resumed = GATE.run_gate("t3", "rtx4090", self.plan, out, baseline=self.baseline,
                                    ppl=Path("proof"), resume=True)
        self.assertEqual(resumed["verdict"], "pass")
        self.assertEqual(calls, self.capture_mock.call_count)

    def test_math_new_secret_stops_first_look_even_if_total_leak_count_is_unchanged(self):
        def baseline_leak(row, score, values, index):
            if row["case_id"] == "case-002.v0":
                score["secret_leaks"] = ["old-secret" if index == 0 else "new-secret"]
        self.mutate = baseline_leak
        self.cache("math", max_shards=4)
        with patch.object(GATE, "verify_ppl", return_value={"verdict": "pass"}):
            result = GATE.run_gate("t3", "rtx4090", self.plan, self.root / "t3", baseline=self.baseline,
                                   ppl=Path("proof"), max_shards=4)
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(result["paired_prompts"], 50)
        self.assertEqual(result["new_secret_leak_cases"], ["case-002.v0"])

    def test_math_nonidentical_nonregressing_outputs_must_complete_all_200(self):
        self.cache("math", max_shards=4)
        def change(row, score, values, index):
            if index == 1 and Q.base_id(row["case_id"]) == "case-050":
                row["reasoning"] += " changed"
        self.mutate = change
        with patch.object(GATE, "verify_ppl", return_value={"verdict": "pass"}):
            result = GATE.run_gate("t3", "rtx4090", self.plan, self.root / "t3", baseline=self.baseline,
                                   ppl=Path("proof"), max_shards=4)
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["paired_prompts"], 200)

    def test_math_claim_regressions_are_not_offset_by_improvements(self):
        self.cache("math", max_shards=4)
        def change(row, score, values, index):
            if index == 1 and int(Q.base_id(row["case_id"]).split("-")[1]) in range(7, 35):
                score["unsupported_claim"] = True
        self.mutate = change
        with patch.object(GATE, "verify_ppl", return_value={"verdict": "pass"}):
            result = GATE.run_gate("t3", "rtx4090", self.plan, self.root / "t3", baseline=self.baseline,
                                   ppl=Path("proof"), max_shards=4)
        self.assertEqual(result["verdict"], "fail")
        self.assertGreater(len(result["introduced_unsupported_cases"]), 6)
        self.assertLess(result["paired_prompts"], 200)

    def test_ppl_failure_prevents_any_math_capture(self):
        self.capture_mock.reset_mock()
        with patch.object(GATE, "verify_ppl", return_value={"verdict": "fail"}):
            result = GATE.run_gate("t3", "rtx4090", self.plan, self.root / "t3", baseline=self.baseline,
                                   ppl=Path("proof"))
        self.assertEqual(result["verdict"], "fail")
        self.capture_mock.assert_not_called()

    def test_fp64_reduction_is_bound_to_the_actual_log_and_binary(self):
        log = self.root / "ctest.log"
        text = []
        for number, name in enumerate(GATE.FP64_TESTS, 1):
            executable = self.root / (name + ".exe")
            executable.write_bytes(name.encode())
            text += [f"Start {number}: {name}", f'{number}: Test command: "{executable}"', f"{number}: OP_ERROR_STATS kind=reduction count=32 rel_l2=0.001 rel_l2_limit=0.002 rel_l2_ratio=0.5 rmse=0.001 reference_rms=1 max_abs=0.01 max_reference=1 gross_limit=0.02 gross_ratio=0.5 non_finite=0 case=T=1"]
        text.append("100% tests passed, 0 tests failed out of 4")
        log.write_text("\n".join(text))
        binary = Path(self.plan_data["arms"]["B"]["binary"])
        proof = GATE.fp64_report(log, binary)
        self.assertTrue(proof["passed"])
        proof_path = self.root / "numeric.json"
        H.save(proof_path, proof)
        self.assertEqual(GATE.verify_numerics(proof_path, self.identity), proof)
        log.write_text(log.read_text().replace("non_finite=0", "non_finite=1"))
        with self.assertRaises(Q.ScreenError):
            GATE.verify_numerics(proof_path, self.identity)
        self.assertFalse(GATE.fp64_report(log, binary)["passed"])


class PerplexityTests(unittest.TestCase):
    def report(self, means=(1.0, 1.0), context=1024):
        domains = [{"domain": str(index), "scored_tokens": 100, "total_nll": mean * 100,
                    "mean_nll": mean, "perplexity": math.exp(mean)} for index, mean in enumerate(means)]
        mean = sum(means) / len(means)
        return {"schema_version": 2, "corpus": {"id": "frozen"},
                "metric": {"log_base": "natural"},
                "execution": {"context_tokens": context, "stride_tokens": context // 2, "kv_dtype": "int8", "purpose": "causal_scoring"},
                "domains": domains, "overall": {"scored_tokens": 200, "total_nll": mean * 200,
                                                   "mean_nll": mean, "perplexity": math.exp(mean)}}

    def test_real_schema2_nll_rules_and_matched_counts(self):
        off = self.report()
        self.assertTrue(GATE.compare_ppl(off, self.report((1.01, 1.01)))["passed"])
        self.assertFalse(GATE.compare_ppl(off, self.report((1.03, 1.03)))["passed"])
        self.assertFalse(GATE.compare_ppl(off, self.report((1.06, 0.98)))["passed"])
        for mutate in (lambda value: value["execution"].update(context_tokens=2048),
                       lambda value: value["overall"].update(scored_tokens=201),
                       lambda value: value["domains"][0].update(mean_nll=float("nan"))):
            changed = self.report()
            mutate(changed)
            with self.assertRaises(Q.ScreenError):
                GATE.compare_ppl(off, changed)

    def test_cli_propagates_failed_and_invalid_gates(self):
        for verdict, code in (("pass", 0), ("fail", 1), ("invalid", 2)):
            with patch.object(GATE, "run_gate", return_value={"verdict": verdict}), patch("sys.stdout", new=io.StringIO()):
                self.assertEqual(GATE.main(["t1", "--lane", "rtx4090", "--plan", "plan", "--out", "out",
                                            "--baseline", "base"]), code)

    def test_real_ppl_runner_uses_frozen_inputs_exact_four_runs_and_restores_power(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            corpus = root / "corpus"
            corpus.mkdir()
            streams = []
            provenance = []
            for index in range(2):
                path = corpus / f"{index}.txt"
                path.write_text("frozen held-out text")
                streams.append({"id": str(index), "domain": str(index), "path": path.name})
                provenance.append({"id": str(index), "selected_sha256": H.sha256_file(path)})
            manifest = corpus / "manifest.json"
            prov = corpus / "provenance.json"
            H.save(manifest, {"corpus_id": "frozen", "streams": streams})
            H.save(prov, {"streams": provenance})
            model, server = root / "model", root / "server"
            model.write_bytes(b"model")
            server.write_bytes(b"server")
            binaries = {}
            for policy in ("on", "off"):
                binary = root / f"{policy}.exe"
                binary.write_bytes(policy.encode())
                binaries[policy] = {"binary": str(binary), "binary_sha256": H.sha256_file(binary)}
            plan = root / "ppl.json"
            H.save(plan, {"model_path": str(model), "model_sha256": H.sha256_file(model),
                          "gpu_uuid": "GPU-test", "power_limit_w": 350, "candidate_server_binary": str(server),
                          "corpus_manifest": str(manifest), "corpus_manifest_sha256": H.sha256_file(manifest),
                          "corpus_provenance_sha256": H.sha256_file(prov), "arms": binaries})
            current = [370]
            def selected_gpu(*unused):
                return {"uuid": "GPU-test", "driver": "driver", "power_limit_w": current[0]}
            def power(uuid, watts):
                current[0] = watts
            def execute(argv, **kwargs):
                context = int(argv[argv.index("--context") + 1])
                output = Path(argv[argv.index("--output") + 1])
                output.mkdir()
                report = self.report(context=context)
                report["corpus"] = {"id": "frozen", "source": str(manifest), "stream_count": 2}
                report["artifact"] = {"path": str(model)}
                report["streams"] = [{"id": "0"}, {"id": "1"}]
                H.save(output / "report.json", report)
                self.assertEqual(kwargs["env"]["CUDA_VISIBLE_DEVICES"], "GPU-test")
                self.assertEqual(argv[argv.index("--stride") + 1], str(context // 2))
                self.assertEqual(argv[argv.index("--kv-dtype") + 1], "int8")
                return types.SimpleNamespace(returncode=0)
            sampler = MagicMock()
            sampler.summary.return_value = {"samples": 2}
            with patch.object(H, "gpu", side_effect=selected_gpu), patch.object(H, "set_power", side_effect=power) as limits, \
                 patch.object(H, "Sampler", return_value=sampler), \
                 patch.object(H, "command", return_value=types.SimpleNamespace(stdout=VERSION)), \
                 patch.object(GATE.subprocess, "run", side_effect=execute) as runs:
                result = GATE.run_ppl(plan, root / "out")
                self.assertEqual(result["verdict"], "pass")
                self.assertEqual(runs.call_count, 4)
                self.assertEqual([row["context"] for row in result["identity"]["runs"]], [1024, 1024, 2048, 2048])
                self.assertEqual([row["policy"] for row in result["identity"]["runs"]], ["off", "on", "on", "off"])
                self.assertEqual(current[0], 370)
                self.assertEqual([call.args[1] for call in limits.call_args_list], [350, 370])
                identity = {"model_sha256": H.sha256_file(model), "binary_sha256": H.sha256_file(server),
                            "binary_version": VERSION, "gpu": {"uuid": "GPU-test", "driver": "driver", "power_limit_w": 350}}
                self.assertEqual(GATE.verify_ppl(root / "out/result.json", identity), result)
                with patch.object(GATE.subprocess, "run", side_effect=subprocess.CalledProcessError(1, ["ppl"])):
                    with self.assertRaises(subprocess.CalledProcessError):
                        GATE.run_ppl(plan, root / "failed")
                self.assertEqual(current[0], 370)
                (corpus / "0.txt").write_text("edited")
                with self.assertRaises(Q.ScreenError):
                    GATE.verify_ppl(root / "out/result.json", identity)


if __name__ == "__main__":
    unittest.main()
