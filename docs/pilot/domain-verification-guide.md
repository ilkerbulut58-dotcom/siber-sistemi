# Domain Verification Guide

## Supported Methods

1. **DNS TXT** — Add record at `_sibercheck.<domain>` or root per in-app instructions.
2. **HTML file** — Serve token at `/.well-known/sibercheck-verification.txt`.
3. **Meta tag** — Add `<meta name="sibercheck-verification" content="...">` on homepage.
4. **Manual admin approval** — Platform or org admin approves active scanning via API.

## Active Scan Approval

Passive scans require verified domain only. Deep/Code (active) scans additionally require `active_scan_allowed` on the domain record (Phase 12).

## Redirect Validation

Redirect targets are re-validated against SSRF guardrails in production/staging.
