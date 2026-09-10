# OMP NInfer v0.6.0 - the RTX 4090 lane on the mainline runtime

The RTX 4090 native Windows lane moves off its divergent `v0.2.x` branch onto the mainline
runtime built for Ada. The same context-cache architecture the RTX 5090 container ships -
sibling forks on a shared long anchor, warm arrival across a restart, streamed SHA-verified
checkpoint restore - now serves on an RTX 4090 from one source tree. The RTX 5090 runtime, its
deployment profile, the RTX 3090 component, and the OMP client are byte-identical to v0.5.1 and
carry their receipts.

## What changed

- **RTX 4090 runtime `v0.6.0-qwen38-4090-beta.1`**
  ([component](https://github.com/alphastorm/ninfer/releases/tag/v0.6.0-qwen38-4090-beta.1),
  runtime fork `075d442e`, server binary `b3f9374f...`, package `da343d64...`,
  573,714,539 bytes), under deployment profile `qwen38-4090-native-v0.6.0-beta.1`
  (configuration `5ee3fb71...`): INT8 KV, MTP3, prefill chunk 2,048, 131,072-token context,
  two device-state slots, 24 host-state slots, 4 GiB Host KV, one active request. Five defects
  that only the hardware showed were fixed at source in the port (cooperative grids sized for
  170 SMs, a prompt-attention CTA that spilled under Ada's register cap, a DirectStorage queue
  that could not overlap streamed batches, an unlogged refusal, an unbounded residency query;
  EXP-025), and the mainline runtime beat the shipped v0.2.3 on the same 130,048-token fixture
  the same day.
- **Qualified through the lane's own lifecycle tool, 15/15 phases** (EXP-027): exact
  130,048-token retrieval in 91.8 s; C1 2,102.6 tok/s prefill and 159.0 tok/s decode at 93.0%
  MTP acceptance and 22,814 MiB peak; 15/15 protocol checks at the shipped pool and again at a
  third of it; an explicitly saved 310 MB session restored across a managed restart with the
  marker quoted exactly; bidirectional rollback; the Windows state-security regression set; the
  OMP golden run exact. Every registered test passes with the Qwen3.8 artifact (101/101).
- **Three runtime defects found and fixed on the way to the candidate.** Admission refused a
  legitimate request whose only reuse source was a long anchor shared with a sibling, because
  the guard measured exclusive ownership rather than residency
  ([ninfer#37](https://github.com/alphastorm/ninfer/issues/37)); the engine delivered a result
  before releasing its lane and republishing statistics, so a consumer could see its own
  completed request as live ([ninfer#38](https://github.com/alphastorm/ninfer/issues/38)); and
  mainline applied `X-NInfer-Session` only on the bodyless Responses routes. The qualification
  itself was corrected too: its restart phase now publishes the session it restarts, and a new
  pass runs the protocol at eight host-state slots so the first class cannot return unobserved.
- **Native manifest rows are derived, not transcribed.** `scripts/bind_native_variant.py`
  binds a native lane's manifest row from its packager's own `SHA256SUMS` and
  `package-build-receipt.json` plus the component tag, refusing a set that does not carry every
  bound asset or a receipt that disagrees with it.

## Evidence route

Lane receipt in `qualification/rtx4090.json`; the window record in
`docs/measurements/2026-09-10-rtx4090-native-lane-qualification.json`; the public-URL install
acceptance in `acceptance/rtx4090-public-install.json` (every asset downloaded and hashed
exactly, the downloaded installer accepting the installed release as the exact qualified bytes,
served identity matched, anonymous status refused, one authenticated completion, host restored);
the composed acceptance in `acceptance/composed-external-installation.json`. The RTX 5090 and
RTX 3090 receipts are the v0.5.1 and v0.5.0 receipts for the unchanged components.

## Known limitation

A managed stop on Windows terminates the server rather than signalling it, on both native lanes
and since their first releases. A session that was never published - automatically above 32,768
frontier tokens, or explicitly through `POST /v1/ninfer/checkpoints` - does not survive a
deliberate stop. Sessions above the gate and explicitly saved sessions do.

## Support boundary

Unchanged: one owner-operated machine per lane; one active request per qualified profile;
loopback-only, bearer-authenticated, fail-closed. Checkpoints from an older runtime fingerprint
replay once from the OMP transcript; RTX 4090 sessions checkpointed under the v0.2.3 lineage do
not carry into the new lineage. Community project; not affiliated with or endorsed by Oh My Pi,
Qwen, or NVIDIA.
