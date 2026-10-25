"""Doctor fixtures never contact Docker, WSL, a GPU or a live model."""
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import doctor


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.model = self.root / "model.ninfer"
        self.model.write_bytes(b"synthetic model")
        self.omp = self.root / "omp"
        self.omp.write_bytes(b"synthetic binary")
        self.key = self.root / "bearer.key"
        self.key.write_text("fixture-not-a-credential\n")
        self.key.chmod(0o600)
        self.profile = self.root / "profile.json"
        self.profile.write_text(json.dumps({"transport": {"runtime_bind_host": "127.0.0.1", "runtime_port": 18089},
            "runtime_host": {"minimum_runtime_memory_mib": 28672, "minimum_vram_mib": 32607},
            "server": {"container_network_mode": "bridge", "published_bind_host": "127.0.0.1", "published_port": 18089,
                       "arguments": ["--host-kv-mib", "16384"]}}))
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps({"product": {"profile": "profile.json"}, "components": {
            "omp": {"platform": "darwin-arm64", "binary_sha256": doctor.digest(self.omp)},
            "model": {"artifact_bytes": self.model.stat().st_size, "artifact_sha256": doctor.digest(self.model)}}}))
        self.args = argparse.Namespace(manifest=self.manifest, lane="rtx5090", profile=None, release_spec=None,
            model=self.model, hash_model=True, key_file=self.key, omp=self.omp, client_platform="darwin-arm64",
            offline=True, running=False, gpu_uuid=None, container=None)

    def result(self):
        with patch.object(doctor, "run", side_effect=AssertionError("offline spawned a command")), \
             patch.object(doctor, "powershell", return_value="true"), \
             patch.object(doctor.socket, "create_connection", side_effect=AssertionError("offline opened a socket")):
            return doctor.diagnose(self.args)

    def check(self, result, name):
        return next(check for check in result["checks"] if check["name"] == name)

    def test_offline_checks_files_but_never_claims_hardware(self):
        result = self.result()
        self.assertEqual(result["status"], "offline")
        self.assertFalse(result["hardware_checked"])
        self.assertEqual(self.check(result, "omp_hash")["status"], "pass")
        self.assertEqual(self.check(result, "model_sha256")["status"], "pass")
        self.assertNotIn(str(self.root), json.dumps(result))
        self.assertNotIn(self.key.read_text().strip(), json.dumps(result))

    def test_hashes_and_missing_model_have_named_causes(self):
        self.omp.write_bytes(b"modified client")
        self.model.write_bytes(b"wrong model")
        result = self.result()
        for name in ("omp_hash", "model_bytes", "model_sha256"):
            check = self.check(result, name)
            self.assertEqual(check["status"], "fail")
            self.assertTrue(check["cause"] and check["remediation"])
        self.model.unlink()
        self.assertEqual(self.check(self.result(), "model_file")["status"], "fail")

    def test_model_hash_is_opt_in(self):
        self.args.hash_model = False
        result = self.result()
        self.assertEqual(self.check(result, "model_sha256")["status"], "skipped")

    @unittest.skipIf(os.name == "nt", "POSIX mode/owner fixture")
    def test_bearer_permissions_refuse_world_readable_empty_and_symlink(self):
        self.assertTrue(doctor.bearer_private(self.key))
        self.key.chmod(0o644)
        self.assertFalse(doctor.bearer_private(self.key))
        result = self.result()
        self.assertEqual(self.check(result, "bearer_permissions")["status"], "fail")
        self.key.chmod(0o600)
        link = self.root / "link"
        link.symlink_to(self.key)
        self.assertFalse(doctor.bearer_private(link))
        self.key.write_text("")
        self.assertFalse(doctor.bearer_private(self.key))

    def test_host_network_and_non_loopback_are_named_failures(self):
        profile = doctor.load(self.profile)
        profile["server"]["container_network_mode"] = "host"
        profile["transport"]["runtime_bind_host"] = "0.0.0.0"
        self.profile.write_text(json.dumps(profile))
        result = self.result()
        self.assertIn("issue #15", self.check(result, "docker_network_mode")["cause"])
        self.assertEqual(self.check(result, "loopback_profile")["status"], "fail")
        bridge = {"HostConfig": {"NetworkMode": "bridge", "PortBindings": {"8080/tcp": [
            {"HostIp": "127.0.0.1", "HostPort": "18089"}]}}}
        self.assertTrue(doctor.inspect_network(bridge, 18089))
        bridge["HostConfig"]["NetworkMode"] = "host"
        self.assertFalse(doctor.inspect_network(bridge, 18089))
        self.assertTrue(doctor.loopback_only(["127.0.0.1", "::1"]))
        self.assertFalse(doctor.loopback_only(["*", "0.0.0.0"]))

    def test_profile_floors_preserve_total_vs_free_memory(self):
        limits = doctor.thresholds(doctor.load(self.profile))
        self.assertEqual(limits["ram_total_mib"], 28672)
        self.assertEqual(limits["ram_free_mib"], 16384)
        self.assertEqual(limits["vram_total_mib"], 32607)
        self.assertEqual(limits["vram_free_mib"], 0)
        native = doctor.thresholds({"runtime_host": {"minimum_runtime_memory_mib": 32768},
                                    "context_cache": {"host_kv_mib": 11264}}, {"gpu": {"minimum_driver_major": 590}})
        self.assertEqual(native["ram_total_mib"], 32768)
        self.assertEqual(native["ram_free_mib"], 11264)
        self.assertEqual(native["driver_major"], 590)
        self.assertEqual(doctor.memory_info("MemTotal: 29360128 kB\nMemAvailable: 16777216 kB\n"),
                         {"total": 28672, "free": 16384})

    def test_gpu_selection_driver_and_memory_use_only_selected_uuid(self):
        rows = doctor.parse_gpu("GPU-one, NVIDIA GeForce RTX 5090, 579.99, 32607, 1024\nGPU-two, NVIDIA GeForce RTX 5090, 621.01, 32607, 30000")
        limits = doctor.thresholds(doctor.load(self.profile))
        limits["vram_free_mib"] = 28000
        ambiguous = doctor.assess_gpu(rows, "NVIDIA GeForce RTX 5090", None, limits)
        self.assertFalse(ambiguous[0][1])
        selected = doctor.assess_gpu(rows, "NVIDIA GeForce RTX 5090", "GPU-one", limits)
        self.assertFalse(next(row for row in selected if row[0] == "driver_floor")[1])
        self.assertFalse(next(row for row in selected if row[0] == "vram_free_mib")[1])
        selected = doctor.assess_gpu(rows, "NVIDIA GeForce RTX 5090", "GPU-two", limits)
        self.assertTrue(all(row[1] for row in selected))

    def test_native_requires_real_package_inputs_not_container_defaults(self):
        self.args.lane = "rtx4090"
        result = self.result()
        self.assertEqual(self.check(result, "native_profile")["status"], "fail")
        self.assertEqual(self.check(result, "native_spec")["status"], "fail")

    def test_json_cli_bad_profile_is_named_failure(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = doctor.main(["--manifest", str(self.root / "missing.json"), "--offline", "--json"])
        self.assertEqual(code, 1)
        receipt = json.loads(output.getvalue())
        self.assertEqual(receipt["checks"][0]["name"], "profile_input")
        self.assertNotIn(str(self.root), output.getvalue())


if __name__ == "__main__":
    unittest.main()
