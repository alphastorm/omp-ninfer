#!/usr/bin/env python3
"""Prove that an unmodified upstream OMP binary keeps one NInfer session across server restarts.

Three scenarios run against one lane, in order, on one OMP session:

  s1  one OMP process: seed two facts, recall one, restart the server, recall both
  s2  a new OMP process continues the session while the server stays up
  s3  the server restarts, then a new OMP process continues the session

--restart-cmd must stop the server gracefully (so live sessions are saved), start it again and
block until the endpoint answers; it runs through bash and must exit 0. --home is an isolated
HOME whose .omp/agent holds the lane's models.yml and config.yml, exactly as the documented
route writes them. OMP runs in RPC mode with PI_OPENAI_STATEFUL=1, as the route requires.

Every recall must name both facts, and all three scenarios must report the same OMP session id.
The receipt records OMP's identity, each turn's answer and stop reason, each restart's outcome
and the pass verdict; the prompts are synthetic. Exit 0 only when every check passes.

Example (operator only):
  python3 scripts/stock_omp_session_proof.py --omp ./omp-darwin-arm64 --omp-sha256 <sha256> \\
    --home /tmp/proof-home --model ninfer-5090/q38-ninfer --restart-cmd 'bash restart-lane.sh' \\
    --receipt /tmp/stock-omp-proof.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import queue
import subprocess
import threading
import time
from pathlib import Path

NAME, BUILD = "Juniper", "5521"
SEED = (f"For this session: the release we are preparing is called {NAME} and its build number is "
        f"{BUILD}. Acknowledge in one short sentence.")
RECALL_BUILD = "What build number did I mention? Reply with just the number."
RECALL_BOTH = "What is the release called and what is its build number? Reply in the form NAME BUILD."


class Omp:
    """One OMP process in RPC mode: newline-delimited JSON commands and events."""

    def __init__(self, args, label, cont):
        env = dict(os.environ, HOME=str(args.home), PI_OPENAI_STATEFUL="1", NO_COLOR="1")
        command = [str(args.omp), "--mode", "rpc", "--model", args.model,
                   "--session-dir", str(args.home / "sessions")]
        if cont:
            command.append("--continue")
        (args.home / "work").mkdir(parents=True, exist_ok=True)
        self.stderr = open(args.home / f"omp-{label}.stderr", "w", encoding="utf-8")
        self.proc = subprocess.Popen(command, cwd=args.home / "work", env=env, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=self.stderr, text=True, bufsize=1)
        assert self.proc.stdin is not None and self.proc.stdout is not None
        self.stdin, self.stdout = self.proc.stdin, self.proc.stdout
        self.events = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()
        self.next_id = 0
        self._wait(lambda event: event.get("type") == "ready", 60)

    def _pump(self):
        for line in self.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self.events.put(json.loads(line))
            except ValueError:
                self.events.put({"type": "_unparsed"})
        self.events.put({"type": "_eof"})

    def _wait(self, predicate, timeout):
        deadline = time.monotonic() + timeout
        seen = []
        while time.monotonic() < deadline:
            try:
                event = self.events.get(timeout=max(0.1, deadline - time.monotonic()))
            except queue.Empty:
                break
            if event.get("type") == "_eof":
                raise RuntimeError(f"omp exited; last events {seen[-5:]}")
            seen.append(event.get("type"))
            if predicate(event):
                return event, seen
        raise RuntimeError(f"timed out after {timeout} s; last events {seen[-8:]}")

    def command(self, kind, **fields):
        self.next_id += 1
        request_id = str(self.next_id)
        self.stdin.write(json.dumps({"id": request_id, "type": kind, **fields}) + "\n")
        self.stdin.flush()
        response, _ = self._wait(lambda e: e.get("type") == "response" and e.get("id") == request_id, 120)
        if response.get("success") is False:
            raise RuntimeError(f"{kind} refused: {json.dumps(response)[:400]}")
        return response

    def prompt(self, text, timeout):
        started = time.monotonic()
        self.command("prompt", message=text)
        end, seen = self._wait(lambda e: e.get("type") == "agent_end", timeout)
        answer, stop = "", None
        for message in reversed(end.get("messages") or []):
            if message.get("role") == "assistant":
                answer = "".join(part.get("text", "") for part in message.get("content") or []
                                 if isinstance(part, dict) and part.get("type") == "text").strip()
                stop = message.get("errorMessage") or message.get("stopReason")
                break
        return {"prompt": text, "answer": answer, "stop": stop,
                "seconds": round(time.monotonic() - started, 2), "events": len(seen)}

    def state(self):
        data = self.command("get_state").get("data") or {}
        return {"session_id": data.get("sessionId"), "message_count": data.get("messageCount")}

    def close(self):
        self.stdin.close()
        try:
            self.proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.stderr.close()


def restart(args):
    started = time.monotonic()
    result = subprocess.run(["bash", "-c", args.restart_cmd], capture_output=True, text=True,
                            timeout=args.restart_timeout)
    return {"exit_code": result.returncode, "seconds": round(time.monotonic() - started, 1),
            "output_tail": (result.stdout + result.stderr)[-600:]}


def recalls(turn, *needles):
    # "Reply in the form NAME BUILD" invites an upper-case name; the fact, not its case, is recalled.
    answer = turn["answer"].casefold()
    return turn["stop"] == "stop" and all(needle.casefold() in answer for needle in needles)


def run_scenario(args, label, cont, steps):
    """steps: prompts, or the literal 'restart'; returns the scenario record."""
    record = {"id": label, "continue": cont, "steps": []}
    omp = Omp(args, label, cont)
    try:
        omp.command("set_thinking_level", level=args.thinking)
        for step in steps:
            if step == "restart":
                outcome = restart(args)
                record["steps"].append({"restart": outcome})
                if outcome["exit_code"] != 0:
                    raise RuntimeError("restart command failed")
            else:
                record["steps"].append({"turn": omp.prompt(step, args.turn_timeout)})
        record["state"] = omp.state()
    finally:
        omp.close()
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--omp", type=Path, required=True, help="unmodified upstream OMP binary")
    parser.add_argument("--omp-sha256", required=True, help="expected SHA-256 of --omp")
    parser.add_argument("--home", type=Path, required=True, help="isolated HOME holding .omp/agent")
    parser.add_argument("--model", required=True, help="provider/model as the lane's fragment names it")
    parser.add_argument("--thinking", default="low")
    parser.add_argument("--restart-cmd", required=True, help="graceful stop and start; blocks until ready")
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--turn-timeout", type=int, default=900)
    parser.add_argument("--restart-timeout", type=int, default=1800)
    args = parser.parse_args(argv)
    args.home = args.home.resolve()
    args.omp = args.omp.resolve()

    actual = hashlib.sha256(args.omp.read_bytes()).hexdigest()
    if actual != args.omp_sha256.lower():
        parser.error(f"{args.omp} has SHA-256 {actual}, not {args.omp_sha256}")
    if not (args.home / ".omp/agent/models.yml").is_file():
        parser.error(f"{args.home}/.omp/agent/models.yml is missing")
    version = subprocess.run([str(args.omp), "--version"], capture_output=True, text=True,
                             env=dict(os.environ, HOME=str(args.home)), timeout=60).stdout.strip()

    receipt = {"artifact_type": "omp_ninfer_stock_session_proof", "schema_version": 1,
               "started_utc": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "omp": {"sha256": actual, "version": version}, "model": args.model,
               "thinking": args.thinking, "environment": {"PI_OPENAI_STATEFUL": "1"},
               "synthetic_prompts_only": True, "scenarios": [], "checks": {}, "error": None}
    try:
        s1 = run_scenario(args, "s1-one-process-across-restart", False,
                          [SEED, RECALL_BUILD, "restart", RECALL_BOTH])
        receipt["scenarios"].append(s1)
        s2 = run_scenario(args, "s2-new-process-server-up", True, [RECALL_BOTH])
        receipt["scenarios"].append(s2)
        s3 = run_scenario(args, "s3-new-process-after-restart", True, ["restart", RECALL_BOTH])
        receipt["scenarios"].append(s3)
        turns = {scenario["id"]: [step["turn"] for step in scenario["steps"] if "turn" in step]
                 for scenario in receipt["scenarios"]}
        receipt["checks"] = {
            "s1_seed_completed": turns[s1["id"]][0]["stop"] == "stop" and bool(turns[s1["id"]][0]["answer"]),
            "s1_recall_before_restart": recalls(turns[s1["id"]][1], BUILD),
            "s1_recall_after_restart": recalls(turns[s1["id"]][2], NAME, BUILD),
            "s2_recall_new_process": recalls(turns[s2["id"]][0], NAME, BUILD),
            "s3_recall_after_restart_new_process": recalls(turns[s3["id"]][0], NAME, BUILD),
            "one_session": len({scenario["state"]["session_id"] for scenario in receipt["scenarios"]}) == 1
                           and s1["state"]["session_id"] is not None,
        }
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
    receipt["passed"] = receipt["error"] is None and bool(receipt["checks"]) and all(receipt["checks"].values())
    receipt["finished_utc"] = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    for name, passed in receipt["checks"].items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    if receipt["error"]:
        print(f"ERROR {receipt['error']}")
    print(f"receipt written: {args.receipt} passed={receipt['passed']}")
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
