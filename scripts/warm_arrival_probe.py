#!/usr/bin/env python3
"""Warm-arrival probe: template -> fork -> save -> restart -> {resume, fork} in both orders.

Measures whether a restored template serves its first sibling fork hot after a process
restart, for both request orders the roadmap's fanout pattern produces: an endpoint resume
arriving first (the common OMP shape: the parent continues, then spawns) and a fork arriving
first. Every request records client wall time and the lane's server-reported reuse decision
(``cache.last_selection`` from ``GET /v1/ninfer/status``), so a re-prefill shows up as reuse
path ``root`` with zero reused tokens rather than as a timing guess. The template carries
three planted ledger keys; every restored continuation must quote them exactly, which ties
the reuse decision to a correct restore rather than a fast one.

Each order runs as its own session with its own verified restart, so the two receipts are
independent. ``--restore-status`` additionally polls the checkpoint status endpoint during
the first post-restart request to time the lazy restore itself.

Example:
  python3 scripts/warm_arrival_probe.py --lane rtx5090-candidate \
    --base-url http://127.0.0.1:18099 --api-key-file ~/.omp/agent/ninfer-5090.key \
    --base-tokens 56000 --order both \
    --restart-cmd 'ssh nyc-pc-wsl "docker restart --time 90 ninfer-5090-warm"' \
    --receipt docs/measurements/$(date +%F)-warm-arrival-rtx5090.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import threading
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fleet_probe import Lane, now  # noqa: E402
from restore_probe import plant_keys, retrieval_prompt, retrieval_result, verified_restart  # noqa: E402

ORDERS = ("resume-first", "fork-first")


def cache_snapshot(lane: Lane) -> dict[str, Any]:
    cache = lane.status().get("cache", {})
    return {
        "last_selection": cache.get("last_selection"),
        "reused_prompt_tokens": cache.get("reused_prompt_tokens"),
        "private_catalog": cache.get("private_catalog"),
        "device_state": cache.get("device_state"),
        "host_state": cache.get("host_state"),
        "host_kv": cache.get("host_kv"),
    }


def build_template(base_tokens: int, keys: dict[str, str]) -> str:
    filler = "Operations ledger entry %d: throughput nominal, cache warm, retrieval verified. "
    entries = [filler % index for index in range(max(3, (base_tokens * 3 // 4) // 11))]
    for name, position in zip(keys, (0.05, 0.5, 0.95)):
        index = min(len(entries) - 1, int(len(entries) * position))
        entries[index] += f"Ledger key {name}={keys[name]}. "
    return "".join(entries)


class Run:
    """One order: a fresh session, a restart, and the post-restart request sequence."""

    def __init__(self, lane: Lane, keys: dict[str, str], restore_status: bool) -> None:
        self.lane = lane
        self.keys = keys
        self.restore_status = restore_status
        self.steps: list[dict[str, Any]] = []
        self.reused_before = 0

    def record(self, step: str, payload: dict[str, Any]) -> None:
        self.steps.append({"step": step, **payload})
        print(f"{step:>26}: {json.dumps(payload, default=str)[:150]}", flush=True)

    def request(self, step: str, text: Any, previous: str | None, max_output: int,
                expect_keys: bool = False, poll_restore: bool = False) -> str:
        polls: list[dict[str, Any]] = []
        stop = threading.Event()

        def poll() -> None:
            last: dict[str, Any] | None = None
            started = now()
            while not stop.is_set():
                try:
                    status = self.lane.checkpoint_status(timeout=30.0)
                except Exception as error:  # noqa: BLE001 - the poll is diagnostic
                    status = {"error": repr(error)}
                snapshot = {k: v for k, v in status.items() if k != "artifact_type"}
                if snapshot != last:
                    polls.append({"t_s": round(now() - started, 2), **snapshot})
                    last = snapshot
                stop.wait(0.5)

        thread = None
        if poll_restore:
            thread = threading.Thread(target=poll, daemon=True)
            thread.start()
        document, wall = self.lane.respond(text, previous=previous, max_output=max_output)
        if thread is not None:
            stop.set()
            thread.join(timeout=5.0)
        snapshot = cache_snapshot(self.lane)
        reused_now = int(snapshot.get("reused_prompt_tokens") or 0)
        payload: dict[str, Any] = {
            "wall_s": round(wall, 3),
            "id": document["id"],
            "input_tokens": document.get("usage", {}).get("input_tokens"),
            "reuse_path": (snapshot.get("last_selection") or {}).get("path"),
            "reuse_frontier": (snapshot.get("last_selection") or {}).get("frontier_tokens"),
            "reused_tokens": reused_now - self.reused_before,
            "cache": snapshot,
        }
        self.reused_before = reused_now
        if expect_keys:
            payload.update(retrieval_result(self.keys, document))
        if polls:
            payload["restore_status_polls"] = polls
        self.record(step, payload)
        return document["id"]

    def save(self, step: str, expected_records: int) -> None:
        document, wall = self.lane.checkpoint_save(expected_records)
        self.record(step, {"wall_s": round(wall, 3), "mode": document.get("mode"),
                           "generation": document.get("generation"),
                           "bytes": document.get("bytes"),
                           "frontier": document.get("frontier_tokens"),
                           "response_records": document.get("response_records")})

    def execute(self, order: str, template: str, restart_cmd: str) -> None:
        base_id = self.request(
            "base_prefill",
            [{"role": "user", "content": [{"type": "input_text",
              "text": "Hold this operations ledger in context for later analysis; reply OK only.\n"
                      + template}]}],
            previous=None, max_output=40)
        fork_id = self.request("pre_restart_fork",
                               "Branch role 0: summarize entry 5 in six words.",
                               previous=base_id, max_output=80)
        self.save("save", 2)
        self.record("cache_before_restart", cache_snapshot(self.lane))
        self.record("restart", verified_restart(self.lane, restart_cmd))
        self.reused_before = 0
        self.record("cache_after_restart", cache_snapshot(self.lane))
        if order == "resume-first":
            self.request("endpoint_resume_first", retrieval_prompt(self.keys, "Resume"),
                         previous=fork_id, max_output=256, expect_keys=True,
                         poll_restore=self.restore_status)
            self.request("fork_after_resume",
                         "Branch role 1: summarize entry 6 in six words.",
                         previous=base_id, max_output=80)
            self.request("fork_second",
                         "Branch role 2: summarize entry 7 in six words.",
                         previous=base_id, max_output=80)
        else:
            self.request("fork_first",
                         "Branch role 1: summarize entry 6 in six words.",
                         previous=base_id, max_output=80,
                         poll_restore=self.restore_status)
            self.request("endpoint_resume_after_fork", retrieval_prompt(self.keys, "Resume"),
                         previous=fork_id, max_output=256, expect_keys=True)
            self.request("fork_after_resume",
                         "Branch role 2: summarize entry 7 in six words.",
                         previous=base_id, max_output=80)
        self.record("session_delete", {"status": self.lane.checkpoint_delete()})


def summarize(order: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    by_step = {entry["step"]: entry for entry in steps}
    post = [entry for entry in steps
            if entry["step"] in ("endpoint_resume_first", "fork_after_resume", "fork_second",
                                 "fork_first", "endpoint_resume_after_fork")]
    forks = [entry for entry in post if entry["step"].startswith("fork")]
    resumes = [entry for entry in post if entry["step"].startswith("endpoint_resume")]
    return {
        "order": order,
        "template_input_tokens": by_step["base_prefill"].get("input_tokens"),
        "cold_prefill_s": by_step["base_prefill"]["wall_s"],
        "pre_restart_fork": [by_step["pre_restart_fork"]["reuse_path"],
                             by_step["pre_restart_fork"]["wall_s"]],
        "checkpoint_bytes": by_step["save"].get("bytes"),
        "post_restart_sequence": [[entry["step"], entry["reuse_path"], entry["reuse_frontier"],
                                   entry["wall_s"]] for entry in post],
        "every_post_restart_fork_hot": bool(forks) and all(
            entry["reuse_path"] == "private_long_anchor" for entry in forks),
        "restored_retrieval_exact": all(entry.get("exact") for entry in resumes),
        "restore_plus_sequence_s": round(sum(entry["wall_s"] for entry in post), 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key-file", required=True, type=Path)
    parser.add_argument("--model", default="q38-ninfer")
    parser.add_argument("--base-tokens", type=int, default=56000)
    parser.add_argument("--order", choices=(*ORDERS, "both"), default="both")
    parser.add_argument("--restart-cmd", required=True)
    parser.add_argument("--restore-status", action="store_true",
                        help="poll the checkpoint status endpoint during the lazy restore")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()

    api_key = args.api_key_file.read_text().strip()
    orders = list(ORDERS) if args.order == "both" else [args.order]
    runs: dict[str, Any] = {}
    summaries: list[dict[str, Any]] = []
    for order in orders:
        session = hashlib.sha256(
            f"warm-arrival-{args.lane}-{order}-{dt.datetime.now(dt.UTC).isoformat()}".encode()
        ).hexdigest()
        lane = Lane(args.base_url, api_key, session, args.model)
        keys = plant_keys()
        run = Run(lane, keys, args.restore_status)
        print(f"== order {order}", flush=True)
        run.execute(order, build_template(args.base_tokens, keys), args.restart_cmd)
        runs[order] = {"steps": run.steps, "transient_retries": lane.retries}
        summaries.append(summarize(order, run.steps))

    receipt = {
        "artifact_type": "omp_ninfer_warm_arrival_probe",
        "schema_version": 2,
        "lane": args.lane,
        "generated_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base_tokens_requested": args.base_tokens,
        "summary": summaries,
        "runs": runs,
    }
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(f"receipt written: {args.receipt}")
    print(json.dumps(summaries, indent=2))
    hot = all(entry["every_post_restart_fork_hot"] for entry in summaries)
    exact = all(entry["restored_retrieval_exact"] for entry in summaries)
    if not exact:
        print("FAILED: a restored continuation did not quote the planted keys", flush=True)
        return 1
    return 0 if hot else 3


if __name__ == "__main__":
    sys.exit(main())
