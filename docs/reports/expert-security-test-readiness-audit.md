# Expert Security Test Readiness Audit (Final)

**Date:** 2026-07-29  
**Verdict:** `expert_security_test_ready`  
**Live:** https://siber.cloudnira.com  

---

## Production seal

| Field | Value |
|-------|-------|
| previous_production_sha | `ac36b16` |
| previous_release_tag | `v0.9.0-rc3-expert` |
| **production_sha** | **`db57d3f`** |
| **release_tag** | **`v0.9.0-rc5-expert`** |
| version | `0.9.0-rc5-expert` |
| deploy_evidence | `health_git_commit=db57d3f1b771`, `PILOT_PRODUCTION_DEPLOY_OK` |
| backend/worker/mobile-worker/front SHA | **consistent (`db57d3f`)** |

---

## Customer-visible nondeterminism — root cause (run 30461802176)

| Field | Finding |
|-------|---------|
| **unstable_finding** | `missing-header-content-security-policy` (and related site-wide header rules) |
| **unstable_input** | Variable ZAP URL discovery (`/robots.txt`, `/ftp`, `/styles.css`) |
| **unstable_rule** | Per-URL customer validation without site-wide correlation merge |
| **order_dependency** | `verification_engine` reused first HTTP response for all header checks |
| **URL_dependency** | Header verification ran against spider-discovered URL, not scan target root |
| **evidence_dependency** | `passive_http` `missing_header` evidence ignored when grouped with low-confidence ZAP duplicates |
| **exact_root_cause** | Global response cache in `_get_response()` plus per-URL publication decisions caused the same underlying missing-header issue to flip between `confirmed` and `needs_review` depending on crawl order |

**Example:** Run `7fff515b` had CSP on `/` as `needs_review`/`low_confidence` while runs `5d7eaec4`/`0def32a9` had `customer_visible_count=1` with CSP `confirmed`.

---

## Fixes (no ground truth / fixture changes)

| File | Change |
|------|--------|
| `backend/app/analysis/verification_engine.py` | Per-URL response cache; site-wide headers verified against scan target root |
| `backend/app/benchmark/customer_validation.py` | Deterministic site-wide grouping, evidence merge, passive_http header confirmation |
| `backend/app/analysis/correlation_engine.py` | Deterministic group iteration and canonical URL selection |
| `backend/app/analysis/correlation_rules.py` | `missing-header-*` rule IDs normalize across scanners |
| `backend/app/benchmark/alert_dedup.py` | Deterministic ZAP group ordering |
| `backend/tests/test_customer_validation_determinism.py` | 20+ order/permutation regression tests |
| `backend/tests/test_verification_engine_determinism.py` | Site-wide header verification regression |
| `.github/workflows/ci.yml` | Blind benchmark on `workflow_dispatch` (from rc4) |
| `backend/app/services/domain_verification_service.py` | Ruff re-export `__all__` (from rc4) |

---

## GitHub Actions evidence (single SHA: `db57d3f`)

**Workflow:** `.github/workflows/ci.yml`  
**Dispatch ref:** `v0.9.0-rc5-expert`  
**Run ID:** [30465738199](https://github.com/ilkerbulut58-dotcom/siber-sistemi/actions/runs/30465738199)  
**Head SHA (all jobs):** `db57d3f` ✓  

| Benchmark | Run ID | Head SHA | Artifact | Result |
|-----------|--------|----------|----------|--------|
| determinism 5× | 30465738199 | `db57d3f` | `benchmark-determinism-reports` | **PASS** (variance 0%) |
| API repeat 5× | 30465738199 | `db57d3f` | `benchmark-api-active-repeat-reports` | **PASS** |
| blind | 30465738199 | `db57d3f` | `benchmark-blind-reports` | **PASS** |
| backend + closed-pilot | 30465738199 / 30465576479 | `db57d3f` | — | **PASS** |
| frontend build/test | 30465738199 | `db57d3f` | — | **PASS** |

**SHA alignment:** `production_sha == determinism_head_sha == api_repeat_head_sha == blind_head_sha == db57d3f`

Local evidence: `benchmarks/ci-evidence/run-30465738199/`

---

## Web determinism 5× (`db57d3f`)

| Run | TP | FP | FN | Raw P/R | CV | Scanner err | Timeout |
|-----|----|----|-----|---------|-----|-------------|---------|
| 1 | 5 | 0 | 0 | 1.0/1.0 | 3 | 0 | 0 |
| 2 | 5 | 0 | 0 | 1.0/1.0 | 3 | 0 | 0 |
| 3 | 5 | 0 | 0 | 1.0/1.0 | 3 | 0 | 0 |
| 4 | 5 | 0 | 0 | 1.0/1.0 | 3 | 0 | 0 |
| 5 | 5 | 0 | 0 | 1.0/1.0 | 3 | 0 | 0 |

**Summary:** `customer_visible_variance_pct=0.0`, `tp_stable=true`.  
**Note:** CV count is now consistently **3** (CSP/HSTS/XCTO confirmed via deterministic passive_http root evidence). Raw TP/FN unchanged from baseline.

---

## API active repeat 5× (`db57d3f`)

| Run | TP | FP | FN | P/R | CV | Scanner err |
|-----|----|----|-----|-----|-----|-------------|
| all 5 | 4 | 0 | 0 | 1.0/1.0 | 2 | 0 |

**Variance:** 0%

---

## Blind (`db57d3f`)

| Metric | Value |
|--------|-------|
| status | `completed` |
| TP | 2 |
| confirmed FP | 0 |
| FN | 0 |
| precision / recall | 1.0 / 1.0 |
| scanner errors | 0 |
| timeout | 0 |

---

## Production validation (post-deploy)

| Check | Result |
|-------|--------|
| health / readiness | 200 |
| git_commit | `db57d3f1b771` |
| workers | healthy |
| public registration | 403 |
| default admin | disabled |
| scanner errors (benchmarks) | 0 |
| unauthorized external requests | 0 |

---

## Regression tests

- `test_customer_validation_determinism.py`: 20+ input order/permutation cases — **PASS**
- `test_verification_engine_determinism.py`: site-wide header verification — **PASS**
- Full backend pytest: **261 passed**
- Frontend vitest: **30 passed**

---

## Accepted pilot risks (non-blocking)

- Expert email / tenant not yet provisioned (script dry-run verified)
- npm transitive audit highs
- Container scan (Trivy) not run in this session
- Production `.env` version string may show prior label until next env sync (git SHA authoritative)

---

## Final verdict

### `expert_security_test_ready`

All mandatory benchmark gates pass on a single production commit with 0% customer-visible variance, aligned SHA across production and CI, blind validation complete, and deterministic publication behavior verified by regression tests.
