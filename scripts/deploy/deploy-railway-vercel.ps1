# Deploy plateforme-sante-guinee to Railway (backend) + Vercel (frontend)
# Requires: npm, RAILWAY_TOKEN, VERCEL_TOKEN (or interactive login)
param(
  [string]$RailwayProjectId = $env:RAILWAY_PROJECT_ID,
  [string]$RailwayServiceId = $env:RAILWAY_SERVICE_ID,
  [string]$VercelProjectId = $env:VERCEL_PROJECT_ID,
  [string]$VercelOrgId = $env:VERCEL_ORG_ID,
  [string]$BackendUrl = $env:RAILWAY_BACKEND_URL
)

$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $Root

Write-Host "=== Generate staging secrets ===" -ForegroundColor Cyan
python scripts/deploy/generate_deploy_secrets.py

Write-Host "`n=== Install CLIs ===" -ForegroundColor Cyan
npm install -g @railway/cli@4.5.4 vercel@41.4.4

if (-not $env:RAILWAY_TOKEN) {
  Write-Host "RAILWAY_TOKEN not set — run: railway login" -ForegroundColor Yellow
  railway login
}

Write-Host "`n=== Deploy Railway backend ===" -ForegroundColor Cyan
if ($RailwayProjectId) {
  railway link $RailwayProjectId --environment production
}
railway up --detach
if ($RailwayServiceId) {
  railway run --service $RailwayServiceId python scripts/deploy/staging_e2e_seed.py
} else {
  railway run python scripts/deploy/staging_e2e_seed.py
}

if (-not $BackendUrl) {
  $BackendUrl = (railway domain 2>$null | Select-Object -Last 1)
}
Write-Host "Backend URL: $BackendUrl" -ForegroundColor Green

Write-Host "`n=== Deploy Vercel frontend ===" -ForegroundColor Cyan
Push-Location frontend-sante/frontend
if (-not $env:VERCEL_TOKEN) {
  Write-Host "VERCEL_TOKEN not set — run: vercel login" -ForegroundColor Yellow
  vercel login
}
$env:VITE_API_URL = $BackendUrl
$env:VITE_TELECONSULT_PROVIDER = "jitsi"
vercel --prod --yes
Pop-Location

Write-Host "`n=== Smoke test ===" -ForegroundColor Cyan
python scripts/deploy/post_deploy_verify.py --backend $BackendUrl

Write-Host "`nDone. Set FRONTEND_PRODUCTION_URL on Railway to your Vercel URL." -ForegroundColor Green
