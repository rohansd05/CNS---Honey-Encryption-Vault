"""Unit tests for pure helper functions in scripts/verify_mtls.py.

Owner: T4 — Parth. Branch: feat/t4-mtls-verify.
"""

from __future__ import annotations

import os
import ssl
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from scripts.verify_mtls import (
    _MTLSAdapter,
    build_ssl_context,
    cleanup_throwaway_cert,
    generate_throwaway_cert,
    resolve_pki_dir,
)


def test_resolve_pki_dir() -> None:
    """Verify resolve_pki_dir locates the directory containing service-ca.crt."""
    pki_dir = resolve_pki_dir()
    assert pki_dir.is_dir()
    assert (pki_dir / "service-ca.crt").is_file()


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


def test_build_ssl_context() -> None:
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


def test_mtls_adapter_init_poolmanager() -> None:
    """Verify _MTLSAdapter injects the configured SSLContext into poolmanager kwargs."""
    pki_dir = resolve_pki_dir()
    ca_path = str(pki_dir / "service-ca.crt")
    adapter = _MTLSAdapter(ca_cert_path=ca_path)

    adapter.init_poolmanager(connections=5, maxsize=5)
    assert adapter.poolmanager is not None
    assert adapter.ca_cert_path == ca_path
    assert adapter.client_cert is None
