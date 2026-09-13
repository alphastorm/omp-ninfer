"""The active qualification must bind the packaged runtime source, not documentation metadata."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PublicNumbersTests(unittest.TestCase):
    def test_packaged_source_identity_is_authoritative(self) -> None:
        authority = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))
        release_root = ROOT / "releases" / authority["product_release"]
        qualification = json.loads(
            (release_root / "qualification" / "rtx5090.json").read_text(encoding="utf-8")
        )
        interpretation = qualification["evidence_interpretation"]
        self.assertTrue(interpretation["packaged_build_identity_authoritative"])
        self.assertFalse(interpretation["documentation_benchmark_source_field_credited"])
        manifest = json.loads((release_root / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(
            qualification["identity"]["source_commit"],
            manifest["components"]["ninfer"]["source_commit"],
        )


if __name__ == "__main__":
    unittest.main()
