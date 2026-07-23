# Data Retention

| Data | Retention | Mechanism |
|------|-----------|-----------|
| Scan findings | Until org deletion | PostgreSQL |
| Scan jobs / audit | Immutable logs | PostgreSQL |
| APK uploads | Deleted after analysis | `mobile_service` immediate delete |
| Reports | Generated on demand | No long-term object store default |
| Benchmark artifacts | CI artifacts (~90 days) | GitHub Actions |

## Account Deletion

Organization soft-delete sets `is_active=false`. Hard delete workflow TBD for production.

## GDPR / EU Notes (Technical)

- Document lawful basis and DPA before production (legal review).
- Support data export via API/report download.
- Account deletion should cascade tenant data (implementation TBD).

## Logs

Structured JSON logs; avoid secrets and PII in log fields.
