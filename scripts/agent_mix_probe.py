#!/usr/bin/env python3
"""Measure shared-prefix reuse for a synthetic three-agent mix, one capacity arm at a time.

Run against an otherwise idle server with max_concurrency=1. Use the same arguments
and a cold server for each capacity arm; --arm labels, but does not configure, it.
Prefix sizes use system text plus compact tool JSON as a character proxy, NOT the
model's chat template/tokenizer. Calibrate with the returned prompt_tokens. The tool JSON
is part of the system message: the server renders no tool definitions under
tool_choice=none, and a live tool call would end the measured history.
Warm-up A becomes the long-lived continuation session. Each measured A/C/B fresh
request is followed by K turns of that session, including after the final B.

Offline example: python3 scripts/agent_mix_probe.py --dry-run --plan-json plan.json
Live example (operator only): python3 agent_mix_probe.py --arm capacity-4 \
  --base-url http://127.0.0.1:18099 --api-key-file api_key --receipt capacity-4.json \
  --identity ninfer_session --log-cmd 'cat requests.jsonl'

--log-cmd must print chronological JSONL from this server only, after flushing all
completed requests. Client/server clocks must agree. The last N completions after
run start are matched in order; shapes and available token counts must agree.
No automatic retries: a retry would change the cache state under measurement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


VOCABULARY = (
    "stable record window service branch document signal library request response "
    "review observe preserve compare verify collect provide return describe inspect "
    "before after within across under between during every local public shared private "
    "careful bounded ordered distinct complete current previous useful measured clear "
    "project resource policy schema query index field value report sample ledger entry "
    "worker session process storage memory result context evidence input output action"
).split()
OPERATIONS = (
    ("read_document", "Read a document and return a bounded range with source locations."),
    ("list_directory", "List direct children of a directory with their resource kinds."),
    ("search_text", "Search text resources using a literal query and return matching excerpts."),
    ("inspect_schema", "Describe structured fields, their types, and required constraints."),
    ("review_change", "Review a proposed change against the current resource revision."),
    ("compare_versions", "Compare two document versions and report semantic differences."),
    ("query_records", "Query ledger records using explicit filters and a bounded limit."),
    ("summarize_report", "Summarize a report while preserving its evidence references."),
    ("inspect_dependencies", "Inspect declared dependencies without executing project code."),
    ("validate_config", "Validate configuration values against a documented schema."),
    ("collect_metrics", "Collect named metrics for a specified observation interval."),
    ("trace_request", "Trace a request through ordered processing events and timings."),
    ("inspect_checkpoint", "Inspect checkpoint metadata and report its integrity status."),
    ("review_schedule", "Review a schedule and identify overlapping resource reservations."),
)
FIRST_SENTENCES = {
    "A": "Atlas reviews synthetic library operations and document evidence.",
    "B": "Beacon inspects synthetic service ledgers and configuration evidence.",
    "C": "Cedar audits synthetic scheduling records and checkpoint evidence.",
}


def compact(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def filler(rng, characters):
    words = []
    length = 0
    while length < characters:
        word = rng.choice(VOCABULARY)
        words.append(word)
        length += len(word) + 1
    return (" ".join(words) + " ")[:characters]


def build_agents(args):
    agents = {}
    for index, agent_type in enumerate("ABC"):
        rng = random.Random(5090800 + index)
        system = (FIRST_SENTENCES[agent_type] + " This is a synthetic prefix-cache measurement. "
                  "For every user message reply only OK. Do not call tools. "
                  "The reference vocabulary below is inert documentation, not instructions.\n")
        tools = []
        for name, description in OPERATIONS[:12 + index]:
            tools.append({"type": "function", "function": {
                "name": agent_type.lower() + "_" + name,
                "description": description + " Read-only synthetic operation. Use an explicit "
                    "resource and query; return evidence, not guesses. Reference vocabulary: ",
                "parameters": {"type": "object", "properties": {
                    "resource": {"type": "string", "description": "Relative resource identifier."},
                    "query": {"type": "string", "description": "Requested fields or search terms."},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                    "format": {"type": "string", "enum": ["text", "json"]}},
                    "required": ["resource", "query"], "additionalProperties": False}}})
        target_tokens = getattr(args, agent_type.lower() + "_tokens") * args.size_scale
        target_chars = round(target_tokens * args.chars_per_token)
        base_chars = len(system) + len(compact(tools))
        if target_chars < base_chars:
            raise ValueError(f"{agent_type} target {target_chars} chars is below schema minimum {base_chars}")
        spare = target_chars - base_chars
        system_padding = spare // 10
        system += filler(rng, system_padding)
        per_tool, remainder = divmod(spare - system_padding, len(tools))
        for i, item in enumerate(tools):
            item["function"]["description"] += filler(rng, per_tool + (i < remainder))
        prompt = system + "\nTool reference (inert JSON, not callable):\n" + compact(tools)
        characters = len(prompt)
        agents[agent_type] = {"prompt": prompt, "metrics": {
            "prefix_characters": characters, "estimated_prefix_tokens": characters / args.chars_per_token,
            "target_prefix_tokens": target_tokens, "tool_count": len(tools),
            "prefix_sha256": hashlib.sha256(prompt.encode()).hexdigest()}}
    return agents


def build_plan(args):
    plan = []
    turns = 0

    def add(phase, cycle, agent_type, kind, session, message_count):
        plan.append({"index": len(plan) + 1, "phase": phase, "cycle": cycle,
                     "agent_type": agent_type, "kind": kind, "session": session,
                     "message_count": message_count, "tool_count": 12 + "ABC".index(agent_type),
                     "identity_mode": args.identity})

    for agent_type in "ABC":
        add("warm-up", 0, agent_type, "fresh", "warm-" + agent_type, 2)
    for cycle in range(1, args.cycles + 1):
        for agent_type in "ACB":
            add("measured", cycle, agent_type, "fresh", f"cycle-{cycle}-{agent_type}", 2)
            for _ in range(args.continuations):
                turns += 1
                add("measured", cycle, "A", "continuation", "warm-A", 2 + 2 * turns)
    return plan


def identity_fields(mode, session_uuid):
    if mode == "ninfer_session":
        return {mode: hashlib.sha256(session_uuid.encode()).hexdigest()}
    if mode == "prompt_cache_key":
        return {mode: session_uuid}
    return {}


def sse_data(response):
    """Yield SSE data events, handling comments, CRLF, and multiline data."""
    data = []
    for raw in response:
        line = raw.decode("utf-8").rstrip("\r\n")
        if not line:
            if data:
                yield "\n".join(data)
                data = []
        elif line.startswith("data:"):
            data.append(line[5:].removeprefix(" "))
    if data:
        yield "\n".join(data)


def stream_chat(args, api_key, payload, row):
    request = urllib.request.Request(args.base_url.rstrip("/") + "/v1/chat/completions",
        data=compact(payload).encode(), headers={"Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json", "Accept": "text/event-stream"})
    started = time.monotonic()
    row.update(client_ttft_s=None, client_total_s=None, api_prompt_tokens=None)
    content = []
    tool_delta_seen = False
    finished = False
    done = False
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            row["http_status"] = response.status
            for event in sse_data(response):
                if event == "[DONE]":
                    done = True
                    break
                chunk = json.loads(event)
                if chunk.get("error"):
                    raise ValueError("server returned a streaming error")
                usage = chunk.get("usage") or {}
                if usage.get("prompt_tokens") is not None:
                    row["api_prompt_tokens"] = usage["prompt_tokens"]
                for choice in chunk.get("choices", []):
                    delta = choice.get("delta") or {}
                    text = delta.get("content") or ""
                    tool_delta = delta.get("tool_calls") or delta.get("function_call")
                    if (text or tool_delta) and row["client_ttft_s"] is None:
                        row["client_ttft_s"] = time.monotonic() - started
                    if text:
                        content.append(text)
                    tool_delta_seen = tool_delta_seen or bool(tool_delta)
                    if choice.get("finish_reason") is not None:
                        finished = True
        if not done or not finished:
            raise ValueError("incomplete SSE response (missing finish reason or [DONE])")
        if tool_delta_seen:
            raise ValueError("server called a tool although the request declared none; cannot continue that history")
        if not content:
            raise ValueError("server returned no assistant content")
        return {"role": "assistant", "content": "".join(content)}
    except urllib.error.HTTPError as error:
        row["http_status"] = error.code
        raise ValueError(f"HTTP {error.code}: {error.read(2000).decode('utf-8', 'replace')}") from error
    finally:
        row["client_total_s"] = time.monotonic() - started


def load_log(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
    if result.returncode:
        raise ValueError(f"log command exited {result.returncode}")
    records = []
    for number, line in enumerate(result.stdout.splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"log line {number} is not JSON") from error
        if not isinstance(record, dict):
            raise ValueError(f"log line {number} is not an object")
        records.append(record)
    return records


def join_logs(rows, records, since_ms):
    """Return new rows only after the entire ordered join passes consistency checks."""
    if not rows:
        return []
    pairs = []
    pending = None
    overlapping = False
    for record in records:
        if record.get("timestamp_unix_ms", 0) < since_ms:
            continue
        if record.get("event") == "request_start":
            overlapping = pending is not None
            pending = record
        elif record.get("event") == "request_done":
            pairs.append((pending, record, overlapping))
            pending = None
            overlapping = False
    if len(pairs) < len(rows):
        raise ValueError(f"log has {len(pairs)} completions after run start, expected {len(rows)}")
    joined = []
    for row, (start, done, overlap) in zip(rows, pairs[-len(rows):]):
        label = f"request {row['index']}"
        if start is None or overlap:
            raise ValueError(f"{label}: missing or overlapping request_start")
        request = start.get("request") or {}
        done_request = done.get("request") or {}
        if (request.get("request_id") is not None and done_request.get("request_id") is not None
                and request["request_id"] != done_request["request_id"]):
            raise ValueError(f"{label}: start/done request_id mismatch")
        for key in ("message_count", "tool_count"):
            if request.get(key) != row[key]:
                raise ValueError(f"{label}: {key} expected {row[key]}, got {request.get(key)}")
            if key in done_request and done_request[key] != request[key]:
                raise ValueError(f"{label}: start/done {key} mismatch")
        result = done.get("result") or {}
        prompt = result.get("prompt_tokens")
        if prompt is None:
            raise ValueError(f"{label}: missing server prompt_tokens")
        api_prompt = row.get("api_prompt_tokens")
        if api_prompt is not None and api_prompt != prompt:
            raise ValueError(f"{label}: prompt_tokens expected {api_prompt}, got {prompt}")
        timings = done.get("timings_seconds") or {}
        server = {key: result.get(key) for key in ("prefix_reuse_path", "prompt_tokens",
            "prefix_cache_hit_tokens", "computed_prefill_tokens")}
        server.update({"ttft_s": timings.get("ttft"), "prefill_s": timings.get("prefill"),
            "total_s": timings.get("total"),
            "queue_wait_s": (done.get("engine_timing") or {}).get("queue_wait_seconds"),
            "request_id": request.get("request_id"), "protocol": request.get("protocol"),
            "session_sha256": (request.get("client_identity") or {}).get("session_sha256"),
            "message_count": request["message_count"], "tool_count": request["tool_count"],
            "timestamp_unix_ms": done["timestamp_unix_ms"],
            "prompt_tokens_checked": api_prompt is not None})
        joined.append(dict(row, server=server))
    return joined


def median(values):
    values = [value for value in values if value is not None]
    return statistics.median(values) if values else None


def p90(values):
    """Nearest-rank percentile; a single observation remains that observation."""
    values = sorted(value for value in values if value is not None)
    return values[math.ceil(0.9 * len(values)) - 1] if values else None


def summarize_group(rows):
    servers = [row.get("server") or {} for row in rows]
    paths = {}
    for server in servers:
        path = server.get("prefix_reuse_path")
        if path is not None:
            paths[path] = paths.get(path, 0) + 1
    known = sum(paths.values())
    client_times = [row.get("client_ttft_s") for row in rows]
    server_times = [server.get("ttft_s") for server in servers]
    return {"request_count": len(rows), "error_count": sum("error" in row for row in rows),
        "fresh_session_count": sum(row["kind"] == "fresh" for row in rows),
        "server_observed_count": known, "root_count": paths.get("root", 0) if known else None,
        "root_rate": paths.get("root", 0) / known if known else None,
        "reuse_path_distribution": paths, "client_ttft_median_s": median(client_times),
        "client_ttft_p90_s": p90(client_times), "server_ttft_median_s": median(server_times),
        "server_ttft_p90_s": p90(server_times),
        "computed_prefill_tokens_median": median([s.get("computed_prefill_tokens") for s in servers]),
        "prefix_cache_hit_tokens_median": median([s.get("prefix_cache_hit_tokens") for s in servers]),
        "prompt_tokens_median": median([s.get("prompt_tokens", r.get("api_prompt_tokens"))
                                         for r, s in zip(rows, servers)])}


def summarize(rows):
    return {phase: {"fresh": {agent: summarize_group([row for row in rows
        if row["phase"] == phase and row["kind"] == "fresh" and row["agent_type"] == agent])
        for agent in "ABC"}, "continuation": summarize_group([row for row in rows
        if row["phase"] == phase and row["kind"] == "continuation"])}
        for phase in ("warm-up", "measured")}


def print_summary(summary):
    def fmt(value):
        return "-" if value is None else f"{value:.3f}"

    print("phase     type kind          n root rate   server TTFT med/p90  client TTFT med/p90  prefill hit prompt")
    for phase, groups in summary.items():
        entries = [(agent, "fresh", group) for agent, group in groups["fresh"].items()]
        entries.append(("A", "continuation", groups["continuation"]))
        for agent, kind, group in entries:
            if not group["request_count"]:
                continue
            print(f"{phase:9} {agent:4} {kind:12} {group['request_count']:2} "
                  f"{str(group['root_count']) if group['root_count'] is not None else '-':>4} "
                  f"{fmt(group['root_rate']):>5}  "
                  f"{fmt(group['server_ttft_median_s'])}/{fmt(group['server_ttft_p90_s'])}  "
                  f"{fmt(group['client_ttft_median_s'])}/{fmt(group['client_ttft_p90_s'])}  "
                  f"{fmt(group['computed_prefill_tokens_median'])} "
                  f"{fmt(group['prefix_cache_hit_tokens_median'])} {fmt(group['prompt_tokens_median'])} "
                  f"reuse={compact(group['reuse_path_distribution'])}")


def write_json(path, document):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", help="server origin; required except in dry-run")
    parser.add_argument("--api-key-file", help="bearer token file; required except in dry-run")
    parser.add_argument("--model", default="q38-ninfer")
    parser.add_argument("--arm", default="unlabeled", help="capacity/runtime label recorded in receipt")
    parser.add_argument("--receipt", help="output JSON path; required except in dry-run")
    parser.add_argument("--log-cmd", help="shell command printing chronological server JSONL")
    parser.add_argument("--identity-json", help="operator-recorded server identity JSON file")
    parser.add_argument("--identity-url", help="optional explicit server identity GET URL (no URL guessed)")
    parser.add_argument("--identity", choices=("none", "ninfer_session", "prompt_cache_key"), default="none",
                        help="session body field; prompt_cache_key may be ignored by current chat runtime")
    parser.add_argument("--cycles", type=int, default=8)
    parser.add_argument("--continuations", type=int, default=1, metavar="K")
    parser.add_argument("--max-tokens", type=int, default=16)
    parser.add_argument("--chars-per-token", type=float, default=3.6)
    parser.add_argument("--size-scale", type=float, default=1.0, help="multiply all prefix token targets")
    parser.add_argument("--a-tokens", type=float, default=23400, help="A prefix token estimate")
    parser.add_argument("--b-tokens", type=float, default=26000, help="B prefix token estimate")
    parser.add_argument("--c-tokens", type=float, default=28000, help="C prefix token estimate")
    parser.add_argument("--timeout", type=float, default=1800, help="HTTP socket timeout in seconds")
    parser.add_argument("--dry-run", action="store_true", help="offline prefixes and full request plan only")
    parser.add_argument("--plan-json", help="write prompt-free sequence and prefix metrics as JSON")
    args = parser.parse_args(argv)
    for key in ("chars_per_token", "size_scale", "a_tokens", "b_tokens", "c_tokens", "timeout"):
        if not math.isfinite(getattr(args, key)) or getattr(args, key) <= 0:
            parser.error(f"--{key.replace('_', '-')} must be finite and positive")
    if args.cycles < 0 or args.continuations < 0 or args.max_tokens < 1:
        parser.error("cycles/continuations must be nonnegative; max-tokens must be positive")
    if not args.dry_run:
        for key in ("base_url", "api_key_file", "receipt"):
            if not getattr(args, key):
                parser.error(f"--{key.replace('_', '-')} is required except in dry-run")
    return args


def main(argv=None):
    args = parse_args(argv)
    try:
        agents = build_agents(args)
    except ValueError as error:
        print(f"ERROR: {error}")
        return 1
    plan = build_plan(args)
    metrics = {agent: value["metrics"] for agent, value in agents.items()}
    if args.plan_json:
        write_json(args.plan_json, {"arguments": vars(args), "prefixes": metrics, "requests": plan})
    if args.dry_run:
        print("Offline prefix proxy: system text + compact tool JSON (not tokenizer/template output)")
        for agent, item in metrics.items():
            print(f"{agent}: chars={item['prefix_characters']} estimated_tokens="
                  f"{item['estimated_prefix_tokens']:.1f} tools={item['tool_count']}")
        print(f"Sequence: {len(plan)} requests (3 warm-up + {args.cycles} x "
              f"(3 fresh + 3 x {args.continuations} continuations))")
        for row in plan:
            print(f"{row['index']:03} {row['phase']:9} cycle={row['cycle']} "
                  f"{row['agent_type']} {row['kind']:12} session={row['session']} "
                  f"messages={row['message_count']} tools={row['tool_count']}")
        return 0

    rows, errors = [], []
    server_identity = {}
    started_ms = None
    try:
        api_key = Path(args.api_key_file).expanduser().read_text(encoding="utf-8").strip()
        if not api_key:
            raise ValueError("API key file is empty")
        if args.identity_json:
            server_identity["operator"] = json.loads(Path(args.identity_json).expanduser().read_text(encoding="utf-8"))
        if args.identity_url:
            request = urllib.request.Request(args.identity_url, headers={"Authorization": f"Bearer {api_key}"})
            with urllib.request.urlopen(request, timeout=args.timeout) as response:
                server_identity["server"] = json.load(response)
        sessions = {}
        started_ms = int(time.time() * 1000)
        for step in plan:
            row = dict(step)
            agent = agents[row["agent_type"]]
            if row["kind"] == "fresh":
                sessions[row["session"]] = {"uuid": str(uuid.uuid4()),
                    "messages": [{"role": "system", "content": agent["prompt"]}]}
            session = sessions[row["session"]]
            session["messages"].append({"role": "user", "content": f"Synthetic check {row['index']:04d}. Reply only OK."})
            row["message_count"] = len(session["messages"])
            fields = identity_fields(args.identity, session["uuid"])
            row["session_identity"] = fields.get(args.identity)
            row["started_unix_ms"] = int(time.time() * 1000)
            rows.append(row)
            payload = {"model": args.model, "messages": session["messages"],
                "stream": True, "stream_options": {"include_usage": True},
                "max_tokens": args.max_tokens, "temperature": 0,
                "enable_thinking": False, **fields}
            try:
                reply = stream_chat(args, api_key, payload, row)
            except Exception as error:
                row["error"] = f"{type(error).__name__}: {error}"
                raise
            session["messages"].append(reply)
            print(f"{row['index']:03} {row['phase']} {row['agent_type']} {row['kind']} "
                  f"prompt_tokens={row['api_prompt_tokens']} client_ttft={row['client_ttft_s']:.3f}s", flush=True)
    except Exception as error:
        errors.append(f"{type(error).__name__}: {error}")
    if args.log_cmd and rows:
        if errors:
            errors.append("Log join skipped after request failure: failed completions may shift tail ordering")
        else:
            try:
                rows = join_logs(rows, load_log(args.log_cmd), started_ms)
            except Exception as error:
                errors.append(f"log join: {type(error).__name__}: {error}")
    summary = summarize(rows)
    write_json(args.receipt, {"artifact_type": "omp_ninfer_agent_mix_arm", "schema_version": 1,
        "arguments": vars(args), "arm": args.arm, "started_unix_ms": started_ms,
        "finished_unix_ms": int(time.time() * 1000), "identity": server_identity,
        "prefixes": metrics, "planned_request_count": len(plan), "requests": rows,
        "summary": summary, "errors": errors})
    print_summary(summary)
    for error in errors:
        print(f"ERROR: {error}")
    print(f"receipt written: {args.receipt} errors={len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
