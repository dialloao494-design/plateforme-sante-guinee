#!/usr/bin/env python3
"""Static smoke checks for Security Wave 3 deploy / TLS / secrets hardening."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main() -> int:
    failures: list[str] = []

    from core.deploy_hardening import (
        compose_publishes_postgres,
        dockerfile_runs_as_non_root,
        nginx_blocks_uploads,
        nginx_enforces_tls12_plus,
        vercel_has_security_headers,
    )

    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    if not dockerfile_runs_as_non_root(dockerfile):
        failures.append("Dockerfile does not drop to non-root")

    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    if compose_publishes_postgres(compose):
        failures.append("Base compose publishes Postgres to host")
    if "no-new-privileges:true" not in compose:
        failures.append("Compose missing no-new-privileges")

    nginx = (ROOT / "deploy/nginx/conf.d/app.conf.template").read_text(encoding="utf-8")
    if not nginx_enforces_tls12_plus(nginx):
        failures.append("Nginx TLS 1.2+ not enforced")
    if not nginx_blocks_uploads(nginx):
        failures.append("Nginx does not block /uploads/")

    vercel = (ROOT / "frontend-sante/frontend/vercel.json").read_text(encoding="utf-8")
    if not vercel_has_security_headers(vercel):
        failures.append("Vercel missing security headers")

    railway = (ROOT / "railway.toml").read_text(encoding="utf-8")
    if "healthcheckPath" not in railway:
        failures.append("railway.toml missing healthcheckPath")

    if failures:
        print("WAVE3 SMOKE FAIL:", "; ".join(failures))
        return 1
    print("WAVE3 SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
