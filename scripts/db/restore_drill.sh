#!/usr/bin/env bash
# Guarded restore drill. Never restores into the source/live database.
# Usage: VERIFICATION_DATABASE_URL=postgresql://.../sante_restore_verify \
#        ./scripts/db/restore_drill.sh backups/sante_YYYYMMDD.sql.gz
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

BACKUP_FILE="${1:-}"
if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
  echo "Usage: VERIFICATION_DATABASE_URL=.../sante_restore_verify $0 <backup.sql.gz>"
  exit 1
fi
if [ -z "${VERIFICATION_DATABASE_URL:-}" ]; then
  echo "VERIFICATION_DATABASE_URL is required and must end in _restore_verify"
  exit 1
fi

ARGS=(
  "$BACKUP_FILE"
  --verification-database-url "$VERIFICATION_DATABASE_URL"
  --rpo-target-minutes "${BACKUP_RPO_TARGET_MINUTES:-1440}"
  --rto-target-minutes "${BACKUP_RTO_TARGET_MINUTES:-60}"
  --evidence "${BACKUP_EVIDENCE_FILE:-evidence/backup/latest-restore-drill.json}"
)
if [ -n "${DATABASE_URL:-}" ]; then
  ARGS+=(--source-database-url "$DATABASE_URL")
fi
if [ "${REPLACE_VERIFICATION_DATABASE:-0}" = "1" ]; then
  ARGS+=(--replace-verification-database)
fi
if [ "${KEEP_VERIFICATION_DATABASE:-0}" = "1" ]; then
  ARGS+=(--keep-verification-database)
fi

exec python3 scripts/db/backup_restore_evidence.py "${ARGS[@]}"
