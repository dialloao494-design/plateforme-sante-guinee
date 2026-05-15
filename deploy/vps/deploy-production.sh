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

# Production safety checks
if [ "${ENABLE_PILOT_SEED:-true}" = "true" ]; then
  echo "WARNING: ENABLE_PILOT_SEED=true — set false after initial bootstrap for public production."
fi

export DOMAIN
envsubst '${DOMAIN}' < deploy/nginx/conf.d/app.conf.template > deploy/nginx/conf.d/app.conf

# Ensure backend env is production
grep -q '^ENVIRONMENT=production' deploy/env/.env.backend || {
  echo "Set ENVIRONMENT=production in deploy/env/.env.backend"
  exit 1
}

docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production build
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d

echo ""
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
curl -fsS "https://${DOMAIN}/api/health"
echo ""
echo "Production live: https://${DOMAIN}"
