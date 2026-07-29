#!/usr/bin/env python3
"""Static smoke checks for Security Wave 4 Clinic Node hardening."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main() -> int:
    failures: list[str] = []
    node = ROOT / "deploy" / "clinic-node"

    from core.clinic_node_security import (
        clinic_compose_publishes_postgres,
        clinic_host_compose_binds_postgres_localhost,
        clinic_nginx_blocks_uploads,
        clinic_nginx_enforces_tls12_plus,
        clinic_nginx_redirects_http_to_https,
        is_clinic_node_environment,
    )

    if not is_clinic_node_environment("clinic-node"):
        failures.append("is_clinic_node_environment broken")

    compose = (node / "compose.yml").read_text(encoding="utf-8")
    if clinic_compose_publishes_postgres(compose):
        failures.append("bridge compose publishes Postgres")

    host = (node / "compose.host.yml").read_text(encoding="utf-8")
    if not clinic_host_compose_binds_postgres_localhost(host):
        failures.append("host compose missing listen_addresses=127.0.0.1")

    nginx = (node / "proxy/app.https.conf").read_text(encoding="utf-8")
    if not clinic_nginx_enforces_tls12_plus(nginx):
        failures.append("nginx TLS")
    if not clinic_nginx_blocks_uploads(nginx):
        failures.append("nginx uploads")
    if not clinic_nginx_redirects_http_to_https(nginx):
        failures.append("nginx redirect")

    script = node / "scripts" / "validate-clinic-node-security.sh"
    proc = subprocess.run(["bash", str(script)], cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        failures.append(f"validate-clinic-node-security.sh failed: {proc.stdout}\n{proc.stderr}")

    if failures:
        print("WAVE4 SMOKE FAIL:", "; ".join(failures))
        return 1
    print("WAVE4 SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
