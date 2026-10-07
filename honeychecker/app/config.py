"""Honeychecker settings (``HC_*`` env vars from the repo-root ``.env``).

Owner: T2 — Rohan. Env var names are frozen (``.env.example``).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Honeychecker service settings. Field names map 1:1 to env vars (upper-cased)."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    hc_port: int = 8001
    hc_database_url: str = "sqlite:///./honeychecker.db"
    hc_transport: Literal["plain", "mtls", "signed"] = "plain"  # must match HONEYCHECKER_TRANSPORT
    hc_allowed_client_cn: str = "honeyvault-api"
    hc_server_cert_path: str = "../pki/out/honeychecker-server.crt"
    hc_server_key_path: str = "../pki/out/honeychecker-server.key"
    # Service CA trust store (Phase 4): points at the Service CA, NOT the Root CA.
    # The Service CA is the trust anchor for service-to-service authentication.
    # A user identity cert (Root → Issuing CA → username) can never build a chain
    # to the Service CA, so it cannot authenticate to the honeychecker.
    hc_trusted_ca_cert_path: str = "../pki/out/service-ca.crt"
    hc_trusted_ca_cert_b64: str = ""
    # Legacy / user-identity issuing CA fields (kept for sharing layer; not used
    # by the honeychecker's verify_caller).
    hc_issuing_ca_cert_b64: str = ""
    # Service CA convenience alias (same as hc_trusted_ca_cert_path; explicit name
    # makes deployment scripts unambiguous).
    hc_service_ca_cert_path: str = "../pki/out/service-ca.crt"
    hc_service_ca_cert_b64: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached ``Settings`` instance."""
    return Settings()
