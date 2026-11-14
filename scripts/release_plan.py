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
             "components", "platforms", "limitations", "decisions"}
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
    # Release-level limitation sentences are authored here and nowhere else; the aggregate
    # adds the generated component-provenance statement and inherits none from the predecessor.
    "limitations": ["sentence"],
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


def latest_ready_manifest(root: Path) -> dict[str, Any]:
    """Select the latest ready GA release, including when a later candidate exists."""
    candidates = []
    for path in (Path(root) / "releases").glob("*/manifest.json"):
        version = GA_RELEASE_RE.fullmatch(path.parent.name)
        if version is None:
            continue
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("status") == "ready":
            candidates.append((tuple(map(int, version.groups())), manifest))
    if not candidates:
        raise ValueError("plan init requires a ready GA predecessor")
    return max(candidates, key=lambda item: item[0])[1]


def initial_plan(root: Path, release: str, *, recut: list[str] | tuple[str, ...] = (),
                 client_tag: str | None = None,
                 decisions: list[str] | tuple[str, ...] = ()) -> dict[str, Any]:
    """Construct public plan inputs; the caller validates before committing them."""
    from verify_release import provenance_claim_errors

    if GA_RELEASE_RE.fullmatch(release) is None:
        raise ValueError("plan release must be a GA version (vX.Y.Z)")
    predecessor = latest_ready_manifest(root)
    overrides = {}
    for value in recut:
        component, separator, identity = value.partition("=")
        tag, at, commit = identity.rpartition("@")
        if (not separator or component not in COMPONENT_IDS or component in overrides
                or not at or not tag or COMMIT_RE.fullmatch(commit) is None):
            raise ValueError("--recut requires unique COMPONENT=TAG@COMMIT40 entries from the closed component set")
        overrides[component] = {"id": component, "disposition": "recut",
                                "release_tag": tag, "source_commit": commit}
    previous = manifest_components(predecessor)
    components = []
    for component in COMPONENT_IDS:
        if component in overrides:
            components.append(overrides[component])
        elif component in previous:
            components.append({"id": component, "disposition": "carried",
                               **{key: previous[component][key] for key in ("release_tag", "source_commit")}})
    decision_rows = []
    for value in decisions:
        fields = value.split(":")
        if len(fields) != 3:
            raise ValueError("--decision requires ID:KIND:SHA256")
        decision_rows.append(dict(zip(("id", "kind", "sha256"), fields)))
    authority = json.loads((Path(root) / "compatibility.json").read_text(encoding="utf-8"))
    limitations = []
    generated_neutral = (
        "Current component evidence does not transfer predecessor review approval or authorize production promotion."
    )
    for sentence in predecessor.get("limitations", []):
        generated = isinstance(sentence, str) and (
            sentence.startswith("Runtime components: ") or sentence == generated_neutral)
        if generated or provenance_claim_errors([sentence], "plan.limitations"):
            print(f"plan init: dropped predecessor limitation: {sentence}")
        else:
            limitations.append(sentence)
    return {
        "artifact_type": PLAN_SCHEMA["artifact_type"], "schema_version": 1, "release": release,
        "predecessor": predecessor["release"],
        "client": {"upstream_tag": client_tag if client_tag is not None else
                   predecessor["components"]["omp"]["upstream_tag"],
                   "disposition": "updated" if client_tag is not None else "carried"},
        "components": components,
        "platforms": {row["id"]: row["status"] for row in authority["profiles"]},
        "limitations": limitations,
        "decisions": decision_rows,
    }


def plan_errors(root: Path, release: str) -> list[str]:
    """Return every schema or authority disagreement without writing any files."""
    # Lazy import avoids a cycle when the verifier checks a plan during validate().
    from verify_release import (PRIVATE_MARKERS, predecessor_manifest, provenance_claim_errors,
                                unchanged_native_variant)

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

    limitations = plan.get("limitations")
    require(isinstance(limitations, list), "limitations must be an array")
    if isinstance(limitations, list):
        require(all(isinstance(value, str) and value and value == value.strip() for value in limitations),
                "limitations must be nonempty trimmed sentences")
        require(len({value for value in limitations if isinstance(value, str)}) == len(limitations),
                "limitations must be unique")
        errors.extend(provenance_claim_errors(
            [value for value in limitations if isinstance(value, str)], "plan.limitations"))

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
