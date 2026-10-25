"""The native qualification receipt names the transport its OMP golden run actually used."""
from __future__ import annotations

import importlib.util
from copy import deepcopy
import hashlib
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


def protocol_fixture() -> dict[str, Any]:
    """Synthetic schema fixture, not an observed native run or qualification receipt."""
    return {
        "artifact_type": "ninfer_agent_protocol_smoke", "schema_version": 2, "contract": "product",
        "status_identity_verified": True, "authenticated_session_identity": True,
        "anthropic_count_tokens": 12,
        "structured_output": {"chat_json_schema": True, "responses_json_schema": True},
        "tool_result_array_finish_reason": "stop", "stream_finish_reason": "stop",
        "nonstream_finish_reason": "stop", "completion_tokens": 4,
        "same_session_reuse_path": "private_input_replay", "isolated_session_reuse_path": "root",
        "responses_session_lifecycle": {
            "first_turn_completed": True, "continuation_completed": True, "fork_count": 2,
            "cross_session_status": 404, "stored_route_isolation_status": 404,
            "parent_delete_status": 200, "parent_get_after_delete_status": 404,
            "surviving_descendants_retrieved": True, "surviving_descendant_continued": True,
        },
    }


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

    def compose_fixture(self, directory: Path, *, first: bool, previous: str = "", mutation=None) -> dict:
        # Immutable identity/restart/security/rollback data plus explicit synthetic protocol
        # inputs exercise composition only. No old protocol result is relabelled schema 2.
        base = json.loads((ROOT / "releases/v0.9.1/qualification/rtx3090.json").read_text())
        identity, config = deepcopy(base["identity"]), base["configuration"]
        native_config_path = ROOT / "profiles/v0.13.1/rtx3090/server-config.json"
        native_config = json.loads(native_config_path.read_text())
        identity.update(
            config_sha256=hashlib.sha256(native_config_path.read_bytes()).hexdigest(),
            configuration_sha256=hashlib.sha256(native_config_path.read_bytes()).hexdigest(),
            deployment_profile=native_config["deployment_profile"])
        state, evidence = directory / "state", directory / "evidence"
        (state / "receipts").mkdir(parents=True)
        evidence.mkdir()
        def save(path: Path, value: dict) -> Path:
            path.write_text(json.dumps(value))
            return path
        release = native_config["release_id"]
        save(state / "qualification-summary.json", {
            "artifact_type": "ninfer_native_qualification_summary", "status": "passed",
            "schema_version": 1, "release_id": release, "qualified_utc": base["qualified_utc"],
            "server_binary_sha256": identity["server_binary_sha256"],
            "configuration_sha256": identity["configuration_sha256"]})
        for phase in ("context_128k", "benchmark_c1", "security", "restart"):
            save(state / "receipts" / f"{phase}.json", {"status": "passed"})
        for phase, filename in (("protocol", "agent-protocol.json"),
                                ("pressure_protocol", "agent-protocol-pressure.json")):
            payload = protocol_fixture()
            path = save(evidence / filename, payload)
            wrapper = {"status": "passed", "protocol": payload,
                       "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            if phase == "protocol":
                wrapper["identity"] = identity
                wrapper["startup_attestation"] = {"request_log_schema": 30, "gpu_uuid_verified": True}
            else:
                wrapper.update(device_state_slots=4, host_context_mib="9366.578125")
            save(state / "receipts" / (phase + ".json"), wrapper)
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
        for name, section in (("long-context-128k.json", "long_session"),
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
        config_path = save(directory / "config.json", native_config)
        spec_path = save(directory / "spec.json", {"release_id": release,
            "host_context_translation": {"host_context_bytes": 12284837888},
            "lifecycle": {field: config[field]
                          for field in ("managed_stop", "graceful_stop_timeout_seconds")}})
        checksums = directory / "SHA256SUMS"
        sbom = package["filename"].removesuffix(".tar.gz") + ".spdx.json"
        checksums.write_text(f"{package['sha256']}  {package['filename']}\n{package['sbom_sha256']}  {sbom}\n")
        args = SimpleNamespace(state_dir=state, evidence_dir=evidence,
            build_receipt=build_path, checksums=checksums, server_start=start_path,
            server_config=config_path, release_spec=spec_path, profile="MTP3", omp_version="omp/18.4.0",
            persistence_note=base["persistence"]["note"], rollback_note="test lineage", limitation=["test fixture"])
        if mutation:
            mutation(args)
        return COMPOSE.compose(args)

    def test_canonical_payloads_and_actual_phase_wrappers_survive_composition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = self.compose_fixture(Path(directory), first=True)
        for section in ("protocol", "protocol_under_pool_pressure"):
            self.assertEqual(receipt[section]["protocol"], protocol_fixture())
            self.assertEqual(receipt["deterministic_gates"][section], "passed")
            self.assertNotIn("checks_passed", receipt[section])
            for field in ("identity", "status", "checks"):
                self.assertNotIn(field, receipt[section]["protocol"])
        self.assertEqual(receipt["configuration"]["host_context_bytes"], 12284837888)
        self.assertEqual(receipt["configuration"]["host_context_mib"], "11715.734375")
        self.assertEqual(receipt["protocol_under_pool_pressure"]["host_context_mib"], "9366.578125")
        self.assertEqual(receipt["configuration"]["admission_headroom_mib"], 768)
        self.assertTrue(receipt["configuration"]["checkpoint_require_origin_auth"])
        for field in ("host_state_slots", "host_kv_mib", "max_private_continuations"):
            self.assertNotIn(field, receipt["configuration"])

    def test_nonpassing_canonical_payload_cannot_be_hidden_by_passed_phase(self) -> None:
        for phase, filename in (("protocol", "agent-protocol.json"),
                                ("pressure_protocol", "agent-protocol-pressure.json")):
            def mutate(args):
                path = args.evidence_dir / filename
                payload = json.loads(path.read_text())
                payload["isolated_session_reuse_path"] = "private_input_replay"
                path.write_text(json.dumps(payload))
                phase_path = args.state_dir / "receipts" / (phase + ".json")
                wrapper = json.loads(phase_path.read_text())
                wrapper.update(protocol=payload, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                phase_path.write_text(json.dumps(wrapper))
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(SystemExit, "isolated_session_reuse_path"):
                    self.compose_fixture(Path(directory), first=True, mutation=mutate)

    def test_protocol_bytes_and_phase_payload_must_match_recorded_evidence(self) -> None:
        for mutation in ("payload", "bytes", "identity"):
            def mutate(args):
                path = args.evidence_dir / "agent-protocol.json"
                if mutation == "payload":
                    value = json.loads(path.read_text())
                    value["completion_tokens"] += 1
                    path.write_text(json.dumps(value))
                elif mutation == "bytes":
                    path.write_bytes(path.read_bytes() + b"\n")
                else:
                    path = args.state_dir / "receipts/protocol.json"
                    wrapper = json.loads(path.read_text())
                    wrapper["identity"]["binary_sha256"] = "0" * 64
                    path.write_text(json.dumps(wrapper))
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(SystemExit, "phase payload|phase-recorded bytes|different binary"):
                    self.compose_fixture(Path(directory), first=True, mutation=mutate)

    def test_shared_host_pressure_must_be_reduced_without_legacy_slots(self) -> None:
        for mutation in ("missing", "full", "slots", "legacy", "schema"):
            def mutate(args):
                path = args.state_dir / "receipts/pressure_protocol.json"
                wrapper = json.loads(path.read_text())
                if mutation == "missing":
                    wrapper.pop("host_context_mib")
                elif mutation == "full":
                    wrapper["host_context_mib"] = "11715.734375"
                elif mutation == "slots":
                    wrapper["device_state_slots"] = 1
                elif mutation == "legacy":
                    wrapper["host_state_slots"] = 8
                else:
                    path = args.server_config
                    wrapper = json.loads(path.read_text())
                    wrapper["schema_version"] = 3
                path.write_text(json.dumps(wrapper))
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(SystemExit, "shared Host|device-state|legacy|schema 4"):
                    self.compose_fixture(Path(directory), first=True, mutation=mutate)

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


class ProductProtocolContractTests(unittest.TestCase):
    def test_exact_private_reuse_and_isolated_public_path_classes_are_accepted(self) -> None:
        for private in ("private_endpoint", "private_input_replay", "private_long_anchor"):
            for isolated in ("root", "shared_stable_prefix"):
                with self.subTest(private=private, isolated=isolated):
                    value = protocol_fixture()
                    value.update(same_session_reuse_path=private, isolated_session_reuse_path=isolated)
                    self.assertEqual(COMPOSE.product_protocol_errors(value), [])

    def test_missing_canonical_fields_and_legacy_success_envelopes_are_refused(self) -> None:
        for field in protocol_fixture():
            with self.subTest(field=field):
                value = protocol_fixture()
                value.pop(field)
                self.assertTrue(COMPOSE.product_protocol_errors(value))
        for value in (
            {"status": "passed", "identity": {}, "checks": {"all": True}},
            {**protocol_fixture(), "schema_version": 1},
            {**protocol_fixture(), "schema_version": 2.0},
            {**protocol_fixture(), "contract": "public"},
            {**protocol_fixture(), "status": "passed"},
            {**protocol_fixture(), "identity": {}},
            {**protocol_fixture(), "checks": {}},
        ):
            with self.subTest(value=value):
                self.assertTrue(COMPOSE.product_protocol_errors(value))

    def test_authentication_reuse_stream_tool_and_usage_failures_are_refused(self) -> None:
        for field, failed in (
            ("status_identity_verified", False), ("authenticated_session_identity", 1),
            ("same_session_reuse_path", "root"), ("same_session_reuse_path", []),
            ("isolated_session_reuse_path", "private_input_replay"),
            ("isolated_session_reuse_path", None), ("anthropic_count_tokens", 0),
            ("anthropic_count_tokens", True), ("completion_tokens", -1),
            ("completion_tokens", True), ("tool_result_array_finish_reason", "error"),
            ("stream_finish_reason", "length"), ("nonstream_finish_reason", None),
        ):
            with self.subTest(field=field, failed=failed):
                value = protocol_fixture()
                value[field] = failed
                self.assertTrue(COMPOSE.product_protocol_errors(value))

    def test_all_structured_and_responses_oracles_must_pass(self) -> None:
        for section in ("structured_output", "responses_session_lifecycle"):
            for field in protocol_fixture()[section]:
                with self.subTest(section=section, field=field):
                    value = protocol_fixture()
                    value[section].pop(field)
                    self.assertTrue(COMPOSE.product_protocol_errors(value))
                    value = protocol_fixture()
                    value[section][field] = False
                    self.assertTrue(COMPOSE.product_protocol_errors(value))
            value = protocol_fixture()
            value[section] = []
            self.assertTrue(COMPOSE.product_protocol_errors(value))

    def test_shared_host_bytes_require_exact_positive_mib(self) -> None:
        self.assertEqual(COMPOSE.shared_host_context_bytes("14787.734375"), 15506063360)
        self.assertEqual(COMPOSE.shared_host_context_bytes("11715.734375"), 12284837888)
        for value in (None, True, 11715.734375, "", "0", "-1", "NaN", "Infinity", "0.0000001"):
            with self.subTest(value=value):
                self.assertIsNone(COMPOSE.shared_host_context_bytes(value))


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
