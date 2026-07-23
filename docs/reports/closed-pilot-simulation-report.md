# Closed Pilot Simulation Report

Local/staging technical validation of SiberCheck pilot infrastructure. **This is not a real closed pilot** — no real customers, external targets, email, or production changes were involved.

## Summary

| Field | Value |
|-------|-------|
| Branch | `feat/phase-12-production-hardening` |
| Commit SHA | `c261dc2f212dfeb6d517261fafcc461698a91649` |
| CI run ID | [30006622097](https://github.com/ilkerbulut58-dotcom/siber-sistemi/actions/runs/30006622097) |
| PR | [#5](https://github.com/ilkerbulut58-dotcom/siber-sistemi/pull/5) |
| Simulation date | 2026-07-23 |

## Artifact Names

| Artifact | CI job |
|----------|--------|
| `closed-pilot-simulation-junit` | `closed-pilot-simulation` |
| `benchmark-pr-reports` | `benchmark-smoke` |

## Pilot Tenants Created

All hostnames use lab domain `pilot-sim.example.com` with `BENCHMARK_LAB_ISOLATED=true`. No production DNS or external scanning.

| Tenant | Scenario | Domain verified | Quota | Kill switch | Pilot end |
|--------|----------|-----------------|-------|-------------|-----------|
| A | pilot-active | yes | 10 / 0 used | off | 2027-06-01 (future) |
| B | unverified-domain | no | 10 | off | active |
| C | quota-exceeded | yes | 2 / 2 used | off | active |
| D | expired-pilot | yes | 10 | off | 2025-06-01 (past) |
| E | kill-switch-disabled | yes | 10 | on (`scans_disabled`) | active |

Example hostnames: `pilot-a.pilot-sim.example.com` … `pilot-e.pilot-sim.example.com`

## User Roles

| Role | Count | Capabilities tested |
|------|-------|---------------------|
| owner | 5 (one per tenant) | domain mgmt, scan start, reports, members |
| analyst (`SECURITY_ANALYST`) | 5 | scan start, findings, feedback |
| viewer | 5 | read-only reports/findings |
| platform_admin | 1 | pilot tenant mgmt, manual domain verify, kill switch |

Sim password (fixture only): `PilotSim123!`

## Domain States Tested

| State | Tenant | Expected / observed |
|-------|--------|---------------------|
| Verified + active scan allowed | A, C, D, E | passive + active scans per policy |
| Unverified | B | active scan 403 `DOMAIN_NOT_VERIFIED`; audit `scan.rejected` |
| Admin manual verify | B → verified | `verification_method=manual_admin`; scan allowed after approval |

## Scan Profiles Tested

| Profile | Maps to | Tenant A result |
|---------|---------|-----------------|
| passive | `safe` | 201 |
| safe_active | `deep` | 201 |
| full_active | `code` | 201 (verified domain + pilot active + quota) |

Benchmark-only profiles (`benchmark-active-web`, `benchmark-active-api`) excluded from pilot UI paths. No external API/APK runtime scan in simulation (mocked dispatch).

## Test Results

| Suite | Passed | Failed |
|-------|--------|--------|
| Closed pilot simulation (`tests/pilot`) | **15** | **0** |
| Full backend regression (local) | **225** | **0** |
| CI `closed-pilot-simulation` job | **15** | **0** |
| CI full workflow run 30006622097 | all jobs green | 0 |

### Scenario Coverage (Tests 1–14)

| # | Scenario | Test file | Status |
|---|----------|-----------|--------|
| 1 | Successful pilot onboarding | `test_pilot_simulation.py` | pass |
| 2 | Unverified domain rejects active scan | `test_pilot_simulation.py` | pass |
| 3 | Manual admin domain approval | `test_pilot_simulation.py` | pass |
| 4 | Quota exceeded | `test_pilot_simulation.py` | pass |
| 5 | Pilot expired | `test_pilot_simulation.py` | pass |
| 6 | Kill switch + recovery | `test_pilot_simulation.py` | pass |
| 7 | Tenant isolation | `test_pilot_isolation.py` | pass |
| 8 | Role permissions | `test_pilot_roles.py` | pass |
| 9 | Scan profile permissions | `test_pilot_profiles.py` | pass |
| 10 | Redirect / SSRF guard | `test_pilot_redirect.py` | pass |
| 11 | Finding feedback audit | `test_pilot_feedback.py` | pass |
| 12 | Notification abstraction (noop) | `test_pilot_notifications.py` | pass |
| 13 | Audit log integrity | `test_pilot_audit.py` | pass |
| 14 | Emergency scan cancellation | `test_pilot_simulation.py` | pass |

## Gate Results

| Gate | Result |
|------|--------|
| Tenant isolation | **pass** — cross-tenant object access 403/404 |
| Authorization (roles) | **pass** — viewer/analyst/owner boundaries enforced |
| Quota enforcement | **pass** — 429 `SCAN_QUOTA_EXCEEDED`, no new job |
| Kill switch | **pass** — 403 `PILOT_SCANS_DISABLED`; admin toggle restores scans |
| Audit log | **pass** — rejections, feedback, cancel, domain verify logged; rejections committed before rollback |
| Notifications | **pass** — noop provider; no secrets in payloads |
| Real email | **not sent** |
| External targets | **not scanned** |
| Production deploy | **not performed** |

## Benchmark Comparison

| Metric | Pre-simulation baseline (run [30004169994](https://github.com/ilkerbulut58-dotcom/siber-sistemi/actions/runs/30004169994)) | Post-simulation (run [30006622097](https://github.com/ilkerbulut58-dotcom/siber-sistemi/actions/runs/30006622097)) |
|--------|----------------------------------------------------------------|------------------------------------------------|
| PR CI overall | success | **success** |
| `benchmark-smoke` | success | **success** |
| `closed-pilot-simulation` | n/a (new job) | **success** |
| Backend unit+integration | success | **success** |
| Determinism 5× / API repeat 5× | workflow_dispatch (not re-run this session) | skipped (dispatch-only jobs) |

No ground-truth manipulation. No regression observed in PR CI benchmark-smoke or backend tests after pilot simulation commit.

## Changed Files

- `.github/workflows/ci.yml` — `closed-pilot-simulation` job
- `backend/app/services/scan_service.py` — pilot guards, rejection audit commit, cancel audit
- `backend/app/services/pilot_service.py` — timezone-safe pilot date checks
- `backend/app/services/domain_service.py` — platform admin manual verify
- `backend/app/api/v1/platform.py` — manual domain verify endpoint
- `backend/app/api/v1/scans.py` — cancel refresh
- `backend/app/api/v1/findings.py` — post-commit refresh
- `backend/app/notifications/service.py` — pilot/quota/critical notifications
- `backend/tests/pilot/*` — fixtures + 15 simulation tests
- `scripts/seed_closed_pilot_simulation.py` — local/staging seed (rejects production)

## Remaining Limitations

1. Simulation uses in-process ASGI client and mocked scan dispatch — no live Juice Shop/crAPI container in pilot tests (benchmark-smoke covers lab fixtures separately).
2. `workflow_dispatch` benchmark jobs (determinism 5×, API repeat 5×, blind full) were not re-executed in this session.
3. Global kill switch is modeled as per-tenant `scans_disabled`; no separate global flag in product.
4. Scan profile names differ from product marketing labels (`safe`/`deep`/`code` vs passive/safe_active/full_active).
5. Seed script imports test fixtures — intended for dev/staging only.

## Manual Steps Before Real Closed Pilot

1. Re-run `benchmark-determinism` and `benchmark-api-active-repeat` via workflow_dispatch.
2. Configure staging DNS for owned test domains (not production customer DNS).
3. Wire real notification provider (replace noop) with opt-in recipients.
4. Legal/commercial pilot agreements and customer onboarding checklist.
5. Production DB migration review — do **not** run seed script against production.

## Final Decision

**`closed_pilot_simulation_passed`**

All 5 tenant scenarios, 14 test scenarios, role/isolation/quota/kill-switch/audit gates pass locally and in CI run 30006622097. PR benchmark-smoke shows no regression. Full `real_closed_pilot_ready` deferred until workflow_dispatch benchmark suites are re-run and staging ops checklist is complete.
