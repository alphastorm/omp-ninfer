# Releases

OMP NInfer versions the integrated product. Component repositories keep their own versions and tags;
the product manifest binds the exact combination.

## Channels

| Channel | Meaning | Current state |
| --- | --- | --- |
| Public release | Published exact profiles with stated limitations and non-claims | `v0.4.8`, GitHub `Latest` |
| Development | Unpublished candidates with no install or support claim | post-`v0.4.8` work |

Prereleases never take GitHub `Latest`; `Latest` always points at the current public release. The
prerelease `omp-beta` Homebrew cask remains separate from the stable `omp` cask.

### Post-v0.4.7 development evidence (shipped in v0.4.8 where noted)

The corrected 2026-09-04 agent-shaped MTP0/3/5/7 campaign changes no released component or
profile. MTP3 was fastest on every lane and in both repetitions; K5/K7 were 13.57%/24.72% slower
on RTX 5090, 7.29%/20.17% slower on RTX 4090, and 11.34%/22.46% slower on RTX 3090. Analysis
revision 5 therefore retains the qualified MTP3 incumbent and rejects deeper drafting for the
current artifacts. Missing campaign and fresh-process MTP0 controls leave exact-output attribution
unresolved, but do not invalidate this no-change throughput decision. Public receipts:
[5090](measurements/2026-09-04-rtx5090-mtp-agent-ablation.json) ·
[4090](measurements/2026-09-04-rtx4090-mtp-agent-ablation.json) ·
[3090](measurements/2026-09-04-rtx3090-mtp-agent-ablation.json).

## Version identities

### v0.4.9 draft (staged 2026-09-05, not cuttable yet)

- `releases/v0.4.9/manifest.json` is a `draft` that carries the native-lane restore-path fix
  (EXP-017, [ninfer#36](https://github.com/alphastorm/ninfer/issues/36)) while the public
  release and the root compatibility authority stay at `v0.4.8`:
  - RTX 4090: `ninfer@v0.2.2-qwen38-4090-durable.1` (qualified head `9834bf58`, packaging
    `e16fa354`, package `d6f162cb...`), qualified on the owner rig with the post-restart
    continuation of the 102,060-token session in 9.5 s (225.6 s on v0.2.1)
    ([receipt](../releases/v0.4.9/qualification/rtx4090.json)); staged as a GitHub draft.
  - RTX 3090: `ninfer@v0.2.4-qwen38-3090-beta.1` (commit `cd06e782`, package `e4fbbfca...`),
    14/14 orchestrator phases ([receipt](../releases/v0.4.9/qualification/rtx3090.json)); staged
    as a GitHub draft.
  - RTX 5090 runtime, profile `qwen38-5090-v0.4.8`, and the OMP client are unchanged.
- Restore probe, shipped versus candidate on the same sessions: RTX 4090 146.6 s / 133.4 s ->
  5.6 s / 5.6 s ([shipped](measurements/2026-09-05-restore-probe-rtx4090-v0.2.1.json) ·
  [candidate](measurements/2026-09-05-restore-probe-rtx4090-candidate.json)); RTX 3090
  91.8 s / 92.2 s -> 10.8 s / 10.7 s ([shipped](measurements/2026-09-05-restore-probe-rtx3090.json) ·
  [candidate](measurements/2026-09-05-restore-probe-rtx3090-candidate.json)).
- Blockers, in order: publish the two native component releases, rerun the composed
  external-installation acceptance from the published URLs, then the pin dance and the cut.

### v0.4.8 public release (requalified lane configurations)

- Product release: `alphastorm/omp-ninfer@v0.4.8`, GitHub `Latest`. Each lane ships on its own
  best measured configuration, requalified on its own rig on 2026-09-05 and accepted from the
  published URLs:
  - RTX 5090: same runtime component (`v0.4.5-qwen38-5090-beta.1`, image `876c7809...`) under
    the new deployment profile `qwen38-5090-v0.4.8` (configuration `95765a38...`:
    `--max-private-continuations 8 --device-state-slots 4 --host-state-slots 24`, so sibling forks
    of a stored template keep the shared base anchor) - measured through the lifecycle tool
    ([receipt](../releases/v0.4.8/qualification/rtx5090.json)).
  - RTX 4090: [`ninfer@v0.2.1-qwen38-4090-durable.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.2.1-qwen38-4090-durable.1)
    (commit `b9c4636b`, package `1c66f7d5...`), prefill chunk 2,048
    ([receipt](../releases/v0.4.8/qualification/rtx4090.json)).
  - RTX 3090: [`ninfer@v0.2.3-qwen38-3090-beta.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.2.3-qwen38-3090-beta.1)
    (commit `2ce6c9dc`, package `96c9c37f...`), 131,072-token context
    ([receipt](../releases/v0.4.8/qualification/rtx3090.json)).
- Composed external-installation acceptance rerun on 2026-09-05
  ([receipt](../releases/v0.4.8/acceptance/composed-external-installation.json)) with native
  public-URL install acceptances on the
  [RTX 3090](../releases/v0.4.8/acceptance/rtx3090-public-install.json) and
  [RTX 4090](../releases/v0.4.8/acceptance/rtx4090-public-install.json), driven by
  [`scripts/hosts/accept-native-public-install.ps1`](../scripts/hosts/accept-native-public-install.ps1).

### v0.4.7 public release (corrects v0.4.6 asset URLs)

- Product release: `alphastorm/omp-ninfer@v0.4.7`, GitHub `Latest`. Identical components to
  v0.4.6; the v0.4.6 manifest bound product-versioned runtime asset names that 404 (tags are
  immutable, so the correction ships as a new release).

### v0.4.6 public release (superseded)

- Product release: `alphastorm/omp-ninfer@v0.4.6`, GitHub `Latest`.
- The RTX 5090 durable container moves to
  [`ninfer@v0.4.5-qwen38-5090-beta.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.4.5-qwen38-5090-beta.1)
  (image digest `876c7809...`): checkpoint manifest ORIGIN authentication (closes
  [ninfer#32](https://github.com/alphastorm/ninfer/issues/32)) - every save publishes an HMAC
  tag keyed outside the checkpoint root, loads verify before trusting manifest content, and
  `--session-checkpoint-require-origin-auth` is the strict posture for future NAS/S3 import
  (council CRS-origin-auth). Rollback-safe additive design: prior binaries read the same store.
  4090/3090 components rebound unchanged.

### v0.4.5 public release

- Product release: `alphastorm/omp-ninfer@v0.4.5`, GitHub `Latest`.
- The RTX 3090 native Windows lane joins the durable train at
  [`ninfer@v0.2.2-qwen38-3090-beta.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.2.2-qwen38-3090-beta.1):
  buffered checkpoint export off the engine lock, every-turn automatic saves with sustained-idle
  debounce and redundant-frontier skip, explicit `POST /v1/ninfer/checkpoints`, lineage-aware
  lazy-restore freshness guard, idempotent exact-endpoint restore, and constant-time
  session-ownership comparisons (council CRS-durable-3090, 14/14 rig qualification: 90.0 tok/s
  at 93.4% MTP under 300 W, 310 MB durable restart with exact recall). 5090/4090 components
  rebound unchanged.

### v0.4.4 public release

- Product release: `alphastorm/omp-ninfer@v0.4.4`, GitHub `Latest`.
- The RTX 5090 durable container moves to
  [`ninfer@v0.4.4-qwen38-5090-beta.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.4.4-qwen38-5090-beta.1)
  (image digest `546bb6a8...`): checkpoint export decoupled from the engine through a bounded
  buffered writer (fail-before-publication preserved), automatic saves debounced to
  sustained-idle with a redundant-frontier skip, and lazy restore repairing partially resident
  sessions (council CR-20260831-ckptdecouple). Warm follow-up during checkpoint traffic
  15.26 s → 0.91 s; explicit save 31.6 s → 13.8 s; four fanout branches 0.90-1.01 s with
  automatic saves at defaults. 4090/3090 components rebound unchanged.

### v0.4.3 public release

- Product release: `alphastorm/omp-ninfer@v0.4.3`, GitHub `Latest`.
- The RTX 5090 durable container moves to
  [`ninfer@v0.4.3-qwen38-5090-beta.2`](https://github.com/alphastorm/ninfer/releases/tag/v0.4.3-qwen38-5090-beta.2)
  (image digest `f66708f5...`): same-lane agent fanout through private long anchors,
  checkpoint-import integrity (streamed re-hash, fail-closed coverage, corrupt-generation
  quarantine), symlink-refusing export writes, constant-time credential equality, an explicit
  compute-to-transfer export fence, and the session-isolation set proven on the 4090 durable
  train (council CR-20260831-fanout43). 4090/3090 components rebound unchanged.

### v0.4.2 public release

- Product release: `alphastorm/omp-ninfer@v0.4.2`, GitHub `Latest`.
- The RTX 4090 native Windows lane moves to the durable v0.2 package
  ([`ninfer@v0.2.0-qwen38-4090-durable.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.2.0-qwen38-4090-durable.1)):
  the durable-train rebase (council CR-20260831-durable4090), the ninfer#28 pinned-client
  status fix, and five upstream ports. Requalified on the owner rig; the pinned client now
  cold-starts on every lane. 5090/3090 components rebound unchanged.

### v0.4.1 public release

- Product release: `alphastorm/omp-ninfer@v0.4.1`, GitHub `Latest`.
- The RTX 5090 durable container moves to
  [`ninfer@v0.4.1-qwen38-5090-beta.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.4.1-qwen38-5090-beta.1)
  (image digest `ce3cd215...`): health-gated checkpoint quota transition, post-publish
  reclamation that never fails an acknowledged save, and named skip reasons in server logs
  (council CR-20260831-v041delta). 4090/3090 components rebound unchanged.
- Release bytes were built in the pinned CI container on the owner appliance after a RunPod
  SECURE allocation outage; the route is documented in the component-release receipt.

### v0.4.0 public release

- Product release: `alphastorm/omp-ninfer@v0.4.0`, GitHub `Latest`.
- The RTX 5090 container lane moves to a new durable runtime image
  ([`ninfer@v0.4.0-qwen38-5090-beta.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.4.0-qwen38-5090-beta.1),
  image digest `8de5efdf...`): transactional session checkpoints restored across docker restarts.
  Durability now ships on all three lanes. 4090/3090 components unchanged.

### v0.3.2 public release

- Product release: `alphastorm/omp-ninfer@v0.3.2`, GitHub `Latest`.
- Corrective release: fixes the v0.3.1 RTX 4090 qualification summary whose limitations block
  contradicted its own MTP3 receipts (template residue). Component bytes and receipts unchanged.

### v0.3.1 public release

- Product release: `alphastorm/omp-ninfer@v0.3.1`, GitHub `Latest`.
- Change over v0.3.0: the RTX 4090 lane moves to its qualified MTP3 package
  ([`alphastorm/ninfer@v0.3.1-qwen38-4090-mtp3.2`](https://github.com/alphastorm/ninfer/releases/tag/v0.3.1-qwen38-4090-mtp3.2)),
  promoted by the recorded two-arm comparison decision; all other component identities unchanged.

### v0.3.0 public release

- Product release: `alphastorm/omp-ninfer@v0.3.0`.
- OMP source/client: `alphastorm/oh-my-pi@omp-v18.0.9-ninfer-beta.2`; the unchanged native archives
  remain at `alphastorm/homebrew-omp@omp-18.0.9-cross-platform-beta-2`.
- RTX 3090 runtime component: release-cut slot
  [`alphastorm/ninfer@v0.3.0-qwen38-3090.1`](https://github.com/alphastorm/ninfer/releases/tag/v0.3.0-qwen38-3090.1),
  which must resolve before cut; package
  `ninfer-rtx3090-omp-v0.2.1-beta.1-windows-x86_64-cuda13.3-rtx3090.tar.gz`, SHA-256
  `e7642d7069e85de497731735bde92a0c9b23f5b486848ab8cbe5c4da222baf97`,
  `573,355,399` bytes, source commit `872ee508c1f9c46fa38f4170c7e21f254a79e21f`, and
  [qualification receipt](measurements/2026-08-30-rtx3090-parity.json).
- RTX 4090 runtime component: rebinds the published
  `alphastorm/ninfer@v0.2.0-qwen38-4090-beta.1` component without changing its bytes.
- RTX 5090 runtime component: source `alphastorm/ninfer@6efa06505` from
  `vendor/neroued-dev`; OCI digest, SBOM identity, and qualification receipt are pending publication
  and remain release blockers until the product manifest binds them.

### Prior release record: v0.2.0-beta.1

- Product prerelease: `alphastorm/omp-ninfer@v0.2.0-beta.1`.
- RTX 5090 runtime component: `alphastorm/ninfer@v0.2.0-qwen38-5090-beta.2`.
- Native client component: `alphastorm/homebrew-omp@omp-18.0.9-cross-platform-beta-2`.
- Public OMP source/client mirror: `alphastorm/oh-my-pi@omp-v18.0.9-ninfer-beta.2`.
- Native runtime components: RTX 3090 preview at
  `alphastorm/ninfer@v0.2.0-qwen38-3090-beta.1` and qualified RTX 4090 beta at
  `alphastorm/ninfer@v0.2.0-qwen38-4090-beta.1`.

A component tag does not make the product release ready. The product tag must carry the exact ready
manifest and qualification summary.

## Release state transition

Each `releases/<version>/manifest.json` has three valid states:

### `draft`

- incomplete external artifact fields may be null;
- `publication.blockers` must be non-empty;
- installation scripts validate the static contract but refuse to start a release; and
- no README or cask may describe it as installable.

### `candidate`

- every OMP, Homebrew, NInfer OCI/SBOM, model, binary, source, and configuration identity required
  for installation is immutable and published;
- `components.omp.artifact_published` is true only after the cask verifier passes without
  `--allow-draft` against the exact release asset;
- `publication.blockers` remains non-empty and the qualification still records that external
  installation has not passed;
- `python3 scripts/verify_release.py --require-installable` passes; and
- maintainers may run the external-install acceptance from that exact commit, but no product tag
  or public-release readiness claim exists yet.

### `ready`

- exact OMP distribution version, source commit, artifact URL/size/hash, and Homebrew cask revision;
- digest-pinned NInfer OCI reference, manifest digest, SBOM URL/hash, source, and binary hash;
- exact Qwen artifact URL/revision/size/hash;
- qualification summary URL/hash matching checked-in bytes;
- external installation passed from public URLs on the supported topology;
- no remaining publication blockers; and
- `python3 scripts/verify_release.py --require-ready` passes.

`ready` means the package is technically cuttable. It does not grant authority to create repositories,
push commits/tags, upload images/assets, publish a GitHub release, or modify the Homebrew tap.
Authorization for those external effects remains separate and bounded.

## Candidate freeze

Before the final external-install smoke, freeze these bytes together:

1. OMP Windows x64 archive and binary;
2. NInfer OCI manifest and every referenced platform blob;
3. NInfer SBOM;
4. Qwen artifact revision;
5. profile JSON and fail-closed/provider fragments;
6. product qualification summary;
7. Homebrew beta cask; and
8. every declared native runtime package, source archive, SBOM, installer/controller, and
   qualification receipt; and
9. product manifest.

Changing executable code, the model, server arguments, OMP state semantics, transport, security
boundary, or support claim invalidates dependent evidence and requires a new candidate. Editing a
mutable tag or rebinding an old qualification to new bytes is prohibited.

## Next native release sequencing

For the next release after v0.2, close shared native-Windows correctness before variant-specific
builds or GPU leases:

1. land checkpoint deletion, protected state, bearer-secret ACLs, GPU ownership, packaging, and
   receipt logic once on a shared native-Windows base branch;
2. freeze and independently review that source candidate before compiling, and close every P1/P2
   finding at source level;
3. run the shared failure matrix up front: cross-session LRU during DELETE, quota GC, NULL DACL,
   raced/precreated/reparse roots, retained-secret ACL after real upgrade/rollback, non-default state
   roots, malformed nvidia-smi output, and SPDX inclusion in SHA256SUMS;
4. make every generated fault harness enumerate its substituted components; security claims require
   exact shipped scripts and real Windows effective-access tests;
5. schema-validate qualification receipts and prove package, SPDX SBOM, scripts, checksums, and final
   sidecar form one closed identity set; and
6. only then derive 3090/4090 packages and run hardware once, in this order: neutral build, package
   and security verification, GPU protocol/restart/performance/OMP gates, then receipt-only closure
   review.

The RTX 3090 parity candidate exercised this sequence end to end with one checkpointed command:
preflight, neutral build, private-path scan, deterministic package, managed install, protocol,
64K, restart, rollback, security, OMP, C1, receipt, and 370 W restoration. The sequence prevents
shared correctness classes from being discovered after variant binaries and hardware evidence are
already frozen.

## External-install acceptance

The v0.2 final gate used clean isolated macOS arm64, Windows x64, and Linux x64 client roots plus
the separately qualified runtime identities. It downloaded the public clients and compatibility
authority, then bound the result into the `ready` manifest and qualification summary before the
product tag. The gate proved:

- all three published client archive and installed binary checksums plus exact OMP version;
- exact served model artifact hash;
- digest-pinned NInfer image, binary hash, and authenticated identity;
- Windows local-loopback, Linux local-loopback, and managed macOS SSH client paths;
- explicit fail-closed OMP provider resolution;
- text/tool, image, stateful follow-up, and OMP exit/resume;
- disconnected-tunnel failure with no cloud answer;
- clean owned-runtime stop/restore while retaining user data; and
- exact native 3090/4090 package and qualification bindings without activating those routes.

The external smoke qualifies the installation composition; it does not repeat CUDA numerical or
performance qualification without a concrete runtime change.

## Release notes

At cut time, move the applicable human-readable entries from `[Unreleased]` in
[`CHANGELOG.md`](../CHANGELOG.md) into the exact version heading, using the actual ISO 8601
release date, and add comparison/tag links as defined by
[Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/). Never date an unpublished version.

Release notes must lead with the exact support boundary and manual topology, then link the manifest,
qualification summary, quickstart, security model, and known limitations. Do not claim:

- “first stateful Responses” or “first persistent KV cache”;
- automatic container restart, multi-GPU, or multi-tenant support;
- structured JSON-schema output or unattended RTX 3090 role activation;
- support response-time guarantees or other SLAs;
- universal GPU performance; or
- benchmark values not present in the public qualification summary.

Use “OMP NInfer” for the product/repository and `omp appliance ...` only for the command concept.
