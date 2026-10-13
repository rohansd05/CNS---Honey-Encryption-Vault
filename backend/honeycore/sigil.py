"""Vault Sigil: 3 emojis + colour from HMAC(sigil_key, b"sigil") (§7.9).

Owner: T1 — Nidhi (implemented by Dhruv on feat/t1-vault-crypto). Phase 1.

``h = HMAC-SHA256(sigil_key, b"sigil")``; emojis ``EMOJI64[h[0..2] % 64]``, colour
``PALETTE16[h[3] % 16]``. Nothing is stored: the user learns to recognise their own sigil, and an
unfamiliar one hints at a typo. It is NOT a password check — every password yields some sigil.
"""

from __future__ import annotations

import hashlib
import hmac

from honeycore.interfaces import InvalidInputError, Sigil

SIGIL_KEY_LEN = 32
SIGIL_MESSAGE = b"sigil"

# 64 visually distinct, single-codepoint emojis with default emoji presentation (no variation
# selector, ZWJ, skin tone or flag). All are Unicode <= 11.0 so they render on Windows 10+,
# macOS, Android and iOS. Grouped: animals, nature, food, objects.
EMOJI64: tuple[str, ...] = (
    "🐝", "🐙", "🦀", "🐢", "🦊", "🐼", "🦁", "🐸",
    "🦉", "🦋", "🐧", "🦒", "🐘", "🦄", "🐌", "🐳",
    "🌵", "🌻", "🌹", "🍀", "🍁", "🍄", "🌙", "⭐",
    "🌈", "🌋", "🔥", "💧", "🍎", "🍋", "🍇", "🍉",
    "🥥", "🥝", "🥕", "🌽", "🥨", "🧀", "🍩", "🍕",
    "🎈", "🎲", "🎸", "🎯", "🚀", "🛸", "🏰", "🔑",
    "💎", "🔔", "📚", "🧩", "🎨", "🧲", "🔭", "⚓",
    "🎩", "👑", "🚲", "⏰", "💡", "🎁", "⚽", "🍯",
)  # fmt: skip

# 16 mid-luminance hues with >= 3:1 contrast (WCAG 1.4.11, non-text) against both white and
# the dark background #09090B, so a sigil swatch reads in either theme.
PALETTE16: tuple[str, ...] = (
    "#D93F3F",  # red
    "#E8590C",  # orange
    "#C27C0E",  # amber
    "#8C8A00",  # olive
    "#5C940D",  # lime
    "#2F9E44",  # green
    "#0CA678",  # jade
    "#0B9AA0",  # teal
    "#1C7ED6",  # blue
    "#4263EB",  # indigo
    "#7048E8",  # violet
    "#9C36B5",  # purple
    "#C2255C",  # crimson
    "#E64980",  # pink
    "#8B6A4F",  # brown
    "#748089",  # slate
)


def compute_sigil(sigil_key: bytes) -> Sigil:
    """Return the sigil for a ``SIGIL_KEY_LEN``-byte ``sigil_key`` (PROJECT-BRIEF.md §7.9).

    Raises ``InvalidInputError`` only for a wrong key length (a programming error — the vault
    always passes a 32-byte HMAC output, whatever the password).
    """
    if len(sigil_key) != SIGIL_KEY_LEN:
        raise InvalidInputError(f"sigil key must be {SIGIL_KEY_LEN} bytes, got {len(sigil_key)}")
    h = hmac.new(bytes(sigil_key), SIGIL_MESSAGE, hashlib.sha256).digest()
    return Sigil(
        emojis=(EMOJI64[h[0] % 64], EMOJI64[h[1] % 64], EMOJI64[h[2] % 64]),
        color=PALETTE16[h[3] % 16],
    )
