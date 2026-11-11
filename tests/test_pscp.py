"""pscp splits a file into exact byte ranges and builds remote commands that need only ssh."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

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
    def receive(self, direction, payload, destination, failure=None):
        expected = hashlib.sha256(payload).hexdigest()

        def remote_text(_host, command, **_kwargs):
            kind = decoded_shell(command)
            if "stat -c" in kind:
                return str(len(payload))
            self.assertEqual(destination.read_bytes(), b"last verified replica")
            return "0" * 64 if failure == "digest" else expected

        def run(_argv, *, stdout, **_kwargs):
            self.assertEqual(destination.read_bytes(), b"last verified replica")
            script = decoded_shell(_argv[len(PSCP.SSH) + 1:])
            offset = int(script.split("skip=")[1].split()[0])
            length = int(script.split("count=")[1].split()[0])
            os.write(stdout, payload[offset:offset + length])
            if failure == "interrupted":
                raise TimeoutError("injected interrupted transfer")
            return types.SimpleNamespace(returncode=0)

        def urlopen(request, **_kwargs):
            self.assertEqual(destination.read_bytes(), b"last verified replica")
            if request.get_method() == "HEAD":
                result = io.BytesIO()
                result.headers = {"Content-Length": str(len(payload))}
                return result
            if request.full_url.endswith("/sha256"):
                return io.BytesIO(("0" * 64 if failure == "digest" else expected).encode())
            if failure == "interrupted":
                raise TimeoutError("injected interrupted transfer")
            first, last = request.get_header("Range").removeprefix("bytes=").split("-")
            return io.BytesIO(payload[int(first):int(last) + 1])

        with mock.patch.object(PSCP, "remote_text", side_effect=remote_text), \
             mock.patch.object(PSCP.subprocess, "run", side_effect=run), \
             mock.patch.object(PSCP.urllib.request, "urlopen", side_effect=urlopen):
            if direction == "pull":
                return PSCP.pull("transfer.invalid", "posix", "/transfer/replica", destination, 3, 2)
            return PSCP.fetch("http://transfer.invalid", "fixture-token", destination, 3, 2)

    def test_pull_and_fetch_replace_only_after_verification(self):
        for direction in ("pull", "fetch"):
            for payload in (b"new verified bytes" * 31, b""):
                with self.subTest(direction=direction, size=len(payload)), tempfile.TemporaryDirectory() as directory:
                    destination = Path(directory) / "replica.tar"
                    destination.write_bytes(b"last verified replica")
                    result = self.receive(direction, payload, destination)
                    self.assertEqual(destination.read_bytes(), payload)
                    self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())
                    self.assertEqual(list(Path(directory).iterdir()), [destination])

    def test_pull_and_fetch_preserve_existing_bytes_on_failed_transfer_or_digest(self):
        for direction in ("pull", "fetch"):
            for failure in ("interrupted", "digest"):
                with self.subTest(direction=direction, failure=failure), tempfile.TemporaryDirectory() as directory:
                    destination = Path(directory) / "replica.tar"
                    destination.write_bytes(b"last verified replica")
                    with self.assertRaises((PSCP.TransferError, TimeoutError)):
                        self.receive(direction, b"new unverified bytes" * 31, destination, failure)
                    self.assertEqual(destination.read_bytes(), b"last verified replica")
                    self.assertEqual(list(Path(directory).iterdir()), [destination])

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
