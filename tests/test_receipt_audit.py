"""Receipt inventories reproduce public history and refuse unadmitted retained bytes."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("receipt_audit", ROOT / "scripts" / "receipt_audit.py")
assert SPEC is not None and SPEC.loader is not None
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)

PREVIOUS = "v0.19.0"
RELEASE = "v0.20.0"
DATE = "2026-11-13"
AUDIT_PATH = f"releases/{RELEASE}/qualification/receipt-audit.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def run_git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", *args],
        cwd=root, check=True, capture_output=True, text=True,
    ).stdout.strip()


def commit(root: Path, message: str) -> str:
    run_git(root, "add", "releases")
    run_git(root, "commit", "--quiet", "-m", message)
    return run_git(root, "rev-parse", "HEAD")


class ReceiptAuditTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for release, status in ((PREVIOUS, "ready"), (RELEASE, "candidate")):
            prefix = f"releases/{release}/"
            self.save(prefix + "manifest.json", {
                "release": release, "status": status, "components": {"ninfer_variants": []},
            })
            self.save(prefix + "qualification.json", {
                "release": release, "evidence": {"same": True, "changed": release,
                                               "a/b~c": [None, "value"]},
            })
            self.save(prefix + "compatibility.json", {"release": release})
            self.put(prefix + "COMPATIBILITY.md", release.encode())
            self.put(prefix + "qualification/runtime-base.json", b'{"immutable": true}\n')
            self.put(prefix + "qualification/execution.json", release.encode())
        self.save(f"releases/{PREVIOUS}/qualification/receipt-audit.json", {})
        self.put(f"releases/{PREVIOUS}/qualification/dropped.json", b"old")
        self.put(f"releases/{RELEASE}/qualification/added.json", b"new")

    def put(self, path: str, data: bytes) -> None:
        AUDIT.atomic_write(self.root / path, data)

    def save(self, path: str, value: object) -> None:
        AUDIT.atomic_write_json(self.root / path, value)

    def load(self, path: str) -> dict:
        return json.loads((self.root / path).read_bytes())

    def generate(self, **kwargs) -> dict:
        return AUDIT.generate_audit(self.root, RELEASE, phase="lane-stage", as_of=DATE, **kwargs)

    def cli(self, *args: str) -> tuple[int, str]:
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            result = AUDIT.main(["--release", RELEASE, "--phase", "lane-stage", *args], root=self.root)
        return result, errors.getvalue()

    def initialize_history(self) -> str:
        run_git(self.root, "init", "--quiet")
        return commit(self.root, "fixture inputs")

    def add_carried_lane(self) -> None:
        lane = "native1-windows-native"
        qualification = {}
        for field, name in (
            ("summary", "qualification/native1.json"),
            ("release_spec", "profiles/native1/release-spec.json"),
            ("server_config", "profiles/native1/server-config.json"),
            ("quality_screen", "qualification/native1.quality-screen.json"),
            ("fit", "qualification/native1.fit.json"),
        ):
            data = json_bytes({"field": field, "original_subject": PREVIOUS})
            old_path = f"releases/{PREVIOUS}/{name}"
            self.put(old_path, data)
            if field == "summary":
                qualification["summary"] = old_path
                qualification["sha256"] = sha(data)
                qualification["public_url"] = (
                    "https://raw.githubusercontent.com/alphastorm/omp-ninfer/"
                    + "1" * 40 + "/" + old_path)
            else:
                qualification[field] = {"path": old_path, "sha256": sha(data)}
            if field in ("summary", "release_spec", "server_config"):
                self.put(f"releases/{RELEASE}/{name}", data)
        checksums = b"fixture component checksums\n"
        for release in (PREVIOUS, RELEASE):
            self.put(f"releases/{release}/qualification/{lane}.SHA256SUMS", checksums)
        row = {
            "id": lane, "release_tag": "v1.0.0-native1-beta.2", "source_commit": "a" * 40,
            "package_sha256": "b" * 64, "server_binary_sha256": "c" * 64,
            "configuration_sha256": "d" * 64, "model_artifact_sha256": "e" * 64,
            "maximum_context_tokens": 1024, "runtime_shape": {"engine": "native"},
            "checksums_sha256": sha(checksums), "qualification": qualification,
        }
        for release in (PREVIOUS, RELEASE):
            variant = copy.deepcopy(row)
            if release == RELEASE:
                q = variant["qualification"]
                q["summary"] = q["summary"].replace(f"/{PREVIOUS}/", f"/{RELEASE}/")
                q["public_url"] = q["public_url"].replace(f"/{PREVIOUS}/", f"/{RELEASE}/")
                for field in ("release_spec", "server_config"):
                    q[field]["path"] = q[field]["path"].replace(f"/{PREVIOUS}/", f"/{RELEASE}/")
            manifest_path = f"releases/{release}/manifest.json"
            manifest = self.load(manifest_path)
            manifest["components"]["ninfer_variants"] = [variant]
            self.save(manifest_path, manifest)

    def test_file_dispositions_and_scalar_pointer_hashes(self) -> None:
        audit = self.generate()
        rows = {row["file"]: row for row in audit["files"]}
        self.assertEqual(rows["qualification/runtime-base.json"]["disposition"], "kept")
        self.assertEqual(rows["qualification/execution.json"]["disposition"], "replaced")
        self.assertEqual(rows["qualification/dropped.json"]["disposition"], "dropped")
        self.assertEqual(rows["qualification/added.json"]["disposition"], "added")
        self.assertNotIn("staged_sha256", rows["qualification/receipt-audit.json"])
        self.assertEqual(list(rows), sorted(rows))
        bindings = {(row["file"], row["pointer"]): row for row in audit["bindings"]}
        row = bindings["qualification.json", "/evidence/a~1b~0c/0"]
        self.assertEqual(row["disposition"], "kept")
        self.assertEqual(row["staged_value_sha256"], sha(b"null"))

    def test_predecessor_is_latest_earlier_ready_ga_not_candidate_or_prerelease(self) -> None:
        for release, status in (("v0.18.0", "ready"), ("v0.19.8", "candidate"),
                                ("v0.19.9-rc.1", "ready"), ("v0.21.0", "ready")):
            self.save(f"releases/{release}/manifest.json", {"release": release, "status": status})
        self.assertEqual(self.generate()["source_release"], PREVIOUS)

    def test_generation_binds_audit_and_check_is_idempotent_without_writes(self) -> None:
        self.assertEqual(self.cli("--as-of", DATE), (0, ""))
        data = (self.root / AUDIT_PATH).read_bytes()
        qualification = self.load(f"releases/{RELEASE}/qualification.json")
        self.assertEqual(qualification["receipt_audit"],
                         {"repository_path": AUDIT_PATH, "sha256": sha(data)})
        self.assertFalse(any(row["pointer"].startswith("/receipt_audit")
                             for row in json.loads(data)["bindings"]))
        with mock.patch.object(AUDIT, "atomic_write") as write, \
                mock.patch.object(AUDIT, "atomic_write_json") as write_json:
            self.assertEqual(self.cli("--check"), (0, ""))
        write.assert_not_called()
        write_json.assert_not_called()
        self.assertEqual((self.root / AUDIT_PATH).read_bytes(), data)
        self.assertEqual(self.load(f"releases/{RELEASE}/qualification.json"), qualification)

    def test_check_refuses_tampered_audit_without_writing(self) -> None:
        self.assertEqual(self.cli("--as-of", DATE), (0, ""))
        audit = self.load(AUDIT_PATH)
        audit["files"][0]["reason"] = "altered"
        self.save(AUDIT_PATH, audit)
        before = (self.root / AUDIT_PATH).read_bytes()
        code, error = self.cli("--check")
        self.assertEqual(code, 1)
        self.assertIn("differs from recomputation", error)
        self.assertEqual((self.root / AUDIT_PATH).read_bytes(), before)

    def test_unadmitted_kept_file_refuses(self) -> None:
        for release in (PREVIOUS, RELEASE):
            self.put(f"releases/{release}/qualification/retained.json", b"same execution")
        with self.assertRaisesRegex(AUDIT.Refusal, "unadmitted predecessor bytes: qualification/retained"):
            self.generate()

    def test_carried_lane_is_detected_and_its_bound_files_are_kept_or_in_place(self) -> None:
        self.add_carried_lane()
        audit = self.generate()
        rows = {row["file"]: row for row in audit["files"]}
        for name in ("qualification/native1.json", "profiles/native1/release-spec.json",
                     "profiles/native1/server-config.json",
                     "qualification/native1-windows-native.SHA256SUMS"):
            self.assertEqual(rows[name]["disposition"], "kept")
            self.assertIn(f"unchanged since {PREVIOUS}", rows[name]["reason"])
        for name in ("qualification/native1.quality-screen.json", "qualification/native1.fit.json"):
            self.assertEqual(rows[name]["disposition"], "dropped")
            self.assertIn("bound in place", rows[name]["reason"])
        self.assertIn(f"byte-identical {PREVIOUS} row", audit["policy"])

    def test_carried_lane_with_different_file_refuses(self) -> None:
        self.add_carried_lane()
        self.put(f"releases/{RELEASE}/profiles/native1/server-config.json", b"changed")
        with self.assertRaisesRegex(AUDIT.Refusal, "carried file is not byte-identical"):
            self.generate()

    def test_carried_bindings_are_matched_by_field_not_object_order(self) -> None:
        self.add_carried_lane()
        expected = self.generate()
        path = f"releases/{RELEASE}/manifest.json"
        manifest = self.load(path)
        row = manifest["components"]["ninfer_variants"][0]
        row["qualification"] = dict(reversed(list(row["qualification"].items())))
        self.save(path, manifest)
        self.assertEqual(self.generate(), expected)

    def test_carried_summary_url_cannot_keep_the_predecessor_path_after_relocation(self) -> None:
        self.add_carried_lane()
        path = f"releases/{RELEASE}/manifest.json"
        manifest = self.load(path)
        qualification = manifest["components"]["ninfer_variants"][0]["qualification"]
        qualification["public_url"] = qualification["public_url"].replace(
            f"/{RELEASE}/", f"/{PREVIOUS}/")
        self.save(path, manifest)
        with self.assertRaisesRegex(AUDIT.Refusal, "carried summary URL"):
            self.generate()

    def test_carried_identity_does_not_allow_other_manifest_row_changes(self) -> None:
        self.add_carried_lane()
        path = f"releases/{RELEASE}/manifest.json"
        manifest = self.load(path)
        manifest["components"]["ninfer_variants"][0]["source_commit"] = "f" * 40
        self.save(path, manifest)
        with self.assertRaisesRegex(AUDIT.Refusal, "carried manifest row"):
            self.generate()

    def test_at_reads_committed_tree_not_working_inputs(self) -> None:
        expected = self.generate()
        inputs = self.initialize_history()
        self.put(f"releases/{RELEASE}/qualification/execution.json", b"uncommitted")
        self.assertEqual(self.generate(at=inputs), expected)
        self.assertNotEqual(self.generate(), expected)

    def test_ready_errors_presence_status_and_legacy_gate(self) -> None:
        self.assertTrue(AUDIT.ready_errors(self.root, RELEASE, phase="candidate", check_pins=False))
        self.assertEqual(AUDIT.ready_errors(self.root, PREVIOUS, phase="acceptance", check_pins=True), [])
        self.assertEqual(AUDIT.ready_errors(self.root, RELEASE, phase="draft", check_pins=True), [])
        self.assertEqual(self.cli("--as-of", DATE), (0, ""))
        self.assertEqual(AUDIT.ready_errors(self.root, RELEASE, phase="candidate", check_pins=False), [])
        self.assertIn("composed-final", AUDIT.ready_errors(
            self.root, RELEASE, phase="acceptance", check_pins=False)[0])
        audit = self.load(AUDIT_PATH)
        audit["status"] = "invalid"
        self.save(AUDIT_PATH, audit)
        self.assertTrue(AUDIT.ready_errors(self.root, RELEASE, phase="candidate", check_pins=False))

    def test_ready_pin_check_uses_last_audit_commit_and_refuses_tampering(self) -> None:
        self.initialize_history()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(AUDIT.main(["--release", RELEASE, "--phase", "composed-final",
                                         "--as-of", DATE], root=self.root), 0)
        audit_commit = commit(self.root, "fixture audit")
        path = f"releases/{RELEASE}/manifest.json"
        manifest = self.load(path)
        manifest["later_pin"] = "immutable URL metadata"
        self.save(path, manifest)
        commit(self.root, "fixture later pin")
        self.assertEqual(AUDIT.ready_errors(self.root, RELEASE, phase="acceptance", check_pins=True), [])
        self.assertEqual(run_git(self.root, "log", "-1", "--format=%H", "--", AUDIT_PATH), audit_commit)
        audit = self.load(AUDIT_PATH)
        audit["bindings"][0]["staged_value_sha256"] = "0" * 64
        self.save(AUDIT_PATH, audit)
        self.assertIn("recomputation mismatch", AUDIT.ready_errors(
            self.root, RELEASE, phase="acceptance", check_pins=True)[0])
        commit(self.root, "fixture altered audit")
        self.assertIn("recomputation mismatch", AUDIT.ready_errors(
            self.root, RELEASE, phase="acceptance", check_pins=True)[0])

    def test_pin_check_refuses_absent_uncommitted_and_shallow_history(self) -> None:
        self.assertEqual(self.cli("--as-of", DATE), (0, ""))
        self.assertTrue(AUDIT.ready_errors(self.root, RELEASE, phase="candidate", check_pins=True))
        run_git(self.root, "init", "--quiet")
        self.assertIn("committed git history", AUDIT.ready_errors(
            self.root, RELEASE, phase="candidate", check_pins=True)[0])
        commit(self.root, "fixture audit")
        with tempfile.TemporaryDirectory() as temporary:
            clone = Path(temporary) / "clone"
            subprocess.run(["git", "clone", "--quiet", "--depth=1", self.root.as_uri(), str(clone)],
                           check=True, capture_output=True)
            self.assertIn("complete git history", AUDIT.ready_errors(
                clone, RELEASE, phase="candidate", check_pins=True)[0])


class PublicHistoryGoldenTest(unittest.TestCase):
    COMMITS = {
        "stage": "bf2a0591f5cef458a1999179e832a04abe511a4a",
        "compose": "7062952768b7ac2ec6831e20471dea9df73e5a7d",
        "acceptance": "0bc70da9bd5bf4e0cc5542a1939953d19d0997a3",
        "audit": "143a9bc3401416460dd450071797cdf9727de9e6",
        "notes": "d6d1dcfe46fa0572d8463345f327a3fef6b85ca4",
    }
    PREFIX = "releases/v0.19.0/"

    @classmethod
    def setUpClass(cls) -> None:
        try:
            if run_git(ROOT, "rev-parse", "--is-shallow-repository") != "false":
                raise ValueError("public-history goldens require a non-shallow clone")
            cls.commits = {name: run_git(ROOT, "rev-parse", "--verify", ref + "^{commit}")
                           for name, ref in cls.COMMITS.items()}
        except (ValueError, subprocess.CalledProcessError) as error:
            if os.environ.get("OMP_NINFER_REQUIRE_HISTORY") == "1":
                raise AssertionError("required public audit history is unavailable") from error
            raise unittest.SkipTest("public audit history is unavailable") from error

    def blob(self, commit: str, name: str) -> bytes:
        return subprocess.run(["git", "show", f"{commit}:{self.PREFIX}{name}"], cwd=ROOT,
                              check=True, capture_output=True).stdout

    def assert_audit_bytes(self, actual: dict, expected: bytes) -> None:
        legacy = (b"no fresh hardware qualification, bounded pressure saves or "
                  b"new-client/product-route acceptance is claimed.")
        neutral = (b"no fresh hardware qualification or "
                   b"new-client/product-route acceptance is claimed.")
        published = json.loads(expected)
        carried_reasons = [row["reason"] for row in published["files"]
                           if row["disposition"] == "kept"
                           and row["reason"].startswith("Carried component, unchanged since ")]
        self.assertGreater(len(carried_reasons), 0)
        self.assertTrue(all(reason.count(legacy.decode()) == 1 for reason in carried_reasons))
        self.assertEqual(expected.count(legacy), len(carried_reasons))
        expected = expected.replace(legacy, neutral)
        data = json_bytes(actual)
        self.assertNotIn(legacy, data)
        if data == expected:
            return
        wanted = json.loads(expected)
        for key in wanted.keys() | actual.keys():
            if wanted.get(key) == actual.get(key):
                continue
            if key in ("files", "bindings"):
                old, new = wanted.get(key, []), actual.get(key, [])
                for index in range(max(len(old), len(new))):
                    before = old[index] if index < len(old) else None
                    after = new[index] if index < len(new) else None
                    if before != after:
                        self.fail(f"first differing {key}[{index}]: expected {before!r}; got {after!r}")
            self.fail(f"first differing field {key}: expected {wanted.get(key)!r}; got {actual.get(key)!r}")
        self.fail("audit values match but serialized bytes differ")

    def test_composed_final_from_acceptance_parent_is_byte_exact(self) -> None:
        inputs = self.commits["acceptance"]
        self.assertEqual(run_git(ROOT, "rev-parse", self.commits["audit"] + "^"), inputs)
        self.assert_audit_bytes(AUDIT.generate_audit(
            ROOT, "v0.19.0", phase="composed-final", as_of=DATE, at=inputs),
            self.blob(self.commits["audit"], "qualification/receipt-audit.json"))

    def test_notes_audit_differs_and_is_byte_exact_from_its_own_parent(self) -> None:
        earlier = self.blob(self.commits["audit"], "qualification/receipt-audit.json")
        later = self.blob(self.commits["notes"], "qualification/receipt-audit.json")
        self.assertNotEqual(earlier, later)
        inputs = run_git(ROOT, "rev-parse", self.commits["notes"] + "^")
        self.assert_audit_bytes(AUDIT.generate_audit(
            ROOT, "v0.19.0", phase="composed-final", as_of=DATE, at=inputs), later)

    def intermediate_inputs(self, commit: str, root: Path) -> None:
        """Undo the audit edge and ensuing summary rebind, not the other staged edits."""
        archive = subprocess.run(
            ["git", "archive", commit, "--", "releases/v0.18.0", "releases/v0.19.0"],
            cwd=ROOT, check=True, capture_output=True,
        ).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as contents:
            for entry in contents:
                if entry.isfile():
                    path = root / entry.name
                    self.assertTrue(path.resolve().is_relative_to(root.resolve()))
                    stream = contents.extractfile(entry)
                    assert stream is not None
                    AUDIT.atomic_write(path, stream.read())
        parent = run_git(ROOT, "rev-parse", commit + "^")
        previous_qualification = json.loads(self.blob(parent, "qualification.json"))
        qualification = json.loads(self.blob(commit, "qualification.json"))
        qualification["receipt_audit"] = previous_qualification["receipt_audit"]
        manifest = json.loads(self.blob(commit, "manifest.json"))
        manifest["qualification"]["summary_sha256"] = sha(json_bytes(qualification))
        AUDIT.atomic_write_json(root / self.PREFIX / "qualification.json", qualification)
        AUDIT.atomic_write_json(root / self.PREFIX / "manifest.json", manifest)

    def test_stage_intermediate_input_tree_is_byte_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.intermediate_inputs(self.commits["stage"], root)
            self.assert_audit_bytes(AUDIT.generate_audit(
                root, "v0.19.0", phase="lane-stage", as_of=DATE),
                self.blob(self.commits["stage"], "qualification/receipt-audit.json"))

    def test_compose_intermediate_input_tree_is_byte_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.intermediate_inputs(self.commits["compose"], root)
            self.assert_audit_bytes(AUDIT.generate_audit(
                root, "v0.19.0", phase="composed-final", as_of=DATE),
                self.blob(self.commits["compose"], "qualification/receipt-audit.json"))


if __name__ == "__main__":
    unittest.main()
