#!/usr/bin/env python3
"""Derive a release's component qualification from closed native bundles.

Usage: aggregate_qualification.py compose --release vX.Y.Z --plan releases/vX.Y.Z/plan.json
       --bundle LANE=DIRECTORY --runtime-publication RECORD [--asset ROLE=FILE] [--check]

The binder runs first. Decisions are release-local, hash-bound by both the plan and
qualification. Bundles keep the original chain projection and declare all retained
inputs in bundle.json. Roles: assets, speed, tails, chain_context, tooling,
incumbent_determinism, candidate_determinism, source_delta and source_history.
Directory roles bind SHA256SUMS; source_history is a portable git bundle with
refs/heads/runtime and refs/heads/native. source_delta binds those full commits,
the exact source_delta path list and serve_inputs_identical. No chain is replayed.
All outputs are validated and planned before the first release-tree write.
The ``admit`` subcommand installs decision bindings and binder inputs, projects
only the proven native rows' qualified/installable posture, and prints the
binder's complete arguments. No package or source manifest field is transcribed.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bind_native_variant as binder
import speed_gate
import verify_release as verifier
from compose_native_qualification import native_protocol_qualification_errors
from qualification_bundle import (Bundle, BundleError, IDENTITY_FIELDS, Inputs, decode,
                                  decisions as bound_decisions, dispositions, field, json_bytes, load_bundles, native_rows,
                                  public_scan, relative, require, sha)
from release_io import atomic_write, git

ARMS = ("A0", "B1", "B2", "A3")
SCENARIOS = ("running", "rollback", "repair")
COUNTS = {"arrival": 12, "mix": 51, "sibling": 5, "restore": 4, "fleet": 11}
DECISIONS = ("native_speed_decision", "native_identity_decision",
             "slow_first_request_parity_decision")
SPEED_BINDINGS = {"decision_sha256", "gate_sha256", "plan_sha256", "plan_gate_sha256"}


def speed_bytes(value: dict[str, Any]) -> bytes:
    """Keep the speed tool's established, key-sorted evidence encoding."""
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def binding(path: Path | str, data: bytes, **extra: Any) -> dict[str, Any]:
    return {**extra, "repository_path": Path(path).as_posix(), "sha256": sha(data)}


def subject(row: dict[str, Any]) -> dict[str, Any]:
    return {"source_commit": row["source_commit"], "component_tag": row["release_tag"],
            "build_profile": row["build_profile"], **{key: row[key] for key in IDENTITY_FIELDS}}


def tail_identity(row: dict[str, Any]) -> dict[str, Any]:
    return {"source_commit": row["source_commit"], "component_tag": row["component_tag"],
            "build_profile": row["variant_label"], "package_sha256": row["package_sha256"],
            "server_binary_sha256": row["server_sha256"], "configuration_sha256": row["config_sha256"],
            "model_artifact_sha256": row["model_sha256"]}


def retained(bundle: Bundle, role: str, name: str) -> Path:
    require(role in bundle.role_directories, bundle.reference_path, f"/inputs/{role}",
            "missing closed evidence directory")
    path = bundle.role_directories[role] / relative(name, bundle.reference_path, f"/inputs/{role}")
    require(path.absolute() in bundle.inputs.hashes, bundle.reference_path, f"/inputs/{role}/{name}",
            "file is not declared by the role's checksums")
    return path


def read_retained(bundle: Bundle, role: str, name: str) -> dict[str, Any]:
    return bundle.inputs.load(retained(bundle, role, name))


def terminal(bundle: Bundle, gate: str) -> dict[str, Any]:
    path = retained(bundle, "tails", f"tail-{gate}-terminal.json")
    value = bundle.inputs.load(path)
    require(value.get("status") == "passed" and value.get("all_outer_restorations_passed") is True
            and value.get("gpu") == bundle.lane[3:] and value.get("gate") == gate,
            path, "/", "failed, incomplete or unrestored terminal")
    require(tail_identity(value["identities"]["candidate"]) == subject(bundle.row),
            path, "/identities/candidate", "differs from manifest")
    return value


def same_identity_evidence(left: dict[str, Any], right: dict[str, Any]) -> bool:
    def measured(value: dict[str, Any]) -> dict[str, Any]:
        value = deepcopy(value)
        value.pop("decision_sha256", None)
        speed = value["speed_abba"]
        speed["declaration"].pop("decision", None)
        speed["plan"].pop("gate_sha256", None)
        return value
    return measured(left) == measured(right)


def derive_admission(root: Path, release: str, bundle: Bundle,
                     decisions: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return release-bound speed and identity evidence without changing the tree."""
    chain_gate = read_retained(bundle, "speed", "speed-gate-bound.json")
    chain_plan = read_retained(bundle, "speed", "speed-plan.json")
    captures = [read_retained(bundle, "speed", f"captures/{arm}.json") for arm in ARMS]
    original = read_retained(bundle, "chain_context", "native-speed-decision.json")
    require(chain_gate.get("decision") == original
            and original.get("rule") == decisions["native_speed_decision"].get("rule")
            and original.get("release") == release,
            bundle.reference_path, "/inputs/speed", "release speed rule differs from the chain rule")
    predecessor = verifier.predecessor_native_variant(root, release, bundle.row["id"])
    require(predecessor is not None, bundle.reference_path, "/lane", "missing published incumbent")
    comparator = {"binary_sha256": predecessor["server_binary_sha256"],
                  "configuration_sha256": predecessor["configuration_sha256"],
                  "build_profile": predecessor["build_profile"]}
    require(chain_gate.get("comparator") == comparator and chain_gate.get("lane") == bundle.lane,
            bundle.reference_path, "/inputs/speed", "chain comparator differs from published incumbent")
    for index, capture in enumerate(captures):
        require(capture.get("status") == "passed" and capture.get("index") == index
                and capture.get("arm") == ARMS[index][0], bundle.reference_path,
                f"/inputs/speed/{ARMS[index]}", "incomplete or unordered capture")
        # Original absolute names are provenance only. Every referenced byte must
        # also have a portable, authenticated location in this bundle.
        for expected in field(capture, "raw_input_sha256", dict, bundle.reference_path).values():
            require(expected in bundle.inputs.hashes.values(), bundle.reference_path,
                    "/inputs/speed", "capture raw input is not covered by the bundle")
    registration = read_retained(bundle, "speed", "registration.json")
    require(registration.get("final_ABBA_credit") is False
            and registration.get("case_count") == len(chain_gate["request_suite"])
            and registration.get("role_case_count") == len(chain_gate["role_case_ids"])
            and registration.get("request_sources"), bundle.reference_path, "/inputs/speed",
            "registration does not bind the complete request suite")
    for expected in registration["request_sources"].values():
        require(expected in bundle.inputs.hashes.values(), bundle.reference_path,
                "/inputs/speed", "registered request source is not bundled")
    # Validate the original result with its original, exact decision context.
    with tempfile.TemporaryDirectory(prefix="qualification-context-") as temporary:
        context = Path(temporary)
        chain_q = read_retained(bundle, "chain_context", "qualification.json")
        for name in ("native-speed-decision.json", "native-identity-decision.json"):
            source = bundle.role_directories["chain_context"] / name
            if source.is_file():
                atomic_write(context / "releases" / release / "qualification" / name,
                             bundle.inputs.read(retained(bundle, "chain_context", name)))
        atomic_write(context / "releases" / release / "qualification.json", json_bytes(chain_q))
        for edge in original.get("quality_screens", []):
            require(edge.get("lane") == bundle.lane and bundle.admission == "quality-screen.json",
                    bundle.reference_path, "/inputs/chain_context", "unexpected chain quality-screen binding")
            screen_data = bundle.inputs.read(bundle.directory / "quality-screen.json", edge.get("sha256"))
            path = relative(edge.get("repository_path"), bundle.reference_path, "/inputs/chain_context")
            require(path.as_posix().startswith(f"releases/{release}/qualification/"),
                    bundle.reference_path, "/inputs/chain_context", "chain quality screen must be release-local")
            atomic_write(context / path, screen_data)
        old = verifier.predecessor_manifest(root, release)
        atomic_write(context / "releases" / old["release"] / "manifest.json", json_bytes(old))
        candidate = {"binary_sha256": bundle.row["server_binary_sha256"],
                     "configuration_sha256": bundle.row["configuration_sha256"],
                     "build_profile": bundle.row["build_profile"]}
        require(speed_gate.prescreen(chain_gate, candidate, root=context) == chain_plan,
                bundle.reference_path, "/inputs/speed", "chain plan differs from its declaration")
        chain_speed = speed_gate.reduce(chain_gate, captures, chain_plan, root=context)
        require(chain_speed == bundle.values["speed.json"] and chain_speed["status"] == "PASS"
                and chain_speed["gate_passed"] is True, bundle.directory / "speed.json", "/",
                "chain speed re-reduction differs or failed")
        if bundle.admission == "identity-proof.json":
            original_identity = read_retained(bundle, "chain_context", "native-identity-decision.json")
            current_identity = decisions["native_identity_decision"]
            require(original_identity["rule"] == current_identity["rule"]
                    and original_identity["sealed_incumbent_determinism"][bundle.lane]
                    == current_identity["sealed_incumbent_determinism"][bundle.lane],
                    bundle.reference_path, "/inputs/chain_context", "release identity rule or seal differs")
            speed_gate.validate_identity_proof(bundle.values[bundle.admission], context, release,
                                               bundle.row, predecessor, bundle.values["release-spec.json"])
    gate = deepcopy(chain_gate)
    gate["decision"] = decisions["native_speed_decision"]
    plan = speed_gate.prescreen(gate, candidate, root=root)
    reduced = speed_gate.reduce(gate, captures, plan, root=root)
    strip = lambda value: {key: item for key, item in value.items() if key not in SPEED_BINDINGS}
    require(strip(reduced) == strip(chain_speed) and reduced["status"] == "PASS"
            and reduced["gate_passed"] is True, bundle.reference_path, "/inputs/speed",
            "release reduction changes chain measurements")
    result = {"speed": reduced}
    if bundle.admission == "identity-proof.json":
        for role in ("incumbent_determinism", "candidate_determinism"):
            retained(bundle, role, "arm.json")
            retained(bundle, role, "responses.jsonl")
        proof = speed_gate.create_identity_proof(
            gate, captures, plan, bundle.role_directories["incumbent_determinism"],
            bundle.role_directories["candidate_determinism"], bundle.values["release-spec.json"], root=root)
        require(same_identity_evidence(proof, bundle.values[bundle.admission]),
                bundle.directory / bundle.admission, "/", "release proof changes chain identity evidence")
        result["identity_proof"] = proof
    return result


def admit_outputs(root: Path, release: str, plan_path: Path, directories: dict[str, Path],
                  assets: dict[str, Path] | None = None) -> tuple[dict[Path, bytes], Inputs, dict[str, Any]]:
    """Authenticate portable inputs before the binder changes component rows."""
    require(verifier.GA_PRODUCT_RELEASE_RE.fullmatch(release), "arguments", "/release", "expected a GA release")
    inputs = Inputs()
    base = Path("releases") / release
    plan = inputs.load(plan_path)
    manifest = inputs.load(root / base / "manifest.json")
    q = inputs.load(root / base / "qualification.json")
    require(manifest.get("release") == release and manifest.get("status") == "draft"
            and manifest.get("publication", {}).get("authorized") is False,
            base / "manifest.json", "/", "admission requires an unauthorized draft")
    previous = verifier.predecessor_manifest(root, release)
    require(plan.get("artifact_type") == "omp_ninfer_release_plan"
            and plan.get("schema_version") == 1 and plan.get("release") == release
            and previous is not None and plan.get("predecessor") == previous["release"],
            plan_path, "/", "wrong release plan or predecessor")
    components = field(plan, "components", list, plan_path)
    native = [item for item in components if item.get("id") in binder.LANE_VARIANTS.values()]
    recut = [item["id"].split("-")[0] for item in native if item.get("disposition") == "recut"]
    require(len(set(recut)) == len(recut) and set(directories) == set(recut),
            plan_path, "/components", "bundle lanes must equal the plan's re-cut native lanes")
    if not recut:
        require(not assets, "arguments", "/asset", "carried lanes cannot accept external package assets")
        dispositions(root, release, manifest, plan)
        bound_decisions(inputs, root, release, plan, q)
        inputs.check()
        return {}, inputs, {"schema": 1, "lanes": {}}
    projected = deepcopy(manifest)
    rows = native_rows(projected, base / "manifest.json")
    bundles = {}
    for item in native:
        lane = item["id"].split("-")[0]
        if lane not in recut:
            continue
        directory = directories[lane]
        reference = inputs.load(directory / "bundle.json")
        declarations = field(reference, "inputs", list, directory / "bundle.json")
        asset_edges = [edge for edge in declarations if edge.get("role") == "assets"]
        require(len(asset_edges) == 1, directory / "bundle.json", "/inputs", "missing or duplicate assets role")
        checksums = directory / relative(asset_edges[0].get("path"), directory / "bundle.json", "/inputs/assets/path")
        receipt = inputs.load(checksums.parent / "package-build-receipt.json")
        spec = inputs.load(directory / "release-spec.json")
        require(lane in rows, base / "manifest.json", "/components/ninfer_variants",
                "admission requires a staged manifest row for each native lane")
        row = rows[lane]
        row.update(release_tag=item.get("release_tag"), source_commit=item.get("source_commit"),
                   package_name=receipt["package"]["filename"], package_sha256=receipt["package"]["sha256"],
                   package_bytes=receipt["package"]["bytes"], server_binary_sha256=receipt["binaries"]["server_sha256"],
                   configuration_sha256=receipt["config_sha256"], model_artifact_sha256=receipt["model_sha256"],
                   build_profile=receipt["build_profile"], runtime_shape=spec["runtime_shape"],
                   checksums_sha256=asset_edges[0].get("sha256"))
        row["maximum_context_tokens"] = inputs.load(directory / "server-config.json")["engine"]["max_context"]
        bundles[lane] = Bundle(directory, lane, row, inputs, release, assets)
    external_roles = {edge["role"] for bundle in bundles.values() for edge in bundle.reference["inputs"]
                      if edge.get("external") is True}
    require(set(assets or {}) == external_roles, "arguments", "/asset", "external asset roles differ from bundle declarations")
    dispositions(root, release, projected, plan)
    source_identity(bundles, projected, previous)
    pending = {}
    output_q = deepcopy(q)
    decision_order = {"native-speed-decision": 0, "native-identity-decision": 1,
                      "slow-first-request-parity-waiver-class": 2}
    planned_decisions = list(enumerate(field(plan, "decisions", list, plan_path)))
    for index, item in sorted(planned_decisions, key=lambda pair: decision_order.get(pair[1].get("id"), 3)):
        identifier = field(item, "id", str, plan_path, f"/decisions/{index}")
        require(re.fullmatch(r"[a-z][a-z0-9-]*", identifier), plan_path, f"/decisions/{index}/id",
                "expected a decision filename stem")
        name = identifier + ".json"
        copies = [bundle.inputs.read(retained(bundle, "decisions", name), item.get("sha256"))
                  for bundle in bundles.values()]
        require(all(data == copies[0] for data in copies), plan_path, f"/decisions/{index}",
                "lane bundles disagree on release decision bytes")
        decision = decode(copies[0], name)
        gate = next((gate for gate, edge in q["observed_gates"].items()
                     if isinstance(edge, dict) and Path(edge.get("repository_path", "")).name == name), None)
        if gate is None:
            gate = ("slow_first_request_parity_decision" if identifier == "slow-first-request-parity-waiver-class"
                    else identifier.replace("-", "_"))
        destination = base / "qualification" / name
        pending[destination] = copies[0]
        output_q["observed_gates"][gate] = binding(destination, copies[0])
        public_scan(decision, destination)
        if gate == "native_speed_decision":
            for edge in decision.get("quality_screens", []):
                lane = edge.get("lane")
                require(lane in bundles and bundles[lane].admission == "quality-screen.json",
                        name, "/quality_screens", "screen does not name a powered lane")
                path = relative(edge.get("repository_path"), name, "/quality_screens/repository_path")
                require(path.as_posix().startswith(base.as_posix() + "/qualification/"),
                        name, "/quality_screens", "screen must be release-local")
                pending[path] = inputs.read(bundles[lane].directory / "quality-screen.json", edge.get("sha256"))
    pending[base / "qualification.json"] = json_bytes(output_q)
    result = {"schema": 1, "lanes": {}}
    with tempfile.TemporaryDirectory(prefix="qualification-admission-") as temporary:
        context = Path(temporary)
        atomic_write(context / "releases" / previous["release"] / "manifest.json", json_bytes(previous))
        for path, data in pending.items():
            atomic_write(context / path, data)
        decisions = bound_decisions(inputs, context, release, plan, output_q)
        validate_decisions(context, release, projected, output_q, bundles, decisions)
        for lane in recut:
            bundle = bundles[lane]
            derived = derive_admission(context, release, bundle, decisions)
            lane_receipt = bundle.values[lane + ".json"]
            errors: list[str] = []
            verifier.validate_native_gates(lane_receipt, lane, errors, complete=True)
            verifier.validate_native_rollback(lane_receipt, lane, errors)
            require(not errors, bundle.directory / (lane + ".json"), "/", "; ".join(errors))
            for role, source_name, destination in (
                ("lane", lane + ".json", base / "qualification" / (lane + ".json")),
                ("fit", "fit.json", base / "qualification" / (bundle.row["id"] + ".fit.json")),
            ):
                pending[destination] = inputs.read(bundle.directory / source_name)
                public_scan(decode(pending[destination], destination), destination)
            speed_path = base / "qualification" / (lane + "-speed.json")
            pending[speed_path] = speed_bytes(derived["speed"])
            admission_kind = "identity-proof" if "identity_proof" in derived else "quality-screen"
            proof_path = base / "qualification" / (bundle.row["id"] + "." + admission_kind + ".json")
            pending[proof_path] = (speed_bytes(derived["identity_proof"]) if "identity_proof" in derived
                                   else inputs.read(bundle.directory / "quality-screen.json"))
            fit_path = base / "qualification" / (bundle.row["id"] + ".fit.json")
            arguments = [
                "--release", release, "--lane", lane, "--tag", bundle.row["release_tag"],
                "--checksums", str(bundle.assets / "SHA256SUMS"),
                "--receipt", str(bundle.assets / "package-build-receipt.json"),
                "--package", str(bundle.asset_paths[bundle.row["package_name"]]),
                "--" + admission_kind, str(root / proof_path), "--fit-proof", str(root / fit_path)]
            result["lanes"][lane] = {"binder_arguments": arguments}
    # Temporary validator context is no longer an input at the commit boundary.
    inputs.data = {path: data for path, data in inputs.data.items() if not path.is_relative_to(context)}
    compatibility = inputs.load(root / base / "compatibility.json")
    for lane in recut:
        actual = next(item for item in manifest["components"]["ninfer_variants"] if item["id"] == binder.LANE_VARIANTS[lane])
        mirrors = [item for item in compatibility["runtime_variants"] if item.get("id") == actual["id"]]
        require(len(mirrors) == 1, base / "compatibility.json", "/runtime_variants/" + lane,
                "missing or ambiguous native posture mirror")
        for row in (actual, mirrors[0]):
            require((row.get("status"), row.get("installable")) in (("preview", False), ("qualified", True)),
                    base / "manifest.json", "/components/ninfer_variants/" + lane,
                    "unexpected native posture")
            row.update(status="qualified", installable=True)
    pending[base / "manifest.json"] = json_bytes(manifest)
    pending[base / "compatibility.json"] = json_bytes(compatibility)
    for path, data in pending.items():
        public_scan(decode(data, path), path)
    inputs.check()
    return pending, inputs, result


def validate_decisions(root: Path, release: str, manifest: dict[str, Any],
                       qualification: dict[str, Any], bundles: dict[str, Bundle],
                       decisions: dict[str, Any]) -> None:
    require(not bundles or set(DECISIONS) <= set(decisions), f"releases/{release}/plan.json",
            "/decisions", "missing native speed, identity or parity decision")
    subjects = None
    for gate in DECISIONS if bundles else ():
        value = decisions[gate]
        current = field(value, "subjects", dict, gate)
        require(subjects is None or subjects == current, gate, "/subjects", "ambiguous decision subjects")
        subjects = current
        require(set(current.get("native", {})) == set(bundles), gate, "/subjects/native",
                "subjects must equal re-cut native lanes; carried lanes are not current subjects")
        for lane, bundle in bundles.items():
            expected = {"source_commit": bundle.row["source_commit"],
                        "candidate_component": bundle.row["release_tag"],
                        "build_profile": bundle.row["build_profile"],
                        "candidate": {key: bundle.row[key] for key in IDENTITY_FIELDS}}
            candidate = current["native"][lane]
            require(all(candidate.get(key) == item for key, item in expected.items()),
                    gate, f"/subjects/native/{lane}", "candidate differs from manifest")
            if "selection_decision" in candidate:
                selection = bundle.inputs.binding(root, candidate["selection_decision"], gate)
                require(selection.get("source_commit") == expected["source_commit"]
                        and selection.get("candidate") == expected["candidate"]
                        and selection.get("build_profile") == expected["build_profile"],
                        gate, "/subjects/native", "profile selection differs")
        component, runtime = manifest["components"]["ninfer"], qualification["runtime_identity"]
        expected_runtime = {
            "source_commit": component["source_commit"], "component": component["release_tag"],
            "image_digest": component["oci_manifest_digest"],
            "server_binary_sha256": component["server_binary_sha256"],
            "configuration_sha256": runtime["configuration_sha256"],
            "archive_sha256": component["binary_archive_sha256"],
            "model_artifact_sha256": manifest["components"]["model"]["artifact_sha256"]}
        runtime_subject = field(current, "runtime", dict, gate, "/subjects")
        require(all(runtime_subject.get(key) == item for key, item in expected_runtime.items()), gate, "/subjects/runtime",
                "runtime subject differs from manifest")
    if bundles:
        identity_lanes = {lane for lane, bundle in bundles.items() if bundle.admission == "identity-proof.json"}
        decision = decisions["native_identity_decision"]
        require(set(decision.get("lanes", [])) == identity_lanes
                and set(decision.get("sealed_incumbent_determinism", {})) == identity_lanes,
                "native-identity-decision.json", "/lanes", "identity seals must cover exactly identity-first lanes")
        powered = {lane for lane in bundles if lane not in identity_lanes}
        screens = decisions["native_speed_decision"].get("quality_screens", [])
        require(len(screens) == len(powered) and {item.get("lane") for item in screens} == powered,
                "native-speed-decision.json", "/quality_screens", "must cover exactly powered lanes")
        for edge in screens:
            bundle = bundles[edge["lane"]]
            require(edge["sha256"] == sha(bundle.inputs.read(bundle.directory / bundle.admission)),
                    bundle.reference_path, "/inputs", "decision quality screen differs")
            bundle.inputs.binding(root, edge, "native-speed-decision.json")


def deployment_policy(release: str, current: dict[str, Any], previous: dict[str, Any]) -> str:
    if current.get("deployment_profile") == previous.get("deployment_profile"):
        require(current.get("configuration_sha256") == previous.get("configuration_sha256"),
                f"releases/{release}/manifest.json", "/runtime_identity/configuration_sha256",
                "kept deployment profile changed configuration identity")
        return "keep"
    require(current.get("deployment_profile") == "qwen38-5090-" + release
            and current.get("configuration_sha256") != previous.get("configuration_sha256"),
            f"releases/{release}/manifest.json", "/runtime_identity",
            "advanced deployment profile must name this release and change configuration identity")
    return "advance"


def verify_runtime(inputs: Inputs, root: Path, release: str, manifest: dict[str, Any],
                   q: dict[str, Any], previous: dict[str, Any]) -> None:
    file = f"releases/{release}/qualification.json"
    require(q.get("artifact_type") == "omp_ninfer_release_qualification"
            and q.get("schema_version") == 1 and q.get("release") == release, file, "/", "wrong qualification")
    require(q.get("publication_authorized") is False and q.get("external_installation_qualified") is False
            and q.get("documented_route_acceptance") == {"status": "pending"}
            and q["composition"]["external_installation_acceptance"]["status"] == "pending",
            file, "/", "aggregate requires an unaccepted stage")
    if q["composition"]["review"].get("status") != "pending":
        old_q = inputs.load(root / "releases" / previous["release"] / "qualification.json")
        require(q["composition"]["review"] == old_q["composition"]["review"]
                and "g4_review" not in q["observed_gates"],
                file, "/composition/review", "stage review is neither pending nor the unchanged predecessor record")
    component, runtime = manifest["components"]["ninfer"], q["runtime_identity"]
    for qkey, mkey in (
        ("release_source_commit", "source_commit"), ("behavioral_source_commit", "source_commit"),
        ("upstream_commit", "upstream_commit"), ("release_source_archive_sha256", "source_archive_sha256"),
        ("release_server_binary_sha256", "server_binary_sha256"), ("repository", "repository"),
    ):
        require(runtime.get(qkey) == component.get(mkey), file, "/runtime_identity/" + qkey, "differs from manifest")
    require(runtime.get("model_artifact_sha256") == manifest["components"]["model"]["artifact_sha256"]
            and all(runtime.get(key) == item for key, item in manifest["runtime_identity"].items()),
            file, "/runtime_identity", "runtime model or policy differs")
    deployment_policy(release, manifest["runtime_identity"], previous["runtime_identity"])
    packaging, behavior = (q["composition"][key] for key in ("local_release_packaging", "behavioral_qualification"))
    require(packaging.get("status") == behavior.get("status") == "passed" and packaging.get("published") is True,
            file, "/composition", "runtime packaging or behavior is not passed")
    for qkey, mkey in (
        ("release_source_commit", "source_commit"), ("release_server_binary_sha256", "server_binary_sha256"),
        ("oci_manifest_digest", "oci_manifest_digest"), ("sbom_sha256", "sbom_sha256"),
        ("binary_package_sha256", "binary_archive_sha256"),
    ):
        require(packaging.get(qkey) == component.get(mkey), file,
                "/composition/local_release_packaging/" + qkey, "differs from manifest")
    receipt = inputs.binding(root, behavior, file)
    require(receipt.get("status") == "passed" and receipt["identity"]["patch_stack_sha"] == component["source_commit"]
            and receipt["identity"]["binary_sha256"] == component["server_binary_sha256"],
            file, "/composition/behavioral_qualification", "runtime receipt differs")
    for key in ("runtime_base_receipt", "publication_receipt", "artifact_authentication"):
        inputs.binding(root, packaging[key], file)
    for edge in q["observed_gates"].values():
        if isinstance(edge, dict) and "repository_path" in edge:
            inputs.binding(root, edge, file)
    if "receipt_audit" in q:
        inputs.binding(root, q["receipt_audit"], file)
    client = inputs.load(root / "releases" / release / "qualification/client-components.json")
    require(client.get("artifact_type") == "omp_ninfer_upstream_client_components"
            and client.get("schema_version") == 1 and client.get("release") == release
            and all(manifest["components"]["omp"].get(key) == item for key, item in client["omp"].items()),
            file, "/composition", "stock-client descriptor differs")


def provenance(root: Path, release: str, manifest: dict[str, Any], recut: set[str],
               plan: dict[str, Any], plan_path: Path) -> tuple[str, dict[str, str]]:
    """The verifier's generated statement and per-component clauses; never a second wording."""
    record, clauses = verifier.component_provenance_parts(root, release, manifest)
    planned = {row["id"]: row["disposition"] for row in plan["components"]}
    derived = {row["id"]: row["disposition"] for row in record["components"]}
    require(derived == planned and {name.split("-")[0] for name, value in derived.items()
                                    if value == "recut" and name != "rtx5090-container"} == set(recut),
            plan_path, "/components", "manifest-derived component provenance differs from the plan")
    return record["statement"], clauses


def plan_limitations(plan: dict[str, Any], plan_path: Path) -> list[str]:
    """Release-level limitations are authored once, in the plan; none is inherited."""
    values = field(plan, "limitations", list, plan_path)
    require(all(isinstance(value, str) and value.strip() == value and value for value in values)
            and len(set(values)) == len(values),
            plan_path, "/limitations", "expected unique non-empty sentences")
    claims = verifier.provenance_claim_errors(values, "plan.limitations")
    require(not claims, plan_path, "/limitations", "; ".join(claims))
    return values


def source_identity(bundles: dict[str, Bundle], manifest: dict[str, Any],
                    previous: dict[str, Any]) -> dict[str, Any]:
    runtime = manifest["components"]["ninfer"]
    sources = {}
    for lane, bundle in bundles.items():
        proof = bundle.evidence("source_delta")
        require(proof.get("runtime_source_commit") == runtime["source_commit"]
                and proof.get("native_source_commit") == bundle.row["source_commit"],
                bundle.reference_path, "/inputs/source_delta", "source relation differs from manifest")
        names = field(proof, "source_delta", list, bundle.reference_path)
        require(names == sorted(set(names)) and all(isinstance(name, str) for name in names),
                bundle.reference_path, "/inputs/source_delta", "source delta must be a sorted unique path list")
        history = bundle.evidence_paths.get("source_history")
        require(history is not None, bundle.reference_path, "/inputs/source_history", "missing portable source history")
        with tempfile.TemporaryDirectory(prefix="qualification-source-") as temporary:
            target = Path(temporary)
            git(target, "init", "--bare", "-q")
            git(target, "fetch", "-q", str(history), "refs/heads/runtime:refs/heads/runtime",
                "refs/heads/native:refs/heads/native")
            require(git(target, "rev-parse", "runtime").strip() == runtime["source_commit"]
                    and git(target, "rev-parse", "native").strip() == bundle.row["source_commit"],
                    bundle.reference_path, "/inputs/source_history", "history refs differ from manifest")
            git(target, "merge-base", "--is-ancestor", "runtime", "native")
            observed = sorted(git(target, "diff", "--name-only", "runtime", "native").splitlines())
        require(observed == names, bundle.reference_path, "/inputs/source_delta", "source diff differs from history")
        # Only these packaging/qualification areas can substantiate an identical
        # serving-input claim; an engine change cannot become a prose assertion.
        nonserve = all(name.startswith("tests/")
                       or name in ("packaging/windows/RELEASE_NOTES.md", "tools/qualification/qualify_native.py")
                       or re.fullmatch(r"packaging/windows/lanes/rtx(?:3090|4090)/release-spec\.json", name)
                       for name in names)
        require(proof.get("serve_inputs_identical") is nonserve,
                bundle.reference_path, "/inputs/source_delta/serve_inputs_identical", "unsupported serving-input claim")
        sources[lane] = proof
    carried = {row["id"]: {"release_tag": row["release_tag"], "source_commit": row["source_commit"],
                           "carried_from": previous["release"]}
               for lane, row in native_rows(manifest, "manifest.json").items() if lane not in bundles}
    base = {"repository": runtime["repository"]}
    distinct = {bundle.row["source_commit"] for bundle in bundles.values()}
    if len(distinct) == 1:
        proof = next(iter(sources.values()))
        base.update(source_commit=next(iter(distinct)), runtime_source_commit=runtime["source_commit"],
                    source_delta=proof["source_delta"], serve_inputs_identical=proof["serve_inputs_identical"])
    else:
        base["variants"] = {bundle.row["id"]: {"source_commit": bundle.row["source_commit"], **sources[lane]}
                            for lane, bundle in bundles.items()}
    base.update(carried_variants=carried, upstream_commit=runtime["upstream_commit"],
                model_artifact_sha256=verifier.effective_native_model(manifest)["artifact_sha256"])
    return base


def carried_entry(inputs: Inputs, root: Path, release: str, previous: dict[str, Any],
                  row: dict[str, Any], mirror: dict[str, Any], entry: dict[str, Any],
                  clause: str) -> dict[str, Any]:
    lane, pred = row["id"].split("-")[0], previous["release"]
    old = native_rows(previous, "predecessor manifest")[lane]
    expected = deepcopy(old)
    q = expected["qualification"]
    q["summary"] = f"releases/{release}/qualification/{lane}.json"
    q["public_url"] = row["qualification"]["public_url"]
    for name in ("release_spec", "server_config"):
        if name in q:
            q[name]["path"] = f"releases/{release}/profiles/{lane}/{Path(q[name]['path']).name}"
    require(row == expected, f"releases/{release}/manifest.json", "/components/ninfer_variants/" + lane,
            "carried manifest row was rebound or altered")
    old_compat = inputs.load(root / "releases" / pred / "compatibility.json")
    expected_mirror = deepcopy(next(item for item in old_compat["runtime_variants"] if item["id"] == row["id"]))
    expected_mirror["qualification_receipt"].update(path=q["summary"], sha256=q["sha256"],
                                                   url=mirror["qualification_receipt"]["url"])
    require(mirror == expected_mirror, f"releases/{release}/compatibility.json", "/runtime_variants/" + lane,
            "carried compatibility row was rebound or altered")
    for name in (f"qualification/{lane}.json", f"qualification/{row['id']}.SHA256SUMS",
                 f"profiles/{lane}/release-spec.json", f"profiles/{lane}/server-config.json"):
        require(inputs.read(root / "releases" / release / name) == inputs.read(root / "releases" / pred / name),
                f"releases/{release}/{name}", "/", "carried bytes differ from predecessor")
    old_q = inputs.load(root / "releases" / pred / "qualification.json")
    prior = old_q["composition"]["native_runtime_variants"][row["id"]]
    relocated = {**prior, "repository_path": q["summary"], "sha256": q["sha256"]}
    require({key: item for key, item in entry.items() if key != "scope"}
            == {key: item for key, item in relocated.items() if key != "scope"},
            f"releases/{release}/qualification.json", "/composition/native_runtime_variants/" + row["id"],
            "carried composition identity was altered")
    return {**relocated, "scope": clause + "; byte-identical published qualification, "
            "not fresh hardware or product-route acceptance."}


def upgrades(bundle: Bundle, release: str) -> dict[str, Any]:
    tail = terminal(bundle, "upgrades")
    scenarios = tail["details"]["scenarios"]
    require(set(scenarios) == set(SCENARIOS), bundle.reference_path, "/inputs/tails", "incomplete upgrade scenarios")
    expected_projection = {
        "status": "passed", "scenarios": {
            name: {"status": edge["receipt"]["status"], "restored": edge["receipt"]["restored"],
                   "supervisor_sha256": edge["supervisor_sha256"]} for name, edge in scenarios.items()},
        "candidate": tail["identities"]["candidate"], "incumbent": tail["identities"]["incumbent"]}
    require(bundle.values["upgrade.json"] == expected_projection, bundle.directory / "upgrade.json", "/",
            "projected upgrade differs from the retained tail")
    config_path = retained(bundle, "tails", "upgrade-config.json")
    config = bundle.inputs.load(config_path, tail["details"]["upgrade_config_sha256"])
    require(config["candidate"]["package_sha256"] == bundle.row["package_sha256"]
            and config["incumbent"]["package_sha256"] == tail["identities"]["incumbent"]["package_sha256"],
            config_path, "/", "upgrade configuration subject differs")
    rows, archives = {}, {}
    for scenario in SCENARIOS:
        edge = scenarios[scenario]
        path = retained(bundle, "tails", f"mirror/supervisor/upgrade-{scenario}/receipt.json")
        raw = bundle.inputs.load(path, edge["supervisor_sha256"])
        receipt = raw["upgrade_receipt"]
        require(raw["kind"] == "upgrade" and raw["job"] == "upgrade-" + scenario
                and raw["status"] == receipt["status"] == "passed" and receipt["scenario"] == scenario
                and receipt["restored"] is True and receipt == edge["receipt"]
                and raw["cleanup_errors"] == [] and raw["forced_containment"] is False
                and raw["before"] == raw["after"] and raw["owned_processes"] == []
                and raw["restored_power_w"] == config["owner_power_limit_w"],
                path, "/", "failed or unrestored upgrade scenario")
        seal_path = retained(bundle, "tails", f"upgrade-{scenario}.archive.json")
        seal = bundle.inputs.load(seal_path)
        require(seal.get("job") == "upgrade-" + scenario and verifier.SHA256_RE.fullmatch(seal.get("sha256", "")),
                seal_path, "/", "invalid archive seal")
        archives[scenario] = seal["sha256"]
        rows[scenario] = {
            "status": receipt["status"], "restored": receipt["restored"],
            "canonical_state_unchanged": raw["before"] == raw["after"],
            "restored_power_w": raw["restored_power_w"], "owned_process_count": len(raw["owned_processes"]),
            "forced_containment": raw["forced_containment"], "cleanup_errors": raw["cleanup_errors"],
            "supervisor_sha256": edge["supervisor_sha256"], "archive_sha256": seal["sha256"],
            "archive_seal_sha256": sha(bundle.inputs.read(seal_path))}
    return {
        "artifact_type": "omp_ninfer_native_upgrade_projection", "schema_version": 1, "release": release,
        "lane": bundle.lane, "status": "passed", "subject": subject(bundle.row),
        "incumbent": tail_identity(tail["identities"]["incumbent"]), "scenarios": rows,
        "provenance": {"evidence_name": "tail-upgrades-terminal.json",
                       "evidence_sha256": sha(bundle.inputs.read(retained(bundle, "tails", "tail-upgrades-terminal.json"))),
                       "source_commit": bundle.row["source_commit"], "evidence_archive_sha256": archives},
        "scope": f"{bundle.row['release_tag']} against {tail['identities']['incumbent']['component_tag']}; "
                 "running upgrade, forced-start rollback and interrupted-install repair. Not product-route acceptance.",
        "publication_authorized": False, "external_installation_qualified": False}


def parity(bundle: Bundle, release: str, decision_edge: dict[str, Any],
           decision: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    tail = terminal(bundle, "card")
    path = retained(bundle, "tails", "agent-verdict.json")
    raw = bundle.inputs.load(path, tail["details"]["agent_verdict_sha256"])
    comparison_path = retained(bundle, "tails", "agent-comparison.json")
    comparison = bundle.inputs.load(comparison_path)
    require(raw["rule"] == "p16-agent-parity/2" and set(raw["jobs"]) == set(comparison["jobs"]) == set(COUNTS)
            and tail["details"]["positions"] == sum(COUNTS.values()),
            path, "/", "incomplete parity verdict")
    failed, jobs = [], {}
    for name, count in COUNTS.items():
        job, authored = raw["jobs"][name], comparison["jobs"][name]
        require(job["rule"] == raw["rule"] and job["judged"] is True and job["positions"] == count
                and len(job["paired_positions"]) == len(authored["positions"]) == count
                and authored["driver_verdict"] == "PASS" and authored["driver_failures"] == [],
                path, "/jobs/" + name, "parity driver or count failure")
        require(len({str(row["position"]) for row in job["paired_positions"]}) == count
                and len({row["label"] for row in job["paired_positions"]}) == count,
                path, "/jobs/" + name, "ambiguous parity positions")
        actual = {}
        for row, original in zip(job["paired_positions"], authored["positions"]):
            require(all(row.get(key) == item for key, item in original.items()), path, "/jobs/" + name,
                    "paired values differ from comparison")
            for arm in ("incumbent", "candidate"):
                prompt, cached, ttft = (row[arm + suffix] for suffix in
                                        ("_prompt_tokens", "_cached_tokens", "_server_ttft_seconds"))
                require(type(prompt) is int and type(cached) is int and prompt >= cached >= 0,
                        path, "/jobs/" + name, "invalid prompt or cache count")
                speed_gate.positive_number(ttft, "parity TTFT")
            old = row["incumbent_server_ttft_seconds"]
            bound = old + max(0.25, old * 0.25)
            gap = ((row["candidate_cached_tokens"] - row["candidate_prompt_tokens"])
                   - (row["incumbent_cached_tokens"] - row["incumbent_prompt_tokens"]))
            reasons = []
            if gap < 0:
                reasons.append(f"cached-prompt {row['candidate_cached_tokens'] - row['candidate_prompt_tokens']} "
                               f"< incumbent {row['incumbent_cached_tokens'] - row['incumbent_prompt_tokens']}")
            if row["candidate_server_ttft_seconds"] > bound:
                reasons.append(f"ttft {row['candidate_server_ttft_seconds']:.3f}s > bound {bound:.3f}s")
            require(row["failures"] == reasons and row["passed"] is (not reasons)
                    and row["cached_prompt_gap_delta"] == gap and row["ttft_bound_seconds"] == bound,
                    path, "/jobs/" + name, "parity arithmetic or raw status differs")
            if reasons:
                actual[str(row["position"])] = reasons
                failed.append((name, row))
        require(job["failing"] == actual and job["passed"] is (not actual),
                path, "/jobs/" + name, "parity job status differs")
        jobs[name] = deepcopy(job)
    require(type(raw["passed"]) is bool and raw["passed"] is (not failed), path, "/passed", "raw status differs")
    public = {
        "artifact_type": "omp_ninfer_native_agent_parity_projection", "schema_version": 1,
        "release": release, "lane": bundle.lane, "subject": subject(bundle.row), "contract_version": 2,
        "rule": raw["rule"], "passed": raw["passed"], "raw_passed": raw["passed"], "jobs": jobs,
        "positions": 83, "passed_positions": 83 - len(failed),
        "status": "passed" if raw["passed"] else "failed-founder-waived", "waiver_applied": bool(failed),
        "provenance": {"evidence_name": "agent-verdict.json", "evidence_sha256": sha(bundle.inputs.read(path)),
                       "comparison_sha256": sha(bundle.inputs.read(comparison_path)),
                       "card_terminal_sha256": sha(bundle.inputs.read(retained(bundle, "tails", "tail-card-terminal.json")))},
        "class_decision": decision_edge, "scope": "Native card parity only; not candidate-bound product-route acceptance."}
    if not failed:
        require(bundle.values["agent-parity.json"] == raw, bundle.directory / "agent-parity.json", "/",
                "projected parity differs from the retained verdict")
        require("parity_waiver" not in tail["details"]
                and not (bundle.role_directories["tails"] / "agent-verdict-waived.json").exists(),
                path, "/", "passing parity cannot also carry a waiver application")
        return public, None
    require(len(failed) == 1, path, "/jobs", "only one observed parity failure is admitted")
    name, row = failed[0]
    require(((name == "restore" and row["position"] in (3, 4) and row["label"] == "restore_" + str(row["position"] - 3))
             or (name == "sibling" and row["position"] == 1 and row["label"] == "base"))
            and len(row["failures"]) == 1 and row["failures"][0].startswith("ttft "),
            path, "/jobs/" + name, "new or unadmitted parity failure class")
    application_path = retained(bundle, "tails", "agent-verdict-waived.json")
    accepted = bundle.inputs.load(application_path)
    require(bundle.values["agent-parity.json"] == accepted, bundle.directory / "agent-parity.json", "/",
            "projected parity differs from the retained waiver application")
    require(accepted == tail["details"].get("parity_waiver") and accepted.get("passed") is True
            and accepted.get("unwaived_passed") is False and accepted.get("gpu_replay") is False
            and accepted.get("status") == "passed-with-recorded-slow-first-request-waiver"
            and accepted.get("original_verdict_sha256") == sha(bundle.inputs.read(path))
            and accepted.get("comparison_sha256") == sha(bundle.inputs.read(comparison_path))
            and accepted.get("authority_sha256") == decision["provenance"]["source_sha256"]
            and accepted.get("identities") == tail["identities"] and len(accepted["waived"]) == 1,
            application_path, "/", "waiver is not this exact class-bound observation")
    waived = accepted["waived"][0]
    require(waived["probe"] == name and waived["position"] == row["position"] and waived["label"] == row["label"]
            and waived["failures"] == row["failures"] and all(row.get(key) == item for key, item in waived["values"].items()),
            application_path, "/waived", "waived values differ from raw failure")
    logs = sorted((bundle.role_directories["tails"] / "mirror/card-candidate" / ("candidate-" + name)).rglob("requests.jsonl"))
    require(logs, application_path, "/", "missing first-request classification logs")
    events = []
    for log in logs:
        retained(bundle, "tails", log.relative_to(bundle.role_directories["tails"]).as_posix())
        events.extend(decode(line.encode(), log) for line in bundle.inputs.read(log).decode("utf-8-sig").splitlines() if line.strip())
    done = sorted((event for event in events if event.get("event") == "request_done"),
                  key=lambda event: event["timestamp_unix_ms"])
    index = row["position"] - 1
    require(len(done) == COUNTS[name] and done[index]["server_instance_id"] == waived["server_instance_id"]
            and done[index]["timestamp_unix_ms"] == waived["request_done_unix_ms"]
            and all(event["server_instance_id"] != waived["server_instance_id"] for event in done[:index]),
            application_path, "/", "waived miss is not the first request of its server instance")
    observed = {
        "job": name, "probe": "two-restart restore" if name == "restore" else "sibling",
        "position": row["position"], "label": row["label"],
        "rule": "p16-agent-parity/2 candidate TTFT <= incumbent + max(0.25 s, 25%)",
        "bound_s": row["ttft_bound_seconds"], "excess_s": row["candidate_server_ttft_seconds"] - row["ttft_bound_seconds"],
        "first_request_of_server_instance": True}
    for arm in ("incumbent", "candidate"):
        observed.update({arm + "_ttft_s": row[arm + "_server_ttft_seconds"],
                         arm + "_prompt_tokens": row[arm + "_prompt_tokens"],
                         arm + "_cached_tokens": row[arm + "_cached_tokens"]})
    errors: list[str] = []
    verifier.validate_waived_position(observed, name, "parity waiver", errors)
    require(not errors, application_path, "/waived", "; ".join(errors))
    public["provenance"]["application_sha256"] = sha(bundle.inputs.read(application_path))
    return public, observed


def publication(inputs: Inputs, path: Path, release: str, manifest: dict[str, Any],
                bundles: dict[str, Bundle]) -> bytes:
    data = inputs.read(path)
    value = decode(data, path)
    require(value.get("artifact_type") == "omp_ninfer_native_component_publication"
            and type(value.get("schema_version")) is int and value["schema_version"] == 1
            and value.get("release") == release
            and value.get("status") == "passed" and value.get("publication_authorized_by_this_receipt") is False
            and value.get("product_publication_authorized") is False, path, "/", "publication is not authenticated")
    identity = value["identity"]
    require(identity.get("repository") == manifest["components"]["ninfer"]["repository"]
            and identity.get("upstream_commit") == manifest["components"]["ninfer"]["upstream_commit"]
            and identity.get("model_artifact_sha256") == verifier.effective_native_model(manifest)["artifact_sha256"],
            path, "/identity", "publication identity differs")
    rows = field(value, "lanes", list, path)
    require(len(rows) == len(bundles) and {row.get("lane") for row in rows} == set(bundles),
            path, "/lanes", "publication lanes must equal re-cut lanes")
    for row in rows:
        bundle = bundles[row["lane"]]
        current = bundle.row
        require(row.get("published") is True and row.get("component_tag") == current["release_tag"]
                and row.get("tag_commit") == row.get("source_commit") == current["source_commit"]
                and row.get("build_profile") == current["build_profile"]
                and row.get("public_package_executed_during_qualification") is False,
                path, "/lanes/" + bundle.lane, "uncut or stale publication subject")
        require(row.get("publication_evidence_class")
                == "anonymous-public-byte-downloads-and-matching-github-asset-digests"
                and row.get("release_url") == current["repository"] + "/releases/tag/" + current["release_tag"],
                path, "/lanes/" + bundle.lane + "/publication_evidence_class",
                "publication must record anonymous public-byte authentication")
        for timestamp in ("published_at", "authenticated_at_utc"):
            text = field(row, timestamp, str, path, "/lanes/" + bundle.lane)
            try:
                observed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError as error:
                raise BundleError(f"{path}#/lanes/{bundle.lane}/{timestamp}: invalid timestamp") from error
            require(observed.utcoffset() is not None, path, "/lanes/" + bundle.lane + "/" + timestamp,
                    "publication timestamp must include its UTC offset")
        sums = inputs.read(bundle.assets / "SHA256SUMS")
        assets = row["assets"]
        require(row.get("outer_checksums_sha256") == sha(sums) == row["checksums_asset"]["sha256"]
                and row["checksums_asset"].get("name") == "SHA256SUMS"
                and row["checksums_asset"].get("bytes") == len(sums)
                and row.get("outer_hashed_entries") == len(bundle.asset_hashes)
                and row.get("total_distribution_files") == len(bundle.asset_hashes) + 1
                and len(assets) == len(bundle.asset_hashes)
                and {item["name"]: item["sha256"] for item in assets} == bundle.asset_hashes
                and all(item["bytes"] == bundle.asset_paths[item["name"]].stat().st_size for item in assets),
                path, "/lanes/" + bundle.lane + "/assets", "published asset closure differs")
        require(row.get("actual_hardware_qualification") == {
            "repository_path": current["qualification"]["summary"], "sha256": current["qualification"]["sha256"]},
            path, "/lanes/" + bundle.lane, "publication hardware receipt differs")
    sources = {bundle.row["source_commit"] for bundle in bundles.values()}
    if len(sources) == 1:
        require(identity.get("source_commit") == next(iter(sources)), path, "/identity/source_commit",
                "publication source differs")
    public_scan(value, path)
    return data


def native_publication(inputs: Inputs, root: Path, release: str, manifest: dict[str, Any],
                       bundles: dict[str, Bundle], paths: dict[str, Path],
                       previous: dict[str, Any], q: dict[str, Any]) -> bytes:
    require(set(paths) == set(bundles), "arguments", "/native-publication",
            "publication lanes must equal re-cut native lanes")
    records = {}
    documents = []
    for lane, bundle in bundles.items():
        data = publication(inputs, paths[lane], release, manifest, {lane: bundle})
        value = decode(data, paths[lane])
        documents.append(value)
        records[lane] = value["lanes"][0]
    # Legacy aggregate trees published only the newly cut native component rows.
    # Successors carry the actual published rows, never fabricate a fresh cut.
    carry_rows = not bundles or (verifier.product_version(release) or (0, 0, 0)) >= (0, 20, 0)
    if carry_rows:
        for lane, row in native_rows(manifest, "manifest.json").items():
            if lane in records:
                continue
            candidate = previous
            while candidate is not None:
                old_q = inputs.load(root / "releases" / candidate["release"] / "qualification.json")
                edge = old_q["composition"].get("native_publication")
                if isinstance(edge, dict):
                    value = inputs.binding(root, edge, "predecessor qualification")
                    matches = [item for item in value.get("lanes", []) if item.get("lane") == lane
                               and item.get("component_tag") == row["release_tag"]
                               and item.get("source_commit") == row["source_commit"]
                               and item.get("build_profile") == row.get("build_profile")]
                    if len(matches) == 1:
                        records[lane] = matches[0]
                        documents.append(value)
                        break
                candidate = verifier.predecessor_manifest(root, candidate["release"])
            require(lane in records, "predecessor qualification", "/composition/native_publication/" + lane,
                    "carried component has no published predecessor row")
    require(documents, "native publication", "/", "no native publication evidence")
    if not carry_rows and len(documents) == 1:
        return json_bytes(documents[0])
    value = deepcopy(documents[0])
    value["release"] = release
    value["as_of"] = max([q["as_of"], *(item["as_of"] for item in documents)])
    value["lanes"] = [records[lane] for lane in native_rows(manifest, "manifest.json") if lane in records]
    sources = sorted({item["source_commit"] for item in value["lanes"]})
    value["identity"].pop("source_commit", None)
    value["identity"].pop("source_commits", None)
    value["identity"]["source_commit" if len(sources) == 1 else "source_commits"] = sources[0] if len(sources) == 1 else sources
    public_scan(value, "native publication")
    return json_bytes(value)


def plan_outputs(root: Path, release: str, plan_path: Path, directories: dict[str, Path],
                 publication_path: Path | None, assets: dict[str, Path] | None = None,
                 native_publications: dict[str, Path] | None = None) -> tuple[dict[Path, bytes], Inputs]:
    require(verifier.GA_PRODUCT_RELEASE_RE.fullmatch(release), "arguments", "/release", "expected a GA release")
    inputs = Inputs()
    base = Path("releases") / release
    manifest = inputs.load(root / base / "manifest.json")
    q = inputs.load(root / base / "qualification.json")
    compatibility = inputs.load(root / base / "compatibility.json")
    plan = inputs.load(plan_path)
    bundles, decisions = load_bundles(root, release, plan, manifest, q, directories, inputs, assets)
    rows, recut, previous = dispositions(root, release, manifest, plan)
    inputs.load(root / "releases" / previous["release"] / "manifest.json")
    require(manifest.get("status") == "draft" and manifest["publication"].get("authorized") is False
            and manifest["publication"].get("external_installation_qualified") is False,
            root / base / "manifest.json", "/", "aggregate requires a draft without publication authority")
    verify_runtime(inputs, root, release, manifest, q, previous)
    runtime_plan = next(item for item in plan["components"] if item["id"] == "rtx5090-container")
    require((publication_path is not None) is (runtime_plan["disposition"] == "recut"),
            "arguments", "/runtime-publication", "required exactly for a re-cut RTX 5090 component")
    if publication_path is not None:
        runtime_publication = inputs.load(publication_path)
        component = manifest["components"]["ninfer"]
        require(runtime_publication.get("artifact_type") == "ninfer_runtime_image_publication_receipt"
                and runtime_publication.get("source_commit") == component["source_commit"]
                and runtime_publication.get("release_tag") == component["release_tag"]
                and runtime_publication.get("image_digest") == component["oci_manifest_digest"]
                and runtime_publication.get("binary_sha256") == component["binary_archive_sha256"]
                and runtime_publication.get("secret_free") is True,
                publication_path, "/", "runtime publication differs from manifest")
        edge = q["composition"]["local_release_packaging"]["publication_receipt"]
        require(sha(inputs.read(publication_path)) == edge.get("sha256"),
                publication_path, "/", "runtime publication differs from staged receipt binding")
    validate_decisions(root, release, manifest, q, bundles, decisions)
    output = deepcopy(q)
    if output["composition"]["review"].get("status") != "pending":
        output["composition"]["review"] = {"status": "pending"}
    statement, clauses = provenance(root, release, manifest, set(recut), plan, plan_path)
    limitations = plan_limitations(plan, plan_path)
    output["composition"]["behavioral_qualification"]["scope"] = (
        clauses["rtx5090-container"]
        + "; retained component-level runtime qualification, not client-platform or product-route acceptance.")
    output["native_runtime_identity"] = source_identity(bundles, manifest, previous)
    pending = {}
    pub_data = native_publication(inputs, root, release, manifest, bundles, native_publications or {}, previous, q)
    pub = decode(pub_data, "native publication")
    output["as_of"] = max(date.fromisoformat(q["as_of"]), date.fromisoformat(pub["as_of"])).isoformat()
    pub_path = base / "qualification/native-publication.json"
    pending[pub_path] = pub_data
    output["composition"]["native_publication"] = binding(pub_path, pub_data)
    for lane, row in rows.items():
        mirrors = [item for item in compatibility["runtime_variants"] if item.get("id") == row["id"]]
        require(len(mirrors) == 1, base / "compatibility.json", "/runtime_variants/" + lane,
                "missing or ambiguous native mirror")
        mirror = mirrors[0]
        if lane not in recut:
            require(not any(name.startswith(lane + "_") for name in q["observed_gates"]),
                    base / "qualification.json", "/observed_gates", "carried lane claims a current gate")
            output["composition"]["native_runtime_variants"][row["id"]] = carried_entry(
                inputs, root, release, previous, row, mirror,
                q["composition"]["native_runtime_variants"][row["id"]], clauses[row["id"]])
            continue
        bundle = bundles[lane]
        require(row.get("status") == "qualified" and row.get("installable") is True,
                base / "manifest.json", "/components/ninfer_variants/" + lane, "binder posture is incomplete")
        require(all(mirror.get(key) == row.get(key) for key in (
            "status", "installable", "release_tag", "source_commit", "package_name", "package_url",
            "package_sha256", "package_bytes", "maximum_context_tokens", "build_profile"))
            and mirror["qualification_receipt"]["path"] == row["qualification"]["summary"]
            and mirror["qualification_receipt"]["sha256"] == row["qualification"]["sha256"],
            base / "compatibility.json", "/runtime_variants/" + lane, "binder mirror differs; run draft rebind first")
        derived = derive_admission(root, release, bundle, decisions)
        metadata = binder.package_metadata(bundle.asset_paths[row["package_name"]], bundle.receipt)
        require(all(metadata[name] == inputs.read(bundle.directory / name) for name in metadata),
                bundle.reference_path, "/inputs/assets", "packaged metadata differs from projection")
        errors = native_protocol_qualification_errors(bundle.values[lane + ".json"], bundle.configuration,
                                                       candidate_build_profile=row["build_profile"])
        verifier.validate_ninfer_variants(root, release, [row], {"runtime_variants": [row]},
                                         verifier.effective_native_model(manifest)["artifact_sha256"], errors)
        require(not errors, bundle.reference_path, "/", "; ".join(errors))
        references = row["qualification"]
        lane_gates = {}
        for key, filename in (("summary", lane + ".json"), ("fit", "fit.json"),
                              ("release_spec", "release-spec.json"), ("server_config", "server-config.json"),
                              ("identity_proof" if bundle.admission == "identity-proof.json" else "quality_screen",
                               bundle.admission)):
            edge = references if key == "summary" else references[key]
            name = edge["summary"] if key == "summary" else edge["path"]
            require(name.startswith(base.as_posix() + "/"), base / "manifest.json",
                    "/components/ninfer_variants/" + lane + "/qualification", "re-cut evidence must be release-local")
            bound = inputs.read(root / relative(name, "manifest.json", "/qualification"), edge["sha256"])
            wanted = speed_bytes(derived["identity_proof"]) if key == "identity_proof" else inputs.read(bundle.directory / filename)
            require(bound == wanted, name, "/", "bound receipt differs from current derived projection")
            if key in ("summary", "fit", "identity_proof", "quality_screen"):
                gate = lane + "_" + ("lane" if key == "summary" else key)
                lane_gates[gate] = binding(name, bound, status="passed")
        speed_path = base / "qualification" / f"{lane}-speed.json"
        speed_data = speed_bytes(derived["speed"])
        pending[speed_path] = speed_data
        admission_gate = lane + ("_identity_proof" if bundle.admission == "identity-proof.json" else "_quality_screen")
        output["observed_gates"].update({
            admission_gate: lane_gates[admission_gate],
            lane + "_fit": lane_gates[lane + "_fit"],
            lane + "_speed": binding(speed_path, speed_data, status="PASS", gate_passed=True),
            lane + "_lane": lane_gates[lane + "_lane"]})
        native_tail = terminal(bundle, "native")
        require(native_tail["details"]["lane_receipt_sha256"] == sha(inputs.read(bundle.directory / (lane + ".json"))),
                bundle.reference_path, "/inputs/tails", "native terminal receipt hash differs")
        speed_tail = read_retained(bundle, "tails", "tail-speed-terminal.json")
        require(speed_tail.get("status") == "passed" and speed_tail.get("all_outer_restorations_passed") is True
                and speed_tail.get("gpu") == lane[3:]
                and speed_tail.get("speed_sha256") == sha(inputs.read(bundle.directory / "speed.json"))
                and all(speed_tail.get(key) == bundle.values["speed.json"].get(key)
                        for key in ("role_suite", "all_cases", "normalized_outputs_identical")),
                bundle.reference_path, "/inputs/tails", "speed terminal differs from projected result")
        close = terminal(bundle, "close")
        require(close["details"]["speed_terminal_sha256"] == sha(inputs.read(retained(bundle, "tails", "tail-speed-terminal.json"))),
                bundle.reference_path, "/inputs/tails", "close terminal does not bind speed terminal")
        entry = {
            "status": "passed", "beta_qualified": True, "installable": row["installable"],
            "repository_path": references["summary"], "sha256": references["sha256"],
            **{key: row[key] for key in ("source_commit", "release_tag", "package_sha256", "configuration_sha256",
                                        "model_artifact_sha256", "build_profile")},
            "public_package_executed": False,
            "scope": clauses[row["id"]] + "; current pre-cut lane qualification. "
                     "Published-byte authentication and product-route acceptance are separate."}
        output["composition"]["native_runtime_variants"][row["id"]] = entry
        upgrade = upgrades(bundle, release)
        upgrade_path = base / "qualification" / f"{lane}-upgrade.json"
        pending[upgrade_path] = json_bytes(upgrade)
        output["observed_gates"][lane + "_upgrade"] = binding(
            upgrade_path, pending[upgrade_path], status=upgrade["status"], scope=upgrade["scope"], provenance=upgrade["provenance"])
        decision_edge = q["observed_gates"]["slow_first_request_parity_decision"]
        parity_value, waived = parity(bundle, release, decision_edge, decisions["slow_first_request_parity_decision"])
        parity_path = base / "qualification" / f"{lane}-agent-parity.json"
        parity_data = json_bytes(parity_value)
        pending[parity_path] = parity_data
        output["observed_gates"][lane + "_agent_parity"] = binding(
            parity_path, parity_data, status=parity_value["status"], raw_passed=parity_value["raw_passed"],
            accepted_under_exact_waiver=parity_value["waiver_applied"], passed_positions=parity_value["passed_positions"], positions=83)
        if waived:
            waiver = {
                "artifact_type": "omp_ninfer_founder_gate_waiver", "schema_version": 1, "release": release, "lane": lane,
                "subject": {"source": row["source_commit"], "component": row["release_tag"], "package": row["package_name"],
                            "package_sha256": row["package_sha256"], "server_sha256": row["server_binary_sha256"]},
                "waived": [waived], "raw_verdict": {"passed": False, "evidence_sha256": {"agent-verdict.json": sha(parity_data)}},
                "class_decision": decision_edge, "disclosure_required": True,
                "scope": "Only the recorded known two-mode slow-first-request TTFT miss; raw parity remains failed."}
            waiver_path = base / "qualification" / f"{lane}-{waived['job']}-waiver.json"
            pending[waiver_path] = json_bytes(waiver)
            output["observed_gates"][lane + "_" + waived["job"] + "_waiver"] = binding(
                waiver_path, pending[waiver_path], status="waived-by-founder")
    output.update(status="runtime-release-eligible", scope=statement + " No product-route or client-platform execution is inferred.",
                  eligibility_scope="Current component lanes only; external-install acceptance, native public installs/campaigns, "
                                    "product review, audit reconciliation and immutable pins remain binding.",
                  interpretation=statement + " Raw parity observations are retained; a class-bound waiver never rewrites a failure into a pass.",
                  publication_authorized=False, external_installation_qualified=False)
    output["remaining_release_gates"] = [
        "Prepare the five-route guide and run fresh candidate-bound external-install acceptance, three stock-client platforms, native campaigns/public installs and independent restoration.",
        "Bind the current product council/combined review ledger; reconcile the receipt audit and immutable evidence pins before publication admission."]
    manifest = deepcopy(manifest)
    manifest["qualification"]["runtime_release_eligible"] = True
    targets = manifest["publication"]["targets"]
    # Targets carry identity only; which components are carried is the generated statement's job.
    native_targets = [
        f"NInfer native {row['release_tag']}; package sha256:" + row["package_sha256"]
        for lane, row in sorted(rows.items(), key=lambda item: (item[0] not in recut, item[0]))]
    insertion = next((index for index, value in enumerate(targets) if isinstance(value, str) and value.startswith("NInfer native ")), len(targets))
    targets = [value for value in targets if not (isinstance(value, str) and value.startswith("NInfer native "))]
    targets[insertion:insertion] = native_targets
    manifest["publication"]["targets"] = targets
    manifest["publication"]["blockers"] = [
        value for value in manifest["publication"]["blockers"]
        if not ("native" in value.lower() and ("unbound" in value.lower() or "bindings pending" in value.lower()))]
    require(any("external-install" in value for value in manifest["publication"]["blockers"]),
            base / "manifest.json", "/publication/blockers", "required route, review or pin blockers absent")
    for blocker in ("current product council review and combined review ledger",
                    "receipt audit reconciliation and immutable evidence pins"):
        if not any(blocker in value for value in manifest["publication"]["blockers"]):
            manifest["publication"]["blockers"].append(blocker)
    neutral_limitation = "Current component evidence does not transfer predecessor review approval or authorize production promotion."
    require(statement not in limitations and neutral_limitation not in limitations,
            plan_path, "/limitations", "generated sentences must not be authored in the plan")
    manifest["limitations"] = [*limitations, statement, neutral_limitation]
    pending[base / "qualification.json"] = json_bytes(output)
    pending[base / "manifest.json"] = json_bytes(manifest)
    for path, data in pending.items():
        public_scan(decode(data, path), path)
    inputs.check()
    return pending, inputs


def assignments(values: list[str], label: str) -> dict[str, Path]:
    result = {}
    for value in values:
        name, separator, path = value.partition("=")
        require(separator and name and path and name not in result, "arguments", "/" + label,
                "expected unique NAME=PATH arguments")
        result[name] = Path(path).absolute()
    return result


def aggregate(root: Path, release: str, plan: Path, bundles: dict[str, Path],
              runtime_publication: Path | None, *, check: bool = False,
              assets: dict[str, Path] | None = None,
              native_publications: dict[str, Path] | None = None) -> list[str]:
    pending, inputs = plan_outputs(root, release, plan, bundles, runtime_publication, assets, native_publications)
    changed = [path for path, data in pending.items()
               if not (root / path).is_file() or (root / path).read_bytes() != data]
    if check:
        require(not changed, "release tree", "/", "generated files differ: " + ", ".join(map(str, changed)))
    else:
        inputs.check()
        for path in changed:
            atomic_write(root / path, pending[path])
    return [path.as_posix() for path in changed]


def admit(root: Path, release: str, plan: Path, bundles: dict[str, Path],
          *, check: bool = False, assets: dict[str, Path] | None = None) -> dict[str, Any]:
    pending, inputs, result = admit_outputs(root, release, plan, bundles, assets)
    changed = [path for path, data in pending.items()
               if not (root / path).is_file() or (root / path).read_bytes() != data]
    if check:
        require(not changed, "release tree", "/", "admission files differ: " + ", ".join(map(str, changed)))
    else:
        inputs.check()
        for path in changed:
            atomic_write(root / path, pending[path])
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("admit", "compose"):
        command = commands.add_parser(name)
        command.add_argument("--release", required=True)
        command.add_argument("--plan", type=Path, required=True)
        command.add_argument("--bundle", action="append", default=[], metavar="LANE=DIRECTORY")
        command.add_argument("--asset", action="append", default=[], metavar="ROLE=FILE")
        command.add_argument("--check", action="store_true")
        if name == "compose":
            command.add_argument("--runtime-publication", type=Path)
            command.add_argument("--native-publication", action="append", default=[], metavar="LANE=FILE")
    args = parser.parse_args(argv)
    try:
        if args.command == "admit":
            result = admit(ROOT, args.release, args.plan, assignments(args.bundle, "bundle"),
                           check=args.check, assets=assignments(args.asset, "asset"))
        else:
            changed = aggregate(ROOT, args.release, args.plan, assignments(args.bundle, "bundle"),
                                args.runtime_publication, check=args.check, assets=assignments(args.asset, "asset"),
                                native_publications=assignments(args.native_publication, "native-publication"))
            result = {"release": args.release, "status": "checked" if args.check else "aggregated",
                      "changed": changed, "publication_authorized": False}
    except (BundleError, OSError, ValueError, KeyError, TypeError, IndexError, subprocess.CalledProcessError) as error:
        print(f"aggregate refused: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
