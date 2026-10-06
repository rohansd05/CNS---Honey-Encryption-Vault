"""Pydantic v2 schemas for user-related endpoints.

Owner: T2 — Rohan. Contract: docs/api-contract.md §4.
"""

from __future__ import annotations

from pydantic import BaseModel


class UserIdentityResponse(BaseModel):
    """Public identity keys and certificate for a user."""

    username: str
    public_key_pem: str
    certificate_pem: str
