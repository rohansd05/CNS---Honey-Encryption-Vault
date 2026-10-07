"""Issue honeychecker-server and api-client leaf certificates from the Service CA.

Owner: T4 — Parth. Phase 4 (feat/t4-hc-security).

TRUST DOMAIN SEPARATION (see also pki/README.md):
These service certs are issued by the *Service CA*, not the Issuing CA.
The honeychecker's trust store contains only the Service CA, so:
  * A user identity cert (Root → Issuing CA → username) can never satisfy the
    honeychecker's chain validation — the chain terminates at the Issuing CA which is
    not trusted by the honeychecker.
  * Only api-client cert (Service CA → honeyvault-api) passes validation.

Run from the repository root::

    python pki/issue_service_certs.py

Prerequisites: ``pki/out/service-ca.crt`` and ``pki/out/service-ca.key`` must exist
(run ``python pki/make_service_ca.py`` first).

Output files (all in ``pki/out/``, all gitignored):
  * ``honeychecker-server.crt`` / ``honeychecker-server.key``  (TLS server cert, SAN localhost)
  * ``api-client.crt`` / ``api-client.key``                    (mTLS/signed client cert, EKU clientAuth)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from cryptography.hazmat.primitives import serialization  # noqa: E402

from honeycore.pki import generate_ec_key, issue_leaf  # noqa: E402


def main() -> None:
    out_dir = Path(__file__).parent / "out"
    out_dir.mkdir(exist_ok=True)

    # Load the Service CA (not the user-identity Issuing CA)
    service_ca_cert = (out_dir / "service-ca.crt").read_bytes()
    service_ca_key = (out_dir / "service-ca.key").read_bytes()

    # ------------------------------------------------------------------
    # 1. honeychecker-server  (TLS server cert; SAN: localhost, honeychecker)
    # ------------------------------------------------------------------
    hc_priv = generate_ec_key()
    hc_pub = hc_priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    hc_cert = issue_leaf(
        issuer_cert_pem=service_ca_cert,
        issuer_key_pem=service_ca_key,
        cn="honeychecker-server",
        public_pem=hc_pub,
        days=365,
        san_dns=["localhost", "honeychecker"],
        san_ip=["127.0.0.1"],
        eku_server_auth=True,
    )
    (out_dir / "honeychecker-server.crt").write_bytes(hc_cert)
    hc_key_path = out_dir / "honeychecker-server.key"
    hc_key_path.write_bytes(
        hc_priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    if os.name != "nt":
        hc_key_path.chmod(0o600)
    print(f"honeychecker-server cert: {out_dir / 'honeychecker-server.crt'}")

    # ------------------------------------------------------------------
    # 2. api-client  (mTLS / signed-request client cert; EKU clientAuth)
    # ------------------------------------------------------------------
    api_priv = generate_ec_key()
    api_pub = api_priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    api_cert = issue_leaf(
        issuer_cert_pem=service_ca_cert,
        issuer_key_pem=service_ca_key,
        cn="honeyvault-api",
        public_pem=api_pub,
        days=365,
        eku_client_auth=True,
    )
    (out_dir / "api-client.crt").write_bytes(api_cert)
    api_key_path = out_dir / "api-client.key"
    api_key_path.write_bytes(
        api_priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    if os.name != "nt":
        api_key_path.chmod(0o600)
    print(f"api-client cert:          {out_dir / 'api-client.crt'}")
    print()
    print("Both certs are issued by the Service CA (pki/out/service-ca.crt).")
    print(
        "The honeychecker ONLY trusts the Service CA - user identity certs "
        "(Root -> Issuing CA -> username) cannot authenticate here."
    )


if __name__ == "__main__":
    main()
