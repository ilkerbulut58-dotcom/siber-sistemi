# Rollback Procedure (Pilot)

1. **Stop traffic** — Set `scans_disabled=true` on all pilot tenants via platform API.
2. **Revert deployment** — Redeploy previous Docker image tag on worker/API hosts.
3. **Database** — If migration issue: `alembic downgrade -1` after backup (see migration runbook).
4. **Verify** — `/api/v1/health/ready` returns ready; smoke test login and read-only scan list.
5. **Communicate** — Notify pilot users of maintenance window.

Do not force-push main. Use feature branch revert or tagged image rollback.
