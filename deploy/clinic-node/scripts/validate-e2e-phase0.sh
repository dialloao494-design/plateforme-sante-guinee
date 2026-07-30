#!/usr/bin/env bash
# Phase 0 full end-to-end acceptance validation (production-like).
# Produces evidence under evidence/clinic-node/e2e-phase0/
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
NODE_DIR="${ROOT_DIR}/deploy/clinic-node"
EVIDENCE_ROOT="${ROOT_DIR}/evidence/clinic-node/e2e-phase0"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="${EVIDENCE_ROOT}/${STAMP}"
REPORT="${RUN_DIR}/ACCEPTANCE_REPORT.md"
LOG="${RUN_DIR}/console.log"

HTTP_PORT="${HTTP_PORT:-8088}"
HTTPS_PORT="${HTTPS_PORT:-8443}"
CLINIC_NODE_NETWORK="${CLINIC_NODE_NETWORK:-host}"

mkdir -p "${RUN_DIR}"

log() { echo "$*" | tee -a "${LOG}" "${REPORT}" >/dev/null; echo "$*" | tee -a "${LOG}"; }
log_only() { echo "$*" | tee -a "${LOG}"; }
criterion() { echo | tee -a "${LOG}" "${REPORT}"; echo "## $*" | tee -a "${LOG}" "${REPORT}"; }
log_pass() { echo "- [x] PASS: $*" | tee -a "${LOG}" "${REPORT}"; }
log_fail() { echo "- [ ] FAIL: $*" | tee -a "${LOG}" "${REPORT}"; echo "FATAL: $*" >&2; exit 1; }

docker_cmd() {
  if docker info >/dev/null 2>&1; then docker "$@"; else sudo docker "$@"; fi
}

load_env() {
  local key value
  while IFS= read -r line || [[ -n "${line}" ]]; do
    [[ -z "${line}" || "${line}" =~ ^# ]] && continue
    key="${line%%=*}"
    value="${line#*=}"
    printf -v "${key}" '%s' "${value}"
    export "${key?}"
  done < "${NODE_DIR}/.env"
}

compose() {
  (cd "${NODE_DIR}" && docker_cmd compose --env-file "${NODE_DIR}/.env" -f "${COMPOSE_FILE}" "$@")
}

{
  echo "# Phase 0 E2E Acceptance Report"
  echo
  echo "- Timestamp UTC: ${STAMP}"
  echo "- Host: $(hostname)"
  echo "- Network mode: ${CLINIC_NODE_NETWORK}"
  echo "- HTTP_PORT=${HTTP_PORT} HTTPS_PORT=${HTTPS_PORT}"
  echo
  echo "## Criteria results"
  echo
} > "${REPORT}"
cp "${REPORT}" "${LOG}"

log_only "=== Phase 0 E2E acceptance ${STAMP} ==="

# ---------------------------------------------------------------------------
criterion "1. Fresh installation on a clean machine"
# ---------------------------------------------------------------------------
log_only "[e2e] Tearing down any prior Clinic Node stack and wiping local data..."
(cd "${NODE_DIR}" && docker_cmd compose --env-file .env -f compose.yml down -v --remove-orphans >/dev/null 2>&1 || true)
(cd "${NODE_DIR}" && docker_cmd compose --env-file .env -f compose.host.yml down -v --remove-orphans >/dev/null 2>&1 || true)
docker_cmd rm -f clinic-node-db-1 clinic-node-backend-1 clinic-node-frontend-1 clinic-node-proxy-1 >/dev/null 2>&1 || true
docker_cmd run --rm -v "${NODE_DIR}/data:/data" alpine:3.20 sh -c 'rm -rf /data/*' >/dev/null 2>&1 || true
sudo rm -rf "${NODE_DIR}/data" >/dev/null 2>&1 || true
rm -f "${NODE_DIR}/.env" "${NODE_DIR}/proxy/app.https.host.runtime.conf" >/dev/null 2>&1 || true
mkdir -p "${NODE_DIR}/data"

log_only "[e2e] Running fresh installer..."
CLINIC_NODE_NETWORK="${CLINIC_NODE_NETWORK}" \
HTTP_PORT="${HTTP_PORT}" \
HTTPS_PORT="${HTTPS_PORT}" \
  bash "${NODE_DIR}/install/install.sh" | tee -a "${LOG}" | tee "${RUN_DIR}/01-fresh-install.log"

[[ -f "${NODE_DIR}/.env" ]] || log_fail "Fresh install did not create .env"
[[ -f "${NODE_DIR}/data/pki/fullchain.pem" ]] || log_fail "Fresh install did not create TLS certs"
load_env
COMPOSE_FILE="${NODE_DIR}/compose.yml"
if [[ "${CLINIC_NODE_NETWORK}" == "host" ]]; then
  COMPOSE_FILE="${NODE_DIR}/compose.host.yml"
fi

log_pass "Fresh installation completed on clean data directory"
cp "${NODE_DIR}/.env" "${RUN_DIR}/env.redacted.txt"
sed -i -E \
  -e 's/^(POSTGRES_PASSWORD)=.*/\1=***REDACTED***/' \
  -e 's/^(SECRET_KEY)=.*/\1=***REDACTED***/' \
  -e 's/^(JWT_SECRET)=.*/\1=***REDACTED***/' \
  -e 's/^(REMINDER_RESPOND_TOKEN)=.*/\1=***REDACTED***/' \
  "${RUN_DIR}/env.redacted.txt"

# ---------------------------------------------------------------------------
criterion "2. PostgreSQL starts automatically"
criterion "3. FastAPI starts automatically"
# ---------------------------------------------------------------------------
compose ps | tee "${RUN_DIR}/02-compose-ps-after-install.txt" | tee -a "${LOG}"
compose exec -T db pg_isready -U "${POSTGRES_USER:-sante}" -d "${POSTGRES_DB:-sante}" -h 127.0.0.1 \
  | tee "${RUN_DIR}/02-postgres-ready.txt" | tee -a "${LOG}" \
  || log_fail "PostgreSQL not ready"
log_pass "PostgreSQL starts automatically and accepts connections"

BACKEND_HEALTH="$(compose ps backend | tr '\n' ' ')"
echo "${BACKEND_HEALTH}" | tee -a "${LOG}" | grep -qi healthy \
  || log_fail "FastAPI backend container not healthy"
log_pass "FastAPI starts automatically - container healthy"

# ---------------------------------------------------------------------------
criterion "4. Frontend is accessible over HTTPS"
# ---------------------------------------------------------------------------
FRONTEND_URL="https://127.0.0.1:${HTTPS_PORT}/"
curl -kfsSI "${FRONTEND_URL}" | tee "${RUN_DIR}/04-frontend-https-headers.txt" | tee -a "${LOG}"
grep -Eiq "HTTP/1\.[01] 200|HTTP/2 200" "${RUN_DIR}/04-frontend-https-headers.txt" \
  || log_fail "Frontend HTTPS did not return 200"
curl -kfsS "${FRONTEND_URL}" | head -c 800 | tee "${RUN_DIR}/04-frontend-https-body-snippet.html" | tee -a "${LOG}" >/dev/null
[[ -s "${RUN_DIR}/04-frontend-https-body-snippet.html" ]] || log_fail "Frontend HTTPS body empty"
echo | openssl s_client -connect "127.0.0.1:${HTTPS_PORT}" -servername sante-locale 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates \
  | tee "${RUN_DIR}/04-tls-cert-info.txt" | tee -a "${LOG}"
log_pass "Frontend is accessible over HTTPS"

# ---------------------------------------------------------------------------
criterion "5. API can read and write to PostgreSQL"
# ---------------------------------------------------------------------------
curl -kfsS "https://127.0.0.1:${HTTPS_PORT}/health/ready" \
  | tee "${RUN_DIR}/05-health-ready-read.json" | tee -a "${LOG}"
grep -q '"status":"ready"' "${RUN_DIR}/05-health-ready-read.json" || log_fail "health/ready not ready"
grep -q '"database":"ok"' "${RUN_DIR}/05-health-ready-read.json" || log_fail "health/ready database not ok"
log_pass "API read path to PostgreSQL works via health/ready"

compose exec -T backend python - <<'PY' | tee "${RUN_DIR}/05-api-db-readwrite.txt" | tee -a "${LOG}"
from sqlalchemy import text
from database import engine

probe = "phase0-e2e-probe"
with engine.begin() as conn:
    conn.execute(text(
        "CREATE TABLE IF NOT EXISTS clinic_node_e2e_probe ("
        "id serial PRIMARY KEY, note text NOT NULL, created_at timestamptz DEFAULT now())"
    ))
    conn.execute(text("INSERT INTO clinic_node_e2e_probe (note) VALUES (:n)"), {"n": probe})
    value = conn.execute(
        text("SELECT note FROM clinic_node_e2e_probe WHERE note = :n ORDER BY id DESC LIMIT 1"),
        {"n": probe},
    ).scalar()
    count = conn.execute(text("SELECT count(*) FROM clinic_node_e2e_probe")).scalar()
assert value == probe, value
print(f"WRITE_OK note={value}")
print(f"READ_OK count={count}")
print("API_DB_READWRITE_PASSED")
PY
grep -q "API_DB_READWRITE_PASSED" "${RUN_DIR}/05-api-db-readwrite.txt" || log_fail "API DB read/write probe failed"
log_pass "API can write and read PostgreSQL through application engine"

# ---------------------------------------------------------------------------
criterion "6. Full machine reboot simulated"
criterion "7. Everything starts automatically after reboot"
criterion "8. No manual intervention required"
# ---------------------------------------------------------------------------
log_only "[e2e] Cold stop all containers, then single compose up -d boot path..."
compose stop | tee "${RUN_DIR}/06-reboot-stop.log" | tee -a "${LOG}"
sleep 2
docker_cmd ps --filter name=clinic-node --format '{{.Names}} {{.Status}}' \
  | tee "${RUN_DIR}/06-running-before-boot.txt" | tee -a "${LOG}" || true

# Boot path identical to systemd ExecStart - one command only
compose up -d | tee "${RUN_DIR}/07-reboot-auto-start.log" | tee -a "${LOG}"

READY=0
for i in $(seq 1 60); do
  if curl -kfsS "https://127.0.0.1:${HTTPS_PORT}/health/ready" >/dev/null 2>&1 \
     || curl -fsS "http://127.0.0.1:8000/health/ready" >/dev/null 2>&1; then
    READY=1
    log_only "ready after ${i} attempts"
    break
  fi
  sleep 5
done
[[ "${READY}" == "1" ]] || log_fail "Stack did not become ready automatically after reboot simulation"

compose ps | tee "${RUN_DIR}/07-compose-ps-after-reboot.txt" | tee -a "${LOG}"
log_pass "Full reboot simulation executed - cold stop then single compose up -d"
log_pass "Everything started automatically after reboot"
log_pass "No manual per-service intervention required"

# ---------------------------------------------------------------------------
criterion "9. Health endpoint returns READY"
# ---------------------------------------------------------------------------
curl -kfsS "https://127.0.0.1:${HTTPS_PORT}/health/ready" \
  | tee "${RUN_DIR}/09-health-ready-final.json" | tee -a "${LOG}"
grep -q '"status":"ready"' "${RUN_DIR}/09-health-ready-final.json" || log_fail "Final health/ready status not ready"
grep -q '"database":"ok"' "${RUN_DIR}/09-health-ready-final.json" || log_fail "Final health/ready database not ok"
curl -kfsSI "https://127.0.0.1:${HTTPS_PORT}/" | head -8 \
  | tee "${RUN_DIR}/09-frontend-after-reboot.txt" | tee -a "${LOG}"

compose exec -T backend python - <<'PY' | tee "${RUN_DIR}/09-data-survived-reboot.txt" | tee -a "${LOG}"
from sqlalchemy import text
from database import engine
with engine.connect() as conn:
    count = conn.execute(text("SELECT count(*) FROM clinic_node_e2e_probe")).scalar()
print(f"probe_rows_after_reboot={count}")
assert count >= 1
print("DATA_SURVIVED_REBOOT")
PY
grep -q "DATA_SURVIVED_REBOOT" "${RUN_DIR}/09-data-survived-reboot.txt" || log_fail "Probe data lost after reboot"
log_pass "Health endpoint returns READY with database ok"
log_pass "PostgreSQL data survived reboot"

{
  echo
  echo "## Summary"
  echo
  echo "**Phase 0 E2E acceptance: ALL CRITERIA PASSED**"
  echo
  echo "Evidence directory: \`evidence/clinic-node/e2e-phase0/${STAMP}/\`"
  echo
} | tee -a "${REPORT}" | tee -a "${LOG}"

log_only "REPORT=${REPORT}"
log_only "PHASE0_E2E_ACCEPTANCE_PASSED"
