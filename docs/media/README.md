# Canonical README media

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

## Files

| File | Provenance |
| --- | --- |
| `omp-ninfer-demo.cast` | Raw asciinema v3 capture of the take, unedited. 100×30, `xterm-256color`. |
| `omp-ninfer-demo.gif` | Rendered from the cast with `agg` (JetBrains Mono 16 px, brand theme, `--idle-time-limit 1.75`), optimized with `gifsicle -O3 --lossy=70`. |
| `omp-ninfer-demo.mp4` | H.264 `yuv420p` faststart master transcoded from the full-quality render. Silent. |
| `omp-ninfer-demo-poster.png` | Single frame: the passing test run, the one-line fix summary, and the stateful follow-up prompt. |

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
