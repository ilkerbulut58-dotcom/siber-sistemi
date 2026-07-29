# Expert UI/UX Readiness Audit

**Date:** 2026-07-29  
**Final verdict:** `expert_ui_ready_with_blockers`  
**Production URL:** https://siber.cloudnira.com  
**Previous production SHA:** `db57d3f`  
**Release (prior):** `v0.9.0-rc5-expert`  
**Tested role (design target):** `security_analyst` (not `platform_admin`)

---

## Executive summary

Backend security and benchmark readiness were already **`expert_security_test_ready`**. This iteration closes the **P0 domain self-service role gap** and implements targeted **P1 UX** improvements (onboarding, domain verification UX, finding filters, i18n, quota display, error sanitization, navigation, support).

**Live expert E2E on production** and **automated CI/deploy** could not be completed in this session (local shell unavailable). Operator must run tests, tag, deploy, and execute controlled production walkthrough before upgrading verdict to **`expert_ui_ready`**.

---

## P0 — Fixed

| ID | Issue | Fix |
|----|-------|-----|
| P0-1 | `security_analyst` could start scans but **not** add/verify domains (API required `ADMIN`) | `POST /domains` and `POST /domains/{id}/verify` now require `SECURITY_ANALYST` minimum; delete/approve-active-scan remain `ADMIN` |
| P0-2 | Expert RoE vs API mismatch | Added `backend/tests/test_domain_analyst_self_service.py` |

---

## P1 — Fixed (this change set)

| Area | Change |
|------|--------|
| Onboarding | `show_onboarding_checklist` for pilot **and** `expert_security_test`; 5-step expert checklist driven by backend counts |
| Domain UX | Why banner, copy fields (DNS/well-known/meta), TTL/propagation/validity/revoke/manual approval notes |
| Verify errors | `failure_code` on verify response + i18n (`DNS_RECORD_NOT_FOUND`, etc.) |
| Quick scan | `DOMAIN_NOT_VERIFIED` redirects to `/dashboard/domains` |
| Profiles | Unified “Güvenli Tarama” / safe copy; deep no longer “aktif mod” |
| Finding triage | Client-side filters (severity, confidence, status, scanner, review, search) |
| i18n | Removed hardcoded TR in `finding-row-card`; DE/TR keys for new strings |
| Quota | `TenantQuotaPanel` uses org `onboarding-status` (tenant quota, reset UTC, concurrency) |
| Errors | `scan.error_log` sanitized in scan detail UI |
| Support | Settings support section + `support_contact_email` in system info (env-driven) |
| Nav | Domains, Findings redirect routes |
| Finding detail | Full workflow statuses, CVSS badge, severity/confidence/status tooltips, retest scope hint |
| Admin UX | Active-scan approval buttons hidden unless org `admin`/`owner` |

---

## P1 — Remaining / verify on deploy

| Item | Notes |
|------|-------|
| Live expert E2E | Requires operator-provisioned test tenant + controlled domain |
| PDF report quality | Not re-validated in this pass |
| Playwright + axe CI | Not added (recommended backlog) |
| Production test account | Create/disable per RoE after walkthrough |

---

## P2 backlog

- Dedicated global Reports page  
- Finding table view + server-side pagination  
- Scan progress percentage / stage bar  
- Full accessibility CI (axe/Lighthouse)  
- Short SHA only in system info (global quota row could be de-emphasized further)

---

## Role / permission model (after fix)

| Action | security_analyst | admin/owner | viewer |
|--------|------------------|-------------|--------|
| Add domain | ✅ | ✅ | ❌ |
| Verify domain (DNS/file/meta) | ✅ | ✅ | ❌ |
| Safe scan start | ✅ | ✅ | ❌ |
| Manual active-scan approval | ❌ | ✅ | ❌ |
| Org settings / quota change | ❌ | ✅ | ❌ |
| Platform admin APIs | ❌ | ❌ | ❌ |

---

## Scorecard (before → after, code-based)

| Dimension | Before | After | Evidence |
|-----------|--------|-------|----------|
| Domain verification UX | 5 | 7 | Copy panel, why text, failure codes |
| Onboarding | 5 | 7 | Always-on checklist for expert/pilot |
| Expert self-service | 4 | 8 | Role fix + nav + redirect |
| Finding triage | 5 | 7 | Filters + CVSS in list |
| i18n | 5 | 8 | finding-row-card + DE keys |
| Quota UX | 6 | 8 | Tenant panel from onboarding API |
| Error handling | 6 | 8 | Sanitized scan failures |
| Navigation | 5 | 7 | Domains/Findings routes |
| **Overall expert readiness** | **6** | **7.5** | Pending live E2E |

---

## Test plan (operator)

```bash
# Backend
cd backend && python -m pytest tests/test_domain_analyst_self_service.py tests/test_domains.py tests/test_pilot_tenant.py -q

# Frontend
cd frontend && npm run test -- --run && npm run build
```

---

## Deploy checklist

1. Commit all changes; tag e.g. `v0.9.0-rc6-expert`  
2. Push `origin/main`; deploy backend/frontend/worker same SHA  
3. Set `SUPPORT_CONTACT_EMAIL` in production env (no personal email in repo)  
4. Verify health `git_commit` alignment  
5. Expert tenant: confirm org membership role is `security_analyst` (not only owner)  
6. Run live walkthrough (login → domain → verify → safe scan → findings → report → feedback)  
7. Disable ephemeral E2E test account if created  

---

## Final recommendation

**Ship after CI green + one successful live expert walkthrough.**  
Verdict upgrade path:

- **`expert_ui_ready`** — live E2E pass, no P0, tests green  
- **`expert_ui_professional_grade`** — additionally PDF quality validated, axe smoke clean, score ≥8 sustained

**Current verdict:** `expert_ui_ready_with_blockers` (implementation done; production proof pending)

---

## Changed files (summary)

**Backend:** `domains.py`, `domain_service.py`, `domain_verification_service.py`, `schemas/domain.py`, `schemas/pilot.py`, `pilot_service.py`, `organizations.py`, `system.py`, `config.py`, `test_domain_analyst_self_service.py`, `test_domains.py`, `prepare_expert_test_tenant.py`

**Frontend:** nav, domains/findings pages, project/scan/org/settings pages, finding panels, domain verification panel, tenant quota panel, i18n TR/DE, scan error sanitizer, finding filters test
