#!/usr/bin/env python3
"""Fleet prefix-locality probe: base -> warm edit -> fanout -> restart -> resume.

Measures the exact pattern the template-fork roadmap bets on, against a live lane,
as an ordinary client session (no server mutation): one large base turn, a warm
continuation, an explicit checkpoint, N branches from the base response id, an
optional process restart, and a post-restart resume. Every step records wall time;
server-side reuse classes are joined from the lane's request JSONL when a
``--log-cmd`` is given (a shell command printing recent request-log lines).

The receipt is public-safe by construction: synthetic prompt content, lane labels
instead of hostnames, no key material.

Example:
  python3 scripts/fleet_probe.py --lane main-5090 \
    --base-url http://127.0.0.1:18191 --api-key-file ~/.omp/agent/ninfer-5090.key \
    --base-tokens 56000 --branches 4 \
    --restart-cmd 'ssh qwen-5090 "docker restart --time 30 ninfer-5090"' \
    --log-cmd 'ssh qwen-5090 "wsl -d Ubuntu-24.04 -e bash -c \"cat /home/sunil/services/ninfer-5090/logs/requests-*.jsonl\""' \
    --receipt docs/measurements/$(date +%F)-fanout-probe-main.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def now() -> float:
    return time.monotonic()


class Lane:
    def __init__(self, base_url: str, api_key: str, session: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = session
        self.model = model

    def _request(self, path: str, payload: dict[str, Any] | None, timeout: float) -> Any:
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())

    def respond(self, text_or_items: Any, previous: str | None, max_output: int,
                timeout: float = 1800.0) -> tuple[dict[str, Any], float]:
        payload: dict[str, Any] = {
            "model": self.model,
            "input": text_or_items,
            "store": True,
            "temperature": 0,
            "max_output_tokens": max_output,
            "ninfer_session": self.session,
        }
        if previous is not None:
            payload["previous_response_id"] = previous
        started = now()
        document = self._request("/v1/responses", payload, timeout)
        return document, now() - started

    def checkpoint_save(self, timeout: float = 900.0) -> tuple[dict[str, Any], float]:
        started = now()
        document = self._request(
            "/v1/ninfer/checkpoints", {"session_sha256": self.session}, timeout)
        return document, now() - started

    def status(self, timeout: float = 60.0) -> dict[str, Any]:
        return self._request("/v1/ninfer/status", None, timeout)


def wait_ready(lane: Lane, deadline_seconds: float) -> float:
    started = now()
    while now() - started < deadline_seconds:
        try:
            lane.status(timeout=10.0)
            return now() - started
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            time.sleep(3.0)
    raise TimeoutError("lane did not become ready after restart")


def reuse_classes(log_cmd: str, since_unix_ms: int) -> list[dict[str, Any]]:
    """Best-effort join: request_done records at/after the probe start."""
    result = subprocess.run(log_cmd, shell=True, capture_output=True, text=True, timeout=120)
    records: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("event") != "request_done":
            continue
        if int(record.get("timestamp_unix_ms", 0)) < since_unix_ms:
            continue
        outcome = record.get("result", {}) or {}
        timings = record.get("timings_seconds", {}) or {}
        records.append({
            "reuse": outcome.get("prefix_reuse_path"),
            "reused_tokens": outcome.get("prefix_cache_hit_tokens"),
            "prompt_tokens": outcome.get("prompt_tokens"),
            "completion_tokens": outcome.get("completion_tokens"),
            "ttft_s": timings.get("ttft"),
        })
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", required=True, help="public lane label for the receipt")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key-file", required=True, type=Path)
    parser.add_argument("--model", default="q38-ninfer")
    parser.add_argument("--base-tokens", type=int, default=56000,
                        help="approximate synthetic base size in tokens")
    parser.add_argument("--branches", type=int, default=4)
    parser.add_argument("--restart-cmd", help="optional shell command restarting the lane")
    parser.add_argument("--log-cmd", help="optional shell command printing request JSONL lines")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()

    api_key = args.api_key_file.read_text().strip()
    session = hashlib.sha256(
        f"fleet-probe-{args.lane}-{dt.datetime.now(dt.UTC).isoformat()}".encode()).hexdigest()
    lane = Lane(args.base_url, api_key, session, args.model)
    probe_started_ms = int(time.time() * 1000)

    steps: list[dict[str, Any]] = []

    def record(step: str, wall: float, extra: dict[str, Any] | None = None) -> None:
        entry: dict[str, Any] = {"step": step, "wall_s": round(wall, 3)}
        if extra:
            entry.update(extra)
        steps.append(entry)
        print(f"{step:>24}: {wall:7.2f} s  {json.dumps(extra or {}, default=str)[:120]}",
              flush=True)

    # Slice 1: large base + warm edit.
    filler = "Operations ledger entry %d: throughput nominal, cache warm, retrieval verified. "
    words_per_entry = 11
    entries = max(1, (args.base_tokens * 3 // 4) // words_per_entry)
    corpus = "".join(filler % index for index in range(entries))
    base_doc, base_wall = lane.respond(
        [{"role": "user", "content": [{"type": "input_text",
          "text": "Hold this operations ledger in context for later analysis; reply OK only.\n"
                  + corpus}]}],
        previous=None, max_output=40)
    base_id = base_doc["id"]
    record("base_prefill", base_wall,
           {"input_tokens": base_doc.get("usage", {}).get("input_tokens"), "id": base_id})

    edit_doc, edit_wall = lane.respond(
        "Summarize entry 3 in six words.", previous=base_id, max_output=80)
    record("warm_edit", edit_wall, {"id": edit_doc["id"]})

    save_doc, save_wall = lane.checkpoint_save()
    record("checkpoint_save", save_wall,
           {"generation": save_doc.get("generation"), "bytes": save_doc.get("bytes"),
            "frontier": save_doc.get("frontier_tokens")})

    # Slice 2: fanout from the base id.
    branch_ids: list[str] = []
    for index in range(args.branches):
        branch_doc, branch_wall = lane.respond(
            f"Branch role {index}: summarize entry {index + 5} in six words.",
            previous=base_id, max_output=80)
        branch_ids.append(branch_doc["id"])
        record(f"branch_{index}", branch_wall, {"id": branch_doc["id"]})

    # Slice 8: restart + resume.
    if args.restart_cmd:
        started = now()
        subprocess.run(args.restart_cmd, shell=True, check=True,
                       capture_output=True, timeout=600)
        ready_wall = wait_ready(lane, 600.0)
        record("restart", now() - started, {"ready_after_s": round(ready_wall, 2)})

        resume_doc, resume_wall = lane.respond(
            "After the restart, summarize entry 9 in six words.",
            previous=branch_ids[-1] if branch_ids else base_id, max_output=80)
        record("post_restart_resume", resume_wall, {"id": resume_doc["id"]})

        save2_doc, save2_wall = lane.checkpoint_save()
        record("post_restart_save", save2_wall,
               {"generation": save2_doc.get("generation"),
                "frontier": save2_doc.get("frontier_tokens")})

    server_side: list[dict[str, Any]] = []
    if args.log_cmd:
        try:
            server_side = reuse_classes(args.log_cmd, probe_started_ms)
        except Exception as error:  # noqa: BLE001 - best-effort join
            print(f"log join failed: {error}", file=sys.stderr)

    receipt = {
        "artifact_type": "omp_ninfer_fleet_fanout_probe",
        "schema_version": 1,
        "lane": args.lane,
        "generated_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base_tokens_requested": args.base_tokens,
        "branches": args.branches,
        "steps": steps,
        "server_reuse_records": server_side,
    }
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(f"receipt written: {args.receipt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
