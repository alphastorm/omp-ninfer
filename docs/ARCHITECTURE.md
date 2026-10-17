# Architecture

Oh My Pi (coding-agent client) → OMP NInfer (qualified appliance and release layer) → NInfer
(inference engine) → Qwen3.8 27B (served model).

OMP NInfer is an integration and release product, not a third inference runtime. Each published
release (`v0.12.1`) binds an exact Oh My Pi (OMP) client, NInfer runtime, lane-specific Qwen3.8 27B
artifact, hardware profile, loopback topology, and qualification summary.

## Runtime topology

```mermaid
sequenceDiagram
    participant User
    participant OMP as OMP 18.10.1 client (Windows/macOS/Linux)
    participant Route as Loopback route (local or SSH forward)
    participant NInfer as NInfer on a qualified GPU lane
    participant GPU as Lane-pinned Qwen3.8 27B artifact

    User->>OMP: new coding turn
    OMP->>Route: OpenAI Responses request<br/>Bearer auth, 127.0.0.1:18089 (5090) or :18082 (native)
    Route->>NInfer: host loopback 127.0.0.1:18089 or :18082
    NInfer->>GPU: prefill/decode or retained continuation
    GPU-->>NInfer: tokens and state transition
    NInfer-->>OMP: Responses stream + response ID
    OMP-->>User: transcript publication
    OMP->>OMP: commit provider snapshot only after transcript publication
```

Every listener endpoint is loopback-only:

- **RTX 5090 container lane (`127.0.0.1:18089`):** On Windows 11 with Docker Desktop and WSL2,
  `examples/manual-tunnel/start-ninfer.sh` runs `ninfer-serve` on `0.0.0.0:8080` inside a Docker
  `bridge` container (`omp-ninfer-beta`, `--restart no`, `--cap-drop ALL`, `no-new-privileges`, and
  the hash-pinned `io_uring` seccomp profile `examples/manual-tunnel/ninfer_io_uring_seccomp.json`)
  and publishes that port to the runtime host's loopback (`--publish 127.0.0.1:18089:8080`). Docker
  host networking is not used because `--network host` on Docker Desktop binds inside the utility VM
  rather than the Windows and WSL2 host loopback. A local Windows client reaches
  `http://127.0.0.1:18089/v1` directly; on the macOS preview route,
  `examples/manual-tunnel/open-tunnel.sh` opens a manual SSH local forward
  (`-L 127.0.0.1:18089:127.0.0.1:18089`, `ExitOnForwardFailure=yes`) from Mac loopback to remote
  loopback. The profile (`qwen38-5090-v0.11.0`, configuration `91a35670`) admits up to two requests
  in flight (`--max-concurrency 2`, `--device-state-slots 2`, `--pending-timeout-ms 180000`) over a
  131,520-token BF16 device KV pool and a 16,384 MiB host KV pool.
- **Native Windows RTX 4090 and RTX 3090 lanes (`127.0.0.1:18082`):** Both native packages
  (`v0.6.11-qwen38-4090-beta.1` and `v0.6.3-qwen38-3090-beta.1`, source `cad19767`) install on one
  two-GPU Windows 11 host under `%ProgramData%\NInfer\qwen38-4090-native` and
  `%ProgramData%\NInfer\qwen38-3090-native`. Each installer binds its card by GPU UUID
  (`Control-GpuOwner.ps1`) rather than device ordinal. Both lanes share `http://127.0.0.1:18082/v1`
  and run sequentially, one lane at a time and one request in flight (`concurrency: 1`, 30 s
  pending timeout, INT8 KV, MTP3, 11,264 MiB host KV on RTX 4090 and 8,192 MiB on RTX 3090). This
  is not multi-GPU inference or concurrent native serving. A managed stop
  (`Control-Release.ps1 -Action Stop`) signals `stop-event` (900 s graceful wait), flushes live
  sessions to checkpoints, records the stop in `last-stop.json`, releases the GPU lease, and on the
  RTX 3090 restores the default 370 W power limit from its 300 W serving cap.
- **Two model artifacts:** Both lanes serve Qwen3.8 27B `.ninfer` weights from
  `huggingface.co/neroued/Qwen3.8-27B-NInfer` at pinned revisions, but they do not share bytes. The
  RTX 5090 container lane binds `components.model` (`0634abb0`, 20,437,336,576 bytes, revision
  `dc370fb6`, with vision, tools, and preserved thinking); both native Windows lanes bind
  `components.native_model` (`eec39564`, 18,210,531,328 bytes, revision `18dfc887`, text and tools).

SSH (where used) authenticates the machine path; a separate bearer token always authenticates the
HTTP endpoint (`~/.config/omp-ninfer/api-key` mounted at `/run/secrets/ninfer_api_key` for the
container, `~/.omp/agent/ninfer-beta.key` on clients, and `%ProgramData%\omp-ninfer-keys\api-key.txt`
for native lanes). All three lanes write authenticated, session-scoped checkpoints to local storage
and restore the prior Responses chain after a server restart. OMP's transcript remains
authoritative if any retained state is absent or invalid.

## State ownership

- **OMP transcript:** authoritative messages, tool calls/results, branches, and session history.
- **OMP provider snapshot:** a private acceleration envelope containing the committed NInfer response
  baseline and identity needed to append the next turn.
- **NInfer Responses state:** retained response/cache state scoped by authenticated client and
  session identity, with durable checkpoints for restart recovery on all three lanes.
- **Qwen artifact:** immutable model bytes pinned by revision, size, and SHA-256.

A turn advances provider state only after a complete valid stream and durable transcript publication.
Cancellation, malformed/incomplete output, transport failure, or transcript persistence failure must
leave the prior committed baseline usable. If acceleration state is absent or invalid, OMP's
transcript remains sufficient for a full replay.

This is why another stateful gateway is not inserted between OMP and NInfer. It would create a second
owner for continuation, persistence, and failure recovery without solving a first-release problem.

## Checkpoint transport

`scripts/checkpoint_sync.py` exports verified published generations to replica storage and
imports them into a local checkpoint root before restore. Host-to-host copying and NAS
replication are implemented; the live runtime never serves a network-share checkpoint root.
Sync checks payload hashes; the runtime authenticates `manifest.mac`. Restore requires the
matching runtime binary, model, profile, and bearer-bound session identity. The recorded
recovery probes return state to its original lane, not a second inference host or different GPU.
See [operator guidance and receipts](FACTS.md#checkpoint-transport-and-nas-replication).

## Identity chain

The [published release manifest](../releases/v0.12.1/manifest.json) binds:

1. product release and support channel;
2. upstream OMP 18.10.1 source revision, platform binaries, byte counts, and SHA-256 pins;
3. primary RTX 5090 NInfer source, server binary, OCI digest, and SBOM plus each UUID-bound native
   variant package, source archive, SBOM, installer/controller scripts, configuration, and
   qualification receipt;
4. both Qwen3.8 27B model artifacts (`components.model` for RTX 5090 and `components.native_model`
   for the native Windows lanes) by revision, byte count, and SHA-256;
5. canonical runtime configuration hash, seccomp profile hash, and hardware profile; and
6. the public product qualification summary and composed external-installation result.

`draft` permits incomplete publication fields and requires explicit blockers. `candidate` requires
every installable component identity and retains the external-install blocker. `ready` additionally
requires an exact qualification-summary hash, an external-install pass, and zero blockers.
`scripts/verify_release.py --require-ready` enforces the cut boundary.

The manifest is authoritative over README examples, mutable container tags, and
branch names. Release images are consumed only by `@sha256:` digest.

## Component boundaries

### `omp-ninfer`

Owns product naming, release/profile contracts, setup and support paths, public qualification
composition, and cross-component version pins. It does not own model mathematics, CUDA kernels,
OMP session semantics, or another request proxy.

### OMP

Owns the coding-agent UX, transcript, tools, and model configuration. The client is unmodified
[upstream Oh My Pi 18.10.1](https://github.com/can1357/oh-my-pi/releases/tag/v18.10.1) (source
`5d0aaffaf1f987503ce129a642fb6e30339615af`), pinned by byte count and SHA-256 across Windows x64,
macOS arm64 (preview), and Linux x64 (WSL2). Each NInfer model entry sets
`compat.statefulResponses: true` for OpenAI Responses chaining (`previous_response_id` and
`prompt_cache_key`) with `PI_OPENAI_STATEFUL` unset, and `examples/manual-tunnel/fail-closed.yml`
disables retries and cloud fallback while bounding per-provider concurrency via
`providers.maxInFlightRequests`. Stock OMP includes no built-in runtime installer or lifecycle
subcommands. Through v0.7.4, a downstream fork and the `alphastorm/homebrew-omp` tap (private since
2026-10-02) distributed the client; this repository no longer builds or publishes an OMP binary
(see [release history](RELEASES.md#version-identities)).

### NInfer

Owns the `.ninfer` engine and server, CUDA execution, Qwen3.8 runtime, Responses state and
checkpoint store, authenticated status, numerical behavior, container and native packages, and
runtime qualification. The RTX 5090 container runtime (`v0.6.16-qwen38-5090-beta.1`, source
`1302d639`) and the UUID-bound native Windows RTX 4090 (`v0.6.11-qwen38-4090-beta.1`) and RTX 3090
(`v0.6.3-qwen38-3090-beta.1`) packages (source `cad19767`) are published under
[alphastorm/ninfer](https://github.com/alphastorm/ninfer), retaining their upstream lineage and
separate hardware contracts.

## Lifecycle routes

Install, upgrade, stop, and rollback follow the documented container scripts and native Windows
controllers in the [Quickstart](QUICKSTART.md). OMP remains the transcript and coding-agent UX
owner.
