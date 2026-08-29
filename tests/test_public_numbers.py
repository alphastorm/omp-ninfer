"""Public v0.2 headline numbers must match the active qualification receipts."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
BENCHMARKS = ROOT / "docs" / "BENCHMARKS.md"


class PublicNumbersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        authority = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))
        cls.release = authority["product_release"]
        release_root = ROOT / "releases" / cls.release
        cls.qualification = json.loads(
            (release_root / "qualification" / "rtx5090.json").read_text(encoding="utf-8")
        )
        cls.profile = json.loads(
            (ROOT / "profiles" / "qwen38-rtx5090-windows-docker-local.json").read_text(
                encoding="utf-8"
            )
        )
        cls.readme = README.read_text(encoding="utf-8")
        cls.benchmarks = BENCHMARKS.read_text(encoding="utf-8")

    def assert_in_both(self, needle: str) -> None:
        for name, source in (("README.md", self.readme), ("docs/BENCHMARKS.md", self.benchmarks)):
            self.assertIn(needle, source, f"{name} must quote {needle!r} from the receipts")

    def test_decode_throughput_matches_receipt(self) -> None:
        gate = self.qualification["gates"]["decode"]
        tokens_per_second = gate["decode_tokens_per_second"]
        self.assert_in_both(f"{tokens_per_second:.2f} tok/s")
        self.assertIn(
            f"decode-{round(tokens_per_second)}%20tok",
            self.readme,
            "README decode badge must match the qualified value",
        )

    def test_mtp_acceptance_matches_receipt(self) -> None:
        gate = self.qualification["gates"]["decode"]
        self.assert_in_both(f"{gate['mtp_acceptance_rate'] * 100:.2f}%")
        self.assertIn(
            f"{gate['accepted_tokens']:,} of {gate['drafted_tokens']:,}",
            self.benchmarks,
        )

    def test_long_context_matches_receipt(self) -> None:
        points = self.qualification["gates"]["prefill_curve"]["points"]
        longest = max(points, key=lambda item: item["prompt_tokens"])
        self.assert_in_both(f"{longest['prompt_tokens']:,}")
        self.assertIn(f"{longest['tokens_per_second']:,.2f} tok/s", self.benchmarks)
        self.assertTrue(self.qualification["gates"]["prefill_curve"]["exact_retrieval_at_every_point"])

    def test_context_ceiling_matches_profile(self) -> None:
        ceiling = self.profile["omp_provider"]["context_window"]
        self.assert_in_both(f"{ceiling:,}")

    def test_packaged_source_identity_is_authoritative(self) -> None:
        interpretation = self.qualification["evidence_interpretation"]
        self.assertTrue(interpretation["packaged_build_identity_authoritative"])
        self.assertFalse(interpretation["documentation_benchmark_source_field_credited"])
        self.assertEqual(
            self.qualification["identity"]["source_commit"],
            "6efa06505da0a439fd046dc8e2ed04554f286bf2",
        )


if __name__ == "__main__":
    unittest.main()
