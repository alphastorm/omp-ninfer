"""Portable, effect-free primitives shared by host acceptance drivers."""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def powershell_quote(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def powershell_encoded_command(code: str) -> str:
    return base64.b64encode(code.encode("utf-16le")).decode("ascii")
