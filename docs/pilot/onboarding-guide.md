# Pilot Onboarding Guide

Closed pilot onboarding for SiberCheck:

1. Register at the application signup page.
2. Verify email via the link sent (dev: token logged; production: SMTP required).
3. Create or join an organization (platform admin marks org as pilot).
4. Add target domain under a project.
5. Verify domain via DNS TXT, HTML file, or meta tag — or request manual admin approval.
6. Accept the scan authorization declaration before each scan.
7. Choose scan profile: **Safe** (passive) default; **Deep/Code** only with admin active-scan approval.
8. Review findings in the customer-visible layer.
9. Download PDF/HTML report.
10. Submit finding feedback (false positive, accepted risk, needs help, etc.).

Platform admin must enable pilot flag, dates, and quota before customer scans succeed.
