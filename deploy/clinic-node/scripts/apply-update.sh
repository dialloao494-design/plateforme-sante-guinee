#!/usr/bin/env bash
# Signed update apply with integrity verification and automatic rollback on health failure.
# Package layout:
#   update/manifest.json  {"version":"1.0.1","backup_required":true}
#   update/manifest.sig   hex HMAC-SHA256 of canonical manifest JSON
#   update/images/*.tar   optional
set -euo pipefail
PKG="${1:?update package directory required}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
NODE_DIR="${ROOT_DIR}/deploy/clinic-node"
MANIFEST="${PKG}/manifest.json"
SIGFILE="${PKG}/manifest.sig"
ROLLBACK_TAG_FILE="${NODE_DIR}/data/update-previous-backend.image"

[[ -f "${MANIFEST}" ]] || { echo "manifest.json missing"; exit 1; }
[[ -f "${SIGFILE}" ]] || { echo "manifest.sig missing — refusing unsigned package"; exit 1; }

set -a; source "${NODE_DIR}/.env"; set +a
SECRET="${CLINIC_NODE_UPDATE_SECRET:-${JWT_SECRET:-}}"
[[ -n "${SECRET}" ]] || { echo "CLINIC_NODE_UPDATE_SECRET/JWT_SECRET required"; exit 1; }

python3 - <<PY
import hashlib, hmac, json, sys
secret='''${SECRET}'''.encode()
raw=open("${MANIFEST}","rb").read()
# Canonical: parsed+re-dumped sorted keys
claims=json.loads(raw)
canon=json.dumps(claims, sort_keys=True, separators=(",",":")).encode()
sig=open("${SIGFILE}").read().strip()
expected=hmac.new(secret, canon, hashlib.sha256).hexdigest()
if not hmac.compare_digest(expected, sig):
    print("SIGNATURE_INVALID", file=sys.stderr)
    sys.exit(1)
print("SIGNATURE_OK", claims.get("version"))
PY

VERSION="$(python3 -c 'import json; print(json.load(open("'"${MANIFEST}"'")).get("version","unknown"))')"
BACKUP_REQUIRED="$(python3 -c 'import json; print(json.load(open("'"${MANIFEST}"'")).get("backup_required", True))')"
echo "[update] Applying signed version ${VERSION}"

if docker info >/dev/null 2>&1; then DOCKER=docker; else DOCKER="sudo docker"; fi
COMPOSE="${NODE_DIR}/compose.host.yml"
[[ "${CLINIC_NODE_NETWORK:-host}" != "host" ]] && COMPOSE="${NODE_DIR}/compose.yml"

# Record previous image for rollback
PREV="$($DOCKER inspect --format='{{.Image}}' clinic-node-backend-1 2>/dev/null || true)"
mkdir -p "${NODE_DIR}/data"
[[ -n "${PREV}" ]] && echo "${PREV}" > "${ROLLBACK_TAG_FILE}"

if [[ "${BACKUP_REQUIRED}" == "True" || "${BACKUP_REQUIRED}" == "true" ]]; then
  echo "[update] Taking pre-update database backup…"
  STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
  OUT="${NODE_DIR}/data/backups/pre-update-${VERSION}-${STAMP}.sql.gz"
  set -o pipefail
  $DOCKER exec clinic-node-db-1 pg_dump -U sante --no-owner --no-acl sante | gzip -c > "${OUT}"
  BYTES="$(wc -c < "${OUT}" | tr -d ' ')"
  [[ "${BYTES}" -ge 200 ]] || { echo "pre-update backup too small (${BYTES})"; exit 1; }
  echo "[update] Backup ok: ${OUT} (${BYTES} bytes)"
fi

if compgen -G "${PKG}/images/*.tar" >/dev/null 2>&1; then
  for tar in "${PKG}"/images/*.tar; do
    echo "[update] docker load ${tar}"
    $DOCKER load -i "${tar}"
  done
fi

(cd "${NODE_DIR}" && $DOCKER compose --env-file .env -f "${COMPOSE}" up -d --build)

# Health gate — rollback on failure
HTTPS_PORT="${HTTPS_PORT:-8443}"
OK=0
for i in $(seq 1 60); do
  if curl -kfsS "https://127.0.0.1:${HTTPS_PORT}/health/ready" >/dev/null 2>&1; then
    OK=1
    break
  fi
  sleep 5
done

if [[ "${OK}" != "1" ]]; then
  echo "[update] HEALTH_FAILED — rolling back backend image"
  if [[ -f "${ROLLBACK_TAG_FILE}" ]]; then
    PREV_IMG="$(cat "${ROLLBACK_TAG_FILE}")"
    $DOCKER tag "${PREV_IMG}" clinic-node-backend:rollback || true
    (cd "${NODE_DIR}" && $DOCKER compose --env-file .env -f "${COMPOSE}" up -d backend) || true
  fi
  echo "UPDATE_ROLLBACK"
  exit 1
fi

echo "[update] Applied ${VERSION}"
echo "UPDATE_APPLY_OK"
