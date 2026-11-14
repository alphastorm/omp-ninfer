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


if __name__ == "__main__":
    unittest.main()
