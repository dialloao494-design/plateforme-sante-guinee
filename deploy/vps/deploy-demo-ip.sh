#!/usr/bin/env bash
# Demo rapide HTTP via IP — sans domaine, sans HTTPS
# Usage: VPS_IP=158.220.83.42 bash deploy/vps/deploy-demo-ip.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

VPS_IP="${VPS_IP:-158.220.83.42}"

# Reuse existing DB password when re-deploying (avoids pg volume mismatch)
if [ -f .env.vps-ip ]; then
  # shellcheck disable=SC1091
  set -a; source .env.vps-ip; set +a
fi
PG_PASS="${POSTGRES_PASSWORD:-$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)}"
JWT_SECRET="${SECRET_KEY:-$(openssl rand -hex 32)}"
JITSI_SECRET="${JITSI_APP_SECRET:-$(openssl rand -base64 32 | tr -d '\n')}"
STRIPE_DEMO="sk_test_$(openssl rand -hex 16)"

echo "=== DEMO IP deploy — http://${VPS_IP} ==="

cat > .env.vps-ip <<EOF
DOMAIN=${VPS_IP}
HTTP_PORT=80
POSTGRES_USER=sante
POSTGRES_PASSWORD=${PG_PASS}
POSTGRES_DB=sante
ENVIRONMENT=staging
ENABLE_PILOT_SEED=true
BYPASS_AVAILABILITY_VALIDATION=false
VITE_API_URL=/api
VITE_SAME_ORIGIN_API=true
VITE_TELECONSULT_PROVIDER=stub
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_placeholder
EOF
chmod 600 .env.vps-ip
cp -f .env.vps-ip .env

mkdir -p deploy/env logs backups
cat > deploy/env/.env.backend <<EOF
ENVIRONMENT=staging
DEBUG=false
ENABLE_LAN_DEV=false
ENABLE_DEMO_CLINIC_SEED=false
ENABLE_STARTUP_TEST_USER=false
ENABLE_STARTUP_SEED=false
ENABLE_PILOT_SEED=true
ENABLE_STAGING_API_DOCS=true
BYPASS_AVAILABILITY_VALIDATION=false
ALLOW_STUB_PAYMENT=true
SECRET_KEY=${JWT_SECRET}
ACCESS_TOKEN_EXPIRE_MINUTES=480
ALLOWED_HOSTS=${VPS_IP},backend,localhost,127.0.0.1
DOMAIN=${VPS_IP}
STRIPE_SECRET_KEY=${STRIPE_DEMO}
STRIPE_PUBLISHABLE_KEY=pk_test_demo
STRIPE_WEBHOOK_SECRET=whsec_$(openssl rand -hex 16)
JITSI_APP_SECRET=${JITSI_SECRET}
JITSI_APP_ID=plateforme-sante-guinee
JITSI_DOMAIN=meet.jit.si
PAYMENT_STUB_TOKEN=$(openssl rand -base64 24 | tr -d '\n')
FRONTEND_URL=http://${VPS_IP}
CORS_ORIGINS=http://${VPS_IP}
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
chmod 600 deploy/env/.env.backend

docker compose --env-file .env.vps-ip up -d --build

echo "Waiting for backend..."
for i in $(seq 1 60); do
  if docker compose --env-file .env.vps-ip exec -T backend curl -fsS http://127.0.0.1:8000/health/ready >/dev/null 2>&1; then
    echo "Backend ready (${i}s)"
    break
  fi
  sleep 5
  if [ "$i" -eq 60 ]; then
    echo "Timeout — run: docker compose --env-file .env.vps-ip logs backend --tail 80"
    exit 1
  fi
done

docker compose --env-file .env.vps-ip exec -T backend alembic upgrade head || true
docker compose --env-file .env.vps-ip exec -T backend python scripts/pilot_provision_demo.py || true

curl -fsS "http://127.0.0.1/api/health"
echo ""
docker compose --env-file .env.vps-ip ps
echo ""
echo "DEMO URL: http://${VPS_IP}"
echo "Doctor: dr.mamady@example.com / Doctor123!"
echo "Patient: test.patient@example.com / Patient123!"
