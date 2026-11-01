"""Content-safe native speed-gate fixtures; no runtime or hardware is started."""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import speed_gate as SPEED


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def fixture():
    configs = {"A": {"speculative": {"backend": "mtp", "draft_tokens": 3}},
               "B": {"speculative": {"backend": "dflash2", "draft_tokens": 7}}}
    suite = [{"id": "log-024@0", "request_sha256": "1" * 64},
             {"id": "role-002@0", "request_sha256": "2" * 64}]
    gate = {"artifact_type": "omp_ninfer_speed_gate", "schema_version": 1,
            "comparator": {"binary_sha256": "a" * 64, "configuration_sha256": digest(configs["A"])},
            "request_suite": suite, "request_suite_sha256": digest(suite),
            "role_case_ids": [row["id"] for row in suite]}
    captures = []
    for index, label in enumerate(("A", "B", "B", "A")):
        captures.append({"arm": label, "index": index, "status": "passed",
                         "identity": {"binary_sha256": ("a" if label == "A" else "b") * 64,
                                      "config": deepcopy(configs[label])},
                         "requests": [{**row, "completion_tokens": 1024, "decode_seconds": 1024 / rate}
                                      for row, rate in zip(suite, (100, 100) if label == "A" else (110, 120))]})
    return gate, captures


class SpeedGateTests(unittest.TestCase):
    def test_candidate_binary_mtp_prescreen_is_diagnostic_not_gate_predictive(self):
        # P16's shape: MTP3 uses the candidate binary, not the shipped incumbent.
        # The isolated case clears 0.95 at ~130.55 / 135.55, unlike the final
        # incumbent comparison (~130.19 / 139.41). Other cases lift the aggregate.
        gate, captures = fixture()
        for arm in captures:
            arm["identity"]["binary_sha256"] = "b" * 64
            rates = (135.55, 100) if arm["arm"] == "A" else (130.55, 200)
            for row, rate in zip(arm["requests"], rates):
                row["decode_seconds"] = row["completion_tokens"] / rate
        result = SPEED.reduce(gate, captures)
        self.assertGreater(result["all_cases"]["weighted_decode_ratio"], 1.08)
        self.assertGreater(result["all_cases"]["minimum_case_ratio"], 0.95)
        self.assertEqual(result["status"], "DIAGNOSTIC")
        self.assertFalse(result["gate_predictive"])
        self.assertIn("binary_sha256", " ".join(result["diagnostic_reasons"]))


if __name__ == "__main__":
    unittest.main()
