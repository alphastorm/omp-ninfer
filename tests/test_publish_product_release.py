"""The product publication command refuses a rehearsal flag combined with the live flag."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/hosts/publish-product-release.sh"


@unittest.skipIf(os.name == "nt", "POSIX shell fixture")
class PublishArgumentTests(unittest.TestCase):
    def test_dry_run_with_publish_is_refused_before_git_or_gh_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory)
            marker = fake / "called"
            for tool in ("git", "gh"):
                stub = fake / tool
                stub.write_text(f"#!/bin/sh\necho {tool} >> '{marker}'\nexit 1\n")
                stub.chmod(0o755)
            result = subprocess.run(
                ["bash", str(SCRIPT), "--release", "v9.9.9", "--commit", "a" * 40, "--pr", "1",
                 "--dry-run", "--publish"],
                capture_output=True, text=True, env=dict(os.environ, PATH=f"{fake}:/usr/bin:/bin"))
            self.assertEqual(result.returncode, 2)
            self.assertIn("choose --dry-run or --publish", result.stderr)
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
