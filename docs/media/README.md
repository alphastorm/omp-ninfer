# Demo and launch media

These files are a **real recorded session**, not a mockup, composite, or scripted animation. Every
frame was produced by the actual released software answering real requests on the maintainer's
RTX 5090. The task content is synthetic and content-safe by construction.

## What was recorded

- **Client:** the published `omp-18.0.9-macos-arm64` beta archive
  (SHA-256 `ba85e7ab…c00c7`, verified before use), run directly from the extracted archive with an
  isolated `HOME` and the shipped provider fragment shape (`ninfer-beta/local-max`,
  `openai-responses` with stateful NInfer continuation).
- **Runtime:** the released `v0.2.0-beta.1` RTX 5090 runtime bytes — image
  `ghcr.io/alphastorm/ninfer-runtime@sha256:63c794e2…f08d`, server binary
  `d11dbba7…efdfa`, model artifact `eec39564…bf3e`, deployment profile
  `qwen38-5090-v0.2.0-beta.2` — verified by `python3 scripts/verify_release.py --require-ready`
  in a fresh tagged clone on the runtime host before launch.
- **Route:** Mac loopback → authenticated SSH local forward → host loopback → bearer-authenticated
  NInfer, the managed-macOS-route shape. One capture adaptation is disclosed below.
- **Session:** two turns in a scratch project. Turn one: find and fix a real off-by-one wraparound
  bug in `ringbuf.py`, rerun the tests (they pass). Turn two: a stateful follow-up question
  answered from retained session context. The recording plays in real time; only idle gaps longer
  than 1.75 s are compressed.

## Capture adaptation (disclosed)

The capture host's WSL mirrored-loopback path was unavailable during this session, so the runtime
container was relaunched from the identical image, model, key file, and serve arguments with
bridge networking and a published host-loopback port instead of the launcher's host-network mode.
Engine bytes, configuration arguments, model, and authentication were unchanged. The qualified
product claims are bound by the release receipts, not by this recording.

## Canonical files

| File | SHA-256 | Provenance |
| --- | --- | --- |
| `omp-ninfer-demo.cast` | `8b019c31973855779a8f8826f8a1950ef5b93806a8257cfe48ffd71322c692af` | Raw asciinema v3 capture of the take, unedited. 100×30, `xterm-256color`. |
| `omp-ninfer-demo.gif` | `d30836afe7abb07cdf137d06971d7be41d3a83846451e746254535d47bdc2ff7` | Rendered from the cast with `agg` (JetBrains Mono 16 px, brand theme, `--idle-time-limit 1.75`), optimized with `gifsicle -O3 --lossy=70`. |
| `omp-ninfer-demo.mp4` | `a8d1b3bbe4f2dbd44a121a43a5c3d59beb6ade19c5e667b99fbfdae3ee932509` | H.264 `yuv420p` faststart master transcoded from the full-quality render. Silent. |
| `omp-ninfer-demo-poster.png` | `321cca847cdbe500502057887e46a9613cdea34dc8198ec4de15c3667713b920` | Single frame: the passing test run, the one-line fix summary, and the stateful follow-up prompt. |

## Public launch derivatives

The canonical recording above remains intact. The launch files below were copied byte-for-byte from
the reviewed launch packet after checksum and media-type verification; none is a canonical
qualification recording.

| File | SHA-256 | Public use |
| --- | --- | --- |
| `omp-ninfer-demo-social.mp4` | `e2e8fbc4cb42c5c30a12ac0299c081728d6f4f6627ae74c260a2abc97fa0bd81` | H.264, 978×694, 30 fps, `yuv420p`, silent, faststart; preferred social attachment. |
| `omp-ninfer-demo-social-discord.gif` | `c5423f9e9289cecb68c42edb9631da0833c05b3ab0e61981465fa61f87ac7763` | Real animated GIF89a, 720×511, 10 fps; fallback where MP4 embedding is unavailable. |
| `omp-ninfer-demo-social-poster.png` | `80b8ce9069b201802dcaecd9a7b5da080ea4aca0a1e7a4eeadaeef7538788373` | 978×694 frame from the clean social interval; static demo fallback. |
| `omp-ninfer-launch-card.png` | `91c7b8be815e0a21ca6bfc753b21e3036f4c8a71ab8390b54bc1e3ea40e0b093` | 1600×900 launch evidence card; warm/cold is explicitly one measured 89,216-token follow-up. |

The social recording begins 8.5 seconds into the full MP4, after the generic updater banner has
left the frame. It is a temporal trim/re-encode only: no task content or output was altered. The GIF
and social poster show that same clean interval. All three inherit the source recording's disclosed
idle-gap compression and the exact released client/runtime/model identity above.

```sh
ffmpeg -ss 8.5 -i omp-ninfer-demo.mp4 \
  -an -vf 'fps=30,format=yuv420p' \
  -c:v libx264 -preset medium -crf 18 -movflags +faststart \
  omp-ninfer-demo-social.mp4
```

The launch card does not claim universal performance: 235.02 tok/s decode and 130,048-token exact
retrieval belong to the qualified released RTX 5090 profile, while warm/cold is one server-side
maintainer sample on that same runtime. RTX 4090 has its own qualification receipt and RTX 3090 is
preview-only; neither inherits the card's 5090 measurements. Source receipts:
[`Benchmarks`](../BENCHMARKS.md) and
[`warm/cold measurement`](../measurements/2026-08-29-warm-vs-cold-ttft.json).

## Redaction discipline

The recorded environment used a neutral shared home directory outside any user account (the
macOS `Users/Shared` tree) and a system-interpreter `PATH`, so no username, hostname, endpoint,
port, key, or private path appears
in any frame or in the raw cast byte stream. Verified over the complete cast:
zero occurrences of the maintainer username, host names, tunnel ports, or key material.

## Reproduce

```sh
agg --font-family "JetBrains Mono" --font-size 16 --idle-time-limit 1.75 \
  --theme "060809,E8ECEF,0B0E11,C85045,8FBF7F,D8A657,7DAEA3,8E7BE8,86B3A8,B6BEC7,3A434D,EA6962,A9B665,E7B84C,89AEB8,AB9DF0,95D1C9,E8ECEF" \
  omp-ninfer-demo.cast omp-ninfer-demo.gif
```

The numbers this demo illustrates are bound by receipts elsewhere: qualified results in
[`../BENCHMARKS.md`](../BENCHMARKS.md) and the warm-vs-cold follow-up measurement in
[`../measurements/2026-08-29-warm-vs-cold-ttft.json`](../measurements/2026-08-29-warm-vs-cold-ttft.json).
Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.
