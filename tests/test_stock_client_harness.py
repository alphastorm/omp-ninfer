"""Offline client preflight and raw-binary installation contracts."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "scripts" / "hosts" / "omp-client-probe.py"


class ProofEnvironmentTests(unittest.TestCase):
    @staticmethod
    def load(name):
        sys.path.insert(0, str(ROOT / "scripts"))
        spec = importlib.util.spec_from_file_location("environment_" + name, ROOT / "scripts" / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_all_rpc_proof_drivers_use_the_client_environment_contract(self):
        for name in ("stock_omp_session_proof", "omp_parallel_proof", "omp_long_session_proof"):
            module = self.load(name)
            for version, expected in (("omp/18.4.0", "1"), ("omp/18.4.10", "1"),
                                      ("omp/18.8.0", None), ("omp/18.8.3", None), ("omp/18.8.7", None)):
                with self.subTest(probe=name, version=version), tempfile.TemporaryDirectory() as temporary:
                    args = argparse.Namespace(home=Path(temporary), omp=Path("fixture-omp"),
                                              model="ninfer-beta/q38-ninfer", omp_version=version)
                    with unittest.mock.patch.dict(os.environ, {"PI_OPENAI_STATEFUL": "0"}), \
                         unittest.mock.patch.object(module.Omp, "_pump"), \
                         unittest.mock.patch.object(module.Omp, "_wait"), \
                         unittest.mock.patch.object(module.subprocess, "Popen") as spawn:
                        omp = module.Omp(args, "environment-invariant", False)
                        try:
                            environment = spawn.call_args.kwargs["env"]
                            if expected is None:
                                self.assertFalse("PI_OPENAI_STATEFUL" in environment,
                                                 "per-model client launch contains the global override")
                            else:
                                self.assertEqual(environment["PI_OPENAI_STATEFUL"], expected)
                        finally:
                            omp.close()

    def test_rpc_proof_receipts_record_the_effective_stateful_environment(self):
        for name in ("stock_omp_session_proof", "omp_parallel_proof", "omp_long_session_proof"):
            module = self.load(name)
            for version in ("omp/18.4.10", "omp/18.8.7"):
                with self.subTest(probe=name, version=version), tempfile.TemporaryDirectory() as temporary:
                    home = Path(temporary)
                    (home / ".omp/agent").mkdir(parents=True)
                    (home / ".omp/agent/models.yml").write_text("fixture\n")
                    binary = home / "omp"
                    binary.write_bytes(b"fixture binary")
                    sha256 = hashlib.sha256(binary.read_bytes()).hexdigest()
                    receipt = home / "receipt.json"
                    argv = ["--omp", str(binary), "--home", str(home), "--model", "ninfer-beta/q38-ninfer",
                            "--receipt", str(receipt)]
                    with unittest.mock.patch.dict(os.environ, {"PI_OPENAI_STATEFUL": "0"}), \
                         unittest.mock.patch.object(module.subprocess, "run", return_value=
                             subprocess.CompletedProcess([], 0, stdout=version)), \
                         unittest.mock.patch("builtins.print"):
                        if name == "omp_parallel_proof":
                            argv += ["--log-cmd", "true", "--omp-sha256", sha256, "--omp-version", version]
                            with unittest.mock.patch.object(module, "prepare_home", return_value=home), \
                                 unittest.mock.patch.object(module, "run_scenario", side_effect=RuntimeError("fixture")):
                                module.main(argv)
                        elif name == "omp_long_session_proof":
                            argv += ["--omp-sha256", sha256]
                            with unittest.mock.patch.object(module.Session, "start", side_effect=RuntimeError("fixture")):
                                module.main(argv)
                        else:
                            argv += ["--omp-sha256", sha256, "--restart-cmd", "true"]
                            with unittest.mock.patch.object(module, "run_scenario", side_effect=RuntimeError("fixture")):
                                module.main(argv)
                    environment = json.loads(receipt.read_text())["environment"]
                    if version == "omp/18.8.7":
                        self.assertNotIn("PI_OPENAI_STATEFUL", environment)
                    else:
                        self.assertEqual(environment["PI_OPENAI_STATEFUL"], "1")


class ParallelIdentityTests(unittest.TestCase):
    def test_descriptor_selects_platform_binary_not_the_primary_asset(self):
        module = ProofEnvironmentTests.load("omp_parallel_proof")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / "omp"
            binary.write_bytes(b"platform fixture binary")
            sha256 = hashlib.sha256(binary.read_bytes()).hexdigest()
            descriptor = root / "client.json"
            descriptor.write_text(json.dumps({"omp": {"distribution_version": "18.8.7", "binary_sha256": "f" * 64},
                                              "platforms": {"darwin-arm64": {"binary_sha256": sha256}}}))
            receipt = root / "receipt.json"
            argv = ["--omp", str(binary), "--home", str(root), "--log-cmd", "true", "--receipt", str(receipt),
                    "--client-component", str(descriptor), "--client-platform", "darwin-arm64"]
            with unittest.mock.patch.object(module.subprocess, "run", return_value=
                     subprocess.CompletedProcess([], 0, stdout="omp/18.8.7")), \
                 unittest.mock.patch.object(module, "prepare_home", return_value=root) as prepare, \
                 unittest.mock.patch.object(module, "run_scenario", side_effect=RuntimeError("fixture")), \
                 unittest.mock.patch("builtins.print"):
                self.assertEqual(module.main(argv), 1)
            prepare.assert_called_once()
            observed = json.loads(receipt.read_text())
            self.assertEqual(observed["omp"]["sha256"], sha256)
            self.assertEqual(observed["omp"]["version"], "omp/18.8.7")
            self.assertNotIn("PI_OPENAI_STATEFUL", observed["environment"])

    def test_explicit_version_mismatch_stops_before_the_workload(self):
        module = ProofEnvironmentTests.load("omp_parallel_proof")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / "omp"
            binary.write_bytes(b"identity fixture")
            argv = ["--omp", str(binary), "--home", str(root), "--log-cmd", "true",
                    "--receipt", str(root / "receipt.json"), "--omp-version", "omp/18.8.7",
                    "--omp-sha256", hashlib.sha256(binary.read_bytes()).hexdigest()]
            with unittest.mock.patch.object(module.subprocess, "run", return_value=
                     subprocess.CompletedProcess([], 0, stdout="omp/18.4.0")), \
                 unittest.mock.patch.object(module, "prepare_home") as prepare, \
                 unittest.mock.patch("builtins.print"):
                self.assertEqual(module.main(argv), 1)
            prepare.assert_not_called()


@unittest.skipIf(os.name == "nt", "local executable fixtures use POSIX launchers")
class ClientPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "scripts").mkdir()
        shutil.copyfile(ROOT / "scripts/omp_client_environment.py", self.root / "scripts/omp_client_environment.py")
        self.manifest = self.root / "releases" / "v9.9.9" / "manifest.json"
        self.manifest.parent.mkdir(parents=True)
        self.manifest.write_text(json.dumps({"components": {"omp": {"distribution_version": "18.4.10"}}}))
        self.binary = self.root / "omp"
        self.binary.write_text(
            f"#!{sys.executable}\n"
            "import os, sys\n"
            "if os.environ.get('PI_OPENAI_STATEFUL') != '1':\n"
            "    sys.exit('stateful environment absent')\n"
            "# OMP 18.4.0 reads piped stdin to EOF before it starts (startup phase readPipedInput).\n"
            "if sys.stdin is not None and not sys.stdin.isatty():\n"
            "    sys.stdin.read()\n"
            "if sys.argv[1:] == ['--version']:\n"
            "    print('omp/18.4.10')\n"
            "elif sys.argv[1:] == ['--help']:\n"
            "    print('--mode --session-dir --continue --no-session --max-time')\n"
            "else:\n"
            "    sys.exit('unexpected preflight invocation')\n"
        )
        self.binary.chmod(0o755)
        self.output = self.root / "receipt"

    def run_probe(self, *extra: str, stdin: int | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run([
            sys.executable, str(PROBE), "--release", "v9.9.9", "--candidate", "1" * 40,
            "--output", str(self.output), "--binary", str(self.binary), "--clone", str(self.root),
            "--platform", "local-fixture", "--profile", "darwin-remote-ssh", "--phase", "preflight", *extra,
        ], stdin=stdin, capture_output=True, text=True, timeout=30, env=dict(os.environ, PI_OPENAI_STATEFUL="0"))

    def test_preflight_accepts_manifest_version_and_enables_stateful_environment(self) -> None:
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.output / "receipt.json").read_text())
        self.assertEqual(receipt["preflight"]["status"], "passed")
        self.assertEqual(receipt["preflight"]["version"], "omp/18.4.10")
        self.assertTrue(receipt["preflight"]["argv_exact"])
        self.assertEqual(receipt["expected_client_version"], "omp/18.4.10")
        self.assertEqual(receipt["environment"], {"PI_OPENAI_STATEFUL": "1"})
        self.assertNotIn("diagnostics", receipt)

    def test_candidate_descriptor_clears_stateful_environment_without_rehearsal(self) -> None:
        descriptor = self.root / "client-component.json"
        descriptor.write_text(json.dumps({"omp": {"distribution_version": "18.8.7"}}))
        self.binary.write_text(self.binary.read_text().replace(
            "if os.environ.get('PI_OPENAI_STATEFUL') != '1':",
            "if 'PI_OPENAI_STATEFUL' in os.environ:",
        ).replace("omp/18.4.10", "omp/18.8.7"))
        result = self.run_probe("--client-component", str(descriptor))
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.output / "receipt.json").read_text())
        self.assertEqual(receipt["preflight"]["version"], "omp/18.8.7")

        self.assertEqual(receipt["expected_client_version"], "omp/18.8.7")
        self.assertEqual(receipt["environment"], {})

    def test_resumed_phases_refuse_a_changed_client_contract(self) -> None:
        descriptor = self.root / "client-component.json"
        descriptor.write_text(json.dumps({"omp": {"distribution_version": "18.8.7"}}))
        self.binary.write_text(self.binary.read_text().replace(
            "if os.environ.get('PI_OPENAI_STATEFUL') != '1':",
            "if 'PI_OPENAI_STATEFUL' in os.environ:",
        ).replace("omp/18.4.10", "omp/18.8.7"))
        result = self.run_probe("--client-component", str(descriptor), "--local-rehearsal")
        self.assertEqual(result.returncode, 0, result.stderr)
        before = (self.output / "receipt.json").read_bytes()
        self.binary.unlink()  # Any attempt to launch instead of refusing the resume must fail.
        for phase in ("live", "outage", "preflight"):
            with self.subTest(phase=phase):
                result = self.run_probe("--phase", phase)  # Baseline manifest would inject =1.
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("preflight client contract", result.stderr)
                self.assertEqual((self.output / "receipt.json").read_bytes(), before)

    def test_same_client_contract_can_resume_the_outage_phase(self) -> None:
        event = json.dumps({"type": "message_end", "message": {
            "role": "assistant", "provider": "ninfer-beta", "model": "q38-ninfer",
            "content": [], "errorMessage": "fixture route unavailable"}})
        self.binary.write_text(self.binary.read_text().replace(
            "    sys.exit('unexpected preflight invocation')",
            f"    print({event!r})\n    sys.exit(1)",
        ))
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_probe("--phase", "outage")
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.output / "receipt.json").read_text())
        self.assertEqual(receipt["expected_client_version"], "omp/18.4.10")
        self.assertEqual(receipt["environment"], {"PI_OPENAI_STATEFUL": "1"})
        self.assertTrue(receipt["live_acceptance"]["fail_closed"]["no_model_response"])

    def test_resumed_phase_refuses_a_changed_recorded_environment(self) -> None:
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        path = self.output / "receipt.json"
        receipt = json.loads(path.read_text())
        receipt["expected_client_version"] = "omp/18.4.10"
        receipt["environment"] = {}
        path.write_text(json.dumps(receipt))
        before = path.read_bytes()
        self.binary.unlink()
        result = self.run_probe("--phase", "outage")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("preflight client contract", result.stderr)
        self.assertEqual(path.read_bytes(), before)

    def test_published_per_model_client_also_clears_stateful_environment(self) -> None:
        self.manifest.write_text(json.dumps({"components": {"omp": {"distribution_version": "18.8.7"}}}))
        self.binary.write_text(self.binary.read_text().replace(
            "if os.environ.get('PI_OPENAI_STATEFUL') != '1':",
            "if 'PI_OPENAI_STATEFUL' in os.environ:",
        ).replace("omp/18.4.10", "omp/18.8.7"))
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.output / "receipt.json").read_text())
        self.assertEqual(receipt["stateful_source"], "per-model compat")

    def test_rehearsal_dry_run_has_no_global_override_or_filesystem_effects(self) -> None:
        descriptor = self.root / "client-component.json"
        descriptor.write_text(json.dumps({"omp": {"distribution_version": "18.8.7"}}))
        self.binary.unlink()
        result = self.run_probe("--client-component", str(descriptor), "--local-rehearsal", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)
        self.assertEqual(plan["environment"], {})
        self.assertEqual(plan["evidence_kind"], "local rehearsal")
        self.assertEqual(plan["expected_client_version"], "omp/18.8.7")
        self.assertFalse(self.output.exists())

    def test_a_client_never_waits_on_the_probes_stdin(self) -> None:
        """v0.9.0's second RTX 5090 window ran the probe over ssh from a terminal that never
        closes. The Linux client inherited that stdin, waited in readPipedInput for an EOF that
        never came, and sent no request before the probe's 210 s limit."""
        read_end, write_end = os.pipe()  # never written, open until the probe ends
        try:
            result = self.run_probe(stdin=read_end)
        finally:
            os.close(write_end)
            os.close(read_end)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.output / "receipt.json").read_text())
        self.assertEqual(receipt["preflight"]["version"], "omp/18.4.10")

    def test_mismatched_version_fails_and_records_expected_and_observed_versions(self) -> None:
        self.manifest.write_text(json.dumps({"components": {"omp": {"distribution_version": "18.4.9"}}}))
        result = self.run_probe()
        self.assertNotEqual(result.returncode, 0)
        receipt = json.loads((self.output / "receipt.json").read_text())
        self.assertEqual(receipt["status"], "failed")
        self.assertIn("expected omp/18.4.9", receipt["first_failing_boundary"])
        self.assertIn("omp/18.4.10", receipt["first_failing_boundary"])

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
        self.assertEqual(plan["expected_client_version"], "omp/18.4.10")
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


@unittest.skipIf(os.name == "nt", "local executable fixtures use POSIX launchers")
class WindowsInteropRelayTests(unittest.TestCase):
    """The WSL-side window releases its Windows hold from sshd children and a detached watchdog,
    outside every wsl.exe session; on a distro an S4U boot task started, their default relay
    cannot start a Windows process."""

    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "interop_host", ROOT / "scripts" / "hosts" / "accept-rtx5090-host.py")
        assert spec and spec.loader
        self.host = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.host)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.runtime = Path(temporary.name) / "run-wsl"
        self.runtime.mkdir()
        # Only the named relay can start this "Windows" process; any other fails the way a dead
        # relay does.
        self.probe = Path(temporary.name) / "cmd.exe"
        self.probe.write_text(
            '#!/bin/sh\n[ "$WSL_INTEROP" = "$LIVE_RELAY" ] && exit 0\n'
            'echo "$0: Invalid argument" >&2\nexit 1\n')
        self.probe.chmod(0o755)
        environment = {key: value for key, value in os.environ.items() if key != "WSL_INTEROP"}
        patcher = unittest.mock.patch.dict(os.environ, environment, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def relay(self, name: str, age_seconds: int) -> str:
        path = self.runtime / name
        path.touch()
        stamp = 1_790_000_000 - age_seconds
        os.utime(path, (stamp, stamp))
        return str(path)

    def test_an_sshd_child_passes_the_dead_root_relay_for_a_live_session(self) -> None:
        self.relay("1_interop", 3600)
        self.relay("2_interop", 3600)
        live = self.relay("3346_interop", 60)
        self.relay("9400_interop", 5)
        os.environ["LIVE_RELAY"] = live
        environment = self.host.windows_environment(self.probe, self.runtime)
        self.assertEqual(environment["WSL_INTEROP"], live)
        released = subprocess.run([str(self.probe)], env=environment, capture_output=True)
        self.assertEqual(released.returncode, 0)

    def test_no_live_relay_refuses_and_names_every_relay_tried(self) -> None:
        root = self.relay("2_interop", 3600)
        own = str(self.runtime / "7777_interop")
        os.environ.update(WSL_INTEROP=own, LIVE_RELAY="/run/WSL/none")
        with self.assertRaisesRegex(RuntimeError, "no WSL interop relay") as refused:
            self.host.windows_environment(self.probe, self.runtime)
        self.assertIn(own, str(refused.exception))
        self.assertIn(root, str(refused.exception))



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


class WindowsHostRestorationTests(unittest.TestCase):
    """What a production window must leave unchanged on the Windows host it ran against."""

    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "rtx5090_routes", ROOT / "scripts" / "hosts" / "accept-rtx5090-routes.py")
        assert spec and spec.loader
        self.routes = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.routes)
        task = {"name": "OMP-ContainerHostSupervisor", "path": "\\", "state": "Ready",
                "definition_sha256": "4c96ce2595ea361bd694af8d68f5737b52637323da12dce0804ee4b79b3c5214"}
        marker = {"path": "C:\\ProgramData\\OMP\\windows-hosts\\state\\container-host-paused",
                  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "bytes": 0}
        self.baseline = {"markers": [marker], "tasks": [task]}

    def snapshot(self, **task):
        return {"markers": self.baseline["markers"], "tasks": [{**self.baseline["tasks"][0], **task}]}

    def test_a_periodic_task_caught_mid_run_is_unchanged(self) -> None:
        self.routes.assert_windows_host_unchanged(self.snapshot(state="Running"), self.snapshot(state="Ready"))

    def test_a_disabled_redefined_or_removed_task_or_a_changed_marker_is_refused(self) -> None:
        for after, message in ((self.snapshot(state="Disabled"), "tasks"),
                               (self.snapshot(definition_sha256="0" * 64), "tasks"),
                               ({"markers": self.baseline["markers"], "tasks": []}, "tasks"),
                               ({"markers": [], "tasks": self.baseline["tasks"]}, "markers")):
            with self.subTest(after=after), self.assertRaisesRegex(AssertionError, message):
                self.routes.assert_windows_host_unchanged(self.baseline, after)



if __name__ == "__main__":
    unittest.main()
