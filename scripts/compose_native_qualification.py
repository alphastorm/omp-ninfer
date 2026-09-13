#!/usr/bin/env python3
"""Compose a native Windows lane's release qualification receipt from its orchestrator window.

The receipt shipped at ``releases/<version>/qualification/<lane>.json`` is the
``ninfer_windows_release_qualification`` form every published native lane carries: the
orchestrator's phase evidence reshaped into the sections the release tree, its verifier, and
the public pages read. Until v0.6.7 that reshaping was done by hand for every cut; this script
is the same composition, and it reproduces the v0.6.1 receipt from that window's inputs.

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
import json
import sys
from pathlib import Path
from typing import Any

ARTIFACT_TYPE = "ninfer_windows_release_qualification"
POOL_PRESSURE_WHY = (
    "The shipped Host StateImage pool hides a class of admission defect that only appears when "
    "StateImage capacity binds. The same fifteen checks run against the same installed bytes with "
    "the Host pool reduced to a third of the shipped size."
)
GATE_SECTIONS = (
    "protocol",
    "protocol_under_pool_pressure",
    "long_session",
    "persistence",
    "rollback",
    "state_security",
    "golden_equivalent",
    "benchmark_c1",
)
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


def omp_event_count(events_path: Path) -> int:
    raw = events_path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise SystemExit(f"error: {events_path} is not UTF-8 or UTF-16")
    return sum(1 for line in text.splitlines() if line.strip())


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
    for name in ("protocol", "pressure"):
        require(evidence[name]["identity"]["binary_sha256"] == identity_start["binary_sha256"],
                f"{EVIDENCE_FILES[name]} ran against a different binary")
    for phase, key in (("protocol", "protocol"), ("pressure_protocol", "pressure"),
                       ("context_128k", "long_context"), ("benchmark_c1", "c1"),
                       ("security", "security")):
        require(receipts[phase]["status"] == "passed" and evidence[key]["status"] == "passed",
                f"phase {phase} did not pass")
    for phase in ("restart", "rollback", "omp"):
        require(receipts[phase]["status"] == "passed", f"phase {phase} did not pass")

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
        "host_state_slots": cache["host_state_slots"],
        "host_kv_mib": cache["host_kv_mib"],
        "max_private_continuations": cache["max_private_continuations"],
        "managed_stop": spec["lifecycle"]["managed_stop"],
        "graceful_stop_timeout_seconds": spec["lifecycle"]["graceful_stop_timeout_seconds"],
    }
    pressure = evidence["pressure"]
    pressure_receipt = receipts["pressure_protocol"]
    require(all(pressure["checks"].values()), "pressure protocol carries a failed check")
    protocol_under_pool_pressure = {
        "artifact_type": pressure["artifact_type"],
        "why": POOL_PRESSURE_WHY,
        "device_state_slots": pressure_receipt["device_state_slots"],
        "host_state_slots": pressure_receipt["host_state_slots"],
        "checks_passed": len(pressure["checks"]),
        "status": pressure["status"],
    }
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
    rollback_receipt = receipts["rollback"]
    rollback = {
        "directions": rollback_receipt["directions"],
        "intermediate_release": rollback_receipt["intermediate_release"],
        "active_release_after": rollback_receipt["active_release"],
        "stops": rollback_receipt["stops"],
        "candidate_stop_mode": rollback_receipt["candidate_stop_mode"],
        "predecessor_stop_mode": rollback_receipt["predecessor_stop_mode"],
        "note": args.rollback_note,
        "status": rollback_receipt["status"],
    }
    omp = receipts["omp"]
    require(omp_event_count(evidence_dir / "omp-events.jsonl") == omp["events"],
            "omp-events.jsonl does not carry the event count the omp phase recorded")
    golden_equivalent = {
        "artifact_type": "ninfer_omp_golden_equivalent_receipt",
        "omp": {
            "transport": "openai-completions",
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
        "protocol": evidence["protocol"],
        "protocol_under_pool_pressure": protocol_under_pool_pressure,
        "long_session": long_session,
        "persistence": persistence,
        "rollback": rollback,
        "state_security": evidence["security"],
        "golden_equivalent": golden_equivalent,
        "benchmark_c1": benchmark_c1,
    }
    receipt["deterministic_gates"] = {
        section: "passed" if receipt[section].get("status", "passed") == "passed" else "failed"
        for section in GATE_SECTIONS
    }
    require(all(value == "passed" for value in receipt["deterministic_gates"].values()),
            "a gate section did not pass")
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
