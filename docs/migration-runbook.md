# Migration Runbook

## Before Deploy

1. Backup PostgreSQL (`pg_dump`).
2. Note current revision: `alembic current`.

## Apply

```bash
docker compose exec api alembic upgrade head
```

## Verify

- `/api/v1/health/ready` returns 200
- Smoke login and list organizations

## Rollback

1. Redeploy previous application image.
2. If schema incompatible: `alembic downgrade -1` **only** after backup and compatibility review.

Latest migrations: `016_phase12_domain_scan_auth`, `017_phase13_pilot_tenant`.

Never edit applied migration files.
