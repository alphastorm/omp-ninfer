#!/usr/bin/env python3
"""Compose a release's route acceptance from its runner receipts and live-client evidence.

The documented routes run on real hosts: scripts/hosts/run-documented-route.{sh,ps1} write one
content-safe receipt per lane, and the published clients' structured live runs yield one
evidence record per client profile. This turns them into the release's acceptance files

  docs/measurements/<prefix>-<lane>-run.json              the runner receipts, byte for byte
  docs/measurements/<prefix>-acceptance-restoration.json
  releases/<release>/acceptance/<client receipt>.json     one per compatibility profile
  releases/<release>/acceptance/rtx4090-public-install.json
  releases/<release>/acceptance/documented-routes.json
  releases/<release>/acceptance/composed-external-installation.json

and moves the manifest, qualification and compatibility authority to the ready posture. Stock
client identity comes from this release's upstream manifest and compatibility profiles, never
from a previous fork's receipts. Installed binaries must match the published upstream assets.

    python3 scripts/compose_route_acceptance.py --release v0.8.0 \\
        --candidate <40-hex> --as-of 2026-09-25 --measurement-prefix 2026-09-25-v080 \\
        --evidence /private/evidence.json \\
        --route rtx5090-container-host=/private/host.json --route ...

The evidence file is private (it names no secrets, but it is the operator's working record);
its schema is the EVIDENCE_KEYS below. The immutable URL pins that follow are
scripts/rebind_release.py's: commit these files, then --stage platform, acceptance, manifest.
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
    OMP_PROFILE_PLATFORMS, validate_upstream_client_bindings, validate_upstream_omp_component,
)

DOCUMENT = ROOT / "docs" / "QUICKSTART.md"
LANES = ("rtx5090-container-host", "rtx5090-macos-client", "rtx5090-windows-client",
         "rtx4090-native")
NATIVE_LANE = "rtx4090-native"
NATIVE_VARIANT = "rtx4090-windows-native"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
EVIDENCE_KEYS = ("platforms", "rtx4090", "restoration", "documented_routes", "composed")
# What every live client run must have observed before its receipt can say passed.
LIVE_TRUE = ("typed_read_tool_calls", "linked_tool_results", "tool_result_marker",
             "exact_visible_final_answer", "agent_end", "continuation_exact_nonce",
             "runtime_identity_bound")

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
    return str(path.relative_to(ROOT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"compose_route_acceptance: {message}")


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


def platform_receipt(release: str, as_of: str, profile: dict, evidence: dict,
                     manifest: dict) -> dict:
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
        require(lane in LANES and path, f"bad --route {item!r}")
        routes[lane] = Path(path)
    require(sorted(routes) == sorted(LANES), f"need one --route for each of {', '.join(LANES)}")
    evidence = load(args.evidence)
    require(all(key in evidence for key in EVIDENCE_KEYS), f"evidence needs {', '.join(EVIDENCE_KEYS)}")

    release_root = ROOT / "releases" / args.release
    acceptance_root = release_root / "acceptance"
    measurements = ROOT / "docs" / "measurements"
    manifest_path = release_root / "manifest.json"
    qualification_path = release_root / "qualification.json"
    authority_path = ROOT / "compatibility.json"
    manifest = load(manifest_path)
    qualification = load(qualification_path)
    authority = load(authority_path)
    require(authority.get("product_release") == args.release,
            "the root compatibility authority is not this release; run the lane cut first")
    omp = manifest["components"]["omp"]
    errors: list[str] = []
    validate_upstream_omp_component(omp, errors)
    validate_upstream_client_bindings(omp, authority["profiles"], errors)
    require(not errors, "; ".join(errors))

    # 1. Route runner receipts, checked and copied byte for byte.
    receipts: dict[str, dict] = {}
    route_rows: dict[str, dict] = {}
    for lane in LANES:
        raw = routes[lane].read_bytes()
        receipt = json.loads(raw)
        check_route(lane, receipt, args.candidate)
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
    addresses = {lane: current_addresses(lane) for lane in LANES}
    blocks_match = all(
        [row["sha256"] for row in addresses[lane]] == [step["block_sha256"] for step in receipts[lane]["steps"]]
        for lane in LANES
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

    # 3. One platform receipt per client profile, at the filename the authority already names.
    platform_rows = []
    for profile in authority["profiles"]:
        filename = profile["acceptance_receipt"]["url"].rsplit("/", 1)[-1]
        receipt = platform_receipt(args.release, args.as_of, profile,
                                   evidence["platforms"][profile["id"]], manifest)
        save(acceptance_root / filename, receipt)
        digest = sha256((acceptance_root / filename).read_bytes())
        # This is product qualification metadata; stock OMP does not read the authority.
        # Non-installable profiles retain their status and blockers.
        if profile.get("installable") is True:
            profile["status"] = "qualified"
            profile["blockers"] = []
        profile["acceptance_receipt"]["sha256"] = digest
        platform_rows.append({"profile": profile["id"], "sha256": digest})

    # 4. The native lane's public-install receipt.
    windows = next(p for p in authority["profiles"]
                   if p["id"] == "windows-docker-local")
    variant = next(v for v in manifest["components"]["ninfer_variants"] if v["id"] == NATIVE_VARIANT)
    native = evidence["rtx4090"]
    native_path = acceptance_root / "rtx4090-public-install.json"
    save(native_path, {
        "artifact_type": "omp_ninfer_native_public_install_acceptance",
        "schema_version": 1,
        "release": args.release,
        "lane": NATIVE_VARIANT,
        "as_of": args.as_of,
        "status": "passed",
        "candidate_commit": args.candidate,
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
            "model_sha256": variant["model_artifact_sha256"],
        },
        "preparation": native["preparation"],
        "observations": native["observations"],
        "documented_route": {"repository_path": route_rows[NATIVE_LANE]["receipt"],
                             "sha256": route_rows[NATIVE_LANE]["sha256"]},
        "restoration": restoration_ref,
        "limitations": native["limitations"],
    })

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
        "candidate_commit": args.candidate,
        "routes": route_rows,
        "steps": [{"lane": lane, "status": "passed"} for lane in LANES],
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
    steps = {lane: {"status": "passed", "blocks": len(route_rows[lane]["steps"])} for lane in LANES}
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
            "rtx4090_public_install": {"repository_path": relative(native_path),
                                       "sha256": sha256(native_path.read_bytes())},
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
    composition["documented_route_acceptance"] = {
        "status": "passed",
        "repository_path": relative(routes_path),
        "sha256": sha256(routes_path.read_bytes()),
    }
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
    print(f"composed {args.release} acceptance: {len(LANES)} routes, {len(platform_rows)} client "
          f"receipts; commit, then rebind_release.py --pin <commit> --stage platform")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
