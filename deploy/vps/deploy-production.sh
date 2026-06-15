#!/usr/bin/env bash
# Final production deploy (after staging sign-off)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [ ! -f .env.production ]; then
  echo "Copy .env.production.example to .env.production"
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env.production
set +a

: "${DOMAIN:?Set DOMAIN in .env.production}"
: "${SECRET_KEY:?Set SECRET_KEY in .env.production}"
: "${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in .env.production}"
: "${TRUSTED_PROXY_HOSTS:?Set TRUSTED_PROXY_HOSTS in .env.production (e.g. 127.0.0.1,backend)}"
: "${REMINDER_RESPOND_TOKEN:?Set REMINDER_RESPOND_TOKEN in .env.production (openssl rand -hex 32)}"

if [ "${ENABLE_PILOT_SEED:-false}" = "true" ]; then
  echo "ERROR: ENABLE_PILOT_SEED must be false for production deploy."
  exit 1
fi

# Sync security-critical vars into compose env_file
mkdir -p deploy/env
BACKEND_ENV="deploy/env/.env.backend"
if [ ! -f "$BACKEND_ENV" ]; then
  cp deploy/env/.env.backend.example "$BACKEND_ENV"
fi

upsert_env() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" "$BACKEND_ENV" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$BACKEND_ENV"
  else
    echo "${key}=${value}" >> "$BACKEND_ENV"
  fi
}

upsert_env ENVIRONMENT production
upsert_env DEBUG false
upsert_env DOMAIN "${DOMAIN}"
upsert_env ALLOWED_HOSTS "${ALLOWED_HOSTS:-${DOMAIN},backend}"
upsert_env TRUSTED_PROXY_HOSTS "${TRUSTED_PROXY_HOSTS}"
upsert_env REMINDER_RESPOND_TOKEN "${REMINDER_RESPOND_TOKEN}"
upsert_env SECRET_KEY "${SECRET_KEY}"
upsert_env ENABLE_PILOT_SEED false
upsert_env ENABLE_STARTUP_TEST_USER false
upsert_env ENABLE_STARTUP_SEED false
upsert_env ENABLE_DEMO_CLINIC_SEED false
upsert_env BYPASS_AVAILABILITY_VALIDATION false
chmod 600 "$BACKEND_ENV"

export DOMAIN
envsubst '${DOMAIN}' < deploy/nginx/conf.d/app.conf.template > deploy/nginx/conf.d/app.conf

docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production build
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d

echo ""
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
curl -fsS "https://${DOMAIN}/api/health"
echo ""
echo "Production live: https://${DOMAIN}"
