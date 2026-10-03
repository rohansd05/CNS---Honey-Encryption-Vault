"""SQLAlchemy 2.0 engine, session factory, declarative base and FastAPI DB dependency.

Owner: T2 — Tanuj (app core).
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


def normalize_database_url(url: str) -> str:
    """Force the psycopg 3 driver for Postgres URLs (Neon/Render hand out ``postgres://``)."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def _make_engine(url: str) -> Engine:
    url = normalize_database_url(url)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


class Base(DeclarativeBase):
    """Declarative base for all ORM models in ``app.models``."""


engine = _make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a session that is always closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
