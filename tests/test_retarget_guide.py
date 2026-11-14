"""Guide identities retarget atomically, with component attribution and immutable history."""
from __future__ import annotations

import contextlib
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
SPEC = importlib.util.spec_from_file_location("retarget_guide", ROOT / "scripts" / "retarget_guide.py")
assert SPEC is not None and SPEC.loader is not None
GUIDE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GUIDE
SPEC.loader.exec_module(GUIDE)
from release_io import atomic_write, atomic_write_json

OLD = "v0.20.0"
NEW = "v0.21.0"
CONTAINER_TAG = "v1.0.0-qwen38-5090-beta.1"
NATIVE_TAG = "v1.0.0-qwen38-4090-beta.1"
SOURCE = "a" * 40
CONTAINER_SOURCE = "b" * 40
NATIVE_SOURCE = "c" * 40


def route_guide(release: str = OLD) -> str:
    headings: dict[str, dict[int, str]] = {}
    for steps in GUIDE.documented_route.LANES.values():
        for step in steps:
            headings.setdefault(step.heading, {})[step.index] = step.language
    parts = ["# Quickstart\n\n", f"Release `{release}`.\n\n"]
    for heading, blocks in headings.items():
        parts.append(f"## {heading}\n\n")
        for index in range(max(blocks) + 1):
            language = blocks.get(index, "yaml")
            parts.append(f"```{language}\nroute-{index}\n```\n\n")
    return "".join(parts)


def release_documents(release: str, *, successor: bool = False) -> dict[str, dict]:
    version = "18.2.0" if successor else "18.1.0"
    client = {
        "upstream_tag": f"v{version}", "distribution_version": version,
        "artifact_name": "client-new.zip" if successor else "client-old.zip",
        "artifact_url": f"https://example.invalid/client/v{version}/client.zip",
        "artifact_sha256": ("e" if successor else "d") * 64,
    }
    return {
        "manifest.json": {
            "release": release, "status": "ready",
            "components": {
                "ninfer": {
                    "release_tag": CONTAINER_TAG[:-1] + ("2" if successor else "1"),
                    "source_commit": CONTAINER_SOURCE if successor else SOURCE,
                },
                "ninfer_variants": [{
                    "id": "rtx4090-windows-native",
                    "release_tag": NATIVE_TAG[:-1] + ("2" if successor else "1"),
                    "source_commit": NATIVE_SOURCE if successor else SOURCE,
                    "package_name": "native-new.zip" if successor else "native-old.zip",
                }],
                "omp": client,
                "model": {"artifact_sha256": "f" * 64},
            },
        },
        "compatibility.json": {
            "product_release": release,
            "profiles": [{"id": "desktop", "client_distribution": deepcopy(client)}],
        },
        "profiles/example.json": {
            "release": release, "client": deepcopy(client),
            "server": {
                "checkpoint_host_directory": "checkpoints-v021" if successor else "checkpoints-v020",
                "image_digest": "sha256:" + ("2" if successor else "1") * 64,
                "image_reference": "registry.example.invalid/runtime@sha256:" + ("2" if successor else "1") * 64,
            },
        },
    }


class RetargetGuideTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.guide = self.root / "docs" / "QUICKSTART.md"
        self.before = release_documents(OLD)
        self.after = release_documents(NEW, successor=True)
        self.write_releases()
        atomic_write(self.guide, route_guide())

    def write_releases(self) -> None:
        for release, documents in ((OLD, self.before), (NEW, self.after)):
            for relative, document in documents.items():
                atomic_write_json(self.root / "releases" / release / relative, document)

    def write_prior(self, release: str = "v0.19.0", *, status: str = "ready") -> dict:
        manifest = deepcopy(self.before["manifest.json"])
        manifest.update(release=release, status=status)
        manifest["components"]["ninfer"].update(
            release_tag="v0.9.0-qwen38-5090-beta.9", source_commit="9" * 40)
        manifest["components"]["ninfer_variants"][0].update(
            release_tag="v0.9.0-qwen38-4090-beta.9", source_commit="9" * 40)
        atomic_write_json(self.root / "releases" / release / "manifest.json", manifest)
        return manifest

    def append(self, text: str) -> None:
        atomic_write(self.guide, self.guide.read_bytes() + text.encode("utf-8"))

    def run_retarget(self, *, check: bool = False) -> bool:
        return GUIDE.retarget(self.root, OLD, NEW, self.guide, check=check)

    def assert_refuses(self, case: str) -> str:
        original = self.guide.read_bytes()
        with self.assertRaises(GUIDE.Refusal) as caught:
            self.run_retarget()
        self.assertIn(f"refusal ({case})", str(caught.exception))
        self.assertRegex(str(caught.exception), r":\d+:")
        self.assertEqual(self.guide.read_bytes(), original)
        return str(caught.exception)

    def test_shared_source_splits_in_adjacent_component_rows(self) -> None:
        self.append(f"| RTX 5090 | `{CONTAINER_TAG}` | `{SOURCE}` |\n"
                    f"| RTX 4090 | `{NATIVE_TAG}` | `{SOURCE}` |\n")
        self.assertTrue(self.run_retarget())
        result = self.guide.read_text(encoding="utf-8")
        self.assertIn(f"| RTX 5090 | `{CONTAINER_TAG[:-1]}2` | `{CONTAINER_SOURCE}` |", result)
        self.assertIn(f"| RTX 4090 | `{NATIVE_TAG[:-1]}2` | `{NATIVE_SOURCE}` |", result)

    def test_carried_source_is_not_rewritten_beside_recut_source(self) -> None:
        native = self.after["manifest.json"]["components"]["ninfer_variants"][0]
        native.update(release_tag=NATIVE_TAG, source_commit=SOURCE)
        self.write_releases()
        self.append(f"| RTX 5090 | `{SOURCE}` |\n| RTX 4090 | `{SOURCE}` |\n")
        self.assertTrue(self.run_retarget())
        result = self.guide.read_text(encoding="utf-8")
        self.assertIn(f"| RTX 5090 | `{CONTAINER_SOURCE}` |", result)
        self.assertIn(f"| RTX 4090 | `{SOURCE}` |", result)
        self.assertFalse(self.run_retarget())

    def test_ambiguous_source_without_anchor_refuses_with_line_and_candidates(self) -> None:
        line = len(self.guide.read_text(encoding="utf-8").splitlines()) + 1
        self.append(f"Source `{SOURCE}`.\n")
        error = self.assert_refuses("a")
        self.assertIn(f"{self.guide}:{line}:", error)
        self.assertIn("rtx5090-container", error)
        self.assertIn("rtx4090-windows-native", error)
        self.assertIn("block anchors: none", error)

    def test_ambiguous_source_with_two_component_anchors_refuses(self) -> None:
        self.append(f"RTX 5090 and RTX 4090 share `{SOURCE}`.\n")
        self.assert_refuses("a")

    def test_attribution_uses_each_list_item_paragraph_and_fenced_block(self) -> None:
        self.append(f"- `{CONTAINER_TAG}` uses\n  `{SOURCE}`.\n"
                    f"- `{NATIVE_TAG}` uses\n  `{SOURCE}`.\n\n"
                    f"`native-old.zip` uses `{SOURCE}`.\n\n"
                    f"```sh\n# RTX 5090\nprintf '%s' '{SOURCE}'\n```\n")
        self.assertTrue(self.run_retarget())
        result = self.guide.read_text(encoding="utf-8")
        self.assertIn(f"- `{CONTAINER_TAG[:-1]}2` uses\n  `{CONTAINER_SOURCE}`.", result)
        self.assertIn(f"- `{NATIVE_TAG[:-1]}2` uses\n  `{NATIVE_SOURCE}`.", result)
        self.assertIn(f"`native-new.zip` uses `{NATIVE_SOURCE}`.", result)
        self.assertIn(f"printf '%s' '{CONTAINER_SOURCE}'", result)

    def test_successor_component_tag_is_also_an_anchor_in_original_text(self) -> None:
        self.append(f"`{NATIVE_TAG[:-1]}2` uses `{SOURCE}`.\n")
        self.run_retarget()
        self.assertIn(f"`{NATIVE_TAG[:-1]}2` uses `{NATIVE_SOURCE}`.", self.guide.read_text(encoding="utf-8"))

    def test_shared_identity_with_consensus_is_global_without_an_anchor(self) -> None:
        self.after["manifest.json"]["components"]["ninfer_variants"][0]["source_commit"] = CONTAINER_SOURCE
        self.write_releases()
        self.append(f"Source `{SOURCE}`.\n")
        self.run_retarget()
        self.assertIn(f"Source `{CONTAINER_SOURCE}`.", self.guide.read_text(encoding="utf-8"))

    def test_unchanged_shared_url_allows_its_embedded_predecessor_version(self) -> None:
        url = f"https://example.invalid/download/{OLD}/carried.zip"
        for documents in (self.before, self.after):
            for relative, document in documents.items():
                if relative == "manifest.json":
                    document["components"]["omp"]["artifact_url"] = url
                    document["components"]["ninfer"]["binary_archive_url"] = url
                elif relative == "compatibility.json":
                    document["profiles"][0]["client_distribution"]["artifact_url"] = url
                else:
                    document["client"]["artifact_url"] = url
        self.write_releases()
        self.append(url + "\n")
        self.assertTrue(self.run_retarget())
        self.assertIn(url, self.guide.read_text(encoding="utf-8"))
        self.assertFalse(self.run_retarget())

    def test_conflicting_targets_inside_one_scope_refuse_at_the_occurrence(self) -> None:
        old = self.before["manifest.json"]["components"]["ninfer"]
        new = self.after["manifest.json"]["components"]["ninfer"]
        old["other_commit"], new["other_commit"] = SOURCE, "9" * 40
        self.write_releases()
        self.append(f"RTX 5090 source `{SOURCE}`.\n")
        self.assert_refuses("a")

    def test_scope_anchor_in_a_different_paragraph_does_not_count(self) -> None:
        self.append(f"RTX 5090.\n\nSource `{SOURCE}`.\n")
        self.assert_refuses("a")

    def test_previous_distinct_and_current_identities_advance_in_one_pass(self) -> None:
        prior = self.write_prior()
        old_tag = prior["components"]["ninfer"]["release_tag"]
        self.append(f"RTX 5090 current `{CONTAINER_TAG}`, rollback `{old_tag}`.\n")
        self.run_retarget()
        result = self.guide.read_text(encoding="utf-8")
        self.assertIn(f"RTX 5090 current `{CONTAINER_TAG[:-1]}2`, rollback `{CONTAINER_TAG}`.", result)
        self.assertFalse(self.run_retarget())

    def test_completed_guide_refuses_stale_recut_component_identities(self) -> None:
        prior = self.write_prior()
        prior_digest = "8" * 64
        prior["components"]["omp"]["artifact_sha256"] = prior_digest
        atomic_write_json(self.root / "releases" / prior["release"] / "manifest.json", prior)
        old_digest = self.before["manifest.json"]["components"]["omp"]["artifact_sha256"]
        new_digest = self.after["manifest.json"]["components"]["omp"]["artifact_sha256"]
        prior_tag = prior["components"]["ninfer"]["release_tag"]
        new_tag = self.after["manifest.json"]["components"]["ninfer"]["release_tag"]
        self.append(f"| RTX 5090 current | `{CONTAINER_TAG}` |\n"
                    f"| RTX 5090 rollback | `{prior_tag}` |\n"
                    f"| Client current | `{old_digest}` |\n"
                    f"| Client rollback | `{prior_digest}` |\n"
                    "| Current store | `checkpoints-v020` |\n"
                    "| Rollback store | `checkpoints-v019` |\n\n"
                    f"[{old_digest}](../releases/{OLD}/manifest.json)\n")
        self.assertTrue(self.run_retarget())
        completed = self.guide.read_text(encoding="utf-8")
        self.assertIn(f"| RTX 5090 rollback | `{CONTAINER_TAG}` |", completed)
        self.assertIn(f"| Client rollback | `{old_digest}` |", completed)
        self.assertIn("| Rollback store | `checkpoints-v020` |", completed)
        self.assertFalse(self.run_retarget())
        self.assertEqual(self.guide.read_text(encoding="utf-8"), completed)
        for current, predecessor in ((new_digest, old_digest), (new_tag, CONTAINER_TAG)):
            with self.subTest(identity=predecessor):
                line = completed.count("\n", 0, completed.index(current)) + 1
                atomic_write(self.guide, completed.replace(current, predecessor, 1))
                error = self.assert_refuses("c")
                self.assertIn(f"{self.guide}:{line}:", error)
                self.assertIn(predecessor, error)

    def test_completed_guide_refuses_ambiguous_component_identity_at_its_line(self) -> None:
        self.assertTrue(self.run_retarget())
        line = len(self.guide.read_text(encoding="utf-8").splitlines()) + 1
        self.append(f"Source `{SOURCE}`.\n")
        error = self.assert_refuses("a")
        self.assertIn(f"{self.guide}:{line}:", error)
        self.assertIn(SOURCE, error)
        self.assertIn("rtx5090-container", error)
        self.assertIn("rtx4090-windows-native", error)

    def test_completed_guide_refuses_stale_component_download_urls_and_package_names(self) -> None:
        client = self.before["manifest.json"]["components"]["omp"]
        for value in (client["artifact_url"], client["artifact_name"], "native-old.zip"):
            with self.subTest(identity=value):
                atomic_write(self.guide, route_guide(NEW))
                line = len(self.guide.read_text(encoding="utf-8").splitlines()) + 1
                self.append(value + "\n")
                error = self.assert_refuses("c")
                self.assertIn(f"{self.guide}:{line}:", error)
                self.assertIn(value, error)

    def test_completed_download_and_package_rollback_clauses_are_occurrence_scoped(self) -> None:
        prior = self.write_prior()
        old = self.before["manifest.json"]["components"]["omp"]
        prior["components"]["omp"].update(
            artifact_url="https://example.invalid/client/prior/client.zip",
            artifact_name="client-prior.zip")
        atomic_write_json(self.root / "releases" / prior["release"] / "manifest.json", prior)
        new = self.after["manifest.json"]["components"]["omp"]
        for key in ("artifact_url", "artifact_name"):
            with self.subTest(key=key):
                text = route_guide() + f"Client current {old[key]}; rollback {prior['components']['omp'][key]}.\n"
                atomic_write(self.guide, text)
                self.assertTrue(self.run_retarget())
                completed = self.guide.read_bytes()
                self.assertIn(f"current {new[key]}; rollback {old[key]}.", completed.decode("utf-8"))
                self.assertFalse(self.run_retarget())
                self.assertEqual(self.guide.read_bytes(), completed)
                atomic_write(self.guide, completed.decode("utf-8").replace(new[key], old[key], 1))
                self.assert_refuses("c")

    def test_release_anchor_wins_over_an_earlier_predecessor_rollback_sentence(self) -> None:
        self.write_prior()
        for kind in ("Prepared", "Versioned"):
            with self.subTest(kind=kind):
                text = (f"Rollback release {OLD}.\n\n"
                        f"> **{kind} guide: {NEW} · documented routes**\n\n" + route_guide(NEW))
                atomic_write(self.guide, text)
                self.assertFalse(self.run_retarget())
                self.assertEqual(self.guide.read_bytes(), text.encode("utf-8"))

    def test_completed_guide_resolves_current_and_rollback_occurrences_individually(self) -> None:
        prior = self.write_prior()
        prior_tag = prior["components"]["ninfer"]["release_tag"]
        new_tag = self.after["manifest.json"]["components"]["ninfer"]["release_tag"]
        for references in (f"current `{CONTAINER_TAG}`, rollback `{prior_tag}`",
                           f"rollback `{prior_tag}`, current `{CONTAINER_TAG}`",
                           f"rollback `{prior_tag}`; install `{CONTAINER_TAG}`",
                           f"rollback `{prior_tag}`. Install `{CONTAINER_TAG}`"):
            with self.subTest(references=references):
                atomic_write(self.guide, route_guide() + f"RTX 5090 {references}.\n")
                self.assertTrue(self.run_retarget())
                completed = self.guide.read_text(encoding="utf-8")
                self.assertFalse(self.run_retarget())
                line = completed.count("\n", 0, completed.index(new_tag)) + 1
                atomic_write(self.guide, completed.replace(new_tag, CONTAINER_TAG, 1))
                error = self.assert_refuses("c")
                self.assertIn(f"{self.guide}:{line}:", error)
                self.assertIn(CONTAINER_TAG, error)

    def test_previous_distinct_stays_put_for_a_carried_lane(self) -> None:
        prior = self.write_prior()
        self.after["manifest.json"]["components"]["ninfer_variants"] = deepcopy(
            self.before["manifest.json"]["components"]["ninfer_variants"])
        self.write_releases()
        old_tag = prior["components"]["ninfer_variants"][0]["release_tag"]
        self.append(f"RTX 4090 current `{NATIVE_TAG}`, rollback `{old_tag}`.\n")
        self.run_retarget()
        self.assertIn(f"RTX 4090 current `{NATIVE_TAG}`, rollback `{old_tag}`.",
                      self.guide.read_text(encoding="utf-8"))

    def test_previous_distinct_skips_carried_releases_and_unready_manifests(self) -> None:
        older = self.write_prior("v0.18.0")
        carried = deepcopy(self.before["manifest.json"])
        carried["release"] = "v0.19.0"
        atomic_write_json(self.root / "releases" / "v0.19.0" / "manifest.json", carried)
        self.write_prior("v0.19.1", status="candidate")
        self.append(f"RTX 5090 rollback `{older['components']['ninfer']['source_commit']}`.\n")
        self.run_retarget()
        self.assertIn(f"RTX 5090 rollback `{SOURCE}`.", self.guide.read_text(encoding="utf-8"))

    def test_current_and_previous_roles_in_different_scopes_need_an_anchor_even_with_consensus(self) -> None:
        prior = self.write_prior()
        shared = prior["components"]["ninfer"]["source_commit"]
        self.before["manifest.json"]["components"]["ninfer_variants"][0]["source_commit"] = shared
        self.after["manifest.json"]["components"]["ninfer_variants"][0]["source_commit"] = SOURCE
        self.write_releases()
        self.append(f"Source `{shared}`.\n")
        self.assert_refuses("a")

    def test_unattributed_ambiguous_previous_distinct_source_refuses(self) -> None:
        self.write_prior()
        self.after["manifest.json"]["components"]["ninfer_variants"] = deepcopy(
            self.before["manifest.json"]["components"]["ninfer_variants"])
        self.write_releases()
        self.append(f"Rollback source `{'9' * 40}`.\n")
        self.assert_refuses("a")

    def test_previous_store_is_allowed_only_at_its_produced_span(self) -> None:
        self.write_prior()
        self.append("Current checkpoints-v020; rollback checkpoints-v019.\n")
        self.run_retarget()
        self.assertIn("Current checkpoints-v021; rollback checkpoints-v020.",
                      self.guide.read_text(encoding="utf-8"))
        self.assertFalse(self.run_retarget())
        original = route_guide() + "Current checkpoints-v020; rollback checkpoints-v019; stray v020.\n"
        atomic_write(self.guide, original)
        self.assert_refuses("c")

    def test_checkpoint_derivation_keeps_the_frozen_historical_store(self) -> None:
        self.assertEqual(GUIDE.checkpoint_name("v0.16.2"), "checkpoints-v013")
        self.assertEqual(GUIDE.checkpoint_name("v0.17.0"), "checkpoints-v017")
        self.assertEqual(GUIDE.checkpoint_name("v1.2.3"), "checkpoints-v102-3")

    def test_empty_map_refuses(self) -> None:
        with self.assertRaisesRegex(GUIDE.Refusal, r"manifest.json:1: refusal \(b\).*empty"):
            GUIDE.identity_map(self.root, OLD, OLD)

    def test_map_without_the_product_release_refuses(self) -> None:
        self.after["manifest.json"].pop("release")
        self.after["compatibility.json"].pop("product_release")
        self.after["profiles/example.json"].pop("release")
        self.write_releases()
        self.assert_refuses("b")

    def test_residual_bare_and_compact_versions_refuse_with_exact_line(self) -> None:
        original = self.guide.read_bytes()
        for value in (OLD[1:], "v020"):
            with self.subTest(value=value):
                atomic_write(self.guide, original)
                line = len(original.decode("utf-8").splitlines()) + 1
                self.append(f"Leftover `{value}`.\n")
                self.assertIn(f"{self.guide}:{line}:", self.assert_refuses("c"))

    def test_residual_checkpoint_without_a_matching_leaf_refuses(self) -> None:
        self.before["profiles/example.json"]["server"].pop("checkpoint_host_directory")
        self.write_releases()
        self.append("Store `checkpoints-v020`.\n")
        self.assert_refuses("c")

    def test_compact_patch_form_is_unambiguous(self) -> None:
        self.assertEqual(GUIDE.residual_versions("v1.2.3"),
                         {"v1.2.3", "1.2.3", "v102-3", "checkpoints-v102-3"})

    def test_structure_refuses_a_missing_heading_without_writing(self) -> None:
        heading = next(iter(GUIDE.documented_route.LANES.values()))[0].heading
        original = self.guide.read_text(encoding="utf-8")
        atomic_write(self.guide, original.replace(f"## {heading}\n", "## Renamed heading\n"))
        self.assert_refuses("d")

    def test_structure_refuses_a_changed_runner_language_at_its_heading(self) -> None:
        heading = next(iter(GUIDE.documented_route.LANES.values()))[0].heading
        original = self.guide.read_text(encoding="utf-8")
        line = original.splitlines().index(f"## {heading}") + 1
        atomic_write(self.guide, original.replace(f"## {heading}\n\n```powershell",
                                                f"## {heading}\n\n```sh", 1))
        self.assertIn(f"{self.guide}:{line}:", self.assert_refuses("d"))

    def test_swaps_use_a_single_pass_and_rerun_does_not_reverse_them(self) -> None:
        old = self.before["manifest.json"]["components"]["omp"]
        new = self.after["manifest.json"]["components"]["omp"]
        old.update(first_commit="3" * 40, second_commit="4" * 40)
        new.update(first_commit="4" * 40, second_commit="3" * 40)
        self.write_releases()
        self.append(f"First `{'3' * 40}`, second `{'4' * 40}`.\n")
        self.run_retarget()
        result = self.guide.read_bytes()
        self.assertIn(f"First `{'4' * 40}`, second `{'3' * 40}`.", result.decode("utf-8"))
        with mock.patch.object(GUIDE, "atomic_write", wraps=GUIDE.atomic_write) as write:
            self.assertFalse(self.run_retarget())
        self.assertEqual(self.guide.read_bytes(), result)
        self.assertNotIn(self.guide, [call.args[0] for call in write.call_args_list])

    def test_immutable_links_survive_including_the_predecessor_guide(self) -> None:
        links = [
            f"[{OLD} guide](https://github.com/example/product/blob/{OLD}/docs/QUICKSTART.md#route)",
            f"[{OLD} tree](../releases/{OLD}/manifest.json)",
            f"[{OLD} tag](https://github.com/example/product/releases/tag/{OLD})",
            f"[{OLD} raw](https://raw.githubusercontent.com/example/product/{'7' * 40}/docs/QUICKSTART.md)",
        ]
        self.append("\n\n".join(links) + "\n")
        self.run_retarget()
        result = self.guide.read_text(encoding="utf-8")
        for link in links:
            self.assertIn(link, result)
        self.assertIn(f"Release `{NEW}`.", result)
        self.assertFalse(self.run_retarget())

    def test_moving_raw_url_and_link_syntax_in_code_are_not_masked(self) -> None:
        self.append(f"[{OLD} raw](https://raw.githubusercontent.com/example/product/main/docs/QUICKSTART.md)\n\n"
                    f"```sh\nprintf '[{OLD}](../releases/{OLD}/guide.md)'\n```\n")
        self.run_retarget()
        result = self.guide.read_text(encoding="utf-8")
        self.assertIn(f"[{NEW} raw]", result)
        self.assertIn(f"printf '[{NEW}](../releases/{NEW}/guide.md)'", result)

    def test_partial_keys_do_not_rewrite_inside_longer_tokens(self) -> None:
        old = self.before["manifest.json"]["components"]["omp"]["artifact_sha256"]
        self.append(f"Hashes `{old}` `{old}f` `x{old}`; versions 18.1.0 18.1.0.1 18.1.0-extra x18.1.0.\n")
        self.run_retarget()
        result = self.guide.read_text(encoding="utf-8")
        self.assertIn(f"Hashes `{'e' * 64}` `{old}f` `x{old}`", result)
        self.assertIn("versions 18.2.0 18.1.0.1 18.1.0-extra x18.1.0.", result)

    def test_longest_url_key_wins_over_the_version_it_contains(self) -> None:
        self.append("https://example.invalid/client/v18.1.0/client.zip\n")
        self.run_retarget()
        self.assertIn("https://example.invalid/client/v18.2.0/client.zip",
                      self.guide.read_text(encoding="utf-8"))

    def test_lists_match_by_id_not_position_and_pointers_escape_keys(self) -> None:
        for documents, successor in ((self.before, False), (self.after, True)):
            documents["manifest.json"]["components"]["ninfer_variants"].append({
                "id": "other", "package_name": "other-new.zip" if successor else "other-old.zip"})
        self.after["manifest.json"]["components"]["ninfer_variants"].reverse()
        self.before["manifest.json"]["a/b~c"] = "8" * 64
        self.after["manifest.json"]["a/b~c"] = "9" * 64
        self.write_releases()
        self.append("native-old.zip other-old.zip\n")
        self.run_retarget()
        self.assertIn("native-new.zip other-new.zip", self.guide.read_text(encoding="utf-8"))
        leaves = GUIDE.string_leaves(self.root / "releases" / OLD / "manifest.json")
        leaf = leaves["/a~1b~0c"]
        source = leaf.file.read_text(encoding="utf-8").splitlines()[leaf.line - 1]
        self.assertIn(leaf.value, source)

    def test_free_prose_and_numeric_metadata_are_not_identities(self) -> None:
        for documents, successor in ((self.before, False), (self.after, True)):
            documents["manifest.json"]["note"] = "Acceptance passed." if successor else "Acceptance pending."
            documents["manifest.json"]["asset_bytes"] = 200 if successor else 100
        self.write_releases()
        self.append("Acceptance pending. Package has 100 bytes.\n")
        self.run_retarget()
        self.assertIn("Acceptance pending. Package has 100 bytes.", self.guide.read_text(encoding="utf-8"))

    def test_unbound_measurements_link_refuses_with_target_and_line(self) -> None:
        target = "measurements/2026-01-01-client-review.json"
        line = len(self.guide.read_text(encoding="utf-8").splitlines()) + 1
        self.append(f"[client review]({target})\n")
        original = self.guide.read_bytes()
        with self.assertRaisesRegex(GUIDE.Refusal, "unbound evidence link") as caught:
            self.run_retarget()
        self.assertIn(f"{self.guide}:{line}:", str(caught.exception))
        self.assertIn(target, str(caught.exception))
        self.assertEqual(self.guide.read_bytes(), original)

    def test_bound_measurements_link_retargets_through_the_identity_map(self) -> None:
        before = "docs/measurements/2026-01-01-client-review.json"
        after = "docs/measurements/2026-02-01-client-review.json"
        root = self.root
        for index, source in enumerate(("manifest.json", "qualification.json", "acceptance/client.json",
                                        "qualification/client-components.json")):
            with self.subTest(binding=source):
                self.root = root / str(index)
                self.guide = self.root / "docs" / "QUICKSTART.md"
                self.before = release_documents(OLD)
                self.after = release_documents(NEW, successor=True)
                for documents, path in ((self.before, before), (self.after, after)):
                    documents.setdefault(source, {})["review"] = {"repository_path": path}
                self.write_releases()
                atomic_write(self.guide, route_guide() + f"[client review]({before[5:]})\n")
                self.run_retarget()
                self.assertIn(f"[client review]({after[5:]})", self.guide.read_text(encoding="utf-8"))
                self.assertFalse(self.run_retarget())

    def test_guide_without_evidence_links_passes(self) -> None:
        self.assertTrue(self.run_retarget())
        self.assertFalse(self.run_retarget())

    def test_check_reports_drift_without_writing_and_then_accepts_a_rerun(self) -> None:
        argv = ["--from", OLD, "--to", NEW, "--guide", str(self.guide)]
        original = self.guide.read_bytes()
        with mock.patch.object(GUIDE, "ROOT", self.root), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(GUIDE.main([*argv, "--check"]), 1)
            self.assertEqual(self.guide.read_bytes(), original)
            self.assertEqual(GUIDE.main(argv), 0)
            changed = self.guide.read_bytes()
            self.assertEqual(GUIDE.main([*argv, "--check"]), 0)
            self.assertEqual(GUIDE.main(argv), 0)
        self.assertNotEqual(changed, original)
        self.assertEqual(self.guide.read_bytes(), changed)
        self.assertIn("would change", output.getvalue())
        self.assertIn("unchanged", output.getvalue())

    def test_cli_uses_the_checkout_guide_by_default(self) -> None:
        with mock.patch.object(GUIDE, "ROOT", self.root), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(GUIDE.main(["--from", OLD, "--to", NEW]), 0)
        self.assertIn(f"Release `{NEW}`.", self.guide.read_text(encoding="utf-8"))

    def test_identity_classes_exclude_embedded_prose(self) -> None:
        identities = {
            "/commit": ("a" * 40, "hex"),
            "/sha256": ("b" * 64, "hex"),
            "/digest": ("sha256:" + "c" * 64, "digest"),
            "/image": ("registry.example.invalid/image@sha256:" + "d" * 64, "image"),
            "/release_tag": (CONTAINER_TAG, "component-tag"),
            "/release": (OLD, "version"),
            "/version": ("18.1.0", "version"),
            "/url": ("https://example.invalid/client.zip", "url"),
            "/record": ("docs/measurements/2026-01-01-client-review.json", "evidence"),
            "/package_name": ("client.zip", "package"),
            "/checkpoint_host_directory": ("checkpoints-v020", "checkpoint"),
        }
        for pointer, (value, kind) in identities.items():
            with self.subTest(pointer=pointer):
                self.assertEqual(GUIDE.identity_class(pointer, value), kind)
                self.assertIsNone(GUIDE.identity_class("/note", f"Selected {value}."))

    def test_crlf_and_nonidentity_bytes_survive(self) -> None:
        original = route_guide().replace("\n", "\r\n") + "Unicode prose: \u03b1.\r\n"
        atomic_write(self.guide, original)
        self.run_retarget()
        self.assertEqual(self.guide.read_bytes(), original.replace(OLD, NEW).encode("utf-8"))

    def test_missing_identity_source_reports_file_and_line(self) -> None:
        path = self.root / "releases" / NEW / "manifest.json"
        path.unlink()
        with self.assertRaisesRegex(GUIDE.Refusal, re.escape(str(path)) + ":1:"):
            self.run_retarget()

    def test_invalid_json_reports_its_actual_line(self) -> None:
        path = self.root / "releases" / NEW / "manifest.json"
        atomic_write(path, '{\n  "release":\n}\n')
        with self.assertRaisesRegex(GUIDE.Refusal, re.escape(str(path)) + ":3:"):
            self.run_retarget()

    def test_cli_refusal_returns_one_and_leaves_the_guide_unchanged(self) -> None:
        self.append(f"Source `{SOURCE}`.\n")
        original = self.guide.read_bytes()
        with mock.patch.object(GUIDE, "ROOT", self.root), contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(GUIDE.main(["--from", OLD, "--to", NEW, "--guide", str(self.guide)]), 1)
        self.assertIn("refusal (a)", errors.getvalue())
        self.assertEqual(self.guide.read_bytes(), original)


class HistoryGoldenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        shallow = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT,
                                 check=True, capture_output=True, text=True).stdout.strip() == "true"
        if shallow:
            if os.environ.get("OMP_NINFER_REQUIRE_HISTORY") == "1":
                raise AssertionError("guide history golden requires full git history")
            raise unittest.SkipTest("guide history golden requires full git history")
        cls.commits = {}
        for tag in ("v0.17.0", "v0.18.0", "v0.19.0"):
            commit = subprocess.run(["git", "rev-parse", "--verify", f"{tag}^{{commit}}"], cwd=ROOT,
                                    check=True, capture_output=True, text=True).stdout.strip()
            if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
                raise AssertionError(f"{tag} must resolve to a full commit")
            cls.commits[tag] = commit

    def historical(self, release: str, path: str) -> bytes:
        return subprocess.run(["git", "show", f"{self.commits[release]}:{path}"], cwd=ROOT,
                              check=True, capture_output=True).stdout

    def write_history(self, root: Path, predecessor: str, release: str) -> tuple[Path, Path]:
        # The complete two release trees supply current identities. Older ready manifests
        # additionally supply previous-distinct identities; all reads use resolved full SHAs.
        files = subprocess.run(["git", "ls-tree", "-r", "--name-only", self.commits[release], "--", "releases"],
                               cwd=ROOT, check=True, capture_output=True, text=True).stdout.splitlines()
        manifests = [file for file in files if re.fullmatch(r"releases/v\d+\.\d+\.\d+/manifest\.json", file)
                     and not file.startswith((f"releases/{predecessor}/", f"releases/{release}/"))]
        archive = subprocess.run(
            ["git", "archive", self.commits[release], f"releases/{predecessor}", f"releases/{release}", *manifests],
            cwd=ROOT, check=True, capture_output=True,
        ).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as tree:
            for member in tree.getmembers():
                if member.isfile():
                    stream = tree.extractfile(member)
                    assert stream is not None
                    atomic_write(root / member.name, stream.read())
        guide, expected = root / "docs" / "QUICKSTART.md", root / "published.md"
        atomic_write(guide, self.historical(predecessor, "docs/QUICKSTART.md"))
        atomic_write(expected, self.historical(release, "docs/QUICKSTART.md"))
        return guide, expected

    def test_retarget_published_predecessor_matches_successor_identities_and_routes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guide, expected = self.write_history(root, "v0.18.0", "v0.19.0")
            published = expected.read_text(encoding="utf-8")
            source = guide.read_text(encoding="utf-8")
            source_lines = source.splitlines(keepends=True)
            # v0.18.0:102 is an unbound evidence link, removed from future guides.
            # Its target is not bound by either release. The published v0.19.0:102
            # editorially changed both target and label, not a manifest-derived identity:
            old_review = "[18.18.6→18.18.7 review](measurements/2026-11-11-omp-18187-client-upgrade-review.json)"
            new_review = "[v0.18.0 client→18.20.0 review](measurements/2026-11-13-omp-18200-client-upgrade-review.json)"
            self.assertEqual(source_lines[101].rstrip("\n"), old_review)
            self.assertEqual(published.splitlines()[101], new_review)
            with self.assertRaisesRegex(GUIDE.Refusal, r":102: unbound evidence link"):
                GUIDE.retarget(root, "v0.18.0", "v0.19.0", guide)
            self.assertEqual(guide.read_text(encoding="utf-8"), source)
            source_lines[101] = "\n"
            atomic_write(guide, "".join(source_lines))
            self.assertTrue(GUIDE.retarget(root, "v0.18.0", "v0.19.0", guide))
            actual = guide.read_text(encoding="utf-8")
            classes: dict[str, set[str]] = {}
            for release in ("v0.18.0", "v0.19.0"):
                for leaf in GUIDE.release_leaves(root, release).values():
                    kind = GUIDE.identity_class(leaf.pointer, leaf.value)
                    assert kind is not None
                    classes.setdefault(kind, set()).add(leaf.value)
            for kind, values in classes.items():
                pattern = GUIDE.boundary_pattern(values)
                with self.subTest(identity_class=kind):
                    self.assertEqual(set(pattern.findall(actual)),
                                     set(pattern.findall(published)))
            for lane in GUIDE.documented_route.LANES:
                actual_blocks = GUIDE.documented_route.lane_blocks(guide, lane)
                expected_blocks = GUIDE.documented_route.lane_blocks(expected, lane)
                self.assertEqual([(step.slug, block.text) for step, block in actual_blocks],
                                 [(step.slug, block.text) for step, block in expected_blocks], lane)
            self.assertFalse(GUIDE.retarget(root, "v0.18.0", "v0.19.0", guide, check=True))
            self.assertFalse(GUIDE.retarget(root, "v0.18.0", "v0.19.0", guide))

    def test_published_and_real_guide_anchors_preserve_an_early_rollback_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guide, expected = self.write_history(root, "v0.18.0", "v0.19.0")
            real = (ROOT / "docs" / "QUICKSTART.md").read_text(encoding="utf-8")
            anchor = re.search(r"\*\*(?:Prepared|Versioned) guide: (v\d+\.\d+\.\d+)", real)
            self.assertIsNotNone(anchor)
            release = anchor[1]
            predecessor = GUIDE.ready_history(ROOT, release)[0][0]
            cases = ((root, expected.read_text(encoding="utf-8"), "v0.18.0", "v0.19.0"),
                     (ROOT, real, predecessor, release))
            for authority, text, predecessor, release in cases:
                with self.subTest(authority=authority):
                    text = f"Rollback release {predecessor}.\n\n" + text
                    mappings, anchors = GUIDE.identity_map(authority, predecessor, release)
                    self.assertEqual(GUIDE.retarget_text(text, guide, predecessor, release, mappings, anchors),
                                     text)


class HistoryPolicyTest(unittest.TestCase):
    def test_shallow_clone_skips_without_required_history(self) -> None:
        shallow = subprocess.CompletedProcess([], 0, "true\n", "")
        with mock.patch.object(subprocess, "run", return_value=shallow), \
                mock.patch.dict(os.environ, {"OMP_NINFER_REQUIRE_HISTORY": ""}):
            with self.assertRaises(unittest.SkipTest):
                HistoryGoldenTest.setUpClass()

    def test_shallow_clone_fails_when_history_is_required(self) -> None:
        shallow = subprocess.CompletedProcess([], 0, "true\n", "")
        with mock.patch.object(subprocess, "run", return_value=shallow), \
                mock.patch.dict(os.environ, {"OMP_NINFER_REQUIRE_HISTORY": "1"}):
            with self.assertRaisesRegex(AssertionError, "full git history"):
                HistoryGoldenTest.setUpClass()


if __name__ == "__main__":
    unittest.main()
