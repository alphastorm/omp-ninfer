#!/usr/bin/env python3
"""Measure an unmodified upstream OMP client with one or two requests in flight on one NInfer lane.

--home is a seed, never modified. Only models.yml, config.yml and the named key file
are copied into a disposable HOME. Two session HOMEs share their entire .omp root
via symlinks: OMP's provider leases live in .omp/run/provider-inflight, NOT in the
agent directory. Their work and session directories remain separate. The imported
stock_omp_session_proof.Omp driver enables RPC and chooses stateful chaining by client version:
per-model compat for 18.8.x and later, PI_OPENAI_STATEFUL=1 for historical 18.4.x clients.

subagents: one parent must call task once with two scout items, each reading its
own ~20 KB file and returning a random code. The parent must return both codes.
Deliveries are bound to dispatched task labels through the tool-call identity and
result index; duplicate or unmatched result identities cannot replace a task.
The receipt records each subagent's outcome and code observations (searched value
by value when the result is JSON text), and task calls that returned no results.
sessions: two processes start together; each gets a different fact, then recalls
it twice (three turns per process). A barrier aligns each pair of turns.
Each recall/delivery must contain the correct value attributed to its code label
at alphanumeric boundaries; equals, colon and whitespace separators are equivalent.
Every session turn and scout result must be nonempty and contain no foreign code
VALUE, even embedded or relabeled. Completion, topology, identity, request-log and
concurrency checks remain mandatory. Exact-marker and whole-answer formatting are
non-gating `compliance` observations, not literal-extraction/recall guarantees or
a general prose-quality proof. Tests enumerate the gating predicates and prohibit
pure exact-text model-output gates.

The pinned binary's `agents unpack` identifies scout's model as @smol (task uses
@task). `config list --json` and v18.4.0 docs/tools/task.md describe task.batch,
task.maxConcurrency and model precedence: agentModelOverrides, then frontmatter,
then task-role/session fallback. We pin both scout/task overrides and smol/task
roles to the lane, expose effort=lo, disable read summarization, and disable async
execution. A synchronous batch still fans out concurrently; it merely waits for
both results before the parent's next request (src/task/index.ts executeSyncFanout).

--log-cmd must print the lane's JSONL request log. Reserve the lane exclusively and
synchronize client/server clocks. Only requests wholly within the wall window and
matching --model's wire id count. Pair request_start/request_done by
(server_instance_id, request.request_id), using timestamp_unix_ms / 1000. If the
start record is absent, use the DONE record's timings_seconds.total, never TTFT,
decode, queue wait, or throughput duration. Overlap is wall time with >=2 active
requests (not a sum of pairwise intersections). Times have millisecond precision;
this is HTTP/request lifetime overlap, not proof of simultaneous GPU execution.
A request the client cancelled lasts until the engine handles the cancel; the
receipt counts them and also reports the overlap without them, while the checks
use every request.

A --max-in-flight 1 run passes when serial; a run at >=2 requires overlap. Use the
same --seed for both runs. --baseline compares against a passing limit-1 receipt
from the SAME server instance, model, client, thinking level and workload. Savings
are observations, not a speedup guarantee: cache warmth, model tool compliance and
sampling can change the amount of work. The receipt contains only codes, numeric
measurements and allowlisted metadata, never prompts, answers, stderr or keys.
Temporary native OMP transcripts and copied credentials are removed on exit.

Operator example (only while the lead has opened the non-production lane):
  python3 scripts/omp_parallel_proof.py --omp /tmp/omp-darwin-arm64 \
    --client-component docs/measurements/2026-10-10-omp-1887-client-components.json \
    --client-platform darwin-arm64 \
    --home ~/.cache/omp-ninfer-v080-scratch/v087/proof-seed \
    --provider ninfer-beta --model ninfer-beta/q38-ninfer \
    --scenario subagents --scenario sessions --max-in-flight 1 --seed 50901840 \
    --log-cmd 'ssh rtx5090-win-a cat /path/to/window/requests.jsonl' --receipt /tmp/c1.json
  # Repeat with --max-in-flight 2 --baseline /tmp/c1.json --receipt /tmp/c2.json.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stock_omp_session_proof import Omp  # noqa: E402
from omp_client_environment import client_environment, stateful_environment  # noqa: E402

CODE = re.compile(r"(?<![\w-])(?:ALPHA|BETA)-CODE=\d{6}(?![\w-])")
DELIVERY_CODE = re.compile(
    r"(?<![^\W_])((?:ALPHA|BETA)-CODE)(?:\s*[:=]\s*|\s+)([0-9]{6})(?![^\W_])")
STOPS = {"stop", "length", "toolUse", "aborted", "error"}


def rewrite_config(config, provider, max_in_flight):
    """Pure nested-config rewrite; preserve other providers/settings and the input.

    Runtime obtains this mapping through OMP's YAML-aware config CLI and writes it
    back through the same CLI, avoiding a second, incomplete YAML implementation.
    """
    if not isinstance(provider, str) or not provider.strip():
        raise ValueError("provider must be nonempty")
    if type(max_in_flight) is not int or max_in_flight < 1:
        raise ValueError("max_in_flight must be a positive integer")
    updated = deepcopy(config)
    if not isinstance(updated, dict):
        raise ValueError("config must be a mapping")
    providers = updated.setdefault("providers", {})
    if not isinstance(providers, dict):
        raise ValueError("providers must be a mapping")
    limits = providers.setdefault("maxInFlightRequests", {})
    if not isinstance(limits, dict):
        raise ValueError("providers.maxInFlightRequests must be a mapping")
    limits[provider] = max_in_flight
    return updated


def finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("request timing must be a finite number")
    return float(value)


def compute_overlap(intervals):
    """Sweep half-open [start, end) intervals; touching endpoints never overlap."""
    events = {}
    for start, end in intervals:
        start, end = finite_number(start), finite_number(end)
        if end < start:
            raise ValueError("request end precedes its start")
        if end == start:
            continue
        events[start] = events.get(start, 0) + 1
        events[end] = events.get(end, 0) - 1
    active = maximum = 0
    overlapped = 0.0
    previous = None
    for timestamp, delta in sorted(events.items()):
        if previous is not None and active >= 2:
            overlapped += timestamp - previous
        active += delta
        maximum = max(maximum, active)
        previous = timestamp
    return {"max_in_flight": maximum, "overlap_seconds": round(overlapped, 6)}


def analyze_requests(records, window_start, window_end, model):
    """Analyze real NInfer request records without retaining their other content."""
    window_start, window_end = finite_number(window_start), finite_number(window_end)
    if window_end < window_start:
        raise ValueError("invalid scenario window")
    starts, dones = {}, {}
    for record in records:
        event = record.get("event")
        if event not in {"request_start", "request_done", "request"}:
            continue
        request = record.get("request") or {}
        if request.get("model") != model:
            continue
        timestamp = finite_number(record.get("timestamp_unix_ms")) / 1000
        if timestamp > window_end:
            continue
        instance, request_id = record.get("server_instance_id"), request.get("request_id")
        if not isinstance(instance, str) or type(request_id) not in (str, int):
            raise ValueError("request record lacks server instance or request id")
        key = (instance, request_id)
        target = starts if event == "request_start" else dones
        if key in target and target[key] != record:
            raise ValueError("conflicting duplicate request record")
        target[key] = record

    intervals, cancelled, sources, ends, instances = [], [], set(), set(), set()
    for key, done in dones.items():
        end = finite_number(done["timestamp_unix_ms"]) / 1000
        if end < window_start:
            continue
        if key in starts:
            start = finite_number(starts[key]["timestamp_unix_ms"]) / 1000
            source = "request_start.timestamp_unix_ms"
        else:
            duration = finite_number((done.get("timings_seconds") or {}).get("total"))
            if duration < 0:
                raise ValueError("negative total request duration")
            start = end - duration
            source = f"{done['event']}.timestamp_unix_ms - timings_seconds.total * 1000"
        if end < start:
            raise ValueError("request end precedes its start")
        if start < window_start or start >= window_end:
            continue
        intervals.append((start, end))
        cancelled.append((done.get("result") or {}).get("finish_reason") == "cancelled")
        sources.add(source)
        ends.add(f"{done['event']}.timestamp_unix_ms")
        instances.add(key[0])
    unmatched = sum(window_start <= finite_number(row["timestamp_unix_ms"]) / 1000 < window_end
                    and key not in dones for key, row in starts.items())
    # A request the client cancels ends when the engine handles the cancel, which can follow the
    # client's next request (EXP-090); report its overlap apart rather than hide it.
    kept = [interval for interval, flag in zip(intervals, cancelled) if not flag]
    return {**compute_overlap(intervals), "request_count": len(intervals),
            "cancelled_requests": sum(cancelled), "without_cancelled": compute_overlap(kept),
            "unmatched_starts": unmatched, "server_instance_ids": sorted(instances),
            "timestamp_fields": {"start": sorted(sources), "end": sorted(ends),
                                 "unit": "milliseconds; converted to seconds"},
            "intervals_unix_seconds": [[start, end] for start, end in sorted(intervals)]}


@contextmanager
def isolated_environment():
    # Omp intentionally inherits its caller's environment. Do not inherit an OMP
    # profile, agent directory, or XDG state directory from the operator's session.
    saved = {key: value for key, value in os.environ.items()
             if key.startswith(("PI_", "OMP_", "XDG_"))}
    try:
        for key in saved:
            os.environ.pop(key)
        yield
    finally:
        for key in list(os.environ):
            if key.startswith(("PI_", "OMP_", "XDG_")):
                os.environ.pop(key)
        os.environ.update(saved)


def config_command(args, home, action, key, value=None):
    command = [str(args.omp), "config", action, key]
    if action == "set":
        command.append(json.dumps(value))
    command.append("--json")
    result = subprocess.run(command, env=dict(os.environ, HOME=str(home), USERPROFILE=str(home), NO_COLOR="1"),
                            cwd=home, capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=60)
    if result.returncode:
        raise RuntimeError("OMP config command failed")
    return json.loads(result.stdout)


def prepare_home(args, root):
    shared = root / "shared"
    agent = shared / ".omp" / "agent"
    agent.mkdir(parents=True)
    source = args.home / ".omp" / "agent"
    for name in ("models.yml", "config.yml", args.key_file):
        shutil.copyfile(source / name, agent / name)
        (agent / name).chmod(0o600)
    existing = config_command(args, shared, "get", "providers.maxInFlightRequests")["value"]
    config = rewrite_config({"providers": {"maxInFlightRequests": existing}},
                            args.provider, args.max_in_flight)
    config_command(args, shared, "set", "providers.maxInFlightRequests",
                   config["providers"]["maxInFlightRequests"])
    for key in ("modelRoles", "task.agentModelOverrides"):
        mapping = config_command(args, shared, "get", key)["value"]
        mapping.update({name: args.model for name in
                        (("smol", "task") if key == "modelRoles" else ("scout", "task"))})
        config_command(args, shared, "set", key, mapping)
    for key, value in {"task.batch": True, "task.maxConcurrency": 2,
                       "task.enableEffort": True, "async.enabled": False,
                       "enabledProviders": [args.provider], "enabledModels": [args.model],
                       "read.summarize.enabled": False, "tools.approvalMode": "yolo",
                       "startup.checkUpdate": False}.items():
        config_command(args, shared, "set", key, value)
    actual = config_command(args, shared, "get", "providers.maxInFlightRequests")["value"]
    if actual.get(args.provider) != args.max_in_flight:
        raise RuntimeError("OMP did not persist the requested provider limit")
    return shared / ".omp"


def client_args(args, root, shared, label):
    home = root / label
    home.mkdir()
    (home / ".omp").symlink_to(shared, target_is_directory=True)
    (home / "work").mkdir()
    return argparse.Namespace(**{**vars(args), "home": home})


@contextmanager
def client(args, label, observe=None):
    # Retain the instance even if RPC readiness fails in Omp.__init__, so a
    # partially started child cannot outlive this proof or its disposable HOME.
    omp = Omp.__new__(Omp)
    try:
        omp.__init__(args, label, False, observe=observe)
        omp.command("set_thinking_level", level=args.thinking)
        yield omp
    finally:
        try:
            if hasattr(omp, "stdin"):
                omp.close()
        finally:
            if hasattr(omp, "proc"):
                if omp.proc.poll() is None:
                    omp.proc.kill()
                omp.proc.wait(timeout=10)
                if omp.proc.stdout:
                    omp.proc.stdout.close()
            if hasattr(omp, "stderr"):
                omp.stderr.close()


def turn_record(turn, label, index, expected=None, *, other_codes=()):
    answer = turn["answer"]
    record = {"session": label, "index": index, "seconds": turn["seconds"],
              "stop": turn["stop"] if turn["stop"] in STOPS else "error",
              "completed": turn["stop"] == "stop", "nonempty": bool(answer.strip()),
              "isolation": not any(code.split("=", 1)[1] in answer for code in other_codes)}
    if expected is not None:
        record["own_recall"] = expected in delivered_codes(answer)
        record["compliance"] = {
            # Preserve the previous exact-marker and whole-answer oracles as observations.
            "marker_exact": re.search(
                rf"(?<![^\W_]){re.escape(expected)}(?![^\W_])", answer) is not None,
            "formatting_exact": answer.strip() == expected}
    return record


def result_strings(output):
    """String values in one result. A structured result arrives as JSON text whose strings escape
    newlines, and the `n` of an escaped newline before a code reads as a word character (EXP-090),
    so search each decoded string value."""
    value = output
    if isinstance(output, str):
        try:
            value = json.loads(output)
        except ValueError:
            value = output
    found, pending = [], [value]
    while pending:
        node = pending.pop()
        if isinstance(node, str):
            found.append(node)
        elif isinstance(node, dict):
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)
    return found


def result_codes(output):
    """Legacy exact-marker observations, used only for non-gating compliance."""
    return sorted({code for text in result_strings(output) for code in CODE.findall(text)})


def delivered_codes(output):
    """Canonical label/value pairs, independent of the marker's separator formatting."""
    return sorted({f"{label}={value}" for text in result_strings(output)
                   for label, value in DELIVERY_CODE.findall(text)})


class TaskObserver:
    """Bind stock OMP's indexed results to their dispatch; retain only allowlisted evidence."""

    def __init__(self, codes=()):
        self.batches, self.completed, self.without_results = [], [], 0
        self.codes, self.tools, self.calls, self.result_ids = codes, [], {}, set()
        self.initial_tasks, self.attributable = [], True

    def __call__(self, event):
        if event.get("type") == "tool_execution_start":
            self.tools.append(event.get("toolName"))
        if event.get("toolName") != "task":
            return
        call_id = event.get("toolCallId")
        if event.get("type") == "tool_execution_start":
            tasks = (event.get("args") or {}).get("tasks") or []
            self.batches.append(len(tasks))
            dispatched = [{"label": str(item.get("name", "")).casefold(),
                           "agent": item.get("agent")} for item in tasks]
            if len(self.batches) == 1:
                self.initial_tasks = dispatched
            if not isinstance(call_id, str) or not call_id or call_id in self.calls:
                self.attributable = False
            self.calls[call_id] = (len(self.batches), dispatched)
        elif event.get("type") == "tool_execution_end":
            results = ((event.get("result") or {}).get("details") or {}).get("results") or []
            self.without_results += not results
            call, dispatched = self.calls.pop(call_id, (None, []))
            self.attributable &= call is not None
            indices = set()
            for item in results:
                index, result_id = item.get("index"), item.get("id")
                task = (dispatched[index] if type(index) is int and 0 <= index < len(dispatched)
                        else {})
                label = task.get("label")
                identity = (bool(task) and label in {"alpha", "beta"}
                            and task.get("agent") == item.get("agent") == "scout"
                            and isinstance(result_id, str) and bool(result_id.strip())
                            and result_id not in self.result_ids and index not in indices)
                if isinstance(result_id, str):
                    self.result_ids.add(result_id)
                if type(index) is int:
                    indices.add(index)
                output = item.get("output", "")
                texts = result_strings(output)
                # Inspect decoded strings and the full serialized result: a foreign value in a
                # JSON key or numeric leaf is still contamination, not harmless formatting.
                visible = texts + [json.dumps(output, ensure_ascii=False)]
                expected = next((code for code in self.codes
                                 if code.split("-", 1)[0].casefold() == label), None)
                self.completed.append({
                    "session": label if label in {"alpha", "beta"} else None,
                    "call": call, "index": index if type(index) is int else None,
                    "id_sha256": hashlib.sha256(result_id.encode()).hexdigest()
                    if isinstance(result_id, str) else None,
                    "attributable": identity,
                    "ok": item.get("exitCode") == 0 and not item.get("aborted") and not item.get("error"),
                    "nonempty": any(text.strip() for text in texts),
                    "codes": result_codes(output), "delivered_codes": delivered_codes(output),
                    "isolation": not any(code.split("=", 1)[1] in text
                                         for code in self.codes if code != expected for text in visible),
                    "compliance": {"marker_exact": expected in result_codes(output),
                                   "formatting_exact": expected is not None
                                   and any(text.strip() == expected for text in texts)}})


def run_subagents(args, root, shared, codes, record):
    subargs = client_args(args, root, shared, "subagents")
    rng = random.Random(args.seed)
    for label, code in zip(("alpha", "beta"), codes):
        filler = [f"build item {n:04d} digest {rng.getrandbits(96):024x} status complete\n"
                  for n in range(360)]
        filler.insert(rng.randrange(100, 260), code + "\n")
        (subargs.home / "work" / f"{label}.txt").write_text("".join(filler), encoding="utf-8")
    observer = TaskObserver(codes)

    prompt = ("This is a parallel file-reading proof. Do not read the files yourself. Your FIRST "
              "action must be ONE task call with context and exactly TWO items in tasks. Use "
              "agent='scout' and effort='lo' for both; name them Alpha and Beta. Each task must "
              "include solutionSpace='literal extraction from one named file; no design choices'. "
              "Alpha must read alpha.txt and return its exact ALPHA-CODE line; Beta must read "
              "beta.txt and return its exact BETA-CODE line. Give each scout only its own file. "
              "They must use read or grep, not guess, not delegate, and must include the exact "
              "code in their final result. These two independent tasks MUST be in the SAME call, "
              "not sequential calls. Wait for both results, then answer with only the two exact "
              "code lines. Do not invent codes.")
    with client(subargs, "parent", observer) as omp:
        turn = omp.prompt(prompt, args.turn_timeout)
        record["turns"].append(turn_record(turn, "parent", 1))
        record["checks"].update(subagent_checks(observer, turn, codes))
        record["compliance"].update(
            codes_exact=sorted(set(CODE.findall(turn["answer"]))) == sorted(codes),
            codes_delivered_by_subagents=sorted(
                {code for item in observer.completed for code in item["codes"]}) == sorted(codes),
            parent_formatting_exact=turn["answer"].strip() == "\n".join(codes))
        record["task_batch_sizes"] = observer.batches
        record["task_calls_without_results"] = observer.without_results
        record["recovered_dispatch"] = observer.batches != [2]
        record["subagent_results"] = observer.completed


def subagent_checks(observer, turn, codes):
    """Require two attributable, nonempty, isolated deliveries, not literal model formatting.

    Stock OMP recovery batches ([2, 2] or [2, 1]) remain permitted: a completed result without its
    own value may be followed by a correctly attributed recovery, but a different task, duplicate
    result identity, empty output, or foreign value cannot stand in for either scout.
    """
    returned = set(delivered_codes(turn["answer"]))
    completed = observer.completed
    return dict(parent_completed=turn["stop"] == "stop",
                parent_nonempty=bool(turn["answer"].strip()),
                first_task_call_dispatched_both=observer.batches[:1] == [2]
                and observer.tools[:1] == ["task"],
                parent_only_task_calls=bool(observer.tools) and set(observer.tools) == {"task"},
                task_results_attributable=observer.attributable and not observer.calls
                and len(observer.initial_tasks) == 2
                and {task["label"] for task in observer.initial_tasks} == {"alpha", "beta"}
                and all(task["agent"] == "scout" for task in observer.initial_tasks)
                and bool(completed) and all(item["attributable"] for item in completed),
                subagents_completed=bool(completed) and all(item["ok"] for item in completed),
                subagent_results_nonempty=bool(completed) and all(item["nonempty"] for item in completed),
                parent_codes_delivered=all(code in returned for code in codes),
                subagent_codes_delivered=all(
                    any(item["attributable"] and item["session"] == label
                        and code in item["delivered_codes"] for item in completed)
                    for label, code in zip(("alpha", "beta"), codes)),
                subagent_isolation=all(item["isolation"] for item in completed),
                parent_code_isolation=returned <= set(codes))


def run_sessions(args, root, shared, codes, record):
    homes = [client_args(args, root, shared, label) for label in ("alpha", "beta")]
    barrier = threading.Barrier(2, timeout=args.turn_timeout + 120)

    def run_one(subargs, label, code):
        turns, session_id = [], None
        other_codes = tuple(other for other in codes if other != code)
        try:
            with client(subargs, label) as omp:
                prompts = [f"Remember this session's release fact exactly: {code}. Reply only OK.",
                           "Recall this session's release fact. Reply only with the exact code line.",
                           "Once more, what release fact did I give you? Reply only with the exact code line."]
                for index, prompt in enumerate(prompts, 1):
                    barrier.wait()
                    turn = omp.prompt(prompt, args.turn_timeout)
                    turns.append(turn_record(turn, label, index, code if index > 1 else None,
                                             other_codes=other_codes))
                session_id = omp.state()["session_id"]
            return {"turns": turns, "session_id": session_id, "error": None}
        except Exception as error:
            barrier.abort()
            return {"turns": turns, "session_id": session_id, "error": type(error).__name__}

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_one, home, label, code)
                   for home, label, code in zip(homes, ("alpha", "beta"), codes)]
        results = [future.result() for future in futures]
    for label, result in zip(("alpha", "beta"), results):
        record["turns"].extend(result["turns"])
        record["checks"][f"{label}_three_turns_completed"] = (
            result["error"] is None and len(result["turns"]) == 3
            and all(turn["completed"] for turn in result["turns"]))
        record["checks"][f"{label}_turns_nonempty"] = (
            len(result["turns"]) == 3 and all(turn["nonempty"] for turn in result["turns"]))
        record["checks"][f"{label}_isolation"] = all(turn["isolation"] for turn in result["turns"])
        record["checks"][f"{label}_both_recalls_correct"] = (
            len(result["turns"]) == 3 and all(turn.get("own_recall") and turn.get("isolation")
                                            for turn in result["turns"] if turn["index"] > 1))
        record["compliance"][f"{label}_both_recalls_marker_exact"] = (
            len(result["turns"]) == 3
            and all(turn["compliance"]["marker_exact"] for turn in result["turns"] if turn["index"] > 1))
        if result["error"]:
            record["errors"].append(result["error"])
    ids = [result["session_id"] for result in results]
    record["checks"]["separate_sessions"] = all(ids) and ids[0] != ids[1]


def fetch_log(command, timeout):
    result = subprocess.run(command, shell=True, capture_output=True, text=True,
                            encoding="utf-8", errors="strict", timeout=timeout)
    if result.returncode:
        raise RuntimeError("request log command failed")
    records = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    if any(not isinstance(record, dict) for record in records):
        raise ValueError("request log must contain JSON objects")
    return records


def run_scenario(args, root, shared, scenario, codes):
    record = {"scenario": scenario, "codes": codes, "turns": [], "checks": {}, "compliance": {}, "errors": [],
              "max_in_flight": None, "overlap_seconds": None, "request_count": None}
    wall_start, started = math.floor(time.time() * 1000) / 1000, time.monotonic()
    try:
        {"subagents": run_subagents, "sessions": run_sessions}[scenario](args, root, shared, codes, record)
    except Exception as error:
        record["errors"].append(type(error).__name__)
    record["wall_seconds"] = round(time.monotonic() - started, 6)
    wall_end = math.ceil(time.time() * 1000) / 1000
    record["window_unix_seconds"] = [wall_start, wall_end]
    try:
        analysis = analyze_requests(fetch_log(args.log_cmd, args.log_timeout), wall_start, wall_end,
                                    args.model.split("/", 1)[1])
        record.update(analysis)
        record["checks"].update(
            logged_requests=analysis["request_count"] >= 2,
            all_logged_requests_completed=analysis["unmatched_starts"] == 0,
            single_server_instance=len(analysis["server_instance_ids"]) == 1,
            provider_limit_respected=analysis["max_in_flight"] <= args.max_in_flight,
            concurrency_expected=(analysis["max_in_flight"] == 1 and analysis["overlap_seconds"] == 0
                                  if args.max_in_flight == 1 else
                                  analysis["max_in_flight"] >= 2 and analysis["overlap_seconds"] > 0))
    except Exception as error:
        record["errors"].append(type(error).__name__)
        record["checks"]["request_log_analyzed"] = False
    record["passed"] = not record["errors"] and all(record["checks"].values())
    return record


def compare_baseline(receipt, baseline):
    """Refuse speedup claims across different workloads, clients or server instances."""
    if baseline.get("max_in_flight") != 1 or not baseline.get("passed"):
        raise ValueError("baseline must be a passing limit-1 receipt")
    for key in ("model", "provider", "thinking", "seed"):
        if receipt.get(key) != baseline.get(key):
            raise ValueError("baseline workload differs")
    if receipt["omp"]["sha256"] != baseline["omp"]["sha256"]:
        raise ValueError("baseline client differs")
    comparisons = []
    for scenario in receipt["scenarios"]:
        before = next((item for item in baseline["scenarios"] if item["scenario"] == scenario["scenario"]), None)
        if not before or not before["passed"] or not scenario["passed"]:
            raise ValueError("both scenario runs must pass before comparison")
        if before["server_instance_ids"] != scenario["server_instance_ids"]:
            raise ValueError("baseline used a different server instance")
        previous, current = finite_number(before["wall_seconds"]), finite_number(scenario["wall_seconds"])
        if previous <= 0 or current <= 0:
            raise ValueError("wall times must be positive")
        comparisons.append({"scenario": scenario["scenario"], "baseline_wall_seconds": previous,
                            "wall_seconds_saved": round(previous - current, 6),
                            "speedup": round(previous / current, 6),
                            "percent_saved": round(100 * (previous - current) / previous, 3)})
    return comparisons


def positive_int(text):
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return value


def expected_client_identity(args):
    """Bind a platform row or explicit CLI identity; never assume a historical client."""
    if args.client_component:
        if args.omp_version or not args.client_platform:
            raise ValueError("--client-component requires --client-platform, not --omp-version")
        payload = args.client_component.read_bytes()
        descriptor = json.loads(payload)
        try:
            distribution_version = descriptor["omp"]["distribution_version"]
            sha256 = descriptor["platforms"][args.client_platform]["binary_sha256"]
        except (KeyError, TypeError) as error:
            raise ValueError("client descriptor lacks the requested platform binary/version") from error
        if not isinstance(distribution_version, str):
            raise ValueError("client descriptor distribution_version must be a string")
        version = "omp/" + distribution_version
        provenance = {"source": "client descriptor", "platform": args.client_platform,
                      "descriptor_sha256": hashlib.sha256(payload).hexdigest()}
    else:
        if not args.omp_version or args.client_platform:
            raise ValueError("--omp-sha256 requires --omp-version, not --client-platform")
        version, sha256 = args.omp_version, args.omp_sha256
        provenance = {"source": "explicit CLI identity"}
    if not isinstance(version, str) or not re.fullmatch(r"omp/[0-9]+[.][0-9]+[.][0-9]+", version):
        raise ValueError("expected client version must be omp/<major>.<minor>.<patch>")
    if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", sha256):
        raise ValueError("expected client binary SHA-256 must contain 64 hexadecimal digits")
    return version, sha256.lower(), provenance


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--omp", type=Path, required=True, help="unmodified upstream OMP binary")
    identity = parser.add_mutually_exclusive_group(required=True)
    identity.add_argument("--client-component", type=Path, help="verified stage_release client descriptor")
    identity.add_argument("--omp-sha256", help="expected binary SHA-256; requires --omp-version")
    parser.add_argument("--omp-version", help="expected --version output, e.g. omp/18.8.7")
    parser.add_argument("--client-platform", choices=("darwin-arm64", "windows-x64", "linux-x64"),
                        help="descriptor platform row; required with --client-component")
    parser.add_argument("--home", type=Path, required=True, help="read-only route seed HOME")
    parser.add_argument("--provider", default="ninfer-beta")
    parser.add_argument("--model", help="<provider>/<served model ID>; default: --provider plus the guide's RTX 5090 model")
    parser.add_argument("--key-file", default="ninfer-beta.key", help="key filename within seed .omp/agent")
    parser.add_argument("--max-in-flight", type=positive_int, default=2)
    parser.add_argument("--scenario", action="append", choices=("subagents", "sessions"), help="repeatable; default both")
    parser.add_argument("--thinking", choices=("low", "medium", "xhigh"), default="low")
    parser.add_argument("--seed", type=int, default=random.SystemRandom().randrange(2**32))
    parser.add_argument("--turn-timeout", type=positive_int, default=600)
    parser.add_argument("--log-cmd", required=True, help="read-only command printing lane request JSONL")
    parser.add_argument("--log-timeout", type=positive_int, default=60)
    parser.add_argument("--baseline", type=Path, help="passing --max-in-flight 1 receipt from this server instance")
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.model is None:
        from client_acceptance import documented_model_id
        args.model = args.provider + "/" + documented_model_id("rtx5090-macos-client")
    try:
        expected_version, expected_sha256, identity_source = expected_client_identity(args)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    args.omp, args.home = args.omp.expanduser().resolve(), args.home.expanduser().resolve()
    if not args.model.startswith(args.provider + "/") or not args.model.split("/", 1)[1]:
        parser.error("--model must be <provider>/<wire-model-id>")
    if args.key_file in ("", ".", "..") or Path(args.key_file).name != args.key_file:
        parser.error("--key-file must be a filename, not a path")
    scenarios = list(dict.fromkeys(args.scenario or ["subagents", "sessions"]))
    if args.baseline and args.max_in_flight == 1:
        parser.error("--baseline is for a run with more than one request in flight")
    with args.omp.open("rb") as binary:
        actual = hashlib.file_digest(binary, "sha256").hexdigest()
    if actual != expected_sha256:
        parser.error("--omp does not match the expected client binary SHA-256")
    baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline else None
    receipt = {"artifact_type": "omp_ninfer_parallel_proof", "schema_version": 1,
               "omp": {"path": str(args.omp), "sha256": actual, "version": None,
                       "expected_version": expected_version, "identity": identity_source},
               "provider": args.provider, "model": args.model, "max_in_flight": args.max_in_flight,
               "thinking": args.thinking, "seed": args.seed, "synthetic_prompts_only": True,
               "environment": {"shared_config_root": True},
               "scenarios": [], "errors": []}
    rng = random.Random(args.seed)
    numbers = rng.sample(range(100000, 1000000), 2)
    codes = [f"{label}-CODE={number}" for label, number in zip(("ALPHA", "BETA"), numbers)]
    try:
        with tempfile.TemporaryDirectory(prefix="omp-parallel-proof-") as temporary, isolated_environment():
            root = Path(temporary)
            version = subprocess.run([str(args.omp), "--version"], env=dict(os.environ, HOME=str(root)),
                                     capture_output=True, text=True, encoding="utf-8", errors="strict",
                                     check=True, timeout=60).stdout.strip()
            receipt["omp"]["version"] = version
            if version != expected_version:
                raise RuntimeError("client version differs from the expected identity")
            args.omp_version = version
            receipt["environment"].update(stateful_environment(client_environment(version)))
            shared = prepare_home(args, root)
            for scenario in scenarios:
                receipt["scenarios"].append(run_scenario(args, root, shared, scenario, codes))
        if baseline is not None:
            receipt["comparison"] = compare_baseline(receipt, baseline)
    except Exception as error:
        # RPC/provider exceptions may embed response bodies or credentials.
        receipt["errors"].append(type(error).__name__)
    receipt["passed"] = (not receipt["errors"] and len(receipt["scenarios"]) == len(scenarios)
                         and all(item["passed"] for item in receipt["scenarios"]))
    receipt["qualifies_c2"] = receipt["passed"] and args.max_in_flight == 2
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    for scenario in receipt["scenarios"]:
        print(f"{scenario['scenario']}: passed={scenario['passed']} wall={scenario['wall_seconds']:.3f}s "
              f"max_in_flight={scenario.get('max_in_flight')} overlap={scenario.get('overlap_seconds')}s")
    print(f"receipt: {args.receipt}; passed={receipt['passed']}")
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
