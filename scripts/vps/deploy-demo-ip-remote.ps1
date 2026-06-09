# Deploy demo HTTP on VPS IP (no domain, no HTTPS) — run from Windows PowerShell
# You will be prompted for root password twice (scp + ssh)
param(
  [string]$VpsHost = "158.220.83.42",
  [string]$VpsUser = "root",
  [string]$RemoteDir = "/opt/plateforme-sante-guinee"
)
$ErrorActionPreference = "Stop"
$VpsIp = $VpsHost

Write-Host "=== DEMO deploy http://${VpsIp} ===" -ForegroundColor Cyan
Write-Host "Enter root password when prompted." -ForegroundColor Yellow

$remoteScript = @"
set -euo pipefail
export VPS_IP='${VpsIp}'
if [ -d '${RemoteDir}/.git' ]; then
  cd '${RemoteDir}' && git pull origin main
else
  git clone https://github.com/dialloao494-design/plateforme-sante-guinee.git '${RemoteDir}'
  cd '${RemoteDir}'
fi
chmod +x deploy/vps/deploy-demo-ip.sh 2>/dev/null || true
if [ -f deploy/vps/deploy-demo-ip.sh ]; then
  VPS_IP='${VpsIp}' bash deploy/vps/deploy-demo-ip.sh
else
  # Fallback inline if script not yet on main
  PG_PASS=\$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)
  JWT=\$(openssl rand -hex 32)
  JITSI=\$(openssl rand -base64 32 | tr -d '\n')
  cat > .env.vps-ip <<EOF
DOMAIN=${VpsIp}
HTTP_PORT=80
POSTGRES_USER=sante
POSTGRES_PASSWORD=\$PG_PASS
POSTGRES_DB=sante
ENVIRONMENT=staging
ENABLE_PILOT_SEED=true
VITE_API_URL=/api
VITE_SAME_ORIGIN_API=true
VITE_TELECONSULT_PROVIDER=stub
EOF
  mkdir -p deploy/env
  cat > deploy/env/.env.backend <<EOF
ENVIRONMENT=staging
ENABLE_PILOT_SEED=true
ENABLE_STAGING_API_DOCS=true
ALLOW_STUB_PAYMENT=true
SECRET_KEY=\$JWT
ALLOWED_HOSTS=${VpsIp},backend,localhost
DOMAIN=${VpsIp}
STRIPE_SECRET_KEY=sk_test_placeholder_demo_ip
STRIPE_WEBHOOK_SECRET=whsec_placeholder_32chars_minimum
JITSI_APP_SECRET=\$JITSI
JITSI_APP_ID=plateforme-sante-guinee
FRONTEND_URL=http://${VpsIp}
CORS_ORIGINS=http://${VpsIp}
EOF
  docker compose --env-file .env.vps-ip up -d --build
  for i in \$(seq 1 40); do curl -fsS http://127.0.0.1/api/health && break; sleep 5; done
  docker compose --env-file .env.vps-ip exec -T backend alembic upgrade head || true
  docker compose --env-file .env.vps-ip exec -T backend python scripts/pilot_provision_demo.py || true
fi
curl -fsS http://127.0.0.1/api/health
echo DEMO_URL=http://${VpsIp}
"@

ssh "${VpsUser}@${VpsHost}" $remoteScript

Write-Host ""
Write-Host "DEMO: http://${VpsIp}" -ForegroundColor Green
Write-Host "Medecin: dr.mamady@example.com / Doctor123!"
Write-Host "Patient: test.patient@example.com / Patient123!"
