from logging.config import fileConfig
import os
import sys

from alembic import context
from alembic.script import ScriptDirectory
from sqlalchemy import engine_from_config, inspect, pool, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from database import Base, DATABASE_URL  # noqa: E402

# Import the complete ORM registry before assigning target_metadata. Importing a
# hand-maintained subset makes Alembic autogenerate silently miss newer clinical
# tables and foreign keys.
import models  # noqa: F401,E402

config = context.config
if config.config_file_name is not None:
    # Alembic also runs inside the API startup lifecycle.  Keep Uvicorn and
    # application loggers alive so migration/startup failures are observable.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

config.set_main_option("sqlalchemy.url", DATABASE_URL)
target_metadata = Base.metadata


def _bootstrap_pristine_database(connection) -> bool:
    """Create the current schema for a truly empty database and stamp head.

    Revision 0001 intentionally stamps databases that predate Alembic, so the
    historical chain cannot construct an empty database.  A pristine install
    is safe to create directly from the complete ORM metadata.  Databases with
    any application table always use normal incremental migrations.
    """
    table_names = set(inspect(connection).get_table_names())
    application_tables = table_names - {"alembic_version"}
    if application_tables:
        return False

    head = ScriptDirectory.from_config(config).get_current_head()
    if not head:
        raise RuntimeError("Alembic migration head could not be resolved")

    target_metadata.create_all(bind=connection)
    connection.execute(
        text(
            "CREATE TABLE IF NOT EXISTS alembic_version ("
            "version_num VARCHAR(64) NOT NULL PRIMARY KEY)"
        )
    )
    connection.execute(text("DELETE FROM alembic_version"))
    connection.execute(
        text("INSERT INTO alembic_version (version_num) VALUES (:head)"),
        {"head": head},
    )
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        with connection.begin():
            if _bootstrap_pristine_database(connection):
                return
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            if (
                connection.dialect.name == "postgresql"
                and inspect(connection).has_table("alembic_version")
            ):
                connection.execute(
                    text(
                        "ALTER TABLE alembic_version "
                        "ALTER COLUMN version_num TYPE VARCHAR(64) "
                        "USING version_num::varchar(64)"
                    )
                )
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
