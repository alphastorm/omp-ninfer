"""Prove component-cut sequencing with sealed synthetic bundles and recording tools."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


FIXTURES = load_module("release_cut_bundle_fixtures", ROOT / "tests/test_qualification_bundle.py")
DRIVER = load_module("release_cut_driver", ROOT / "scripts/release.py")
from release_io import atomic_copy, atomic_write, atomic_write_json
from release_plan import initial_plan

STUB = r'''import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from release_io import atomic_write, atomic_write_json

private = Path(os.environ["CUT_PRIVATE"])
control_path = private / "control.json"
control = json.loads(control_path.read_text())
records_path = private / "commands.json"
records = json.loads(records_path.read_text()) if records_path.exists() else []

def record(tool, arguments):
    records.append({"tool": tool, "arguments": arguments,
                    "runtime_dir": os.environ.get("NINFER_RUNTIME_DIR")})
    if tool == "cut":
        directory = Path(arguments[arguments.index("--assets") + 1])
        records[-1]["asset_sha256"] = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in directory.iterdir() if path.is_file()}
    atomic_write_json(records_path, records)

def value(arguments, flag):
    return arguments[arguments.index(flag) + 1]

def cut():
    arguments = sys.argv[1:]
    record("cut", arguments)
    if "--dry-run" in arguments:
        if control.get("existing"):
            tag = value(arguments, "--version") + "-qwen38-" + value(arguments, "--lane")[3:]
            tag += "-beta." + value(arguments, "--beta")
            print("tag already exists: " + tag, file=sys.stderr)
            return 1
        if control.get("dry_failure"):
            print("dry-run failure", file=sys.stderr)
            return 7
        if control.get("mutate_authorization"):
            atomic_write(private / "authorization.txt", "changed authorization\n")
        print("dry run: no tag, release, or upload was created")
        return 0
    if control.get("publish_failure"):
        print("publication failed", file=sys.stderr)
        return 8
    control["existing"] = True
    atomic_write_json(control_path, control)
    return 0

def publication(contract):
    arguments = sys.argv[1:]
    record("publication", arguments)
    plan = json.loads(Path(value(arguments, "--plan")).read_text())
    lane = value(arguments, "--lane")
    assets = {}
    for index, argument in enumerate(arguments):
        if argument == "--asset":
            role, path = arguments[index + 1].split("=", 1)
            assets[role] = Path(path)
    release, bundle = contract.load_bundle(plan, lane, Path(value(arguments, "--bundle")),
                                           contract.Inputs(), assets)
    if control.get("bad_publication"):
        print("native publication refused: differs from bundle SHA-256: package: "
              "public 'sha256:" + "0" * 64 + "', bundle 'sha256:" +
              bundle.row["package_sha256"] + "'", file=sys.stderr)
        return 1
    out = Path(value(arguments, "--out"))
    if "--check" in arguments:
        if not out.is_file():
            print("native publication refused: existing record is missing", file=sys.stderr)
            return 1
    else:
        atomic_write_json(out, {
            "artifact_type": "omp_ninfer_native_component_publication", "schema_version": 1,
            "release": release, "status": "passed",
            "lanes": [{"lane": lane, "component_tag": bundle.row["release_tag"],
                       "source_commit": bundle.row["source_commit"], "published": True}],
            "product_publication_authorized": False})
    print(json.dumps({"schema": 1, "lane": lane, "status": "checked" if "--check" in arguments else "authenticated"}))
    return 0
'''

PUBLICATION = r'''import importlib.util
import sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("cut_publication_contract", Path(__file__).with_name("native_publication_contract.py"))
assert spec is not None and spec.loader is not None
contract = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = contract
spec.loader.exec_module(contract)
load_bundle = contract.load_bundle

class NoPublicTransport:
    def __init__(self, *args, **kwargs):
        raise AssertionError("recording tests must never use the real public transport")

contract.HTTPTransport = NoPublicTransport
if __name__ == "__main__":
    from cut_stub import publication
    raise SystemExit(publication(contract))
'''

def _git_output(root, environment, *arguments):
    return subprocess.run(["git", *arguments], cwd=root, env=environment, check=True,
                          capture_output=True, text=True, encoding="utf-8").stdout.strip()


class ReleaseCutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.prepared.cleanup)
        base = Path(cls.prepared.name)
        root, private = (base / "repository").resolve(), (base / "private").resolve()
        root.mkdir()
        private.mkdir()
        cls.prepared_bundle = FIXTURES.SyntheticBundle(root)
        bundle = cls.prepared_bundle
        receipt_path = bundle.assets / "package-build-receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["upstream_base_sha"] = json.loads(
            (bundle.directory / "rtx3090.json").read_text(encoding="utf-8"))["identity"]["upstream_base_sha"]
        atomic_write_json(receipt_path, receipt)
        bundle.reseal_assets()
        cls.release = bundle.release
        shutil.copytree(ROOT / "scripts", root / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        atomic_copy(ROOT / "compatibility.json", root / "compatibility.json")
        authorization = private / "authorization.txt"
        atomic_write(authorization, "authorize the planned native component cut\n")
        atomic_write(private / "notes.md", "# Native component\n\nThe planned component cut.\n")
        plan = initial_plan(root, cls.release)
        row = next(row for row in plan["components"] if row["id"] == "rtx3090-windows-native")
        row.update(disposition="recut", release_tag=bundle.row["release_tag"],
                   source_commit=bundle.row["source_commit"])
        plan["decisions"] = [*copy.deepcopy(bundle.plan["decisions"]),
                              {"kind": "component-cut", "id": "cut-rtx3090",
                               "sha256": DRIVER.file_sha(authorization)}]
        atomic_write_json(root / "releases" / cls.release / "plan.json", plan)
        atomic_write_json(root / "releases" / plan["predecessor"] /
                          "qualification/client-components.json", {})
        atomic_write(root / ".gitignore", ".release-state/\nbundle/\n")
        scripts = root / "scripts"
        atomic_copy(scripts / "native_publication.py", scripts / "native_publication_contract.py")
        atomic_write(scripts / "native_publication.py", PUBLICATION)
        atomic_write(scripts / "cut_stub.py", STUB + '\nif __name__ == "__main__":\n    raise SystemExit(cut())\n')
        atomic_write(scripts / "hosts/cut-ninfer-4090-component.sh",
                     '#!/usr/bin/env bash\nexec "$CUT_PYTHON" "$(dirname "$0")/../cut_stub.py" "$@"\n')
        cls.prepared_root, cls.prepared_private = root, private
        cls.environment = {**os.environ, "CUT_PYTHON": sys.executable, "PYTHONIOENCODING": "utf-8",
                           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                           "GIT_AUTHOR_NAME": "Release Test", "GIT_COMMITTER_NAME": "Release Test",
                           "GIT_AUTHOR_EMAIL": "release@example.com", "GIT_COMMITTER_EMAIL": "release@example.com"}
        for arguments in (("init", "-q"), ("config", "core.autocrlf", "false"), ("add", "--all"),
                          ("commit", "-qm", "test(release): commit the component cut plan")):
            _git_output(root, cls.environment, *arguments)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.root, self.private = (base / "repository").resolve(), (base / "private").resolve()
        self.private.mkdir()
        self.environment = {**type(self).environment, "CUT_PRIVATE": str(self.private)}
        _git_output(base, self.environment, "clone", "-q", "--shared", "--config", "core.autocrlf=false",
                    str(self.prepared_root), str(self.root))
        self.bundle = copy.deepcopy(self.prepared_bundle)
        self.bundle.root = self.root
        self.bundle.directory = self.root / "bundle"
        self.bundle.assets = self.bundle.directory / "assets"
        for path in self.prepared_bundle.directory.rglob("*"):
            if path.is_file():
                atomic_copy(path, self.bundle.directory / path.relative_to(self.prepared_bundle.directory))
        for path in self.prepared_private.iterdir():
            atomic_copy(path, self.private / path.name)
        self.authorization = self.private / "authorization.txt"
        self.notes = self.private / "notes.md"
        self.runtime = self.private / "engine"
        self.runtime.mkdir()
        self.plan_path = self.root / "releases" / self.release / "plan.json"
        self.plan = json.loads(self.plan_path.read_text(encoding="utf-8"))
        atomic_write_json(self.private / "control.json", {})
        self.head = self.git("rev-parse", "HEAD")

    def git(self, *arguments):
        return _git_output(self.root, self.environment, *arguments)

    def command(self, *arguments, success=True):
        result = subprocess.run([sys.executable, "scripts/release.py", *arguments,
                                 "--release", self.release], cwd=self.root, env=self.environment,
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0 if success else 1, result.stdout + result.stderr)
        return result

    def cut(self, *arguments, success=True):
        return self.command("cut", "--lane", "rtx3090", "--bundle", str(self.bundle.directory),
                            "--runtime-dir", str(self.runtime), "--notes-file", str(self.notes),
                            *arguments, success=success)

    def control(self, **values):
        path = self.private / "control.json"
        current = json.loads(path.read_text(encoding="utf-8"))
        current.update(values)
        atomic_write_json(path, current)

    def calls(self):
        path = self.private / "commands.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

    def state(self):
        return json.loads((self.root / ".release-state" / (self.release + ".json")).read_text(encoding="utf-8"))

    def commit_plan(self):
        atomic_write_json(self.plan_path, self.plan)
        self.git("add", "--", self.plan_path.relative_to(self.root).as_posix())
        self.git("commit", "-qm", "test(release): change the component cut plan")
        self.head = self.git("rev-parse", "HEAD")

    def test_default_is_only_dry_run_with_derived_arguments_and_private_state(self):
        result = self.cut()
        self.assertIn("cut-rtx3090", result.stdout)
        self.assertIn("--publish", result.stdout)
        self.assertIn(DRIVER.file_sha(self.authorization), result.stdout)
        calls = self.calls()
        self.assertEqual([row["tool"] for row in calls], ["cut"])
        arguments = calls[0]["arguments"]
        expected = ["--lane", "rtx3090", "--version", "v0.8.0", "--beta", "4",
                    "--commit", "15c3e3959c0a6167f799e9383482ec4e03db9cad",
                    "--assets", str(self.bundle.assets.resolve()), "--checksums-sha",
                    self.bundle.row["checksums_sha256"], "--notes-file", str(self.notes.resolve()), "--dry-run"]
        self.assertEqual(arguments, expected)
        self.assertEqual(calls[0]["runtime_dir"], str(self.runtime.resolve()))
        self.assertNotIn("native_publications", self.state()["private"])
        self.assertNotIn(str(self.private), self.plan_path.read_text(encoding="utf-8"))
        self.assertEqual(self.git("rev-parse", "HEAD"), self.head)

    def test_authorized_publish_runs_dry_then_publish_then_authenticates(self):
        self.cut("--publish", "--authorization", str(self.authorization))
        calls = self.calls()
        self.assertEqual([row["tool"] for row in calls], ["cut", "cut", "publication"])
        self.assertEqual(calls[0]["arguments"][-1], "--dry-run")
        self.assertEqual(calls[1]["arguments"], [*calls[0]["arguments"][:-1], "--publish"])
        publication = calls[2]["arguments"]
        self.assertNotIn("--check", publication)
        out = Path(publication[publication.index("--out") + 1])
        self.assertEqual(out.parent, self.root / ".release-state" / self.release)
        self.assertEqual(self.state()["private"]["native_publications"]["rtx3090"], str(out))
        self.assertEqual(self.state()["private"]["bundles"]["rtx3090"], str(self.bundle.directory.resolve()))
        DRIVER.ReleaseDriver(self.root, self.release).validate_stage_inputs()
        self.assertEqual(self.git("rev-parse", "HEAD"), self.head)

    def test_publish_requires_the_lane_grant_before_any_effect(self):
        for arguments in (("--publish",), ("--publish", "--authorization", str(self.notes))):
            with self.subTest(arguments=arguments):
                result = self.cut(*arguments, success=False)
                self.assertIn("authorization", result.stderr)
                self.assertEqual(self.calls(), [])
                self.assertFalse((self.root / ".release-state").exists())
        self.plan["decisions"] = [row for row in self.plan["decisions"] if row["kind"] != "component-cut"]
        self.commit_plan()
        result = self.cut("--publish", "--authorization", str(self.authorization), success=False)
        self.assertIn("cut-rtx3090", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_carried_lane_refuses_without_tools_or_state(self):
        previous = json.loads((self.root / "releases" / self.plan["predecessor"] / "manifest.json").read_text(encoding="utf-8"))
        carried = next(row for row in previous["components"]["ninfer_variants"]
                       if row["id"] == "rtx3090-windows-native")
        row = next(row for row in self.plan["components"] if row["id"] == carried["id"])
        row.update(disposition="carried", **{key: carried[key] for key in ("release_tag", "source_commit")})
        self.commit_plan()
        result = self.cut(success=False)
        self.assertIn("carried", result.stderr)
        self.assertIn("rtx3090", result.stderr)
        self.assertEqual(self.calls(), [])
        self.assertFalse((self.root / ".release-state").exists())

    def test_uncommitted_plan_refuses(self):
        self.plan["limitations"].append("Only documented routes are qualified.")
        atomic_write_json(self.plan_path, self.plan)
        result = self.cut("--publish", "--authorization", str(self.authorization), success=False)
        self.assertIn("plan commit", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_bundle_mismatch_prevents_even_dry_run(self):
        path = self.bundle.assets / self.bundle.row["package_name"]
        atomic_write(path, b"different archive")
        result = self.cut("--publish", "--authorization", str(self.authorization), success=False)
        self.assertIn("SHA-256 mismatch", result.stderr)
        self.assertEqual(self.calls(), [])
        self.assertFalse((self.root / ".release-state").exists())

    def test_dry_run_failure_never_publishes_or_saves_inputs(self):
        self.control(dry_failure=True)
        result = self.cut("--publish", "--authorization", str(self.authorization), success=False)
        self.assertIn("dry-run failure", result.stderr)
        self.assertEqual([row["tool"] for row in self.calls()], ["cut"])
        self.assertFalse((self.root / ".release-state" / (self.release + ".json")).exists())

    def test_authorization_is_rechecked_after_dry_run(self):
        self.control(mutate_authorization=True)
        result = self.cut("--publish", "--authorization", str(self.authorization), success=False)
        self.assertIn("authorization", result.stderr)
        self.assertEqual([row["tool"] for row in self.calls()], ["cut"])
        self.assertFalse((self.root / ".release-state" / (self.release + ".json")).exists())

    def test_failed_publication_never_authenticates_or_records(self):
        self.control(publish_failure=True)
        result = self.cut("--publish", "--authorization", str(self.authorization), success=False)
        self.assertIn("publication failed", result.stderr)
        self.assertEqual([row["tool"] for row in self.calls()], ["cut", "cut"])
        self.assertFalse((self.root / ".release-state" / (self.release + ".json")).exists())

    def test_existing_public_tag_is_authenticated_without_republishing(self):
        self.control(existing=True)
        self.cut("--publish", "--authorization", str(self.authorization))
        self.cut("--publish", "--authorization", str(self.authorization))
        self.assertEqual([row["tool"] for row in self.calls()], ["cut", "publication", "cut", "publication"])
        self.assertNotIn("--check", self.calls()[1]["arguments"])
        self.assertIn("--check", self.calls()[3]["arguments"])
        self.assertTrue(Path(self.state()["private"]["native_publications"]["rtx3090"]).is_file())

    def test_authenticated_publish_rerun_never_publishes_twice(self):
        self.cut("--publish", "--authorization", str(self.authorization))
        self.cut("--publish", "--authorization", str(self.authorization))
        modes = [row["arguments"][-1] for row in self.calls() if row["tool"] == "cut"]
        self.assertEqual(modes.count("--publish"), 1)
        self.assertEqual(modes.count("--dry-run"), 2)
        self.assertIn("--check", self.calls()[-1]["arguments"])

    def test_differing_public_bytes_names_both_digests_and_records_nothing(self):
        self.control(existing=True, bad_publication=True)
        result = self.cut("--publish", "--authorization", str(self.authorization), success=False)
        self.assertIn("0" * 64, result.stderr)
        self.assertIn(self.bundle.row["package_sha256"], result.stderr)
        self.assertEqual([row["tool"] for row in self.calls()], ["cut", "publication"])
        self.assertFalse((self.root / ".release-state" / (self.release + ".json")).exists())
        self.assertEqual(list((self.root / ".release-state" / self.release).glob("*.json")), [])

    def test_failed_reauthentication_preserves_the_prior_record_and_state(self):
        self.cut("--publish", "--authorization", str(self.authorization))
        state_path = self.root / ".release-state" / (self.release + ".json")
        record = Path(self.state()["private"]["native_publications"]["rtx3090"])
        before = (state_path.read_bytes(), record.read_bytes())
        self.control(bad_publication=True)
        self.cut(success=False)
        self.assertEqual((state_path.read_bytes(), record.read_bytes()), before)
        self.assertEqual(sum("--publish" in row["arguments"] for row in self.calls()), 1)

    def test_status_and_next_report_pending_without_tool_calls(self):
        pending = self.command("status")
        self.assertIn("cut-rtx3090\tpending", pending.stdout)
        self.assertIn("cut", self.command("next").stdout)
        self.assertEqual(self.calls(), [])

    def test_status_and_next_report_recorded_without_network_or_tool_calls(self):
        self.cut("--publish", "--authorization", str(self.authorization))
        self.control(bad_publication=True)
        count = len(self.calls())
        self.assertIn("cut-rtx3090\trecorded", self.command("status").stdout)
        next_step = self.command("next")
        self.assertIn("native_publication.py", next_step.stdout)
        self.assertIn("--check", next_step.stdout)
        self.assertIn("re-reads public bytes", next_step.stdout)
        self.assertEqual(len(self.calls()), count)

    def test_external_package_is_streamed_to_a_closed_nonaliasing_asset_directory(self):
        package = self.bundle.assets / self.bundle.row["package_name"]
        external = self.private / package.name
        atomic_copy(package, external)
        package.unlink()
        self.bundle.reference["inputs"].append({
            "role": "rtx3090-package", "external": True, "name": package.name,
            "sha256": self.bundle.row["package_sha256"], "bytes": external.stat().st_size})
        self.bundle.reseal()
        self.cut("--asset", "rtx3090-package=" + str(external))
        arguments = self.calls()[0]["arguments"]
        materialized = Path(arguments[arguments.index("--assets") + 1])
        self.assertNotEqual(materialized, self.bundle.assets)
        self.assertFalse(materialized.exists())
        self.assertEqual(external.read_bytes(), b"synthetic archive")
        expected = {path.name: DRIVER.file_sha(path) for path in self.bundle.assets.iterdir()}
        expected[package.name] = self.bundle.row["package_sha256"]
        self.assertEqual(self.calls()[0]["asset_sha256"], expected)
        self.assertEqual(self.state()["private"]["assets"]["rtx3090-package"], str(external.resolve()))


class RecordedCutVectorTests(unittest.TestCase):
    def test_historical_public_argv_differs_only_in_private_locations(self):
        manifest = json.loads((ROOT / "releases/v0.19.0/manifest.json").read_text(encoding="utf-8"))
        row = next(row for row in manifest["components"]["ninfer_variants"]
                   if row["id"] == "rtx3090-windows-native")
        component = {key: row[key] for key in ("id", "release_tag", "source_commit")}
        assets, notes = Path("cut-assets").resolve(), Path("component-notes.md").resolve()
        expected = ["--lane", "rtx3090", "--version", "v0.8.0", "--beta", "4",
                    "--commit", "15c3e3959c0a6167f799e9383482ec4e03db9cad", "--assets", str(assets),
                    "--checksums-sha", "d1bce21e6d22fb38b1530937f4fa7ea76c706243ea339058f7c46b84885aec22",
                    "--notes-file", str(notes), "--dry-run"]
        self.assertEqual(DRIVER._native_cut_arguments(component, assets, row["checksums_sha256"], notes), expected)
        self.assertEqual(DRIVER._native_cut_arguments(component, assets, row["checksums_sha256"], notes,
                                                      publish=True), [*expected[:-1], "--publish"])


if __name__ == "__main__":
    unittest.main()
