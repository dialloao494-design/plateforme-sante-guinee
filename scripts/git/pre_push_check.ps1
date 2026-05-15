# Run before git push — ensures secrets are not staged
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "../..")

$blocked = @(
    ".env",
    ".env.production",
    ".env.staging",
    "deploy/env/.env.backend",
    "deploy/env/.env.frontend"
)

$staged = git diff --cached --name-only 2>$null
$tracked = git ls-files 2>$null

foreach ($pattern in $blocked) {
    if ($staged -match [regex]::Escape($pattern)) {
        Write-Error "BLOCKED: $pattern is staged. Unstage before push."
    }
    if ($tracked -match "(?m)^$([regex]::Escape($pattern))$") {
        Write-Error "BLOCKED: $pattern is tracked by git. Remove from index: git rm --cached $pattern"
    }
}

Write-Host "pre_push_check: OK (no secret env files in commit)"
Write-Host "Remote: $(git remote get-url origin 2>$null)"
