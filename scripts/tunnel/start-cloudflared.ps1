# Public HTTPS URL for phone on 4G/5G (Cloudflare quick tunnel → local Vite).
# Prerequisite: backend :8000 + frontend `npm run dev:tunnel` on :5173
param(
  [int]$FrontendPort = 5173
)
$ErrorActionPreference = "Stop"

$bundled = Join-Path $PSScriptRoot "cloudflared.exe"
$cf = if (Test-Path $bundled) { $bundled } else { (Get-Command cloudflared -ErrorAction SilentlyContinue)?.Source }
if (-not $cf) {
  Write-Host ""
  Write-Host "cloudflared not found. Install one of:" -ForegroundColor Yellow
  Write-Host "  winget install Cloudflare.cloudflared"
  Write-Host "  https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
  Write-Host ""
  Write-Host "Or use ngrok: ngrok http $FrontendPort" -ForegroundColor Yellow
  exit 1
}

Write-Host ""
Write-Host "Starting Cloudflare tunnel → http://127.0.0.1:$FrontendPort" -ForegroundColor Cyan
Write-Host "Copy the https://....trycloudflare.com URL for the PATIENT phone." -ForegroundColor Green
Write-Host "Doctor laptop can use http://localhost:$FrontendPort (same Vite server)." -ForegroundColor White
Write-Host ""

& $cf tunnel --url "http://127.0.0.1:$FrontendPort"
