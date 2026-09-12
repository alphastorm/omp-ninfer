"""The route a release accepts is the route the documentation prints."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import documented_route  # noqa: E402

RUNNER = ROOT / "scripts" / "hosts" / "run-documented-route.sh"


class ExtractionTests(unittest.TestCase):
    def test_every_lane_resolves_to_fenced_blocks_of_its_language(self) -> None:
        for lane in documented_route.LANES:
            with self.subTest(lane=lane):
                resolved = documented_route.lane_blocks(documented_route.DEFAULT_DOC, lane)
                self.assertEqual(len(resolved), len(documented_route.LANES[lane]))
                for step, block in resolved:
                    self.assertEqual(block.language, step.language)
                    self.assertTrue(block.text.strip(), f"{lane}/{step.slug} is empty")

    def test_bundle_files_are_the_documented_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            manifest = documented_route.bundle(documented_route.DEFAULT_DOC, "rtx4090-native", output)
            for step in manifest["steps"]:
                data = (output / step["file"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), step["sha256"])
                block = documented_route.extract(documented_route.DEFAULT_DOC, step["heading"], step["index"])
                self.assertEqual(data.decode("utf-8"), block.text)
            self.assertEqual(
                manifest["document_sha256"],
                hashlib.sha256(documented_route.DEFAULT_DOC.read_bytes()).hexdigest(),
            )

    def test_native_route_steps_carry_the_variables_they_use(self) -> None:
        """A reader pastes the blocks into one window; a later block may only use names an
        earlier one defined. Catches a doc edit that moves a definition below its first use."""
        defined: set[str] = set()
        import re
        for step, block in documented_route.lane_blocks(documented_route.DEFAULT_DOC, "rtx4090-native"):
            used = set(re.findall(r"\$([A-Z][A-Za-z]+)\b", block.text))
            assigned = set(re.findall(r"^\s*\$([A-Z][A-Za-z]+)\s*=", block.text, re.M))
            missing = {name for name in used - assigned - defined if name not in {"Sid", "Rule", "Asset", "Name", "Path", "Applied", "Acl", "Admins", "Secret", "LASTEXITCODE", "HOME"}}
            self.assertFalse(missing, f"{step.slug} uses {sorted(missing)} before any block defines them")
            defined |= assigned

    def test_windows_blocks_stay_within_windows_powershell(self) -> None:
        """The Windows routes run in Windows PowerShell 5.1 on .NET Framework. These calls exist
        only on .NET 5+ and failed the RTX 4090 route on a stock host (EXP-032)."""
        forbidden = ("[Convert]::ToHexString", "RandomNumberGenerator]::Fill(", "[Convert]::FromHexString")
        for block in documented_route.parse_blocks(documented_route.DEFAULT_DOC.read_text(encoding="utf-8")):
            if block.language != "powershell":
                continue
            for call in forbidden:
                self.assertNotIn(call, block.text, f"{block.heading!r} uses {call}, which Windows PowerShell lacks")

    def test_no_block_ends_by_opening_an_interactive_session(self) -> None:
        """A block that launches the OMP TUI cannot be followed by 'run these in the same
        process' and cannot be checked by a reader's shell; interactive launches live in prose,
        blocks stay non-interactive on every platform (EXP-032)."""
        import re
        launch = re.compile(r"(?:^|[\s&;(])(?:omp|\$Launcher|& \"\$env:LOCALAPPDATA\\\\OMP\\\\omp\.cmd\")\s")
        for block in documented_route.parse_blocks(documented_route.DEFAULT_DOC.read_text(encoding="utf-8")):
            if block.language not in ("sh", "powershell"):
                continue
            joined = " ".join(line.strip().rstrip("\\`") for line in block.text.splitlines())
            for command in re.split(r"[;|]|&&|\|\|", joined):
                if "--model" in command and ("omp " in command or "omp.cmd" in command or "$Launcher" in command):
                    self.assertIn(" -p", command, f"{block.heading!r} opens an interactive OMP session inside a block: {command.strip()[:120]}")

    def test_macos_acceptance_blocks_test_their_own_outcome(self) -> None:
        """Every macOS acceptance block ends with a shell test of what the turn produced, so a
        reader (and the runner) gets pass/fail from the shell, not from reading model prose."""
        for step, block in documented_route.lane_blocks(documented_route.DEFAULT_DOC, "rtx5090-macos-client"):
            if step.slug in ("tool", "vision", "resume", "survives-restart"):
                self.assertRegex(block.text, r"(grep -q|test -s)", f"{step.slug} has no shell-checkable outcome")
            if step.slug == "fail-closed":
                self.assertIn("unexpectedly succeeded", block.text)

    def test_variant_blocks_select_the_lane(self) -> None:
        self.assertIn("git clone --branch", documented_route.extract(documented_route.DEFAULT_DOC, "Native Windows RTX 4090 and RTX 3090 release lanes", 0).text)
        self.assertIn("'rtx4090-windows-native'", documented_route.extract(documented_route.DEFAULT_DOC, "Native Windows RTX 4090 and RTX 3090 release lanes", 1).text)
        self.assertIn("'rtx3090-windows-native'", documented_route.extract(documented_route.DEFAULT_DOC, "Native Windows RTX 4090 and RTX 3090 release lanes", 2).text)


class RunnerTests(unittest.TestCase):
    def write_bundle(self, root: Path, steps: list[tuple[str, str]]) -> Path:
        bundle = root / "bundle"
        bundle.mkdir()
        manifest = []
        for position, (slug, body) in enumerate(steps, start=1):
            name = f"{position:02d}-{slug}.sh"
            (bundle / name).write_text(body, encoding="utf-8")
            manifest.append({"position": position, "slug": slug, "file": name, "heading": "H",
                             "index": 0, "language": "sh",
                             "sha256": hashlib.sha256(body.encode()).hexdigest()})
        (bundle / "manifest.json").write_text(json.dumps({
            "lane": "smoke", "document": "doc", "document_sha256": "0" * 64, "steps": manifest}))
        clone = root / "clone"
        clone.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=clone, check=True)
        return bundle

    def run_bundle(self, root: Path, bundle: Path) -> tuple[int, dict]:
        receipt = root / "receipt.json"
        completed = subprocess.run(["bash", str(RUNNER), str(bundle), str(root / "clone"), str(receipt)],
                                   capture_output=True, text=True, check=False)
        return completed.returncode, json.loads(receipt.read_text())

    def test_blocks_share_one_shell_and_the_first_failure_ends_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self.write_bundle(root, [
                ("define", "ROUTE_VAR=carried\n"),
                ("use", 'test "$ROUTE_VAR" = carried\n'),
                ("break", "false\n"),
                ("after", "echo never\n"),
            ])
            code, receipt = self.run_bundle(root, bundle)
            self.assertEqual(code, 1)
            self.assertEqual(receipt["status"], "failed")
            self.assertEqual([s["status"] for s in receipt["steps"]], ["passed", "passed", "failed", "skipped"])
            self.assertIn("exit 1: false", receipt["steps"][2]["error"])

    def test_a_step_that_consumes_stdin_cannot_end_the_run_early(self) -> None:
        """A block that reads stdin or backgrounds a process must not eat the step list;
        a run that executed only some steps is a failure, never a pass (macOS route, EXP-032)."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self.write_bundle(root, [
                ("eats-stdin", "cat >/dev/null\n"),
                ("after", "echo reached > \"$PWD/../after.txt\"\n"),
            ])
            code, receipt = self.run_bundle(root, bundle)
            self.assertEqual(code, 0, receipt)
            self.assertEqual([s["status"] for s in receipt["steps"]], ["passed", "passed"])
            self.assertTrue((root / "after.txt").exists())

    def test_a_step_whose_bytes_drifted_from_the_document_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self.write_bundle(root, [("ok", "true\n"), ("edited", "true\n")])
            (bundle / "02-edited.sh").write_text("true # edited after bundling\n")
            code, receipt = self.run_bundle(root, bundle)
            self.assertEqual(code, 1)
            self.assertEqual(receipt["steps"][1]["status"], "refused")


if __name__ == "__main__":
    unittest.main()
