"""Byte-exact public-history replay of the published release pin chain."""

from __future__ import annotations

import importlib.util
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
            subprocess.run(["git", "clone", "--quiet", "--shared", "--no-checkout",
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


if __name__ == "__main__":
    unittest.main()
