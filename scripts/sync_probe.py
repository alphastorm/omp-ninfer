#!/usr/bin/env python3
"""Checkpoint replication probe: does a session survive the machine losing its local state?

One stored session is checkpointed, exported with ``scripts/checkpoint_sync.py``, carried
off the machine, and then the lane's local copy is destroyed (server stopped, session
directory removed). The replica is carried back, imported, the server restarted, and the
session's continuation must restore from the imported generation and quote three ledger
keys planted in the template. Two refusals are exercised on the same replica: a payload byte
flip must be refused by the tool before anything reaches the runtime, and a manifest edit
that keeps the payload digests consistent must be refused by the runtime's origin
authentication after import.

The lane-specific glue (how to run the tool on the host, how to carry bytes off and back,
how to stop and start the server, how to destroy the session directory) is passed as shell
commands with ``{session}``, ``{generation}``, ``{flavor}``, and ``{session_dir}`` placeholders
(the export command must print ``session-dir <name>`` for the on-disk session directory). Commands are
recorded in the receipt only as SHA-256 digests so host paths never reach public evidence.

Example (RTX 5090 container):
  python3 scripts/sync_probe.py --lane rtx5090 --base-url http://host:18088 \\
    --api-key-file ~/.omp/agent/ninfer-5090.key --model q38-ninfer --base-tokens 48000 \\
    --export-cmd '<runs checkpoint_sync export on the host into a replica dir>' \\
    --pull-cmd '<copies the replica off the machine>' --wipe-cmd '<rm -rf the session dir>' \\
    --push-cmd '<copies the replica back into a fresh dir>' --import-cmd '<checkpoint_sync import>' \\
    --tamper-payload-cmd '<flips one payload byte in the replica>' \\
    --tamper-manifest-cmd '<edits a manifest field in the replica>' \\
    --stop-cmd '<stop the server>' --start-cmd '<start the server>' \\
    --receipt docs/measurements/$(date +%F)-sync-probe-rtx5090.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fleet_probe import Lane, now, wait_ready  # noqa: E402
from restore_probe import plant_keys, retrieval_prompt, retrieval_result  # noqa: E402


class ProbeError(RuntimeError):
    pass


def run_command(template: str, fields: dict[str, str], timeout: float = 7200.0) -> dict[str, Any]:
    command = template.format(**fields)
    started = now()
    completed = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
    return {"command_sha256": hashlib.sha256(template.encode("utf-8")).hexdigest()[:16],
            "returncode": completed.returncode, "wall_s": round(now() - started, 3),
            "stdout_tail": completed.stdout.strip()[-400:], "stderr_tail": completed.stderr.strip()[-400:]}


def tolerant_status(lane: Lane) -> dict[str, Any]:
    try:
        status = lane.checkpoint_status(timeout=60.0)
    except urllib.error.HTTPError as error:
        return {"http": error.code, "body": error.read().decode("utf-8", "replace")[:300]}
    except Exception as error:  # noqa: BLE001 - diagnostic capture
        return {"error": repr(error)[:300]}
    return {k: status.get(k) for k in ("state", "generation", "bytes", "frontier_tokens", "error")}


def require(step: dict[str, Any], label: str) -> dict[str, Any]:
    if step["returncode"] != 0:
        raise ProbeError(f"{label} failed rc={step['returncode']}: {step['stderr_tail'] or step['stdout_tail']}")
    return step


def wait_down(lane: Lane, deadline_seconds: float) -> None:
    started = now()
    while now() - started < deadline_seconds:
        try:
            lane.status(timeout=5.0)
        except Exception:  # noqa: BLE001 - the endpoint going away is the success condition
            return
        time.sleep(1.0)
    raise ProbeError("server did not stop")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key-file", required=True, type=Path)
    parser.add_argument("--model", default="q38-ninfer")
    parser.add_argument("--base-tokens", type=int, default=48000)
    for name in ("export", "pull", "wipe", "push", "import", "tamper-payload", "tamper-manifest",
                 "stop", "start"):
        parser.add_argument(f"--{name}-cmd", required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()

    api_key = args.api_key_file.read_text().strip()
    session = hashlib.sha256(
        f"sync-probe-{args.lane}-{dt.datetime.now(dt.UTC).isoformat()}".encode()).hexdigest()
    lane = Lane(args.base_url, api_key, session, args.model)
    steps: list[dict[str, Any]] = []

    def record(step: str, payload: dict[str, Any]) -> None:
        steps.append({"step": step, **payload})
        print(f"{step:>22}: {json.dumps(payload, default=str)[:160]}", flush=True)

    def stop_and_start(label: str, between: list[tuple[str, str, dict[str, str]]]) -> None:
        record(f"{label}_stop", require(run_command(args.stop_cmd, {}), "stop"))
        wait_down(lane, 120.0)
        for step_name, template, fields in between:
            record(step_name, require(run_command(template, fields), step_name))
        record(f"{label}_start", require(run_command(args.start_cmd, {}), "start"))
        record(f"{label}_ready", {"ready_after_s": round(wait_ready(lane, 900.0), 2)})

    try:
        filler = "Operations ledger entry %d: throughput nominal, cache warm, retrieval verified. "
        entries = [filler % index for index in range(max(3, (args.base_tokens * 3 // 4) // 11))]
        keys = plant_keys()
        for name, position in zip(keys, (0.05, 0.5, 0.95)):
            index = min(len(entries) - 1, int(len(entries) * position))
            entries[index] += f"Ledger key {name}={keys[name]}. "
        base_doc, base_wall = lane.respond(
            [{"role": "user", "content": [{"type": "input_text",
              "text": "Hold this operations ledger in context for later analysis; reply OK only.\n"
                      + "".join(entries)}]}], previous=None, max_output=40)
        record("base_prefill", {"wall_s": round(base_wall, 3),
                                "input_tokens": base_doc.get("usage", {}).get("input_tokens")})
        control_doc, control_wall = lane.respond(retrieval_prompt(keys, "Control"),
                                                 previous=base_doc["id"], max_output=256)
        record("control_retrieval", {"wall_s": round(control_wall, 3),
                                     **retrieval_result(keys, control_doc)})
        save_doc, save_wall = lane.checkpoint_save(2)
        # The RTX 3090 train's explicit save answers without the generation; the status
        # endpoint carries it on every lane.
        published = lane.checkpoint_status(timeout=60.0)
        generation = str(save_doc.get("generation") or published.get("generation"))
        record("checkpoint_save", {"wall_s": round(save_wall, 3), "mode": save_doc.get("mode"),
                                   "generation": generation,
                                   "bytes": save_doc.get("bytes") or published.get("bytes"),
                                   "frontier": save_doc.get("frontier_tokens") or published.get("frontier_tokens"),
                                   "status_state": published.get("state")})
        if not generation or generation == "None":
            raise ProbeError("save reported no generation")
        fields = {"session": session, "generation": generation, "flavor": "clean", "session_dir": ""}

        # 1. Export from the live store and carry the replica off the machine.
        export = require(run_command(args.export_cmd, fields), "export")
        record("export", export)
        # The export glue prints the on-disk session directory (a namespace digest, not the
        # client session id); later glue addresses the session by it after current advances.
        match = re.search(r"session-dir ([0-9a-f]{64})", export["stdout_tail"] + export["stderr_tail"])
        if not match:
            raise ProbeError("export did not report the session directory")
        fields["session_dir"] = match.group(1)
        record("pull_offsite", require(run_command(args.pull_cmd, fields), "pull"))

        # 2. Destroy the local copy with the server stopped, carry the replica back, import,
        #    restart, and the continuation must restore and quote the keys.
        stop_and_start("restore", [("wipe", args.wipe_cmd, fields),
                                   ("push_onsite", args.push_cmd, fields),
                                   ("import", args.import_cmd, fields)])
        record("status_after_import", tolerant_status(lane))
        started = now()
        restored_doc, restored_wall = lane.respond(retrieval_prompt(keys, "Restored"),
                                                   previous=control_doc["id"], max_output=256)
        record("restored_retrieval", {"wall_s": round(restored_wall, 3),
                                      "input_tokens": restored_doc.get("usage", {}).get("input_tokens"),
                                      **retrieval_result(keys, restored_doc)})
        if not retrieval_result(keys, restored_doc)["exact"]:
            raise ProbeError("restored continuation did not quote the planted keys")

        # 3a. Payload tamper: the tool must refuse before anything reaches the runtime.
        tamper_fields = dict(fields, flavor="payload")
        record("tamper_payload", require(run_command(args.tamper_payload_cmd, tamper_fields), "tamper"))
        record("push_tampered_payload", require(run_command(args.push_cmd, tamper_fields), "push"))
        refused = run_command(args.import_cmd, tamper_fields)
        record("import_tampered_payload", refused)
        if refused["returncode"] == 0:
            raise ProbeError("tool imported a tampered payload")
        if "manifest digest" not in refused["stdout_tail"] + refused["stderr_tail"]:
            raise ProbeError("tampered payload was refused for the wrong reason: "
                             + (refused["stdout_tail"] or refused["stderr_tail"])[:200])

        # 3b. Manifest tamper with consistent payload digests: the tool passes it through and
        #     the runtime's origin authentication must refuse it after a restart.
        manifest_fields = dict(fields, flavor="manifest")
        record("tamper_manifest", require(run_command(args.tamper_manifest_cmd, manifest_fields), "tamper"))
        record("push_forged_manifest", require(run_command(args.push_cmd, manifest_fields), "push"))
        stop_and_start("forged", [("wipe_again", args.wipe_cmd, manifest_fields),
                                  ("import_forged_manifest", args.import_cmd, manifest_fields)])
        record("status_forged", tolerant_status(lane))
        # The runtime must not resurrect the session from a forged manifest: either the
        # continuation is refused (404 previous_response_not_found) or it is served from a
        # fresh replay without the checkpoint. Both are recorded; a restore that quotes the
        # keys through the forged generation is the failure.
        forged_started = now()
        try:
            forged_doc, forged_wall = lane.respond(retrieval_prompt(keys, "Forged"),
                                                   previous=control_doc["id"], max_output=256)
            forged = {"http": 200, "wall_s": round(forged_wall, 3),
                      "input_tokens": forged_doc.get("usage", {}).get("input_tokens"),
                      **retrieval_result(keys, forged_doc)}
        except urllib.error.HTTPError as refusal:
            forged = {"http": refusal.code, "wall_s": round(now() - forged_started, 3),
                      "body": refusal.read().decode("utf-8", "replace")[:300]}
        forged.update({"state_after": tolerant_status(lane).get("state")})
        record("forged_continuation", forged)
        if forged.get("http") == 200 and forged.get("exact") and forged["state_after"] == "available":
            raise ProbeError("runtime restored through a forged manifest")
        record("session_delete", {"status": lane.checkpoint_delete()})
        status = "passed"
        error = None
    except (ProbeError, subprocess.TimeoutExpired, RuntimeError) as failure:
        status = "failed"
        error = str(failure)
        print(f"FAILED: {error}", flush=True)

    by_step = {entry["step"]: entry for entry in steps}
    receipt = {
        "artifact_type": "omp_ninfer_sync_probe",
        "schema_version": 1,
        "lane": args.lane,
        "generated_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "error": error,
        "summary": {
            "template_input_tokens": by_step.get("base_prefill", {}).get("input_tokens"),
            "checkpoint_bytes": by_step.get("checkpoint_save", {}).get("bytes"),
            "export_wall_s": by_step.get("export", {}).get("wall_s"),
            "import_wall_s": by_step.get("import", {}).get("wall_s"),
            "restored_wall_s": by_step.get("restored_retrieval", {}).get("wall_s"),
            "restored_retrieval_exact": by_step.get("restored_retrieval", {}).get("exact"),
            "tampered_payload_refused_by_tool": by_step.get("import_tampered_payload", {}).get("returncode") not in (None, 0),
            "forged_manifest_state": by_step.get("status_forged", {}).get("state"),
            "forged_continuation_http": by_step.get("forged_continuation", {}).get("http"),
            "forged_continuation_state": by_step.get("forged_continuation", {}).get("state_after"),
        },
        "steps": steps,
        "transient_retries": lane.retries,
    }
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(f"receipt written: {args.receipt}")
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
