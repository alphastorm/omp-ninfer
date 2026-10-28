"""The product publication command refuses malformed arguments before git or gh runs."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/hosts/publish-product-release.sh"
ARGUMENTS = ["--release", "v9.9.9", "--commit", "a" * 40, "--pr", "1"]


@unittest.skipIf(os.name == "nt", "POSIX shell fixture")
class PublishArgumentTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        fake = Path(temporary.name)
        self.marker = fake / "called"
        for tool in ("git", "gh"):
            stub = fake / tool
            stub.write_text(f"#!/bin/sh\necho {tool} >> '{self.marker}'\nexit 1\n")
            stub.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{fake}:/usr/bin:/bin")

    def publish(self, *arguments: str) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(SCRIPT), *arguments], capture_output=True, text=True, env=self.env)

    def test_dry_run_with_publish_is_refused_before_git_or_gh_runs(self) -> None:
        result = self.publish(*ARGUMENTS, "--dry-run", "--publish")
        self.assertEqual(result.returncode, 2)
        self.assertIn("choose --dry-run or --publish", result.stderr)
        self.assertFalse(self.marker.exists())

    def test_value_flag_without_a_value_is_a_usage_error_before_git_or_gh_runs(self) -> None:
        for flag in ("--release", "--commit", "--pr"):
            with self.subTest(flag=flag):
                result = self.publish(*ARGUMENTS, flag)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(f"{flag} requires a value", result.stderr)
                self.assertFalse(self.marker.exists())


if __name__ == "__main__":
    unittest.main()
