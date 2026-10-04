"""Honeychecker microservice HTTP client.

Owner: T2 — Rohan. Phase 1 (PROJECT-BRIEF.md §8).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class HoneycheckerUnavailable(Exception):
    """Raised when the honeychecker service is unreachable or returns a 5xx error."""


class HoneycheckerClient:
    """HTTP client for communicating with the Honeychecker microservice."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 5.0,
        client_factory: Callable[[], httpx.Client] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        if client_factory is not None:
            self._client = client_factory()
        else:
            self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Execute HTTP request, translating network and 5xx errors to HoneycheckerUnavailable."""
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
    )
