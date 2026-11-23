#!/usr/bin/env bash
# Clinic Node installer — Phase 0
# Technician happy path: run this script once. No manual docker/sql required.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
NODE_DIR="${ROOT_DIR}/deploy/clinic-node"
DATA_DIR="${CLINIC_DATA_DIR:-${NODE_DIR}/data}"
ENV_FILE="${NODE_DIR}/.env"
REQUESTED_HTTP_PORT="${HTTP_PORT-}"
REQUESTED_HTTPS_PORT="${HTTPS_PORT-}"
REQUESTED_NETWORK="${CLINIC_NODE_NETWORK-}"
REQUESTED_HOST_ACK="${CLINIC_NODE_ALLOW_HOST_NETWORK-}"
COMPOSE_BIN=(docker compose)
if ! docker compose version >/dev/null 2>&1; then
  if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_BIN=(docker-compose)
  else
    echo "ERROR: Docker Compose is required. Install Docker Desktop / docker-compose-plugin."
    exit 1
  fi
fi

docker_cmd() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
  else
    sudo docker "$@"
  fi
}

compose() {
  if docker info >/dev/null 2>&1; then
    (cd "${NODE_DIR}" && "${COMPOSE_BIN[@]}" "$@")
  else
    (cd "${NODE_DIR}" && sudo "${COMPOSE_BIN[@]}" "$@")
  fi
}

echo "============================================"
echo " Santé Guinée — Clinic Node installer (P0)"
echo "============================================"
echo "Data directory: ${DATA_DIR}"
echo

if ! command -v openssl >/dev/null 2>&1; then
  echo "ERROR: openssl is required to generate local HTTPS certificates."
  exit 1
fi

if ! docker_cmd info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon is not reachable."
  exit 1
fi

detect_lan_ip() {
  if command -v ip >/dev/null 2>&1; then
    ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1;i<=NF;i++) if ($i=="src") {print $(i+1); exit}}' || true
  fi
}

LAN_IP="${LAN_IP:-$(detect_lan_ip)}"
DOMAIN="${DOMAIN:-sante-locale}"
HTTP_PORT="${HTTP_PORT:-80}"
HTTPS_PORT="${HTTPS_PORT:-443}"

gen_secret() {
  python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
}

select_network_mode() {
  case "${CLINIC_NODE_NETWORK:-bridge}" in
    bridge|auto) NETWORK_MODE="bridge" ;;
    host)
      if [[ "${CLINIC_NODE_ALLOW_HOST_NETWORK:-false}" != "true" ]]; then
        echo "ERROR: host networking requires explicit CLINIC_NODE_ALLOW_HOST_NETWORK=true; configuration unchanged."
        exit 1
      fi
      NETWORK_MODE="host"
      ;;
    *) echo "ERROR: CLINIC_NODE_NETWORK must be bridge or explicitly approved host; configuration unchanged."; exit 1 ;;
  esac
}

validate_existing_keys() {
  PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" python3 - <<'PY'
import os
import sys
from cryptography.fernet import Fernet
from core.settings import is_insecure_secret

primary = (os.getenv("SECRET_KEY") or "").strip()
alias = (os.getenv("JWT_SECRET") or "").strip()
keys = {
    "JWT signing key": primary or alias,
    "CLINIC_NODE_LICENSE_SECRET": (os.getenv("CLINIC_NODE_LICENSE_SECRET") or "").strip(),
    "CLINIC_NODE_UPDATE_SECRET": (os.getenv("CLINIC_NODE_UPDATE_SECRET") or "").strip(),
    "ATTACHMENT_ENCRYPTION_KEY": (os.getenv("ATTACHMENT_ENCRYPTION_KEY") or "").strip(),
}
errors = []
if primary and alias and primary != alias:
    errors.append("SECRET_KEY and JWT_SECRET disagree")
for name, value in keys.items():
    if not value:
        errors.append(name + " is missing")
    elif name != "ATTACHMENT_ENCRYPTION_KEY" and is_insecure_secret(value, min_length=32):
        errors.append(name + " must be a strong random value (32+ chars)")
if len([v for v in keys.values() if v]) != len(set(v for v in keys.values() if v)):
    errors.append("Signing, license, update and attachment keys must be distinct")
if keys["ATTACHMENT_ENCRYPTION_KEY"]:
    try:
        Fernet(keys["ATTACHMENT_ENCRYPTION_KEY"].encode("utf-8"))
    except (ValueError, TypeError):
        errors.append("ATTACHMENT_ENCRYPTION_KEY is invalid")
if errors:
    print("ERROR: " + "; ".join(errors) + ".", file=sys.stderr)
    print("Recovery required: preserve the current .env and backups; identify existing signing, attachment, license and update key lineage before changing keys. See docs/SECURITY_RECOVERY_2026-11-23.md. Installer made no configuration changes.", file=sys.stderr)
    sys.exit(1)
PY
}

if [[ ! -f "${ENV_FILE}" ]]; then
  select_network_mode
  umask 077
  mkdir -p "${DATA_DIR}"
  echo "[install] Generating secrets and .env…"
  POSTGRES_PASSWORD="$(gen_secret)"
  SECRET_KEY="$(gen_secret)"
  JWT_SECRET="${SECRET_KEY}"
  REMINDER_RESPOND_TOKEN="$(gen_secret)"
  CLINIC_NODE_LICENSE_SECRET="$(gen_secret)"
  CLINIC_NODE_UPDATE_SECRET="$(gen_secret)"
  ATTACHMENT_ENCRYPTION_KEY="$(python3 - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
)"
  NODE_ID="$(python3 - <<'PY'
import uuid
print(str(uuid.uuid4()))
PY
)"
  ADMIN_EMAIL="${CLINIC_NODE_ADMIN_EMAIL:-admin@clinic.local}"
  ADMIN_PASSWORD="${CLINIC_NODE_ADMIN_PASSWORD:-$(python3 - <<'PY'
import secrets
print("Adm-" + secrets.token_urlsafe(12) + "!")
PY
)}"
  CLINIC_NAME="${CLINIC_NODE_CLINIC_NAME:-Clinique Locale}"
  # Quote values that may contain spaces for safe shell sourcing
  cat > "${ENV_FILE}" <<EOF
ENVIRONMENT=clinic-node
DEBUG=false
DOMAIN=${DOMAIN}
ALLOWED_HOSTS=${DOMAIN},localhost,127.0.0.1,backend,proxy
TRUSTED_PROXY_HOSTS=proxy,127.0.0.1,localhost,backend
FRONTEND_URL=https://${DOMAIN}
CORS_ORIGINS=https://${DOMAIN},https://127.0.0.1,https://localhost${LAN_IP:+,https://${LAN_IP}}
POSTGRES_USER=sante
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=sante
SECRET_KEY=${SECRET_KEY}
JWT_SECRET=${JWT_SECRET}
REMINDER_RESPOND_TOKEN=${REMINDER_RESPOND_TOKEN}
CLINIC_NODE_LICENSE_SECRET=${CLINIC_NODE_LICENSE_SECRET}
CLINIC_NODE_UPDATE_SECRET=${CLINIC_NODE_UPDATE_SECRET}
ATTACHMENT_ENCRYPTION_KEY=${ATTACHMENT_ENCRYPTION_KEY}
REQUIRE_ATTACHMENT_ENCRYPTION=true
NODE_ID=${NODE_ID}
CLINIC_ID=${CLINIC_ID:-}
CLINIC_DATA_DIR=${DATA_DIR}
HTTP_PORT=${HTTP_PORT}
HTTPS_PORT=${HTTPS_PORT}
DISABLE_API_DOCS=true
ENABLE_PILOT_SEED=false
ENABLE_STARTUP_TEST_USER=false
ENABLE_STARTUP_SEED=false
ENABLE_DEMO_CLINIC_SEED=false
ENABLE_LAN_DEV=false
BYPASS_AVAILABILITY_VALIDATION=false
CLINIC_NODE_NETWORK=${NETWORK_MODE}
CLINIC_NODE_ALLOW_HOST_NETWORK=${CLINIC_NODE_ALLOW_HOST_NETWORK:-false}
ENABLE_CLINIC_NODE_BOOTSTRAP=true
CLINIC_NODE_CLINIC_NAME="${CLINIC_NAME}"
CLINIC_NODE_CLINIC_CITY="${CLINIC_NODE_CLINIC_CITY:-}"
CLINIC_NODE_ADMIN_EMAIL=${ADMIN_EMAIL}
CLINIC_NODE_ADMIN_PASSWORD=${ADMIN_PASSWORD}
CLINIC_NODE_ADMIN_MUST_CHANGE_PASSWORD=${CLINIC_NODE_ADMIN_MUST_CHANGE_PASSWORD:-true}
CLINIC_NODE_BOOTSTRAP_STAFF=${CLINIC_NODE_BOOTSTRAP_STAFF:-false}
EOF
  chmod 600 "${ENV_FILE}"
  umask 077
  cat > "${DATA_DIR}/ADMIN_CREDENTIALS.txt" <<CREDS
Clinic Node — initial admin (change after first login)
Clinic: ${CLINIC_NAME}
Email: ${ADMIN_EMAIL}
Password: ${ADMIN_PASSWORD}
CREDS
  chmod 600 "${DATA_DIR}/ADMIN_CREDENTIALS.txt"
  echo "[install] Wrote ${ENV_FILE}"
  echo "[install] Initial admin credentials saved to ${DATA_DIR}/ADMIN_CREDENTIALS.txt"
else
  echo "[install] Reusing existing ${ENV_FILE}"
fi

# shellcheck disable=SC1090
# The existing file is authoritative for key lineage; ambient values must not
# silently fill a missing key or conceal an incomplete upgrade configuration.
unset SECRET_KEY JWT_SECRET CLINIC_NODE_LICENSE_SECRET CLINIC_NODE_UPDATE_SECRET ATTACHMENT_ENCRYPTION_KEY
set -a
# shellcheck source=/dev/null
source "${ENV_FILE}"
set +a
validate_existing_keys
# Environment overrides are explicit operator choices; never invent host consent.
if [[ -n "${REQUESTED_NETWORK}" ]]; then CLINIC_NODE_NETWORK="${REQUESTED_NETWORK}"; fi
if [[ -n "${REQUESTED_HOST_ACK}" ]]; then CLINIC_NODE_ALLOW_HOST_NETWORK="${REQUESTED_HOST_ACK}"; fi
select_network_mode
export CLINIC_NODE_NETWORK="${NETWORK_MODE}" CLINIC_NODE_ALLOW_HOST_NETWORK
# Only explicitly requested ports may change a validated existing configuration.
for PORT_NAME in HTTP_PORT HTTPS_PORT; do
  REQUEST_NAME="REQUESTED_${PORT_NAME}"
  PORT_VALUE="${!REQUEST_NAME}"
  if [[ -n "${PORT_VALUE}" ]]; then
    if [[ ! "${PORT_VALUE}" =~ ^[0-9]+$ ]] || (( 10#${PORT_VALUE} < 1 || 10#${PORT_VALUE} > 65535 )); then
      echo "ERROR: ${PORT_NAME} must be a valid TCP port."
      exit 1
    fi
    if grep -q "^${PORT_NAME}=" "${ENV_FILE}"; then
      sed -i "s/^${PORT_NAME}=.*/${PORT_NAME}=${PORT_VALUE}/" "${ENV_FILE}"
    else
      echo "${PORT_NAME}=${PORT_VALUE}" >> "${ENV_FILE}"
    fi
    export "${PORT_NAME}=${PORT_VALUE}"
  fi
done
DATA_DIR="${CLINIC_DATA_DIR:-${DATA_DIR}}"
HTTP_PORT="${HTTP_PORT:-80}"
HTTPS_PORT="${HTTPS_PORT:-443}"

export DOMAIN LAN_IP
mkdir -p "${DATA_DIR}/postgres" "${DATA_DIR}/uploads" "${DATA_DIR}/logs" "${DATA_DIR}/pki" "${DATA_DIR}/backups"
bash "${NODE_DIR}/scripts/generate-pki.sh" "${DATA_DIR}"

COMPOSE_FILES=(-f "${NODE_DIR}/compose.yml")
if [[ "${NETWORK_MODE}" == "host" ]]; then
  echo "[install] Using host network mode (LAB ONLY — bridge preferred for mini-PC)."
  sed \
    -e "s/listen 80;/listen ${HTTP_PORT};/" \
    -e "s/listen 443 ssl;/listen ${HTTPS_PORT} ssl;/" \
    -e "s/listen 443 ssl http2;/listen ${HTTPS_PORT} ssl http2;/" \
    "${NODE_DIR}/proxy/app.https.host.conf" > "${NODE_DIR}/proxy/app.https.host.runtime.conf"
  COMPOSE_FILES=(-f "${NODE_DIR}/compose.host.yml")
else
  echo "[install] Using Docker bridge network mode."
fi

echo "[install] Building and starting Clinic Node stack…"
compose --env-file "${ENV_FILE}" "${COMPOSE_FILES[@]}" up -d --build

echo "[install] Waiting for API readiness…"
READY=0
if [[ "${HTTPS_PORT}" == "443" ]]; then
  HEALTH_URL="https://127.0.0.1/health/ready"
else
  HEALTH_URL="https://127.0.0.1:${HTTPS_PORT}/health/ready"
fi
for i in $(seq 1 60); do
  if curl -kfsS "${HEALTH_URL}" >/dev/null 2>&1; then
    READY=1
    break
  fi
  # Fallback: hit backend directly on host network
  if curl -fsS "http://127.0.0.1:8000/health/ready" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 5
done

if [[ "${READY}" != "1" ]]; then
  echo "ERROR: API did not become ready in time."
  compose --env-file "${ENV_FILE}" "${COMPOSE_FILES[@]}" ps || true
  compose --env-file "${ENV_FILE}" "${COMPOSE_FILES[@]}" logs --tail=80 backend || true
  exit 1
fi

cat <<EOF

============================================
 Installation successful
============================================
 Open:     https://${DOMAIN}${HTTPS_PORT:+:${HTTPS_PORT}}
           https://127.0.0.1:${HTTPS_PORT}
 Network:  ${NETWORK_MODE}
 Node ID:  $(grep -E '^NODE_ID=' "${ENV_FILE}" | cut -d= -f2)
 Trust CA: ${DATA_DIR}/pki/ca-trust.crt
 Admin:    see ${DATA_DIR}/ADMIN_CREDENTIALS.txt (if freshly generated)
 Login:    local clinic admin — change password on first login

 Security Wave 4 next steps (mini-PC):
   sudo ${NODE_DIR}/scripts/harden-host-firewall.sh
   sudo ${NODE_DIR}/scripts/verify-luks.sh ${DATA_DIR}/backups/luks-evidence.txt
   ${NODE_DIR}/scripts/audit-pki-perms.sh ${DATA_DIR}
   # After each backup: ${NODE_DIR}/scripts/encrypt-backup.sh data/backups/*.sql.gz
============================================
EOF
