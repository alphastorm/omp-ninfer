"""Native public-install runtime records retain the selected build variant."""
from __future__ import annotations

import unittest

import test_compose_route_acceptance as fixture


class ProfileRouteCompositionTests(unittest.TestCase):
    def test_public_install_runtime_retains_package_selected_profile(self):
        f = fixture.UpstreamCompositionTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        module = fixture.MODULE
        manifest = module.load(f.release_root / "manifest.json")
        variant = manifest["components"]["ninfer_variants"][0]
        profiles = {key: f"native-v0.8.0-beta.3{suffix}-rtx4090" for key, suffix in
                    (("default", ""), ("a8", "-a8"), ("tc", "-tc"), ("tc-a8", "-tc-a8"))}
        selected = profiles["tc-a8"]
        variant["build_profile"] = selected
        reference = variant["qualification"]["release_spec"]
        path = f.root / reference["path"]
        spec = module.load(path)
        spec.update(build_profile=selected, build_profiles=profiles)
        module.save(path, spec)
        reference["sha256"] = module.sha256(path.read_bytes())
        module.save(f.release_root / "manifest.json", manifest)
        path = f.root / "evidence.json"
        evidence = module.load(path)
        evidence["rtx4090"]["probe_acceptance"]["fleet"]["identity"]["build_profile"] = selected
        module.save(path, evidence)
        self.assertEqual(f.compose(), 0)
        receipt = module.load(f.release_root / "acceptance/rtx4090-public-install.json")
        self.assertEqual(receipt["runtime"].get("build_profile"), selected)
        self.assertEqual(receipt["probe_acceptance"]["fleet"]["identity"].get("build_profile"), selected)
