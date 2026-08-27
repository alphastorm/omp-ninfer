# Security model

## Supported trust boundary

`v0.1.0-beta.1` supports one trusted owner controlling both the Mac and the RTX 5090 Linux/WSL2
host. Local administrators and root can inspect processes, files, container state, GPU memory, and
traffic endpoints. Shared shell hosts, hostile local users, untrusted containers, public HTTP
service, and tenant isolation are outside the release claim.

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

1. The container shares the Linux/WSL2 host network namespace and NInfer binds
   `127.0.0.1:18089` there. No Docker bridge port is published.
2. The Mac reaches it only through an authenticated SSH local forward bound to Mac loopback.
3. NInfer requires a random bearer key for status, Responses, and stored-response identities.
4. The key lives in user-only files, is never committed or embedded in YAML, and is passed into the
   container through a read-only mount plus in-container expansion.
5. OMP uses an explicit `ninfer-beta/local-max` route with model fallback disabled.
6. The model, OMP artifact, NInfer image, binary, configuration, qualification summary, and Homebrew
   cask are pinned by immutable hashes or commits before release status becomes `ready`.
7. The NInfer image is pulled by OCI manifest digest, never a mutable tag.
8. Support material excludes raw prompts, outputs, request logs, secrets, private paths, hostnames,
   IP addresses, and Docker inspection dumps.
9. The beta container uses restart policy `no`; a process exit is observable rather than silently
   presented as proven recovery.

The in-container server process necessarily receives `--api-key` because NInfer v0.1 exposes that
server option. The launcher avoids placing the expanded key in Docker configuration or host shell
history, but root inside the trusted host/container boundary can inspect the process argument. Do
not use this topology where local administrators are outside the trust boundary.

## Data flow and retention

OMP stores its normal session transcript and a provider acceleration snapshot on the Mac. NInfer
retains bounded Responses/cache state in the live process; v0.1 does not claim durable NInfer
process-restart continuity. The optional request JSONL is written to the user-owned log directory on
the inference host. Treat it as sensitive even though the supported release path and issue forms use
content-safe aggregates only.

Stopping the container does not delete the model, key, OMP transcript, or request-log files. Delete
those explicitly when removing the beta. Removing NInfer response state does not remove the OMP
transcript.

## Network exposure

Never change either bind address to `0.0.0.0`, replace host networking with an unqualified bridge
publish, expose port `18089` beyond loopback, reverse proxy the endpoint, or enable a public tunnel.
Host firewalls and SSH configuration remain operator responsibilities. Verify the SSH host key out
of band before copying the bearer key or opening the forward.

A tunnel disconnect must fail closed. If OMP contacts any cloud model after the explicit local route
fails, preserve the content-safe observation, stop testing, and report it as a release defect.

## Artifact verification

Run from the exact release tag:

```sh
python3 scripts/verify_release.py --require-ready
```

The runtime launcher then checks model bytes, the digest-pinned image's `ninfer-serve` binary, and the
authenticated live identity before reporting ready. Do not bypass a mismatch by editing expected
hashes locally; a changed executable component requires a new release candidate and qualification
binding.

## Reporting a vulnerability

Follow [`../SECURITY.md`](../SECURITY.md). Do not open a public issue for a vulnerability or attach a
secret, prompt, output, raw log, private host identifier, or exploit against someone else's system.
