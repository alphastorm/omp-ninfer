"""Measurement records are read by tools, so their declared fields keep their JSON types."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MeasurementRecordTests(unittest.TestCase):
    def test_schema_version_is_an_integer_and_raw_content_flags_are_booleans(self) -> None:
        """EXP-070 to EXP-072 were written with "1" and "False". A reader that tests the flag takes
        the string "False" as true and would treat those records as carrying raw prompts or secrets."""
        for path in sorted((ROOT / "docs" / "measurements").glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(record, dict):
                continue
            with self.subTest(path=path.name):
                if "schema_version" in record:
                    self.assertIs(type(record["schema_version"]), int)
                for key, value in record.items():
                    if key.startswith("raw_") and key.endswith("_included"):
                        self.assertIs(type(value), bool, key)


if __name__ == "__main__":
    unittest.main()
