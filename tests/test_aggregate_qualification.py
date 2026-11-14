"""Behavioural aggregate checks and an opt-in replay of retained release evidence."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("aggregate_qualification", ROOT / "scripts/aggregate_qualification.py")
assert SPEC is not None and SPEC.loader is not None
AGGREGATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AGGREGATE)
from release_io import atomic_write, atomic_write_json


def load(path):
    return json.loads(path.read_bytes())


def command(root, *arguments):
    return subprocess.run([sys.executable, *map(str, arguments)], cwd=root, capture_output=True,
                          text=True, encoding="utf-8")


def carry_plan(root, release):
    manifest = load(root / "releases" / release / "manifest.json")
    predecessor = AGGREGATE.verifier.predecessor_manifest(root, release)
    components = manifest["components"]
    return {
        "artifact_type": "omp_ninfer_release_plan", "schema_version": 1, "release": release,
        "predecessor": predecessor["release"],
        "client": {"upstream_tag": components["omp"]["upstream_tag"], "disposition": "carried"},
        "components": [
            {"id": "rtx5090-container", "disposition": "carried",
             **{key: components["ninfer"][key] for key in ("release_tag", "source_commit")}},
            *[{"id": row["id"], "disposition": "carried",
               **{key: row[key] for key in ("release_tag", "source_commit")}}
              for row in components["ninfer_variants"]]],
        "platforms": {row["id"]: "qualified" for row in load(root / "releases" / release / "compatibility.json")["profiles"]},
        "decisions": []}


class CarriedAggregateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.staged = Path(cls.temporary.name) / "staged"
        shutil.copytree(ROOT, cls.staged, ignore=shutil.ignore_patterns(".git", "__pycache__", "tests"))
        runtime = load(cls.staged / "releases/v0.19.0/manifest.json")["components"]["ninfer"]
        args = [
            "scripts/stage_release.py", "--from", "v0.19.0", "--release", "v0.20.0",
            "--release-tag", runtime["release_tag"], "--source-tag", runtime["source_archive_url"].split("/")[-2],
            "--source-commit", runtime["source_commit"], "--binary-sha", runtime["server_binary_sha256"],
            "--archive-sha", runtime["binary_archive_sha256"], "--source-archive-sha", runtime["source_archive_sha256"],
            "--sbom-sha", runtime["sbom_sha256"], "--image-digest", runtime["oci_manifest_digest"],
            "--runtime-receipt-release", runtime["runtime_receipt_release"],
            "--archive-name", runtime["binary_archive_url"].rsplit("/", 1)[-1], "--keep-deployment-profile",
            "--omp-component", "releases/v0.19.0/qualification/client-components.json"]
        staged = command(cls.staged, *args)
        if staged.returncode != 0:
            raise AssertionError(f"carry-all staging exited {staged.returncode}\n{staged.stdout}\n{staged.stderr}")
        cls.plan = carry_plan(cls.staged, "v0.20.0")
        atomic_write_json(cls.staged / "releases/v0.20.0/plan.json", cls.plan)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        shutil.copytree(self.staged, self.root, dirs_exist_ok=True)
        self.plan_path = self.root / "releases/v0.20.0/plan.json"

    def compose(self, *, check=False):
        return AGGREGATE.aggregate(self.root, "v0.20.0", self.plan_path, {}, None, check=check)

    def test_all_carried_admit_is_no_write_and_emits_empty_binder_map(self):
        before = {path: path.read_bytes() for path in (self.root / "releases/v0.20.0").rglob("*") if path.is_file()}
        result = AGGREGATE.admit(self.root, "v0.20.0", self.plan_path, {})
        self.assertEqual(result, {"schema": 1, "lanes": {}})
        self.assertEqual(before, {path: path.read_bytes() for path in before})

    def test_all_carried_compose_is_idempotent_and_has_fact_derived_prose(self):
        before = json.loads(command(self.root, "scripts/verify_release.py", "--release", "v0.20.0", "--json").stdout)
        self.compose()
        self.assertEqual(self.compose(check=True), [])
        rebound = command(self.root, "scripts/rebind_release.py", "--release", "v0.20.0", "--draft")
        self.assertEqual(rebound.returncode, 0, rebound.stdout + rebound.stderr)
        after = json.loads(command(self.root, "scripts/verify_release.py", "--release", "v0.20.0", "--json").stdout)
        self.assertFalse(set(after["errors"]) - set(before["errors"]), "aggregate introduced a draft verifier refusal")
        q = load(self.root / "releases/v0.20.0/qualification.json")
        self.assertEqual(q["status"], "runtime-release-eligible")
        self.assertEqual(q["scope"].count("carried unchanged from v0.19.0"), 3)
        self.assertIn("3 distinct NInfer source commits", q["scope"])
        self.assertNotIn("re-cut for this release", q["scope"])
        self.assertFalse(q["publication_authorized"])
        self.assertFalse(q["external_installation_qualified"])
        self.assertEqual(q["observed_gates"], {})
        pub = load(self.root / "releases/v0.20.0/qualification/native-publication.json")
        self.assertEqual({row["lane"] for row in pub["lanes"]}, {"rtx3090", "rtx4090"})

    def test_carried_lane_changed_bytes_refuse_before_any_write(self):
        path = self.root / "releases/v0.20.0/qualification/rtx3090.json"
        atomic_write(path, path.read_bytes() + b" ")
        before = (self.root / "releases/v0.20.0/qualification.json").read_bytes()
        with self.assertRaisesRegex(AGGREGATE.BundleError, "carried bytes differ"):
            self.compose()
        self.assertEqual((self.root / "releases/v0.20.0/qualification.json").read_bytes(), before)

    def test_missing_decision_refuses(self):
        plan = deepcopy(self.plan)
        plan["decisions"] = [{"id": "scope-decision", "kind": "scope", "sha256": "a" * 64}]
        atomic_write_json(self.plan_path, plan)
        with self.assertRaisesRegex(AGGREGATE.BundleError, "decision must have"):
            self.compose()

    def test_check_cli_exits_one_on_tampered_tree_and_writes_nothing(self):
        self.compose()
        path = self.root / "releases/v0.20.0/qualification.json"
        value = load(path)
        value["interpretation"] = "Tampered summary."
        atomic_write_json(path, value)
        before = path.read_bytes()
        result = command(self.root, "scripts/aggregate_qualification.py", "compose", "--release", "v0.20.0",
                         "--plan", "releases/v0.20.0/plan.json", "--check")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("generated files differ", result.stderr)
        self.assertEqual(path.read_bytes(), before)

    def test_runtime_publication_is_refused_for_carried_runtime(self):
        with self.assertRaisesRegex(AGGREGATE.BundleError, "required exactly"):
            AGGREGATE.aggregate(self.root, "v0.20.0", self.plan_path, {}, Path("unused.json"))

    def test_native_publication_and_bundle_are_refused_for_carried_lane(self):
        with self.assertRaisesRegex(AGGREGATE.BundleError, "re-cut native lanes"):
            AGGREGATE.aggregate(self.root, "v0.20.0", self.plan_path, {"rtx3090": Path("unused")}, None)
        with self.assertRaisesRegex(AGGREGATE.BundleError, "publication lanes"):
            AGGREGATE.aggregate(self.root, "v0.20.0", self.plan_path, {}, None,
                                native_publications={"rtx3090": Path("unused")})

    def test_deployment_keep_and_advance_are_bound_to_configuration(self):
        previous = {"deployment_profile": "prior", "configuration_sha256": "a" * 64}
        self.assertEqual(AGGREGATE.deployment_policy("v0.20.0", deepcopy(previous), previous), "keep")
        with self.assertRaisesRegex(AGGREGATE.BundleError, "kept deployment"):
            AGGREGATE.deployment_policy("v0.20.0", {**previous, "configuration_sha256": "b" * 64}, previous)
        self.assertEqual(AGGREGATE.deployment_policy(
            "v0.20.0", {"deployment_profile": "qwen38-5090-v0.20.0", "configuration_sha256": "b" * 64}, previous), "advance")
        with self.assertRaisesRegex(AGGREGATE.BundleError, "advanced deployment"):
            AGGREGATE.deployment_policy("v0.20.0", {**previous, "deployment_profile": "other"}, previous)


class NativePublicationTests(unittest.TestCase):
    def test_each_publication_identity_closure_and_anonymous_read_binding(self):
        from test_qualification_bundle import SyntheticBundle
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = SyntheticBundle(root)
            bundle = fixture.open()
            row = bundle.row
            sums = (bundle.assets / "SHA256SUMS").read_bytes()
            lane = {
                "lane": bundle.lane, "published": True, "component_tag": row["release_tag"],
                "tag_commit": row["source_commit"], "source_commit": row["source_commit"],
                "build_profile": row["build_profile"], "public_package_executed_during_qualification": False,
                "publication_evidence_class": "anonymous-public-byte-downloads-and-matching-github-asset-digests",
                "release_url": row["repository"] + "/releases/tag/" + row["release_tag"],
                "published_at": "2026-11-13T00:00:00Z", "authenticated_at_utc": "2026-11-13T00:00:01Z",
                "outer_checksums_sha256": AGGREGATE.sha(sums), "outer_hashed_entries": len(bundle.asset_hashes),
                "total_distribution_files": len(bundle.asset_hashes) + 1,
                "assets": [{"name": name, "sha256": digest, "bytes": bundle.asset_paths[name].stat().st_size}
                           for name, digest in bundle.asset_hashes.items()],
                "checksums_asset": {"name": "SHA256SUMS", "sha256": AGGREGATE.sha(sums), "bytes": len(sums)},
                "actual_hardware_qualification": {"repository_path": row["qualification"]["summary"],
                                                  "sha256": row["qualification"]["sha256"]}}
            record = {
                "artifact_type": "omp_ninfer_native_component_publication", "schema_version": 1,
                "release": fixture.release, "as_of": "2026-11-13", "status": "passed",
                "publication_authorized_by_this_receipt": False, "product_publication_authorized": False,
                "identity": {"repository": row["repository"], "source_commit": row["source_commit"],
                             "upstream_commit": fixture.manifest["components"]["ninfer"]["upstream_commit"],
                             "model_artifact_sha256": row["model_artifact_sha256"]},
                "lanes": [lane]}
            path = root / "publication.json"
            atomic_write_json(path, record)
            AGGREGATE.publication(AGGREGATE.Inputs(), path, fixture.release, fixture.manifest, {bundle.lane: bundle})
            for name, wrong in (
                ("component_tag", "different"), ("source_commit", "a" * 40), ("tag_commit", "b" * 40),
                ("build_profile", "different"), ("published", False),
                ("outer_checksums_sha256", "a" * 64), ("outer_hashed_entries", 0),
                ("publication_evidence_class", "unauthenticated"),
                ("authenticated_at_utc", "not-a-timestamp"),
            ):
                with self.subTest(field=name):
                    changed = deepcopy(record)
                    changed["lanes"][0][name] = wrong
                    atomic_write_json(path, changed)
                    with self.assertRaises(AGGREGATE.BundleError):
                        AGGREGATE.publication(AGGREGATE.Inputs(), path, fixture.release,
                                              fixture.manifest, {bundle.lane: bundle})
            changed = deepcopy(record)
            changed["lanes"][0]["assets"][0]["bytes"] += 1
            atomic_write_json(path, changed)
            with self.assertRaisesRegex(AGGREGATE.BundleError, "/assets"):
                AGGREGATE.publication(AGGREGATE.Inputs(), path, fixture.release, fixture.manifest, {bundle.lane: bundle})


# These are prose-only exceptions. Hashes of files containing generated prose are
# compared after substituting the corresponding observed digest.
PROSE_POINTERS = {
    "qualification.json": ["/scope", "/interpretation",
        "/composition/behavioral_qualification/scope",
        "/composition/native_runtime_variants/rtx3090-windows-native/scope",
        "/composition/native_runtime_variants/rtx4090-windows-native/scope",
        "/observed_gates/rtx3090_upgrade/scope"],
    "manifest.json": ["/limitations", "/publication/blockers"],
    "qualification/rtx3090-upgrade.json": ["/scope"],
}
OTHER_STAGE_FILES = (
    "ROADMAP.md", "docs/FACTS.md", "docs/RELEASES.md",
    "releases/v0.19.0/NINFER_RELEASE_NOTES.md",
    "releases/v0.19.0/qualification/receipt-audit.json",
)


def replace_pointer(value, pointer, replacement):
    parts = pointer.strip("/").split("/")
    for part in parts[:-1]:
        value = value[int(part)] if isinstance(value, list) else value[part]
    if isinstance(value, list):
        value[int(parts[-1])] = replacement
    else:
        value[parts[-1]] = replacement


def first_difference(left, right, pointer=""):
    if type(left) is not type(right):
        return f"{pointer}: {left!r} != {right!r}"
    if isinstance(left, dict):
        if set(left) != set(right):
            return f"{pointer}: keys {sorted(left)} != {sorted(right)}"
        for key in left:
            found = first_difference(left[key], right[key], pointer + "/" + key)
            if found:
                return found
    elif isinstance(left, list):
        if len(left) != len(right):
            return f"{pointer}: lengths {len(left)} != {len(right)}"
        for index, (a, b) in enumerate(zip(left, right)):
            found = first_difference(a, b, pointer + "/" + str(index))
            if found:
                return found
    elif left != right:
        return f"{pointer}: {left!r} != {right!r}"
    return ""


class PrivateAggregateGoldenTests(unittest.TestCase):
    def test_retained_stage_replays_admit_real_binder_and_compose(self):
        registry_path = os.environ.get("OMP_NINFER_PRIVATE_FIXTURES")
        if not registry_path:
            self.skipTest("OMP_NINFER_PRIVATE_FIXTURES is unset")
        registry = load(Path(registry_path).expanduser())
        fixture = registry["v0.19.0"]["aggregate"]
        if "bundle_root" not in fixture:
            self.fail("private fixture registry must declare v0.19.0.aggregate.bundle_root")
        bundle_root = Path(fixture["bundle_root"]).expanduser()
        shallow = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT,
                                 check=True, capture_output=True, text=True).stdout.strip() == "true"
        if shallow:
            if os.environ.get("OMP_NINFER_REQUIRE_HISTORY") == "1":
                self.fail("full release history is required")
            self.skipTest("release replay needs a full clone")
        commits = registry["v0.19.0"]["commits"]
        def git(*args):
            return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout
        before = git("rev-parse", commits["runtime_stage"]).decode().strip()
        after = git("rev-parse", commits["stage"]).decode().strip()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = git("archive", before)
            with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
                for member in stream:
                    if member.isfile():
                        atomic_write(root / member.name, stream.extractfile(member).read())
            shutil.copytree(ROOT / "scripts", root / "scripts", dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
            manifest = load(root / "releases/v0.19.0/manifest.json")
            plan = carry_plan(root, "v0.19.0")
            plan["components"][0]["disposition"] = "recut"
            bundle_path = bundle_root / "rtx3090"
            reference = load(bundle_path / "bundle.json")
            asset_edge = next(edge for edge in reference["inputs"] if edge["role"] == "assets")
            receipt = load(bundle_path / Path(asset_edge["path"]).parent / "package-build-receipt.json")
            for component in plan["components"]:
                if component["id"] == "rtx3090-windows-native":
                    component.update(disposition="recut",
                                     release_tag=AGGREGATE.verifier.native_package_component_tag(receipt["package"]["filename"]),
                                     source_commit=receipt["patch_stack_sha"])
            decisions_edge = next(edge for edge in reference["inputs"] if edge["role"] == "decisions")
            decision_root = bundle_path / Path(decisions_edge["path"]).parent
            plan["decisions"] = [{"id": path.stem, "kind": "waiver" if "waiver" in path.stem else "scope",
                                  "sha256": AGGREGATE.sha(path.read_bytes())}
                                 for path in sorted(decision_root.glob("*.json"))]
            plan_path = root / "releases/v0.19.0/plan.json"
            atomic_write_json(plan_path, plan)
            old_manifest = deepcopy(manifest)
            admitted = command(root, "scripts/aggregate_qualification.py", "admit", "--release", "v0.19.0",
                               "--plan", plan_path, "--bundle", "rtx3090=" + str(bundle_path))
            self.assertEqual(admitted.returncode, 0, admitted.stdout + admitted.stderr)
            report = json.loads(admitted.stdout)
            manifest = load(root / "releases/v0.19.0/manifest.json")
            expected_manifest = deepcopy(old_manifest)
            next(row for row in expected_manifest["components"]["ninfer_variants"]
                 if row["id"] == "rtx3090-windows-native").update(status="qualified", installable=True)
            self.assertEqual(manifest, expected_manifest, "admit may change only the two native posture fields")
            bound = command(root, "scripts/bind_native_variant.py", *report["lanes"]["rtx3090"]["binder_arguments"])
            self.assertEqual(bound.returncode, 0, bound.stdout + bound.stderr)
            rebound = command(root, "scripts/rebind_release.py", "--release", "v0.19.0", "--draft")
            self.assertEqual(rebound.returncode, 0, rebound.stdout + rebound.stderr)
            composed = command(root, "scripts/aggregate_qualification.py", "compose", "--release", "v0.19.0",
                               "--plan", plan_path, "--bundle", "rtx3090=" + str(bundle_path),
                               "--runtime-publication", root / "releases/v0.19.0/qualification/runtime-publication.json",
                               "--native-publication", "rtx3090=" + str(bundle_root / "native-publication-rtx3090.json"))
            self.assertEqual(composed.returncode, 0, composed.stdout + composed.stderr)
            rebound = command(root, "scripts/rebind_release.py", "--release", "v0.19.0", "--draft")
            self.assertEqual(rebound.returncode, 0, rebound.stdout + rebound.stderr)
            # The stage audit is a separate producer after the aggregate. Install
            # its published bytes and rebind its edge, rather than attribute it
            # to this tool. The resulting summary's only other differences are
            # the explicitly enumerated prose and its transitive hashes.
            audit_name = "releases/v0.19.0/qualification/receipt-audit.json"
            atomic_write(root / audit_name, git("show", f"{after}:{audit_name}"))
            q_path = root / "releases/v0.19.0/qualification.json"
            q = load(q_path)
            q["receipt_audit"]["sha256"] = AGGREGATE.sha((root / audit_name).read_bytes())
            atomic_write_json(q_path, q)
            files = [
                "manifest.json", "qualification.json", "compatibility.json", "COMPATIBILITY.md", "qualification/native-publication.json",
                "qualification/native-speed-decision.json", "qualification/native-identity-decision.json",
                "qualification/slow-first-request-parity-waiver-class.json", "qualification/rtx3090-upgrade.json",
                "qualification/rtx3090-agent-parity.json", "qualification/rtx3090-speed.json",
                "qualification/rtx3090-windows-native.identity-proof.json", "qualification/rtx3090-windows-native.fit.json",
                "qualification/rtx3090.json", "qualification/rtx3090-windows-native.SHA256SUMS",
                "profiles/rtx3090/release-spec.json", "profiles/rtx3090/server-config.json"]
            stage_parent = git("rev-parse", after + "^").decode().strip()
            changed = set(git("diff", "--name-only", stage_parent, after).decode().splitlines())
            self.assertEqual(changed, {*(f"releases/v0.19.0/{name}" for name in files), *OTHER_STAGE_FILES})
            upgrade_sha = AGGREGATE.sha((root / "releases/v0.19.0/qualification/rtx3090-upgrade.json").read_bytes())
            for name in files:
                expected_bytes = git("show", f"{after}:releases/v0.19.0/{name}")
                observed_bytes = (root / "releases/v0.19.0" / name).read_bytes()
                if name not in PROSE_POINTERS:
                    self.assertEqual(observed_bytes, expected_bytes, name)
                    continue
                expected, observed = json.loads(expected_bytes), json.loads(observed_bytes)
                for pointer in PROSE_POINTERS[name]:
                    replace_pointer(expected, pointer, "generated prose")
                    replace_pointer(observed, pointer, "generated prose")
                if name == "qualification.json":
                    expected["observed_gates"]["rtx3090_upgrade"]["sha256"] = upgrade_sha
                if name == "manifest.json":
                    # rebind owns these hashes; generated qualification prose
                    # necessarily changes the summary's content digest.
                    expected["qualification"]["summary_sha256"] = observed["qualification"]["summary_sha256"]
                self.assertFalse(first_difference(observed, expected), name + first_difference(observed, expected))
                self.assertEqual(AGGREGATE.json_bytes(observed), AGGREGATE.json_bytes(expected),
                                 name + ": non-prose byte ordering differs")


if __name__ == "__main__":
    unittest.main()
