#!/usr/bin/env bash
# Generate local CA + server certificate for Clinic Node HTTPS (LAN).
# Output: $DATA_DIR/pki/{ca.crt,ca.key,fullchain.pem,privkey.pem,ca-trust.crt}
set -euo pipefail

DATA_DIR="${1:-./data}"
DOMAIN="${DOMAIN:-sante-locale}"
EXTRA_IP="${LAN_IP:-}"
PKI_DIR="${DATA_DIR}/pki"
DAYS_CA="${PKI_DAYS_CA:-3650}"
DAYS_SRV="${PKI_DAYS_SERVER:-825}"

mkdir -p "${PKI_DIR}"
chmod 700 "${PKI_DIR}"

if [[ -f "${PKI_DIR}/fullchain.pem" && -f "${PKI_DIR}/privkey.pem" && "${FORCE_PKI:-0}" != "1" ]]; then
  echo "[pki] Existing certificates found in ${PKI_DIR} (set FORCE_PKI=1 to regenerate)"
  exit 0
fi

echo "[pki] Generating Clinic Node CA and server certificate…"

openssl genrsa -out "${PKI_DIR}/ca.key" 4096
openssl req -x509 -new -nodes -key "${PKI_DIR}/ca.key" -sha256 -days "${DAYS_CA}" \
  -subj "/O=Sante Guinee/OU=Clinic Node/CN=Sante Guinee Local CA" \
  -out "${PKI_DIR}/ca.crt"

openssl genrsa -out "${PKI_DIR}/privkey.pem" 2048

SAN="DNS:${DOMAIN},DNS:localhost,IP:127.0.0.1"
if [[ -n "${EXTRA_IP}" ]]; then
  SAN="${SAN},IP:${EXTRA_IP}"
fi

openssl req -new -key "${PKI_DIR}/privkey.pem" \
  -subj "/O=Sante Guinee/OU=Clinic Node/CN=${DOMAIN}" \
  -out "${PKI_DIR}/server.csr"

cat > "${PKI_DIR}/server.ext" <<EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = ${SAN}
EOF

openssl x509 -req -in "${PKI_DIR}/server.csr" -CA "${PKI_DIR}/ca.crt" -CAkey "${PKI_DIR}/ca.key" \
  -CAcreateserial -out "${PKI_DIR}/server.crt" -days "${DAYS_SRV}" -sha256 \
  -extfile "${PKI_DIR}/server.ext"

cat "${PKI_DIR}/server.crt" "${PKI_DIR}/ca.crt" > "${PKI_DIR}/fullchain.pem"
cp "${PKI_DIR}/ca.crt" "${PKI_DIR}/ca-trust.crt"

chmod 600 "${PKI_DIR}/ca.key" "${PKI_DIR}/privkey.pem"
chmod 644 "${PKI_DIR}/ca.crt" "${PKI_DIR}/fullchain.pem" "${PKI_DIR}/ca-trust.crt" "${PKI_DIR}/server.crt"

rm -f "${PKI_DIR}/server.csr" "${PKI_DIR}/server.ext" "${PKI_DIR}/ca.srl"

echo "[pki] Done. Trust file for workstations: ${PKI_DIR}/ca-trust.crt"
echo "[pki] SAN: ${SAN}"
