"""Password strength estimation utility.

Owner: T5 — Aryan.
Pure standard-library module for assessing password entropy, common patterns,
and actionable user feedback. Invariant: never logs or stores any password.
"""

import math
import re
import string
from dataclasses import dataclass

# Built-in tuple of 100 most common passwords (all lowercase).
COMMON_PASSWORDS: tuple[str, ...] = (  # noqa: S105
    "123456",
    "password",
    "123456789",
    "12345678",
    "12345",
    "111111",
    "1234567",
    "sunshine",
    "qwerty",
    "iloveyou",
    "princess",
    "admin",
    "welcome",
    "666666",
    "football",
    "monkey",
    "123123",
    "1234567890",
    "letmein",
    "test",
    "dragon",
    "1234",
    "654321",
    "1111",
    "baseball",
    "7777777",
    "superman",
    "555555",
    "888888",
    "999999",
    "starwars",
    "shadow",
    "master",
    "access",
    "mustang",
    "michael",
    "trustno1",
    "charlie",
    "daniel",
    "killer",
    "freedom",
    "chevy",
    "jordan",
    "computer",
    "harley",
    "cowboy",
    "hunter",
    "cookie",
    "ginger",
    "secret",
    "rover",
    "sparkle",
    "hockey",
    "ranger",
    "thunder",
    "maggie",
    "merlin",
    "pepper",
    "splash",
    "scooter",
    "muffin",
    "dexter",
    "jasmine",
    "oscar",
    "bailey",
    "barney",
    "casper",
    "buster",
    "boots",
    "bandit",
    "peanut",
    "brandon",
    "sammie",
    "tigger",
    "copper",
    "whiskers",
    "tinker",
    "rocky",
    "samantha",
    "fluffy",
    "chester",
    "bubbles",
    "simba",
    "lucky",
    "max",
    "daisy",
    "buddy",
    "coco",
    "bear",
    "bella",
    "molly",
    "angel",
    "pass1234",
    "test1234",
    "guest",
    "default",
    "liverpool",
    "chelsea",
    "arsenal",
    "barcelona",
)

_COMMON_PASSWORDS_SET: frozenset[str] = frozenset(COMMON_PASSWORDS)

_KEYBOARD_ROWS: tuple[str, ...] = (
    "qwertyuiop",
    "asdfghjkl",
    "zxcvbnm",
    "1234567890",
    "qwertzuiop",
    "azertyuiop",
)

_YEAR_REGEX: re.Pattern[str] = re.compile(r"(19[5-9]\d|20[0-2]\d|203[0-5])")
_REPEAT_REGEX: re.Pattern[str] = re.compile(r"(.)\1{2,}")


@dataclass
class StrengthResult:
    """Password strength evaluation result."""

    score: int
    entropy_bits: float
    feedback: list[str]


def _has_alphabetical_sequence(text: str, length: int = 3) -> bool:
    """Check if the text contains an alphabetical sequence of at least `length` chars."""
    lower = text.lower()
    for i in range(len(lower) - length + 1):
        chunk = lower[i : i + length]
        if all("a" <= c <= "z" for c in chunk):
            if all(ord(chunk[j + 1]) - ord(chunk[j]) == 1 for j in range(length - 1)):
                return True
            if all(ord(chunk[j]) - ord(chunk[j + 1]) == 1 for j in range(length - 1)):
                return True
    return False


def _has_numerical_sequence(text: str, length: int = 3) -> bool:
    """Check if the text contains a numerical sequence of at least `length` chars."""
    for i in range(len(text) - length + 1):
        chunk = text[i : i + length]
        if all("0" <= c <= "9" for c in chunk):
            if all(ord(chunk[j + 1]) - ord(chunk[j]) == 1 for j in range(length - 1)):
                return True
            if all(ord(chunk[j]) - ord(chunk[j + 1]) == 1 for j in range(length - 1)):
                return True
    return False


def _has_keyboard_sequence(text: str, length: int = 3) -> bool:
    """Check if the text contains a keyboard row sequence of at least `length` chars."""
    lower = text.lower()
    for row in _KEYBOARD_ROWS:
        rev_row = row[::-1]
        for i in range(len(lower) - length + 1):
            sub = lower[i : i + length]
            if sub in row or sub in rev_row:
                return True
    return False


def estimate_strength(password: str) -> StrengthResult:
    """Estimate the strength of a password based on entropy, penalties, and patterns.

    Calculates pool size from character classes present:
    - Lowercase letters: 26
    - Uppercase letters: 26
    - Digits: 10
    - Symbols: 33

    Entropy is calculated as `len(password) * log2(pool)`.
    Penalties are applied for common passwords, sequences, repeated characters,
    4-digit years (1950-2035), and short length.

    Returns:
        StrengthResult with score (0-4), entropy_bits, and feedback suggestions.
    """
    feedback: list[str] = []

    if not password:
        return StrengthResult(
            score=0,
            entropy_bits=0.0,
            feedback=["Password cannot be empty."],
        )

    # 1. Determine character classes and pool size
    has_lower = any("a" <= c <= "z" for c in password)
    has_upper = any("A" <= c <= "Z" for c in password)
    has_digit = any("0" <= c <= "9" for c in password)
    has_symbol = any(
        (c in string.punctuation) or c.isspace() or (not c.isalnum()) for c in password
    )

    pool = 0
    if has_lower:
        pool += 26
    if has_upper:
        pool += 26
    if has_digit:
        pool += 10
    if has_symbol:
        pool += 33

    # Calculate entropy
    if pool > 0 and len(password) > 0:
        entropy = len(password) * math.log2(pool)
    else:
        entropy = 0.0

    entropy_bits = round(entropy, 2)

    # 2. Base score from entropy thresholds:
    # <28: 0, <36: 1, <60: 2, <80: 3, else 4
    if entropy_bits < 28.0:
        base_score = 0
    elif entropy_bits < 36.0:
        base_score = 1
    elif entropy_bits < 60.0:
        base_score = 2
    elif entropy_bits < 80.0:
        base_score = 3
    else:
        base_score = 4

    # 3. Penalties and Feedback Checks
    penalties = 0

    # Common passwords check
    lower_pwd = password.lower()
    is_common = lower_pwd in _COMMON_PASSWORDS_SET or password in _COMMON_PASSWORDS_SET
    if is_common:
        feedback.append("Avoid commonly used passwords.")

    # Length checks
    if len(password) < 8:
        penalties += 1
        feedback.append("Password is too short. Use at least 8 characters (12+ recommended).")
    elif len(password) < 12:
        feedback.append("Add more characters (12+ recommended) for better security.")

    # Character class diversity feedback
    if not has_lower:
        feedback.append("Add lowercase letters.")
    if not has_upper:
        feedback.append("Add uppercase letters.")
    if not has_digit:
        feedback.append("Add numbers.")
    if not has_symbol:
        feedback.append("Add special characters or symbols.")

    # Sequences check (abc, 123, qwerty)
    has_seq = (
        _has_alphabetical_sequence(password)
        or _has_numerical_sequence(password)
        or _has_keyboard_sequence(password)
    )
    if has_seq:
        penalties += 1
        feedback.append("Avoid sequential character patterns (e.g. 'abc', '123', 'qwerty').")

    # Repeated characters check
    has_repeats = bool(_REPEAT_REGEX.search(password)) or (
        len(password) >= 6 and len(set(lower_pwd)) <= len(password) // 2
    )
    if has_repeats:
        penalties += 1
        feedback.append("Avoid repeated characters or simple repetition.")

    # 4-digit year (1950–2035) check
    has_year = bool(_YEAR_REGEX.search(password))
    if has_year:
        penalties += 1
        feedback.append("Avoid including 4-digit years (1950–2035) in your password.")

    # 4. Final score computation
    if is_common:
        score = 0
    else:
        score = max(0, min(4, base_score - penalties))

    # Ensure weak passwords (score < 3) always have actionable feedback
    if score < 3 and not feedback:
        feedback.append("Use a longer, more complex passphrase with varied characters.")

    return StrengthResult(
        score=score,
        entropy_bits=entropy_bits,
        feedback=feedback,
    )
