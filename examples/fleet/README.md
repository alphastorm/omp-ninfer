# Fleet: two model-bound agents, one per qualified lane

Run up to two concurrent OMP agents, each statically pinned to one qualified NInfer lane. Every
endpoint stays loopback-only on its own machine; reach remote lanes through authenticated SSH
local forwards (the managed route), never by exposing a listener.

| Role | Lane | OMP model | Notes |
| --- | --- | --- | --- |
| `main` | RTX 5090 container | `ninfer-main/q38-ninfer` | 131,072-token ceiling; durable checkpoints as of v0.4.0 |
| `heavy` | RTX 4090 native Windows | `ninfer-heavy/qwen3.8-27b` | MTP3 profile (v0.3.1); durable DirectStorage checkpoints |

The RTX 3090 scout role stays deferred: v0.10.0 targets the RTX 3090 as a standalone native
lane, not as an unattended fleet role, so no scout fragment ships here. Its three-lane form and
the legacy OMP 18.0.9 instructions for that lane stay at the immutable v0.7.2 tag.

The current fragments target **unreleased candidate OMP 18.8.7**; GPU-host and documented-route
requalification are pending. No fresh fleet qualification is claimed. For a qualified install,
use the immutable v0.10.0 guide and fragments. The candidate uses the checksummed binary from the
[quickstart](../../docs/QUICKSTART.md). Merge the installed lanes from `models.fragment.yml` into
`~/.omp/agent/models.yml`; it uses the exact server model ids, per-lane forwards, and key files.
`models.yml` and `provider-5090.json` / `provider-4090.json` are role and deployment metadata, not
OMP configuration. Fill their `<...>` placeholders from your own deployment. The exact package,
image digest, and receipt for every lane live in the current release manifest; install lanes only
from those pinned identities.

Each model in the candidate fragment sets `compat.statefulResponses: true`. Remove the old
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
