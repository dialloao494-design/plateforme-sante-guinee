#!/bin/sh
# Launch uvicorn with proxy settings aligned to TRUSTED_PROXY_HOSTS (never '*').
set -e

FORWARDED="${TRUSTED_PROXY_HOSTS:-127.0.0.1,backend}"
echo "[uvicorn] forwarded-allow-ips=${FORWARDED}"

exec uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED}"
