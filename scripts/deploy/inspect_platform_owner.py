#!/usr/bin/env python3
"""Read-only: list platform_owner accounts in production (email only, no passwords)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def classify_email(email: str) -> str:
    e = (email or "").lower().strip()
    local = e.split("@")[0]
    domain = e.split("@")[-1] if "@" in e else ""
    if e.endswith("@sante-gn.test"):
        return "staging_test"
    if domain in {"example.com", "test.com", "test.gn", "pilot.local", "clinic.test"}:
        return "test"
    if "demo" in local or local.startswith("test") or ".test" in domain:
        return "test"
    return "real"


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL required", file=sys.stderr)
        return 1

    engine = create_engine(url)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT id, email, role, is_active, clinic_id "
                "FROM users WHERE role = 'platform_owner' ORDER BY id"
            )
        ).fetchall()

        if not rows:
            print("NO_PLATFORM_OWNER")
            return 0

        for row in rows:
            data = dict(row._mapping)
            data["classification"] = classify_email(data["email"])
            print(data)

        scope = conn.execute(
            text(
                "SELECT id, email, role, is_active FROM users "
                "WHERE role IN ('platform_owner', 'platform_admin') ORDER BY role, id"
            )
        ).fetchall()
        print("--- platform_scope_users ---")
        for row in scope:
            d = dict(row._mapping)
            d["classification"] = classify_email(d["email"])
            print(d)

    return 0


if __name__ == "__main__":
    sys.exit(main())
