from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from typing import Any
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_variant_campaign", ROOT / "scripts" / "run_variant_campaign.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
CORPUS = MODULE.corpus

ARMS_PATH = ROOT / "docs" / "measurements" / "2026-09-04-variant-campaign-arms.json"
COMMIT = "d" * 40
BINARY = "b" * 64
GW_SHA = "1" * 64
NVFP4_SHA = "2" * 64
CAMPAIGN = "c" * 64
LANE = "rtx-test"
MODEL = "qwen3.8-27b"
STEP_NAMES = {
    "responses_short": ("single",),
    "responses_long_decode": ("single",),
    "chat_history_p50": ("single",),
    "chat_history_p90": ("single",),
    "chat_tool_roundtrip": ("tool_call", "tool_result"),
    "responses_medium_branch": ("base", "continuation", "branch"),
    "responses_long_replay": ("base", "continuation", "branch"),
}


def arm(label: str, role: str, **overrides: Any) -> dict[str, Any]:
    spec = {
        "label": label,
        "role": role,
        "weights_id": "groupwise-int",
        "kv_dtype": "bf16",
        "prefill_chunk": 1024,
        "max_context": 131072,
        "speculative_backend": "mtp",
        "speculative_draft_window": 3,
        "quality_gate": "byte-equivalent",
    }
    spec.update(overrides)
    return spec


def test_manifest() -> dict[str, Any]:
    return {
        "artifact_type": MODULE.ARMS_ARTIFACT_TYPE,
        "schema_version": 1,
        "corpus_sha256": CORPUS.corpus_manifest()["sha256"],
        "workload_references": [
            {"label": "prefill-heavy", "computed_prefill_tokens": 600000, "prefix_hit_tokens": 0, "decode_tokens": 30000},
            {"label": "decode-heavy", "computed_prefill_tokens": 100000, "prefix_hit_tokens": 0, "decode_tokens": 200000},
        ],
        "artifacts": {
            "groupwise-int": {"sha256": GW_SHA, "bytes": 1000},
            "nvfp4": {"sha256": NVFP4_SHA, "bytes": 1200},
        },
        "lanes": {
            LANE: {
                "source_commit": COMMIT,
                "binary_sha256": BINARY,
                "qualified_context": 131072,
                "incumbent": "inc",
                "arms": [
                    arm("inc", "incumbent"),
                    arm("ctl", "control", speculative_backend="none", speculative_draft_window=0),
                    arm("chunk", "candidate", prefill_chunk=2048),
                    arm("nvfp4", "candidate", weights_id="nvfp4", quality_gate="role-corpus"),
                ],
            }
        },
    }


def matrix_for(manifest: dict[str, Any] | None = None) -> Any:
    return MODULE.load_lane_matrix(manifest or test_manifest(), LANE)


def step_ids() -> list[str]:
    return [
        f"{scenario}/r{repetition}/{step}"
        for repetition in range(CORPUS.REPETITIONS)
        for scenario, steps in STEP_NAMES.items()
        for step in steps
    ]


def identity(kind: str, label: str, suffix: str) -> str:
    return CORPUS.scoped_identity(
        kind,
        campaign_id=CAMPAIGN,
        corpus_sha256=CORPUS.corpus_manifest()["sha256"],
        lane=LANE,
        arm=label,
        suffix=suffix,
    )


def server_start(spec: dict[str, Any], instance: str, *, kv_capacity: int = 131072) -> dict[str, Any]:
    artifact = test_manifest()["artifacts"][spec["weights_id"]]
    speculative = spec["speculative_backend"] == "mtp"
    return {
        "event": "server_start",
        "server_instance_id": instance,
        "server": {
            "api_key_configured": True,
            "cors_enabled": False,
            "default_output_tokens": 32768,
            "default_preserve_thinking": True,
            "default_thinking": True,
            "default_thinking_budget": None,
            "host": "127.0.0.1",
            "max_request_bytes": 1048576,
            "port": 18082,
            "public_model_id": MODEL,
            "request_log_jsonl": "/private/requests.jsonl",
        },
        "identity": {
            "upstream_base_sha": COMMIT,
            "patch_stack_sha": COMMIT,
            "source_dirty": False,
            "build_profile": "variant-test",
            "build_type": "Release",
            "config_sha256": "a" * 64,
            "cxx_compiler": "test",
            "cuda_compiler": "test",
            "cuda_toolkit": "13.1",
            "deployment_profile": "variant-test",
            "binary_sha256": BINARY,
            "model_artifact_sha256": artifact["sha256"],
            "target": "qwen3_8_27b",
            "model_id": MODEL,
            "weights_id": spec["weights_id"],
        },
        "artifact": {
            "bytes_read": artifact["bytes"],
            "host_to_device_bytes": artifact["bytes"],
            "load_seconds": 12.5,
            "peak_staging_bytes": 1,
            "resource_count": 6,
            "size_bytes": artifact["bytes"],
            "target": "qwen3_8_27b",
            "tensor_count": 1118,
            "upload_seconds": 1.0,
            "weights_id": spec["weights_id"],
        },
        "engine": {
            "cuda_graph": True,
            "device": 0,
            "kv_cache": {"int8": "int8-group64"}.get(spec["kv_dtype"], spec["kv_dtype"]),
            "kv_capacity": kv_capacity,
            "kv_capacity_max_page_groups": 64,
            "kv_capacity_mode": "auto",
            "kv_capacity_page_groups": 32,
            "log_stats_interval_ms": 0,
            "max_concurrency": 1,
            "max_context": spec["max_context"],
            "max_pending_requests": 16,
            "pending_timeout_ms": 30000,
            "prefill_chunk": spec["prefill_chunk"],
            "prefix_reuse": True,
            "proposal_head": "optimized" if speculative else "full",
            "speculative_backend": spec["speculative_backend"],
            "speculative_draft_window": spec["speculative_draft_window"],
            "vision": True,
        },
        "sampling_defaults": {
            "greedy": True,
            "non_thinking": {},
            "omitted_seed": "random",
            "server_overrides": {},
            "thinking": {},
        },
    }


def request_done(
    spec: dict[str, Any],
    instance: str,
    step_id: str,
    *,
    prefill_rate: float,
    decode_rate: float,
    projection: str,
) -> dict[str, Any]:
    scenario = step_id.split("/")[0]
    base = step_id.endswith("/base")
    computed = 8192 if (scenario == "responses_long_replay" and base) else 256
    completion = 512 if scenario == "responses_long_decode" else 80
    prefill_seconds = computed / prefill_rate
    decode_seconds = (completion - 1) / decode_rate
    speculative = spec["speculative_backend"] == "mtp"
    return {
        "event": "request_done",
        "server_instance_id": instance,
        "request": {
            "protocol": "openai_responses" if scenario.startswith("responses") else "openai_chat_completions",
            "enable_thinking": True,
            "client_identity": {
                "request_sha256": identity("request", spec["label"], step_id),
                "session_sha256": identity("session", spec["label"], step_id.rsplit("/", 1)[0]),
            },
        },
        "result": {
            "prompt_tokens": computed + 64,
            "completion_tokens": completion,
            "computed_prefill_tokens": computed,
            "prefix_cache_hit_tokens": 64,
            "prefix_reuse_path": "root",
            "finish_reason": "output_limit",
            "tool_call_count": 0,
        },
        "timings_seconds": {
            "prepare": 0.001,
            "ttft": prefill_seconds + 0.01,
            "prefill": prefill_seconds,
            "decode": decode_seconds,
            "total": prefill_seconds + decode_seconds + 0.02,
        },
        "speculative": {
            "backend": spec["speculative_backend"],
            "draft_window": spec["speculative_draft_window"],
            "rounds": 40 if speculative else 0,
            "drafted_tokens": 120 if speculative else 0,
            "accepted_tokens": 70 if speculative else 0,
            "fallback_steps": 0,
            "accepted_per_position": [30, 22, 18] if speculative else [],
        },
        "_projection": projection,
    }


def write_arm_fixtures(
    directory: Path,
    label: str,
    *,
    prefill_rate: float,
    decode_rate: float,
    instance: str,
    kv_capacity: int = 131072,
    projection: str = "f" * 64,
    manifest: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    lane_manifest = manifest or test_manifest()
    spec = next(item for item in lane_manifest["lanes"][LANE]["arms"] if item["label"] == label)
    trace = {
        "artifact_type": MODULE.RUN_ARTIFACT_TYPE,
        "schema_version": 1,
        "created_utc": "2026-09-04T00:00:00Z",
        "lane": LANE,
        "arm": label,
        "arm_spec": MODULE.parse_spec(spec).as_dict(),
        "model": MODEL,
        "campaign_id": CAMPAIGN,
        "corpus_sha256": CORPUS.corpus_manifest()["sha256"],
        "expected_scenarios": len(STEP_NAMES) * CORPUS.REPETITIONS,
        "expected_requests": len(step_ids()),
        "scenarios": {},
    }
    records = [server_start(spec, instance, kv_capacity=kv_capacity)]
    for step_id in step_ids():
        scenario_key = step_id.rsplit("/", 1)[0]
        record = request_done(
            spec, instance, step_id, prefill_rate=prefill_rate, decode_rate=decode_rate, projection=projection
        )
        record.pop("_projection")
        records.append(record)
        result = {
            "step_id": step_id,
            "request_sha256": identity("request", label, step_id),
            "protocol": record["request"]["protocol"],
            "prompt_tokens": record["result"]["prompt_tokens"],
            "completion_tokens": record["result"]["completion_tokens"],
            "wall_seconds": record["timings_seconds"]["total"] + 0.05,
            "projection_sha256": projection,
        }
        trace["scenarios"].setdefault(scenario_key, {"status": "complete", "steps": []})["steps"].append(result)
    directory.mkdir(parents=True, exist_ok=True)
    trace_path = directory / f"run-{label}.json"
    log_path = directory / f"requests-{label}.jsonl"
    trace_path.write_text(json.dumps(trace), encoding="utf-8")
    log_path.write_text("\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8")
    return trace_path, log_path


def receipt_for(
    directory: Path,
    label: str,
    *,
    prefill_rate: float,
    decode_rate: float,
    instance: str,
    kv_capacity: int = 131072,
    projection: str = "f" * 64,
    memory_samples: Path | None = None,
) -> dict[str, Any]:
    trace_path, log_path = write_arm_fixtures(
        directory,
        label,
        prefill_rate=prefill_rate,
        decode_rate=decode_rate,
        instance=instance,
        kv_capacity=kv_capacity,
        projection=projection,
    )
    return MODULE.summarize_arm(trace_path, log_path, matrix=matrix_for(), memory_samples_path=memory_samples)


def quality_receipt(arm_receipt: dict[str, Any], *, passed: bool, leaks: int = 0) -> dict[str, Any]:
    return {
        "artifact_type": MODULE.QUALITY_ARTIFACT_TYPE,
        "arm": arm_receipt["arm"],
        "lane": arm_receipt["lane"],
        "campaign_id": arm_receipt["campaign_id"],
        "model_artifact_sha256": arm_receipt["model_artifact_sha256"],
        "configuration_sha256": arm_receipt["configuration_sha256"],
        "passed": passed,
        "canary_leak_count": leaks,
        "reference_canary_leak_count": 0,
        "criteria": {"schema_valid_rate": "PASS", "required_fact_recall": "PASS" if passed else "FAIL", "secret_leaks": "PASS" if leaks == 0 else "FAIL"},
        "reference_arm": "inc",
    }


ROLE_AGGREGATE = {
    "required_fact_recall": 0.97,
    "evidence_precision": 0.99,
    "unsupported_claim_rate": 0.0,
    "forbidden_claim_count": 0,
    "critical_miss_count": 0,
    "schema_valid_rate": 1.0,
    "tool_selection_accuracy": 1.0,
    "tool_argument_accuracy": 1.0,
    "secret_leak_count": 0,
    "redaction_control_pass_rate": 1.0,
    "duplicate_rate": 0.0,
    "mean_output_tokens": 300.0,
    "mean_reasoning_tokens": 900.0,
    "cold_ttft_ms": 400.0,
    "warm_ttft_ms_p50": 200.0,
    "warm_ttft_ms_p95": 800.0,
    "prefill_tps": 3000.0,
    "decode_tps": 170.0,
    "wall_ms_p50": 4000.0,
    "wall_ms_p95": 12000.0,
    "failure_count": 0,
    "retry_count": 0,
}


def write_role_run(directory: Path, label: str, aggregate: dict[str, Any], *, concurrency: int = 1) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "scores.json").write_text(
        json.dumps({"aggregate": aggregate, "counts": {"cases": 89, "redaction_control_cases": 8}}),
        encoding="utf-8",
    )
    (directory / "manifest.json").write_text(
        json.dumps(
            {
                "label": label,
                "corpus_sha256": "7" * 64,
                "transport": "raw-http",
                "reasoning_level": "low",
                "concurrency": concurrency,
            }
        ),
        encoding="utf-8",
    )
    return directory


class ArmsManifestTests(unittest.TestCase):
    def test_committed_manifest_binds_the_frozen_corpus_for_every_lane(self) -> None:
        manifest = json.loads(ARMS_PATH.read_text(encoding="utf-8"))
        for lane in ("rtx5090", "rtx4090", "rtx3090"):
            matrix = MODULE.load_lane_matrix(manifest, lane)
            self.assertEqual(matrix.corpus_sha256, CORPUS.corpus_manifest()["sha256"])
            incumbent = matrix.spec(matrix.incumbent)
            self.assertEqual(incumbent.role, "incumbent")
            self.assertEqual(incumbent.speculative_backend, "mtp")
            self.assertEqual(incumbent.speculative_draft_window, 3)
            self.assertLessEqual(matrix.qualified_context, incumbent.max_context)
            for spec in matrix.arms:
                if spec.weights_id != incumbent.weights_id or spec.kv_dtype != incumbent.kv_dtype:
                    self.assertEqual(spec.quality_gate, "role-corpus", spec.label)
        self.assertEqual(manifest["lanes"]["rtx3090"]["qualified_context"], 65536)
        self.assertEqual(manifest["artifacts"]["nvfp4"]["bytes"] - manifest["artifacts"]["groupwise-int"]["bytes"], 3282163712)

    def test_manifest_rejects_drift(self) -> None:
        manifest = test_manifest()
        manifest["lanes"][LANE]["arms"][1]["role"] = "incumbent"
        with self.assertRaisesRegex(MODULE.CampaignError, "exactly one incumbent"):
            matrix_for(manifest)
        manifest = test_manifest()
        manifest["corpus_sha256"] = "e" * 64
        with self.assertRaisesRegex(MODULE.CampaignError, "corpus does not match"):
            matrix_for(manifest)
        manifest = test_manifest()
        manifest["lanes"][LANE]["arms"][0]["speculative_draft_window"] = 0
        with self.assertRaisesRegex(MODULE.CampaignError, "draft window does not match"):
            matrix_for(manifest)
        manifest = test_manifest()
        manifest["lanes"][LANE]["arms"][2]["label"] = "Chunk 2048"
        with self.assertRaisesRegex(MODULE.CampaignError, "lowercase"):
            matrix_for(manifest)


class EngineKvNameTests(unittest.TestCase):
    def test_engine_reported_int8_group_name_binds_to_int8_and_foreign_names_fail(self) -> None:
        manifest = test_manifest()
        manifest["lanes"][LANE]["arms"][2]["kv_dtype"] = "int8"
        manifest["lanes"][LANE]["arms"][2]["quality_gate"] = "role-corpus"
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            trace_path, log_path = write_arm_fixtures(
                directory, "chunk", prefill_rate=3000.0, decode_rate=170.0, instance="i-int8", manifest=manifest
            )
            receipt = MODULE.summarize_arm(trace_path, log_path, matrix=matrix_for(manifest))
            self.assertEqual(receipt["configuration"]["engine"]["kv_cache"], "int8-group64")
            self.assertEqual(receipt["arm_spec"]["kv_dtype"], "int8")
            lines = log_path.read_text(encoding="utf-8").splitlines()
            start = json.loads(lines[0])
            start["engine"]["kv_cache"] = "bf16"
            log_path.write_text("\n".join([json.dumps(start), *lines[1:]]) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.CampaignError, "is not a 'int8' format"):
                MODULE.summarize_arm(trace_path, log_path, matrix=matrix_for(manifest))


class SummarizeTests(unittest.TestCase):
    def test_summarize_binds_fresh_process_spec_and_capacity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            samples = directory / "vram.jsonl"
            samples.write_text('{"memory_used_mib": 20000}\n{"memory_used_mib": 24100}\n', encoding="utf-8")
            receipt = receipt_for(
                directory, "nvfp4", prefill_rate=8000.0, decode_rate=150.0, instance="i-nvfp4", memory_samples=samples
            )
        self.assertEqual(receipt["status"], "completed")
        self.assertEqual(receipt["arm_spec"]["weights_id"], "nvfp4")
        self.assertEqual(receipt["model_artifact_sha256"], NVFP4_SHA)
        self.assertEqual(receipt["model_artifact_bytes"], 1200)
        self.assertEqual(receipt["capacity"]["kv_capacity"], 131072)
        self.assertEqual(receipt["capacity"]["artifact_load_seconds"], 12.5)
        self.assertEqual(receipt["capacity"]["device_memory"]["peak_memory_used_mib"], 24100)
        self.assertEqual(receipt["completed_requests"], 24)
        self.assertNotIn("request_log_jsonl", receipt["configuration"]["server"])
        self.assertEqual(receipt["configuration"]["engine"]["kv_cache"], "bf16")

    def test_summarize_rejects_second_process_and_spec_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            trace_path, log_path = write_arm_fixtures(
                directory, "chunk", prefill_rate=3000.0, decode_rate=170.0, instance="i-chunk"
            )
            lines = log_path.read_text(encoding="utf-8").splitlines()
            second = json.loads(lines[0])
            second["server_instance_id"] = "i-other"
            log_path.write_text("\n".join([lines[0], json.dumps(second), *lines[1:]]) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.CampaignError, "exactly one fresh server process"):
                MODULE.summarize_arm(trace_path, log_path, matrix=matrix_for())

            start = json.loads(lines[0])
            start["engine"]["prefill_chunk"] = 1024
            log_path.write_text("\n".join([json.dumps(start), *lines[1:]]) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.CampaignError, "engine.prefill_chunk mismatch"):
                MODULE.summarize_arm(trace_path, log_path, matrix=matrix_for())

            start = json.loads(lines[0])
            start["artifact"]["size_bytes"] = 999
            log_path.write_text("\n".join([json.dumps(start), *lines[1:]]) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.CampaignError, "artifact.size_bytes mismatch"):
                MODULE.summarize_arm(trace_path, log_path, matrix=matrix_for())

            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            trace["arm_spec"]["prefill_chunk"] = 4096
            trace_path.write_text(json.dumps(trace), encoding="utf-8")
            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.CampaignError, "drifted from the arms manifest"):
                MODULE.summarize_arm(trace_path, log_path, matrix=matrix_for())


class AggregateTests(unittest.TestCase):
    def test_aggregate_reports_prefill_decode_long_prefill_and_wall(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            receipt = receipt_for(Path(tmp), "inc", prefill_rate=3000.0, decode_rate=170.0, instance="i-inc")
        metrics = MODULE.aggregate_arm(receipt)
        self.assertEqual(metrics["request_count"], 24)
        self.assertAlmostEqual(metrics["prefill_tokens_per_second"], 3000.0, places=6)
        self.assertAlmostEqual(metrics["decode_tokens_per_second"], 170.0, places=6)
        self.assertEqual(metrics["long_prefill_tokens"], 8192 * 2)
        self.assertAlmostEqual(metrics["long_prefill_tokens_per_second"], 3000.0, places=6)
        for repetition in ("r0", "r1"):
            self.assertAlmostEqual(metrics["long_prefill_ttft_seconds_by_repetition"][repetition], 8192 / 3000.0 + 0.01)
            self.assertGreater(metrics["corpus_client_wall_seconds_by_repetition"][repetition], 0.0)
        self.assertEqual(metrics["decode_throughput_spread_pct"], 0.0)
        self.assertAlmostEqual(metrics["acceptance_rate"], 70 / 120)

    def test_workload_model_weights_prefill_and_decode(self) -> None:
        reference = {"label": "x", "computed_prefill_tokens": 6000, "decode_tokens": 340}
        self.assertAlmostEqual(MODULE.modeled_session_seconds(reference, 3000.0, 170.0), 4.0)


class CombineTests(unittest.TestCase):
    def build(self, directory: Path, **rates: tuple[float, float]) -> dict[str, dict[str, Any]]:
        receipts = {}
        for label, (prefill, decode) in rates.items():
            receipts[label] = receipt_for(
                directory, label, prefill_rate=prefill, decode_rate=decode, instance=f"i-{label}"
            )
        return receipts

    def test_promotes_chunk_candidate_that_clears_margin_everywhere(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            receipts = self.build(
                Path(tmp),
                inc=(3000.0, 170.0),
                ctl=(3000.0, 80.0),
                chunk=(3600.0, 190.0),
                nvfp4=(3000.0, 170.0),
            )
            lane = MODULE.combine_receipts(matrix_for(), list(receipts.values()))
        self.assertEqual(lane["decision"]["selected_arm"], "chunk")
        self.assertEqual(lane["decision"]["action"], "promote chunk")
        self.assertTrue(lane["arms"]["chunk"]["eligible"])
        self.assertGreaterEqual(lane["arms"]["chunk"]["minimum_improvement_vs_incumbent"], 0.05)
        self.assertFalse(lane["arms"]["ctl"]["eligible"])
        self.assertIn("control arms are not promotion candidates", lane["arms"]["ctl"]["ineligibility"])
        self.assertFalse(lane["arms"]["nvfp4"]["eligible"])
        self.assertEqual(lane["decision"]["pending_quality_candidates"], [])
        self.assertEqual(lane["arms"]["inc"]["normalized_output_mismatch_count"], 0)
        self.assertEqual(
            lane["arms"]["chunk"]["evidence"]["arm_receipt_sha256"], CORPUS.sha256_json(receipts["chunk"])
        )

    def test_prefill_only_win_does_not_clear_a_decode_heavy_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            receipts = self.build(
                Path(tmp),
                inc=(3000.0, 170.0),
                ctl=(3000.0, 80.0),
                chunk=(3000.0, 170.0),
                nvfp4=(9000.0, 150.0),
            )
            nvfp4_quality = quality_receipt(receipts["nvfp4"], passed=True)
            lane = MODULE.combine_receipts(
                matrix_for(), list(receipts.values()), {"nvfp4": nvfp4_quality}
            )
        entry = lane["arms"]["nvfp4"]
        self.assertTrue(entry["eligible"])
        self.assertGreater(entry["improvement_vs_incumbent"]["prefill-heavy"]["r0"], 0.05)
        self.assertLess(entry["improvement_vs_incumbent"]["decode-heavy"]["r0"], 0.05)
        self.assertFalse(entry["meets_promotion_margin"])
        self.assertEqual(lane["decision"]["selected_arm"], "inc")
        self.assertEqual(lane["decision"]["action"], "retain inc")

    def test_role_corpus_candidate_needs_a_passing_quality_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            receipts = self.build(
                Path(tmp),
                inc=(3000.0, 170.0),
                ctl=(3000.0, 80.0),
                chunk=(3000.0, 170.0),
                nvfp4=(9000.0, 190.0),
            )
            pending = MODULE.combine_receipts(matrix_for(), list(receipts.values()))
            self.assertEqual(pending["decision"]["selected_arm"], "inc")
            self.assertEqual(pending["decision"]["pending_quality_candidates"], ["nvfp4"])
            self.assertIn("quality receipt is missing", pending["arms"]["nvfp4"]["ineligibility"][0])

            failed = MODULE.combine_receipts(
                matrix_for(),
                list(receipts.values()),
                {"nvfp4": quality_receipt(receipts["nvfp4"], passed=False, leaks=3)},
            )
            self.assertEqual(failed["decision"]["selected_arm"], "inc")
            self.assertEqual(failed["decision"]["pending_quality_candidates"], [])
            self.assertIn("quality screen failed", failed["arms"]["nvfp4"]["ineligibility"][0])

            promoted = MODULE.combine_receipts(
                matrix_for(),
                list(receipts.values()),
                {"nvfp4": quality_receipt(receipts["nvfp4"], passed=True)},
            )
            self.assertEqual(promoted["decision"]["selected_arm"], "nvfp4")
            self.assertEqual(promoted["arms"]["nvfp4"]["quality"]["canary_leak_count"], 0)

            with self.assertRaisesRegex(MODULE.CampaignError, "more canary leaks than its reference"):
                MODULE.combine_receipts(
                    matrix_for(),
                    list(receipts.values()),
                    {"nvfp4": quality_receipt(receipts["nvfp4"], passed=True, leaks=1)},
                )
            unbound = quality_receipt(receipts["nvfp4"], passed=True)
            unbound["configuration_sha256"] = "9" * 64
            with self.assertRaisesRegex(MODULE.CampaignError, "does not bind the arm receipt"):
                MODULE.combine_receipts(matrix_for(), list(receipts.values()), {"nvfp4": unbound})

    def test_capacity_below_qualified_context_blocks_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            receipts = self.build(directory, inc=(3000.0, 170.0), ctl=(3000.0, 80.0), chunk=(3000.0, 170.0))
            receipts["nvfp4"] = receipt_for(
                directory, "nvfp4", prefill_rate=9000.0, decode_rate=190.0, instance="i-nvfp4", kv_capacity=98304
            )
            lane = MODULE.combine_receipts(
                matrix_for(),
                list(receipts.values()),
                {"nvfp4": quality_receipt(receipts["nvfp4"], passed=True)},
            )
        self.assertFalse(lane["arms"]["nvfp4"]["holds_qualified_context"])
        self.assertFalse(lane["arms"]["nvfp4"]["eligible"])
        self.assertEqual(lane["decision"]["selected_arm"], "inc")
        self.assertEqual(lane["decision"]["pending_quality_candidates"], [])

    def test_combine_requires_shared_campaign_and_distinct_processes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            receipts = self.build(
                Path(tmp), inc=(3000.0, 170.0), ctl=(3000.0, 80.0), chunk=(3000.0, 170.0), nvfp4=(3000.0, 170.0)
            )
        drifted = copy.deepcopy(receipts)
        drifted["chunk"]["campaign_id"] = "e" * 64
        with self.assertRaisesRegex(MODULE.CampaignError, "share one campaign identity"):
            MODULE.combine_receipts(matrix_for(), list(drifted.values()))
        shared = copy.deepcopy(receipts)
        shared["chunk"]["server_instance_sha256"] = shared["inc"]["server_instance_sha256"]
        with self.assertRaisesRegex(MODULE.CampaignError, "distinct server processes"):
            MODULE.combine_receipts(matrix_for(), list(shared.values()))
        with self.assertRaisesRegex(MODULE.CampaignError, "each declared arm exactly once"):
            MODULE.combine_receipts(matrix_for(), list(receipts.values())[:3] + [receipts["inc"]])

    def test_failed_arm_is_recorded_and_never_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            receipts = self.build(directory, inc=(3000.0, 170.0), ctl=(3000.0, 80.0), chunk=(3600.0, 190.0))
            trace_path, log_path = write_arm_fixtures(
                directory, "nvfp4", prefill_rate=9000.0, decode_rate=190.0, instance="i-nvfp4"
            )
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            trace["scenarios"].pop("responses_long_replay/r1")
            trace_path.write_text(json.dumps(trace), encoding="utf-8")
            evidence = directory / "server-nvfp4.stderr.log"
            evidence.write_text("CUDA out of memory\n", encoding="utf-8")
            receipts["nvfp4"] = MODULE.summarize_arm(
                trace_path,
                log_path,
                matrix=matrix_for(),
                failure_code="server_exit",
                failed_step_id="responses_long_replay/r1/base",
                failure_evidence_path=evidence,
            )
            lane = MODULE.combine_receipts(matrix_for(), list(receipts.values()))
        self.assertEqual(receipts["nvfp4"]["status"], "failed")
        self.assertEqual(lane["arms"]["nvfp4"]["ineligibility"], ["arm did not complete"])
        self.assertEqual(lane["decision"]["selected_arm"], "chunk")


class QualityBindingTests(unittest.TestCase):
    def receipts(self, directory: Path) -> dict[str, dict[str, Any]]:
        return {
            "inc": receipt_for(directory, "inc", prefill_rate=3000.0, decode_rate=170.0, instance="i-inc"),
            "nvfp4": receipt_for(directory, "nvfp4", prefill_rate=9000.0, decode_rate=190.0, instance="i-nvfp4"),
        }

    def bind(self, directory: Path, receipts: dict[str, dict[str, Any]], candidate_aggregate: dict[str, Any]) -> dict[str, Any]:
        reference_run = write_role_run(directory / "role-inc", f"{LANE}/inc/{CAMPAIGN}", ROLE_AGGREGATE)
        candidate_run = write_role_run(directory / "role-nvfp4", f"{LANE}/nvfp4/{CAMPAIGN}", candidate_aggregate)
        return MODULE.quality_receipt(
            matrix=matrix_for(),
            arm_receipt=receipts["nvfp4"],
            reference_receipt=receipts["inc"],
            candidate_run=candidate_run,
            reference_run=reference_run,
        )

    def test_relative_screen_passes_within_tolerance_and_ignores_concurrency_criteria(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            receipts = self.receipts(directory)
            candidate = dict(ROLE_AGGREGATE, required_fact_recall=0.955, mean_output_tokens=360.0, cold_ttft_ms=900.0)
            receipt = self.bind(directory, receipts, candidate)
            self.assertTrue(receipt["passed"])
            self.assertEqual(receipt["canary_leak_count"], 0)
            self.assertEqual(receipt["configuration_sha256"], receipts["nvfp4"]["configuration_sha256"])
            self.assertEqual(receipt["reference_arm"], "inc")
            self.assertNotIn("concurrency_4", receipt["criteria"])
            self.assertNotIn("cold_ttft", receipt["criteria"])
            self.assertTrue(all(verdict == "PASS" for verdict in receipt["criteria"].values()))
            lane = MODULE.combine_receipts(
                matrix_for(),
                [
                    receipts["inc"],
                    receipt_for(directory, "ctl", prefill_rate=3000.0, decode_rate=80.0, instance="i-ctl"),
                    receipt_for(directory, "chunk", prefill_rate=3000.0, decode_rate=170.0, instance="i-chunk"),
                    receipts["nvfp4"],
                ],
                {"nvfp4": receipt},
            )
            self.assertEqual(lane["decision"]["selected_arm"], "nvfp4")

    def test_relative_screen_fails_on_leak_recall_drop_or_inflation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            receipts = self.receipts(directory)
            leaked = self.bind(directory, receipts, dict(ROLE_AGGREGATE, secret_leak_count=1, redaction_control_pass_rate=0.875))
            self.assertFalse(leaked["passed"])
            self.assertEqual(leaked["criteria"]["secret_leaks"], "FAIL")
            self.assertEqual(leaked["canary_leak_count"], 1)
            recall = self.bind(directory, receipts, dict(ROLE_AGGREGATE, required_fact_recall=0.94))
            self.assertEqual(recall["criteria"]["required_fact_recall"], "FAIL")
            self.assertFalse(recall["passed"])
            inflated = self.bind(directory, receipts, dict(ROLE_AGGREGATE, mean_output_tokens=400.0))
            self.assertEqual(inflated["criteria"]["output_inflation"], "FAIL")
            unknown = self.bind(directory, receipts, dict(ROLE_AGGREGATE, tool_argument_accuracy=None))
            self.assertEqual(unknown["criteria"]["tool_argument_accuracy"], "UNKNOWN")
            self.assertFalse(unknown["passed"])

    def test_quality_binding_refuses_mislabelled_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            receipts = self.receipts(directory)
            reference_run = write_role_run(directory / "role-inc", f"{LANE}/inc/{CAMPAIGN}", ROLE_AGGREGATE)
            wrong = write_role_run(directory / "role-wrong", f"{LANE}/chunk/{CAMPAIGN}", ROLE_AGGREGATE)
            with self.assertRaisesRegex(MODULE.CampaignError, "does not bind"):
                MODULE.quality_receipt(
                    matrix=matrix_for(),
                    arm_receipt=receipts["nvfp4"],
                    reference_receipt=receipts["inc"],
                    candidate_run=wrong,
                    reference_run=reference_run,
                )
            different = write_role_run(directory / "role-c4", f"{LANE}/nvfp4/{CAMPAIGN}", ROLE_AGGREGATE, concurrency=4)
            with self.assertRaisesRegex(MODULE.CampaignError, "differ in concurrency"):
                MODULE.quality_receipt(
                    matrix=matrix_for(),
                    arm_receipt=receipts["nvfp4"],
                    reference_receipt=receipts["inc"],
                    candidate_run=different,
                    reference_run=reference_run,
                )
            with self.assertRaisesRegex(MODULE.CampaignError, "does not require a role-corpus"):
                MODULE.quality_receipt(
                    matrix=matrix_for(),
                    arm_receipt=receipts["inc"],
                    reference_receipt=receipts["inc"],
                    candidate_run=reference_run,
                    reference_run=reference_run,
                )


class DeadServerTests(unittest.TestCase):
    def test_server_that_never_starts_yields_failed_receipt_without_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            spec = next(item for item in test_manifest()["lanes"][LANE]["arms"] if item["label"] == "nvfp4")
            trace_path = directory / "run-nvfp4.json"
            trace_path.write_text(
                json.dumps(
                    MODULE.initial_run_state(matrix_for(), MODULE.parse_spec(spec), MODEL, CAMPAIGN)
                ),
                encoding="utf-8",
            )
            evidence = directory / "server-nvfp4.stderr.log"
            evidence.write_text("artifact load failed\n", encoding="utf-8")
            receipt = MODULE.summarize_arm(
                trace_path,
                directory / "requests-nvfp4.jsonl",
                matrix=matrix_for(),
                failure_code="server_start",
                failed_step_id="responses_short/r0/single",
                failure_evidence_path=evidence,
            )
            self.assertEqual(receipt["status"], "failed")
            self.assertIsNone(receipt["configuration"])
            self.assertIsNone(receipt["capacity"])
            self.assertIsNone(receipt["server_instance_sha256"])
            self.assertEqual(receipt["completed_requests"], 0)
            others = {
                label: receipt_for(directory, label, prefill_rate=3000.0, decode_rate=rate, instance=f"i-{label}")
                for label, rate in (("inc", 170.0), ("ctl", 80.0), ("chunk", 170.0))
            }
            lane = MODULE.combine_receipts(matrix_for(), [*others.values(), receipt])
            self.assertEqual(lane["arms"]["nvfp4"]["ineligibility"], ["arm did not complete"])
            self.assertFalse(lane["arms"]["nvfp4"]["holds_qualified_context"])
            self.assertEqual(lane["decision"]["selected_arm"], "inc")
            complete_trace, complete_log = write_arm_fixtures(
                directory / "complete", "nvfp4", prefill_rate=9000.0, decode_rate=190.0, instance="i-late"
            )
            complete_log.unlink()
            with self.assertRaisesRegex(MODULE.CampaignError, "missing"):
                MODULE.summarize_arm(complete_trace, complete_log, matrix=matrix_for())


class NextStepTests(unittest.TestCase):
    def test_next_step_walks_corpus_order_and_cli_round_trips(self) -> None:
        spec = next(item for item in test_manifest()["lanes"][LANE]["arms"] if item["label"] == "chunk")
        state = MODULE.initial_run_state(matrix_for(), MODULE.parse_spec(spec), MODEL, CAMPAIGN)
        self.assertEqual(MODULE.next_incomplete_step(state), "responses_short/r0/single")
        state["scenarios"]["responses_short/r0"] = {"status": "complete", "steps": []}
        state["scenarios"]["responses_long_decode/r0"] = {"status": "complete", "steps": []}
        self.assertEqual(MODULE.next_incomplete_step(state), "chat_history_p50/r0/single")
        for name in STEP_NAMES:
            for repetition in range(CORPUS.REPETITIONS):
                state["scenarios"][f"{name}/r{repetition}"] = {"status": "complete", "steps": []}
        with self.assertRaisesRegex(MODULE.CampaignError, "no incomplete step"):
            MODULE.next_incomplete_step(state)
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "arms.json"
            manifest_path.write_text(json.dumps(test_manifest()), encoding="utf-8")
            trace = Path(tmp) / "run-chunk.json"
            self.assertEqual(
                MODULE.main(
                    [
                        "init", "--arms", str(manifest_path), "--lane", LANE, "--arm", "chunk",
                        "--model", MODEL, "--campaign-id", CAMPAIGN, "--output", str(trace),
                    ]
                ),
                0,
            )
            self.assertEqual(
                MODULE.main(
                    [
                        "init", "--arms", str(manifest_path), "--lane", LANE, "--arm", "chunk",
                        "--model", MODEL, "--campaign-id", CAMPAIGN, "--output", str(trace),
                    ]
                ),
                2,
            )
            self.assertEqual(MODULE.main(["next-step", "--trace", str(trace)]), 0)


if __name__ == "__main__":
    unittest.main()
