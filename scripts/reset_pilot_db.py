#!/usr/bin/env python3
"""
Reset local pilot database and reseed canonical demo accounts.

SQLite (default): deletes ./sante.db (or path from DATABASE_URL), recreates schema, runs pilot seed.
Postgres: drops all tables in metadata and recreates (DESTRUCTIVE for that database).

Usage (from repo root):
  python scripts/reset_pilot_db.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Repo root on sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    os.chdir(ROOT)
    from dotenv import load_dotenv

    load_dotenv()

    raw_url = os.getenv("DATABASE_URL", "sqlite:///./sante.db")

    from database import engine, Base

    if raw_url.startswith("sqlite"):
        engine.dispose()
        path_part = raw_url.replace("sqlite:///", "").replace("sqlite://", "")
        db_path = Path(path_part).resolve()
        if db_path.exists():
            db_path.unlink()
            print(f"Removed SQLite file: {db_path}")
        else:
            print(f"No existing SQLite file at {db_path}")
    import models.user  # noqa: F401
    import models.patient  # noqa: F401
    import models.doctor  # noqa: F401
    import models.rendezvous  # noqa: F401
    import models.payment  # noqa: F401
    import models.availability  # noqa: F401
    import models.message  # noqa: F401
    import models.notification_event  # noqa: F401

    if not raw_url.startswith("sqlite"):
        print("Postgres DATABASE_URL detected: dropping all application tables...")
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    print("Schema created.")

    from database_migrations import ensure_doctor_geolocation_columns

    ensure_doctor_geolocation_columns(engine)

    from services.pilot_seed import seed_pilot_accounts

    seed_pilot_accounts()
    print("Pilot accounts seeded (doctors + test.patient).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
