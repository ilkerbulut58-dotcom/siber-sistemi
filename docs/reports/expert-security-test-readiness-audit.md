# Expert Security Test Readiness Audit (Final Seal)

**Date:** 2026-07-29  
**Verdict:** `expert_security_test_ready_with_blockers`  
**Live:** https://siber.cloudnira.com  

---

## Git seal

| Field | Value |
|-------|-------|
| clean_commit_sha | `ac36b16` |
| origin_main_sha | `ac36b16` |
| release_tag | `v0.9.0-rc3-expert` |
| working_tree_clean | tracked files clean; local untracked ops scripts excluded from deploy gate |
| secret_scan_before_commit | manual pattern scan on staged paths; no secrets committed |

**Commits (expert readiness):**

1. `2bfd0a8` fix(security): domain authorization and revalidation  
2. `68c6053` fix(auth): closed pilot registration and sessions  
3. `35e3c8e` fix(ops): release identity and worker health verification  
4. `45c117f` docs(security): RoE and README  
5. `8288f87` docs(reports): handoff tracking  
6. `6fcab49` fix: normalize_hostname export  
7. `1962f62` fix(ops): Celery ping healthcheck  
8. `eed7ead` fix(ops): LF gitattributes  
9. `ac36b16` fix(ops): CRLF strip in Docker build  

---

## Worker healthcheck root cause

1. **Wrong probe:** Production image inherited API `HEALTHCHECK` (curl :8000) while worker runs Celery — fixed by per-service compose healthchecks.  
2. **Wrong grep:** Celery `inspect ping` returns `OK`/`pong`, not JSON `"ok"`.  
3. **CRLF scripts:** Windows deploy tarball left `\r` in shell scripts → `set: Illegal option -`; fixed via `.gitattributes` + `sed` in Dockerfile.

**Worker final health (2026-07-29 post-deploy):** `siber-worker` **healthy**, `siber-mobile-worker` **healthy**

---

## Production (live evidence)

| Check | Result |
|-------|--------|
| Domain | https://siber.cloudnira.com |
| Deploy SHA | `ac36b16` (short `ac36b16…`) |
| Version | `0.9.0-rc3-expert` |
| Tag | `v0.9.0-rc3-expert` |
| Backend/frontend/worker SHA | consistent |
| Health / readiness | 200, DB+Redis ok |
| Public registration | 403 `REGISTRATION_DISABLED` |
| Default admin | disabled |
| Migration | `019_domain_revalidation_expert` (head) |
| Scan notifications | noop |
| Access token | 60 min |

---

## Tests (local, final commit)

| Suite | Result |
|-------|--------|
| Backend pytest | **249 passed**, 0 failed |
| Frontend vitest | **30 passed** |
| Frontend build | success |
| Closed-pilot simulation | **15 passed** |
| Release gates (local) | **all gates passed** |
| Ruff | clean |

---

## Benchmarks

| Suite | Status | Notes |
|-------|--------|-------|
| benchmark-determinism 5× | **UNVERIFIED** | Requires GitHub `workflow_dispatch`; `gh` CLI unavailable locally |
| benchmark-api-active-repeat 5× | **UNVERIFIED** | same |
| benchmark-blind | **UNVERIFIED** | CI job on main push; run ID not captured |
| benchmark-smoke | **UNVERIFIED** | CI on main push |
| closed-pilot-simulation | **PASS** (local) | 15/15 |
| release-gates | **PASS** (local) | `release-gates-mvp.json` |

**Minimum gate:** No local regression in pilot/release-gates; full CI benchmark matrix not re-run with captured run IDs in this session.

---

## Dependency / secret scan

| Scan | Result | Decision |
|------|--------|----------|
| pip-audit | no known vulnerabilities | OK |
| npm audit | 3 high (postcss/sharp via Next.js) | accepted pilot risk |
| Secret commit scan | no secrets in commits | OK |
| Container scan (Trivy) | not run | UNVERIFIED |

---

## Expert tenant

| Item | Status |
|------|--------|
| Script | `backend/scripts/prepare_expert_test_tenant.py` |
| Dry-run | verified |
| Live account | not created (no expert email) |
| Quota template | 10/day, concurrency 1, safe only |

**Create when email known:**

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

## Accepted pilot risks

- MFA absent  
- Single-server / no offsite encrypted backup  
- npm transitive highs  
- Benchmark CI run IDs not attached to this seal  
- Expert tenant pending operator provisioning  

---

## Final verdict

### `expert_security_test_ready_with_blockers`

Platform is sealed, deployed, and worker-healthy. Remaining blocker for **`expert_security_test_ready`**: documented CI benchmark-determinism 5× + API repeat 5× + blind validation run IDs on `ac36b16` (trigger via GitHub Actions → `workflow_dispatch` on `ci.yml`).
