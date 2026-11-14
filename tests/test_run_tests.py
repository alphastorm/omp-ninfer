"""The chunk runner preserves failures, isolation and exact test-id coverage."""

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

WINDOWS_FIXTURE = """import unittest
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

    def write_split_module(self, directory: Path, count: int = 13, fail: bool = False) -> set[str]:
        source = "import unittest\nclass ContractTests(unittest.TestCase):\n"
        for index in range(count):
            body = "self.fail('chunk failure detail')" if fail and index == 0 else "self.assertTrue(True)"
            source += f"    def test_{index:02d}(self):\n        {body}\n"
        self.write_module(directory, "test_verify_release", source)
        return {f"test_verify_release.ContractTests.test_{index:02d}" for index in range(count)}

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
            self.assertIn("2 tests in 2 modules, 2 chunks, 1 failed", result.stdout)

    def test_import_crash_fails_the_run_and_reports_the_exception(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_module(directory, "test_crash", "raise RuntimeError('import crashed')\n")
            result = self.invoke(directory)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("FAIL test_crash", result.stdout)
            self.assertIn("RuntimeError: import crashed", result.stdout)

    def test_abrupt_child_exit_cannot_be_reported_as_success(self) -> None:
        for phase in ("import", "test"):
            for code in (0, 7):
                with self.subTest(code=code, phase=phase), tempfile.TemporaryDirectory() as temporary:
                    directory = Path(temporary)
                    source = (f"import os\nos._exit({code})\n" if phase == "import" else
                              PASSING.replace("self.assertTrue(True)", f"import os; os._exit({code})"))
                    self.write_module(directory, "test_exit", source)
                    result = self.invoke(directory)
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn(f"exit {code}; zero tests or missing unittest result", result.stdout)

    @unittest.skipIf(os.name == "nt", "POSIX signal termination status")
    def test_a_signal_killed_child_fails_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_module(directory, "test_killed", PASSING.replace(
                "self.assertTrue(True)", "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"))
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

    def test_shards_partition_discovery_exactly_and_execute_every_selected_chunk(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            names = {f"test_fixture_{index:02d}" for index in range(11)}
            for name in names:
                self.write_module(directory, name)
            (directory / "helper.py").write_text("raise RuntimeError('not a test')\n")
            expected = {name + ".ContractTests.test_passes" for name in names}
            listed = self.invoke(directory, "--list-tests")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertEqual(set(listed.stdout.splitlines()), expected)
            shards = []
            for index in range(1, 4):
                listed = self.invoke(directory, "--shard", f"{index}/3", "--list-tests")
                self.assertEqual(listed.returncode, 0, listed.stderr)
                selected = set(listed.stdout.splitlines())
                shards.append(selected)
                result = self.invoke(directory, "--shard", f"{index}/3", "--jobs", "2")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                executed = {line.split()[1] for line in result.stdout.splitlines()
                            if line.startswith("PASS ")}
                self.assertEqual(executed, {test_id.split(".")[0] for test_id in selected})
            self.assertEqual(set.union(*shards), expected)
            for index, selected in enumerate(shards):
                for other in shards[index + 1:]:
                    self.assertFalse(selected & other)

    def test_chunks_and_shards_partition_ids_exactly_including_windows_exclusions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            verifier_ids = self.write_split_module(directory)
            self.write_module(directory, "test_documented_route", WINDOWS_FIXTURE)
            self.write_module(directory, "test_plain")
            chunks = RUNNER.split_module("test_verify_release", tuple(reversed(sorted(verifier_ids))))
            self.assertEqual(len(chunks), 4)
            self.assertEqual(set.union(*(set(chunk.test_ids) for chunk in chunks)), verifier_ids)
            for index, chunk in enumerate(chunks):
                self.assertEqual(chunk.test_ids, tuple(sorted(verifier_ids)[index::4]))
                self.assertEqual(chunk.estimated_seconds, 201 / 4)
                for other in chunks[index + 1:]:
                    self.assertFalse(set(chunk.test_ids) & set(other.test_ids))
            expected = verifier_ids | {
                "test_plain.ContractTests.test_passes",
                "test_documented_route.RunnerTests.test_posix",
                "test_documented_route.ExtractionTests.test_restart_seed_never_contains_the_planted_nonce",
                "test_documented_route.ExtractionTests.test_restart_seed_stays_between_the_checkpoint_gate_and_client_compaction",
                "test_documented_route.ExtractionTests.test_portable_extraction",
                "test_documented_route.PortableTests.test_portable",
            }
            for flags in ((), ("--windows-skips",)):
                with self.subTest(flags=flags):
                    listed = self.invoke(directory, *flags, "--list-tests")
                    self.assertEqual(listed.returncode, 0, listed.stdout + listed.stderr)
                    self.assertEqual(set(listed.stdout.splitlines()), expected)
                    shards = []
                    for index in range(1, 5):
                        listed = self.invoke(directory, *flags, "--shard", f"{index}/4", "--list-tests")
                        self.assertEqual(listed.returncode, 0, listed.stdout + listed.stderr)
                        selected = set(listed.stdout.splitlines())
                        self.assertTrue(selected)
                        self.assertTrue(all(not selected & other for other in shards))
                        shards.append(selected)
                    self.assertEqual(set.union(*shards), expected)
            listed = self.invoke(directory, "--list")
            self.assertEqual(listed.returncode, 0, listed.stdout + listed.stderr)
            for index in range(1, 5):
                self.assertIn(f"test_verify_release[{index}/4]\t50.250s", listed.stdout)
            self.assertIn("estimated_seconds=253.000", listed.stdout)

    def test_a_failure_in_one_chunk_fails_the_run_and_names_the_chunk(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_split_module(directory, count=9, fail=True)
            result = self.invoke(directory, "--jobs", "2")
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("FAIL test_verify_release[1/4]", result.stdout)
            self.assertIn("PASS test_verify_release[2/4]", result.stdout)
            self.assertIn("AssertionError: chunk failure detail", result.stdout)
            self.assertIn("9 tests in 1 modules, 4 chunks, 1 failed", result.stdout)
            self.assertIn("Slowest chunks:", result.stdout)
            self.assertIn("Module totals (sum of chunk elapsed seconds):", result.stdout)

    def test_an_empty_chunk_fails_even_when_unittest_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_module(directory, "test_only")
            chunk = RUNNER.Chunk("test_only", (), 1, 2, 1)
            result = RUNNER.run_chunk(directory, chunk, False)
            self.assertEqual(result.tests, 0)
            self.assertFalse(result.passed)
            # unittest versions differ on whether an empty suite itself exits zero.
            self.assertFalse(result._replace(returncode=0).passed)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                RUNNER.report(result)
            self.assertIn("FAIL test_only[1/2]", output.getvalue())
            self.assertIn("zero tests or missing unittest result", output.getvalue())

    def test_oversized_module_enumeration_failure_cannot_fall_back_to_an_unsplit_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_module(directory, "test_verify_release", "raise RuntimeError('cannot enumerate')\n")
            for flags in ((), ("--list",), ("--list-tests", "--shard", "4/4")):
                with self.subTest(flags=flags):
                    result = self.invoke(directory, *flags)
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("test-id enumeration failed", result.stdout)
                    self.assertIn("RuntimeError: cannot enumerate", result.stdout)
                    self.assertNotIn("PASS ", result.stdout)

    def test_duplicate_test_ids_are_refused_instead_of_overlapping_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_module(directory, "test_verify_release", PASSING + """
def load_tests(loader, suite, pattern):
    return unittest.TestSuite([ContractTests('test_passes'), ContractTests('test_passes')])
""")
            result = self.invoke(directory, "--list-tests")
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("duplicate test ids cannot be partitioned", result.stdout)

    def test_class_and_module_fixtures_run_once_per_chunk(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = """import unittest
module_setups = 0
def setUpModule():
    global module_setups
    module_setups += 1
class ContractTests(unittest.TestCase):
    class_setups = 0
    @classmethod
    def setUpClass(cls):
        cls.class_setups += 1
"""
            for index in range(12):
                source += (f"    def test_{index:02d}(self):\n"
                           "        self.assertEqual(module_setups, 1)\n"
                           "        self.assertEqual(self.class_setups, 1)\n")
            self.write_module(directory, "test_verify_release", source)
            result = self.invoke(directory, "--jobs", "2")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("12 tests in 1 modules, 4 chunks, 0 failed", result.stdout)

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

    def test_longest_first_and_weight_balancing_are_deterministic(self) -> None:
        names = ["test_a", "test_b", "test_c", "test_d"]
        with mock.patch.object(RUNNER, "MODULE_SECONDS", {"test_b": 8, "test_c": 3}):
            chunks = [RUNNER.split_module(name, (name + ".ContractTests.test_passes",))[0]
                      for name in names]
            self.assertEqual([chunk.module for chunk in RUNNER.select_chunks(chunks, None)],
                             ["test_b", "test_c", "test_a", "test_d"])
            shards = [RUNNER.select_chunks(chunks, (index, 2)) for index in (1, 2)]
            self.assertEqual(shards, [RUNNER.select_chunks(list(reversed(chunks)), (index, 2))
                                      for index in (1, 2)])
            self.assertEqual({chunk.module for chunk in shards[0]}, {"test_b"})
            self.assertEqual({chunk.module for chunk in shards[1]}, {"test_a", "test_c", "test_d"})
            totals = [sum(chunk.estimated_seconds for chunk in shard) for shard in shards]
            self.assertLessEqual(max(totals) - min(totals), max(chunk.estimated_seconds for chunk in chunks))

    def test_parallelism_is_bounded_and_serial_modules_have_no_overlap(self) -> None:
        import threading
        active: set[str] = set()
        overlaps = []
        barrier = threading.Barrier(2)
        lock = threading.Lock()

        def child(directory: Path, chunk, windows_skips: bool):
            module = chunk.module
            with lock:
                active.add(module)
                overlaps.append(set(active))
            if module != "test_serial":
                barrier.wait(timeout=10)
            with lock:
                active.remove(module)
            return RUNNER.ChunkResult(chunk, 0.1, 0, 1, "")

        with mock.patch.object(RUNNER, "SERIAL_MODULES", ("test_serial",)), \
                mock.patch.object(RUNNER, "run_chunk", side_effect=child), \
                contextlib.redirect_stdout(io.StringIO()):
            chunks = [RUNNER.Chunk(name, (name + ".ContractTests.test_passes",), 1, 1, 1)
                      for name in ("test_a", "test_serial", "test_b")]
            results = RUNNER.run_chunks(Path("."), chunks, 2, False)
        self.assertEqual(len(results), 3)
        self.assertIn({"test_a", "test_b"}, overlaps)
        self.assertIn({"test_serial"}, overlaps)
        self.assertTrue(all(len(group) <= 2 for group in overlaps))
        self.assertTrue(all(group == {"test_serial"} for group in overlaps if "test_serial" in group))

    def test_environment_is_forwarded_without_runner_variables(self) -> None:
        import hashlib
        import json
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            environment = dict(os.environ, CONTRACT_RUNNER_SENTINEL="inherited verbatim")
            digest = hashlib.sha256(json.dumps(environment, sort_keys=True).encode()).hexdigest()
            self.write_module(directory, "test_environment", PASSING.replace(
                "self.assertTrue(True)",
                "import hashlib, json, os; self.assertEqual("
                "hashlib.sha256(json.dumps(dict(os.environ), sort_keys=True).encode()).hexdigest(), "
                + repr(digest) + ")"))
            result = self.invoke(directory, env=environment)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_windows_exclusions_use_the_same_module_subprocess_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_module(directory, "test_documented_route", WINDOWS_FIXTURE)
            result = self.invoke(directory, "--windows-skips")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS test_documented_route (5 tests,", result.stdout)
            result = self.invoke(directory)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("5 tests in 1 modules, 1 chunks, 1 failed", result.stdout)

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
            self.assertIn("Slowest chunks:", output.getvalue())
            self.assertIn("Module totals (sum of chunk elapsed seconds):", output.getvalue())
            result = self.invoke(directory, "--durations", "0")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("Slowest chunks:", result.stdout)


if __name__ == "__main__":
    unittest.main()
