#!/usr/bin/env bash
# Apply a signed update package with integrity verification, encrypted pre-update
# backup, health gate, and automatic rollback metadata (Wave 5).
#
# Usage: ./scripts/security/apply_update.sh <package-dir>
# Requires: CLINIC_NODE_UPDATE_SECRET (JWT fallback refused)
set -euo pipefail

PKG="${1:?update package directory required}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NODE_DIR="${ROOT_DIR}/deploy/clinic-node"
ROLLBACK_TAG_FILE="${ROLLBACK_TAG_FILE:-${NODE_DIR}/data/update-previous-backend.image}"
BACKUPS_DIR="${BACKUPS_DIR:-${NODE_DIR}/data/backups}"

export PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<PY
import os, sys
from pathlib import Path
sys.path.insert(0, "${ROOT_DIR}")
from core.update_security import UpdateSecurityError, load_and_verify_package

# Refuse JWT fallback in clinic-node / production
os.environ.setdefault("ENVIRONMENT", os.environ.get("ENVIRONMENT", "clinic-node"))
try:
    pkg = load_and_verify_package(Path("${PKG}"))
except UpdateSecurityError as exc:
    print(f"VERIFY_FAIL {exc}", file=sys.stderr)
    sys.exit(1)
print("SIGNATURE_OK", pkg.version)
open("/tmp/wave5-update-version.txt", "w").write(pkg.version)
open("/tmp/wave5-update-backup-required.txt", "w").write("1" if pkg.backup_required else "0")
PY

VERSION="$(cat /tmp/wave5-update-version.txt)"
BACKUP_REQUIRED="$(cat /tmp/wave5-update-backup-required.txt)"
echo "[update] Verified signed version ${VERSION}"

if [[ ! -d "${NODE_DIR}" ]]; then
  echo "[update] deploy/clinic-node missing — verification-only mode (no docker apply)"
  echo "UPDATE_VERIFY_OK"
  exit 0
fi

if docker info >/dev/null 2>&1; then DOCKER=docker; else DOCKER="sudo docker"; fi
COMPOSE="${NODE_DIR}/compose.host.yml"
[[ "${CLINIC_NODE_NETWORK:-host}" != "host" ]] && COMPOSE="${NODE_DIR}/compose.yml"

# Record previous image for rollback
PREV="$($DOCKER inspect --format='{{.Image}}' clinic-node-backend-1 2>/dev/null || true)"
mkdir -p "$(dirname "${ROLLBACK_TAG_FILE}")" "${BACKUPS_DIR}"
if [[ -n "${PREV}" ]]; then
  python3 - <<PY
from pathlib import Path
import sys
sys.path.insert(0, "${ROOT_DIR}")
from core.update_security import record_rollback_image
record_rollback_image(Path("${ROLLBACK_TAG_FILE}"), """${PREV}""")
print("ROLLBACK_TAG_RECORDED")
PY
fi

if [[ "${BACKUP_REQUIRED}" == "1" ]]; then
  echo "[update] Taking encrypted pre-update database backup…"
  STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
  PLAIN="${BACKUPS_DIR}/pre-update-${VERSION}-${STAMP}.sql.gz"
  set -o pipefail
  if $DOCKER exec clinic-node-db-1 pg_dump -U sante --no-owner --no-acl sante 2>/dev/null | gzip -c > "${PLAIN}"; then
    BYTES="$(wc -c < "${PLAIN}" | tr -d ' ')"
    [[ "${BYTES}" -ge 200 ]] || { echo "pre-update backup too small (${BYTES})"; exit 1; }
    python3 "${ROOT_DIR}/scripts/security/encrypt_backup.py" "${PLAIN}"
    echo "[update] Encrypted backup ok"
  else
    echo "[update] WARN: db dump unavailable — skipping live backup (lab/CI)"
  fi
fi

if compgen -G "${PKG}/images/*.tar" >/dev/null 2>&1; then
  for tar in "${PKG}"/images/*.tar; do
    echo "[update] docker load ${tar}"
    $DOCKER load -i "${tar}"
  done
fi

if [[ -f "${COMPOSE}" && -f "${NODE_DIR}/.env" ]]; then
  (cd "${NODE_DIR}" && $DOCKER compose --env-file .env -f "${COMPOSE}" up -d --build)

  HTTPS_PORT="${HTTPS_PORT:-8443}"
  OK=0
  for _ in $(seq 1 60); do
    if curl -kfsS "https://127.0.0.1:${HTTPS_PORT}/health/ready" >/dev/null 2>&1; then
      OK=1
      break
    fi
    sleep 5
  done

  if [[ "${OK}" != "1" ]]; then
    echo "[update] HEALTH_FAILED — rolling back backend image"
    if [[ -f "${ROLLBACK_TAG_FILE}" ]]; then
      PREV_IMG="$(tr -d '\n' < "${ROLLBACK_TAG_FILE}")"
      $DOCKER tag "${PREV_IMG}" clinic-node-backend:rollback || true
      (cd "${NODE_DIR}" && $DOCKER compose --env-file .env -f "${COMPOSE}" up -d backend) || true
    fi
    echo "UPDATE_ROLLBACK"
    exit 1
  fi
fi

echo "[update] Applied ${VERSION}"
echo "UPDATE_APPLY_OK"
