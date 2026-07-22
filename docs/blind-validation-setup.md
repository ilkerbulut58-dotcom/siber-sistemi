# Blind Benchmark Validation Setup

Blind holdout ground truth is **never stored in plaintext** in the repository. Only public metadata and an encrypted artifact are published.

## Prerequisites

- Repository admin access to configure GitHub Actions secrets
- The blind encryption passphrase (held outside the repo by security/benchmark owners)

## Manual procedure (GitHub Actions)

1. Open **Settings → Secrets and variables → Actions** for `ilkerbulut58-dotcom/siber-sistemi`.
2. Create repository secret: `BLIND_GROUND_TRUTH_SECRET`
   - Value: the blind holdout passphrase (do **not** commit, log, or paste into PR comments)
3. Re-run the **CI → benchmark-blind** job on `main` or a PR branch.
4. Expected outcomes:
   - **Secret missing:** job exits 0 with `"status": "skipped"` and `skip_reason: secret_missing` — no synthetic results
   - **Secret present:** job decrypts `benchmarks/blind/web-smoke-blind.enc`, runs holdout matching, writes `benchmarks/reports/blind-benchmark.json`

## Security rules

- Never write the secret into code, CI logs, artifacts, or benchmark reports
- Scanner developers must not have access to plaintext blind labels during feature development
- CI logs must not print decrypted ground truth contents
- If the secret is rotated, re-seal the artifact with `python -m app.benchmark blind-seal` (owner workflow only)

## Verification

Public metadata: `benchmarks/blind/metadata.yaml`  
Artifact hash: `artifact_sha256` in metadata must match `web-smoke-blind.enc`

## Release gate dependency

MVP release gate `blind_validation` passes only when blind job reports successful holdout validation. Until the secret is configured, release status remains **not_ready** with an explicit blocker — this is expected and not a CI failure.
