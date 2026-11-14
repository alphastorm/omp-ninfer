"""Publication notes must have a release title and no unfinished release prose."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_notes_check", ROOT / "scripts/verify_release.py")
assert SPEC is not None and SPEC.loader is not None
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)
from release_io import atomic_write


class ReleaseNotesTests(unittest.TestCase):
    def check(self, text: str | None, release="v0.20.0"):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "releases" / release / "NINFER_RELEASE_NOTES.md"
            if text is not None:
                atomic_write(path, text)
            errors = []
            VERIFY.validate_release_notes(root, release, errors)
            return errors

    def test_missing_title_wrong_release_and_prefix_release_refuse(self):
        for text in (None, "", "NInfer v0.20.0\n", "# NInfer v0.20.1\n", "# NInfer v0.20.01\n"):
            with self.subTest(text=text):
                self.assertTrue(self.check(text))

    def test_unfinished_wording_tokens_and_placeholders_refuse(self):
        for paragraph in ("Draft publication.", "Prepared for publication.", "Unreleased.",
                          "Acceptance is pending.", "<result>", "TBD", "TODO",
                          "__V0200_RUNTIME_RESULT__"):
            with self.subTest(paragraph=paragraph):
                self.assertTrue(self.check(f"# NInfer v0.20.0\n\n{paragraph}\n"))

    def test_claim_free_notes_accept_autolinks_and_fenced_examples(self):
        self.assertEqual(self.check(
            "# NInfer v0.20.0\n\nPublished runtime.\n\n<https://example.invalid/notes>\n\n"
            "```text\npending request\nprepared\n```\n"), [])

    def test_tokens_and_placeholders_in_fences_still_refuse(self):
        for token in ("__V0200_RESULT__", "<result>"):
            self.assertTrue(self.check(f"# NInfer v0.20.0\n\n```text\n{token}\n```\n"))

    def test_historical_gate_does_not_rewrite_old_notes_contract(self):
        self.assertEqual(self.check(None, release="v0.19.0"), [])

    def test_published_notes_calibrate_the_new_rule_without_retroactive_enforcement(self):
        release = "v0.19.0"
        path = ROOT / "releases" / release / "NINFER_RELEASE_NOTES.md"
        errors = VERIFY.release_notes_errors(path.read_text(encoding="utf-8"), release, path.name)
        # Historical prose describes a prepared export and a save that can stay pending.
        # The new vocabulary is intentionally not imposed on those published bytes.
        self.assertEqual(len(errors), 2, errors)
        self.assertTrue(any("'prepared'" in error for error in errors), errors)
        self.assertTrue(any("'pending'" in error for error in errors), errors)
        current_errors = []
        VERIFY.validate_release_notes(ROOT, release, current_errors)
        self.assertEqual(current_errors, [])


if __name__ == "__main__":
    unittest.main()
