"""P16 binds native policy to authenticated package metadata, not card/backend defaults."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bind_native_variant as binder
import compose_native_qualification as native
import run_variant_campaign as campaign
import verify_release as verifier


def candidate_profile(lane: str) -> tuple[dict, dict, dict]:
    concurrency, headroom, host = ((2, 768, "20867.734375") if lane == "rtx3090"
                                   else (1, 640, "15747.734375"))
    config = {
        "artifact_type": "ninfer_windows_server_config", "schema_version": 4,
        "release_id": f"qwen38-{lane[3:]}-native-v0.8.0-beta.1",
        "deployment_profile": f"qwen38-{lane[3:]}-native-v0.8.0-beta.1",
        "model_id": "q38-ninfer" if lane == "rtx3090" else "qwen3.8-27b",
        "engine": {"max_context": 131072, "kv_capacity": 131072, "kv_dtype": "int8",
                   "max_concurrency": concurrency, "pending_timeout_ms": 180000 if concurrency == 2 else 30000,
                   "admission_headroom_mib": headroom, "prefill_chunk": 1024},
        "context_cache": {"device_state_slots": 2, "host_context_mib": host},
        "speculative": {"backend": "dflash2", "draft_tokens": 7},
    }
    shape = {"max_concurrency": concurrency, "speculative_backend": "dflash2",
             "draft_tokens": {"min": 7, "max": 7}, "proposal": "artifact-default",
             "fit": {"device_state_slots": 2, "admission_headroom_mib": headroom,
                     "draft_mlp_device_format": "Q4_G64_FP16", "token_embedding_residency": "host-mapped"}}
    host_bytes = 21881405440 if lane == "rtx3090" else 16512696320
    spec = {"artifact_type": "ninfer_windows_release_spec", "schema_version": 5, "lane": lane,
            "release_id": config["release_id"], "deployment_profile": config["deployment_profile"],
            "runtime_shape": shape, "host_context_translation": {"host_context_bytes": host_bytes}}
    configuration = {
        "max_context": 131072, "kv_capacity": 131072, "kv_dtype": "int8",
        "concurrency": concurrency, "pending_timeout_ms": config["engine"]["pending_timeout_ms"],
        "prefill_chunk": 1024, "device_state_slots": 2, "admission_headroom_mib": headroom,
        "host_context_mib": host, "host_context_bytes": host_bytes,
        "speculative_backend": "dflash2", "speculative_draft_tokens": 7,
        "public_model_id": config["model_id"],
    }
    return spec, config, configuration


class NativeCandidateFitTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.directory = self.root / "releases/v0.16.0/qualification"
        self.directory.mkdir(parents=True)

    def evidence(self, field, value):
        path = self.directory / f"{field}.json"
        path.write_text(json.dumps(value))
        self.variant["qualification"][field] = {
            "path": path.relative_to(self.root).as_posix(), "sha256": verifier.sha256_file(path)}
        return path

    def prepare(self, lane):
        self.spec, self.config, self.configuration = candidate_profile(lane)
        self.variant = {
            "id": f"{lane}-windows-native", "maximum_context_tokens": 131072,
            "runtime_shape": deepcopy(self.spec["runtime_shape"]), "qualification": {},
            "package_sha256": "a" * 64, "server_binary_sha256": "b" * 64,
            "configuration_sha256": "c" * 64, "model_artifact_sha256": "d" * 64,
        }
        self.evidence("release_spec", self.spec)
        config_path = self.evidence("server_config", self.config)
        self.variant["configuration_sha256"] = verifier.sha256_file(config_path)
        self.fit = {
            "artifact_type": "omp-ninfer.native-fit", "schema_version": 1, "status": "passed",
            "identity": {key: self.variant[key] for key in
                         ("package_sha256", *verifier.NATIVE_IDENTITY_FIELDS)},
            "runtime_shape": deepcopy(self.spec["runtime_shape"]), "maximum_context_tokens": 131072,
            "configuration": deepcopy(self.configuration),
            "measured_admission_headroom_mib": self.configuration["admission_headroom_mib"],
            "effective_weights": {"converted_device_bytes": 1024, "host_mapped_bytes": 2048},
            "raw_prompts_outputs_or_secrets_included": False,
        }
        self.evidence("fit", self.fit)

    def errors(self):
        errors = []
        verifier.validate_native_fit(self.root, "v0.16.0", self.variant, errors)
        return errors

    def test_c2_3090_and_dflash2_4090_fit_their_authenticated_profiles(self):
        for lane in ("rtx3090", "rtx4090"):
            with self.subTest(lane=lane):
                self.prepare(lane)
                self.assertEqual(self.errors(), [])

    def test_fit_configuration_cannot_disagree_with_any_candidate_policy_field(self):
        self.prepare("rtx3090")
        for field in self.configuration:
            with self.subTest(field=field):
                value = deepcopy(self.fit)
                actual = value["configuration"][field]
                value["configuration"][field] = actual + 1 if type(actual) is int else actual + "-wrong"
                self.evidence("fit", value)
                self.assertTrue(self.errors(), field)

    def test_slots_concurrency_headroom_and_metadata_hashes_remain_fail_closed(self):
        for lane in ("rtx3090", "rtx4090"):
            for field, wrong in (("device_state_slots", 0), ("admission_headroom_mib", 1),
                                 ("max_concurrency", 3)):
                with self.subTest(lane=lane, field=field):
                    self.prepare(lane)
                    target = self.fit["runtime_shape"]
                    (target if field == "max_concurrency" else target["fit"])[field] = wrong
                    self.evidence("fit", self.fit)
                    self.assertTrue(self.errors())
            self.prepare(lane)
            self.fit["measured_admission_headroom_mib"] -= 1
            self.evidence("fit", self.fit)
            self.assertTrue(self.errors())
            self.prepare(lane)
            (self.directory / "server_config.json").write_text("{}")
            self.assertTrue(self.errors())

    def test_ceiling_comes_from_candidate_config_not_a_verifier_literal(self):
        self.prepare("rtx3090")
        for value in (self.config["engine"], self.configuration, self.fit["configuration"]):
            value.update(max_context=65536, kv_capacity=65536)
        self.variant["maximum_context_tokens"] = self.fit["maximum_context_tokens"] = 65536
        path = self.evidence("server_config", self.config)
        self.variant["configuration_sha256"] = verifier.sha256_file(path)
        self.fit["identity"]["configuration_sha256"] = self.variant["configuration_sha256"]
        self.evidence("fit", self.fit)
        self.assertEqual(self.errors(), [])

    def test_packaged_shape_must_agree_with_config_beyond_backend(self):
        for field in ("max_concurrency", "admission_headroom_mib"):
            spec, config, _ = candidate_profile("rtx3090")
            config["engine"][field] += 1
            data = json.dumps(config).encode()
            package = self.root / "native.tar.gz"
            with tarfile.open(package, "w:gz") as archive:
                for name, payload in (("release-spec.json", json.dumps(spec).encode()),
                                      ("server-config.json", data)):
                    member = tarfile.TarInfo("payload/" + name)
                    member.size = len(payload)
                    archive.addfile(member, io.BytesIO(payload))
            receipt = {"lane": "rtx3090", "config_sha256": hashlib.sha256(data).hexdigest(),
                       "package": {"sha256": verifier.sha256_file(package)}}
            with self.subTest(field=field), self.assertRaises(binder.BindError):
                binder.package_runtime_shape(package, receipt)


class NativeConcurrentProtocolTests(unittest.TestCase):
    def test_protocol_accepts_c2_but_not_under_reserved_or_short_deadline_c2(self):
        from test_compose_native_qualification import SHIPPED_RECEIPT
        receipt = deepcopy(SHIPPED_RECEIPT)
        receipt["configuration"].update(concurrency=2, device_state_slots=2, pending_timeout_ms=180000)
        receipt["protocol_under_pool_pressure"]["device_state_slots"] = 2
        self.assertEqual(native.native_protocol_qualification_errors(receipt), [])
        for fields in ({"concurrency": True}, {"concurrency": 0}, {"device_state_slots": 1},
                       {"pending_timeout_ms": 30000}):
            value = deepcopy(receipt)
            value["configuration"].update(fields)
            self.assertTrue(native.native_protocol_qualification_errors(value), fields)

    def test_concurrent_acceptance_is_separate_from_serial_speed_gate(self):
        spec, _, configuration = candidate_profile("rtx3090")
        argv = campaign.concurrency_acceptance_arguments("rtx3090", configuration)
        self.assertIn("rtx3090-C2-acceptance", argv)
        self.assertEqual(argv[argv.index("--scenario") + 1], "fanout")
        self.assertEqual(argv[argv.index("--fanout-concurrency") + 1], "4")
        configuration["concurrency"] = 1
        with self.assertRaises(campaign.CampaignError):
            campaign.concurrency_acceptance_arguments("rtx3090", configuration)
        from test_run_variant_campaign import matrix_for, server_start, MODEL
        matrix = matrix_for()
        arm = matrix.spec("inc")
        start = server_start(arm.as_dict(), "instance")
        start["engine"]["max_concurrency"] = 2
        with self.assertRaisesRegex(campaign.CampaignError, "max_concurrency"):
            campaign.bind_server_start(start, spec=arm, matrix=matrix, model=MODEL, instance_id="instance")


if __name__ == "__main__":
    unittest.main()
