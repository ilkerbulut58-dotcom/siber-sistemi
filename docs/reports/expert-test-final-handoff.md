# Expert Test Final Handoff

**Handoff date:** 2026-07-29  
**Final verdict:** `expert_security_test_ready_with_blockers`

---

## Summary

SIBER closed pilot is deployed at **`v0.9.0-rc3-expert`** (`ac36b16`), workers healthy, and GitHub Actions benchmark evidence collected. Expert may begin **after operator provisions tenant**; acknowledge determinism customer-visible variance and blind SHA shim documented below.

---

## Production

| Item | Value |
|------|-------|
| Domain | https://siber.cloudnira.com |
| Final commit | `ac36b16` |
| Release tag | `v0.9.0-rc3-expert` |
| Version | `0.9.0-rc3-expert` |
| Registration | closed (403) |
| Domain verification | required |
| Worker health | **healthy** |

**No redeploy required** for documentation-only updates after `ac36b16`.

---

## GitHub benchmark evidence (Cursor-dispatched)

| Benchmark | Run ID | Head SHA | Ref | Artifact | Result |
|-----------|--------|----------|-----|----------|--------|
| determinism 5× | [30461802176](https://github.com/ilkerbulut58-dotcom/siber-sistemi/actions/runs/30461802176) | **`ac36b16`** | `v0.9.0-rc3-expert` | `benchmark-determinism-reports` | raw metrics PASS; **CV variance FAIL (125%)** |
| API repeat 5× | [30461802176](https://github.com/ilkerbulut58-dotcom/siber-sistemi/actions/runs/30461802176) | **`ac36b16`** | `v0.9.0-rc3-expert` | `benchmark-api-active-repeat-reports` | **PASS** |
| blind | [30462666435](https://github.com/ilkerbulut58-dotcom/siber-sistemi/actions/runs/30462666435) | `0d8256a`* | `expert/benchmark-ac36b16` | `benchmark-blind-reports` | metrics PASS; SHA caveat |
| CI regression | [30462639867](https://github.com/ilkerbulut58-dotcom/siber-sistemi/actions/runs/30462639867) | `2a6adbf` | `main` push | multiple | success |

\* `0d8256a` = `ac36b16` + ruff `__all__` re-export + blind `workflow_dispatch` CI fix (no logic change). Blind could not run on exact `ac36b16` due to backend lint failure.

Local evidence path: `benchmarks/ci-evidence/run-30461802176/`, `benchmarks/ci-evidence/run-30462666435/`

---

## Key metrics

**Web (ac36b16):** TP=5 all runs, FP=0, FN=0, raw P/R=1.0; customer-visible counts 1,0,1,1,1 (variance 125%).  
**API (ac36b16):** TP=4 all runs, FP=0, FN=0, P/R=1.0, CV stable.  
**Blind (0d8256a):** status=completed, TP=2, confirmed FP=0, FN=0, P/R=1.0, scanner errors=0.

---

## Operator actions before expert start

1. Fill RoE placeholders in `docs/security/expert-test-rules-of-engagement.md`.
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

3. Send credentials via secure channel — **not** platform_admin.
4. (Optional engineering) Investigate customer-validation non-determinism on web-realistic-active before removing `ready_with_blockers`.

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

## Why not `expert_security_test_ready`

- Web determinism **customer-visible variance 125%** on production commit (gate: 0%).  
- Blind benchmark completed on lint shim `0d8256a`, not exact deploy SHA `ac36b16`.  
- All other mandatory gates (API repeat, scanner errors, timeouts, unauthorized requests) pass.
