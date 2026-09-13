#!/usr/bin/env python3
"""Minimal reproduction: continue a sibling branch after another sibling exists.

Shape, all in one session, all small prompts:

    R0 (base) -> R1 -> R2          first branch from R1
                  \\-> R3          second branch from R1 (sibling of R2)
                       \\-> R4     continue the second sibling

The last step is the one under test. This is the ordinary agent-fanout pattern OMP produces when
two subagents branch from the same turn and one of them keeps going, so a server error here is
reachable from a supported client without pressure, long contexts, or restarts.

Example:
  python3 scripts/sibling_continue_probe.py --lane rtx5090-v063-published \
    --base-url http://127.0.0.1:18189 --api-key-file /tmp/route-key \
    --receipt docs/measurements/$(date +%F)-sibling-continue-rtx5090.json
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
from fleet_probe import Lane, lane_identity  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key-file", required=True)
    parser.add_argument("--model", default="q38-ninfer")
    parser.add_argument("--depth", type=int, default=1,
                        help="turns between the base and the branch point")
    parser.add_argument("--siblings", type=int, default=2, help="branches from the branch point")
    parser.add_argument("--continue-sibling", type=int, default=2,
                        help="1-based sibling to continue after the others exist")
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    api_key = Path(args.api_key_file).read_text(encoding="utf-8").strip()
    session = hashlib.sha256(
        f"sibling-{dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%S%fZ')}".encode()).hexdigest()
    lane = Lane(args.base_url, api_key, session, args.model)
    steps: list[dict[str, Any]] = []
    error: dict[str, Any] | None = None

    def turn(step: str, text: str, previous: str | None) -> str | None:
        nonlocal error
        started = time.monotonic()
        try:
            document, _ = lane.respond(text, previous=previous, max_output=16)
        except urllib.error.HTTPError as failure:
            body = failure.read().decode("utf-8", "replace")
            error = {"step": step, "previous_response_id": previous, "http_status": failure.code,
                     "body": json.loads(body) if body.startswith("{") else body[:400]}
            steps.append({"step": step, "previous": previous, "http_status": failure.code,
                          "wall_s": round(time.monotonic() - started, 3)})
            print(f"{step:>22}: HTTP {failure.code} {body[:160]}", flush=True)
            return None
        usage = document.get("usage", {}) or {}
        cached = (usage.get("input_tokens_details") or {}).get("cached_tokens")
        steps.append({"step": step, "previous": previous, "id": document["id"],
                      "prompt_tokens": usage.get("input_tokens"), "cached_tokens": cached,
                      "wall_s": round(time.monotonic() - started, 3)})
        print(f"{step:>22}: {document['id']} prompt={usage.get('input_tokens')} "
              f"cached={cached}", flush=True)
        return document["id"]

    status = lane.status()
    head = turn("base", "Remember the token SIBLING-77. Reply OK only.", None)
    for index in range(args.depth):
        if head is None:
            break
        head = turn(f"depth_{index + 1}", "Reply OK only.", head)
    branch_point = head
    siblings: list[str] = []
    for index in range(args.siblings):
        if branch_point is None:
            break
        child = turn(f"sibling_{index + 1}", f"Branch {index + 1}: reply OK only.", branch_point)
        if child is None:
            break
        siblings.append(child)
    target = args.continue_sibling - 1
    if error is None and len(siblings) > target:
        turn(f"continue_sibling_{args.continue_sibling}",
             "Return only the token you were asked to remember.", siblings[target])

    try:
        lane.checkpoint_delete()
    except urllib.error.HTTPError:
        pass
    receipt = {
        "artifact_type": "omp_ninfer_sibling_continuation_probe",
        "schema_version": 1,
        "lane": args.lane,
        "identity": lane_identity(status),
        "generated_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "shape": {"depth": args.depth, "siblings": args.siblings,
                  "continued_sibling": args.continue_sibling},
        "reproduced": error is not None,
        "error": error,
        "steps": steps,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"receipt written: {args.receipt} reproduced={error is not None}")
    return 1 if error is not None else 0


if __name__ == "__main__":
    raise SystemExit(main())
