#!/usr/bin/env python3
"""Collect completed acceptance-driver outputs without running a window.

Platform postures come exclusively from the release plan. Receipts are copied unchanged
to ``<receipts-dir>/<lane>-run.json`` (default: ``<output parent>/receipts``); stdout is
a JSON object with the evidence path and the five composer ``--route`` paths.
``--lane-dir LANE=DIR`` selects an accepted directory explicitly; otherwise exactly
``<window-root>/<lane>`` is used. No attempt directory or acceptance verdict is guessed.
For a corrected slot, ``--corrected-attempt LANE=PRIOR_DIR`` identifies its restored
failed predecessor. Founder exceptions require both ``--native-route-waiver`` and
``--lead-restoration`` (raw output) and ``--lead-restoration-proof`` (JSON) bindings,
never merely a failed status. Post-recovery census paths can also be supplied explicitly.
Component cut/carry and source-count prose is deliberately absent: the composer owns it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compose_route_acceptance as composer
from release_io import atomic_write
from verify_release import native_profile, validate_native_route_waiver, validate_native_lead_recovery
from compose_native_qualification import native_probe_acceptance_errors, native_probe_summary

LANES = ("rtx5090", "rtx4090", "rtx3090")
LABELS = {"mac": "darwin-remote-ssh", "windows": "windows-docker-local",
          "linux": "linux-docker-local"}


def require(condition: Any, message: str) -> None:
    if not condition:
        raise SystemExit("collect_route_evidence: " + message)


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        raise SystemExit(f"collect_route_evidence: cannot read {path.name}: {error}") from error
    require(isinstance(value, dict), f"{path.name} must contain an object")
    return value


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def subject(value: dict, release: str, candidate: str, label: str, *, native: bool = False) -> None:
    require(value.get("release") == release
            and value.get("candidate_commit" if native else "candidate") == candidate,
            f"{label}: release or candidate differs")


def checks(value: dict, label: str, status: str = "passed") -> None:
    require(value.get("status") == status, f"{label}: status is not {status}")
    observed = value.get("checks")
    require(isinstance(observed, dict) and observed and all(child is True for child in observed.values()),
            f"{label}: checks did not all pass")


def pairs(arguments: list[str], label: str, *, allowed: tuple[str, ...] = LANES) -> dict[str, Path]:
    output = {}
    for argument in arguments:
        lane, separator, value = argument.partition("=")
        require(separator and lane in allowed and value, f"{label} needs LANE=PATH")
        require(lane not in output, f"duplicate {label} for {lane}")
        output[lane] = Path(value).expanduser().resolve()
    return output


def collected_native(folder: Path, release: str, candidate: str) -> dict:
    collection = load(folder / "driver-collection.json")
    subject(collection, release, candidate, "native collection")
    require(collection.get("status") == "collected", "native window is uncollected")
    for field, filename in (("window_sha256", "window.json"),
                            ("restoration_sha256", "restoration.json"),
                            ("final_audit_sha256", "final-audit.json")):
        require(collection.get(field) == digest(folder / "evidence" / filename),
                f"native collection {field} does not match collected bytes")
    return load(folder / "evidence/window.json")


def corrected_prior(lane: str, folder: Path, release: str, candidate: str) -> dict:
    if lane == "rtx5090":
        restored = load(folder / "restoration.json")
        require(all(restored.get(key) is True for key in (
            "running", "same_image", "checkpoint_mount_retained", "documented_key_restored",
            "checkout_restored", "beta_absent", "documented_directories_restored")),
            "corrected container attempt needs a restored prior window")
        require(restored.get("health", {}).get("status") == "ok",
                "corrected container attempt prior window is unhealthy")
        subject(load(folder / "preflight.json"), release, candidate, "prior container preflight")
        failure = load(folder / "first-failure.json")
        require(isinstance(failure.get("boundary"), str) and bool(failure["boundary"]),
                "corrected attempt needs a failed prior window")
        require(load(folder / "window-attempt.json").get("attempt") == "initial",
                "corrected attempt needs the initial prior window")
        if (folder / "final-summary.json").is_file():
            require(load(folder / "final-summary.json").get("status") != "passed",
                    "corrected attempt prior window already passed")
        require(load(folder / "collection.json").get("completed_utc"),
                "prior container window is uncollected")
        return restored
    window = collected_native(folder, release, candidate)
    subject(window, release, candidate, "prior native window")
    require(window.get("status") == "failed" and window.get("restoration_status") == "passed",
            "corrected native attempt needs a failed and restored prior window")
    for name in ("restoration.json", "final-audit.json"):
        checks(load(folder / "evidence" / name), "prior native " + name)
    return window


def templates() -> dict:
    return {
        "scope": "Fresh candidate-bound documented routes, stock clients, native public installs "
                 "and candidate-profile probes. Linux is WSL2-scoped; macOS remains preview.",
        "mode": "Fresh candidate-bound acceptance; native lanes and the incumbent "
                "production service restored after final windows.",
        "document_change": "Only later non-executable release-state prose may change; composer must "
                           "independently require every executed block to remain byte-identical.",
        "deferred_routes": {},
        "qualification_environment": "One Windows/WSL2 RTX 5090 container host with macOS arm64 and "
            "native Windows x64 clients, plus a WSL2 Linux x64 client; one two-GPU Windows host "
            "served the native lanes sequentially. Owner-operated tester-equivalent, not "
            "independent external-user acceptance.",
    }


def lead_recovery(output: Path, proof_path: Path, waiver: dict, candidate: str,
                  lane: str, census: dict) -> dict:
    require(waiver["evidence_sha256"].get("lead-restoration.out") == digest(output)
            and waiver["evidence_sha256"].get("lead-restoration.json") == digest(proof_path),
            f"{lane}: waiver must bind both lead restoration sources")
    proof = load(proof_path)
    require(proof.get("candidate_commit") == candidate and proof.get("lane") == lane + "-native"
            and proof.get("status") == "restored-by-lead"
            and all(proof.get(key) is True for key in (
                "census_equal", "holds_client_files_equal", "failed_evidence_unchanged"))
            and proof.get("checks") and all(value is True for value in proof["checks"].values()),
            f"{lane}: lead restoration proof failed")
    text = output.read_text(encoding="utf-8-sig")
    records = []
    for match in re.finditer(r"(?m)^\{", text):
        try:
            record, _ = json.JSONDecoder().raw_decode(text[match.start():])
        except ValueError:
            continue
        if isinstance(record, dict):
            records.append(record.get("last_stop", record))
    graceful = [record for record in records if record.get("outcome") == "graceful"]
    require(graceful, f"{lane}: lead recovery did not record a graceful managed Stop")
    owner = next(row for row in census["lanes"] if row["lane"] == lane)
    return {
        "status": proof["status"], "outcome": graceful[-1]["outcome"],
        "sessions_refused": graceful[-1]["sessions_refused"],
        "runtime_record_absent": proof["checks"]["runtime_record_absent"],
        "gpu_owner_lease_absent": proof["checks"]["gpu_owner_lease_absent"],
        "power_limit_w": owner["power_limit_w"],
        "all_native_tasks_ready": all(row["task_state"] == "Ready" for row in census["lanes"]),
        "server_processes": len(census["processes"]), "port_18082_listeners": len(census["listeners"]),
    }


def collect(root: Path, release: str, candidate: str, window_root: Path, plan: dict,
            *, lane_dirs: dict[str, Path] | None = None,
            corrected: dict[str, Path] | None = None,
            waivers: dict[str, Path] | None = None,
            recoveries: dict[str, Path] | None = None,
            recovery_proofs: dict[str, Path] | None = None,
            final_census: Path | None = None, final_holds: Path | None = None) -> tuple[dict, dict[str, Path]]:
    require(re.fullmatch(r"[0-9a-f]{40}", candidate), "candidate must be a full commit")
    require(plan.get("artifact_type") == "omp_ninfer_release_plan"
            and plan.get("schema_version") == 1 and plan.get("release") == release,
            "plan must be this release's schema-1 release plan")
    manifest = load(root / "releases" / release / "manifest.json")
    authority = load(root / "compatibility.json")
    require(manifest.get("release") == release and authority.get("product_release") == release,
            "manifest and promoted authority must name the requested release")
    platforms = plan.get("platforms")
    require(isinstance(platforms, dict)
            and set(platforms) == {profile["id"] for profile in authority["profiles"]}
            and all(status in ("qualified", "preview") for status in platforms.values()),
            "plan.platforms must name every authority profile with qualified or preview")
    directories = {lane: window_root / lane for lane in LANES}
    directories.update(lane_dirs or {})
    corrected, waivers, recoveries = corrected or {}, waivers or {}, recoveries or {}
    recovery_proofs = recovery_proofs or {}
    variants = {row["id"].split("-")[0]: row for row in manifest["components"].get("ninfer_variants", [])}
    native = {lane: variants[lane] for lane in LANES[1:] if lane in variants}
    require(set(directories) == set(LANES) and set(corrected) <= set(LANES),
            "unknown lane directory or corrected attempt")
    require(set(waivers) == set(recoveries) == set(recovery_proofs) and set(waivers) <= set(native),
            "each native waiver needs exactly one explicit lead restoration")
    priors = {lane: corrected_prior(lane, folder, release, candidate)
              for lane, folder in corrected.items()}
    runtime = directories["rtx5090"]
    require(load(runtime / "collection.json").get("missing") == [], "container window is uncollected")
    summary = load(runtime / "final-summary.json")
    subject(summary, release, candidate, "container summary")
    require(summary.get("status") == "passed", "container window failed")
    require(set(summary.get("clients", {})) == set(LABELS), "container clients are incomplete")
    for label, client in summary["clients"].items():
        subject(client, release, candidate, label + " client")
        require(client.get("status") == "passed", f"{label} client failed")
        composer.check_live(LABELS[label], client["live_acceptance"], manifest)
    rr = summary["restoration"]
    raw_restoration = load(runtime / "restoration.json")
    require(all(key in raw_restoration for key in (
        "running", "health", "same_image", "image", "restart", "checkpoint_mount_retained",
        "documented_key_restored", "checkout_restored", "beta_absent",
        "documented_directories_restored", "window_seconds"))
        and all(rr.get(key) == value for key, value in raw_restoration.items()),
        "container restoration differs from summary")
    post = load(window_root / "production-and-fleet-after.json")
    require(post.get("candidate") == candidate and post.get("status") == "passed" and post.get("same_container") is True
            and post.get("same_image") is True and post.get("health_http") == 200
            and post.get("restart_policy") == "unless-stopped"
            and post.get("checkpoint_mounts_identical_sorted_by_destination") is True
            and post.get("fleet_phase") == "Fleet" and post.get("fleet_healthy") is True,
            "post-window production service is unrestored")
    original = load(window_root / "native-pre-window-census.json")
    final_census = final_census or window_root / "native-final.json"
    final_holds = final_holds or window_root / "native-final-holds-client.json"
    final = load(final_census)
    holds = load(window_root / "native-pre-window-census-holds-client.json")
    final_holds_value = load(final_holds)
    require(original == final and holds == final_holds_value, "native census or client files are unrestored")
    require(not final["processes"] and not final["listeners"], "native processes or listeners remain")

    def reference(path: Path) -> dict:
        base = window_root.resolve()
        resolved = path.resolve()
        # An explicit lane override may live outside the window root. Keep a logical lane name,
        # never an absolute private path, in the composer's provenance references.
        if resolved.is_relative_to(base):
            name = resolved.relative_to(base).as_posix()
        elif resolved == final_census.resolve():
            name = "native-final.json"
        else:
            matches = [(lane, folder.resolve()) for lane, folder in directories.items()
                       if resolved.is_relative_to(folder.resolve())]
            require(len(matches) == 1, "evidence source is outside the selected lane directories")
            lane, folder = matches[0]
            name = lane + "/" + resolved.relative_to(folder).as_posix()
        return {"evidence_name": name, "sha256": digest(path)}

    health = rr["windows_health"]
    if isinstance(health, dict):
        windows_health = health.get("status") == "ok" or health.get("status_code") == 200
    else:
        windows_health = "ok" in str(health).lower() or "200" in str(health)
    restore5090 = {
        "original_runtime_healthy": rr["running"] and rr["health"]["status"] == "ok",
        "original_image_retained": rr["same_image"], "original_image": rr["image"],
        "restart_policy": rr["restart"], "checkpoint_mount_retained": rr["checkpoint_mount_retained"],
        "documented_route_key_restored": rr["documented_key_restored"],
        "original_checkout_restored": rr["checkout_restored"], "route_container_absent": rr["beta_absent"],
        "window_hold_removed": bool(rr["windows_release"]),
        "preexisting_markers_and_supervisors_unchanged": rr["windows_markers_tasks_unchanged"],
        "documented_directories_restored": rr["documented_directories_restored"],
        "retained_window_created_parents": rr["retained_window_created_parents"],
        "windows_health_ok": windows_health, "wsl_health_ok": rr["health"]["status"] == "ok",
        "same_container_retained": post["same_container"], "fleet_phase": post["fleet_phase"],
        "fleet_healthy": post["fleet_healthy"], "completed_utc": rr["completed_utc"],
        "window_hold_seconds": [rr["window_seconds"]], "production_windows": 1,
        "source_summary": reference(runtime / "final-summary.json"),
        "source_restoration": reference(runtime / "restoration.json"),
    }
    if "rtx5090" in priors:
        require(summary.get("corrections"), "corrected container attempt needs explicit corrections")
        restore5090["window_hold_seconds"].insert(0, priors["rtx5090"]["window_seconds"])
        restore5090["production_windows"] = 2
    else:
        require(not summary.get("corrections"), "corrected container attempt requires explicit input")
    restore5090["accepted_window_hold_seconds"] = rr["window_seconds"]
    restoration = {"candidate_commit": candidate, "rtx5090": restore5090}
    evidence = {"platforms": {}, "restoration": restoration,
                "documented_routes": templates()}
    pf, wp, hp = (load(runtime / name) for name in (
        "preflight.json", "windows-preflight.json", "host-preflight.json"))
    subject(pf, release, candidate, "container preflight")
    require(pf.get("status") == wp.get("status") == hp.get("status") == "passed"
            and wp.get("candidate") == candidate, "container preflight failed or differs from candidate")
    client_digests = {"mac": pf["mac_binary_sha256"], "windows": wp["binary_sha256"],
                      "linux": hp["client_binary_sha256"]}
    profiles = {row["id"]: row for row in authority["profiles"]}
    for label, profile in LABELS.items():
        client = summary["clients"][label]
        require(client_digests[label] == profiles[profile]["client_distribution"]["binary_sha256"],
                f"{profile}: preflight binary differs from authority")
        evidence["platforms"][profile] = {
            "release": client["release"], "candidate": client["candidate"],
            "status": platforms[profile], "binary_sha256": client_digests[label],
            "live_acceptance": client["live_acceptance"],
            "limitations": ["Owner-operated tester-equivalent acceptance; no new runtime performance guarantee."]
                + (["macOS manual SSH preview."] if label == "mac" else [])
                + (["Linux x64 under WSL2 only; no separate native Linux OS or Linux vision claim."]
                   if label == "linux" else []),
        }
    routes = dict(zip(composer.LANES, (runtime / name for name in (
        "host-route.json", "mac-route.json", "windows-route.json"))))
    for lane, variant in native.items():
        folder = directories[lane]
        window = load(folder / "driver-window.json")
        subject(window["plan"], release, candidate, lane + " driver plan")
        expected_attempt = 2 if lane in corrected else 1
        require(window["plan"].get("attempt") == expected_attempt,
                f"{lane}: corrected attempt requires explicit prior input")
        collected = collected_native(folder, release, candidate)
        subject(collected, release, candidate, lane + " collected window")
        require(collected.get("attempt") == expected_attempt,
                f"{lane}: collected attempt differs from explicit selection")
        route_path = folder / "evidence/route.json"
        routes[lane + "-native"] = route_path
        if lane in waivers:
            waiver = load(waivers[lane])
            recovery = lead_recovery(recoveries[lane], recovery_proofs[lane], waiver, candidate, lane, final)
            failure = load(folder / "evidence/window-failure.json")
            route = load(route_path)
            binding = {"repository_path": waivers[lane].resolve().relative_to(root.resolve()).as_posix(),
                       "sha256": digest(waivers[lane])}
            require(window.get("status") == collected.get("status") == "failed",
                    f"{lane}: waiver requires a failed native campaign")
            require(not (folder / "public-install.json").exists(),
                    f"{lane}: waiver cannot replace a completed public install")
            owner = next(row for row in original["lanes"] if row["lane"] == lane)
            errors = []
            validate_native_lead_recovery(recovery, owner["power_limit_w"], lane, errors)
            require(not errors, "; ".join(errors))
            failed = {"evidence_name": f"{lane}/evidence/window-failure.json",
                      "sha256": digest(folder / "evidence/window-failure.json"),
                      "boundary": failure["boundary"], "observed_summary": waiver["observed_summary"]}
            census = {**reference(window_root / "native-pre-window-census.json"), "lane": lane,
                      "power_limit_w": owner["power_limit_w"]}
            behavior = load(folder / "evidence/expected-runtime.json")
            probe_acceptance = native_probe_summary({
                name: load(folder / "evidence" / (name + "-probe.json"))
                for name in ("fleet", "fanout", "parallel", "compaction")
                if (folder / "evidence" / (name + "-probe.json")).is_file()})
            for name, source in (
                ("documented-route.json", route_path),
                ("window-failure.json", folder / "evidence/window-failure.json"),
                ("driver-window.json", folder / "driver-window.json"),
                ("pre-window-census.json", window_root / "native-pre-window-census.json"),
            ):
                require(waiver.get("evidence_sha256", {}).get(name) == digest(source),
                        f"{lane}: waiver does not bind {name}")
            if waiver.get("failed_phase") == "native-probes":
                probe = load(folder / "evidence/compaction-probe.json")
                require(waiver["evidence_sha256"].get("compaction-probe.json")
                        == digest(folder / "evidence/compaction-probe.json")
                        and probe.get("passed") is False
                        and probe.get("error") == waiver["observed_summary"].get("error"),
                        f"{lane}: waiver does not match the failed compaction capture")
            else:
                refused = re.fullmatch(
                    r"incomplete shutdown: (\d+) live session\(s\) refused; "
                    r"preserve candidate checkpoints and reconcile before rollback", failure.get("error", ""))
                require(refused is not None
                        and int(refused[1]) == waiver["observed_summary"].get("sessions_refused"),
                        f"{lane}: waiver does not match the refused managed Stop")
            validate_native_route_waiver(
                root, release, candidate, lane + "-native", failure["boundary"], binding, errors,
                window_failure=failed, stopped_owner_census=census, probe_acceptance=probe_acceptance)
            require(not errors, "; ".join(errors))
            preparation = load(folder / "evidence/preparation.json")
            subject(preparation, release, candidate, lane + " waived preparation")
            require(preparation.get("lineage_mode") == "first_release"
                    and preparation.get("previous_release_present") is False,
                    f"{lane}: founder campaign waiver requires observed first-lineage preparation")
            configuration = native_profile(root, release, variant, errors)
            require(configuration is not None and not errors, "; ".join(errors))
            errors = native_probe_acceptance_errors(
                configuration, probe_acceptance, variant, manifest["components"]["omp"]["binary_sha256"],
                waived_failed_compaction=waiver["failed_phase"] == "native-probes")
            require(not errors, lane + ": " + "; ".join(errors))
            evidence[lane] = {
                **{key: route[key] for key in ("candidate_commit", "release", "client", "installed")},
                "status": "failed", "failed_phase": failure["boundary"], "founder_waiver": binding,
                "window_failure": failed, "stopped_owner_census": census,
                "runtime_configuration": behavior["configuration"], "probe_acceptance": probe_acceptance,
                "preparation": {key: preparation[key] for key in ("lineage_mode", "previous_release_present")},
                "observations": {"rollback": {"status": "not_applicable", "directions": 0,
                                             "reason": "first release of the lineage"}},
                "limitations": [waiver["application_rule"], waiver["disclosure_required"]],
            }
            restoration[lane] = {**waiver["restoration_summary"], **recovery, "founder_waiver": binding,
                                 "wrapper_audit_status": "failed"}
            continue
        require(window.get("status") == collected.get("status") == "passed_and_restored"
                and collected.get("restoration_status") == "passed"
                and collected.get("first_failing_boundary") is None
                and all(window.get(key, 0) == 0 for key in ("accept_exit", "restoration_exit", "audit_exit")),
                f"{lane}: native window failed or is unrestored")
        behavior, restored, audit, prep = (load(folder / "evidence" / name) for name in (
            "behavior-evidence.json", "restoration.json", "final-audit.json", "preparation.json"))
        public = load(folder / "public-install.json")
        for value, label in ((behavior, "behavior"), (restored, "restoration"), (audit, "final audit")):
            checks(value, lane + " " + label)
        require(public.get("status") == "passed" and public.get("restoration", {}).get("prior_state_restored") is True,
                f"{lane}: public install failed or is unrestored")
        subject(behavior, release, candidate, lane + " behavior", native=True)
        subject(prep, release, candidate, lane + " preparation")
        require(public["source"].get("product_release") == release
                and public["source"].get("candidate_commit") == candidate,
                f"{lane}: public install subject differs")
        require(prep.get("status") == "restored", f"{lane}: preparation is unrestored")
        row = next(item for item in final["lanes"] if item["lane"] == lane)
        require(row["task_state"] == "Ready" and not row["lease_entries"], f"{lane}: owner is unrestored")
        first = prep["lineage_mode"] == "first_release"
        require(first == (prep["previous_release_present"] is False), f"{lane}: inconsistent lineage mode")
        rollback = ({"status": "not_applicable", "directions": 0, "reason": "first release of the lineage"}
                    if first else behavior.get("rollback"))
        require(isinstance(rollback, dict), f"{lane}: upgrade window needs observed rollback")
        observations = {
            "exact_tool_marker": behavior["checks"]["exact_tool_marker"],
            "server_tool_calls": sum(item["tool_call_count"] for item in behavior["request_summaries"]),
            "linked_tool_history": behavior["checks"]["linked_tool_history"],
            "exact_continuation_nonce": behavior["checks"]["exact_continuation_nonce"],
            "continuation_reuse": behavior["request_summaries"][-1]["prefix_reuse_path"],
            "offline_request_failed_without_model_response": behavior["checks"]["offline_failed_without_response"],
            "recovery_health_and_bound_runtime_identity_passed":
                behavior["checks"]["recovered_healthy"] and behavior["checks"]["served_identity_bound"],
            "local_reasoning_compatibility_retries": len(behavior["local_compatibility_errors"]),
            "cloud_fallback_observed": not behavior["checks"]["only_local_client_responses"],
            "structured_client": behavior["live_acceptance"],
            "documented_marker_bare_line": behavior["documented_marker_bare_line"],
            "rollback": rollback, "retained_previous_release": row["previous_release"],
            "public_install": {key: public[key] for key in (
                "status", "source", "client", "integrity", "installed", "install", "smoke", "restoration")},
        }
        evidence[lane] = {
            **{key: behavior[key] for key in ("candidate_commit", "release", "client", "installed")},
            "runtime_configuration": behavior["runtime_configuration"],
            "probe_acceptance": behavior["probe_acceptance"],
            "preparation": {
                "lineage_mode": prep["lineage_mode"], "previous_release_present": prep["previous_release_present"],
                "qualification_installed_instance_preserved":
                    any(move["kind"] == "lineage-root" and move["exists"] for move in prep["moves"]),
                "documented_stage_preserved":
                    any(move["kind"] == "documented-stage" and move["exists"] for move in prep["moves"]),
                "documented_install": "Temporary documented install and separate public-URL installer "
                                     "acceptance; the canonical root and documented stage were restored.",
                "two_gpu_host": True, "one_native_lane_at_a_time": True, "shared_port": 18082,
                "public_install_model_reference": "Manifest-bound published model; no predecessor checkpoint import.",
            },
            "observations": observations,
            "limitations": [
                "One two-GPU Windows host, native serving sequential on shared port 18082.",
                ("First-lineage route acceptance has no predecessor; rollback not_applicable, zero directions. "
                 "This is not running-lane upgrade/rollback qualification." if first else
                 "Running-lane upgrade and rollback are limited to the observed lineage."),
                "No native vision or additional runtime performance claim; component qualification remains separate."],
        }
        composer.check_native_observations(lane, observations)
        errors = []
        configuration = native_profile(root, release, variant, errors)
        require(configuration is not None and not errors, "; ".join(errors))
        errors = native_probe_acceptance_errors(configuration, behavior["probe_acceptance"], variant,
                                                 manifest["components"]["omp"]["binary_sha256"])
        require(not errors, lane + ": " + "; ".join(errors))
        restoration[lane] = {
            "status": restored["status"], "restoration_checks": restored["checks"],
            "final_audit_checks": audit["checks"], "window_hold_seconds": window["elapsed_seconds"],
            "power_limit_w": row["power_limit_w"], "public_install_restored": public["restoration"]["prior_state_restored"],
            "canonical_cross_lane_census_identical": original == final,
            "holds_and_client_files_unchanged": holds == final_holds_value,
            "documented_directory_presence_restored":
                restored["checks"]["directory_presence_identical"] and audit["checks"]["directory_presence_identical"],
            "documented_stage_restored":
                restored["checks"]["documented_stage_identical"] and audit["checks"]["documented_stage_identical"],
            "active_release": row["active_release"], "state_sha256": row["state_sha256"],
            "task_state": row["task_state"], "processes": len(final["processes"]),
            "listeners": len(final["listeners"]), "lease_entries": len(row["lease_entries"]),
            "sources": [reference(folder / "evidence/restoration.json"), reference(folder / "evidence/final-audit.json"),
                        reference(folder / "driver-window.json"), reference(folder / "public-install.json"),
                        reference(final_census)],
            "scope": "Restored the same stopped canonical root and stage; preserved lineages remain untouched.",
        }
    linux = summary["clients"]["linux"]
    evidence["composed"] = {
        "authority_status": "qualified", "public_client_downloads": {"status": "passed", "anonymous": True},
        "linux_live_client": {
            "status": linux["status"], "profile": "linux-docker-local", "omp_version": linux["omp_version"],
            "binary_sha256": client_digests["linux"],
            "scope": "Fresh stock OMP Linux x64 client under WSL2; no separate native Linux OS or Linux vision claim.",
            "structured_stream_audit": linux["full_stream_audit"], "fail_closed": linux["live_acceptance"]["fail_closed"]},
        "mode": "Fresh candidate-bound route acceptance; native lanes and "
                "the same incumbent production container restored.",
        "client_note": "Every stock OMP client was freshly downloaded and accepted "
                       "against the candidate-bound selected runtime identities.",
        "vision_scope": {LABELS[label]: {
            "status": "passed", "input_image_records": summary["clients"][label]["full_stream_audit"]["vision"]["input_image_records"],
            "input_sha256": summary["clients"][label]["live_acceptance"]["vision_input_sha256"]}
            for label in ("mac", "windows")},
        "runtime_qualification": {
            "rtx5090-container": {"status": "passed",
                "repository_path": f"releases/{release}/qualification/rtx5090.json",
                "scope": "Selected component qualification; fresh acceptance additionally binds runtime identity."},
            **{lane + "-windows-native": {"status": "passed",
                "repository_path": f"releases/{release}/qualification/{lane}.json",
                "scope": "Selected component qualification; fresh route/public-install/probe acceptance "
                         "and restored canonical instance."} for lane in sorted(native)}},
        "qualification_note": "Fresh five-route execution and candidate-profile native probes passed, "
            "with independent restoration and final audits. Exact stock client and current runtime/configuration/model "
            "identities were observed. Council binding, final immutable pins, strict ready verification and "
            "publication remain separate gates.",
        "limitations": [
            "Owner-operated tester-equivalent, not independent external-user outcomes.",
            "macOS arm64 manual SSH preview; Linux x64 evidence is WSL2-scoped.",
            "Native first-release route acceptance does not claim running-lane upgrade/rollback; component qualification is separate.",
            "Image input covers macOS and Windows against RTX 5090 only; no native or Linux vision claim.",
            "Independent post-window observation verifies the same incumbent container and its restart policy; infrastructure controls remain private."],
    }
    evidence["composed"]["vision_scope"].update({
        "linux-docker-local": "Not exercised; no Linux vision claim.",
        **{lane + "-native": "No native vision claim." for lane in native}})
    for lane in corrected:
        evidence["composed"]["limitations"].append(
            f"{lane}: an explicitly selected corrected attempt followed a failed, restored window.")
    for lane in waivers:
        disclosure = f"{lane}-native: documented blocks passed; the failed native campaign is founder-waived. " + composer.NATIVE_WAIVER_NON_CLAIM + "."
        evidence["documented_routes"]["scope"] += " " + disclosure
        evidence["composed"]["qualification_note"] = "Documented routes and stock clients passed. " + disclosure
        evidence["composed"]["limitations"].append(disclosure)
        evidence["composed"]["runtime_qualification"][lane + "-windows-native"]["scope"] = (
            "Selected component qualification is separate from the failed, founder-waived native campaign.")
    for lane, path in routes.items():
        composer.check_route(lane, load(path), candidate)
    predecessors = [load(path) for path in (root / "releases").glob("*/manifest.json")]
    previous = [item for item in predecessors if item.get("status") == "ready"
                and composer.ga_release(item.get("release"))
                and composer.product_version(item["release"]) < composer.product_version(release)]
    require(previous, "restoration needs a ready predecessor")
    incumbent = max(previous, key=lambda item: composer.product_version(item["release"]))
    composer.check_restoration(restoration, tuple(routes), candidate,
                               incumbent["components"]["ninfer"]["oci_manifest_digest"],
                               {lane + "-native": evidence[lane] for lane in waivers})
    return evidence, routes


def write_evidence(root: Path, release: str, candidate: str, window_root: Path, plan: dict,
                   output: Path, *, receipts_dir: Path | None = None, **kwargs) -> dict:
    evidence, sources = collect(root, release, candidate, window_root, plan, **kwargs)
    receipts_dir = receipts_dir or output.parent / "receipts"
    receipts = {lane: receipts_dir / (lane + "-run.json") for lane in sources}
    pending = [(receipts[lane], path.read_bytes()) for lane, path in sources.items()]
    payload = json.dumps(evidence, indent=2) + "\n"
    for path, data in pending:
        atomic_write(path, data)
    atomic_write(output, payload)
    return {"evidence": str(output.resolve()),
            "routes": {lane: str(path.resolve()) for lane, path in receipts.items()}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--window-root", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--receipts-dir", type=Path)
    parser.add_argument("--lane-dir", action="append", default=[], metavar="LANE=DIR")
    parser.add_argument("--corrected-attempt", action="append", default=[], metavar="LANE=PRIOR_DIR")
    parser.add_argument("--native-route-waiver", action="append", default=[], metavar="LANE=FILE")
    parser.add_argument("--lead-restoration", action="append", default=[], metavar="LANE=FILE")
    parser.add_argument("--lead-restoration-proof", action="append", default=[], metavar="LANE=FILE")
    parser.add_argument("--final-census", type=Path, help="explicit post-recovery native census")
    parser.add_argument("--final-holds-client", type=Path, help="explicit post-recovery client census")
    args = parser.parse_args()
    print(json.dumps(write_evidence(
        ROOT, args.release, args.candidate, args.window_root, load(args.plan), args.output,
        receipts_dir=args.receipts_dir, lane_dirs=pairs(args.lane_dir, "lane directory"),
        corrected=pairs(args.corrected_attempt, "corrected attempt"),
        waivers=pairs(args.native_route_waiver, "native waiver", allowed=LANES[1:]),
        recoveries=pairs(args.lead_restoration, "lead restoration", allowed=LANES[1:]),
        recovery_proofs=pairs(args.lead_restoration_proof, "lead restoration proof", allowed=LANES[1:]),
        final_census=args.final_census, final_holds=args.final_holds_client)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
