"""Honeychecker ORM models.

Owner: T2 — Rohan.
Models:
* UserIndex(user_id str PK, real_index int, created_at)
* Alarm(id uuid str, user_id str, claimed_index int, kind str, created_at)
"""

from __future__ import annotations

import datetime
import uuid
from typing import Literal

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

AlarmKind = Literal["HONEYWORD_MISMATCH", "UNKNOWN_USER"]


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def _uuid4_str() -> str:
    return str(uuid.uuid4())


class UserIndex(Base):
    """Maps a user to their real sweetword index."""

    __tablename__ = "user_indices"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    real_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )


class Alarm(Base):
    """Records honeyword mismatches and unknown user check attempts."""

    __tablename__ = "alarms"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid4_str)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    claimed_index: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
