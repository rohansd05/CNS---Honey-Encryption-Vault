"""Create the HoneyVault Service CA — a self-signed P-256 CA used exclusively for
service-to-service certificates (honeychecker-server, api-client).

Owner: T4 — Parth. Phase 4 (feat/t4-hc-security).

WHY A SEPARATE SERVICE CA?
The Issuing CA (Root → Issuing → user cert) issues user *identity* certificates whose
Subject CN is a username.  If that same CA also signed service certs, a user identity cert
would satisfy the honeychecker's ``verify_certificate(expected_cn="honeyvault-api")``
check—provided the attacker could craft a cert with CN=honeyvault-api.  Worse, a
compromised user cert from the Issuing CA would be trusted at the service boundary.

By giving service-to-service TLS its own, completely separate CA:
  * The honeychecker's trust store (HC_TRUSTED_CA_CERT_B64) contains ONLY the Service CA.
  * A user identity cert (issued by Issuing CA) can never build a valid chain to the
    Service CA, so it cannot authenticate to the honeychecker—even if the user cert
    happens to have a matching CN.
  * The blast radius of a compromised user-cert key is contained to the sharing layer;
    it cannot escalate to service impersonation.

Run from the repository root::

    python pki/make_service_ca.py

Output: ``pki/out/service-ca.crt`` and ``pki/out/service-ca.key`` (gitignored).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow imports from backend/honeycore without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from honeycore.pki import build_root_ca  # noqa: E402


def main() -> None:
    out_dir = Path(__file__).parent / "out"
    out_dir.mkdir(exist_ok=True)

    cert_pem, key_pem = build_root_ca(cn="HoneyVault Service CA", days=3650)  # 10 years

    cert_path = out_dir / "service-ca.crt"
    key_path = out_dir / "service-ca.key"

    cert_path.write_bytes(cert_pem)
    key_path.write_bytes(key_pem)

    if os.name != "nt":
        key_path.chmod(0o600)

    print(f"Service CA written to {cert_path}")
    print(f"Service CA key written to {key_path}")
    print("NOTE: service-ca.key is the trust anchor for service-to-service auth.")
    print("      Keep it offline; never deploy it.")


if __name__ == "__main__":
    main()
