"""The RTX 4090 route driver accounts for every request the documented acceptance sends."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("accept_rtx4090_route",
                                              ROOT / "scripts" / "hosts" / "accept-rtx4090-route.py")
assert SPEC is not None and SPEC.loader is not None
DRIVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER)


def completed(*tool_calls: int) -> list[dict]:
    return [{"result": {"tool_call_count": count}} for count in tool_calls]


class RequestShapeTests(unittest.TestCase):
    def test_extra_tool_calls_pass_and_unexplained_requests_fail(self) -> None:
        """v0.8.6's second RTX 4090 run made two tool calls: five requests and a passing documented
        route, which the driver refused as not exactly one call. A request that no tool call
        explains is a hidden retry or a duplicate and still fails."""
        cases = {
            (1, 0, 0, 0): True,      # read, answer, nonce plant, nonce recall
            (1, 1, 0, 0, 0): True,   # glob, then read
            (1, 0, 0, 0, 0): False,  # one request too many
            (1, 0, 0): False,        # one request missing
            (0, 0, 0): False,        # no tool call
        }
        for calls, passed in cases.items():
            with self.subTest(calls=calls):
                self.assertEqual(all(DRIVER.request_shape(completed(*calls)).values()), passed)


if __name__ == "__main__":
    unittest.main()
