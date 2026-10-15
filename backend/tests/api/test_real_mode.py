"""End-to-end API flow on the REAL honeycore (PCFG DTEs, Argon2id, AES-256-CTR).

Owner: T1 — Nidhi (integration check for ``HONEYCORE_IMPL=real``).

The ``get_honeycore`` dependency is overridden with ``load_honeycore("real")`` and the
honeychecker with an in-memory fake (same pattern as ``tests/api/test_auth.py``). Vault and
honeyword KDFs use the fast ``demo`` profile so the test stays quick.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.deps import get_honeycore
from app.rate_limit import limiter
from app.services.honeychecker_client import HoneycheckerClient, get_honeychecker_client
from honeycore.dte import password_dte, username_dte
from honeycore.dte.pcfg import is_valid_field
from honeycore.factory import load_honeycore
from honeycore.interfaces import ENTRY_SEED_LEN
from honeycore.vault import SCHEME

pytestmark = pytest.mark.skipif(
    not (password_dte.DEFAULT_MODEL_PATH.exists() and username_dte.DEFAULT_MODEL_PATH.exists()),
    reason="default PCFG models not trained yet (scripts/train_pcfg.py)",
)

LOGIN_PW = "Login-pass-123!"
MASTER_PW = "Master-pass-456@"
ENTRY = {"service": "github.com", "username": "octo_dev", "password": "Tr0ub4dor&3"}


class FakeHoneycheckerClient(HoneycheckerClient):
    """In-memory honeychecker: remembers the real sweetword index per user."""

    def __init__(self) -> None:
        self.indices: dict[str, int] = {}

    def register(self, user_id: str, index: int) -> None:
        self.indices[user_id] = index

    def check(self, user_id: str, index: int) -> bool:
        return self.indices.get(user_id) == index

    def health(self) -> bool:
        return True


@pytest.fixture
def real_client(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """The API client wired to the real honeycore, a fake honeychecker and demo KDF profiles."""
    monkeypatch.setenv("VAULT_KDF_PROFILE", "demo")
    monkeypatch.setenv("HONEYWORDS_KDF_PROFILE", "demo")
    get_settings.cache_clear()
    limiter.reset()
    real = load_honeycore("real")
    fake_hc = FakeHoneycheckerClient()
    client.app.dependency_overrides[get_honeycore] = lambda: real
    client.app.dependency_overrides[get_honeychecker_client] = lambda: fake_hc
    yield client
    client.app.dependency_overrides.pop(get_honeycore, None)
    client.app.dependency_overrides.pop(get_honeychecker_client, None)
    limiter.reset()
    get_settings.cache_clear()  # monkeypatch restores the env after this fixture


def _register_and_login(client: TestClient) -> dict[str, str]:
    username = f"real_{uuid.uuid4().hex[:8]}"
    reg = client.post(
        "/api/auth/register",
        json={"username": username, "login_password": LOGIN_PW, "master_password": MASTER_PW},
    )
    assert reg.status_code == 201, reg.text
    login = client.post("/api/auth/login", json={"username": username, "login_password": LOGIN_PW})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_register_add_unlock_right_and_wrong(real_client: TestClient) -> None:
    headers = _register_and_login(real_client)

    added = real_client.post(
        "/api/vault/entries", json={"master_password": MASTER_PW, **ENTRY}, headers=headers
    )
    assert added.status_code == 201, added.text
    entry_id = added.json()["id"]

    blob = real_client.get("/api/vault/export", headers=headers).json()
    assert blob["scheme"] == SCHEME  # the real vault, not the stub
    assert blob["kdf"]["profile"] == "demo"
    assert blob["dte"] == {
        "password_model": "pcfg-password-v2",
        "username_model": "pcfg-username-v1",
        "entry_seed_len": ENTRY_SEED_LEN,
    }

    right = real_client.post(
        "/api/vault/unlock", json={"master_password": MASTER_PW}, headers=headers
    )
    assert right.status_code == 200, right.text
    [entry] = right.json()["entries"]
    assert entry["id"] == entry_id
    assert {k: entry[k] for k in ENTRY} == ENTRY

    wrong = real_client.post(
        "/api/vault/unlock", json={"master_password": MASTER_PW + "x"}, headers=headers
    )
    assert wrong.status_code == 200, wrong.text
    body = wrong.json()
    assert set(body) == set(right.json())
    [decoy] = body["entries"]
    assert set(decoy) == set(entry)
    assert (decoy["id"], decoy["service"]) == (entry_id, ENTRY["service"])
    assert is_valid_field(decoy["username"])
    assert is_valid_field(decoy["password"])
    assert (decoy["username"], decoy["password"]) != (ENTRY["username"], ENTRY["password"])
    assert body["sigil"] != right.json()["sigil"]
