# Incident Response Checklist (Pilot)

1. **Detect** — Monitoring alert, customer report, or audit log review.
2. **Contain** — Set `scans_disabled` on affected pilot tenant; cancel running scans.
3. **Investigate** — Preserve audit logs; check scan targets and authorization records.
4. **Remediate** — Revoke credentials if compromised; patch misconfiguration.
5. **Notify** — Internal stakeholders; customer if their data affected (legal review required).
6. **Review** — Post-incident notes in pilot tenant record.

Severity levels: P1 unauthorized external scan, P2 data exposure, P3 availability, P4 minor misconfiguration.

Contact placeholders: `security@siber.example`, on-call rotation TBD.
