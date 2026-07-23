# Plan Guardrails

Billing is **not integrated**. Enforcement uses configuration and org fields:

| Guardrail | Implementation |
|-----------|----------------|
| Daily scan quota | `SCAN_DAILY_QUOTA` + org `pilot_scan_quota` override |
| Concurrency | `SCAN_CONCURRENCY_LIMIT` per org |
| Rate limits | Redis buckets (auth, scan, upload, retest) |
| Active scan | Domain `active_scan_allowed` + pilot `pilot_active_scan_allowed` |
| Profiles | Deep/Code blocked on production projects |

## Plan Model (Future)

`docs/database-schema.md` describes planned `subscriptions` table. Until implemented:

- **Free/dev**: `SKIP_DOMAIN_VERIFICATION=true` in development only
- **Pilot**: `is_pilot` org flag with dates and quota
- **Paid**: not enforced

Do not expose paid features without entitlement checks once billing ships.
