"""Exercise release commits and interrupted groups in disposable, host-free repositories."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from tests.test_release_plan import PREDECESSOR, RELEASE, plan_fixture

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_driver_test", ROOT / "scripts" / "release.py")
assert SPEC is not None and SPEC.loader is not None
DRIVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER)
from release_io import atomic_write, atomic_write_json

TOOLS = ("stage_release.py", "aggregate_qualification.py", "bind_native_variant.py",
         "rebind_release.py", "receipt_audit.py", "retarget_guide.py", "verify_release.py",
         "collect_route_evidence.py", "review_ledger.py", "compose_route_acceptance.py", "run_tests.py")

# These tools implement only their public command contracts. No sibling implementation is needed.
SUPPORT = r'''
import copy
import json
import re
import sys
from pathlib import Path
from release_io import atomic_write, atomic_write_json

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKERS = ("nonpublic-fixture-marker",)
ROUTES = ("rtx5090-container-host", "rtx5090-macos-client", "rtx5090-windows-client",
          "rtx4090-native", "rtx3090-native")

def predecessor_manifest(root, release):
    version = lambda name: tuple(map(int, name[1:].split(".")))
    rows = [json.loads(path.read_text(encoding="utf-8")) for path in (root / "releases").glob("*/manifest.json")
            if re.fullmatch(r"v\d+\.\d+\.\d+", path.parent.name) and version(path.parent.name) < version(release)]
    return max((row for row in rows if row.get("status") == "ready"),
               key=lambda row: version(row["release"]), default=None)

def unchanged_native_variant(row, previous):
    return previous is not None and all(row.get(key) == previous.get(key) for key in (
        "release_tag", "source_commit", "package_sha256", "server_binary_sha256",
        "configuration_sha256", "model_artifact_sha256", "maximum_context_tokens", "runtime_shape"))

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def run(name, args):
    def value(flag, default=None):
        return args[args.index(flag) + 1] if flag in args else default
    def values(flag):
        return [args[index + 1] for index, item in enumerate(args) if item == flag]
    local = ROOT / ".release-state"
    trace = local / "invocations.json"
    invocations = load(trace) if trace.exists() else []
    invocations.append({"tool": name, "arguments": args})
    atomic_write_json(trace, invocations)
    fail = load(local / "fail.json") if (local / "fail.json").exists() else {}
    failure = fail.get("tool") == name and (not fail.get("phase") or value("--phase") == fail["phase"])
    release = value("--release", value("--to"))
    directory = ROOT / "releases" / release if release else None
    manifest = directory / "manifest.json" if directory else None
    qualification = directory / "qualification.json" if directory else None
    authority = directory / "compatibility.json" if directory else None
    if name == "stage_release.py":
        assert not directory.exists(), "stager requires an absent directory"
        prior = load(ROOT / "releases" / value("--from") / "manifest.json")
        prior.update(release=release, status="draft")
        runtime = prior["components"]["ninfer"]
        for key, flag in (("release_tag", "--release-tag"), ("source_commit", "--source-commit"),
                          ("server_binary_sha256", "--binary-sha"), ("binary_archive_sha256", "--archive-sha"),
                          ("source_archive_sha256", "--source-archive-sha"), ("sbom_sha256", "--sbom-sha"),
                          ("oci_manifest_digest", "--image-digest"), ("runtime_receipt_release", "--runtime-receipt-release")):
            assert value(flag) is not None, flag
            runtime[key] = value(flag)
        if value("--omp-component"):
            prior["components"]["omp"] = load(Path(value("--omp-component")))["omp"]
        atomic_write_json(manifest, prior)
        atomic_write_json(qualification, {"as_of": "2026-01-02", "status": "draft"})
        current = load(ROOT / "compatibility.json")
        current["product_release"] = release
        atomic_write_json(authority, current)
        atomic_write(directory / "COMPATIBILITY.md", "matrix\n")
        atomic_write(directory / "NINFER_RELEASE_NOTES.md", "# " + release + "\n")
    elif name == "aggregate_qualification.py":
        plan = load(ROOT / value("--plan"))
        expected = {row["id"].split("-")[0] for row in plan["components"]
                    if row["disposition"] == "recut" and row["id"].endswith("windows-native")}
        bundles = {item.partition("=")[0]: Path(item.partition("=")[2]) for item in values("--bundle")}
        assert set(bundles) == expected
        if args[0] == "admit":
            lanes = {lane: {"binder_arguments": ["--release", release, "--lane", lane, "--tag",
                      next(row["release_tag"] for row in plan["components"] if row["id"].startswith(lane)),
                      "--receipt", str(path / "receipt.json")]} for lane, path in bundles.items()}
            override = local / "admit-output.json"
            print(json.dumps(load(override) if override.exists() else {"schema": 1, "lanes": lanes}))
        else:
            assert args[0] == "compose"
            recut = plan["components"][0]["disposition"] == "recut"
            assert (value("--runtime-publication") is not None) == recut
            assert {item.partition("=")[0] for item in values("--native-publication")} == expected
            document = load(qualification)
            document["aggregate"] = "passed"
            atomic_write_json(qualification, document)
    elif name == "bind_native_variant.py":
        document = load(manifest)
        variant = next(row for row in document["components"]["ninfer_variants"] if row["id"].startswith(value("--lane")))
        variant.update(load(Path(value("--receipt"))))
        variant["release_tag"] = value("--tag")
        atomic_write_json(manifest, document)
    elif name == "rebind_release.py":
        document = load(manifest)
        stage = value("--stage", "draft" if "--draft" in args else "chain")
        if stage == "lane":
            document["status"] = "candidate"
            atomic_write_json(ROOT / "compatibility.json", load(authority))
            atomic_write(ROOT / "docs" / "COMPATIBILITY.md", "matrix " + release + "\n")
        document["last_rebind"] = stage
        if value("--pin"):
            document[stage + "_pin"] = value("--pin")
        atomic_write_json(manifest, document)
    elif name == "receipt_audit.py":
        atomic_write_json(directory / "qualification" / "receipt-audit.json", {"status": value("--phase")})
        document = load(qualification)
        document["audit_phase"] = value("--phase")
        atomic_write_json(qualification, document)
    elif name == "retarget_guide.py":
        guide = ROOT / "docs" / "QUICKSTART.md"
        atomic_write(guide, guide.read_text(encoding="utf-8").replace(value("--from"), value("--to")))
    elif name == "collect_route_evidence.py":
        assert Path(value("--window-root")).is_dir()
        assert load(ROOT / value("--plan"))["release"] == release
        atomic_write_json(Path(value("--output")), {"candidate": value("--candidate")})
        for lane in ROUTES:
            atomic_write_json(Path(value("--receipts-dir")) / (lane + "-run.json"),
                              {"candidate": value("--candidate"), "lane": lane})
    elif name == "review_ledger.py":
        assert Path(value("--reviews")).is_dir()
        candidate = load(Path(value("--values"))).get("candidate_override", value("--candidate"))
        atomic_write_json(directory / "review" / "runtime-ledger.json", {"product_tooling": {"stage_commit": candidate}})
    elif name == "compose_route_acceptance.py":
        assert load(Path(value("--evidence")))["candidate"] == value("--candidate")
        assert set(item.partition("=")[0] for item in values("--route")) == set(ROUTES)
        for item in values("--route"):
            assert load(Path(item.partition("=")[2]))["candidate"] == value("--candidate")
        for filename in ("composed-external-installation.json", "documented-routes.json"):
            atomic_write_json(directory / "acceptance" / filename, {"candidate": value("--candidate")})
        atomic_write_json(ROOT / "docs" / "measurements" / (value("--measurement-prefix") + "-routes.json"),
                          {"candidate": value("--candidate")})
        document = load(manifest)
        document["status"] = "ready"
        atomic_write_json(manifest, document)
    elif name == "publish":
        assert "--publish" not in args and value("--pr") and value("--commit")
    elif name not in ("verify_release.py", "run_tests.py"):
        raise AssertionError(name)
    if failure:
        raise SystemExit(7)

if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2:])
'''


class ReleaseDriverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.root = base / "product"
        self.root.mkdir()
        self.private = base / "inputs"
        self.private.mkdir()
        self.environment = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                            "GIT_AUTHOR_NAME": "Release fixture", "GIT_COMMITTER_NAME": "Release fixture",
                            "GIT_AUTHOR_EMAIL": "release@example.invalid",
                            "GIT_COMMITTER_EMAIL": "release@example.invalid"}
        self.plan, self.previous, self.authority = plan_fixture(self.root)
        for name in ("release.py", "release_plan.py", "release_io.py"):
            atomic_write(self.root / "scripts" / name, (ROOT / "scripts" / name).read_bytes())
        atomic_write(self.root / "scripts" / "stub_support.py", SUPPORT)
        for name in TOOLS:
            source = ("from stub_support import PRIVATE_MARKERS, predecessor_manifest, unchanged_native_variant, run\n"
                      "import sys\n"
                      f"if __name__ == '__main__': run({name!r}, sys.argv[1:])\n")
            atomic_write(self.root / "scripts" / name, source)
        atomic_write(self.root / ".gitignore", ".release-state/\n__pycache__/\n")
        atomic_write(self.root / "docs" / "QUICKSTART.md", "# Guide\n" + PREDECESSOR + "\n")
        atomic_write_json(self.private / "values.json", {})
        (self.private / "windows").mkdir()
        (self.private / "reviews").mkdir()
        atomic_write(self.private / "notes.md", "# " + RELEASE + "\nRelease scope.\n")
        self.git("init", "-q")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "user.name", "Release fixture")
        self.git("config", "user.email", "release@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.git("config", "core.filemode", "false")
        self.git("add", "--", ".")
        self.git("commit", "-qm", "test(release): seed disposable release inputs")
        self.initial = self.git("rev-parse", "HEAD")

    def git(self, *arguments: str) -> str:
        return subprocess.run(["git", *arguments], cwd=self.root, env=self.environment,
                              check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()

    def invoke(self, command: str, *arguments: str, success: bool = True) -> subprocess.CompletedProcess:
        result = subprocess.run([sys.executable, str(self.root / "scripts" / "release.py"), command,
                                 "--release", RELEASE, *map(str, arguments)],
                                cwd=self.root, env=self.environment, capture_output=True,
                                text=True, encoding="utf-8")
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def candidate(self, *arguments: str) -> None:
        self.invoke("candidate", "--notes", str(self.private / "notes.md"), *arguments)

    def finalize(self, *arguments: str, success: bool = True) -> subprocess.CompletedProcess:
        return self.invoke("finalize", "--window-root", str(self.private / "windows"),
                           "--reviews", str(self.private / "reviews"), "--values", str(self.private / "values.json"),
                           "--as-of", "2026-01-02", *arguments, success=success)

    def calls(self, name: str | None = None) -> list[dict]:
        path = self.root / ".release-state" / "invocations.json"
        calls = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        return [call for call in calls if name is None or call["tool"] == name]

    def worktree_bytes(self) -> dict[str, bytes]:
        listed = self.git("ls-files", "-z", "--cached", "--others", "--exclude-standard")
        return {name: (self.root / name).read_bytes() for name in listed.split("\0") if name}

    def driver(self, **values) -> Any:
        options = argparse.Namespace(**{"notes": self.private / "notes.md", **values})
        return DRIVER.ReleaseDriver(self.root, RELEASE, options)

    def interrupt(self, *, finalize: bool = False, **values) -> None:
        driver = self.driver(**values)
        with mock.patch.object(driver, "commit", side_effect=DRIVER.ReleaseError("interrupted before commit")):
            with self.assertRaisesRegex(DRIVER.ReleaseError, "interrupted before commit"):
                DRIVER.run_pipeline(driver, finalize=finalize, no_suite=True)

    def test_full_candidate_finalize_order_subjects_and_trailers(self) -> None:
        self.candidate()
        self.finalize()
        records = DRIVER.group_commits(self.root, RELEASE)
        self.assertEqual(list(records), ["stage", "lane-pin", "guide", "compose", "platform-pin",
                                         "acceptance-pin", "audit", "manifest-pin"])
        subjects = self.git("log", "--reverse", "--format=%s", f"{self.initial}..HEAD").splitlines()
        self.assertEqual(subjects, [
            f"chore(release): stage {RELEASE} lane receipts",
            f"chore(release): pin {RELEASE} lane receipts",
            f"docs(quickstart): retarget guide to {RELEASE}",
            f"chore(release): compose {RELEASE} acceptance",
            f"chore(release): pin {RELEASE} platform receipts",
            f"chore(release): pin {RELEASE} composed acceptance",
            f"chore(release): audit {RELEASE} receipts",
            f"chore(release): pin {RELEASE} manifest evidence",
        ])
        for group, record in records.items():
            body = self.git("show", "-s", "--format=%B", record["commit"])
            self.assertIn("Release: " + RELEASE, body)
            self.assertIn("Release-Step: " + group, body)
        for call in self.calls("rebind_release.py"):
            args = call["arguments"]
            if "--pin" in args:
                stage = args[args.index("--stage") + 1]
                source = {"lane": "stage", "platform": "compose", "acceptance": "platform-pin", "manifest": "audit"}[stage]
                self.assertEqual(args[args.index("--pin") + 1], records[source]["commit"])
                self.assertEqual(records[stage + "-pin"]["pins"], records[source]["commit"])
        self.assertEqual(len(self.calls("run_tests.py")), 2)
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertNotIn(str(self.private), self.git("log", "--format=%B", f"{self.initial}..HEAD"))

    def test_finalize_notes_are_committed_by_compose(self) -> None:
        self.candidate("--no-suite")
        notes = self.private / "accepted-notes.md"
        content = f"# {RELEASE}\nDocumented acceptance passed.\n".encode()
        atomic_write(notes, content)
        self.finalize("--no-suite", "--notes", str(notes))
        compose = DRIVER.group_commits(self.root, RELEASE)["compose"]["commit"]
        path = f"releases/{RELEASE}/NINFER_RELEASE_NOTES.md"
        committed = subprocess.run(["git", "show", f"{compose}:{path}"], cwd=self.root,
                                   env=self.environment, check=True, capture_output=True).stdout
        self.assertEqual(committed, content)
        self.assertEqual((self.root / path).read_bytes(), content)

    def test_finalize_without_notes_keeps_staged_notes(self) -> None:
        self.candidate("--no-suite")
        path = self.root / "releases" / RELEASE / "NINFER_RELEASE_NOTES.md"
        staged = path.read_bytes()
        atomic_write(self.private / "notes.md", "Do not reread this stage-only input.\n")
        self.finalize("--no-suite")
        compose = DRIVER.group_commits(self.root, RELEASE)["compose"]["commit"]
        committed = subprocess.run(["git", "show", f"{compose}:{path.relative_to(self.root).as_posix()}"],
                                   cwd=self.root, env=self.environment, check=True, capture_output=True).stdout
        self.assertEqual(committed, staged)
        self.assertEqual(path.read_bytes(), staged)

    def test_changed_finalize_notes_rerun_interrupted_compose(self) -> None:
        self.candidate("--no-suite")
        notes = self.private / "accepted-notes.md"
        atomic_write(notes, f"# {RELEASE}\nInitial acceptance summary.\n")
        self.interrupt(finalize=True, command="finalize", notes=notes,
                       window_root=self.private / "windows", reviews=self.private / "reviews",
                       values=self.private / "values.json", as_of="2026-01-02")
        content = f"# {RELEASE}\nFinal acceptance summary.\n".encode()
        atomic_write(notes, content)
        self.finalize("--no-suite")
        self.assertEqual(len(self.calls("collect_route_evidence.py")), 2)
        self.assertEqual((self.root / "releases" / RELEASE / "NINFER_RELEASE_NOTES.md").read_bytes(), content)

    def test_completed_groups_create_no_more_commits_or_tool_calls(self) -> None:
        self.candidate("--no-suite")
        self.finalize("--no-suite")
        head = self.git("rev-parse", "HEAD")
        before = [call for call in self.calls() if call["tool"] != "verify_release.py"]
        self.invoke("candidate", "--no-suite")
        self.invoke("finalize", "--no-suite")
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assertEqual([call for call in self.calls() if call["tool"] != "verify_release.py"], before)
        self.assertEqual(len(self.calls("run_tests.py")), 0)
        self.assertTrue(any("--lint-ready" in call["arguments"] for call in self.calls("verify_release.py")))
        self.assertTrue(any("--require-ready" in call["arguments"] for call in self.calls("verify_release.py")))

    def test_interrupted_unchanged_group_is_commit_only(self) -> None:
        self.interrupt()
        self.assertEqual(self.git("rev-parse", "HEAD"), self.initial)
        self.candidate("--no-suite")
        self.assertEqual(len(self.calls("stage_release.py")), 1)
        self.assertEqual(len(DRIVER.group_commits(self.root, RELEASE)), 3)

    def test_changed_private_input_restores_and_reruns_group(self) -> None:
        self.interrupt()
        orphan = self.root / "releases" / RELEASE / "qualification" / "orphan.json"
        atomic_write_json(orphan, {"uncommitted": True})
        atomic_write(self.private / "notes.md", "# " + RELEASE + "\nChanged scope.\n")
        self.candidate("--no-suite")
        self.assertEqual(len(self.calls("stage_release.py")), 2)
        self.assertFalse(orphan.exists())
        self.assertIn("Changed scope.", (self.root / "releases" / RELEASE / "NINFER_RELEASE_NOTES.md").read_text())

    def test_changed_plan_restores_stale_outputs_before_revalidation(self) -> None:
        self.interrupt()
        self.plan["platforms"]["darwin-remote-ssh"] = "qualified"
        atomic_write_json(self.root / "releases" / RELEASE / "plan.json", self.plan)
        self.candidate("--no-suite")
        self.assertEqual(len(self.calls("stage_release.py")), 2)

    def test_missing_output_reruns_instead_of_committing_partial_tree(self) -> None:
        self.interrupt()
        (self.root / "releases" / RELEASE / "qualification" / "receipt-audit.json").unlink()
        self.candidate("--no-suite")
        self.assertEqual(len(self.calls("stage_release.py")), 2)

    def test_tool_failure_leaves_no_partial_commit_and_retry_succeeds(self) -> None:
        failure = self.root / ".release-state" / "fail.json"
        atomic_write_json(failure, {"tool": "stage_release.py"})
        result = self.invoke("candidate", "--no-suite", success=False)
        self.assertIn("stage_release.py failed (exit 7)", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.initial)
        self.assertEqual(DRIVER.group_commits(self.root, RELEASE), {})
        failure.unlink()
        self.candidate("--no-suite")
        self.assertEqual(len(self.calls("stage_release.py")), 2)

    def test_foreign_dirty_path_is_refused_without_touching_it(self) -> None:
        path = self.root / "foreign name.txt"
        atomic_write(path, "operator work\n")
        result = self.invoke("candidate", "--no-suite", success=False)
        self.assertIn("dirty file outside declared paths: foreign name.txt", result.stderr)
        self.assertEqual(path.read_text(), "operator work\n")
        self.assertEqual(self.calls(), [])

    def test_first_stage_refuses_authored_declared_paths_without_mutation(self) -> None:
        for relative in (f"releases/{RELEASE}/NINFER_RELEASE_NOTES.md", f"releases/{RELEASE}/plan.json"):
            with self.subTest(path=relative):
                path = self.root / relative
                original = path.read_bytes() if path.exists() else None
                atomic_write(path, original + b"\n" if original is not None else b"Authored release notes.\n")
                if original is not None:
                    self.git("add", "--", relative)
                before = self.worktree_bytes()
                index = self.git("diff", "--cached", "--binary")
                result = self.invoke("candidate", "--no-suite", success=False)
                self.assertIn("first stage run refuses dirty declared paths: " + relative, result.stderr)
                for guidance in ("--notes", "commit", "discard"):
                    self.assertIn(guidance, result.stderr)
                self.assertEqual(self.worktree_bytes(), before)
                self.assertEqual(self.git("diff", "--cached", "--binary"), index)
                self.assertEqual(self.git("rev-parse", "HEAD"), self.initial)
                self.assertEqual(self.calls(), [])
                if original is None:
                    path.unlink()
                else:
                    atomic_write(path, original)
                    self.git("add", "--", relative)

    def test_first_compose_refuses_authored_declared_paths_without_mutation(self) -> None:
        self.candidate("--no-suite")
        head = self.git("rev-parse", "HEAD")
        for filename in ("NINFER_RELEASE_NOTES.md", "qualification.json", "acceptance/authored.json"):
            with self.subTest(path=filename):
                relative = f"releases/{RELEASE}/{filename}"
                path = self.root / relative
                original = path.read_bytes() if path.exists() else None
                atomic_write(path, original + b"\n" if original is not None else b'{"authored":true}\n')
                before = self.worktree_bytes()
                result = self.finalize("--no-suite", success=False)
                self.assertIn("first compose run refuses dirty declared paths: " + relative, result.stderr)
                for guidance in ("--notes", "commit", "discard"):
                    self.assertIn(guidance, result.stderr)
                self.assertEqual(self.worktree_bytes(), before)
                self.assertEqual(self.git("rev-parse", "HEAD"), head)
                self.assertEqual(self.calls("collect_route_evidence.py"), [])
                if original is None:
                    path.unlink()
                else:
                    atomic_write(path, original)

    def test_failed_compose_resumes_and_restores_partial_tool_outputs(self) -> None:
        self.candidate("--no-suite")
        failure = self.root / ".release-state" / "fail.json"
        atomic_write_json(failure, {"tool": "compose_route_acceptance.py"})
        self.finalize("--no-suite", success=False)
        orphan = self.root / "releases" / RELEASE / "acceptance" / "partial.json"
        atomic_write_json(orphan, {"partial": True})
        failure.unlink()
        self.finalize("--no-suite")
        self.assertEqual(len(self.calls("collect_route_evidence.py")), 2)
        self.assertFalse(orphan.exists())

    def test_authored_guide_rides_only_the_guide_commit(self) -> None:
        path = self.root / "docs" / "QUICKSTART.md"
        original = path.read_bytes()
        authored = original + b"\nOperator-authored release instructions.\n"
        atomic_write(path, authored)
        self.candidate("--no-suite")
        records = DRIVER.group_commits(self.root, RELEASE)
        for group in ("stage", "lane-pin"):
            committed = subprocess.run(["git", "show", records[group]["commit"] + ":docs/QUICKSTART.md"],
                                       cwd=self.root, env=self.environment, check=True, capture_output=True).stdout
            self.assertEqual(committed, original)
        self.assertEqual(path.read_bytes(), authored.replace(PREDECESSOR.encode(), RELEASE.encode()))
        self.assertEqual(len(self.calls("retarget_guide.py")), 1)

    def test_failed_guide_resumes_in_place_without_losing_authored_edits(self) -> None:
        path = self.root / "docs" / "QUICKSTART.md"
        atomic_write(path, path.read_bytes() + b"\nAuthored before retarget.\n")
        failure = self.root / ".release-state" / "fail.json"
        atomic_write_json(failure, {"tool": "retarget_guide.py"})
        self.invoke("candidate", "--no-suite", success=False)
        expected = path.read_bytes() + b"\nAuthored after interruption.\n"
        atomic_write(path, expected)
        failure.unlink()
        self.candidate("--no-suite")
        self.assertEqual(path.read_bytes(), expected)
        self.assertEqual(len(self.calls("retarget_guide.py")), 2)

    def test_interrupted_guide_commits_unchanged_output_without_rerunning(self) -> None:
        driver = self.driver()
        DRIVER.run_pipeline(driver, finalize=False, no_suite=True, through="lane-pin")
        with mock.patch.object(driver, "commit", side_effect=DRIVER.ReleaseError("interrupt guide commit")):
            with self.assertRaisesRegex(DRIVER.ReleaseError, "interrupt guide commit"):
                DRIVER.run_pipeline(driver, finalize=False, no_suite=True)
        self.candidate("--no-suite")
        self.assertEqual(len(self.calls("retarget_guide.py")), 1)

    def test_interrupted_guide_hashes_new_authored_edits_and_retargets_in_place(self) -> None:
        driver = self.driver()
        DRIVER.run_pipeline(driver, finalize=False, no_suite=True, through="lane-pin")
        with mock.patch.object(driver, "commit", side_effect=DRIVER.ReleaseError("interrupt guide commit")):
            with self.assertRaisesRegex(DRIVER.ReleaseError, "interrupt guide commit"):
                DRIVER.run_pipeline(driver, finalize=False, no_suite=True)
        path = self.root / "docs" / "QUICKSTART.md"
        expected = path.read_bytes() + b"\nNew authored guidance.\n"
        atomic_write(path, expected)
        self.candidate("--no-suite")
        self.assertEqual(path.read_bytes(), expected)
        self.assertEqual(len(self.calls("retarget_guide.py")), 2)

    def test_rewritten_recorded_history_is_refused(self) -> None:
        self.candidate("--no-suite")
        tree = self.git("rev-parse", "HEAD^{tree}")
        replacement = self.git("commit-tree", tree, "-m", "test(release): replace temporary history")
        self.git("update-ref", "HEAD", replacement)
        result = self.invoke("status", success=False)
        self.assertIn("rewritten history under recorded", result.stderr)

    def test_finalize_requires_guide_commit(self) -> None:
        result = self.finalize("--no-suite", success=False)
        self.assertIn("requires the guide candidate commit", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_wrong_new_ledger_subject_is_refused_before_compose(self) -> None:
        self.candidate("--no-suite")
        atomic_write_json(self.private / "values.json", {"candidate_override": self.initial})
        result = self.finalize("--no-suite", success=False)
        self.assertIn("ledger stage_commit is not the guide candidate", result.stderr)
        self.assertEqual(self.calls("compose_route_acceptance.py"), [])
        self.assertEqual(len(DRIVER.group_commits(self.root, RELEASE)), 3)

    def test_existing_wrong_ledger_subject_is_not_overwritten(self) -> None:
        self.candidate("--no-suite")
        ledger = self.root / "releases" / RELEASE / "review" / "runtime-ledger.json"
        atomic_write_json(ledger, {"product_tooling": {"stage_commit": self.initial}})
        result = self.finalize("--no-suite", success=False)
        self.assertIn("first compose run refuses dirty declared paths", result.stderr)
        self.assertIn("review/runtime-ledger.json", result.stderr)
        self.assertEqual(self.calls("review_ledger.py"), [])
        self.assertEqual(json.loads(ledger.read_text())["product_tooling"]["stage_commit"], self.initial)

    def test_manifest_plan_disagreement_is_refused(self) -> None:
        self.candidate("--no-suite")
        path = self.root / "releases" / RELEASE / "plan.json"
        plan = json.loads(path.read_text())
        plan["components"][0]["source_commit"] = "9" * 40
        atomic_write_json(path, plan)
        result = self.finalize("--no-suite", success=False)
        self.assertIn("tag or commit differs from plan", result.stderr)
        self.assertEqual(self.calls("collect_route_evidence.py"), [])

    def test_missing_tool_is_named(self) -> None:
        (self.root / "scripts" / "retarget_guide.py").unlink()
        result = self.invoke("candidate", "--no-suite", success=False)
        self.assertIn("missing release tool: scripts/retarget_guide.py", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.initial)

    def test_status_and_next_at_staging_candidate_and_acceptance_pin(self) -> None:
        self.assertTrue(self.invoke("next").stdout.startswith("stage: plan"))
        self.assertEqual(self.invoke("status").stdout.count("\tpending\t"), 8)
        self.candidate("--no-suite")
        self.assertTrue(self.invoke("next").stdout.startswith("compose: --window-root"))
        self.assertEqual(self.invoke("status").stdout.count("\tdone\t"), 3)
        driver = self.driver(window_root=self.private / "windows", reviews=self.private / "reviews",
                             values=self.private / "values.json", as_of="2026-01-02")
        DRIVER.run_pipeline(driver, finalize=True, no_suite=True, through="acceptance-pin")
        self.assertTrue(self.invoke("next").stdout.startswith("audit: none"))
        self.assertEqual(self.invoke("status").stdout.count("\tdone\t"), 6)
        self.invoke("finalize", "--no-suite")
        self.assertEqual(self.invoke("next").stdout.strip(), "complete: publication preflight")

    def test_trailers_recover_state_after_cache_is_removed(self) -> None:
        self.candidate("--no-suite")
        (self.root / ".release-state" / (RELEASE + ".json")).unlink()
        head = self.git("rev-parse", "HEAD")
        self.invoke("candidate", "--no-suite")
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assertEqual(len(self.calls("stage_release.py")), 1)

    def test_native_admission_binder_and_aggregate_are_ordered(self) -> None:
        row = self.plan["components"][1]
        row.update(disposition="recut", release_tag="v3.0.0-native", source_commit="9" * 40)
        bundle = self.private / "native"
        atomic_write_json(bundle / "receipt.json", {"source_commit": "9" * 40, "package_sha256": "8" * 64})
        publication = self.private / "native-publication.json"
        atomic_write_json(publication, {"status": "passed"})
        atomic_write_json(self.root / "releases" / RELEASE / "plan.json", self.plan)
        self.git("add", "--", "releases/" + RELEASE + "/plan.json")
        self.git("commit", "-qm", "test(release): declare native component cut")
        self.candidate("--no-suite", "--bundle", f"rtx4090={bundle}",
                       "--native-publication", f"rtx4090={publication}")
        sequence = [call["tool"] + (" " + call["arguments"][0] if call["tool"] == "aggregate_qualification.py" else "")
                    for call in self.calls()]
        self.assertEqual(sequence[:7], ["stage_release.py", "aggregate_qualification.py admit",
                                       "bind_native_variant.py", "rebind_release.py",
                                       "aggregate_qualification.py compose", "rebind_release.py", "receipt_audit.py"])

    def test_admit_output_wrong_lane_or_arguments_is_refused(self) -> None:
        for output in ({"schema": 1, "lanes": {"unexpected": {"binder_arguments": ["--release", RELEASE]}}},
                       {"schema": True, "lanes": {}}):
            with self.subTest(output=output):
                atomic_write_json(self.root / ".release-state" / "admit-output.json", output)
                result = self.invoke("candidate", "--no-suite", success=False)
                self.assertIn("admit lanes disagree", result.stderr)
                self.assertEqual(self.git("rev-parse", "HEAD"), self.initial)

    def test_carried_runtime_refuses_publication_input(self) -> None:
        publication = self.private / "publication.json"
        atomic_write_json(publication, {})
        result = self.invoke("candidate", "--no-suite", "--runtime-publication", str(publication), success=False)
        self.assertIn("carried rtx5090-container refuses", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_native_missing_bundle_and_publication_name_the_lane(self) -> None:
        self.plan["components"][1].update(disposition="recut", release_tag="v3.0.0-native")
        atomic_write_json(self.root / "releases" / RELEASE / "plan.json", self.plan)
        self.git("add", "--", f"releases/{RELEASE}/plan.json")
        self.git("commit", "-qm", "test(release): commit the native cut plan")
        result = self.invoke("candidate", "--no-suite", success=False)
        self.assertIn("--bundle lanes disagree with plan: missing rtx4090", result.stderr)
        bundle = self.private / "native"
        bundle.mkdir()
        result = self.invoke("candidate", "--no-suite", "--bundle", f"rtx4090={bundle}", success=False)
        self.assertIn("--native-publication lanes disagree with plan: missing rtx4090", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_recut_runtime_uses_plan_and_stage_input_without_native_publication(self) -> None:
        self.plan["components"][0].update(disposition="recut", release_tag="v3.0.0-runtime",
                                           source_commit="9" * 40)
        atomic_write_json(self.root / "releases" / RELEASE / "plan.json", self.plan)
        self.git("add", "--", f"releases/{RELEASE}/plan.json")
        self.git("commit", "-qm", "test(release): commit the container cut plan")
        inputs = {
            "release_tag": "ignored-runtime-tag", "source_commit": "8" * 40,
            "source_tag": "v3.0.0-source", "binary_sha": "7" * 64,
            "archive_sha": "6" * 64, "source_archive_sha": "5" * 64,
            "sbom_sha": "4" * 64, "image_digest": "sha256:" + "3" * 64,
            "runtime_receipt_release": "v3.0.0-image", "source_archive": "source.tar.gz",
            "checksums": "SHA256SUMS",
        }
        atomic_write_json(self.private / "stage.json", inputs)
        atomic_write(self.private / "source.tar.gz", b"source fixture")
        atomic_write(self.private / "SHA256SUMS", "checksum fixture\n")
        atomic_write_json(self.private / "lane.json", {"status": "passed"})
        atomic_write_json(self.private / "runtime-publication.json", {"status": "passed"})
        self.candidate("--no-suite", "--stage-input", str(self.private / "stage.json"),
                       "--lane-receipt", f"rtx5090={self.private / 'lane.json'}",
                       "--runtime-publication", str(self.private / "runtime-publication.json"))
        args = self.calls("stage_release.py")[0]["arguments"]
        self.assertEqual(args[args.index("--release-tag") + 1], "v3.0.0-runtime")
        self.assertEqual(args[args.index("--source-commit") + 1], "9" * 40)
        self.assertEqual(args[args.index("--source-archive") + 1], str((self.private / "source.tar.gz").resolve()))
        self.assertNotIn("--archive-name", args)
        calls = self.calls("aggregate_qualification.py")
        self.assertNotIn("--runtime-publication", calls[0]["arguments"])
        self.assertIn("--runtime-publication", calls[1]["arguments"])
        self.assertNotIn("--native-publication", calls[1]["arguments"])

    def test_publish_only_wraps_preflight_with_exact_head(self) -> None:
        if shutil.which("bash") is None:
            self.skipTest("publication shell preflight needs bash")
        script = self.root / "scripts" / "hosts" / "publish-product-release.sh"
        atomic_write(script, "#!/usr/bin/env bash\nexec " + shlex.quote(sys.executable)
                     + " scripts/stub_support.py publish \"$@\"\n")
        self.git("add", "--", "scripts/hosts/publish-product-release.sh")
        self.git("commit", "-qm", "test(release): install publication preflight fixture")
        self.candidate("--no-suite")
        self.finalize("--no-suite")
        self.invoke("publish", "--preflight", "--pr", "1")
        arguments = self.calls("publish")[0]["arguments"]
        self.assertEqual(arguments, ["--release", RELEASE, "--commit", self.git("rev-parse", "HEAD"), "--pr", "1"])
        result = self.invoke("publish", "--preflight", "--pr", "1", "--publish", success=False)
        self.assertIn("unrecognized arguments: --publish", result.stderr)


if __name__ == "__main__":
    unittest.main()
