"""Content-safe native speed-gate fixtures; no runtime or hardware is started."""
from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import speed_gate as SPEED

ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def fixture():
    configs = {"A": {"speculative": {"backend": "mtp", "draft_tokens": 3}},
               "B": {"speculative": {"backend": "dflash2", "draft_tokens": 7}}}
    suite = [{"id": "log-024@0", "request_sha256": "1" * 64},
             {"id": "role-002@0", "request_sha256": "2" * 64}]
    gate = {"artifact_type": "omp_ninfer_speed_gate", "schema_version": 1, "release": "v0.99.0",
            "decision": {
                "artifact_type": "omp_ninfer_founder_gate_decision", "schema_version": 1,
                "release": "v0.99.0",
                "rule": {"weighted_decode_ratio_minimum": 1.08, "every_case_ratio_minimum": 0.95,
                         "byte_identical_normalized_outputs": "required for every case (A0/A3, B1/B2, A0/B1)",
                         "applies_to": ["role weighted", "all-cases weighted", "every case"]}},
            "comparator": {"binary_sha256": "a" * 64, "configuration_sha256": digest(configs["A"])},
            "request_suite": suite, "request_suite_sha256": digest(suite),
            "role_case_ids": [row["id"] for row in suite]}
    captures = []
    for index, label in enumerate(("A", "B", "B", "A")):
        captures.append({"arm": label, "index": index, "status": "passed",
                         "identity": {"binary_sha256": ("a" if label == "A" else "b") * 64,
                                      "config": deepcopy(configs[label])},
                         "requests": [{**row, "completion_tokens": 1024, "decode_seconds": 1024 / rate,
                                       "normalized_output": json.dumps({"content": row["id"], "reasoning": "",
                                                                        "tool_calls": []}, sort_keys=True)}
                                      for row, rate in zip(suite, (100, 100) if label == "A" else (110, 120))]})
    return gate, captures


def plan_for(gate, captures):
    candidate = next(arm["identity"] for arm in captures if arm["arm"] == "B")
    return SPEED.prescreen(gate, {"binary_sha256": candidate["binary_sha256"],
                                  "configuration_sha256": digest(candidate["config"])})


class SpeedGateTests(unittest.TestCase):
    def test_recorded_native_no_regression_rule_replaces_the_speedup_floor(self):
        gate, captures = fixture()
        gate["decision"] = json.loads(
            (ROOT / "releases/v0.16.2/qualification/native-speed-decision.json").read_text())
        gate["release"] = gate["decision"]["release"]
        for arm in captures:
            for row in arm["requests"]:
                row.update(completion_tokens=100, decode_seconds=1)
        result = SPEED.reduce(gate, captures, plan_for(gate, captures))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["thresholds"], {"weighted_minimum": 0.98, "every_case_minimum": 0.95})
        self.assertEqual(result["decision_sha256"], digest(gate["decision"]))

    def test_recorded_no_regression_weighted_and_case_floors_are_inclusive(self):
        for candidate_tokens, expected in (((98, 98), "PASS"), ((97, 97), "FAIL"),
                                           ((95, 101), "PASS"), ((94, 110), "FAIL")):
            with self.subTest(candidate_tokens=candidate_tokens):
                gate, captures = fixture()
                gate["decision"]["rule"]["weighted_decode_ratio_minimum"] = 0.98
                for arm in captures:
                    for row, tokens in zip(arm["requests"], (100, 100) if arm["arm"] == "A" else candidate_tokens):
                        row.update(completion_tokens=tokens, decode_seconds=1)
                self.assertEqual(SPEED.reduce(gate, captures, plan_for(gate, captures))["status"], expected)

    def test_normalized_outputs_must_match_within_and_across_abba_arms(self):
        for indices in ((0,), (1,), (2,), (3,), (0, 3), (1, 2)):
            with self.subTest(indices=indices):
                gate, captures = fixture()
                for index in indices:
                    captures[index]["requests"][0]["normalized_output"] += " "
                result = SPEED.reduce(gate, captures, plan_for(gate, captures))
                self.assertTrue(result["thresholds_passed"])
                self.assertEqual(result["status"], "FAIL")
                self.assertFalse(result["normalized_outputs_identical"])
                self.assertFalse(result["gate_passed"])
                self.assertEqual(result["output_mismatch_case_ids"], ["log-024@0"])

    def test_missing_normalized_bytes_cannot_be_replaced_by_a_hash_or_pass_flag(self):
        gate, captures = fixture()
        captures[0]["requests"][0].pop("normalized_output")
        captures[0]["requests"][0].update(output_sha256="f" * 64, normalized_output_hashes_match=True)
        with self.assertRaisesRegex(SPEED.SpeedGateError, "normalized_output"):
            SPEED.reduce(gate, captures, plan_for(gate, captures))

    def test_rule_and_release_are_bound_to_the_recorded_plan(self):
        gate, captures = fixture()
        plan = plan_for(gate, captures)
        gate["decision"]["rule"]["weighted_decode_ratio_minimum"] = 0.98
        result = SPEED.reduce(gate, captures, plan)
        self.assertEqual(result["status"], "DIAGNOSTIC")
        self.assertIn("plan.gate_sha256", " ".join(result["diagnostic_reasons"]))
        self.assertFalse(result["gate_passed"])

    def test_missing_foreign_or_invalid_recorded_decisions_are_rejected(self):
        gate, _ = fixture()
        for decision in (None, {}, {**gate["decision"], "release": "v0.98.0"},
                         {**gate["decision"], "rule": {}},
                         {**gate["decision"], "rule": {**gate["decision"]["rule"],
                                                       "weighted_decode_ratio_minimum": True}},
                         {**gate["decision"], "rule": {**gate["decision"]["rule"],
                                                       "byte_identical_normalized_outputs": False}}):
            with self.subTest(decision=decision):
                with self.assertRaises(SPEED.SpeedGateError):
                    SPEED.declaration({**gate, "decision": decision})

    def test_changed_role_partition_from_prescreen_is_diagnostic(self):
        gate, captures = fixture()
        gate["role_case_ids"] = ["log-024@0"]
        plan = plan_for(gate, captures)
        for arm in captures:
            for row, tokens in zip(arm["requests"], (100, 100) if arm["arm"] == "A" else (107, 1000)):
                row.update(completion_tokens=tokens, decode_seconds=1)
        unchanged = SPEED.reduce(gate, captures, plan)
        self.assertEqual(unchanged["status"], "FAIL")
        self.assertTrue(unchanged["gate_predictive"])
        gate["role_case_ids"] = ["role-002@0"]
        result = SPEED.reduce(gate, captures, plan)
        self.assertTrue(result["thresholds_passed"])
        self.assertEqual(result["status"], "DIAGNOSTIC")
        self.assertFalse(result["gate_predictive"])
        self.assertFalse(result["gate_passed"])
        reasons = " ".join(result["diagnostic_reasons"])
        self.assertIn("plan.gate_sha256", reasons)
        self.assertIn("plan.role_case_ids", reasons)
        self.assertEqual(result["plan_sha256"], digest(plan))
        self.assertNotEqual(result["gate_sha256"], plan["gate_sha256"])

    def test_each_plan_declaration_identity_mismatch_is_diagnostic(self):
        for field, value in (("gate_sha256", "f" * 64),
                             ("role_case_ids", ["log-024@0"]),
                             ("request_suite_sha256", "f" * 64),
                             ("request_suite", [{"id": "log-024@0", "request_sha256": "3" * 64}]),
                             ("order", ["B", "A", "A", "B"])):
            with self.subTest(field=field):
                gate, captures = fixture()
                plan = plan_for(gate, captures)
                plan[field] = value
                result = SPEED.reduce(gate, captures, plan)
                self.assertEqual(result["status"], "DIAGNOSTIC")
                self.assertFalse(result["gate_predictive"])
                self.assertFalse(result["gate_passed"])
                self.assertIn("plan." + field, " ".join(result["diagnostic_reasons"]))

    def test_plan_arm_identity_drift_is_diagnostic(self):
        for arm in ("A", "B"):
            for field in ("binary_sha256", "configuration_sha256"):
                with self.subTest(arm=arm, field=field):
                    gate, captures = fixture()
                    plan = plan_for(gate, captures)
                    plan["arms"][arm][field] = "f" * 64
                    result = SPEED.reduce(gate, captures, plan)
                    self.assertFalse(result["gate_predictive"])
                    self.assertIn("plan", " ".join(result["diagnostic_reasons"]))

    def test_reduction_requires_the_recorded_prescreen_plan(self):
        gate, captures = fixture()
        with self.assertRaises(TypeError):
            SPEED.reduce(gate, captures)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as rejected:
            SPEED.main(["reduce", "--gate", "gate.json", "--capture", "A0.json", "--out", "result.json"])
        self.assertEqual(rejected.exception.code, 2)

    def test_candidate_binary_mtp_prescreen_is_diagnostic_not_gate_predictive(self):
        # P16's shape: MTP3 uses the candidate binary, not the shipped incumbent.
        # The isolated case clears 0.95 at ~130.55 / 135.55, unlike the final
        # incumbent comparison (~130.19 / 139.41). Other cases lift the aggregate.
        gate, captures = fixture()
        for arm in captures:
            arm["identity"]["binary_sha256"] = "b" * 64
            rates = (135.55, 100) if arm["arm"] == "A" else (130.55, 200)
            for row, rate in zip(arm["requests"], rates):
                row["decode_seconds"] = row["completion_tokens"] / rate
        result = SPEED.reduce(gate, captures, plan_for(gate, captures))
        self.assertGreater(result["all_cases"]["weighted_decode_ratio"], 1.08)
        self.assertGreater(result["all_cases"]["minimum_case_ratio"], 0.95)
        self.assertEqual(result["status"], "DIAGNOSTIC")
        self.assertFalse(result["gate_predictive"])
        self.assertIn("binary_sha256", " ".join(result["diagnostic_reasons"]))

    def test_final_gate_shape_passes_and_receipts_bind_each_arm(self):
        gate, captures = fixture()
        result = SPEED.reduce(gate, captures, plan_for(gate, captures))
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["gate_predictive"])
        self.assertTrue(result["gate_passed"])
        self.assertEqual(result["diagnostic_reasons"], [])
        for source, receipt in zip(captures, result["arms"]):
            self.assertEqual(receipt["identity"]["binary_sha256"], source["identity"]["binary_sha256"])
            self.assertEqual(receipt["identity"]["configuration_sha256"], digest(source["identity"]["config"]))
            self.assertEqual(receipt["request_suite_sha256"], gate["request_suite_sha256"])
            self.assertEqual(receipt["capture_sha256s"], [digest(source)])

    def test_real_4090_final_floor_remains_a_predictive_failure_without_waiver(self):
        gate, captures = fixture()
        for arm in captures:
            for row, rate in zip(arm["requests"], (139.4120056820121, 100) if arm["arm"] == "A"
                                 else (130.18738833254372, 200)):
                row["decode_seconds"] = row["completion_tokens"] / rate
        result = SPEED.reduce(gate, captures, plan_for(gate, captures))
        self.assertTrue(result["gate_predictive"])
        self.assertFalse(result["gate_passed"])
        self.assertEqual(result["status"], "FAIL")
        self.assertAlmostEqual(result["all_cases"]["minimum_case_ratio"], 0.9338319730475076)
        self.assertEqual(result["all_cases"]["below_case_floor"], ["log-024@0"])

    def test_changed_requests_on_either_or_both_arms_are_diagnostic(self):
        for labels in ({"A"}, {"B"}, {"A", "B"}):
            with self.subTest(labels=labels):
                gate, captures = fixture()
                for arm in captures:
                    if arm["arm"] in labels:
                        arm["requests"][0]["request_sha256"] = "3" * 64
                result = SPEED.reduce(gate, captures, plan_for(gate, captures))
                self.assertEqual(result["status"], "DIAGNOSTIC")
                self.assertFalse(result["gate_predictive"])
                self.assertFalse(result["gate_passed"])
                self.assertIn("request_suite_sha256", " ".join(result["diagnostic_reasons"]))

    def test_partial_suite_is_never_a_gate_pass(self):
        gate, captures = fixture()
        for arm in captures:
            arm["requests"].pop()
        result = SPEED.reduce(gate, captures, plan_for(gate, captures))
        self.assertFalse(result["gate_predictive"])
        self.assertEqual(result["status"], "DIAGNOSTIC")

    def test_comparator_configuration_and_candidate_repeat_drift_are_diagnostic(self):
        for index, field, value in ((0, "config", {"speculative": {"backend": "mtp", "draft_tokens": 7}}),
                                    (2, "binary_sha256", "c" * 64)):
            with self.subTest(index=index, field=field):
                gate, captures = fixture()
                captures[index]["identity"][field] = value
                result = SPEED.reduce(gate, captures, plan_for(gate, captures))
                self.assertFalse(result["gate_predictive"])
                self.assertIn("configuration_sha256" if field == "config" else field,
                              " ".join(result["diagnostic_reasons"]))

    def test_recorded_speedup_thresholds_are_inclusive(self):
        for candidate_tokens, expected in ((108, "PASS"), (107, "FAIL")):
            with self.subTest(weighted=candidate_tokens):
                gate, captures = fixture()
                for arm in captures:
                    for row in arm["requests"]:
                        row.update(completion_tokens=100 if arm["arm"] == "A" else candidate_tokens, decode_seconds=1)
                result = SPEED.reduce(gate, captures, plan_for(gate, captures))
                self.assertEqual(result["thresholds"], {"weighted_minimum": 1.08, "every_case_minimum": 0.95})
                self.assertEqual(result["status"], expected)
        for floor_tokens, expected in ((95, "PASS"), (94, "FAIL")):
            with self.subTest(floor=floor_tokens):
                gate, captures = fixture()
                for arm in captures:
                    for row, tokens in zip(arm["requests"], (100, 100) if arm["arm"] == "A" else (floor_tokens, 140)):
                        row.update(completion_tokens=tokens, decode_seconds=1)
                self.assertEqual(SPEED.reduce(gate, captures, plan_for(gate, captures))["status"], expected)

    def test_weighting_is_pooled_tokens_over_seconds_and_case_floor_uses_medians(self):
        gate, captures = fixture()
        result = SPEED.reduce(gate, captures, plan_for(gate, captures))
        self.assertAlmostEqual(result["all_cases"]["weighted_decode_ratio"], 2 / (1 / 110 + 1 / 120) / 100)
        captures[1]["requests"][0]["decode_seconds"] = 1024 / 90
        captures[2]["requests"][0]["decode_seconds"] = 1024 / 110
        result = SPEED.reduce(gate, captures, plan_for(gate, captures))
        self.assertAlmostEqual(result["all_cases"]["cases"][0]["ratio"], 1.0)

    def test_role_and_combined_weighted_bars_both_remain_binding(self):
        gate, captures = fixture()
        gate["role_case_ids"] = ["log-024@0"]
        for arm in captures:
            for row, tokens in zip(arm["requests"], (100, 100) if arm["arm"] == "A" else (107, 1000)):
                row.update(completion_tokens=tokens, decode_seconds=1)
        result = SPEED.reduce(gate, captures, plan_for(gate, captures))
        self.assertGreater(result["all_cases"]["weighted_decode_ratio"], 1.08)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["role_suite"]["case_count"], 1)
        self.assertEqual(result["supplemental"]["case_count"], 1)

    def test_depth_and_supplemental_shards_combine_without_double_counting(self):
        gate, captures = fixture()
        shards = []
        for capture in captures:
            for row in capture["requests"]:
                shard = deepcopy(capture)
                shard["requests"] = [row]
                shards.append(shard)
        result = SPEED.reduce(gate, shards, plan_for(gate, shards))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["all_cases"], SPEED.reduce(gate, captures, plan_for(gate, captures))["all_cases"])
        self.assertTrue(all(len(arm["capture_sha256s"]) == 2 for arm in result["arms"]))
        with self.assertRaisesRegex(SPEED.SpeedGateError, "duplicate"):
            SPEED.reduce(gate, shards + [shards[0]], plan_for(gate, shards + [shards[0]]))

    def test_public_receipt_projects_identities_without_copying_private_capture_fields(self):
        gate, captures = fixture()
        for arm in captures:
            arm["internal_notes"] = "must-not-export"
            arm["identity"]["private_metadata"] = "must-not-export"
            for row in arm["requests"]:
                row["output_text"] = "must-not-export"
                row["normalized_output"] = "must-not-export"
        result = SPEED.reduce(gate, captures, plan_for(gate, captures))
        self.assertNotIn("must-not-export", json.dumps(result))
        self.assertNotIn("config", result["arms"][0]["identity"])
        self.assertEqual(set(result["arms"][0]["identity"]), {"binary_sha256", "configuration_sha256"})

    def test_invalid_or_incomplete_captures_cannot_produce_a_verdict(self):
        for field, value in (("completion_tokens", True), ("decode_seconds", 0), ("decode_seconds", float("nan"))):
            with self.subTest(field=field, value=value):
                gate, captures = fixture()
                captures[0]["requests"][0][field] = value
                with self.assertRaises(SPEED.SpeedGateError):
                    SPEED.reduce(gate, captures, plan_for(gate, captures))
        gate, captures = fixture()
        with self.assertRaisesRegex(SPEED.SpeedGateError, "four"):
            SPEED.reduce(gate, captures[:-1], plan_for(gate, captures[:-1]))
        captures[0]["status"] = "failed"
        with self.assertRaisesRegex(SPEED.SpeedGateError, "passed"):
            SPEED.reduce(gate, captures, plan_for(gate, captures))
        gate["request_suite_sha256"] = "f" * 64
        with self.assertRaisesRegex(SPEED.SpeedGateError, "bind"):
            SPEED.declaration(gate)

    def test_prescreen_has_no_free_comparator_and_uses_the_reducers_declaration(self):
        gate, captures = fixture()
        candidate = {"binary_sha256": captures[1]["identity"]["binary_sha256"],
                     "configuration_sha256": digest(captures[1]["identity"]["config"])}
        plan = SPEED.prescreen(gate, candidate)
        self.assertEqual(plan["arms"], {"A": gate["comparator"], "B": candidate})
        self.assertEqual(plan["request_suite_sha256"], gate["request_suite_sha256"])
        self.assertEqual(plan["gate_sha256"], SPEED.reduce(gate, captures, plan_for(gate, captures))["gate_sha256"])
        self.assertEqual(plan["order"], ["A", "B", "B", "A"])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as rejected:
            SPEED.main(["prescreen", "--gate", "gate.json", "--candidate", "candidate.json",
                        "--out", "plan.json", "--comparator", "override.json"])
        self.assertEqual(rejected.exception.code, 2)

    def test_file_only_cli_round_trip_and_diagnostic_exit_status(self):
        gate, captures = fixture()
        candidate = {"binary_sha256": "b" * 64, "configuration_sha256": digest(captures[1]["identity"]["config"])}
        with tempfile.TemporaryDirectory() as temporary, redirect_stdout(io.StringIO()):
            root = Path(temporary)
            for name, value in (("gate", gate), ("candidate", candidate), *[(str(i), arm) for i, arm in enumerate(captures)]):
                (root / f"{name}.json").write_text(json.dumps(value), encoding="utf-8")
            self.assertEqual(SPEED.main(["prescreen", "--gate", str(root / "gate.json"), "--candidate",
                                        str(root / "candidate.json"), "--out", str(root / "plan.json")]), 0)
            argv = ["reduce", "--gate", str(root / "gate.json"), "--plan", str(root / "plan.json"),
                    "--out", str(root / "result.json")]
            for i in range(4):
                argv += ["--capture", str(root / f"{i}.json")]
            self.assertEqual(SPEED.main(argv), 0)
            captures[0]["identity"]["binary_sha256"] = "b" * 64
            (root / "0.json").write_text(json.dumps(captures[0]), encoding="utf-8")
            self.assertEqual(SPEED.main(argv), 1)
            self.assertFalse(json.loads((root / "result.json").read_text())["gate_predictive"])
            (root / "0.json").write_text(json.dumps(fixture()[1][0]), encoding="utf-8")
            gate["role_case_ids"] = ["log-024@0"]
            (root / "gate.json").write_text(json.dumps(gate), encoding="utf-8")
            self.assertEqual(SPEED.main(argv), 1)
            result = json.loads((root / "result.json").read_text())
            self.assertFalse(result["gate_predictive"])
            self.assertIn("plan.role_case_ids", " ".join(result["diagnostic_reasons"]))
            (root / "gate.json").write_text("{}", encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                self.assertEqual(SPEED.main(argv), 2)


if __name__ == "__main__":
    unittest.main()
