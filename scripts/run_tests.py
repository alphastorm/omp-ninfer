"""Run the contract suite in isolated, bounded-concurrency unittest processes."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from types import ModuleType
from typing import NamedTuple
import unittest

ROOT = Path(__file__).resolve().parents[1]

# Fixed estimates keep scheduling deterministic across checkouts. Unknown modules use one
# second until a measured suite run justifies updating these estimates.
MODULE_SECONDS = {
    "test_documented_route": 170,
    "test_verify_release": 116,
    "test_accept_rtx4090_route": 41,
    "test_concurrency_probe": 22,
    "test_native_screen_arm": 13,
    "test_stage_release": 10,
    "test_agent_parity": 8,
    "test_cut_native_component": 5,
    "test_manual_tunnel_scripts": 5,
    "test_accept_rtx5090_documented_model": 3,
    "test_client_acceptance": 2,
    "test_accept_windows_client": 2,
    "test_publish_product_release": 2,
}

# Reserved for modules empirically shown to share ports or process-global state across
# subprocesses. Entries must name the observed conflict; isolated fixtures need no entry.
SERIAL_MODULES: tuple[str, ...] = ()

POSIX_REASON = "POSIX executable/path/permission fixtures; covered on Ubuntu and macOS"
WINDOWS_CLASS_SKIPS = (
    ("test_cut_native_component", "NativeCutterTests", POSIX_REASON),
    ("test_documented_route", "RunnerTests", POSIX_REASON),
    ("test_fleet_example", "FleetExampleTests", POSIX_REASON),
    ("test_manual_tunnel_scripts", "ManualTunnelScriptsTest", POSIX_REASON),
)
WINDOWS_METHOD_SKIPS = (
    (
        "test_documented_route",
        "ExtractionTests",
        (
            "test_restart_seed_never_contains_the_planted_nonce",
            "test_restart_seed_stays_between_the_checkpoint_gate_and_client_compaction",
        ),
        "executes the documented POSIX seed pipeline",
    ),
    (
        "test_accept_rtx4090_route",
        "NativeLaneTests",
        (
            "test_powershell_baseline_enforces_lane_power_and_operator_holds",
            "test_optional_native_directories_preserve_presence_in_both_lineage_modes",
        ),
        "scratch C: PSDrive fixture runs on Ubuntu and macOS",
    ),
)


def apply_windows_skips(module: ModuleType) -> None:
    """Apply exactly the native-Windows fixture exclusions used by CI and local runs."""
    for name, class_name, reason in WINDOWS_CLASS_SKIPS:
        if module.__name__ == name:
            cls = getattr(module, class_name)
            cls.__unittest_skip__ = True
            cls.__unittest_skip_why__ = reason
    for name, class_name, methods, reason in WINDOWS_METHOD_SKIPS:
        if module.__name__ == name:
            cls = getattr(module, class_name)
            for method in methods:
                setattr(cls, method, unittest.skip(reason)(getattr(cls, method)))


def discover_modules(directory: Path, pattern: str = "test_*.py") -> list[str]:
    """Discover top-level contract modules without importing or executing their tests."""
    return sorted(path.stem for path in directory.glob(pattern)
                  if path.is_file() and path.name.startswith("test_") and path.suffix == ".py")


def select_modules(modules: list[str], shard: tuple[int, int] | None) -> list[str]:
    """Assign sorted names by round robin, independently of duration estimates."""
    ordered = sorted(modules)
    if shard is not None:
        index, total = shard
        ordered = ordered[index - 1::total]
    return sorted(ordered, key=lambda name: (-MODULE_SECONDS.get(name, 1), name))


class ModuleResult(NamedTuple):
    module: str
    seconds: float
    returncode: int
    tests: int
    output: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0 and self.tests > 0


def run_module(directory: Path, module: str, windows_skips: bool) -> ModuleResult:
    """Keep unittest's CLI and inherited environment, including for Windows exclusions."""
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="contract-tests-") as temporary:
        start = directory
        pattern = module + ".py"
        excluded = {name for name, *_ in WINDOWS_CLASS_SKIPS + WINDOWS_METHOD_SKIPS}
        if windows_skips and module in excluded:
            # A discovery adapter lets the real `python -m unittest` subprocess apply skips
            # before loading this module's suite. No PYTHONPATH or other environment changes.
            start = Path(temporary)
            pattern = "windows_" + module + ".py"
            (start / pattern).write_text(
                "import importlib\n"
                "import importlib.util\n"
                "import sys\n"
                f"sys.path.insert(0, {str(directory)!r})\n"
                f"spec = importlib.util.spec_from_file_location('contract_runner', {str(Path(__file__).resolve())!r})\n"
                "runner = importlib.util.module_from_spec(spec)\n"
                "spec.loader.exec_module(runner)\n"
                "def load_tests(loader, suite, pattern):\n"
                f"    module = importlib.import_module({module!r})\n"
                "    runner.apply_windows_skips(module)\n"
                "    return loader.loadTestsFromModule(module)\n",
                encoding="utf-8",
            )
        command = [sys.executable, "-m", "unittest", "discover", "-s", str(start),
                   "-p", pattern, "-v"]
        try:
            completed = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                       errors="replace", check=False)
            output, returncode = completed.stdout, completed.returncode
        except OSError as exc:
            output, returncode = str(exc), 1
    counts = re.findall(r"(?m)^Ran (\d+) tests? in ", output)
    return ModuleResult(module, time.perf_counter() - started, returncode,
                        int(counts[-1]) if counts else 0, output)


def report(result: ModuleResult) -> None:
    status = "PASS" if result.passed else "FAIL"
    print(f"{status} {result.module} ({result.tests} tests, {result.seconds:.3f}s)", flush=True)
    if not result.passed:
        print(f"--- {result.module}: exit {result.returncode}"
              f"{'; zero tests or missing unittest result' if result.tests == 0 else ''} ---",
              flush=True)
        print(result.output, end="" if result.output.endswith("\n") else "\n", flush=True)
        print(f"--- end {result.module} ---", flush=True)


def run_modules(directory: Path, modules: list[str], jobs: int,
                windows_skips: bool) -> list[ModuleResult]:
    results = []
    parallel = [module for module in modules if module not in SERIAL_MODULES]
    if parallel:
        with ThreadPoolExecutor(max_workers=min(jobs, len(parallel))) as executor:
            pending = [executor.submit(run_module, directory, module, windows_skips)
                       for module in parallel]
            for future in as_completed(pending):
                result = future.result()
                results.append(result)
                report(result)
    # Serial modules run only after every parallel child has exited, never alongside a suite.
    for module in modules:
        if module in SERIAL_MODULES:
            result = run_module(directory, module, windows_skips)
            results.append(result)
            report(result)
    return results


def positive_integer(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def nonnegative_integer(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be a nonnegative integer")
    return number


def shard_argument(value: str) -> tuple[int, int]:
    try:
        index, total = (int(part) for part in value.split("/"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be I/N with 1 <= I <= N") from exc
    if not 1 <= index <= total:
        raise argparse.ArgumentTypeError("must be I/N with 1 <= I <= N")
    return index, total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=positive_integer, default=os.cpu_count() or 1,
                        help="maximum parallel modules (default: CPU count)")
    parser.add_argument("--shard", type=shard_argument, metavar="I/N",
                        help="run the I-th stable name-based shard, numbered from one")
    parser.add_argument("--durations", type=nonnegative_integer, default=10, metavar="K",
                        help="print the K slowest modules (default: 10; zero disables)")
    parser.add_argument("--windows-skips", action="store_true",
                        help="apply native-Windows fixture exclusions, as CI does")
    parser.add_argument("--test-dir", type=Path, default=ROOT / "tests",
                        help="directory containing test modules (default: repository tests)")
    parser.add_argument("--pattern", default="test_*.py",
                        help="module filename pattern (default: test_*.py)")
    parser.add_argument("--list", action="store_true", help="list selected modules without running")
    args = parser.parse_args(argv)
    directory = args.test_dir.resolve()
    modules = select_modules(discover_modules(directory, args.pattern), args.shard)
    if not modules:
        parser.error("selection contains no test modules")
    if args.list:
        print("\n".join(modules))
        return 0
    print(f"Running {len(modules)} modules with {args.jobs} jobs"
          f"{' (Windows fixture exclusions)' if args.windows_skips else ''}", flush=True)
    started = time.perf_counter()
    results = run_modules(directory, modules, args.jobs, args.windows_skips)
    failed = sum(not result.passed for result in results)
    print(f"{'FAILED' if failed else 'OK'}: {sum(result.tests for result in results)} tests"
          f" in {len(results)} modules, {failed} failed, {time.perf_counter() - started:.3f}s wall",
          flush=True)
    if args.durations:
        print("Slowest modules:", flush=True)
        for result in sorted(results, key=lambda item: (-item.seconds, item.module))[:args.durations]:
            print(f"  {result.seconds:9.3f}s  {result.module}", flush=True)
    return int(failed > 0)


if __name__ == "__main__":
    raise SystemExit(main())
