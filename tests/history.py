"""Fail closed in CI when a history-dependent contract cannot be exercised."""

from __future__ import annotations

import os
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require_commits(*full_shas: str, root: Path = ROOT) -> None:
    shallow = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"], cwd=root,
        capture_output=True, text=True, check=True,
    ).stdout.strip() == "true"
    missing = [
        sha for sha in full_shas
        if re.fullmatch(r"[0-9a-f]{40}", sha) is None
        or subprocess.run(
            ["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=root,
            capture_output=True,
        ).returncode != 0
    ]
    if shallow or missing:
        message = "full public history required" + (f": {', '.join(missing)}" if missing else "")
        if os.environ.get("OMP_NINFER_REQUIRE_HISTORY") == "1":
            raise AssertionError(message)
        raise unittest.SkipTest(message)


def resolve_commits(*references: str, root: Path = ROOT) -> tuple[str, ...]:
    require_commits(root=root)
    commits = tuple(subprocess.run(
        ["git", "rev-parse", "--verify", f"{reference}^{{commit}}"], cwd=root,
        capture_output=True, text=True, check=True,
    ).stdout.strip() for reference in references)
    require_commits(*commits, root=root)
    return commits
