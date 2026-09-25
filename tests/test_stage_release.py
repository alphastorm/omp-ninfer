from __future__ import annotations

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
              source_release: str = SOURCE) -> subprocess.CompletedProcess:
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
            "--keep-deployment-profile",
        ]
        if descriptor is not None:
            command.extend(["--omp-component", str(descriptor)])
        if require_clean_client:
            command.append("--require-clean-client")
        return subprocess.run(command, cwd=root, capture_output=True, text=True)

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
        self.assertEqual(staged["components"]["omp"]["upstream_tag"], "v18.3.0")

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
        self.assertEqual(staged["components"]["omp"]["upstream_tag"], "v18.3.0")

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


if __name__ == "__main__":
    unittest.main()
