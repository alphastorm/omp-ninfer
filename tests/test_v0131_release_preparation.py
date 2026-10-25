"""Native preparation binds real public config bytes, never invented cut or acceptance proof."""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render_compatibility

RELEASE = ROOT / "releases/v0.13.1"
MODEL_SHA = "81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da"
CONFIGS = {
    "4090": ("9774e70154007aa2e803f7d31766e2edb274209b5b2d48f00429472cea6af4fe",
             2, 2048, 15506063360, 640, 60000, "qwen3.8-27b"),
    "3090": ("73a33e63db44ecb15bb0a64a39b7f77783c14285543c72977ac0a0675bc00c7d",
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
                identity = f"qwen38-{number}-native-v0.7.0-beta.1"
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

    def test_preparation_has_no_fake_manifest_or_runtime_acceptance(self) -> None:
        manifest_path = RELEASE / "manifest.json"
        qualification = load(RELEASE / "qualification.json")
        if not manifest_path.exists():
            self.assertEqual({path.name for path in RELEASE.iterdir()},
                             {"NINFER_RELEASE_NOTES.md", "qualification.json",
                              "compatibility.json", "COMPATIBILITY.md"})
            self.assertEqual(qualification["status"], "preparation-only")
            self.assertFalse(qualification["publication_authorized"])
            self.assertFalse(qualification["external_installation_qualified"])
            gates = qualification["observed_gates"]
            self.assertEqual(gates["native_packaging"]["status"], "pending")
            self.assertEqual(gates["native_protocol"]["status"], "pending")
            self.assertEqual(gates["native_precut_decode"]["status"], "measured-not-release-qualified")
            self.assertEqual(gates["native_precut_decode"]["rtx4090_tokens_per_second"], 137.35)
            self.assertEqual(gates["native_precut_decode"]["rtx3090_tokens_per_second"], 78.33)
        else:
            manifest = load(manifest_path)
            self.assertNotIn("native_model", manifest["components"])
            self.assertEqual(manifest["components"]["model"]["artifact_sha256"], MODEL_SHA)
            for variant in manifest["components"]["ninfer_variants"]:
                number = variant["id"].split("-", 1)[0][3:]
                self.assertEqual(variant["release_tag"], f"v0.7.0-qwen38-{number}-beta.1")
                self.assertEqual(variant["model_artifact_sha256"], MODEL_SHA)
                self.assertEqual(variant["configuration_sha256"], CONFIGS[number][0])

    def test_prepared_matrix_is_rendered_and_cannot_be_installed(self) -> None:
        path = RELEASE / "compatibility.json"
        authority = load(path)
        if authority.get("artifact_type") == "omp_ninfer_prepared_compatibility":
            with self.assertRaisesRegex(ValueError, "not an installable authority"):
                render_compatibility.load_authority(path)
            authority = render_compatibility.load_authority(path, allow_prepared=True)
            self.assertEqual(authority["status"], "preparation-only")
            self.assertEqual(authority["native_model_transition"]["to_artifact_sha256"], MODEL_SHA)
            for native in authority["runtime_contracts"][1:]:
                self.assertIn("Gated", native["json_schema"])
                self.assertIn("not yet qualified", native["lane"])
        else:
            authority = render_compatibility.load_authority(path)
        self.assertEqual((RELEASE / "COMPATIBILITY.md").read_text(encoding="utf-8"),
                         render_compatibility.render(authority))

    def test_unpinned_preparation_preserves_published_root_authority(self) -> None:
        manifest_path = RELEASE / "manifest.json"
        if not manifest_path.exists() or load(manifest_path)["status"] == "draft":
            self.assertEqual((ROOT / "compatibility.json").read_bytes(),
                             (ROOT / "releases/v0.13.0/compatibility.json").read_bytes())
            self.assertEqual((ROOT / "docs/COMPATIBILITY.md").read_bytes(),
                             (ROOT / "releases/v0.13.0/COMPATIBILITY.md").read_bytes())

    def test_notes_are_bounded_readable_and_keep_measurement_gates_distinct(self) -> None:
        from test_documented_route import ReleaseProseTests
        text = (RELEASE / "NINFER_RELEASE_NOTES.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 210)
        self.assertEqual(ReleaseProseTests.glued_tokens(text), [])
        self.assertIn("137.35", text)
        self.assertIn("78.33", text)
        self.assertIn("Pre-cut experiment", text)
        self.assertIn("documented_routes.document_change", text)
        self.assertIn("prompt_cache_key names a session capability", text)


if __name__ == "__main__":
    unittest.main()
