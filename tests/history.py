"""Fail closed in CI when a history-dependent contract cannot be exercised."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IO_SPEC = importlib.util.spec_from_file_location("history_release_io", ROOT / "scripts/release_io.py")
assert IO_SPEC is not None and IO_SPEC.loader is not None
IO = importlib.util.module_from_spec(IO_SPEC)
IO_SPEC.loader.exec_module(IO)


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


def release_snapshot(root: Path, release: str) -> dict[str, bytes]:
    """All bytes the rebind stages own, including the deliberately unpromoted root."""
    paths = ("compatibility.json", "docs/COMPATIBILITY.md", "profiles", f"releases/{release}",
             "examples/manual-tunnel/start-ninfer.sh", "examples/manual-tunnel/stop-ninfer.sh")
    result = {}
    for name in paths:
        path = root / name
        for file in path.rglob("*") if path.is_dir() else [path]:
            if file.is_file():
                result[file.relative_to(root).as_posix()] = file.read_bytes()
    return result


def _different_pointers(before: object, after: object, pointer: str = "") -> set[str]:
    if isinstance(before, dict) and isinstance(after, dict):
        changed = set()
        for key in before.keys() | after.keys():
            child = pointer + "/" + key.replace("~", "~0").replace("/", "~1")
            if key not in before or key not in after:
                changed.add(child)
            else:
                changed.update(_different_pointers(before[key], after[key], child))
        return changed
    if isinstance(before, list) and isinstance(after, list):
        changed = set()
        for index in range(max(len(before), len(after))):
            child = f"{pointer}/{index}"
            if index >= len(before) or index >= len(after):
                changed.add(child)
            else:
                changed.update(_different_pointers(before[index], after[index], child))
        return changed
    return {pointer} if before != after else set()


def corrected_lane_snapshot(
    snapshot_commit: str, authority_path: str | Path, draft: bool, *, root: Path = ROOT,
) -> tuple[dict[str, bytes], set[tuple[str, str]]]:
    """Correct v0.19.0's historical lane label and close its hashes using historical code.

    Returns repository-relative expected bytes and changed JSON leaves as
    ``(repository_path, RFC6901_pointer)`` pairs. Rendered Markdown must compare exactly
    against the returned bytes; it receives no whole-file pointer exception.
    ``authority_path`` is a repository-relative Git path, never a caller's live file.
    """
    authority_path = Path(authority_path)
    if authority_path.is_absolute() or ".." in authority_path.parts:
        raise ValueError("authority_path must be repository-relative")
    require_commits(snapshot_commit, root=root)
    published_commit = resolve_commits("v0.19.0", root=root)[0]
    with tempfile.TemporaryDirectory() as temporary:
        snapshot_root = Path(temporary) / "snapshot"
        subprocess.run(["git", "clone", "--quiet", "--config", "core.autocrlf=false",
                        "--shared", "--no-checkout", str(root), str(snapshot_root)],
                       check=True, capture_output=True)
        subprocess.run(["git", "checkout", "--quiet", "--detach", snapshot_commit],
                       cwd=snapshot_root, check=True, capture_output=True)
        published = json.loads(subprocess.run(
            ["git", "show", f"{published_commit}:compatibility.json"], cwd=root,
            capture_output=True, check=True,
        ).stdout)
        path = snapshot_root / authority_path
        authority = json.loads(path.read_bytes())
        release = authority["product_release"]
        if release != "v0.19.0":
            raise AssertionError("the historical lane correction belongs to v0.19.0")
        before = release_snapshot(snapshot_root, release)
        rows = [row for row in authority["runtime_contracts"] if row["lane"].startswith("RTX 3090 ")]
        final = [row["lane"] for row in published["runtime_contracts"]
                 if row["lane"].startswith("RTX 3090 ")]
        if len(rows) != 1 or len(final) != 1 or rows[0]["lane"] == final[0]:
            raise AssertionError("snapshot must contain exactly the stale historical lane label")
        rows[0]["lane"] = final[0]
        IO.atomic_write_json(path, authority)
        # Historical text-mode output translates LF on Windows. Share only the byte writer;
        # both derivation and rendering remain the snapshot's immutable implementations.
        historical = """
import sys
from pathlib import Path
root, helpers = map(Path, sys.argv[1:3])
draft = sys.argv[3] == "1"
sys.path.insert(0, str(root / "scripts"))
import rebind_release
import render_compatibility
sys.path.insert(0, str(helpers))
from release_io import atomic_write, atomic_write_json
rebind_release.save = atomic_write_json
rebind_release.render = lambda authority, output: atomic_write(
    output, render_compatibility.render(render_compatibility.load_authority(authority)))
sys.argv = ["rebind_release.py", "--release", "v0.19.0"] + (["--draft"] if draft else [])
raise SystemExit(rebind_release.main())
"""
        subprocess.run([sys.executable, "-c", historical, str(snapshot_root),
                        str(ROOT / "scripts"), "1" if draft else "0"],
                       cwd=snapshot_root, capture_output=True, check=True)
        expected = release_snapshot(snapshot_root, release)
        if before.keys() != expected.keys():
            raise AssertionError("historical label correction must not add or remove bound files")
        pointers = {
            (name, pointer)
            for name in before if name.endswith(".json") and before[name] != expected[name]
            for pointer in _different_pointers(json.loads(before[name]), json.loads(expected[name]))
        }
        return expected, pointers
