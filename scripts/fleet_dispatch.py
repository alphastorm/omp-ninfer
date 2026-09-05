#!/usr/bin/env python3
"""Fixed fleet workload: the frozen agent corpus dispatched across one, two, or three lanes.

The roadmap's fleet-routing claim is gated on a measured fixed workload. This runner takes the
public MTP-ablation corpus (7 scenarios x 2 repetitions = 14 independent jobs, 24 requests) and
dispatches the jobs across the named lanes with one worker per lane (one active request per
qualified profile), then records batch completion wall, per-lane completed work, and per-lane
output projections. Two policies:

  dynamic  every idle lane pulls the next job from one longest-first queue
  role     jobs are pinned by scenario class to the lane roles main / heavy / scout
  cost     longest-processing-time assignment from measured per-lane scenario costs
           (--cost-model: the lanes' solo receipts from this runner)

Receipts keep hashes and structural metrics only; the corpus is fully synthetic public text.
Outputs across lanes are not cross-comparable (each lane has its own KV format); repeatability is
checked per lane across run-level repetitions.

Example:
  python3 scripts/fleet_dispatch.py --policy dynamic --repetitions 2 \
    --lane main=http://127.0.0.1:18191=~/.omp/agent/ninfer-5090.key=q38-ninfer \
    --lane heavy=http://127.0.0.1:18192=~/.omp/agent/ninfer-4090.key=qwen3.8-27b \
    --lane scout=http://127.0.0.1:18193=~/.omp/agent/ninfer-3090.key=q38-ninfer \
    --receipt docs/measurements/2026-09-05-fleet-dispatch-three-lane-dynamic.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import queue
import sys
import threading
import time
import urllib.error
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_mtp_ablation import (  # noqa: E402
    CORPUS_STEP_NAMES,
    REPETITIONS,
    HttpClient,
    corpus_manifest,
    execute_scenario,
    scoped_identity,
)

ARM = 3  # every lane ships MTP3
# Longest-first queue order for the dynamic policy (measured per-scenario cost, largest first).
JOB_ORDER = (
    "responses_long_replay",
    "responses_medium_branch",
    "responses_long_decode",
    "chat_tool_roundtrip",
    "chat_history_p90",
    "chat_history_p50",
    "responses_short",
)
ROLE_OF_SCENARIO = {
    "responses_long_replay": "heavy",
    "responses_medium_branch": "main",
    "responses_long_decode": "main",
    "responses_short": "main",
    "chat_tool_roundtrip": "scout",
    "chat_history_p90": "scout",
    "chat_history_p50": "scout",
}
ROLE_FALLBACK = {"heavy": ("main",), "scout": ("main", "heavy"), "main": ("heavy", "scout")}
SCHEMA_VERSION = 1


class Lane:
    def __init__(self, name: str, base_url: str, api_key: str, model: str) -> None:
        self.name = name
        self.model = model
        self.client = HttpClient(base_url=base_url, api_key=api_key, timeout=1800.0)
        self.jobs: list[dict[str, Any]] = []
        self.busy_seconds = 0.0

    def checkpoint_delete(self, session: str) -> int:
        try:
            self.client.request("DELETE", "/v1/ninfer/checkpoints", {"session_sha256": session})
            return 200
        except urllib.error.HTTPError as error:
            return error.code
        except Exception:  # noqa: BLE001 - cleanup must never fail a measurement
            return -1


def parse_lane(spec: str) -> Lane:
    parts = spec.split("=")
    if len(parts) != 4:
        raise SystemExit(f"--lane expects NAME=BASE_URL=API_KEY_FILE=MODEL, got {spec!r}")
    name, base_url, key_file, model = parts
    if name not in ROLE_FALLBACK:
        raise SystemExit(f"lane name must be one of {sorted(ROLE_FALLBACK)}, got {name!r}")
    return Lane(name, base_url, Path(key_file).expanduser().read_text().strip(), model)


def build_jobs() -> list[tuple[str, int]]:
    jobs = [(name, repetition) for name in JOB_ORDER for repetition in range(REPETITIONS)]
    if {name for name, _ in jobs} != set(CORPUS_STEP_NAMES):
        raise AssertionError("job order drifted from the corpus scenario inventory")
    return jobs


def scenario_costs(receipts: list[Path]) -> dict[str, dict[str, float]]:
    """Mean measured wall per scenario for every lane in the given solo receipts."""
    costs: dict[str, dict[str, float]] = {}
    for path in receipts:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if receipt.get("artifact_type") != "omp_ninfer_fleet_dispatch" or len(receipt["lanes"]) != 1:
            raise SystemExit(f"{path} is not a single-lane fleet dispatch receipt")
        lane = next(iter(receipt["lanes"]))
        samples: dict[str, list[float]] = {}
        for run in receipt["runs"]:
            for job in run["jobs"]:
                if job["status"] == "complete":
                    samples.setdefault(job["scenario"], []).append(job["wall_s"])
        costs[lane] = {name: sum(values) / len(values) for name, values in samples.items()}
    return costs


def assign_cost(jobs: list[tuple[str, int]], lanes: dict[str, Lane],
                costs: dict[str, dict[str, float]]) -> dict[str, list[tuple[str, int]]]:
    """Longest-processing-time first on unrelated machines: each job, largest first by its
    cheapest cost, goes to the lane that finishes it earliest given that lane's current load."""
    missing = [name for name in lanes if name not in costs]
    if missing:
        raise SystemExit(f"cost model lacks lanes {missing}")
    order = sorted(jobs, key=lambda item: -min(costs[name][item[0]] for name in lanes))
    load = {name: 0.0 for name in lanes}
    plan: dict[str, list[tuple[str, int]]] = {name: [] for name in lanes}
    for scenario, repetition in order:
        best = min(lanes, key=lambda name: load[name] + costs[name][scenario])
        load[best] += costs[best][scenario]
        plan[best].append((scenario, repetition))
    return plan


def assign_role(scenario: str, lanes: dict[str, Lane]) -> Lane:
    role = ROLE_OF_SCENARIO[scenario]
    for candidate in (role, *ROLE_FALLBACK[role]):
        if candidate in lanes:
            return lanes[candidate]
    raise AssertionError("no lane available")


def run_job(lane: Lane, scenario: str, repetition: int, campaign_id: str,
            corpus_sha256: str, batch_started: float, cleanup: bool) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        steps = execute_scenario(
            lane.client, model=lane.model, lane=lane.name, arm=ARM, campaign_id=campaign_id,
            corpus_sha256=corpus_sha256, name=scenario, repetition=repetition,
        )
        status = "complete"
        error = None
    except Exception as exc:  # noqa: BLE001 - the receipt records the failure
        steps, status, error = [], "failed", f"{type(exc).__name__}: {exc}"[:300]
    finished = time.perf_counter()
    session = scoped_identity("session", campaign_id=campaign_id, corpus_sha256=corpus_sha256,
                              lane=lane.name, arm=ARM, suffix=f"{scenario}/r{repetition}")
    cleanup_status = lane.checkpoint_delete(session) if cleanup else None
    job = {
        "scenario": scenario,
        "repetition": repetition,
        "lane": lane.name,
        "status": status,
        "error": error,
        "started_offset_s": round(started - batch_started, 3),
        "wall_s": round(finished - started, 3),
        "requests": len(steps),
        "prompt_tokens": sum(step["prompt_tokens"] for step in steps),
        "completion_tokens": sum(step["completion_tokens"] for step in steps),
        "step_walls_s": {step["step_id"].rsplit("/", 1)[-1]: round(step["wall_seconds"], 3) for step in steps},
        "projection_sha256": {step["step_id"].rsplit("/", 1)[-1]: step["projection_sha256"] for step in steps},
        "checkpoint_delete_status": cleanup_status,
    }
    lane.jobs.append(job)
    lane.busy_seconds += finished - started
    return job


def run_batch(lanes: dict[str, Lane], policy: str, campaign_id: str, corpus_sha256: str,
              cleanup: bool, costs: dict[str, dict[str, float]] | None = None) -> dict[str, Any]:
    jobs = build_jobs()
    for lane in lanes.values():
        lane.jobs, lane.busy_seconds = [], 0.0
    batch_started = time.perf_counter()
    if policy == "dynamic":
        pending: queue.Queue[tuple[str, int]] = queue.Queue()
        for item in jobs:
            pending.put(item)

        def worker(lane: Lane) -> None:
            while True:
                try:
                    scenario, repetition = pending.get_nowait()
                except queue.Empty:
                    return
                run_job(lane, scenario, repetition, campaign_id, corpus_sha256, batch_started, cleanup)

        threads = [threading.Thread(target=worker, args=(lane,), name=lane.name) for lane in lanes.values()]
    else:
        if policy == "cost":
            plan = assign_cost(jobs, lanes, costs or {})
        else:
            plan = {name: [] for name in lanes}
            for scenario, repetition in jobs:
                plan[assign_role(scenario, lanes).name].append((scenario, repetition))

        def role_worker(lane: Lane) -> None:
            for scenario, repetition in plan[lane.name]:
                run_job(lane, scenario, repetition, campaign_id, corpus_sha256, batch_started, cleanup)

        threads = [threading.Thread(target=role_worker, args=(lane,), name=lane.name) for lane in lanes.values()]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    batch_wall = time.perf_counter() - batch_started
    per_lane = {}
    for lane in lanes.values():
        per_lane[lane.name] = {
            "jobs": len(lane.jobs),
            "requests": sum(job["requests"] for job in lane.jobs),
            "prompt_tokens": sum(job["prompt_tokens"] for job in lane.jobs),
            "completion_tokens": sum(job["completion_tokens"] for job in lane.jobs),
            "busy_s": round(lane.busy_seconds, 3),
            "utilization": round(lane.busy_seconds / batch_wall, 3) if batch_wall else None,
            "failed_jobs": sum(1 for job in lane.jobs if job["status"] != "complete"),
        }
    all_jobs = sorted((job for lane in lanes.values() for job in lane.jobs),
                      key=lambda job: job["started_offset_s"])
    return {
        "policy": policy,
        "batch_wall_s": round(batch_wall, 3),
        "jobs_completed": sum(1 for job in all_jobs if job["status"] == "complete"),
        "jobs_total": len(jobs),
        "requests_total": sum(job["requests"] for job in all_jobs),
        "prompt_tokens_total": sum(job["prompt_tokens"] for job in all_jobs),
        "completion_tokens_total": sum(job["completion_tokens"] for job in all_jobs),
        "per_lane": per_lane,
        "jobs": all_jobs,
    }


def per_lane_projections(batch: dict[str, Any]) -> dict[str, dict[str, str]]:
    projections: dict[str, dict[str, str]] = {}
    for job in batch["jobs"]:
        for step, digest in job["projection_sha256"].items():
            projections.setdefault(job["lane"], {})[f"{job['scenario']}/{step}"] = digest
    return projections


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lane", action="append", required=True, help="NAME=BASE_URL=API_KEY_FILE=MODEL; NAME in main/heavy/scout")
    parser.add_argument("--policy", choices=("dynamic", "role", "cost"), default="dynamic")
    parser.add_argument("--cost-model", action="append", type=Path, default=[],
                        help="single-lane receipts from this runner supplying per-scenario costs (policy cost)")
    parser.add_argument("--repetitions", type=int, default=2, help="run-level repetitions of the whole batch")
    parser.add_argument("--campaign-id", default=None)
    parser.add_argument("--no-cleanup", action="store_true", help="leave session checkpoints on the lanes")
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    lanes = {lane.name: lane for lane in (parse_lane(spec) for spec in args.lane)}
    if len(lanes) != len(args.lane):
        raise SystemExit("lane names must be unique")
    manifest = corpus_manifest()
    costs = scenario_costs(args.cost_model) if args.policy == "cost" else None
    if args.policy == "cost" and not costs:
        raise SystemExit("--policy cost requires --cost-model receipts")
    generated = dt.datetime.now(dt.UTC)
    campaign_id = args.campaign_id or hashlib.sha256(
        f"fleet-dispatch/{generated.isoformat()}/{'+'.join(sorted(lanes))}/{args.policy}".encode()).hexdigest()
    batches = []
    for repetition in range(args.repetitions):
        batch = run_batch(lanes, args.policy, f"{campaign_id}/run{repetition}", manifest["sha256"], not args.no_cleanup, costs)
        batch["run"] = repetition
        batches.append(batch)
        print(f"run {repetition}: {batch['policy']} lanes={sorted(lanes)} wall={batch['batch_wall_s']} s "
              f"completed={batch['jobs_completed']}/{batch['jobs_total']} "
              + " ".join(f"{name}:{lane['jobs']}j/{lane['busy_s']}s" for name, lane in batch['per_lane'].items()),
              flush=True)
    projections = [per_lane_projections(batch) for batch in batches]
    repeatability = {}
    for name in lanes:
        keys = set().union(*(set(p.get(name, {})) for p in projections))
        mismatches = sorted(k for k in keys if len({p.get(name, {}).get(k) for p in projections}) != 1)
        repeatability[name] = {"steps_compared": len(keys), "mismatched_steps": mismatches}
    receipt = {
        "artifact_type": "omp_ninfer_fleet_dispatch",
        "schema_version": SCHEMA_VERSION,
        "generated_utc": generated.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "campaign_id": campaign_id,
        "corpus_sha256": manifest["sha256"],
        "corpus_version": manifest["version"],
        "policy": args.policy,
        "lanes": {name: {"model": lane.model, "identity": lane.client.request("GET", "/v1/ninfer/status").get("identity", {})} for name, lane in lanes.items()},
        "job_order": list(JOB_ORDER),
        "role_of_scenario": ROLE_OF_SCENARIO if args.policy == "role" else None,
        "cost_model": ({"receipts": [str(p) for p in args.cost_model],
                        "costs_s": {lane: {k: round(v, 3) for k, v in per.items()} for lane, per in costs.items()},
                        "assignment": {lane: [f"{s}/r{r}" for s, r in plan] for lane, plan in assign_cost(build_jobs(), lanes, costs).items()}}
                       if costs else None),
        "summary": {
            "batch_walls_s": [batch["batch_wall_s"] for batch in batches],
            "batch_wall_min_s": min(batch["batch_wall_s"] for batch in batches),
            "jobs_total": batches[0]["jobs_total"],
            "all_jobs_completed": all(batch["jobs_completed"] == batch["jobs_total"] for batch in batches),
            "per_lane_jobs": {name: [batch["per_lane"][name]["jobs"] for batch in batches] for name in lanes},
            "per_lane_utilization": {name: [batch["per_lane"][name]["utilization"] for batch in batches] for name in lanes},
        },
        "repeatability": repeatability,
        "runs": batches,
        "privacy": "fully synthetic public corpus; hashes and structural metrics only; lane identities are the served status identities",
    }
    for lane_identity in receipt["lanes"].values():
        lane_identity["identity"] = {k: v for k, v in lane_identity["identity"].items()
                                     if k in ("deployment_profile", "binary_sha256", "config_sha256", "model_artifact_sha256", "patch_stack_sha")}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"receipt written: {args.receipt}", flush=True)
    return 0 if receipt["summary"]["all_jobs_completed"] else 1


if __name__ == "__main__":
    sys.exit(main())
