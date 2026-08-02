#!/usr/bin/env bash
# Repair demo IP deploy when nginx cannot reach backend:8000
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

VPS_IP="${VPS_IP:-158.220.83.42}"
ENV_FILE="${ENV_FILE:-.env.vps-ip}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE — run deploy/vps/deploy-demo-ip.sh first"
  exit 1
fi

# Docker Compose substitutes ${POSTGRES_PASSWORD} from project-root .env
cp -f "$ENV_FILE" .env
set -a
# shellcheck disable=SC1091
source "$ENV_FILE"
set +a

echo "=== Fix backend demo (IP=${VPS_IP}) ==="
echo "Using POSTGRES_PASSWORD from ${ENV_FILE}"

# Regenerate backend secrets if missing (keep DB password unchanged)
if [ ! -f deploy/env/.env.backend ]; then
  echo "Recreating deploy/env/.env.backend"
  JWT_SECRET="$(openssl rand -hex 32)"
  JITSI_SECRET="$(openssl rand -base64 32 | tr -d '\n')"
  STRIPE_DEMO="sk_test_$(openssl rand -hex 16)"
  mkdir -p deploy/env
  cat > deploy/env/.env.backend <<EOF
ENVIRONMENT=staging
DEBUG=false
ENABLE_PILOT_SEED=true
ENABLE_STAGING_API_DOCS=true
ALLOW_STUB_PAYMENT=true
BYPASS_AVAILABILITY_VALIDATION=false
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
fi

docker compose --env-file "$ENV_FILE" down
docker compose --env-file "$ENV_FILE" up -d --build

echo "Waiting for backend health..."
for i in $(seq 1 60); do
  if docker compose --env-file "$ENV_FILE" exec -T backend curl -fsS http://127.0.0.1:8000/health/ready >/dev/null 2>&1; then
    echo "Backend ready (${i})"
    break
  fi
  sleep 5
  if [ "$i" -eq 60 ]; then
    echo "Backend still down — logs:"
    docker compose --env-file "$ENV_FILE" logs backend --tail 60
    exit 1
  fi
done

docker compose --env-file "$ENV_FILE" exec -T backend python scripts/pilot_provision_demo.py || true

echo "=== Tests ==="
docker compose --env-file "$ENV_FILE" exec -T nginx wget -qO- http://backend:8000/health || \
  docker compose --env-file "$ENV_FILE" exec -T backend curl -fsS http://127.0.0.1:8000/health
echo ""
curl -fsS "http://127.0.0.1/api/health"
echo ""
curl -fsS -X POST "http://127.0.0.1/api/auth/login-json" \
  -H "Content-Type: application/json" \
  -d '{"email":"dr.mamady@example.com","password":"DoctorPilot123!"}' | head -c 200
echo ""
echo "OK — http://${VPS_IP}"
