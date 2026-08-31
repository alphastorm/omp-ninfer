"""Public v0.2 headline numbers must match the active qualification receipts."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
BENCHMARKS = ROOT / "docs" / "BENCHMARKS.md"


class PublicNumbersTests(unittest.TestCase):
    def test_predecessor_prefix_hit_is_not_rebound_to_v02(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        performance = (ROOT / "docs" / "PERFORMANCE.md").read_text(encoding="utf-8")
        if "37,591" in readme:
            self.assertIn("predecessor v0.1 campaign", readme)
            self.assertIn("not rebind that numeric result", readme)
        self.assertIn("not rebound as a v0.2 numeric claim", performance)

    @classmethod
    def setUpClass(cls) -> None:
        authority = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))
        cls.release = authority["product_release"]
        release_root = ROOT / "releases" / cls.release
        receipt = release_root / "qualification" / "rtx5090.json"
        if not receipt.is_file():
            manifest = json.loads((release_root / "manifest.json").read_text(encoding="utf-8"))
            if manifest.get("status") != "draft":
                raise AssertionError(
                    f"{cls.release} is {manifest.get('status')!r} but carries no rtx5090 receipt"
                )
            qualified = sorted(
                path
                for path in (ROOT / "releases").iterdir()
                if (path / "qualification" / "rtx5090.json").is_file()
            )
            if not qualified:
                raise AssertionError("no release carries an rtx5090 qualification receipt")
            receipt = qualified[-1] / "qualification" / "rtx5090.json"
        cls.qualification = json.loads(receipt.read_text(encoding="utf-8"))
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
        if "accepted_tokens" in gate and "drafted_tokens" in gate:
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

    def test_warm_cold_measurement_matches_receipt(self) -> None:
        for name in (
            "2026-08-29-warm-vs-cold-ttft.json",
            "2026-08-30-warm-vs-cold-ttft-v03.json",
            "2026-08-30-warm-vs-cold-v04.json",
        ):
            receipt = json.loads(
                (ROOT / "docs" / "measurements" / name).read_text(encoding="utf-8")
            )
            for row in receipt["results"]:
                self.assertIn(f"{row['session_input_tokens']:,}", self.benchmarks)
                self.assertIn(f"{row['warm_ttft_s']:.3f} s", self.benchmarks)
                self.assertIn(f"{row['cold_ttft_s']:.3f} s", self.benchmarks)
        current = json.loads(
            (ROOT / "docs" / "measurements" / "2026-08-30-warm-vs-cold-v04.json").read_text(
                encoding="utf-8"
            )
        )
        largest = max(current["results"], key=lambda row: row["session_input_tokens"])
        self.assertIn(f"{largest['warm_ttft_s']:.3f} s", self.readme)

    def test_packaged_source_identity_is_authoritative(self) -> None:
        interpretation = self.qualification["evidence_interpretation"]
        self.assertTrue(interpretation["packaged_build_identity_authoritative"])
        self.assertFalse(interpretation["documentation_benchmark_source_field_credited"])
        self.assertEqual(
            self.qualification["identity"]["source_commit"],
            "51fd30e5427bd8115ca71c5b20c86fdfbfdf988e",
        )


if __name__ == "__main__":
    unittest.main()
