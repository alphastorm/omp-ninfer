# Public client acceptance and doctor

- Branch: `v013/acceptance-runner`; base `release/v0.13.0` at `f72484c`.
- `scripts/client_acceptance.py`: real stock OMP typed read/result, continuation, same-process server restart, fresh-client resume, session identity and fail-closed checks. Disposable HOME; owned disk-backed Responses stub in a separate process for rehearsal. Live hooks are explicit JSON argv arrays; partial restart/stop failures attempt the start hook. No shell interpolation or private transcripts in receipts.
- Receipt boundary: `rehearsal` versus `owner-live`; neither self-authorizes release qualification. `verify_release.py` rejects rehearsal labels in inline evidence and recursively bound local/pinned-product-URL JSON, including platform lists and cyclic references. Historical unlabeled receipts retain the existing gates.
- `scripts/doctor.py`: profile/actual container network mode, WSL2/Docker reachability, read-only bind-mount staging, ports 18089/18082, UUID-selected driver/GPU memory, runtime RAM, model presence/size and optional streaming SHA-256, POSIX/Windows bearer protection, stock client pin. Failures carry named cause/remediation; offline skips hardware instead of reporting passes.
- Prose only in QUICKSTART/TROUBLESHOOTING plus one README line. No release/profile edits. The 31 documented-route blocks are unchanged.
- Source authority: `start-ninfer.sh:273–369`; native package `Install-Release.ps1` host prerequisite/ACL conventions, `server-config.json` and `release-spec.json`. Existing client-probe `summarize`/`launch`, stock RPC driver and documented-route addressing are reused. The supplied probe's `--local-rehearsal` is a label, not a stub; the missing stub is implemented in the owned runner, not represented as pre-existing code.
- Conservative threshold interpretation: profile total RAM/VRAM minima remain totals. Free RAM must back the declared pinned host-KV pool unless an explicit free floor exists. Free VRAM is observed but no undeclared threshold is invented. Native driver floors come from the package; container default is CUDA 13 major compatibility floor 580, overridable by a higher profile floor. This is not driver qualification.
- Scoped tests: 44 tests in 132.107 s, OK, one skipped; includes `tests.test_documented_route` and release-prose checks. After final lifecycle/reference/fixture edits, 19 focused tests in 0.756 s, OK.
- Mac smoke: downloaded the exact stock OMP 18.12.1 arm64 asset; SHA-256 `fa41b27d434380e99b713e4f9ced0f73eb1fc0c409fdf23a57c119971d24bac5`. Initial real-client rehearsal passed seven checks in 19.69 s; final-code rehearsal passed the same seven in 18.06 s (captured below). Doctor offline passed its three applicable checks, skipped six unprovided/hardware checks, and did not claim hardware qualification.
- Not exercised: owner-live lifecycle hooks, Windows execution/ACLs, GPU/driver probes, real Docker/WSL staging or NInfer restart/cache reuse. The stub proves client/harness wiring only. No GPU host, production lane, release asset, tag or publication was changed.
- Lead integration: run the full Python suite and ready verifier on the integrated candidate; add `python3 scripts/doctor.py --offline --json` to ProductCI's acceptance-dry-run job. Real live checks still require an owner window and the existing runtime-identity/restoration gates.

## Commands exercised

Commands ran from this worktree. Smoke assets/receipts stayed outside the repository.

```sh
PY=/opt/homebrew/opt/python@3.13/libexec/bin/python3
mkdir -p /tmp/omp-v013-acceptance-smoke
curl --fail --location --output /tmp/omp-v013-acceptance-smoke/omp-darwin-arm64 https://github.com/can1357/oh-my-pi/releases/download/v18.12.1/omp-darwin-arm64
chmod +x /tmp/omp-v013-acceptance-smoke/omp-darwin-arm64
$PY -m unittest tests.test_client_acceptance tests.test_doctor tests.test_documented_route tests.test_verify_release.ReleaseContractTest.test_rehearsal_cannot_be_bound_as_release_qualification
$PY -m unittest tests.test_client_acceptance tests.test_doctor tests.test_verify_release.ReleaseContractTest.test_rehearsal_cannot_be_bound_as_release_qualification
$PY scripts/client_acceptance.py --omp /tmp/omp-v013-acceptance-smoke/omp-darwin-arm64 --omp-sha256 fa41b27d434380e99b713e4f9ced0f73eb1fc0c409fdf23a57c119971d24bac5 --omp-version omp/18.12.1 --local-rehearsal --receipt /tmp/omp-v013-acceptance-smoke/rehearsal.json
$PY scripts/doctor.py --offline --json --omp /tmp/omp-v013-acceptance-smoke/omp-darwin-arm64 --client-platform darwin-arm64
$PY scripts/client_acceptance.py --omp /tmp/omp-v013-acceptance-smoke/omp-darwin-arm64 --omp-sha256 fa41b27d434380e99b713e4f9ced0f73eb1fc0c409fdf23a57c119971d24bac5 --omp-version omp/18.12.1 --local-rehearsal --receipt /tmp/omp-v013-acceptance-smoke/final-rehearsal.json
```

## Captured client smoke output

```json
{
  "artifact_type": "omp_ninfer_client_acceptance",
  "schema_version": 1,
  "receipt_class": "rehearsal",
  "qualification_claimed": false,
  "lane": "rtx5090-macos-client",
  "synthetic_prompts_only": true,
  "document": "docs/QUICKSTART.md",
  "document_sha256": "e1149a3f6d3435722871344fd74380bb7703b14f8ff1d7cf294a94a17c57acf7",
  "block_addresses": [
    {"slug": "tool", "heading": "Text and tool turn", "index": 0, "sha256": "20be720027ed8cf9cd4297ded3a923adac01873fff27e59ef27bb0f510d973c9", "language": "sh"},
    {"slug": "resume", "heading": "Stateful follow-up and OMP resume", "index": 0, "sha256": "cd1befb5daadbb1bbb5df28179b3e9e23a897cc12a921f52e3f2f9b3e88a9d3c", "language": "sh"},
    {"slug": "survives-restart", "heading": "Session survives the server process", "index": 0, "sha256": "5ea55d391650c75a128a0429da7e422608201a592d9e5771f6a9da9607a7f4dd", "language": "sh"},
    {"slug": "fail-closed", "heading": "Fail closed", "index": 0, "sha256": "73341e46e74e37137db0be4318e851b90f9533c43e413731ddad91837772bb61", "language": "sh"}
  ],
  "execution": "semantic client checks; not verbatim install-route execution",
  "checks": {"tool_turn": true, "seed": true, "continuation": true, "restart_survival": true, "client_resume": true, "same_session": true, "fail_closed": true},
  "error": null,
  "started_utc": "2026-10-25T02:44:14.454009+00:00",
  "omp": {"sha256": "fa41b27d434380e99b713e4f9ced0f73eb1fc0c409fdf23a57c119971d24bac5", "version": "omp/18.12.1"},
  "passed": true,
  "status": "passed"
}
```

## Captured doctor smoke output

```json
{
  "artifact_type": "omp_ninfer_doctor",
  "schema_version": 1,
  "receipt_class": "preflight",
  "mode": "offline",
  "lane": "rtx5090",
  "qualification_claimed": false,
  "hardware_checked": false,
  "status": "offline",
  "checks": [
    {"name": "loopback_profile", "status": "pass", "cause": "", "remediation": ""},
    {"name": "docker_network_mode", "status": "pass", "cause": "", "remediation": ""},
    {"name": "model_file", "status": "skipped", "cause": "offline: no model supplied", "remediation": ""},
    {"name": "bearer_permissions", "status": "skipped", "cause": "offline: no bearer file supplied", "remediation": ""},
    {"name": "omp_hash", "status": "pass", "cause": "", "remediation": "", "evidence": {"observed": "fa41b27d434380e99b713e4f9ced0f73eb1fc0c409fdf23a57c119971d24bac5", "expected": "fa41b27d434380e99b713e4f9ced0f73eb1fc0c409fdf23a57c119971d24bac5"}},
    {"name": "docker_wsl", "status": "skipped", "cause": "offline: hardware/network commands disabled", "remediation": ""},
    {"name": "driver_floor", "status": "skipped", "cause": "offline: hardware/network commands disabled", "remediation": ""},
    {"name": "memory", "status": "skipped", "cause": "offline: hardware/network commands disabled", "remediation": ""},
    {"name": "loopback_listener", "status": "skipped", "cause": "offline: hardware/network commands disabled", "remediation": ""}
  ],
  "thresholds": {"ram_total_mib": 28672, "ram_free_mib": 16384, "vram_total_mib": 32607, "vram_free_mib": 0, "driver_major": 580}
}
```
