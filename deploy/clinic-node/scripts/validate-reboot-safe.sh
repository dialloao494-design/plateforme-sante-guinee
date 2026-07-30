#!/usr/bin/env bash
# Reboot-safe / crash-recovery validation for Clinic Node (Phase 0).
# Writes evidence under evidence/clinic-node/
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
NODE_DIR="${ROOT_DIR}/deploy/clinic-node"
ENV_FILE="${NODE_DIR}/.env"
EVIDENCE_DIR="${ROOT_DIR}/evidence/clinic-node"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT="${EVIDENCE_DIR}/reboot-safe-${STAMP}.md"

mkdir -p "${EVIDENCE_DIR}"

[[ -f "${ENV_FILE}" ]] || { echo "ERROR: .env missing — run install/install.sh first"; exit 1; }

# shellcheck disable=SC1090
set -a
# shellcheck source=/dev/null
source "${ENV_FILE}"
set +a

NETWORK_MODE="${CLINIC_NODE_NETWORK:-bridge}"
if [[ "${NETWORK_MODE}" == "host" ]]; then
  COMPOSE_FILE="${NODE_DIR}/compose.host.yml"
else
  COMPOSE_FILE="${NODE_DIR}/compose.yml"
fi

compose() {
  if docker info >/dev/null 2>&1; then
    (cd "${NODE_DIR}" && docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@")
  else
    (cd "${NODE_DIR}" && sudo docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@")
  fi
}

https_ready() {
  local port="${HTTPS_PORT:-443}"
  if [[ "${port}" == "443" ]]; then
    curl -kfsS "https://127.0.0.1/health/ready" >/dev/null 2>&1 \
      || curl -fsS "http://127.0.0.1:8000/health/ready" >/dev/null 2>&1
  else
    curl -kfsS "https://127.0.0.1:${port}/health/ready" >/dev/null 2>&1 \
      || curl -fsS "http://127.0.0.1:8000/health/ready" >/dev/null 2>&1
  fi
}

http_health() {
  local port="${HTTPS_PORT:-443}"
  if [[ "${port}" == "443" ]]; then
    curl -kfsS "https://127.0.0.1/health" >/dev/null 2>&1 \
      || curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1
  else
    curl -kfsS "https://127.0.0.1:${port}/health" >/dev/null 2>&1 \
      || curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1
  fi
}

{
  echo "# Clinic Node reboot-safe validation"
  echo
  echo "- Timestamp (UTC): ${STAMP}"
  echo "- Host: $(hostname)"
  echo "- Network mode: ${NETWORK_MODE}"
  echo "- Compose file: ${COMPOSE_FILE}"
  echo
} > "${REPORT}"

fail() {
  echo "## FAILED: $1" | tee -a "${REPORT}"
  exit 1
}

pass() {
  echo "- PASS: $1" | tee -a "${REPORT}"
}

echo "## 1. Baseline health" >> "${REPORT}"
https_ready || fail "baseline /health/ready"
http_health || fail "baseline /health"
pass "baseline HTTPS/API health/ready"

echo "## 2. Simulate backend crash (docker kill)" >> "${REPORT}"
compose kill backend || fail "kill backend"
sleep 3
compose up -d backend
for i in $(seq 1 36); do
  if https_ready; then
    pass "API recovered after backend kill (${i}*5s)"
    break
  fi
  sleep 5
  if [[ "$i" == "36" ]]; then
    fail "API did not recover after backend kill"
  fi
done

echo "## 3. Full stack stop + start (reboot simulation)" >> "${REPORT}"
compose stop
sleep 2
compose up -d
for i in $(seq 1 48); do
  if https_ready; then
    pass "Full stack healthy after stop/start (${i}*5s)"
    break
  fi
  sleep 5
  if [[ "$i" == "48" ]]; then
    fail "Full stack did not recover after stop/start"
  fi
done

echo "## 4. PostgreSQL container restart" >> "${REPORT}"
compose restart db
sleep 5
for i in $(seq 1 36); do
  if https_ready; then
    pass "API healthy after db restart (${i}*5s)"
    break
  fi
  sleep 5
  if [[ "$i" == "36" ]]; then
    fail "API did not recover after db restart"
  fi
done

echo "## 5. Service status" >> "${REPORT}"
compose ps >> "${REPORT}"

echo >> "${REPORT}"
echo "## Result: ALL CHECKS PASSED" >> "${REPORT}"
echo "Evidence written to ${REPORT}"
cat "${REPORT}"
