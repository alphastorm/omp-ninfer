#!/usr/bin/env python3
"""Normalize and compare two sanitized OpenAI Responses wire captures."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

ARTIFACT_TYPE = "omp_ninfer_responses_wire_capture"
ID_RE = re.compile(r"^(?P<prefix>[A-Za-z][A-Za-z0-9]*)(?:_|-)[0-9A-Za-z-]{8,}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TERMINAL_EVENTS = {"response.completed", "response.failed", "response.incomplete"}
SECRET_HEADERS = {"authorization", "x-api-key", "x-ninfer-session"}
TIMESTAMP_KEYS = {"created_at", "completed_at", "timestamp", "timestamp_unix_ms"}


class CaptureError(ValueError):
    pass


@dataclass
class Normalizer:
    workspace: Path | None = None
    ids: dict[str, str] = field(default_factory=dict)
    digests: dict[str, str] = field(default_factory=dict)

    def token(self, value: str) -> str:
        match = ID_RE.fullmatch(value)
        if match is None:
            return value
        existing = self.ids.get(value)
        if existing is not None:
            return existing
        prefix = match.group("prefix").lower()
        token = f"<{prefix}:{sum(item.startswith(f'<{prefix}:') for item in self.ids.values()) + 1}>"
        self.ids[value] = token
        return token

    def digest(self, value: str) -> str:
        existing = self.digests.get(value)
        if existing is not None:
            return existing
        token = f"<digest:{len(self.digests) + 1}>"
        self.digests[value] = token
        return token


def require_capture(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CaptureError(f"{label}: capture root must be an object")
    if value.get("artifact_type") != ARTIFACT_TYPE or value.get("schema_version") != 1:
        raise CaptureError(f"{label}: unsupported capture identity")
    if not isinstance(value.get("scenario"), str) or not value["scenario"]:
        raise CaptureError(f"{label}: scenario must be a non-empty string")
    for key in ("requests", "events"):
        if not isinstance(value.get(key), list) or not all(
            isinstance(item, dict) for item in value[key]
        ):
            raise CaptureError(f"{label}: {key} must be an array of objects")
    return value


def normalize_value(
    value: Any,
    normalizer: Normalizer,
    *,
    key: str | None = None,
    in_usage: bool = False,
) -> Any:
    if key in TIMESTAMP_KEYS and isinstance(value, (int, float, str)):
        return "<timestamp>"
    if in_usage and isinstance(value, (int, float)) and not isinstance(value, bool):
        return "<number>"
    if isinstance(value, str):
        lowered = key.lower() if key else ""
        if lowered in SECRET_HEADERS:
            if not value:
                raise CaptureError(f"credential header {key} is empty")
            return "<present>"
        if lowered in {"ninfer_session", "ninfer_request_id"} and SHA256_RE.fullmatch(value):
            return normalizer.digest(value)
        if normalizer.workspace is not None:
            workspace = str(normalizer.workspace)
            if workspace and workspace in value:
                value = value.replace(workspace, "<workspace>")
        if lowered == "id" or lowered.endswith("_id") or lowered in {
            "previous_response_id",
            "call_id",
            "response_id",
            "item_id",
        }:
            return normalizer.token(value)
        return value
    if isinstance(value, list):
        return [normalize_value(item, normalizer, in_usage=in_usage) for item in value]
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for child_key in sorted(value):
            child_usage = in_usage or child_key == "usage"
            output[child_key] = normalize_value(
                value[child_key], normalizer, key=child_key, in_usage=child_usage
            )
        return output
    return value


def event_response_id(event: dict[str, Any]) -> str | None:
    direct = event.get("response_id")
    if isinstance(direct, str):
        return direct
    response = event.get("response")
    if isinstance(response, dict) and isinstance(response.get("id"), str):
        return response["id"]
    return None


def validate_events(events: list[dict[str, Any]], label: str) -> list[str]:
    errors: list[str] = []
    if not events:
        return [f"{label}: events are empty"]
    types = [event.get("type") for event in events]
    if types[0] != "response.created":
        errors.append(f"{label}: first event must be response.created")
    if types[-1] not in TERMINAL_EVENTS:
        errors.append(f"{label}: final event must be terminal")

    sequences = [event.get("sequence_number") for event in events]
    if not all(isinstance(number, int) and not isinstance(number, bool) for number in sequences):
        errors.append(f"{label}: every event needs an integer sequence_number")
    else:
        sequence_numbers = [cast(int, number) for number in sequences]
        if any(
            right != left + 1
            for left, right in zip(sequence_numbers, sequence_numbers[1:])
        ):
            errors.append(f"{label}: sequence_number values must be contiguous")

    response_ids = {value for event in events if (value := event_response_id(event)) is not None}
    if len(response_ids) != 1:
        errors.append(f"{label}: events must retain one response id")

    added: set[str] = set()
    done: set[str] = set()
    for event in events:
        item = event.get("item")
        item_id = item.get("id") if isinstance(item, dict) else None
        if event.get("type") == "response.output_item.added" and isinstance(item_id, str):
            added.add(item_id)
        if event.get("type") == "response.output_item.done" and isinstance(item_id, str):
            done.add(item_id)
    if added != done:
        errors.append(f"{label}: output item ids differ between added and done events")
    return errors


def normalize_capture(
    capture: dict[str, Any], *, workspace: Path | None = None
) -> dict[str, Any]:
    normalizer = Normalizer(workspace=workspace.resolve() if workspace else None)
    return normalize_value(capture, normalizer)


def compare_captures(
    reference: dict[str, Any],
    candidate: dict[str, Any],
    *,
    reference_workspace: Path | None = None,
    candidate_workspace: Path | None = None,
) -> dict[str, Any]:
    reference = require_capture(reference, "reference")
    candidate = require_capture(candidate, "candidate")
    errors = validate_events(reference["events"], "reference") + validate_events(
        candidate["events"], "candidate"
    )
    if reference["scenario"] != candidate["scenario"]:
        errors.append("scenario names differ")
    normalized_reference = normalize_capture(reference, workspace=reference_workspace)
    normalized_candidate = normalize_capture(candidate, workspace=candidate_workspace)
    reference_text = json.dumps(normalized_reference, indent=2, sort_keys=True).splitlines()
    candidate_text = json.dumps(normalized_candidate, indent=2, sort_keys=True).splitlines()
    diff = list(
        difflib.unified_diff(
            reference_text,
            candidate_text,
            fromfile="reference",
            tofile="candidate",
            lineterm="",
        )
    )
    return {
        "artifact_type": "omp_ninfer_responses_wire_comparison",
        "schema_version": 1,
        "scenario": reference["scenario"],
        "valid": not errors,
        "equivalent": not errors and not diff,
        "errors": errors,
        "diff": diff,
    }


def load(path: Path) -> dict[str, Any]:
    try:
        return require_capture(json.loads(path.read_text(encoding="utf-8")), str(path))
    except (OSError, json.JSONDecodeError) as error:
        raise CaptureError(f"{path}: {error}") from error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--reference-workspace", type=Path)
    parser.add_argument("--candidate-workspace", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = compare_captures(
            load(args.reference),
            load(args.candidate),
            reference_workspace=args.reference_workspace,
            candidate_workspace=args.candidate_workspace,
        )
    except CaptureError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(payload, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(args.output)
    return 0 if result["equivalent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
