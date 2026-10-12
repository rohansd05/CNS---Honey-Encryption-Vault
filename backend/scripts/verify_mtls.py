"""Verify mTLS enforcement between the API and Honeychecker.

Owner: T4 — Parth. Branch: feat/t4-mtls-verify.

Validates three connection scenarios against the Honeychecker microservice:
1. No client cert presented -> Handshake rejected / connection dropped (PASS)
2. Valid API client cert presented (signed by Service CA) -> HTTP 200 (PASS)
3. Client cert issued by an untrusted throwaway CA -> Handshake rejected / connection dropped (PASS)
"""

from __future__ import annotations

import datetime
import os
import ssl
import sys
import tempfile
from pathlib import Path
from typing import Any

import requests
import urllib3
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from urllib3.util.ssl_ import create_urllib3_context

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def resolve_pki_dir() -> Path:
    """Locate the pki/out directory relative to cwd or repository root."""
    candidates = [
        Path("pki/out"),
        Path(__file__).resolve().parent.parent.parent / "pki" / "out",
        Path(__file__).resolve().parent.parent / "pki" / "out",
        Path("../pki/out"),
    ]
    for c in candidates:
        if (c / "service-ca.crt").is_file():
            return c.resolve()

    msg = "Could not locate pki/out containing service-ca.crt in search paths."
    raise FileNotFoundError(msg)


def generate_throwaway_cert(out_dir: Path | str | None = None) -> tuple[str, str]:
    """Generate a self-signed throwaway CA and an issued client cert."""
    target_dir = Path(out_dir) if out_dir else Path.cwd()
    target_dir.mkdir(parents=True, exist_ok=True)

    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Throwaway CA")])
    now = datetime.datetime.now(datetime.UTC)

    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(issuer)
        .issuer_name(issuer)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )

    client_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client_subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "throwaway-user")])
    client_cert = (
        x509.CertificateBuilder()
        .subject_name(client_subject)
        .issuer_name(ca_cert.subject)
        .public_key(client_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )

    key_path = target_dir / "throwaway-client.key"
    crt_path = target_dir / "throwaway-client.crt"

    key_path.write_bytes(
        client_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    crt_path.write_bytes(client_cert.public_bytes(serialization.Encoding.PEM))

    return str(crt_path), str(key_path)


def cleanup_throwaway_cert(
    crt_path: str = "throwaway-client.crt", key_path: str = "throwaway-client.key"
) -> None:
    """Remove temporary throwaway certificate and private key files."""
    for p in (crt_path, key_path):
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


def build_ssl_context(
    ca_cert_path: str, client_cert: tuple[str, str] | None = None
) -> ssl.SSLContext:
    """Construct an SSLContext trusting the CA and optionally mounting a client certificate."""
    ctx = create_urllib3_context()
    # Python 3.13 enables STRICT verification by default which mandates AuthorityKeyIdentifier.
    if hasattr(ssl, "VERIFY_X509_STRICT"):
        ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT

    ctx.load_verify_locations(ca_cert_path)
    if client_cert and client_cert[0] and client_cert[1]:
        ctx.load_cert_chain(certfile=client_cert[0], keyfile=client_cert[1])
    return ctx


class _MTLSAdapter(requests.adapters.HTTPAdapter):
    """Custom HTTPAdapter injecting the configured mTLS SSLContext."""

    def __init__(
        self,
        ca_cert_path: str,
        client_cert: tuple[str, str] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.ca_cert_path = ca_cert_path
        self.client_cert = client_cert
        super().__init__(*args, **kwargs)

    def init_poolmanager(
        self,
        connections: int = 10,
        maxsize: int = 10,
        block: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        ctx = build_ssl_context(self.ca_cert_path, self.client_cert)
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(connections, maxsize, *args, block=block, **kwargs)


def _make_request(
    url: str,
    ca_cert_path: str,
    client_cert: tuple[str, str] | None = None,
    timeout: float = 5.0,
) -> requests.Response:
    """Issue a GET request using a scoped Session with the mTLS adapter."""
    with requests.Session() as s:
        s.mount("https://", _MTLSAdapter(ca_cert_path, client_cert))
        return s.get(url, timeout=timeout)


def run_tests(url: str = "https://localhost:8001/hc/health") -> list[tuple[str, str]]:
    """Execute mTLS verification tests and return test-result pairs."""
    pki_dir = resolve_pki_dir()
    ca_cert_path = str(pki_dir / "service-ca.crt")
    api_cert = (str(pki_dir / "api-client.crt"), str(pki_dir / "api-client.key"))

    results: list[tuple[str, str]] = []

    # -------------------------------------------------------------------------
    # Test 1: No client cert
    # -------------------------------------------------------------------------
    try:
        res = _make_request(url, ca_cert_path, client_cert=None, timeout=5.0)
        results.append(
            (
                "1. No client cert",
                f"FAIL (expected failure, got {res.status_code} {res.text})",
            )
        )
    except (requests.exceptions.SSLError, requests.exceptions.ConnectionError):
        results.append(("1. No client cert", "PASS"))
    except Exception as exc:
        results.append(("1. No client cert", f"FAIL (unexpected error: {exc})"))

    # -------------------------------------------------------------------------
    # Test 2: API client cert
    # -------------------------------------------------------------------------
    try:
        res = _make_request(url, ca_cert_path, client_cert=api_cert, timeout=5.0)
        if res.status_code == 200:
            results.append(("2. With API client cert", "PASS"))
        else:
            results.append(
                (
                    "2. With API client cert",
                    f"FAIL (got status {res.status_code}: {res.text})",
                )
            )
    except Exception as exc:
        results.append(("2. With API client cert", f"FAIL (error: {exc})"))

    # -------------------------------------------------------------------------
    # Test 3: Throwaway cert (untrusted CA)
    # -------------------------------------------------------------------------
    with tempfile.TemporaryDirectory() as tmp_dir:
        throwaway_crt, throwaway_key = generate_throwaway_cert(tmp_dir)
        try:
            res = _make_request(
                url,
                ca_cert_path,
                client_cert=(throwaway_crt, throwaway_key),
                timeout=5.0,
            )
            results.append(
                (
                    "3. With throwaway cert",
                    f"FAIL (expected failure, got {res.status_code})",
                )
            )
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError):
            results.append(("3. With throwaway cert", "PASS"))
        except Exception as exc:
            results.append(("3. With throwaway cert", f"FAIL (unexpected error: {exc})"))
        finally:
            cleanup_throwaway_cert(throwaway_crt, throwaway_key)

    return results


def main() -> int:
    """Print results table and exit with appropriate code."""
    results = run_tests()
    print(f"{'TEST':<30} | {'RESULT'}")
    print("-" * 50)
    all_passed = True
    for test, result in results:
        print(f"{test:<30} | {result}")
        if result != "PASS":
            all_passed = False

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
