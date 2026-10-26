"""Acceptance restoration primitives; platform effects remain in the lane drivers."""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path


@contextmanager
def restoration_lock(root: Path):
    # Only the WSL backend needs flock. Import lazily so native planners stay portable.
    import fcntl

    with (root / "restore.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def completed_restoration(root: Path) -> bool:
    proof = root / "restoration.json"
    if not proof.exists():
        return False
    previous = json.loads(proof.read_text())
    assert not previous.get("retained_window_created_parents"), (
        "window-created parents retained; restoration proof failed")
    return True


def directory_snapshot(paths) -> dict:
    directories = {}
    for path in paths:
        try:
            metadata = path.stat()
        except FileNotFoundError:
            directories[str(path)] = {"exists": False}
        else:
            directories[str(path)] = {
                "exists": True, "mode": metadata.st_mode & 0o777,
                "atime_ns": metadata.st_atime_ns, "mtime_ns": metadata.st_mtime_ns}
    return directories


def restore_directory_metadata(directories: dict) -> list[str]:
    retained = []
    for name, metadata in sorted(directories.items(), key=lambda row: len(Path(row[0]).parts), reverse=True):
        path = Path(name)
        if metadata["exists"]:
            os.chmod(path, metadata["mode"])
            os.utime(path, ns=(metadata["atime_ns"], metadata["mtime_ns"]))
        elif path.exists():
            # Never recurse into another owner's new state.
            try:
                path.rmdir()
            except OSError:
                retained.append(name)
    return retained


def restore_and_audit(restore, audit=None):
    """Run an independent restore before its proof; never turn an exception into success."""
    restored = restore()
    audited = audit() if audit is not None else None
    return restored, audited
