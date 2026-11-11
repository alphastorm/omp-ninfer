"""Selected native build profiles originate in authenticated package receipts."""
from __future__ import annotations

import hashlib
import io
import json
import tarfile
import unittest

import test_bind_native_variant as fixture
from test_native_candidate_policy import candidate_profile


class ProfileVariantBindingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.BindNativeVariantTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def select(self, lane):
        f = self.fixture
        profile = f"native-v0.8.0-beta.3-tc-a8-{lane}"
        f.receipt["build_profile"] = profile
        f.write_receipt()
        f.entries["package-build-receipt.json"] = f.receipt_digest
        f.write_checksums()
        path = f.write_lane_receipt()
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["identity"]["build_profile"] = profile
        path.write_text(json.dumps(receipt), encoding="utf-8")
        return profile

    def test_manifest_copies_receipt_profile_not_predecessor(self):
        f = self.fixture
        profile = self.select("rtx4090")
        f.manifest["components"]["ninfer_variants"][-1]["build_profile"] = "stale-default"
        self.assertEqual(f.bind().get("build_profile"), profile)

    def test_new_lane_public_mirrors_retain_selected_profile(self):
        f = self.fixture
        f.prepare_3090()
        profile = self.select("rtx3090")
        variant = f.add_3090(add=True)
        variant["build_profile"] = profile
        release = f.release_root.parent
        (release / "compatibility.json").write_text(json.dumps({"runtime_variants": []}), encoding="utf-8")
        (release / "qualification.json").write_text(json.dumps({"composition": {}}), encoding="utf-8")
        fixture.BINDER.add_lane_rows(fixture.RELEASE, variant)
        authority = json.loads((release / "compatibility.json").read_text(encoding="utf-8"))
        qualification = json.loads((release / "qualification.json").read_text(encoding="utf-8"))
        self.assertEqual(authority["runtime_variants"][0].get("build_profile"), profile)
        self.assertEqual(qualification["composition"]["native_runtime_variants"][variant["id"]].get(
            "build_profile"), profile)

    def test_packaged_spec_and_receipt_cannot_select_different_allowlisted_profiles(self):
        f = self.fixture
        spec, config, _ = candidate_profile("rtx4090")
        profiles = {key: f"native-v0.8.0-beta.3{suffix}-rtx4090" for key, suffix in
                    (("default", ""), ("a8", "-a8"), ("tc", "-tc"), ("tc-a8", "-tc-a8"))}
        spec.update(build_profiles=profiles, build_profile=profiles["tc"])
        package = f.workspace / "profile.tar.gz"
        config_bytes = json.dumps(config).encode()
        with tarfile.open(package, "w:gz") as archive:
            for name, data in (("server-config.json", config_bytes),
                               ("release-spec.json", json.dumps(spec).encode())):
                member = tarfile.TarInfo("payload/" + name)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
        receipt = {"lane": "rtx4090", "build_profile": profiles["a8"],
                   "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
                   "package": {"sha256": fixture.BINDER.sha256_file(package)}}
        with self.assertRaisesRegex(fixture.BINDER.BindError, "build_profile"):
            fixture.BINDER.package_metadata(package, receipt)
