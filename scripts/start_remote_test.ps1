# Real multi-device test launcher (doctor laptop + patient phone).
# Usage:
#   .\scripts\start_remote_test.ps1 -Mode lan      # same Wi-Fi only
#   .\scripts\start_remote_test.ps1 -Mode tunnel   # phone on 4G/Orange (recommended)
param(
  [ValidateSet('lan', 'tunnel')]
  [string]$Mode = 'tunnel',
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 5173,
  [switch]$ResetData,
  [switch]$OpenFirewall
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if ($ResetData) {
  & "$PSScriptRoot\run_lan_qa.ps1" | Out-Host
}

if ($OpenFirewall -and $Mode -eq 'lan') {
  Write-Host "Requesting firewall rules (Admin)..." -ForegroundColor Yellow
  Start-Process powershell -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -File `"$PSScriptRoot\open_firewall_lan.ps1`" -FrontendPort $FrontendPort -BackendPort $BackendPort"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " REMOTE TEST MODE: $Mode" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($Mode -eq 'lan') {
  & "$PSScriptRoot\print_lan_urls.ps1" -FrontendPort $FrontendPort -BackendPort $BackendPort
  Write-Host "Open 3 terminals:" -ForegroundColor White
  Write-Host "  1) .\scripts\qa_start_backend.ps1 -Port $BackendPort"
  Write-Host "  2) .\scripts\qa_start_frontend.ps1 -Port $FrontendPort"
  Write-Host "  3) (optional) .\scripts\qa_verify_lan.ps1"
  Write-Host ""
  Write-Host "PHONE URL: http://LAN_IP:$FrontendPort/login" -ForegroundColor Green
  Write-Host "LAPTOP:    http://localhost:$FrontendPort/doctor/dashboard" -ForegroundColor Yellow
} else {
  Write-Host "TUNNEL mode — patient can use Orange mobile data / any network." -ForegroundColor Green
  Write-Host ""
  Write-Host "Open 3 terminals IN ORDER:" -ForegroundColor White
  Write-Host ""
  Write-Host "  Terminal 1 — Backend (local only, proxied by Vite):" -ForegroundColor Yellow
  Write-Host "    .\scripts\qa_start_backend.ps1 -Port $BackendPort"
  Write-Host "    (or: .\scripts\run_local_backend.ps1 -Port $BackendPort)"
  Write-Host ""
  Write-Host "  Terminal 2 — Frontend (tunnel + proxy):" -ForegroundColor Yellow
  Write-Host "    cd frontend-sante\frontend"
  Write-Host "    npm run dev:tunnel"
  Write-Host ""
  Write-Host "  Terminal 3 — Public HTTPS URL for phone (APP):" -ForegroundColor Yellow
  Write-Host "    .\scripts\tunnel\start-cloudflared.ps1 -FrontendPort $FrontendPort"
  Write-Host ""
  Write-Host "  Terminal 4 — Jitsi Docker (video):" -ForegroundColor Yellow
  Write-Host "    .\scripts\start_jitsi_dev.ps1"
  Write-Host ""
  Write-Host "  Terminal 5 — Public HTTPS URL for Jitsi (port 8443):" -ForegroundColor Yellow
  Write-Host "    .\scripts\tunnel\start-jitsi-cloudflared.ps1"
  Write-Host "    .\scripts\apply_jitsi_tunnel_domain.ps1 -TunnelUrl https://JITSI-XXX.trycloudflare.com"
  Write-Host "    Then RESTART terminals 1 and 2."
  Write-Host ""
  Write-Host "LAPTOP doctor:  http://localhost:$FrontendPort/login" -ForegroundColor Cyan
  Write-Host "PHONE patient:  https://XXXX.trycloudflare.com/login  (from terminal 3)" -ForegroundColor Green
  Write-Host ""
  Write-Host "Teleconsult GO/NO GO: docs\TELECONSULT_REAL_CALL_PROCEDURE.md" -ForegroundColor Magenta
  Write-Host ""
  Write-Host "Set ENABLE_TUNNEL_TEST=true on backend if you disable Vite proxy." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Full guide: deploy\REAL_NETWORK_TEST.md" -ForegroundColor White
Write-Host ""
