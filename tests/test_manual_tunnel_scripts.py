from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "manual-tunnel"


class ManualTunnelScriptsTest(unittest.TestCase):
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

    def test_start_contract_accepts_checked_in_draft(self) -> None:
        result = self.run_script("start-ninfer.sh", "--check-contract")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("launcher contract valid", result.stdout)

    def test_start_refuses_draft_before_runtime_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = root / "model.ninfer"
            key = root / "api-key"
            model.write_bytes(b"not-used")
            key.write_text("not-used\n", encoding="utf-8")
            result = self.run_script(
                "start-ninfer.sh",
                "--model",
                str(model),
                "--api-key-file",
                str(key),
                "--log-dir",
                str(root / "logs"),
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("release manifest is not installable", result.stderr)

    def test_start_passes_host_network_to_docker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("examples", "profiles", "releases", "scripts"):
                shutil.copytree(ROOT / directory, root / directory)

            manifest_path = root / "releases" / "v0.1.0-beta.1" / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            model = root / "model.ninfer"
            with model.open("wb") as model_file:
                model_file.truncate(manifest["components"]["model"]["artifact_bytes"])
            manifest["status"] = "candidate"
            omp_artifact_name = manifest["components"]["omp"]["artifact_name"]
            manifest["components"]["omp"].update(
                {
                    "artifact_url": (
                        "https://api.github.com/repos/alphastorm/homebrew-omp/"
                        f"releases/assets/123456789#{omp_artifact_name}"
                    ),
                    "homebrew_cask_revision": "c" * 40,
                }
            )
            manifest["components"]["ninfer"].update(
                {
                    "oci_reference": f"ghcr.io/alphastorm/ninfer@sha256:{'d' * 64}",
                    "oci_manifest_digest": f"sha256:{'d' * 64}",
                    "sbom_url": "https://example.test/ninfer.spdx.json",
                    "sbom_sha256": "e" * 64,
                }
            )
            manifest_path.write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )

            key = root / "api-key"
            key.write_text("test-key\n", encoding="utf-8")
            key.chmod(0o600)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            capture = root / "docker-arguments"
            docker = fake_bin / "docker"
            docker.write_text(
                "#!/bin/sh\n"
                "if [ \"$1:$2\" = \"container:inspect\" ]; then exit 1; fi\n"
                "if [ \"$1\" = pull ]; then exit 0; fi\n"
                "if [ \"$1\" = run ]; then\n"
                "  for argument in \"$@\"; do\n"
                "    if [ \"$argument\" = --entrypoint ]; then\n"
                "      printf '%s  /usr/local/bin/ninfer-serve\\n' "
                "\"$EXPECTED_BINARY_SHA256\"\n"
                "      exit 0\n"
                "    fi\n"
                "  done\n"
                "  printf '%s\\n' \"$@\" > \"$DOCKER_ARGUMENT_CAPTURE\"\n"
                "  exit 42\n"
                "fi\n"
                "exit 2\n",
                encoding="utf-8",
            )
            nvidia_smi = fake_bin / "nvidia-smi"
            nvidia_smi.write_text(
                "#!/bin/sh\nprintf 'NVIDIA GeForce RTX 5090, 32607 MiB, 12.0\\n'\n",
                encoding="utf-8",
            )
            chmod = fake_bin / "chmod"
            chmod.write_text(
                "#!/bin/sh\n"
                "if [ \"$2\" = -- ]; then exec /bin/chmod \"$1\" \"$3\"; fi\n"
                "exec /bin/chmod \"$@\"\n",
                encoding="utf-8",
            )
            sha256sum = fake_bin / "sha256sum"
            sha256sum.write_text(
                "#!/bin/sh\n[ \"$1\" = -- ] && shift\n"
                "printf '%s  %s\\n' \"$EXPECTED_MODEL_SHA256\" \"$1\"\n",
                encoding="utf-8",
            )
            for executable in (chmod, docker, nvidia_smi, sha256sum):
                executable.chmod(executable.stat().st_mode | stat.S_IXUSR)

            environment = os.environ.copy()
            environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
            environment["DOCKER_ARGUMENT_CAPTURE"] = str(capture)
            environment["EXPECTED_BINARY_SHA256"] = manifest["components"]["ninfer"][
                "server_binary_sha256"
            ]
            environment["EXPECTED_MODEL_SHA256"] = manifest["components"]["model"][
                "artifact_sha256"
            ]
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
                ],
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(
                capture.exists(),
                f"launcher stopped before Docker run\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            arguments = capture.read_text(encoding="utf-8").splitlines()
            network_index = arguments.index("--network")
            self.assertEqual(arguments[network_index + 1], "host")
            self.assertNotIn("--publish", arguments)

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
