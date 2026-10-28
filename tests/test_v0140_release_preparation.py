"""Bind the three beta.3 lanes without transferring predecessor acceptance or review."""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import documented_route
import render_compatibility
import verify_release

RELEASE = ROOT / "releases/v0.14.0"
SOURCE = "2c6f423bd817b6534158553e1b34ab4959c43165"
MODEL = "81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da"
CONFIG = "751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47"
NATIVE_CONFIGS = {
    "4090": "b5cfbf50d264831832fbe69458b56629a65b0d5b5295ec8bbbd4ea2d73002c38",
    "3090": "d08d262bfe939ed9aaa6f7053ab8a8304fb7e3fef50dad3cb9329e28fb4ece15",
}
SERVERS = {
    "5090": "55f0b95ac3609673ff544d9a512fb28aee9580b5948719dfac537858b6714467",
    "4090": "5caa778029ba973ed06446f002d9da95faba0d70d66cb033abee7c4b88ad46e9",
    "3090": "fedce425c09b3eca249d7ae3b4f8dcfe4a6839a82befa6168f77625ef6ec04c3",
}
NATIVE_SHAPES = {
    "4090": (2, 2048, 15506063360, 640, 60000, "qwen3.8-27b"),
    "3090": (4, 1024, 12284837888, 768, 0, "q38-ninfer"),
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class V0140PreparationTests(unittest.TestCase):
    def test_prepared_guide_keeps_publication_and_acceptance_gated(self) -> None:
        text = documented_route.DEFAULT_DOC.read_text(encoding="utf-8")
        self.assertIn(
            "> **Prepared guide: v0.14.0 · stock Oh My Pi 18.12.6 · product-route qualification pending**",
            text)
        self.assertIn("Do not execute these install blocks before the product is published",
                      " ".join(text.split()))
        self.assertIn("The published release remains v0.13.1:", text)
        published = "https://github.com/alphastorm/omp-ninfer/blob/v0.13.1/docs/QUICKSTART.md"
        self.assertIn(f"[use its immutable guide]({published})", text)
        self.assertIn("documented_routes.document_change", text)
        self.assertIn("## Previous release acceptance — v0.13.1", text)
        self.assertIn("predecessor acceptance does not transfer", text)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"[published-guide]: {published}", readme)
        self.assertIn("### [Get started →][published-guide]", readme)

    def test_prepared_guide_lane_identities_match_the_candidate_manifest(self) -> None:
        manifest = load(RELEASE / "manifest.json")
        text = documented_route.DEFAULT_DOC.read_text(encoding="utf-8")
        self.assertIn(SOURCE, text)
        glance = text.split("## Prepared composition at a glance\n", 1)[1].split(
            "\n- **Serving limits", 1)[0]
        primary = manifest["components"]["ninfer"]
        self.assertIn(primary["release_tag"], glance)
        self.assertIn(primary["oci_reference"], glance)
        self.assertIn(primary["server_binary_sha256"][:8], glance)
        self.assertIn(manifest["runtime_identity"]["deployment_profile"], glance)
        self.assertIn(CONFIG[:8], glance)
        self.assertIn("20,437,521,664 bytes", glance)
        for variant in manifest["components"]["ninfer_variants"]:
            number = variant["id"].split("-", 1)[0][3:]
            row = next(line for line in glance.splitlines()
                       if line.startswith(f"| RTX {number} native Windows"))
            with self.subTest(lane=number):
                for value in (variant["release_tag"], variant["source_commit"][:8],
                              variant["package_sha256"][:8], variant["server_binary_sha256"][:8],
                              variant["configuration_sha256"][:8], MODEL[:8],
                              f"qwen38-{number}-native-v0.7.0-beta.3",
                              "MTP3/INT8", "`Group64` A8 off"):
                    self.assertIn(value, row)
                if number == "3090":
                    self.assertIn("350 W serving cap", row)
        self.assertNotIn("beta.2", glance)
        self.assertIn("founder-approved 5090-only reproducibility exception", glance)

    def test_native_3090_upgrade_requires_stop_before_the_first_install_block(self) -> None:
        text = documented_route.DEFAULT_DOC.read_text(encoding="utf-8")
        section = text.split("## Native Windows RTX 3090 release lane\n", 1)[1].split(
            "```powershell", 1)[0]
        for claim in ("stop the running RTX 3090 lane before installing v0.14.0",
                      "installed controller's `Stop` action", "300 W GPU-owner lease",
                      "350 W serving cap", "A stopped lane upgrades normally",
                      "https://github.com/alphastorm/omp-ninfer/issues/94"):
            self.assertIn(claim, section)

    def test_three_lanes_bind_one_exact_engine_source(self) -> None:
        manifest = load(RELEASE / "manifest.json")
        self.assertNotIn("native_model", manifest["components"])
        self.assertEqual(manifest["components"]["model"]["artifact_sha256"], MODEL)
        primary = manifest["components"]["ninfer"]
        self.assertEqual(primary["source_commit"], SOURCE)
        self.assertEqual(primary["release_tag"], "v0.7.0-qwen38-5090-beta.3")
        self.assertEqual(primary["server_binary_sha256"], SERVERS["5090"])
        qualification = load(RELEASE / "qualification.json")
        self.assertEqual(qualification["observed_gates"]["native_packaging"]["status"], "passed")
        for variant in manifest["components"]["ninfer_variants"]:
            number = variant["id"].split("-", 1)[0][3:]
            self.assertEqual(variant["source_commit"], SOURCE)
            self.assertEqual(variant["release_tag"], f"v0.7.0-qwen38-{number}-beta.3")
            self.assertEqual(variant["server_binary_sha256"], SERVERS[number])
            self.assertEqual(variant["model_artifact_sha256"], MODEL)
            self.assertEqual(variant["configuration_sha256"], NATIVE_CONFIGS[number])
            self.assertEqual(variant["status"], "qualified")
            self.assertTrue(variant["installable"])
            path = ROOT / variant["qualification"]["summary"]
            receipt = load(path)
            self.assertEqual(sha(path), variant["qualification"]["sha256"])
            for key in ("source_commit", "server_binary_sha256", "configuration_sha256"):
                self.assertEqual(receipt["identity"][key], variant[key])
            self.assertEqual(receipt["status"], "passed")
            self.assertEqual(receipt["package"]["sha256"], variant["package_sha256"])
            self.assertEqual(receipt["package"]["dependency_sbom_sha256"],
                             variant["sbom_dependency_sha256"])
            self.assertEqual(receipt["protocol"]["protocol"]["structured_output"],
                             {"chat_json_schema": True, "responses_json_schema": True})
            checksums = RELEASE / "qualification" / f"{variant['id']}.SHA256SUMS"
            self.assertEqual(sha(checksums), variant["checksums_sha256"])

    def test_primary_archive_sizes_checksums_and_kept_profile_are_current(self) -> None:
        manifest = load(RELEASE / "manifest.json")
        primary = manifest["components"]["ninfer"]
        self.assertEqual(primary["binary_archive_bytes"], 547378794)
        self.assertEqual(primary["source_archive_bytes"], 12538488)
        self.assertEqual(primary["checksums_sha256"],
                         "9f5ed2e607345c23e97f7616ebba8f59ed18293a614e1fd337ffe4084c4366cc")
        self.assertEqual(primary["binary_archive_sha256"],
                         "b8f315bc3d735c1263d69ed2789bc5b4a6fc10c0652384fcd935d0137c9699fa")
        self.assertEqual(primary["source_archive_sha256"],
                         "1964794f3b48998634b52c5bdc3fdf8a029e78d673af79b4c6211dc95fc161ff")
        self.assertEqual(manifest["runtime_identity"]["configuration_sha256"], CONFIG)
        self.assertEqual(manifest["runtime_identity"]["deployment_profile"],
                         "qwen38-5090-v0.13.0")
        base = load(RELEASE / "qualification/runtime-base.json")
        self.assertEqual(base["runtime_source_commit"], SOURCE)
        self.assertEqual(base["original_publication"]["source_commit"],
                         "04b603aae4e9ce3c26f4175cf808180c0f05b5fe")
        self.assertEqual(base["base_image_reference"], primary["runtime_base_reference"])
        publication = load(RELEASE / "qualification/runtime-publication.json")
        self.assertEqual(publication["schema_version"], 4)
        self.assertEqual(publication["source_commit"], SOURCE)
        self.assertEqual(publication["image_reference"], primary["oci_reference"])
        self.assertEqual(publication["binary_sha256"], primary["binary_archive_sha256"])

    def test_native_profiles_preserve_exact_packaged_bytes_and_supported_shapes(self) -> None:
        manifest = load(RELEASE / "manifest.json")
        variants = {row["id"]: row for row in manifest["components"]["ninfer_variants"]}
        for number, (slots, prefill, host_bytes, headroom, keep_warm, model_id) in NATIVE_SHAPES.items():
            with self.subTest(lane=number):
                path = ROOT / f"profiles/v0.14.0/rtx{number}/server-config.json"
                self.assertEqual(path.read_bytes(),
                                 (RELEASE / f"profiles/rtx{number}/server-config.json").read_bytes())
                self.assertEqual(sha(path), variants[f"rtx{number}-windows-native"]["configuration_sha256"])
                raw = path.read_bytes()
                self.assertNotIn(b"\r", raw)
                self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
                self.assertTrue(raw.endswith(b"\n"))
                profile = json.loads(raw)
                self.assertEqual(profile["artifact_type"], "ninfer_windows_server_config")
                self.assertEqual(profile["schema_version"], 4)
                identity = f"qwen38-{number}-native-v0.7.0-beta.3"
                self.assertEqual(profile["release_id"], identity)
                self.assertEqual(profile["deployment_profile"], identity)
                self.assertEqual(profile["listen"], {
                    "host": "127.0.0.1",
                    "port": 18082,
                    "allowed_host_classes": ["loopback", "tailscale-ipv4"],
                })
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
                self.assertEqual(Decimal(profile["context_cache"]["host_context_mib"]) * 1024 ** 2,
                                 host_bytes)
                self.assertEqual(profile["speculative"], {"backend": "mtp", "draft_tokens": 3})
                self.assertTrue(profile["session_checkpoint"]["require_origin_auth"])
                for obsolete in ("host_state_slots", "host_kv_mib", "max_private_continuations"):
                    self.assertNotIn(obsolete, profile["context_cache"])

    def test_native_selection_publication_and_scratch_scope_are_explicit(self) -> None:
        integration = load(RELEASE / "qualification/native-integration.json")
        publication = load(RELEASE / "qualification/native-publication.json")
        self.assertEqual(integration["identity"]["source_commit"], SOURCE)
        self.assertEqual(publication["identity"]["source_commit"], SOURCE)
        for lane in ("rtx4090", "rtx3090"):
            with self.subTest(lane=lane):
                bound = integration["lanes"][lane]
                self.assertEqual(bound["selection"]["group64_a8"], "OFF")
                self.assertEqual(bound["hardware_qualification"]["recorded_phase_count"], 15)
                self.assertFalse(bound["scratch_equivalence"]["public_package_executed"])
                self.assertEqual(bound["rollback"]["status"], "not_applicable")
                self.assertEqual(bound["rollback"]["directions"], 0)
                cut = next(row for row in publication["lanes"] if row["lane"] == lane)
                self.assertTrue(cut["published"])
                self.assertEqual(cut["preflight_exit"], 0)
                self.assertEqual((cut["outer_hashed_entries"], cut["total_distribution_files"]),
                                 (10, 11))
        self.assertEqual(integration["lanes"]["rtx3090"]["selection"]["qualified_power_limit_w"], 350)
        self.assertEqual(integration["lanes"]["rtx3090"]["selection"]["restored_power_limit_w"], 370)

    def test_reproducibility_exception_is_explicit_and_shipping_byte_scoped(self) -> None:
        build = load(RELEASE / "qualification/build.json")
        self.assertEqual(build["identity"]["server_binary_sha256"], SERVERS["5090"])
        reproducibility = build["reproducibility"]
        self.assertEqual(reproducibility["status"], "founder-approved-exception")
        self.assertFalse(reproducibility["bit_identical"])
        self.assertEqual(reproducibility["shipping_round"], 1)
        self.assertEqual(reproducibility["first_pair_differing_files"], 249)
        self.assertEqual(reproducibility["corrected_pair_differing_files"], 177)
        parity = load(RELEASE / "qualification/decode-parity.json")
        self.assertEqual(parity["identity"]["server_binary_sha256"], SERVERS["5090"])
        self.assertEqual(parity["measured"]["role_cases"], 84)
        self.assertEqual(parity["measured"]["output_hash_matches_all_arms"], 84)
        self.assertIn("not retained-byte", parity["scope"])

    def test_release_local_matrix_and_draft_authority_are_not_prematurely_promoted(self) -> None:
        authority = render_compatibility.load_authority(RELEASE / "compatibility.json")
        self.assertEqual((RELEASE / "COMPATIBILITY.md").read_text(encoding="utf-8"),
                         render_compatibility.render(authority))
        self.assertEqual({row["id"] for row in authority["runtime_variants"]},
                         {"rtx4090-windows-native", "rtx3090-windows-native"})
        self.assertTrue(all(row["source_commit"] == SOURCE for row in authority["runtime_variants"]))
        if load(RELEASE / "manifest.json")["status"] == "draft":
            self.assertEqual((ROOT / "compatibility.json").read_bytes(),
                             (ROOT / "releases/v0.13.1/compatibility.json").read_bytes())
            self.assertEqual((ROOT / "docs/COMPATIBILITY.md").read_bytes(),
                             (ROOT / "releases/v0.13.1/COMPATIBILITY.md").read_bytes())

    def test_receipt_audit_accounts_for_every_predecessor_and_current_file(self) -> None:
        audit = load(RELEASE / "qualification/receipt-audit.json")
        self.assertEqual((audit["source_release"], audit["release"]), ("v0.13.1", "v0.14.0"))
        rows = {row["file"]: row for row in audit["files"]}
        previous = ROOT / "releases/v0.13.1/qualification"
        current = RELEASE / "qualification"
        self.assertEqual(set(rows), {path.name for path in previous.iterdir() if path.is_file()}
                         | {path.name for path in current.iterdir() if path.is_file()})
        self.assertEqual({name for name, row in rows.items() if row["disposition"] != "dropped"},
                         {path.name for path in current.iterdir() if path.is_file()})
        for name, row in rows.items():
            with self.subTest(file=name):
                self.assertTrue(row["reason"])
                if name != "receipt-audit.json" and row["disposition"] != "dropped":
                    self.assertEqual(sha(current / name), row["staged_sha256"])
                if (previous / name).is_file():
                    self.assertEqual(sha(previous / name), row["predecessor_sha256"])
                if row["disposition"] == "kept-unchanged-subject":
                    self.assertIn(name, {"stock-omp.json", "client-components.json"})
                    self.assertEqual((current / name).read_bytes(), (previous / name).read_bytes())

    def test_staged_acceptance_and_review_do_not_inherit_predecessor_approval(self) -> None:
        qualification = load(RELEASE / "qualification.json")
        if load(RELEASE / "manifest.json")["status"] in {"draft", "candidate"}:
            self.assertFalse(qualification["external_installation_qualified"])
            self.assertEqual(qualification["documented_route_acceptance"]["status"], "pending")
            self.assertFalse((RELEASE / "acceptance").exists())
        gate = qualification["observed_gates"]["g4_review"]
        if gate["status"] == "pending":
            ledger = load(ROOT / gate["repository_path"])
            for key in ("approval_granted", "publication_authorized", "public_route_acceptance_granted"):
                self.assertFalse(ledger[key])
            self.assertNotIn("carried_rtx5090_review", ledger)

    def test_notes_are_bounded_and_distinguish_measurement_acceptance_and_exception(self) -> None:
        from test_documented_route import ReleaseProseTests
        text = (RELEASE / "NINFER_RELEASE_NOTES.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 210)
        self.assertEqual(ReleaseProseTests.glued_tokens(text), [])
        for claim in ("350 W", "A8 remains off", "reproducibility exception", "not retained",
                      "151.573", "90.879", "347.57", "session-checkpoints-v3", "ntfs-write-through",
                      "documented_routes.document_change", "prompt_cache_key names a session capability",
                      "stop the running RTX 3090 lane", "300 W GPU-owner lease", "#94", "#95", "#96"):
            self.assertIn(claim, text)

    def test_beta3_tags_remain_lane_scoped(self) -> None:
        self.assertIsNotNone(verify_release.NINFER_RELEASE_TAG_RE.fullmatch(
            "v0.7.0-qwen38-5090-beta.3"))
        for number in NATIVE_SHAPES:
            tag = f"v0.7.0-qwen38-{number}-beta.3"
            self.assertIsNotNone(render_compatibility.RUNTIME_VARIANT_RELEASE_TAG_RES[
                f"rtx{number}-windows-native"].fullmatch(tag))
            self.assertIsNone(verify_release.NINFER_RELEASE_TAG_RE.fullmatch(tag))


if __name__ == "__main__":
    unittest.main()
