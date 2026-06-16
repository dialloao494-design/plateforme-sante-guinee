#!/bin/sh
# Launch uvicorn with proxy settings aligned to TRUSTED_PROXY_HOSTS (never '*').
set -e

PORT="${PORT:-8000}"
FORWARDED="${TRUSTED_PROXY_HOSTS:-127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,backend}"
echo "[uvicorn] port=${PORT} forwarded-allow-ips=${FORWARDED}"

exec uvicorn main:app \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED}"
