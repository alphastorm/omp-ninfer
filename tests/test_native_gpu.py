"""Installed-card selection and host-side helper plumbing, without a host operation."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOSTS = ROOT / "scripts/hosts"


class NativeGpuTests(unittest.TestCase):
    def test_all_probe_entrypoints_load_the_same_helper(self) -> None:
        for filename in ("accept-native-public-install.ps1", "accept-rtx4090-route.ps1"):
            with self.subTest(filename=filename):
                text = (HOSTS / filename).read_text()
                self.assertIn("'native-gpu.ps1'", text)
                self.assertIn("Resolve-NativeGpuUuid $StateRoot", text)
        campaign = (HOSTS / "variant_campaign.py").read_text()
        self.assertIn('"--gpus", "device=" + plan["gpu_uuid"]', campaign)
        self.assertIn('CUDA_VISIBLE_DEVICES=self.plan["gpu_uuid"]', campaign)
        driver = (HOSTS / "accept-rtx4090-route.py").read_text()
        self.assertIn('gpu_helper = scripts / "native-gpu.ps1"', driver)
        self.assertIn('preflight["gpu_helper_sha256"] != sha(gpu_helper)', driver)
        public = (HOSTS / "accept-native-public-install.ps1").read_text()
        self.assertIn("$installArgs.GpuUuid = $gpuUuid", public)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is needed for installed-card selection")
    def test_uuid_binding_and_legacy_multi_gpu_refusal(self) -> None:
        proof = r'''
param($Helper, $Scratch)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. ([scriptblock]::Create([IO.File]::ReadAllText($Helper)))
$global:cards=@('card-zero','card-one');$global:calls=@()
function nvidia-smi.exe {
    $global:calls+=($args -join ' ');$global:LASTEXITCODE=0
    if($args -contains '--query-gpu=uuid'){return $global:cards}
    if($args -contains '--query-gpu=power.limit'){return '450'}
    throw 'unexpected NVIDIA operation'
}
function State($release) {
    @{active_release='active';releases=@{active=$release}}|ConvertTo-Json -Depth 5|Set-Content (Join-Path $Scratch 'state.json')
}
State @{gpu_uuid='card-one';gpu_index=1;gpu_name='NVIDIA GeForce RTX 3090'}
if((Resolve-NativeGpuUuid $Scratch) -cne 'card-one' -or $global:calls.Count -ne 0){throw 'record UUID not authoritative'}
State @{gpu_index=0}
$rejected=$false;try{Resolve-NativeGpuUuid $Scratch|Out-Null}catch{$rejected=$true}
if(-not $rejected){throw 'unbound multi-GPU record accepted'}
$global:cards=@('card-one')
if((Resolve-NativeGpuUuid $Scratch) -cne 'card-one'){throw 'legacy single GPU did not resolve its UUID'}
if((Get-NativeGpuPowerLimit 'card-one') -ne 450 -or $global:calls[-1] -cnotmatch '-i card-one'){throw 'power query not selected'}
@{status='passed';multi_gpu_without_uuid_refused=$rejected}|ConvertTo-Json -Compress
'''
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "binding.ps1"
            script.write_text(proof)
            result = subprocess.run([shutil.which("pwsh"), "-NoProfile", "-File", str(script),
                                     str(HOSTS / "native-gpu.ps1"), directory],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout),
                             {"status": "passed", "multi_gpu_without_uuid_refused": True})


if __name__ == "__main__":
    unittest.main()
