"""Selected profiles remain compatible with decision-bound native speed admissions."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import unittest

import test_native_gate_decisions as fixture


class ProfileSpeedAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.NativeDecisionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def screen(self, *, screen_profiles=False):
        f = self.fixture
        gate, captures, path = f.screen_fixture()
        baseline = "native-v0.8.0-beta.2-rtx4090"
        selected = "native-v0.8.0-beta.3-tc-a8-rtx4090"
        gate["comparator"]["build_profile"] = baseline
        for capture in captures:
            capture["identity"]["build_profile"] = baseline if capture["arm"] == "A" else selected
        if screen_profiles:
            value = json.loads(path.read_text(encoding="utf-8"))
            for role in ("production", "production_determinism", "candidate", "candidate_determinism"):
                value["runs"][role]["arm"]["build_profile"] = (
                    baseline if role.startswith("production") else selected)
            self.bind_screen(gate, path, value)
        fixture.record_decision(f.root, gate)
        candidate = fixture.SPEED.arm_identity({
            **captures[1]["identity"],
            "configuration_sha256": fixture.SPEED.digest(captures[1]["identity"]["config"])})
        plan = fixture.SPEED.prescreen(gate, candidate)
        return gate, captures, path, plan

    def bind_screen(self, gate, path, value):
        path.write_text(json.dumps(value), encoding="utf-8")
        gate["decision"]["quality_screens"][0]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        fixture.record_decision(self.fixture.root, gate)

    def test_variant_with_profile_passes_its_bound_screen_with_or_without_screen_profile(self):
        for recorded in (False, True):
            with self.subTest(screen_profiles=recorded):
                gate, captures, _, plan = self.screen(screen_profiles=recorded)
                result = fixture.SPEED.reduce(gate, captures, plan)
                self.assertEqual(result["status"], "PASS", result["diagnostic_reasons"])
                self.assertTrue(result["output_rule_passed"])
                self.assertFalse(result["normalized_outputs_identical"])

    def test_bound_screen_digest_or_recorded_profile_mismatch_still_fails(self):
        for field in ("server_binary_sha256", "configuration_sha256", "build_profile"):
            with self.subTest(field=field):
                gate, captures, path, plan = self.screen(screen_profiles=True)
                value = json.loads(path.read_text(encoding="utf-8"))
                for role in ("candidate", "candidate_determinism"):
                    value["runs"][role]["arm"][field] = (
                        "native-v0.8.0-beta.3-a8-rtx4090" if field == "build_profile" else "f" * 64)
                self.bind_screen(gate, path, value)
                plan = fixture.SPEED.prescreen(gate, plan["arms"]["B"])
                result = fixture.SPEED.reduce(gate, captures, plan)
                self.assertEqual(result["status"], "FAIL")
                self.assertFalse(result["gate_passed"])
                self.assertFalse(result["output_rule_passed"])

    def test_default_identity_proof_admits_profiles_recorded_on_either_or_both_sides(self):
        proof, gate, _, _, spec, variant, predecessor, _ = self.fixture.identity_proof()
        profiles = {"A": "native-v0.8.0-beta.2-rtx4090", "B": spec["build_profile"]}
        for recorded in ("arms-only", "plan-only", "one-arm-only", "both"):
            with self.subTest(recorded=recorded):
                value = deepcopy(proof)
                if recorded != "plan-only":
                    for arm in value["speed_abba"]["arms"]:
                        if recorded != "one-arm-only" or arm["index"] == 1:
                            arm["identity"]["build_profile"] = profiles[arm["arm"]]
                if recorded in ("plan-only", "both"):
                    declaration = value["speed_abba"]["declaration"]
                    declaration["comparator"]["build_profile"] = profiles["A"]
                    candidate = {**value["speed_abba"]["arms"][1]["identity"],
                                 "build_profile": profiles["B"]}
                    value["speed_abba"]["plan"] = fixture.SPEED.prescreen(declaration, candidate)
                fixture.SPEED.validate_identity_proof(
                    value, self.fixture.root, gate["release"],
                    {**variant, "build_profile": profiles["B"]},
                    {**predecessor, "build_profile": profiles["A"]}, spec)

    def test_identity_proof_refuses_variant_profiles_and_recorded_profile_disagreement(self):
        proof, gate, _, _, spec, variant, predecessor, _ = self.fixture.identity_proof()
        for profile in ("native-v0.9.0-beta.1-a8-rtx4090", "native-v0.9.0-beta.1-tc-rtx4090",
                        "native-v0.9.0-beta.1-tc-a8-rtx4090"):
            with self.subTest(profile=profile), self.assertRaises(fixture.SPEED.SpeedGateError):
                fixture.SPEED.validate_identity_proof(
                    proof, self.fixture.root, gate["release"], {**variant, "build_profile": profile},
                    predecessor, {**spec, "build_profile": profile})
        for field in ("binary_sha256", "configuration_sha256", "build_profile"):
            value = deepcopy(proof)
            for arm in value["speed_abba"]["arms"][1:3]:
                arm["identity"][field] = (
                    "native-v0.9.0-beta.1-a8-rtx4090" if field == "build_profile" else "f" * 64)
            with self.subTest(field=field), self.assertRaises(fixture.SPEED.SpeedGateError):
                fixture.SPEED.validate_identity_proof(
                    value, self.fixture.root, gate["release"],
                    {**variant, "build_profile": spec["build_profile"]}, predecessor, spec)
