# OMP NInfer v0.8.0 — bring your own OMP

**Owner-operated, exact-profile 0.x release; no SLA.** RTX 5090 uses the manual Docker/SSH
route; RTX 4090 uses the native Windows package. The client is the unmodified upstream Oh My Pi
v18.3.0 release binary - no fork, archive or installer. Both GPU components advance to the
stock-client runtime; the model artifact and every serving setting are unchanged from v0.7.4.
RTX 3090 is deferred.

[Manifest](manifest.json) · [Qualification](qualification.json) ·
[Quickstart](../../docs/QUICKSTART.md) · [Security model](../../docs/SECURITY.md) ·
[Known limitations](#support-boundaries)

## Bring your own OMP

The documented client is the executable from the upstream
[Oh My Pi v18.3.0 release](https://github.com/can1357/oh-my-pi/releases/tag/v18.3.0), downloaded
and checked against its SHA-256:

| Client binary | SHA-256 |
| --- | --- |
| `omp-windows-x64.exe` | `9be13f13e3c11dcba25dfccfad0f8c508f66fd8bc2f95a0f06f2964be8d8f527` |
| `omp-linux-x64` | `d2fdaa29affe96e596eb9c78d42f548f1f291df28608631bcc00750a84b94bc3` |
| `omp-darwin-arm64` | `d61fb411f24146bed48dd901b13b5912a297d899ee691dda69c4b5b7ab8c35dc` |

The documented provider fragments do the rest: thinking stays within the server template's `low`,
`medium` and `xhigh` efforts, encrypted reasoning and reasoning summaries are off because the
server refuses fields it does not implement, and every route exports `PI_OPENAI_STATEFUL=1` so OMP
chains turns with `previous_response_id`. Stock OMP has no `omp appliance` commands: install and
operate each lane through its documented route. This product no longer builds or publishes an OMP
client.

## Runtime change

Stock OpenAI clients get durable sessions. With API authentication configured, a Responses or chat
request's `prompt_cache_key` becomes the session identity: the runtime hashes it under its own
domain and never stores the raw key, refuses it together with `ninfer_session` or
`X-NInfer-Session`, and treats a null key as no key. A client that resumes after both it and the
server restarted replays its transcript without naming a previous response; the runtime now
restores that session's checkpoint on its first request, and the engine's exact prefix match
decides how much it reuses.

A tool result may be content parts instead of a string. Stock OMP returns an image read as a
`function_call_output` whose output is an `input_text` and `input_image` array: the RTX 5090 passes
the image to the model inside the tool turn, and the text-only RTX 4090 refuses the image as
`vision_disabled` instead of rejecting the request as malformed.

New sessions start from the shared prefix. The shared-prefix catalog holds one owner per active
request or per cache marker a request may place, whichever is larger - four at one active
request - so each agent type's system and tool prefix keeps its own owner. On the published
RTX 5090 image, with three alternating agent types whose prefixes were 11,887-14,199 tokens, the
first session of each type prefilled its prefix in 3.8-4.4 s; none of the 24 later fresh sessions
fell back to a full prefill, and their median time to first token was 0.095-0.102 s.

Both components come from one runtime reviewed by an independent four-model council and four
remediation epochs ([dispositions](review/runtime-ledger.json)). The first epoch refused
`prompt_cache_key` together with `X-NInfer-Session` on chat completions, tightened the restore
pre-filter, and made concurrent first requests of one session restore it once; the second removed
a Windows pinning retry after the RTX 4090 qualification showed it could not recover. Route
acceptance on the first published components prompted the third, which accepts content-part tool
outputs and charges the RTX 4090 host pool's commit before pinning it; the fourth added the margin
that start still needed (see [Support boundaries](#support-boundaries)). RTX 5090 ships source
`86733c0e93fceccf9af3fa345ca9c8b6754f7abb`; RTX 4090 ships
`b0e8c2fa732e3a84eeb356c5e586879f3563c70c`, which adds only that Windows-only margin.

## Two qualified GPU routes

- RTX 5090: `v0.6.9-qwen38-5090-beta.2`, image
  `sha256:049dc788f6e5353b159edaece53afbabb219bc6e49f1e8ce8675338fada521a6`, server
  `d90079e887752aa3266a6c2d17ad0e029a35cfc12b6091d9851dde69c3100054`.
- RTX 4090: `v0.6.7-qwen38-4090-beta.2`, package
  `888a5859fb11d88cc374a944c680a5678d0a0a51b6562d4fce20f9934718fa0c`, server
  `e4688dda2307c5171ddb97fe7954e822deac837a56de40ca64ba0bfaa55ca244`.
- Unchanged model artifact:
  `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`.

Every runtime gate was measured on the published bytes. On the RTX 5090, the image was pulled
anonymously by digest and passed the profile gates (130,048-token exact retrieval, decode, the
agent protocol across a restart), the EXP-050 durability workload - four saves before eviction, a
stop with `saved 1, nothing to save 3, refused 0`, all four stored sessions restored from their
checkpoints after a restart, and a second stop refusing nothing - EXP-051's publication barrier,
and the fanout, warm-arrival, restore and multisession probes
([lane receipt](qualification/rtx5090.json)). The RTX 4090 package passed all 15 canonical native
phases, including its first managed start after a fresh install, 130,048-token retrieval, the
managed-stop flush of an unpublished session, rollback in both directions, protected state, and
the OMP 18.3.0 tool call ([lane receipt](qualification/rtx4090.json)).

On both lanes, unmodified OMP 18.3.0 configured only by the documented fragment kept one session
across graceful server restarts: one OMP process across a restart, a new process with the server
up, and a new process after a restart all recalled the seeded facts under one OMP session id, and
each lane restored the resuming process's first request from the session's checkpoint
([EXP-053](../../docs/measurements/2026-09-25-stock-omp-durable-sessions.json)).

RTX 5090 retains deployment `qwen38-5090-v0.7.0`, configuration
`762e6bf448b389cd6a8d08871a3df2c74080c5b1fbd7bbb95146030f1990eea8`, 16384 MiB host KV,
and a 28672 MiB host floor. RTX 4090 retains 11264 MiB host KV, 24 slots, and a 32768 MiB floor;
its release identity and configuration hash advance with the lane version.

RTX 3090 is omitted from this release pending access to its physical qualification host. Its
[v0.7.2 instructions](https://github.com/alphastorm/omp-ninfer/blob/v0.7.2/docs/QUICKSTART.md)
and OMP 18.0.9 client remain a separate historical route, not a v0.8.0 qualification claim.

## Upgrading from v0.7.4

Clone the v0.8.0 tag and follow the quickstart: install the upstream binary for your platform,
replace the provider fragment (its thinking and reasoning settings changed), and export
`PI_OPENAI_STATEFUL=1` in every shell that launches OMP. Sessions saved by the fork client under
`ninfer_session` names are not reachable from stock OMP: each takes one cold first turn after the
upgrade, and those checkpoints age out under the checkpoint quota.

## Support boundaries

An RTX 4090 start could fail when the driver refused to pin the host-KV pool
([#48](https://github.com/alphastorm/omp-ninfer/issues/48)). The lane's server commits about 39 GiB
on its 32 GiB host, so a start extends the system-managed pagefile, and a pin whose free commit
covered only its size raced that extension. The server now commits and releases each pinned
allocation's size plus 1/64 before pinning it; the qualified package passed its first managed
start after a fresh install, where the candidate without that margin was refused. The issue stays
open until field confirmation, and a refusal that still occurs reports the commit limit, available
commit and available memory.

Automatic checkpointing remains best effort under live traffic: a crash or an expired graceful
wait can still leave unpublished work unsaved. Saving before eviction delays the admitting
request - about 6.5 s per 126K-token session on the RTX 5090 - and that request waits while a
victim's reply is still reaching its client, bounded by its own queue deadline. Ceiling-class
save-before-evict was exercised on the RTX 5090; the RTX 4090 lane runs the same serving runtime
through its own phases. The multisession control again recorded root fallback on 2 of 8
continuations/forks; universal warm reuse is not claimed. Owner-operated exact profiles only; no
SLA, multi-GPU, multi-tenant, priority/preemption, or silent cloud fallback. Native Windows RTX 4090
is text/tools; vision remains an RTX 5090 container capability. Do not mix a predecessor manifest
with these commands.
