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

import hashlib
import json
import re
from decimal import Decimal, DecimalException
from typing import Any

NATIVE_RECEIPT_POLICY_FIELDS = (
    "max_context", "kv_capacity", "kv_dtype", "concurrency", "prefill_chunk",
    "device_state_slots", "admission_headroom_mib", "host_context_mib", "host_context_bytes",
    "speculative_backend", "speculative_draft_tokens", "public_model_id",
)


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


def native_runtime_configuration(spec: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Project the exact packaged policy, checking spec/config agreement before binding it."""
    lane = spec.get("lane")
    floor = {"rtx3090": 768, "rtx4090": 640}.get(lane)
    if (spec.get("artifact_type") != "ninfer_windows_release_spec"
            or spec.get("schema_version") != 5 or floor is None
            or config.get("artifact_type") != "ninfer_windows_server_config"
            or config.get("schema_version") != 4):
        raise ValueError("native profile requires lane-bound schema-5 spec and schema-4 config")
    for field in ("release_id", "deployment_profile"):
        if not isinstance(spec.get(field), str) or not spec[field] or spec[field] != config.get(field):
            raise ValueError(f"native spec/config {field} must match")
    engine, cache, speculative = (config.get(key, {}) for key in
                                   ("engine", "context_cache", "speculative"))
    shape = spec.get("runtime_shape", {})
    if not all(isinstance(value, dict) for value in (engine, cache, speculative, shape)):
        raise ValueError("native profile must describe engine, cache, speculation and runtime_shape")
    fit, draft = shape.get("fit", {}), shape.get("draft_tokens", {})
    if not isinstance(fit, dict) or not isinstance(draft, dict):
        raise ValueError("native runtime_shape must describe fit and draft bounds")
    for field in ("max_context", "kv_capacity", "max_concurrency", "pending_timeout_ms", "prefill_chunk"):
        if type(engine.get(field)) is not int or engine[field] <= 0:
            raise ValueError(f"native engine.{field} must be a positive integer")
    if engine["kv_capacity"] < engine["max_context"]:
        raise ValueError("native shared KV capacity must cover the per-request context ceiling")
    if not isinstance(engine.get("kv_dtype"), str) or not engine["kv_dtype"]:
        raise ValueError("native KV dtype must name the configured format")
    slots, headroom = cache.get("device_state_slots"), engine.get("admission_headroom_mib")
    if type(slots) is not int or slots < 0 or type(headroom) is not int or headroom < floor:
        raise ValueError(f"native fit requires nonnegative extra slots and at least {floor} MiB headroom")
    if engine["max_concurrency"] > 1 and (slots < 2 or not 180000 <= engine["pending_timeout_ms"] <= 2147483647):
        raise ValueError("concurrent native policy requires two extra slots and a 180-second pending timeout")
    for actual, expected, field in (
        (shape.get("max_concurrency"), engine["max_concurrency"], "max_concurrency"),
        (fit.get("device_state_slots"), slots, "device_state_slots"),
        (fit.get("admission_headroom_mib"), headroom, "admission_headroom_mib"),
        (shape.get("speculative_backend"), speculative.get("backend"), "speculative_backend"),
    ):
        if type(actual) is not type(expected) or actual != expected:
            raise ValueError(f"native runtime_shape.{field} must match server-config")
    backend, width = speculative.get("backend"), speculative.get("draft_tokens")
    if backend not in ("mtp", "dflash2") or type(width) is not int or width <= 0:
        raise ValueError("native speculative backend/draft width is invalid")
    minimum, maximum = draft.get("min"), draft.get("max")
    if (type(minimum) is not int or width < minimum
            or (maximum is not None and (type(maximum) is not int or width > maximum))):
        raise ValueError("native draft width must meet the packaged runtime_shape bounds")
    seam = ("Q4_G64_FP16", "host-mapped") if backend == "dflash2" else ("artifact", "device")
    if (fit.get("draft_mlp_device_format"), fit.get("token_embedding_residency")) != seam:
        raise ValueError("native fit load seam must match its speculative backend")
    host = shared_host_context_bytes(cache.get("host_context_mib"))
    translation = spec.get("host_context_translation", {})
    if (host is None or not isinstance(translation, dict)
            or type(translation.get("host_context_bytes")) is not int
            or translation["host_context_bytes"] != host):
        raise ValueError("native spec/config must bind the same exact shared Host byte budget")
    model = config.get("model_id")
    if not isinstance(model, str) or not model:
        raise ValueError("native server-config must name its public model")
    return {
        "max_context": engine["max_context"], "kv_capacity": engine["kv_capacity"],
        "kv_dtype": engine["kv_dtype"], "concurrency": engine["max_concurrency"],
        "pending_timeout_ms": engine["pending_timeout_ms"], "prefill_chunk": engine["prefill_chunk"],
        "device_state_slots": slots, "admission_headroom_mib": headroom,
        "host_context_mib": cache["host_context_mib"], "host_context_bytes": host,
        "speculative_backend": backend, "speculative_draft_tokens": width, "public_model_id": model,
    }


def native_status_errors(status: Any, variant: dict[str, Any], configuration: dict[str, Any]) -> list[str]:
    """Authenticated config identity binds timeout/backend; status also proves the active scheduler."""
    if not isinstance(status, dict):
        return ["native status must be an object"]
    errors = []
    identity = status.get("identity", {})
    if not isinstance(identity, dict):
        return ["native status identity must be an object"]
    for field, expected in (
        ("binary_sha256", variant.get("server_binary_sha256")),
        ("config_sha256", variant.get("configuration_sha256")),
        ("model_artifact_sha256", variant.get("model_artifact_sha256")),
    ):
        if identity.get(field) != expected or not isinstance(expected, str):
            errors.append(f"native served {field} must match the candidate")
    if (status.get("status") != "ok" or status.get("artifact_type") != "ninfer_server_status"
            or type(status.get("schema_version")) is not int or status["schema_version"] not in (1, 2)
            or identity.get("source_dirty") is not False):
        errors.append("native status must be healthy and clean")
    scheduler, runtime = status.get("scheduler"), status.get("runtime")
    if (not isinstance(scheduler, dict) or type(scheduler.get("max_concurrency")) is not int
            or scheduler["max_concurrency"] != configuration["concurrency"]):
        errors.append("native served concurrency must match the candidate")
    if (not isinstance(runtime, dict) or type(runtime.get("max_context")) is not int
            or runtime["max_context"] != configuration["max_context"]):
        errors.append("native served context ceiling must match the candidate")
    return errors


def matches_native_configuration(value: Any, expected: dict[str, Any]) -> bool:
    return (isinstance(value, dict) and set(value) == set(expected)
            and all(type(value[key]) is type(wanted) and value[key] == wanted for key, wanted in expected.items()))


def native_probe_summary(probes: dict[str, Any]) -> dict[str, Any]:
    """Content-safe projection of actual probe receipts, not an authored boolean checks map."""
    def digest(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    fleet = probes["fleet"]
    summary = {"fleet": {
        "sha256": digest(fleet), "artifact_type": fleet.get("artifact_type"),
        "identity": {field: fleet.get("identity", {}).get(field) for field in
                     ("binary_sha256", "config_sha256", "model_artifact_sha256", "model_id", "source_dirty")},
        "branches": fleet.get("branches"),
        "transient_retries": fleet.get("transient_retries"),
        "steps": [step.get("step") for step in fleet.get("steps", [])],
    }}
    if "fanout" in probes:
        fanout = probes["fanout"]
        scenarios = fanout.get("scenarios", [])
        summary["fanout"] = {
            "sha256": digest(fanout), "artifact_type": fanout.get("artifact_type"),
            "ok": fanout.get("ok"), "arguments": {field: fanout.get("arguments", {}).get(field)
                for field in ("arm", "scenario", "fanout_concurrency", "branches", "model")},
            "statuses": {},
            "scenarios": [{"name": row.get("name"), "ok": row.get("ok"),
                "requests": [{field: request.get(field) for field in
                    ("label", "ok", "http_status", "submitted_monotonic_s", "completed_monotonic_s")}
                    for request in row.get("requests", [])]} for row in scenarios],
        }
        for phase in ("server_before", "server_after"):
            status = fanout.get("identity", {}).get(phase, {}).get("body", {})
            summary["fanout"]["statuses"][phase] = {
                **{field: status.get(field) for field in ("artifact_type", "schema_version", "status")},
                "identity": {field: status.get("identity", {}).get(field) for field in
                             ("binary_sha256", "config_sha256", "model_artifact_sha256", "source_dirty")},
                "runtime": {"max_context": status.get("runtime", {}).get("max_context")},
                "scheduler": {"max_concurrency": status.get("scheduler", {}).get("max_concurrency")},
            }
    for name in ("parallel", "compaction"):
        if name not in probes:
            continue
        proof = probes[name]
        summary[name] = {
            "sha256": digest(proof), "artifact_type": proof.get("artifact_type"), "passed": proof.get("passed"),
            "model": proof.get("model"), "omp": {field: proof.get("omp", {}).get(field)
                                                for field in ("sha256", "version")},
            "checks": proof.get("checks"),
        }
        if name == "parallel":
            summary[name].update(max_in_flight=proof.get("max_in_flight"),
                                 scenarios=[{field: row.get(field) for field in
                                     ("scenario", "passed", "max_in_flight", "overlap_seconds", "checks")}
                                     for row in proof.get("scenarios", [])])
        else:
            summary[name].update(committed=sum(row.get("committed") is True for row in proof.get("compactions", [])),
                                 parameters=proof.get("parameters"))
    return summary


def native_probe_acceptance_errors(configuration: dict[str, Any], probes: Any,
                                   variant: dict[str, Any], client_sha256: str | None = None) -> list[str]:
    """Judge sequential regression separately from C2 fanout and real stock-OMP proofs."""
    if not isinstance(probes, dict):
        return ["native probe acceptance must carry actual probe projections"]
    errors = []
    names = ["fleet"] + (["fanout", "parallel", "compaction"] if configuration["concurrency"] > 1 else [])
    for name in names:
        row = probes.get(name)
        if not isinstance(row, dict) or not isinstance(row.get("sha256"), str) or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None:
            errors.append(f"native {name} must bind its actual probe receipt")
    if errors:
        return errors
    fleet = probes.get("fleet", {})
    identity = fleet.get("identity", {})
    if (fleet.get("artifact_type") != "omp_ninfer_fleet_fanout_probe" or fleet.get("branches") != 4
            or fleet.get("transient_retries") != 0
            or identity.get("model_id") != configuration["public_model_id"]
            or any(identity.get(actual) != variant.get(expected) for actual, expected in (
                ("binary_sha256", "server_binary_sha256"), ("config_sha256", "configuration_sha256"),
                ("model_artifact_sha256", "model_artifact_sha256")))
            or not {"base_prefill", "warm_edit", "checkpoint_save", "session_delete",
                    *(f"branch_{index}" for index in range(4))}.issubset(fleet.get("steps", []))):
        errors.append("native fleet sequential regression must complete on the candidate without retries")
    if configuration["concurrency"] <= 1:
        return errors
    fanout = probes.get("fanout", {})
    arguments = fanout.get("arguments", {})
    scenarios = fanout.get("scenarios", [])
    if (fanout.get("artifact_type") != "omp_ninfer_concurrency_probe" or fanout.get("ok") is not True
            or arguments.get("arm") != variant["id"].split("-")[0] + "-C2-acceptance"
            or arguments.get("scenario") != ["fanout"] or arguments.get("fanout_concurrency") != 4
            or arguments.get("branches") != 4 or arguments.get("model") != configuration["public_model_id"]
            or len(scenarios) != 1 or scenarios[0].get("name") != "fanout" or scenarios[0].get("ok") is not True):
        errors.append("native C2 acceptance requires the real four-way fanout scenario")
    for status in ("server_before", "server_after"):
        errors.extend(native_status_errors(fanout.get("statuses", {}).get(status), variant, configuration))
    requests = scenarios[0].get("requests", []) if len(scenarios) == 1 else []
    branches = [row for row in requests if row.get("label") in {f"branch-{index}" for index in range(4)}]
    intervals = [(row.get("submitted_monotonic_s"), row.get("completed_monotonic_s")) for row in branches]
    valid_times = all(type(start) in (int, float) and type(end) in (int, float) and end > start
                      for start, end in intervals)
    if (len(requests) != 5 or len(branches) != 4 or len({row["label"] for row in branches}) != 4
            or any(row.get("ok") is not True or row.get("http_status") != 200 for row in requests)
            or not valid_times or not any(a < d and c < b for index, (a, b) in enumerate(intervals)
                                          for c, d in intervals[index + 1:])):
        errors.append("native fanout must complete five requests with genuinely overlapping branches")
    model = f"ninfer-native-{variant['id'].split('-')[0][3:]}/{configuration['public_model_id']}"
    for name, artifact in (("parallel", "omp_ninfer_parallel_proof"), ("compaction", "omp_ninfer_long_session_proof")):
        proof = probes.get(name, {})
        checks = proof.get("checks")
        if (proof.get("artifact_type") != artifact or proof.get("passed") is not True
                or proof.get("model") != model or (client_sha256 is not None
                and proof.get("omp", {}).get("sha256") != client_sha256)):
            errors.append(f"native C2 {name} must pass using the candidate's documented stock client/model")
        if name == "parallel":
            runs = proof.get("scenarios", [])
            mandatory = {"logged_requests", "all_logged_requests_completed", "single_server_instance",
                         "provider_limit_respected", "concurrency_expected"}
            if (proof.get("max_in_flight") != configuration["concurrency"]
                    or {row.get("scenario") for row in runs} != {"subagents", "sessions"}
                    or any(row.get("passed") is not True or row.get("max_in_flight") != 2
                           or type(row.get("overlap_seconds")) not in (int, float) or row["overlap_seconds"] <= 0
                           or not isinstance(row.get("checks"), dict) or not mandatory.issubset(row["checks"])
                           or not all(value is True for value in row["checks"].values())
                           for row in runs)):
                errors.append("native C2 must prove OMP subagent/session overlap at provider limit two")
        elif (not isinstance(checks, dict)
              or not {"every_turn_completed", "compactions_committed", "no_failed_compaction",
                      "control_recalled_after_each_compaction", "one_session"}.issubset(checks)
              or not all(value is True for value in checks.values())
              or type(proof.get("committed")) is not int or proof["committed"] < 2):
            errors.append("native C2 must commit and recall through two automatic compactions")
    return errors


def native_protocol_qualification_errors(receipt: dict[str, Any],
                                         candidate_configuration: dict[str, Any] | None = None) -> list[str]:
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
    concurrency = configuration.get("concurrency")
    if type(concurrency) is not int or concurrency < 1:
        errors.append("canonical native protocol requires positive integer concurrency")
    slots = configuration.get("device_state_slots")
    if type(slots) is not int or slots < 0:
        errors.append("configuration device_state_slots must be a nonnegative integer")
    if type(concurrency) is int and concurrency > 1:
        if type(slots) is not int or slots < 2:
            errors.append("concurrent native protocol requires at least two extra device-state slots")
        # The fork's schema-1 orchestrator receipt does not project pending_timeout_ms.
        # The product supplies it from the separately authenticated packaged server-config.
        pending = (candidate_configuration if candidate_configuration is not None
                   else configuration).get("pending_timeout_ms")
        if type(pending) is not int or not 180000 <= pending <= 2147483647:
            errors.append("concurrent native protocol requires at least a 180-second pending timeout")
    pressure = receipt.get("protocol_under_pool_pressure", {})
    if isinstance(pressure, dict):
        pressure_bytes = shared_host_context_bytes(pressure.get("host_context_mib"))
        if pressure_bytes is None or full_bytes is None or pressure_bytes >= full_bytes:
            errors.append("pressure protocol must record a positive reduced shared Host budget")
        if type(pressure.get("device_state_slots")) is not int or pressure.get("device_state_slots") != slots:
            errors.append("pressure protocol must retain the profile's extra device-state slots")
    return errors
