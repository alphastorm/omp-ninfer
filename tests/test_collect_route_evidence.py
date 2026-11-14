"""The collector consumes driver verdicts, never guesses acceptance or component provenance."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


COLLECT = module("collect_route_evidence", ROOT / "scripts/collect_route_evidence.py")
FIXTURES = module("acceptance_fixtures", ROOT / "tests/acceptance_fixtures.py")
from release_io import atomic_write, atomic_write_json, git


def leaves(value, path=()):
    if isinstance(value, dict):
        return {key: child for name, item in value.items()
                for key, child in leaves(item, (*path, name)).items()}
    if isinstance(value, list):
        return {key: child for index, item in enumerate(value)
                for key, child in leaves(item, (*path, index)).items()}
    return {path: value}


# Historical prose exceptions are exhaustive, not a wildcard over prose or native evidence.
# In particular the two false source/cut claims are recorded verbatim, not silently normalized.
GOLDEN_PROSE = {
    ("documented_routes", "scope"): "All five fresh candidate-bound documented routes, three stock OMP 18.20.0 clients, both newly cut beta.4 native public installs, and candidate-profile native probes. Linux is WSL2-scoped; macOS remains preview. Native component qualification binds the current one-source N cuts; no prior product-route or client acceptance is carried.",
    ("documented_routes", "mode"): "Fresh v0.19.0 acceptance on 6b22f219c7298db4b8fa5c2bc7bb33eb7a37799f; both promoted beta.4 native lanes and the incumbent production service restored after final windows.",
    ("restoration", "rtx4090", "scope"): "Restored the same promoted beta.4 stopped canonical root and stage; any pre-existing preserved lineages remain untouched.",
    ("restoration", "rtx3090", "scope"): "Restored the same promoted beta.4 stopped canonical root and stage; any pre-existing preserved lineages remain untouched.",
    ("rtx4090", "preparation", "documented_install"): "Fresh temporary first-lineage install; the promoted beta.4 canonical root and documented stage were preserved and restored. Separate public-URL installer acceptance followed on that same canonical package. Canonical promotion preceded acceptance; its preserved beta.3 lineage remains untouched.",
    ("rtx3090", "preparation", "documented_install"): "Fresh temporary first-lineage install; the promoted beta.4 canonical root and documented stage were preserved and restored. Separate public-URL installer acceptance followed on that same canonical package. Canonical promotion preceded acceptance; its preserved beta.3 lineage remains untouched.",
    ("rtx4090", "preparation", "public_install_model_reference"): "Manifest-bound published v3 model; no predecessor checkpoint import.",
    ("rtx3090", "preparation", "public_install_model_reference"): "Manifest-bound published v3 model; no predecessor checkpoint import.",
    ("rtx4090", "limitations", 2): "No native vision or additional runtime performance claim; exact-source component qualification remains separate.",
    ("rtx3090", "limitations", 2): "No native vision or additional runtime performance claim; exact-source component qualification remains separate.",
    ("composed", "linux_live_client", "scope"): "Fresh stock OMP 18.20.0 Linux x64 client under WSL2; no separate native Linux OS or Linux vision claim.",
    ("composed", "mode"): "Fresh five-route acceptance on frozen v0.19.0 candidate 6b22f219c7298db4b8fa5c2bc7bb33eb7a37799f, new beta.4 native packages and published RTX 5090 candidate runtime; both canonical native lanes and the same incumbent production container restored.",
    ("composed", "client_note"): "Every stock OMP 18.20.0 client was freshly downloaded and accepted against the candidate-bound selected runtime identities; all three runtime components were rebuilt from one N source.",
    ("composed", "runtime_qualification", "rtx5090-container", "scope"): "Current exact-source published candidate component qualification; fresh acceptance additionally binds exact runtime identity.",
    ("composed", "runtime_qualification", "rtx3090-windows-native", "scope"): "Current exact-source published beta.4 component qualification; fresh OMP 18.20.0 route/public-install/probe acceptance and restored promoted canonical instance.",
    ("composed", "runtime_qualification", "rtx4090-windows-native", "scope"): "Current exact-source published beta.4 component qualification; fresh OMP 18.20.0 route/public-install/probe acceptance and restored promoted canonical instance.",
}


class CollectorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "repository"
        self.root.mkdir()
        previous = FIXTURES.predecessor(ROOT)
        current = previous["release"]
        major, minor, _ = COLLECT.composer.product_version(current)
        self.release = f"v{major}.{minor + 1}.0"
        directory = self.root / "releases" / self.release
        shutil.copytree(ROOT / "releases" / current, directory)
        atomic_write_json(self.root / "releases" / current / "manifest.json",
                          COLLECT.load(ROOT / "releases" / current / "manifest.json"))
        manifest = json.loads((directory / "manifest.json").read_text().replace(
            f"releases/{current}/", f"releases/{self.release}/"))
        manifest.update(release=self.release, status="candidate")
        atomic_write_json(directory / "manifest.json", manifest)
        authority = COLLECT.load(ROOT / "releases" / current / "compatibility.json")
        authority["product_release"] = self.release
        atomic_write_json(self.root / "compatibility.json", authority)
        atomic_write(self.root / "docs/QUICKSTART.md", (ROOT / "docs/QUICKSTART.md").read_bytes())
        git(self.root, "init", "--quiet")
        git(self.root, "config", "user.name", "Synthetic Test")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "add", "--", "compatibility.json")
        git(self.root, "commit", "--quiet", "-m", "test: initialize synthetic candidate")
        self.candidate = git(self.root, "rev-parse", "HEAD").strip()
        self.windows = Path(temporary.name) / "windows"
        self.outputs = FIXTURES.write_fixtures(self.root, self.release, self.candidate, self.windows)
        self.plan = COLLECT.load(self.windows / "plan.json")
        self.destination = Path(temporary.name) / "collected/evidence.json"

    def collect(self, **kwargs):
        return COLLECT.collect(self.root, self.release, self.candidate,
                                self.windows, self.plan, **kwargs)

    def change(self, name, mutate):
        path = self.windows / name
        value = COLLECT.load(path)
        mutate(value)
        atomic_write_json(path, value)
        if "/evidence/" in name and path.name in ("window.json", "restoration.json", "final-audit.json"):
            collection_path = path.parent.parent / "driver-collection.json"
            collection = COLLECT.load(collection_path)
            key = {"window.json": "window_sha256", "restoration.json": "restoration_sha256",
                   "final-audit.json": "final_audit_sha256"}[path.name]
            collection[key] = COLLECT.digest(path)
            atomic_write_json(collection_path, collection)

    def assert_refused_without_writes(self, pattern, **kwargs):
        atomic_write(self.destination, b"previous evidence\n")
        with self.assertRaisesRegex(SystemExit, pattern):
            COLLECT.write_evidence(self.root, self.release, self.candidate, self.windows,
                                   self.plan, self.destination, **kwargs)
        self.assertEqual(self.destination.read_bytes(), b"previous evidence\n")
        self.assertFalse((self.destination.parent / "receipts").exists())

    def test_fixture_evidence_round_trips_and_receipts_keep_the_original_bytes(self):
        evidence, sources = self.collect()
        self.assertEqual(evidence, COLLECT.load(Path(self.outputs["evidence"])))
        result = COLLECT.write_evidence(self.root, self.release, self.candidate,
                                        self.windows, self.plan, self.destination)
        self.assertEqual(evidence, COLLECT.load(self.destination))
        self.assertEqual(set(result["routes"]), set(COLLECT.composer.documented_route.LANES))
        for lane, path in result["routes"].items():
            self.assertEqual(Path(path).name, lane + "-run.json")
            self.assertEqual(Path(path).read_bytes(), sources[lane].read_bytes())

    def test_platform_statuses_are_owned_by_the_plan_not_the_old_evidence(self):
        selected = ("qualified" if self.plan["platforms"]["darwin-remote-ssh"] == "preview"
                    else "preview")
        self.plan["platforms"]["darwin-remote-ssh"] = selected
        evidence, _ = self.collect()
        self.assertEqual(evidence["platforms"]["darwin-remote-ssh"]["status"], selected)
        for change in (
            lambda value: value["platforms"].pop("darwin-remote-ssh"),
            lambda value: value["platforms"].update(extra="qualified"),
            lambda value: value["platforms"].update({"darwin-remote-ssh": "passed"}),
        ):
            original = deepcopy(self.plan)
            change(self.plan)
            self.assert_refused_without_writes("plan.platforms")
            self.plan = original

    def test_failed_container_window_is_refused(self):
        self.change("rtx5090/final-summary.json", lambda value: value.update(status="failed"))
        self.assert_refused_without_writes("container window failed")

    def test_failed_native_window_is_refused(self):
        self.change("rtx3090/driver-window.json", lambda value: value.update(status="failed"))
        self.assert_refused_without_writes("native window failed")

    def test_uncollected_container_window_is_refused(self):
        self.change("rtx5090/collection.json", lambda value: value.update(missing=["route.json"]))
        self.assert_refused_without_writes("uncollected")

    def test_uncollected_native_window_is_refused(self):
        self.change("rtx4090/driver-collection.json", lambda value: value.update(status="pending"))
        self.assert_refused_without_writes("uncollected")

    def test_collection_digest_drift_is_refused(self):
        self.change("rtx4090/driver-collection.json", lambda value: value.update(restoration_sha256="0" * 64))
        self.assert_refused_without_writes("collected bytes")

    def test_unrestored_native_window_is_refused(self):
        self.change("rtx3090/evidence/restoration.json",
                    lambda value: value["checks"].update(task_ready=False))
        self.assert_refused_without_writes("checks did not all pass")

    def test_failed_final_audit_is_refused(self):
        self.change("rtx4090/evidence/final-audit.json", lambda value: value.update(status="failed"))
        self.assert_refused_without_writes("status is not passed")

    def test_unrestored_production_service_is_refused(self):
        self.change("production-and-fleet-after.json", lambda value: value.update(same_image=False))
        self.assert_refused_without_writes("production service is unrestored")

    def test_native_census_or_holds_drift_is_refused(self):
        self.change("native-final.json", lambda value: value["lanes"][0].update(state_sha256="0" * 64))
        self.assert_refused_without_writes("census or client files are unrestored")

    def test_failed_public_install_is_refused(self):
        self.change("rtx4090/public-install.json", lambda value: value.update(status="failed"))
        self.assert_refused_without_writes("public install failed")

    def test_a_route_from_another_candidate_is_refused(self):
        self.change("rtx5090/mac-route.json", lambda value: value.update(clone_commit="0" * 40))
        self.assert_refused_without_writes("not candidate")

    def test_a_missing_required_output_is_refused(self):
        (self.windows / "rtx3090/evidence/behavior-evidence.json").unlink()
        self.assert_refused_without_writes("cannot read behavior-evidence")

    def test_a_selected_lane_directory_overrides_the_default_without_guessing_its_name(self):
        selected = self.windows.parent / "selected/attempt-7"
        selected.parent.mkdir()
        shutil.move(str(self.windows / "rtx3090"), selected)
        self.assert_refused_without_writes("cannot read driver-window")
        evidence, routes = self.collect(lane_dirs={"rtx3090": selected})
        self.assertEqual(routes["rtx3090-native"], selected / "evidence/route.json")
        self.assertEqual(evidence["rtx3090"]["release"], self.release)
        self.assertEqual(evidence["restoration"]["rtx3090"]["sources"][0]["evidence_name"],
                         "rtx3090/evidence/restoration.json")

    def test_corrected_attempt_requires_an_explicit_failed_restored_prior(self):
        prior = self.windows.parent / "prior"
        shutil.copytree(self.windows / "rtx3090", prior)
        self.change("rtx3090/driver-window.json", lambda value: value["plan"].update(attempt=2))
        self.change("rtx3090/evidence/window.json", lambda value: value.update(attempt=2))
        self.assert_refused_without_writes("corrected attempt requires explicit")
        self.assert_refused_without_writes("failed and restored", corrected={"rtx3090": prior})
        window = COLLECT.load(prior / "evidence/window.json")
        window.update(status="failed", first_failing_boundary="native-probes")
        atomic_write_json(prior / "evidence/window.json", window)
        collection = COLLECT.load(prior / "driver-collection.json")
        collection["window_sha256"] = COLLECT.digest(prior / "evidence/window.json")
        atomic_write_json(prior / "driver-collection.json", collection)
        evidence, _ = self.collect(corrected={"rtx3090": prior})
        self.assertIn("explicitly selected corrected attempt", evidence["composed"]["limitations"][-1])

    def test_waiver_is_not_inferred_and_requires_an_explicit_bound_recovery(self):
        self.assert_refused_without_writes(
            "explicit lead restoration", waivers={"rtx3090": self.root / "waiver.json"})

    def prepare_waiver(self, failed_phase):
        from test_native_candidate_policy import probe_receipts
        folder = self.windows / "rtx3090"
        body = COLLECT.load(folder / "evidence/behavior-evidence.json")
        manifest = COLLECT.load(self.root / "releases" / self.release / "manifest.json")
        variant = next(row for row in manifest["components"]["ninfer_variants"]
                       if row["id"] == "rtx3090-windows-native")
        probes = probe_receipts(variant, body["runtime_configuration"])
        def bind_identity(value):
            if isinstance(value, dict):
                if {"binary_sha256", "config_sha256", "model_artifact_sha256"} <= value.keys():
                    value["build_profile"] = variant["build_profile"]
                if "omp" in value:
                    value["omp"].update(sha256=body["client"]["binary_sha256"],
                                        version=body["client"]["version"])
                for child in value.values():
                    bind_identity(child)
            elif isinstance(value, list):
                for child in value:
                    bind_identity(child)
        bind_identity(probes)
        if failed_phase == "native-probes":
            probes["compaction"].update(passed=False, checks={}, compactions=[],
                                         error="RuntimeError: timed out after 900 s")
        for name, probe in probes.items():
            atomic_write_json(folder / "evidence" / (name + "-probe.json"), probe)
        atomic_write_json(folder / "evidence/expected-runtime.json",
                          {"configuration": body["runtime_configuration"]})
        self.change("rtx3090/driver-window.json", lambda value: value.update(status="failed"))
        self.change("rtx3090/evidence/window.json",
                    lambda value: value.update(status="failed", restoration_status="failed",
                                                first_failing_boundary=failed_phase))
        failure = folder / "evidence/window-failure.json"
        atomic_write_json(failure, {
            "boundary": failed_phase,
            "error": ("native profile acceptance probes failed" if failed_phase == "native-probes" else
                      "incomplete shutdown: 1 live session(s) refused; preserve candidate checkpoints and reconcile before rollback"),
        })
        (folder / "public-install.json").unlink()
        output = folder / "lead-restoration.out"
        atomic_write_json(output, {"last_stop": {"outcome": "graceful", "sessions_refused": 0}})
        proof = folder / "lead-restoration.json"
        atomic_write_json(proof, {
            "candidate_commit": self.candidate, "lane": "rtx3090-native", "status": "restored-by-lead",
            "census_equal": True, "holds_client_files_equal": True, "failed_evidence_unchanged": True,
            "checks": {"runtime_record_absent": True, "gpu_owner_lease_absent": True},
        })
        route = folder / "evidence/route.json"
        waiver = FIXTURES.campaign_waiver(self.release, self.candidate, COLLECT.digest(route),
                                         failed_phase=failed_phase)
        waiver["restoration_summary"]["power_limit_w"] = 300
        waiver.update(application_rule="This decision applies only to the observed failed native campaign.",
                      disclosure_required="Native campaign failed; documented blocks passed.")
        waiver["evidence_sha256"].update({
            "window-failure.json": COLLECT.digest(failure),
            "driver-window.json": COLLECT.digest(folder / "driver-window.json"),
            "lead-restoration.out": COLLECT.digest(output), "lead-restoration.json": COLLECT.digest(proof),
            "pre-window-census.json": COLLECT.digest(self.windows / "native-pre-window-census.json"),
        })
        if failed_phase == "native-probes":
            waiver["evidence_sha256"]["compaction-probe.json"] = COLLECT.digest(
                folder / "evidence/compaction-probe.json")
            waiver["probe_projection_sha256"]["compaction"] = COLLECT.native_probe_summary(probes)["compaction"]["sha256"]
        path = self.root / "releases" / self.release / "qualification/rtx3090-route-waiver.json"
        atomic_write_json(path, waiver)
        return {"waivers": {"rtx3090": path}, "recoveries": {"rtx3090": output},
                "recovery_proofs": {"rtx3090": proof}}

    def assert_waived_failure(self, phase):
        arguments = self.prepare_waiver(phase)
        evidence, _ = self.collect(**arguments)
        self.assertEqual(evidence["rtx3090"]["status"], "failed")
        self.assertNotIn("public_install", evidence["rtx3090"]["observations"])
        self.assertEqual(evidence["restoration"]["rtx3090"]["status"], "restored-by-lead")
        self.assertIn("founder-waived", evidence["composed"]["qualification_note"])
        proof = arguments["recovery_proofs"]["rtx3090"]
        value = COLLECT.load(proof)
        value["checks"]["gpu_owner_lease_absent"] = False
        atomic_write_json(proof, value)
        self.assert_refused_without_writes("bind both lead restoration", **arguments)

    def test_structured_outage_waiver_preserves_failure_and_bound_lead_recovery(self):
        self.assert_waived_failure("structured-outage")

    def test_native_probes_waiver_preserves_failure_and_bound_lead_recovery(self):
        self.assert_waived_failure("native-probes")

    def test_container_corrected_attempt_is_explicit_and_retains_both_hold_times(self):
        prior = self.windows.parent / "container-prior"
        shutil.copytree(self.windows / "rtx5090", prior)
        (prior / "final-summary.json").unlink()
        atomic_write_json(prior / "window-attempt.json", {"attempt": "initial"})
        atomic_write_json(prior / "first-failure.json", {"boundary": "documented route failed"})
        self.change("rtx5090/final-summary.json",
                    lambda value: value.update(corrections=[{"route": "host", "change": "Restored route precondition."}]))
        self.assert_refused_without_writes("requires explicit input")
        evidence, _ = self.collect(corrected={"rtx5090": prior})
        self.assertEqual(evidence["restoration"]["rtx5090"]["window_hold_seconds"], [1.0, 1.0])
        self.assertEqual(evidence["restoration"]["rtx5090"]["production_windows"], 2)

    def test_all_descriptive_output_is_claim_free_and_has_no_component_identity(self):
        evidence, _ = self.collect()
        claims = re.compile(r"\b(?:rebuilt|re-?cut|newly cut|one.source|same.source|single.source|carried|promoted)\b"
                            r"|\bnew\b.*\bpackage", re.I)
        for path, value in leaves(evidence).items():
            if not isinstance(value, str) or not re.search(r"\s", value):
                continue
            self.assertIsNone(claims.search(value), path)
            self.assertNotIn(self.candidate, value, path)

    def test_cli_hands_the_driver_an_explicit_receipt_map(self):
        shutil.copytree(ROOT / "scripts", self.root / "scripts")
        result = subprocess.run([
            sys.executable, "scripts/collect_route_evidence.py", "--release", self.release,
            "--candidate", self.candidate, "--window-root", str(self.windows),
            "--plan", str(self.windows / "plan.json"), "--output", str(self.destination),
            "--receipts-dir", str(self.destination.parent / "route-inputs"),
            "--lane-dir", "rtx3090=" + str(self.windows / "rtx3090"),
        ], cwd=self.root, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        outputs = json.loads(result.stdout)
        self.assertEqual(len(outputs["routes"]), 5)
        self.assertEqual(Path(outputs["routes"]["rtx3090-native"]).parent.name, "route-inputs")


class PrivateCollectorGoldenTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("OMP_NINFER_PRIVATE_FIXTURES"),
                         "private fixture locations are not configured")
    def test_retained_window_outputs_match_except_the_enumerated_historical_prose(self):
        locations = COLLECT.load(Path(os.environ["OMP_NINFER_PRIVATE_FIXTURES"]).expanduser())["v0.19.0"]
        plan = {"artifact_type": "omp_ninfer_release_plan", "schema_version": 1, "release": "v0.19.0",
                "platforms": FIXTURES.ACCEPTED}
        with tempfile.TemporaryDirectory() as temporary:
            public_tree = Path(temporary) / "public-tag"
            FIXTURES.public_release_tree(ROOT, "v0.19.0", public_tree)
            actual, routes = COLLECT.collect(public_tree, "v0.19.0", locations["candidate"],
                                             Path(locations["window_root"]).expanduser(), plan)
        expected_path = Path(locations["composition_evidence"]).expanduser()
        expected = COLLECT.load(expected_path)
        self.assertEqual((json.dumps(expected, indent=2) + "\n").encode(), expected_path.read_bytes())
        left, right = leaves(expected), leaves(actual)
        self.assertEqual(set(left), set(right))
        differences = {path for path in left if left[path] != right[path]}
        self.assertEqual(differences, set(GOLDEN_PROSE))
        for path, sentence in GOLDEN_PROSE.items():
            self.assertIsInstance(right[path], str, path)
            self.assertEqual(left[path], sentence, path)
            current = expected
            for key in path[:-1]:
                current = current[key]
            current[path[-1]] = right[path]
        self.assertEqual((json.dumps(actual, indent=2) + "\n").encode(),
                         (json.dumps(expected, indent=2) + "\n").encode())
        self.assertEqual(set(routes), set(COLLECT.composer.documented_route.LANES))


if __name__ == "__main__":
    unittest.main()
