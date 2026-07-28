#!/usr/bin/env bash
# Phase 4 — apply a signed update package directory (rebuild + restart).
# Package layout:
#   update/manifest.json  {"version":"1.0.1","backup_required":true}
#   update/images/*.tar   optional docker images
set -euo pipefail
PKG="${1:?update package directory required}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
NODE_DIR="${ROOT_DIR}/deploy/clinic-node"
MANIFEST="${PKG}/manifest.json"

[[ -f "${MANIFEST}" ]] || { echo "manifest.json missing"; exit 1; }
VERSION="$(python3 -c 'import json; print(json.load(open("'"${MANIFEST}"'")).get("version","unknown"))')"
BACKUP_REQUIRED="$(python3 -c 'import json; print(json.load(open("'"${MANIFEST}"'")).get("backup_required", True))')"
echo "[update] Applying version ${VERSION}"

if docker info >/dev/null 2>&1; then DOCKER=docker; else DOCKER="sudo docker"; fi
set -a; source "${NODE_DIR}/.env"; set +a
COMPOSE="${NODE_DIR}/compose.host.yml"
[[ "${CLINIC_NODE_NETWORK:-host}" != "host" ]] && COMPOSE="${NODE_DIR}/compose.yml"

if [[ "${BACKUP_REQUIRED}" == "True" || "${BACKUP_REQUIRED}" == "true" ]]; then
  echo "[update] Taking pre-update database backup…"
  mkdir -p "${NODE_DIR}/data/backups"
  STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
  OUT="${NODE_DIR}/data/backups/pre-update-${VERSION}-${STAMP}.sql.gz"
  set -o pipefail
  $DOCKER exec clinic-node-db-1 pg_dump -U sante --no-owner --no-acl sante | gzip -c > "${OUT}"
  BYTES="$(wc -c < "${OUT}" | tr -d ' ')"
  [[ "${BYTES}" -ge 200 ]] || { echo "pre-update backup too small (${BYTES})"; exit 1; }
  echo "[update] Backup ok: ${OUT} (${BYTES} bytes)"
fi

# Optional: load docker image tarballs if present
if compgen -G "${PKG}/images/*.tar" >/dev/null 2>&1; then
  for tar in "${PKG}"/images/*.tar; do
    echo "[update] docker load ${tar}"
    $DOCKER load -i "${tar}"
  done
fi

(cd "${NODE_DIR}" && $DOCKER compose --env-file .env -f "${COMPOSE}" up -d --build)
echo "[update] Applied ${VERSION}"
echo "UPDATE_APPLY_OK"
