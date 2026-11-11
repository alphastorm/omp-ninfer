"""Native speed plans/results retain explicitly observed build-profile variants."""
from __future__ import annotations

from copy import deepcopy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import test_speed_gate as fixture


class ProfileSpeedIdentityTests(unittest.TestCase):
    def test_plan_and_measured_abba_result_keep_selected_profiles(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
                fixture.SPEED, "ROOT", Path(temporary)):
            gate, captures = fixture.fixture()
            baseline = "native-v0.8.0-beta.2-rtx4090"
            selected = "native-v0.8.0-beta.3-tc-a8-rtx4090"
            gate["comparator"]["build_profile"] = baseline
            for capture in captures:
                capture["identity"]["build_profile"] = baseline if capture["arm"] == "A" else selected
            candidate = {"binary_sha256": captures[1]["identity"]["binary_sha256"],
                         "configuration_sha256": fixture.digest(captures[1]["identity"]["config"]),
                         "build_profile": selected}
            plan = fixture.SPEED.prescreen(gate, candidate)
            result = fixture.SPEED.reduce(gate, captures, plan)
            self.assertEqual(plan["arms"]["B"].get("build_profile"), selected)
            self.assertEqual(result["comparator"].get("build_profile"), baseline)
            self.assertEqual(result["arms"][1]["identity"].get("build_profile"), selected)
            self.assertEqual(result["status"], "PASS")
            wrong = deepcopy(captures)
            wrong[2]["identity"]["build_profile"] = "native-v0.8.0-beta.3-rtx4090"
            refused = fixture.SPEED.reduce(gate, wrong, plan)
            self.assertEqual(refused["status"], "DIAGNOSTIC")
            self.assertTrue(any("build_profile" in reason for reason in refused["diagnostic_reasons"]))
