#!/usr/bin/env bash
# Static Clinic Node security validation (Security Wave 4).
set -euo pipefail

NODE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ROOT_DIR="$(cd "${NODE_DIR}/../.." && pwd)"
FAIL=0

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAIL=1; }

echo "===== Wave 4 Clinic Node static checks ====="

if grep -q 'driver: bridge' "${NODE_DIR}/compose.yml"; then pass "bridge network in compose.yml"; else fail "bridge network in compose.yml"; fi
if ! grep -E '^\s+-\s*["'\'']?[0-9]+:5432' "${NODE_DIR}/compose.yml"; then pass "compose.yml does not publish Postgres"; else fail "compose.yml publishes Postgres"; fi
if grep -q 'listen_addresses=127.0.0.1' "${NODE_DIR}/compose.host.yml"; then pass "host compose binds Postgres to localhost"; else fail "host compose localhost bind"; fi
if grep -q 'LAB ONLY' "${NODE_DIR}/compose.host.yml"; then pass "host compose marked lab-only"; else fail "host compose lab-only marker"; fi
if grep -q 'TLSv1.2' "${NODE_DIR}/proxy/app.https.conf" && grep -q 'TLSv1.3' "${NODE_DIR}/proxy/app.https.conf"; then pass "nginx TLS 1.2+"; else fail "nginx TLS"; fi
if grep -q 'location /uploads/' "${NODE_DIR}/proxy/app.https.conf" && grep -q 'return 403' "${NODE_DIR}/proxy/app.https.conf"; then pass "nginx blocks /uploads/"; else fail "nginx uploads block"; fi
if grep -q 'return 301 https://' "${NODE_DIR}/proxy/app.https.conf"; then pass "nginx HTTP→HTTPS redirect"; else fail "nginx redirect"; fi
if grep -q 'Strict-Transport-Security' "${NODE_DIR}/proxy/app.https.conf"; then pass "nginx HSTS"; else fail "nginx HSTS"; fi
if [[ -x "${NODE_DIR}/scripts/generate-pki.sh" ]]; then pass "generate-pki.sh executable"; else fail "generate-pki.sh"; fi
if [[ -f "${NODE_DIR}/scripts/harden-host-firewall.sh" ]]; then pass "harden-host-firewall.sh present"; else fail "firewall script"; fi
if [[ -f "${NODE_DIR}/scripts/verify-luks.sh" ]]; then pass "verify-luks.sh present"; else fail "luks script"; fi
if [[ -f "${NODE_DIR}/scripts/encrypt-backup.sh" ]]; then pass "encrypt-backup.sh present"; else fail "encrypt-backup script"; fi
if grep -q 'ATTACHMENT_ENCRYPTION_KEY' "${NODE_DIR}/install/install.sh"; then pass "installer sets ATTACHMENT_ENCRYPTION_KEY"; else fail "installer encryption key"; fi
if grep -q 'CLINIC_NODE_LICENSE_SECRET' "${NODE_DIR}/install/install.sh"; then pass "installer sets license secret"; else fail "installer license secret"; fi

cd "${ROOT_DIR}"
python3 - <<'PY'
from pathlib import Path
from core.clinic_node_security import (
    clinic_compose_publishes_postgres,
    clinic_host_compose_binds_postgres_localhost,
    clinic_nginx_enforces_tls12_plus,
    clinic_nginx_blocks_uploads,
)
node = Path("deploy/clinic-node")
assert not clinic_compose_publishes_postgres((node / "compose.yml").read_text())
assert clinic_host_compose_binds_postgres_localhost((node / "compose.host.yml").read_text())
assert clinic_nginx_enforces_tls12_plus((node / "proxy/app.https.conf").read_text())
assert clinic_nginx_blocks_uploads((node / "proxy/app.https.conf").read_text())
print("PASS: core.clinic_node_security helpers")
PY

echo "==========================================="
exit "${FAIL}"
