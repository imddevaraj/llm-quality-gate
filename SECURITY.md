# Security Policy

## Reporting a vulnerability

Please do not open a public issue for a security vulnerability. Contact the repository maintainers privately with:

- A description of the vulnerability
- Affected files or endpoints
- Reproduction steps or proof of concept
- Potential impact
- Any suggested mitigation

Do not include live API keys, webhook URLs, personal data, or customer content in reports.

## Scope

Security-sensitive areas include secret handling, report redaction, webhook delivery, dataset path handling, provider requests, and API exposure. The MVP has no authentication and should not be exposed directly to an untrusted network.
