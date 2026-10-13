"""Core API tests: auth, JWT, 401/403 paths, 422 safety, migration.

Owner: T2 — Tanuj.

Note: In Phase 0/1 the auth, admin and vault routers are stubs (no routes yet).
These tests focus on:
  1. JWT token creation and decode round-trip (library-level, not HTTP).
  2. The security dependencies themselves (unit-tested via test-only routes).
  3. 422 body shape and password-safety.
  4. Migration smoke test.
"""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.security import create_access_token, decode_token, get_current_user, require_admin

# ---------------------------------------------------------------------------
# JWT round-trip (library level)
# ---------------------------------------------------------------------------


class TestJWTRoundTrip:
    def test_token_contains_expected_claims(self, make_user):
        user = make_user("alice")
        token = create_access_token(user)
        payload = decode_token(token)

        assert payload["sub"] == user.id
        assert payload["username"] == "alice"
        assert payload["is_admin"] is False
        assert "iat" in payload
        assert "exp" in payload

    def test_admin_claim_propagated(self, make_user):
        admin = make_user("adminuser", is_admin=True)
        token = create_access_token(admin)
        payload = decode_token(token)
        assert payload["is_admin"] is True

    def test_tampered_token_is_rejected(self, make_user):
        """A token with a flipped signature byte must fail ``decode_token``."""
        import pytest
        from fastapi import HTTPException

        user = make_user("bob")
        token = create_access_token(user)
        parts = token.split(".")
        bad_sig = parts[2][:-1] + ("A" if parts[2][-1] != "A" else "B")
        bad_token = ".".join(parts[:2] + [bad_sig])

        with pytest.raises(HTTPException) as exc_info:
            decode_token(bad_token)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Not authenticated"


# ---------------------------------------------------------------------------
# 401 / 403 paths via in-app test routes
# ---------------------------------------------------------------------------


@pytest.fixture()
def secured_client(db_session, client: TestClient) -> TestClient:
    """Add ephemeral secured test routes to the underlying app."""

    the_app = client.app

    # Register minimal test-only routes so we can probe the dependencies.
    from fastapi import APIRouter

    test_router = APIRouter(prefix="/_test")

    @test_router.get("/protected")
    def _protected(current_user: object = Depends(get_current_user)):
        return {"user": current_user.username}  # type: ignore[attr-defined]

    @test_router.get("/admin-only")
    def _admin_only(current_user: object = Depends(require_admin)):
        return {"user": current_user.username}  # type: ignore[attr-defined]

    the_app.include_router(test_router)
    return client


class TestUnauthorizedAndForbidden:
    def test_missing_token_returns_401(self, secured_client: TestClient):
        resp = secured_client.get("/_test/protected")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Not authenticated"

    def test_invalid_bearer_returns_401(self, secured_client: TestClient):
        resp = secured_client.get(
            "/_test/protected",
            headers={"Authorization": "Bearer notavalidtoken"},
        )
        assert resp.status_code == 401

    def test_valid_token_is_accepted(self, secured_client: TestClient, make_user, auth_headers):
        user = make_user("carol")
        resp = secured_client.get("/_test/protected", headers=auth_headers(user))
        assert resp.status_code == 200
        assert resp.json()["user"] == "carol"

    def test_non_admin_on_admin_endpoint_returns_403(
        self, secured_client: TestClient, make_user, auth_headers
    ):
        user = make_user("regularuser")
        resp = secured_client.get("/_test/admin-only", headers=auth_headers(user))
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Admin only"

    def test_admin_can_access_admin_endpoint(
        self, secured_client: TestClient, make_user, auth_headers
    ):
        admin = make_user("superadmin", is_admin=True)
        resp = secured_client.get("/_test/admin-only", headers=auth_headers(admin))
        assert resp.status_code == 200
        assert resp.json()["user"] == "superadmin"


# ---------------------------------------------------------------------------
# 422 responses must not echo submitted passwords
# ---------------------------------------------------------------------------


class TestValidationErrorSafety:
    def test_422_does_not_echo_password(self, client: TestClient):
        """A 422 body must never contain the submitted password."""
        from fastapi import APIRouter
        from pydantic import BaseModel

        # Add a route that will produce a 422 for a missing required field.
        the_app = client.app

        class _Body(BaseModel):
            username: str
            secret_password: str

        test_router = APIRouter(prefix="/_test422")

        @test_router.post("/submit")
        def _submit(body: _Body):
            return {"ok": True}

        the_app.include_router(test_router)

        submitted_value = "VerySecretP@ssw0rd9999"  # noqa: S105
        resp = client.post(
            "/_test422/submit",
            # Send secret_password but omit username → 422
            json={"secret_password": submitted_value},
        )
        assert resp.status_code == 422
        body_text = resp.text
        # The password value must NOT appear anywhere in the response.
        assert submitted_value not in body_text

    def test_422_body_has_loc_msg_type_not_input(self, client: TestClient):
        """Each error item must have loc/msg/type but NOT 'input' or 'ctx'."""
        from fastapi import APIRouter
        from pydantic import BaseModel

        the_app = client.app

        class _Req(BaseModel):
            value: int

        tr = APIRouter(prefix="/_test422b")

        @tr.post("/val")
        def _val(body: _Req):
            return {}

        the_app.include_router(tr)

        resp = client.post("/_test422b/val", json={"value": "not-an-int"})
        assert resp.status_code == 422
        errors = resp.json().get("detail", [])
        if isinstance(errors, list) and errors:
            for err in errors:
                assert "input" not in err, "'input' must be stripped from 422 errors"
                assert "ctx" not in err, "'ctx' must be stripped from 422 errors"
                assert "loc" in err
                assert "msg" in err
                assert "type" in err


# ---------------------------------------------------------------------------
# Migration smoke test: alembic upgrade head on a fresh SQLite file
# ---------------------------------------------------------------------------


class TestMigration:
    def test_alembic_upgrade_head_on_fresh_sqlite(self):
        """Run ``alembic upgrade head`` on a temporary SQLite file and verify tables."""
        from alembic import command
        from alembic.config import Config
        from sqlalchemy import create_engine, inspect

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = os.path.join(tmpdir, "test_migration.db")
            db_url = f"sqlite:///{db_path}"

            alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "../../alembic.ini"))
            # Override URL programmatically so env.py picks it up.
            alembic_cfg.set_main_option("sqlalchemy.url", db_url)
            command.upgrade(alembic_cfg, "head")

            eng = create_engine(db_url)
            try:
                inspector = inspect(eng)
                tables = inspector.get_table_names()
            finally:
                # Dispose before tmpdir context exits to release the Windows file lock.
                eng.dispose()

        assert "users" in tables
        assert "vaults" in tables
        assert "shares" in tables
        assert "alerts" in tables
