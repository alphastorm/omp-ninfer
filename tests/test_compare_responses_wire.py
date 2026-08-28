from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "compare_responses_wire", ROOT / "scripts" / "compare_responses_wire.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def capture(
    *,
    response_id: str,
    item_id: str,
    call_id: str,
    secret: str,
    workspace: str,
    created_at: int,
    input_tokens: int,
) -> dict:
    item = {
        "id": item_id,
        "type": "function_call",
        "call_id": call_id,
        "name": "exec",
        "arguments": json.dumps({"cmd": f"cat {workspace}/input.txt"}),
    }
    return {
        "artifact_type": MODULE.ARTIFACT_TYPE,
        "schema_version": 1,
        "scenario": "tool-round-trip",
        "requests": [
            {
                "method": "POST",
                "path": "/v1/responses",
                "headers": {
                    "Authorization": "Bearer test-key",
                    "X-NInfer-Session": secret,
                },
                "body": {
                    "model": "q38-ninfer",
                    "previous_response_id": response_id,
                    "input": [
                        {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": "ok",
                        }
                    ],
                },
            }
        ],
        "events": [
            {
                "type": "response.created",
                "sequence_number": 0,
                "response": {"id": response_id, "created_at": created_at},
            },
            {
                "type": "response.output_item.added",
                "sequence_number": 1,
                "response_id": response_id,
                "item": item,
            },
            {
                "type": "response.output_item.done",
                "sequence_number": 2,
                "response_id": response_id,
                "item": item,
            },
            {
                "type": "response.completed",
                "sequence_number": 3,
                "response": {
                    "id": response_id,
                    "created_at": created_at,
                    "output": [item],
                    "usage": {"input_tokens": input_tokens, "output_tokens": 7},
                },
            },
        ],
    }


class ResponsesWireComparisonTest(unittest.TestCase):
    def setUp(self) -> None:
        self.reference = capture(
            response_id="resp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            item_id="fc_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            call_id="call_cccccccccccccccccccccccccccccccc",
            secret="1" * 64,
            workspace="/reference/workspace",
            created_at=100,
            input_tokens=50,
        )
        self.candidate = capture(
            response_id="resp_dddddddddddddddddddddddddddddddd",
            item_id="fc_eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
            call_id="call_ffffffffffffffffffffffffffffffff",
            secret="2" * 64,
            workspace="/candidate/workspace",
            created_at=999,
            input_tokens=73,
        )

    def compare(self) -> dict:
        return MODULE.compare_captures(
            self.reference,
            self.candidate,
            reference_workspace=Path("/reference/workspace"),
            candidate_workspace=Path("/candidate/workspace"),
        )

    def test_volatile_ids_credentials_usage_and_paths_normalize(self) -> None:
        result = self.compare()
        self.assertTrue(result["valid"])
        self.assertTrue(result["equivalent"])
        self.assertEqual(result["diff"], [])
        serialized = json.dumps(
            MODULE.normalize_capture(self.reference, workspace=Path("/reference/workspace"))
        )
        self.assertNotIn("test-key", serialized)
        self.assertNotIn("/reference/workspace", serialized)
        self.assertNotIn("1" * 64, serialized)

    def test_semantic_request_difference_produces_readable_diff(self) -> None:
        self.candidate["requests"][0]["body"]["input"][0]["type"] = "custom_tool_call_output"
        result = self.compare()
        self.assertTrue(result["valid"])
        self.assertFalse(result["equivalent"])
        self.assertTrue(any("custom_tool_call_output" in line for line in result["diff"]))

    def test_sequence_gaps_fail_before_equivalence(self) -> None:
        self.candidate["events"][2]["sequence_number"] = 9
        result = self.compare()
        self.assertFalse(result["valid"])
        self.assertTrue(any("contiguous" in error for error in result["errors"]))

    def test_item_identity_must_survive_added_to_done(self) -> None:
        self.candidate["events"][2]["item"] = dict(
            self.candidate["events"][2]["item"], id="fc_11111111111111111111111111111111"
        )
        result = self.compare()
        self.assertFalse(result["valid"])
        self.assertTrue(any("output item ids" in error for error in result["errors"]))

    def test_capture_loader_rejects_wrong_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "capture.json"
            path.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.CaptureError, "unsupported capture identity"):
                MODULE.load(path)


if __name__ == "__main__":
    unittest.main()
