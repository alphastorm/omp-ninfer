# OMP NInfer v0.6.9 - Qwen tool-parser semantics without a serve-adapter rebase

**Staged product release; RTX 5090 host/macOS route acceptance pending.** v0.6.8 remains the
current public release and install authority. Both new runtime components are published and
lane-qualified. RTX 4090 public-URL already-installed acceptance passed; the integrated product
is not yet promoted.

## Exact components

- Runtime source, frozen and independently reviewed:
  `696e78c7b4e3ac28ffcffafc73acc1496e65ef03`.
- RTX 5090 component: `v0.6.5-qwen38-5090-beta.1`, image
  `ghcr.io/alphastorm/ninfer-runtime@sha256:5e3e15581cb44a2dff5e1be0c64cad206f3048e9f01c98b04ef13f61195a9bb8`.
- RTX 4090 native component: `v0.6.3-qwen38-4090-beta.1`, built from the same source for Ada.
- The model, OMP client, RTX 3090 component, and serving settings are unchanged from v0.6.8.
  The RTX 5090 public deployment remains `qwen38-5090-v0.6.3`, configuration `622ab621`.
  Candidate lifecycle qualification uses the unchanged `qwen38-5090-v0.6.2`, configuration
  `5eb8a557`; these are distinct configuration identities, not interchangeable acceptance evidence.

## Fixed

The Qwen tool parser independently implements the semantics of upstream `3b50962b` and
`0c5d570c`: supported scalar unions, case-insensitive booleans, precise numeric lexemes,
mathematically integral values, duplicate parameters, and balanced embedded markup.
This is a semantic port into the downstream parser, **not a wholesale serve-adapter rebase**.
Custom raw input, history, opaque IDs, and stream ownership are preserved.

The earlier upstream-backport campaign deferred these commits because their extracted parser
files do not exist on this tree. This release does not pull that extraction and its adapter
campaign as dependencies. The
[dated backport ledger](../../docs/measurements/2026-09-12-upstream-backport-ledger.json)
remains unchanged as the record of that earlier decision.

## Review and parser verification

The frozen source includes review remediation that prevents malformed-region rescans and
recursive union traversal. Bytewise regressions and an 8,192-deep union case pass.
Focused appliance suites passed **13/13**, and Windows parser/wire suites passed **4/4**.
Blackwell CI on an ephemeral sm_120a GPU recorded **95 passed, 7 skipped, 0 failed out of
102 registered**; the pod was deleted after the run
([receipt](../../docs/measurements/2026-09-13-runpod-ci-full-696e78c7.json)).
Skipped tests are not credited as passes.

## Candidate lane qualification

### RTX 5090

Measured on the lifecycle candidate, not on the public deployment route:

- Exact retrieval at **130,048 prompt tokens**, **2,193.3 tok/s** prefill.
- **2,048-token** decode at **134.87 tok/s wall**.
- Fanout **4/4 hot at each of 57K and 67K tokens**, median **1.401 / 1.520 s**.
- Warm arrival hot in both resume-first and fork-first orders.
- Exact **5.201 GB** checkpoint restores in **4.155 / 3.886 s**; payload tamper refused.
- Live sibling continuation **HTTP 200**; deleted continuation **HTTP 404 before and after
  restart**.

[RTX 5090 qualification receipt](qualification/rtx5090.json).
The payload-tamper arc was exercised in this window; the origin-authentication arc is inherited,
not a fresh measurement.

### RTX 4090 native

- **15/15** native qualification phases.
- Exact retrieval at **130,048 prompt tokens** in **91.2377 s**.
- C1 decode **153.464 tok/s** at **87.58865% MTP acceptance**.
- Both explicitly saved and never-published sessions restored across managed stop/flush.
- Rollback with the `68a0722f` predecessor graceful in both directions.

[RTX 4090 qualification receipt](qualification/rtx4090.json).
The C1 fixture remains trajectory-sensitive as measured in EXP-037; its old measurement and
attribution are unchanged. These results do not claim a parser-driven throughput improvement.

## Public-route acceptance

RTX 4090 public-URL installer acceptance passed on the **already-installed path**: the downloaded
installer accepted the exact qualified bytes, changed no lifecycle pointers, and requested no
runtime start. Authenticated status returned **200**, anonymous status **401**, and completion
returned the `ACCEPTED` marker. The host was restored to its stopped state and **450 W**
([receipt](acceptance/rtx4090-public-install.json)). This is not a fresh-install observation.

The published RTX 5090 image was pulled with an empty Docker configuration and its binary hash
matched `b8a0a2c3`. That verifies published bytes, not the documented serving route. RTX 5090
host and macOS route acceptance remain pending; no composed external-installation acceptance
is claimed yet.

## Upgrading

After product promotion and public-route acceptance, use the exact v0.6.9 tagged quickstart.
RTX 5090: re-clone the tag and rerun section 4 on the inference host; the start block selects the
new image by digest. RTX 4090: install `v0.6.3-qwen38-4090-beta.1` with its
`Install-Release.ps1`; retain the predecessor for rollback. Candidate qualification exercised
managed session restoration and graceful rollback, not the public installer path. Do not bypass
the ready-manifest gate or mix v0.6.8 install commands with v0.6.9 component bytes.

## Known limitations

The qualified model, hardware, client, and deployment boundaries are unchanged from v0.6.8;
the RTX 3090 component does not receive this parser change. Community project; not affiliated
with or endorsed by Oh My Pi, Qwen, or NVIDIA.
