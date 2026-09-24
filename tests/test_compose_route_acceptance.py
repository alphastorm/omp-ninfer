"""The route acceptance composer refuses evidence that did not prove what its receipt would claim."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "compose_route_acceptance", ROOT / "scripts" / "compose_route_acceptance.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

CANDIDATE = "1" * 40
MANIFEST = {
    "components": {
        "ninfer": {"oci_manifest_digest": "sha256:" + "a" * 64, "server_binary_sha256": "b" * 64},
        "model": {"artifact_sha256": "c" * 64},
    },
    "runtime_identity": {"configuration_sha256": "d" * 64},
}
LIVE = {
    "event_counts": {"tool_execution_start": 1, "tool_execution_end": 1},
    "typed_read_tool_calls": 1,
    "linked_tool_results": 1,
    "tool_result_marker": True,
    "exact_visible_final_answer": True,
    "agent_end": True,
    "continuation_exact_nonce": True,
    "runtime_identity_bound": True,
    "raw_transcript_included": False,
    "runtime_image_digest": "sha256:" + "a" * 64,
    "runtime_server_binary_sha256": "b" * 64,
    "runtime_configuration_sha256": "d" * 64,
    "model_sha256": "c" * 64,
    "fail_closed": {"exit_code": 1, "no_model_response": True,
                    "only_selected_local_provider_observed": True},
}


def route_receipt(lane: str) -> dict:
    steps = [
        {"slug": step.slug, "status": "passed", "block_sha256": "e" * 64, "executed_sha256": "e" * 64,
         "elapsed_seconds": 1.0}
        for step in MODULE.documented_route.LANES[lane]
    ]
    return {"artifact_type": "omp_ninfer_documented_route_run", "lane": lane, "status": "passed",
            "clone_commit": CANDIDATE, "document_sha256": "f" * 64, "steps": steps}


def refused(function, *arguments) -> str:
    with unittest.TestCase().assertRaises(SystemExit) as caught:
        function(*arguments)
    return str(caught.exception)


class RouteReceiptTests(unittest.TestCase):
    def test_a_fully_passed_route_from_the_candidate_is_accepted(self) -> None:
        MODULE.check_route("rtx4090-native", route_receipt("rtx4090-native"), CANDIDATE)

    def test_a_route_with_a_failed_or_skipped_step_is_refused(self) -> None:
        receipt = route_receipt("rtx5090-macos-client")
        receipt["steps"][-1]["status"] = "skipped"
        self.assertIn("fail-closed", refused(MODULE.check_route, "rtx5090-macos-client", receipt, CANDIDATE))

    def test_a_recorded_clone_substitution_counts_and_an_unrecorded_one_does_not(self) -> None:
        receipt = route_receipt("rtx5090-windows-client")
        receipt["steps"][0].update(status="substituted", substitution="cloned the candidate commit")
        MODULE.check_route("rtx5090-windows-client", receipt, CANDIDATE)
        receipt["steps"][0]["substitution"] = None
        self.assertIn("clone-and-verify", refused(MODULE.check_route, "rtx5090-windows-client", receipt, CANDIDATE))

    def test_a_block_executed_with_other_bytes_than_bundled_is_refused(self) -> None:
        receipt = route_receipt("rtx5090-container-host")
        receipt["steps"][0]["executed_sha256"] = "0" * 64
        self.assertIn("executed bytes", refused(MODULE.check_route, "rtx5090-container-host", receipt, CANDIDATE))

    def test_a_route_missing_a_documented_step_is_refused(self) -> None:
        receipt = route_receipt("rtx5090-windows-client")
        del receipt["steps"][0]
        self.assertIn("differ from", refused(MODULE.check_route, "rtx5090-windows-client", receipt, CANDIDATE))

    def test_a_route_run_from_another_commit_is_refused(self) -> None:
        receipt = route_receipt("rtx4090-native")
        receipt["clone_commit"] = "2" * 40
        self.assertIn("not candidate", refused(MODULE.check_route, "rtx4090-native", receipt, CANDIDATE))


class LiveEvidenceTests(unittest.TestCase):
    def test_complete_live_evidence_against_the_manifest_runtime_is_accepted(self) -> None:
        MODULE.check_live("darwin-remote-ssh", deepcopy(LIVE), MANIFEST)

    def test_a_run_against_another_runtime_image_is_refused(self) -> None:
        live = deepcopy(LIVE)
        live["runtime_image_digest"] = "sha256:" + "9" * 64
        self.assertIn("runtime_image_digest", refused(MODULE.check_live, "linux-docker-local", live, MANIFEST))

    def test_a_missing_continuation_nonce_is_refused(self) -> None:
        live = deepcopy(LIVE)
        live["continuation_exact_nonce"] = False
        self.assertIn("continuation_exact_nonce", refused(MODULE.check_live, "windows-docker-local", live, MANIFEST))

    def test_a_turn_without_exactly_one_tool_execution_is_refused(self) -> None:
        live = deepcopy(LIVE)
        live["event_counts"]["tool_execution_end"] = 0
        self.assertIn("one tool execution", refused(MODULE.check_live, "darwin-remote-ssh", live, MANIFEST))

    def test_a_fail_closed_request_that_succeeded_or_reached_a_model_is_refused(self) -> None:
        for field, value in (("exit_code", 0), ("no_model_response", False),
                             ("only_selected_local_provider_observed", False)):
            with self.subTest(field=field):
                live = deepcopy(LIVE)
                live["fail_closed"][field] = value
                self.assertIn("fail-closed", refused(MODULE.check_live, "darwin-remote-ssh", live, MANIFEST))


class PlatformReceiptTests(unittest.TestCase):
    PROFILE = {"id": "darwin-remote-ssh", "client_distribution": {
        "archive_sha256": "7" * 64, "binary_sha256": "8" * 64, "asset_url": "https://example.invalid/a"}}
    PREVIOUS = {"source": {"commit": "5" * 40}, "hosted_ci": {"run_id": 1},
                "client": {"archive_sha256": "7" * 64, "binary_sha256": "8" * 64,
                           "asset_url": "https://example.invalid/a"}}

    def evidence(self, binary: str) -> dict:
        return {"binary_sha256": binary, "live_acceptance": deepcopy(LIVE),
                "diagnostics": {"status": "blocked"}, "limitations": []}

    def test_an_unchanged_client_carries_its_identity_into_the_new_release(self) -> None:
        receipt = MODULE.platform_receipt("v9.9.9", "2026-01-01", self.PROFILE, self.PREVIOUS,
                                          self.evidence("8" * 64), MANIFEST)
        self.assertEqual(receipt["product_release"], "v9.9.9")
        self.assertEqual(receipt["client"], self.PREVIOUS["client"])
        self.assertFalse(receipt["safety"]["cloud_fallback_observed"])

    def test_an_installed_binary_other_than_the_published_client_is_refused(self) -> None:
        message = refused(MODULE.platform_receipt, "v9.9.9", "2026-01-01", self.PROFILE,
                          self.PREVIOUS, self.evidence("9" * 64), MANIFEST)
        self.assertIn("not the published client", message)

    def test_a_changed_client_cannot_carry_the_previous_release_identity(self) -> None:
        previous = deepcopy(self.PREVIOUS)
        previous["client"]["binary_sha256"] = "6" * 64
        message = refused(MODULE.platform_receipt, "v9.9.9", "2026-01-01", self.PROFILE,
                          previous, self.evidence("8" * 64), MANIFEST)
        self.assertIn("cannot carry", message)


if __name__ == "__main__":
    unittest.main()
