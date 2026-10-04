"""Alembic environment: DATABASE_URL from ``app.config``, metadata from ``app.db.Base``.

Owner: T2 — Tanuj. Run from ``backend/`` (``alembic upgrade head``).

The database URL is resolved in order:
1. The ``sqlalchemy.url`` option in ``alembic.ini`` / programmatic override (e.g. tests).
2. ``get_settings().database_url`` (from the ``DATABASE_URL`` env var / ``.env``).
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context

# Ensure backend directory is on sys.path whether alembic is run from repo root or backend/
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import app.models  # noqa: E402, F401  (registers every model on Base.metadata)
from app.db import Base, _make_engine, normalize_database_url  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _resolve_database_url() -> str:
    """Return the database URL: prefer the config file setting, fall back to app settings."""
    ini_url: str | None = config.get_main_option("sqlalchemy.url")
    if ini_url:
        return normalize_database_url(ini_url)
    from app.config import get_settings

    return normalize_database_url(get_settings().database_url)


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a DB connection (``alembic upgrade head --sql``)."""
    url = _resolve_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""
    url = _resolve_database_url()
    connectable = _make_engine(url)
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
