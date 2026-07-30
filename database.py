from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm import Session
import os
import logging

from core.deploy_hardening import (
    normalize_database_url_for_runtime,
    resolve_db_sslmode_connect_arg,
)

logger = logging.getLogger(__name__)

_raw_url = os.getenv("DATABASE_URL", "sqlite:///./sante.db")

# Railway provides postgres:// but SQLAlchemy requires postgresql://.
# Also strip private-mesh sslmode=require which breaks *.railway.internal.
DATABASE_URL = normalize_database_url_for_runtime(_raw_url)

_is_sqlite = DATABASE_URL.startswith("sqlite")
_connect_args: dict = {"check_same_thread": False} if _is_sqlite else {}

if not _is_sqlite:
    sslmode = resolve_db_sslmode_connect_arg(DATABASE_URL)
    if sslmode:
        # libpq connect arg — applies when URL does not already set sslmode.
        _connect_args["sslmode"] = sslmode

if _is_sqlite:
    engine = create_engine(DATABASE_URL, connect_args=_connect_args)
else:
    engine = create_engine(
        DATABASE_URL,
        connect_args=_connect_args,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

# Log masked URL so we can confirm which DB is active at startup
_masked = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
logger.info("Database engine created → ...@%s", _masked)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
