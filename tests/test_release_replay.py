"""Byte-exact public-history replay of the published release pin chain."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_history", ROOT / "tests/history.py")
assert SPEC is not None and SPEC.loader is not None
HISTORY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HISTORY)
BOUND_PATHS = (
    "compatibility.json", "docs/COMPATIBILITY.md", "profiles", "releases/v0.19.0",
    "examples/manual-tunnel/start-ninfer.sh", "examples/manual-tunnel/stop-ninfer.sh",
)


class HistoryPolicyTests(unittest.TestCase):
    def test_lane_correction_cannot_write_a_callers_live_authority(self):
        for path in (ROOT / "compatibility.json", "../compatibility.json"):
            with self.subTest(path=path), mock.patch.object(HISTORY.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "repository-relative"):
                    HISTORY.corrected_lane_snapshot("a" * 40, path, False)
                run.assert_not_called()

    def test_shallow_history_skips_locally_and_fails_when_required(self):
        result = subprocess.CompletedProcess([], 0, stdout="true\n")
        with mock.patch.object(HISTORY.subprocess, "run", return_value=result):
            with mock.patch.dict(os.environ, {"OMP_NINFER_REQUIRE_HISTORY": "0"}):
                with self.assertRaises(unittest.SkipTest):
                    HISTORY.require_commits()
            with mock.patch.dict(os.environ, {"OMP_NINFER_REQUIRE_HISTORY": "1"}):
                with self.assertRaisesRegex(AssertionError, "full public history"):
                    HISTORY.require_commits()


class ReleasePinReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        references = ("bf2a059", "fc15ffc", "7062952", "e064bd8", "0bc70da",
                      "143a9bc", "57526ad", "v0.19.0")
        cls.commits = dict(zip(references, HISTORY.resolve_commits(*references)))

    def replay(self, before: str, stage: str, after: str) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "replay"
            expected = None
            if stage == "lane":
                expected, pointers = HISTORY.corrected_lane_snapshot(
                    self.commits[after], "compatibility.json", False)
                lane_pointers = {name for name, pointer in pointers if pointer.endswith("/lane")}
                self.assertEqual(lane_pointers,
                                 {"compatibility.json", "releases/v0.19.0/compatibility.json"})
            subprocess.run(["git", "clone", "--quiet", "--config", "core.autocrlf=false",
                            "--shared", "--no-checkout",
                            str(ROOT), str(root)], check=True, capture_output=True)
            subprocess.run(["git", "checkout", "--quiet", "--detach", self.commits[before]],
                           cwd=root, check=True, capture_output=True)
            shutil.copytree(ROOT / "scripts", root / "scripts", dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
            result = subprocess.run(
                [sys.executable, str(root / "scripts/rebind_release.py"), "--release",
                 "v0.19.0", "--pin", self.commits[before], "--stage", stage],
                cwd=root, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            if expected is not None:
                self.assertEqual(HISTORY.release_snapshot(root, "v0.19.0"), expected)
                return
            difference = subprocess.run(
                ["git", "diff", "--exit-code", self.commits[after], "--", *BOUND_PATHS],
                cwd=root, capture_output=True, text=True,
            )
            self.assertEqual(difference.returncode, 0, difference.stdout + difference.stderr)

    def test_lane_pin(self):
        self.replay("bf2a059", "lane", "fc15ffc")

    def test_platform_pin(self):
        self.replay("7062952", "platform", "e064bd8")

    def test_acceptance_pin(self):
        self.replay("e064bd8", "acceptance", "0bc70da")

    def test_manifest_pin(self):
        self.replay("143a9bc", "manifest", "57526ad")

    def test_draft_lane_correction_preserves_the_unpromoted_root(self):
        expected, pointers = HISTORY.corrected_lane_snapshot(
            self.commits["bf2a059"], "releases/v0.19.0/compatibility.json", True)
        lane_pointers = {(name, pointer) for name, pointer in pointers if pointer.endswith("/lane")}
        self.assertEqual(len(lane_pointers), 1)
        self.assertEqual(next(iter(lane_pointers))[0], "releases/v0.19.0/compatibility.json")
        self.assertTrue(all(name.startswith("releases/v0.19.0/") for name, _ in pointers))
        for name, data in expected.items():
            if not name.startswith("releases/v0.19.0/"):
                original = subprocess.run(["git", "show", f"{self.commits['bf2a059']}:{name}"],
                                          cwd=ROOT, capture_output=True, check=True).stdout
                self.assertEqual(data, original, name)
        authority = json.loads(expected["releases/v0.19.0/compatibility.json"])
        published = json.loads(subprocess.run(
            ["git", "show", f"{self.commits['v0.19.0']}:compatibility.json"],
            cwd=ROOT, capture_output=True, check=True,
        ).stdout)
        self.assertEqual(next(row["lane"] for row in authority["runtime_contracts"]
                              if row["lane"].startswith("RTX 3090 ")),
                         next(row["lane"] for row in published["runtime_contracts"]
                              if row["lane"].startswith("RTX 3090 ")))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "draft"
            subprocess.run(["git", "clone", "--quiet", "--config", "core.autocrlf=false",
                            "--shared", "--no-checkout", str(ROOT), str(root)],
                           capture_output=True, check=True)
            subprocess.run(["git", "checkout", "--quiet", "--detach", self.commits["bf2a059"]],
                           cwd=root, capture_output=True, check=True)
            shutil.copytree(ROOT / "scripts", root / "scripts", dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
            result = subprocess.run(
                [sys.executable, str(root / "scripts/rebind_release.py"),
                 "--release", "v0.19.0", "--draft"],
                cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(HISTORY.release_snapshot(root, "v0.19.0"), expected)


if __name__ == "__main__":
    unittest.main()
