"""Unmocked verifier admission of a decision-scoped native byte-identity proof."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from test_native_candidate_policy import candidate_profile
from test_native_gate_decisions import identity_fixture
from test_speed_gate import SPEED
import verify_release as verifier


class NativeIdentityAdmissionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        patch = mock.patch.object(SPEED, "ROOT", self.root)
        patch.start()
        self.addCleanup(patch.stop)
        gate, captures, runs, spec, variant, predecessor, _ = identity_fixture(self.root)
        self.release = gate["release"]
        spec, config, configuration = candidate_profile("rtx4090")
        spec["build_profile"] = "native-v0.9.0-beta.1-rtx4090"
        variant["configuration_sha256"] = hashlib.sha256(json.dumps(config).encode()).hexdigest()
        for index in (1, 2):
            captures[index]["identity"] = {
                "binary_sha256": variant["server_binary_sha256"],
                "configuration_sha256": variant["configuration_sha256"]}
        arm_path = runs[1] / "arm.json"
        arm = json.loads(arm_path.read_text(encoding="utf-8"))
        arm["configuration_sha256"] = variant["configuration_sha256"]
        arm_path.write_text(json.dumps(arm), encoding="utf-8")
        plan = SPEED.prescreen(gate, captures[1]["identity"], root=self.root)
        proof = SPEED.create_identity_proof(gate, captures, plan, *runs, spec, root=self.root)
        variant.update(runtime_shape=spec["runtime_shape"], maximum_context_tokens=131072, qualification={})
        self.variant = variant
        previous = {"id": variant["id"], **predecessor, "runtime_shape": spec["runtime_shape"]}
        path = self.root / "releases/v0.98.0/manifest.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"status": "ready", "components": {"ninfer_variants": [previous]}}),
                        encoding="utf-8")
        self.spec_path = self.evidence("release_spec", spec, profile=True)
        self.evidence("server_config", config, profile=True)
        self.proof_path = self.evidence("identity_proof", proof)
        self.evidence("fit", {
            "artifact_type": "omp-ninfer.native-fit", "schema_version": 1, "status": "passed",
            "identity": {key: variant[key] for key in SPEED.NATIVE_IDENTITY_FIELDS},
            "runtime_shape": spec["runtime_shape"], "maximum_context_tokens": 131072,
            "configuration": configuration, "measured_admission_headroom_mib": 640,
            "effective_weights": {"converted_device_bytes": 1024, "host_mapped_bytes": 2048},
            "raw_prompts_outputs_or_secrets_included": False,
        })

    def evidence(self, field, value, profile=False):
        directory = self.root / "releases" / self.release / ("profiles/rtx4090" if profile else "qualification")
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (field.replace("_", "-") + ".json")
        path.write_text(json.dumps(value), encoding="utf-8")
        self.variant["qualification"][field] = {
            "path": path.relative_to(self.root).as_posix(), "sha256": verifier.sha256_file(path)}
        return path

    def test_default_dflash2_candidate_binds_identity_instead_of_screen_without_waiving_fit(self):
        errors = []
        verifier.validate_native_quality(self.root, self.release, self.variant, errors)
        self.assertEqual(errors, [])
        self.variant["qualification"].pop("fit")
        verifier.validate_native_quality(self.root, self.release, self.variant, errors)
        self.assertTrue(any("fit" in error for error in errors))

    def test_output_changing_build_or_one_changed_determinism_output_cannot_skip_screen(self):
        spec = json.loads(self.spec_path.read_text(encoding="utf-8"))
        default_profile = spec["build_profile"]
        for mutation in ("build", "output"):
            with self.subTest(mutation=mutation):
                if mutation == "build":
                    spec["build_profile"] += "-a8"
                    self.evidence("release_spec", spec, profile=True)
                else:
                    spec["build_profile"] = default_profile
                    self.evidence("release_spec", spec, profile=True)
                    proof = json.loads(self.proof_path.read_text(encoding="utf-8"))
                    proof["determinism"]["outputs"][0]["candidate_sha256"] = "f" * 64
                    self.evidence("identity_proof", proof)
                errors = []
                verifier.validate_native_quality(self.root, self.release, self.variant, errors)
                self.assertTrue(any("identity_proof" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
