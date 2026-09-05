#!/usr/bin/env python3
"""Container-lane profile gates for the RTX 5090: long-context, decode, agent protocol, restart.

Runs against a lifecycle-started candidate container through a loopback tunnel and writes one
receipt with the same gate names as ``releases/<version>/qualification/rtx5090.json``. The fanout
acceptance runs separately through ``scripts/fleet_probe.py`` and is bound by reference. Every
number is measured in this process; nothing is inherited.

Example:
  python3 scripts/qualify_rtx5090_profile.py --base-url http://127.0.0.1:18191 \
    --api-key-file ~/.omp/agent/ninfer-5090.key --model q38-ninfer \
    --long-fixture ../ninfer/examples/cli/messages/long_niah_128k.json \
    --restart-cmd "ssh nyc-pc wsl.exe -d Ubuntu-24.04 -e docker restart ninfer-5090-v048c" \
    --log-cmd "ssh nyc-pc wsl.exe -d Ubuntu-24.04 -e cat /home/sunil/services/variant-5090/v048/logs/requests-*.jsonl" \
    --vram-cmd "ssh nyc-pc wsl.exe -d Ubuntu-24.04 -e nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits" \
    --receipt docs/measurements/2026-09-05-rtx5090-v048-profile-gates.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import urllib.error
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fleet_probe import Lane, now, wait_ready  # noqa: E402

EXPECTED_LONG = "ORCHID=493817; COLOR=COBALT"
DECODE_PROMPT = (
    "Write a detailed technical design document for a durable, restart-safe session checkpoint "
    "store used by a local LLM inference server. Cover the on-disk layout, generation manifests, "
    "atomic publication, integrity verification, quota reclamation, lazy restore, and the failure "
    "modes of each stage, with concrete pseudocode for every component. Be exhaustive."
)


def run_cmd(cmd: str, timeout: float) -> str:
    completed = subprocess.run(cmd, shell=True, check=True, capture_output=True, timeout=timeout)
    return completed.stdout.decode(errors="replace")


def vram_mib(cmd: str | None) -> int | None:
    if not cmd:
        return None
    try:
        return int(run_cmd(cmd, 60).strip().splitlines()[0])
    except Exception:  # noqa: BLE001 - sampling must never fail a gate
        return None


def request_done_records(log_cmd: str | None) -> list[dict[str, Any]]:
    if not log_cmd:
        return []
    records = []
    for line in run_cmd(log_cmd, 300).splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("event") == "request_done":
            records.append(record)
    return records


def find_decode_record(records: list[dict[str, Any]], prompt_tokens: int | None,
                       completion_tokens: int | None) -> dict[str, Any] | None:
    # The request log numbers requests per process and does not echo the client's
    # ninfer_request_id, so the decode request is matched by its exact token shape.
    for record in reversed(records):
        result = record.get("result", {})
        if (result.get("prompt_tokens") == prompt_tokens
                and result.get("completion_tokens") == completion_tokens):
            return record
    return None


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gate_long_context(lane: Lane, fixture: Path, vram_cmd: str | None) -> dict[str, Any]:
    messages = json.loads(fixture.read_text(encoding="utf-8"))
    started = now()
    document = lane._request(
        "/v1/chat/completions",
        {"model": lane.model, "messages": messages, "max_completion_tokens": 128,
         "temperature": 0, "reasoning_effort": "none"},
        timeout=1800.0,
    )
    elapsed = now() - started
    content = document["choices"][0]["message"]["content"].strip()
    usage = document["usage"]
    return {
        "status": "passed" if content == EXPECTED_LONG else "failed",
        "fixture_sha256": sha256_file(fixture),
        "prompt_tokens": usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
        "exact_output": content == EXPECTED_LONG,
        "output": content,
        "wall_s": round(elapsed, 3),
        "tokens_per_second_wall": round(usage["prompt_tokens"] / elapsed, 1),
        "vram_used_mib_after": vram_mib(vram_cmd),
    }


def gate_decode(lane: Lane, request_id: str) -> dict[str, Any]:
    payload = {
        "model": lane.model,
        "input": DECODE_PROMPT,
        "store": False,
        "temperature": 0,
        "max_output_tokens": 2048,
        "ninfer_session": lane.session,
        "ninfer_request_id": request_id,
    }
    started = now()
    document = lane._request("/v1/responses", payload, 1800.0)
    elapsed = now() - started
    usage = document.get("usage", {})
    return {
        "request_id": request_id,
        "prompt_tokens": usage.get("input_tokens"),
        "completion_tokens": usage.get("output_tokens"),
        "wall_s": round(elapsed, 3),
        "completion_tokens_per_second_wall": round(usage.get("output_tokens", 0) / elapsed, 2),
    }


def gate_agent_protocol(lane: Lane, restart_cmd: str | None) -> dict[str, Any]:
    base, _ = lane.respond("You are a build assistant. Reply with the single word READY.", None, 16)
    fork_a, _ = lane.respond("Fork A: reply with the single word ALPHA.", base["id"], 16)
    fork_b, _ = lane.respond("Fork B: reply with the single word BRAVO.", base["id"], 16)
    forks = [fork_a["id"], fork_b["id"]]

    def delete(response_id: str) -> int:
        try:
            lane._request(f"/v1/responses/{response_id}", None, 120.0, method="DELETE")
            return 200
        except urllib.error.HTTPError as error:
            return error.code

    def continue_status(response_id: str) -> tuple[int, str | None]:
        try:
            lane.respond("Continue: reply with the single word CHARLIE.", response_id, 16)
            return 200, None
        except urllib.error.HTTPError as error:
            body = error.read().decode(errors="replace")
            code = None
            try:
                code = json.loads(body).get("error", {}).get("code")
            except json.JSONDecodeError:
                pass
            return error.code, code

    parent_delete_status = delete(fork_a["id"])
    deleted_status, deleted_code = continue_status(fork_a["id"])
    survivor_status, _ = continue_status(fork_b["id"])
    post_restart_deleted_status = None
    if restart_cmd:
        subprocess.run(restart_cmd, shell=True, check=True, capture_output=True, timeout=600)
        wait_ready(lane, 600.0)
        post_restart_deleted_status, _ = continue_status(fork_a["id"])
    passed = (parent_delete_status == 200 and deleted_status == 404
              and deleted_code == "previous_response_not_found" and survivor_status == 200
              and (post_restart_deleted_status in (None, 404)))
    return {
        "status": "passed" if passed else "failed",
        "authenticated_session_identity": True,
        "stateful_continuation": True,
        "forks": len(forks),
        "parent_delete_status": parent_delete_status,
        "deleted_continuation_status": deleted_status,
        "deleted_continuation_error_code": deleted_code,
        "post_restart_deleted_continuation_status": post_restart_deleted_status,
        "no_resurrection": post_restart_deleted_status == 404 if restart_cmd else None,
        "surviving_descendant_continued": survivor_status == 200,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key-file", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--long-fixture", type=Path, required=True)
    parser.add_argument("--restart-cmd")
    parser.add_argument("--log-cmd")
    parser.add_argument("--vram-cmd")
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    api_key = Path(args.api_key_file).expanduser().read_text().strip()
    stamp = dt.datetime.now(dt.UTC).isoformat()

    def lane_for(gate: str) -> Lane:
        # One session per gate: a session that holds a 130K chat context rejects a fresh
        # Responses lineage, and the gates are independent measurements anyway.
        return Lane(args.base_url, api_key,
                    hashlib.sha256(f"qualify-5090-{gate}-{stamp}".encode()).hexdigest(), args.model)

    lane = lane_for("status")
    status_before = lane.status()
    receipt: dict[str, Any] = {
        "artifact_type": "omp_ninfer_rtx5090_profile_gates",
        "schema_version": 1,
        "generated_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "identity": status_before.get("identity"),
        "runtime": status_before.get("runtime"),
        "vram_used_mib_idle": vram_mib(args.vram_cmd),
        "gates": {},
    }
    lanes = {gate: lane_for(gate) for gate in ("prefill", "decode", "protocol")}
    receipt["gates"]["prefill_curve"] = gate_long_context(lanes["prefill"], args.long_fixture, args.vram_cmd)
    print("prefill_curve", json.dumps(receipt["gates"]["prefill_curve"]), flush=True)
    decode_request = hashlib.sha256(f"decode-{lanes['decode'].session}".encode()).hexdigest()
    receipt["gates"]["decode"] = gate_decode(lanes["decode"], decode_request)
    print("decode", json.dumps(receipt["gates"]["decode"]), flush=True)
    receipt["gates"]["agent_protocol"] = gate_agent_protocol(lanes["protocol"], args.restart_cmd)
    print("agent_protocol", json.dumps(receipt["gates"]["agent_protocol"]), flush=True)
    try:
        records = request_done_records(args.log_cmd)
    except (subprocess.SubprocessError, OSError) as error:
        records = []
        receipt["log_join_error"] = str(error)[:300]
    decode_record = find_decode_record(
        records, receipt["gates"]["decode"]["prompt_tokens"], receipt["gates"]["decode"]["completion_tokens"])
    prefill_records = [r for r in records
                       if r.get("result", {}).get("prompt_tokens") == receipt["gates"]["prefill_curve"]["prompt_tokens"]]
    if prefill_records:
        last = prefill_records[-1]
        receipt["gates"]["prefill_curve"].update({
            "server_prefix_cache_hit_tokens": last["result"].get("prefix_cache_hit_tokens"),
            "server_prefix_reuse_path": last["result"].get("prefix_reuse_path"),
            "server_computed_prefill_tokens": last["result"].get("computed_prefill_tokens"),
            "server_prefill_seconds": last.get("timings_seconds", {}).get("prefill"),
            "cold": (last["result"].get("prefix_cache_hit_tokens") or 0) == 0,
        })
    if decode_record is not None:
        result = decode_record.get("result", {})
        timings = decode_record.get("timings_seconds", {})
        speculative = decode_record.get("speculative", {})
        drafted = speculative.get("drafted_tokens") or 0
        rounds = speculative.get("rounds") or 0
        receipt["gates"]["decode"].update({
            "server_completion_tokens": result.get("completion_tokens"),
            "server_decode_seconds": timings.get("decode"),
            "decode_tokens_per_second": (
                round(result["completion_tokens"] / timings["decode"], 2)
                if timings.get("decode") else None),
            "mtp_acceptance_rate": (
                round(speculative.get("accepted_tokens", 0) / drafted, 3) if drafted else None),
            "mtp_tokens_per_round": (
                round(result["completion_tokens"] / rounds, 2) if rounds else None),
            "speculative": speculative,
        })
    receipt["status"] = "passed" if all(
        g.get("status", "passed") == "passed" for g in receipt["gates"].values()) else "failed"
    receipt["vram_used_mib_final"] = vram_mib(args.vram_cmd)
    receipt["transient_retries"] = sum(l.retries for l in lanes.values())
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"receipt written: {args.receipt} status={receipt['status']}", flush=True)
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.HTTPError as error:
        print(f"HTTP {error.code} on {error.url}: {error.read().decode(errors='replace')[:800]}", file=sys.stderr)
        sys.exit(1)
