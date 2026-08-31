from __future__ import annotations

import importlib.util
import hashlib
import json
import unittest
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "render_compatibility", ROOT / "scripts" / "render_compatibility.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CompatibilityAuthorityTests(unittest.TestCase):
    def test_authority_renders_the_checked_in_public_matrix(self) -> None:
        authority = MODULE.load_authority(ROOT / "compatibility.json")
        rendered = MODULE.render(authority)
        self.assertEqual(
            rendered,
            (ROOT / "docs" / "COMPATIBILITY.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            [profile["id"] for profile in authority["profiles"]],
            [
                "darwin-remote-ssh",
                "windows-docker-local",
                "linux-docker-local",
            ],
        )
        self.assertTrue(
            all(profile["status"] in MODULE.STATUSES for profile in authority["profiles"])
        )
        self.assertEqual(authority["product_release"], "v0.4.5")
        receipt_sha = hashlib.sha256(
            (ROOT / "releases" / "v0.4.5" / "qualification" / "rtx5090.json").read_bytes()
        ).hexdigest()
        self.assertTrue(
            all(
                profile["gpu_qualification"]["status"] == "qualified"
                and profile["gpu_qualification"]["receipt"]["sha256"] == receipt_sha
                for profile in authority["profiles"]
            )
        )
        self.assertTrue(
            all(
                profile["runtime"]["image_reference"]
                == "ghcr.io/alphastorm/ninfer-runtime@sha256:546bb6a8230ca52cdeaaf7ecd29f64ece38a18db3c430fc622af7285618a4d57"
                and profile["runtime"]["image_digest"]
                == "sha256:546bb6a8230ca52cdeaaf7ecd29f64ece38a18db3c430fc622af7285618a4d57"
                for profile in authority["profiles"]
            )
        )
        receipts = {profile["id"]: profile["acceptance_receipt"] for profile in authority["profiles"]}
        self.assertIsNotNone(receipts["darwin-remote-ssh"])
        self.assertIsNotNone(receipts["windows-docker-local"])
        self.assertIsNotNone(receipts["linux-docker-local"])

    def test_bound_acceptance_receipts_match_immutable_public_files(self) -> None:
        authority = MODULE.load_authority(ROOT / "compatibility.json")
        for profile in authority["profiles"]:
            receipt = profile["acceptance_receipt"]
            if receipt is None:
                self.assertIsNone(profile["acceptance_receipt"])
                continue
            filename = Path(urlparse(receipt["url"]).path).name
            url_parts = Path(urlparse(receipt["url"]).path).parts
            receipt_release = url_parts[url_parts.index("releases") + 1]
            path = (
                ROOT
                / "releases"
                / receipt_release
                / "acceptance"
                / filename
            )
            subject = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(subject["kind"], "omp-ninfer-platform-acceptance-receipt")
            self.assertEqual(subject["product_release"], receipt_release)
            self.assertEqual(subject["profile"], profile["id"])
            self.assertEqual(subject["status"], "passed")
            self.assertEqual(
                subject["source"]["commit"], authority["composition"]["composed_source_commit"]
            )
            self.assertEqual(
                subject["source"]["main_commit"], authority["composition"]["lifecycle_main_commit"]
            )
            self.assertEqual(
                subject["source"]["main_tree"], authority["composition"]["lifecycle_main_tree"]
            )
            self.assertFalse(subject["safety"]["cloud_fallback_observed"])
            self.assertFalse(subject["safety"]["production_omp_activation_performed"])
            self.assertTrue(subject["safety"]["runtime_incumbent_restored"])
            if profile["id"] == "windows-docker-local":
                self.assertEqual(
                    subject["live_acceptance"]["runtime_variant"],
                    "historical-rtx3090-protocol-endpoint",
                )
                self.assertFalse(subject["live_acceptance"]["runtime_identity_bound"])
                self.assertFalse(
                    subject["live_acceptance"]["profile_runtime_qualified_by_this_receipt"]
                )
            distribution = profile["client_distribution"]
            self.assertTrue(distribution["published"])
            self.assertEqual(subject["client"]["archive_sha256"], distribution["archive_sha256"])
            self.assertEqual(subject["client"]["binary_sha256"], distribution["binary_sha256"])
            self.assertEqual(subject["client"]["component_release_tag"], distribution["release_tag"])
            self.assertEqual(subject["client"]["component_release_id"], distribution["release_id"])
            self.assertEqual(subject["client"]["asset_id"], distribution["asset_id"])
            self.assertEqual(subject["client"]["asset_url"], distribution["asset_url"])
            self.assertTrue(
                receipt["url"].endswith(
                    f"/releases/{receipt_release}/acceptance/{filename}"
                )
            )
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), receipt["sha256"])

    def test_runtime_identity_matches_the_release_manifest(self) -> None:
        authority = MODULE.load_authority(ROOT / "compatibility.json")
        manifest = json.loads(
            (
                ROOT / "releases" / authority["product_release"] / "manifest.json"
            ).read_text(encoding="utf-8")
        )
        expected = {
            "image_reference": manifest["components"]["ninfer"]["oci_reference"],
            "model_sha256": manifest["components"]["model"]["artifact_sha256"],
            "configuration_sha256": manifest["runtime_identity"]["configuration_sha256"],
            "server_binary_sha256": manifest["components"]["ninfer"]["server_binary_sha256"],
        }
        for profile in authority["profiles"]:
            for key, value in expected.items():
                self.assertEqual(profile["runtime"][key], value)

    def test_primary_rtx5090_profiles_do_not_claim_process_restart(self) -> None:
        authority = MODULE.load_authority(ROOT / "compatibility.json")
        for profile in authority["profiles"]:
            self.assertNotIn(
                "process-restart-continuation",
                profile["runtime"]["capabilities"],
            )

        for filename in (
            "qwen38-rtx5090-manual-tunnel.json",
            "qwen38-rtx5090-windows-docker-local.json",
        ):
            profile = json.loads((ROOT / "profiles" / filename).read_text(encoding="utf-8"))
            self.assertNotIn("process-restart-continuation", profile["capabilities"])
            self.assertIn("process-restart-continuation", profile["unsupported"])

    def test_unknown_or_incomplete_profiles_fail_closed(self) -> None:
        authority = MODULE.load_authority(ROOT / "compatibility.json")
        invalid = deepcopy(authority)
        invalid["profiles"][0]["status"] = "experimental"
        with self.assertRaisesRegex(ValueError, "status"):
            MODULE.load_authority(self._write(invalid))

        invalid = deepcopy(authority)
        invalid["profiles"][1]["commands"].append("repair")
        with self.assertRaisesRegex(ValueError, "unknown command"):
            MODULE.load_authority(self._write(invalid))

        invalid = deepcopy(authority)
        invalid["profiles"][2]["silent_cloud_fallback"] = True
        with self.assertRaisesRegex(ValueError, "silent cloud fallback"):
            MODULE.load_authority(self._write(invalid))

        invalid = deepcopy(authority)
        invalid["profiles"][0]["lifecycle"]["script_url"] = invalid["profiles"][0][
            "lifecycle"
        ]["script_url"].replace(
            invalid["composition"]["ninfer_lifecycle_source_commit"], "f" * 40
        )
        with self.assertRaisesRegex(ValueError, "lifecycle script"):
            MODULE.load_authority(self._write(invalid))

        invalid = deepcopy(authority)
        invalid["profiles"][0]["gpu_qualification"] = {
            "profile": "qwen38-5090-v0.3.0",
            "status": "qualified",
            "receipt": {
                "url": (
                    "https://github.com/alphastorm/omp-ninfer/releases/download/"
                    "v0.3.0/future-receipt.json"
                ),
                "sha256": "a" * 64,
            },
        }
        with self.assertRaisesRegex(ValueError, "GPU qualification receipt URL"):
            MODULE.load_authority(self._write(invalid))

        invalid = deepcopy(authority)
        invalid["profiles"][0]["acceptance_receipt"]["url"] = (
            "https://raw.githubusercontent.com/alphastorm/omp-ninfer/main/receipt.json"
        )
        with self.assertRaisesRegex(ValueError, "not immutable"):
            MODULE.load_authority(self._write(invalid))

        invalid = deepcopy(authority)
        invalid["profiles"][1]["acceptance_receipt"]["sha256"] = "not-a-sha"
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            MODULE.load_authority(self._write(invalid))

    def test_native_runtime_variants_render_and_fail_closed(self) -> None:
        authority = MODULE.load_authority(ROOT / "compatibility.json")
        variants = {item["id"]: item for item in authority["runtime_variants"]}
        rtx3090 = variants["rtx3090-windows-native"]
        self.assertEqual(rtx3090["status"], "qualified")
        self.assertTrue(rtx3090["installable"])
        self.assertEqual(rtx3090["release_tag"], "v0.2.2-qwen38-3090-beta.1")
        self.assertEqual(
            rtx3090["package_name"],
            "ninfer-rtx3090-omp-v0.2.2-beta.1-windows-x86_64-"
            "cuda13.3-rtx3090.tar.gz",
        )
        self.assertEqual(
            rtx3090["package_sha256"],
            "57652260531a391f1a443437c200657ef90e85e322e078f6c7cb6e47682f5aa1",
        )
        self.assertEqual(rtx3090["package_bytes"], 573249238)
        self.assertEqual(
            rtx3090["qualification_receipt"]["path"],
            "releases/v0.4.5/qualification/rtx3090.json",
        )
        self.assertEqual(
            rtx3090["package_url"],
            "https://github.com/alphastorm/ninfer/releases/download/v0.2.2-qwen38-3090-beta.1/"
            "ninfer-rtx3090-omp-v0.2.2-beta.1-windows-x86_64-cuda13.3-rtx3090.tar.gz",
        )
        self.assertEqual(
            variants["rtx4090-windows-native"]["release_tag"],
            "v0.2.0-qwen38-4090-beta.1",
        )
        variant = {
            "id": "rtx3090-windows-native",
            "status": "qualified",
            "platform": "Windows 11 x64",
            "gpu": "NVIDIA GeForce RTX 3090",
            "cuda_architecture": "sm_86",
            "maximum_context_tokens": 65536,
            "installation_mode": "native-windows-package",
            "installable": True,
            "silent_cloud_fallback": False,
            "qualification_receipt": {
                "url": (
                    "https://raw.githubusercontent.com/alphastorm/omp-ninfer/"
                    + "a" * 40
                    + f"/releases/{authority['product_release']}/qualification/rtx3090.json"
                ),
                "sha256": "b" * 64,
            },
        }
        authority["runtime_variants"] = [variant]
        loaded = MODULE.load_authority(self._write(authority))
        self.assertIn("rtx3090-windows-native", MODULE.render(loaded))

        invalid = deepcopy(authority)
        invalid["runtime_variants"][0]["silent_cloud_fallback"] = True
        with self.assertRaisesRegex(ValueError, "silent cloud fallback"):
            MODULE.load_authority(self._write(invalid))

    def test_plain_and_beta_product_versions_remain_renderable(self) -> None:
        current = MODULE.load_authority(ROOT / "compatibility.json")
        self.assertEqual(current["product_release"], "v0.4.5")

        historical_path = ROOT / "releases" / "v0.2.0-beta.1"
        historical = MODULE.load_authority(historical_path / "compatibility.json")
        self.assertEqual(historical["product_release"], "v0.2.0-beta.1")
        self.assertEqual(
            MODULE.render(historical),
            (historical_path / "COMPATIBILITY.md").read_text(encoding="utf-8"),
        )

    def _write(self, value: object) -> Path:
        path = Path(self._testMethodName + ".compatibility.tmp.json")
        self.addCleanup(path.unlink, missing_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main()
