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


def decoded_shell(argv: list[str]) -> str:
    return base64.b64decode(argv[-1].strip('"').split()[1]).decode("utf-8")


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
        self.assertEqual(PSCP.posix_script("read", "/srv/a.tar", 10, 20, 0),
                         "dd if='/srv/a.tar' bs=4M skip=10 count=20 iflag=skip_bytes,count_bytes status=none")
        self.assertEqual(PSCP.remote_command("posix", "read", "/srv/a.tar", 10, 20)[:2], ["sh", "-c"])
        self.assertIn("'/srv/a.tar'.part-0 '/srv/a.tar'.part-1", PSCP.posix_script("join", "/srv/a.tar", 0, 0, 2))
        self.assertEqual(PSCP.posix_script("size", "/srv/a.tar", 0, 0, 0), "stat -c %s '/srv/a.tar'")

    def test_posix_paths_with_quotes_survive_both_joins(self) -> None:
        # The remote shell receives one base64 word, so no path character can escape quoting.
        argv = PSCP.remote_command("posix", "size", "/srv/it's.tar")
        self.assertEqual(argv[:2], ["sh", "-c"])
        self.assertEqual(decoded_shell(argv), "stat -c %s '/srv/it'\\''s.tar'")

    def test_ssh_disables_compression(self) -> None:
        self.assertIn("Compression=no", PSCP.SSH)

    def test_stream_default_is_higher_for_http_than_ssh(self) -> None:
        self.assertEqual(PSCP.default_streams("fetch"), 16)
        self.assertEqual(PSCP.default_streams("pull"), 8)
        self.assertEqual(PSCP.default_streams("push"), 8)


if __name__ == "__main__":
    unittest.main()
