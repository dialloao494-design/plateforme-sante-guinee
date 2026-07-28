#!/usr/bin/env bash
# Clinic Node installer — Phase 0
# Technician happy path: run this script once. No manual docker/sql required.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
NODE_DIR="${ROOT_DIR}/deploy/clinic-node"
DATA_DIR="${CLINIC_DATA_DIR:-${NODE_DIR}/data}"
ENV_FILE="${NODE_DIR}/.env"
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

mkdir -p "${DATA_DIR}/postgres" "${DATA_DIR}/uploads" "${DATA_DIR}/logs" "${DATA_DIR}/pki" "${DATA_DIR}/backups"

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

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[install] Generating secrets and .env…"
  POSTGRES_PASSWORD="$(gen_secret)"
  SECRET_KEY="$(gen_secret)"
  JWT_SECRET="$(gen_secret)"
  REMINDER_RESPOND_TOKEN="$(gen_secret)"
  NODE_ID="$(python3 - <<'PY'
import uuid
print(str(uuid.uuid4()))
PY
)"
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
CLINIC_NODE_NETWORK=${CLINIC_NODE_NETWORK:-auto}
EOF
  chmod 600 "${ENV_FILE}"
  echo "[install] Wrote ${ENV_FILE}"
else
  echo "[install] Reusing existing ${ENV_FILE}"
  # Persist requested ports into .env when provided by operator
  if grep -q '^HTTP_PORT=' "${ENV_FILE}"; then
    sed -i "s/^HTTP_PORT=.*/HTTP_PORT=${HTTP_PORT}/" "${ENV_FILE}"
  else
    echo "HTTP_PORT=${HTTP_PORT}" >> "${ENV_FILE}"
  fi
  if grep -q '^HTTPS_PORT=' "${ENV_FILE}"; then
    sed -i "s/^HTTPS_PORT=.*/HTTPS_PORT=${HTTPS_PORT}/" "${ENV_FILE}"
  else
    echo "HTTPS_PORT=${HTTPS_PORT}" >> "${ENV_FILE}"
  fi
fi

# shellcheck disable=SC1090
set -a
# shellcheck source=/dev/null
source "${ENV_FILE}"
set +a
DATA_DIR="${CLINIC_DATA_DIR:-${DATA_DIR}}"
HTTP_PORT="${HTTP_PORT:-80}"
HTTPS_PORT="${HTTPS_PORT:-443}"

export DOMAIN LAN_IP
bash "${NODE_DIR}/scripts/generate-pki.sh" "${DATA_DIR}"

# Decide network mode: bridge (default) or host (fallback for broken Docker bridges).
NETWORK_MODE="${CLINIC_NODE_NETWORK:-auto}"
if [[ "${NETWORK_MODE}" == "auto" ]]; then
  echo "[install] Probing Docker bridge networking…"
  if docker_cmd run --rm --network bridge alpine:3.20 ping -c 1 -W 2 1.1.1.1 >/dev/null 2>&1; then
    # Bridge outbound may work while container-to-container fails; prefer host in nested VMs if env sets it.
    NETWORK_MODE="bridge"
  else
    NETWORK_MODE="host"
  fi
fi
# Nested/cloud agents frequently break veth; allow explicit override via env already set.
if [[ "${CLINIC_NODE_NETWORK:-}" == "host" ]]; then
  NETWORK_MODE="host"
fi

COMPOSE_FILES=(-f "${NODE_DIR}/compose.yml")
if [[ "${NETWORK_MODE}" == "host" ]]; then
  echo "[install] Using host network mode (bridge unavailable or forced)."
  sed \
    -e "s/listen 80;/listen ${HTTP_PORT};/" \
    -e "s/listen 443 ssl;/listen ${HTTPS_PORT} ssl;/" \
    "${NODE_DIR}/proxy/app.https.host.conf" > "${NODE_DIR}/proxy/app.https.host.runtime.conf"
  COMPOSE_FILES=(-f "${NODE_DIR}/compose.host.yml")
  if grep -q '^CLINIC_NODE_NETWORK=' "${ENV_FILE}"; then
    sed -i 's/^CLINIC_NODE_NETWORK=.*/CLINIC_NODE_NETWORK=host/' "${ENV_FILE}"
  else
    echo "CLINIC_NODE_NETWORK=host" >> "${ENV_FILE}"
  fi
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
           (install once on each workstation browser/OS)

 Next: Phase 1 will add local staff login bootstrap.
============================================
EOF
