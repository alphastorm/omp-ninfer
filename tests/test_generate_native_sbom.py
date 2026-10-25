"""Dependency inventory is bound to build inputs, not inferred from filenames."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/generate_native_sbom.py"
SPEC = importlib.util.spec_from_file_location("generate_native_sbom", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
FIXTURE = json.loads((ROOT / "tests/fixtures/native-sbom.json").read_text(encoding="utf-8"))


class NativeSbomTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.package = self.root / "package"
        self.source = self.root / "source"
        self.fixture = deepcopy(FIXTURE)
        for directory, key in ((self.package, "package_files"), (self.source, "source_files")):
            for path, content in self.fixture[key].items():
                target = directory / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content.encode())
        self.inputs = {"manifest": self.source / "vcpkg.json", "lock": self.root / "vcpkg-resolved.json",
                       "cuda": self.root / "cuda-runtime.json", "third_party": self.root / "third-party.json"}
        self.write_inputs()

    def write_inputs(self) -> None:
        for key, path in self.inputs.items():
            path.write_text(json.dumps(self.fixture[key]), encoding="utf-8")

    def build(self) -> dict:
        self.write_inputs()
        return MODULE.build_sbom(package_dir=self.package, source_dir=self.source,
            source_commit=self.fixture["source_commit"], vcpkg_manifest=self.inputs["manifest"],
            vcpkg_lock=self.inputs["lock"], cuda_inventory=self.inputs["cuda"],
            third_party_inventory=self.inputs["third_party"])

    def test_schema_runtime_and_dependency_graph(self) -> None:
        document = self.build()
        self.assertEqual((document["bomFormat"], document["specVersion"], document["version"]),
                         ("CycloneDX", "1.5", 1))
        runtime = document["metadata"]["component"]
        self.assertEqual(runtime["name"], "ninfer-serve.exe")
        self.assertEqual(runtime["version"], FIXTURE["source_commit"])
        self.assertEqual(runtime["hashes"], [{"alg": "SHA-256", "content": hashlib.sha256(
            FIXTURE["package_files"]["bin/ninfer-serve.exe"].encode()).hexdigest()}])
        self.assertIn({"name": "ninfer:source_commit", "value": FIXTURE["source_commit"]}, runtime["properties"])
        components = {row["bom-ref"]: row for row in document["components"]}
        self.assertEqual(len(components), 7)  # Three vcpkg, two CUDA, two vendored.
        self.assertEqual(components["vcpkg:curl"]["version"], "8.14.1#2")
        self.assertEqual(components["vcpkg:curl"]["purl"], "pkg:vcpkg/curl@8.14.1%232")
        self.assertEqual(components["vcpkg:ffmpeg"]["licenses"], [{"expression": "LGPL-2.1-or-later"}])
        dll = components["cuda:bin/cudart64_13.dll"]
        self.assertEqual(dll["version"], FIXTURE["cuda"]["dlls"][0]["version"])
        self.assertEqual(dll["licenses"][0]["license"]["url"], FIXTURE["cuda"]["dlls"][0]["eula"])
        self.assertEqual(dll["hashes"][0]["content"], hashlib.sha256(
            FIXTURE["package_files"]["bin/cudart64_13.dll"].encode()).hexdigest())
        self.assertEqual(components["third_party:utf8proc"]["licenses"], [{"expression": "MIT AND Unicode-3.0"}])
        edges = {row["ref"]: row["dependsOn"] for row in document["dependencies"]}
        self.assertEqual(edges["vcpkg:curl"], ["vcpkg:zlib"])
        self.assertNotIn("vcpkg:zlib", edges[runtime["bom-ref"]])
        self.assertEqual({target for targets in edges.values() for target in targets}, set(components))
        self.assertEqual(set(edges), {*components, runtime["bom-ref"]})
        for path in self.inputs.values():
            self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), json.dumps(document["metadata"]["properties"]))
        self.assertNotIn(str(self.root), json.dumps(document))

    def test_input_order_does_not_change_component_or_graph_order(self) -> None:
        before = self.build()
        for key, field in (("lock", "packages"), ("cuda", "dlls"), ("third_party", "sources")):
            self.fixture[key][field].reverse()
        self.fixture["manifest"]["dependencies"].reverse()
        after = self.build()
        # Input-byte hashes deliberately change; the bill of materials and graph do not.
        self.assertEqual(before["components"], after["components"])
        self.assertEqual(before["dependencies"], after["dependencies"])

    def test_missing_unresolved_duplicate_or_unreachable_vcpkg_packages_are_refused(self) -> None:
        original = deepcopy(self.fixture["lock"])
        cases = []
        lock = deepcopy(original)
        lock["builtin-baseline"] = "0" * 40
        cases.append((lock, "baseline"))
        lock = deepcopy(original)
        lock["packages"].pop()
        cases.append((lock, "missing dependency: zlib"))
        lock = deepcopy(original)
        lock["packages"].append(deepcopy(lock["packages"][0]))
        cases.append((lock, "duplicate vcpkg"))
        for field in ("version", "license", "dependencies"):
            lock = deepcopy(original)
            lock["packages"][0].pop(field)
            cases.append((lock, field))
        lock = deepcopy(original)
        lock["packages"].append({"name": "unused", "version": "1", "license": "MIT", "dependencies": []})
        cases.append((lock, "outside the manifest"))
        for lock, message in cases:
            with self.subTest(message=message):
                self.fixture["lock"] = lock
                with self.assertRaisesRegex(ValueError, message):
                    self.build()

    def test_cuda_inventory_cannot_omit_dll_version_or_eula(self) -> None:
        original = deepcopy(self.fixture["cuda"])
        for field in ("version", "eula"):
            with self.subTest(field=field):
                self.fixture["cuda"] = deepcopy(original)
                self.fixture["cuda"]["dlls"][0].pop(field)
                with self.assertRaisesRegex(ValueError, "version|EULA"):
                    self.build()
        self.fixture["cuda"] = deepcopy(original)
        self.fixture["cuda"]["dlls"][0]["eula"] = "http://example.invalid/eula"
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            self.build()
        self.fixture["cuda"] = deepcopy(original)
        self.fixture["cuda"]["dlls"].pop()
        with self.assertRaisesRegex(ValueError, "missing packaged DLL"):
            self.build()
        self.fixture["cuda"] = deepcopy(original)
        self.fixture["cuda"]["dlls"].append(deepcopy(original["dlls"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate CUDA"):
            self.build()

    def test_vendored_inventory_cannot_omit_sources_versions_or_license_files(self) -> None:
        original = deepcopy(self.fixture["third_party"])
        for field in ("version", "license", "license_file"):
            with self.subTest(field=field):
                self.fixture["third_party"] = deepcopy(original)
                self.fixture["third_party"]["sources"][0].pop(field)
                with self.assertRaisesRegex(ValueError, "version|license"):
                    self.build()
        self.fixture["third_party"] = deepcopy(original)
        self.fixture["third_party"]["sources"].pop()
        with self.assertRaisesRegex(ValueError, "every source directory"):
            self.build()

    def test_absolute_or_parent_inventory_paths_are_refused(self) -> None:
        for path in ("../outside.dll", "bin/../../outside.dll", "/outside.dll", "C:/outside.dll", "bin\\outside.dll"):
            with self.subTest(path=path):
                self.fixture["cuda"]["dlls"][0]["path"] = path
                with self.assertRaisesRegex(ValueError, "normalized relative"):
                    self.build()

    def test_cli_is_deterministic_and_writes_nothing_on_bad_input(self) -> None:
        output = self.root / "native-dependencies.cdx.json"
        command = [sys.executable, str(SCRIPT), "--package-dir", str(self.package), "--source-dir", str(self.source),
            "--source-commit", FIXTURE["source_commit"], "--vcpkg-lock", str(self.inputs["lock"]),
            "--cuda-inventory", str(self.inputs["cuda"]), "--third-party-inventory", str(self.inputs["third_party"]),
            "--output", str(output)]
        first = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        document = output.read_bytes()
        second = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(document, output.read_bytes())
        self.assertEqual(first.stdout, second.stdout)
        output.unlink()
        self.fixture["lock"]["packages"][0].pop("license")
        self.write_inputs()
        failed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(failed.returncode, 1)
        self.assertIn("license", failed.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
