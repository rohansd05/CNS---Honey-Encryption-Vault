"""Tests for /api/vault endpoints.

Owner: T2 — Tanuj.
Tests (HONEYCORE_IMPL=stub via fixtures):
- add 3 entries then unlock with the right password -> the same entries;
- a wrong password -> 200, same count/services, different values;
- update/delete/404;
- no auth -> 401;
- invalid field -> 422 without echoing the value;
- export has the v1 keys;
- unlock rate limit -> 429.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.models.core import User


@pytest.fixture()
def test_user(make_user) -> User:
    """Create a unique test user."""
    return make_user(f"vaultuser_{uuid.uuid4().hex[:8]}")


@pytest.fixture()
def headers(test_user: User, auth_headers) -> dict[str, str]:
    """Auth headers for test_user."""
    return auth_headers(test_user)


MASTER_PW = "correct-horse-battery-staple"
WRONG_PW = "wrong-horse-battery-staple"


def test_add_3_entries_and_unlock_right_password(client: TestClient, headers: dict[str, str]):
    """Add 3 entries then unlock with the right password -> returns the exact same entries."""
    entries_data = [
        {"service": "github.com", "username": "alice_gh", "password": "password123!"},
        {"service": "google.com", "username": "alice_mail", "password": "password456@"},
        {"service": "slack.com", "username": "alice_work", "password": "password789#"},
    ]

    created_ids = []
    for item in entries_data:
        res = client.post(
            "/api/vault/entries",
            headers=headers,
            json={"master_password": MASTER_PW, **item},
        )
        assert res.status_code == 201
        data = res.json()
        assert "id" in data
        created_ids.append(data["id"])

    assert len(created_ids) == 3

    # Unlock with the right master password
    unlock_res = client.post(
        "/api/vault/unlock",
        headers=headers,
        json={"master_password": MASTER_PW},
    )
    assert unlock_res.status_code == 200
    vault_data = unlock_res.json()

    assert "entries" in vault_data
    assert "sigil" in vault_data
    assert len(vault_data["entries"]) == 3

    # Verify each entry recovered matches what was stored
    for i, orig in enumerate(entries_data):
        rec = vault_data["entries"][i]
        assert rec["id"] == created_ids[i]
        assert rec["service"] == orig["service"]
        assert rec["username"] == orig["username"]
        assert rec["password"] == orig["password"]

    # Sigil verification
    sigil = vault_data["sigil"]
    assert len(sigil["emojis"]) == 3
    assert sigil["color"].startswith("#")


def test_wrong_password_returns_200_decoy_vault(client: TestClient, headers: dict[str, str]):
    """A wrong password -> 200, same count/services, different values & different sigil."""
    entries_data = [
        {"service": "github.com", "username": "alice_gh", "password": "password123!"},
        {"service": "google.com", "username": "alice_mail", "password": "password456@"},
        {"service": "slack.com", "username": "alice_work", "password": "password789#"},
    ]

    for item in entries_data:
        client.post(
            "/api/vault/entries",
            headers=headers,
            json={"master_password": MASTER_PW, **item},
        )

    # Unlock with the correct password first to capture truth
    real_res = client.post(
        "/api/vault/unlock",
        headers=headers,
        json={"master_password": MASTER_PW},
    )
    assert real_res.status_code == 200
    real_data = real_res.json()

    # Unlock with WRONG password: must return 200 and well-formed shape
    wrong_res = client.post(
        "/api/vault/unlock",
        headers=headers,
        json={"master_password": WRONG_PW},
    )
    assert wrong_res.status_code == 200
    decoy_data = wrong_res.json()

    assert len(decoy_data["entries"]) == 3
    for i in range(3):
        # Service is public metadata (ADR-001) so it matches
        assert decoy_data["entries"][i]["service"] == real_data["entries"][i]["service"]
        # Decrypted content differs (honey decoy)
        assert decoy_data["entries"][i]["username"] != real_data["entries"][i]["username"]
        assert decoy_data["entries"][i]["password"] != real_data["entries"][i]["password"]

    # Sigil should also differ
    assert decoy_data["sigil"] != real_data["sigil"]


def test_update_delete_and_404(client: TestClient, headers: dict[str, str]):
    """Test updating an entry, deleting an entry, and 404 on missing entry id."""
    # Add 2 entries
    r1 = client.post(
        "/api/vault/entries",
        headers=headers,
        json={
            "master_password": MASTER_PW,
            "service": "github.com",
            "username": "user1",
            "password": "pass1",
        },
    )
    r2 = client.post(
        "/api/vault/entries",
        headers=headers,
        json={
            "master_password": MASTER_PW,
            "service": "gitlab.com",
            "username": "user2",
            "password": "pass2",
        },
    )
    id1 = r1.json()["id"]
    id2 = r2.json()["id"]

    # Update entry 1
    up_res = client.put(
        f"/api/vault/entries/{id1}",
        headers=headers,
        json={
            "master_password": MASTER_PW,
            "service": "github.com",
            "username": "user1_updated",
            "password": "pass1_updated",
        },
    )
    assert up_res.status_code == 200
    assert up_res.json()["id"] == id1

    # Verify update via unlock
    unlock1 = client.post(
        "/api/vault/unlock",
        headers=headers,
        json={"master_password": MASTER_PW},
    )
    entries = {e["id"]: e for e in unlock1.json()["entries"]}
    assert entries[id1]["username"] == "user1_updated"
    assert entries[id1]["password"] == "pass1_updated"  # noqa: S105

    # Delete entry 2
    del_res = client.delete(f"/api/vault/entries/{id2}", headers=headers)
    assert del_res.status_code == 204

    # Verify delete via unlock
    unlock2 = client.post(
        "/api/vault/unlock",
        headers=headers,
        json={"master_password": MASTER_PW},
    )
    remaining_ids = [e["id"] for e in unlock2.json()["entries"]]
    assert id1 in remaining_ids
    assert id2 not in remaining_ids

    # 404 tests for unknown entry id
    missing_id = str(uuid.uuid4())
    up_404 = client.put(
        f"/api/vault/entries/{missing_id}",
        headers=headers,
        json={
            "master_password": MASTER_PW,
            "service": "github.com",
            "username": "ghost",
            "password": "ghostpass",
        },
    )
    assert up_404.status_code == 404
    assert up_404.json() == {"detail": "Entry not found"}

    del_404 = client.delete(f"/api/vault/entries/{missing_id}", headers=headers)
    assert del_404.status_code == 404
    assert del_404.json() == {"detail": "Entry not found"}


def test_no_auth_returns_401(client: TestClient):
    """Endpoints require valid JWT auth; unauthenticated requests return 401."""
    # unlock
    r_unlock = client.post("/api/vault/unlock", json={"master_password": MASTER_PW})
    assert r_unlock.status_code == 401

    # add entry
    r_add = client.post(
        "/api/vault/entries",
        json={
            "master_password": MASTER_PW,
            "service": "github.com",
            "username": "u",
            "password": "p",
        },
    )
    assert r_add.status_code == 401

    # update entry
    r_update = client.put(
        f"/api/vault/entries/{uuid.uuid4()}",
        json={
            "master_password": MASTER_PW,
            "service": "github.com",
            "username": "u",
            "password": "p",
        },
    )
    assert r_update.status_code == 401

    # delete entry
    r_del = client.delete(f"/api/vault/entries/{uuid.uuid4()}")
    assert r_del.status_code == 401

    # export
    r_exp = client.get("/api/vault/export")
    assert r_exp.status_code == 401


def test_invalid_field_returns_422_without_echoing_value(
    client: TestClient, headers: dict[str, str]
):
    """Validation errors return 422 and must NEVER echo the invalid input value."""
    secret_pw = "secret_bad_\x00_pwd"  # noqa: S105
    res = client.post(
        "/api/vault/entries",
        headers=headers,
        json={
            "master_password": MASTER_PW,
            "service": "github.com",
            "username": "alice",
            "password": secret_pw,
        },
    )
    assert res.status_code == 422
    assert secret_pw not in res.text

    # Service too long (> 64 chars)
    long_service = "s" * 65
    res_service = client.post(
        "/api/vault/entries",
        headers=headers,
        json={
            "master_password": MASTER_PW,
            "service": long_service,
            "username": "alice",
            "password": "pwd",
        },
    )
    assert res_service.status_code == 422

    # Username too long (> 32 chars)
    long_username = "u" * 33
    res_user = client.post(
        "/api/vault/entries",
        headers=headers,
        json={
            "master_password": MASTER_PW,
            "service": "github.com",
            "username": long_username,
            "password": "pwd",
        },
    )
    assert res_user.status_code == 422
    assert long_username not in res_user.text

    # Non-printable username
    res_np = client.post(
        "/api/vault/entries",
        headers=headers,
        json={
            "master_password": MASTER_PW,
            "service": "github.com",
            "username": "alice\nadmin",
            "password": "pwd",
        },
    )
    assert res_np.status_code == 422


def test_export_has_v1_keys(client: TestClient, headers: dict[str, str]):
    """Exporting the vault returns a dict satisfying the blob v1 layout."""
    res = client.get("/api/vault/export", headers=headers)
    assert res.status_code == 200
    blob = res.json()

    assert blob["format"] == "honeyvault"
    assert blob["version"] == 1
    assert "scheme" in blob

    kdf = blob["kdf"]
    assert "alg" in kdf
    assert "profile" in kdf
    assert "salt" in kdf
    assert "time_cost" in kdf
    assert "memory_cost_kib" in kdf
    assert "parallelism" in kdf
    assert "hash_len" in kdf

    dte = blob["dte"]
    assert "password_model" in dte
    assert "username_model" in dte
    assert dte["entry_seed_len"] == 532

    assert isinstance(blob["entries"], list)


def test_unlock_rate_limit_returns_429(client: TestClient, make_user, auth_headers):
    """POST /api/vault/unlock enforces rate limiting (10/minute per user -> 429)."""
    user = make_user("rate_limited_user")
    user_headers = auth_headers(user)

    # 10 calls should succeed
    for _ in range(10):
        r = client.post(
            "/api/vault/unlock",
            headers=user_headers,
            json={"master_password": MASTER_PW},
        )
        assert r.status_code == 200

    # 11th call exceeds the rate limit
    r_exceeded = client.post(
        "/api/vault/unlock",
        headers=user_headers,
        json={"master_password": MASTER_PW},
    )
    assert r_exceeded.status_code == 429
    assert r_exceeded.json() == {"detail": "Rate limit exceeded"}
    assert "Retry-After" in r_exceeded.headers
