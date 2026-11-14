"""Publication identities use the guide engine without manufacturing release prose."""
from __future__ import annotations

import contextlib
import difflib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("flip_docs", ROOT / "scripts" / "flip_docs.py")
assert SPEC is not None and SPEC.loader is not None
FLIP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = FLIP
SPEC.loader.exec_module(FLIP)
ENGINE = FLIP.engine
from release_io import atomic_write, atomic_write_json

OLD, NEW = "v0.20.0", "v0.21.0"
TAG = "v1.0.0-qwen38-5090-beta.1"
NATIVE = "v1.0.0-qwen38-4090-beta.1"
# Reviewed historical layouts, not production heuristics. These pages interleave records
# with later living sections, so no one-line Records boundary can be inserted honestly.
INTERLEAVED_HISTORY = {
    "ROADMAP.md": ("## Deferred and rejected decisions", "## Path to v1.0"),
    "docs/BENCHMARKS.md": ("## Historical measurements", "## Model quality at this quantization"),
    "docs/PERFORMANCE.md": (
        "## v0.18.0 unified F4 runtime re-cut, RTX 3090 `tc` selection, and acceptance boundary",
        "## Current state",
    ),
    "docs/RELEASES.md": (
        "## v0.18.0 — unified engine native re-cut and stock OMP 18.18.7", "## Channels"),
    "docs/UPSTREAM.md": ("## v0.18.0 runtime and client binding", "## Running the watch"),
}
# Exact identity-line exceptions in the two immutable historical trees. Reasons are part
# of the fixture: no paragraph or input is hidden from the inventory comparison.
HISTORY_DIFFERENCES = {
    "BRAND.md": ("authored-state-or-results", (45,), ()),
    "CHANGELOG.md": ("authored-state-or-results", (41, 43), ()),
    "README.md": ("atomic-ambiguity",
                  (9, 10, 12, 18, 81, 82, 83, 116, 121, 123, 124, 127, 129, 130, 131, 132,
                   133, 139, 140, 150, 151, 159, 160, 161, 163, 164, 167, 181, 189, 244),
                  (10, 18, 92, 116, 119, 120, 126, 214)),
    "ROADMAP.md": ("authored-state-or-results;interleaved-legacy-layout",
                   (28, 37, 43, 44, 45, 52, 53, 56, 59, 60, 64, 65, 83, 86, 89, 92, 94, 95,
                    96, 97, 100, 102, 119, 123, 125, 126, 128, 132, 134, 170, 172, 173, 174,
                    175, 193, 204, 208, 311, 312, 353, 368, 520),
                   (40, 41, 45, 46, 76, 77, 78, 97, 109, 164, 171, 186, 274, 275, 277, 283,
                    285, 286, 288, 290, 362, 515, 870, 1013)),
    "assets/benchmarks.html": ("authored-state-or-results", (23,), ()),
    "docs/BENCHMARKS.md": ("authored-results;interleaved-legacy-layout",
                           (18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 29, 30, 31, 32, 34, 37, 38,
                            41, 56, 59, 60, 64, 65, 66, 67, 68, 71, 72, 77, 281, 311, 312, 319,
                            320, 321, 1473, 1505, 1510),
                           (19, 20, 22, 23, 25, 32, 33, 34, 35, 53, 54, 55, 56, 57, 60, 61, 67,
                            70, 74, 75, 88, 90, 91, 92, 95, 332, 341, 1493)),
    "docs/FACTS.md": ("atomic-ambiguity;new-identity-rows;evidence-link-review",
                      (3, 9, 10, 11, 57, 66, 71, 72, 73, 74, 76, 77, 78, 79, 80, 81, 83, 84, 85,
                       86, 89, 90, 91, 96, 100, 102, 107, 111, 112, 113, 114, 126, 130, 131, 145,
                       146, 156, 158, 159, 160, 161, 163, 164, 166, 168, 174, 175, 176, 189, 191,
                       193, 195, 196, 200, 205, 207, 209, 210, 212, 215, 217, 218, 221, 224, 226,
                       228, 230, 245, 248, 250, 251, 252, 256, 258, 290, 291, 292, 378, 384, 389,
                       391, 597, 599, 628, 631, 647, 650, 656, 676, 685, 689, 690, 716),
                      (11, 56, 58, 61, 66, 70, 77, 78, 79, 80, 82, 97, 101, 102, 103, 104, 119,
                       123, 129, 141, 142, 152, 153, 188, 194, 195, 197, 198, 227, 369, 370, 386,
                       652, 691, 692)),
    "docs/PERFORMANCE.md": ("authored-state-or-results;interleaved-legacy-layout",
                            (340, 342, 343, 354, 355, 356, 358, 364, 365, 367, 369, 370, 371, 372,
                             373, 375, 376, 377, 378, 381, 382, 384, 385, 2956),
                            (28, 29, 34, 35, 36, 44, 61, 72, 392, 396, 408, 409, 412, 413, 418, 427,
                             429, 434, 435, 436, 447, 518, 525, 526, 571, 2904, 2910, 3020, 3024,
                             3034, 3039)),
    "docs/RELEASES.md": ("atomic-ambiguity;new-identity-rows;interleaved-legacy-layout",
                         (19, 29, 755),
                         (20, 25, 31, 32, 33, 36, 41, 42, 43, 44, 45, 46, 49, 56, 57, 58, 65, 66,
                          80, 81, 82, 86, 99, 829, 865, 869, 870, 872, 874, 875, 881, 883, 885, 887,
                          888, 889, 894, 917, 919, 920, 921, 922, 923, 924, 925, 927, 928, 929, 930,
                          932, 965, 966, 967, 968, 974, 976, 978, 983, 986, 988, 991)),
    "docs/UPSTREAM.md": ("atomic-ambiguity;new-identity-rows;interleaved-legacy-layout",
                         (5, 13, 15, 16, 17, 18, 952, 1221, 1283, 1284),
                         (5, 15, 16, 17, 18, 43, 44, 46, 47, 52, 53, 54, 56, 58, 62, 68, 73, 74, 77,
                          988, 992, 993, 995, 1012, 1344, 1346, 1347)),
    "llms.txt": ("authored-state-or-results",
                 (9, 10, 19, 23, 24, 25, 31, 39, 40, 53, 54), (19, 28, 43)),
    "site/benchmarks/index.html": ("atomic-ambiguity;authored-results",
                                   (28, 46, 61, 63, 76, 79, 83, 86, 90, 93, 102),
                                   (47, 62, 75, 78, 82, 85, 89, 92, 101)),
    "site/compare/index.html": ("authored-state-or-results", (28, 61), ()),
    "site/index.html": ("authored-state-or-results",
                        (30, 73, 74, 126, 129, 132, 135, 138, 141, 231),
                        (74, 126, 129, 132, 135, 138, 141, 231)),
    "site/llms.txt": ("authored-state-or-results",
                      (9, 10, 19, 23, 24, 25, 31, 39, 40, 53, 54), (19, 28, 43)),
    "site/security/index.html": ("authored-state-or-results", (28, 61, 93, 95), (93, 95)),
    "site/status/index.html": ("authored-state-or-results;new-identity-rows",
                               (28, 58, 59, 62, 68, 72, 73, 74, 85, 87, 88, 92, 93, 94, 95, 99, 100,
                                101, 102, 115, 116, 118, 127, 128, 129),
                               (58, 59, 61, 64, 71, 72, 73, 76, 84, 86, 87, 91, 92, 93, 94, 98, 99,
                                101, 117, 119, 126, 127)),
}
HISTORY_INVENTORIES = {
    "BRAND.md": (("v0.18.0",), ()),
    "CHANGELOG.md": (("v0.18.0",), ()),
    "README.md": (("18.18.7", "48c8ac46", "https://github.com/can1357/oh-my-pi/releases/tag/v18.18.7",
                   "native-v0.8.0-beta.3-rtx4090", "native-v0.8.0-beta.3-tc-rtx3090", "v0.17.0",
                   "v0.7.0-qwen38-5090-beta.7", "v0.8.0-qwen38-3090-beta.3"), ()),
    "ROADMAP.md": (("48c8ac4644322f024b5c3bd5b657af5874567251", "531c5ed1", "674d5260",
                    "763178cb", "9ba2abe1f1dd7c64b8d3f99dc0e41d689d96886c", "9bd9fd74",
                    "cf77a595", "e7ac3ab7"), ()),
    "assets/benchmarks.html": (("v0.18.0",), ()),
    "docs/BENCHMARKS.md": (("440868478", "48c8ac4644322f024b5c3bd5b657af5874567251", "674d5260",
                            "804ef8ac", "checkpoints-v018", "e325ffc7", "e5713286",
                            "qwen38-3090-native-v0.8.0-beta.3"), ("763178cb", "e7ac3ab7")),
    "docs/FACTS.md": (("0cecaac7", "1,011,087,765", "12,877,499", "1f935ae2", "221,982,864",
                       "250,108,928", "269941ec", "286,136,496", "440868478",
                       "48c8ac4644322f024b5c3bd5b657af5874567251", "4a6e39ea", "580,020,196",
                       "674d5260", "7ced9ab1", "823d9357", "8ac165c5", "9ba2abe1",
                       "9ba2abe1f1dd7c64b8d3f99dc0e41d689d96886c", "e325ffc7",
                       "e325ffc73ab86e03bdd20a91b77d8e2b3964c906", "ea6c216f",
                       "measurements/2026-11-12-v0180-acceptance-restoration.json",
                       "qwen38-3090-native-v0.8.0-beta.3", "v0.7.0-qwen38-5090-runtime-beta.7",
                       "v18.18.7"), ()),
    "docs/PERFORMANCE.md": (("674d5260", "checkpoints-v018", "qwen38-3090-native-v0.8.0-beta.3"), ()),
    "docs/RELEASES.md": ((), ("4ad1f5e8", "60a1d35d", "8d18d8fa", "ac41700a")),
    "docs/UPSTREAM.md": (("531c5ed1", "580,020,196", "674d5260", "763178cb", "823d9357", "e7ac3ab7"), ()),
    "llms.txt": (("18.18.7", "674d5260", "bf1ceaa9", "e325ffc7", "e5713286",
                  "https://github.com/alphastorm/ninfer", "native-v0.8.0-beta.3-tc-rtx3090",
                  "qwen38-3090-native-v0.8.0-beta.3"), ()),
    "site/benchmarks/index.html": (("18.18.7", "674d5260", "804ef8ac", "bf1ceaa9", "e5713286",
                                    "native-v0.8.0-beta.3-tc-rtx3090", "qwen38-3090-native-v0.8.0-beta.3",
                                    "v0.7.0-qwen38-5090-beta.7", "v0.8.0-qwen38-3090-beta.3"), ()),
    "site/compare/index.html": (("18.18.7", "v0.18.0"), ()),
    "site/index.html": (("18.18.7", "v0.7.0-qwen38-5090-beta.7", "v0.8.0-qwen38-3090-beta.3"), ()),
    "site/llms.txt": (("18.18.7", "674d5260", "bf1ceaa9", "e325ffc7", "e5713286",
                       "https://github.com/alphastorm/ninfer", "native-v0.8.0-beta.3-tc-rtx3090",
                       "qwen38-3090-native-v0.8.0-beta.3"), ()),
    "site/security/index.html": (("18.18.7", "checkpoints-v018", "v0.18.0"), ()),
    "site/status/index.html": (("0cecaac7", "1,011,087,765", "18.18.7", "269941ec", "4a6e39ea",
                                "674d5260", "804ef8ac", "8ac165c5", "bf1ceaa9", "checkpoints-v018",
                                "e325ffc7", "e5713286", "ea6c216f", "https://github.com/alphastorm/ninfer",
                                "native-v0.8.0-beta.3-tc-rtx3090", "qwen38-3090-native-v0.8.0-beta.3",
                                "v0.7.0-qwen38-5090-beta.7"), ()),
}
HISTORY_REFUSALS = {
    "README.md": (124, "48c8ac46"),
    "docs/FACTS.md": (111, "e325ffc7"),
    "docs/RELEASES.md": (126, "440868478"),
    "docs/UPSTREAM.md": (1295, "e325ffc7"),
    "site/benchmarks/index.html": (121, "48c8ac46"),
}


@contextlib.contextmanager
def historical_records(path: Path, heading: str | None):
    """An explicitly reviewed, single-boundary historical fixture adapter."""
    if heading is None:
        yield
        return
    original = path.read_text(encoding="utf-8")
    marker = heading + "\n"
    if original.count(marker) != 1 or "## Records\n" in original:
        raise AssertionError("historical record boundary must be exact and unique")
    position = original.index(marker)
    tail = original[position:]
    atomic_write(path, original[:position] + "## Records\n" + tail)
    try:
        yield
    finally:
        changed = path.read_text(encoding="utf-8")
        if changed.count("## Records\n") != 1:
            raise AssertionError("exactly one historical Records line must be removed")
        before, separator, after = changed.partition("## Records\n")
        if not separator or after != tail:
            raise AssertionError("historical record bytes changed")
        atomic_write(path, before + after)


def declared_release() -> str:
    """The release the living pages describe; it trails the authority while a release is staged."""
    text = (ROOT / "docs" / "RELEASES.md").read_text(encoding="utf-8")
    section = text.split("\n## Current release\n", 1)[1].split("\n## ", 1)[0]
    match = re.search(r"(?<![\w.-])v\d+\.\d+\.\d+(?![\w-]|\.\d)", section)
    assert match is not None, "docs/RELEASES.md must name its current release"
    return match[0]


def manifest(release: str, successor: bool = False) -> dict:
    return {
        "release": release, "status": "ready",
        "components": {
            "omp": {
                "upstream_tag": "v18.2.0" if successor else "v18.1.0",
                "distribution_version": "18.2.0" if successor else "18.1.0",
                "artifact_name": "client-new.zip" if successor else "client-old.zip",
                "artifact_sha256": ("e" if successor else "d") * 64,
                "artifact_bytes": 31_000_000 if successor else 30_000_000,
                "release_id": 441_000_000 if successor else 440_000_000,
            },
            "ninfer": {
                "release_tag": TAG[:-1] + ("2" if successor else "1"),
                "source_commit": ("b" if successor else "a") * 40,
                "server_binary_sha256": ("6" if successor else "5") * 64,
            },
            "ninfer_variants": [{
                "id": "rtx4090-windows-native",
                "release_tag": NATIVE[:-1] + ("2" if successor else "1"),
                "source_commit": ("c" if successor else "a") * 40,
                "build_profile": "native-new" if successor else "native-old",
            }],
            "model": {"artifact_sha256": "f" * 64},
        },
    }


def declaration(pages: tuple[str, ...]) -> str:
    rows = "\n".join(f"| `{page}` | Current identities |" for page in pages)
    return ("# Releases\n\n## After publication\n\n| Page | Edit |\n| --- | --- |\n"
            + rows + "\n\n## Records\n\nRelease `v0.10.0` passed.\n")


class FlipDocsTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.before, self.after = manifest(OLD), manifest(NEW, True)
        self.write_releases()
        self.pages("docs/FACTS.md")
        self.write("docs/FACTS.md", f"# Facts\n\nVersion `{OLD}`.\n")

    def write(self, page: str, text: str) -> None:
        atomic_write(self.root / page, text)

    def pages(self, *pages: str) -> None:
        self.write("docs/RELEASES.md", declaration(tuple(pages)))
        for page in pages:
            if "*" not in page and not (self.root / page).exists():
                self.write(page, "# Page\n")

    def write_releases(self) -> None:
        for release, document in ((OLD, self.before), (NEW, self.after)):
            directory = self.root / "releases" / release
            atomic_write_json(directory / "manifest.json", document)
            atomic_write_json(directory / "compatibility.json", {"product_release": release})
            atomic_write_json(directory / "profiles" / "example.json", {
                "release": release,
                "server": {"checkpoint_host_directory": ENGINE.checkpoint_name(release),
                           "checkpoint_mount_target": "/checkpoints-v013"},
            })

    def flip(self, *, check: bool = False):
        return FLIP.flip(self.root, OLD, NEW, check=check)

    def test_owner_table_drives_files_globs_and_combined_cells(self) -> None:
        self.write("docs/RELEASES.md",
                   "# Releases\n\n## After publication\n\n| Page | Edit |\n| --- | --- |\n"
                   "| `README.md` and `BRAND.md` | Identity tokens |\n"
                   "| `site/**/*.html` | Identity tokens |\n\n## Records\n| `ignored.md` | Old |\n")
        for page in ("README.md", "BRAND.md", "site/index.html", "site/nested/index.html"):
            self.write(page, f"Version {OLD}.\n")
        self.write("ignored.md", f"Version {OLD}.\n")
        self.assertEqual({path.relative_to(self.root).as_posix() for path in FLIP.publication_pages(self.root)},
                         {"README.md", "BRAND.md", "site/index.html", "site/nested/index.html"})
        self.flip()
        self.assertEqual((self.root / "ignored.md").read_text(encoding="utf-8"), f"Version {OLD}.\n")

    def test_missing_declaration_is_a_refusal_not_a_fallback_list(self) -> None:
        self.write("docs/RELEASES.md", "# Releases\n")
        with self.assertRaisesRegex(ENGINE.Refusal, "missing After publication"):
            self.flip()

    def test_candidate_guide_and_authorities_cannot_be_declared_living_pages(self) -> None:
        for page in ("docs/QUICKSTART.md", "compatibility.json", "releases/v0.20.0/manifest.json"):
            with self.subTest(page=page):
                self.pages(page)
                with self.assertRaisesRegex(ENGINE.Refusal, "release-candidate authority"):
                    self.flip()

    def test_scoped_prefixes_full_identities_and_numbers_retarget_once(self) -> None:
        self.write("docs/FACTS.md",
                   f"# Facts\n\nVersion `{OLD}`.\n\n"
                   f"| RTX 5090 | `{TAG}` | `{'a' * 40}` | `{'a' * 8}` | `{'a' * 12}` |\n"
                   f"| RTX 4090 | `{NATIVE}` | `{'a' * 8}` | native-old |\n"
                   "| Client | client-old.zip | dddddddd | dddddddddddd | 30000000 | 30,000,000 | 440000000 | 440,000,000 |\n")
        result = self.flip()
        self.assertEqual(result.issues, ())
        value = (self.root / "docs/FACTS.md").read_text(encoding="utf-8")
        self.assertIn(f"`{TAG[:-1]}2` | `{'b' * 40}` | `{'b' * 8}` | `{'b' * 12}`", value)
        self.assertIn(f"`{NATIVE[:-1]}2` | `{'c' * 8}` | native-new", value)
        self.assertIn("client-new.zip | eeeeeeee | eeeeeeeeeeee | 31000000 | 31,000,000 | 441000000 | 441,000,000", value)
        self.assertEqual(result.statistics, (FLIP.PageStatistics("docs/FACTS.md", 15, 0),))
        self.assertEqual(self.flip().changed, ())
        self.assertEqual(self.flip(check=True).issues, ())

    def test_prefix_collision_between_components_requires_the_original_block_anchor(self) -> None:
        self.before["components"]["ninfer"]["source_commit"] = "12345678" + "a" * 32
        self.before["components"]["ninfer_variants"][0]["source_commit"] = "12345678" + "b" * 32
        self.write_releases()
        self.write("docs/FACTS.md", f"Version {OLD}.\n\nSource `12345678`.\n")
        original = (self.root / "docs/FACTS.md").read_bytes()
        result = self.flip()
        self.assertEqual(result.issues[0].kind, "refused")
        self.assertIn("refusal (a)", result.issues[0].detail)
        self.assertEqual((self.root / "docs/FACTS.md").read_bytes(), original)

    def test_later_page_refusal_writes_none_of_the_declared_pages(self) -> None:
        self.pages("README.md", "docs/FACTS.md")
        self.write("README.md", f"Version {OLD}.\r\n")
        self.write("docs/FACTS.md", f"Version {OLD}.\n\nSource `aaaaaaaa`.\n")
        before = {path: path.read_bytes() for path in FLIP.publication_pages(self.root)}
        result = self.flip()
        self.assertTrue(any(issue.kind == "refused" for issue in result.issues))
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        self.assertEqual(result.changed, ())

    def test_failed_post_write_validation_restores_every_original_page(self) -> None:
        self.pages("README.md", "docs/FACTS.md")
        self.write("README.md", f"Version {OLD}.\r\n")
        self.write("docs/FACTS.md",
                   f"Version {OLD}.\n\nRelease {NEW}: acceptance is pending.\n")
        before = {path: path.read_bytes() for path in FLIP.publication_pages(self.root)}
        validate = FLIP.validate_release_documentation

        def validate_written_pages(root, release, errors):
            for path in before:
                self.assertIn(f"Version {NEW}.", path.read_text(encoding="utf-8"))
            validate(root, release, errors)

        with mock.patch.object(FLIP, "validate_release_documentation", side_effect=validate_written_pages):
            result = self.flip()
        self.assertTrue(any(issue.kind == "stale release state" for issue in result.issues))
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        self.assertEqual(result.changed, ())

    def test_prefix_used_as_an_unrelated_token_is_not_silently_rewritten(self) -> None:
        self.write("docs/FACTS.md", f"Version {OLD}.\n\nUnrelated token `dddddddd`.\n")
        result = self.flip()
        self.assertEqual(result.issues[0].kind, "refused")
        self.assertIn("block anchors: none", result.issues[0].detail)

    def test_prefix_equal_to_another_leafs_full_value_is_ambiguous(self) -> None:
        self.before["components"]["omp"]["artifact_sha256"] = "deadbeef" + "d" * 56
        self.after["components"]["omp"]["artifact_sha256"] = "12345678" + "e" * 56
        self.before["components"]["ninfer"]["deployment_profile"] = "deadbeef"
        self.after["components"]["ninfer"]["deployment_profile"] = "container-new"
        self.write_releases()
        self.write("docs/FACTS.md", f"Version {OLD}.\n\nToken deadbeef.\n")
        self.assertEqual(self.flip().issues[0].kind, "refused")
        self.write("docs/FACTS.md", f"Version {OLD}.\n\n| RTX 5090 | deadbeef |\n| Client | client-old.zip | deadbeef |\n")
        self.assertEqual(self.flip().issues, ())
        text = (self.root / "docs/FACTS.md").read_text(encoding="utf-8")
        self.assertIn("| RTX 5090 | container-new |", text)
        self.assertIn("| Client | client-new.zip | 12345678 |", text)

    def test_projections_are_whole_tokens_not_hex_or_numeric_substrings(self) -> None:
        self.write("docs/FACTS.md", f"Version {OLD}.\n\n"
                   "| Client | client-old.zip | ddddddd | ddddddddf | dddddddd.suffix | xdddddddd | 300000001 | 30,000,000,001 |\n")
        self.assertEqual(self.flip().issues, ())
        value = (self.root / "docs/FACTS.md").read_text(encoding="utf-8")
        self.assertIn("ddddddd | ddddddddf | dddddddd.suffix | xdddddddd | 300000001 | 30,000,000,001", value)

    def test_small_integers_and_measured_counts_are_not_projected(self) -> None:
        self.before["components"]["omp"].update(artifact_bytes=999_999, prompts=30_000_000)
        self.after["components"]["omp"].update(artifact_bytes=888_888, prompts=31_000_000)
        self.write_releases()
        self.write("docs/FACTS.md", f"Version {OLD}.\n\n| Client | client-old.zip | 999999 |\n"
                   "\nMeasured 30000000 prompts at 181.71 tok/s.\n")
        result = self.flip()
        self.assertTrue(any(issue.kind == "needs authoring" for issue in result.issues))
        value = (self.root / "docs/FACTS.md").read_text(encoding="utf-8")
        self.assertIn("| client-new.zip | 999999 |", value)
        self.assertIn("Measured 30000000 prompts at 181.71 tok/s.", value)

    def test_percentages_and_wall_times_are_results_even_if_they_equal_an_identity(self) -> None:
        body = "Client client-old.zip: 30,000,000% across 30000000 s.\n"
        self.write("docs/FACTS.md", f"Version {OLD}.\n\n" + body)
        result = self.flip()
        self.assertTrue(any(issue.kind == "needs authoring" for issue in result.issues))
        self.assertIn(body, (self.root / "docs/FACTS.md").read_text(encoding="utf-8"))

    def test_release_state_and_results_stay_byte_identical_while_tables_flip(self) -> None:
        state = f"Published {OLD}; all 31 blocks passed on 2026-01-01.\n"
        self.write("docs/FACTS.md", "# Facts\n\n" + state + f"\n| RTX 5090 | {TAG} |\n")
        result = self.flip()
        self.assertEqual([(issue.line, issue.kind) for issue in result.issues], [(3, "needs authoring")])
        value = (self.root / "docs/FACTS.md").read_text(encoding="utf-8")
        self.assertIn(state, value)
        self.assertIn(TAG[:-1] + "2", value)
        self.assertEqual(self.flip().changed, ())
        self.assertTrue(self.flip(check=True).issues)

    def test_records_heading_itself_and_everything_below_it_stay_identical(self) -> None:
        records = f"## Records\n\n### {OLD}\n\nRTX 5090 {TAG}; {'a' * 8}; published and passed.\n"
        self.write("docs/FACTS.md", f"Version {OLD}.\n\n" + records)
        result = self.flip()
        self.assertEqual(result.issues, ())
        self.assertTrue((self.root / "docs/FACTS.md").read_text(encoding="utf-8").endswith(records))

    def test_shorter_or_different_fences_do_not_expose_the_records_section(self) -> None:
        records = f"## Records\n\nRTX 5090 {TAG}; {'a' * 8}.\n"
        for opening, literal, closing in (("````", "```", "````"),
                                          ("~~~~", "~~~", "~~~~~"),
                                          ("````", "~~~~", "`````")):
            with self.subTest(opening=opening, literal=literal, closing=closing):
                self.write("docs/FACTS.md",
                           f"Version {OLD}.\n\n{opening}text\n{literal}\n{closing}\n\n" + records)
                result = self.flip()
                self.assertEqual(result.issues, ())
                value = (self.root / "docs/FACTS.md").read_text(encoding="utf-8")
                self.assertIn(f"Version {NEW}.", value)
                self.assertTrue(value.endswith(records))

    def test_reviewed_historical_boundary_inserts_and_removes_exactly_one_line(self) -> None:
        heading = "## Prior release record"
        tail = f"{heading}\n\nPublished {OLD}; RTX 5090 {TAG}.\n"
        self.write("docs/FACTS.md", f"Version {OLD}.\n\n" + tail)
        with historical_records(self.root / "docs/FACTS.md", heading):
            self.assertEqual((self.root / "docs/FACTS.md").read_text(encoding="utf-8").count("## Records\n"), 1)
            self.flip()
        result = (self.root / "docs/FACTS.md").read_text(encoding="utf-8")
        self.assertEqual(result.count("## Records\n"), 0)
        self.assertTrue(result.endswith(tail))
        self.assertIn(NEW, result.split(heading)[0])

    def test_released_changelog_sections_and_tag_definitions_are_immutable(self) -> None:
        self.pages("CHANGELOG.md")
        released = f"## [0.20.0] - 2026-01-01\n\nPassed {OLD}.\n\n[0.20.0]: https://example.invalid/{OLD}\n"
        self.write("CHANGELOG.md", "# Changelog\n\n## [Unreleased]\n\nA neutral entry.\n\n" + released
                   + f"\n[Unreleased]: https://example.invalid/compare/{OLD}...HEAD\n")
        self.flip()
        value = (self.root / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(released, value)
        self.assertIn(f"[Unreleased]: https://example.invalid/compare/{NEW}...HEAD", value)

    def test_pending_request_timeout_is_not_pending_release_work(self) -> None:
        self.write("docs/FACTS.md", f"Version {OLD}.\n\nPending timeout is 180 seconds.\n")
        self.assertFalse(any(issue.kind == "needs authoring" for issue in self.flip().issues))

    def test_previous_distinct_tokens_remain_idempotent_after_partial_authoring(self) -> None:
        prior = manifest("v0.19.0")
        prior["components"]["ninfer"]["release_tag"] = "v0.9.0-qwen38-5090-beta.9"
        atomic_write_json(self.root / "releases" / "v0.19.0" / "manifest.json", prior)
        self.write("docs/FACTS.md", f"Published {OLD}.\n\nVersion {OLD}.\n\n"
                   f"RTX 5090 rollback to {prior['components']['ninfer']['release_tag']}.\n")
        self.flip()
        result = (self.root / "docs/FACTS.md").read_bytes()
        self.flip()
        self.assertEqual((self.root / "docs/FACTS.md").read_bytes(), result)

    def test_unbound_compound_instance_is_reported_not_reconstructed(self) -> None:
        self.before["components"]["ninfer"]["deployment_profile"] = "qwen38-old"
        self.after["components"]["ninfer"]["deployment_profile"] = "qwen38-new"
        self.write_releases()
        self.write("docs/FACTS.md", f"Version {OLD}.\n\nRTX 5090 qwen38-old-aaaaaaaaaaaa.\n")
        result = self.flip()
        self.assertTrue(any("unbound compound identity" in issue.detail for issue in result.issues))
        self.assertIn("qwen38-old-aaaaaaaaaaaa", (self.root / "docs/FACTS.md").read_text(encoding="utf-8"))

    def test_living_evidence_links_are_advisory_and_do_not_block_other_identities(self) -> None:
        self.pages("README.md", "docs/FACTS.md")
        bad = f"Version {OLD}.\n\n[review](measurements/2026-01-01-client-review.json)\n"
        self.write("docs/FACTS.md", bad)
        self.write("README.md", f"Version {OLD}.\n")
        result = self.flip()
        self.assertTrue(any(issue.kind == "review: evidence link" for issue in result.issues))
        self.assertEqual((self.root / "docs/FACTS.md").read_text(encoding="utf-8"), bad.replace(OLD, NEW))
        self.assertEqual((self.root / "README.md").read_text(encoding="utf-8"), f"Version {NEW}.\n")
        with mock.patch.object(FLIP, "ROOT", self.root), contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(FLIP.main(["--from", OLD, "--to", NEW, "--check"]), 0)

    def test_evidence_policy_is_one_shared_guide_or_living_mode(self) -> None:
        text = "[record](measurements/2026-01-01-record.json)\n"
        with self.assertRaisesRegex(ENGINE.Refusal, "unbound evidence link"):
            ENGINE.evidence_diagnostics(text, set(), Path("guide.md"), mode="guide")
        self.assertEqual(ENGINE.evidence_diagnostics(text, set(), Path("facts.md"), mode="living"),
                         [(1, "measurements/2026-01-01-record.json")])

    def test_bound_evidence_link_uses_the_normal_map(self) -> None:
        self.before["review"] = "docs/measurements/2026-01-01-review.json"
        self.after["review"] = "docs/measurements/2026-02-01-review.json"
        self.write_releases()
        self.write("docs/FACTS.md", f"Version {OLD}.\n\n[record](measurements/2026-01-01-review.json)\n")
        self.assertEqual(self.flip().issues, ())
        self.assertIn("measurements/2026-02-01-review.json", (self.root / "docs/FACTS.md").read_text(encoding="utf-8"))

    def test_html_rows_use_scope_and_html_measurements_need_authoring(self) -> None:
        self.pages("site/index.html")
        self.write("site/index.html", f"<h1>Version {OLD}</h1>\n"
                   f"<table>\n<tr><td>RTX 5090</td><td>{TAG}</td><td>aaaaaaaa</td></tr>\n"
                   f"<tr><td>RTX 4090</td><td>{NATIVE}</td><td>aaaaaaaa</td></tr>\n</table>\n"
                   "<p>Measured 181.71 tok/s, all 31 blocks passed.</p>\n")
        result = self.flip()
        self.assertTrue(any(issue.kind == "needs authoring" for issue in result.issues))
        text = (self.root / "site/index.html").read_text(encoding="utf-8")
        self.assertIn("<td>bbbbbbbb</td>", text)
        self.assertIn("<td>cccccccc</td>", text)
        self.assertIn("<p>Measured 181.71 tok/s, all 31 blocks passed.</p>", text)

    def test_html_has_several_bounded_records_and_living_content_after_each(self) -> None:
        self.pages("site/index.html")
        first = f"<!-- records -->\n<h2>{OLD}</h2>\n<!-- /records -->\n"
        second = f"<!-- records -->\n<p>RTX 5090 {TAG}</p>\n<!-- /records -->\n"
        self.write("site/index.html", first + f"<p>Version {OLD}</p>\n" + second + f"<p>Version {OLD}</p>\n")
        self.assertEqual(self.flip().issues, ())
        value = (self.root / "site/index.html").read_text(encoding="utf-8")
        self.assertIn(first, value)
        self.assertIn(second, value)
        self.assertEqual(value.count(f"<p>Version {NEW}</p>"), 2)

    def test_markdown_pairs_keep_worked_precedents_but_not_later_living_text(self) -> None:
        record = f"<!-- records -->\n\n### {OLD} precedent\n\n{TAG}\n\n<!-- /records -->\n"
        example = "\n```html\n<!-- records -->\n```\n\n`<!-- /records -->` is literal code.\n"
        self.write("docs/FACTS.md", record + f"\nVersion {OLD}.\n" + example)
        self.assertEqual(self.flip().issues, ())
        value = (self.root / "docs/FACTS.md").read_text(encoding="utf-8")
        self.assertTrue(value.startswith(record))
        self.assertIn(f"Version {NEW}.", value)
        self.assertIn(example, value)

    def test_invalid_html_record_markers_refuse_with_file_and_line(self) -> None:
        self.pages("site/index.html")
        cases = [
            ("<!-- records -->\n<p>old</p>\n", 1),
            ("<!-- /records -->\n", 1),
            ("<!-- records -->\n<!-- records -->\n<!-- /records -->\n", 2),
            ("<!-- records -->\n<!-- /records -->\n<!-- /records -->\n", 3),
            ("<p><!-- records --></p>\n", 1),
        ]
        for text, line in cases:
            with self.subTest(text=text):
                self.write("site/index.html", text)
                result = self.flip()
                self.assertEqual((result.issues[0].page, result.issues[0].line, result.issues[0].kind),
                                 ("site/index.html", line, "refused"))
                self.assertEqual((self.root / "site/index.html").read_text(encoding="utf-8"), text)

    def test_check_reports_precise_drift_and_never_writes(self) -> None:
        before = (self.root / "docs/FACTS.md").read_bytes()
        with mock.patch.object(FLIP, "ROOT", self.root), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(FLIP.main(["--from", OLD, "--to", NEW, "--check"]), 1)
        self.assertIn("docs/FACTS.md:3: stale identities", out.getvalue())
        self.assertEqual((self.root / "docs/FACTS.md").read_bytes(), before)
        self.flip()
        with mock.patch.object(FLIP, "ROOT", self.root), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(FLIP.main(["--from", OLD, "--to", NEW, "--check"]), 0)

    def test_target_version_does_not_hide_a_stale_client_identity(self) -> None:
        self.write("docs/FACTS.md", f"Version {NEW}.\n\n| Client | client-old.zip | dddddddd |\n")
        result = self.flip(check=True)
        self.assertEqual(result.issues, ())
        self.assertTrue(result.edits)
        self.assertIn("eeeeeeee", result.edits[0].detail)

    def test_new_release_state_does_not_need_to_be_reauthored(self) -> None:
        self.write("docs/FACTS.md", f"Published {NEW}; all 31 blocks passed.\n")
        self.assertEqual(self.flip(check=True).issues, ())

    def test_results_are_advisory_but_verifier_stale_publication_work_fails_check(self) -> None:
        self.write("docs/FACTS.md", f"Published {OLD}; 31 blocks passed.\n")
        with mock.patch.object(FLIP, "ROOT", self.root), contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(FLIP.main(["--from", OLD, "--to", NEW, "--check"]), 0)
        self.write("docs/FACTS.md", f"Release {NEW}: acceptance is pending.\n")
        result = self.flip(check=True)
        self.assertTrue(any(issue.kind == "stale release state" for issue in result.issues))
        with mock.patch.object(FLIP, "ROOT", self.root), contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(FLIP.main(["--from", OLD, "--to", NEW, "--check"]), 1)


class PublicDocumentationTests(unittest.TestCase):
    def test_current_record_layout_cannot_silently_add_old_release_headings(self) -> None:
        release = declared_release()
        predecessor = ENGINE.ready_history(ROOT, release)[0][0]
        previous_distinct = ENGINE.ready_history(ROOT, predecessor)[0][0]
        versions = re.compile(r"(?<![\w.-])v\d+\.\d+\.\d+(?![\w-]|\.\d)")

        def older(title: str) -> bool:
            return any(ENGINE.release_version(match[0]) < ENGINE.release_version(previous_distinct)
                       for match in versions.finditer(title))
        failures = []
        html_results = {}
        for page in FLIP.publication_pages(ROOT):
            text = page.read_text(encoding="utf-8")
            visible = ENGINE.records_mask(text, page)
            page_failures = []
            if page.suffix == ".html":
                for heading in re.finditer(r"<h[1-6]\b[^>]*>(.*?)</h[1-6]>", visible, re.IGNORECASE | re.DOTALL):
                    if older(FLIP.prose(heading[1])):
                        page_failures.append(text.count("\n", 0, heading.start()) + 1)
                html_results[page.relative_to(ROOT).as_posix()] = {
                    "regions": len(ENGINE.immutable_regions(text, page)), "unprotected_headings": page_failures}
            else:
                fences = [block for block in ENGINE.markdown_blocks(visible) if block.fenced]
                for heading in re.finditer(r"^#{1,6}\s+(.+)", visible, re.MULTILINE):
                    if (older(heading[1])
                            and not any(block.start <= heading.start() < block.end for block in fences)):
                        page_failures.append(text.count("\n", 0, heading.start()) + 1)
            failures.extend(f"{page.relative_to(ROOT)}:{line}: older release heading needs records"
                            for line in page_failures)
        print("HTML_FORWARD_GUARD=" + json.dumps(html_results, sort_keys=True))
        self.assertEqual(failures, [])

    def test_historical_site_record_bytes_and_living_verified_paragraph_are_unchanged(self) -> None:
        shallow = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT,
                                 check=True, capture_output=True, text=True).stdout.strip() == "true"
        if shallow:
            if os.environ.get("OMP_NINFER_REQUIRE_HISTORY") == "1":
                self.fail("historical HTML proof requires full git history")
            self.skipTest("historical HTML proof requires full git history")
        commit = subprocess.run(
            ["git", "rev-parse", "--verify", "1d154a6ee697e053f469cc1b78ba771abb29e05f^{commit}"],
            cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
        published = subprocess.run(["git", "show", f"{commit}:site/benchmarks/index.html"],
                                   cwd=ROOT, check=True, capture_output=True).stdout.decode("utf-8")
        page = ROOT / "site" / "benchmarks" / "index.html"
        current = page.read_text(encoding="utf-8")
        regions = ENGINE.immutable_regions(current, page)
        self.assertEqual(len(regions), 1)
        region = current[slice(*regions[0])]
        historical = region.removeprefix("<!-- records -->\n").removesuffix("<!-- /records -->\n")
        self.assertIn(historical, published)
        self.assertEqual(region.count("<!-- records -->"), 1)
        self.assertEqual(region.count("<!-- /records -->"), 1)
        self.assertNotIn('<p class="verified">', region)
        self.assertIn('<p class="verified">All qualification and acceptance receipts',
                      ENGINE.records_mask(current, page))

    def test_llms_mirror_is_identical(self) -> None:
        self.assertEqual((ROOT / "llms.txt").read_bytes(), (ROOT / "site/llms.txt").read_bytes())

    def test_current_tree_checks_every_owned_page_without_writing(self) -> None:
        release = declared_release()
        previous = max((path.parent.name for path in (ROOT / "releases").glob("*/manifest.json")
                        if ENGINE.RELEASE_RE.fullmatch(path.parent.name)
                        and ENGINE.release_version(path.parent.name) < ENGINE.release_version(release)),
                       key=ENGINE.release_version)
        pages = FLIP.publication_pages(ROOT)
        before = {path: path.read_bytes() for path in pages}
        result = FLIP.flip(ROOT, previous, release, check=True)
        print("CURRENT_DOCS_FINDINGS=" + json.dumps([issue._asdict() for issue in result.issues], sort_keys=True))
        for path, data in before.items():
            self.assertEqual(path.read_bytes(), data)
        self.assertFalse(result.edits, "\n".join(map(str, result.edits)))
        self.assertFalse([issue for issue in result.issues if issue.kind == "refused"],
                         "\n".join(map(str, result.issues)))
        for issue in result.issues:
            self.assertIn(issue.kind, {"needs authoring", "review: evidence link"})
            self.assertIn(ROOT / issue.page, pages)
            self.assertGreater(issue.line, 0)

    def test_existing_reference_page_contract_is_not_a_second_publication_list(self) -> None:
        spec = importlib.util.spec_from_file_location("docs_contract", ROOT / "tests" / "test_docs.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        references = set(module.ReleaseNeutralPageTests.PAGES)
        living = {path.relative_to(ROOT).as_posix() for path in FLIP.publication_pages(ROOT)}
        self.assertEqual(references & living, set())

    def test_publication_history_identity_inventories(self) -> None:
        git = lambda *args: subprocess.run(["git", *args], cwd=ROOT, check=True,
                                           capture_output=True).stdout
        if git("rev-parse", "--is-shallow-repository").strip() == b"true":
            if os.environ.get("OMP_NINFER_REQUIRE_HISTORY") == "1":
                self.fail("publication golden requires full git history")
            self.skipTest("publication golden requires full git history")
        source = git("rev-parse", "--verify", "v0.19.0^{commit}").decode().strip()
        published = git("rev-parse", "--verify", "1d154a6ee697e053f469cc1b78ba771abb29e05f^{commit}").decode().strip()
        self.assertRegex(source, r"^[0-9a-f]{40}$")
        self.assertRegex(published, r"^[0-9a-f]{40}$")
        owner = ROOT / "docs" / "RELEASES.md"
        paths = [path.relative_to(ROOT).as_posix() for path in FLIP.publication_pages(ROOT)]
        files = git("ls-tree", "-r", "--name-only", source, "--", "releases").decode().splitlines()
        history = [file for file in files if re.fullmatch(r"releases/v\d+\.\d+\.\d+/manifest\.json", file)
                   and not file.startswith(("releases/v0.18.0/", "releases/v0.19.0/"))]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = git("archive", source, "releases/v0.18.0", "releases/v0.19.0", *history, *paths)
            with tarfile.open(fileobj=io.BytesIO(archive)) as tree:
                for member in tree.getmembers():
                    if member.isfile():
                        stream = tree.extractfile(member)
                        assert stream is not None
                        atomic_write(root / member.name, stream.read())
            original_pages = {page: (root / page).read_bytes() for page in paths}
            # The tag predates the page declaration; the current, single owner is applied
            # as data to both trees. No legacy-record heuristics or input masks are used.
            for page, (record, later_living) in INTERLEAVED_HISTORY.items():
                original = (root / page).read_text(encoding="utf-8")
                self.assertLess(original.index(record + "\n"), original.index(later_living + "\n"))
            with contextlib.ExitStack() as stack:
                for page in paths:
                    # All five historical record-bearing pages interleave later living
                    # sections, as asserted above. No honest single boundary exists.
                    stack.enter_context(historical_records(root / page, None))
                result = FLIP.flip(root, "v0.18.0", "v0.19.0", declaration=owner)
            refused = {issue.page: issue for issue in result.issues if issue.kind == "refused"}
            self.assertEqual(set(refused), set(HISTORY_REFUSALS))
            for page, (line, token) in HISTORY_REFUSALS.items():
                self.assertEqual(refused[page].line, line)
                self.assertIn(repr(token), refused[page].detail)
            for page in paths:
                self.assertEqual((root / page).read_bytes(), original_pages[page])
            self.assertEqual(result.changed, ())
            # The whole publication is atomic. Keep the existing per-page inventory proof
            # by selecting each page independently, not by accepting a partially written set.
            single_page_owner = root / "publication-pages.md"
            for page in paths:
                atomic_write(single_page_owner, declaration((page,)))
                single = FLIP.flip(root, "v0.18.0", "v0.19.0", declaration=single_page_owner)
                self.assertEqual({issue.page for issue in single.issues if issue.kind == "refused"},
                                 {page} if page in HISTORY_REFUSALS else set())
            mappings, _ = ENGINE.identity_map(root, "v0.18.0", "v0.19.0", projections=True)
            inventory = ENGINE.identity_pattern(mappings, projections=True)
            differences = {}
            differing_lines = {}
            for page in paths:
                actual = FLIP.records_mask((root / page).read_text(encoding="utf-8"), page)
                expected = FLIP.records_mask(git("show", f"{published}:{page}").decode(), page)
                left, right = set(inventory.findall(actual)), set(inventory.findall(expected))
                if left != right:
                    differences[page] = {"result_only": sorted(left - right), "published_only": sorted(right - left)}
                first = [(number, tuple(inventory.findall(line))) for number, line in enumerate(actual.splitlines(), 1)
                         if inventory.search(line)]
                second = [(number, tuple(inventory.findall(line))) for number, line in enumerate(expected.splitlines(), 1)
                          if inventory.search(line)]
                a, b = set(), set()
                for operation, start, end, other_start, other_end in difflib.SequenceMatcher(
                        a=[entry[1] for entry in first], b=[entry[1] for entry in second], autojunk=False).get_opcodes():
                    if operation != "equal":
                        a.update(entry[0] for entry in first[start:end])
                        b.update(entry[0] for entry in second[other_start:other_end])
                if a or b:
                    differing_lines[page] = {"result": sorted(a), "published": sorted(b)}
            print("PUBLICATION_GOLDEN_FINDINGS=" + json.dumps(
                [{"page": issue.page, "line": issue.line, "kind": issue.kind,
                  "detail": issue.detail if issue.kind != "needs authoring" else ""} for issue in result.issues],
                sort_keys=True))
            print("PUBLICATION_GOLDEN_INVENTORIES=" + json.dumps(differences, sort_keys=True))
            print("PUBLICATION_GOLDEN_LINES=" + json.dumps(differing_lines, sort_keys=True))
            print("PUBLICATION_GOLDEN_STATISTICS=" + json.dumps([entry._asdict() for entry in result.statistics], sort_keys=True))
            expected_lines = {page: {"result": list(source_lines), "published": list(published_lines)}
                              for page, (reason, source_lines, published_lines) in HISTORY_DIFFERENCES.items()}
            self.assertEqual(differing_lines, expected_lines)
            self.assertEqual(differences, {
                page: {"result_only": list(source_values), "published_only": list(published_values)}
                for page, (source_values, published_values) in HISTORY_INVENTORIES.items()})
            self.assertTrue(all(reason for reason, _, _ in HISTORY_DIFFERENCES.values()))


if __name__ == "__main__":
    unittest.main()
