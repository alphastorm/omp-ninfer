"""Review publication preserves source evidence and refuses an unclosed subject."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


LEDGER = module("review_ledger", ROOT / "scripts/review_ledger.py")
FIXTURES = module("acceptance_fixtures", ROOT / "tests/acceptance_fixtures.py")
from release_io import atomic_write_json, git


class ReviewLedgerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        git(self.root, "init", "--quiet")
        git(self.root, "config", "user.name", "Synthetic Test")
        git(self.root, "config", "user.email", "test@example.invalid")
        atomic_write_json(self.root / "initial.json", {})
        git(self.root, "add", "initial.json")
        git(self.root, "commit", "--quiet", "-m", "test: initialize synthetic subject")
        self.candidate = git(self.root, "rev-parse", "HEAD").strip()
        self.release = "v0.20.0"
        self.out = self.root / "inputs"
        FIXTURES.write_reviews(self.out, self.release, self.candidate, {
            "components": {"ninfer": {"source_commit": "1" * 40}}})
        self.manifest_path = self.out / "reviews/manifest.json"
        self.values = LEDGER.load(self.out / "values.json")
        self.qualification = self.root / "releases" / self.release / "qualification.json"
        atomic_write_json(self.qualification, {
            "composition": {"review": {"status": "pending", "scope": "Synthetic staged review."}},
            "observed_gates": {"other_gate": {"status": "passed"}},
        })

    def write(self, **kwargs):
        return LEDGER.write_ledger(self.root, self.release, self.candidate,
                                   self.manifest_path, self.values, **kwargs)

    def test_closed_reviews_write_a_verifier_accepted_g4_binding_and_check_is_read_only(self):
        result = self.write()
        ledger = LEDGER.load(self.root / result["repository_path"])
        qualification = LEDGER.load(self.qualification)
        self.assertEqual(ledger["product_tooling"]["stage_commit"], self.candidate)
        self.assertFalse(ledger["publication_authorized"])
        self.assertEqual(qualification["observed_gates"]["other_gate"], {"status": "passed"})
        review = qualification["composition"]["review"]
        self.assertEqual(review["status"], ledger["status"])
        self.assertEqual(review, LEDGER.composition_review(ledger, self.values, result["repository_path"]))
        self.assertIn(self.candidate, review["scope"])
        self.assertIn(result["repository_path"], review["scope"])
        errors = []
        LEDGER.validate_review_ledger(self.root, self.release, qualification, errors)
        self.assertEqual(errors, [])
        before = self.qualification.read_bytes()
        self.assertEqual(self.write(check=True), result)
        self.assertEqual(self.qualification.read_bytes(), before)
        atomic_write_json(self.root / result["repository_path"], {})
        with self.assertRaisesRegex(SystemExit, "not up to date"):
            self.write(check=True)

    def test_every_nonclosed_section_and_ledger_status_is_refused_before_writing(self):
        original = LEDGER.load(self.manifest_path)
        for section in LEDGER.SECTIONS:
            for status in ("pending", "open", "", None):
                with self.subTest(section=section, status=status):
                    manifest = deepcopy(original)
                    manifest[section]["status"] = status
                    atomic_write_json(self.manifest_path, manifest)
                    with self.assertRaisesRegex(SystemExit, "not closed"):
                        self.write()
                    self.assertFalse((self.qualification.parent / "review").exists())
        atomic_write_json(self.manifest_path, original)
        self.values["ledger_status"] = "pending"
        with self.assertRaisesRegex(SystemExit, "not closed"):
            self.write()

    def test_nonclosed_source_record_cannot_be_approved_by_values(self):
        record = self.out / "reviews/product_tooling/review-record.json"
        source = LEDGER.load(record)
        source["status"] = "open"
        atomic_write_json(record, source)
        with self.assertRaisesRegex(SystemExit, "not closed"):
            self.write()

    def test_another_operators_review_edit_is_never_overwritten(self):
        original = LEDGER.load(self.qualification)
        for edited in (None, {}, {"status": "draft"}, {"status": "passed"},
                       {"status": "closed-by-disposition", "scope": "A different closed review."}):
            with self.subTest(edited=edited):
                qualification = deepcopy(original)
                qualification["composition"]["review"] = edited
                atomic_write_json(self.qualification, qualification)
                before = self.qualification.read_bytes()
                with self.assertRaisesRegex(SystemExit, "neither pending nor the generated"):
                    self.write()
                self.assertEqual(self.qualification.read_bytes(), before)
                self.assertFalse((self.qualification.parent / "review").exists())

    def test_check_detects_a_pending_composition_review_without_writing_either_file(self):
        result = self.write()
        ledger_path = self.root / result["repository_path"]
        qualification = LEDGER.load(self.qualification)
        qualification["composition"]["review"] = {"status": "pending", "scope": "Restaged review."}
        atomic_write_json(self.qualification, qualification)
        before = self.qualification.read_bytes(), ledger_path.read_bytes()
        with self.assertRaisesRegex(SystemExit, "composition review is not up to date"):
            self.write(check=True)
        self.assertEqual((self.qualification.read_bytes(), ledger_path.read_bytes()), before)
        self.write()
        self.assertEqual(LEDGER.load(self.qualification)["composition"]["review"]["status"],
                         "closed-by-disposition")

    def test_only_product_review_is_described_when_no_runtime_review_was_supplied(self):
        manifest = LEDGER.load(self.manifest_path)
        atomic_write_json(self.manifest_path, {"product_tooling": manifest["product_tooling"]})
        result = self.write()
        ledger = LEDGER.load(self.root / result["repository_path"])
        self.assertNotIn("native_runtime", ledger)
        self.assertNotIn("native_component_delta", ledger)
        scope = LEDGER.load(self.qualification)["composition"]["review"]["scope"]
        self.assertIn("Product full council product_tooling", scope)
        self.assertNotIn("Runtime", scope)
        self.assertNotIn("native", scope)
        self.assertNotIn(self.values["composition_review"]["native_runtime_summary"], scope)

    def test_scope_defaults_to_closed_source_closures_when_no_result_clauses_are_supplied(self):
        del self.values["composition_review"]
        self.values["product_council"].pop("residuals_sentence")
        result = self.write()
        scope = LEDGER.load(self.qualification)["composition"]["review"]["scope"]
        self.assertIn("closed (closed-by-disposition). Closed synthetic review.", scope)
        self.assertIn(self.values["product_council"]["scope_sentence"], scope)

    def test_private_result_clauses_are_refused_before_public_writes(self):
        self.values["composition_review"]["native_runtime_summary"] = LEDGER.PRIVATE_MARKERS[0] + "synthetic"
        with self.assertRaisesRegex(SystemExit, "private marker"):
            self.write()
        self.assertFalse((self.qualification.parent / "review").exists())

    def test_a_nonancestor_commit_and_a_changed_stage_commit_are_refused(self):
        tree = git(self.root, "rev-parse", "HEAD^{tree}").strip()
        detached = git(self.root, "commit-tree", tree, "-m", "test: unrelated subject").strip()
        with self.assertRaisesRegex(SystemExit, "not an ancestor"):
            LEDGER.build(self.root, self.release, detached, self.manifest_path, self.values)
        self.values["product_council"]["stage_commit"] = detached
        with self.assertRaisesRegex(SystemExit, "stage_commit"):
            self.write()

    def test_missing_approval_and_private_markers_are_refused(self):
        self.values["approval_granted"] = False
        with self.assertRaisesRegex(SystemExit, "grant G4 approval"):
            self.write()
        self.values["approval_granted"] = True
        self.values["product_council"]["closure"] = LEDGER.PRIVATE_MARKERS[0] + "synthetic"
        with self.assertRaisesRegex(SystemExit, "private marker"):
            self.write()

    def test_known_privacy_rule_examples_are_sanitized_and_counted_without_changing_sources(self):
        source = self.out / "reviews/product_tooling/critic.json"
        sentinel = "GPU-" + "12345678-1234-1234-1234-123456789abc"
        prefix = "C:/" + "Users/"
        atomic_write_json(source, {"summary": prefix + "synthetic " + sentinel,
                                   "evidence": [], "unresolved": []})
        before = source.read_bytes()
        result = self.write()
        self.assertEqual(result["sanitized"], {
            "a forward-slash Windows user-profile prefix": 1, "a synthetic GPU-identifier sentinel": 1})
        self.assertEqual(source.read_bytes(), before)
        output = (self.root / result["repository_path"]).read_text()
        self.assertNotIn(prefix, output)
        self.assertNotIn(sentinel, output)

    def test_verifier_self_check_happens_before_either_public_write(self):
        before = self.qualification.read_bytes()
        def refuse(root, release, qualification, errors):
            errors.append("synthetic verifier refusal")
        with patch.object(LEDGER, "validate_review_ledger", refuse):
            with self.assertRaisesRegex(SystemExit, "synthetic verifier refusal"):
                self.write()
        self.assertEqual(before, self.qualification.read_bytes())
        self.assertFalse((self.qualification.parent / "review").exists())

    def test_cli_writes_using_the_directory_manifest(self):
        script = self.root / "scripts/review_ledger.py"
        shutil.copytree(ROOT / "scripts", script.parent)
        result = subprocess.run([
            sys.executable, str(script), "--release", self.release, "--candidate", self.candidate,
            "--reviews", str(self.manifest_path.parent), "--values", str(self.out / "values.json"),
        ], cwd=self.root, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "closed-by-disposition")

    def test_history_fixture_materializes_the_full_public_tag_commit(self):
        git(self.root, "tag", self.release, self.candidate)
        tree = self.root / "public-tag"
        commit = FIXTURES.public_release_tree(self.root, self.release, tree)
        self.assertEqual(commit, self.candidate)
        self.assertEqual(git(tree, "rev-parse", "HEAD").strip(), self.candidate)
        self.assertEqual((tree / "initial.json").read_bytes(), (self.root / "initial.json").read_bytes())

    def test_history_fixture_skips_shallow_clones_unless_history_is_required(self):
        shallow = self.root / "shallow"
        subprocess.run(["git", "clone", "--quiet", "--depth=1", self.root.as_uri(), str(shallow)],
                       check=True, capture_output=True)
        with patch.dict(os.environ, {"OMP_NINFER_REQUIRE_HISTORY": "0"}):
            with self.assertRaises(unittest.SkipTest):
                FIXTURES.public_release_tree(shallow, self.release, self.root / "unused")
        with patch.dict(os.environ, {"OMP_NINFER_REQUIRE_HISTORY": "1"}):
            with self.assertRaisesRegex(AssertionError, "full public history"):
                FIXTURES.public_release_tree(shallow, self.release, self.root / "unused")


class PrivateReviewGoldenTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("OMP_NINFER_PRIVATE_FIXTURES"),
                         "private fixture locations are not configured")
    def test_retained_closed_directories_reproduce_the_published_ledger_bytes(self):
        locations = LEDGER.load(Path(os.environ["OMP_NINFER_PRIVATE_FIXTURES"]).expanduser())["v0.19.0"]
        reviews = locations["reviews"]
        constants = LEDGER.load(Path(reviews["ledger_token_sources"]).expanduser())["constants"]
        values = LEDGER.load(Path(reviews["values"]).expanduser())
        # These two lead-written result clauses and the subject label are not stated verbatim
        # in the closed ledger. Preserve the historical scope by supplying them as values.
        values["composition_review"] = {
            "native_runtime_summary": "closed with no confirmed in-scope P0 or P1 finding; its residuals are deferred to https://github.com/alphastorm/ninfer/issues/123.",
            "native_component_delta_subject": "the native power-check delta",
            "native_component_delta_summary": "found no P0 or P1 finding; its two diagnostic-evidence gaps are deferred to https://github.com/alphastorm/ninfer/issues/127.",
        }
        manifest = {
            "native_runtime": {
                "directory": reviews["runtime_council"], "status": constants["RUNTIME_COUNCIL_STATUS"],
                "closure": constants["RUNTIME_COUNCIL_CLOSURE"]},
            "native_component_delta": {
                "directory": reviews["focused_native_delta"], "status": constants["FOCUSED_REVIEW_STATUS"],
                "closure": constants["FOCUSED_REVIEW_CLOSURE"], "base_commit": constants["RUNTIME_SOURCE"]},
            "product_tooling": {"directory": reviews["product_council"],
                                "status": values["product_council"]["status"]},
        }
        with tempfile.TemporaryDirectory() as temporary:
            public_tree = Path(temporary) / "public-tag"
            FIXTURES.public_release_tree(ROOT, "v0.19.0", public_tree)
            reference = public_tree / "releases/v0.19.0/review/runtime-ledger.json"
            expected = LEDGER.load(reference)
            path = Path(temporary) / "manifest.json"
            atomic_write_json(path, manifest)
            ledger, counts = LEDGER.build(public_tree, "v0.19.0", locations["candidate"], path,
                                          values, as_of=expected["as_of"])
            self.assertEqual((json.dumps(ledger, indent=2) + "\n").encode(), reference.read_bytes())
            self.assertEqual(counts, {})
            review = LEDGER.composition_review(ledger, values, reference.relative_to(public_tree).as_posix())
            published = LEDGER.load(public_tree / "releases/v0.19.0/qualification.json")["composition"]["review"]
            self.assertEqual(review, published)
            self.assertEqual(json.dumps(review, indent=2), json.dumps(published, indent=2))


if __name__ == "__main__":
    unittest.main()
