# OMP NInfer v0.2.0-beta.1

**RTX 5090 + 4090 qualified · RTX 3090 preview · invited-tester beta**

Not stable or GA. No production route is activated.

## What is qualified

- Native OMP 18.0.9 clients for macOS arm64, Windows x64, and Linux x64, with exact public source at [`alphastorm/oh-my-pi`](https://github.com/alphastorm/oh-my-pi/releases/tag/omp-v18.0.9-ninfer-beta.2).
- Manifest-driven `doctor`, `plan`, `install`, `status`, quick benchmark, checkpoint, rollback, and support-bundle adapters.
- Primary RTX 5090 runtime: digest-pinned BF16-KV/MTP3 image, 131,072-token context ceiling, 130,048-token exact retrieval, and 235.02 tok/s over 2,048 decode tokens.
- Native Windows RTX 4090 beta: exact MTP0 package, 15/15 protocol, 102,060 → 102,075 process-restart continuation, 1,410.691 prefill tok/s, 52.330 decode tok/s, exact source-controlled OMP Golden-equivalent, and full lifecycle/restoration evidence.

## RTX 3090 preview

The tagged RTX 3090 package is public and review-closed but **not installable or beta-qualified**. Current sm_86 response-store, session-checkpoint, and HTTP contract tests passed 3/3 on Windows and an ephemeral Community RTX 3090. The following current-package gates remain `not_run`:

- live authenticated model protocol;
- 64,512-token retrieval;
- process-restart continuation;
- bounded C1 performance;
- fresh exact Windows RTX 3090 install/security/bidirectional rollback; and
- exact OMP 18.0.9 acceptance.

Community live-model attempts returned provider `cudaErrorUnknown`; all owned pods were deleted and no passing claim is inferred. Historical package measurements are isolated and do not qualify the preview package.

## Evidence and safety

- [Manifest](manifest.json)
- [Product qualification](qualification.json)
- [Compatibility authority](compatibility.json)
- [Human-readable matrix](COMPATIBILITY.md)
- [Quickstart](https://github.com/alphastorm/omp-ninfer/blob/v0.2.0-beta.1/docs/QUICKSTART.md)
- [Security model](https://github.com/alphastorm/omp-ninfer/blob/v0.2.0-beta.1/docs/SECURITY.md)

The historical private Golden corpus was unavailable and was not reused, read, copied, hashed, or transmitted. Its RTX 4090 replacement is source-controlled and proves one typed tool call, exact primitive arguments, linked tool-result continuation, and an exact visible final answer.

Process-restart Responses continuation is qualified only for the native RTX 4090 variant. The primary RTX 5090 image uses restart policy `no`; OMP transcript replay remains its recovery path. Response DELETE is logical object deletion, not secure erasure of context required by surviving descendant continuation.

Structured JSON-schema output, multi-GPU, multi-tenant, priority, preemption, silent cloud fallback, and universal performance claims are excluded.
