"""The fleet example binds the qualified lanes to explicit roles with fail-closed tunnels."""

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
        providers = dict(re.findall(r"^  (ninfer-\w+):\n((?:    .*\n)+)", fragment, re.M))
        expected = {
            "ninfer-main": ("q38-ninfer", "18191", "ninfer-5090.key"),
            "ninfer-heavy": ("qwen3.8-27b", "18192", "ninfer-4090.key"),
        }
        self.assertEqual(set(providers), set(expected))
        for provider, (model, port, key) in expected.items():
            with self.subTest(provider=provider):
                body = providers[provider]
                self.assertIn(f"    baseUrl: http://127.0.0.1:{port}/v1\n", body)
                self.assertEqual(re.findall(r"^      - id: (\S+)$", body, re.M), [model])
                self.assertIn("    api: openai-responses\n", body)
                self.assertIn("    authHeader: true\n", body)
                self.assertIn(f'!cat "$HOME/.omp/agent/{key}"', body)
                self.assertIn(
                    "        thinking:\n          mode: effort\n          efforts: [low, medium, xhigh]\n",
                    body,
                )
                self.assertIn(
                    "        compat:\n          includeEncryptedReasoning: false\n          supportsReasoningSummary: false\n",
                    body,
                )
        for forbidden in ("requestModelId", "ninferStatefulResponses"):
            self.assertNotIn(forbidden, fragment)
        self.assertNotIn("apiKey: sk", fragment)

    def test_deferred_lane_declares_no_installable_provider(self) -> None:
        """A deferred GPU must not reach an operator as a mergeable provider. The fragment is
        merged whole, so a scout stanza would advertise a lane this release never qualified."""
        fragment = (FLEET / "models.fragment.yml").read_text(encoding="utf-8")
        for absent in ("ninfer-scout", "local-scout", "ninfer-3090.key", "18193"):
            self.assertNotIn(absent, fragment)
        self.assertFalse((FLEET / "agents" / "fleet-scout.md").exists())
        self.assertFalse((FLEET / "provider-3090.json").exists())

    def test_agents_use_the_role_models(self) -> None:
        heavy = (FLEET / "agents" / "fleet-heavy.md").read_text(encoding="utf-8")
        self.assertEqual(
            re.findall(r"^model: (\S+)$", heavy, re.M),
            ["ninfer-heavy/qwen3.8-27b:medium"],
        )
        self.assertEqual(
            sorted(path.name for path in (FLEET / "agents").glob("*.md")),
            ["fleet-heavy.md"],
        )

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
            result = self.run_script("tester@main.example", "-", env=environment)
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = capture.read_text(encoding="utf-8").splitlines()
            self.assertIn("127.0.0.1:18191:127.0.0.1:18088", lines)
            self.assertNotIn("127.0.0.1:18192:127.0.0.1:18082", lines)
            self.assertNotIn("127.0.0.1:18193:127.0.0.1:18082", lines)
            self.assertEqual(lines.count("ExitOnForwardFailure=yes"), 1)

    def test_tunnels_reject_bad_destinations_and_all_skipped(self) -> None:
        for arguments in (("a@b@c", "-"), ("-", "runtime.example"), ("-", "-bad@host")):
            with self.subTest(arguments=arguments):
                result = self.run_script(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertIn("destination must be one SSH user@host argument", result.stderr)
        result = self.run_script("-", "-")
        self.assertEqual(result.returncode, 2)
        self.assertIn("every lane was skipped", result.stderr)
        for arity in (("tester@only.example",), ("a@b", "c@d", "e@f")):
            with self.subTest(arity=arity):
                result = self.run_script(*arity)
                self.assertEqual(result.returncode, 2)
                self.assertIn("usage: open-tunnels.sh", result.stderr)


if __name__ == "__main__":
    unittest.main()
