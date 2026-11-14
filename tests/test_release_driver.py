"""Exercise release commits and interrupted groups in disposable, host-free repositories."""

from __future__ import annotations

import argparse
import copy
import contextlib
import hashlib
import importlib.util
import io
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

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_SPEC = importlib.util.spec_from_file_location("release_driver_plan_fixture", ROOT / "tests" / "test_release_plan.py")
assert FIXTURE_SPEC is not None and FIXTURE_SPEC.loader is not None
FIXTURES = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(FIXTURES)
PREDECESSOR, RELEASE, plan_fixture = FIXTURES.PREDECESSOR, FIXTURES.RELEASE, FIXTURES.plan_fixture
SPEC = importlib.util.spec_from_file_location("release_driver_test", ROOT / "scripts" / "release.py")
assert SPEC is not None and SPEC.loader is not None
DRIVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER)
from release_io import atomic_write, atomic_write_json
from verify_release import PROVENANCE_CLAIM_RE

TOOLS = ("stage_release.py", "aggregate_qualification.py", "bind_native_variant.py",
         "rebind_release.py", "receipt_audit.py", "retarget_guide.py", "verify_release.py",
         "collect_route_evidence.py", "review_ledger.py", "compose_route_acceptance.py", "run_tests.py")

# These tools implement only their public command contracts. No sibling implementation is needed.
SUPPORT = r'''
import copy
import json
import re
import subprocess
import sys
from pathlib import Path
from release_io import atomic_write, atomic_write_json

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKERS = ("nonpublic-fixture-marker",)
ROUTES = ("rtx5090-container-host", "rtx5090-macos-client", "rtx5090-windows-client",
          "rtx4090-native", "rtx3090-native")

def provenance_claim_errors(value, label, *, statement="", clauses=()):
    if isinstance(value, list):
        return [error for index, child in enumerate(value)
                for error in provenance_claim_errors(child, f"{label}[{index}]", statement=statement, clauses=clauses)]
    if isinstance(value, dict):
        return [error for key, child in value.items()
                for error in provenance_claim_errors(child, f"{label}.{key}", statement=statement, clauses=clauses)]
    if isinstance(value, str) and any(character.isspace() for character in value):
        prose = value.replace(statement, "") if statement else value
        for clause in clauses:
            prose = prose.replace(clause, "")
        match = re.search(PROVENANCE_PATTERN, prose, re.IGNORECASE)
        if match:
            return [f"{label} makes an ungenerated component provenance claim: {match[0]!r}"]
    return []

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
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                          capture_output=True, text=True, encoding="utf-8").stdout.strip()
    invocations.append({"tool": name, "arguments": args, "head": head})
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
        rewrite = local / "rewrite-mode.json"
        if rewrite.exists():
            path = ROOT / load(rewrite)["path"]
            atomic_write(path, path.read_bytes() + b"\n# Rewritten by the release tool.\n")
            path.chmod(0o644)
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
        declared = {row["id"] for row in load(manifest)["components"]["ninfer_variants"]}
        lanes = [lane for lane in ROUTES if not lane.endswith("-native")
                 or lane.removesuffix("-native") + "-windows-native" in declared]
        if values("--lane-dir"):
            runtime_lanes = {"rtx5090", *(lane.removesuffix("-native") for lane in lanes if lane.endswith("-native"))}
            assert {item.partition("=")[0] for item in values("--lane-dir")} == runtime_lanes
        for item in values("--lane-dir") + values("--corrected-attempt"):
            path = Path(item.partition("=")[2])
            assert path.is_absolute() and path.is_dir()
        atomic_write_json(Path(value("--output")), {"candidate": value("--candidate")})
        for lane in lanes:
            atomic_write_json(Path(value("--receipts-dir")) / (lane + "-run.json"),
                              {"candidate": value("--candidate"), "lane": lane})
    elif name == "review_ledger.py":
        assert Path(value("--reviews")).is_dir()
        candidate = load(Path(value("--values"))).get("candidate_override", value("--candidate"))
        atomic_write_json(directory / "review" / "runtime-ledger.json", {"product_tooling": {"stage_commit": candidate}})
    elif name == "compose_route_acceptance.py":
        assert load(Path(value("--evidence")))["candidate"] == value("--candidate")
        declared = {row["id"] for row in load(manifest)["components"]["ninfer_variants"]}
        lanes = {lane for lane in ROUTES if not lane.endswith("-native")
                 or lane.removesuffix("-native") + "-windows-native" in declared}
        assert set(item.partition("=")[0] for item in values("--route")) == lanes
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
                            "PYTHONIOENCODING": "utf-8",
                            "GIT_AUTHOR_NAME": "Release fixture", "GIT_COMMITTER_NAME": "Release fixture",
                            "GIT_AUTHOR_EMAIL": "release@example.invalid",
                            "GIT_COMMITTER_EMAIL": "release@example.invalid"}
        self.plan, self.previous, self.authority = plan_fixture(self.root)
        for name in ("release.py", "release_plan.py", "release_io.py"):
            atomic_write(self.root / "scripts" / name, (ROOT / "scripts" / name).read_bytes())
        atomic_write(self.root / "scripts" / "stub_support.py",
                     f"PROVENANCE_PATTERN = {PROVENANCE_CLAIM_RE.pattern!r}\n" + SUPPORT)
        for name in TOOLS:
            source = ("from stub_support import PRIVATE_MARKERS, predecessor_manifest, "
                      "provenance_claim_errors, unchanged_native_variant, run\n"
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
        result = subprocess.run([sys.executable, str(self.root / "scripts" / "release.py"), *command.split(),
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

    def window_state(self) -> dict:
        candidate = DRIVER.group_commits(self.root, RELEASE)["guide"]["commit"]
        manifest = json.loads((self.root / "releases" / RELEASE / "manifest.json").read_text())
        state = {"schema": 1, "release": RELEASE, "candidate": candidate, "lanes": {},
                 "other_field": "ignored"}
        for component in DRIVER.manifest_components(manifest):
            lane = component.split("-", 1)[0]
            directory = f"{lane}/attempt-1"
            (self.private / "windows" / directory).mkdir(parents=True)
            state["lanes"][lane] = {
                "accepted": 1, "other_field": "ignored",
                "attempts": [{"attempt": 1, "directory": directory, "status": "passed",
                              "other_field": "ignored"}],
            }
        atomic_write_json(self.private / "windows" / "window-state.json", state)
        return state

    def driver(self, **values) -> Any:
        options = argparse.Namespace(**{"notes": self.private / "notes.md", **values})
        return DRIVER.ReleaseDriver(self.root, RELEASE, options)

    def remove_plan(self) -> None:
        (self.root / "releases" / RELEASE / "plan.json").unlink()
        self.git("add", "--", f"releases/{RELEASE}/plan.json")
        self.git("commit", "-qm", "test(release): start without a release plan")

    def test_plan_init_commits_the_opening_plan_without_completing_a_group(self) -> None:
        self.remove_plan()
        self.invoke("plan init")
        self.assertEqual(self.git("log", "-1", "--format=%s"), f"chore(release): plan {RELEASE}")
        self.assertEqual(self.git("log", "-1", "--format=%(trailers:only)").strip(), f"Release: {RELEASE}")
        self.assertEqual(DRIVER.group_commits(self.root, RELEASE), {})
        plan = json.loads((self.root / "releases" / RELEASE / "plan.json").read_text())
        self.assertTrue(all(row["disposition"] == "carried" for row in plan["components"]))
        self.assertEqual(plan["decisions"], [])
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.candidate("--no-suite")
        self.assertEqual(len(DRIVER.group_commits(self.root, RELEASE)), 3)

    def test_plan_init_accepts_explicit_public_inputs(self) -> None:
        self.remove_plan()
        self.invoke("plan init", "--recut", "rtx5090-container=v3.0.0-runtime@" + "9" * 40,
                    "--client-tag", "v3.0.0", "--decision", "scope:scope:" + "8" * 64)
        plan = json.loads((self.root / "releases" / RELEASE / "plan.json").read_text())
        self.assertEqual(plan["components"][0]["disposition"], "recut")
        self.assertEqual(plan["client"]["disposition"], "updated")
        self.assertEqual(plan["decisions"][0]["id"], "scope")
        self.invoke("plan check")

    def test_plan_init_no_commit_then_authored_plan_commit(self) -> None:
        self.remove_plan()
        head = self.git("rev-parse", "HEAD")
        result = self.invoke("plan init", "--no-commit")
        self.assertIn("plan commit", result.stdout)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        path = self.root / "releases" / RELEASE / "plan.json"
        plan = json.loads(path.read_text())
        plan["limitations"] = ["Only the documented transport topology is supported."]
        atomic_write_json(path, plan)
        self.invoke("plan commit")
        self.assertEqual(self.git("log", "-1", "--format=%s"), f"chore(release): plan {RELEASE}")
        self.assertEqual(json.loads(path.read_text())["limitations"], plan["limitations"])
        self.assertEqual(DRIVER.group_commits(self.root, RELEASE), {})
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_plan_commit_refuses_other_dirty_paths_without_mutation(self) -> None:
        self.remove_plan()
        self.invoke("plan init", "--no-commit")
        atomic_write(self.root / "operator.txt", "Authored work.\n")
        before = self.worktree_bytes()
        head = self.git("rev-parse", "HEAD")
        result = self.invoke("plan commit", success=False)
        self.assertIn("plan commit refuses other dirty paths: operator.txt", result.stderr)
        self.assertEqual(self.worktree_bytes(), before)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)

    def test_plan_commit_validates_authored_limitations_without_mutation(self) -> None:
        self.remove_plan()
        self.invoke("plan init", "--no-commit")
        path = self.root / "releases" / RELEASE / "plan.json"
        plan = json.loads(path.read_text())
        plan["limitations"] = ["All runtime packages were rebuilt together."]
        atomic_write_json(path, plan)
        before = self.worktree_bytes()
        head = self.git("rev-parse", "HEAD")
        result = self.invoke("plan commit", success=False)
        self.assertIn("ungenerated component provenance claim", result.stderr)
        self.assertEqual(self.worktree_bytes(), before)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)

    def test_plan_init_refuses_existing_plan_without_mutation(self) -> None:
        before = self.worktree_bytes()
        self.invoke("plan init", success=False)
        self.assertEqual(self.worktree_bytes(), before)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.initial)

    def test_plan_init_refuses_dirty_tree_without_mutation(self) -> None:
        self.remove_plan()
        atomic_write(self.root / "operator.txt", "Authored input.\n")
        before = self.worktree_bytes()
        head = self.git("rev-parse", "HEAD")
        result = self.invoke("plan init", success=False)
        self.assertIn("plan init requires a clean tree", result.stderr)
        self.assertEqual(self.worktree_bytes(), before)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)

    def test_plan_init_rejects_an_invalid_result_without_leaving_a_plan(self) -> None:
        self.remove_plan()
        before = self.worktree_bytes()
        head = self.git("rev-parse", "HEAD")
        tag = self.previous["components"]["ninfer"]["release_tag"]
        result = self.invoke("plan init", "--recut", f"rtx5090-container={tag}@" + "9" * 40, success=False)
        self.assertIn("failed plan check", result.stderr)
        self.assertEqual(self.worktree_bytes(), before)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)

    def test_candidate_refuses_an_untracked_plan_with_opening_commit_guidance(self) -> None:
        self.remove_plan()
        atomic_write_json(self.root / "releases" / RELEASE / "plan.json", self.plan)
        before = self.worktree_bytes()
        result = self.invoke("candidate", "--no-suite", success=False)
        self.assertIn("plan init", result.stderr)
        self.assertIn("commit", result.stderr)
        self.assertEqual(self.worktree_bytes(), before)

    def test_rehearsal_refuses_a_dirty_source_before_cloning(self) -> None:
        atomic_write(self.root / "operator.txt", "Authored input.\n")
        before = self.worktree_bytes()
        destination = self.private / "rehearsal"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = DRIVER.rehearse(self.root, keep=destination)
        self.assertEqual(result, 1)
        self.assertIn("rehearsal requires a clean repository", output.getvalue())
        self.assertFalse(destination.exists())
        self.assertEqual(self.worktree_bytes(), before)

    def test_rehearsal_refuses_shallow_history_before_cloning(self) -> None:
        destination = self.private / "rehearsal"
        output = io.StringIO()
        with mock.patch.object(DRIVER, "git", return_value="true\n"), contextlib.redirect_stdout(output):
            result = DRIVER.rehearse(self.root, keep=destination)
        self.assertEqual(result, 1)
        self.assertIn("non-shallow", output.getvalue())
        self.assertFalse(destination.exists())

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

    def test_interrupted_unchanged_group_reruns_tools_before_committing(self) -> None:
        self.interrupt()
        self.assertEqual(self.git("rev-parse", "HEAD"), self.initial)
        self.candidate("--no-suite")
        self.assertEqual(len(self.calls("stage_release.py")), 2)
        self.assertEqual(len(DRIVER.group_commits(self.root, RELEASE)), 3)

    def test_forged_complete_state_runs_tools_before_committing(self) -> None:
        driver = self.driver()
        DRIVER.run_pipeline(driver, finalize=False, no_suite=True, through="lane-pin")
        head = self.git("rev-parse", "HEAD")
        guide = self.root / "docs" / "QUICKSTART.md"
        atomic_write(guide, guide.read_bytes().replace(PREDECESSOR.encode(), RELEASE.encode()))
        guide_sha = hashlib.sha256(guide.read_bytes()).hexdigest()
        # Reconstruct the old completion fingerprint without trusting driver helpers.
        payload = {"plan_sha256": hashlib.sha256(driver.plan_path.read_bytes()).hexdigest(),
                   "HEAD": head, "private": {"guide_sha256": guide_sha},
                   "options": driver.state["options"],
                   "tools": {"retarget_guide.py": hashlib.sha256(
                       (self.root / "scripts" / "retarget_guide.py").read_bytes()).hexdigest()}}
        driver.state["groups"]["guide"] = {
            "attempts": 1, "tools_complete": True,
            "inputs_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest(),
            "outputs": {"docs/QUICKSTART.md": guide_sha},
        }
        driver.save()
        self.assertEqual(self.calls("retarget_guide.py"), [])
        self.candidate("--no-suite")
        calls = self.calls("retarget_guide.py")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["head"], head)
        self.assertNotEqual(DRIVER.group_commits(self.root, RELEASE)["guide"]["commit"], head)
        self.assertEqual(hashlib.sha256(guide.read_bytes()).hexdigest(), guide_sha)

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
        before = self.worktree_bytes()
        result = self.invoke("candidate", "--no-suite", success=False)
        self.assertIn("plan commit", result.stderr)
        self.assertEqual(self.worktree_bytes(), before)
        self.git("add", "--", f"releases/{RELEASE}/plan.json")
        self.git("commit", "-qm", "test(release): commit the revised support posture")
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

    def test_interrupted_stage_recovers_the_missing_committed_plan(self) -> None:
        driver = self.driver()
        driver.state["groups"]["stage"] = {"attempts": 1, "tools_complete": False}
        driver.save()
        plan = driver.plan_path.read_bytes()
        driver.plan_path.unlink()
        partial = self.root / "releases" / RELEASE / "qualification" / "partial.json"
        atomic_write_json(partial, {"partial": True})
        atomic_write_json(driver.plan_path.parent / "manifest.json", {"status": "draft"})
        self.candidate("--no-suite")
        self.assertEqual(driver.plan_path.read_bytes(), plan)
        self.assertEqual(driver.plan_path.read_bytes(), subprocess.run(
            ["git", "show", f"HEAD:releases/{RELEASE}/plan.json"], cwd=self.root,
            env=self.environment, check=True, capture_output=True).stdout)
        self.assertFalse(partial.exists())
        self.assertEqual(len(self.calls("stage_release.py")), 1)
        self.assertEqual(len(DRIVER.group_commits(self.root, RELEASE)), 3)

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
                if relative.endswith("/plan.json"):
                    self.assertIn("candidate requires a committed plan: " + relative, result.stderr)
                    self.assertIn("plan init", result.stderr)
                else:
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

    def assert_first_group_preserves_authored_paths(self, group: str) -> None:
        driver = self.driver(window_root=self.private / "windows", reviews=self.private / "reviews",
                             values=self.private / "values.json", as_of="2026-01-02")
        preceding = DRIVER.GROUPS[DRIVER.GROUPS.index(group) - 1]
        DRIVER.run_pipeline(driver, finalize=False, no_suite=True,
                            through="stage" if group == "lane-pin" else "guide")
        if group != "lane-pin":
            DRIVER.run_pipeline(driver, finalize=True, no_suite=True, through=preceding)
        relative = f"releases/{RELEASE}/NINFER_RELEASE_NOTES.md"
        notes = self.root / relative
        atomic_write(notes, notes.read_bytes() + b"\nAuthored after the preceding commit.\n")
        untracked = self.root / "releases" / RELEASE / "authored.txt"
        atomic_write(untracked, "Uncommitted release input.\n")
        before = self.worktree_bytes()
        head = self.git("rev-parse", "HEAD")
        calls = self.calls()
        result = (self.invoke("candidate", "--no-suite", success=False) if group == "lane-pin"
                  else self.finalize("--no-suite", success=False))
        self.assertIn(relative, result.stderr)
        self.assertIn(untracked.relative_to(self.root).as_posix(), result.stderr)
        self.assertEqual(self.worktree_bytes(), before)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assertEqual(self.calls(), calls)

    def test_first_lane_pin_preserves_authored_declared_paths(self) -> None:
        self.assert_first_group_preserves_authored_paths("lane-pin")

    def test_first_platform_pin_preserves_authored_declared_paths(self) -> None:
        self.assert_first_group_preserves_authored_paths("platform-pin")

    def test_first_acceptance_pin_preserves_authored_declared_paths(self) -> None:
        self.assert_first_group_preserves_authored_paths("acceptance-pin")

    def test_first_audit_preserves_authored_declared_paths(self) -> None:
        self.assert_first_group_preserves_authored_paths("audit")

    def test_first_manifest_pin_preserves_authored_declared_paths(self) -> None:
        self.assert_first_group_preserves_authored_paths("manifest-pin")

    def test_tool_mode_change_refuses_the_group_without_committing(self) -> None:
        driver = self.driver()
        DRIVER.run_pipeline(driver, finalize=False, no_suite=True, through="stage")
        self.git("config", "core.filemode", "true")
        relative = f"releases/{RELEASE}/release-helper.sh"
        path = self.root / relative
        atomic_write(path, "#!/bin/sh\nexit 0\n")
        path.chmod(0o755)
        self.git("add", "--", relative)
        self.git("commit", "-qm", "test(release): seed executable release helper")
        head = self.git("rev-parse", "HEAD")
        self.assertTrue(self.git("ls-tree", "HEAD", "--", relative).startswith("100755 "))
        atomic_write_json(self.root / ".release-state" / "rewrite-mode.json", {"path": relative})
        result = self.invoke("candidate", "--no-suite", success=False)
        self.assertIn(relative, result.stderr)
        self.assertIn("100755", result.stderr)
        self.assertIn("100644", result.stderr)
        self.assertEqual(path.stat().st_mode & 0o111, 0)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assertEqual(list(DRIVER.group_commits(self.root, RELEASE)), ["stage"])
        self.assertEqual(self.calls("rebind_release.py")[-1]["head"], head)

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

    def test_interrupted_guide_reruns_without_changing_its_output(self) -> None:
        driver = self.driver()
        DRIVER.run_pipeline(driver, finalize=False, no_suite=True, through="lane-pin")
        with mock.patch.object(driver, "commit", side_effect=DRIVER.ReleaseError("interrupt guide commit")):
            with self.assertRaisesRegex(DRIVER.ReleaseError, "interrupt guide commit"):
                DRIVER.run_pipeline(driver, finalize=False, no_suite=True)
        expected = (self.root / "docs" / "QUICKSTART.md").read_bytes()
        self.candidate("--no-suite")
        self.assertEqual(len(self.calls("retarget_guide.py")), 2)
        self.assertEqual((self.root / "docs" / "QUICKSTART.md").read_bytes(), expected)

    def test_interrupted_guide_preserves_new_authored_edits_and_retargets_in_place(self) -> None:
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

    def test_clean_window_index_passes_accepted_lane_directories(self) -> None:
        self.candidate("--no-suite")
        state = self.window_state()
        state["lanes"]["rtx3090"]["attempts"][0]["status"] = "retired"
        atomic_write_json(self.private / "windows" / "window-state.json", state)
        self.finalize("--no-suite")
        arguments = self.calls("collect_route_evidence.py")[0]["arguments"]
        actual = {arguments[position + 1] for position, argument in enumerate(arguments) if argument == "--lane-dir"}
        expected = {f"{lane}={(self.private / 'windows' / row['attempts'][0]['directory']).resolve()}"
                    for lane, row in state["lanes"].items()}
        self.assertEqual(actual, expected)
        self.assertNotIn("--corrected-attempt", arguments)

    def test_corrected_container_attempt_passes_each_earlier_spent_attempt(self) -> None:
        self.candidate("--no-suite")
        state = self.window_state()
        attempts = []
        for number, status in ((1, "spent-failed"), (2, "spent-failed"), (3, "passed"), (4, "spent-failed")):
            directory = f"rtx5090/attempt-{number}"
            (self.private / "windows" / directory).mkdir(parents=True, exist_ok=True)
            attempts.append({"attempt": number, "directory": directory, "status": status})
        state["lanes"]["rtx5090"] = {"accepted": 3, "attempts": attempts}
        atomic_write_json(self.private / "windows" / "window-state.json", state)
        self.finalize("--no-suite")
        arguments = self.calls("collect_route_evidence.py")[0]["arguments"]
        self.assertIn(f"rtx5090={(self.private / 'windows' / 'rtx5090/attempt-3').resolve()}", arguments)
        corrected = [arguments[position + 1] for position, argument in enumerate(arguments)
                     if argument == "--corrected-attempt"]
        self.assertEqual(corrected, [f"rtx5090={(self.private / 'windows' / f'rtx5090/attempt-{number}').resolve()}"
                                     for number in (1, 2)])

    def test_unindexed_window_keeps_the_recorded_layout(self) -> None:
        self.candidate("--no-suite")
        self.finalize("--no-suite")
        arguments = self.calls("collect_route_evidence.py")[0]["arguments"]
        self.assertIn("--window-root", arguments)
        self.assertNotIn("--lane-dir", arguments)
        self.assertNotIn("--corrected-attempt", arguments)

    def test_index_lane_set_follows_the_manifest_not_a_fixed_lane_count(self) -> None:
        self.previous["components"]["ninfer_variants"] = []
        self.plan["components"] = self.plan["components"][:1]
        atomic_write_json(self.root / "releases" / PREDECESSOR / "manifest.json", self.previous)
        atomic_write_json(self.root / "releases" / RELEASE / "plan.json", self.plan)
        self.git("add", "--", f"releases/{PREDECESSOR}/manifest.json", f"releases/{RELEASE}/plan.json")
        self.git("commit", "-qm", "test(release): declare only the container runtime")
        self.candidate("--no-suite")
        self.window_state()
        self.finalize("--no-suite")
        arguments = self.calls("collect_route_evidence.py")[0]["arguments"]
        actual = [arguments[position + 1].partition("=")[0] for position, argument in enumerate(arguments)
                  if argument == "--lane-dir"]
        self.assertEqual(actual, ["rtx5090"])

    def test_window_index_refusals_do_not_run_tools_or_change_product_bytes(self) -> None:
        self.candidate("--no-suite")
        baseline = self.window_state()
        (self.private / "outside").mkdir()
        atomic_write(self.private / "windows" / "not-a-directory", "file\n")
        mutations = [
            ("schema", lambda state: state.update(schema=2), "schema must be 1"),
            ("schema-type", lambda state: state.update(schema=True), "schema must be 1"),
            ("release", lambda state: state.update(release=PREDECESSOR), "release must match"),
            ("candidate", lambda state: state.update(candidate=self.initial), "candidate must equal"),
            ("lanes-type", lambda state: state.update(lanes=[]), "lanes must equal"),
            ("missing-lane", lambda state: state["lanes"].pop("rtx4090"), "lanes must equal"),
            ("extra-lane", lambda state: state["lanes"].update(extra={}), "lanes must equal"),
            ("lane-type", lambda state: state["lanes"].update(rtx5090=[]), "rtx5090 must be an object"),
            ("unaccepted", lambda state: state["lanes"]["rtx5090"].update(accepted=None), "positive integer"),
            ("accepted-type", lambda state: state["lanes"]["rtx5090"].update(accepted=True), "positive integer"),
            ("accepted-zero", lambda state: state["lanes"]["rtx5090"].update(accepted=0), "positive integer"),
            ("accepted-missing", lambda state: state["lanes"]["rtx5090"].update(accepted=2), "no matching entry"),
            ("attempts-type", lambda state: state["lanes"]["rtx5090"].update(attempts={}), "attempts must be an array"),
            ("entry-type", lambda state: state["lanes"]["rtx5090"]["attempts"].__setitem__(0, []), "must be an object"),
            ("attempt-type", lambda state: state["lanes"]["rtx5090"]["attempts"][0].update(attempt=True),
             "unique positive integer"),
            ("duplicate", lambda state: state["lanes"]["rtx5090"]["attempts"].append(
                copy.deepcopy(state["lanes"]["rtx5090"]["attempts"][0])), "unique positive integer"),
            ("planned", lambda state: state["lanes"]["rtx5090"]["attempts"][0].update(status="planned"),
             "accepted attempt must be passed or retired"),
            ("failed", lambda state: state["lanes"]["rtx5090"]["attempts"][0].update(status="spent-failed"),
             "accepted attempt must be passed or retired"),
            ("invalid-status", lambda state: state["lanes"]["rtx5090"]["attempts"][0].update(status="other"),
             "status is invalid"),
            ("directory-type", lambda state: state["lanes"]["rtx5090"]["attempts"][0].update(directory=[]),
             "relative POSIX path"),
            ("absolute", lambda state: state["lanes"]["rtx5090"]["attempts"][0].update(
                directory=(self.private / "outside").resolve().as_posix()), "relative POSIX path"),
            ("drive", lambda state: state["lanes"]["rtx5090"]["attempts"][0].update(directory="D:/outside"),
             "relative POSIX path"),
            ("backslash", lambda state: state["lanes"]["rtx5090"]["attempts"][0].update(directory=r"rtx5090\attempt-1"),
             "relative POSIX path"),
            ("escape", lambda state: state["lanes"]["rtx5090"]["attempts"][0].update(directory="../outside"),
             "escapes the window root"),
            ("missing", lambda state: state["lanes"]["rtx5090"]["attempts"][0].update(directory="missing"),
             "directory must exist"),
            ("file", lambda state: state["lanes"]["rtx5090"]["attempts"][0].update(directory="not-a-directory"),
             "directory must exist"),
            ("unselected-directory", lambda state: state["lanes"]["rtx5090"]["attempts"].append(
                {"attempt": 2, "directory": "../outside", "status": "planned"}), "escapes the window root"),
        ]
        before = self.worktree_bytes()
        candidate = self.git("rev-parse", "HEAD")
        for name, mutate, message in mutations:
            with self.subTest(rule=name):
                state = copy.deepcopy(baseline)
                mutate(state)
                atomic_write_json(self.private / "windows" / "window-state.json", state)
                result = self.finalize("--no-suite", success=False)
                self.assertIn("window-state.json:", result.stderr)
                self.assertIn(message, result.stderr)
                self.assertEqual(self.calls("collect_route_evidence.py"), [])
                self.assertEqual(self.worktree_bytes(), before)
                self.assertEqual(self.git("rev-parse", "HEAD"), candidate)

    def test_window_index_rejects_malformed_json(self) -> None:
        self.candidate("--no-suite")
        for content in ("[]", "{"):
            with self.subTest(content=content):
                atomic_write(self.private / "windows" / "window-state.json", content)
                self.finalize("--no-suite", success=False)
                self.assertEqual(self.calls("collect_route_evidence.py"), [])

    def test_window_index_rejects_a_symlink_escape(self) -> None:
        self.candidate("--no-suite")
        state = self.window_state()
        outside = self.private / "outside"
        outside.mkdir()
        try:
            (self.private / "windows" / "escape").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("directory symlinks are not available")
        state["lanes"]["rtx5090"]["attempts"][0]["directory"] = "escape"
        atomic_write_json(self.private / "windows" / "window-state.json", state)
        result = self.finalize("--no-suite", success=False)
        self.assertIn("directory escapes the window root", result.stderr)
        self.assertEqual(self.calls("collect_route_evidence.py"), [])

    def test_changed_index_reruns_interrupted_compose_with_the_new_accepted_attempt(self) -> None:
        self.candidate("--no-suite")
        state = self.window_state()
        directory = "rtx5090/attempt-2"
        (self.private / "windows" / directory).mkdir()
        state["lanes"]["rtx5090"]["attempts"].append({"attempt": 2, "directory": directory, "status": "passed"})
        atomic_write_json(self.private / "windows" / "window-state.json", state)
        self.interrupt(finalize=True, command="finalize", window_root=self.private / "windows",
                       reviews=self.private / "reviews", values=self.private / "values.json", as_of="2026-01-02")
        state["lanes"]["rtx5090"]["accepted"] = 2
        atomic_write_json(self.private / "windows" / "window-state.json", state)
        self.finalize("--no-suite")
        calls = self.calls("collect_route_evidence.py")
        self.assertEqual(len(calls), 2)
        self.assertIn(f"rtx5090={(self.private / 'windows' / directory).resolve()}", calls[1]["arguments"])

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

    def test_carried_client_defaults_to_the_predecessor_public_descriptor(self) -> None:
        self.candidate("--no-suite")
        arguments = self.calls("stage_release.py")[0]["arguments"]
        expected = self.root / "releases" / PREDECESSOR / "qualification" / "client-components.json"
        self.assertEqual(arguments[arguments.index("--omp-component") + 1], str(expected.resolve()))

    def test_carried_client_refuses_a_missing_predecessor_descriptor(self) -> None:
        relative = f"releases/{PREDECESSOR}/qualification/client-components.json"
        (self.root / relative).unlink()
        self.git("add", "--", relative)
        self.git("commit", "-qm", "test(release): remove the predecessor client descriptor")
        result = self.invoke("candidate", "--no-suite", success=False)
        self.assertIn("carried client requires predecessor descriptor: " + relative, result.stderr)
        self.assertEqual(self.calls(), [])

    def test_carried_client_can_use_an_explicit_descriptor(self) -> None:
        descriptor = self.private / "client-components.json"
        atomic_write_json(descriptor, {"omp": self.previous["components"]["omp"]})
        self.candidate("--no-suite", "--client-component", str(descriptor))
        arguments = self.calls("stage_release.py")[0]["arguments"]
        self.assertEqual(arguments[arguments.index("--omp-component") + 1], str(descriptor.resolve()))

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
