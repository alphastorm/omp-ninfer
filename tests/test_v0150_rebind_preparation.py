"""The prepared RTX 3090 guide binds real F2 evidence, not a fabricated screen or lane pin."""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import documented_route
import verify_release

RELEASE = ROOT / "releases/v0.15.0"
SOURCE = "2af6b3dec467e61d284889c69e903eef464bda97"
TAG = "v0.8.0-qwen38-3090-beta.1"
PACKAGE = "ninfer-rtx3090-native-v0.8.0-beta.1-windows-x86_64-cuda13.3-rtx3090.tar.gz"
DOWNLOAD = f"https://github.com/alphastorm/ninfer/releases/download/{TAG}"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class V0150RebindPreparationTests(unittest.TestCase):
    def test_exact_qualification_fit_and_packaged_configuration_are_staged(self) -> None:
        expected = {
            "qualification/rtx3090.json":
                "48e517c8a794217e4d4d1164d445ea3b8bf59d4c8c203fe54416547d39f57c2b",
            "qualification/rtx3090-windows-native.fit.json":
                "1716e71d1bbcecdc2fbc758747653579d63443fcb2bfb9c372985951d267eebf",
            "profiles/rtx3090/server-config.json":
                "55788a647fb250a37754076a2d8f28d542119fb88191428bbaeb7be076ee43aa",
        }
        for relative, digest in expected.items():
            with self.subTest(path=relative):
                raw = (RELEASE / relative).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
                text = raw.decode("utf-8")
                for marker in verify_release.PRIVATE_MARKERS:
                    self.assertNotIn(marker, text)
                self.assertNotRegex(text, r"[A-Za-z]:[\\/]")
                self.assertNotRegex(text, r"(?i)\b(?:GPU-)?[0-9a-f]{8}-[0-9a-f]{4}-"
                                    r"[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")

    def test_fit_and_qualification_identify_the_same_shipping_bytes(self) -> None:
        receipt = load(RELEASE / "qualification/rtx3090.json")
        fit = load(RELEASE / "qualification/rtx3090-windows-native.fit.json")
        self.assertEqual(receipt["status"], "passed")
        self.assertEqual(receipt["identity"]["source_commit"], SOURCE)
        self.assertEqual(receipt["package"]["filename"], PACKAGE)
        self.assertEqual(len(receipt["orchestration_evidence"]), 15)
        self.assertEqual({row["status"] for row in receipt["orchestration_evidence"].values()},
                         {"passed"})
        self.assertEqual(receipt["rollback"]["status"], "not_applicable")
        self.assertEqual(receipt["rollback"]["directions"], 0)
        self.assertEqual(fit["runtime_shape"], receipt["runtime_shape"])
        self.assertEqual(fit["identity"]["package_sha256"], receipt["package"]["sha256"])
        for field in ("server_binary_sha256", "configuration_sha256", "model_artifact_sha256"):
            self.assertEqual(fit["identity"][field], receipt["identity"][field])
        errors = []
        variant = {
            "id": "rtx3090-windows-native",
            **fit["identity"],
            "runtime_shape": fit["runtime_shape"],
            "maximum_context_tokens": 131072,
            "qualification": {"fit": {
                "path": "releases/v0.15.0/qualification/rtx3090-windows-native.fit.json",
                "sha256": hashlib.sha256(
                    (RELEASE / "qualification/rtx3090-windows-native.fit.json").read_bytes()
                ).hexdigest(),
            }},
        }
        verify_release.validate_native_fit(ROOT, "v0.15.0", variant, errors)
        self.assertEqual(errors, [])

    def test_packaged_fit_uses_measured_native_host_translation(self) -> None:
        config = load(RELEASE / "profiles/rtx3090/server-config.json")
        fit = load(RELEASE / "qualification/rtx3090-windows-native.fit.json")
        self.assertEqual(config["speculative"], {"backend": "dflash2", "draft_tokens": 7})
        self.assertEqual(config["context_cache"]["device_state_slots"], 0)
        self.assertEqual(config["engine"]["admission_headroom_mib"], 768)
        host_bytes = Decimal(config["context_cache"]["host_context_mib"]) * 1024 ** 2
        self.assertEqual(host_bytes, fit["host_context_bytes"])
        self.assertEqual(host_bytes, 8192 * 1024 ** 2 + 24 * fit["native_state_image_bytes"])
        self.assertTrue(config["session_checkpoint"]["require_origin_auth"])
        self.assertEqual(fit["durability"]["cold_cached_input_tokens"], 0)
        self.assertEqual(fit["durability"]["restored_input_tokens"], 3066)
        self.assertTrue(fit["durability"]["output_bytes_identical"])
        self.assertTrue(fit["durability"]["generated_token_ids_identical"])

    def test_incoming_receipt_cannot_qualify_the_old_manifest_before_gated_binding(self) -> None:
        manifest = load(RELEASE / "manifest.json")
        variant = next(row for row in manifest["components"]["ninfer_variants"]
                       if row["id"] == "rtx3090-windows-native")
        errors = []
        verify_release.validate_ninfer_variants(
            ROOT, "v0.15.0", [variant], load(RELEASE / "compatibility.json"),
            verify_release.effective_native_model(manifest)["artifact_sha256"], errors,
            allow_pending=manifest["status"] == "draft",
        )
        if variant["source_commit"] == SOURCE:
            self.assertEqual(errors, [])
        else:
            self.assertEqual(manifest["status"], "draft")
            self.assertNotEqual(variant["package_sha256"],
                                load(RELEASE / "qualification/rtx3090.json")["package"]["sha256"])
            self.assertIn("components.ninfer_variants.rtx3090-windows-native.qualification "
                          "SHA-256 must match receipt bytes", errors)

    def test_3090_guide_prose_names_the_prepared_component_and_transition_scope(self) -> None:
        guide = documented_route.DEFAULT_DOC.read_text(encoding="utf-8")
        section = guide.split("## Native Windows RTX 3090 release lane\n", 1)[1].split(
            "```powershell", 1)[0]
        for value in (TAG, SOURCE[:8], f"{DOWNLOAD}/{PACKAGE}", f"{DOWNLOAD}/SHA256SUMS",
                      "8536cdff", "971,617,000 bytes", "350 W to 350 W",
                      "zero extra", "same-instance reinstall", "not_applicable",
                      "MTP3 checkpoint generations must not enter", "prior_paused=true",
                      "https://github.com/alphastorm/omp-ninfer/issues/116"):
            self.assertIn(value, section)
        self.assertNotIn("stop the running RTX 3090 lane before installing v0.14.0", section)
        row = next(line for line in guide.splitlines()
                   if line.startswith("| RTX 3090 native Windows (`"))
        for value in (TAG, "8536cdff", "05cb97e4", "55788a64", "DFlash2 K7/INT8",
                      "12,675.734375 MiB", "768 MiB", "Q4_G64_FP16", "host-mapped"):
            self.assertIn(value, row)
        self.assertIn("qwen38-3090-native-v0.8.0-beta.1", guide)

    def test_all_seven_3090_blocks_and_both_shared_dispatches_keep_dynamic_install_flow(self) -> None:
        steps = {step.slug: block.text for step, block in documented_route.lane_blocks(
            documented_route.DEFAULT_DOC, "rtx3090-native")}
        self.assertEqual(len(steps), 7)
        self.assertIn("v0.15.0", steps["clone-and-verify"])
        self.assertIn("--require-ready", steps["clone-and-verify"])
        self.assertIn("'rtx3090-windows-native'", steps["variant"])
        for heading in ("Native Windows RTX 3090 release lane",
                        "Native Windows RTX 4090 release lane"):
            install = documented_route.extract(documented_route.DEFAULT_DOC, heading, 2).text
            for binding in ("releases\\v0.15.0\\manifest.json", "$Variant[0].package_url",
                            "$Variant[0].package_sha256", "$Variant[0].installer_url",
                            "$Variant[0].controller_url", "$Variant[0].model_artifact_sha256"):
                self.assertIn(binding, install)
            self.assertNotIn(TAG, install)
        provider = documented_route.extract(
            documented_route.DEFAULT_DOC, "Point OMP at the native lane").text
        self.assertIn("'ninfer-native-3090'", provider)
        self.assertIn("'ninfer-native-3090'", steps["provider"])
        self.assertIn('"$Provider/q38-ninfer"', steps["acceptance"])

    def test_notes_fill_only_observed_results_without_substituting_c1_for_abba(self) -> None:
        notes = (RELEASE / "NINFER_RELEASE_NOTES.md").read_text(encoding="utf-8")
        placeholders = set(re.findall(r"<(RTX3090_[A-Z_]+)>", notes))
        self.assertLessEqual(placeholders, {
            "RTX3090_SCREEN_VERDICT_AND_BOUNDS",
            "RTX3090_SPEED_RATIO_MIN_AND_BYTE_IDENTITY_COUNTS",
            "RTX3090_AGENT_PROBE_RESULTS",
        })
        self.assertNotIn("RTX3090_FIT_PEAK_HEADROOM_AND_DURABILITY", notes)
        for value in (SOURCE, "34/34", "21,968 MiB", "2,358 MiB", "3,066", "32",
                      "not an ABBA speed ratio", "11/11", "2 accept / 8 defer",
                      "https://github.com/alphastorm/omp-ninfer/issues/116"):
            self.assertIn(value, notes)


if __name__ == "__main__":
    unittest.main()
