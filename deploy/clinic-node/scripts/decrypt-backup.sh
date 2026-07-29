#!/usr/bin/env bash
# Decrypt a Clinic Node encrypted backup (age or gpg).
# Usage: ./decrypt-backup.sh <backup.sql.gz.age|gpg> [output.sql.gz]
set -euo pipefail

SRC="${1:?Usage: decrypt-backup.sh <encrypted> [out.sql.gz]}"
OUT="${2:-}"
DATA_DIR="${CLINIC_DATA_DIR:-$(cd "$(dirname "$0")/.." && pwd)/data}"
KEY_FILE="${BACKUP_ENCRYPTION_KEY_FILE:-${DATA_DIR}/backups/.backup-age-key}"

if [[ ! -f "${SRC}" ]]; then
  echo "ERROR: file not found: ${SRC}"
  exit 1
fi

if [[ -f "${SRC}.sha256" ]]; then
  echo "[backup] Verifying SHA-256 sidecar…"
  if command -v sha256sum >/dev/null 2>&1; then
    echo "$(cat "${SRC}.sha256")  ${SRC}" | sha256sum -c -
  else
    echo "$(cat "${SRC}.sha256")  ${SRC}" | shasum -a 256 -c -
  fi
fi

case "${SRC}" in
  *.age)
    OUT="${OUT:-${SRC%.age}}"
    age -d -i "${KEY_FILE}" -o "${OUT}" "${SRC}"
    ;;
  *.gpg)
    OUT="${OUT:-${SRC%.gpg}}"
    if [[ -z "${BACKUP_GPG_PASSPHRASE:-}" ]]; then
      echo "ERROR: set BACKUP_GPG_PASSPHRASE"
      exit 1
    fi
    gpg --batch --yes --decrypt --passphrase "${BACKUP_GPG_PASSPHRASE}" -o "${OUT}" "${SRC}"
    ;;
  *)
    echo "ERROR: unsupported extension (expected .age or .gpg)"
    exit 1
    ;;
esac

chmod 600 "${OUT}"
echo "[backup] Decrypted: ${OUT}"
