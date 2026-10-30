# Demo and launch media

These files are a **real v0.14.0 coding, server-restart, and continuation recording**
(recorded `2026-10-28T07:24:02Z`), not a mockup, composite, or scripted animation. Every frame was
produced by the released v0.14.0 software answering real requests on one maintainer RTX 5090,
including a `ninfer-serve` container restart mid-session and a follow-up answered from the
restored session. The task content is synthetic and content-safe by construction. This clip
demonstrates the end-to-end interactive flow on one machine; **qualified product and performance
claims are bound by the release receipts under `releases/v0.14.0/` and `docs/BENCHMARKS.md`, not
timed from this clip.**

The current GIF/MP4 files and changed poster frames were regenerated on **2026-10-30** from
the path-normalized public casts (P15-R12). This is a presentation-only correction, not a new
recording or runtime qualification. Published `releases/` records are unchanged.

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
| `omp-ninfer-demo-v14.cast` | `e01935efe16ec1cd7a48948991eb39fbb4fc42a4e972aced7b508944e83e00d8` | Path-normalized asciinema capture (`653,405` bytes, `100×30`, `1,345` events, `76.64 s`); capture-only command/environment headers removed. |
| `omp-ninfer-demo-v14-render.cast` | `3bdf99428470638ac96cee12186f2ddaf9fe7530e1e9990e1d7f6ce7c8574b5d` | Path-normalized render cast (`624,604` bytes, `1,315` kept events, `35.159 s`): payloads match the normalized capture; the `36.158 s` restart wait (`632..1084`) is scaled by `0.066375` to `2.4 s` and the `/exit` tail after event `1315` is dropped. |
| `omp-ninfer-demo-v14.gif` | `e2e6e2864102741ce137f558d02077fd76d05e9ace9ef53ba80e123d9dcc96e8` | `1714×1215`, `285` frames, `31.83 s` (including a `3 s` final hold), `2,215,462` bytes; re-rendered from `omp-ninfer-demo-v14-render.cast` with `agg` (JetBrains Mono `28 px`, `--fps-cap 20`, `--idle-time-limit 1.75`, `--last-frame-duration 3`) and lossless `gifsicle -O3`. The README embed. |
| `omp-ninfer-demo-v14.mp4` | `65fcb60362ce6cf9063c15608eb9a574936cad5dcf00d580e32c8a88ec85e673` | `1714×1216` (one row of `#060809` ground color padded for an even height), `30 fps` CFR (`955` frames), `31.83 s`, `1,822,674` bytes; re-encoded H.264 `yuv420p` faststart, silent. |
| `omp-ninfer-demo-v14-poster.png` | `f6c6389648f4c0e16c4a21d580b59efd6f04ffb839efd0a5300239a232ef6bdd` | Regenerated final frame (GIF frame `285` of `285`, zero-based `284`), `1714×1215`, `196,303` bytes: the passing test run, the `!ninfer-restart` recovery line, and the post-restart follow-up answer. |

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
9.0.2. The same versions and parameters were used for the path-normalized re-render.

```sh
agg --font-family "JetBrains Mono" --font-size 28 --fps-cap 20 --idle-time-limit 1.75 --last-frame-duration 3 \
  --theme 060809,E8ECEF,0B0E11,C85045,85C29A,D8B575,87A5C4,8E7BE8,8FB8B2,B6BEC7,3A434D,E0685C,9FD3AE,E7C98A,9FBBD8,AB9DF0,A8CFC9,E8ECEF \
  omp-ninfer-demo-v14-render.cast omp-ninfer-demo-v14.gif   # then gifsicle -O3 (lossless)
ffmpeg -i omp-ninfer-demo-v14.gif -an -vf 'fps=30,pad=ceil(iw/2)*2:ceil(ih/2)*2:0:0:color=#060809,format=yuv420p' \
  -c:v libx264 -preset slow -crf 18 -movflags +faststart omp-ninfer-demo-v14.mp4
ffmpeg -i omp-ninfer-demo-v14.gif -vf 'select=eq(n\,284)' \
  -fps_mode passthrough -frames:v 1 omp-ninfer-demo-v14-poster.png
```

The theme keeps the brand ground/ink and Local violet slots exactly and re-tunes the green,
yellow, blue, and cyan slots to the same restrained saturation family.

## Redaction discipline

The recorded environment used a neutral shared home directory outside any user account and a
`PATH` limited to the demo bin directory and the system directories. The v0.15.1 documentation
scrub removes command/environment metadata from every public cast header and normalizes displayed
home-path prefixes to `/demo-home`. Event order, timing, and all other event bytes are retained.
The release verifier scans both raw and decoded `.cast` text, including headers, for private
markers. The v14 streams retain their `5,522` truecolor sequences. The current rendered
representations now use those normalized casts too; neither the scrub nor the re-render is
a new recording or runtime qualification.

## Historical media (v0.3-era recording)

The v0.3.0 recording was re-rendered from its normalized cast (`15.303371 s`, `1224×868`,
`2,823,113` bytes MP4; the cast retains `5,425` truecolor sequences).
It was recorded with `omp-18.0.9-macos-arm64` (SHA-256
`ba85e7ab…c00c7`) against the v0.3.0 RTX 5090 runtime (image
`ghcr.io/alphastorm/ninfer-runtime@sha256:63c794e2…f08d`, server binary `d11dbba7…efdfa`, model
artifact `eec39564…bf3e`, profile `qwen38-5090-v0.2.0-beta.2`) fixing an off-by-one wraparound bug
in `ringbuf.py` and answering one stateful follow-up, with no server restart shown.

| File | SHA-256 | Provenance |
| --- | --- | --- |
| `omp-ninfer-demo-v3.cast` | `77bdd1d8695729b98bca986e06a18d48df3c27734f577c6955efc9576d87b5d8` | Path-normalized asciinema v3 capture; capture-only headers removed. 100×30, `xterm-256color`, 1,283 events. |
| `omp-ninfer-demo-v3.gif` | `26ba0feed9f28a8d84a4e17e3d2a6bf527ada18bb192c477968e02f7051554ad` | Re-rendered 1224×868, 142-frame, 17.02 s GIF89a from the banner-trimmed cast (below) with `agg` (JetBrains Mono 20 px, 20 fps cap, brand theme, `--idle-time-limit 1.75`), optimized with `gifsicle -O3`. |
| `omp-ninfer-demo-v3.mp4` | `ae2e6858a64a72cad453907d0a152b3eda493e97467fabda2fc2335419dfe4de` | Re-encoded H.264 `yuv420p` faststart transcode of the same render, 142 VFR frames, even dimensions, silent. |
| `omp-ninfer-demo-v3-poster.png` | `722b8bf81e031510690b31cc770c92a982c2a39c82dc1cfcd6d975c216d3698d` | Unchanged 1224×868 poster: its source GIF frame 100 (zero-based) is pixel-identical after normalization. The passing test run, the one-line fix summary, and the stateful follow-up question. |

The rendered v0.3 files begin after the pinned client's generic update banner
([#18](https://github.com/alphastorm/omp-ninfer/issues/18)) left the frame: the cast's leading 633
events were re-timed to zero across the first 14.93 s of idle-compressed playback, keeping event
payloads and order byte-identical to the normalized cast. At recording time the
appliance's incumbent container was a post-release development build, so the owner's
stop/record/restore flow served the pinned v0.3.0 image temporarily on a separate loopback port
with a fresh temporary key and restored the incumbent container afterward.

## Historical media (v0.2-era recording)

The previous recording and its launch derivatives were also re-rendered from the normalized
public cast. They were recorded against the identical runtime image during the
`v0.2.0-beta.1` window, when the client displayed a beta-suffixed provider name and the RTX 3090
lane was still preview-only.

| File | SHA-256 | Provenance |
| --- | --- | --- |
| `omp-ninfer-demo.cast` | `64be5fe325a6298ceea1a55adf05e864d7afc7d5e12da091375b16308c1447f9` | Path-normalized asciinema v3 capture; capture-only headers removed. 100×30. |
| `omp-ninfer-demo.gif` | `8a94dd01f1285b1dd6d6f35d5d6be559994f527f9ccd38d09bb82dd324f2904d` | Re-rendered 979×694, 456 frames, 31.09 s; `agg` (16 px, 30 fps cap), `gifsicle -O3 --lossy=70`. |
| `omp-ninfer-demo.mp4` | `deae37e4cd401b48f8a11adb9aa812f4db65a1a8b923e51394b40798a0b81524` | Re-encoded 978×694 H.264 `yuv420p` faststart master from the full-quality render, 456 VFR frames, 26.88 s declared duration. Silent. |
| `omp-ninfer-demo-poster.png` | `baf7fd262fdc607bfd25b922a2a1ef4025d93e31d92ea866a4e92c16d74783d9` | Regenerated full-quality GIF frame 262 (zero-based), 979×694: passing tests, fix summary, follow-up prompt. |
| `omp-ninfer-demo-social.mp4` | `96256e86734261c71c2b338f3764b68799b64698fdfb8ff7cc4a4f9844ff9bb5` | Re-encoded 978×694, 30 fps, 587 frames, 19.566667 s; begins 8.5 s in, after the update banner left the frame. |
| `omp-ninfer-demo-social-discord.gif` | `524148d704539022adf09390d056b6562d4d3a75bb77c769bea66425792f51fe` | Regenerated 720×511, 10 fps, 196-frame, 19.6 s GIF89a fallback, 64-color palette. |
| `omp-ninfer-demo-social-poster.png` | `6da345eaafc87cd3b676f338110bf7ad4d667de642267e27d4cc60ba7acf2e13` | Regenerated 978×694 frame from the clean social interval (social MP4 frame 100, zero-based). |
| `omp-ninfer-launch-card.png` | `91c7b8be815e0a21ca6bfc753b21e3036f4c8a71ab8390b54bc1e3ea40e0b093` | 1600×900 evidence card; its warm/cold figure is one measured 89,216-token follow-up — retained state versus fresh-process cold start. |
| `omp-ninfer-demo-2x.gif` | `54e17ed3b0ca709b6efec5e9cedf966d848c2700d93e7840f1514782f4e07b38` | Re-rendered 1224×868, 20 fps cap, 226 frames, 22.59 s; the v0.3.0-launch README embed, superseded by `-v3`. Font size 20, not double-speed playback. |
| `omp-ninfer-demo-2x.mp4` | `89625a2a96c46e134ee1f2dcabdbe88808f48236ec173ee4e0ac1227486d465b` | Re-encoded H.264 transcode of the 2x render, 226 VFR frames, 17.94 s declared duration. |
| `omp-ninfer-demo-2x-poster.png` | `970cc0b8aa581463b13559024b372616624062f696a13a86471fabc0b1ab42c6` | Regenerated GIF frame 120 (zero-based), 1224×868. |

The historical capture carries its own disclosed adaptation: the capture host's WSL
mirrored-loopback path was unavailable during that session, so the runtime container was
relaunched from the identical image with bridge networking and a published host-loopback port.
Engine bytes, configuration, model, and authentication were unchanged.

## Reproducing the historical re-renders

Run in `docs/media/` with the tool versions listed above. The historical command lineage is
preserved in commits `6a78aab` (16 px render), `865cc45` (social and 20 px derivatives), and
`50c6af8` (v3 trim). All casts here are the normalized representations, not the old capture
bytes. The `-2x` trim removes exactly `8.5 s` of idle-compressed playback: zero the first `371`
event intervals and shorten the next interval to `0.026 s`. The v3 trim zeroes the first `633`
intervals (`14.931 s` idle-compressed). Payloads and order stay unchanged.

```sh
python3 - <<'PY'
import json
from pathlib import Path

for source, target, count in [
    ("omp-ninfer-demo.cast", "demo-trim.cast", 371),
    ("omp-ninfer-demo-v3.cast", "demo-v3-trim.cast", 633),
]:
    records = [json.loads(line) for line in Path(source).read_text().splitlines()]
    for event in records[1:count + 1]:
        event[0] = 0.0
    if count == 371:
        records[count + 1][0] = 0.026
    Path(target).write_text("\n".join(
        json.dumps(record, ensure_ascii=False, separators=(",", ":")) for record in records
    ) + "\n")
PY

legacy_theme='060809,E8ECEF,0B0E11,C85045,8FBF7F,D8A657,7DAEA3,8E7BE8,86B3A8,B6BEC7,3A434D,EA6962,A9B665,E7B84C,89AEB8,AB9DF0,95D1C9,E8ECEF'
brand_theme='060809,E8ECEF,0B0E11,C85045,85C29A,D8B575,87A5C4,8E7BE8,8FB8B2,B6BEC7,3A434D,E0685C,9FD3AE,E7C98A,9FBBD8,AB9DF0,A8CFC9,E8ECEF'

agg --font-family "JetBrains Mono" --font-size 16 --fps-cap 30 \
  --idle-time-limit 1.75 --last-frame-duration 3 --theme "$legacy_theme" \
  omp-ninfer-demo.cast demo-full.gif
gifsicle -O3 --lossy=70 -o omp-ninfer-demo.gif demo-full.gif
ffmpeg -i demo-full.gif -an -vf 'scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p' \
  -c:v libx264 -preset medium -crf 23 -movflags +faststart omp-ninfer-demo.mp4

agg --font-family "JetBrains Mono" --font-size 20 --fps-cap 20 \
  --idle-time-limit 1.75 --last-frame-duration 3 --theme "$brand_theme" \
  demo-trim.cast demo-2x-full.gif
gifsicle -O3 -o omp-ninfer-demo-2x.gif demo-2x-full.gif
ffmpeg -i omp-ninfer-demo-2x.gif -an -vf format=yuv420p \
  -c:v libx264 -preset medium -crf 23 -movflags +faststart omp-ninfer-demo-2x.mp4

agg --font-family "JetBrains Mono" --font-size 20 --fps-cap 20 \
  --idle-time-limit 1.75 --last-frame-duration 3 --theme "$brand_theme" \
  demo-v3-trim.cast demo-v3-full.gif
gifsicle -O3 -o omp-ninfer-demo-v3.gif demo-v3-full.gif
ffmpeg -i omp-ninfer-demo-v3.gif -an -vf format=yuv420p \
  -c:v libx264 -preset medium -crf 18 -movflags +faststart omp-ninfer-demo-v3.mp4

ffmpeg -ss 8.5 -i omp-ninfer-demo.mp4 -an -vf 'fps=30,format=yuv420p' \
  -c:v libx264 -preset medium -crf 18 -movflags +faststart \
  -frames:v 587 omp-ninfer-demo-social.mp4
ffmpeg -i omp-ninfer-demo-social.mp4 \
  -filter_complex 'fps=10,scale=720:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=64[p];[b][p]paletteuse' \
  omp-ninfer-demo-social-discord.gif

ffmpeg -i demo-full.gif -vf 'select=eq(n\,262)' \
  -fps_mode passthrough -frames:v 1 omp-ninfer-demo-poster.png
ffmpeg -i omp-ninfer-demo-2x.gif -vf 'select=eq(n\,120)' \
  -fps_mode passthrough -frames:v 1 omp-ninfer-demo-2x-poster.png
ffmpeg -i omp-ninfer-demo-social.mp4 -vf 'select=eq(n\,100)' \
  -fps_mode passthrough -frames:v 1 omp-ninfer-demo-social-poster.png
```

The legacy MP4s intentionally retain their original VFR encoding and declared durations; unlike
the v14 transcode, they do not add a CFR final hold. Their last decoded presentation timestamps
can exceed the container's declared duration. The social transcode explicitly retains the
original `587` CFR frames: re-encoding the normalized master changes B-frame packet-tail timing,
so an uncapped trim can otherwise add two frames. All five GIFs retain the original dimensions,
frame counts and durations; the four cast-derived GIFs also retain every original frame delay.

The original social provenance specifies the trim, scale and frame rate, but not its complete
palette/dither expression or exact poster timestamp. The reconstruction uses the original GIF's
measured `64` colors with FFmpeg's default palette dithering and selects social frame `100`,
matching the original poster's depicted interval. These are disclosed reconstruction choices,
not recovered historical commands. The base, 2x and v14 poster source frames changed and were
regenerated; the v3 poster's source frame was pixel-identical and its existing PNG was retained.
No media was removed: every retained demo file still has a media or brand inventory reference.

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
