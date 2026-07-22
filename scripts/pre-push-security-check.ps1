# Pre-push security scan for SIBER repository.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "== Checking tracked .env files =="
$envFiles = Get-ChildItem -Recurse -Force -Include ".env", ".env.*" -File |
    Where-Object { $_.FullName -notmatch "\\node_modules\\|\\\.venv\\" }
foreach ($file in $envFiles) {
    if ($file.Name -eq ".env.example") { continue }
    throw "Sensitive env file present: $($file.FullName)"
}

Write-Host "== Scanning for credential patterns =="
$patterns = @(
    "OPENAI_API_KEY\s*=\s*['\`"]?sk-",
    "SECRET_KEY\s*=\s*['\`"]?[A-Za-z0-9+/=_-]{20,}",
    "DEPLOY_SSH_PASSWORD\s*=",
    "BEGIN (RSA |OPENSSH )?PRIVATE KEY",
    "AKIA[0-9A-Z]{16}",
    "sk-live-[A-Za-z0-9]{20,}"
)
$scanRoots = @("backend", "frontend/src", "benchmarks", "deploy", "scripts", ".github")
$hits = @()
foreach ($scanRoot in $scanRoots) {
    $path = Join-Path $root $scanRoot
    if (-not (Test-Path $path)) { continue }
    Get-ChildItem -Path $path -Recurse -File |
        Where-Object {
            $_.FullName -notmatch "\\node_modules\\|\\\.venv\\|\\\.next\\|\\dist\\|\\\.pytest_cache\\"
        } |
        ForEach-Object {
            $content = Get-Content -LiteralPath $_.FullName -Raw -ErrorAction SilentlyContinue
            if (-not $content) { return }
            foreach ($pattern in $patterns) {
                if ($content -match $pattern) {
                    if ($_.FullName -match "test_|\.example|build_fixture_apk|secret_patterns|evidence-masker") { continue }
                    $hits += "$($_.FullName): matched $pattern"
                }
            }
        }
}
if ($hits.Count -gt 0) {
    $hits | ForEach-Object { Write-Host $_ }
    throw "Potential credential material detected."
}

Write-Host "== Ensuring benchmark artifacts are ignored =="
$gitignore = Get-Content ".gitignore" -Raw
foreach ($required in @("benchmarks/reports/", "benchmarks/baselines/", "fixture.apk")) {
    if ($gitignore -notmatch [regex]::Escape($required)) {
        throw ".gitignore missing entry: $required"
    }
}

Write-Host "Pre-push security check passed."
