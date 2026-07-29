# Expert Test Final Handoff

**Handoff date:** 2026-07-29  
**Final verdict:** `expert_security_test_ready_with_blockers`

---

## Summary

SIBER closed pilot is **sealed in Git**, deployed at **`v0.9.0-rc3-expert`**, and **workers are healthy**. Expert may begin after operator provisions tenant and CI benchmark 5× runs are confirmed on GitHub.

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
| Notifications | noop |
| Worker health | **healthy** |

---

## Operator actions before expert start

1. Confirm GitHub Actions CI green on `ac36b16` (backend, frontend, closed-pilot-simulation, benchmark-main, benchmark-blind, release-gates).
2. Run `workflow_dispatch`: **benchmark-determinism** and **benchmark-api-active-repeat** (5× each); archive run IDs.
3. Fill RoE placeholders in `docs/security/expert-test-rules-of-engagement.md`.
4. Create expert tenant (command below) when email is known.
5. Send credentials via secure channel — **not** platform_admin.

```bash
python backend/scripts/prepare_expert_test_tenant.py \
  --email EXPERT@EXAMPLE.COM \
  --display-name "Expert Name" \
  --operator operator@company.com \
  --start-date 2026-08-01 \
  --end-date 2026-08-31 \
  --confirm EXPERT_TENANT_CREATE
```

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

## Why not `expert_security_test_ready` yet

Benchmark **determinism 5×** and **API active repeat 5×** CI runs were not captured with run IDs in this sealing session (`gh` unavailable). All other mandatory gates passed including worker health, Git seal, deploy SHA consistency, and local 249+30 tests.
