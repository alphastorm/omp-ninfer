# OMP NInfer — brand spec

Identity for `alphastorm/omp-ninfer`: the integration and release layer
connecting OMP clients on native Windows, macOS, or Linux over an
authenticated loopback route to NInfer running Qwen3.8 on a user-owned
NVIDIA GPU. It owns setup, release manifests, hardware profiles,
qualification, security boundaries, and support — not duplicated OMP or
NInfer implementations.

**Brand sibling of `omp-session-gateway`.** OMP NInfer shares that family's ground, neutrals,
type, kinship rule, and voice register; this file is the complete authority for the OMP NInfer
identity. The retired fork and code-mode colors — signal blue `#3FA9DC` and exec amber `#E0A33E` —
stay retired. Do not reuse them.

## Naming canon

- Repository: `alphastorm/omp-ninfer`
- Display name: **OMP NInfer** (capital N, capital I)
- Alternate lockup: **OMP × NInfer** — the × is Local violet, weight 500
- Category (the market we claim): **durable local inference for coding agents**
- Product descriptor: **the qualified local inference appliance for Oh My Pi**
- Headline: **Your coding session should survive the process.**
- Tagline: **Durable session state on your GPU.**
- Messaging stack — every first screen answers, in order: category, headline, entity
  (what it is, for whom), proof (one receipt line from the current release), one action.
  The enemy is the cold context rebuild and implicit-cache roulette; the promise is one
  private, long-lived coding session that is explicitly resumable across process restarts.
- Entity grammar: state the four-part relationship in nearly identical words on every
  surface — *Oh My Pi (coding-agent client) → OMP NInfer (qualified appliance and release
  layer) → NInfer (inference engine) → Qwen3.8 27B (served model).* Spell out "Oh My Pi"
  before using "OMP" on any page that can be read standalone.
- Positioning rule: never claim "no re-prefill" as the value. In-process prefix caching
  (upstream ninfer `prefix_reuse`, llama.cpp prompt cache, vLLM APC) already covers the
  live-process append-only case and is conceded as prior art. The product claim is explicit,
  transactional, durable continuation — checkpoints that survive process death, portability as
  the trajectory. Warm/cold figures are always captioned retained state versus fresh-process
  cold start, never versus an ordinary follow-up.
- Non-fit is part of the brand: say plainly when Ollama, LM Studio, llama.cpp, or vLLM is
  the better choice (breadth, GUI, portability, multi-user throughput). The narrow target
  is what makes the recommendation credible; never publish a self-assigned score.
- Status grammar: when lane status is stated, write **"Qualified on RTX 5090 · 4090 · 3090"**.
  When install authority matters, bind it to the current ready release (`v0.4.7`) instead of
  restating per-lane caveats inline; per-lane evidence lives in the manifest and benchmarks.
- Primary conversion action: **Get started**, linked to `docs/QUICKSTART.md`. Put it before
  documentation links whenever the surface has room for only one action. The GitHub `Latest`
  release card is the secondary conversion surface; never add a third competing action.
- The user-facing command remains `omp`; "appliance" describes the operating
  concept, never the repository name.

## The mark: "The Socket"

The Gate's grammar plugged into hardware: a leg (the OMP client), a link (the
authenticated loopback), and a hollow die (the private hardware boundary)
holding the dot — session state resident on the user's own GPU. Geometry
(96×96 viewBox):

- leg `x12 y12 w10 h72 rx2`
- link `x22 y43 w26 h10 rx2`
- die: stroked rect, path `x51 y31 w28 h34 rx2`, stroke-width 10
  (outer bounds 46..84 × 26..70)
- dot `cx65 cy48 r8` in Local violet — deliberately snug inside the die

Rules (inherited from the Gate, same numbers): never derive from upstream
OMP's π-with-plug mark; clearspace one dot diameter (16 units); minimum size
16px; the dot is always Local violet; frame is Ink on dark (`logo.svg`),
Ink-dark on light (`logo-light.svg`); never recolor; never use Live emerald
`#31C48D` — that dot belongs to the gateway.

## Color

Same blue-black ground and neutral ramp as the gateway (`ground #060809`,
`ink-dark #0B0E11`, `surface #0E1319`, `ink #E8ECEF`, `body #B6BEC7`,
`muted #8A939D`). NInfer-owned:

| Token | Hex | oklch | Use |
|---|---|---|---|
| local | `#8E7BE8` | oklch(0.65 0.15 290) | the dot, the ×, links, focus, boundary lines |
| local-hover | `#AB9DF0` | — | link hover lighten |
| fail | `#C85045` | oklch(0.58 0.14 27) | failed qualification/fail-closed states (shared) |
| kinship | `#F97316` | — (upstream orange) | citation micro-dot only; see gateway kinship rule |

Local violet is deliberately not NVIDIA green and not Qwen purple-gradient —
no implied partnership. Restrained, no gamer RGB.

## Type & voice

Space Grotesk 500/600 (headings, wordmark, −0.015em) + JetBrains Mono 400/500
(eyebrows, stats, paths; labels 10–12px uppercase, letter-spacing 0.1–0.2em).
Webfonts on marketing surfaces only.

Composition is editorial, not dashboard-like: one message wins the first read, one proof wins the
second, and metadata recedes. Use open ground, large type, thin rules, and asymmetry before adding
containers. Violet is an action or retained-state accent, not decoration. Avoid equal-weight card
grids, glowing tiles, ornamental gradients, and more than one primary call to action. At thumbnail
size, the headline and one proof must remain legible without reading labels.

Voice: the gateway's sober register, operator-flavored. Sentence case, no
emoji, no exclamation marks. Claims stated as invariants:

- "Your model prompt stays on hardware you own."
- "Three qualified GPU candidates, each bound to exact bytes and a receipt."
- "The tunnel is authenticated and fail-closed; identity is visible."
- "Stateful local coding through OpenAI Responses."

Hard constraints — never write:

- stable/v1.0 support, SLAs, or upgrade commitments — the 0.x series carries an explicit
  support boundary: the latest published release and its exact manifest/profile only
- support outside the exact RTX 5090, RTX 4090, and RTX 3090 profiles bound by the current
  ready manifest
- wording that transfers one lane's measured numbers, restart semantics, or capabilities to
  another lane
- cloud hosting, multi-tenant serving, unattended production activation, or universal RTX support
- "first stateful Responses", automatic restart, or universal performance
- `omp appliance ...` outside the exact compatibility authority or as an implicit production
  activation path

Standing disclaimer: "Community project; not affiliated with or endorsed by
Oh My Pi, Qwen, or NVIDIA." Never set NVIDIA, Qwen, or OMP marks in ways that
imply official partnership.

## Asset inventory

| File | Purpose |
|---|---|
| `assets/logo.svg` | mark, transparent, for dark backgrounds |
| `assets/logo-light.svg` | mark for light backgrounds |
| `assets/lockup.png` / `lockup-light.png` | horizontal lockup, transparent @2x |
| `assets/lockup-x.png` / `lockup-x-light.png` | OMP × NInfer alternate, transparent @2x |
| `assets/lockups.html` | lockup source |
| `assets/brand.css` | shared color, type, spacing, and guide tokens for campaign assets |
| `assets/banner.html` | README banner source (1280×320) |
| `assets/banner.png` | rendered banner @2x (2560×640) |
| `assets/og.html` | GitHub social preview source (1280×640) |
| `assets/og.png` | GitHub social preview (1280×640) |
| `assets/architecture.html` | architecture illustration source (1240×420) |
| `assets/architecture.png` | rendered architecture @2x (2480×840) — for the README |
| `assets/benchmarks.html` | released-evidence continuation story source (1240×360) |
| `assets/benchmarks.png` | rendered released-evidence strip @2x — for the README and benchmarks page |
| `assets/chart-warm-cold.html` / `chart-warm-cold.png` | warm vs cold TTFT chart source (1240×420) and @2x render — benchmarks page |
| `assets/chart-prefill.html` / `chart-prefill.png` | 5090 prefill-curve chart source (1240×420) and @2x render — benchmarks page |
| `assets/chart-decode.html` / `chart-decode.png` | per-lane decode chart source (1240×420) and @2x render — benchmarks page |
| `assets/favicon.svg` | favicon (96, rx22 tile) |
| `assets/icon.svg` | icon source (512, rx116 tile) |
| `assets/icon-512.png` | rendered icon — repo/org avatar |
| `assets/favicon-32.png` / `favicon-16.png` | PNG favicon fallbacks |
| `docs/media/omp-ninfer-demo.gif` | canonical full-session GIF render; retained for provenance |
| `docs/media/omp-ninfer-demo.mp4` | real-session demo master (MP4) |
| `docs/media/omp-ninfer-demo-poster.png` | demo poster frame for posts and video embeds |
| `docs/media/omp-ninfer-demo.cast` | raw asciinema capture behind the demo (provenance: `docs/media/README.md`) |
| `docs/media/omp-ninfer-demo-social.mp4` | updater-free social derivative of the canonical demo |
| `docs/media/omp-ninfer-demo-social-discord.gif` | update-banner-free README/Discord fallback |
| `docs/media/omp-ninfer-demo-social-poster.png` | poster from the clean social interval |
| `docs/media/omp-ninfer-launch-card.png` | scoped launch evidence card; provenance in `docs/media/README.md` |
| `docs/media/omp-ninfer-demo-2x.gif` | crisp 1224×868 20 fps README embed rendered straight from the cast |
| `docs/media/omp-ninfer-demo-2x.mp4` | H.264 transcode of the 2x render; preferred social attachment |
| `docs/media/omp-ninfer-demo-2x-poster.png` | poster frame from the 2x render |

Regeneration: run `python3 scripts/render_assets.py`. It renders the banner, architecture,
benchmark, and social-preview HTML sources with headless Chrome and verifies every PNG dimension;
`python3 scripts/render_assets.py --check` fails when a committed raster is stale. Render
`#lk-dark`/`#lk-light`/`#lkx-dark`/`#lkx-light` from `assets/lockups.html` at
2× for transparent lockups, `icon.svg` at 512, and `favicon.svg` at 32/16. Expected raster
dimensions are 2560×640 for the banner, 2480×840 for architecture, 2480×720 for the benchmark
story, 1720×360 for each lockup, and 1280×640 for the social preview.

Demo captures are real sessions, never mockups presented as recordings: record against a real
qualified-profile runtime, use synthetic task content only, and verify no hostname, username,
private path, key, or personal data appears in any frame. Any number shown must match a published
receipt or be visibly produced by the recorded session itself. Composites and illustrations must
be labelled as such in the media provenance file; provenance for every demo lives in
`docs/media/README.md`.

## README header (drop-in)

```md
![OMP NInfer](assets/banner.png)

<div align="center">

# OMP NInfer

**Durable session state on your GPU.**

**Qualified on RTX 5090 · 4090 · 3090**

If you use [Oh My Pi](https://github.com/can1357/oh-my-pi) and own a qualified RTX card,
OMP NInfer keeps Qwen3.8 27B and your session's continuation state on your GPU — as an explicit,
durable primitive, not a lucky prefix-cache hit.

**[Get started](docs/QUICKSTART.md)**

**[Download v0.4.7](https://github.com/alphastorm/omp-ninfer/releases/latest)** ·
**[Benchmarks](docs/BENCHMARKS.md)** · **[Architecture](docs/ARCHITECTURE.md)** ·
**[Performance program](docs/PERFORMANCE.md)** · **[Security](docs/SECURITY.md)** ·
**[Roadmap](ROADMAP.md)** · **[Changelog](CHANGELOG.md)**
```

followed by the badge row and the private-by-design subline as currently set in `README.md`.

Badges are shields.io flat style only, `labelColor 0B0E11`, values in Local violet `#8E7BE8` or
surface `#1C232B` — never green/red status colors, never more than one row. Sanctioned badges:
CI, release, measured decode, measured context, license. A measured-value badge must match the
qualified numbers in `docs/BENCHMARKS.md` and changes only with a new qualification receipt.

Place `![OMP NInfer architecture](assets/architecture.png)` under `## How it works` and the scoped
released-evidence strip at `assets/benchmarks.png` under `## Measured, not estimated`;
neither is part of the header.

The update-banner-free social GIF sits inside the header block directly under the private-by-design
subline, at width 900 with a full alt description; link the social MP4 and provenance beside it.

Then upload `assets/og.png` at GitHub → Settings → Social preview.
