#!/usr/bin/env python3
"""Validate the OMP NInfer release manifest and its bound profile/qualification."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_compatibility import (  # pyright: ignore[reportMissingImports]
    RUNTIME_VARIANT_PACKAGE_NAME_RES,
    RUNTIME_VARIANT_RELEASE_TAG_RES,
    load_authority,
    render as render_compatibility_matrix,
)

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
OCI_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
OMP_RELEASE_ID_RE = re.compile(
    r"^(?P<version>[0-9]+\.[0-9]+\.[0-9]+)-cross-platform-"
    r"(?P<channel>preview|beta)-(?P<sequence>[1-9][0-9]*)$"
)
PRODUCT_RELEASE_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")
GA_PRODUCT_RELEASE_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")
OMP_ASSET_DOWNLOAD_RE = re.compile(
    r"^/alphastorm/homebrew-omp/releases/download/(?P<tag>[^/]+)/(?P<name>[^/]+)$"
)
PRIVATE_MARKERS = (
    "/Users/",
    "/home/",
    "C:\\Users\\",
    "nyc-pc",
    "sf-pc",
    "sf-old",
    "sf-nas",
    "ALPHA-DESKTOP",
    "ALPHA-NG",
    "ALPHA-OLD",
)
PLACEHOLDER_RE = re.compile(r"(?:<[^>]+>|\bTODO\b|\bTBD\b)", re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r'!?\[[^]]*\]\(([^)\s]+)(?:\s+["\'][^)]*["\'])?\)')
MARKDOWN_REFERENCE_RE = re.compile(r'^\[[^]]+\]:\s+(\S+)', re.MULTILINE)


class ContractError(Exception):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"{path}: {error}") from error
    if not isinstance(value, dict):
        raise ContractError(f"{path}: root must be an object")
    return value


def resolve_product_release(root: Path, requested: str | None) -> str:
    release = requested
    if release is None:
        release = load_json(root / "compatibility.json").get("product_release")
    if not isinstance(release, str) or PRODUCT_RELEASE_RE.fullmatch(release) is None:
        raise ContractError("product release must be a versioned release directory name")
    return release


def ga_release(release: Any) -> bool:
    return (
        isinstance(release, str)
        and GA_PRODUCT_RELEASE_RE.fullmatch(release) is not None
    )


def expected_omp_source_repository(release: str) -> str:
    return (
        "https://github.com/alphastorm/omp-monorepo"
        if release == "v0.1.0-beta.1"
        else "https://github.com/alphastorm/oh-my-pi"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def require_sha(value: Any, label: str, errors: list[str], *, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    require(isinstance(value, str) and SHA256_RE.fullmatch(value) is not None,
            f"{label} must be a lower-case SHA-256", errors)


def require_git_sha(value: Any, label: str, errors: list[str], *, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    require(isinstance(value, str) and GIT_SHA_RE.fullmatch(value) is not None,
            f"{label} must be a lower-case 40-character Git commit", errors)


def require_https(value: Any, label: str, errors: list[str], *, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    require(isinstance(value, str) and urlparse(value).scheme == "https" and bool(urlparse(value).netloc),
            f"{label} must be an HTTPS URL", errors)


def require_product_raw_url(value: Any, label: str, path: str, errors: list[str]) -> None:
    require_https(value, label, errors)
    require(
        isinstance(value, str)
        and re.fullmatch(
            r"https://raw\.githubusercontent\.com/alphastorm/omp-ninfer/"
            r"[0-9a-f]{40}/" + re.escape(path),
            value,
        )
        is not None,
        f"{label} must bind an immutable product commit and path",
        errors,
    )


PRODUCT_RAW_URL_RE = re.compile(
    r"https://raw\.githubusercontent\.com/alphastorm/omp-ninfer/([0-9a-f]{40})/(.+)"
)


def pinned_blob_sha256(
    root: Path, commit: str, path: str, cache: dict[tuple[str, str], str | None]
) -> str | None:
    """SHA-256 of ``path`` at ``commit`` in the repository at ``root``.

    None when the commit is not in local history (shallow clones, exported trees); the
    string "absent" when the commit is known but does not contain the path.
    """
    key = (commit, path)
    if key not in cache:
        result: str | None = None
        if (root / ".git").exists():
            probe = subprocess.run(
                ["git", "-C", str(root), "cat-file", "-e", f"{commit}^{{commit}}"],
                capture_output=True,
            )
            if probe.returncode == 0:
                shown = subprocess.run(
                    ["git", "-C", str(root), "show", f"{commit}:{path}"],
                    capture_output=True,
                )
                result = (
                    hashlib.sha256(shown.stdout).hexdigest()
                    if shown.returncode == 0
                    else "absent"
                )
        cache[key] = result
    return cache[key]


def require_pinned_bytes(
    root: Path,
    url: Any,
    expected_sha256: Any,
    label: str,
    errors: list[str],
    cache: dict[tuple[str, str], str | None],
) -> None:
    """A pinned raw URL must serve exactly the bytes its companion SHA-256 records.

    Fails closed: a commit that local history cannot resolve is an error, not a skip, because
    the check is requested explicitly and a vacuous pass would read as verified.
    """
    match = PRODUCT_RAW_URL_RE.fullmatch(url) if isinstance(url, str) else None
    if match is None or not isinstance(expected_sha256, str):
        return
    commit, path = match.group(1), match.group(2)
    observed = pinned_blob_sha256(root, commit, path, cache)
    require(observed is not None,
            f"{label} pins commit {commit[:12]} which is not in local git history "
            "(full history is required to verify pins)", errors)
    require(observed != "absent",
            f"{label} pins commit {commit[:12]} which does not contain {path}", errors)
    require(observed in (None, "absent") or observed == expected_sha256,
            f"{label} pins commit {commit[:12]} whose {path} differs from the recorded SHA-256",
            errors)


def pinned_evidence(
    manifest: dict[str, Any],
    compatibility: dict[str, Any],
    qualification: dict[str, Any],
) -> Iterator[tuple[str, Any, Any]]:
    """Every (label, url, sha256) evidence pin a ready release publishes."""
    manifest_qualification = manifest.get("qualification", {})
    yield ("qualification.public_url", manifest_qualification.get("public_url"),
           manifest_qualification.get("summary_sha256"))
    omp = manifest.get("components", {}).get("omp", {})
    yield ("components.omp.compatibility_url", omp.get("compatibility_url"),
           omp.get("compatibility_sha256"))
    for item in manifest.get("components", {}).get("ninfer_variants", []):
        if isinstance(item, dict):
            qual = item.get("qualification", {})
            yield (f"components.ninfer_variants[{item.get('id')}].qualification.public_url",
                   qual.get("public_url"), qual.get("sha256"))
    acceptance = qualification.get("composition", {}).get("external_installation_acceptance", {})
    yield ("external acceptance public_url", acceptance.get("public_url"), acceptance.get("sha256"))
    for profile_item in compatibility.get("profiles", []):
        if not isinstance(profile_item, dict):
            continue
        profile_id = profile_item.get("id")
        receipt = profile_item.get("gpu_qualification", {}).get("receipt", {})
        yield (f"compatibility {profile_id} gpu_qualification.receipt.url",
               receipt.get("url"), receipt.get("sha256"))
        acceptance_receipt = profile_item.get("acceptance_receipt", {})
        if isinstance(acceptance_receipt, dict):
            yield (f"compatibility {profile_id} acceptance_receipt.url",
                   acceptance_receipt.get("url"), acceptance_receipt.get("sha256"))
    for item in compatibility.get("runtime_variants", []):
        if isinstance(item, dict):
            receipt = item.get("qualification_receipt", {})
            yield (f"compatibility.runtime_variants[{item.get('id')}].qualification_receipt.url",
                   receipt.get("url"), receipt.get("sha256"))


def validate_pinned_evidence(
    root: Path,
    manifest: dict[str, Any],
    compatibility: dict[str, Any],
    qualification: dict[str, Any],
    errors: list[str],
) -> None:
    cache: dict[tuple[str, str], str | None] = {}
    for label, url, expected in pinned_evidence(manifest, compatibility, qualification):
        require_pinned_bytes(root, url, expected, label, errors, cache)


def validate_ga_evidence_bindings(
    release: Any,
    manifest: dict[str, Any],
    compatibility: dict[str, Any],
    qualification: dict[str, Any],
    profiles: list[tuple[str, dict[str, Any]]],
    errors: list[str],
) -> None:
    """A ready GA release's derived records must name the manifest's exact components.

    Profile launch arguments, the qualification summary's runtime identity, and the native
    variant rows of the compatibility authority and qualification composition are all copies of
    manifest identities; a copy that drifts is a stale public claim.
    """
    components = manifest.get("components", {})
    ninfer = components.get("ninfer", {})
    model = components.get("model", {})
    runtime = manifest.get("runtime_identity", {})

    for label, profile in profiles:
        arguments = profile.get("server", {}).get("arguments", [])
        if not isinstance(arguments, list):
            continue
        for flag, expected, source in (
            ("--binary-sha256", ninfer.get("server_binary_sha256"),
             "components.ninfer.server_binary_sha256"),
            ("--artifact-sha256", model.get("artifact_sha256"),
             "components.model.artifact_sha256"),
            ("--config-sha256", runtime.get("configuration_sha256"),
             "runtime_identity.configuration_sha256"),
        ):
            require(arguments.count(flag) == 1 and argument_value(arguments, flag) == expected,
                    f"{label}: {flag} must occur once and equal {source}", errors)
        # The identity a server echoes must be the identity of the configuration the launcher
        # actually runs: a declared value copied from a qualification of a different
        # configuration is a false public claim (measured on v0.6.2, whose route declared the
        # checkpointed identity while running with no checkpoint store).
        require(runtime.get("configuration_sha256") == configuration_identity(profile),
                f"{label}: runtime_identity.configuration_sha256 must equal the identity of the "
                "configuration this profile launches", errors)

    identity = qualification.get("runtime_identity", {})
    composition = qualification.get("composition", {})
    behavioral = composition.get("behavioral_qualification", {})
    for key, expected, source in (
        ("upstream_commit", ninfer.get("upstream_commit"), "components.ninfer.upstream_commit"),
        ("release_source_archive_sha256", ninfer.get("source_archive_sha256"),
         "components.ninfer.source_archive_sha256"),
        ("behavioral_source_commit", behavioral.get("source_commit"),
         "composition.behavioral_qualification.source_commit"),
    ):
        require(identity.get(key) == expected,
                f"qualification.runtime_identity.{key} must equal {source}", errors)

    manifest_variants = {
        item.get("id"): item
        for item in components.get("ninfer_variants", [])
        if isinstance(item, dict)
    }
    for item in compatibility.get("runtime_variants", []):
        if not isinstance(item, dict):
            continue
        source_item = manifest_variants.get(item.get("id"))
        if source_item is None:
            continue
        prefix = f"compatibility.runtime_variants[{item.get('id')}]"
        for key in ("release_tag", "source_commit", "package_name", "package_url",
                    "package_sha256", "package_bytes", "maximum_context_tokens"):
            require(item.get(key) == source_item.get(key),
                    f"{prefix}.{key} must equal the manifest component", errors)
        receipt = item.get("qualification_receipt", {})
        qual = source_item.get("qualification", {})
        require(receipt.get("path") == qual.get("summary"),
                f"{prefix}.qualification_receipt.path must equal the manifest qualification summary",
                errors)
        require(receipt.get("sha256") == qual.get("sha256"),
                f"{prefix}.qualification_receipt.sha256 must equal the manifest qualification hash",
                errors)
        if isinstance(qual.get("summary"), str):
            require_product_raw_url(receipt.get("url"),
                                    f"{prefix}.qualification_receipt.url", qual["summary"], errors)

    native = composition.get("native_runtime_variants", {})
    for variant_id, entry in (native.items() if isinstance(native, dict) else ()):
        source_item = manifest_variants.get(variant_id)
        if source_item is None or not isinstance(entry, dict):
            continue
        prefix = f"qualification.composition.native_runtime_variants[{variant_id}]"
        qual = source_item.get("qualification", {})
        for key, expected in (
            ("release_tag", source_item.get("release_tag")),
            ("package_sha256", source_item.get("package_sha256")),
            ("repository_path", qual.get("summary")),
            ("sha256", qual.get("sha256")),
        ):
            require(entry.get(key) == expected,
                    f"{prefix}.{key} must equal the manifest component", errors)

    for profile_item in compatibility.get("profiles", []):
        if not isinstance(profile_item, dict):
            continue
        profile_id = profile_item.get("id")
        gpu = profile_item.get("gpu_qualification", {})
        require(gpu.get("profile") == runtime.get("deployment_profile"),
                f"compatibility {profile_id} gpu_qualification.profile must equal the manifest deployment profile",
                errors)
        require_product_raw_url(gpu.get("receipt", {}).get("url"),
                                f"compatibility {profile_id} gpu_qualification.receipt.url",
                                f"releases/{release}/qualification/rtx5090.json", errors)


def walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for child in value.values() for item in walk_strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in walk_strings(child)]
    return []


def walk_object_fields(
    value: Any, path: str
) -> Iterator[tuple[str, str, Any]]:
    if isinstance(value, dict):
        for field, child in value.items():
            child_path = f"{path}.{field}"
            yield child_path, field, child
            yield from walk_object_fields(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_object_fields(child, f"{path}[{index}]")


def validate_ready_state_consistency(
    manifest: dict[str, Any],
    compatibility: dict[str, Any],
    qualification: dict[str, Any],
    errors: list[str],
) -> None:
    forbidden_markers = ("draft", "pending")
    stale_phrases = (
        "release draft",
        "remains pending",
        "remain pending",
        "remains blocked",
        "remain blocked",
        "publication remains blocked",
        "in qualification",
    )
    for label, document in (
        ("manifest", manifest),
        ("compatibility", compatibility),
        ("qualification", qualification),
    ):
        for path, field, value in walk_object_fields(document, label):
            if field == "status" and isinstance(value, str):
                normalized = value.casefold()
                require(
                    not any(marker in normalized for marker in forbidden_markers),
                    f"{path} must not contain draft or pending in ready mode",
                    errors,
                )
            if field == "authority_id" and isinstance(value, str):
                normalized = value.casefold()
                require(
                    not any(
                        marker in normalized
                        for marker in forbidden_markers
                    ),
                    f"{path} must not contain draft or pending in ready mode",
                    errors,
                )
            if field in {"remaining_release_gates"}:
                require(
                    isinstance(value, list) and value == [],
                    f"{path} must be an empty array in ready mode",
                    errors,
                )
            if label in {"manifest", "compatibility"} and field == "blockers":
                require(
                    isinstance(value, list) and value == [],
                    f"{path} must be an empty array in ready mode",
                    errors,
                )
        for text in walk_strings(document):
            normalized = text.casefold()
            for phrase in stale_phrases:
                require(
                    phrase not in normalized,
                    f"{label} contains stale release-state phrase {phrase!r} in ready mode",
                    errors,
                )



def validate_exact_lane_set(
    manifest: dict[str, Any],
    compatibility: dict[str, Any],
    qualification: dict[str, Any],
    errors: list[str],
) -> None:
    manifest_variant_ids = {
        item.get("id")
        for item in manifest.get("components", {}).get("ninfer_variants", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    compatibility_variant_ids = {
        item.get("id")
        for item in compatibility.get("runtime_variants", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    qualification_variants = qualification.get("composition", {}).get(
        "native_runtime_variants"
    )
    qualification_variant_ids = (
        set(qualification_variants)
        if isinstance(qualification_variants, dict)
        else set()
    )
    require(
        bool(manifest_variant_ids),
        "ready release requires a non-empty components.ninfer_variants id set",
        errors,
    )
    require(
        manifest_variant_ids == compatibility_variant_ids,
        "ready components.ninfer_variants ids must exactly match compatibility.runtime_variants ids",
        errors,
    )
    require(
        isinstance(qualification_variants, dict),
        "qualification.composition.native_runtime_variants must be an object in ready mode",
        errors,
    )
    require(
        manifest_variant_ids == qualification_variant_ids,
        "ready components.ninfer_variants ids must exactly match qualification.composition.native_runtime_variants keys",
        errors,
    )


def argument_value(arguments: list[Any], flag: str) -> Any:
    try:
        index = arguments.index(flag)
    except ValueError:
        return None
    return arguments[index + 1] if index + 1 < len(arguments) else None


REQUIRED_TUNING_VALUES = (
    "--kv-capacity",
    "--prefill-chunk",
    "--kv-dtype",
    "--max-concurrency",
    "--spec",
    "--draft-tokens",
)
REQUIRED_SERVER_FLAGS = ("--lm-head-draft", "--vision", "--preserve-thinking")
NINFER_VARIANT_IDS = ("rtx3090-windows-native", "rtx4090-windows-native")
NINFER_RELEASE_TAG_RE = re.compile(
    r"^v(?:0\.2\.0|0\.3\.0|0\.4\.0|0\.4\.1|0\.4\.3|0\.4\.4|0\.4\.5|0\.5\.1|0\.6\.2|0\.6\.3|0\.6\.4)-qwen38-5090-beta\.[1-9][0-9]*$"
)
CHECKSUM_REQUIRED_ASSET_FIELDS = (
    "package",
    "sbom",
    "installer",
    "controller",
    "gpu_owner_controller",
    "state_protection",
)
CHECKSUM_TRIGGER_ASSET_FIELDS = CHECKSUM_REQUIRED_ASSET_FIELDS[1:] + (
    "source_archive",
)
SHA256SUMS_ENTRY_RE = re.compile(r"^([0-9a-f]{64}) [ *](.+)$")


def validate_variant_checksums(
    root: Path,
    release: str,
    item: dict[str, Any],
    prefix: str,
    errors: list[str],
) -> None:
    has_component_assets = any(
        item.get(f"{field}_url") is not None
        or item.get(f"{field}_sha256") is not None
        for field in CHECKSUM_TRIGGER_ASSET_FIELDS
    )
    if not has_component_assets:
        return

    required_assets: list[tuple[str, str, str]] = []
    for field in CHECKSUM_REQUIRED_ASSET_FIELDS:
        url = item.get(f"{field}_url")
        digest = item.get(f"{field}_sha256")
        if (
            isinstance(url, str)
            and isinstance(digest, str)
            and SHA256_RE.fullmatch(digest) is not None
        ):
            filename = Path(unquote(urlparse(url).path)).name
            if filename:
                required_assets.append((field, filename, digest))

    source_asset: tuple[str, str, str] | None = None
    source_url = item.get("source_archive_url")
    source_digest = item.get("source_archive_sha256")
    if (
        isinstance(source_url, str)
        and isinstance(source_digest, str)
        and SHA256_RE.fullmatch(source_digest) is not None
    ):
        source_filename = Path(unquote(urlparse(source_url).path)).name
        if source_filename:
            source_asset = ("source_archive", source_filename, source_digest)

    checksums_digest = item.get("checksums_sha256")
    require_sha(checksums_digest, f"{prefix}.checksums_sha256", errors)
    checksums_path = (
        root
        / "releases"
        / release
        / "qualification"
        / f"{item.get('id')}.SHA256SUMS"
    )
    require(checksums_path.is_file(), f"{prefix} checksums file must exist", errors)
    if not checksums_path.is_file():
        return

    if isinstance(checksums_digest, str):
        require(
            sha256_file(checksums_path) == checksums_digest,
            f"{prefix}.checksums_sha256 must match the checksums file",
            errors,
        )

    entries: dict[str, list[str]] = {}
    try:
        lines = checksums_path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        errors.append(f"{prefix} checksums file: {error}")
        return
    for line_number, line in enumerate(lines, 1):
        if not line:
            continue
        match = SHA256SUMS_ENTRY_RE.fullmatch(line)
        if match is None:
            errors.append(
                f"{prefix} checksums file line {line_number} is not a SHA256SUMS entry"
            )
            continue
        entries.setdefault(match.group(2), []).append(match.group(1))

    for field, filename, expected_digest in required_assets:
        require(
            entries.get(filename) == [expected_digest],
            f"{prefix} checksums entry {filename} must match {field}_sha256",
            errors,
        )
    if source_asset is not None and source_asset[1] in entries:
        field, filename, expected_digest = source_asset
        require(
            entries[filename] == [expected_digest],
            f"{prefix} checksums entry {filename} must match {field}_sha256",
            errors,
        )


def validate_ninfer_variants(
    root: Path,
    release: str,
    variants: Any,
    compatibility: dict[str, Any],
    model_sha256: Any,
    errors: list[str],
    *,
    allow_pending: bool = False,
) -> None:
    require(isinstance(variants, list), "components.ninfer_variants must be an array", errors)
    if not isinstance(variants, list):
        return
    ids = [item.get("id") for item in variants if isinstance(item, dict)]
    require(len(ids) == len(variants), "NInfer runtime variant must be an object", errors)
    require(ids == [item for item in NINFER_VARIANT_IDS if item in ids],
            "NInfer runtime variants must use the closed set in canonical order", errors)
    require(len(ids) == len(set(ids)), "NInfer runtime variants are duplicated", errors)
    compatibility_ids = [
        item.get("id")
        for item in compatibility.get("runtime_variants", [])
        if isinstance(item, dict)
    ]
    require(ids == compatibility_ids,
            "manifest and compatibility runtime variant sets must match", errors)
    for item in variants:
        if not isinstance(item, dict):
            continue
        variant_id = item.get("id", "<unknown>")
        prefix = f"components.ninfer_variants.{variant_id}"
        status = item.get("status")
        require(status in {"qualified", "preview"},
                f"{prefix}.status must be qualified or preview", errors)
        require(item.get("installable") is (status == "qualified"),
                f"{prefix}.installable must match status", errors)
        compatibility_item = next(
            (candidate for candidate in compatibility.get("runtime_variants", [])
             if isinstance(candidate, dict) and candidate.get("id") == variant_id),
            {},
        )
        require(compatibility_item.get("status") == status,
                f"{prefix}.status must match compatibility", errors)
        require(compatibility_item.get("installable") is item.get("installable"),
                f"{prefix}.installable must match compatibility", errors)
        require(item.get("repository") == "https://github.com/alphastorm/ninfer",
                f"{prefix}.repository must be the public NInfer repository", errors)
        require_git_sha(item.get("source_commit"), f"{prefix}.source_commit", errors)
        for field in (
            "source_archive_sha256",
            "sbom_sha256",
            "installer_sha256",
            "controller_sha256",
            "gpu_owner_controller_sha256",
            "state_protection_sha256",
            "server_binary_sha256",
            "configuration_sha256",
        ):
            require_sha(item.get(field), f"{prefix}.{field}", errors, nullable=allow_pending)
        require_sha(item.get("package_sha256"), f"{prefix}.package_sha256", errors)
        require_sha(item.get("model_artifact_sha256"),
                    f"{prefix}.model_artifact_sha256", errors)
        require(item.get("model_artifact_sha256") == model_sha256,
                f"{prefix}.model_artifact_sha256 must match the product model", errors)
        require(isinstance(item.get("package_bytes"), int) and item["package_bytes"] > 0,
                f"{prefix}.package_bytes must be positive", errors)
        require(isinstance(item.get("maximum_context_tokens"), int)
                and item["maximum_context_tokens"] > 0,
                f"{prefix}.maximum_context_tokens must be positive", errors)
        release_tag = item.get("release_tag")
        require(isinstance(release_tag, str)
                and RUNTIME_VARIANT_RELEASE_TAG_RES[variant_id].fullmatch(release_tag) is not None,
                f"{prefix}.release_tag is invalid", errors)
        asset_prefix = (
            "https://github.com/alphastorm/ninfer/releases/download/"
            + str(release_tag)
            + "/"
        )
        for field in (
            "source_archive_url",
            "package_url",
            "sbom_url",
            "installer_url",
            "controller_url",
            "gpu_owner_controller_url",
            "state_protection_url",
        ):
            require_https(item.get(field), f"{prefix}.{field}", errors,
                          nullable=allow_pending)
            if item.get(field) is not None:
                require(isinstance(item.get(field), str) and item[field].startswith(asset_prefix),
                        f"{prefix}.{field} must bind its component release", errors)

        package_url = item.get("package_url")
        package_name = item.get("package_name")
        if package_name is None and isinstance(package_url, str):
            package_name = Path(urlparse(package_url).path).name
        require(isinstance(package_name, str)
                and RUNTIME_VARIANT_PACKAGE_NAME_RES[variant_id].fullmatch(package_name) is not None,
                f"{prefix}.package_name is invalid", errors)
        if isinstance(package_url, str) and isinstance(package_name, str):
            require(package_url == asset_prefix + package_name,
                    f"{prefix}.package_url must bind the exact package name", errors)

        if ga_release(release):
            validate_variant_checksums(root, release, item, prefix, errors)

        qualification = item.get("qualification", {})
        require(isinstance(qualification, dict), f"{prefix}.qualification must be an object", errors)
        summary = qualification.get("summary") if isinstance(qualification, dict) else None
        require(isinstance(summary, str), f"{prefix}.qualification.summary must be a path", errors)
        release_root = (root / "releases" / release).resolve()
        if isinstance(summary, str) and summary.startswith(("docs/", "releases/")):
            summary_path = (root / summary).resolve()
        else:
            summary_path = (release_root / str(summary)).resolve()
        require(summary_path.is_relative_to(root.resolve()),
                f"{prefix}.qualification summary must stay inside the repository", errors)
        if not allow_pending:
            require(summary_path.is_relative_to(release_root),
                    f"{prefix}.qualification summary must stay inside the release", errors)
        require(summary_path.is_file(), f"{prefix}.qualification summary must exist", errors)
        require_sha(qualification.get("sha256"), f"{prefix}.qualification.sha256", errors)
        if summary_path.is_file() and isinstance(qualification.get("sha256"), str):
            require(sha256_file(summary_path) == qualification.get("sha256"),
                    f"{prefix}.qualification SHA-256 must match receipt bytes", errors)
        public_url = qualification.get("public_url")
        if public_url is None:
            require(allow_pending,
                    f"{prefix}.qualification.public_url must bind published evidence", errors)
        elif summary_path.is_relative_to(root.resolve()):
            require_product_raw_url(
                public_url,
                f"{prefix}.qualification.public_url",
                summary_path.relative_to(root.resolve()).as_posix(),
                errors,
            )
        receipt = load_json(summary_path) if summary_path.is_file() else {}
        # The RTX 3090 parity lineage and every mainline native lane qualify through an
        # orchestrator summary; the RTX 4090 durable lineage through its beta receipt.
        native_receipt = (
            receipt.get("artifact_type") == "ninfer_native_qualification_summary"
            and receipt.get("lane") == variant_id.split("-")[0]
        )
        parity_receipt = native_receipt or (
            variant_id == "rtx3090-windows-native"
            and receipt.get("artifact_type") == "ninfer_rtx3090_qualification_summary"
        )
        if status == "qualified":
            if parity_receipt:
                require(receipt.get("status") == "passed",
                        f"{prefix} parity qualification must pass", errors)
            else:
                require(receipt.get("status") == "passed"
                        and (receipt.get("beta_qualified") is True
                             or receipt.get("qualification_class") == "public-release-qualification"),
                        f"{prefix} qualification must pass beta support", errors)
        else:
            require(receipt.get("status") == "incomplete"
                    and receipt.get("beta_qualified") is False
                    and receipt.get("installable") is False,
                    f"{prefix} preview qualification must remain incomplete", errors)
            require(isinstance(receipt.get("deferred_gates"), list)
                    and len(receipt["deferred_gates"]) > 0,
                    f"{prefix} preview qualification must enumerate deferred gates", errors)
        identity = receipt.get("identity", {})
        package = receipt.get("package", {})
        if parity_receipt:
            require(receipt.get("source_commit") == item.get("source_commit"),
                    f"{prefix} qualification source must match", errors)
            require(package.get("filename") == package_name,
                    f"{prefix} qualification package name must match", errors)
            require(package.get("sha256") == item.get("package_sha256"),
                    f"{prefix} qualification package must match", errors)
            require(package.get("bytes") == item.get("package_bytes"),
                    f"{prefix} qualification package size must match", errors)
            if native_receipt:
                require(receipt.get("server_binary_sha256") == item.get("server_binary_sha256"),
                        f"{prefix} qualification server must match", errors)
                require(receipt.get("configuration_sha256") == item.get("configuration_sha256"),
                        f"{prefix} qualification configuration must match", errors)
                support = receipt.get("support_assets", {})
                for field in ("installer_sha256", "controller_sha256",
                              "gpu_owner_controller_sha256", "state_protection_sha256"):
                    require(support.get(field) == item.get(field),
                            f"{prefix} qualification {field} must match", errors)
                require(receipt.get("model_sha256") == item.get("model_artifact_sha256"),
                        f"{prefix} qualification model must match the variant", errors)
        else:
            require(identity.get("source_commit") == item.get("source_commit"),
                    f"{prefix} qualification source must match", errors)
            require(identity.get("server_binary_sha256") == item.get("server_binary_sha256"),
                    f"{prefix} qualification server must match", errors)
            require(identity.get("configuration_sha256") == item.get("configuration_sha256"),
                    f"{prefix} qualification configuration must match", errors)
            require(package.get("sha256") == item.get("package_sha256"),
                    f"{prefix} qualification package must match", errors)
            for field in (
                "sbom_sha256",
                "installer_sha256",
                "controller_sha256",
                "gpu_owner_controller_sha256",
                "state_protection_sha256",
            ):
                require(package.get(field) == item.get(field),
                        f"{prefix} qualification {field} must match", errors)


def validate_server_arguments(
    profile: dict[str, Any], label: str, errors: list[str]
) -> None:
    transport = profile.get("transport", {})
    model = profile.get("model", {})
    server = profile.get("server", {})
    provider = profile.get("omp_provider", {})
    arguments = server.get("arguments", [])
    if not isinstance(arguments, list) or not all(isinstance(item, str) for item in arguments):
        require(False, f"{label}: server.arguments must be a string array", errors)
        return

    expected_values = {
        # The server binds every interface inside its own network namespace; Docker publishes
        # that port on the runtime host's loopback. A host-network bind is unreachable from the
        # operator on Docker Desktop, where "host" means the engine VM (omp-ninfer#15).
        "--host": "0.0.0.0",
        "--port": str(server.get("container_port")),
        "--model-id": model.get("public_id"),
        "--deployment-profile": server.get("deployment_profile"),
        "--max-context": str(provider.get("context_window")),
        "--session-checkpoint-dir": server.get("checkpoint_mount_target"),
    }
    for flag, expected in expected_values.items():
        require(isinstance(expected, str) and expected not in {"", "None"},
                f"{label}: cannot derive {flag} from structured profile fields", errors)
        require(arguments.count(flag) == 1 and argument_value(arguments, flag) == expected,
                f"{label}: {flag} must occur once and equal {expected}", errors)
    for flag in REQUIRED_TUNING_VALUES:
        value = argument_value(arguments, flag)
        require(arguments.count(flag) == 1 and isinstance(value, str) and bool(value),
                f"{label}: {flag} must occur once with a non-empty value", errors)
    for flag in REQUIRED_SERVER_FLAGS:
        require(arguments.count(flag) == 1, f"{label}: must include {flag} exactly once", errors)
    require("--api-key" not in arguments, f"{label}: must not embed an API key", errors)


# Flags the launcher derives from the release and profile identities rather than from the
# profile's tuning; the lifecycle tool passes their equivalents itself and excludes them from
# the configuration it hashes.
IDENTITY_FLAGS = frozenset({
    "--host", "--port", "--model-id", "--binary-sha256", "--artifact-sha256",
    "--config-sha256", "--deployment-profile", "--session-checkpoint-dir",
})


def tuning_arguments(arguments: list[str]) -> list[str]:
    """The profile's arguments minus the identity flags: the configuration that is hashed."""
    tuning: list[str] = []
    skip = 0
    for item in arguments:
        if skip:
            skip -= 1
            continue
        if item in IDENTITY_FLAGS:
            skip = 1
            continue
        tuning.append(item)
    return tuning


def configuration_identity(profile: dict[str, Any]) -> str:
    """SHA-256 of the configuration the public launcher runs, as the runtime fork's lifecycle
    tool (tools/lifecycle/ninfer_container.py, canonical_identity) computes it for the same
    configuration. The launcher refuses to start a container whose declared identity is not
    this value, and a ready release must record it - so the identity a stranger's server echoes
    names the configuration it is running, never one qualified elsewhere."""
    server = profile.get("server", {})
    canonical = {
        "bind_host": server.get("published_bind_host"),
        "api_key_configured": True,
        "args": tuning_arguments(server.get("arguments", [])),
        "deployment_profile": server.get("deployment_profile"),
        "model_id": profile.get("model", {}).get("public_id"),
        "port": server.get("published_port"),
        "request_log_configured": True,
        "checkpoint_configured": True,
        "checkpoint_mount_target": server.get("checkpoint_mount_target"),
        "checkpoint_seccomp_sha256": server.get("checkpoint_seccomp_sha256"),
        "restart_policy": server.get("restart_policy"),
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_profile_contract(
    profile: dict[str, Any],
    label: str,
    release: Any,
    model: dict[str, Any],
    public_model_id: Any,
    deployment_profile: Any,
    errors: list[str],
) -> None:
    require(profile.get("schema_version") == 1, f"{label}: schema_version must be 1", errors)
    require(profile.get("release") == release, f"{label}: release must match the manifest", errors)

    transport = profile.get("transport", {})
    require(transport.get("client_bind_host") == "127.0.0.1",
            f"{label}: client endpoint must bind loopback", errors)
    require(transport.get("runtime_bind_host") == "127.0.0.1",
            f"{label}: runtime endpoint must bind loopback", errors)
    require(transport.get("client_port") == transport.get("runtime_port") == 18089,
            f"{label}: loopback ports must both be 18089", errors)
    require(transport.get("silent_cloud_fallback") is False,
            f"{label}: silent cloud fallback must be disabled", errors)

    server = profile.get("server", {})
    require(server.get("deployment_profile") == deployment_profile,
            f"{label}: deployment_profile must match the manifest", errors)
    require(server.get("restart_policy") == "no", f"{label}: restart_policy must be no", errors)
    require(server.get("container_network_mode") == "bridge",
            f"{label}: container network mode must be bridge", errors)
    require(server.get("container_port") == 8080,
            f"{label}: container port must be 8080", errors)
    require(server.get("published_bind_host") == transport.get("runtime_bind_host") == "127.0.0.1",
            f"{label}: published port must bind the runtime host loopback", errors)
    require(server.get("published_port") == transport.get("runtime_port"),
            f"{label}: published port must be the transport's runtime port", errors)
    require(server.get("checkpoint_mount_target") == "/checkpoints",
            f"{label}: checkpoint mount target must be /checkpoints", errors)
    seccomp_path = server.get("checkpoint_seccomp_profile")
    require(seccomp_path == "examples/manual-tunnel/ninfer_io_uring_seccomp.json",
            f"{label}: checkpoint seccomp profile must be the repository-owned io_uring profile",
            errors)
    require(isinstance(server.get("checkpoint_seccomp_sha256"), str)
            and SHA256_RE.fullmatch(server.get("checkpoint_seccomp_sha256") or "") is not None,
            f"{label}: checkpoint_seccomp_sha256 must be a SHA-256", errors)
    validate_server_arguments(profile, label, errors)

    omp_provider = profile.get("omp_provider", {})
    require(omp_provider.get("api") == "openai-responses",
            f"{label}: OMP provider API must be openai-responses", errors)
    require(omp_provider.get("base_url") == "http://127.0.0.1:18089/v1",
            f"{label}: OMP provider must use the local loopback endpoint", errors)
    require(omp_provider.get("request_model_id") == public_model_id,
            f"{label}: OMP provider request model must match the manifest", errors)
    require(omp_provider.get("ninfer_stateful_responses") is True,
            f"{label}: OMP provider must enable NInfer stateful Responses", errors)

    profile_model = profile.get("model", {})
    require(profile_model.get("public_id") == public_model_id,
            f"{label}: model public_id must match the manifest", errors)
    require(profile_model.get("artifact_sha256") == model.get("artifact_sha256"),
            f"{label}: model hash must match the manifest", errors)
    require(profile_model.get("artifact_bytes") == model.get("artifact_bytes"),
            f"{label}: model bytes must match the manifest", errors)


def validate_markdown_links(root: Path, errors: list[str]) -> None:
    resolved_root = root.resolve()
    for document in sorted(root.rglob("*.md")):
        source = document.read_text(encoding="utf-8")
        targets = MARKDOWN_LINK_RE.findall(source) + MARKDOWN_REFERENCE_RE.findall(source)
        for raw_target in targets:
            target = raw_target.removeprefix("<").removesuffix(">")
            parsed = urlparse(target)
            if parsed.scheme or target.startswith(("#", "//")):
                continue
            relative = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not relative:
                continue
            linked = (document.parent / relative).resolve()
            require(linked.is_relative_to(resolved_root),
                    f"{document.relative_to(root)} link escapes repository: {target}", errors)
            if linked.is_relative_to(resolved_root):
                require(linked.exists(),
                        f"{document.relative_to(root)} has missing local link: {target}", errors)


def validate_public_text(root: Path, errors: list[str]) -> None:
    assets = root / "assets"
    documents = set(root.rglob("*.md"))
    documents.update(assets.glob("*.html"))
    documents.update(assets.glob("*.svg"))
    releases_root = root / "releases"
    if releases_root.is_dir():
        documents.update(releases_root.rglob("*.json"))
        documents.update(releases_root.rglob("*.SHA256SUMS"))
        documents.update(releases_root.rglob("*.jsonl"))
    # Dated receipts are published alongside the docs that cite them, and they are written from
    # host measurements, so they are the likeliest place for a hostname or a home directory to
    # reach the public repository. Scan them with the same rule as the prose.
    measurements = root / "docs" / "measurements"
    if measurements.is_dir():
        documents.update(measurements.rglob("*.json"))
    for document in sorted(documents):
        source = document.read_text(encoding="utf-8")
        for marker in PRIVATE_MARKERS:
            require(marker not in source,
                    f"{document.relative_to(root)} contains private marker {marker!r}", errors)


def validate(
    root: Path,
    require_ready: bool,
    require_installable: bool = False,
    product_release: str | None = None,
    check_pins: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    selected_release = resolve_product_release(root, product_release)
    manifest_path = root / "releases" / selected_release / "manifest.json"
    manifest = load_json(manifest_path)
    errors: list[str] = []
    # A clone whose checkout rewrote line endings (Git for Windows installs with
    # core.autocrlf=true) fails every hash in the chain at once; name that cause first, as one
    # actionable error, instead of leaving a reader with a page of mismatches (EXP-032). The
    # signature is exact: the file's CRLF->LF bytes hash to a value the chain records while its
    # actual bytes do not. Receipts checked in with CRLF hash as checked in and are not flagged.
    recorded = set()
    for name in ("manifest.json", "qualification.json", "compatibility.json"):
        candidate = manifest_path.parent / name
        if candidate.is_file():
            recorded.update(re.findall(r"[0-9a-f]{64}", candidate.read_text(encoding="utf-8", errors="replace")))
    rewritten = []
    for path in sorted(manifest_path.parent.rglob("*.json")):
        data = path.read_bytes()
        if b"\r\n" not in data or hashlib.sha256(data).hexdigest() in recorded:
            continue
        if hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest() in recorded:
            rewritten.append(str(path.relative_to(root)))
    if rewritten:
        errors.append(
            f"{len(rewritten)} release file(s) were rewritten to CRLF at checkout (git"
            " core.autocrlf), so their bytes no longer match the recorded hashes; clone a tag"
            " that carries the repository's .gitattributes, or re-clone with"
            f" core.autocrlf=false - first: {rewritten[0]}"
        )

    require(manifest.get("schema_version") == 1, "manifest schema_version must be 1", errors)
    release = manifest.get("release")
    require(release == selected_release,
            f"manifest release must match selected release {selected_release}", errors)
    status = manifest.get("status")
    require(status in {"draft", "candidate", "ready"},
            "manifest status must be draft, candidate, or ready", errors)
    pending_allowed = status == "draft" and not require_installable and not require_ready
    release_posture = (manifest.get("channel"), manifest.get("audience"))
    require(
        release_posture in {
            ("early-access", "invited-testers"),
            ("public", "public"),
        },
        "manifest channel and audience must form a recognized release posture",
        errors,
    )

    product = manifest.get("product", {})
    require(isinstance(product, dict), "manifest product must be an object", errors)
    profile_ref = product.get("profile") if isinstance(product, dict) else None
    require(isinstance(profile_ref, str), "manifest product.profile must be a path", errors)
    profile_path = (manifest_path.parent / profile_ref).resolve() if isinstance(profile_ref, str) else root
    require(profile_path.is_relative_to(root.resolve()), "manifest profile must stay inside the repository", errors)
    require(profile_path.is_file(), "manifest profile path must exist", errors)

    qualification_ref = manifest.get("qualification", {}).get("summary")
    require(isinstance(qualification_ref, str), "manifest qualification.summary must be a path", errors)
    qualification_path = (
        manifest_path.parent / qualification_ref
    ).resolve() if isinstance(qualification_ref, str) else root
    require(qualification_path.is_relative_to(root.resolve()),
            "manifest qualification summary must stay inside the repository", errors)
    if not pending_allowed:
        require(qualification_path.is_file(), "manifest qualification summary must exist", errors)

    profile = load_json(profile_path) if profile_path.is_file() else {}
    qualification = load_json(qualification_path) if qualification_path.is_file() else {}
    qualification_pending = pending_allowed and not qualification
    components = manifest.get("components", {})
    omp = components.get("omp", {})
    ninfer = components.get("ninfer", {})
    model = components.get("model", {})
    runtime = manifest.get("runtime_identity", {})
    manifest_qualification = manifest.get("qualification", {})

    expected_profile_id = product.get("primary_profile_id") if isinstance(product, dict) else None
    installation_mode = manifest.get("installation", {}).get("mode")
    require(isinstance(expected_profile_id, str) and profile.get("profile_id") == expected_profile_id,
            "profile_id must match manifest product.primary_profile_id", errors)
    require(isinstance(installation_mode, str)
            and profile.get("installation_mode") == installation_mode,
            "profile installation_mode must match manifest installation.mode", errors)
    validate_profile_contract(profile, "profile", release, model,
                              runtime.get("public_model_id"),
                              runtime.get("deployment_profile"), errors)
    profiles: list[tuple[str, dict[str, Any]]] = [("profile", profile)]

    profiles_dir = root / "profiles"
    if profiles_dir.is_dir():
        for extra_path in sorted(profiles_dir.glob("*.json")):
            if extra_path.resolve() == profile_path:
                continue
            try:
                extra_profile = load_json(extra_path)
            except ContractError as error:
                errors.append(str(error))
                continue
            validate_profile_contract(extra_profile, f"profiles/{extra_path.name}", release,
                                      model, runtime.get("public_model_id"),
                                      runtime.get("deployment_profile"), errors)
            profiles.append((f"profiles/{extra_path.name}", extra_profile))

    release_compatibility_path = manifest_path.parent / "compatibility.json"
    compatibility_path = (
        release_compatibility_path
        if release_compatibility_path.is_file()
        else root / "compatibility.json"
    )
    compatibility_matrix_path = (
        manifest_path.parent / "COMPATIBILITY.md"
        if release_compatibility_path.is_file()
        else root / "docs" / "COMPATIBILITY.md"
    )
    compatibility: dict[str, Any] = {}
    try:
        compatibility = load_authority(compatibility_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        errors.append(f"compatibility.json: {error}")
    if compatibility:
        root_compatibility_path = root / "compatibility.json"
        if release_compatibility_path.is_file() and root_compatibility_path.is_file():
            require(sha256_file(release_compatibility_path) == sha256_file(root_compatibility_path),
                    "root and release compatibility authorities must be byte-identical", errors)
            root_matrix_path = root / "docs" / "COMPATIBILITY.md"
            require(root_matrix_path.is_file()
                    and compatibility_matrix_path.read_bytes() == root_matrix_path.read_bytes(),
                    "root and release compatibility matrices must be byte-identical", errors)
        require(compatibility.get("product_release") == release,
                "compatibility product_release must match the manifest", errors)
        try:
            require(compatibility_matrix_path.read_text(encoding="utf-8")
                    == render_compatibility_matrix(compatibility),
                    "generated compatibility matrix is stale", errors)
        except OSError as error:
            errors.append(f"docs/COMPATIBILITY.md: {error}")
        composition = compatibility.get("composition", {})
        require_git_sha(composition.get("lifecycle_source_commit"),
                        "compatibility composition.lifecycle_source_commit", errors)
        require_git_sha(composition.get("qualification_source_commit"),
                        "compatibility composition.qualification_source_commit", errors)
        require_git_sha(composition.get("lifecycle_main_commit"),
                        "compatibility composition.lifecycle_main_commit", errors)
        require_git_sha(composition.get("lifecycle_main_tree"),
                        "compatibility composition.lifecycle_main_tree", errors)
        require_git_sha(composition.get("request_compatibility_source_commit"),
                        "compatibility composition.request_compatibility_source_commit", errors)
        require(compatibility.get("authority_id") == omp.get("compatibility_authority"),
                "OMP component must bind the checked-in compatibility authority", errors)
        require_sha(omp.get("compatibility_sha256"),
                    "components.omp.compatibility_sha256", errors)
        require(omp.get("compatibility_sha256") == sha256_file(compatibility_path),
                "OMP compatibility SHA-256 must match compatibility.json", errors)
        if omp.get("compatibility_url") is None:
            require(pending_allowed,
                    "components.omp.compatibility_url must bind the published authority", errors)
        else:
            require_product_raw_url(
                omp.get("compatibility_url"),
                "components.omp.compatibility_url",
                "compatibility.json",
                errors,
            )
        require(composition.get("lifecycle_source_commit") == omp.get("source_commit"),
                "OMP source commit must match compatibility composition", errors)
        require(composition.get("qualification_source_commit") == omp.get("qualification_commit"),
                "OMP qualification commit must match compatibility composition", errors)
        require(composition.get("lifecycle_main_commit") == omp.get("main_commit"),
                "OMP main commit must match compatibility composition", errors)
        require(composition.get("lifecycle_generated_lock_tree") == omp.get("source_tree"),
                "OMP source tree must match compatibility final tree", errors)
        primary_client = next(
            (item.get("client_distribution", {}) for item in compatibility.get("profiles", [])
             if item.get("id") == "windows-docker-local"),
            {},
        )
        require(primary_client.get("archive_sha256") == omp.get("artifact_sha256"),
                "OMP Windows artifact must match compatibility authority", errors)
        require(primary_client.get("binary_sha256") == omp.get("binary_sha256"),
                "OMP Windows binary must match compatibility authority", errors)
        require(primary_client.get("asset_url") == omp.get("artifact_url"),
                "OMP Windows asset URL must match compatibility authority", errors)
        for profile_item in compatibility.get("profiles", []):
            profile_id = profile_item.get("id", "<unknown>")
            profile_runtime = profile_item.get("runtime", {})
            require(profile_item.get("product_release") == release,
                    f"compatibility {profile_id} product release must match", errors)
            require(profile_runtime.get("image_reference") == ninfer.get("oci_reference"),
                    f"compatibility {profile_id} image must match the manifest", errors)
            require(profile_runtime.get("model_sha256") == model.get("artifact_sha256"),
                    f"compatibility {profile_id} model must match the manifest", errors)
            require(profile_runtime.get("configuration_sha256") == runtime.get("configuration_sha256"),
                    f"compatibility {profile_id} configuration must match the manifest", errors)
            require(profile_runtime.get("server_binary_sha256") == ninfer.get("server_binary_sha256"),
                    f"compatibility {profile_id} server must match the manifest", errors)
            client = profile_item.get("client_distribution", {})
            require_git_sha(client.get("source_commit"),
                            f"compatibility {profile_id} client source", errors)
            if client.get("archive_sha256") is not None:
                require_sha(client.get("archive_sha256"),
                            f"compatibility {profile_id} client archive", errors)

        primary_receipt_path = manifest_path.parent / "qualification" / "rtx5090.json"
        primary_receipts = [
            item.get("gpu_qualification", {}).get("receipt")
            for item in compatibility.get("profiles", [])
            if isinstance(item, dict)
        ]
        if not (pending_allowed and all(receipt is None for receipt in primary_receipts)):
            require(primary_receipt_path.is_file(),
                    "primary RTX 5090 qualification receipt must exist", errors)
            primary_receipt_hashes = {
                receipt.get("sha256")
                for receipt in primary_receipts
                if isinstance(receipt, dict)
            }
            require(len(primary_receipt_hashes) == 1
                    and all(isinstance(receipt, dict) for receipt in primary_receipts),
                    "compatibility profiles must share one RTX 5090 receipt hash", errors)
            if primary_receipt_path.is_file() and len(primary_receipt_hashes) == 1:
                require(sha256_file(primary_receipt_path) == next(iter(primary_receipt_hashes)),
                        "primary RTX 5090 qualification SHA-256 must match checked-in bytes", errors)

        if qualification:
            behavioral = qualification.get("composition", {}).get("behavioral_qualification", {})
            behavioral_ref = behavioral.get("repository_path")
            behavioral_path = (root / behavioral_ref).resolve() if isinstance(behavioral_ref, str) else root
            require(isinstance(behavioral_ref, str) and behavioral_path.is_relative_to(root.resolve())
                    and behavioral_path.is_file(),
                    "behavioral qualification receipt path must resolve inside the repository", errors)
            require_sha(behavioral.get("sha256"), "behavioral qualification SHA-256", errors)
            if behavioral_path.is_file() and isinstance(behavioral.get("sha256"), str):
                require(sha256_file(behavioral_path) == behavioral.get("sha256"),
                        "behavioral qualification SHA-256 must match checked-in bytes", errors)

    validate_ninfer_variants(
        root,
        release,
        components.get("ninfer_variants", []),
        compatibility,
        model.get("artifact_sha256"),
        errors,
        allow_pending=pending_allowed,
    )

    for key in ("upstream_commit", "source_commit"):
        require_git_sha(ninfer.get(key), f"components.ninfer.{key}", errors)
    require_git_sha(omp.get("upstream_commit"), "components.omp.upstream_commit", errors)
    require_git_sha(omp.get("source_commit"), "components.omp.source_commit", errors)
    require_git_sha(omp.get("qualification_commit"), "components.omp.qualification_commit", errors)
    require_git_sha(omp.get("main_commit"), "components.omp.main_commit", errors)
    require_git_sha(omp.get("source_tree"), "components.omp.source_tree", errors)
    omp_release_id = omp.get("release_id")
    omp_release_match = (
        OMP_RELEASE_ID_RE.fullmatch(omp_release_id)
        if isinstance(omp_release_id, str)
        else None
    )
    require(omp_release_match is not None,
            "components.omp.release_id must be a cross-platform preview or beta identity",
            errors)
    if omp_release_match is not None:
        omp_version = omp_release_match.group("version")
        require(omp.get("upstream_tag") == f"v{omp_version}",
                "OMP release ID version must match upstream_tag", errors)
        require(omp.get("distribution_version") == omp_release_id,
                "OMP distribution version must equal release_id", errors)
        require(omp.get("component_release_tag") == f"omp-{omp_release_id}",
                "OMP component tag must derive from release_id", errors)
    omp_platform = omp.get("platform")
    require(omp_platform == "windows-x64",
            "ready OMP primary platform must be windows-x64", errors)
    expected_omp_artifact_name = (
        f"omp-{omp_release_match.group('version')}-{omp_platform}.tar.gz"
        if omp_release_match is not None and isinstance(omp_platform, str)
        else None
    )
    require(omp.get("artifact_name") == expected_omp_artifact_name,
            "OMP artifact name must bind release version and primary platform", errors)
    require(omp.get("component_repository") == "https://github.com/alphastorm/homebrew-omp",
            "OMP component repository must be alphastorm/homebrew-omp", errors)
    require(omp.get("source_repository") == expected_omp_source_repository(release),
            "OMP source repository must match the release's public-source policy", errors)
    require(isinstance(omp.get("component_release_id"), int)
            and omp.get("component_release_id", 0) > 0,
            "OMP component_release_id must be positive", errors)
    require(isinstance(omp.get("artifact_release_id"), int)
            and omp.get("artifact_release_id", 0) > 0,
            "OMP artifact_release_id must be positive", errors)
    require(omp.get("component_release_id") == omp.get("artifact_release_id"),
            "OMP component and artifact release IDs must match", errors)
    require(isinstance(omp.get("artifact_asset_id"), int)
            and omp.get("artifact_asset_id", 0) > 0,
            "OMP artifact_asset_id must be positive", errors)
    require(isinstance(omp.get("artifact_published"), bool),
            "OMP artifact_published must be boolean", errors)
    require_sha(omp.get("artifact_sha256"), "components.omp.artifact_sha256", errors)
    require_sha(omp.get("binary_sha256"), "components.omp.binary_sha256", errors)
    require(isinstance(omp.get("artifact_bytes"), int) and omp.get("artifact_bytes", 0) > 0,
            "OMP artifact_bytes must be positive", errors)
    omp_artifact_url = omp.get("artifact_url")
    require_https(omp_artifact_url, "components.omp.artifact_url", errors, nullable=True)
    if isinstance(omp_artifact_url, str):
        parsed_omp_url = urlparse(omp_artifact_url)
        omp_asset_path_match = OMP_ASSET_DOWNLOAD_RE.fullmatch(parsed_omp_url.path)
        require(
            parsed_omp_url.scheme == "https"
            and parsed_omp_url.netloc == "github.com"
            and omp_asset_path_match is not None
            and omp_asset_path_match.group("tag") == omp.get("component_release_tag")
            and omp_asset_path_match.group("name") == omp.get("artifact_name")
            and parsed_omp_url.params == ""
            and parsed_omp_url.query == ""
            and parsed_omp_url.fragment == "",
            "OMP artifact URL must bind the public component tag and artifact name",
            errors,
        )
    for key in ("source_archive_sha256", "server_binary_sha256"):
        require_sha(ninfer.get(key), f"components.ninfer.{key}", errors,
                    nullable=pending_allowed)
    require(isinstance(ninfer.get("release_tag"), str)
            and NINFER_RELEASE_TAG_RE.fullmatch(ninfer["release_tag"]) is not None,
            "components.ninfer.release_tag is invalid", errors)
    require_sha(model.get("artifact_sha256"), "components.model.artifact_sha256", errors)
    require_sha(runtime.get("configuration_sha256"),
                "runtime_identity.configuration_sha256", errors,
                nullable=pending_allowed)
    require_https(model.get("repository"), "components.model.repository", errors)
    require_git_sha(model.get("revision"), "components.model.revision", errors)
    require_https(model.get("artifact_url"), "components.model.artifact_url", errors)
    require(model.get("artifact_name") == "qwen3_8_27b.ninfer",
            "model artifact name must be qwen3_8_27b.ninfer", errors)
    expected_model_url = (
        f"{model.get('repository')}/resolve/{model.get('revision')}/{model.get('artifact_name')}"
    )
    require(model.get("artifact_url") == expected_model_url,
            "model artifact URL must bind repository, revision, and name", errors)
    require(model.get("artifact_bytes") == 18210531328,
            "model artifact size must be 18210531328 bytes", errors)

    require(model.get("artifact_sha256") == profile.get("model", {}).get("artifact_sha256"),
            "profile and manifest model hashes must match", errors)
    require(qualification_pending or model.get("artifact_sha256") == qualification.get("runtime_identity", {}).get("model_artifact_sha256"),
            "qualification and manifest model hashes must match", errors)
    require(qualification_pending or ninfer.get("source_commit") == qualification.get("runtime_identity", {}).get("release_source_commit"),
            "qualification and manifest NInfer source commits must match", errors)
    require(qualification_pending or ninfer.get("server_binary_sha256") == qualification.get("runtime_identity", {}).get("release_server_binary_sha256"),
            "qualification and manifest NInfer binary hashes must match", errors)
    local_packaging = qualification.get("composition", {}).get("local_release_packaging", {})
    require(qualification_pending or local_packaging.get("status") == "passed",
            "qualification must record passing local release packaging", errors)
    require(qualification_pending or isinstance(local_packaging.get("published"), bool),
            "qualification local release packaging must record publication state", errors)
    require(qualification_pending or local_packaging.get("release_source_commit") == ninfer.get("source_commit"),
            "local packaging and manifest NInfer source commits must match", errors)
    require(qualification_pending or local_packaging.get("release_server_binary_sha256") == ninfer.get("server_binary_sha256"),
            "local packaging and manifest NInfer binary hashes must match", errors)
    require(qualification_pending or ninfer.get("oci_manifest_digest") == local_packaging.get("oci_manifest_digest"),
            "local packaging and manifest OCI digests must match", errors)
    require(qualification_pending or ninfer.get("sbom_sha256") == local_packaging.get("sbom_sha256"),
            "local packaging and manifest SBOM hashes must match", errors)
    oci_manifest_digest = ninfer.get("oci_manifest_digest")
    if oci_manifest_digest is None:
        require(pending_allowed, "NInfer OCI manifest digest is absent", errors)
    else:
        require(isinstance(oci_manifest_digest, str)
                and OCI_DIGEST_RE.fullmatch(oci_manifest_digest) is not None,
                "NInfer OCI manifest digest must be sha256:<64 hex>", errors)
    require_sha(ninfer.get("sbom_sha256"), "components.ninfer.sbom_sha256", errors,
                nullable=pending_allowed)
    require(qualification_pending or runtime.get("configuration_sha256") == qualification.get("runtime_identity", {}).get("configuration_sha256"),
            "qualification and manifest configuration hashes must match", errors)
    require(qualification_pending or qualification.get("release") == release,
            "qualification release must match manifest", errors)
    require(qualification_pending or qualification.get("status") == "runtime-release-eligible",
            "qualification must record runtime-release-eligible", errors)
    require(qualification_pending or qualification.get("publication_authorized") is False,
            "checked-in qualification must not grant publication authority", errors)
    external_acceptance = qualification.get("composition", {}).get("external_installation_acceptance", {})
    acceptance_ref = external_acceptance.get("repository_path")
    acceptance_path = (
        (root / acceptance_ref).resolve()
        if isinstance(acceptance_ref, str)
        else root
    )
    acceptance_inside_repository = (
        isinstance(acceptance_ref, str)
        and acceptance_path.is_relative_to(root.resolve())
    )
    acceptance_subject: dict[str, Any] = {}
    if isinstance(acceptance_ref, str) and (
        qualification.get("external_installation_qualified") is True
        or ga_release(release)
    ):
        require(acceptance_inside_repository,
                "external acceptance path must stay inside the repository", errors)
        require(acceptance_path.is_file(), "external acceptance receipt must exist", errors)
        if acceptance_inside_repository and acceptance_path.is_file():
            acceptance_subject = load_json(acceptance_path)
            if ga_release(release):
                require(
                    acceptance_subject.get("release") == release,
                    "external acceptance receipt release must match manifest release",
                    errors,
                )
                require(
                    acceptance_subject.get("status") == "passed",
                    "external acceptance receipt status must be passed",
                    errors,
                )
                require(
                    acceptance_subject.get("compatibility_authority")
                    == omp.get("compatibility_authority"),
                    "external acceptance receipt compatibility_authority must match manifest",
                    errors,
                )
                require(
                    acceptance_subject.get("compatibility_sha256")
                    == omp.get("compatibility_sha256"),
                    "external acceptance receipt compatibility_sha256 must match manifest",
                    errors,
                )

    if qualification.get("external_installation_qualified") is True:
        require(external_acceptance.get("status") == "passed",
                "external installation acceptance must pass", errors)
        require(isinstance(acceptance_ref, str),
                "external acceptance repository_path must be present", errors)
        require_sha(external_acceptance.get("sha256"),
                    "external acceptance SHA-256", errors)
        if (
            acceptance_inside_repository
            and acceptance_path.is_file()
            and isinstance(external_acceptance.get("sha256"), str)
        ):
            require(sha256_file(acceptance_path) == external_acceptance.get("sha256"),
                    "external acceptance SHA-256 must match receipt bytes", errors)
        platform_rows = acceptance_subject.get("platform_receipts", [])
        require(isinstance(platform_rows, list),
                "external acceptance platform_receipts must be an array", errors)
        platform_hashes = {
            row.get("profile"): row.get("sha256")
            for row in platform_rows
            if isinstance(row, dict)
        } if isinstance(platform_rows, list) else {}
        expected_platform_hashes = {
            profile_item.get("id"): profile_item.get("acceptance_receipt", {}).get("sha256")
            for profile_item in compatibility.get("profiles", [])
            if isinstance(profile_item, dict)
        }
        require(len(platform_hashes) == len(platform_rows),
                "external acceptance platform receipts are duplicated or malformed", errors)
        require(platform_hashes == expected_platform_hashes,
                "external acceptance platform receipt hashes must match compatibility", errors)
        for profile_id, digest in platform_hashes.items():
            require_sha(digest, f"external acceptance {profile_id} SHA-256", errors)
        require_product_raw_url(
            external_acceptance.get("public_url"),
            "external acceptance public_url",
            str(external_acceptance.get("repository_path")),
            errors,
        )
        require(external_acceptance.get("component_release_tag") == omp.get("component_release_tag"),
                "external acceptance component tag must match manifest", errors)
        require(external_acceptance.get("windows_asset_sha256") == omp.get("artifact_sha256"),
                "external acceptance Windows archive must match manifest", errors)
        require(external_acceptance.get("windows_binary_sha256") == omp.get("binary_sha256"),
                "external acceptance Windows binary must match manifest", errors)
        require(external_acceptance.get("compatibility_authority") == omp.get("compatibility_authority"),
                "external acceptance compatibility authority must match manifest", errors)
        require(external_acceptance.get("compatibility_sha256") == omp.get("compatibility_sha256"),
                "external acceptance compatibility SHA-256 must match manifest", errors)
        for key in ("tools", "vision", "stateful_resume", "fail_closed", "runtime_incumbent_restored"):
            require(external_acceptance.get(key) is True,
                    f"external acceptance must pass {key}", errors)

    expected_summary_sha = manifest_qualification.get("summary_sha256")
    require_sha(expected_summary_sha, "qualification.summary_sha256", errors, nullable=True)
    if isinstance(expected_summary_sha, str) and qualification_path.is_file():
        require(sha256_file(qualification_path) == expected_summary_sha,
                "qualification.summary_sha256 does not match qualification.json", errors)

    for label, document in (("manifest", manifest), ("profile", profile), ("qualification", qualification)):
        for text in walk_strings(document):
            for marker in PRIVATE_MARKERS:
                require(marker not in text, f"{label} contains private marker {marker!r}", errors)
            require(PLACEHOLDER_RE.search(text) is None,
                    f"{label} contains placeholder text: {text!r}", errors)

    publication = manifest.get("publication", {})
    blockers = publication.get("blockers")
    require(isinstance(blockers, list), "publication.blockers must be an array", errors)
    blocker_items = blockers if isinstance(blockers, list) else []
    require(publication.get("authorized") is False,
            "checked-in candidate manifest must not grant publication authority", errors)

    if status in {"draft", "candidate"}:
        require(bool(blocker_items),
                f"a {status} manifest must enumerate publication blockers", errors)

    if require_installable:
        require(status in {"candidate", "ready"},
                "release manifest is not installable", errors)

    if status in {"candidate", "ready"} or require_installable or require_ready:
        installable_values = {
            "components.omp.distribution_version": omp.get("distribution_version"),
            "components.omp.platform": omp.get("platform"),
            "components.omp.source_commit": omp.get("source_commit"),
            "components.omp.qualification_commit": omp.get("qualification_commit"),
            "components.omp.main_commit": omp.get("main_commit"),
            "components.omp.source_tree": omp.get("source_tree"),
            "components.omp.component_release_tag": omp.get("component_release_tag"),
            "components.omp.component_release_id": omp.get("component_release_id"),
            "components.omp.artifact_name": omp.get("artifact_name"),
            "components.omp.artifact_url": omp.get("artifact_url"),
            "components.omp.artifact_release_id": omp.get("artifact_release_id"),
            "components.omp.artifact_asset_id": omp.get("artifact_asset_id"),
            "components.omp.artifact_published": omp.get("artifact_published"),
            "components.omp.artifact_bytes": omp.get("artifact_bytes"),
            "components.omp.artifact_sha256": omp.get("artifact_sha256"),
            "components.omp.binary_sha256": omp.get("binary_sha256"),
            "components.omp.compatibility_sha256": omp.get("compatibility_sha256"),
            "components.ninfer.oci_reference": ninfer.get("oci_reference"),
            "components.ninfer.oci_manifest_digest": ninfer.get("oci_manifest_digest"),
            "components.ninfer.sbom_url": ninfer.get("sbom_url"),
            "components.ninfer.sbom_sha256": ninfer.get("sbom_sha256"),
        }
        for label, value in installable_values.items():
            require(value is not None, f"installable release requires {label}", errors)
        require(omp.get("artifact_published") is True,
                "installable release requires a published OMP artifact", errors)
        require(local_packaging.get("published") is True,
                "installable release requires published NInfer packaging", errors)
        require(isinstance(ninfer.get("oci_reference"), str)
                and "@sha256:" in ninfer.get("oci_reference", ""),
                "ready NInfer OCI reference must be digest-pinned", errors)
        oci_repository = ninfer.get("oci_repository", "ghcr.io/alphastorm/ninfer")
        require(oci_repository in {
                    "ghcr.io/alphastorm/ninfer",
                    "ghcr.io/alphastorm/ninfer-runtime",
                },
                "NInfer OCI repository is not an approved public runtime repository", errors)
        require(ninfer.get("oci_reference")
                == f"{oci_repository}@{ninfer.get('oci_manifest_digest')}",
                "NInfer OCI reference must exactly bind its manifest digest", errors)
        require_https(ninfer.get("sbom_url"), "components.ninfer.sbom_url", errors, nullable=True)

    if status == "candidate":
        require(any(isinstance(item, str) and "external-install" in item.lower()
                    for item in blocker_items),
                "candidate manifest must retain the external-install blocker", errors)
        require(manifest_qualification.get("external_installation_passed") is False,
                "candidate manifest must not claim external installation passed", errors)
        require(qualification.get("external_installation_qualified") is False,
                "candidate qualification must not claim external installation passed", errors)

    if status == "ready" or require_ready:
        require(status == "ready", "release manifest is not ready", errors)
        require(expected_summary_sha is not None,
                "ready release requires qualification.summary_sha256", errors)
        require(manifest_qualification.get("public_url") is not None,
                "ready release requires qualification.public_url", errors)
        require_product_raw_url(
            manifest_qualification.get("public_url"),
            "qualification.public_url",
            f"releases/{release}/{manifest_qualification.get('summary')}",
            errors,
        )
        require(manifest_qualification.get("external_installation_passed") is True,
                "ready release requires a passing external installation", errors)
        require(qualification.get("external_installation_qualified") is True,
                "ready qualification must record the passing external installation", errors)
        require(blocker_items == [], "ready release must have no publication blockers", errors)

        if ga_release(release):
            validate_exact_lane_set(manifest, compatibility, qualification, errors)
            validate_ready_state_consistency(
                manifest, compatibility, qualification, errors
            )
            validate_ga_evidence_bindings(
                release, manifest, compatibility, qualification, profiles, errors
            )
            if check_pins:
                validate_pinned_evidence(root, manifest, compatibility, qualification, errors)

    validate_markdown_links(root, errors)
    validate_public_text(root, errors)

    return manifest, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--release", help="product release directory; defaults to compatibility.json")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--require-installable", action="store_true")
    mode.add_argument("--require-ready", action="store_true")
    parser.add_argument("--check-pins", action="store_true",
                        help="with --require-ready: every pinned raw evidence URL whose commit is "
                             "in local git history must serve exactly its recorded SHA-256 "
                             "(the final gate of the pin dance; needs full history)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.check_pins and not args.require_ready:
        parser.error("--check-pins requires --require-ready")

    try:
        manifest, errors = validate(
            args.root.resolve(),
            args.require_ready,
            args.require_installable,
            args.release,
            check_pins=args.check_pins,
        )
    except ContractError as error:
        errors = [str(error)]
        manifest = {}

    result = {
        "release": manifest.get("release"),
        "status": manifest.get("status"),
        "valid": not errors,
        "errors": errors,
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
    else:
        print(f"valid {result['release']} manifest ({result['status']})")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
