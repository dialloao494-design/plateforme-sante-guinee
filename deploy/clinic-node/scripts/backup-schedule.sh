#!/usr/bin/env bash
# Scheduled Clinic Node backup + verify + retention (cron-friendly).
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
NODE_DIR="${ROOT_DIR}/deploy/clinic-node"
set -a; source "${NODE_DIR}/.env"; set +a
HTTPS_PORT="${HTTPS_PORT:-8443}"
BASE="https://127.0.0.1:${HTTPS_PORT}"
LOG_DIR="${NODE_DIR}/data/logs"
mkdir -p "${LOG_DIR}" "${NODE_DIR}/data/backups"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="${LOG_DIR}/backup-schedule-${STAMP}.log"

ADMIN_EMAIL="$(grep '^CLINIC_NODE_ADMIN_EMAIL=' "${NODE_DIR}/.env" | cut -d= -f2- | tr -d '"')"
ADMIN_PASSWORD="$(grep '^CLINIC_NODE_ADMIN_PASSWORD=' "${NODE_DIR}/.env" | cut -d= -f2- | tr -d '"')"

{
  echo "[backup-schedule] ${STAMP}"
  LOGIN="$(curl -kfsS -X POST "${BASE}/api/auth/login-json" -H 'Content-Type: application/json' \
    -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}")"
  TOKEN="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])' <<<"${LOGIN}")"
  BAK="$(curl -kfsS -X POST "${BASE}/api/clinic-node/backup/run" -H "Authorization: Bearer ${TOKEN}")"
  echo "${BAK}"
  python3 - <<PY
import json,sys
d=json.loads('''${BAK}''')
assert d.get("ok") and d.get("verified") and d.get("bytes",0)>=200, d
print("BACKUP_SCHEDULE_OK", d["path"], d["sha256"][:16])
PY
} | tee "${LOG}"
