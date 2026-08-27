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

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
OCI_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
OMP_RELEASE_ID_RE = re.compile(
    r"^(?P<version>[0-9]+\.[0-9]+\.[0-9]+)-(?P<identity>[0-9a-f]{64})$"
)
OMP_ASSET_PATH_RE = re.compile(
    r"^/repos/alphastorm/homebrew-omp/releases/assets/[1-9][0-9]*$"
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
) -> tuple[dict[str, Any], list[str]]:
    manifest_path = root / "releases" / "v0.1.0-beta.1" / "manifest.json"
    manifest = load_json(manifest_path)
    errors: list[str] = []

    require(manifest.get("schema_version") == 1, "manifest schema_version must be 1", errors)
    release = manifest.get("release")
    require(release == "v0.1.0-beta.1", "manifest release must be v0.1.0-beta.1", errors)
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

    require(profile.get("schema_version") == 1, "profile schema_version must be 1", errors)
    require(profile.get("release") == release, "profile release must match manifest release", errors)
    require(profile.get("profile_id") == "qwen38-rtx5090-manual-tunnel",
            "profile_id must be qwen38-rtx5090-manual-tunnel", errors)
    require(profile.get("installation_mode") == "manual-ssh-tunnel",
            "profile installation_mode must be manual-ssh-tunnel", errors)

    transport = profile.get("transport", {})
    require(transport.get("client_bind_host") == "127.0.0.1",
            "client tunnel endpoint must bind loopback", errors)
    require(transport.get("runtime_bind_host") == "127.0.0.1",
            "runtime endpoint must bind loopback", errors)
    require(transport.get("client_port") == transport.get("runtime_port") == 18089,
            "profile tunnel ports must both be 18089", errors)
    require(transport.get("silent_cloud_fallback") is False,
            "profile must disable silent cloud fallback", errors)

    server = profile.get("server", {})
    arguments = server.get("arguments", [])
    require(isinstance(arguments, list) and all(isinstance(item, str) for item in arguments),
            "profile server.arguments must be a string array", errors)
    require(server.get("restart_policy") == "no", "profile restart_policy must be no", errors)
    require(server.get("container_network_mode") == "host",
            "profile container network mode must be host", errors)
    required_values = {
        "--host": "127.0.0.1",
        "--port": "18089",
        "--model-id": "q38-ninfer",
        "--deployment-profile": "qwen38-5090-v0.1.0",
        "--max-context": "131072",
        "--kv-capacity": "auto",
        "--prefill-chunk": "1024",
        "--kv-dtype": "bf16",
        "--max-concurrency": "1",
        "--spec": "mtp",
        "--draft-tokens": "3",
    }
    for flag, expected in required_values.items():
        require(argument_value(arguments, flag) == expected,
                f"profile {flag} must equal {expected}", errors)
    for flag in ("--lm-head-draft", "--vision", "--preserve-thinking"):
        require(flag in arguments, f"profile must include {flag}", errors)
    require("--api-key" not in arguments, "profile must not embed an API key", errors)

    omp_provider = profile.get("omp_provider", {})
    require(omp_provider.get("api") == "openai-responses",
            "OMP provider API must be openai-responses", errors)
    require(omp_provider.get("base_url") == "http://127.0.0.1:18089/v1",
            "OMP provider must use the local tunnel endpoint", errors)
    require(omp_provider.get("request_model_id") == "q38-ninfer",
            "OMP provider request model must be q38-ninfer", errors)
    require(omp_provider.get("ninfer_stateful_responses") is True,
            "OMP provider must enable NInfer stateful Responses", errors)

    components = manifest.get("components", {})
    omp = components.get("omp", {})
    ninfer = components.get("ninfer", {})
    model = components.get("model", {})
    runtime = manifest.get("runtime_identity", {})
    manifest_qualification = manifest.get("qualification", {})

    for key in ("upstream_commit", "source_commit"):
        require_git_sha(ninfer.get(key), f"components.ninfer.{key}", errors)
    require_git_sha(omp.get("upstream_commit"), "components.omp.upstream_commit", errors)
    require_git_sha(omp.get("source_commit"), "components.omp.source_commit", errors)
    omp_release_id = omp.get("release_id")
    omp_release_match = (
        OMP_RELEASE_ID_RE.fullmatch(omp_release_id)
        if isinstance(omp_release_id, str)
        else None
    )
    require(omp_release_match is not None,
            "components.omp.release_id must bind a semantic version and 64-hex identity", errors)
    if omp_release_match is not None:
        omp_version = omp_release_match.group("version")
        omp_identity = omp_release_match.group("identity")
        expected_distribution_version = f"{omp_version}-{omp_identity[:8]}"
        require(omp.get("upstream_tag") == f"v{omp_version}",
                "OMP release ID version must match upstream_tag", errors)
        require(omp.get("distribution_version") == expected_distribution_version,
                "OMP distribution version must derive from release_id", errors)
    omp_distribution_version = omp.get("distribution_version")
    expected_omp_artifact_name = (
        f"omp-{omp_distribution_version}-darwin-arm64.tar.gz"
        if isinstance(omp_distribution_version, str)
        else None
    )
    require(omp.get("artifact_name") == expected_omp_artifact_name,
            "OMP artifact name must bind distribution_version and darwin-arm64", errors)
    require_sha(omp.get("artifact_sha256"), "components.omp.artifact_sha256", errors)
    require(isinstance(omp.get("artifact_bytes"), int) and omp.get("artifact_bytes", 0) > 0,
            "OMP artifact_bytes must be positive", errors)
    require(omp.get("homebrew_repository") == "https://github.com/alphastorm/homebrew-omp",
            "OMP Homebrew repository must be alphastorm/homebrew-omp", errors)
    require(omp.get("homebrew_cask") == "omp-beta",
            "OMP Homebrew cask must be omp-beta", errors)
    omp_artifact_url = omp.get("artifact_url")
    require_https(omp_artifact_url, "components.omp.artifact_url", errors, nullable=True)
    if isinstance(omp_artifact_url, str):
        parsed_omp_url = urlparse(omp_artifact_url)
        require(
            parsed_omp_url.scheme == "https"
            and parsed_omp_url.netloc == "api.github.com"
            and OMP_ASSET_PATH_RE.fullmatch(parsed_omp_url.path) is not None
            and parsed_omp_url.params == ""
            and parsed_omp_url.query == ""
            and parsed_omp_url.fragment == omp.get("artifact_name"),
            "OMP artifact URL must bind the private Homebrew release asset and artifact name",
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
    require(runtime.get("configuration_sha256") == qualification.get("runtime_identity", {}).get("configuration_sha256"),
            "qualification and manifest configuration hashes must match", errors)
    require(qualification.get("release") == release, "qualification release must match manifest", errors)
    require(qualification.get("status") == "runtime-release-eligible",
            "qualification must record runtime-release-eligible", errors)
    require(qualification.get("publication_authorized") is False,
            "checked-in qualification must not grant publication authority", errors)

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
            "components.omp.source_commit": omp.get("source_commit"),
            "components.omp.artifact_name": omp.get("artifact_name"),
            "components.omp.artifact_url": omp.get("artifact_url"),
            "components.omp.artifact_bytes": omp.get("artifact_bytes"),
            "components.omp.artifact_sha256": omp.get("artifact_sha256"),
            "components.omp.homebrew_cask_revision": omp.get("homebrew_cask_revision"),
            "components.ninfer.oci_reference": ninfer.get("oci_reference"),
            "components.ninfer.oci_manifest_digest": ninfer.get("oci_manifest_digest"),
            "components.ninfer.sbom_url": ninfer.get("sbom_url"),
            "components.ninfer.sbom_sha256": ninfer.get("sbom_sha256"),
        }
        for label, value in installable_values.items():
            require(value is not None, f"installable release requires {label}", errors)
        require_git_sha(omp.get("homebrew_cask_revision"),
                        "components.omp.homebrew_cask_revision", errors, nullable=True)
        require(isinstance(ninfer.get("oci_reference"), str)
                and "@sha256:" in ninfer.get("oci_reference", ""),
                "ready NInfer OCI reference must be digest-pinned", errors)
        require(isinstance(ninfer.get("oci_manifest_digest"), str)
                and OCI_DIGEST_RE.fullmatch(ninfer.get("oci_manifest_digest", "")) is not None,
                "installable NInfer OCI manifest digest must be sha256:<64 hex>", errors)
        require(ninfer.get("oci_reference")
                == f"ghcr.io/alphastorm/ninfer@{ninfer.get('oci_manifest_digest')}",
                "NInfer OCI reference must exactly bind its manifest digest", errors)
        require_https(ninfer.get("sbom_url"), "components.ninfer.sbom_url", errors, nullable=True)
        require_sha(ninfer.get("sbom_sha256"), "components.ninfer.sbom_sha256", errors, nullable=True)

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
