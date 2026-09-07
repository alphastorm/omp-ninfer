#!/usr/bin/env python3
"""Parallel ranged file transfer over ssh for high-latency links.

A single scp/sftp stream is bound by the SSH channel window (about 1.6 MB in flight), so on
a 120-190 ms path it tops out near 8-14 MB/s regardless of link speed. This tool moves one
file as N byte ranges over N independent ssh connections and joins them, which scales the
window linearly (measured 4x with four streams from both coasts to Japan). Each range is a
plain read or write at an offset - PowerShell FileStream on Windows hosts, ``dd`` on POSIX
hosts - so nothing beyond ssh is required on the remote side. (A file on a WSL distro's ext4
cannot be served through ``wsl.exe`` from a Windows sshd: interop stalls on binary stdout.
Write the archive onto ``/mnt/c`` with ``tar -b 8192`` first - 4 MiB records make 9p about
eight times faster - and pull it with ``--platform windows``.)
Pushes go the other way round
as N part files over N parallel ``scp`` connections joined on the remote side (PowerShell's
standard input does not stream under the Windows sshd). Both directions verify the whole file
by SHA-256 on both ends before reporting success.

Between two Windows hosts neither ssh direction works for bulk: ``ssh.exe`` acting as a client
inside an sshd session stalls on any large binary stream, whatever the far side is. For that
case use the ranged-HTTP pair instead - ``serve`` on the sending host (one file, bearer token,
tailnet-reachable, exits when the transfer completes or the deadline passes) and ``fetch`` on
the receiving host (N parallel Range requests, SHA-256 verified against the server) - which
needs only the standard library on both ends.

  pscp.py pull --host sf-old --platform windows --remote C:/Users/me/replica.tar --local replica.tar
  pscp.py push --host sf-old --platform windows --local replica.tar --remote C:/Users/me/replica.tar
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import concurrent.futures
import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Compression is forced off: checkpoint payloads are incompressible and zlib on the sending
# sshd becomes the bottleneck (a global `Compression yes` in ssh_config would otherwise apply).
# Every child gets an explicit /dev/null stdin and file-backed stdout/stderr: Windows OpenSSH's
# ssh.exe hangs indefinitely when either output handle is an anonymous pipe and the parent was
# itself started by sshd (measured on both Windows hosts), so nothing here uses subprocess pipes.
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-o", "Compression=no", "-T"]
BUFFER = 8 << 20


class TransferError(RuntimeError):
    pass


def encoded_powershell(script: str) -> list[str]:
    return ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-EncodedCommand", base64.b64encode(script.encode("utf-16-le")).decode("ascii")]


def ps_path(path: str) -> str:
    return path.replace("/", "\\").replace("'", "''")


def encoded_shell(script: str) -> str:
    """base64 the script so neither the ssh command-line join nor an intermediate cmd.exe can
    alter it; the alphabet has no characters either shell treats specially."""
    return base64.b64encode(script.encode("utf-8")).decode("ascii")


def posix_argv(script: str) -> list[str]:
    return ["sh", "-c", f'"echo {encoded_shell(script)} | base64 -d | sh"']


def posix_script(kind: str, path: str, offset: int, length: int, size: int) -> str:
    q = "'" + path.replace("'", "'\\''") + "'"
    if kind == "size":
        return f"stat -c %s {q}"
    if kind == "sha256":
        return f"sha256sum {q} | cut -c1-64"
    if kind == "join":
        parts = " ".join(f"{q}.part-{index}" for index in range(size))
        return f"mkdir -p \"$(dirname {q})\" && cat {parts} > {q} && rm -f {parts} && echo joined"
    if kind == "read":
        return f"dd if={q} bs=4M skip={offset} count={length} iflag=skip_bytes,count_bytes status=none"
    raise ValueError(kind)


def remote_command(platform: str, kind: str, path: str, offset: int = 0, length: int = 0,
                   size: int = 0) -> list[str]:
    """Build the remote argv for size / sha256 / read-range / join."""
    if platform == "windows":
        p = ps_path(path)
        if kind == "size":
            return encoded_powershell(f"(Get-Item -LiteralPath '{p}').Length")
        if kind == "sha256":
            return encoded_powershell(f"(Get-FileHash -LiteralPath '{p}' -Algorithm SHA256).Hash.ToLower()")
        if kind == "join":
            # size carries the part count; parts are <path>.part-<index>
            return encoded_powershell(
                f"$d = Split-Path -Parent '{p}'; if ($d) {{ New-Item -ItemType Directory -Force -Path $d | Out-Null }}; "
                f"$out = [IO.File]::Open('{p}', [IO.FileMode]::Create, [IO.FileAccess]::Write, [IO.FileShare]::None); "
                f"$buf = New-Object byte[] {BUFFER}; for ($i = 0; $i -lt {size}; $i++) {{ "
                f"$part = '{p}' + '.part-' + $i; $in = [IO.File]::OpenRead($part); "
                "while (($n = $in.Read($buf, 0, $buf.Length)) -gt 0) { $out.Write($buf, 0, $n) }; $in.Close(); Remove-Item -LiteralPath $part -Force }; "
                "$out.Flush(); $out.Close(); 'joined'")
        if kind == "read":
            return encoded_powershell(
                f"$fs = [IO.File]::Open('{p}', [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite); "
                f"$fs.Seek({offset}, 'Begin') | Out-Null; $out = [Console]::OpenStandardOutput(); "
                f"$buf = New-Object byte[] {BUFFER}; $left = {length}; "
                "while ($left -gt 0) { $n = $fs.Read($buf, 0, [Math]::Min($buf.Length, $left)); if ($n -le 0) { break }; "
                "$out.Write($buf, 0, $n); $left -= $n }; $out.Flush(); $fs.Close(); if ($left -ne 0) { exit 3 }")
    else:
        return posix_argv(posix_script(kind, path, offset, length, size))
    raise ValueError(kind)


def run_to_files(argv: list[str], timeout: float, stdout_path: Path | None = None) -> tuple[int, str, str]:
    """Run argv with stdin at /dev/null and both output streams on real files."""
    with tempfile.TemporaryDirectory() as scratch:
        out_path = stdout_path or (Path(scratch) / "out")
        err_path = Path(scratch) / "err"
        with open(out_path, "wb") as out, open(err_path, "wb") as err:
            code = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                  timeout=timeout).returncode
        text = "" if stdout_path else out_path.read_text("utf-8", "replace")
        return code, text, err_path.read_text("utf-8", "replace")


def remote_text(host: str, argv: list[str], timeout: float = 600.0) -> str:
    code, out, err = run_to_files(SSH + [host] + argv, timeout)
    if code != 0:
        raise TransferError(f"{argv[0]} on {host} failed rc={code}: {err.strip()[-300:]}")
    return out.strip().splitlines()[-1].strip() if out.strip() else ""


def ranges(size: int, streams: int) -> list[tuple[int, int]]:
    if size == 0:
        return []
    part = -(-size // streams)
    return [(offset, min(part, size - offset)) for offset in range(0, size, part)]


def sha256_local(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(BUFFER), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pull(host: str, platform: str, remote: str, local: Path, streams: int, timeout: float) -> dict:
    size = int(remote_text(host, remote_command(platform, "size", remote)))
    started = time.monotonic()
    local.parent.mkdir(parents=True, exist_ok=True)
    with local.open("wb") as handle:
        handle.truncate(size)

    def fetch(item: tuple[int, int]) -> int:
        offset, length = item
        # The child writes straight into the destination through its own descriptor, positioned
        # at this range's offset: no pipe, no staging copy, no seek races between streams.
        descriptor = os.open(local, os.O_WRONLY | getattr(os, "O_BINARY", 0))
        try:
            os.lseek(descriptor, offset, os.SEEK_SET)
            with tempfile.TemporaryDirectory() as scratch:
                err_path = Path(scratch) / "err"
                with open(err_path, "wb") as err:
                    code = subprocess.run(SSH + [host] + remote_command(platform, "read", remote, offset, length),
                                          stdin=subprocess.DEVNULL, stdout=descriptor, stderr=err,
                                          timeout=timeout).returncode
                received = os.lseek(descriptor, 0, os.SEEK_CUR) - offset
                if code != 0 or received != length:
                    raise TransferError(f"range {offset}+{length} received {received} rc={code}: "
                                        + err_path.read_text('utf-8', 'replace').strip()[-200:])
        finally:
            os.close(descriptor)
        return received

    with concurrent.futures.ThreadPoolExecutor(streams) as pool:
        moved = sum(pool.map(fetch, ranges(size, streams)))
    wall = time.monotonic() - started
    remote_digest = remote_text(host, remote_command(platform, "sha256", remote), timeout=timeout)
    local_digest = sha256_local(local)
    if moved != size or remote_digest != local_digest:
        raise TransferError(f"pull did not verify: moved {moved}/{size}, remote {remote_digest[:12]} local {local_digest[:12]}")
    return {"direction": "pull", "bytes": size, "streams": streams, "wall_s": round(wall, 2),
            "mb_per_s": round(size / 1e6 / wall, 1) if wall else None, "sha256": local_digest}


def push(host: str, platform: str, local: Path, remote: str, streams: int, timeout: float) -> dict:
    size = local.stat().st_size
    parts = ranges(size, streams)
    started = time.monotonic()
    scratch = local.parent / f".{local.name}.pscp"
    scratch.mkdir(exist_ok=True)

    def send(item: tuple[int, tuple[int, int]]) -> int:
        index, (offset, length) = item
        part = scratch / f"part-{index}"
        with local.open("rb") as src, part.open("wb") as dst:
            src.seek(offset)
            left = length
            while left > 0:
                chunk = src.read(min(BUFFER, left))
                if not chunk:
                    break
                dst.write(chunk)
                left -= len(chunk)
        if left != 0:
            raise TransferError(f"range {offset}+{length} short by {left} bytes locally")
        target = f"{remote}.part-{index}"
        code, _, err = run_to_files(["scp", "-q", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20",
                                     "-o", "Compression=no", str(part), f"{host}:{target}"], timeout)
        part.unlink()
        if code != 0:
            raise TransferError(f"scp of part {index} failed: {err.strip()[-200:]}")
        return length

    try:
        with concurrent.futures.ThreadPoolExecutor(streams) as pool:
            moved = sum(pool.map(send, enumerate(parts)))
    finally:
        for stale in scratch.glob("part-*"):
            stale.unlink()
        scratch.rmdir()
    remote_text(host, remote_command(platform, "join", remote, size=len(parts)), timeout=timeout)
    wall = time.monotonic() - started
    remote_digest = remote_text(host, remote_command(platform, "sha256", remote), timeout=timeout)
    local_digest = sha256_local(local)
    if moved != size or remote_digest != local_digest:
        raise TransferError(f"push did not verify: moved {moved}/{size}, remote {remote_digest[:12]} local {local_digest[:12]}")
    return {"direction": "push", "bytes": size, "streams": streams, "wall_s": round(wall, 2),
            "mb_per_s": round(size / 1e6 / wall, 1) if wall else None, "sha256": local_digest}



class RangeHandler(BaseHTTPRequestHandler):
    """Serves exactly one file, only to a caller holding the token, only for GET/HEAD."""

    protocol_version = "HTTP/1.1"

    def __init__(self, *args, path: Path, token: str, digest: str, state: dict, **kwargs):
        self.path_served, self.token, self.digest, self.state = path, token, digest, state
        super().__init__(*args, **kwargs)

    def log_message(self, *_args) -> None:  # noqa: D102 - quiet by design
        return

    def _authorized(self) -> bool:
        return secrets.compare_digest(self.headers.get("Authorization", ""), f"Bearer {self.token}")

    def _refuse(self, code: int) -> None:
        self.send_response(code)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self) -> None:  # noqa: N802
        if not self._authorized() or self.path not in ("/file", "/sha256"):
            return self._refuse(404 if self._authorized() else 401)
        self.send_response(200)
        self.send_header("Content-Length", str(self.path_served.stat().st_size if self.path == "/file" else 64))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorized():
            return self._refuse(401)
        if self.path == "/sha256":
            body = self.digest.encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path != "/file":
            return self._refuse(404)
        size = self.path_served.stat().st_size
        start, length = 0, size
        header = self.headers.get("Range", "")
        if header.startswith("bytes="):
            first, _, last = header[6:].partition("-")
            start = int(first)
            end = int(last) if last else size - 1
            if start >= size or end >= size or end < start:
                return self._refuse(416)
            length = end - start + 1
        self.send_response(206 if header else 200)
        if header:
            self.send_header("Content-Range", f"bytes {start}-{start + length - 1}/{size}")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        with self.path_served.open("rb") as handle:
            handle.seek(start)
            left = length
            while left > 0:
                chunk = handle.read(min(BUFFER, left))
                if not chunk:
                    break
                self.wfile.write(chunk)
                left -= len(chunk)
        with self.state["lock"]:
            self.state["served"] += length - left
            if self.state["served"] >= self.state["expect"]:
                self.state["done"].set()


def serve(path: Path, port: int, deadline: float, expect_multiple: int) -> dict:
    digest = sha256_local(path)
    size = path.stat().st_size
    state = {"served": 0, "expect": size * expect_multiple, "lock": threading.Lock(),
             "done": threading.Event()}
    # Hex, not urlsafe base64: a token starting with "-" is parsed as an option by every shell
    # and CLI that has to carry it to the other host.
    handler = partial(RangeHandler, path=path, token=(token := secrets.token_hex(24)),
                      digest=digest, state=state)
    server = ThreadingHTTPServer(("0.0.0.0", port), handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(json.dumps({"status": "serving", "port": server.server_address[1], "token": token,
                      "bytes": size, "sha256": digest, "host": socket.gethostname()}), flush=True)
    completed = state["done"].wait(deadline)
    with contextlib.suppress(Exception):
        server.shutdown()
    return {"status": "passed" if completed else "failed", "direction": "serve",
            "bytes": size, "served_bytes": state["served"], "sha256": digest,
            "error": None if completed else "deadline passed before the transfer completed"}


def fetch(url: str, token: str, local: Path, streams: int, timeout: float) -> dict:
    def request(path: str, start: int | None = None, length: int | None = None, method: str = "GET"):
        req = urllib.request.Request(url.rstrip("/") + path, method=method,
                                     headers={"Authorization": f"Bearer {token}"})
        if start is not None and length:
            req.add_header("Range", f"bytes={start}-{start + length - 1}")
        return urllib.request.urlopen(req, timeout=timeout)

    # HEAD, never a bodied GET: probing with a full GET and abandoning it makes the server
    # write the whole file into a socket nobody reads, doubling the bytes on the wire.
    with request("/file", method="HEAD") as probe:
        size = int(probe.headers["Content-Length"])
    with request("/sha256") as answer:
        remote_digest = answer.read().decode().strip()
    local.parent.mkdir(parents=True, exist_ok=True)
    with local.open("wb") as handle:
        handle.truncate(size)
    started = time.monotonic()

    def grab(item: tuple[int, int]) -> int:
        offset, length = item
        received = 0
        with request("/file", offset, length) as response, \
                os.fdopen(os.open(local, os.O_WRONLY | getattr(os, "O_BINARY", 0)), "r+b", buffering=0) as out:
            out.seek(offset)
            while received < length:
                chunk = response.read(min(BUFFER, length - received))
                if not chunk:
                    break
                out.write(chunk)
                received += len(chunk)
        if received != length:
            raise TransferError(f"range {offset}+{length} received {received}")
        return received

    with concurrent.futures.ThreadPoolExecutor(streams) as pool:
        moved = sum(pool.map(grab, ranges(size, streams)))
    wall = time.monotonic() - started
    local_digest = sha256_local(local)
    if moved != size or local_digest != remote_digest:
        raise TransferError(f"fetch did not verify: moved {moved}/{size}, remote {remote_digest[:12]} local {local_digest[:12]}")
    return {"direction": "fetch", "bytes": size, "streams": streams, "wall_s": round(wall, 2),
            "mb_per_s": round(size / 1e6 / wall, 1) if wall else None, "sha256": local_digest}


def default_streams(direction: str) -> int:
    """A Windows sshd resets above roughly eight concurrent connections, so ssh transfers stay
    there; ranged HTTP has no such limit and each connection is window-bound, so it scales
    further (measured 5.8 MB/s at eight streams against 9.2 at sixteen, cross-site)."""
    return 16 if direction == "fetch" else 8


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("direction", choices=("pull", "push", "serve", "fetch"))
    parser.add_argument("--host", help="ssh destination (pull/push)")
    parser.add_argument("--platform", choices=("windows", "posix"), help="remote OS (pull/push)")
    parser.add_argument("--remote", help="remote path (pull/push)")
    parser.add_argument("--local", type=Path, help="local path (pull/push/serve/fetch)")
    parser.add_argument("--url", help="server base URL (fetch)")
    parser.add_argument("--token", help="bearer token printed by serve (fetch)")
    parser.add_argument("--port", type=int, default=0, help="listen port, 0 picks one (serve)")
    parser.add_argument("--expect-transfers", type=int, default=1,
                        help="finish serve after this many complete passes over the file")
    parser.add_argument("--streams", type=int, default=None,
                        help="parallel connections; default 8 over ssh (a Windows sshd resets\n"
                             "above about that) and 16 for fetch, where each connection is\n"
                             "window-bound and more of them still scale")
    parser.add_argument("--timeout", type=float, default=3600.0)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    if args.streams is None:
        args.streams = default_streams(args.direction)
    if args.streams < 1 or args.streams > 64:
        parser.error("--streams must be in [1, 64]")
    if args.direction in ("pull", "push") and not (args.host and args.platform and args.remote and args.local):
        parser.error("pull/push need --host, --platform, --remote and --local")
    if args.direction == "serve" and not args.local:
        parser.error("serve needs --local")
    if args.direction == "fetch" and not (args.url and args.token and args.local):
        parser.error("fetch needs --url, --token and --local")
    try:
        if args.direction == "pull":
            result = pull(args.host, args.platform, args.remote, args.local, args.streams, args.timeout)
        elif args.direction == "push":
            result = push(args.host, args.platform, args.local, args.remote, args.streams, args.timeout)
        elif args.direction == "serve":
            result = serve(args.local, args.port, args.timeout, max(1, args.expect_transfers))
        else:
            result = fetch(args.url, args.token, args.local, args.streams, args.timeout)
        result.setdefault("status", "passed")
    except (TransferError, OSError, urllib.error.URLError, subprocess.TimeoutExpired) as error:
        result = {"status": "failed", "direction": args.direction, "error": str(error)}
    if args.host:
        result.update({"host": args.host, "platform": args.platform})
    if args.receipt:
        args.receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
