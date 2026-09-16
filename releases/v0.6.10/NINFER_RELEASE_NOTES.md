# OMP NInfer v0.6.10 - the documented route refuses a launch the engine cannot stage

No component, model, client, or serving configuration changed. Both RTX 5090 documented routes
were re-run against the unchanged published image: host 2/2 blocks and macOS 10/10 blocks
([composed receipt](acceptance/composed-external-installation.json),
[routes](acceptance/documented-routes.json)).

## Exact components

Unchanged from `v0.6.9`:

- Runtime source, frozen and independently reviewed:
  `696e78c7b4e3ac28ffcffafc73acc1496e65ef03`.
- RTX 5090 component: `v0.6.5-qwen38-5090-beta.1`, image
  `sha256:5e3e15581cb44a2dff5e1be0c64cad206f3048e9f01c98b04ef13f61195a9bb8`, server binary
  `b8a0a2c33d79304afb1701ca7d179a6ed750685d1365a75634fdc738bab6a831`.
- RTX 4090 native component: `v0.6.3-qwen38-4090-beta.1`. RTX 3090 component unchanged.
- Model artifact `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`; pinned OMP
  client `omp-18.0.9-cross-platform-beta-2`.

## What changed

A machine reboot does not return either route by itself, and one of the two ways that fails is
silent. Docker Desktop stages a container's bind mounts once, when the container is created, from
the filesystem those paths live on. After that filesystem's WSL distro restarts - which every
reboot does - a container created against the old staging either refuses to start (`not a
directory` against the staging placeholder, recorded as exit `127` with `RestartCount 0`, which no
restart policy retries) or starts with **empty** file mounts, whereupon the server rejects its own
empty `--api-key`, prints usage text, and exits `1`; a restart policy then loops on it.

- `examples/manual-tunnel/start-ninfer.sh` proves the route's mounts inside a throwaway container
  before loading the 18 GB artifact: the model byte count seen inside the container must equal the
  host's, the key file must be non-empty, and the store must be a directory. It refuses with what
  that container saw and how to repair the engine, instead of leaving either shape running.
- `docs/TROUBLESHOOTING.md` names both signatures and states that recovery here is recreation -
  `stop-ninfer.sh`, then the same `start-ninfer.sh` - which the durable store makes a
  continuation rather than a loss.
- `docs/QUICKSTART.md` says plainly that the container route does not return by itself after a
  machine reboot, alongside the native route's existing statement.

Evidence for the class this came from, including the owner appliance's 26 h 51 min outage, four
authorised reboots recovering unattended, and the first receipt of the native lane's documented
post-reboot start with its checkpointed session resuming exactly:
[EXP-040](../../docs/measurements/2026-09-16-lane-reboot-survivability.json).

## Support boundaries

Unchanged: prerelease support only with no SLA; one owner-operated machine per lane; one active
request per qualified profile; JSON-schema structured output rejected rather than ignored; no
multi-GPU, multi-tenant, priority, or preemptive scheduling claim; no universal throughput,
latency, or hardware claim; no silent cloud fallback; measured numbers apply only to the recorded
package, machine, and profile.
