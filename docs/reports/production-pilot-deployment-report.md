# Production Pilot Deployment Report

Controlled production/pilot deployment to **siber.cloudnira.com** (trial domain, no real customer onboarding).

## Summary

| Field | Value |
|-------|-------|
| Domain | `https://siber.cloudnira.com` |
| Deploy date | 2026-07-23 12:47 UTC |
| Branch / commit deployed | `main` @ `a0c43cb` |
| Release tag | `v0.9.0-rc1` |
| Deploy method | `scripts/deploy-pilot-production.cjs` (SSH + Docker Compose) |
| CI reference | [30007191153](https://github.com/ilkerbulut58-dotcom/siber-sistemi/actions/runs/30007191153) |
| **Nihai karar** | **`production_pilot_deployment_passed`** |

## 1. Merge & Release

| Item | Status |
|------|--------|
| PR #5 | merged → `main` |
| Tag `v0.9.0-rc1` | pushed |
| Simulation seed on production | **not run** |

## 2. Server Architecture (verified via deploy)

| Component | Status |
|-----------|--------|
| Host | `87.106.10.169`, Docker 29.6.2, Compose 5.3.1 |
| App path | `/opt/siber` |
| Disk | 232G total, 20% used |
| Reverse proxy | Plesk Apache + nginx |
| API | `127.0.0.1:8010` — healthy |
| Frontend | `127.0.0.1:3011` — up |
| PostgreSQL | internal volume — healthy |
| Redis | internal — healthy |
| Worker | Celery + beat — up |
| ZAP | internal — healthy |
| Mobile worker | up |

## 3. Backup

| Item | Result |
|------|--------|
| Location | `/opt/siber/backups/20260723T124710Z/` |
| File | `siber-pre-deploy.dump` |
| Size | **328,723 bytes** (non-empty) |
| Pre-deploy SHA recorded | yes (`previous-deploy-sha.txt`) |
| Restore smoke on temp DB | **not run** (blocker documented; dump size verified) |

## 4. Production Environment

| Setting | Deployed value |
|---------|----------------|
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |
| `SKIP_DOMAIN_VERIFICATION` | **`false`** |
| `USE_CELERY_FOR_SCANS` | `true` |
| `CORS_ORIGINS` | `https://siber.cloudnira.com` |
| `SCAN_DAILY_QUOTA` | `5` |
| `SCAN_CONCURRENCY_LIMIT` | `1` |
| `RATE_LIMIT_ENABLED` | `true` |
| `NOTIFICATIONS_PROVIDER` | `noop` |

Existing secrets preserved from `/opt/siber/.env` (not rotated).

## 5. Migration

| | Revision |
|---|----------|
| Before | `012_target_site_profiles` |
| After | **`017_phase13_pilot_tenant` (head)** |
| Applied | `013` → `014` → `015` → `016` → `017` |
| Destructive ops | none |

Rollback: redeploy prior image + `alembic downgrade 015_benchmark_active_profiles` after backup restore if needed.

## 6. Deploy Outcome

Deploy completed with **`PILOT_PRODUCTION_DEPLOY_OK`**.

Post-deploy smoke (from deploy script):

- `GET /api/v1/health` → 200, `skip_domain_verification: false`
- `GET /api/v1/health/ready` → 200, database + redis ok
- Public HTTPS health/ready → 200

## 7. Post-Deploy Verification

| Test | Result |
|------|--------|
| HTTPS homepage | OK |
| Health | OK |
| Readiness | OK |
| Login (existing platform admin) | OK |
| Fake domain add (`*.example.com`) | **rejected** — DNS resolution required (expected) |
| Worker queue live test | **pending** — requires verified owned domain scan |
| Safe active scan on owned domain | **pending operator** |

Platform admin bootstrap via `.env` was skipped (no `INITIAL_PLATFORM_ADMIN_*` in env). Existing admin account remains usable for manual testing.

## 8. Manual Test Preparation

Operator next steps:

1. Log in as existing platform admin (credentials on server / operator vault — **not in this report**).
2. **Change weak default password** if still using legacy credentials.
3. Create 2–3 pilot orgs via platform admin (`is_pilot=true`, low quota).
4. Add and verify **owned trial domain** (DNS TXT or admin manual approve).
5. Run passive (`safe`) then safe active (`deep`) scan only — no full active (`code`).
6. Kill switch: `PATCH /api/v1/platform/pilot-tenants/{id}` → `scans_disabled: true`.
7. Cancel scan: `POST /api/v1/organizations/{org_id}/scans/{scan_id}/cancel`.

## 9. Rollback

```bash
# Application
cd /opt/siber && docker compose -f docker-compose.prod.yml up -d --build  # prior image/tag

# Database restore
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_restore -U siber -d siber --clean --if-exists \
  < /opt/siber/backups/20260723T124710Z/siber-pre-deploy.dump

# Schema rollback (only if app rolled back)
docker compose exec api alembic downgrade 015_benchmark_active_profiles
```

## 10. Remaining Gaps

1. Backup restore not tested on isolated DB.
2. Live scan + findings + report on **owned domain** not executed in this session.
3. Public self-registration still open in API — restrict operationally or via proxy during pilot.
4. Platform admin password rotation recommended before external manual testing.

## Nihai Karar

**`production_pilot_deployment_passed`**

Deploy, backup, migration 017, HTTPS, health/readiness, and domain verification enforcement are confirmed live. **`manual_production_pilot_testing_ready`** deferred until operator completes owned-domain scan validation and admin hardening.
