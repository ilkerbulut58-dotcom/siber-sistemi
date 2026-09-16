# RC9 production steps (requires DEPLOY_SSH_PASSWORD in process env — never commit).
$ErrorActionPreference = 'Stop'
if (-not $env:DEPLOY_SSH_PASSWORD) {
  Write-Error 'Set DEPLOY_SSH_PASSWORD in this terminal session (User secrets / env), then re-run.'
}
$env:DEPLOY_CONFIRM = 'production-pilot'
$env:RELEASE_TAG = 'v0.9.0-rc9-evidence-profile-4'
$env:APP_VERSION = '0.9.0-rc9-evidence-profile'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
node scripts/deploy-pilot-production.cjs
node scripts/ssh-export-scan-report-pdf.cjs a6426ea8-d574-41ea-92fc-d37157af71d3 tr
node scripts/ssh-prod-dns-reject-smoke.cjs
curl.exe -sS -k "https://siber.cloudnira.com/api/v1/health"
Pop-Location
