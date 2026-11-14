"""Opt-in replay of the real re-cut candidate with unmodified release tools."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from test_aggregate_qualification import HISTORY, load

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from release_io import atomic_write, atomic_write_json, git
from release_plan import initial_plan


class PrivateRecutReplayTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("OMP_NINFER_PRIVATE_FIXTURES"),
                         "private fixture locations are not configured")
    def test_real_recut_candidate(self):
        locations = load(Path(os.environ["OMP_NINFER_PRIVATE_FIXTURES"]).expanduser())["v0.19.0"]
        commits = locations["commits"]
        before, staged, published = HISTORY.resolve_commits(
            commits["runtime_stage"] + "^", commits["runtime_stage"], "v0.19.0")
        environment = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                       "GIT_AUTHOR_NAME": "Release replay", "GIT_COMMITTER_NAME": "Release replay",
                       "GIT_AUTHOR_EMAIL": "release@example.invalid",
                       "GIT_COMMITTER_EMAIL": "release@example.invalid", "PYTHONIOENCODING": "utf-8"}
        environment.pop("PYTHONPATH", None)
        with tempfile.TemporaryDirectory(prefix="release-recut-") as temporary:
            root = Path(temporary) / "product"
            private = Path(temporary) / "inputs"
            private.mkdir()
            subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", "--no-checkout",
                            str(ROOT), str(root)], check=True, capture_output=True, env=environment)
            git(root, "config", "commit.gpgsign", "false")
            git(root, "config", "user.name", "Release replay")
            git(root, "config", "user.email", "release@example.invalid")
            git(root, "config", "core.autocrlf", "false")
            git(root, "checkout", "--quiet", "--detach", before)
            git(root, "remote", "remove", "origin")
            shutil.copytree(ROOT / "scripts", root / "scripts", dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
            atomic_write(root / ".gitignore", (ROOT / ".gitignore").read_bytes())
            git(root, "add", "scripts", ".gitignore")
            git(root, "commit", "--quiet", "-m", "test(release): install current replay tools")

            def historical(commit, path):
                return subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT,
                                      check=True, capture_output=True, env=environment).stdout

            base = "releases/v0.19.0/"
            manifest = json.loads(historical(published, base + "manifest.json"))
            runtime = manifest["components"]["ninfer"]
            native = next(row for row in manifest["components"]["ninfer_variants"]
                          if row["id"] == "rtx3090-windows-native")
            bundle_root = Path(locations["aggregate"]["bundle_root"]).expanduser()
            bundle = bundle_root / "rtx3090"
            reference = load(bundle / "bundle.json")
            decisions = bundle / Path(next(edge["path"] for edge in reference["inputs"]
                                           if edge["role"] == "decisions")).parent
            plan = initial_plan(root, "v0.19.0", recut=[
                f"rtx5090-container={runtime['release_tag']}@{runtime['source_commit']}",
                f"{native['id']}={native['release_tag']}@{native['source_commit']}",
            ], client_tag=manifest["components"]["omp"]["upstream_tag"],
                decisions=[f"{path.stem}:{'waiver' if 'waiver' in path.stem else 'scope'}:"
                           + __import__("hashlib").sha256(path.read_bytes()).hexdigest()
                           for path in sorted(decisions.glob("*.json"))])
            plan["limitations"] = ["Only the documented deployment topology is supported."]
            atomic_write_json(root / base / "plan.json", plan)

            def command(*args):
                return subprocess.run([sys.executable, *map(str, args)], cwd=root,
                                      env=environment, capture_output=True, text=True, encoding="utf-8")

            result = command("scripts/release.py", "plan", "commit", "--release", "v0.19.0")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for name, source in (("rtx5090.json", "qualification/rtx5090.json"),
                                 ("runtime-publication.json", "qualification/runtime-publication.json"),
                                 ("client-components.json", "qualification/client-components.json"),
                                 ("notes.md", "NINFER_RELEASE_NOTES.md")):
                atomic_write(private / name, historical(staged, base + source))
            retained = Path(locations["aggregate"]["live_inputs"]).expanduser().parents[2]
            source_name = runtime["source_archive_url"].rsplit("/", 1)[-1]
            matches = list(retained.rglob(source_name))
            self.assertEqual(len(matches), 1, f"expected one retained source archive: {source_name}")
            archive = matches[0]
            sums = archive.parent / (runtime["binary_archive_url"].rsplit("/", 1)[-1].removesuffix(".tar.gz")
                                     + ".SHA256SUMS")
            for path in (archive, sums):
                shutil.copyfile(path, private / path.name)
            stage_input = {
                "source_tag": runtime["source_archive_url"].split("/")[-2],
                "binary_sha": runtime["server_binary_sha256"], "archive_sha": runtime["binary_archive_sha256"],
                "source_archive_sha": runtime["source_archive_sha256"], "sbom_sha": runtime["sbom_sha256"],
                "source_archive": source_name, "checksums": sums.name,
                "archive_name": runtime["binary_archive_url"].rsplit("/", 1)[-1],
                "image_digest": runtime["oci_manifest_digest"],
                "runtime_receipt_release": runtime["runtime_receipt_release"],
                "upstream_commit": runtime["upstream_commit"],
            }
            atomic_write_json(private / "stage-input.json", stage_input)
            # The predecessor linked an unbound client review. Preserve its label, not its link;
            # this is an authored guide input, not an acceptance or qualification override.
            guide = root / "docs/QUICKSTART.md"
            text = guide.read_text(encoding="utf-8")
            text = text.replace(
                "[18.18.6→18.18.7 review](measurements/2026-11-11-omp-18187-client-upgrade-review.json)",
                "18.18.6→18.18.7 review")
            atomic_write(guide, text)
            result = command(
                "scripts/release.py", "candidate", "--release", "v0.19.0", "--no-suite",
                "--stage-input", private / "stage-input.json", "--lane-receipt", f"rtx5090={private / 'rtx5090.json'}",
                "--runtime-publication", private / "runtime-publication.json",
                "--client-component", private / "client-components.json",
                "--bundle", f"rtx3090={bundle}",
                "--native-publication", f"rtx3090={bundle_root / 'native-publication-rtx3090.json'}",
                "--notes", private / "notes.md", "--as-of", "2026-11-13")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = command("scripts/verify_release.py", "--release", "v0.19.0", "--lint-ready", "--check-pins")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(load(root / base / "manifest.json")["status"], "candidate")
            self.assertEqual((root / base / "qualification/runtime-publication.json").read_bytes(),
                             (private / "runtime-publication.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
