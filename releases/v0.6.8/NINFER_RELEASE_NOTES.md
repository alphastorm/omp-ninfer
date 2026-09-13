# OMP NInfer v0.6.8 - both mainline lanes on one runtime, and a fork bug fixed

The RTX 5090 runtime component advances to `v0.6.4-qwen38-5090-beta.1` (source `68a0722f`, image
`d346174a…`) and the RTX 4090 native component to `v0.6.2-qwen38-4090-beta.1`, built from the
same source for Ada. The 5090 deployment profile and configuration, the RTX 3090 component, and
the OMP client are unchanged.

## Fixed

Continuing a fork while its sibling is still alive answered HTTP 500 (`sequence StateImage
entitlement is inconsistent`) on every release since v0.6.2. The agent-protocol gate had never
exercised it: it deleted one sibling before continuing the other. Found by the multi-session
pressure probe, reduced to a 40-second deterministic reproduction
(`scripts/sibling_continue_probe.py`), fixed at source ([ninfer#43](https://github.com/alphastorm/ninfer/issues/43)):
a sequence's entitlement is now charged for the device slots it alone owns, so a long anchor a
sibling also holds no longer counts against it. Green across six fork shapes on the appliance;
the gate now continues a live sibling and records the status.

## The RTX 4090 lane takes the upstream engine work

The 18-commit selective backport that v0.6.7 shipped on the 5090 now runs on the native lane,
plus this product's fix for the cooperative GDN gating grids: on 128 SMs a 2,048-token prefill
chunk's preferred grid does not fit, and the launcher now partitions it over token-tile
intervals instead of falling through to a narrower split. The partitioned route is exact within
1.5e-6 relative-L2 of the double-precision reference on the 4090 itself.

The lane's fixed C1 fixture moved with it - 153.4 tok/s decode at 87.6% MTP3 acceptance, from
159.1 at 93.0% - and that number was bisected rather than accepted. The shift enters exactly at
the partition commit, which changes the fp32 summation order of those chunks; five diverse prompts
are byte-identical between the two runtimes, and the fixture (28,000 characters of one repeated
sentence) swings from 52% to 87% acceptance on the same binary when its own length changes by 1%
([EXP-037](../../docs/measurements/2026-09-13-rtx4090-c1-fixture-sensitivity.json)). The
published number carries the fixture's trajectory sensitivity, not a slower runtime.

## Measured

RTX 5090, every lane gate on the candidate: 130,048-token retrieval exact at 2,178.8 tok/s,
decode 134.8 tok/s wall, 5.2 GB restore in 3.85/3.65 s, fanout 4/4 hot after a verified restart
at 57K and 67K, warm arrival in both orders, tampered restore refused, agent protocol
200/404/404 with the live sibling at 200. Full 102-test suite on an ephemeral sm_120a GPU. RTX
4090: 15 of 15 lane phases on the lane host - neutral deterministic build, package, transfer
install, protocol at the shipped pool and at a third of it, 130,048-token exact retrieval in
91.5 s, a never-published session and an explicitly saved one both restored across a graceful
managed restart, rollback both directions, state security, OMP Golden-equivalent exact
([5090 receipts](qualification/rtx5090.json), [4090 receipt](qualification/rtx4090.json)).

## Review

Two independent councils on the frozen subjects: the 4090 backport candidate (`a98b150e`) drew
two P2 findings on the GDN capacity contract - the fused fallback's scratch scope and the
residency budget's specialization - both closed by `68a0722f` before this cut; the sibling
entitlement fix drew none. The strong critic's selector resolves again after re-qualification.

## Upgrading

RTX 5090: re-clone the tag and rerun section 4 on the inference host; the start block pulls the
new image by digest. RTX 4090: install `v0.6.2-qwen38-4090-beta.1` with its `Install-Release.ps1`;
the previous release stays installed for rollback. Installed sessions and checkpoints are
unaffected on both - the store format and configuration are unchanged.

## Known limitations

Unchanged from v0.6.7, plus the C1 fixture note above. Community project; not affiliated with
or endorsed by Oh My Pi, Qwen, or NVIDIA.
