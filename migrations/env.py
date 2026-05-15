"""Alembic environment.

Reads `DATABASE_URL` from the application settings (which honours .env). Uses
Base.metadata from platform_core for autogenerate.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make sure every model is registered on Base.metadata before autogenerate.
from platform_core.db import Base
from platform_core.models import registry as _model_registry  # noqa: F401
from platform_core.settings import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the runtime DATABASE_URL.
_db_url = get_settings().database_url
config.set_main_option("sqlalchemy.url", _db_url)

# Ensure the SQLite parent directory exists so the file can be created.
if _db_url.startswith("sqlite:///"):
    from pathlib import Path

    _file = _db_url.replace("sqlite:///", "", 1)
    if _file and _file != ":memory:":
        Path(_file).parent.mkdir(parents=True, exist_ok=True)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL without a live DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite") if url else False,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against an engine."""
    section = config.get_section(config.config_ini_section) or {}
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    is_sqlite = connectable.url.get_backend_name() == "sqlite"
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,  # required for SQLite ALTERs
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
