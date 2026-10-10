from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import subprocess
import sys
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
        shutil.copytree(ROOT / "scripts", root / "scripts")
        # Loaded from the copy, so the module's ROOT is the temporary tree.
        spec = importlib.util.spec_from_file_location("rebind_release_copy",
                                                      root / "scripts" / "rebind_release.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return root, module

    def test_split_model_rebind_keeps_primary_profiles_and_native_rows_separate(self) -> None:
        root, module = self.promotion_copy()
        release = root / "releases" / CURRENT
        manifest_path = release / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["components"]["native_model"] = manifest["components"]["model"]
        model = self.load(ROOT / "tests/fixtures/dflash2-model.json")
        manifest["components"]["model"] = model
        module.save(manifest_path, manifest)
        module.bind_lane_receipts(CURRENT, release / "compatibility.json", manifest_path,
                                  release / "qualification.json")
        authority = self.load(release / "compatibility.json")
        for profile in authority["profiles"]:
            self.assertEqual(profile["runtime"]["model_sha256"], model["artifact_sha256"])
            self.assertEqual(profile["runtime"]["model_bytes"], model["artifact_bytes"])
            self.assertEqual(profile["runtime"]["model_url"], model["artifact_url"])
        native = manifest["components"]["native_model"]
        for variant in authority["runtime_variants"]:
            self.assertEqual(variant["model_sha256"], native["artifact_sha256"])
            self.assertEqual(variant["model_bytes"], native["artifact_bytes"])
            self.assertEqual(variant["model_url"], native["artifact_url"])
        module.promote_root(CURRENT, manifest_path)
        for path in (root / "profiles").glob("*.json"):
            profile = self.load(path)
            self.assertEqual(profile["model"]["artifact_sha256"], model["artifact_sha256"])
            self.assertEqual(profile["model"]["artifact_bytes"], model["artifact_bytes"])
            arguments = profile["server"]["arguments"]
            self.assertEqual(arguments[arguments.index("--artifact-sha256") + 1], model["artifact_sha256"])

    def test_lane_stage_repins_profile_client_archives_to_the_manifest_client(self) -> None:
        """v0.8.4 moved the client from OMP 18.3.0 to 18.3.5; the lane stage promoted the
        release into the root profiles but left the Windows profile's archive on 18.3.0."""
        fork = {"component_release_tag": "omp-99.0.0-cross-platform-beta-1",
                "artifact_url": "https://github.com/alphastorm/homebrew-omp/releases/download/"
                                "omp-99.0.0-cross-platform-beta-1/omp-99.0.0-windows-x64.tar.gz",
                "artifact_sha256": "c" * 64, "binary_sha256": "d" * 64}
        root, module = self.promotion_copy()
        manifest_path = root / "releases" / CURRENT / "manifest.json"
        manifest = self.load(manifest_path)
        omp = manifest["components"]["omp"]
        omp.pop("distribution_kind", None)
        omp.update(fork)
        module.save(manifest_path, manifest)
        for path in (root / "profiles").glob("*.json"):
            profile = self.load(path)
            profile["status"] = "candidate"
            module.save(path, profile)
        before = {path.name: self.load(path) for path in (root / "profiles").glob("*.json")}

        module.promote_root(CURRENT, manifest_path)

        pinned = 0
        for path in sorted((root / "profiles").glob("*.json")):
            previous = before[path.name].get("client", {})
            profile = self.load(path)
            self.assertEqual(profile["status"], "candidate", path.name)
            current = profile.get("client", {})
            if not any(key in previous for key in ARCHIVE_KEYS):
                self.assertEqual(current, previous, path.name)
                continue
            pinned += 1
            expected = copy.deepcopy(previous)
            expected.update(component_release_tag=fork["component_release_tag"],
                            asset_url=fork["artifact_url"],
                            asset_sha256=fork["artifact_sha256"],
                            binary_sha256=fork["binary_sha256"])
            self.assertEqual(current, expected, path.name)
        self.assertGreater(pinned, 0, "no root profile pins a client archive")

    def test_upstream_lane_stage_uses_each_platform_distribution(self) -> None:
        root, module = self.promotion_copy()
        release = root / "releases" / CURRENT
        manifest_path = release / "manifest.json"
        descriptor = self.load(ROOT / "tests/fixtures/upstream-omp-component.json")
        manifest = self.load(manifest_path)
        manifest["components"]["omp"] = descriptor["omp"]
        module.save(manifest_path, manifest)
        authority_path = release / "compatibility.json"
        authority = self.load(authority_path)
        platforms = {"darwin-remote-ssh": "darwin-arm64",
                     "windows-docker-local": "windows-x64",
                     "linux-docker-local": "linux-x64"}
        for profile in authority["profiles"]:
            profile["client_distribution"] = descriptor["platforms"][platforms[profile["id"]]]
        module.save(authority_path, authority)

        module.promote_root(CURRENT, manifest_path)

        modes = {"manual-ssh-tunnel": "darwin-arm64",
                 "native-windows-docker-local": "windows-x64"}
        for path in (root / "profiles").glob("*.json"):
            profile = self.load(path)
            expected = descriptor["platforms"][modes[profile["installation_mode"]]]
            self.assertEqual(profile["client"], expected, path.name)
            self.assertNotIn("component_release_tag", profile["client"], path.name)

    def test_upstream_promotion_consumes_only_the_bound_client_candidate_marker(self) -> None:
        root, module = self.promotion_copy()
        release_name = "v0.11.0"
        release = root / "releases" / release_name
        if release_name != CURRENT:
            shutil.copytree(ROOT / "releases" / release_name, release)
        shutil.copytree(ROOT / "docs" / "measurements", root / "docs" / "measurements")
        shutil.copy2(release / "COMPATIBILITY.md", root / "docs" / "COMPATIBILITY.md")
        shutil.copy2(release / "compatibility.json", root / "compatibility.json")
        for name in ("QUICKSTART.md", "SECURITY.md"):
            (root / "docs" / name).write_text("# Test fixture\n", encoding="utf-8")
        manifest_path = release / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["status"] = "candidate"
        # This control starts before acceptance, even after the live root becomes ready.
        manifest["publication"]["blockers"] = ["external-installation acceptance has not been performed"]
        manifest["publication"]["external_installation_qualified"] = False
        manifest["qualification"]["external_installation_passed"] = False
        qualification_path = release / "qualification.json"
        qualification = self.load(qualification_path)
        qualification["external_installation_qualified"] = False
        qualification["composition"]["external_installation_acceptance"] = {"status": "pending"}
        qualification["remaining_release_gates"] = ["Published-component external-installation acceptance"]
        module.save(qualification_path, qualification)
        manifest["qualification"]["summary_sha256"] = module.sha256(qualification_path)
        module.save(manifest_path, manifest)
        for path in (root / "profiles").glob("*.json"):
            profile = self.load(path)
            profile["status"] = "candidate"
            module.save(path, profile)

        command = [sys.executable, str(root / "scripts" / "verify_release.py"),
                   "--release", release_name, "--require-installable", "--json"]
        before = subprocess.run(command, cwd=root, capture_output=True, text=True)
        self.assertNotEqual(before.returncode, 0)
        self.assertTrue(any("unqualified client candidate" in error
                            for error in json.loads(before.stdout)["errors"]))

        module.promote_root(release_name, manifest_path)

        after = subprocess.run(command, cwd=root, capture_output=True, text=True)
        self.assertEqual(after.returncode, 0, after.stdout + after.stderr)
        self.assertEqual(self.load(manifest_path)["status"], "candidate")
        self.assertFalse(self.load(manifest_path)["qualification"]["external_installation_passed"])
        self.assertTrue(self.load(manifest_path)["publication"]["blockers"])
        for path in (root / "profiles").glob("*.json"):
            profile = self.load(path)
            self.assertNotIn("status", profile)
            self.assertEqual(profile["release"], release_name)

    def test_lane_stage_makes_a_draft_manifest_a_candidate_and_keeps_later_states(self) -> None:
        """The cut must leave a manifest that route acceptance can install. v0.8.5's and
        v0.8.6's cuts left the draft status in place, and the RTX 4090 route's preflight
        refused the v0.8.6 candidate as not installable."""
        for before, after in (("draft", "candidate"), ("candidate", "candidate"), ("ready", "ready")):
            with self.subTest(status=before):
                root, module = self.promotion_copy()
                manifest_path = root / "releases" / CURRENT / "manifest.json"
                manifest = self.load(manifest_path)
                manifest["status"] = before
                manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

                module.promote_root(CURRENT, manifest_path)

                self.assertEqual(self.load(manifest_path)["status"], after)


if __name__ == "__main__":
    unittest.main()
