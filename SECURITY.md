# Security Policy

## Reporting a vulnerability

Do not open a public issue for a security vulnerability. Report it privately to the repository maintainer through the security contact listed on the GitHub repository, including:

- a description of the issue and affected commit;
- reproduction steps or a minimal proof of concept;
- impact, including whether secrets or external state can be affected;
- any suggested mitigation.

Please do not include API keys, passwords, payment data, verification codes, or other live credentials in a report.

## Security model

TypeSafe Jev Gate is an experimental advisory and fail-closed policy layer. Hermes hardline blocks, normal authorization, and interactive approval remain authoritative. Jev outages, malformed responses, and uncertainty must not turn into an autonomous allow decision.

Before reporting an issue, users can disable network decisions with:

```text
HERMES_JEV_DISABLED=1
```
