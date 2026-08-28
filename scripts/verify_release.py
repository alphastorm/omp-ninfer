#!/usr/bin/env python3
"""Validate the OMP NInfer release manifest and its bound profile/qualification."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_compatibility import (  # pyright: ignore[reportMissingImports]
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
OMP_ASSET_DOWNLOAD_RE = re.compile(
    r"^/alphastorm/homebrew-omp/releases/download/(?P<tag>[^/]+)/(?P<name>[^/]+)$"
)
PRIVATE_MARKERS = (
    "/Users/",
    "/home/",
    "C:\\Users\\",
    "nyc-pc",
    "sf-pc",
    "ALPHA-DESKTOP",
    "ALPHA-NG",
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


def walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for child in value.values() for item in walk_strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in walk_strings(child)]
    return []


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
        "--host": transport.get("runtime_bind_host"),
        "--port": str(transport.get("runtime_port")),
        "--model-id": model.get("public_id"),
        "--deployment-profile": server.get("deployment_profile"),
        "--max-context": str(provider.get("context_window")),
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


def validate_profile_contract(
    profile: dict[str, Any],
    label: str,
    release: Any,
    model: dict[str, Any],
    public_model_id: Any,
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
    require(server.get("restart_policy") == "no", f"{label}: restart_policy must be no", errors)
    require(server.get("container_network_mode") == "host",
            f"{label}: container network mode must be host", errors)
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
) -> tuple[dict[str, Any], list[str]]:
    selected_release = resolve_product_release(root, product_release)
    manifest_path = root / "releases" / selected_release / "manifest.json"
    manifest = load_json(manifest_path)
    errors: list[str] = []

    require(manifest.get("schema_version") == 1, "manifest schema_version must be 1", errors)
    release = manifest.get("release")
    require(release == selected_release,
            f"manifest release must match selected release {selected_release}", errors)
    status = manifest.get("status")
    require(status in {"draft", "candidate", "ready"},
            "manifest status must be draft, candidate, or ready", errors)
    require(manifest.get("channel") == "early-access", "manifest channel must be early-access", errors)
    require(manifest.get("audience") == "invited-testers", "manifest audience must be invited-testers", errors)

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
    require(qualification_path.is_file(), "manifest qualification summary must exist", errors)

    profile = load_json(profile_path) if profile_path.is_file() else {}
    qualification = load_json(qualification_path) if qualification_path.is_file() else {}
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
                              runtime.get("public_model_id"), errors)

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
                                      model, runtime.get("public_model_id"), errors)

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
    require(omp.get("source_repository") == "https://github.com/alphastorm/omp-monorepo",
            "OMP source repository must be alphastorm/omp-monorepo", errors)
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
        require_sha(ninfer.get(key), f"components.ninfer.{key}", errors)
    require_sha(model.get("artifact_sha256"), "components.model.artifact_sha256", errors)
    require_sha(runtime.get("configuration_sha256"),
                "runtime_identity.configuration_sha256", errors)
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
    require(model.get("artifact_sha256") == qualification.get("runtime_identity", {}).get("model_artifact_sha256"),
            "qualification and manifest model hashes must match", errors)
    require(ninfer.get("source_commit") == qualification.get("runtime_identity", {}).get("release_source_commit"),
            "qualification and manifest NInfer source commits must match", errors)
    require(ninfer.get("server_binary_sha256") == qualification.get("runtime_identity", {}).get("release_server_binary_sha256"),
            "qualification and manifest NInfer binary hashes must match", errors)
    local_packaging = qualification.get("composition", {}).get("local_release_packaging", {})
    require(local_packaging.get("status") == "passed",
            "qualification must record passing local release packaging", errors)
    require(isinstance(local_packaging.get("published"), bool),
            "qualification local release packaging must record publication state", errors)
    require(local_packaging.get("release_source_commit") == ninfer.get("source_commit"),
            "local packaging and manifest NInfer source commits must match", errors)
    require(local_packaging.get("release_server_binary_sha256") == ninfer.get("server_binary_sha256"),
            "local packaging and manifest NInfer binary hashes must match", errors)
    require(ninfer.get("oci_manifest_digest") == local_packaging.get("oci_manifest_digest"),
            "local packaging and manifest OCI digests must match", errors)
    require(ninfer.get("sbom_sha256") == local_packaging.get("sbom_sha256"),
            "local packaging and manifest SBOM hashes must match", errors)
    require(isinstance(ninfer.get("oci_manifest_digest"), str)
            and OCI_DIGEST_RE.fullmatch(ninfer.get("oci_manifest_digest", "")) is not None,
            "NInfer OCI manifest digest must be sha256:<64 hex>", errors)
    require_sha(ninfer.get("sbom_sha256"), "components.ninfer.sbom_sha256", errors)
    require(runtime.get("configuration_sha256") == qualification.get("runtime_identity", {}).get("configuration_sha256"),
            "qualification and manifest configuration hashes must match", errors)
    require(qualification.get("release") == release, "qualification release must match manifest", errors)
    require(qualification.get("status") == "runtime-release-eligible",
            "qualification must record runtime-release-eligible", errors)
    require(qualification.get("publication_authorized") is False,
            "checked-in qualification must not grant publication authority", errors)
    external_acceptance = qualification.get("composition", {}).get("external_installation_acceptance", {})
    if qualification.get("external_installation_qualified") is True:
        require(external_acceptance.get("status") == "passed",
                "external installation acceptance must pass", errors)
        acceptance_ref = external_acceptance.get("repository_path")
        require(isinstance(acceptance_ref, str),
                "external acceptance repository_path must be present", errors)
        acceptance_path = (root / acceptance_ref).resolve() if isinstance(acceptance_ref, str) else root
        require(acceptance_path.is_relative_to(root.resolve()),
                "external acceptance path must stay inside the repository", errors)
        require(acceptance_path.is_file(), "external acceptance receipt must exist", errors)
        require_sha(external_acceptance.get("sha256"),
                    "external acceptance SHA-256", errors)
        if acceptance_path.is_file() and isinstance(external_acceptance.get("sha256"), str):
            require(sha256_file(acceptance_path) == external_acceptance.get("sha256"),
                    "external acceptance SHA-256 must match receipt bytes", errors)
        require_https(external_acceptance.get("public_url"),
                      "external acceptance public_url", errors)
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
        require(ninfer.get("oci_reference")
                == f"ghcr.io/alphastorm/ninfer@{ninfer.get('oci_manifest_digest')}",
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
        require_https(manifest_qualification.get("public_url"),
                      "qualification.public_url", errors, nullable=True)
        require(manifest_qualification.get("external_installation_passed") is True,
                "ready release requires a passing external installation", errors)
        require(qualification.get("external_installation_qualified") is True,
                "ready qualification must record the passing external installation", errors)
        require(blocker_items == [], "ready release must have no publication blockers", errors)

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
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        manifest, errors = validate(
            args.root.resolve(),
            args.require_ready,
            args.require_installable,
            args.release,
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
