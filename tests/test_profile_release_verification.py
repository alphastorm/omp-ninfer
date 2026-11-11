"""The public native build profile must match the selected package and qualification."""
from __future__ import annotations

import json
import unittest

import test_bind_native_variant as binding
import test_native_candidate_policy as policy
import verify_release as verifier


class ProfileReleaseVerificationTests(unittest.TestCase):
    def test_packaged_profile_must_match_explicit_selected_variant(self):
        f = policy.NativeCandidateFitTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        f.prepare("rtx4090")
        profiles = {key: f"native-v0.8.0-beta.3{suffix}-rtx4090" for key, suffix in
                    (("default", ""), ("a8", "-a8"), ("tc", "-tc"), ("tc-a8", "-tc-a8"))}
        f.spec.update(build_profile=profiles["tc-a8"], build_profiles=profiles)
        f.evidence("release_spec", f.spec)
        f.variant["build_profile"] = profiles["tc-a8"]
        errors = []
        self.assertEqual(verifier.native_profile(f.root, "v0.16.0", f.variant, errors), f.configuration)
        self.assertEqual(errors, [])
        for profile in (profiles["default"], "uncommitted", None):
            with self.subTest(profile=profile):
                if profile is None:
                    f.variant.pop("build_profile", None)
                else:
                    f.variant["build_profile"] = profile
                errors = []
                self.assertIsNone(verifier.native_profile(f.root, "v0.16.0", f.variant, errors))
                self.assertTrue(any("build_profile" in error for error in errors), errors)

    def test_qualification_cannot_record_a_different_profile(self):
        f = binding.BindNativeVariantTest()
        f.setUp()
        self.addCleanup(f.doCleanups)
        variant = f.bind()
        variant["build_profile"] = "native-v0.6.1-beta.1-tc-a8-rtx4090"
        path = f.release_root / "rtx4090.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["identity"]["build_profile"] = "native-v0.6.1-beta.1-rtx4090"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        variant["qualification"]["sha256"] = verifier.sha256_file(path)
        errors = []
        verifier.validate_ninfer_variants(
            f.workspace, binding.RELEASE, [variant], {"runtime_variants": [variant]},
            f.receipt["model_sha256"], errors,
            incoming_checksums={variant["id"]: f.checksums_path})
        self.assertTrue(any("qualification build_profile" in error for error in errors), errors)
