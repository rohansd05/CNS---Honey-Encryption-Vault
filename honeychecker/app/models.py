"""Honeychecker ORM models.

Owner: T2 — Rohan. TODO(T2 — Rohan): ``SweetwordIndex(user_id PK, real_index)`` and
``Alarm(id, user_id, submitted_index, created_at)``; tables created on startup or via a
small migration (the honeychecker has no Alembic setup yet).
"""

from app.db import Base  # noqa: F401  (models will subclass Base)
