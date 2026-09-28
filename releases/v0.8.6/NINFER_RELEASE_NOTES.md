# OMP NInfer v0.8.6 — Long sessions compact inline

**Owner-operated, exact-profile 0.x release; no SLA.** Long sessions no longer lose a turn while
OMP compacts them. The config every route installs now makes the unmodified upstream OMP 18.4.0
client compact before a turn instead of in the background, and a new proof drives stock OMP
through repeated automatic compaction on both lanes. The client, the provider fragments, both GPU
lanes' runtime bytes, configurations and qualification receipts, the model and the memory floors
are unchanged from v0.8.5. RTX 3090 and the upstream engine merge remain deferred.

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Quickstart](../../docs/QUICKSTART.md) · [Security model](../../docs/SECURITY.md) ·
[Known limitations](#support-boundaries)

## What changed

### A turn no longer fails while OMP compacts the session

OMP compacts a 131,072-token session on its own at 111,412 tokens. By default it starts that work
in the background as the session nears the threshold. For the text-only RTX 4090 model that work
is a handoff: one request that resends the whole session and asks the model to write a summary.
Both lanes admit one request at a time, so the user's next turn waited behind it. Each attempt
expired at the runtime's 30 s admission deadline and OMP resent it. The handoffs took 56-61 s, and
in the third of three compactions one outlasted the resends: the turn failed with
`503 request_queue_timeout`.

`examples/manual-tunnel/fail-closed.yml`, the config every route installs, now sets
`compaction.asyncEnabled: false`, so OMP compacts before the turn. Three consecutive RTX 4090
compactions took 77.0-83.7 s each, no admission expired, and the session recalled its newest
identifier after each compaction and after a graceful restart.
The RTX 5090 compacts with snapcompact on the client in under 0.1 s, so the setting changes
nothing there ([EXP-072](../../docs/measurements/2026-09-28-omp-long-sessions.json)).

### Long sessions measured on both lanes

`scripts/omp_long_session_proof.py` drives one stock OMP session through repeated automatic
compactions, and optionally a restart after the last, with a route's documented fragment and
config. EXP-072 ran it on both lanes with OMP 18.4.0:

- RTX 4090, three handoffs and a graceful restart: every check passed, and the session still named
  all three older identifiers after the third compaction. The turn that carries a compaction takes
  91-101 s.
- RTX 5090, two snapcompact compactions: every check passed. The archive's frames reach the model
  at native resolution under `detail: "auto"`, and the session read back both identifiers that
  existed only inside frames. Snapcompact keeps a bounded archive and drops the rest of the older
  middle by design: 76,832 and 192,080 characters in the two compactions.
- A mock endpoint that admits one request at a time reproduces the failure deterministically: with
  the v0.8.5 config the turn behind a 45 s handoff failed after six expired attempts; with this
  config no attempt expired.
- OMP recognizes the runtime's `context_length_exceeded` refusal as a context overflow on both
  fragments, compacts and retries the turn.

## Two qualified GPU routes

- RTX 5090: `v0.6.12-qwen38-5090-beta.1`, image
  `sha256:cd9e10b115bbf38df011b201dfdd37ec3b56613da39b2f1701334c8157236b78`, server
  `3ab266e5cd82398be98c2baee6a41a123ce1a4b0d38bd9ddcda75044dcd5dcb1`, source
  `9d1ef7485d9c741c2830fa3d55218f3242cec5d7`, unchanged from v0.8.3.
- RTX 4090: `v0.6.9-qwen38-4090-beta.1`, package
  `6492588ea9b62a02a5b83434c653c61ea709c7d1609eb9de9d1c0eaf7ae23e87` (574,751,101 bytes), server
  `65364401fb1adb66e903f96ed6553f8b70042d4a7b2360ec88fb68049afb9aa4`, source
  `5ac17674e8e0b6ecd2bdc56a8eb6f9c397c2c1f4`, unchanged from v0.8.4.
- Unchanged model artifact:
  `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`.
- Unchanged client: unmodified upstream OMP 18.4.0.

RTX 5090 keeps deployment profile `qwen38-5090-v0.8.2`, configuration
`56878aed92e8f3fb4101884fa889c98d1da75914573ebd167305ca0b4aa83e98`, 60 s keep-warm,
16384 MiB host KV and a 28672 MiB host floor; its [lane receipt](qualification/rtx5090.json) is
byte-identical to v0.8.3's. RTX 4090 keeps deployment profile `qwen38-4090-native-v0.6.9-beta.1`,
configuration `ccecfbe3946e8cfea761fd1ad2187e92f04483c85a358122ca89dcaa3092672f`, 60 s keep-warm
with its sm_89 spin of 50 ms every 100 ms, 11264 MiB host KV, 24 host-state slots and the
32768 MiB floor. Its [lane receipt](qualification/rtx4090.json) is byte-identical to v0.8.4's and
records the 15 canonical qualification phases, including a typed tool call, with OMP 18.3.5.

RTX 3090 is omitted while its physical host is offline. Its built and tested `v0.6.2-beta.1`
package ([build preparedness](../../docs/measurements/2026-09-28-rtx3090-v062-build-preparedness.json))
is unpublished and absent from the manifest; one `qualify_native.py` window on the physical
RTX 3090 remains before inclusion. Its
[v0.7.2 instructions](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)
and OMP 18.0.9 client remain a separate historical route, not a v0.8.6 qualification claim.

## Documented routes and clients

The four documented routes - RTX 5090 container host, macOS client, Windows client and RTX 4090
native Windows - run against this candidate's published components with unmodified OMP 18.4.0
before the release is cut, with fresh client-platform acceptance.

## Upgrading from v0.8.5

Clone the v0.8.6 tag and merge its config into `~/.omp/agent/config.yml`; the one new setting is

```yaml
compaction:
  asyncEnabled: false
```

The OMP binary, `models.yml` and `PI_OPENAI_STATEFUL=1` are unchanged. Do not use a generic
`omp update` to move outside the release's pinned bytes. Neither lane's server build changes, so
checkpoints on both lanes remain valid across this upgrade.

## Support boundaries

EXP-072 is one run per configuration on each lane with synthetic build-log filler, one seed and
thinking `low`; the async failure depends on how long a handoff takes against OMP's resends, so
its rate is not measured. Older identifiers surviving compaction is recorded, not gated. The
RTX 5090 was not restarted after a compaction.

Compaction is expensive on the RTX 4090. The handoff re-prefills the whole session, because the
runtime renders OMP's `tool_choice: none` summary request without the tool block every other turn
starts with. Just below the threshold OMP replays the whole session, and the runtime reuses no
cache for the second replay in a row (about 102,600 tokens, 68 s). After a compaction, a graceful
restart restores a checkpoint that reuses nothing, so the first turn re-prefills the compacted
context once (about 32,000 tokens, 17 s); without compaction the restore is hot. In every RTX 5090
run one chained turn re-prefilled its whole context from root (93,696-105,066 tokens, 40-46 s);
its cause is not identified. These are runtime items for a later release.

Since v0.8.0 the RTX 4090 server commits and releases each pinned allocation's size plus 1/64
before pinning it ([#48](https://github.com/alphastorm/omp-ninfer/issues/48),
[lane receipt](qualification/rtx4090.json)). A refusal that still occurs reports the commit
limit, available commit and available memory.

Automatic checkpointing remains best effort under live traffic: a crash or an expired graceful
wait can still leave unpublished work unsaved. Saving before eviction delays the admitting
request - about 6.5 s per 126K-token session on the RTX 5090 - and that request waits while a
victim's reply is still reaching its client, bounded by its own queue deadline. The carried
multisession control recorded root fallback on 2 of 8 continuations/forks; universal warm reuse
is not claimed. Prefill, decode and power figures apply only to the recorded packages, machines
and profiles. Owner-operated exact profiles only; no SLA, multi-GPU, multi-tenant,
priority/preemption, or silent cloud fallback. Native Windows RTX 4090 is text/tools; vision
remains an RTX 5090 container capability. Do not mix a predecessor manifest with these commands.
