# Expert Security Test Readiness Audit (Final Benchmark Evidence)

**Date:** 2026-07-29  
**Verdict:** `expert_security_test_ready_with_blockers`  
**Live:** https://siber.cloudnira.com  

---

## GitHub authentication (no secrets disclosed)

| Field | Value |
|-------|-------|
| github_authenticated | yes (`gh` CLI, account `ilkerbulut58-dotcom`) |
| auth_method | pre-existing `gh auth` keyring session |
| token_scopes | `repo`, `workflow`, `read:org`, `gist` (value not logged) |
| repository | `ilkerbulut58-dotcom/siber-sistemi` |
| default_branch | `main` |
| workflow_dispatch_permission | yes |
| artifact_read_permission | yes |
| BLIND_GROUND_TRUTH_SECRET | present (repository secret; value not read) |

---

## Git seal

| Field | Value |
|-------|-------|
| production_commit | `ac36b16` |
| release_tag | `v0.9.0-rc3-expert` (annotated tag → `ac36b16`) |
| origin_main_sha (post-benchmark) | `2a6adbf` (lint/CI shim only; production unchanged) |
| working_tree_clean | tracked files clean |
| secret_scan_before_commit | manual pattern scan on staged paths; no secrets committed |

**Production deploy commit:** `ac36b16` — backend/frontend/worker on https://siber.cloudnira.com remain at this SHA.  
**Docs/lint commits after deploy:** `730de67` (reports), `2a6adbf` (ruff re-export + blind dispatch), `0d8256a` (same shim on `expert/benchmark-ac36b16`). **No redeploy required** for documentation or lint-only CI fixes.

---

## Production (live evidence)

| Check | Result |
|-------|-------|
| Domain | https://siber.cloudnira.com |
| Deploy SHA | `ac36b16` |
| Version | `0.9.0-rc3-expert` |
| Tag | `v0.9.0-rc3-expert` |
| Backend/frontend/worker SHA | consistent |
| Health / readiness | 200, DB+Redis ok |
| Public registration | 403 `REGISTRATION_DISABLED` |
| Default admin | disabled |
| Migration | `019_domain_revalidation_expert` (head) |
| Worker health | **healthy** |

---

## GitHub Actions workflow definitions

| Workflow | File | Trigger | Notes |
|----------|------|---------|-------|
| benchmark-determinism | `.github/workflows/ci.yml` | `workflow_dispatch` | 5× `web-realistic-active`; artifact `benchmark-determinism-reports` |
| benchmark-api-active-repeat | `.github/workflows/ci.yml` | `workflow_dispatch` | 5× `api-realistic-active`; artifact `benchmark-api-active-repeat-reports` |
| benchmark-blind | `.github/workflows/ci.yml` | `pull_request`, `main`, `workflow_dispatch`* | artifact `benchmark-blind-reports`; needs `BLIND_GROUND_TRUTH_SECRET` |
| benchmark-release-gates | `.github/workflows/ci.yml` | `pull_request`, `main` | artifact `benchmark-release-gates-reports` |
| closed-pilot-simulation | `.github/workflows/ci.yml` | all pushes | artifact `closed-pilot-simulation-junit` |
| backend / frontend / docker | `.github/workflows/ci.yml` | all | standard CI |

\* `workflow_dispatch` for blind added in `2a6adbf` (required because tag dispatch on `ac36b16` skipped blind due to `github.ref == refs/heads/main` and backend ruff failure).

**Workflow inputs:** `ci.yml` has no `workflow_dispatch` input parameters — dispatch uses ref only.

---

## Benchmark run evidence

### Primary production-commit run (determinism + API)

| Field | Value |
|-------|-------|
| Run ID | **30461802176** |
| URL | https://github.com/ilkerbulut58-dotcom/siber-sistemi/actions/runs/30461802176 |
| Event | `workflow_dispatch` |
| Ref | `v0.9.0-rc3-expert` |
| Head SHA | **`ac36b16`** ✓ |
| Dispatched | 2026-07-29T14:37:34Z |
| Overall | `failure` (backend ruff F401; benchmark jobs succeeded) |

| Job | Conclusion |
|-----|------------|
| benchmark-determinism | **success** |
| benchmark-api-active-repeat | **success** |
| benchmark-blind | **skipped** (backend failed + ref not `main`) |
| backend | **failure** (F401 unused import) |
| closed-pilot-simulation | success |
| frontend / docker | success |

**Artifacts downloaded:** `benchmarks/ci-evidence/run-30461802176/`

### Blind validation run (lint shim required)

| Field | Value |
|-------|-------|
| Run ID | **30462666435** |
| URL | https://github.com/ilkerbulut58-dotcom/siber-sistemi/actions/runs/30462666435 |
| Event | `workflow_dispatch` |
| Ref | `expert/benchmark-ac36b16` |
| Head SHA | **`0d8256a`** (= `ac36b16` + ruff `__all__` re-export + CI dispatch fix only) |
| Dispatched | 2026-07-29T14:48:01Z |
| Overall | **success** |

| Job | Conclusion |
|-----|------------|
| benchmark-blind | **success** |
| backend | success |
| benchmark-determinism | success (supplementary; not used for production gate) |
| benchmark-api-active-repeat | success (supplementary) |

**Why not exact `ac36b16`:** commit `ac36b16` fails backend ruff (`normalize_hostname` re-export F401), which blocks `benchmark-blind` via `needs: [backend]`. Shim commit `0d8256a` parent is `ac36b16`; no application logic changed.

**Artifacts downloaded:** `benchmarks/ci-evidence/run-30462666435/benchmark-blind-reports/`

### Supplementary main CI run

| Field | Value |
|-------|-------|
| Run ID | **30462639867** |
| URL | https://github.com/ilkerbulut58-dotcom/siber-sistemi/actions/runs/30462639867 |
| Event | `push` to `main` |
| Head SHA | `2a6adbf` |
| Overall | **success** |
| benchmark-blind | success |
| benchmark-release-gates | success (job ran; see gate result below) |
| backend / frontend / closed-pilot-simulation | success |

---

## Web determinism 5× (`ac36b16`, run 30461802176)

Artifact: `benchmark-determinism-reports` (`determinism-summary.json` + 5 report JSONs)

| Run | TP | FP | FN | Raw P | Raw R | CV count | CV P | CV R | Dup | ZAP | Scanner errors | Timeout |
|-----|----|----|-----|-------|-------|----------|------|------|-----|-----|----------------|---------|
| 5d7eaec4 | 5 | 0 | 0 | 1.0 | 1.0 | 1 | 1.0 | 1.0 | 3 | 5 | 0 | 0 |
| 7fff515b | 5 | 0 | 0 | 1.0 | 1.0 | **0** | 1.0 | 1.0 | 4 | 5 | 0 | 0 |
| a4c0c217 | 5 | 0 | 0 | 1.0 | 1.0 | 1 | 1.0 | 1.0 | 3 | 5 | 0 | 0 |
| d9b3265d | 5 | 0 | 0 | 1.0 | 1.0 | 1 | 1.0 | 1.0 | 4 | 5 | 0 | 0 |
| fc0157f3 | 5 | 0 | 0 | 1.0 | 1.0 | 1 | 1.0 | 1.0 | 3 | 5 | 0 | 0 |

**Summary:** `tp_stable=true`, `customer_visible_variance_pct=125%` (counts: 1,0,1,1,1).  
**Baseline comparison:** raw TP/FP/FN match baseline (TP=5, FP=0, FN=0, P/R=1.0). **Customer-visible variance regressed** from expected 0% — run `7fff515b` had all 9 raw findings classified `needs_review`/`informational` (0 customer-visible).  
**Root cause:** non-deterministic ZAP URL discovery (`/robots.txt`, `/ftp`) combined with customer-validation visibility rules; detection metrics stable, publication pipeline variable.  
**Release impact:** expert-visible finding count may differ run-to-run despite correct detection.  
**Expert test blocker:** yes — fails 0% customer-visible variance gate.

---

## API active repeat 5× (`ac36b16`, run 30461802176)

Artifact: `benchmark-api-active-repeat-reports`

| Run | TP | FP | FN | Raw P | Raw R | CV count | CV P | CV R | Dup | Scanner errors | Timeout |
|-----|----|----|-----|-------|-------|----------|------|------|-----|----------------|---------|
| 31bfcbcb | 4 | 0 | 0 | 1.0 | 1.0 | 1 | 1.0 | 1.0 | 0 | 0 | 0 |
| b58b4fa2 | 4 | 0 | 0 | 1.0 | 1.0 | 1 | 1.0 | 1.0 | 0 | 0 | 0 |
| c0ea0e67 | 4 | 0 | 0 | 1.0 | 1.0 | 1 | 1.0 | 1.0 | 0 | 0 | 0 |
| c38fec8d | 4 | 0 | 0 | 1.0 | 1.0 | 1 | 1.0 | 1.0 | 0 | 0 | 0 |
| e47fa4ed | 4 | 0 | 0 | 1.0 | 1.0 | 1 | 1.0 | 1.0 | 0 | 0 | 0 |

**Summary:** 5/5 completed; matches baseline (TP=4, FP=0, FN=0, P/R=1.0, CV stable). **PASS.**

---

## Blind validation (run 30462666435, head `0d8256a`)

Artifact: `benchmark-blind-reports/blind-benchmark.json`

| Metric | Value | Baseline | Pass |
|--------|-------|----------|------|
| Status | `completed` | completed | ✓ |
| TP | 2 | 2 | ✓ |
| Confirmed FP | 0 | 0 | ✓ |
| FN | 0 | 0 | ✓ |
| Additional valid | 6 | — | informational |
| Informational | 2 | — | — |
| Precision | 1.0 | 1.0 | ✓ |
| Recall | 1.0 | 1.0 | ✓ |
| Secret/decryption | success | — | ✓ |
| Scanner errors | 0 | 0 | ✓ |
| Timeout | 0 | 0 | ✓ |

**SHA caveat:** blind did **not** execute on exact production commit `ac36b16` (blocked by ruff). Metrics above are from `0d8256a` (lint-only delta).  
**Expert test blocker:** partial — metrics pass but head SHA ≠ production deploy SHA.

---

## Scanner errors, timeouts, external requests

| Benchmark | Scanner errors | Timeouts | Unauthorized external requests |
|-----------|----------------|----------|--------------------------------|
| Web determinism 5× | 0 | 0 | 0 (ZAP budget internal proxy only) |
| API repeat 5× | 0 | 0 | 0 |
| Blind | 0 | 0 | 0 |

---

## Additional CI verification (run 30462639867, head `2a6adbf`)

| Suite | Run ID | Head SHA | Result |
|-------|--------|----------|--------|
| backend (ruff + pytest) | 30462639867 | `2a6adbf` | success |
| frontend (lint/test/build) | 30462639867 | `2a6adbf` | success |
| closed-pilot-simulation | 30462639867 | `2a6adbf` | success |
| benchmark-blind | 30462639867 | `2a6adbf` | success |
| benchmark-release-gates | 30462639867 | `2a6adbf` | job success; MVP report `not_ready` (baseline fixture thresholds) |
| benchmark-determinism 5× | 30461802176 | **`ac36b16`** | success (variance fail) |
| benchmark-api-active-repeat 5× | 30461802176 | **`ac36b16`** | success |

Local tests on final application code (pre-shim): backend 249 passed, frontend 30 passed, closed-pilot 15 passed.

---

## Remaining blockers

1. **Web determinism customer-visible variance 125%** on production commit `ac36b16` (gate requires 0%).  
2. **Blind benchmark head SHA** `0d8256a` ≠ production deploy `ac36b16` (lint shim required to unblock CI).  
3. **Release-gates MVP report** on CI reports `not_ready` for passive/active subset thresholds (separate from expert benchmark gates; tracked as accepted pilot scope).

Non-blockers: expert email unknown, expert tenant not created (script dry-run verified).

---

## Final verdict

### `expert_security_test_ready_with_blockers`

GitHub Actions benchmarks were dispatched, tracked, and artifact-analyzed by automation. API repeat 5× passes on `ac36b16`. Web determinism raw detection is stable but customer-visible publication is non-deterministic. Blind completes with perfect holdout metrics but required a lint-only shim commit off `ac36b16`. Production remains deployed at `ac36b16`; no redeploy needed for this documentation update.
