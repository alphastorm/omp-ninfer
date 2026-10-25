from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import agent_mix_probe
import concurrency_probe
import engine_window_compare
import fleet_probe
import multisession_probe
import omp_parallel_proof
import qualify_rtx5090_profile
import speculative_decode_probe
import warm_arrival_probe

FIXTURES = json.loads((ROOT / "tests/fixtures/status-log-consumers.json").read_text())
PROBE_SPEC = importlib.util.spec_from_file_location("schema_client_probe", ROOT / "scripts/hosts/omp-client-probe.py")
CLIENT_PROBE = importlib.util.module_from_spec(PROBE_SPEC)
PROBE_SPEC.loader.exec_module(CLIENT_PROBE)


class StatusConsumerTests(unittest.TestCase):
    def test_old_and_new_status_bind_the_same_complete_subject(self):
        subjects = []
        for schema in (1, 2):
            status = copy.deepcopy(FIXTURES[f"status_{schema}"])
            lane = fleet_probe.Lane("http://unused.invalid", "fixture-key", "fixture-session", "q38-ninfer")
            with mock.patch.object(lane, "_request", return_value=status):
                self.assertEqual(lane.status(), status)
                subjects.append(lane.identity())
                snapshot = warm_arrival_probe.cache_snapshot(lane)
            self.assertEqual(snapshot["reused_prompt_tokens"], 10000)
            self.assertEqual(snapshot["last_selection"]["path"], "private_long_anchor")
            self.assertEqual(multisession_probe.counters(status), {})
            if schema == 2:
                self.assertIsNone(snapshot["host_state"]["capacity"])
                self.assertIsNone(snapshot["host_kv"]["capacity_bytes"])
                self.assertEqual(snapshot["unavailable_fields"], status["unavailable_fields"])
        self.assertEqual(subjects[0], subjects[1])
        self.assertEqual(set(subjects[0]), set(fleet_probe.IDENTITY_KEYS))

    def test_missing_or_null_attestation_never_weakens_subject_binding(self):
        for schema in (1, 2):
            for key in fleet_probe.IDENTITY_KEYS:
                for missing in (False, True):
                    with self.subTest(schema=schema, key=key, missing=missing):
                        status = copy.deepcopy(FIXTURES[f"status_{schema}"])
                        if missing:
                            del status["identity"][key]
                        else:
                            status["identity"][key] = None
                        with self.assertRaises(ValueError):
                            fleet_probe.lane_identity(status)

    def test_restart_requires_real_counter_reset_on_both_schemas(self):
        for schema in (1, 2):
            before = copy.deepcopy(FIXTURES[f"status_{schema}"])
            after = copy.deepcopy(before)
            after["scheduler"]["computed_prefill_tokens"] = 0
            lane = mock.Mock()
            lane.status.side_effect = [before, after]
            with mock.patch.object(fleet_probe, "wait_ready", return_value=0.0), mock.patch.object(fleet_probe.subprocess, "run"):
                proof = fleet_probe.verified_restart(lane, "restart-fixture")
            self.assertEqual((proof["prefill_counter_before"], proof["prefill_counter_after"]), (12000, 0))
            for value in (None, True, -1, "12000"):
                with self.subTest(schema=schema, value=value):
                    invalid = copy.deepcopy(before)
                    invalid["scheduler"]["computed_prefill_tokens"] = value
                    lane.status.side_effect = [invalid]
                    with mock.patch.object(fleet_probe.subprocess, "run") as restart, self.assertRaises(ValueError):
                        fleet_probe.verified_restart(lane, "must-not-run")
                    restart.assert_not_called()
            lane.status.side_effect = [before, before]
            with mock.patch.object(fleet_probe, "wait_ready", return_value=0.0), mock.patch.object(fleet_probe.subprocess, "run"), self.assertRaisesRegex(RuntimeError, "did not reset"):
                fleet_probe.verified_restart(lane, "ineffective-fixture")

    def test_missing_reuse_is_not_fabricated_as_zero(self):
        for schema in (1, 2):
            status = copy.deepcopy(FIXTURES[f"status_{schema}"])
            status["cache"]["reused_prompt_tokens"] = None
            with self.assertRaises(ValueError):
                warm_arrival_probe.cache_snapshot(mock.Mock(status=mock.Mock(return_value=status)))

    def test_status_schema_is_not_a_request_log_or_health_response(self):
        for schema in (None, True, 17, 30):
            status = copy.deepcopy(FIXTURES["status_2"])
            status["schema_version"] = schema
            with self.assertRaises(ValueError):
                fleet_probe.validate_status(status)

    def test_host_client_acceptance_accepts_both_schemas_without_weakening_identity(self):
        expected = {"server_binary_sha256": "b" * 64, "model_sha256": "a" * 64,
                    "configuration_sha256": "e" * 64}
        for schema in (1, 2):
            status = copy.deepcopy(FIXTURES[f"status_{schema}"])
            self.assertEqual(CLIENT_PROBE.runtime_identity(status, expected), status["identity"])
            with self.assertRaises(AssertionError):
                CLIENT_PROBE.runtime_identity(status, dict(expected, status_schema_version=3 - schema))
            status["identity"]["binary_sha256"] = None
            with self.assertRaises(AssertionError):
                CLIENT_PROBE.runtime_identity(status, expected)


class RequestLogConsumerTests(unittest.TestCase):
    def test_old_and_new_log_projections_keep_usage_and_speculative_work(self):
        views = []
        for schema in (17, 30):
            row = FIXTURES[f"request_done_{schema}"]
            outcome = row["result"]
            self.assertEqual(qualify_rtx5090_profile.find_decode_record([row], 12000, 512), row)
            engine = engine_window_compare.server_view([row], 12000, 512)
            speculative = speculative_decode_probe.server_view([row], outcome, set())
            self.assertEqual(engine["computed_prefill_tokens"], 2000)
            self.assertEqual(engine["reused_tokens"], 10000)
            self.assertEqual(engine["decode_tok_s"], 256.0)
            self.assertEqual(speculative["drafted_tokens"], 1024)
            self.assertEqual(speculative["accepted_tokens"], 256)
            self.assertEqual(speculative["draft_acceptance"], 0.25)
            self.assertEqual(speculative["accepted_per_position"], row["speculative"]["accepted_per_position"])
            views.append((engine, speculative))
        self.assertEqual(views[0], views[1])

    def test_log_window_joins_both_schemas_by_client_identity(self):
        for schema in (17, 30):
            row = FIXTURES[f"request_done_{schema}"]
            fetched = subprocess.CompletedProcess("fixture", 0, json.dumps(row), "")
            request = {"request_sha256": row["request"]["client_identity"]["request_sha256"]}
            receipt = {"scenarios": [{"requests": [request]}]}
            probe = object.__new__(concurrency_probe.Probe)
            probe.args = argparse.Namespace(log_cmd="fixture")
            probe.api_key = "fixture-key"
            probe.receipt = receipt
            with mock.patch.object(concurrency_probe, "run_command", return_value=fetched):
                probe.attach_logs(1000, 3000)
            self.assertEqual(len(request["server_request_done"]), 1)
            self.assertEqual(request["prefix_reuse_path"], "private_long_anchor")
            with mock.patch.object(fleet_probe.subprocess, "run", return_value=fetched):
                reuse = fleet_probe.reuse_classes("fixture", 1000)
            self.assertEqual(reuse[0]["reused_tokens"], 10000)

    def test_parallel_overlap_still_uses_request_timestamps_not_schema_number(self):
        for schema in (17, 30):
            done = copy.deepcopy(FIXTURES[f"request_done_{schema}"])
            done["timestamp_unix_ms"] = 5000
            start = copy.deepcopy(done)
            start.update(event="request_start", timestamp_unix_ms=2000)
            proof = omp_parallel_proof.analyze_requests([start, done], 0, 10, "q38-ninfer")
            self.assertEqual(proof["intervals_unix_seconds"], [[2.0, 5.0]])
            self.assertEqual(proof["request_count"], 1)

    def test_agent_mix_join_preserves_server_work_not_prompt_length(self):
        for schema in (17, 30):
            done = FIXTURES[f"request_done_{schema}"]
            start = dict(done, event="request_start", timestamp_unix_ms=1000)
            row = {"index": 1, "message_count": 1, "tool_count": 0, "api_prompt_tokens": 12000}
            joined = agent_mix_probe.join_logs([row], [start, done], 1000)
            self.assertEqual(joined[0]["server"]["computed_prefill_tokens"], 2000)
            self.assertEqual(joined[0]["server"]["prefix_cache_hit_tokens"], 10000)

    def test_optional_pressure_counters_stay_absent_not_zero(self):
        for schema in (1, 2):
            self.assertEqual(multisession_probe.counters(FIXTURES[f"status_{schema}"]), {})


if __name__ == "__main__":
    unittest.main()
