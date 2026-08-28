#!/usr/bin/env python3
"""Run a clean NInfer build and focused contract tests on an ephemeral RunPod GPU."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

DEFAULT_GPU_ID = "NVIDIA GeForce RTX 5090"
DEFAULT_IMAGE = "runpod/pytorch:1.1.0-cu1300-torch291-ubuntu2404"
DEFAULT_CUDA_PACKAGES = ("cuda-compiler-13-1", "cuda-libraries-dev-13-1")
DEFAULT_CTEST_REGEX = (
    "ninfer_(checkpoint_io_contract|resource_manager|openai_schema|responses_schema|response_store|"
    "tool_call_parser|serve_options|request_log)_test"
)
GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
TRANSIENT_RUNPOD_ERRORS = {"network_error", "rate_limited", "server_error"}


class CiError(RuntimeError):
    """A bounded CI lifecycle failure."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


Runner = Callable[[Sequence[str]], CommandResult]


def run_command(command: Sequence[str], *, cwd: Path | None = None) -> CommandResult:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def require_success(result: CommandResult, step: str) -> CommandResult:
    if result.returncode == 0:
        return result
    detail = (result.stderr or result.stdout).strip()
    if len(detail) > 8_000:
        detail = detail[-8_000:]
    raise CiError(f"{step} failed ({result.returncode}): {detail}")


def parse_json_output(text: str) -> Any:
    """Parse JSON even when a CLI emitted bounded progress text first."""
    stripped = text.strip()
    if not stripped:
        raise CiError("command returned no JSON")
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for index, character in enumerate(stripped):
            if character not in "[{":
                continue
            try:
                value, end = decoder.raw_decode(stripped[index:])
            except json.JSONDecodeError:
                continue
            if not stripped[index + end :].strip():
                return value
    raise CiError("command output did not end in valid JSON")


def git_text(source: Path, *arguments: str) -> str:
    result = require_success(
        run_command(["git", "-C", str(source), *arguments]),
        f"git {' '.join(arguments)}",
    )
    return result.stdout.strip()


def validate_source(source: Path) -> str:
    if not source.is_dir():
        raise CiError(f"source directory does not exist: {source}")
    commit = git_text(source, "rev-parse", "HEAD")
    if not GIT_SHA_PATTERN.fullmatch(commit):
        raise CiError("source HEAD is not a full lowercase Git SHA")
    status = git_text(source, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise CiError("source worktree must be completely clean and committed")
    return commit


def read_upstream_base(source: Path, override: str | None) -> str:
    if override is not None:
        value = override
    else:
        preset_path = source / "CMakePresets.json"
        try:
            presets = json.loads(preset_path.read_text(encoding="utf-8"))
            value = presets["configurePresets"][0]["cacheVariables"][
                "NINFER_UPSTREAM_BASE_SHA"
            ]
        except (FileNotFoundError, KeyError, IndexError, json.JSONDecodeError) as error:
            raise CiError(
                "cannot resolve NINFER_UPSTREAM_BASE_SHA; pass --upstream-base-sha"
            ) from error
    if not GIT_SHA_PATTERN.fullmatch(value):
        raise CiError("upstream base must be a full lowercase Git SHA")
    ancestry = run_command(["git", "-C", str(source), "merge-base", "--is-ancestor", value, "HEAD"])
    if ancestry.returncode != 0:
        raise CiError("upstream base is not an ancestor of source HEAD")
    return value


def gpu_hourly_price(catalog: Any, gpu_id: str, cloud_type: str) -> float:
    if not isinstance(catalog, list):
        raise CiError("runpodctl gpu list returned an unexpected shape")
    for gpu in catalog:
        if not isinstance(gpu, dict):
            continue
        if gpu.get("gpuId") != gpu_id and gpu.get("displayName") != gpu_id:
            continue
        if not gpu.get("available", False):
            raise CiError(f"requested GPU is unavailable: {gpu_id}")
        key = "communityPricePerHr" if cloud_type == "COMMUNITY" else "securePricePerHr"
        price = gpu.get(key)
        if not isinstance(price, (int, float)):
            raise CiError(f"requested GPU has no {cloud_type.lower()} hourly price")
        return float(price)
    raise CiError(f"requested GPU was not found: {gpu_id}")


def extract_pod_id(result: CommandResult) -> str | None:
    for candidate in (result.stdout, result.stderr, result.stdout + "\n" + result.stderr):
        try:
            value = parse_json_output(candidate)
        except CiError:
            value = None
        if isinstance(value, dict) and isinstance(value.get("id"), str):
            return value["id"]
    match = re.search(r"\bpod ([a-z0-9]{8,})\b", result.stderr + "\n" + result.stdout)
    return match.group(1) if match else None


def runpod_error_code(result: CommandResult) -> str | None:
    for candidate in (result.stdout, result.stderr):
        try:
            value = parse_json_output(candidate)
        except CiError:
            continue
        if isinstance(value, dict) and isinstance(value.get("code"), str):
            return value["code"]
    return None


def delete_pod(
    pod_id: str,
    *,
    runner: Runner = run_command,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    delays = (0.0, 2.0, 5.0)
    last: CommandResult | None = None
    for delay in delays:
        if delay:
            sleep(delay)
        last = runner(["runpodctl", "pod", "delete", pod_id])
        if last.returncode == 0:
            return
        if runpod_error_code(last) not in TRANSIENT_RUNPOD_ERRORS:
            break
    assert last is not None
    detail = (last.stderr or last.stdout).strip()
    raise CiError(f"URGENT: failed to delete billing pod {pod_id}: {detail}")


def remote_script(
    *,
    source_commit: str,
    upstream_base: str,
    cuda_arch: str,
    cuda_packages: Sequence[str],
    ctest_regex: str,
) -> str:
    packages = (
        "cmake git ninja-build pkg-config libavcodec-dev libavformat-dev "
        "libavutil-dev libcurl4-openssl-dev libssl-dev libswscale-dev "
        + " ".join(shlex.quote(package) for package in cuda_packages)
    )
    targets = (
        "ninfer ninfer-serve ninfer_checkpoint_io_contract_test "
        "ninfer_resource_manager_test ninfer_openai_schema_test "
        "ninfer_responses_schema_test ninfer_response_store_test "
        "ninfer_tool_call_parser_test ninfer_serve_options_test ninfer_request_log_test"
    )
    return f"""set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends {packages}
export PATH=/usr/local/cuda-13.1/bin:$PATH
rm -rf /workspace/ninfer
mkdir -p /workspace/ninfer
git clone -q /workspace/omp-ninfer-ci.bundle /workspace/ninfer
cd /workspace/ninfer
[[ $(git rev-parse HEAD) == {shlex.quote(source_commit)} ]]
[[ -z $(git status --porcelain --untracked-files=all) ]]
cmake -S . -B build/runpod -G Ninja \\
  -DCMAKE_BUILD_TYPE=Release \\
  -DCMAKE_CUDA_ARCHITECTURES={shlex.quote(cuda_arch)} \\
  -DNINFER_BUILD_APPS=ON \\
  -DBUILD_TESTING=ON \\
  -DNINFER_BUILD_BENCHMARKS=OFF \\
  -DNINFER_BUILD_PROFILE=runpod-ci \\
  -DNINFER_UPSTREAM_BASE_SHA={shlex.quote(upstream_base)} \\
  -DNINFER_PATCH_STACK_SHA={shlex.quote(source_commit)} \\
  -DNINFER_SOURCE_CLEAN_VERIFIED=ON
cmake --build build/runpod --parallel --target {targets}
ctest --test-dir build/runpod --output-on-failure -R {shlex.quote(ctest_regex)}
build/runpod/apps/ninfer-serve --version
"""


def write_receipt(path: Path | None, receipt: dict[str, Any]) -> None:
    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if path is None:
        print(payload, end="")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def install_signal_handlers() -> None:
    def terminate(signum: int, _frame: object) -> None:
        del _frame
        raise KeyboardInterrupt(f"received signal {signum}")

    signal.signal(signal.SIGTERM, terminate)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--upstream-base-sha")
    parser.add_argument("--gpu-id", default=DEFAULT_GPU_ID)
    parser.add_argument("--cloud-type", choices=("COMMUNITY", "SECURE"), default="COMMUNITY")
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--cuda-arch", default="120a")
    parser.add_argument(
        "--cuda-package",
        action="append",
        dest="cuda_packages",
        help="CUDA apt package; repeat as needed",
    )
    parser.add_argument("--container-disk-gb", type=int, default=40)
    parser.add_argument("--max-hourly-price", type=float, default=0.70)
    parser.add_argument("--cleanup-deadline-minutes", type=int, default=55)
    parser.add_argument("--wait-timeout", default="15m")
    parser.add_argument("--ctest-regex", default=DEFAULT_CTEST_REGEX)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()

    if args.container_disk_gb < 20:
        parser.error("--container-disk-gb must be at least 20")
    if not 10 <= args.cleanup_deadline_minutes <= 180:
        parser.error("--cleanup-deadline-minutes must be between 10 and 180")
    cuda_packages = tuple(args.cuda_packages or DEFAULT_CUDA_PACKAGES)
    if not cuda_packages or any(not package for package in cuda_packages):
        parser.error("at least one non-empty --cuda-package is required")

    install_signal_handlers()
    source = args.source.resolve()
    started = dt.datetime.now(dt.UTC)
    receipt: dict[str, Any] = {
        "artifact_type": "omp_ninfer_runpod_ci_receipt",
        "schema_version": 1,
        "started_at": started.isoformat(),
        "status": "failed",
        "source_commit": None,
        "upstream_base_sha": None,
        "gpu_id": args.gpu_id,
        "cloud_type": args.cloud_type,
        "image": args.image,
        "cuda_arch": args.cuda_arch,
        "cuda_packages": list(cuda_packages),
        "hourly_price_usd": None,
        "pod_id": None,
        "pod_deleted": False,
        "failed_step": None,
    }
    pod_id: str | None = None
    watchdog: subprocess.Popen[bytes] | None = None
    failure: BaseException | None = None

    try:
        source_commit = validate_source(source)
        upstream_base = read_upstream_base(source, args.upstream_base_sha)
        receipt["source_commit"] = source_commit
        receipt["upstream_base_sha"] = upstream_base

        require_success(run_command(["runpodctl", "user"]), "RunPod authentication")
        catalog_result = require_success(run_command(["runpodctl", "gpu", "list"]), "GPU catalog")
        price = gpu_hourly_price(parse_json_output(catalog_result.stdout), args.gpu_id, args.cloud_type)
        receipt["hourly_price_usd"] = price
        if price > args.max_hourly_price:
            raise CiError(
                f"hourly price ${price:.2f} exceeds cap ${args.max_hourly_price:.2f}"
            )

        with tempfile.TemporaryDirectory(prefix="omp-ninfer-runpod-") as temporary:
            bundle = Path(temporary) / "omp-ninfer-ci.bundle"
            require_success(
                run_command(["git", "-C", str(source), "bundle", "create", str(bundle), "HEAD"]),
                "source bundle",
            )
            pod_name = "omp-ninfer-ci-" + started.strftime("%Y%m%d-%H%M%S")
            create_command = [
                "runpodctl",
                "pod",
                "create",
                "--name",
                pod_name,
                "--image",
                args.image,
                "--gpu-id",
                args.gpu_id,
                "--cloud-type",
                args.cloud_type,
                "--container-disk-in-gb",
                str(args.container_disk_gb),
                "--ports",
                "22/tcp",
                "--wait",
                "--wait-timeout",
                args.wait_timeout,
            ]
            if args.cloud_type == "COMMUNITY":
                create_command.append("--public-ip")
            created = run_command(create_command)
            pod_id = extract_pod_id(created)
            if pod_id is None:
                require_success(created, "pod creation")
                raise CiError("pod creation returned no pod id")
            receipt["pod_id"] = pod_id
            require_success(created, "pod readiness")

            watchdog = subprocess.Popen(
                [
                    "/bin/sh",
                    "-c",
                    f"sleep {args.cleanup_deadline_minutes * 60}; "
                    f"runpodctl pod delete {shlex.quote(pod_id)} >/dev/null 2>&1",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

            ssh_result = require_success(
                run_command(["runpodctl", "ssh", "info", pod_id]), "SSH discovery"
            )
            ssh = parse_json_output(ssh_result.stdout)
            try:
                host = ssh["ip"]
                port = str(ssh["port"])
                key = ssh["ssh_key"]["path"]
            except (KeyError, TypeError) as error:
                raise CiError("runpodctl ssh info returned an unexpected shape") from error

            ssh_options = [
                "-i",
                key,
                "-p",
                port,
                "-o",
                "BatchMode=yes",
                "-o",
                "StrictHostKeyChecking=accept-new",
                "-o",
                "ConnectTimeout=20",
            ]
            require_success(
                run_command(
                    [
                        "scp",
                        "-q",
                        "-i",
                        key,
                        "-P",
                        port,
                        "-o",
                        "StrictHostKeyChecking=accept-new",
                        str(bundle),
                        f"root@{host}:/workspace/omp-ninfer-ci.bundle",
                    ]
                ),
                "bundle transfer",
            )
            remote = remote_script(
                source_commit=source_commit,
                upstream_base=upstream_base,
                cuda_arch=args.cuda_arch,
                cuda_packages=cuda_packages,
                ctest_regex=args.ctest_regex,
            )
            remote_result = run_command(["ssh", *ssh_options, f"root@{host}", remote])
            if remote_result.stdout:
                print(remote_result.stdout, end="")
            require_success(remote_result, "remote build and tests")
            receipt["status"] = "passed"
    except BaseException as error:  # cleanup must also run for SIGTERM/KeyboardInterrupt
        failure = error
        receipt["failed_step"] = type(error).__name__
    finally:
        if pod_id is not None:
            try:
                delete_pod(pod_id)
                receipt["pod_deleted"] = True
            except BaseException as cleanup_error:
                failure = cleanup_error
                receipt["failed_step"] = type(cleanup_error).__name__
        if watchdog is not None and watchdog.poll() is None:
            watchdog.terminate()
        receipt["finished_at"] = dt.datetime.now(dt.UTC).isoformat()
        write_receipt(args.receipt, receipt)

    if failure is not None:
        print(f"error: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
