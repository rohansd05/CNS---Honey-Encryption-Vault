"""Unit tests for pure helper functions in scripts/verify_mtls.py.

Owner: T4 — Parth. Branch: feat/t4-mtls-verify.
"""

from __future__ import annotations

import os
import ssl
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from honeycore.pki import build_root_ca, generate_ec_key, issue_leaf
from scripts.verify_mtls import (
    _MTLSAdapter,
    build_ssl_context,
    cleanup_throwaway_cert,
    generate_throwaway_cert,
    resolve_pki_dir,
)


@pytest.fixture
def pki_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a throwaway service CA + api-client cert/key under ``tmp_path/pki/out``.

    Uses the same file names as ``pki/make_service_ca.py`` / ``issue_service_certs.py``,
    then chdirs into ``tmp_path`` so ``resolve_pki_dir()`` finds ``pki/out`` first and
    never touches the developer's real (gitignored) ``pki/out``.
    """
    out_dir = tmp_path / "pki" / "out"
    out_dir.mkdir(parents=True)

    ca_cert_pem, ca_key_pem = build_root_ca("Test Service CA", days=1)
    client_key = generate_ec_key()
    client_public_pem = client_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    client_cert_pem = issue_leaf(
        ca_cert_pem,
        ca_key_pem,
        cn="honeyvault-api",
        public_pem=client_public_pem,
        days=1,
        eku_client_auth=True,
    )
    client_key_pem = client_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    (out_dir / "service-ca.crt").write_bytes(ca_cert_pem)
    (out_dir / "api-client.crt").write_bytes(client_cert_pem)
    (out_dir / "api-client.key").write_bytes(client_key_pem)

    monkeypatch.chdir(tmp_path)
    return out_dir.resolve()


def test_resolve_pki_dir(pki_out: Path) -> None:
    """Verify resolve_pki_dir locates the directory containing service-ca.crt."""
    pki_dir = resolve_pki_dir()
    assert pki_dir.is_dir()
    assert (pki_dir / "service-ca.crt").is_file()
    assert pki_dir == pki_out


def test_generate_and_cleanup_throwaway_cert(tmp_path: Path) -> None:
    """Verify throwaway cert and key generation attributes and cleanup."""
    crt_path, key_path = generate_throwaway_cert(tmp_path)
    assert os.path.isfile(crt_path)
    assert os.path.isfile(key_path)

    # Parse and validate the generated X.509 certificate
    cert_data = Path(crt_path).read_bytes()
    cert = x509.load_pem_x509_certificate(cert_data)

    subject_cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    issuer_cn = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    assert subject_cn == "throwaway-user"
    assert issuer_cn == "Throwaway CA"

    # Validate EKU contains clientAuth
    eku_ext = cert.extensions.get_extension_for_oid(x509.ExtensionOID.EXTENDED_KEY_USAGE)
    assert ExtendedKeyUsageOID.CLIENT_AUTH in eku_ext.value  # type: ignore[operator]

    # Validate public key is RSA
    assert isinstance(cert.public_key(), rsa.RSAPublicKey)

    # Clean up and verify deletion
    cleanup_throwaway_cert(crt_path, key_path)
    assert not os.path.exists(crt_path)
    assert not os.path.exists(key_path)


def test_build_ssl_context(pki_out: Path) -> None:
    """Verify build_ssl_context configures CA verify locations and client certificate."""
    pki_dir = resolve_pki_dir()
    ca_path = str(pki_dir / "service-ca.crt")
    api_cert = (str(pki_dir / "api-client.crt"), str(pki_dir / "api-client.key"))

    # Context without client cert
    ctx = build_ssl_context(ca_path)
    assert isinstance(ctx, ssl.SSLContext)
    if hasattr(ssl, "VERIFY_X509_STRICT"):
        assert not (ctx.verify_flags & ssl.VERIFY_X509_STRICT)

    # Context with client cert
    ctx_client = build_ssl_context(ca_path, client_cert=api_cert)
    assert isinstance(ctx_client, ssl.SSLContext)


def test_mtls_adapter_init_poolmanager(pki_out: Path) -> None:
    """Verify _MTLSAdapter injects the configured SSLContext into poolmanager kwargs."""
    pki_dir = resolve_pki_dir()
    ca_path = str(pki_dir / "service-ca.crt")
    adapter = _MTLSAdapter(ca_cert_path=ca_path)

    adapter.init_poolmanager(connections=5, maxsize=5)
    assert adapter.poolmanager is not None
    assert adapter.ca_cert_path == ca_path
    assert adapter.client_cert is None
