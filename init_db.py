from dotenv import load_dotenv
load_dotenv()

import logging
from pathlib import Path

import models  # noqa: F401 - required so SQLAlchemy metadata includes all tables
from alembic import command
from alembic.config import Config
from database import Base, engine
from sqlalchemy import inspect

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def initialize_database() -> None:
    """Create database tables once, only when manually invoked."""
    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        application_tables = existing_tables - {"alembic_version"}
        if application_tables:
            logger.info("Schema already initialized; no action needed.")
            return

        Base.metadata.create_all(bind=engine)
        alembic_config = Config(str(Path(__file__).resolve().parent / "alembic.ini"))
        command.stamp(alembic_config, "head")
        logger.info("Schema initialized and stamped at the current Alembic head.")
    except Exception as exc:
        logger.exception("Database initialization failed: %s", exc)
        raise


if __name__ == "__main__":
    initialize_database()
