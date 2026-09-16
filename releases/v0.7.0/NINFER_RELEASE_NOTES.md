# OMP NInfer v0.7.0 - two long sessions keep their reuse

The RTX 5090 serving configuration advances so two sessions at the 131,072-token ceiling keep
their prefix reuse on one card. No component, image, model, or client changed; the configuration
identity did, and the runtime host now needs more memory than before.

## Exact components

Unchanged from `v0.6.10`:

- Runtime source, frozen and independently reviewed:
  `696e78c7b4e3ac28ffcffafc73acc1496e65ef03`.
- RTX 5090 component: `v0.6.5-qwen38-5090-beta.1`, image
  `sha256:5e3e15581cb44a2dff5e1be0c64cad206f3048e9f01c98b04ef13f61195a9bb8`, server binary
  `b8a0a2c33d79304afb1701ca7d179a6ed750685d1365a75634fdc738bab6a831`.
- RTX 4090 native component: `v0.6.3-qwen38-4090-beta.1`. RTX 3090 component unchanged.
- Model artifact `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`; pinned OMP
  client `omp-18.0.9-cross-platform-beta-2`.

New serving configuration: deployment profile `qwen38-5090-v0.7.0`, Host KV pool 16 GiB
(was 8 GiB), KV dtype unchanged at `bf16`.

## What changed

Alternating between two long sessions used to cost a full re-prefill every turn. A 126K-token
session's bf16 KV is about 4.2 GB and the shipped pool was 8 GiB, so each session evicted the
other's endpoint and every continuation came back from root in about 58 s. With a 16 GiB pool the
same workload loses nothing: 0 of 8 continuations and forks, each reusing about 125,900 cached
tokens in 1.6-3.5 s. Entering that steady state from a pool another long session already occupies
costs one re-prefill per session, once.

The pool is pinned runtime-host memory, so this is also a host requirement:

- the profile declares `runtime_host.minimum_runtime_memory_mib` 28,672;
- `examples/manual-tunnel/start-ninfer.sh` compares it with the memory a throwaway container sees
  and refuses before loading the artifact, naming the `.wslconfig` remedy;
- the refusal exists because the alternative is a kill, not a slowdown: the same configuration in
  a 24 GiB WSL utility VM reached 24,006 MiB and was OOM-killed mid-request (exit 137);
- a host that cannot give the container that memory runs `v0.6.10`, whose 8 GiB pool holds one
  session at the ceiling and two of about 75,000 tokens.

Because the configuration identity changes, checkpoints written under `v0.6.10` do not carry
across, exactly as the `v0.4.8` profile advance recorded.

## Why the KV dtype did not change

Both 8-bit KV dtypes fix the same reuse loss - fp8 holds two long sessions even in the old 8 GiB
pool and halves device KV - and both were rejected on quality, re-scored on one runtime against
the private role corpus (89 deterministic cases): fp8 and int8 each drop the redaction control
pass rate from 0.750 to 0.625 and add a secret leak, fp8 loses 2.1 points of required fact recall,
and int8 loses 1.7 while adding unsupported claims and critical misses. Throughput is within
noise. Capacity bought with redaction is not a trade this product makes.

## Qualification

Lane gates re-measured on this configuration
([receipt](../../docs/measurements/2026-09-16-rtx5090-v070-profile-gates.json)):

- exact 130,048-token retrieval at **2,203.0 tok/s** prefill, 2,048-token decode at
  **133.03 tok/s** wall, VRAM 28,144 MiB;
- the agent protocol across a restart, including a live sibling continuation answering 200 and no
  resurrection after a delete;
- four hot sibling forks at 67.7K and 80.0K templates before and after a restart (1.64-2.03 s);
- warm arrival in both orders, every post-restart fork hot;
- a 4.51 GB checkpoint restored in 3.5-3.7 s with exact retrieval;
- two 126K sessions keeping reuse, and both sessions checkpointing at 9.24 GB each.

## Known boundary: what survives a restart

Durability is narrower than reuse, and this release states the boundary rather than implying it.
With two sessions at the ceiling, both checkpoint and a graceful stop saves both
(`shutdown: saved 2, nothing to save 0, refused 0`). After the restart one of the two is accepted
back and the other is declined - `the engine did not accept the checkpointed continuation` - so it
re-prefills from its transcript. A declined checkpoint is refused, not corrupted, and the store is
untouched. Sessions below the ceiling are unaffected. On the RTX 4090 native lane the same
workload is worse and unchanged by this release: its 4 GiB pool loses every continuation, the
server refuses automatic checkpoints while both sessions are live, and a managed stop saved one
and lost the other. Both follow-ups are named in the roadmap.

## Support boundaries

Unchanged: prerelease support only with no SLA; one owner-operated machine per lane; one active
request per qualified profile; JSON-schema structured output rejected rather than ignored; no
multi-GPU, multi-tenant, priority, or preemptive scheduling claim; no universal throughput,
latency, or hardware claim; no silent cloud fallback; measured numbers apply only to the recorded
package, machine, and profile.
