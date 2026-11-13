"""Watch receipts separate composition, observations and incomplete triage evidence."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("upstream_watch", ROOT / "scripts" / "upstream_watch.py")
assert SPEC is not None and SPEC.loader is not None
WATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WATCH)

ENTRY = {
    "id": "engine",
    "upstream": "example/engine",
    "upstream_ref": "master",
    "fork_repo": "example/fork",
    "fork_point": "a" * 40,
    "fork_point_meaning": "declared fixture comparison base",
    "overlap_paths": ["src/serve/", "src/runtime/engine/"],
}


def watch(
    files: list[str], commit_count: int, ahead_by: int, *,
    compare_extra: dict[str, Any] | None = None,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    commits = [
        {"sha": f"{i:040x}", "commit": {"message": f"fix(ops): change {i}", "committer": {"date": "2026-09-23T00:00:00Z"}}}
        for i in range(commit_count)
    ]

    def gh_api(path: str) -> Any:
        if path == "repos/example/engine/commits/master":
            return {"sha": "b" * 40, "commit": {"committer": {"date": "2026-09-23T00:00:00Z"}}}
        if path.startswith("repos/example/engine/commits/") and detail is not None:
            return detail
        if path.startswith("repos/example/engine/compare/"):
            return {
                "status": "ahead", "ahead_by": ahead_by, "total_commits": ahead_by,
                "commits": commits, "files": [{"filename": name} for name in files],
                **(compare_extra or {}),
            }
        raise AssertionError(f"unexpected API path {path}")

    with mock.patch.object(WATCH, "gh_api", gh_api):
        return WATCH.watch_one(
            ENTRY, per_commit_files=detail is not None,
            incorporated=WATCH.incorporated_baseline(ENTRY, {}),
        )


class UpstreamWatchTest(unittest.TestCase):
    def test_cut_file_list_is_unknown_not_an_applicability_claim(self) -> None:
        # The API lists the first 300 paths alphabetically; the overlapping src/ paths come later.
        files = [f"bench/ops/case_{i:03d}.cu" for i in range(WATCH.API_FILE_LIMIT)]
        result = watch(files, commit_count=250, ahead_by=402)
        comparison = result["comparison"]
        self.assertEqual(comparison["path_triage"], "unknown-truncated")
        self.assertEqual(comparison["status"], "unknown")
        self.assertTrue(comparison["files_truncated"])
        self.assertTrue(comparison["commits_truncated"])
        self.assertEqual((comparison["commits_listed"], comparison["ahead_by"]), (250, 402))
        self.assertEqual({commit["triage"] for commit in result["commits"]}, {"review-incomplete-evidence"})
        self.assertEqual({commit["applicability"] for commit in result["commits"]}, {"not-assessed"})

    def test_complete_list_without_overlap_is_only_path_triage(self) -> None:
        files = [f"bench/ops/case_{i:03d}.cu" for i in range(WATCH.API_FILE_LIMIT - 1)]
        result = watch(files, commit_count=3, ahead_by=3)
        comparison = result["comparison"]
        self.assertEqual(comparison["path_triage"], "no-watched-path-match")
        self.assertEqual(comparison["status"], "complete")
        self.assertFalse(comparison["files_truncated"])
        self.assertFalse(comparison["commits_truncated"])
        self.assertEqual({commit["triage"] for commit in result["commits"]}, {"review-no-watched-path-match"})
        self.assertEqual({commit["applicability"] for commit in result["commits"]}, {"not-assessed"})

    def test_overlapping_paths_are_review_overlap(self) -> None:
        files = ["src/serve/http_server.cpp", "docs/serving.md", "bench/a.cu", "bench/b.cu", "bench/c.cu"]
        result = watch(files, commit_count=1, ahead_by=1)
        self.assertEqual(result["comparison"]["path_triage"], "watched-path-match")
        self.assertEqual(result["commits"][0]["triage"], "review-fix-or-perf-title")
        self.assertEqual(result["commits"][0]["applicability"], "not-assessed")

    def test_cut_commit_list_is_unknown_even_when_file_list_has_no_match(self) -> None:
        result = watch(["docs/guide.md"], commit_count=2, ahead_by=3)
        self.assertEqual(result["verdict"], "unknown")
        self.assertEqual(result["comparison"]["path_triage"], "unknown-truncated")
        self.assertTrue(result["comparison"]["commits_truncated"])

    def test_commit_api_limit_is_conservatively_unknown(self) -> None:
        result = watch(["docs/guide.md"], commit_count=250, ahead_by=250)
        self.assertEqual(result["comparison"]["status"], "unknown")

    def test_unfollowed_compare_pagination_is_unknown(self) -> None:
        result = watch(
            ["docs/guide.md"], commit_count=1, ahead_by=1,
            compare_extra={"_watch_has_next_page": True},
        )
        self.assertEqual(result["comparison"]["status"], "unknown")
        self.assertIn("pagination-incomplete", result["comparison"]["unknown_reasons"])

    def test_unfollowed_commit_files_pagination_is_unknown(self) -> None:
        result = watch(
            ["docs/guide.md"], commit_count=1, ahead_by=1,
            detail={"files": [{"filename": "docs/guide.md"}], "_watch_has_next_page": True},
        )
        self.assertEqual(result["comparison"]["status"], "unknown")
        self.assertEqual(result["comparison"]["path_triage"], "unknown-truncated")
        self.assertEqual(result["commits"][0]["path_triage"], "unknown-truncated")

    def test_commit_files_at_limit_are_unknown(self) -> None:
        result = watch(
            ["docs/guide.md"], commit_count=1, ahead_by=1,
            detail={"files": [{"filename": f"docs/{i}.md"} for i in range(300)]},
        )
        self.assertEqual(result["comparison"]["status"], "unknown")
        self.assertEqual(result["commits"][0]["triage"], "review-incomplete-evidence")

    def test_diverged_comparison_is_unknown(self) -> None:
        result = watch(
            [], commit_count=1, ahead_by=1,
            compare_extra={"status": "diverged"},
        )
        self.assertEqual(result["comparison"]["status"], "unknown")

    def test_missing_compare_files_are_unknown(self) -> None:
        head = {"sha": "b" * 40, "commit": {"committer": {"date": "2026-11-12T00:00:00Z"}}}
        compare = {"status": "ahead", "ahead_by": 0, "total_commits": 0, "commits": []}
        with mock.patch.object(WATCH, "gh_api", side_effect=[head, compare]):
            result = WATCH.watch_one(ENTRY, False, WATCH.incorporated_baseline(ENTRY, {}))
        self.assertEqual(result["comparison"]["status"], "unknown")
        self.assertIn("comparison-lists-missing", result["comparison"]["unknown_reasons"])

    def test_commits_keep_full_identities(self) -> None:
        result = watch(["docs/guide.md"], commit_count=3, ahead_by=3)
        self.assertEqual([commit["sha"] for commit in result["commits"]], [f"{i:040x}" for i in range(3)])
        with self.assertRaisesRegex(ValueError, "full 40-hex"):
            WATCH.full_commit("12345678")

    def test_github_read_retains_pagination_boundary(self) -> None:
        response = subprocess.CompletedProcess(
            [], 0,
            'HTTP/2.0 200 OK\r\nLink: <https://api.github.com/next>; rel="next"\r\n\r\n{"files": []}\n',
            "",
        )
        with mock.patch.object(WATCH.subprocess, "run", return_value=response) as run:
            result = WATCH.gh_api("repos/example/engine/commits/" + "a" * 40)
        self.assertTrue(result["_watch_has_next_page"])
        self.assertEqual(run.call_args.args[0][:3], ["gh", "api", "--include"])


class CompositionTest(unittest.TestCase):
    def test_real_composition_locks_current_client_and_all_runtime_lanes(self) -> None:
        composition = WATCH.load_composition(ROOT)
        inventory = json.loads((ROOT / "upstream-watch.json").read_text(encoding="utf-8"))
        entries = {entry["id"]: entry for entry in inventory["upstreams"]}
        client = WATCH.incorporated_baseline(entries["oh-my-pi-client"], composition)
        engine = WATCH.incorporated_baseline(entries["ninfer-5090"], composition)
        authority = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / composition["manifest"]).read_text(encoding="utf-8"))
        components = manifest["components"]
        self.assertEqual(composition["product_release"], authority["product_release"])
        self.assertEqual(client["version"], components["omp"]["distribution_version"])
        self.assertEqual(client["tag"], components["omp"]["upstream_tag"])
        self.assertEqual(client["commit"], components["omp"]["upstream_commit"])
        self.assertEqual(engine["commit"], components["ninfer"]["upstream_commit"])
        self.assertEqual(engine["fork"]["commit"], components["ninfer"]["source_commit"])
        self.assertEqual(
            [(variant["id"], variant["commit"], variant["tag"]) for variant in composition["engine"]["variants"]],
            [(variant["id"], variant["source_commit"], variant["release_tag"])
             for variant in components["ninfer_variants"]],
        )
        for entry in (entries["oh-my-pi-client"], entries["ninfer-5090"]):
            self.assertNotIn("fork_point", entry)
            self.assertEqual(WATCH.incorporated_baseline(entry, composition)["status"], "derived")

    def test_authority_selects_composed_release_not_newest_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "compatibility.json").write_text('{"product_release": "v1.0.0"}', encoding="utf-8")
            release = root / "releases" / "v1.0.0"
            release.mkdir(parents=True)
            (root / "releases" / "v2.0.0").mkdir()
            manifest = {
                "release": "v1.0.0",
                "components": {
                    "omp": {
                        "upstream_repository": "https://github.com/example/client",
                        "upstream_commit": "c" * 40, "upstream_tag": "v20.0.0",
                        "distribution_version": "20.0.0",
                    },
                    "ninfer": {
                        "repository": "https://github.com/example/fork",
                        "source_commit": "d" * 40, "upstream_commit": "e" * 40,
                        "release_tag": "engine-v1",
                    },
                },
            }
            (release / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            composition = WATCH.load_composition(root)
        self.assertEqual(composition["client"]["commit"], "c" * 40)
        self.assertEqual(composition["engine"]["commit"], "d" * 40)
        self.assertEqual(composition["manifest"], "releases/v1.0.0/manifest.json")

    def test_unmapped_watches_keep_declared_base_without_adoption_claim(self) -> None:
        baseline = WATCH.incorporated_baseline(ENTRY, WATCH.load_composition(ROOT))
        self.assertEqual(baseline["commit"], ENTRY["fork_point"])
        self.assertEqual(baseline["status"], "declared-not-derived")
        self.assertIn("not established", baseline["role"])


class ObservationTest(unittest.TestCase):
    def setUp(self) -> None:
        inventory = json.loads((ROOT / "upstream-watch.json").read_text(encoding="utf-8"))
        self.entry = next(entry for entry in inventory["upstreams"] if entry["id"] == "oh-my-pi-client")
        self.baseline = WATCH.incorporated_baseline(self.entry, WATCH.load_composition(ROOT))
        self.release_tag = "v18.18.7"
        self.release_commit = self.baseline["commit"]
        self.head = "f" * 40

    def api(self, path: str) -> dict[str, Any]:
        prefix = "repos/can1357/oh-my-pi/"
        if path == prefix + "commits/main":
            return {"sha": self.head, "commit": {"committer": {"date": "2026-11-12T00:00:00Z"}}}
        if path == prefix + "releases/latest":
            return {"tag_name": self.release_tag, "id": 123, "published_at": "2026-11-12T00:00:00Z"}
        if path == prefix + "commits/" + self.release_tag:
            return {"sha": self.release_commit}
        if path == prefix + f"compare/{self.baseline['commit']}...{self.head}":
            return {
                "status": "ahead", "ahead_by": 1, "total_commits": 1,
                "commits": [{
                    "sha": self.head,
                    "commit": {"message": "fix: example", "committer": {"date": "2026-11-12T00:00:00Z"}},
                }],
                "files": [{"filename": "packages/ai/client.ts"}],
            }
        raise AssertionError(f"unexpected API path {path}")

    def test_new_release_moves_last_seen_without_moving_incorporated(self) -> None:
        with mock.patch.object(WATCH, "gh_api", self.api):
            first = WATCH.watch_one(self.entry, False, self.baseline)
            self.release_tag, self.release_commit = "v99.0.0", "d" * 40
            second = WATCH.watch_one(self.entry, False, self.baseline, first)
        self.assertEqual(first["incorporated"], second["incorporated"])
        self.assertEqual(second["incorporated"]["tag"], self.baseline["tag"])
        self.assertEqual(second["last_seen"]["latest_release"]["tag"], "v99.0.0")
        self.assertEqual(second["last_seen"]["latest_release"]["commit"], "d" * 40)
        self.assertEqual(second["observation"], "changed")
        self.assertNotEqual(first["evidence_identity"], second["evidence_identity"])

    def test_second_cli_receipt_has_identical_evidence_despite_new_run_time(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "receipt.json"
            argv = ["upstream_watch.py", "--only", self.entry["id"], "--receipt", str(receipt)]
            with (
                mock.patch.object(WATCH, "gh_api", self.api),
                mock.patch("sys.argv", argv),
                mock.patch.object(WATCH.dt, "datetime") as clock,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                clock.now.return_value.strftime.side_effect = ["2026-11-12T01:00:00Z", "2026-11-12T02:00:00Z"]
                self.assertEqual(WATCH.main(), 0)
                first = json.loads(receipt.read_text(encoding="utf-8"))
                self.assertEqual(WATCH.main(), 0)
                second = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertNotEqual(first["generated_utc"], second["generated_utc"])
        self.assertEqual(first["evidence_identity"], second["evidence_identity"])
        self.assertEqual(first["upstreams"][0]["evidence_identity"], second["upstreams"][0]["evidence_identity"])
        self.assertEqual(second["upstreams"][0]["observation"], "unchanged")

    def test_identical_head_needs_no_compare_and_is_complete(self) -> None:
        self.head = self.baseline["commit"]
        with mock.patch.object(WATCH, "gh_api", self.api):
            result = WATCH.watch_one(self.entry, False, self.baseline)
        self.assertEqual(result["verdict"], "up-to-date")
        self.assertEqual(result["comparison"]["status"], "complete")
        self.assertEqual(result["comparison"]["ahead_by"], 0)
        self.assertEqual(result["commits"], [])


if __name__ == "__main__":
    unittest.main()
