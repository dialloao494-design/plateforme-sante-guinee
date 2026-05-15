#!/usr/bin/env bash
# Post-deploy validation for staging (run on VPS after deploy-staging.sh)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

set -a
# shellcheck disable=SC1091
source .env.staging
set +a

BASE="${VALIDATE_BASE_URL:-https://${DOMAIN}}"
API="${BASE}/api"
FAIL=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd"; then
    echo "  OK  $name"
  else
    echo "  FAIL $name"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== Staging validation: $BASE ==="

check "API health" "curl -fsS '${API}/health' | grep -q ok"
check "API ready" "curl -fsS '${API}/health/ready' | grep -q ready"
check "Frontend" "curl -fsS -o /dev/null -w '%{http_code}' '${BASE}/' | grep -q 200"
check "HTTPS redirect" "curl -fsSI 'http://${DOMAIN}/' 2>/dev/null | head -1 | grep -qE '301|302' || true"

echo ""
echo "=== WebSocket proxy ==="
python3 <<PY || FAIL=$((FAIL+1))
import asyncio
import json
import os
import sys
try:
    import websockets
except ImportError:
    print("  SKIP WS (pip install websockets)")
    sys.exit(0)

domain = os.environ.get("DOMAIN", "")
uri = f"wss://{domain}/api/ws/health"

async def main():
    async with websockets.connect(uri, open_timeout=10) as ws:
        msg = await ws.recv()
        data = json.loads(msg)
        assert data.get("type") == "ready", data
        await ws.send("ping")
        pong = json.loads(await ws.recv())
        assert pong.get("type") == "pong", pong

asyncio.run(main())
print("  OK  WebSocket health")
PY

echo ""
echo "=== Docker restart test ==="
docker compose -f docker-compose.yml -f docker-compose.staging.yml restart backend
sleep 8
check "Backend after restart" "curl -fsS '${API}/health/ready' | grep -q ready"

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "All automated checks passed."
  exit 0
fi
echo "$FAIL check(s) failed — see deploy/STAGING_VALIDATION.md for manual mobile tests."
exit 1
