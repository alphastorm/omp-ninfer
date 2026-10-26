"""Portable acceptance helpers preserve quoting, digest and restoration failure contracts."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HOSTS = Path(__file__).resolve().parents[1] / "scripts/hosts"
sys.path.insert(0, str(HOSTS))
import common
import restore


class CommonHostTests(unittest.TestCase):
    def test_streamed_digest_and_powershell_encoding_preserve_exact_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact"
            content = bytes(range(256)) * 65537
            path.write_bytes(content)
            self.assertEqual(common.sha256_file(path), hashlib.sha256(content).hexdigest())
            self.assertEqual(common.sha256_file(str(path)), hashlib.sha256(content).hexdigest())
        value = "C:/owner's/日本語/файл"
        quoted = common.powershell_quote(value)
        self.assertEqual(quoted, "'C:/owner''s/日本語/файл'")
        code = "Write-Output " + quoted
        self.assertEqual(base64.b64decode(common.powershell_encoded_command(code)).decode("utf-16le"), code)

    def test_restore_precedes_audit_and_failures_are_never_success(self):
        events = []
        def recover():
            events.append("restore")
            return 7
        def audit():
            events.append("audit")
            return 9
        self.assertEqual(restore.restore_and_audit(recover, audit), (7, 9))
        self.assertEqual(events, ["restore", "audit"])
        events.clear()
        self.assertEqual(restore.restore_and_audit(recover), (7, None))
        self.assertEqual(events, ["restore"])
        def failed():
            raise RuntimeError("restoration failed")
        probe = mock.Mock()
        with self.assertRaisesRegex(RuntimeError, "restoration failed"):
            restore.restore_and_audit(failed, probe)
        probe.assert_not_called()
        with self.assertRaisesRegex(RuntimeError, "restoration failed"):
            restore.restore_and_audit(recover, failed)

    def test_completed_proof_keeps_failed_directory_restoration_failed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertFalse(restore.completed_restoration(root))
            proof = root / "restoration.json"
            proof.write_text(json.dumps({"retained_window_created_parents": []}))
            self.assertTrue(restore.completed_restoration(root))
            proof.write_text(json.dumps({"retained_window_created_parents": ["other-owner-state"]}))
            with self.assertRaisesRegex(AssertionError, "window-created parents retained"):
                restore.completed_restoration(root)

    def test_container_planner_dry_run_does_not_launch_or_create_workspaces(self):
        spec = importlib.util.spec_from_file_location("container_route_planner", HOSTS / "accept-rtx5090-routes.py")
        driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(driver)
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "not-created"
            for action in ("preflight", "window", "windows-live-only", "restore", "collect", "summarize"):
                args = [str(HOSTS / "accept-rtx5090-routes.py"), "--action", action,
                        "--release", "v0.13.1", "--candidate", "1" * 40, "--workspace", str(workspace),
                        "--wsl-workspace", "/tmp/not-created", "--windows-workspace", "C:/ci/not-created",
                        "--production-image", "no-image.invalid", "--wsl-host", "no-host.invalid",
                        "--windows-host", "no-host.invalid", "--dry-run"]
                with self.subTest(action=action), mock.patch.object(sys, "argv", args), \
                        mock.patch.object(driver.subprocess, "run", side_effect=AssertionError("host contacted")), \
                        mock.patch.object(sys, "stdout", io.StringIO()) as output:
                    driver.main()
                    self.assertEqual(json.loads(output.getvalue())["effects"], "none")
                    self.assertFalse(workspace.exists())


if __name__ == "__main__":
    unittest.main()
