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
import compose_route_acceptance as composer
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


def probe_receipts(variant, configuration):
    """Synthetic wire/driver shapes; never qualification evidence."""
    identity = {"binary_sha256": variant["server_binary_sha256"],
                "config_sha256": variant["configuration_sha256"],
                "model_artifact_sha256": variant["model_artifact_sha256"], "source_dirty": False,
                "model_id": configuration["public_model_id"]}
    status = {"artifact_type": "ninfer_server_status", "schema_version": 2, "status": "ok",
              "identity": identity, "scheduler": {"max_concurrency": configuration["concurrency"]},
              "runtime": {"max_context": configuration["max_context"]}}
    fleet = {"artifact_type": "omp_ninfer_fleet_fanout_probe", "schema_version": 3,
             "identity": identity, "branches": 4, "transient_retries": 0,
             "steps": [{"step": step} for step in
                       ("base_prefill", "warm_edit", "checkpoint_save", "branch_0", "branch_1",
                        "branch_2", "branch_3", "session_delete")]}
    if configuration["concurrency"] == 1:
        return {"fleet": fleet}
    model = f"ninfer-native-{variant['id'].split('-')[0][3:]}/{configuration['public_model_id']}"
    fanout = {"artifact_type": "omp_ninfer_concurrency_probe", "schema_version": 1, "ok": True,
              "arguments": {"arm": "rtx3090-C2-acceptance", "scenario": ["fanout"], "branches": 4,
                            "fanout_concurrency": 4, "model": configuration["public_model_id"]},
              "identity": {phase: {"body": deepcopy(status)} for phase in ("server_before", "server_after")},
              "scenarios": [{"name": "fanout", "ok": True, "requests": [
                  {"label": label, "ok": True, "http_status": 200,
                   "submitted_monotonic_s": 1 if label == "fanout-base" else 3,
                   "completed_monotonic_s": 2 if label == "fanout-base" else 6}
                  for label in ("fanout-base", "branch-0", "branch-1", "branch-2", "branch-3")]}]}
    omp = {"sha256": "1" * 64, "version": "omp/18.14.0"}
    parallel = {"artifact_type": "omp_ninfer_parallel_proof", "passed": True, "model": model,
                "omp": omp, "max_in_flight": 2, "scenarios": [
                    {"scenario": name, "passed": True, "max_in_flight": 2, "overlap_seconds": 1.5,
                     "checks": {"logged_requests": True, "all_logged_requests_completed": True,
                                "single_server_instance": True, "provider_limit_respected": True,
                                "concurrency_expected": True}}
                    for name in ("subagents", "sessions")]}
    compaction = {"artifact_type": "omp_ninfer_long_session_proof", "passed": True, "model": model,
                  "omp": omp, "checks": {"every_turn_completed": True, "compactions_committed": True,
                    "no_failed_compaction": True, "control_recalled_after_each_compaction": True,
                    "one_session": True},
                  "parameters": {"compactions": 2},
                  "compactions": [{"committed": True}, {"committed": True}]}
    return {"fleet": fleet, "fanout": fanout, "parallel": parallel, "compaction": compaction}


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

    def test_composer_and_ready_verifier_bind_actual_policy_and_c2_probes(self):
        for lane in ("rtx3090", "rtx4090"):
            self.prepare(lane)
            probes = native.native_probe_summary(probe_receipts(self.variant, self.configuration))
            evidence = {"runtime_configuration": self.configuration, "probe_acceptance": probes}
            with mock.patch.object(composer, "ROOT", self.root):
                self.assertEqual(composer.check_native_policy("v0.16.0", self.variant, evidence, "1" * 64),
                                 self.configuration)
                wrong = deepcopy(evidence)
                wrong["runtime_configuration"]["pending_timeout_ms"] += 1
                with self.assertRaisesRegex(SystemExit, "actual runtime configuration"):
                    composer.check_native_policy("v0.16.0", self.variant, wrong, "1" * 64)
            acceptance = self.root / "releases/v0.16.0/acceptance"
            acceptance.mkdir(exist_ok=True)
            path = acceptance / f"{lane}-public-install.json"
            receipt = {"status": "passed", "release": "v0.16.0", "lane": self.variant["id"],
                       "runtime": {"package_sha256": self.variant["package_sha256"],
                                   "binary_sha256": self.variant["server_binary_sha256"],
                                   "configuration_sha256": self.variant["configuration_sha256"],
                                   "model_sha256": self.variant["model_artifact_sha256"],
                                   "runtime_shape": self.variant["runtime_shape"], "configuration": self.configuration},
                       "probe_acceptance": probes}
            composed = acceptance / "composed.json"
            def bind_receipt():
                path.write_text(json.dumps(receipt))
                composed.write_text(json.dumps({"evidence": {f"{lane}_public_install": {
                    "repository_path": path.relative_to(self.root).as_posix(),
                    "sha256": verifier.sha256_file(path)}}}))
                return {"composition": {"external_installation_acceptance": {
                    "repository_path": composed.relative_to(self.root).as_posix(),
                    "sha256": verifier.sha256_file(composed)}}}
            manifest = {"components": {"omp": {"binary_sha256": "1" * 64}, "ninfer_variants": [self.variant]}}
            errors = []
            verifier.validate_native_route_policy(self.root, "v0.16.0", manifest, bind_receipt(), errors)
            self.assertEqual(errors, [])
            receipt["runtime"]["configuration"] = {**self.configuration, "concurrency": 99}
            errors = []
            verifier.validate_native_route_policy(self.root, "v0.16.0", manifest, bind_receipt(), errors)
            self.assertTrue(any("exact authenticated" in error for error in errors))


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
        # Preserve the real orchestrator receipt schema: timeout lives in the authenticated
        # packaged config, not in a fabricated edit to a qualification receipt.
        receipt["configuration"].pop("pending_timeout_ms")
        _, _, policy = candidate_profile("rtx3090")
        self.assertEqual(native.native_protocol_qualification_errors(receipt, policy), [])
        self.assertTrue(native.native_protocol_qualification_errors(receipt))
        self.assertTrue(native.native_protocol_qualification_errors(receipt, {**policy, "pending_timeout_ms": 30000}))

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

    def test_c2_requires_real_fanout_stock_omp_and_automatic_compaction_oracles(self):
        _, _, configuration = candidate_profile("rtx3090")
        variant = {"id": "rtx3090-windows-native", "server_binary_sha256": "a" * 64,
                   "configuration_sha256": "b" * 64, "model_artifact_sha256": "c" * 64}
        raw = probe_receipts(variant, configuration)
        summary = native.native_probe_summary(raw)
        self.assertEqual(native.native_probe_acceptance_errors(configuration, summary, variant, "1" * 64), [])
        for name in raw:
            value = deepcopy(summary)
            del value[name]
            self.assertTrue(native.native_probe_acceptance_errors(configuration, value, variant, "1" * 64), name)
        for mutate in (
            lambda value: value["fanout"]["arguments"].update(fanout_concurrency=1),
            lambda value: value["fanout"]["statuses"]["server_after"]["scheduler"].update(max_concurrency=1),
            lambda value: value["fanout"]["statuses"]["server_before"]["identity"].update(config_sha256="0" * 64),
            lambda value: value["parallel"].update(max_in_flight=1),
            lambda value: value["parallel"]["omp"].update(sha256="0" * 64),
            lambda value: value["compaction"].update(committed=1),
            lambda value: value["compaction"]["checks"].update(control_recalled_after_each_compaction=False),
        ):
            value = deepcopy(summary)
            mutate(value)
            self.assertTrue(native.native_probe_acceptance_errors(configuration, value, variant, "1" * 64))
        sequential = deepcopy(raw)
        for index, row in enumerate(sequential["fanout"]["scenarios"][0]["requests"]):
            row.update(submitted_monotonic_s=index * 10, completed_monotonic_s=index * 10 + 2)
        self.assertTrue(native.native_probe_acceptance_errors(
            configuration, native.native_probe_summary(sequential), variant, "1" * 64))

    def test_serial_4090_campaign_accepts_dflash2_without_an_mtp_proposal_head(self):
        from test_run_variant_campaign import matrix_for, server_start, test_manifest, MODEL
        manifest = test_manifest()
        entry = manifest["lanes"]["rtx-test"]["arms"][0]
        entry.update(speculative_backend="dflash2", speculative_draft_window=7)
        matrix = matrix_for(manifest)
        spec = matrix.spec("inc")
        start = server_start(spec.as_dict(), "instance")
        start["engine"]["proposal_head"] = "artifact-default"
        self.assertEqual(campaign.bind_server_start(
            start, spec=spec, matrix=matrix, model=MODEL, instance_id="instance")["capacity"]["kv_capacity"], 131072)

    def test_native_client_home_uses_candidate_context_and_provider_limit(self):
        from client_acceptance import prepare_home
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            prepare_home(home, "http://127.0.0.1:18082/v1", "synthetic-key", "q38-ninfer",
                         context_window=65536, concurrency=2)
            models = json.loads((home / ".omp/agent/models.yml").read_text())
            config = json.loads((home / ".omp/agent/config.yml").read_text())
            self.assertEqual(models["providers"]["ninfer-acceptance"]["models"][0]["contextWindow"], 65536)
            self.assertEqual(config["providers"]["maxInFlightRequests"]["ninfer-acceptance"], 2)

    def test_served_concurrency_and_ceiling_must_match_with_integer_types(self):
        for lane in ("rtx3090", "rtx4090"):
            _, _, configuration = candidate_profile(lane)
            variant = {"server_binary_sha256": "a" * 64, "configuration_sha256": "b" * 64,
                       "model_artifact_sha256": "c" * 64}
            status = {"artifact_type": "ninfer_server_status", "schema_version": 2, "status": "ok",
                      "identity": {"binary_sha256": "a" * 64, "config_sha256": "b" * 64,
                                   "model_artifact_sha256": "c" * 64, "source_dirty": False},
                      "scheduler": {"max_concurrency": configuration["concurrency"]},
                      "runtime": {"max_context": 131072}}
            self.assertEqual(native.native_status_errors(status, variant, configuration), [])
            for field, wrong in (("max_concurrency", True), ("max_concurrency", 3), ("max_context", 65536)):
                value = deepcopy(status)
                value["scheduler" if field == "max_concurrency" else "runtime"][field] = wrong
                self.assertTrue(native.native_status_errors(value, variant, configuration))


if __name__ == "__main__":
    unittest.main()
