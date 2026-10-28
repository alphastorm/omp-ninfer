"""Contract predicates for a native Windows lane's release qualification receipt.

Every published native lane carries a ``ninfer_windows_release_qualification`` receipt at
``releases/<version>/qualification/<lane>.json``. The runtime fork's canonical orchestrator
(``tools/qualification/qualify_native.py``) stages it from its own phase receipts; the release
tree copies it unchanged and nothing in this repository composes one. ``verify_release.py``,
``compose_route_acceptance.py`` and the native route-acceptance driver judge it with these
predicates: the two honest rollback outcomes, and the canonical schema-2 product protocol
evidence and shared Host profile that native components from v0.7.0 must carry. Published
historical receipts remain immutable; no legacy checks map is synthesized.
"""

from __future__ import annotations

import re
from decimal import Decimal, DecimalException
from typing import Any


def first_release_rollback(value: Any) -> bool:
    """The orchestrator's explicit zero-direction first-lineage result, not a passed rollback."""
    return (isinstance(value, dict) and value.get("status") == "not_applicable"
            and type(value.get("directions")) is int and value["directions"] == 0
            and value.get("reason") == "first release of the lineage"
            and value.get("intermediate_release") is None and value.get("stops", []) == [])


def bidirectional_rollback(value: Any) -> bool:
    """A passed rollback: both directions through a named predecessor, back to the candidate."""
    if not isinstance(value, dict) or value.get("status") != "passed":
        return False
    predecessor = value.get("intermediate_release")
    candidate = value.get("active_release_after", value.get("active_release"))
    return (type(value.get("directions")) is int and value["directions"] == 2
            and isinstance(predecessor, str) and predecessor != ""
            and isinstance(candidate, str) and candidate != "" and predecessor != candidate)


def product_protocol_errors(value: Any) -> list[str]:
    """Validate the real schema-2 smoke result, never an authored legacy checks map."""
    if not isinstance(value, dict):
        return ["canonical product protocol must be an object"]
    errors = []
    for field, expected in (("artifact_type", "ninfer_agent_protocol_smoke"),
                            ("schema_version", 2), ("contract", "product")):
        if type(value.get(field)) is not type(expected) or value[field] != expected:
            errors.append(f"{field} must be {expected!r}")
    for field in ("status", "checks", "identity"):
        if field in value:
            errors.append(f"canonical protocol must not carry legacy {field}")
    for field in ("status_identity_verified", "authenticated_session_identity"):
        if value.get(field) is not True:
            errors.append(f"{field} must be true")
    private = value.get("same_session_reuse_path")
    if not isinstance(private, str) or private not in {
            "private_endpoint", "private_input_replay", "private_long_anchor"}:
        errors.append("same_session_reuse_path must select private continuation reuse")
    isolated = value.get("isolated_session_reuse_path")
    if not isinstance(isolated, str) or isolated not in {"root", "shared_stable_prefix"}:
        errors.append("isolated_session_reuse_path must miss private continuation reuse")
    count = value.get("anthropic_count_tokens")
    if type(count) is not int or count <= 0:
        errors.append("anthropic_count_tokens must be positive")
    completion = value.get("completion_tokens")
    if type(completion) is not int or completion < 0:
        errors.append("completion_tokens must be a nonnegative integer")
    finishes = ("stop", "length", "tool_calls")
    if value.get("tool_result_array_finish_reason") not in finishes:
        errors.append("tool_result_array_finish_reason is invalid")
    if (value.get("stream_finish_reason") not in finishes
            or value.get("stream_finish_reason") != value.get("nonstream_finish_reason")):
        errors.append("stream and nonstream finish reasons must be valid and equal")
    structured = value.get("structured_output")
    if not isinstance(structured, dict) or any(
            structured.get(field) is not True
            for field in ("chat_json_schema", "responses_json_schema")):
        errors.append("structured_output must pass Chat and Responses JSON-schema checks")
    responses = value.get("responses_session_lifecycle")
    if not isinstance(responses, dict):
        errors.append("responses_session_lifecycle must be an object")
    else:
        for field in ("first_turn_completed", "continuation_completed",
                      "surviving_descendants_retrieved", "surviving_descendant_continued"):
            if responses.get(field) is not True:
                errors.append(f"responses_session_lifecycle.{field} must be true")
        forks = responses.get("fork_count")
        if type(forks) is not int or forks < 2:
            errors.append("responses_session_lifecycle.fork_count must be at least two")
        for field, status in (("cross_session_status", 404), ("stored_route_isolation_status", 404),
                              ("parent_delete_status", 200), ("parent_get_after_delete_status", 404)):
            if type(responses.get(field)) is not int or responses[field] != status:
                errors.append(f"responses_session_lifecycle.{field} must be {status}")
    return errors


def shared_host_context_bytes(value: Any) -> int | None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value) is None:
        return None
    try:
        size = Decimal(value) * 1048576
        if size.is_finite() and size > 0 and size == size.to_integral_value():
            return int(size)
    except DecimalException:
        pass
    return None


def native_protocol_qualification_errors(receipt: dict[str, Any]) -> list[str]:
    """The native release shape preserves actual phase wrappers around canonical payloads."""
    errors = []
    gates = receipt.get("deterministic_gates", {})
    if not isinstance(gates, dict):
        gates = {}
    for section in ("protocol", "protocol_under_pool_pressure"):
        phase = receipt.get(section)
        if not isinstance(phase, dict):
            errors.append(f"{section} must carry its actual phase receipt")
            continue
        if phase.get("status") != "passed" or gates.get(section) != "passed":
            errors.append(f"{section} phase and deterministic gate must pass")
        errors.extend(f"{section}.protocol: {error}"
                      for error in product_protocol_errors(phase.get("protocol")))
        if "host_state_slots" in phase or "checks_passed" in phase:
            errors.append(f"{section} must not use legacy split-pool/check-count fields")
    configuration = receipt.get("configuration", {})
    if not isinstance(configuration, dict):
        return [*errors, "configuration must describe the shared Host profile"]
    for field in ("host_state_slots", "host_kv_mib", "max_private_continuations"):
        if field in configuration:
            errors.append(f"configuration must not use legacy {field}")
    full_bytes = shared_host_context_bytes(configuration.get("host_context_mib"))
    if (full_bytes is None or type(configuration.get("host_context_bytes")) is not int
            or configuration["host_context_bytes"] != full_bytes):
        errors.append("configuration shared Host MiB/bytes must agree exactly")
    if configuration.get("concurrency") != 1 or type(configuration.get("concurrency")) is not int:
        errors.append("canonical native protocol requires concurrency one")
    slots = configuration.get("device_state_slots")
    if type(slots) is not int or slots < 0:
        errors.append("configuration device_state_slots must be a nonnegative integer")
    pressure = receipt.get("protocol_under_pool_pressure", {})
    if isinstance(pressure, dict):
        pressure_bytes = shared_host_context_bytes(pressure.get("host_context_mib"))
        if pressure_bytes is None or full_bytes is None or pressure_bytes >= full_bytes:
            errors.append("pressure protocol must record a positive reduced shared Host budget")
        if type(pressure.get("device_state_slots")) is not int or pressure.get("device_state_slots") != slots:
            errors.append("pressure protocol must retain the profile's extra device-state slots")
    return errors
