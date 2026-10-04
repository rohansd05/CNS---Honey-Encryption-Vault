"""Fixtures for backend API tests.

Owner: T2 — Tanuj / Rohan.

Provides:
- in-memory SQLite engine (StaticPool) with create_all
- ``get_db`` dependency override
- ``client`` (TestClient with in-memory DB wired in)
- ``db_session``
- ``make_user(username, is_admin=False)`` — inserts a user with dummy honeyword fields
- ``auth_headers(user)`` — returns {"Authorization": "Bearer <token>"}
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

# Force stub honeycore before any app imports.
os.environ.setdefault("HONEYCORE_IMPL", "stub")
# Use a throwaway JWT secret for tests.
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use")

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.db import Base, get_db  # noqa: E402
from app.models.core import User  # noqa: E402
from app.security import create_access_token  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    """A single in-memory SQLite engine for the whole test session."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine) -> Iterator[Session]:
    """Yield a transaction-scoped session, rolling back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    """TestClient with the in-memory DB injected via dependency override."""
    from app.main import create_app

    the_app = create_app()

    def _override_get_db() -> Iterator[Session]:
        yield db_session

    the_app.dependency_overrides[get_db] = _override_get_db

    with TestClient(the_app, raise_server_exceptions=True) as c:
        yield c

    the_app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db_session: Session) -> Callable[..., User]:
    """Factory fixture: insert a User with dummy honeyword fields and return it."""

    def _factory(username: str, *, is_admin: bool = False) -> User:
        user = User(
            username=username,
            is_admin=is_admin,
            hw_salt="dummysalt",
            hw_hashes=["dummyhash"],
            hw_kdf_profile="demo",
        )
        db_session.add(user)
        db_session.flush()
        return user

    return _factory


@pytest.fixture()
def auth_headers(make_user: Callable[..., User]) -> Callable[..., dict[str, str]]:
    """Return ``{"Authorization": "Bearer <token>"}`` for a given user."""

    def _headers(user: User) -> dict[str, str]:
        token = create_access_token(user)
        return {"Authorization": f"Bearer {token}"}

    return _headers
