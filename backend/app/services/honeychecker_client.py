"""Honeychecker microservice HTTP client.

Owner: T2 — Rohan. Phase 1 (PROJECT-BRIEF.md §8, §10, ADR-005).
"""

from __future__ import annotations

import base64
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pydantic import SecretStr

from app.config import get_settings
from honeycore.transport import httpx_client_kwargs, sign_request

logger = logging.getLogger(__name__)


class HoneycheckerUnavailable(Exception):
    """Raised when the honeychecker service is unreachable or returns a 5xx error."""


def _resolve_file_path(p: str | None) -> Path | None:
    """Resolve a file path relative to current working directory or repository root."""
    if not p or not p.strip():
        return None
    cleaned = p.strip()
    direct = Path(cleaned)
    if direct.is_file():
        return direct
    if cleaned.startswith("../") and Path(cleaned[3:]).is_file():
        return Path(cleaned[3:])
    if (Path("backend") / cleaned).is_file():
        return Path("backend") / cleaned
    return None


def _extract_pem(val: str | bytes | None) -> bytes | None:
    """Extract PEM bytes from a string, bytes, or base64 representation."""
    if val is None:
        return None
    raw = val.strip() if isinstance(val, (str, bytes)) else None
    if not raw:
        return None
    if isinstance(raw, str):
        if "-----BEGIN" in raw:
            return raw.encode("utf-8")
        try:
            decoded = base64.b64decode(raw)
            if decoded:
                return decoded
        except Exception as exc:
            raise RuntimeError(f"Certificate/key base64 decode failed: {exc}") from exc
    elif isinstance(raw, bytes):
        if b"-----BEGIN" in raw:
            return raw
        try:
            decoded = base64.b64decode(raw)
            if decoded:
                return decoded
        except Exception as exc:
            raise RuntimeError(f"Certificate/key base64 decode failed: {exc}") from exc
    return None


def _load_client_cert_pem(
    cert_b64: str | None = None,
    cert_path: str | None = None,
    cert_pem: bytes | None = None,
) -> bytes:
    """Load and validate X.509 client certificate PEM bytes."""
    if cert_pem:
        data = cert_pem
    else:
        data = _extract_pem(cert_b64)
        if data is None and cert_path:
            p = _resolve_file_path(cert_path)
            if p is not None:
                try:
                    data = p.read_bytes()
                except Exception as exc:
                    raise RuntimeError(
                        f"Failed to read client cert file '{cert_path}': {exc}"
                    ) from exc
            else:
                raise RuntimeError(f"Client cert file not found: '{cert_path}'")

    if not data:
        raise RuntimeError(
            "Signed transport requires a client certificate. "
            "Set HC_CLIENT_CERT_B64 or ensure HC_CLIENT_CERT_PATH exists."
        )

    try:
        x509.load_pem_x509_certificate(data)
    except Exception as exc:
        raise RuntimeError(f"Invalid client certificate PEM: {exc}") from exc

    return data


def _load_client_key_pem(
    key_b64: str | SecretStr | None = None,
    key_path: str | None = None,
    key_pem: bytes | None = None,
) -> bytes:
    """Load and validate EC private key PEM bytes."""
    if key_pem:
        data = key_pem
    else:
        raw_key = key_b64.get_secret_value() if isinstance(key_b64, SecretStr) else key_b64
        data = _extract_pem(raw_key)
        if data is None and key_path:
            p = _resolve_file_path(key_path)
            if p is not None:
                try:
                    data = p.read_bytes()
                except Exception as exc:
                    raise RuntimeError(
                        f"Failed to read client key file '{key_path}': {exc}"
                    ) from exc
            else:
                raise RuntimeError(f"Client key file not found: '{key_path}'")

    if not data:
        raise RuntimeError(
            "Signed transport requires a client private key. "
            "Set HC_CLIENT_KEY_B64 or ensure HC_CLIENT_KEY_PATH exists."
        )

    try:
        priv_key = serialization.load_pem_private_key(data, password=None)
        if not isinstance(priv_key, ec.EllipticCurvePrivateKey):
            raise RuntimeError("Client private key must be an EC private key")
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Invalid client private key PEM: {exc}") from exc

    return data


class HoneycheckerClient:
    """HTTP client for communicating with the Honeychecker microservice."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 5.0,
        transport_mode: str = "plain",
        *,
        client_cert_path: str | None = None,
        client_key_path: str | None = None,
        ca_cert_path: str | None = None,
        client_cert_b64: str | None = None,
        client_key_b64: str | SecretStr | None = None,
        client_cert_pem: bytes | None = None,
        client_key_pem: bytes | None = None,
        client_factory: Callable[[], httpx.Client] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport_mode = transport_mode
        self._client_cert_pem: bytes | None = None
        self._client_key_pem: bytes | None = None
        self._mtls_kwargs: dict[str, Any] = {}

        if self.transport_mode == "plain":
            if client_factory is not None:
                self._client = client_factory()
            else:
                self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

        elif self.transport_mode == "mtls":
            if not self.base_url.lower().startswith("https://"):
                raise RuntimeError(
                    f"mTLS transport mode requires an https:// base URL, got: {self.base_url!r}"
                )
            if not client_cert_path or not client_key_path or not ca_cert_path:
                msg = (
                    "mTLS transport mode requires client_cert_path, "
                    "client_key_path, and ca_cert_path"
                )
                raise RuntimeError(msg)
            resolved_cert = _resolve_file_path(client_cert_path)
            if resolved_cert is None:
                raise RuntimeError(f"mTLS client_cert_path file not found: {client_cert_path}")
            resolved_key = _resolve_file_path(client_key_path)
            if resolved_key is None:
                raise RuntimeError(f"mTLS client_key_path file not found: {client_key_path}")
            resolved_ca = _resolve_file_path(ca_cert_path)
            if resolved_ca is None:
                raise RuntimeError(f"mTLS ca_cert_path file not found: {ca_cert_path}")

            try:
                self._mtls_kwargs = httpx_client_kwargs(
                    "mtls",
                    client_cert_path=str(resolved_cert),
                    client_key_path=str(resolved_key),
                    ca_cert_path=str(resolved_ca),
                )
            except Exception as exc:
                raise RuntimeError(f"Failed to configure mTLS transport: {exc}") from exc

            if client_factory is not None:
                self._client = client_factory()
            else:
                self._client = httpx.Client(
                    base_url=self.base_url,
                    timeout=self.timeout,
                    **self._mtls_kwargs,
                )

        elif self.transport_mode == "signed":
            self._client_cert_pem = _load_client_cert_pem(
                cert_b64=client_cert_b64,
                cert_path=client_cert_path,
                cert_pem=client_cert_pem,
            )
            self._client_key_pem = _load_client_key_pem(
                key_b64=client_key_b64,
                key_path=client_key_path,
                key_pem=client_key_pem,
            )
            if client_factory is not None:
                self._client = client_factory()
            else:
                self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

        else:
            msg = (
                f"Unknown transport mode: {self.transport_mode!r}. "
                "Choose from: plain, mtls, signed."
            )
            raise RuntimeError(msg)

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Execute HTTP request, translating network and 5xx errors to HoneycheckerUnavailable."""
        if self.transport_mode == "signed":
            headers = dict(kwargs.pop("headers", None) or {})
            if "json" in kwargs:
                body = json.dumps(kwargs.pop("json")).encode("utf-8")
                kwargs["content"] = body
                headers["Content-Type"] = "application/json"
            elif "content" in kwargs:
                c = kwargs["content"]
                if isinstance(c, bytes):
                    body = c
                elif isinstance(c, str):
                    body = c.encode("utf-8")
                else:
                    body = bytes(c)
            else:
                body = b""

            url_obj = httpx.URL(path, params=kwargs.get("params"))
            path_with_query = url_obj.raw_path.decode("ascii")

            if self._client_cert_pem is None or self._client_key_pem is None:
                msg = "Signed transport missing client cert/key"
                raise RuntimeError(msg)

            sig_headers = sign_request(
                method=method,
                path=path_with_query,
                body=body,
                client_cert_pem=self._client_cert_pem,
                client_key_pem=self._client_key_pem,
            )
            headers.update(sig_headers)
            kwargs["headers"] = headers

        try:
            resp = self._client.request(method, path, **kwargs)
            if resp.status_code >= 500:
                raise HoneycheckerUnavailable(
                    f"Honeychecker server error HTTP {resp.status_code}: {resp.text}"
                )
            return resp
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            raise HoneycheckerUnavailable(f"Honeychecker network error: {exc}") from exc

    def register(self, user_id: str, index: int) -> None:
        """Register a user's real sweetword index with the honeychecker.

        Raises HoneycheckerUnavailable on network or 5xx server errors.
        Raises httpx.HTTPStatusError on 409 Conflict if already registered.
        """
        resp = self._request("POST", "/hc/register", json={"user_id": user_id, "index": index})
        if resp.status_code >= 400:
            resp.raise_for_status()

    def check(self, user_id: str, index: int) -> bool:
        """Check a candidate sweetword index against the honeychecker.

        Returns True if matched, False on mismatch or unknown user.
        Raises HoneycheckerUnavailable on network or 5xx server errors.
        """
        resp = self._request("POST", "/hc/check", json={"user_id": user_id, "index": index})
        if resp.status_code == 200:
            return bool(resp.json().get("match", False))
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        return False

    def health(self) -> bool:
        """Check honeychecker service health.

        Returns True if healthy.
        Raises HoneycheckerUnavailable on network or 5xx server errors.
        """
        resp = self._request("GET", "/hc/health")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("status") == "ok" and data.get("db", "ok") == "ok"
        return False

    def close(self) -> None:
        """Close the underlying HTTP client session."""
        self._client.close()

    def __enter__(self) -> HoneycheckerClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def get_honeychecker_client() -> HoneycheckerClient:
    """FastAPI dependency providing a HoneycheckerClient built from settings."""
    settings = get_settings()
    return HoneycheckerClient(
        base_url=settings.honeychecker_url,
        timeout=settings.honeychecker_timeout_seconds,
        transport_mode=settings.honeychecker_transport,
        client_cert_path=settings.hc_client_cert_path,
        client_key_path=settings.hc_client_key_path,
        ca_cert_path=settings.hc_ca_cert_path,
        client_cert_b64=settings.hc_client_cert_b64,
        client_key_b64=settings.hc_client_key_b64,
    )
