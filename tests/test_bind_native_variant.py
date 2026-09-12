"""The native-variant binder transcribes published bytes into a manifest, or refuses.

Every field it writes is load-bearing at install time: a wrong hash or a stale URL is exactly the
derived-record drift v0.5.1 had to correct with a whole release.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "bind_native_variant", ROOT / "scripts" / "bind_native_variant.py"
)
assert SPEC is not None and SPEC.loader is not None
BINDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BINDER)

PACKAGE = "ninfer-rtx4090-native-v0.6.1-beta.1-windows-x86_64-cuda13.3-rtx4090.tar.gz"
SOURCE = "ninfer-rtx4090-native-v0.6.1-beta.1-source.tar.gz"
TAG = "v0.6.1-qwen38-4090-beta.1"
DOWNLOAD = f"https://github.com/alphastorm/ninfer/releases/download/{TAG}"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class BindNativeVariantTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.workspace = Path(self.directory.name)
        self.receipt_path = self.workspace / "package-build-receipt.json"
        self.receipt = {
            "artifact_type": "ninfer_windows_package_build_receipt",
            "lane": "rtx4090",
            "patch_stack_sha": "6912a15c0bf4f7e9e12dc44188f1f4f10b95e47b",
            "binaries": {"server_sha256": digest("server")},
            "config_sha256": digest("config"),
            "model_sha256": digest("model"),
            "package": {"filename": PACKAGE, "sha256": digest("package"), "bytes": 573730038},
        }
        self.write_receipt()
        self.checksums_path = self.workspace / "SHA256SUMS"
        self.entries = {
            "Control-GpuOwner.ps1": digest("gpu-owner"),
            "Control-Release.ps1": digest("controller"),
            "Install-Release.ps1": digest("installer"),
            "Protect-StateRoot.ps1": digest("protect"),
            SOURCE: digest("source"),
            f"{PACKAGE.removesuffix('.tar.gz')}.spdx.json": digest("sbom"),
            PACKAGE: digest("package"),
            "package-build-receipt.json": self.receipt_digest,
        }
        self.write_checksums()
        # The binder writes the checked-in checksum copy and reads the lane receipt from the
        # release tree, so point it at a temporary repository root.
        self.release_root = self.workspace / "releases" / "v0.6.6" / "qualification"
        self.release_root.mkdir(parents=True)
        (self.release_root / "rtx4090.json").write_text('{"status": "passed"}', encoding="utf-8")
        BINDER.ROOT = self.workspace
        self.addCleanup(setattr, BINDER, "ROOT", ROOT)
        self.manifest = {
            "components": {
                "ninfer_variants": [
                    {"id": "rtx3090-windows-native", "package_sha256": digest("other")},
                    {"id": "rtx4090-windows-native", "release_tag": "v0.2.3-qwen38-4090-durable.1"},
                ]
            }
        }

    def write_receipt(self) -> None:
        payload = json.dumps(self.receipt, indent=2)
        self.receipt_path.write_text(payload, encoding="utf-8")
        self.receipt_digest = hashlib.sha256(self.receipt_path.read_bytes()).hexdigest()

    def write_checksums(self) -> None:
        self.checksums_path.write_text(
            "".join(f"{value}  {name}\n" for name, value in self.entries.items()), encoding="utf-8"
        )

    def bind(self) -> dict[str, object]:
        return BINDER.bind(
            self.manifest, "rtx4090", TAG, self.checksums_path, self.receipt_path, "v0.6.6"
        )

    def test_binds_every_published_asset_from_the_distribution_set(self) -> None:
        variant = self.bind()
        self.assertEqual(variant["release_tag"], TAG)
        self.assertEqual(variant["package_url"], f"{DOWNLOAD}/{PACKAGE}")
        self.assertEqual(variant["package_sha256"], self.entries[PACKAGE])
        self.assertEqual(variant["package_bytes"], 573730038)
        self.assertEqual(variant["source_archive_url"], f"{DOWNLOAD}/{SOURCE}")
        self.assertEqual(variant["source_archive_sha256"], self.entries[SOURCE])
        self.assertEqual(variant["installer_sha256"], self.entries["Install-Release.ps1"])
        self.assertEqual(variant["controller_url"], f"{DOWNLOAD}/Control-Release.ps1")
        self.assertEqual(variant["state_protection_sha256"], self.entries["Protect-StateRoot.ps1"])
        self.assertEqual(variant["server_binary_sha256"], self.receipt["binaries"]["server_sha256"])
        self.assertEqual(variant["configuration_sha256"], self.receipt["config_sha256"])
        self.assertEqual(variant["source_commit"], self.receipt["patch_stack_sha"])
        self.assertEqual(
            variant["qualification"]["sha256"],
            hashlib.sha256((self.release_root / "rtx4090.json").read_bytes()).hexdigest(),
        )
        # The sibling lane is untouched: a variant-only release must not disturb the other row.
        other = self.manifest["components"]["ninfer_variants"][0]
        self.assertEqual(other, {"id": "rtx3090-windows-native", "package_sha256": digest("other")})

    def test_binds_the_outer_checksum_set_and_checks_a_copy_into_the_release(self) -> None:
        variant = self.bind()
        checked_in = self.release_root / "rtx4090-windows-native.SHA256SUMS"
        self.assertEqual(checked_in.read_bytes(), self.checksums_path.read_bytes())
        self.assertEqual(variant["checksums_url"], f"{DOWNLOAD}/SHA256SUMS")
        self.assertEqual(
            variant["checksums_sha256"],
            hashlib.sha256(self.checksums_path.read_bytes()).hexdigest(),
        )

    def test_refuses_a_package_hash_the_build_receipt_disputes(self) -> None:
        self.entries[PACKAGE] = digest("tampered")
        self.write_checksums()
        with self.assertRaises(BINDER.BindError) as raised:
            self.bind()
        self.assertIn("package hash disagrees", str(raised.exception))

    def test_refuses_a_distribution_set_missing_a_bound_asset(self) -> None:
        del self.entries["Protect-StateRoot.ps1"]
        self.write_checksums()
        with self.assertRaises(BINDER.BindError) as raised:
            self.bind()
        self.assertIn("Protect-StateRoot.ps1", str(raised.exception))

    def test_refuses_a_receipt_that_is_not_the_one_the_set_lists(self) -> None:
        self.receipt["config_sha256"] = digest("edited-after-publication")
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2), encoding="utf-8")
        with self.assertRaises(BINDER.BindError) as raised:
            self.bind()
        self.assertIn("does not hash to its own checksum entry", str(raised.exception))

    def test_refuses_a_receipt_from_another_lane(self) -> None:
        self.receipt["lane"] = "rtx3090"
        self.write_receipt()
        self.entries["package-build-receipt.json"] = self.receipt_digest
        self.write_checksums()
        with self.assertRaises(BINDER.BindError) as raised:
            self.bind()
        self.assertIn("is not 'rtx4090'", str(raised.exception))

    def test_refuses_a_malformed_checksum_line(self) -> None:
        self.checksums_path.write_text("not-a-checksum  file\n", encoding="utf-8")
        with self.assertRaises(BINDER.BindError) as raised:
            self.bind()
        self.assertIn("malformed checksum line", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
