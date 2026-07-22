# Publish feat/detection-quality-benchmark-lab to GitHub and open a PR.
# Prerequisites:
#   1. Create an EMPTY repo: https://github.com/new?name=siber-sistemi
#   2. Authenticate once: gh auth login
#      OR set env: $env:GITHUB_TOKEN = "<personal access token with repo scope>"
param(
    [string]$Owner = "ilkerbulut58-dotcom",
    [string]$Repo = "siber-sistemi",
    [string]$FeatureBranch = "feat/detection-quality-benchmark-lab"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$gh = Get-Command gh -ErrorAction SilentlyContinue
if (-not $gh) {
    $portable = Join-Path $env:TEMP "gh-cli\bin\gh.exe"
    if (Test-Path $portable) { $gh = @{ Source = $portable } }
}
if (-not $gh) {
    throw "GitHub CLI (gh) is required. Install from https://cli.github.com/ or rerun after portable gh is downloaded."
}

& $gh.Source auth status | Out-Null

Write-Host "Running pre-push security check..."
& (Join-Path $root "scripts/pre-push-security-check.ps1")

$remote = "https://github.com/$Owner/$Repo.git"
git remote remove origin 2>$null
git remote add origin $remote

Write-Host "Ensuring remote repository exists..."
& $gh.Source repo view "$Owner/$Repo" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $gh.Source repo create "$Owner/$Repo" --private --description "SIBER security analysis platform" --confirm
}

if (-not (git show-ref --verify --quiet refs/heads/main)) {
    git branch main d7ddacc
}

Write-Host "Pushing main (gitignore baseline only)..."
git push -u origin main

Write-Host "Pushing feature branch..."
git push -u origin $FeatureBranch

Write-Host "Creating pull request (no merge)..."
& $gh.Source pr create `
    --base main `
    --head $FeatureBranch `
    --title "feat: Detection Quality Benchmark Lab" `
    --body @"
## Summary
- Adds detection quality benchmark lab (migrations 001-013, fixtures, runner, report-only gate).
- Hardens system-scope organization isolation and support grant rules.
- Fixes pytest regressions and adds authorization regression tests.
- Extends GitHub Actions with Postgres/Redis-backed web/api/android smoke benchmarks.

## Test plan
- [ ] CI backend job (102 tests)
- [ ] CI frontend typecheck/lint/vitest/build
- [ ] benchmark-smoke job with fixture health checks and artifact upload

## Notes
- BENCHMARK_GATE_MODE=report (not enforce)
- No production deploy
- Do not merge until benchmark metrics are reviewed
"@

Write-Host "Done. Monitor Actions at: https://github.com/$Owner/$Repo/actions"
