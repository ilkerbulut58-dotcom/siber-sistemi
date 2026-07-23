# Production Runbook

## Prerequisites

- Docker and Docker Compose on target host
- PostgreSQL and Redis (via compose)
- Secrets from `deploy/production.env.example`

## Deploy

1. Copy `deploy/production.env.example` to `.env` on server and fill secrets.
2. Run `node scripts/deploy-full.cjs` or manual:
   ```bash
   docker compose -f docker-compose.prod.yml build
   docker compose -f docker-compose.prod.yml up -d
   docker compose exec api alembic upgrade head
   ```
3. Verify:
   ```bash
   curl -sf https://<host>/api/v1/health
   curl -sf https://<host>/api/v1/health/ready
   ```

## Rollback

See `docs/pilot/rollback-procedure.md` and `docs/migration-runbook.md`.

## Staging

Use `deploy/staging.env.example` with same compose file; separate database and CORS origins.

## Worker / Queue

- Celery worker + beat in `docker-compose.prod.yml`
- Mobile worker on isolated network profile

## Health Checks

- Liveness: `/api/v1/health/live`
- Readiness: `/api/v1/health/ready` (503 when DB/Redis down)

No automated production deploy from CI in this release.
