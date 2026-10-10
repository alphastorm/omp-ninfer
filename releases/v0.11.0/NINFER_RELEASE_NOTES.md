# OMP NInfer v0.11.0 — draft, not a released product

Proposed RTX 5090 component **v0.6.16**, source
`a59c13d00492d47dc58bf822533688c90c5d1f6a`, combined with unmodified upstream OMP
**18.8.7**. Root runtime/model pins and the published v0.10.0 release remain unchanged.
No tag, GitHub release, registry push, route acceptance or production promotion was performed.

## Exact component and build

v0.6.15 source `eaf221ac` plus `3a2fadbd` (small-T pair Q5 mixer), `b72daad6`
(EXP-092) and `a59c13d0` (EXP-094), with **no source edits**. The appliance-local
clean Release build used `ninfer-dflash2-build-env:20261001`, CUDA **13.1.115**,
GNU **13.3.0** and `sm_120a`. The packaged serve reports that commit and a clean tree.

- Serve SHA-256: `675e72e66bce5ef75b74107930d521ad8f7188e38e83907b009d6a58e8ba5df8`.
- Local image: `ninfer-overnight:S1-a59c13d0-package-local`; image ID
  `sha256:a848d2bce422c4511d4375f22434b3e4cbc379f759cdb4d318526de370569af7`.
  This is **not an OCI publication digest**.
- Model `0634abb07024221de141456cf04a42ab74b18bc38e1b781c6eb2e062a467eec3`,
  20,437,336,576 bytes.
- Deployment profile `qwen38-5090-v0.11.0`; configuration identity
  `91a3567002a43025876e811597353764b20e32f0818bcb6c582a5072c96d7e11`.
- Shape unchanged from v0.10.0: DFlash2 K=7, BF16 KV, two in flight, two device slots,
  131,520 KV tokens, 131,072-token context ceiling and 180-second pending timeout.

### Assets and founder dry-run

Verified on the Mac in `$HOME/Desktop/ninfer-v0.6.16-release/`:

| Asset | SHA-256 |
| --- | --- |
| ninfer-qwen38-rtx5090-v0.6.16-linux-x86_64-cuda13.1.tar.gz | 95dbe24fade7b776cedf23d3dda0baa9870413b360759dd403ad0351e1f65d10 |
| ninfer-qwen38-rtx5090-v0.6.16-linux-x86_64-cuda13.1.spdx.json | fdad0f6b905d7a3ff132733c966c92230bfa089e437fd4abf0a71d31d2ad12dc |
| ninfer-qwen38-rtx5090-v0.6.16-linux-x86_64-cuda13.1.SHA256SUMS | 7fc5b4d0097043a5af6d0adfa74a3e20622106e392fb1cc2c0e935d30f17cace |
| runtime-source-a59c13d0.tar.gz | 30b89a50d008f621754fdb9d6e4b138588f3acddbbc14ae32206093e172fa543 |

The source archive equals the Mac's `git archive --format=tar.gz` of the exact commit.
The cutter's **--dry-run passed**; no tag, release or workflow run was created.
[Build receipt](qualification/build.json) · [cutter preflight](qualification/component-cut-dry-run.json).

## Qualification — retain red and invalid verdicts

The full sm_120a ctest run returned **8**: **110 passed, seven skipped, one failed**
(118 tests; 865.41 seconds). The failed NVFP4 graph/serial test reports:
“NVFP4 graph batch row differs from its serial NVFP4 oracle.” All direct supported BF16
K=7 checks passed. The earlier eaf221ac release logs did not build that NVFP4 target,
so a shipped-baseline pass or failure could not be inferred from them. Fresh exact
eaf221ac built and passed; fresh exact3a2fadbd built and failed the same assertion.
The first red is therefore3a, before EXP092/094. This is strict generated-TokenId
vector equality, not a floating tolerance. The test does not identify the first
divergent op,row or token. Its ordinary eager C1/T1 oracle differs from graph-enabled
DFlash2K7/C2/T8–16 in more than scheduling. The sole3a runtime change routes
K6144/T16 from MmaResidualR64C16 to Split2ExactResidual; intermediate numerical
mechanism is unmeasured. [Source attribution](qualification/nvfp4-source-attribution.json)
retains both test exits/log hashes and the precise contract. No source fix or
unchanged-test rerun was made.
The Q5 resolver keys the tensor shape, not KV storage; T1 uses residual GEMV while
T8/T16 use the small-T MMA on sm120. The new T16 route matching T8 is not an exact
T1-oracle guarantee. Different arithmetic paths changing greedy TokenIds is an
inference, not a measured first-op mechanism or evidence of cross-row state corruption.

Founder source choices (the release proposal remains exact `a59c13d0`):

| Choice | Source | Observed evidence and cost | Founder gate |
|---|---|---|---|
| (a) Restrict the pair route | New source change to3a | Not attempted; clean rebuild, EXP092/094 remeasurement and rescreen required | Approve and qualify a real source fix; do not relax the oracle |
| (b) Keep the exact target | `a59c13d0` | All15 original local lane criteria pass; full ctest110 pass/7 skip/1 fail in the unshipped NVFP4-KV configuration rejected by EXP085 | Explicit all-green-ctest policy exception, not a skip or suppression; none approved |
| (c) Omit3a | Local, **unpublished** `1302d63929e400a05e1c9cdb0fc8003a70269825`: eaf+b72+a59 without3a | Clean full sm_120a ctest **111 pass/7 skip/0 fail**, including the NVFP4 oracle;89/89 serial output signatures and request bodies match unchanged a59 (84 counted cases,0 errors;5 vacuous fixture errors excluded). A/B/B/A pair round cost **+9.35%**,19.408→21.222ms; pair aggregate wall throughput505.40→462.33tok/s (**−8.52%**). Single-request round cost changes−0.14% to−0.004% across0/32K/64K/120K. | **Experiment, not candidate**. Source selection and any source publication/cut remain founder decisions; no replacement of the a59 assets or proposal |

Option-C cherry-picks applied without conflicts: b72 replay
`344850b3e9e3c8f5855f6a979a630d1c4eada4a8`, then a59 replay`1302d639…`.
The runtime experiment branch was not pushed. The serve SHA is
`548fe239a3f2f97c98d864b4a7b9c6beb1263788633f1a4bf13c101f2beecace`;
its clean version reports CUDA13.1.115/GNU13.3.0/sm_120a. The source archive
SHA`dbf5a221d99fdcfa315ae880f2fe58744e90f44d139bfc5ab1ded5d8b83c37b2`
equals a Mac `git archive` of that exact local commit. Assets are retained separately
from the original component handoff. The serial quality transfer is transitive
through the measured a59→EXP094 binding; it is not a newly run powered screen or
a claim of pair output invariance. The nonce-dependent decode-token-rate swings
are not attributed to source omission: per-round cost is the comparison metric.
[Source](qualification/option-c-source.json) · [Build](qualification/option-c-build.json) ·
[Serial binding](qualification/option-c-output-identity.json) · [ABBA](qualification/option-c-abba.json).

The exact new binary differs from EXP-094's `884e5a43…` binary. One uninterrupted
lease ran the same frozen 89-case role corpus on both images: **89/89 output signatures
matched**, with 84 counted cases and zero counted errors in each arm. Five vacuous
fixture errors are explicitly excluded in both arms. This transfers EXP-094's frozen
EXP-085 powered-screen pass to this exact binary **for that serial method**, not to
a fresh full screen or solo/pair equivalence.
[Quality binding](qualification/output-identity.json).

A separate unchanged-BF16-profile five-case control found **1/5** solo/paired signatures
identical and **4/5** different, with actual content/reasoning changes, matching request
hashes and zero errors in either arm. Real two-row execution was observed. The same
five cases on the shipped eaf221ac image also yielded1/5identical and4/5different,
with real pair execution (2329row-rounds/1592rounds). The supported-profile
scheduling dependence is therefore pre-existing, not newly attributable to EXP094.
This does not prove its numerical mechanism is identical to the NVFP4 oracle failure.
[Shipped control](qualification/bf16-solo-pair-shipped.json).
[Pair receipt](qualification/bf16-solo-pair-candidate.json) ·
[field comparison](qualification/bf16-solo-pair-difference-fields.json).

### Criteria 1–15

The detailed [lane receipt](qualification/lane.json) distinguishes formal predecessor
criteria from independently red diagnostics. Criteria 10–14 of the initial job were
**invalidated by the lead's external Docker stop**, not by the candidate. The corrected
lease is `20261010T085424Z-S1-lane-criteria-10-14-external-stop-cleared-1267878`;
it completed exit0 in2,454seconds with no leftovers. All15 unchanged criteria pass
on the actual replacement receipts: **qualified except for the ctest disposition**.
The invalid initial attempt remains invalid and preserved; it is not relabelled green.

| Criterion | Verdict | Unchanged requirement | Exercised evidence |
| --- | --- | --- | --- |
| 1 | PASS | Clean exact source/build/model/image/config identity; unchanged supported serving shape | source_dirty=false; kv_pool_tokens=131520; context_tokens=131072; max_in_flight=2; device_state_slots=2; pending_timeout_ms=180000 |
| 2 | PASS | Precedent-selected CPU/oracle/BF16 tests | full_suite_total=118; full_suite_passed=110; full_suite_skipped=7; full_suite_failed=1; full_suite_exit=8 |
| 3 | PASS | Quality evidence bound to the exact packaged binary | binary_identical_to_exp094=false; identical_serial_role_signatures=89; different_serial_role_signatures=0; counted_cases=84; counted_errors_each_arm=0; excluded_vacuous_errors_each_arm=5 |
| 4 | PASS | MTP3 control matches the frozen v0.9.0 production corpus | compared_cases=89; identical_signatures=89; different_signatures=0; identical_request_bodies=89 |
| 5 | PASS | Exact 130,048-token retrieval, exact 2,048-token decode, agent protocol across restart | retrieval_prompt_tokens=130048; retrieval_exact=true; retrieval_wall_s=58.917; decode_output_tokens=2048; decode_server_tok_s=179.79; decode_wall_tok_s=177.95; deleted_descendant_post_restart_status=404; no_resurrection=true; live_survivor_restored=true; idle_vram_mib=29468; retrieval_vram_mib=29470; transient_retries=0 |
| 6 | PASS | Actual stock OMP macOS arm64 proof exits 0 | checks_passed=6; passed=true |
| 7 | PASS | No chained root prefill above 60K; each long run succeeds or stops at the documented predecessor harness precondition | runs=3; successful_runs=2; predecessor_harness_precondition_runs=1; compactions_committed=6; max_root_computed_prefill_tokens=58112; root_prefills_over_60000=0 |
| 8 | PASS | Quota reclamation and post-crash long continuation retains at least 60K cached tokens | short_records=35; quota_bytes=25769803776; reclaimed=true; crash_exit=0; continuation_input_tokens=60079; continuation_cached_tokens=60057; continuation_wall_s=2.31 |
| 9 | PASS | No workload errors, all stored sessions restored from checkpoints, first shutdown refused 0 | workload_errors=0; stored_sessions=4; restored_from_checkpoint=4; multisession_reuse_losses=0; multisession_continuations=8; first_shutdown_refused=0 |
| 10 | PASS | Held publication barrier resumes exactly; zero shutdown refusals | six-second held barrier hit; resume exact; shutdown refused0 |
| 11 | PASS | Fanout57k/fanout67k/warm-arrival/restore exit0; multisession loss at most2/8 | all exits0; multisession reuse loss2/8; fanout hot medians0.668/0.790s; restore2.877/2.689s |
| 12 | PASS | Agent mix fresh roots0/24 | measured fresh roots0/24; continuation roots0/24; errors0 |
| 13 | PASS | All7C2 scenarios repeat2 pass; all3 restart pairs retain at least62404 cached tokens per session | all14scenario runs pass; six post-restart sessions each cached62404; request failures0 |
| 14 | PASS | Actual OMP18.8.7 limits1 then2 on same instance, amended #74 criterion | both pass; task batches[2] then recovered[2,2]; subagents complete/codes delivered/parent exact; same instance; pair overlap13.146s |
| 15 | PASS | All request logs without server errors; C2 shutdown refusals at most7, every other step0 | all12stages0server request errors; C2probe refused7; every other stage0 |

The third long-session plant-after=3 run exited 1 at the unchanged, expressly admitted
predecessor harness precondition. Two compactions had committed; its failure remains
a failure. Across all three runs, the largest computed/root prefill was **58,112**
tokens and there were **zero** root prefills above 60K. Both other runs passed.
[Long sessions](qualification/long-sessions.json).

All four durable workload sessions restored from checkpoint, but desk-code exactness
after restore was **D1 true / D2 false**. That semantic failure is retained separately
from the mechanical command's exit 0. All six completed initial stages had zero
server request errors and zero shutdown refusals.
[Durability](qualification/durability.json) · [logs](qualification/lane-logs-initial.json).
Replacement receipts: [held barrier](qualification/publication-barrier.json) ·
[fanout/restore](qualification/fanout-restore.json) · [agent mix](qualification/agent-mix.json) ·
[C2 and restart](qualification/concurrency.json) · [actual OMP parallel](qualification/omp-parallel.json) ·
[all12stage logs](qualification/lane-logs.json). The recovered[2,2]limit2 task dispatch
passed amendment#74 with all subagents completed/codes delivered and exact parent
answer; it is explicitly not an unrecovered[1,1]dispatch.

Qualification finished before15:00Z. The required gpu-lease status observation at
10:12:02Z found S5 holding and four queued jobs, so the conjunctive empty-queue
condition for an extra full powered screen was false. No extra screen is claimed.

The stock macOS arm64 client is the real upstream 18.8.7 binary, SHA-256
`cf0227bdefca0c486bd2aed1771de3ab98930266883eb69d341caf5665caee14`. Its six stock proof
checks passed. Frozen probe hashes and exact source diffs are in
[probe provenance](qualification/omp-1887-probe-provenance.json); the corrected parallel
job uses unmodified S2 `239eec2` tooling with supported version/hash flags, documented
in [parallel provenance](qualification/omp-1887-parallel-provenance.json). The branch
was rebased onto S2 final `38a81628e2fb9e35d5b831610489133a5f5c35e7`.
Its final follow-on `b622cbda514ce381658f631cdf1ad61b4b89b7bd` was cherry-picked
as eaee6d0, binding non-candidate contracts to manifest OMP identity and resumed
host-probe phases to their preflight version/environment. Eight affected upstream
verifier tests passed after this change; the descriptor and its hash are unchanged.

### Measured performance, not a wider promise

Exact 130,048-token retrieval: **58.917 s**, versus v0.10.0 **58.738 s** (+0.305% wall
time). Exact 2,048-token decode: **179.79 server tok/s**, versus **161.39 tok/s**
(+11.40%); wall throughput **177.95 tok/s**. Idle/peak retrieval VRAM: **29,468 /
29,470 MiB**. This does not retest EXP-094's traffic-weighted **+9.6%** prediction or
its separate short/long/pair round-duration claims. [Profile receipt](qualification/rtx5090.json).

## Release tooling

- Enumerate exactly v0.6.16, not a wildcard, in the runtime-tag verifier. The focused
  allowlist regression passed.
- The promote_root bug was real: upstream root clients all received the primary
  Windows asset. The new per-platform selection preserves full Darwin/Windows
  distribution metadata; the regression was observed red before and green after.
- The verifier now checks the same platform-specific archive pins. Its six focused
  upstream tests passed; legacy fork archive checks are intentionally unchanged.
- Staging's sole obsolete diagnostic consumer was migrated; a public-root draft
  regression was red before and green after. The candidate-relabelling security
  regression also passed. Full repository verification belongs to the existing
  Ubuntu/Python 3.11 draft-PR CI.
The initial draft commit a1379e45b66abb4016f4a63eb097bc34d3cefe94 passed the
full workflow in [CI38042843797](https://github.com/alphastorm/omp-ninfer/actions/runs/38042843797).
That result precedes the final S2 follow-on and is not a final-head substitution.
The follow-on exposed the staging regression fixture's legacy OMP18.3 descriptor
with a modern per-model provider contract; CI38043597806 retained that failure.
The fixture now uses its real legacy environment and explicitly asserts both
platform draft-pin diagnostics, without weakening the provider verifier. The
corrected code/test head d7e32dd0908fb1b16ace1e0ac5dec1108740b936 passed all
workflow steps in [CI38043955727](https://github.com/alphastorm/omp-ninfer/actions/runs/38043955727).

## Founder morning sequence — admission → cut → stage → acceptance

First read the completed corrected lease receipts, disposition the independently red tests/quality
observations, and decide whether this exact source is admissible. If a runtime source
fix is required, this component is not a releasable substitute for EXP-092/094 evidence.

### 1. Founder-only live component cut

The following is **not an agent command**. Only its --dry-run form was executed tonight:

```bash
PATH="/opt/homebrew/opt/python@3.13/libexec/bin:$PATH" \
NINFER_RUNTIME_DIR="$HOME/Development/ninfer-S1" \
bash scripts/hosts/cut-ninfer-5090-component.sh \
  --version v0.6.16 \
  --commit a59c13d00492d47dc58bf822533688c90c5d1f6a \
  --assets "$HOME/Desktop/ninfer-v0.6.16-release" \
  --archive-sha 95dbe24fade7b776cedf23d3dda0baa9870413b360759dd403ad0351e1f65d10 \
  --sbom-sha fdad0f6b905d7a3ff132733c966c92230bfa089e437fd4abf0a71d31d2ad12dc \
  --source-archive-sha 30b89a50d008f621754fdb9d6e4b138588f3acddbbc14ae32206093e172fa543 \
  --beta 1 \
  --notes-file "$HOME/Desktop/ninfer-v0.6.16-release/NINFER_RELEASE_NOTES.md"
```

Wait for the component publication and runtime-image workflow. Verify its published
receipt against these exact hashes and export the **real** OCI digest as
`NINFER_OCI_DIGEST`. Do not reuse the local Docker image ID or fabricate a digest.

### 2. Stage with the verified OMP 18.8.7 descriptor

The existing draft must first be preserved outside `releases/`; stage_release refuses
a pre-existing destination. The exact command preserves it and uses its actual lane receipt:

```bash
V011_DRAFT_BACKUP="$(mktemp -d "${TMPDIR:-/tmp}/omp-ninfer-v011-draft.XXXXXX")/v0.11.0"
mv releases/v0.11.0 "$V011_DRAFT_BACKUP"
/opt/homebrew/bin/python3.13 scripts/stage_release.py \
  --from v0.10.0 --release v0.11.0 \
  --release-tag v0.6.16-qwen38-5090-beta.1 \
  --source-tag v0.6.16-qwen38-5090-source.1 \
  --source-commit a59c13d00492d47dc58bf822533688c90c5d1f6a \
  --binary-sha 675e72e66bce5ef75b74107930d521ad8f7188e38e83907b009d6a58e8ba5df8 \
  --archive-sha 95dbe24fade7b776cedf23d3dda0baa9870413b360759dd403ad0351e1f65d10 \
  --source-archive-sha 30b89a50d008f621754fdb9d6e4b138588f3acddbbc14ae32206093e172fa543 \
  --sbom-sha fdad0f6b905d7a3ff132733c966c92230bfa089e437fd4abf0a71d31d2ad12dc \
  --image-digest "${NINFER_OCI_DIGEST:?supply the real digest from the founder component cut}" \
  --runtime-receipt-release v0.6.16-qwen38-5090-runtime-beta.1 \
  --config-sha 91a3567002a43025876e811597353764b20e32f0818bcb6c582a5072c96d7e11 \
  --lane-receipt "$V011_DRAFT_BACKUP/qualification/rtx5090.json" \
  --omp-component docs/measurements/2026-10-10-omp-1887-client-components.json
```

Descriptor SHA-256: `728f6c4486ae7ebf5d7d7b6033b1307d55edc1fbc4f8748de6e689aadb4bd4e9`.
Merge supplemental receipts and updated notes back without overwriting generated
manifest/qualification/compatibility bindings. Freeze and publish the final lane
evidence commit, then pin it with
`rebind_release.py --release v0.11.0 --stage lane --pin "$V011_LANE_COMMIT"`.
The cut and promote_root **do not clear root status:candidate**; resolve that posture
from real qualification. Never relabel unqualified profiles to evade candidate guards.

### 3. Published-image acceptance window

Only after a frozen, legitimately installable product candidate and the real rollback
image/host destinations are known, run fresh preflight and then the founder-authorized
window. These commands are documented only; no acceptance driver was run tonight:

```bash
acceptance=(
  /opt/homebrew/bin/python3.13 scripts/hosts/accept-rtx5090-routes.py
  --release v0.11.0
  --candidate "${V011_CANDIDATE_COMMIT:?published frozen 40-hex candidate}"
  --workspace "${V011_MAC_ACCEPTANCE_DIR:?fresh private Mac evidence directory}"
  --wsl-workspace "${V011_WSL_ACCEPTANCE_DIR:?fresh absolute private POSIX evidence directory}"
  --windows-workspace "${V011_WINDOWS_ACCEPTANCE_DIR:?fresh absolute C:/ private evidence directory}"
  --production-image "${RTX5090_INCUMBENT_OCI_IMAGE:?actual measured incumbent rollback image}"
  --wsl-host "${RTX5090_WSL_SSH:?verified POSIX SSH destination, not an assumed alias}"
  --windows-host "${RTX5090_WINDOWS_SSH:?verified Windows SSH destination}"
  --route-ssh-destination "${RTX5090_DOCUMENTED_SSH_DESTINATION:?actual documented route destination}"
)
"${acceptance[@]}" --action preflight
"${acceptance[@]}" --action window
```

The window's independent watchdog/restoration behavior is appropriate for this future
founder-controlled acceptance, not for the overnight exclusive lease. Compose fresh
receipts for every retained route, then platform/acceptance/manifest pin stages and
`--require-ready --check-pins` before the product cut.

### Explicit blockers

1. **Native RTX 4090:** no host; the designated machine has held an RTX PRO 6000 since
   2026-10-05. Founder decides retire versus hold. No substituted GPU is qualified.
2. **Native RTX 3090:** fresh OMP 18.8.7 acceptance is outside tonight's scope.
3. **All retained documented routes:** fresh acceptance must use the anonymously
   pullable published image after the cut, not this package-local image.
4. The unshipped NVFP4 ctest failure requires the founder's explicit policy disposition;
   a legitimate candidate-posture transition remains a prerequisite. Cutter preflight
   success does not clear either gate.

All public receipts omit raw prompts, generated content, secrets, private hostnames
and absolute private paths. Lease jobs and exact identity hashes are preserved.
