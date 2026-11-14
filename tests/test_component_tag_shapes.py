"""New component versions bind shapes and immutable artifacts rather than an allowlist."""

from __future__ import annotations

import copy
import importlib.util
import unittest
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("component_tag_shapes", ROOT / "scripts/verify_release.py")
assert SPEC is not None and SPEC.loader is not None
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)
from release_io import atomic_write_json
from render_compatibility import load_authority, runtime_variant_patterns


class ComponentTagShapeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manifest = VERIFY.load_json(ROOT / "releases/v0.19.0/manifest.json")
        self.previous = copy.deepcopy(self.manifest)
        atomic_write_json(self.root / "releases/v0.19.0/manifest.json", self.previous)
        self.manifest["release"] = "v0.20.0"

    def errors(self):
        errors = []
        VERIFY.validate_component_tag_bindings(self.root, self.manifest["release"], self.manifest, errors)
        return errors

    def test_never_bound_future_tag_and_digest_are_accepted_without_a_code_change(self):
        ninfer = self.manifest["components"]["ninfer"]
        tag = "v42.7.3-qwen38-5090-beta.123"
        ninfer["release_tag"] = tag
        ninfer["sbom_url"] = f"https://github.com/alphastorm/ninfer/releases/download/{tag}/runtime.spdx.json"
        source_tag = tag.replace("-beta.", "-source.")
        ninfer["source_archive_url"] = (
            f"https://github.com/alphastorm/ninfer/releases/download/{source_tag}/"
            f"runtime-source-{ninfer['source_commit'][:8]}.tar.gz")
        self.assertEqual(self.errors(), [])

    def test_reusing_a_container_or_native_tag_with_other_bytes_refuses(self):
        self.assertEqual(self.errors(), [])
        for component, field in (
            (self.manifest["components"]["ninfer"], "oci_manifest_digest"),
            (self.manifest["components"]["ninfer_variants"][0], "package_sha256"),
        ):
            with self.subTest(field=field):
                old = component[field]
                component[field] = "sha256:" + "f" * 64 if field.startswith("oci") else "f" * 64
                self.assertTrue(any("rebound" in error for error in self.errors()))
                component[field] = old

    def test_primary_downloads_bind_the_component_or_derived_source_tag(self):
        ninfer = self.manifest["components"]["ninfer"]
        for field in ("sbom_url", "source_archive_url"):
            with self.subTest(field=field):
                old = ninfer[field]
                ninfer[field] = "https://github.com/alphastorm/ninfer/releases/download/unbound/file"
                self.assertTrue(any(field in error for error in self.errors()))
                ninfer[field] = old

    def test_bad_lane_beta_or_extra_suffix_refuses(self):
        for tag in ("v1.0.0-qwen38-4090-beta.1", "v1.0.0-qwen38-5090-beta.0",
                    "v1.0.0-qwen38-5090-beta.01", "v1.0.0-qwen38-5090-beta.1-extra"):
            with self.subTest(tag=tag):
                self.manifest["components"]["ninfer"]["release_tag"] = tag
                self.assertTrue(any("release_tag" in error for error in self.errors()))

    def test_new_native_versions_render_but_historical_expressions_stay_frozen(self):
        authority = VERIFY.load_json(ROOT / "releases/v0.19.0/compatibility.json")
        authority["product_release"] = "v0.20.0"
        for profile in authority["profiles"]:
            profile["product_release"] = "v0.20.0"
            for reference in (profile["gpu_qualification"]["receipt"], profile["acceptance_receipt"]):
                if reference is not None:
                    reference["url"] = reference["url"].replace("/v0.19.0/", "/v0.20.0/")
        for row in authority["runtime_variants"]:
            gpu = row["id"].split("-")[0]
            tag = f"v42.7.3-qwen38-{gpu[3:]}-beta.123"
            package = f"ninfer-{gpu}-native-v42.7.3-beta.123-windows-x86_64-cuda13.3-{gpu}.tar.gz"
            row.update(release_tag=tag, package_name=package,
                       package_url=f"https://github.com/alphastorm/ninfer/releases/download/{tag}/{package}")
            row["qualification_receipt"]["url"] = row["qualification_receipt"]["url"].replace(
                "/v0.19.0/", "/v0.20.0/")
            historical_tag, historical_package = runtime_variant_patterns("v0.19.0", row["id"])
            self.assertIsNone(historical_tag.fullmatch(tag))
            self.assertIsNone(historical_package.fullmatch(package))
        path = self.root / "authority.json"
        atomic_write_json(path, authority)
        self.assertEqual(load_authority(path), authority)

    def test_old_release_keeps_its_original_shape_contract(self):
        self.manifest["release"] = "v0.19.0"
        self.manifest["components"]["ninfer"]["sbom_url"] = "https://example.invalid/legacy.json"
        self.assertEqual(self.errors(), [])


if __name__ == "__main__":
    unittest.main()
