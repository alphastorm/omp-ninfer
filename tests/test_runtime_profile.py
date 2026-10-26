"""One authored profile schema renders the already-qualified wire identities exactly."""
from __future__ import annotations

import copy

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render_runtime_profile as renderer
import verify_release


def source(lane):
    return json.loads((ROOT / "profiles/runtime" / (lane + ".json")).read_text(encoding="utf-8"))


class RuntimeProfileTests(unittest.TestCase):
    def test_native_schema4_outputs_are_byte_identical_to_both_qualified_configs(self):
        for lane in ("rtx4090", "rtx3090"):
            with self.subTest(lane=lane):
                profile = source(lane)
                before = copy.deepcopy(profile)
                expected = ROOT / "profiles/v0.13.1" / lane / "server-config.json"
                self.assertEqual(renderer.rendered_bytes(profile), expected.read_bytes())
                self.assertEqual(profile, before)
                self.assertEqual(renderer.render(profile)["schema_version"], 4)

    def test_container_outputs_preserve_argument_order_and_qualified_identity(self):
        profile = source("rtx5090")
        arguments = renderer.render(profile)
        for path in sorted((ROOT / "profiles").glob("qwen38-rtx5090-*.json")):
            with self.subTest(profile=path.name):
                template = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(arguments, template["server"]["arguments"])
                self.assertEqual(renderer.rendered_bytes(profile, template), path.read_bytes())
                rendered = renderer.render(profile, template)
                identity = verify_release.configuration_identity(rendered)
                self.assertEqual(identity, "751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47")
                self.assertEqual(verify_release.argument_value(arguments, "--config-sha256"), identity)

    def test_each_backend_uses_shared_serving_settings_without_inheriting_the_other_lane(self):
        container = source("rtx5090")
        original = renderer.container_arguments(container)
        container["settings"]["engine"]["max_context"] = 65536
        container["settings"]["speculative"]["draft_tokens"] = 5
        changed = renderer.container_arguments(container)
        self.assertEqual(verify_release.argument_value(changed, "--max-context"), "65536")
        self.assertEqual(verify_release.argument_value(changed, "--draft-tokens"), "5")
        self.assertNotEqual(verify_release.argument_value(original, "--config-sha256"),
                            verify_release.argument_value(changed, "--config-sha256"))
        native = source("rtx4090")
        native["settings"]["engine"]["max_context"] = 65536
        native["settings"]["speculative"]["draft_tokens"] = 5
        rendered = renderer.render(native)
        self.assertEqual(rendered["engine"]["max_context"], 65536)
        self.assertEqual(rendered["speculative"]["draft_tokens"], 5)
        self.assertNotIn("arguments", rendered)
        self.assertNotIn("container", rendered)

    def test_boolean_defaults_emit_only_real_engine_switches(self):
        profile = source("rtx5090")
        profile["settings"]["engine"].update(vision=False, cuda_graph=True, prefix_reuse=True)
        profile["settings"]["reasoning"]["thinking"] = True
        arguments = renderer.container_arguments(profile)
        for flag in ("--vision", "--no-vision", "--cuda-graph", "--prefix-reuse", "--no-thinking"):
            self.assertNotIn(flag, arguments)
        profile["settings"]["engine"].update(cuda_graph=False, prefix_reuse=False)
        profile["settings"]["reasoning"]["thinking"] = False
        arguments = renderer.container_arguments(profile)
        for flag in ("--no-cuda-graph", "--no-prefix-reuse", "--no-thinking"):
            self.assertIn(flag, arguments)

    def test_unrepresentable_and_unknown_fields_are_refused_instead_of_ignored(self):
        for mutation in ("kind", "lane", "setting", "engine", "container", "native-only", "authentication"):
            profile = source("rtx5090")
            if mutation in ("kind", "lane"):
                profile[mutation] = "unknown"
            elif mutation == "setting":
                profile["settings"]["unknown"] = 1
            elif mutation == "engine":
                profile["settings"]["engine"]["unknown"] = 1
            elif mutation == "container":
                profile["container"]["unknown"] = 1
            elif mutation == "authentication":
                profile["settings"]["authentication"]["mode"] = "none"
            else:
                profile["settings"]["response_store"] = {"max_records": 100}
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                renderer.render(profile)
        native = source("rtx4090")
        native["settings"]["speculative"]["lm_head_draft"] = False
        with self.assertRaisesRegex(ValueError, "container-only"):
            renderer.render(native)

    def test_cli_renders_and_checks_without_rewriting_a_qualified_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "server-config.json"
            command = [sys.executable, str(ROOT / "scripts/render_runtime_profile.py"), "--profile",
                       str(ROOT / "profiles/runtime/rtx4090.json"), "--output", str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            before = output.stat().st_mtime_ns
            result = subprocess.run(command + ["--check"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.stat().st_mtime_ns, before)
            output.write_text("different config\n")
            result = subprocess.run(command + ["--check"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("rendered profile differs", result.stderr)
            self.assertEqual(output.read_text(), "different config\n")


if __name__ == "__main__":
    unittest.main()
