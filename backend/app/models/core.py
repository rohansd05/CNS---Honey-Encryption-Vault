from __future__ import annotations

import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def _uuid4_str() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid4_str)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    hw_salt: Mapped[str] = mapped_column(String)
    hw_hashes: Mapped[list[str]] = mapped_column(JSON)
    hw_kdf_profile: Mapped[str] = mapped_column(String)

    identity_public_pem: Mapped[str | None] = mapped_column(Text, nullable=True)
    identity_private_wrapped: Mapped[str | None] = mapped_column(Text, nullable=True)
    identity_cert_pem: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)


class Vault(Base):
    __tablename__ = "vaults"

    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), primary_key=True)
    blob: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now
    )


class Share(Base):
    __tablename__ = "shares"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid4_str)
    sender_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    recipient_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    service: Mapped[str] = mapped_column(String)
    envelope: Mapped[dict] = mapped_column(JSON)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    opened_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid4_str)
    user_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    username: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    sweetword_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_ip: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
