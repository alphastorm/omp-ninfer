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

    def candidate_copy(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        shutil.copytree(ROOT / "releases", root / "releases")
        shutil.copytree(ROOT / "profiles", root / "profiles")
        shutil.copy2(ROOT / "compatibility.json", root / "compatibility.json")
        (root / "docs").mkdir()
        shutil.copy2(ROOT / "docs" / "COMPATIBILITY.md", root / "docs" / "COMPATIBILITY.md")
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
        manifest, errors = VERIFY_RELEASE.validate(ROOT, require_ready=False)
        self.assertEqual(manifest["status"], "ready")
        self.assertEqual(errors, [])

        _, ready_errors = VERIFY_RELEASE.validate(ROOT, require_ready=True)
        self.assertEqual(ready_errors, [])

        _, installable_errors = VERIFY_RELEASE.validate(
            ROOT,
            require_ready=False,
            require_installable=True,
        )
        self.assertEqual(installable_errors, [])

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
        _, errors = VERIFY_RELEASE.validate(ROOT, require_ready=True)
        self.assertEqual(errors, [])

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

    def test_cross_component_model_hash_drift_is_rejected(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        profile_path = root / "profiles" / "qwen38-rtx5090-windows-docker-local.json"
        profile = self.load(profile_path)
        profile["model"]["artifact_sha256"] = "0" * 64
        self.save(profile_path, profile)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("profile and manifest model hashes must match", errors)

    def test_profile_rejects_container_private_loopback_networking(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        profile_path = root / "profiles" / "qwen38-rtx5090-windows-docker-local.json"
        profile = self.load(profile_path)
        profile["server"]["container_network_mode"] = "bridge"
        self.save(profile_path, profile)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("profile: container network mode must be host", errors)

    def test_release_defaults_to_compatibility_authority(self) -> None:
        self.assertEqual(
            VERIFY_RELEASE.resolve_product_release(ROOT, None),
            "v0.2.0-beta.1",
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
                    "v0.2.0-qwen38-3090-beta.1/package.tar.gz"
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
