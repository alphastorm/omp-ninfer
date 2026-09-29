#!/usr/bin/env python3
"""Measure one RTX 5090 window arm; run unchanged against C1 and C2 and compare receipts.

Run on the appliance beside engine_window_compare.py (Python 3.12, stdlib only):
  python3 concurrency_probe.py --arm C2 --api-key-file ~/services/ninfer-5090/secrets/api_key \
    --scenario decode_pair --repeat 3 --receipt c2-decode-pair.json

The default URL is the window arm, http://127.0.0.1:18099. This tool does not change
server concurrency or operate containers. Only an explicitly supplied
--kill-during-decode shell command can stop/restart a server. For a manual restart,
run --scenario restart --phase seed, restart the arm, then run --scenario restart
--phase resume --resume-from seed.json with a different --receipt path.

All eight scenarios run unless --scenario is supplied (repeatable). FILLER token
sizes use engine_window_compare's word-count estimate, not a tokenizer; usage is
the authoritative size. --long-fixture accepts its chat-messages JSON fixture and
replaces only the long B input in the two prefill scenarios. Other long workloads
keep their distinct ledgers, and fanout keeps fleet_probe's exact construction.

TTFT starts at submit and ends at the first text OR reasoning delta, never at
response.created. Delta gaps are inter-output-event latency: an SSE delta can
contain multiple tokens, especially with MTP. Decode tok/s is usage.output_tokens
/ (last delta - first delta); aggregate tok/s includes prefill and queue time.
Percentiles use linear interpolation. Output-text and reasoning digests are
separate. No prompt, output, or credential text is retained in a receipt.
Receipts retain every output-event timestamp and each phase summary, including
unsuccessful peers. --log-cmd attaches only request_done events inside the run
window and joins prefix_reuse_path by ninfer_request_id, never by token counts.
--vram-cmd must print one GPU's used MiB as its first line (for example nvidia-smi
--query-gpu=memory.used --format=csv,noheader,nounits --id=0).

A reset is retried once, after two seconds, only before any SSE event is received:
replaying an accepted stream could duplicate a stored turn. --timeout is a total
per-request deadline, including a retry. Fail-fast stops subsequent batches, not
already in-flight peers. Intentional restart interruption failures are recorded
but do not prevent the subsequent restore measurement. A restart seed receipt is
written before the interruption command, preserving the last completed heads.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import errno
import hashlib
import http.client
import json
import math
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine_window_compare import (  # noqa: E402
    DECODE_PROMPT, FILLER, RESUME_OUTPUT_TOKENS, now, session_digest, usage_of,
)

SCENARIOS = ("solo", "decode_pair", "prefill_during_decode", "decode_during_prefill",
             "two_sessions", "fanout", "restart", "near_capacity")
SECOND_DECODE_PROMPT = (
    "Write an exhaustive technical design for a distributed build scheduler. Cover dependency "
    "graphs, fair admission, worker leases, cancellation, retries, artifact publication, and "
    "recovery after coordinator failure. Include concrete pseudocode and failure analysis."
)
DELTA_EVENTS = {"response.output_text.delta": "text", "response.reasoning_text.delta": "reasoning"}
TERMINAL_EVENTS = {"response.completed", "response.incomplete", "response.cancelled", "response.failed"}
PRIVATE_FIELDS = {"api_key", "authorization", "x-api-key", "input", "prompt", "messages",
                  "output", "content", "text", "delta", "instructions"}


def utc() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def digest(value: str | bytes) -> str:
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def redact(value: Any, secrets: tuple[str, ...], external: bool = False) -> Any:
    """External structured content is hashed; known credentials/inputs are scrubbed everywhere."""
    if isinstance(value, dict):
        return {key: ({"redacted_sha256": digest(json.dumps(item, sort_keys=True))}
                      if external and key.lower() in PRIVATE_FIELDS else redact(item, secrets, external))
                for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item, secrets, external) for item in value]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[REDACTED]")
    return value


def safe_body(body: str, secrets: tuple[str, ...]) -> str:
    try:
        return json.dumps(redact(json.loads(body), secrets, external=True), ensure_ascii=False)
    except json.JSONDecodeError:
        return redact(body, secrets)


def input_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [text for item in value for text in input_strings(item)]
    if isinstance(value, dict):
        return [text for key, item in value.items() if key in ("input", "content", "text")
                for text in input_strings(item)]
    return []


def percentiles(values: list[float]) -> dict[str, float | None]:
    ordered = sorted(values)
    def at(q: float) -> float | None:
        if not ordered:
            return None
        index = (len(ordered) - 1) * q
        lo, hi = math.floor(index), math.ceil(index)
        return ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo)
    return {"p50": at(.50), "p95": at(.95), "p99": at(.99), "max": max(ordered) if ordered else None}


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    timed = [r for r in records if r.get("submitted_monotonic_s") is not None]
    makespan = (max(r["completed_monotonic_s"] for r in timed)
                - min(r["submitted_monotonic_s"] for r in timed)) if timed else None
    tokens = sum(r.get("output_tokens") or 0 for r in records)
    rates = [r["decode_tok_s"] for r in records if r.get("ok") and r.get("decode_tok_s") is not None]
    return {
        "requests": len(records), "succeeded": sum(bool(r.get("ok")) for r in records),
        "failed": sum(not r.get("ok", False) for r in records),
        "output_tokens": tokens, "token_accounting_complete": all(r.get("output_tokens") is not None for r in records),
        "makespan_s": makespan, "aggregate_tok_s": tokens / makespan if makespan else None,
        "fairness": min(rates) / max(rates) if len(rates) >= 2 and len(rates) == len(records) and max(rates) else None,
        "per_request": [{k: r.get(k) for k in (
            "label", "finish_status", "http_status", "ttft_s", "total_s", "decode_tok_s",
            "prompt_tokens", "output_tokens", "cached_tokens", "reasoning_tokens", "itl_ms",
            "output_text_sha256", "reasoning_text_sha256")} for r in records],
    }


class Progress:
    def __init__(self) -> None:
        self.condition = threading.Condition()
        self.submitted: float | None = None
        self.deltas = 0
        self.finished = False

    def update(self, *, submitted: float | None = None, delta: bool = False, finished: bool = False) -> None:
        with self.condition:
            if submitted is not None:
                self.submitted = submitted
            self.deltas += int(delta)
            self.finished = finished
            self.condition.notify_all()

    def wait_deltas(self, count: int) -> bool:
        with self.condition:
            self.condition.wait_for(lambda: self.deltas >= count or self.finished)
            return self.deltas >= count and not self.finished

    def wait_submitted(self) -> float | None:
        with self.condition:
            self.condition.wait_for(lambda: self.submitted is not None or self.finished)
            return self.submitted


def sse_events(response: http.client.HTTPResponse):
    name, data = "", []
    while True:
        line = response.readline()
        if line in (b"\n", b"\r\n", b""):
            if data:
                text = "\n".join(data)
                if text != "[DONE]":
                    event = json.loads(text)
                    if not isinstance(event, dict):
                        raise ValueError("SSE data is not an object")
                    yield name or event.get("type", ""), event, now()
            name, data = "", []
            if not line:
                return
        else:
            field, _, value = line.decode("utf-8").rstrip("\r\n").partition(":")
            value = value.removeprefix(" ")
            if field == "event":
                name = value
            elif field == "data":
                data.append(value)


def stream_request(args: argparse.Namespace, api_key: str, spec: dict[str, Any],
                   progress: Progress, barrier: threading.Barrier) -> dict[str, Any]:
    record: dict[str, Any] = {
        "label": spec["label"], "session_sha256": spec["session"],
        "request_sha256": session_digest(spec["label"]), "previous_response_id": spec.get("previous"),
        "input_sha256": digest(json.dumps(spec["input"], sort_keys=True)),
        "max_output_tokens": spec["max_output"], "store": spec.get("store", True),
        "expected_interruption": spec.get("expected_interruption", False),
        "submitted_monotonic_s": None, "first_output_monotonic_s": None,
        "last_output_monotonic_s": None, "completed_monotonic_s": None,
        "response_id": None, "finish_status": "skipped", "http_status": None,
        "usage": None, "output_deltas": [], "attempts": [], "ok": False,
    }
    payload = {"model": args.model, "input": spec["input"], "temperature": 0,
               "stream": True, "store": record["store"], "max_output_tokens": spec["max_output"],
               "ninfer_session": spec["session"], "ninfer_request_id": record["request_sha256"]}
    if spec.get("previous"):
        payload["previous_response_id"] = spec["previous"]
    data = json.dumps(payload).encode()
    secrets = (api_key, *input_strings(spec["input"]))
    text_hash, reasoning_hash = hashlib.sha256(), hashlib.sha256()
    endpoint = urllib.parse.urlsplit(args.base_url)
    connection_type = http.client.HTTPSConnection if endpoint.scheme == "https" else http.client.HTTPConnection
    received_event = False
    try:
        barrier.wait()
        if spec.get("gate") and not spec["gate"]():
            record["error"] = "submission trigger was not reached while the peer was in flight"
            return record
        record["submitted_monotonic_s"] = now()
        record["submitted_utc"] = utc()
        progress.update(submitted=record["submitted_monotonic_s"])
        deadline = record["submitted_monotonic_s"] + args.timeout
        for attempt in range(2):
            remaining = deadline - now()
            if remaining <= 0:
                record.update(finish_status="timeout", error="request deadline exceeded")
                break
            connection = connection_type(endpoint.hostname, endpoint.port, timeout=remaining)
            expired = threading.Event()
            timer = None
            attempt_record: dict[str, Any] = {"submitted_monotonic_s": now()}
            retry = False
            try:
                connection.connect()
                sock = connection.sock
                def expire(sock=sock, expired=expired) -> None:
                    expired.set()
                    try:
                        sock.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                timer = threading.Timer(max(0, deadline - now()), expire)
                timer.daemon = True
                timer.start()
                connection.request("POST", endpoint.path.rstrip("/") + "/v1/responses", body=data, headers={
                    "Authorization": f"Bearer {api_key}", "X-NInfer-Session": spec["session"],
                    "Content-Type": "application/json", "Accept": "text/event-stream",
                })
                response = connection.getresponse()
                record["http_status"] = response.status
                attempt_record["http_status"] = response.status
                if response.status >= 400:
                    record.update(finish_status="http_error", http_error_body=safe_body(
                        response.read().decode("utf-8", "replace"), secrets))
                    break
                if response.getheader("Content-Type", "").split(";")[0].strip() != "text/event-stream":
                    record.update(finish_status="protocol_error", error="expected text/event-stream",
                                  http_error_body=safe_body(response.read().decode("utf-8", "replace"), secrets))
                    break
                for name, event, timestamp in sse_events(response):
                    received_event = True
                    document = event.get("response") or {}
                    if document.get("id"):
                        record["response_id"] = document["id"]
                    if name in DELTA_EVENTS and event.get("delta"):
                        kind = DELTA_EVENTS[name]
                        (text_hash if kind == "text" else reasoning_hash).update(event["delta"].encode())
                        record["output_deltas"].append({"kind": kind, "monotonic_s": timestamp})
                        progress.update(delta=True)
                    if name in TERMINAL_EVENTS:
                        record.update(completed_monotonic_s=timestamp, terminal_event=name,
                                      finish_status=document.get("status", name.removeprefix("response.")),
                                      usage=document.get("usage"))
                        if document.get("error"):
                            record["error"] = redact(document["error"], secrets, external=True)
                        if document.get("incomplete_details"):
                            record["incomplete_details"] = document["incomplete_details"]
                        record["ok"] = record["finish_status"] in ("completed", "incomplete") and not document.get("error")
                        break
                if not record.get("terminal_event"):
                    record.update(finish_status="timeout" if expired.is_set() else "truncated",
                                  error="request deadline exceeded" if expired.is_set() else "stream ended without a terminal event")
                break
            except Exception as error:  # A peer failure must not discard the other request's evidence.
                timed_out = expired.is_set() or isinstance(error, TimeoutError) or now() >= deadline
                record.update(finish_status="timeout" if timed_out else "transport_error",
                              error=redact(f"{type(error).__name__}: {error}", secrets))
                attempt_record["error"] = record["error"]
                reset = isinstance(error, (http.client.RemoteDisconnected, ConnectionResetError)) or (
                    isinstance(error, OSError) and error.errno == errno.ECONNRESET)
                retry = attempt == 0 and reset and not received_event and not timed_out and deadline - now() > 2
                if not retry:
                    break
            finally:
                if timer is not None:
                    timer.cancel()
                connection.close()
                attempt_record["completed_monotonic_s"] = now()
                record["attempts"].append(attempt_record)
            if retry:
                time.sleep(2)
                record.pop("error", None)
    finally:
        record["completed_monotonic_s"] = record["completed_monotonic_s"] or now()
        record["completed_utc"] = utc()
        timestamps = [d["monotonic_s"] for d in record["output_deltas"]]
        record["first_output_monotonic_s"] = timestamps[0] if timestamps else None
        record["last_output_monotonic_s"] = timestamps[-1] if timestamps else None
        submitted = record["submitted_monotonic_s"]
        record["ttft_s"] = timestamps[0] - submitted if timestamps and submitted is not None else None
        record["total_s"] = record["completed_monotonic_s"] - submitted if submitted is not None else None
        gaps = [(b - a) * 1000 for a, b in zip(timestamps, timestamps[1:])]
        record["itl_gaps_ms"], record["itl_ms"] = gaps, percentiles(gaps)
        prompt, completion, cached = usage_of({"usage": record["usage"]})
        record.update(prompt_tokens=prompt, output_tokens=completion, cached_tokens=cached,
                      reasoning_tokens=((record["usage"] or {}).get("output_tokens_details") or {}).get("reasoning_tokens"))
        duration = timestamps[-1] - timestamps[0] if len(timestamps) >= 2 else 0
        record["decode_tok_s"] = completion / duration if completion is not None and duration > 0 else None
        record["output_text_sha256"], record["reasoning_text_sha256"] = text_hash.hexdigest(), reasoning_hash.hexdigest()
        progress.update(finished=True)
    return record


def long_input(tokens: int, desk: str, *, fanout: bool = False) -> list[dict[str, Any]]:
    if fanout:
        corpus = "".join("Operations ledger entry %d: throughput nominal, cache warm, retrieval verified. " % entry
                         for entry in range(max(1, (tokens * 3 // 4) // 11)))
        prefix = "Hold this operations ledger in context for later analysis; reply OK only.\n"
    else:
        corpus = "".join(FILLER % (entry, desk)
                         for entry in range(max(1, (tokens * 3 // 4) // len(FILLER.split()))))
        prefix = f"Hold this operations ledger for desk {desk} in context for later analysis; reply OK only.\n"
    return [{"role": "user", "content": [{"type": "input_text", "text": prefix + corpus}]}]


def fixture_input(path: Path) -> Any:
    messages = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(messages, list):
        raise ValueError("long fixture must be a chat-messages JSON array")
    return [{"role": message["role"], "content": [
        {"type": "input_text", "text": message["content"]}]} for message in messages]


def run_command(command: str, timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)


class VramSampler:
    def __init__(self, command: str | None) -> None:
        self.command = command
        self.stop = threading.Event()
        self.samples: list[dict[str, Any]] = []
        self.thread = threading.Thread(target=self.sample, daemon=True)

    def sample(self) -> None:
        while not self.stop.is_set():
            started = now()
            sample: dict[str, Any] = {"monotonic_s": started, "utc": utc()}
            try:
                result = run_command(self.command, 10)
                if result.returncode:
                    raise ValueError(f"VRAM command exited {result.returncode}")
                value = float(result.stdout.strip().splitlines()[0])
                if not math.isfinite(value) or value < 0:
                    raise ValueError("VRAM command must print nonnegative used MiB")
                sample["used_mib"] = value
            except (OSError, subprocess.SubprocessError, ValueError, IndexError) as error:
                sample["error"] = str(error)
            self.samples.append(sample)
            self.stop.wait(max(0, 1 - (now() - started)))

    def start(self) -> None:
        if self.command:
            self.thread.start()

    def finish(self) -> dict[str, Any]:
        if self.command:
            self.stop.set()
            self.thread.join()
        values = [s["used_mib"] for s in self.samples if "used_mib" in s]
        return {"peak_mib": max(values) if values else None, "samples": self.samples}


class ProbeFailure(Exception):
    pass


class Probe:
    def __init__(self, args: argparse.Namespace, api_key: str, receipt: dict[str, Any]) -> None:
        self.args, self.api_key, self.receipt = args, api_key, receipt
        self.result: dict[str, Any] = {}
        self.resume_sessions = (json.loads(args.resume_from.read_text(encoding="utf-8"))["sessions"]
                                if args.resume_from else None)
        self.fixture = fixture_input(args.long_fixture) if args.long_fixture else None

    def save(self) -> None:
        self.args.receipt.parent.mkdir(parents=True, exist_ok=True)
        self.args.receipt.write_text(json.dumps(redact(self.receipt, (self.api_key,)), indent=2) + "\n", encoding="utf-8")

    def spec(self, label: str, text: Any, tokens: int, session: str | None = None,
             previous: str | None = None, **options: Any) -> dict[str, Any]:
        return {"label": label, "input": text, "max_output": tokens,
                "session": session or session_digest(label), "previous": previous, **options}

    def batch(self, specs: list[dict[str, Any]], phase: str,
              action: Callable[[list[Progress]], None] | None = None) -> list[dict[str, Any]]:
        progress = [Progress() for _ in specs]
        for spec in specs:
            if "gate_factory" in spec:
                spec["gate"] = spec["gate_factory"](progress)
        barrier = threading.Barrier(len(specs))
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(specs)) as pool:
            futures = [pool.submit(stream_request, self.args, self.api_key, spec, state, barrier)
                       for spec, state in zip(specs, progress)]
            action_error = None
            try:
                if action:
                    action(progress)
            except Exception as error:
                action_error = error
            records = [future.result() for future in futures]
        for record in records:
            record["phase"] = phase
        self.result["requests"].extend(records)
        self.result["phases"].append({"name": phase, "summary": summarize(records)})
        if action_error:
            raise action_error
        if self.args.fail_fast and any(not r["ok"] and not r["expected_interruption"] for r in records):
            raise ProbeFailure(f"request failed in {phase}")
        return records

    def seed_pair(self, tokens: int, phase: str = "seed") -> list[dict[str, Any]]:
        return self.batch([self.spec(f"{phase}-{desk}", long_input(tokens, desk), 64)
                           for desk in ("D1", "D2")], phase)

    def continue_pair(self, sessions: dict[str, Any], phase: str) -> list[dict[str, Any]]:
        if len(sessions) != 2:
            raise ProbeFailure("continuation requires two successfully seeded sessions")
        return self.batch([self.spec(f"{phase}-{label}", "Summarize ledger entry 3 in six words.",
                                    RESUME_OUTPUT_TOKENS, state["session_sha256"], state["newest_response_id"])
                           for label, state in sessions.items()], phase)

    @staticmethod
    def heads(records: list[dict[str, Any]]) -> dict[str, Any]:
        return {f"session-D{index + 1}": {"session_sha256": r["session_sha256"],
                                         "newest_response_id": r["response_id"]}
                for index, r in enumerate(records) if r["ok"] and r["response_id"]}

    def inspect(self, path: str, timeout: float = 10) -> dict[str, Any]:
        request = urllib.request.Request(self.args.base_url.rstrip("/") + path,
                                         headers={"Authorization": f"Bearer {self.api_key}"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return {"http_status": response.status, "body": redact(json.loads(response.read()),
                                                                         (self.api_key,), external=True)}
        except urllib.error.HTTPError as error:
            return {"http_status": error.code, "body": safe_body(error.read().decode("utf-8", "replace"), (self.api_key,))}
        except (OSError, ValueError) as error:
            return {"error": redact(str(error), (self.api_key,))}

    def restart(self) -> None:
        args = self.args
        if args.phase == "resume":
            records = self.continue_pair(self.resume_sessions or {}, "resume")
            self.resume_sessions = self.heads(records)
            self.receipt["sessions"] = self.resume_sessions
            self.result["sessions"] = self.resume_sessions
            return
        seeds = self.seed_pair(args.session_tokens)
        sessions = self.heads(seeds)
        self.result["sessions"] = sessions
        self.receipt["sessions"] = sessions
        self.save()  # Persist completed heads before the operator-supplied interruption.
        if not args.kill_during_decode:
            return
        if len(sessions) != 2:
            raise ProbeFailure("restart interruption requires two successful seed responses")
        command_result: dict[str, Any] = {}
        self.result["restart_command"] = command_result
        def interrupt(progress: list[Progress]) -> None:
            if not all(state.wait_deltas(32) for state in progress) or any(state.finished for state in progress):
                raise ProbeFailure("both requests did not reach 32 deltas while in flight; restart command not executed")
            command_result["started_monotonic_s"] = now()
            completed = run_command(args.kill_during_decode, args.health_timeout)
            command_result.update(returncode=completed.returncode, stdout_sha256=digest(completed.stdout),
                                  stderr_sha256=digest(completed.stderr), completed_monotonic_s=now())
            if completed.returncode:
                raise ProbeFailure(f"restart command exited {completed.returncode}")
        self.batch([self.spec(f"interrupted-{label}", DECODE_PROMPT, args.decode_tokens,
                              state["session_sha256"], state["newest_response_id"],
                              store=False, expected_interruption=True) for label, state in sessions.items()],
                   "interrupted_decode", interrupt)
        deadline = now() + args.health_timeout
        while now() < deadline:
            health = self.inspect("/health", min(5, deadline - now()))
            if health.get("http_status") == 200 and health.get("body", {}).get("status") == "ok":
                self.result["health_after_restart"] = health
                break
            time.sleep(min(1, max(0, deadline - now())))
        else:
            raise ProbeFailure("server did not become healthy after the restart command")
        resumed = self.continue_pair(sessions, "resume")
        self.result["resumed_sessions"] = self.heads(resumed)
        self.receipt["sessions"] = self.heads(resumed)

    def scenario(self, name: str, repeat: int) -> dict[str, Any]:
        args = self.args
        result = self.result = {"name": name, "repeat": repeat, "started_utc": utc(),
                                "started_monotonic_s": now(), "requests": [], "phases": []}
        self.receipt["scenarios"].append(result)
        sampler = VramSampler(args.vram_cmd)
        sampler.start()
        try:
            if name == "solo":
                self.batch([self.spec("solo", DECODE_PROMPT, args.decode_tokens, store=False)], "decode")
            elif name == "decode_pair":
                self.batch([self.spec("decode-A", DECODE_PROMPT, args.decode_tokens, store=False),
                            self.spec("decode-B", SECOND_DECODE_PROMPT, args.decode_tokens, store=False)], "decode")
            elif name == "prefill_during_decode":
                records = self.batch([
                    self.spec("decode-A", DECODE_PROMPT, args.decode_tokens, store=False),
                    self.spec("prefill-B", self.fixture or long_input(args.prefill_tokens, "B"), 32,
                              store=False, gate_factory=lambda states: lambda: states[0].wait_deltas(args.stall_after)),
                ], "interference")
                a, b = records
                start, end = b["submitted_monotonic_s"], b["first_output_monotonic_s"]
                stamps = [d["monotonic_s"] for d in a["output_deltas"]]
                result["interference"] = {
                    "prefill_window_definition": "B submit through B first output (includes queueing)",
                    "b_prefill_window_monotonic_s": [start, end], "b_ttft_s": b["ttft_s"],
                    "a_itl_max_ms": a["itl_ms"]["max"],
                    "a_gaps_overlapping_b_prefill": [
                        {"start_monotonic_s": x, "end_monotonic_s": y, "gap_ms": (y - x) * 1000,
                         "overlap_ms": (min(y, end) - max(x, start)) * 1000}
                        for x, y in zip(stamps, stamps[1:])
                        if start is not None and end is not None and x < end and y > start],
                }
            elif name == "decode_during_prefill":
                def delayed(states: list[Progress]) -> Callable[[], bool]:
                    def gate() -> bool:
                        submitted = states[0].wait_submitted()
                        if submitted is None:
                            return False
                        time.sleep(max(0, submitted + 1 - now()))
                        return True
                    return gate
                b, a = self.batch([
                    self.spec("prefill-B", self.fixture or long_input(args.prefill_tokens, "B"), 32, store=False),
                    self.spec("decode-A", DECODE_PROMPT, 256, store=False, gate_factory=delayed),
                ], "interference")
                result["interference"] = {"a_ttft_s": a["ttft_s"], "a_total_s": a["total_s"],
                                          "b_first_output_monotonic_s": b["first_output_monotonic_s"]}
            elif name == "two_sessions":
                heads = self.heads(self.seed_pair(args.session_tokens))
                for turn in range(args.turns):
                    records = self.continue_pair(heads, f"turn-{turn + 1}")
                    # A failed turn leaves its last completed head available to the next round.
                    for label, state in self.heads(records).items():
                        heads[label] = state
                result["sessions"] = heads
            elif name == "fanout":
                base = self.batch([self.spec("fanout-base", long_input(args.fanout_base_tokens, "", fanout=True), 40)], "base")[0]
                if not base["ok"] or not base["response_id"]:
                    raise ProbeFailure("fanout base failed")
                for offset in range(0, args.branches, args.fanout_concurrency):
                    self.batch([self.spec(f"branch-{index}", f"Branch role {index}: summarize entry {index + 5} in six words.",
                                          80, base["session_sha256"], base["response_id"])
                                for index in range(offset, min(args.branches, offset + args.fanout_concurrency))], "branches")
            elif name == "restart":
                self.restart()
            elif name == "near_capacity":
                self.seed_pair(args.large_tokens, "capacity")
        except Exception as error:
            result["error"] = redact(f"{type(error).__name__}: {error}", (self.api_key,))
        finally:
            result["finished_monotonic_s"], result["finished_utc"] = now(), utc()
            result["vram"] = sampler.finish()
            result["summary"] = summarize(result["requests"])
            result["ok"] = not result.get("error") and all(r["ok"] or r["expected_interruption"] for r in result["requests"])
        return result

    def attach_logs(self, since_ms: int, until_ms: int) -> None:
        self.receipt["request_log_window_unix_ms"] = [since_ms, until_ms]
        self.receipt["request_done"] = []
        if not self.args.log_cmd:
            return
        try:
            fetched = run_command(self.args.log_cmd, 300)
            if fetched.returncode:
                raise ProbeFailure(f"log command exited {fetched.returncode}")
            for line in fetched.stdout.splitlines():
                try:
                    record = json.loads(line)
                    if (record.get("event") == "request_done"
                            and since_ms <= int(record.get("timestamp_unix_ms", 0)) <= until_ms):
                        self.receipt["request_done"].append(redact(record, (self.api_key,), external=True))
                except (ValueError, TypeError, AttributeError):
                    continue
            for scenario in self.receipt["scenarios"]:
                for request in scenario["requests"]:
                    matches = [record for record in self.receipt["request_done"]
                               if (record.get("request", {}).get("client_identity") or {}).get("request_sha256") == request["request_sha256"]]
                    request["server_request_done"] = matches
                    if len(matches) == 1:
                        request["prefix_reuse_path"] = matches[0].get("result", {}).get("prefix_reuse_path")
        except (OSError, subprocess.SubprocessError, ProbeFailure) as error:
            self.receipt["log_error"] = redact(str(error), (self.api_key,))


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be finite and positive")
    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--arm", default="unlabelled", help="receipt label, e.g. C1 or C2")
    parser.add_argument("--base-url", default="http://127.0.0.1:18099")
    parser.add_argument("--api-key-file", required=True, type=Path)
    parser.add_argument("--model", default="q38-ninfer")
    parser.add_argument("--identity-json", type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--scenario", choices=SCENARIOS, action="append", help="repeatable; default: all; with --resume-from: restart")
    parser.add_argument("--repeat", type=positive_int, default=1)
    parser.add_argument("--timeout", type=positive_float, default=1800, help="total deadline per request, seconds")
    parser.add_argument("--decode-tokens", type=positive_int, default=1024)
    parser.add_argument("--stall-after", type=positive_int, default=64)
    parser.add_argument("--prefill-tokens", type=positive_int, default=60000)
    parser.add_argument("--session-tokens", type=positive_int, default=50000)
    parser.add_argument("--turns", type=positive_int, default=2)
    parser.add_argument("--fanout-base-tokens", type=positive_int, default=67700)
    parser.add_argument("--branches", type=positive_int, default=4)
    parser.add_argument("--fanout-concurrency", type=positive_int, default=2)
    parser.add_argument("--large-tokens", type=positive_int, default=100000)
    parser.add_argument("--long-fixture", type=Path, help="chat-messages JSON for B in the prefill scenarios")
    parser.add_argument("--phase", choices=("seed", "resume"), help="restart phase; inferred from --resume-from")
    parser.add_argument("--resume-from", type=Path)
    parser.add_argument("--kill-during-decode", metavar="CMD", help="explicit stop/start shell command, after both sessions stream 32 deltas")
    parser.add_argument("--health-timeout", type=positive_float, default=300, help="restart command and subsequent health-wait deadlines")
    parser.add_argument("--vram-cmd", metavar="CMD", help="shell command printing one GPU's used MiB; sampled every second")
    parser.add_argument("--log-cmd", metavar="CMD", help="shell command printing request JSONL after the run")
    parser.add_argument("--fail-fast", action="store_true")
    args = parser.parse_args(argv)
    args.scenario = args.scenario or (["restart"] if args.resume_from else list(SCENARIOS))
    args.phase = args.phase or ("resume" if args.resume_from else "seed")
    endpoint = urllib.parse.urlsplit(args.base_url)
    if endpoint.scheme not in ("http", "https") or not endpoint.hostname or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
        parser.error("--base-url must be an HTTP(S) server URL without credentials, query, or fragment")
    if args.phase == "resume" and not args.resume_from:
        parser.error("--phase resume requires --resume-from")
    if args.resume_from and args.phase != "resume":
        parser.error("--resume-from requires --phase resume")
    if args.kill_during_decode and (args.phase != "seed" or "restart" not in args.scenario):
        parser.error("--kill-during-decode requires the restart seed scenario")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    api_key = args.api_key_file.read_text(encoding="utf-8").strip()
    if not api_key:
        raise ValueError("API key file is empty")
    started_ms = int(time.time() * 1000)
    receipt: dict[str, Any] = {
        "artifact_type": "omp_ninfer_concurrency_probe", "schema_version": 1, "tool": "concurrency_probe",
        "started_utc": utc(), "finished_utc": None,
        "arguments": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
        "identity": {"operator": redact(json.loads(args.identity_json.read_text(encoding="utf-8")), (api_key,), external=True)
                     if args.identity_json else None},
        "scenarios": [], "sessions": {},
    }
    if args.long_fixture:
        receipt["long_fixture_sha256"] = digest(args.long_fixture.read_bytes())
    if args.resume_from:
        receipt["resumed_from_sha256"] = digest(args.resume_from.read_bytes())
    probe = Probe(args, api_key, receipt)
    receipt["identity"]["health_before"] = probe.inspect("/health")
    receipt["identity"]["server_before"] = probe.inspect("/v1/ninfer/status")
    try:
        for name in args.scenario:
            for repeat in range(1, args.repeat + 1):
                result = probe.scenario(name, repeat)
                print(f"{name} repeat={repeat} ok={result['ok']} "
                      f"aggregate_tok_s={result['summary']['aggregate_tok_s']} failures={result['summary']['failed']}", flush=True)
                probe.save()
                if args.fail_fast and not result["ok"]:
                    raise ProbeFailure("fail-fast stopped subsequent scenarios")
    except ProbeFailure as error:
        receipt["error"] = str(error)
    finally:
        until_ms = int(time.time() * 1000)
        receipt["identity"]["health_after"] = probe.inspect("/health")
        receipt["identity"]["server_after"] = probe.inspect("/v1/ninfer/status")
        probe.attach_logs(started_ms, until_ms)
        receipt["finished_utc"] = utc()
        receipt["ok"] = not receipt.get("error") and not receipt.get("log_error") and all(s["ok"] for s in receipt["scenarios"])
        probe.save()
    print(f"receipt written: {args.receipt}")
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
