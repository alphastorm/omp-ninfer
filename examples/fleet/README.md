# Fleet: three model-bound agents, one per qualified lane

Run up to three concurrent OMP agents, each statically pinned to one qualified NInfer lane. Every
endpoint stays loopback-only on its own machine; reach remote lanes through authenticated SSH
local forwards (the managed route), never by exposing a listener.

| Role | Lane | Fragment | Notes |
| --- | --- | --- | --- |
| `main` | RTX 5090 container | `provider-5090.json` | 131,072-token ceiling; durable checkpoints as of v0.4.0 |
| `heavy` | RTX 4090 native Windows | `provider-4090.json` | MTP3 profile (v0.3.1); durable DirectStorage checkpoints |
| `scout` | RTX 3090 native Windows | `provider-3090.json` | 64K-class working context is the comfortable envelope on this lane |

`models.yml` maps the roles for an OMP agent configuration. Fill each fragment's `<...>`
placeholders from your own deployment: the local forward port for that lane and the path to that
lane's api-key file. The exact package, image digest, and receipt for every lane live in the
current release manifest; install lanes only from those pinned identities.

Warm-start tip (all lanes): checkpoint a session right after your system prompt and repository
context have prefetched, then fork subagents from that generation — each fork starts hot instead
of re-prefilling. See the roadmap's template-fork warm-start item for the receipted pattern.
