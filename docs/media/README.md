# Demo and launch media

These files are a **real v0.14.0 coding, server-restart, and continuation recording**
(recorded `2026-10-28T07:24:02Z`), not a mockup, composite, or scripted animation. Every frame was
produced by the released v0.14.0 software answering real requests on one maintainer RTX 5090,
including a `ninfer-serve` container restart mid-session and a follow-up answered from the
restored session. The task content is synthetic and content-safe by construction. This clip
demonstrates the end-to-end interactive flow on one machine; **qualified product and performance
claims are bound by the release receipts under `releases/v0.14.0/` and `docs/BENCHMARKS.md`, not
timed from this clip.**

## Canonical recording (v0.14)

- **Client:** unmodified upstream Oh My Pi `18.12.6` (`v18.12.6`) release binary `omp-darwin-arm64`
  (SHA-256 `cfbb5e38cd8f8a3be55e710700be587d287deaacdc58c9b0a661c5086bccfe58`, verified against
  `releases/v0.14.0/qualification/client-components.json`), run with a neutral shared home
  directory outside any user account. The shipped `examples/manual-tunnel/models.fragment.yml`
  (provider `ninfer-beta`, model `q38-ninfer`, `compat.statefulResponses: true`) and
  `examples/manual-tunnel/fail-closed.yml` (retries and model fallback off, update check off, and
  `maxInFlightRequests` cap) were installed verbatim with the appliance bearer key in
  `ninfer-beta.key` (mode `600`). Launched as
  `omp --model ninfer-beta/q38-ninfer --hide-thinking --thinking low` with `OMP_SKIP_SETUP=1`.
- **Runtime:** the v0.14.0 RTX 5090 component `v0.7.0-qwen38-5090-beta.3` — container image
  `ghcr.io/alphastorm/ninfer-runtime@sha256:760fb6bea925eb26d4fa53ab87a126494b69ba7bcfed515d23dee7afa65cdb2a`,
  server binary `55f0b95ac3609673ff544d9a512fb28aee9580b5948719dfac537858b6714467`, configuration
  `751d22dc405595c17ef129b9b57d3582908567e47e6aa39507c02b9b9da82a47`, model artifact
  `81f924d440c27261d820c19a9f8d45794c5aee410f8a68bd358133fa8c0375da` (`q38-ninfer`), deployment
  profile `qwen38-5090-v0.13.0` (retained in v0.14.0), engine source (`patch_stack_sha`)
  `2c6f423bd817b6534158553e1b34ab4959c43165` on upstream `64d10fbf9f8e6bfc79ab0570b94674c5b9997929`
  (`rtx5090`, CUDA `120a`, `source_dirty: false`), DFlash2 draft window `7`, BF16 KV cache
  (`146,368` tokens capacity, `131,072` max context), two requests in flight (`max_concurrency: 2`)
  — identity confirmed over the authenticated `/v1/ninfer/status` route before and after the take on
  the maintainer's Windows 11 Docker Desktop/WSL2 RTX 5090 appliance.
- **Route:** Mac loopback (the product's documented loopback port) → OpenSSH local forward →
  appliance host loopback → Docker published port → bearer-authenticated `ninfer-serve`. Capture
  adaptations are disclosed below.
- **Session:** `100×30` truecolor terminal (terminal type `xterm-kitty`, with `TERM=xterm-256color`
  and `COLORTERM=truecolor`) in a synthetic scratch git repository with `lru.py` (an `OrderedDict`
  LRU cache whose `get()` does not refresh recency) and `test_lru.py` (three `unittest` cases, one
  failing). Turn 1 prompt: `"One test in test_lru.py fails: the cache evicts the wrong entry. Find
  the bug in lru.py, fix it, and run the tests."` — the agent read both files, explained the bug,
  made a one-line edit at `lru.py:16` (`self._items.move_to_end(key)`), ran
  `python3 -m unittest -v` (`3/3` ok), and summarized the fix (`8.2 s` wall from Enter to idle).
  Next, the user bang command `!ninfer-restart` restarted the `ninfer-serve` container on the
  appliance and reported `"serving again after 36 s"` (`36.3 s` wall). Turn 2 prompt: `"In one
  sentence: why did only the third test catch it?"` — answered in context after the restart
  (`4.7 s` wall; the first two tests never rely on `get()` refreshing recency before eviction).
  Context usage ended at `8%` of `131,072` tokens in the OMP status line (wall times use a `3.0 s`
  idle threshold). Keystrokes were typed by a pty driver at roughly 36 characters/s with jitter;
  no text was pasted.

## Capture adaptation (disclosed)

The maintainer's production container keeps the released image, server binary, configuration,
model, and deployment profile (`qwen38-5090-v0.13.0`), but publishes its port on the Windows host
instead of the product profile's loopback-only binding and runs with `restart=unless-stopped`; the
Mac client connected to the product's documented loopback port through the SSH local forward.
Engine bytes, configuration, model, and bearer authentication were the released identity
throughout. Owner fleet admission was paused before the take, the same container ID was reconciled
after the restart, and admission resumed after the take.

The `!ninfer-restart` command is a demo shell helper outside the project directory that prints a
restart notice, runs `docker restart --timeout 60` on the inference host over SSH, polls `/health`
through the tunnel, and prints a second line summarizing the authenticated `/v1/ninfer/status`
response (`max_context` and the engine source `patch_stack_sha` prefix). Both output lines are the
helper's own text; the SSH destination comes from an environment variable and never appears on
screen.

On the client side, `--hide-thinking` hid reasoning blocks in the terminal UI while the model's
reasoning ran unchanged, `--thinking low` selected the fragment's lowest effort level, and
`OMP_SKIP_SETUP=1` skipped the first-run wizard in the fresh demo home directory.

## Continuation after the restart

The authenticated `/v1/ninfer/status` read over the tunnel after the recording
([`../measurements/2026-10-28-readme-demo-v14.json`](../measurements/2026-10-28-readme-demo-v14.json))
shows that since the restarted container started (`2026-10-28T07:24:32.911Z`), the follow-up turn
reused **10,375 retained prompt tokens** over the session's own continuation endpoint
(`cache.last_selection.path = private_endpoint`, `frontier_tokens = 10375`) and computed only
**155 new prefill tokens** (`committed_decode_tokens = 314` across `84` decode rounds). The
session was below the `32,768`-token automatic checkpoint gate; its state survived because the
graceful stop (`docker restart --timeout 60`, `SIGTERM` with a `60 s` grace period) flushed it to
the release-isolated checkpoint store before exit, and the restarted server restored it from that
store. Without a graceful stop, the same turn would have been replayed from Oh My Pi's committed
transcript. This status read is a maintainer observation, not a qualification receipt; product
claims stay bound by `releases/v0.14.0/`.

## Canonical files

| File | SHA-256 | Provenance |
| --- | --- | --- |
| `omp-ninfer-demo-v14.cast` | `40d38c380ec13053b7542e5a86213f747329baa1bbc46c0c4b453ef561295ff1` | Raw asciinema capture of the take, unedited (`653,823` bytes, `100×30`, `1,345` events, `76.64 s`). |
| `omp-ninfer-demo-v14-render.cast` | `5474eeb485453f92c127157b1aa3a5acb9799ec4a224c8ea19ca3f53c09c465e` | Render cast (`625,022` bytes, `1,315` kept events, `35.159 s`): byte-identical event payloads and order; only the `36.158 s` restart wait (`632..1084`) is scaled by `0.066375` to `2.4 s` and the `/exit` shutdown tail after event `1315` is dropped. |
| `omp-ninfer-demo-v14.gif` | `c1fb503ae66feeec80f55a2c3af84386357f412b3c8a56aa4831d86bd9d9f694` | `1714×1215`, `285` frames, `31.83 s` (including a `3 s` final hold), `2,232,959` bytes; rendered from `omp-ninfer-demo-v14-render.cast` with `agg` (JetBrains Mono `28 px`, `--fps-cap 20`, `--idle-time-limit 1.75`, `--last-frame-duration 3`) and lossless `gifsicle -O3`. The README embed. |
| `omp-ninfer-demo-v14.mp4` | `e571f21ceb8558b4db1bf541716a110a59949e55b4dddc64034dedd2cac3823c` | `1714×1216` (one row of `#060809` ground color padded for an even height), `30 fps` CFR (`955` frames), `31.83 s`, `1,837,044` bytes; H.264 `yuv420p` faststart, silent. |
| `omp-ninfer-demo-v14-poster.png` | `35dce796a491338bd3ee42ec3295559b3cabe69b9779abd38cde49923f6ed88e` | Final frame (GIF frame `285` of `285`), `1714×1215`, `196,316` bytes: the passing test run, the `!ninfer-restart` recovery line, and the post-restart follow-up answer. |

## Render cast and render

`omp-ninfer-demo-v14-render.cast` is derived from `omp-ninfer-demo-v14.cast` with byte-identical
event payloads and order and only two timing changes:

1. The `36.158 s` restart wait between events `632..1084` (from the helper's first output line to
   its `"serving again"` line, while the TUI showed only a running indicator) is scaled by
   `0.066375` to `2.4 s`.
2. The tail after event `1315` (events `1316..1345`, the `/exit` keystrokes and shutdown after the
   final answer render) is dropped.

Together, these two timing changes reduce the cast duration from `76.639 s` (`76.64 s`, `1,345`
events) to `35.159 s` (`1,315` kept events) before `agg` idle compression.

Rendered with `asciinema` 3.2.1, `agg` 1.9.0, LCDF `Gifsicle` 1.98 (lossless `-O3`), and `ffmpeg`
9.0.2:

```sh
agg --font-family "JetBrains Mono" --font-size 28 --fps-cap 20 --idle-time-limit 1.75 --last-frame-duration 3 \
  --theme 060809,E8ECEF,0B0E11,C85045,85C29A,D8B575,87A5C4,8E7BE8,8FB8B2,B6BEC7,3A434D,E0685C,9FD3AE,E7C98A,9FBBD8,AB9DF0,A8CFC9,E8ECEF \
  omp-ninfer-demo-v14-render.cast omp-ninfer-demo-v14.gif   # then gifsicle -O3 (lossless)
ffmpeg -i omp-ninfer-demo-v14.gif -an -vf 'fps=30,pad=ceil(iw/2)*2:ceil(ih/2)*2:0:0:color=#060809,format=yuv420p' \
  -c:v libx264 -preset slow -crf 18 -movflags +faststart omp-ninfer-demo-v14.mp4
```

The theme keeps the brand ground/ink and Local violet slots exactly and re-tunes the green,
yellow, blue, and cyan slots to the same restrained saturation family.

## Redaction discipline

The recorded environment used a neutral shared home directory outside any user account and a
`PATH` limited to the demo bin directory and the system directories. Verified over the complete
raw cast byte stream: zero occurrences of the maintainer username, host names or tailnet suffixes,
tunnel and appliance port numbers, bearer key material, pyenv or Homebrew interpreter paths, or
user home directories, and `5,522` truecolor sequences confirming a full-fidelity render. The
scratch project path under a neutral shared home directory outside any user account is visible in
one tool panel.

## Historical media (v0.3-era recording)

The v0.3.0 recording remains published and immutable (`15.303371 s`, `1224×868`, `2,829,121` bytes
MP4; `5,425` truecolor sequences). It was recorded with `omp-18.0.9-macos-arm64` (SHA-256
`ba85e7ab…c00c7`) against the v0.3.0 RTX 5090 runtime (image
`ghcr.io/alphastorm/ninfer-runtime@sha256:63c794e2…f08d`, server binary `d11dbba7…efdfa`, model
artifact `eec39564…bf3e`, profile `qwen38-5090-v0.2.0-beta.2`) fixing an off-by-one wraparound bug
in `ringbuf.py` and answering one stateful follow-up, with no server restart shown.

| File | SHA-256 | Provenance |
| --- | --- | --- |
| `omp-ninfer-demo-v3.cast` | `c541c0ea8b213582af078e2f86d7b30a56a91b5defb4267ecb75550521f37904` | Raw asciinema v3 capture of the take, unedited. 100×30, `xterm-256color`, 1,283 events. |
| `omp-ninfer-demo-v3.gif` | `481dc84654bef6c087985670a990bcdcfda75634e40be43b7f5d41bf2cee6717` | 1224×868, 20 fps GIF89a rendered from the banner-trimmed cast (below) with `agg` (JetBrains Mono 20 px, brand theme, `--idle-time-limit 1.75`), optimized with `gifsicle -O3`. |
| `omp-ninfer-demo-v3.mp4` | `e7f8be69b4040edc8209e8ee75bcf04cffe8155d82b0758894491b4380266ae3` | H.264 `yuv420p` faststart transcode of the same render, even dimensions, silent. |
| `omp-ninfer-demo-v3-poster.png` | `722b8bf81e031510690b31cc770c92a982c2a39c82dc1cfcd6d975c216d3698d` | Single 1224×868 frame: the passing test run, the one-line fix summary, and the stateful follow-up question. |

The rendered v0.3 files begin after the pinned client's generic update banner
([#18](https://github.com/alphastorm/omp-ninfer/issues/18)) left the frame: the cast's leading 633
events were re-timed to zero across the first 14.93 s of idle-compressed playback, keeping event
payloads and order byte-identical to the raw cast (trimmed intermediate SHA-256
`778d9f0ed1bececa7074f5c1b488e6378e4f8ab924075d753df5b75a8317a8ca`). At recording time the
appliance's incumbent container was a post-release development build, so the owner's
stop/record/restore flow served the pinned v0.3.0 image temporarily on a separate loopback port
with a fresh temporary key and restored the incumbent container afterward.

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
| `omp-ninfer-launch-card.png` | `91c7b8be815e0a21ca6bfc753b21e3036f4c8a71ab8390b54bc1e3ea40e0b093` | 1600×900 evidence card; its warm/cold figure is one measured 89,216-token follow-up — retained state versus fresh-process cold start. |
| `omp-ninfer-demo-2x.gif` | `c806e5d585ca9ff4042951be0d1e80efb08667a00742d49197fb8bef8f1d45a5` | 1224×868, 20 fps; the v0.3.0-launch README embed, superseded by `-v3`. |
| `omp-ninfer-demo-2x.mp4` | `99cb0dbfff8ae01a979ff8f89bf46916c55a84503b5a2e38febdac2d59c3109e` | H.264 transcode of the 2x render. |
| `omp-ninfer-demo-2x-poster.png` | `a30db22bcdbb4455f80d042af6091438f41ae9508166150dafcc9b8e84b5213c` | Single 1224×868 frame. |

The historical capture carries its own disclosed adaptation: the capture host's WSL
mirrored-loopback path was unavailable during that session, so the runtime container was
relaunched from the identical image with bridge networking and a published host-loopback port.
Engine bytes, configuration, model, and authentication were unchanged.

## Receipts

Performance and restart claims are established by separate receipts, not timed from this clip:
qualified results in
[`../BENCHMARKS.md`](../BENCHMARKS.md), the v0.14.0 README demo recording receipt in
[`../measurements/2026-10-28-readme-demo-v14.json`](../measurements/2026-10-28-readme-demo-v14.json),
the warm-vs-cold follow-up measurement in
[`../measurements/2026-08-29-warm-vs-cold-ttft.json`](../measurements/2026-08-29-warm-vs-cold-ttft.json),
and the RTX 3090 parity receipt in
[`../measurements/2026-08-30-rtx3090-parity.json`](../measurements/2026-08-30-rtx3090-parity.json).
Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.
