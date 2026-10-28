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


def control_blocks() -> list[documented_route.Block]:
    return documented_route.parse_blocks(documented_route.DEFAULT_DOC.read_text(encoding="utf-8"))


class ReleaseProseTests(unittest.TestCase):
    # One-letter v-versions (v0.11.0) are not words of two or more letters.
    GLUED = re.compile(r"\b[^\W\d_]{2,}\d\w*\b")
    IDENTIFIER = re.compile(
        r"[0-9a-fA-F]{7,}|"  # Committed abbreviated/full hexadecimal identities.
        r"(?i:bf16|nvfp4|int8|fp(?:8|16|32|64))|"  # Recorded numeric/quantization formats.
        r"(?i:qwen3|qwen38|dflash2|mtp(?:0|3|7))|"  # Model and speculative-backend names.
        r"Gen3|x86|arm64|sm120|"  # PCIe generation, CPU targets and CUDA architecture.
        r"(?i:sha256|sha256sums|mp4)|ext4|WSL2|"  # Digest/file formats, filesystem and OS.
        r"DS918|can1357|"  # The documented NAS model and upstream repository owner.
        r"rk2v4|split[24]|rtx(?:3090|4090)|"  # Historical model, kernel routes and native variant IDs.
        r"fanout43|durable4090"  # Exact historical council-receipt suffixes in RELEASES.md.
    )

    @staticmethod
    def prose(text: str) -> str:
        lines = []
        fence = None
        for line in text.splitlines():
            marker = re.match(r"^\s*(?:>\s*)*(`{3,}|~{3,})(.*)$", line)
            if marker:
                token, suffix = marker.groups()
                if fence is None:
                    fence = (token[0], len(token))
                elif token[0] == fence[0] and len(token) >= fence[1] and not suffix.strip():
                    fence = None
                lines.append("")
                continue
            lines.append(line if fence is None else "")
        text = "\n".join(lines)
        text = re.sub(r"(?<!`)(`+)(?!`).*?(?<!`)\1(?!`)",
                      lambda match: " " + "\n" * match.group().count("\n"), text, flags=re.S)
        text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
        text = re.sub(r"(?m)^\s*\[[^\]]+\]:.*$", "", text)
        return re.sub(r"\b(?:[A-Za-z][A-Za-z0-9+.-]*://|mailto:)\S+", "", text)

    @classmethod
    def glued_tokens(cls, text: str) -> list[tuple[int, str]]:
        prose = cls.prose(text)
        return [(prose.count("\n", 0, match.start()) + 1, match.group())
                for match in cls.GLUED.finditer(prose)
                if cls.IDENTIFIER.fullmatch(match.group()) is None]

    @staticmethod
    def current_changelog(text: str, release: str) -> str:
        lines = []
        current = True
        for line in text.splitlines():
            heading = re.match(r"^## \[([^\]]+)\]", line)
            if heading:
                current = heading.group(1) in ("Unreleased", release)
            lines.append(line if current else "")
        return "\n".join(lines)

    def test_release_facing_prose_has_no_glued_tokens(self) -> None:
        release = json.loads((ROOT / "compatibility.json").read_text())["product_release"]
        paths = [ROOT / name for name in ("README.md", "CHANGELOG.md", "ROADMAP.md")]
        paths += sorted((ROOT / "docs").glob("*.md"))
        paths.append(ROOT / "releases" / release / "NINFER_RELEASE_NOTES.md")
        for path in paths:
            with self.subTest(path=str(path.relative_to(ROOT))):
                text = path.read_text(encoding="utf-8")
                if path.name == "CHANGELOG.md":
                    text = self.current_changelog(text, release)
                matches = self.glued_tokens(text)
                self.assertEqual(matches, [], f"{path.relative_to(ROOT)} glued prose: {matches}")

    def test_glued_words_are_rejected_in_prose(self) -> None:
        text = ("RTX5090 RTX4090 OMP18 Retainedv0 Fresh18 Focused5090 selected1302d639 "
                "passes28 refused0 Its65b6c426 therefore3a final40 CI38042843797 "
                "arbitrary123 café2")
        self.assertEqual([token for _, token in self.glued_tokens(text)], text.split())

    def test_only_complete_documented_identifiers_are_allowed(self) -> None:
        text = ("abcdef1 eaf221ac c6f41f52 v0.11.0 v18.8.7 Gen3 x86 arm64 sha256 "
                "SHA256SUMS qwen38 Qwen3.8 DFlash2 MTP0 MTP3 MTP7 NVFP4 BF16 INT8 "
                "FP8 FP16 FP32 FP64 sm120 MP4 ext4 WSL2 DS918+ can1357 rk2v4-e8 "
                "split2 split4 rtx3090 rtx4090 fanout43 durable4090")
        self.assertEqual(self.glued_tokens(text), [])
        invalid = "abc123 bf16result arm64owners sha256broken mtp99 rtx4090owner rtx5090owner"
        self.assertEqual([token for _, token in self.glued_tokens(invalid)], invalid.split())

    def test_current_changelog_excludes_older_published_entries(self) -> None:
        text = ("# Changelog\n## [Unreleased]\nFresh18\n"
                "## [v0.11.0] - 2026-10-10\nRetainedv0\n"
                "## [v0.10.0] - 2026-10-02\nLegacyv0\n")
        self.assertEqual(self.glued_tokens(self.current_changelog(text, "v0.11.0")),
                         [(3, "Fresh18"), (5, "Retainedv0")])

    def test_fenced_inline_and_url_literals_are_not_prose(self) -> None:
        text = ("RTX 5090 and OMP 18.8.7; `RTX5090` and ``on5861712f``.\n"
                "```sh\nOMP18.8.7 at13:46\n```\n"
                "~~~~text\nwith385.948s\n~~~~~\n"
                "> ```sh\n> RTX5090 and OMP18.8.7\n> ```\n"
                "[lane](https://example.invalid/RTX5090/on5861712f)\n"
                "https://example.invalid/OMP18.8.7\n"
                "ftp://example.invalid/Fresh18 ssh://example.invalid/OMP18\n"
                "mailto:person123@example.invalid\n"
                "[asset]: https://example.invalid/RTX5090\n")
        self.assertEqual(self.glued_tokens(text), [])

    def test_link_labels_remain_prose(self) -> None:
        self.assertEqual(self.glued_tokens("[RTX5090](asset.json)"), [(1, "RTX5090")])


class ExtractionTests(unittest.TestCase):
    def test_v0140_prepared_routes_keep_all_composer_addresses_and_new_pins(self) -> None:
        routes = {lane: documented_route.lane_blocks(documented_route.DEFAULT_DOC, lane)
                  for lane in documented_route.LANES}
        self.assertEqual(sum(len(steps) for steps in routes.values()), 31)
        for lane, steps in routes.items():
            for step, block in steps:
                self.assertEqual(documented_route.extract(
                    documented_route.DEFAULT_DOC, step.heading, step.index).text, block.text)
                if step.slug == "client-install":
                    self.assertIn("v18.12.6", block.text)
                if step.slug == "clone-and-verify":
                    self.assertIn("git clone --branch v0.14.0 --depth 1", block.text)
                    self.assertIn("--require-ready", block.text)
        executable = "\n".join(
            block.text for block in documented_route.parse_blocks(
                documented_route.DEFAULT_DOC.read_text(encoding="utf-8"))
            if block.language in ("sh", "powershell"))
        self.assertNotIn("v0.13.1", executable)
        self.assertEqual(re.findall(r"git clone --branch (v[0-9.]+)", executable),
                         ["v0.14.0"] * 4)
        self.assertEqual(re.findall(r"releases[/\\](v[0-9.]+)[/\\]manifest\.json", executable),
                         ["v0.14.0"] * 5)
        preparation = documented_route.extract(
            documented_route.DEFAULT_DOC, "3. Prepare the model and key on the inference host").text
        self.assertIn('CHECKPOINTS="$ROOT/checkpoints-v013"', preparation)
        self.assertIn("releases/v0.14.0/manifest.json", preparation)
        self.assertIn('MODEL="$ROOT/qwen3_8_27b-v3.ninfer"', preparation)
        for lane in ("rtx4090-native", "rtx3090-native"):
            steps = {step.slug: block for step, block in routes[lane]}
            native = steps["stage-and-install"].text
            self.assertIn(r"releases\v0.14.0\manifest.json", native)
            self.assertIn("'qwen3_8_27b-v3.ninfer'", native)
            self.assertIn("$NativeModel = $Manifest.components.model", native)
            self.assertNotIn("components.native_model", native)
            self.assertIn("$NativeModel.artifact_sha256 -cne $Variant[0].model_artifact_sha256", native)

    def test_every_lane_resolves_to_fenced_blocks_of_its_language(self) -> None:
        for lane in documented_route.LANES:
            with self.subTest(lane=lane):
                resolved = documented_route.lane_blocks(documented_route.DEFAULT_DOC, lane)
                self.assertEqual(len(resolved), len(documented_route.LANES[lane]))
                for step, block in resolved:
                    self.assertEqual(block.language, step.language)
                    self.assertTrue(block.text.strip(), f"{lane}/{step.slug} is empty")

    def test_bundle_files_are_the_documented_bytes(self) -> None:
        doc = documented_route.DEFAULT_DOC
        for lane in documented_route.LANES:
            with self.subTest(lane=lane), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary)
                manifest = documented_route.bundle(doc, lane, output)
                self.assertEqual(len(manifest["steps"]), len(documented_route.LANES[lane]))
                for step in manifest["steps"]:
                    data = (output / step["file"]).read_bytes()
                    self.assertEqual(hashlib.sha256(data).hexdigest(), step["sha256"])
                    block = documented_route.extract(doc, step["heading"], step["index"])
                    self.assertEqual(data.decode("utf-8"), block.text)
                self.assertEqual(
                    manifest["document_sha256"],
                    hashlib.sha256(doc.read_bytes()).hexdigest(),
                )

    def test_native_route_steps_carry_the_variables_they_use(self) -> None:
        """A reader pastes the blocks into one window; a later block may only use names an
        earlier one defined. Catches a doc edit that moves a definition below its first use."""
        for lane in ("rtx4090-native", "rtx3090-native"):
            with self.subTest(lane=lane):
                defined: set[str] = set()
                for step, block in documented_route.lane_blocks(documented_route.DEFAULT_DOC, lane):
                    used = set(re.findall(r"\$([A-Z][A-Za-z]+)\b", block.text))
                    assigned = set(re.findall(r"^\s*\$([A-Z][A-Za-z]+)\s*=", block.text, re.M))
                    missing = {name for name in used - assigned - defined if name not in {"Sid", "Rule", "Asset", "Name", "Path", "Applied", "Acl", "Admins", "Secret", "LASTEXITCODE", "HOME"}}
                    self.assertFalse(missing, f"{step.slug} uses {sorted(missing)} before any block defines them")
                    defined |= assigned

    def test_windows_blocks_stay_within_windows_powershell(self) -> None:
        """The Windows routes run in Windows PowerShell 5.1 on .NET Framework. These calls exist
        only on .NET 5+ and failed the RTX 4090 route on a stock host (EXP-032)."""
        forbidden = ("[Convert]::ToHexString", "RandomNumberGenerator]::Fill(", "[Convert]::FromHexString")
        for block in control_blocks():
            if block.language != "powershell":
                continue
            for call in forbidden:
                self.assertNotIn(call, block.text, f"{block.heading!r} uses {call}, which Windows PowerShell lacks")

    def test_no_block_ends_by_opening_an_interactive_session(self) -> None:
        """A block that launches the OMP TUI cannot be followed by 'run these in the same
        process' and cannot be checked by a reader's shell; interactive launches live in prose,
        blocks stay non-interactive on every platform (EXP-032)."""
        import re
        launch = re.compile(r"(?:^|[\s&;(])(?:omp|\$Launcher|& \"\$env:LOCALAPPDATA\\OMP\\omp\.cmd\")\s")
        for block in control_blocks():
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
        digits = set(re.findall(r"\b(\d{6})-\d{6}\b", block.text))
        self.assertEqual(len(digits), 1, block.text)
        seed = documented_route.restart_seed(documented_route.DEFAULT_DOC, ROOT)
        self.assertNotIn(digits.pop().encode(), seed)

    def test_model_download_blocks_survive_a_rerun_with_a_complete_file(self) -> None:
        """curl 8.5 with --fail turns the CDN's HTTP 416 for a complete-file resume into exit 22,
        so a reader who reruns the prepare block after any later failure was stopped there
        (measured 2026-09-13). Both download blocks must let the byte count decide instead."""
        blocks = [block for block in control_blocks() if "--continue-at -" in block.text]

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
        nonce = next(ast.literal_eval(node.value) for node in probe.body
                     if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == "NONCE"
                             for target in node.targets))
        for node in ast.walk(probe):
            if (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "call"
                    and len(node.args) == 2 and isinstance(node.args[1], ast.List)):
                prompt = node.args[1].elts[-1]
                if isinstance(prompt, ast.Constant):
                    self.assertNotIn("Remember the nonce ", prompt.value, "probe plant must interpolate NONCE")
                    prompts.append(("omp-client-probe", prompt.value))
                elif isinstance(prompt, ast.JoinedStr):
                    expected = ast.parse(
                        'f"Remember the nonce {NONCE} for my next turn. Reply OK only."', mode="eval").body
                    self.assertEqual(ast.dump(prompt), ast.dump(expected))
                    prompts.append(("omp-client-probe", f"Remember the nonce {nonce} for my next turn. Reply OK only."))
        planted = recalled = 0
        for where, text in prompts:
            if "nonce" not in text.lower():
                continue
            if re.search(r"\b(?:[A-Z]+-\d{6}|\d{6}-\d{6})\b", text):
                planted += 1
                self.assertTrue(text.endswith("Reply OK only."), f"{where} invites a restatement: {text!r}")
            else:
                recalled += 1
                self.assertIn("verbatim, character for character", text, f"{where}: {text!r}")
                self.assertTrue(text.endswith("Return nothing else."), f"{where}: {text!r}")
        # Five documented checks (both native lanes, Windows, macOS resume/restart) and the probe.
        self.assertGreaterEqual(planted, 5)
        self.assertGreaterEqual(recalled, 5)

    def test_every_nonce_check_uses_the_documented_numeric_nonce(self) -> None:
        """All route plants, greps and driver checks must use the same hardened nonce.
        This is an exact-recall test; changing its token must not leave a driver
        checking the previous token or widen the answer comparison."""
        nonce = "493817-205361"
        drivers = ("omp-client-probe.py", "accept-rtx5090-routes.py", "accept-rtx4090-route.py")
        for driver in drivers:
            tree = ast.parse((ROOT / "scripts" / "hosts" / driver).read_text(encoding="utf-8"))
            constants = [ast.literal_eval(node.value) for node in tree.body
                         if isinstance(node, ast.Assign)
                         and any(isinstance(target, ast.Name) and target.id == "NONCE"
                                 for target in node.targets)]
            with self.subTest(driver=driver):
                self.assertEqual(constants, [nonce], f"{driver} disagrees with the documented nonce")
            for node in ast.walk(tree):
                if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                        and re.fullmatch(r"(?:[A-Z]+-\d{6}|\d{6}-\d{6})", node.value)):
                    with self.subTest(driver=driver, check=node.value):
                        self.assertEqual(node.value, nonce)

        plants = greps = 0
        for lane in documented_route.LANES:
            for step, block in documented_route.lane_blocks(documented_route.DEFAULT_DOC, lane):
                for planted in re.findall(r"Remember the nonce ([A-Z0-9-]+)(?: for my next turn)?\.", block.text):
                    plants += 1
                    with self.subTest(lane=lane, step=step.slug, plant=planted):
                        self.assertEqual(planted, nonce)
                for checked in re.findall(r"grep -q ([A-Z0-9-]+)", block.text):
                    if re.fullmatch(r"(?:[A-Z]+-\d{6}|\d{6}-\d{6})", checked):
                        greps += 1
                        with self.subTest(lane=lane, step=step.slug, grep=checked):
                            self.assertEqual(checked, nonce)
        self.assertGreaterEqual(plants, 5)
        self.assertEqual(greps, 2)


class RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        # The runner checks its tunnel on a free ephemeral port, never on the documented 18089: a
        # live macOS route on this machine binds that port between its steps (omp-ninfer#97).
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            self.port = probe.getsockname()[1]

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
                       "HTTPServer((\"127.0.0.1\", {port}), H).serve_forever()'\n")

    def write_tunnel_listener(self, root: Path, body: str | None = None) -> None:
        listener = root / "clone" / "open-tunnel.sh"
        listener.write_text((body if body is not None else self.HEALTH_LISTENER).format(port=self.port))
        listener.chmod(0o755)

    def run_bundle(self, root: Path, bundle: Path, stdin: int | None = None,
                   timeout: float | None = None) -> tuple[int, dict]:
        receipt = root / "receipt.json"
        completed = subprocess.run(["bash", str(RUNNER), str(bundle), str(root / "clone"), str(receipt)],
                                   stdin=stdin, capture_output=True, text=True, check=False,
                                   timeout=timeout, env=dict(os.environ, ROUTE_TUNNEL_PORT=str(self.port)))
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
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self.write_bundle(root, [
                ("tunnel", "./open-tunnel.sh\n"),
                ("fail-closed", "python3 - <<'PY'\nimport socket, sys\ns = socket.socket(); s.settimeout(1)\n"
                                f"try: s.connect(('127.0.0.1', {self.port}))\nexcept OSError: sys.exit(0)\n"
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
        squatter.bind(("127.0.0.1", 0))
        squatter.listen(1)
        self.port = squatter.getsockname()[1]
        with contextlib.closing(squatter), tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self.write_bundle(root, [("tunnel", "./open-tunnel.sh\n")])
            listener = root / "clone" / "open-tunnel.sh"
            listener.write_text("#!/bin/sh\ntouch started\nexec sleep 600\n")
            listener.chmod(0o755)
            code, receipt = self.run_bundle(root, bundle)
            self.assertEqual(code, 1, receipt)
            self.assertEqual(receipt["steps"][0]["status"], "failed")
            self.assertFalse((root / "clone" / "started").exists(), "the tunnel started on a taken port")

    def test_a_failed_run_stops_the_tunnel_it_started(self) -> None:
        """The error path must release the forward, or the next run inherits it."""
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
                after.connect(("127.0.0.1", self.port))
            after.close()

    def test_a_tunnel_that_reaches_nothing_fails_its_own_step(self) -> None:
        """A bound forward only proves ssh exists. When the far end serves nothing the tunnel
        step used to pass and the failure surfaced two blocks later as a tool-turn error
        (measured 2026-09-12, post-cut). The step owns that diagnosis."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self.write_bundle(root, [("tunnel", "./open-tunnel.sh\n"), ("after", "echo never\n")])
            # binds the forward's port but answers no HTTP: ssh is up, the route is not
            self.write_tunnel_listener(root, "#!/bin/sh\nexec python3 -c 'import socket, time\n"
                                             "s = socket.socket()\n"
                                             "s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n"
                                             "s.bind((\"127.0.0.1\", {port})); s.listen(64); time.sleep(600)'\n")
            code, receipt = self.run_bundle(root, bundle)
            self.assertEqual(code, 1, receipt)
            self.assertEqual([s["status"] for s in receipt["steps"]], ["failed", "skipped"])

    def test_a_tunnel_checked_off_the_documented_port_says_so_in_its_receipt(self) -> None:
        """Only tests move the runner's tunnel checks off 18089, the port the documented forward
        binds; a receipt from such a run must not read as the documented route (omp-ninfer#97)."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self.write_bundle(root, [("tunnel", "./open-tunnel.sh\n")])
            self.write_tunnel_listener(root)
            code, receipt = self.run_bundle(root, bundle)
            self.assertEqual(code, 0, receipt)
            self.assertIn(str(self.port), receipt["steps"][0]["substitution"])

    def test_a_malformed_tunnel_port_is_refused_before_any_step_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self.write_bundle(root, [("mark", 'touch "$PWD/../ran"\n')])
            for port in ("0", "65536", "080", "port"):
                with self.subTest(port=port):
                    completed = subprocess.run(
                        ["bash", str(RUNNER), str(bundle), str(root / "clone"), str(root / "receipt.json")],
                        capture_output=True, text=True, check=False, timeout=30,
                        env=dict(os.environ, ROUTE_TUNNEL_PORT=port))
                    self.assertEqual(completed.returncode, 2, completed.stderr)
                    self.assertFalse((root / "ran").exists())
                    self.assertFalse((root / "receipt.json").exists())

    def test_missing_empty_or_nonexistent_arguments_are_refused_before_any_step_runs(self) -> None:
        """`cd -- ""` succeeds, so an empty CLONE ran the route in the caller's directory, and a
        missing or unwritable RECEIPT failed only after every step had run. The runner checks its
        arguments first and exits 2 with nothing run or written."""
        cases = {
            "no arguments": (),
            "no receipt": ("{bundle}", "{clone}"),
            "an extra argument": ("{bundle}", "{clone}", "{receipt}", "{receipt}"),
            "empty bundle": ("", "{clone}", "{receipt}"),
            "bundle without a manifest": ("{clone}", "{clone}", "{receipt}"),
            "empty clone": ("{bundle}", "", "{receipt}"),
            "missing clone": ("{bundle}", "{root}/missing", "{receipt}"),
            "empty receipt": ("{bundle}", "{clone}", ""),
            "receipt in a missing directory": ("{bundle}", "{clone}", "{root}/missing/receipt.json"),
            "receipt names a directory": ("{bundle}", "{clone}", "{clone}"),
        }
        for case, arguments in cases.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                bundle = self.write_bundle(root, [("mark", 'touch "$PWD/ran"\n')])
                paths = {"root": root, "bundle": bundle, "clone": root / "clone", "receipt": root / "receipt.json"}
                completed = subprocess.run(
                    ["bash", str(RUNNER), *(argument.format(**paths) for argument in arguments)],
                    cwd=root, capture_output=True, text=True, check=False, timeout=30,
                    env=dict(os.environ, ROUTE_TUNNEL_PORT=str(self.port)))
                self.assertEqual(completed.returncode, 2, completed.stderr)
                self.assertEqual(sorted(path.name for path in root.iterdir()), ["bundle", "clone"])
                self.assertFalse((root / "clone" / "ran").exists())

    def test_relative_arguments_name_paths_in_the_callers_directory(self) -> None:
        """The runner changes into CLONE before it reads BUNDLE and writes RECEIPT; a relative
        path still names what it named where the operator typed it."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_bundle(root, [("mark", 'touch "$PWD/ran"\n')])
            completed = subprocess.run(
                ["bash", str(RUNNER), "bundle", "clone", "receipt.json"],
                cwd=root, capture_output=True, text=True, check=False, timeout=30,
                env=dict(os.environ, ROUTE_TUNNEL_PORT=str(self.port)))
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads((root / "receipt.json").read_text())["status"], "passed")
            self.assertTrue((root / "clone" / "ran").exists())

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
            releases = set(re.findall(r"releases[/\\](v[^/\\\s]+)[/\\]manifest\.json",
                                      "\n".join(blocks.values())))
            self.assertTrue(releases, "native route must read a release manifest")
            cases = ([], [{"id": variant_id, "status": "preview"}],
                     [{"id": variant_id, "status": "qualified"}] * 2)
            for variants in cases:
                with self.subTest(lane=lane, variants=variants), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    for release in releases:
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


class HostPreparationTests(unittest.TestCase):
    """A reader reruns the inference host's preparation block after any later failure. The rerun
    must keep the bearer key: checkpoint MACs and every client's copy are bound to it
    (omp-ninfer#100 item 6)."""

    def prepare(self, home: Path) -> bytes:
        block = documented_route.extract(
            documented_route.DEFAULT_DOC, "3. Prepare the model and key on the inference host").text
        release = re.search(r"releases/(v[0-9.]+)/manifest\.json", block).group(1)
        model = json.loads((ROOT / "releases" / release / "manifest.json").read_text(
            encoding="utf-8"))["components"]["model"]
        # The transfer and the 20 GB checks are not under test: curl fetches nothing, and the
        # size and checksum probes report the pinned artifact.
        stubs = home / "stubs"
        stubs.mkdir(exist_ok=True)
        for name, body in (("curl", "exit 0"), ("stat", f"echo {model['artifact_bytes']}"),
                           ("sha256sum", "cat >/dev/null")):
            (stubs / name).write_text(f"#!/bin/sh\n{body}\n")
            (stubs / name).chmod(0o755)
        subprocess.run(["bash", "-eo", "pipefail", "-c", block], cwd=ROOT, check=True, timeout=60,
                       env={"HOME": str(home), "PATH": f"{stubs}{os.pathsep}{os.environ['PATH']}"})
        return (home / ".config" / "omp-ninfer" / "api-key").read_bytes()

    def test_a_rerun_keeps_the_existing_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            key = home / ".config" / "omp-ninfer" / "api-key"
            first = self.prepare(home)
            self.assertRegex(first.decode(), r"\A[0-9a-f]{64}\n\Z")
            self.assertEqual(key.stat().st_mode & 0o777, 0o600)
            self.assertEqual(self.prepare(home), first)
            key.write_bytes(b"")  # what an interrupted first run leaves behind
            self.assertRegex(self.prepare(home).decode(), r"\A[0-9a-f]{64}\n\Z")


@unittest.skipIf(os.name == "nt", "executes POSIX shell blocks and checks POSIX file modes")
class ClientConfigurationTests(unittest.TestCase):
    """Section 7's macOS/Linux blocks install OMP's models.yml and config.yml. A reader reruns blocks
    after a later failure and may already run OMP with their own providers and settings: a block
    leaves an identical file alone and refuses to replace a different one, as the Windows blocks
    refuse (omp-ninfer#100 item 6)."""

    @staticmethod
    def install(home: Path, slug: str) -> subprocess.CompletedProcess:
        block = {step.slug: block.text for step, block in documented_route.lane_blocks(
            documented_route.DEFAULT_DOC, "rtx5090-macos-client")}[slug]
        return subprocess.run(["bash", "-eo", "pipefail", "-c", block], cwd=ROOT, capture_output=True,
                              text=True, timeout=30, env={"HOME": str(home), "PATH": os.environ["PATH"]})

    def test_a_rerun_keeps_an_identical_file_and_a_different_one_is_refused(self) -> None:
        for slug, name, source in (("provider", "models.yml", "models.fragment.yml"),
                                   ("fail-closed-config", "config.yml", "fail-closed.yml")):
            with self.subTest(slug=slug), tempfile.TemporaryDirectory() as temporary:
                home = Path(temporary)
                target = home / ".omp" / "agent" / name
                target.parent.mkdir(parents=True)  # section 6 creates it
                shipped = (ROOT / "examples" / "manual-tunnel" / source).read_bytes()
                for attempt in ("fresh", "rerun"):
                    completed = self.install(home, slug)
                    self.assertEqual(completed.returncode, 0, f"{attempt}: {completed.stderr}")
                    self.assertEqual(target.read_bytes(), shipped)
                    self.assertEqual(target.stat().st_mode & 0o777, 0o600)
                own = b"# the reader's own OMP settings\n"
                target.write_bytes(own)
                refused = self.install(home, slug)
                self.assertNotEqual(refused.returncode, 0)
                self.assertIn(name, refused.stderr)
                self.assertEqual(target.read_bytes(), own)


@unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed to execute the Windows blocks")
class WindowsNativeCommandTests(unittest.TestCase):
    """A pasted PowerShell block does not stop at a failed native command; without a $LASTEXITCODE
    check its next line runs (omp-ninfer#100 item 7). Each block runs with its native commands
    stubbed: every stub records its call, and the named ones fail."""

    @staticmethod
    def steps(lane: str) -> dict[str, str]:
        return {step.slug: block.text
                for step, block in documented_route.lane_blocks(documented_route.DEFAULT_DOC, lane)}

    def run_block(self, block: str, failing: set[str], prelude: str = "",
                  stale_clone: bool = False) -> tuple[list[str], bool]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stubs = root / "bin"
            stubs.mkdir()
            calls = root / "calls.txt"
            for name, effect in (("git", "mkdir -p omp-ninfer"), ("py", ""), ("wsl.exe", ""), ("omp", "")):
                result = "exit 1" if name in failing else f"{effect}\nexit 0"
                (stubs / name).write_text(f"#!/bin/sh\necho {name} >> '{calls}'\n{result}\n")
                (stubs / name).chmod(0o755)
            if stale_clone:
                (root / "omp-ninfer").mkdir()
            script = root / "block.ps1"
            script.write_text("function Set-ExecutionPolicy {}\n"  # Windows-only policy; not under test.
                              + prelude + block + "'NEXT_BLOCK_REACHED'\n")
            completed = subprocess.run(
                [shutil.which("pwsh"), "-NoProfile", "-File", str(script)], cwd=root, capture_output=True,
                text=True, timeout=60, env=dict(os.environ, PATH=f"{stubs}{os.pathsep}{os.environ['PATH']}"))
            ran = calls.read_text().split() if calls.exists() else []
            return ran, "NEXT_BLOCK_REACHED" in completed.stdout

    def test_a_failed_clone_or_ready_gate_stops_the_route(self) -> None:
        for lane in ("rtx5090-windows-client", "rtx4090-native", "rtx3090-native"):
            block = self.steps(lane)["clone-and-verify"]
            with self.subTest(lane=lane, failing="nothing"):
                self.assertEqual(self.run_block(block, set()), (["git", "py"], True))
            with self.subTest(lane=lane, failing="ready gate"):
                self.assertEqual(self.run_block(block, {"py"}), (["git", "py"], False))
            with self.subTest(lane=lane, failing="clone"):
                # The likeliest failed clone: an earlier release's clone already holds the name.
                self.assertEqual(self.run_block(block, {"git"}, stale_clone=True), (["git"], False))

    def test_a_failed_runtime_stop_ends_the_outage_check_before_its_request(self) -> None:
        block = self.steps("rtx5090-windows-client")["fail-closed"]
        prelude = "$Launcher = Join-Path $PSScriptRoot 'bin/omp'\n"
        # The stop works and the request fails, as an outage requires.
        self.assertEqual(self.run_block(block, {"omp"}, prelude), (["wsl.exe", "omp"], True))
        # The runtime may still be serving: no request may stand in for the outage.
        self.assertEqual(self.run_block(block, {"wsl.exe", "omp"}, prelude), (["wsl.exe"], False))


@unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed to execute the Windows host scripts")
@unittest.skipIf(os.name == "nt", "the native command stubs are POSIX shell scripts")
class WindowsHostScriptNativeCommandTests(unittest.TestCase):
    """The Windows acceptance scripts check each native command's exit status (omp-ninfer#100
    item 7). git and py are stubs that record their calls; the named git subcommands fail."""

    CANDIDATE = "1" * 40
    # The receipt's host facts exist only on Windows and are not under test.
    RUNNER_HOST = r"""param($Runner, $Bundle, $WorkDir, $Receipt, $Candidate)
function Get-CimInstance { [pscustomobject]@{ Caption = 'fixture' } }
function Set-ExecutionPolicy {}
class FixtureIdentity { static [object] GetCurrent() { return [FixtureIdentity]::new() } }
class FixturePrincipal { FixturePrincipal([object]$Identity) {} [bool] IsInRole([object]$Role) { return $false } }
$accelerators = [psobject].Assembly.GetType('System.Management.Automation.TypeAccelerators')
$accelerators::Add('Security.Principal.WindowsIdentity', [FixtureIdentity])
$accelerators::Add('Security.Principal.WindowsPrincipal', [FixturePrincipal])
& ([scriptblock]::Create([IO.File]::ReadAllText($Runner))) -Bundle $Bundle -WorkDir $WorkDir -Receipt $Receipt -CloneOverride $Candidate
"""

    def run_pwsh(self, root: Path, failing: set[str], arguments: list) -> tuple[list[str], str]:
        stubs = root / "bin"
        stubs.mkdir()
        calls = root / "calls.txt"
        effects = {"clone": "mkdir -p omp-ninfer", "rev-parse": f"echo {self.CANDIDATE}"}
        cases = "".join(f"  {name}) {'exit 128' if name in failing else effects.get(name, ':')} ;;\n"
                        for name in ("clone", "checkout", "rev-parse", "status"))
        (stubs / "git").write_text(f"#!/bin/sh\n[ \"$1\" = -C ] && shift 2\n"
                                   f"echo \"git $1\" >> '{calls}'\ncase \"$1\" in\n{cases}esac\n")
        (stubs / "py").write_text(f"#!/bin/sh\necho py >> '{calls}'\n")
        for stub in stubs.iterdir():
            stub.chmod(0o755)
        completed = subprocess.run(
            [shutil.which("pwsh"), "-NoProfile", "-File", *map(str, arguments)], cwd=root, capture_output=True,
            text=True, timeout=60, env=dict(os.environ, PATH=f"{stubs}{os.pathsep}{os.environ['PATH']}"))
        return (calls.read_text().splitlines() if calls.exists() else []), completed.stdout + completed.stderr

    def substitute_clone(self, failing: set[str], stale_clone: bool = False) -> tuple[list[str], list[str]]:
        clone = {step.slug: block.text for step, block in documented_route.lane_blocks(
            documented_route.DEFAULT_DOC, "rtx5090-windows-client")}["clone-and-verify"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "bundle"
            bundle.mkdir()
            steps = []
            for position, (slug, text) in enumerate((("clone-and-verify", clone), ("after", "$null = 1\n")), 1):
                name = f"{position:02d}-{slug}.ps1"
                (bundle / name).write_text(text, encoding="utf-8")
                steps.append({"position": position, "slug": slug, "file": name, "heading": "H", "index": 0,
                              "sha256": hashlib.sha256(text.encode()).hexdigest()})
            (bundle / "manifest.json").write_text(json.dumps({
                "lane": "rtx5090-windows-client", "document": "doc", "document_sha256": "0" * 64,
                "steps": steps}))
            work = root / "work"
            (work / "omp-ninfer" if stale_clone else work).mkdir(parents=True)
            host = root / "host.ps1"
            host.write_text(self.RUNNER_HOST)
            receipt = root / "receipt.json"
            ran, output = self.run_pwsh(root, failing, [
                host, ROOT / "scripts" / "hosts" / "run-documented-route.ps1", bundle, work, receipt, self.CANDIDATE])
            self.assertTrue(receipt.exists(), output)
            return [step["status"] for step in json.loads(receipt.read_text())["steps"]], ran

    def test_a_failed_candidate_clone_or_checkout_fails_the_substituted_step(self) -> None:
        """A failed clone or checkout left the runner in whatever directory existed: it verified
        that commit as the candidate and recorded the step as substituted."""
        self.assertEqual(self.substitute_clone(set()),
                         (["substituted", "passed"], ["git clone", "git checkout", "py"]))
        self.assertEqual(self.substitute_clone({"checkout"}),
                         (["failed", "skipped"], ["git clone", "git checkout"]))
        # An earlier attempt's clone already holds the name.
        self.assertEqual(self.substitute_clone({"clone"}, stale_clone=True), (["failed", "skipped"], ["git clone"]))

    def test_an_unreadable_candidate_clone_is_not_read_as_clean(self) -> None:
        """A failed `git status --porcelain` prints nothing, which read as a clean candidate clone."""
        for failing, expected in ((set(), ["git rev-parse", "git status", "py"]),
                                  ({"status"}, ["git rev-parse", "git status"])):
            with self.subTest(failing=sorted(failing)), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                workspace = root / "workspace"
                (workspace / "candidate").mkdir(parents=True)
                ran, output = self.run_pwsh(root, failing, [
                    ROOT / "scripts" / "hosts" / "accept-windows-client.ps1", "-Action", "Preflight",
                    "-Workspace", workspace, "-Release", "v0.14.0", "-Candidate", self.CANDIDATE,
                    "-ControlRoot", root / "control"])
                self.assertEqual(ran, expected, output)


if __name__ == "__main__":
    unittest.main()
