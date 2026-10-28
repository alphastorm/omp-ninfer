"""A corrected 5090 attempt carries its corrections before it spends a window."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("accept_rtx5090_routes",
                                              ROOT / "scripts" / "hosts" / "accept-rtx5090-routes.py")
assert SPEC is not None and SPEC.loader is not None
DRIVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER)


class CorrectionRecordTests(unittest.TestCase):
    def write(self, directory: str, value: object) -> None:
        (Path(directory) / "corrections.json").write_text(json.dumps(value))

    def test_records_written_before_the_window_are_carried_into_the_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            record = {"route": "host", "change": "the documented route printed the marker twice"}
            self.write(directory, [record])
            self.assertEqual(DRIVER.correction_records(directory), [record])

    def test_a_corrected_attempt_is_refused_without_usable_records(self) -> None:
        cases = {
            "missing": None,
            "empty": [],
            "not a list": {"route": "host", "change": "x"},
            "record is not an object": ["host printed the marker twice"],
            "route missing": [{"change": "the documented route printed the marker twice"}],
            "change blank": [{"route": "host", "change": "  "}],
            "change not a string": [{"route": "host", "change": ["twice"]}],
        }
        for label, value in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as directory:
                if value is not None:
                    self.write(directory, value)
                with self.assertRaises(AssertionError):
                    DRIVER.correction_records(directory)


if __name__ == "__main__":
    unittest.main()
