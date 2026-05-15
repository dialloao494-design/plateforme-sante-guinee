#!/usr/bin/env bash
# Staging deploy on Ubuntu 22.04 VPS (HTTPS subdomain)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [ ! -f .env.staging ]; then
  echo "Copy .env.staging.example to .env.staging and configure DOMAIN + secrets."
  exit 1
fi

if [ ! -f deploy/env/.env.backend ]; then
  cp deploy/env/.env.backend.example deploy/env/.env.backend
  echo "Edit deploy/env/.env.backend — set ENVIRONMENT=staging and secrets."
fi

set -a
# shellcheck disable=SC1091
source .env.staging
set +a

export DOMAIN
if [ -f deploy/nginx/conf.d/app.conf.template ]; then
  envsubst '${DOMAIN}' < deploy/nginx/conf.d/app.conf.template > deploy/nginx/conf.d/app.conf
fi

# First-time SSL (skip if certs exist)
if [ ! -d "certbot/conf/live/${DOMAIN}" ]; then
  echo "Run deploy/vps/init-ssl.sh for first certificate, or use HTTP-only compose for smoke test."
fi

docker compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging build
docker compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging up -d

echo ""
docker compose -f docker-compose.yml -f docker-compose.staging.yml ps
echo ""
curl -fsS "https://${DOMAIN}/api/health" && echo "" || curl -fsS "http://127.0.0.1/api/health" && echo ""
echo "Staging: https://${DOMAIN}"
