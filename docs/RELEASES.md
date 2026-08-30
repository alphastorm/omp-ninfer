# Releases

OMP NInfer versions the integrated product. Component repositories keep their own versions and tags;
the product manifest binds the exact combination.

## Channels

| Channel | Meaning | Current state |
| --- | --- | --- |
| Early access | Invited testers, closed exact profiles, known limitations and non-claims | `v0.2.0-beta.1` ready prerelease |
| Stable | Broadly advertised supported release | none |
| Development | Qualified candidates with no published install/support claim | RTX 3090 `v0.2.1-beta.1` parity candidate |

GitHub `Latest` must not point to an early-access prerelease. The stable `omp` Homebrew cask remains
unchanged; early access uses `omp-beta`.

## Version identities

- Product prerelease: `alphastorm/omp-ninfer@v0.2.0-beta.1`
- RTX 5090 runtime component: `alphastorm/ninfer@v0.2.0-qwen38-5090-beta.2`
- native client component: `alphastorm/homebrew-omp@omp-18.0.9-cross-platform-beta-2`
- public OMP source/client mirror: `alphastorm/oh-my-pi@omp-v18.0.9-ninfer-beta.2`
- native runtime components: RTX 3090 preview at `alphastorm/ninfer@v0.2.0-qwen38-3090-beta.1`
  and qualified RTX 4090 beta at `v0.2.0-qwen38-4090-beta.1`
- post-release RTX 3090 parity candidate: source
  `872ee508c1f9c46fa38f4170c7e21f254a79e21f`, package
  `e7642d7069e85de497731735bde92a0c9b23f5b486848ab8cbe5c4da222baf97`, and
  [qualification summary](measurements/2026-08-30-rtx3090-parity.json)

A component tag does not make the product release ready. The product tag must carry the exact ready
manifest and qualification summary.

The RTX 3090 candidate is qualification-complete but unpublished. It must enter a new product
manifest as those exact bytes—or be requalified—before any install documentation can select it.

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
- maintainers may run the tester-equivalent external-install acceptance from that exact commit, but
  no product tag or invited-tester readiness claim exists yet.

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
- stable/GA support or universal GPU performance; or
- benchmark values not present in the public qualification summary.

Use “OMP NInfer” for the product/repository and `omp appliance ...` only for the command concept.
