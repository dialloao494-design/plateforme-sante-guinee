#!/usr/bin/env bash
# One-shot autonomous VPS bootstrap — Ubuntu 22.04+
# Usage (on VPS as root or sudo user):
#   DOMAIN=sante.example.gn CERTBOT_EMAIL=admin@example.gn bash deploy/vps/bootstrap-autonomous.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

: "${DOMAIN:?Set DOMAIN (e.g. sante.example.gn)}"
: "${CERTBOT_EMAIL:?Set CERTBOT_EMAIL for Let's Encrypt}"

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging"
INSTALL_DIR="${INSTALL_DIR:-/opt/plateforme-sante-guinee}"

echo "=== Plateforme Santé — bootstrap autonome ==="
echo "Domain: $DOMAIN"
echo "Install: $INSTALL_DIR"

# --- Docker ---
if ! command -v docker >/dev/null 2>&1; then
  echo "[1/8] Installing Docker..."
  bash deploy/vps/install-docker.sh
else
  echo "[1/8] Docker already installed: $(docker --version)"
fi

# --- Secrets / env files ---
echo "[2/8] Generating .env.staging and deploy/env/.env.backend..."
PG_PASS="${POSTGRES_PASSWORD:-$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)}"
JWT_SECRET="${SECRET_KEY:-$(openssl rand -hex 32)}"
REMINDER_TOKEN="${REMINDER_RESPOND_TOKEN:-$(openssl rand -hex 32)}"
TRUSTED_PROXIES="${TRUSTED_PROXY_HOSTS:-127.0.0.1,backend}"
PUBLIC_URL="https://${DOMAIN}"

cat > .env.staging <<EOF
DOMAIN=${DOMAIN}
HTTP_PORT=80

POSTGRES_USER=sante
POSTGRES_PASSWORD=${PG_PASS}
POSTGRES_DB=sante

ENVIRONMENT=staging
ENABLE_PILOT_SEED=true
ALLOWED_HOSTS=${DOMAIN},backend
TRUSTED_PROXY_HOSTS=${TRUSTED_PROXIES}
REMINDER_RESPOND_TOKEN=${REMINDER_TOKEN}

VITE_API_URL=/api
VITE_SAME_ORIGIN_API=true
VITE_TELECONSULT_PROVIDER=jitsi
VITE_STRIPE_PUBLISHABLE_KEY=${VITE_STRIPE_PUBLISHABLE_KEY:-pk_test_placeholder}

CERTBOT_EMAIL=${CERTBOT_EMAIL}
EOF
chmod 600 .env.staging

mkdir -p deploy/env
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
ACCESS_TOKEN_EXPIRE_MINUTES=60
ALLOWED_HOSTS=${DOMAIN},backend
DOMAIN=${DOMAIN}
TRUSTED_PROXY_HOSTS=${TRUSTED_PROXIES}
REMINDER_RESPOND_TOKEN=${REMINDER_TOKEN}

STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY:-sk_test_placeholder}
STRIPE_PUBLISHABLE_KEY=${STRIPE_PUBLISHABLE_KEY:-pk_test_placeholder}
STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET:-whsec_placeholder_32chars_min}

JITSI_APP_SECRET=${JITSI_APP_SECRET:-$(openssl rand -base64 32 | tr -d '\n')}
JITSI_APP_ID=plateforme-sante-guinee
JITSI_DOMAIN=meet.jit.si

PAYMENT_STUB_TOKEN=${PAYMENT_STUB_TOKEN:-$(openssl rand -base64 24 | tr -d '\n')}
FRONTEND_URL=${PUBLIC_URL}
CORS_ORIGINS=${PUBLIC_URL}

LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
chmod 600 deploy/env/.env.backend

# --- SSL init ---
echo "[3/8] Preparing nginx + certbot directories..."
mkdir -p certbot/www certbot/conf deploy/nginx/conf.d
export DOMAIN
envsubst '${DOMAIN}' < deploy/nginx/conf.d/app.conf.init.template > deploy/nginx/conf.d/app.conf

echo "[4/8] Building and starting stack (HTTP bootstrap)..."
$COMPOSE build
$COMPOSE up -d db
$COMPOSE up -d backend frontend
sleep 5
$COMPOSE up -d nginx

echo "[5/8] Obtaining Let's Encrypt certificate..."
if [ ! -d "certbot/conf/live/${DOMAIN}" ]; then
  docker run --rm \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
    certbot/certbot certonly --webroot -w /var/www/certbot \
    -d "$DOMAIN" --email "$CERTBOT_EMAIL" --agree-tos --no-eff-email --non-interactive
else
  echo "Certificate already exists for ${DOMAIN}"
fi

envsubst '${DOMAIN}' < deploy/nginx/conf.d/app.conf.template > deploy/nginx/conf.d/app.conf

echo "[6/8] Starting full HTTPS stack..."
$COMPOSE up -d --build

echo "[7/8] Waiting for backend health..."
for i in $(seq 1 30); do
  if curl -fsS "https://${DOMAIN}/api/health" >/dev/null 2>&1; then
    echo "Backend healthy on attempt $i"
    break
  fi
  sleep 5
  if [ "$i" -eq 30 ]; then
    echo "WARNING: health check timeout — inspect: $COMPOSE logs backend"
  fi
done

echo "[8/8] Provisioning demo data + systemd + backups..."
$COMPOSE exec -T backend python scripts/pilot_provision_demo.py 2>/dev/null || true

# systemd — auto-start Docker stack on reboot
if [ -d /etc/systemd/system ]; then
  sed "s|/opt/plateforme-sante-guinee|${ROOT}|g" deploy/vps/plateforme-sante.service | \
    sed 's|docker-compose.staging.yml|docker-compose.staging.yml|' > /tmp/plateforme-sante.service
  sudo cp /tmp/plateforme-sante.service /etc/systemd/system/plateforme-sante.service
  sudo systemctl daemon-reload
  sudo systemctl enable plateforme-sante.service
  echo "systemd unit enabled: plateforme-sante.service"
fi

# Daily PostgreSQL backup (03:00 UTC)
BACKUP_CRON="0 3 * * * cd ${ROOT} && ENV_FILE=.env.staging COMPOSE_EXTRA='-f docker-compose.staging.yml' bash deploy/vps/backup-db.sh >> ${ROOT}/logs/backup.log 2>&1"
( crontab -l 2>/dev/null | grep -v 'deploy/vps/backup-db.sh'; echo "$BACKUP_CRON" ) | crontab -
mkdir -p "${ROOT}/logs" "${ROOT}/backups"
echo "Cron backup installed (daily 03:00 UTC)"

echo ""
echo "=== DEPLOY COMPLETE ==="
echo "URL: https://${DOMAIN}"
echo "API: https://${DOMAIN}/api/health"
$COMPOSE ps
echo ""
echo "Run validation: VPS_API_BASE=https://${DOMAIN}/api python3 scripts/vps_autonomous_verify.py"
