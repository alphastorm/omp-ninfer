"""Fleet dispatch policies and receipt shape, without any network."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("fleet_dispatch", ROOT / "scripts" / "fleet_dispatch.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def fake_execute(client, *, model, lane, arm, campaign_id, corpus_sha256, name, repetition):
    steps = MODULE.CORPUS_STEP_NAMES[name]
    return [
        {
            "step_id": f"{name}/r{repetition}/{step}",
            "protocol": "openai_responses",
            "prompt_tokens": 100,
            "completion_tokens": 10,
            "wall_seconds": 0.001,
            "projection_sha256": f"{lane}-{name}-{step}",
        }
        for step in steps
    ]


class FakeClient:
    def request(self, method, path, payload=None):
        return {"identity": {"deployment_profile": "fake"}}


def make_lane(name: str) -> "MODULE.Lane":
    lane = MODULE.Lane.__new__(MODULE.Lane)
    lane.name, lane.model, lane.client, lane.jobs, lane.busy_seconds = name, "m", FakeClient(), [], 0.0
    return lane


class FleetDispatchTests(unittest.TestCase):
    def test_job_order_covers_the_frozen_corpus_twice(self) -> None:
        jobs = MODULE.build_jobs()
        self.assertEqual(len(jobs), len(MODULE.CORPUS_STEP_NAMES) * MODULE.REPETITIONS)
        self.assertEqual({name for name, _ in jobs}, set(MODULE.CORPUS_STEP_NAMES))
        self.assertEqual(jobs[0][0], "responses_long_replay")

    def test_role_policy_pins_by_scenario_and_falls_back(self) -> None:
        three = {n: make_lane(n) for n in ("main", "heavy", "scout")}
        self.assertEqual(MODULE.assign_role("responses_long_replay", three).name, "heavy")
        self.assertEqual(MODULE.assign_role("chat_history_p50", three).name, "scout")
        two = {n: make_lane(n) for n in ("main", "heavy")}
        self.assertEqual(MODULE.assign_role("chat_history_p50", two).name, "main")
        one = {"main": make_lane("main")}
        self.assertEqual(MODULE.assign_role("responses_long_replay", one).name, "main")
        self.assertEqual(set(MODULE.ROLE_OF_SCENARIO), set(MODULE.CORPUS_STEP_NAMES))

    def test_dynamic_batch_completes_every_job_once_and_records_lanes(self) -> None:
        lanes = {n: make_lane(n) for n in ("main", "heavy")}
        with mock.patch.object(MODULE, "execute_scenario", fake_execute):
            batch = MODULE.run_batch(lanes, "dynamic", "c/run0", "corpus", cleanup=False)
        self.assertEqual(batch["jobs_completed"], batch["jobs_total"])
        self.assertEqual(sum(v["jobs"] for v in batch["per_lane"].values()), batch["jobs_total"])
        keys = sorted((job["scenario"], job["repetition"]) for job in batch["jobs"])
        self.assertEqual(keys, sorted(MODULE.build_jobs()))
        self.assertEqual(batch["requests_total"], sum(len(s) for s in MODULE.CORPUS_STEP_NAMES.values()) * MODULE.REPETITIONS)

    def test_role_batch_places_every_job_on_its_role_lane(self) -> None:
        lanes = {n: make_lane(n) for n in ("main", "heavy", "scout")}
        with mock.patch.object(MODULE, "execute_scenario", fake_execute):
            batch = MODULE.run_batch(lanes, "role", "c/run0", "corpus", cleanup=False)
        for job in batch["jobs"]:
            self.assertEqual(job["lane"], MODULE.ROLE_OF_SCENARIO[job["scenario"]])
        projections = MODULE.per_lane_projections(batch)
        self.assertIn("responses_long_replay/base", projections["heavy"])

    def test_failed_job_is_recorded_not_raised(self) -> None:
        lanes = {"main": make_lane("main")}

        def boom(*args, **kwargs):
            raise RuntimeError("lane down")

        with mock.patch.object(MODULE, "execute_scenario", boom):
            batch = MODULE.run_batch(lanes, "dynamic", "c/run0", "corpus", cleanup=False)
        self.assertEqual(batch["jobs_completed"], 0)
        self.assertTrue(all(job["status"] == "failed" for job in batch["jobs"]))


if __name__ == "__main__":
    unittest.main()


class FleetCostPolicyTests(unittest.TestCase):
    def test_cost_assignment_sends_expensive_prefill_jobs_to_the_fast_lane(self) -> None:
        lanes = {n: make_lane(n) for n in ("main", "heavy")}
        costs = {
            "main": {s: (15.0 if s == "responses_long_replay" else 1.0) for s in MODULE.CORPUS_STEP_NAMES},
            "heavy": {s: (48.0 if s == "responses_long_replay" else 1.0) for s in MODULE.CORPUS_STEP_NAMES},
        }
        plan = MODULE.assign_cost(MODULE.build_jobs(), lanes, costs)
        self.assertEqual({s for s, _ in plan["main"] if s == "responses_long_replay"}, {"responses_long_replay"})
        self.assertEqual(sum(1 for s, _ in plan["heavy"] if s == "responses_long_replay"), 0)
        self.assertEqual(sum(len(v) for v in plan.values()), len(MODULE.build_jobs()))
        with mock.patch.object(MODULE, "execute_scenario", fake_execute):
            batch = MODULE.run_batch(lanes, "cost", "c/run0", "corpus", cleanup=False, costs=costs)
        self.assertEqual(batch["jobs_completed"], batch["jobs_total"])

    def test_cost_policy_refuses_a_lane_without_costs(self) -> None:
        lanes = {n: make_lane(n) for n in ("main", "scout")}
        with self.assertRaises(SystemExit):
            MODULE.assign_cost(MODULE.build_jobs(), lanes, {"main": {s: 1.0 for s in MODULE.CORPUS_STEP_NAMES}})
