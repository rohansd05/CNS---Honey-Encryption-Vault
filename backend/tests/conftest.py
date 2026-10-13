"""Shared pytest fixtures. Owner: T1 lead — Nidhi (scaffold); tracks may add fixtures.

Forces ``HONEYCORE_IMPL=stub`` so tests never depend on a developer's ``.env``.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

os.environ["HONEYCORE_IMPL"] = "stub"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A TestClient for a freshly built app."""
    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
