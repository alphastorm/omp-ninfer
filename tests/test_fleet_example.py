"""The fleet example binds three lanes to explicit roles with fail-closed tunnels."""

from __future__ import annotations

import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLEET = ROOT / "examples" / "fleet"


class FleetExampleTests(unittest.TestCase):
    def run_script(self, *arguments: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(FLEET / "open-tunnels.sh"), *arguments],
            capture_output=True, text=True, env=env, timeout=30,
        )

    def test_fragment_binds_each_lane_to_its_published_model_and_port(self) -> None:
        fragment = (FLEET / "models.fragment.yml").read_text(encoding="utf-8")
        providers = dict(re.findall(r"^  (ninfer-\w+):\n    baseUrl: http://127\.0\.0\.1:(\d+)/v1", fragment, re.M))
        self.assertEqual(providers, {"ninfer-main": "18191", "ninfer-heavy": "18192", "ninfer-scout": "18193"})
        request_ids = re.findall(r"requestModelId: (\S+)", fragment)
        self.assertEqual(request_ids, ["q38-ninfer", "qwen3.8-27b", "q38-ninfer"])
        self.assertEqual(re.findall(r"- id: (local-\w+)", fragment), ["local-main", "local-heavy", "local-scout"])
        self.assertEqual(fragment.count("ninferStatefulResponses: true"), 6)
        self.assertNotIn("apiKey: sk", fragment)
        for key in ("ninfer-5090.key", "ninfer-4090.key", "ninfer-3090.key"):
            self.assertIn(f'!cat "$HOME/.omp/agent/{key}"', fragment)

    def test_agents_use_the_role_models_and_scout_stays_read_only(self) -> None:
        scout = (FLEET / "agents" / "fleet-scout.md").read_text(encoding="utf-8")
        heavy = (FLEET / "agents" / "fleet-heavy.md").read_text(encoding="utf-8")
        self.assertIn("model: ninfer-scout/local-scout:low", scout)
        self.assertIn("tools: read, grep, glob\n", scout)
        self.assertIn("model: ninfer-heavy/local-heavy:medium", heavy)

    def test_tunnels_execute_exact_fail_closed_ssh_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            capture = root / "arguments"
            fake_ssh = root / "ssh"
            fake_ssh.write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$@\" >> \"$SSH_ARGUMENT_CAPTURE\"\n",
                encoding="utf-8",
            )
            fake_ssh.chmod(fake_ssh.stat().st_mode | stat.S_IXUSR)
            environment = os.environ.copy()
            environment["PATH"] = f"{root}:{environment['PATH']}"
            environment["SSH_ARGUMENT_CAPTURE"] = str(capture)
            result = self.run_script("tester@main.example", "-", "tester@scout.example", env=environment)
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = capture.read_text(encoding="utf-8").splitlines()
            self.assertIn("127.0.0.1:18191:127.0.0.1:18088", lines)
            self.assertIn("127.0.0.1:18193:127.0.0.1:18082", lines)
            self.assertNotIn("127.0.0.1:18192:127.0.0.1:18082", lines)
            self.assertEqual(lines.count("ExitOnForwardFailure=yes"), 2)

    def test_tunnels_reject_bad_destinations_and_all_skipped(self) -> None:
        for arguments in (("a@b@c", "-", "-"), ("-", "runtime.example", "-"), ("-", "-", "-bad@host")):
            with self.subTest(arguments=arguments):
                result = self.run_script(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertIn("destination must be one SSH user@host argument", result.stderr)
        result = self.run_script("-", "-", "-")
        self.assertEqual(result.returncode, 2)
        self.assertIn("every lane was skipped", result.stderr)
        result = self.run_script("tester@only.example")
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
