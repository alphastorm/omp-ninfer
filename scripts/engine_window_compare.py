#!/usr/bin/env python3
"""Engine window, step 1: one arm of the shipped-runtime vs upstream-head comparison.

Runs the RTX 5090 lane gates that need no durable checkpoint layer - exact long-context retrieval,
decode, two long sessions alternating turns, sibling fanout from one base, and the live-sibling
agent protocol - against one candidate server and writes one receipt. Run it once per arm on the
same appliance, with the same model weights and serving arguments, and compare the receipts.

``--wire fork`` sends the shipped runtime's authenticated session (the ``X-NInfer-Session`` header
and ``ninfer_session`` body field). ``--wire upstream`` sends neither: upstream NInfer rejects
unknown body fields and has no session identity, so the arms differ only where the runtimes do.
Timings come from each runtime's own request-log JSONL, which both write in the same shape.

The receipt names every session's newest stored response. After a graceful stop and a restart of
the same arm, ``--resume-from`` continues each of those sessions once from that response and
records whether the server restored it from its checkpoint instead of prefilling it again.

Example (on the appliance, against a window container on 127.0.0.1:18099):
  python3 engine_window_compare.py --arm upstream-594930e7 --wire upstream \
    --base-url http://127.0.0.1:18099 --api-key-file ~/services/ninfer-5090/secrets/api_key \
    --long-fixture long_niah_128k.json --log-cmd 'cat ~/services/engine-window/logs/*.jsonl' \
    --identity-json identity.json --receipt w1-upstream.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import http.client
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

EXPECTED_LONG = "ORCHID=493817; COLOR=COBALT"
DECODE_PROMPT = (
    "Write a detailed technical design document for a durable, restart-safe session checkpoint "
    "store used by a local LLM inference server. Cover the on-disk layout, generation manifests, "
    "atomic publication, integrity verification, quota reclamation, lazy restore, and the failure "
    "modes of each stage, with concrete pseudocode for every component. Be exhaustive."
)
FILLER = "Operations ledger entry %d for desk %s: throughput nominal, cache warm, retrieval verified. "
RESUME_OUTPUT_TOKENS = 1024


def now() -> float:
    return time.monotonic()


class Client:
    def __init__(self, base_url: str, api_key: str, model: str, wire: str, session: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.wire = wire
        self.session = session
        self.newest: str | None = None

    def request(self, path: str, payload: dict[str, Any] | None, timeout: float = 1800.0,
                method: str | None = None) -> Any:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        if self.wire == "fork":
            headers["X-NInfer-Session"] = self.session
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(self.base_url + path, data=data, method=method, headers=headers)
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    return json.loads(response.read() or b"{}")
            except (http.client.RemoteDisconnected, ConnectionResetError):
                if attempt == 2:
                    raise
                time.sleep(2.0)
        raise AssertionError("unreachable")

    def respond(self, text_or_items: Any, previous: str | None, max_output: int,
                store: bool = True) -> tuple[dict[str, Any], float]:
        payload: dict[str, Any] = {"model": self.model, "input": text_or_items, "store": store,
                                   "temperature": 0, "max_output_tokens": max_output}
        if self.wire == "fork":
            payload["ninfer_session"] = self.session
        if previous is not None:
            payload["previous_response_id"] = previous
        started = now()
        document = self.request("/v1/responses", payload)
        if store:
            self.newest = document.get("id")
        return document, now() - started

    def chat(self, messages: list[dict[str, Any]], max_tokens: int) -> tuple[dict[str, Any], float]:
        started = now()
        document = self.request("/v1/chat/completions", {
            "model": self.model, "messages": messages, "max_completion_tokens": max_tokens,
            "temperature": 0, "reasoning_effort": "none"})
        return document, now() - started


def session_digest(label: str) -> str:
    return hashlib.sha256(f"engine-window-{label}-{dt.datetime.now(dt.UTC).isoformat()}".encode()).hexdigest()


def usage_of(document: dict[str, Any]) -> tuple[int | None, int | None, int | None]:
    usage = document.get("usage") or {}
    prompt = usage.get("input_tokens", usage.get("prompt_tokens"))
    completion = usage.get("output_tokens", usage.get("completion_tokens"))
    details = usage.get("input_tokens_details") or usage.get("prompt_tokens_details") or {}
    return prompt, completion, details.get("cached_tokens")


def output_text(document: dict[str, Any]) -> str:
    if "choices" in document:
        return (document["choices"][0]["message"].get("content") or "").strip()
    return "".join(part.get("text", "") for item in document.get("output", [])
                   for part in item.get("content", []) or [] if isinstance(part, dict))


def request_log(log_cmd: str, since_ms: int) -> list[dict[str, Any]]:
    result = subprocess.run(log_cmd, shell=True, capture_output=True, text=True, timeout=300)
    records = []
    for line in result.stdout.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("event") == "request_done" and int(record.get("timestamp_unix_ms", 0)) >= since_ms:
            records.append(record)
    return records


def server_view(records: list[dict[str, Any]], prompt: int | None, completion: int | None) -> dict[str, Any]:
    """The request-log record with this exact token shape, reduced to rates and reuse."""
    for record in reversed(records):
        result = record.get("result") or {}
        if result.get("prompt_tokens") != prompt or result.get("completion_tokens") != completion:
            continue
        timings = record.get("timings_seconds") or {}
        speculative = record.get("speculative") or result.get("speculative") or {}
        prefill, decode = timings.get("prefill"), timings.get("decode")
        computed = result.get("computed_prefill_tokens")
        drafted, accepted = speculative.get("drafted_tokens"), speculative.get("accepted_tokens")
        rounds = speculative.get("rounds")
        return {
            "reuse": result.get("prefix_reuse_path"),
            "reused_tokens": result.get("prefix_cache_hit_tokens"),
            "computed_prefill_tokens": computed,
            "ttft_s": timings.get("ttft"),
            "prefill_s": prefill,
            "decode_s": decode,
            "prefill_tok_s": round(computed / prefill, 1) if computed and prefill else None,
            "decode_tok_s": round(completion / decode, 2) if completion and decode else None,
            "mtp_acceptance": round(accepted / drafted, 4) if drafted and accepted is not None else None,
            "mtp_tokens_per_round": round(completion / rounds, 2) if completion and rounds else None,
        }
    return {}


def code_check(document: dict[str, Any], code: str) -> bool | None:
    """Whether the answer names the code; None when the output limit cut the answer off first."""
    if code in output_text(document):
        return True
    return None if document.get("status") == "incomplete" else False


def desk_code(label: str) -> str | None:
    """The code the two-session workload asked session-D<n> to remember, or None."""
    if not label.startswith("session-D"):
        return None
    index = int(label.removeprefix("session-D")) - 1
    return f"D{index + 1}-{index * 7919 + 4111}"


def resume(args: argparse.Namespace, api_key: str) -> int:
    """Continue every session a workload receipt recorded, once, from its newest stored response."""
    source = json.loads(args.resume_from.read_text(encoding="utf-8"))
    started_ms = int(time.time() * 1000)
    results: list[dict[str, Any]] = []
    for label, session in sorted(source["sessions"].items()):
        lane = Client(args.base_url, api_key, args.model, args.wire, session["session_sha256"])
        code = desk_code(label)
        prompt = (f"Return only the desk code you were asked to remember for desk {code.split('-')[0]}."
                  if code else "Continue: reply with the single word RESUMED.")
        outcome: dict[str, Any] = {"session": label, "session_sha256_prefix": session["session_sha256"][:12]}
        try:
            # Thinking stays on as in the workload, so the budget must cover the reasoning that
            # precedes the answer; the workload's 24-token continuations end inside it.
            document, wall = lane.respond(prompt, session["newest_response_id"], RESUME_OUTPUT_TOKENS)
        except urllib.error.HTTPError as error:
            outcome.update({"http_status": error.code, "body": error.read().decode("utf-8", "replace")[:300]})
        else:
            prompt_tokens, completion, cached = usage_of(document)
            outcome.update({"http_status": 200, "wall_s": round(wall, 3), "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion, "cached_tokens": cached})
            outcome["output"] = output_text(document)[-200:]
            if code:
                outcome["code_exact"] = code_check(document, code)
        print(f"{'resume_' + label:>30}: {json.dumps(outcome)}", flush=True)
        results.append(outcome)

    time.sleep(2.0)
    records = request_log(args.log_cmd, started_ms)
    for outcome in results:
        if outcome["http_status"] == 200:
            outcome["server"] = server_view(records, outcome["prompt_tokens"], outcome["completion_tokens"])
    resumed = [outcome for outcome in results if outcome["http_status"] == 200]
    # A restarted server holds no cache, so reusing most of the prompt means it restored the checkpoint.
    restored = [outcome for outcome in resumed
                if (outcome["cached_tokens"] or 0) * 2 > (outcome["prompt_tokens"] or 0)]
    receipt = {
        "artifact_type": "omp_ninfer_engine_window_resume",
        "schema_version": 1,
        "arm": args.arm,
        "wire": args.wire,
        "generated_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "identity": json.loads(args.identity_json.read_text(encoding="utf-8")) if args.identity_json else None,
        "resumed_from_sha256": hashlib.sha256(args.resume_from.read_bytes()).hexdigest(),
        "summary": {
            "sessions": len(results),
            "resumed": len(resumed),
            "restored_from_checkpoint": len(restored),
            "desk_codes_exact": {outcome["session"]: outcome.get("code_exact")
                                 for outcome in results if desk_code(outcome["session"])},
        },
        "sessions": results,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"receipt written: {args.receipt} restored={len(restored)}/{len(results)}")
    return 0 if len(restored) == len(results) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--arm", required=True, help="receipt label for this runtime arm")
    parser.add_argument("--wire", choices=("fork", "upstream"), required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key-file", required=True, type=Path)
    parser.add_argument("--model", default="q38-ninfer")
    parser.add_argument("--long-fixture", type=Path, help="required unless --resume-from")
    parser.add_argument("--log-cmd", required=True, help="shell command printing the arm's request JSONL")
    parser.add_argument("--identity-json", type=Path, help="operator-recorded identity of the arm")
    parser.add_argument("--decode-reps", type=int, default=3)
    parser.add_argument("--session-base-tokens", type=int, default=100000)
    parser.add_argument("--fanout-base-tokens", type=int, default=56000)
    parser.add_argument("--fanout-branches", type=int, default=4)
    parser.add_argument("--explicit-saves", action="store_true",
                        help="fork wire only: after the gates, POST an explicit checkpoint for every session")
    parser.add_argument("--resume-from", type=Path,
                        help="a receipt of this arm: continue each of its sessions once after a restart")
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    if args.resume_from is None and args.long_fixture is None:
        parser.error("--long-fixture is required unless --resume-from is given")

    api_key = args.api_key_file.read_text(encoding="utf-8").strip()
    if args.resume_from is not None:
        return resume(args, api_key)
    started_ms = int(time.time() * 1000)
    errors: list[dict[str, Any]] = []
    calls: list[tuple[str, dict[str, Any], float]] = []

    clients: dict[str, Client] = {}

    def client(label: str) -> Client:
        clients[label] = Client(args.base_url, api_key, args.model, args.wire, session_digest(label))
        return clients[label]

    def call(step: str, fn, *fn_args, **fn_kwargs) -> dict[str, Any] | None:
        try:
            document, wall = fn(*fn_args, **fn_kwargs)
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", "replace")[:400]
            errors.append({"step": step, "http_status": error.code, "body": body})
            print(f"{step:>30}: HTTP {error.code} {body[:120]}", flush=True)
            return None
        calls.append((step, document, wall))
        prompt, completion, cached = usage_of(document)
        print(f"{step:>30}: {wall:8.2f} s prompt={prompt} completion={completion} cached={cached}", flush=True)
        return document

    # Long context: exact retrieval at the ceiling-class prompt.
    messages = json.loads(args.long_fixture.read_text(encoding="utf-8"))
    long_doc = call("long_context", client("long").chat, messages, 128)

    # Decode: the qualification gate's prompt, as the gate sends it and with thinking off.
    decode_client = client("decode")
    for rep in range(args.decode_reps):
        call(f"decode_responses_{rep + 1}", decode_client.respond, DECODE_PROMPT, None, 2048, store=False)
    for rep in range(args.decode_reps):
        call(f"decode_chat_no_thinking_{rep + 1}", decode_client.chat,
             [{"role": "user", "content": DECODE_PROMPT}], 2048)

    # Two long sessions alternating turns (EXP-041's workload): continuation, then a fork.
    words = len(FILLER.split())
    sessions = []
    for index in range(2):
        desk = f"D{index + 1}"
        corpus = "".join(FILLER % (entry, desk) for entry in range(max(1, (args.session_base_tokens * 3 // 4) // words)))
        lane = client(f"session-{desk}")
        doc = call(f"session_base_{desk}", lane.respond,
                   [{"role": "user", "content": [{"type": "input_text",
                     "text": f"Hold this operations ledger for desk {desk} in context for later analysis; "
                             f"remember the desk code {desk}-{index * 7919 + 4111}. Reply OK only.\n" + corpus}]}],
                   None, 16)
        sessions.append({"desk": desk, "code": f"{desk}-{index * 7919 + 4111}", "lane": lane,
                         "head": doc["id"] if doc else None})
    for round_index in range(2):
        for session in sessions:
            if not session["head"]:
                continue
            doc = call(f"r{round_index + 1}_continue_{session['desk']}", session["lane"].respond,
                       f"Return only the desk code you were asked to remember for desk {session['desk']}.",
                       session["head"], 24)
            if doc:
                session["head"] = doc["id"]
                session.setdefault("exact", []).append(code_check(doc, session["code"]))
            call(f"r{round_index + 1}_fork_{session['desk']}", session["lane"].respond,
                 f"Fork: restate the desk code for desk {session['desk']} only.", session["head"], 24)

    # Sibling fanout from one base (fleet_probe's shape), then a continuation from one sibling.
    fan = client("fanout")
    corpus = "".join("Operations ledger entry %d: throughput nominal, cache warm, retrieval verified. " % index
                     for index in range(max(1, (args.fanout_base_tokens * 3 // 4) // 11)))
    base = call("fanout_base", fan.respond,
                [{"role": "user", "content": [{"type": "input_text",
                  "text": "Hold this operations ledger in context for later analysis; reply OK only.\n" + corpus}]}],
                None, 40)
    branches = []
    if base:
        call("fanout_warm_edit", fan.respond, "Summarize entry 3 in six words.", base["id"], 80)
        for index in range(args.fanout_branches):
            doc = call(f"fanout_branch_{index}", fan.respond,
                       f"Branch role {index}: summarize entry {index + 5} in six words.", base["id"], 80)
            if doc:
                branches.append(doc["id"])
        if len(branches) > 1:
            call("fanout_continue_sibling", fan.respond, "Continue: summarize entry 30 in six words.", branches[1], 80)

    # Agent protocol: a continuation while its sibling is alive (ninfer#43), then DELETE semantics.
    agent = client("agent")
    protocol: dict[str, Any] = {}
    root = call("agent_base", agent.respond, "You are a build assistant. Reply with the single word READY.", None, 16)
    if root:
        fork_a = call("agent_fork_a", agent.respond, "Fork A: reply with the single word ALPHA.", root["id"], 16)
        fork_b = call("agent_fork_b", agent.respond, "Fork B: reply with the single word BRAVO.", root["id"], 16)
        if fork_a and fork_b:
            live = call("agent_live_sibling_continue", agent.respond, "Continue: reply with the single word CHARLIE.",
                        fork_b["id"], 16)
            protocol["live_sibling_continue"] = "ok" if live else "error"
            try:
                agent.request(f"/v1/responses/{fork_a['id']}", None, 120.0, method="DELETE")
                protocol["delete_status"] = 200
            except urllib.error.HTTPError as error:
                protocol["delete_status"] = error.code
            try:
                agent.respond("Continue: reply with the single word CHARLIE.", fork_a["id"], 16)
                protocol["deleted_continue_status"] = 200
            except urllib.error.HTTPError as error:
                body = error.read().decode("utf-8", "replace")
                protocol["deleted_continue_status"] = error.code
                try:
                    protocol["deleted_continue_code"] = json.loads(body).get("error", {}).get("code")
                except json.JSONDecodeError:
                    protocol["deleted_continue_code"] = None
            survivor = call("agent_survivor_continue", agent.respond, "Continue: reply with the single word DELTA.",
                            fork_b["id"], 16)
            protocol["survivor_continue"] = "ok" if survivor else "error"

    # Explicit saves, one per session, so a refusal logged by the server is attributable to a session.
    explicit_saves: list[dict[str, Any]] = []
    if args.explicit_saves and args.wire == "fork":
        for label, lane in clients.items():
            started = now()
            try:
                document = lane.request("/v1/ninfer/checkpoints", {"session_sha256": lane.session}, 900.0)
                outcome: dict[str, Any] = {"http_status": 200, "generation": document.get("generation"),
                                           "bytes": document.get("bytes"),
                                           "frontier_tokens": document.get("frontier_tokens")}
            except urllib.error.HTTPError as error:
                body = error.read().decode("utf-8", "replace")[:300]
                try:
                    code = json.loads(body).get("error", {}).get("code")
                except json.JSONDecodeError:
                    code = None
                outcome = {"http_status": error.code, "error_code": code}
            outcome.update({"session": label, "session_sha256_prefix": lane.session[:12],
                            "wall_s": round(now() - started, 3)})
            explicit_saves.append(outcome)
            print(f"{'explicit_save_' + label:>30}: {json.dumps(outcome)}", flush=True)

    time.sleep(2.0)
    records = request_log(args.log_cmd, started_ms)
    steps = []
    for step, document, wall in calls:
        prompt, completion, cached = usage_of(document)
        steps.append({"step": step, "wall_s": round(wall, 3), "prompt_tokens": prompt,
                      "completion_tokens": completion, "cached_tokens": cached,
                      "server": server_view(records, prompt, completion)})

    def pick(prefix: str) -> list[dict[str, Any]]:
        return [s for s in steps if s["step"].startswith(prefix)]

    long_text = output_text(long_doc) if long_doc else None
    continuation_steps = [s for s in steps if s["step"].startswith("r")]
    receipt = {
        "artifact_type": "omp_ninfer_engine_window_arm",
        "schema_version": 1,
        "arm": args.arm,
        "wire": args.wire,
        "generated_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "identity": json.loads(args.identity_json.read_text(encoding="utf-8")) if args.identity_json else None,
        "long_fixture_sha256": hashlib.sha256(args.long_fixture.read_bytes()).hexdigest(),
        "summary": {
            "long_context_exact": long_text == EXPECTED_LONG,
            "long_context_output": long_text,
            "long_context": pick("long_context")[0] if pick("long_context") else None,
            "decode_responses": [s["server"] | {"completion_tokens": s["completion_tokens"]} for s in pick("decode_responses")],
            "decode_chat_no_thinking": [s["server"] | {"completion_tokens": s["completion_tokens"]} for s in pick("decode_chat_no_thinking")],
            "session_continuations_losing_reuse": sum(
                1 for s in continuation_steps if not s["cached_tokens"] and (s["prompt_tokens"] or 0) > args.session_base_tokens // 2),
            "session_continuations": len(continuation_steps),
            "session_codes_exact": {s["desk"]: s.get("exact") for s in sessions},
            "fanout_branch_cached_tokens": [s["cached_tokens"] for s in pick("fanout_branch")],
            "agent_protocol": protocol,
            "explicit_saves": explicit_saves,
            "errors": errors,
        },
        "steps": steps,
        # What --resume-from continues after a restart: each session's newest stored response.
        "sessions": {label: {"session_sha256": lane.session, "newest_response_id": lane.newest}
                     for label, lane in clients.items() if lane.newest},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"receipt written: {args.receipt} errors={len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
