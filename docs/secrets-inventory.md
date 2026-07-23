# Secrets Inventory

| Variable | Required | Environment | Notes |
|----------|----------|-------------|-------|
| `SECRET_KEY` | Yes | all | JWT signing |
| `POSTGRES_PASSWORD` | Yes | prod/staging | Database |
| `DATABASE_URL` | Yes | all | Async PG URL |
| `REDIS_URL` | Yes | prod/staging | Rate limits, Celery |
| `INITIAL_PLATFORM_ADMIN_*` | Bootstrap | prod | First admin only |
| `OPENAI_API_KEY` | Optional | prod | AI enrichment |
| `BLIND_GROUND_TRUTH_SECRET` | CI only | GitHub secret | Blind benchmark |
| `DEPLOY_SSH_PASSWORD` | Deploy | operator | deploy-full.cjs |
| SMTP_* | Future | prod | Not wired |
| STRIPE_* | Future | prod | Billing not integrated |

Store in environment variables or secret manager; never commit `.env` with real values.

Rotation: rotate `SECRET_KEY` invalidates sessions; plan maintenance window.
