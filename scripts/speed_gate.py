#!/usr/bin/env python3
"""Plan gate-bound pre-screens and reduce native ABBA speed captures, without contacting hosts."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Sequence

ORDER = ("A", "B", "B", "A")
WEIGHTED_MINIMUM = 1.08
EVERY_CASE_MINIMUM = 0.95


class SpeedGateError(ValueError):
    pass


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def require_sha256(value: Any, description: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise SpeedGateError(f"{description} must be a lowercase SHA-256 digest")
    return value


def request_suite(rows: Any) -> list[dict[str, str]]:
    if not isinstance(rows, list) or not rows:
        raise SpeedGateError("request suite must be a nonempty list")
    suite = []
    for row in rows:
        if not isinstance(row, dict):
            raise SpeedGateError("request suite entries must be objects")
        case_id = row.get("id")
        if not isinstance(case_id, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.@:-]*", case_id) is None:
            raise SpeedGateError("request id must be a content-safe case identifier")
        suite.append({"id": case_id, "request_sha256": require_sha256(
            row.get("request_sha256"), "request_sha256")})
    if len({row["id"] for row in suite}) != len(suite):
        raise SpeedGateError("duplicate request id in suite")
    return sorted(suite, key=lambda row: row["id"])


def arm_identity(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise SpeedGateError("arm identity must be an object")
    return {key: require_sha256(value.get(key), key)
            for key in ("binary_sha256", "configuration_sha256")}


def declaration(value: Any) -> dict[str, Any]:
    if (not isinstance(value, dict) or value.get("artifact_type") != "omp_ninfer_speed_gate"
            or type(value.get("schema_version")) is not int or value["schema_version"] != 1):
        raise SpeedGateError("expected a schema-1 omp_ninfer_speed_gate declaration")
    suite = request_suite(value.get("request_suite"))
    if value.get("request_suite_sha256") != digest(suite):
        raise SpeedGateError("gate request_suite_sha256 does not bind its requests")
    roles = value.get("role_case_ids")
    if (not isinstance(roles, list) or not roles or any(not isinstance(case, str) for case in roles)
            or len(set(roles)) != len(roles) or not set(roles) <= {row["id"] for row in suite}):
        raise SpeedGateError("role_case_ids must select unique declared role requests")
    return {"artifact_type": "omp_ninfer_speed_gate", "schema_version": 1,
            "comparator": arm_identity(value.get("comparator")), "request_suite": suite,
            "request_suite_sha256": digest(suite), "role_case_ids": sorted(roles)}


def prescreen(gate: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """There is no comparator argument: A always comes from the gate declaration."""
    gate = declaration(gate)
    return {"artifact_type": "omp_ninfer_speed_prescreen_plan", "schema_version": 1,
            "gate_sha256": digest(gate), "order": list(ORDER),
            "arms": {"A": gate["comparator"], "B": arm_identity(candidate)},
            "request_suite": gate["request_suite"], "request_suite_sha256": gate["request_suite_sha256"],
            "role_case_ids": gate["role_case_ids"]}


def positive_number(value: Any, description: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise SpeedGateError(f"{description} must be a finite positive number")
    return float(value)


def receipts(captures: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Combine disjoint depth/supplemental shards at each ABBA position, retaining only safe fields."""
    arms: dict[int, dict[str, Any]] = {}
    for capture in captures:
        index = capture.get("index")
        if type(index) is not int or index not in range(4) or capture.get("arm") != ORDER[index] or capture.get("status") != "passed":
            raise SpeedGateError("captures must be passed, indexed ABBA arms")
        identity = capture.get("identity")
        if not isinstance(identity, dict):
            raise SpeedGateError("capture has no measured identity")
        safe_identity = arm_identity({**identity, "configuration_sha256": (
            digest(identity["config"]) if isinstance(identity.get("config"), dict)
            else identity.get("configuration_sha256"))})
        rows = capture.get("requests")
        request_suite(rows)
        arm = arms.setdefault(index, {"arm": ORDER[index], "index": index, "identity": safe_identity,
                                      "capture_sha256s": [], "requests": []})
        if arm["identity"] != safe_identity:
            raise SpeedGateError("one ABBA position has inconsistent shard binary/configuration identities")
        arm["capture_sha256s"].append(digest(capture))
        for row in rows:
            tokens = row.get("completion_tokens")
            if type(tokens) is not int or tokens <= 0:
                raise SpeedGateError("completion_tokens must be a positive integer")
            seconds = positive_number(row.get("decode_seconds"), "decode_seconds")
            positive_number(tokens / seconds, "decode rate")
            arm["requests"].append({"id": row["id"], "request_sha256": row["request_sha256"],
                                    "completion_tokens": tokens, "decode_seconds": seconds})
    if set(arms) != set(range(4)):
        raise SpeedGateError("all four ABBA positions are required")
    result = [arms[index] for index in range(4)]
    for arm in result:
        arm["request_suite_sha256"] = digest(request_suite(arm["requests"]))
    if any({row["id"] for row in arm["requests"]} != {row["id"] for row in result[0]["requests"]} for arm in result):
        raise SpeedGateError("each ABBA position must contain the same case ids")
    return result


def summarize(arms: Sequence[dict[str, Any]], case_ids: set[str]) -> dict[str, Any] | None:
    if not case_ids:
        return None
    samples = {label: [row for arm in arms if arm["arm"] == label
                       for row in arm["requests"] if row["id"] in case_ids] for label in ("A", "B")}
    rates = {label: sum(row["completion_tokens"] for row in rows) / sum(row["decode_seconds"] for row in rows)
             for label, rows in samples.items()}
    cases = []
    for case_id in sorted(case_ids):
        rate = {label: statistics.median(row["completion_tokens"] / row["decode_seconds"]
                                        for row in rows if row["id"] == case_id)
                for label, rows in samples.items()}
        cases.append({"id": case_id, "baseline_decode_tok_s": rate["A"], "candidate_decode_tok_s": rate["B"],
                      "ratio": rate["B"] / rate["A"]})
    return {"case_count": len(cases), "weighted_decode_tok_s": rates, "weighted_decode_ratio": rates["B"] / rates["A"],
            "minimum_case_ratio": min(row["ratio"] for row in cases),
            "below_case_floor": [row["id"] for row in cases if row["ratio"] < EVERY_CASE_MINIMUM], "cases": cases}


def identity_differences(gate: dict[str, Any], arms: Sequence[dict[str, Any]]) -> list[str]:
    reasons = []
    for arm in arms:
        name = f"{arm['arm']}{arm['index']}"
        if arm["arm"] == "A":
            for field, expected in gate["comparator"].items():
                if arm["identity"][field] != expected:
                    reasons.append(f"{name}.{field} differs from gate comparator")
        if arm["request_suite_sha256"] != gate["request_suite_sha256"]:
            reasons.append(f"{name}.request_suite_sha256 differs from gate role suite")
    for field in ("binary_sha256", "configuration_sha256"):
        if arms[1]["identity"][field] != arms[2]["identity"][field]:
            reasons.append(f"candidate {field} differs between B1 and B2")
    return reasons


def reduce(gate: dict[str, Any], captures: Sequence[dict[str, Any]]) -> dict[str, Any]:
    gate = declaration(gate)
    arms = receipts(captures)
    case_ids = {row["id"] for row in arms[0]["requests"]}
    role_ids = case_ids & set(gate["role_case_ids"])
    roles = summarize(arms, role_ids)
    all_cases = summarize(arms, case_ids)
    reasons = identity_differences(gate, arms)
    passed = (roles is not None and roles["weighted_decode_ratio"] >= WEIGHTED_MINIMUM
              and all_cases["weighted_decode_ratio"] >= WEIGHTED_MINIMUM
              and all_cases["minimum_case_ratio"] >= EVERY_CASE_MINIMUM)
    return {"artifact_type": "omp_ninfer_speed_gate_result", "schema_version": 1,
            "status": "DIAGNOSTIC" if reasons else ("PASS" if passed else "FAIL"),
            "gate_predictive": not reasons, "diagnostic_reasons": reasons,
            "thresholds_passed": passed, "gate_passed": not reasons and passed,
            "gate_sha256": digest(gate), "comparator": gate["comparator"],
            "request_suite_sha256": gate["request_suite_sha256"],
            "thresholds": {"weighted_minimum": WEIGHTED_MINIMUM, "every_case_minimum": EVERY_CASE_MINIMUM},
            "role_suite": roles, "supplemental": summarize(arms, case_ids - role_ids), "all_cases": all_cases,
            "arms": arms}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise SpeedGateError("input must be a JSON object")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("prescreen", help="derive comparator A and requests from the gate declaration")
    plan.add_argument("--candidate", type=Path, required=True, help="candidate binary/configuration SHA-256 JSON")
    reduction = commands.add_parser("reduce", help="reduce complete ABBA capture files, including disjoint shards")
    reduction.add_argument("--capture", type=Path, action="append", required=True)
    for command in (plan, reduction):
        command.add_argument("--gate", type=Path, required=True)
        command.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = (prescreen(load(args.gate), load(args.candidate)) if args.command == "prescreen"
                  else reduce(load(args.gate), [load(path) for path in args.capture]))
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"speed_gate: {exc}", file=sys.stderr)
        return 2
    if args.command == "prescreen":
        print(json.dumps({"gate_sha256": result["gate_sha256"]}, sort_keys=True))
        return 0
    print(json.dumps({key: result[key] for key in ("status", "gate_predictive", "thresholds")}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
