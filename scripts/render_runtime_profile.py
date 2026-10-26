#!/usr/bin/env python3
"""Render one product runtime profile into container argv or native server-config schema 4.

The authored schema is shared across lanes; wire formats and their identity algorithms are not.
--template updates a container's client/transport envelope without changing its other fields.
--check compares the exact rendered bytes without writing anything.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys


SETTINGS = {
    "release_id", "deployment_profile", "listen", "authentication", "model_id", "engine",
    "context_cache", "speculative", "reasoning", "session_checkpoint", "response_store",
    "telemetry", "runtime_host",
}
GROUPS = {
    "listen": {"host", "port", "allowed_host_classes"},
    "authentication": {"mode"},
    "engine": {"device", "max_context", "kv_capacity", "admission_headroom_mib", "prefill_chunk",
               "kv_dtype", "max_concurrency", "max_pending_requests", "pending_timeout_ms",
               "gpu_keep_warm_ms", "cuda_graph", "prefix_reuse", "vision"},
    "context_cache": {"device_state_slots", "host_context_mib"},
    "speculative": {"backend", "draft_tokens", "lm_head_draft"},
    "reasoning": {"thinking", "preserve_thinking"},
    "session_checkpoint": {"enabled", "quota_mib", "staging_mib", "require_origin_auth"},
    "response_store": {"max_records", "max_mib"},
    "telemetry": {"request_log_jsonl", "stats_interval_ms"},
    "runtime_host": {"minimum_runtime_memory_mib", "reason"},
}
CONTAINER_FIELDS = {"binary_sha256", "model_artifact_sha256", "published_bind_host", "published_port",
                    "checkpoint_mount_target", "checkpoint_seccomp_sha256", "restart_policy"}


def validate(profile: dict) -> None:
    if profile.get("artifact_type") != "omp_ninfer_runtime_profile" or profile.get("schema_version") != 1:
        raise ValueError("expected omp_ninfer_runtime_profile schema 1")
    if set(profile) - {"artifact_type", "schema_version", "kind", "lane", "settings", "container"}:
        raise ValueError("unknown product runtime profile field")
    kind, lane = profile.get("kind"), profile.get("lane")
    if (kind, lane) not in {("container", "rtx5090"), ("native", "rtx4090"), ("native", "rtx3090")}:
        raise ValueError("unsupported runtime kind/lane")
    settings = profile["settings"]
    if set(settings) - SETTINGS:
        raise ValueError("unknown runtime setting")
    for group, fields in GROUPS.items():
        if group in settings and (not isinstance(settings[group], dict) or set(settings[group]) - fields):
            raise ValueError(f"unknown {group} setting")
    for field in ("deployment_profile", "listen", "authentication", "model_id", "engine",
                  "context_cache", "speculative", "reasoning", "session_checkpoint"):
        if field not in settings:
            raise ValueError(f"missing {field} setting")
    if settings["authentication"] != {"mode": "required-api-key-file"}:
        raise ValueError("runtime profiles require API-key-file authentication")
    if kind == "native":
        if "container" in profile or "lm_head_draft" in settings["speculative"]:
            raise ValueError("native schema 4 cannot represent container-only settings")
        if not settings.get("release_id"):
            raise ValueError("native schema 4 requires release_id")
    else:
        if set(profile.get("container", {})) != CONTAINER_FIELDS:
            raise ValueError("container identity and publication settings must be complete")
        # Do not silently discard native-only settings when producing CLI arguments.
        for group in ("release_id", "response_store", "telemetry", "runtime_host"):
            if group in settings:
                raise ValueError(f"{group} is not a container CLI setting")
        if "allowed_host_classes" in settings["listen"]:
            raise ValueError("container CLI does not represent allowed_host_classes")
        if not settings["session_checkpoint"].get("enabled"):
            raise ValueError("container identity requires enabled checkpoints")


def container_arguments(profile: dict) -> list[str]:
    validate(profile)
    if profile["kind"] != "container":
        raise ValueError("container argv requires --kind container in the profile")
    s, c = profile["settings"], profile["container"]
    args = ["--host", s["listen"]["host"], "--port", str(s["listen"]["port"]),
            "--model-id", s["model_id"], "--binary-sha256", c["binary_sha256"],
            "--artifact-sha256", c["model_artifact_sha256"], "--config-sha256", "",
            "--deployment-profile", s["deployment_profile"]]

    def value(group, field, flag):
        if field in s[group]:
            args.extend((flag, str(s[group][field])))

    def boolean(group, field, yes=None, no=None, default=False):
        if field in s[group]:
            enabled = s[group][field]
            if not isinstance(enabled, bool):
                raise ValueError(f"{group}.{field} must be boolean")
            flag = yes if enabled else no
            if flag is None:
                if enabled == default:
                    return
                raise ValueError(f"container CLI cannot represent {group}.{field}={enabled}")
            args.append(flag)

    for field in ("device", "max_context", "kv_capacity", "admission_headroom_mib", "prefill_chunk",
                  "kv_dtype", "max_concurrency", "max_pending_requests", "pending_timeout_ms"):
        value("engine", field, "--" + field.replace("_", "-"))
    value("speculative", "backend", "--spec")
    value("speculative", "draft_tokens", "--draft-tokens")
    boolean("speculative", "lm_head_draft", "--lm-head-draft")
    boolean("engine", "vision", "--vision")
    boolean("engine", "cuda_graph", no="--no-cuda-graph", default=True)
    boolean("engine", "prefix_reuse", no="--no-prefix-reuse", default=True)
    boolean("reasoning", "thinking", no="--no-thinking", default=True)
    boolean("reasoning", "preserve_thinking", "--preserve-thinking")
    args.extend(("--session-checkpoint-dir", c["checkpoint_mount_target"]))
    value("session_checkpoint", "quota_mib", "--session-checkpoint-quota-mib")
    value("session_checkpoint", "staging_mib", "--session-checkpoint-staging-mib")
    boolean("session_checkpoint", "require_origin_auth", "--session-checkpoint-require-origin-auth")
    value("context_cache", "device_state_slots", "--device-state-slots")
    value("context_cache", "host_context_mib", "--host-context-mib")
    value("engine", "gpu_keep_warm_ms", "--gpu-keep-warm-ms")
    # Reuse the shipped verifier's lifecycle identity algorithm, including argument order.
    from verify_release import configuration_identity
    envelope = {"model": {"public_id": s["model_id"]}, "server": {
        **{key: c[key] for key in ("published_bind_host", "published_port", "checkpoint_mount_target",
                                  "checkpoint_seccomp_sha256", "restart_policy")},
        "arguments": args, "deployment_profile": s["deployment_profile"]}}
    args[args.index("--config-sha256") + 1] = configuration_identity(envelope)
    return args


def render(profile: dict, template: dict | None = None) -> dict | list[str]:
    validate(profile)
    if profile["kind"] == "native":
        if template is not None:
            raise ValueError("--template is container-only")
        return {"artifact_type": "ninfer_windows_server_config", "schema_version": 4,
                **copy.deepcopy(profile["settings"])}
    arguments = container_arguments(profile)
    if template is None:
        return arguments
    result = copy.deepcopy(template)
    s, c = profile["settings"], profile["container"]
    result["server"].update({key: c[key] for key in (
        "published_bind_host", "published_port", "checkpoint_mount_target", "checkpoint_seccomp_sha256", "restart_policy")})
    result["server"].update(arguments=arguments, deployment_profile=s["deployment_profile"],
                              container_port=s["listen"]["port"])
    result["model"].update(public_id=s["model_id"], artifact_sha256=c["model_artifact_sha256"])
    return result


def rendered_bytes(profile: dict, template: dict | None = None) -> bytes:
    return (json.dumps(render(profile, template), indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--template", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check and args.output is None:
        parser.error("--check requires --output")
    try:
        data = rendered_bytes(json.loads(args.profile.read_text(encoding="utf-8")),
                              json.loads(args.template.read_text(encoding="utf-8")) if args.template else None)
        if args.check:
            if args.output.read_bytes() != data:
                raise ValueError(f"rendered profile differs: {args.output}")
        elif args.output:
            args.output.write_bytes(data)
        else:
            sys.stdout.buffer.write(data)
    except (KeyError, ValueError, OSError) as error:
        parser.exit(1, str(error) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
