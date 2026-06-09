# Expose pilote Docker stack (nginx :8088) via Cloudflare quick tunnel — HTTPS public URL.
# Prerequisite: docker compose -f docker-compose.yml -f docker-compose.pilot.yml --env-file .env.pilot up -d
param(
  [int]$NginxPort = 8088
)
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $Root

$bundled = Join-Path $PSScriptRoot "cloudflared.exe"
$cf = if (Test-Path $bundled) { $bundled } else { (Get-Command cloudflared -ErrorAction SilentlyContinue)?.Source }
if (-not $cf) {
  Write-Host "cloudflared not found. winget install Cloudflare.cloudflared" -ForegroundColor Yellow
  exit 1
}

Write-Host ""
Write-Host "Pilote stack must be running on http://127.0.0.1:$NginxPort" -ForegroundColor Cyan
Write-Host "Public HTTPS URL (share on WhatsApp):" -ForegroundColor Green
Write-Host ""

& $cf tunnel --url "http://127.0.0.1:$NginxPort"
