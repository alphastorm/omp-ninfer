# OMP NInfer v0.6.2 - three cards, one runtime tree

The RTX 5090 container lane moves onto the mainline runtime. Since v0.4.4 it served from a
separate branch head while the two native Windows lanes were ported to mainline; from this
release all three lanes are built from one commit. Nothing about how the lane is tuned changed -
the same context-cache arguments, the same 131,072-token ceiling, the same numbers - and the
RTX 4090 component, the RTX 3090 component, and the OMP client are byte-identical to v0.6.1 and
carry their receipts.

## What changed

- **RTX 5090 runtime `v0.6.2-qwen38-5090-beta.1`**
  ([component](https://github.com/alphastorm/ninfer/releases/tag/v0.6.2-qwen38-5090-beta.1),
  runtime fork `63f28c95`, server binary `6ab904d7...`, archive `05aa9c4b...`, 319,416,469
  bytes; image `ghcr.io/alphastorm/ninfer-runtime@sha256:a62dd5b8...` wrapped onto the same
  digest-pinned base), under deployment profile `qwen38-5090-v0.6.2` (configuration
  `5eb8a557...`): BF16 KV, MTP3, prefill chunk 1,024, 131,072-token context, four device-state
  slots, 24 host-state slots, eight private continuations, one active request - the v0.4.8
  argument set, unchanged.
- **One tree for three cards.** `63f28c95` is the commit the RTX 4090 lane shipped as v0.6.1
  and the RTX 3090 mainline candidate builds from. The container lane therefore now carries the
  portability and lifecycle work done for Windows, and the native lanes carry the container
  lane's context-cache architecture, from the same source.
- **Requalified on the owner appliance, 7/7 gates** (EXP-030): exact 130,048-token retrieval at
  2,169.9 tok/s, 2,048-token decode at 132.53 tok/s, the agent-protocol battery across a
  restart, 8/8 sibling forks on the shared anchor at 57.9K and 67.7K templates before and after
  a verified restart, warm arrival hot in both orders, and a 5.2 GB session restored in 3.6-4.0 s
  with exact planted-key retrieval and a flipped payload byte refused. Within run-to-run noise
  of v0.5.1 (2,180.3 tok/s prefill, 133.13 tok/s decode, 3.8/4.4 s restore).
- **Acceptance on the published bytes.** Every release asset was downloaded anonymously and
  hashed on a workstation, the image was pulled anonymously by digest with an empty credential
  store, and the lane's own gate script then ran against that pulled image. The configuration
  identity computed from the published image equals the qualified one, so the profile did not
  drift between qualification and publication.

## Evidence route

Lane receipt in `qualification/rtx5090.json`; the candidate window in
`docs/measurements/2026-09-10-rtx5090-v062-qualification.json` with its fanout, warm-arrival and
restore probes beside it; the published-image gates in
`docs/measurements/2026-09-11-rtx5090-v062-public-image-gates.json`; the lane's public-URL
acceptance in `acceptance/rtx5090-public-image.json`; the composed acceptance in
`acceptance/composed-external-installation.json`. The RTX 4090 and RTX 3090 receipts are the
v0.6.1 receipts for the unchanged components.

## Known limitations

Unchanged from v0.6.1. A managed stop of the RTX 4090 native lane saves every live session; a
crash, a power loss, or a stop whose graceful wait expires still loses what was never published,
and the stop receipt records which happened. The RTX 3090 lane keeps the v0.2.5 behaviour - a
managed stop terminates - until its mainline candidate ships. Sibling branches beyond the first
re-materialize the shared base from host KV until shared-page fanout lands.

## Support boundary

Unchanged: one owner-operated machine per lane; one active request per qualified profile;
loopback-only, bearer-authenticated, fail-closed. Checkpoints written by an older runtime
fingerprint replay once from the OMP transcript - sessions saved under the v0.5.1 runtime do
that on this upgrade. Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or
NVIDIA.
