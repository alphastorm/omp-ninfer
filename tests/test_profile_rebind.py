"""Rebinding preserves package-selected native build profiles in public authority."""
from __future__ import annotations

import unittest

import test_rebind_release as fixture


class ProfileRebindTests(unittest.TestCase):
    def test_rebind_carries_selected_profile_into_authority_and_qualification(self):
        f = fixture.PromoteRootTests()
        self.addCleanup(f.doCleanups)
        root, module = f.promotion_copy()
        release = root / "releases" / fixture.CURRENT
        path = release / "manifest.json"
        manifest = f.load(path)
        selected = {}
        for variant in manifest["components"]["ninfer_variants"]:
            lane = variant["id"].split("-")[0]
            selected[variant["id"]] = f"native-v0.8.0-beta.3-tc-a8-{lane}"
            variant["build_profile"] = selected[variant["id"]]
        module.save(path, manifest)
        module.bind_lane_receipts(fixture.CURRENT, release / "compatibility.json", path,
                                  release / "qualification.json")
        authority = f.load(release / "compatibility.json")
        qualification = f.load(release / "qualification.json")
        for variant in authority["runtime_variants"]:
            self.assertEqual(variant.get("build_profile"), selected[variant["id"]])
        for variant_id, row in qualification["composition"]["native_runtime_variants"].items():
            self.assertEqual(row.get("build_profile"), selected[variant_id])
