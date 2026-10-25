# Security model

Oh My Pi (coding-agent client) → OMP NInfer (qualified appliance and release layer) → NInfer
(inference engine) → Qwen3.8 27B (served model).

## Supported trust boundary

Every published release supports one trusted owner controlling each Oh My Pi (OMP) client and
qualified RTX runtime host. Local administrators and root can inspect processes, files,
container and native runtime state, GPU memory, and traffic endpoints. Shared shell hosts, hostile
local users, untrusted containers, public HTTP service, and tenant isolation are outside the
release claim.

The model artifact and registered release inputs are trusted. Prompts, repository files, tool output,
images, and model output may be sensitive user data; they are not trusted instructions to the host.
OMP remains responsible for tool approval and workspace boundaries.

## Protected assets

- NInfer bearer key;
- OMP transcripts and provider snapshots;
- source repositories and files exposed to OMP tools;
- prompts, images, model output, and request-log metadata;
- SSH credentials and host identity; and
- immutable release identities whose substitution could execute different code or weights.

## Release invariants

1. On the RTX 5090 lane, the container (`omp-ninfer-beta`) runs in a Docker `bridge` network with
   every Linux capability dropped (`--cap-drop ALL`), `no-new-privileges`, and the hash-pinned
   `io_uring` seccomp profile (`examples/manual-tunnel/ninfer_io_uring_seccomp.json`), and Docker
   publishes its server port only on host loopback (`--publish 127.0.0.1:18089:8080`). On the
   native Windows RTX 4090 and RTX 3090 lanes, the server binds `127.0.0.1:18082` directly on the
   host, and only one native lane runs at a time.
2. A local Windows client connects over host loopback (`127.0.0.1:18089` or `127.0.0.1:18082`);
   the macOS preview client reaches the RTX 5090 host only through an authenticated manual SSH
   local forward (`-L 127.0.0.1:18089:127.0.0.1:18089`, `ExitOnForwardFailure=yes`) bound to Mac
   loopback.
3. NInfer requires a random bearer key for status, Responses, checkpoints, and stored-response
   identities.
4. The bearer key lives in access-restricted files (`~/.config/omp-ninfer/api-key` and
   `~/.omp/agent/ninfer-beta.key` at mode `0600` on POSIX and WSL2;
   `%ProgramData%\omp-ninfer-keys\api-key.txt` restricted to Administrators `S-1-5-32-544` and
   SYSTEM `S-1-5-18` on native Windows, and `$HOME\.omp\agent\ninfer-beta.key` restricted via
   `icacls.exe` to the current user). It is never committed or embedded in YAML. The RTX 5090
   container receives it through a read-only mount (`/run/secrets/ninfer_api_key:ro`) passed to
   `--api-key-file /run/secrets/ninfer_api_key`, and Windows OMP clients read it from
   process-scoped environment variables (`NINFER_BETA_API_KEY` or `NINFER_NATIVE_API_KEY`).
5. OMP uses explicit local provider routes (`ninfer-beta/q38-ninfer`,
   `ninfer-native-4090/qwen3.8-27b`, or `ninfer-native-3090/q38-ninfer`) with retries, model
   fallback, and automatic client self-updates disabled (`examples/manual-tunnel/fail-closed.yml`).
6. The upstream OMP 18.12.6 binaries, lane-specific Qwen3.8 27B model artifacts (`81f924d4` on
   RTX 5090 and `eec39564` on the native lanes), NInfer container image and native packages, server
   binaries, seccomp profile, runtime configurations, and qualification summaries are pinned by
   immutable SHA-256 digests and commits in `releases/v0.13.0/manifest.json` before release status
   becomes `ready`.
7. The NInfer container image is pulled by OCI manifest digest (`@sha256:`), never a mutable tag.
8. Support material excludes raw prompts, outputs, request logs, secrets, private paths, hostnames,
   IP addresses, and unredacted Docker or system inspection dumps.
9. The RTX 5090 container uses restart policy `no`, and native Windows lanes require an explicit
   `Control-Release.ps1 -Action Start` after a reboot; process exits and reboots are observable
   rather than masked as silent recovery.

Passing `--api-key-file /run/secrets/ninfer_api_key` from a read-only secret mount and using
ACL-restricted key files under `%ProgramData%` avoids placing the bearer key in Docker
configuration, command-line argument vectors, YAML files, or shell history. However, root or local
administrators inside the trusted host and container boundary can still inspect mounted secret
files, process memory, process environment blocks, and loopback traffic. Do not deploy this
topology where local administrators are outside the trust boundary.

## Data flow and retention

OMP stores its authoritative session transcript and a provider acceleration snapshot on the client.
NInfer retains bounded in-memory Responses and cache state and writes durable session-scoped
checkpoints across all three qualified lanes:

- **RTX 5090 container lane:** Checkpoints and request logs (`requests.jsonl`) live in
  operator-owned host directories (`chmod 700`, default `~/.local/share/omp-ninfer/checkpoints-v013` and
  `~/.local/state/omp-ninfer`) bind-mounted into the container at `/checkpoints-v013` (24,576 MiB quota,
  256 MiB staging, schema 3, mandatory `--session-checkpoint-require-origin-auth`) and `/logs`, written as the invoking user via `io_uring` and `O_DIRECT`.
- **Native Windows RTX 4090 and RTX 3090 lanes:** Checkpoints, release metadata, `last-stop.json`,
  and request JSONL logs live under protected state roots
  (`%ProgramData%\NInfer\qwen38-4090-native` and `%ProgramData%\NInfer\qwen38-3090-native`), while
  installer assets stage under `%ProgramData%\omp-ninfer-stage-<variant>`. Both directory trees are
  owned by Administrators (`S-1-5-32-544`) with inheritance disabled and access restricted to
  Administrators and SYSTEM (`S-1-5-18`). `Protect-StateRoot.ps1` rejects pre-created unowned
  roots, null DACLs, and root or child junctions before any state is written.

Checkpoints and replicas are origin-authenticated, not encrypted. Each published generation records
`manifest.mac`, an HMAC over the manifest bytes keyed from material derived from the lane's bearer
key and stored outside the checkpoint root. `scripts/checkpoint_sync.py` verifies every file by
byte count and SHA-256 before atomic rename publication, and the runtime refuses or quarantines
modified or unauthenticated generations at load (`--session-checkpoint-require-origin-auth` is
mandatory in the `qwen38-5090-v0.13.0` profile and requires a valid MAC on at least a 32-byte
bearer key; within one API-key principal, `prompt_cache_key` names a session capability, so use
unique high-entropy keys and never share that principal among mutually untrusted clients). Because checkpoint payloads and request logs
contain unencrypted session state on disk, treat checkpoint directories, replica storage, and log
directories as sensitive user data even though public qualification receipts record content-safe
aggregates only.

Stopping or removing the container (`examples/manual-tunnel/stop-ninfer.sh`) or stopping a native
lane (`Control-Release.ps1 -Action Stop`) retains the model artifact, bearer key, checkpoint store,
request logs, and OMP transcripts. On native lanes, a managed stop flushes live sessions to
checkpoints within a 900-second graceful wait and, on the RTX 3090 lane, restores the 370 W default
power limit from its 300 W serving cap. Delete the model, key, checkpoint root, logs, and
transcripts explicitly when decommissioning a machine. Removing NInfer checkpoint state does not
remove the OMP transcript.

## Network exposure

Never change a host bind address (`published_bind_host` on the container or the native server bind)
to `0.0.0.0`, publish a container port on a non-loopback bridge interface, expose port `18089` or
`18082` beyond `127.0.0.1`, place a reverse proxy in front of NInfer, or attach a public tunnel.
Inside the RTX 5090 container namespace, `ninfer-serve` binds `0.0.0.0:8080` solely so Docker's
loopback publisher (`--publish 127.0.0.1:18089:8080`) can forward from host loopback; the
host-facing socket remains `127.0.0.1:18089`. Host firewalls and SSH daemon configuration remain
operator responsibilities. Verify the SSH host key out of band before copying the bearer key or
opening the tunnel.

A tunnel or runtime disconnect must fail closed. If OMP contacts any cloud model after an explicit
local route fails, preserve the content-safe observation, stop testing, and report it as a release
defect.

## Artifact verification

Run from the exact release tag (`v0.13.0`):

```sh
python3 scripts/verify_release.py --require-ready
```

`examples/manual-tunnel/start-ninfer.sh` and the native Windows `Install-Release.ps1` /
`Control-Release.ps1` workflows then verify model byte count and SHA-256, digest-pinned container
or native package hashes, the `ninfer-serve` binary SHA-256, the seccomp profile or state-root ACLs,
the computed configuration identity, and the authenticated `/v1/ninfer/status` payload before
reporting ready. Do not bypass a mismatch by editing expected hashes locally; any changed
executable, model, or profile requires a new release qualification binding.

### Native dependency inventory

The native package's existing SPDX file inventory remains authoritative for packaged bytes.
An additional CycloneDX 1.5 dependency inventory can be generated with
`scripts/generate_native_sbom.py`. It records resolved vcpkg packages and their dependency graph,
CUDA runtime DLL names, versions, hashes and EULA URLs, vendored `third_party/` source names,
versions and license expressions, and the runtime executable's SHA-256 and build source commit.
The inventories and vcpkg manifest are themselves hash-bound in the output. Absolute build paths
and operator identities are not recorded.

Versions and licenses must come from the exact build: the generator does not download packages,
resolve version constraints, infer versions from DLL names, or substitute unknown licenses.
The resolved vcpkg snapshot must cover the manifest's full transitive dependency closure at the
same baseline; CUDA DLL and vendored-source inventories must not omit packaged CUDA libraries or
source directories. CUDA versions come from the packaged DLLs' version metadata; the EULA is
recorded as an HTTPS license reference, not as a claim that redistribution terms have been met.
The build owner still reviews license obligations and the complete shipped DLL closure.

A native manifest variant may bind this additional asset with the atomic
`sbom_dependency_url` / `sbom_dependency_sha256` pair. The verifier checks an HTTPS asset under
that variant's component release and a lower-case SHA-256; if its checksum entry is also present
in the pinned checksum set, that entry must agree. Verification is local and does not download
the dependency SBOM. These optional pins do not replace the package, executable or SPDX pins,
do not retroactively change older releases, and do not assert that a vulnerability scan passed.

## Reporting a vulnerability

Follow [`../SECURITY.md`](../SECURITY.md). Do not open a public issue for a vulnerability or attach a
secret, prompt, output, raw log, private host identifier, or exploit against someone else's system.
