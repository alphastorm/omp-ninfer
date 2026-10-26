"""The paired quality screen must decide every gate metric by its pre-registered rule and refuse invalid screens."""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("quality_screen", ROOT / "scripts" / "quality_screen.py")
assert SPEC is not None and SPEC.loader is not None
SCREEN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCREEN)

GATE = SCREEN.PREREGISTRATION["gate_variants_per_case"]
REDACTION = SCREEN.PREREGISTRATION["redaction_variants_per_control"]
SUBSET = SCREEN.PREREGISTRATION["determinism_prompts"]
CASES = ("log-001", "log-002", "log-003", "log-004", "log-005", "log-006",
         "repo-001", "repo-002", "repo-003", "repo-004", "struct-002", "worklog-001")
CONTROLS = ("log-023", "repo-029")
FAST = {"resamples": 2000}

Sample = dict[str, Any]


def production_sample(case: str, index: int) -> Sample:
    control = case in CONTROLS
    leaks = {"log-023": index % 4, "repo-029": index % 2}.get(case, 0)
    return {
        "error": False, "output": f"{case}:{index % 5}", "class": case.split("-")[0], "control": control,
        "facts_found": 3 if case == "log-001" and index % 2 else 4, "facts_total": 4,
        "citations_supported": 2 if case == "repo-001" and index % 4 == 0 else 3, "citations_total": 3,
        "unsupported": int(case == "repo-002" and index % 2 == 0), "schema_valid": 1,
        "tool_evaluable": int(case == "struct-002"), "tool_selection_ok": int(case == "struct-002"),
        "tool_argument_evaluable": int(case == "struct-002"), "tool_argument_ok": int(case == "struct-002"),
        "items_duplicate": 0, "items_total": 5 if case == "worklog-001" else 0,
        "critical": int(case == "log-002" and index % 4 == 0), "forbidden": 0, "output_tokens": 900,
        "leaks": leaks, "passed": int(leaks == 0), "count": 1,
    }


def arm(change: Callable[[str, int, Sample], None] = lambda case, index, sample: None) -> dict[str, Sample]:
    samples = {}
    for case in CASES + CONTROLS:
        for index in range(REDACTION if case in CONTROLS else GATE):
            sample = production_sample(case, index)
            change(case, index, sample)
            samples[f"{case}.v{index}"] = sample
    for index in range(GATE):  # a vacuous case errors in every sample and is never counted
        samples[f"struct-007.v{index}"] = {**production_sample("struct-007", index), "error": True}
    return samples


def rerun(samples: dict[str, Sample], changed: str | None = None) -> dict[str, Sample]:
    order = SCREEN.screen_order(CASES + CONTROLS, set(CONTROLS))
    subset = {sample_id: dict(samples[sample_id]) for sample_id in order[:SUBSET]}
    if changed:
        subset[changed]["output"] = "a different output"
    return subset


def decide(candidate: dict[str, Sample], candidate_rerun: dict[str, Sample] | None = None) -> dict[str, Any]:
    production = arm()
    return SCREEN.decide(production, candidate, rerun(production), candidate_rerun or rerun(candidate), **FAST)


def outside(result: dict[str, Any]) -> list[str]:
    return sorted(name for name, entry in result["primary"].items() if not entry["inside_margin"])


class DecisionTest(unittest.TestCase):
    def test_a_candidate_that_only_reorders_outcomes_within_cases_passes(self) -> None:
        def swap(case: str, index: int, sample: Sample) -> None:
            if case == "log-001":
                sample["facts_found"] = 4 if index % 2 else 3
            if case == "repo-002" and index < 2:
                sample["unsupported"] = index
        result = decide(arm(swap))
        self.assertTrue(result["validity"]["valid"])
        self.assertEqual(result["pairs"], {"gate": 14 * GATE, "redaction": 2 * REDACTION})
        self.assertEqual(result["primary"]["required_fact_recall"]["difference"], 0.0)
        self.assertLess(result["primary"]["required_fact_recall"]["difference_lower_95"], 0.0)
        self.assertEqual(outside(result), [])
        self.assertEqual(result["verdict"], "pass")

    def test_lost_citations_fail_evidence_precision_alone(self) -> None:
        def lose(case: str, index: int, sample: Sample) -> None:
            if case.startswith("repo-") and case not in CONTROLS and index % 2:
                sample["citations_supported"] = 2
        result = decide(arm(lose))
        self.assertLess(result["primary"]["evidence_precision"]["difference_lower_95"], -0.02)
        self.assertEqual(outside(result), ["evidence_precision"])
        self.assertEqual(result["verdict"], "fail")

    def test_more_unsupported_claims_fail_on_the_upper_bound(self) -> None:
        def claim(case: str, index: int, sample: Sample) -> None:
            if case.startswith("log-") and index in (2, 5):
                sample["unsupported"] = 1
        result = decide(arm(claim))
        entry = result["primary"]["unsupported_claim_rate"]
        self.assertGreater(entry["difference"], 0.0)
        self.assertGreater(entry["difference_upper_95"], 0.03)
        self.assertEqual(outside(result), ["unsupported_claim_rate"])

    def test_a_tool_selection_lost_once_fails_the_tool_margin(self) -> None:
        def miss(case: str, index: int, sample: Sample) -> None:
            if case == "struct-002" and index == 3:
                sample["tool_selection_ok"] = 0
        result = decide(arm(miss))
        self.assertEqual(result["primary"]["tool_selection_accuracy"]["candidate"], 0.875)
        self.assertEqual(outside(result), ["tool_selection_accuracy"])

    def test_more_leaks_fail_the_leak_ratio(self) -> None:
        def leak(case: str, index: int, sample: Sample) -> None:
            if case in CONTROLS and index % 3 == 1:
                sample["leaks"] += 1
                sample["passed"] = 0
        result = decide(arm(leak))
        self.assertGreater(result["primary"]["secret_leak_ratio"]["ratio_upper_95"], 1.10)
        self.assertIn("secret_leak_ratio", outside(result))
        self.assertEqual(result["verdict"], "fail")

    def test_a_changed_output_in_the_determinism_subset_invalidates_the_screen(self) -> None:
        last = SCREEN.screen_order(CASES + CONTROLS, set(CONTROLS))[SUBSET - 1]
        candidate = arm()
        result = decide(candidate, candidate_rerun=rerun(candidate, changed=last))
        self.assertFalse(result["validity"]["checks"]["deterministic"])
        self.assertEqual(result["validity"]["determinism_mismatches"]["candidate"], 1)
        self.assertEqual(result["verdict"], "invalid")
        self.assertNotIn("primary", result)

    def test_errors_beyond_one_percent_of_counted_prompts_invalidate_the_screen(self) -> None:
        # 240 counted prompts allow two errors; three are too many. The vacuous case's errors never count.
        def failing(*ids: str) -> Callable[[str, int, Sample], None]:
            def change(case: str, index: int, sample: Sample) -> None:
                sample["error"] = f"{case}.v{index}" in ids
            return change
        allowed = decide(arm(failing("log-003.v7", "repo-029.v70")))
        self.assertTrue(allowed["validity"]["valid"])
        self.assertEqual(allowed["pairs"], {"gate": 14 * GATE - 1, "redaction": 2 * REDACTION - 1})
        refused = decide(arm(failing("log-003.v7", "repo-029.v70", "worklog-001.v1")))
        self.assertFalse(refused["validity"]["checks"]["errors_within_bound"])
        self.assertEqual(refused["verdict"], "invalid")

    def test_a_missing_counted_sample_invalidates_the_screen(self) -> None:
        candidate = arm()
        del candidate["repo-029.v71"]
        result = decide(candidate)
        self.assertFalse(result["validity"]["checks"]["complete"])
        self.assertEqual(result["verdict"], "invalid")

    def test_variants_that_do_not_change_outputs_invalidate_the_screen(self) -> None:
        def constant(case: str, index: int, sample: Sample) -> None:
            sample["output"] = case
        result = decide(arm(constant))
        self.assertFalse(result["validity"]["checks"]["variants_perturb_outputs"])
        self.assertEqual(result["verdict"], "invalid")


class VariantsTest(unittest.TestCase):
    def write_cases(self, root: Path, rows: list[dict[str, Any]]) -> Path:
        cases = root / "cases"
        cases.mkdir()
        (cases / "set.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        return cases

    def test_cases_get_gate_or_redaction_variants_and_the_subset_is_the_screen_head(self) -> None:
        control = {"case_id": "log-023", "input": {"allowed_sources": ["a.log"], "task": "Summarize."},
                   "safety": {"contains_synthetic_secret": True}}
        vacuous = {"case_id": "struct-007", "input": {"context": "schema", "task": "Emit JSON."},
                   "safety": {"contains_synthetic_secret": True}}
        other = {"case_id": "log-001", "input": {"context": "x", "task": "Answer."}, "safety": {}}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            summary = SCREEN.write_variants(self.write_cases(root, [vacuous, control, other]),
                                            root / "screen.jsonl", root / "subset.jsonl")
            screen = [json.loads(line) for line in (root / "screen.jsonl").read_text().splitlines()]
            subset = [json.loads(line)["case_id"] for line in (root / "subset.jsonl").read_text().splitlines()]
        self.assertEqual(summary["controls"], ["log-023"])
        self.assertEqual(summary["counted_cases"], 2)
        ids = [row["case_id"] for row in screen]
        self.assertEqual(ids, [f"log-001.v{i}" for i in range(GATE)] + [f"log-023.v{i}" for i in range(REDACTION)])
        self.assertEqual(subset, ids[:SUBSET])
        self.assertEqual(screen[0]["input"], other["input"])
        tasks = [row["input"]["task"] for row in screen if row["case_id"].startswith("log-023.")]
        prefixes = [task[: -len("Summarize.")] for task in tasks]
        self.assertEqual(len(set(prefixes)), REDACTION)
        self.assertTrue(all(not prefix.strip() for prefix in prefixes))

    def test_a_counted_case_with_nothing_before_its_task_is_refused(self) -> None:
        bare = {"case_id": "log-002", "input": {"task": "Summarize."}, "safety": {}}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(SCREEN.ScreenError):
                SCREEN.write_variants(self.write_cases(root, [bare]), root / "screen.jsonl", root / "subset.jsonl")


class EndpointTest(unittest.TestCase):
    def test_managed_pair_propagates_powered_fail_and_invalid_verdicts(self) -> None:
        for verdict, expected in (("pass", 0), ("fail", 1), ("invalid", 2)):
            runner = types.SimpleNamespace(run_campaign=lambda *a, **kw: {"quality": {"verdict": verdict}})
            with patch.dict(sys.modules, {"variant_campaign": runner}), patch("sys.stdout", new=io.StringIO()):
                self.assertEqual(SCREEN.main(["pair", "--lane", "rtx4090", "--plan", "plan.json",
                                              "--out", "out"]), expected)

    def test_native_and_container_urls_do_not_encode_a_lane(self) -> None:
        for port in (18082, 18089):
            root = f"http://127.0.0.1:{port}"
            for suffix in ("", "/", "/v1", "/v1/"):
                self.assertEqual(SCREEN.endpoint_root(root + suffix), root)
        for bad in ("file:///tmp/key", "http://user:secret@example.com", "http://example.com/v1?key=x",
                    "http://example.com/chat/completions"):
            with self.assertRaises(SCREEN.ScreenError):
                SCREEN.endpoint_root(bad)

    def test_wrong_served_id_fails_before_any_corpus_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            key = root / "key"
            key.write_text("secret")
            with patch.object(SCREEN.urllib.request, "urlopen",
                              return_value=io.BytesIO(b'{"data":[{"id":"q38-ninfer"}]}')), \
                 patch.object(SCREEN.subprocess, "run") as runner:
                with self.assertRaisesRegex(SCREEN.ScreenError, "does not serve"):
                    SCREEN.capture_endpoint(qualification=root, cases=root, fixtures=root,
                                            base_url="http://127.0.0.1:18082/v1", model="qwen3.8-27b",
                                            api_key_file=key, out=root / "new", label="test")
                runner.assert_not_called()

    def test_capture_preserves_powered_settings_and_keeps_key_off_argv(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "scripts").mkdir()
            for name in ("run_qualification.py", "score_qualification.py"):
                (root / "scripts" / name).touch()
            key = root / "key"
            key.write_text("secret")
            with patch.object(SCREEN.urllib.request, "urlopen",
                              return_value=io.BytesIO(b'{"data":[{"id":"q38-ninfer"}]}')), \
                 patch.object(SCREEN.subprocess, "run") as runner, \
                 patch.object(SCREEN, "run_identity", return_value={"label": "test"}):
                SCREEN.capture_endpoint(qualification=root, cases=root, fixtures=root,
                                        base_url="http://127.0.0.1:18089", model="q38-ninfer",
                                        api_key_file=key, out=root / "new", label="test")
            argv = runner.call_args_list[0].args[0]
            self.assertEqual(argv[argv.index("--base-url") + 1], "http://127.0.0.1:18089/v1")
            self.assertEqual(argv[argv.index("--concurrency") + 1], "1")
            self.assertEqual(argv[argv.index("--reasoning-token-headroom") + 1], "8192")
            self.assertEqual(argv[argv.index("--reasoning-mode") + 1], "low")
            self.assertNotIn("secret", argv)
            self.assertEqual(runner.call_args_list[0].kwargs["env"]["LOCAL_5090_API_KEY"], "secret")

    def test_byte_comparison_uses_outputs_not_response_timing_or_tool_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline, candidate = root / "A", root / "B"
            baseline.mkdir()
            candidate.mkdir()
            row = {"case_id": "case", "content": "exact", "reasoning": "reason",
                   "tool_calls": [{"id": "transport-A", "function": {"name": "read", "arguments": "{}"}}]}
            (baseline / "responses.jsonl").write_text(json.dumps(row) + "\n")
            row["wall_ms"] = 999
            row["tool_calls"][0]["id"] = "transport-B"
            (candidate / "responses.jsonl").write_text(json.dumps(row) + "\n")
            self.assertTrue(SCREEN.compare_responses(baseline, candidate)["all_identical"])
            row["content"] += " "
            (candidate / "responses.jsonl").write_text(json.dumps(row) + "\n")
            self.assertEqual(SCREEN.compare_responses(baseline, candidate)["different_or_missing"], 1)


class ShardsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cases = self.root / "cases"
        self.cases.mkdir()
        rows = [{"case_id": case, "class": "test",
                 "input": {"context": "evidence", "task": "Answer."},
                 "safety": {"contains_synthetic_secret": case in CONTROLS}}
                for case in (*CASES, *CONTROLS)]
        (self.cases / "set.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
        self.plan = self.root / "plan.json"
        self.plan.write_text(json.dumps({"cases": str(self.cases)}))
        sys.path.insert(0, str(ROOT / "scripts/hosts"))
        import variant_campaign
        self.runner = variant_campaign
        self.identity = {"binary_sha256": "binary", "binary_version": "source",
                         "model_sha256": "model", "config_sha256": "config", "image": None,
                         "seccomp_profile_sha256": None,
                         "gpu": {"uuid": "GPU-selected", "driver": "driver", "power_limit_w": 450}}
        self.fingerprint = {"arms": {"A": self.identity, "B": self.identity}, "inputs": "frozen"}
        self.patches = [
            patch.object(self.runner, "validate_plan"),
            patch.object(SCREEN, "pair_fingerprint", return_value=self.fingerprint),
            patch.object(self.runner, "capture_arm", side_effect=self.capture),
        ]
        self.mocks = [item.start() for item in self.patches]
        for item in self.patches:
            self.addCleanup(item.stop)
        self.out = self.root / "out"

    def capture(self, lane, plan, model_sha, key, index, directory, mode, **kwargs):
        directory.mkdir()
        run = directory / "quality"
        run.mkdir()
        ids = [json.loads(line)["case_id"] for line in kwargs["quality_cases"].read_text().splitlines()]
        self.runner.save(run / "manifest.json", {"label": "test"})
        scores, responses = [], []
        for sample_id in ids:
            case, variant = sample_id.rsplit(".v", 1)
            sample = production_sample(case, int(variant))
            responses.append({"case_id": sample_id, "content": sample["output"], "reasoning": "", "error": None})
            scores.append({"case_id": sample_id, "class": "test", "is_redaction_control": sample["control"],
                           "required_facts_found": sample["facts_found"], "required_facts_total": sample["facts_total"],
                           "schema_valid": True, "tool_evaluable": True, "tool_selection_ok": True,
                           "tool_argument_ok": True, "output_tokens": 100, "secret_leaks": sample["leaks"]})
        (run / "responses.jsonl").write_text("".join(json.dumps(row) + "\n" for row in responses))
        self.runner.save(run / "scores.json", {"per_case": scores})
        receipt = {"status": "passed", "identity": self.identity, "wall_seconds": len(ids) * 2}
        self.runner.save(directory / "receipt.json", receipt)
        return receipt

    def pair(self, **kwargs):
        return SCREEN.sharded_pair("rtx4090", self.plan, self.out, shard_size=50, **kwargs)

    def test_plan_is_deterministic_complete_and_preserves_prompt_and_subset_order(self):
        layout, files = SCREEN.shard_plan(self.cases, 50)
        again = SCREEN.shard_plan(self.cases, 50)
        self.assertEqual((layout, files), again)
        expected = SCREEN.screen_order(CASES + CONTROLS, set(CONTROLS))
        for role in ("production", "candidate", "production_determinism", "candidate_determinism"):
            jobs = [job for job in layout["jobs"] if job["role"] == role]
            ids = [sample for job in jobs for sample in job["prompt_ids"]]
            self.assertEqual(ids, expected[:80] if "determinism" in role else expected)
            self.assertTrue(all(len(job["prompt_ids"]) <= 50 for job in jobs))
        for invalid in (0, -1):
            with self.assertRaises(SCREEN.ScreenError):
                SCREEN.shard_plan(self.cases, invalid)

    def test_resume_skips_verified_shards_and_never_decides_a_partial_set(self):
        first = self.pair(max_shards=1)
        self.assertNotIn("quality", first)
        self.assertFalse((self.out / "result.json").exists())
        self.assertEqual(first["completed_shards"], 1)
        with self.assertRaisesRegex(SCREEN.ScreenError, "requires --resume"):
            self.pair(max_shards=1)
        self.mocks[-1].reset_mock()
        second = self.pair(max_shards=1, resume=True)
        self.assertEqual(second["completed_shards"], 2)
        self.mocks[-1].assert_called_once()
        self.assertNotIn("quality", second)

    def test_complete_self_pair_scores_all_shards_and_compares_retained_bytes(self):
        original = SCREEN.decide
        with patch.object(SCREEN, "decide", side_effect=lambda *args: original(*args, resamples=100)):
            result = self.pair()
        self.assertEqual(result["completed_shards"], result["total_shards"])
        self.assertEqual(result["quality"]["verdict"], "pass")
        self.assertEqual(result["quality"]["counted_prompts"], 240)
        self.assertEqual(result["byte_comparison"]["identical"], 240)
        self.assertTrue(all(row["all_identical"] for row in result["determinism_byte_comparison"].values()))
        self.assertTrue(all(row["wall_seconds_per_100_prompts"] == 200 for row in result["timing"]))

    def test_changed_inputs_runtime_prompt_and_sealed_capture_are_refused_before_launch(self):
        self.pair(max_shards=1)
        self.mocks[-1].reset_mock()
        with patch.object(SCREEN, "pair_fingerprint", return_value={**self.fingerprint, "inputs": "changed"}):
            with self.assertRaisesRegex(SCREEN.ScreenError, "identity changed"):
                self.pair(max_shards=1, resume=True)
        prompt = self.out / "prompts/screen-0000.jsonl"
        original = prompt.read_bytes()
        prompt.write_bytes(original + b"\n")
        with self.assertRaisesRegex(SCREEN.ScreenError, "prompt file changed"):
            self.pair(max_shards=1, resume=True)
        prompt.write_bytes(original)
        run = next(self.out.glob("0-production-*/attempt-*/quality"))
        (run / "manifest.json").write_text('{"label":"changed"}')
        with self.assertRaisesRegex(SCREEN.ScreenError, "hash changed"):
            self.pair(max_shards=1, resume=True)
        self.mocks[-1].assert_not_called()

    def test_changed_measured_runtime_and_response_bytes_cannot_be_skipped(self):
        self.pair(max_shards=1)
        self.mocks[-1].reset_mock()
        capture = next(self.out.glob("0-production-*/attempt-*"))
        path = capture / "receipt.json"
        receipt = self.runner.load(path)
        for field in ("binary_sha256", "config_sha256", "model_sha256"):
            changed = json.loads(json.dumps(receipt))
            changed["identity"][field] = "different"
            self.runner.save(path, changed)
            with self.assertRaisesRegex(SCREEN.ScreenError, "runtime identity"):
                self.pair(max_shards=1, resume=True)
        self.runner.save(path, receipt)
        responses = capture / "quality/responses.jsonl"
        responses.write_text(responses.read_text().replace("log-001:0", "changed:0"))
        with self.assertRaisesRegex(SCREEN.ScreenError, "hash changed"):
            self.pair(max_shards=1, resume=True)
        self.mocks[-1].assert_not_called()

    def test_actual_tool_output_difference_invalidates_fresh_determinism(self):
        original_capture = self.capture
        def changed(*args, **kwargs):
            receipt = original_capture(*args, **kwargs)
            if args[4] == 2:
                path = args[5] / "quality/responses.jsonl"
                rows = [json.loads(line) for line in path.read_text().splitlines()]
                rows[0]["tool_calls"] = [{"function": {"name": "changed", "arguments": "{}"}}]
                path.write_text("".join(json.dumps(row) + "\n" for row in rows))
            return receipt
        self.mocks[-1].side_effect = changed
        original = SCREEN.decide
        with patch.object(SCREEN, "decide", side_effect=lambda *args: original(*args, resamples=100)):
            result = self.pair()
        self.assertEqual(result["quality"]["verdict"], "invalid")
        self.assertFalse(result["quality"]["validity"]["checks"]["deterministic_bytes"])
        self.assertNotIn("primary", result["quality"])

    def test_fingerprint_binds_source_config_corpus_fixture_and_qualification_bytes(self):
        model = self.root / "model"
        binary = self.root / "binary"
        fixtures = self.root / "fixtures"
        qualification = self.root / "qualification"
        config = self.root / "config.json"
        model.write_bytes(b"model")
        binary.write_bytes(b"binary")
        fixtures.mkdir()
        qualification.mkdir()
        (fixtures / "source.txt").write_text("evidence")
        (qualification / "executor.py").write_text("executor")
        self.runner.save(config, {"engine": {"kv_dtype": "int8"}})
        plan = {"cases": str(self.cases), "fixtures": str(fixtures), "qualification": str(qualification),
                "model_path": str(model), "gpu_uuid": "GPU-selected", "config_path": str(config),
                "arms": {label: {"binary": str(binary)} for label in ("A", "B")}}
        self.runner.save(self.plan, plan)
        fingerprint = self.patches[1]
        fingerprint.stop()
        # Use the real native hash/version path while keeping this test host-free.
        with patch.object(self.runner, "gpu", return_value=self.identity["gpu"]), \
             patch.object(self.runner, "command", return_value=types.SimpleNamespace(stdout="source")):
            baseline = SCREEN.pair_fingerprint(self.runner, "rtx4090", self.plan, plan)
            for path in (model, binary, config, self.cases / "set.jsonl",
                         fixtures / "source.txt", qualification / "executor.py", self.plan):
                before = path.read_bytes()
                if path == config:
                    self.runner.save(path, {"engine": {"kv_dtype": "bf16"}})
                else:
                    path.write_bytes(before + b"\n")
                self.assertNotEqual(SCREEN.pair_fingerprint(self.runner, "rtx4090", self.plan, plan), baseline)
                path.write_bytes(before)
        fingerprint.start()

    def test_duplicate_missing_or_reordered_capture_ids_cannot_be_sealed(self):
        layout, _ = SCREEN.shard_plan(self.cases, 50)
        job = layout["jobs"][0]
        self.pair(max_shards=1)
        capture = next(self.out.glob("0-production-*/attempt-*"))
        path = capture / "quality/responses.jsonl"
        rows = path.read_text().splitlines()
        for bad in (rows[:-1], [rows[1], rows[0], *rows[2:]], [rows[0], *rows[:-1]]):
            path.write_text("\n".join(bad) + "\n")
            with self.assertRaisesRegex(SCREEN.ScreenError, "order/completeness"):
                SCREEN.verified_capture(self.runner, capture, job, self.identity)

    def test_interrupted_attempt_is_retained_but_failed_finished_capture_is_not_retried(self):
        self.pair(max_shards=1)
        directory = self.out / "0-production-0001"
        partial = directory / "attempt-0000"
        partial.mkdir(parents=True)
        (partial / "stderr.log").write_text("interrupted")
        self.pair(max_shards=1, resume=True)
        self.assertTrue((directory / "attempt-0001/receipt.json").exists())
        self.assertEqual((partial / "stderr.log").read_text(), "interrupted")
        failed = self.out / "0-production-0002/attempt-0000"
        failed.mkdir(parents=True)
        self.runner.save(failed / "receipt.json", {"status": "failed"})
        self.mocks[-1].reset_mock()
        with self.assertRaisesRegex(SCREEN.ScreenError, "unsealed finished/failed"):
            self.pair(max_shards=1, resume=True)
        self.mocks[-1].assert_not_called()


if __name__ == "__main__":
    unittest.main()
