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
