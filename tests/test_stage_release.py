from __future__ import annotations

import hashlib
import importlib.util
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
# Staging mechanics start from an immutable accepted source, not an unqualified restage.
CURRENT = "v0.12.2"
ACCEPTED_PROFILES = ROOT / "tests/fixtures/profiles-v0.12.2"
sys.path.insert(0, str(ROOT / "scripts"))
from verify_release import configuration_identity, product_version


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
        # This fixture stages its chosen source as the immediate predecessor.
        # Later checked-in releases are not part of that historical starting state.
        source_version = product_version(source_release)
        assert source_version is not None
        for path in (root / "releases").iterdir():
            version = product_version(path.name)
            if version is not None and version > source_version:
                shutil.rmtree(path)
        for profile in ACCEPTED_PROFILES.glob("*.json"):
            shutil.copy2(profile, root / "profiles" / profile.name)
        if source_release in (SOURCE, "v0.10.0"):
            # Historical-source fixtures keep their real legacy provider epoch.
            if source_release == "v0.10.0":
                authority = self.load(root / "releases" / source_release / "compatibility.json")
                clients = {row["id"]: row["client_distribution"] for row in authority["profiles"]}
                profile_ids = {"manual-ssh-tunnel": "darwin-remote-ssh",
                               "native-windows-docker-local": "windows-docker-local"}
            for path in (root / "profiles").glob("*.json"):
                profile = self.load(path)
                profile["omp_provider"].pop("compat", None)
                profile["omp_provider"]["stateful_responses_environment"] = {"PI_OPENAI_STATEFUL": "1"}
                if source_release == "v0.10.0":
                    profile["client"] = clients[profile_ids[profile["installation_mode"]]]
                self.save(path, profile)
        shutil.copy2(ROOT / "releases" / CURRENT / "compatibility.json",
                     root / "compatibility.json")
        shutil.copytree(ROOT / "docs" / "measurements", root / "docs" / "measurements")
        shutil.copy2(ROOT / "releases" / CURRENT / "COMPATIBILITY.md",
                     root / "docs" / "COMPATIBILITY.md")
        for document in ("QUICKSTART.md", "SECURITY.md", "BENCHMARKS.md"):
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
        # Redacting client-only evidence changes native summary bytes too. Keep
        # the predecessor's configuration proof hash-bound to those fixture bytes.
        for variant in manifest["components"].get("ninfer_variants", []):
            qualification = variant["qualification"]
            summary = root / qualification["summary"]
            qualification["sha256"] = hashlib.sha256(summary.read_bytes()).hexdigest()
        self.save(source / "manifest.json", manifest)
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
              model_args: list[str] | None = None,
              dependency_args: list[str] | None = None) -> subprocess.CompletedProcess:
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
        command.extend(dependency_args or [])
        return subprocess.run(command, cwd=root, capture_output=True, text=True)

    def test_optional_dependency_sbom_binds_only_the_selected_native_variant(self) -> None:
        root = self.staging_copy(source_release=CURRENT)
        previous = self.load(root / "releases" / CURRENT / "manifest.json")
        variant = previous["components"]["ninfer_variants"][-1]
        url = (f"https://github.com/alphastorm/ninfer/releases/download/"
               f"{variant['release_tag']}/{variant['package_name'].removesuffix('.tar.gz')}.cdx.json")
        pins = {"sbom_dependency_url": url, "sbom_dependency_sha256": "a" * 64}
        result = self.stage(root, None, source_release=CURRENT, dependency_args=[
            "--sbom-dependency-url", f"{variant['id']}={url}",
            "--sbom-dependency-sha256", f"{variant['id']}={'a' * 64}"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        staged = self.load(root / "releases" / TARGET / "manifest.json")
        for before, after in zip(previous["components"]["ninfer_variants"],
                                 staged["components"]["ninfer_variants"]):
            expected = {**before, **pins} if before["id"] == variant["id"] else before
            self.assertEqual({key: value for key, value in after.items() if key != "qualification"},
                             {key: value for key, value in expected.items() if key != "qualification"})
        self.assertEqual(self.load(root / "releases" / CURRENT / "manifest.json"), previous)

    def test_prepared_notes_gate_prose_and_new_profile_shape_survive_staging_and_promote_at_lane_pin(self) -> None:
        root = self.staging_copy(source_release=CURRENT)
        target = root / "releases" / TARGET
        target.mkdir()
        notes = "# Prepared fixture notes\nNo predecessor acceptance is claimed.\n"
        (target / "NINFER_RELEASE_NOTES.md").write_text(notes)
        self.save(target / "qualification.json", {
            "release": TARGET, "status": "preparation-only",
            "scope": "Fresh runtime and client acceptance required.",
            "interpretation": "No inherited observations.",
            "observed_gates": {"fresh_runtime": {"status": "pending"}},
            "documented_route_acceptance": {"status": "pending"},
        })
        # The real release becomes a full authority after staging. This fixture still
        # exercises the notes-only input contract, independently of that later posture.
        prepared_authority = {
            "artifact_type": "omp_ninfer_prepared_compatibility",
            "schema_version": 1,
            "product_release": TARGET,
            "status": "preparation-only",
            "runtime_contracts": self.load(
                ROOT / "releases/v0.13.0/compatibility.json")["runtime_contracts"],
        }
        self.save(target / "compatibility.json", prepared_authority)
        templates = root / "profiles" / "fixture-new-shape"
        templates.mkdir()
        for path in (ROOT / "profiles/v0.13.0").glob("*.json"):
            profile = self.load(path)
            profile["release"] = TARGET
            profile["server"]["deployment_profile"] = f"qwen38-5090-{TARGET}"
            arguments = profile["server"]["arguments"]
            arguments[arguments.index("--deployment-profile") + 1] = f"qwen38-5090-{TARGET}"
            config = configuration_identity(profile)
            arguments[arguments.index("--config-sha256") + 1] = config
            self.save(templates / path.name, profile)
        live = [root / "compatibility.json", *(root / "profiles").glob("*.json")]
        original = {path: path.read_bytes() for path in live}
        descriptor = ROOT / "docs/measurements/2026-10-25-omp-18126-client-components.json"
        result = self.stage(root, descriptor, source_release=CURRENT, config_sha=config,
                            dependency_args=["--prepared-draft", "--profile-template-dir", str(templates)])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((target / "NINFER_RELEASE_NOTES.md").read_text(), notes)
        self.assertEqual({path: path.read_bytes() for path in live}, original)
        qualification = self.load(target / "qualification.json")
        self.assertEqual(qualification["observed_gates"], {"fresh_runtime": {"status": "pending"}})
        self.assertEqual(qualification["composition"]["local_release_packaging"]["status"], "pending")
        self.assertNotIn("publication_receipt", qualification["composition"]["local_release_packaging"])
        authority = self.load(target / "compatibility.json")
        self.assertEqual(authority["runtime_contracts"], prepared_authority["runtime_contracts"])
        for row in authority["profiles"]:
            self.assertEqual(row["runtime"]["session_checkpoints"]["store_mount"], "/checkpoints-v013")
            self.assertEqual(row["runtime"]["speculative_backend"], "dflash2")
            self.assertEqual(row["runtime"]["draft_tokens"], 7)
        manifest_path = target / "manifest.json"
        manifest = self.load(manifest_path)
        shutil.copytree(ROOT / "examples/manual-tunnel", root / "examples/manual-tunnel")
        spec = importlib.util.spec_from_file_location("prepared_rebind", root / "scripts/rebind_release.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.promote_root(TARGET, manifest_path)
        for path in (root / "profiles").glob("*.json"):
            profile = self.load(path)
            self.assertEqual(profile["release"], TARGET)
            self.assertEqual(profile["server"]["status_schema_version"], 2)
            self.assertEqual(profile["server"]["checkpoint_mount_target"], "/checkpoints-v013")
            args = profile["server"]["arguments"]
            self.assertEqual(args[args.index("--binary-sha256") + 1],
                             manifest["components"]["ninfer"]["server_binary_sha256"])
            self.assertEqual(configuration_identity(profile), config)

    def test_prepared_draft_never_overwrites_an_existing_manifest(self) -> None:
        root = self.staging_copy(source_release=CURRENT)
        target = root / "releases" / TARGET
        target.mkdir()
        (target / "manifest.json").write_text('{"release":"already-staged"}')
        result = self.stage(root, None, source_release=CURRENT, dependency_args=["--prepared-draft"])
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(self.load(target / "manifest.json"), {"release": "already-staged"})

    def test_partial_invalid_or_duplicate_dependency_pins_fail_before_staging(self) -> None:
        root = self.staging_copy(source_release=CURRENT)
        manifest = self.load(root / "releases" / CURRENT / "manifest.json")
        variant = manifest["components"]["ninfer_variants"][-1]
        key = variant["id"]
        url = (f"https://github.com/alphastorm/ninfer/releases/download/"
               f"{variant['release_tag']}/{variant['package_name'].removesuffix('.tar.gz')}.cdx.json")
        valid = ["--sbom-dependency-url", f"{key}={url}",
                 "--sbom-dependency-sha256", f"{key}={'a' * 64}"]
        cases = (valid[:2], valid[2:],
                 valid[:2] + ["--sbom-dependency-sha256", f"{key}={'A' * 64}"],
                 ["--sbom-dependency-url", f"{key}=https://example.invalid/dependencies.json", *valid[2:]],
                 valid + valid[:2], ["--sbom-dependency-url", f"unknown={url}", *valid[2:]])
        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = self.stage(root, None, source_release=CURRENT, dependency_args=arguments)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertFalse((root / "releases" / TARGET).exists())

    def test_omitted_dependency_pins_preserve_an_existing_native_inventory(self) -> None:
        root = self.staging_copy(source_release=CURRENT)
        path = root / "releases" / CURRENT / "manifest.json"
        manifest = self.load(path)
        variant = manifest["components"]["ninfer_variants"][-1]
        variant.update(sbom_dependency_url=(
            f"https://github.com/alphastorm/ninfer/releases/download/"
            f"{variant['release_tag']}/{variant['package_name'].removesuffix('.tar.gz')}.cdx.json"),
            sbom_dependency_sha256="a" * 64)
        self.save(path, manifest)
        result = self.stage(root, None, source_release=CURRENT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        staged = self.load(root / "releases" / TARGET / "manifest.json")["components"]["ninfer_variants"][-1]
        for field in ("sbom_dependency_url", "sbom_dependency_sha256"):
            self.assertEqual(staged[field], variant[field])

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
        source_release = "v0.10.0"  # Explicit native baseline, independent of root scope.
        root = self.staging_copy(source_release=source_release)
        source = root / "releases" / source_release
        previous = self.load(source / "manifest.json")
        immutable = [root / "compatibility.json", *(root / "profiles").glob("*.json"),
                     *source.rglob("*")]
        before = {path: path.read_bytes() for path in immutable if path.is_file()}
        model = self.distinct_model(previous["components"]["model"])
        native = previous["components"].get("native_model", previous["components"]["model"])
        result = self.stage(root, None, source_release=source_release, model_args=self.model_arguments(model))
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

    def test_upstream_descriptor_allows_unpromoted_platform_root_pins(self) -> None:
        root = self.staging_copy()
        for path in (root / "profiles").glob("*.json"):
            profile = self.load(path)
            profile["status"] = "public"
            self.save(path, profile)
        result = self.stage(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[draft-posture] profile: client archive must match windows-x64 compatibility distribution", result.stdout)
        self.assertIn("[draft-posture] profiles/qwen38-rtx5090-manual-tunnel.json: client archive must match darwin-arm64 compatibility distribution", result.stdout)

    def test_unmodified_predecessor_stages_before_notes_and_evidence_are_rewritten(self) -> None:
        root = self.staging_copy(prepare_client_evidence=False)
        result = self.stage(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stderr, r"NINFER_RELEASE_NOTES\.md:\d+: retains predecessor OMP identity")
        self.assertFalse((root / "releases" / TARGET / "acceptance").exists())

    def test_older_source_with_newer_native_shape_still_requires_a_screen(self) -> None:
        root = self.staging_copy()
        later = root / "releases" / CURRENT
        shutil.copytree(ROOT / "releases" / CURRENT, later)
        manifest = self.load(later / "manifest.json")
        variant = next(row for row in manifest["components"]["ninfer_variants"]
                       if row["id"] == "rtx4090-windows-native")
        variant["runtime_shape"] = {
            "speculative_backend": "dflash2",
            "fit": {"device_state_slots": 0, "admission_headroom_mib": 640,
                    "draft_mlp_device_format": "Q4_G64_FP16", "token_embedding_residency": "host-mapped"}}
        self.save(later / "manifest.json", manifest)
        result = self.stage(root)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("rtx4090-windows-native.qualification.quality_screen is required", result.stdout)
        staged = self.load(root / "releases" / TARGET / "manifest.json")
        source = self.load(root / "releases" / SOURCE / "manifest.json")
        self.assertEqual(staged["components"]["ninfer_variants"][0]["package_sha256"],
                         source["components"]["ninfer_variants"][0]["package_sha256"])

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

    def test_staging_clears_predecessor_native_optional_evidence(self) -> None:
        root = self.staging_copy(source_release=CURRENT)
        source_path = root / "releases" / CURRENT / "manifest.json"
        source = self.load(source_path)
        for variant in source["components"]["ninfer_variants"]:
            for field in ("quality_screen", "t1_parity", "fit"):
                variant["qualification"][field] = {
                    "path": f"releases/{CURRENT}/qualification/old-{field}.json", "sha256": "0" * 64}
        self.save(source_path, source)
        result = self.stage(root, None, source_release=CURRENT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        staged = self.load(root / "releases" / TARGET / "manifest.json")
        for variant in staged["components"]["ninfer_variants"]:
            for field in ("quality_screen", "t1_parity", "fit"):
                self.assertNotIn(field, variant["qualification"])
        self.assertEqual(self.load(source_path), source)


if __name__ == "__main__":
    unittest.main()
