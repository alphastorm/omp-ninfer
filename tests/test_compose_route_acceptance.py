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
        manifest.update(status="candidate", publication={"blockers": ["acceptance"]}, qualification={})
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

    def bind_subject(self):
        path = self.release_root / "review/runtime-ledger.json"
        MODULE.save(path, {"artifact_type": "omp_ninfer_review_ledger", "release": self.release,
                           "product_tooling": {"stage_commit": CANDIDATE}})
        qualification = MODULE.load(self.release_root / "qualification.json")
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

    def p15_fixture(self, *, rebuild_4090: bool) -> dict:
        self.add_3090()
        self.release = "v0.15.0"
        target = self.root / "releases" / self.release
        self.release_root.rename(target)
        self.release_root = target
        self.argv[self.argv.index("--release") + 1] = self.release
        manifest = MODULE.load(target / "manifest.json")
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
