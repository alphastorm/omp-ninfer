"""The upstream watch must not read an API-truncated delta as having no path overlap."""
from __future__ import annotations

import importlib.util
import json
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
    "fork_point": "a" * 40,
    "overlap_paths": ["src/serve/", "src/runtime/engine/"],
}


def watch(files: list[str], commit_count: int, ahead_by: int) -> dict[str, Any]:
    commits = [
        {"sha": f"{i:040x}", "commit": {"message": f"fix(ops): change {i}", "committer": {"date": "2026-09-23T00:00:00Z"}}}
        for i in range(commit_count)
    ]

    def gh_api(path: str) -> Any:
        if path.startswith("repos/example/engine/commits/"):
            return {"sha": "b" * 40, "commit": {"committer": {"date": "2026-09-23T00:00:00Z"}}}
        if path.startswith("repos/example/engine/compare/"):
            return {"ahead_by": ahead_by, "commits": commits, "files": [{"filename": name} for name in files]}
        raise AssertionError(f"unexpected API path {path}")

    with mock.patch.object(WATCH, "gh_api", gh_api):
        return WATCH.watch_one(ENTRY, per_commit_files=False)


class UpstreamWatchTest(unittest.TestCase):
    def test_product_watch_tracks_named_sources_and_same_base_adoption(self) -> None:
        entries = json.loads((ROOT / "upstream-watch.json").read_text())["upstreams"]
        self.assertEqual(len({entry["id"] for entry in entries}), len(entries))
        sources = {entry["upstream"]: entry for entry in entries}
        for repository, ref, base in (
            ("Wallawalla47/ninfer-custom", "master", "81c8ce09"),
            ("gzenz/ninfer", "master", "d44ab584"),
            ("hyz615/RUR1NINFER", "codex/xgrammar-structured-output", "79d2296"),
            ("ashalliants/ninfer-3090", "master", "64d10fbf"),
        ):
            with self.subTest(repository=repository):
                entry = sources[repository]
                self.assertEqual(entry["upstream_ref"], ref)
                self.assertRegex(entry["fork_point"], r"^[0-9a-f]{40}$")
                self.assertTrue(entry["fork_point"].startswith(base))
                self.assertIn("src/", entry["overlap_paths"])
                # Each real entry drives the existing planner's exact compare baseline.
                with mock.patch.object(WATCH, "gh_api", return_value={
                    "sha": entry["fork_point"], "commit": {"committer": {"date": "2026-10-26T00:00:00Z"}}}):
                    self.assertEqual(WATCH.watch_one(entry, False)["verdict"], "up-to-date")
        self.assertEqual(sources["ashalliants/ninfer-3090"]["adoption_role"], "same-base-source")

    def test_cut_file_list_is_unknown_overlap_not_a_pull_candidate(self) -> None:
        # The API lists the first 300 paths alphabetically; the overlapping src/ paths come later.
        files = [f"bench/ops/case_{i:03d}.cu" for i in range(WATCH.API_FILE_LIMIT)]
        result = watch(files, commit_count=250, ahead_by=402)
        self.assertEqual(result["aggregate_overlap"], "unknown-truncated")
        self.assertTrue(result["files_truncated"])
        self.assertTrue(result["commits_truncated"])
        self.assertEqual((result["commits_listed"], result["ahead_by"]), (250, 402))
        self.assertNotIn("pull-candidate", {commit["recommendation"] for commit in result["commits"]})

    def test_complete_list_without_overlap_still_recommends_a_pull(self) -> None:
        files = [f"bench/ops/case_{i:03d}.cu" for i in range(WATCH.API_FILE_LIMIT - 1)]
        result = watch(files, commit_count=3, ahead_by=3)
        self.assertEqual(result["aggregate_overlap"], "no-direct-path-overlap")
        self.assertFalse(result["files_truncated"])
        self.assertFalse(result["commits_truncated"])
        self.assertEqual({commit["recommendation"] for commit in result["commits"]}, {"pull-candidate"})

    def test_overlapping_paths_are_review_overlap(self) -> None:
        files = ["src/serve/http_server.cpp", "docs/serving.md", "bench/a.cu", "bench/b.cu", "bench/c.cu"]
        result = watch(files, commit_count=1, ahead_by=1)
        self.assertEqual(result["aggregate_overlap"], "review-overlap")
        self.assertEqual(result["commits"][0]["recommendation"], "next-release")


if __name__ == "__main__":
    unittest.main()
