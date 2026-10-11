"""The native qualification receipt names the transport its OMP golden run actually used."""
from __future__ import annotations

import importlib.util
import json

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "compose_native_qualification", ROOT / "scripts" / "compose_native_qualification.py")
assert SPEC is not None and SPEC.loader is not None
COMPOSE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPOSE)


def transcript(*apis: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = [{"type": "agent_start"}]
    for api in apis:
        events.append({"type": "message_start", "message": {"role": "assistant", "api": api}})
        events.append({"type": "message_end", "message": {"role": "assistant", "api": api}})
    events.append({"type": "message_end", "message": {"role": "toolResult"}})
    return events


class FirstReleaseRollbackTests(unittest.TestCase):
    def test_only_an_explicit_empty_first_lineage_is_not_applicable(self) -> None:
        valid = {"status": "not_applicable", "directions": 0,
                 "reason": "first release of the lineage"}
        self.assertTrue(COMPOSE.first_release_rollback(valid))
        for fields in ({"directions": False}, {"directions": 2}, {"status": "passed"},
                       {"reason": "no hardware available"}, {"intermediate_release": "older"},
                       {"stops": [{"outcome": "graceful"}]}):
            with self.subTest(fields=fields):
                self.assertFalse(COMPOSE.first_release_rollback({**valid, **fields}))

    def compose_fixture(self, directory: Path, *, first: bool, previous: str = "") -> dict:
        # Reuse a public measured fixture, not private host files or the current lane set.
        base = json.loads((ROOT / "releases/v0.9.1/qualification/rtx3090.json").read_text())
        identity, config = base["identity"], base["configuration"]
        state, evidence = directory / "state", directory / "evidence"
        (state / "receipts").mkdir(parents=True)
        evidence.mkdir()
        def save(path: Path, value: dict) -> Path:
            path.write_text(json.dumps(value))
            return path
        release = base["release_id"]
        save(state / "qualification-summary.json", {
            "artifact_type": "ninfer_native_qualification_summary", "status": "passed",
            "schema_version": 1, "release_id": release, "qualified_utc": base["qualified_utc"],
            "server_binary_sha256": identity["server_binary_sha256"],
            "configuration_sha256": identity["configuration_sha256"]})
        for phase in ("protocol", "context_128k", "benchmark_c1", "security", "restart"):
            save(state / "receipts" / f"{phase}.json", {"status": "passed"})
        pressure = base["protocol_under_pool_pressure"]
        save(state / "receipts/pressure_protocol.json", {
            "status": "passed", "device_state_slots": pressure["device_state_slots"],
            "host_state_slots": pressure["host_state_slots"]})
        save(state / "receipts/preflight.json", {"initial": {"previous_release": previous}})
        rollback = ({"status": "not_applicable", "directions": 0,
                     "reason": "first release of the lineage",
                     "active_release": f"{release}-{identity['patch_stack_sha'][:12]}"} if first else
                    {**base["rollback"], "active_release": base["rollback"]["active_release_after"]})
        save(state / "receipts/rollback.json", rollback)
        events = transcript("openai-responses")
        (evidence / "omp-events.jsonl").write_text("\n".join(map(json.dumps, events)))
        save(state / "receipts/omp.json", {"status": "passed", "events": len(events),
            "typed_tool_name": "read", "tool_results": 1, "exact_final_answer": True})
        for name, section in (("agent-protocol.json", "protocol"),
                              ("agent-protocol-pressure.json", "protocol"),
                              ("long-context-128k.json", "long_session"),
                              ("managed-c1.json", "benchmark_c1"),
                              ("state-security.json", "state_security")):
            save(evidence / name, {**base[section], "status": "passed"})
        save(evidence / "checkpoint-restart-proof.json", {**base["persistence"],
            "old_pid": 1, "new_pid": 2, "cached_input_tokens": base["persistence"]["restored_cached_input_tokens"]})
        package = base["package"]
        build = {"artifact_type": "ninfer_windows_package_build_receipt", "release_id": release,
                 "binaries": {"server_sha256": identity["server_binary_sha256"]},
                 "config_sha256": identity["configuration_sha256"], "package": package,
                 "model_sha256": identity["model_artifact_sha256"], "checksums": {"entries": 2},
                 "support_assets": {field: package[field] for field in ("installer_sha256",
                    "controller_sha256", "gpu_owner_controller_sha256", "state_protection_sha256")},
                 **{field: identity[field] for field in ("build_profile", "deployment_profile",
                    "patch_stack_sha", "upstream_base_sha", "lineage_base_sha")}}
        build_path = save(directory / "build.json", build)
        start_path = save(directory / "start.json", {"event": "server_start", "identity": identity,
            "environment": {"device": identity["gpu_index"], "gpu_name": identity["gpu_name"]}})
        config_path = save(directory / "config.json", {"release_id": release,
            "model_id": config["public_model_id"],
            "engine": {**{field: config[field] for field in ("max_context", "kv_capacity", "kv_dtype", "prefill_chunk")},
                       "max_concurrency": config["concurrency"]},
            "context_cache": {field: config[field] for field in ("device_state_slots", "host_state_slots",
                              "host_kv_mib", "max_private_continuations")},
            "speculative": {"backend": config["speculative_backend"], "draft_tokens": config["speculative_draft_tokens"]}})
        spec_path = save(directory / "spec.json", {"release_id": release, "lifecycle": {field: config[field]
            for field in ("managed_stop", "graceful_stop_timeout_seconds")}})
        checksums = directory / "SHA256SUMS"
        sbom = package["filename"].removesuffix(".tar.gz") + ".spdx.json"
        checksums.write_text(f"{package['sha256']}  {package['filename']}\n{package['sbom_sha256']}  {sbom}\n")
        return COMPOSE.compose(SimpleNamespace(state_dir=state, evidence_dir=evidence,
            build_receipt=build_path, checksums=checksums, server_start=start_path,
            server_config=config_path, release_spec=spec_path, profile="MTP3", omp_version="omp/18.4.0",
            persistence_note=base["persistence"]["note"], rollback_note="test lineage", limitation=["test fixture"]))

    def test_composition_keeps_not_applicable_visible_and_upgrades_unchanged(self) -> None:
        for first in (True, False):
            with self.subTest(first=first), tempfile.TemporaryDirectory() as directory:
                receipt = self.compose_fixture(Path(directory), first=first)
                self.assertEqual(receipt["status"], "passed")
                self.assertEqual(receipt["deterministic_gates"]["rollback"], "not_applicable" if first else "passed")
                self.assertEqual(receipt["rollback"]["directions"], 0 if first else 2)

    def test_first_release_with_a_previous_release_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(SystemExit, "never a predecessor"):
            self.compose_fixture(Path(directory), first=True, previous="older")


class OmpTransportTest(unittest.TestCase):
    def write(self, directory: Path, events: list[dict[str, Any]], encoding: str) -> Path:
        path = directory / "omp-events.jsonl"
        path.write_bytes("\n".join(json.dumps(event) for event in events).encode(encoding))
        return path

    def test_reports_the_api_the_client_used_in_either_encoding(self) -> None:
        # Windows PowerShell redirection writes UTF-16; OMP 18.2.3 talks Responses to NInfer.
        with tempfile.TemporaryDirectory() as directory:
            for encoding in ("utf-16", "utf-8"):
                path = self.write(Path(directory), transcript("openai-responses", "openai-responses"),
                                  encoding)
                self.assertEqual(COMPOSE.omp_transport(path), "openai-responses")
            path = self.write(Path(directory), transcript("openai-completions"), "utf-8")
            self.assertEqual(COMPOSE.omp_transport(path), "openai-completions")

    def test_refuses_a_run_without_one_assistant_api(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for events in (transcript("openai-responses", "openai-completions"), transcript()):
                path = self.write(Path(directory), events, "utf-8")
                with self.assertRaises(SystemExit):
                    COMPOSE.omp_transport(path)


if __name__ == "__main__":
    unittest.main()
