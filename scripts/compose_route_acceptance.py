#!/usr/bin/env python3
"""Compose a release's route acceptance from its runner receipts and live-client evidence.

The documented routes run on real hosts: scripts/hosts/run-documented-route.{sh,ps1} write one
content-safe receipt per lane, and the published clients' structured live runs yield one
evidence record per client profile. This turns them into the release's acceptance files

  docs/measurements/<prefix>-<lane>-run.json              the runner receipts, byte for byte
  docs/measurements/<prefix>-acceptance-restoration.json
  releases/<release>/acceptance/<platform>-<version>.json  one per compatibility profile
  releases/<release>/acceptance/rtx4090-public-install.json
  releases/<release>/acceptance/documented-routes.json
  releases/<release>/acceptance/composed-external-installation.json

and moves the manifest, qualification (with the documented-route acceptance summary the ready gate
reads) and compatibility authority to the ready posture. Stock client identity comes from this
release's upstream manifest and compatibility profiles, never from a previous fork's receipts.
Installed binaries must match the published upstream assets.

    python3 scripts/compose_route_acceptance.py --release v0.8.0 \\
        --candidate <40-hex> --as-of 2026-09-25 --measurement-prefix 2026-09-25-v080 \\
        --evidence /private/evidence.json \\
        --route rtx5090-container-host=/private/host.json --route ...

The evidence file is private (it names no secrets, but it is the operator's working record);
its schema is the EVIDENCE_KEYS below, and each platforms entry names the status (qualified or
preview) its profile takes, plus the original client probe's candidate and release: upstream
staging leaves every profile pending, so this is where the
accepted posture is decided. documented_routes.scope states what the accepted routes cover.
restoration is the restoration receipt's body in v0.14.0's shape (candidate_commit, rtx5090 and
one section per accepted native lane); every displaced incumbent must be observed back in place,
or nothing is written. The immutable URL pins that follow are scripts/rebind_release.py's:
commit these files, then --stage platform, acceptance, manifest.
Before composition, qualification.observed_gates.g4_review must hash-bind this release's
review ledger; product_tooling.stage_commit is the frozen candidate every input must name.
This subject binding is not council approval or publication authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_release import (  # pyright: ignore[reportMissingImports]
    OMP_PROFILE_PLATFORMS, effective_native_model, validate_upstream_client_bindings,
    validate_upstream_omp_component, ga_release, product_version, OCI_DIGEST_RE,
    bound_file,
)
from rebind_release import RAW  # pyright: ignore[reportMissingImports]
from compose_native_qualification import first_release_rollback

DOCUMENT = ROOT / "docs" / "QUICKSTART.md"
LANES = ("rtx5090-container-host", "rtx5090-macos-client", "rtx5090-windows-client")
NATIVE_LANES = {"rtx4090-native": "rtx4090-windows-native",
                "rtx3090-native": "rtx3090-windows-native"}
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
EVIDENCE_KEYS = ("platforms", "restoration", "documented_routes", "composed")
# What every live client run must have observed before its receipt can say passed.
LIVE_TRUE = ("typed_read_tool_calls", "linked_tool_results", "tool_result_marker",
             "exact_visible_final_answer", "agent_end", "continuation_exact_nonce",
             "runtime_identity_bound")
ACCEPTED_STATUSES = ("qualified", "preview")
# The restoration receipt's own fields: evidence cannot set them, so it cannot relabel itself.
RESTORATION_RECEIPT_FIELDS = ("artifact_type", "schema_version", "release", "as_of", "status",
                              "production_upgrade_activated",
                              "raw_private_paths_credentials_or_outputs_included")
# What the displaced RTX 5090 incumbent's restoration must have observed: the same immutable image
# healthy from Windows and WSL2 with its checkpoint mount, and the route's key, checkout,
# container, hold and directories undone. Its digest and unless-stopped policy are checked apart.
INCUMBENT_RESTORED = ("original_runtime_healthy", "original_image_retained",
                      "checkpoint_mount_retained", "windows_health_ok", "wsl_health_ok",
                      "documented_route_key_restored", "original_checkout_restored",
                      "route_container_absent", "window_hold_removed",
                      "documented_directories_restored")
# What each accepted native lane's restoration must have observed, beside its two audits.
NATIVE_RESTORED = ("public_install_restored", "canonical_cross_lane_census_identical",
                   "holds_and_client_files_unchanged", "documented_directory_presence_restored",
                   "documented_stage_restored")
NATIVE_AUDITS = ("restoration_checks", "final_audit_checks")
# What a native lane's own live run must have observed before its public-install receipt can
# back the composed tool, continuation and fail-closed claims.
NATIVE_OBSERVED = ("exact_tool_marker", "linked_tool_history", "exact_continuation_nonce",
                   "offline_request_failed_without_model_response",
                   "recovery_health_and_bound_runtime_identity_passed")
OCI_IMAGE_RE = re.compile(r"^[^@\s]+@sha256:[0-9a-f]{64}$")

_spec = importlib.util.spec_from_file_location("documented_route", ROOT / "scripts" / "documented_route.py")
assert _spec and _spec.loader
documented_route = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = documented_route  # dataclasses resolve their module by name
_spec.loader.exec_module(documented_route)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"compose_route_acceptance: {message}")


def frozen_candidate(release: str, qualification: dict) -> str:
    """The hash-bound product review subject owns acceptance identity, not --candidate."""
    gate = qualification.get("observed_gates", {}).get("g4_review", {})
    path = bound_file(ROOT, gate.get("repository_path"))
    require(path is not None and path.is_relative_to((ROOT / "releases" / release).resolve())
            and sha256(path.read_bytes()) == gate.get("sha256"),
            "acceptance requires a hash-bound frozen product subject in this release")
    ledger = load(path)
    require(ledger.get("artifact_type") == "omp_ninfer_review_ledger"
            and ledger.get("release") == release,
            "the frozen product subject ledger must belong to this release")
    candidate = ledger.get("product_tooling", {}).get("stage_commit")
    require(isinstance(candidate, str) and COMMIT_RE.fullmatch(candidate) is not None,
            "the frozen product subject must name product_tooling.stage_commit")
    return candidate


def check_native_first_release(native: dict[str, Any], qualification: dict[str, Any]) -> None:
    first = first_release_rollback(qualification.get("rollback"))
    preparation = native["preparation"]
    observed = native["observations"].get("rollback", {})
    claims_first = preparation.get("lineage_mode") == "first_release" or observed.get("status") == "not_applicable"
    if first or claims_first:
        require(first and preparation.get("lineage_mode") == "first_release"
                and preparation.get("previous_release_present") is False
                and first_release_rollback(observed),
                "native first-release acceptance must prove no predecessor and preserve not_applicable rollback")


def check_route(lane: str, receipt: dict, candidate: str) -> None:
    """A route counts only when every documented block ran as bundled and passed."""
    require(receipt.get("artifact_type") == "omp_ninfer_documented_route_run",
            f"{lane}: not a documented-route runner receipt")
    require(receipt.get("lane") == lane, f"{lane}: receipt names lane {receipt.get('lane')!r}")
    require(receipt.get("status") == "passed", f"{lane}: route status is {receipt.get('status')!r}")
    expected = [step.slug for step in documented_route.LANES[lane]]
    steps = receipt.get("steps", [])
    require([step.get("slug") for step in steps] == expected,
            f"{lane}: executed steps {[s.get('slug') for s in steps]} differ from {expected}")
    for step in steps:
        # The pre-cut clone substitution is the only non-verbatim block a runner may record,
        # and it must say what it substituted.
        substituted = step.get("status") == "substituted" and bool(step.get("substitution"))
        require(step.get("status") == "passed" or substituted,
                f"{lane}/{step.get('slug')}: {step.get('status')}")
        require(step.get("executed_sha256") == step.get("block_sha256"),
                f"{lane}/{step.get('slug')}: executed bytes differ from the bundled block")
    require(receipt.get("clone_commit") == candidate,
            f"{lane}: ran from {receipt.get('clone_commit')!r}, not candidate {candidate}")


def current_addresses(lane: str) -> list[dict]:
    return [{"slug": step.slug, "heading": step.heading, "index": step.index, "sha256": block.sha256}
            for step, block in documented_route.lane_blocks(DOCUMENT, lane)]


def check_live(profile: str, live: dict, manifest: dict) -> None:
    """The live run's own observations, never an exit status, decide a client receipt."""
    for key in LIVE_TRUE:
        value = live.get(key)
        require(value is True or (isinstance(value, int) and not isinstance(value, bool) and value >= 1),
                f"{profile}: live acceptance did not observe {key}")
    counts = live.get("event_counts", {})
    require(counts.get("tool_execution_start") == 1 and counts.get("tool_execution_end") == 1,
            f"{profile}: expected exactly one tool execution, saw {counts}")
    require(live.get("raw_transcript_included") is False, f"{profile}: raw transcript included")
    ninfer = manifest["components"]["ninfer"]
    identity = {
        "runtime_image_digest": ninfer["oci_manifest_digest"],
        "runtime_server_binary_sha256": ninfer["server_binary_sha256"],
        "runtime_configuration_sha256": manifest["runtime_identity"]["configuration_sha256"],
        "model_sha256": manifest["components"]["model"]["artifact_sha256"],
    }
    for key, value in identity.items():
        require(live.get(key) == value, f"{profile}: observed {key} {live.get(key)!r}, manifest {value}")
    closed = live.get("fail_closed", {})
    require(isinstance(closed.get("exit_code"), int) and closed["exit_code"] != 0,
            f"{profile}: fail-closed request did not fail")
    require(closed.get("no_model_response") is True and closed.get("only_selected_local_provider_observed") is True,
            f"{profile}: fail-closed request reached a model or another provider")


def check_native_observations(lane: str, observations: Any) -> None:
    """A native lane's own live run, never its exit status, decides its public-install receipt."""
    require(isinstance(observations, dict), f"{lane}: native acceptance observations are missing")
    for key in NATIVE_OBSERVED:
        require(observations.get(key) is True, f"{lane}: native acceptance did not observe {key}")
    calls = observations.get("server_tool_calls")
    require(isinstance(calls, int) and not isinstance(calls, bool) and calls >= 1,
            f"{lane}: native acceptance observed no server tool call")
    require(observations.get("cloud_fallback_observed") is False,
            f"{lane}: native acceptance did not rule out cloud fallback")
    install = observations.get("public_install")
    require(isinstance(install, dict) and install.get("status") == "passed",
            f"{lane}: the native public install did not pass")


def positive_seconds(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def predecessor_image_digest(release: str) -> str:
    """Read the incumbent from the latest ready GA predecessor, never from operator evidence."""
    current = product_version(release)
    predecessors = []
    for path in (ROOT / "releases").iterdir():
        version = product_version(path.name)
        if (not path.is_dir() or not ga_release(path.name) or version is None
                or current is None or version >= current or not (path / "manifest.json").is_file()):
            continue
        manifest = load(path / "manifest.json")
        if manifest.get("status") == "ready":
            predecessors.append((version, manifest))
    require(bool(predecessors), "restoration requires a published predecessor manifest")
    predecessor = max(predecessors, key=lambda row: row[0])[1]
    digest = predecessor.get("components", {}).get("ninfer", {}).get("oci_manifest_digest")
    require(isinstance(digest, str) and OCI_DIGEST_RE.fullmatch(digest) is not None,
            "published predecessor must bind an RTX 5090 image digest")
    return digest


def check_restoration(restoration: Any, lanes: tuple[str, ...], candidate: str,
                      predecessor_digest: str) -> None:
    """Restoration counts only when it observed every incumbent the windows displaced back in place."""
    require(isinstance(restoration, dict) and bool(restoration), "restoration evidence is empty")
    overridden = sorted(set(restoration).intersection(RESTORATION_RECEIPT_FIELDS))
    require(not overridden, f"restoration evidence cannot set the receipt's own fields {overridden}")
    require(restoration.get("candidate_commit") == candidate,
            f"restoration ran for {restoration.get('candidate_commit')!r}, not candidate {candidate}")
    incumbent = restoration.get("rtx5090")
    require(isinstance(incumbent, dict), "restoration evidence needs the rtx5090 incumbent")
    for key in INCUMBENT_RESTORED:
        require(incumbent.get(key) is True, f"rtx5090 restoration did not observe {key}")
    image = incumbent.get("original_image")
    require(isinstance(image, str) and OCI_IMAGE_RE.fullmatch(image) is not None,
            "rtx5090 restoration must name the incumbent's digest-pinned image")
    require(image.rsplit("@", 1)[1] == predecessor_digest,
            "rtx5090 restored image must match the published predecessor digest")
    require(incumbent.get("restart_policy") == "unless-stopped",
            f"rtx5090 restoration left restart policy {incumbent.get('restart_policy')!r}, "
            "not unless-stopped")
    holds = incumbent.get("window_hold_seconds")
    require(isinstance(holds, list) and bool(holds) and all(positive_seconds(hold) for hold in holds),
            "rtx5090 restoration must record every production window's hold seconds")
    for lane in NATIVE_LANES:
        gpu = lane.removesuffix("-native")
        native = restoration.get(gpu)
        if lane not in lanes:
            require(native is None, f"restoration names undeclared native lane {gpu}")
            continue
        require(isinstance(native, dict) and native.get("status") == "passed",
                f"{gpu} restoration did not pass")
        for key in NATIVE_RESTORED:
            require(native.get(key) is True, f"{gpu} restoration did not observe {key}")
        for key in NATIVE_AUDITS:
            checks = native.get(key)
            require(isinstance(checks, dict) and bool(checks)
                    and all(value is True for value in checks.values()),
                    f"{gpu} restoration {key} did not all pass")
        require(positive_seconds(native.get("window_hold_seconds")),
                f"{gpu} restoration must record its window hold seconds")


def restoration_summary(restoration: dict, lanes: tuple[str, ...], path: str) -> dict:
    """The qualification's restoration line, read from the evidence check_restoration accepted."""
    natives = {lane.removesuffix("-native"): restoration[lane.removesuffix("-native")]
               for lane in lanes if lane in NATIVE_LANES}
    incumbent = restoration["rtx5090"]
    summary: dict[str, Any] = {
        "path": path,
        "status": "passed",
        # The accepted window is the last: a corrected attempt follows the restored failure.
        "driver_hold_s": incumbent["window_hold_seconds"][-1],
        "production_upgrade_activated": False,
        "documented_directory_presence_restored": incumbent["documented_directories_restored"]
        and all(native["documented_directory_presence_restored"] for native in natives.values()),
    }
    if natives:
        summary["native_documented_stage_restored"] = all(
            native["documented_stage_restored"] for native in natives.values())
        summary["native_driver_window_s"] = {gpu: native["window_hold_seconds"]
                                             for gpu, native in natives.items()}
    return summary


def platform_receipt(release: str, as_of: str, profile: dict, evidence: dict,
                     manifest: dict, candidate: str) -> dict:
    require(evidence.get("candidate") == candidate,
            f"{profile['id']}: live capture candidate must match the frozen product subject")
    require(evidence.get("release") == release,
            f"{profile['id']}: live capture release must match {release}")
    distribution = profile["client_distribution"]
    omp = manifest["components"]["omp"]
    errors: list[str] = []
    validate_upstream_omp_component(omp, errors)
    require(not errors, "; ".join(errors))
    require(distribution.get("distribution_kind") == "upstream-release",
            f"{profile['id']}: stock upstream client required")
    require(evidence.get("binary_sha256") == distribution["binary_sha256"],
            f"{profile['id']}: installed binary {evidence.get('binary_sha256')!r} is not the "
            "published client")
    check_live(profile["id"], evidence["live_acceptance"], manifest)
    require(evidence["live_acceptance"].get("omp_version") == f"omp/{omp['distribution_version']}",
            f"{profile['id']}: observed client version differs from the manifest")
    return {
        "schema_version": 1,
        "kind": "omp-ninfer-platform-acceptance-receipt",
        "receipt_id": f"{profile['id']}-{omp['upstream_commit'][:8]}-{distribution['asset_sha256'][:10]}-{release}",
        "product_release": release,
        "candidate_commit": candidate,
        "profile": profile["id"],
        "status": "passed",
        "as_of": as_of,
        "source": {"repository": omp["upstream_repository"], "tag": omp["upstream_tag"],
                   "commit": omp["upstream_commit"], "tree": omp["upstream_tree"]},
        "client": dict(distribution),
        "live_acceptance": evidence["live_acceptance"],
        "checks": {
            "new_client_asset_and_binary_identity": "passed",
            "new_client_clean_install": "passed",
            "new_client_version": "passed",
            "live_authenticated_tool_and_continuation": "passed",
            "fail_closed_route_configuration": "passed",
        },
        "safety": {
            "cloud_fallback_observed": False,
            "production_omp_activation_performed": False,
            "runtime_incumbent_restored": True,
            "private_fleet_projection_included": False,
        },
        "limitations": evidence["limitations"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--release", required=True)
    parser.add_argument("--candidate", required=True, help="40-hex commit every route ran from")
    parser.add_argument("--as-of", required=True, help="ISO date of the acceptance")
    parser.add_argument("--measurement-prefix", required=True,
                        help="docs/measurements file prefix, e.g. 2026-09-24-v074")
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--route", action="append", default=[], metavar="LANE=PATH",
                        help="runner receipt for each documented lane")
    args = parser.parse_args()
    require(COMMIT_RE.fullmatch(args.candidate) is not None, "--candidate must be a 40-hex commit")
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.as_of) is not None, "--as-of must be an ISO date")

    routes: dict[str, Path] = {}
    for item in args.route:
        lane, _, path = item.partition("=")
        require(lane in (*LANES, *NATIVE_LANES) and path, f"bad --route {item!r}")
        require(lane not in routes, f"duplicate --route {lane!r}")
        routes[lane] = Path(path)
    evidence = load(args.evidence)
    require(all(key in evidence for key in EVIDENCE_KEYS), f"evidence needs {', '.join(EVIDENCE_KEYS)}")

    release_root = ROOT / "releases" / args.release
    acceptance_root = release_root / "acceptance"
    measurements = ROOT / "docs" / "measurements"
    manifest_path = release_root / "manifest.json"
    qualification_path = release_root / "qualification.json"
    authority_path = ROOT / "compatibility.json"
    manifest = load(manifest_path)
    variant_ids = {v["id"] for v in manifest["components"].get("ninfer_variants", [])}
    lanes = LANES + tuple(lane for lane, variant in NATIVE_LANES.items() if variant in variant_ids)
    require(sorted(routes) == sorted(lanes), f"need one --route for each of {', '.join(lanes)}")
    require(not set(lanes).intersection(evidence["documented_routes"].get("deferred_routes", {})),
            "accepted routes cannot also be deferred")
    for lane in lanes:
        if lane in NATIVE_LANES:
            require(lane.removesuffix("-native") in evidence, f"evidence needs {lane.removesuffix('-native')}")
    for lane in NATIVE_LANES:
        key = lane.removesuffix("-native")
        require(key not in evidence or lane in lanes, f"undeclared native evidence: {key}")
    qualification = load(qualification_path)
    candidate = frozen_candidate(args.release, qualification)
    require(args.candidate == candidate, "--candidate does not match the frozen product subject")
    authority = load(authority_path)
    require(authority.get("product_release") == args.release,
            "the root compatibility authority is not this release; run the lane cut first")
    omp = manifest["components"]["omp"]
    errors: list[str] = []
    validate_upstream_omp_component(omp, errors)
    validate_upstream_client_bindings(omp, authority["profiles"], errors)
    require(not errors, "; ".join(errors))
    # Upstream staging leaves every profile pending, without a receipt or installability, so the
    # evidence decides each accepted status; check them all before anything is written.
    platform_receipts = {}
    for profile in authority["profiles"]:
        status = evidence["platforms"].get(profile["id"], {}).get("status")
        require(status in ACCEPTED_STATUSES,
                f"{profile['id']}: evidence must name status qualified or preview")
        require(status != "qualified"
                or profile.get("gpu_qualification", {}).get("status") == "qualified",
                f"{profile['id']}: qualified without a qualified GPU runtime")
        platform_receipts[profile["id"]] = platform_receipt(
            args.release, args.as_of, profile, evidence["platforms"][profile["id"]], manifest, candidate)
    native_model = effective_native_model(manifest)
    for variant in manifest["components"].get("ninfer_variants", []):
        require(variant.get("model_artifact_sha256") == native_model.get("artifact_sha256"),
                f"{variant['id']}: runtime model must match the effective native model")
        native = evidence[variant["id"].split("-")[0]]
        check_native_observations(variant["id"], native.get("observations"))
        lane_receipt = variant.get("qualification", {}).get("summary")
        receipt_path = ROOT / lane_receipt if lane_receipt and lane_receipt.startswith("releases/") else release_root / str(lane_receipt)
        check_native_first_release(native, load(receipt_path) if lane_receipt else {})
    # The restoration receipt and every incumbent-restored claim below rest on this evidence.
    check_restoration(evidence["restoration"], lanes, candidate,
                      predecessor_image_digest(args.release))
    scope = evidence["documented_routes"].get("scope")
    require(isinstance(scope, str) and bool(scope.strip()),
            "evidence documented_routes needs the scope the accepted routes cover")

    # 1. Route runner receipts, checked and copied byte for byte.
    receipts: dict[str, dict] = {}
    route_rows: dict[str, dict] = {}
    for lane in lanes:
        raw = routes[lane].read_bytes()
        receipt = json.loads(raw)
        check_route(lane, receipt, candidate)
        receipts[lane] = receipt
        target = measurements / f"{args.measurement_prefix}-{lane}-run.json"
        target.write_bytes(raw)
        route_rows[lane] = {
            "status": "passed",
            "steps": [step["slug"] for step in receipt["steps"]],
            "elapsed_s": round(sum(float(step["elapsed_seconds"]) for step in receipt["steps"]), 3),
            "receipt": relative(target),
            "sha256": sha256(raw),
        }
    executed_documents = {receipt["document_sha256"] for receipt in receipts.values()}
    require(len(executed_documents) == 1, f"routes ran different documents: {executed_documents}")
    executed_document = executed_documents.pop()
    addresses = {lane: current_addresses(lane) for lane in lanes}
    blocks_match = all(
        [row["sha256"] for row in addresses[lane]] == [step["block_sha256"] for step in receipts[lane]["steps"]]
        for lane in lanes
    )
    require(blocks_match, "a documented block changed after it was executed; rerun that route")
    current_document = sha256(DOCUMENT.read_bytes())

    # 2. Restoration receipt.
    restoration_path = measurements / f"{args.measurement_prefix}-acceptance-restoration.json"
    save(restoration_path, {
        "artifact_type": "omp_ninfer_acceptance_restoration",
        "schema_version": 1,
        "release": args.release,
        "as_of": args.as_of,
        "status": "passed",
        **evidence["restoration"],
        "production_upgrade_activated": False,
        "raw_private_paths_credentials_or_outputs_included": False,
    })
    restoration_ref = {"repository_path": relative(restoration_path),
                       "sha256": sha256(restoration_path.read_bytes())}

    # 3. One platform receipt per client profile, named for its platform and the client version.
    platform_rows, platform_paths = [], []
    for profile in authority["profiles"]:
        platform_evidence = evidence["platforms"][profile["id"]]
        filename = f"{OMP_PROFILE_PLATFORMS[profile['id']]}-{omp['distribution_version']}.json"
        receipt = platform_receipts[profile["id"]]
        save(acceptance_root / filename, receipt)
        digest = sha256((acceptance_root / filename).read_bytes())
        # This is product qualification metadata; stock OMP does not read the authority. The URL
        # names the candidate until rebind_release.py --stage platform pins the receipt's commit.
        status = platform_evidence["status"]
        profile.update(status=status, installable=status == "qualified", blockers=[])
        profile["acceptance_receipt"] = {
            "url": f"{RAW}/{candidate}/releases/{args.release}/acceptance/{filename}",
            "sha256": digest,
        }
        platform_rows.append({"profile": profile["id"], "sha256": digest})
        platform_paths.append(relative(acceptance_root / filename))

    # 4. The native lane's public-install receipt.
    windows = next(p for p in authority["profiles"]
                   if p["id"] == "windows-docker-local")
    native_refs: dict[str, dict] = {}
    for native_lane, native_variant in NATIVE_LANES.items():
        if native_lane not in lanes:
            continue
        gpu_lane = native_lane.removesuffix("-native")
        variant = next(v for v in manifest["components"]["ninfer_variants"] if v["id"] == native_variant)
        native = evidence[gpu_lane]
        native_path = acceptance_root / f"{gpu_lane}-public-install.json"
        save(native_path, {
            "artifact_type": "omp_ninfer_native_public_install_acceptance",
            "schema_version": 1,
            "release": args.release,
            "lane": native_variant,
            "as_of": args.as_of,
            "status": "passed",
            "candidate_commit": candidate,
            "client": {
                **windows["client_distribution"],
                "version": f"omp/{omp['distribution_version']}",
            },
            "runtime": {
                "tag": variant["release_tag"],
                "source_commit": variant["source_commit"],
                "package_bytes": variant["package_bytes"],
                "package_sha256": variant["package_sha256"],
                "binary_sha256": variant["server_binary_sha256"],
                "configuration_sha256": variant["configuration_sha256"],
                "model_sha256": native_model["artifact_sha256"],
            },
            "preparation": native["preparation"],
            "observations": native["observations"],
            "documented_route": {"repository_path": route_rows[native_lane]["receipt"],
                                 "sha256": route_rows[native_lane]["sha256"]},
            "restoration": restoration_ref,
            "limitations": native["limitations"],
        })
        native_refs[f"{gpu_lane}_public_install"] = {
            "repository_path": relative(native_path), "sha256": sha256(native_path.read_bytes())}

    # 5. The documented-route acceptance.
    routes_doc: dict[str, Any] = {
        "artifact_type": "omp_ninfer_documented_route_acceptance",
        "schema_version": 1,
        "release": args.release,
        "as_of": args.as_of,
        "status": "passed",
        "operator_class": "owner-operated tester-equivalent",
        "mode": evidence["documented_routes"]["mode"],
        "document_sha256": executed_document,
        "current_document_sha256": current_document,
        "executed_blocks_match_current": True,
    }
    if current_document != executed_document:
        change = evidence["documented_routes"].get("document_change")
        require(isinstance(change, str) and bool(change),
                "the guide changed after the routes ran; evidence must describe document_change")
        routes_doc["document_change"] = change
    routes_doc.update({
        "candidate_commit": candidate,
        "routes": route_rows,
        "steps": [{"lane": lane, "status": "passed"} for lane in lanes],
        "current_block_addresses": addresses,
        "restoration_receipt": restoration_ref,
        "deferred_routes": evidence["documented_routes"].get("deferred_routes", {}),
        "raw_prompts_outputs_or_secrets_included": False,
        "qualification_environment": evidence["documented_routes"]["qualification_environment"],
    })
    routes_path = acceptance_root / "documented-routes.json"
    save(routes_path, routes_doc)

    # 6. The composed external-installation acceptance.
    composed = evidence["composed"]
    # Hash the promoted authority, not the draft snapshot that predates these receipts.
    authority["composition"]["status"] = composed["authority_status"]
    authority["composition"]["blockers"] = []
    save(authority_path, authority)
    shutil.copy(authority_path, release_root / "compatibility.json")
    compatibility_sha = sha256(authority_path.read_bytes())
    omp["compatibility_sha256"] = compatibility_sha
    client_components = release_root / "qualification" / "client-components.json"
    save(client_components, {
        "artifact_type": "omp_ninfer_upstream_client_components",
        "schema_version": 1,
        "release": args.release,
        "omp": {key: value for key, value in omp.items()
                if key not in ("compatibility_authority", "compatibility_sha256")},
        "platforms": {OMP_PROFILE_PLATFORMS[profile["id"]]: profile["client_distribution"]
                      for profile in authority["profiles"]},
    })
    downloads = composed["public_client_downloads"]
    require(downloads.get("status") == "passed" and downloads.get("anonymous") is True,
            "public client downloads must pass without authentication")
    public_client_downloads = {
        "status": "passed", "anonymous": True, "assets": len(authority["profiles"]),
        "downloads": [{"profile": profile["id"],
                       "url": profile["client_distribution"]["asset_url"],
                       "sha256": profile["client_distribution"]["asset_sha256"]}
                      for profile in authority["profiles"]],
    }
    composed_path = acceptance_root / "composed-external-installation.json"
    steps = {lane: {"status": "passed", "blocks": len(route_rows[lane]["steps"])} for lane in lanes}
    steps = {"public_client_downloads": public_client_downloads, **steps,
             "linux_live_client": composed["linux_live_client"]}
    save(composed_path, {
        "artifact_type": "omp_ninfer_composed_external_installation",
        "schema_version": 1,
        "release": args.release,
        "as_of": args.as_of,
        "status": "passed",
        "operator_class": "owner-operated tester-equivalent",
        "mode": composed["mode"],
        "client": {
            "distribution_kind": omp["distribution_kind"],
            "component_release_tag": omp["upstream_tag"],
            "upstream_repository": omp["upstream_repository"],
            "upstream_commit": omp["upstream_commit"],
            "upstream_tree": omp["upstream_tree"],
            "note": composed["client_note"],
        },
        "compatibility_authority": omp["compatibility_authority"],
        "compatibility_sha256": compatibility_sha,
        "windows_asset_sha256": omp["artifact_sha256"],
        "windows_binary_sha256": omp["binary_sha256"],
        "platform_receipts": platform_rows,
        "steps": steps,
        "tools": True,
        "vision": True,
        "vision_scope": composed["vision_scope"],
        "stateful_resume": True,
        "fail_closed": True,
        "runtime_incumbent_restored": True,
        "runtime_qualification": composed["runtime_qualification"],
        "evidence": {
            "documented_routes": {"repository_path": relative(routes_path),
                                  "sha256": sha256(routes_path.read_bytes())},
            **native_refs,
            "restoration": restoration_ref,
            "published_client_components": {"repository_path": relative(client_components),
                                            "sha256": sha256(client_components.read_bytes())},
        },
        "limitations": composed["limitations"],
        "raw_prompts_outputs_or_secrets_included": False,
    })

    # 7. Ready posture: the authority, the qualification composition and the manifest.
    composition = qualification["composition"]
    composition["external_installation_acceptance"] = {
        "status": "passed",
        "repository_path": relative(composed_path),
        "sha256": sha256(composed_path.read_bytes()),
        "public_url": composition["external_installation_acceptance"].get("public_url"),
        "as_of": args.as_of,
        "release": args.release,
        "component_release_tag": omp["upstream_tag"],
        "tools": True,
        "vision": True,
        "stateful_resume": True,
        "fail_closed": True,
        "runtime_incumbent_restored": True,
        "windows_asset_sha256": omp["artifact_sha256"],
        "windows_binary_sha256": omp["binary_sha256"],
        "compatibility_authority": omp["compatibility_authority"],
        "compatibility_sha256": compatibility_sha,
        "platform_receipts": platform_rows,
        "note": composed["qualification_note"],
    }
    routes_ref = {"repository_path": relative(routes_path), "sha256": sha256(routes_path.read_bytes())}
    composition["documented_route_acceptance"] = {"status": "passed", **routes_ref}
    # The summary the ready gate reads replaces the pending one staging wrote, restating this
    # composition instead of waiting for a hand edit.
    summary: dict[str, Any] = {
        "status": "passed",
        "scope": scope,
        "candidate_commit": candidate,
        # Every executed block still matches the guide (refused above otherwise), so committing
        # this evidence leaves the candidate's routes unchanged.
        "evidence_commit_changes_candidate": False,
        "evidence_path": routes_ref["repository_path"],
        "evidence_sha256": routes_ref["sha256"],
    }
    if "document_change" in routes_doc:
        summary["document_change"] = routes_doc["document_change"]
    summary.update({
        # check_route required every documented step to run and pass.
        "documented_route_steps": {lane: "{0}/{0}".format(len(route_rows[lane]["steps"]))
                                   for lane in lanes},
        "platform_receipts": platform_paths,
        "fresh_product_acceptance": True,
        "restoration": restoration_summary(evidence["restoration"], lanes,
                                           restoration_ref["repository_path"]),
        "composition_run": True,
    })
    qualification["documented_route_acceptance"] = summary
    qualification["as_of"] = max(qualification["as_of"], args.as_of)
    qualification["external_installation_qualified"] = True
    qualification["remaining_release_gates"] = []
    save(qualification_path, qualification)
    manifest["qualification"]["summary_sha256"] = sha256(qualification_path.read_bytes())
    manifest["status"] = "ready"
    manifest["publication"]["blockers"] = []
    manifest["publication"]["external_installation_qualified"] = True
    manifest["qualification"]["external_installation_passed"] = True
    save(manifest_path, manifest)
    print(f"composed {args.release} acceptance: {len(lanes)} routes, {len(platform_rows)} client "
          f"receipts; commit, then rebind_release.py --pin <commit> --stage platform")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
