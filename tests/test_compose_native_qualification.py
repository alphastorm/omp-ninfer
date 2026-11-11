"""The native lane receipt contract the verifier and route acceptance judge receipts with."""
from __future__ import annotations

import importlib.util
import json
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "compose_native_qualification", ROOT / "scripts" / "compose_native_qualification.py")
assert SPEC is not None and SPEC.loader is not None
CONTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT)
# A shipped orchestrator receipt: canonical payloads inside their actual phase wrappers.
SHIPPED_RECEIPT = json.loads(
    (ROOT / "releases/v0.14.0/qualification/rtx3090.json").read_text(encoding="utf-8"))


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
        self.assertTrue(CONTRACT.first_release_rollback(valid))
        for fields in ({"directions": False}, {"directions": 2}, {"status": "passed"},
                       {"reason": "no hardware available"}, {"intermediate_release": "older"},
                       {"stops": [{"outcome": "graceful"}]}):
            with self.subTest(fields=fields):
                self.assertFalse(CONTRACT.first_release_rollback({**valid, **fields}))


class NativeProtocolQualificationTests(unittest.TestCase):
    def test_shipped_orchestrator_receipt_satisfies_the_contract(self) -> None:
        self.assertEqual(CONTRACT.native_protocol_qualification_errors(SHIPPED_RECEIPT), [])

    def test_nonpassing_canonical_payload_cannot_be_hidden_by_passed_phase(self) -> None:
        for section in ("protocol", "protocol_under_pool_pressure"):
            with self.subTest(section=section):
                receipt = deepcopy(SHIPPED_RECEIPT)
                receipt[section]["protocol"]["isolated_session_reuse_path"] = "private_input_replay"
                self.assertEqual(CONTRACT.native_protocol_qualification_errors(receipt), [
                    f"{section}.protocol: isolated_session_reuse_path must miss private "
                    "continuation reuse"])

    def test_shared_host_pressure_must_be_reduced_without_legacy_fields(self) -> None:
        full = SHIPPED_RECEIPT["configuration"]["host_context_mib"]
        reduced = "pressure protocol must record a positive reduced shared Host budget"
        for label, mutate, expected in (
            ("missing pressure budget",
             lambda receipt: receipt["protocol_under_pool_pressure"].pop("host_context_mib"), reduced),
            ("unreduced pressure budget",
             lambda receipt: receipt["protocol_under_pool_pressure"].update(host_context_mib=full),
             reduced),
            ("pressure device slots",
             lambda receipt: receipt["protocol_under_pool_pressure"].update(device_state_slots=1),
             "pressure protocol must retain the profile's extra device-state slots"),
            ("legacy pressure slots",
             lambda receipt: receipt["protocol_under_pool_pressure"].update(host_state_slots=8),
             "protocol_under_pool_pressure must not use legacy split-pool/check-count fields"),
            ("legacy host pool",
             lambda receipt: receipt["configuration"].update(host_kv_mib=11264),
             "configuration must not use legacy host_kv_mib"),
            ("host bytes disagree",
             lambda receipt: receipt["configuration"].update(
                 host_context_bytes=receipt["configuration"]["host_context_bytes"] + 1),
             "configuration shared Host MiB/bytes must agree exactly"),
        ):
            with self.subTest(label=label):
                receipt = deepcopy(SHIPPED_RECEIPT)
                mutate(receipt)
                self.assertEqual(CONTRACT.native_protocol_qualification_errors(receipt), [expected])


class NativeBuildProfileTests(unittest.TestCase):
    def spec(self, lane: str = "rtx3090") -> dict[str, Any]:
        profiles = {key: f"native-v0.8.0-beta.3{suffix}-{lane}" for key, suffix in
                    (("default", ""), ("a8", "-a8"), ("tc", "-tc"), ("tc-a8", "-tc-a8"))}
        return {"lane": lane, "build_profile": profiles["default"], "build_profiles": profiles}

    def test_committed_allowlist_selects_each_exact_profile(self) -> None:
        for lane in ("rtx3090", "rtx4090"):
            spec = self.spec(lane)
            for profile in spec["build_profiles"].values():
                with self.subTest(lane=lane, profile=profile):
                    self.assertEqual(CONTRACT.native_build_profile(spec, profile), profile)
                    packaged = {**spec, "build_profile": profile}
                    self.assertEqual(CONTRACT.native_build_profile(packaged, profile), profile)

    def test_absent_allowlist_keeps_published_exact_equality(self) -> None:
        for release in ("v0.16.2", "v0.17.0"):
            for lane in ("rtx3090", "rtx4090"):
                path = ROOT / "releases" / release / "profiles" / lane / "release-spec.json"
                spec = json.loads(path.read_text(encoding="utf-8"))
                receipt = json.loads((ROOT / "releases" / release / "qualification" /
                                      f"{lane}.json").read_text(encoding="utf-8"))
                config = json.loads(path.with_name("server-config.json").read_text(encoding="utf-8"))
                configuration = CONTRACT.native_runtime_configuration(spec, config)
                observed = receipt["identity"]["build_profile"]
                with self.subTest(release=release, lane=lane):
                    self.assertNotIn("build_profiles", spec)
                    self.assertEqual(CONTRACT.native_build_profile(spec, observed), observed)
                    self.assertEqual(CONTRACT.native_protocol_qualification_errors(
                        receipt, configuration, candidate_build_profile=observed), [])
                    with self.assertRaises(ValueError):
                        CONTRACT.native_build_profile(spec, observed + "-other")

    def test_present_invalid_allowlists_and_unlisted_profiles_fail_closed(self) -> None:
        spec = self.spec()
        profiles = spec["build_profiles"]
        for value in (None, [], {}, [*profiles.values()],
                      {key: profile for key, profile in profiles.items() if key != "tc-a8"},
                      {**profiles, "other": "native-other"},
                      {**profiles, "a8": profiles["default"]},
                      {**profiles, "a8": None}, {**profiles, "a8": ""}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                CONTRACT.native_build_profile({**spec, "build_profiles": value}, spec["build_profile"])
        for profile in (None, "", True, [], "native-v0.8.0-beta.3-uncommitted-rtx3090"):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                CONTRACT.native_build_profile(spec, profile)

    def test_qualification_binds_observed_profile_without_defaulting(self) -> None:
        profile = self.spec()["build_profiles"]["tc-a8"]
        receipt = deepcopy(SHIPPED_RECEIPT)
        receipt["identity"]["build_profile"] = profile
        self.assertEqual(CONTRACT.native_protocol_qualification_errors(
            receipt, candidate_build_profile=profile), [])
        for value in (None, self.spec()["build_profile"]):
            with self.subTest(value=value):
                receipt["identity"]["build_profile"] = value
                self.assertIn("qualification identity.build_profile must match the candidate",
                              CONTRACT.native_protocol_qualification_errors(
                                  receipt, candidate_build_profile=profile))

    def test_status_and_probe_projections_retain_the_selected_profile(self) -> None:
        profile = self.spec()["build_profiles"]["a8"]
        variant = {"server_binary_sha256": "b" * 64, "configuration_sha256": "c" * 64,
                   "model_artifact_sha256": "d" * 64, "build_profile": profile}
        configuration = {"concurrency": 1, "max_context": 131072, "public_model_id": "q38-ninfer"}
        identity = {"binary_sha256": "b" * 64, "config_sha256": "c" * 64,
                    "model_artifact_sha256": "d" * 64, "source_dirty": False,
                    "build_profile": profile, "model_id": "q38-ninfer"}
        status = {"artifact_type": "ninfer_server_status", "schema_version": 2, "status": "ok",
                  "identity": identity, "scheduler": {"max_concurrency": 1},
                  "runtime": {"max_context": 131072}}
        fleet = {"artifact_type": "omp_ninfer_fleet_fanout_probe", "identity": identity,
                 "branches": 4, "transient_retries": 0,
                 "steps": [{"step": step} for step in (
                     "base_prefill", "warm_edit", "checkpoint_save", "session_delete",
                     "branch_0", "branch_1", "branch_2", "branch_3")]}
        probes = {"fleet": fleet, "fanout": {
            "identity": {phase: {"body": status} for phase in ("server_before", "server_after")}}}
        summary = CONTRACT.native_probe_summary(probes)
        self.assertEqual(summary["fleet"]["identity"]["build_profile"], profile)
        for phase in ("server_before", "server_after"):
            self.assertEqual(summary["fanout"]["statuses"][phase]["identity"]["build_profile"], profile)
        self.assertEqual(CONTRACT.native_status_errors(status, variant, configuration), [])
        self.assertEqual(CONTRACT.native_probe_acceptance_errors(configuration, summary, variant), [])
        for value in (None, self.spec()["build_profile"]):
            with self.subTest(value=value):
                status["identity"]["build_profile"] = value
                self.assertIn("native served build_profile must match the candidate",
                              CONTRACT.native_status_errors(status, variant, configuration))
                wrong = CONTRACT.native_probe_summary(probes)
                self.assertIn("native fleet build_profile must match the candidate",
                              CONTRACT.native_probe_acceptance_errors(configuration, wrong, variant))


class ProductProtocolContractTests(unittest.TestCase):
    def test_exact_private_reuse_and_isolated_public_path_classes_are_accepted(self) -> None:
        for private in ("private_endpoint", "private_input_replay", "private_long_anchor"):
            for isolated in ("root", "shared_stable_prefix"):
                with self.subTest(private=private, isolated=isolated):
                    value = protocol_fixture()
                    value.update(same_session_reuse_path=private, isolated_session_reuse_path=isolated)
                    self.assertEqual(CONTRACT.product_protocol_errors(value), [])

    def test_missing_canonical_fields_and_legacy_success_envelopes_are_refused(self) -> None:
        for field in protocol_fixture():
            with self.subTest(field=field):
                value = protocol_fixture()
                value.pop(field)
                self.assertTrue(CONTRACT.product_protocol_errors(value))
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
                self.assertTrue(CONTRACT.product_protocol_errors(value))

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
                self.assertTrue(CONTRACT.product_protocol_errors(value))

    def test_all_structured_and_responses_oracles_must_pass(self) -> None:
        for section in ("structured_output", "responses_session_lifecycle"):
            for field in protocol_fixture()[section]:
                with self.subTest(section=section, field=field):
                    value = protocol_fixture()
                    value[section].pop(field)
                    self.assertTrue(CONTRACT.product_protocol_errors(value))
                    value = protocol_fixture()
                    value[section][field] = False
                    self.assertTrue(CONTRACT.product_protocol_errors(value))
            value = protocol_fixture()
            value[section] = []
            self.assertTrue(CONTRACT.product_protocol_errors(value))

    def test_shared_host_bytes_require_exact_positive_mib(self) -> None:
        self.assertEqual(CONTRACT.shared_host_context_bytes("14787.734375"), 15506063360)
        self.assertEqual(CONTRACT.shared_host_context_bytes("11715.734375"), 12284837888)
        for value in (None, True, 11715.734375, "", "0", "-1", "NaN", "Infinity", "0.0000001"):
            with self.subTest(value=value):
                self.assertIsNone(CONTRACT.shared_host_context_bytes(value))


if __name__ == "__main__":
    unittest.main()
