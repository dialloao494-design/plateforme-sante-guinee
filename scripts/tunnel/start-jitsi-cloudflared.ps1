# Public HTTPS URL for Jitsi (port 8443) — required for iPhone Safari embed.
# Prerequisite: Jitsi Docker running (.\scripts\start_jitsi_dev.ps1)
param(
  [string]$JitsiUrl = "https://127.0.0.1:8443"
)

$ErrorActionPreference = "Stop"
$Bundled = Join-Path $PSScriptRoot "cloudflared.exe"
$Cf = if (Test-Path $Bundled) { $Bundled } else { (Get-Command cloudflared -ErrorAction SilentlyContinue)?.Source }

if (-not $Cf) {
  Write-Host "cloudflared introuvable." -ForegroundColor Yellow
  Write-Host "  winget install Cloudflare.cloudflared"
  Write-Host "  ou placez cloudflared.exe dans scripts\tunnel\"
  exit 1
}

Write-Host ""
Write-Host "Tunnel Cloudflare → $JitsiUrl (Jitsi / port 8443)" -ForegroundColor Cyan
Write-Host "Copiez l'URL https://....trycloudflare.com puis exécutez :" -ForegroundColor Green
Write-Host "  .\scripts\apply_jitsi_tunnel_domain.ps1 -TunnelUrl https://XXXX.trycloudflare.com" -ForegroundColor White
Write-Host ""
Write-Host "Redémarrez ensuite le backend et npm run dev:tunnel." -ForegroundColor DarkGray
Write-Host ""

# Self-signed cert on local Jitsi — cloudflared must skip TLS verify to origin
& $Cf tunnel --url $JitsiUrl --no-tls-verify
