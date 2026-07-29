#!/usr/bin/env bash
# Restore drill — verify backup integrity and optionally restore into a throwaway DB.
# Usage:
#   ./deploy/clinic-node/scripts/restore-drill.sh /path/to/backup.sql.gz
#   RESTORE_LIVE=1 ./deploy/clinic-node/scripts/restore-drill.sh /path/to/backup.sql.gz
set -euo pipefail
BACKUP="${1:?backup .sql.gz path required}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
NODE_DIR="${ROOT_DIR}/deploy/clinic-node"

if docker info >/dev/null 2>&1; then DOCKER=docker; else DOCKER="sudo docker"; fi

echo "[restore-drill] verifying ${BACKUP}"
python3 - <<PY
import gzip, hashlib, sys
from pathlib import Path
p=Path("${BACKUP}")
assert p.exists(), p
data=p.read_bytes()
assert len(data)>=200, len(data)
with gzip.open(p,"rb") as g:
    chunk=g.read(65536)
    assert chunk, "empty"
    while g.read(1024*1024):
        pass
h=hashlib.sha256(data).hexdigest()
print("VERIFY_OK", h, len(data))
open("/tmp/clinic-node-restore-sha256.txt","w").write(h)
PY

if [[ "${RESTORE_LIVE:-0}" != "1" ]]; then
  # Spin ephemeral postgres for restore proof without touching live data
  NAME="clinic-node-restore-drill"
  $DOCKER rm -f "${NAME}" >/dev/null 2>&1 || true
  $DOCKER run -d --name "${NAME}" -e POSTGRES_PASSWORD=drill -e POSTGRES_USER=sante -e POSTGRES_DB=sante_restore postgres:16-alpine >/dev/null
  for i in $(seq 1 30); do
    $DOCKER exec "${NAME}" pg_isready -U sante >/dev/null 2>&1 && break
    sleep 1
  done
  set -o pipefail
  gzip -dc "${BACKUP}" | $DOCKER exec -i "${NAME}" psql -U sante -d sante_restore -v ON_ERROR_STOP=1 >/tmp/clinic-node-restore-drill.log 2>&1 \
    || { echo "RESTORE_DRILL_FAIL"; tail -50 /tmp/clinic-node-restore-drill.log; $DOCKER rm -f "${NAME}" >/dev/null; exit 1; }
  TABLES="$($DOCKER exec "${NAME}" psql -U sante -d sante_restore -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")"
  $DOCKER rm -f "${NAME}" >/dev/null
  [[ "${TABLES}" -gt 5 ]] || { echo "RESTORE_DRILL_TOO_FEW_TABLES ${TABLES}"; exit 1; }
  echo "RESTORE_DRILL_OK tables=${TABLES}"
  exit 0
fi

echo "[restore-drill] LIVE restore requested — stopping API"
$DOCKER stop clinic-node-backend-1 >/dev/null
set -o pipefail
gzip -dc "${BACKUP}" | $DOCKER exec -i clinic-node-db-1 psql -U sante -d sante -v ON_ERROR_STOP=1
$DOCKER start clinic-node-backend-1 >/dev/null
echo "RESTORE_LIVE_OK"
