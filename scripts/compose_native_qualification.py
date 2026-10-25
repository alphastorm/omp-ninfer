#!/usr/bin/env python3
"""Compose a native Windows lane's release qualification receipt from its orchestrator window.

The receipt shipped at ``releases/<version>/qualification/<lane>.json`` is the
``ninfer_windows_release_qualification`` form every published native lane carries: the
orchestrator's phase evidence reshaped into the sections the release tree, its verifier, and
the public pages read. Current native composition requires schema 4 shared Host configuration
and preserves canonical schema-2 product protocol payloads inside their actual phase receipts.
Published historical receipts remain immutable; no legacy checks map is synthesized.

Inputs are the artifacts the qualification window already produced, nothing is measured here:

- the orchestrator's state directory (``qualification-summary.json``, ``receipts/*.json``),
- the target host's evidence directory (``agent-protocol.json``, ``agent-protocol-pressure.json``,
  ``checkpoint-restart-proof.json``, ``long-context-128k.json``, ``managed-c1.json``,
  ``state-security.json``, ``omp-events.jsonl``),
- the packager's ``package-build-receipt.json`` and outer ``SHA256SUMS``,
- the installed release's first request-log record (``server_start``), which carries the
  runtime's own build identity and the GPU it ran on,
- the OMP version the golden-equivalent phase ran (``omp --version`` on the target),
- the lane's ``server-config.json`` and ``release-spec.json`` from the runtime tree.

The free-text fields a receipt carries (limitations, the persistence and rollback notes) are
authored per release and passed explicitly; the script never invents prose.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, DecimalException
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ARTIFACT_TYPE = "ninfer_windows_release_qualification"
GATE_PHASES = {
    "protocol": "protocol",
    "protocol_under_pool_pressure": "pressure_protocol",
    "long_session": "context_128k",
    "persistence": "restart",
    "rollback": "rollback",
    "state_security": "security",
    "golden_equivalent": "omp",
    "benchmark_c1": "benchmark_c1",
}
EVIDENCE_FILES = {
    "protocol": "agent-protocol.json",
    "pressure": "agent-protocol-pressure.json",
    "restart": "checkpoint-restart-proof.json",
    "long_context": "long-context-128k.json",
    "c1": "managed-c1.json",
    "security": "state-security.json",
}


def load_json(path: Path) -> Any:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            return json.loads(raw.decode(encoding))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise SystemExit(f"error: {path} is not UTF-8 or UTF-16 JSON")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"error: {message}")


def first_release_rollback(value: Any) -> bool:
    """The orchestrator's explicit zero-direction first-lineage result, not a passed rollback."""
    return (isinstance(value, dict) and value.get("status") == "not_applicable"
            and type(value.get("directions")) is int and value["directions"] == 0
            and value.get("reason") == "first release of the lineage"
            and value.get("intermediate_release") is None and value.get("stops", []) == [])


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


def omp_event_lines(events_path: Path) -> list[str]:
    raw = events_path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise SystemExit(f"error: {events_path} is not UTF-8 or UTF-16")
    return [line for line in text.splitlines() if line.strip()]


def omp_event_count(events_path: Path) -> int:
    return len(omp_event_lines(events_path))


def omp_transport(events_path: Path) -> str:
    """The one API every assistant message of the golden run went through, as OMP recorded it."""
    apis = set()
    for line in omp_event_lines(events_path):
        event = json.loads(line)
        message = event.get("message") if event.get("type") == "message_end" else None
        if isinstance(message, dict) and message.get("role") == "assistant":
            apis.add(message.get("api"))
    require(len(apis) == 1 and isinstance(next(iter(apis)), str),
            f"{events_path}: assistant messages must name exactly one API, found {sorted(map(str, apis))}")
    return next(iter(apis))


def parse_checksums(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, name = line.partition("  ")
        require(len(digest) == 64 and name != "", f"{path}: malformed line {line!r}")
        entries[name.strip()] = digest.lower()
    return entries


def compose(args: argparse.Namespace) -> dict[str, Any]:
    state_dir: Path = args.state_dir
    evidence_dir: Path = args.evidence_dir
    summary = load_json(state_dir / "qualification-summary.json")
    receipts = {path.stem: load_json(path) for path in (state_dir / "receipts").glob("*.json")}
    evidence = {name: load_json(evidence_dir / file) for name, file in EVIDENCE_FILES.items()}
    build = load_json(args.build_receipt)
    start = load_json(args.server_start)
    server_config = load_json(args.server_config)
    spec = load_json(args.release_spec)

    require(summary.get("artifact_type") == "ninfer_native_qualification_summary",
            "state directory summary is not an orchestrator summary")
    require(summary.get("status") == "passed", "the window did not pass")
    require(build.get("artifact_type") == "ninfer_windows_package_build_receipt",
            "build receipt is not a package build receipt")
    require(start.get("event") == "server_start", "server-start record is not a server_start event")
    release_id = summary["release_id"]
    for name, value in (("build receipt", build.get("release_id")),
                        ("server config", server_config.get("release_id")),
                        ("release spec", spec.get("release_id"))):
        require(value == release_id, f"{name} release_id {value!r} differs from the window's {release_id!r}")
    identity_start = start["identity"]
    require(identity_start["binary_sha256"] == build["binaries"]["server_sha256"]
            == summary["server_binary_sha256"],
            "the served binary, the packaged binary, and the summary disagree")
    require(identity_start["config_sha256"] == build["config_sha256"]
            == summary["configuration_sha256"],
            "the served configuration, the packaged configuration, and the summary disagree")
    for phase, key in (("protocol", "protocol"), ("pressure_protocol", "pressure")):
        recorded = receipts[phase]
        evidence_path = evidence_dir / EVIDENCE_FILES[key]
        require(recorded.get("status") == "passed", f"phase {phase} did not pass")
        require(recorded.get("protocol") == evidence[key],
                f"{EVIDENCE_FILES[key]} differs from its actual phase payload")
        require(recorded.get("sha256") == hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
                f"{EVIDENCE_FILES[key]} differs from its phase-recorded bytes")
    require(receipts["protocol"]["identity"]["binary_sha256"] == identity_start["binary_sha256"],
            "protocol phase ran against a different binary")
    for phase, key in (("context_128k", "long_context"), ("benchmark_c1", "c1"),
                       ("security", "security")):
        require(receipts[phase]["status"] == "passed" and evidence[key]["status"] == "passed",
                f"phase {phase} did not pass")
    for phase in ("restart", "omp"):
        require(receipts[phase]["status"] == "passed", f"phase {phase} did not pass")
    rollback_receipt = receipts["rollback"]
    first_release = first_release_rollback(rollback_receipt)
    require(rollback_receipt["status"] == "passed" or first_release,
            "phase rollback did not pass")
    if first_release:
        require(not receipts["preflight"]["initial"].get("previous_release")
                and rollback_receipt.get("active_release") == f"{release_id}-{build['patch_stack_sha'][:12]}",
                "first-release rollback must name only the active candidate, never a predecessor")

    identity = {
        "build_type": identity_start["build_type"],
        "cuda_compiler": identity_start["cuda_compiler"],
        "cuda_toolkit": identity_start["cuda_toolkit"],
        "cxx_compiler": identity_start["cxx_compiler"],
        "model_id": identity_start["model_id"],
        "target": identity_start["target"],
        "weights_id": identity_start["weights_id"],
        "gpu_index": start["environment"]["device"],
        "gpu_name": start["environment"]["gpu_name"],
        "source_dirty": identity_start["source_dirty"],
        "binary_sha256": identity_start["binary_sha256"],
        "build_profile": build["build_profile"],
        "config_sha256": build["config_sha256"],
        "cuda_architecture": identity_start["cuda_architecture"],
        "deployment_profile": build["deployment_profile"],
        "model_artifact_sha256": build["model_sha256"],
        "patch_stack_sha": build["patch_stack_sha"],
        "upstream_base_sha": build["upstream_base_sha"],
        "lineage_base_sha": build["lineage_base_sha"],
        "source_commit": build["patch_stack_sha"],
        "server_binary_sha256": build["binaries"]["server_sha256"],
        "configuration_sha256": build["config_sha256"],
    }
    engine = server_config["engine"]
    cache = server_config["context_cache"]
    speculative = server_config["speculative"]
    require(server_config.get("schema_version") == 4,
            "native composition requires a schema 4 shared Host configuration")
    host_bytes = shared_host_context_bytes(cache.get("host_context_mib"))
    require(host_bytes is not None and host_bytes == spec["host_context_translation"]["host_context_bytes"],
            "shared Host configuration differs from the release specification's byte budget")
    configuration = {
        "public_model_id": server_config["model_id"],
        "max_context": engine["max_context"],
        "kv_capacity": engine["kv_capacity"],
        "kv_dtype": engine["kv_dtype"],
        "prefill_chunk": engine["prefill_chunk"],
        "speculative_backend": speculative["backend"],
        "speculative_draft_tokens": speculative["draft_tokens"],
        "concurrency": engine["max_concurrency"],
        "device_state_slots": cache["device_state_slots"],
        "host_context_mib": cache["host_context_mib"],
        "host_context_bytes": host_bytes,
        "admission_headroom_mib": engine["admission_headroom_mib"],
        "checkpoint_require_origin_auth": server_config["session_checkpoint"]["require_origin_auth"],
        "managed_stop": spec["lifecycle"]["managed_stop"],
        "graceful_stop_timeout_seconds": spec["lifecycle"]["graceful_stop_timeout_seconds"],
    }
    if "gpu_keep_warm_ms" in engine:
        # Packages built since the field existed declare it; older qualification windows omit it.
        configuration["gpu_keep_warm_ms"] = engine["gpu_keep_warm_ms"]
    long_context = evidence["long_context"]
    long_session = {key: long_context[key] for key in
                    ("prompt_tokens", "completion_tokens", "elapsed_seconds", "exact_output",
                     "fixture_sha256")}
    restart = evidence["restart"]
    persistence = {
        "managed_stop": restart["managed_stop"],
        "explicit_control": restart["explicit_control"],
        "managed_stop_flush": restart["managed_stop_flush"],
        "checkpoint_files": restart["checkpoint_files"],
        "checkpoint_bytes": restart["checkpoint_bytes"],
        "restart_seconds": restart["restart_seconds"],
        "process_replaced": restart["new_pid"] != restart["old_pid"],
        "restored_cached_input_tokens": restart["cached_input_tokens"],
        "exact_output": restart["exact_output"],
        "note": args.persistence_note,
    }
    rollback = ({
        "directions": 0, "reason": rollback_receipt["reason"],
        "intermediate_release": None, "stops": [],
        "active_release_after": rollback_receipt["active_release"],
        "note": args.rollback_note, "status": "not_applicable",
    } if first_release else {
        "directions": rollback_receipt["directions"],
        "intermediate_release": rollback_receipt["intermediate_release"],
        "active_release_after": rollback_receipt["active_release"],
        "stops": rollback_receipt["stops"],
        "candidate_stop_mode": rollback_receipt["candidate_stop_mode"],
        "predecessor_stop_mode": rollback_receipt["predecessor_stop_mode"],
        "note": args.rollback_note,
        "status": rollback_receipt["status"],
    })
    omp = receipts["omp"]
    require(omp_event_count(evidence_dir / "omp-events.jsonl") == omp["events"],
            "omp-events.jsonl does not carry the event count the omp phase recorded")
    golden_equivalent = {
        "artifact_type": "ninfer_omp_golden_equivalent_receipt",
        "omp": {
            "transport": omp_transport(evidence_dir / "omp-events.jsonl"),
            "version": args.omp_version,
            "events": omp["events"],
            "typed_tool_name": omp["typed_tool_name"],
            "tool_results": omp["tool_results"],
        },
        "oracles": {
            "exact_visible_final_answer": "passed" if omp["exact_final_answer"] else "failed",
            "typed_tool_invocation": "passed" if omp["typed_tool_name"] else "failed",
            "tool_result_continuation": "passed" if omp["tool_results"] else "failed",
        },
        "raw_transcript_included": False,
        "schema_version": 1,
        "status": omp["status"],
    }
    c1 = evidence["c1"]
    benchmark_c1 = {key: c1[key] for key in
                    ("prompt_tokens", "completion_tokens", "prefill_tokens_per_second",
                     "decode_tokens_per_second", "mtp_acceptance_percent", "wall_seconds",
                     "max_memory_used_mib", "max_power_w", "max_temperature_c",
                     "max_gpu_utilization_percent")}
    checksums = parse_checksums(args.checksums)
    require(len(checksums) == build["checksums"]["entries"],
            f"{args.checksums} carries {len(checksums)} entries, the build receipt says "
            f"{build['checksums']['entries']}")
    require(checksums.get(build["package"]["filename"]) == build["package"]["sha256"],
            "the outer SHA256SUMS does not carry the packaged bytes")
    sbom_name = build["package"]["filename"].removesuffix(".tar.gz") + ".spdx.json"
    require(sbom_name in checksums, f"checksums carry no SBOM entry {sbom_name}")
    support = build["support_assets"]
    package = {
        "filename": build["package"]["filename"],
        "sha256": build["package"]["sha256"],
        "bytes": build["package"]["bytes"],
        "sbom_sha256": checksums[sbom_name],
        "installer_sha256": support["installer_sha256"],
        "controller_sha256": support["controller_sha256"],
        "gpu_owner_controller_sha256": support["gpu_owner_controller_sha256"],
        "state_protection_sha256": support["state_protection_sha256"],
    }
    receipt: dict[str, Any] = {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": summary["schema_version"],
        "status": summary["status"],
        "qualified_utc": summary["qualified_utc"],
        "release_id": release_id,
        "profile": args.profile,
        "identity": identity,
        "configuration": configuration,
        "protocol": receipts["protocol"],
        "protocol_under_pool_pressure": receipts["pressure_protocol"],
        "long_session": long_session,
        "persistence": persistence,
        "rollback": rollback,
        "state_security": evidence["security"],
        "golden_equivalent": golden_equivalent,
        "benchmark_c1": benchmark_c1,
    }
    receipt["deterministic_gates"] = {
        section: receipts[phase]["status"] for section, phase in GATE_PHASES.items()
    }
    require(all(value == "passed" or (section == "rollback" and first_release
                                    and value == "not_applicable")
                for section, value in receipt["deterministic_gates"].items()),
            "a gate section did not pass")
    protocol_errors = native_protocol_qualification_errors(receipt)
    require(not protocol_errors, "; ".join(protocol_errors))
    receipt["limitations"] = list(args.limitation)
    receipt["beta_qualified"] = True
    receipt["package"] = package
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--state-dir", type=Path, required=True,
                        help="orchestrator state directory (qualification-summary.json, receipts/)")
    parser.add_argument("--evidence-dir", type=Path, required=True,
                        help="copy of the target host's evidence directory")
    parser.add_argument("--build-receipt", type=Path, required=True,
                        help="the packager's package-build-receipt.json")
    parser.add_argument("--checksums", type=Path, required=True,
                        help="the packager's outer SHA256SUMS (the closed distribution set)")
    parser.add_argument("--server-start", type=Path, required=True,
                        help="the installed release's first request-log record (server_start)")
    parser.add_argument("--server-config", type=Path, required=True,
                        help="the lane's server-config.json")
    parser.add_argument("--release-spec", type=Path, required=True,
                        help="the lane's release-spec.json")
    parser.add_argument("--profile", default="MTP3")
    parser.add_argument("--omp-version", required=True,
                        help="the OMP build the golden-equivalent phase ran, e.g. omp/18.0.9")
    parser.add_argument("--persistence-note", required=True)
    parser.add_argument("--rollback-note", required=True)
    parser.add_argument("--limitation", action="append", default=[], required=True,
                        help="one limitation sentence; repeat for each")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = compose(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"composed {args.output} for {receipt['release_id']} "
          f"(C1 {receipt['benchmark_c1']['decode_tokens_per_second']:.1f} tok/s, "
          f"128K {receipt['long_session']['elapsed_seconds']:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
