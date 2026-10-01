"""Consumer-visible concurrency evidence, baseline comparability and config rewrites."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "omp_parallel_proof.py"
SPEC = importlib.util.spec_from_file_location("omp_parallel_proof", SCRIPT)
proof = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(proof)


def request(event, number, timestamp, *, instance="lane-1", model="q38-ninfer", duration=None):
    record = {"event": event, "server_instance_id": instance, "timestamp_unix_ms": timestamp * 1000,
              "request": {"request_id": number, "model": model}}
    if duration is not None:
        record["timings_seconds"] = {"total": duration, "decode": 0.01, "ttft": 999}
    return record


class OverlapTests(unittest.TestCase):
    def test_nested_intervals_measure_overlapped_wall_time_not_pairwise_sum(self):
        result = proof.compute_overlap([(2, 5), (0, 8), (3, 4), (10, 12), (11, 13)])
        self.assertEqual(result, {"max_in_flight": 3, "overlap_seconds": 4.0})

    def test_half_open_boundaries_and_zero_duration_do_not_create_overlap(self):
        self.assertEqual(proof.compute_overlap([(0, 1), (1, 2), (1, 1)]),
                         {"max_in_flight": 1, "overlap_seconds": 0.0})
        self.assertEqual(proof.compute_overlap([]), {"max_in_flight": 0, "overlap_seconds": 0.0})

    def test_invalid_intervals_cannot_be_evidence(self):
        for interval in ((2, 1), (0, float("nan")), (float("inf"), 3), (True, 3)):
            with self.subTest(interval=interval), self.assertRaises(ValueError):
                proof.compute_overlap([interval])

    def test_start_records_take_precedence_over_own_total_duration(self):
        rows = [request("request_start", 1, 1), request("request_done", 1, 5, duration=20),
                request("request_start", 2, 3), request("request_done", 2, 6, duration=20)]
        result = proof.analyze_requests(rows[::-1], 0, 10, "q38-ninfer")
        self.assertEqual(result["intervals_unix_seconds"], [[1.0, 5.0], [3.0, 6.0]])
        self.assertEqual(result["max_in_flight"], 2)
        self.assertEqual(result["overlap_seconds"], 2)
        self.assertEqual(result["request_count"], 2)
        self.assertEqual(result["timestamp_fields"]["start"], ["request_start.timestamp_unix_ms"])

    def test_missing_starts_use_each_done_records_total_not_other_timings(self):
        rows = [request("request_done", 1, 5, duration=4), request("request", 2, 7, duration=4)]
        result = proof.analyze_requests(rows, 0, 10, "q38-ninfer")
        self.assertEqual(result["intervals_unix_seconds"], [[1.0, 5.0], [3.0, 7.0]])
        self.assertEqual(result["overlap_seconds"], 2)
        self.assertEqual(result["timestamp_fields"]["start"],
                         ["request.timestamp_unix_ms - timings_seconds.total * 1000",
                          "request_done.timestamp_unix_ms - timings_seconds.total * 1000"])

    def test_duplicate_log_records_do_not_double_count_and_restarts_do_not_alias(self):
        first = [request("request_start", 1, 1), request("request_done", 1, 3)]
        second = [request("request_start", 1, 2, instance="lane-2"),
                  request("request_done", 1, 4, instance="lane-2")]
        result = proof.analyze_requests(first + second + first, 0, 5, "q38-ninfer")
        self.assertEqual(result["server_instance_ids"], ["lane-1", "lane-2"])
        self.assertEqual(result["request_count"], 2)
        self.assertEqual(result["overlap_seconds"], 1)

    def test_only_contained_requests_on_selected_model_count(self):
        rows = [request("request_start", 1, 9), request("request_done", 1, 11),
                request("request_done", 2, 12, duration=1),
                request("request_start", 3, 18), request("request_done", 3, 21),
                request("request_start", 4, 11, model="another"),
                request("request_done", 4, 14, model="another"),
                {"event": "throughput", "timestamp_unix_ms": 13000, "interval_seconds": 30}]
        result = proof.analyze_requests(rows, 10, 20, "q38-ninfer")
        self.assertEqual(result["intervals_unix_seconds"], [[11.0, 12.0]])
        self.assertEqual(result["request_count"], 1)
        self.assertEqual(result["unmatched_starts"], 1)
        self.assertEqual(result["overlap_seconds"], 0)

    def test_missing_or_invalid_duration_fails_instead_of_inventing_an_interval(self):
        for duration in (None, -1, float("nan"), "3"):
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                proof.analyze_requests([request("request_done", 1, 5, duration=duration)],
                                       0, 10, "q38-ninfer")

    def test_conflicting_duplicates_and_backwards_timestamps_are_not_proof(self):
        for rows in ([request("request_start", 1, 1), request("request_start", 1, 2)],
                     [request("request_start", 1, 7), request("request_done", 1, 5)]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                proof.analyze_requests(rows, 0, 10, "q38-ninfer")

    def test_cancelled_requests_are_counted_and_their_overlap_is_reported_apart(self):
        rows = [request("request_start", 1, 1), request("request_done", 1, 4),
                request("request_start", 2, 2), request("request_done", 2, 3),
                request("request_start", 3, 5), request("request_done", 3, 6)]
        rows[3]["result"] = {"finish_reason": "cancelled", "completion_tokens": 0}
        result = proof.analyze_requests(rows, 0, 10, "q38-ninfer")
        self.assertEqual((result["max_in_flight"], result["overlap_seconds"]), (2, 1))
        self.assertEqual(result["cancelled_requests"], 1)
        self.assertEqual(result["without_cancelled"], {"max_in_flight": 1, "overlap_seconds": 0.0})


class SubagentResultTests(unittest.TestCase):
    def test_codes_after_escaped_newlines_in_structured_results_count(self):
        # EXP-090: scouts returned JSON text whose report ended "verbatim:\n\nALPHA-CODE=...".
        output = json.dumps({"summary": "Read alpha.txt.", "files": [{"path": "alpha.txt"}],
                             "report": "The exact line, verbatim:\n\nALPHA-CODE=201123"}, indent=2)
        self.assertEqual(proof.result_codes(output), ["ALPHA-CODE=201123"])
        self.assertEqual(proof.result_codes({"report": ["x", "BETA-CODE=313027"]}), ["BETA-CODE=313027"])
        self.assertEqual(proof.result_codes("plain BETA-CODE=313027."), ["BETA-CODE=313027"])
        self.assertEqual(proof.result_codes('{"report": "XALPHA-CODE=201123 ALPHA-CODE=2011234"}'), [])

    def test_observer_records_calls_without_results_and_each_subagent(self):
        observer = proof.TaskObserver()
        two = {"type": "tool_execution_start", "toolName": "task", "args": {"tasks": [{}, {}]}}
        results = [{"exitCode": 0, "output": json.dumps({"report": "line:\nALPHA-CODE=201123"})},
                   {"exitCode": 1, "aborted": False, "output": "BETA-CODE=313027"}]
        for event in (two, {"type": "tool_execution_end", "toolName": "task",
                            "result": {"content": [{"type": "text", "text": "Task execution failed"}]}},
                      {"type": "tool_execution_start", "toolName": "read", "args": {}},
                      two, {"type": "tool_execution_end", "toolName": "task",
                            "result": {"details": {"results": results}}}):
            observer(event)
        self.assertEqual(observer.batches, [2, 2])
        self.assertEqual(observer.without_results, 1)
        self.assertEqual(observer.completed, [{"ok": True, "codes": ["ALPHA-CODE=201123"]},
                                              {"ok": False, "codes": ["BETA-CODE=313027"]}])


class ConfigRewriteTests(unittest.TestCase):
    def test_changes_only_the_selected_provider_without_mutating_the_seed(self):
        original = {"providers": {"maxInFlightRequests": {"ninfer-beta": 1, "another": 3},
                                  "streamIdleTimeoutSeconds": 90},
                    "retry": {"enabled": False}}
        seed = deepcopy(original)
        result = proof.rewrite_config(original, "ninfer-beta", 2)
        self.assertEqual(original, seed)
        self.assertEqual(result, {"providers": {"maxInFlightRequests": {"ninfer-beta": 2, "another": 3},
                                               "streamIdleTimeoutSeconds": 90},
                                  "retry": {"enabled": False}})
        self.assertEqual(proof.rewrite_config(result, "ninfer-beta", 1), original)

    def test_adds_missing_provider_and_mapping(self):
        self.assertEqual(proof.rewrite_config({}, "ninfer-beta", 2),
                         {"providers": {"maxInFlightRequests": {"ninfer-beta": 2}}})
        result = proof.rewrite_config({"providers": {"maxInFlightRequests": {"another": 1}}},
                                     "ninfer-beta", 2)
        self.assertEqual(result["providers"]["maxInFlightRequests"], {"another": 1, "ninfer-beta": 2})

    def test_refuses_invalid_limits_and_nonmapping_configuration(self):
        for limit in (0, -1, 1.5, True, "2"):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                proof.rewrite_config({}, "ninfer-beta", limit)
        for config in (None, [], {"providers": None}, {"providers": {"maxInFlightRequests": []}}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                proof.rewrite_config(config, "ninfer-beta", 2)


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.baseline = {"max_in_flight": 1, "passed": True, "model": "ninfer-beta/q38-ninfer",
                         "provider": "ninfer-beta", "thinking": "low", "seed": 7,
                         "omp": {"sha256": proof.OMP_SHA256},
                         "scenarios": [{"scenario": "sessions", "passed": True,
                                        "server_instance_ids": ["same-lane"], "wall_seconds": 12}]}
        self.current = deepcopy(self.baseline)
        self.current["max_in_flight"] = 2
        self.current["scenarios"][0]["wall_seconds"] = 8

    def test_reports_observed_savings_including_negative_savings(self):
        result = proof.compare_baseline(self.current, self.baseline)[0]
        self.assertEqual(result["wall_seconds_saved"], 4)
        self.assertEqual(result["speedup"], 1.5)
        self.current["scenarios"][0]["wall_seconds"] = 24
        self.assertEqual(proof.compare_baseline(self.current, self.baseline)[0]["wall_seconds_saved"], -12)

    def test_rejects_incomparable_runs(self):
        for key, value in (("seed", 8), ("model", "other"), ("provider", "other"), ("thinking", "medium")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                proof.compare_baseline({**self.current, key: value}, self.baseline)
        for changed in ({"passed": False}, {"server_instance_ids": ["restarted"]}, {"wall_seconds": 0}):
            current = deepcopy(self.current)
            current["scenarios"][0].update(changed)
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                proof.compare_baseline(current, self.baseline)
        with self.assertRaises(ValueError):
            proof.compare_baseline(self.current, {**self.baseline, "max_in_flight": 2})
        current = deepcopy(self.current)
        current["omp"]["sha256"] = "different-client"
        with self.assertRaises(ValueError):
            proof.compare_baseline(current, self.baseline)


if __name__ == "__main__":
    unittest.main()
