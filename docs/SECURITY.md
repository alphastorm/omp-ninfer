# Security model

Oh My Pi (coding-agent client) → OMP NInfer (qualified appliance and release layer) → NInfer
(inference engine) → Qwen3.8 27B (served model).

## Supported trust boundary

Every published release supports one trusted owner controlling each Oh My Pi (OMP) client and
qualified RTX runtime host. Local administrators and root can inspect processes, files, container
and native runtime state, GPU memory, and traffic endpoints. Shared shell hosts, hostile local
users, untrusted containers, public HTTP service, and tenant isolation are outside the release
claim.

The model artifact and registered release inputs are trusted. Prompts, repository files, tool
output, images, and model output may be sensitive user data; they are not trusted instructions to
the host. OMP remains responsible for tool approval and workspace boundaries.

## Protected assets

- NInfer bearer key;
- OMP transcripts and provider snapshots;
- source repositories and files exposed to OMP tools;
- prompts, images, model output, and request-log metadata;
- SSH credentials and host identity; and
- immutable release identities whose substitution could execute different code or weights.

## Release invariants

1. On the RTX 5090 lane, container `omp-ninfer-beta` runs on a Docker `bridge` network with
   `--cap-drop ALL`, `no-new-privileges`, and the hash-pinned `io_uring` seccomp profile
   (`examples/manual-tunnel/ninfer_io_uring_seccomp.json`). Docker publishes its server port only
   on host loopback (`--publish 127.0.0.1:18089:8080`). Native Windows RTX 4090 and RTX 3090
   servers bind `127.0.0.1:18082` directly on the host and run one lane at a time.
2. A local Windows client connects over host loopback (`127.0.0.1:18089` or `127.0.0.1:18082`).
   The macOS preview client reaches the RTX 5090 host only through an authenticated manual SSH
   local forward (`-L 127.0.0.1:18089:127.0.0.1:18089`, `ExitOnForwardFailure=yes`) bound to Mac
   loopback.
3. NInfer requires a random bearer key for status, Responses, checkpoints, and stored-response
   identities.
4. The bearer key is stored in access-restricted files (server `~/.config/omp-ninfer/api-key` and
   client `~/.omp/agent/ninfer-beta.key` at mode `0600` on POSIX and WSL2; native server
   `%ProgramData%\omp-ninfer-keys\api-key.txt` restricted to Administrators `S-1-5-32-544` and
   SYSTEM `S-1-5-18`, and client `$HOME\.omp\agent\ninfer-beta.key` restricted via `icacls.exe` to
   the current user). It is never committed or embedded in YAML. The RTX 5090 container mounts it
   read-only (`/run/secrets/ninfer_api_key:ro`) for `--api-key-file /run/secrets/ninfer_api_key`,
   and Windows OMP clients read `NINFER_BETA_API_KEY` or `NINFER_NATIVE_API_KEY`.
5. OMP uses explicit local provider routes (`ninfer-beta/q38-ninfer`,
   `ninfer-native-4090/qwen3.8-27b`, or `ninfer-native-3090/q38-ninfer`) with retries, model
   fallback, and automatic client self-updates disabled (`examples/manual-tunnel/fail-closed.yml`).
6. The release manifest pins the release's inputs by immutable SHA-256 digests and commits before
   its status becomes `ready` ([current release](FACTS.md#current-release)). The pins cover the
   upstream Oh My Pi binaries, the shared Qwen3.8 27B model artifact, the NInfer container image
   and native packages, server binaries, SPDX and CycloneDX dependency SBOMs, the seccomp profile,
   runtime configurations, and qualification summaries.
7. The NInfer container image is pulled by OCI manifest digest (`@sha256:`), never a mutable tag.
8. Support material excludes raw prompts, outputs, request logs, secrets, private paths, hostnames,
   IP addresses, and unredacted Docker or system inspection dumps.
9. The RTX 5090 container uses restart policy `no`, and native Windows lanes require an explicit
   `Control-Release.ps1 -Action Start` after a reboot so exits and reboots stay observable rather
   than masked as silent recovery.

Passing `--api-key-file /run/secrets/ninfer_api_key` from a read-only secret mount and using
ACL-restricted key files under `%ProgramData%` keeps the bearer key out of Docker configuration,
argument vectors, YAML files, and shell history. Root or local administrators inside the host and
container boundary can inspect mounted secrets, process memory, environment blocks, and loopback
traffic. Do not deploy this topology where local administrators are outside the trust boundary.

## Data flow and retention

OMP stores its authoritative session transcript and a provider acceleration snapshot on the client.
NInfer retains bounded in-memory Responses and cache state and writes durable session-scoped
checkpoints across all three qualified lanes:

- **RTX 5090 container lane:** Checkpoints are in a per-release directory under
  `~/.local/share/omp-ninfer/` (name in [lanes and limits](FACTS.md#lanes-and-limits)), and request
  logs (`requests.jsonl`) are in `~/.local/state/omp-ninfer`, both at `chmod 700`. Docker
  bind-mounts them (logs at `/logs`) and writes as the invoking user via `io_uring` and `O_DIRECT`
  (schema 3, 24,576 MiB quota, 256 MiB staging, `--session-checkpoint-require-origin-auth`).
- **Native Windows RTX 4090 and RTX 3090 lanes:** Checkpoints
  (`cache/<release-instance-id>/session-checkpoints-v3`, where `<release-instance-id>` is the
  installed release ID; see [lanes and limits](FACTS.md#lanes-and-limits)), release metadata,
  `last-stop.json`, and request logs sit under `%ProgramData%\NInfer\qwen38-4090-native` and
  `%ProgramData%\NInfer\qwen38-3090-native` (schema 3, 24,576 MiB quota, 256 MiB staging,
  `--session-checkpoint-require-origin-auth`), while installer assets stage under
  `%ProgramData%\omp-ninfer-stage-<variant>`. Both directory trees are owned by Administrators
  (`S-1-5-32-544`) with inheritance disabled and access limited to Administrators and SYSTEM
  (`S-1-5-18`). `Protect-StateRoot.ps1` rejects pre-created unowned roots, null DACLs, and root or
  child junctions before any state is written.
- **Origin authentication, not encryption:** Each published checkpoint generation records
  `manifest.mac`, an HMAC over the manifest bytes keyed from material derived from the lane's
  bearer key (stored outside the checkpoint root). `scripts/checkpoint_sync.py` verifies every file
  by byte count and SHA-256 before atomic rename publication. Every lane profile sets
  `--session-checkpoint-require-origin-auth`, which needs at least a 32-byte bearer key and
  refuses or quarantines modified or unauthenticated generations at load. Within one API-key
  principal, `prompt_cache_key` names a session capability: use unique high-entropy keys and never
  share that principal among mutually untrusted clients. Checkpoint payloads and request logs are
  unencrypted on disk, so treat checkpoint directories, replica storage, and log directories as
  sensitive user data; public qualification receipts record content-safe aggregates only.

Stopping or removing the container (`examples/manual-tunnel/stop-ninfer.sh`) or stopping a native
lane (`Control-Release.ps1 -Action Stop`) retains the model artifact, bearer key, checkpoint store,
request logs, and OMP transcripts. Native managed stop flushes live sessions within a 900-second
graceful wait and on RTX 3090 restores the 370 W default power limit from its 350 W serving cap.
Delete the model, key, checkpoint root, logs, and transcripts explicitly when decommissioning a
machine; removing NInfer checkpoint state does not remove the OMP transcript.

## Network exposure

Never change a host bind address (`published_bind_host` on the container or the native server bind)
to `0.0.0.0` or publish a container port on a non-loopback bridge interface. Never expose port
`18089` or `18082` beyond `127.0.0.1`, place a reverse proxy in front of NInfer, or attach a public
tunnel. Inside the RTX 5090 container namespace, `ninfer-serve` binds `0.0.0.0:8080` solely so
Docker's loopback publisher (`--publish 127.0.0.1:18089:8080`) can forward from host loopback; the
host-facing socket remains `127.0.0.1:18089`. Host firewalls and SSH daemon configuration remain
operator responsibilities. Verify the SSH host key out of band before copying the bearer key or
opening the tunnel.

A tunnel or runtime disconnect must fail closed. If OMP contacts any cloud model after an explicit
local route fails, preserve the content-safe observation, stop testing, and report it as a release
defect.

## Artifact verification

Run from the release tag you installed:

```sh
python3 scripts/verify_release.py --require-ready
```

`examples/manual-tunnel/start-ninfer.sh` and the packaged native Windows `Install-Release.ps1` and
`Control-Release.ps1` scripts verify model byte count and SHA-256, digest-pinned container or
native package hashes, and the `ninfer-serve` binary SHA-256. They also verify the seccomp profile
or state-root ACLs, the computed configuration identity, and the authenticated `/v1/ninfer/status`
payload before reporting ready. Do not bypass a mismatch by editing expected hashes locally; any
changed executable, model, or profile requires a new release qualification binding.

### Native dependency inventory

Each native Windows package ships an SPDX file inventory that is authoritative for packaged bytes.
An additional CycloneDX 1.5 dependency inventory (`scripts/generate_native_sbom.py`) records
resolved vcpkg packages and shipped DLL hashes, CUDA runtime DLLs, vendored `third_party/` sources,
and the runtime executable hash and source commit, with no absolute build paths or operator
identities. Native runtime components at `v0.7.0` or later must bind this inventory through
`sbom_dependency_url` and `sbom_dependency_sha256`; those pins are optional only for older
component sets and do not replace the package, executable, or SPDX pins. `scripts/verify_release.py`
checks the asset URL, lower-case SHA-256, and pinned checksum entry locally without downloading the
dependency SBOM. Neither inventory asserts that a vulnerability scan passed. Recorded CUDA EULA
URLs are license references rather than a redistribution compliance claim, and the build owner
reviews license obligations and the shipped DLL closure. Generator inputs and packaging rules are
in [native dependency SBOM](RELEASES.md#native-dependency-sbom).

## Reporting a vulnerability

Follow the security policy in [`../SECURITY.md`](../SECURITY.md). Do not open a public issue for a
vulnerability or attach a secret, prompt, output, raw log, private host identifier, or exploit
against someone else's system.

Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.
