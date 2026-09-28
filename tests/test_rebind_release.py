from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CURRENT = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))["product_release"]
# The fields verify_release checks against the manifest's OMP component in a root profile.
ARCHIVE_KEYS = ("component_release_tag", "asset_url", "asset_sha256", "binary_sha256")


class PromoteRootTests(unittest.TestCase):
    @staticmethod
    def load(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def promotion_copy(self) -> tuple[Path, Any]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        shutil.copytree(ROOT / "profiles", root / "profiles")
        shutil.copytree(ROOT / "examples" / "manual-tunnel", root / "examples" / "manual-tunnel")
        shutil.copytree(ROOT / "releases" / CURRENT, root / "releases" / CURRENT)
        (root / "scripts").mkdir()
        shutil.copy2(ROOT / "scripts" / "rebind_release.py", root / "scripts" / "rebind_release.py")
        # Loaded from the copy, so the module's ROOT is the temporary tree.
        spec = importlib.util.spec_from_file_location("rebind_release_copy",
                                                      root / "scripts" / "rebind_release.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return root, module

    def test_lane_stage_repins_profile_client_archives_to_the_manifest_client(self) -> None:
        """v0.8.4 moved the client from OMP 18.3.0 to 18.3.5; the lane stage promoted the
        release into the root profiles but left the Windows profile's archive on 18.3.0."""
        upstream = {"distribution_kind": "upstream-release",
                    "artifact_url": "https://github.com/can1357/oh-my-pi/releases/download/"
                                    "v99.0.0/omp-windows-x64.exe",
                    "artifact_sha256": "a" * 64, "binary_sha256": "b" * 64}
        fork = {"component_release_tag": "omp-99.0.0-cross-platform-beta-1",
                "artifact_url": "https://github.com/alphastorm/homebrew-omp/releases/download/"
                                "omp-99.0.0-cross-platform-beta-1/omp-99.0.0-windows-x64.tar.gz",
                "artifact_sha256": "c" * 64, "binary_sha256": "d" * 64}
        for kind, client in (("upstream", upstream), ("fork", fork)):
            with self.subTest(kind=kind):
                root, module = self.promotion_copy()
                manifest_path = root / "releases" / CURRENT / "manifest.json"
                manifest = self.load(manifest_path)
                omp = manifest["components"]["omp"]
                if kind == "fork":
                    omp.pop("distribution_kind", None)
                omp.update(client)
                manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
                before = {path.name: self.load(path) for path in (root / "profiles").glob("*.json")}

                module.promote_root(CURRENT, manifest_path)

                pinned = 0
                for path in sorted((root / "profiles").glob("*.json")):
                    previous = before[path.name].get("client", {})
                    current = self.load(path).get("client", {})
                    if not any(key in previous for key in ARCHIVE_KEYS):
                        self.assertEqual(current, previous, path.name)
                        continue
                    pinned += 1
                    expected = copy.deepcopy(previous)
                    expected.pop("component_release_tag", None)
                    expected.update(asset_url=client["artifact_url"],
                                    asset_sha256=client["artifact_sha256"],
                                    binary_sha256=client["binary_sha256"])
                    if kind == "fork":
                        expected["component_release_tag"] = client["component_release_tag"]
                    self.assertEqual(current, expected, path.name)
                self.assertGreater(pinned, 0, "no root profile pins a client archive")


if __name__ == "__main__":
    unittest.main()
