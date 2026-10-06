from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "manual-tunnel"


class ManualTunnelScriptsTest(unittest.TestCase):
    def test_fragments_match_each_lane_served_identity(self) -> None:
        cases = (
            ("manual-tunnel", "ninfer-beta", "q38-ninfer", 18089,
             "'!cat \"$HOME/.omp/agent/ninfer-beta.key\"'", ["text", "image"]),
            ("windows-docker-local", "ninfer-beta", "q38-ninfer", 18089,
             "NINFER_BETA_API_KEY", ["text", "image"]),
            ("windows-native", "ninfer-native-4090", "qwen3.8-27b", 18082,
             "NINFER_NATIVE_API_KEY", ["text"]),
        )
        for directory, provider, model, port, key, inputs in cases:
            with self.subTest(route=directory):
                fragment = (
                    ROOT / "examples" / directory / "models.fragment.yml"
                ).read_text(encoding="utf-8")
                self.assertEqual(re.findall(r"^  ([\w-]+):$", fragment, re.M), [provider])
                self.assertEqual(re.findall(r"^      - id: (\S+)$", fragment, re.M), [model])
                self.assertIn(f"    baseUrl: http://127.0.0.1:{port}/v1\n", fragment)
                self.assertIn(f"    apiKey: {key}\n", fragment)
                self.assertIn("    api: openai-responses\n", fragment)
                self.assertIn("    authHeader: true\n", fragment)
                self.assertIn(
                    "        thinking:\n          mode: effort\n          efforts: [low, medium, xhigh]\n",
                    fragment,
                )
                self.assertIn(
                    "        compat:\n          includeEncryptedReasoning: false\n          supportsReasoningSummary: false\n",
                    fragment,
                )
                for forbidden in ("requestModelId", "ninferStatefulResponses"):
                    self.assertNotIn(forbidden, fragment)
                # The deferred RTX 3090 shares the native port; no provider may advertise it.
                self.assertNotIn("3090", fragment)
                # Only the RTX 5090 container lane supports image input.
                self.assertEqual(re.findall(r"^          - (\w+)$", fragment, re.M), inputs)
                # OMP 18.6.3 defaults custom Responses hosts to auto image detail.
                self.assertNotIn("supportsImageDetailOriginal", fragment)
                self.assertIn("          statefulResponses: true\n", fragment)

    def test_every_ninfer_model_opts_into_stateful_responses_without_global_environment(self) -> None:
        for path in (ROOT / "examples").glob("*/models*.fragment.yml"):
            with self.subTest(fragment=path.relative_to(ROOT)):
                fragment = path.read_text(encoding="utf-8")
                self.assertEqual(len(re.findall(r"^      - id: \S+$", fragment, re.M)),
                                 fragment.count("          statefulResponses: true\n"))
                self.assertNotIn("PI_OPENAI_STATEFUL", fragment)
                self.assertNotIn("supportsImageDetailOriginal", fragment)

    def test_every_documented_provider_admits_as_many_requests_as_its_lane(self) -> None:
        # A request past its lane's --max-concurrency waits at the server, which expires it after
        # --pending-timeout-ms. OMP's async compaction sends its summary in the background as a
        # session nears the threshold, and a turn queued behind it at the server failed once the
        # summary outlasted OMP's resends (EXP-072). OMP waits for its own in-flight slot without a
        # deadline, but leaves a provider missing from the limits unlimited, so every provider a
        # shipped fragment declares needs one, equal to its lane's concurrency: the RTX 5090
        # providers take the root profiles' value and the RTX 4090 providers admit one.
        config = (EXAMPLES / "fail-closed.yml").read_text(encoding="utf-8")
        block = re.search(r"^providers:\n  maxInFlightRequests:\n((?:    [\w-]+: \d+\n)+)",
                          config, re.M)
        self.assertIsNotNone(block)
        limits = {name: int(value) for name, value in re.findall(r"^    ([\w-]+): (\d+)$",
                                                                  block.group(1), re.M)}
        # Every shipped provider fragment, including a lane's own (models-rtx3090.fragment.yml):
        # the RTX 3090 route installs fail-closed.yml beside its fragment like every other route.
        declared = {
            provider
            for fragment in (ROOT / "examples").glob("*/models*.fragment.yml")
            for provider in re.findall(r"^  ([\w-]+):$", fragment.read_text(encoding="utf-8"), re.M)
        }
        self.assertTrue({"ninfer-beta", "ninfer-native-4090", "ninfer-native-3090"} <= declared)
        rtx5090_providers = {"ninfer-main"}
        rtx5090_concurrency = set()
        for path in (ROOT / "profiles").glob("qwen38-rtx5090-*.json"):
            profile = json.loads(path.read_text(encoding="utf-8"))
            arguments = profile["server"]["arguments"]
            rtx5090_concurrency.add(int(arguments[arguments.index("--max-concurrency") + 1]))
            rtx5090_providers.add(profile["omp_provider"]["id"])
        self.assertEqual(len(rtx5090_concurrency), 1, "the RTX 5090 routes run one configuration")
        (rtx5090,) = rtx5090_concurrency
        self.assertEqual(limits, {provider: rtx5090 if provider in rtx5090_providers else 1
                                  for provider in declared})
        self.assertNotIn("asyncEnabled", config)

    def test_a_lane_admitting_two_requests_holds_a_waiting_one_inside_omps_stream_watchdog(self) -> None:
        # With two requests in flight, one whose prompt and output reservation do not fit beside
        # the running request's waits at the server. At the default 30 s --pending-timeout-ms it
        # expired while OMP had nothing else to wait for (EXP-072, EXP-077). OMP 18.4.0 aborts a
        # stream after 300 s without a progress event, and a waiting request sends none until its
        # first token: the wait plus the longest root prefill (130,048 tokens in 58.3 s on the
        # RTX 5090, v0.8.7) must stay inside that watchdog, so the server's own timeout ends the
        # wait first and OMP resends the request.
        omp_stream_idle_ms, longest_prefill_ms = 300_000, 60_000
        for path in (ROOT / "profiles").glob("qwen38-rtx5090-*.json"):
            arguments = json.loads(path.read_text(encoding="utf-8"))["server"]["arguments"]
            if int(arguments[arguments.index("--max-concurrency") + 1]) == 1:
                continue
            with self.subTest(profile=path.name):
                self.assertIn("--pending-timeout-ms", arguments)
                pending = int(arguments[arguments.index("--pending-timeout-ms") + 1])
                self.assertGreater(pending, 30_000)
                self.assertLess(pending + longest_prefill_ms, omp_stream_idle_ms)

    @staticmethod
    def copy_contract_tree(root: Path) -> None:
        for directory in ("examples", "profiles", "releases", "scripts"):
            shutil.copytree(ROOT / directory, root / directory)
        shutil.copy2(ROOT / "compatibility.json", root / "compatibility.json")
        shutil.copytree(ROOT / "docs" / "measurements", root / "docs" / "measurements")
        shutil.copy2(ROOT / "docs" / "COMPATIBILITY.md", root / "docs" / "COMPATIBILITY.md")
        for document in ("QUICKSTART.md", "SECURITY.md"):
            (root / "docs" / document).write_text("# Test fixture\n", encoding="utf-8")

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

    def test_start_refuses_draft_before_runtime_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_contract_tree(root)
            release = json.loads((root / "compatibility.json").read_text(encoding="utf-8"))["product_release"]
            manifest_path = root / "releases" / release / "manifest.json"
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
        self, root: Path, docker_script: str, mutate_profile=None, probe: dict | None = None
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
        # What the fake docker reports from inside the bind-staging probe container. The defaults
        # are a correctly staged route; a test overrides them to stage one incompletely.
        answers = {"key_bytes": str(len("test-key\n")), "store": "directory", "memory_mib": "65536"}
        answers.update(probe or {})
        environment["EXPECTED_MODEL_BYTES"] = str(manifest["components"]["model"]["artifact_bytes"])
        environment["PROBE_KEY_BYTES"] = answers["key_bytes"]
        environment["PROBE_STORE"] = answers["store"]
        environment["PROBE_MEMORY_MIB"] = answers["memory_mib"]
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

    STAGING_PROBE_BRANCH = (
        "    if [ \"${argument#*model=%s key=%s}\" != \"$argument\" ]; then\n"
        "      printf 'model=%s key=%s store=%s mem=%s\\n' \"$EXPECTED_MODEL_BYTES\" \"$PROBE_KEY_BYTES\" \"$PROBE_STORE\" \"$PROBE_MEMORY_MIB\"\n"
        "      exit 0\n"
        "    fi\n"
    )

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
        + STAGING_PROBE_BRANCH +
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

    def test_start_refuses_a_route_whose_bind_mounts_are_staged_incompletely(self) -> None:
        """A reboot replaces Docker Desktop's per-container bind staging, and a container created
        against the replacement can start with empty file mounts: the server then rejects its own
        empty --api-key, prints usage, exits 1, and a restart policy loops on it. The launcher
        proves the mounts inside a throwaway container first, so that costs one refusal instead of
        an outage."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result, capture, _ = self.launch_with_fakes(
                root, self.CAPTURING_DOCKER, probe={"key_bytes": "0"}
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("bind mounts incompletely", result.stderr)
            self.assertIn("key=0", result.stderr)
            self.assertFalse(capture.exists(), "the launcher must refuse before the server runs")

    def test_start_refuses_a_host_that_cannot_back_the_host_kv_pool(self) -> None:
        """The profile's Host KV pool holds two sessions at the context ceiling, and a host that
        cannot back it does not degrade: the same configuration was OOM-killed mid-request in a
        24 GiB WSL VM (container exit 137). The launcher compares the profile's declared floor
        with what a throwaway container sees and refuses before the 18 GB load."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result, capture, _ = self.launch_with_fakes(
                root, self.CAPTURING_DOCKER, probe={"memory_mib": "24576"}
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("MiB of runtime-host memory", result.stderr)
            self.assertIn("24576", result.stderr)
            self.assertIn("memory=32GB", result.stderr)
            self.assertFalse(capture.exists(), "the launcher must refuse before the server runs")

    SERVING_DOCKER = CAPTURING_DOCKER.replace(
        "  printf '%s\\n' \"$@\" > \"$DOCKER_ARGUMENT_CAPTURE\"\n  exit 42\n",
        "  printf 'container-under-test\\n'\n  exit 0\n",
    )

    def test_start_verifies_the_server_against_the_concurrency_its_profile_declares(self) -> None:
        """v0.9.0's first RTX 5090 route window refused its own server: the RTX 5090 profile moved
        to --max-concurrency 2, and the launcher still required the served scheduler to report 1.
        The launcher now expects what the profile it launched declares, and still refuses a
        server that reports anything else."""
        import http.server
        import sys
        import threading

        sys.path.insert(0, str(ROOT / "scripts"))
        import verify_release  # noqa: PLC0415

        for served_offset, accepted in ((0, True), (-1, False)):
            with self.subTest(served_offset=served_offset), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                state: dict = {}

                class Status(http.server.BaseHTTPRequestHandler):
                    def do_GET(self) -> None:  # noqa: N802
                        manifest = json.loads(state["manifest"].read_text(encoding="utf-8"))
                        profile = json.loads(state["profile"].read_text(encoding="utf-8"))
                        arguments = profile["server"]["arguments"]
                        declared = int(verify_release.argument_value(arguments, "--max-concurrency"))
                        body = json.dumps({
                            "artifact_type": "ninfer_server_status",
                            "schema_version": 1,
                            "status": "ok",
                            "identity": {
                                "upstream_base_sha": manifest["components"]["ninfer"]["upstream_commit"],
                                "patch_stack_sha": manifest["components"]["ninfer"]["source_commit"],
                                "source_dirty": False,
                                "deployment_profile": profile["server"]["deployment_profile"],
                                "binary_sha256": manifest["components"]["ninfer"]["server_binary_sha256"],
                                "model_artifact_sha256": manifest["components"]["model"]["artifact_sha256"],
                                "config_sha256": manifest["runtime_identity"]["configuration_sha256"],
                            },
                            "runtime": {
                                "public_model_id": "q38-ninfer",
                                "max_context": int(verify_release.argument_value(arguments, "--max-context")),
                                "kv_cache": verify_release.argument_value(arguments, "--kv-dtype"),
                            },
                            "scheduler": {"max_concurrency": declared + served_offset},
                        }).encode("utf-8")
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)

                    def log_message(self, *_: object) -> None:
                        pass

                server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Status)
                threading.Thread(target=server.serve_forever, daemon=True).start()
                self.addCleanup(server.server_close)
                self.addCleanup(server.shutdown)

                def serve_on_test_port(profile: dict) -> None:
                    profile["server"]["published_port"] = server.server_address[1]
                    arguments = profile["server"]["arguments"]
                    arguments[arguments.index("--config-sha256") + 1] = verify_release.configuration_identity(profile)

                release = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))["product_release"]
                state["manifest"] = root / "releases" / release / "manifest.json"
                state["profile"] = root / "profiles" / "qwen38-rtx5090-manual-tunnel.json"
                result, _, _ = self.launch_with_fakes(root, self.SERVING_DOCKER, serve_on_test_port)

                if accepted:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('"status": "ok"', result.stdout)
                else:
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn("authenticated NInfer identity mismatch", result.stderr)
                    self.assertIn("max_concurrency", result.stderr)

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
