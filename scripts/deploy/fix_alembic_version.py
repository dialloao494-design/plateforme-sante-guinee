#!/usr/bin/env python3
"""One-shot fix: widen alembic_version.version_num and run upgrade head."""
from __future__ import annotations

import os
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def main() -> int:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("DATABASE_URL required", file=sys.stderr)
        return 1
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(url)
    with engine.begin() as conn:
        exists = conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'alembic_version'"
            )
        ).fetchone()
        if exists:
            conn.execute(
                text(
                    "ALTER TABLE alembic_version "
                    "ALTER COLUMN version_num TYPE VARCHAR(64) "
                    "USING version_num::varchar(64)"
                )
            )
            print("Widened alembic_version.version_num to VARCHAR(64)")
            row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            print(f"Current version: {row[0] if row else '(empty)'}")

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    print("Alembic upgrade head OK")

    with engine.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        print(f"Final version: {row[0] if row else '(empty)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
