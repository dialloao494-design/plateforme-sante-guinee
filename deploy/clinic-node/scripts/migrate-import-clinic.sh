#!/usr/bin/env bash
# Phase 5 — import migration SQL into local Clinic Node Postgres (freeze/cutover helper).
# Usage:
#   ./deploy/clinic-node/scripts/migrate-import-clinic.sh /path/to/export.sgmig.sql
set -euo pipefail
IN="${1:?input sql file required}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
NODE_DIR="${ROOT_DIR}/deploy/clinic-node"

echo "[migrate-import] Importing ${IN} into clinic-node-db-1"
# Stop API writes during import
if docker info >/dev/null 2>&1; then DOCKER=docker; else DOCKER="sudo docker"; fi
$DOCKER stop clinic-node-backend-1 >/dev/null 2>&1 || true
$DOCKER exec -i clinic-node-db-1 psql -U sante -d sante < "${IN}"
$DOCKER start clinic-node-backend-1 >/dev/null
echo "[migrate-import] restarting API and waiting for ready…"
for i in $(seq 1 36); do
  if curl -kfsS "https://127.0.0.1:${HTTPS_PORT:-8443}/health/ready" >/dev/null 2>&1 \
     || curl -fsS "http://127.0.0.1:8000/health/ready" >/dev/null 2>&1; then
    echo "MIGRATION_IMPORT_OK"
    exit 0
  fi
  sleep 5
done
echo "MIGRATION_IMPORT_API_NOT_READY" >&2
exit 1
