# SIBER — Security & Authorization Policy

## Purpose

This policy defines mandatory security controls for the SIBER platform. All development, deployment, and operational activities must comply with these rules.

## Authorization & Legal Requirements

### Domain Ownership Verification

- **No scan may start** until domain ownership is verified.
- Supported verification methods:
  1. **DNS TXT record**: `_siber-verify.{domain}` with token value
  2. **Well-known file**: `https://{domain}/.well-known/security-scan-verification.txt`
  3. **HTML meta tag**: `<meta name="siber-domain-verification" content="{token}">`
- Tokens must be: cryptographically random, single-purpose, time-limited, bound to user + project.
- Verification is re-checked on a scheduled basis (default: every 24 hours).
- Loss of verification **blocks all new scans** for that domain.
- **Subdomains are not automatically authorized** — each must be explicitly added and verified.

### User Authorization Acceptance

Before initiating any scan, the user must explicitly confirm:

> "I confirm that I am authorized to perform security testing on the specified target(s)."

The system records:
- User ID
- Organization ID
- Target domain/URL
- Timestamp (UTC)
- Source IP address
- User agent
- Scan profile selected

This record is **immutable** and retained for audit purposes.

## Scan Restrictions

### Prohibited Activities

The platform must **never** perform:

- Denial of Service (DoS/DDoS) testing
- Brute force or credential stuffing attacks
- Data deletion or destructive operations
- File upload exploitation against production targets
- Service disruption beyond safe passive/active security checks
- Exploitation of vulnerabilities without explicit user-defined scope
- Scanning of unverified third-party domains
- Scanning of out-of-scope subdomains

### Scan Mode Policy

| Mode       | Allowed Environments     | Requirements                          |
|------------|--------------------------|---------------------------------------|
| Safe Scan  | Production               | Default; no destructive checks        |
| Deep Scan  | Staging/test only        | Explicit user flag + environment tag  |
| Code Scan  | User-provided repos      | Repository access authorization       |

- Production environments **must** use Safe Scan only.
- Aggressive/experimental tests run **only** in isolated lab environments (not customer-facing workers).

## SSRF Protection

All user-supplied URLs undergo validation before any outbound request:

### Blocked Address Ranges

- `127.0.0.0/8` (loopback)
- `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` (private)
- `169.254.0.0/16` (link-local / cloud metadata)
- `0.0.0.0/8`, `100.64.0.0/10` (reserved/CGN)
- `::1/128`, `fc00::/7`, `fe80::/10` (IPv6 private/link-local)
- Hostnames: `localhost`, `*.local`, `*.internal`, metadata endpoints

### URL Handling Rules

- Resolve DNS before connecting; validate resolved IP against blocklist
- Re-validate IP after redirects (limit redirect depth)
- Allow only `http` and `https` schemes
- Block file://, gopher://, and other non-HTTP schemes

## Authentication & Access Control

### Password Policy

- Minimum 12 characters
- Hashed with bcrypt (cost factor ≥ 12) or Argon2id
- Never stored or logged in plaintext

### Session Management

- Access tokens: short-lived (15 minutes default)
- Refresh tokens: rotation on use; revocation support
- Secure, HttpOnly, SameSite=Strict cookies where applicable
- Session invalidation on password change

### Role-Based Access Control

| Role              | Permissions Summary                                    |
|-------------------|--------------------------------------------------------|
| Owner             | Full org control, billing, member management           |
| Admin             | Manage projects, scans, members (except billing delete)|
| Security Analyst  | Run scans, manage findings, generate reports             |
| Developer         | View findings, mark resolved, trigger retest             |
| Viewer            | Read-only access to projects and reports                 |

- **Every API endpoint** enforces server-side authorization.
- Frontend role checks are supplementary only.
- Platform admin is a separate elevated scope, not assignable by org owners.

### Brute Force Protection

- Login rate limit: 5 attempts per 15 minutes per IP+email
- Account lockout after repeated failures (temporary)
- CAPTCHA consideration for Phase 10

## Data Protection

### Sensitive Data Handling

Never log or store in plaintext:
- Passwords
- API keys
- Session/refresh tokens
- Scan authentication credentials
- Authorization headers in request/response samples

### Evidence Masking

Before persisting findings or sending to AI:
- Mask `Authorization`, `Cookie`, `Set-Cookie` headers
- Redact JWT patterns, API key patterns, password fields
- Truncate large response bodies

### AI Data Policy

- AI outputs are **supplementary only** — never mark a finding as confirmed vulnerability based solely on AI
- All AI outputs tagged: `unverified`, `verified`, or `likely_false_positive`
- No exploit code generation
- No harmful payload generation
- Scan output treated as untrusted (prompt injection defense)
- AI failure must not block scan completion

## Application Security (OWASP ASVS Alignment)

### Input Validation

- Pydantic/Zod validation on all API inputs
- Allowlist-based validation for enums and scan profiles
- Maximum payload sizes enforced

### Output Encoding

- XSS prevention in frontend (React default escaping + CSP)
- HTML reports sanitized before rendering

### Injection Prevention

- SQLAlchemy ORM with parameterized queries
- No raw SQL with user input

### CSRF Protection

- SameSite cookies
- CSRF tokens for state-changing browser requests (Phase 2+)

### Security Headers (via Nginx/API)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; ...
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

## Infrastructure Security

### Container Security

- Non-root user in all containers
- Resource limits on scan workers: CPU, RAM, disk, network, execution time
- Temp files cleaned after scan completion
- Scan tools run in worker container, **never** in API container

### Secrets Management

- All secrets via environment variables or secret manager
- No secrets in source code or Docker images
- `.env` files gitignored; `.env.example` documents required vars

### Network Segmentation

- Scan workers: restricted egress, no access to internal DB
- API: access to DB/Redis only
- Database: not exposed to public internet in production

## Audit & Logging

### Audit Events (Minimum)

- User registration, login, logout, password change
- Authorization acceptance for scans
- Domain add/verify/revoke
- Scan start/cancel/complete/fail
- Finding status changes
- Role changes
- Admin actions
- Failed authorization attempts

### Log Requirements

- Structured JSON format
- Correlation IDs (`request_id`, `user_id`, `org_id`, `scan_id`)
- Sensitive field masking
- Retention per compliance requirements

## Rate Limiting

| Resource            | Default Limit              |
|---------------------|----------------------------|
| API requests        | 100/min per user           |
| Login attempts      | 5/15min per IP+email       |
| Scan creation       | Plan-dependent             |
| Concurrent scans    | 1 per target (configurable)|
| Domain verification | 10/hour per domain         |

## Incident Response

1. Detect via monitoring/alerts or user report
2. Contain: suspend affected accounts, block scans
3. Investigate via audit logs
4. Remediate and document
5. Notify affected customers if data breach confirmed

## Compliance Notes

- Platform reports must **not** represent automated scans as manual penetration test certification
- Unverified findings must be clearly labeled in all reports
- Users responsible for ensuring they have legal authority to test targets

## Policy Review

This policy is reviewed before each release phase and updated when:
- New scan tools are integrated
- New attack vectors are identified
- Regulatory requirements change
