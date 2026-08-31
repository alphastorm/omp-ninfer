from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_release", ROOT / "scripts" / "verify_release.py"
)
assert SPEC is not None and SPEC.loader is not None
VERIFY_RELEASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY_RELEASE)


class ReleaseContractTest(unittest.TestCase):
    def test_omp_component_identity_accepts_preview_and_beta_only(self) -> None:
        self.assertIsNotNone(
            VERIFY_RELEASE.OMP_RELEASE_ID_RE.fullmatch(
                "18.0.9-cross-platform-beta-1"
            )
        )
        self.assertIsNotNone(
            VERIFY_RELEASE.OMP_RELEASE_ID_RE.fullmatch(
                "18.0.9-cross-platform-preview-5"
            )
        )
        self.assertIsNone(
            VERIFY_RELEASE.OMP_RELEASE_ID_RE.fullmatch("18.0.9-cross-platform-stable-1")
        )

    def test_ga_release_predicate_exempts_prerelease_contracts(self) -> None:
        self.assertFalse(VERIFY_RELEASE.ga_release("v0.2.0-beta.1"))
        self.assertFalse(VERIFY_RELEASE.ga_release("v0.3.0-rc.1"))
        self.assertTrue(VERIFY_RELEASE.ga_release("v0.4.2"))

    def candidate_copy(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        shutil.copytree(ROOT / "releases", root / "releases")
        shutil.copytree(ROOT / "profiles", root / "profiles")
        (root / "docs").mkdir()
        historical = root / "releases" / "v0.2.0-beta.1"
        shutil.copy2(historical / "compatibility.json", root / "compatibility.json")
        shutil.copy2(historical / "COMPATIBILITY.md", root / "docs" / "COMPATIBILITY.md")
        historical_manifest = self.load(historical / "manifest.json")
        historical_profile = historical_manifest["runtime_identity"]["deployment_profile"]
        for profile_path in (root / "profiles").glob("*.json"):
            profile = self.load(profile_path)
            profile["release"] = "v0.2.0-beta.1"
            profile["server"]["deployment_profile"] = historical_profile
            arguments = profile["server"].get("arguments", [])
            for index, argument in enumerate(arguments[:-1]):
                if argument == "--deployment-profile":
                    arguments[index + 1] = historical_profile
            self.save(profile_path, profile)
        return temporary, root

    def public_draft_copy(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        shutil.copytree(ROOT / "releases", root / "releases")
        shutil.copytree(ROOT / "profiles", root / "profiles")
        shutil.copy2(ROOT / "compatibility.json", root / "compatibility.json")
        (root / "docs" / "measurements").mkdir(parents=True)
        shutil.copy2(ROOT / "docs" / "COMPATIBILITY.md", root / "docs" / "COMPATIBILITY.md")
        shutil.copy2(
            ROOT / "docs" / "measurements" / "2026-08-30-rtx3090-parity.json",
            root / "docs" / "measurements" / "2026-08-30-rtx3090-parity.json",
        )
        return temporary, root

    @staticmethod
    def load(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def save(path: Path, value: dict) -> None:
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def make_candidate(self, root: Path, manifest: dict) -> None:
        qualification_path = root / "releases" / "v0.2.0-beta.1" / "qualification.json"
        qualification = self.load(qualification_path)
        qualification["external_installation_qualified"] = False
        self.save(qualification_path, qualification)
        manifest["qualification"]["summary_sha256"] = hashlib.sha256(
            qualification_path.read_bytes()
        ).hexdigest()
        manifest["status"] = "candidate"
        manifest["qualification"]["external_installation_passed"] = False
        manifest["publication"]["blockers"] = ["Run the external-install acceptance path."]

    def test_checked_in_ready_release_is_installable(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertEqual(manifest["status"], "ready")
        self.assertEqual(errors, [])

        _, ready_errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertEqual(ready_errors, [])

        _, installable_errors = VERIFY_RELEASE.validate(
            root,
            require_ready=False,
            require_installable=True,
        )
        self.assertEqual(installable_errors, [])

    def test_checked_in_public_release_is_ready(self) -> None:
        manifest, errors = VERIFY_RELEASE.validate(ROOT, require_ready=False)
        self.assertEqual(errors, [])
        self.assertEqual(manifest["status"], "ready")
        self.assertEqual((manifest["channel"], manifest["audience"]), ("public", "public"))
        self.assertEqual(manifest["publication"]["blockers"], [])
        self.assertEqual(
            manifest["components"]["ninfer"]["oci_manifest_digest"],
            "sha256:ce3cd21591d9a5a424a56c78652e0e8e70a7e0c85983df96fd55727058c04937",
        )
        summary_sha = hashlib.sha256(
            (ROOT / "releases" / "v0.4.2" / "qualification.json").read_bytes()
        ).hexdigest()
        self.assertEqual(manifest["qualification"].get("summary_sha256"), summary_sha)

    def test_release_tree_text_rejects_private_markers(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        planted = root / "releases" / "v0.4.2" / "review" / "planted.json"
        planted.write_text('{"path": "/Users/someone/secret"}', encoding="utf-8")
        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertTrue(
            any("private marker" in error and "planted.json" in error for error in errors),
            errors,
        )

    def test_ready_rejects_stale_phrase_inside_limitation_lists(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.4.2" / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["limitations"] = list(manifest.get("limitations", [])) + [
            "The RTX 5090 identities remain pending."
        ]
        self.save(manifest_path, manifest)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertTrue(
            any("stale release-state phrase" in error for error in errors),
            errors,
        )

    def test_public_release_passes_ready_validation(self) -> None:
        _, errors = VERIFY_RELEASE.validate(ROOT, require_ready=True)
        self.assertEqual(errors, [])

    def test_unknown_release_channel_fails_closed(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.4.2" / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["channel"] = "general-availability"
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn(
            "manifest channel and audience must form a recognized release posture",
            errors,
        )

    def test_draft_contract_remains_noninstallable(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["status"] = "draft"
        manifest["components"]["omp"]["artifact_published"] = False
        manifest["publication"]["blockers"] = ["Draft release is not installable."]
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertEqual(errors, [])
        _, installable_errors = VERIFY_RELEASE.validate(
            root, require_ready=False, require_installable=True
        )
        self.assertIn("release manifest is not installable", installable_errors)

    def test_draft_still_validates_present_external_identities(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["status"] = "draft"
        manifest["publication"]["blockers"] = ["Draft release is not installable."]
        manifest["components"]["ninfer"]["oci_manifest_digest"] = f"sha256:{'f' * 64}"
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("local packaging and manifest OCI digests must match", errors)

    def test_candidate_accepts_exact_installable_components_before_external_smoke(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        self.make_candidate(root, manifest)
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(
            root,
            require_ready=False,
            require_installable=True,
        )
        self.assertEqual(errors, [])

    def test_ready_contract_accepts_complete_immutable_identities(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertEqual(errors, [])

    def test_external_acceptance_rejects_short_or_stale_platform_hashes(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        release = "v0.2.0-beta.1"
        manifest_path = root / "releases" / release / "manifest.json"
        qualification_path = root / "releases" / release / "qualification.json"
        acceptance_path = root / "releases" / release / "acceptance" / "composed-external-installation.json"
        manifest = self.load(manifest_path)
        qualification = self.load(qualification_path)
        acceptance = self.load(acceptance_path)
        acceptance["platform_receipts"][1]["sha256"] = "a" * 62
        self.save(acceptance_path, acceptance)
        qualification["composition"]["external_installation_acceptance"]["sha256"] = hashlib.sha256(
            acceptance_path.read_bytes()
        ).hexdigest()
        self.save(qualification_path, qualification)
        manifest["qualification"]["summary_sha256"] = hashlib.sha256(
            qualification_path.read_bytes()
        ).hexdigest()
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertIn(
            "external acceptance platform receipt hashes must match compatibility",
            errors,
        )

    def test_composed_acceptance_subject_identity_fields_must_match(self) -> None:
        cases = (
            (
                "release",
                "v9.9.9",
                "external acceptance receipt release must match manifest release",
            ),
            (
                "status",
                "failed",
                "external acceptance receipt status must be passed",
            ),
            (
                "compatibility_authority",
                "stale-authority",
                "external acceptance receipt compatibility_authority must match manifest",
            ),
            (
                "compatibility_sha256",
                "0" * 64,
                "external acceptance receipt compatibility_sha256 must match manifest",
            ),
        )
        for field, stale_value, expected_error in cases:
            with self.subTest(field=field):
                temporary, root = self.public_draft_copy()
                try:
                    release = "v0.4.2"
                    release_root = root / "releases" / release
                    acceptance_path = (
                        release_root
                        / "acceptance"
                        / "composed-external-installation.json"
                    )
                    qualification_path = release_root / "qualification.json"
                    manifest_path = release_root / "manifest.json"

                    acceptance = self.load(acceptance_path)
                    acceptance[field] = stale_value
                    self.save(acceptance_path, acceptance)

                    qualification = self.load(qualification_path)
                    qualification["composition"][
                        "external_installation_acceptance"
                    ]["sha256"] = hashlib.sha256(
                        acceptance_path.read_bytes()
                    ).hexdigest()
                    self.save(qualification_path, qualification)

                    manifest = self.load(manifest_path)
                    manifest["qualification"]["summary_sha256"] = hashlib.sha256(
                        qualification_path.read_bytes()
                    ).hexdigest()
                    self.save(manifest_path, manifest)

                    _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
                    self.assertIn(expected_error, errors)
                finally:
                    temporary.cleanup()

    def test_ready_contract_rejects_incomplete_publication(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        qualification_path = root / "releases" / "v0.2.0-beta.1" / "qualification.json"
        manifest = self.load(manifest_path)
        qualification = self.load(qualification_path)
        manifest["status"] = "ready"
        manifest["components"]["omp"]["artifact_url"] = None
        manifest["qualification"]["summary_sha256"] = None
        manifest["qualification"]["public_url"] = None
        manifest["qualification"]["external_installation_passed"] = False
        manifest["publication"]["blockers"] = []
        qualification["external_installation_qualified"] = False
        self.save(qualification_path, qualification)
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertIn("installable release requires components.omp.artifact_url", errors)
        self.assertIn("ready release requires qualification.summary_sha256", errors)
        self.assertIn("ready release requires a passing external installation", errors)

    def test_ga_ready_state_sweep_rejects_stale_machine_state(self) -> None:
        cases = (
            (
                "manifest_blockers",
                "manifest.consistency_probe.blockers must be an empty array in ready mode",
            ),
            (
                "compatibility_blockers",
                "compatibility.composition.blockers must be an empty array in ready mode",
            ),
            (
                "qualification_status",
                "qualification.consistency_probe.status must not contain draft or pending in ready mode",
            ),
            (
                "authority_id",
                "compatibility.authority_id must not contain draft or pending in ready mode",
            ),
        )
        for case, expected_error in cases:
            with self.subTest(case=case):
                temporary, root = self.public_draft_copy()
                try:
                    release_root = root / "releases" / "v0.4.2"
                    manifest_path = release_root / "manifest.json"
                    qualification_path = release_root / "qualification.json"
                    compatibility_path = release_root / "compatibility.json"

                    if case == "manifest_blockers":
                        manifest = self.load(manifest_path)
                        manifest["consistency_probe"] = {
                            "blockers": ["unresolved release gate"]
                        }
                        self.save(manifest_path, manifest)
                    elif case == "qualification_status":
                        qualification = self.load(qualification_path)
                        qualification["consistency_probe"] = {
                            "status": "release pending publication"
                        }
                        self.save(qualification_path, qualification)
                        manifest = self.load(manifest_path)
                        manifest["qualification"]["summary_sha256"] = (
                            hashlib.sha256(qualification_path.read_bytes()).hexdigest()
                        )
                        self.save(manifest_path, manifest)
                    else:
                        compatibility = self.load(compatibility_path)
                        if case == "compatibility_blockers":
                            compatibility["composition"]["blockers"] = [
                                "unresolved composition gate"
                            ]
                        else:
                            compatibility["authority_id"] += "-draft"
                        self.save(compatibility_path, compatibility)
                        self.save(root / "compatibility.json", compatibility)

                    _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
                    self.assertIn(expected_error, errors)
                finally:
                    temporary.cleanup()

    def test_ga_ready_lane_set_must_match_qualification_composition(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        release_root = root / "releases" / "v0.4.2"
        qualification_path = release_root / "qualification.json"
        manifest_path = release_root / "manifest.json"
        qualification = self.load(qualification_path)
        native_variants = qualification["composition"]["native_runtime_variants"]
        native_variants["unexpected-windows-native"] = dict(
            native_variants["rtx4090-windows-native"]
        )
        self.save(qualification_path, qualification)
        manifest = self.load(manifest_path)
        manifest["qualification"]["summary_sha256"] = hashlib.sha256(
            qualification_path.read_bytes()
        ).hexdigest()
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertIn(
            "ready components.ninfer_variants ids must exactly match qualification.composition.native_runtime_variants keys",
            errors,
        )

        empty_errors: list[str] = []
        VERIFY_RELEASE.validate_exact_lane_set(
            {"components": {"ninfer_variants": []}},
            {"runtime_variants": []},
            {"composition": {"native_runtime_variants": {}}},
            empty_errors,
        )
        self.assertIn(
            "ready release requires a non-empty components.ninfer_variants id set",
            empty_errors,
        )

    def test_cross_component_model_hash_drift_is_rejected(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        profile_path = root / "profiles" / "qwen38-rtx5090-windows-docker-local.json"
        profile = self.load(profile_path)
        profile["model"]["artifact_sha256"] = "0" * 64
        self.save(profile_path, profile)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("profile and manifest model hashes must match", errors)

    def test_primary_gpu_receipt_bytes_must_match_compatibility(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        receipt_path = root / "releases" / "v0.2.0-beta.1" / "qualification" / "rtx5090.json"
        receipt = self.load(receipt_path)
        receipt["debug_drift"] = True
        self.save(receipt_path, receipt)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn(
            "primary RTX 5090 qualification SHA-256 must match checked-in bytes",
            errors,
        )

    def test_root_and_release_compatibility_copies_must_match(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        root_compatibility = self.load(root / "compatibility.json")
        root_compatibility["authority_id"] += "-drift"
        self.save(root / "compatibility.json", root_compatibility)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn(
            "root and release compatibility authorities must be byte-identical",
            errors,
        )

    def test_product_public_urls_must_bind_immutable_raw_paths(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["qualification"]["public_url"] = (
            "https://github.com/alphastorm/omp-ninfer/releases/latest"
        )
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn(
            "qualification.public_url must bind an immutable product commit and path",
            errors,
        )

    def test_profile_rejects_container_private_loopback_networking(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        profile_path = root / "profiles" / "qwen38-rtx5090-windows-docker-local.json"
        profile = self.load(profile_path)
        profile["server"]["container_network_mode"] = "bridge"
        self.save(profile_path, profile)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("profile: container network mode must be host", errors)

    def test_profile_deployment_identity_must_match_manifest(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        profile_path = root / "profiles" / "qwen38-rtx5090-windows-docker-local.json"
        profile = self.load(profile_path)
        profile["server"]["deployment_profile"] = "qwen38-5090-v0.1.0"
        arguments = profile["server"]["arguments"]
        arguments[arguments.index("--deployment-profile") + 1] = "qwen38-5090-v0.1.0"
        self.save(profile_path, profile)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("profile: deployment_profile must match the manifest", errors)

    def test_release_defaults_to_compatibility_authority(self) -> None:
        self.assertEqual(
            VERIFY_RELEASE.resolve_product_release(ROOT, None),
            "v0.4.2",
        )
        with self.assertRaisesRegex(VERIFY_RELEASE.ContractError, "versioned release"):
            VERIFY_RELEASE.resolve_product_release(ROOT, "../v0.2.0")

    def test_server_arguments_derive_hardware_specific_values(self) -> None:
        profile = self.load(ROOT / "profiles" / "qwen38-rtx5090-windows-docker-local.json")
        profile["omp_provider"]["context_window"] = 65536
        arguments = profile["server"]["arguments"]
        arguments[arguments.index("--max-context") + 1] = "65536"
        arguments[arguments.index("--kv-dtype") + 1] = "int8"
        errors: list[str] = []
        VERIFY_RELEASE.validate_server_arguments(profile, "profile", errors)
        self.assertEqual(errors, [])

        arguments[arguments.index("--max-context") + 1] = "131072"
        VERIFY_RELEASE.validate_server_arguments(profile, "profile", errors)
        self.assertTrue(any("--max-context" in error for error in errors))

    def test_additional_profiles_share_the_release_contract(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        profile_path = root / "profiles" / "qwen38-rtx5090-manual-tunnel.json"
        profile = self.load(profile_path)
        profile["transport"]["runtime_bind_host"] = "0.0.0.0"
        profile["model"]["artifact_sha256"] = "0" * 64
        self.save(profile_path, profile)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn(
            "profiles/qwen38-rtx5090-manual-tunnel.json: runtime endpoint must bind loopback",
            errors,
        )
        self.assertIn(
            "profiles/qwen38-rtx5090-manual-tunnel.json: model hash must match the manifest",
            errors,
        )

    def test_model_url_must_bind_its_recorded_revision(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["components"]["model"]["artifact_url"] = (
            "https://huggingface.co/neroued/Qwen3.8-27B-NInfer/resolve/main/qwen3_8_27b.ninfer"
        )
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("model artifact URL must bind repository, revision, and name", errors)

    def test_omp_distribution_version_must_equal_release_id(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["components"]["omp"]["distribution_version"] = "18.0.5-deadbeef"
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("OMP distribution version must equal release_id", errors)

    def test_v02_requires_the_public_auditable_omp_source_repository(self) -> None:
        self.assertEqual(
            VERIFY_RELEASE.expected_omp_source_repository("v0.2.0-beta.1"),
            "https://github.com/alphastorm/oh-my-pi",
        )
        self.assertEqual(
            VERIFY_RELEASE.expected_omp_source_repository("v0.1.0-beta.1"),
            "https://github.com/alphastorm/omp-monorepo",
        )

    def test_omp_artifact_name_must_bind_version_and_platform(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["components"]["omp"]["artifact_name"] = "omp-macos-arm64.tar.gz"
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn(
            "OMP artifact name must bind release version and primary platform",
            errors,
        )

    def test_candidate_omp_asset_url_must_bind_public_component(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        self.make_candidate(root, manifest)
        manifest["components"]["omp"]["artifact_url"] = (
            "https://github.com/alphastorm/homebrew-omp/releases/download/"
            "omp-18.0.7-cross-platform-preview-5/wrong.tar.gz"
        )
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn(
            "OMP artifact URL must bind the public component tag and artifact name",
            errors,
        )

    def test_candidate_rejects_a_draft_omp_asset(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        self.make_candidate(root, manifest)
        manifest["components"]["omp"]["artifact_published"] = False
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(
            root, require_ready=False, require_installable=True
        )
        self.assertIn(
            "installable release requires a published OMP artifact",
            errors,
        )

    def test_candidate_oci_reference_must_match_manifest_digest(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        self.make_candidate(root, manifest)
        manifest["components"]["ninfer"]["oci_manifest_digest"] = f"sha256:{'f' * 64}"
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("NInfer OCI reference must exactly bind its manifest digest", errors)

    def test_candidate_accepts_the_public_runtime_repository(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        self.make_candidate(root, manifest)
        ninfer = manifest["components"]["ninfer"]
        ninfer["oci_repository"] = "ghcr.io/alphastorm/ninfer-runtime"
        ninfer["oci_reference"] = (
            f"{ninfer['oci_repository']}@{ninfer['oci_manifest_digest']}"
        )
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertNotIn(
            "NInfer OCI reference must exactly bind its manifest digest", errors
        )
        self.assertNotIn(
            "NInfer OCI repository is not an approved public runtime repository", errors
        )

    def test_native_runtime_variant_binds_its_qualification_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = "v0.2.0-beta.1"
            qualification_dir = root / "releases" / release / "qualification"
            qualification_dir.mkdir(parents=True)
            receipt_path = qualification_dir / "rtx3090.json"
            receipt = {
                "status": "passed",
                "beta_qualified": True,
                "identity": {
                    "source_commit": "a" * 40,
                    "server_binary_sha256": "b" * 64,
                    "configuration_sha256": "c" * 64,
                },
                "package": {
                    "sha256": "d" * 64,
                    "sbom_sha256": "f" * 64,
                    "installer_sha256": "4" * 64,
                    "controller_sha256": "5" * 64,
                    "gpu_owner_controller_sha256": "6" * 64,
                    "state_protection_sha256": "7" * 64,
                },
            }
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            variant = {
                "id": "rtx3090-windows-native",
                "status": "qualified",
                "installable": True,
                "repository": "https://github.com/alphastorm/ninfer",
                "release_tag": "v0.2.0-qwen38-3090-beta.1",
                "source_commit": "a" * 40,
                "source_archive_url": (
                    "https://github.com/alphastorm/ninfer/releases/download/"
                    "v0.2.0-qwen38-3090-beta.1/source.tar.gz"
                ),
                "source_archive_sha256": "e" * 64,
                "package_url": (
                    "https://github.com/alphastorm/ninfer/releases/download/"
                    "v0.2.0-qwen38-3090-beta.1/"
                    "ninfer-rtx3090-omp-v0.2.0-windows-x86_64-cuda12.8-rtx3090.tar.gz"
                ),
                "package_name": (
                    "ninfer-rtx3090-omp-v0.2.0-windows-x86_64-"
                    "cuda12.8-rtx3090.tar.gz"
                ),
                "package_sha256": "d" * 64,
                "package_bytes": 1,
                "sbom_url": (
                    "https://github.com/alphastorm/ninfer/releases/download/"
                    "v0.2.0-qwen38-3090-beta.1/package.spdx.json"
                ),
                "sbom_sha256": "f" * 64,
                "installer_url": (
                    "https://github.com/alphastorm/ninfer/releases/download/"
                    "v0.2.0-qwen38-3090-beta.1/Install-Release.ps1"
                ),
                "installer_sha256": "4" * 64,
                "controller_url": (
                    "https://github.com/alphastorm/ninfer/releases/download/"
                    "v0.2.0-qwen38-3090-beta.1/Control-Release.ps1"
                ),
                "controller_sha256": "5" * 64,
                "gpu_owner_controller_url": (
                    "https://github.com/alphastorm/ninfer/releases/download/"
                    "v0.2.0-qwen38-3090-beta.1/Control-GpuOwner.ps1"
                ),
                "gpu_owner_controller_sha256": "6" * 64,
                "state_protection_url": (
                    "https://github.com/alphastorm/ninfer/releases/download/"
                    "v0.2.0-qwen38-3090-beta.1/Protect-StateRoot.ps1"
                ),
                "state_protection_sha256": "7" * 64,
                "server_binary_sha256": "b" * 64,
                "configuration_sha256": "c" * 64,
                "model_artifact_sha256": "1" * 64,
                "maximum_context_tokens": 65536,
                "qualification": {
                    "summary": "qualification/rtx3090.json",
                    "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                    "public_url": (
                        "https://raw.githubusercontent.com/alphastorm/omp-ninfer/"
                        + "2" * 40
                        + "/releases/v0.2.0-beta.1/qualification/rtx3090.json"
                    ),
                },
            }
            compatibility = {
                "runtime_variants": [{
                    "id": variant["id"],
                    "status": "qualified",
                    "installable": True,
                }]
            }
            errors: list[str] = []
            VERIFY_RELEASE.validate_ninfer_variants(
                root, release, [variant], compatibility, "1" * 64, errors
            )
            self.assertEqual(errors, [])

            receipt["status"] = "incomplete"
            receipt["beta_qualified"] = False
            receipt["installable"] = False
            receipt["deferred_gates"] = ["fresh Windows hardware gate"]
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            variant["status"] = "preview"
            variant["installable"] = False
            variant["qualification"]["sha256"] = hashlib.sha256(
                receipt_path.read_bytes()
            ).hexdigest()
            compatibility["runtime_variants"][0]["status"] = "preview"
            compatibility["runtime_variants"][0]["installable"] = False
            errors = []
            VERIFY_RELEASE.validate_ninfer_variants(
                root, release, [variant], compatibility, "1" * 64, errors
            )
            self.assertEqual(errors, [])

            variant["package_sha256"] = "3" * 64
            errors = []
            VERIFY_RELEASE.validate_ninfer_variants(
                root, release, [variant], compatibility, "1" * 64, errors
            )
            self.assertIn(
                "components.ninfer_variants.rtx3090-windows-native qualification package must match",
                errors,
            )

    def test_ga_native_variant_checksum_closure_is_complete(self) -> None:
        prefix = "components.ninfer_variants.rtx4090-windows-native"
        cases = (
            "missing_digest",
            "missing_file",
            "outer_digest_drift",
            "installer_entry_drift",
            "package_entry_drift",
        )
        for case in cases:
            with self.subTest(case=case):
                temporary, root = self.public_draft_copy()
                try:
                    release_root = root / "releases" / "v0.4.2"
                    manifest_path = release_root / "manifest.json"
                    manifest = self.load(manifest_path)
                    variant = next(
                        item
                        for item in manifest["components"]["ninfer_variants"]
                        if item["id"] == "rtx4090-windows-native"
                    )
                    checksums_path = (
                        release_root
                        / "qualification"
                        / "rtx4090-windows-native.SHA256SUMS"
                    )
                    checksums_text = checksums_path.read_text(encoding="utf-8")
                    self.assertNotIn("runtime-source-e4654b5a.tar.gz", checksums_text)

                    if case == "missing_digest":
                        variant.pop("checksums_sha256")
                        expected_error = (
                            f"{prefix}.checksums_sha256 must be a lower-case SHA-256"
                        )
                    elif case == "missing_file":
                        checksums_path.unlink()
                        expected_error = f"{prefix} checksums file must exist"
                    elif case == "outer_digest_drift":
                        variant["checksums_sha256"] = "0" * 64
                        expected_error = (
                            f"{prefix}.checksums_sha256 must match the checksums file"
                        )
                    else:
                        if case == "installer_entry_drift":
                            digest_field = "installer_sha256"
                            filename = "Install-Release.ps1"
                        else:
                            digest_field = "package_sha256"
                            filename = variant["package_name"]
                        original_entry = f"{variant[digest_field]}  {filename}"
                        stale_entry = f"{'0' * 64}  {filename}"
                        mutated_text = checksums_text.replace(
                            original_entry, stale_entry
                        )
                        self.assertNotEqual(mutated_text, checksums_text)
                        checksums_path.write_text(mutated_text, encoding="utf-8")
                        variant["checksums_sha256"] = hashlib.sha256(
                            checksums_path.read_bytes()
                        ).hexdigest()
                        expected_error = (
                            f"{prefix} checksums entry {filename} must match {digest_field}"
                        )

                    self.save(manifest_path, manifest)
                    _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
                    self.assertIn(expected_error, errors)
                    self.assertFalse(
                        any("runtime-source-e4654b5a.tar.gz" in error for error in errors),
                        errors,
                    )
                finally:
                    temporary.cleanup()

        temporary, root = self.public_draft_copy()
        try:
            release_root = root / "releases" / "v0.4.2"
            manifest_path = release_root / "manifest.json"
            manifest = self.load(manifest_path)
            variant = next(
                item
                for item in manifest["components"]["ninfer_variants"]
                if item["id"] == "rtx3090-windows-native"
            )
            checksums_path = (
                release_root
                / "qualification"
                / "rtx3090-windows-native.SHA256SUMS"
            )
            source_filename = variant["source_archive_url"].rsplit("/", 1)[-1]
            checksums_text = checksums_path.read_text(encoding="utf-8")
            original_entry = (
                f"{variant['source_archive_sha256']}  {source_filename}"
            )
            mutated_text = checksums_text.replace(
                original_entry, f"{'0' * 64}  {source_filename}"
            )
            self.assertNotEqual(mutated_text, checksums_text)
            checksums_path.write_text(mutated_text, encoding="utf-8")
            variant["checksums_sha256"] = hashlib.sha256(
                checksums_path.read_bytes()
            ).hexdigest()
            self.save(manifest_path, manifest)

            _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
            self.assertIn(
                "components.ninfer_variants.rtx3090-windows-native checksums entry "
                f"{source_filename} must match source_archive_sha256",
                errors,
            )
        finally:
            temporary.cleanup()

    def test_local_packaging_oci_digest_drift_is_rejected(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["components"]["ninfer"]["oci_manifest_digest"] = f"sha256:{'f' * 64}"
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("local packaging and manifest OCI digests must match", errors)

    def test_private_paths_are_rejected_from_public_receipts(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        qualification_path = root / "releases" / "v0.2.0-beta.1" / "qualification.json"
        qualification = self.load(qualification_path)
        qualification["debug_path"] = "/Users/private/operator-receipt.json"
        self.save(qualification_path, qualification)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertTrue(any("private marker" in error for error in errors), errors)

    def test_private_paths_are_rejected_from_public_brand_sources(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        (root / "BRAND.md").write_text(
            "Regenerate from /Users/private/Desktop/brand.\n", encoding="utf-8"
        )
        assets = root / "assets"
        assets.mkdir()
        (assets / "banner.html").write_text(
            "<p>source: C:\\Users\\private\\banner</p>\n", encoding="utf-8"
        )

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("BRAND.md contains private marker '/Users/'", errors)
        self.assertIn(
            "assets/banner.html contains private marker 'C:\\\\Users\\\\'", errors
        )

    def test_missing_local_documentation_link_is_rejected(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        (root / "README.md").write_text("[missing](docs/not-there.md)\n", encoding="utf-8")

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("README.md has missing local link: docs/not-there.md", errors)


if __name__ == "__main__":
    unittest.main()
