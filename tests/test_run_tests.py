"""The module runner preserves failures, empty selections, isolation and shard coverage."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_tests.py"
SPEC = importlib.util.spec_from_file_location("contract_runner", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)

PASSING = """import unittest
class ContractTests(unittest.TestCase):
    def test_passes(self):
        self.assertTrue(True)
"""


class RunnerTests(unittest.TestCase):
    def invoke(self, directory: Path, *arguments: str,
               env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--test-dir", str(directory), *arguments],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=False, timeout=60, env=env,
        )

    def write_module(self, directory: Path, name: str, source: str = PASSING) -> None:
        (directory / (name + ".py")).write_text(source, encoding="utf-8")

    def test_assertion_failure_fails_the_run_and_prints_its_complete_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_module(directory, "test_pass")
            self.write_module(directory, "test_failure", PASSING.replace(
                "self.assertTrue(True)", "print('failure output'); self.fail('assertion detail')"))
            result = self.invoke(directory, "--jobs", "2")
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS test_pass", result.stdout)
            self.assertIn("FAIL test_failure", result.stdout)
            self.assertIn("failure output", result.stdout)
            self.assertIn("AssertionError: assertion detail", result.stdout)
            self.assertIn("2 tests in 2 modules, 1 failed", result.stdout)

    def test_import_crash_fails_the_run_and_reports_the_exception(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_module(directory, "test_crash", "raise RuntimeError('import crashed')\n")
            result = self.invoke(directory)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("FAIL test_crash", result.stdout)
            self.assertIn("RuntimeError: import crashed", result.stdout)

    def test_abrupt_child_exit_cannot_be_reported_as_success(self) -> None:
        for code in (0, 7):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                self.write_module(directory, "test_exit", f"import os\nos._exit({code})\n")
                result = self.invoke(directory)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(f"exit {code}; zero tests or missing unittest result", result.stdout)

    @unittest.skipIf(os.name == "nt", "POSIX signal termination status")
    def test_a_signal_killed_child_fails_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_module(directory, "test_killed",
                              "import os, signal\nos.kill(os.getpid(), signal.SIGTERM)\n")
            result = self.invoke(directory)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("FAIL test_killed", result.stdout)
            self.assertIn("exit -15", result.stdout)

    def test_a_module_with_zero_tests_fails_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_module(directory, "test_empty", "VALUE = 1\n")
            result = self.invoke(directory)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("zero tests or missing unittest result", result.stdout)

    def test_empty_discovery_and_an_empty_shard_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            result = self.invoke(directory)
            self.assertEqual(result.returncode, 2)
            self.assertIn("selection contains no test modules", result.stderr)
            self.write_module(directory, "test_only")
            result = self.invoke(directory, "--shard", "2/2")
            self.assertEqual(result.returncode, 2)
            self.assertIn("selection contains no test modules", result.stderr)

    def test_shards_partition_discovery_exactly_and_execute_every_selected_module(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            names = {f"test_fixture_{index:02d}" for index in range(11)}
            for name in names:
                self.write_module(directory, name)
            (directory / "helper.py").write_text("raise RuntimeError('not a test')\n")
            all_modules = self.invoke(directory, "--list")
            self.assertEqual(all_modules.returncode, 0, all_modules.stderr)
            self.assertEqual(set(all_modules.stdout.splitlines()), names)
            shards = []
            for index in range(1, 4):
                listed = self.invoke(directory, "--shard", f"{index}/3", "--list")
                self.assertEqual(listed.returncode, 0, listed.stderr)
                selected = set(listed.stdout.splitlines())
                self.assertEqual(selected, set(sorted(names)[index - 1::3]))
                shards.append(selected)
                result = self.invoke(directory, "--shard", f"{index}/3", "--jobs", "2")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                executed = {line.split()[1] for line in result.stdout.splitlines()
                            if line.startswith("PASS ")}
                self.assertEqual(executed, selected)
            self.assertEqual(set.union(*shards), names)
            for index, selected in enumerate(shards):
                for other in shards[index + 1:]:
                    self.assertFalse(selected & other)

    def test_invalid_jobs_shards_and_durations_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_module(directory, "test_only")
            for arguments in (("--jobs", "0"), ("--jobs", "-1"), ("--durations", "-1"),
                              ("--shard", "0/2"), ("--shard", "3/2"),
                              ("--shard", "1/0"), ("--shard", "1/2/3"),
                              ("--shard", "not-a-shard")):
                with self.subTest(arguments=arguments):
                    result = self.invoke(directory, *arguments)
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_longest_first_order_and_shards_do_not_depend_on_timing_estimates(self) -> None:
        names = ["test_a", "test_b", "test_c", "test_d"]
        with mock.patch.object(RUNNER, "MODULE_SECONDS", {"test_b": 8, "test_c": 3}):
            self.assertEqual(RUNNER.select_modules(names, None),
                             ["test_b", "test_c", "test_a", "test_d"])
            self.assertEqual(RUNNER.select_modules(list(reversed(names)), (1, 2)),
                             ["test_c", "test_a"])
        with mock.patch.object(RUNNER, "MODULE_SECONDS", {"test_a": 100}):
            self.assertEqual(set(RUNNER.select_modules(names, (1, 2))), {"test_a", "test_c"})

    def test_parallelism_is_bounded_and_serial_modules_have_no_overlap(self) -> None:
        import threading
        active: set[str] = set()
        overlaps = []
        barrier = threading.Barrier(2)
        lock = threading.Lock()

        def child(directory: Path, module: str, windows_skips: bool):
            with lock:
                active.add(module)
                overlaps.append(set(active))
            if module != "test_serial":
                barrier.wait(timeout=10)
            with lock:
                active.remove(module)
            return RUNNER.ModuleResult(module, 0.1, 0, 1, "")

        with mock.patch.object(RUNNER, "SERIAL_MODULES", ("test_serial",)), \
                mock.patch.object(RUNNER, "run_module", side_effect=child), \
                contextlib.redirect_stdout(io.StringIO()):
            results = RUNNER.run_modules(Path("."), ["test_a", "test_serial", "test_b"], 2, False)
        self.assertEqual(len(results), 3)
        self.assertIn({"test_a", "test_b"}, overlaps)
        self.assertIn({"test_serial"}, overlaps)
        self.assertTrue(all(len(group) <= 2 for group in overlaps))
        self.assertTrue(all(group == {"test_serial"} for group in overlaps if "test_serial" in group))

    def test_environment_is_forwarded_without_runner_variables(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            environment = dict(os.environ, CONTRACT_RUNNER_SENTINEL="inherited verbatim")
            self.write_module(directory, "test_environment", PASSING.replace(
                "self.assertTrue(True)",
                "import os; self.assertEqual(dict(os.environ), " + repr(environment) + ")"))
            result = self.invoke(directory, env=environment)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_windows_exclusions_use_the_same_module_subprocess_path(self) -> None:
        source = """import unittest
class RunnerTests(unittest.TestCase):
    def test_posix(self):
        self.fail('POSIX fixture must be skipped')
class ExtractionTests(unittest.TestCase):
    def test_restart_seed_never_contains_the_planted_nonce(self):
        self.fail('POSIX pipeline must be skipped')
    def test_restart_seed_stays_between_the_checkpoint_gate_and_client_compaction(self):
        self.fail('POSIX pipeline must be skipped')
    def test_portable_extraction(self):
        self.assertTrue(True)
class PortableTests(unittest.TestCase):
    def test_portable(self):
        self.assertTrue(True)
"""
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_module(directory, "test_documented_route", source)
            result = self.invoke(directory, "--windows-skips")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS test_documented_route (5 tests,", result.stdout)
            result = self.invoke(directory)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("5 tests in 1 modules, 1 failed", result.stdout)

    def test_all_windows_exclusions_preserve_unlisted_tests(self) -> None:
        from types import ModuleType
        modules = {}
        for name, class_name, _ in RUNNER.WINDOWS_CLASS_SKIPS:
            module = modules.setdefault(name, ModuleType(name))
            setattr(module, class_name, type(class_name, (unittest.TestCase,),
                                             {"test_fixture": lambda self: self.fail("not skipped")}))
        for name, class_name, methods, _ in RUNNER.WINDOWS_METHOD_SKIPS:
            module = modules.setdefault(name, ModuleType(name))
            setattr(module, class_name, type(class_name, (unittest.TestCase,),
                                             {method: lambda self: self.fail("not skipped")
                                              for method in methods}))
        for module in modules.values():
            module.PortableTests = type("PortableTests", (unittest.TestCase,),
                                        {"test_portable": lambda self: self.assertTrue(True)})
            RUNNER.apply_windows_skips(module)
            suite = unittest.TestLoader().loadTestsFromModule(module)
            result = unittest.TestResult()
            suite.run(result)
            self.assertTrue(result.wasSuccessful(), result.errors + result.failures)
            self.assertEqual(len(result.skipped), result.testsRun - 1)

    def test_default_jobs_and_duration_count_are_respected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_module(directory, "test_only")
            with mock.patch.object(RUNNER.os, "cpu_count", return_value=3):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = RUNNER.main(["--test-dir", str(directory), "--durations", "1"])
            self.assertEqual(code, 0, output.getvalue())
            self.assertIn("with 3 jobs", output.getvalue())
            self.assertIn("Slowest modules:", output.getvalue())
            result = self.invoke(directory, "--durations", "0")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("Slowest modules:", result.stdout)


if __name__ == "__main__":
    unittest.main()
