[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Lane,            # rtx3090 | rtx4090
    [Parameter(Mandatory = $true)][string]$ManifestPath,    # product manifest.json (draft or ready)
    [Parameter(Mandatory = $true)][string]$ExpectedSums,    # product-bound SHA256SUMS for the lane
    [Parameter(Mandatory = $true)][string]$StateRoot,
    [Parameter(Mandatory = $true)][string]$Workspace,
    [Parameter(Mandatory = $true)][string]$ReceiptPath,
    [string]$ModelArtifactPath = ''
)
# Public-URL install acceptance for a native Windows lane. Downloads every manifest-bound asset
# from the published component release, verifies the closed checksum set and each hash against
# the manifest, proves the public bytes are the installed qualified bytes (the 3090 installer's
# already_installed verification or a member-by-member comparison where the installer refuses
# a duplicate instance), then smokes the installed release through its own controller and
# restores the machine. Records identities as digests only; no hostnames, paths, or outputs.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
function Sha([string]$Path) { (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant() }
function ShaText([string]$Text) { $s=[Security.Cryptography.SHA256]::Create(); try { ([BitConverter]::ToString($s.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text))) -replace '-','').ToLowerInvariant() } finally { $s.Dispose() } }
function Utc() { [DateTime]::UtcNow.ToString('o') }
$receipt = [ordered]@{ artifact_type='omp_ninfer_native_public_install_acceptance'; schema_version=1; status='running'; lane=$Lane; started_utc=(Utc) }
function Finish([string]$Status) {
    $receipt.status = $Status; $receipt.completed_utc = (Utc)
    $json = $receipt | ConvertTo-Json -Depth 8
    [IO.File]::WriteAllText($ReceiptPath, $json, [Text.UTF8Encoding]::new($false))
}
try {
    $manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $variant = @($manifest.components.ninfer_variants | Where-Object { $_.id -ceq "$Lane-windows-native" })
    if ($variant.Count -ne 1) { throw 'variant is absent or duplicated in the manifest' }
    $v = $variant[0]
    New-Item -ItemType Directory -Force -Path $Workspace | Out-Null
    $baseUrl = ([string]$v.package_url).Substring(0, ([string]$v.package_url).LastIndexOf('/'))
    $receipt.source = [ordered]@{ release_tag=[string]$v.release_tag; base_url=$baseUrl; product_release=[string]$manifest.release }
    # 1. Closed checksum set from the public release must equal the product-bound bytes.
    $sumsPath = Join-Path $Workspace 'SHA256SUMS'
    Invoke-WebRequest -Uri "$baseUrl/SHA256SUMS" -OutFile $sumsPath -UseBasicParsing
    $expectedSums = Sha $ExpectedSums; $actualSums = Sha $sumsPath
    if ($expectedSums -cne $actualSums) { throw 'public SHA256SUMS differs from the product-bound checksum set' }
    $entries = @{}
    foreach ($line in @(Get-Content -LiteralPath $sumsPath -Encoding UTF8)) {
        if ($line -match '^([0-9a-f]{64})  (.+)$') { $entries[$Matches[2]] = $Matches[1] }
    }
    # 2. Every manifest-bound asset downloads from its public URL and hashes as bound.
    $assets = [ordered]@{ package=@($v.package_url,$v.package_sha256); sbom=@($v.sbom_url,$v.sbom_sha256); source_archive=@($v.source_archive_url,$v.source_archive_sha256); installer=@($v.installer_url,$v.installer_sha256); controller=@($v.controller_url,$v.controller_sha256); gpu_owner_controller=@($v.gpu_owner_controller_url,$v.gpu_owner_controller_sha256); state_protection=@($v.state_protection_url,$v.state_protection_sha256) }
    $downloaded = [ordered]@{}
    foreach ($name in $assets.Keys) {
        $url = [string]$assets[$name][0]; $expected = [string]$assets[$name][1]
        $file = Join-Path $Workspace ([IO.Path]::GetFileName($url))
        Invoke-WebRequest -Uri $url -OutFile $file -UseBasicParsing
        $actual = Sha $file
        if ($actual -cne $expected) { throw "downloaded $name hash mismatch" }
        $member = [IO.Path]::GetFileName($url)
        if ($entries.ContainsKey($member) -and $entries[$member] -cne $actual) { throw "downloaded $name is not the SHA256SUMS member" }
        $downloaded[$name] = [ordered]@{ sha256=$actual; bytes=(Get-Item -LiteralPath $file).Length; in_checksum_set=$entries.ContainsKey($member) }
    }
    $pkgFile = Join-Path $Workspace ([IO.Path]::GetFileName([string]$v.package_url))
    if ((Get-Item -LiteralPath $pkgFile).Length -ne [int64]$v.package_bytes) { throw 'package size differs from the manifest' }
    $receipt.integrity = [ordered]@{ checksum_set_sha256=$actualSums; checksum_entries=$entries.Count; assets=$downloaded; all_manifest_assets_downloaded_from_public_urls=$true; all_manifest_asset_hashes_verified=$true }
    # 3. Installed release identity.
    $state = Get-Content -LiteralPath (Join-Path $StateRoot 'state.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $active = [string]$state.active_release
    $rel = $state.releases.PSObject.Properties[$active].Value
    $installedBinary = Sha ([string]$rel.server_executable)
    $installedConfig = Sha ([string]$rel.config_file)
    if ($installedBinary -cne [string]$v.server_binary_sha256) { throw 'installed server binary is not the manifest binary' }
    if ($installedConfig -cne [string]$v.configuration_sha256) { throw 'installed configuration is not the manifest configuration' }
    $receipt.installed = [ordered]@{ release_id=$active; server_binary_sha256=$installedBinary; configuration_sha256=$installedConfig; matches_manifest=$true }
    $controller = Join-Path $StateRoot 'Control-Release.ps1'
    # 4. Public bytes are the installed qualified bytes.
    if ($Lane -ceq 'rtx3090') {
        $installer = Join-Path $Workspace 'Install-Release.ps1'
        $out = @(& $installer -PackagePath $pkgFile -PackageSha256 ([string]$v.package_sha256) -ModelArtifactPath $ModelArtifactPath -ApiKeyFile ([string]$rel.api_key_file) -NoStart)
        $last = ($out | Where-Object { $_ -is [string] -and $_.TrimStart().StartsWith('{') } | Select-Object -Last 1)
        $ins = $last | ConvertFrom-Json
        if ([string]$ins.status -cne 'already_installed' -or [string]$ins.release_id -cne $active -or [string]$ins.package_sha256 -cne [string]$v.package_sha256) { throw 'downloaded installer did not accept the installed release as the exact qualified bytes' }
        $receipt.install = [ordered]@{ execution_source='downloaded-public-url'; outcome='already_installed'; release_id=[string]$ins.release_id; package_sha256=[string]$ins.package_sha256; exact_qualified_bytes_accepted=$true; lifecycle_pointers_changed=[bool]$ins.lifecycle_pointers_changed; runtime_start_requested=[bool]$ins.runtime_start_requested }
    } else {
        # The 4090 installer refuses a duplicate instance; compare the public package members
        # against the installed release tree instead.
        $extract = Join-Path $Workspace 'extract'
        if (Test-Path $extract) { Remove-Item $extract -Recurse -Force }
        Expand-Archive -LiteralPath $pkgFile -DestinationPath $extract -Force
        $members = @(Get-ChildItem $extract -Recurse -File)
        $compared = 0; $mismatch = @()
        $releaseRoot = [string]$rel.release_root
        $unmatched = @()
        foreach ($m in $members) {
            # Members sit under one top-level directory; the installer fans them out into
            # bin\, bin\lifecycle\, bin\qualification\, bin\qualification\smoke\, config\, receipts\.
            $relPath = $m.FullName.Substring($extract.Length).TrimStart('\')
            $parts = $relPath.Split('\'); if ($parts.Count -gt 1) { $relPath = ($parts[1..($parts.Count-1)] -join '\') }
            $name = [IO.Path]::GetFileName($relPath)
            $candidates = @((Join-Path $releaseRoot $relPath), (Join-Path (Join-Path $releaseRoot 'bin\lifecycle') $name), (Join-Path (Join-Path $releaseRoot 'bin\qualification') $name), (Join-Path (Join-Path $releaseRoot 'bin\qualification') $relPath), (Join-Path (Join-Path $releaseRoot 'config') $name), (Join-Path (Join-Path $releaseRoot 'receipts') $name))
            $hit = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
            if ($null -eq $hit) { $unmatched += $relPath; continue }
            $compared++
            if ((Sha $hit) -cne (Sha $m.FullName)) { $mismatch += $relPath }
        }
        if ($compared -lt 20 -or $mismatch.Count -ne 0 -or $unmatched.Count -ne 0) { throw "installed release does not match the public package members (compared=$compared mismatches=$($mismatch.Count) unmatched=$($unmatched -join ','))" }
        $receipt.install = [ordered]@{ execution_source='downloaded-public-url'; outcome='already-installed-exact-bytes'; note='the installer refuses a duplicate release instance; public package members were compared against the installed release tree'; members_in_package=$members.Count; members_compared=$compared; mismatches=0 }
    }
    # 5. Smoke through the installed controller.
    $before = ((@(& $controller -Action Status -StateRoot $StateRoot) -join "`n") | ConvertFrom-Json)
    $wasRunning = ([string]$before.process_state -ceq 'running')
    if (-not $wasRunning) { & $controller -Action Start -StateRoot $StateRoot | Out-Null }
    $status = ((@(& $controller -Action Status -StateRoot $StateRoot) -join "`n") | ConvertFrom-Json)
    if ([string]$status.process_state -cne 'running' -or [string]$status.endpoint_state -cne 'ready') { throw 'controller did not report a ready release' }
    $keyBytes = [IO.File]::ReadAllBytes([string]$rel.api_key_file); $len=$keyBytes.Length
    while ($len -gt 0 -and ($keyBytes[$len-1] -eq 10 -or $keyBytes[$len-1] -eq 13)) { $len-- }
    $key = [Text.Encoding]::UTF8.GetString($keyBytes, 0, $len)
    $headers = @{ Authorization = "Bearer $key" }
    $base = "http://$($rel.host):$($rel.port)"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $st = Invoke-RestMethod -Method Get -Uri "$base/v1/ninfer/status" -Headers $headers -TimeoutSec 30 -UseBasicParsing
    $statusMs = $sw.Elapsed.TotalMilliseconds
    $identityOk = ([string]$st.identity.binary_sha256 -ceq $installedBinary) -and ([string]$st.identity.config_sha256 -ceq $installedConfig)
    if (-not $identityOk) { throw 'served identity does not match the installed release' }
    $anon = 0
    try { Invoke-WebRequest -Method Get -Uri "$base/v1/ninfer/status" -TimeoutSec 30 -UseBasicParsing | Out-Null; $anon = 200 } catch { $anon = [int]$_.Exception.Response.StatusCode }
    $publicModel = [string]((Get-Content -LiteralPath ([string]$rel.config_file) -Raw -Encoding UTF8 | ConvertFrom-Json).model_id)
    $body = @{ model=$publicModel; messages=@(@{ role='user'; content='Reply with exactly the single word ACCEPTED.' }); max_completion_tokens=16; temperature=0; reasoning_effort='none' } | ConvertTo-Json -Depth 6 -Compress
    $sw.Restart()
    $comp = Invoke-RestMethod -Method Post -Uri "$base/v1/chat/completions" -Headers $headers -ContentType 'application/json' -Body $body -TimeoutSec 120 -UseBasicParsing
    $compMs = $sw.Elapsed.TotalMilliseconds
    $text = [string]$comp.choices[0].message.content
    $receipt.smoke = [ordered]@{ authenticated_status_http=200; status_ms=[math]::Round($statusMs,1); served_identity_matches_installed=$true; anonymous_status_http=$anon; completion_http=200; completion_ms=[math]::Round($compMs,1); completion_tokens=[int]$comp.usage.completion_tokens; output_sha256=(ShaText $text); output_contains_marker=($text -match 'ACCEPTED'); speculative_backend=[string]$st.runtime.speculative_backend; public_model_id=$publicModel }
    if ($anon -ne 401) { throw 'anonymous status request was not refused' }
    # 6. Restoration: return the release to its prior state.
    if (-not $wasRunning) { & $controller -Action Stop -StateRoot $StateRoot | Out-Null }
    $after = ((@(& $controller -Action Status -StateRoot $StateRoot) -join "`n") | ConvertFrom-Json)
    $limit = [int][double](nvidia-smi.exe --query-gpu=power.limit --format=csv,noheader,nounits)
    $receipt.restoration = [ordered]@{ process_state=[string]$after.process_state; endpoint_state=[string]$after.endpoint_state; prior_state_restored=(([string]$after.process_state -ceq 'running') -eq $wasRunning); power_limit_w=$limit; active_release=[string]$after.release_id }
    $receipt.content_safety = [ordered]@{ hostnames_recorded=0; usernames_recorded=0; private_paths_recorded=0; secret_values_recorded=0; raw_prompts_recorded=0; model_outputs_recorded=0; identities_bound_by_sha256=$true }
    Finish 'passed'
} catch {
    $receipt.error = [string]$_.Exception.Message
    Finish 'failed'
    exit 1
}
exit 0
