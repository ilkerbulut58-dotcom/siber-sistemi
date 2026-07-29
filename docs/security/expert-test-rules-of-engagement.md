# SIBER Expert Security Test — Rules of Engagement

**Product:** SIBER Security Analysis Platform  
**Environment:** Production Closed Pilot  
**Live URL:** https://siber.cloudnira.com  
**Document version:** 2026-07-29  

---

## 1. Purpose

Independent security expert evaluation of:

1. **Customer scan workflow** — domain onboarding, ownership verification, safe scanning, findings, reports, retest, feedback.
2. **Platform security** — authentication, authorization, tenant isolation, domain verification bypass resistance, SSRF controls, rate limits, report access.

This is **not** a public commercial penetration test of third-party targets.

---

## 2. System Under Test

| Item | Value |
|------|-------|
| Deployment | Single-server Docker Compose on operator infrastructure |
| Public entry | HTTPS via reverse proxy |
| Scanner stack | Passive HTTP/TLS, OWASP ZAP (passive), Nuclei (passive templates) |
| Active/full attack | **Disabled** in closed pilot |
| Semgrep / source-code analysis | **Not included** |
| Scan notifications | **Disabled** (`noop`) — auth e-mail uses separate SMTP |

---

## 3. Test Tenant

| Field | Policy |
|-------|--------|
| Creation | Operator-only (`backend/scripts/prepare_expert_test_tenant.py` or platform admin command) |
| `tenant_type` | `expert_security_test` |
| Role | `security_analyst` — **not** `platform_admin` |
| Pilot status | `active` |
| Daily scan quota | **10** |
| Concurrency | **1** (global and per tenant) |
| Allowed profiles | `safe` only by default |
| `deep` | **Off** unless written operator approval |
| `code` / full active | **Forbidden** |
| Domain verification | **Required** before any scan |
| Account expiry | Set by operator; revoke at test end |
| Notifications | Shown as disabled in UI |

**Placeholders (operator fills before test):**

- Test start date: `________________`
- Test end date: `________________`
- Expert contact e-mail: `________________`
- Operator contact: `________________`

---

## 4. Authorized Targets

### Allowed

- Domains **owned and verified** by the expert test tenant (DNS TXT, `.well-known`, or meta tag).
- Operator-approved isolated benchmark/lab targets (if provided separately).

### Forbidden

- Any third-party domain without explicit written authorization.
- Government, financial, healthcare, or competitor sites not owned by the tester.
- Shared infrastructure of other pilot tenants.

---

## 5. Scan Profile Rules

| Profile | Status |
|---------|--------|
| `safe` | **Allowed** — passive checks only |
| `deep` | **Requires written operator approval** — limited spider may run |
| `code` (exposed-paths / web exposure) | **Forbidden** in expert pilot |
| Full active / ZAP active scan | **Forbidden** |

---

## 6. Prohibited Activities (without written approval)

- Denial-of-service or stress testing
- Credential stuffing or brute-force against production auth
- Social engineering of staff or customers
- Physical security testing
- Data modification or deletion on targets
- Scanning unverified domains
- Exploitation that could damage production data or availability

---

## 7. Platform Testing Scope (tenant account)

Permitted on the platform itself (using expert tenant, not platform admin):

- Authentication and session handling
- Role enforcement and IDOR attempts within authorized scope
- Tenant isolation checks
- Domain verification bypass attempts
- SSRF and redirect authorization tests against **owned** targets only
- Rate limit behavior
- Report and finding access controls
- Feedback authorization
- APK upload security (if enabled for tenant)

---

## 8. Emergency Stop

| Control | Action |
|---------|--------|
| Kill switch | Operator sets `scans_disabled` on organization |
| Worker stop | `docker compose -f docker-compose.prod.yml stop worker` on server |
| Account revoke | Disable expert user + revoke domain verification |
| Contact | `________________` (operator on-call) |

---

## 9. Reporting Findings

- **Non-critical:** Platform finding feedback UI or agreed secure channel
- **Critical (platform):** Immediate operator notification — do not disclose publicly before coordinated fix
- **Target findings:** Standard SIBER report export (HTML/PDF/JSON)

---

## 10. Data Retention

- Scan artifacts retained per operator data-retention policy
- Expert tenant and domains **revoked** after test completion
- Refresh tokens revoked; account disabled

---

## 11. Responsible Disclosure

Findings affecting the platform operator or other tenants must follow coordinated disclosure with the operator contact above.

---

## 12. Known Limitations (Accepted Pilot Risks)

- **MFA not enabled** — accepted closed-pilot risk
- **Single-server architecture** — no HA failover
- **Offsite backup may be absent** — verify with operator
- **Scan notifications noop** — no e-mail on scan complete
- **No Semgrep** — `code` profile is exposure analysis, not SAST
- Product does **not** guarantee detection of all vulnerabilities

---

## 13. Expert Workflow Checklist

1. Log in with operator-provisioned expert tenant account
2. Add owned domain to project
3. Complete DNS / file / meta verification
4. Accept scan authorization declaration
5. Run **safe** scan only
6. Review findings, export reports, submit feedback
7. Request retest as needed
8. Request **deep** only with written operator approval
9. At test end: operator revokes domain and disables account
