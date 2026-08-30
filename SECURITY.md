# Security policy

## Supported versions

For the 0.x series, only the latest published OMP NInfer release and its exact manifest/profile
receive security fixes. Older releases, draft manifests, and development branches are unsupported
deployments.

| Version | Supported |
| --- | --- |
| latest published `0.3.x` release | yes |
| older releases | no |
| `main` / draft manifests | no |

## Report privately

Use [GitHub private vulnerability reporting](https://github.com/alphastorm/omp-ninfer/security/advisories/new).
Do not open a public issue for a suspected vulnerability.

Include the affected product release/profile, component identity, impact, minimum reproduction, and
whether the report concerns OMP integration, NInfer, the model artifact, Homebrew packaging, or the
SSH topology. Remove API keys, credentials, private prompts/output, usernames, hostnames, IP
addresses, private paths, raw logs, and third-party data. Do not test against systems you do not own
or have explicit permission to assess.

A report is in scope when it can violate an advertised boundary such as loopback-only exposure,
release artifact integrity, bearer-key handling, fail-closed local routing, transcript/provider-state
publication ordering, or support-data redaction. The public release does not claim protection from
root or local administrators on either user-controlled machine, multi-tenant isolation, or public-Internet
service.

We will acknowledge and disposition reports through the private advisory. Public disclosure and any
credit are coordinated there after a fix or explicit decision.
