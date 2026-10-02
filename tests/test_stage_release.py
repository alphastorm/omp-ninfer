from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR = ROOT / "tests" / "fixtures" / "upstream-omp-component.json"
SOURCE = "v0.7.4"
# A release that is never checked in, so the staged tree cannot collide with a real one.
TARGET = "v0.99.0"
# The checked-in public release, whose client the root profiles describe.
CURRENT = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))["product_release"]


class StageReleaseTests(unittest.TestCase):
    @staticmethod
    def load(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def save(path: Path, value: dict) -> None:
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def staging_copy(self, *, prepare_client_evidence: bool = True, source_release: str = SOURCE) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for name in ("scripts", "profiles", "releases"):
            shutil.copytree(ROOT / name, root / name)
        shutil.copy2(ROOT / "compatibility.json", root / "compatibility.json")
        shutil.copytree(ROOT / "docs" / "measurements", root / "docs" / "measurements")
        shutil.copy2(ROOT / "docs" / "COMPATIBILITY.md", root / "docs" / "COMPATIBILITY.md")
        for document in ("QUICKSTART.md", "SECURITY.md"):
            (root / "docs" / document).write_text("# Staging fixture\n", encoding="utf-8")
        source = root / "releases" / source_release
        if not prepare_client_evidence:
            return root
        manifest = self.load(source / "manifest.json")
        pins = set()
        for path in (root / "releases").glob("*/manifest.json"):
            client = self.load(path)["components"]["omp"]
            if "distribution_kind" not in client:
                pins.update((client["upstream_tag"].removeprefix("v"),
                             client["source_commit"], client["upstream_commit"]))

        # This fixture carries runtime identity, not a claim about predecessor client proof.
        # Real old client evidence must fail the staging sweep, rather than be relabelled.
        def omit_client_evidence(value):
            if isinstance(value, dict):
                return {key: omit_client_evidence(item) for key, item in value.items()}
            if isinstance(value, list):
                return [omit_client_evidence(item) for item in value]
            if isinstance(value, str) and any(pin in value for pin in pins):
                return "Client evidence omitted from staging fixture."
            return value

        manifest["publication"] = omit_client_evidence(manifest["publication"])
        self.save(source / "manifest.json", manifest)
        for path in source.rglob("*.json"):
            if path.name not in {"manifest.json", "compatibility.json"}:
                self.save(path, omit_client_evidence(self.load(path)))
        for path in source.glob("*.md"):
            path.write_text("# Staging fixture\n", encoding="utf-8")
        compatibility = self.load(source / "compatibility.json")
        for profile in compatibility["profiles"]:
            profile["limitations"] = []
        self.save(source / "compatibility.json", compatibility)
        return root

    def stage(self, root: Path, descriptor: Path | None = DESCRIPTOR,
              *, require_clean_client: bool = False,
              source_release: str = SOURCE,
              config_sha: str | None = None,
              model_args: list[str] | None = None) -> subprocess.CompletedProcess:
        ninfer = self.load(root / "releases" / source_release / "manifest.json")["components"]["ninfer"]
        command = [
            sys.executable, str(root / "scripts" / "stage_release.py"),
            "--from", source_release, "--release", TARGET,
            "--release-tag", ninfer["release_tag"],
            "--source-tag", ninfer["source_archive_url"].split("/")[-2],
            "--source-commit", ninfer["source_commit"],
            "--binary-sha", ninfer["server_binary_sha256"],
            "--archive-sha", ninfer["binary_archive_sha256"],
            "--source-archive-sha", ninfer["source_archive_sha256"],
            "--sbom-sha", ninfer["sbom_sha256"],
            "--image-digest", ninfer["oci_manifest_digest"],
            "--runtime-receipt-release", ninfer["runtime_receipt_release"],
            "--archive-name", ninfer["binary_archive_url"].rsplit("/", 1)[-1],
            *(["--config-sha", config_sha] if config_sha else ["--keep-deployment-profile"]),
        ]
        if descriptor is not None:
            command.extend(["--omp-component", str(descriptor)])
        if require_clean_client:
            command.append("--require-clean-client")
        command.extend(model_args or [])
        return subprocess.run(command, cwd=root, capture_output=True, text=True)

    def model_arguments(self, model: dict) -> list[str]:
        return ["--model-revision", model["revision"],
                "--model-sha256", model["artifact_sha256"],
                "--model-bytes", str(model["artifact_bytes"])]

    @staticmethod
    def distinct_model(model: dict) -> dict:
        revision = hashlib.sha256((model["revision"] + "synthetic").encode()).hexdigest()[:40]
        return dict(
            model, revision=revision,
            artifact_url=model["artifact_url"].replace(model["revision"], revision),
            artifact_sha256=hashlib.sha256((model["artifact_sha256"] + "synthetic").encode()).hexdigest(),
            artifact_bytes=model["artifact_bytes"] + 1)

    def test_primary_model_change_preserves_native_packages_and_predecessor_model(self) -> None:
        root = self.staging_copy(source_release=CURRENT)
        source = root / "releases" / CURRENT
        previous = self.load(source / "manifest.json")
        immutable = [root / "compatibility.json", *(root / "profiles").glob("*.json"),
                     *source.rglob("*")]
        before = {path: path.read_bytes() for path in immutable if path.is_file()}
        model = self.distinct_model(previous["components"]["model"])
        native = previous["components"].get("native_model", previous["components"]["model"])
        result = self.stage(root, None, source_release=CURRENT, model_args=self.model_arguments(model))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        staged = root / "releases" / TARGET
        manifest = self.load(staged / "manifest.json")
        self.assertEqual(manifest["components"]["model"], model)
        self.assertEqual(manifest["components"]["native_model"], native)
        for current, old in zip(manifest["components"]["ninfer_variants"],
                                previous["components"]["ninfer_variants"]):
            self.assertEqual({k: v for k, v in current.items() if k != "qualification"},
                             {k: v for k, v in old.items() if k != "qualification"})
        authority = self.load(staged / "compatibility.json")
        self.assertEqual({row["runtime"]["model_sha256"] for row in authority["profiles"]},
                         {model["artifact_sha256"]})
        self.assertEqual({row["model_sha256"] for row in authority["runtime_variants"]},
                         {native["artifact_sha256"]})
        qualification = self.load(staged / "qualification.json")
        self.assertEqual(qualification["runtime_identity"]["model_artifact_sha256"], model["artifact_sha256"])
        self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_later_primary_change_keeps_an_existing_native_model(self) -> None:
        root = self.staging_copy(source_release=CURRENT)
        source = root / "releases" / CURRENT / "manifest.json"
        manifest = self.load(source)
        native = manifest["components"].setdefault("native_model", manifest["components"]["model"])
        manifest["components"]["model"] = self.distinct_model(manifest["components"]["model"])
        model = self.distinct_model(manifest["components"]["model"])
        self.save(source, manifest)
        result = self.stage(root, None, source_release=CURRENT, model_args=self.model_arguments(model))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        components = self.load(root / "releases" / TARGET / "manifest.json")["components"]
        self.assertEqual(components["native_model"], native)
        self.assertEqual(components["model"], model)

    def test_unchanged_model_does_not_add_redundant_native_model(self) -> None:
        for split in (False, True):
            with self.subTest(split=split):
                root = self.staging_copy(source_release=CURRENT)
                path = root / "releases" / CURRENT / "manifest.json"
                manifest = self.load(path)
                components = manifest["components"]
                native = components.get("native_model", components["model"])
                if split:
                    components["native_model"] = native
                    components["model"] = self.distinct_model(native)
                else:
                    components["model"] = native
                    components.pop("native_model", None)
                self.save(path, manifest)
                model = components["model"]
                result = self.stage(root, None, source_release=CURRENT, model_args=self.model_arguments(model))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                staged = self.load(root / "releases" / TARGET / "manifest.json")["components"]
                self.assertEqual(staged["model"], model)
                if split:
                    self.assertEqual(staged["native_model"], native)
                else:
                    self.assertNotIn("native_model", staged)

    def test_primary_returning_to_native_model_removes_the_override(self) -> None:
        root = self.staging_copy(source_release=CURRENT)
        path = root / "releases" / CURRENT / "manifest.json"
        manifest = self.load(path)
        model = manifest["components"].setdefault("native_model", manifest["components"]["model"])
        manifest["components"]["model"] = self.distinct_model(manifest["components"]["model"])
        self.save(path, manifest)
        result = self.stage(root, None, source_release=CURRENT, model_args=self.model_arguments(model))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        components = self.load(root / "releases" / TARGET / "manifest.json")["components"]
        self.assertNotIn("native_model", components)
        self.assertEqual(components["model"], model)

    def test_invalid_or_partial_model_override_fails_before_creating_release(self) -> None:
        model = self.load(ROOT / "tests/fixtures/dflash2-model.json")
        cases = (["--model-revision", model["revision"]],
                 self.model_arguments(dict(model, revision="z" * 40)),
                 self.model_arguments(dict(model, artifact_sha256="A" * 64)),
                 self.model_arguments(dict(model, artifact_bytes=0)))
        for arguments in cases:
            with self.subTest(arguments=arguments):
                root = self.staging_copy(source_release=CURRENT)
                result = self.stage(root, None, source_release=CURRENT, model_args=arguments)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertFalse((root / "releases" / TARGET).exists())

    def test_descriptor_replaces_client_and_discards_predecessor_acceptance(self) -> None:
        root = self.staging_copy()
        immutable = [root / "compatibility.json", *(root / "profiles").glob("*.json"),
                     *(root / "releases" / SOURCE).rglob("*")]
        before = {path: path.read_bytes() for path in immutable if path.is_file()}
        result = self.stage(root, require_clean_client=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        descriptor = self.load(DESCRIPTOR)
        staged = root / "releases" / TARGET
        manifest = self.load(staged / "manifest.json")
        for key, value in descriptor["omp"].items():
            self.assertEqual(manifest["components"]["omp"][key], value)
        self.assertNotIn("source_commit", manifest["components"]["omp"])
        compatibility = self.load(staged / "compatibility.json")
        platforms = ("darwin-arm64", "windows-x64", "linux-x64")
        for profile, platform in zip(compatibility["profiles"], platforms):
            self.assertEqual(profile["client_distribution"], descriptor["platforms"][platform])
            self.assertIsNone(profile["acceptance_receipt"])
            self.assertFalse(profile["installable"])
            self.assertEqual(profile["status"], "preview")
        self.assertFalse((staged / "acceptance").exists())
        qualification = self.load(staged / "qualification.json")
        self.assertNotIn("documented_route_acceptance", qualification["composition"])
        self.assertFalse(qualification["external_installation_qualified"])
        self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_unmodified_predecessor_stages_before_notes_and_evidence_are_rewritten(self) -> None:
        root = self.staging_copy(prepare_client_evidence=False)
        result = self.stage(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stderr, r"NINFER_RELEASE_NOTES\.md:\d+: retains predecessor OMP identity")
        self.assertFalse((root / "releases" / TARGET / "acceptance").exists())

    def test_staging_reports_leftover_predecessor_pins_without_failing(self) -> None:
        root = self.staging_copy()
        source = root / "releases" / SOURCE
        omp = self.load(source / "manifest.json")["components"]["omp"]
        pins = [omp["upstream_tag"], omp["component_release_tag"], omp["source_commit"],
                omp["artifact_url"]]
        (source / "operator-pins.txt").write_text("\n".join(pins), encoding="utf-8")
        result = self.stage(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for line, pin in enumerate(pins, 1):
            self.assertIn(f"operator-pins.txt:{line}: retains predecessor OMP identity {pin!r}", result.stderr)
        staged = self.load(root / "releases" / TARGET / "manifest.json")
        self.assertEqual(staged["components"]["omp"]["upstream_tag"],
                         self.load(DESCRIPTOR)["omp"]["upstream_tag"])

    def test_require_clean_client_rejects_pins_after_writing_the_draft(self) -> None:
        root = self.staging_copy()
        source = root / "releases" / SOURCE
        omp = self.load(source / "manifest.json")["components"]["omp"]
        (source / "operator-pin.txt").write_text(omp["source_commit"], encoding="utf-8")
        result = self.stage(root, require_clean_client=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("operator-pin.txt:1: retains predecessor OMP identity", result.stderr)
        self.assertIn("--require-clean-client: staged draft retains predecessor client pins", result.stderr)
        staged = self.load(root / "releases" / TARGET / "manifest.json")
        self.assertEqual(staged["components"]["omp"]["upstream_tag"],
                         self.load(DESCRIPTOR)["omp"]["upstream_tag"])

    def test_invalid_descriptor_fails_before_creating_release(self) -> None:
        root = self.staging_copy()
        descriptor = self.load(DESCRIPTOR)
        descriptor["platforms"]["linux-x64"].pop("asset_id")
        path = root / "invalid-client.json"
        self.save(path, descriptor)
        result = self.stage(root, path)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("linux-docker-local client_distribution.asset_id must be a positive integer",
                      result.stderr)
        self.assertFalse((root / "releases" / TARGET).exists())

    def test_a_new_profile_cannot_keep_the_source_configuration_identity(self) -> None:
        """The configuration identity hashes --deployment-profile. v0.8.3 was staged with
        v0.8.2's identity under a new profile name, and its launcher refused the candidate."""
        root = self.staging_copy()
        source = self.load(root / "releases" / SOURCE / "manifest.json")
        result = self.stage(root, config_sha=source["runtime_identity"]["configuration_sha256"])
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("pass --keep-deployment-profile", result.stderr)
        self.assertFalse((root / "releases" / TARGET).exists())

    def test_staging_without_descriptor_preserves_the_source_client(self) -> None:
        """Without a descriptor the staged client is the source release's, whatever its kind."""
        root = self.staging_copy(source_release=CURRENT)
        source = root / "releases" / CURRENT
        previous = self.load(source / "manifest.json")["components"]["omp"]
        clients = [row["client_distribution"] for row in self.load(source / "compatibility.json")["profiles"]]
        result = self.stage(root, None, source_release=CURRENT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        staged = root / "releases" / TARGET
        current = self.load(staged / "manifest.json")["components"]["omp"]
        for key in previous:
            if key != "compatibility_sha256":
                self.assertEqual(current[key], previous[key])
        self.assertEqual([row["client_distribution"]
                          for row in self.load(staged / "compatibility.json")["profiles"]], clients)

    def test_staged_manifest_publishes_as_the_staged_release(self) -> None:
        """v0.8.5 and v0.8.6 were staged still targeting their predecessor's GitHub release."""
        root = self.staging_copy(source_release=CURRENT)
        result = self.stage(root, None, source_release=CURRENT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        targets = self.load(root / "releases" / TARGET / "manifest.json")["publication"]["targets"]
        releases = [target for target in targets if target.startswith("GitHub public release ")]
        self.assertEqual(releases, [f"GitHub public release {TARGET}"])


if __name__ == "__main__":
    unittest.main()
