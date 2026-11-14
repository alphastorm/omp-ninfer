"""Hermetic closure and identity tests for the chain-to-product boundary."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Explicit immutable evidence fixtures, never the working tree's current authority.
FIXTURE_RELEASE = "v0.19.0"
FIXTURE_PREDECESSOR = "v0.18.0"
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("qualification_bundle", ROOT / "scripts/qualification_bundle.py")
assert SPEC is not None and SPEC.loader is not None
BUNDLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUNDLE)
from release_io import atomic_write, atomic_write_json


def load(path):
    return json.loads(path.read_bytes())


def hashes(directory):
    return {path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*")) if path.is_file() and path != directory / "SHA256SUMS"}


def seal_directory(directory):
    atomic_write(directory / "SHA256SUMS", "".join(f"{digest}  {name}\n" for name, digest in hashes(directory).items()))


class SyntheticBundle:
    """Real public policy metadata, synthetic package bytes and isolated authorities."""

    release = FIXTURE_RELEASE
    lane = "rtx3090"

    def __init__(self, root):
        self.root = root
        self.directory = root / "bundle"
        self.directory.mkdir()
        evidence = ROOT / "releases" / FIXTURE_RELEASE
        self.manifest = load(evidence / "manifest.json")
        self.manifest["status"] = "draft"
        self.row = next(row for row in self.manifest["components"]["ninfer_variants"] if row["id"] == "rtx3090-windows-native")
        self.row["package_sha256"] = BUNDLE.sha(b"synthetic archive")
        self.row["package_bytes"] = len(b"synthetic archive")
        self.assets = self.directory / "assets"
        self.assets.mkdir()
        atomic_write(self.assets / self.row["package_name"], b"synthetic archive")
        receipt = {
            "artifact_type": "ninfer_windows_package_build_receipt", "lane": self.lane,
            "package": {"filename": self.row["package_name"], "sha256": self.row["package_sha256"],
                        "bytes": self.row["package_bytes"]},
            "patch_stack_sha": self.row["source_commit"], "runtime_source_sha": self.row["source_commit"],
            "package_source_sha": self.row["source_commit"], "build_profile": self.row["build_profile"],
            "binaries": {"server_sha256": self.row["server_binary_sha256"]},
            "config_sha256": self.row["configuration_sha256"], "model_sha256": self.row["model_artifact_sha256"]}
        atomic_write_json(self.assets / "package-build-receipt.json", receipt)
        seal_directory(self.assets)
        self.row["checksums_sha256"] = BUNDLE.sha((self.assets / "SHA256SUMS").read_bytes())
        native = load(evidence / "qualification/rtx3090.json")
        native["package"]["sha256"] = self.row["package_sha256"]
        fit = load(evidence / "qualification/rtx3090-windows-native.fit.json")
        fit["identity"]["package_sha256"] = self.row["package_sha256"]
        for name, value in {
            "rtx3090.json": native, "fit.json": fit, "speed.json": {"status": "PASS"},
            "upgrade.json": {"status": "passed"}, "agent-parity.json": {"passed": True},
            "identity-proof.json": {},
        }.items():
            atomic_write_json(self.directory / name, value)
        for name in ("server-config.json", "release-spec.json"):
            atomic_write(self.directory / name, (evidence / "profiles/rtx3090" / name).read_bytes())
        tooling = self.directory / "tooling"
        tooling.mkdir()
        for name in ("compose_native_qualification.py", "speed_gate.py", "verify_release.py"):
            atomic_write(tooling / name, b"pass\n")
        seal_directory(tooling)
        self.proof = {
            "status": "passed", "lead_staging_required": True, "publication_authorized": False,
            "input_sha256": {}, "consumer_sha256": {name: digest for name, digest in hashes(tooling).items()},
            "files": {}}
        self.reference = {
            "artifact_type": "omp_ninfer_qualification_bundle", "schema_version": 1,
            "release": self.release, "lane": self.lane, "inputs": []}
        self.declare("assets", self.assets / "SHA256SUMS")
        self.declare("tooling", tooling / "SHA256SUMS")
        self.reseal()
        previous = load(ROOT / "releases" / FIXTURE_PREDECESSOR / "manifest.json")
        atomic_write_json(root / "releases" / FIXTURE_PREDECESSOR / "manifest.json", previous)
        self.plan = {
            "artifact_type": "omp_ninfer_release_plan", "schema_version": 1, "release": self.release,
            "predecessor": FIXTURE_PREDECESSOR,
            "components": [
                {"id": "rtx5090-container", "disposition": "recut",
                 **{key: self.manifest["components"]["ninfer"][key] for key in ("release_tag", "source_commit")}},
                *[{"id": row["id"], "disposition": "recut" if row["id"].startswith("rtx3090") else "carried",
                   **{key: row[key] for key in ("release_tag", "source_commit")}}
                  for row in self.manifest["components"]["ninfer_variants"]]],
            "decisions": []}
        decision_path = f"releases/{self.release}/qualification/native-speed-decision.json"
        decision = {"artifact_type": "omp_ninfer_founder_gate_decision", "schema_version": 1, "release": self.release}
        atomic_write_json(root / decision_path, decision)
        digest = BUNDLE.sha((root / decision_path).read_bytes())
        self.qualification = {"observed_gates": {"native_speed_decision": {"repository_path": decision_path, "sha256": digest}}}
        # A qualification decision; cut authorizations (kind component-cut) are not bound here.
        self.plan["decisions"] = [{"id": "native-speed-decision", "kind": "scope", "sha256": digest}]

    def declare(self, role, path):
        self.reference["inputs"].append({"role": role, "path": path.relative_to(self.directory).as_posix(),
                                         "sha256": BUNDLE.sha(path.read_bytes()), "bytes": path.stat().st_size})

    def reseal(self):
        names = {*BUNDLE.PROJECTION_FILES, self.lane + ".json", "identity-proof.json"}
        self.proof["files"] = {name: BUNDLE.sha((self.directory / name).read_bytes()) for name in sorted(names)}
        atomic_write_json(self.directory / "projection-proof.json", self.proof)
        entries = {**self.proof["files"], "projection-proof.json": BUNDLE.sha((self.directory / "projection-proof.json").read_bytes())}
        atomic_write(self.directory / "SHA256SUMS", "".join(f"{digest}  {name}\n" for name, digest in sorted(entries.items())))
        atomic_write_json(self.directory / "bundle.json", self.reference)

    def change_projection(self, name, change):
        value = load(self.directory / name)
        change(value)
        atomic_write_json(self.directory / name, value)
        self.reseal()

    def reseal_assets(self):
        seal_directory(self.assets)
        self.row["checksums_sha256"] = BUNDLE.sha((self.assets / "SHA256SUMS").read_bytes())
        edge = next(item for item in self.reference["inputs"] if item["role"] == "assets")
        edge.update(sha256=self.row["checksums_sha256"], bytes=(self.assets / "SHA256SUMS").stat().st_size)
        self.reseal()

    def open(self):
        return BUNDLE.Bundle(self.directory, self.lane, self.row, BUNDLE.Inputs(), self.release)


class QualificationBundleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.fixture = SyntheticBundle(Path(temporary.name))

    def test_accepts_closed_projection_and_asset_set(self):
        bundle = self.fixture.open()
        self.assertEqual(bundle.lane, "rtx3090")
        self.assertEqual(set(bundle.asset_hashes), {"package-build-receipt.json", bundle.row["package_name"]})
        bundle.inputs.check()

    def test_projection_closure_refuses_missing_extra_and_changed_bytes(self):
        for mutation in ("missing", "extra", "changed"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                fixture = SyntheticBundle(Path(temporary))
                if mutation == "missing":
                    (fixture.directory / "fit.json").unlink()
                elif mutation == "extra":
                    atomic_write(fixture.directory / "unexpected.json", "{}")
                else:
                    atomic_write(fixture.directory / "fit.json", "{}")
                with self.assertRaises(BUNDLE.BundleError):
                    fixture.open()

    def test_projection_file_set_and_admission_are_exact(self):
        for mutation in ("omit", "both", "additional"):
            with self.subTest(mutation=mutation):
                value = deepcopy(self.fixture.proof)
                if mutation == "omit":
                    value["files"].pop("fit.json")
                elif mutation == "both":
                    value["files"]["quality-screen.json"] = "a" * 64
                else:
                    value["files"]["unknown.json"] = "b" * 64
                atomic_write_json(self.fixture.directory / "projection-proof.json", value)
                with self.assertRaisesRegex(BUNDLE.BundleError, "projection-proof.json#/files"):
                    self.fixture.open()

    def test_checksums_must_bind_the_proof_and_every_projection(self):
        path = self.fixture.directory / "SHA256SUMS"
        for data in (b"", b"a" * 64 + b"  fit.json\n", path.read_bytes() + path.read_bytes()):
            atomic_write(path, data)
            with self.assertRaisesRegex(BUNDLE.BundleError, "SHA256SUMS"):
                self.fixture.open()

    def test_asset_set_is_closed_and_hashed(self):
        atomic_write(self.fixture.assets / "extra", b"extra")
        with self.assertRaisesRegex(BUNDLE.BundleError, "extra"):
            self.fixture.open()

    def test_unlisted_projection_raw_input_refuses(self):
        self.fixture.proof["input_sha256"] = {"retained-evidence": "f" * 64}
        self.fixture.reseal()
        with self.assertRaisesRegex(BUNDLE.BundleError, "input_sha256"):
            self.fixture.open()

    def test_tooling_consumer_hash_must_match(self):
        self.fixture.proof["consumer_sha256"]["speed_gate.py"] = "a" * 64
        self.fixture.reseal()
        with self.assertRaisesRegex(BUNDLE.BundleError, "SHA-256 mismatch"):
            self.fixture.open()

    def test_manifest_roles_refuse_duplicate_paths_sizes_and_digests(self):
        for change, message in (
            (lambda edge: edge.update(path="../outside"), "path"),
            (lambda edge: edge.update(path="/absolute"), "path"),
            (lambda edge: edge.update(bytes=1), "size"),
            (lambda edge: edge.update(sha256="a" * 64), "SHA-256"),
        ):
            with self.subTest(message=message):
                reference = deepcopy(self.fixture.reference)
                change(reference["inputs"][0])
                atomic_write_json(self.fixture.directory / "bundle.json", reference)
                with self.assertRaisesRegex(BUNDLE.BundleError, message):
                    self.fixture.open()

    def test_duplicate_role_and_overlapping_binding_refuse(self):
        reference = deepcopy(self.fixture.reference)
        reference["inputs"].append(deepcopy(reference["inputs"][0]))
        atomic_write_json(self.fixture.directory / "bundle.json", reference)
        with self.assertRaisesRegex(BUNDLE.BundleError, "/role"):
            self.fixture.open()
        reference["inputs"][-1]["role"] = "other"
        atomic_write_json(self.fixture.directory / "bundle.json", reference)
        with self.assertRaisesRegex(BUNDLE.BundleError, "overlap"):
            self.fixture.open()

    def test_external_package_requires_explicit_matching_role(self):
        package = self.fixture.assets / self.fixture.row["package_name"]
        external = self.fixture.root / "external-package.tar.gz"
        atomic_write(external, package.read_bytes())
        package.unlink()
        role = self.fixture.lane + "-package"
        self.fixture.reference["inputs"].append({
            "role": role, "external": True, "name": self.fixture.row["package_name"],
            "sha256": self.fixture.row["package_sha256"], "bytes": self.fixture.row["package_bytes"]})
        self.fixture.reseal()
        with self.assertRaisesRegex(BUNDLE.BundleError, "external package role not supplied"):
            self.fixture.open()
        bundle = BUNDLE.Bundle(self.fixture.directory, self.fixture.lane, self.fixture.row,
                               BUNDLE.Inputs(), self.fixture.release, {role: external})
        self.assertEqual(bundle.asset_paths[self.fixture.row["package_name"]], external)
        atomic_write(external, b"incorrect")
        with self.assertRaisesRegex(BUNDLE.BundleError, "SHA-256 mismatch|wrong size"):
            BUNDLE.Bundle(self.fixture.directory, self.fixture.lane, self.fixture.row,
                          BUNDLE.Inputs(), self.fixture.release, {role: external})

    def test_symlink_refuses(self):
        path = self.fixture.directory / "alias"
        try:
            path.symlink_to(self.fixture.directory / "fit.json")
        except OSError as error:
            self.skipTest(f"symlinks unavailable: {error}")
        with self.assertRaisesRegex(BUNDLE.BundleError, "symlink"):
            self.fixture.open()

    def test_each_native_identity_field_is_bound_to_manifest(self):
        for name, alias in (
            ("server_binary_sha256", "binary_sha256"), ("source_commit", "source_commit"),
            ("configuration_sha256", "configuration_sha256"), ("model_artifact_sha256", "model_artifact_sha256"),
            ("build_profile", "build_profile"),
        ):
            with self.subTest(field=name), tempfile.TemporaryDirectory() as temporary:
                fixture = SyntheticBundle(Path(temporary))
                fixture.change_projection("rtx3090.json", lambda value: value["identity"].update({alias: "incorrect"}))
                with self.assertRaisesRegex(BUNDLE.BundleError, "/identity/" + alias):
                    fixture.open()

    def test_package_and_fit_identities_refuse(self):
        self.fixture.change_projection("rtx3090.json", lambda value: value["package"].update(sha256="a" * 64))
        with self.assertRaisesRegex(BUNDLE.BundleError, "/package/sha256"):
            self.fixture.open()

    def test_every_fit_identity_and_dirty_or_failed_native_refuse(self):
        for key in BUNDLE.IDENTITY_FIELDS:
            with self.subTest(field=key), tempfile.TemporaryDirectory() as temporary:
                fixture = SyntheticBundle(Path(temporary))
                fixture.change_projection("fit.json", lambda value: value["identity"].update({key: "a" * 64}))
                with self.assertRaisesRegex(BUNDLE.BundleError, "fit.json#/identity"):
                    fixture.open()
        for change, pointer in (
            (lambda value: value["identity"].update(source_dirty=True), "source_dirty"),
            (lambda value: value.update(status="failed"), "/status"),
        ):
            with self.subTest(pointer=pointer), tempfile.TemporaryDirectory() as temporary:
                fixture = SyntheticBundle(Path(temporary))
                fixture.change_projection("rtx3090.json", change)
                with self.assertRaisesRegex(BUNDLE.BundleError, pointer):
                    fixture.open()

    def test_package_receipt_identity_refusals(self):
        for key in ("patch_stack_sha", "runtime_source_sha", "package_source_sha",
                    "config_sha256", "model_sha256", "build_profile"):
            with self.subTest(field=key), tempfile.TemporaryDirectory() as temporary:
                fixture = SyntheticBundle(Path(temporary))
                path = fixture.assets / "package-build-receipt.json"
                value = load(path)
                value[key] = "incorrect"
                atomic_write_json(path, value)
                fixture.reseal_assets()
                with self.assertRaisesRegex(BUNDLE.BundleError, "/" + key):
                    fixture.open()
        value = load(self.fixture.assets / "package-build-receipt.json")
        value["binaries"]["server_sha256"] = "a" * 64
        atomic_write_json(self.fixture.assets / "package-build-receipt.json", value)
        self.fixture.reseal_assets()
        with self.assertRaisesRegex(BUNDLE.BundleError, "/binaries/server_sha256"):
            self.fixture.open()

    def test_schema_errors_name_file_and_pointer(self):
        reference = deepcopy(self.fixture.reference)
        reference["inputs"] = {}
        atomic_write_json(self.fixture.directory / "bundle.json", reference)
        with self.assertRaisesRegex(BUNDLE.BundleError, r"bundle.json#/inputs"):
            self.fixture.open()

    def test_duplicate_json_keys_and_nonfinite_numbers_refuse(self):
        for data in (b'{"a": 1, "a": 2}', b'{"a": NaN}'):
            with self.assertRaisesRegex(BUNDLE.BundleError, "document.json#/"):
                BUNDLE.decode(data, "document.json")

    def test_lane_set_equals_plan_recut_set(self):
        for directories in ({}, {"rtx4090": self.fixture.directory},
                            {"rtx3090": self.fixture.directory, "rtx4090": self.fixture.directory}):
            with self.assertRaisesRegex(BUNDLE.BundleError, "re-cut native lanes"):
                BUNDLE.load_bundles(self.fixture.root, self.fixture.release, self.fixture.plan,
                                    self.fixture.manifest, self.fixture.qualification, directories)

    def test_missing_and_changed_decisions_refuse(self):
        path = self.fixture.root / self.fixture.qualification["observed_gates"]["native_speed_decision"]["repository_path"]
        atomic_write(path, b"{}")
        with self.assertRaisesRegex(BUNDLE.BundleError, "SHA-256 mismatch"):
            BUNDLE.decisions(BUNDLE.Inputs(), self.fixture.root, self.fixture.release, self.fixture.plan, self.fixture.qualification)
        self.fixture.qualification["observed_gates"].clear()
        with self.assertRaisesRegex(BUNDLE.BundleError, "decision must have"):
            BUNDLE.decisions(BUNDLE.Inputs(), self.fixture.root, self.fixture.release, self.fixture.plan, self.fixture.qualification)

    def test_inputs_detect_change_after_validation(self):
        bundle = self.fixture.open()
        atomic_write(self.fixture.directory / "fit.json", "{}")
        with self.assertRaisesRegex(BUNDLE.BundleError, "input changed"):
            bundle.inputs.check()


if __name__ == "__main__":
    unittest.main()
