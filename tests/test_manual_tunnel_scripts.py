from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "manual-tunnel"


class ManualTunnelScriptsTest(unittest.TestCase):
    def test_start_identity_uses_profile_deployment_identity(self) -> None:
        source = (ROOT / "examples" / "manual-tunnel" / "start-ninfer.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn('MANIFEST="$ROOT/releases/v0.6.5/manifest.json"', source)
        self.assertIn('EXPECTED_DEPLOYMENT_PROFILE=${PROFILE_VALUES[2]}', source)
        self.assertIn('"deployment_profile": (identity.get("deployment_profile"), deployment_profile)', source)
        self.assertNotIn('"qwen38-5090-v0.1.0"', source)

        stop_source = (ROOT / "examples" / "manual-tunnel" / "stop-ninfer.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("EXPECTED_RELEASE=v0.6.5", stop_source)

    def test_windows_ready_path_materializes_key_and_refuses_overwrite(self) -> None:
        quickstart = (ROOT / "docs" / "QUICKSTART.md").read_text(encoding="utf-8")
        provider = quickstart.split("### Native Windows OMP", 1)[1].split(
            "The sealed launcher owns config selection", 1
        )[0]
        self.assertIn("wsl.exe -d Ubuntu-24.04", provider)
        self.assertIn("$HOME/.config/omp-ninfer/api-key", provider)
        self.assertIn("[IO.File]::WriteAllText($KeyPath", provider)
        self.assertIn("icacls.exe $KeyPath /inheritance:r", provider)
        self.assertIn("Existing OMP models/config found", provider)
        self.assertIn("Copy-Item .\\examples\\manual-tunnel\\fail-closed.yml", provider)
        self.assertIn("$env:NINFER_BETA_API_KEY", provider)
        self.assertNotIn("install -m", provider)
        self.assertLess(
            provider.index("Existing OMP models/config found"),
            provider.index("Copy-Item .\\examples\\windows-docker-local"),
        )

        acceptance = quickstart.split("### Native Windows command forms", 1)[1].split(
            "### macOS/Linux command forms", 1
        )[0]
        self.assertIn("$env:LOCALAPPDATA\\OMP\\omp.cmd", acceptance)
        self.assertIn("stop-ninfer.sh", acceptance)
        self.assertIn("if ($LASTEXITCODE -eq 0)", acceptance)
        self.assertNotIn("Stop the tunnel", acceptance)

    def test_native_lane_install_is_completable_from_the_document(self) -> None:
        """Every input the native installer demands must be produced by the documented path.

        Install-Release.ps1 on the RTX 4090 lane requires -StateRoot and a model artifact, and
        refuses a key file it did not find; a reader with only this section must still finish."""
        quickstart = (ROOT / "docs" / "QUICKSTART.md").read_text(encoding="utf-8")
        native = quickstart.split("## Native Windows RTX 4090 and RTX 3090 release lanes", 1)[
            1
        ].split("## Managed macOS SSH qualified route", 1)[0]
        manifest = json.loads(
            (ROOT / "releases" / "v0.6.5" / "manifest.json").read_text(encoding="utf-8")
        )
        release = manifest["release"]
        self.assertIn(f"releases\\{release}\\manifest.json", native)
        # The installer's mandatory inputs.
        self.assertIn("-StateRoot $StateRoot", native)
        self.assertIn("-ModelArtifactPath $Model", native)
        self.assertIn("-ApiKeyFile $ApiKeyFile", native)
        # ... each produced before the call, from the manifest's own identities.
        self.assertIn("$Manifest.components.model.artifact_url", native)
        self.assertIn("$Manifest.components.model.artifact_sha256", native)
        self.assertIn("RandomNumberGenerator]::Create().GetBytes($Secret)", native)
        for state_root in ("qwen38-4090-native", "qwen38-3090-omp-v0.2"):
            self.assertIn(state_root, native)
        # The lifecycle surface a reader needs after a reboot, and the lane's own endpoint.
        for action in ("-Action Status", "-Action Start", "-Action Stop"):
            self.assertIn(f"{action} -StateRoot $StateRoot", native)
        self.assertIn("127.0.0.1:18082", native)
        # The native lanes carry neither the WSL2 key path nor a Vision check.
        self.assertNotIn("wsl.exe", native)
        self.assertNotIn("icon-512.png", native)

    def test_native_fragment_matches_each_lane_served_identity(self) -> None:
        fragment = (
            ROOT / "examples" / "windows-native" / "models.fragment.yml"
        ).read_text(encoding="utf-8")
        for provider, request_model in (
            ("ninfer-native-4090", "qwen3.8-27b"),
            ("ninfer-native-3090", "q38-ninfer"),
        ):
            self.assertIn(f"  {provider}:", fragment)
            self.assertIn(f"requestModelId: {request_model}", fragment)
        self.assertIn("baseUrl: http://127.0.0.1:18082/v1", fragment)
        self.assertIn("apiKey: NINFER_NATIVE_API_KEY", fragment)
        # Native lanes are text and tools only; a vision input would advertise an absent route.
        self.assertNotIn("image", fragment)

    @staticmethod
    def copy_contract_tree(root: Path) -> None:
        for directory in ("examples", "profiles", "releases", "scripts"):
            shutil.copytree(ROOT / directory, root / directory)
        shutil.copy2(ROOT / "compatibility.json", root / "compatibility.json")
        (root / "docs").mkdir()
        shutil.copy2(ROOT / "docs" / "COMPATIBILITY.md", root / "docs" / "COMPATIBILITY.md")

    @staticmethod
    def materialize_synthetic_runtime(
        root: Path, manifest_path: Path, manifest: dict
    ) -> None:
        manifest["components"]["ninfer"]["oci_reference"] = (
            "ghcr.io/alphastorm/ninfer-runtime@sha256:" + "a" * 64
        )
        manifest["components"]["ninfer"]["server_binary_sha256"] = "b" * 64
        manifest["runtime_identity"]["configuration_sha256"] = "c" * 64
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        # The synthetic manifest cannot pass the real verifier's CLI gate, but the launcher
        # also imports the verifier for the configuration identity: keep that real.
        (root / "scripts" / "verify_release.py").write_text(
            "import importlib.util\n"
            "import sys\n"
            "if __name__ == '__main__':\n"
            "    raise SystemExit(0)\n"
            f"_spec = importlib.util.spec_from_file_location('verify_release', {str(ROOT / 'scripts' / 'verify_release.py')!r})\n"
            "_module = importlib.util.module_from_spec(_spec)\n"
            "_spec.loader.exec_module(_module)\n"
            "sys.modules[__name__] = _module\n",
            encoding="utf-8",
        )

    def run_script(
        self,
        name: str,
        *arguments: str,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(EXAMPLES / name), *arguments],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_start_contract_accepts_checked_in_candidate(self) -> None:
        result = self.run_script("start-ninfer.sh", "--check-contract")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("launcher contract valid", result.stdout)

    def test_start_refuses_draft_before_runtime_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_contract_tree(root)
            manifest_path = root / "releases" / "v0.6.5" / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["status"] = "draft"
            manifest["components"]["omp"]["artifact_published"] = False
            manifest_path.write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            model = root / "model.ninfer"
            key = root / "api-key"
            model.write_bytes(b"not-used")
            key.write_text("not-used\n", encoding="utf-8")
            result = subprocess.run(
                [
                    "bash",
                    str(root / "examples" / "manual-tunnel" / "start-ninfer.sh"),
                    "--model",
                    str(model),
                    "--api-key-file",
                    str(key),
                    "--log-dir",
                    str(root / "logs"),
                    "--checkpoint-dir",
                    str(root / "checkpoints"),
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("release manifest is not installable", result.stderr)

    def launch_with_fakes(
        self, root: Path, docker_script: str, mutate_profile=None
    ) -> tuple[subprocess.CompletedProcess[str], Path, dict]:
        """Run the launcher against a synthetic release with a fake docker on PATH; the fake
        captures the `run` argv the launcher would hand to Docker. The synthetic manifest
        records the identity the profile declares, as a real release does."""
        self.copy_contract_tree(root)
        release = json.loads((root / "compatibility.json").read_text(encoding="utf-8"))["product_release"]
        manifest_path = root / "releases" / release / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.materialize_synthetic_runtime(root, manifest_path, manifest)
        profile_path = root / "profiles" / "qwen38-rtx5090-manual-tunnel.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        if mutate_profile is not None:
            mutate_profile(profile)
            profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
        arguments = profile["server"]["arguments"]
        manifest["runtime_identity"]["configuration_sha256"] = arguments[
            arguments.index("--config-sha256") + 1
        ]
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        model = root / "model.ninfer"
        with model.open("wb") as model_file:
            model_file.truncate(manifest["components"]["model"]["artifact_bytes"])
        key = root / "api-key"
        key.write_text("test-key\n", encoding="utf-8")
        key.chmod(0o600)
        fake_bin = root / "bin"
        fake_bin.mkdir()
        capture = root / "docker-arguments"
        (fake_bin / "docker").write_text(docker_script, encoding="utf-8")
        self.write_common_fakes(fake_bin)
        environment = os.environ.copy()
        environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
        environment["DOCKER_ARGUMENT_CAPTURE"] = str(capture)
        environment["EXPECTED_BINARY_SHA256"] = manifest["components"]["ninfer"]["server_binary_sha256"]
        environment["EXPECTED_MODEL_SHA256"] = manifest["components"]["model"]["artifact_sha256"]
        result = subprocess.run(
            [
                "bash",
                str(root / "examples" / "manual-tunnel" / "start-ninfer.sh"),
                "--model", str(model),
                "--api-key-file", str(key),
                "--log-dir", str(root / "logs"),
                "--checkpoint-dir", str(root / "checkpoints"),
            ],
            cwd=root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
        return result, capture, manifest

    CAPTURING_DOCKER = (
        "#!/bin/sh\n"
        "if [ \"$1:$2\" = \"container:inspect\" ]; then exit 1; fi\n"
        "if [ \"$1\" = pull ]; then exit 0; fi\n"
        "if [ \"$1\" = run ]; then\n"
        "  for argument in \"$@\"; do\n"
        "    if [ \"$argument\" = sha256sum ]; then\n"
        "      printf '%s  /usr/local/bin/ninfer-serve\\n' \"$EXPECTED_BINARY_SHA256\"\n"
        "      exit 0\n"
        "    fi\n"
        "    if [ \"$argument\" = nvidia-smi ]; then\n"
        "      printf 'NVIDIA GeForce RTX 5090, 32607 MiB, 12.0\\n'\n"
        "      exit 0\n"
        "    fi\n"
        "  done\n"
        "  printf '%s\\n' \"$@\" > \"$DOCKER_ARGUMENT_CAPTURE\"\n"
        "  exit 42\n"
        "fi\n"
        "exit 2\n"
    )

    def test_start_runs_a_published_loopback_container_with_a_durable_store(self) -> None:
        """The route a stranger runs: a bridge container published on the runtime host's
        loopback (a host-network bind never reaches the operator on Docker Desktop), as the
        invoking user with capabilities dropped and the repository's io_uring seccomp profile,
        with the checkpoint directory mounted and the session store enabled."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result, capture, manifest = self.launch_with_fakes(root, self.CAPTURING_DOCKER)

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(
                capture.exists(),
                f"launcher stopped before Docker run\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            arguments = capture.read_text(encoding="utf-8").splitlines()
            self.assertEqual(arguments[arguments.index("--network") + 1], "bridge")
            self.assertEqual(arguments[arguments.index("--publish") + 1], "127.0.0.1:18089:8080")
            self.assertEqual(arguments[arguments.index("--user") + 1], f"{os.getuid()}:{os.getgid()}")
            self.assertEqual(arguments[arguments.index("--cap-drop") + 1], "ALL")
            self.assertIn("no-new-privileges=true", arguments)
            seccomp = [a for a in arguments if a.startswith("seccomp=")]
            self.assertEqual(seccomp, [f"seccomp={root / 'examples' / 'manual-tunnel' / 'ninfer_io_uring_seccomp.json'}"])
            self.assertIn(f"{(root / 'checkpoints').resolve()}:/checkpoints", arguments)
            self.assertEqual(arguments[arguments.index("--session-checkpoint-dir") + 1], "/checkpoints")
            self.assertEqual(arguments[arguments.index("--host") + 1], "0.0.0.0")
            self.assertEqual(arguments[arguments.index("--port") + 1], "8080")
            self.assertEqual(
                arguments[arguments.index("--config-sha256") + 1],
                manifest["runtime_identity"]["configuration_sha256"],
            )
            self.assertIn("--api-key-file", arguments)
            self.assertNotIn("--api-key", arguments)
            self.assertTrue((root / "checkpoints").is_dir())
            self.assertEqual(stat.S_IMODE((root / "checkpoints").stat().st_mode), 0o700)

    def test_start_refuses_a_configuration_identity_that_is_not_its_own(self) -> None:
        """v0.6.2's route declared the identity of a configuration it did not run. The launcher
        computes the identity of what it is about to launch and refuses any other."""
        def retune(profile: dict) -> None:
            arguments = profile["server"]["arguments"]
            arguments[arguments.index("--host-state-slots") + 1] = "16"

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result, capture, _ = self.launch_with_fakes(root, self.CAPTURING_DOCKER, retune)

            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("configuration identity mismatch", result.stderr)
            self.assertFalse(capture.exists(), "the launcher must refuse before Docker runs")

    @staticmethod
    def write_common_fakes(fake_bin: Path) -> None:
        (fake_bin / "nvidia-smi").write_text(
            "#!/bin/sh\nprintf 'NVIDIA GeForce RTX 5090, 32607 MiB, 12.0\\n'\n",
            encoding="utf-8",
        )
        (fake_bin / "chmod").write_text(
            "#!/bin/sh\n"
            "if [ \"$2\" = -- ]; then exec /bin/chmod \"$1\" \"$3\"; fi\n"
            "exec /bin/chmod \"$@\"\n",
            encoding="utf-8",
        )
        (fake_bin / "sha256sum").write_text(
            "#!/bin/sh\n[ \"$1\" = -- ] && shift\n"
            "printf '%s  %s\\n' \"$EXPECTED_MODEL_SHA256\" \"$1\"\n",
            encoding="utf-8",
        )
        for name in ("chmod", "docker", "nvidia-smi", "sha256sum"):
            path = fake_bin / name
            path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def test_tunnel_executes_exact_fail_closed_ssh_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            capture = root / "arguments"
            fake_ssh = root / "ssh"
            fake_ssh.write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$SSH_ARGUMENT_CAPTURE\"\n",
                encoding="utf-8",
            )
            fake_ssh.chmod(fake_ssh.stat().st_mode | stat.S_IXUSR)
            environment = os.environ.copy()
            environment["PATH"] = f"{root}:{environment['PATH']}"
            environment["SSH_ARGUMENT_CAPTURE"] = str(capture)

            result = self.run_script(
                "open-tunnel.sh",
                "tester@runtime.example",
                env=environment,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                capture.read_text(encoding="utf-8").splitlines(),
                [
                    "-NT",
                    "-o",
                    "ExitOnForwardFailure=yes",
                    "-o",
                    "ServerAliveInterval=30",
                    "-o",
                    "ServerAliveCountMax=3",
                    "-L",
                    "127.0.0.1:18089:127.0.0.1:18089",
                    "tester@runtime.example",
                ],
            )

    def test_tunnel_rejects_non_user_host_destinations(self) -> None:
        for destination in ("runtime.example", "@runtime.example", "tester@", "a@b@c", "-bad@host"):
            with self.subTest(destination=destination):
                result = self.run_script("open-tunnel.sh", destination)
                self.assertEqual(result.returncode, 2)
                self.assertIn("destination must be one SSH user@host argument", result.stderr)


if __name__ == "__main__":
    unittest.main()
