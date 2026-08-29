# Launch copy — DRAFT, not published

> **Status: draft only. Nothing in this file has been posted, submitted, or scheduled anywhere.**
> It is prepared for the `v0.2.0-beta.1` post-release announcement window. Immediately before any
> use, reverify every claim against [`docs/BENCHMARKS.md`](../BENCHMARKS.md),
> [`docs/COMPATIBILITY.md`](../COMPATIBILITY.md), and the
> [release status](../RELEASES.md), and replace every `[release link]` placeholder with the real
> tag URL.

All copy below describes an **invited-tester beta**. Do not edit it toward stable or
general-availability readiness, broader GPU support, or upstream affiliation: this is a community
project, not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA. Attached media are real
recorded sessions against the exact released runtime with synthetic task content — verify no
hostname, username, key, private path, or personal data appears in anything attached to a post
(provenance: [`docs/media/README.md`](README.md)).

## Pre-publish checklist

- [ ] `v0.2.0-beta.1` is the published prerelease and the README/quickstart reference it.
- [ ] Advertised lane status still matches `docs/COMPATIBILITY.md`: 5090 + 4090 qualified,
      3090 preview (non-installable).
- [ ] Attached media are the canonical files from this directory, unmodified.
- [ ] Every `[release link]` placeholder replaced; links resolve.
- [ ] Numbers quoted below still match `docs/BENCHMARKS.md` exactly.

## GitHub repository description

**Private, stateful Qwen3.8 coding appliance for OMP — qualified RTX 5090 and RTX 4090 lanes,
RTX 3090 preview. Measured, hash-pinned, fail-closed.**

## README one-liner

**Private Qwen coding appliance for RTX 5090, RTX 4090, and RTX 3090.**

## Discord `#showcase` post

**OMP NInfer v0.2 — OMP on your own RTX card, with a Qwen that remembers the session**

I got tired of choosing between metered cloud tokens and stateless local servers that re-prefill a
100K-token coding session on every turn. So I built the third option as an appliance: one pinned
Qwen3.8 27B artifact + the [NInfer](https://github.com/Neroued/ninfer) engine + your own RTX card,
wired into OMP through stateful OpenAI Responses (`previous_response_id`).

What that buys you in practice:

- **Warm turns skip the re-read.** Follow-ups append to GPU-resident session state instead of
  re-prefilling the transcript. Measured post-release on the released runtime: an 89,216-token
  session's follow-up started streaming in **0.375 s** vs **36.7 s** for an equivalent cold
  prefill — roughly 98× faster to first token, receipt committed in the repo. OMP commits its
  transcript first, so losing the cache degrades to a replay, never a broken session.
- **Measured, not estimated.** The shipped RTX 5090 profile measured 235.02 tok/s decode (MTP3
  speculative, 99.87% acceptance on that workload) and exact retrieval at a 130,048-token prompt
  with a 131,072 ceiling. Receipts are committed in the repo.
- **Private and fail-closed.** Loopback-only, bearer-authenticated, cloud fallback disabled: if
  your GPU is unreachable, the turn errors — it is never silently answered by a cloud model. That
  behavior is part of the acceptance suite.
- **Verifiable to the byte.** Model SHA-256, image OCI digest + SBOM, client checksums, one release
  manifest; `python3 scripts/verify_release.py --require-ready` proves your clone is the qualified
  release.

Status: invited-tester beta. RTX 5090 (primary container) and native Windows RTX 4090 are
qualified; RTX 3090 is a built-and-reviewed preview whose remaining gates just need validation
hardware — if you own a 3090, your acceptance run and hardware report are literally what closes
them.

Repo: [release link] — quickstart, benchmarks, architecture, and the performance program are all
linked from the README. The demo GIF is a real recorded session against the exact released
runtime. Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.

*Attach `omp-ninfer-demo.mp4` (preferred) or `omp-ninfer-demo.gif`.*

## X post — product-first

Serious OMP coding sessions run past 100K tokens. A cloud meters every one of them; a stateless
local server re-prefills the whole transcript every turn.

So my GPU holds the session now: OMP + Qwen3.8 27B + NInfer on an RTX 5090 — a follow-up on an
89K-token session starts streaming in 0.375 s (vs 36.7 s cold), 235.02 tok/s measured decode,
fail-closed instead of cloud fallback, every byte hash-pinned.

v0.2.0-beta.1: [release link]

*Attach `omp-ninfer-demo.mp4` (preferred) or `omp-ninfer-demo-poster.png`.*

## X post — tighter

My coding agent's session state lives on my own GPU now.

OMP + Qwen3.8 27B on an RTX 5090: warm follow-ups in 0.375 s at 89K tokens instead of a 36.7 s
re-prefill, 235.02 tok/s measured decode, 130K exact context, loopback-only and fail-closed.

v0.2.0-beta.1: [release link]

*Attach `omp-ninfer-demo.mp4` (preferred) or `omp-ninfer-demo-poster.png`.*

## Show HN title

**Show HN: OMP NInfer – a stateful, fail-closed local Qwen appliance for the OMP coding agent**

## Show HN body

I run long OMP coding sessions — 100K-token transcripts with tools, thinking, and images. Routed
to a cloud provider, every token is metered and every file leaves the machine. Routed to a typical
local OpenAI-compatible server, the API is stateless: each turn re-sends and re-prefills the whole
transcript.

OMP NInfer ships the third option as a small set of qualified combinations: OMP, the NInfer
engine, and one pinned Qwen3.8 27B artifact on an RTX 5090 or RTX 4090 (plus a reviewed RTX 3090
preview). OMP drives NInfer through stateful OpenAI Responses, so a follow-up turn continues from
retained GPU state; OMP commits its transcript before advancing provider state, so the cache is an
acceleration, never the source of truth. The shipped 5090 profile measured 235.02 tok/s decode and
exact retrieval across a 130,048-token prompt; receipts are committed in the repo, and the README
demo is a real recorded session against the exact released runtime.

The part I care most about: the route is loopback-only, bearer-authenticated, and fail-closed —
when the GPU is unreachable the turn fails instead of silently falling back to a cloud model, and
that behavior is acceptance-tested. Everything is pinned: model SHA-256, image OCI digest with an
SPDX SBOM, client checksums, one release manifest.

This is an invited-tester beta, not GA, and a community project not affiliated with the Oh My Pi
maintainers. I would especially value 3090/4090 hardware reports (they close real qualification
gates), setup-friction feedback, and kernel people looking at the public performance program.

## Phrases to avoid

- "Works on any RTX card." Support is three exact lanes with receipts; the 3090 is preview-only.
- "Never re-prefills." Retained-state follow-ups skip re-prefill; cache loss degrades to replay.
- "Fastest local inference." The numbers are one profile on one machine, not a leaderboard claim.
- "First stateful Responses" / "first persistent KV cache." Prior art is documented in
  [`RELATED_WORK.md`](../RELATED_WORK.md).
- "Production-ready" / "GA" / "stable." The release classification is invited-tester beta.
- Anything implying Oh My Pi, Qwen, or NVIDIA affiliation or endorsement.
