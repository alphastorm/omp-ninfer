# Demo and launch media

These files are a **real recorded session**, not a mockup, composite, or scripted animation. Every
frame was produced by the actual released software answering real requests on the maintainer's
RTX 5090. The task content is synthetic and content-safe by construction.

## Canonical recording (v0.3)

- **Client:** the published `omp-18.0.9-macos-arm64` archive
  (SHA-256 `ba85e7ab…c00c7`, verified before use), run directly from the extracted archive with an
  isolated neutral `HOME` and the shipped provider fragment shape (`ninfer/local-max`,
  `openai-responses` with stateful NInfer continuation). The provider display name is
  `Qwen3.8 27B NInfer RTX 5090`.
- **Runtime:** the exact RTX 5090 runtime the `v0.3.0` manifest binds — image
  `ghcr.io/alphastorm/ninfer-runtime@sha256:63c794e2…f08d`, server binary
  `d11dbba7…efdfa`, model artifact `eec39564…bf3e`, deployment profile
  `qwen38-5090-v0.2.0-beta.2` — identity confirmed over the authenticated `/status` route
  immediately before recording.
- **Route:** Mac loopback → authenticated SSH local forward → appliance loopback →
  bearer-authenticated NInfer, the managed-macOS-route shape. One capture adaptation is disclosed
  below.
- **Session:** two turns in a scratch project. Turn one: find and fix a real off-by-one wraparound
  bug in `ringbuf.py`, rerun the tests (they pass). Turn two: a stateful follow-up question
  answered from retained session context. The recording plays in real time; only idle gaps longer
  than 1.75 s are compressed.

## Capture adaptation (disclosed)

At recording time the appliance's incumbent serve was a post-release development build whose
status schema the published client correctly rejects. The owner's qualification
stop/record/restore flow was used: the incumbent container's exact pre-state was recorded, it was
stopped but never removed, the exact pinned released image above was served temporarily on a
separate loopback port with a fresh temporary key, the session was recorded, the temporary
container was stopped and its key removed, and the incumbent was restarted and verified against
its recorded pre-state. Engine bytes, configuration, model, and authentication were the released
identity throughout. The qualified product claims are bound by the release receipts, not by this
recording.

## Canonical files

| File | SHA-256 | Provenance |
| --- | --- | --- |
| `omp-ninfer-demo-v3.cast` | `c541c0ea8b213582af078e2f86d7b30a56a91b5defb4267ecb75550521f37904` | Raw asciinema v3 capture of the take, unedited. 100×30, `xterm-256color`, 1,283 events. |
| `omp-ninfer-demo-v3.gif` | `481dc84654bef6c087985670a990bcdcfda75634e40be43b7f5d41bf2cee6717` | 1224×868, 20 fps GIF89a rendered from the banner-trimmed cast (below) with `agg` (JetBrains Mono 20 px, brand theme, `--idle-time-limit 1.75`), optimized with `gifsicle -O3`. The README embed. |
| `omp-ninfer-demo-v3.mp4` | `e7f8be69b4040edc8209e8ee75bcf04cffe8155d82b0758894491b4380266ae3` | H.264 `yuv420p` faststart transcode of the same render, even dimensions, silent; preferred social attachment. |
| `omp-ninfer-demo-v3-poster.png` | `722b8bf81e031510690b31cc770c92a982c2a39c82dc1cfcd6d975c216d3698d` | Single 1224×868 frame: the passing test run, the one-line fix summary, and the stateful follow-up question. |

## Trim and render

The raw cast opens with the pinned client's generic update banner
([#18](https://github.com/alphastorm/omp-ninfer/issues/18)). The rendered files begin after that
banner has left the frame: the cast's leading 633 events are re-timed to zero until 14.93 s of
idle-compressed playback have elapsed. The trim is state-preserving — event payloads and order are
byte-identical to the raw cast (trimmed intermediate SHA-256
`778d9f0ed1bececa7074f5c1b488e6378e4f8ab924075d753df5b75a8317a8ca`, reproducible below), so
terminal state is preserved while the banner interval contributes no frames.

```sh
agg --font-family "JetBrains Mono" --font-size 20 --fps-cap 20 --idle-time-limit 1.75 \
  --theme "060809,E8ECEF,0B0E11,C85045,85C29A,D8B575,87A5C4,8E7BE8,8FB8B2,B6BEC7,3A434D,E0685C,9FD3AE,E7C98A,9FBBD8,AB9DF0,A8CFC9,E8ECEF" \
  demo-trim.cast omp-ninfer-demo-v3.gif   # then gifsicle -O3
ffmpeg -i omp-ninfer-demo-v3.gif -an -vf 'format=yuv420p' \
  -c:v libx264 -preset medium -crf 18 -movflags +faststart omp-ninfer-demo-v3.mp4
```

The theme keeps the brand ground/ink and Local violet slots exactly and re-tunes the green,
yellow, blue, and cyan slots to the same restrained saturation family.

## Redaction discipline

The recorded environment used a neutral shared home directory outside any user account (the
macOS `Users/Shared` tree) and a system-interpreter `PATH`, so no username, hostname, endpoint,
port, key, or private path appears in any frame or in the raw cast byte stream. Verified over the
complete cast: zero occurrences of the maintainer username, host names, tunnel ports, key
material, or beta-suffixed identity strings, and 5,425 truecolor sequences confirming a
full-fidelity render.

## Historical media (v0.2-era recording)

The previous canonical recording and its launch derivatives remain published and immutable; their
hashes are unchanged. They were recorded against the identical runtime image during the
`v0.2.0-beta.1` window, when the client displayed a beta-suffixed provider name and the RTX 3090
lane was still preview-only.

| File | SHA-256 | Provenance |
| --- | --- | --- |
| `omp-ninfer-demo.cast` | `8b019c31973855779a8f8826f8a1950ef5b93806a8257cfe48ffd71322c692af` | Raw asciinema v3 capture, unedited. 100×30. |
| `omp-ninfer-demo.gif` | `d30836afe7abb07cdf137d06971d7be41d3a83846451e746254535d47bdc2ff7` | `agg` render (16 px), `gifsicle -O3 --lossy=70`. |
| `omp-ninfer-demo.mp4` | `a8d1b3bbe4f2dbd44a121a43a5c3d59beb6ade19c5e667b99fbfdae3ee932509` | H.264 `yuv420p` faststart master. Silent. |
| `omp-ninfer-demo-poster.png` | `321cca847cdbe500502057887e46a9613cdea34dc8198ec4de15c3667713b920` | Single frame: passing tests, fix summary, follow-up prompt. |
| `omp-ninfer-demo-social.mp4` | `e2e8fbc4cb42c5c30a12ac0299c081728d6f4f6627ae74c260a2abc97fa0bd81` | 978×694, 30 fps, begins 8.5 s in, after the update banner left the frame. |
| `omp-ninfer-demo-social-discord.gif` | `c5423f9e9289cecb68c42edb9631da0833c05b3ab0e61981465fa61f87ac7763` | 720×511, 10 fps GIF89a fallback. |
| `omp-ninfer-demo-social-poster.png` | `80b8ce9069b201802dcaecd9a7b5da080ea4aca0a1e7a4eeadaeef7538788373` | 978×694 frame from the clean social interval. |
| `omp-ninfer-launch-card.png` | `91c7b8be815e0a21ca6bfc753b21e3036f4c8a71ab8390b54bc1e3ea40e0b093` | 1600×900 evidence card; its warm/cold figure is one measured 89,216-token follow-up. |
| `omp-ninfer-demo-2x.gif` | `c806e5d585ca9ff4042951be0d1e80efb08667a00742d49197fb8bef8f1d45a5` | 1224×868, 20 fps; the v0.3.0-launch README embed, superseded by `-v3`. |
| `omp-ninfer-demo-2x.mp4` | `99cb0dbfff8ae01a979ff8f89bf46916c55a84503b5a2e38febdac2d59c3109e` | H.264 transcode of the 2x render. |
| `omp-ninfer-demo-2x-poster.png` | `a30db22bcdbb4455f80d042af6091438f41ae9508166150dafcc9b8e84b5213c` | Single 1224×868 frame. |

The historical capture carries its own disclosed adaptation: the capture host's WSL
mirrored-loopback path was unavailable during that session, so the runtime container was
relaunched from the identical image with bridge networking and a published host-loopback port.
Engine bytes, configuration, model, and authentication were unchanged.

## Receipts

The numbers these recordings illustrate are bound by receipts elsewhere: qualified results in
[`../BENCHMARKS.md`](../BENCHMARKS.md), the warm-vs-cold follow-up measurement in
[`../measurements/2026-08-29-warm-vs-cold-ttft.json`](../measurements/2026-08-29-warm-vs-cold-ttft.json),
and the RTX 3090 parity receipt in
[`../measurements/2026-08-30-rtx3090-parity.json`](../measurements/2026-08-30-rtx3090-parity.json).
Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.
