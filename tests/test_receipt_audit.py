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
import sys
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


def stage_carry_all(root: Path) -> subprocess.CompletedProcess[str]:
    subprocess.run(["git", "clone", "--quiet", "--local", "--no-hardlinks", str(ROOT), str(root)],
                   check=True, capture_output=True)
    for key, value in (("user.name", "fixture"), ("user.email", "fixture@example.invalid"),
                       ("commit.gpgsign", "false"), ("core.autocrlf", "false")):
        run_git(root, "config", key, value)
    run_git(root, "remote", "remove", "origin")
    # Run the same plan/stage path as rehearsal, not a second set of stager flags.
    code = """
import argparse
import importlib.util
import json
from pathlib import Path

root = Path.cwd()
spec = importlib.util.spec_from_file_location("receipt_audit_driver", root / "scripts/release.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
previous = driver.latest_ready_manifest(root)
major, minor, _ = map(int, previous["release"][1:].split("."))
minor += 1
while (root / "releases" / f"v{major}.{minor}.0").exists():
    minor += 1
release = f"v{major}.{minor}.0"
driver.init_plan(root, release)
notes = root / ".release-state" / "receipt-audit" / "stage-notes.md"
driver.atomic_write(notes, f"# {release}\\n\\nSynthetic host-free audit fixture.\\n"
                    "Runtime and native component identities are retained; no new execution is claimed.\\n")
predecessor = previous["release"]
qualification = driver.read_json(root / "releases" / predecessor / "qualification.json")
candidate = driver.ReleaseDriver(root, release, argparse.Namespace(
    command="candidate", notes=notes, as_of=qualification["as_of"],
    client_component=root / "releases" / predecessor / "qualification/client-components.json"))
driver.run_pipeline(candidate, finalize=False, no_suite=True, through="stage")
print(json.dumps({"release": release, "predecessor": predecessor}))
"""
    return subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True)


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
        result, _, errors = self.invoke(*args)
        return result, errors

    def invoke(self, *args: str) -> tuple[int, str, str]:
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            result = AUDIT.main(["--release", RELEASE, "--phase", "lane-stage", *args], root=self.root)
        return result, output.getvalue(), errors.getvalue()

    def snapshot(self) -> dict[str, bytes]:
        return {path.relative_to(self.root).as_posix(): path.read_bytes()
                for path in (self.root / "releases").rglob("*") if path.is_file()}

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

    def add_carried_runtime(self) -> None:
        row = {"release_tag": "v1.0.0-engine-beta.2", "source_commit": "0" * 40,
               "server_binary_sha256": "1" * 64, "oci_manifest_digest": "sha256:" + "2" * 64}
        for release in (PREVIOUS, RELEASE):
            prefix = f"releases/{release}/"
            manifest = self.load(prefix + "manifest.json")
            manifest["components"]["ninfer"] = row
            self.save(prefix + "manifest.json", manifest)
            qualification = self.load(prefix + "qualification.json")
            composition = qualification.setdefault("composition", {})
            data = json_bytes({"source_commit": row["source_commit"], "original_subject": PREVIOUS})
            self.put(prefix + "qualification/runtime-lane.json", data)
            composition["behavioral_qualification"] = {
                "repository_path": prefix + "qualification/runtime-lane.json", "sha256": sha(data)}
            base = prefix + "qualification/runtime-base.json"
            composition["local_release_packaging"] = {
                "runtime_base_receipt": {"repository_path": base,
                                         "sha256": sha((self.root / base).read_bytes())}}
            self.save(prefix + "qualification.json", qualification)

    def recut_native(self) -> None:
        path = f"releases/{RELEASE}/manifest.json"
        manifest = self.load(path)
        native = manifest["components"]["ninfer_variants"][0]
        native.update(release_tag="v1.0.1-native1-beta.1", source_commit="f" * 40,
                      package_sha256="9" * 64)
        qualification = native["qualification"]
        for field, reference in list(qualification.items()):
            if field == "summary":
                target = reference
            elif isinstance(reference, dict):
                target = reference["path"].replace(f"/{PREVIOUS}/", f"/{RELEASE}/")
                reference["path"] = target
            else:
                continue
            data = json_bytes({"recut_source": native["source_commit"], "field": field})
            self.put(target, data)
            if field == "summary":
                qualification["sha256"] = sha(data)
            else:
                reference["sha256"] = sha(data)
        checksums = b"recut native checksums\n"
        self.put(f"releases/{RELEASE}/qualification/{native['id']}.SHA256SUMS", checksums)
        native["checksums_sha256"] = sha(checksums)
        self.save(path, manifest)

    def add_reference_chain(self) -> list[str]:
        children = {
            "qualification/runtime-rc.json": json_bytes({"result": "previous subject"}),
            "qualification/slow-first-request-parity-waiver-class.json": json_bytes({"decision": "previous subject"}),
        }
        parent = "qualification/unbound-parent.json"
        files = {**children, parent: json_bytes({
            "receipts": [{"path": Path(name).name, "sha256": sha(data)} for name, data in children.items()],
        })}
        for release in (PREVIOUS, RELEASE):
            for name, data in files.items():
                self.put(f"releases/{release}/{name}", data)
        return sorted(files)

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

    def test_all_unadmitted_kept_files_are_reported_sorted_without_writes(self) -> None:
        names = ["qualification/z-retained.json", "qualification/a-retained.json"]
        for release in (PREVIOUS, RELEASE):
            for name in names:
                self.put(f"releases/{release}/{name}", name.encode())
        with mock.patch.object(AUDIT, "atomic_write") as write, \
                mock.patch.object(AUDIT, "atomic_write_json") as write_json:
            self.assertEqual(AUDIT.unadmitted_kept(self.root, RELEASE), sorted(names))
        write.assert_not_called()
        write_json.assert_not_called()
        with self.assertRaises(AUDIT.Refusal) as refused:
            self.generate()
        self.assertEqual(str(refused.exception),
                         "unadmitted predecessor bytes: " + ", ".join(sorted(names)))

    def test_byte_identical_predecessor_release_notes_refuse(self) -> None:
        for release in (PREVIOUS, RELEASE):
            self.put(f"releases/{release}/NINFER_RELEASE_NOTES.md", b"# Unchanged release notes\n")
        self.assertEqual(AUDIT.unadmitted_kept(self.root, RELEASE), ["NINFER_RELEASE_NOTES.md"])
        with self.assertRaisesRegex(AUDIT.Refusal, "NINFER_RELEASE_NOTES.md"):
            self.generate()

    def test_prune_preserves_unedited_notes_and_every_other_copy_on_refusal(self) -> None:
        for release in (PREVIOUS, RELEASE):
            self.put(f"releases/{release}/NINFER_RELEASE_NOTES.md", b"# Previous release\n")
            self.put(f"releases/{release}/qualification/unbound.json", b'{"subject": "previous"}\n')
        before = self.snapshot()
        code, output, error = self.invoke("--prune-unbound", "--as-of", DATE)
        self.assertEqual(code, 1)
        self.assertIn("NINFER_RELEASE_NOTES.md", error)
        self.assertEqual(output, "")
        self.assertEqual(self.snapshot(), before)

    def test_prune_refuses_references_from_all_three_release_authorities(self) -> None:
        name = "qualification/unbound.json"
        data = b'{"subject": "previous"}\n'
        for release in (PREVIOUS, RELEASE):
            self.put(f"releases/{release}/{name}", data)
        prefix = f"releases/{RELEASE}/"
        references = (
            prefix + name,
            "./" + name + "#evidence",
            "https://raw.githubusercontent.com/alphastorm/omp-ninfer/" + "a" * 40 + "/" + prefix + name,
            "The retained file is `" + prefix + name + "`.",
        )
        for document in ("manifest.json", "qualification.json", "compatibility.json"):
            path = prefix + document
            original = self.load(path)
            for reference in references:
                with self.subTest(document=document, reference=reference):
                    value = copy.deepcopy(original)
                    value["extra"] = {"repository_path": reference, "sha256": sha(data)}
                    self.save(path, value)
                    before = self.snapshot()
                    code, output, error = self.invoke("--prune-unbound", "--as-of", DATE)
                    self.assertEqual(code, 1)
                    self.assertIn(prefix + name, error)
                    self.assertIn(path + "#/extra/repository_path", error)
                    self.assertEqual(output, "")
                    self.assertEqual(self.snapshot(), before)
            self.save(path, original)

    def test_prune_flag_refuses_check_at_and_composed_final_without_effects(self) -> None:
        for release in (PREVIOUS, RELEASE):
            self.put(f"releases/{release}/qualification/unbound.json", b'{"subject": "previous"}\n')
        before = self.snapshot()
        for args in (("--check",), ("--at", "HEAD"), ("--phase", "composed-final")):
            with self.subTest(args=args):
                code, output, error = self.invoke("--prune-unbound", *args)
                self.assertEqual(code, 1)
                self.assertIn("--prune-unbound requires lane-stage without --check or --at", error)
                self.assertEqual(output, "")
                self.assertEqual(self.snapshot(), before)

    def test_prune_refuses_markdown_links_and_plain_mentions_without_deleting_anything(self) -> None:
        name = "qualification/unbound.json"
        for release in (PREVIOUS, RELEASE):
            self.put(f"releases/{release}/{name}", b'{"subject": "previous"}\n')
            self.put(f"releases/{release}/qualification/also-unbound.json", b'{}\n')
        prefix = f"releases/{RELEASE}/"
        for document, reference in (
            ("NINFER_RELEASE_NOTES.md", f"[Retained receipt]({name})"),
            ("NINFER_RELEASE_NOTES.md", f"[Retained receipt](./{name}#evidence)"),
            ("NINFER_RELEASE_NOTES.md", f"Retained receipt: `{prefix}{name}`"),
            ("NINFER_RELEASE_NOTES.md", f"Retained receipt: {name}"),
            ("NINFER_RELEASE_NOTES.md", f"//[draft] Retained receipt: {name}"),
            ("review/notes.md", f"[Retained receipt](../{name})"),
            ("review/notes.md", "[Retained receipt](https://raw.githubusercontent.com/alphastorm/"
                                "omp-ninfer/" + "a" * 40 + "/" + prefix + name + ")"),
        ):
            with self.subTest(document=document, reference=reference):
                path = prefix + document
                self.put(path, ("# New release evidence\n\n" + reference + "\n").encode("utf-8"))
                before = self.snapshot()
                code, output, error = self.invoke("--prune-unbound", "--as-of", DATE)
                self.assertEqual(code, 1)
                self.assertIn(prefix + name, error)
                self.assertIn(path, error)
                self.assertEqual(output, "")
                self.assertEqual(self.snapshot(), before)
                (self.root / path).unlink()

    def test_late_audit_planning_refusal_does_not_delete_copies(self) -> None:
        for release in (PREVIOUS, RELEASE):
            self.put(f"releases/{release}/qualification/unbound.json", b'{"subject": "previous"}\n')
        before = self.snapshot()
        code, output, error = self.invoke("--prune-unbound", "--as-of", "not-a-date")
        self.assertEqual(code, 1)
        self.assertIn("as_of must be an ISO date", error)
        self.assertEqual(output, "")
        self.assertEqual(self.snapshot(), before)

    def test_prune_recut_lane_predecessor_only_copy_and_empty_directories(self) -> None:
        self.add_carried_runtime()
        self.add_carried_lane()
        self.recut_native()
        name = "qualification/obsolete/only/previous-result.json"
        for release in (PREVIOUS, RELEASE):
            self.put(f"releases/{release}/{name}", b'{"subject": "previous native component"}\n')
        self.assertEqual(AUDIT.unadmitted_kept(self.root, RELEASE), [name])
        code, output, error = self.invoke("--prune-unbound", "--as-of", DATE)
        self.assertEqual((code, error), (0, ""))
        self.assertFalse((self.root / "releases" / RELEASE / "qualification/obsolete").exists())
        self.assertTrue((self.root / "releases" / PREVIOUS / name).is_file())
        audit = self.load(AUDIT_PATH)
        row = next(row for row in audit["files"] if row["file"] == name)
        self.assertEqual(row["disposition"], "dropped")
        self.assertEqual(row["reason"],
                         "Predecessor evidence is not a current successor result, waiver or review approval.")
        self.assertIn(f"pruned releases/{RELEASE}/{name}: {row['reason']}", output.splitlines())
        self.assertEqual(self.cli("--check"), (0, ""))

    def test_unrooted_parent_and_both_children_are_unadmitted_and_pruned_in_one_pass(self) -> None:
        names = self.add_reference_chain()
        self.assertEqual(AUDIT.unadmitted_kept(self.root, RELEASE), names)
        with self.assertRaises(AUDIT.Refusal) as refused:
            self.generate()
        self.assertEqual(str(refused.exception), "unadmitted predecessor bytes: " + ", ".join(names))
        code, output, error = self.invoke("--prune-unbound", "--as-of", DATE)
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(AUDIT.unadmitted_kept(self.root, RELEASE), [])
        audit = self.load(AUDIT_PATH)
        rows = {row["file"]: row for row in audit["files"]}
        self.assertEqual(len([line for line in output.splitlines() if line.startswith("pruned ")]), 3)
        for name in names:
            self.assertFalse((self.root / "releases" / RELEASE / name).exists())
            self.assertEqual(rows[name]["disposition"], "dropped")
            self.assertIn(f"pruned releases/{RELEASE}/{name}: {rows[name]['reason']}", output.splitlines())
        self.assertEqual(self.cli("--check"), (0, ""))

    def test_unchanged_row_roots_admission_of_a_complete_reference_chain(self) -> None:
        names = self.add_reference_chain()
        parent = "qualification/unbound-parent.json"
        digest = sha((self.root / "releases" / PREVIOUS / parent).read_bytes())
        for release in (PREVIOUS, RELEASE):
            path = f"releases/{release}/manifest.json"
            manifest = self.load(path)
            manifest["components"]["retained"] = {
                "release_tag": "v1.0.0", "source_commit": "b" * 40,
                "qualification": {"path": parent, "sha256": digest},
            }
            self.save(path, manifest)
        self.assertEqual(AUDIT.unadmitted_kept(self.root, RELEASE), [])
        rows = {row["file"]: row for row in self.generate()["files"]}
        for name in names:
            self.assertEqual(rows[name]["disposition"], "kept")
            self.assertIn("v1.0.0 (source bbbbbbbb)", rows[name]["reason"])

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

    def test_runtime_is_carried_in_a_mixed_release_with_a_recut_native(self) -> None:
        self.add_carried_runtime()
        self.add_carried_lane()
        self.recut_native()
        audit = self.generate()
        rows = {row["file"]: row for row in audit["files"]}
        self.assertEqual(AUDIT.unadmitted_kept(self.root, RELEASE), [])
        self.assertEqual(rows["qualification/runtime-lane.json"]["disposition"], "kept")
        self.assertIn("v1.0.0-engine-beta.2 (source 00000000)",
                      rows["qualification/runtime-lane.json"]["reason"])
        self.assertEqual(rows["qualification/native1.json"]["disposition"], "replaced")
        self.assertNotIn("The carried NATIVE", audit["policy"])
        self.assertIn("The carried ninfer v1.0.0-engine-beta.2", audit["policy"])

    def test_carried_runtime_file_must_remain_byte_identical(self) -> None:
        self.add_carried_runtime()
        self.put(f"releases/{RELEASE}/qualification/runtime-lane.json", b"changed")
        with self.assertRaisesRegex(AUDIT.Refusal, "carried file is not byte-identical"):
            self.generate()

    def test_runtime_row_change_does_not_admit_its_kept_receipt(self) -> None:
        self.add_carried_runtime()
        path = f"releases/{RELEASE}/manifest.json"
        manifest = self.load(path)
        manifest["components"]["ninfer"]["server_binary_sha256"] = "9" * 64
        self.save(path, manifest)
        self.assertEqual(AUDIT.unadmitted_kept(self.root, RELEASE), ["qualification/runtime-lane.json"])
        with self.assertRaisesRegex(AUDIT.Refusal, "qualification/runtime-lane.json"):
            self.generate()

    def test_other_unchanged_component_admits_only_its_exact_bound_files(self) -> None:
        for release in (PREVIOUS, RELEASE):
            prefix = f"releases/{release}/"
            path = prefix + "qualification/model.json"
            data = b'{"revision": "original"}\n'
            self.put(path, data)
            manifest = self.load(prefix + "manifest.json")
            manifest["components"]["model"] = {
                "revision": "a" * 40, "qualification": {"repository_path": path, "sha256": sha(data)}}
            self.save(prefix + "manifest.json", manifest)
        rows = {row["file"]: row for row in self.generate()["files"]}
        self.assertEqual(rows["qualification/model.json"]["disposition"], "kept")
        self.assertIn("source aaaaaaaa", rows["qualification/model.json"]["reason"])
        path = f"releases/{RELEASE}/manifest.json"
        manifest = self.load(path)
        manifest["components"]["model"]["revision"] = "b" * 40
        self.save(path, manifest)
        self.assertIn("qualification/model.json", AUDIT.unadmitted_kept(self.root, RELEASE))

    def test_other_component_bound_only_in_place_does_not_claim_local_kept_files(self) -> None:
        path = f"releases/{PREVIOUS}/qualification/model.json"
        data = b'{"revision": "original"}\n'
        self.put(path, data)
        for release in (PREVIOUS, RELEASE):
            manifest_path = f"releases/{release}/manifest.json"
            manifest = self.load(manifest_path)
            manifest["components"]["model"] = {
                "revision": "a" * 40, "qualification": {"repository_path": path, "sha256": sha(data)}}
            self.save(manifest_path, manifest)
        audit = self.generate()
        row = next(row for row in audit["files"] if row["file"] == "qualification/model.json")
        self.assertEqual(row["disposition"], "dropped")
        self.assertIn("bound in place", row["reason"])
        self.assertIn("row and qualification bound in place.", audit["policy"])

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

    def test_ready_pin_check_does_not_detect_later_unhashed_notes_changes(self) -> None:
        for release in (PREVIOUS, RELEASE):
            self.put(f"releases/{release}/NINFER_RELEASE_NOTES.md", release.encode())
        self.initialize_history()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(AUDIT.main(["--release", RELEASE, "--phase", "composed-final",
                                         "--as-of", DATE], root=self.root), 0)
        commit(self.root, "fixture audit")
        self.put(f"releases/{RELEASE}/NINFER_RELEASE_NOTES.md", b"# Later authored notes\n")
        commit(self.root, "fixture later notes")
        self.assertEqual(AUDIT.ready_errors(self.root, RELEASE, phase="acceptance", check_pins=True), [])

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


class StagedCarryAllTest(unittest.TestCase):
    def test_staged_carry_all_audits_with_logged_pruning_and_then_checks_without_effects(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "copy"
            staged = stage_carry_all(root)
            self.assertEqual(staged.returncode, 0, staged.stdout + staged.stderr)
            identities = json.loads(staged.stdout.splitlines()[-1])
            release, predecessor = identities["release"], identities["predecessor"]
            version = tuple(map(int, release[1:].split(".")))
            previous_version = tuple(map(int, predecessor[1:].split(".")))
            self.assertGreaterEqual(version, (0, 20, 0))
            self.assertEqual(version[0], previous_version[0])
            self.assertGreater(version[1], previous_version[1])
            self.assertEqual(version[2], 0)
            prefix = root / "releases" / release
            before = root / "releases" / predecessor
            plan = json.loads((prefix / "plan.json").read_bytes())
            self.assertEqual(plan["predecessor"], predecessor)
            self.assertTrue(all(row["disposition"] == "carried" for row in plan["components"]))
            previous_manifest = json.loads((before / "manifest.json").read_bytes())
            manifest = json.loads((prefix / "manifest.json").read_bytes())
            self.assertEqual(manifest["components"]["ninfer"], previous_manifest["components"]["ninfer"])
            self.assertEqual(AUDIT.unadmitted_kept(root, release), [])
            snapshot = {path.relative_to(prefix).as_posix(): path.read_bytes()
                        for path in prefix.rglob("*") if path.is_file()}
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(AUDIT.main(["--release", release, "--phase", "lane-stage",
                                             "--check"], root=root), 0)
            self.assertEqual(snapshot, {path.relative_to(prefix).as_posix(): path.read_bytes()
                                        for path in prefix.rglob("*") if path.is_file()})
            audit = json.loads((prefix / "qualification/receipt-audit.json").read_bytes())
            self.assertEqual(audit["status"], "lane-stage")
            self.assertEqual(audit["source_release"], predecessor)
            rows = {row["file"]: row for row in audit["files"]}
            for row in rows.values():
                if row["disposition"] == "kept":
                    self.assertTrue(row["reason"].startswith("Carried component, unchanged since "))
            log_prefix = f"pruned releases/{release}/"
            pruned = [line for line in staged.stdout.splitlines() if line.startswith(log_prefix)]
            for line in pruned:
                name = line.removeprefix(log_prefix).split(": ", 1)[0]
                self.assertEqual(rows[name]["disposition"], "dropped")
                self.assertEqual(line, log_prefix + name + ": " + rows[name]["reason"])
            self.assertEqual(len(pruned), len(set(pruned)))
            in_place = []
            old_prefix = f"releases/{predecessor}/"
            for variant in manifest["components"]["ninfer_variants"]:
                for reference in variant["qualification"].values():
                    if isinstance(reference, dict) and reference.get("path", "").startswith(old_prefix):
                        name = reference["path"].removeprefix(old_prefix)
                        if (before / name).is_file():
                            in_place.append(name)
            # A newer ready predecessor may already have removed every in-place
            # copy; the isolated carry fixtures always exercise that disposition.
            for name in in_place:
                self.assertEqual(rows[name]["disposition"], "dropped")
                self.assertIn("bound in place at " + old_prefix + name, rows[name]["reason"])
            qualification = json.loads((before / "qualification.json").read_bytes())
            ledger = qualification["observed_gates"]["g4_review"]["repository_path"].removeprefix(old_prefix)
            self.assertEqual(rows[ledger]["disposition"], "dropped")
            self.assertEqual(rows[ledger]["reason"],
                             "Predecessor evidence is not a current successor result, waiver or review approval.")
            runtime_receipt = json.loads((prefix / "qualification.json").read_bytes())[
                "composition"]["behavioral_qualification"]["repository_path"]
            row = rows[runtime_receipt.removeprefix(f"releases/{release}/")]
            runtime = manifest["components"]["ninfer"]
            self.assertIn(runtime["release_tag"] + " (source " + runtime["source_commit"][:8] + ")", row["reason"])


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
