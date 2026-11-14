"""Run measured, balanced contract-suite chunks in isolated unittest processes."""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import contextlib
import json
import math
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
    "test_verify_release": 201,
    "test_documented_route": 51,
    "test_stage_release": 50,
    "test_accept_rtx4090_route": 47,
    "test_concurrency_probe": 24,
    "test_native_screen_arm": 18,
    "test_manual_tunnel_scripts": 17,
    "test_cut_native_component": 15,
    "test_agent_parity": 14,
    "test_publish_product_release": 7,
    "test_stock_client_harness": 5,
    "test_run_tests": 5,
    "test_accept_rtx5090_documented_model": 4,
    "test_client_acceptance": 3,
    "test_run_variant_campaign": 3,
    "test_accept_windows_client": 3,
    "test_compose_route_acceptance": 3,
    "test_rebind_release": 3,
    "test_quality_screen": 2,
}
# The verifier measures about 200 seconds; the next modules measure 47-53 seconds.
# A 60-second target splits only that outlier into four roughly 50-second chunks.
SPLIT_SECONDS = 60

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
    (
        "test_release_driver",
        "ReleaseDriverTests",
        (
            "test_publish_only_wraps_preflight_with_exact_head",
            "test_tool_mode_change_refuses_the_group_without_committing",  # Requires executable bits.
        ),
        "runs the POSIX publication preflight script",
    ),
    (
        "test_release_cut",
        "ReleaseCutTests",
        (
            "test_default_is_only_dry_run_with_derived_arguments_and_private_state",
            "test_authorized_publish_runs_dry_then_publish_then_authenticates",
            "test_dry_run_failure_never_publishes_or_saves_inputs",
            "test_authorization_is_rechecked_after_dry_run",
            "test_failed_publication_never_authenticates_or_records",
            "test_existing_public_tag_is_authenticated_without_republishing",
            "test_authenticated_publish_rerun_never_publishes_twice",
            "test_differing_public_bytes_names_both_digests_and_records_nothing",
            "test_failed_reauthentication_preserves_the_prior_record_and_state",
            "test_status_and_next_report_recorded_without_network_or_tool_calls",
            "test_external_package_is_streamed_to_a_closed_nonaliasing_asset_directory",
        ),
        "runs the POSIX component cut recording script",
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


class Chunk(NamedTuple):
    module: str
    test_ids: tuple[str, ...]
    index: int
    total: int
    estimated_seconds: float

    @property
    def label(self) -> str:
        return self.module if self.total == 1 else f"{self.module}[{self.index}/{self.total}]"


class ChunkResult(NamedTuple):
    chunk: Chunk
    seconds: float
    returncode: int
    tests: int
    output: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0 and self.tests > 0 and self.tests == len(self.chunk.test_ids)


class ModuleTests(NamedTuple):
    module: str
    test_ids: tuple[str, ...]
    seconds: float
    returncode: int
    output: str


def iter_test_ids(suite: unittest.TestSuite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from iter_test_ids(test)
        else:
            yield test.id()


def emit_test_ids(directory: Path, module: str, windows_skips: bool) -> int:
    """Internal subprocess entry point: enumerate with unittest, never execute a test."""
    loader = unittest.TestLoader()
    # Import-time prints are diagnostics, not part of the JSON enumeration protocol.
    with contextlib.redirect_stdout(sys.stderr):
        suite = loader.discover(str(directory), pattern=module + ".py")
        if loader.errors:
            print("\n".join(loader.errors), file=sys.stderr)
            return 1
        if windows_skips:
            apply_windows_skips(sys.modules[module])
        ids = sorted(iter_test_ids(suite))
    if not ids:
        print(f"{module}: zero tests discovered", file=sys.stderr)
        return 1
    if len(set(ids)) != len(ids):
        print(f"{module}: duplicate test ids cannot be partitioned", file=sys.stderr)
        return 1
    print(json.dumps(ids))
    return 0


def enumerate_tests(directory: Path, module: str, windows_skips: bool) -> ModuleTests:
    started = time.perf_counter()
    command = [sys.executable, str(Path(__file__).resolve()), "--test-dir", str(directory),
               "--_enumerate-module", module]
    if windows_skips:
        command.append("--windows-skips")
    ids: tuple[str, ...] = ()
    try:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", check=False)
        output, returncode = completed.stderr + completed.stdout, completed.returncode
        if returncode == 0:
            try:
                decoded = json.loads(completed.stdout)
                if (not isinstance(decoded, list) or not decoded
                        or not all(isinstance(test_id, str) for test_id in decoded)
                        or len(set(decoded)) != len(decoded)):
                    raise ValueError("expected a nonempty list of unique test ids")
                ids = tuple(sorted(decoded))
            except (ValueError, TypeError) as exc:
                output = f"cannot enumerate {module}: {exc}\n" + output
    except OSError as exc:
        output, returncode = str(exc), 1
    return ModuleTests(module, ids, time.perf_counter() - started, returncode, output)


def split_module(module: str, ids: tuple[str, ...]) -> list[Chunk]:
    seconds = MODULE_SECONDS.get(module, 1)
    count = min(len(ids), math.ceil(seconds / SPLIT_SECONDS))
    ordered = tuple(sorted(ids))
    return [Chunk(module, ordered[index::count], index + 1, count, seconds / count)
            for index in range(count)]


def ordered_chunks(chunks: list[Chunk]) -> list[Chunk]:
    return sorted(chunks, key=lambda chunk: (-chunk.estimated_seconds, chunk.label))


def select_chunks(chunks: list[Chunk], shard: tuple[int, int] | None) -> list[Chunk]:
    """Greedily balance fixed-duration chunks; test ids never move between chunks."""
    ordered = ordered_chunks(chunks)
    if shard is None:
        return ordered
    index, total = shard
    buckets: list[list[Chunk]] = [[] for _ in range(total)]
    seconds = [0.0] * total
    for chunk in ordered:
        destination = min(range(total), key=lambda number: (seconds[number], number))
        buckets[destination].append(chunk)
        seconds[destination] += chunk.estimated_seconds
    return buckets[index - 1]


def plan_chunks(directory: Path, modules: list[str], jobs: int,
                windows_skips: bool) -> tuple[list[Chunk], list[ChunkResult]]:
    chunks = []
    failures = []
    with ThreadPoolExecutor(max_workers=min(jobs, len(modules))) as executor:
        pending = [executor.submit(enumerate_tests, directory, module, windows_skips)
                   for module in modules]
        for future in as_completed(pending):
            discovered = future.result()
            if discovered.returncode != 0 or not discovered.test_ids:
                chunk = Chunk(discovered.module, (), 1, 1,
                              MODULE_SECONDS.get(discovered.module, 1))
                result = ChunkResult(chunk, discovered.seconds, discovered.returncode, 0,
                                     "test-id enumeration failed\n" + discovered.output)
                failures.append(result)
                report(result)
            else:
                chunks.extend(split_module(discovered.module, discovered.test_ids))
    return ordered_chunks(chunks), failures


def run_chunk(directory: Path, chunk: Chunk, windows_skips: bool) -> ChunkResult:
    """Load explicit ids under unittest's CLI without changing the inherited environment."""
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="contract-tests-") as temporary:
        start = Path(temporary)
        pattern = "contract_chunk.py"
        # An adapter avoids Windows command-line length limits while still running explicit
        # ids in a real `python -m unittest` child. Fixtures run once per chunk, not per id.
        (start / pattern).write_text(
            "import importlib\n"
            "import importlib.util\n"
            "import sys\n"
            f"sys.path.insert(0, {str(directory)!r})\n"
            f"spec = importlib.util.spec_from_file_location('contract_runner', {str(Path(__file__).resolve())!r})\n"
            "runner = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(runner)\n"
            "def load_tests(loader, suite, pattern):\n"
            f"    module = importlib.import_module({chunk.module!r})\n"
            + ("    runner.apply_windows_skips(module)\n" if windows_skips else "")
            + f"    return loader.loadTestsFromNames({chunk.test_ids!r})\n",
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
    return ChunkResult(chunk, time.perf_counter() - started, returncode,
                       int(counts[-1]) if counts else 0, output)


def report(result: ChunkResult) -> None:
    status = "PASS" if result.passed else "FAIL"
    print(f"{status} {result.chunk.label} ({result.tests} tests, {result.seconds:.3f}s)", flush=True)
    if not result.passed:
        print(f"--- {result.chunk.label}: exit {result.returncode}"
              f"{'; zero tests or missing unittest result' if result.tests == 0 else ''} ---",
              flush=True)
        print(result.output, end="" if result.output.endswith("\n") else "\n", flush=True)
        if result.tests != len(result.chunk.test_ids):
            print(f"expected {len(result.chunk.test_ids)} tests, ran {result.tests}", flush=True)
        print(f"--- end {result.chunk.label} ---", flush=True)


def run_chunks(directory: Path, chunks: list[Chunk], jobs: int,
               windows_skips: bool) -> list[ChunkResult]:
    results = []
    parallel = [chunk for chunk in chunks if chunk.module not in SERIAL_MODULES]
    if parallel:
        with ThreadPoolExecutor(max_workers=min(jobs, len(parallel))) as executor:
            pending = [executor.submit(run_chunk, directory, chunk, windows_skips)
                       for chunk in parallel]
            for future in as_completed(pending):
                result = future.result()
                results.append(result)
                report(result)
    # Serial chunks run only after every parallel child has exited, and never overlap each other.
    for chunk in chunks:
        if chunk.module in SERIAL_MODULES:
            result = run_chunk(directory, chunk, windows_skips)
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
                        help="maximum parallel chunks (default: CPU count)")
    parser.add_argument("--shard", type=shard_argument, metavar="I/N",
                        help="run the I-th duration-balanced chunk shard, numbered from one")
    parser.add_argument("--durations", type=nonnegative_integer, default=10, metavar="K",
                        help="print the K slowest chunks and module totals (default: 10)")
    parser.add_argument("--windows-skips", action="store_true",
                        help="apply native-Windows fixture exclusions, as CI does")
    parser.add_argument("--test-dir", type=Path, default=ROOT / "tests",
                        help="directory containing test modules (default: repository tests)")
    parser.add_argument("--pattern", default="test_*.py",
                        help="module filename pattern (default: test_*.py)")
    listing = parser.add_mutually_exclusive_group()
    listing.add_argument("--list", action="store_true",
                         help="list selected chunks and estimated seconds without running")
    listing.add_argument("--list-tests", action="store_true",
                         help="list the selected test ids without running")
    parser.add_argument("--_enumerate-module", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    directory = args.test_dir.resolve()
    if args._enumerate_module is not None:
        return emit_test_ids(directory, args._enumerate_module, args.windows_skips)
    started = time.perf_counter()
    modules = discover_modules(directory, args.pattern)
    if not modules:
        parser.error("selection contains no test modules")
    chunks, failures = plan_chunks(directory, modules, args.jobs, args.windows_skips)
    chunks = select_chunks(chunks, args.shard)
    if failures and (args.list or args.list_tests):
        return 1
    if not chunks and not failures:
        parser.error("selection contains no test modules or chunks")
    if args.list:
        for chunk in chunks:
            print(f"{chunk.label}\t{chunk.estimated_seconds:.3f}s\t{len(chunk.test_ids)} tests")
        print(f"estimated_seconds={sum(chunk.estimated_seconds for chunk in chunks):.3f}")
        return 0
    if args.list_tests:
        print("\n".join(sorted(test_id for chunk in chunks for test_id in chunk.test_ids)))
        return 0
    print(f"Running {len(chunks)} chunks with {args.jobs} jobs"
          f"{' (Windows fixture exclusions)' if args.windows_skips else ''}", flush=True)
    results = failures + run_chunks(directory, chunks, args.jobs, args.windows_skips)
    failed = sum(not result.passed for result in results)
    module_count = len({result.chunk.module for result in results})
    print(f"{'FAILED' if failed else 'OK'}: {sum(result.tests for result in results)} tests"
          f" in {module_count} modules, {len(results)} chunks, {failed} failed,"
          f" {time.perf_counter() - started:.3f}s wall",
          flush=True)
    if args.durations:
        print("Slowest chunks:", flush=True)
        for result in sorted(results, key=lambda item: (-item.seconds, item.chunk.label))[:args.durations]:
            print(f"  {result.seconds:9.3f}s  {result.chunk.label}", flush=True)
        totals: dict[str, float] = defaultdict(float)
        for result in results:
            totals[result.chunk.module] += result.seconds
        print("Module totals (sum of chunk elapsed seconds):", flush=True)
        for module, seconds in sorted(totals.items(), key=lambda item: (-item[1], item[0]))[:args.durations]:
            print(f"  {seconds:9.3f}s  {module}", flush=True)
    return int(failed > 0)


if __name__ == "__main__":
    raise SystemExit(main())
