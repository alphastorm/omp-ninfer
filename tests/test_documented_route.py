"""The route a release accepts is the route the documentation prints."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import os
import socket
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import documented_route  # noqa: E402

RUNNER = ROOT / "scripts" / "hosts" / "run-documented-route.sh"


class ExtractionTests(unittest.TestCase):
    def test_every_lane_resolves_to_fenced_blocks_of_its_language(self) -> None:
        for lane in documented_route.LANES:
            with self.subTest(lane=lane):
                resolved = documented_route.lane_blocks(documented_route.DEFAULT_DOC, lane)
                self.assertEqual(len(resolved), len(documented_route.LANES[lane]))
                for step, block in resolved:
                    self.assertEqual(block.language, step.language)
                    self.assertTrue(block.text.strip(), f"{lane}/{step.slug} is empty")

    def test_bundle_files_are_the_documented_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            manifest = documented_route.bundle(documented_route.DEFAULT_DOC, "rtx4090-native", output)
            for step in manifest["steps"]:
                data = (output / step["file"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), step["sha256"])
                block = documented_route.extract(documented_route.DEFAULT_DOC, step["heading"], step["index"])
                self.assertEqual(data.decode("utf-8"), block.text)
            self.assertEqual(
                manifest["document_sha256"],
                hashlib.sha256(documented_route.DEFAULT_DOC.read_bytes()).hexdigest(),
            )

    def test_native_route_steps_carry_the_variables_they_use(self) -> None:
        """A reader pastes the blocks into one window; a later block may only use names an
        earlier one defined. Catches a doc edit that moves a definition below its first use."""
        defined: set[str] = set()
        import re
        for step, block in documented_route.lane_blocks(documented_route.DEFAULT_DOC, "rtx4090-native"):
            used = set(re.findall(r"\$([A-Z][A-Za-z]+)\b", block.text))
            assigned = set(re.findall(r"^\s*\$([A-Z][A-Za-z]+)\s*=", block.text, re.M))
            missing = {name for name in used - assigned - defined if name not in {"Sid", "Rule", "Asset", "Name", "Path", "Applied", "Acl", "Admins", "Secret", "LASTEXITCODE", "HOME"}}
            self.assertFalse(missing, f"{step.slug} uses {sorted(missing)} before any block defines them")
            defined |= assigned

    def test_windows_blocks_stay_within_windows_powershell(self) -> None:
        """The Windows routes run in Windows PowerShell 5.1 on .NET Framework. These calls exist
        only on .NET 5+ and failed the RTX 4090 route on a stock host (EXP-032)."""
        forbidden = ("[Convert]::ToHexString", "RandomNumberGenerator]::Fill(", "[Convert]::FromHexString")
        for block in documented_route.parse_blocks(documented_route.DEFAULT_DOC.read_text(encoding="utf-8")):
            if block.language != "powershell":
                continue
            for call in forbidden:
                self.assertNotIn(call, block.text, f"{block.heading!r} uses {call}, which Windows PowerShell lacks")

    def test_no_block_ends_by_opening_an_interactive_session(self) -> None:
        """A block that launches the OMP TUI cannot be followed by 'run these in the same
        process' and cannot be checked by a reader's shell; interactive launches live in prose,
        blocks stay non-interactive on every platform (EXP-032)."""
        import re
        launch = re.compile(r"(?:^|[\s&;(])(?:omp|\$Launcher|& \"\$env:LOCALAPPDATA\\\\OMP\\\\omp\.cmd\")\s")
        for block in documented_route.parse_blocks(documented_route.DEFAULT_DOC.read_text(encoding="utf-8")):
            if block.language not in ("sh", "powershell"):
                continue
            joined = " ".join(line.strip().rstrip("\\`") for line in block.text.splitlines())
            for command in re.split(r"[;|]|&&|\|\|", joined):
                if "--model" in command and ("omp " in command or "omp.cmd" in command or "$Launcher" in command):
                    self.assertIn(" -p", command, f"{block.heading!r} opens an interactive OMP session inside a block: {command.strip()[:120]}")

    def test_macos_acceptance_blocks_test_their_own_outcome(self) -> None:
        """Every macOS acceptance block ends with a shell test of what the turn produced, so a
        reader (and the runner) gets pass/fail from the shell, not from reading model prose."""
        for step, block in documented_route.lane_blocks(documented_route.DEFAULT_DOC, "rtx5090-macos-client"):
            if step.slug in ("tool", "vision", "resume", "survives-restart"):
                self.assertRegex(block.text, r"(grep -q|test -s)", f"{step.slug} has no shell-checkable outcome")
            if step.slug == "fail-closed":
                self.assertIn("unexpectedly succeeded", block.text)

    def test_restart_seed_stays_between_the_checkpoint_gate_and_client_compaction(self) -> None:
        """The survives-restart step seeds its session from the release's own documents, which grow
        every release. The seed must pass the runtime's 32,768-token checkpoint gate and stay below
        OMP's automatic compaction of a 131,072-token window (131,072 minus 15%: 111,412 tokens). A
        compacted continuation replays a different prefix, so the step would stop testing a restored
        checkpoint; v0.8.5's first candidate was refused there once its documents crossed the
        threshold. The bounds allow 2.5-4.5 bytes per token and a 15,000-token system prompt around
        the ~3.1 bytes per token the lane showed for these documents."""
        size = len(documented_route.restart_seed(documented_route.DEFAULT_DOC, ROOT))
        self.assertGreater(size, 32_768 * 4.5)
        self.assertLess(size, (111_412 - 15_000) * 2.5)

    def test_restart_seed_never_contains_the_planted_nonce(self) -> None:
        """The seed is the release's own prose, which quotes earlier runs of this check. v0.8.7's
        first RTX 5090 window seeded the misspelled copy v0.8.6's notes quote, and after a hot
        restore the model returned that copy instead of the planted nonce. The planted nonce must be
        the only copy of its digits the session holds, whatever the documents say."""
        block = documented_route.extract(documented_route.DEFAULT_DOC, documented_route.RESTART_SEED_HEADING)
        digits = set(re.findall(r"\b[A-Z]+-(\d{6})\b", block.text))
        self.assertEqual(len(digits), 1, block.text)
        seed = documented_route.restart_seed(documented_route.DEFAULT_DOC, ROOT)
        self.assertNotIn(digits.pop().encode(), seed)

    def test_model_download_blocks_survive_a_rerun_with_a_complete_file(self) -> None:
        """curl 8.5 with --fail turns the CDN's HTTP 416 for a complete-file resume into exit 22,
        so a reader who reruns the prepare block after any later failure was stopped there
        (measured 2026-09-13). Both download blocks must let the byte count decide instead."""
        doc = documented_route.DEFAULT_DOC.read_text(encoding="utf-8")
        blocks = [b for b in documented_route.parse_blocks(doc) if "--continue-at -" in b.text]

        for block in blocks:
            self.assertIn("artifact_bytes", block.text)
            if block.language == "sh":
                self.assertRegex(block.text, r'curl --fail[^\n]*\\\n\s*\|\| test "\$\(stat -c %s "\$MODEL"\)" = "\$MODEL_BYTES"')
            else:
                self.assertIn("$LASTEXITCODE -ne 0 -and (Get-Item $Model", block.text)

    def test_every_nonce_check_plants_without_a_restatement_and_recalls_verbatim(self) -> None:
        """The lanes sample at temperature 1.0, so every copy of the nonce the model writes may
        change it, and a restated copy becomes what the recall turn copies. v0.7.4's probe and
        v0.8.6's macOS route both failed on COBOLT-493817 that way. Every documented route and the
        structured probe must plant the nonce with an OK-only reply and ask for a verbatim recall."""
        prompts = []
        for lane in documented_route.LANES:
            for step, block in documented_route.lane_blocks(documented_route.DEFAULT_DOC, lane):
                quoted = r'"([^"\n]*)"' if block.language == "sh" else r"'([^'\n]*)'"
                prompts += [(f"{lane}/{step.slug}", text) for text in re.findall(quoted, block.text)]
        probe = ast.parse((ROOT / "scripts" / "hosts" / "omp-client-probe.py").read_text(encoding="utf-8"))
        for node in ast.walk(probe):
            if (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "call"
                    and len(node.args) == 2 and isinstance(node.args[1], ast.List)
                    and isinstance(node.args[1].elts[-1], ast.Constant)):
                prompts.append(("omp-client-probe", node.args[1].elts[-1].value))
        planted = recalled = 0
        for where, text in prompts:
            if "nonce" not in text.lower():
                continue
            if re.search(r"\b[A-Z]+-\d{6}\b", text):
                planted += 1
                self.assertTrue(text.endswith("Reply OK only."), f"{where} invites a restatement: {text!r}")
            else:
                recalled += 1
                self.assertIn("verbatim, character for character", text, f"{where}: {text!r}")
                self.assertTrue(text.endswith("Return nothing else."), f"{where}: {text!r}")
        # Four documented checks (RTX 4090, Windows, macOS resume and restart) and the probe.
        self.assertGreaterEqual(planted, 5)
        self.assertGreaterEqual(recalled, 5)


class RunnerTests(unittest.TestCase):
    def write_bundle(self, root: Path, steps: list[tuple[str, ...]]) -> Path:
        bundle = root / "bundle"
        bundle.mkdir()
        manifest = []
        for position, step in enumerate(steps, start=1):
            slug, body = step[0], step[1]
            heading = step[2] if len(step) > 2 else "H"
            name = f"{position:02d}-{slug}.sh"
            (bundle / name).write_text(body, encoding="utf-8")
            manifest.append({"position": position, "slug": slug, "file": name, "heading": heading,
                             "index": 0, "language": "sh",
                             "sha256": hashlib.sha256(body.encode()).hexdigest()})
        (bundle / "manifest.json").write_text(json.dumps({
            "lane": "smoke", "document": "doc", "document_sha256": "0" * 64, "steps": manifest}))
        clone = root / "clone"
        clone.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=clone, check=True)
        return bundle

    HEALTH_LISTENER = ("#!/bin/sh\n"
                       "exec python3 -c 'from http.server import BaseHTTPRequestHandler, HTTPServer\n"
                       "class H(BaseHTTPRequestHandler):\n"
                       "    def do_GET(self):\n"
                       "        self.send_response(200); self.send_header(\"Content-Length\", \"2\"); self.end_headers(); self.wfile.write(b\"ok\")\n"
                       "    def log_message(self, *a): pass\n"
                       "HTTPServer((\"127.0.0.1\", 18089), H).serve_forever()'\n")

    def write_tunnel_listener(self, root: Path, body: str | None = None) -> None:
        listener = root / "clone" / "open-tunnel.sh"
        listener.write_text(body if body is not None else self.HEALTH_LISTENER)
        listener.chmod(0o755)

    def run_bundle(self, root: Path, bundle: Path, stdin: int | None = None,
                   timeout: float | None = None) -> tuple[int, dict]:
        receipt = root / "receipt.json"
        completed = subprocess.run(["bash", str(RUNNER), str(bundle), str(root / "clone"), str(receipt)],
                                   stdin=stdin, capture_output=True, text=True, check=False,
                                   timeout=timeout)
        return completed.returncode, json.loads(receipt.read_text())

    def test_blocks_share_one_shell_and_the_first_failure_ends_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self.write_bundle(root, [
                ("define", "ROUTE_VAR=carried\n"),
                ("use", 'test "$ROUTE_VAR" = carried\n'),
                ("break", "false\n"),
                ("after", "echo never\n"),
            ])
            code, receipt = self.run_bundle(root, bundle)
            self.assertEqual(code, 1)
            self.assertEqual(receipt["status"], "failed")
            self.assertEqual([s["status"] for s in receipt["steps"]], ["passed", "passed", "failed", "skipped"])
            self.assertIn("exit 1: false", receipt["steps"][2]["error"])

    def test_a_step_that_consumes_stdin_cannot_end_the_run_early(self) -> None:
        """A block that reads stdin or backgrounds a process must not eat the step list;
        a run that executed only some steps is a failure, never a pass (macOS route, EXP-032)."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self.write_bundle(root, [
                ("eats-stdin", "cat >/dev/null\n"),
                ("after", "echo reached > \"$PWD/../after.txt\"\n"),
            ])
            code, receipt = self.run_bundle(root, bundle)
            self.assertEqual(code, 0, receipt)
            self.assertEqual([s["status"] for s in receipt["steps"]], ["passed", "passed"])
            self.assertTrue((root / "after.txt").exists())

    def test_a_block_never_waits_on_the_runners_stdin(self) -> None:
        """OMP 18.4.0's print mode reads piped stdin to EOF before its first request. Run over
        ssh from a terminal that never closes, the runner's stdin never ends, and a client that
        inherited it never sent a request (v0.9.0's second RTX 5090 window). A block reads
        nothing from the runner."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self.write_bundle(root, [("reads-piped-input", "cat >/dev/null\n")])
            read_end, write_end = os.pipe()  # never written, open until the run ends
            try:
                code, receipt = self.run_bundle(root, bundle, stdin=read_end, timeout=30)
            finally:
                os.close(write_end)
                os.close(read_end)
            self.assertEqual(code, 0, receipt)
            self.assertEqual([s["status"] for s in receipt["steps"]], ["passed"])

    def test_the_tunnel_block_is_stopped_for_real_before_fail_closed(self) -> None:
        """The tunnel block execs ssh inside the runner's wrapper; stopping only the wrapper
        leaves the listener up and the fail-closed check sees a live route (macOS run 8)."""
        probe = socket.socket()
        probe.settimeout(0.5)
        try:
            probe.connect(("127.0.0.1", 18089))
        except OSError:
            pass
        else:
            self.skipTest("local port 18089 is in use")
        finally:
            probe.close()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self.write_bundle(root, [
                ("tunnel", "./open-tunnel.sh\n"),
                ("fail-closed", "python3 - <<'PY'\nimport socket, sys\ns = socket.socket(); s.settimeout(1)\n"
                                "try: s.connect(('127.0.0.1', 18089))\nexcept OSError: sys.exit(0)\n"
                                "print('outage request unexpectedly succeeded'); sys.exit(1)\nPY\n", "Fail closed"),
            ])
            self.write_tunnel_listener(root)
            code, receipt = self.run_bundle(root, bundle)
            self.assertEqual(code, 0, receipt)
            self.assertEqual([s["status"] for s in receipt["steps"]], ["passed", "passed"])
            self.assertIn("tunnel stopped before this block", receipt["steps"][1]["substitution"])

    def test_the_route_refuses_to_start_a_tunnel_on_a_port_it_does_not_own(self) -> None:
        """A forward left by an earlier run answers the readiness probe: the tunnel step would
        pass without binding and its listener would survive stop_tunnel, so the fail-closed
        block sees a live route. The run must refuse instead (measured 2026-09-12)."""
        import contextlib
        squatter = socket.socket()
        squatter.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            squatter.bind(("127.0.0.1", 18089))
        except OSError:
            self.skipTest("local port 18089 is in use")
        squatter.listen(1)
        with contextlib.closing(squatter), tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self.write_bundle(root, [("tunnel", "./open-tunnel.sh\n")])
            listener = root / "clone" / "open-tunnel.sh"
            listener.write_text("#!/bin/sh\nexec sleep 600\n")
            listener.chmod(0o755)
            code, receipt = self.run_bundle(root, bundle)
            self.assertEqual(code, 1, receipt)
            self.assertEqual(receipt["steps"][0]["status"], "failed")

    def test_a_failed_run_stops_the_tunnel_it_started(self) -> None:
        """The error path must release the forward, or the next run inherits it."""
        probe = socket.socket()
        probe.settimeout(0.5)
        try:
            probe.connect(("127.0.0.1", 18089))
        except OSError:
            pass
        else:
            self.skipTest("local port 18089 is in use")
        finally:
            probe.close()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self.write_bundle(root, [("tunnel", "./open-tunnel.sh\n"), ("break", "false\n")])
            self.write_tunnel_listener(root)
            code, receipt = self.run_bundle(root, bundle)
            self.assertEqual(code, 1)
            self.assertEqual([s["status"] for s in receipt["steps"]], ["passed", "failed"])
            after = socket.socket()
            after.settimeout(1)
            with self.assertRaises(OSError):
                after.connect(("127.0.0.1", 18089))
            after.close()

    def test_a_tunnel_that_reaches_nothing_fails_its_own_step(self) -> None:
        """A bound forward only proves ssh exists. When the far end serves nothing the tunnel
        step used to pass and the failure surfaced two blocks later as a tool-turn error
        (measured 2026-09-12, post-cut). The step owns that diagnosis."""
        probe = socket.socket()
        probe.settimeout(0.5)
        try:
            probe.connect(("127.0.0.1", 18089))
        except OSError:
            pass
        else:
            self.skipTest("local port 18089 is in use")
        finally:
            probe.close()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self.write_bundle(root, [("tunnel", "./open-tunnel.sh\n"), ("after", "echo never\n")])
            # binds the forward's port but answers no HTTP: ssh is up, the route is not
            self.write_tunnel_listener(root, "#!/bin/sh\nexec python3 -c 'import socket, time\n"
                                             "s = socket.socket()\n"
                                             "s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n"
                                             "s.bind((\"127.0.0.1\", 18089)); s.listen(64); time.sleep(600)'\n")
            code, receipt = self.run_bundle(root, bundle)
            self.assertEqual(code, 1, receipt)
            self.assertEqual([s["status"] for s in receipt["steps"]], ["failed", "skipped"])

    def test_a_step_whose_bytes_drifted_from_the_document_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self.write_bundle(root, [("ok", "true\n"), ("edited", "true\n")])
            (bundle / "02-edited.sh").write_text("true # edited after bundling\n")
            code, receipt = self.run_bundle(root, bundle)
            self.assertEqual(code, 1)
            self.assertEqual(receipt["steps"][1]["status"], "refused")


class NativeInstallGateTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed to execute the install gate")
    def test_unqualified_or_ambiguous_native_variant_stops_before_download(self) -> None:
        """Prospective documentation is not install authority: execute its real manifest gate.

        A provider file or a GPU name in prose is not evidence of qualification. Both native
        recipes must refuse missing, preview and duplicate manifest rows before any download.
        """
        for lane in ("rtx3090", "rtx4090"):
            variant_id = f"{lane}-windows-native"
            blocks = {step.slug: block.text for step, block in documented_route.lane_blocks(
                documented_route.DEFAULT_DOC, f"{lane}-native")}
            cases = ([], [{"id": variant_id, "status": "preview"}],
                     [{"id": variant_id, "status": "qualified"}] * 2)
            for variants in cases:
                with self.subTest(lane=lane, variants=variants), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    for release in ("v0.9.0", "v0.9.1"):
                        directory = root / "releases" / release
                        directory.mkdir(parents=True)
                        (directory / "manifest.json").write_text(json.dumps({
                            "components": {"ninfer_variants": variants}}))
                    script = root / "install-gate.ps1"
                    script.write_text(
                        "function Set-ExecutionPolicy {}\n"  # Windows-only policy; irrelevant to the gate.
                        "function Invoke-WebRequest { throw 'unexpected download' }\n"
                        + blocks["variant"] + "try {\n" + blocks["stage-and-install"]
                        + "\nthrow 'unqualified variant reached install'\n} catch {\n"
                        "if ($_.Exception.Message -cne 'requested native runtime variant is not uniquely qualified') {throw}\n"
                        "'REFUSED_BEFORE_DOWNLOAD'\n}\n")
                    result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(script)],
                                            cwd=root, capture_output=True, text=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout.strip(), "REFUSED_BEFORE_DOWNLOAD")



if __name__ == "__main__":
    unittest.main()
