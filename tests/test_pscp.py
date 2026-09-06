"""pscp splits a file into exact byte ranges and builds remote commands that need only ssh."""
from __future__ import annotations

import base64
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pscp", ROOT / "scripts" / "hosts" / "pscp.py")
assert SPEC is not None and SPEC.loader is not None
PSCP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PSCP)


def decoded(argv: list[str]) -> str:
    return base64.b64decode(argv[-1]).decode("utf-16-le")


class PscpTest(unittest.TestCase):
    def test_ranges_partition_exactly(self) -> None:
        for size, streams in ((100, 8), (1, 8), (268435456, 8), (7, 3), (0, 4)):
            parts = PSCP.ranges(size, streams)
            self.assertEqual(sum(length for _, length in parts), size)
            self.assertEqual([offset for offset, _ in parts], [sum(l for _, l in parts[:i]) for i in range(len(parts))])
            self.assertTrue(all(length > 0 for _, length in parts))
            self.assertLessEqual(len(parts), streams)

    def test_windows_commands_are_encoded_powershell_with_literal_paths(self) -> None:
        read = PSCP.remote_command("windows", "read", "C:/Users/me/it's.tar", 4096, 8192)
        self.assertEqual(read[:2], ["powershell", "-NoProfile"])
        script = decoded(read)
        self.assertIn("'C:\\Users\\me\\it''s.tar'", script)
        self.assertIn("Seek(4096", script)
        self.assertIn("$left = 8192", script)
        join = decoded(PSCP.remote_command("windows", "join", "C:/x/y.tar", size=3))
        self.assertIn("$i -lt 3", join)
        self.assertIn(".part-", join)
        self.assertIn("(Get-FileHash", decoded(PSCP.remote_command("windows", "sha256", "C:/x/y.tar")))

    def test_posix_commands_use_byte_offsets(self) -> None:
        self.assertEqual(PSCP.remote_command("posix", "read", "/srv/a.tar", 10, 20),
                         ["dd", "if=/srv/a.tar", "bs=4M", "skip=10", "count=20", "iflag=skip_bytes,count_bytes", "status=none"])
        join = PSCP.remote_command("posix", "join", "/srv/a.tar", size=2)
        self.assertIn("'/srv/a.tar'.part-0 '/srv/a.tar'.part-1", join[-1])
        self.assertEqual(PSCP.remote_command("posix", "size", "/srv/a.tar")[:2], ["stat", "-c"])

    def test_ssh_disables_compression(self) -> None:
        self.assertIn("Compression=no", PSCP.SSH)


if __name__ == "__main__":
    unittest.main()
