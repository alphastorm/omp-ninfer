#!/usr/bin/env python3
"""Run and reduce the privacy-safe MTP depth ablation corpus."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

ARMS = (0, 3, 5, 7)
CORPUS_VERSION = 3
REPETITIONS = 2
RUN_ARTIFACT_TYPE = "omp_ninfer_mtp_ablation_run"
ARM_ARTIFACT_TYPE = "omp_ninfer_mtp_ablation_arm"
LANE_ARTIFACT_TYPE = "omp_ninfer_mtp_ablation_lane"
SCHEMA_VERSION = 1
CONFIGURATION_SCHEMA_VERSION = 2
ANALYSIS_VERSION = 4
PROMOTION_MARGIN = 0.05
CORPUS_STEP_NAMES = {
    "responses_short": ("single",),
    "responses_long_decode": ("single",),
    "chat_history_p50": ("single",),
    "chat_history_p90": ("single",),
    "chat_tool_roundtrip": ("tool_call", "tool_result"),
    "responses_medium_branch": ("base", "continuation", "branch"),
    "responses_long_replay": ("base", "continuation", "branch"),
}
EXPECTED_STEP_IDS = frozenset(
    f"{scenario}/r{repetition}/{step}"
    for repetition in range(REPETITIONS)
    for scenario, steps in CORPUS_STEP_NAMES.items()
    for step in steps
)

SHORT_PROMPT = (
    "State the transaction invariant that every successful operation commits all records or none. "
    "Reply in one concise sentence."
)
LONG_DECODE_PROMPT = (
    "Write 64 numbered, one-sentence invariants for a durable job queue. Cover admission, ordering, "
    "idempotency, cancellation, retries, checkpoints, recovery, and observability. Do not omit numbers."
)
SYSTEM_PROMPT = (
    "You are reviewing a deterministic storage engine. Give concrete answers, preserve stated "
    "constraints, and do not invent external dependencies."
)
TOOL_USER_PROMPT = "Call lookup_build for target linux-arm64 and revision deadbeef exactly once."
TOOL_RESULT = '{"status":"green","target":"linux-arm64","revision":"deadbeef"}'


class AblationError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def synthetic_prefix(label: str, target_chars: int) -> str:
    rows: list[str] = []
    total_chars = 0
    index = 0
    while total_chars < target_chars:
        row = (
            f"{label} record {index:05d}: owner=worker-{index % 17:02d}; "
            f"state={('ready', 'running', 'checkpointed', 'complete')[index % 4]}; "
            f"epoch={index // 17:04d}; invariant=commit-before-publish;\n"
        )
        rows.append(row)
        total_chars += len(row)
        index += 1
    return "".join(rows)[:target_chars]


def history_messages(turn_pairs: int) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in range(turn_pairs):
        messages.extend(
            [
                {
                    "role": "user",
                    "content": f"At checkpoint {turn}, which state transition is legal?",
                },
                {
                    "role": "assistant",
                    "content": f"Checkpoint {turn} may advance only after its durable record commits.",
                },
            ]
        )
    messages.append(
        {
            "role": "user",
            "content": "Name the preserved invariant and the first recovery check.",
        }
    )
    return messages


def corpus_blueprint() -> dict[str, Any]:
    medium = synthetic_prefix("medium", 16_384)
    long = synthetic_prefix("long", 98_304)
    inputs = {
        "short_prompt": SHORT_PROMPT,
        "long_decode_prompt": LONG_DECODE_PROMPT,
        "history_p50": history_messages(1),
        "history_p90": history_messages(11),
        "tool_prompt": TOOL_USER_PROMPT,
        "tool_result": TOOL_RESULT,
        "medium_prefix": medium,
        "long_prefix": long,
    }
    scenarios = [
        {
            "name": "responses_short",
            "stratum": "short single turn",
            "protocols": ["openai_responses"],
            "steps": 1,
            "max_output_tokens": [32],
        },
        {
            "name": "responses_long_decode",
            "stratum": "long decode",
            "protocols": ["openai_responses"],
            "steps": 1,
            "max_output_tokens": [512],
        },
        {
            "name": "chat_history_p50",
            "stratum": "median message history",
            "protocols": ["openai_chat_completions"],
            "steps": 1,
            "message_count": len(inputs["history_p50"]),
            "max_output_tokens": [80],
        },
        {
            "name": "chat_history_p90",
            "stratum": "deep message history",
            "protocols": ["openai_chat_completions"],
            "steps": 1,
            "message_count": len(inputs["history_p90"]),
            "max_output_tokens": [80],
        },
        {
            "name": "chat_tool_roundtrip",
            "stratum": "forced tool call and tool history",
            "protocols": ["openai_chat_completions", "openai_chat_completions"],
            "steps": 2,
            "tool_count": 1,
            "preserve_assistant_reasoning": True,
            "max_output_tokens": [96, 80],
        },
        {
            "name": "responses_medium_branch",
            "stratum": "medium stored response continuation and sibling branch",
            "protocols": ["openai_responses"] * 3,
            "steps": 3,
            "prefix_chars": len(medium),
            "max_output_tokens": [16, 80, 80],
        },
        {
            "name": "responses_long_replay",
            "stratum": "long stored response replay and sibling branch",
            "protocols": ["openai_responses"] * 3,
            "steps": 3,
            "prefix_chars": len(long),
            "max_output_tokens": [16, 80, 80],
        },
    ]
    for scenario in scenarios:
        step_names = CORPUS_STEP_NAMES.get(scenario["name"])
        if step_names is None or len(step_names) != scenario["steps"]:
            raise AssertionError(f"corpus step inventory drifted for {scenario['name']}")
    input_hashes = {name: sha256_json(value) for name, value in sorted(inputs.items())}
    return {
        "version": CORPUS_VERSION,
        "generator": "omp-ninfer/scripts/run_mtp_ablation.py",
        "repetitions": REPETITIONS,
        "request_count": sum(item["steps"] for item in scenarios) * REPETITIONS,
        "input_sha256": input_hashes,
        "scenarios": scenarios,
        "sampling": {"greedy": True, "temperature": 0},
        "thinking": {"enable_thinking": True, "preserve_thinking_server_default": True},
        "output_projection": {
            "version": 2,
            "included": [
                "answer_text",
                "reasoning_text",
                "reasoning_summary",
                "tool_name",
                "parsed_tool_arguments",
                "finish_status",
            ],
            "excluded": ["generated_object_ids"],
        },
        "privacy": "fully synthetic public inputs; receipts retain hashes and structural metrics only",
        "decision_rule": {
            "quality": "all normalized user-visible outputs must be byte-identical across arms",
            "primary_metric": "aggregate server-reported decode tokens per second",
            "incumbent": 3,
            "promotion_margin": PROMOTION_MARGIN,
            "rule": "retain MTP3 unless another arm is at least 5% faster; an ineligible arm cannot win",
        },
    }


def corpus_manifest() -> dict[str, Any]:
    blueprint = corpus_blueprint()
    return {**blueprint, "sha256": sha256_json(blueprint)}


def identity_digest(label: str) -> str:
    return sha256_bytes(f"omp-mtp-ablation-v1/{label}".encode("utf-8"))


def scoped_identity(
    kind: str,
    *,
    campaign_id: str | None,
    corpus_sha256: str,
    lane: str,
    arm: int,
    suffix: str,
) -> str:
    campaign = f"{campaign_id}/" if campaign_id is not None else ""
    return identity_digest(f"{kind}/{campaign}{corpus_sha256}/{lane}/{arm}/{suffix}")


def require_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AblationError(f"{label} must be a lowercase SHA-256")
    return value


def require_commit(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AblationError(f"{label} must be a lowercase 40-character Git commit")
    return value


@dataclass
class HttpClient:
    base_url: str
    api_key: str
    timeout: float

    def request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        body = None if payload is None else canonical_json(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url.rstrip("/") + path,
            data=body,
            method=method,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                **({"Content-Type": "application/json"} if body is not None else {}),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                status = response.status
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            status = exc.code
        except OSError as exc:
            raise AblationError(f"request failed for {path}: {exc}") from exc
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AblationError(f"{path} returned non-JSON status {status}") from exc
        if status != 200:
            error = decoded.get("error") if isinstance(decoded, dict) else None
            code = error.get("code") if isinstance(error, dict) else None
            raise AblationError(f"{path} returned HTTP {status} code={code!r}")
        if not isinstance(decoded, dict):
            raise AblationError(f"{path} returned a non-object response")
        return decoded

    def health(self) -> None:
        self.request("GET", "/health")


def parsed_arguments(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def responses_content_projection(
    chunk: Mapping[str, Any], *, section: str
) -> dict[str, Any]:
    kind = chunk.get("type")
    if section == "message" and kind == "output_text":
        unknown = set(chunk) - {"type", "text", "annotations", "logprobs"}
        if unknown:
            raise AblationError(
                f"Responses message content has unsupported fields: {sorted(unknown)}"
            )
        text = chunk.get("text")
        if not isinstance(text, str):
            raise AblationError("Responses output_text content omitted text")
        for field in ("annotations", "logprobs"):
            if field in chunk and chunk[field] not in (None, []):
                raise AblationError(
                    f"Responses output_text has unsupported non-empty {field}"
                )
        return {"type": kind, "text": text}
    if section == "message" and kind == "refusal":
        unknown = set(chunk) - {"type", "refusal"}
        if unknown:
            raise AblationError(
                f"Responses refusal content has unsupported fields: {sorted(unknown)}"
            )
        refusal = chunk.get("refusal")
        if not isinstance(refusal, str):
            raise AblationError("Responses refusal content omitted refusal text")
        return {"type": kind, "refusal": refusal}
    if section == "reasoning":
        expected = "reasoning_text"
    elif section == "summary":
        expected = "summary_text"
    else:
        raise AblationError(
            f"Responses message contains unsupported content type {kind!r}"
        )
    if kind == expected:
        unknown = set(chunk) - {"type", "text"}
        if unknown:
            raise AblationError(
                f"Responses {section} content has unsupported fields: {sorted(unknown)}"
            )
        text = chunk.get("text")
        if not isinstance(text, str):
            raise AblationError(f"Responses {expected} content omitted text")
        return {"type": kind, "text": text}
    raise AblationError(
        f"Responses {section} contains unsupported content type {kind!r}"
    )


def response_projection(protocol: str, response: Mapping[str, Any]) -> dict[str, Any]:
    if protocol == "openai_chat_completions":
        choices = response.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise AblationError("Chat Completions response has the wrong choices shape")
        choice = choices[0]
        message = choice.get("message")
        if not isinstance(message, dict):
            raise AblationError("Chat Completions response omitted its message")
        calls: list[dict[str, Any]] = []
        raw_calls = message.get("tool_calls", [])
        if raw_calls is not None:
            if not isinstance(raw_calls, list):
                raise AblationError("Chat Completions tool_calls is not an array")
            for call in raw_calls:
                function = call.get("function") if isinstance(call, dict) else None
                if not isinstance(function, dict) or not isinstance(function.get("name"), str):
                    raise AblationError("Chat Completions returned a malformed tool call")
                calls.append(
                    {
                        "name": function["name"],
                        "arguments": parsed_arguments(function.get("arguments")),
                    }
                )
        content = message.get("content")
        if content is not None and not isinstance(content, (str, list)):
            raise AblationError("Chat Completions returned malformed content")
        reasoning = message.get("reasoning_content")
        if reasoning is not None and not isinstance(reasoning, str):
            raise AblationError("Chat Completions returned malformed reasoning_content")
        return {
            "protocol": protocol,
            "finish_reason": choice.get("finish_reason"),
            "reasoning_content": reasoning,
            "content": content,
            "tool_calls": calls,
        }

    if protocol != "openai_responses":
        raise AblationError(f"unsupported protocol {protocol!r}")
    output = response.get("output")
    if not isinstance(output, list):
        raise AblationError("Responses object omitted its output array")
    projected: list[dict[str, Any]] = []
    for item in output:
        if not isinstance(item, dict):
            raise AblationError("Responses output contains a non-object item")
        kind = item.get("type")
        if kind == "message":
            content = item.get("content")
            if not isinstance(content, list):
                raise AblationError("Responses message omitted content")
            chunks: list[dict[str, Any]] = []
            for chunk in content:
                if not isinstance(chunk, dict):
                    raise AblationError("Responses content contains a non-object item")
                chunks.append(responses_content_projection(chunk, section="message"))
            projected.append({"type": "message", "role": item.get("role"), "content": chunks})
        elif kind in {"function_call", "tool_call"}:
            projected.append(
                {
                    "type": kind,
                    "name": item.get("name"),
                    "arguments": parsed_arguments(item.get("arguments")),
                }
            )
        elif kind == "reasoning":
            content = item.get("content")
            summary = item.get("summary")
            if not isinstance(content, list) or not isinstance(summary, list):
                raise AblationError("Responses reasoning item has malformed content or summary")
            reasoning_content: list[dict[str, Any]] = []
            for chunk in content:
                if not isinstance(chunk, dict):
                    raise AblationError("Responses reasoning content contains a non-object item")
                reasoning_content.append(
                    responses_content_projection(chunk, section="reasoning")
                )
            reasoning_summary: list[dict[str, Any]] = []
            for chunk in summary:
                if not isinstance(chunk, dict):
                    raise AblationError("Responses reasoning summary contains a non-object item")
                reasoning_summary.append(
                    responses_content_projection(chunk, section="summary")
                )
            projected.append(
                {
                    "type": "reasoning",
                    "status": item.get("status"),
                    "summary": reasoning_summary,
                    "content": reasoning_content,
                }
            )
        else:
            raise AblationError(f"Responses output contains unsupported item type {kind!r}")
    return {"protocol": protocol, "status": response.get("status"), "output": projected}


def usage_tokens(protocol: str, response: Mapping[str, Any]) -> tuple[int, int]:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        raise AblationError(f"{protocol} response omitted usage")
    if protocol == "openai_chat_completions":
        prompt = usage.get("prompt_tokens")
        completion = usage.get("completion_tokens")
    else:
        prompt = usage.get("input_tokens")
        completion = usage.get("output_tokens")
    if (
        not isinstance(prompt, int)
        or isinstance(prompt, bool)
        or prompt <= 0
        or not isinstance(completion, int)
        or isinstance(completion, bool)
        or completion < 0
    ):
        raise AblationError(f"{protocol} response has invalid usage")
    return prompt, completion


def response_identifier(response: Mapping[str, Any]) -> str:
    value = response.get("id")
    if not isinstance(value, str) or not value.startswith("resp_"):
        raise AblationError("Responses object omitted its response id")
    return value


def chat_tool_message(response: Mapping[str, Any]) -> dict[str, Any]:
    choices = response.get("choices")
    message = choices[0].get("message") if isinstance(choices, list) and choices else None
    if not isinstance(message, dict):
        raise AblationError("forced tool request omitted its message")
    calls = message.get("tool_calls")
    if not isinstance(calls, list) or len(calls) != 1 or not isinstance(calls[0], dict):
        raise AblationError("forced tool request did not return exactly one tool call")
    function = calls[0].get("function")
    if not isinstance(function, dict) or function.get("name") != "lookup_build":
        raise AblationError("forced tool request returned the wrong function")
    arguments = function.get("arguments")
    if not isinstance(arguments, str):
        raise AblationError("forced tool request returned non-string arguments")
    parsed = parsed_arguments(arguments)
    if parsed != {"revision": "deadbeef", "target": "linux-arm64"}:
        raise AblationError(f"forced tool request returned unexpected arguments: {parsed!r}")
    reasoning = message.get("reasoning_content")
    if reasoning is not None and not isinstance(reasoning, str):
        raise AblationError("forced tool request returned malformed reasoning_content")
    result = {
        "role": "assistant",
        "content": message.get("content"),
        "tool_calls": [
            {
                "id": "call_lookup_build_00000001",
                "type": "function",
                "function": {"name": "lookup_build", "arguments": canonical_json(parsed)},
            }
        ],
    }
    if reasoning is not None:
        result["reasoning_content"] = reasoning
    return result


def base_payload(model: str, session: str, request_id: str) -> dict[str, Any]:
    return {
        "model": model,
        "temperature": 0,
        "enable_thinking": True,
        "ninfer_session": session,
        "ninfer_request_id": request_id,
    }


def request_step(
    client: HttpClient,
    *,
    model: str,
    protocol: str,
    session: str,
    request_id: str,
    payload: Mapping[str, Any],
    step_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    body = {**base_payload(model, session, request_id), **payload}
    path = "/v1/responses" if protocol == "openai_responses" else "/v1/chat/completions"
    if protocol == "openai_responses":
        # Responses uses the server's frozen thinking default; this extension is Chat-only on
        # the oldest qualified lane.
        body.pop("enable_thinking")
    started = time.perf_counter()
    response = client.request("POST", path, body)
    wall_seconds = time.perf_counter() - started
    prompt_tokens, completion_tokens = usage_tokens(protocol, response)
    projection = response_projection(protocol, response)
    result = {
        "step_id": step_id,
        "request_sha256": request_id,
        "protocol": protocol,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "wall_seconds": wall_seconds,
        "projection_sha256": sha256_json(projection),
    }
    return result, response


def execute_scenario(
    client: HttpClient,
    *,
    model: str,
    lane: str,
    arm: int,
    campaign_id: str,
    corpus_sha256: str,
    name: str,
    repetition: int,
) -> list[dict[str, Any]]:
    scenario_key = f"{name}/r{repetition}"
    session = scoped_identity(
        "session",
        campaign_id=campaign_id,
        corpus_sha256=corpus_sha256,
        lane=lane,
        arm=arm,
        suffix=scenario_key,
    )
    results: list[dict[str, Any]] = []

    def send(protocol: str, step: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        step_id = f"{scenario_key}/{step}"
        request_id = scoped_identity(
            "request",
            campaign_id=campaign_id,
            corpus_sha256=corpus_sha256,
            lane=lane,
            arm=arm,
            suffix=step_id,
        )
        result, response = request_step(
            client,
            model=model,
            protocol=protocol,
            session=session,
            request_id=request_id,
            payload=payload,
            step_id=step_id,
        )
        results.append(result)
        return response

    if name == "responses_short":
        send(
            "openai_responses",
            "single",
            {"input": SHORT_PROMPT, "max_output_tokens": 32, "store": True},
        )
    elif name == "responses_long_decode":
        send(
            "openai_responses",
            "single",
            {"input": LONG_DECODE_PROMPT, "max_output_tokens": 512, "store": True},
        )
    elif name == "chat_history_p50":
        send(
            "openai_chat_completions",
            "single",
            {"messages": history_messages(1), "max_completion_tokens": 80},
        )
    elif name == "chat_history_p90":
        send(
            "openai_chat_completions",
            "single",
            {"messages": history_messages(11), "max_completion_tokens": 80},
        )
    elif name == "chat_tool_roundtrip":
        tool = {
            "type": "function",
            "function": {
                "name": "lookup_build",
                "description": "Read a deterministic build result.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string"},
                        "revision": {"type": "string"},
                    },
                    "required": ["target", "revision"],
                },
            },
        }
        first = send(
            "openai_chat_completions",
            "tool_call",
            {
                "messages": [{"role": "user", "content": TOOL_USER_PROMPT}],
                "tools": [tool],
                "tool_choice": {"type": "function", "function": {"name": "lookup_build"}},
                "max_completion_tokens": 96,
            },
        )
        assistant = chat_tool_message(first)
        send(
            "openai_chat_completions",
            "tool_result",
            {
                "messages": [
                    {"role": "user", "content": TOOL_USER_PROMPT},
                    assistant,
                    {
                        "role": "tool",
                        "tool_call_id": "call_lookup_build_00000001",
                        "content": [{"type": "text", "text": TOOL_RESULT}],
                    },
                    {"role": "user", "content": "Report the result in one concise sentence."},
                ],
                "tools": [tool],
                "max_completion_tokens": 80,
            },
        )
    elif name in {"responses_medium_branch", "responses_long_replay"}:
        prefix = (
            synthetic_prefix("medium", 16_384)
            if name == "responses_medium_branch"
            else synthetic_prefix("long", 98_304)
        )
        base = send(
            "openai_responses",
            "base",
            {
                "input": prefix + "\nAcknowledge this state ledger with the word READY.",
                "max_output_tokens": 16,
                "store": True,
            },
        )
        previous = response_identifier(base)
        send(
            "openai_responses",
            "continuation",
            {
                "input": "Name the commit-before-publish invariant in one sentence.",
                "previous_response_id": previous,
                "max_output_tokens": 80,
                "store": True,
            },
        )
        send(
            "openai_responses",
            "branch",
            {
                "input": "Name the first recovery check in one sentence.",
                "previous_response_id": previous,
                "max_output_tokens": 80,
                "store": True,
            },
        )
    else:
        raise AblationError(f"unknown corpus scenario {name!r}")
    return results


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def initial_run_state(lane: str, arm: int, model: str, campaign_id: str) -> dict[str, Any]:
    manifest = corpus_manifest()
    return {
        "artifact_type": RUN_ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "created_utc": utc_now(),
        "lane": lane,
        "arm": arm,
        "model": model,
        "campaign_id": require_sha256(campaign_id, "campaign_id"),
        "corpus_sha256": manifest["sha256"],
        "expected_scenarios": len(manifest["scenarios"]) * REPETITIONS,
        "expected_requests": manifest["request_count"],
        "scenarios": {},
    }


def load_run_state(
    path: Path, lane: str, arm: int, model: str, campaign_id: str, resume: bool
) -> dict[str, Any]:
    expected = initial_run_state(lane, arm, model, campaign_id)
    if not path.exists():
        return expected
    if not resume:
        raise AblationError(f"{path} already exists; pass --resume to continue it")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AblationError(f"cannot read run state {path}: {exc}") from exc
    for key in (
        "artifact_type",
        "schema_version",
        "lane",
        "arm",
        "model",
        "campaign_id",
        "corpus_sha256",
    ):
        if state.get(key) != expected[key]:
            raise AblationError(f"run state {key} does not match this campaign")
    if not isinstance(state.get("scenarios"), dict):
        raise AblationError("run state scenarios must be an object")
    return state


def run_campaign(args: argparse.Namespace) -> dict[str, Any]:
    if args.arm not in ARMS:
        raise AblationError(f"arm must be one of {ARMS}")
    output = Path(args.output)
    campaign_id = require_sha256(args.campaign_id, "campaign_id")
    state = load_run_state(
        output, args.lane, args.arm, args.model, campaign_id, args.resume
    )
    api_key = Path(args.api_key_file).read_text(encoding="utf-8").strip()
    if not api_key:
        raise AblationError("API key file is empty")
    client = HttpClient(args.base_url, api_key, args.timeout)
    client.health()
    manifest = corpus_manifest()
    scenarios = state["scenarios"]
    for repetition in range(REPETITIONS):
        for definition in manifest["scenarios"]:
            name = definition["name"]
            key = f"{name}/r{repetition}"
            existing = scenarios.get(key)
            if isinstance(existing, dict) and existing.get("status") == "complete":
                continue
            steps = execute_scenario(
                client,
                model=args.model,
                lane=args.lane,
                arm=args.arm,
                campaign_id=campaign_id,
                corpus_sha256=manifest["sha256"],
                name=name,
                repetition=repetition,
            )
            scenarios[key] = {"status": "complete", "steps": steps}
            atomic_write_json(output, state)
            print(f"complete {key} ({len(steps)} request(s))", flush=True)
    state["completed_utc"] = utc_now()
    atomic_write_json(output, state)
    return state


def flatten_steps(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    scenarios = state.get("scenarios")
    if not isinstance(scenarios, dict):
        raise AblationError("run state scenarios must be an object")
    steps: list[dict[str, Any]] = []
    for key in sorted(scenarios):
        scenario = scenarios[key]
        if not isinstance(scenario, dict) or scenario.get("status") != "complete":
            raise AblationError(f"scenario {key} is incomplete")
        current = scenario.get("steps")
        if not isinstance(current, list):
            raise AblationError(f"scenario {key} omitted steps")
        for step in current:
            if not isinstance(step, dict):
                raise AblationError(f"scenario {key} contains a malformed step")
            steps.append(step)
    return sorted(steps, key=lambda item: item["step_id"])


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AblationError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AblationError(f"{path} must contain a JSON object")
    return value


def request_identity(record: Mapping[str, Any]) -> str | None:
    request = record.get("request")
    client = request.get("client_identity") if isinstance(request, dict) else None
    value = client.get("request_sha256") if isinstance(client, dict) else None
    return value if isinstance(value, str) else None


SAFE_CONFIGURATION_INCLUDED = {
    "server": frozenset(
        {
            "cors_enabled",
            "default_output_tokens",
            "default_preserve_thinking",
            "default_reasoning_effort",
            "default_thinking",
            "default_thinking_budget",
            "host",
            "max_request_bytes",
            "media_cache_bytes",
            "media_live_bytes",
            "media_preprocess_threads",
            "port",
            "public_model_id",
        }
    ),
    "identity": frozenset(
        {
            "binary_sha256",
            "build_profile",
            "build_type",
            "cuda_architecture",
            "cuda_compiler",
            "cuda_toolkit",
            "cxx_compiler",
            "deployment_profile",
            "model_artifact_sha256",
            "model_id",
            "patch_stack_sha",
            "source_dirty",
            "target",
            "upstream_base_sha",
            "weights_id",
        }
    ),
    "artifact": frozenset(
        {"resource_count", "size_bytes", "target", "weights_id"}
    ),
    "engine": frozenset(
        {
            "context_cache",
            "context_cost",
            "cuda_graph",
            "device",
            "kv_cache",
            "kv_capacity",
            "kv_capacity_max_page_groups",
            "kv_capacity_mode",
            "kv_capacity_page_groups",
            "log_stats_interval_ms",
            "max_concurrency",
            "max_context",
            "max_pending_requests",
            "pending_timeout_ms",
            "prefill_chunk",
            "prefix_reuse",
            "vision",
        }
    ),
    "sampling_defaults": frozenset(
        {"greedy", "non_thinking", "omitted_seed", "server_overrides", "thinking"}
    ),
}
SAFE_CONFIGURATION_EXCLUDED = {
    "server": frozenset({"api_key_configured", "request_log_jsonl"}),
    "identity": frozenset({"config_sha256"}),
    "artifact": frozenset(
        {
            "bytes_read",
            "host_to_device_bytes",
            "load_seconds",
            "path",
            "peak_staging_bytes",
            "tensor_count",
            "upload_seconds",
        }
    ),
    "engine": frozenset(
        {"proposal_head", "speculative_backend", "speculative_draft_window"}
    ),
    "sampling_defaults": frozenset(),
}
SAFE_CONFIGURATION_REQUIRED = {
    "server": frozenset(
        {
            "api_key_configured",
            "cors_enabled",
            "default_output_tokens",
            "default_preserve_thinking",
            "default_thinking",
            "host",
            "max_request_bytes",
            "port",
            "public_model_id",
            "request_log_jsonl",
        }
    ),
    "identity": frozenset(
        {
            "binary_sha256",
            "build_profile",
            "build_type",
            "config_sha256",
            "cuda_compiler",
            "cuda_toolkit",
            "cxx_compiler",
            "deployment_profile",
            "model_artifact_sha256",
            "model_id",
            "patch_stack_sha",
            "source_dirty",
            "target",
            "upstream_base_sha",
            "weights_id",
        }
    ),
    "artifact": frozenset(
        {
            "bytes_read",
            "host_to_device_bytes",
            "load_seconds",
            "peak_staging_bytes",
            "resource_count",
            "size_bytes",
            "target",
            "tensor_count",
            "upload_seconds",
            "weights_id",
        }
    ),
    "engine": frozenset(
        {
            "cuda_graph",
            "device",
            "kv_cache",
            "kv_capacity",
            "kv_capacity_max_page_groups",
            "kv_capacity_mode",
            "kv_capacity_page_groups",
            "log_stats_interval_ms",
            "max_concurrency",
            "max_context",
            "max_pending_requests",
            "pending_timeout_ms",
            "prefill_chunk",
            "prefix_reuse",
            "proposal_head",
            "speculative_backend",
            "speculative_draft_window",
            "vision",
        }
    ),
    "sampling_defaults": SAFE_CONFIGURATION_INCLUDED["sampling_defaults"],
}
SAFE_CONFIGURATION_NULLABLE = frozenset({("server", "default_thinking_budget")})


def safe_configuration_section(start: Mapping[str, Any], section: str) -> dict[str, Any]:
    raw = start.get(section)
    if not isinstance(raw, dict):
        raise AblationError(f"server_start omitted {section}")
    known = SAFE_CONFIGURATION_INCLUDED[section] | SAFE_CONFIGURATION_EXCLUDED[section]
    unknown = sorted(set(raw) - known)
    if unknown:
        raise AblationError(f"server_start {section} has unclassified fields: {unknown}")
    missing = sorted(SAFE_CONFIGURATION_REQUIRED[section] - set(raw))
    if missing:
        raise AblationError(f"server_start {section} omitted required fields: {missing}")
    result = {
        key: raw[key] for key in sorted(SAFE_CONFIGURATION_INCLUDED[section]) if key in raw
    }
    nulls = sorted(
        key
        for key, value in result.items()
        if value is None and (section, key) not in SAFE_CONFIGURATION_NULLABLE
    )
    if nulls:
        raise AblationError(f"server_start {section} has null configuration fields: {nulls}")
    return result


def safe_configuration(start: Mapping[str, Any]) -> dict[str, Any]:
    return {
        section: safe_configuration_section(start, section)
        for section in ("server", "identity", "artifact", "engine", "sampling_defaults")
    }


def summarize_arm(
    trace_path: Path,
    log_path: Path,
    *,
    expected_binary_sha256: str,
    expected_model_sha256: str,
    expected_source_commit: str,
    failure_code: str | None = None,
    failed_step_id: str | None = None,
    failure_evidence_path: Path | None = None,
) -> dict[str, Any]:
    state = read_json_object(trace_path)
    if state.get("artifact_type") != RUN_ARTIFACT_TYPE:
        raise AblationError("trace has the wrong artifact_type")
    arm = state.get("arm")
    if arm not in ARMS:
        raise AblationError("trace has an unsupported arm")
    lane = state.get("lane")
    model = state.get("model")
    if not isinstance(lane, str) or not lane:
        raise AblationError("trace has an invalid lane")
    if not isinstance(model, str) or not model:
        raise AblationError("trace has an invalid model")
    corpus_sha = require_sha256(state.get("corpus_sha256"), "corpus_sha256")
    campaign_value = state.get("campaign_id")
    campaign_id = (
        None
        if campaign_value is None
        else require_sha256(campaign_value, "campaign_id")
    )
    steps = flatten_steps(state)
    expected_requests = state.get("expected_requests")
    if not isinstance(expected_requests, int) or isinstance(expected_requests, bool):
        raise AblationError("trace has an invalid expected request count")
    failure_values = (failure_code, failed_step_id, failure_evidence_path)
    if any(value is not None for value in failure_values) and not all(
        value is not None for value in failure_values
    ):
        raise AblationError("failure code, step, and evidence path must be supplied together")
    failed = failure_code is not None
    if not failed and len(steps) != expected_requests:
        raise AblationError("trace does not contain the expected request count")
    if failed and len(steps) >= expected_requests:
        raise AblationError("a failed arm must have fewer than the expected request count")
    wanted: dict[str, dict[str, Any]] = {}
    for step in steps:
        step_id = step.get("step_id")
        if not isinstance(step_id, str) or not step_id:
            raise AblationError("trace contains a malformed step ID")
        request_id = require_sha256(step.get("request_sha256"), "request_sha256")
        expected_request_id = scoped_identity(
            "request",
            campaign_id=campaign_id,
            corpus_sha256=corpus_sha,
            lane=lane,
            arm=arm,
            suffix=step_id,
        )
        if request_id != expected_request_id:
            raise AblationError(f"trace request identity mismatch for {step_id}")
        if request_id in wanted:
            raise AblationError("trace contains duplicate request identities")
        wanted[request_id] = step

    starts: dict[str, dict[str, Any]] = {}
    latest: dict[str, dict[str, Any]] = {}
    try:
        handle = log_path.open("r", encoding="utf-8")
    except OSError as exc:
        raise AblationError(f"cannot read server log {log_path}: {exc}") from exc
    with handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict):
                continue
            instance = record.get("server_instance_id")
            if record.get("event") == "server_start" and isinstance(instance, str):
                starts[instance] = record
            request_id = request_identity(record)
            if request_id is not None and request_id in wanted:
                latest[request_id] = record
    missing = sorted(set(wanted) - set(latest))
    if missing:
        raise AblationError(f"server log omitted {len(missing)} completed trace request(s)")
    non_done = sorted(key for key, record in latest.items() if record.get("event") != "request_done")
    if non_done:
        raise AblationError(f"latest log event was not request_done for {len(non_done)} request(s)")
    instance_values = {record.get("server_instance_id") for record in latest.values()}
    if not instance_values or not all(isinstance(item, str) for item in instance_values):
        raise AblationError("trace requests contain an invalid server instance")
    instance_ids = sorted(item for item in instance_values if isinstance(item, str))
    missing_starts = [instance for instance in instance_ids if instance not in starts]
    if missing_starts:
        raise AblationError("server log omitted a matching server_start record")

    binary_sha = require_sha256(expected_binary_sha256, "expected binary SHA-256")
    model_sha = require_sha256(expected_model_sha256, "expected model SHA-256")
    source_commit = require_commit(expected_source_commit, "expected source commit")
    configuration: dict[str, Any] | None = None
    expected_backend = "none" if arm == 0 else "mtp"
    for instance in instance_ids:
        start = starts[instance]
        server = start.get("server")
        identity = start.get("identity")
        engine = start.get("engine")
        sampling = start.get("sampling_defaults")
        if (
            not isinstance(server, dict)
            or not isinstance(identity, dict)
            or not isinstance(engine, dict)
            or not isinstance(sampling, dict)
        ):
            raise AblationError(
                "server_start omitted server, identity, engine, or sampling defaults"
            )
        checks = {
            "binary_sha256": (identity.get("binary_sha256"), binary_sha),
            "model_artifact_sha256": (identity.get("model_artifact_sha256"), model_sha),
            "patch_stack_sha": (identity.get("patch_stack_sha"), source_commit),
            "public_model_id": (server.get("public_model_id"), model),
        }
        for label, (actual, expected) in checks.items():
            if actual != expected:
                raise AblationError(
                    f"server identity {label} mismatch: {actual!r} != {expected!r}"
                )
        if identity.get("source_dirty") is not False:
            raise AblationError("experiment binary reports a dirty source tree")
        if engine.get("speculative_backend") != expected_backend:
            raise AblationError("server speculative backend does not match the arm")
        if arm != 0 and engine.get("speculative_draft_window") != arm:
            raise AblationError("server speculative draft window does not match the arm")
        if arm != 0 and engine.get("proposal_head") != "optimized":
            raise AblationError("MTP arm did not use the optimized proposal head")
        if engine.get("prefix_reuse") is not True:
            raise AblationError("agent corpus requires prefix reuse")
        if sampling.get("greedy") is not True:
            raise AblationError("agent corpus requires greedy server sampling")
        current_configuration = safe_configuration(start)
        if configuration is None:
            configuration = current_configuration
        elif configuration != current_configuration:
            raise AblationError("resumed arm changed non-speculative server configuration")
    if configuration is None:
        raise AssertionError("at least one server configuration was validated")

    failure: dict[str, Any] | None = None
    if failed:
        assert failure_code is not None
        assert failed_step_id is not None
        assert failure_evidence_path is not None
        scenario_names = {item["name"] for item in corpus_manifest()["scenarios"]}
        step_parts = failed_step_id.split("/")
        if (
            not failure_code
            or any(not (char.islower() or char.isdigit() or char == "_") for char in failure_code)
            or len(step_parts) != 3
            or step_parts[0] not in scenario_names
            or step_parts[1] not in {f"r{index}" for index in range(REPETITIONS)}
            or not step_parts[2]
        ):
            raise AblationError("failure metadata is malformed")
        try:
            evidence_size = failure_evidence_path.stat().st_size
        except OSError as exc:
            raise AblationError(f"cannot read failure evidence: {exc}") from exc
        if evidence_size <= 0:
            raise AblationError("failure evidence is empty")
        failure = {
            "code": failure_code,
            "step_id": failed_step_id,
            "evidence_sha256": sha256_file(failure_evidence_path),
            "evidence_size_bytes": evidence_size,
        }

    rows: list[dict[str, Any]] = []
    for request_id, trace in sorted(wanted.items(), key=lambda item: item[1]["step_id"]):
        record = latest[request_id]
        request = record.get("request")
        result = record.get("result")
        timings = record.get("timings_seconds")
        speculative = record.get("speculative")
        if not isinstance(request, dict):
            raise AblationError(f"request_done {request_id} omitted request metadata")
        if not isinstance(result, dict):
            raise AblationError(f"request_done {request_id} omitted result metrics")
        if not isinstance(timings, dict):
            raise AblationError(f"request_done {request_id} omitted timing metrics")
        if not isinstance(speculative, dict):
            raise AblationError(f"request_done {request_id} omitted speculative metrics")
        client_identity = request.get("client_identity")
        if not isinstance(client_identity, dict):
            raise AblationError(f"request_done {request_id} omitted client identity")
        if client_identity.get("request_sha256") != request_id:
            raise AblationError(f"request identity mismatch for {trace['step_id']}")
        scenario_key = trace["step_id"].rsplit("/", 1)[0]
        expected_session_id = scoped_identity(
            "session",
            campaign_id=campaign_id,
            corpus_sha256=corpus_sha,
            lane=lane,
            arm=arm,
            suffix=scenario_key,
        )
        if client_identity.get("session_sha256") != expected_session_id:
            raise AblationError(f"session identity mismatch for {trace['step_id']}")
        if request.get("protocol") != trace.get("protocol"):
            raise AblationError(f"protocol mismatch for {trace['step_id']}")
        if result.get("prompt_tokens") != trace.get("prompt_tokens"):
            raise AblationError(f"prompt usage mismatch for {trace['step_id']}")
        if result.get("completion_tokens") != trace.get("completion_tokens"):
            raise AblationError(f"completion usage mismatch for {trace['step_id']}")
        if request.get("enable_thinking") is not True:
            raise AblationError(f"thinking was not enabled for {trace['step_id']}")
        if speculative.get("backend") != expected_backend:
            raise AblationError(f"speculative backend mismatch for {trace['step_id']}")
        if speculative.get("draft_window") != arm:
            raise AblationError(f"speculative draft window mismatch for {trace['step_id']}")
        drafted = speculative.get("drafted_tokens")
        accepted = speculative.get("accepted_tokens")
        if (
            not isinstance(drafted, int)
            or isinstance(drafted, bool)
            or drafted < 0
            or not isinstance(accepted, int)
            or isinstance(accepted, bool)
            or accepted < 0
            or accepted > drafted
        ):
            raise AblationError(f"invalid speculative token counts for {trace['step_id']}")
        if arm == 0 and any(
            speculative.get(field) != 0
            for field in ("rounds", "drafted_tokens", "accepted_tokens", "fallback_steps")
        ):
            raise AblationError(f"MTP0 reported speculative work for {trace['step_id']}")
        rows.append(
            {
                "step_id": trace["step_id"],
                "request_sha256": request_id,
                "protocol": trace["protocol"],
                "projection_sha256": require_sha256(
                    trace.get("projection_sha256"), "projection_sha256"
                ),
                "client_wall_seconds": trace["wall_seconds"],
                "prompt_tokens": result.get("prompt_tokens"),
                "completion_tokens": result.get("completion_tokens"),
                "computed_prefill_tokens": result.get("computed_prefill_tokens"),
                "prefix_cache_hit_tokens": result.get("prefix_cache_hit_tokens"),
                "prefix_reuse_path": result.get("prefix_reuse_path"),
                "finish_reason": result.get("finish_reason"),
                "tool_call_count": result.get("tool_call_count"),
                "timings_seconds": {
                    key: timings.get(key) for key in ("prepare", "ttft", "prefill", "decode", "total")
                },
                "speculative": {
                    key: speculative.get(key)
                    for key in (
                        "backend",
                        "draft_window",
                        "rounds",
                        "drafted_tokens",
                        "accepted_tokens",
                        "fallback_steps",
                        "accepted_per_position",
                    )
                },
            }
        )
    return {
        "artifact_type": ARM_ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "generated_utc": utc_now(),
        "scope": "within-lane experiment; not release qualification and not cross-lane comparable",
        "status": "failed" if failed else "completed",
        "lane": lane,
        "arm": arm,
        "model": model,
        "campaign_id": campaign_id,
        "corpus_sha256": corpus_sha,
        "source_commit": source_commit,
        "binary_sha256": binary_sha,
        "model_artifact_sha256": model_sha,
        "server_instance_sha256s": [
            sha256_bytes(instance.encode("utf-8")) for instance in instance_ids
        ],
        "trace_sha256": sha256_file(trace_path),
        "server_log_sha256": sha256_file(log_path),
        "configuration_schema_version": CONFIGURATION_SCHEMA_VERSION,
        "configuration": configuration,
        "configuration_sha256": sha256_json(configuration),
        "completed_requests": len(rows),
        "expected_requests": expected_requests,
        "failure": failure,
        "requests": rows,
    }


def finite_number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise AblationError(f"{label} must be a finite number")
    return float(value)


def aggregate_arm(receipt: Mapping[str, Any]) -> dict[str, Any]:
    requests = receipt.get("requests")
    if not isinstance(requests, list) or not requests:
        raise AblationError("arm receipt has no requests")
    prompt_tokens = 0
    completion_tokens = 0
    decode_tokens = 0
    decode_seconds = 0.0
    total_seconds = 0.0
    ttft_values: list[float] = []
    wall_values: list[float] = []
    rounds = 0
    drafted = 0
    accepted = 0
    fallback = 0
    reuse: dict[str, int] = {}
    repetition_decode_tokens = {f"r{index}": 0 for index in range(REPETITIONS)}
    repetition_decode_seconds = {f"r{index}": 0.0 for index in range(REPETITIONS)}
    for row in requests:
        if not isinstance(row, dict):
            raise AblationError("arm receipt contains a malformed request")
        prompt = row.get("prompt_tokens")
        completion = row.get("completion_tokens")
        timings = row.get("timings_seconds")
        speculative = row.get("speculative")
        if (
            not isinstance(prompt, int)
            or isinstance(prompt, bool)
            or prompt <= 0
            or not isinstance(completion, int)
            or isinstance(completion, bool)
            or completion < 0
        ):
            raise AblationError("arm receipt contains invalid token counts")
        if not isinstance(timings, dict) or not isinstance(speculative, dict):
            raise AblationError("arm receipt omitted timing or speculative metrics")
        step_id = row.get("step_id")
        parts = step_id.split("/") if isinstance(step_id, str) else []
        if len(parts) != 3 or parts[1] not in repetition_decode_tokens:
            raise AblationError("arm receipt contains an invalid repetition step id")
        repetition = parts[1]
        row_decode_tokens = max(0, completion - 1)
        row_decode_seconds = finite_number(timings.get("decode"), "decode seconds")
        row_total_seconds = finite_number(timings.get("total"), "total seconds")
        row_ttft = finite_number(timings.get("ttft"), "TTFT seconds")
        row_wall = finite_number(row.get("client_wall_seconds"), "client wall seconds")
        if min(row_decode_seconds, row_total_seconds, row_ttft, row_wall) < 0:
            raise AblationError("arm receipt contains a negative duration")
        prompt_tokens += prompt
        completion_tokens += completion
        decode_tokens += row_decode_tokens
        decode_seconds += row_decode_seconds
        total_seconds += row_total_seconds
        ttft_values.append(row_ttft)
        wall_values.append(row_wall)
        repetition_decode_tokens[repetition] += row_decode_tokens
        repetition_decode_seconds[repetition] += row_decode_seconds
        for label, target in (
            ("rounds", "rounds"),
            ("drafted_tokens", "drafted"),
            ("accepted_tokens", "accepted"),
            ("fallback_steps", "fallback"),
        ):
            value = speculative.get(label)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise AblationError(f"arm receipt contains invalid {label}")
            if target == "rounds":
                rounds += value
            elif target == "drafted":
                drafted += value
            elif target == "accepted":
                accepted += value
            else:
                fallback += value
        path = row.get("prefix_reuse_path")
        reuse[str(path)] = reuse.get(str(path), 0) + 1
    by_repetition = {
        repetition: repetition_decode_tokens[repetition] / seconds
        if seconds > 0
        else None
        for repetition, seconds in repetition_decode_seconds.items()
    }
    finite_repetition_speeds = [
        speed for speed in by_repetition.values() if isinstance(speed, float) and speed > 0
    ]
    if len(finite_repetition_speeds) != REPETITIONS:
        raise AblationError("arm receipt has no decode throughput for a repetition")
    return {
        "request_count": len(requests),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "decode_tokens": decode_tokens,
        "decode_seconds": decode_seconds,
        "decode_tokens_per_second": decode_tokens / decode_seconds if decode_seconds > 0 else None,
        "decode_tokens_per_second_by_repetition": by_repetition,
        "decode_throughput_spread_pct": (
            max(finite_repetition_speeds) / min(finite_repetition_speeds) - 1.0
        )
        * 100.0,
        "total_seconds": total_seconds,
        "median_ttft_seconds": statistics.median(ttft_values),
        "median_client_wall_seconds": statistics.median(wall_values),
        "speculative_rounds": rounds,
        "drafted_tokens": drafted,
        "accepted_tokens": accepted,
        "acceptance_rate": accepted / drafted if drafted else None,
        "completion_tokens_per_round": completion_tokens / rounds if rounds else None,
        "fallback_steps": fallback,
        "prefix_reuse_paths": dict(sorted(reuse.items())),
    }


def projection_map(requests: Sequence[Any], label: str) -> dict[str, str]:
    outputs: dict[str, str] = {}
    for row in requests:
        if not isinstance(row, dict):
            raise AblationError(f"{label} receipt contains a malformed request")
        step_id = row.get("step_id")
        if not isinstance(step_id, str) or not step_id:
            raise AblationError(f"{label} receipt contains a malformed step ID")
        projection = require_sha256(row.get("projection_sha256"), "projection_sha256")
        if step_id in outputs:
            raise AblationError(f"{label} receipt contains duplicate step ID {step_id}")
        outputs[step_id] = projection
    return outputs


def repeatability_mismatches(requests: Sequence[Any], label: str) -> list[str]:
    repetitions: dict[str, dict[str, str]] = {}
    for row in requests:
        if not isinstance(row, dict):
            raise AblationError(f"{label} receipt contains a malformed request")
        step_id = row.get("step_id")
        if not isinstance(step_id, str):
            raise AblationError(f"{label} receipt contains a malformed step ID")
        parts = step_id.split("/")
        if len(parts) != 3 or parts[1] not in {"r0", "r1"} or not parts[0] or not parts[2]:
            raise AblationError(f"{label} receipt contains a non-corpus step ID {step_id!r}")
        key = f"{parts[0]}/{parts[2]}"
        projection = require_sha256(row.get("projection_sha256"), "projection_sha256")
        by_repetition = repetitions.setdefault(key, {})
        if parts[1] in by_repetition:
            raise AblationError(f"{label} receipt duplicates {key}/{parts[1]}")
        by_repetition[parts[1]] = projection
    incomplete = sorted(key for key, values in repetitions.items() if set(values) != {"r0", "r1"})
    if incomplete:
        raise AblationError(f"{label} receipt has incomplete repetitions")
    return sorted(
        key for key, values in repetitions.items() if values["r0"] != values["r1"]
    )


def validate_arm_receipt_content(
    receipt: Mapping[str, Any],
    *,
    label: str,
    current_corpus: Mapping[str, Any],
) -> tuple[str, list[Any], dict[str, str], dict[str, Any], list[str]]:
    if receipt.get("artifact_type") != ARM_ARTIFACT_TYPE:
        raise AblationError(f"{label} has the wrong artifact_type")
    if receipt.get("schema_version") != SCHEMA_VERSION:
        raise AblationError(f"{label} has an unsupported schema_version")
    if receipt.get("configuration_schema_version") != CONFIGURATION_SCHEMA_VERSION:
        raise AblationError(f"{label} has an unsupported configuration schema")
    if receipt.get("corpus_sha256") != current_corpus["sha256"]:
        raise AblationError(f"{label} corpus_sha256 is not the current corpus")
    campaign_id = receipt.get("campaign_id")
    if campaign_id is not None:
        require_sha256(campaign_id, f"{label} campaign_id")
    status = receipt.get("status")
    if status not in {"completed", "failed"}:
        raise AblationError(f"{label} has an invalid status")
    requests = receipt.get("requests")
    completed_requests = receipt.get("completed_requests")
    expected_requests = current_corpus["request_count"]
    if not isinstance(requests, list):
        raise AblationError(f"{label} omitted requests")
    if (
        not isinstance(completed_requests, int)
        or isinstance(completed_requests, bool)
        or completed_requests < 0
        or completed_requests != len(requests)
        or receipt.get("expected_requests") != expected_requests
    ):
        raise AblationError(f"{label} has inconsistent request counts")
    if status == "completed" and completed_requests != expected_requests:
        raise AblationError(f"completed {label} omitted corpus requests")
    if status == "failed" and completed_requests >= expected_requests:
        raise AblationError(f"failed {label} did not stop before corpus completion")
    outputs = projection_map(requests, label)
    observed_step_ids = set(outputs)
    if status == "completed" and observed_step_ids != EXPECTED_STEP_IDS:
        missing = sorted(EXPECTED_STEP_IDS - observed_step_ids)
        unexpected = sorted(observed_step_ids - EXPECTED_STEP_IDS)
        raise AblationError(
            f"{label} corpus step inventory mismatch: "
            f"missing={missing}, unexpected={unexpected}"
        )
    if status == "failed" and not observed_step_ids <= EXPECTED_STEP_IDS:
        unexpected = sorted(observed_step_ids - EXPECTED_STEP_IDS)
        raise AblationError(
            f"{label} corpus step inventory contains unexpected steps: {unexpected}"
        )
    configuration = receipt.get("configuration")
    if not isinstance(configuration, dict):
        raise AblationError(f"{label} omitted its safe configuration")
    configuration_sha256 = require_sha256(
        receipt.get("configuration_sha256"), "configuration_sha256"
    )
    if sha256_json(configuration) != configuration_sha256:
        raise AblationError(f"{label} configuration_sha256 does not match its content")
    instances = receipt.get("server_instance_sha256s")
    if not isinstance(instances, list) or not instances:
        raise AblationError(f"{label} omitted server instance evidence")
    instance_sha256s = [
        require_sha256(value, "server instance SHA-256") for value in instances
    ]
    if len(set(instance_sha256s)) != len(instance_sha256s):
        raise AblationError(f"{label} repeated a server instance identity")
    evidence = {
        "arm_receipt_content_sha256": sha256_json(receipt),
        "trace_sha256": require_sha256(receipt.get("trace_sha256"), "trace SHA-256"),
        "server_log_sha256": require_sha256(
            receipt.get("server_log_sha256"), "server log SHA-256"
        ),
        "server_instance_count": len(instance_sha256s),
    }
    return str(status), requests, outputs, evidence, instance_sha256s


def combine_receipts(
    receipts: Sequence[Mapping[str, Any]],
    baseline_control: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if len(receipts) != len(ARMS):
        raise AblationError(f"combine requires exactly {len(ARMS)} arm receipts")
    by_arm: dict[int, Mapping[str, Any]] = {}
    for receipt in receipts:
        if receipt.get("artifact_type") != ARM_ARTIFACT_TYPE:
            raise AblationError("combine input has the wrong artifact_type")
        arm = receipt.get("arm")
        if arm not in ARMS or arm in by_arm:
            raise AblationError("combine inputs must contain each arm exactly once")
        by_arm[arm] = receipt
    if tuple(sorted(by_arm)) != ARMS:
        raise AblationError(f"combine inputs must contain arms {ARMS}")

    current_corpus = corpus_manifest()
    normalized_outputs_by_arm: dict[int, dict[str, str]] = {}
    evidence_by_arm: dict[int, dict[str, Any]] = {}
    instances_by_arm: dict[int, list[str]] = {}
    statuses: dict[int, str] = {}
    for arm, receipt in by_arm.items():
        status, _, outputs, evidence, instances = validate_arm_receipt_content(
            receipt, label=f"arm {arm}", current_corpus=current_corpus
        )
        statuses[arm] = status
        normalized_outputs_by_arm[arm] = outputs
        evidence_by_arm[arm] = evidence
        instances_by_arm[arm] = instances

    baseline = by_arm[0]
    invariant_fields = (
        "lane",
        "model",
        "corpus_sha256",
        "source_commit",
        "binary_sha256",
        "model_artifact_sha256",
        "campaign_id",
        "configuration_schema_version",
        "configuration_sha256",
    )
    for arm, receipt in by_arm.items():
        for field in invariant_fields:
            if receipt.get(field) != baseline.get(field):
                raise AblationError(f"arm {arm} changed invariant field {field}")

    campaign_bound = isinstance(baseline.get("campaign_id"), str)
    baseline_control_outputs: dict[str, str] | None = None
    baseline_control_evidence: dict[str, Any] | None = None
    baseline_control_repeat_mismatches: list[str] | None = None
    baseline_control_mismatches: list[str] | None = None
    if baseline_control is not None:
        if baseline_control.get("arm") != 0:
            raise AblationError("fresh-process baseline control must be an MTP0 receipt")
        (
            control_status,
            control_requests,
            baseline_control_outputs,
            baseline_control_evidence,
            control_instances,
        ) = validate_arm_receipt_content(
            baseline_control, label="fresh-process MTP0 control", current_corpus=current_corpus
        )
        if control_status != "completed":
            raise AblationError("fresh-process MTP0 control must complete")
        for field in invariant_fields:
            if baseline_control.get(field) != baseline.get(field):
                raise AblationError(
                    f"fresh-process MTP0 control changed invariant field {field}"
                )
        if set(control_instances) & set(instances_by_arm[0]):
            raise AblationError(
                "fresh-process MTP0 control reused a baseline server instance"
            )
        baseline_control_repeat_mismatches = repeatability_mismatches(
            control_requests, "fresh-process MTP0 control"
        )
        baseline_control_mismatches = sorted(
            key
            for key in set(normalized_outputs_by_arm[0]) | set(baseline_control_outputs)
            if normalized_outputs_by_arm[0].get(key) != baseline_control_outputs.get(key)
        )

    if statuses[0] != "completed":
        raise AblationError("the non-speculative MTP0 baseline must complete")
    if statuses[3] != "completed":
        raise AblationError("the incumbent MTP3 arm must complete")

    baseline_requests = by_arm[0].get("requests")
    if not isinstance(baseline_requests, list):
        raise AblationError("MTP0 receipt omitted requests")
    baseline_outputs = normalized_outputs_by_arm[0]
    mismatches_by_arm: dict[int, list[str]] = {}
    repeat_mismatches_by_arm: dict[int, list[str]] = {}
    for arm, receipt in by_arm.items():
        if statuses[arm] == "failed":
            failure = receipt.get("failure")
            if not isinstance(failure, dict):
                raise AblationError(f"failed arm {arm} omitted failure evidence")
            if (
                not isinstance(failure.get("code"), str)
                or not failure["code"]
                or not isinstance(failure.get("step_id"), str)
                or not failure["step_id"]
                or not isinstance(failure.get("evidence_size_bytes"), int)
                or isinstance(failure["evidence_size_bytes"], bool)
                or failure["evidence_size_bytes"] <= 0
            ):
                raise AblationError(f"failed arm {arm} has malformed failure evidence")
            require_sha256(failure.get("evidence_sha256"), "failure evidence SHA-256")
            mismatches_by_arm[arm] = []
            repeat_mismatches_by_arm[arm] = []
            continue
        requests = receipt.get("requests")
        if not isinstance(requests, list):
            raise AblationError(f"arm {arm} omitted requests")
        outputs = normalized_outputs_by_arm[arm]
        repeat_mismatches_by_arm[arm] = repeatability_mismatches(requests, f"arm {arm}")
        mismatches_by_arm[arm] = sorted(
            key
            for key in set(outputs) | set(baseline_outputs)
            if outputs.get(key) != baseline_outputs.get(key)
        )

    summaries: dict[int, dict[str, Any]] = {}
    for arm, receipt in sorted(by_arm.items()):
        if statuses[arm] == "completed":
            summaries[arm] = {"status": "completed", **aggregate_arm(receipt)}
        else:
            summaries[arm] = {
                "status": "failed",
                "completed_requests": receipt.get("completed_requests"),
                "expected_requests": receipt.get("expected_requests"),
                "failure": receipt.get("failure"),
            }
        summaries[arm]["evidence"] = evidence_by_arm[arm]
        summaries[arm]["normalized_output_sha256"] = normalized_outputs_by_arm[arm]
    speeds = {
        arm: summary["decode_tokens_per_second"]
        for arm, summary in summaries.items()
        if statuses[arm] == "completed"
    }
    if any(not isinstance(speed, (int, float)) or speed <= 0 for speed in speeds.values()):
        raise AblationError("every arm must report positive decode throughput")
    incumbent_speed = float(speeds[3])
    completed_arms = tuple(arm for arm in ARMS if statuses[arm] == "completed")
    fastest_observed = max(completed_arms, key=lambda arm: float(speeds[arm]))
    baseline_within_instance_repeatable = not repeat_mismatches_by_arm[0]
    baseline_control_available = baseline_control is not None
    baseline_cross_instance_repeatable = (
        None
        if not baseline_control_available
        else not baseline_control_repeat_mismatches and not baseline_control_mismatches
    )
    validity_failures: list[str] = []
    if not campaign_bound:
        validity_failures.append("arm receipts lack one shared non-null campaign identity")
    if not baseline_within_instance_repeatable:
        validity_failures.append("MTP0 changed output between same-process repetitions")
    if not baseline_control_available:
        validity_failures.append("a fresh-process MTP0 control receipt is missing")
    elif not baseline_cross_instance_repeatable:
        validity_failures.append("MTP0 changed output across fresh server instances")
    baseline_repeatable = not validity_failures
    eligible = tuple(
        arm
        for arm in completed_arms
        if baseline_repeatable
        and not repeat_mismatches_by_arm[arm]
        and not mismatches_by_arm[arm]
    )
    fastest_eligible = max(eligible, key=lambda arm: float(speeds[arm])) if eligible else None
    incumbent_eligible = 3 in eligible

    def clears_promotion_margin(arm: int) -> bool:
        candidate = summaries[arm]["decode_tokens_per_second_by_repetition"]
        incumbent = summaries[3]["decode_tokens_per_second_by_repetition"]
        if not isinstance(candidate, dict) or not isinstance(incumbent, dict):
            raise AblationError("arm receipt omitted per-repetition decode throughput")
        return all(
            float(candidate[f"r{index}"])
            >= float(incumbent[f"r{index}"]) * (1.0 + PROMOTION_MARGIN)
            for index in range(REPETITIONS)
        )

    if not baseline_repeatable:
        selected = None
    elif not incumbent_eligible:
        assert fastest_eligible is not None
        selected = fastest_eligible
    else:
        assert fastest_eligible is not None
        promotable = tuple(
            arm for arm in eligible if arm != 3 and clears_promotion_margin(arm)
        )
        selected = (
            max(promotable, key=lambda arm: float(speeds[arm])) if promotable else 3
        )
    for arm in ARMS:
        summaries[arm]["quality_eligible"] = (
            arm in eligible
        )
        if statuses[arm] == "completed":
            summaries[arm]["decode_change_vs_mtp3_pct"] = (
                (float(speeds[arm]) / incumbent_speed - 1.0) * 100.0
                if baseline_repeatable
                else None
            )
            summaries[arm]["normalized_output_mismatch_count"] = len(
                mismatches_by_arm[arm]
            )
            summaries[arm]["repeatability_mismatch_count"] = len(
                repeat_mismatches_by_arm[arm]
            )
        else:
            summaries[arm]["decode_change_vs_mtp3_pct"] = None
            summaries[arm]["normalized_output_mismatch_count"] = None
            summaries[arm]["repeatability_mismatch_count"] = None
    decision = {
        "status": "inconclusive" if not baseline_repeatable else "decided",
        "selected_arm": selected,
        "fastest_observed_arm": fastest_observed if baseline_repeatable else None,
        "fastest_eligible_arm": fastest_eligible,
        "incumbent_arm": 3,
        "promotion_margin": PROMOTION_MARGIN,
        "action": (
            "no draft-depth decision"
            if not baseline_repeatable
            else "replace output-drifted MTP3"
            if not incumbent_eligible
            else "change lane default"
            if selected != 3
            else "retain MTP3"
        ),
        "reason": (
            "; ".join(validity_failures)
            if not baseline_repeatable
            else f"MTP3 changed normalized output versus MTP0; MTP{selected} is the fastest output-identical completed arm"
            if not incumbent_eligible
            else f"eligible MTP{selected} exceeded MTP3 decode throughput by at least 5% in each repetition"
            if selected != 3
            else "no output-identical alternative exceeded MTP3 decode throughput by 5% in every repetition"
        ),
    }
    return {
        "artifact_type": LANE_ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "generated_utc": utc_now(),
        "scope": "within-lane experiment; not release qualification and not cross-lane comparable",
        "lane": baseline.get("lane"),
        "model": baseline.get("model"),
        "campaign_id": baseline.get("campaign_id"),
        "model_artifact_sha256": baseline.get("model_artifact_sha256"),
        "source_commit": baseline.get("source_commit"),
        "binary_sha256": baseline.get("binary_sha256"),
        "configuration_schema_version": baseline.get("configuration_schema_version"),
        "configuration_sha256": baseline.get("configuration_sha256"),
        "corpus": current_corpus,
        "trust_boundary": (
            "owner measurement host and local arm receipts are trusted; hashes are "
            "provenance identifiers, not remote attestation"
        ),
        "analysis": {
            "version": ANALYSIS_VERSION,
            "quality_reference_arm": 0,
            "requires_within_arm_repeatability": True,
            "cross_arm_attribution_requires_repeatable_baseline": True,
            "requires_shared_campaign_identity": True,
            "requires_fresh_process_baseline_control": True,
            "promotion_requires_margin_in_each_repetition": True,
            "corpus_decision_rule_superseded": True,
            "selection_rule": {
                "validity_gate": (
                    "one shared campaign identity plus within-process and fresh-process "
                    "MTP0 output identity"
                ),
                "incumbent_eligible": (
                    "retain MTP3 unless another eligible arm improves decode throughput "
                    "by at least 5% in every repetition"
                ),
                "incumbent_ineligible": (
                    "select the fastest eligible output-identical fallback without applying "
                    "the promotion margin to the ineligible incumbent"
                ),
            },
            "fresh_process_baseline_control": {
                "available": baseline_control_available,
                "evidence": baseline_control_evidence,
                "normalized_output_sha256": baseline_control_outputs,
            },
        },
        "quality": {
            "normalized_outputs_identical": baseline_repeatable
            and all(
                statuses[arm] == "completed"
                and not repeat_mismatches_by_arm[arm]
                and not mismatches_by_arm[arm]
                for arm in ARMS
            ),
            "reference_arm": 0,
            "compared_steps": len(baseline_outputs),
            "baseline_repeatable": baseline_repeatable,
            "baseline_within_instance_repeatable": baseline_within_instance_repeatable,
            "baseline_cross_instance_repeatable": baseline_cross_instance_repeatable,
            "baseline_control_repeatability_mismatches": (
                baseline_control_repeat_mismatches
            ),
            "baseline_control_mismatches": baseline_control_mismatches,
            "validity_failures": validity_failures,
            "repeatability_compared_steps": len(baseline_outputs) // REPETITIONS,
            "repeatability_mismatches_by_arm": {
                str(arm): {
                    "count": (
                        len(mismatches) if statuses[arm] == "completed" else None
                    ),
                    "step_ids": mismatches,
                }
                for arm, mismatches in sorted(repeat_mismatches_by_arm.items())
            },
            "eligible_arms": list(eligible),
            "failed_arms": [arm for arm in ARMS if statuses[arm] == "failed"],
            "mismatches_by_arm": {
                str(arm): {
                    "count": len(mismatches) if statuses[arm] == "completed" else None,
                    "step_ids": mismatches,
                }
                for arm, mismatches in sorted(mismatches_by_arm.items())
            },
        },
        "arms": {str(arm): summaries[arm] for arm in ARMS},
        "decision": decision,
    }


def write_or_print(payload: Mapping[str, Any], output: str | None) -> None:
    if output is None:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        atomic_write_json(Path(output), payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    contract = subparsers.add_parser("contract", help="render the deterministic corpus contract")
    contract.add_argument("--output")

    run = subparsers.add_parser("run", help="execute or resume one arm against a running server")
    run.add_argument("--base-url", required=True)
    run.add_argument("--api-key-file", required=True)
    run.add_argument("--model", required=True)
    run.add_argument("--lane", required=True)
    run.add_argument("--arm", required=True, type=int, choices=ARMS)
    run.add_argument("--campaign-id", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--timeout", type=float, default=900.0)
    run.add_argument("--resume", action="store_true")

    summarize = subparsers.add_parser("summarize", help="bind one run trace to server metrics")
    summarize.add_argument("--trace", type=Path, required=True)
    summarize.add_argument("--server-log", type=Path, required=True)
    summarize.add_argument("--binary-sha256", required=True)
    summarize.add_argument("--model-sha256", required=True)
    summarize.add_argument("--source-commit", required=True)
    summarize.add_argument("--failure-code")
    summarize.add_argument("--failed-step-id")
    summarize.add_argument("--failure-evidence", type=Path)
    summarize.add_argument("--output", required=True)

    combine = subparsers.add_parser("combine", help="validate and decide one four-arm lane")
    combine.add_argument("--arm-receipt", type=Path, action="append", required=True)
    combine.add_argument("--baseline-control-receipt", type=Path)
    combine.add_argument("--output", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "contract":
            write_or_print(corpus_manifest(), args.output)
        elif args.command == "run":
            state = run_campaign(args)
            print(
                canonical_json(
                    {
                        "status": "complete",
                        "lane": state["lane"],
                        "arm": state["arm"],
                        "campaign_id": state["campaign_id"],
                        "requests": len(flatten_steps(state)),
                        "corpus_sha256": state["corpus_sha256"],
                    }
                )
            )
        elif args.command == "summarize":
            receipt = summarize_arm(
                args.trace,
                args.server_log,
                expected_binary_sha256=args.binary_sha256,
                expected_model_sha256=args.model_sha256,
                expected_source_commit=args.source_commit,
                failure_code=args.failure_code,
                failed_step_id=args.failed_step_id,
                failure_evidence_path=args.failure_evidence,
            )
            write_or_print(receipt, args.output)
        elif args.command == "combine":
            receipts = [read_json_object(path) for path in args.arm_receipt]
            baseline_control = (
                read_json_object(args.baseline_control_receipt)
                if args.baseline_control_receipt is not None
                else None
            )
            write_or_print(combine_receipts(receipts, baseline_control), args.output)
        else:
            raise AssertionError(args.command)
    except (AblationError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
