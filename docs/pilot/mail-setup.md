# SIBER Mail Setup (Ionos SMTP)

Production transactional mail for SIBER (verify email, password reset).

## Current production configuration

| Item | Value |
|------|--------|
| SMTP | `smtp.ionos.de:587` STARTTLS |
| Auth user | Ionos mailbox with relay permission (e.g. `info@wolkeshopping.de`) |
| From header | `SIBER <info@wolkeshopping.de>` |
| App env | `/opt/siber/.env` (`SMTP_*`, `EMAIL_FROM`, `FRONTEND_PUBLIC_URL`) |

SIBER sends **directly to Ionos SMTP** from Docker (`api` / `worker`). Local Plesk Postfix is not used for app mail.

> **Why not `noreply@cloudnira.com` via Ionos?** Ionos rejects relay when the authenticated account is not authorized to send as that address (`550 Sender address is not allowed`). Until `noreply@cloudnira.com` exists on Ionos or SPF/DKIM + Plesk direct MX delivery is configured, use the authorized Ionos sender above.

Configure on server:

```powershell
$env:DEPLOY_SSH_PASSWORD = "..."
node scripts/ssh-configure-ionos-smtp.cjs
```

## DNS (recommended)

Update SPF for `cloudnira.com` at Ionos so future `noreply@cloudnira.com` direct sending is trusted:

```
v=spf1 include:_spf.perfora.net include:_spf.kundenserver.de ip4:87.106.10.169 ~all
```

## Verify

1. Register or use **Forgot password** on https://siber.cloudnira.com
2. Check API logs: `docker logs siber-api 2>&1 | grep email`
3. Expect `email.sent` (not `email.send_failed`)

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `451 Temporary lookup failure` via Plesk Postfix | Use Ionos direct (`scripts/ssh-configure-ionos-smtp.cjs`) |
| Missing `/etc/postfix/sender_relay.db` | `postmap /etc/postfix/sender_relay && postfix reload` |
| `550 Sender address is not allowed` on Ionos | Use authorized `SMTP_USER` as `EMAIL_FROM` |
| Mail in spam | Check Hotmail junk folder; update SPF/DKIM |

## Scripts

- `scripts/ssh-configure-ionos-smtp.cjs` — apply Ionos SMTP to `/opt/siber/.env` and restart API
- `scripts/ssh-mail-diagnose.cjs` — Postfix / DNS diagnostics
- `scripts/ssh-resend-verification.cjs` — resend verification for a registered user
