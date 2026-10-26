#!/usr/bin/env python3
"""Matched, fresh-server A/B/B/A campaigns on one selected GPU (stdlib only).

Run locally on the GPU host, under its hostlock/gpu-lease. No installed service is
stopped or restored: the endpoint must be free and every child is owned by this
runner. Native Windows and Linux Docker use the same plan and evidence contract.
See docs/VARIANT-CAMPAIGNS.md for the plan format and profiling limitations.
"""
from __future__ import annotations

import argparse
import bisect
from contextlib import closing
import copy
import ctypes
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import sqlite3
import statistics
import subprocess
import sys
import threading
import time
from typing import Any, Sequence
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import quality_screen as quality
from common import sha256_file

LANES = ("rtx3090", "rtx4090", "rtx5090")
ORDER = ("A", "B", "B", "A")
C1_PARAGRAPH = ("A reliable GPU inference service separates admission control, scheduling, memory "
                "accounting, observability, and failure recovery. ")
C1_PROMPT = (C1_PARAGRAPH * (28000 // len(C1_PARAGRAPH) + 2))[:28000] + "\nContinue until the output limit."


class CampaignError(RuntimeError):
    pass


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path: Path, value: Any) -> None:
    # Match EXP-085's report encoding, including its explicitly unbounded leak ratios.
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False).encode()).hexdigest()


def command(argv: Sequence[str], timeout: float = 120, **kwargs: Any) -> subprocess.CompletedProcess:
    return subprocess.run(list(map(str, argv)), stdin=subprocess.DEVNULL, check=True,
                          capture_output=True, text=True, timeout=timeout, **kwargs)


def gpu(uuid_: str) -> dict[str, Any]:
    fields = ("uuid", "name", "driver_version", "power.limit", "memory.used", "power.draw",
              "temperature.gpu", "utilization.gpu")
    text = command(["nvidia-smi", "-i", uuid_, "--query-gpu=" + ",".join(fields),
                    "--format=csv,noheader,nounits"]).stdout
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) != 1 or len(rows[0]) != len(fields):
        raise CampaignError("GPU selection did not resolve exactly one device")
    values = [cell.strip() for cell in rows[0]]
    if values[0] != uuid_:
        raise CampaignError("GPU UUID changed")
    return dict(zip(("uuid", "name", "driver", "power_limit_w", "memory_used_mib", "power_w",
                     "temperature_c", "utilization_percent"),
                    values[:3] + [float(value) for value in values[3:]]))


def set_power(uuid_: str, watts: float) -> None:
    command(["nvidia-smi", "-i", uuid_, "-pl", str(watts)])
    if abs(gpu(uuid_)["power_limit_w"] - watts) > 0.5:
        raise CampaignError("selected GPU did not adopt requested power limit")


class Sampler:
    def __init__(self, uuid_: str, path: Path, interval: float):
        self.uuid, self.path, self.interval = uuid_, path, interval
        self.stop = threading.Event()
        self.rows: list[dict[str, Any]] = []
        self.errors: list[Exception] = []
        self.thread = threading.Thread(target=self.poll, daemon=True)

    def sample(self) -> None:
        row = dict(gpu(self.uuid), unix_seconds=time.time())
        self.rows.append(row)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row) + "\n")

    def poll(self) -> None:
        try:
            while not self.stop.wait(self.interval):
                self.sample()
        except Exception as error:
            self.errors.append(error)

    def __enter__(self) -> "Sampler":
        self.sample()
        self.thread.start()
        return self

    def __exit__(self, *unused: Any) -> None:
        self.stop.set()
        self.thread.join(timeout=130)
        if self.thread.is_alive():
            raise CampaignError("GPU sampler did not stop")
        self.sample()
        if self.errors:
            raise CampaignError("GPU sampler failed; no trustworthy VRAM maximum") from self.errors[0]

    def summary(self) -> dict[str, Any]:
        return {"samples": len(self.rows), **{
            "max_" + field: max(row[field] for row in self.rows)
            for field in ("memory_used_mib", "power_w", "temperature_c", "utilization_percent")}}


def http(root: str, key: str, path: str, body: Any = None, timeout: float = 900) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(root + path, data=data,
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def deep_update(base: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in changes.items():
        result[key] = deep_update(result.get(key, {}), value) if isinstance(value, dict) else value
    return result


def effective_config(plan: dict[str, Any], arm: dict[str, Any]) -> dict[str, Any]:
    source = arm.get("config_path", plan.get("config_path"))
    config = load(Path(source)) if source else plan.get("config", {})
    return deep_update(config, arm.get("overrides", {}))


def validate_plan(plan: dict[str, Any], lane: str) -> None:
    if lane not in LANES or plan.get("lane", lane) != lane:
        raise CampaignError("plan lane differs from requested lane")
    if not isinstance(plan.get("gpu_uuid"), str) or not plan["gpu_uuid"].startswith("GPU-"):
        raise CampaignError("select the GPU by its full UUID, never its ordinal")
    if set(plan.get("arms", {})) != {"A", "B"}:
        raise CampaignError("plan must contain exactly baseline A and candidate B")
    if not Path(plan["model_path"]).is_file():
        raise CampaignError("model_path is not a file")
    for arm in plan["arms"].values():
        if not arm.get("binary"):
            raise CampaignError("each arm needs its binary path")
        if not arm.get("image") and not Path(arm["binary"]).is_file():
            raise CampaignError("native arm binary is not a file")
        if arm.get("image") and not str(plan.get("holder", "harness")).replace("-", "").isalnum():
            raise CampaignError("container holder must contain only letters, digits and hyphens")
        if float(arm.get("power_limit_w", 1)) <= 0:
            raise CampaignError("power limit must be positive")
    if not 0 < float(plan.get("sample_interval_seconds", 0.2)) <= 5:
        raise CampaignError("sampling interval must be in (0, 5] seconds")


def server_arguments(config: dict[str, Any], paths: dict[str, str], arm: dict[str, Any]) -> list[str]:
    args = [paths["model"], "--host", paths.get("bind_host", "127.0.0.1"), "--port", paths["port"],
            "--api-key-file", paths["key_file"], "--model-id", paths["model_id"],
            "--binary-sha256", paths["binary_sha256"], "--artifact-sha256", paths["model_sha256"],
            "--config-sha256", digest(config), "--deployment-profile", "matched-campaign",
            "--device", "0", "--request-log-jsonl", paths["log"], "--log-stats-interval-ms", "0"]
    sections = {
        "engine": ("max_context", "kv_capacity", "prefill_chunk", "kv_dtype", "max_concurrency",
                   "max_pending_requests", "pending_timeout_ms", "gpu_keep_warm_ms", "admission_headroom_mib"),
        "context_cache": ("device_state_slots", "host_context_mib", "host_state_slots", "host_kv_mib",
                          "max_private_continuations"),
    }
    for section, fields in sections.items():
        for field in fields:
            if field in config.get(section, {}):
                args += ["--" + field.replace("_", "-"), str(config[section][field])]
    for field in ("max_records", "max_mib"):
        if field in config.get("response_store", {}):
            args += ["--response-store-" + field.replace("_", "-"), str(config["response_store"][field])]
    engine = config.get("engine", {})
    for field, flag in (("cuda_graph", "--no-cuda-graph"), ("prefix_reuse", "--no-prefix-reuse")):
        if engine.get(field) is False:
            args.append(flag)
    if engine.get("vision"):
        args.append("--vision")
    reasoning = config.get("reasoning", {})
    if reasoning.get("thinking") is False:
        args.append("--no-thinking")
    if reasoning.get("preserve_thinking", True):
        args.append("--preserve-thinking")
    spec = config.get("speculative", {})
    if spec.get("backend", "none") != "none":
        args += ["--spec", str(spec["backend"]), "--draft-tokens", str(spec["draft_tokens"]), "--lm-head-draft"]
    checkpoint = config.get("session_checkpoint", {})
    if checkpoint.get("enabled"):
        args += ["--session-checkpoint-dir", paths["checkpoints"]]
        for field in ("quota_mib", "staging_mib"):
            args += ["--session-checkpoint-" + field.replace("_", "-"), str(checkpoint[field])]
        if checkpoint.get("require_origin_auth"):
            args.append("--session-checkpoint-require-origin-auth")
    args += [str(value).format_map(paths) for value in arm.get("server_args", [])]
    return args


def nsys_summary(path: Path) -> dict[str, Any]:
    """Read Nsight's stable SQLite activity tables; never treat CPU NVTX time as GPU time."""
    with closing(sqlite3.connect(path)) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "StringIds" not in tables:
            raise CampaignError("Nsight export omits StringIds")
        strings = dict(db.execute("SELECT id,value FROM StringIds"))
        kernels: list[dict[str, Any]] = []
        if "CUPTI_ACTIVITY_KIND_KERNEL" in tables:
            columns = {row[1] for row in db.execute("PRAGMA table_info(CUPTI_ACTIVITY_KIND_KERNEL)")}
            kernel_column = "demangledName" if "demangledName" in columns else "shortName"
            for name_id, count, total in db.execute(
                    f'SELECT "{kernel_column}",COUNT(*),SUM(end-start) FROM CUPTI_ACTIVITY_KIND_KERNEL GROUP BY "{kernel_column}"'):
                kernels.append({"name": strings.get(name_id, str(name_id)), "calls": count, "gpu_ns": total})
        runtime = []
        if "CUPTI_ACTIVITY_KIND_RUNTIME" in tables:
            for name_id, count, total in db.execute(
                    "SELECT nameId,COUNT(*),SUM(end-start) FROM CUPTI_ACTIVITY_KIND_RUNTIME GROUP BY nameId"):
                name = strings.get(name_id, str(name_id))
                if "cudaGraphLaunch" in name:
                    runtime.append({"name": name, "calls": count, "cpu_ns": total,
                                    "mean_cpu_ns": total / count})
        ranges: dict[str, dict[str, Any]] = {}
        round_ranges: list[tuple[int, int, str]] = []
        prefill_ranges: dict[str, list[dict[str, Any]]] = {}
        if "NVTX_EVENTS" in tables:
            columns = {row[1] for row in db.execute("PRAGMA table_info(NVTX_EVENTS)")}
            text_id = "textId" if "textId" in columns else "NULL"
            payload = "uint64Value" if "uint64Value" in columns else "NULL"
            for start, end, text, name_id, value in db.execute(
                    f"SELECT start,end,text,{text_id},{payload} FROM NVTX_EVENTS WHERE end>start"):
                label = text or strings.get(name_id, "")
                lower = label.lower()
                if lower in ("prefill", "prefill.chunk", "prefill.mtp_chunk"):
                    prefill_ranges.setdefault(label, []).append(
                        {"start_ns": start, "end_ns": end, "payload": value, "per_op": {}})
                if any(word in lower for word in ("mtp", "dflash", "verify")):
                    entry = ranges.setdefault(label, {"calls": 0, "cpu_ns": 0})
                    entry["calls"] += 1
                    entry["cpu_ns"] += end - start
                    if "round" in lower and ("mtp" in lower or "dflash" in lower):
                        round_ranges.append((start, end, label))
        if not kernels or not runtime:
            raise CampaignError("Nsight capture lacks CUDA graph nodes or cudaGraphLaunch CPU activity")
        by_round: dict[str, Any] = {}
        if round_ranges or prefill_ranges:
            # Attribute asynchronous GPU work through its launch correlation, not by
            # intersecting GPU time with a CPU NVTX span that can end before the GPU.
            ordered = sorted(round_ranges)
            starts = [row[0] for row in ordered]
            prefill_starts = {}
            for label, rows in prefill_ranges.items():
                rows.sort(key=lambda row: row["start_ns"])
                prefill_starts[label] = [row["start_ns"] for row in rows]
            launches = dict(db.execute("SELECT correlationId,start FROM CUPTI_ACTIVITY_KIND_RUNTIME"))
            for name_id, start, end, correlation in db.execute(
                    f'SELECT "{kernel_column}",start,end,correlationId FROM CUPTI_ACTIVITY_KIND_KERNEL'):
                submitted = launches.get(correlation)
                if submitted is None:
                    continue
                kernel_name = strings.get(name_id, str(name_id))
                for label, rows in prefill_ranges.items():
                    index = bisect.bisect_right(prefill_starts[label], submitted) - 1
                    if index >= 0 and submitted <= rows[index]["end_ns"]:
                        op = rows[index]["per_op"].setdefault(kernel_name, {"calls": 0, "gpu_ns": 0})
                        op["calls"] += 1
                        op["gpu_ns"] += end - start
                index = bisect.bisect_right(starts, submitted) - 1
                if index < 0 or submitted > ordered[index][1]:
                    continue
                label = ordered[index][2]
                group = by_round.setdefault(label, {"rounds": ranges[label]["calls"], "per_op": {}})
                op = group["per_op"].setdefault(kernel_name, {"calls": 0, "gpu_ns": 0})
                op["calls"] += 1
                op["gpu_ns"] += end - start
            for group in by_round.values():
                group["per_op"] = [
                    {"name": kernel_name, **op, "mean_gpu_ns_per_round": op["gpu_ns"] / group["rounds"]}
                    for kernel_name, op in sorted(group["per_op"].items(), key=lambda item: -item[1]["gpu_ns"])]
        for rows in prefill_ranges.values():
            for row in rows:
                total = sum(op["gpu_ns"] for op in row["per_op"].values())
                row["gpu_ns"] = total
                row["per_op"] = [{"name": name, **op, "gpu_share": op["gpu_ns"] / total}
                                 for name, op in sorted(row["per_op"].items(), key=lambda item: -item[1]["gpu_ns"])]
        return {"per_op": sorted(kernels, key=lambda row: -row["gpu_ns"]),
                "cuda_graph_launch": runtime, "speculative_nvtx_ranges": ranges,
                "per_op_by_round": by_round,
                "per_op_by_prefill_range": prefill_ranges,
                "round_attribution": "GPU kernels correlated to runtime launches inside speculative CPU NVTX round ranges",
                "scope": "whole server lifetime, including startup and warmup; NVTX durations are CPU ranges"}


class Server:
    def __init__(self, plan: dict[str, Any], arm: dict[str, Any], config: dict[str, Any],
                 directory: Path, model_sha: str, key_file: Path, profile: bool):
        self.plan, self.arm, self.config, self.directory = plan, arm, config, directory
        self.container = "ov-" + plan.get("holder", "harness") + "-" + uuid.uuid4().hex[:12]
        self.proc: subprocess.Popen | None = None
        self.stdout = self.stderr = None
        self.profile = profile
        self.nsys = arm.get("nsys_path", plan.get("nsys_path", "nsys"))
        self.seccomp_profile = arm.get("seccomp_profile", plan.get("seccomp_profile")) if arm.get("image") else None
        self.docker_security_args = (["--security-opt", "seccomp=" + str(self.seccomp_profile)]
                                     if self.seccomp_profile else [])
        self.checkpoint_filesystem = None
        if arm.get("image") and config.get("session_checkpoint", {}).get("enabled"):
            self.checkpoint_filesystem = command(
                ["findmnt", "--noheadings", "--output", "FSTYPE", "--target", str(directory)]).stdout.strip()
            if self.checkpoint_filesystem != "ext4":
                raise CampaignError("container checkpoint stores require WSL ext4; choose an ext4 --out root")
        self.binary_sha, self.version = self.binary_identity()
        port = str(plan.get("port", 18089 if arm.get("image") else 18082))
        self.root = "http://127.0.0.1:" + port
        self.key = key_file.read_text().strip()
        self.paths = {"model": str(Path(plan["model_path"]).resolve()), "port": port,
                      "model_id": plan.get("model_id", config.get("model_id", "q38-ninfer")),
                      "key_file": str(key_file), "log": str(directory / "requests.jsonl"),
                      "checkpoints": str(directory / "checkpoints"), "arm_dir": str(directory),
                      "binary_sha256": self.binary_sha, "model_sha256": model_sha, "base_url": self.root}
        if arm.get("image"):
            self.paths.update(model="/model.ninfer", key_file="/campaign/api-key", log="/campaign/requests.jsonl",
                              checkpoints="/campaign/checkpoints", bind_host="0.0.0.0")
        self.argv = [arm["binary"]] + server_arguments(config, self.paths, arm)
        self.stop_event = None
        if os.name == "nt" and not arm.get("image"):
            self.stop_event = "Local\\NInfer-Serve-Stop-" + uuid.uuid4().hex
            self.argv += ["--stop-event", self.stop_event,
                          "--shutdown-report", str(directory / "shutdown.json")]
        if profile:
            self.argv = [self.nsys, "profile", "--trace=cuda,nvtx", "--sample=none", "--cpuctxsw=none",
                         "--cuda-graph-trace=node", "--force-overwrite=true", "--output",
                         "/campaign/profile" if arm.get("image") else str(directory / "profile")] + self.argv
        if arm.get("image"):
            shutil.copyfile(key_file, directory / "api-key")
            self.argv = ["docker", "run", "--rm", "--name", self.container,
                         "--publish", f"127.0.0.1:{port}:{port}",
                         "--gpus", "device=" + plan["gpu_uuid"]] + self.docker_security_args + ["--volume",
                         str(Path(plan["model_path"]).resolve()) + ":/model.ninfer:ro", "--volume",
                         str(directory.resolve()) + ":/campaign", "--entrypoint", self.argv[0],
                         arm["image"]] + self.argv[1:]

    def image_command(self, argv: list[str]) -> list[str]:
        # The ELF loader needs the NVIDIA runtime's libcuda mount even for --version.
        return ["docker", "run", "--rm", "--name", self.container + "-info",
                "--gpus", "device=" + self.plan["gpu_uuid"]] + self.docker_security_args + ["--entrypoint", argv[0],
                self.arm["image"]] + argv[1:]

    def binary_identity(self) -> tuple[str, str]:
        if self.arm.get("image"):
            sha = command(self.image_command(["sha256sum", self.arm["binary"]])).stdout.split()[0]
            version = command(self.image_command([self.arm["binary"], "--version"])).stdout.strip()
        else:
            sha = sha256_file(Path(self.arm["binary"]))
            version = command([self.arm["binary"], "--version"]).stdout.strip()
        expected = self.arm.get("binary_sha256")
        if expected and sha != expected:
            raise CampaignError("arm binary SHA-256 differs from frozen plan")
        return sha, version

    def start(self) -> None:
        # A pre-existing listener must not make another process appear healthy.
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", int(self.paths["port"]))) == 0:
                raise CampaignError("campaign port already has a listener; stop it through its owner")
        self.stdout = (self.directory / "stdout.log").open("wb")
        self.stderr = (self.directory / "stderr.log").open("wb")
        env = dict(os.environ, CUDA_VISIBLE_DEVICES=self.plan["gpu_uuid"])
        self.proc = subprocess.Popen(self.argv, stdin=subprocess.DEVNULL, stdout=self.stdout,
                                     stderr=self.stderr, env=env,
                                     start_new_session=os.name != "nt",
                                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
        deadline = time.monotonic() + float(self.plan.get("startup_timeout_seconds", 1200))
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise CampaignError("owned server exited before readiness; inspect its stderr.log")
            try:
                if http(self.root, self.key, "/health", timeout=3).get("status") == "ok":
                    models = http(self.root, self.key, "/v1/models", timeout=5)
                    if self.paths["model_id"] not in {row["id"] for row in models["data"]}:
                        raise CampaignError("owned endpoint serves the wrong model ID")
                    return
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                pass
            time.sleep(1)
        raise CampaignError("owned server did not become ready before startup deadline")

    def stop(self) -> None:
        try:
            if self.proc is not None and self.proc.poll() is None:
                if self.arm.get("image"):
                    command(["docker", "stop", "--signal", "SIGINT", "--time", "30", self.container], timeout=45)
                elif os.name == "nt":
                    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                    kernel.OpenEventW.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_wchar_p]
                    kernel.OpenEventW.restype = ctypes.c_void_p
                    kernel.SetEvent.argtypes = [ctypes.c_void_p]
                    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
                    handle = kernel.OpenEventW(2, False, self.stop_event)
                    if handle:
                        try:
                            if not kernel.SetEvent(handle):
                                raise ctypes.WinError(ctypes.get_last_error())
                        finally:
                            kernel.CloseHandle(handle)
                    else:
                        # Startup can fail before the event exists. Never target another server.
                        command(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"], timeout=30)
                else:
                    os.killpg(self.proc.pid, signal.SIGINT)
                try:
                    self.proc.wait(timeout=45)
                except subprocess.TimeoutExpired:
                    if os.name == "nt":
                        command(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"], timeout=30)
                    else:
                        os.killpg(self.proc.pid, signal.SIGKILL)
                    self.proc.wait(timeout=30)
        finally:
            if self.stdout:
                self.stdout.close()
            if self.stderr:
                self.stderr.close()

    def profile_summary(self) -> dict[str, Any]:
        report = self.directory / "profile.nsys-rep"
        database = self.directory / "profile.sqlite"
        argv = [self.nsys, "export", "--type", "sqlite", "--output", str(database), str(report)]
        if self.arm.get("image"):
            argv = ["docker", "run", "--rm", "--name", self.container + "-export", "--volume",
                    str(self.directory.resolve()) + ":/campaign"] + self.docker_security_args + ["--entrypoint", self.nsys,
                    self.arm["image"], "export", "--type", "sqlite", "--output", "/campaign/profile.sqlite",
                    "/campaign/profile.nsys-rep"]
        command(argv, timeout=300)
        return nsys_summary(database)


def log_records(path: Path) -> list[dict[str, Any]]:
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def request_metrics(server: Server, body: dict[str, Any], label: str) -> dict[str, Any]:
    log = server.directory / "requests.jsonl"
    before = len(log_records(log))
    started = time.perf_counter()
    response = http(server.root, server.key, "/v1/chat/completions", body,
                    timeout=float(server.plan.get("request_timeout_seconds", 1800)))
    wall = time.perf_counter() - started
    deadline = time.monotonic() + 10
    while True:
        rows = log_records(log)[before:]
        done = [row for row in rows if row.get("event") == "request_done"]
        if done or time.monotonic() >= deadline:
            break
        time.sleep(0.05)
    if len(done) != 1 or any(row.get("event") == "request_error" for row in rows):
        raise CampaignError("request must bind to exactly one successful server request_done")
    record = done[0]
    result, timing, spec = record["result"], record["timings_seconds"], record["speculative"]
    message = response["choices"][0]["message"]
    # Tool-call transport IDs vary per request and are not model output.
    tools = [{k: v for k, v in tool.items() if k != "id"} for tool in message.get("tool_calls") or []]
    output = [message.get("content") or "", message.get("reasoning_content") or message.get("reasoning") or "", tools]
    encoded_output = json.dumps(output, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    output_file = Path("outputs") / (digest([label, body]) + ".json")
    (server.directory / output_file).parent.mkdir(exist_ok=True)
    (server.directory / output_file).write_bytes(encoded_output)
    (server.directory / output_file).chmod(0o600)
    row = {"id": label, "wall_seconds": wall, "request_sha256": digest(body),
           "output_sha256": hashlib.sha256(encoded_output).hexdigest(),
           "output_file": output_file.as_posix(), "prompt_tokens": result["prompt_tokens"],
           "computed_prefill_tokens": result["computed_prefill_tokens"],
           "completion_tokens": result["completion_tokens"],
           "prefix_cache_hit_tokens": result.get("prefix_cache_hit_tokens", 0),
           "decode_seconds": timing["decode"], "prefill_seconds": timing["prefill"],
           "decode_tokens_per_second": result["completion_tokens"] / timing["decode"],
           "prefill_tokens_per_second": result["computed_prefill_tokens"] / timing["prefill"] if timing["prefill"] else None,
           "rounds": spec.get("rounds", 0), "drafted_tokens": spec.get("drafted_tokens", 0),
           "accepted_tokens": spec.get("accepted_tokens", 0), "backend": spec.get("backend"),
           "finish_reason": response["choices"][0].get("finish_reason")}
    return row


def c1(server: Server) -> list[dict[str, Any]]:
    body = {"model": server.paths["model_id"], "messages": [{"role": "user", "content": C1_PROMPT}],
            "max_tokens": 1024, "temperature": 0, "seed": 57004, "reasoning_effort": "medium"}
    row = request_metrics(server, body, "benchmark_c1")
    if (row["prompt_tokens"], row["computed_prefill_tokens"], row["completion_tokens"]) != (4541, 4541, 1024):
        raise CampaignError("C1 must compute 4541 fresh prompt tokens and generate exactly 1024 tokens")
    if row["prefix_cache_hit_tokens"]:
        raise CampaignError("C1 unexpectedly reused a prefix")
    return [row]


def role_requests(server: Server, plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Reuse private prompt construction; depth calibration needs no tokenizer endpoint."""
    path = Path(plan["qualification"]) / "scripts/run_qualification.py"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("campaign_qualification", path)
    if spec is None or spec.loader is None:
        raise CampaignError("private role executor is unavailable")
    q = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(q)
    cases, _ = q.load_cases([str(plan.get("cases", Path(plan["qualification"]) / "cases"))])
    ids = load(Path(plan["case_ids"])) if plan.get("case_ids") else sorted(
        case["case_id"] for case in cases if case["case_id"] not in quality.PREREGISTRATION["vacuous_cases"])
    by_id = {case["case_id"]: case for case in cases}
    rows = []
    for depth in plan.get("role_depths", [0]):
        for case_id in ids:
            case = by_id[case_id]
            warnings: list[str] = []
            system, user, _, _ = q.build_prompt(case, str(plan["fixtures"]), warnings)
            if warnings:
                raise CampaignError("role fixture source resolution changed")
            messages = ([{"role": "system", "content": system}] if system else [])
            if depth:
                # Shipped servers have no /tokenize or /detokenize route. Measure chat-template
                # overhead with bounded one-token requests, identically in all four arms.
                probe = {"model": server.paths["model_id"], "max_tokens": 1, "temperature": 0,
                         "reasoning_effort": plan.get("role_reasoning", "low")}
                for field in ("tools", "response_format"):
                    if field in case:
                        probe[field] = case[field]
                counts = []
                for copies in (0, 8):
                    probe["messages"] = messages + [{"role": "user",
                        "content": C1_PARAGRAPH * copies + "\n\n" + user}]
                    response = http(server.root, server.key, "/v1/chat/completions", probe)
                    counts.append(int(response["usage"]["prompt_tokens"]))
                per_copy = (counts[1] - counts[0]) / 8
                if per_copy <= 0 or counts[0] >= int(depth):
                    raise CampaignError("role source exceeds requested context depth")
                copies = max(0, int((int(depth) - counts[0]) / per_copy))
                user = C1_PARAGRAPH * copies + "\n\n" + user
            messages.append({"role": "user", "content": user})
            body = {"model": server.paths["model_id"], "messages": messages, "temperature": 0,
                    "reasoning_effort": plan.get("role_reasoning", "low"),
                    "max_tokens": min(int(case.get("max_output_tokens", 1024)), int(plan.get("role_max_tokens", 1024)))}
            for field in ("tools", "response_format"):
                if field in case:
                    body[field] = case[field]
            row = request_metrics(server, body, f"{case_id}@{depth}")
            row.update(case_id=case_id, context_depth=depth, workload=case["class"])
            if depth and abs(row["prompt_tokens"] - int(depth)) > 64:
                raise CampaignError("calibrated role depth differs by more than 64 tokens")
            rows.append(row)
            save(server.directory / "role-requests.json", rows)
    return rows


def summarize_arms(arms: list[dict[str, Any]], output_root: Path | None = None) -> dict[str, Any]:
    if [arm["arm"] for arm in arms] != list(ORDER):
        raise CampaignError("complete campaign must have A/B/B/A arms in order")
    identities = [arm["identity"] for arm in arms]
    for field in ("model_sha256",):
        if len({identity[field] for identity in identities}) != 1:
            raise CampaignError("matched arms changed model identity")
    for field in ("uuid", "driver"):
        if len({identity["gpu"][field] for identity in identities}) != 1:
            raise CampaignError("matched arms changed GPU or driver")
    for left, right in ((0, 3), (1, 2)):
        for field in ("binary_sha256", "config_sha256"):
            if identities[left][field] != identities[right][field]:
                raise CampaignError("repeated arm changed binary or configuration")
        if identities[left]["gpu"]["power_limit_w"] != identities[right]["gpu"]["power_limit_w"]:
            raise CampaignError("repeated arm changed power limit")
        if identities[left].get("seccomp_profile_sha256") != identities[right].get("seccomp_profile_sha256"):
            raise CampaignError("repeated arm changed its reviewed syscall policy")
    outputs: dict[str, list[bytes]] = {}
    if output_root is not None:
        for index, arm in enumerate(arms):
            for row in arm.get("requests", []):
                encoded = (output_root / f"{index}-{arm['arm']}" / row["output_file"]).read_bytes()
                if hashlib.sha256(encoded).hexdigest() != row["output_sha256"]:
                    raise CampaignError("private output evidence changed after capture")
                outputs.setdefault(row["id"], []).append(encoded)
    samples = {label: [row for arm in arms if arm["arm"] == label for row in arm.get("requests", [])]
               for label in ("A", "B")}
    rates = {label: sum(row["completion_tokens"] for row in rows) / sum(row["decode_seconds"] for row in rows)
             for label, rows in samples.items() if rows}
    per_case = {}
    ids = {row["id"] for rows in samples.values() for row in rows}
    for id_ in sorted(ids):
        selected = {label: [row for row in rows if row["id"] == id_] for label, rows in samples.items()}
        if not all(len(rows) == 2 for rows in selected.values()):
            raise CampaignError("matched case omitted from an ABBA arm")
        if len({row["request_sha256"] for rows in selected.values() for row in rows}) != 1:
            raise CampaignError("matched case changed request bytes between arms")
        per_case[id_] = {"candidate_baseline_decode_ratio": statistics.median(
            row["decode_tokens_per_second"] for row in selected["B"]) / statistics.median(
            row["decode_tokens_per_second"] for row in selected["A"]),
            "all_output_digests_identical": len({row["output_sha256"] for rows in selected.values() for row in rows}) == 1,
            "all_output_bytes_identical": len(set(outputs[id_])) == 1 if output_root is not None else None}
    return {"weighted_decode_tokens_per_second": rates,
            "candidate_baseline_decode_ratio": rates["B"] / rates["A"] if rates else None,
            "per_case": per_case,
            "all_output_bytes_identical": all(row["all_output_bytes_identical"] for row in per_case.values())
            if per_case and output_root is not None else None}


def run_campaign(lane: str, plan_path: Path, out: Path, mode: str = "c1", profile: bool = False,
                 arm_index: int | None = None) -> dict[str, Any]:
    plan = load(plan_path)
    validate_plan(plan, lane)
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    plan_sha = sha256_file(plan_path)
    manifest = out / "campaign.json"
    if manifest.exists() and load(manifest)["plan_sha256"] != plan_sha:
        raise CampaignError("output root belongs to a different frozen plan")
    if not manifest.exists():
        save(manifest, {"plan_sha256": plan_sha, "lane": lane, "mode": mode, "order": ORDER,
                        "runner_sha256": sha256_file(Path(__file__))})
    elif load(manifest)["mode"] != mode:
        raise CampaignError("output root belongs to a different workload mode")
    elif load(manifest)["runner_sha256"] != sha256_file(Path(__file__)):
        raise CampaignError("output root belongs to a different frozen runner")
    model_sha = sha256_file(Path(plan["model_path"]))
    if plan.get("model_sha256") and model_sha != plan["model_sha256"]:
        raise CampaignError("model SHA-256 differs from frozen plan")
    key_file = out / "api-key"
    if not key_file.exists():
        key_file.write_text(secrets.token_hex(32) + "\n")
        key_file.chmod(0o600)
    if mode == "quality" and not (out / "screen.jsonl").exists():
        save(out / "variants.json", quality.write_variants(Path(plan["cases"]), out / "screen.jsonl",
                                                           out / "determinism.jsonl"))
    indices = range(4) if arm_index is None else [arm_index]
    for index in indices:
        label = ORDER[index]
        if index and not (out / f"{index - 1}-{ORDER[index - 1]}" / "receipt.json").exists():
            raise CampaignError("run the preceding ABBA arm first")
        if index and load(out / f"{index - 1}-{ORDER[index - 1]}" / "receipt.json")["status"] != "passed":
            raise CampaignError("a failed preceding arm invalidates this campaign")
        directory = out / f"{index}-{label}"
        directory.mkdir(exist_ok=False)
        arm = plan["arms"][label]
        config = effective_config(plan, arm)
        before = gpu(plan["gpu_uuid"])
        sampler = Sampler(plan["gpu_uuid"], directory / "vram.jsonl",
                          float(plan.get("sample_interval_seconds", 0.2)))
        server: Server | None = None
        receipt: dict[str, Any] = {"arm": label, "index": index, "status": "failed", "requests": []}
        try:
            if "power_limit_w" in arm:
                set_power(plan["gpu_uuid"], float(arm["power_limit_w"]))
            server = Server(plan, arm, config, directory, model_sha, key_file, profile)
            receipt["identity"] = {"binary_sha256": server.binary_sha, "binary_version": server.version,
                                   "model_sha256": model_sha, "config": config, "config_sha256": digest(config),
                                   "gpu": gpu(plan["gpu_uuid"]), "image": arm.get("image"),
                                   "seccomp_profile_sha256": sha256_file(Path(server.seccomp_profile))
                                   if server.seccomp_profile else None,
                                   "checkpoint_filesystem": server.checkpoint_filesystem,
                                   "server_arguments": server.argv,
                                   "server_arguments_sha256": digest(server.argv)}
            with sampler:
                server.start()
                receipt["ready_memory_mib"] = gpu(plan["gpu_uuid"])["memory_used_mib"]
                if mode == "quality":
                    cases = out / ("screen.jsonl" if index < 2 else "determinism.jsonl")
                    receipt["quality_run"] = quality.capture_endpoint(
                        qualification=Path(plan["qualification"]), cases=cases, fixtures=Path(plan["fixtures"]),
                        base_url=server.root, model=server.paths["model_id"], api_key_file=key_file,
                        out=directory / "quality", label=f"{lane}/{index}-{label}")
                else:
                    http(server.root, server.key, "/v1/chat/completions",
                         {"model": server.paths["model_id"], "messages": [{"role": "user", "content": "Warm the managed path."}],
                          "max_tokens": 32, "temperature": 0})
                    if mode == "c1":
                        receipt["requests"] = c1(server)
                    elif mode == "role":
                        receipt["requests"] = role_requests(server, plan)
                    elif mode == "requests":
                        receipt["requests"] = [
                            request_metrics(server, dict(entry["body"], model=server.paths["model_id"]), entry["id"])
                            for entry in plan["requests"]]
                    elif mode == "retrieval":
                        body = {"model": server.paths["model_id"], "messages": load(Path(plan["retrieval_fixture"])),
                                "max_completion_tokens": 128, "temperature": 0, "reasoning_effort": "none"}
                        row = request_metrics(server, body, "retrieval_130048")
                        expected = digest(["ORCHID=493817; COLOR=COBALT", "", []])
                        row["exact"] = row["output_sha256"] == expected
                        if row["prompt_tokens"] != 130048 or not row["exact"]:
                            raise CampaignError("130048-token retrieval was not exact")
                        receipt["requests"] = [row]
                    else:
                        replacements = dict(server.paths, arm_dir=str(directory), log=str(directory / "requests.jsonl"),
                                            key_file=str(key_file))
                        argv = [str(value).format_map(replacements) for value in plan["workload_command"]]
                        with (directory / "workload.log").open("wb") as log:
                            subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                           check=True, timeout=float(plan.get("workload_timeout_seconds", 3000)))
                receipt["status"] = "passed"
        except BaseException as error:
            receipt.update(status="failed", error_type=type(error).__name__)
            raise
        finally:
            try:
                try:
                    if server:
                        server.stop()
                        if profile:
                            receipt["nsys"] = server.profile_summary()
                except BaseException as error:
                    receipt.update(status="failed", cleanup_error_type=type(error).__name__)
                    raise
                if sampler.rows:
                    receipt["vram"] = sampler.summary()
            finally:
                try:
                    if abs(gpu(plan["gpu_uuid"])["power_limit_w"] - before["power_limit_w"]) > 0.5:
                        set_power(plan["gpu_uuid"], before["power_limit_w"])
                    receipt["restored_power_limit_w"] = gpu(plan["gpu_uuid"])["power_limit_w"]
                except BaseException as error:
                    receipt.update(status="failed", restore_error_type=type(error).__name__)
                    raise
                finally:
                    save(directory / "receipt.json", receipt)
    arm_paths = [out / f"{index}-{label}" / "receipt.json" for index, label in enumerate(ORDER)]
    if not all(path.exists() for path in arm_paths):
        return {"status": "arm-complete", "completed_index": arm_index}
    arms = [load(path) for path in arm_paths]
    if any(arm["status"] != "passed" for arm in arms):
        raise CampaignError("failed arm cannot produce a matched campaign verdict")
    result = {"artifact_type": "omp-ninfer.matched-campaign", "schema_version": 1, "lane": lane,
              "mode": mode, "plan_sha256": plan_sha, "order": ORDER, "arms": arms}
    if mode == "quality":
        summarize_arms(arms)  # Identity consistency also applies to powered captures.
        args = argparse.Namespace(production=out / "0-A/quality", candidate=out / "1-B/quality",
                                  production_determinism=out / "3-A/quality", candidate_determinism=out / "2-B/quality")
        result["quality"] = quality.verdict(args)
        result["byte_comparison"] = quality.compare_responses(args.production, args.candidate)
    else:
        result["summary"] = summarize_arms(arms, out)
    save(out / "result.json", result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", choices=LANES, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=("c1", "role", "quality", "retrieval", "requests", "command"), default="c1")
    parser.add_argument("--nsys", action="store_true")
    parser.add_argument("--arm-index", type=int, choices=range(4), help="one bounded arm; same out root, indices 0..3")
    args = parser.parse_args(argv)
    try:
        result = run_campaign(args.lane, args.plan, args.out, args.mode, args.nsys, args.arm_index)
    except (CampaignError, quality.ScreenError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"variant_campaign: {error}", file=sys.stderr)
        return 2
    print(json.dumps({key: result[key] for key in ("status", "summary", "byte_comparison") if key in result}, indent=2))
    if args.mode == "quality" and "quality" in result:
        print(json.dumps({"quality_verdict": result["quality"]["verdict"]}))
        return {"pass": 0, "fail": 1, "invalid": 2}[result["quality"]["verdict"]]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
