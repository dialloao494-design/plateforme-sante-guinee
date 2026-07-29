#!/usr/bin/env bash
# Audit Clinic Node PKI permissions (Security Wave 4).
set -euo pipefail

DATA_DIR="${1:-${CLINIC_DATA_DIR:-./data}}"
PKI_DIR="${DATA_DIR}/pki"
FAIL=0

echo "[pki-audit] Checking ${PKI_DIR}"

if [[ ! -d "${PKI_DIR}" ]]; then
  echo "WARN: PKI directory missing (run generate-pki.sh)"
  exit 0
fi

dir_mode="$(stat -c '%a' "${PKI_DIR}" 2>/dev/null || stat -f '%OLp' "${PKI_DIR}")"
if [[ "${dir_mode}" != "700" && "${dir_mode}" != "0700" ]]; then
  echo "FAIL: pki/ mode ${dir_mode} (expected 700)"
  FAIL=1
else
  echo "PASS: pki/ mode ${dir_mode}"
fi

for key in ca.key privkey.pem; do
  path="${PKI_DIR}/${key}"
  if [[ ! -f "${path}" ]]; then
    echo "WARN: missing ${key}"
    continue
  fi
  mode="$(stat -c '%a' "${path}" 2>/dev/null || stat -f '%OLp' "${path}")"
  if [[ "${mode}" != "600" && "${mode}" != "0600" ]]; then
    echo "FAIL: ${key} mode ${mode} (expected 600)"
    FAIL=1
  else
    echo "PASS: ${key} mode ${mode}"
  fi
done

for pub in ca.crt ca-trust.crt fullchain.pem; do
  path="${PKI_DIR}/${pub}"
  if [[ -f "${path}" ]]; then
    echo "PASS: ${pub} present"
  else
    echo "WARN: missing ${pub}"
  fi
done

echo "[pki-audit] Never email ca.key / privkey.pem. Distribute ca-trust.crt only."
exit "${FAIL}"
