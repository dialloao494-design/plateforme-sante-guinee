#!/usr/bin/env bash
# Encrypt a Clinic Node SQL backup with age (preferred) or gpg (fallback).
# Usage: ./encrypt-backup.sh <backup.sql.gz> [output.age|.gpg]
set -euo pipefail

SRC="${1:?Usage: encrypt-backup.sh <backup.sql.gz> [out]}"
OUT="${2:-}"
DATA_DIR="${CLINIC_DATA_DIR:-$(cd "$(dirname "$0")/.." && pwd)/data}"
KEY_FILE="${BACKUP_ENCRYPTION_KEY_FILE:-${DATA_DIR}/backups/.backup-age-key}"
SHA_FILE=""

if [[ ! -f "${SRC}" ]]; then
  echo "ERROR: backup not found: ${SRC}"
  exit 1
fi

mkdir -p "$(dirname "${KEY_FILE}")"
chmod 700 "$(dirname "${KEY_FILE}")" 2>/dev/null || true

sha256_sidecar() {
  local f="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${f}" | awk '{print $1}' > "${f}.sha256"
  else
    shasum -a 256 "${f}" | awk '{print $1}' > "${f}.sha256"
  fi
  chmod 600 "${f}.sha256"
  SHA_FILE="${f}.sha256"
}

if command -v age >/dev/null 2>&1; then
  if [[ ! -f "${KEY_FILE}" ]]; then
    echo "[backup] Generating age identity at ${KEY_FILE}"
    age-keygen -o "${KEY_FILE}" >/dev/null
    chmod 600 "${KEY_FILE}"
  fi
  RECIPIENT="$(grep -E '^# public key:' "${KEY_FILE}" | awk '{print $NF}')"
  if [[ -z "${RECIPIENT}" ]]; then
    # age-keygen also prints pubkey to stderr on create; derive from identity
    RECIPIENT="$(age-keygen -y "${KEY_FILE}")"
  fi
  OUT="${OUT:-${SRC}.age}"
  age -r "${RECIPIENT}" -o "${OUT}" "${SRC}"
  chmod 600 "${OUT}"
  sha256_sidecar "${OUT}"
  echo "[backup] Encrypted (age): ${OUT}"
  echo "[backup] Integrity: ${SHA_FILE}"
  exit 0
fi

if command -v gpg >/dev/null 2>&1; then
  OUT="${OUT:-${SRC}.gpg}"
  # Symmetric passphrase from env (operator-provided) — never log it.
  if [[ -z "${BACKUP_GPG_PASSPHRASE:-}" ]]; then
    echo "ERROR: set BACKUP_GPG_PASSPHRASE or install 'age' for key-based encryption."
    exit 1
  fi
  gpg --batch --yes --symmetric --cipher-algo AES256 \
    --passphrase "${BACKUP_GPG_PASSPHRASE}" \
    -o "${OUT}" "${SRC}"
  chmod 600 "${OUT}"
  sha256_sidecar "${OUT}"
  echo "[backup] Encrypted (gpg-symmetric): ${OUT}"
  echo "[backup] Integrity: ${SHA_FILE}"
  exit 0
fi

echo "ERROR: install 'age' (recommended) or 'gpg' to encrypt Clinic Node backups."
exit 1
