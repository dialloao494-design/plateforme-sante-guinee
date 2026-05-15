#!/usr/bin/env bash
# Minimal PostgreSQL backup (daily cron: 0 3 * * * /opt/plateforme-sante/deploy/vps/backup-db.sh)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
mkdir -p "$BACKUP_DIR"

set -a
# shellcheck disable=SC1091
source .env.production 2>/dev/null || true
set +a

STAMP="$(date +%Y%m%d_%H%M%S)"
FILE="$BACKUP_DIR/sante_${STAMP}.sql.gz"

docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
  pg_dump -U "${POSTGRES_USER:-sante}" "${POSTGRES_DB:-sante}" | gzip > "$FILE"

find "$BACKUP_DIR" -name 'sante_*.sql.gz' -mtime +14 -delete

echo "Backup written: $FILE"
