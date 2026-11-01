"""Suite jobs need immutable Git objects, not just the candidate's working tree."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ci.yml"


class CiCheckoutTests(unittest.TestCase):
    def test_every_ci_checkout_has_full_history(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        # Match the workflow's step layout, without adding a YAML dependency to the suite.
        checkouts = [step for step in re.split(r"(?m)^      - ", source)
                     if step.startswith("uses: actions/checkout@")]
        self.assertTrue(checkouts, "CI must check out the repository before running suites")
        self.assertEqual(len(checkouts), source.count("actions/checkout@"),
                         "Update the invariant if the checkout step layout changes")
        for number, checkout in enumerate(checkouts, 1):
            with self.subTest(checkout=number):
                self.assertRegex(checkout, r"(?m)^          fetch-depth: 0(?:[ \t]+#.*)?$",
                                 "Every suite-running CI job needs full Git history")

    @unittest.skipUnless(os.environ.get("GITHUB_ACTIONS") == "true", "checks the actual CI checkout")
    def test_running_ci_checkout_is_not_shallow(self) -> None:
        shallow = subprocess.check_output(
            ["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT, text=True
        ).strip()
        self.assertEqual(shallow, "false", "CI suites read immutable guides and evidence from Git history")


if __name__ == "__main__":
    unittest.main()
