"""Offline client preflight and raw-binary installation contracts."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "scripts" / "hosts" / "omp-client-probe.py"


@unittest.skipIf(os.name == "nt", "local executable fixtures use POSIX launchers")
class ClientPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manifest = self.root / "releases" / "v9.9.9" / "manifest.json"
        self.manifest.parent.mkdir(parents=True)
        self.manifest.write_text(json.dumps({"components": {"omp": {"distribution_version": "31.4.5"}}}))
        self.binary = self.root / "omp"
        self.binary.write_text(
            f"#!{sys.executable}\n"
            "import os, sys\n"
            "if os.environ.get('PI_OPENAI_STATEFUL') != '1':\n"
            "    sys.exit('stateful environment absent')\n"
            "if sys.argv[1:] == ['--version']:\n"
            "    print('omp/31.4.5')\n"
            "elif sys.argv[1:] == ['--help']:\n"
            "    print('--mode --session-dir --continue --no-session --max-time')\n"
            "else:\n"
            "    sys.exit('unexpected preflight invocation')\n"
        )
        self.binary.chmod(0o755)
        self.output = self.root / "receipt"

    def run_probe(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([
            sys.executable, str(PROBE), "--release", "v9.9.9", "--candidate", "1" * 40,
            "--output", str(self.output), "--binary", str(self.binary), "--clone", str(self.root),
            "--platform", "local-fixture", "--profile", "darwin-remote-ssh", "--phase", "preflight", *extra,
        ], capture_output=True, text=True, timeout=30, env=dict(os.environ, PI_OPENAI_STATEFUL="0"))

    def test_preflight_accepts_manifest_version_and_enables_stateful_environment(self) -> None:
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.output / "receipt.json").read_text())
        self.assertEqual(receipt["preflight"]["status"], "passed")
        self.assertEqual(receipt["preflight"]["version"], "omp/31.4.5")
        self.assertTrue(receipt["preflight"]["argv_exact"])
        self.assertNotIn("diagnostics", receipt)

    def test_mismatched_version_fails_and_records_expected_and_observed_versions(self) -> None:
        self.manifest.write_text(json.dumps({"components": {"omp": {"distribution_version": "32.0.0"}}}))
        result = self.run_probe()
        self.assertNotEqual(result.returncode, 0)
        receipt = json.loads((self.output / "receipt.json").read_text())
        self.assertEqual(receipt["status"], "failed")
        self.assertIn("expected omp/32.0.0", receipt["first_failing_boundary"])
        self.assertIn("omp/31.4.5", receipt["first_failing_boundary"])

    def test_missing_manifest_fails_before_launching_client_or_creating_receipts(self) -> None:
        self.manifest.unlink()
        self.binary.unlink()
        result = self.run_probe()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot read client version", result.stderr)
        self.assertIn(str(self.manifest), result.stderr)
        self.assertFalse(self.output.exists())

    def test_missing_or_invalid_distribution_version_has_no_fallback(self) -> None:
        for omp in ({}, {"distribution_version": None}, {"distribution_version": ""}):
            with self.subTest(omp=omp):
                self.manifest.write_text(json.dumps({"components": {"omp": omp}}))
                result = self.run_probe()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("components.omp.distribution_version", result.stderr)
                self.assertFalse(self.output.exists())

    def test_dry_run_resolves_manifest_version_without_launching_or_writing(self) -> None:
        self.binary.unlink()
        result = self.run_probe("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)
        self.assertEqual(plan["expected_client_version"], "omp/31.4.5")
        self.assertEqual(plan["effects"], "none")
        self.assertFalse(self.output.exists())


@unittest.skipIf(os.name == "nt", "Linux installation uses POSIX modes")
class LinuxClientInstallationTests(unittest.TestCase):
    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "linux_client_host", ROOT / "scripts" / "hosts" / "accept-rtx5090-host.py")
        assert spec and spec.loader
        self.host = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.host)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.asset = self.root / "omp-linux-x64"
        self.asset.write_text("#!/bin/sh\nprintf 'omp/31.4.5\\n'\n")
        self.home = self.root / "home"
        self.launcher = self.home / ".local/bin/omp"
        self.distribution = {
            "distribution_kind": "upstream-release", "asset_url": "https://example.invalid/omp-linux-x64",
            "asset_sha256": self.host.digest(self.asset), "binary_sha256": self.host.digest(self.asset),
        }

    def test_verified_raw_binary_is_executable_at_the_documented_path(self) -> None:
        receipt = self.host.install_linux_client(self.distribution, self.asset, self.home)
        result = subprocess.run([str(self.launcher), "--version"], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "omp/31.4.5")
        self.assertEqual(self.launcher.stat().st_mode & 0o777, 0o755)
        self.assertEqual(receipt["method"], "documented-url-and-sha256")
        self.assertFalse(receipt["fenced_block"])
        self.assertEqual(receipt["asset_sha256"], self.host.digest(self.launcher))
        self.assertFalse((self.home / ".local/share/omp/releases").exists())

    def test_bad_download_or_binary_identity_cannot_replace_an_installed_client(self) -> None:
        self.launcher.parent.mkdir(parents=True)
        self.launcher.write_text("previous client")
        for field in ("asset_sha256", "binary_sha256"):
            with self.subTest(field=field):
                distribution = dict(self.distribution, **{field: "0" * 64})
                with self.assertRaisesRegex(AssertionError, "client asset"):
                    self.host.install_linux_client(distribution, self.asset, self.home)
                self.assertEqual(self.launcher.read_text(), "previous client")

    def test_fork_distribution_cannot_be_installed_as_a_stock_binary(self) -> None:
        self.distribution["distribution_kind"] = "fork"
        with self.assertRaisesRegex(AssertionError, "stock upstream client required"):
            self.host.install_linux_client(self.distribution, self.asset, self.home)
        self.assertFalse(self.launcher.exists())


class WindowsRouteAnswerTests(unittest.TestCase):
    """The documented Windows commands' visible answers, as the route log records them."""

    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "rtx5090_routes", ROOT / "scripts" / "hosts" / "accept-rtx5090-routes.py")
        assert spec and spec.loader
        self.routes = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.routes)

    def test_a_reported_marker_passes_and_records_whether_it_was_a_bare_line(self) -> None:
        for answer, bare in ((["Exact single line: `OMP_NINFER_TOOL_OK`"], False),
                             (["The exact single line in marker.txt is:", "```", "OMP_NINFER_TOOL_OK", "```"], True)):
            with self.subTest(answer=answer):
                observed = self.routes.windows_route_answers(
                    ["Working...", *answer, "Working...", "Got it - COBALT-493817.", "COBALT-493817"])
                self.assertEqual(observed, {"tool_marker_observed": True, "plain_stdout_exact_marker": bare,
                                            "exact_nonce_line": True})

    def test_a_missing_marker_or_an_inexact_nonce_is_refused(self) -> None:
        for lines, message in ((["OMP_NINFER_TOOL_OKAY", "COBALT-493817"], "tool marker"),
                               (["MY_OMP_NINFER_TOOL_OK", "COBALT-493817"], "tool marker"),
                               (["`OMP_NINFER_TOOL_OK`", "The nonce was COBALT-493817."], "exact nonce")):
            with self.subTest(lines=lines), self.assertRaisesRegex(AssertionError, message):
                self.routes.windows_route_answers(lines)



if __name__ == "__main__":
    unittest.main()
