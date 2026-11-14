"""Host-free acceptance inputs for composer tests and disposable release rehearsals.

These are synthetic observations, never real qualification evidence. The ``write`` command
requires an already-staged release and its full candidate commit in the current tree.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "acceptance_fixture_composer", ROOT / "scripts" / "compose_route_acceptance.py")
assert SPEC and SPEC.loader
COMPOSER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = COMPOSER
SPEC.loader.exec_module(COMPOSER)
HISTORY_SPEC = importlib.util.spec_from_file_location(
    "acceptance_fixture_history", ROOT / "tests" / "history.py")
assert HISTORY_SPEC and HISTORY_SPEC.loader
HISTORY = importlib.util.module_from_spec(HISTORY_SPEC)
sys.modules[HISTORY_SPEC.name] = HISTORY
HISTORY_SPEC.loader.exec_module(HISTORY)
from release_io import atomic_write_json, git

# v0.7.4's accepted posture: the macOS SSH profile stays preview, the Docker-local ones install.
ACCEPTED = {"darwin-remote-ssh": "preview", "windows-docker-local": "qualified",
            "linux-docker-local": "qualified"}
FIXTURE_LIMITATIONS = ("Acceptance covers only the documented routes and recorded client operations.",)

DESCRIPTOR = json.loads(
    (ROOT / "tests" / "fixtures" / "upstream-omp-component.json").read_text(encoding="utf-8")
)
CANDIDATE = "1" * 40
UPSTREAM = {"distribution_kind": "upstream-release",
            "upstream_repository": "https://github.com/can1357/oh-my-pi",
            "upstream_tag": DESCRIPTOR["omp"]["upstream_tag"],
            "upstream_commit": "5" * 40, "release_id": 42}


def client_distribution(platform: str, digest: str = "8" * 64) -> dict:
    asset = f"omp-{platform}" + (".exe" if platform == "windows-x64" else "")
    return {**UPSTREAM, "os": platform.split("-")[0], "architecture": platform.rsplit("-", 1)[1],
            "published": True, "asset_name": asset, "asset_bytes": 123, "asset_id": 43,
            "asset_url": f"{UPSTREAM['upstream_repository']}/releases/download/{UPSTREAM['upstream_tag']}/{asset}",
            "asset_sha256": digest, "binary_sha256": digest}


WINDOWS = client_distribution("windows-x64")
MANIFEST = {
    "components": {
        "omp": {**UPSTREAM, "upstream_tree": "6" * 40,
                "distribution_version": DESCRIPTOR["omp"]["distribution_version"],
                "platform": "windows-x64", "artifact_name": WINDOWS["asset_name"],
                "artifact_url": WINDOWS["asset_url"], "artifact_bytes": WINDOWS["asset_bytes"],
                "artifact_release_id": 42, "artifact_asset_id": 43, "artifact_published": True,
                "artifact_sha256": WINDOWS["asset_sha256"], "binary_sha256": WINDOWS["binary_sha256"],
                "compatibility_authority": "https://example.invalid/compatibility.json"},
        "ninfer": {"release_tag": "v9.9.9-qwen38-5090-beta.1", "source_commit": "4" * 40,
                   "oci_manifest_digest": "sha256:" + "a" * 64, "server_binary_sha256": "b" * 64},
        "model": {"artifact_sha256": "c" * 64},
    },
    "runtime_identity": {"configuration_sha256": "d" * 64},
}
LIVE = {
    "omp_version": f"omp/{DESCRIPTOR['omp']['distribution_version']}",
    "event_counts": {"tool_execution_start": 1, "tool_execution_end": 1},
    "typed_read_tool_calls": 1,
    "linked_tool_results": 1,
    "tool_result_marker": True,
    "exact_visible_final_answer": True,
    "agent_end": True,
    "continuation_exact_nonce": True,
    "runtime_identity_bound": True,
    "raw_transcript_included": False,
    "runtime_image_digest": "sha256:" + "a" * 64,
    "runtime_server_binary_sha256": "b" * 64,
    "runtime_configuration_sha256": "d" * 64,
    "model_sha256": "c" * 64,
    "fail_closed": {"exit_code": 1, "no_model_response": True,
                    "only_selected_local_provider_observed": True},
}
# v0.14.0's restoration evidence: its receipt without the fields the composer writes itself.
RESTORATION = {key: value for key, value in json.loads(
    (ROOT / "docs/measurements/2026-10-28-v0140-acceptance-restoration.json").read_text(encoding="utf-8")
).items() if key not in ("artifact_type", "schema_version", "release", "as_of", "status",
                         "production_upgrade_activated",
                         "raw_private_paths_credentials_or_outputs_included")}
RESTORATION["candidate_commit"] = CANDIDATE
FIRST_RELEASE = {"rollback": {"status": "not_applicable", "directions": 0,
                              "reason": "first release of the lineage"}}
# The route-acceptance summary v0.14.0's staging left for composition to replace.
STAGED_ROUTE_ACCEPTANCE = {
    "status": "pending",
    "fresh_product_acceptance": False,
    "scope": "Fresh candidate-bound external-install acceptance of all five routes, stock clients "
             "and both native public installs is required. Every route must be accepted fresh.",
    "document_change": "Published QUICKSTART blocks remain on v0.13.1 at this stage.",
}


def native_evidence(gpu: str) -> dict:
    """v0.14.0's first-of-lineage public-install evidence for one native lane."""
    receipt = json.loads((ROOT / f"releases/v0.14.0/acceptance/{gpu}-public-install.json")
                         .read_text(encoding="utf-8"))
    return {key: receipt[key] for key in ("preparation", "observations", "limitations")}



def route_receipt(lane: str) -> dict:
    steps = [
        {"slug": step.slug, "status": "passed", "block_sha256": "e" * 64, "executed_sha256": "e" * 64,
         "elapsed_seconds": 1.0}
        for step in COMPOSER.documented_route.LANES[lane]
    ]
    return {"artifact_type": "omp_ninfer_documented_route_run", "lane": lane, "status": "passed",
            "clone_commit": CANDIDATE, "document_sha256": "f" * 64, "steps": steps}


def campaign_waiver(release: str, candidate: str, route_sha256: str,
                    *, failed_phase: str = "structured-outage") -> dict:
    waiver = {
        "artifact_type": "omp_ninfer_founder_gate_waiver", "schema_version": 1,
        "release": release, "candidate": candidate, "lane": "rtx3090-native",
        "status": "waived-by-founder", "observed_status": "failed",
        "documented_route_status": "passed", "failed_phase": "structured-outage",
        "observed_summary": {
            "action": "Control-Release.ps1 -Action Stop after structured live and native probes",
            "outcome": "graceful_incomplete_shutdown", "sessions_saved": 1, "sessions_skipped": 8,
            "sessions_refused": 1, "shutdown_complete": False,
            "final_durable_save_reason": "capacity", "reclaimed_host_bytes": 0},
        "restoration_summary": {
            "status": "restored-by-lead", "outcome": "graceful", "sessions_refused": 0,
            "runtime_record_absent": True, "gpu_owner_lease_absent": True, "power_limit_w": 370,
            "all_native_tasks_ready": True, "server_processes": 0, "port_18082_listeners": 0},
        "provenance": {"source_sha256": "7" * 64},
        "evidence_sha256": {"documented-route.json": route_sha256,
                            "window-failure.json": "8" * 64, "driver-window.json": "9" * 64,
                            "lead-restoration.out": "a" * 64, "pre-window-census.json": "b" * 64},
    }
    if failed_phase == "native-probes":
        waiver["failed_phase"] = failed_phase
        waiver["observed_summary"] = {
            "probe": "compaction", "error": "RuntimeError: timed out after 900 s",
            "timeout_seconds": 900, "http_status_counts": {"503": 8, "499": 2},
            "managed_stop": {**waiver["observed_summary"], "sessions_refused": 3},
        }
        waiver["evidence_sha256"]["compaction-probe.json"] = "c" * 64
        waiver["probe_projection_sha256"] = {"compaction": "d" * 64}
    return waiver


def waived_campaign_evidence(waiver: dict) -> dict:
    """Content-safe collector projections retain their original private source digests."""
    return {
        "window_failure": {"evidence_name": "rtx3090/evidence/window-failure.json",
                           "sha256": waiver["evidence_sha256"]["window-failure.json"],
                           "boundary": waiver["failed_phase"],
                           "observed_summary": deepcopy(waiver["observed_summary"])},
        "stopped_owner_census": {"evidence_name": "native-pre-window-census.json",
                                 "sha256": waiver["evidence_sha256"]["pre-window-census.json"],
                                 "lane": "rtx3090", "power_limit_w": 370},
    }


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def subprocess_environment(root: Path) -> dict[str, str]:
    """Give child interpreters their own test import root, not the caller's Python path."""
    return {**os.environ, "PYTHONPATH": str(root / "tests")}


def predecessor(root: Path, release: str | None = None) -> dict:
    """Latest ready GA predecessor, optionally bounded by an already-selected successor."""
    version = COMPOSER.product_version(release) if release is not None else None
    manifests = [load(path) for path in (root / "releases").glob("*/manifest.json")]
    ready = [item for item in manifests if item.get("status") == "ready"
             and COMPOSER.ga_release(item["release"])
             and (version is None or COMPOSER.product_version(item["release"]) < version)]
    if not ready:
        raise ValueError("a staged successor needs a ready predecessor")
    return max(ready, key=lambda item: COMPOSER.product_version(item["release"]))


def public_release_tree(root: Path, release: str, destination: Path) -> str:
    """Materialize the public tag's exact tree and history, never the current authority."""
    (commit,) = HISTORY.resolve_commits(f"refs/tags/{release}", root=root)
    subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", "--no-checkout",
                    str(root), str(destination)], check=True, capture_output=True,
                   env=subprocess_environment(root))
    git(destination, "checkout", "--quiet", "--detach", commit)
    return commit


def fixture_evidence(root: Path, release: str, candidate: str) -> tuple[dict, dict]:
    """Bind synthetic observations to the staged manifest without editing that manifest."""
    from test_native_candidate_policy import probe_receipts
    from compose_native_qualification import native_probe_summary
    from verify_release import native_profile

    manifest = load(root / "releases" / release / "manifest.json")
    authority = load(root / "compatibility.json")
    if authority["product_release"] != release:
        raise ValueError("the staged successor must be lane-pinned before fixtures are written")
    previous = predecessor(root, release)
    plan_path = root / "releases" / release / "plan.json"
    statuses = (load(plan_path)["platforms"] if plan_path.is_file() else {
        profile["id"]: (profile["status"] if profile.get("status") in ("qualified", "preview")
                        else ACCEPTED[profile["id"]]) for profile in authority["profiles"]})
    omp = manifest["components"]["omp"]
    client = {"version": f"omp/{omp['distribution_version']}", "binary_sha256": omp["binary_sha256"]}
    live = deepcopy(LIVE)
    live.update(omp_version=client["version"],
                runtime_image_digest=manifest["components"]["ninfer"]["oci_manifest_digest"],
                runtime_server_binary_sha256=manifest["components"]["ninfer"]["server_binary_sha256"],
                runtime_configuration_sha256=manifest["runtime_identity"]["configuration_sha256"],
                model_sha256=manifest["components"]["model"]["artifact_sha256"])
    restoration = {
        "candidate_commit": candidate,
        "rtx5090": {**{key: True for key in COMPOSER.INCUMBENT_RESTORED},
                    "original_image": "ghcr.io/alphastorm/ninfer-runtime@"
                    + previous["components"]["ninfer"]["oci_manifest_digest"],
                    "restart_policy": "unless-stopped", "window_hold_seconds": [1.0]},
    }
    evidence = {
        "platforms": {profile["id"]: {
            "status": statuses[profile["id"]], "candidate": candidate, "release": release,
            "binary_sha256": profile["client_distribution"]["binary_sha256"],
            "live_acceptance": deepcopy(live), "limitations": [],
        } for profile in authority["profiles"]},
        "restoration": restoration,
        "documented_routes": {
            "mode": "offline-fixture", "qualification_environment": {},
            "scope": "Fresh candidate-bound route, client and public-install observations.",
        },
        "composed": {
            "mode": "offline-fixture", "authority_status": "qualified",
            "public_client_downloads": {"status": "passed", "anonymous": True},
            "linux_live_client": {"status": "passed"}, "client_note": "Stock binary acceptance.",
            "vision_scope": ["darwin-remote-ssh", "windows-docker-local"],
            "runtime_qualification": {}, "limitations": [], "qualification_note": "Observed.",
        },
    }
    document = root / "docs/QUICKSTART.md"
    routes = {}
    native = {row["id"].split("-")[0]: row
              for row in manifest["components"].get("ninfer_variants", [])}
    for lane in (*COMPOSER.LANES, *(name + "-native" for name in native)):
        receipt = route_receipt(lane)
        receipt.update(clone_commit=candidate,
                       document_sha256=COMPOSER.sha256(document.read_bytes()))
        for step, (_, block) in zip(receipt["steps"], COMPOSER.documented_route.lane_blocks(document, lane)):
            step["block_sha256"] = step["executed_sha256"] = block.sha256
        routes[lane] = receipt
    for lane, variant in native.items():
        errors = []
        configuration = native_profile(root, release, variant, errors)
        if errors or configuration is None:
            raise ValueError("; ".join(errors))
        installed = {"source_commit": variant["source_commit"],
                     "package_sha256": variant["package_sha256"],
                     "binary_sha256": variant["server_binary_sha256"],
                     "config_sha256": variant["configuration_sha256"]}
        body = native_evidence(lane)
        body.update(candidate_commit=candidate, release=release, client=deepcopy(client),
                    installed=deepcopy(installed), runtime_configuration=configuration)
        probes = probe_receipts(variant, configuration)
        if "build_profile" in variant:
            def bind_profile(value):
                if isinstance(value, dict):
                    if {"binary_sha256", "config_sha256", "model_artifact_sha256"} <= value.keys():
                        value["build_profile"] = variant["build_profile"]
                    for child in value.values():
                        bind_profile(child)
                elif isinstance(value, list):
                    for child in value:
                        bind_profile(child)
            bind_profile(probes)
        for name in ("parallel", "compaction"):
            if name in probes:
                probes[name]["omp"] = {"version": client["version"], "sha256": client["binary_sha256"]}
        body["probe_acceptance"] = native_probe_summary(probes)
        observed = body["observations"]
        observed["structured_client"]["omp_version"] = client["version"]
        public = observed["public_install"]
        public["source"] = {"product_release": release, "candidate_commit": candidate}
        public["client"] = deepcopy(client)
        public["installed"].update(installed, server_binary_sha256=variant["server_binary_sha256"],
                                   configuration_sha256=variant["configuration_sha256"])
        public["integrity"]["assets"]["package"].update(
            sha256=variant["package_sha256"], bytes=variant["package_bytes"])
        public["install"]["package_sha256"] = variant["package_sha256"]
        routes[lane + "-native"].update(candidate_commit=candidate, release=release,
                                        client=deepcopy(client), installed=deepcopy(installed))
        evidence[lane] = body
        restoration[lane] = {
            "status": "passed", **{key: True for key in COMPOSER.NATIVE_RESTORED},
            **{key: {field: True for field in COMPOSER.AUDIT_FIELDS}
               for key in COMPOSER.NATIVE_AUDITS},
            "window_hold_seconds": 1.0, "power_limit_w": 300,
        }
    return evidence, routes


def write_reviews(out: Path, release: str, candidate: str, manifest: dict,
                  *, product_only: bool = False) -> dict:
    """A tiny closed directory set in the same wire shapes as the retained reviews."""
    source = manifest["components"]["ninfer"]["source_commit"]
    variants = manifest["components"].get("ninfer_variants", [])
    delta = variants[0]["source_commit"] if variants else source
    seat = {"reviewer_id": "critic", "selectionClass": "focused", "role": "strong_critic",
            "independence_class": "cross_family", "authority": "independent_evidence",
            "model": "synthetic", "model_family": "synthetic"}
    entries = {}
    subjects = (("product_tooling", candidate),) if product_only else (
        ("native_runtime", source), ("native_component_delta", delta), ("product_tooling", candidate))
    for key, commit in subjects:
        directory = out / "reviews" / key
        focused = key == "native_component_delta"
        subject = {"subjectCommit": commit, "subjectDigest": "1" * 64, "files": []}
        receipt = {"assignments": [seat], "subjectDigest": "2" * 64, "reviewClass": "focused"}
        if focused:
            atomic_write_json(directory / "subject.json", subject)
            atomic_write_json(directory / "receipt.json", receipt)
            from release_io import atomic_write
            atomic_write(directory / "scope.md", "# Synthetic review scope\n")
            atomic_write(directory / "dispositions.md",
                         "| ID | Seat | Severity | Result | Disposition | Rationale |\n"
                         "| --- | --- | --- | --- | --- | --- |\n"
                         "| F1 | critic | P3 | verified | accept | Synthetic evidence. |\n")
        else:
            atomic_write_json(directory / "frozen-subject.json", subject)
            atomic_write_json(directory / "panel-selection.json",
                              {"selected": [seat], "subjectDigest": "2" * 64})
            atomic_write_json(directory / "resolver-receipt.json", receipt)
            atomic_write_json(directory / "review-record.json",
                              {"review_id": directory.name, "review_sequence_id": release + "-fixture",
                               "status": "closed-by-disposition"})
            atomic_write_json(directory / "prepare-input.json", {"subject": {"base": commit}})
            from release_io import atomic_write
            atomic_write(directory / "close-report.md", "# Closed synthetic review\n")
            atomic_write(directory / "ledger.md",
                         "| Finding | Seat | Evidence | Severity | Subject | Claim | Result | Disposition | Change | Rationale |\n"
                         "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
                         "| F1 | critic | receipt | P3 | fixture | synthetic | verified | accept | none | Synthetic evidence. |\n")
        atomic_write_json(directory / "critic.json",
                          {"summary": "Synthetic review only.", "evidence": [], "unresolved": []})
        entries[key] = {"directory": key, "status": "closed-by-disposition",
                        "closure": "Closed synthetic review.", "base_commit": source}
    atomic_write_json(out / "reviews/manifest.json", entries)
    values = {"as_of": "2000-01-01", "ledger_status": "closed-by-disposition",
              "approval_granted": True, "product_council": {
                  "stage_commit": candidate, "status": "closed-by-disposition",
                  "closure": "Closed synthetic review.", "scope_sentence": "Synthetic rehearsal only.",
                  "residuals_sentence": "Synthetic review findings are fully dispositioned."}}
    if not product_only:
        values["composition_review"] = {
            "native_runtime_summary": "closed with synthetic findings fully dispositioned.",
            "native_component_delta_subject": "the synthetic native delta",
            "native_component_delta_summary": "closed with synthetic findings fully dispositioned.",
        }
    atomic_write_json(out / "values.json", values)
    return entries


def write_windows(out: Path, release: str, candidate: str, evidence: dict, routes: dict) -> None:
    """Write the acceptance drivers' wire shapes, including their collection bindings."""
    timestamp = "2000-01-01T00:00:00+00:00"
    restored = evidence["restoration"]["rtx5090"]
    rr = {
        "running": True, "health": {"status": "ok"}, "same_image": True,
        "image": restored["original_image"], "restart": "unless-stopped",
        "checkpoint_mount_retained": True, "documented_key_restored": True,
        "checkout_restored": True, "beta_absent": True, "windows_release": True,
        "windows_markers_tasks_unchanged": True, "documented_directories_restored": True,
        "retained_window_created_parents": [], "windows_health": {"status": "ok"},
        "completed_utc": timestamp, "window_seconds": 1.0,
    }
    runtime = out / "rtx5090"
    clients = {}
    for label, profile in (("mac", "darwin-remote-ssh"), ("windows", "windows-docker-local"),
                           ("linux", "linux-docker-local")):
        live = deepcopy(evidence["platforms"][profile]["live_acceptance"])
        live["vision_input_sha256"] = "a" * 64
        clients[label] = {"release": release, "candidate": candidate, "status": "passed",
                          "omp_version": live["omp_version"], "live_acceptance": live,
                          "full_stream_audit": {"vision": {"input_image_records": 1}}}
    atomic_write_json(runtime / "final-summary.json", {
        "release": release, "candidate": candidate, "status": "passed",
        "completed_utc": timestamp, "clients": clients, "restoration": rr, "corrections": [],
    })
    atomic_write_json(runtime / "restoration.json", rr)
    atomic_write_json(runtime / "collection.json", {"completed_utc": timestamp, "missing": []})
    atomic_write_json(runtime / "preflight.json", {
        "release": release, "candidate": candidate, "status": "passed",
        "mac_binary_sha256": evidence["platforms"]["darwin-remote-ssh"]["binary_sha256"]})
    atomic_write_json(runtime / "windows-preflight.json", {
        "status": "passed", "candidate": candidate,
        "binary_sha256": evidence["platforms"]["windows-docker-local"]["binary_sha256"]})
    atomic_write_json(runtime / "host-preflight.json", {
        "status": "passed",
        "client_binary_sha256": evidence["platforms"]["linux-docker-local"]["binary_sha256"]})
    for lane, name in zip(COMPOSER.LANES, ("host-route.json", "mac-route.json", "windows-route.json")):
        atomic_write_json(runtime / name, routes[lane])
    atomic_write_json(out / "production-and-fleet-after.json", {
        "release": release, "candidate": candidate, "status": "passed", "same_container": True,
        "same_image": True, "health_http": 200, "restart_policy": "unless-stopped",
        "checkpoint_mounts_identical_sorted_by_destination": True,
        "fleet_phase": "Fleet", "fleet_healthy": True,
    })
    census = {"lanes": [], "processes": [], "listeners": []}
    for lane in ("rtx4090", "rtx3090"):
        if lane not in evidence:
            continue
        folder = out / lane
        body = evidence[lane]
        observed = body["observations"]
        restore = evidence["restoration"][lane]
        census["lanes"].append({
            "lane": lane, "task_state": "Ready", "lease_entries": [], "power_limit_w": 300,
            "previous_release": None, "active_release": "synthetic-runtime", "state_sha256": "1" * 64,
        })
        atomic_write_json(folder / "evidence/route.json", routes[lane + "-native"])
        atomic_write_json(folder / "evidence/behavior-evidence.json", {
            **{key: deepcopy(body[key]) for key in ("candidate_commit", "release", "client", "installed",
                                                    "runtime_configuration", "probe_acceptance")},
            "status": "passed",
            "checks": {
                "exact_tool_marker": observed["exact_tool_marker"],
                "linked_tool_history": observed["linked_tool_history"],
                "exact_continuation_nonce": observed["exact_continuation_nonce"],
                "offline_failed_without_response": observed["offline_request_failed_without_model_response"],
                "recovered_healthy": True, "served_identity_bound": True, "only_local_client_responses": True,
            },
            "request_summaries": [{"tool_call_count": observed["server_tool_calls"],
                                   "prefix_reuse_path": observed["continuation_reuse"]}],
            "local_compatibility_errors": [], "live_acceptance": observed["structured_client"],
            "documented_marker_bare_line": observed.get("documented_marker_bare_line", True),
        })
        for name, key in (("restoration.json", "restoration_checks"), ("final-audit.json", "final_audit_checks")):
            atomic_write_json(folder / "evidence" / name, {"status": "passed", "checks": restore[key]})
        atomic_write_json(folder / "evidence/preparation.json", {
            "release": release, "candidate": candidate, "status": "restored", "attempt": 1,
            "lineage_mode": body["preparation"]["lineage_mode"],
            "previous_release_present": body["preparation"]["previous_release_present"],
            "moves": [{"kind": "lineage-root", "exists": True}, {"kind": "documented-stage", "exists": True}],
        })
        atomic_write_json(folder / "public-install.json", observed["public_install"])
        atomic_write_json(folder / "evidence/window.json", {
            "release": release, "candidate": candidate, "status": "passed_and_restored",
            "attempt": 1, "restoration_status": "passed", "first_failing_boundary": None, "route_exit": 0,
        })
        atomic_write_json(folder / "driver-window.json", {
            "plan": {"release": release, "candidate": candidate, "attempt": 1},
            "status": "passed_and_restored", "elapsed_seconds": 1.0,
        })
        atomic_write_json(folder / "driver-collection.json", {
            "release": release, "candidate": candidate, "status": "collected",
            **{key: COMPOSER.sha256((folder / "evidence" / name).read_bytes()) for key, name in (
                ("window_sha256", "window.json"), ("restoration_sha256", "restoration.json"),
                ("final_audit_sha256", "final-audit.json"))},
        })
    for name in ("native-pre-window-census.json", "native-final.json"):
        atomic_write_json(out / name, census)
    for name in ("native-pre-window-census-holds-client.json", "native-final-holds-client.json"):
        atomic_write_json(out / name, {"identical": True})


def write_fixtures(root: Path, release: str, candidate: str, out: Path) -> dict:
    if re.fullmatch(r"[0-9a-f]{40}", candidate) is None:
        raise ValueError("candidate must be a full commit")
    if git(root, "rev-parse", candidate + "^{commit}").strip() != candidate:
        raise ValueError("candidate must resolve to its full commit")
    git(root, "merge-base", "--is-ancestor", candidate, "HEAD")
    evidence, routes = fixture_evidence(root, release, candidate)
    write_windows(out, release, candidate, evidence, routes)
    plan = {"artifact_type": "omp_ninfer_release_plan", "schema_version": 1, "release": release,
            "platforms": {profile: row["status"] for profile, row in evidence["platforms"].items()},
            "limitations": list(FIXTURE_LIMITATIONS)}
    atomic_write_json(out / "plan.json", plan)
    from collect_route_evidence import collect
    evidence, _ = collect(root, release, candidate, out, plan)
    atomic_write_json(out / "composition-evidence.json", evidence)
    atomic_write_json(out / "restoration.json", evidence["restoration"])
    paths = {}
    for lane, receipt in routes.items():
        path = out / "receipts" / (lane + "-run.json")
        atomic_write_json(path, receipt)
        paths[lane] = str(path.resolve())
    from verify_release import unchanged_native_variant
    manifest = load(root / "releases" / release / "manifest.json")
    previous = predecessor(root, release)
    current_components, previous_components = manifest["components"], previous["components"]
    unchanged_runtime = all(current_components["ninfer"].get(key) == previous_components["ninfer"].get(key)
                            for key in ("release_tag", "source_commit", "oci_manifest_digest", "server_binary_sha256"))
    native = {row["id"]: row for row in current_components.get("ninfer_variants", [])}
    previous_native = {row["id"]: row for row in previous_components.get("ninfer_variants", [])}
    product_only = (unchanged_runtime and native.keys() == previous_native.keys()
                    and all(unchanged_native_variant(row, previous_native[name]) for name, row in native.items()))
    write_reviews(out, release, candidate, manifest, product_only=product_only)
    return {"evidence": str((out / "composition-evidence.json").resolve()), "routes": paths,
            "reviews": str((out / "reviews/manifest.json").resolve()),
            "values": str((out / "values.json").resolve()), "window_root": str(out.resolve())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    write = subparsers.add_parser("write", help="write synthetic inputs for an already-staged candidate")
    write.add_argument("--release", required=True)
    write.add_argument("--candidate", required=True)
    write.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(write_fixtures(ROOT, args.release, args.candidate, args.out)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

