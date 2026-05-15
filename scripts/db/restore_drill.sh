#!/usr/bin/env bash
# Restore drill into a temporary database inside the same Postgres container (non-destructive to prod DB).
# Usage: ./scripts/db/restore_drill.sh backups/sante_YYYYMMDD.sql.gz
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

BACKUP_FILE="${1:-}"
if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
  echo "Usage: $0 <path-to-backup.sql.gz>"
  exit 1
fi

ENV_FILE=".env.production"
[ -f .env.staging ] && ENV_FILE=".env.staging"

set -a
# shellcheck disable=SC1091
source "$ENV_FILE"
set +a

DRILL_DB="${POSTGRES_DB}_restore_drill"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"

echo "Creating drill database ${DRILL_DB} ..."
docker compose $COMPOSE_FILES exec -T db psql -U "${POSTGRES_USER:-sante}" -d postgres -c \
  "DROP DATABASE IF EXISTS ${DRILL_DB}; CREATE DATABASE ${DRILL_DB};"

echo "Restoring into ${DRILL_DB} ..."
gunzip -c "$BACKUP_FILE" | docker compose $COMPOSE_FILES exec -T db \
  psql -U "${POSTGRES_USER:-sante}" -d "$DRILL_DB"

echo "Row counts:"
docker compose $COMPOSE_FILES exec -T db psql -U "${POSTGRES_USER:-sante}" -d "$DRILL_DB" -c \
  "SELECT 'users' AS t, COUNT(*) FROM users UNION ALL SELECT 'rendezvous', COUNT(*) FROM rendezvous;"

echo "Dropping drill database..."
docker compose $COMPOSE_FILES exec -T db psql -U "${POSTGRES_USER:-sante}" -d postgres -c \
  "DROP DATABASE ${DRILL_DB};"

echo "Restore drill completed successfully."
