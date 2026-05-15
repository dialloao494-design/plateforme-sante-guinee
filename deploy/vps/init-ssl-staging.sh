#!/usr/bin/env bash
export ENV_FILE=".env.staging"
export COMPOSE_EXTRA="-f docker-compose.staging.yml"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
exec bash deploy/vps/init-ssl.sh
