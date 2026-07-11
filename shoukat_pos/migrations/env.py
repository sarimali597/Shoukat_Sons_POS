"""Alembic migrations environment configuration."""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, event
from alembic import context

# Import the config and schema modules
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATABASE_PATH  # noqa: E402

# Alembic Config object
config = context.config

# Set the SQLAlchemy URL to use SQLite with the configured path
config.set_main_option("sqlalchemy.url", f"sqlite:///{DATABASE_PATH}")

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support
target_metadata = None


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # REQUIRED for SQLite batch migrations
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection
    with the context. For SQLite, we must disable foreign keys during
    batch migrations that restructure tables.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Disable foreign keys during migration for SQLite
        if connection.dialect.name == "sqlite":
            @event.listens_for(connection, "begin")
            def do_begin(conn):
                conn.exec_driver_sql("PRAGMA foreign_keys=OFF")

            @event.listens_for(connection, "commit")
            def do_commit(conn):
                conn.exec_driver_sql("PRAGMA foreign_keys=ON")

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # REQUIRED for SQLite batch migrations
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
