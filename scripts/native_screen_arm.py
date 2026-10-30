#!/usr/bin/env python3
"""Capture one native EXP-085 arm in resumable, at-most-55-minute scratch-install holds.

Generate --prompts with quality_screen.py variants. Run production screen, production
subset, candidate screen, candidate subset in that order. Each invocation stops the
product lane, installs with -ScratchTaskSuffix screen-prod|screen-cand -NoStart,
then Stop -> empty cache -> Start -> capture/score -> Stop for each shard. Hooks are
blocking JSON argv arrays, as in client_acceptance.py; no shell is implied. The lead
owns product restoration between holds. --resume verifies all sealed evidence before
starting more work. A partial attempt is retained and never mistaken for completion.
Only merged, complete run directories have arm.json and are eligible for verdict().
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

from quality_screen import capture_endpoint, endpoint_root, load_run
from redaction_screen import ScreenError, native_arm

MAX_HOLD_SECONDS = 55 * 60
STOP_RESERVE_SECONDS = 900
EVIDENCE_FILES = ("manifest.json", "scores.json", "responses.jsonl", "arm.json")


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ScreenError("expected a JSON object")
    return value


def save(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def command_json(value: str) -> list[str]:
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not parsed or not all(isinstance(s, str) and s for s in parsed):
        raise argparse.ArgumentTypeError("use a nonempty JSON argv array")
    return parsed


def option(command: Sequence[str], flag: str) -> str | None:
    positions = [i for i, value in enumerate(command) if value.lower() == flag.lower()]
    if len(positions) != 1 or positions[0] + 1 == len(command):
        return None
    return command[positions[0] + 1]


def check_hooks(args: argparse.Namespace) -> str:
    root = args.state_root.resolve()
    for name, action in (("stop_cmd", "Stop"), ("start_cmd", "Start"), ("production_stop_cmd", "Stop")):
        command = getattr(args, name)
        if not any(Path(part).name.lower() == "control-release.ps1" for part in command):
            raise ScreenError("lifecycle hooks must use Control-Release.ps1")
        state = option(command, "-StateRoot")
        if not state or option(command, "-Action") != action:
            raise ScreenError("lifecycle hooks require their action and state root")
        if (Path(state).resolve() == root) != (name != "production_stop_cmd"):
            raise ScreenError("scratch hooks must target scratch state; product stop must not")
    command = args.install_cmd
    suffix = option(command, "-ScratchTaskSuffix")
    if (not any(Path(part).name.lower() == "install-release.ps1" for part in command)
            or suffix not in ("screen-prod", "screen-cand") or "-NoStart" not in command
            or option(command, "-StateRoot") is None
            or Path(option(command, "-StateRoot")).resolve() != root):
        raise ScreenError("install hook requires Install-Release.ps1, scratch suffix, state root and -NoStart")
    return suffix


def hook(command: Sequence[str], deadline: float, maximum: float = 900) -> None:
    remaining = min(maximum, deadline - time.monotonic())
    if remaining <= 0:
        raise ScreenError("native screen hold deadline exhausted")
    result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, timeout=remaining)
    if result.returncode:
        raise ScreenError("lifecycle hook failed; inspect owner-local diagnostics")


def active_release(state_root: Path, suffix: str) -> tuple[dict[str, Any], dict[str, Any]]:
    state = load(state_root / "state.json")
    if (state.get("artifact_type") != "ninfer_windows_lifecycle_state" or state.get("schema_version") != 4
            or not str(state.get("task_name", "")).endswith("-" + suffix)):
        raise ScreenError("native screen requires its scratch lifecycle state")
    release = state["releases"][state["active_release"]]
    spec = load(Path(release["receipts_root"]) / "release-spec.json")
    if state["task_name"] != spec["lifecycle"]["task_name"] + "-Scratch-" + suffix:
        raise ScreenError("native screen task must be the spec's isolated scratch task")
    if state_root.name != spec["lifecycle"]["state_root_name"]:
        raise ScreenError("scratch root leaf must equal the release-spec state_root_name")
    if release["port"] != spec["lifecycle"]["listen_port"] or release["port"] != 18082:
        raise ScreenError("active endpoint port must equal release-spec listen_port 18082")
    host = release["host"]
    if not isinstance(host, str) or not host or host in ("0.0.0.0", "::", "*"):
        raise ScreenError("active endpoint must name a reachable host, not a wildcard")
    authority = "[" + host + "]" if ":" in host else host
    release = dict(release, endpoint=endpoint_root(f"http://{authority}:{release['port']}"),
                   release_id=state["active_release"])
    for field, name in (("server_executable", "binary_sha256"), ("config_file", "config_sha256"),
                        ("model_artifact", "model_artifact_sha256")):
        if digest(Path(release[field])) != release[name]:
            raise ScreenError("installed runtime bytes differ from the active release record")
    return release, spec


def measured_power(release: dict[str, Any], spec: dict[str, Any], expected: float) -> float:
    policy = spec["lifecycle"].get("gpu_owner_controller_protocol", {})
    # A lane without a serving cap (qualified_power_limit_w null, e.g. RTX 4090 beta.3) runs at the
    # owner's documented setting, so the arm must match owner_power_limit_w instead.
    qualified = policy.get("qualified_power_limit_w")
    if qualified is None:
        qualified = policy.get("owner_power_limit_w")
    if qualified is not None and qualified != expected:
        raise ScreenError("requested power cap differs from release-spec qualification")
    result = subprocess.run(["nvidia-smi", "--id=" + release["gpu_uuid"],
                             "--query-gpu=name,power.limit", "--format=csv,noheader,nounits"],
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            text=True, check=True, timeout=30)
    name, power = [part.strip() for part in result.stdout.strip().split(",")]
    if name != release["gpu_name"] or float(power) != expected:
        raise ScreenError("measured GPU name/power differs from the qualified arm")
    return float(power)


def empty_cache(state_root: Path, release: dict[str, Any]) -> None:
    cache = Path(release["cache_root"])
    expected = state_root.resolve() / "cache" / release["release_id"]
    if cache.is_symlink() or cache.resolve() != expected or not expected.is_relative_to(state_root.resolve()):
        raise ScreenError("refusing to clear a cache outside the scratch release")
    if cache.exists():
        for entry in cache.iterdir():
            if entry.is_symlink() or entry.is_file():
                entry.unlink()
            else:
                shutil.rmtree(entry)
    else:
        cache.mkdir(parents=True)
    if any(cache.iterdir()):
        raise ScreenError("scratch cache is not empty")


def arm_record(release: dict[str, Any], lane: str, power: float, prompts_sha: str,
               state_root: Path) -> dict[str, Any]:
    runtime = load(state_root / "runtime.json")
    if (runtime.get("release_id") != release["release_id"] or runtime.get("gpu_uuid_verified") is not True
            or runtime.get("gpu_name") != release["gpu_name"]):
        raise ScreenError("fresh process must attest the selected release and GPU")
    started = datetime(1, 1, 1, tzinfo=timezone.utc) + timedelta(
        microseconds=int(runtime["start_time_utc_ticks"]) // 10)
    return native_arm({
        "artifact_type": "omp_ninfer_screen_arm", "schema_version": 1, "kind": "native-windows",
        "lane": lane, "release_id": release["release_id"], "package_sha256": release["package_sha256"],
        "server_binary_sha256": release["binary_sha256"], "configuration_sha256": release["config_sha256"],
        "model_artifact_sha256": release["model_artifact_sha256"], "gpu_name": release["gpu_name"],
        "power_limit_w": power, "endpoint_port": release["port"], "concurrency": 1, "reasoning": "low",
        "fresh_start": {"cache_root_empty": True, "process_started_utc": started.isoformat()},
        "prompts_sha256": prompts_sha,
    })


def verify_capture(directory: Path, ids: list[str]) -> dict[str, str]:
    responses = [json.loads(line) for line in (directory / "responses.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    scores = load(directory / "scores.json")["per_case"]
    if ([row["case_id"] for row in responses] != ids or len(scores) != len(ids)
            or {row["case_id"] for row in scores} != set(ids)):
        raise ScreenError("shard capture/scored IDs differ from frozen prompt order")
    load_run(directory)
    native_arm(load(directory / "arm.json"))
    return {name: digest(directory / name) for name in EVIDENCE_FILES}


def _run_arm(args: argparse.Namespace, deadline: float) -> dict[str, Any]:
    if not args.fresh or args.shard_size < 1 or args.max_shards < 1 or args.power_limit_w <= 0:
        raise ScreenError("fresh start, positive shard bounds and a qualified power cap are required")
    suffix = check_hooks(args)
    capture_deadline = deadline - STOP_RESERVE_SECONDS
    hook(args.production_stop_cmd, capture_deadline)
    if not (args.state_root / "state.json").exists():
        hook(args.install_cmd, capture_deadline)
    release, spec = active_release(args.state_root, suffix)
    lane = "rtx" + release["gpu_name"].rsplit(" ", 1)[-1]
    rows = [line for line in args.prompts.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [json.loads(line)["case_id"] for line in rows]
    if not ids or len(ids) != len(set(ids)):
        raise ScreenError("prompts must have unique, nonempty case IDs")
    prompts_sha = digest(args.prompts)
    stable = {name: release[name] for name in ("release_id", "package_sha256", "binary_sha256",
              "config_sha256", "model_artifact_sha256", "gpu_name", "port")}
    inputs = {"qualification": {path.relative_to(args.qualification).as_posix(): digest(path)
              for path in sorted(args.qualification.rglob("*"))
              if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"}}
    inputs["fixtures"] = {path.relative_to(args.fixtures).as_posix(): digest(path)
                          for path in sorted(args.fixtures.rglob("*")) if path.is_file()}
    tools = {name: digest(Path(__file__).with_name(name)) for name in (
        "native_screen_arm.py", "quality_screen.py", "redaction_screen.py")}
    plan = {"artifact_type": "omp_ninfer_native_screen_shards", "schema_version": 1,
            "runtime": stable, "power_limit_w": args.power_limit_w, "prompts_sha256": prompts_sha,
            "shard_size": args.shard_size, "prompt_ids": ids, "inputs": inputs, "tools": tools}
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    plan_path = out / "shards.json"
    if plan_path.exists():
        if not args.resume or load(plan_path) != plan:
            raise ScreenError("resume requires unchanged prompts, runtime, tools and qualification inputs")
    elif any(out.iterdir()):
        raise ScreenError("new native screen requires an empty output directory")
    else:
        save(plan_path, plan)
    completed: list[Path] = []
    pending = []
    for number, start in enumerate(range(0, len(rows), args.shard_size)):
        directory = out / f"shard-{number:04d}"
        shard_ids = ids[start:start + args.shard_size]
        seal_path = directory / "complete.json"
        if seal_path.exists():
            seal = load(seal_path)
            capture = directory / seal["attempt"]
            if (capture.parent != directory or seal["files"] != verify_capture(capture, shard_ids)
                    or seal["plan_sha256"] != digest(plan_path)):
                raise ScreenError("sealed native shard evidence changed")
            arm = load(capture / "arm.json")
            expected = (stable["package_sha256"], stable["binary_sha256"], stable["config_sha256"],
                        stable["model_artifact_sha256"], prompts_sha, args.power_limit_w)
            if tuple(arm[name] for name in ("package_sha256", "server_binary_sha256", "configuration_sha256",
                     "model_artifact_sha256", "prompts_sha256", "power_limit_w")) != expected:
                raise ScreenError("sealed shard runtime differs from frozen arm")
            completed.append(capture)
        else:
            pending.append((directory, start, shard_ids))
    try:
        for directory, start, shard_ids in pending[:args.max_shards]:
            if time.monotonic() >= capture_deadline:
                break
            directory.mkdir(exist_ok=True)
            attempt = directory / f"attempt-{len(list(directory.glob('attempt-*'))):04d}"
            cases = directory / "prompts"
            cases.mkdir(exist_ok=True)
            (cases / "shard.jsonl").write_text("\n".join(rows[start:start + args.shard_size]) + "\n",
                                                encoding="utf-8")
            hook(args.stop_cmd, capture_deadline)
            empty_cache(args.state_root, release)
            not_before = datetime.now(timezone.utc)
            hook(args.start_cmd, capture_deadline, maximum=600)
            power = measured_power(release, spec, args.power_limit_w)
            arm = arm_record(release, lane, power, prompts_sha, args.state_root)
            if datetime.fromisoformat(arm["fresh_start"]["process_started_utc"]) < not_before:
                raise ScreenError("start hook did not create a fresh process after cache cleanup")
            capture_endpoint(qualification=args.qualification, cases=cases, fixtures=args.fixtures,
                             base_url=release["endpoint"], model=load(Path(release["config_file"]))["model_id"],
                             api_key_file=args.key_file, out=attempt, label=suffix,
                             deadline=capture_deadline)
            save(attempt / "arm.json", arm)
            hook(args.stop_cmd, deadline)
            files = verify_capture(attempt, shard_ids)
            temporary = directory / "complete.tmp"
            save(temporary, {"attempt": attempt.name, "files": files, "plan_sha256": digest(plan_path)})
            temporary.replace(directory / "complete.json")
            completed.append(attempt)
    finally:
        hook(args.stop_cmd, deadline)
    total = (len(rows) + args.shard_size - 1) // args.shard_size
    result = {"status": "shard-complete", "completed_shards": len(completed), "total_shards": total}
    if len(completed) != total:
        return result
    captures = sorted(completed, key=lambda path: path.parent.name)
    scores = [row for path in captures for row in load(path / "scores.json")["per_case"]]
    save(out / "scores.json", {"per_case": scores, "corpus_sha256": prompts_sha})
    (out / "responses.jsonl").write_bytes(b"".join(
        (path / "responses.jsonl").read_bytes().rstrip(b"\r\n") + b"\n" for path in captures))
    save(out / "manifest.json", {"label": suffix, "shards_sha256": digest(plan_path)})
    arms = [load(path / "arm.json") for path in captures]
    # A determinism run must start after the LAST screen shard's fresh process.
    arm = max(arms, key=lambda value: value["fresh_start"]["process_started_utc"])
    save(out / "arm.json", arm)
    return dict(result, status="complete")


def run_arm(args: argparse.Namespace) -> dict[str, Any]:
    check_hooks(args)
    deadline = time.monotonic() + MAX_HOLD_SECONDS
    try:
        return _run_arm(args, deadline)
    finally:
        hook(args.stop_cmd, deadline)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ("state-root", "key-file", "prompts", "out", "qualification", "fixtures"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("install", "stop", "start", "production-stop"):
        parser.add_argument("--" + name + "-cmd", type=command_json, required=True)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--power-limit-w", type=float, required=True)
    parser.add_argument("--shard-size", type=int, default=100)
    parser.add_argument("--max-shards", type=int, default=1)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(run_arm(args), indent=2))
    except (ScreenError, OSError, KeyError, ValueError, subprocess.SubprocessError):
        # Hook output, URLs, local paths and credentials remain only in owner-local diagnostics.
        print("native_screen_arm: capture did not complete; inspect local prerequisites/evidence", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
