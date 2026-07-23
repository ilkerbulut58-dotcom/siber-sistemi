# Abuse Handling Guide

## Signals

- Scan quota exceeded repeatedly
- Failed authorization (unverified domain)
- SSRF / blocked target attempts
- Platform admin `scans_disabled` flag

## Response

1. Review audit logs for `scan.started`, `scan.failed`, failed auth events.
2. Suspend pilot tenant via `PATCH /api/v1/platform/pilot-tenants/{id}` with `scans_disabled: true`.
3. Revoke domain active scan approval if needed.
4. Document incident in pilot notes field.

## Escalation

See `docs/pilot/incident-response-checklist.md`.
