# RC9 production verify — run in YOUR Cursor terminal (agent oturumu parolayı görmez).
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root

if (-not $env:DEPLOY_SSH_PASSWORD) {
  Write-Host 'SSH parolasini bu oturumda guvenli girin (ekranda gorunmez):'
  $sec = Read-Host -AsSecureString 'Deploy SSH password'
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
  try {
    $env:DEPLOY_SSH_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
  } finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
  }
}

$env:DEPLOY_CONFIRM = 'production-pilot'
$env:RELEASE_TAG = 'v0.9.0-rc9-evidence-profile-4'
$env:APP_VERSION = '0.9.0-rc9-evidence-profile'

Write-Host '=== 1/4 Deploy (tag' $env:RELEASE_TAG ') ==='
node scripts/deploy-pilot-production.cjs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '=== 2/4 Health (git_commit) ==='
curl.exe -sS -k "https://siber.cloudnira.com/api/v1/health"

Write-Host ''
Write-Host '=== 3/4 PDF a6426ea8 ==='
node scripts/ssh-export-scan-report-pdf.cjs a6426ea8-d574-41ea-92fc-d37157af71d3 tr
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '=== 4/4 Live DNS reject smoke ==='
node scripts/ssh-prod-dns-reject-smoke.cjs
$code = $LASTEXITCODE
Remove-Item Env:DEPLOY_SSH_PASSWORD -ErrorAction SilentlyContinue
Pop-Location
exit $code
