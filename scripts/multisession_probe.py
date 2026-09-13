#!/usr/bin/env python3
"""Multi-session pressure probe: does a continuation lose its prefix reuse when several large
sessions are resident?

Reproduces the shape of upstream Neroued/ninfer#229 as an ordinary client: N large sessions are
created back to back (each new one displaces the previous from device state), then continuations
and forks are issued round-robin, each immediately after the previous turn completes - the moment
the materialization planner's bounded pressure search runs against the fullest candidate set. A
continuation whose prompt is a byte-identical extension of its own session must reuse; one that
comes back with zero reused tokens and a cold-prefill TTFT is the root re-prefill fallback the
issue describes. The server's ``pressure_search_budget_exhaustions`` counter is read before and
after so an exhaustion that did not cost reuse is still visible.

Example:
  python3 scripts/multisession_probe.py --lane rtx5090-v063 --base-url http://127.0.0.1:18189 \
    --api-key-file ~/.omp/agent/ninfer-5090.key --sessions 3 --base-tokens 100000 --rounds 2 \
    --log-cmd "ssh nyc-pc-wsl cat /home/sunil/.local/state/omp-ninfer/requests-*.jsonl" \
    --receipt docs/measurements/$(date +%F)-multisession-probe-rtx5090.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import time
import urllib.error
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fleet_probe import Lane, lane_identity, now, reuse_classes  # noqa: E402

FILLER = "Operations ledger entry %d for desk %s: throughput nominal, cache warm, retrieval verified. "


def counters(status: dict[str, Any]) -> dict[str, Any]:
    cache = status.get("cache") or {}
    keys = ("pressure_search_budget_exhaustions", "pressure_plans", "pressure_fallbacks",
            "materializations", "host_swaps_in", "host_swaps_out")
    return {k: cache.get(k) for k in keys if k in cache}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key-file", required=True)
    parser.add_argument("--model", default="q38-ninfer")
    parser.add_argument("--sessions", type=int, default=3)
    parser.add_argument("--base-tokens", type=int, default=100000)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--forks", type=int, default=1, help="forks per session per round, after its continuation")
    parser.add_argument("--log-cmd", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    api_key = Path(args.api_key_file).read_text(encoding="utf-8").strip()
    started_ms = int(time.time() * 1000)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    lanes: list[Lane] = []
    for index in range(args.sessions):
        session = hashlib.sha256(f"multisession-{stamp}-{index}".encode()).hexdigest()
        lanes.append(Lane(args.base_url, api_key, session, args.model))
    status_before = lanes[0].status()
    identity = lane_identity(status_before)
    steps: list[dict[str, Any]] = []

    def record(step: str, wall: float, detail: dict[str, Any]) -> None:
        steps.append({"step": step, "wall_s": round(wall, 3), **detail})
        print(f"{step:>28}: {wall:7.2f} s  {json.dumps(detail, default=str)[:160]}", flush=True)

    server_errors: list[dict[str, Any]] = []

    def turn(step: str, lane: Lane, text: Any, previous: str | None, max_output: int):
        """One request; a server error becomes a recorded step, never a lost receipt."""
        try:
            return lane.respond(text, previous=previous, max_output=max_output)
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", "replace")[:400]
            server_errors.append({"step": step, "http_status": error.code, "body": body})
            record(step, 0.0, {"http_status": error.code, "error": body[:160]})
            return None, 0.0

    words_per_entry = len(FILLER.split())
    entries = max(1, (args.base_tokens * 3 // 4) // words_per_entry)
    heads: list[str] = []
    for index, lane in enumerate(lanes):
        desk = f"D{index + 1}"
        corpus = "".join(FILLER % (entry, desk) for entry in range(entries))
        doc, wall = turn(f"base_{desk}", lane,
            [{"role": "user", "content": [{"type": "input_text",
              "text": f"Hold this operations ledger for desk {desk} in context for later analysis; "
                      f"remember the desk code {desk}-{index * 7919 + 4111}. Reply OK only.\n" + corpus}]}],
            None, 16)
        if doc is None:
            break
        heads.append(doc["id"])
        record(f"base_{desk}", wall, {"input_tokens": doc.get("usage", {}).get("input_tokens"), "id": doc["id"]})

    exposures = 0
    stop = len(heads) != len(lanes)
    for round_index in range(args.rounds):
        if stop:
            break
        for index, lane in enumerate(lanes):
            desk = f"D{index + 1}"
            t0 = now()
            doc, wall = turn(f"r{round_index + 1}_continue_{desk}", lane,
                f"Return only the desk code you were asked to remember for desk {desk}.",
                heads[index], 24)
            if doc is None:
                stop = True
                break
            cached = (doc.get("usage", {}).get("input_tokens_details") or {}).get("cached_tokens")
            prompt = doc.get("usage", {}).get("input_tokens")
            text = "".join(part.get("text", "") for item in doc.get("output", [])
                           for part in item.get("content", []) if isinstance(part, dict))
            exact = f"{desk}-{index * 7919 + 4111}" in text
            heads[index] = doc["id"]
            lost = (cached or 0) == 0 and (prompt or 0) > args.base_tokens // 2
            exposures += int(lost)
            record(f"r{round_index + 1}_continue_{desk}", wall, {"prompt_tokens": prompt, "cached_tokens": cached,
                   "exact": exact, "reuse_lost": lost, "since_previous_turn_s": round(now() - t0, 3)})
            for fork in range(args.forks):
                fdoc, fwall = turn(f"r{round_index + 1}_fork{fork + 1}_{desk}", lane,
                                   f"Fork {fork + 1}: restate the desk code for desk {desk} only.",
                                   heads[index], 24)
                if fdoc is None:
                    stop = True
                    break
                fcached = (fdoc.get("usage", {}).get("input_tokens_details") or {}).get("cached_tokens")
                fprompt = fdoc.get("usage", {}).get("input_tokens")
                flost = (fcached or 0) == 0 and (fprompt or 0) > args.base_tokens // 2
                exposures += int(flost)
                record(f"r{round_index + 1}_fork{fork + 1}_{desk}", fwall,
                       {"prompt_tokens": fprompt, "cached_tokens": fcached, "reuse_lost": flost})

    status_after = lanes[0].status()
    for lane in lanes:
        try:
            lane.checkpoint_delete()
        except urllib.error.HTTPError as error:
            server_errors.append({"step": f"delete_{lane.session[:8]}", "http_status": error.code})
    records = reuse_classes(args.log_cmd, started_ms)
    receipt = {
        "artifact_type": "omp_ninfer_multisession_pressure_probe",
        "schema_version": 1,
        "lane": args.lane,
        "identity": identity,
        "generated_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "question": "With several large sessions resident, does a byte-identical-extension continuation or a fork issued immediately after another session's turn lose its prefix reuse (upstream Neroued/ninfer#229)?",
        "parameters": {"sessions": args.sessions, "base_tokens_requested": args.base_tokens, "rounds": args.rounds, "forks_per_session_per_round": args.forks},
        "counters_before": counters(status_before),
        "counters_after": counters(status_after),
        "summary": {
            "continuations_and_forks": sum(1 for s in steps if "continue" in s["step"] or "fork" in s["step"]),
            "reuse_lost": exposures,
            "exposed": exposures > 0,
            "server_errors": server_errors,
            "server_reuse_paths": sorted({str(r.get("reuse")) for r in records}),
            "server_root_requests_after_bases": sum(1 for r in records[args.sessions:] if r.get("reuse") == "root"),
        },
        "steps": steps,
        "server_reuse_records": records,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"receipt written: {args.receipt} exposed={exposures > 0} reuse_lost={exposures} "
          f"server_errors={len(server_errors)}")
    return 1 if server_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
