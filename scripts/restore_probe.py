#!/usr/bin/env python3
"""Checkpoint restore probe: template -> save -> restart -> restore, twice.

Diagnoses why a lane's post-restart restore is slower than re-prefilling the same
template. One stored template (the checkpointed generation) is restored across two
verified restarts: a first-read effect (page cache, on-access scanning of freshly
written files) shows up as a fast second restore, a slow restore path shows up twice.
While each restore runs, ``GET /v1/ninfer/checkpoints/status`` is polled so the
receipt carries the store's state transitions with timestamps.

Example:
  python3 scripts/restore_probe.py --lane rtx4090 --base-url http://127.0.0.1:18192 \
    --api-key-file ~/.omp/agent/ninfer-4090.key --model qwen3.8-27b --base-tokens 48000 \
    --restart-cmd '<verified lane restart command>' \
    --receipt docs/measurements/$(date +%F)-restore-probe-rtx4090.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fleet_probe import Lane, now, wait_ready  # noqa: E402


def verified_restart(lane: Lane, command: str) -> dict[str, Any]:
    before = lane.status().get("scheduler", {}).get("computed_prefill_tokens")
    started = now()
    subprocess.run(command, shell=True, check=True, capture_output=True, timeout=600)
    ready = wait_ready(lane, 600.0)
    after = lane.status().get("scheduler", {}).get("computed_prefill_tokens")
    if before is not None and after is not None and after >= before:
        raise RuntimeError("restart command returned but the lane's counters did not reset")
    return {"wall_s": round(now() - started, 3), "ready_after_s": round(ready, 2),
            "prefill_counter_before": before, "prefill_counter_after": after}


def timed_restore(lane: Lane, previous: str, prompt: str) -> dict[str, Any]:
    polls: list[dict[str, Any]] = []
    stop = threading.Event()

    def poll() -> None:
        last: dict[str, Any] | None = None
        started = now()
        while not stop.is_set():
            try:
                status = lane.checkpoint_status(timeout=30.0)
            except Exception as error:  # noqa: BLE001 - the poll is diagnostic
                status = {"error": repr(error)}
            snapshot = {k: v for k, v in status.items() if k != "artifact_type"}
            if snapshot != last:
                polls.append({"t_s": round(now() - started, 2), **snapshot})
                last = snapshot
            stop.wait(1.0)

    thread = threading.Thread(target=poll, daemon=True)
    thread.start()
    started = now()
    document, wall = lane.respond(prompt, previous=previous, max_output=80)
    stop.set()
    thread.join(timeout=5.0)
    return {"wall_s": round(wall, 3), "id": document["id"],
            "input_tokens": document.get("usage", {}).get("input_tokens"),
            "status_polls": polls, "started_utc": dt.datetime.fromtimestamp(
                time.time() - (now() - started), dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key-file", required=True, type=Path)
    parser.add_argument("--model", default="q38-ninfer")
    parser.add_argument("--base-tokens", type=int, default=48000)
    parser.add_argument("--restart-cmd", required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()

    api_key = args.api_key_file.read_text().strip()
    session = hashlib.sha256(
        f"restore-probe-{args.lane}-{dt.datetime.now(dt.UTC).isoformat()}".encode()).hexdigest()
    lane = Lane(args.base_url, api_key, session, args.model)
    steps: list[dict[str, Any]] = []

    def record(step: str, payload: dict[str, Any]) -> None:
        steps.append({"step": step, **payload})
        print(f"{step:>22}: {json.dumps(payload, default=str)[:160]}", flush=True)

    filler = "Operations ledger entry %d: throughput nominal, cache warm, retrieval verified. "
    corpus = "".join(filler % index for index in range(max(1, (args.base_tokens * 3 // 4) // 11)))
    base_doc, base_wall = lane.respond(
        [{"role": "user", "content": [{"type": "input_text",
          "text": "Hold this operations ledger in context for later analysis; reply OK only.\n"
                  + corpus}]}], previous=None, max_output=40)
    record("base_prefill", {"wall_s": round(base_wall, 3),
                            "input_tokens": base_doc.get("usage", {}).get("input_tokens")})
    save_doc, save_wall = lane.checkpoint_save(1)
    record("checkpoint_save", {"wall_s": round(save_wall, 3), "mode": save_doc.get("mode"),
                               "generation": save_doc.get("generation"),
                               "bytes": save_doc.get("bytes"),
                               "frontier": save_doc.get("frontier_tokens")})

    previous = base_doc["id"]
    for round_index in range(2):
        record(f"restart_{round_index}", verified_restart(lane, args.restart_cmd))
        restore = timed_restore(lane, previous, f"Restore round {round_index}: summarize entry "
                                                f"{round_index + 3} in six words.")
        record(f"restore_{round_index}", restore)
        # Only the continuation of the newest stored response restores on the native lanes
        # (a fork from an older response re-prefills), so each round continues the lineage
        # and the settle save covers it for the next restart.
        previous = restore["id"]
        settle_doc, settle_wall = lane.checkpoint_save(2 + round_index)
        record(f"settle_save_{round_index}", {"wall_s": round(settle_wall, 3),
                                              "mode": settle_doc.get("mode"),
                                              "generation": settle_doc.get("generation")})

    delete_status = lane.checkpoint_delete()
    record("session_delete", {"status": delete_status})

    by_step = {entry["step"]: entry for entry in steps}
    receipt = {
        "artifact_type": "omp_ninfer_restore_probe",
        "schema_version": 1,
        "lane": args.lane,
        "generated_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base_tokens_requested": args.base_tokens,
        "summary": {
            "template_input_tokens": by_step["base_prefill"].get("input_tokens"),
            "cold_prefill_s": by_step["base_prefill"]["wall_s"],
            "checkpoint_bytes": by_step["checkpoint_save"].get("bytes"),
            "restore_0_wall_s": by_step["restore_0"]["wall_s"],
            "restore_1_wall_s": by_step["restore_1"]["wall_s"],
        },
        "steps": steps,
        "transient_retries": lane.retries,
    }
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(f"receipt written: {args.receipt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
