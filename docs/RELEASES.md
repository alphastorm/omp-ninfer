# Releases

OMP NInfer versions the integrated product. Component repositories keep their own versions and tags;
the product manifest binds the exact combination.

## Channels

| Channel | Meaning | Current state |
| --- | --- | --- |
| Early access | Invited testers, narrow exact profile, known manual steps and non-claims | `v0.1.0-beta.1` ready prerelease |
| Stable | Broadly advertised supported release | none |
| Development | Branch content with no install/support claim | `main` after publication |

GitHub `Latest` must not point to an early-access prerelease. The stable `omp` Homebrew cask remains
unchanged; early access uses `omp-beta`.

## Version identities

- Product prerelease: `alphastorm/omp-ninfer@v0.1.0-beta.1`
- RTX 5090 runtime component: `alphastorm/ninfer@v0.1.0-qwen38-5090`
- native client component: `alphastorm/homebrew-omp@omp-18.0.7-cross-platform-preview-5`
- RTX 4090 runtime: no v0.1 product binding

A component tag does not make the product release ready. The product tag must carry the exact ready
manifest and qualification summary.

## Release state transition

`releases/v0.1.0-beta.1/manifest.json` has three valid states:

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
8. product manifest.

Changing executable code, the model, server arguments, OMP state semantics, transport, security
boundary, or support claim invalidates dependent evidence and requires a new candidate. Editing a
mutable tag or rebinding an old qualification to new bytes is prohibited.

## External-install acceptance

The final gate used a clean isolated native Windows client root and the exact Docker Desktop WSL2
RTX 5090 runtime identity. It downloaded the public client and compatibility authority, then bound
the result into the `ready` manifest and qualification summary before the product tag. The gate
proved:

- published Windows archive and installed binary checksums plus exact OMP version;
- exact served model artifact hash;
- digest-pinned NInfer image, binary hash, and authenticated identity;
- Windows local-loopback connectivity to Docker Desktop WSL2;
- explicit fail-closed OMP provider resolution;
- text/tool, image, stateful follow-up, and OMP exit/resume;
- disconnected-tunnel failure with no cloud answer; and
- clean owned-container stop while retaining user data.

The external smoke qualifies the installation composition; it does not repeat CUDA numerical or
performance qualification without a concrete runtime change.

## Release notes

At cut time, move the applicable human-readable entries from `[Unreleased]` in
[`CHANGELOG.md`](../CHANGELOG.md) into `## [0.1.0-beta.1] - YYYY-MM-DD`, using the actual ISO 8601
release date, and add comparison/tag links as defined by
[Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/). Never date an unpublished version.

Release notes must lead with the exact support boundary and manual topology, then link the manifest,
qualification summary, quickstart, security model, and known limitations. Do not claim:

- “first stateful Responses” or “first persistent KV cache”;
- automatic restart or NInfer process-restart continuation;
- `omp appliance install`, managed rollback, or RTX 4090 support;
- universal 5090 performance; or
- benchmark values not present in the public qualification summary.

Use “OMP NInfer” for the product/repository and `omp appliance ...` only for the command concept.
