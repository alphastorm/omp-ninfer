from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Immutable ready fixture; root authority may legitimately be a newer candidate.
PUBLIC_RELEASE = "v0.10.0"
ACCEPTED_PROFILES = ROOT / "tests/fixtures/profiles-v0.12.2"
SPEC = importlib.util.spec_from_file_location(
    "verify_release", ROOT / "scripts" / "verify_release.py"
)
assert SPEC is not None and SPEC.loader is not None
VERIFY_RELEASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY_RELEASE)
STAGE_SPEC = importlib.util.spec_from_file_location("stage_release", ROOT / "scripts/stage_release.py")
assert STAGE_SPEC is not None and STAGE_SPEC.loader is not None
STAGE_RELEASE = importlib.util.module_from_spec(STAGE_SPEC)
STAGE_SPEC.loader.exec_module(STAGE_RELEASE)
REBIND_SPEC = importlib.util.spec_from_file_location("rebind_release", ROOT / "scripts/rebind_release.py")
assert REBIND_SPEC is not None and REBIND_SPEC.loader is not None
REBIND_RELEASE = importlib.util.module_from_spec(REBIND_SPEC)
REBIND_SPEC.loader.exec_module(REBIND_RELEASE)


class DependencySbomContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.release = ROOT / "releases" / PUBLIC_RELEASE
        self.manifest = json.loads((self.release / "manifest.json").read_text(encoding="utf-8"))
        self.authority = json.loads((self.release / "compatibility.json").read_text(encoding="utf-8"))
        self.variant = self.manifest["components"]["ninfer_variants"][-1]
        self.prefix = f"components.ninfer_variants.{self.variant['id']}"
        self.dependency_name = self.variant["package_name"].removesuffix(".tar.gz") + ".cdx.json"
        self.pins = {"sbom_dependency_url": (
            f"https://github.com/alphastorm/ninfer/releases/download/"
            f"{self.variant['release_tag']}/{self.dependency_name}"),
            "sbom_dependency_sha256": "a" * 64}

    def validate(self, pins: dict) -> list[str]:
        variants = deepcopy(self.manifest["components"]["ninfer_variants"])
        variants[-1].update(pins)
        errors = []
        VERIFY_RELEASE.validate_ninfer_variants(
            ROOT, PUBLIC_RELEASE, variants, self.authority,
            VERIFY_RELEASE.effective_native_model(self.manifest)["artifact_sha256"], errors)
        return errors

    def test_older_variants_without_dependency_sbom_and_complete_pins_are_accepted(self) -> None:
        self.assertEqual(self.validate({}), [])
        self.assertEqual(self.validate(self.pins), [])

    def test_present_dependency_pins_are_atomic_and_release_bound_even_in_drafts(self) -> None:
        for pins, expected in (
            ({"sbom_dependency_url": self.pins["sbom_dependency_url"]}, "sbom_dependency_sha256"),
            ({"sbom_dependency_sha256": "a" * 64}, "sbom_dependency_url"),
            ({**self.pins, "sbom_dependency_sha256": "A" * 64}, "sbom_dependency_sha256"),
            ({**self.pins, "sbom_dependency_url": "http://example.invalid/bom.json"}, "sbom_dependency_url"),
            ({**self.pins, "sbom_dependency_url": self.pins["sbom_dependency_url"].replace(
                self.variant["release_tag"], "wrong-component")}, "must bind its component release"),
            ({**self.pins, "sbom_dependency_url": self.pins["sbom_dependency_url"].replace(
                ".cdx.json", ".spdx.json")}, "canonical"),
            ({"sbom_dependency_url": None, "sbom_dependency_sha256": None}, "sbom_dependency_sha256"),
        ):
            with self.subTest(pins=pins):
                self.assertTrue(any(expected in error for error in self.validate(pins)))
                errors = []
                VERIFY_RELEASE.validate_dependency_sbom({**self.variant, **pins}, self.prefix, errors)
                self.assertTrue(any(expected in error for error in errors))

    def test_optional_checksum_entry_cannot_disagree_with_the_dependency_pin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "releases" / PUBLIC_RELEASE / "qualification" / f"{self.variant['id']}.SHA256SUMS"
            target.parent.mkdir(parents=True)
            original = (self.release / "qualification" / target.name).read_text(encoding="utf-8")
            variant = {**self.variant, **self.pins}
            for checksum, expected_count in (("a" * 64, 0), ("b" * 64, 1)):
                target.write_text(original + f"{checksum}  {self.dependency_name}\n", encoding="utf-8")
                variant["checksums_sha256"] = VERIFY_RELEASE.sha256_file(target)
                errors = []
                VERIFY_RELEASE.validate_variant_checksums(root, PUBLIC_RELEASE, variant, self.prefix, errors)
                self.assertEqual(len(errors), expected_count, errors)
                if errors:
                    self.assertIn("must match sbom_dependency_sha256", errors[0])

    def test_rebased_components_require_canonical_dependency_pins_and_outer_checksum_entry(self) -> None:
        for lane in ("3090", "4090"):
            package = f"ninfer-rtx{lane}-native-v0.7.0-beta.1-windows-x86_64-cuda13.3-rtx{lane}.tar.gz"
            tag = f"v0.7.0-qwen38-{lane}-beta.1"
            dependency = package.removesuffix(".tar.gz") + ".cdx.json"
            item = {"release_tag": tag, "package_name": package}
            errors = []
            VERIFY_RELEASE.validate_dependency_sbom(item, self.prefix, errors)
            self.assertTrue(any("sbom_dependency_sha256" in error for error in errors))
            item.update(sbom_dependency_url=(
                f"https://github.com/alphastorm/ninfer/releases/download/{tag}/{dependency}"),
                sbom_dependency_sha256="a" * 64)
            errors = []
            VERIFY_RELEASE.validate_dependency_sbom(item, self.prefix, errors)
            self.assertEqual(errors, [])

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "releases" / PUBLIC_RELEASE / "qualification" / f"{self.variant['id']}.SHA256SUMS"
            target.parent.mkdir(parents=True)
            target.write_bytes((self.release / "qualification" / target.name).read_bytes())
            item = {**self.variant, **self.pins, "release_tag": "v0.7.0-qwen38-4090-beta.1",
                    "checksums_sha256": VERIFY_RELEASE.sha256_file(target)}
            errors = []
            VERIFY_RELEASE.validate_variant_checksums(root, PUBLIC_RELEASE, item, self.prefix, errors)
            self.assertEqual(len(errors), 1)
            self.assertIn("must match sbom_dependency_sha256", errors[0])

    def test_rebased_native_cannot_promote_a_legacy_protocol_receipt(self) -> None:
        # The immutable old receipt remains accepted under its actual old component tag,
        # but changing the tag cannot promote its legacy protocol fields to native v0.7.0.
        self.assertEqual(self.validate({}), [])
        errors = self.validate({"release_tag": "v0.7.0-qwen38-4090-beta.1"})
        self.assertTrue(any("protocol.protocol: canonical product protocol" in error for error in errors),
                        errors)


class NativeRollbackContractTest(unittest.TestCase):
    def test_native_binding_and_verifier_keep_the_first_lineage_exception_honest(self) -> None:
        rollback = {"status": "not_applicable", "directions": 0, "reason": "first release of the lineage"}
        receipt = {"rollback": rollback, "deterministic_gates": {"rollback": "not_applicable"}}
        errors = []
        VERIFY_RELEASE.validate_native_rollback(receipt, "native", errors)
        self.assertEqual(errors, [])
        for fields, gate in (({"directions": 2}, "not_applicable"), ({"directions": False}, "not_applicable"),
                             ({"reason": "phase skipped"}, "not_applicable"),
                             ({"intermediate_release": "old"}, "not_applicable"), ({}, "passed"),
                             ({"status": "passed"}, "not_applicable")):
            with self.subTest(fields=fields, gate=gate):
                errors = []
                VERIFY_RELEASE.validate_native_rollback({"rollback": {**rollback, **fields},
                    "deterministic_gates": {"rollback": gate}}, "native", errors)
                self.assertEqual(len(errors), 1)

    def test_passed_rollback_requires_both_directions_through_a_named_predecessor(self) -> None:
        # The shipped composer-form upgrade rollback, and the orchestrator's passed form of it.
        shipped = json.loads((ROOT / "releases/v0.13.0/qualification/rtx3090.json").read_text(
            encoding="utf-8"))["rollback"]
        orchestrated = {"status": "passed", "directions": 2,
                        "intermediate_release": shipped["intermediate_release"],
                        "active_release": shipped["active_release_after"], "stops": shipped["stops"]}
        for rollback in (shipped, orchestrated):
            errors = []
            VERIFY_RELEASE.validate_native_rollback(
                {"rollback": rollback, "deterministic_gates": {"rollback": "passed"}}, "native", errors)
            self.assertEqual(errors, [])
        candidate = shipped["active_release_after"]
        for fields, gate in (
            ({"directions": None}, "passed"), ({"directions": 1}, "passed"),
            ({"directions": True}, "passed"), ({"intermediate_release": None}, "passed"),
            ({"intermediate_release": ""}, "passed"), ({"intermediate_release": candidate}, "passed"),
            ({"status": None}, "passed"), ({}, None),
        ):
            with self.subTest(fields=fields, gate=gate):
                rollback = {key: value for key, value in {**shipped, **fields}.items()
                            if value is not None}
                errors = []
                VERIFY_RELEASE.validate_native_rollback(
                    {"rollback": rollback, "deterministic_gates": {"rollback": gate} if gate else {}},
                    "native", errors)
                self.assertEqual(len(errors), 1, errors)


class ShippedNativeReceiptBindingTest(unittest.TestCase):
    """Mutations of a shipped v0.14.0 orchestrator receipt, rehashed into its manifest row."""

    RELEASE = "v0.14.0"

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        release = ROOT / "releases" / self.RELEASE
        shutil.copytree(release / "qualification",
                        self.root / "releases" / self.RELEASE / "qualification")
        self.manifest = json.loads((release / "manifest.json").read_text(encoding="utf-8"))
        self.authority = json.loads((release / "compatibility.json").read_text(encoding="utf-8"))
        self.variant = self.manifest["components"]["ninfer_variants"][-1]
        self.prefix = f"components.ninfer_variants.{self.variant['id']}"
        self.receipt_path = self.root / self.variant["qualification"]["summary"]
        self.original = self.receipt_path.read_bytes()

    def validate(self, mutate=None) -> list[str]:
        receipt = json.loads(self.original)
        if mutate is not None:
            mutate(receipt)
        self.receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        self.variant["qualification"]["sha256"] = VERIFY_RELEASE.sha256_file(self.receipt_path)
        errors: list[str] = []
        VERIFY_RELEASE.validate_ninfer_variants(
            self.root, self.RELEASE, self.manifest["components"]["ninfer_variants"], self.authority,
            VERIFY_RELEASE.effective_native_model(self.manifest)["artifact_sha256"], errors)
        return errors

    def test_receipt_package_and_model_identities_must_match_the_variant(self) -> None:
        self.assertEqual(self.validate(), [])
        other = "0" * 64
        for label, mutate, expected in (
            ("dependency inventory", lambda receipt: receipt["package"].update(
                dependency_sbom_sha256=other), "dependency_sbom_sha256 must match"),
            ("no dependency inventory", lambda receipt: receipt["package"].pop(
                "dependency_sbom_sha256"), "dependency_sbom_sha256 must match"),
            ("package filename", lambda receipt: receipt["package"].update(
                filename=receipt["package"]["filename"].replace("beta.3", "beta.2")),
             "package name must match"),
            ("package bytes", lambda receipt: receipt["package"].update(
                bytes=receipt["package"]["bytes"] + 1), "package size must match"),
            ("model", lambda receipt: receipt["identity"].update(model_artifact_sha256=other),
             "model must match the variant"),
            ("outer checksum set", lambda receipt: receipt["package"].update(
                outer_checksums_sha256=other), "outer_checksums_sha256 must match"),
            ("no outer checksum set", lambda receipt: receipt["package"].pop(
                "outer_checksums_sha256"), "outer_checksums_sha256 must match"),
        ):
            with self.subTest(label=label):
                self.assertEqual(self.validate(mutate), [f"{self.prefix} qualification {expected}"])

    def test_every_deterministic_gate_and_its_evidence_section_must_pass(self) -> None:
        for label, mutate in (
            ("failed security gate", lambda receipt: receipt["deterministic_gates"].update(
                state_security="failed")),
            ("skipped benchmark gate", lambda receipt: receipt["deterministic_gates"].update(
                benchmark_c1="skipped")),
            ("missing long-session gate", lambda receipt: receipt["deterministic_gates"].pop(
                "long_session")),
            ("failed section behind a passed gate", lambda receipt: receipt["persistence"].update(
                status="failed")),
            ("missing golden-equivalent section", lambda receipt: receipt.pop("golden_equivalent")),
        ):
            with self.subTest(label=label):
                errors = self.validate(mutate)
                self.assertEqual(len(errors), 1, errors)
                self.assertTrue(errors[0].startswith(f"{self.prefix}: deterministic gate"), errors)

    def test_component_tag_must_name_the_package_version_and_beta(self) -> None:
        shipped = self.variant["release_tag"]
        for tag in ("v0.7.0-qwen38-4090-beta.2", "v0.6.11-qwen38-4090-beta.3"):
            with self.subTest(tag=tag):
                variant = deepcopy(self.variant)
                for field, value in variant.items():
                    if field.endswith("_url"):
                        variant[field] = value.replace(f"/{shipped}/", f"/{tag}/")
                variant["release_tag"] = tag
                errors: list[str] = []
                VERIFY_RELEASE.validate_ninfer_variants(
                    self.root, self.RELEASE, [variant], {"runtime_variants": [variant]},
                    variant["model_artifact_sha256"], errors)
                self.assertEqual(errors, [
                    f"{self.prefix}.release_tag must name the package version and beta ({shipped})"])


class NativeQualityContractTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.release = "v0.15.0"
        self.directory = self.root / "releases" / self.release / "qualification"
        self.directory.mkdir(parents=True)
        self.variant = {
            "id": "rtx3090-windows-native", "release_tag": "v0.8.0-qwen38-3090-beta.1",
            "package_sha256": "b" * 64, "server_binary_sha256": "d" * 64,
            "configuration_sha256": "f" * 64, "model_artifact_sha256": "1" * 64,
            "maximum_context_tokens": 131072, "qualification": {},
            "runtime_shape": {"max_concurrency": 1, "speculative_backend": "dflash2",
                "draft_tokens": {"min": 7, "max": 7}, "proposal": "artifact-default", "fit": {
                    "device_state_slots": 0, "admission_headroom_mib": 768,
                    "draft_mlp_device_format": "Q4_G64_FP16", "token_embedding_residency": "host-mapped"}},
        }
        self.predecessor = deepcopy(self.variant)
        self.predecessor.update(release_tag="v0.7.0-qwen38-3090-beta.3",
                                package_sha256="a" * 64, server_binary_sha256="c" * 64,
                                configuration_sha256="e" * 64)
        self.predecessor["runtime_shape"]["speculative_backend"] = "mtp"
        self.predecessor["runtime_shape"]["fit"].update(
            device_state_slots=2, draft_mlp_device_format="artifact", token_embedding_residency="device")
        self.save_predecessor()
        from test_native_screen_arm import screen_run_identity
        self.screen = {
            "artifact_type": "omp-ninfer.quality-screen-verdict", "schema_version": 1,
            "verdict": "pass", "validity": {"valid": True},
            "runs": {role: screen_run_identity(role)
                     for role in ("production", "candidate", "production_determinism", "candidate_determinism")},
            "raw_prompts_outputs_or_secrets_included": False,
        }

    def save_predecessor(self):
        path = self.root / "releases/v0.14.0/manifest.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({"components": {"ninfer_variants": [self.predecessor]}}))

    def evidence(self, field, value):
        path = self.directory / f"{field}.json"
        path.write_text(json.dumps(value))
        self.variant["qualification"][field] = {
            "path": path.relative_to(self.root).as_posix(), "sha256": VERIFY_RELEASE.sha256_file(path)}
        return path

    def validate(self):
        errors = []
        VERIFY_RELEASE.validate_native_quality(self.root, self.release, self.variant, errors)
        return errors

    def fit(self):
        return {"artifact_type": "omp-ninfer.native-fit", "schema_version": 1, "status": "passed",
                "identity": {key: self.variant[key] for key in ("package_sha256", *VERIFY_RELEASE.NATIVE_IDENTITY_FIELDS)},
                "runtime_shape": self.variant["runtime_shape"], "maximum_context_tokens": 131072,
                "measured_admission_headroom_mib": 768,
                "effective_weights": {"converted_device_bytes": 1024, "host_mapped_bytes": 1024},
                "raw_prompts_outputs_or_secrets_included": False}

    def test_dflash_requires_bound_screen_and_fit_even_for_a_draft(self):
        self.assertTrue(any("quality_screen" in error for error in self.validate()))
        self.evidence("quality_screen", self.screen)
        self.assertTrue(any("qualification.fit" in error for error in self.validate()))
        self.evidence("fit", self.fit())
        self.assertEqual(self.validate(), [])
        for key, value in (("converted_device_bytes", 0), ("host_mapped_bytes", 0)):
            fit = self.fit()
            fit["effective_weights"][key] = value
            self.evidence("fit", fit)
            self.assertTrue(any(key in error for error in self.validate()))

    def test_screen_rejects_wrong_bytes_invalid_verdict_and_disclosed_content(self):
        for mutate in (
            lambda value: value.update(verdict="fail"),
            lambda value: value["validity"].update(valid=False),
            lambda value: value.update(raw_prompts_outputs_or_secrets_included=True),
            lambda value: value["runs"]["candidate"]["arm"].update(server_binary_sha256="0" * 64),
            lambda value: value["runs"]["production"]["arm"].update(lane="rtx4090"),
        ):
            screen = deepcopy(self.screen)
            mutate(screen)
            self.evidence("quality_screen", screen)
            errors = []
            VERIFY_RELEASE.validate_quality_screen(self.root, self.release, self.variant, errors)
            self.assertTrue(errors)
        path = self.evidence("quality_screen", self.screen)
        path.write_text(json.dumps({**self.screen, "extra": "changed"}))
        errors = []
        VERIFY_RELEASE.validate_quality_screen(self.root, self.release, self.variant, errors)
        self.assertTrue(any("SHA-256" in error for error in errors))

    def test_incoming_screen_is_checked_before_destination_exists(self):
        incoming = self.evidence("quality_screen", self.screen)
        data = incoming.read_bytes()
        incoming.unlink()
        source = self.root / "incoming.json"
        source.write_bytes(data)
        errors = []
        VERIFY_RELEASE.validate_quality_screen(self.root, self.release, self.variant, errors, source)
        self.assertEqual(errors, [])
        self.assertFalse(incoming.exists())
        self.variant["qualification"]["quality_screen"]["path"] = "../outside.json"
        errors = []
        VERIFY_RELEASE.validate_quality_screen(self.root, self.release, self.variant, errors, source)
        self.assertTrue(any("stay inside" in error for error in errors))

    def test_screen_production_must_match_the_published_predecessor(self):
        for key in ("package_sha256", *VERIFY_RELEASE.NATIVE_IDENTITY_FIELDS):
            with self.subTest(key=key):
                screen = deepcopy(self.screen)
                for role in ("production", "production_determinism"):
                    screen["runs"][role]["arm"][key] = "9" * 64
                if key == "model_artifact_sha256":
                    for role in ("candidate", "candidate_determinism"):
                        screen["runs"][role]["arm"][key] = "9" * 64
                self.evidence("quality_screen", screen)
                errors = []
                VERIFY_RELEASE.validate_quality_screen(self.root, self.release, self.variant, errors)
                self.assertTrue(any(f"production {key} must match the predecessor" in error
                                    for error in errors), errors)
        self.evidence("quality_screen", self.screen)
        (self.root / "releases/v0.14.0/manifest.json").unlink()
        errors = []
        VERIFY_RELEASE.validate_quality_screen(self.root, self.release, self.variant, errors)
        self.assertTrue(any("must bind a predecessor variant" in error for error in errors), errors)

    def test_screen_requires_exact_full_corpus_membership_for_all_four_runs(self):
        for role in self.screen["runs"]:
            for field, value in (("prompt_count", 80 if "determinism" not in role else 79),
                                 ("prompt_ids_sha256", "0" * 64),
                                 ("prompt_ids_sha256", None)):
                with self.subTest(role=role, field=field, value=value):
                    screen = deepcopy(self.screen)
                    if value is None:
                        screen["runs"][role].pop(field)
                    else:
                        screen["runs"][role][field] = value
                    self.evidence("quality_screen", screen)
                    errors = []
                    VERIFY_RELEASE.validate_quality_screen(self.root, self.release, self.variant, errors)
                    self.assertTrue(any("frozen corpus membership" in error for error in errors), errors)

    def test_mtp_rebuild_exemption_requires_frozen_corpus_direct_bytes_and_same_fit(self):
        self.variant["runtime_shape"] = deepcopy(self.predecessor["runtime_shape"])
        identity = lambda row: {key: row[key] for key in VERIFY_RELEASE.NATIVE_IDENTITY_FIELDS}
        parity = {"artifact_type": "omp-ninfer.native-t1-parity", "schema_version": 1, "status": "passed",
                  "lane": "rtx3090", "predecessor": identity(self.predecessor), "candidate": identity(self.variant),
                  "case_ids_sha256": VERIFY_RELEASE.T1_CASE_IDS_SHA256, "compared": 84, "identical": 84,
                  "comparison_method": VERIFY_RELEASE.T1_COMPARISON_METHOD,
                  "raw_prompts_outputs_or_secrets_included": False}
        self.evidence("t1_parity", parity)
        self.assertEqual(self.validate(), [])
        for field, value in (("compared", 83), ("identical", 83), ("case_ids_sha256", "0" * 64),
                             ("comparison_method", "digest-equality"), ("raw_prompts_outputs_or_secrets_included", True),
                             ("predecessor", identity(self.variant))):
            self.evidence("t1_parity", {**parity, field: value})
            self.assertTrue(self.validate(), field)
        self.evidence("t1_parity", parity)
        self.variant["runtime_shape"]["fit"]["device_state_slots"] = 0
        self.assertTrue(any("unchanged predecessor" in error for error in self.validate()))
        self.variant["runtime_shape"] = deepcopy(self.predecessor["runtime_shape"])
        (self.root / "releases/v0.14.0/manifest.json").unlink()
        self.assertTrue(self.validate())

    def test_carried_rows_and_historical_releases_are_exempt_but_changed_shape_is_not(self):
        self.variant = deepcopy(self.predecessor)
        self.assertEqual(self.validate(), [])
        self.variant["runtime_shape"]["fit"]["device_state_slots"] = 0
        self.assertTrue(any("quality_screen" in error for error in self.validate()))
        self.release = "v0.14.0"
        self.assertEqual(self.validate(), [])

    def test_legacy_predecessor_shape_uses_only_hash_bound_mtp_configuration(self):
        path = self.root / "releases/v0.14.0/qualification/rtx3090.json"
        path.parent.mkdir()
        path.write_text(json.dumps({"configuration": {"speculative_backend": "mtp",
                                                   "device_state_slots": 2, "admission_headroom_mib": 768}}))
        predecessor = deepcopy(self.predecessor)
        del predecessor["runtime_shape"]
        predecessor["qualification"] = {"summary": path.relative_to(self.root).as_posix(),
                                        "sha256": VERIFY_RELEASE.sha256_file(path)}
        self.assertEqual(VERIFY_RELEASE.native_shape(self.root, predecessor),
                         VERIFY_RELEASE.native_shape(self.root, self.predecessor))
        path.write_text("{}")
        self.assertIsNone(VERIFY_RELEASE.native_shape(self.root, predecessor))


class ReleaseContractTest(unittest.TestCase):
    def test_receipt_command_text_is_not_a_json_evidence_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            child = root / "child.json"
            child.write_text('{"receipt_class":"rehearsal"}', encoding="utf-8")
            errors: list[str] = []
            VERIFY_RELEASE.validate_receipt_classes(root, root, [{
                "command": "python3 tool.py \\\n  --argument " + "x" * 512 + ".json",
                "repository_path": "child.json",
            }], errors)
            self.assertEqual(len(errors), 1)
            self.assertIn("rehearsal receipt is not qualification evidence", errors[0])

    def test_rehearsal_cannot_be_bound_as_release_qualification(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        path = root / "releases" / PUBLIC_RELEASE / "qualification.json"
        qualification = self.load(path)
        qualification["receipt_class"] = "rehearsal"
        self.save(path, qualification)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertTrue(any("rehearsal receipt is not qualification evidence" in error
                            for error in errors), errors)

    def test_runtime_tag_allowlist_accepts_only_the_new_component_version(self) -> None:
        self.assertIsNotNone(VERIFY_RELEASE.NINFER_RELEASE_TAG_RE.fullmatch(
            "v0.6.16-qwen38-5090-beta.1"))
        self.assertIsNotNone(VERIFY_RELEASE.NINFER_RELEASE_TAG_RE.fullmatch(
            "v0.6.15-qwen38-5090-beta.1"))
        self.assertIsNotNone(VERIFY_RELEASE.NINFER_RELEASE_TAG_RE.fullmatch(
            "v0.7.0-qwen38-5090-beta.1"))
        self.assertIsNotNone(VERIFY_RELEASE.NINFER_RELEASE_TAG_RE.fullmatch(
            "v0.7.0-qwen38-5090-beta.2"))
        for tag in ("v0.6.17-qwen38-5090-beta.1", "v0.7.1-qwen38-5090-beta.1",
                    "v0.6.16-qwen38-5090-beta.0", "v0.6.16-qwen38-5090-beta.01",
                    "v0.6.16-qwen38-4090-beta.1", "v0.6.16-qwen38-5090-beta.1-extra"):
            with self.subTest(tag=tag):
                self.assertIsNone(VERIFY_RELEASE.NINFER_RELEASE_TAG_RE.fullmatch(tag))

    def test_historical_manifests_keep_their_native_model_contract(self) -> None:
        for path in sorted((ROOT / "releases").glob("*/manifest.json")):
            with self.subTest(release=path.parent.name):
                manifest = self.load(path)
                if "native_model" in manifest["components"]:
                    continue  # Only manifests using the historical implicit binding.
                model = VERIFY_RELEASE.effective_native_model(manifest)
                errors = []
                VERIFY_RELEASE.validate_model_component(model, "components.model", errors)
                authority_path = path.parent / "compatibility.json"
                authority = self.load(authority_path) if authority_path.exists() else {}
                VERIFY_RELEASE.validate_ninfer_variants(
                    ROOT, manifest["release"], manifest["components"].get("ninfer_variants", []),
                    authority, model["artifact_sha256"], errors,
                    allow_pending=manifest["status"] == "draft")
                self.assertEqual(errors, [])

    def split_model_copy(self) -> tuple[Path, dict]:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        release = root / "releases" / PUBLIC_RELEASE
        manifest = self.load(release / "manifest.json")
        manifest["status"] = "candidate"
        manifest["qualification"]["external_installation_passed"] = False
        manifest["publication"]["blockers"] = ["external-install acceptance pending"]
        components = manifest["components"]
        components.setdefault("native_model", components["model"])
        previous = components["model"]
        revision = hashlib.sha256((previous["revision"] + "synthetic").encode()).hexdigest()[:40]
        components["model"] = dict(
            previous, revision=revision,
            artifact_url=previous["artifact_url"].replace(previous["revision"], revision),
            artifact_sha256=hashlib.sha256((previous["artifact_sha256"] + "synthetic").encode()).hexdigest(),
            artifact_bytes=previous["artifact_bytes"] + 1)
        model = components["model"]
        lane_path = release / "qualification/rtx5090.json"
        lane = self.load(lane_path)
        lane["identity"]["model_artifact_sha256"] = model["artifact_sha256"]
        self.save(lane_path, lane)
        for path in (root / "profiles").glob("*.json"):
            profile = self.load(path)
            profile["model"].update(artifact_sha256=model["artifact_sha256"],
                                    artifact_bytes=model["artifact_bytes"])
            arguments = profile["server"]["arguments"]
            arguments[arguments.index("--artifact-sha256") + 1] = model["artifact_sha256"]
            self.save(path, profile)
        authority = self.load(release / "compatibility.json")
        for profile in authority["profiles"]:
            profile["gpu_qualification"]["receipt"]["sha256"] = VERIFY_RELEASE.sha256_file(lane_path)
            profile["runtime"].update(model_url=model["artifact_url"],
                                      model_bytes=model["artifact_bytes"],
                                      model_sha256=model["artifact_sha256"])
        native = components["native_model"]
        for variant in authority["runtime_variants"]:
            variant.update(model_url=native["artifact_url"], model_bytes=native["artifact_bytes"],
                           model_sha256=native["artifact_sha256"])
        for path in (root / "compatibility.json", release / "compatibility.json"):
            self.save(path, authority)
        for path in (root / "docs/COMPATIBILITY.md", release / "COMPATIBILITY.md"):
            path.write_text(VERIFY_RELEASE.render_compatibility_matrix(authority), encoding="utf-8")
        qualification_path = release / "qualification.json"
        qualification = self.load(qualification_path)
        qualification["runtime_identity"]["model_artifact_sha256"] = model["artifact_sha256"]
        qualification["external_installation_qualified"] = False
        qualification["composition"]["external_installation_acceptance"] = {"status": "pending"}
        qualification["composition"]["behavioral_qualification"]["sha256"] = VERIFY_RELEASE.sha256_file(lane_path)
        self.save(qualification_path, qualification)
        manifest["qualification"]["summary_sha256"] = VERIFY_RELEASE.sha256_file(qualification_path)
        components["omp"]["compatibility_sha256"] = VERIFY_RELEASE.sha256_file(release / "compatibility.json")
        self.save(release / "manifest.json", manifest)
        return root, manifest

    def test_split_model_manifest_verifies_without_rebinding_native_packages(self) -> None:
        root, manifest = self.split_model_copy()
        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertEqual(errors, [])
        original = self.load(ROOT / "releases" / PUBLIC_RELEASE / "manifest.json")
        self.assertEqual(manifest["components"]["ninfer_variants"],
                         original["components"]["ninfer_variants"])

    def test_native_variant_cannot_bind_the_primary_model_in_a_split_release(self) -> None:
        root, manifest = self.split_model_copy()
        for variant in manifest["components"]["ninfer_variants"]:
            variant["model_artifact_sha256"] = manifest["components"]["model"]["artifact_sha256"]
        self.save(root / "releases" / PUBLIC_RELEASE / "manifest.json", manifest)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        for variant in manifest["components"]["ninfer_variants"]:
            self.assertTrue(any(variant["id"] in error and "effective native model" in error
                                for error in errors), errors)

    def test_redundant_native_model_is_rejected(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        path = root / "releases" / PUBLIC_RELEASE / "manifest.json"
        manifest = self.load(path)
        manifest["components"]["native_model"] = manifest["components"]["model"]
        self.save(path, manifest)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertTrue(any("native_model" in error and "omitted" in error for error in errors), errors)

    def test_native_model_identity_is_validated_like_the_primary(self) -> None:
        cases = {"repository": "http://example.invalid/model", "revision": "a" * 39,
                 "artifact_url": "https://example.invalid/wrong.ninfer",
                 "artifact_bytes": 0, "artifact_sha256": "a" * 63,
                 "artifact_name": "wrong.ninfer"}
        for field, value in cases.items():
            with self.subTest(field=field):
                root, manifest = self.split_model_copy()
                manifest["components"]["native_model"][field] = value
                self.save(root / "releases" / PUBLIC_RELEASE / "manifest.json", manifest)
                _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
                self.assertTrue(any("native_model" in error and field in error
                                    for error in errors), errors)

    def test_malformed_native_override_never_falls_back_to_primary(self) -> None:
        for override in (None, [], {}, {"artifact_bytes": True}):
            with self.subTest(override=override):
                root, manifest = self.split_model_copy()
                manifest["components"]["native_model"] = override
                self.save(root / "releases" / PUBLIC_RELEASE / "manifest.json", manifest)
                _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
                self.assertTrue(any("components.native_model" in error for error in errors), errors)

    def test_split_model_requires_explicit_native_authority_binding(self) -> None:
        root, _ = self.split_model_copy()
        path = root / "releases" / PUBLIC_RELEASE / "compatibility.json"
        authority = self.load(path)
        for variant in authority["runtime_variants"]:
            for field in ("model_url", "model_bytes", "model_sha256"):
                del variant[field]
        self.save(path, authority)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertTrue(any("effective native model" in error for error in errors), errors)

    def test_native_authority_cannot_render_a_primary_model_binding(self) -> None:
        root, manifest = self.split_model_copy()
        path = root / "releases" / PUBLIC_RELEASE / "compatibility.json"
        authority = self.load(path)
        model = manifest["components"]["model"]
        for variant in authority["runtime_variants"]:
            variant.update(model_url=model["artifact_url"], model_bytes=model["artifact_bytes"],
                           model_sha256=model["artifact_sha256"])
        self.save(path, authority)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        for variant in authority["runtime_variants"]:
            self.assertTrue(any(variant["id"] in error and "effective native model" in error
                                for error in errors), errors)

    def upstream_candidate_copy(self, descriptor: dict | None = None) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary, root = self.public_draft_copy()
        release_root = root / "releases" / PUBLIC_RELEASE
        if descriptor is None:
            descriptor = self.load(ROOT / "tests" / "fixtures" / "upstream-omp-component.json")
        manifest = self.load(release_root / "manifest.json")
        previous = manifest["components"]["omp"]
        manifest["components"]["omp"] = {
            **descriptor["omp"],
            **{key: previous[key] for key in (
                "compatibility_authority", "compatibility_url", "compatibility_sha256"
            )},
        }
        manifest["status"] = "candidate"
        manifest["publication"]["blockers"] = ["Upstream client external-install acceptance pending."]
        manifest["qualification"]["external_installation_passed"] = False
        authority = self.load(root / "compatibility.json")
        composition = authority["composition"]
        composition["lifecycle_repository"] = descriptor["omp"]["upstream_repository"]
        composition["lifecycle_source_release"] = (
            f"{descriptor['omp']['upstream_repository']}/releases/tag/{descriptor['omp']['upstream_tag']}"
        )
        for key in ("lifecycle_source_commit", "request_compatibility_source_commit"):
            composition[key] = descriptor["omp"]["upstream_commit"]
        for key in ("qualification_source_commit", "lifecycle_main_commit", "lifecycle_main_tree",
                    "lifecycle_generated_lock_tree"):
            composition.pop(key, None)
        for item in authority["profiles"]:
            platform = VERIFY_RELEASE.OMP_PROFILE_PLATFORMS[item["id"]]
            item["client_distribution"] = descriptor["platforms"][platform]
            item["acceptance_receipt"] = None
            item["status"] = "preview"
            item["installable"] = False
        for path in (root / "compatibility.json", release_root / "compatibility.json"):
            self.save(path, authority)
        rendered = VERIFY_RELEASE.render_compatibility_matrix(authority)
        for path in (root / "docs" / "COMPATIBILITY.md", release_root / "COMPATIBILITY.md"):
            path.write_text(rendered, encoding="utf-8")
        for path in (root / "profiles").glob("*.json"):
            profile = self.load(path)
            platform = {"manual-ssh-tunnel": "darwin-arm64",
                        "native-windows-docker-local": "windows-x64"}[
                            profile["installation_mode"]]
            profile["client"] = descriptor["platforms"][platform]
            self.save(path, profile)
        qualification_path = release_root / "qualification.json"
        qualification = self.load(qualification_path)
        qualification["external_installation_qualified"] = False
        qualification["composition"]["external_installation_acceptance"] = {"status": "pending"}
        self.save(qualification_path, qualification)
        manifest["qualification"]["summary_sha256"] = VERIFY_RELEASE.sha256_file(qualification_path)
        manifest["components"]["omp"]["compatibility_sha256"] = (
            VERIFY_RELEASE.sha256_file(root / "compatibility.json")
        )
        self.save(release_root / "manifest.json", manifest)
        return temporary, root

    def test_upstream_release_manifest_and_profiles_are_installable(self) -> None:
        temporary, root = self.upstream_candidate_copy()
        self.addCleanup(temporary.cleanup)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=False, require_installable=True)
        self.assertEqual(errors, [])

    def test_upstream_root_profile_rejects_primary_asset_for_another_platform(self) -> None:
        temporary, root = self.upstream_candidate_copy()
        self.addCleanup(temporary.cleanup)
        descriptor = self.load(ROOT / "tests" / "fixtures" / "upstream-omp-component.json")
        path = root / "profiles" / "qwen38-rtx5090-manual-tunnel.json"
        profile = self.load(path)
        profile["client"] = descriptor["platforms"]["windows-x64"]
        self.save(path, profile)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=False, require_installable=True)
        self.assertTrue(any("client archive must match darwin-arm64 compatibility distribution"
                            in error for error in errors), errors)

    def test_upstream_component_rejects_invalid_artifact_identity(self) -> None:
        descriptor = self.load(ROOT / "tests" / "fixtures" / "upstream-omp-component.json")
        cases = (
            ("upstream_repository", "https://github.com/alphastorm/oh-my-pi",
             "upstream_repository must be https://github.com/can1357/oh-my-pi"),
            ("source_commit", "a" * 40,
             "source_commit is a fork-only field forbidden for upstream-release"),
            ("binary_sha256", "a" * 64,
             "binary_sha256 must equal artifact_sha256 for an upstream raw binary"),
            ("artifact_url", "https://github.com/can1357/oh-my-pi/releases/download/v18.2.3/omp-windows-x64.exe",
             "artifact_url must bind the upstream tag and artifact name"),
            ("artifact_asset_id", None, "artifact_asset_id must be a positive integer"),
            ("release_id", True, "release_id must be a positive integer"),
            ("artifact_bytes", 0, "artifact_bytes must be a positive integer"),
            ("artifact_published", False, "artifact_published must be true"),
            ("upstream_tag", descriptor["omp"]["distribution_version"],
             "upstream_tag must be a v-prefixed semantic version"),
            ("upstream_tree", "a" * 39, "upstream_tree must be a lower-case 40-character Git commit"),
            ("artifact_sha256", "A" * 64, "artifact_sha256 must be a lower-case SHA-256"),
        )
        for key, value, error in cases:
            with self.subTest(field=key):
                temporary, root = self.upstream_candidate_copy()
                self.addCleanup(temporary.cleanup)
                path = root / "releases" / PUBLIC_RELEASE / "manifest.json"
                manifest = self.load(path)
                if value is None:
                    manifest["components"]["omp"].pop(key)
                else:
                    manifest["components"]["omp"][key] = value
                self.save(path, manifest)
                _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
                self.assertIn(f"components.omp.{error}", errors)

    def test_upstream_component_must_match_every_profile_tag_and_primary_asset(self) -> None:
        for field, value in (("upstream_tag", "v18.3.1"), ("asset_sha256", "a" * 64)):
            with self.subTest(field=field):
                temporary, root = self.upstream_candidate_copy()
                self.addCleanup(temporary.cleanup)
                path = root / "releases" / PUBLIC_RELEASE / "compatibility.json"
                authority = self.load(path)
                profile = next(item for item in authority["profiles"]
                               if item["id"] == "windows-docker-local")
                client = profile["client_distribution"]
                previous_tag = client["upstream_tag"]
                client[field] = value
                if field == "upstream_tag":
                    client["asset_url"] = client["asset_url"].replace(previous_tag, value)
                    component_field = "upstream_tag"
                else:
                    client["binary_sha256"] = value
                    component_field = "artifact_sha256"
                self.save(path, authority)
                _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
                self.assertIn(f"compatibility windows-docker-local client_distribution.{field} "
                              f"must match components.omp.{component_field}", errors)

    def test_upstream_predecessor_pins_warn_in_drafts_and_block_readiness(self) -> None:
        for mode in ("draft", "require-ready", "ready-status"):
            with self.subTest(mode=mode):
                temporary, root = self.upstream_candidate_copy()
                self.addCleanup(temporary.cleanup)
                release_root = root / "releases" / PUBLIC_RELEASE
                historical = self.load(ROOT / "releases" / "v0.7.4" / "manifest.json")["components"]["omp"]
                pins = [historical["component_release_tag"], historical["source_commit"],
                        historical["artifact_url"]]
                (release_root / "predecessor.txt").write_text(
                    "\n".join([*pins, "A separately qualified, deferred lane retains OMP 18.0.9."]),
                    encoding="utf-8",
                )
                manifest_path = release_root / "manifest.json"
                manifest = self.load(manifest_path)
                manifest["status"] = "ready" if mode == "ready-status" else "draft"
                self.save(manifest_path, manifest)
                warnings: list[str] = []
                _, errors = VERIFY_RELEASE.validate(root, require_ready=mode == "require-ready",
                                                     warnings=warnings)
                if mode == "draft":
                    self.assertEqual(errors, [])
                for line, pin in enumerate(pins, 1):
                    expected = (f"releases/{PUBLIC_RELEASE}/predecessor.txt:{line}: "
                                f"retains predecessor OMP identity {pin!r}")
                    self.assertIn(expected, warnings if mode == "draft" else errors)
                self.assertFalse(any(f"releases/{PUBLIC_RELEASE}/predecessor.txt:4:" in diagnostic
                                     for diagnostic in [*warnings, *errors]))

    def test_fork_component_rejects_explicit_distribution_kind(self) -> None:
        for kind in (None, "alphastorm-fork-component", "unsupported"):
            with self.subTest(kind=kind):
                temporary, root = self.candidate_copy()
                self.addCleanup(temporary.cleanup)
                path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
                manifest = self.load(path)
                manifest["components"]["omp"]["distribution_kind"] = kind
                self.save(path, manifest)
                _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
                self.assertIn("components.omp.distribution_kind must be absent for a fork component", errors)

    def test_omp_component_identity_accepts_preview_and_beta_only(self) -> None:
        self.assertIsNotNone(
            VERIFY_RELEASE.OMP_RELEASE_ID_RE.fullmatch(
                "18.0.9-cross-platform-beta-1"
            )
        )
        self.assertIsNotNone(
            VERIFY_RELEASE.OMP_RELEASE_ID_RE.fullmatch(
                "18.0.9-cross-platform-preview-5"
            )
        )
        self.assertIsNone(
            VERIFY_RELEASE.OMP_RELEASE_ID_RE.fullmatch("18.0.9-cross-platform-stable-1")
        )

    def test_ga_release_predicate_exempts_prerelease_contracts(self) -> None:
        self.assertFalse(VERIFY_RELEASE.ga_release("v0.2.0-beta.1"))
        self.assertFalse(VERIFY_RELEASE.ga_release("v0.3.0-rc.1"))
        self.assertTrue(VERIFY_RELEASE.ga_release("v0.7.1"))

    def candidate_copy(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary, root = self.public_draft_copy()
        historical = root / "releases" / "v0.2.0-beta.1"
        shutil.copy2(historical / "compatibility.json", root / "compatibility.json")
        shutil.copy2(historical / "COMPATIBILITY.md", root / "docs" / "COMPATIBILITY.md")
        historical_manifest = self.load(historical / "manifest.json")
        historical_profile = historical_manifest["runtime_identity"]["deployment_profile"]
        historical_omp = historical_manifest["components"]["omp"]
        historical_model = historical_manifest["components"]["model"]
        for profile_path in (root / "profiles").glob("*.json"):
            profile = self.load(profile_path)
            profile["release"] = "v0.2.0-beta.1"
            profile["server"]["deployment_profile"] = historical_profile
            profile["model"].update(artifact_sha256=historical_model["artifact_sha256"],
                                    artifact_bytes=historical_model["artifact_bytes"])
            arguments = profile["server"].get("arguments", [])
            for index, argument in enumerate(arguments[:-1]):
                if argument == "--deployment-profile":
                    arguments[index + 1] = historical_profile
                elif argument == "--artifact-sha256":
                    arguments[index + 1] = historical_model["artifact_sha256"]
            # The historical manifest pins the fork client, so a profile that pins a client binary
            # pins its archive, and the provider carries the fork's stateful compat flag.
            client = profile.get("client")
            if isinstance(client, dict) and "asset_url" in client:
                client.update({
                    "component_release_tag": historical_omp["component_release_tag"],
                    "asset_url": historical_omp["artifact_url"],
                    "asset_sha256": historical_omp["artifact_sha256"],
                    "binary_sha256": historical_omp["binary_sha256"],
                })
            provider = profile.get("omp_provider", {})
            if provider.pop("stateful_responses_environment", None) is not None:
                provider["ninfer_stateful_responses"] = True
            self.save(profile_path, profile)
        return temporary, root

    def public_draft_copy(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        shutil.copytree(ROOT / "releases", root / "releases")
        shutil.copytree(ROOT / "profiles", root / "profiles")
        # PUBLIC_RELEASE's historical tuning cannot inherit a newer root's K5 server shape.
        for profile in ACCEPTED_PROFILES.glob("*.json"):
            shutil.copy2(profile, root / "profiles" / profile.name)
        shutil.copytree(ROOT / "examples" / "manual-tunnel", root / "examples" / "manual-tunnel")
        previous_root = REBIND_RELEASE.ROOT
        try:
            REBIND_RELEASE.ROOT = root
            REBIND_RELEASE.promote_root(PUBLIC_RELEASE, root / "releases" / PUBLIC_RELEASE / "manifest.json")
        finally:
            REBIND_RELEASE.ROOT = previous_root
        # Restore the frozen published provider contract, not the live candidate's.
        omp = self.load(root / "releases" / PUBLIC_RELEASE / "manifest.json")["components"]["omp"]
        for path in (root / "profiles").glob("*.json"):
            profile = self.load(path)
            profile["status"] = "public"
            profile["omp_provider"].pop("compat", None)
            profile["omp_provider"]["stateful_responses_environment"] = {"PI_OPENAI_STATEFUL": "1"}
            client = {key: profile["client"][key] for key in ("os", "architecture")}
            if profile["installation_mode"] == "manual-ssh-tunnel":
                client["asset_name"] = "omp-darwin-arm64"
            else:
                client.update(asset_url=omp["artifact_url"], asset_sha256=omp["artifact_sha256"],
                              binary_sha256=omp["binary_sha256"])
            profile["client"] = client
            self.save(path, profile)
        shutil.copytree(ROOT / "docs" / "measurements", root / "docs" / "measurements")
        shutil.copy2(root / "releases" / PUBLIC_RELEASE / "COMPATIBILITY.md",
                     root / "docs" / "COMPATIBILITY.md")
        # Component-mutation fixtures need valid release-note link targets; the
        # real documentation graph is checked by the normal validation of ROOT.
        for document in ("QUICKSTART.md", "SECURITY.md", "BENCHMARKS.md"):
            (root / "docs" / document).write_text("# Test fixture\n", encoding="utf-8")
        return temporary, root

    def add_unbound_client_candidate(self, root: Path) -> None:
        """Change only client/provider state, preserving the fixture's runtime identity."""
        for path in (root / "profiles").glob("*.json"):
            profile = self.load(path)
            current = self.load(ROOT / "profiles" / path.name)
            profile["status"] = "candidate"
            profile["client"] = current["client"]
            profile["omp_provider"] = current["omp_provider"]
            self.save(path, profile)

    @staticmethod
    def load(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def save(path: Path, value: dict) -> None:
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def make_candidate(self, root: Path, manifest: dict) -> None:
        qualification_path = root / "releases" / "v0.2.0-beta.1" / "qualification.json"
        qualification = self.load(qualification_path)
        qualification["external_installation_qualified"] = False
        self.save(qualification_path, qualification)
        manifest["qualification"]["summary_sha256"] = hashlib.sha256(
            qualification_path.read_bytes()
        ).hexdigest()
        manifest["status"] = "candidate"
        manifest["qualification"]["external_installation_passed"] = False
        manifest["publication"]["blockers"] = ["Run the external-install acceptance path."]

    def test_checked_in_ready_release_is_installable(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertEqual(manifest["status"], "ready")
        self.assertEqual(errors, [])

        _, ready_errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertEqual(ready_errors, [])

        _, installable_errors = VERIFY_RELEASE.validate(
            root,
            require_ready=False,
            require_installable=True,
        )
        self.assertEqual(installable_errors, [])

    def test_ready_rejects_unreleased_quickstart_banner(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        (root / "docs/QUICKSTART.md").write_text(
            f"# Quickstart\n\n> **Ready, UNRELEASED {PUBLIC_RELEASE} product candidate**\n",
            encoding="utf-8",
        )
        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertEqual(errors, [
            f"docs/QUICKSTART.md:3: describes {PUBLIC_RELEASE} as unreleased or pending publication; "
            "use release-neutral wording before publishing",
        ])
        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertEqual(errors, [])

    def test_ready_accepts_release_neutral_quickstart_banner(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        (root / "docs/QUICKSTART.md").write_text(
            f"# Quickstart\n\n> **{PUBLIC_RELEASE}: RTX 5090 · RTX 4090 · RTX 3090**\n",
            encoding="utf-8",
        )
        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertEqual(errors, [])

    def test_ready_rejects_pending_publication_in_user_facing_docs(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        for relative in ("README.md", "docs/QUICKSTART.md", "docs/DECISION_GUIDE.md", "ROADMAP.md"):
            document = root / relative
            for wording in ("unreleased", "PUBLICATION PENDING", "Publication remains", "Ready candidate"):
                with self.subTest(document=relative, wording=wording):
                    document.write_text(f"# Test fixture\n\n{PUBLIC_RELEASE}: {wording}\n", encoding="utf-8")
                    _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
                    self.assertEqual(errors, [
                        f"{relative}:3: describes {PUBLIC_RELEASE} as unreleased or pending publication; "
                        "use release-neutral wording before publishing",
                    ])
            document.write_text("# Test fixture\n", encoding="utf-8")

    def test_ready_rejects_pending_quickstart_banner_without_version(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        (root / "docs/QUICKSTART.md").write_text(
            "# Quickstart\n\n> **Ready candidate · exact GPU lanes**\n", encoding="utf-8",
        )
        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertEqual(errors, [
            f"docs/QUICKSTART.md:3: describes {PUBLIC_RELEASE} as unreleased or pending publication; "
            "use release-neutral wording before publishing",
        ])

    def test_ready_documentation_guard_ignores_other_release_versions(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        (root / "README.md").write_text(
            "# Test fixture\n\nv0.9.1: unreleased\nv0.10.01: publication pending\n"
            "v0.10.0-beta.1: ready candidate\n", encoding="utf-8",
        )
        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertEqual(errors, [])

    def test_ready_rejects_unreleased_example_documentation(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        document = root / "examples/extra/README.md"
        document.parent.mkdir(parents=True)
        document.write_text(f"# Test fixture\n\n{PUBLIC_RELEASE}: unreleased\n", encoding="utf-8")
        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertEqual(errors, [
            f"examples/extra/README.md:3: describes {PUBLIC_RELEASE} as unreleased or pending publication; "
            "use release-neutral wording before publishing",
        ])

    def test_ready_documentation_guard_scans_tracked_markdown_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            document = root / "README.md"
            document.write_text(f"{PUBLIC_RELEASE}: unreleased\n", encoding="utf-8")
            errors: list[str] = []
            VERIFY_RELEASE.validate_release_documentation(root, PUBLIC_RELEASE, errors)
            self.assertEqual(errors, [])
            subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
            VERIFY_RELEASE.validate_release_documentation(root, PUBLIC_RELEASE, errors)
            self.assertEqual(errors, [
                f"README.md:1: describes {PUBLIC_RELEASE} as unreleased or pending publication; "
                "use release-neutral wording before publishing",
            ])

    def test_ready_documentation_guard_excludes_published_release_markdown(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        (root / "releases" / PUBLIC_RELEASE / "NINFER_RELEASE_NOTES.md").write_text(
            f"{PUBLIC_RELEASE}: unreleased\n", encoding="utf-8",
        )
        errors: list[str] = []
        VERIFY_RELEASE.validate_release_documentation(root, PUBLIC_RELEASE, errors)
        self.assertEqual(errors, [])

    def test_ready_rejects_pending_work_anywhere_in_the_versioned_guide(self) -> None:
        """v0.14.0's composed guide before its finalization sweep: the stale sentences wrap and
        never name the version. The engine's pending-request queue and fenced code are not
        release state."""
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        (root / "docs/QUICKSTART.md").write_text(
            f"# Quickstart\n\n> **{PUBLIC_RELEASE}: RTX 5090 · RTX 4090 · RTX 3090**\n\n"
            "- **Native rollback:** Both beta.3 runtime qualifications record no predecessor. Fresh\n"
            "  public-install and restoration acceptance remains\n"
            "  pending. Preserve prior native release roots separately for historical recovery.\n\n"
            "The beta.3 runtime qualification records no predecessor; fresh public-install and\n"
            "product-route acceptance is pending. Keep prior native release roots untouched.\n\n"
            "RTX 5090 admits two requests at once and holds a pending\n"
            "request for up to 180 s; native lanes serve one at a time with a 30 s pending timeout.\n\n"
            "```powershell\n$pending = Get-Job -State Running\n```\n",
            encoding="utf-8",
        )
        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertEqual(errors, [
            "docs/QUICKSTART.md:7: contains stale release-state phrase 'pending' in ready mode",
            "docs/QUICKSTART.md:10: contains stale release-state phrase 'pending' in ready mode",
        ])

    def test_ready_rejects_pending_work_on_lines_naming_the_release(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        (root / "README.md").write_text(
            f"# Test fixture\n\nFresh {PUBLIC_RELEASE} public-route acceptance is pending.\n"
            f"The {PUBLIC_RELEASE} RTX 5090 lane holds a pending\nrequest for up to 180 s.\n"
            "Fresh changed-client acceptance is pending for the next release.\n",
            encoding="utf-8",
        )
        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertEqual(errors, [
            "README.md:3: contains stale release-state phrase 'pending' in ready mode",
        ])

    def test_release_tree_text_rejects_private_markers(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        planted = root / "releases" / PUBLIC_RELEASE / "review" / "planted.json"
        planted.parent.mkdir(parents=True, exist_ok=True)
        planted.write_text('{"path": "/Users/someone/secret"}', encoding="utf-8")
        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertTrue(
            any("private marker" in error and "planted.json" in error for error in errors),
            errors,
        )

    def test_ready_rejects_pending_work_in_any_phrasing(self) -> None:
        """How staged releases state unfinished work; v0.12.0 and v0.11.0 shipped the first two
        ready. The engine's queue terms and a receipt's recorded state are not release work."""
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / PUBLIC_RELEASE / "manifest.json"
        original = self.load(manifest_path)
        path = f"manifest.limitations[{len(original['limitations'])}]"
        for sentence, phrase in (
            ("Fresh product acceptance is pending; predecessor acceptance is not carried forward.",
             "pending"),
            ("Local C qualification is distinct from the still-pending documented-route/composed "
             "acceptance.", "pending"),
            ("The RTX 5090 identities remain pending.", "pending"),
            ("Upstream OMP client external-install acceptance pending", "pending"),
            ("Pending candidate-bound public-install acceptance.", "Pending"),
            ("G4 is explicitly pending in its ledger.", "pending"),
            ("Two active lanes plus two extra device-state slots and 180-second pending timeout.", None),
            ("Both sets bind their build receipts; build hardware-pending capture is not altered.", None),
            ("Keep-warm stops whenever a request is pending.", None),
        ):
            with self.subTest(sentence=sentence):
                manifest = deepcopy(original)
                manifest["limitations"].append(sentence)
                self.save(manifest_path, manifest)
                _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
                self.assertEqual(errors, [] if phrase is None else [
                    f"{path} contains stale release-state phrase {phrase!r} in ready mode"])

    def test_public_release_passes_ready_validation(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertEqual(errors, [])

    def test_client_candidate_matches_the_verified_upstream_descriptor(self) -> None:
        release = self.load(ROOT / "compatibility.json")["product_release"]
        descriptor = STAGE_RELEASE.load_omp_component(
            ROOT / "releases" / release / "qualification/client-components.json")
        for name, platform in (("manual-tunnel", "darwin-arm64"), ("windows-docker-local", "windows-x64")):
            profile = self.load(ROOT / f"profiles/qwen38-rtx5090-{name}.json")
            for key in ("distribution_kind", "upstream_repository", "upstream_tag", "upstream_commit",
                        "published", "release_id", "asset_id", "asset_name", "asset_bytes", "asset_url",
                        "asset_sha256", "binary_sha256"):
                self.assertEqual(profile["client"][key], descriptor["platforms"][platform][key])

    def test_client_candidate_is_valid_but_not_ready_or_installable(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        self.add_unbound_client_candidate(root)
        warnings = []
        manifest, errors = VERIFY_RELEASE.validate(root, require_ready=False, warnings=warnings)
        self.assertEqual(errors, [])
        self.assertEqual(manifest["components"]["omp"]["upstream_tag"], "v18.4.10")
        self.assertEqual(len(warnings), 2)
        self.assertTrue(all("documented-route requalification pending" in item for item in warnings))
        for mode in ("require_ready", "require_installable"):
            with self.subTest(mode=mode):
                _, errors = VERIFY_RELEASE.validate(
                    root, require_ready=mode == "require_ready",
                    require_installable=mode == "require_installable")
                self.assertEqual(len(errors), 2, errors)
                self.assertTrue(all("unqualified client candidate" in item for item in errors))

    def test_client_candidate_requires_per_model_stateful_responses(self) -> None:
        for value in (None, False, "true", 1):
            with self.subTest(value=value):
                profile = self.load(ROOT / "profiles/qwen38-rtx5090-manual-tunnel.json")
                profile["omp_provider"]["compat"]["statefulResponses"] = value
                errors = []
                VERIFY_RELEASE.validate_profile_contract(
                    profile, "candidate", profile["release"], profile["model"],
                    profile["model"]["public_id"], profile["server"]["deployment_profile"],
                    errors, upstream_client=True, per_model_stateful=True)
                self.assertTrue(any("per-model compat.statefulResponses" in item for item in errors))
        for key, value in (("stateful_responses_environment", {"PI_OPENAI_STATEFUL": "1"}),
                           ("ninfer_stateful_responses", True)):
            with self.subTest(obsolete_key=key):
                profile = self.load(ROOT / "profiles/qwen38-rtx5090-manual-tunnel.json")
                profile["omp_provider"][key] = value
                errors = []
                VERIFY_RELEASE.validate_profile_contract(
                    profile, "candidate", profile["release"], profile["model"],
                    profile["model"]["public_id"], profile["server"]["deployment_profile"],
                    errors, upstream_client=True, per_model_stateful=True)
                self.assertTrue(any("per-model compat.statefulResponses" in item for item in errors))

    def test_non_candidate_cannot_select_stateful_contract_from_its_own_tag(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        descriptor = STAGE_RELEASE.load_omp_component(
            ROOT / "docs/measurements/2026-10-10-omp-1887-client-components.json")
        for path in (root / "profiles").glob("*.json"):
            profile = self.load(path)
            profile["client"]["upstream_tag"] = descriptor["omp"]["upstream_tag"]
            profile["omp_provider"].pop("stateful_responses_environment")
            profile["omp_provider"]["compat"] = {"statefulResponses": True}
            self.save(path, profile)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertEqual(sum("OMP provider must name PI_OPENAI_STATEFUL=1" in item for item in errors), 2, errors)

    def test_per_model_client_environment_contract_survives_qualification(self) -> None:
        descriptor = STAGE_RELEASE.load_omp_component(
            ROOT / "docs/measurements/2026-10-10-omp-1887-client-components.json")
        temporary, root = self.upstream_candidate_copy(descriptor)
        self.addCleanup(temporary.cleanup)
        for path in (root / "profiles").glob("*.json"):
            profile = self.load(path)
            profile["client"].pop("upstream_tag", None)
            profile["omp_provider"].pop("stateful_responses_environment")
            profile["omp_provider"]["compat"] = {"statefulResponses": True}
            self.save(path, profile)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertEqual(errors, [])
        for path in (root / "profiles").glob("*.json"):
            profile = self.load(path)
            profile["omp_provider"]["stateful_responses_environment"] = {"PI_OPENAI_STATEFUL": "1"}
            self.save(path, profile)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertEqual(sum("per-model compat.statefulResponses" in item for item in errors), 2, errors)

    def test_client_candidate_checks_exact_upstream_binary_identity(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        self.add_unbound_client_candidate(root)
        path = root / "profiles/qwen38-rtx5090-windows-docker-local.json"
        profile = self.load(path)
        profile["client"]["asset_url"] = profile["client"]["asset_url"].replace(
            profile["client"]["upstream_tag"], "v18.4.10")
        self.save(path, profile)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertTrue(any("asset_url must bind the upstream tag and asset name" in item
                            for item in errors), errors)

    def test_client_candidate_cannot_bypass_qualification_by_relabelling_itself(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        self.add_unbound_client_candidate(root)
        for path in (root / "profiles").glob("*.json"):
            profile = self.load(path)
            profile["status"] = "public"
            self.save(path, profile)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertTrue(any("client archive must match windows-x64 compatibility distribution" in item
                            for item in errors), errors)

    def test_unknown_release_channel_fails_closed(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / PUBLIC_RELEASE / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["channel"] = "general-availability"
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn(
            "manifest channel and audience must form a recognized release posture",
            errors,
        )

    def test_draft_contract_remains_noninstallable(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["status"] = "draft"
        manifest["components"]["omp"]["artifact_published"] = False
        manifest["publication"]["blockers"] = ["Draft release is not installable."]
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertEqual(errors, [])
        _, installable_errors = VERIFY_RELEASE.validate(
            root, require_ready=False, require_installable=True
        )
        self.assertIn("release manifest is not installable", installable_errors)

    def test_draft_still_validates_present_external_identities(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["status"] = "draft"
        manifest["publication"]["blockers"] = ["Draft release is not installable."]
        manifest["components"]["ninfer"]["oci_manifest_digest"] = f"sha256:{'f' * 64}"
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("local packaging and manifest OCI digests must match", errors)

    def test_candidate_accepts_exact_installable_components_before_external_smoke(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        self.make_candidate(root, manifest)
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(
            root,
            require_ready=False,
            require_installable=True,
        )
        self.assertEqual(errors, [])

    def test_ready_contract_accepts_complete_immutable_identities(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertEqual(errors, [])

    def test_external_acceptance_rejects_short_or_stale_platform_hashes(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        release = "v0.2.0-beta.1"
        manifest_path = root / "releases" / release / "manifest.json"
        qualification_path = root / "releases" / release / "qualification.json"
        acceptance_path = root / "releases" / release / "acceptance" / "composed-external-installation.json"
        manifest = self.load(manifest_path)
        qualification = self.load(qualification_path)
        acceptance = self.load(acceptance_path)
        acceptance["platform_receipts"][1]["sha256"] = "a" * 62
        self.save(acceptance_path, acceptance)
        qualification["composition"]["external_installation_acceptance"]["sha256"] = hashlib.sha256(
            acceptance_path.read_bytes()
        ).hexdigest()
        self.save(qualification_path, qualification)
        manifest["qualification"]["summary_sha256"] = hashlib.sha256(
            qualification_path.read_bytes()
        ).hexdigest()
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertIn(
            "external acceptance platform receipt hashes must match compatibility",
            errors,
        )

    def test_composed_acceptance_subject_identity_fields_must_match(self) -> None:
        cases = (
            (
                "release",
                "v9.9.9",
                "external acceptance receipt release must match manifest release",
            ),
            (
                "status",
                "failed",
                "external acceptance receipt status must be passed",
            ),
            (
                "compatibility_authority",
                "stale-authority",
                "external acceptance receipt compatibility_authority must match manifest",
            ),
            (
                "compatibility_sha256",
                "0" * 64,
                "external acceptance receipt compatibility_sha256 must match manifest",
            ),
        )
        for field, stale_value, expected_error in cases:
            with self.subTest(field=field):
                temporary, root = self.public_draft_copy()
                try:
                    release = PUBLIC_RELEASE
                    release_root = root / "releases" / release
                    acceptance_path = (
                        release_root
                        / "acceptance"
                        / "composed-external-installation.json"
                    )
                    qualification_path = release_root / "qualification.json"
                    manifest_path = release_root / "manifest.json"

                    acceptance = self.load(acceptance_path)
                    acceptance[field] = stale_value
                    self.save(acceptance_path, acceptance)

                    qualification = self.load(qualification_path)
                    qualification["composition"][
                        "external_installation_acceptance"
                    ]["sha256"] = hashlib.sha256(
                        acceptance_path.read_bytes()
                    ).hexdigest()
                    self.save(qualification_path, qualification)

                    manifest = self.load(manifest_path)
                    manifest["qualification"]["summary_sha256"] = hashlib.sha256(
                        qualification_path.read_bytes()
                    ).hexdigest()
                    self.save(manifest_path, manifest)

                    _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
                    self.assertIn(expected_error, errors)
                finally:
                    temporary.cleanup()

    def test_ready_contract_rejects_incomplete_publication(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        qualification_path = root / "releases" / "v0.2.0-beta.1" / "qualification.json"
        manifest = self.load(manifest_path)
        qualification = self.load(qualification_path)
        manifest["status"] = "ready"
        manifest["components"]["omp"]["artifact_url"] = None
        manifest["qualification"]["summary_sha256"] = None
        manifest["qualification"]["public_url"] = None
        manifest["qualification"]["external_installation_passed"] = False
        manifest["publication"]["blockers"] = []
        qualification["external_installation_qualified"] = False
        self.save(qualification_path, qualification)
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertIn("installable release requires components.omp.artifact_url", errors)
        self.assertIn("ready release requires qualification.summary_sha256", errors)
        self.assertIn("ready release requires a passing external installation", errors)

    def test_installable_release_authority_must_parse_in_the_pinned_client(self) -> None:
        """One profile the OMP client rejects takes appliance commands away from every platform."""
        cases = (
            ("qualified", {"installable": False},
             "compatibility {id} is qualified without acceptance, a qualified GPU runtime and "
             "installability; the OMP client rejects the authority"),
            ("blocked", {"installable": True},
             "compatibility {id} is blocked but installable; the OMP client rejects the authority"),
        )
        for status, fields, expected in cases:
            with self.subTest(status=status, fields=fields):
                temporary, root = self.public_draft_copy()
                self.addCleanup(temporary.cleanup)
                profile_id = ""
                for authority_path in (
                    root / "compatibility.json",
                    root / "releases" / PUBLIC_RELEASE / "compatibility.json",
                ):
                    authority = self.load(authority_path)
                    profile = next(item for item in authority["profiles"]
                                   if item["status"] == "qualified")
                    profile_id = profile["id"]
                    profile["status"] = status
                    profile.update(fields)
                    self.save(authority_path, authority)
                _, errors = VERIFY_RELEASE.validate(root, require_ready=False, require_installable=True)
                self.assertIn(expected.format(id=profile_id), errors)

    def test_ready_release_requires_the_continuation_capability_it_observed(self) -> None:
        """A receipt that observed a restart continuation pins the capability that provides it."""
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        for authority_path in (
            root / "compatibility.json",
            root / "releases" / PUBLIC_RELEASE / "compatibility.json",
        ):
            authority = self.load(authority_path)
            runtime = authority["profiles"][0]["runtime"]
            runtime["capabilities"] = [
                item
                for item in runtime["capabilities"]
                if item != VERIFY_RELEASE.CONTINUATION_CAPABILITY
            ]
            self.save(authority_path, authority)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertTrue(
            any(
                "restart continuation" in error
                and VERIFY_RELEASE.CONTINUATION_CAPABILITY in error
                for error in errors
            ),
            errors,
        )

    def test_ready_qualification_date_cannot_precede_its_own_evidence(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        release_root = root / "releases" / PUBLIC_RELEASE
        qualification_path = release_root / "qualification.json"
        qualification = self.load(qualification_path)
        qualification["as_of"] = "2026-01-01"
        self.save(qualification_path, qualification)
        manifest_path = release_root / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["qualification"]["summary_sha256"] = hashlib.sha256(
            qualification_path.read_bytes()
        ).hexdigest()
        self.save(manifest_path, manifest)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertTrue(
            any("qualification as_of 2026-01-01 is older than" in error for error in errors),
            errors,
        )

    def test_ready_prose_cannot_name_a_component_tag_this_release_omits(self) -> None:
        """Limitation and publication text is the operator's rollback reference.

        A tag inherited from an earlier release survives every hash check, because prose is not
        a component binding, and sends a reader to a package this release never published.
        """
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / PUBLIC_RELEASE / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["limitations"] = list(manifest["limitations"]) + [
            "Native Windows RTX 4090 support binds only "
            "alphastorm/ninfer@v0.6.1-qwen38-4090-beta.1 and its exact package."
        ]
        self.save(manifest_path, manifest)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertTrue(
            any(
                "names component tag v0.6.1-qwen38-4090-beta.1" in error
                and "does not bind" in error
                for error in errors
            ),
            errors,
        )

    def test_ga_ready_state_sweep_rejects_stale_machine_state(self) -> None:
        cases = (
            (
                "manifest_blockers",
                "manifest.consistency_probe.blockers must be an empty array in ready mode",
            ),
            (
                "compatibility_blockers",
                "compatibility.composition.blockers must be an empty array in ready mode",
            ),
            (
                "qualification_status",
                "qualification.consistency_probe.status must not contain draft or pending in ready mode",
            ),
            (
                "authority_id",
                "compatibility.authority_id must not contain draft or pending in ready mode",
            ),
        )
        for case, expected_error in cases:
            with self.subTest(case=case):
                temporary, root = self.public_draft_copy()
                try:
                    release_root = root / "releases" / PUBLIC_RELEASE
                    manifest_path = release_root / "manifest.json"
                    qualification_path = release_root / "qualification.json"
                    compatibility_path = release_root / "compatibility.json"

                    if case == "manifest_blockers":
                        manifest = self.load(manifest_path)
                        manifest["consistency_probe"] = {
                            "blockers": ["unresolved release gate"]
                        }
                        self.save(manifest_path, manifest)
                    elif case == "qualification_status":
                        qualification = self.load(qualification_path)
                        qualification["consistency_probe"] = {
                            "status": "release pending publication"
                        }
                        self.save(qualification_path, qualification)
                        manifest = self.load(manifest_path)
                        manifest["qualification"]["summary_sha256"] = (
                            hashlib.sha256(qualification_path.read_bytes()).hexdigest()
                        )
                        self.save(manifest_path, manifest)
                    else:
                        compatibility = self.load(compatibility_path)
                        if case == "compatibility_blockers":
                            compatibility["composition"]["blockers"] = [
                                "unresolved composition gate"
                            ]
                        else:
                            compatibility["authority_id"] += "-draft"
                        self.save(compatibility_path, compatibility)
                        self.save(root / "compatibility.json", compatibility)

                    _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
                    self.assertIn(expected_error, errors)
                finally:
                    temporary.cleanup()

    def bind_g4_review(self, root: Path, change_ledger=None, change_gate=None) -> None:
        """Bind v0.14.0's closed council ledger and the G4 summary restating it into the fixture,
        after an optional change to either; the summary pins the ledger bytes it is given."""
        release_root = root / "releases" / PUBLIC_RELEASE
        ledger = self.load(ROOT / "releases/v0.14.0/review/runtime-ledger.json")
        ledger["release"] = PUBLIC_RELEASE
        if change_ledger is not None:
            change_ledger(ledger)
        ledger_path = release_root / "review" / "runtime-ledger.json"
        self.save(ledger_path, ledger)
        gate = self.load(ROOT / "releases/v0.14.0/qualification.json")["observed_gates"]["g4_review"]
        gate.update(repository_path=ledger_path.relative_to(root).as_posix(),
                    sha256=hashlib.sha256(ledger_path.read_bytes()).hexdigest())
        if change_gate is not None:
            change_gate(gate)
        self.rebind_qualification(
            release_root, lambda qualification: qualification["observed_gates"].update(g4_review=gate))

    def test_ready_g4_summary_must_restate_a_closed_approved_ledger(self) -> None:
        ledger = f"releases/{PUBLIC_RELEASE}/review/runtime-ledger.json"
        gate = "qualification.observed_gates.g4_review"
        mismatched = [f"{gate}.ledger_status must equal the review ledger's status",
                      f"{gate}.approval_granted must equal the review ledger's approval_granted"]
        cases = (
            ("closed and approved", None, None, []),
            # v0.14.0's binding as staging wrote it, under the summary finalization writes.
            ("staged binding", lambda record: record.update(
                artifact_type="omp_ninfer_runtime_review_binding", status="pending",
                approval_granted=False), None, [
                f"{ledger} must be this release's review ledger",
                f"{ledger} status 'pending' is not closed",
                f"{ledger} must grant G4 approval", *mismatched]),
            # v0.13.1's ledger between its two councils.
            ("one council closed", lambda record: record.update(
                status="native-closed-product-tooling-pending", approval_granted=False), None, [
                f"{ledger} status 'native-closed-product-tooling-pending' is not closed",
                f"{ledger} must grant G4 approval", *mismatched]),
            ("council left open", lambda record: record["product_tooling"].update(status="pending"),
             None, [f"{ledger} product_tooling.status 'pending' is not closed"]),
            ("other bytes", None, lambda summary: summary.update(sha256="0" * 64),
             [f"{gate}.sha256 must match the review ledger bytes"]),
            ("failed summary", None, lambda summary: summary.update(status="failed"),
             [f"{gate}.status must be passed in ready mode"]),
        )
        for case, change_ledger, change_gate, expected in cases:
            with self.subTest(case=case):
                temporary, root = self.public_draft_copy()
                try:
                    self.bind_g4_review(root, change_ledger, change_gate)
                    _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
                    self.assertEqual(errors, expected)
                finally:
                    temporary.cleanup()

    def test_ready_g4_omission_fails_closed_for_new_releases_only(self) -> None:
        historical = self.load(ROOT / "releases/v0.10.0/qualification.json")
        self.assertNotIn("g4_review", historical["observed_gates"])
        errors = []
        VERIFY_RELEASE.validate_review_ledger(ROOT, "v0.10.0", historical, errors)
        self.assertEqual(errors, [], "published evidence predates the mandatory G4 binding")
        for qualification in ({}, {"observed_gates": {}}, {"observed_gates": {"g4_review": None}}):
            with self.subTest(qualification=qualification):
                errors = []
                VERIFY_RELEASE.validate_review_ledger(ROOT, "v0.15.1", qualification, errors)
                self.assertEqual(errors, [
                    "qualification.observed_gates.g4_review is required in ready mode"])

    def test_bound_routes_must_pass_for_this_release_inside_its_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "releases/v0.15.1/acceptance/documented-routes.json"
            path.parent.mkdir(parents=True)
            for fields, foreign, expected in (
                ({}, False, None),
                ({"release": "v0.15.0"}, False, "receipt release must match"),
                ({"status": "failed"}, False, "receipt status must be passed"),
                ({}, True, "repository_path must stay inside release"),
            ):
                with self.subTest(fields=fields, foreign=foreign):
                    target = path if not foreign else root / "old-routes.json"
                    target.write_text(json.dumps({"release": "v0.15.1", "status": "passed", **fields}))
                    qualification = {"release": "v0.15.1", "composition": {
                        "documented_route_acceptance": {"status": "passed",
                            "repository_path": target.relative_to(root).as_posix(),
                            "sha256": VERIFY_RELEASE.sha256_file(target)}}}
                    errors = []
                    VERIFY_RELEASE.validate_documented_route_acceptance(root, qualification, errors)
                    if expected:
                        self.assertTrue(any(expected in error for error in errors), errors)
                    else:
                        self.assertEqual(errors, [])

    def test_ready_route_acceptance_summary_must_restate_its_bound_evidence(self) -> None:
        """The fixture binds its routes evidence but predates the summary: add v0.14.0's summary,
        restated for that evidence, then drift it the ways a hand edit did."""
        summary_field = "qualification.documented_route_acceptance"
        bound = "qualification.composition.documented_route_acceptance"
        cases = (
            ("restated", lambda root, summary: None, []),
            # v0.14.0 reconciled its routes evidence and rewrote this hash by hand (1a6a224).
            ("hash before the reconcile", lambda root, summary: summary.update(
                evidence_sha256="95a64662e83c8a636e2fe399e8aa6f4169e7dc9147dd61635155b71ab93b5fa1"),
             [f"{summary_field}.evidence_sha256 must be {bound}.sha256"]),
            ("other candidate", lambda root, summary: summary.update(
                candidate_commit="c81a8e7efb37b8d5c36b16a10a18945cb5aa313d"),
             [f"{summary_field}.candidate_commit must be the routes evidence's candidate_commit"]),
            ("staged", lambda root, summary: summary.update(status="pending"), [
                f"{summary_field}.status must not contain draft or pending in ready mode",
                f"{summary_field}.status contains stale release-state phrase 'pending' in ready mode",
                f"{summary_field}.status must be passed"]),
            ("evidence edited after binding", lambda root, summary: (
                root / "releases" / PUBLIC_RELEASE / "acceptance" / "documented-routes.json").write_text(
                    "{}\n", encoding="utf-8"),
             [f"{bound} must bind the checked-in passed routes evidence",
              f"{bound} receipt release must match qualification release",
              f"{bound} receipt status must be passed",
              f"{summary_field}.candidate_commit must be the routes evidence's candidate_commit"]),
        )
        for case, change, expected in cases:
            with self.subTest(case=case):
                temporary, root = self.public_draft_copy()
                try:
                    release_root = root / "releases" / PUBLIC_RELEASE
                    qualification = self.load(release_root / "qualification.json")
                    reference = qualification["composition"]["documented_route_acceptance"]
                    routes = self.load(root / reference["repository_path"])
                    summary = self.load(ROOT / "releases/v0.14.0/qualification.json")[
                        "documented_route_acceptance"]
                    summary.update(candidate_commit=routes["candidate_commit"],
                                   evidence_path=reference["repository_path"],
                                   evidence_sha256=reference["sha256"])
                    change(root, summary)
                    self.rebind_qualification(release_root, lambda record: record.update(
                        documented_route_acceptance=summary))
                    _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
                    self.assertEqual(errors, expected)
                finally:
                    temporary.cleanup()

    def test_ga_ready_lane_set_must_match_qualification_composition(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        release_root = root / "releases" / PUBLIC_RELEASE
        qualification_path = release_root / "qualification.json"
        manifest_path = release_root / "manifest.json"
        qualification = self.load(qualification_path)
        native_variants = qualification["composition"]["native_runtime_variants"]
        native_variants["unexpected-windows-native"] = dict(
            native_variants["rtx4090-windows-native"]
        )
        self.save(qualification_path, qualification)
        manifest = self.load(manifest_path)
        manifest["qualification"]["summary_sha256"] = hashlib.sha256(
            qualification_path.read_bytes()
        ).hexdigest()
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertIn(
            "ready components.ninfer_variants ids must exactly match qualification.composition.native_runtime_variants keys",
            errors,
        )

    def test_ready_5090_only_has_an_exact_empty_native_set(self) -> None:
        empty_errors: list[str] = []
        VERIFY_RELEASE.validate_exact_lane_set(
            {"components": {"ninfer_variants": []}},
            {"runtime_variants": []},
            {"composition": {"native_runtime_variants": {}}},
            empty_errors,
        )
        self.assertEqual(empty_errors, [])

    def rebind_qualification(self, release_root: Path, mutate) -> None:
        qualification_path = release_root / "qualification.json"
        qualification = self.load(qualification_path)
        mutate(qualification)
        self.save(qualification_path, qualification)
        manifest_path = release_root / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["qualification"]["summary_sha256"] = hashlib.sha256(
            qualification_path.read_bytes()
        ).hexdigest()
        self.save(manifest_path, manifest)

    def test_ready_profile_launch_arguments_must_name_manifest_identities(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        profile_path = root / "profiles" / "qwen38-rtx5090-windows-docker-local.json"
        profile = self.load(profile_path)
        arguments = profile["server"]["arguments"]
        arguments[arguments.index("--config-sha256") + 1] = "0" * 64
        arguments[arguments.index("--binary-sha256") + 1] = "1" * 64
        self.save(profile_path, profile)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertIn(
            "profile: --config-sha256 must occur once and equal runtime_identity.configuration_sha256",
            errors,
        )
        self.assertIn(
            "profile: --binary-sha256 must occur once and equal components.ninfer.server_binary_sha256",
            errors,
        )

    def test_ready_qualification_identity_must_name_the_manifest_component(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)

        def stale_identity(qualification: dict) -> None:
            identity = qualification["runtime_identity"]
            identity["upstream_commit"] = "4eef14a7560d87a3ba717898e1d488a4c4c7246d"
            identity["release_source_archive_sha256"] = "2" * 64

        self.rebind_qualification(root / "releases" / PUBLIC_RELEASE, stale_identity)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertIn(
            "qualification.runtime_identity.upstream_commit must equal components.ninfer.upstream_commit",
            errors,
        )
        self.assertIn(
            "qualification.runtime_identity.release_source_archive_sha256 must equal components.ninfer.source_archive_sha256",
            errors,
        )

    def test_ready_native_variant_rows_must_equal_manifest_components(self) -> None:
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        release_root = root / "releases" / PUBLIC_RELEASE
        for compatibility_path in (root / "compatibility.json", release_root / "compatibility.json"):
            compatibility = self.load(compatibility_path)
            row = compatibility["runtime_variants"][0]
            variant_id = row["id"]
            tag_base, tag_iteration = row["release_tag"].rsplit(".", 1)
            row["release_tag"] = f"{tag_base}.{int(tag_iteration) + 1}"
            row["package_url"] = (
                "https://github.com/alphastorm/ninfer/releases/download/"
                f"{row['release_tag']}/{row['package_name']}"
            )
            row["maximum_context_tokens"] = 65536
            self.save(compatibility_path, compatibility)

        def stale_composition(qualification: dict) -> None:
            entry = qualification["composition"]["native_runtime_variants"]["rtx4090-windows-native"]
            entry["repository_path"] = "releases/v0.4.3/qualification/rtx4090.json"

        self.rebind_qualification(release_root, stale_composition)
        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        for key in ("release_tag", "package_url", "maximum_context_tokens"):
            self.assertIn(
                f"compatibility.runtime_variants[{variant_id}].{key} must equal the manifest component",
                errors,
            )
        self.assertIn(
            "qualification.composition.native_runtime_variants[rtx4090-windows-native].repository_path must equal the manifest component",
            errors,
        )

    def test_pinned_evidence_urls_must_serve_their_recorded_bytes(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        repository = Path(temporary.name)
        receipt = repository / "releases" / "v9.9.9" / "receipt.json"
        receipt.parent.mkdir(parents=True)
        receipt.write_text("{\"gate\": \"passed\"}\n", encoding="utf-8")
        git = ("git", "-C", str(repository))
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "-c", "user.name=t", "-c", "user.email=t@example.com",
                        "add", "-A"], check=True)
        subprocess.run([*git, "-c", "user.name=t", "-c", "user.email=t@example.com",
                        "commit", "-q", "-m", "receipt"], check=True)
        commit = subprocess.run([*git, "rev-parse", "HEAD"], check=True,
                                capture_output=True, text=True).stdout.strip()
        receipt.write_text("{\"gate\": \"passed\", \"edited\": true}\n", encoding="utf-8")
        recorded = hashlib.sha256(b"{\"gate\": \"passed\"}\n").hexdigest()
        raw = f"https://raw.githubusercontent.com/alphastorm/omp-ninfer/{commit}"

        cases = (
            (f"{raw}/releases/v9.9.9/receipt.json", recorded, []),
            (
                f"{raw}/releases/v9.9.9/receipt.json",
                hashlib.sha256(receipt.read_bytes()).hexdigest(),
                [f"receipt pins commit {commit[:12]} whose releases/v9.9.9/receipt.json differs from the recorded SHA-256"],
            ),
            (
                f"{raw}/releases/v9.9.9/absent.json",
                recorded,
                [f"receipt pins commit {commit[:12]} which does not contain releases/v9.9.9/absent.json"],
            ),
            (
                f"https://raw.githubusercontent.com/alphastorm/omp-ninfer/{'f' * 40}/releases/v9.9.9/receipt.json",
                "3" * 64,
                [f"receipt pins commit {'f' * 12} which is not in local git history "
                 "(full history is required to verify pins)"],
            ),
        )
        for url, expected, expected_errors in cases:
            with self.subTest(url=url, expected=expected[:8]):
                errors: list[str] = []
                VERIFY_RELEASE.require_pinned_bytes(repository, url, expected, "receipt", errors, {})
                self.assertEqual(errors, expected_errors)

    def test_cross_component_model_hash_drift_is_rejected(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        profile_path = root / "profiles" / "qwen38-rtx5090-windows-docker-local.json"
        profile = self.load(profile_path)
        profile["model"]["artifact_sha256"] = "0" * 64
        self.save(profile_path, profile)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("profile and manifest model hashes must match", errors)

    def test_profile_client_archive_must_follow_the_manifest_client(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        profile_path = root / "profiles" / "qwen38-rtx5090-windows-docker-local.json"
        profile = self.load(profile_path)
        # A client archive other than the one the manifest pins, as v0.7.3's profile kept v0.7.2's
        # archive after the manifest moved on. The fixture manifest pins 18.0.9; name 18.2.3.
        profile["client"]["component_release_tag"] = "omp-18.2.3-cross-platform-beta-1"
        profile["client"]["asset_sha256"] = "4fca02603e83ecb4f15598818c215da4e17fefd075a5450d502333349a59a311"
        self.save(profile_path, profile)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("profile: client archive must be the manifest's OMP component", errors)

    def test_primary_gpu_receipt_bytes_must_match_compatibility(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        receipt_path = root / "releases" / "v0.2.0-beta.1" / "qualification" / "rtx5090.json"
        receipt = self.load(receipt_path)
        receipt["debug_drift"] = True
        self.save(receipt_path, receipt)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn(
            "primary RTX 5090 qualification SHA-256 must match checked-in bytes",
            errors,
        )

    def test_root_and_release_compatibility_copies_must_match(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        root_compatibility = self.load(root / "compatibility.json")
        root_compatibility["authority_id"] += "-drift"
        self.save(root / "compatibility.json", root_compatibility)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn(
            "root and release compatibility authorities must be byte-identical",
            errors,
        )

    def test_product_public_urls_must_bind_immutable_raw_paths(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["qualification"]["public_url"] = (
            "https://github.com/alphastorm/omp-ninfer/releases/latest"
        )
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn(
            "qualification.public_url must bind an immutable product commit and path",
            errors,
        )

    def test_profile_rejects_host_networking_and_unpublished_ports(self) -> None:
        """On Docker Desktop a host-network bind lives in the engine VM and never reaches the
        operator (omp-ninfer#15); the route is a bridge container published on loopback."""
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        profile_path = root / "profiles" / "qwen38-rtx5090-windows-docker-local.json"
        profile = self.load(profile_path)
        profile["server"]["container_network_mode"] = "host"
        profile["server"]["published_bind_host"] = "0.0.0.0"
        self.save(profile_path, profile)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("profile: container network mode must be bridge", errors)
        self.assertIn("profile: published port must bind the runtime host loopback", errors)

    def test_configuration_identity_reproduces_the_lifecycle_tool(self) -> None:
        """Cross-repository vector: the owner appliance's v0.6.2 lifecycle configuration
        (published on 127.0.0.1:18088, restart unless-stopped, checkpoints on) hashes to the
        identity tools/lifecycle/ninfer_container.py computed and the v0.6.2 receipts record.
        The configuration is pinned here rather than derived from the shipping profile, which
        advances between releases - v0.7.1 added the Host KV pool argument - so the vector keeps
        testing agreement with the other repository instead of restating this one."""
        profile = {
            "model": {"public_id": "q38-ninfer"},
            "server": {
                "published_bind_host": "127.0.0.1",
                "published_port": 18088,
                "restart_policy": "unless-stopped",
                "deployment_profile": "qwen38-5090-v0.6.2",
                "checkpoint_mount_target": "/checkpoints",
                "checkpoint_seccomp_sha256": (
                    "3b7bf1e9fa71bfd8ed536c8aaaa2d40e4f133a0c853d226efd9b9e4966dd1506"
                ),
                "arguments": [
                    "--max-context", "131072",
                    "--kv-capacity", "auto",
                    "--prefill-chunk", "1024",
                    "--kv-dtype", "bf16",
                    "--max-concurrency", "1",
                    "--spec", "mtp",
                    "--draft-tokens", "3",
                    "--lm-head-draft",
                    "--vision",
                    "--preserve-thinking",
                    "--session-checkpoint-quota-mib", "24576",
                    "--session-checkpoint-staging-mib", "256",
                    "--max-private-continuations", "8",
                    "--device-state-slots", "4",
                    "--host-state-slots", "24",
                ],
            },
        }
        self.assertEqual(
            VERIFY_RELEASE.configuration_identity(profile),
            "5eb8a557327acabd91149c3e31ac62fab5f767e113df762f7539176ed91d62f2",
        )

    def test_shipping_profile_declares_the_identity_it_hashes_to(self) -> None:
        """The launcher refuses a container whose declared identity is not the identity of the
        configuration it launches, so the shipping profile's --config-sha256 must be its own
        hash: v0.7.1's pool change moved it from 5eb8a557 to 762e6bf4."""
        profile = self.load(ROOT / "profiles" / "qwen38-rtx5090-manual-tunnel.json")
        arguments = profile["server"]["arguments"]
        declared = arguments[arguments.index("--config-sha256") + 1]
        self.assertEqual(VERIFY_RELEASE.configuration_identity(profile), declared)

    def test_recorded_configuration_identity_must_be_the_launched_one(self) -> None:
        """v0.6.2 declared the checkpointed identity while its launcher ran no checkpoint store;
        a recorded identity that is not the identity of the launched configuration is a false
        public claim and fails the release."""
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        profile_path = root / "profiles" / "qwen38-rtx5090-manual-tunnel.json"
        profile = self.load(profile_path)
        arguments = profile["server"]["arguments"]
        arguments[arguments.index("--host-state-slots") + 1] = "16"
        self.save(profile_path, profile)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
        self.assertIn(
            "profiles/qwen38-rtx5090-manual-tunnel.json: runtime_identity.configuration_sha256 "
            "must equal the identity of the configuration this profile launches",
            errors,
        )

    def test_installable_candidate_must_launch_the_configuration_it_declares(self) -> None:
        """v0.8.3 was staged under a new deployment profile name with v0.8.2's configuration
        identity, which hashes the old name. It passed --require-installable, and the documented
        route's launcher refused it inside a production window."""
        temporary, root = self.upstream_candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / PUBLIC_RELEASE / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["runtime_identity"]["deployment_profile"] = "qwen38-5090-v0.99.0"
        self.save(manifest_path, manifest)
        for profile_path in (root / "profiles").glob("qwen38-rtx5090-*.json"):
            profile = self.load(profile_path)
            profile["server"]["deployment_profile"] = "qwen38-5090-v0.99.0"
            arguments = profile["server"]["arguments"]
            arguments[arguments.index("--deployment-profile") + 1] = "qwen38-5090-v0.99.0"
            self.save(profile_path, profile)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False, require_installable=True)
        self.assertIn(
            "profiles/qwen38-rtx5090-manual-tunnel.json: runtime_identity.configuration_sha256 "
            "must equal the identity of the configuration this profile launches",
            errors,
        )

    def test_installable_candidate_declares_the_configuration_its_lane_qualified(self) -> None:
        """The RTX 5090 lane receipt records the identity its qualified server reported; a
        release declaring another configuration claims a qualification it does not have."""
        temporary, root = self.upstream_candidate_copy()
        self.addCleanup(temporary.cleanup)
        receipt_path = root / "releases" / PUBLIC_RELEASE / "qualification" / "rtx5090.json"
        receipt = self.load(receipt_path)
        receipt["identity"]["deployment_profile"] = "qwen38-5090-v0.99.0"
        self.save(receipt_path, receipt)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False, require_installable=True)
        self.assertIn(
            "primary RTX 5090 qualification receipt identity.deployment_profile must equal "
            "runtime_identity.deployment_profile",
            errors,
        )

    def test_profile_deployment_identity_must_match_manifest(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        profile_path = root / "profiles" / "qwen38-rtx5090-windows-docker-local.json"
        profile = self.load(profile_path)
        profile["server"]["deployment_profile"] = "qwen38-5090-v0.1.0"
        arguments = profile["server"]["arguments"]
        arguments[arguments.index("--deployment-profile") + 1] = "qwen38-5090-v0.1.0"
        self.save(profile_path, profile)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("profile: deployment_profile must match the manifest", errors)

    def test_release_selector_rejects_path_traversal(self) -> None:
        with self.assertRaisesRegex(VERIFY_RELEASE.ContractError, "versioned release"):
            VERIFY_RELEASE.resolve_product_release(ROOT, "../v0.2.0")

    def test_server_arguments_derive_hardware_specific_values(self) -> None:
        profile = self.load(ROOT / "profiles" / "qwen38-rtx5090-windows-docker-local.json")
        profile["omp_provider"]["context_window"] = 65536
        arguments = profile["server"]["arguments"]
        arguments[arguments.index("--max-context") + 1] = "65536"
        arguments[arguments.index("--kv-dtype") + 1] = "int8"
        errors: list[str] = []
        VERIFY_RELEASE.validate_server_arguments(profile, "profile", errors)
        self.assertEqual(errors, [])

        arguments[arguments.index("--max-context") + 1] = "131072"
        VERIFY_RELEASE.validate_server_arguments(profile, "profile", errors)
        self.assertTrue(any("--max-context" in error for error in errors))

    def test_additional_profiles_share_the_release_contract(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        profile_path = root / "profiles" / "qwen38-rtx5090-manual-tunnel.json"
        profile = self.load(profile_path)
        profile["transport"]["runtime_bind_host"] = "0.0.0.0"
        profile["model"]["artifact_sha256"] = "0" * 64
        self.save(profile_path, profile)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn(
            "profiles/qwen38-rtx5090-manual-tunnel.json: runtime endpoint must bind loopback",
            errors,
        )
        self.assertIn(
            "profiles/qwen38-rtx5090-manual-tunnel.json: model hash must match the manifest",
            errors,
        )

    def test_upstream_client_profiles_name_the_stock_stateful_environment(self) -> None:
        """Published OMP 18.4.10 chains Responses turns only with PI_OPENAI_STATEFUL=1; the fork's
        ninferStatefulResponses flag is inert upstream, so a profile still carrying it describes
        a client that silently loses stateful continuation."""
        temporary, root = self.public_draft_copy()
        self.addCleanup(temporary.cleanup)
        profile_path = root / "profiles" / "qwen38-rtx5090-manual-tunnel.json"
        profile = self.load(profile_path)
        del profile["omp_provider"]["stateful_responses_environment"]
        profile["omp_provider"]["ninfer_stateful_responses"] = True
        self.save(profile_path, profile)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn(
            "profiles/qwen38-rtx5090-manual-tunnel.json: OMP provider must name "
            "PI_OPENAI_STATEFUL=1, not the fork's stateful compat flag",
            errors,
        )

    def test_model_url_must_bind_its_recorded_revision(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["components"]["model"]["artifact_url"] = (
            "https://huggingface.co/neroued/Qwen3.8-27B-NInfer/resolve/main/qwen3_8_27b.ninfer"
        )
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertTrue(any("components.model.artifact_url" in error for error in errors), errors)

    def test_omp_distribution_version_must_equal_release_id(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["components"]["omp"]["distribution_version"] = "18.0.5-deadbeef"
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("OMP distribution version must equal release_id", errors)

    def test_v02_requires_the_public_auditable_omp_source_repository(self) -> None:
        self.assertEqual(
            VERIFY_RELEASE.expected_omp_source_repository("v0.2.0-beta.1"),
            "https://github.com/alphastorm/oh-my-pi",
        )
        self.assertEqual(
            VERIFY_RELEASE.expected_omp_source_repository("v0.1.0-beta.1"),
            "https://github.com/alphastorm/omp-monorepo",
        )

    def test_omp_artifact_name_must_bind_version_and_platform(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["components"]["omp"]["artifact_name"] = "omp-macos-arm64.tar.gz"
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn(
            "OMP artifact name must bind release version and primary platform",
            errors,
        )

    def test_candidate_omp_asset_url_must_bind_public_component(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        self.make_candidate(root, manifest)
        manifest["components"]["omp"]["artifact_url"] = (
            "https://github.com/alphastorm/homebrew-omp/releases/download/"
            "omp-18.0.7-cross-platform-preview-5/wrong.tar.gz"
        )
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn(
            "OMP artifact URL must bind the public component tag and artifact name",
            errors,
        )

    def test_candidate_rejects_a_draft_omp_asset(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        self.make_candidate(root, manifest)
        manifest["components"]["omp"]["artifact_published"] = False
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(
            root, require_ready=False, require_installable=True
        )
        self.assertIn(
            "installable release requires a published OMP artifact",
            errors,
        )

    def test_candidate_oci_reference_must_match_manifest_digest(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        self.make_candidate(root, manifest)
        manifest["components"]["ninfer"]["oci_manifest_digest"] = f"sha256:{'f' * 64}"
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("NInfer OCI reference must exactly bind its manifest digest", errors)

    def test_candidate_accepts_the_public_runtime_repository(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        self.make_candidate(root, manifest)
        ninfer = manifest["components"]["ninfer"]
        ninfer["oci_repository"] = "ghcr.io/alphastorm/ninfer-runtime"
        ninfer["oci_reference"] = (
            f"{ninfer['oci_repository']}@{ninfer['oci_manifest_digest']}"
        )
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertNotIn(
            "NInfer OCI reference must exactly bind its manifest digest", errors
        )
        self.assertNotIn(
            "NInfer OCI repository is not an approved public runtime repository", errors
        )

    def test_native_runtime_variant_binds_its_qualification_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = "v0.2.0-beta.1"
            qualification_dir = root / "releases" / release / "qualification"
            qualification_dir.mkdir(parents=True)
            receipt_path = qualification_dir / "rtx3090.json"
            receipt = {
                "status": "passed",
                "beta_qualified": True,
                "identity": {
                    "source_commit": "a" * 40,
                    "server_binary_sha256": "b" * 64,
                    "configuration_sha256": "c" * 64,
                    "model_artifact_sha256": "1" * 64,
                },
                "package": {
                    "filename": "ninfer-rtx3090-omp-v0.2.0-windows-x86_64-cuda12.8-rtx3090.tar.gz",
                    "sha256": "d" * 64,
                    "bytes": 1,
                    "sbom_sha256": "f" * 64,
                    "installer_sha256": "4" * 64,
                    "controller_sha256": "5" * 64,
                    "gpu_owner_controller_sha256": "6" * 64,
                    "state_protection_sha256": "7" * 64,
                },
            }
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            variant = {
                "id": "rtx3090-windows-native",
                "status": "qualified",
                "installable": True,
                "repository": "https://github.com/alphastorm/ninfer",
                "release_tag": "v0.2.0-qwen38-3090-beta.1",
                "source_commit": "a" * 40,
                "source_archive_url": (
                    "https://github.com/alphastorm/ninfer/releases/download/"
                    "v0.2.0-qwen38-3090-beta.1/source.tar.gz"
                ),
                "source_archive_sha256": "e" * 64,
                "package_url": (
                    "https://github.com/alphastorm/ninfer/releases/download/"
                    "v0.2.0-qwen38-3090-beta.1/"
                    "ninfer-rtx3090-omp-v0.2.0-windows-x86_64-cuda12.8-rtx3090.tar.gz"
                ),
                "package_name": (
                    "ninfer-rtx3090-omp-v0.2.0-windows-x86_64-"
                    "cuda12.8-rtx3090.tar.gz"
                ),
                "package_sha256": "d" * 64,
                "package_bytes": 1,
                "sbom_url": (
                    "https://github.com/alphastorm/ninfer/releases/download/"
                    "v0.2.0-qwen38-3090-beta.1/package.spdx.json"
                ),
                "sbom_sha256": "f" * 64,
                "installer_url": (
                    "https://github.com/alphastorm/ninfer/releases/download/"
                    "v0.2.0-qwen38-3090-beta.1/Install-Release.ps1"
                ),
                "installer_sha256": "4" * 64,
                "controller_url": (
                    "https://github.com/alphastorm/ninfer/releases/download/"
                    "v0.2.0-qwen38-3090-beta.1/Control-Release.ps1"
                ),
                "controller_sha256": "5" * 64,
                "gpu_owner_controller_url": (
                    "https://github.com/alphastorm/ninfer/releases/download/"
                    "v0.2.0-qwen38-3090-beta.1/Control-GpuOwner.ps1"
                ),
                "gpu_owner_controller_sha256": "6" * 64,
                "state_protection_url": (
                    "https://github.com/alphastorm/ninfer/releases/download/"
                    "v0.2.0-qwen38-3090-beta.1/Protect-StateRoot.ps1"
                ),
                "state_protection_sha256": "7" * 64,
                "server_binary_sha256": "b" * 64,
                "configuration_sha256": "c" * 64,
                "model_artifact_sha256": "1" * 64,
                "maximum_context_tokens": 65536,
                "qualification": {
                    "summary": "qualification/rtx3090.json",
                    "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                    "public_url": (
                        "https://raw.githubusercontent.com/alphastorm/omp-ninfer/"
                        + "2" * 40
                        + "/releases/v0.2.0-beta.1/qualification/rtx3090.json"
                    ),
                },
            }
            compatibility = {
                "runtime_variants": [{
                    "id": variant["id"],
                    "status": "qualified",
                    "installable": True,
                }]
            }
            errors: list[str] = []
            VERIFY_RELEASE.validate_ninfer_variants(
                root, release, [variant], compatibility, "1" * 64, errors
            )
            self.assertEqual(errors, [])

            old_tag = variant["release_tag"]
            variant["release_tag"] = "v0.6.2-qwen38-3090-beta.1"
            variant["package_name"] = "ninfer-rtx3090-native-v0.6.2-beta.1-windows-x86_64-cuda13.3-rtx3090.tar.gz"
            for field, value in tuple(variant.items()):
                if field.endswith("_url"):
                    variant[field] = value.replace(old_tag, variant["release_tag"])
            variant["package_url"] = (
                f"https://github.com/alphastorm/ninfer/releases/download/{variant['release_tag']}/{variant['package_name']}")
            receipt["package"]["filename"] = variant["package_name"]
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            variant["qualification"]["sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
            errors = []
            VERIFY_RELEASE.validate_ninfer_variants(root, release, [variant], compatibility, "1" * 64, errors)
            self.assertEqual(errors, [])
            for field in ("release_tag", "package_name"):
                original = variant[field]
                variant[field] = original.replace("v0.6.2", "v0.6.4")
                errors = []
                VERIFY_RELEASE.validate_ninfer_variants(root, release, [variant], compatibility, "1" * 64, errors)
                self.assertIn(f"components.ninfer_variants.rtx3090-windows-native.{field} is invalid", errors)
                variant[field] = original

            receipt["status"] = "incomplete"
            receipt["beta_qualified"] = False
            receipt["installable"] = False
            receipt["deferred_gates"] = ["fresh Windows hardware gate"]
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            variant["status"] = "preview"
            variant["installable"] = False
            variant["qualification"]["sha256"] = hashlib.sha256(
                receipt_path.read_bytes()
            ).hexdigest()
            compatibility["runtime_variants"][0]["status"] = "preview"
            compatibility["runtime_variants"][0]["installable"] = False
            errors = []
            VERIFY_RELEASE.validate_ninfer_variants(
                root, release, [variant], compatibility, "1" * 64, errors
            )
            self.assertEqual(errors, [])

            variant["package_sha256"] = "3" * 64
            errors = []
            VERIFY_RELEASE.validate_ninfer_variants(
                root, release, [variant], compatibility, "1" * 64, errors
            )
            self.assertIn(
                "components.ninfer_variants.rtx3090-windows-native qualification package must match",
                errors,
            )

    def test_ga_native_variant_checksum_closure_is_complete(self) -> None:
        errors = []
        VERIFY_RELEASE.validate_ninfer_variants(ROOT, "v0.9.0", [{"id": "unknown-native"}],
                                                {"runtime_variants": []}, "a" * 64, errors)
        self.assertIn("NInfer runtime variants must use the closed set in canonical order", errors)
        prefix = "components.ninfer_variants.rtx4090-windows-native"
        cases = (
            "missing_digest",
            "missing_file",
            "outer_digest_drift",
            "installer_entry_drift",
            "package_entry_drift",
            "source_entry_missing",
        )
        for case in cases:
            with self.subTest(case=case):
                temporary, root = self.public_draft_copy()
                try:
                    release_root = root / "releases" / PUBLIC_RELEASE
                    manifest_path = release_root / "manifest.json"
                    manifest = self.load(manifest_path)
                    variant = next(
                        item
                        for item in manifest["components"]["ninfer_variants"]
                        if item["id"] == "rtx4090-windows-native"
                    )
                    checksums_path = (
                        release_root
                        / "qualification"
                        / "rtx4090-windows-native.SHA256SUMS"
                    )
                    checksums_text = checksums_path.read_text(encoding="utf-8")

                    if case == "missing_digest":
                        variant.pop("checksums_sha256")
                        expected_error = (
                            f"{prefix}.checksums_sha256 must be a lower-case SHA-256"
                        )
                    elif case == "missing_file":
                        checksums_path.unlink()
                        expected_error = f"{prefix} checksums file must exist"
                    elif case == "outer_digest_drift":
                        variant["checksums_sha256"] = "0" * 64
                        expected_error = (
                            f"{prefix}.checksums_sha256 must match the checksums file"
                        )
                    elif case == "source_entry_missing":
                        # Native-packager sets always list their source archive.
                        filename = variant["source_archive_url"].rsplit("/", 1)[-1]
                        mutated_text = "\n".join(
                            line for line in checksums_text.split("\n")
                            if not line.endswith(f"  {filename}")
                        )
                        self.assertNotEqual(mutated_text, checksums_text)
                        checksums_path.write_text(mutated_text, encoding="utf-8")
                        variant["checksums_sha256"] = hashlib.sha256(
                            checksums_path.read_bytes()
                        ).hexdigest()
                        expected_error = (
                            f"{prefix} checksums entry {filename} must match "
                            "source_archive_sha256"
                        )
                    else:
                        if case == "installer_entry_drift":
                            digest_field = "installer_sha256"
                            filename = "Install-Release.ps1"
                        else:
                            digest_field = "package_sha256"
                            filename = variant["package_name"]
                        original_entry = f"{variant[digest_field]}  {filename}"
                        stale_entry = f"{'0' * 64}  {filename}"
                        mutated_text = checksums_text.replace(
                            original_entry, stale_entry
                        )
                        self.assertNotEqual(mutated_text, checksums_text)
                        checksums_path.write_text(mutated_text, encoding="utf-8")
                        variant["checksums_sha256"] = hashlib.sha256(
                            checksums_path.read_bytes()
                        ).hexdigest()
                        expected_error = (
                            f"{prefix} checksums entry {filename} must match {digest_field}"
                        )

                    self.save(manifest_path, manifest)
                    _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
                    self.assertIn(expected_error, errors)
                finally:
                    temporary.cleanup()

        temporary, root = self.public_draft_copy()
        try:
            release_root = root / "releases" / PUBLIC_RELEASE
            manifest_path = release_root / "manifest.json"
            manifest = self.load(manifest_path)
            variant = manifest["components"]["ninfer_variants"][0]
            checksums_path = (
                release_root
                / "qualification"
                / f"{variant['id']}.SHA256SUMS"
            )
            source_filename = variant["source_archive_url"].rsplit("/", 1)[-1]
            checksums_text = checksums_path.read_text(encoding="utf-8")
            original_entry = (
                f"{variant['source_archive_sha256']}  {source_filename}"
            )
            mutated_text = checksums_text.replace(
                original_entry, f"{'0' * 64}  {source_filename}"
            )
            self.assertNotEqual(mutated_text, checksums_text)
            checksums_path.write_text(mutated_text, encoding="utf-8")
            variant["checksums_sha256"] = hashlib.sha256(
                checksums_path.read_bytes()
            ).hexdigest()
            self.save(manifest_path, manifest)

            _, errors = VERIFY_RELEASE.validate(root, require_ready=True)
            self.assertIn(
                f"components.ninfer_variants.{variant['id']} checksums entry "
                f"{source_filename} must match source_archive_sha256",
                errors,
            )
        finally:
            temporary.cleanup()

    def test_local_packaging_oci_digest_drift_is_rejected(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        manifest_path = root / "releases" / "v0.2.0-beta.1" / "manifest.json"
        manifest = self.load(manifest_path)
        manifest["components"]["ninfer"]["oci_manifest_digest"] = f"sha256:{'f' * 64}"
        self.save(manifest_path, manifest)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("local packaging and manifest OCI digests must match", errors)

    def test_private_paths_are_rejected_from_public_receipts(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        qualification_path = root / "releases" / "v0.2.0-beta.1" / "qualification.json"
        qualification = self.load(qualification_path)
        qualification["debug_path"] = "/Users/private/operator-receipt.json"
        self.save(qualification_path, qualification)

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertTrue(any("private marker" in error for error in errors), errors)

    def test_private_paths_are_rejected_from_public_brand_sources(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        (root / "BRAND.md").write_text(
            "Regenerate from /Users/private/Desktop/brand.\n", encoding="utf-8"
        )
        assets = root / "assets"
        assets.mkdir()
        (assets / "banner.html").write_text(
            "<p>source: C:\\Users\\private\\banner</p>\n", encoding="utf-8"
        )

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("BRAND.md contains private marker '/Users/'", errors)
        self.assertIn(
            "assets/banner.html contains private marker 'C:\\\\Users\\\\'", errors
        )

    def test_missing_local_documentation_link_is_rejected(self) -> None:
        temporary, root = self.candidate_copy()
        self.addCleanup(temporary.cleanup)
        (root / "README.md").write_text("[missing](docs/not-there.md)\n", encoding="utf-8")

        _, errors = VERIFY_RELEASE.validate(root, require_ready=False)
        self.assertIn("README.md has missing local link: docs/not-there.md", errors)

    def test_git_ignored_local_artifacts_are_not_published_documents(self) -> None:
        # A RepoPrompt plan export under the ignored prompt-exports/ once failed staging with a
        # missing link; ignored files are never published, but an untracked one would be.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".gitignore").write_text("prompt-exports/\n", encoding="utf-8")
            (root / "prompt-exports").mkdir()
            (root / "prompt-exports" / "plan.md").write_text(
                "[banner](assets/banner.png) from /Users/someone\n", encoding="utf-8")
            (root / "notes.md").write_text("[missing](gone.md) from sf-pc\n", encoding="utf-8")
            errors: list[str] = []
            VERIFY_RELEASE.validate_markdown_links(root, errors)
            VERIFY_RELEASE.validate_public_text(root, errors)
        self.assertEqual(errors, ["notes.md has missing local link: gone.md",
                                  "notes.md contains private marker 'sf-pc'"])


if __name__ == "__main__":
    unittest.main()
