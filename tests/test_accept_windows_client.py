"""The RTX 5090 Windows client acceptance script checks each native command's exit status
(omp-ninfer#100 item 7). git and py are stubs that record their calls; the named git subcommands
fail."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hosts" / "accept-windows-client.ps1"


@unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed to execute the Windows client script")
@unittest.skipIf(os.name == "nt", "the native command stubs are POSIX shell scripts")
class WindowsClientNativeCommandTests(unittest.TestCase):
    CANDIDATE = "1" * 40

    def preflight(self, root: Path, failing: set[str]) -> tuple[list[str], str]:
        stubs = root / "bin"
        stubs.mkdir()
        calls = root / "calls.txt"
        effects = {"rev-parse": f"echo {self.CANDIDATE}"}
        cases = "".join(f"  {name}) {'exit 128' if name in failing else effects.get(name, ':')} ;;\n"
                        for name in ("rev-parse", "status"))
        (stubs / "git").write_text(f"#!/bin/sh\n[ \"$1\" = -C ] && shift 2\n"
                                   f"echo \"git $1\" >> '{calls}'\ncase \"$1\" in\n{cases}esac\n")
        (stubs / "py").write_text(f"#!/bin/sh\necho py >> '{calls}'\n")
        for stub in stubs.iterdir():
            stub.chmod(0o755)
        workspace = root / "workspace"
        (workspace / "candidate").mkdir(parents=True)
        completed = subprocess.run(
            [shutil.which("pwsh"), "-NoProfile", "-File", str(SCRIPT), "-Action", "Preflight",
             "-Workspace", str(workspace), "-Release", "v0.14.0", "-Candidate", self.CANDIDATE,
             "-ControlRoot", str(root / "control"), "-ModelId", "q38-ninfer"],
            cwd=root, capture_output=True, text=True, timeout=60,
            env=dict(os.environ, PATH=f"{stubs}{os.pathsep}{os.environ['PATH']}"))
        return (calls.read_text().splitlines() if calls.exists() else []), completed.stdout + completed.stderr

    def test_an_unreadable_candidate_clone_is_not_read_as_clean(self) -> None:
        """A failed `git status --porcelain` prints nothing, which read as a clean candidate clone."""
        for failing, expected in ((set(), ["git rev-parse", "git status", "py"]),
                                  ({"status"}, ["git rev-parse", "git status"])):
            with self.subTest(failing=sorted(failing)), tempfile.TemporaryDirectory() as temporary:
                ran, output = self.preflight(Path(temporary), failing)
                self.assertEqual(ran, expected, output)


if __name__ == "__main__":
    unittest.main()
