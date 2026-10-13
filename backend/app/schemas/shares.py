"""Pydantic v2 schemas for share-related endpoints.

Owner: T2 — Rohan. Contract: docs/api-contract.md §5.
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, Field


class ShareCreateRequest(BaseModel):
    """Payload to seal and share a vault entry with another user."""

    master_password: str = Field(..., min_length=1, max_length=128)
    entry_id: str
    recipient_username: str


class ShareCreateResponse(BaseModel):
    """Response returned upon successfully sealing and creating a share."""

    share_id: str


class ShareInboxItem(BaseModel):
    """Metadata of an incoming share received by the user."""

    share_id: str
    sender: str
    service: str
    created_at: datetime.datetime
    opened_at: datetime.datetime | None = None


class ShareSentItem(BaseModel):
    """Metadata of an outgoing share sent by the user."""

    share_id: str
    recipient: str
    service: str
    created_at: datetime.datetime
    opened_at: datetime.datetime | None = None


class OpenShareResponse(BaseModel):
    """Decrypted credential entry and cryptographic verification results."""

    service: str
    username: str | None = None
    password: str | None = None
    sender: str
    signature_valid: bool
    certificate_valid: bool
    certificate_subject: str
    certificate_issuer: str


class TamperShareResponse(BaseModel):
    """Response returned after tampering with a share envelope in demo mode."""

    tampered: bool = True
