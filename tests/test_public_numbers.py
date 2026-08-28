"""Public headline numbers must match the qualification receipts.

The README and benchmarks page quote measured values (and encode two of them in
badges). Release policy forbids benchmark values that are not present in the
public qualification summary, so drift between prose and receipts is a release
defect, not a typo.
"""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUALIFICATION = ROOT / "releases" / "v0.1.0-beta.1" / "qualification.json"
MANIFEST = ROOT / "releases" / "v0.1.0-beta.1" / "manifest.json"
README = ROOT / "README.md"
BENCHMARKS = ROOT / "docs" / "BENCHMARKS.md"


class PublicNumbersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gates = json.loads(QUALIFICATION.read_text(encoding="utf-8"))["observed_gates"]
        cls.runtime = json.loads(MANIFEST.read_text(encoding="utf-8"))["runtime_identity"]
        cls.readme = README.read_text(encoding="utf-8")
        cls.benchmarks = BENCHMARKS.read_text(encoding="utf-8")

    def assert_in_both(self, needle: str) -> None:
        for name, source in (("README.md", self.readme), ("docs/BENCHMARKS.md", self.benchmarks)):
            self.assertIn(needle, source, f"{name} must quote {needle!r} from the receipts")

    def test_decode_throughput_matches_receipt(self) -> None:
        tokens_per_second = self.gates["decode_throughput"]["tokens_per_second"]
        self.assert_in_both(f"{tokens_per_second:.2f} tok/s")
        self.assertIn(f"decode-{round(tokens_per_second)}%20tok", self.readme,
                      "README decode badge must match the qualified value")

    def test_mtp_acceptance_matches_receipt(self) -> None:
        gate = self.gates["mtp_acceptance"]
        self.assert_in_both(f"{gate['rate'] * 100:.1f}%")
        self.assertIn(
            f"{gate['accepted_tokens']:,} of {gate['drafted_tokens']:,} drafted",
            self.benchmarks,
            "benchmarks page must carry the accepted/drafted counts",
        )

    def test_long_context_matches_receipt(self) -> None:
        gate = self.gates["long_context"]
        self.assert_in_both(f"{gate['prompt_tokens']:,}-token")
        self.assertTrue(gate["exact_output_match"])

    def test_prefix_cache_matches_receipt(self) -> None:
        tokens = self.gates["stateful_responses"]["maximum_prefix_cache_hit_tokens"]
        self.assert_in_both(f"{tokens:,}-token")

    def test_context_ceiling_matches_manifest(self) -> None:
        ceiling = self.runtime["maximum_context_tokens"]
        self.assert_in_both(f"{ceiling:,}-token")


if __name__ == "__main__":
    unittest.main()
