# Security Policy

## Reporting a vulnerability

SAKSHYA handles forensic evidence, so security reports are taken seriously.

**Please do not open a public issue for security vulnerabilities.** Instead,
report privately via [GitHub Security Advisories](https://github.com/sayaksatpathi/SAKSHYA/security/advisories/new)
(preferred), or contact the maintainer directly.

When reporting, please include:

- A description of the vulnerability and its impact
- Steps to reproduce (proof-of-concept if possible)
- Affected component/version and any suggested remediation

You can expect an acknowledgement, and we will keep you updated as the issue is
investigated and resolved. Please allow reasonable time for a fix before any
public disclosure.

## Scope & design

The platform's threat model, trust boundaries, and cryptographic design are
documented in **[docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md)**, with the
open risk items tracked in **[docs/RISK_REGISTER.md](docs/RISK_REGISTER.md)**.

### Known limitations (see the README for the full list)

- **No per-user case isolation (IDOR):** all `investigator`-role users can
  currently access all cases. Multi-tenant isolation is on the roadmap.
- The **BSA §63(4) certificate is an unsigned draft** — it must be reviewed and
  authenticated by a responsible person; SAKSHYA does not determine legal
  admissibility.

## Operational guidance

- Always set `SAKSHYA_SECRET_KEY` (and any credentials) via environment
  variables — never rely on the hardcoded development default.
- Run behind TLS and restrict network exposure of the API and Trust service in
  any real deployment.
