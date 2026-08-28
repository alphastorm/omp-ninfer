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
- v0.1 tagline: **Private Qwen coding appliance for RTX 5090**
- Reserved post-qualification tagline: **Private Qwen coding appliance for RTX 4090/5090**
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

Voice: the gateway's sober register, operator-flavored. Sentence case, no
emoji, no exclamation marks. Claims stated as invariants:

- "Your model prompt stays on hardware you own."
- "One supported target, qualified: an RTX 5090 on Linux/WSL2."
- "The tunnel is authenticated and fail-closed; identity is visible."
- "Stateful local coding through OpenAI Responses."

Hard constraints — never write:

- anything implying general availability (v0.1.0-beta.1 is invited)
- RTX 4090 as supported in v0.1; the dual-GPU tagline remains reserved until an RTX 4090 release is
  qualified and shipped
- cloud hosting, automatic appliance installation, or universal RTX support
- "first stateful Responses", automatic restart, or universal performance
- `omp appliance ...` as available now (managed lifecycle comes later;
  v0.1 tunnel is manual)

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
| `assets/banner.html` | README banner source (1280×320) |
| `assets/banner.png` | rendered banner @2x (2560×640) |
| `assets/og.html` | GitHub social preview source (1280×640) |
| `assets/og.png` | GitHub social preview (1280×640) |
| `assets/architecture.html` | architecture illustration source (1240×380) |
| `assets/architecture.png` | rendered architecture @2x — for the README |
| `assets/benchmarks.html` | qualified-results stat strip source (1240×300) |
| `assets/benchmarks.png` | rendered stat strip @2x — for the README and benchmarks page |
| `assets/favicon.svg` | favicon (96, rx22 tile) |
| `assets/icon.svg` | icon source (512, rx116 tile) |
| `assets/icon-512.png` | rendered icon — repo/org avatar |
| `assets/favicon-32.png` / `favicon-16.png` | PNG favicon fallbacks |

Regeneration: screenshot `.banner` at 2× for `banner.png`, `.arch` at 2×
for `architecture.png`, `.stats` at 2× for `benchmarks.png`,
`#lk-dark`/`#lk-light`/`#lkx-dark`/`#lkx-light`
at 2× for the lockup PNGs (transparent); render `icon.svg` at 512 and
`favicon.svg` at 32/16; screenshot `.og` at 1× for `og.png`. Expected raster dimensions are
2560×640 for the banner, 2480×760 for architecture, 2480×600 for the stat strip, 1720×360 for
each lockup, and 1280×640 for the social preview.

## README header (drop-in)

```md
![OMP NInfer](assets/banner.png)

<div align="center">

# OMP NInfer

**Private Qwen coding appliance for RTX 5090**

Run a stateful Qwen3.8 coding model on your own NVIDIA GPU and use it from
[Oh My Pi](https://github.com/can1357/oh-my-pi) on native Windows, Linux, or a Mac.

**[Quickstart](docs/QUICKSTART.md)** · **[Benchmarks](docs/BENCHMARKS.md)** ·
**[Architecture](docs/ARCHITECTURE.md)** · **[Performance program](docs/PERFORMANCE.md)** ·
**[Security](docs/SECURITY.md)** · **[Roadmap](ROADMAP.md)** · **[Changelog](CHANGELOG.md)**
```

followed by the badge row and the private-by-design subline as currently set in `README.md`.

Badges are shields.io flat style only, `labelColor 0B0E11`, values in Local violet `#8E7BE8` or
surface `#1C232B` — never green/red status colors, never more than one row. Sanctioned badges:
CI, release, measured decode, measured context, license. A measured-value badge must match the
qualified numbers in `docs/BENCHMARKS.md` and changes only with a new qualification receipt.

Place `![OMP NInfer architecture](assets/architecture.png)` under `## How it works` and
`![Qualified v0.1.0-beta.1 results](assets/benchmarks.png)` under `## Measured, not estimated`;
neither is part of the header.

Then upload `assets/og.png` at GitHub → Settings → Social preview.
