## Final Prompt
<taskname="Post-release launch pass"/>

<task>
Produce the requested planning deliverable only (do not implement): an ordered, per-file v0.2 post-release documentation and launch-assets edit plan for OMP NInfer, plus a deterministic demo-media production plan and a launch-copy outline. The repository is already released at `v0.2.0-beta.1`, clean at merge commit `273a89f49a6fd112c084c2c6fdc70d27a78c58d7`. Plan changes that sharpen the README hero for OMP + local Qwen users on RTX 5090/4090/3090, accurately reframe the 3090 preview, repair v0.1-era text, add `docs/media/` GIF/MP4/poster/provenance assets and `docs/media/LAUNCH_COPY.md`, and update competitive framing if justified. Do not propose release-manifest, receipt, or generated `docs/COMPATIBILITY.md` hand-edits. State validation commands and a sensible Conventional Commit sequence.

The hero must communicate within 20–30 seconds: stateful GPU-resident sessions with no per-turn re-prefill; 235.02 tok/s measured decode on the exact 27B profile; 130K exact context; fail-closed privacy; hash-pinned releases. The 3090 truth is: component built and reviewed, local validation rig offline / hardware unavailable, current live-model and fresh Windows package gates remain `not_run`; tester hardware reports can close remaining gates; manifest remains `preview`, `installable: false`, and installers must refuse it. Avoid implying the failed unattended evidence-role corpus is the only blocker.

Preserve pinned public-number strings and provenance language required by tests: `235.02 tok/s`, badge substring `decode-235%20tok`, `99.87%`, `130,048`, `131,072`, benchmark-only `2,180.87 tok/s`, `predecessor v0.1 campaign`, and `not rebind that numeric result`. No receipt or manifest changes. `scripts/verify_release.py` and `python3 -m unittest discover -s tests -v` must remain passing.
</task>

<architecture>
- `README.md` is the public front door: hero, invited-tester disclaimer, value proposition, measured results, comparison table, family framing, roadmap summary, integrity, disclaimer.
- `BRAND.md` is the naming/voice/visual authority. It contains hard non-claims, community-project disclaimer, asset conventions, and stale tagline/header canon that must be brought into alignment.
- `compatibility.json` is the live machine-readable authority. `docs/COMPATIBILITY.md` is generated from it by `scripts/render_compatibility.py`; consult but do not hand-edit.
- `releases/v0.2.0-beta.1/*` is immutable evidence. Because the workspace file index lagged newly added files, their complete current contents are selected as add-file patches from HEAD~1..HEAD; treat patch `+` lines as the actual released artifacts, not proposed changes.
- `docs/BENCHMARKS.md` and `docs/PERFORMANCE.md` explain measured numbers and the important v0.1/v0.2 provenance boundary. `tests/test_public_numbers.py` encodes exact string contracts.
- `docs/QUICKSTART.md`, `ROADMAP.md`, `CONTRIBUTING.md`, and `docs/RELATED_WORK.md` contain the stale or weak 3090/4090/product-wedge language named in the request.
- `docs/RELEASES.md`, `docs/SECURITY.md`, `docs/ARCHITECTURE.md`, issue forms, and profiles supply release, privacy, reporting, and topology boundaries.
- Existing `assets/*.html` sources and `BRAND.md` describe the visual system. New demo deliverables belong under a new `docs/media/` subtree and should not mutate immutable release evidence.
</architecture>

<selected_context>
- `README.md`: full current v0.2 front page. Hero presently leads with “Private Qwen coding appliance…” and defers the strongest session/performance/context claims below the fold; 3090 is called a “non-installable public preview”; comparison currently covers OMP NInfer, Ollama, llama.cpp server, and vLLM.
- `BRAND.md`: complete brand spec. Stale naming canon still lists v0.1 and “reserved post-qualification” taglines; voice invariant still says one qualified 5090 target; README drop-in header is stale. Hard constraints prohibit GA implication, universal GPU/performance claims, unsupported activation, “first stateful Responses,” and official-affiliation implication.
- `CONTRIBUTING.md`: stale ownership row points RTX 4090 at `alphastorm/ninfer-4090` and says it is outside the first release, while v0.2 consolidates public 5090/4090/3090 component source at `alphastorm/ninfer`.
- `ROADMAP.md`: opening wedge is still 5090-only; historical v0.1 non-claims are intentionally historical, while current v0.2 section already records qualified 4090 and review-closed/non-installable 3090 preview. Its help section is the natural tester call-to-action.
- `docs/RELATED_WORK.md`: stale NInfer-family prose calls the 4090 lane deferred and 3090 lane planned; comparison discussion covers vLLM Agentic API, Ollama, LocalAI, vLLM APC, LMCache, SGLang, and llama.cpp, but not LM Studio.
- `docs/BENCHMARKS.md`: authoritative published measurement wording, 3090 `not_run` row, current and predecessor campaigns, community result rules.
- `docs/PERFORMANCE.md`: exact v0.2 baseline and explicit statement that predecessor prefix-hit evidence is not rebound.
- `docs/QUICKSTART.md`: installer refusal contract for 3090 and separately qualified 4090 path; current line says 3090 remains non-installable until later receipt closes deferred gates.
- `compatibility.json`: current authority: `rtx3090-windows-native` has `status: preview`, `installable: false`; `rtx4090-windows-native` is qualified/installable. Do not alter for this docs pass.
- `docs/COMPATIBILITY.md`: generated rendering, selected for reference only.
- `scripts/render_compatibility.py`: generator and schema expectations for compatibility docs.
- `scripts/verify_release.py`: extensive immutable release graph/hash validation; useful for defining no-touch boundaries and validation commands.
- `tests/test_public_numbers.py`: exact public strings and receipt-derived numeric checks. README badge must contain `decode-235%20tok`; README and benchmarks must contain receipt-derived strings; `2,180.87 tok/s` is asserted in benchmarks, not README.
- `tests/test_compatibility.py`, `tests/test_verify_release.py`, `tests/test_manual_tunnel_scripts.py`: broader generated-doc, release-integrity, and shell-contract constraints.
- `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/RELEASES.md`, `docs/TROUBLESHOOTING.md`: state ownership, fail-closed/privacy, prerelease/non-claim, release lifecycle, and content-safe reporting language.
- `.github/ISSUE_TEMPLATE/hardware-report.yml`, `.github/ISSUE_TEMPLATE/benchmark-report.yml`: content-safe tester intake and hardware/measurement fields; useful when specifying the 3090 CTA.
- `assets/banner.html`, `assets/benchmarks.html`, `assets/architecture.html`, `assets/og.html`: visual tokens and existing launch image source conventions.
- `CHANGELOG.md`: `[Unreleased]` destination for user-visible documentation/launch-asset changes.
- `profiles/qwen38-rtx5090-*.json`: exact 131,072 context and provider/failover profile details.
- `_git_data/.../MAP.txt`: map of v0.2 release commit changes and exact paths.
- `_git_data/.../releases__v0.2.0-beta.1__*.patch`: full contents of immutable v0.2 manifest, compatibility snapshot, composed qualification, GPU receipts, platform acceptances, generated compatibility snapshot, and release notes. Use these to ground claims; do not plan edits to them.
</selected_context>

<relationships>
- README headline claims → `docs/BENCHMARKS.md` / v0.2 RTX 5090 receipt → `tests/test_public_numbers.py` exact-string checks.
- README release/support wording → root `compatibility.json` → generated `docs/COMPATIBILITY.md`; immutable release snapshot and manifest bind the released status.
- 3090 messaging → `qualification/rtx3090.json` (`not_run` gates, reviewed/build evidence) + root compatibility (`preview`, non-installable) + quickstart refusal logic + hardware-report CTA.
- README hero/launch copy/media chrome → `BRAND.md` naming, voice, visual tokens, non-claims, and standing community-project disclaimer.
- README competitive table ↔ `docs/RELATED_WORK.md`; any LM Studio addition or Ollama/llama.cpp/vLLM correction should be based on current first-party docs and dated sourcing, not assumption.
- User-visible docs/media additions → `CHANGELOG.md [Unreleased]`; implementation work should be split into Conventional Commits by coherent docs/assets scope.
- New demo source/provenance → deterministic render outputs (`.gif`, `.mp4`, poster) → README embedding/linking, with receipt-sourced fixed numbers and clearly labeled capture-only chrome.
</relationships>

<ambiguities>
- The requested sibling `omp-session-gateway` demo-media conventions are not present in this single-root workspace. The plan should explicitly call for inspecting/copying that sibling’s exact filenames, dimensions, frame timing, encoder commands, README schema, and chrome labels before production; do not invent claims that its conventions were verified here.
- Competitive products change quickly. Current repo prose says sources were reviewed 2026-08-26/28. Verifying Ollama, llama.cpp, vLLM, and LM Studio requires fresh primary-source research at implementation time; distinguish verified facts from proposed comparison categories.
- User asks for a plan, demo-media production plan, and launch-copy outline—not the actual rewritten docs/copy or rendered binaries. Keep deliverable ordered and concrete per file, with dependencies, acceptance checks, and no implementation.
</ambiguities>

## Selection
- Files: 44 total (44 full)
- Total tokens: 92741 (Auto view)
- Token breakdown: full 92741
- Token accounting: fresh from active_tab_published

### Files
### Selected Files
├── .github/
│   └── ISSUE_TEMPLATE/
│       ├── benchmark-report.yml — 888 tokens (full)
│       └── hardware-report.yml — 718 tokens (full)
├── _git_data/
│   └── repos/
│       └── omp-ninfer-6980ca66/
│           └── 2026-08-29/
│               └── 0839/
│                   ├── diff/
│                   │   └── per-file/
│                   │       ├── releases__v0.2.0-beta.1__COMPATIBILITY.md.patch — 1,113 tokens (full)
│                   │       ├── releases__v0.2.0-beta.1__NINFER_RELEASE_NOTES.md.patch — 797 tokens (full)
│                   │       ├── releases__v0.2.0-beta.1__acceptance__composed-external-installation.json.patch — 715 tokens (full)
│                   │       ├── releases__v0.2.0-beta.1__acceptance__linux-x64-18.0.9-beta2.json.patch — 815 tokens (full)
│                   │       ├── releases__v0.2.0-beta.1__acceptance__macos-arm64-18.0.9-beta2.json.patch — 832 tokens (full)
│                   │       ├── releases__v0.2.0-beta.1__acceptance__windows-x64-18.0.9-beta2.json.patch — 890 tokens (full)
│                   │       ├── releases__v0.2.0-beta.1__compatibility.json.patch — 4,165 tokens (full)
│                   │       ├── releases__v0.2.0-beta.1__manifest.json.patch — 3,133 tokens (full)
│                   │       ├── releases__v0.2.0-beta.1__qualification.json.patch — 1,923 tokens (full)
│                   │       ├── releases__v0.2.0-beta.1__qualification__rtx3090.json.patch — 1,101 tokens (full)
│                   │       ├── releases__v0.2.0-beta.1__qualification__rtx4090.json.patch — 1,076 tokens (full)
│                   │       └── releases__v0.2.0-beta.1__qualification__rtx5090.json.patch — 1,121 tokens (full)
│                   └── MAP.txt — 4,464 tokens (full)
├── assets/
│   ├── architecture.html — 1,029 tokens (full)
│   ├── banner.html — 848 tokens (full)
│   ├── benchmarks.html — 831 tokens (full)
│   └── og.html — 858 tokens (full)
├── docs/
│   ├── ARCHITECTURE.md — 1,471 tokens (full)
│   ├── BENCHMARKS.md — 2,368 tokens (full)
│   ├── COMPATIBILITY.md — 1,041 tokens (full)
│   ├── PERFORMANCE.md — 2,312 tokens (full)
│   ├── QUICKSTART.md — 4,550 tokens (full)
│   ├── RELATED_WORK.md — 1,584 tokens (full)
│   ├── RELEASES.md — 1,921 tokens (full)
│   ├── SECURITY.md — 1,345 tokens (full)
│   └── TROUBLESHOOTING.md — 1,641 tokens (full)
├── profiles/
│   ├── qwen38-rtx5090-manual-tunnel.json — 760 tokens (full)
│   └── qwen38-rtx5090-windows-docker-local.json — 870 tokens (full)
├── scripts/
│   ├── render_compatibility.py — 3,436 tokens (full)
│   └── verify_release.py — 13,087 tokens (full)
├── tests/
│   ├── test_compatibility.py — 2,605 tokens (full)
│   ├── test_manual_tunnel_scripts.py — 2,760 tokens (full)
│   ├── test_public_numbers.py — 935 tokens (full)
│   └── test_verify_release.py — 6,852 tokens (full)
├── BRAND.md — 1,844 tokens (full)
├── CHANGELOG.md — 1,841 tokens (full)
├── CONTRIBUTING.md — 897 tokens (full)
├── LICENSE — 283 tokens (full)
├── README.md — 4,599 tokens (full)
├── ROADMAP.md — 1,966 tokens (full)
├── SECURITY.md — 435 tokens (full)
└── compatibility.json — 4,021 tokens (full)


---

## Generated Plan

## Chat Send ✅
- **Chat**: `post-release-launch-pass-486A1E` | **Mode**: plan

### Response


# 1. Summary

This is a targeted post-release documentation and launch-assets pass, not a release-contract refactor. Reorganize `README.md` so a local-Qwen/OMP user sees the stateful-session, measured RTX 5090 performance, exact-context, fail-closed, and hash-pinning value proposition within 20–30 seconds; correct stale v0.1 and pre-v0.2 language across brand, roadmap, contribution, security, quickstart, benchmark, and related-work pages; and add reproducible launch media plus channel-specific copy under `docs/media/`. Preserve the released evidence graph unchanged: do not edit `compatibility.json`, generated `docs/COMPATIBILITY.md`, or anything under `releases/v0.2.0-beta.1/`.

# 2. Current-state analysis

## Authority and publication flow

The repository has three distinct layers:

1. **Immutable release evidence**
   - `releases/v0.2.0-beta.1/manifest.json`, qualification receipts, acceptance receipts, release compatibility snapshot, and release notes bind the released artifacts and claims.
   - These files must remain byte-identical to merge commit `273a89f49a6fd112c084c2c6fdc70d27a78c58d7`.

2. **Live compatibility authority**
   - Root `compatibility.json` declares the supported client profiles and native runtime variants.
   - `scripts/render_compatibility.py` validates its closed profile/variant sets and generates `docs/COMPATIBILITY.md`.
   - `scripts/verify_release.py` requires the root and release compatibility copies, and their generated Markdown matrices, to be byte-identical. Neither authority nor generated matrix belongs in this documentation pass.

3. **Editable public presentation**
   - `README.md`, `BRAND.md`, mutable docs, issue forms, and `assets/*.html` explain the already-released contract.
   - New launch media can be added under `docs/media/` without becoming part of the v0.2 manifest.

## Public-number data flow

The v0.2 RTX 5090 qualification receipt is the numerical authority:

`releases/v0.2.0-beta.1/qualification/rtx5090.json`
→ `docs/BENCHMARKS.md` / `README.md`
→ `tests/test_public_numbers.py`

The protected strings are:

- `235.02 tok/s`
- README badge substring `decode-235%20tok`
- `99.87%`
- `130,048`
- `131,072`
- `2,180.87 tok/s`, retained as benchmark-specific detail rather than launch/hero copy
- `predecessor v0.1 campaign`
- `not rebind that numeric result`

The v0.1 prefix-hit evidence remains historical. The README may explain the mechanism and retain those exact provenance phrases, but must not present the 37,591-token observation as a v0.2 measurement.

## Stateful request path

The relevant runtime flow is already documented and must not be redesigned:

User turn → OMP transcript/session → bearer-authenticated loopback route → NInfer Responses state → Qwen GPU execution → complete stream → durable OMP transcript publication → provider snapshot commit.

OMP owns durable truth; retained NInfer state is an acceleration. Hero copy should therefore say that retained follow-ups avoid full transcript re-prefill while state remains valid, followed by the replay recovery qualification. It must not imply that GPU cache is durable on every profile or that replay is impossible.

## 3090 status flow

The 3090 status derives from:

- `compatibility.json`: `status: preview`, `installable: false`
- v0.2 manifest: same status plus the native package identity
- `qualification/rtx3090.json`: component built/reviewed, current live-model and fresh Windows package gates `not_run`
- `docs/QUICKSTART.md`: installer selection accepts only uniquely qualified variants and must refuse 3090
- hardware-report issue form: content-safe path for tester evidence

Current prose is mostly accurate but scattered. Some passages emphasize the failed unattended evidence-role corpus without making clear that it is separate from—and not the only reason for—the remaining `not_run` gates. The post-release wording must consistently state:

- the component exists and was reviewed;
- the local validation rig is offline / suitable hardware is unavailable;
- live-model and fresh Windows package gates remain `not_run`;
- tester reports can help close those gates;
- the authority remains preview/non-installable;
- installers continue to refuse it.

## Stale or weak presentation

- `README.md` defers the strongest value proposition below the fold and its headline groups all three GPUs too loosely.
- `BRAND.md` still contains v0.1 and “reserved post-qualification” tagline rules, a 5090-only invariant, and a stale drop-in header.
- `ROADMAP.md` opens with a 5090-only product wedge despite the released multi-lane v0.2 boundary.
- `CONTRIBUTING.md` routes 4090 work to the old separate repository and says it is outside the first release.
- `docs/RELATED_WORK.md` calls the 4090 lane deferred and the 3090 lane planned.
- Root `SECURITY.md` lists the latest `0.1.0-beta.x` as supported.
- The benchmark issue form still refers to v0.1 having no product benchmark and uses v0.1 example numbers.
- Existing banner, architecture, benchmark, and social-preview sources use compressed lane wording that can be read as 3090 support.

## Reuse and scope decision

Reuse:

- Existing brand tokens and Socket mark from `BRAND.md`.
- Existing `assets/*.html` source-first raster workflow.
- Receipt-derived claims already established in `docs/BENCHMARKS.md`.
- Existing release verifier, compatibility renderer, and standard-library unit-test patterns.
- Sibling `omp-session-gateway` media conventions after inspecting its exact committed implementation.

A broader documentation schema or release-authority refactor is unnecessary and risky. The only new tooling should be a small deterministic media renderer/checker because reproducible binary assets otherwise cannot be audited.

# 3. Design

## 3.1 Canonical claim hierarchy

Use this order in the README hero, launch animation, poster, and launch-copy outline:

1. **Task and audience**
   - OMP running Qwen3.8 27B on user-owned GPU hardware.
2. **Stateful advantage**
   - Retained follow-ups append to GPU-resident Responses state rather than fully re-prefilling the transcript each turn.
   - If retained state is unavailable, OMP replays its authoritative transcript.
3. **Measured proof**
   - `235.02 tok/s` measured decode on the exact RTX 5090 BF16-KV/MTP3 profile.
   - Exact retrieval at `130,048` prompt tokens.
   - `131,072` context ceiling.
   - `99.87%` remains identified as workload-specific MTP3 acceptance.
4. **Privacy**
   - Loopback-only, bearer-authenticated, explicitly fail-closed; no silent cloud answer.
5. **Integrity**
   - Client, runtime, model, configuration, SBOM, and qualification identities are hash- or digest-pinned.
6. **Hardware lanes**
   - RTX 5090 primary qualified container.
   - RTX 4090 separately beta-qualified native Windows package.
   - RTX 3090 built/reviewed preview, non-installable, current gates `not_run`, hardware reports requested.

Do not put `2,180.87 tok/s` in the README hero, general launch copy, or overview animation. Retain it in `docs/BENCHMARKS.md` and the benchmark-specific visual, where its prompt shape and exact-retrieval context are adjacent.

## 3.2 README information architecture

Restructure the top of `README.md` in this order:

1. Existing banner.
2. Product title.
3. New canonical tagline that distinguishes support status, for example conceptually:
   - stateful local Qwen for OMP;
   - 5090 and 4090 qualified;
   - 3090 preview.
4. One two-line value statement naming Qwen3.8 27B, user-owned hardware, and retained follow-up state.
5. Existing navigation and badge row, retaining `decode-235%20tok`.
6. A compact four-part proof strip:
   - stateful continuation/no full warm-turn re-prefill;
   - `235.02 tok/s` exact-profile measurement;
   - `130,048` exact retrieval / `131,072` ceiling;
   - loopback, fail-closed, hash-pinned identity.
7. Explicit invited-tester and lane-status note.
8. New overview GIF with adjacent MP4, poster, and provenance links.
9. Existing longer-form sections, deduplicated so the hero does not repeat entire paragraphs.

The current “Why this exists” state-ownership explanation remains the long-form authority. Preserve the exact sentences containing `predecessor v0.1 campaign` and `not rebind that numeric result`, even if the surrounding paragraph is tightened.

In “Measured, not estimated,” keep the benchmark image and concise results, but remove the `2,180.87 tok/s` value from the README table. Refer readers to `docs/BENCHMARKS.md` for the full prefill curve instead. Keep `130,048`, `131,072`, `235.02 tok/s`, and `99.87%` visible.

Create a dedicated, visually scannable 3090 callout near the hardware-lane summary rather than distributing the full explanation across unrelated sections. It must state preview/non-installable status before the request for reports.

## 3.3 Brand and static launch visuals

Update `BRAND.md` to define one current v0.2 tagline rather than retaining v0.1 plus “reserved” alternatives. The canonical brand wording must not say “for RTX 3090” without immediately labeling it preview.

The four existing launch-visual sources should use the same lane grammar:

- **Qualified:** RTX 5090, RTX 4090 beta
- **Preview/non-installable:** RTX 3090
- Never use shorthand such as “5090 / 4090 / 3090” without status.

Specific visual changes:

- `banner.html`: lead with stateful local Qwen rather than an undifferentiated GPU list; keep the status line explicit.
- `og.html`: include the stateful/fail-closed value proposition and qualified-versus-preview status.
- `architecture.html`: label the primary container and native variants separately; do not imply native restart on the 5090 lane.
- `benchmarks.html`: use “2 qualified / 1 preview” rather than “2 + 1 qualified + preview lanes”; identify `131,072` as the 5090 ceiling and native restart as 4090-specific.

Regenerate the matching PNGs from their HTML sources using the existing dimensions in `BRAND.md`. HTML source and raster output must land atomically.

## 3.4 Deterministic overview media

### Required discovery

Before authoring the media source, inspect the sibling `omp-session-gateway` repository at a fixed commit and record:

- exact file naming and directory structure;
- viewport and output dimensions;
- master and GIF frame rates;
- frame timing mechanism;
- browser and encoder invocation;
- codec/pixel-format/metadata flags;
- README/provenance schema;
- chrome labels and “illustrative” disclosure;
- asset-size limits.

Copy those conventions exactly where they apply. Do not write that sibling conventions were followed until its repository, commit, and inspected paths are recorded in the new provenance file.

If the sibling cannot be accessed, use the fallback names and specifications below and record the inability and deviations rather than implying equivalence.

### Fallback file set

- `docs/media/omp-ninfer-v0.2-overview.html`
- `docs/media/omp-ninfer-v0.2-overview.mp4`
- `docs/media/omp-ninfer-v0.2-overview.gif`
- `docs/media/omp-ninfer-v0.2-overview-poster.png`
- `docs/media/omp-ninfer-v0.2-overview.provenance.json`
- `docs/media/README.md`
- `docs/media/LAUNCH_COPY.md`
- `scripts/render_launch_media.py`
- `tests/test_launch_media.py`

If the sibling uses different standard names, adopt its exact names consistently in the renderer, provenance, README links, and tests.

### Media type and storyboard

Produce a scripted, silent product-tour animation, not a purported live benchmark recording. Label it as illustrative UI with receipt-derived measurements. Use synthetic session text only; do not capture a private prompt, model output, host path, key, hostname, or raw log.

Fallback master specification:

- 27.0 seconds
- 1280×720
- 30 fps MP4 master, H.264, `yuv420p`, metadata stripped, web-fast-start
- 15 fps optimized GIF derived from the same source frames
- poster taken from the canonical proof-summary frame
- no audio
- no flashing or rapid transitions

Storyboard:

| Time | Content |
| --- | --- |
| 0–3 s | OMP NInfer title, local Qwen3.8 27B purpose, explicit 5090/4090 qualified and 3090 preview line |
| 3–9 s | OMP transcript → authenticated loopback → GPU state; follow-up appends to retained state without full transcript re-prefill; small replay-recovery note |
| 9–14 s | Receipt-bound proof: `235.02 tok/s`, `99.87%`, `130,048` exact retrieval, `131,072` ceiling; mark performance as exact RTX 5090 profile only |
| 14–19 s | Loopback-only, bearer-authenticated, fail-closed route; runtime/model/client hashes and OCI digest |
| 19–23 s | Separate RTX 5090 primary and RTX 4090 native-beta cards, including restart qualification only on 4090 |
| 23–27 s | RTX 3090 preview card: built/reviewed, hardware unavailable, live-model and fresh Windows package gates `not_run`, installer refuses it, hardware reports wanted |

The final frame should work as the poster and contain the product title, three headline proofs, explicit lane status, and invited-tester label.

### Renderer interface and execution

Add a synchronous standard-library orchestrator in `scripts/render_launch_media.py` with two modes:

- `render`: stage frames and outputs in a temporary directory using the pinned sibling/fallback browser and ffmpeg toolchain.
- `check`: perform no rendering; validate checked-in files, provenance hashes, dimensions, duration metadata, source hash, and claim fields.

Conceptual interface:

```text
render_assets(source, output_dir, toolchain_digest, source_date_epoch) -> provenance
check_assets(provenance_path) -> list[validation_error]
```

Rendering rules:

1. Use a digest-pinned container/toolchain or exact locally hashed browser, ffmpeg, and fonts.
2. Disable network access during frame capture.
3. Drive the HTML by explicit integer frame index rather than wall-clock animation.
4. Require every expected frame exactly once and in ascending order.
5. Encode MP4, GIF, and poster from the same canonical frame set.
6. Strip creation timestamps and other nondeterministic metadata; use fixed `SOURCE_DATE_EPOCH`.
7. Compute output hashes only after all validations pass.
8. Move completed outputs into place atomically. Cancellation or an encoder failure leaves the previously committed files unchanged and removes the temporary frame directory.
9. Reject parallel renderers targeting the same output directory rather than racing.

### Provenance schema

Use schema version 1 with these logical fields:

- asset-set ID and product release;
- source file and SHA-256;
- sibling repository, exact commit, inspected paths, and recorded deviations;
- fixed duration, dimensions, frame rates, poster frame index, and source epoch;
- toolchain image digest or executable/font hashes;
- normalized render and encoder arguments;
- input asset hashes;
- output filename, bytes, SHA-256, dimensions, codec, pixel format, and frame count;
- capture disclosure;
- claim ledger mapping each displayed fact to an immutable receipt path and JSON field;
- confirmation that no live prompt, model output, secret, or private identifier is included.

Do not include absolute workstation paths or current-time generation timestamps.

### Media validation behavior

`tests/test_launch_media.py` should use only the Python standard library and verify:

- every provenance-referenced repository file exists;
- output and source hashes match;
- PNG and GIF headers report expected dimensions;
- MP4 has the expected container signature and recorded bytes/hash;
- duration is between 20 and 30 seconds;
- provenance names `v0.2.0-beta.1`;
- the claim ledger contains the 5090 measurement and 3090 status authorities;
- the overview source and `LAUNCH_COPY.md` do not contain `2,180.87 tok/s`;
- no output is described as a live benchmark recording.

Full codec/duration inspection with `ffprobe` remains part of production validation because standard-library CI should not acquire a new multimedia dependency.

## 3.5 Launch-copy outline

`docs/media/LAUNCH_COPY.md` should be a reusable outline, not a second release note. Give every channel the same claim order and links.

### Shared preamble

- Audience: OMP users who want Qwen3.8 27B on their own RTX hardware.
- Status: already-released `v0.2.0-beta.1`, invited testers, not stable/GA.
- One-sentence differentiator: retained local Responses state avoids full warm-turn transcript re-prefill while OMP remains the durable transcript owner.

### Copy variants

1. **One-line headline**
   - Stateful local Qwen for OMP, followed by the exact qualified/preview lane status.
2. **Short social post**
   - Problem, stateful benefit, `235.02 tok/s`, `130,048` exact retrieval, fail-closed/hash-pinned proof, invited-tester link.
3. **Community/Discord post**
   - Adds the separate 5090/4090 profile boundaries and a concise 3090 status paragraph.
4. **Long-form Hacker News/Reddit/GitHub discussion outline**
   - Why stateful local inference matters.
   - OMP/NInfer ownership boundary.
   - Exact measured profile and limitations.
   - Security/release-integrity model.
   - Comparison to broad local runtimes without claiming invention or universal superiority.
   - Requested tester feedback.
5. **3090-specific follow-up**
   - Component built and reviewed.
   - Local rig offline/hardware unavailable.
   - Current live-model and fresh Windows package gates remain `not_run`.
   - Manifest remains preview and non-installable; installer refusal is intentional.
   - Content-safe hardware reports can close the remaining evidence.
   - The failed unattended role corpus is a separate stricter gate, not the sole blocker.
6. **Media caption and alt text**
   - Identify the animation as scripted.
   - Summarize stateful continuation, exact-profile results, privacy, and lane status.
7. **Link block**
   - Quickstart → benchmarks → compatibility authority/matrix → architecture/security → hardware report.
8. **Standing disclaimer**
   - Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.

Include a prohibited-claims checklist covering GA/stable support, universal RTX support or throughput, 3090 installability, process-restart continuation on the primary 5090 image, structured JSON-schema support, “first stateful Responses,” automatic restart, and cloud/production activation.

## 3.6 Competitive framing

Add LM Studio to the README comparison only after refreshing all competitive cells from current first-party documentation. It is justified because local-Qwen users commonly compare GUI/local-server options, while the current table omits that category.

At implementation time, inspect and cite dated primary sources for:

- Ollama OpenAI/Responses compatibility and cache/session behavior;
- llama.cpp server slots and cache behavior;
- vLLM core prefix caching and Agentic API state ownership;
- LM Studio local-server, OpenAI compatibility, supported request/session behavior, and model/backend variability.

Update the review date in `docs/RELATED_WORK.md` to the actual research date. Do not infer absence of a feature from missing documentation. If stateful Responses or another capability is unclear, use “not documented in the reviewed first-party source” or “varies by backend/client” rather than “unsupported.”

The README table should remain descriptive:

- what the product is;
- who owns cross-turn state;
- breadth versus exact qualification;
- profile-specific speculative decoding;
- modalities/tools variability;
- release identity;
- fail-closed ownership.

Do not add rankings or a synthetic score. Preserve the “where each shines” format, adding a neutral LM Studio sentence grounded in verified desktop/local-server positioning.

# 4. File-by-file impact

## Public front door and brand

### `README.md`

- Replace the undifferentiated three-GPU tagline with explicit 5090/4090 qualified and 3090-preview wording.
- Add the compact proof strip and overview media immediately below the header.
- Keep the badge substring `decode-235%20tok`.
- Tighten the invited-tester callout and add the canonical 3090 explanation/CTA.
- Preserve all protected number and provenance strings except move `2,180.87 tok/s` out of README prose.
- Clarify restart continuation as 4090-only.
- Add LM Studio to the comparison after the related-work source refresh.
- Link GIF, MP4, poster, provenance, and launch copy.
- Depends on the new media files and refreshed `docs/RELATED_WORK.md`.

### `BRAND.md`

- Replace stale v0.1/reserved taglines with a current v0.2 canon.
- Replace the 5090-only voice invariant with exact lane-aware wording.
- Refresh the README drop-in header.
- Add launch-media conventions: scripted disclosure, claim scoping, lane-status grammar, no live/private capture, and provenance requirements.
- Update asset inventory with the new `docs/media/` set.
- Drives all HTML source and launch-copy wording.

### `CHANGELOG.md`

- Under `[Unreleased]`, add:
  - an “Added” entry for deterministic overview media, provenance, and launch-copy outline;
  - “Changed” entries for the README hero, corrected lane/status wording, stale v0.1 cleanup, and refreshed comparison framing.
- Do not create a new release heading or date.

## Product and contributor documentation

### `ROADMAP.md`

- Change the opening product wedge from 5090-only to the released v0.2 closed lane set.
- Keep the historical v0.1 non-claims explicitly historical.
- In the v0.2/3090 discussion, enumerate current `not_run` gate categories and hardware unavailability before mentioning the separate unattended-role corpus.
- Strengthen the 3090 hardware-report CTA without implying preview activation.

### `CONTRIBUTING.md`

- Route all 5090/4090/3090 runtime work to `alphastorm/ninfer`, while retaining upstream lineage attribution.
- Remove the statement that 4090 is outside the first release and the stale `alphastorm/ninfer-4090` ownership route.
- Add a 3090 evidence lane: reports must use the exact preview package/profile, remain content-safe, and do not authorize installation or support.
- Keep engine implementation out of this product repository.

### `SECURITY.md`

- Change supported prerelease from latest `0.1.0-beta.x` to latest published `0.2.0-beta.x`, or phrase it generically as the latest published prerelease with `v0.2.0-beta.1` as the current instance.
- Preserve the no-stable-release boundary and private-reporting policy.

### `docs/QUICKSTART.md`

- Reframe the 3090 paragraph to state built/reviewed status, unavailable local hardware, and the exact remaining `not_run` categories.
- Preserve the manifest-driven unique-qualification guard and explicit installer refusal.
- Add a direct content-safe hardware-report link for 3090 owners.
- Do not add an installation workaround for preview assets.

### `docs/BENCHMARKS.md`

- Retain all current measured values, especially `2,180.87 tok/s`.
- Expand the 3090 row/note with hardware-unavailable and report-request context.
- Explicitly distinguish current package gates from historical measurements and the separate unattended-role corpus.
- Keep the community row as `not run`; do not insert hypothetical performance.
- Add a 3090-specific submission note referencing the hardware report when benchmark gates cannot yet run.

### `docs/PERFORMANCE.md`

- Keep the page’s 5090 focus and v0.1/v0.2 provenance wording unchanged.
- Update the durable-checkpoint backlog row to explain that 3090 requires current live-model and fresh-package evidence on available hardware.
- Link the hardware-report CTA rather than implying the failed role corpus is the remaining performance gate.

### `docs/RELATED_WORK.md`

- Replace deferred/planned 4090/3090 family language with the released qualified/preview status and consolidated `alphastorm/ninfer` ownership.
- Refresh the source-review date.
- Add a first-party-sourced LM Studio section.
- Recheck Ollama, llama.cpp, and vLLM claims; soften any statement not established by current source.
- Keep the direct OMP-to-NInfer ownership rationale.

## Issue intake

### `.github/ISSUE_TEMPLATE/hardware-report.yml`

- Rename the Mac-specific client field to “OMP client OS and architecture.”
- Generalize inference-host/runtime fields so native Windows variants do not require Docker-only answers.
- Make profile instructions accept either a client profile ID or native runtime variant ID.
- Add result/check options for preview evidence and expected installer refusal.
- Add a 3090 note explaining that reports provide evidence but do not change preview/installability status.
- Changing field IDs affects future issue bodies only; existing issues require no migration.

### `.github/ISSUE_TEMPLATE/benchmark-report.yml`

- Replace v0.1 example values with the v0.2 receipt-derived examples.
- Replace the “v0.1 ships no one-command product benchmark” note with the v0.2 `benchmark --quick` boundary.
- Allow a native runtime variant ID while requiring exact release identity.
- Keep method, redaction, and workload context mandatory.

## Existing visual sources and rasters

### `assets/banner.html` / `assets/banner.png`

- Make the headline/status lane-aware and stateful-first.
- Regenerate at 2560×640.
- Source and PNG must land together.

### `assets/og.html` / `assets/og.png`

- Add stateful/fail-closed positioning and qualified-versus-preview status.
- Regenerate at 1280×640.
- Keep the community-project footer.

### `assets/architecture.html` / `assets/architecture.png`

- Separate the primary 5090 container from native variants in labels.
- Scope durable restart to 4090.
- Regenerate at 2480×760.

### `assets/benchmarks.html` / `assets/benchmarks.png`

- Replace ambiguous lane arithmetic with “2 qualified / 1 preview.”
- Retain `235.02`, `99.87%`, `130,048`, `2,180.87 tok/s`, and `131,072`.
- Scope native restart to 4090 and label 3090 hardware evidence as pending.
- Regenerate at 2480×600.

## New launch-media files

### `docs/media/omp-ninfer-v0.2-overview.html`

- Deterministic frame-indexed animation source.
- Inline or locally resolved brand graphics only; no network resources.
- Owned by the media renderer.

### `docs/media/omp-ninfer-v0.2-overview.mp4`

- Canonical 27-second silent video.
- Generated only from the committed HTML source and pinned toolchain.

### `docs/media/omp-ninfer-v0.2-overview.gif`

- README-compatible animated derivative from the same frames.
- Optimize to the sibling convention or fallback size ceiling of 10 MiB.

### `docs/media/omp-ninfer-v0.2-overview-poster.png`

- Static summary frame for non-autoplay contexts and social uploads.

### `docs/media/omp-ninfer-v0.2-overview.provenance.json`

- Owns the reproducibility and claim ledger described above.
- Hashes the source and all outputs; it is not release evidence.

### `docs/media/README.md`

- Shows poster/GIF links and provides accessibility description.
- Documents the exact reproduction and `ffprobe` validation commands.
- States that the animation is scripted and measurements are receipt-derived.

### `docs/media/LAUNCH_COPY.md`

- Contains the channel-specific outline, shared claim ledger, 3090 response block, links, disclaimer, and prohibited claims.

### `scripts/render_launch_media.py`

- New deterministic media orchestrator/checker.
- Sequential, synchronous, no network, atomic output replacement.
- Reuse the sibling implementation shape instead of creating a second media framework.

## Tests

### `tests/test_public_numbers.py`

- Preserve all existing receipt-derived assertions.
- Add an assertion that `2,180.87 tok/s` is absent from `README.md` and overview/launch copy but remains in `docs/BENCHMARKS.md`.
- Assert the README still contains the badge substring and both v0.1 provenance phrases.
- Load `compatibility.json` and assert launch-facing 3090 copy uses preview/non-installable language rather than claiming support.

### `tests/test_launch_media.py`

- New standard-library media/provenance integrity tests.
- Validate hashes, file existence, dimensions, duration range, release ID, claim sources, and scripted-capture disclosure.
- Do not invoke Chromium or ffmpeg in ordinary unit tests.

No changes are planned for `scripts/verify_release.py`, `scripts/render_compatibility.py`, profiles, root/release compatibility authorities, generated compatibility Markdown, or release evidence.

# 5. Risks and migration

- **Release drift:** Even a whitespace edit under `releases/v0.2.0-beta.1/`, `compatibility.json`, or `docs/COMPATIBILITY.md` breaks the immutable graph. Guard these paths explicitly before every commit.
- **3090 overclaim:** Phrases such as “supports RTX 3090” or a three-GPU slash list can imply installability. Every compact visual must carry the preview label.
- **Measurement scope loss:** `235.02 tok/s` and `99.87%` are one RTX 5090 workload/profile, not 4090/3090 or universal claims.
- **Stateful overclaim:** “No re-prefill” applies to retained follow-ups, not cache-loss recovery. Keep the replay sentence adjacent in long-form prose and media disclosure.
- **Competitive drift:** README cells must be refreshed from primary sources and dated; unclear facts must be labeled rather than inferred.
- **Binary nondeterminism:** Browser/fonts/ffmpeg metadata can change output hashes. Pin toolchain bytes, render by frame number, strip metadata, and require a two-run hash comparison.
- **Repository size:** Enforce the sibling asset limits or fallback ceilings before commit. Prefer MP4 for quality and keep the GIF optimized for README use.
- **Issue-form compatibility:** Renamed field IDs affect new submissions only. Existing issues are immutable text and require no migration.
- **Rollback:** This pass has no runtime or persisted-data migration. Rollback consists of reverting mutable docs/assets/media commits; never rewrite the published release tag.

# 6. Implementation order

1. **Freeze and inventory the no-touch boundary.**
   - Record hashes/status of `compatibility.json`, `docs/COMPATIBILITY.md`, and `releases/v0.2.0-beta.1/`.
   - Inspect the sibling media convention at a fixed commit.
   - Refresh competitive facts from primary sources and record the actual review date.

2. **Update the brand and canonical status language.**
   - Modify `BRAND.md` first so downstream copy and visuals have one authority.
   - Update `ROADMAP.md`, `CONTRIBUTING.md`, root `SECURITY.md`, `docs/QUICKSTART.md`, `docs/BENCHMARKS.md`, `docs/PERFORMANCE.md`, and `docs/RELATED_WORK.md`.
   - Update both issue forms.
   - Run unit tests before adding binaries.

3. **Add the deterministic media source and renderer.**
   - Add the overview HTML, renderer/checker, media README, launch-copy outline, and provenance schema.
   - Generate frames in an isolated temporary directory.
   - Render MP4, GIF, and poster twice from clean directories and require identical SHA-256 values.
   - Add `tests/test_launch_media.py`.
   - Land the source, generated assets, provenance, and tests atomically.

4. **Refresh existing static launch assets.**
   - Update all four HTML sources.
   - Regenerate all four PNGs at the dimensions declared by `BRAND.md`.
   - Validate source/raster consistency and visual lane labels.
   - Land each source/output family in the same commit.

5. **Restructure `README.md`.**
   - Add the new hero hierarchy, proof strip, media links, and precise 3090 callout.
   - Tighten duplicate lower sections.
   - Add the researched LM Studio comparison.
   - Preserve all protected strings and remove `2,180.87 tok/s` from README text.

6. **Extend public-copy tests and changelog.**
   - Update `tests/test_public_numbers.py`.
   - Add `[Unreleased]` entries to `CHANGELOG.md`.
   - Perform a repository-wide stale-string audit for 5090-only, planned/deferred 4090/3090, and v0.1 support text.

7. **Run final validation.**

   ```sh
   python3 scripts/render_compatibility.py --check
   python3 scripts/render_launch_media.py --check
   python3 scripts/verify_release.py --require-ready
   python3 -m unittest discover -s tests -v
   bash -n examples/manual-tunnel/*.sh
   ```

   Production-media validation:

   ```sh
   ffprobe -v error -show_streams -show_format docs/media/omp-ninfer-v0.2-overview.mp4
   file docs/media/omp-ninfer-v0.2-overview.{gif,mp4} \
        docs/media/omp-ninfer-v0.2-overview-poster.png
   ```

   Protected-string checks:

   ```sh
   grep -F '235.02 tok/s' README.md docs/BENCHMARKS.md
   grep -F 'decode-235%20tok' README.md
   grep -F '99.87%' README.md docs/BENCHMARKS.md
   grep -F '130,048' README.md docs/BENCHMARKS.md
   grep -F '131,072' README.md docs/BENCHMARKS.md
   grep -F '2,180.87 tok/s' docs/BENCHMARKS.md
   grep -F 'predecessor v0.1 campaign' README.md
   grep -F 'not rebind that numeric result' README.md
   ```

   Immutable-boundary check:

   ```sh
   git diff --exit-code 273a89f49a6fd112c084c2c6fdc70d27a78c58d7 -- \
     compatibility.json \
     docs/COMPATIBILITY.md \
     releases/v0.2.0-beta.1
   ```

## Suggested Conventional Commit sequence

1. `docs(brand): align v0.2 launch positioning and support boundaries`
2. `docs(related-work): refresh local runtime comparison framing`
3. `docs(media): add reproducible v0.2 overview and launch copy`
4. `docs(assets): clarify qualified and preview runtime lanes`
5. `docs(readme): sharpen the v0.2 post-release hero`
6. `test(docs): protect launch claims and media provenance`
7. `docs(changelog): record the post-release launch pass`

The media source, generated binaries, provenance, and initial media integrity test must be atomic; the README commit must follow the media commit so it never introduces broken links.


> 💡 Continue this plan conversation with ask_oracle(chat_id: "post-release-launch-pass-486A1E", new_chat: false)