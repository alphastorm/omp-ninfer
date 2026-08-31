#!/usr/bin/env python3
"""Render the public client support matrix from compatibility.json."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

PROFILE_IDS = (
    "darwin-remote-ssh",
    "windows-docker-local",
    "linux-docker-local",
)
RUNTIME_VARIANT_IDS = (
    "rtx3090-windows-native",
    "rtx4090-windows-native",
)
STATUSES = {"qualified", "preview", "blocked", "unsupported"}
TRANSPORTS = {"ssh-loopback", "local-loopback"}
COMMANDS = {
    "doctor",
    "plan",
    "install",
    "status",
    "benchmark",
    "checkpoint",
    "rollback",
    "support-bundle",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_authority(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "compatibility authority must be an object")
    require(value.get("schema_version") == 1, "unsupported compatibility schema")
    require(isinstance(value.get("authority_id"), str) and value["authority_id"],
            "compatibility authority_id is absent")
    product_release = value.get("product_release")
    require(isinstance(product_release, str)
            and re.fullmatch(r"v\d+\.\d+\.\d+(?:-beta\.\d+)?", product_release) is not None,
            "compatibility product_release is invalid")
    require(isinstance(value.get("composition"), dict), "composition is absent")
    composition = value["composition"]
    lifecycle_source_commit = composition.get("ninfer_lifecycle_source_commit")
    require(isinstance(lifecycle_source_commit, str)
            and re.fullmatch(r"[0-9a-f]{40}", lifecycle_source_commit) is not None,
            "NInfer lifecycle source commit is invalid")
    profiles = value.get("profiles")
    require(isinstance(profiles, list), "profiles must be an array")
    require([profile.get("id") for profile in profiles] == list(PROFILE_IDS),
            "profiles must contain the closed adapter set in canonical order")
    for profile in profiles:
        profile_id = profile["id"]
        require(profile.get("adapter") == profile_id, f"{profile_id} adapter drift")
        require(profile.get("status") in STATUSES, f"{profile_id} status is invalid")
        require(profile.get("transport") in TRANSPORTS, f"{profile_id} transport is invalid")
        require(profile.get("silent_cloud_fallback") is False,
                f"{profile_id} must disable silent cloud fallback")
        commands = profile.get("commands")
        require(isinstance(commands, list) and len(commands) > 0 and len(commands) == len(set(commands)),
                f"{profile_id} commands are absent or duplicated")
        require(set(commands) <= COMMANDS, f"{profile_id} contains an unknown command")
        require(isinstance(profile.get("client_distribution"), dict),
                f"{profile_id} client distribution is absent")
        require(isinstance(profile.get("runtime"), dict), f"{profile_id} runtime is absent")
        lifecycle = profile.get("lifecycle")
        require(isinstance(lifecycle, dict), f"{profile_id} lifecycle is absent")
        require(
            lifecycle.get("script_url") == (
                "https://raw.githubusercontent.com/alphastorm/ninfer/"
                f"{lifecycle_source_commit}/tools/lifecycle/ninfer_container.py"
            ),
            f"{profile_id} lifecycle script does not bind the declared source commit",
        )
        require(isinstance(lifecycle.get("script_sha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", lifecycle["script_sha256"]) is not None,
                f"{profile_id} lifecycle script SHA-256 is invalid")
        require(isinstance(profile.get("gpu_qualification"), dict),
                f"{profile_id} GPU qualification is absent")
        gpu_status = profile["gpu_qualification"].get("status")
        require(gpu_status in {"qualified", "in qualification"},
                f"{profile_id} GPU qualification status is invalid")
        gpu_receipt = profile["gpu_qualification"].get("receipt")
        if gpu_status == "in qualification":
            require(gpu_receipt is None,
                    f"{profile_id} in-qualification GPU receipt must be pending")
        else:
            require(isinstance(gpu_receipt, dict),
                    f"{profile_id} GPU qualification receipt is absent")
            require(
                isinstance(gpu_receipt.get("url"), str)
                and re.fullmatch(
                    r"https://raw\.githubusercontent\.com/alphastorm/omp-ninfer/"
                    r"[0-9a-f]{40}/releases/"
                    + re.escape(product_release)
                    + r"/qualification/rtx5090\.json",
                    gpu_receipt["url"],
                )
                is not None,
                f"{profile_id} GPU qualification receipt URL is not immutable",
            )
            require(isinstance(gpu_receipt.get("sha256"), str)
                    and re.fullmatch(r"[0-9a-f]{64}", gpu_receipt["sha256"]) is not None,
                    f"{profile_id} GPU qualification receipt SHA-256 is invalid")
        acceptance = profile.get("acceptance_receipt")
        if acceptance is not None:
            require(isinstance(acceptance, dict), f"{profile_id} acceptance receipt is invalid")
            require(
                isinstance(acceptance.get("url"), str)
                and re.fullmatch(
                    r"https://raw\.githubusercontent\.com/alphastorm/omp-ninfer/"
                    r"[0-9a-f]{40}/releases/v\d+\.\d+\.\d+(?:-beta\.\d+)?/"
                    r"acceptance/[a-z0-9-]+(?:\.[a-z0-9-]+)*\.json",
                    acceptance["url"],
                )
                is not None,
                f"{profile_id} acceptance receipt URL is not immutable",
            )
            require(
                isinstance(acceptance.get("sha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", acceptance["sha256"]) is not None,
                f"{profile_id} acceptance receipt SHA-256 is invalid",
            )
        if profile["status"] == "qualified":
            require(profile.get("acceptance_receipt") is not None,
                    f"{profile_id} qualified without acceptance")
    variants = value.get("runtime_variants", [])
    require(isinstance(variants, list), "runtime_variants must be an array")
    variant_ids = [variant.get("id") for variant in variants if isinstance(variant, dict)]
    require(len(variant_ids) == len(variants), "runtime variant must be an object")
    require(variant_ids == [item for item in RUNTIME_VARIANT_IDS if item in variant_ids],
            "runtime variants must use the closed set in canonical order")
    require(len(variant_ids) == len(set(variant_ids)), "runtime variants are duplicated")
    for variant in variants:
        variant_id = variant["id"]
        require(variant.get("status") in STATUSES, f"{variant_id} status is invalid")
        require(variant.get("silent_cloud_fallback") is False,
                f"{variant_id} must disable silent cloud fallback")
        require(isinstance(variant.get("platform"), str) and variant["platform"],
                f"{variant_id} platform is absent")
        require(isinstance(variant.get("gpu"), str) and variant["gpu"],
                f"{variant_id} GPU is absent")
        require(isinstance(variant.get("cuda_architecture"), str)
                and re.fullmatch(r"sm_\d+[a-z]?", variant["cuda_architecture"]) is not None,
                f"{variant_id} CUDA architecture is invalid")
        require(isinstance(variant.get("maximum_context_tokens"), int)
                and variant["maximum_context_tokens"] > 0,
                f"{variant_id} context ceiling is invalid")
        require(isinstance(variant.get("installation_mode"), str)
                and variant["installation_mode"],
                f"{variant_id} installation mode is absent")
        receipt = variant.get("qualification_receipt")
        require(isinstance(receipt, dict), f"{variant_id} qualification receipt is absent")
        receipt_url = receipt.get("url")
        receipt_path = receipt.get("path")
        immutable_receipt_url = (
            isinstance(receipt_url, str)
            and re.fullmatch(
                r"https://raw\.githubusercontent\.com/alphastorm/omp-ninfer/"
                r"[0-9a-f]{40}/releases/v\d+\.\d+\.\d+(?:-beta\.\d+)?/"
                r"qualification/[a-z0-9-]+(?:\.[a-z0-9-]+)*\.json",
                receipt_url,
            ) is not None
        )
        local_measurement = (
            receipt_url is None
            and isinstance(receipt_path, str)
            and re.fullmatch(r"docs/measurements/[a-z0-9-]+\.json", receipt_path) is not None
        )
        require(immutable_receipt_url or local_measurement,
                f"{variant_id} qualification receipt binding is invalid")
        require(isinstance(receipt.get("sha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", receipt["sha256"]) is not None,
                f"{variant_id} qualification receipt SHA-256 is invalid")
        if "release_tag" in variant:
            expected_release_tags = {
                "rtx3090-windows-native": "v0.2.2-qwen38-3090-beta.1",
                "rtx4090-windows-native": "v0.2.0-qwen38-4090-beta.1",
            }
            expected_package_names = {
                "rtx3090-windows-native": (
                    "ninfer-rtx3090-omp-v0.2.2-beta.1-windows-x86_64-"
                    "cuda13.3-rtx3090.tar.gz"
                ),
                "rtx4090-windows-native": "ninfer-4090-qwen38-v0.1.0-win-x64.zip",
            }
            require(variant.get("release_tag") == expected_release_tags[variant_id],
                    f"{variant_id} component release tag is invalid")
            require(variant.get("package_name") == expected_package_names[variant_id],
                    f"{variant_id} package name is invalid")
            require(isinstance(variant.get("source_commit"), str)
                    and re.fullmatch(r"[0-9a-f]{40}", variant["source_commit"]) is not None,
                    f"{variant_id} source commit is invalid")
            require(isinstance(variant.get("package_sha256"), str)
                    and re.fullmatch(r"[0-9a-f]{64}", variant["package_sha256"]) is not None,
                    f"{variant_id} package SHA-256 is invalid")
            require(isinstance(variant.get("package_bytes"), int)
                    and variant["package_bytes"] > 0,
                    f"{variant_id} package size is invalid")
            package_url = variant.get("package_url")
            if package_url is not None:
                require(
                    package_url == (
                        "https://github.com/alphastorm/ninfer/releases/download/"
                        f"{variant['release_tag']}/{variant['package_name']}"
                    ),
                    f"{variant_id} package URL does not bind its component release",
                )
        if variant["status"] == "qualified":
            require(variant.get("installable") is True,
                    f"{variant_id} qualified without an installable artifact")
    return value


def render(authority: dict[str, Any]) -> str:
    composition = authority["composition"]
    lines = [
        "<!-- Generated by scripts/render_compatibility.py from compatibility.json; do not edit. -->",
        "# Compatibility matrix",
        "",
        f"Authority: `{authority['authority_id']}`",
        f"Product release: `{authority['product_release']}`",
        f"Composition: **{composition['status']}**",
        "",
        "Client status is independent from each GPU runtime qualification. "
        "`preview` is not a support claim.",
        "",
        "| Profile | Client | Runtime | Transport | Adapter | Status | Installable | Acceptance |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for profile in authority["profiles"]:
        client = profile["client_distribution"]
        gpu = profile["gpu_qualification"]
        runtime_text = f"`{gpu['profile']}`"
        if gpu.get("status") != "qualified":
            runtime_text += f" ({gpu['status']})"
        acceptance = profile.get("acceptance_receipt")
        acceptance_text = (
            f"[receipt]({acceptance['url']})" if acceptance else "pending"
        )
        lines.append(
            "| `{id}` | {os} {arch} | {gpu} | `{transport}` | `{adapter}` | "
            "**{status}** | {installable} | {acceptance} |".format(
                id=profile["id"],
                os=client["os"],
                arch=client["architecture"],
                gpu=runtime_text,
                transport=profile["transport"],
                adapter=profile["adapter"],
                status=profile["status"],
                installable="yes" if profile["installable"] else "no",
                acceptance=acceptance_text,
            )
        )
    variants = authority.get("runtime_variants", [])
    if variants:
        lines.extend([
            "",
            "## Native runtime variants",
            "",
            "These variants use the same OMP clients but own separate native runtime packages and qualification receipts.",
            "",
            "| Variant | Platform | GPU | CUDA | Context | Status | Installable | Installation | Qualification |",
            "| --- | --- | --- | --- | ---: | --- | --- | --- | --- |",
        ])
        for variant in variants:
            receipt = variant["qualification_receipt"]
            receipt_text = (
                f"[receipt]({receipt['url']})"
                if receipt.get("url")
                else f"`{receipt['path']}`"
            )
            lines.append(
                "| {id} | {platform} | {gpu} | {cuda} | {context:,} | "
                "**{status}** | {installable} | {installation} | {receipt} |".format(
                    id=variant["id"],
                    platform=variant["platform"],
                    gpu=variant["gpu"],
                    cuda=variant["cuda_architecture"],
                    context=variant["maximum_context_tokens"],
                    status=variant["status"],
                    installable="yes" if variant["installable"] else "no",
                    installation=variant["installation_mode"],
                    receipt=receipt_text,
                )
            )
        if all("package_name" in variant for variant in variants):
            lines.extend(["", "Package bindings:", ""])
            for variant in variants:
                package = (
                    f"[`{variant['package_name']}`]({variant['package_url']})"
                    if variant.get("package_url")
                    else f"`{variant['package_name']}` (public URL pending)"
                )
                lines.append(
                    f"- `{variant['id']}`: component `{variant['release_tag']}`; "
                    f"package {package}; SHA-256 `{variant['package_sha256']}`; "
                    f"{variant['package_bytes']:,} bytes."
                )
    lines.extend(["", "## Profile boundaries", ""])
    for profile in authority["profiles"]:
        lines.extend(
            [
                f"### `{profile['id']}`",
                "",
                "Commands: " + ", ".join(f"`{command}`" for command in profile["commands"]),
                "",
                "Limitations:",
                *[f"- {item}" for item in profile["limitations"]],
                "",
                "Blockers:",
                *[f"- {item}" for item in profile["blockers"]],
                "",
            ]
        )
    lines.extend(["## Composition blockers", ""])
    lines.extend(f"- {item}" for item in composition["blockers"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority", type=Path, default=root / "compatibility.json")
    parser.add_argument("--output", type=Path, default=root / "docs" / "COMPATIBILITY.md")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = render(load_authority(args.authority))
    if args.check:
        require(args.output.read_text(encoding="utf-8") == rendered,
                "generated compatibility matrix is stale")
        print(f"verified {args.output}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
