"""Native component preflight validates real local archives without publishing or networking."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CUTTER = ROOT / "scripts/hosts/cut-ninfer-4090-component.sh"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class NativeCutterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runtime = self.root / "runtime"
        self.runtime.mkdir()
        self.git = shutil.which("git")
        self.git_run("init", "-q")
        self.git_run("config", "user.name", "Native cutter fixture")
        self.git_run("config", "user.email", "fixture@example.invalid")
        self.specs = {}
        for lane, version in (("rtx3090", "0.6.2"), ("rtx4090", "0.6.2")):
            spec = {"lane": lane, "release_version": version + "-beta.1",
                    "release_id": f"qwen38-{lane[3:]}-native-v{version}-beta.1",
                    "deployment_profile": f"qwen38-{lane[3:]}-native-v{version}-beta.1",
                    "build_profile": f"native-v{version}-beta.1-{lane}",
                    "product_prefix": f"ninfer-{lane}-native",
                    "platform": f"windows-x86_64-cuda13.3-{lane}"}
            path = self.runtime / "packaging/windows/lanes" / lane / "release-spec.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(spec))
            self.specs[lane] = spec
        self.git_run("add", ".")
        self.git_run("commit", "-qm", "fixture")
        self.commit = self.git_run("rev-parse", "HEAD").strip()
        self.git_run("update-ref", "refs/remotes/origin/main", self.commit)
        self.remote = self.root / "remote.git"
        subprocess.run([self.git, "init", "--bare", "-q", str(self.remote)], check=True)
        self.git_run("remote", "add", "origin", str(self.remote))
        self.notes = self.root / "notes.txt"
        self.notes.write_text("Fixture component notes\n")
        tools = self.root / "bin"
        tools.mkdir()
        # Redirect only public tag discovery. All local archive/ref operations and the actual
        # push --dry-run use Git itself against a disposable local bare origin.
        (tools / "git").write_text(
            '#!/bin/sh\nif [ "$1" = ls-remote ]; then shift; shift; shift; '
            'exec "$REAL_GIT" ls-remote --tags "$LOCAL_ORIGIN" "$@"; fi\n'
            'exec "$REAL_GIT" "$@"\n')
        (tools / "gh").write_text(
            '#!/bin/sh\ncase "$1 $2" in\n'
            ' "auth status") exit 0;;\n "api repos/alphastorm/ninfer") echo true;;\n'
            ' "release view") exit 1;;\n *) echo "unexpected GitHub operation" >&2; exit 99;;\nesac\n')
        for path in tools.iterdir():
            path.chmod(0o755)
        self.env = {**os.environ, "PATH": f"{tools}:{os.environ['PATH']}",
                    "REAL_GIT": self.git, "LOCAL_ORIGIN": str(self.remote),
                    "NINFER_RUNTIME_DIR": str(self.runtime)}

    def git_run(self, *args: str) -> str:
        return subprocess.run([self.git, "-C", str(self.runtime), *args], check=True,
                              capture_output=True, text=True).stdout

    def assets(self, lane: str) -> Path:
        spec = self.specs[lane]
        root = self.root / f"{lane}-assets"
        root.mkdir()
        stem = f"{spec['product_prefix']}-v{spec['release_version']}"
        package = f"{stem}-{spec['platform']}.tar.gz"
        source = f"{stem}-source.tar.gz"
        sbom = f"{stem}-{spec['platform']}.spdx.json"
        inner = f"{stem}-{spec['platform']}.SHA256SUMS"
        (root / package).write_bytes(b"native package fixture\n")
        (root / sbom).write_text('{}\n')
        archive = subprocess.run([self.git, "-C", str(self.runtime), "-c", "core.autocrlf=false",
                                  "-c", "core.eol=lf", "archive", "--format=tar",
                                  "--prefix=runtime-source/", self.commit],
                                 check=True, capture_output=True).stdout
        (root / source).write_bytes(gzip.compress(archive, mtime=0))
        support = {"Install-Release.ps1": "installer_sha256", "Control-Release.ps1": "controller_sha256",
                   "Control-GpuOwner.ps1": "gpu_owner_controller_sha256",
                   "Protect-StateRoot.ps1": "state_protection_sha256"}
        for name in support:
            (root / name).write_text("# " + name + "\n")
        (root / inner).write_text("".join(f"{digest((root / name).read_bytes())}  {name}\n"
                                        for name in (package, source, sbom)))
        receipt = {key: spec[key] for key in
                   ("lane", "release_id", "release_version", "deployment_profile", "build_profile")}
        receipt.update({"patch_stack_sha": self.commit, "runtime_source_sha": self.commit,
                        "package_source_sha": self.commit, "secret_values_recorded": 0,
                        "package": {"filename": package, "sha256": digest((root / package).read_bytes()),
                                    "bytes": (root / package).stat().st_size},
                        "checksums": {"entries": 9},
                        "support_assets": {key: digest((root / name).read_bytes()) for name, key in support.items()}})
        (root / "package-build-receipt.json").write_text(json.dumps(receipt))
        self.sums(root)
        return root

    def sums(self, root: Path) -> None:
        (root / "SHA256SUMS").write_text("".join(
            f"{digest(p.read_bytes())}  {p.name}\n" for p in sorted(root.iterdir()) if p.name != "SHA256SUMS"))

    def command(self, lane: str, assets: Path) -> list[str]:
        return ["bash", str(CUTTER), "--version", "v" + self.specs[lane]["release_version"].split("-")[0],
                "--commit", self.commit, "--assets", str(assets), "--checksums-sha",
                digest((assets / "SHA256SUMS").read_bytes()), "--notes-file", str(self.notes)]

    def run_cut(self, command: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(command, env=self.env, cwd=self.root, capture_output=True, text=True)

    def test_both_lanes_close_the_ten_file_set_without_creating_a_tag(self) -> None:
        for lane in self.specs:
            with self.subTest(lane=lane):
                assets = self.assets(lane)
                command = self.command(lane, assets)
                result = self.run_cut(command + ["--lane", lane, "--dry-run"])
                self.assertEqual(result.returncode, 0, result.stderr)
                receipt = json.loads((assets / "package-build-receipt.json").read_text())
                package = receipt["package"]
                tag = f"v{self.specs[lane]['release_version'].split('-')[0]}-qwen38-{lane[3:]}-beta.1"
                self.assertEqual(result.stdout,
                    f"assets verified: {package['filename']} {package['sha256']}; source runtime-source/ is {self.commit}\n"
                    f"preflight ok: {tag} at {self.commit}\ndry run: no tag, release, or upload was created\n")
                refs = subprocess.run([self.git, "--git-dir", str(self.remote), "show-ref", "--tags"],
                                      capture_output=True, text=True)
                self.assertEqual(refs.stdout, "")
                if lane == "rtx4090":
                    self.assertEqual(self.run_cut(command).stdout, result.stdout)

    def test_forgotten_lane_extra_asset_and_receipt_drift_are_refused(self) -> None:
        assets = self.assets("rtx3090")
        result = self.run_cut(self.command("rtx3090", assets))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact closed distribution set", result.stderr)
        (assets / "unlisted.txt").write_text("not a component asset")
        self.sums(assets)
        result = self.run_cut(self.command("rtx3090", assets) + ["--lane", "rtx3090"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact closed distribution set", result.stderr)
        (assets / "unlisted.txt").unlink()
        receipt_path = assets / "package-build-receipt.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["lane"] = "rtx4090"
        receipt_path.write_text(json.dumps(receipt))
        self.sums(assets)
        result = self.run_cut(self.command("rtx3090", assets) + ["--lane", "rtx3090"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("receipt lane", result.stderr)

    def test_arguments_fail_before_any_external_operation(self) -> None:
        for lane in self.specs:
            assets = self.assets(lane)
            for flag, value, message in (("--lane", "rtx5090", "--lane must be"),
                                          ("--version", "v0.6.2-beta.1", "--version must be"),
                                          ("--commit", "short", "--commit must be"),
                                          ("--beta", "0", "--beta must be")):
                with self.subTest(lane=lane, flag=flag):
                    result = self.run_cut(self.command(lane, assets) + ["--lane", lane, flag, value])
                    self.assertEqual(result.returncode, 2)
                    self.assertIn(message, result.stderr)
        result = self.run_cut(["bash", str(CUTTER), "--lane"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("--lane requires a value", result.stderr)

    @unittest.skipIf(os.name == "nt", "POSIX fixture maps the Windows build path under its temporary root")
    def test_3090_default_build_directory_is_selected_from_the_source_head(self) -> None:
        assets = self.assets("rtx3090")
        command = self.command("rtx3090", assets)
        explicit = self.run_cut(command + ["--lane", "rtx3090"])
        target = self.root / "C:" / "b" / f"ninfer-rtx3090-{self.commit[:8]}" / "package-a"
        target.parent.mkdir(parents=True)
        assets.rename(target)
        position = command.index("--assets")
        del command[position:position + 2]
        implicit = self.run_cut(command + ["--lane", "rtx3090"])
        self.assertEqual(implicit.returncode, 0, implicit.stderr)
        self.assertEqual(implicit.stdout, explicit.stdout)



if __name__ == "__main__":
    unittest.main()
