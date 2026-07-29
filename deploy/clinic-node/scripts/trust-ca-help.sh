#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
NODE_DIR="${ROOT_DIR}/deploy/clinic-node"
ENV_FILE="${NODE_DIR}/.env"
DATA_DIR="${NODE_DIR}/data"
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "${ENV_FILE}"
  set +a
  DATA_DIR="${CLINIC_DATA_DIR:-${DATA_DIR}}"
fi
CA="${DATA_DIR}/pki/ca-trust.crt"
[[ -f "${CA}" ]] || { echo "CA not found at ${CA}. Run install.sh first."; exit 1; }
cat <<MSG
Clinic Node — trust the local CA on each workstation (once)

CA file: ${CA}

Linux (Debian/Ubuntu):
  sudo cp "${CA}" /usr/local/share/ca-certificates/sante-guinee-clinic-node.crt
  sudo update-ca-certificates

Firefox: Preferences → Certificates → Import → select the CA file above

Chrome/Edge (Windows): Install Certificate → Trusted Root Certification Authorities

Then open: https://sante-locale  (or https://<server-ip>)
MSG
