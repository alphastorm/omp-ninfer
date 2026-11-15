"""Qwen4 readiness is a read-only signal, never model adoption or qualification."""
from __future__ import annotations

import base64
import contextlib
import copy
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("qwen4_watch", ROOT / "scripts" / "upstream_watch.py")
assert SPEC is not None and SPEC.loader is not None
WATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WATCH)
FIXTURE = json.loads((ROOT / "tests/fixtures/upstream-watch-qwen4.json").read_text(encoding="utf-8"))
ENTRY = {"id": "qwen4-readiness", "upstream": "Neroued/ninfer", "upstream_ref": "master"}


class Qwen4ReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.responses = copy.deepcopy(FIXTURE)
        self.hf = {"models": self.responses["hugging_face"], "has_next_page": False}
        self.paths: list[str] = []

    def api(self, path: str):
        self.paths.append(path)
        prefix = "repos/Neroued/ninfer/"
        sha = self.responses["head"]["sha"]
        return {
            prefix + "commits/master": self.responses["head"],
            prefix + f"contents/src/models?ref={sha}": self.responses["models"],
            prefix + f"contents/tools/convert/official_recipes.py?ref={sha}": self.responses["recipes"],
        }[path]

    def watch(self, previous=None):
        with (
            mock.patch.object(WATCH, "gh_api", self.api),
            mock.patch.object(WATCH, "hf_models", return_value=self.hf),
        ):
            return WATCH.watch_qwen4(ENTRY, previous)

    def recipe(self, source: str) -> None:
        self.responses["recipes"]["content"] = base64.b64encode(source.encode()).decode()

    def test_recorded_master_and_empty_official_search_are_not_ready(self) -> None:
        result = self.watch()
        self.assertEqual(result["verdict"], "up-to-date")
        self.assertEqual(result["last_seen"]["commit"], FIXTURE["head"]["sha"])
        self.assertEqual(result["hugging_face"]["model_ids"], [])
        self.assertIs(result["hugging_face"]["models_present"], False)
        self.assertIs(result["engine"]["dense_recipe_present"], False)
        self.assertIs(result["engine"]["dense_model_directory_present"], False)
        self.assertEqual(result["unknown_reasons"], [])
        self.assertEqual(result["applicability"], "not-assessed")
        self.assertIn("qwen4_exp", [item["name"] for item in FIXTURE["models"]])
        self.assertTrue(all("?ref=" + FIXTURE["head"]["sha"] in p for p in self.paths[1:]))
        WATCH.validate_qwen4_readiness(result)

    def test_moe_recipe_and_mentions_do_not_claim_dense_support(self) -> None:
        self.recipe('''"""qwen4_27b is planned, not implemented."""
def qwen4_27b(model, recipe, sources):
    pass
RECIPES = {"qwen4_exp": qwen3_8_flash_next, "qwen3_8_flash_next": qwen3_8_flash_next}
''')
        result = self.watch()
        self.assertIs(result["engine"]["dense_recipe_present"], False)
        self.assertEqual(result["engine"]["dense_recipe_names"], [])

    def test_registered_dense_recipe_is_a_delta_not_adoption(self) -> None:
        self.recipe('RECIPES = {"qwen4_27b_nvfp4": qwen4_27b_nvfp4}\n')
        result = self.watch()
        self.assertEqual(result["verdict"], "delta-observed")
        self.assertEqual(result["engine"]["dense_recipe_names"], ["qwen4_27b_nvfp4"])
        self.assertIs(result["engine"]["dense_recipe_present"], True)
        self.assertEqual(result["applicability"], "not-assessed")

    def test_dense_model_directory_is_independent_of_recipe(self) -> None:
        self.responses["models"].extend([
            {"name": "qwen4", "path": "src/models/qwen4", "type": "dir"},
            {"name": "qwen4_27b", "path": "src/models/qwen4_27b", "type": "file"},
        ])
        result = self.watch()
        self.assertEqual(result["verdict"], "delta-observed")
        self.assertEqual(result["engine"]["dense_model_directories"], ["qwen4"])
        self.assertIs(result["engine"]["dense_recipe_present"], False)

    def test_official_model_listing_is_a_delta_without_engine_support(self) -> None:
        self.hf["models"] = [
            {"id": "Qwen/Qwen4-27B"},
            {"id": "Qwen/Qwen3.8-27B"},
            {"id": "third-party/Qwen4-27B-placeholder"},
        ]
        result = self.watch()
        self.assertEqual(result["verdict"], "delta-observed")
        self.assertEqual(result["hugging_face"]["model_ids"], ["Qwen/Qwen4-27B"])
        self.assertIs(result["engine"]["dense_recipe_present"], False)

    def test_incomplete_official_search_is_unknown_not_absent(self) -> None:
        self.hf["has_next_page"] = True
        result = self.watch()
        self.assertEqual(result["verdict"], "unknown")
        self.assertIsNone(result["hugging_face"]["models_present"])
        self.assertIn("hugging-face-pagination-incomplete", result["unknown_reasons"])

    def test_unrecognized_recipe_registry_is_unknown_not_absent(self) -> None:
        for source in ("RECIPES = build_recipes()\n", "not valid python\n",
                       "RECIPES = {**other}\n", "# registry moved\n"):
            with self.subTest(source=source):
                self.recipe(source)
                result = self.watch()
                self.assertEqual(result["verdict"], "unknown")
                self.assertIsNone(result["engine"]["dense_recipe_present"])
                self.assertIn("recipe-registry-not-understood", result["unknown_reasons"])

    def test_directory_api_limit_cannot_prove_absence(self) -> None:
        self.responses["models"] = [
            {"name": f"model{i}", "path": f"src/models/model{i}", "type": "dir"}
            for i in range(1000)
        ]
        result = self.watch()
        self.assertEqual(result["verdict"], "unknown")
        self.assertIsNone(result["engine"]["dense_model_directory_present"])

    def test_malformed_responses_are_errors_not_negative_signals(self) -> None:
        for key, value in (("models", {}), ("recipes", {"encoding": "none", "content": ""})):
            with self.subTest(key=key):
                saved = self.responses[key]
                self.responses[key] = value
                with self.assertRaises(ValueError):
                    self.watch()
                self.responses[key] = saved
        self.hf["models"] = [{"modelId": "Qwen/Qwen4-27B"}]
        with self.assertRaises(ValueError):
            self.watch()

    def test_receipt_schema_rejects_missing_unknown_and_inconsistent_fields(self) -> None:
        result = self.watch()
        for mutate in (
            lambda r: r["engine"].pop("dense_recipe_present"),
            lambda r: r["engine"].update(ready=True),
            lambda r: r["hugging_face"].update(models_present="false"),
            lambda r: r["engine"].update(dense_recipe_present=True),
            lambda r: r.update(verdict="ready"),
            lambda r: r["last_seen"].update(commit="d9ad9dea4"),
            lambda r: r.update(evidence_identity="sha256:" + "0" * 64),
        ):
            with self.subTest(mutate=mutate):
                changed = copy.deepcopy(result)
                mutate(changed)
                with self.assertRaises(ValueError):
                    WATCH.validate_qwen4_readiness(changed)

    def test_evidence_tracks_hf_changes_at_the_same_master_head(self) -> None:
        first = self.watch()
        second = self.watch(first)
        self.assertEqual(first["evidence_identity"], second["evidence_identity"])
        self.assertEqual(second["observation"], "unchanged")
        self.hf["models"] = [{"id": "Qwen/Qwen4-27B"}]
        third = self.watch(second)
        self.assertEqual(third["last_seen"], second["last_seen"])
        self.assertEqual(third["observation"], "changed")
        self.assertNotEqual(third["evidence_identity"], second["evidence_identity"])

    def test_cli_only_check_reuses_receipt_without_changing_composition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "receipt.json"
            argv = ["watch", "--only", ENTRY["id"], "--receipt", str(receipt)]
            with (
                mock.patch.object(WATCH, "gh_api", self.api),
                mock.patch.object(WATCH, "hf_models", return_value=self.hf),
                mock.patch("sys.argv", argv),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(WATCH.main(), 0)
                first = json.loads(receipt.read_text(encoding="utf-8"))
                self.assertEqual(WATCH.main(), 0)
                second = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(first["schema_version"], 2)
        self.assertEqual(first["upstreams"], [])
        self.assertEqual(first["composition"], WATCH.load_composition(ROOT))
        self.assertEqual(first["evidence_identity"], second["evidence_identity"])
        self.assertEqual(second["readiness_checks"][0]["observation"], "unchanged")

    def test_cli_records_read_failure_and_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "receipt.json"
            with (
                mock.patch.object(WATCH, "hf_models", side_effect=OSError("read failed")),
                mock.patch("sys.argv", ["watch", "--only", ENTRY["id"], "--receipt", str(receipt)]),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(WATCH.main(), 1)
            result = json.loads(receipt.read_text(encoding="utf-8"))["readiness_checks"][0]
        self.assertEqual(result["verdict"], "error")
        self.assertIn("read failed", result["error"])

    def test_hugging_face_read_is_unauthenticated_get_and_keeps_pagination(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b"[]"
        response.headers.get.return_value = '<https://huggingface.co/api/models?cursor=x>; rel="next"'
        with mock.patch.object(WATCH.urllib.request, "urlopen", return_value=response) as get:
            result = WATCH.hf_models()
        self.assertEqual(result, {"models": [], "has_next_page": True})
        request = get.call_args.args[0]
        self.assertEqual(request.full_url, "https://huggingface.co/api/models?author=Qwen&search=Qwen4")
        self.assertEqual(request.get_method(), "GET")
        self.assertIsNone(request.get_header("Authorization"))


class UpstreamCampaignDocumentationTests(unittest.TestCase):
    def test_upstream_campaign_conditions_and_current_figures(self) -> None:
        text = (ROOT / "docs/BENCHMARKS.md").read_text(encoding="utf-8")
        campaign = text.split("## Engine campaign highlights\n", 1)[1].split("\n## ", 1)[0]
        self.assertIn("FP8 E4M3", campaign)
        self.assertIn("17,705.4 tok/s", campaign)
        self.assertIn("1,380.7 aggregate tok/s", campaign)
        self.assertIn("231.7 tok/s at 90.6% acceptance", campaign)
        self.assertNotIn("15,544 tok/s", campaign)
        self.assertNotIn("1,313.8 aggregate tok/s", campaign)


if __name__ == "__main__":
    unittest.main()
