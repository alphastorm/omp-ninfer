"""Versioned, file-only replay of retained agent-probe comparisons."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_parity.py"
FIXTURES = ROOT / "tests" / "fixtures" / "agent_parity"


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


class AgentParityTests(unittest.TestCase):
    def setUp(self):
        self.receipts = {name: fixture(name) for name in (
            "control", "candidate", "corrected-control", "corrected-candidate")}

    def judge(self, document):
        with tempfile.TemporaryDirectory(prefix="agent-parity-") as directory:
            root = Path(directory)
            for name, receipt in self.receipts.items():
                (root / f"{name}.json").write_text(json.dumps(receipt), encoding="utf-8")
            comparison = root / "comparison.json"
            comparison.write_text(json.dumps(document), encoding="utf-8")
            output = root / "verdict.json"
            result = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), str(comparison), "--out", str(output)],
                capture_output=True, text=True, timeout=15)
            self.assertIn(result.returncode, (0, 1, 2), result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertEqual(output.read_text(encoding="utf-8"), result.stdout)
            verdict = json.loads(result.stdout)
            if result.returncode != 2:
                self.assertEqual(result.returncode == 0, verdict["passed"])
            return result.returncode, verdict

    def contract_error(self, document):
        code, verdict = self.judge(document)
        self.assertEqual(code, 2, verdict)
        self.assertFalse(verdict["passed"])
        self.assertEqual(verdict["error"]["code"], "contract-version")
        self.assertIn("contract-version error", verdict["error"]["message"])
        self.assertNotIn("jobs", verdict)  # Never export an empty or partial judgement.
        return verdict

    def ordered(self, arm):
        requests = self.receipts[arm]["scenarios"][0]["requests"]
        return sorted((row for row in requests if row["phase"] == "branches"),
                      key=lambda row: row["first_output_monotonic_s"])

    def test_real_label_swap_passes_under_rule_two(self):
        code, verdict = self.judge(fixture("label-swap"))
        self.assertEqual(code, 0, verdict)
        self.assertEqual(verdict["rule"], "p16-agent-parity/2")
        job = verdict["jobs"]["concurrency"]
        self.assertEqual(len(job["paired_positions"]), job["positions"])
        concurrent = [row for row in job["paired_positions"] if row["pairing"] == "admission_rank"]
        self.assertEqual(len(concurrent), 4)
        self.assertTrue(any(row["incumbent_label"] != row["candidate_label"] for row in concurrent))
        self.assertTrue(all(row["ordering_source"] == "client_first_output_monotonic_s" for row in concurrent))

    def test_same_label_swap_fails_under_rule_one(self):
        document = fixture("label-swap")
        document["rule"] = "p16-agent-parity/1"
        code, verdict = self.judge(document)
        self.assertEqual(code, 1, verdict)
        self.assertEqual(verdict["jobs"]["concurrency"]["failing"], {
            "3": ["ttft 1.183s > bound 0.536s"],
            "5": ["cached-prompt -29 < incumbent -23"],
        })

    def test_admission_rank_030_seconds_slower_fails(self):
        document = fixture("label-swap")
        incumbent, candidate = self.ordered("control")[1], self.ordered("candidate")[1]
        rows = document["jobs"]["concurrency"]["positions"]
        inc = next(row for row in rows if row["label"] == incumbent["label"])
        cand = next(row for row in rows if row["label"] == candidate["label"])
        ttft = inc["incumbent_server_ttft_seconds"] + 0.30
        cand["candidate_server_ttft_seconds"] = ttft
        candidate["first_output_monotonic_s"] = candidate["submitted_monotonic_s"] + ttft
        code, verdict = self.judge(document)
        self.assertEqual(code, 1, verdict)
        failing = verdict["jobs"]["concurrency"]["failing"]
        self.assertEqual(failing, {str(inc["position"]): ["ttft 0.586s > bound 0.536s"]})

    def test_one_token_admission_rank_cache_gap_deficit_fails(self):
        document = fixture("label-swap")
        label = self.ordered("candidate")[1]["label"]
        row = next(row for row in document["jobs"]["concurrency"]["positions"] if row["label"] == label)
        row["candidate_cached_tokens"] -= 1
        code, verdict = self.judge(document)
        self.assertEqual(code, 1, verdict)
        self.assertEqual(verdict["jobs"]["concurrency"]["failing"], {
            "3": ["cached-prompt -30 < incumbent -29"],
        })

    def test_contract_and_rule_identify_every_verdict_level(self):
        _, verdict = self.judge(fixture("label-swap"))
        levels = [verdict, verdict["jobs"]["concurrency"], *verdict["jobs"]["concurrency"]["paired_positions"]]
        for item in levels:
            self.assertEqual(item["contract_version"], 2)
            self.assertEqual(item["rule"], "p16-agent-parity/2")

    def test_legacy_position_only_inputs_keep_rule_one_verdicts(self):
        for name, count in (("legacy-arrival", 12), ("legacy-native", 83)):
            with self.subTest(fixture=name):
                code, verdict = self.judge(fixture(name))
                self.assertEqual(code, 0, verdict)
                self.assertEqual(verdict["contract_version"], 1)
                self.assertEqual(verdict["rule"], "p16-agent-parity/1")
                self.assertEqual(sum(job["positions"] for job in verdict["jobs"].values()), count)

    def test_legacy_input_under_rule_two_has_explicit_contract_error(self):
        document = fixture("legacy-arrival")
        document["rule"] = "p16-agent-parity/2"
        self.contract_error(document)
        document["contract_version"] = 2  # Stamping a new version cannot invent missing labels.
        self.contract_error(document)

    def test_missing_or_unsupported_contract_or_rule_fails_loudly(self):
        for key, values in (("contract_version", (None, 0, 3, "2", True)),
                            ("rule", (None, "p16-agent-parity/0", "p16-agent-parity/3", 2))):
            for value in values:
                with self.subTest(key=key, value=value):
                    document = fixture("label-swap")
                    if value is None:
                        del document[key]
                    else:
                        document[key] = value
                    self.contract_error(document)

    def test_empty_jobs_or_positions_never_pass_vacuously(self):
        for jobs in ({}, {"probe": {"positions": []}}):
            self.contract_error({"contract_version": 2, "rule": "p16-agent-parity/2", "jobs": jobs})

    def test_pairing_failure_is_contract_error_not_empty_pairings(self):
        self.receipts["candidate"]["scenarios"][0]["requests"][-1]["phase"] = "foreign-phase"
        self.contract_error(fixture("label-swap"))

    def test_missing_receipt_is_explicit_contract_error(self):
        document = fixture("label-swap")
        document["jobs"]["concurrency"]["concurrent_receipts"]["candidate"] = "missing.json"
        self.contract_error(document)

    def test_driver_only_jobs_remain_explicitly_unjudged(self):
        code, verdict = self.judge({"contract_version": 2, "rule": "p16-agent-parity/2",
                                    "jobs": {"driver-only": {}}})
        self.assertEqual(code, 0, verdict)
        self.assertFalse(verdict["jobs"]["driver-only"]["judged"])
        self.assertEqual(verdict["jobs"]["driver-only"]["note"], "no per-position rows; driver verdict applies")

    def test_renamed_labels_and_phases_keep_receipt_derived_membership(self):
        document = fixture("label-swap")
        for receipt in self.receipts.values():
            for scenario in receipt["scenarios"]:
                for request in scenario["requests"]:
                    request["label"] = "renamed-" + request["label"]
                    request["phase"] = "phase-" + request["phase"]
                for phase in scenario["phases"]:
                    phase["name"] = "phase-" + phase["name"]
                    for request in phase["summary"]["per_request"]:
                        request["label"] = "renamed-" + request["label"]
        for row in document["jobs"]["concurrency"]["positions"]:
            row["label"] = "renamed-" + row["label"]
        self.assertEqual(self.judge(document)[0], 0)

    def test_sequential_positions_keep_label_pairing(self):
        document = fixture("label-swap")
        base = document["jobs"]["concurrency"]["positions"][0]
        base["candidate_server_ttft_seconds"] = base["incumbent_server_ttft_seconds"] * 1.25 + 0.01
        code, verdict = self.judge(document)
        self.assertEqual(code, 1, verdict)
        self.assertIn("1", verdict["jobs"]["concurrency"]["failing"])

    def test_server_timestamps_take_precedence_over_client_order(self):
        for arm in ("control", "candidate"):
            for index, request in enumerate(self.ordered(arm)):
                request["server_request_done"] = [{"generation": {"admission": {"admitted_monotonic_s": index}}}]
        ordered = self.ordered("candidate")
        for row, value in zip(ordered, reversed([row["first_output_monotonic_s"] for row in ordered])):
            row["first_output_monotonic_s"] = value
        code, verdict = self.judge(fixture("label-swap"))
        self.assertEqual(code, 0, verdict)
        concurrent = [row for row in verdict["jobs"]["concurrency"]["paired_positions"]
                      if row["pairing"] == "admission_rank"]
        self.assertTrue(all(row["ordering_source"] == "server_admission.admitted_monotonic_s" for row in concurrent))

    def test_retained_labeled_consumers_preserve_verdicts(self):
        for name, count, expected_code in (("labeled-arrival", 12, 0), ("initial-labels", 88, 1),
                                            ("corrected-comparison", 17, 1)):
            with self.subTest(fixture=name):
                code, verdict = self.judge(fixture(name))
                self.assertEqual(code, expected_code, verdict)
                self.assertEqual(sum(len(job["paired_positions"]) for job in verdict["jobs"].values()), count)
                if name == "corrected-comparison":
                    concurrent = [row for row in verdict["jobs"]["concurrency"]["paired_positions"]
                                  if row["pairing"] == "admission_rank"]
                    self.assertTrue(all(row["ordering_source"] == "server_admission.started_unix_ms"
                                        for row in concurrent))


if __name__ == "__main__":
    unittest.main()
