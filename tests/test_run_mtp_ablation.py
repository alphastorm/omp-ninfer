from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_mtp_ablation", ROOT / "scripts" / "run_mtp_ablation.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
COMMIT = "d" * 40


def arm_receipt(arm: int, decode_seconds: float) -> dict[str, object]:
    expected_requests = MODULE.corpus_manifest()["request_count"]
    configuration = {"fixture": "frozen"}
    return {
        "artifact_type": MODULE.ARM_ARTIFACT_TYPE,
        "schema_version": 1,
        "status": "completed",
        "lane": "rtx-test",
        "arm": arm,
        "model": "qwen3.8-27b",
        "corpus_sha256": MODULE.corpus_manifest()["sha256"],
        "source_commit": COMMIT,
        "binary_sha256": SHA_B,
        "model_artifact_sha256": SHA_C,
        "configuration": configuration,
        "configuration_sha256": MODULE.sha256_json(configuration),
        "trace_sha256": SHA_A,
        "server_log_sha256": SHA_B,
        "server_instance_sha256s": [SHA_C],
        "completed_requests": expected_requests,
        "expected_requests": expected_requests,
        "requests": [
            {
                "step_id": (
                    f"synthetic/r{index // (expected_requests // 2)}/"
                    f"step-{index % (expected_requests // 2):02d}"
                ),
                "projection_sha256": "f" * 64,
                "prompt_tokens": 64,
                "completion_tokens": 101,
                "client_wall_seconds": decode_seconds + 0.5,
                "prefix_reuse_path": "root",
                "timings_seconds": {
                    "prepare": 0.01,
                    "ttft": 0.1,
                    "prefill": 0.1,
                    "decode": decode_seconds,
                    "total": decode_seconds + 0.2,
                },
                "speculative": {
                    "backend": "none" if arm == 0 else "mtp",
                    "draft_window": arm,
                    "rounds": 0 if arm == 0 else 50,
                    "drafted_tokens": 0 if arm == 0 else 50 * arm,
                    "accepted_tokens": 0 if arm == 0 else 75,
                    "fallback_steps": 0 if arm == 0 else 10,
                },
            }
            for index in range(expected_requests)
        ],
    }


class CorpusContractTests(unittest.TestCase):
    def test_corpus_is_deterministic_content_safe_and_agent_shaped(self) -> None:
        first = MODULE.corpus_manifest()
        second = MODULE.corpus_manifest()

        self.assertEqual(first, second)
        self.assertEqual(first["request_count"], 24)
        self.assertEqual(first["repetitions"], 2)
        self.assertEqual(
            first["sha256"],
            MODULE.sha256_json({key: value for key, value in first.items() if key != "sha256"}),
        )
        names = {scenario["name"] for scenario in first["scenarios"]}
        self.assertIn("chat_tool_roundtrip", names)
        self.assertIn("responses_long_replay", names)
        serialized = MODULE.canonical_json(first)
        for private_marker in ("/Users/", "C:\\\\Users\\\\", "api_key", "Authorization"):
            self.assertNotIn(private_marker, serialized)

    def test_resume_skips_completed_scenarios(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "state.json"
            key = root / "api-key"
            key.write_text("not-a-real-secret\n", encoding="utf-8")
            state = MODULE.initial_run_state("rtx-test", 3, "qwen3.8-27b")
            manifest = MODULE.corpus_manifest()
            for repetition in range(MODULE.REPETITIONS):
                for definition in manifest["scenarios"]:
                    scenario_key = f"{definition['name']}/r{repetition}"
                    state["scenarios"][scenario_key] = {
                        "status": "complete",
                        "steps": [
                            {
                                "step_id": f"{scenario_key}/done",
                                "request_sha256": SHA_A,
                                "projection_sha256": SHA_B,
                            }
                        ],
                    }
            missing_key = "responses_short/r1"
            del state["scenarios"][missing_key]
            MODULE.atomic_write_json(output, state)
            args = argparse.Namespace(
                base_url="http://127.0.0.1:1",
                api_key_file=str(key),
                model="qwen3.8-27b",
                lane="rtx-test",
                arm=3,
                output=str(output),
                timeout=1.0,
                resume=True,
            )
            replacement = [
                {
                    "step_id": f"{missing_key}/single",
                    "request_sha256": SHA_C,
                    "projection_sha256": SHA_B,
                }
            ]
            with (
                mock.patch.object(MODULE.HttpClient, "health"),
                mock.patch.object(MODULE, "execute_scenario", return_value=replacement) as execute,
            ):
                result = MODULE.run_campaign(args)

            execute.assert_called_once()
            self.assertEqual(execute.call_args.kwargs["name"], "responses_short")
            self.assertEqual(execute.call_args.kwargs["repetition"], 1)
            self.assertEqual(result["scenarios"][missing_key]["steps"], replacement)

    def test_thinking_extension_is_only_sent_to_chat(self) -> None:
        class CaptureClient:
            def __init__(self) -> None:
                self.calls: list[tuple[str, dict[str, object]]] = []

            def request(
                self, _: str, path: str, payload: dict[str, object]
            ) -> dict[str, object]:
                self.calls.append((path, payload))
                if path == "/v1/responses":
                    return {
                        "status": "completed",
                        "output": [],
                        "usage": {"input_tokens": 1, "output_tokens": 0},
                    }
                return {
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": "ok"},
                        }
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                }

        client = CaptureClient()
        common = {
            "client": client,
            "model": "qwen3.8-27b",
            "session": SHA_A,
            "request_id": SHA_B,
            "step_id": "compatibility",
        }
        MODULE.request_step(
            **common,
            protocol="openai_responses",
            payload={"input": "hello", "max_output_tokens": 16},
        )
        MODULE.request_step(
            **common,
            protocol="openai_chat_completions",
            payload={"messages": [{"role": "user", "content": "hello"}]},
        )

        self.assertNotIn("enable_thinking", client.calls[0][1])
        self.assertIs(client.calls[1][1]["enable_thinking"], True)

    def test_output_projection_includes_client_visible_reasoning(self) -> None:
        chat = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"reasoning_content": "think", "content": "answer"},
                }
            ]
        }
        responses = {
            "status": "completed",
            "output": [
                {
                    "id": "rs_generated",
                    "type": "reasoning",
                    "status": "completed",
                    "summary": [],
                    "content": [{"type": "reasoning_text", "text": "think"}],
                },
                {
                    "id": "msg_generated",
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "answer"}],
                },
            ],
        }

        chat_projection = MODULE.response_projection("openai_chat_completions", chat)
        responses_projection = MODULE.response_projection("openai_responses", responses)

        self.assertEqual(chat_projection["reasoning_content"], "think")
        self.assertEqual(responses_projection["output"][0]["content"][0]["text"], "think")
        self.assertNotIn("rs_generated", MODULE.canonical_json(responses_projection))
        changed = json.loads(json.dumps(responses))
        changed["output"][0]["content"][0]["text"] = "different thought"
        self.assertNotEqual(
            MODULE.sha256_json(responses_projection),
            MODULE.sha256_json(MODULE.response_projection("openai_responses", changed)),
        )

    def test_tool_roundtrip_preserves_assistant_reasoning(self) -> None:
        message = MODULE.chat_tool_message(
            {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "reasoning_content": "I need the build result.",
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "lookup_build",
                                        "arguments": (
                                            '{"target":"linux-arm64","revision":"deadbeef"}'
                                        ),
                                    }
                                }
                            ],
                        }
                    }
                ]
            }
        )

        self.assertEqual(message["reasoning_content"], "I need the build result.")


class ReceiptTests(unittest.TestCase):
    def test_safe_configuration_excludes_arm_specific_runtime_state(self) -> None:
        baseline = {
            "server": {},
            "identity": {},
            "artifact": {"tensor_count": 1104},
            "engine": {"proposal_head": "full"},
            "sampling_defaults": {},
        }
        speculative = {
            "server": {},
            "identity": {},
            "artifact": {"tensor_count": 1118},
            "engine": {"proposal_head": "optimized"},
            "sampling_defaults": {},
        }

        self.assertEqual(
            MODULE.safe_configuration(baseline), MODULE.safe_configuration(speculative)
        )

    def test_summarize_binds_trace_to_clean_server_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            trace = root / "trace.json"
            log = root / "requests.jsonl"
            request_id = "1" * 64
            instance = "srv-test"
            trace.write_text(
                json.dumps(
                    {
                        "artifact_type": MODULE.RUN_ARTIFACT_TYPE,
                        "schema_version": 1,
                        "lane": "rtx-test",
                        "arm": 3,
                        "model": "qwen3.8-27b",
                        "corpus_sha256": SHA_A,
                        "expected_requests": 2,
                        "scenarios": {
                            "responses_short/r0": {
                                "status": "complete",
                                "steps": [
                                    {
                                        "step_id": "responses_short/r0/single",
                                        "request_sha256": request_id,
                                        "protocol": "openai_responses",
                                        "prompt_tokens": 64,
                                        "completion_tokens": 32,
                                        "wall_seconds": 2.0,
                                        "projection_sha256": SHA_B,
                                    },
                                    {
                                        "step_id": "responses_short/r1/single",
                                        "request_sha256": "2" * 64,
                                        "protocol": "openai_responses",
                                        "prompt_tokens": 64,
                                        "completion_tokens": 32,
                                        "wall_seconds": 2.1,
                                        "projection_sha256": SHA_B,
                                    },
                                ],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            start = {
                "event": "server_start",
                "server_instance_id": instance,
                "server": {
                    "public_model_id": "qwen3.8-27b",
                    "request_log_jsonl": "C:/private/requests.jsonl",
                    "default_output_tokens": 32768,
                    "default_thinking": True,
                    "default_thinking_budget": None,
                    "default_preserve_thinking": True,
                },
                "identity": {
                    "upstream_base_sha": COMMIT,
                    "patch_stack_sha": COMMIT,
                    "source_dirty": False,
                    "build_profile": "mtp-depth-ablation-test",
                    "build_type": "Release",
                    "cxx_compiler": "test",
                    "cuda_compiler": "test",
                    "cuda_toolkit": "13.1",
                    "deployment_profile": "mtp-depth-ablation-test",
                    "binary_sha256": SHA_B,
                    "model_artifact_sha256": SHA_C,
                    "target": "qwen3_8_27b",
                    "model_id": "artifact-default-model-id",
                    "weights_id": "weights-test",
                },
                "artifact": {
                    "size_bytes": 1,
                    "target": "qwen3_8_27b",
                    "weights_id": "weights-test",
                    "tensor_count": 1,
                    "resource_count": 1,
                },
                "engine": {
                    "device": 0,
                    "max_context": 65536,
                    "kv_capacity_mode": "automatic",
                    "kv_capacity": 65536,
                    "max_concurrency": 1,
                    "max_pending_requests": 1,
                    "pending_timeout_ms": 0,
                    "prefill_chunk": 1024,
                    "kv_cache": "int8",
                    "vision": False,
                    "cuda_graph": True,
                    "prefix_reuse": True,
                    "speculative_backend": "mtp",
                    "speculative_draft_window": 3,
                    "proposal_head": "optimized",
                },
                "sampling_defaults": {"greedy": True},
            }
            done = {
                "event": "request_done",
                "server_instance_id": instance,
                "request": {
                    "protocol": "openai_responses",
                    "enable_thinking": True,
                    "client_identity": {"request_sha256": request_id},
                },
                "result": {
                    "prompt_tokens": 64,
                    "completion_tokens": 32,
                    "computed_prefill_tokens": 64,
                    "prefix_cache_hit_tokens": 0,
                    "prefix_reuse_path": "root",
                    "finish_reason": "output_limit",
                    "tool_call_count": 0,
                },
                "timings_seconds": {
                    "prepare": 0.01,
                    "ttft": 0.1,
                    "prefill": 0.1,
                    "decode": 1.0,
                    "total": 1.2,
                },
                "speculative": {
                    "backend": "mtp",
                    "draft_window": 3,
                    "rounds": 16,
                    "drafted_tokens": 48,
                    "accepted_tokens": 20,
                    "fallback_steps": 4,
                    "accepted_per_position": [12, 6, 2],
                },
            }
            resumed_instance = "srv-test-resumed"
            resumed_start = {**start, "server_instance_id": resumed_instance}
            resumed_done = json.loads(json.dumps(done))
            resumed_done["server_instance_id"] = resumed_instance
            resumed_done["request"]["client_identity"]["request_sha256"] = "2" * 64
            log.write_text(
                "\n".join(
                    json.dumps(item) for item in (start, done, resumed_start, resumed_done)
                )
                + "\n",
                encoding="utf-8",
            )

            receipt = MODULE.summarize_arm(
                trace,
                log,
                expected_binary_sha256=SHA_B,
                expected_model_sha256=SHA_C,
                expected_source_commit=COMMIT,
            )

            self.assertEqual(receipt["binary_sha256"], SHA_B)
            self.assertEqual(receipt["requests"][0]["projection_sha256"], SHA_B)
            self.assertEqual(len(receipt["server_instance_sha256s"]), 2)
            self.assertNotIn("request_log_jsonl", MODULE.canonical_json(receipt["configuration"]))
            self.assertNotIn("C:/private", MODULE.canonical_json(receipt))

            evidence = root / "failure.log"
            evidence.write_text("cudaErrorIllegalAddress\n", encoding="utf-8")
            incomplete = json.loads(trace.read_text(encoding="utf-8"))
            incomplete["expected_requests"] = 3
            trace.write_text(json.dumps(incomplete), encoding="utf-8")
            failed = MODULE.summarize_arm(
                trace,
                log,
                expected_binary_sha256=SHA_B,
                expected_model_sha256=SHA_C,
                expected_source_commit=COMMIT,
                failure_code="cuda_illegal_address",
                failed_step_id="responses_long_replay/r1/continuation",
                failure_evidence_path=evidence,
            )
            self.assertEqual(failed["status"], "failed")
            self.assertEqual(failed["completed_requests"], 2)
            self.assertEqual(failed["expected_requests"], 3)
            self.assertEqual(failed["failure"]["evidence_sha256"], MODULE.sha256_file(evidence))

    def test_combine_enforces_frozen_binary_and_exact_outputs(self) -> None:
        receipts = [arm_receipt(arm, seconds) for arm, seconds in zip(MODULE.ARMS, (20.0, 10.0, 9.8, 8.0))]
        combined = MODULE.combine_receipts(receipts)
        self.assertEqual(combined["decision"]["selected_arm"], 7)
        self.assertEqual(combined["analysis"]["version"], 2)
        self.assertTrue(
            combined["analysis"]["cross_arm_attribution_requires_repeatable_baseline"]
        )
        self.assertTrue(combined["quality"]["normalized_outputs_identical"])
        self.assertEqual(
            combined["arms"]["0"]["normalized_output_sha256"][
                "synthetic/r0/step-00"
            ],
            "f" * 64,
        )
        self.assertEqual(
            combined["arms"]["0"]["evidence"]["arm_receipt_content_sha256"],
            MODULE.sha256_json(receipts[0]),
        )

        receipts[2]["binary_sha256"] = "0" * 64
        with self.assertRaisesRegex(MODULE.AblationError, "binary_sha256"):
            MODULE.combine_receipts(receipts)

    def test_combine_rejects_stale_corpus_and_inconsistent_counts(self) -> None:
        receipts = [
            arm_receipt(arm, seconds)
            for arm, seconds in zip(MODULE.ARMS, (20.0, 10.0, 9.8, 8.0))
        ]
        for receipt in receipts:
            receipt["corpus_sha256"] = SHA_A
        with self.assertRaisesRegex(MODULE.AblationError, "corpus_sha256"):
            MODULE.combine_receipts(receipts)

        receipts = [
            arm_receipt(arm, seconds)
            for arm, seconds in zip(MODULE.ARMS, (20.0, 10.0, 9.8, 8.0))
        ]
        receipts[2]["completed_requests"] = 23
        with self.assertRaisesRegex(MODULE.AblationError, "request counts"):
            MODULE.combine_receipts(receipts)

        receipts = [
            arm_receipt(arm, seconds)
            for arm, seconds in zip(MODULE.ARMS, (20.0, 10.0, 9.8, 8.0))
        ]
        receipts[2]["configuration"] = {"fixture": "changed"}
        with self.assertRaisesRegex(MODULE.AblationError, "configuration_sha256"):
            MODULE.combine_receipts(receipts)

    def test_combine_disqualifies_output_drift_and_retains_inside_margin(self) -> None:
        receipts = [arm_receipt(arm, seconds) for arm, seconds in zip(MODULE.ARMS, (20.0, 10.0, 9.7, 8.0))]
        combined = MODULE.combine_receipts(receipts)
        self.assertEqual(combined["decision"]["selected_arm"], 7)

        requests = receipts[3]["requests"]
        assert isinstance(requests, list) and isinstance(requests[0], dict)
        requests[0]["projection_sha256"] = "0" * 64
        drifted = MODULE.combine_receipts(receipts)
        self.assertEqual(drifted["decision"]["selected_arm"], 3)
        self.assertEqual(drifted["decision"]["fastest_observed_arm"], 7)
        self.assertNotIn(7, drifted["quality"]["eligible_arms"])
        self.assertFalse(drifted["arms"]["7"]["quality_eligible"])
        self.assertFalse(drifted["quality"]["normalized_outputs_identical"])

    def test_combine_makes_no_decision_when_mtp0_is_not_repeatable(self) -> None:
        receipts = [
            arm_receipt(arm, seconds)
            for arm, seconds in zip(MODULE.ARMS, (20.0, 10.0, 9.7, 8.0))
        ]
        for receipt in receipts:
            requests = receipt["requests"]
            assert isinstance(requests, list) and isinstance(requests[0], dict)
            requests[0]["projection_sha256"] = SHA_A

        combined = MODULE.combine_receipts(receipts)

        self.assertFalse(combined["quality"]["baseline_repeatable"])
        self.assertFalse(combined["quality"]["normalized_outputs_identical"])
        self.assertEqual(combined["quality"]["eligible_arms"], [])
        self.assertIsNone(combined["decision"]["selected_arm"])
        self.assertEqual(combined["decision"]["status"], "inconclusive")
        self.assertEqual(combined["decision"]["action"], "no draft-depth decision")

    def test_combine_disqualifies_failed_arm(self) -> None:
        receipts = [
            arm_receipt(arm, seconds)
            for arm, seconds in zip(MODULE.ARMS, (20.0, 10.0, 9.7, 8.0))
        ]
        failed = receipts[3]
        failed["status"] = "failed"
        failed["completed_requests"] = 23
        failed["expected_requests"] = 24
        failed["failure"] = {
            "code": "cuda_illegal_address",
            "step_id": "responses_long_replay/r1/continuation",
            "evidence_sha256": SHA_A,
            "evidence_size_bytes": 100,
        }
        requests = failed["requests"]
        assert isinstance(requests, list)
        failed["requests"] = requests[:23]

        combined = MODULE.combine_receipts(receipts)

        self.assertEqual(combined["decision"]["selected_arm"], 3)
        self.assertEqual(combined["quality"]["failed_arms"], [7])
        self.assertFalse(combined["arms"]["7"]["quality_eligible"])
        self.assertEqual(combined["arms"]["7"]["failure"], failed["failure"])

    def test_combine_replaces_output_drifted_incumbent(self) -> None:
        receipts = [
            arm_receipt(arm, seconds)
            for arm, seconds in zip(MODULE.ARMS, (20.0, 10.0, 9.7, 8.0))
        ]
        for receipt, output_sha in zip(receipts[1:], (SHA_A, SHA_C, "0" * 64)):
            requests = receipt["requests"]
            assert isinstance(requests, list) and isinstance(requests[0], dict)
            requests[0]["projection_sha256"] = output_sha

        combined = MODULE.combine_receipts(receipts)

        self.assertEqual(combined["quality"]["reference_arm"], 0)
        self.assertEqual(combined["quality"]["eligible_arms"], [0])
        self.assertEqual(combined["decision"]["selected_arm"], 0)
        self.assertEqual(
            combined["decision"]["action"], "replace output-drifted MTP3"
        )


if __name__ == "__main__":
    unittest.main()
