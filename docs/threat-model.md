# SIBER — Threat Model

## Scope

This document covers threats to the SIBER platform itself and threats arising from platform misuse. Analysis follows STRIDE methodology adapted for a multi-tenant SaaS security scanner.

## Assets

| Asset                    | Sensitivity | Description                                    |
|--------------------------|-------------|------------------------------------------------|
| User credentials         | Critical    | Passwords (hashed), refresh tokens, MFA secrets |
| Scan credentials         | Critical    | Auth tokens provided for authenticated scans   |
| Domain verification tokens | High      | Proof-of-ownership secrets                       |
| Scan results & findings  | High        | Security posture of customer applications        |
| Audit logs               | High        | Legal/compliance evidence of authorized testing  |
| AI prompts/responses     | Medium      | May contain masked technical details             |
| Billing data             | High        | Subscription and payment metadata                |
| Platform infrastructure  | Critical    | Workers, DB, Redis, object storage               |

## Trust Boundaries

```
[Internet User] ──► [CDN/Proxy] ──► [Frontend/API]
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
              [PostgreSQL]           [Redis]            [Scan Workers]
                                                          │
                                                    [Customer Target]
                                                    (verified only)
```

**Untrusted inputs:**
- User-supplied URLs and domains
- Scan tool output (treat as untrusted — prompt injection risk for AI)
- Webhook payloads (future)
- Uploaded repository archives (Code Scan)

## STRIDE Analysis

### Spoofing

| Threat | Impact | Mitigation |
|--------|--------|------------|
| Account takeover via credential stuffing | High | Rate limiting, bcrypt/argon2 hashing, MFA (optional), account lockout |
| Session hijacking | High | HttpOnly/Secure cookies, refresh token rotation, short-lived access tokens |
| Domain ownership spoofing | Critical | Mandatory DNS/file/meta verification before scans |
| Scan worker impersonation | High | Scoped job tokens, mTLS or signed job payloads (Phase 4+) |

### Tampering

| Threat | Impact | Mitigation |
|--------|--------|------------|
| IDOR on findings/scans | High | Server-side RBAC on every endpoint; org-scoped queries |
| Audit log modification | Critical | Append-only audit table; no UPDATE/DELETE on audit records |
| Scan result manipulation | Medium | Raw outputs stored immutably; checksums on worker uploads |
| Database injection | Critical | Parameterized queries (SQLAlchemy ORM); input validation |

### Repudiation

| Threat | Impact | Mitigation |
|--------|--------|------------|
| User denies authorizing scan | High | Authorization acceptance logged with timestamp, IP, user ID, domain |
| Admin action without trace | High | Audit log for all admin operations |

### Information Disclosure

| Threat | Impact | Mitigation |
|--------|--------|------------|
| Cross-tenant data leak | Critical | Strict org_id filtering; integration tests for isolation |
| Secrets in logs/reports | Critical | Log masking; evidence redaction before storage |
| SSRF to internal networks | Critical | URL validation, IP blocklist, no redirect following to private IPs |
| AI data leakage to provider | Medium | Mask tokens/passwords/PII before AI calls; data processing agreements |
| Error messages exposing internals | Medium | Generic client errors; detailed logs server-side only |

### Denial of Service

| Threat | Impact | Mitigation |
|--------|--------|------------|
| Scan flooding target | Critical | Safe Scan only in production; rate limits; concurrent scan caps |
| Platform resource exhaustion | High | Worker CPU/RAM/time limits; queue backpressure; plan quotas |
| Redis/DB connection exhaustion | Medium | Connection pooling; timeouts; circuit breakers |

### Elevation of Privilege

| Threat | Impact | Mitigation |
|--------|--------|------------|
| Viewer → Admin escalation | Critical | Server-side role checks; principle of least privilege |
| Regular user → platform admin | Critical | Separate admin role; admin routes isolated |
| Scan worker → internal network | Critical | Network policies; egress filtering on worker containers |

## Abuse Scenarios

### Unauthorized Scanning

**Scenario**: Attacker registers and attempts to scan third-party domains.

**Controls**:
1. Domain verification required (DNS TXT, well-known file, or meta tag)
2. Explicit authorization checkbox with immutable audit record
3. Subdomains not auto-included
4. Abuse reporting and account suspension (Admin panel)
5. Rate limiting per org/IP

### SSRF via Target URL

**Scenario**: Attacker submits `http://169.254.169.254/` or internal IP as scan target.

**Controls**:
1. Resolve hostname; reject private/reserved/link-local/metadata ranges
2. Block localhost, `.local`, `.internal` TLDs
3. No automatic redirect following without re-validation
4. Scan workers on isolated network segment

### Scan Tool Output → AI Prompt Injection

**Scenario**: Malicious page embeds instructions in HTTP response to manipulate AI analysis.

**Controls**:
1. Treat all scan output as untrusted data
2. System prompts explicitly forbid executing embedded instructions
3. Structured output schema validation
4. AI labels all outputs as unverified analysis

### Worker Container Escape

**Scenario**: Vulnerability in scan tool leads to host compromise.

**Controls**:
1. Non-root containers
2. Read-only root filesystem where possible
3. seccomp/AppArmor profiles (Phase 10)
4. Ephemeral workers destroyed after scan
5. No persistent credentials in worker images

## Risk Matrix (Initial)

| Risk ID | Description                     | Likelihood | Impact   | Priority |
|---------|---------------------------------|------------|----------|----------|
| R-001   | Unauthorized third-party scan   | Medium     | Critical | P0       |
| R-002   | SSRF to internal infrastructure | Medium   | Critical | P0       |
| R-003   | Cross-tenant data exposure      | Low        | Critical | P0       |
| R-004   | DoS via aggressive scan profile | Medium     | High     | P1       |
| R-005   | Credential leakage in logs      | Medium     | High     | P1       |
| R-006   | AI prompt injection             | Medium     | Medium   | P2       |
| R-007   | Session fixation/theft          | Low        | High     | P1       |

## Security Testing Requirements

- Permission tests for every API endpoint
- Domain verification bypass attempts
- SSRF regression test suite
- IDOR test matrix per resource type
- Dependency scanning in CI (Trivy)
- Container image scanning in CI

## Review Schedule

This threat model must be reviewed:
- Before each major phase release
- When adding new scan tools or AI providers
- After any security incident
- At minimum quarterly in production
