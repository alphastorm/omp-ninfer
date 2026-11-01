"""Consumer-visible concurrency evidence, baseline comparability and config rewrites."""
from __future__ import annotations

import ast
from contextlib import contextmanager
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

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


def task_events(outputs, *, names=("Alpha", "Beta"), call="call-1", ids=None):
    """Stock OMP's indexed task results, bound to their dispatch by toolCallId."""
    tasks = [{"name": name, "agent": "scout", "task": f"Read {name.lower()}.txt"}
             for name in names]
    results = [{"index": index, "id": (ids or names)[index], "agent": "scout",
                "exitCode": 0, "output": output}
               for index, output in enumerate(outputs)]
    return [{"type": "tool_execution_start", "toolName": "task", "toolCallId": call,
             "args": {"tasks": tasks}},
            {"type": "tool_execution_end", "toolName": "task", "toolCallId": call,
             "result": {"details": {"results": results}}}]


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
    codes = ("ALPHA-CODE=201123", "BETA-CODE=313027")

    def subagents(self, outputs=None, *, answer=None, events=None, stop="stop"):
        """Exercise the real subagent/receipt aggregation without an OMP process or lane."""
        if outputs is None:
            outputs = self.codes
        if answer is None:
            answer = "\n".join(self.codes)
        if events is None:
            events = task_events(outputs)
        args = SimpleNamespace(seed=7, turn_timeout=1, log_cmd="synthetic", log_timeout=1,
                               model="synthetic/q38-ninfer", max_in_flight=2)

        @contextmanager
        def fake_client(_args, _label, observe):
            def prompt(_prompt, _timeout):
                for event in events:
                    observe(event)
                return {"answer": answer, "stop": stop, "seconds": 0.25}
            yield SimpleNamespace(prompt=prompt)

        rows = [request("request_start", 1, 1), request("request_done", 1, 3),
                request("request_start", 2, 2), request("request_done", 2, 4)]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shared = root / "shared" / ".omp"
            shared.mkdir(parents=True)
            with patch.object(proof, "client", fake_client), \
                 patch.object(proof, "fetch_log", return_value=rows), \
                 patch.object(proof.time, "time", side_effect=[0, 5]):
                return proof.run_scenario(args, root, shared, "subagents", self.codes)

    def test_codes_after_escaped_newlines_in_structured_results_count(self):
        # EXP-090: scouts returned JSON text whose report ended "verbatim:\n\nALPHA-CODE=...".
        output = json.dumps({"summary": "Read alpha.txt.", "files": [{"path": "alpha.txt"}],
                             "report": "The exact line, verbatim:\n\nALPHA-CODE=201123"}, indent=2)
        self.assertEqual(proof.result_codes(output), ["ALPHA-CODE=201123"])
        self.assertEqual(proof.result_codes({"report": ["x", "BETA-CODE=313027"]}), ["BETA-CODE=313027"])
        self.assertEqual(proof.result_codes("plain BETA-CODE=313027."), ["BETA-CODE=313027"])
        self.assertEqual(proof.result_codes('{"report": "XALPHA-CODE=201123 ALPHA-CODE=2011234"}'), [])

    def test_observer_records_calls_without_results_and_each_subagent(self):
        observer = proof.TaskObserver(self.codes)
        retry = task_events([json.dumps({"report": "line:\n" + self.codes[0]}), self.codes[1]],
                            call="retry")
        retry[1]["result"]["details"]["results"][1]["exitCode"] = 1
        for event in task_events([]) + retry:
            observer(event)
        self.assertEqual(observer.batches, [2, 2])
        self.assertEqual(observer.without_results, 1)
        self.assertEqual([item["ok"] for item in observer.completed], [True, False])
        self.assertEqual([item["session"] for item in observer.completed], ["alpha", "beta"])
        self.assertEqual([item["codes"] for item in observer.completed], [[code] for code in self.codes])
        self.assertTrue(all(item["attributable"] and item["nonempty"] for item in observer.completed))
        self.assertTrue(all(item["compliance"]["marker_exact"] for item in observer.completed))
        self.assertEqual([item["compliance"]["formatting_exact"] for item in observer.completed],
                         [False, True])
        self.assertTrue(all("output" not in item and "task" not in item for item in observer.completed))
        self.assertNotEqual(*[item["id_sha256"] for item in observer.completed])

    def test_recovered_dispatch_passes_but_sequential_errored_or_parent_read_runs_fail(self):
        # eaf221ac fourth window: a first task call without results, re-issued; then a scout that
        # answered without its code, re-dispatched alone. Both recovered; both must pass.
        recovered = task_events([]) + task_events(self.codes, call="retry")
        self.assertTrue(self.subagents(events=recovered)["passed"])
        recovered = (task_events([self.codes[0], "I could not extract the marker."])
                     + task_events([self.codes[1]], names=("Beta",), call="retry", ids=("Beta-2",)))
        self.assertTrue(self.subagents(events=recovered)["passed"])
        self.assertTrue(self.subagents()["passed"])
        sequential = (task_events([self.codes[0]], names=("Alpha",))
                      + task_events([self.codes[1]], names=("Beta",), call="second"))
        self.assertFalse(self.subagents(events=sequential)["checks"]["first_task_call_dispatched_both"])
        for tool in ("read", "grep", "bash", "eval"):
            events = [{"type": "tool_execution_start", "toolName": tool}] + task_events(self.codes)
            record = self.subagents(events=events)
            self.assertFalse(record["passed"])
            self.assertFalse(record["checks"]["parent_only_task_calls"])
        self.assertFalse(self.subagents(events=[])["checks"]["first_task_call_dispatched_both"])

    def test_delivery_values_not_marker_formatting_gate_plain_and_structured_results(self):
        alpha, beta = self.codes
        for code_index, own in enumerate(self.codes):
            cases = ((own.replace("=", ": "), True), (own.replace("=", " "), True),
                     (own, True), ("Marker unavailable.", False),
                     (own[:-1] + "9", False), (own.split("=")[1], False),
                     (own.replace(own.split("-")[0], "BETA" if code_index == 0 else "ALPHA"), False),
                     ("", False), (" \n", False), (own + "\n" + self.codes[1 - code_index], False))
            for answer, expected in cases:
                for structured in (False, True):
                    with self.subTest(index=code_index, answer=answer, structured=structured):
                        outputs = list(self.codes)
                        outputs[code_index] = (json.dumps({"report": "line:\n" + answer})
                                               if structured and answer.strip() else
                                               json.dumps({"report": answer}) if structured else answer)
                        record = self.subagents(outputs)
                        self.assertEqual(record["passed"], expected)
                        self.assertEqual(record["errors"], [])
        colon = self.subagents([alpha.replace("=", ": "), beta.replace("=", ": ")],
                               answer=alpha.replace("=", ": ") + "\n" + beta.replace("=", ": "))
        self.assertTrue(colon["passed"])
        self.assertFalse(colon["compliance"]["codes_exact"])
        self.assertFalse(colon["compliance"]["codes_delivered_by_subagents"])
        self.assertFalse(colon["compliance"]["parent_formatting_exact"])
        exact = self.subagents()
        self.assertTrue(exact["passed"])
        self.assertTrue(all(exact["compliance"].values()))
        self.assertTrue(all(item["compliance"]["formatting_exact"] for item in exact["subagent_results"]))

    def test_diagnosed_colon_delivery_replica_passes_without_rewriting_compliance(self):
        self.codes = ("ALPHA-CODE=860044", "BETA-CODE=962843")
        record = self.subagents(
            ["`ALPHA-CODE: 860044`",
             "BETA-CODE: 962843\n\n(Verbatim line: `BETA-CODE=962843`.)"],
            answer="ALPHA-CODE: 860044\nBETA-CODE=962843")
        self.assertTrue(record["passed"])
        self.assertFalse(record["compliance"]["codes_exact"])
        self.assertFalse(record["compliance"]["codes_delivered_by_subagents"])
        self.assertTrue(all(item["nonempty"] and item["attributable"] and item["isolation"]
                            for item in record["subagent_results"]))

    def test_parent_delivery_missing_near_miss_empty_or_foreign_values_fail(self):
        alpha, beta = self.codes
        for answer in (alpha, alpha + "\n" + beta[:-1] + "9", "", " \n",
                       alpha + "\n" + beta + "\nALPHA-CODE: 999999"):
            with self.subTest(answer=answer):
                self.assertFalse(self.subagents(answer=answer)["passed"])
        for stop in ("length", "aborted", "error", "toolUse"):
            with self.subTest(stop=stop):
                self.assertFalse(self.subagents(stop=stop)["checks"]["parent_completed"])

    def test_foreign_values_fail_without_a_marker_or_at_any_token_boundary(self):
        for index, own in enumerate(self.codes):
            other = self.codes[1 - index].split("=")[1]
            for foreign in (other, "X" + other + "7", "ALPHA-CODE: " + other,
                            {"number": int(other)}, {other: "metadata"}):
                with self.subTest(index=index, foreign=foreign):
                    outputs = list(self.codes)
                    outputs[index] = {"report": own, "extra": foreign}
                    self.assertFalse(self.subagents(outputs)["checks"]["subagent_isolation"])

    def test_own_values_need_attributable_labels_and_alphanumeric_boundaries(self):
        own, beta = self.codes
        for separator in ("=", ": ", " ", " =\n"):
            marker = own.replace("=", separator)
            for wrapped in (f"`{marker}`.", f"_{marker}_", f"({marker})"):
                self.assertTrue(self.subagents([wrapped, beta])["passed"])
            for wrapped in ("X" + marker, marker + "7", marker + "x", "é" + marker, marker + "٢"):
                self.assertFalse(self.subagents([wrapped, beta])["passed"])

    def test_task_delivery_requires_two_distinct_matching_result_identities(self):
        for change in ("missing_result", "duplicate_id", "duplicate_index", "missing_index",
                       "unmatched_call", "missing_id", "wrong_agent", "unrelated_task",
                       "duplicate_task", "swapped_outputs"):
            with self.subTest(change=change):
                events = task_events(self.codes)
                results = events[1]["result"]["details"]["results"]
                if change == "missing_result":
                    results.pop()
                elif change == "duplicate_id":
                    results[1]["id"] = results[0]["id"]
                elif change == "duplicate_index":
                    results[1]["index"] = 0
                elif change == "missing_index":
                    results[1].pop("index")
                elif change == "unmatched_call":
                    events[1]["toolCallId"] = "unrelated"
                elif change == "missing_id":
                    results[1].pop("id")
                elif change == "wrong_agent":
                    results[1]["agent"] = "task"
                elif change == "unrelated_task":
                    events[0]["args"]["tasks"][1]["name"] = "Gamma"
                elif change == "duplicate_task":
                    events[0]["args"]["tasks"][1]["name"] = "Alpha"
                elif change == "swapped_outputs":
                    results[0]["output"], results[1]["output"] = results[1]["output"], results[0]["output"]
                record = self.subagents(events=events)
                self.assertFalse(record["passed"])
        for field, value in (("exitCode", 1), ("aborted", True), ("error", "failed")):
            events = task_events(self.codes)
            events[1]["result"]["details"]["results"][1][field] = value
            record = self.subagents(events=events)
            self.assertFalse(record["passed"])
            self.assertFalse(record["checks"]["subagents_completed"])

    def test_empty_structured_metadata_does_not_substitute_for_output(self):
        for empty in ({}, [], None, {"exitCode": 0, "aborted": False}, {"report": "\n"}):
            with self.subTest(empty=empty):
                record = self.subagents([empty, self.codes[1]])
                self.assertFalse(record["passed"])
                self.assertFalse(record["checks"]["subagent_results_nonempty"])


class SessionRecallTests(unittest.TestCase):
    codes = ("ALPHA-CODE=123456", "BETA-CODE=654321")

    def sessions(self, answer, *, session="alpha", index=2, stop="stop"):
        """Exercise the real session/check aggregation with synthetic in-memory RPC turns."""
        args = SimpleNamespace(turn_timeout=1, log_cmd="synthetic", log_timeout=1,
                               model="synthetic/q38-ninfer", max_in_flight=2)

        @contextmanager
        def fake_client(_args, label):
            own = self.codes[("alpha", "beta").index(label)]
            count = 0

            def prompt(_prompt, _timeout):
                nonlocal count
                count += 1
                selected = label == session and count == index
                return {"answer": answer if selected else ("OK" if count == 1 else own),
                        "stop": stop if selected else "stop", "seconds": 0.25}

            yield SimpleNamespace(prompt=prompt, state=lambda: {"session_id": label})

        rows = [request("request_start", 1, 1), request("request_done", 1, 3),
                request("request_start", 2, 2), request("request_done", 2, 4)]
        with patch.object(proof, "client_args", side_effect=lambda _args, _root, _shared, label: label), \
             patch.object(proof, "client", fake_client), \
             patch.object(proof, "fetch_log", return_value=rows), \
             patch.object(proof.time, "time", side_effect=[0, 5]):
            return proof.run_scenario(args, None, None, "sessions", self.codes)

    def test_gates_recall_and_isolation_not_formatting(self):
        for session, own, other in (("alpha", *self.codes), ("beta", *self.codes[::-1])):
            cases = (
                ("code_with_disclaimer", own + "\n\nSynthetic note: copied from the earlier prompt, "
                 "not independently verified.", True),
                ("colon_format", own.replace("=", ": "), True),
                ("space_format", own.replace("=", " "), True),
                ("missing_code", "I do not recall the synthetic marker.", False),
                ("near_miss", own[:-1] + "0", False),
                ("foreign_code", own + "\n" + other, False),
                ("empty_result", "", False),
                ("code_only", own, True),
            )
            for index in (2, 3):
                for name, answer, expected in cases:
                    with self.subTest(session=session, index=index, case=name):
                        record = self.sessions(answer, session=session, index=index)
                        self.assertEqual(record["passed"], expected)
                        self.assertEqual(record["errors"], [])

    def test_own_code_requires_alphanumeric_boundaries(self):
        own = self.codes[0]
        for answer in (f"`{own}`.", f"({own})", f"_{own}_", f"\n{own}\n"):
            with self.subTest(answer=answer):
                self.assertTrue(self.sessions(answer)["passed"])
        for answer in ("X" + own, own + "7", own + "x", "é" + own, own + "٢"):
            with self.subTest(answer=answer):
                self.assertFalse(self.sessions(answer)["passed"])

    def test_records_recall_isolation_and_non_gating_formatting_separately(self):
        own, other = self.codes
        for answer, recall, isolation, formatting in (
                (own + "\n\nSynthetic disclaimer.", True, True, False),
                ("unknown", False, True, False),
                (own + "\n" + other, True, False, False),
                (" \n" + own + "\n ", True, True, True)):
            with self.subTest(answer=answer):
                record = self.sessions(answer)
                turn = next(row for row in record["turns"]
                            if row["session"] == "alpha" and row["index"] == 2)
                self.assertEqual((turn["own_recall"], turn["isolation"],
                                  turn["compliance"]["formatting_exact"]),
                                 (recall, isolation, formatting))
                self.assertNotIn("recall_exact", turn)
                self.assertNotIn("answer", turn)
                seed = next(row for row in record["turns"]
                            if row["session"] == "alpha" and row["index"] == 1)
                self.assertNotIn("compliance", seed)
                self.assertEqual(set(record["checks"]), {
                    "alpha_three_turns_completed", "alpha_both_recalls_correct",
                    "beta_three_turns_completed", "beta_both_recalls_correct", "separate_sessions",
                    "alpha_turns_nonempty", "beta_turns_nonempty", "alpha_isolation", "beta_isolation",
                    "logged_requests", "all_logged_requests_completed", "single_server_instance",
                    "provider_limit_respected", "concurrency_expected",
                })

    def test_value_isolation_and_nonempty_output_apply_to_every_turn(self):
        own, other = self.codes
        foreign = other.split("=")[1]
        for index in (1, 2, 3):
            for answer in ("", " \n", own + "\n" + foreign,
                           own + "\nX" + foreign + "7", own + "\n" + other.replace("=", ": "),
                           own + "\nALPHA-CODE: " + foreign):
                with self.subTest(index=index, answer=answer):
                    self.assertFalse(self.sessions(answer, index=index)["passed"])
        colon = self.sessions(own.replace("=", ": "))
        self.assertTrue(colon["passed"])
        self.assertFalse(colon["compliance"]["alpha_both_recalls_marker_exact"])
        turn = next(row for row in colon["turns"] if row["session"] == "alpha" and row["index"] == 2)
        self.assertEqual(turn["compliance"], {"marker_exact": False, "formatting_exact": False})

    def test_foreign_code_is_rejected_even_inside_a_longer_run(self):
        own, other = self.codes
        record = self.sessions(own + "\nX" + other + "7")
        self.assertFalse(record["passed"])
        turn = next(row for row in record["turns"]
                    if row["session"] == "alpha" and row["index"] == 2)
        self.assertTrue(turn["own_recall"])
        self.assertFalse(turn["isolation"])

    def test_correct_recall_does_not_bypass_completion_or_stop_checks(self):
        for stop in ("length", "aborted", "error", "toolUse", "unexpected"):
            with self.subTest(stop=stop):
                record = self.sessions(self.codes[0], stop=stop)
                self.assertFalse(record["passed"])
                self.assertFalse(record["checks"]["alpha_three_turns_completed"])
                turn = next(row for row in record["turns"]
                            if row["session"] == "alpha" and row["index"] == 2)
                self.assertEqual(turn["seconds"], 0.25)
                self.assertEqual(turn["stop"], stop if stop in proof.STOPS else "error")
                self.assertFalse(turn["completed"])


class GatingPredicateTests(unittest.TestCase):
    # Classification from the C2 diagnosis: structural/lane checks remain gates;
    # literal model-text compliance must not feed the verdict. Unknown gates fail closed.
    classifications = {
        "parent_completed": "completion", "parent_nonempty": "delivery",
        "first_task_call_dispatched_both": "topology",
        "parent_only_task_calls": "topology",
        "task_results_attributable": "identity", "subagents_completed": "completion",
        "subagent_results_nonempty": "delivery", "parent_codes_delivered": "delivery",
        "subagent_codes_delivered": "delivery", "subagent_isolation": "isolation",
        "parent_code_isolation": "isolation",
        "alpha_three_turns_completed": "completion", "beta_three_turns_completed": "completion",
        "alpha_turns_nonempty": "delivery", "beta_turns_nonempty": "delivery",
        "alpha_both_recalls_correct": "delivery", "beta_both_recalls_correct": "delivery",
        "alpha_isolation": "isolation", "beta_isolation": "isolation",
        "separate_sessions": "identity", "logged_requests": "evidence",
        "all_logged_requests_completed": "evidence", "single_server_instance": "identity",
        "provider_limit_respected": "concurrency", "concurrency_expected": "concurrency",
        "request_log_analyzed": "evidence",
        "codes_exact": "model_exact_text", "codes_delivered_by_subagents": "model_exact_text",
    }

    def test_gating_inventory_excludes_exact_model_text(self):
        scouts, sessions = SubagentResultTests(), SessionRecallTests()
        records = [scouts.subagents(), sessions.sessions(sessions.codes[0])]
        observed = {key for record in records for key in record["checks"]}
        # Enumerate every checks write, including the log-analysis failure sentinel, so a new
        # branch cannot add an unclassified gate without extending this invariant.
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        declared = set()

        def is_checks(node):
            return (isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant)
                    and node.slice.value == "checks")

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "subagent_checks":
                returned = next(item for item in ast.walk(node) if isinstance(item, ast.Return))
                declared.update(keyword.arg for keyword in returned.value.keywords)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "update" and is_checks(node.func.value):
                    declared.update(keyword.arg for keyword in node.keywords)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Subscript) and is_checks(target.value):
                        key = target.slice
                        if isinstance(key, ast.Constant):
                            declared.add(key.value)
                        else:
                            self.assertIsInstance(key, ast.JoinedStr)
                            self.assertIsInstance(key.values[0], ast.FormattedValue)
                            self.assertEqual(key.values[0].value.id, "label")
                            self.assertEqual(len(key.values), 2)
                            declared.update(label + key.values[1].value for label in ("alpha", "beta"))
        self.assertEqual(declared, observed | {"request_log_analyzed"})
        self.assertFalse(observed - self.classifications.keys(), "unclassified gating predicate")
        self.assertFalse(declared - self.classifications.keys(), "unclassified gating predicate")
        exact = sorted(key for key in declared if self.classifications[key] == "model_exact_text")
        self.assertEqual(exact, [], "pure exact-text predicates on model output must be compliance only")
        self.assertTrue(all(record["passed"] for record in records))

        # Enumerate every success-path gate under formatting-equivalent deliveries, not just a
        # hand-maintained name registry: repurposing an existing gate as a literal oracle fails too.
        for separator in (": ", " ", " = ", ":\n"):
            with self.subTest(separator=separator):
                outputs = [code.replace("=", separator) for code in scouts.codes]
                variant = scouts.subagents(outputs, answer="Reported:\n" + "\n".join(outputs))
                self.assertEqual(variant["checks"], records[0]["checks"])
                self.assertTrue(variant["passed"])
                for label, own in zip(("alpha", "beta"), sessions.codes):
                    variant = sessions.sessions("Reported:\n" + own.replace("=", separator),
                                                session=label)
                    self.assertEqual(variant["checks"], records[1]["checks"])
                    self.assertTrue(variant["passed"])

    def test_engine_gates_remain_fail_closed_for_both_scenarios(self):
        scouts, sessions = SubagentResultTests(), SessionRecallTests()
        analysis = scouts.subagents()
        keys = ("max_in_flight", "overlap_seconds", "request_count", "unmatched_starts",
                "server_instance_ids")
        baseline = {key: analysis[key] for key in keys}
        for change, gate in (
                ({"request_count": 1}, "logged_requests"),
                ({"unmatched_starts": 1}, "all_logged_requests_completed"),
                ({"server_instance_ids": ["one", "two"]}, "single_server_instance"),
                ({"max_in_flight": 3}, "provider_limit_respected"),
                ({"max_in_flight": 1, "overlap_seconds": 0}, "concurrency_expected"),
                ({"overlap_seconds": 0}, "concurrency_expected")):
            for scenario in ("subagents", "sessions"):
                with self.subTest(change=change, scenario=scenario), \
                     patch.object(proof, "analyze_requests", return_value={**baseline, **change}):
                    record = (scouts.subagents() if scenario == "subagents"
                              else sessions.sessions(sessions.codes[0]))
                    self.assertFalse(record["passed"])
                    self.assertFalse(record["checks"][gate])
        with patch.object(proof, "analyze_requests", side_effect=ValueError):
            for record in (scouts.subagents(), sessions.sessions(sessions.codes[0])):
                self.assertFalse(record["passed"])
                self.assertFalse(record["checks"]["request_log_analyzed"])


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
                         "omp": {"sha256": "90111c710fb861b03e5ef6fd3257319001acdd77ff7d06d3a6207996f2777709"},
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
