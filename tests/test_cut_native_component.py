"""Native component preflight validates real local archives without publishing or networking."""
from __future__ import annotations

from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CUTTER = ROOT / "scripts/hosts/cut-ninfer-4090-component.sh"
SBOM_FIXTURE = json.loads((ROOT / "tests/fixtures/native-sbom.json").read_text(encoding="utf-8"))
GENERATOR_SPEC = importlib.util.spec_from_file_location(
    "generate_native_sbom", ROOT / "scripts/generate_native_sbom.py")
assert GENERATOR_SPEC and GENERATOR_SPEC.loader
GENERATOR = importlib.util.module_from_spec(GENERATOR_SPEC)
GENERATOR_SPEC.loader.exec_module(GENERATOR)


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

    def assets(self, lane: str, unlisted_package_files: dict[str, str] | None = None) -> Path:
        spec = self.specs[lane]
        root = self.root / f"{lane}-assets"
        root.mkdir()
        stem = f"{spec['product_prefix']}-v{spec['release_version']}"
        package = f"{stem}-{spec['platform']}.tar.gz"
        source = f"{stem}-source.tar.gz"
        sbom = f"{stem}-{spec['platform']}.spdx.json"
        dependency = f"{stem}-{spec['platform']}.cdx.json"
        inner = f"{stem}-{spec['platform']}.SHA256SUMS"
        # A real payload archive whose dependency inventory is the generator's actual output for
        # that payload: the cut must accept exactly what generate_native_sbom.py emits.
        work = Path(tempfile.mkdtemp(dir=self.root))
        payload, tree = work / "payload", work / "source"
        for directory, key in ((payload, "package_files"), (tree, "source_files")):
            for path, content in SBOM_FIXTURE[key].items():
                (directory / path).parent.mkdir(parents=True, exist_ok=True)
                (directory / path).write_bytes(content.encode())
        inputs = {key: work / f"{key}.json" for key in ("manifest", "lock", "cuda", "third_party")}
        for key, path in inputs.items():
            path.write_text(json.dumps(SBOM_FIXTURE[key]))
        inventory = GENERATOR.build_sbom(
            package_dir=payload, source_dir=tree, source_commit=self.commit,
            vcpkg_manifest=inputs["manifest"], vcpkg_lock=inputs["lock"],
            cuda_inventory=inputs["cuda"], third_party_inventory=inputs["third_party"])
        (root / dependency).write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
        # Files added after generation model a package that drifted from its inventory.
        for path, content in (unlisted_package_files or {}).items():
            (payload / path).write_bytes(content.encode())
        with tarfile.open(root / package, "w:gz") as bundle:
            bundle.add(payload, arcname=package.removesuffix(".tar.gz"))
        (root / sbom).write_text('{}\n')
        server_sha = digest((payload / "bin/ninfer-serve.exe").read_bytes())
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
                        "checksums": {"entries": 10},
                        "binaries": {"server_sha256": server_sha},
                        "dependency_sbom": {"name": dependency, "format": "CycloneDX-1.5",
                                            "sha256": digest((root / dependency).read_bytes())},
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

    def test_both_lanes_close_the_eleven_file_set_without_creating_a_tag(self) -> None:
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

    def test_dependency_inventory_name_receipt_format_and_runtime_identity_are_bound(self) -> None:
        for mutation in ("missing", "renamed", "receipt", "spdx", "source", "binary"):
            with self.subTest(mutation=mutation):
                assets = self.assets("rtx4090")
                receipt_path = assets / "package-build-receipt.json"
                receipt = json.loads(receipt_path.read_text())
                dependency_path = assets / receipt["dependency_sbom"]["name"]
                if mutation == "missing":
                    dependency_path.unlink()
                elif mutation == "renamed":
                    dependency_path.rename(assets / "native-dependencies.cdx.json")
                elif mutation == "receipt":
                    receipt["dependency_sbom"]["sha256"] = "0" * 64
                else:
                    inventory = json.loads(dependency_path.read_text())
                    if mutation == "spdx":
                        inventory = {"spdxVersion": "SPDX-2.3"}
                    elif mutation == "source":
                        inventory["metadata"]["component"]["version"] = "0" * 40
                    else:
                        inventory["metadata"]["component"]["hashes"][0]["content"] = "0" * 64
                    dependency_path.write_text(json.dumps(inventory))
                    receipt["dependency_sbom"]["sha256"] = digest(dependency_path.read_bytes())
                receipt_path.write_text(json.dumps(receipt))
                self.sums(assets)
                result = self.run_cut(self.command("rtx4090", assets))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("distribution set" if mutation in ("missing", "renamed")
                              else "SBOM", result.stderr)
                shutil.rmtree(assets)

    def test_identity_only_or_open_dependency_inventory_is_refused(self) -> None:
        refusals = {"identity-only": "dependency SBOM lists no components",
                    "no-graph": "dependency SBOM dependency graph",
                    "dangling-edge": "dependency SBOM dependency graph",
                    "unreachable": "unreachable from the server",
                    "duplicate-ref": "unique bom-refs",
                    "unmapped-dll": "does not map packaged DLL bin/libcurl.dll",
                    "rehashed-dll": "does not hash packaged DLL bin/zlib1.dll",
                    "phantom-dll": "maps bin/zlib-ng.dll, which the package does not ship",
                    "unlisted-dll": "does not map packaged DLL bin/brotlicommon.dll"}
        for mutation, message in refusals.items():
            with self.subTest(mutation=mutation):
                assets = self.assets("rtx4090", {"bin/brotlicommon.dll": "unlisted transitive DLL\n"}
                                     if mutation == "unlisted-dll" else None)
                receipt_path = assets / "package-build-receipt.json"
                receipt = json.loads(receipt_path.read_text())
                dependency_path = assets / receipt["dependency_sbom"]["name"]
                inventory = json.loads(dependency_path.read_text())
                server = inventory["metadata"]["component"]["bom-ref"]
                edges = {row["ref"]: row["dependsOn"] for row in inventory["dependencies"]}
                files = {row["name"]: row.get("components", []) for row in inventory["components"]
                         if row["bom-ref"].startswith("vcpkg:")}
                if mutation == "identity-only":
                    inventory = {key: inventory[key] for key in
                                 ("$schema", "bomFormat", "specVersion", "version", "metadata")}
                elif mutation == "no-graph":
                    del inventory["dependencies"]
                elif mutation == "dangling-edge":
                    edges[server].append("vcpkg:absent")
                elif mutation == "unreachable":
                    edges[server].remove("third_party:nlohmann")
                elif mutation == "duplicate-ref":
                    inventory["components"].append(deepcopy(inventory["components"][0]))
                elif mutation == "unmapped-dll":
                    files["curl"].clear()
                elif mutation == "rehashed-dll":
                    files["zlib"][0]["hashes"][0]["content"] = "0" * 64
                elif mutation == "phantom-dll":
                    phantom = deepcopy(files["zlib"][0])
                    phantom.update({"bom-ref": "vcpkg:zlib:bin/zlib-ng.dll", "name": "zlib-ng.dll",
                                    "properties": [{"name": "ninfer:package_path", "value": "bin/zlib-ng.dll"}]})
                    files["zlib"].append(phantom)
                dependency_path.write_text(json.dumps(inventory))
                receipt["dependency_sbom"]["sha256"] = digest(dependency_path.read_bytes())
                receipt_path.write_text(json.dumps(receipt))
                self.sums(assets)
                result = self.run_cut(self.command("rtx4090", assets))
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(message, result.stderr)
                self.assertNotIn("preflight ok", result.stdout)
                shutil.rmtree(assets)

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
            with self.subTest(lane=lane, flags="--dry-run --publish"):
                result = self.run_cut(self.command(lane, assets) + ["--lane", lane, "--dry-run", "--publish"])
                self.assertEqual(result.returncode, 2)
                self.assertIn("choose --dry-run or --publish", result.stderr)
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
