#!/usr/bin/env python3
"""Prove that an unmodified upstream OMP session keeps working through automatic compaction.

One OMP session on one NInfer lane grows past OMP's compaction threshold --compactions times. Each
epoch plants a durable identifier early among synthetic build-log filler, keeps adding filler, and
plants a control identifier in the turn before the one expected to cross OMP's threshold (the
resolved context window less max(15%, 16,384) tokens). After OMP commits a compaction on its own,
the session is asked for that control identifier: recent context must survive every compaction.
With --restart-cmd, the first OMP process exits after the last compaction, the server restarts, a
new OMP process continues the session and must recall the last control identifier again.

Durable identifiers are never repeated until the final turn, which asks for all of them. Whether
older context survives depends on the compaction method: a handoff summarizes it, while snapcompact
keeps only a bounded archive and drops the rest of the older middle by design. Their recall is
recorded, not gated.

--home is an isolated HOME whose .omp/agent holds the lane's models.yml and config.yml exactly as the
documented route writes them. OMP runs in RPC mode with PI_OPENAI_STATEFUL=1, as the route requires.
--restart-cmd must stop the server gracefully, start it again and block until the endpoint answers.

The receipt records OMP's identity, the lane model OMP resolved, every turn's stop reason, usage and
duration, every compaction OMP reported (trigger, method, tokens before, duration), each recall
answer, the restart outcome and the pass verdict. Prompts are synthetic and reproducible from
--seed. Exit 0 only when every gated check passes.

Example (operator only):
  python3 scripts/omp_long_session_proof.py --omp ./omp-darwin-arm64 --omp-sha256 <sha256> \\
    --home /tmp/long-home --model ninfer-native-4090/qwen3.8-27b --compactions 3 \\
    --expect-method handoff --restart-cmd 'bash restart-lane.sh' --receipt /tmp/long-session.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import random
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stock_omp_session_proof import Omp, restart  # noqa: E402

WORDS = ("JUNIPER", "LANTERN", "HARBOR", "QUARTZ", "MERIDIAN", "OSPREY", "CITADEL", "TUNDRA",
         "FALCON", "EMBER", "GLACIER", "SEQUOIA")
STEPS = ("configure", "compile", "link", "test", "package", "sign", "upload")
PLANT_DURABLE = ("Keep this identifier for later; I will ask for it. The release ticket for "
                 "milestone {k} is {durable}. Reply with OK only.")
PLANT_CONTROL = ("Keep this identifier for later; I will ask for it. The freeze window for "
                 "milestone {k} is {control}. Reply with OK only.")
FILLER = ("Build log part {part} for milestone {k} follows. No action is needed; reply with OK "
          "only.\n```text\n{log}\n```")
RECALL_CONTROL = ("What is the freeze window identifier for milestone {k}? Reply with just the "
                  "identifier.")
RECALL_DURABLE = ("List the release ticket identifier for every milestone from 1 to {n}, one per "
                  "line as '<milestone>: <identifier>'.")


def identifiers(seed, epochs):
    rng = random.Random(seed)
    words = rng.sample(WORDS, 2 * epochs) if 2 * epochs <= len(WORDS) else [
        rng.choice(WORDS) for _ in range(2 * epochs)]
    values = rng.sample(range(1000, 10000), 2 * epochs)
    return [{"epoch": k + 1, "durable": f"{words[2 * k]}-{values[2 * k]}",
             "control": f"{words[2 * k + 1]}-{values[2 * k + 1]}"} for k in range(epochs)]


def build_log(rng, size):
    lines, total = [], 0
    while total < size:
        line = (f"2026-09-28T{rng.randrange(24):02d}:{rng.randrange(60):02d}:{rng.randrange(60):02d}Z "
                f"worker-{rng.randrange(64):02d} {rng.choice(STEPS)} "
                f"src/module_{rng.randrange(4096):04d}.cpp {rng.randrange(1, 9999)} ms "
                f"cache={'hit' if rng.random() < 0.6 else 'miss'} "
                f"digest={rng.getrandbits(64):016x}")
        lines.append(line)
        total += len(line) + 1
    return "\n".join(lines)[:size]


def compaction_threshold(context_window):
    """OMP 18.4.0's default automatic-compaction threshold for a context window."""
    return context_window - max(int(context_window * 0.15), 16384)


def recalled(answer, *needles):
    folded = answer.casefold()
    return all(needle.casefold() in folded for needle in needles)


class Session:
    """Drives one epoch-structured session and keeps the receipt's turn and compaction records."""

    def __init__(self, args):
        self.args = args
        self.rng = random.Random(args.seed)
        self.turns, self.compactions, self.omp, self.label = [], [], None, None
        self.threshold = None
        self._usage = None

    def observe(self, event):
        kind = event.get("type")
        if kind == "auto_compaction_start":
            self.compactions.append({"turn": len(self.turns) + 1, "process": self.label,
                                     "reason": event.get("reason"), "action": event.get("action"),
                                     "started": time.monotonic(), "committed": False})
        elif kind == "auto_compaction_end":
            record = (self.compactions[-1] if self.compactions and "seconds" not in self.compactions[-1]
                      else {"turn": len(self.turns) + 1, "process": self.label, "started": time.monotonic()})
            if record not in self.compactions:
                self.compactions.append(record)
            result = event.get("result") if isinstance(event.get("result"), dict) else None
            record.update(
                end_action=event.get("action"), aborted=bool(event.get("aborted")),
                will_retry=bool(event.get("willRetry")), skipped=bool(event.get("skipped")),
                error=event.get("errorMessage"),
                tokens_before=result.get("tokensBefore") if result else None,
                summary_bytes=len(str(result.get("summary", "")).encode()) if result else 0,
                seconds=round(time.monotonic() - record.pop("started"), 2),
                committed=bool(result) and not event.get("aborted") and not event.get("errorMessage"))
        elif kind == "agent_end":
            for message in reversed(event.get("messages") or []):
                if message.get("role") == "assistant":
                    self._usage = message.get("usage")
                    break

    def committed(self):
        return sum(1 for record in self.compactions if record.get("committed"))

    def start(self, label, cont):
        self.label = label
        self.omp = Omp(self.args, label, cont, observe=self.observe)
        self.omp.command("set_thinking_level", level=self.args.thinking)

    def stop(self):
        if self.omp:
            state = self.omp.state()
            self.omp.close()
            self.omp = None
            return state
        return None

    def turn(self, kind, text, epoch):
        self._usage = None
        assert self.omp is not None
        result = self.omp.prompt(text, self.args.turn_timeout)
        usage = self._usage or {}
        record = {"index": len(self.turns) + 1, "process": self.label, "epoch": epoch, "kind": kind,
                  "prompt_bytes": len(text.encode()), "seconds": result["seconds"], "stop": result["stop"],
                  "input_tokens": usage.get("input"), "cache_read_tokens": usage.get("cacheRead"),
                  "output_tokens": usage.get("output")}
        if kind != "filler":
            record["answer"] = result["answer"][:500]
        self.turns.append(record)
        if result["stop"] != "stop":
            raise RuntimeError(f"turn {record['index']} ({kind}) ended with {result['stop']!r}")
        return result["answer"]

    @staticmethod
    def context_after(turn):
        """The context after a turn, as the lane reported it."""
        return sum(turn.get(key) or 0 for key in ("input_tokens", "cache_read_tokens", "output_tokens"))

    def filler_growth(self):
        """How much the last filler turn grew the context; before any, a conservative guess."""
        for earlier, later in zip(reversed(self.turns[:-1]), reversed(self.turns)):
            if later["kind"] == "filler" and later["process"] == earlier["process"]:
                grown = self.context_after(later) - self.context_after(earlier)
                if grown > 0:
                    return grown
        return self.args.filler_bytes

    def epoch(self, facts):
        k, before = facts["epoch"], self.committed()
        assert self.threshold is not None
        part, durable, control = 0, False, False
        while self.committed() == before:
            if not durable and part == self.args.plant_after:
                self.turn("plant-durable", PLANT_DURABLE.format(k=k, durable=facts["durable"]), k)
                durable = True
            elif durable and not control and self.turns and (
                    self.context_after(self.turns[-1]) + self.filler_growth() >= self.threshold):
                self.turn("plant-control", PLANT_CONTROL.format(k=k, control=facts["control"]), k)
                control = True
            else:
                part += 1
                self.turn("filler", FILLER.format(part=part, k=k,
                                                  log=build_log(self.rng, self.args.filler_bytes)), k)
            if part > self.args.max_epoch_turns:
                raise RuntimeError(f"epoch {k}: no compaction within {part} filler turns")
        if not (durable and control):
            raise RuntimeError(f"epoch {k}: OMP compacted before both identifiers were planted")
        answer = self.turn("recall-control", RECALL_CONTROL.format(k=k), k)
        return {"epoch": k, "durable": facts["durable"], "control": facts["control"],
                "control_answer": answer[:500], "control_recalled": recalled(answer, facts["control"])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--omp", type=Path, required=True, help="unmodified upstream OMP binary")
    parser.add_argument("--omp-sha256", required=True, help="expected SHA-256 of --omp")
    parser.add_argument("--home", type=Path, required=True, help="isolated HOME holding .omp/agent")
    parser.add_argument("--model", required=True, help="provider/model as the lane's fragment names it")
    parser.add_argument("--thinking", default="low")
    parser.add_argument("--compactions", type=int, default=2, help="epochs, one compaction each")
    parser.add_argument("--expect-method", choices=("handoff", "snapcompact", "context-full", "shake"),
                        help="the compaction method every epoch must commit")
    parser.add_argument("--restart-cmd", help="graceful stop and start; blocks until ready")
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260928)
    parser.add_argument("--filler-bytes", type=int, default=40000)
    parser.add_argument("--plant-after", type=int, default=1, help="filler turns before each durable plant")
    parser.add_argument("--max-epoch-turns", type=int, default=24)
    parser.add_argument("--turn-timeout", type=int, default=900)
    parser.add_argument("--restart-timeout", type=int, default=1800)
    args = parser.parse_args(argv)
    args.home, args.omp = args.home.resolve(), args.omp.resolve()
    if args.compactions < 1:
        parser.error("--compactions must be at least 1")

    actual = hashlib.sha256(args.omp.read_bytes()).hexdigest()
    if actual != args.omp_sha256.lower():
        parser.error(f"{args.omp} has SHA-256 {actual}, not {args.omp_sha256}")
    if not (args.home / ".omp/agent/models.yml").is_file():
        parser.error(f"{args.home}/.omp/agent/models.yml is missing")
    version = subprocess.run([str(args.omp), "--version"], capture_output=True, text=True,
                             env={"HOME": str(args.home), "PATH": "/usr/bin:/bin"}, timeout=60).stdout.strip()

    facts = identifiers(args.seed, args.compactions)
    receipt = {"artifact_type": "omp_ninfer_long_session_proof", "schema_version": 1,
               "started_utc": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "omp": {"sha256": actual, "version": version}, "model": args.model,
               "thinking": args.thinking, "environment": {"PI_OPENAI_STATEFUL": "1"},
               "synthetic_prompts_only": True,
               "parameters": {"compactions": args.compactions, "expect_method": args.expect_method,
                              "seed": args.seed, "filler_bytes": args.filler_bytes,
                              "plant_after": args.plant_after, "restart": bool(args.restart_cmd)},
               "resolved_model": None, "threshold_tokens": None, "epochs": [], "turns": [],
               "compactions": [], "restart": None, "after_restart": None, "durable_recall": None,
               "session_ids": [], "checks": {}, "error": None}
    session = Session(args)
    try:
        session.start("p1", False)
        assert session.omp is not None
        model = (session.omp.command("get_state").get("data") or {}).get("model") or {}
        receipt["resolved_model"] = {key: model.get(key) for key in
                                     ("provider", "id", "input", "contextWindow", "maxTokens", "compat")}
        if not isinstance(model.get("contextWindow"), int):
            raise RuntimeError("OMP resolved no context window for the model")
        session.threshold = receipt["threshold_tokens"] = compaction_threshold(model["contextWindow"])
        for epoch_facts in facts:
            receipt["epochs"].append(session.epoch(epoch_facts))
        last = facts[-1]
        if args.restart_cmd:
            state = session.stop()
            assert state is not None
            receipt["session_ids"].append(state["session_id"])
            receipt["restart"] = restart(args)
            if receipt["restart"]["exit_code"] != 0:
                raise RuntimeError("restart command failed")
            session.start("p2", True)
            answer = session.turn("recall-control", RECALL_CONTROL.format(k=last["epoch"]), None)
            receipt["after_restart"] = {"control": last["control"], "answer": answer[:500],
                                        "recalled": recalled(answer, last["control"])}
        answer = session.turn("recall-durable", RECALL_DURABLE.format(n=args.compactions), None)
        receipt["durable_recall"] = {"answer": answer[:1000], "recalled": {
            str(f["epoch"]): recalled(answer, f["durable"]) for f in facts}}
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
    finally:
        try:
            state = session.stop()
            if state:
                receipt["session_ids"].append(state["session_id"])
        except (RuntimeError, OSError) as error:
            receipt["error"] = receipt["error"] or f"{type(error).__name__}: {error}"
    receipt["turns"], receipt["compactions"] = session.turns, session.compactions
    committed = [record for record in session.compactions if record.get("committed")]
    if receipt["error"] is None:
        receipt["checks"] = {
            "every_turn_completed": all(turn["stop"] == "stop" for turn in session.turns),
            "compactions_committed": len(committed) >= args.compactions,
            "no_failed_compaction": all(record.get("committed") or record.get("skipped")
                                        for record in session.compactions),
            "control_recalled_after_each_compaction": all(e["control_recalled"] for e in receipt["epochs"]),
            "one_session": len(set(receipt["session_ids"])) == 1 and None not in receipt["session_ids"],
        }
        if args.restart_cmd:
            receipt["checks"]["control_recalled_after_restart"] = receipt["after_restart"]["recalled"]
        if args.expect_method:
            receipt["checks"]["expected_method"] = all(r.get("end_action") == args.expect_method
                                                       for r in committed)
    receipt["passed"] = receipt["error"] is None and all(receipt["checks"].values())
    receipt["finished_utc"] = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    for record in session.compactions:
        print(f"compaction turn {record.get('turn')}: {record.get('reason')}/{record.get('end_action')} "
              f"tokens_before={record.get('tokens_before')} {record.get('seconds')} s "
              f"committed={record.get('committed')}")
    for name, passed in receipt["checks"].items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    if receipt["durable_recall"]:
        print(f"durable identifiers recalled (recorded, not gated): {receipt['durable_recall']['recalled']}")
    if receipt["error"]:
        print(f"ERROR {receipt['error']}")
    print(f"receipt written: {args.receipt} passed={receipt['passed']}")
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
