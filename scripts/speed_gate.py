#!/usr/bin/env python3
"""Reduce native ABBA captures under their release's recorded speed decision.

The declaration embeds the release's hash-bound qualification decision, binding
its authenticated rule into the pre-screen plan. Both weighted suites, every case,
and retained normalized UTF-8 output bytes must pass; neither a digest-only capture
nor a waiver supplies a pass.
No host is contacted and normalized output text is never copied into the result.
"""
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
OUTPUT_RULE = "required for every case (A0/A3, B1/B2, A0/B1)"
ROOT = Path(__file__).resolve().parents[1]


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


def recorded_thresholds(decision: Any, release: Any) -> dict[str, float]:
    if (not isinstance(release, str) or not release
            or not isinstance(decision, dict)
            or decision.get("artifact_type") != "omp_ninfer_founder_gate_decision"
            or type(decision.get("schema_version")) is not int or decision["schema_version"] != 1
            or decision.get("release") != release):
        raise SpeedGateError("decision must be this release's schema-1 omp_ninfer_founder_gate_decision")
    rule = decision.get("rule")
    if not isinstance(rule, dict) or rule.get("byte_identical_normalized_outputs") != OUTPUT_RULE:
        raise SpeedGateError("decision rule must require normalized output bytes for every ABBA case")
    applies_to = rule.get("applies_to")
    if (not isinstance(applies_to, list) or len(applies_to) != 3
            or any(not isinstance(item, str) for item in applies_to)
            or set(applies_to) != {"role weighted", "all-cases weighted", "every case"}):
        raise SpeedGateError("decision rule must cover role weighted, all-cases weighted and every case")
    return {"weighted_minimum": positive_number(rule.get("weighted_decode_ratio_minimum"), "weighted minimum"),
            "every_case_minimum": positive_number(rule.get("every_case_ratio_minimum"), "every-case minimum")}


def authenticate_decision(value: dict[str, Any], root: Path) -> None:
    release = value["release"]
    if re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", release) is None:
        raise SpeedGateError("release must name a versioned release directory")
    qualification = load(root / "releases" / release / "qualification.json")
    gates = qualification.get("observed_gates")
    binding = gates.get("native_speed_decision") if isinstance(gates, dict) else None
    if not isinstance(binding, dict):
        raise SpeedGateError("release qualification must bind native_speed_decision")
    reference = binding.get("repository_path")
    if not isinstance(reference, str) or Path(reference).is_absolute():
        raise SpeedGateError("native_speed_decision must name a repository-relative file")
    path = (root / reference).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise SpeedGateError("native_speed_decision must name a file inside the repository")
    expected_sha = require_sha256(binding.get("sha256"), "native_speed_decision sha256")
    decision_bytes = path.read_bytes()
    if hashlib.sha256(decision_bytes).hexdigest() != expected_sha:
        raise SpeedGateError("native_speed_decision SHA-256 must match the bound file bytes")
    if value["decision"] != json.loads(decision_bytes):
        raise SpeedGateError("gate decision must equal the release's bound decision")


def declaration(value: Any, *, root: Path | None = None) -> dict[str, Any]:
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
    recorded_thresholds(value.get("decision"), value.get("release"))
    authenticate_decision(value, root if root is not None else ROOT)
    return {"artifact_type": "omp_ninfer_speed_gate", "schema_version": 1,
            "release": value["release"], "decision": value["decision"],
            "comparator": arm_identity(value.get("comparator")), "request_suite": suite,
            "request_suite_sha256": digest(suite), "role_case_ids": sorted(roles)}


def prescreen(gate: dict[str, Any], candidate: dict[str, Any], *,
              root: Path | None = None) -> dict[str, Any]:
    """There is no comparator argument: A always comes from the gate declaration."""
    gate = declaration(gate, root=root)
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
        for row in rows:
            tokens = row.get("completion_tokens")
            if type(tokens) is not int or tokens <= 0:
                raise SpeedGateError("completion_tokens must be a positive integer")
            seconds = positive_number(row.get("decode_seconds"), "decode_seconds")
            positive_number(tokens / seconds, "decode rate")
            output = row.get("normalized_output")
            if not isinstance(output, str):
                raise SpeedGateError("normalized_output must contain the retained normalized UTF-8 output")
            arm["requests"].append({"id": row["id"], "request_sha256": row["request_sha256"],
                                    "completion_tokens": tokens, "decode_seconds": seconds,
                                    "normalized_output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest()})
        arm["capture_sha256s"].append(digest(capture))
    if set(arms) != set(range(4)):
        raise SpeedGateError("all four ABBA positions are required")
    result = [arms[index] for index in range(4)]
    for arm in result:
        arm["request_suite_sha256"] = digest(request_suite(arm["requests"]))
    if any({row["id"] for row in arm["requests"]} != {row["id"] for row in result[0]["requests"]} for arm in result):
        raise SpeedGateError("each ABBA position must contain the same case ids")
    return result


def summarize(arms: Sequence[dict[str, Any]], case_ids: set[str],
              every_case_minimum: float) -> dict[str, Any] | None:
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
            "below_case_floor": [row["id"] for row in cases if row["ratio"] < every_case_minimum], "cases": cases}


def output_mismatches(captures: Sequence[dict[str, Any]]) -> list[str]:
    """Compare retained bytes, not claimed matching hashes or booleans."""
    outputs: dict[int, dict[str, bytes]] = {index: {} for index in range(4)}
    for capture in captures:
        for row in capture["requests"]:
            outputs[capture["index"]][row["id"]] = row["normalized_output"].encode("utf-8")
    return sorted(case_id for case_id, baseline in outputs[0].items()
                  if any(outputs[index][case_id] != baseline for index in (3, 1, 2)))


def identity_differences(gate: dict[str, Any], arms: Sequence[dict[str, Any]],
                         plan: dict[str, Any], *, root: Path | None = None) -> list[str]:
    if (not isinstance(plan, dict) or plan.get("artifact_type") != "omp_ninfer_speed_prescreen_plan"
            or type(plan.get("schema_version")) is not int or plan["schema_version"] != 1):
        raise SpeedGateError("expected a schema-1 omp_ninfer_speed_prescreen_plan")
    require_sha256(plan.get("gate_sha256"), "plan gate_sha256")
    planned_arms = plan.get("arms")
    if not isinstance(planned_arms, dict) or set(planned_arms) != {"A", "B"}:
        raise SpeedGateError("plan arms must declare A and B identities")
    planned_arms = {label: arm_identity(value) for label, value in planned_arms.items()}
    expected_plan = prescreen(gate, planned_arms["B"], root=root)
    reasons = []
    for field in ("gate_sha256", "role_case_ids", "request_suite", "request_suite_sha256", "order"):
        if plan.get(field) != expected_plan[field]:
            reasons.append(f"plan.{field} differs from gate declaration")
    if planned_arms["A"] != gate["comparator"]:
        reasons.append("plan.arms.A differs from gate comparator")
    for arm in arms:
        name = f"{arm['arm']}{arm['index']}"
        if arm["arm"] == "A":
            for field, expected in gate["comparator"].items():
                if arm["identity"][field] != expected:
                    reasons.append(f"{name}.{field} differs from gate comparator")
        if arm["request_suite_sha256"] != gate["request_suite_sha256"]:
            reasons.append(f"{name}.request_suite_sha256 differs from gate role suite")
        for field, expected in planned_arms[arm["arm"]].items():
            if arm["identity"][field] != expected:
                reasons.append(f"{name}.{field} differs from plan arm {arm['arm']}")
    for field in ("binary_sha256", "configuration_sha256"):
        if arms[1]["identity"][field] != arms[2]["identity"][field]:
            reasons.append(f"candidate {field} differs between B1 and B2")
    return reasons


def reduce(gate: dict[str, Any], captures: Sequence[dict[str, Any]],
           plan: dict[str, Any], *, root: Path | None = None) -> dict[str, Any]:
    gate = declaration(gate, root=root)
    thresholds = recorded_thresholds(gate["decision"], gate["release"])
    arms = receipts(captures)
    case_ids = {row["id"] for row in arms[0]["requests"]}
    role_ids = case_ids & set(gate["role_case_ids"])
    roles = summarize(arms, role_ids, thresholds["every_case_minimum"])
    all_cases = summarize(arms, case_ids, thresholds["every_case_minimum"])
    reasons = identity_differences(gate, arms, plan, root=root)
    mismatches = output_mismatches(captures)
    passed = (roles is not None and roles["weighted_decode_ratio"] >= thresholds["weighted_minimum"]
              and all_cases["weighted_decode_ratio"] >= thresholds["weighted_minimum"]
              and all_cases["minimum_case_ratio"] >= thresholds["every_case_minimum"])
    gate_passed = not reasons and passed and not mismatches
    return {"artifact_type": "omp_ninfer_speed_gate_result", "schema_version": 1,
            "status": "DIAGNOSTIC" if reasons else ("PASS" if gate_passed else "FAIL"),
            "gate_predictive": not reasons, "diagnostic_reasons": reasons,
            "thresholds_passed": passed, "gate_passed": gate_passed,
            "normalized_outputs_identical": not mismatches, "output_mismatch_case_ids": mismatches,
            "release": gate["release"], "decision_sha256": digest(gate["decision"]),
            "gate_sha256": digest(gate), "comparator": gate["comparator"],
            "plan_sha256": digest(plan), "plan_gate_sha256": plan["gate_sha256"],
            "role_case_ids": gate["role_case_ids"],
            "request_suite_sha256": gate["request_suite_sha256"],
            "thresholds": thresholds, "role_suite": roles,
            "supplemental": summarize(arms, case_ids - role_ids, thresholds["every_case_minimum"]),
            "all_cases": all_cases,
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
    reduction.add_argument("--plan", type=Path, required=True, help="recorded pre-screen identity plan")
    for command in (plan, reduction):
        command.add_argument("--root", type=Path,
                             help="repository root containing release qualification (default: this checkout)")
        command.add_argument("--gate", type=Path, required=True)
        command.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = (prescreen(load(args.gate), load(args.candidate), root=args.root) if args.command == "prescreen"
                  else reduce(load(args.gate), [load(path) for path in args.capture],
                              load(args.plan), root=args.root))
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
