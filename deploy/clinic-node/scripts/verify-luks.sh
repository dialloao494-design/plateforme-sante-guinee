#!/usr/bin/env bash
# Verify full-disk encryption (LUKS) presence for Clinic Node go-live (Security Wave 4).
# Read-only evidence helper — does not modify disks.
set -euo pipefail

OUT="${1:-}"
REPORT_LINES=()

pass() { REPORT_LINES+=("PASS: $1"); }
warn() { REPORT_LINES+=("WARN: $1"); }
fail() { REPORT_LINES+=("FAIL: $1"); }

if [[ "$(uname -s)" != "Linux" ]]; then
  fail "LUKS verification requires Linux mini-PC (found $(uname -s))"
else
  if command -v lsblk >/dev/null 2>&1; then
    if lsblk -o NAME,FSTYPE,TYPE,MOUNTPOINT 2>/dev/null | grep -qi crypt; then
      pass "lsblk reports at least one crypt/LUKS volume"
    else
      fail "No crypt/LUKS volumes found in lsblk — enable full-disk encryption before pilot go-live"
    fi
  else
    warn "lsblk not available"
  fi

  if command -v cryptsetup >/dev/null 2>&1; then
    if cryptsetup status 2>/dev/null | grep -qi "is active"; then
      pass "cryptsetup reports active mapping(s)"
    else
      # Enumerate /dev/mapper
      if ls /dev/mapper/* 2>/dev/null | grep -vq control; then
        warn "cryptsetup present; inspect /dev/mapper manually"
      else
        warn "cryptsetup installed but no active mapping detected via status"
      fi
    fi
  else
    warn "cryptsetup not installed — install cryptsetup-bin for verification"
  fi

  # Root filesystem on encrypted mapper is a strong signal
  ROOT_SRC="$(findmnt -n -o SOURCE / 2>/dev/null || true)"
  if [[ "${ROOT_SRC}" == /dev/mapper/* ]]; then
    pass "Root filesystem mounted from ${ROOT_SRC} (encrypted mapper)"
  else
    warn "Root SOURCE=${ROOT_SRC:-unknown} — confirm OS disk is LUKS-encrypted"
  fi
fi

echo "===== Clinic Node LUKS verification ====="
printf '%s\n' "${REPORT_LINES[@]}"
echo "========================================="

if [[ -n "${OUT}" ]]; then
  {
    echo "# Clinic Node LUKS evidence — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf '%s\n' "${REPORT_LINES[@]}"
  } > "${OUT}"
  echo "Wrote ${OUT}"
fi

if printf '%s\n' "${REPORT_LINES[@]}" | grep -q '^FAIL:'; then
  exit 2
fi
exit 0
