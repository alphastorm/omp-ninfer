"""Public plans bind identities and support decisions to the ready predecessor."""

from __future__ import annotations

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_plan_test", ROOT / "scripts" / "release_plan.py")
assert SPEC is not None and SPEC.loader is not None
PLAN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PLAN)

from release_io import atomic_write, atomic_write_json
from verify_release import PRIVATE_MARKERS

PREDECESSOR = "v1.0.0"
RELEASE = "v1.1.0"


def plan_fixture(root: Path) -> tuple[dict, dict, dict]:
    runtime = {
        "release_tag": "v2.0.0-runtime", "source_commit": "a" * 40,
        "server_binary_sha256": "b" * 64, "binary_archive_sha256": "c" * 64,
        "source_archive_sha256": "d" * 64, "sbom_sha256": "e" * 64,
        "oci_manifest_digest": "sha256:" + "f" * 64,
        "source_archive_url": "https://example.invalid/download/v2.0.0-source/source.tar.gz",
        "binary_archive_url": "https://example.invalid/download/v2.0.0-runtime/runtime.tar.gz",
        "runtime_receipt_release": "v2.0.0-image",
    }
    natives = [
        {"id": lane, "release_tag": f"v2.0.0-{lane}", "source_commit": "a" * 40,
         "package_sha256": "1" * 64, "server_binary_sha256": "2" * 64,
         "configuration_sha256": "3" * 64, "model_artifact_sha256": "4" * 64,
         "maximum_context_tokens": 4096, "runtime_shape": {"max_concurrency": 1}}
        for lane in PLAN.COMPONENT_IDS[1:]
    ]
    manifest = {"release": PREDECESSOR, "status": "ready",
                "components": {"ninfer": runtime, "ninfer_variants": natives,
                               "omp": {"upstream_tag": "v2.0.0"}}}
    authority = {"product_release": PREDECESSOR,
                 "profiles": [{"id": name} for name in (
                     "windows-docker-local", "darwin-remote-ssh", "linux-docker-local")]}
    plan = {
        "artifact_type": "omp_ninfer_release_plan", "schema_version": 1, "release": RELEASE,
        "predecessor": PREDECESSOR, "client": {"upstream_tag": "v2.0.0", "disposition": "carried"},
        "components": [{"id": key, "disposition": "carried", "release_tag": row["release_tag"],
                        "source_commit": row["source_commit"]}
                       for key, row in PLAN.manifest_components(manifest).items()],
        "platforms": {row["id"]: "preview" if row["id"].startswith("darwin") else "qualified"
                      for row in authority["profiles"]},
        "limitations": ["No general performance guarantee is implied."],
        "decisions": [{"id": "support", "kind": "scope", "sha256": "5" * 64}],
    }
    atomic_write_json(root / "releases" / PREDECESSOR / "manifest.json", manifest)
    atomic_write_json(root / "compatibility.json", authority)
    atomic_write_json(root / "releases" / RELEASE / "plan.json", plan)
    return plan, manifest, authority


class ReleasePlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.plan, self.previous, self.authority = plan_fixture(self.root)
        self.path = self.root / "releases" / RELEASE / "plan.json"

    def errors(self) -> list[str]:
        atomic_write_json(self.path, self.plan)
        return PLAN.plan_errors(self.root, RELEASE)

    def refuses(self, message: str) -> None:
        self.assertTrue(any(message in error for error in self.errors()), self.errors())

    def manifest(self) -> dict:
        manifest = copy.deepcopy(self.previous)
        manifest.update(release=RELEASE, status="draft")
        atomic_write_json(self.path.parent / "manifest.json", manifest)
        return manifest

    def test_valid_plan_before_and_after_staging(self) -> None:
        self.assertEqual(PLAN.load_plan(self.root, RELEASE), self.plan)
        self.assertEqual(self.errors(), [])
        self.manifest()
        self.assertEqual(self.errors(), [])

    def test_release_must_be_ga(self) -> None:
        self.assertIn("GA version", PLAN.plan_errors(self.root, RELEASE + "-rc.1")[0])

    def test_release_must_match_directory(self) -> None:
        self.plan["release"] = PREDECESSOR
        self.refuses("release must match")

    def test_release_must_advance_predecessor(self) -> None:
        self.plan["predecessor"] = RELEASE
        self.refuses("greater than")

    def test_predecessor_must_be_ga(self) -> None:
        self.plan["predecessor"] = PREDECESSOR + "-rc.1"
        self.refuses("predecessor must be a GA")

    def test_predecessor_is_latest_ready_not_held_candidate(self) -> None:
        held = copy.deepcopy(self.previous)
        held.update(release="v1.0.5", status="candidate")
        atomic_write_json(self.root / "releases" / held["release"] / "manifest.json", held)
        self.assertEqual(self.errors(), [])
        held["status"] = "ready"
        atomic_write_json(self.root / "releases" / held["release"] / "manifest.json", held)
        self.refuses("latest ready")

    def test_component_ids_are_closed(self) -> None:
        self.plan["components"][1]["id"] = "unknown"
        self.refuses("closed component set")

    def test_component_ids_are_unique(self) -> None:
        self.plan["components"].append(copy.deepcopy(self.plan["components"][0]))
        self.refuses("duplicated")

    def test_runtime_component_is_required(self) -> None:
        self.plan["components"].pop(0)
        self.refuses("include rtx5090-container")

    def test_carried_tag_must_equal_predecessor(self) -> None:
        self.plan["components"][0]["release_tag"] = "v3.0.0-runtime"
        self.refuses("carried identity")

    def test_carried_source_must_equal_predecessor(self) -> None:
        self.plan["components"][1]["source_commit"] = "9" * 40
        self.refuses("carried identity")

    def test_recut_tag_cannot_reuse_predecessor(self) -> None:
        self.plan["components"][0]["disposition"] = "recut"
        self.refuses("recut tag reuses")

    def test_manifest_tag_must_agree(self) -> None:
        manifest = self.manifest()
        manifest["components"]["ninfer"]["release_tag"] = "v3.0.0-runtime"
        atomic_write_json(self.path.parent / "manifest.json", manifest)
        self.refuses("tag or commit differs")

    def test_manifest_commit_must_agree(self) -> None:
        manifest = self.manifest()
        manifest["components"]["ninfer_variants"][0]["source_commit"] = "9" * 40
        atomic_write_json(self.path.parent / "manifest.json", manifest)
        self.refuses("tag or commit differs")

    def test_manifest_component_set_must_agree(self) -> None:
        manifest = self.manifest()
        manifest["components"]["ninfer_variants"].pop()
        atomic_write_json(self.path.parent / "manifest.json", manifest)
        self.refuses("component ids differ")

    def test_manifest_native_provenance_must_agree(self) -> None:
        manifest = self.manifest()
        manifest["components"]["ninfer_variants"][0]["package_sha256"] = "9" * 64
        atomic_write_json(self.path.parent / "manifest.json", manifest)
        self.refuses("provenance disposition")

    def test_manifest_container_provenance_must_agree(self) -> None:
        manifest = self.manifest()
        manifest["components"]["ninfer"]["oci_manifest_digest"] = "sha256:" + "9" * 64
        atomic_write_json(self.path.parent / "manifest.json", manifest)
        self.refuses("provenance disposition")

    def test_platform_keys_must_equal_authority_profiles(self) -> None:
        self.plan["platforms"].pop("darwin-remote-ssh")
        self.refuses("keys must equal")

    def test_release_local_authority_owns_profile_keys(self) -> None:
        local = {"profiles": [{"id": "local-profile"}]}
        atomic_write_json(self.path.parent / "compatibility.json", local)
        self.plan["platforms"] = {"local-profile": "qualified"}
        self.assertEqual(self.errors(), [])

    def test_absolute_paths_are_forbidden_in_every_string(self) -> None:
        for path in ("/absolute/file", "D:\\absolute\\file", "\\\\server\\share\\file"):
            with self.subTest(path=path):
                self.plan["decisions"][0]["id"] = path
                self.refuses("absolute path")

    def test_private_markers_are_forbidden_in_every_string(self) -> None:
        for marker in PRIVATE_MARKERS:
            with self.subTest(marker=marker):
                self.plan["decisions"][0]["id"] = "prefix " + marker + " suffix"
                self.refuses("private marker")

    def test_schema_is_closed_and_typed(self) -> None:
        mutations = [
            ("artifact_type", "other"), ("schema_version", True), ("extra", "field"),
            ("client", []), ("components", {}), ("platforms", []), ("decisions", {}),
            ("limitations", {}), ("limitations", [""]), ("limitations", [" padded "]),
            ("limitations", ["same", "same"]),
            ("limitations", ["The native component is carried unchanged."]),
        ]
        original = copy.deepcopy(self.plan)
        for key, value in mutations:
            with self.subTest(key=key):
                self.plan = {**copy.deepcopy(original), key: value}
                self.assertTrue(self.errors())

    def test_component_schema_and_identity_types(self) -> None:
        for field, value in (("source_commit", "short"), ("disposition", "updated"),
                             ("release_tag", ""), ("id", [])):
            with self.subTest(field=field):
                original = self.plan["components"][0][field]
                self.plan["components"][0][field] = value
                self.assertTrue(self.errors())
                self.plan["components"][0][field] = original

    def test_platform_posture_is_closed(self) -> None:
        self.plan["platforms"]["windows-docker-local"] = "pending"
        self.refuses("values must be qualified or preview")

    def test_decision_schema_and_unique_ids(self) -> None:
        for field, value in (("kind", "other"), ("sha256", "short"), ("id", "")):
            with self.subTest(field=field):
                original = self.plan["decisions"][0][field]
                self.plan["decisions"][0][field] = value
                self.assertTrue(self.errors())
                self.plan["decisions"][0][field] = original
        self.plan["decisions"].append(copy.deepcopy(self.plan["decisions"][0]))
        self.refuses("duplicated")

    def test_client_disposition_and_manifest_agreement(self) -> None:
        self.plan["client"]["disposition"] = "updated"
        self.refuses("updated tag reuses")
        self.plan["client"] = {"upstream_tag": "v3.0.0", "disposition": "carried"}
        self.refuses("carried tag differs")
        self.plan["client"]["disposition"] = "updated"
        self.manifest()
        self.refuses("manifest client tag differs")

    def test_malformed_or_missing_plan_is_an_error(self) -> None:
        for content in ("[]", "{"):
            atomic_write(self.path, content)
            self.assertTrue(PLAN.plan_errors(self.root, RELEASE))
        self.path.unlink()
        self.assertTrue(PLAN.plan_errors(self.root, RELEASE))


if __name__ == "__main__":
    unittest.main()
