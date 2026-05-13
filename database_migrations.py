"""
Lightweight additive migrations for SQLite / Postgres without Alembic runs.
Called after SQLAlchemy create_all on startup.
"""

from __future__ import annotations

import logging
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def ensure_doctor_geolocation_columns(engine: Engine) -> None:
    insp = inspect(engine)
    if "doctors" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("doctors")}
    dialect = engine.dialect.name
    coltype = "DOUBLE PRECISION" if dialect == "postgresql" else "FLOAT"
    stmts: list[str] = []
    if "latitude" not in cols:
        stmts.append(f"ALTER TABLE doctors ADD COLUMN latitude {coltype}")
    if "longitude" not in cols:
        stmts.append(f"ALTER TABLE doctors ADD COLUMN longitude {coltype}")
    for stmt in stmts:
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Applied doctor schema migration: %s", stmt)
        except Exception as exc:
            logger.warning("Doctor geo migration skipped or failed (%s): %s", stmt, exc)
