from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_runpod_ci", ROOT / "scripts" / "run_runpod_ci.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RunpodCiTest(unittest.TestCase):
    def test_parses_json_after_wait_progress(self) -> None:
        value = MODULE.parse_json_output(
            "waiting for ssh on pod abc12345\n"
            '{"id":"abc12345","runtimeStatus":"running"}\n'
        )
        self.assertEqual(value["id"], "abc12345")

    def test_catalog_price_uses_the_selected_cloud(self) -> None:
        catalog = [
            {
                "available": True,
                "displayName": "RTX 5090",
                "gpuId": "NVIDIA GeForce RTX 5090",
                "communityPricePerHr": 0.69,
                "securePricePerHr": 0.99,
            }
        ]
        self.assertEqual(
            MODULE.gpu_hourly_price(catalog, "NVIDIA GeForce RTX 5090", "COMMUNITY"),
            0.69,
        )
        self.assertEqual(
            MODULE.gpu_hourly_price(catalog, "NVIDIA GeForce RTX 5090", "SECURE"),
            0.99,
        )

    def test_delete_retries_only_transient_runpod_errors(self) -> None:
        calls: list[list[str]] = []
        results = iter(
            [
                MODULE.CommandResult(1, '{"code":"network_error"}', ""),
                MODULE.CommandResult(0, "{}", ""),
            ]
        )

        def runner(command: list[str]):
            calls.append(command)
            return next(results)

        sleeps: list[float] = []
        MODULE.delete_pod("pod12345", runner=runner, sleep=sleeps.append)
        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, [2.0])

        calls.clear()
        with self.assertRaisesRegex(MODULE.CiError, "URGENT"):
            MODULE.delete_pod(
                "pod12345",
                runner=lambda command: (
                    calls.append(command)
                    or MODULE.CommandResult(1, '{"code":"bad_request"}', "")
                ),
                sleep=sleeps.append,
            )
        self.assertEqual(len(calls), 1)

    def test_command_retry_recovers_a_transient_scp_close(self) -> None:
        results = iter(
            [
                MODULE.CommandResult(255, "", "scp: Connection closed"),
                MODULE.CommandResult(255, "", "scp: Connection closed"),
                MODULE.CommandResult(0, "", ""),
            ]
        )
        calls: list[list[str]] = []
        sleeps: list[float] = []
        result = MODULE.run_with_retries(
            ["scp", "bundle", "host:/workspace/bundle"],
            "bundle transfer",
            runner=lambda command: calls.append(list(command)) or next(results),
            sleep=sleeps.append,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleeps, [2.0, 5.0])

    def test_source_must_be_clean_and_committed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(
                ["git", "-C", str(source), "config", "core.fsmonitor", "false"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(source), "config", "user.name", "RunPod CI Test"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(source), "config", "user.email", "test@example.invalid"],
                check=True,
            )
            tracked = source / "tracked.txt"
            tracked.write_text("clean\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(source), "add", "tracked.txt"], check=True)
            subprocess.run(
                ["git", "-C", str(source), "commit", "-q", "-m", "test: seed fixture"],
                check=True,
            )
            commit = MODULE.validate_source(source)
            self.assertRegex(commit, r"^[0-9a-f]{40}$")

            tracked.write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.CiError, "completely clean"):
                MODULE.validate_source(source)

    def test_remote_script_binds_identity_and_cleanup_sensitive_tests(self) -> None:
        source = "1" * 40
        upstream = "2" * 40
        script = MODULE.remote_script(
            source_commit=source,
            upstream_base=upstream,
            cuda_arch="120a",
            cuda_packages=MODULE.DEFAULT_CUDA_PACKAGES,
            build_targets=MODULE.DEFAULT_BUILD_TARGETS,
            ctest_regex=MODULE.DEFAULT_CTEST_REGEX,
        )
        self.assertIn("set -euo pipefail", script)
        self.assertIn("cuda-compiler-13-1", script)
        self.assertIn("cuda-libraries-dev-13-1", script)
        self.assertIn("cuda-nvtx-13-1", script)
        self.assertIn("libssl-dev", script)
        self.assertIn("-DCMAKE_CUDA_ARCHITECTURES=120a", script)
        self.assertIn(f"-DNINFER_PATCH_STACK_SHA={source}", script)
        self.assertIn(f"-DNINFER_UPSTREAM_BASE_SHA={upstream}", script)
        self.assertIn("ninfer_tool_call_parser_test", script)
        self.assertIn("ninfer_checkpoint_io_contract_test", script)
        self.assertIn("ninfer_resource_manager_test", script)
        self.assertIn("build/runpod/apps/ninfer-serve --version", script)

    def test_remote_script_uses_the_requested_build_targets(self) -> None:
        script = MODULE.remote_script(
            source_commit="1" * 40,
            upstream_base="2" * 40,
            cuda_arch="86",
            cuda_packages=MODULE.DEFAULT_CUDA_PACKAGES,
            build_targets=("ninfer-serve", "ninfer_session_checkpoint_store_test"),
            ctest_regex="ninfer_session_checkpoint_store_test",
        )
        self.assertIn(
            "--target ninfer-serve ninfer_session_checkpoint_store_test", script
        )
        self.assertNotIn("ninfer_checkpoint_io_contract_test", script)

    def test_receipt_is_atomic_and_contains_no_connection_details(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            receipt = {
                "artifact_type": "omp_ninfer_runpod_ci_receipt",
                "pod_id": "pod12345",
                "status": "passed",
            }
            MODULE.write_receipt(path, receipt)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), receipt)
            self.assertFalse(path.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
