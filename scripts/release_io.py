"""Atomic writes and git reads shared by the release tools.

An authority, journal or evidence file that is rewritten in place can be left truncated by an
interrupted run, and the next tool then reads a shorter, still-parseable document. Every release
tool writes through ``atomic_write`` or ``atomic_copy`` instead: bytes go to a temporary file
in the target's directory, are flushed to disk, and replace the target in one rename.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def atomic_write(path: Path, data: bytes | str) -> None:
    """Replace ``path`` with ``data`` in one rename; a failure leaves the previous bytes.

    The replacement keeps the target's permission bits, so a rewritten launcher stays executable.
    A new file gets the mode a plain ``open`` would give it rather than the temporary file's.
    """
    payload = data.encode("utf-8") if isinstance(data, str) else data
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except FileNotFoundError:
        umask = os.umask(0)
        os.umask(umask)
        mode = 0o666 & ~umask
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def atomic_write_json(path: Path, document: Any) -> None:
    """The release tree's JSON form: two-space indent and one trailing newline."""
    atomic_write(path, json.dumps(document, indent=2) + "\n")


def atomic_copy(source: Path, destination: Path) -> None:
    """Stream into a sibling temporary file; interruption preserves the destination.

    The copy carries the source's permission bits, as ``atomic_write`` keeps its target's.
    """
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp",
                                       dir=destination.parent)
    try:
        with os.fdopen(handle, "wb") as output, Path(source).open("rb") as source_stream:
            for chunk in iter(lambda: source_stream.read(1024 * 1024), b""):
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, stat.S_IMODE(os.stat(source).st_mode))
        os.replace(temporary, destination)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def git(root: Path, *arguments: str) -> str:
    """Standard output of ``git`` run in ``root``; a non-zero exit raises ``CalledProcessError``."""
    return subprocess.run(["git", *arguments], cwd=root, check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout
