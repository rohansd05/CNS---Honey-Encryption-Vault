"""Print env-var assignments that can be pasted into ``.env`` or a CI secrets store.

Owner: T4 — Parth. Phase 4 (feat/t4-hc-security).

Run from the repository root::

    python pki/export_env.py

TRUST DOMAIN NOTE:
  HC_TRUSTED_CA_CERT_B64 is the *Service CA* (not the Root CA).
  The honeychecker's trust store must contain only the Service CA so that user
  identity certs (Root → Issuing CA → username) cannot authenticate to the service
  channel.  See pki/README.md for the full rationale.
"""

from __future__ import annotations

import base64
from pathlib import Path


def _b64(path: Path) -> str:
    """Return standard base64 of file contents, or empty string if missing."""
    try:
        return base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception:
        return ""


def main() -> None:
    out = Path(__file__).parent / "out"

    # ---- User-identity PKI (Root → Issuing CA → user cert) ----
    print(f"ROOT_CA_CERT_B64={_b64(out / 'root_ca.crt')}")
    print(f"ISSUING_CA_CERT_B64={_b64(out / 'issuing_ca.crt')}")
    print(f"ISSUING_CA_KEY_B64={_b64(out / 'issuing_ca.key')}")

    # ---- Service-to-service PKI (Service CA → honeychecker-server / api-client) ----
    # HC_TRUSTED_CA_CERT_B64 intentionally points at the SERVICE CA, not the root.
    # This ensures the honeychecker's trust store is completely disjoint from the
    # user-identity trust store — a user cert can never build a chain to the service CA.
    print()
    print("# --- Service CA (trust anchor for service-to-service channel) ---")
    print(f"HC_TRUSTED_CA_CERT_B64={_b64(out / 'service-ca.crt')}")
    print(f"HC_TRUSTED_CA_CERT_PATH=../pki/out/service-ca.crt")
    print(f"HC_SERVICE_CA_CERT_PATH=../pki/out/service-ca.crt")

    # ---- api-client cert (used by honeyvault-api to call honeychecker) ----
    print()
    print("# --- api-client cert (mtls / signed mode) ---")
    print(f"HC_CLIENT_CERT_B64={_b64(out / 'api-client.crt')}")
    print(f"HC_CLIENT_KEY_B64={_b64(out / 'api-client.key')}")

    # ---- honeychecker-server cert (used by uvicorn in mtls mode) ----
    print()
    print("# --- honeychecker-server cert (uvicorn TLS) ---")
    print(f"HC_SERVER_CERT_B64={_b64(out / 'honeychecker-server.crt')}")
    print(f"HC_SERVER_KEY_B64={_b64(out / 'honeychecker-server.key')}")


if __name__ == "__main__":
    main()
