# RC9: deploy + PDF always. DNS smoke only after blocked-IP second control is in the script.
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
$env:RELEASE_TAG = 'v0.9.0-rc12-admin-quota'
$env:APP_VERSION = '0.9.0-rc12-admin-quota'

Write-Host '=== 1/3 Deploy (tag' $env:RELEASE_TAG ') ==='
node scripts/deploy-pilot-production.cjs
if ($LASTEXITCODE -ne 0) {
  Remove-Item Env:DEPLOY_SSH_PASSWORD -ErrorAction SilentlyContinue
  Pop-Location
  exit $LASTEXITCODE
}

Write-Host '=== 2/3 Health ==='
curl.exe -sS -k "https://siber.cloudnira.com/api/v1/health"
Write-Host ''

Write-Host '=== 3/3 PDF a6426ea8 ==='
node scripts/ssh-export-scan-report-pdf.cjs a6426ea8-d574-41ea-92fc-d37157af71d3 tr
if ($LASTEXITCODE -ne 0) {
  Remove-Item Env:DEPLOY_SSH_PASSWORD -ErrorAction SilentlyContinue
  Pop-Location
  exit $LASTEXITCODE
}

Write-Host '=== DNS smoke (192.0.2.1 + redis LLEN scans) ==='
node scripts/ssh-prod-dns-reject-smoke.cjs
$smoke = $LASTEXITCODE
Remove-Item Env:DEPLOY_SSH_PASSWORD -ErrorAction SilentlyContinue
Pop-Location
if ($smoke -ne 0) {
  Write-Host 'DNS smoke FAILED or blocked — deploy/PDF may still have succeeded. Do not treat live DNS reject as verified.'
  exit $smoke
}
exit 0
