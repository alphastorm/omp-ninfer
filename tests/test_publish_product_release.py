"""The product publication command refuses malformed arguments before git or gh runs."""
from __future__ import annotations

import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/hosts/publish-product-release.sh"
ARGUMENTS = ["--release", "v9.9.9", "--commit", "a" * 40, "--pr", "1"]


@unittest.skipIf(os.name == "nt", "POSIX shell fixture")
class PublishArgumentTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        fake = Path(temporary.name)
        self.marker = fake / "called"
        for tool in ("git", "gh"):
            stub = fake / tool
            stub.write_text(f"#!/bin/sh\necho {tool} >> '{self.marker}'\nexit 1\n")
            stub.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{fake}:/usr/bin:/bin")

    def publish(self, *arguments: str) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(SCRIPT), *arguments], capture_output=True, text=True, env=self.env)

    def test_dry_run_with_publish_is_refused_before_git_or_gh_runs(self) -> None:
        result = self.publish(*ARGUMENTS, "--dry-run", "--publish")
        self.assertEqual(result.returncode, 2)
        self.assertIn("choose --dry-run or --publish", result.stderr)
        self.assertFalse(self.marker.exists())

    def test_value_flag_without_a_value_is_a_usage_error_before_git_or_gh_runs(self) -> None:
        for flag in ("--release", "--commit", "--pr"):
            with self.subTest(flag=flag):
                result = self.publish(*ARGUMENTS, flag)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(f"{flag} requires a value", result.stderr)
                self.assertFalse(self.marker.exists())


@unittest.skipIf(os.name == "nt", "POSIX shell fixture")
class PublishGuardTests(unittest.TestCase):
    """All ref/GitHub effects are fake; the shell's real admission and recovery paths execute."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.log = self.root / "calls.jsonl"
        self.state = self.root / "state.json"
        self.configuration = {
            "state": "OPEN", "headRefOid": "a" * 40, "baseRefName": "main",
            "mergeable": "MERGEABLE", "statusCheckRollup": [{"name": "tests", "conclusion": "SUCCESS"}],
            "main": "b" * 40, "tag": None, "release": None, "latest": "v9.9.8",
        }
        fake = r'''
import json, os, pathlib, sys
tool = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
state_path = pathlib.Path(os.environ["PUBLISH_STATE"])
state = json.loads(state_path.read_text())
with open(os.environ["PUBLISH_LOG"], "a") as log:
    log.write(json.dumps([tool, *args]) + "\n")
def finish(code=0, output=""):
    state_path.write_text(json.dumps(state))
    print(output, end="")
    raise SystemExit(code)
if tool == "git":
    if args[:1] == ["-C"]:
        args = args[2:]
    if args[:1] in (["fetch"], ["cat-file"]):
        finish()
    if args[:1] == ["rev-parse"]:
        finish(1 if state["tag"] is None else 0, (state["tag"] or "") + "\n")
    if args[:1] == ["ls-remote"]:
        if any("refs/heads/main" == arg for arg in args):
            finish(output=state["main"] + "\trefs/heads/main\n")
        finish(output="" if state["tag"] is None else
               state["tag"] + "\trefs/tags/v9.9.9\n" + state["tag"] + "\trefs/tags/v9.9.9^{}\n")
    if args[:1] == ["merge-base"]:
        finish(1 if state.get("non_ff") else 0)
    if args[:2] == ["worktree", "add"]:
        tree = pathlib.Path(args[-2])
        (tree / "scripts").mkdir(parents=True)
        (tree / "compatibility.json").write_text(json.dumps({"product_release": state.get("product", "v9.9.9")}))
        notes = tree / "releases/v9.9.9/NINFER_RELEASE_NOTES.md"
        notes.parent.mkdir(parents=True)
        notes.write_text("# Fixture product\n\nPublic fixture notes.\n")
        (tree / "scripts/verify_release.py").write_text(
            "import json,os,sys\n"
            "with open(os.environ['PUBLISH_LOG'],'a') as log: log.write(json.dumps(['verify',*sys.argv[1:]])+'\\n')\n"
            "sys.exit(" + str(int(bool(state.get("bad_pins")))) + ")\n")
        finish()
    if args[:2] == ["worktree", "remove"]:
        finish()
    if args[:1] == ["tag"]:
        state["local_tag"] = "a" * 40
        finish()
    if args[:1] == ["push"]:
        if "--dry-run" in args:
            finish(1 if state.get("refused_push") else 0)
        if "refs/heads/main" in args[-1]:
            state["main"] = args[-1].split(":")[0]
        else:
            state["tag"] = state["local_tag"]
        finish()
if tool == "gh":
    if args[:2] == ["pr", "view"]:
        finish(output=json.dumps(state))
    if args[:2] == ["release", "view"]:
        finish(1 if state["release"] is None else 0, json.dumps(state["release"]))
    if args[:2] == ["release", "create"]:
        if state.get("fail_create"):
            finish(1)
        state["release"] = {"tagName": "v9.9.9", "targetCommitish": "a"*40,
                            "isDraft": False, "isPrerelease": False}
        if not state.get("fail_latest"):
            state["latest"] = "v9.9.9"
        finish()
    if args[:2] == ["release", "edit"]:
        state["latest"] = "v9.9.9"
        finish()
    if args[:1] == ["api"]:
        finish(output=state["latest"] + "\n")
raise SystemExit("unexpected fake command: " + repr([tool, *args]))
'''
        for tool in ("git", "gh"):
            path = self.root / tool
            path.write_text(f"#!{sys.executable}\n" + fake)
            path.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{self.root}:{os.environ['PATH']}",
                        PUBLISH_STATE=str(self.state), PUBLISH_LOG=str(self.log))

    def run_publish(self, *arguments: str) -> subprocess.CompletedProcess:
        self.state.write_text(json.dumps(self.configuration))
        result = subprocess.run(["bash", str(SCRIPT), *ARGUMENTS, *arguments],
                                env=self.env, capture_output=True, text=True, timeout=30)
        self.configuration = json.loads(self.state.read_text())
        return result

    def effects(self) -> list:
        calls = [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []
        return [call for call in calls
                if (call[0] == "git" and ("tag" in call or ("push" in call and "--dry-run" not in call)))
                or (call[0] == "gh" and call[1:3] in (["release", "create"], ["release", "edit"]))]

    def test_admission_refusals_take_no_publication_effect(self) -> None:
        for update in (
            {"headRefOid": "c" * 40}, {"state": "CLOSED"}, {"baseRefName": "other"},
            {"mergeable": "CONFLICTING"}, {"statusCheckRollup": []},
            {"statusCheckRollup": [{"name": "tests", "conclusion": "FAILURE"}]},
            {"tag": "a" * 40}, {"release": {"tagName": "v9.9.9"}},
            {"non_ff": True}, {"refused_push": True}, {"bad_pins": True}, {"product": "v9.9.8"},
        ):
            with self.subTest(update=update):
                original = dict(self.configuration)
                self.configuration.update(update)
                result = self.run_publish("--dry-run")
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(self.effects(), [])
                self.configuration = original

    def test_successful_preflight_verifies_pins_without_live_ref_or_release_effects(self) -> None:
        result = self.run_publish("--dry-run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("preflight passed", result.stdout)
        self.assertEqual(self.effects(), [])
        self.assertIn(["verify", "--release", "v9.9.9", "--require-ready", "--check-pins"],
                      [json.loads(line) for line in self.log.read_text().splitlines()])

    def test_tag_push_partial_failure_completes_without_replaying_refs(self) -> None:
        self.configuration["fail_create"] = True
        first = self.run_publish("--publish")
        self.assertNotEqual(first.returncode, 0)
        self.assertEqual(self.configuration["tag"], "a" * 40)
        previous = self.effects()
        self.configuration["fail_create"] = False
        self.configuration["state"] = "MERGED"
        result = self.run_publish("--complete-existing", "--publish")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        effects = self.effects()[len(previous):]
        self.assertEqual([call[0:3] for call in effects], [["gh", "release", "create"]])
        self.assertEqual(self.configuration["latest"], "v9.9.9")

    def test_latest_failure_completes_the_verified_existing_release_only(self) -> None:
        self.configuration["fail_latest"] = True
        self.assertNotEqual(self.run_publish("--publish").returncode, 0)
        previous = self.effects()
        result = self.run_publish("--complete-existing", "--publish")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([call[0:3] for call in self.effects()[len(previous):]],
                         [["gh", "release", "edit"]])

    def test_completion_refuses_mismatched_main_tag_or_release_without_effects(self) -> None:
        baseline = dict(self.configuration, main="a" * 40, tag="a" * 40, state="MERGED")
        for update in (
            {"main": "b" * 40}, {"tag": "c" * 40}, {"tag": None},
            {"release": {"tagName": "other", "targetCommitish": "a" * 40,
                         "isDraft": False, "isPrerelease": False}},
            {"release": {"tagName": "v9.9.9", "targetCommitish": "c" * 40,
                         "isDraft": False, "isPrerelease": False}},
            {"release": {"tagName": "v9.9.9", "targetCommitish": "a" * 40,
                         "isDraft": True, "isPrerelease": False}},
        ):
            with self.subTest(update=update):
                self.configuration = dict(baseline, **update)
                self.assertNotEqual(self.run_publish("--complete-existing", "--publish").returncode, 0)
                self.assertEqual(self.effects(), [])


if __name__ == "__main__":
    unittest.main()
