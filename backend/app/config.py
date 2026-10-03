"""Application settings loaded from environment / the repo-root ``.env``.

Owner: T2 — Tanuj (app core). Env var NAMES are a frozen contract (``.env.example``);
adding or renaming one requires a ``contract-change`` PR.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

KDFProfileName = Literal["default", "server_lite", "demo"]
TransportMode = Literal["plain", "mtls", "signed"]


class Settings(BaseSettings):
    """Backend + backend→honeychecker settings. Field names map 1:1 to env vars (upper-cased)."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Common ----
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    demo_mode: bool = True

    # ---- Backend API ----
    api_port: int = 8000
    database_url: str = "sqlite:///./honeyvault.db"
    allowed_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    jwt_secret: SecretStr = SecretStr("")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    honeycore_impl: Literal["stub", "real"] = "stub"
    vault_kdf_profile: KDFProfileName = "default"
    honeywords_k: int = 10
    honeywords_kdf_profile: KDFProfileName = "server_lite"
    rate_limit_login: str = "5/minute"
    rate_limit_unlock: str = "10/minute"
    admin_username: str = "admin"
    admin_login_password: SecretStr = SecretStr("")
    demo_username: str = "demo"
    demo_login_password: SecretStr = SecretStr("")
    demo_master_password: SecretStr = SecretStr("")
    pcfg_password_model_path: str = "honeycore/models/pcfg_password_v1.json.gz"  # noqa: S105
    pcfg_username_model_path: str = "honeycore/models/pcfg_username_v1.json.gz"
    eval_results_path: str = "eval/results/latest.json"
    key_wrap_secret: SecretStr = SecretStr("")
    root_ca_cert_b64: str = ""
    issuing_ca_cert_b64: str = ""
    issuing_ca_key_b64: SecretStr = SecretStr("")

    # ---- Backend -> Honeychecker ----
    honeychecker_url: str = "http://localhost:8001"
    honeychecker_transport: TransportMode = "plain"
    honeychecker_timeout_seconds: float = 5.0
    hc_client_cert_path: str = "../pki/out/api-client.crt"
    hc_client_key_path: str = "../pki/out/api-client.key"
    hc_ca_cert_path: str = "../pki/out/root-ca.crt"
    hc_client_cert_b64: str = ""
    hc_client_key_b64: SecretStr = SecretStr("")

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accept ``ALLOWED_ORIGINS`` as a comma-separated string."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached ``Settings`` instance."""
    return Settings()
