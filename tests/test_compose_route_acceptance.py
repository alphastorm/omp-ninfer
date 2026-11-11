"""The route acceptance composer refuses evidence that did not prove what its receipt would claim."""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "compose_route_acceptance", ROOT / "scripts" / "compose_route_acceptance.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
STAGE_SPEC = importlib.util.spec_from_file_location("stage_release", ROOT / "scripts" / "stage_release.py")
assert STAGE_SPEC and STAGE_SPEC.loader
STAGE = importlib.util.module_from_spec(STAGE_SPEC)
sys.modules[STAGE_SPEC.name] = STAGE
STAGE_SPEC.loader.exec_module(STAGE)
from verify_release import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    validate_client_profile_predicates, validate_ready_state_consistency,
    validate_documented_route_acceptance, validate_native_route_policy,
)

# v0.7.4's accepted posture: the macOS SSH profile stays preview, the Docker-local ones install.
ACCEPTED = {"darwin-remote-ssh": "preview", "windows-docker-local": "qualified",
            "linux-docker-local": "qualified"}

DESCRIPTOR = json.loads(
    (ROOT / "tests" / "fixtures" / "upstream-omp-component.json").read_text(encoding="utf-8")
)
CANDIDATE = "1" * 40
UPSTREAM = {"distribution_kind": "upstream-release",
            "upstream_repository": "https://github.com/can1357/oh-my-pi",
            "upstream_tag": DESCRIPTOR["omp"]["upstream_tag"],
            "upstream_commit": "5" * 40, "release_id": 42}


def client_distribution(platform: str, digest: str = "8" * 64) -> dict:
    asset = f"omp-{platform}" + (".exe" if platform == "windows-x64" else "")
    return {**UPSTREAM, "os": platform.split("-")[0], "architecture": platform.rsplit("-", 1)[1],
            "published": True, "asset_name": asset, "asset_bytes": 123, "asset_id": 43,
            "asset_url": f"{UPSTREAM['upstream_repository']}/releases/download/{UPSTREAM['upstream_tag']}/{asset}",
            "asset_sha256": digest, "binary_sha256": digest}


WINDOWS = client_distribution("windows-x64")
MANIFEST = {
    "components": {
        "omp": {**UPSTREAM, "upstream_tree": "6" * 40,
                "distribution_version": DESCRIPTOR["omp"]["distribution_version"],
                "platform": "windows-x64", "artifact_name": WINDOWS["asset_name"],
                "artifact_url": WINDOWS["asset_url"], "artifact_bytes": WINDOWS["asset_bytes"],
                "artifact_release_id": 42, "artifact_asset_id": 43, "artifact_published": True,
                "artifact_sha256": WINDOWS["asset_sha256"], "binary_sha256": WINDOWS["binary_sha256"],
                "compatibility_authority": "https://example.invalid/compatibility.json"},
        "ninfer": {"oci_manifest_digest": "sha256:" + "a" * 64, "server_binary_sha256": "b" * 64},
        "model": {"artifact_sha256": "c" * 64},
    },
    "runtime_identity": {"configuration_sha256": "d" * 64},
}
LIVE = {
    "omp_version": f"omp/{DESCRIPTOR['omp']['distribution_version']}",
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
# v0.14.0's restoration evidence: its receipt without the fields the composer writes itself.
RESTORATION = {key: value for key, value in json.loads(
    (ROOT / "docs/measurements/2026-10-28-v0140-acceptance-restoration.json").read_text(encoding="utf-8")
).items() if key not in ("artifact_type", "schema_version", "release", "as_of", "status",
                         "production_upgrade_activated",
                         "raw_private_paths_credentials_or_outputs_included")}
RESTORATION["candidate_commit"] = CANDIDATE
FIRST_RELEASE = {"rollback": {"status": "not_applicable", "directions": 0,
                              "reason": "first release of the lineage"}}
# The route-acceptance summary v0.14.0's staging left for composition to replace.
STAGED_ROUTE_ACCEPTANCE = {
    "status": "pending",
    "fresh_product_acceptance": False,
    "scope": "Fresh candidate-bound external-install acceptance of all five routes, three unchanged "
             "stock OMP 18.12.6 clients and both beta.3 native public installs is required. No "
             "predecessor product acceptance is carried.",
    "document_change": "Published QUICKSTART blocks remain on v0.13.1 at this stage.",
}


def native_evidence(gpu: str) -> dict:
    """v0.14.0's first-of-lineage public-install evidence for one native lane."""
    receipt = json.loads((ROOT / f"releases/v0.14.0/acceptance/{gpu}-public-install.json")
                         .read_text(encoding="utf-8"))
    return {key: receipt[key] for key in ("preparation", "observations", "limitations")}



def route_receipt(lane: str) -> dict:
    steps = [
        {"slug": step.slug, "status": "passed", "block_sha256": "e" * 64, "executed_sha256": "e" * 64,
         "elapsed_seconds": 1.0}
        for step in MODULE.documented_route.LANES[lane]
    ]
    return {"artifact_type": "omp_ninfer_documented_route_run", "lane": lane, "status": "passed",
            "clone_commit": CANDIDATE, "document_sha256": "f" * 64, "steps": steps}


def campaign_waiver(release: str, candidate: str, route_sha256: str,
                    *, failed_phase: str = "structured-outage") -> dict:
    waiver = {
        "artifact_type": "omp_ninfer_founder_gate_waiver", "schema_version": 1,
        "release": release, "candidate": candidate, "lane": "rtx3090-native",
        "status": "waived-by-founder", "observed_status": "failed",
        "documented_route_status": "passed", "failed_phase": "structured-outage",
        "observed_summary": {
            "action": "Control-Release.ps1 -Action Stop after structured live and native probes",
            "outcome": "graceful_incomplete_shutdown", "sessions_saved": 1, "sessions_skipped": 8,
            "sessions_refused": 1, "shutdown_complete": False,
            "final_durable_save_reason": "capacity", "reclaimed_host_bytes": 0},
        "restoration_summary": {
            "status": "restored-by-lead", "outcome": "graceful", "sessions_refused": 0,
            "runtime_record_absent": True, "gpu_owner_lease_absent": True, "power_limit_w": 370,
            "all_native_tasks_ready": True, "server_processes": 0, "port_18082_listeners": 0},
        "provenance": {"source_sha256": "7" * 64},
        "evidence_sha256": {"documented-route.json": route_sha256,
                            "window-failure.json": "8" * 64, "driver-window.json": "9" * 64,
                            "lead-restoration.out": "a" * 64, "pre-window-census.json": "b" * 64},
    }
    if failed_phase == "native-probes":
        waiver["failed_phase"] = failed_phase
        waiver["observed_summary"] = {
            "probe": "compaction", "error": "RuntimeError: timed out after 900 s",
            "timeout_seconds": 900, "http_status_counts": {"503": 8, "499": 2},
            "managed_stop": {**waiver["observed_summary"], "sessions_refused": 3},
        }
        waiver["evidence_sha256"]["compaction-probe.json"] = "c" * 64
        waiver["probe_projection_sha256"] = {"compaction": "d" * 64}
    return waiver


def waived_campaign_evidence(waiver: dict) -> dict:
    """Content-safe collector projections retain their original private source digests."""
    return {
        "window_failure": {"evidence_name": "rtx3090/evidence/window-failure.json",
                           "sha256": waiver["evidence_sha256"]["window-failure.json"],
                           "boundary": waiver["failed_phase"],
                           "observed_summary": deepcopy(waiver["observed_summary"])},
        "stopped_owner_census": {"evidence_name": "native-pre-window-census.json",
                                 "sha256": waiver["evidence_sha256"]["pre-window-census.json"],
                                 "lane": "rtx3090", "power_limit_w": 370},
    }


def refused(function, *arguments) -> str:
    with unittest.TestCase().assertRaises(SystemExit) as caught:
        function(*arguments)
    return str(caught.exception)


class FirstReleaseNativeTests(unittest.TestCase):
    def test_first_release_acceptance_cannot_claim_an_upgrade_or_passed_rollback(self) -> None:
        rollback = {"status": "not_applicable", "directions": 0, "reason": "first release of the lineage"}
        qualification = {"rollback": rollback}
        native = {"preparation": {"lineage_mode": "first_release", "previous_release_present": False},
                  "observations": {"rollback": rollback}}
        MODULE.check_native_first_release(native, qualification)
        for path, value in (("lineage_mode", "upgrade"), ("previous_release_present", True)):
            candidate = deepcopy(native)
            candidate["preparation"][path] = value
            self.assertIn("first-release", refused(MODULE.check_native_first_release, candidate, qualification))
        candidate = deepcopy(native)
        candidate["observations"]["rollback"]["status"] = "passed"
        self.assertIn("not_applicable", refused(MODULE.check_native_first_release, candidate, qualification))
        self.assertIn("first-release", refused(MODULE.check_native_first_release, native, {"rollback": {"status": "passed"}}))
        MODULE.check_native_first_release({"preparation": {}, "observations": {}}, {"rollback": {"status": "passed"}})


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

    def test_non_clone_substitution_cannot_qualify_an_unexecuted_block(self) -> None:
        for lane in MODULE.documented_route.LANES:
            receipt = route_receipt(lane)
            for index, step in enumerate(receipt["steps"]):
                if step["slug"] == "clone-and-verify":
                    continue
                with self.subTest(lane=lane, step=receipt["steps"][index]["slug"]):
                    edited = deepcopy(receipt)
                    edited["steps"][index].update(status="substituted", substitution="not executed")
                    self.assertIn(edited["steps"][index]["slug"],
                                  refused(MODULE.check_route, lane, edited, CANDIDATE))

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
    PROFILE = {"id": "darwin-remote-ssh", "client_distribution": client_distribution("darwin-arm64")}

    def evidence(self, binary: str) -> dict:
        return {"binary_sha256": binary, "live_acceptance": deepcopy(LIVE),
                "candidate": CANDIDATE, "release": "v9.9.9", "limitations": []}

    def test_stock_client_receipt_needs_no_previous_fork_receipt(self) -> None:
        receipt = MODULE.platform_receipt("v9.9.9", "2026-01-01", self.PROFILE,
                                          self.evidence("8" * 64), MANIFEST, CANDIDATE)
        self.assertEqual(receipt["product_release"], "v9.9.9")
        self.assertEqual(receipt["candidate_commit"], CANDIDATE)
        self.assertEqual(receipt["client"]["asset_sha256"], "8" * 64)
        self.assertEqual(receipt["source"]["repository"], UPSTREAM["upstream_repository"])
        self.assertNotIn("hosted_ci", receipt)
        self.assertNotIn("diagnostics", receipt)
        self.assertFalse(receipt["safety"]["cloud_fallback_observed"])

    def test_an_installed_binary_other_than_the_published_client_is_refused(self) -> None:
        message = refused(MODULE.platform_receipt, "v9.9.9", "2026-01-01", self.PROFILE,
                          self.evidence("9" * 64), MANIFEST, CANDIDATE)
        self.assertIn("not the published client", message)

    def test_wrong_preflight_version_cannot_be_claimed_as_passed(self) -> None:
        evidence = self.evidence("8" * 64)
        evidence["live_acceptance"]["omp_version"] = "omp/18.2.3"
        message = refused(MODULE.platform_receipt, "v9.9.9", "2026-01-01", self.PROFILE,
                          evidence, MANIFEST, CANDIDATE)
        self.assertIn("client version differs", message)

    def test_fork_client_cannot_be_accepted_as_stock(self) -> None:
        profile = deepcopy(self.PROFILE)
        del profile["client_distribution"]["distribution_kind"]
        self.assertIn("stock upstream client required", refused(
            MODULE.platform_receipt, "v9.9.9", "2026-01-01", profile, self.evidence("8" * 64),
            MANIFEST, CANDIDATE))

    def test_private_nonmarker_error_text_is_projected_without_mutating_the_capture(self) -> None:
        evidence = self.evidence("8" * 64)
        sentinel = "PRIVATE_ERROR_SENTINEL_493817"
        evidence["live_acceptance"]["fail_closed"]["errors"] = [sentinel]
        receipt = MODULE.platform_receipt("v9.9.9", "2026-01-01", self.PROFILE,
                                          evidence, MANIFEST, CANDIDATE)
        self.assertNotIn(sentinel, json.dumps(receipt))
        self.assertEqual(receipt["live_acceptance"]["fail_closed"]["errors"],
                         [{"kind": "client-error", "sha256": MODULE.sha256(sentinel.encode())}])
        self.assertEqual(evidence["live_acceptance"]["fail_closed"]["errors"], [sentinel])


class UpstreamCompositionTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.release = "v9.9.9"
        self.release_root = self.root / "releases" / self.release
        (self.root / "docs" / "measurements").mkdir(parents=True)
        self.document = self.root / "docs" / "QUICKSTART.md"
        self.document.write_bytes(MODULE.DOCUMENT.read_bytes() + b"\n" +
                                  (ROOT / "tests/fixtures/native-quickstart-5861712f.md").read_bytes())
        manifest = deepcopy(MANIFEST)
        manifest["components"]["ninfer_variants"] = [{
            "id": "rtx4090-windows-native", "release_tag": "native-runtime",
            "source_commit": "9" * 40, "package_bytes": 100, "package_sha256": "9" * 64,
            "server_binary_sha256": "a" * 64, "configuration_sha256": "b" * 64,
            "model_artifact_sha256": "c" * 64,
            "qualification": {"summary": "qualification/rtx4090.json"}}]
        MODULE.save(self.release_root / "qualification" / "rtx4090.json", FIRST_RELEASE)
        manifest.update(release=self.release, status="candidate",
                        publication={"blockers": ["acceptance"]}, qualification={})
        MODULE.save(self.release_root / "manifest.json", manifest)
        MODULE.save(self.root / "releases/v0.14.0/manifest.json", {
            "release": "v0.14.0", "status": "ready", "components": {"ninfer": {
                "oci_manifest_digest": RESTORATION["rtx5090"]["original_image"].split("@")[1]}}})
        MODULE.save(self.release_root / "qualification.json", {
            "as_of": "2026-01-01", "documented_route_acceptance": deepcopy(STAGED_ROUTE_ACCEPTANCE),
            "composition": {"external_installation_acceptance": {
                "public_url": "https://example.invalid/acceptance.json"}}})
        self.bind_subject()
        # The authority exactly as upstream staging leaves it: the predecessor's accepted profiles
        # reset to pending, without receipts or installability.
        authority = {"product_release": self.release, "composition": {"status": "v9.9.8", "blockers": []},
                     "profiles": [{
                         "id": profile, "status": ACCEPTED[profile], "installable": ACCEPTED[profile] == "qualified",
                         "blockers": [], "gpu_qualification": {"status": "qualified"},
                         "acceptance_receipt": {"url": f"https://example.invalid/{profile}.json", "sha256": "0" * 64}}
                         for profile in MODULE.OMP_PROFILE_PLATFORMS]}
        platforms = {platform: client_distribution(platform, digest * 64)
                     for platform, digest in zip(MODULE.OMP_PROFILE_PLATFORMS.values(), ("7", "8", "9"))}
        STAGE.bind_upstream_client(authority, {"omp": manifest["components"]["omp"], "platforms": platforms},
                                   self.release)
        self.profiles = authority["profiles"]
        MODULE.save(self.root / "compatibility.json", authority)
        MODULE.save(self.release_root / "compatibility.json", authority)
        evidence = {
            "platforms": {profile["id"]: {
                "status": ACCEPTED[profile["id"]],
                "candidate": CANDIDATE, "release": self.release,
                "binary_sha256": profile["client_distribution"]["binary_sha256"],
                "live_acceptance": deepcopy(LIVE), "limitations": []} for profile in self.profiles},
            "rtx4090": native_evidence("rtx4090"),
            "restoration": {key: deepcopy(RESTORATION[key])
                            for key in ("candidate_commit", "rtx5090", "rtx4090")},
            "documented_routes": {"mode": "offline-fixture", "qualification_environment": {},
                                  "scope": "Fresh candidate-bound routes, stock clients and the "
                                           "native public install passed; no predecessor product "
                                           "acceptance is carried."},
            "composed": {"mode": "offline-fixture", "authority_status": "qualified",
                "public_client_downloads": {"status": "passed", "anonymous": True},
                "linux_live_client": {"status": "passed"}, "client_note": "Stock binary",
                "vision_scope": ["darwin-remote-ssh", "windows-docker-local"],
                "runtime_qualification": {}, "limitations": [], "qualification_note": "Observed"}}
        MODULE.save(self.root / "evidence.json", evidence)
        self.argv = ["compose_route_acceptance.py", "--release", self.release, "--candidate", CANDIDATE,
                     "--as-of", "2026-01-02", "--measurement-prefix", "fixture",
                     "--evidence", str(self.root / "evidence.json")]
        for lane in (*MODULE.LANES, "rtx4090-native"):
            receipt = route_receipt(lane)
            receipt["document_sha256"] = MODULE.sha256(self.document.read_bytes())
            for step, (_, block) in zip(receipt["steps"], MODULE.documented_route.lane_blocks(self.document, lane)):
                step["block_sha256"] = step["executed_sha256"] = block.sha256
            path = self.root / f"{lane}.json"
            MODULE.save(path, receipt)
            self.argv += ["--route", f"{lane}={path}"]
        self.bind_native_policies()

    def bind_native_policies(self):
        """Future-release fixtures carry real-shaped authenticated native policy and probe edges."""
        if MODULE.product_version(self.release) < (0, 16, 0):
            return
        from test_native_candidate_policy import candidate_profile, probe_receipts
        from compose_native_qualification import native_probe_summary
        manifest = MODULE.load(self.release_root / "manifest.json")
        evidence = MODULE.load(self.root / "evidence.json")
        for variant in manifest["components"]["ninfer_variants"]:
            lane = variant["id"].split("-")[0]
            spec, config, configuration = candidate_profile(lane)
            variant.update(maximum_context_tokens=configuration["max_context"], runtime_shape=spec["runtime_shape"])
            for field, filename, value in (("release_spec", "release-spec.json", spec),
                                           ("server_config", "server-config.json", config)):
                path = self.release_root / "profiles" / lane / filename
                MODULE.save(path, value)
                variant["qualification"][field] = {
                    "path": path.relative_to(self.root).as_posix(), "sha256": MODULE.sha256(path.read_bytes())}
            variant["configuration_sha256"] = variant["qualification"]["server_config"]["sha256"]
            if lane in evidence:
                client = {"version": f"omp/{manifest['components']['omp']['distribution_version']}",
                          "binary_sha256": manifest["components"]["omp"]["binary_sha256"]}
                evidence[lane].update(candidate_commit=CANDIDATE, release=self.release,
                                      client=deepcopy(client))
                if "structured_client" in evidence[lane].get("observations", {}):
                    evidence[lane]["observations"]["structured_client"]["omp_version"] = client["version"]
                installed = {"source_commit": variant["source_commit"],
                             "package_sha256": variant["package_sha256"],
                             "binary_sha256": variant["server_binary_sha256"],
                             "config_sha256": variant["configuration_sha256"]}
                evidence[lane]["installed"] = deepcopy(installed)
                route_path = self.root / f"{lane}-native.json"
                if route_path.is_file():
                    receipt = MODULE.load(route_path)
                    receipt.update(candidate_commit=CANDIDATE, release=self.release,
                                   client=deepcopy(client), installed=deepcopy(installed))
                    MODULE.save(route_path, receipt)
                probes = probe_receipts(variant, configuration)
                for name in ("parallel", "compaction"):
                    if name in probes:
                        probes[name]["omp"]["sha256"] = manifest["components"]["omp"]["binary_sha256"]
                if evidence[lane].get("failed_phase") == "native-probes":
                    probes["compaction"].update(passed=False, checks={}, compactions=[])
                evidence[lane].update(runtime_configuration=configuration,
                                      probe_acceptance=native_probe_summary(probes))
                install = evidence[lane].get("observations", {}).get("public_install")
                if install is not None:
                    install["source"] = {"product_release": self.release,
                                         "candidate_commit": CANDIDATE}
                    install["client"] = deepcopy(client)
                    install["installed"].update(installed)
                    install["integrity"]["assets"]["package"].update(
                        sha256=variant["package_sha256"], bytes=variant["package_bytes"])
                    install["installed"].update(
                        server_binary_sha256=variant["server_binary_sha256"],
                        configuration_sha256=variant["configuration_sha256"])
                    if "package_sha256" in install["install"]:
                        install["install"]["package_sha256"] = variant["package_sha256"]
        MODULE.save(self.release_root / "manifest.json", manifest)
        MODULE.save(self.root / "evidence.json", evidence)

    def bind_subject(self):
        path = self.release_root / "review/runtime-ledger.json"
        MODULE.save(path, {"artifact_type": "omp_ninfer_review_ledger", "release": self.release,
                           "product_tooling": {"stage_commit": CANDIDATE}})
        qualification = MODULE.load(self.release_root / "qualification.json")
        qualification["release"] = self.release
        qualification["observed_gates"] = {"g4_review": {
            "repository_path": path.relative_to(self.root).as_posix(),
            "sha256": MODULE.sha256(path.read_bytes())}}
        MODULE.save(self.release_root / "qualification.json", qualification)

    def compose(self) -> int:
        with patch.object(MODULE, "ROOT", self.root), patch.object(MODULE, "DOCUMENT", self.document), \
                patch.object(sys, "argv", self.argv), redirect_stdout(io.StringIO()):
            return MODULE.main()

    def omit_4090(self) -> None:
        manifest = MODULE.load(self.release_root / "manifest.json")
        manifest["components"]["ninfer_variants"] = []
        MODULE.save(self.release_root / "manifest.json", manifest)
        evidence = MODULE.load(self.root / "evidence.json")
        del evidence["rtx4090"], evidence["restoration"]["rtx4090"]
        MODULE.save(self.root / "evidence.json", evidence)
        del self.argv[-2:]

    def test_5090_only_composes_three_routes_without_native_evidence(self) -> None:
        self.omit_4090()
        self.assertEqual(self.compose(), 0)
        acceptance = self.release_root / "acceptance"
        routes = MODULE.load(acceptance / "documented-routes.json")
        self.assertEqual(set(routes["routes"]), {
            "rtx5090-container-host", "rtx5090-macos-client", "rtx5090-windows-client"})
        external = MODULE.load(acceptance / "composed-external-installation.json")
        self.assertEqual(len(external["platform_receipts"]), 3)
        self.assertNotIn("rtx4090_public_install", external["evidence"])
        self.assertFalse((acceptance / "rtx4090-public-install.json").exists())
        self.assertEqual(MODULE.load(self.release_root / "manifest.json")["status"], "ready")

    def test_declared_4090_without_its_route_is_refused(self) -> None:
        del self.argv[-2:]
        with self.assertRaisesRegex(SystemExit, "need one --route"):
            self.compose()
        self.assertFalse((self.release_root / "acceptance").exists())

    def test_undeclared_4090_route_is_refused(self) -> None:
        self.omit_4090()
        self.argv += ["--route", f"rtx4090-native={self.root / 'unused.json'}"]
        with self.assertRaisesRegex(SystemExit, "need one --route"):
            self.compose()
        self.assertFalse((self.release_root / "acceptance").exists())

    def test_undeclared_native_evidence_is_refused(self) -> None:
        self.omit_4090()
        for gpu in ("rtx3090", "rtx4090"):
            with self.subTest(gpu=gpu):
                evidence = MODULE.load(self.root / "evidence.json")
                evidence[gpu] = native_evidence(gpu)
                MODULE.save(self.root / "evidence.json", evidence)
                with self.assertRaisesRegex(SystemExit, "undeclared native evidence"):
                    self.compose()
                self.assertFalse((self.release_root / "acceptance").exists())
                del evidence[gpu]
                MODULE.save(self.root / "evidence.json", evidence)

    def test_split_model_keeps_live_clients_primary_and_native_receipts_native(self) -> None:
        manifest = MODULE.load(self.release_root / "manifest.json")
        manifest["components"]["native_model"] = {"artifact_sha256": "e" * 64}
        manifest["components"]["ninfer_variants"][0]["model_artifact_sha256"] = "e" * 64
        MODULE.save(self.release_root / "manifest.json", manifest)
        self.bind_native_policies()
        self.assertEqual(self.compose(), 0)
        native = MODULE.load(self.release_root / "acceptance/rtx4090-public-install.json")
        self.assertEqual(native["runtime"]["model_sha256"], "e" * 64)
        for path in (self.release_root / "acceptance").glob("*-" + DESCRIPTOR["omp"]["distribution_version"] + ".json"):
            self.assertEqual(MODULE.load(path)["live_acceptance"]["model_sha256"], "c" * 64)

    def test_native_receipt_cannot_accept_the_primary_model_in_a_split_release(self) -> None:
        manifest = MODULE.load(self.release_root / "manifest.json")
        manifest["components"]["native_model"] = {"artifact_sha256": "e" * 64}
        MODULE.save(self.release_root / "manifest.json", manifest)
        with self.assertRaisesRegex(SystemExit, "native model"):
            self.compose()
        self.assertFalse((self.release_root / "acceptance").exists())

    def test_full_stock_composition_binds_current_assets_and_final_authority(self) -> None:
        self.assertEqual(self.compose(), 0)
        acceptance = self.release_root / "acceptance"
        external = MODULE.load(acceptance / "composed-external-installation.json")
        qualification = MODULE.load(self.release_root / "qualification.json")
        manifest = MODULE.load(self.release_root / "manifest.json")
        omp = manifest["components"]["omp"]
        summary = qualification["composition"]["external_installation_acceptance"]
        digest = MODULE.sha256((self.root / "compatibility.json").read_bytes())
        self.assertEqual((self.root / "compatibility.json").read_bytes(),
                         (self.release_root / "compatibility.json").read_bytes())
        self.assertEqual(summary["component_release_tag"], DESCRIPTOR["omp"]["upstream_tag"])
        self.assertEqual(external["client"]["component_release_tag"], DESCRIPTOR["omp"]["upstream_tag"])
        for receipt in (summary, external):
            self.assertEqual(receipt["windows_asset_sha256"], omp["artifact_sha256"])
            self.assertEqual(receipt["windows_binary_sha256"], omp["binary_sha256"])
            self.assertEqual(receipt["compatibility_authority"], omp["compatibility_authority"])
            self.assertEqual(receipt["compatibility_sha256"], digest)
        self.assertEqual(omp["compatibility_sha256"], digest)
        self.assertEqual(summary["sha256"], MODULE.sha256((acceptance / "composed-external-installation.json").read_bytes()))
        downloads = external["steps"]["public_client_downloads"]
        self.assertEqual(downloads["assets"], 3)
        self.assertEqual({row["profile"]: (row["url"], row["sha256"]) for row in downloads["downloads"]},
                         {p["id"]: (p["client_distribution"]["asset_url"], p["client_distribution"]["asset_sha256"]) for p in self.profiles})
        components = MODULE.load(self.release_root / "qualification" / "client-components.json")
        self.assertEqual(components["omp"]["distribution_kind"], "upstream-release")
        self.assertEqual(set(components["platforms"]), {"darwin-arm64", "windows-x64", "linux-x64"})
        self.assertEqual(components["platforms"]["windows-x64"]["asset_sha256"], omp["artifact_sha256"])
        self.assertEqual(MODULE.load(acceptance / "rtx4090-public-install.json")["client"]["asset_url"], omp["artifact_url"])
        authority = MODULE.load(self.root / "compatibility.json")
        rows = {row["profile"]: row["sha256"] for row in external["platform_receipts"]}
        for profile in authority["profiles"]:
            filename = (f"{MODULE.OMP_PROFILE_PLATFORMS[profile['id']]}-"
                        f"{DESCRIPTOR['omp']['distribution_version']}.json")
            path = acceptance / filename
            self.assertEqual((profile["status"], profile["installable"], profile["blockers"]),
                             (ACCEPTED[profile["id"]], ACCEPTED[profile["id"]] == "qualified", []))
            self.assertEqual(profile["acceptance_receipt"], {
                "url": f"https://raw.githubusercontent.com/alphastorm/omp-ninfer/{CANDIDATE}"
                       f"/releases/{self.release}/acceptance/{filename}",
                "sha256": MODULE.sha256(path.read_bytes())})
            self.assertEqual(rows[profile["id"]], profile["acceptance_receipt"]["sha256"])
            self.assertNotIn("diagnostics", MODULE.load(path))
        errors = []
        MODULE.validate_upstream_omp_component(omp, errors)
        MODULE.validate_upstream_client_bindings(omp, authority["profiles"], errors)
        validate_client_profile_predicates(authority, errors)
        self.assertEqual(errors, [])
        self.assertEqual(manifest["status"], "ready")

    def test_qualified_status_without_a_qualified_gpu_runtime_is_refused_before_writing(self) -> None:
        authority = MODULE.load(self.root / "compatibility.json")
        windows = next(p for p in authority["profiles"] if p["id"] == "windows-docker-local")
        windows["gpu_qualification"]["status"] = "in qualification"
        MODULE.save(self.root / "compatibility.json", authority)
        with self.assertRaisesRegex(SystemExit, "qualified without a qualified GPU runtime"):
            self.compose()
        self.assertFalse((self.release_root / "acceptance").exists())
        self.assertEqual(list((self.root / "docs" / "measurements").iterdir()), [])

    def refused_before_writing(self, select, cases) -> None:
        """Each change to the evidence section select picks is refused, and nothing is written."""
        original = (self.root / "evidence.json").read_text(encoding="utf-8")
        for case, change, message in cases:
            with self.subTest(case=case):
                evidence = json.loads(original)
                change(select(evidence))
                MODULE.save(self.root / "evidence.json", evidence)
                with self.assertRaisesRegex(SystemExit, message):
                    self.compose()
                self.assertFalse((self.release_root / "acceptance").exists())
                self.assertEqual(list((self.root / "docs" / "measurements").iterdir()), [])

    def test_restoration_must_observe_every_displaced_incumbent_before_writing(self) -> None:
        """Empty restoration evidence once composed a passed receipt and incumbent-restored claims."""
        self.refused_before_writing(lambda evidence: evidence["restoration"], (
            ("empty", lambda restoration: restoration.clear(), "restoration evidence is empty"),
            ("no incumbent", lambda restoration: restoration.pop("rtx5090"),
             "needs the rtx5090 incumbent"),
            ("other image", lambda restoration: restoration["rtx5090"].update(original_image_retained=False),
             "did not observe original_image_retained"),
            ("unpinned image", lambda restoration: restoration["rtx5090"].update(
                original_image="ghcr.io/alphastorm/ninfer-runtime:latest"), "digest-pinned image"),
            ("restart policy", lambda restoration: restoration["rtx5090"].update(restart_policy="no"),
             "not unless-stopped"),
            ("unhealthy", lambda restoration: restoration["rtx5090"].update(wsl_health_ok=False),
             "did not observe wsl_health_ok"),
            ("no window", lambda restoration: restoration["rtx5090"].update(window_hold_seconds=[]),
             "hold seconds"),
            ("native lane", lambda restoration: restoration.pop("rtx4090"), "rtx4090 restoration did not pass"),
            ("native audit", lambda restoration: restoration["rtx4090"]["final_audit_checks"].update(
                task_ready=False), "rtx4090 restoration final_audit_checks did not all pass"),
            ("native stage", lambda restoration: restoration["rtx4090"].update(documented_stage_restored=False),
             "did not observe documented_stage_restored"),
            ("undeclared lane", lambda restoration: restoration.update(rtx3090=deepcopy(RESTORATION["rtx3090"])),
             "undeclared native lane rtx3090"),
            ("other candidate", lambda restoration: restoration.update(candidate_commit="2" * 40),
             "not candidate"),
            ("relabelled upgrade", lambda restoration: restoration.update(production_upgrade_activated=True),
             "cannot set the receipt's own fields"),
        ))

    def test_restored_image_must_equal_the_published_predecessor_digest(self) -> None:
        self.refused_before_writing(lambda evidence: evidence["restoration"]["rtx5090"], (
            ("wrong digest", lambda incumbent: incumbent.update(
                original_image="ghcr.io/alphastorm/ninfer-runtime@sha256:" + "0" * 64),
             "restored image must match the published predecessor digest"),
            ("candidate not predecessor", lambda incumbent: incumbent.update(
                original_image="ghcr.io/alphastorm/ninfer-runtime@" +
                MANIFEST["components"]["ninfer"]["oci_manifest_digest"]),
             "restored image must match the published predecessor digest"),
        ))

    def test_restoration_requires_a_published_predecessor_not_a_draft(self) -> None:
        path = self.root / "releases/v0.14.0/manifest.json"
        predecessor = MODULE.load(path)
        predecessor["status"] = "draft"
        MODULE.save(path, predecessor)
        with self.assertRaisesRegex(SystemExit, "published predecessor"):
            self.compose()
        self.assertFalse((self.release_root / "acceptance").exists())
        self.assertEqual(list((self.root / "docs/measurements").iterdir()), [])

    def test_caller_and_all_receipts_cannot_override_the_frozen_product_subject(self):
        other = "2" * 40
        self.argv[self.argv.index("--candidate") + 1] = other
        for path in self.root.glob("*-*.json"):
            receipt = MODULE.load(path)
            if "clone_commit" in receipt:
                receipt["clone_commit"] = other
                MODULE.save(path, receipt)
        evidence = MODULE.load(self.root / "evidence.json")
        evidence["restoration"]["candidate_commit"] = other
        for platform in evidence["platforms"].values():
            platform["candidate"] = other
        MODULE.save(self.root / "evidence.json", evidence)
        with self.assertRaisesRegex(SystemExit, "does not match the frozen product subject"):
            self.compose()
        self.assertFalse((self.release_root / "acceptance").exists())
        self.assertEqual(list((self.root / "docs/measurements").iterdir()), [])

    def test_composition_requires_a_hash_bound_current_release_product_subject(self):
        qualification = MODULE.load(self.release_root / "qualification.json")
        qualification["observed_gates"]["g4_review"]["sha256"] = "0" * 64
        MODULE.save(self.release_root / "qualification.json", qualification)
        with self.assertRaisesRegex(SystemExit, "hash-bound frozen product subject"):
            self.compose()
        self.assertFalse((self.release_root / "acceptance").exists())

    def test_ready_routes_reconcile_the_rehashed_review_candidate(self):
        self.assertEqual(self.compose(), 0)
        path = self.release_root / "review/runtime-ledger.json"
        ledger = MODULE.load(path)
        ledger["product_tooling"]["stage_commit"] = "2" * 40
        MODULE.save(path, ledger)
        qualification = MODULE.load(self.release_root / "qualification.json")
        qualification["observed_gates"]["g4_review"]["sha256"] = MODULE.sha256(path.read_bytes())
        errors = []
        validate_documented_route_acceptance(self.root, qualification, errors)
        self.assertTrue(any("frozen product subject" in error for error in errors), errors)

    def test_ready_routes_rederive_current_document_and_block_addresses(self):
        self.assertEqual(self.compose(), 0)
        path = self.release_root / "acceptance/documented-routes.json"
        original = MODULE.load(path)
        qualification = MODULE.load(self.release_root / "qualification.json")
        for case in ("document", "address", "clone", "block"):
            with self.subTest(case=case):
                routes = deepcopy(original)
                if case == "document":
                    routes["current_document_sha256"] = "0" * 64
                elif case == "address":
                    routes["current_block_addresses"]["rtx4090-native"][0]["index"] += 1
                else:
                    receipt_path = self.root / routes["routes"]["rtx4090-native"]["receipt"]
                    receipt = MODULE.load(receipt_path)
                    if case == "clone":
                        receipt["clone_commit"] = "2" * 40
                    else:
                        receipt["steps"][0]["executed_sha256"] = "0" * 64
                    MODULE.save(receipt_path, receipt)
                    routes["routes"]["rtx4090-native"]["sha256"] = MODULE.sha256(receipt_path.read_bytes())
                MODULE.save(path, routes)
                digest = MODULE.sha256(path.read_bytes())
                qualification["composition"]["documented_route_acceptance"]["sha256"] = digest
                qualification["documented_route_acceptance"]["evidence_sha256"] = digest
                errors = []
                validate_documented_route_acceptance(self.root, qualification, errors)
                self.assertTrue(errors, case)

    def test_ready_routes_reject_a_guide_edit_after_composition(self):
        self.assertEqual(self.compose(), 0)
        self.document.write_bytes(self.document.read_bytes() + b"\nPost-composition prose.\n")
        errors = []
        validate_documented_route_acceptance(
            self.root, MODULE.load(self.release_root / "qualification.json"), errors)
        self.assertTrue(any("current_document_sha256" in error for error in errors), errors)

    def test_native_campaign_and_nested_install_bind_observed_candidate_release_and_client(self):
        self.refused_before_writing(lambda evidence: evidence["rtx4090"], (
            ("campaign candidate", lambda native: native.update(candidate_commit="2" * 40),
             "candidate_commit"),
            ("campaign release", lambda native: native.update(release="v0.17.0"), "release"),
            ("campaign client", lambda native: native["client"].update(binary_sha256="0" * 64),
             "client.binary_sha256"),
            ("campaign version", lambda native: native["client"].update(version="omp/18.2.3"),
             "client.version"),
            ("structured predecessor client", lambda native: native["observations"]["structured_client"].update(
                omp_version="omp/18.2.3"), "structured_client.omp_version"),
            ("campaign installed package", lambda native: native["installed"].update(
                package_sha256="0" * 64), "installed.package_sha256"),
            ("campaign installed source", lambda native: native["installed"].update(
                source_commit="0" * 40), "installed.source_commit"),
            ("install candidate", lambda native: native["observations"]["public_install"]["source"].update(
                candidate_commit="2" * 40), "candidate_commit"),
            ("install release", lambda native: native["observations"]["public_install"]["source"].update(
                product_release="v0.17.0"), "product_release"),
            ("install client", lambda native: native["observations"]["public_install"]["client"].update(
                binary_sha256="0" * 64), "client.binary_sha256"),
            ("install version", lambda native: native["observations"]["public_install"]["client"].update(
                version="omp/18.2.3"), "client.version"),
            ("install package record", lambda native: native["observations"]["public_install"]["installed"].update(
                package_sha256="0" * 64), "installed.package_sha256"),
            ("install binary record", lambda native: native["observations"]["public_install"]["installed"].update(
                binary_sha256="0" * 64), "installed.binary_sha256"),
            ("missing candidate", lambda native: native.pop("candidate_commit"), "candidate_commit"),
        ))

    def test_every_composed_native_receipt_keeps_the_observed_client_and_candidate(self):
        self.assertEqual(self.compose(), 0)
        native = MODULE.load(self.root / "evidence.json")["rtx4090"]
        routes = MODULE.load(self.release_root / "acceptance/documented-routes.json")
        install = MODULE.load(self.release_root / "acceptance/rtx4090-public-install.json")
        for row in (routes["routes"]["rtx4090-native"], routes["native_campaigns"]["rtx4090-native"],
                    install):
            self.assertEqual(row["candidate_commit"], CANDIDATE)
            self.assertEqual(row["client"]["version"], native["client"]["version"])
            self.assertEqual(row["client"]["binary_sha256"], native["client"]["binary_sha256"])

    def test_ready_verifier_refuses_rehashed_native_candidate_and_client_relabels(self):
        self.assertEqual(self.compose(), 0)
        path = self.release_root / "acceptance/rtx4090-public-install.json"
        original = MODULE.load(path)
        external_path = self.release_root / "acceptance/composed-external-installation.json"
        original_external = MODULE.load(external_path)
        for section, field, value in (
            ("outer", "candidate_commit", "2" * 40), ("client", "binary_sha256", "0" * 64),
            ("nested_source", "candidate_commit", "2" * 40),
            ("nested_source", "product_release", "v0.17.0"),
            ("nested_client", "version", "omp/18.2.3"),
            ("structured_client", "omp_version", "omp/18.2.3"),
        ):
            with self.subTest(section=section, field=field):
                receipt, external = deepcopy(original), deepcopy(original_external)
                target = {"outer": receipt, "client": receipt["client"],
                          "nested_source": receipt["observations"]["public_install"]["source"],
                          "nested_client": receipt["observations"]["public_install"]["client"],
                          "structured_client": receipt["observations"]["structured_client"]}[section]
                target[field] = value
                MODULE.save(path, receipt)
                external["evidence"]["rtx4090_public_install"]["sha256"] = MODULE.sha256(path.read_bytes())
                MODULE.save(external_path, external)
                qualification = MODULE.load(self.release_root / "qualification.json")
                qualification["composition"]["external_installation_acceptance"]["sha256"] = MODULE.sha256(
                    external_path.read_bytes())
                errors = []
                validate_native_route_policy(
                    self.root, self.release, MODULE.load(self.release_root / "manifest.json"),
                    qualification, errors)
                self.assertTrue(any(field in error for error in errors), errors)

    def test_every_late_refusal_preserves_the_entire_tree(self):
        for case in ("downloads", "last route", "documents", "blocks", "document change"):
            with self.subTest(case=case):
                fixture = UpstreamCompositionTests()
                fixture.setUp()
                try:
                    if case in ("downloads", "document change"):
                        evidence = MODULE.load(fixture.root / "evidence.json")
                        if case == "downloads":
                            evidence["composed"]["public_client_downloads"]["anonymous"] = False
                        else:
                            for lane in (*MODULE.LANES, "rtx4090-native"):
                                path = fixture.root / f"{lane}.json"
                                receipt = MODULE.load(path)
                                receipt["document_sha256"] = "0" * 64
                                MODULE.save(path, receipt)
                        MODULE.save(fixture.root / "evidence.json", evidence)
                    else:
                        path = fixture.root / "rtx4090-native.json"
                        receipt = MODULE.load(path)
                        if case == "last route":
                            receipt["status"] = "failed"
                        elif case == "documents":
                            receipt["document_sha256"] = "0" * 64
                        else:
                            receipt["steps"][0]["block_sha256"] = "0" * 64
                            receipt["steps"][0]["executed_sha256"] = "0" * 64
                        MODULE.save(path, receipt)
                    def snapshot():
                        return {path.relative_to(fixture.root).as_posix():
                                path.read_bytes() if path.is_file() else None
                                for path in fixture.root.rglob("*")}
                    before = snapshot()
                    with self.assertRaises(SystemExit):
                        fixture.compose()
                    self.assertEqual(snapshot(), before)
                finally:
                    fixture.doCleanups()

    def test_public_projection_excludes_nested_errors_paths_and_unknown_keys(self):
        evidence = MODULE.load(self.root / "evidence.json")
        sentinel = "sk-live-CREDENTIAL_SENTINEL_493817"
        for row in (
            evidence["platforms"]["darwin-remote-ssh"]["live_acceptance"],
            evidence["rtx4090"]["preparation"], evidence["rtx4090"]["observations"],
            evidence["rtx4090"]["observations"]["public_install"]["installed"],
            evidence["restoration"]["rtx5090"], evidence["restoration"]["rtx4090"],
            evidence["composed"]["linux_live_client"],
            evidence["rtx4090"]["probe_acceptance"]["fleet"],
            evidence["rtx4090"]["probe_acceptance"]["fleet"]["identity"],
        ):
            row.update(error=sentinel, path=sentinel, unexpected={sentinel: sentinel})
        evidence["rtx4090"]["preparation"]["documented_install"] = sentinel
        evidence["rtx4090"]["observations"]["structured_client"]["fail_closed"].update(
            endpoint=sentinel, method=sentinel)
        for key in ("restoration_checks", "final_audit_checks"):
            evidence["restoration"]["rtx4090"][key][sentinel] = True
        MODULE.save(self.root / "evidence.json", evidence)
        self.assertEqual(self.compose(), 0)
        published = [*self.release_root.rglob("*.json"), *(
            self.root / "docs/measurements").glob("*.json")]
        self.assertTrue(published)
        for path in published:
            self.assertNotIn(sentinel, path.read_text(encoding="utf-8"), path)
        self.assertEqual(MODULE.load(self.root / "evidence.json"), evidence)

    def test_public_window_failure_projects_error_to_digest(self):
        path = self.waive_3090(failed_phase="native-probes")
        sentinel = "sk-live-CREDENTIAL_SENTINEL_205361"
        waiver = MODULE.load(path)
        waiver["observed_summary"]["error"] = sentinel
        MODULE.save(path, waiver)
        evidence = MODULE.load(self.root / "evidence.json")
        binding = {"repository_path": path.relative_to(self.root).as_posix(),
                   "sha256": MODULE.sha256(path.read_bytes())}
        native = evidence["rtx3090"]
        native["founder_waiver"] = binding
        native["window_failure"]["observed_summary"]["error"] = sentinel
        native["window_failure"]["path"] = sentinel
        evidence["restoration"]["rtx3090"]["founder_waiver"] = binding
        MODULE.save(self.root / "evidence.json", evidence)
        self.assertEqual(self.compose(), 0)
        for name in ("documented-routes.json", "composed-external-installation.json"):
            self.assertNotIn(sentinel, (self.release_root / "acceptance" / name).read_text())
        routes = MODULE.load(self.release_root / "acceptance/documented-routes.json")
        observed = routes["native_campaigns"]["rtx3090-native"]["window_failure"]["observed_summary"]
        self.assertEqual(observed["error"], {"kind": "probe-error",
                                           "sha256": MODULE.sha256(sentinel.encode())})
        errors = []
        validate_documented_route_acceptance(
            self.root, MODULE.load(self.release_root / "qualification.json"), errors)
        self.assertEqual(errors, [])

    def test_composition_rebinds_references_to_the_evidence_it_rewrites(self):
        descriptor = self.release_root / "qualification/client-components.json"
        MODULE.save(descriptor, {"old": "staged descriptor"})
        qualification = MODULE.load(self.release_root / "qualification.json")
        qualification["observed_gates"]["stock_client_review"] = {"descriptor": {
            "repository_path": descriptor.relative_to(self.root).as_posix(),
            "sha256": MODULE.sha256(descriptor.read_bytes())}}
        qualification["observed_gates"]["changed_client_acceptance"] = {
            "repository_path": f"releases/{self.release}/acceptance/composed-external-installation.json"}
        independent = self.root / "independent.json"
        MODULE.save(independent, {"retained": True})
        binding = {"repository_path": "independent.json", "sha256": MODULE.sha256(independent.read_bytes())}
        qualification["independent"] = binding
        MODULE.save(self.release_root / "qualification.json", qualification)
        self.assertEqual(self.compose(), 0)
        qualification = MODULE.load(self.release_root / "qualification.json")
        for reference in (
            qualification["observed_gates"]["stock_client_review"]["descriptor"],
            qualification["observed_gates"]["changed_client_acceptance"],
        ):
            self.assertEqual(reference["sha256"],
                             MODULE.sha256((self.root / reference["repository_path"]).read_bytes()))
        self.assertEqual(qualification["independent"], binding)

    def test_platform_capture_must_bind_the_frozen_candidate_and_release_before_writing(self):
        self.refused_before_writing(lambda evidence: evidence["platforms"]["darwin-remote-ssh"], (
            ("other candidate", lambda platform: platform.update(candidate="2" * 40),
             "live capture candidate must match the frozen product subject"),
            ("missing candidate", lambda platform: platform.pop("candidate"),
             "live capture candidate must match the frozen product subject"),
            ("other release", lambda platform: platform.update(release="v0.14.0"),
             "live capture release must match"),
        ))

    def test_native_receipt_needs_its_own_live_observations_before_writing(self) -> None:
        """Empty native observations once composed a passed public-install receipt."""
        self.refused_before_writing(lambda evidence: evidence["rtx4090"]["observations"], (
            ("empty", lambda observations: observations.clear(), "did not observe exact_tool_marker"),
            ("no tool call", lambda observations: observations.update(server_tool_calls=0),
             "no server tool call"),
            ("no continuation", lambda observations: observations.update(exact_continuation_nonce=False),
             "did not observe exact_continuation_nonce"),
            ("not fail-closed", lambda observations: observations.update(
                offline_request_failed_without_model_response=False),
             "did not observe offline_request_failed_without_model_response"),
            ("cloud fallback", lambda observations: observations.update(cloud_fallback_observed=True),
             "rule out cloud fallback"),
            ("install failed", lambda observations: observations["public_install"].update(status="failed"),
             "public install did not pass"),
        ))

    def test_predecessor_public_install_is_refused_before_composition(self) -> None:
        self.refused_before_writing(
            lambda evidence: evidence["rtx4090"]["observations"]["public_install"], (
                ("package", lambda install: install["integrity"]["assets"]["package"].update(
                    sha256="0" * 64), "package.sha256 must match candidate"),
                ("server", lambda install: install["installed"].update(
                    server_binary_sha256="0" * 64), "server_binary_sha256 must match candidate"),
                ("configuration", lambda install: install["installed"].update(
                    configuration_sha256="0" * 64), "configuration_sha256 must match candidate"),
            ))

    def test_ready_verifier_refuses_rehashed_predecessor_nested_public_install(self) -> None:
        self.assertEqual(self.compose(), 0)
        path = self.release_root / "acceptance/rtx4090-public-install.json"
        qualification_path = self.release_root / "qualification.json"
        qualification = MODULE.load(qualification_path)
        external_path = self.release_root / "acceptance/composed-external-installation.json"
        external = MODULE.load(external_path)
        receipt = MODULE.load(path)
        receipt["observations"]["public_install"]["installed"]["configuration_sha256"] = "0" * 64
        MODULE.save(path, receipt)
        external["evidence"]["rtx4090_public_install"]["sha256"] = MODULE.sha256(path.read_bytes())
        MODULE.save(external_path, external)
        qualification["composition"]["external_installation_acceptance"]["sha256"] = MODULE.sha256(
            external_path.read_bytes())
        errors = []
        validate_native_route_policy(self.root, self.release,
                                     MODULE.load(self.release_root / "manifest.json"), qualification, errors)
        self.assertTrue(any("configuration_sha256 must match candidate" in error for error in errors), errors)

    def test_native_error_projection_keeps_private_capture_separate(self) -> None:
        path = self.root / "evidence.json"
        evidence = MODULE.load(path)
        sentinel = "PRIVATE_NATIVE_ERROR_SENTINEL_205361"
        evidence["rtx4090"]["observations"]["structured_client"]["fail_closed"]["errors"] = [sentinel]
        MODULE.save(path, evidence)
        self.assertEqual(self.compose(), 0)
        receipt = MODULE.load(self.release_root / "acceptance/rtx4090-public-install.json")
        self.assertNotIn(sentinel, json.dumps(receipt))
        self.assertEqual(MODULE.load(path), evidence)

    def test_composition_replaces_the_staged_route_acceptance_summary(self) -> None:
        """Staging leaves the summary the ready gate reads pending; composition, not a hand edit,
        replaces it with what this composition bound."""
        self.add_3090()
        self.assertEqual(self.compose(), 0)
        qualification = MODULE.load(self.release_root / "qualification.json")
        routes = self.release_root / "acceptance" / "documented-routes.json"
        version = DESCRIPTOR["omp"]["distribution_version"]
        self.assertEqual(qualification["documented_route_acceptance"], {
            "status": "passed",
            "scope": MODULE.load(self.root / "evidence.json")["documented_routes"]["scope"],
            "candidate_commit": CANDIDATE,
            "evidence_commit_changes_candidate": False,
            "evidence_path": f"releases/{self.release}/acceptance/documented-routes.json",
            "evidence_sha256": MODULE.sha256(routes.read_bytes()),
            "documented_route_steps": {
                lane: "{0}/{0}".format(len(MODULE.documented_route.LANES[lane]))
                for lane in (*MODULE.LANES, *MODULE.NATIVE_LANES)},
            "platform_receipts": [f"releases/{self.release}/acceptance/{platform}-{version}.json"
                                  for platform in MODULE.OMP_PROFILE_PLATFORMS.values()],
            "fresh_product_acceptance": True,
            "restoration": {
                "path": "docs/measurements/fixture-acceptance-restoration.json",
                "status": "passed",
                "driver_hold_s": RESTORATION["rtx5090"]["window_hold_seconds"][-1],
                "production_upgrade_activated": False,
                "documented_directory_presence_restored": True,
                "native_documented_stage_restored": True,
                "native_driver_window_s": {gpu: RESTORATION[gpu]["window_hold_seconds"]
                                           for gpu in ("rtx4090", "rtx3090")},
            },
            "composition_run": True,
        })
        self.assertEqual(qualification["composition"]["documented_route_acceptance"]["sha256"],
                         MODULE.sha256(routes.read_bytes()))
        errors: list[str] = []
        validate_ready_state_consistency({}, {}, qualification, errors)
        self.assertEqual(errors, [])

    def test_route_acceptance_summary_needs_the_accepted_scope_before_writing(self) -> None:
        self.refused_before_writing(lambda evidence: evidence["documented_routes"], (
            ("absent", lambda routes: routes.pop("scope"), "needs the scope"),
            ("blank", lambda routes: routes.update(scope=" "), "needs the scope"),
        ))

    def add_3090(self, *, route: bool = True, evidence: bool = True) -> None:
        manifest = MODULE.load(self.release_root / "manifest.json")
        variant = deepcopy(manifest["components"]["ninfer_variants"][0])
        variant.update(id="rtx3090-windows-native", release_tag="v0.6.2-qwen38-3090-beta.1",
                       package_sha256="3" * 64, qualification={"summary": "qualification/rtx3090.json"})
        manifest["components"]["ninfer_variants"].insert(0, variant)
        MODULE.save(self.release_root / "manifest.json", manifest)
        MODULE.save(self.release_root / "qualification" / "rtx3090.json", FIRST_RELEASE)
        if evidence:
            source = MODULE.load(self.root / "evidence.json")
            source["rtx3090"] = native_evidence("rtx3090")
            source["restoration"]["rtx3090"] = deepcopy(RESTORATION["rtx3090"])
            MODULE.save(self.root / "evidence.json", source)
        if route:
            receipt = route_receipt("rtx3090-native")
            receipt["document_sha256"] = MODULE.sha256(self.document.read_bytes())
            for step, (_, block) in zip(receipt["steps"], MODULE.documented_route.lane_blocks(self.document, "rtx3090-native")):
                step["block_sha256"] = step["executed_sha256"] = block.sha256
            path = self.root / "rtx3090-native.json"
            MODULE.save(path, receipt)
            self.argv += ["--route", f"rtx3090-native={path}"]
        self.bind_native_policies()

    def test_five_routes_bind_separate_native_public_install_receipts(self) -> None:
        self.add_3090()
        self.assertEqual(self.compose(), 0)
        acceptance = self.release_root / "acceptance"
        routes = MODULE.load(acceptance / "documented-routes.json")
        self.assertEqual(set(routes["routes"]), set(MODULE.LANES) | set(MODULE.NATIVE_LANES))
        external = MODULE.load(acceptance / "composed-external-installation.json")
        for lane, digest in (("rtx4090", "9" * 64), ("rtx3090", "3" * 64)):
            path = acceptance / f"{lane}-public-install.json"
            receipt = MODULE.load(path)
            self.assertEqual(receipt["runtime"]["package_sha256"], digest)
            self.assertEqual(receipt["lane"], f"{lane}-windows-native")
            self.assertEqual(external["evidence"][f"{lane}_public_install"]["sha256"], MODULE.sha256(path.read_bytes()))

    def waive_3090(self, *, failed_phase: str = "structured-outage") -> Path:
        self.add_3090(evidence=False)
        route = self.root / "rtx3090-native.json"
        path = self.release_root / "qualification/rtx3090-route-waiver.json"
        waiver = campaign_waiver(self.release, CANDIDATE, MODULE.sha256(route.read_bytes()),
                                 failed_phase=failed_phase)
        MODULE.save(path, waiver)
        binding = {"repository_path": path.relative_to(self.root).as_posix(),
                   "sha256": MODULE.sha256(path.read_bytes())}
        evidence = MODULE.load(self.root / "evidence.json")
        evidence["rtx3090"] = {
            "status": "failed", "failed_phase": failed_phase, "founder_waiver": binding,
            **waived_campaign_evidence(waiver),
            "preparation": {"lineage_mode": "first_release", "previous_release_present": False},
            "observations": {"rollback": deepcopy(FIRST_RELEASE["rollback"])}}
        evidence["restoration"]["rtx3090"] = {**waiver["restoration_summary"], "founder_waiver": binding}
        MODULE.save(self.root / "evidence.json", evidence)
        self.bind_native_policies()
        evidence = MODULE.load(self.root / "evidence.json")
        waiver["evidence_sha256"]["documented-route.json"] = MODULE.sha256(route.read_bytes())
        if failed_phase == "native-probes":
            waiver["probe_projection_sha256"]["compaction"] = (
                evidence["rtx3090"]["probe_acceptance"]["compaction"]["sha256"])
        MODULE.save(path, waiver)
        binding["sha256"] = MODULE.sha256(path.read_bytes())
        evidence["rtx3090"]["founder_waiver"] = binding
        evidence["restoration"]["rtx3090"]["founder_waiver"] = binding
        MODULE.save(self.root / "evidence.json", evidence)
        self.argv += ["--native-route-waiver", f"rtx3090-native={binding['repository_path']}"]
        return path

    def test_waived_campaign_composes_and_verifies_without_rewriting_the_passed_route(self) -> None:
        path = self.waive_3090()
        raw = (self.root / "rtx3090-native.json").read_bytes()
        self.assertEqual(self.compose(), 0)
        qualification = MODULE.load(self.release_root / "qualification.json")
        routes = MODULE.load(self.release_root / "acceptance/documented-routes.json")
        external = MODULE.load(self.release_root / "acceptance/composed-external-installation.json")
        binding = {"repository_path": path.relative_to(self.root).as_posix(),
                   "sha256": MODULE.sha256(path.read_bytes())}
        self.assertEqual(routes["routes"]["rtx3090-native"]["status"], "passed")
        campaign = routes["native_campaigns"]["rtx3090-native"]
        self.assertEqual(campaign["status"], "failed")
        self.assertEqual(campaign["failed_phase"], "structured-outage")
        self.assertEqual(campaign["founder_waiver"], binding)
        self.assertIn("probe_acceptance", campaign)
        self.assertEqual((self.root / routes["routes"]["rtx3090-native"]["receipt"]).read_bytes(), raw)
        self.assertEqual(external["status"], "waived-by-founder")
        self.assertEqual(qualification["composition"]["external_installation_acceptance"]["status"],
                         "waived-by-founder")
        self.assertEqual(external["steps"]["rtx3090-native"]["status"], "failed")
        self.assertEqual(external["steps"]["rtx4090-native"]["status"], "passed")
        restoration = MODULE.load(self.root / routes["restoration_receipt"]["repository_path"])
        self.assertEqual(restoration["status"], "passed-with-founder-waiver")
        self.assertEqual(restoration["rtx3090"]["status"], "restored-by-lead")
        self.assertEqual(restoration["rtx4090"]["status"], "passed")
        self.assertEqual(restoration["rtx3090"]["power_limit_w"],
                         campaign["stopped_owner_census"]["power_limit_w"])
        self.assertEqual(qualification["documented_route_acceptance"]["restoration"]["status"],
                         "passed-with-founder-waiver")
        self.assertNotIn("rtx3090_public_install", external["evidence"])
        self.assertFalse((self.release_root / "acceptance/rtx3090-public-install.json").exists())
        errors = []
        validate_documented_route_acceptance(self.root, qualification, errors)
        validate_native_route_policy(self.root, self.release,
                                     MODULE.load(self.release_root / "manifest.json"), qualification, errors)
        self.assertEqual(errors, [])

    def test_native_probes_waiver_composes_and_verifies_the_failed_compaction(self) -> None:
        self.waive_3090(failed_phase="native-probes")
        raw = (self.root / "rtx3090-native.json").read_bytes()
        self.assertEqual(self.compose(), 0)
        qualification = MODULE.load(self.release_root / "qualification.json")
        routes = MODULE.load(self.release_root / "acceptance/documented-routes.json")
        campaign = routes["native_campaigns"]["rtx3090-native"]
        self.assertEqual(campaign["status"], "failed")
        self.assertEqual(campaign["failed_phase"], "native-probes")
        self.assertIs(campaign["probe_acceptance"]["compaction"]["passed"], False)
        self.assertEqual(campaign["probe_acceptance"]["compaction"]["checks"], {})
        self.assertEqual(campaign["window_failure"]["observed_summary"]["managed_stop"]["sessions_refused"], 3)
        self.assertEqual((self.root / routes["routes"]["rtx3090-native"]["receipt"]).read_bytes(), raw)
        external = MODULE.load(self.release_root / "acceptance/composed-external-installation.json")
        self.assertEqual(external["status"], "waived-by-founder")
        self.assertEqual(external["steps"]["rtx3090-native"]["status"], "failed")
        self.assertNotIn("rtx3090_public_install", external["evidence"])
        self.assertFalse((self.release_root / "acceptance/rtx3090-public-install.json").exists())
        restoration = MODULE.load(self.root / routes["restoration_receipt"]["repository_path"])
        self.assertEqual(restoration["status"], "passed-with-founder-waiver")
        self.assertEqual(restoration["rtx3090"]["outcome"], "graceful")
        self.assertTrue(any("native-probes compaction probe failed" in note
                            for note in external["limitations"]))
        errors = []
        validate_documented_route_acceptance(self.root, qualification, errors)
        validate_native_route_policy(self.root, self.release,
                                     MODULE.load(self.release_root / "manifest.json"), qualification, errors)
        self.assertEqual(errors, [])

    def test_native_probe_waiver_binds_the_failed_projection_before_writing(self) -> None:
        path = self.waive_3090(failed_phase="native-probes")
        original, source = MODULE.load(path), MODULE.load(self.root / "evidence.json")
        for case in ("missing object", "missing compaction", "non-object", "mismatched waiver",
                     "mismatched projection"):
            with self.subTest(case=case):
                waiver, evidence = deepcopy(original), deepcopy(source)
                if case == "missing object":
                    waiver.pop("probe_projection_sha256")
                elif case == "missing compaction":
                    waiver["probe_projection_sha256"].clear()
                elif case == "non-object":
                    waiver["probe_projection_sha256"] = []
                elif case == "mismatched waiver":
                    waiver["probe_projection_sha256"]["compaction"] = "0" * 64
                else:
                    evidence["rtx3090"]["probe_acceptance"]["compaction"]["sha256"] = "0" * 64
                MODULE.save(path, waiver)
                binding = {"repository_path": path.relative_to(self.root).as_posix(),
                           "sha256": MODULE.sha256(path.read_bytes())}
                evidence["rtx3090"]["founder_waiver"] = binding
                evidence["restoration"]["rtx3090"]["founder_waiver"] = binding
                MODULE.save(self.root / "evidence.json", evidence)
                with self.assertRaisesRegex(SystemExit, "compaction projection SHA-256"):
                    self.compose()
                self.assertFalse((self.release_root / "acceptance").exists())
                self.assertEqual(list((self.root / "docs/measurements").iterdir()), [])

    def test_native_probe_waiver_does_not_excuse_other_probes_or_relabel_compaction_passed(self) -> None:
        self.waive_3090(failed_phase="native-probes")
        source = MODULE.load(self.root / "evidence.json")
        for name in ("fleet", "fanout", "parallel", "compaction"):
            with self.subTest(probe=name):
                evidence = deepcopy(source)
                proof = evidence["rtx3090"]["probe_acceptance"][name]
                if name == "fleet":
                    proof["transient_retries"] = 1
                elif name == "fanout":
                    proof["ok"] = False
                else:
                    proof["passed"] = name == "compaction"
                MODULE.save(self.root / "evidence.json", evidence)
                with self.assertRaisesRegex(SystemExit, name):
                    self.compose()
                self.assertFalse((self.release_root / "acceptance").exists())

    def test_native_probe_failure_without_a_founder_waiver_is_refused(self) -> None:
        self.waive_3090(failed_phase="native-probes")
        del self.argv[-2:]
        with self.assertRaisesRegex(SystemExit, "explicit founder waiver"):
            self.compose()
        self.assertFalse((self.release_root / "acceptance").exists())

    def test_waiver_requires_the_specific_refused_managed_stop_observations(self) -> None:
        path = self.waive_3090()
        original = MODULE.load(path)
        source = MODULE.load(self.root / "evidence.json")
        for field, value in (("action", "Control-Release.ps1 -Action Start"), ("outcome", "forced"),
                             ("sessions_refused", 0), ("sessions_refused", True),
                             ("sessions_refused", 1.0), ("shutdown_complete", True),
                             ("outcome", None)):
            with self.subTest(field=field, value=value):
                waiver, evidence = deepcopy(original), deepcopy(source)
                if value is None:
                    waiver["observed_summary"].pop(field)
                else:
                    waiver["observed_summary"][field] = value
                MODULE.save(path, waiver)
                binding = {"repository_path": path.relative_to(self.root).as_posix(),
                           "sha256": MODULE.sha256(path.read_bytes())}
                evidence["rtx3090"]["founder_waiver"] = binding
                evidence["restoration"]["rtx3090"]["founder_waiver"] = binding
                MODULE.save(self.root / "evidence.json", evidence)
                with self.assertRaisesRegex(SystemExit, "observed_summary"):
                    self.compose()
                self.assertFalse((self.release_root / "acceptance").exists())

    def test_waiver_requires_matching_hash_bound_window_failure_observations(self) -> None:
        self.waive_3090()
        original = MODULE.load(self.root / "evidence.json")
        for field, value in (("sha256", "0" * 64), ("boundary", "behavior-evidence"),
                             ("action", "Control-Release.ps1 -Action Start"), ("outcome", "forced"),
                             ("sessions_refused", 0), ("shutdown_complete", True)):
            with self.subTest(field=field):
                evidence = deepcopy(original)
                failure = evidence["rtx3090"]["window_failure"]
                target = failure if field in ("sha256", "boundary") else failure["observed_summary"]
                target[field] = value
                MODULE.save(self.root / "evidence.json", evidence)
                with self.assertRaisesRegex(SystemExit, "window-failure"):
                    self.compose()
                self.assertFalse((self.release_root / "acceptance").exists())

    def test_waived_restoration_requires_lead_observations_and_stopped_owner_power(self) -> None:
        path = self.waive_3090()
        original, source = MODULE.load(path), MODULE.load(self.root / "evidence.json")
        for target in ("waiver", "restoration"):
            for field, value in (("outcome", None), ("outcome", "forced"), ("sessions_refused", 1),
                                 ("sessions_refused", False), ("runtime_record_absent", False),
                                 ("gpu_owner_lease_absent", False), ("all_native_tasks_ready", False),
                                 ("server_processes", 1), ("port_18082_listeners", 1),
                                 ("power_limit_w", 350)):
                with self.subTest(target=target, field=field, value=value):
                    waiver, evidence = deepcopy(original), deepcopy(source)
                    recovery = (waiver["restoration_summary"] if target == "waiver"
                                else evidence["restoration"]["rtx3090"])
                    if value is None:
                        recovery.pop(field)
                    else:
                        recovery[field] = value
                    MODULE.save(path, waiver)
                    binding = {"repository_path": path.relative_to(self.root).as_posix(),
                               "sha256": MODULE.sha256(path.read_bytes())}
                    evidence["rtx3090"]["founder_waiver"] = binding
                    evidence["restoration"]["rtx3090"]["founder_waiver"] = binding
                    MODULE.save(self.root / "evidence.json", evidence)
                    with self.assertRaisesRegex(SystemExit, field):
                        self.compose()
                    self.assertFalse((self.release_root / "acceptance").exists())

    def test_waived_restoration_requires_the_hash_bound_lane_census(self) -> None:
        self.waive_3090()
        original = MODULE.load(self.root / "evidence.json")
        for field, value in (("sha256", "0" * 64), ("lane", "rtx4090"), ("power_limit_w", None)):
            with self.subTest(field=field):
                evidence = deepcopy(original)
                evidence["rtx3090"]["stopped_owner_census"][field] = value
                MODULE.save(self.root / "evidence.json", evidence)
                with self.assertRaisesRegex(SystemExit, "native census evidence"):
                    self.compose()
                self.assertFalse((self.release_root / "acceptance").exists())

    def test_unwaived_failed_native_campaign_is_refused(self) -> None:
        self.waive_3090()
        del self.argv[-2:]
        with self.assertRaises(SystemExit):
            self.compose()
        self.assertFalse((self.release_root / "acceptance").exists())

    def test_waiver_on_a_passed_native_campaign_is_refused(self) -> None:
        path = self.waive_3090()
        evidence = MODULE.load(self.root / "evidence.json")
        binding = evidence["rtx3090"]["founder_waiver"]
        evidence["rtx3090"] = {**native_evidence("rtx3090"), "status": "passed",
                               "failed_phase": "structured-outage", "founder_waiver": binding}
        evidence["restoration"]["rtx3090"] = deepcopy(RESTORATION["rtx3090"])
        MODULE.save(self.root / "evidence.json", evidence)
        with self.assertRaises(SystemExit):
            self.compose()
        self.assertTrue(path.exists())
        self.assertFalse((self.release_root / "acceptance").exists())

    def test_waiver_subject_mismatch_is_refused_before_writing(self) -> None:
        path = self.waive_3090()
        original = MODULE.load(path)
        for field, value in (("release", "v0.1.0"), ("candidate", "2" * 40),
                             ("lane", "rtx4090-native"), ("failed_phase", "documented-route")):
            with self.subTest(field=field):
                MODULE.save(path, {**original, field: value})
                evidence = MODULE.load(self.root / "evidence.json")
                binding = {"repository_path": path.relative_to(self.root).as_posix(),
                           "sha256": MODULE.sha256(path.read_bytes())}
                evidence["rtx3090"]["founder_waiver"] = binding
                evidence["restoration"]["rtx3090"]["founder_waiver"] = binding
                MODULE.save(self.root / "evidence.json", evidence)
                with self.assertRaises(SystemExit):
                    self.compose()
                self.assertFalse((self.release_root / "acceptance").exists())
                self.assertEqual(list((self.root / "docs/measurements").iterdir()), [])

    def test_missing_waiver_and_changed_projection_binding_are_refused(self) -> None:
        path = self.waive_3090()
        original = path.read_bytes()
        path.unlink()
        with self.assertRaises(SystemExit):
            self.compose()
        path.write_bytes(original + b"\n")
        with self.assertRaises(SystemExit):
            self.compose()
        self.assertFalse((self.release_root / "acceptance").exists())

    def test_waiver_does_not_excuse_an_incomplete_documented_route(self) -> None:
        path = self.waive_3090()
        receipt_path = self.root / "rtx3090-native.json"
        receipt = MODULE.load(receipt_path)
        receipt["steps"][-1]["status"] = "failed"
        MODULE.save(receipt_path, receipt)
        waiver = MODULE.load(path)
        waiver["evidence_sha256"]["documented-route.json"] = MODULE.sha256(receipt_path.read_bytes())
        MODULE.save(path, waiver)
        evidence = MODULE.load(self.root / "evidence.json")
        binding = {"repository_path": path.relative_to(self.root).as_posix(),
                   "sha256": MODULE.sha256(path.read_bytes())}
        evidence["rtx3090"]["founder_waiver"] = binding
        evidence["restoration"]["rtx3090"]["founder_waiver"] = binding
        MODULE.save(self.root / "evidence.json", evidence)
        with self.assertRaises(SystemExit):
            self.compose()
        self.assertFalse((self.release_root / "acceptance").exists())

    def test_waiver_does_not_excuse_native_probe_failure(self) -> None:
        self.waive_3090()
        evidence = MODULE.load(self.root / "evidence.json")
        evidence["rtx3090"]["probe_acceptance"]["compaction"]["passed"] = False
        MODULE.save(self.root / "evidence.json", evidence)
        with self.assertRaises(SystemExit):
            self.compose()
        self.assertFalse((self.release_root / "acceptance").exists())

    def test_waiver_does_not_excuse_another_native_lanes_observations(self) -> None:
        self.waive_3090()
        evidence = MODULE.load(self.root / "evidence.json")
        evidence["rtx4090"]["observations"]["exact_tool_marker"] = False
        MODULE.save(self.root / "evidence.json", evidence)
        with self.assertRaises(SystemExit):
            self.compose()
        self.assertFalse((self.release_root / "acceptance").exists())

    def p15_fixture(self, *, rebuild_4090: bool) -> dict:
        self.add_3090()
        self.release = "v0.15.0"
        target = self.root / "releases" / self.release
        self.release_root.rename(target)
        self.release_root = target
        self.argv[self.argv.index("--release") + 1] = self.release
        manifest = MODULE.load(target / "manifest.json")
        manifest["release"] = self.release
        evidence = MODULE.load(self.root / "evidence.json")
        for variant in manifest["components"]["ninfer_variants"]:
            gpu = variant["id"].split("-")[0]
            variant["release_tag"] = f"v0.8.0-qwen38-{gpu[3:]}-beta.1"
            variant["runtime_shape"] = {
                "max_concurrency": 1, "speculative_backend": "dflash2" if gpu == "rtx3090" else "mtp",
                "fit": {"device_state_slots": 0 if gpu == "rtx3090" else 2,
                        "admission_headroom_mib": 768 if gpu == "rtx3090" else 640,
                        "draft_mlp_device_format": "Q4_G64_FP16" if gpu == "rtx3090" else "artifact",
                        "token_embedding_residency": "host-mapped" if gpu == "rtx3090" else "device"}}
            field = "quality_screen" if gpu == "rtx3090" else "t1_parity"
            variant["qualification"][field] = {
                "path": f"releases/{self.release}/qualification/{gpu}.{field}.json", "sha256": "7" * 64}
            rollback = {"status": "passed", "directions": 2,
                        "intermediate_release": f"qwen38-{gpu[3:]}-native-v0.7.0-beta.3",
                        "active_release": f"qwen38-{gpu[3:]}-native-v0.8.0-beta.1"}
            MODULE.save(target / "qualification" / f"{gpu}.json", {"rollback": rollback})
            evidence[gpu]["preparation"].update(lineage_mode="upgrade", previous_release_present=True)
            evidence[gpu]["observations"]["rollback"] = rollback
        if not rebuild_4090:
            manifest["components"]["ninfer_variants"] = [
                row for row in manifest["components"]["ninfer_variants"] if row["id"].startswith("rtx3090")]
            del evidence["rtx4090"], evidence["restoration"]["rtx4090"]
            index = self.argv.index(f"rtx4090-native={self.root / 'rtx4090-native.json'}")
            del self.argv[index - 1:index + 1]
        MODULE.save(target / "manifest.json", manifest)
        MODULE.save(self.root / "evidence.json", evidence)
        self.bind_subject()
        evidence = MODULE.load(self.root / "evidence.json")
        for platform in evidence["platforms"].values():
            platform["release"] = self.release
        MODULE.save(self.root / "evidence.json", evidence)
        for path in (self.root / "compatibility.json", target / "compatibility.json"):
            authority = MODULE.load(path)
            authority["product_release"] = self.release
            MODULE.save(path, authority)
        return manifest

    def test_p15_3090_dflash_and_4090_mtp_rebuild_compose_without_changing_runtime_gates(self):
        before = self.p15_fixture(rebuild_4090=True)
        self.assertEqual(self.compose(), 0)
        after = MODULE.load(self.release_root / "manifest.json")
        self.assertEqual(after["components"]["ninfer_variants"], before["components"]["ninfer_variants"])
        routes = MODULE.load(self.release_root / "acceptance/documented-routes.json")
        self.assertEqual(set(routes["routes"]), set(MODULE.LANES) | set(MODULE.NATIVE_LANES))
        for gpu in ("rtx3090", "rtx4090"):
            receipt = MODULE.load(self.release_root / "acceptance" / f"{gpu}-public-install.json")
            self.assertEqual(receipt["runtime"]["tag"], f"v0.8.0-qwen38-{gpu[3:]}-beta.1")
            self.assertEqual(receipt["observations"]["rollback"]["directions"], 2)
            self.assertIn("v0.7.0-beta.3", receipt["observations"]["rollback"]["intermediate_release"])

    def test_p15_3090_only_uses_four_routes_and_one_native_restoration(self):
        self.p15_fixture(rebuild_4090=False)
        self.assertEqual(self.compose(), 0)
        routes = MODULE.load(self.release_root / "acceptance/documented-routes.json")
        self.assertEqual(set(routes["routes"]), set(MODULE.LANES) | {"rtx3090-native"})
        self.assertFalse((self.release_root / "acceptance/rtx4090-public-install.json").exists())
        qualification = MODULE.load(self.release_root / "qualification.json")
        self.assertEqual(set(qualification["documented_route_acceptance"]["restoration"]["native_driver_window_s"]),
                         {"rtx3090"})

    def test_bound_3090_requires_its_route_and_evidence(self) -> None:
        self.add_3090(route=False, evidence=False)
        with self.assertRaisesRegex(SystemExit, "need one --route"):
            self.compose()
        self.assertFalse((self.release_root / "acceptance").exists())
        self.argv += ["--route", f"rtx3090-native={self.root / 'unused.json'}"]
        with self.assertRaisesRegex(SystemExit, "evidence needs rtx3090"):
            self.compose()

    def test_unbound_3090_or_duplicate_route_is_refused(self) -> None:
        self.argv += ["--route", f"rtx3090-native={self.root / 'unused.json'}"]
        with self.assertRaisesRegex(SystemExit, "need one --route"):
            self.compose()
        self.argv[-1] = f"rtx4090-native={self.root / 'unused.json'}"
        with self.assertRaisesRegex(SystemExit, "duplicate --route"):
            self.compose()

    def test_accepted_3090_cannot_keep_a_deferred_route_claim(self) -> None:
        self.add_3090()
        evidence = MODULE.load(self.root / "evidence.json")
        evidence["documented_routes"]["deferred_routes"] = {"rtx3090-native": "old release"}
        MODULE.save(self.root / "evidence.json", evidence)
        with self.assertRaisesRegex(SystemExit, "accepted routes cannot also be deferred"):
            self.compose()
        self.assertFalse((self.release_root / "acceptance").exists())


    def test_client_from_another_upstream_release_is_refused_before_writing_receipts(self) -> None:
        authority = MODULE.load(self.root / "compatibility.json")
        authority["profiles"][0]["client_distribution"]["upstream_tag"] = "v18.4.0"
        MODULE.save(self.root / "compatibility.json", authority)
        with self.assertRaisesRegex(SystemExit, "upstream_tag must match"):
            self.compose()
        self.assertFalse((self.release_root / "acceptance").exists())


if __name__ == "__main__":
    unittest.main()
