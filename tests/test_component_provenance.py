"""Only manifest-derived runtime provenance may appear in new release evidence."""

from __future__ import annotations

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("component_provenance", ROOT / "scripts/verify_release.py")
assert SPEC is not None and SPEC.loader is not None
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)
from release_io import atomic_write_json


class ComponentProvenanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manifest = VERIFY.load_json(ROOT / "releases/v0.19.0/manifest.json")
        self.previous = copy.deepcopy(self.manifest)
        atomic_write_json(self.root / "releases/v0.19.0/manifest.json", self.previous)
        self.manifest["release"] = "v0.20.0"
        self.manifest["limitations"] = ["Qualification is limited to the documented routes."]
        self.manifest["publication"]["targets"] = ["Public component releases"]
        self.release = self.manifest["release"]

    def test_carried_and_recut_components_and_distinct_sources_are_derived(self):
        provenance = VERIFY.component_provenance(self.root, self.release, self.manifest)
        self.assertEqual([row["id"] for row in provenance["components"]],
                         ["rtx5090-container", *VERIFY.NINFER_VARIANT_IDS])
        self.assertTrue(all(row["disposition"] == "carried" and row["carried_from"] == "v0.19.0"
                            for row in provenance["components"]))
        self.assertEqual(provenance["distinct_source_commits"], 3)
        self.manifest["components"]["ninfer"]["source_commit"] = "f" * 40
        self.manifest["components"]["ninfer"]["release_tag"] = "v1.0.0-qwen38-5090-beta.1"
        provenance = VERIFY.component_provenance(self.root, self.release, self.manifest)
        self.assertEqual(provenance["components"][0]["disposition"], "recut")
        self.assertIsNone(provenance["components"][0]["carried_from"])
        self.assertIn("re-cut for this release", provenance["statement"])
        for variant in self.manifest["components"]["ninfer_variants"]:
            variant["source_commit"] = "f" * 40
        self.assertEqual(VERIFY.component_provenance(
            self.root, self.release, self.manifest)["distinct_source_commits"], 1)

    def validate(self, qualification, *, acceptance=False):
        errors = []
        VERIFY.validate_component_provenance(
            self.root, self.release, self.manifest, {}, qualification, errors,
            acceptance=acceptance)
        return errors

    def test_both_published_false_sentences_are_refused_from_the_new_gate(self):
        published = ROOT / "releases/v0.19.0"
        sentences = (
            VERIFY.load_json(published / "qualification.json")["documented_route_acceptance"]["scope"],
            VERIFY.load_json(published / "acceptance/composed-external-installation.json")["client"]["note"],
        )
        for sentence in sentences:
            with self.subTest(sentence=sentence):
                errors = self.validate({"interpretation": sentence})
                self.assertTrue(any("qualification.interpretation" in error for error in errors), errors)
        self.assertEqual(self.validate({"interpretation": "The documented routes passed."}), [])

    def test_generated_statement_is_masked_but_added_claims_are_not(self):
        statement = VERIFY.component_provenance(self.root, self.release, self.manifest)["statement"]
        self.assertEqual(self.validate({"interpretation": statement + " Observed routes passed."}), [])
        self.assertTrue(self.validate({"interpretation": statement + " All runtimes were rebuilt."}))

    def test_claim_vocabulary_matches_each_supported_spelling(self):
        for claim in ("re-cut", "recut", "newly cut", "newly-cut", "fresh cut", "freshly-cut",
                      "rebuilt", "re-built", "rebuild", "carried", "carry-over",
                      "one source", "one N source", "one-source", "single source", "same-source"):
            with self.subTest(claim=claim):
                self.assertTrue(VERIFY.provenance_claim_errors({"note": f"Runtime {claim}."},
                                                              "evidence"))

    def test_acceptance_requires_exact_record_note_scope_and_plan_dispositions(self):
        provenance = VERIFY.component_provenance(self.root, self.release, self.manifest)
        statement = provenance["statement"]
        external = {"component_provenance": provenance}
        path = self.root / "releases" / self.release / "acceptance/composed-external-installation.json"
        atomic_write_json(path, external)
        qualification = {"composition": {"external_installation_acceptance": {
            "note": statement + " Observed routes passed."}},
            "documented_route_acceptance": {"scope": statement + " Documented routes passed."}}
        self.assertEqual(self.validate(qualification, acceptance=True), [])
        external["component_provenance"]["distinct_source_commits"] = 1
        atomic_write_json(path, external)
        self.assertTrue(self.validate(qualification, acceptance=True))
        external["component_provenance"] = provenance
        external["component_provenance"]["distinct_source_commits"] = 3
        atomic_write_json(path, external)
        qualification["composition"]["external_installation_acceptance"]["note"] = "Observed routes passed."
        self.assertTrue(self.validate(qualification, acceptance=True))
        qualification["composition"]["external_installation_acceptance"]["note"] = statement
        atomic_write_json(self.root / "releases" / self.release / "plan.json", {
            "components": [{"id": row["id"], "disposition": "recut"} for row in provenance["components"]]})
        self.assertTrue(self.validate(qualification, acceptance=True))

    def test_historical_releases_retain_their_contract(self):
        self.release = "v0.19.0"
        self.assertEqual(self.validate({"interpretation": "All runtimes were rebuilt."}), [])


class ComponentComposerTests(unittest.TestCase):
    def setUp(self):
        from test_compose_route_acceptance import UpstreamCompositionTests, MODULE
        self.fixture = UpstreamCompositionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.module = MODULE
        manifest_path = self.fixture.release_root / "manifest.json"
        manifest = MODULE.load(manifest_path)
        manifest["components"]["ninfer"].update(
            release_tag="v1.0.0-qwen38-5090-beta.1", source_commit="1" * 40)
        manifest["components"]["ninfer_variants"][0]["release_tag"] = "v1.0.0-qwen38-4090-beta.1"
        MODULE.save(manifest_path, manifest)
        self.evidence_path = self.fixture.root / "evidence.json"
        evidence = MODULE.load(self.evidence_path)
        evidence["documented_routes"]["scope"] = "Documented routes and stock client installs passed."
        MODULE.save(self.evidence_path, evidence)

    def test_composer_generates_provenance_and_atomically_writes_every_output(self):
        module = self.module
        with mock.patch.object(module, "atomic_write", wraps=module.atomic_write) as write:
            self.assertEqual(self.fixture.compose(), 0)
        self.assertGreater(write.call_count, 10)
        external = module.load(self.fixture.release_root / "acceptance/composed-external-installation.json")
        manifest = module.load(self.fixture.release_root / "manifest.json")
        provenance = VERIFY.component_provenance(self.fixture.root, self.fixture.release, manifest)
        self.assertEqual(external["component_provenance"], provenance)
        qualification = module.load(self.fixture.release_root / "qualification.json")
        self.assertTrue(qualification["documented_route_acceptance"]["scope"].startswith(provenance["statement"]))
        self.assertTrue(qualification["composition"]["external_installation_acceptance"]["note"].startswith(
            provenance["statement"]))
        for call in write.call_args_list:
            self.assertEqual(call.args[0].read_bytes(), call.args[1])

    def test_evidence_claim_refuses_before_any_output_write(self):
        evidence = self.module.load(self.evidence_path)
        evidence["composed"]["client_note"] = "All runtime components were rebuilt from one source."
        self.module.save(self.evidence_path, evidence)
        before = {path: path.read_bytes() for path in self.fixture.root.rglob("*") if path.is_file()}
        with self.assertRaisesRegex(SystemExit, "composed.client_note"):
            self.fixture.compose()
        self.assertEqual({path: path.read_bytes() for path in self.fixture.root.rglob("*")
                          if path.is_file()}, before)

    def test_every_authored_prose_field_uses_the_shared_claim_scan(self):
        evidence = self.module.load(self.evidence_path)
        fields = [
            ("documented_routes", "scope"),
            *(("composed", field) for field in (
                "qualification_note", "client_note", "limitations",
                "runtime_qualification", "vision_scope", "mode")),
            *(("platforms", profile, "limitations") for profile in evidence["platforms"]),
        ]
        for fields_path in fields:
            with self.subTest(field=fields_path):
                document = copy.deepcopy(evidence)
                parent = document
                for field in fields_path[:-1]:
                    parent = parent[field]
                parent[fields_path[-1]] = "These components were newly cut."
                errors = self.module.evidence_provenance_claim_errors(document)
                self.assertTrue(any(".".join(fields_path) in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
