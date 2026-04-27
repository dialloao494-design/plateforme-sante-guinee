from dotenv import load_dotenv
load_dotenv()

import logging

import models  # noqa: F401 - required so SQLAlchemy metadata includes all tables
from database import Base, engine
from sqlalchemy import inspect

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def initialize_database() -> None:
    """Create database tables once, only when manually invoked."""
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        if existing_tables:
            logger.info("Schema already initialized; no action needed.")
            return

        Base.metadata.create_all(bind=engine)
        logger.info("Schema initialized successfully.")
    except Exception as exc:
        logger.exception("Database initialization failed: %s", exc)
        raise


if __name__ == "__main__":
    initialize_database()
