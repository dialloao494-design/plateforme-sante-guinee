#!/usr/bin/env bash
# PostgreSQL backup — daily cron on VPS
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.staging}"
COMPOSE_EXTRA="${COMPOSE_EXTRA:--f docker-compose.staging.yml}"

BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
mkdir -p "$BACKUP_DIR"

set -a
# shellcheck disable=SC1091
source "$ENV_FILE"
set +a

STAMP="$(date +%Y%m%d_%H%M%S)"
FILE="$BACKUP_DIR/sante_${STAMP}.sql.gz"

docker compose -f docker-compose.yml ${COMPOSE_EXTRA} --env-file "$ENV_FILE" exec -T db \
  pg_dump -U "${POSTGRES_USER:-sante}" "${POSTGRES_DB:-sante}" | gzip > "$FILE"

gzip -t "$FILE"
sha256sum "$FILE" > "${FILE}.sha256"
EVIDENCE_DIR="${BACKUP_EVIDENCE_DIR:-$ROOT/evidence/backup}"
mkdir -p "$EVIDENCE_DIR"
python3 scripts/db/backup_restore_evidence.py "$FILE" \
  --rpo-target-minutes "${BACKUP_RPO_TARGET_MINUTES:-1440}" \
  --evidence "$EVIDENCE_DIR/backup-${STAMP}.json"

find "$BACKUP_DIR" -name 'sante_*.sql.gz*' -mtime +"${BACKUP_RETENTION_DAYS:-30}" -delete

echo "Backup verified: $FILE"
echo "Checksum written: ${FILE}.sha256"
