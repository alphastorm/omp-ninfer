"""The shared identity projection for staged and promoted client profiles."""

from __future__ import annotations

PROFILE_ARGUMENTS = (("--binary-sha256", ("components", "ninfer", "server_binary_sha256")),
                     ("--artifact-sha256", ("components", "model", "artifact_sha256")),
                     ("--config-sha256", ("runtime_identity", "configuration_sha256")),
                     ("--deployment-profile", ("runtime_identity", "deployment_profile")))
CLIENT_ARCHIVE_KEYS = ("component_release_tag", "asset_url", "asset_sha256", "binary_sha256")


def stamp_profile(profile: dict, release: str, manifest: dict, clients: dict) -> None:
    """Use the same identity projection for staged snapshots and their promoted copies."""
    profile["release"] = release
    model = manifest["components"]["model"]
    profile["model"].update(artifact_sha256=model["artifact_sha256"],
                            artifact_bytes=model["artifact_bytes"])
    profile["server"]["deployment_profile"] = manifest["runtime_identity"]["deployment_profile"]
    arguments = profile["server"]["arguments"]
    for flag, keys in PROFILE_ARGUMENTS:
        value = manifest
        for key in keys:
            value = value[key]
        arguments[arguments.index(flag) + 1] = value
    omp = manifest["components"]["omp"]
    client = profile.get("client", {})
    if omp.get("distribution_kind") == "upstream-release":
        compatibility_id = {"manual-ssh-tunnel": "darwin-remote-ssh",
                            "native-windows-docker-local": "windows-docker-local"}[
                                profile["installation_mode"]]
        profile["client"] = dict(clients[compatibility_id])
        if profile.get("status") == "candidate":
            profile.pop("status")
    elif any(key in client for key in CLIENT_ARCHIVE_KEYS):
        client["component_release_tag"] = omp["component_release_tag"]
        client["asset_url"] = omp["artifact_url"]
        client["asset_sha256"] = omp["artifact_sha256"]
        client["binary_sha256"] = omp["binary_sha256"]
