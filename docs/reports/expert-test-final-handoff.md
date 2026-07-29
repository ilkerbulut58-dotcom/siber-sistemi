# Expert Test Final Handoff

**Handoff date:** 2026-07-29  
**Final verdict:** `expert_security_test_ready`

---

## Summary

SIBER is deployed at **`v0.9.0-rc5-expert`** (`db57d3f`) with **0% customer-visible benchmark variance**, **aligned production/CI SHA**, and **blind validation complete**. Expert may begin after operator provisions tenant and fills RoE placeholders.

---

## Production

| Item | Value |
|------|-------|
| Domain | https://siber.cloudnira.com |
| Previous commit | `ac36b16` (`v0.9.0-rc3-expert`) |
| **Final commit** | **`db57d3f`** |
| **Release tag** | **`v0.9.0-rc5-expert`** |
| Worker health | **healthy** |
| Registration | closed (403) |

---

## Benchmark evidence (run [30465738199](https://github.com/ilkerbulut58-dotcom/siber-sistemi/actions/runs/30465738199))

| Benchmark | Head SHA | Result |
|-----------|----------|--------|
| determinism 5× | `db57d3f` | TP=5, FP=0, FN=0, CV=3×5 stable, variance **0%** |
| API repeat 5× | `db57d3f` | TP=4, FP=0, FN=0, P/R=1.0, variance **0%** |
| blind | `db57d3f` | completed, TP=2, FP=0, FN=0, P/R=1.0 |

**Artifacts:** `benchmark-determinism-reports`, `benchmark-api-active-repeat-reports`, `benchmark-blind-reports`  
**Local path:** `benchmarks/ci-evidence/run-30465738199/`

---

## Operator actions before expert start

1. Fill RoE placeholders in `docs/security/expert-test-rules-of-engagement.md`
2. Create expert tenant when email is known:

```bash
python backend/scripts/prepare_expert_test_tenant.py \
  --email EXPERT@EXAMPLE.COM \
  --display-name "Expert Name" \
  --operator operator@company.com \
  --start-date 2026-08-01 \
  --end-date 2026-08-31 \
  --confirm EXPERT_TENANT_CREATE
```

3. Send credentials via secure channel — **not** platform_admin

---

## Emergency stop

1. Tenant `scans_disabled=true`  
2. Cancel running scans  
3. `docker compose -f /opt/siber/docker-compose.prod.yml stop worker`  
4. Revoke domain verification + disable expert account  

---

## Documents

- RoE: `docs/security/expert-test-rules-of-engagement.md`  
- Audit: `docs/reports/expert-security-test-readiness-audit.md`  

---

## Resolved blockers

1. ~~Web customer-visible variance 125%~~ → **0%** (deterministic site-wide header publication)  
2. ~~Blind benchmark SHA mismatch~~ → blind runs on same `db57d3f` as production  
