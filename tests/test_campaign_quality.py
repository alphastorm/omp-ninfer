"""The variant campaign's quality.sh deletes and rewrites only its own arm's run directory."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/hosts/quality.sh"
URL = "http://127.0.0.1:9/v1"
KEY = "<the campaign's api-key>"


@unittest.skipIf(os.name == "nt", "POSIX shell fixture")
class QualityArgumentTests(unittest.TestCase):
    def campaign(self) -> Path:
        """A campaign root holding one scored run and the qualification corpus. The corpus run and
        its scoring are not under test: each writes what the real script leaves in the run directory."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        scripts = root / "qualification" / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "run_qualification.py").write_text(
            "import pathlib, sys\n"
            "out = pathlib.Path(sys.argv[sys.argv.index('--out') + 1])\n"
            "out.mkdir(parents=True, exist_ok=True)\n"
            "(out / 'run.json').write_text('{}')\n")
        (scripts / "score_qualification.py").write_text(
            "import pathlib, sys\n"
            "(pathlib.Path(sys.argv[sys.argv.index('--run') + 1]) / 'scores.json').write_text('{}')\n")
        (root / "quality" / "incumbent").mkdir(parents=True)
        (root / "quality" / "incumbent" / "scores.json").write_text('{"scored": true}\n')
        (root / "api-key").write_text("0" * 64 + "\n")
        return root

    @staticmethod
    def quality(root: Path, *arguments: str) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(SCRIPT), *arguments], capture_output=True, text=True, timeout=60,
                              env=dict(os.environ, CAMPAIGN_ROOT=str(root)))

    @staticmethod
    def tree(root: Path) -> dict[str, bytes | None]:
        return {str(path.relative_to(root)): path.read_bytes() if path.is_file() else None
                for path in root.rglob("*")}

    def test_an_arm_is_scored_in_its_own_run_directory(self) -> None:
        root = self.campaign()
        completed = self.quality(root, "rtx5090", "candidate-a", "campaign-1", URL, str(root / "api-key"))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue((root / "quality" / "candidate-a" / "scores.json").is_file())
        self.assertEqual((root / "quality" / "incumbent" / "scores.json").read_text(), '{"scored": true}\n')

    def test_missing_empty_or_escaping_arguments_are_refused_before_any_effect(self) -> None:
        """An empty label made the arm's run directory the quality directory itself, so the script
        deleted every scored run before it ran; a label holding a path could name any directory."""
        for arguments in ((), ("rtx5090", "candidate-a"),
                          ("rtx5090", "candidate-a", "campaign-1", URL, KEY, "q38-ninfer", "extra"),
                          ("", "candidate-a", "campaign-1", URL, KEY),
                          ("rtx5090", "candidate-a", "", URL, KEY),
                          ("rtx5090", "", "campaign-1", URL, KEY),
                          ("rtx5090", "..", "campaign-1", URL, KEY),
                          ("rtx5090", "../qualification", "campaign-1", URL, KEY)):
            with self.subTest(arguments=arguments):
                root = self.campaign()
                before = self.tree(root)
                completed = self.quality(root, *(str(root / "api-key") if value == KEY else value
                                                 for value in arguments))
                self.assertEqual(completed.returncode, 2, completed.stderr)
                self.assertEqual(self.tree(root), before)


if __name__ == "__main__":
    unittest.main()
