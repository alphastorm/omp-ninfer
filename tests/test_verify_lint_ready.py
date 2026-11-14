"""Ready checks run as soon as staging has produced their required inputs."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify_lint_ready", ROOT / "scripts/verify_release.py")
assert SPEC is not None and SPEC.loader is not None
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)
from release_io import atomic_write, atomic_write_json

HISTORY_SPEC = importlib.util.spec_from_file_location("lint_history", ROOT / "tests/history.py")
assert HISTORY_SPEC is not None and HISTORY_SPEC.loader is not None
HISTORY = importlib.util.module_from_spec(HISTORY_SPEC)
HISTORY_SPEC.loader.exec_module(HISTORY)


def stage_successor(root: Path, *, release: str | None = None) -> str:
    """Carry the latest published runtime and client through the real staging CLI."""
    manifests = [json.loads(path.read_text(encoding="utf-8"))
                 for path in (root / "releases").glob("*/manifest.json")]
    source = max((item for item in manifests
                  if item.get("status") == "ready" and VERIFY.ga_release(item.get("release"))),
                 key=lambda item: VERIFY.product_version(item["release"]))
    major, minor, patch = VERIFY.product_version(source["release"])
    release = release or f"v{major}.{minor}.{patch + 1}"
    runtime = source["components"]["ninfer"]
    command = [
        sys.executable, str(root / "scripts/stage_release.py"), "--from", source["release"],
        "--release", release, "--keep-deployment-profile",
        "--omp-component", f"releases/{source['release']}/qualification/client-components.json",
        "--source-tag", runtime["source_archive_url"].split("/download/", 1)[1].split("/")[0],
        "--archive-name", runtime["binary_archive_url"].rsplit("/", 1)[1],
    ]
    for flag, key in (
        ("release-tag", "release_tag"), ("source-commit", "source_commit"),
        ("binary-sha", "server_binary_sha256"), ("archive-sha", "binary_archive_sha256"),
        ("source-archive-sha", "source_archive_sha256"), ("sbom-sha", "sbom_sha256"),
        ("image-digest", "oci_manifest_digest"), ("runtime-receipt-release", "runtime_receipt_release"),
    ):
        command.extend((f"--{flag}", runtime[key]))
    result = subprocess.run(command, cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return release


class ReadyTableTests(unittest.TestCase):
    def test_ready_table_preserves_every_legacy_check(self):
        expected = {
            "ready_status", "qualification_summary", "qualification_public_url",
            "external_installation", "publication_blockers",
            "validate_release_markdown_tokens", "validate_exact_lane_set",
            "validate_ready_state_consistency", "validate_review_ledger",
            "validate_documented_route_acceptance", "validate_frozen_native_pins",
            "validate_native_route_policy", "validate_ga_evidence_bindings",
            "validate_continuation_capability", "validate_aggregate_as_of",
            "validate_manifest_tag_prose", "validate_pinned_evidence",
            "upstream_client_leftovers", "validate_release_documentation",
        }
        rows = VERIFY.READY_CHECKS
        self.assertEqual({row.name for row in rows if row.legacy}, expected)
        self.assertEqual(len(rows), len({row.name for row in rows}))
        self.assertTrue(all(row.phase in VERIFY.READY_PHASES for row in rows))
        # Every old check is selected for explicit ready, including flag- and pin-only rows.
        context = VERIFY.ReadyContext(ROOT, "v0.19.0", {}, {}, {}, [], True, True, "acceptance")
        selected = VERIFY.selected_ready_checks(context, flagged=True)
        self.assertEqual({row.name for row in selected if row.legacy}, expected)

    def test_receipt_audit_is_one_non_legacy_ga_candidate_check(self):
        rows = [row for row in VERIFY.READY_CHECKS if row.name == "receipt_audit"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.phase, "candidate")
        self.assertTrue(row.ga_only)
        self.assertFalse(row.legacy)
        self.assertIs(row.run, VERIFY.ready_receipt_audit)
        context = VERIFY.ReadyContext(ROOT, "v0.20.0", {}, {}, {}, [], True, True, "draft")
        for phase in VERIFY.READY_PHASES:
            with self.subTest(phase=phase):
                selected = VERIFY.selected_ready_checks(context._replace(through=phase), flagged=True)
                self.assertEqual(row in selected, phase != "draft")
        self.assertNotIn(row, VERIFY.selected_ready_checks(
            context._replace(release="v0.20.0-rc.1", through="candidate"), flagged=True))

    def test_link_row_defers_own_acceptance_only_before_acceptance_phase(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            release = "v0.20.0"
            atomic_write(root / "releases" / release / "notes.md",
                         "[Evidence](acceptance/future.json)\n")
            row = next(row for row in VERIFY.READY_CHECKS if row.name == "validate_markdown_links")
            for phase in VERIFY.READY_PHASES:
                errors = []
                context = VERIFY.ReadyContext(root, release, {}, {}, {}, [], False, False, phase)
                row.run(context, errors)
                self.assertEqual(bool(errors), phase == "acceptance", errors)


class LintDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.staged = Path(cls.temporary.name) / "staged"
        subprocess.run(["git", "clone", "--quiet", "--shared", str(ROOT), str(cls.staged)],
                       check=True, capture_output=True)
        shutil.copytree(ROOT / "scripts", cls.staged / "scripts", dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__"))
        cls.release = stage_successor(cls.staged)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "draft"
        shutil.copytree(self.staged, self.root, ignore=shutil.ignore_patterns("__pycache__"))

    def lint(self):
        result = subprocess.run([
            sys.executable, str(self.root / "scripts/verify_release.py"),
            "--release", self.release, "--lint-ready", "--check-pins", "--json",
        ], cwd=self.root, capture_output=True, text=True)
        self.assertIn(result.returncode, (0, 1), result.stdout + result.stderr)
        return result.returncode, json.loads(result.stdout)

    def assert_ready_refuses(self):
        result = subprocess.run([
            sys.executable, str(self.root / "scripts/verify_release.py"),
            "--release", self.release, "--require-ready", "--json",
        ], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_pristine_draft_passes_and_skips_acceptance(self):
        code, report = self.lint()
        self.assertEqual(code, 0, report)
        self.assertEqual(report["lint_phase"], "draft")
        expected = {row.name for row in VERIFY.READY_CHECKS if row.phase == "acceptance"}
        self.assertTrue(expected.issubset(set(report["skipped_checks"])), report)

    def test_acceptance_links_are_deferred_only_for_the_owning_release(self):
        release_root = self.root / "releases" / self.release
        notes = release_root / "NINFER_RELEASE_NOTES.md"
        # The real stager copies predecessor notes, including three not-yet-authored receipts.
        strict = subprocess.run([
            sys.executable, str(self.root / "scripts/verify_release.py"),
            "--release", self.release, "--require-ready", "--json",
        ], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(strict.returncode, 1)
        errors = json.loads(strict.stdout)["errors"]
        missing = [error for error in errors if f"releases/{self.release}/NINFER_RELEASE_NOTES.md"
                   in error and "has missing local link: acceptance/" in error]
        self.assertEqual(len(missing), 3, errors)
        original = notes.read_bytes()
        for source, target in (
            (notes, "missing-evidence.json"),
            (notes, "../v0.19.0/acceptance/missing-evidence.json"),
            (self.root / "docs/extra.md", f"../releases/{self.release}/acceptance/missing-evidence.json"),
        ):
            with self.subTest(source=source, target=target):
                atomic_write(source, original + f"\n[Evidence]({target})\n".encode())
                code, report = self.lint()
                self.assertEqual(code, 1, report)
                self.assertTrue(any(f"has missing local link: {target}" in error
                                    for error in report["errors"]), report)
                if source == notes:
                    atomic_write(source, original)
                else:
                    source.unlink()

    def test_available_checks_refuse_and_name_the_check(self):
        mutations = (
            ("compatibility.json", lambda doc: doc["runtime_contracts"][0].update(lane="stale lane"),
             "validate_exact_lane_set"),
            ("qualification.json", lambda doc: doc.update(interpretation="Acceptance is pending."),
             "validate_ready_state_consistency"),
            ("manifest.json", lambda doc: doc["publication"]["targets"].append(
                "Runtime v99.0.0-qwen38-5090-beta.99"), "validate_manifest_tag_prose"),
        )
        for filename, mutate, check in mutations:
            with self.subTest(check=check):
                path = self.root / "releases" / self.release / filename
                original = path.read_bytes()
                document = json.loads(original)
                mutate(document)
                atomic_write_json(path, document)
                code, report = self.lint()
                self.assertEqual(code, 1, report)
                self.assertTrue(any(f"[{check}]" in error for error in report["errors"]), report)
                self.assert_ready_refuses()
                atomic_write(path, original)
        notes = self.root / "releases" / self.release / "NINFER_RELEASE_NOTES.md"
        atomic_write(notes, notes.read_bytes() + b"\n__V9999_RESULT__\n")
        code, report = self.lint()
        self.assertEqual(code, 1, report)
        self.assertTrue(any("[validate_release_markdown_tokens]" in error
                            for error in report["errors"]), report)
        self.assert_ready_refuses()

    def test_draft_posture_requires_byte_exact_predecessor_authority(self):
        path = self.root / "compatibility.json"
        atomic_write(path, path.read_bytes() + b" ")
        code, report = self.lint()
        self.assertEqual(code, 1, report)
        self.assertTrue(any("draft posture" in error and "byte" in error
                            for error in report["errors"]), report)

    def test_candidate_lint_requires_the_audit_only_from_v0200(self):
        # The historical boundary is fixed even after the live root advances.
        source = HISTORY.resolve_commits("v0.19.0")[0]
        for release in ("v0.19.1", "v0.20.0"):
            with self.subTest(release=release), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "candidate"
                subprocess.run(["git", "clone", "--quiet", "--config", "core.autocrlf=false",
                                "--shared", "--no-checkout", str(ROOT), str(root)],
                               capture_output=True, check=True)
                subprocess.run(["git", "checkout", "--quiet", "--detach", source],
                               cwd=root, capture_output=True, check=True)
                shutil.copytree(ROOT / "scripts", root / "scripts", dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("__pycache__"))
                self.assertEqual(stage_successor(root, release=release), release)
                directory = root / "releases" / release
                manifest = VERIFY.load_json(directory / "manifest.json")
                statement = VERIFY.component_provenance(root, release, manifest)["statement"]

                def authored_prose(value):
                    if isinstance(value, dict):
                        return {key: authored_prose(child) for key, child in value.items()}
                    if isinstance(value, list):
                        return [authored_prose(child) for child in value]
                    if isinstance(value, str) and VERIFY.provenance_claim_errors(
                            value, "fixture", statement=statement):
                        return statement
                    return value

                for name in ("manifest.json", "compatibility.json", "qualification.json"):
                    document = authored_prose(VERIFY.load_json(directory / name))
                    if name == "compatibility.json":
                        # Candidate prose stays neutral; no acceptance flag is promoted.
                        document["composition"]["status"] = "candidate"
                    atomic_write_json(directory / name, document)
                atomic_write(directory / "NINFER_RELEASE_NOTES.md",
                             f"# OMP NInfer {release}\n\nQualification is limited to documented routes.\n")
                promoted = subprocess.run([
                    sys.executable, str(root / "scripts/rebind_release.py"), "--release", release,
                    "--pin", source, "--stage", "lane",
                ], cwd=root, capture_output=True, text=True)
                self.assertEqual(promoted.returncode, 0, promoted.stdout + promoted.stderr)
                audit = f"releases/{release}/qualification/receipt-audit.json"
                self.assertFalse((root / audit).exists())
                lint = subprocess.run([
                    sys.executable, str(root / "scripts/verify_release.py"),
                    "--release", release, "--lint-ready", "--json",
                ], cwd=root, capture_output=True, text=True)
                report = json.loads(lint.stdout)
                self.assertEqual(report["lint_phase"], "candidate")
                if release == "v0.20.0":
                    self.assertEqual(lint.returncode, 1, report)
                    self.assertEqual(report["errors"], [f"[receipt_audit] receipt audit: {audit} is required"])
                else:
                    self.assertEqual(lint.returncode, 0, report)
                    self.assertEqual(report["errors"], [])


if __name__ == "__main__":
    unittest.main()
