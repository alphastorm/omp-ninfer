#!/usr/bin/env python3
"""Parallel ranged file transfer over ssh for high-latency links.

A single scp/sftp stream is bound by the SSH channel window (about 1.6 MB in flight), so on
a 120-190 ms path it tops out near 8-14 MB/s regardless of link speed. This tool moves one
file as N byte ranges over N independent ssh connections and joins them, which scales the
window linearly (measured 4x with four streams from both coasts to Japan). Each range is a
plain read or write at an offset - PowerShell FileStream on Windows hosts, ``dd`` on POSIX
hosts - so nothing beyond ssh is required on the remote side. Pushes go the other way round
as N part files over N parallel ``scp`` connections joined on the remote side (PowerShell's
standard input does not stream under the Windows sshd). Both directions verify the whole file
by SHA-256 on both ends before reporting success.

  pscp.py pull --host sf-old --platform windows --remote C:/Users/me/replica.tar --local replica.tar
  pscp.py push --host sf-old --platform windows --local replica.tar --remote C:/Users/me/replica.tar
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Compression is forced off: checkpoint payloads are incompressible and zlib on the sending
# sshd becomes the bottleneck (a global `Compression yes` in ssh_config would otherwise apply).
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-o", "Compression=no", "-T"]
BUFFER = 8 << 20


class TransferError(RuntimeError):
    pass


def encoded_powershell(script: str) -> list[str]:
    return ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-EncodedCommand", base64.b64encode(script.encode("utf-16-le")).decode("ascii")]


def ps_path(path: str) -> str:
    return path.replace("/", "\\").replace("'", "''")


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
        q = "'" + path.replace("'", "'\\''") + "'"
        if kind == "size":
            return ["stat", "-c", "%s", q]
        if kind == "sha256":
            return ["sh", "-c", f"sha256sum {q} | cut -c1-64"]
        if kind == "join":
            parts = " ".join(f"{q}.part-{index}" for index in range(size))
            return ["sh", "-c", f"mkdir -p \"$(dirname {q})\" && cat {parts} > {q} && rm -f {parts} && echo joined"]
        if kind == "read":
            return ["dd", f"if={path}", "bs=4M", f"skip={offset}", f"count={length}",
                    "iflag=skip_bytes,count_bytes", "status=none"]
    raise ValueError(kind)


def remote_text(host: str, argv: list[str], timeout: float = 600.0) -> str:
    completed = subprocess.run(SSH + [host] + argv, capture_output=True, text=True, timeout=timeout)
    if completed.returncode != 0:
        raise TransferError(f"{argv[0]} on {host} failed rc={completed.returncode}: {completed.stderr.strip()[-300:]}")
    return completed.stdout.strip().splitlines()[-1].strip() if completed.stdout.strip() else ""


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
        with subprocess.Popen(SSH + [host] + remote_command(platform, "read", remote, offset, length),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc, \
                os.fdopen(os.open(local, os.O_WRONLY), "r+b", buffering=0) as out:
            out.seek(offset)
            received = 0
            assert proc.stdout is not None
            for chunk in iter(lambda: proc.stdout.read(BUFFER), b""):
                out.write(chunk)
                received += len(chunk)
            stderr = proc.stderr.read().decode("utf-8", "replace") if proc.stderr is not None else ""
            if proc.wait(timeout=timeout) != 0 or received != length:
                raise TransferError(f"range {offset}+{length} received {received}: {stderr.strip()[-200:]}")
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
        completed = subprocess.run(["scp", "-q", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-o", "Compression=no", str(part), f"{host}:{target}"],
                                   capture_output=True, text=True, timeout=timeout)
        part.unlink()
        if completed.returncode != 0:
            raise TransferError(f"scp of part {index} failed: {completed.stderr.strip()[-200:]}")
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("direction", choices=("pull", "push"))
    parser.add_argument("--host", required=True)
    parser.add_argument("--platform", choices=("windows", "posix"), required=True)
    parser.add_argument("--remote", required=True)
    parser.add_argument("--local", required=True, type=Path)
    parser.add_argument("--streams", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=3600.0)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    if args.streams < 1 or args.streams > 64:
        parser.error("--streams must be in [1, 64]")
    try:
        if args.direction == "pull":
            result = pull(args.host, args.platform, args.remote, args.local, args.streams, args.timeout)
        else:
            result = push(args.host, args.platform, args.local, args.remote, args.streams, args.timeout)
        result["status"] = "passed"
    except (TransferError, OSError, subprocess.TimeoutExpired) as error:
        result = {"status": "failed", "direction": args.direction, "error": str(error)}
    result.update({"host": args.host, "platform": args.platform})
    if args.receipt:
        args.receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
