"""Run the real, host-free product tail once, including immutable-evidence refusal probes."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY_SPEC = importlib.util.spec_from_file_location("release_rehearsal_history", ROOT / "tests" / "history.py")
assert HISTORY_SPEC is not None and HISTORY_SPEC.loader is not None
HISTORY = importlib.util.module_from_spec(HISTORY_SPEC)
HISTORY_SPEC.loader.exec_module(HISTORY)
require_commits = HISTORY.require_commits
SPEC = importlib.util.spec_from_file_location("release_rehearsal_test", ROOT / "scripts" / "release.py")
assert SPEC is not None and SPEC.loader is not None
DRIVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER)


class ReleaseRehearsalTests(unittest.TestCase):
    def test_real_carry_all_tail_and_refusal_probes(self) -> None:
        require_commits(root=ROOT)
        source_head = DRIVER.git(ROOT, "rev-parse", "HEAD").strip()
        with tempfile.TemporaryDirectory() as temporary:
            clone = Path(temporary) / "product"
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                result = DRIVER.rehearse(ROOT, keep=clone)
            transcript = output.getvalue()
            self.assertEqual(result, 0, transcript)
            skipped = re.search(r"^rehearsal: skipped: .+$", transcript, re.MULTILINE)
            if skipped is not None:
                # On a release branch the real release is the subject; see the next test.
                self.skipTest(skipped[0])
            self.assertTrue(transcript.endswith("rehearsal: passed\n"), transcript)
            timings = {match[1]: float(match[2]) for match in re.finditer(
                r"^rehearsal: (.+): passed \((\d+\.\d+)s\)$", transcript, re.MULTILINE)}
            for step in ("clone", "plan init", "candidate", "fixtures", "finalize", "ready gate",
                         "status", "negative receipt audit", "negative pinned evidence", "restored gate"):
                self.assertIn(step, timings, transcript)
                self.assertGreaterEqual(timings[step], 0)
            self.assertEqual(transcript.count("\tdone\t"), 8, transcript)
            release = json.loads((clone / "compatibility.json").read_text(encoding="utf-8"))["product_release"]
            records = DRIVER.group_commits(clone, release)
            self.assertEqual(list(records), list(DRIVER.GROUPS))
            self.assertEqual(DRIVER.git(clone, "remote").strip(), "")
            audit_path = f"releases/{release}/qualification/receipt-audit.json"
            staged = json.loads(subprocess.run(
                ["git", "show", f"{records['stage']['commit']}:{audit_path}"],
                cwd=clone, check=True, capture_output=True, text=True, encoding="utf-8").stdout)
            self.assertEqual(staged["status"], "lane-stage")
            qualification = json.loads((clone / "releases" / release / "qualification.json").read_text(encoding="utf-8"))
            audit = clone / audit_path
            self.assertEqual(hashlib.sha256(audit.read_bytes()).hexdigest(),
                             qualification["receipt_audit"]["sha256"])
            manifest = json.loads((clone / "releases" / release / "manifest.json").read_text(encoding="utf-8"))
            summary = clone / "releases" / release / manifest["qualification"]["summary"]
            self.assertEqual(hashlib.sha256(summary.read_bytes()).hexdigest(),
                             manifest["qualification"]["summary_sha256"])
            self.assertEqual(DRIVER.git(clone, "status", "--porcelain").strip(), "")
        self.assertEqual(DRIVER.git(ROOT, "rev-parse", "HEAD").strip(), source_head)
        self.assertEqual(DRIVER.git(ROOT, "status", "--porcelain").strip(), "")

    def test_a_release_in_progress_skips_instead_of_colliding(self) -> None:
        require_commits(root=ROOT)
        with tempfile.TemporaryDirectory() as temporary:
            clone = Path(temporary) / "product"
            subprocess.run(["git", "clone", "--quiet", "--shared", str(ROOT), str(clone)],
                           check=True, capture_output=True)
            ready = DRIVER.latest_ready_manifest(clone)["release"]
            major, minor, _ = map(int, ready[1:].split("."))
            later = f"v{major}.{minor + 1}.0"
            plan = clone / "releases" / later / "plan.json"
            if not plan.parent.exists():
                plan.parent.mkdir(parents=True)
                plan.write_text("{}\n", encoding="utf-8")
                subprocess.run(["git", "add", "--", str(plan)], cwd=clone, check=True, capture_output=True)
                subprocess.run(["git", "-c", "user.name=Release fixture", "-c",
                                "user.email=release@example.invalid", "-c", "commit.gpgsign=false",
                                "commit", "--quiet", "-m", f"chore(release): plan {later}"],
                               cwd=clone, check=True, capture_output=True)
            head = DRIVER.git(clone, "rev-parse", "HEAD").strip()
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                result = DRIVER.rehearse(clone)
            transcript = output.getvalue()
            self.assertEqual(result, 0, transcript)
            self.assertIn(f"rehearsal: skipped: release {later} is in progress", transcript)
            self.assertNotIn("rehearsal: clone", transcript)
            self.assertEqual(DRIVER.git(clone, "rev-parse", "HEAD").strip(), head)
            self.assertEqual(DRIVER.git(clone, "status", "--porcelain").strip(), "")


if __name__ == "__main__":
    unittest.main()
