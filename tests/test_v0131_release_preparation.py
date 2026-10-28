"""Native staging binds real package subjects without transferring predecessor approval."""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))  # test_documented_route, also when this module runs alone
import render_compatibility
import verify_release

RELEASE = ROOT / "releases/v0.13.1"
MODEL_SHA = "81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da"
CONFIGS = {
    "4090": ("b21cdaf8b5edeed4e7d498edf5dbfae77a993145f1d511a8e1aa1b7bdab42950",
             2, 2048, 15506063360, 640, 60000, "qwen3.8-27b"),
    "3090": ("b49aad9915dd333f14cc7a3f0bb269aec124b38112e8ea984af3f569fe2dac75",
             4, 1024, 12284837888, 768, 0, "q38-ninfer"),
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class V0131PreparationTests(unittest.TestCase):
    def test_native_profiles_bind_exact_packaged_bytes_and_k5_contract(self) -> None:
        for number, (expected_sha, slots, prefill, host_bytes, headroom, keep_warm, model_id) in CONFIGS.items():
            with self.subTest(lane=number):
                path = ROOT / "profiles/v0.13.1" / ("rtx" + number) / "server-config.json"
                raw = path.read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), expected_sha)
                self.assertNotIn(b"\r", raw)
                self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
                self.assertTrue(raw.endswith(b"\n"))
                profile = json.loads(raw)
                self.assertEqual(profile["artifact_type"], "ninfer_windows_server_config")
                self.assertEqual(profile["schema_version"], 4)
                identity = f"qwen38-{number}-native-v0.7.0-beta.2"
                self.assertEqual(profile["release_id"], identity)
                self.assertEqual(profile["deployment_profile"], identity)
                self.assertEqual(profile["listen"]["host"], "127.0.0.1")
                self.assertEqual(profile["listen"]["port"], 18082)
                self.assertEqual(profile["model_id"], model_id)
                engine = profile["engine"]
                self.assertEqual((engine["max_context"], engine["kv_capacity"]), (131072, 131072))
                self.assertEqual(engine["kv_dtype"], "int8")
                self.assertEqual(engine["max_concurrency"], 1)
                self.assertEqual(engine["pending_timeout_ms"], 30000)
                self.assertEqual(engine["prefill_chunk"], prefill)
                self.assertEqual(engine["admission_headroom_mib"], headroom)
                self.assertEqual(engine["gpu_keep_warm_ms"], keep_warm)
                self.assertFalse(engine["vision"])
                self.assertEqual(profile["context_cache"]["device_state_slots"], slots)
                self.assertEqual(Decimal(profile["context_cache"]["host_context_mib"]) * (1024 ** 2),
                                 host_bytes)
                self.assertEqual(profile["speculative"], {"backend": "mtp", "draft_tokens": 3})
                self.assertTrue(profile["reasoning"]["thinking"])
                self.assertTrue(profile["reasoning"]["preserve_thinking"])
                self.assertTrue(profile["session_checkpoint"]["enabled"])
                self.assertTrue(profile["session_checkpoint"]["require_origin_auth"])
                self.assertEqual(profile["session_checkpoint"]["quota_mib"], 24576)
                self.assertEqual(profile["session_checkpoint"]["staging_mib"], 256)
                for obsolete in ("host_state_slots", "host_kv_mib", "max_private_continuations",
                                 "max_shared_prefixes", "max_long_anchors_per_continuation",
                                 "max_cache_markers_per_request"):
                    self.assertNotIn(obsolete, profile["context_cache"])

    def test_native_stage_binds_real_model_profiles_and_qualification(self) -> None:
        manifest = load(RELEASE / "manifest.json")
        qualification = load(RELEASE / "qualification.json")
        self.assertNotIn("native_model", manifest["components"])
        self.assertEqual(manifest["components"]["model"]["artifact_sha256"], MODEL_SHA)
        sources = set()
        for variant in manifest["components"]["ninfer_variants"]:
            number = variant["id"].split("-", 1)[0][3:]
            self.assertRegex(variant["release_tag"], rf"^v0\.7\.0-qwen38-{number}-beta\.[1-9][0-9]*$")
            self.assertEqual(variant["model_artifact_sha256"], MODEL_SHA)
            self.assertEqual(variant["configuration_sha256"], CONFIGS[number][0])
            path = ROOT / variant["qualification"]["summary"]
            receipt = load(path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                             variant["qualification"]["sha256"])
            self.assertEqual(receipt["identity"]["source_commit"], variant["source_commit"])
            self.assertEqual(receipt["identity"]["server_binary_sha256"],
                             variant["server_binary_sha256"])
            self.assertEqual(receipt["identity"]["configuration_sha256"],
                             variant["configuration_sha256"])
            self.assertEqual(receipt["package"]["sha256"], variant["package_sha256"])
            self.assertEqual(receipt["package"]["dependency_sbom_sha256"],
                             variant["sbom_dependency_sha256"])
            sources.add(variant["source_commit"])
            if qualification["status"] == "runtime-release-eligible":
                self.assertEqual(variant["release_tag"], f"v0.7.0-qwen38-{number}-beta.2")
                self.assertEqual(receipt["status"], "passed")
                self.assertEqual(receipt["protocol"]["protocol"]["structured_output"],
                                 {"chat_json_schema": True, "responses_json_schema": True})
        self.assertEqual(len(sources), 1)

    def test_release_local_matrix_is_rendered_and_lane_scoped(self) -> None:
        path = RELEASE / "compatibility.json"
        authority = render_compatibility.load_authority(path)
        if load(RELEASE / "qualification.json")["status"] == "runtime-release-eligible":
            for native in authority["runtime_contracts"][1:]:
                self.assertIn("Supported", native["json_schema"])
                self.assertEqual(native["tool_name_max_characters"], 128)
                self.assertEqual(native["status_schema_version"], 2)
                self.assertEqual(native["request_log_schema_version"], 30)
        self.assertEqual((RELEASE / "COMPATIBILITY.md").read_text(encoding="utf-8"),
                         render_compatibility.render(authority))

    def test_unpinned_preparation_preserves_published_root_authority(self) -> None:
        if load(RELEASE / "manifest.json")["status"] == "draft":
            self.assertEqual((ROOT / "compatibility.json").read_bytes(),
                             (ROOT / "releases/v0.13.0/compatibility.json").read_bytes())
            self.assertEqual((ROOT / "docs/COMPATIBILITY.md").read_bytes(),
                             (ROOT / "releases/v0.13.0/COMPATIBILITY.md").read_bytes())

    def test_notes_are_bounded_readable_and_keep_measurement_gates_distinct(self) -> None:
        from test_documented_route import ReleaseProseTests
        text = (RELEASE / "NINFER_RELEASE_NOTES.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 210)
        self.assertEqual(ReleaseProseTests.glued_tokens(text), [])
        if load(RELEASE / "qualification.json")["status"] == "runtime-release-eligible":
            for number in CONFIGS:
                receipt = load(RELEASE / "qualification" / f"rtx{number}.json")
                self.assertIn(f'{receipt["benchmark_c1"]["decode_tokens_per_second"]:.2f}', text)
                self.assertIn(f'{receipt["long_session"]["elapsed_seconds"]:.2f}', text)
        self.assertIn("640", text)
        self.assertIn("768", text)
        self.assertIn("session-checkpoints-v3", text)
        self.assertIn("ntfs-write-through", text)
        self.assertIn("documented_routes.document_change", text)
        self.assertIn("prompt_cache_key names a session capability", text)

    def test_native_beta2_allowlist_does_not_broaden_primary_5090_tags(self) -> None:
        for number in CONFIGS:
            variant_id = f"rtx{number}-windows-native"
            tag = f"v0.7.0-qwen38-{number}-beta.2"
            self.assertIsNotNone(
                render_compatibility.RUNTIME_VARIANT_RELEASE_TAG_RES[variant_id].fullmatch(tag))
            self.assertIsNone(verify_release.NINFER_RELEASE_TAG_RE.fullmatch(tag))
            other = "3090" if number == "4090" else "4090"
            self.assertIsNone(
                render_compatibility.RUNTIME_VARIANT_RELEASE_TAG_RES[variant_id].fullmatch(
                    f"v0.7.0-qwen38-{other}-beta.2"))
        self.assertIsNotNone(
            verify_release.NINFER_RELEASE_TAG_RE.fullmatch("v0.7.0-qwen38-5090-beta.2"))

    def test_receipt_audit_covers_every_staged_file_and_keeps_carried_bytes(self) -> None:
        audit = load(RELEASE / "qualification/receipt-audit.json")
        self.assertEqual(audit["release"], "v0.13.1")
        self.assertEqual(audit["source_release"], "v0.13.0")
        rows = {row["file"]: row for row in audit["files"]}
        staged = {path.name for path in (RELEASE / "qualification").iterdir() if path.is_file()}
        self.assertEqual(staged, {
            name for name, row in rows.items() if row["disposition"] != "dropped"
        })
        for name, row in rows.items():
            if row["disposition"] == "kept-unchanged-subject":
                self.assertEqual((RELEASE / "qualification" / name).read_bytes(),
                                 (ROOT / "releases/v0.13.0/qualification" / name).read_bytes())

    def test_pending_native_council_cannot_inherit_5090_approval(self) -> None:
        qualification = load(RELEASE / "qualification.json")
        gate = qualification["observed_gates"]["g4_review"]
        if gate["status"] == "pending":
            ledger = load(ROOT / gate["repository_path"])
            self.assertFalse(ledger["approval_granted"])
            self.assertFalse(ledger["publication_authorized"])
            self.assertFalse(ledger["public_route_acceptance_granted"])
            carried = ledger["carried_rtx5090_review"]
            path = ROOT / carried["repository_path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), carried["sha256"])
            self.assertIn("no native", carried["scope"].lower())


if __name__ == "__main__":
    unittest.main()
