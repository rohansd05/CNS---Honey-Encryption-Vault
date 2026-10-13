"""Tests for ``honeycore.sigil`` (PROJECT-BRIEF.md §7.9). Owner: T1 — Dhruv."""

from __future__ import annotations

import hashlib
import hmac
import itertools
import re
import secrets

import pytest

from honeycore.interfaces import InvalidInputError, Sigil
from honeycore.sigil import EMOJI64, PALETTE16, SIGIL_KEY_LEN, compute_sigil

LIGHT_BG = "#FFFFFF"
DARK_BG = "#09090B"  # shadcn zinc-950


def _rgb(color: str) -> tuple[int, int, int]:
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def _luminance(color: str) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in _rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


# --- EMOJI64 -----------------------------------------------------------------------------


def test_emoji64_has_64_distinct() -> None:
    assert len(EMOJI64) == 64
    assert len(set(EMOJI64)) == 64


@pytest.mark.parametrize("emoji", EMOJI64)
def test_emoji_is_single_codepoint_without_modifiers(emoji: str) -> None:
    assert len(emoji) == 1  # rules out ZWJ sequences, VS16, skin tones, keycaps
    cp = ord(emoji)
    assert not 0x1F1E6 <= cp <= 0x1F1FF  # regional indicators (flags)
    assert not 0x1F3FB <= cp <= 0x1F3FF  # skin-tone modifiers
    assert cp not in (0x200D, 0xFE0F)
    assert cp >= 0x2300  # an emoji block, not ASCII / Latin text


# --- PALETTE16 ---------------------------------------------------------------------------


def test_palette16_has_16_distinct_hex_colours() -> None:
    assert len(PALETTE16) == 16
    assert len({c.upper() for c in PALETTE16}) == 16
    assert all(re.fullmatch(r"#[0-9A-F]{6}", c) for c in PALETTE16)


@pytest.mark.parametrize("color", PALETTE16)
def test_palette_colour_readable_on_light_and_dark(color: str) -> None:
    # WCAG 1.4.11 non-text contrast (>= 3:1) against both theme backgrounds.
    assert _contrast(color, LIGHT_BG) >= 3.0
    assert _contrast(color, DARK_BG) >= 3.0


def test_palette_colours_are_mutually_distinct() -> None:
    def dist(a: str, b: str) -> float:
        return sum((x - y) ** 2 for x, y in zip(_rgb(a), _rgb(b), strict=True)) ** 0.5

    assert min(dist(a, b) for a, b in itertools.combinations(PALETTE16, 2)) >= 40


# --- compute_sigil -----------------------------------------------------------------------


def test_matches_spec_formula() -> None:
    key = bytes(range(SIGIL_KEY_LEN))
    h = hmac.new(key, b"sigil", hashlib.sha256).digest()
    expected = Sigil(
        emojis=(EMOJI64[h[0] % 64], EMOJI64[h[1] % 64], EMOJI64[h[2] % 64]),
        color=PALETTE16[h[3] % 16],
    )
    assert compute_sigil(key) == expected


def test_deterministic_and_well_formed() -> None:
    key = secrets.token_bytes(SIGIL_KEY_LEN)
    sigil = compute_sigil(key)
    assert sigil == compute_sigil(key)
    assert isinstance(sigil.emojis, tuple) and len(sigil.emojis) == 3
    assert all(e in EMOJI64 for e in sigil.emojis)
    assert sigil.color in PALETTE16


def test_accepts_bytearray() -> None:
    key = secrets.token_bytes(SIGIL_KEY_LEN)
    assert compute_sigil(bytearray(key)) == compute_sigil(key)


def test_covers_whole_alphabet() -> None:
    sigils = [compute_sigil(secrets.token_bytes(SIGIL_KEY_LEN)) for _ in range(2000)]
    assert {e for s in sigils for e in s.emojis} == set(EMOJI64)
    assert {s.color for s in sigils} == set(PALETTE16)
    # 64^3 * 16 ≈ 4.2M sigils: 2000 random keys should essentially never collide.
    assert len(set(sigils)) >= 1990


@pytest.mark.parametrize("key_len", [0, 16, 31, 33, 64])
def test_wrong_key_length_raises(key_len: int) -> None:
    with pytest.raises(InvalidInputError):
        compute_sigil(b"\x00" * key_len)
