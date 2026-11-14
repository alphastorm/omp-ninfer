"""A release tool's interrupted write must leave the previous document intact."""
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_io", ROOT / "scripts" / "release_io.py")
assert SPEC is not None and SPEC.loader is not None
release_io = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_io)


class AtomicWriteTests(unittest.TestCase):
    def test_a_failed_replace_keeps_the_previous_bytes_and_leaves_no_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "authority.json"
            target.write_text('{"release": "previous"}\n', encoding="utf-8")
            with (mock.patch.object(os, "replace", side_effect=OSError("disk full")),
                  self.assertRaises(OSError)):
                release_io.atomic_write_json(target, {"release": "next"})
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"release": "previous"})
            self.assertEqual([path.name for path in Path(temporary).iterdir()], ["authority.json"])

    def test_json_documents_use_the_release_tree_form(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "nested" / "manifest.json"
            release_io.atomic_write_json(target, {"status": "draft", "items": [1]})
            self.assertEqual(target.read_bytes(),
                             b'{\n  "status": "draft",\n  "items": [\n    1\n  ]\n}\n')


class AtomicCopyTests(unittest.TestCase):
    def test_multichunk_copy_matches_without_aliasing_the_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.bin"
            destination = Path(temporary) / "nested" / "copied.bin"
            payload = bytes(range(256)) * 8193
            release_io.atomic_write(source, payload)
            release_io.atomic_copy(source, destination)
            self.assertEqual(destination.read_bytes(), payload)
            release_io.atomic_write(destination, b"changed copy")
            self.assertEqual(source.read_bytes(), payload)
            self.assertEqual([path.name for path in destination.parent.iterdir()], ["copied.bin"])

    def test_interrupted_copy_keeps_existing_or_absent_destination(self) -> None:
        for exists in (False, True):
            with self.subTest(exists=exists), tempfile.TemporaryDirectory() as temporary:
                source = Path(temporary) / "source.bin"
                destination = Path(temporary) / "copied.bin"
                release_io.atomic_write(source, b"source")
                if exists:
                    release_io.atomic_write(destination, b"previous")
                reader = mock.MagicMock()
                reader.__enter__.return_value = reader
                reader.read.side_effect = [b"x" * (1024 * 1024), OSError("copy interrupted")]
                with (mock.patch.object(Path, "open", return_value=reader),
                      self.assertRaisesRegex(OSError, "copy interrupted")):
                    release_io.atomic_copy(source, destination)
                self.assertEqual(reader.read.call_args_list,
                                 [mock.call(1024 * 1024), mock.call(1024 * 1024)])
                if exists:
                    self.assertEqual(destination.read_bytes(), b"previous")
                else:
                    self.assertFalse(destination.exists())
                self.assertEqual(sorted(path.name for path in Path(temporary).iterdir()),
                                 ["copied.bin", "source.bin"] if exists else ["source.bin"])

    def test_existing_destination_changes_only_at_the_replace_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.bin"
            destination = Path(temporary) / "copied.bin"
            payload = b"next" * (1024 * 1024)
            release_io.atomic_write(source, payload)
            release_io.atomic_write(destination, b"previous")
            replace = os.replace
            observations = []

            def replace_after_inspection(temporary_path, target):
                observations.append(destination.read_bytes())
                self.assertEqual(Path(temporary_path).read_bytes(), payload)
                replace(temporary_path, target)

            with mock.patch.object(os, "replace", side_effect=replace_after_inspection):
                release_io.atomic_copy(source, destination)
            self.assertEqual(observations, [b"previous"])
            self.assertEqual(destination.read_bytes(), payload)
            self.assertEqual(sorted(path.name for path in Path(temporary).iterdir()),
                             ["copied.bin", "source.bin"])


if __name__ == "__main__":
    unittest.main()
