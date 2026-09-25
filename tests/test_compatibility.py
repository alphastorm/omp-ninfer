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
    def upstream_authority(self) -> dict:
        authority = MODULE.load_authority(ROOT / "compatibility.json")
        descriptor = json.loads(
            (ROOT / "tests" / "fixtures" / "upstream-omp-component.json").read_text(encoding="utf-8")
        )
        for profile in authority["profiles"]:
            platform = MODULE.OMP_PROFILE_PLATFORMS[profile["id"]]
            profile["client_distribution"] = descriptor["platforms"][platform]
        return authority

    def test_upstream_raw_binaries_render_download_and_digest(self) -> None:
        authority = MODULE.load_authority(self._write(self.upstream_authority()))
        rendered = MODULE.render(authority)
        for profile in authority["profiles"]:
            client = profile["client_distribution"]
            self.assertIn(
                f"upstream `{client['upstream_tag']}` "
                f"[`{client['asset_name']}`]({client['asset_url']}) "
                f"(sha256 `{client['asset_sha256'][:12]}`)", rendered,
            )

    def test_upstream_profile_rejects_invalid_artifact_identity(self) -> None:
        cases = (
            ("upstream_repository", "https://github.com/alphastorm/oh-my-pi",
             "upstream_repository must be https://github.com/can1357/oh-my-pi"),
            ("source_commit", "a" * 40,
             "source_commit is a fork-only field forbidden for upstream-release"),
            ("qualification_receipt_url", "https://github.com/alphastorm/homebrew-omp/receipt.json",
             "qualification_receipt_url is a fork-only field forbidden for upstream-release"),
            ("binary_sha256", "a" * 64,
             "binary_sha256 must equal asset_sha256 for an upstream raw binary"),
            ("asset_url", "https://github.com/can1357/oh-my-pi/releases/download/v18.2.3/omp-darwin-arm64",
             "asset_url must bind the upstream tag and asset name"),
            ("asset_id", None, "asset_id must be a positive integer"),
            ("release_id", True, "release_id must be a positive integer"),
            ("asset_bytes", 0, "asset_bytes must be a positive integer"),
            ("asset_sha256", "A" * 64, "asset_sha256 must be a lower-case SHA-256"),
            ("published", False, "published must be true"),
            ("upstream_tag", "v18.03.0", "upstream_tag must be a v-prefixed semantic version"),
            ("upstream_commit", "a" * 39, "upstream_commit must be a lower-case 40-character Git commit"),
            ("asset_name", "omp-linux-x64", "asset_name must match darwin-arm64's upstream binary"),
        )
        for key, value, error in cases:
            with self.subTest(field=key):
                authority = self.upstream_authority()
                client = authority["profiles"][0]["client_distribution"]
                if value is None:
                    client.pop(key)
                else:
                    client[key] = value
                with self.assertRaises(ValueError) as raised:
                    MODULE.load_authority(self._write(authority))
                self.assertEqual(str(raised.exception), f"darwin-remote-ssh client_distribution.{error}")

    def test_fork_profile_cannot_declare_a_distribution_kind(self) -> None:
        for kind in (None, "fork", "unsupported"):
            with self.subTest(kind=kind):
                authority = MODULE.load_authority(ROOT / "compatibility.json")
                authority["profiles"][0]["client_distribution"]["distribution_kind"] = kind
                with self.assertRaisesRegex(ValueError, "distribution_kind must be upstream-release"):
                    MODULE.load_authority(self._write(authority))

    def test_authority_renders_the_checked_in_public_matrix(self) -> None:
        authority = MODULE.load_authority(ROOT / "compatibility.json")
        self.assertEqual(
            MODULE.render(authority),
            (ROOT / "docs" / "COMPATIBILITY.md").read_text(encoding="utf-8"),
        )

    def test_bound_acceptance_receipts_match_immutable_public_files(self) -> None:
        authority = MODULE.load_authority(ROOT / "compatibility.json")
        omp = json.loads(
            (
                ROOT / "releases" / authority["product_release"] / "manifest.json"
            ).read_text(encoding="utf-8")
        )["components"]["omp"]
        for profile in authority["profiles"]:
            receipt = profile["acceptance_receipt"]
            if receipt is None:
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
            distribution = profile["client_distribution"]
            self.assertEqual(
                subject["source"],
                {
                    "repository": omp["upstream_repository"],
                    "tag": omp["upstream_tag"],
                    "commit": authority["composition"]["composed_source_commit"],
                    "tree": omp["upstream_tree"],
                },
            )
            self.assertEqual(subject["source"]["commit"], distribution["upstream_commit"])
            self.assertFalse(subject["safety"]["cloud_fallback_observed"])
            self.assertFalse(subject["safety"]["production_omp_activation_performed"])
            self.assertTrue(subject["safety"]["runtime_incumbent_restored"])
            self.assertTrue(distribution["published"])
            self.assertEqual(subject["client"], distribution)
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

    def test_client_unknown_runtime_capability_is_rejected(self) -> None:
        authority = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))
        authority["profiles"][0]["runtime"]["capabilities"].append(
            "process-restart-continuation"
        )
        with self.assertRaises(ValueError):
            MODULE.load_authority(self._write(authority))

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
        invalid["profiles"][0]["acceptance_receipt"] = {
            "url": "https://raw.githubusercontent.com/alphastorm/omp-ninfer/main/receipt.json",
            "sha256": "a" * 64,
        }
        with self.assertRaisesRegex(ValueError, "not immutable"):
            MODULE.load_authority(self._write(invalid))

        invalid = deepcopy(authority)
        invalid["profiles"][1]["acceptance_receipt"] = {
            "url": ("https://raw.githubusercontent.com/alphastorm/omp-ninfer/"
                    + "a" * 40 + "/releases/" + authority["product_release"]
                    + "/acceptance/windows-x64.json"),
            "sha256": "not-a-sha",
        }
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            MODULE.load_authority(self._write(invalid))

    def test_native_runtime_variants_render_and_fail_closed(self) -> None:
        authority = MODULE.load_authority(ROOT / "compatibility.json")
        variants = {item["id"]: item for item in authority["runtime_variants"]}
        manifest = json.loads(
            (ROOT / "releases" / authority["product_release"] / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        components = {item["id"]: item for item in manifest["components"]["ninfer_variants"]}
        self.assertEqual(set(variants), set(components))
        for variant_id, variant in variants.items():
            component = components[variant_id]
            self.assertEqual(variant["status"], "qualified")
            self.assertTrue(variant["installable"])
            for key in (
                "release_tag",
                "source_commit",
                "package_name",
                "package_url",
                "package_sha256",
                "package_bytes",
                "maximum_context_tokens",
            ):
                self.assertEqual(variant[key], component[key], f"{variant_id} {key}")
            self.assertEqual(
                variant["qualification_receipt"]["path"],
                component["qualification"]["summary"],
            )
            self.assertEqual(
                variant["qualification_receipt"]["sha256"],
                hashlib.sha256((ROOT / component["qualification"]["summary"]).read_bytes()).hexdigest(),
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

    def test_historical_beta_matrix_remains_renderable(self) -> None:
        historical_path = ROOT / "releases" / "v0.2.0-beta.1"
        historical = MODULE.load_authority(historical_path / "compatibility.json")
        self.assertEqual(
            MODULE.render(historical),
            (historical_path / "COMPATIBILITY.md").read_text(encoding="utf-8"),
        )

    def test_receipt_urls_must_bind_this_product_release(self) -> None:
        """A receipt path names the release whose evidence it is.

        Without that binding a self-consistent receipt from another release, carrying the same
        client identity, authenticates a qualified profile: the bytes hash correctly and the
        evidence is still the wrong release's.
        """
        authority = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))
        release = authority["product_release"]
        elsewhere = "v0.0.1"
        stale_profile = deepcopy(authority)
        receipt = stale_profile["profiles"][0]["acceptance_receipt"]
        receipt["url"] = receipt["url"].replace(
            f"/releases/{release}/", f"/releases/{elsewhere}/"
        )
        with self.assertRaisesRegex(ValueError, "acceptance receipt URL is not immutable"):
            MODULE.load_authority(self._write(stale_profile))

        stale_variant = deepcopy(authority)
        variant_receipt = stale_variant["runtime_variants"][0]["qualification_receipt"]
        variant_receipt["url"] = variant_receipt["url"].replace(
            f"/releases/{release}/", f"/releases/{elsewhere}/"
        )
        with self.assertRaisesRegex(ValueError, "qualification receipt binding is invalid"):
            MODULE.load_authority(self._write(stale_variant))

    def test_qualified_profile_must_keep_the_core_client_capabilities(self) -> None:
        """An allowlist cannot see a removal: a shorter list is still a subset."""
        authority = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))
        qualified = next(index for index, profile in enumerate(authority["profiles"])
                         if profile["status"] == "qualified")
        for capability in sorted(MODULE.REQUIRED_CLIENT_CAPABILITIES):
            with self.subTest(capability=capability):
                invalid = deepcopy(authority)
                runtime = invalid["profiles"][qualified]["runtime"]
                runtime["capabilities"] = [
                    item for item in runtime["capabilities"] if item != capability
                ]
                with self.assertRaisesRegex(ValueError, "without required capabilities"):
                    MODULE.load_authority(self._write(invalid))
        duplicated = deepcopy(authority)
        capabilities = duplicated["profiles"][qualified]["runtime"]["capabilities"]
        capabilities.append(capabilities[0])
        with self.assertRaisesRegex(ValueError, "capabilities are duplicated"):
            MODULE.load_authority(self._write(duplicated))

    def _write(self, value: object) -> Path:
        path = Path(self._testMethodName + ".compatibility.tmp.json")
        self.addCleanup(path.unlink, missing_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main()
