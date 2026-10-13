"""Tests for password strength estimation utility.

Owner: T5 — Aryan.
"""

import math
from dataclasses import is_dataclass

from app.utils.strength import COMMON_PASSWORDS, StrengthResult, estimate_strength


def test_strength_result_dataclass() -> None:
    """Verify StrengthResult is a dataclass with expected attributes."""
    assert is_dataclass(StrengthResult)
    res = StrengthResult(score=3, entropy_bits=65.4, feedback=["Add length"])
    assert res.score == 3
    assert res.entropy_bits == 65.4
    assert res.feedback == ["Add length"]


def test_common_passwords_tuple() -> None:
    """Verify COMMON_PASSWORDS has exactly 100 unique lowercase entries."""
    assert isinstance(COMMON_PASSWORDS, tuple)
    assert len(COMMON_PASSWORDS) == 100
    assert len(set(COMMON_PASSWORDS)) == 100
    for entry in COMMON_PASSWORDS:
        assert entry == entry.lower()
        assert len(entry) > 0


def test_empty_password() -> None:
    """Empty password returns score 0, 0.0 entropy, and non-empty feedback."""
    res = estimate_strength("")
    assert res.score == 0
    assert res.entropy_bits == 0.0
    assert len(res.feedback) > 0
    assert any("empty" in msg.lower() for msg in res.feedback)


def test_common_passwords_score_zero() -> None:
    """Common passwords (e.g. '123456', 'password') always score 0."""
    res1 = estimate_strength("123456")
    assert res1.score == 0
    assert len(res1.feedback) > 0

    res2 = estimate_strength("password")
    assert res2.score == 0
    assert len(res2.feedback) > 0

    # Case insensitivity test for common passwords
    res3 = estimate_strength("PASSWORD")
    assert res3.score == 0

    res4 = estimate_strength("Admin")
    assert res4.score == 0

    res5 = estimate_strength("qwerty")
    assert res5.score == 0


def test_long_random_mixed_string() -> None:
    """A long random mixed string with all character classes scores 4."""
    # 20 chars, all 4 classes present, no sequences, no repeats, no years
    sample_text = "kX9#mP2$vL5&qW8*zR1!"
    res = estimate_strength(sample_text)
    assert res.score == 4
    assert res.entropy_bits >= 80.0
    assert res.feedback == []


def test_entropy_and_pool_size_calculation() -> None:
    """Verify character pool sizes: 26 lower, 26 upper, 10 digit, 33 symbol."""
    # 8 lowercase chars: pool = 26
    res_lower = estimate_strength("abcdefgh")
    expected_lower = round(8 * math.log2(26), 2)
    assert res_lower.entropy_bits == expected_lower

    # 8 uppercase chars: pool = 26
    res_upper = estimate_strength("ABCDEFGH")
    expected_upper = round(8 * math.log2(26), 2)
    assert res_upper.entropy_bits == expected_upper

    # 8 digits: pool = 10
    res_digits = estimate_strength("01234567")
    expected_digits = round(8 * math.log2(10), 2)
    assert res_digits.entropy_bits == expected_digits

    # 8 symbols: pool = 33
    res_symbols = estimate_strength("!@#$%^&*")
    expected_symbols = round(8 * math.log2(33), 2)
    assert res_symbols.entropy_bits == expected_symbols

    # All classes: pool = 26 + 26 + 10 + 33 = 95
    res_all = estimate_strength("aA1!")
    expected_all = round(4 * math.log2(95), 2)
    assert res_all.entropy_bits == expected_all


def test_score_thresholds() -> None:
    """Check score thresholds: <28: 0, <36: 1, <60: 2, <80: 3, >=80: 4."""
    # 5 digits (pool 10): entropy = 5 * log2(10) = 16.61 (< 28 -> base 0)
    res0 = estimate_strength("94827")
    assert res0.entropy_bits < 28.0
    assert res0.score == 0

    # 6 lowercase chars (pool 26): entropy = 6 * log2(26) = 28.2 (< 36 -> base 1)
    # With length penalty (<8), score is 0
    res_short = estimate_strength("xkzmpt")
    assert 28.0 <= res_short.entropy_bits < 36.0

    # 10 lowercase chars (pool 26): entropy = 10 * log2(26) = 47.0 (>= 36, < 60 -> base 2)
    res2 = estimate_strength("xkzmptqwvb")
    assert 36.0 <= res2.entropy_bits < 60.0
    assert res2.score == 2

    # 11 mixed lower+upper+digit (pool 62): entropy = 11 * log2(62) = 65.49 (>= 60, < 80 -> base 3)
    res3 = estimate_strength("xK9mP2vL5qW")
    assert 60.0 <= res3.entropy_bits < 80.0
    assert res3.score == 3


def test_year_penalty_lowers_score() -> None:
    """Verify that 4-digit years (1950–2035) apply penalties and lower the score."""
    # Compare candidate without year vs with year
    text_clean = "Xk9#Mp2$Vl5&Qw8*"  # 16 chars, 4 classes, entropy ~ 105 bits -> score 4
    res_clean = estimate_strength(text_clean)
    assert res_clean.score == 4

    text_with_year = "Xk9#Mp2$1995Qw8*"  # Includes year 1995 -> penalty lowers score
    res_with_year = estimate_strength(text_with_year)
    assert res_with_year.score < res_clean.score
    assert any("year" in msg.lower() or "1950" in msg for msg in res_with_year.feedback)

    # Check edge years in range 1950-2035
    assert estimate_strength("Pass1950#Word!").score < 4
    assert estimate_strength("Pass2035#Word!").score < 4
    assert estimate_strength("Pass2024#Word!").score < 4


def test_sequence_penalty_lowers_score() -> None:
    """Verify that alphabetical, numerical, and keyboard sequences lower the score."""
    # Alphabetical sequence 'abc'
    text_abc = "Xk9#abc$Vl5&Qw8*"
    res_abc = estimate_strength(text_abc)
    assert res_abc.score < 4
    assert any("sequential" in msg.lower() or "abc" in msg for msg in res_abc.feedback)

    # Numerical sequence '123'
    text_123 = "Xk9#123$Vl5&Qw8*"
    res_123 = estimate_strength(text_123)
    assert res_123.score < 4
    assert any("sequential" in msg.lower() or "123" in msg for msg in res_123.feedback)

    # Keyboard sequence 'qwerty'
    text_qwe = "Xk9#qwerty$Vl5&*"
    res_qwe = estimate_strength(text_qwe)
    assert res_qwe.score < 4
    assert any("sequential" in msg.lower() or "qwerty" in msg for msg in res_qwe.feedback)


def test_repeated_chars_penalty() -> None:
    """Verify that repeated characters apply a penalty and generate feedback."""
    text_repeat = "Xk9#aaaa$Vl5&Qw8*"
    res_repeat = estimate_strength(text_repeat)
    assert res_repeat.score < 4
    assert any("repeat" in msg.lower() for msg in res_repeat.feedback)


def test_weak_passwords_have_feedback() -> None:
    """Verify that weak passwords (score < 3) have non-empty feedback."""
    weak_samples = [
        "123456",
        "password",
        "admin",
        "short",
        "hello12",
        "12345678",
        "abc123qwerty",
        "Pass1999",
        "xK9mP",
    ]
    for sample in weak_samples:
        res = estimate_strength(sample)
        assert res.score < 3
        assert len(res.feedback) > 0
        for tip in res.feedback:
            assert isinstance(tip, str)
            assert len(tip) > 0


def test_deterministic() -> None:
    """Verify that estimate_strength is completely deterministic."""
    sample_inputs = [
        "123456",
        "password",
        "kX9#mP2$vL5&qW8*zR1!",
        "ComplexPassphrase!2024",
        "Random@Word#123$",
    ]
    for sample in sample_inputs:
        res1 = estimate_strength(sample)
        res2 = estimate_strength(sample)
        assert res1.score == res2.score
        assert res1.entropy_bits == res2.entropy_bits
        assert res1.feedback == res2.feedback
