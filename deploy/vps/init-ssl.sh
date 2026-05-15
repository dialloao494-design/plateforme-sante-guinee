#!/usr/bin/env bash
# First-time Let's Encrypt certificate (run on VPS after DNS points to server)
# Usage:
#   Production: bash deploy/vps/init-ssl.sh
#   Staging:    bash deploy/vps/init-ssl-staging.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE_EXTRA="${COMPOSE_EXTRA:- -f docker-compose.prod.yml}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE — copy from the matching .example file"
  exit 1
fi

set -a
# shellcheck disable=SC1091
source "$ENV_FILE"
set +a

: "${DOMAIN:?Set DOMAIN in $ENV_FILE}"
: "${CERTBOT_EMAIL:?Set CERTBOT_EMAIL in $ENV_FILE}"

mkdir -p deploy/nginx/conf.d certbot/www

COMPOSE_CMD="docker compose -f docker-compose.yml ${COMPOSE_EXTRA} --env-file ${ENV_FILE}"

$COMPOSE_CMD up -d db backend frontend

docker run --rm \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d "$DOMAIN" --email "$CERTBOT_EMAIL" --agree-tos --no-eff-email

export DOMAIN
envsubst '${DOMAIN}' < deploy/nginx/conf.d/app.conf.template > deploy/nginx/conf.d/app.conf

$COMPOSE_CMD up -d

echo "SSL initialized for https://${DOMAIN}"
