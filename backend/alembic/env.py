"""Alembic environment: DATABASE_URL from ``app.config``, metadata from ``app.db.Base``.

Owner: T2 — Tanuj. Run from ``backend/`` (``alembic upgrade head``).
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context

import app.models  # noqa: F401  (registers every model on Base.metadata)
from app.config import get_settings
from app.db import Base, _make_engine, normalize_database_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
database_url = normalize_database_url(get_settings().database_url)


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a DB connection (``alembic upgrade head --sql``)."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=database_url.startswith("sqlite"),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""
    connectable = _make_engine(database_url)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=connection.dialect.name == "sqlite",  # SQLite ALTER support
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
