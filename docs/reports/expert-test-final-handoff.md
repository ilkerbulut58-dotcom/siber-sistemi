# Expert Test Final Handoff

**Handoff date:** 2026-07-29  
**Verdict:** Updated after v0.9.0-rc3-expert deploy gate.

See operator checklist sections 1–40 in the sealing workflow output.

**Expert tenant create command (when email known):**

```bash
python backend/scripts/prepare_expert_test_tenant.py \
  --email EXPERT@EXAMPLE.COM \
  --display-name "Expert Name" \
  --operator operator@company.com \
  --start-date 2026-08-01 \
  --end-date 2026-08-31 \
  --confirm EXPERT_TENANT_CREATE
```

**RoE:** `docs/security/expert-test-rules-of-engagement.md`
