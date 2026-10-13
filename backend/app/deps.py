"""FastAPI dependency helpers.

Owner: T2 — Tanuj (app core).
"""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.db import get_db as get_db  # re-export for routers


@lru_cache(maxsize=1)
def get_honeycore():
    """Return the cached HoneyCore bundle (stub or real, per settings).

    Cached at process level — load_honeycore reads model files from disk once.
    In tests, override by clearing the cache or patching ``settings.honeycore_impl``.
    """
    from honeycore.factory import load_honeycore

    return load_honeycore(get_settings().honeycore_impl)
