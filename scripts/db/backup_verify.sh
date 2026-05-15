#!/usr/bin/env bash
# Create a backup and verify the gzip archive is readable (dry-run restore check).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [ ! -f .env.production ] && [ ! -f .env.staging ]; then
  echo "Missing .env.production or .env.staging"
  exit 1
fi

ENV_FILE=".env.production"
[ -f .env.staging ] && ENV_FILE=".env.staging"

set -a
# shellcheck disable=SC1091
source "$ENV_FILE"
set +a

COMPOSE_FILES="-f docker-compose.yml"
if [ -f docker-compose.prod.yml ] && [ "${ENVIRONMENT:-}" = "production" ]; then
  COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.prod.yml"
fi
if [ -f docker-compose.staging.yml ] && [ "${ENVIRONMENT:-}" = "staging" ]; then
  COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.staging.yml"
fi

BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
FILE="$BACKUP_DIR/verify_${STAMP}.sql.gz"

echo "Creating backup $FILE ..."
docker compose $COMPOSE_FILES exec -T db \
  pg_dump -U "${POSTGRES_USER:-sante}" "${POSTGRES_DB:-sante}" | gzip > "$FILE"

echo "Verifying gzip integrity..."
gzip -t "$FILE"

echo "Listing SQL header (first 20 lines)..."
gunzip -c "$FILE" | head -n 20

echo "Backup verification OK: $FILE"
