"""Security tests for honeychecker verify_caller (Phase 4, feat/t4-hc-security).

Owner: T4 — Parth.

Coverage:
- plain transport → all endpoints open (no auth).
- signed transport → valid signed request → 200 on POST /hc/check.
- signed transport → wrong CN → 401.
- signed transport → user identity cert (Root → Issuing CA, not Service CA) → 401.
- signed transport → stale timestamp (> 60 s skew) → 401.
- signed transport → nonce replay (same nonce twice) → 401.
- signed transport → tampered body → 401.
- /hc/health always open regardless of transport.

All PKI material is generated in-process; no pki/out/ files are read.
"""

from __future__ import annotations

import base64
import time
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Import honeycore helpers (backend/ is on sys.path via pyproject.toml)
# ---------------------------------------------------------------------------
from honeycore.pki import build_issuing_ca, build_root_ca, generate_ec_key, issue_leaf
from honeycore.transport import ReplayCache, sign_request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db import Base, get_db
from app.main import create_app

# ---------------------------------------------------------------------------
# PKI fixtures — generated once per session for speed
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def root_ca_pem() -> tuple[bytes, bytes]:
    """Self-signed Root CA (user-identity hierarchy)."""
    return build_root_ca(cn="Test Root CA", days=3650)


@pytest.fixture(scope="session")
def issuing_ca_pem(root_ca_pem: tuple[bytes, bytes]) -> tuple[bytes, bytes]:
    """Issuing CA signed by Root CA (user-identity hierarchy)."""
    root_cert, root_key = root_ca_pem
    return build_issuing_ca(root_cert, root_key, cn="Test Issuing CA", days=1825)


@pytest.fixture(scope="session")
def service_ca_pem() -> tuple[bytes, bytes]:
    """Self-signed Service CA (service-to-service hierarchy)."""
    return build_root_ca(cn="Test Service CA", days=3650)


@pytest.fixture(scope="session")
def api_client_cert_pem(service_ca_pem: tuple[bytes, bytes]) -> tuple[bytes, bytes]:
    """api-client leaf cert issued by Service CA (EKU clientAuth, CN=honeyvault-api)."""
    svc_cert, svc_key = service_ca_pem
    priv = generate_ec_key()
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    cert_pem = issue_leaf(
        issuer_cert_pem=svc_cert,
        issuer_key_pem=svc_key,
        cn="honeyvault-api",
        public_pem=pub_pem,
        days=365,
        eku_client_auth=True,
    )
    key_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return cert_pem, key_pem


@pytest.fixture(scope="session")
def wrong_cn_cert_pem(service_ca_pem: tuple[bytes, bytes]) -> tuple[bytes, bytes]:
    """Leaf cert with wrong CN (CN=evil-service) issued by Service CA."""
    svc_cert, svc_key = service_ca_pem
    priv = generate_ec_key()
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    cert_pem = issue_leaf(
        issuer_cert_pem=svc_cert,
        issuer_key_pem=svc_key,
        cn="evil-service",
        public_pem=pub_pem,
        days=365,
        eku_client_auth=True,
    )
    key_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return cert_pem, key_pem


@pytest.fixture(scope="session")
def user_identity_cert_pem(issuing_ca_pem: tuple[bytes, bytes]) -> tuple[bytes, bytes]:
    """User identity cert: Root → Issuing CA → 'honeyvault-api'.

    Despite having CN=honeyvault-api, it MUST be rejected by the honeychecker
    because its chain terminates at the Issuing CA, which is NOT in the
    honeychecker's trust store (Service CA only).
    """
    iss_cert, iss_key = issuing_ca_pem
    priv = generate_ec_key()
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    # Deliberately give it the correct CN so the only difference is the issuer chain
    cert_pem = issue_leaf(
        issuer_cert_pem=iss_cert,
        issuer_key_pem=iss_key,
        cn="honeyvault-api",
        public_pem=pub_pem,
        days=365,
        eku_client_auth=True,
    )
    key_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return cert_pem, key_pem


# ---------------------------------------------------------------------------
# App / client fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """In-memory SQLite session for test isolation."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _make_signed_client(
    db_session: Session,
    service_ca_cert_b64: str,
    *,
    allowed_cn: str = "honeyvault-api",
) -> TestClient:
    """Create a TestClient whose app is configured for signed transport."""
    settings = Settings(
        hc_transport="signed",
        hc_trusted_ca_cert_b64=service_ca_cert_b64,
        hc_allowed_client_cn=allowed_cn,
        hc_database_url="sqlite:///:memory:",
    )
    application = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    application.dependency_overrides[get_db] = override_get_db

    # Patch settings so verify_caller picks up our test settings.
    with (
        patch("app.security.get_settings", return_value=settings),
        patch("app.config.get_settings", return_value=settings),
    ):
        client = TestClient(application, raise_server_exceptions=False)
    return client


def _sign_and_post(
    path: str,
    body: bytes,
    cert_pem: bytes,
    key_pem: bytes,
    service_ca_pem_bytes: bytes,
    db_session: Session,
    *,
    allowed_cn: str = "honeyvault-api",
    override_now: float | None = None,
    override_headers: dict[str, str] | None = None,
    override_body_for_sig: bytes | None = None,
    replay_cache: ReplayCache | None = None,
) -> Any:
    """Sign a request and POST it; returns the httpx Response."""
    if replay_cache is None:
        replay_cache = ReplayCache()

    ca_b64 = base64.b64encode(service_ca_pem_bytes).decode("ascii")
    settings = Settings(
        hc_transport="signed",
        hc_trusted_ca_cert_b64=ca_b64,
        hc_allowed_client_cn=allowed_cn,
        hc_database_url="sqlite:///:memory:",
    )
    application = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    application.dependency_overrides[get_db] = override_get_db

    with (
        patch("app.security.get_settings", return_value=settings),
        patch("app.config.get_settings", return_value=settings),
        patch("app.security._get_replay_cache", return_value=replay_cache),
    ):
        # Sign the (possibly overridden) body
        body_for_sig = override_body_for_sig if override_body_for_sig is not None else body
        hv_headers = sign_request(
            method="POST",
            path=path,
            body=body_for_sig,
            client_cert_pem=cert_pem,
            client_key_pem=key_pem,
            now=override_now,
        )
        if override_headers:
            hv_headers.update(override_headers)

        with TestClient(application, raise_server_exceptions=False) as client:
            return client.post(
                path,
                content=body,
                headers={**hv_headers, "content-type": "application/json"},
            )


# ---------------------------------------------------------------------------
# Test: plain transport
# ---------------------------------------------------------------------------


class TestPlainTransport:
    """plain transport: all endpoints open (no auth)."""

    @pytest.fixture()
    def client(self, db_session: Session) -> Generator[TestClient, None, None]:
        settings = Settings(hc_transport="plain", hc_database_url="sqlite:///:memory:")
        application = create_app()

        def override_get_db() -> Generator[Session, None, None]:
            yield db_session

        application.dependency_overrides[get_db] = override_get_db
        with (
            patch("app.security.get_settings", return_value=settings),
            patch("app.config.get_settings", return_value=settings),
        ):
            with TestClient(application) as c:
                yield c

    def test_plain_register_ok(self, client: TestClient) -> None:
        resp = client.post("/hc/register", json={"user_id": "u1", "index": 0})
        assert resp.status_code == 201

    def test_plain_check_ok(self, client: TestClient) -> None:
        client.post("/hc/register", json={"user_id": "u2", "index": 3})
        resp = client.post("/hc/check", json={"user_id": "u2", "index": 3})
        assert resp.status_code == 200
        assert resp.json()["match"] is True

    def test_plain_health_open(self, client: TestClient) -> None:
        resp = client.get("/hc/health")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Test: signed transport — valid request
# ---------------------------------------------------------------------------


class TestSignedTransportValid:
    """signed transport: valid api-client cert → 200."""

    def test_signed_check_valid(
        self,
        db_session: Session,
        service_ca_pem: tuple[bytes, bytes],
        api_client_cert_pem: tuple[bytes, bytes],
    ) -> None:
        svc_ca_cert, _ = service_ca_pem
        cert_pem, key_pem = api_client_cert_pem

        # Pre-register so /hc/check can return a match
        body_reg = b'{"user_id": "s-valid", "index": 2}'
        _sign_and_post(
            path="/hc/register",
            body=body_reg,
            cert_pem=cert_pem,
            key_pem=key_pem,
            service_ca_pem_bytes=svc_ca_cert,
            db_session=db_session,
        )

        body_chk = b'{"user_id": "s-valid", "index": 2}'
        resp = _sign_and_post(
            path="/hc/check",
            body=body_chk,
            cert_pem=cert_pem,
            key_pem=key_pem,
            service_ca_pem_bytes=svc_ca_cert,
            db_session=db_session,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["match"] is True


# ---------------------------------------------------------------------------
# Test: signed transport — rejection cases
# ---------------------------------------------------------------------------


class TestSignedTransportRejected:
    """signed transport: various invalid requests → 401."""

    def test_wrong_cn_rejected(
        self,
        db_session: Session,
        service_ca_pem: tuple[bytes, bytes],
        wrong_cn_cert_pem: tuple[bytes, bytes],
    ) -> None:
        """Cert with wrong CN (evil-service) must be rejected with 401."""
        svc_ca_cert, _ = service_ca_pem
        cert_pem, key_pem = wrong_cn_cert_pem

        resp = _sign_and_post(
            path="/hc/check",
            body=b'{"user_id": "x", "index": 0}',
            cert_pem=cert_pem,
            key_pem=key_pem,
            service_ca_pem_bytes=svc_ca_cert,
            db_session=db_session,
        )
        assert resp.status_code == 401
        # Must not leak the reason
        assert resp.json() == {"detail": "unauthorized caller"}

    def test_user_identity_cert_rejected(
        self,
        db_session: Session,
        service_ca_pem: tuple[bytes, bytes],
        user_identity_cert_pem: tuple[bytes, bytes],
    ) -> None:
        """User identity cert (Root → Issuing CA → honeyvault-api) must be rejected.

        Even though CN=honeyvault-api, the chain does not terminate at the Service CA,
        so verify_certificate raises InvalidSignatureError and we get a 401.
        """
        svc_ca_cert, _ = service_ca_pem
        cert_pem, key_pem = user_identity_cert_pem

        resp = _sign_and_post(
            path="/hc/check",
            body=b'{"user_id": "x", "index": 0}',
            cert_pem=cert_pem,
            key_pem=key_pem,
            service_ca_pem_bytes=svc_ca_cert,
            db_session=db_session,
        )
        assert resp.status_code == 401
        assert resp.json() == {"detail": "unauthorized caller"}

    def test_stale_timestamp_rejected(
        self,
        db_session: Session,
        service_ca_pem: tuple[bytes, bytes],
        api_client_cert_pem: tuple[bytes, bytes],
    ) -> None:
        """Timestamp > 60 s in the past → 401."""
        svc_ca_cert, _ = service_ca_pem
        cert_pem, key_pem = api_client_cert_pem
        stale_now = time.time() - 120  # 2 minutes ago

        resp = _sign_and_post(
            path="/hc/check",
            body=b'{"user_id": "x", "index": 0}',
            cert_pem=cert_pem,
            key_pem=key_pem,
            service_ca_pem_bytes=svc_ca_cert,
            db_session=db_session,
            override_now=stale_now,
        )
        assert resp.status_code == 401
        assert resp.json() == {"detail": "unauthorized caller"}

    def test_nonce_replay_rejected(
        self,
        db_session: Session,
        service_ca_pem: tuple[bytes, bytes],
        api_client_cert_pem: tuple[bytes, bytes],
    ) -> None:
        """Replaying the same nonce a second time → 401."""
        svc_ca_cert, _ = service_ca_pem
        cert_pem, key_pem = api_client_cert_pem
        shared_cache = ReplayCache(ttl_seconds=300)
        body = b'{"user_id": "replay-user", "index": 0}'

        # First request must succeed (or at least not 401 on security grounds).
        resp1 = _sign_and_post(
            path="/hc/check",
            body=body,
            cert_pem=cert_pem,
            key_pem=key_pem,
            service_ca_pem_bytes=svc_ca_cert,
            db_session=db_session,
            replay_cache=shared_cache,
        )
        # Should be 200 (user not registered → match=False, but not 401)
        assert resp1.status_code != 401, f"First request should not 401: {resp1.text}"

        # Second request with the SAME nonce must 401.
        # We need to capture the nonce from the first signed request headers.
        # Instead, we construct a helper that reuses a fixed nonce.
        fixed_nonce = "AAAAAAAAAAAAAAAAAAAAAA"  # 22 URL-safe base64 chars = 16 bytes

        ca_b64 = base64.b64encode(svc_ca_cert).decode("ascii")
        settings = Settings(
            hc_transport="signed",
            hc_trusted_ca_cert_b64=ca_b64,
            hc_allowed_client_cn="honeyvault-api",
            hc_database_url="sqlite:///:memory:",
        )
        application = create_app()

        def override_get_db() -> Generator[Session, None, None]:
            yield db_session

        application.dependency_overrides[get_db] = override_get_db

        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        from honeycore.transport import _b64_encode, canonical_request

        ts = str(int(time.time()))
        priv_key = serialization.load_pem_private_key(key_pem, password=None)
        to_sign = canonical_request("POST", "/hc/check", ts, fixed_nonce, body)
        der_sig = priv_key.sign(to_sign, ec.ECDSA(hashes.SHA256()))  # type: ignore[arg-type]

        hv_headers = {
            "X-HV-Cert": _b64_encode(cert_pem),
            "X-HV-Timestamp": ts,
            "X-HV-Nonce": fixed_nonce,
            "X-HV-Signature": _b64_encode(der_sig),
        }

        # Use a fresh cache; add the nonce to simulate it already being seen.
        fresh_cache = ReplayCache(ttl_seconds=300)
        fresh_cache.seen_or_add(fixed_nonce)  # pre-populate

        with (
            patch("app.security.get_settings", return_value=settings),
            patch("app.config.get_settings", return_value=settings),
            patch("app.security._get_replay_cache", return_value=fresh_cache),
        ):
            with TestClient(application, raise_server_exceptions=False) as client:
                resp2 = client.post(
                    "/hc/check",
                    content=body,
                    headers={**hv_headers, "content-type": "application/json"},
                )
        assert resp2.status_code == 401
        assert resp2.json() == {"detail": "unauthorized caller"}

    def test_tampered_body_rejected(
        self,
        db_session: Session,
        service_ca_pem: tuple[bytes, bytes],
        api_client_cert_pem: tuple[bytes, bytes],
    ) -> None:
        """Signature computed over original body; sending a tampered body → 401."""
        svc_ca_cert, _ = service_ca_pem
        cert_pem, key_pem = api_client_cert_pem
        original_body = b'{"user_id": "tamper-user", "index": 0}'
        tampered_body = b'{"user_id": "admin", "index": 0}'

        resp = _sign_and_post(
            path="/hc/check",
            body=tampered_body,  # send the tampered body ...
            cert_pem=cert_pem,
            key_pem=key_pem,
            service_ca_pem_bytes=svc_ca_cert,
            db_session=db_session,
            override_body_for_sig=original_body,  # ... but sign the original
        )
        assert resp.status_code == 401
        assert resp.json() == {"detail": "unauthorized caller"}


# ---------------------------------------------------------------------------
# Test: /hc/health always open
# ---------------------------------------------------------------------------


class TestHealthAlwaysOpen:
    """GET /hc/health must not require authentication in any transport mode."""

    @pytest.mark.parametrize("transport", ["plain", "signed", "mtls"])
    def test_health_open_all_transports(
        self,
        transport: str,
        db_session: Session,
        service_ca_pem: tuple[bytes, bytes],
    ) -> None:
        svc_ca_cert, _ = service_ca_pem
        ca_b64 = base64.b64encode(svc_ca_cert).decode("ascii")
        settings = Settings(
            hc_transport=transport,  # type: ignore[arg-type]
            hc_trusted_ca_cert_b64=ca_b64,
            hc_database_url="sqlite:///:memory:",
        )
        application = create_app()

        def override_get_db() -> Generator[Session, None, None]:
            yield db_session

        application.dependency_overrides[get_db] = override_get_db

        with (
            patch("app.security.get_settings", return_value=settings),
            patch("app.config.get_settings", return_value=settings),
        ):
            with TestClient(application, raise_server_exceptions=False) as client:
                resp = client.get("/hc/health")
        assert resp.status_code == 200, f"health failed for transport={transport}: {resp.text}"
