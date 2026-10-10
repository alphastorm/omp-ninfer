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
from verify_release import validate_client_profile_predicates  # noqa: E402  # pyright: ignore[reportMissingImports]

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
    PROFILE = {"id": "darwin-remote-ssh", "client_distribution": client_distribution("darwin-arm64")}

    def evidence(self, binary: str) -> dict:
        return {"binary_sha256": binary, "live_acceptance": deepcopy(LIVE),
                "limitations": []}

    def test_stock_client_receipt_needs_no_previous_fork_receipt(self) -> None:
        receipt = MODULE.platform_receipt("v9.9.9", "2026-01-01", self.PROFILE,
                                          self.evidence("8" * 64), MANIFEST)
        self.assertEqual(receipt["product_release"], "v9.9.9")
        self.assertEqual(receipt["client"]["asset_sha256"], "8" * 64)
        self.assertEqual(receipt["source"]["repository"], UPSTREAM["upstream_repository"])
        self.assertNotIn("hosted_ci", receipt)
        self.assertNotIn("diagnostics", receipt)
        self.assertFalse(receipt["safety"]["cloud_fallback_observed"])

    def test_an_installed_binary_other_than_the_published_client_is_refused(self) -> None:
        message = refused(MODULE.platform_receipt, "v9.9.9", "2026-01-01", self.PROFILE,
                          self.evidence("9" * 64), MANIFEST)
        self.assertIn("not the published client", message)

    def test_wrong_preflight_version_cannot_be_claimed_as_passed(self) -> None:
        evidence = self.evidence("8" * 64)
        evidence["live_acceptance"]["omp_version"] = "omp/18.2.3"
        message = refused(MODULE.platform_receipt, "v9.9.9", "2026-01-01", self.PROFILE,
                          evidence, MANIFEST)
        self.assertIn("client version differs", message)

    def test_fork_client_cannot_be_accepted_as_stock(self) -> None:
        profile = deepcopy(self.PROFILE)
        del profile["client_distribution"]["distribution_kind"]
        self.assertIn("stock upstream client required", refused(
            MODULE.platform_receipt, "v9.9.9", "2026-01-01", profile, self.evidence("8" * 64), MANIFEST))


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
            "model_artifact_sha256": "c" * 64}]
        manifest.update(status="candidate", publication={"blockers": ["acceptance"]}, qualification={})
        MODULE.save(self.release_root / "manifest.json", manifest)
        MODULE.save(self.release_root / "qualification.json", {
            "as_of": "2026-01-01", "composition": {"external_installation_acceptance": {
                "public_url": "https://example.invalid/acceptance.json"}}})
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
                "binary_sha256": profile["client_distribution"]["binary_sha256"],
                "live_acceptance": deepcopy(LIVE), "limitations": []} for profile in self.profiles},
            "rtx4090": {"preparation": {}, "observations": {}, "limitations": []},
            "restoration": {},
            "documented_routes": {"mode": "offline-fixture", "qualification_environment": {}},
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

    def compose(self) -> int:
        with patch.object(MODULE, "ROOT", self.root), patch.object(MODULE, "DOCUMENT", self.document), \
                patch.object(sys, "argv", self.argv), redirect_stdout(io.StringIO()):
            return MODULE.main()

    def omit_4090(self) -> None:
        manifest = MODULE.load(self.release_root / "manifest.json")
        manifest["components"]["ninfer_variants"] = []
        MODULE.save(self.release_root / "manifest.json", manifest)
        evidence = MODULE.load(self.root / "evidence.json")
        del evidence["rtx4090"]
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
                evidence[gpu] = {"preparation": {}, "observations": {}, "limitations": []}
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

    def add_3090(self, *, route: bool = True, evidence: bool = True) -> None:
        manifest = MODULE.load(self.release_root / "manifest.json")
        variant = deepcopy(manifest["components"]["ninfer_variants"][0])
        variant.update(id="rtx3090-windows-native", release_tag="v0.6.2-qwen38-3090-beta.1",
                       package_sha256="3" * 64)
        manifest["components"]["ninfer_variants"].insert(0, variant)
        MODULE.save(self.release_root / "manifest.json", manifest)
        if evidence:
            source = MODULE.load(self.root / "evidence.json")
            source["rtx3090"] = {"preparation": {}, "observations": {"lane": "rtx3090"}, "limitations": []}
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
