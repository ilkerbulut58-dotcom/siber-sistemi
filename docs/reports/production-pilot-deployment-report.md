# Production Pilot Deployment Report

Controlled production/pilot deployment to the existing trial domain **without real customer onboarding**. This report records verifiable outcomes only; steps requiring operator SSH access are marked explicitly.

## Summary

| Field | Value |
|-------|-------|
| Domain | `https://siber.cloudnira.com` |
| Deploy date | 2026-07-23 (release prep completed; **live deploy pending operator SSH**) |
| Branch merged | `feat/phase-12-production-hardening` → `main` |
| Deploy target commit | `5831500` |
| Release tag | `v0.9.0-rc1` (annotated tag `e313fbb`) |
| PR | [#5](https://github.com/ilkerbulut58-dotcom/siber-sistemi/pull/5) — merged to `main` locally |
| Last green CI (simulation) | [30007191153](https://github.com/ilkerbulut58-dotcom/siber-sistemi/actions/runs/30007191153) |
| **Nihai karar** | **`production_pilot_deployment_partial`** |

## 1. Merge & Release (completed)

| Item | Status |
|------|--------|
| PR #5 merge conflicts | none (`mergeable_state: clean`) |
| CI on head `3120b69` | success (run 30007191153) |
| Merge to `main` | **done** — fast-forward to `5831500` |
| Tag `v0.9.0-rc1` | **created and pushed** |
| Simulation seed on production | **not run** (by design) |

Deploy commit includes pilot production script: `scripts/deploy-pilot-production.cjs` (`5831500`).

## 2. Existing Server Architecture (documented, not SSH-verified this session)

From repository deploy tooling and public probes:

| Component | Expected configuration |
|-----------|------------------------|
| OS | Linux (Ubuntu, Plesk host) |
| Server | `87.106.10.169` (`root` SSH) |
| App path | `/opt/siber` |
| Orchestration | Docker Compose (`docker-compose.prod.yml`) |
| Reverse proxy | Plesk Apache + nginx (`/var/www/vhosts/system/siber.cloudnira.com/conf/`) |
| SSL | HTTPS active on public domain |
| Backend | FastAPI @ `127.0.0.1:8010` |
| Frontend | Next.js @ `127.0.0.1:3011` |
| PostgreSQL | Docker volume `postgres_data` (internal) |
| Redis | Docker volume `redis_data` (internal) |
| Worker | Celery + beat (`siber-worker`) |
| Scanner | OWASP ZAP daemon (internal `zap:8080`) |
| Mobile worker | Isolated network profile |

**Public pre-deploy state (verified):**

- `GET /api/v1/health` → 200, `version: 0.1.0`, `environment: production`
- `GET /api/v1/health/ready` → 200, database + redis ok
- Homepage loads over HTTPS

This confirms the **previous** release is still live; phase 12–14 code is **not yet deployed** to the server.

## 3. Backup (not executed — blocker)

| Requirement | Status |
|-------------|--------|
| PostgreSQL full backup | **pending** — requires SSH |
| Upload/persistent file backup | **pending** |
| Backup non-empty verification | **pending** |
| Restore smoke test | **pending** |

**Blocker:** `DEPLOY_SSH_PASSWORD` is not available in the agent environment. Deploy script refuses to run without it.

Planned backup location (when deploy runs):

```
/opt/siber/backups/<UTC-timestamp>/siber-pre-deploy.dump
/opt/siber/backups/<UTC-timestamp>/alembic-pre.txt
/opt/siber/backups/<UTC-timestamp>/previous-deploy-sha.txt
```

## 4. Production Environment Checklist

Compared against `docs/secrets-inventory.md` and `deploy/production.env.example`:

| Variable / setting | Deploy script value | Notes |
|-------------------|---------------------|-------|
| `ENVIRONMENT` | `production` | |
| `DEBUG` | `false` | |
| `SECRET_KEY` | preserved from existing `.env` | not rotated automatically |
| `DATABASE_URL` | via compose | internal postgres only |
| `REDIS_URL` | via compose | internal redis only |
| `CORS_ORIGINS` | `https://siber.cloudnira.com` | no wildcard |
| `SKIP_DOMAIN_VERIFICATION` | `false` | enforced |
| `USE_CELERY_FOR_SCANS` | `true` | real worker queue |
| `RATE_LIMIT_ENABLED` | `true` | |
| `SCAN_DAILY_QUOTA` | `5` | low pilot quota |
| `SCAN_CONCURRENCY_LIMIT` | `1` | |
| `NOTIFICATIONS_PROVIDER` | `noop` | no real email |
| `ZAP_ENABLED` | `true` | internal only |

**Gap:** Public self-registration (`POST /api/v1/auth/register`) remains enabled in code. Operational mitigation until a config flag exists:

- Do not publish registration URL during manual pilot
- Optionally block `/api/v1/auth/register` at reverse proxy during pilot
- Use platform admin + member invite for test tenants

## 5. Production Security Settings

| Control | Code/deploy support | Live status |
|---------|---------------------|-------------|
| Domain verification required | yes (`SKIP_DOMAIN_VERIFICATION=false`) | after deploy |
| Active scan admin approval | yes (migration 016) | after deploy |
| Safe active (`deep`) available | yes | after deploy |
| Full active (`code`) gated | yes (domain + project env) | after deploy |
| Low quota / concurrency | yes (env) | after deploy |
| Kill switch (`scans_disabled`) | yes (migration 017) | after deploy |
| SSRF / private IP block | yes (`url_guard`) | after deploy |
| Scanner not public | yes (ZAP internal network) | expected |
| Postgres/Redis not public | yes (no host ports) | expected |

## 6. Database Migration Plan

| Item | Value |
|------|-------|
| Head revision (target) | `017_phase13_pilot_tenant` |
| Pending from typical pre-phase-12 | `016_phase12_domain_scan_auth`, `017_phase13_pilot_tenant` |
| Destructive ops | **none** — additive columns only |
| Rollback command | `alembic downgrade 015_benchmark_active_profiles` (after backup + app rollback) |

Migration runs **only after** successful backup inside `deploy-pilot-production.cjs`.

## 7. Deploy (not executed)

**Operator command** (from repo root, Windows PowerShell):

```powershell
$env:DEPLOY_SSH_PASSWORD = "<operator-secret>"
$env:DEPLOY_CONFIRM = "production-pilot"
git checkout main
git pull
node scripts/deploy-pilot-production.cjs
```

The script will: backup → extract release → preserve secrets → build/start containers → migrate → proxy reload → smoke tests.

## 8–12. Post-Deploy Tests (not executed)

All items below require successful deploy first:

| Test | Status |
|------|--------|
| HTTPS / HTTP→HTTPS | pre-deploy homepage OK; post-deploy **pending** |
| Health / readiness | pre-deploy OK (v0.1.0); post-deploy **pending** |
| Login / authz | **pending** |
| Worker queue | **pending** |
| Safe scan on owned domain | **pending** |
| Findings + report | **pending** |
| Quota / kill switch | **pending** |
| Tenant isolation | **pending** |
| Log secret scan | **pending** |

## 13. Rollback Method (documented)

1. **Application rollback:** redeploy previous image/build from backup tag or prior archive; or `git checkout <previous-sha>` + `deploy-pilot-production.cjs` only after review.
2. **Database restore:**
   ```bash
   cd /opt/siber
   docker compose -f docker-compose.prod.yml exec -T postgres \
     pg_restore -U siber -d siber --clean --if-exists \
     < /opt/siber/backups/<timestamp>/siber-pre-deploy.dump
   ```
3. **Schema rollback (if needed):** `docker compose exec api alembic downgrade 015_benchmark_active_profiles`
4. **Proxy:** Plesk vhost configs preserved; reload nginx/apache after container port rollback.

Rollback commands were **not executed** against live data.

## 14. Manual Test Preparation (after deploy)

Operator actions post-deploy:

1. Ensure `INITIAL_PLATFORM_ADMIN_EMAIL` and `INITIAL_PLATFORM_ADMIN_PASSWORD` are set in `/opt/siber/.env` (strong unique password — **not** simulation defaults).
2. Run `docker compose exec api python scripts/create_admin.py` if admin not bootstrapped.
3. Log in at `https://siber.cloudnira.com/login` — change password on first use if policy added later.
4. Create 2–3 empty pilot orgs via platform admin (`is_pilot=true`, low `pilot_scan_quota`).
5. Document kill switch: `PATCH /api/v1/platform/pilot-tenants/{id}` with `scans_disabled: true`.
6. Document scan cancel: `POST /api/v1/organizations/{org_id}/scans/{scan_id}/cancel`.

**Credentials are not recorded in this report.**

## Changed Files (this deployment prep)

- `scripts/deploy-pilot-production.cjs` — backup-first pilot deploy
- `docker-compose.prod.yml` — scan quota env passthrough
- `deploy/production.env.example` — pilot production defaults
- `README.md` — deploy instructions corrected

## Remaining Gaps

1. **SSH deploy not run** — `DEPLOY_SSH_PASSWORD` unavailable to agent.
2. **Backup/restore not verified** on server.
3. **Migrations 016–017 not applied** on production DB yet.
4. **Live version still `0.1.0`** — phase 12–14 code not on server.
5. **Public registration** — no env flag; use operational/proxy restriction.
6. **PR #5** — may need manual close on GitHub UI if not auto-closed after push.

## Nihai Karar

**`production_pilot_deployment_partial`**

Release engineering completed (merge, tag, deploy script, config). Live production pilot deployment and validation **cannot** be marked passed or `manual_production_pilot_testing_ready` until the operator runs `deploy-pilot-production.cjs` with SSH credentials and post-deploy tests succeed.
