# Incident Response (Production Readiness)

## Contacts (Placeholders)

- Abuse: abuse@siber.example
- Security: security@siber.example
- On-call: TBD

## Severity

| Level | Example | Response |
|-------|---------|----------|
| P1 | Unauthorized external scan | Kill switch all pilots, revoke domains |
| P2 | Credential leak | Rotate secrets, audit access |
| P3 | Worker outage | Restart workers, check readiness |
| P4 | Single tenant misconfig | Suspend tenant |

## Procedures

1. **Emergency shutdown** — Set global maintenance or disable pilot tenants (`scans_disabled`).
2. **Scanner IP list** — Document in `docs/pilot/scanner-ip-allowlist-guide.md`.
3. **Credential rotation** — `SECRET_KEY`, DB password, admin passwords.
4. **Evidence** — Preserve audit logs and scan records before remediation.

See also `docs/pilot/incident-response-checklist.md`.

## Data Breach

Follow legal notification requirements (EU: assess 72h GDPR timeline with counsel).
