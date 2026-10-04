"""Tests for /api/admin endpoints.

Owner: T2 — Rohan.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.core import User
from app.services import alerts


def test_admin_alerts_forbidden_for_non_admin(
    client: TestClient, make_user: Callable[..., User], auth_headers: Callable[..., dict[str, str]]
) -> None:
    """Non-admin users receive 403 Forbidden on GET /api/admin/alerts."""
    regular_user = make_user(f"regular_{uuid.uuid4().hex[:8]}", is_admin=False)
    headers = auth_headers(regular_user)

    resp = client.get("/api/admin/alerts", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Admin only"


def test_admin_alerts_unauthenticated_returns_401(client: TestClient) -> None:
    """Unauthenticated calls to /api/admin/alerts return 401 Unauthorized."""
    resp = client.get("/api/admin/alerts")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Not authenticated"


def test_admin_alerts_success_for_admin(
    client: TestClient,
    db_session: Session,
    make_user: Callable[..., User],
    auth_headers: Callable[..., dict[str, str]],
) -> None:
    """Admin user can list security alerts ordered newest first."""
    admin_user = make_user(f"admin_{uuid.uuid4().hex[:8]}", is_admin=True)
    headers = auth_headers(admin_user)

    # Insert two alerts with different sweetword indices
    alert1 = alerts.create_alert(
        db=db_session,
        username="target1",
        kind="HONEYWORD_LOGIN",
        severity="critical",
        sweetword_index=3,
        source_ip="192.168.1.100",
        user_agent="AttackBot/1.0",
    )
    alert2 = alerts.create_alert(
        db=db_session,
        username="target2",
        kind="HONEYWORD_LOGIN",
        severity="critical",
        sweetword_index=7,
        source_ip="192.168.1.101",
        user_agent="AttackBot/2.0",
    )

    resp = client.get("/api/admin/alerts", headers=headers)
    assert resp.status_code == 200
    alert_list = resp.json()
    assert len(alert_list) >= 2

    # Newest first
    ids = [a["id"] for a in alert_list]
    assert ids.index(alert2.id) < ids.index(alert1.id)

    # Validate alert fields
    item = next(a for a in alert_list if a["id"] == alert2.id)
    assert item["username"] == "target2"
    assert item["sweetword_index"] == 7
    assert item["source_ip"] == "192.168.1.101"
    assert item["user_agent"] == "AttackBot/2.0"
    assert item["severity"] == "critical"
    assert item["kind"] == "HONEYWORD_LOGIN"

    # Test limit query param
    lim_resp = client.get("/api/admin/alerts?limit=1", headers=headers)
    assert lim_resp.status_code == 200
    assert len(lim_resp.json()) == 1
