import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class QuickstartReleaseTargetsTest(unittest.TestCase):
    def test_executable_release_store_and_client_targets_follow_root_authority(self):
        release = json.loads((ROOT / 'compatibility.json').read_text())['product_release']
        descriptor = json.loads((ROOT / 'releases' / release / 'qualification/client-components.json').read_text())
        profile = json.loads((ROOT / 'releases' / release / 'profiles/qwen38-rtx5090-manual-tunnel.json').read_text())
        store = profile['server']['checkpoint_host_directory']
        document = (ROOT / 'docs/QUICKSTART.md').read_text()
        blocks = re.findall(r'^```[^\n]*\n(.*?)^```', document, re.MULTILINE | re.DOTALL)
        for block in blocks:
            targets = re.findall(r'(?:releases[/\\]|--branch\s+|--release\s+)(v\d+\.\d+\.\d+)', block)
            self.assertTrue(all(value == release for value in targets), targets)
            self.assertTrue(all(value == store for value in re.findall(r'checkpoints-v\d+(?:-\d+)?', block)))
        for platform in ('windows-x64', 'darwin-arm64'):
            row = descriptor['platforms'][platform]
            matches = [block for block in blocks if row['asset_name'] in block and '/releases/download/' in block]
            self.assertEqual(len(matches), 1, platform)
            self.assertIn(row['asset_url'], matches[0])
            self.assertIn(row['asset_sha256'], matches[0])


if __name__ == '__main__':
    unittest.main()
