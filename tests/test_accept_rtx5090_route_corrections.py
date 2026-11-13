"""A corrected 5090 attempt carries its corrections before it spends a window."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("accept_rtx5090_routes",
                                              ROOT / "scripts" / "hosts" / "accept-rtx5090-routes.py")
assert SPEC is not None and SPEC.loader is not None
DRIVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER)


class CorrectionRecordTests(unittest.TestCase):
    def write(self, directory: str, value: object) -> None:
        (Path(directory) / "corrections.json").write_text(json.dumps(value))

    def test_records_written_before_the_window_are_carried_into_the_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            record = {"route": "host", "change": "the documented route printed the marker twice"}
            self.write(directory, [record])
            self.assertEqual(DRIVER.correction_records(directory), [record])

    def test_a_corrected_attempt_is_refused_without_usable_records(self) -> None:
        cases = {
            "missing": None,
            "empty": [],
            "not a list": {"route": "host", "change": "x"},
            "record is not an object": ["host printed the marker twice"],
            "route missing": [{"change": "the documented route printed the marker twice"}],
            "change blank": [{"route": "host", "change": "  "}],
            "change not a string": [{"route": "host", "change": ["twice"]}],
        }
        for label, value in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as directory:
                if value is not None:
                    self.write(directory, value)
                with self.assertRaises(AssertionError):
                    DRIVER.correction_records(directory)

    def failed_window(self, action: str, hold_acquired: bool) -> tuple[str, list]:
        with tempfile.TemporaryDirectory() as directory:
            root, prior = Path(directory) / "window", Path(directory) / "prior"
            root.mkdir()
            prior.mkdir()
            (root / "preflight.json").write_text(json.dumps({"status": "passed"}))
            (prior / "window-attempt.json").write_text(json.dumps({"attempt": "initial"}))
            (prior / "restoration.json").write_text(json.dumps({
                "window_seconds": 1, **{field: True for field in (
                    "checkout_restored", "documented_key_restored", "beta_absent",
                    "documented_directories_restored")}}))
            for label in ("host", "mac", "windows"):
                (prior / (label + "-route.json")).write_text(json.dumps({"status": "passed"}))
            args = [
                "accept-rtx5090-routes.py", "--action", action,
                "--workspace", str(root), "--prior-workspace", str(prior),
                "--release", "v0.18.0", "--candidate", "1" * 40,
                "--wsl-workspace", "/fixture/window", "--windows-workspace", "C:/fixture",
                "--wsl-host", "fixture-wsl", "--windows-host", "fixture-windows",
                "--route-ssh-destination", "fixture-route", "--production-image", "fixture-image",
                "--window-dir", "/fixture/window",
            ]

            def command(argv, **kwargs):
                code = 1 if "--action begin " in str(argv[-1]) else 0
                return subprocess.CompletedProcess(argv, code, "", "")

            with mock.patch.object(sys, "argv", args), \
                    mock.patch.object(DRIVER, "documented_model", return_value="fixture-model"), \
                    mock.patch.object(DRIVER.socket, "socket"), \
                    mock.patch.object(DRIVER, "acquire_windows_hold",
                                      side_effect=None if hold_acquired else RuntimeError("hold refused")), \
                    mock.patch.object(DRIVER.subprocess, "run", side_effect=command) as run:
                with self.assertRaises(RuntimeError) as failure:
                    DRIVER.main()
            return str(failure.exception), [call.args[0] for call in run.call_args_list]

    def test_hold_refusal_never_claims_that_restoration_ran(self) -> None:
        for action in ("window", "windows-live-only"):
            with self.subTest(action=action):
                message, calls = self.failed_window(action, hold_acquired=False)
                self.assertIn("hold refused", message)
                self.assertNotIn("restoration completed", message)
                self.assertNotIn("completion restored", message)
                self.assertIn("did not run" if action == "window" else "did not restore", message)
                self.assertFalse(any("--action restore " in str(call[-1]) for call in calls))

    def test_failure_after_acquiring_the_hold_reports_the_completed_restoration(self) -> None:
        for action in ("window", "windows-live-only"):
            with self.subTest(action=action):
                message, calls = self.failed_window(action, hold_acquired=True)
                self.assertIn("host-begin exited 1", message)
                self.assertIn("restoration completed" if action == "window" else "completion restored", message)
                self.assertEqual(sum("--action restore " in str(call[-1]) for call in calls), 1)


if __name__ == "__main__":
    unittest.main()
