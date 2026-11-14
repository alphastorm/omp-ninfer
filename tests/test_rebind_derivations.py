"""Rebinding derives display identities while preserving contract content and draft roots."""

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

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("rebind_derivations", ROOT / "scripts/rebind_release.py")
assert SPEC is not None and SPEC.loader is not None
REBIND = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REBIND)
from release_plan import latest_ready_manifest

RELEASE = latest_ready_manifest(ROOT)["release"]


class RebindDerivationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for directory in ("scripts", "examples/manual-tunnel", f"releases/{RELEASE}"):
            shutil.copytree(ROOT / directory, self.root / directory,
                            ignore=shutil.ignore_patterns("__pycache__"))
        (self.root / "docs").mkdir()
        self.release = self.root / "releases" / RELEASE
        # A published fixture is one coherent snapshot, even when the live root advances
        # to a candidate or to a client-only, all-carried successor.
        shutil.copytree(self.release / "profiles", self.root / "profiles")
        shutil.copy2(self.release / "compatibility.json", self.root / "compatibility.json")
        shutil.copy2(self.release / "COMPATIBILITY.md", self.root / "docs/COMPATIBILITY.md")
        self.manifest = REBIND.load(self.release / "manifest.json")
        self.authority = REBIND.load(self.release / "compatibility.json")

    def run_rebind(self, *arguments):
        result = subprocess.run(
            [sys.executable, str(self.root / "scripts/rebind_release.py"),
             "--release", RELEASE, *arguments], cwd=self.root, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_draft_and_lane_pin_correct_stale_labels_and_target_tags(self):
        expected_rows = copy.deepcopy(self.authority["runtime_contracts"])
        expected_targets = copy.deepcopy(self.manifest["publication"]["targets"])
        for mode in ("draft", "lane"):
            with self.subTest(mode=mode):
                authority = copy.deepcopy(self.authority)
                authority["runtime_contracts"][0]["lane"] = "RTX 5090 beta.999 container"
                manifest = copy.deepcopy(self.manifest)
                original = manifest["components"]["ninfer"]["release_tag"]
                manifest["publication"]["targets"] = [
                    target.replace(original, "v99.0.0-qwen38-5090-beta.99")
                    for target in expected_targets]
                REBIND.save(self.release / "manifest.json", manifest)
                REBIND.save(self.release / "compatibility.json", authority)
                root_bytes = (self.root / "compatibility.json").read_bytes()
                if mode == "draft":
                    self.run_rebind("--draft")
                    self.assertEqual((self.root / "compatibility.json").read_bytes(), root_bytes)
                else:
                    pin = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                         check=True, capture_output=True, text=True).stdout.strip()
                    self.run_rebind("--pin", pin, "--stage", "lane")
                    self.assertEqual(REBIND.load(self.root / "compatibility.json")[
                        "runtime_contracts"], expected_rows)
                self.assertEqual(REBIND.load(self.release / "compatibility.json")[
                    "runtime_contracts"], expected_rows)
                self.assertEqual(REBIND.load(self.release / "manifest.json")[
                    "publication"]["targets"], expected_targets)

    def test_unknown_missing_duplicate_and_unmatched_rows_refuse(self):
        for case in ("unknown", "missing", "duplicate", "unmatched"):
            with self.subTest(case=case):
                authority = copy.deepcopy(self.authority)
                manifest = copy.deepcopy(self.manifest)
                if case == "unknown":
                    authority["runtime_contracts"][0]["lane"] = "Unrecognised contract"
                elif case == "missing":
                    authority["runtime_contracts"].pop()
                elif case == "duplicate":
                    authority["runtime_contracts"].append(authority["runtime_contracts"][0])
                else:
                    manifest["components"]["ninfer_variants"].pop()
                with self.assertRaises(SystemExit):
                    REBIND.derive_runtime_contract_lanes(authority, manifest, RELEASE)

    def test_upstream_client_refuses_a_fork_target(self):
        self.assertEqual(self.manifest["components"]["omp"]["distribution_kind"], "upstream-release")
        self.manifest["publication"]["targets"].append("Client omp-99.0.0-cross-platform-beta-1")
        with self.assertRaisesRegex(SystemExit, "unbound component tag"):
            REBIND.derive_publication_target_tags(self.manifest)

    def test_published_release_rebind_and_rerun_change_no_byte(self):
        def snapshot():
            return {path.relative_to(self.root).as_posix(): path.read_bytes()
                    for name in ("compatibility.json", "docs", "profiles", f"releases/{RELEASE}")
                    for path in ([self.root / name] if (self.root / name).is_file()
                                 else (self.root / name).rglob("*"))
                    if path.is_file()}
        before = snapshot()
        self.run_rebind()
        self.assertEqual(snapshot(), before)
        self.run_rebind()
        self.assertEqual(snapshot(), before)


if __name__ == "__main__":
    unittest.main()
