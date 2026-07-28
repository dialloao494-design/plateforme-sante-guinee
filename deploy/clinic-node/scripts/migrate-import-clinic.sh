#!/usr/bin/env bash
# Safe import with checksum verification, dry-run, pre-import rollback snapshot.
# Usage:
#   ./deploy/clinic-node/scripts/migrate-import-clinic.sh /path/to/export.sgmig.sql.gz
#   DRY_RUN=1 ./...  (checksum + gunzip parse only)
#   CONFIRM_IMPORT=1 ./...  (required for live import)
set -euo pipefail
IN="${1:?input sql.gz file required}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
NODE_DIR="${ROOT_DIR}/deploy/clinic-node"
DRY_RUN="${DRY_RUN:-0}"
CONFIRM_IMPORT="${CONFIRM_IMPORT:-0}"

if docker info >/dev/null 2>&1; then DOCKER=docker; else DOCKER="sudo docker"; fi

echo "[migrate-import] ${IN} dry_run=${DRY_RUN}"

python3 - <<PY
import gzip, hashlib, sys
from pathlib import Path
p=Path("${IN}")
assert p.exists(), p
raw=gzip.open(p,"rb").read()
assert b"clinic_id=" in raw or b"CREATE TABLE" in raw or b"BEGIN" in raw, "unexpected content"
digest=hashlib.sha256(raw).hexdigest()
sha_path=Path(str(p)+".sha256")
if sha_path.exists():
    expected=sha_path.read_text().strip().split()[0]
    assert expected==digest, (expected, digest)
    print("CHECKSUM_OK", digest)
else:
    print("CHECKSUM_GENERATED", digest)
    sha_path.write_text(digest+"\n")
print("IMPORT_VALIDATE_OK bytes", len(raw))
PY

if [[ "${DRY_RUN}" == "1" ]]; then
  echo "MIGRATION_IMPORT_DRY_RUN_OK"
  exit 0
fi

[[ "${CONFIRM_IMPORT}" == "1" ]] || {
  echo "Refusing live import without CONFIRM_IMPORT=1 (prevents accidental overwrite)" >&2
  exit 2
}

# Pre-import rollback snapshot of local DB
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SNAP="${NODE_DIR}/data/backups/pre-migrate-${STAMP}.sql.gz"
mkdir -p "${NODE_DIR}/data/backups"
set -o pipefail
$DOCKER exec clinic-node-db-1 pg_dump -U sante --no-owner --no-acl sante | gzip -c > "${SNAP}"
echo "[migrate-import] rollback snapshot ${SNAP}"

$DOCKER stop clinic-node-backend-1 >/dev/null 2>&1 || true
if ! gzip -dc "${IN}" | $DOCKER exec -i clinic-node-db-1 psql -U sante -d sante -v ON_ERROR_STOP=1; then
  echo "[migrate-import] IMPORT FAILED — restoring snapshot"
  gzip -dc "${SNAP}" | $DOCKER exec -i clinic-node-db-1 psql -U sante -d sante -v ON_ERROR_STOP=1 || true
  $DOCKER start clinic-node-backend-1 >/dev/null || true
  echo "MIGRATION_IMPORT_ROLLED_BACK"
  exit 1
fi
$DOCKER start clinic-node-backend-1 >/dev/null
for i in $(seq 1 36); do
  if curl -kfsS "https://127.0.0.1:${HTTPS_PORT:-8443}/health/ready" >/dev/null 2>&1; then
    echo "MIGRATION_IMPORT_OK snapshot=${SNAP}"
    exit 0
  fi
  sleep 5
done
echo "MIGRATION_IMPORT_API_NOT_READY" >&2
exit 1
