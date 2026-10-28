"""The RTX 5090 window asks each structured client for the model its candidate serves (omp-ninfer#98).

The driver runs from the operator's checkout against a frozen candidate. It takes each client's model
from the candidate's documented provider step and the fragment that step installs, hands it to the WSL
host and Windows client scripts, and its summary expects the same model. A candidate that renames its
served model is asked for, and accepted with, the new one. Every host and client command here is a
recording fake: no host is contacted and no port is bound."""
from __future__ import annotations

import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import documented_route  # noqa: E402


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DRIVER = load("documented_model_driver", ROOT / "scripts/hosts/accept-rtx5090-routes.py")
RELEASE = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))["product_release"]
MANIFEST = Path("releases") / RELEASE / "manifest.json"
CANDIDATE = "1" * 40
WINDOWS = "C:/acceptance/window"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def option(argv: list[str], name: str) -> str | None:
    return argv[argv.index(name) + 1] if name in argv else None


def served_model(clone: Path) -> str:
    """The RTX 5090 container's served model ID: a server-side identity, never a client fragment."""
    return json.loads((clone / MANIFEST).read_text(encoding="utf-8"))["runtime_identity"]["public_model_id"]


def driver_workspace(root: Path, suffix: str) -> Path:
    """The driver's private workspace after its bundles were built: a candidate clone whose RTX 5090
    container serves, and whose guide's client fragments configure, the current model ID plus
    ``suffix``, the Mac route's clone of it, and the three documented bundles. Returns the clone."""
    clone = root / "candidate"
    for relative in (Path("docs/QUICKSTART.md"), Path("compatibility.json"), MANIFEST):
        (clone / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / relative, clone / relative)
    for directory in ("manual-tunnel", "windows-docker-local"):
        shutil.copytree(ROOT / "examples" / directory, clone / "examples" / directory)
    for fragment in (clone / "examples").glob("*/models*.fragment.yml"):
        fragment.write_text(re.sub(r"(?m)^(      - id: \S+)$", lambda match: match.group(1) + suffix,
                                   fragment.read_text(encoding="utf-8")), encoding="utf-8")
    manifest = json.loads((clone / MANIFEST).read_text(encoding="utf-8"))
    manifest["runtime_identity"]["public_model_id"] += suffix
    write_json(clone / MANIFEST, manifest)
    shutil.copytree(clone, root / "mac-home" / "omp-ninfer")
    for label, lane in (("host", "rtx5090-container-host"), ("mac", "rtx5090-macos-client"),
                        ("windows", "rtx5090-windows-client")):
        documented_route.bundle(clone / "docs/QUICKSTART.md", lane, root / (label + "-bundle"))
    return clone


def drive(root: Path, wsl: Path, action: str, command) -> None:
    """Run one driver action; ``command`` fakes every subprocess the driver starts."""
    argv = ["accept-rtx5090-routes.py", "--action", action, "--release", RELEASE, "--candidate", CANDIDATE,
            "--workspace", str(root), "--wsl-workspace", str(wsl), "--windows-workspace", WINDOWS,
            "--production-image", "fixture-image"]
    tunnel = types.SimpleNamespace(poll=lambda: None, terminate=lambda: None, wait=lambda timeout=None: 0)
    health = mock.MagicMock()
    health.__enter__.return_value.status = 200
    # socket.socket is a fake, so freeport() never binds 127.0.0.1:18089 (omp-ninfer#97).
    with mock.patch.object(sys, "argv", argv), \
            mock.patch.object(DRIVER.subprocess, "run", side_effect=command), \
            mock.patch.object(DRIVER.subprocess, "Popen", return_value=tunnel), \
            mock.patch.object(DRIVER.socket, "socket"), \
            mock.patch.object(DRIVER.urllib.request, "urlopen", return_value=health), \
            mock.patch.object(DRIVER.shutil, "which", return_value="fixture-tool"), \
            contextlib.redirect_stdout(io.StringIO()):
        DRIVER.main()


class WindowEnded(Exception):
    """Raised by the fake commands when the window's collection starts."""


class WindowModelTests(unittest.TestCase):
    """The operator's preflight and window against a candidate that renamed its served model."""

    PROBE = r'''
param($Source,$Workspace,$Action,$ModelId)
$ErrorActionPreference='Stop'
# py records the structured probe's arguments instead of running it.
function py {[Console]::Out.WriteLine((ConvertTo-Json -Compress @($args)));$global:LASTEXITCODE=0}
$agent=Join-Path $Workspace 'structured-home/.omp/agent'
New-Item -ItemType Directory -Force $agent,(Join-Path $Workspace 'candidate')|Out-Null
# The key the documented provider step installed; with it present the script skips that step.
Set-Content -NoNewline -LiteralPath (Join-Path $agent 'ninfer-beta.key') -Value 'synthetic-test-key'
$parameters=@{Action=$Action;Workspace=$Workspace;Release='v0.14.0';Candidate=('1'*40);ControlRoot=(Join-Path $Workspace 'control')}
if($ModelId){$parameters.ModelId=$ModelId}
& ([scriptblock]::Create([IO.File]::ReadAllText($Source))) @parameters
'''

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.top = Path(temporary.name)
        self.root, self.wsl = self.top / "mac", self.top / "wsl"
        self.clone = driver_workspace(self.root, "-next")
        self.served = served_model(self.clone)
        self.commands: list[list[str]] = []
        self.collecting = False

    def command(self, argv, **kwargs):
        argv = [str(value) for value in argv]
        self.commands.append(argv)
        if self.collecting and argv[0] == "scp":
            raise WindowEnded
        output = CANDIDATE if argv[0] == "git" and "rev-parse" in argv else ""
        return subprocess.CompletedProcess(argv, 0, output, "")

    def run_window(self) -> None:
        """Preflight, then the window up to its collection. The Mac's stock client is the file the
        documented install step leaves in preflight's scratch HOME; the Mac probe passed both phases."""
        compatibility = self.clone / "compatibility.json"
        authority = json.loads(compatibility.read_text(encoding="utf-8"))
        client = next(profile["client_distribution"] for profile in authority["profiles"]
                      if profile["id"] == "darwin-remote-ssh")
        scratch = self.root / "mac-preflight-home"
        (scratch / ".local/bin").mkdir(parents=True)
        for path in (scratch / client["asset_name"], scratch / ".local/bin/omp"):
            path.write_bytes(b"fixture stock client")
        client["asset_sha256"] = client["binary_sha256"] = hashlib.sha256(b"fixture stock client").hexdigest()
        write_json(compatibility, authority)
        drive(self.root, self.wsl, "preflight", self.command)
        write_json(self.root / "mac-structured/receipt.json",
                   {"live_acceptance": {"fail_closed": {"no_model_response": True}}})
        self.collecting = True
        with self.assertRaises(WindowEnded):
            drive(self.root, self.wsl, "window", self.command)

    def host_commands(self, *actions: str) -> list[list[str]]:
        """The WSL host script's argv for each of ``actions``, as the driver's ssh commands start it."""
        remote = [shlex.split(argv[-1]) for argv in self.commands
                  if argv[0] == "ssh" and "accept-rtx5090-host.py" in argv[-1]]
        return [argv[1:] for argv in remote if option(argv, "--action") in actions]

    def windows_requests(self) -> dict[str, str | None]:
        """The model each Windows client action that runs the structured probe is handed."""
        requests = {}
        for argv in self.commands:
            if argv[0] == "ssh" and argv[-1].startswith("powershell "):
                words = argv[-1].split()
                text = base64.b64decode(words[words.index("-EncodedCommand") + 1]).decode("utf-16le")
                action = re.search(r" -Action (\w+)", text)
                if action and action.group(1) in ("Preflight", "Live", "Outage"):
                    model = re.search(r" -ModelId '((?:[^']|'')*)'", text)
                    requests[action.group(1)] = model.group(1).replace("''", "'") if model else None
        return requests

    def wsl_host(self, argv: list[str]) -> list[list[str]]:
        """Run the WSL host script with ``argv`` in its workspace, which holds the candidate clone.
        Every command it starts is a fake recorded in ``self.started``, which is returned."""
        host = load("documented_model_host", ROOT / "scripts/hosts/accept-rtx5090-host.py")
        home = self.top / "wsl-home"
        key = home / ".config/omp-ninfer/api-key"
        if not key.exists():
            key.parent.mkdir(parents=True)
            key.write_text("synthetic-test-key\n")
        if not (self.wsl / "candidate").exists():
            shutil.copytree(self.clone, self.wsl / "candidate")
        self.started: list[list[str]] = []
        def command(argv, **kwargs):
            self.started.append([str(value) for value in argv])
            return subprocess.CompletedProcess(argv, 0, "", "")
        with mock.patch.object(sys, "argv", argv), \
                mock.patch.dict(os.environ), \
                mock.patch.object(host.Path, "home", return_value=home), \
                mock.patch.object(host.subprocess, "run", side_effect=command), \
                mock.patch("builtins.print"):
            host.main()
        return self.started

    def windows_probe(self, action: str, model_id: str) -> subprocess.CompletedProcess[str]:
        """Run the Windows client script's ``action`` with ``-ModelId``; its probe is a recording fake."""
        script, workspace = self.top / "probe.ps1", self.top / "windows"
        script.write_text(self.PROBE)
        return subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(script),
                               str(ROOT / "scripts/hosts/accept-windows-client.ps1"), str(workspace), action,
                               model_id], capture_output=True, text=True, timeout=60)

    def test_the_mac_client_is_asked_for_the_served_model(self) -> None:
        self.run_window()
        probes = [argv for argv in self.commands if argv[1:2] and argv[1].endswith("omp-client-probe.py")]
        self.assertEqual({option(argv, "--phase"): (option(argv, "--provider"), option(argv, "--model"))
                          for argv in probes},
                         dict.fromkeys(("preflight", "outage", "live"), ("ninfer-beta", "ninfer-beta/" + self.served)))

    @unittest.skipIf(os.name == "nt", "the WSL host script requires POSIX fcntl")
    def test_the_linux_client_is_asked_for_the_served_model(self) -> None:
        self.run_window()
        handed = {option(argv, "--action"): option(argv, "--model-id")
                  for argv in self.host_commands("preflight", "linux-live", "linux-outage")}
        self.assertEqual(handed, dict.fromkeys(("preflight", "linux-live", "linux-outage"), self.served))
        for argv in self.host_commands("linux-live", "linux-outage"):
            with self.subTest(action=option(argv, "--action")):
                probes = [command for command in self.wsl_host(argv) if command[1].endswith("omp-client-probe.py")]
                self.assertEqual([(option(probe, "--provider"), option(probe, "--model")) for probe in probes],
                                 [("ninfer-beta", "ninfer-beta/" + self.served)])

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed to run the Windows client script")
    def test_the_windows_client_is_asked_for_the_served_model(self) -> None:
        self.run_window()
        handed = self.windows_requests()
        self.assertEqual(handed, dict.fromkeys(("Preflight", "Live", "Outage"), self.served))
        for action in ("Live", "Outage"):
            with self.subTest(action=action):
                result = self.windows_probe(action, handed[action])
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                probe = json.loads(result.stdout.splitlines()[-1])
                self.assertEqual((option(probe, "--provider"), option(probe, "--model")),
                                 ("ninfer-beta", "ninfer-beta/" + self.served))

    @unittest.skipIf(os.name == "nt", "the WSL host script requires POSIX fcntl")
    def test_the_wsl_host_never_probes_without_a_named_model(self) -> None:
        for action in ("preflight", "linux-live", "linux-outage"):
            with self.subTest(action=action):
                argv = ["accept-rtx5090-host.py", "--action", action, "--workspace", str(self.wsl),
                        "--release", RELEASE, "--candidate", CANDIDATE, "--windows-workspace", WINDOWS,
                        "--production-image", "fixture-image"]
                refusal = io.StringIO()
                with self.assertRaises(SystemExit) as refused, contextlib.redirect_stderr(refusal):
                    self.wsl_host(argv)
                self.assertEqual(refused.exception.code, 2)
                self.assertIn("requires --model-id", refusal.getvalue())
                self.assertEqual(self.started, [])

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed to run the Windows client script")
    def test_the_windows_client_never_probes_without_a_named_model(self) -> None:
        for action in ("Live", "Outage"):
            with self.subTest(action=action):
                result = self.windows_probe(action, "")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("requires -ModelId", result.stdout + result.stderr)
                self.assertNotIn("omp-client-probe.py", result.stdout)


class SummaryModelTests(unittest.TestCase):
    """The window's summary expects, in every structured client's transcripts, the model its
    candidate's documented provider steps configure."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.top = Path(temporary.name)

    def collected(self, suffix: str, models: dict[str, str]) -> Path:
        """A passed window's collected evidence for a candidate serving its model under ``suffix``;
        each structured client's transcript names ``models[client]``. Returns the workspace."""
        root = Path(tempfile.mkdtemp(dir=self.top)) / "mac"
        clone = driver_workspace(root, suffix)
        for label in ("host", "mac", "windows"):
            manifest = json.loads((root / (label + "-bundle/manifest.json")).read_text(encoding="utf-8"))
            steps = [{"slug": step["slug"], "status": "passed", "block_sha256": step["sha256"],
                      "executed_sha256": step["sha256"]} for step in manifest["steps"]]
            write_json(root / (label + "-route.json"),
                       {"status": "passed", "document_sha256": manifest["document_sha256"], "steps": steps})
        for label, folder in (("linux", "remote-linux-structured"), ("mac", "mac-structured"),
                              ("windows", "windows-structured")):
            write_json(root / folder / "receipt.json",
                       {"status": "passed", "phases": {"tool": {}}, "live_acceptance": {}, "execution_context": {}})
            response = {"type": "message_end", "message": {"role": "assistant", "provider": "ninfer-beta",
                                                           "model": models[label], "content": []}}
            (root / folder / "tool.jsonl").write_text(json.dumps(response) + "\n", encoding="utf-8")
        runtime = next(profile["runtime"] for profile in
                       json.loads((clone / "compatibility.json").read_text(encoding="utf-8"))["profiles"]
                       if profile["id"] == "linux-docker-local")
        write_json(root / "runtime-observed.json", {"configured_image": runtime["image_reference"],
                                                    "repo_digests": [runtime["image_reference"]],
                                                    "binary_sha256": runtime["server_binary_sha256"]})
        restored = ("checkout_restored", "documented_key_restored", "beta_absent", "documented_directories_restored")
        write_json(root / "restoration.json", {**dict.fromkeys(restored, True), "window_seconds": 400.0})
        for name in ("windows-baseline.json", "windows-final.json"):
            write_json(root / name, {"markers": [], "tasks": [], "directories": [], "windows_health18088": {"status": "ok"}})
        smoke = root / "mac-home/tmp/smoke"
        smoke.mkdir(parents=True)
        for name, text in (("durable.txt", DRIVER.NONCE), ("resume.txt", DRIVER.NONCE), ("tool.txt", DRIVER.MARKER)):
            (smoke / name).write_text(text + "\n")
        (root / "windows-route.log").write_text(DRIVER.MARKER + "\n" + DRIVER.NONCE + "\n")
        return root

    def summarize(self, root: Path) -> dict:
        def command(argv, **kwargs):
            self.fail("summary started a command: " + repr(argv))
        drive(root, self.top / "wsl", "summarize", command)
        return json.loads((root / "final-summary.json").read_text(encoding="utf-8"))

    def test_each_client_is_accepted_with_the_model_its_candidate_serves(self) -> None:
        for suffix in ("", "-next"):
            with self.subTest(suffix=suffix):
                served = served_model(ROOT) + suffix
                summary = self.summarize(self.collected(suffix, dict.fromkeys(("linux", "mac", "windows"), served)))
                self.assertEqual({label: client["full_stream_audit"]["tool"]["models"]
                                  for label, client in summary["clients"].items()},
                                 dict.fromkeys(("linux", "mac", "windows"), [served]))

    def test_a_client_asked_for_the_model_before_a_rename_is_refused(self) -> None:
        previous, served = served_model(ROOT), served_model(ROOT) + "-next"
        for label in ("linux", "mac", "windows"):
            with self.subTest(client=label):
                models = dict.fromkeys(("linux", "mac", "windows"), served)
                models[label] = previous
                root = self.collected("-next", models)
                with self.assertRaisesRegex(AssertionError, "^" + label + "/tool: unexpected provider/model record"):
                    self.summarize(root)
                self.assertFalse((root / "final-summary.json").exists())


if __name__ == "__main__":
    unittest.main()
