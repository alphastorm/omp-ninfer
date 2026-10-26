# Fleet: two model-bound agents, one per qualified lane

Run up to two concurrent OMP agents, each statically pinned to one qualified NInfer lane. Every
endpoint stays loopback-only on its own machine; reach remote lanes through authenticated SSH
local forwards (the managed route), never by exposing a listener.

| Role | Lane | OMP model | Notes |
| --- | --- | --- | --- |
| `main` | RTX 5090 container | `ninfer-main/q38-ninfer` | 131,072-token ceiling; durable checkpoints as of v0.4.0 |
| `heavy` | RTX 4090 native Windows | `ninfer-heavy/qwen3.8-27b` | MTP3 profile (v0.3.1); durable DirectStorage checkpoints |

The RTX 3090 scout role stays deferred: v0.12.0 targets the RTX 3090 as a standalone native
lane, not as an unattended fleet role, so no scout fragment ships here. Its three-lane form and
the legacy OMP 18.0.9 instructions for that lane stay at the immutable v0.7.2 tag.

The current fragments target **v0.13.1 / OMP 18.12.6**.
The RTX 5090 profile uses `qwen38-5090-v0.13.0` (`751d22dc`), model container version 3 `81f924d4`,
and host directory `checkpoints-v013` mounted at `/checkpoints-v013` with mandatory
`--session-checkpoint-require-origin-auth` (carried unchanged from v0.13.0); prior server sessions
replay from OMP transcripts, never from the old checkpoint root. Native RTX 4090 uses
`v0.7.0-qwen38-4090-beta.2` (source `7a25cd72` on `64d10fbf`, profile
`qwen38-4090-native-v0.7.0-beta.2`, public config `b21cdaf8`), the same published model container
version 3 `81f924d4` (`qwen3_8_27b-v3.ninfer`), and release-isolated schema 3 checkpoint directory
`cache/<release-instance-id>/session-checkpoints-v3` (where `<release-instance-id>` is the installed release ID such as `qwen38-4090-native-v0.7.0-beta.2-7a25cd72f490`) with mandatory
`--session-checkpoint-require-origin-auth`. Enforced JSON-schema output and 128-character
Chat/Responses tool names are qualified on both the RTX 5090 container and rebased native lanes. No
multi-machine fleet completed-work qualification is claimed for v0.13.1; per-lane installation
eligibility follows the exact manifest ready gate. The release uses the
checksummed binary from the [quickstart](../../docs/QUICKSTART.md). Merge the installed lanes from `models.fragment.yml` into
`~/.omp/agent/models.yml`; it uses the exact server model ids, per-lane forwards, and key files.
`models.yml` and `provider-5090.json` / `provider-4090.json` are role and deployment metadata, not
OMP configuration. Fill their `<...>` placeholders from your own deployment. The exact package,
image digest, and receipt for every lane live in the current release manifest; install lanes only
from those pinned identities.

Each model in the current fragment sets `compat.statefulResponses: true`. Remove the old
`PI_OPENAI_STATEFUL` export from launch scripts and shell profiles, and unset it in the launching
shell; an inherited environment value still overrides per-model compatibility.

Stock OMP names each session with `prompt_cache_key`; with API authentication configured, the
server hashes that key into the session identity without storing the raw key, enabling automatic
checkpoints and restore. Per-model `compat.statefulResponses` chains turns with `previous_response_id`. The
fragment disables encrypted reasoning and reasoning summaries because the server refuses fields
it does not implement. Its thinking efforts match the template's `low`, `medium`, and `xhigh`
levels (`off` clamps to `low`, `high` to `medium`). Launch the lead with
`omp --model ninfer-main/q38-ninfer`; `agents/fleet-heavy.md` selects the RTX 4090 model.

Warm-start tip (all lanes): checkpoint a session right after your system prompt and repository
context have prefetched, then fork subagents from that generation — each fork starts hot instead
of re-prefilling. See the roadmap's template-fork warm-start item for the receipted pattern.
