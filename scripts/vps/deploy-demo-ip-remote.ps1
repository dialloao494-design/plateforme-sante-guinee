# Deploy demo HTTP on VPS IP (no domain, no HTTPS) — run from Windows PowerShell
# You will be prompted for root password (ssh)
param(
  [string]$VpsHost = "158.220.83.42",
  [string]$VpsUser = "root",
  [string]$RemoteDir = "/opt/plateforme-sante-guinee",
  [switch]$UseTar
)
$ErrorActionPreference = "Stop"
$VpsIp = $VpsHost
$RepoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent

Write-Host "=== DEMO deploy http://${VpsIp} ===" -ForegroundColor Cyan
Write-Host "Enter root password when prompted." -ForegroundColor Yellow

if ($UseTar) {
  $tar = Join-Path $env:TEMP "plateforme-sante-deploy.tgz"
  Push-Location $RepoRoot
  tar -czf $tar --exclude=.git --exclude=node_modules --exclude=frontend-sante/frontend/node_modules --exclude=__pycache__ --exclude=.venv --exclude=uploads --exclude=logs --exclude=.env --exclude=.env.vps-ip .
  Pop-Location
  scp $tar "${VpsUser}@${VpsHost}:/tmp/plateforme-sante-deploy.tgz"
  $remoteScript = @"
set -euo pipefail
export VPS_IP='${VpsIp}'
mkdir -p '${RemoteDir}'
tar -xzf /tmp/plateforme-sante-deploy.tgz -C '${RemoteDir}'
cd '${RemoteDir}'
chmod +x deploy/vps/*.sh 2>/dev/null || true
if [ -f .env.vps-ip ]; then cp -f .env.vps-ip .env; fi
if [ -f deploy/vps/fix-demo-ip-backend.sh ]; then
  VPS_IP='${VpsIp}' bash deploy/vps/fix-demo-ip-backend.sh
else
  VPS_IP='${VpsIp}' bash deploy/vps/deploy-demo-ip.sh
fi
"@
} else {
  $remoteScript = @"
set -euo pipefail
export VPS_IP='${VpsIp}'
if [ -d '${RemoteDir}/.git' ]; then
  cd '${RemoteDir}' && git pull origin main
else
  git clone https://github.com/dialloao494-design/plateforme-sante-guinee.git '${RemoteDir}'
  cd '${RemoteDir}'
fi
chmod +x deploy/vps/*.sh 2>/dev/null || true
if [ -f .env.vps-ip ]; then cp -f .env.vps-ip .env; fi
if [ -f deploy/vps/fix-demo-ip-backend.sh ]; then
  VPS_IP='${VpsIp}' bash deploy/vps/fix-demo-ip-backend.sh
else
  VPS_IP='${VpsIp}' bash deploy/vps/deploy-demo-ip.sh
fi
"@
}

ssh "${VpsUser}@${VpsHost}" $remoteScript

Write-Host ""
Write-Host "DEMO: http://${VpsIp}" -ForegroundColor Green
Write-Host "Medecin: dr.mamady@example.com / [REDACTED]"
Write-Host "Patient: test.patient@example.com / [REDACTED]"
