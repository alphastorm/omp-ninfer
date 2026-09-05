#!/usr/bin/env python3
"""Replicate NInfer session checkpoints: export a store's published generations to shared
storage, or import them back to a local checkpoint root before a restore.

The native IO paths (O_DIRECT / DirectStorage) need a local filesystem, so a checkpoint root
is never served from a network share; replication is a crash-consistent copy of what the
store publishes and nothing else. A generation is copied only after every file it lists is
verified against the manifest (size and SHA-256), it is written to a staging directory that
the runtime never scans, published with one atomic rename, and the session's ``current``
pointer is replaced last. Generations without an origin tag (``manifest.mac``) are refused
by default: a checkpoint that crosses a trust boundary must carry the tag the runtime
verifies under ``--session-checkpoint-require-origin-auth``; ``--allow-unauthenticated``
keeps the compatibility window for locally produced legacy generations. The tool cannot
verify the tag itself (the key lives with the server), so import proves integrity and the
runtime proves origin.

Layout (identical on the RTX 5090 container and both native Windows lanes)::

  <root>/sessions/<session>/current                       -> generation name
  <root>/sessions/<session>/generations/<generation>/manifest.json
  <root>/sessions/<session>/generations/<generation>/manifest.mac      (origin tag)
  <root>/sessions/<session>/generations/<generation>/<manifest files>  (responses.cbor, engine/*)

Examples::

  python3 scripts/checkpoint_sync.py export --root /srv/ninfer/checkpoints \\
      --destination /mnt/nas/ninfer-sessions --receipt export.json
  python3 scripts/checkpoint_sync.py import --source /mnt/nas/ninfer-sessions \\
      --root /srv/ninfer/checkpoints --session <session> --receipt import.json
  python3 scripts/checkpoint_sync.py verify --root /mnt/nas/ninfer-sessions
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import shutil
import sys
from pathlib import Path, PurePosixPath
from typing import Any

ARTIFACT_TYPE = "omp_ninfer_checkpoint_sync"
SCHEMA_VERSION = 1
MANIFEST_ARTIFACT_TYPE = "ninfer_session_checkpoint"
MANIFEST_LIMIT_BYTES = 16 << 20
GENERATION_RE = re.compile(r"^[0-9]{1,20}-[0-9]{1,10}$")
SESSION_RE = re.compile(r"^[0-9a-f]{64}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class SyncError(RuntimeError):
    pass


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def fsync_path(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) if path.is_dir() else os.O_RDONLY
    try:
        fd = os.open(path, flags)
    except OSError:
        return  # directory fsync is not available on every platform; the file syncs stand
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def write_synced(path: Path, data: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    fsync_path(path.parent)


def copy_synced(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as src, destination.open("wb") as dst:
        shutil.copyfileobj(src, dst, 8 << 20)
        dst.flush()
        os.fsync(dst.fileno())


def generation_order(name: str) -> tuple[int, int]:
    stamp, sequence = name.split("-", 1)
    return int(stamp), int(sequence)


def valid_manifest_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or len(value) > 512:
        return False
    parts = PurePosixPath(value).parts
    return (
        not value.startswith("/") and "\\" not in value and ".." not in parts
        and all(part not in ("", ".") for part in parts)
        and value not in ("manifest.json", "manifest.mac")
    )


def read_current(session: Path) -> str | None:
    pointer = session / "current"
    if not pointer.exists():
        return None
    if not pointer.is_file():
        raise SyncError(f"{session.name}: current pointer is not a regular file")
    value = pointer.read_text(encoding="utf-8").rstrip("\r\n")
    if not GENERATION_RE.fullmatch(value):
        raise SyncError(f"{session.name}: current pointer is invalid")
    return value


def verify_generation(root: Path, session: str, generation: str,
                      allow_unauthenticated: bool) -> dict[str, Any]:
    """Verify a published generation against its manifest; return its descriptor."""
    directory = root / "sessions" / session / "generations" / generation
    manifest_path = directory / "manifest.json"
    if not directory.is_dir():
        raise SyncError(f"{session}/{generation}: generation directory is missing")
    if not manifest_path.is_file() or manifest_path.stat().st_size > MANIFEST_LIMIT_BYTES:
        raise SyncError(f"{session}/{generation}: manifest is missing or oversized")
    manifest_bytes = manifest_path.read_bytes()
    try:
        manifest = json.loads(manifest_bytes)
    except ValueError as error:
        raise SyncError(f"{session}/{generation}: manifest is not JSON") from error
    if (
        not isinstance(manifest, dict)
        or manifest.get("artifact_type") != MANIFEST_ARTIFACT_TYPE
        or manifest.get("generation") != generation
        or not isinstance(manifest.get("files"), list)
        or not isinstance(manifest.get("runtime_fingerprint"), dict)
    ):
        raise SyncError(f"{session}/{generation}: manifest identity is invalid")
    files: list[dict[str, Any]] = []
    total = 0
    seen: set[str] = set()
    for entry in manifest["files"]:
        if (
            not isinstance(entry, dict) or not valid_manifest_path(entry.get("path"))
            or not isinstance(entry.get("bytes"), int) or entry["bytes"] < 0
            or not isinstance(entry.get("sha256"), str)
            or not SHA256_RE.fullmatch(entry["sha256"]) or entry["path"] in seen
        ):
            raise SyncError(f"{session}/{generation}: manifest file descriptor is invalid")
        seen.add(entry["path"])
        payload = directory / Path(*PurePosixPath(entry["path"]).parts)
        if not payload.is_file():
            raise SyncError(f"{session}/{generation}: payload {entry['path']} is missing")
        digest, size = sha256_file(payload)
        if size != entry["bytes"] or digest != entry["sha256"]:
            raise SyncError(f"{session}/{generation}: payload {entry['path']} does not match "
                            "its manifest digest")
        files.append({"path": entry["path"], "bytes": size, "sha256": digest})
        total += size
    tag_path = directory / "manifest.mac"
    origin_tag: str | None = None
    if tag_path.exists():
        if not tag_path.is_file() or tag_path.stat().st_size > 128:
            raise SyncError(f"{session}/{generation}: origin tag is not a regular file")
        origin_tag = tag_path.read_text(encoding="utf-8").rstrip("\r\n")
        if not SHA256_RE.fullmatch(origin_tag):
            raise SyncError(f"{session}/{generation}: origin tag is malformed")
    elif not allow_unauthenticated:
        raise SyncError(f"{session}/{generation}: generation carries no origin tag "
                        "(manifest.mac); refuse to replicate an unauthenticated checkpoint "
                        "across a trust boundary, or pass --allow-unauthenticated for a "
                        "locally produced legacy generation")
    return {
        "session": session,
        "generation": generation,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "manifest_bytes": len(manifest_bytes),
        "origin_tag": origin_tag,
        "runtime_fingerprint": manifest["runtime_fingerprint"],
        "latest_response_id": manifest.get("latest_response_id"),
        "frontier_tokens": manifest.get("frontier_tokens"),
        "files": files,
        "payload_bytes": total,
    }


def list_sessions(root: Path, requested: list[str]) -> list[str]:
    sessions_root = root / "sessions"
    if not sessions_root.is_dir():
        raise SyncError(f"{root}: no sessions directory")
    if requested:
        for name in requested:
            if not SESSION_RE.fullmatch(name):
                raise SyncError(f"session name {name!r} is invalid")
            if not (sessions_root / name).is_dir():
                raise SyncError(f"session {name} is not present under {root}")
        return sorted(set(requested))
    return sorted(entry.name for entry in sessions_root.iterdir()
                  if entry.is_dir() and SESSION_RE.fullmatch(entry.name))


def replicate_generation(source_root: Path, target_root: Path, descriptor: dict[str, Any],
                         force: bool) -> dict[str, Any]:
    """Copy one verified generation from source_root to target_root and publish it."""
    session, generation = descriptor["session"], descriptor["generation"]
    source = source_root / "sessions" / session / "generations" / generation
    target_session = target_root / "sessions" / session
    target = target_session / "generations" / generation
    outcome: dict[str, Any] = {"session": session, "generation": generation,
                               "payload_bytes": descriptor["payload_bytes"],
                               "files": len(descriptor["files"]),
                               "origin_tag_present": descriptor["origin_tag"] is not None}
    existing_current = read_current(target_session) if target_session.is_dir() else None
    if existing_current is not None and not force:
        if generation_order(existing_current) > generation_order(generation):
            raise SyncError(f"{session}: target current {existing_current} is newer than "
                            f"{generation}; pass --force to move current backwards")
    if target.is_dir():
        manifest_digest = hashlib.sha256((target / "manifest.json").read_bytes()).hexdigest() \
            if (target / "manifest.json").is_file() else None
        if manifest_digest != descriptor["manifest_sha256"]:
            raise SyncError(f"{session}/{generation}: target already holds a different "
                            "generation of the same name")
        outcome["copied"] = False
    else:
        # Stage outside every directory the runtime scans (sessions/, .tombstones), on the
        # same volume so the final publication is one rename.
        staging_root = target_root / ".sync-staging"
        staging_root.mkdir(parents=True, exist_ok=True)
        staging = staging_root / f"{session[:16]}-{generation}-{secrets.token_hex(4)}"
        try:
            staging.mkdir()
            for entry in descriptor["files"]:
                relative = Path(*PurePosixPath(entry["path"]).parts)
                copy_synced(source / relative, staging / relative)
                digest, size = sha256_file(staging / relative)
                if size != entry["bytes"] or digest != entry["sha256"]:
                    raise SyncError(f"{session}/{generation}: copy of {entry['path']} "
                                    "did not verify")
            if descriptor["origin_tag"] is not None:
                copy_synced(source / "manifest.mac", staging / "manifest.mac")
            copy_synced(source / "manifest.json", staging / "manifest.json")
            if hashlib.sha256((staging / "manifest.json").read_bytes()).hexdigest() \
                    != descriptor["manifest_sha256"]:
                raise SyncError(f"{session}/{generation}: manifest copy did not verify")
            for directory in sorted({p.parent for p in staging.rglob("*") if p.is_file()},
                                    key=lambda p: len(p.parts), reverse=True):
                fsync_path(directory)
            (target_session / "generations").mkdir(parents=True, exist_ok=True)
            os.replace(staging, target)
            fsync_path(target.parent)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        outcome["copied"] = True
    if existing_current != generation:
        write_synced(target_session / "current", (generation + "\n").encode("ascii"))
    outcome["current_before"] = existing_current
    outcome["current"] = generation
    return outcome


def run_sync(source_root: Path, target_root: Path, sessions: list[str],
             allow_unauthenticated: bool, force: bool) -> list[dict[str, Any]]:
    results = []
    for session in list_sessions(source_root, sessions):
        current = read_current(source_root / "sessions" / session)
        if current is None:
            results.append({"session": session, "skipped": "no published generation"})
            continue
        descriptor = verify_generation(source_root, session, current, allow_unauthenticated)
        results.append(replicate_generation(source_root, target_root, descriptor, force))
    return results


def run_verify(root: Path, sessions: list[str], allow_unauthenticated: bool) -> list[dict[str, Any]]:
    results = []
    for session in list_sessions(root, sessions):
        current = read_current(root / "sessions" / session)
        if current is None:
            results.append({"session": session, "skipped": "no published generation"})
            continue
        descriptor = verify_generation(root, session, current, allow_unauthenticated)
        results.append({k: v for k, v in descriptor.items() if k != "files"}
                       | {"files": len(descriptor["files"])})
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    def common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--session", action="append", default=[],
                         help="session directory name (repeatable; default: every session)")
        sub.add_argument("--allow-unauthenticated", action="store_true",
                         help="accept generations without manifest.mac (compatibility window)")
        sub.add_argument("--receipt", type=Path, help="write a JSON receipt")

    export = subparsers.add_parser("export", help="copy published generations to shared storage")
    export.add_argument("--root", type=Path, required=True, help="local checkpoint root")
    export.add_argument("--destination", type=Path, required=True, help="replica root")
    export.add_argument("--force", action="store_true",
                        help="replace a newer generation already in the destination")
    common(export)
    imp = subparsers.add_parser("import", help="copy generations back to a local checkpoint root")
    imp.add_argument("--source", type=Path, required=True, help="replica root")
    imp.add_argument("--root", type=Path, required=True, help="local checkpoint root")
    imp.add_argument("--force", action="store_true",
                     help="replace a newer generation already in the local root")
    common(imp)
    verify = subparsers.add_parser("verify", help="verify published generations in place")
    verify.add_argument("--root", type=Path, required=True)
    common(verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    receipt: dict[str, Any] = {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "operation": args.command,
        "started_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "allow_unauthenticated": args.allow_unauthenticated,
    }
    try:
        if args.command == "export":
            receipt["source_root"] = str(args.root.resolve())
            receipt["target_root"] = str(args.destination.resolve())
            receipt["results"] = run_sync(args.root, args.destination, args.session,
                                          args.allow_unauthenticated, args.force)
        elif args.command == "import":
            receipt["source_root"] = str(args.source.resolve())
            receipt["target_root"] = str(args.root.resolve())
            receipt["results"] = run_sync(args.source, args.root, args.session,
                                          args.allow_unauthenticated, args.force)
        else:
            receipt["root"] = str(args.root.resolve())
            receipt["results"] = run_verify(args.root, args.session, args.allow_unauthenticated)
        receipt["status"] = "passed"
    except (SyncError, OSError) as error:
        receipt["status"] = "failed"
        receipt["error"] = str(error)
    receipt["finished_utc"] = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
