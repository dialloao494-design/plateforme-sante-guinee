#!/usr/bin/env bash
# Harden mini-PC host firewall for Clinic Node (Security Wave 4).
# Allows HTTPS/HTTP (+ optional SSH). Denies Postgres and backend ports from LAN.
set -euo pipefail

SSH_PORT="${SSH_PORT:-22}"
HTTP_PORT="${HTTP_PORT:-80}"
HTTPS_PORT="${HTTPS_PORT:-443}"
ALLOW_SSH_FROM="${ALLOW_SSH_FROM:-}"  # optional CIDR, e.g. 192.168.1.0/24

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root (sudo) to apply firewall rules."
  exit 1
fi

if command -v ufw >/dev/null 2>&1; then
  echo "[firewall] Configuring ufw…"
  ufw --force reset >/dev/null
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow "${HTTP_PORT}/tcp" comment "clinic-node-http"
  ufw allow "${HTTPS_PORT}/tcp" comment "clinic-node-https"
  if [[ -n "${ALLOW_SSH_FROM}" ]]; then
    ufw allow from "${ALLOW_SSH_FROM}" to any port "${SSH_PORT}" proto tcp comment "clinic-node-ssh-admin"
  else
    ufw allow "${SSH_PORT}/tcp" comment "clinic-node-ssh"
  fi
  # Explicit deny high-value services if somehow published
  ufw deny 5432/tcp comment "deny-postgres"
  ufw deny 8000/tcp comment "deny-fastapi"
  ufw deny 8080/tcp comment "deny-spa-direct"
  ufw --force enable
  ufw status verbose
  echo "[firewall] ufw enabled."
  exit 0
fi

if command -v nft >/dev/null 2>&1; then
  echo "[firewall] ufw not found — writing basic nftables inet filter (manual persistence required)."
  cat <<EOF
table inet clinic_node {
  chain input {
    type filter hook input priority 0; policy drop;
    ct state established,related accept
    iif lo accept
    tcp dport { ${HTTP_PORT}, ${HTTPS_PORT}, ${SSH_PORT} } accept
  }
}
EOF
  echo "[firewall] Apply with: nft -f <file> and enable nftables service."
  exit 0
fi

echo "ERROR: neither ufw nor nft found. Install ufw on Ubuntu/Debian mini-PCs."
exit 1
