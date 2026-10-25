from __future__ import annotations

import json
import hashlib
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import doctor
import render_compatibility
import verify_release

CONFIG_SHA = "751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47"


class V013PreparationTests(unittest.TestCase):
    def profiles(self):
        for path in sorted((ROOT / "profiles/v0.13.0").glob("*.json")):
            yield path, json.loads(path.read_text(encoding="utf-8"))

    def test_new_profile_has_byte_equivalent_host_budget_and_unchanged_other_tuning(self):
        count = 0
        for path, profile in self.profiles():
            count += 1
            arguments = profile["server"]["arguments"]
            old = json.loads((ROOT / "releases/v0.12.2/manifest.json").read_text(encoding="utf-8"))
            # Root profiles intentionally remain live until the lane pin.
            previous = json.loads((ROOT / "profiles" / path.name).read_text(encoding="utf-8"))
            if previous["release"] == "v0.12.2":
                old_tuning = verify_release.tuning_arguments(previous["server"]["arguments"])
                for flag in ("--host-state-slots", "--host-kv-mib", "--max-private-continuations"):
                    index = old_tuning.index(flag)
                    del old_tuning[index:index + 2]
                new_tuning = verify_release.tuning_arguments(arguments)
                new_tuning.remove("--session-checkpoint-require-origin-auth")
                index = new_tuning.index("--host-context-mib")
                del new_tuning[index:index + 2]
                self.assertEqual(new_tuning, old_tuning)
                self.assertNotEqual(CONFIG_SHA, old["runtime_identity"]["configuration_sha256"])
            host_mib = verify_release.argument_value(arguments, "--host-context-mib")
            self.assertEqual(Decimal(host_mib) * (1 << 20), 21881405440)
            self.assertEqual(verify_release.argument_value(arguments, "--device-state-slots"), "2")
            self.assertEqual(verify_release.argument_value(arguments, "--gpu-keep-warm-ms"), "60000")
            self.assertEqual(arguments.count("--session-checkpoint-require-origin-auth"), 1)
            self.assertEqual(verify_release.configuration_identity(profile), CONFIG_SHA)
            self.assertEqual(verify_release.argument_value(arguments, "--config-sha256"), CONFIG_SHA)
            self.assertEqual(profile["server"]["checkpoint_mount_target"], "/checkpoints-v013")
            self.assertEqual(profile["server"]["status_schema_version"], 2)
            self.assertEqual(doctor.thresholds(profile)["ram_free_mib"], 20868)
            self.assertEqual(doctor.thresholds(profile)["ram_total_mib"], 28672)
            errors = []
            verify_release.validate_profile_contract(
                profile, path.name, "v0.13.0",
                {"artifact_sha256": profile["model"]["artifact_sha256"],
                 "artifact_bytes": 20437521664},
                "q38-ninfer", "qwen38-5090-v0.13.0", errors,
                upstream_client=True, per_model_stateful=True)
            self.assertEqual(errors, [])
        self.assertEqual(count, 2)

    def test_strict_origin_profile_copies_share_the_new_configuration(self):
        for template_path, template in self.profiles():
            staged = json.loads((ROOT / "releases/v0.13.0/profiles" / template_path.name).read_text(
                encoding="utf-8"))
            for profile in (template, staged):
                arguments = profile["server"]["arguments"]
                self.assertEqual(arguments.count("--session-checkpoint-require-origin-auth"), 1)
                self.assertEqual(verify_release.configuration_identity(profile), CONFIG_SHA)
                self.assertEqual(
                    verify_release.argument_value(arguments, "--config-sha256"), CONFIG_SHA)

    def test_unbound_beta2_preparation_cannot_reuse_beta1_eligibility(self):
        release = ROOT / "releases/v0.13.0"
        manifest = json.loads((release / "manifest.json").read_text(encoding="utf-8"))
        preparation = manifest.get("restage_preparation", {})
        if preparation.get("status") != "awaiting-F2-inventory":
            return
        qualification = json.loads((release / "qualification.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "draft")
        self.assertFalse(manifest["qualification"]["runtime_release_eligible"])
        self.assertEqual(qualification["status"], "preparation-only")
        self.assertEqual(qualification["observed_gates"]["g4_review"]["status"],
                         "remediation-required")
        self.assertEqual(preparation["target_configuration_sha256"], CONFIG_SHA)
        self.assertFalse(preparation["stage_release_executed"])
        self.assertNotEqual(
            preparation["historical_configuration_sha256"], CONFIG_SHA)
        self.assertIn("prompt_cache_key names a session capability",
                      preparation["principal_limitation"])

    def test_prepared_authority_does_not_claim_accepted_schema_support_on_carried_natives(self):
        path = ROOT / "releases/v0.13.0/compatibility.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("artifact_type") == "omp_ninfer_prepared_compatibility":
            with self.assertRaisesRegex(ValueError, "not an installable authority"):
                render_compatibility.load_authority(path)
        authority = render_compatibility.load_authority(path, allow_prepared=True)
        if authority.get("artifact_type") == "omp_ninfer_prepared_compatibility":
            rendered = render_compatibility.render(authority)
            self.assertEqual((ROOT / "releases/v0.13.0/COMPATIBILITY.md").read_text(encoding="utf-8"), rendered)
            self.assertIn("Preparation only", rendered)
            contracts = authority["runtime_contracts"]
            self.assertIn("acceptance pending", contracts[0]["json_schema"])
            self.assertEqual(contracts[0]["tool_name_max_characters"], 128)
            self.assertEqual(contracts[0]["status_schema_version"], 2)
            for native in contracts[1:]:
                self.assertEqual(native["tool_name_max_characters"], 64)
                self.assertEqual(native["status_schema_version"], 1)
                self.assertIn("Rejected with HTTP 400", native["json_schema"])
        else:
            contracts = authority["runtime_contracts"]
            self.assertIn("Supported on RTX 5090", contracts[0]["json_schema"])
            self.assertEqual(contracts[0]["tool_name_max_characters"], 128)
            for native in contracts[1:]:
                self.assertIn("Rejected with HTTP 400", native["json_schema"])
                self.assertEqual(native["tool_name_max_characters"], 64)

    def test_staged_receipt_inventory_carries_only_unchanged_native_subjects(self):
        release = ROOT / "releases/v0.13.0"
        if not (release / "manifest.json").exists():
            self.skipTest("notes-only preparation has no staged receipt inventory")
        audit = json.loads((release / "qualification/receipt-audit.json").read_text(encoding="utf-8"))
        allowed = {"rtx3090.json", "rtx4090.json", "rtx3090-windows-native.SHA256SUMS",
                   "rtx4090-windows-native.SHA256SUMS"}
        self.assertEqual({item["file"] for item in audit["files"]
                          if item["disposition"] == "kept"}, allowed)
        for item in audit["files"]:
            current = release / "qualification" / item["file"]
            previous = ROOT / "releases/v0.12.2/qualification" / item["file"]
            with self.subTest(receipt=item["file"]):
                self.assertTrue(item["reason"])
                if item["disposition"] == "dropped":
                    self.assertFalse(current.exists())
                elif item["disposition"] == "kept":
                    self.assertEqual(current.read_bytes(), previous.read_bytes())
                else:
                    self.assertNotEqual(current.read_bytes(), previous.read_bytes())

    def test_staged_gate_evidence_keeps_comparison_and_publication_subjects_distinct(self):
        release = ROOT / "releases/v0.13.0"
        if not (release / "manifest.json").exists():
            self.skipTest("notes-only preparation has no frozen runtime identity")
        manifest = json.loads((release / "manifest.json").read_text(encoding="utf-8"))
        qualification = json.loads((release / "qualification.json").read_text(encoding="utf-8"))
        gates = qualification["observed_gates"]
        self.assertEqual(gates["g1_restart"]["checkpoint_hit_tokens"], 20926)
        self.assertTrue(gates["g1_restart"]["byte_identical"])
        self.assertEqual(gates["g2_decode"]["minimum_ratio"], 0.96)
        self.assertGreaterEqual(gates["g2_decode"]["observed_ratio"], 0.96)
        self.assertEqual(gates["g3_integrated_qualification"]["host_tests"],
                         {"passed": 65, "failed": 0, "skipped": 0})
        self.assertTrue(qualification["not_remeasured_gates"])
        for item in qualification["not_remeasured_gates"]:
            self.assertEqual(item["status"], "not re-measured for v0.13.0")
            self.assertTrue(item["reason"])
        for name in ("runtime-publication.json", "runtime-base.json"):
            receipt = json.loads((release / "qualification" / name).read_text(encoding="utf-8"))
            self.assertEqual(receipt["source_commit"], manifest["components"]["ninfer"]["source_commit"])
        for key in ("package_inventory", "publication_receipt", "runtime_base_receipt"):
            edge = qualification["composition"]["local_release_packaging"][key]
            self.assertEqual(edge["sha256"], hashlib.sha256(
                (ROOT / edge["repository_path"]).read_bytes()).hexdigest())

    def test_prepared_notes_are_bounded_and_use_readable_release_prose(self):
        from test_documented_route import ReleaseProseTests
        text = (ROOT / "releases/v0.13.0/NINFER_RELEASE_NOTES.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 210)
        self.assertEqual(ReleaseProseTests.glued_tokens(text), [])
        self.assertIn("335.332 → 290.781", text)
        self.assertIn("diagnostic-only and reverted", text)

    def test_rebased_native_tag_shapes_are_bounded_not_a_future_version_wildcard(self):
        for lane in ("rtx3090", "rtx4090"):
            pattern = render_compatibility.RUNTIME_VARIANT_RELEASE_TAG_RES[f"{lane}-windows-native"]
            self.assertIsNotNone(pattern.fullmatch(f"v0.7.0-qwen38-{lane[3:]}-beta.1"))
            self.assertIsNone(pattern.fullmatch(f"v0.7.1-qwen38-{lane[3:]}-beta.1"))


if __name__ == "__main__":
    unittest.main()
