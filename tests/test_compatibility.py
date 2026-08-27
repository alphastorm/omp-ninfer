from __future__ import annotations

import importlib.util
import json
import unittest
from copy import deepcopy
from pathlib import Path

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
        self.assertTrue(all(profile["status"] == "preview" for profile in authority["profiles"]))
        self.assertTrue(all(profile["acceptance_receipt"] is None for profile in authority["profiles"]))

    def test_runtime_identity_matches_the_release_manifest(self) -> None:
        authority = MODULE.load_authority(ROOT / "compatibility.json")
        manifest = json.loads(
            (ROOT / "releases" / "v0.1.0-beta.1" / "manifest.json").read_text(encoding="utf-8")
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

    def _write(self, value: object) -> Path:
        path = Path(self._testMethodName + ".compatibility.tmp.json")
        self.addCleanup(path.unlink, missing_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main()
