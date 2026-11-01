"""Windows PowerShell 5.1 must not strip quotes from native-command payloads."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Keep strings (including here-strings) atomic, and skip comments and continuations.
# This is a lexical check, not a PowerShell interpreter: an unresolved -c argument
# fails closed so a computed payload cannot silently evade the invariant.
TOKENS = re.compile(
    r'''<\#.*?\#>|\#[^\n]*|@'\r?\n.*?^'@|@"\r?\n.*?^"@|'''
    r''''(?:''|[^'])*'|"(?:`.|""|[^"])*"|\$[\w:]+|[=,]|[^\s'"$=,();{}|#`]+''',
    re.MULTILINE | re.DOTALL,
)


def literal(token: str) -> str | None:
    if token.startswith(("@'", '@"')):
        return token[2:-2]
    if token.startswith(("'", '"')):
        return token[1:-1]
    return None


def unsafe_payloads(source: str) -> list[tuple[int, str]]:
    tokens = [token for token in TOKENS.finditer(source)
              if not token.group().startswith(("#", "<#"))]
    assignments: dict[str, str | None] = {}
    failures = []
    for index, token in enumerate(tokens):
        text = token.group()
        if text.startswith("$") and index + 2 < len(tokens) and tokens[index + 1].group() == "=":
            value = tokens[index + 2]
            # Only a whole literal assignment is statically known, not its first term.
            remainder = source[value.end():].split("\n", 1)[0].strip()
            assignments[text.lower()] = literal(value.group()) if not remainder or remainder.startswith((";", "#")) else None
        if (literal(text) or text) != "-c":
            continue
        argument = index + 1
        if argument < len(tokens) and tokens[argument].group() == ",":
            argument += 1  # Native argv arrays, e.g. Invoke-Wsl @('python3', '-c', ...).
        payload = None
        if argument < len(tokens):
            value = tokens[argument].group()
            payload = assignments.get(value.lower()) if value.startswith("$") else literal(value)
        line = source.count("\n", 0, token.start()) + 1
        if payload is None:
            failures.append((line, "-c payload is not a statically known string; use a file or stdin"))
        elif '"' in payload:
            failures.append((line, "-c payload contains a double quote mangled by Windows PowerShell 5.1"))
    return failures


class NativePayloadInvariantTests(unittest.TestCase):
    def test_all_powershell_native_c_payloads_are_double_quote_free(self) -> None:
        failures = [f"{path.relative_to(ROOT)}:{line}: {message}"
                    for path in sorted(ROOT.rglob("*.ps1"))
                    for line, message in unsafe_payloads(path.read_text(encoding="utf-8-sig"))]
        self.assertEqual(failures, [], "\n" + "\n".join(failures))

    def test_scanner_covers_literals_here_strings_variables_and_native_argv_arrays(self) -> None:
        unsafe = (
            "& python -c 'print(\"unsafe\")'",
            '& python -c "print(`"unsafe`")"',
            "$code=@'\nprint(\"unsafe\")\n'@\n& py -3 -c $code",
            '$code=@"\nprint(`"unsafe`")\n"@\n& py -3 -c $code',
            "Invoke-Wsl @('python3', '-c', 'print(\"unsafe\")')",
            "& another-native.exe -c $unknown",
        )
        for source in unsafe:
            with self.subTest(source=source):
                self.assertEqual(len(unsafe_payloads(source)), 1)
        safe = (
            '& python -c "print(\'safe\')"',
            "$code=@'\nprint('safe')\n'@\n& py -3 -c $code",
            "Invoke-Wsl @('bash', '-c', \"echo $value\")",
            "# python -c 'print(\"comment\")'\n& git -C $Clone status",
            "<# python -c 'print(\"comment\")' #>\nWrite-Output 'not a -c payload'",
        )
        for source in safe:
            with self.subTest(source=source):
                self.assertEqual(unsafe_payloads(source), [])

    @unittest.skipUnless(sys.platform == "win32", "requires native Windows PowerShell 5.1")
    def test_candidate_configuration_executes_through_windows_powershell_51(self) -> None:
        powershell = shutil.which("powershell.exe")
        self.assertIsNotNone(powershell, "Windows CI must exercise powershell.exe, not pwsh")
        proof = r'''
param($Source,$Clone,$Release,$Lane)
$ErrorActionPreference='Stop'
if($PSVersionTable.PSVersion.Major -ne 5 -or $PSVersionTable.PSVersion.Minor -ne 1){throw 'requires Windows PowerShell 5.1'}
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
$function=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'CandidateConfiguration'},$false)
. ([scriptblock]::Create($function.Extent.Text))
CandidateConfiguration|ConvertTo-Json -Depth 20 -Compress
'''
        release = json.loads((ROOT / "compatibility.json").read_text())["product_release"]
        sys.path.insert(0, str(ROOT / "scripts"))
        from verify_release import native_profile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            clone = root / "candidate's checkout with spaces"
            shutil.copytree(ROOT / "scripts", clone / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
            tree = Path("releases") / release
            shutil.copytree(ROOT / tree / "profiles", clone / tree / "profiles")
            manifest_path = clone / tree / "manifest.json"
            manifest = json.loads((ROOT / tree / "manifest.json").read_text())
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            script = root / "configuration.ps1"
            script.write_text(proof, encoding="utf-8")
            for lane in ("rtx3090", "rtx4090"):
                with self.subTest(lane=lane):
                    command = [powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                               "-File", str(script), str(ROOT / "scripts/hosts/accept-rtx4090-route.ps1"),
                               str(clone), release, lane]
                    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    variant = next(row for row in manifest["components"]["ninfer_variants"]
                                   if row["id"] == lane + "-windows-native")
                    errors = []
                    self.assertEqual(json.loads(result.stdout), native_profile(clone, release, variant, errors))
                    self.assertEqual(errors, [])
                    for field in ("release_spec", "server_config"):
                        variant["qualification"][field]["sha256"] = "0" * 64
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    rejected = subprocess.run(command, capture_output=True, text=True, timeout=60)
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertNotIn("SyntaxError", rejected.stdout + rejected.stderr)
                    for field in ("release_spec", "server_config"):
                        self.assertIn(field + " SHA-256 must match packaged bytes", rejected.stdout + rejected.stderr)


if __name__ == "__main__":
    unittest.main()
