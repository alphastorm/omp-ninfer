#!/usr/bin/env python3
"""Reduce native ABBA captures under their release's recorded speed decision.

The declaration embeds the release's hash-bound qualification decision, binding
its authenticated rule into the pre-screen plan. Both weighted suites and every case
must pass. Output bytes must match across all arms unless the decision selects
within-engine identity and binds this lane/candidate's passing EXP-085 screen.
Neither a digest-only capture nor a waiver supplies a pass.
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
SCREEN_OUTPUT_RULE = ("required within each engine (A0/A3, B1/B2); "
                      "cross-engine differences require a bound passing EXP-085 verdict")
IDENTITY_RULE = "speed-ABBA byte identity and 80/80 sealed incumbent determinism byte identity"
NATIVE_IDENTITY_FIELDS = ("package_sha256", "server_binary_sha256",
                          "configuration_sha256", "model_artifact_sha256")
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
            or decision.get("status") == "draft"
            or decision.get("release") != release):
        raise SpeedGateError("decision must be this release's schema-1 omp_ninfer_founder_gate_decision")
    rule = decision.get("rule")
    if (not isinstance(rule, dict)
            or rule.get("byte_identical_normalized_outputs") not in (OUTPUT_RULE, SCREEN_OUTPUT_RULE)):
        raise SpeedGateError("decision rule must select a supported normalized output-byte rule")
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
    result = {"artifact_type": "omp_ninfer_speed_gate", "schema_version": 1,
              "release": value["release"], "decision": value["decision"],
              "comparator": arm_identity(value.get("comparator")), "request_suite": suite,
              "request_suite_sha256": digest(suite), "role_case_ids": sorted(roles)}
    if value["decision"]["rule"]["byte_identical_normalized_outputs"] == SCREEN_OUTPUT_RULE:
        if value.get("lane") not in ("rtx3090", "rtx4090"):
            raise SpeedGateError("the screened output rule requires a native lane")
        result["lane"] = value["lane"]
    return result


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


def output_mismatches(captures: Sequence[dict[str, Any]], *,
                      within_engine: bool = False) -> list[str]:
    """Compare retained bytes, not claimed matching hashes or booleans."""
    outputs: dict[int, dict[str, bytes]] = {index: {} for index in range(4)}
    for capture in captures:
        for row in capture["requests"]:
            outputs[capture["index"]][row["id"]] = row["normalized_output"].encode("utf-8")
    if within_engine:
        return sorted(case_id for case_id, baseline in outputs[0].items()
                      if outputs[3][case_id] != baseline
                      or outputs[1][case_id] != outputs[2][case_id])
    return sorted(case_id for case_id, baseline in outputs[0].items()
                  if any(outputs[index][case_id] != baseline for index in (3, 1, 2)))


def bound_document(root: Path, binding: Any, label: str) -> dict[str, Any]:
    """Authenticate a repository-relative JSON edge before interpreting its contents."""
    if not isinstance(binding, dict):
        raise SpeedGateError(f"{label} must bind repository_path and sha256")
    reference = binding.get("repository_path")
    if not isinstance(reference, str) or Path(reference).is_absolute():
        raise SpeedGateError(f"{label} must name a repository-relative file")
    path = (root / reference).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise SpeedGateError(f"{label} must name a file inside the repository")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != require_sha256(binding.get("sha256"), f"{label} sha256"):
        raise SpeedGateError(f"{label} SHA-256 must match the bound file bytes")
    value = json.loads(data)
    if not isinstance(value, dict):
        raise SpeedGateError(f"{label} must bind a JSON object")
    return value


def passing_screen(gate: dict[str, Any], candidate: dict[str, str], root: Path) -> str | None:
    """A decision-bound passing screen may authorize only its exact lane and measured arms."""
    from quality_screen import validate_native_arms
    from redaction_screen import ScreenError, native_arm

    bindings = gate["decision"].get("quality_screens", [])
    if not isinstance(bindings, list):
        return None
    for binding in bindings:
        if not isinstance(binding, dict) or binding.get("lane") != gate["lane"]:
            continue
        try:
            value = bound_document(root, binding, "quality screen")
            if (value.get("artifact_type") != "omp-ninfer.quality-screen-verdict"
                    or type(value.get("schema_version")) is not int or value["schema_version"] != 1
                    or value.get("verdict") != "pass" or value.get("validity", {}).get("valid") is not True
                    or value.get("preregistration", {}).get("experiment") != "EXP-085"
                    or value.get("counted_prompts") != 1120
                    or value.get("raw_prompts_outputs_or_secrets_included") is not False):
                continue
            runs = value["runs"]
            selected = {role: {**runs[role], "arm": native_arm(runs[role]["arm"])} for role in (
                "production", "candidate", "production_determinism", "candidate_determinism")}
            validate_native_arms(selected)
            for role, expected in (("production", gate["comparator"]), ("candidate", candidate)):
                arm = selected[role]["arm"]
                if (arm["lane"] != gate["lane"]
                        or arm_identity({"binary_sha256": arm["server_binary_sha256"],
                                         "configuration_sha256": arm["configuration_sha256"]}) != expected):
                    raise SpeedGateError("screen arm differs from the speed comparison")
            return binding["sha256"]
        except (ScreenError, OSError, ValueError, KeyError, TypeError, AttributeError):
            continue
    return None


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
    screened = gate["decision"]["rule"]["byte_identical_normalized_outputs"] == SCREEN_OUTPUT_RULE
    within_mismatches = output_mismatches(captures, within_engine=True) if screened else mismatches
    screen_sha = (passing_screen(gate, arms[1]["identity"], root if root is not None else ROOT)
                  if screened and mismatches and not within_mismatches else None)
    output_passed = not mismatches or (screened and not within_mismatches and screen_sha is not None)
    gate_passed = not reasons and passed and output_passed
    result = {"artifact_type": "omp_ninfer_speed_gate_result", "schema_version": 1,
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
    if screened:
        result.update(output_rule=SCREEN_OUTPUT_RULE, output_rule_passed=output_passed,
                      within_engine_outputs_identical=not within_mismatches,
                      within_engine_output_mismatch_case_ids=within_mismatches,
                      quality_screen_sha256=screen_sha)
    return result


def native_identity(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise SpeedGateError("native identity must be an object")
    return {key: require_sha256(value.get(key), key) for key in NATIVE_IDENTITY_FIELDS}


def identity_decision(root: Path, release: str, lane: str) -> tuple[dict[str, Any], str]:
    if re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", release) is None:
        raise SpeedGateError("identity proof requires a versioned release")
    qualification = load(root / "releases" / release / "qualification.json")
    binding = qualification.get("observed_gates", {}).get("native_identity_decision")
    decision = bound_document(root, binding, "native_identity_decision")
    if (decision.get("artifact_type") != "omp_ninfer_founder_gate_decision"
            or type(decision.get("schema_version")) is not int or decision["schema_version"] != 1
            or decision.get("release") != release or decision.get("status") == "draft"
            or decision.get("rule", {}).get("quality_admission") != IDENTITY_RULE
            or lane not in decision.get("lanes", [])):
        raise SpeedGateError("release decision does not allow identity-first admission for this lane")
    return decision, binding["sha256"]


def default_native_build(spec: dict[str, Any], lane: str) -> str:
    profile = spec.get("build_profile")
    if (lane not in ("rtx3090", "rtx4090") or spec.get("lane") != lane
            or not isinstance(profile, str)
            or re.fullmatch(r"native-v[0-9]+\.[0-9]+\.[0-9]+(?:-beta\.[0-9]+)?-" + lane, profile) is None):
        raise SpeedGateError("identity-first requires the default native build profile; "
                             "output-changing build variants require a powered screen")
    return profile


def determinism_run(directory: Path) -> tuple[dict[str, str], str, dict[str, bytes]]:
    """Normalize retained native-screen responses, excluding only transport tool IDs."""
    from quality_screen import FROZEN_SCREEN_IDS
    from redaction_screen import ScreenError, native_arm

    try:
        identity = native_identity(native_arm(load(directory / "arm.json")))
        data = (directory / "responses.jsonl").read_bytes()
        outputs = {}
        for line in data.decode("utf-8-sig").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            case = row["case_id"]
            if (case in outputs or row.get("error") or "content" not in row
                    or not isinstance(row.get("content") or "", str)
                    or not isinstance(row.get("reasoning") or "", str)):
                raise SpeedGateError("determinism requires unique, successful retained responses")
            calls = row.get("tool_calls") or []
            if not isinstance(calls, list) or any(not isinstance(call, dict) for call in calls):
                raise SpeedGateError("determinism tool calls must be ordered objects")
            projection = {"content": row.get("content") or "", "reasoning": row.get("reasoning") or "",
                          "tool_calls": [{key: value for key, value in call.items() if key != "id"}
                                         for call in calls]}
            outputs[case] = json.dumps(projection, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=False, allow_nan=False).encode("utf-8")
        if set(outputs) != set(FROZEN_SCREEN_IDS[:80]):
            raise SpeedGateError("determinism must contain the frozen 80 prompts exactly once")
    except (ScreenError, KeyError, TypeError, AttributeError, UnicodeError) as error:
        raise SpeedGateError("invalid retained native determinism run") from error
    return identity, hashlib.sha256(data).hexdigest(), outputs


def create_identity_proof(gate: dict[str, Any], captures: Sequence[dict[str, Any]], plan: dict[str, Any],
                          incumbent: Path, candidate: Path, spec: dict[str, Any], *,
                          root: Path | None = None) -> dict[str, Any]:
    """Compare actual retained bytes before projecting a public, hash-bound admission receipt."""
    from quality_screen import FROZEN_DETERMINISM_MEMBERSHIP

    root = root if root is not None else ROOT
    lane = spec.get("lane")
    profile = default_native_build(spec, lane)
    _, decision_sha = identity_decision(root, gate["release"], lane)
    result = reduce(gate, captures, plan, root=root)
    if not result["gate_passed"] or not result["normalized_outputs_identical"]:
        raise SpeedGateError("identity-first requires every speed-ABBA case byte-identical to the incumbent")
    previous, previous_sha, a = determinism_run(incumbent)
    current, current_sha, b = determinism_run(candidate)
    if a != b:
        raise SpeedGateError("identity-first requires 80/80 retained determinism outputs byte-identical")
    value = {
        "artifact_type": "omp-ninfer.native-identity-proof", "schema_version": 1, "status": "passed",
        "release": gate["release"], "lane": lane, "decision_sha256": decision_sha,
        "candidate": current, "predecessor": previous, "build_profile": profile,
        "speed_abba": {"declaration": declaration(gate, root=root),
                       "plan": prescreen(gate, result["arms"][1]["identity"], root=root),
                       "arms": result["arms"]},
        "determinism": {
            **FROZEN_DETERMINISM_MEMBERSHIP, "compared": 80, "identical": 80,
            "incumbent_responses_sha256": previous_sha, "candidate_responses_sha256": current_sha,
            "outputs": [{"id": case, "incumbent_sha256": hashlib.sha256(a[case]).hexdigest(),
                         "candidate_sha256": hashlib.sha256(b[case]).hexdigest()} for case in sorted(a)],
        },
        "comparison_method": "retained-output-bytes",
        "raw_prompts_outputs_or_secrets_included": False,
    }
    validate_identity_proof(value, root, gate["release"], {"id": lane + "-windows-native", **current},
                            previous, spec)
    return value


def validate_identity_proof(value: Any, root: Path, release: str, variant: dict[str, Any],
                            predecessor: dict[str, Any], spec: dict[str, Any]) -> None:
    """Shared binder/verifier admission; counts and booleans cannot replace the per-case evidence."""
    from quality_screen import FROZEN_DETERMINISM_MEMBERSHIP, FROZEN_SCREEN_IDS

    lane = variant["id"].split("-")[0]
    profile = default_native_build(spec, lane)
    decision, decision_sha = identity_decision(root, release, lane)
    fields = {"artifact_type", "schema_version", "status", "release", "lane", "decision_sha256",
              "candidate", "predecessor", "build_profile", "speed_abba", "determinism",
              "comparison_method", "raw_prompts_outputs_or_secrets_included"}
    if (not isinstance(value, dict) or set(value) != fields
            or value.get("artifact_type") != "omp-ninfer.native-identity-proof"
            or type(value.get("schema_version")) is not int or value["schema_version"] != 1
            or value.get("status") != "passed" or value.get("release") != release or value.get("lane") != lane
            or value.get("decision_sha256") != decision_sha or value.get("build_profile") != profile
            or value.get("comparison_method") != "retained-output-bytes"
            or value.get("raw_prompts_outputs_or_secrets_included") is not False):
        raise SpeedGateError("identity proof must be this release's content-safe decision-bound receipt")
    previous, current = native_identity(predecessor), native_identity(variant)
    if value["predecessor"] != previous or value["candidate"] != current:
        raise SpeedGateError("identity proof must bind the exact candidate and incumbent native identities")
    if current["model_artifact_sha256"] != previous["model_artifact_sha256"]:
        raise SpeedGateError("identity-first requires the same incumbent model")
    try:
        speed = value["speed_abba"]
        gate = declaration(speed["declaration"], root=root)
        arms = speed["arms"]
        if (gate["release"] != release or not isinstance(arms, list) or len(arms) != 4
                or identity_differences(gate, arms, speed["plan"], root=root)):
            raise SpeedGateError("identity proof speed ABBA must match its complete declaration and plan")
        for index, arm in enumerate(arms):
            expected = previous if ORDER[index] == "A" else current
            if (arm["arm"] != ORDER[index] or type(arm["index"]) is not int or arm["index"] != index
                    or arm["identity"] != {"binary_sha256": expected["server_binary_sha256"],
                                           "configuration_sha256": expected["configuration_sha256"]}
                    or request_suite(arm["requests"]) != gate["request_suite"]):
                raise SpeedGateError("identity proof speed ABBA identities and every declared case must match")
            for row in arm["requests"]:
                if type(row["completion_tokens"]) is not int or row["completion_tokens"] <= 0:
                    raise SpeedGateError("identity proof speed counts must be positive integers")
                positive_number(row["decode_seconds"], "decode_seconds")
                require_sha256(row["normalized_output_sha256"], "normalized_output_sha256")
        maps = [{row["id"]: row["normalized_output_sha256"] for row in arm["requests"]} for arm in arms]
        if any(outputs != maps[0] for outputs in maps[1:]):
            raise SpeedGateError("identity proof requires every speed-ABBA output byte-identical")
        thresholds = recorded_thresholds(gate["decision"], release)
        all_cases = summarize(arms, set(maps[0]), thresholds["every_case_minimum"])
        roles = summarize(arms, set(gate["role_case_ids"]), thresholds["every_case_minimum"])
        if (roles["weighted_decode_ratio"] < thresholds["weighted_minimum"]
                or all_cases["weighted_decode_ratio"] < thresholds["weighted_minimum"]
                or all_cases["minimum_case_ratio"] < thresholds["every_case_minimum"]):
            raise SpeedGateError("identity proof speed ABBA must pass its recorded thresholds")
        determinism = value["determinism"]
        seal = decision["sealed_incumbent_determinism"][lane]
        if (any(determinism.get(key) != expected for key, expected in FROZEN_DETERMINISM_MEMBERSHIP.items())
                or any(seal.get(key) != expected for key, expected in FROZEN_DETERMINISM_MEMBERSHIP.items())
                or seal["identity"] != previous
                or determinism["incumbent_responses_sha256"] != require_sha256(
                    seal["responses_sha256"], "sealed incumbent responses_sha256")
                or type(determinism["compared"]) is not int or determinism["compared"] != 80
                or type(determinism["identical"]) is not int or determinism["identical"] != 80):
            raise SpeedGateError("identity proof must bind 80/80 outputs from the sealed incumbent")
        require_sha256(determinism["candidate_responses_sha256"], "candidate responses_sha256")
        outputs = determinism["outputs"]
        if (not isinstance(outputs, list) or len(outputs) != 80
                or {row["id"] for row in outputs} != set(FROZEN_SCREEN_IDS[:80])):
            raise SpeedGateError("identity proof determinism membership must be the frozen 80 prompts")
        for row in outputs:
            if (set(row) != {"id", "incumbent_sha256", "candidate_sha256"}
                    or require_sha256(row["incumbent_sha256"], "incumbent output") != require_sha256(
                        row["candidate_sha256"], "candidate output")):
                raise SpeedGateError("identity proof requires 80/80 byte-identical determinism outputs")
    except (KeyError, TypeError, AttributeError, IndexError) as error:
        raise SpeedGateError("malformed identity proof evidence") from error


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
    identity = commands.add_parser("identity-proof", help="compare ABBA and sealed native determinism bytes")
    identity.add_argument("--capture", type=Path, action="append", required=True)
    identity.add_argument("--plan", type=Path, required=True)
    identity.add_argument("--incumbent-determinism", type=Path, required=True, help="sealed native run directory")
    identity.add_argument("--candidate-determinism", type=Path, required=True, help="fresh native run directory")
    identity.add_argument("--release-spec", type=Path, required=True, help="candidate packaged release-spec.json")
    for command in (plan, reduction, identity):
        command.add_argument("--root", type=Path,
                             help="repository root containing release qualification (default: this checkout)")
        command.add_argument("--gate", type=Path, required=True)
        command.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prescreen":
            result = prescreen(load(args.gate), load(args.candidate), root=args.root)
        elif args.command == "identity-proof":
            result = create_identity_proof(
                load(args.gate), [load(path) for path in args.capture], load(args.plan),
                args.incumbent_determinism, args.candidate_determinism, load(args.release_spec), root=args.root)
        else:
            result = reduce(load(args.gate), [load(path) for path in args.capture], load(args.plan), root=args.root)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"speed_gate: {exc}", file=sys.stderr)
        return 2
    if args.command == "prescreen":
        print(json.dumps({"gate_sha256": result["gate_sha256"]}, sort_keys=True))
        return 0
    if args.command == "identity-proof":
        print(json.dumps({"status": result["status"], "lane": result["lane"]}, sort_keys=True))
        return 0
    print(json.dumps({key: result[key] for key in ("status", "gate_predictive", "thresholds")}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
