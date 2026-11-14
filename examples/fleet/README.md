# Fleet: two model-bound agents, one per qualified lane

Oh My Pi (coding-agent client) → OMP NInfer (qualified appliance and release layer) → NInfer
(inference engine) → Qwen3.8 27B (served model).

Run up to two concurrent Oh My Pi (OMP) agents from one POSIX client, each pinned to one NInfer
lane. Every endpoint stays loopback-only on its own machine; the client reaches each lane through
an authenticated SSH local forward, never an exposed listener.

This two-lane recipe is not qualified on the current release: the quickstart keeps it as a
[legacy configuration](../../docs/QUICKSTART.md#fleet-legacy-multi-lane-configuration). Install
and verify each lane on its own first, from the [quickstart](../../docs/QUICKSTART.md) and the
[current release](../../docs/FACTS.md#current-release).

## Roles

| Role | Lane | OMP model | Scope |
| --- | --- | --- | --- |
| `main` | RTX 5090 container | `ninfer-main/q38-ninfer` | Interactive lead session (131,072-token context, text, vision, tools, two requests in flight) |
| `heavy` | RTX 4090 native Windows | `ninfer-heavy/qwen3.8-27b` | Long-context background worker (131,072-token context, text and tools, one request at a time) |

## Files

- `open-tunnels.sh`: opens SSH local forwards (`ExitOnForwardFailure=yes`; `-` skips a lane).
- `models.fragment.yml`: Oh My Pi provider configuration for `~/.omp/agent/models.yml`.
- `agents/fleet-heavy.md`: Oh My Pi worker agent prompt (`ninfer-heavy/qwen3.8-27b:medium`).
- `models.yml`: role-to-lane metadata (`main` and `heavy`), not Oh My Pi configuration.
- `provider-5090.json`: RTX 5090 metadata with `<...>` placeholders, not Oh My Pi configuration.
- `provider-4090.json`: RTX 4090 metadata with `<...>` placeholders, not Oh My Pi configuration.

## Wire it

1. Run `examples/fleet/open-tunnels.sh` in its own shell
   (`open-tunnels.sh user@main-host|- user@heavy-host|-`). It forwards local `127.0.0.1:18191` to
   remote `127.0.0.1:18088` for the RTX 5090 lane and local `127.0.0.1:18192` to remote
   `127.0.0.1:18082` for the RTX 4090 lane. The quickstart's RTX 5090 container publishes `18089`,
   not `18088`. Against that install, pass `-` as the first argument and open the forward yourself:
   `ssh -NT -o ExitOnForwardFailure=yes -L 127.0.0.1:18191:127.0.0.1:18089 user@main-host`.
2. Place mode `600` bearer keys where `models.fragment.yml` reads them via `!cat`
   ([provider setup](../../docs/QUICKSTART.md#7-add-the-omp-provider)):
   `$HOME/.omp/agent/ninfer-5090.key` (`ninfer-main`) and
   `$HOME/.omp/agent/ninfer-4090.key` (`ninfer-heavy`).
3. Merge the `providers` entries from `models.fragment.yml` into `~/.omp/agent/models.yml` without
   overwriting existing providers.
4. Merge [`examples/manual-tunnel/fail-closed.yml`](../manual-tunnel/fail-closed.yml) into
   `~/.omp/agent/config.yml` to keep `providers.maxInFlightRequests` (`ninfer-main: 2`,
   `ninfer-heavy: 1`) and fail-closed settings.
5. Run `unset PI_OPENAI_STATEFUL` and launch the lead with `omp --model ninfer-main/q38-ninfer`;
   `agents/fleet-heavy.md` selects the RTX 4090 model (`ninfer-heavy/qwen3.8-27b:medium`).

## Stateful sessions

- Each model in `models.fragment.yml` sets `compat.statefulResponses: true` to chain turns via
  `previous_response_id`. Remove `PI_OPENAI_STATEFUL` exports from launch scripts and shell
  profiles and unset `PI_OPENAI_STATEFUL` in the launching shell so an environment value cannot
  override per-model compatibility.
- Stock OMP names each session with `prompt_cache_key`; under bearer authentication, the server
  hashes that key into the session identity without storing the raw key, enabling automatic
  checkpoints and restore.
- The fragment disables encrypted reasoning and reasoning summaries (`includeEncryptedReasoning: false`,
  `supportsReasoningSummary: false`) because NInfer rejects unimplemented fields, and maps thinking
  efforts to `low`, `medium`, and `xhigh` (`off` clamps to `low`, `high` to `medium`).

## Limits

- No RTX 3090 role or provider fragment ships here; the RTX 3090 is qualified only as a standalone
  native Windows lane.
- No multi-machine completed-work qualification is claimed; per-lane installation eligibility
  follows the release manifest's `ready` gate, and listeners remain loopback-only behind SSH.
- Warm-start tip: checkpoint a session right after your system prompt and repository context
  finish prefilling, then fork subagents from that generation so each fork can reuse the shared
  prefix. How much a fork reuses depends on the lane and is not guaranteed; the measured pattern
  is the template-fork entry in the [ideas backlog](../../docs/PERFORMANCE.md#ideas-backlog).

Community project; not affiliated with or endorsed by Oh My Pi, Qwen, or NVIDIA.
