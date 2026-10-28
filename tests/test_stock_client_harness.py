"""Offline client preflight and raw-binary installation contracts."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import types
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
                                      ("omp/18.8.0", None), ("omp/18.8.3", None), ("omp/18.8.7", None),
                                      ("omp/18.10.1", None), ("omp/18.12.1", None),
                                      ("omp/18.12.6", None)):
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
    # The probe assumes no lane, so every run names its provider and model selector.
    SELECTOR = ("--provider", "ninfer-beta", "--model", "ninfer-beta/q38-ninfer")

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

    def run_probe(self, *extra: str, stdin: int | None = None,
                  selector: tuple[str, ...] = SELECTOR) -> subprocess.CompletedProcess[str]:
        return subprocess.run([
            sys.executable, str(PROBE), "--release", "v9.9.9", "--candidate", "1" * 40,
            "--output", str(self.output), "--binary", str(self.binary), "--clone", str(self.root),
            "--platform", "local-fixture", "--profile", "darwin-remote-ssh", "--phase", "preflight", *selector, *extra,
        ], stdin=stdin, capture_output=True, text=True, timeout=30, env=dict(os.environ, PI_OPENAI_STATEFUL="0"))

    def test_a_probe_without_a_provider_or_model_refuses_before_any_client_runs(self) -> None:
        """The probe assumes no lane. The RTX 5090 window's callers named none and were asked for
        ninfer-beta/q38-ninfer whatever their candidate served (omp-ninfer#98)."""
        for missing, selector in (("--provider", self.SELECTOR[2:]), ("--model", self.SELECTOR[:2])):
            with self.subTest(missing=missing):
                result = self.run_probe(selector=selector)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn(missing, result.stderr)
                self.assertFalse(self.output.exists())

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



@unittest.skipIf(os.name == "nt", "host directory preservation uses POSIX modes")
class HostDirectoryRestorationTests(unittest.TestCase):
    """Run the real begin/restore filesystem operations; every host command is a fixture."""

    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "directory_host", ROOT / "scripts/hosts/accept-rtx5090-host.py")
        self.host = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.host)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name) / "home"
        self.workspace = Path(temporary.name) / "window"
        self.workspace.mkdir()
        self.key = self.home / ".config/omp-ninfer/api-key"
        self.key.parent.mkdir(parents=True)
        self.key.write_text("original private fixture key\n")
        self.logs = self.home / ".local/state/omp-ninfer"
        self.checkpoints = self.home / ".local/share/omp-ninfer/checkpoints"
        self.checkpoints.parent.mkdir(parents=True)
        self.image = {"Config": {"Image": "fixture-image"}, "Image": "fixture-image-id",
                      "State": {"Running": True},
                      "HostConfig": {"RestartPolicy": {"Name": "unless-stopped"}}, "Mounts": []}
        self.sha = "1" * 40
        self.branch = "main"
        self.fail_fetch = False
        self.windows_commands = []
        self.commands = []
        # A callable per command step, run once when that host command starts.
        self.interleave = {}

    def command(self, argv, **kwargs):
        argv = [str(v) for v in argv]
        self.commands.append(argv)
        for step in [step for step in self.interleave if step in argv]:
            self.interleave.pop(step)()
        code, output = 0, ""
        if argv[:2] == ["docker", "inspect"]:
            if "--format" in argv:
                output = json.dumps(self.image)
            else:
                code = 1  # The beta container is absent throughout this filesystem fixture.
        elif argv[:2] == ["docker", "rm"]:
            pass
        elif argv[0] == "git":
            if "rev-parse" in argv:
                output = self.branch if "--abbrev-ref" in argv else self.sha
            elif "checkout" in argv:
                self.sha, self.branch = (("2" * 40, "HEAD") if "--detach" in argv else ("1" * 40, "main"))
            elif "fetch" in argv and self.fail_fetch:
                return subprocess.CompletedProcess(argv, 1, "", "fixture fetch failure")
        elif argv[0] == "bash":
            self.image["State"]["Running"] = argv[-1] == "restore"
        else:
            self.fail("unexpected external command: " + repr(argv))
        return subprocess.CompletedProcess(argv, code, output, "")

    def action(self, action):
        argv = ["accept-rtx5090-host.py", "--action", action, "--workspace", str(self.workspace),
                "--release", "v0.12.0", "--candidate", "2" * 40, "--windows-workspace", "C:/fixture",
                "--production-image", "fixture-image", "--restore-after-seconds", "60"]
        def health(*args, **kwargs):
            response = io.BytesIO(b'{"status":"ok"}')
            response.status = 200
            return response
        with unittest.mock.patch.object(sys, "argv", argv), \
             unittest.mock.patch.dict(os.environ), \
             unittest.mock.patch.object(self.host.Path, "home", return_value=self.home), \
             unittest.mock.patch.object(self.host.subprocess, "run", side_effect=self.command), \
             unittest.mock.patch.object(self.host.subprocess, "Popen", return_value=types.SimpleNamespace(pid=123)), \
             unittest.mock.patch.object(self.host.urllib.request, "urlopen", side_effect=health), \
             unittest.mock.patch.object(self.host, "windows_environment", return_value={}), \
             unittest.mock.patch("builtins.print"):
            # The Windows release command is a fixture too, never a real host operation.
            command = self.command
            def with_windows(argv, **kwargs):
                if str(argv[0]).endswith("powershell.exe"):
                    self.windows_commands.append(argv)
                    return subprocess.CompletedProcess(argv, 0, "fixture hold released", "")
                return command(argv, **kwargs)
            with unittest.mock.patch.object(self.host.subprocess, "run", side_effect=with_windows):
                self.host.main()

    def restore_now(self) -> None:
        """An independent restoration starting at this instant: the detached watchdog at its
        deadline, or the driver's restore after its begin call timed out. Its flock blocks while
        another holder has the lock; made non-blocking here, a held lock refuses it at once, and
        the caller resumes it after begin returns, where the blocked restoration would continue."""
        fcntl = self.host.fcntl
        flock = fcntl.flock
        def attempt(descriptor, operation):
            return flock(descriptor, operation | fcntl.LOCK_NB)
        with unittest.mock.patch.object(fcntl, "flock", side_effect=attempt):
            try:
                self.action("restore")
            except BlockingIOError:
                pass

    def test_absent_logs_and_checkpoints_are_recorded_created_and_restored_absent(self) -> None:
        parent = self.logs.parent.parent
        os.utime(parent, ns=(1_790_000_000_000_000_000, 1_790_000_001_000_000_000))
        parent_metadata = parent.stat()
        self.action("begin")
        baseline = json.loads((self.workspace / "baseline.json").read_text())
        for path in (self.logs.parent, self.logs, self.checkpoints):
            self.assertIs(baseline["directories"][str(path)]["exists"], False)
        for path in (self.logs, self.checkpoints):
            self.assertEqual(path.stat().st_mode & 0o777, 0o700)
            (path / "window-only").write_text("private window state")
        self.key.write_text("window key\n")
        self.action("restore")
        for path in (self.logs.parent, self.logs, self.checkpoints):
            self.assertFalse(path.exists(), path)
        self.assertEqual(self.key.read_text(), "original private fixture key\n")
        self.assertEqual((parent.stat().st_atime_ns, parent.stat().st_mtime_ns),
                         (parent_metadata.st_atime_ns, parent_metadata.st_mtime_ns))
        for label in ("logs", "checkpoints"):
            self.assertEqual((self.workspace / ("window-" + label) / "window-only").read_text(), "private window state")
        self.assertTrue(json.loads((self.workspace / "restoration.json").read_text())["documented_key_restored"])

    def test_existing_directories_restore_original_files_modes_and_timestamps(self) -> None:
        metadata = {}
        for path in (self.logs, self.checkpoints):
            path.mkdir(parents=True, mode=0o750)
            (path / "original").write_text("original bytes")
            os.utime(path, ns=(1_790_000_000_000_000_000, 1_790_000_001_000_000_000))
            s = path.stat()
            metadata[path] = (s.st_mode & 0o777, s.st_atime_ns, s.st_mtime_ns)
        self.action("begin")
        baseline = json.loads((self.workspace / "baseline.json").read_text())
        for path in metadata:
            self.assertIs(baseline["directories"][str(path)]["exists"], True)
            (path / "window-only").write_text("window bytes")
        self.action("restore")
        for path, expected in metadata.items():
            s = path.stat()
            self.assertEqual((s.st_mode & 0o777, s.st_atime_ns, s.st_mtime_ns), expected)
            self.assertEqual((path / "original").read_text(), "original bytes")
            self.assertFalse((path / "window-only").exists())

    def test_nonempty_window_created_parent_releases_hold_and_records_failed_proof(self) -> None:
        self.action("begin")
        other_state = self.logs.parent / "other-owner-history"
        other_state.write_text("unrelated owner bytes")
        self.key.write_text("window key\n")
        with self.assertRaisesRegex(AssertionError, "window-created parents retained"):
            self.action("restore")
        proof = json.loads((self.workspace / "restoration.json").read_text())
        self.assertFalse(proof["documented_directories_restored"])
        self.assertEqual(proof["retained_window_created_parents"], [str(self.logs.parent)])
        self.assertEqual(proof["windows_release"], "fixture hold released")
        self.assertTrue(proof["documented_key_restored"] and proof["checkout_restored"])
        self.assertEqual(self.key.read_text(), "original private fixture key\n")
        self.assertEqual((self.sha, self.branch), ("1" * 40, "main"))
        self.assertEqual(other_state.read_text(), "unrelated owner bytes")
        self.assertFalse(self.logs.exists())
        self.assertFalse(self.checkpoints.exists())
        self.assertEqual(len(self.windows_commands), 1)
        with self.assertRaisesRegex(AssertionError, "window-created parents retained"):
            self.action("restore")
        self.assertEqual(len(self.windows_commands), 1)
        self.assertEqual(other_state.read_text(), "unrelated owner bytes")

    def test_failed_begin_restores_absence_and_original_key(self) -> None:
        self.fail_fetch = True
        with self.assertRaisesRegex(RuntimeError, "fixture fetch failure"):
            self.action("begin")
        self.assertFalse(self.logs.exists())
        self.assertFalse(self.logs.parent.exists())
        self.assertFalse(self.checkpoints.exists())
        self.assertEqual(self.key.read_text(), "original private fixture key\n")
        self.assertTrue((self.workspace / "restoration.json").exists())

    def assert_restoration_during_begin_undoes_all_of_it(self, step: str) -> None:
        self.interleave[step] = self.restore_now
        self.action("begin")
        self.assertEqual(self.interleave, {}, "the restoration never started inside begin")
        self.action("restore")
        proof = json.loads((self.workspace / "restoration.json").read_text())
        self.assertTrue(self.image["State"]["Running"], "production left stopped behind a restoration proof")
        self.assertTrue(proof["running"] and proof["same_image"] and proof["documented_key_restored"]
                        and proof["checkout_restored"] and proof["documented_directories_restored"])
        self.assertEqual(self.key.read_text(), "original private fixture key\n")
        self.assertEqual((self.sha, self.branch), ("1" * 40, "main"))
        for path in (self.logs.parent, self.logs, self.checkpoints):
            self.assertFalse(path.exists(), path)

    def test_restoration_starting_before_the_candidate_checkout_undoes_all_of_begin(self) -> None:
        self.assert_restoration_during_begin_undoes_all_of_it("fetch")

    def test_restoration_starting_while_production_stops_undoes_all_of_begin(self) -> None:
        self.assert_restoration_during_begin_undoes_all_of_it("stop-production")

    def test_begin_refuses_a_workspace_whose_restoration_is_recorded(self) -> None:
        # The driver restores in its finally even when its begin call never reached the host;
        # every restoration after a recorded one is a no-op, so nothing may change the host now.
        self.action("restore")
        commands = len(self.commands)
        with self.assertRaisesRegex(AssertionError, "already restored"):
            self.action("begin")
        self.assertEqual(self.commands[commands:], [])
        self.assertFalse((self.workspace / "baseline.json").exists())
        self.assertEqual(self.key.read_text(), "original private fixture key\n")
        self.assertTrue(self.image["State"]["Running"])
        self.assertEqual((self.sha, self.branch), ("1" * 40, "main"))

    def assert_window_actions_refused(self, message: str) -> None:
        for action in ("host-route", "setup", "beta-start", "beta-stop"):
            with self.subTest(action=action):
                issued = (len(self.commands), len(self.windows_commands))
                with self.assertRaisesRegex(AssertionError, message):
                    self.action(action)
                self.assertEqual((len(self.commands), len(self.windows_commands)), issued)

    def test_window_actions_never_change_the_host_before_begin(self) -> None:
        self.assert_window_actions_refused("not begun")

    def test_window_actions_never_change_a_restored_host(self) -> None:
        # Restoration is recorded once; nothing would undo a beta container, key or route state
        # created after it.
        self.action("begin")
        self.action("restore")
        self.assert_window_actions_refused("already restored")
        self.assertEqual(self.key.read_text(), "original private fixture key\n")


class WindowsHoldDirectoryTests(unittest.TestCase):
    def test_hold_ownership_is_claimed_only_after_exclusive_creation(self) -> None:
        source = (ROOT / "scripts/hosts/accept-windows-client.ps1").read_text()
        hold = source.split("if($Action -eq 'Hold') {", 1)[1].split("if($Action -eq 'Release') {", 1)[0]
        self.assertLess(hold.index("hold_created=$false"), hold.index("New-Item -ItemType File -Path $Hold"))
        self.assertLess(hold.index("New-Item -ItemType File -Path $Hold"), hold.index("$ownership.hold_created=$true"))
        release = source.split("if($Action -eq 'Release') {", 1)[1].split("if($Action -eq 'Preflight') {", 1)[0]
        self.assertIn("if($ownership.hold_created -and (Test-Path $Hold))", release)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for the Windows hold lifecycle")
    def test_hold_restores_absent_or_existing_state_directory_without_touching_other_holds(self) -> None:
        proof = r'''
param($Source,$Scratch)
$ErrorActionPreference='Stop'
$text=[IO.File]::ReadAllText($Source);$tokens=$null;$errors=$null
$null=[Management.Automation.Language.Parser]::ParseInput($text,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
function Get-ScheduledTask {@()}
function Invoke-WebRequest {param([switch]$UseBasicParsing,$Uri,$TimeoutSec) @{StatusCode=200;Content='{"status":"ok"}'}}
function Invoke-RestMethod {param($Uri,$TimeoutSec) @{status='ok'}}
function Get-ExecutionPolicy {param([switch]$List) @()}
function Get-Acl {param($Path,$LiteralPath)
    $p=if($LiteralPath){$LiteralPath}else{$Path}
    if(-not (Test-Path -LiteralPath $p)){throw "ACL queried for absent path: $p"}
    @{Sddl='fixture-acl'}
}
$cases=@(@{exists=$false;race=$false},@{exists=$true;race=$false},@{exists=$false;race=$true},@{exists=$true;race=$true})
$results=@(foreach($case in $cases) {
    $exists=$case.exists;$race=$case.race
    $root=Join-Path $Scratch "control-$exists-$race";$workspace=Join-Path $Scratch "window-$exists-$race"
    New-Item -ItemType Directory -Force "$root/bin",$workspace|Out-Null
    Set-Content "$root/bin/windows-host-common.ps1" 'function Set-OmpAdminOnlyFile {param($Path)}'
    $env:LOCALAPPDATA=Join-Path $Scratch "client-$exists-$race"
    $state=Join-Path $root 'state'
    if($exists) {
        New-Item -ItemType Directory -Force $state|Out-Null
        Set-Content "$state/owner-paused" 'unrelated hold bytes'
        (Get-Item $state).LastWriteTimeUtc=[DateTime]::UtcNow.AddHours(-1)
    }
    $script=[scriptblock]::Create($text)
    if($race) {
        Add-Content "$root/bin/windows-host-common.ps1" @'
$null=[IO.Directory]::CreateDirectory((Join-Path $ControlRoot 'state'))
[IO.File]::WriteAllText((Join-Path $ControlRoot 'state/lane-container-paused'),'racing tool hold')
'@
        $holdFailed=$false
        try {$null=& $script -Action Hold -Workspace $workspace -Release v0.12.0 -Candidate ('1'*40) -ControlRoot $root} catch {$holdFailed=$true}
        if(-not $holdFailed){throw 'exclusive hold creation unexpectedly succeeded'}
        $ownership=Get-Content "$workspace/own-hold.json" -Raw|ConvertFrom-Json
        if($ownership.hold_created -ne $false){throw 'failed acquisition claims a racing tool hold'}
        try {$null=& $script -Action Release -Workspace $workspace -Release v0.12.0 -Candidate ('1'*40) -ControlRoot $root} catch {}
        if((Get-Content "$state/lane-container-paused") -cne 'racing tool hold'){throw 'racing tool hold was removed or changed'}
        if($exists -and (Get-Content "$state/owner-paused") -ne 'unrelated hold bytes'){throw 'unrelated hold changed'}
        @{original_state_exists=$exists;racing_hold=$true;passed=$true}
        continue
    }
    $null=& $script -Action Hold -Workspace $workspace -Release v0.12.0 -Candidate ('1'*40) -ControlRoot $root
    $ownership=Get-Content "$workspace/own-hold.json" -Raw|ConvertFrom-Json
    if($ownership.hold_created -ne $true){throw 'successful acquisition did not claim its hold'}
    $before=Get-Content "$workspace/windows-baseline.json" -Raw|ConvertFrom-Json
    $directory=@($before.directories|Where-Object path -EQ $state)[0]
    if($directory.exists -ne $exists){throw 'original state presence not recorded'}
    if(-not (Test-Path "$state/lane-container-paused")){throw 'own hold was not created'}
    $null=& $script -Action Release -Workspace $workspace -Release v0.12.0 -Candidate ('1'*40) -ControlRoot $root
    if((Test-Path $state) -ne $exists){throw 'original state presence not restored'}
    if(Test-Path "$state/lane-container-paused"){throw 'own hold remains'}
    if($exists -and (Get-Content "$state/owner-paused") -ne 'unrelated hold bytes'){throw 'unrelated hold changed'}
    $after=Get-Content "$workspace/windows-final.json" -Raw|ConvertFrom-Json
    foreach($original in $before.directories) {
        $final=@($after.directories|Where-Object path -EQ $original.path)[0]
        foreach($field in @('exists','sddl','creation_time_utc_ticks','last_write_time_utc_ticks')) {
            if($final.$field -cne $original.$field){throw "directory metadata changed: $field"}
        }
    }
    @{original_state_exists=$exists;racing_hold=$false;passed=$true}
})
$results|ConvertTo-Json -Compress
'''
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "hold.ps1"
            script.write_text(proof)
            result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(script),
                                     str(ROOT / "scripts/hosts/accept-windows-client.ps1"), directory],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            rows = json.loads(result.stdout)
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(row["passed"] for row in rows))


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
                    ["Working...", *answer, "Working...", "Got it - 493817-205361.", "493817-205361"])
                self.assertEqual(observed, {"tool_marker_observed": True, "plain_stdout_exact_marker": bare,
                                            "exact_nonce_line": True})

    def test_a_missing_marker_or_an_inexact_nonce_is_refused(self) -> None:
        for lines, message in ((["OMP_NINFER_TOOL_OKAY", "493817-205361"], "tool marker"),
                               (["MY_OMP_NINFER_TOOL_OK", "493817-205361"], "tool marker"),
                               (["`OMP_NINFER_TOOL_OK`", "The nonce was 493817-205361."], "exact nonce")):
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
        self.baseline = {"markers": [marker], "tasks": [task], "directories": []}

    def snapshot(self, **task):
        return {"markers": self.baseline["markers"], "tasks": [{**self.baseline["tasks"][0], **task}],
                "directories": self.baseline["directories"]}

    def test_failed_directory_restoration_cannot_be_accepted_by_summary_or_recovery(self) -> None:
        fields = ("checkout_restored", "documented_key_restored", "beta_absent", "documented_directories_restored")
        proof = dict.fromkeys(fields, True)
        self.routes.assert_host_restored(proof)
        for field in fields:
            with self.subTest(field=field), self.assertRaisesRegex(AssertionError, field):
                self.routes.assert_host_restored(dict(proof, **{field: False}))
        with self.assertRaises(KeyError):
            self.routes.assert_host_restored({field: True for field in fields[:-1]})

    def test_a_periodic_task_caught_mid_run_is_unchanged(self) -> None:
        self.routes.assert_windows_host_unchanged(self.snapshot(state="Running"), self.snapshot(state="Ready"))

    def test_documented_directory_absence_and_existing_acl_are_restoration_invariants(self) -> None:
        before = self.snapshot()
        before["directories"] = [{"path": "C:/fixture/state", "exists": False, "sddl": None}]
        for directory in ({"path": "C:/fixture/state", "exists": True, "sddl": "fixture-acl"},
                          {"path": "C:/fixture/other", "exists": False, "sddl": None}):
            after = dict(self.snapshot(), directories=[directory])
            with self.subTest(directory=directory), self.assertRaisesRegex(AssertionError, "directories"):
                self.routes.assert_windows_host_unchanged(before, after)
        before["directories"] = [{"path": "C:/fixture/state", "exists": True, "sddl": "original-acl"}]
        after = dict(self.snapshot(), directories=[{"path": "C:/fixture/state", "exists": True, "sddl": "changed-acl"}])
        with self.assertRaisesRegex(AssertionError, "directories"):
            self.routes.assert_windows_host_unchanged(before, after)

    def test_a_disabled_redefined_or_removed_task_or_a_changed_marker_is_refused(self) -> None:
        for after, message in ((self.snapshot(state="Disabled"), "tasks"),
                               (self.snapshot(definition_sha256="0" * 64), "tasks"),
                               ({"markers": self.baseline["markers"], "tasks": []}, "tasks"),
                               ({"markers": [], "tasks": self.baseline["tasks"]}, "markers")):
            with self.subTest(after=after), self.assertRaisesRegex(AssertionError, message):
                self.routes.assert_windows_host_unchanged(self.baseline, after)


@unittest.skipIf(os.name == "nt", "WSL host driver requires POSIX fcntl")
class DocumentedHostNamesTests(unittest.TestCase):
    """The 5090 host driver checks and preserves exactly what the current guide's host route creates."""

    def test_driver_store_and_model_match_the_current_guide(self) -> None:
        def load(name, path):
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            return module
        host = load("names_host", ROOT / "scripts/hosts/accept-rtx5090-host.py")
        route = load("names_route", ROOT / "scripts/documented_route.py")
        text = "\n".join(block.text for _, block in route.lane_blocks(
            ROOT / "docs/QUICKSTART.md", "rtx5090-container-host"))
        assignment = lambda name: re.search(rf'^{name}="\$(?:HOME|ROOT)/([^"]+)"$', text, re.M).group(1)
        release = json.loads((ROOT / "compatibility.json").read_text())["product_release"]
        self.assertEqual(release, "v0.14.0")
        self.assertEqual(assignment("ROOT"), ".local/share/omp-ninfer")
        names = (assignment("CHECKPOINTS"), assignment("MODEL"))
        self.assertEqual(names, ("checkpoints-v013", "qwen3_8_27b-v3.ninfer"))
        for version in ("v0.13.0", "v0.13.1", release):
            with self.subTest(release=version):
                self.assertEqual(host.documented_host_names(version), names)



if __name__ == "__main__":
    unittest.main()
