"""checkpoint_sync replicates only verified, published generations and fails closed."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("checkpoint_sync", ROOT / "scripts" / "checkpoint_sync.py")
assert SPEC is not None and SPEC.loader is not None
SYNC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNC)

SESSION = "a" * 64
OTHER = "b" * 64


def plant_generation(root: Path, session: str, generation: str, *, tag: bool = True,
                     payload: bytes = b"kv-pages" * 4096, current: bool = True) -> Path:
    directory = root / "sessions" / session / "generations" / generation
    (directory / "engine").mkdir(parents=True)
    responses = b"\xa1\x63abc\x01"
    (directory / "responses.cbor").write_bytes(responses)
    (directory / "engine" / "text-kv.bin").write_bytes(payload)
    manifest = {
        "artifact_type": "ninfer_session_checkpoint",
        "schema_version": 2,
        "generation": generation,
        "runtime_fingerprint": {"deployment_profile": "qwen38-test", "binary_sha256": "0" * 64},
        "latest_response_id": "resp_test",
        "frontier_tokens": 1234,
        "files": [
            {"path": "responses.cbor", "bytes": len(responses),
             "sha256": hashlib.sha256(responses).hexdigest()},
            {"path": "engine/text-kv.bin", "bytes": len(payload),
             "sha256": hashlib.sha256(payload).hexdigest()},
        ],
    }
    (directory / "manifest.json").write_bytes(json.dumps(manifest).encode())
    if tag:
        (directory / "manifest.mac").write_text("c" * 64 + "\n")
    if current:
        (root / "sessions" / session / "current").write_text(generation + "\n")
    return directory


class CheckpointSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "store"
        self.replica = Path(self.temporary.name) / "replica"
        self.restored = Path(self.temporary.name) / "restored"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_export_copies_exactly_the_published_generation(self) -> None:
        plant_generation(self.root, SESSION, "1700000000000-0")
        # Noise the runtime never publishes: staging, quarantine, tombstones, stray files.
        (self.root / "sessions" / SESSION / "generations" / ".staging-x").mkdir()
        (self.root / "sessions" / SESSION / "generations" / "1700000000000-0.corrupt-1").mkdir()
        (self.root / ".tombstones").mkdir()
        (self.root / "sessions" / SESSION / "generations" / "1700000000000-0" / "stray.tmp").write_text("x")
        results = SYNC.run_sync(self.root, self.replica, [], False, False)
        self.assertEqual(results[0]["copied"], True)
        copied = self.replica / "sessions" / SESSION / "generations" / "1700000000000-0"
        self.assertEqual(sorted(p.relative_to(copied).as_posix() for p in copied.rglob("*") if p.is_file()),
                         ["engine/text-kv.bin", "manifest.json", "manifest.mac", "responses.cbor"])
        self.assertEqual((self.replica / "sessions" / SESSION / "current").read_text(), "1700000000000-0\n")
        self.assertFalse((self.replica / ".tombstones").exists())
        self.assertFalse(list((self.replica / ".sync-staging").iterdir()))

    def test_round_trip_survives_local_state_loss(self) -> None:
        source = plant_generation(self.root, SESSION, "1700000000000-0")
        original = {p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob("*") if p.is_file()}
        SYNC.run_sync(self.root, self.replica, [], False, False)
        shutil.rmtree(self.root)
        results = SYNC.run_sync(self.replica, self.root, [SESSION], False, False)
        self.assertEqual(results[0]["current"], "1700000000000-0")
        restored = self.root / "sessions" / SESSION / "generations" / "1700000000000-0"
        self.assertEqual({p.relative_to(restored).as_posix(): p.read_bytes()
                          for p in restored.rglob("*") if p.is_file()}, original)
        self.assertEqual(SYNC.run_verify(self.root, [], False)[0]["origin_tag"], "c" * 64)

    def test_tampered_payload_is_refused(self) -> None:
        plant_generation(self.root, SESSION, "1700000000000-0")
        SYNC.run_sync(self.root, self.replica, [], False, False)
        payload = self.replica / "sessions" / SESSION / "generations" / "1700000000000-0" / "engine" / "text-kv.bin"
        data = bytearray(payload.read_bytes())
        data[100] ^= 0x01
        payload.write_bytes(data)
        with self.assertRaisesRegex(SYNC.SyncError, "does not match its manifest digest"):
            SYNC.run_sync(self.replica, self.restored, [], False, False)
        self.assertFalse((self.restored / "sessions").exists())

    def test_unauthenticated_generation_needs_explicit_window(self) -> None:
        plant_generation(self.root, SESSION, "1700000000000-0", tag=False)
        with self.assertRaisesRegex(SYNC.SyncError, "no origin tag"):
            SYNC.run_sync(self.root, self.replica, [], False, False)
        results = SYNC.run_sync(self.root, self.replica, [], True, False)
        self.assertFalse(results[0]["origin_tag_present"])

    def test_current_never_moves_backwards_without_force(self) -> None:
        plant_generation(self.root, SESSION, "1700000000000-0")
        SYNC.run_sync(self.root, self.replica, [], False, False)
        plant_generation(self.root, SESSION, "1700000000001-0")
        with self.assertRaisesRegex(SYNC.SyncError, "newer than"):
            SYNC.run_sync(self.replica, self.root, [], False, False)
        self.assertEqual((self.root / "sessions" / SESSION / "current").read_text(), "1700000000001-0\n")
        results = SYNC.run_sync(self.replica, self.root, [], False, True)
        self.assertEqual(results[0]["current_before"], "1700000000001-0")
        self.assertEqual((self.root / "sessions" / SESSION / "current").read_text(), "1700000000000-0\n")

    def test_reimport_is_idempotent_and_name_collisions_are_refused(self) -> None:
        plant_generation(self.root, SESSION, "1700000000000-0")
        SYNC.run_sync(self.root, self.replica, [], False, False)
        again = SYNC.run_sync(self.root, self.replica, [], False, False)
        self.assertEqual(again[0]["copied"], False)
        other = Path(self.temporary.name) / "other"
        plant_generation(other, SESSION, "1700000000000-0", payload=b"different" * 4096)
        with self.assertRaisesRegex(SYNC.SyncError, "different generation of the same name"):
            SYNC.run_sync(other, self.replica, [], False, False)

    def test_manifest_paths_are_confined(self) -> None:
        directory = plant_generation(self.root, SESSION, "1700000000000-0")
        manifest = json.loads((directory / "manifest.json").read_text())
        manifest["files"][0]["path"] = "../escape.bin"
        (directory / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(SYNC.SyncError, "descriptor is invalid"):
            SYNC.run_verify(self.root, [], False)

    def test_cli_receipt_and_exit_codes(self) -> None:
        plant_generation(self.root, SESSION, "1700000000000-0")
        receipt = Path(self.temporary.name) / "receipt.json"
        code = SYNC.main(["export", "--root", str(self.root), "--destination", str(self.replica),
                          "--receipt", str(receipt)])
        self.assertEqual(code, 0)
        document = json.loads(receipt.read_text())
        self.assertEqual(document["status"], "passed")
        self.assertEqual(document["results"][0]["generation"], "1700000000000-0")
        code = SYNC.main(["import", "--source", str(self.replica), "--root", str(self.root),
                          "--session", OTHER])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
