"""Every native Windows GPU operation must target the installed lane's card."""
from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOSTS = ROOT / "scripts" / "hosts"
# .sh samplers run inside the single-GPU RTX 5090 container/WSL lane, not native Windows.
# Include Python drivers because they may embed PowerShell commands.
GPU_SCAN_FILES = tuple(sorted(path for path in HOSTS.rglob("*")
                              if path.suffix in {".ps1", ".py"}))
# The only enumeration resolves legacy records on a SINGLE-GPU host. It refuses multiple
# cards rather than choosing an ordinal. Pin its exact query/function and allow it only once.
GPU_ENUMERATIONS = {
    ("scripts/hosts/native-gpu.ps1", "Resolve-NativeGpuUuid"): "--query-gpu=uuid",
}


def unindexed_gpu_commands(sources: dict[str, str]) -> list[str]:
    violations = []
    used_enumerations = set()
    operation = re.compile(r"--query-[a-z-]+(?:=[a-z0-9_.,]+)?|(?<![\w-])-pl\b|--power-limit\b|(?<![\w-])-q\b")
    for path, original in sources.items():
        text = re.sub(r"\x60\r?\n\s*", " ", original)
        text = re.sub(r"Invoke-NvidiaSmi\s+@\([^)]*\)",
                      lambda match: match[0].replace("\n", " "), text)
        function = ""
        for number, line in enumerate(text.splitlines(), 1):
            definition = re.match(r"\s*(?:function\s+([\w-]+)|def\s+(\w+)\()", line)
            if definition:
                function = definition[1] or definition[2]
            if line.lstrip().startswith("#"):
                continue
            for statement in line.split(";"):
                for match in operation.finditer(statement):
                    if match[0] == "-q" and not re.search(r"nvidia[-_]?smi|NvidiaSmi", statement, re.I):
                        continue
                    if re.search(r"(?<![\w-])(?:-i|--id)(?:['\"]?\s*[,=]|\s+)", statement):
                        continue
                    key = (path, function)
                    if GPU_ENUMERATIONS.get(key) == match[0] and key not in used_enumerations:
                        used_enumerations.add(key)
                        continue
                    violations.append(f"{path}:{number}: {match[0]} in {function}")
    return violations


class WindowsHostGpuTests(unittest.TestCase):
    def test_no_unindexed_gpu_queries_or_sets(self) -> None:
        sources = {path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
                   for path in GPU_SCAN_FILES}
        self.assertEqual(unindexed_gpu_commands(sources), [])

    def test_invariant_detects_multiline_chained_and_absolute_commands(self) -> None:
        path = "scripts/hosts/fixture.ps1"
        for command in (
            "Invoke-NvidiaSmi @(\n '--query-gpu=power.limit',\n '--format=csv,noheader')",
            "& $absolutePath -pl 300", "nvidia-smi.exe -q -x",
            "nvidia-smi -i $uuid --query-gpu=name; nvidia-smi --query-gpu=power.limit",
            "& 'C:/tools/nvidia-smi.exe' `\n --power-limit 300",
        ):
            with self.subTest(command=command):
                self.assertTrue(unindexed_gpu_commands({path: command}))
        self.assertEqual(unindexed_gpu_commands({path:
            "Invoke-NvidiaSmi @(\n '-i', $uuid,\n '-pl', '300')"}), [])

    def test_enumeration_exception_cannot_be_reused_or_relocated(self) -> None:
        source = "function Resolve-NativeGpuUuid {\nnvidia-smi --query-gpu=uuid\n"
        path = "scripts/hosts/native-gpu.ps1"
        self.assertEqual(unindexed_gpu_commands({path: source}), [])
        self.assertEqual(len(unindexed_gpu_commands({path: source + "nvidia-smi --query-gpu=uuid"})), 1)
        self.assertTrue(unindexed_gpu_commands({"scripts/hosts/fixture.ps1": source}))


if __name__ == "__main__":
    unittest.main()
