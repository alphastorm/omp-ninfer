"""Validate the public, release-neutral input contract for a product cut.

Plans contain identities and support decisions, never operator locations. Private input
locations belong to the driver's ignored state file.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

COMPONENT_IDS = ("rtx5090-container", "rtx4090-windows-native", "rtx3090-windows-native")
PLAN_KEYS = {"artifact_type", "schema_version", "release", "predecessor", "client",
             "components", "platforms", "decisions"}
GA_RELEASE_RE = re.compile(r"v(\d+)\.(\d+)\.(\d+)")
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")

# The on-disk schema is deliberately closed; the semantic checks below bind it to authority.
PLAN_SCHEMA = {
    "artifact_type": "omp_ninfer_release_plan",
    "schema_version": 1,
    "client": {"upstream_tag": "string", "disposition": ("carried", "updated")},
    "components": {"id": COMPONENT_IDS, "disposition": ("recut", "carried"),
                   "release_tag": "string", "source_commit": "40 lowercase hex"},
    "platforms": {"profile id": ("qualified", "preview")},
    "decisions": {"id": "string", "kind": ("component-cut", "scope", "waiver"),
                  "sha256": "64 lowercase hex"},
}


def load_plan(root: Path, release: str) -> dict[str, Any]:
    """Load one plan, rejecting a non-object or an unsafe directory name."""
    if not isinstance(release, str) or GA_RELEASE_RE.fullmatch(release) is None:
        raise ValueError("plan release must be a GA version (vX.Y.Z)")
    path = Path(root) / "releases" / release / "plan.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"releases/{release}/plan.json: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"releases/{release}/plan.json must be an object")
    return value


def manifest_components(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    components = manifest.get("components", {})
    return {"rtx5090-container": components.get("ninfer", {}),
            **{row["id"]: row for row in components.get("ninfer_variants", [])
               if isinstance(row, dict) and isinstance(row.get("id"), str)}}


def plan_errors(root: Path, release: str) -> list[str]:
    """Return every schema or authority disagreement without writing any files."""
    # Lazy import avoids a cycle when the verifier checks a plan during validate().
    from verify_release import PRIVATE_MARKERS, predecessor_manifest, unchanged_native_variant

    root = Path(root)
    try:
        plan = load_plan(root, release)
    except ValueError as error:
        return [str(error)]
    errors: list[str] = []

    def require(condition: Any, message: str) -> None:
        if not condition:
            errors.append(f"plan.{message}")

    def shape(value: Any, keys: set[str], label: str) -> bool:
        valid = isinstance(value, dict) and set(value) == keys
        require(valid, f"{label} must contain exactly {', '.join(sorted(keys))}")
        return valid

    def strings(value: Any, label: str) -> None:
        if isinstance(value, str):
            text = value.strip()
            windows = PureWindowsPath(text)
            require(not (PurePosixPath(text).is_absolute() or windows.drive or windows.root),
                    f"{label} must not be an absolute path")
            require(not any(marker in value for marker in PRIVATE_MARKERS),
                    f"{label} contains a private marker")
        elif isinstance(value, dict):
            for key, child in value.items():
                strings(key, f"{label}.key")
                strings(child, f"{label}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                strings(child, f"{label}[{index}]")

    strings(plan, "")
    shape(plan, PLAN_KEYS, "keys")
    require(plan.get("artifact_type") == PLAN_SCHEMA["artifact_type"],
            "artifact_type must be omp_ninfer_release_plan")
    require(type(plan.get("schema_version")) is int and plan["schema_version"] == 1,
            "schema_version must be 1")
    require(plan.get("release") == release, "release must match its directory")
    predecessor = plan.get("predecessor")
    match = GA_RELEASE_RE.fullmatch(predecessor) if isinstance(predecessor, str) else None
    require(match is not None, "predecessor must be a GA version")
    if match is not None:
        current = GA_RELEASE_RE.fullmatch(release)
        assert current is not None
        require(tuple(map(int, current.groups())) > tuple(map(int, match.groups())),
                "release must be greater than predecessor")
    try:
        previous = predecessor_manifest(root, release)
    except (OSError, ValueError) as error:
        errors.append(f"plan.predecessor cannot be resolved: {error}")
        previous = None
    require(previous is not None and previous.get("release") == predecessor,
            "predecessor must be the latest ready GA manifest")
    prior_rows = manifest_components(previous or {})

    client = plan.get("client")
    if shape(client, {"upstream_tag", "disposition"}, "client"):
        tag = client["upstream_tag"]
        require(isinstance(tag, str) and bool(tag), "client.upstream_tag must be a nonempty string")
        require(client["disposition"] in ("carried", "updated"),
                "client.disposition must be carried or updated")
        prior_tag = (previous or {}).get("components", {}).get("omp", {}).get("upstream_tag")
        if client["disposition"] == "carried":
            require(tag == prior_tag, "client carried tag differs from predecessor")
        elif client["disposition"] == "updated":
            require(tag != prior_tag, "client updated tag reuses predecessor")

    rows = plan.get("components")
    require(isinstance(rows, list) and bool(rows), "components must be a nonempty array")
    planned: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows if isinstance(rows, list) else []):
        label = f"components[{index}]"
        if not shape(row, {"id", "disposition", "release_tag", "source_commit"}, label):
            continue
        component_id = row["id"]
        require(isinstance(component_id, str) and component_id in COMPONENT_IDS,
                f"{label}.id must belong to the closed component set")
        if not isinstance(component_id, str):
            continue
        require(component_id not in planned, f"{label}.id is duplicated")
        planned[component_id] = row
        require(row["disposition"] in ("carried", "recut"),
                f"{label}.disposition must be carried or recut")
        require(isinstance(row["release_tag"], str) and bool(row["release_tag"]),
                f"{label}.release_tag must be a nonempty string")
        require(isinstance(row["source_commit"], str)
                and COMMIT_RE.fullmatch(row["source_commit"]) is not None,
                f"{label}.source_commit must be 40 lowercase hex")
        prior = prior_rows.get(component_id, {})
        if row["disposition"] == "carried":
            require(bool(prior) and all(row[key] == prior.get(key)
                                       for key in ("release_tag", "source_commit")),
                    f"{label} carried identity differs from predecessor")
        elif row["disposition"] == "recut":
            require(row["release_tag"] != prior.get("release_tag"),
                    f"{label} recut tag reuses predecessor")
    require("rtx5090-container" in planned, "components must include rtx5090-container")

    platforms = plan.get("platforms")
    require(isinstance(platforms, dict) and bool(platforms), "platforms must be a nonempty object")
    if isinstance(platforms, dict):
        require(all(value in ("qualified", "preview") for value in platforms.values()),
                "platforms values must be qualified or preview")
    authority_path = root / "releases" / release / "compatibility.json"
    if not authority_path.is_file():
        authority_path = root / "compatibility.json"
    try:
        authority = json.loads(authority_path.read_text(encoding="utf-8"))
        profile_ids = [row["id"] for row in authority["profiles"]]
        require(isinstance(platforms, dict) and set(platforms) == set(profile_ids),
                "platforms keys must equal authority profile ids")
    except (OSError, ValueError, KeyError, TypeError) as error:
        errors.append(f"plan.platforms authority cannot be read: {error}")

    decisions = plan.get("decisions")
    require(isinstance(decisions, list), "decisions must be an array")
    seen: set[str] = set()
    for index, decision in enumerate(decisions if isinstance(decisions, list) else []):
        label = f"decisions[{index}]"
        if not shape(decision, {"id", "kind", "sha256"}, label):
            continue
        decision_id = decision["id"]
        valid_id = isinstance(decision_id, str) and bool(decision_id)
        require(valid_id, f"{label}.id must be a nonempty string")
        if valid_id:
            require(decision_id not in seen, f"{label}.id is duplicated")
            seen.add(decision_id)
        require(decision["kind"] in ("component-cut", "scope", "waiver"),
                f"{label}.kind must be component-cut, scope or waiver")
        require(isinstance(decision["sha256"], str)
                and SHA256_RE.fullmatch(decision["sha256"]) is not None,
                f"{label}.sha256 must be 64 lowercase hex")

    manifest_path = root / "releases" / release / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            actual = manifest_components(manifest)
            require(manifest.get("release") == release, "manifest release differs from plan")
            require(set(actual) == set(planned), "manifest component ids differ from plan")
            require(isinstance(client, dict) and client.get("upstream_tag")
                    == manifest["components"]["omp"].get("upstream_tag"),
                    "manifest client tag differs from plan")
            for component_id, row in planned.items():
                bound = actual.get(component_id, {})
                require(all(row[key] == bound.get(key) for key in ("release_tag", "source_commit")),
                        f"manifest {component_id} tag or commit differs from plan")
                prior = prior_rows.get(component_id)
                carried = (
                    prior is not None and all(bound.get(key) == prior.get(key) for key in (
                        "release_tag", "oci_manifest_digest", "server_binary_sha256", "source_commit"))
                    if component_id == "rtx5090-container"
                    else unchanged_native_variant(bound, prior)
                )
                require(row["disposition"] == ("carried" if carried else "recut"),
                        f"manifest {component_id} provenance disposition differs from plan")
        except (OSError, ValueError, KeyError, TypeError) as error:
            errors.append(f"plan.manifest cannot be read: {error}")
    return errors
