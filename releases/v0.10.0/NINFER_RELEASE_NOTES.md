# OMP NInfer v0.10.0 — DFlash2 on the RTX 5090

**Owner-operated, exact-profile 0.x release; no SLA.** RTX 5090 uses a Windows 11
Docker Desktop/WSL2 container reached by authenticated local loopback or a manual macOS SSH
tunnel; RTX 4090 and RTX 3090 use their native Windows 11 packages. RTX 5090 advances to
DFlash2 K=7 with BF16 KV on the published v0.6.15 runtime; all lanes use unmodified upstream
OMP 18.4.10. All five documented routes and composed installation acceptance passed on the
published components. The upstream engine merge and unattended RTX 3090 fleet role remain
deferred.

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Quickstart](../../docs/QUICKSTART.md) · [Security model](../../docs/SECURITY.md) ·
[Known limitations](#support-boundaries)

## Exact component identities

RTX 5090 runtime tag `v0.6.15-qwen38-5090-beta.1` and source tag
`v0.6.15-qwen38-5090-source.1` bind source `eaf221ac7a7c71e3b0049e59508e370c0ded4226`,
with upstream base `6e8b2e2ad5d53597c3ba8e7989f9546d40b921fc` as recorded by the window
identity and the predecessor manifest. The downloaded archive hashes to
`6cedad5812fd20eca83d22c03c5df0116a519c73eed17ab49eaa76acd7a0020f`; its extracted server hashes
to `7a8908e81b18d0a58dbe1391a7b6e5ad4ac622c008b49b9f589c25c1be8f5e68`. GitHub's published
SBOM and source-archive digests are respectively
`5e1d4c771073876bb562fde228c1c97b68f68f1bf53a6b891dc6fcaab133346a` and
`fbc7cb86aa85c59cf7e2edcf4454ba76e7f3b3e69aeaecc9ddfd19d4ae8f8f67`.

Runtime publication [workflow 37015468410](https://github.com/alphastorm/ninfer/actions/runs/37015468410)
succeeded. The `v0.6.15-qwen38-5090-runtime-beta.1` receipt binds the archive to
`ghcr.io/alphastorm/ninfer-runtime@sha256:fff4ee38bf687549470072f9bcc7285707577cc3892b5c68c6ec180e1e6b269b`.
The qualification window ran the package-local image built from that binary archive, not the
later published image. Fresh anonymous-pull and composed acceptance of the published image
passed separately; the qualification window alone does not establish that result.

The profile is `qwen38-5090-v0.10.0`, configuration
`8b2f495992c88d20287b4e31d0bb0b7118203081ea76bae46d80d8e571fd393a`, with 131,520 BF16 KV
tokens, 131,072 maximum context, DFlash2 K=7, two device state slots and two requests in flight.
The new model is 20,437,336,576 bytes, SHA-256
`0634abb07024221de141456cf04a42ab74b18bc38e1b781c6eb2e062a467eec3`, at public revision
`dc370fb6295ae8b786e1af4f90d7142a16255c35`. Size and checksum are from its
[published artifact manifest](https://huggingface.co/neroued/Qwen3.8-27B-NInfer/resolve/dc370fb6295ae8b786e1af4f90d7142a16255c35/artifact-manifest.json);
the public repository API resolves that revision. The native lanes retain their previous model
`eec39564` through `components.native_model`; their package and model hashes do not change.

The client is the unmodified `can1357/oh-my-pi` v18.4.10 release, source
`cb0d5295e5edd48d000c1979e195186ec92aac79`, tree `ab30077eeffb21ce3d5e49641aafe5553712a9cd`,
GitHub release 401477136. Its raw macOS arm64, Windows x64 and Linux x64 asset hashes are also
the binary hashes. This does not use the downstream OMP/Homebrew archive. Fresh acceptance
passed for all three binaries; the window's stock OMP 18.4.0 proofs remain historical evidence,
not qualification of these newer client binaries.

## Lane receipt and candidate arc

The original `v0100-eaf221ac-profile.json` has artifact type
`omp_ninfer_rtx5090_profile_gates`, generated at 2026-10-02T05:26:31Z. It was retrieved read-only
from the retained appliance and installed byte-for-byte at `qualification/rtx5090.json`, SHA-256
`28c06311cb0cf76224f8eb08254ac79bdc1e235a55e2ecd62dd34a8c2013538f`. It is the profile-gate
artifact expected by the staging script, not a fabricated aggregate. The candidate arc
and numbers below record the window PLAN's fourth-candidate result and criterion-14 decision;
this profile receipt and the later published-component acceptance remain distinct evidence.

Candidate c11b02f4 failed criteria 13 and 15: a store:false continuation could evict its
own stored seed without saving first. Candidate 6cad4075 preserved both sessions but one resumed
from root; criterion 14 also failed. Candidate 2020a1a4 preserved a queued named session's
DeviceFork replay capture but still missed the HostSnapshot placement under slot pressure;
it failed criteria 4 and 13. EXP-091 found one MTP3 server instance diverging for its lifetime,
with the cause unresolved. The fourth candidate eaf221ac keeps the masked-draft ResponseReplay
capture in both placements. Its MTP3 control did not repeat that divergence.

## Fourth-candidate qualification gates

The 2026-10-02 05:02:37–06:34:22Z window passed criteria 1–13 and 15. Identity was exact
on every server start: source eaf221ac, server 7a8908e8, clean source, configuration 8b2f4959,
model 0634abb0 and the profile above. Every recorded GPU oracle and real-model test exited 0.
The role corpus was 84/84 identical to the EXP-085 screen, 89/89 to candidate 6cad4075 and
86/89 to production; log-016/019/020 were the same three differences. Criterion 4's MTP3 control
was 89/89 identical to both production and candidate 6cad4075's control.

The original profile receipt records exact 130,048-token retrieval in 58.738 s and
161.39 decode tokens/s (159.92 completion tokens/s wall-clock for 2,048 output tokens), with
29,468 MiB VRAM idle/final. Its agent protocol passed authenticated identity, stateful
continuation, two forks, deletion returning 404 after restart without resurrection, and live
sibling/descendant continuation. These figures describe this exact candidate, not all hardware.

The window's stock OMP 18.4.0 client proof exited 0. Long-session evidence had zero root prefills over 60K
tokens; run 3 stopped at the registered predecessor harness precondition, not a new passing
long-session result. The short-session sequence retained 60,021 cached tokens. The workload
restored 4/4 sessions with zero shutdown refusals; the barrier was exact; probes exited 0,
with multisession reuse lost on 2/8 continuations/forks. Agent mix had zero root prefills.
The c2probe passed with seven shutdown refusals, within the registered allowance; this is not
a claim that every live checkpoint save succeeds.

Criterion 13 passed for the first time on all three c2restart repeats: both D1 and D2
resumed with 62,404 cached tokens each, first-output latency 5.5–7.1 s and total time 9.0–10.3 s.
The retained evidence files are `v0100-eaf221ac-c2restart.json` and
`v0100-eaf221ac-c2probe.json`; raw private logs and session material are not release artifacts.

## Criterion 14: failures, amendment, deciding rerun

Limit 1 passed both original runs. Limit 2 failed twice in the subagents scenario despite
all server requests completing without cancellation/error and the identity, provider-limit and
concurrency checks passing. The first run had batches [2,2] and a task call without results;
the registered rerun had [2,1], exact final codes and no task call without results, but one scout
omitted its code and the parent dispatched it again. Overlap was 13.5 s and 20.4 s respectively.
Under the original rule the second result failed criterion 14; it is not relabeled as a pass.

The founder chose the proof amendment in [PR #74](https://github.com/alphastorm/omp-ninfer/pull/74),
not acceptance of a failed check. It requires the first task call to dispatch both scouts,
completed subagents and codes actually delivered by subagents, while allowing recovery calls;
sequential [1,1], errored/missing subagents and missing delivered codes still fail. A new
13:43:40–13:46:32Z ompparallel-only run passed both limits with this amended proof. At limit 2,
subagents used batches [2], `recovered_dispatch: false`, maximum in flight 2, overlap 9.679 s,
and one server instance with every request completed; the sessions scenario overlapped 3.229 s.
Criterion 14 therefore passes under the amended criterion, completing criteria 1–15.

The deciding receipts are `ompparallel-1.json` and `ompparallel-2.json` in the current
`lane-window-v0100-eaf221ac` evidence set. `lane-window-v0100-eaf221ac.run1` and
`lane-window-v0100-eaf221ac.run2-ompparallel` preserve the superseded runs. A 13:40Z attempt
was killed before proof startup and produced no receipt. The window and completed reruns
record production restored healthy.

## Carried lanes and historical evidence

RTX 3090 remains on `v0.6.2-qwen38-3090-beta.1` and RTX 4090 on
`v0.6.10-qwen38-4090-beta.1`, with their historical lane receipts and predecessor model retained.
The OMP 18.4.0 references in these notes, the manifest limitations, `qualification.json`,
`qualification/rtx3090.json` and `qualification/rtx4090.json` record the clients actually
exercised in the candidate window and carried native-lane measurements, including the RTX 4090
orchestrator rerun. EXP-074's process-restart observation is also historical. These references
are an evidence inventory, not current client pins or acceptance of OMP 18.4.10. The inherited
durable RTX 5090 and review ledgers remain predecessor records, not fresh review approval.
Fresh platform-client and published-component route/composed acceptance is linked below.

## Documented routes and clients

All **five documented routes, 31 steps** passed on candidate
`ca9298222ed09f84e3c0e15ff6ef75218d942fb0` with unmodified upstream OMP **18.4.10**, published
RTX 5090 image `fff4ee38`, RTX 4090 package `a0ea4c81` and RTX 3090 package `da1d62f2`.
The receipts record the pre-cut substitution of that commit for the not-yet-created tag and
an installable check for the ready check; the executable blocks are otherwise bound by hash.

| Route | Steps | Sum of step elapsed seconds | Recorded environment | Receipt |
| --- | ---: | ---: | --- | --- |
| RTX 5090 container host | 2 | 54.869 | Ubuntu 24.04.4 LTS under Windows Docker Desktop/WSL2 | [run](../../docs/measurements/2026-10-02-v0100-rtx5090-container-host-run.json) |
| RTX 5090 macOS client | 10 | 108.626 | macOS 27.0.1 arm64 | [run](../../docs/measurements/2026-10-02-v0100-rtx5090-macos-client-run.json) |
| RTX 5090 Windows client | 5 | 48.258 | Windows 11 Pro | [run](../../docs/measurements/2026-10-02-v0100-rtx5090-windows-client-run.json) |
| RTX 4090 native Windows | 7 | 418.322 | Windows 11 Pro | [run](../../docs/measurements/2026-10-02-v0100-rtx4090-native-run.json) |
| RTX 3090 native Windows | 7 | 1,142.220 | Windows 11 Pro | [run](../../docs/measurements/2026-10-02-v0100-rtx3090-native-run.json) |

These are sums of the recorded step timers, not end-to-end installation durations. Both native
routes performed fresh canonical upgrade installations after preserving the active published
instances; they do not establish an idempotent-reinstall claim.
[Documented routes](acceptance/documented-routes.json) ·
[RTX 4090 public install](acceptance/rtx4090-public-install.json) ·
[RTX 3090 public install](acceptance/rtx3090-public-install.json).

The upstream macOS arm64, Windows x64 and Linux x64 binaries each passed an authenticated typed
tool turn, exact continuation and fail-closed request against the published RTX 5090 image
([composed acceptance](acceptance/composed-external-installation.json)). macOS remains preview:
the upstream client has no managed installation or appliance lifecycle. Linux ran under Ubuntu
WSL2, not a separately qualified non-WSL Linux OS. Vision passed on the RTX 5090; native lanes
remain text/tools. All observations are maintainer-operated, not independent external-user
installation or repeat-use outcomes.

The RTX 5090 window passed on its **first attempt**, in the c2 workspace, from the maintainer's
Apple silicon workstation over the tailnet, with production downtime at most **387.499 s
(6.5 min)**. The earlier candidate `20a75bd5` failed both native routes on the native-model
block before any install effect. On the accepted candidate, RTX 4090 passed in **attempt c4**
after two refusals before any install effect: staged-model timestamps changed by the first
candidate's resumed download, then an interactive GPU owner (Desktop Window Manager above
1 GiB, with nobody signed in). RTX 3090 passed in **attempt c5**, with the console signed out,
after refusals for an interactive GPU owner (NVIDIA Overlay on the signed-in console).
All hosts were restored after every attempt; the accepted runs' receipt records the original
RTX 5090 runtime healthy, native state and task definitions unchanged, and no production upgrade
activated ([restoration](../../docs/measurements/2026-10-02-v0100-acceptance-restoration.json)).

## Upgrading from v0.9.1

Use the exact v0.10.0 manifest and quickstart for the new OMP 18.4.10 binaries on every lane.
RTX 5090 changes runtime, model and profile: install the v0.6.15 image and model `0634abb0`,
then use the DFlash2 K=7/BF16 profile with two device state slots. Both prompts plus output
reservations must fit the 131,520-token KV pool; the pending timeout is 180 s. Predecessor
checkpoint reuse is not claimed because the runtime fingerprint and model change.
RTX 4090 and RTX 3090 retain their runtime packages, native model and serving profiles.
The historical v0.7.2 RTX 3090 lineage and OMP 18.0.9 client remain separate; its sessions do
not carry over. Do not use a generic `omp update` to move beyond this release's pinned bytes.

## Support boundaries

A managed RTX 3090 or RTX 4090 start refuses while any process holds at least 1 GiB of GPU
memory, including the desktop compositor or NVIDIA Overlay. Closing applications or signing
out alone does not establish that the GPU is free. RTX 3090 rollback remains proven against
its unpublished v0.6.0-beta.1 predecessor; that package predates the stop-event channel and
stops by termination. Native Windows lanes are text/tools; vision is RTX 5090 only.

Automatic checkpointing remains best effort under live traffic. A crash or expired graceful
wait can leave unpublished work unsaved; multisession reuse was lost on 2/8 continuations/forks.
Concurrent prefill can delay peer decode, and two requests in flight do not provide preemption
or universal warm reuse. The predecessor's latency and throughput do not describe this changed
runtime and model. Historical OMP 18.4.0 process-restart observations are not a claim about
18.4.10's resume behavior beyond the fresh acceptance receipts.

All hardware observations are maintainer-operated. Throughput and latency apply only to the
recorded packages, machines and profiles, not universal GPU performance or faster OMP work.
Owner-operated exact profiles only: no SLA, automatic container restart, structured JSON-schema
output, multi-GPU, multi-tenant, priority/preemption or silent cloud fallback. Do not mix a
predecessor manifest with these commands.
