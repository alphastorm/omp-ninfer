"""Decision-scoped native speed and identity admissions; no hardware is contacted."""
from __future__ import annotations

from copy import deepcopy
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from test_speed_gate import ROOT, SCREEN_RULE, SPEED, fixture, plan_for, record_decision

IDENTITY_RULE = "speed-ABBA byte identity and 80/80 sealed incumbent determinism byte identity"
SAME_PROFILE_BUILD_RULE = "default-or-same-profile-published-incumbent"


def identity_fixture(root, *, lane="rtx4090", profile_variant="", incumbent_variant=None):
    """Synthetic retained outputs with real frozen prompt membership, never release evidence."""
    from quality_screen import FROZEN_SCREEN_IDS, FROZEN_DETERMINISM_MEMBERSHIP
    gate, captures = fixture()
    screen = json.loads(
        (ROOT / "releases/v0.16.0/qualification/rtx4090-windows-native.quality-screen.json").read_text())
    directories = []
    identities = []
    for role, index in (("production", 0), ("candidate", 1)):
        directory = root / role
        directory.mkdir(exist_ok=True)
        arm = deepcopy(screen["runs"][role + "_determinism"]["arm"])
        arm.update(server_binary_sha256=captures[index]["identity"]["binary_sha256"],
                   configuration_sha256=SPEED.digest(captures[index]["identity"]["config"]),
                   lane=lane, gpu_name="NVIDIA GeForce RTX " + lane[3:],
                   release_id=f"qwen38-{lane[3:]}-native-v0.8.0-beta.3")
        (directory / "arm.json").write_text(json.dumps(arm), encoding="utf-8")
        rows = [{"case_id": case, "content": "retained " + case, "reasoning": "",
                 "tool_calls": [], "error": None} for case in FROZEN_SCREEN_IDS[:80]]
        (directory / "responses.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        directories.append(directory)
        identities.append({key: arm[key] for key in (
            "package_sha256", "server_binary_sha256", "configuration_sha256", "model_artifact_sha256")})
    suffix = f"-{profile_variant}" if profile_variant else ""
    spec = {"lane": lane, "build_profile": f"native-v0.9.0-beta.1{suffix}-{lane}"}
    decision = {
        "artifact_type": "omp_ninfer_founder_gate_decision", "schema_version": 1,
        "release": gate["release"], "rule": {"quality_admission": IDENTITY_RULE},
        "lanes": ["rtx3090", "rtx4090"],
        "sealed_incumbent_determinism": {lane: {
            "identity": identities[0], **FROZEN_DETERMINISM_MEMBERSHIP,
            "responses_sha256": hashlib.sha256((directories[0] / "responses.jsonl").read_bytes()).hexdigest(),
        }},
    }
    predecessor = identities[0]
    variant = {"id": lane + "-windows-native", **identities[1]}
    if profile_variant:
        incumbent_variant = profile_variant if incumbent_variant is None else incumbent_variant
        previous_suffix = f"-{incumbent_variant}" if incumbent_variant else ""
        predecessor = {
            **predecessor, "id": variant["id"],
            "release_tag": f"v0.8.0-qwen38-{lane[3:]}-beta.3",
            "build_profile": f"native-v0.8.0-beta.3{previous_suffix}-{lane}",
        }
        variant["build_profile"] = spec["build_profile"]
        decision["rule"]["build_variant"] = SAME_PROFILE_BUILD_RULE
        decision["sealed_incumbent_determinism"][lane].update(
            component=predecessor["release_tag"], build_profile=predecessor["build_profile"])
        previous_path = root / "releases/v0.98.0/manifest.json"
        previous_path.parent.mkdir(parents=True, exist_ok=True)
        previous_path.write_text(json.dumps({
            "status": "ready", "components": {"ninfer_variants": [predecessor]},
        }), encoding="utf-8")
    path = root / "releases" / gate["release"] / "qualification/native-identity-decision.json"
    path.write_text(json.dumps(decision), encoding="utf-8")
    qual_path = path.parent.parent / "qualification.json"
    qualification = json.loads(qual_path.read_text())
    qualification["observed_gates"]["native_identity_decision"] = {
        "repository_path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    qual_path.write_text(json.dumps(qualification), encoding="utf-8")
    return gate, captures, directories, spec, variant, predecessor, path


class NativeDecisionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        patch = mock.patch.object(SPEED, "ROOT", self.root)
        patch.start()
        self.addCleanup(patch.stop)

    def screen_fixture(self):
        gate, captures = fixture()
        gate["lane"] = "rtx4090"
        gate["decision"]["rule"]["byte_identical_normalized_outputs"] = SCREEN_RULE
        gate["decision"]["rule"]["weighted_decode_ratio_minimum"] = 0.98
        screen = json.loads(
            (ROOT / "releases/v0.16.0/qualification/rtx4090-windows-native.quality-screen.json").read_text())
        for role, index in (("production", 0), ("production_determinism", 0),
                            ("candidate", 1), ("candidate_determinism", 1)):
            screen["runs"][role]["arm"].update(
                server_binary_sha256=captures[index]["identity"]["binary_sha256"],
                configuration_sha256=SPEED.digest(captures[index]["identity"]["config"]))
        path = self.root / "releases/v0.99.0/qualification/screen.json"
        path.write_text(json.dumps(screen), encoding="utf-8")
        gate["decision"]["quality_screens"] = [{
            "lane": "rtx4090", "repository_path": path.relative_to(self.root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}]
        for index in (1, 2):
            captures[index]["requests"][0]["normalized_output"] += " changed"
        record_decision(self.root, gate)
        return gate, captures, path

    def test_cross_engine_differences_require_a_bound_passing_lane_candidate_screen(self):
        gate, captures, path = self.screen_fixture()
        result = SPEED.reduce(gate, captures, plan_for(gate, captures))
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["normalized_outputs_identical"])
        self.assertTrue(result["within_engine_outputs_identical"])
        self.assertEqual(result["quality_screen_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_missing_failed_foreign_or_tampered_screen_never_admits_changed_outputs(self):
        for change in ("missing", "fail", "invalid", "lane", "candidate", "production", "tampered"):
            with self.subTest(change=change):
                gate, captures, path = self.screen_fixture()
                screen = json.loads(path.read_text())
                if change == "missing":
                    gate["decision"]["quality_screens"] = []
                elif change == "tampered":
                    path.write_bytes(path.read_bytes() + b"\n")
                else:
                    if change == "fail":
                        screen["verdict"] = "fail"
                    elif change == "invalid":
                        screen["validity"]["valid"] = False
                    elif change == "lane":
                        gate["decision"]["quality_screens"][0]["lane"] = "rtx3090"
                    else:
                        screen["runs"][change]["arm"]["server_binary_sha256"] = "f" * 64
                    path.write_text(json.dumps(screen), encoding="utf-8")
                    gate["decision"]["quality_screens"][0]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                record_decision(self.root, gate)
                result = SPEED.reduce(gate, captures, plan_for(gate, captures))
                self.assertEqual(result["status"], "FAIL")
                self.assertFalse(result["gate_passed"])

    def test_within_engine_determinism_remains_required_with_a_passing_screen(self):
        for index in range(4):
            with self.subTest(index=index):
                gate, captures, _ = self.screen_fixture()
                captures[index]["requests"][0]["normalized_output"] += " nondeterministic"
                result = SPEED.reduce(gate, captures, plan_for(gate, captures))
                self.assertEqual(result["status"], "FAIL")
                self.assertFalse(result["within_engine_outputs_identical"])

    def test_default_rule_still_refuses_screened_cross_engine_differences(self):
        gate, captures, _ = self.screen_fixture()
        gate["decision"]["rule"]["byte_identical_normalized_outputs"] = SPEED.OUTPUT_RULE
        record_decision(self.root, gate)
        result = SPEED.reduce(gate, captures, plan_for(gate, captures))
        self.assertEqual(result["status"], "FAIL")
        self.assertNotIn("quality_screen_sha256", result)

    def test_new_rule_without_cross_engine_differences_needs_no_screen(self):
        gate, captures, _ = self.screen_fixture()
        for index in (1, 2):
            captures[index]["requests"][0]["normalized_output"] = captures[0]["requests"][0]["normalized_output"]
        gate["decision"]["quality_screens"] = []
        record_decision(self.root, gate)
        self.assertEqual(SPEED.reduce(gate, captures, plan_for(gate, captures))["status"], "PASS")

    def test_screen_permission_does_not_relax_the_weighted_or_per_case_floor(self):
        for candidate_tokens, status in (((98, 98), "PASS"), ((97, 97), "FAIL"),
                                         ((95, 101), "PASS"), ((94, 110), "FAIL")):
            with self.subTest(candidate_tokens=candidate_tokens):
                gate, captures, _ = self.screen_fixture()
                for arm in captures:
                    tokens = (100, 100) if arm["arm"] == "A" else candidate_tokens
                    for row, count in zip(arm["requests"], tokens):
                        row.update(completion_tokens=count, decode_seconds=1)
                self.assertEqual(SPEED.reduce(gate, captures, plan_for(gate, captures))["status"], status)

    def identity_proof(self, **kwargs):
        gate, captures, directories, spec, variant, predecessor, path = identity_fixture(self.root, **kwargs)
        proof = SPEED.create_identity_proof(gate, captures, plan_for(gate, captures),
                                            *directories, spec, root=self.root)
        return proof, gate, captures, directories, spec, variant, predecessor, path

    def test_identity_first_compares_retained_bytes_and_validates_content_safe_receipt(self):
        proof, gate, _, _, spec, variant, predecessor, _ = self.identity_proof()
        SPEED.validate_identity_proof(proof, self.root, gate["release"], variant, predecessor, spec)
        self.assertEqual(proof["determinism"]["compared"], 80)
        self.assertEqual(proof["determinism"]["identical"], 80)
        self.assertNotIn("retained ", json.dumps(proof))
        self.assertNotIn(str(self.root), json.dumps(proof))

    def test_same_profile_nondefault_proofs_admit_identical_outputs_on_both_lanes(self):
        for lane in ("rtx3090", "rtx4090"):
            for profile_variant in ("tc", "a8", "tc-a8"):
                with self.subTest(lane=lane, profile_variant=profile_variant):
                    proof, gate, _, _, spec, variant, predecessor, _ = self.identity_proof(
                        lane=lane, profile_variant=profile_variant)
                    SPEED.validate_identity_proof(
                        proof, self.root, gate["release"], variant, predecessor, spec)
                    self.assertEqual(proof["build_profile"], spec["build_profile"])
                    self.assertEqual(proof["determinism"]["identical"], 80)
                    self.assertEqual([arm["arm"] for arm in proof["speed_abba"]["arms"]], list("ABBA"))

    def test_tensor_core_identity_refuses_a_default_or_different_variant_incumbent(self):
        for incumbent_variant in ("", "a8", "tc-a8"):
            with self.subTest(incumbent_variant=incumbent_variant):
                gate, captures, runs, spec, _, _, _ = identity_fixture(
                    self.root, lane="rtx3090", profile_variant="tc", incumbent_variant=incumbent_variant)
                with self.assertRaises(SPEED.SpeedGateError):
                    SPEED.create_identity_proof(gate, captures, plan_for(gate, captures),
                                                *runs, spec, root=self.root)

    def test_same_profile_still_refuses_one_changed_speed_or_determinism_output(self):
        for source in ("speed", "determinism"):
            with self.subTest(source=source):
                gate, captures, runs, spec, _, _, _ = identity_fixture(
                    self.root, lane="rtx3090", profile_variant="tc")
                if source == "speed":
                    for index in (1, 2):
                        captures[index]["requests"][0]["normalized_output"] += " changed"
                else:
                    path = runs[1] / "responses.jsonl"
                    rows = [json.loads(line) for line in path.read_text().splitlines()]
                    rows[0]["content"] += " changed"
                    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
                with self.assertRaisesRegex(SPEED.SpeedGateError, "byte-identical"):
                    SPEED.create_identity_proof(gate, captures, plan_for(gate, captures),
                                                *runs, spec, root=self.root)

    def test_same_profile_permission_and_sealed_component_profile_are_authenticated(self):
        for field in ("permission", "component", "build_profile", "identity", "seal", "hash"):
            with self.subTest(field=field):
                proof, gate, _, _, spec, variant, predecessor, path = self.identity_proof(
                    lane="rtx3090", profile_variant="tc")
                decision = json.loads(path.read_text())
                if field == "permission":
                    decision["rule"].pop("build_variant")
                elif field == "seal":
                    decision["sealed_incumbent_determinism"] = None
                elif field == "identity":
                    decision["sealed_incumbent_determinism"]["rtx3090"]["identity"]["package_sha256"] = "f" * 64
                elif field != "hash":
                    decision["sealed_incumbent_determinism"]["rtx3090"][field] = "foreign"
                path.write_text(json.dumps(decision) + " ", encoding="utf-8")
                if field != "hash":
                    qualification_path = path.parent.parent / "qualification.json"
                    qualification = json.loads(qualification_path.read_text())
                    binding = qualification["observed_gates"]["native_identity_decision"]
                    binding["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                    proof["decision_sha256"] = binding["sha256"]
                    qualification_path.write_text(json.dumps(qualification), encoding="utf-8")
                with self.assertRaises(SPEED.SpeedGateError):
                    SPEED.validate_identity_proof(proof, self.root, gate["release"], variant, predecessor, spec)

    def test_same_profile_producer_requires_the_published_predecessor_not_a_held_candidate(self):
        for mutation in ("missing", "draft", "candidate", "profile", "package", "lane"):
            with self.subTest(mutation=mutation):
                gate, captures, runs, spec, _, _, _ = identity_fixture(
                    self.root, lane="rtx3090", profile_variant="tc")
                path = self.root / "releases/v0.98.0/manifest.json"
                previous = json.loads(path.read_text())
                if mutation == "missing":
                    path.unlink()
                else:
                    row = previous["components"]["ninfer_variants"][0]
                    if mutation in ("draft", "candidate"):
                        previous["status"] = mutation
                    elif mutation == "profile":
                        row.pop("build_profile")
                    elif mutation == "package":
                        row["package_sha256"] = "f" * 64
                    else:
                        row["id"] = "rtx4090-windows-native"
                    path.write_text(json.dumps(previous), encoding="utf-8")
                with self.assertRaises(SPEED.SpeedGateError):
                    SPEED.create_identity_proof(gate, captures, plan_for(gate, captures),
                                                *runs, spec, root=self.root)

    def test_same_profile_receipt_still_requires_complete_speed_declaration(self):
        for mutation in ("declaration", "case", "arm", "output"):
            with self.subTest(mutation=mutation):
                proof, gate, _, _, spec, variant, predecessor, _ = self.identity_proof(
                    lane="rtx3090", profile_variant="tc")
                speed = proof["speed_abba"]
                if mutation == "declaration":
                    speed.pop("declaration")
                elif mutation == "case":
                    speed["arms"][2]["requests"].pop()
                elif mutation == "arm":
                    speed["arms"].pop()
                else:
                    speed["arms"][2]["requests"][0]["normalized_output_sha256"] = "f" * 64
                with self.assertRaises(SPEED.SpeedGateError):
                    SPEED.validate_identity_proof(proof, self.root, gate["release"], variant, predecessor, spec)

    def test_identity_proof_rejects_a_changed_output_build_profile_even_with_identical_samples(self):
        proof, gate, _, _, spec, variant, predecessor, _ = self.identity_proof()
        for profile in ("native-v0.9.0-beta.1-rtx4090-tc", "native-v0.9.0-beta.1-rtx4090-a8",
                        "unrecorded-profile", None):
            with self.subTest(profile=profile), self.assertRaisesRegex(SPEED.SpeedGateError, "build profile"):
                SPEED.validate_identity_proof(proof, self.root, gate["release"], variant, predecessor,
                                              {**spec, "build_profile": profile})

    def test_identity_first_requires_the_release_recorded_permission_and_sealed_incumbent(self):
        for field in ("permission", "seal", "hash"):
            with self.subTest(field=field):
                proof, gate, _, _, spec, variant, predecessor, path = self.identity_proof()
                decision = json.loads(path.read_text())
                if field == "permission":
                    decision["rule"]["quality_admission"] = "powered screen only"
                elif field == "seal":
                    decision["sealed_incumbent_determinism"]["rtx4090"]["responses_sha256"] = "f" * 64
                path.write_text(json.dumps(decision) + " ", encoding="utf-8")
                if field != "hash":
                    qual_path = path.parent.parent / "qualification.json"
                    qualification = json.loads(qual_path.read_text())
                    binding = qualification["observed_gates"]["native_identity_decision"]
                    binding["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                    qual_path.write_text(json.dumps(qualification), encoding="utf-8")
                    proof["decision_sha256"] = binding["sha256"]
                with self.assertRaises(SPEED.SpeedGateError):
                    SPEED.validate_identity_proof(proof, self.root, gate["release"], variant, predecessor, spec)

    def test_identity_first_rejects_one_changed_speed_or_determinism_output(self):
        for source in ("speed", "content", "reasoning", "tool_calls", "membership", "sealed"):
            with self.subTest(source=source):
                gate, captures, directories, spec, _, _, _ = identity_fixture(self.root)
                if source == "speed":
                    for index in (1, 2):
                        captures[index]["requests"][0]["normalized_output"] += " changed"
                else:
                    path = directories[0 if source == "sealed" else 1] / "responses.jsonl"
                    rows = [json.loads(line) for line in path.read_text().splitlines()]
                    if source == "membership":
                        rows.pop()
                    elif source == "tool_calls":
                        rows[0]["tool_calls"] = [{"function": {"name": "read", "arguments": '{"path":"different"}'}}]
                    else:
                        rows[0]["reasoning" if source == "reasoning" else "content"] += " changed"
                    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
                with self.assertRaises(SPEED.SpeedGateError):
                    SPEED.create_identity_proof(gate, captures, plan_for(gate, captures),
                                                *directories, spec, root=self.root)

    def test_identity_receipt_validation_rederives_membership_and_every_pair(self):
        for field in ("speed-output", "determinism-output", "count", "candidate", "predecessor"):
            with self.subTest(field=field):
                proof, gate, _, _, spec, variant, predecessor, _ = self.identity_proof()
                if field == "speed-output":
                    proof["speed_abba"]["arms"][2]["requests"][0]["normalized_output_sha256"] = "f" * 64
                elif field == "determinism-output":
                    proof["determinism"]["outputs"][0]["candidate_sha256"] = "f" * 64
                elif field == "count":
                    proof["determinism"]["outputs"].pop()
                else:
                    proof[field]["configuration_sha256"] = "f" * 64
                with self.assertRaises(SPEED.SpeedGateError):
                    SPEED.validate_identity_proof(proof, self.root, gate["release"], variant, predecessor, spec)

    def test_identity_proof_cli_round_trip(self):
        gate, captures, directories, spec, _, _, _ = identity_fixture(self.root)
        plan = plan_for(gate, captures)
        for name, value in (("gate", gate), ("plan", plan), ("spec", spec),
                            *[(str(index), capture) for index, capture in enumerate(captures)]):
            (self.root / f"{name}.json").write_text(json.dumps(value), encoding="utf-8")
        argv = ["identity-proof", "--root", str(self.root), "--gate", str(self.root / "gate.json"),
                "--plan", str(self.root / "plan.json"), "--release-spec", str(self.root / "spec.json"),
                "--incumbent-determinism", str(directories[0]), "--candidate-determinism", str(directories[1]),
                "--out", str(self.root / "proof.json")]
        for index in range(4):
            argv += ["--capture", str(self.root / f"{index}.json")]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(SPEED.main(argv), 0)
        proof = json.loads((self.root / "proof.json").read_text())
        self.assertEqual(proof["determinism"]["identical"], 80)


if __name__ == "__main__":
    unittest.main()
