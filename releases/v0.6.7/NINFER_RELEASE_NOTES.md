# OMP NInfer v0.6.7 - the RTX 5090 runtime takes the upstream engine work

The RTX 5090 runtime component advances to `v0.6.3-qwen38-5090-beta.1` (source `8818b88b`,
image `fc244576…`): the mainline runtime plus a selective backport of 18 commits from upstream
Neroued/ninfer master and one downstream adaptation. Deployment profile, configuration, the RTX
4090 and RTX 3090 components, and the OMP client are unchanged.

## What is in the backport

Kernel work on the paths this profile executes - MoE prefill weight staging, w8 rowsplit decode
and the w8 vocabulary t64 route, the fp8 w8a16 vocabulary GEMM, routed gate/up tile staging and
pipeline depth by route, shared-expert down-weight prefetch and L2 warm from the MoE down tail,
the GDN prefill convolution written straight into q/k/v, rmsnorm weight-first reads, sparse-MoE
one-CTA-per-token S2 - and correctness fixes: sparse-MoE gather index lifetimes, GDN record
snapshot bits with batched fp8 projection (and its template dependency), host uploads completed
before returning. Frontend: pure-ASCII NFC skip and a flat BPE merge table. Vendored cpp-httplib
moves to 0.54.1 (byte-identical to the upstream release), with this product's serve layer
adapted to its disconnect and lifetime APIs.

Deferred with reasons, in `docs/measurements/2026-09-12-upstream-backport-ledger.json`: the
runtime materialization/pressure fix family (unreachable without upstream's value-aware shared
prefix scheduling, which pulls the serve-adapter campaign), that campaign itself, dflash2, the
nvfp4/k8v4 kv-cache formats, the spdlog logging rework, and upstream's GDN cooperative-capacity
fix, which overlaps this product's own fix for alphastorm/ninfer#42 and needs its own window.

## Measured

Every RTX 5090 lane gate re-run on the lifecycle-started candidate and compared with v0.6.2:
130,048-token retrieval exact at 2,174.5 tok/s (2,169.9), decode 134.15 tok/s wall (132.53),
5.2 GB restore in 3.89/3.86 s (4.00/3.63), fanout 4/4 hot after a verified restart at 57K and
67K, warm arrival in both orders, tampered restore refused, agent protocol 200/404/404. Full
102-test suite on an ephemeral sm_120a GPU. On the documented route the published image, pulled
by digest, served the launcher-computed identity, re-measured exact at 2,172.5 tok/s, and the
macOS client route passed 10 of 10 including a server restart with the session continued
([receipts](qualification/rtx5090.json), [acceptance](acceptance/composed-external-installation.json)).

## Review

One full independent council was dispatched on the frozen subject. The cross-family supplement
completed with zero findings; the strong critic could not render a verdict because its model
selector no longer resolves in the upgraded review harness, and a second supplement returned a
provider quota error. The epoch closed on disposition with no P0/P1 and that residual on record.

## Route fix

The inference-host prepare block now survives a rerun with a complete model file: curl 8.5 turned
the CDN's HTTP 416 into a failure, which stopped a reader who reran the block after any later
step failed. The byte count and checksum decide.

## Upgrading

Re-clone the tag and rerun section 4 on the inference host: the start block pulls the new image by
digest. Installed sessions and checkpoints are unaffected - the store format and configuration are
unchanged.

## Known limitations

Unchanged from v0.6.3. Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or
NVIDIA.
