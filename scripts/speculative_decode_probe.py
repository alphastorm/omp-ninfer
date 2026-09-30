#!/usr/bin/env python3
"""Speculative decode probe: decode rate and draft acceptance by context length on one server arm.

Sends the same code-writing instruction behind 0 to about 120K tokens of an unrelated document,
continues the conversation at one of those lengths so the server can reuse its prefix, and can
run two requests decoding together. Every prompt starts with its own nonce, so no request reuses
another's prefix except the continuation. Requests are plain Chat Completions at temperature 0
with thinking off and no session identity, which the shipped runtime and upstream NInfer both
accept; one receipt per arm compares speculative backends on one binary, or runtimes on one
workload. Timings, acceptance and the server's startup capacities come from its own request-log
JSONL; outputs are recorded as SHA-256 only.

Example (on the appliance, against a window container on 127.0.0.1:18099):
  python3 speculative_decode_probe.py --arm up-d44ab584-df2k7 --base-url http://127.0.0.1:18099 \
    --api-key-file ~/services/ninfer-5090/secrets/api_key --long-fixture long_niah_128k.json \
    --log-cmd 'cat ~/services/engine-window/logs/up-d44ab584-df2k7/requests.jsonl' \
    --identity-json identity-up-d44ab584-df2k7.json --receipt receipts/up-d44ab584-df2k7-decode.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import http.client
import json
import secrets
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# The fixture's rendered prompt is 130,048 tokens (EXP-048); its document is English prose.
FIXTURE_PROMPT_TOKENS = 130048
INSTRUCTION = (
    "Write a complete, production-quality Python 3.12 module named ttl_cache.py: a thread-safe LRU "
    "cache with a per-entry time-to-live, a maximum total size in bytes, hit/miss/eviction "
    "statistics, and an argparse command-line interface that benchmarks it. After the module, "
    "write an exhaustive pytest test suite for it. Output only code, in two fenced blocks."
)
UNRELATED = "The document above is unrelated to this task; do not refer to it.\n\n"
CONTINUATION = (
    "Now add complete type hints and a docstring to every function and class in ttl_cache.py, "
    "and output the full revised module."
)
STARTUP_FIELDS = (
    ("engine", "max_concurrency"), ("engine", "speculative_backend"),
    ("engine", "speculative_draft_window"), ("engine", "kv_cache"), ("engine", "kv_capacity"),
    ("memory", "available_after_startup_bytes"), ("memory", "kv_payload_bytes"),
    ("memory", "cuda_graph_allowance_bytes"),
)


def document_text(fixture: Path) -> str:
    """The fixture's user document, without its leading instruction."""
    messages = json.loads(fixture.read_text(encoding="utf-8"))
    user = next(message["content"] for message in messages if message["role"] == "user")
    return user.split("\n\n", 1)[1]


def prompt(document: str, chars_per_token: float, context_tokens: int, nonce: str) -> str:
    head = f"Request {nonce}.\n\n"
    if context_tokens <= 0:
        return head + INSTRUCTION
    cut = document[: int(context_tokens * chars_per_token)]
    cut = cut[: cut.rfind("\n") + 1] or cut
    return f"{head}<document>\n{cut}</document>\n\n{UNRELATED}{INSTRUCTION}"


def chat(base_url: str, api_key: str, model: str, messages: list[dict[str, str]],
         max_tokens: int, timeout: float) -> dict[str, Any]:
    payload = {"model": model, "messages": messages, "max_completion_tokens": max_tokens,
               "temperature": 0, "reasoning_effort": "none"}
    request = urllib.request.Request(
        base_url.rstrip("/") + "/v1/chat/completions", data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    outcome: dict[str, Any] = {"submitted_unix_s": time.time()}
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            document = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        outcome.update(http_status=error.code, body=error.read().decode("utf-8", "replace")[:300])
        return outcome
    except (OSError, http.client.HTTPException) as error:
        outcome.update(http_status=None, error=f"{type(error).__name__}: {error}"[:300])
        return outcome
    usage = document.get("usage") or {}
    choice = (document.get("choices") or [{}])[0]
    text = (choice.get("message") or {}).get("content") or ""
    outcome.update(http_status=200, wall_s=round(time.monotonic() - started, 3),
                   completed_unix_s=time.time(), prompt_tokens=usage.get("prompt_tokens"),
                   completion_tokens=usage.get("completion_tokens"),
                   cached_tokens=(usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
                   finish_reason=choice.get("finish_reason"),
                   output_sha256=hashlib.sha256(text.encode()).hexdigest(), text=text)
    return outcome


def log_records(log_cmd: str) -> list[dict[str, Any]]:
    result = subprocess.run(log_cmd, shell=True, capture_output=True, text=True, timeout=300)
    records = []
    for line in result.stdout.splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def server_view(done: list[dict[str, Any]], outcome: dict[str, Any], used: set[int]) -> dict[str, Any]:
    """The first unused request_done record with this request's token shape."""
    for index, record in enumerate(done):
        result = record.get("result") or {}
        if index in used or result.get("prompt_tokens") != outcome.get("prompt_tokens") \
                or result.get("completion_tokens") != outcome.get("completion_tokens"):
            continue
        used.add(index)
        timings = record.get("timings_seconds") or {}
        speculative = record.get("speculative") or {}
        completion, computed = result.get("completion_tokens"), result.get("computed_prefill_tokens")
        prefill, decode = timings.get("prefill"), timings.get("decode")
        drafted, accepted, rounds = (speculative.get(key) for key in ("drafted_tokens", "accepted_tokens", "rounds"))
        return {
            "reuse": result.get("prefix_reuse_path"), "reused_tokens": result.get("prefix_cache_hit_tokens"),
            "computed_prefill_tokens": computed, "ttft_s": timings.get("ttft"), "prefill_s": prefill,
            "decode_s": decode, "rounds": rounds, "drafted_tokens": drafted, "accepted_tokens": accepted,
            "accepted_per_position": speculative.get("accepted_per_position"),
            "prefill_tok_s": round(computed / prefill, 1) if computed and prefill else None,
            "decode_tok_s": round(completion / decode, 2) if completion and decode else None,
            "draft_acceptance": round(accepted / drafted, 4) if drafted and accepted is not None else None,
            "tokens_per_round": round(completion / rounds, 3) if completion and rounds else None,
        }
    return {}


def startup(records: list[dict[str, Any]], since_unix_ms: int) -> dict[str, Any]:
    starts = [record for record in records if record.get("event") == "server_start"]
    if not starts:
        return {}
    newest = starts[-1]
    view = {f"{group}.{key}": (newest.get(group) or {}).get(key) for group, key in STARTUP_FIELDS}
    view["weights_used_bytes"] = ((newest.get("memory") or {}).get("weights") or {}).get("used_bytes")
    view["started_before_probe"] = int(newest.get("timestamp_unix_ms", 0)) < since_unix_ms
    return view


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--arm", required=True, help="receipt label for this server arm")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key-file", required=True, type=Path)
    parser.add_argument("--model", default="q38-ninfer")
    parser.add_argument("--long-fixture", required=True, type=Path, help="chat-messages JSON whose user document is the context")
    parser.add_argument("--contexts", default="0,32000,64000,120000", help="comma-separated context lengths, approximate tokens")
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--continuation-context", type=int, default=64000, help="continue the request at this context; -1 skips")
    parser.add_argument("--continuation-tokens", type=int, default=1024)
    parser.add_argument("--pair", action="store_true", help="also run two short-context requests together")
    parser.add_argument("--pair-tokens", type=int, default=1024)
    parser.add_argument("--timeout", type=float, default=1800.0, help="per request, seconds")
    parser.add_argument("--log-cmd", required=True, help="shell command printing the arm's request JSONL")
    parser.add_argument("--identity-json", type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args(argv)
    contexts = [int(value) for value in args.contexts.split(",") if value.strip()]
    if args.continuation_context >= 0 and args.continuation_context not in contexts:
        parser.error("--continuation-context must be one of --contexts, or -1")

    api_key = args.api_key_file.read_text(encoding="utf-8").strip()
    document = document_text(args.long_fixture)
    chars_per_token = len(document) / FIXTURE_PROMPT_TOKENS
    since_ms = int(time.time() * 1000)
    steps: list[dict[str, Any]] = []

    def run(label: str, messages: list[dict[str, str]], max_tokens: int) -> dict[str, Any]:
        outcome = {"step": label, **chat(args.base_url, api_key, args.model, messages, max_tokens, args.timeout)}
        printable = {key: value for key, value in outcome.items() if key != "text"}
        print(f"{label:>24}: {json.dumps(printable)}", flush=True)
        steps.append(outcome)
        return outcome

    for context in contexts:
        messages = [{"role": "user", "content": prompt(document, chars_per_token, context, secrets.token_hex(8))}]
        outcome = run(f"context-{context}", messages, args.max_tokens)
        if context == args.continuation_context and outcome.get("http_status") == 200:
            run(f"continuation-{context}", messages + [
                {"role": "assistant", "content": outcome["text"]}, {"role": "user", "content": CONTINUATION}],
                args.continuation_tokens)

    pair: dict[str, Any] | None = None
    if args.pair:
        results: list[dict[str, Any]] = []
        lock = threading.Lock()

        def pair_request(index: int) -> None:
            messages = [{"role": "user", "content": prompt(document, chars_per_token, 0, secrets.token_hex(8))}]
            outcome = {"step": f"pair-{index}", **chat(args.base_url, api_key, args.model, messages,
                                                        args.pair_tokens, args.timeout)}
            with lock:
                results.append(outcome)

        threads = [threading.Thread(target=pair_request, args=(index,)) for index in (1, 2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        results.sort(key=lambda outcome: outcome["step"])
        for outcome in results:
            print(f"{outcome['step']:>24}: {json.dumps({k: v for k, v in outcome.items() if k != 'text'})}", flush=True)
        steps.extend(results)
        ok = [outcome for outcome in results if outcome.get("http_status") == 200]
        if len(ok) == 2:
            span = max(o["completed_unix_s"] for o in ok) - min(o["submitted_unix_s"] for o in ok)
            tokens = sum(o["completion_tokens"] or 0 for o in ok)
            pair = {"completion_tokens": tokens, "span_s": round(span, 3),
                    "client_aggregate_tok_s": round(tokens / span, 2) if span > 0 else None}

    time.sleep(2.0)
    records = log_records(args.log_cmd)
    done = [record for record in records if record.get("event") == "request_done"
            and int(record.get("timestamp_unix_ms", 0)) >= since_ms]
    used: set[int] = set()
    for outcome in steps:
        if outcome.get("http_status") == 200:
            outcome["server"] = server_view(done, outcome, used)
        outcome.pop("text", None)
    if pair is not None:
        views = [o.get("server") or {} for o in steps if o["step"].startswith("pair-")]
        pair["server_decode_tok_s"] = [view.get("decode_tok_s") for view in views]

    receipt = {
        "artifact_type": "omp_ninfer_speculative_decode_probe",
        "schema_version": 1,
        "arm": args.arm,
        "generated_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "long_fixture_sha256": hashlib.sha256(args.long_fixture.read_bytes()).hexdigest(),
        "instruction_sha256": hashlib.sha256(INSTRUCTION.encode()).hexdigest(),
        "identity": json.loads(args.identity_json.read_text(encoding="utf-8")) if args.identity_json else None,
        "server_start": startup(records, since_ms),
        "steps": steps,
        "pair": pair,
        "raw_prompts_outputs_or_secrets_included": False,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    failed = [outcome["step"] for outcome in steps if outcome.get("http_status") != 200]
    print(f"receipt: {args.receipt}; failed steps: {failed or 'none'}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
