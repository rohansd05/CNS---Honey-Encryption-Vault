import re
import secrets

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)
settings = get_settings()


def normalize_path(path: str) -> str:
    return re.sub(r"\{.*?\}", "{}", path)


def test_openapi_contract_paths_exist():
    schema = app.openapi()
    paths = schema["paths"]

    expected_endpoints = [
        ("get", "/api/health"),
        ("post", "/api/auth/register"),
        ("post", "/api/auth/login"),
        ("get", "/api/auth/me"),
        ("post", "/api/vault/unlock"),
        ("post", "/api/vault/entries"),
        ("put", "/api/vault/entries/{id}"),
        ("delete", "/api/vault/entries/{id}"),
        ("get", "/api/vault/export"),
        ("get", "/api/users/{username}/identity"),
        ("post", "/api/shares"),
        ("get", "/api/shares/inbox"),
        ("get", "/api/shares/sent"),
        ("post", "/api/shares/{id}/open"),
        ("post", "/api/shares/{id}/tamper"),
        ("get", "/api/admin/alerts"),
        ("get", "/api/eval/summary"),
        ("get", "/api/attack/stolen-vault"),
        ("post", "/api/attack/dictionary"),
        ("get", "/api/attack/stolen-honeywords"),
        ("get", "/api/attack/alarms"),
        ("post", "/api/utils/strength"),
    ]

    normalized_actual = {normalize_path(p): methods for p, methods in paths.items()}

    for method, path in expected_endpoints:
        norm_path = normalize_path(path)
        assert norm_path in normalized_actual, f"Path {path} missing in OpenAPI schema"
        assert method in normalized_actual[norm_path], f"Method {method.upper()} missing for {path}"


def test_post_password_no_echo():
    """For every POST endpoint accepting a password-like field, submit an invalid value
    and verify the response body does not contain that submitted value."""

    endpoints = [
        (
            "/api/auth/register",
            {
                "username": "foo",
                "login_password": "invalid_login_pass_123",
                "master_password": "invalid_master_pass_123",
            },
        ),
        ("/api/auth/login", {"username": "foo", "login_password": "invalid_login_pass_123"}),
        ("/api/vault/unlock", {"master_password": "invalid_master_pass_123"}),
        (
            "/api/vault/entries",
            {
                "master_password": "invalid_master_pass_123",
                "service": "foo",
                "username": "u",
                "password": "invalid_entry_pass_123",
            },
        ),
        (
            "/api/shares",
            {
                "master_password": "invalid_master_pass_123",
                "entry_id": "foo",
                "recipient_username": "bar",
            },
        ),
        ("/api/utils/strength", {"password": "invalid_strength_pass_123"}),
    ]

    for path, payload in endpoints:
        res = client.post(path, json=payload)
        resp_text = res.text
        for k, v in payload.items():
            if "pass" in k.lower():
                assert v not in resp_text, f"Endpoint {path} echoes {k} in response: {resp_text}"


def test_unlock_wrong_master_password():
    """Verify wrong master password on /api/vault/unlock returns HTTP 200 with entries and sigil."""
    username = f"test_{secrets.token_hex(4)}"
    login_pw = "login_" + secrets.token_hex(8)
    master_pw = "master_" + secrets.token_hex(8)

    res = client.post(
        "/api/auth/register",
        json={"username": username, "login_password": login_pw, "master_password": master_pw},
    )
    assert res.status_code == 201

    res = client.post("/api/auth/login", json={"username": username, "login_password": login_pw})
    assert res.status_code == 200
    token = res.json()["access_token"]

    res = client.post(
        "/api/vault/unlock",
        json={"master_password": "wrong_password_123"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert res.status_code == 200
    data = res.json()
    assert "entries" in data
    assert "sigil" in data


@pytest.mark.skipif(not settings.demo_mode, reason="DEMO_MODE is disabled")
@pytest.mark.parametrize(
    "method, endpoint",
    [
        ("post", "/api/shares/test-id/tamper"),
        ("get", "/api/attack/stolen-vault"),
        ("post", "/api/attack/dictionary"),
        ("get", "/api/attack/stolen-honeywords"),
        ("get", "/api/attack/alarms"),
    ],
)
def test_demo_mode_endpoints(method, endpoint):
    """Mark intentional DEMO_MODE-only endpoints with explicit skip reasons rather than failing."""
    # We just make sure they don't return 404 because of "Demo mode disabled"
    # (Since we are skipping if demo_mode is disabled, this code only runs when enabled).
    if method == "get":
        res = client.get(endpoint)
    else:
        res = client.post(endpoint, json={})

    # The endpoints might return 404 for other reasons (e.g. "Demo user not found")
    # But they should NOT return the explicit "Demo mode disabled" detail.
    if res.status_code == 404:
        assert res.json().get("detail") != "Demo mode disabled"
