#!/usr/bin/env python3
"""Run and reduce the per-lane runtime variant campaign on the frozen agent corpus.

Every arm is one server configuration (artifact, KV format, prefill chunk, context, speculation)
started as a fresh process inside one shared campaign identity. The corpus, request execution,
output projection, and server-log binding are reused from ``run_mtp_ablation.py``; this module
owns the variant arm contract, the prefill/decode metrics, the workload model, and the per-lane
decision.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import statistics
import sys
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_mtp_ablation as corpus  # noqa: E402

ARMS_ARTIFACT_TYPE = "omp_ninfer_variant_campaign_arms"
RUN_ARTIFACT_TYPE = "omp_ninfer_variant_campaign_run"
ARM_ARTIFACT_TYPE = "omp_ninfer_variant_campaign_arm"
LANE_ARTIFACT_TYPE = "omp_ninfer_variant_campaign_lane"
QUALITY_ARTIFACT_TYPE = "omp_ninfer_variant_campaign_quality"
SCHEMA_VERSION = 1
ANALYSIS_VERSION = 1
PROMOTION_MARGIN = 0.05
LONG_PREFILL_MIN_TOKENS = 4096
LONG_PREFILL_STEP = "responses_long_replay"
ROLES = ("incumbent", "candidate", "control")
QUALITY_GATES = ("byte-equivalent", "role-corpus")
KV_DTYPES = ("bf16", "int8", "rk2v4-e8")
# CLI --kv-dtype value -> names the engine reports in server_start engine.kv_cache.
ENGINE_KV_NAMES = {
    "bf16": frozenset({"bf16"}),
    "int8": frozenset({"int8", "int8-group64"}),
    "rk2v4-e8": frozenset({"rk2v4-e8"}),
}
SPECULATIVE_BACKENDS = ("none", "mtp")
LABEL_CHARACTERS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-")

CampaignError = corpus.AblationError


@dataclass(frozen=True)
class VariantSpec:
    label: str
    role: str
    weights_id: str
    kv_dtype: str
    prefill_chunk: int
    max_context: int
    speculative_backend: str
    speculative_draft_window: int
    quality_gate: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "role": self.role,
            "weights_id": self.weights_id,
            "kv_dtype": self.kv_dtype,
            "prefill_chunk": self.prefill_chunk,
            "max_context": self.max_context,
            "speculative_backend": self.speculative_backend,
            "speculative_draft_window": self.speculative_draft_window,
            "quality_gate": self.quality_gate,
        }


@dataclass(frozen=True)
class LaneMatrix:
    lane: str
    source_commit: str
    binary_sha256: str
    qualified_context: int
    incumbent: str
    arms: tuple[VariantSpec, ...]
    artifacts: Mapping[str, Mapping[str, Any]]
    workload_references: tuple[Mapping[str, Any], ...]
    corpus_sha256: str

    def spec(self, label: str) -> VariantSpec:
        for spec in self.arms:
            if spec.label == label:
                return spec
        raise CampaignError(f"lane {self.lane} has no arm {label!r}")

    def artifact(self, weights_id: str) -> Mapping[str, Any]:
        artifact = self.artifacts.get(weights_id)
        if artifact is None:
            raise CampaignError(f"arms manifest has no artifact {weights_id!r}")
        return artifact


def positive_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise CampaignError(f"{label} must be a positive integer")
    return value


def non_negative_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise CampaignError(f"{label} must be a non-negative integer")
    return value


def parse_spec(value: Any) -> VariantSpec:
    if not isinstance(value, dict):
        raise CampaignError("arm specification must be an object")
    label = value.get("label")
    if not isinstance(label, str) or not label or any(char not in LABEL_CHARACTERS for char in label):
        raise CampaignError("arm label must use lowercase letters, digits, and hyphens")
    role = value.get("role")
    if role not in ROLES:
        raise CampaignError(f"arm {label} role must be one of {ROLES}")
    weights_id = value.get("weights_id")
    if not isinstance(weights_id, str) or not weights_id:
        raise CampaignError(f"arm {label} weights_id must be a non-empty string")
    kv_dtype = value.get("kv_dtype")
    if kv_dtype not in KV_DTYPES:
        raise CampaignError(f"arm {label} kv_dtype must be one of {KV_DTYPES}")
    backend = value.get("speculative_backend")
    if backend not in SPECULATIVE_BACKENDS:
        raise CampaignError(f"arm {label} speculative_backend must be one of {SPECULATIVE_BACKENDS}")
    window = non_negative_int(value.get("speculative_draft_window"), f"arm {label} draft window")
    if (backend == "none") != (window == 0):
        raise CampaignError(f"arm {label} draft window does not match its speculative backend")
    gate = value.get("quality_gate")
    if gate not in QUALITY_GATES:
        raise CampaignError(f"arm {label} quality_gate must be one of {QUALITY_GATES}")
    return VariantSpec(
        label=label,
        role=role,
        weights_id=weights_id,
        kv_dtype=kv_dtype,
        prefill_chunk=positive_int(value.get("prefill_chunk"), f"arm {label} prefill chunk"),
        max_context=positive_int(value.get("max_context"), f"arm {label} max context"),
        speculative_backend=backend,
        speculative_draft_window=window,
        quality_gate=gate,
    )


def parse_workload_reference(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CampaignError("workload reference must be an object")
    label = value.get("label")
    if not isinstance(label, str) or not label:
        raise CampaignError("workload reference label must be a non-empty string")
    return {
        "label": label,
        "source": value.get("source"),
        "computed_prefill_tokens": positive_int(
            value.get("computed_prefill_tokens"), f"workload {label} computed prefill tokens"
        ),
        "prefix_hit_tokens": non_negative_int(
            value.get("prefix_hit_tokens"), f"workload {label} prefix hit tokens"
        ),
        "decode_tokens": positive_int(value.get("decode_tokens"), f"workload {label} decode tokens"),
    }


def load_lane_matrix(manifest: Mapping[str, Any], lane: str) -> LaneMatrix:
    if manifest.get("artifact_type") != ARMS_ARTIFACT_TYPE:
        raise CampaignError("arms manifest has the wrong artifact_type")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise CampaignError("arms manifest has an unsupported schema_version")
    corpus_sha = corpus.require_sha256(manifest.get("corpus_sha256"), "arms manifest corpus_sha256")
    if corpus_sha != corpus.corpus_manifest()["sha256"]:
        raise CampaignError("arms manifest corpus does not match the runner corpus")
    lanes = manifest.get("lanes")
    if not isinstance(lanes, dict) or lane not in lanes:
        raise CampaignError(f"arms manifest has no lane {lane!r}")
    entry = lanes[lane]
    if not isinstance(entry, dict):
        raise CampaignError(f"lane {lane} entry must be an object")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise CampaignError("arms manifest must declare artifacts")
    for weights_id, artifact in artifacts.items():
        if not isinstance(artifact, dict):
            raise CampaignError(f"artifact {weights_id} must be an object")
        corpus.require_sha256(artifact.get("sha256"), f"artifact {weights_id} sha256")
        positive_int(artifact.get("bytes"), f"artifact {weights_id} bytes")
    raw_arms = entry.get("arms")
    if not isinstance(raw_arms, list) or len(raw_arms) < 2:
        raise CampaignError(f"lane {lane} must declare at least two arms")
    specs = tuple(parse_spec(item) for item in raw_arms)
    labels = [spec.label for spec in specs]
    if len(set(labels)) != len(labels):
        raise CampaignError(f"lane {lane} declares duplicate arm labels")
    incumbent = entry.get("incumbent")
    incumbents = [spec.label for spec in specs if spec.role == "incumbent"]
    if not isinstance(incumbent, str) or incumbents != [incumbent]:
        raise CampaignError(f"lane {lane} must declare exactly one incumbent arm")
    for spec in specs:
        if spec.weights_id not in artifacts:
            raise CampaignError(f"arm {spec.label} references unknown artifact {spec.weights_id}")
    references = manifest.get("workload_references")
    if not isinstance(references, list) or not references:
        raise CampaignError("arms manifest must declare workload references")
    parsed_references = tuple(parse_workload_reference(item) for item in references)
    reference_labels = [item["label"] for item in parsed_references]
    if len(set(reference_labels)) != len(reference_labels):
        raise CampaignError("workload reference labels must be unique")
    return LaneMatrix(
        lane=lane,
        source_commit=corpus.require_commit(entry.get("source_commit"), f"lane {lane} source commit"),
        binary_sha256=corpus.require_sha256(entry.get("binary_sha256"), f"lane {lane} binary sha256"),
        qualified_context=positive_int(entry.get("qualified_context"), f"lane {lane} qualified context"),
        incumbent=incumbent,
        arms=specs,
        artifacts=artifacts,
        workload_references=parsed_references,
        corpus_sha256=corpus_sha,
    )


def load_lane_matrix_file(path: Path, lane: str) -> LaneMatrix:
    return load_lane_matrix(corpus.read_json_object(path), lane)


def initial_run_state(matrix: LaneMatrix, spec: VariantSpec, model: str, campaign_id: str) -> dict[str, Any]:
    manifest = corpus.corpus_manifest()
    return {
        "artifact_type": RUN_ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "created_utc": corpus.utc_now(),
        "lane": matrix.lane,
        "arm": spec.label,
        "arm_spec": spec.as_dict(),
        "model": model,
        "campaign_id": corpus.require_sha256(campaign_id, "campaign_id"),
        "corpus_sha256": manifest["sha256"],
        "expected_scenarios": len(manifest["scenarios"]) * corpus.REPETITIONS,
        "expected_requests": manifest["request_count"],
        "scenarios": {},
    }


def load_run_state(
    path: Path, matrix: LaneMatrix, spec: VariantSpec, model: str, campaign_id: str, resume: bool
) -> dict[str, Any]:
    expected = initial_run_state(matrix, spec, model, campaign_id)
    if not path.exists():
        return expected
    if not resume:
        raise CampaignError(f"{path} already exists; pass --resume to continue it")
    state = corpus.read_json_object(path)
    for key in ("artifact_type", "schema_version", "lane", "arm", "arm_spec", "model", "campaign_id", "corpus_sha256"):
        if state.get(key) != expected[key]:
            raise CampaignError(f"run state {key} does not match this campaign")
    if not isinstance(state.get("scenarios"), dict):
        raise CampaignError("run state scenarios must be an object")
    return state


def run_campaign(args: argparse.Namespace) -> dict[str, Any]:
    matrix = load_lane_matrix_file(Path(args.arms), args.lane)
    spec = matrix.spec(args.arm)
    output = Path(args.output)
    campaign_id = corpus.require_sha256(args.campaign_id, "campaign_id")
    state = load_run_state(output, matrix, spec, args.model, campaign_id, args.resume)
    api_key = Path(args.api_key_file).read_text(encoding="utf-8").strip()
    if not api_key:
        raise CampaignError("API key file is empty")
    client = corpus.HttpClient(args.base_url, api_key, args.timeout)
    client.health()
    manifest = corpus.corpus_manifest()
    scenarios = state["scenarios"]
    for repetition in range(corpus.REPETITIONS):
        for definition in manifest["scenarios"]:
            name = definition["name"]
            key = f"{name}/r{repetition}"
            existing = scenarios.get(key)
            if isinstance(existing, dict) and existing.get("status") == "complete":
                continue
            steps = corpus.execute_scenario(
                client,
                model=args.model,
                lane=matrix.lane,
                arm=spec.label,  # type: ignore[arg-type]
                campaign_id=campaign_id,
                corpus_sha256=manifest["sha256"],
                name=name,
                repetition=repetition,
            )
            scenarios[key] = {"status": "complete", "steps": steps}
            corpus.atomic_write_json(output, state)
            print(f"complete {key} ({len(steps)} request(s))", flush=True)
    state["completed_utc"] = corpus.utc_now()
    corpus.atomic_write_json(output, state)
    return state


def next_incomplete_step(state: Mapping[str, Any]) -> str:
    scenarios = state.get("scenarios")
    if not isinstance(scenarios, dict):
        raise CampaignError("run state scenarios must be an object")
    manifest = corpus.corpus_manifest()
    for repetition in range(corpus.REPETITIONS):
        for definition in manifest["scenarios"]:
            key = f"{definition['name']}/r{repetition}"
            existing = scenarios.get(key)
            if isinstance(existing, dict) and existing.get("status") == "complete":
                continue
            return f"{key}/{corpus.CORPUS_STEP_NAMES[definition['name']][0]}"
    raise CampaignError("run state has no incomplete step")


def read_memory_samples(path: Path) -> dict[str, Any]:
    peaks: list[int] = []
    count = 0
    try:
        handle = path.open("r", encoding="utf-8")
    except OSError as exc:
        raise CampaignError(f"cannot read memory samples {path}: {exc}") from exc
    with handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                record = json.loads(text)
            except json.JSONDecodeError as exc:
                raise CampaignError(f"memory sample line is not JSON: {text[:80]}") from exc
            if not isinstance(record, dict):
                raise CampaignError("memory sample must be an object")
            used = record.get("memory_used_mib")
            if not isinstance(used, int) or isinstance(used, bool) or used < 0:
                raise CampaignError("memory sample memory_used_mib must be a non-negative integer")
            peaks.append(used)
            count += 1
    if count == 0:
        raise CampaignError("memory samples file is empty")
    return {"samples": count, "peak_memory_used_mib": max(peaks), "sha256": corpus.sha256_file(path)}


def bind_server_start(
    start: Mapping[str, Any], *, spec: VariantSpec, matrix: LaneMatrix, model: str, instance_id: str
) -> dict[str, Any]:
    server = start.get("server")
    identity = start.get("identity")
    engine = start.get("engine")
    artifact = start.get("artifact")
    sampling = start.get("sampling_defaults")
    if not all(isinstance(section, dict) for section in (server, identity, engine, artifact, sampling)):
        raise CampaignError("server_start omitted server, identity, engine, artifact, or sampling defaults")
    assert isinstance(server, dict) and isinstance(identity, dict) and isinstance(engine, dict)
    assert isinstance(artifact, dict) and isinstance(sampling, dict)
    expected_artifact = matrix.artifact(spec.weights_id)
    checks = {
        "identity.binary_sha256": (identity.get("binary_sha256"), matrix.binary_sha256),
        "identity.patch_stack_sha": (identity.get("patch_stack_sha"), matrix.source_commit),
        "identity.model_artifact_sha256": (identity.get("model_artifact_sha256"), expected_artifact["sha256"]),
        "identity.weights_id": (identity.get("weights_id"), spec.weights_id),
        "identity.source_dirty": (identity.get("source_dirty"), False),
        "artifact.weights_id": (artifact.get("weights_id"), spec.weights_id),
        "artifact.size_bytes": (artifact.get("size_bytes"), expected_artifact["bytes"]),
        "server.public_model_id": (server.get("public_model_id"), model),
        "engine.prefill_chunk": (engine.get("prefill_chunk"), spec.prefill_chunk),
        "engine.max_context": (engine.get("max_context"), spec.max_context),
        "engine.speculative_backend": (engine.get("speculative_backend"), spec.speculative_backend),
        "engine.speculative_draft_window": (engine.get("speculative_draft_window"), spec.speculative_draft_window),
        "engine.max_concurrency": (engine.get("max_concurrency"), 1),
        "engine.prefix_reuse": (engine.get("prefix_reuse"), True),
        "sampling_defaults.greedy": (sampling.get("greedy"), True),
    }
    if spec.speculative_backend == "mtp":
        checks["engine.proposal_head"] = (engine.get("proposal_head"), "optimized")
    for field, (actual, expected) in checks.items():
        if actual != expected:
            raise CampaignError(f"server {field} mismatch: {actual!r} != {expected!r}")
    engine_kv = engine.get("kv_cache")
    if engine_kv not in ENGINE_KV_NAMES[spec.kv_dtype]:
        raise CampaignError(f"server engine.kv_cache mismatch: {engine_kv!r} is not a {spec.kv_dtype!r} format")
    kv_capacity = engine.get("kv_capacity")
    if not isinstance(kv_capacity, int) or isinstance(kv_capacity, bool) or kv_capacity <= 0:
        raise CampaignError("server_start omitted a positive engine kv_capacity")
    load_seconds = artifact.get("load_seconds")
    if not isinstance(load_seconds, (int, float)) or isinstance(load_seconds, bool) or load_seconds < 0:
        raise CampaignError("server_start omitted artifact load seconds")
    configuration = corpus.safe_configuration(start)
    return {
        "instance_id": instance_id,
        "configuration": configuration,
        "capacity": {
            "kv_capacity": kv_capacity,
            "kv_capacity_mode": engine.get("kv_capacity_mode"),
            "kv_capacity_page_groups": engine.get("kv_capacity_page_groups"),
            "kv_capacity_max_page_groups": engine.get("kv_capacity_max_page_groups"),
            "artifact_load_seconds": float(load_seconds),
        },
    }


def summarize_arm(
    trace_path: Path,
    log_path: Path,
    *,
    matrix: LaneMatrix,
    memory_samples_path: Path | None = None,
    failure_code: str | None = None,
    failed_step_id: str | None = None,
    failure_evidence_path: Path | None = None,
) -> dict[str, Any]:
    state = corpus.read_json_object(trace_path)
    if state.get("artifact_type") != RUN_ARTIFACT_TYPE:
        raise CampaignError("trace has the wrong artifact_type")
    if state.get("lane") != matrix.lane:
        raise CampaignError("trace lane does not match the arms manifest lane")
    label = state.get("arm")
    if not isinstance(label, str):
        raise CampaignError("trace has an invalid arm label")
    spec = matrix.spec(label)
    if state.get("arm_spec") != spec.as_dict():
        raise CampaignError("trace arm specification drifted from the arms manifest")
    model = state.get("model")
    if not isinstance(model, str) or not model:
        raise CampaignError("trace has an invalid model")
    corpus_sha = corpus.require_sha256(state.get("corpus_sha256"), "corpus_sha256")
    if corpus_sha != matrix.corpus_sha256:
        raise CampaignError("trace corpus does not match the arms manifest")
    campaign_id = corpus.require_sha256(state.get("campaign_id"), "campaign_id")
    steps = corpus.flatten_steps(state)
    expected_requests = state.get("expected_requests")
    if not isinstance(expected_requests, int) or isinstance(expected_requests, bool):
        raise CampaignError("trace has an invalid expected request count")
    failure_values = (failure_code, failed_step_id, failure_evidence_path)
    if any(value is not None for value in failure_values) and not all(
        value is not None for value in failure_values
    ):
        raise CampaignError("failure code, step, and evidence path must be supplied together")
    failed = failure_code is not None
    if not failed and len(steps) != expected_requests:
        raise CampaignError("trace does not contain the expected request count")
    if failed and len(steps) >= expected_requests:
        raise CampaignError("a failed arm must have fewer than the expected request count")
    wanted: dict[str, dict[str, Any]] = {}
    for step in steps:
        step_id = step.get("step_id")
        if not isinstance(step_id, str) or not step_id:
            raise CampaignError("trace contains a malformed step ID")
        request_id = corpus.require_sha256(step.get("request_sha256"), "request_sha256")
        expected_request_id = corpus.scoped_identity(
            "request",
            campaign_id=campaign_id,
            corpus_sha256=corpus_sha,
            lane=matrix.lane,
            arm=label,  # type: ignore[arg-type]
            suffix=step_id,
        )
        if request_id != expected_request_id:
            raise CampaignError(f"trace request identity mismatch for {step_id}")
        if request_id in wanted:
            raise CampaignError("trace contains duplicate request identities")
        wanted[request_id] = step

    starts: dict[str, dict[str, Any]] = {}
    latest: dict[str, dict[str, Any]] = {}
    log_present = log_path.exists()
    if not log_present and not failed:
        raise CampaignError(f"cannot read server log {log_path}: missing")
    if log_present:
        try:
            handle = log_path.open("r", encoding="utf-8")
        except OSError as exc:
            raise CampaignError(f"cannot read server log {log_path}: {exc}") from exc
        with handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                instance = record.get("server_instance_id")
                if record.get("event") == "server_start" and isinstance(instance, str):
                    starts[instance] = record
                request_id = corpus.request_identity(record)
                if request_id is not None and request_id in wanted:
                    latest[request_id] = record
    missing = sorted(set(wanted) - set(latest))
    if missing:
        raise CampaignError(f"server log omitted {len(missing)} completed trace request(s)")
    non_done = sorted(key for key, record in latest.items() if record.get("event") != "request_done")
    if non_done:
        raise CampaignError(f"latest log event was not request_done for {len(non_done)} request(s)")
    expected_artifact = matrix.artifact(spec.weights_id)
    binding: dict[str, Any] | None = None
    if failed and not starts:
        if latest:
            raise CampaignError("server log has requests without a server_start record")
    else:
        if len(starts) != 1:
            raise CampaignError("a variant arm must run inside exactly one fresh server process")
        (instance_id, start), = starts.items()
        request_instances = {record.get("server_instance_id") for record in latest.values()}
        if request_instances and request_instances != {instance_id}:
            raise CampaignError("trace requests were served by a different server instance")
        binding = bind_server_start(start, spec=spec, matrix=matrix, model=model, instance_id=instance_id)

    failure: dict[str, Any] | None = None
    if failed:
        assert failure_code is not None
        assert failed_step_id is not None
        assert failure_evidence_path is not None
        scenario_names = {item["name"] for item in corpus.corpus_manifest()["scenarios"]}
        step_parts = failed_step_id.split("/")
        if (
            not failure_code
            or any(not (char.islower() or char.isdigit() or char == "_") for char in failure_code)
            or len(step_parts) != 3
            or step_parts[0] not in scenario_names
            or step_parts[1] not in {f"r{index}" for index in range(corpus.REPETITIONS)}
            or not step_parts[2]
        ):
            raise CampaignError("failure metadata is malformed")
        try:
            evidence_size = failure_evidence_path.stat().st_size
        except OSError as exc:
            raise CampaignError(f"cannot read failure evidence: {exc}") from exc
        if evidence_size <= 0:
            raise CampaignError("failure evidence is empty")
        failure = {
            "code": failure_code,
            "step_id": failed_step_id,
            "evidence_sha256": corpus.sha256_file(failure_evidence_path),
            "evidence_size_bytes": evidence_size,
        }

    rows: list[dict[str, Any]] = []
    for request_id, trace in sorted(wanted.items(), key=lambda item: item[1]["step_id"]):
        record = latest[request_id]
        request = record.get("request")
        result = record.get("result")
        timings = record.get("timings_seconds")
        speculative = record.get("speculative")
        if not isinstance(request, dict):
            raise CampaignError(f"request_done {request_id} omitted request metadata")
        if not isinstance(result, dict):
            raise CampaignError(f"request_done {request_id} omitted result metrics")
        if not isinstance(timings, dict):
            raise CampaignError(f"request_done {request_id} omitted timing metrics")
        if not isinstance(speculative, dict):
            raise CampaignError(f"request_done {request_id} omitted speculative metrics")
        client_identity = request.get("client_identity")
        if not isinstance(client_identity, dict):
            raise CampaignError(f"request_done {request_id} omitted client identity")
        if client_identity.get("request_sha256") != request_id:
            raise CampaignError(f"request identity mismatch for {trace['step_id']}")
        scenario_key = trace["step_id"].rsplit("/", 1)[0]
        expected_session_id = corpus.scoped_identity(
            "session",
            campaign_id=campaign_id,
            corpus_sha256=corpus_sha,
            lane=matrix.lane,
            arm=label,  # type: ignore[arg-type]
            suffix=scenario_key,
        )
        if client_identity.get("session_sha256") != expected_session_id:
            raise CampaignError(f"session identity mismatch for {trace['step_id']}")
        if request.get("protocol") != trace.get("protocol"):
            raise CampaignError(f"protocol mismatch for {trace['step_id']}")
        if result.get("prompt_tokens") != trace.get("prompt_tokens"):
            raise CampaignError(f"prompt usage mismatch for {trace['step_id']}")
        if result.get("completion_tokens") != trace.get("completion_tokens"):
            raise CampaignError(f"completion usage mismatch for {trace['step_id']}")
        if request.get("enable_thinking") is not True:
            raise CampaignError(f"thinking was not enabled for {trace['step_id']}")
        if speculative.get("backend") != spec.speculative_backend:
            raise CampaignError(f"speculative backend mismatch for {trace['step_id']}")
        if speculative.get("draft_window") != spec.speculative_draft_window:
            raise CampaignError(f"speculative draft window mismatch for {trace['step_id']}")
        drafted = speculative.get("drafted_tokens")
        accepted = speculative.get("accepted_tokens")
        if (
            not isinstance(drafted, int)
            or isinstance(drafted, bool)
            or drafted < 0
            or not isinstance(accepted, int)
            or isinstance(accepted, bool)
            or accepted < 0
            or accepted > drafted
        ):
            raise CampaignError(f"invalid speculative token counts for {trace['step_id']}")
        if spec.speculative_backend == "none" and any(
            speculative.get(field) != 0
            for field in ("rounds", "drafted_tokens", "accepted_tokens", "fallback_steps")
        ):
            raise CampaignError(f"non-speculative arm reported speculative work for {trace['step_id']}")
        computed = result.get("computed_prefill_tokens")
        if not isinstance(computed, int) or isinstance(computed, bool) or computed < 0:
            raise CampaignError(f"invalid computed prefill tokens for {trace['step_id']}")
        rows.append(
            {
                "step_id": trace["step_id"],
                "request_sha256": request_id,
                "protocol": trace["protocol"],
                "projection_sha256": corpus.require_sha256(
                    trace.get("projection_sha256"), "projection_sha256"
                ),
                "client_wall_seconds": trace["wall_seconds"],
                "prompt_tokens": result.get("prompt_tokens"),
                "completion_tokens": result.get("completion_tokens"),
                "computed_prefill_tokens": computed,
                "prefix_cache_hit_tokens": result.get("prefix_cache_hit_tokens"),
                "prefix_reuse_path": result.get("prefix_reuse_path"),
                "finish_reason": result.get("finish_reason"),
                "tool_call_count": result.get("tool_call_count"),
                "timings_seconds": {
                    key: timings.get(key) for key in ("prepare", "ttft", "prefill", "decode", "total")
                },
                "speculative": {
                    key: speculative.get(key)
                    for key in (
                        "backend",
                        "draft_window",
                        "rounds",
                        "drafted_tokens",
                        "accepted_tokens",
                        "fallback_steps",
                        "accepted_per_position",
                    )
                },
            }
        )
    memory = read_memory_samples(memory_samples_path) if memory_samples_path is not None else None
    configuration = binding["configuration"] if binding is not None else None
    capacity = dict(binding["capacity"]) if binding is not None else None
    if capacity is not None:
        capacity["device_memory"] = memory
    return {
        "artifact_type": ARM_ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "generated_utc": corpus.utc_now(),
        "scope": "within-lane experiment; not release qualification and not cross-lane comparable",
        "status": "failed" if failed else "completed",
        "lane": matrix.lane,
        "arm": label,
        "arm_spec": spec.as_dict(),
        "model": model,
        "campaign_id": campaign_id,
        "corpus_sha256": corpus_sha,
        "source_commit": matrix.source_commit,
        "binary_sha256": matrix.binary_sha256,
        "model_artifact_sha256": expected_artifact["sha256"],
        "model_artifact_bytes": expected_artifact["bytes"],
        "server_instance_sha256": (
            corpus.sha256_bytes(binding["instance_id"].encode("utf-8")) if binding is not None else None
        ),
        "trace_sha256": corpus.sha256_file(trace_path),
        "server_log_sha256": corpus.sha256_file(log_path) if log_present else None,
        "configuration_schema_version": corpus.CONFIGURATION_SCHEMA_VERSION,
        "configuration": configuration,
        "configuration_sha256": corpus.sha256_json(configuration) if configuration is not None else None,
        "capacity": capacity,
        "completed_requests": len(rows),
        "expected_requests": expected_requests,
        "failure": failure,
        "requests": rows,
    }


def repetition_of(step_id: Any) -> str:
    parts = step_id.split("/") if isinstance(step_id, str) else []
    if len(parts) != 3 or parts[1] not in {f"r{index}" for index in range(corpus.REPETITIONS)}:
        raise CampaignError("arm receipt contains an invalid repetition step id")
    return parts[1]


def aggregate_arm(receipt: Mapping[str, Any]) -> dict[str, Any]:
    requests = receipt.get("requests")
    if not isinstance(requests, list) or not requests:
        raise CampaignError("arm receipt has no requests")
    repetitions = [f"r{index}" for index in range(corpus.REPETITIONS)]
    totals = {
        key: {repetition: 0.0 for repetition in repetitions}
        for key in (
            "prompt_tokens",
            "completion_tokens",
            "decode_tokens",
            "decode_seconds",
            "computed_prefill_tokens",
            "prefill_seconds",
            "long_prefill_tokens",
            "long_prefill_seconds",
            "client_wall_seconds",
            "total_seconds",
        )
    }
    long_ttft = {repetition: [] for repetition in repetitions}
    ttft_values: list[float] = []
    rounds = drafted = accepted = fallback = 0
    reuse: dict[str, int] = {}
    for row in requests:
        if not isinstance(row, dict):
            raise CampaignError("arm receipt contains a malformed request")
        repetition = repetition_of(row.get("step_id"))
        prompt = positive_int(row.get("prompt_tokens"), "arm receipt prompt tokens")
        completion = non_negative_int(row.get("completion_tokens"), "arm receipt completion tokens")
        computed = non_negative_int(row.get("computed_prefill_tokens"), "arm receipt computed prefill tokens")
        timings = row.get("timings_seconds")
        speculative = row.get("speculative")
        if not isinstance(timings, dict) or not isinstance(speculative, dict):
            raise CampaignError("arm receipt omitted timing or speculative metrics")
        decode_seconds = corpus.finite_number(timings.get("decode"), "decode seconds")
        prefill_seconds = corpus.finite_number(timings.get("prefill"), "prefill seconds")
        total_seconds = corpus.finite_number(timings.get("total"), "total seconds")
        ttft = corpus.finite_number(timings.get("ttft"), "TTFT seconds")
        wall = corpus.finite_number(row.get("client_wall_seconds"), "client wall seconds")
        if min(decode_seconds, prefill_seconds, total_seconds, ttft, wall) < 0:
            raise CampaignError("arm receipt contains a negative duration")
        decode_tokens = max(0, completion - 1)
        step = row["step_id"].split("/")
        bucket = totals
        bucket["prompt_tokens"][repetition] += prompt
        bucket["completion_tokens"][repetition] += completion
        bucket["decode_tokens"][repetition] += decode_tokens
        bucket["decode_seconds"][repetition] += decode_seconds
        bucket["computed_prefill_tokens"][repetition] += computed
        bucket["prefill_seconds"][repetition] += prefill_seconds
        bucket["client_wall_seconds"][repetition] += wall
        bucket["total_seconds"][repetition] += total_seconds
        if computed >= LONG_PREFILL_MIN_TOKENS:
            bucket["long_prefill_tokens"][repetition] += computed
            bucket["long_prefill_seconds"][repetition] += prefill_seconds
        if step[0] == LONG_PREFILL_STEP and step[2] == "base":
            long_ttft[repetition].append(ttft)
        ttft_values.append(ttft)
        for label, value in (
            ("rounds", speculative.get("rounds")),
            ("drafted_tokens", speculative.get("drafted_tokens")),
            ("accepted_tokens", speculative.get("accepted_tokens")),
            ("fallback_steps", speculative.get("fallback_steps")),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CampaignError(f"arm receipt contains invalid {label}")
        rounds += speculative["rounds"]
        drafted += speculative["drafted_tokens"]
        accepted += speculative["accepted_tokens"]
        fallback += speculative["fallback_steps"]
        path = row.get("prefix_reuse_path")
        reuse[str(path)] = reuse.get(str(path), 0) + 1

    def rate(tokens: Mapping[str, float], seconds: Mapping[str, float]) -> dict[str, float | None]:
        return {
            repetition: (tokens[repetition] / seconds[repetition] if seconds[repetition] > 0 else None)
            for repetition in repetitions
        }

    decode_by_repetition = rate(totals["decode_tokens"], totals["decode_seconds"])
    prefill_by_repetition = rate(totals["computed_prefill_tokens"], totals["prefill_seconds"])
    long_prefill_by_repetition = rate(totals["long_prefill_tokens"], totals["long_prefill_seconds"])
    for name, rates in (("decode", decode_by_repetition), ("prefill", prefill_by_repetition)):
        if any(value is None or value <= 0 for value in rates.values()):
            raise CampaignError(f"arm receipt has no {name} throughput for a repetition")
    long_ttft_by_repetition = {
        repetition: (statistics.median(values) if values else None)
        for repetition, values in long_ttft.items()
    }

    def total(key: str) -> float:
        return sum(totals[key].values())

    decode_speeds = [value for value in decode_by_repetition.values() if value]
    return {
        "request_count": len(requests),
        "prompt_tokens": int(total("prompt_tokens")),
        "completion_tokens": int(total("completion_tokens")),
        "computed_prefill_tokens": int(total("computed_prefill_tokens")),
        "decode_tokens": int(total("decode_tokens")),
        "decode_seconds": total("decode_seconds"),
        "prefill_seconds": total("prefill_seconds"),
        "decode_tokens_per_second": total("decode_tokens") / total("decode_seconds"),
        "decode_tokens_per_second_by_repetition": decode_by_repetition,
        "decode_throughput_spread_pct": (max(decode_speeds) / min(decode_speeds) - 1.0) * 100.0,
        "prefill_tokens_per_second": total("computed_prefill_tokens") / total("prefill_seconds"),
        "prefill_tokens_per_second_by_repetition": prefill_by_repetition,
        "long_prefill_tokens": int(total("long_prefill_tokens")),
        "long_prefill_tokens_per_second": (
            total("long_prefill_tokens") / total("long_prefill_seconds")
            if total("long_prefill_seconds") > 0
            else None
        ),
        "long_prefill_tokens_per_second_by_repetition": long_prefill_by_repetition,
        "long_prefill_ttft_seconds_by_repetition": long_ttft_by_repetition,
        "corpus_client_wall_seconds": total("client_wall_seconds"),
        "corpus_client_wall_seconds_by_repetition": dict(totals["client_wall_seconds"]),
        "total_seconds": total("total_seconds"),
        "median_ttft_seconds": statistics.median(ttft_values),
        "speculative_rounds": rounds,
        "drafted_tokens": drafted,
        "accepted_tokens": accepted,
        "acceptance_rate": accepted / drafted if drafted else None,
        "completion_tokens_per_round": total("completion_tokens") / rounds if rounds else None,
        "fallback_steps": fallback,
        "prefix_reuse_paths": dict(sorted(reuse.items())),
    }


def modeled_session_seconds(
    reference: Mapping[str, Any], prefill_tokens_per_second: float, decode_tokens_per_second: float
) -> float:
    return (
        reference["computed_prefill_tokens"] / prefill_tokens_per_second
        + reference["decode_tokens"] / decode_tokens_per_second
    )


def workload_model(
    metrics: Mapping[str, Any], references: Sequence[Mapping[str, Any]]
) -> dict[str, dict[str, float]]:
    prefill = metrics["prefill_tokens_per_second_by_repetition"]
    decode = metrics["decode_tokens_per_second_by_repetition"]
    return {
        reference["label"]: {
            repetition: modeled_session_seconds(reference, prefill[repetition], decode[repetition])
            for repetition in prefill
        }
        for reference in references
    }


QUALITY_TOLERANCE = 0.02
OUTPUT_INFLATION_LIMIT = 1.25
QUALITY_CRITERIA: tuple[tuple[str, str, str], ...] = (
    # (criterion, aggregate key, relation to the reference run)
    ("secret_leaks", "secret_leak_count", "count_not_above"),
    ("redaction_control", "redaction_control_pass_rate", "rate_not_below"),
    ("critical_misses", "critical_miss_count", "count_not_above"),
    ("forbidden_claims", "forbidden_claim_count", "count_not_above"),
    ("failures", "failure_count", "count_not_above"),
    ("schema_valid_rate", "schema_valid_rate", "rate_within_tolerance"),
    ("required_fact_recall", "required_fact_recall", "rate_within_tolerance"),
    ("evidence_precision", "evidence_precision", "rate_within_tolerance"),
    ("tool_selection_accuracy", "tool_selection_accuracy", "rate_within_tolerance"),
    ("tool_argument_accuracy", "tool_argument_accuracy", "rate_within_tolerance"),
    ("unsupported_claim_rate", "unsupported_claim_rate", "rate_not_above_tolerance"),
    ("output_inflation", "mean_output_tokens", "inflation_limit"),
)


def role_corpus_run(directory: Path) -> dict[str, Any]:
    scores = corpus.read_json_object(directory / "scores.json")
    manifest = corpus.read_json_object(directory / "manifest.json")
    aggregate = scores.get("aggregate")
    if not isinstance(aggregate, dict):
        raise CampaignError(f"{directory} scores.json has no aggregate object")
    corpus_sha = corpus.require_sha256(manifest.get("corpus_sha256"), f"{directory} manifest corpus_sha256")
    label = manifest.get("label")
    if not isinstance(label, str) or not label:
        raise CampaignError(f"{directory} manifest has no label")
    return {
        "aggregate": aggregate,
        "corpus_sha256": corpus_sha,
        "label": label,
        "transport": manifest.get("transport"),
        "reasoning_level": manifest.get("reasoning_level"),
        "concurrency": manifest.get("concurrency"),
        "counts": scores.get("counts") if isinstance(scores.get("counts"), dict) else {},
        "scores_sha256": corpus.sha256_file(directory / "scores.json"),
        "manifest_sha256": corpus.sha256_file(directory / "manifest.json"),
    }


def metric_number(aggregate: Mapping[str, Any], key: str) -> float | None:
    value = aggregate.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CampaignError(f"role-corpus aggregate {key} must be a number or null")
    return float(value)


def quality_verdict(relation: str, candidate: float | None, reference: float | None) -> str:
    if candidate is None or reference is None:
        return "UNKNOWN"
    if relation == "count_not_above":
        return "PASS" if candidate <= reference else "FAIL"
    if relation == "rate_not_below":
        return "PASS" if candidate >= reference else "FAIL"
    if relation == "rate_within_tolerance":
        return "PASS" if candidate >= reference - QUALITY_TOLERANCE else "FAIL"
    if relation == "rate_not_above_tolerance":
        return "PASS" if candidate <= reference + QUALITY_TOLERANCE else "FAIL"
    if relation == "inflation_limit":
        return "PASS" if candidate <= reference * OUTPUT_INFLATION_LIMIT else "FAIL"
    raise AssertionError(relation)


def quality_receipt(
    *,
    matrix: LaneMatrix,
    arm_receipt: Mapping[str, Any],
    reference_receipt: Mapping[str, Any],
    candidate_run: Path,
    reference_run: Path,
) -> dict[str, Any]:
    label = arm_receipt.get("arm")
    reference_label = reference_receipt.get("arm")
    if not isinstance(label, str) or not isinstance(reference_label, str):
        raise CampaignError("arm receipts must carry arm labels")
    spec = matrix.spec(label)
    if spec.quality_gate != "role-corpus":
        raise CampaignError(f"arm {label} does not require a role-corpus quality receipt")
    if reference_label != matrix.incumbent:
        raise CampaignError("the quality reference must be the incumbent arm receipt")
    for receipt, name in ((arm_receipt, label), (reference_receipt, reference_label)):
        if receipt.get("artifact_type") != ARM_ARTIFACT_TYPE or receipt.get("lane") != matrix.lane:
            raise CampaignError(f"{name} is not an arm receipt for lane {matrix.lane}")
        if receipt.get("status") != "completed":
            raise CampaignError(f"{name} must complete before its quality screen is bound")
    if arm_receipt.get("campaign_id") != reference_receipt.get("campaign_id"):
        raise CampaignError("quality runs must come from one campaign")
    campaign_id = corpus.require_sha256(arm_receipt.get("campaign_id"), "campaign_id")
    candidate = role_corpus_run(candidate_run)
    reference = role_corpus_run(reference_run)
    if candidate["corpus_sha256"] != reference["corpus_sha256"]:
        raise CampaignError("role-corpus runs answered different corpora")
    for field in ("transport", "reasoning_level", "concurrency"):
        if candidate[field] != reference[field]:
            raise CampaignError(f"role-corpus runs differ in {field}")
    expected_labels = {
        f"{matrix.lane}/{label}/{campaign_id}": candidate["label"],
        f"{matrix.lane}/{reference_label}/{campaign_id}": reference["label"],
    }
    for expected, actual in expected_labels.items():
        if actual != expected:
            raise CampaignError(f"role-corpus run label {actual!r} does not bind {expected!r}")
    criteria: dict[str, str] = {}
    metrics: dict[str, dict[str, float | None]] = {}
    for name, key, relation in QUALITY_CRITERIA:
        candidate_value = metric_number(candidate["aggregate"], key)
        reference_value = metric_number(reference["aggregate"], key)
        criteria[name] = quality_verdict(relation, candidate_value, reference_value)
        metrics[key] = {"candidate": candidate_value, "reference": reference_value}
    canary_leaks = metric_number(candidate["aggregate"], "secret_leak_count")
    reference_leaks = metric_number(reference["aggregate"], "secret_leak_count")
    if canary_leaks is None or reference_leaks is None:
        raise CampaignError("role-corpus runs must record secret_leak_count")
    passed = all(verdict == "PASS" for verdict in criteria.values())
    return {
        "artifact_type": QUALITY_ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "generated_utc": corpus.utc_now(),
        "scope": (
            "relative role-corpus quality screen against the incumbent arm inside one campaign; "
            "concurrency-4 and cold-TTFT promotion criteria are not applicable to a single-request lane"
        ),
        "lane": matrix.lane,
        "arm": label,
        "reference_arm": reference_label,
        "campaign_id": campaign_id,
        "model_artifact_sha256": arm_receipt.get("model_artifact_sha256"),
        "configuration_sha256": arm_receipt.get("configuration_sha256"),
        "reference_configuration_sha256": reference_receipt.get("configuration_sha256"),
        "corpus_sha256": candidate["corpus_sha256"],
        "reasoning_level": candidate["reasoning_level"],
        "transport": candidate["transport"],
        "concurrency": candidate["concurrency"],
        "counts": {"candidate": candidate["counts"], "reference": reference["counts"]},
        "tolerance": QUALITY_TOLERANCE,
        "output_inflation_limit": OUTPUT_INFLATION_LIMIT,
        "metrics": metrics,
        "criteria": criteria,
        "canary_leak_count": int(canary_leaks),
        "reference_canary_leak_count": int(reference_leaks),
        "passed": passed,
        "evidence_sha256": {
            "candidate_scores": candidate["scores_sha256"],
            "candidate_manifest": candidate["manifest_sha256"],
            "reference_scores": reference["scores_sha256"],
            "reference_manifest": reference["manifest_sha256"],
        },
    }


def validate_quality_receipt(receipt: Mapping[str, Any], *, label: str, arm_receipt: Mapping[str, Any]) -> dict[str, Any]:
    if receipt.get("artifact_type") != QUALITY_ARTIFACT_TYPE:
        raise CampaignError(f"quality receipt for {label} has the wrong artifact_type")
    if receipt.get("arm") != label:
        raise CampaignError(f"quality receipt arm does not match {label}")
    for field in ("lane", "campaign_id", "model_artifact_sha256", "configuration_sha256"):
        if receipt.get(field) != arm_receipt.get(field):
            raise CampaignError(f"quality receipt for {label} does not bind the arm receipt {field}")
    passed = receipt.get("passed")
    if not isinstance(passed, bool):
        raise CampaignError(f"quality receipt for {label} must declare a boolean passed")
    canary_leaks = non_negative_int(receipt.get("canary_leak_count"), f"quality receipt {label} canary leaks")
    reference_leaks = non_negative_int(
        receipt.get("reference_canary_leak_count"), f"quality receipt {label} reference canary leaks"
    )
    if passed and canary_leaks > reference_leaks:
        raise CampaignError(f"quality receipt for {label} cannot pass with more canary leaks than its reference")
    criteria = receipt.get("criteria")
    if not isinstance(criteria, dict) or not criteria:
        raise CampaignError(f"quality receipt for {label} must record its criteria")
    for name, verdict in criteria.items():
        if verdict not in ("PASS", "FAIL", "UNKNOWN"):
            raise CampaignError(f"quality receipt for {label} criterion {name} has an invalid verdict")
    if passed and any(verdict != "PASS" for verdict in criteria.values()):
        raise CampaignError(f"quality receipt for {label} cannot pass with a failed or unknown criterion")
    return {
        "passed": passed,
        "canary_leak_count": canary_leaks,
        "reference_canary_leak_count": reference_leaks,
        "criteria": dict(sorted(criteria.items())),
        "metrics": receipt.get("metrics"),
        "reference_arm": receipt.get("reference_arm"),
        "reasoning_level": receipt.get("reasoning_level"),
        "corpus_sha256": receipt.get("corpus_sha256"),
        "evidence_sha256": receipt.get("evidence_sha256"),
    }


def combine_receipts(
    matrix: LaneMatrix,
    receipts: Sequence[Mapping[str, Any]],
    quality_receipts: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    expected_labels = [spec.label for spec in matrix.arms]
    by_label: dict[str, Mapping[str, Any]] = {}
    for receipt in receipts:
        if receipt.get("artifact_type") != ARM_ARTIFACT_TYPE:
            raise CampaignError("combine input has the wrong artifact_type")
        label = receipt.get("arm")
        if label not in expected_labels or label in by_label:
            raise CampaignError("combine inputs must contain each declared arm exactly once")
        by_label[label] = receipt
    if sorted(by_label) != sorted(expected_labels):
        raise CampaignError(f"combine inputs must contain arms {expected_labels}")

    campaign_ids = {receipt.get("campaign_id") for receipt in by_label.values()}
    if len(campaign_ids) != 1:
        raise CampaignError("arm receipts must share one campaign identity")
    campaign_id = corpus.require_sha256(next(iter(campaign_ids)), "campaign_id")
    instances = [
        receipt.get("server_instance_sha256")
        for receipt in by_label.values()
        if receipt.get("server_instance_sha256") is not None
    ]
    if len(set(instances)) != len(instances):
        raise CampaignError("arm receipts must come from distinct server processes")
    for label, receipt in by_label.items():
        spec = matrix.spec(label)
        if receipt.get("arm_spec") != spec.as_dict():
            raise CampaignError(f"arm {label} receipt drifted from the arms manifest")
        checks = {
            "lane": matrix.lane,
            "corpus_sha256": matrix.corpus_sha256,
            "source_commit": matrix.source_commit,
            "binary_sha256": matrix.binary_sha256,
            "model_artifact_sha256": matrix.artifact(spec.weights_id)["sha256"],
            "configuration_schema_version": corpus.CONFIGURATION_SCHEMA_VERSION,
        }
        for field, expected in checks.items():
            if receipt.get(field) != expected:
                raise CampaignError(f"arm {label} receipt {field} does not match the arms manifest")
        if receipt.get("status") not in ("completed", "failed"):
            raise CampaignError(f"arm {label} has an invalid status")
        if receipt.get("status") == "failed":
            failure = receipt.get("failure")
            if not isinstance(failure, dict) or not failure.get("code") or not failure.get("step_id"):
                raise CampaignError(f"failed arm {label} omitted failure evidence")
        configuration = receipt.get("configuration")
        capacity = receipt.get("capacity")
        if receipt.get("status") == "failed" and configuration is None and capacity is None:
            if receipt.get("server_instance_sha256") is not None:
                raise CampaignError(f"failed arm {label} has a server instance but no configuration")
            continue
        if not isinstance(configuration, dict) or receipt.get("configuration_sha256") != corpus.sha256_json(configuration):
            raise CampaignError(f"arm {label} configuration hash does not match its configuration")
        if not isinstance(capacity, dict):
            raise CampaignError(f"arm {label} receipt omitted capacity facts")
        positive_int(capacity.get("kv_capacity"), f"arm {label} kv_capacity")
    models = {receipt.get("model") for receipt in by_label.values()}
    if len(models) != 1:
        raise CampaignError("arm receipts must serve one public model id")

    incumbent_receipt = by_label[matrix.incumbent]
    if incumbent_receipt.get("status") != "completed":
        raise CampaignError("the incumbent arm must complete")
    incumbent_metrics = aggregate_arm(incumbent_receipt)
    incumbent_model = workload_model(incumbent_metrics, matrix.workload_references)
    incumbent_outputs = corpus.projection_map(incumbent_receipt["requests"], "incumbent")

    quality_by_label: dict[str, dict[str, Any]] = {}
    for label, quality in (quality_receipts or {}).items():
        if label not in by_label:
            raise CampaignError(f"quality receipt names unknown arm {label}")
        quality_by_label[label] = validate_quality_receipt(quality, label=label, arm_receipt=by_label[label])

    arms: dict[str, Any] = {}
    promotable: list[tuple[float, str]] = []
    pending_quality: list[str] = []
    capacity_findings: list[dict[str, Any]] = []
    for label in expected_labels:
        receipt = by_label[label]
        spec = matrix.spec(label)
        status = receipt["status"]
        capacity = receipt["capacity"]
        entry: dict[str, Any] = {
            "role": spec.role,
            "status": status,
            "spec": spec.as_dict(),
            "model_artifact_bytes": receipt.get("model_artifact_bytes"),
            "configuration_sha256": receipt.get("configuration_sha256"),
            "capacity": capacity,
            "evidence": {
                "arm_receipt_sha256": corpus.sha256_json(receipt),
                "trace_sha256": receipt.get("trace_sha256"),
                "server_log_sha256": receipt.get("server_log_sha256"),
                "server_instance_sha256": receipt.get("server_instance_sha256"),
            },
            "failure": receipt.get("failure"),
            "quality": quality_by_label.get(label),
        }
        holds_qualified_context = (
            capacity is not None and capacity["kv_capacity"] >= matrix.qualified_context
        )
        entry["holds_qualified_context"] = holds_qualified_context
        if spec.max_context > matrix.qualified_context and capacity is not None:
            capacity_findings.append(
                {
                    "arm": label,
                    "status": status,
                    "max_context": spec.max_context,
                    "kv_capacity": capacity["kv_capacity"],
                    "fits_declared_context": capacity["kv_capacity"] >= spec.max_context,
                    "peak_memory_used_mib": (capacity.get("device_memory") or {}).get("peak_memory_used_mib"),
                }
            )
        if status != "completed":
            entry["eligible"] = False
            entry["ineligibility"] = ["arm did not complete"]
            arms[label] = entry
            continue
        metrics = aggregate_arm(receipt)
        model = workload_model(metrics, matrix.workload_references)
        outputs = corpus.projection_map(receipt["requests"], label)
        mismatches = sorted(
            key for key in set(incumbent_outputs) | set(outputs) if incumbent_outputs.get(key) != outputs.get(key)
        )
        improvements = {
            reference: {
                repetition: 1.0 - model[reference][repetition] / incumbent_model[reference][repetition]
                for repetition in model[reference]
            }
            for reference in model
        }
        flat = [value for per_repetition in improvements.values() for value in per_repetition.values()]
        entry.update(
            {
                "metrics": metrics,
                "modeled_session_seconds": model,
                "improvement_vs_incumbent": improvements,
                "minimum_improvement_vs_incumbent": min(flat),
                "mean_improvement_vs_incumbent": statistics.fmean(flat),
                "decode_change_vs_incumbent_pct": (
                    metrics["decode_tokens_per_second"] / incumbent_metrics["decode_tokens_per_second"] - 1.0
                )
                * 100.0,
                "prefill_change_vs_incumbent_pct": (
                    metrics["prefill_tokens_per_second"] / incumbent_metrics["prefill_tokens_per_second"] - 1.0
                )
                * 100.0,
                "normalized_output_mismatch_count": len(mismatches),
                "normalized_output_mismatch_step_ids": mismatches,
                "repeatability_mismatch_step_ids": corpus.repeatability_mismatches(receipt["requests"], label),
            }
        )
        reasons: list[str] = []
        if spec.role != "candidate":
            reasons.append(f"{spec.role} arms are not promotion candidates")
        if not holds_qualified_context:
            reasons.append(
                f"automatic KV capacity {capacity['kv_capacity']} is below the qualified context {matrix.qualified_context}"
            )
        quality = quality_by_label.get(label)
        if spec.quality_gate == "role-corpus":
            if quality is None:
                reasons.append("role-corpus quality receipt is missing")
                if spec.role == "candidate" and min(flat) >= PROMOTION_MARGIN and holds_qualified_context:
                    pending_quality.append(label)
            elif not quality["passed"]:
                reasons.append("role-corpus quality screen failed")
        entry["eligible"] = not reasons
        entry["ineligibility"] = reasons
        entry["meets_promotion_margin"] = min(flat) >= PROMOTION_MARGIN
        if entry["eligible"] and entry["meets_promotion_margin"]:
            promotable.append((statistics.fmean(flat), label))
        arms[label] = entry

    if promotable:
        best = max(promotable)[1]
        decision = {
            "status": "decided",
            "action": f"promote {best}",
            "selected_arm": best,
            "incumbent_arm": matrix.incumbent,
            "promotion_margin": PROMOTION_MARGIN,
            "pending_quality_candidates": sorted(pending_quality),
            "reason": (
                f"{best} improves the modeled session time by at least {PROMOTION_MARGIN:.0%} for every "
                "workload reference in every repetition, holds the qualified context, and passed its quality gate"
            ),
        }
    else:
        decision = {
            "status": "decided",
            "action": f"retain {matrix.incumbent}",
            "selected_arm": matrix.incumbent,
            "incumbent_arm": matrix.incumbent,
            "promotion_margin": PROMOTION_MARGIN,
            "pending_quality_candidates": sorted(pending_quality),
            "reason": (
                "no eligible candidate improved the modeled session time by at least "
                f"{PROMOTION_MARGIN:.0%} for every workload reference in every repetition"
                + ("; candidates meeting the margin await role-corpus quality evidence" if pending_quality else "")
            ),
        }

    return {
        "artifact_type": LANE_ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "generated_utc": corpus.utc_now(),
        "scope": "within-lane experiment; not release qualification and not cross-lane comparable",
        "trust_boundary": (
            "owner measurement host and local arm receipts are trusted; hashes are provenance "
            "identifiers, not remote attestation"
        ),
        "lane": matrix.lane,
        "model": next(iter(models)),
        "campaign_id": campaign_id,
        "corpus_sha256": matrix.corpus_sha256,
        "source_commit": matrix.source_commit,
        "binary_sha256": matrix.binary_sha256,
        "qualified_context": matrix.qualified_context,
        "incumbent_arm": matrix.incumbent,
        "analysis": {
            "version": ANALYSIS_VERSION,
            "primary_metric": "modeled session engine seconds from measured prefill and decode throughput",
            "promotion_margin": PROMOTION_MARGIN,
            "requires_shared_campaign_identity": True,
            "requires_fresh_process_per_arm": True,
            "requires_margin_in_every_repetition_and_reference": True,
            "long_prefill_min_tokens": LONG_PREFILL_MIN_TOKENS,
            "workload_references": list(matrix.workload_references),
        },
        "arms": arms,
        "capacity_findings": capacity_findings,
        "decision": decision,
    }


def parse_quality_arguments(values: Sequence[str] | None) -> dict[str, Mapping[str, Any]]:
    receipts: dict[str, Mapping[str, Any]] = {}
    for item in values or ():
        label, separator, path = item.partition("=")
        if not separator or not label or not path:
            raise CampaignError("--quality-receipt expects <arm-label>=<path>")
        if label in receipts:
            raise CampaignError(f"duplicate quality receipt for {label}")
        receipts[label] = corpus.read_json_object(Path(path))
    return receipts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    contract = subparsers.add_parser("contract", help="render the lane arm matrix bound to the corpus contract")
    contract.add_argument("--arms", required=True)
    contract.add_argument("--lane", required=True)
    contract.add_argument("--output")

    init = subparsers.add_parser(
        "init", help="write an empty run trace so a server that never serves still yields a failed receipt"
    )
    init.add_argument("--arms", required=True)
    init.add_argument("--lane", required=True)
    init.add_argument("--arm", required=True)
    init.add_argument("--model", required=True)
    init.add_argument("--campaign-id", required=True)
    init.add_argument("--output", required=True)

    next_step = subparsers.add_parser("next-step", help="print the first incomplete step id of a run trace")
    next_step.add_argument("--trace", type=Path, required=True)

    run = subparsers.add_parser("run", help="execute or resume one arm against a running server")
    run.add_argument("--arms", required=True)
    run.add_argument("--lane", required=True)
    run.add_argument("--arm", required=True)
    run.add_argument("--base-url", required=True)
    run.add_argument("--api-key-file", required=True)
    run.add_argument("--model", required=True)
    run.add_argument("--campaign-id", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--timeout", type=float, default=900.0)
    run.add_argument("--resume", action="store_true")

    summarize = subparsers.add_parser("summarize", help="bind one run trace to server metrics")
    summarize.add_argument("--arms", required=True)
    summarize.add_argument("--lane", required=True)
    summarize.add_argument("--trace", type=Path, required=True)
    summarize.add_argument("--server-log", type=Path, required=True)
    summarize.add_argument("--memory-samples", type=Path)
    summarize.add_argument("--failure-code")
    summarize.add_argument("--failed-step-id")
    summarize.add_argument("--failure-evidence", type=Path)
    summarize.add_argument("--output", required=True)

    quality = subparsers.add_parser(
        "quality", help="bind a relative role-corpus screen to a candidate arm receipt"
    )
    quality.add_argument("--arms", required=True)
    quality.add_argument("--lane", required=True)
    quality.add_argument("--arm-receipt", type=Path, required=True)
    quality.add_argument("--reference-receipt", type=Path, required=True)
    quality.add_argument("--candidate-run", type=Path, required=True)
    quality.add_argument("--reference-run", type=Path, required=True)
    quality.add_argument("--output", required=True)

    combine = subparsers.add_parser("combine", help="validate and decide one lane")
    combine.add_argument("--arms", required=True)
    combine.add_argument("--lane", required=True)
    combine.add_argument("--arm-receipt", type=Path, action="append", required=True)
    combine.add_argument("--quality-receipt", action="append", metavar="LABEL=PATH")
    combine.add_argument("--output", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "contract":
            matrix = load_lane_matrix_file(Path(args.arms), args.lane)
            corpus.write_or_print(
                {
                    "lane": matrix.lane,
                    "corpus_sha256": matrix.corpus_sha256,
                    "request_count": corpus.corpus_manifest()["request_count"],
                    "source_commit": matrix.source_commit,
                    "binary_sha256": matrix.binary_sha256,
                    "qualified_context": matrix.qualified_context,
                    "incumbent": matrix.incumbent,
                    "arms": [spec.as_dict() for spec in matrix.arms],
                    "artifacts": {key: dict(value) for key, value in matrix.artifacts.items()},
                },
                args.output,
            )
        elif args.command == "init":
            matrix = load_lane_matrix_file(Path(args.arms), args.lane)
            spec = matrix.spec(args.arm)
            output = Path(args.output)
            if output.exists():
                raise CampaignError(f"{output} already exists")
            corpus.atomic_write_json(output, initial_run_state(matrix, spec, args.model, args.campaign_id))
        elif args.command == "next-step":
            print(next_incomplete_step(corpus.read_json_object(args.trace)))
        elif args.command == "run":
            state = run_campaign(args)
            print(
                corpus.canonical_json(
                    {
                        "status": "complete",
                        "lane": state["lane"],
                        "arm": state["arm"],
                        "campaign_id": state["campaign_id"],
                        "requests": len(corpus.flatten_steps(state)),
                        "corpus_sha256": state["corpus_sha256"],
                    }
                )
            )
        elif args.command == "summarize":
            matrix = load_lane_matrix_file(Path(args.arms), args.lane)
            receipt = summarize_arm(
                args.trace,
                args.server_log,
                matrix=matrix,
                memory_samples_path=args.memory_samples,
                failure_code=args.failure_code,
                failed_step_id=args.failed_step_id,
                failure_evidence_path=args.failure_evidence,
            )
            corpus.write_or_print(receipt, args.output)
        elif args.command == "quality":
            matrix = load_lane_matrix_file(Path(args.arms), args.lane)
            corpus.write_or_print(
                quality_receipt(
                    matrix=matrix,
                    arm_receipt=corpus.read_json_object(args.arm_receipt),
                    reference_receipt=corpus.read_json_object(args.reference_receipt),
                    candidate_run=args.candidate_run,
                    reference_run=args.reference_run,
                ),
                args.output,
            )
        elif args.command == "combine":
            matrix = load_lane_matrix_file(Path(args.arms), args.lane)
            receipts = [corpus.read_json_object(path) for path in args.arm_receipt]
            corpus.write_or_print(
                combine_receipts(matrix, receipts, parse_quality_arguments(args.quality_receipt)),
                args.output,
            )
        else:
            raise AssertionError(args.command)
    except (CampaignError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
