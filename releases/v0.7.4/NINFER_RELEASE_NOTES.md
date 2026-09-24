# OMP NInfer v0.7.4 — live sessions survive a graceful stop

**Owner-operated, exact-profile 0.x release; no SLA.** RTX 5090 uses the manual Docker/SSH
route; RTX 4090 uses the native Windows package. Both GPU components advance to one durable-session
runtime; the OMP 18.2.3 client, the model artifact and every serving setting are unchanged from
v0.7.3. RTX 3090 is deferred.

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Quickstart](../../docs/QUICKSTART.md) · [Security model](../../docs/SECURITY.md)

## Runtime change

Before this release a graceful stop could lose live sessions: on the RTX 5090, EXP-048's workload
stopped with `saved 2, nothing to save 0, refused 2`. The runtime now keeps them
([#45](https://github.com/alphastorm/omp-ninfer/issues/45),
[#46](https://github.com/alphastorm/omp-ninfer/issues/46)):

- an automatic checkpoint refused at a transient gate - the newest turn not yet catalogued, or
  another request's transaction in progress - retries up to six times per completed turn once the
  engine quiesces;
- before admission evicts a session whose newest turn is not on disk, the engine saves it, waiting
  while that turn's reply is still being stored;
- re-saving a session under the disk quota no longer deletes other sessions' only checkpoints,
  including when a cleanup fails; and
- a graceful stop counts a session whose newest response is already on disk as nothing to save.

Both components are built from source `1c17c3facfbfd1243cf7711a412119302e6dbd74`: runtime
`a4d26ccb`, whose changes passed an independent four-model council and a remediation epoch
([dispositions](review/runtime-ledger.json)), plus one packaging-only commit that advances the
RTX 4090 lane to `v0.6.6-beta.1`.

## Two qualified GPU routes

- RTX 5090: `v0.6.8-qwen38-5090-beta.1`, image
  `sha256:f193b7469d062fc923b93ba72dbb4f8bb871912b505b529a062db50f65de2447`, server
  `72aa57dd147ef95ca3574ec4b550fb46676690d704bb9422ba0061d23f1f0ad6`.
- RTX 4090: `v0.6.6-qwen38-4090-beta.1`, package
  `cd9ab90f1a030424fcbe1025ad4b6240c7a14760759df873e3a60002232924ac`, server
  `7a923c21f73f03583ce25a2311d39818aeba82ce5bf7efaf508bfa8b4a1df41a`.
- Unchanged model artifact:
  `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`.

Every runtime gate was measured on the published bytes. On the RTX 5090, the image was pulled
anonymously by digest and passed the profile gates (130,048-token exact retrieval, decode, the
agent protocol across a restart), the EXP-050 durability workload - four saves before eviction, a
stop with `saved 1, nothing to save 3, refused 0`, all four stored sessions restored from their
checkpoints after a restart, and a second stop refusing nothing - EXP-051's publication barrier,
and the fanout, warm-arrival, restore and multisession probes
([lane receipt](qualification/rtx5090.json)). The RTX 4090 package passed all 15 canonical native
phases, including 130,048-token retrieval, the managed-stop flush of an unpublished session,
rollback in both directions, protected state, and the OMP 18.2.3 tool call
([lane receipt](qualification/rtx4090.json)).

RTX 5090 retains deployment `qwen38-5090-v0.7.0`, configuration
`762e6bf448b389cd6a8d08871a3df2c74080c5b1fbd7bbb95146030f1990eea8`, 16384 MiB host KV,
and a 28672 MiB host floor. RTX 4090 retains 11264 MiB host KV, 24 slots, and a 32768 MiB floor;
its release identity and configuration hash advance with the lane version.

RTX 3090 is omitted from this release pending access to its physical qualification host. Its
[v0.7.2 instructions](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)
and OMP 18.0.9 client remain a separate historical route, not a v0.7.4 qualification claim.

## Documented routes and clients

The four documented routes passed on the published components: RTX 5090 container host (2 steps),
macOS client (10, including a session that survived a server restart), Windows client (5) and
RTX 4090 native Windows (7), with pre-cut substitutions recorded and every host restored
([routes](acceptance/documented-routes.json)). The published macOS arm64, Windows x64 and Linux x64
OMP 18.2.3 clients each ran a typed tool turn, an exact continuation and a fail-closed request
against the RTX 5090 image; Linux ran under WSL2, not a separately qualified Linux OS
([composed acceptance](acceptance/composed-external-installation.json)).

The compatibility authority's `darwin-remote-ssh` profile is now `preview`. It was never
installable, and the pinned client reads a qualified profile as an installable one, so it rejected
the whole authority: `omp appliance doctor` failed for every profile against v0.7.3's authority.
The documented macOS client route does not use that command and stays accepted.

## Support boundaries

Automatic checkpointing remains best effort under live traffic: a crash or an expired graceful
wait can still leave unpublished work unsaved. Saving before eviction delays the admitting
request - about 6.5 s per 126K-token session on the RTX 5090 - and that request waits while a
victim's reply is still reaching its client, bounded by its own queue deadline. Ceiling-class
save-before-evict was exercised on the RTX 5090; the RTX 4090 lane runs the same runtime source
through its own phases. The multisession control again recorded root fallback on 2 of 8
continuations/forks; universal warm reuse is not claimed. Owner-operated exact profiles only; no
SLA, multi-GPU, multi-tenant, priority/preemption, or silent cloud fallback. Native Windows RTX 4090
is text/tools; vision remains an RTX 5090 container capability. Do not mix a predecessor manifest
with these commands.
