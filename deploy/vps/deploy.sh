#!/usr/bin/env bash
# Production deploy / update on VPS
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [ ! -f .env.production ]; then
  echo "Copy .env.production.example to .env.production and edit secrets."
  exit 1
fi

if [ ! -f deploy/env/.env.backend ]; then
  cp deploy/env/.env.backend.example deploy/env/.env.backend
  echo "Created deploy/env/.env.backend — edit before production traffic."
fi

set -a
# shellcheck disable=SC1091
source .env.production
set +a

if [ -f deploy/nginx/conf.d/app.conf.template ] && [ -n "${DOMAIN:-}" ]; then
  export DOMAIN
  envsubst '${DOMAIN}' < deploy/nginx/conf.d/app.conf.template > deploy/nginx/conf.d/app.conf
fi

docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production build
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d

echo ""
echo "Stack status:"
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

echo ""
echo "Health:"
curl -fsS "https://${DOMAIN}/api/health" || curl -fsS "http://127.0.0.1/api/health" || true

echo ""
echo "Done. App: https://${DOMAIN}"
