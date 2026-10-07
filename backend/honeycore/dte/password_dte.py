"""Password DTE (66-int seed) implementing ``PasswordModel`` (PROJECT-BRIEF.md §7.3).

Owner: T1 — Nidhi. Phase 1.

Seed layout (``PASSWORD_SEED_INTS`` = 66 big-endian uint32, one per choice, see §7.2)::

    PCFG path:     [path] [template] then per segment: [vocab-or-__CHARS__] [word | char x n]
    fallback path: [path] [length] [char x length]
    rest:          secrets.randbits(32) padding

Worst case is 2 + 32 segments + 32 chars = 66 ints, so ``decode`` can never run out of seed.
``decode`` is total: every 264-byte string maps to a 1..32-char printable password.

The block codec, model loading and normalisation live in ``pcfg._PCFGBase`` (shared with the
username DTE); templates come from ``pcfg.parse`` / ``pcfg.template``.
"""

from __future__ import annotations

import math
import secrets
from pathlib import Path

from honeycore.dte.int_codec import SeedReader, SeedWriter
from honeycore.dte.pcfg import (
    CHARS_TOKEN,
    CLASS_CHARS,
    _PCFGBase,
    _validate_field,
    char_class,
    parse,
)
from honeycore.interfaces import INT_BYTES, PASSWORD_SEED_INTS

__all__ = [
    "CHARS_TOKEN",
    "DEFAULT_MODEL_PATH",
    "MODEL_ID",
    "PCFGPasswordModel",
    "parse_template",
]

MODEL_ID = "pcfg-password-v1"
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "pcfg_password_v1.json.gz"


def parse_template(password: str) -> tuple[str, list[str]]:
    """Split ``password`` into maximal L/D/S runs: returns (template, segments).

    ``parse_template("monkey12!")`` -> ``("L6D2S1", ["monkey", "12", "!"])``. Thin wrapper
    over ``pcfg.parse``; callers validate the input first (non-L/D characters are class S).
    """
    runs = parse(password)
    return "".join(f"{cls}{len(seg)}" for cls, seg in runs), [seg for _, seg in runs]


class PCFGPasswordModel(_PCFGBase):
    """PCFG password model and DTE (``PasswordModel``, PROJECT-BRIEF.md §7.3).

    ``PCFGPasswordModel()`` loads the default model (this is how ``load_honeycore("real")``
    instantiates it); ``from_file`` loads any model file; ``PCFGPasswordModel(model_dict)``
    uses an already-parsed model.
    """

    kind = "password"
    default_model_path = DEFAULT_MODEL_PATH
    model_id: str = MODEL_ID
    seed_len: int = PASSWORD_SEED_INTS * INT_BYTES

    # ---- FieldDTE -----------------------------------------------------------------------

    def encode(self, value: str) -> bytes:
        """Encode a 1..32-char printable password to a random ``seed_len``-byte seed.

        Raises:
            InvalidInputError: ``value`` is outside the §7.1 limits (the value is not echoed).
        """
        w = SeedWriter()
        self._encode_block(w, _validate_field(value, "password"))
        return w.to_bytes(PASSWORD_SEED_INTS)

    def decode(self, seed: bytes) -> str:
        """TOTAL: map any ``seed_len``-byte seed to a valid 1..32-char printable password.

        Raises:
            ValueError: only if ``len(seed) != seed_len``.
        """
        if len(seed) != self.seed_len:
            raise ValueError(f"password seed must be {self.seed_len} bytes")
        return self._decode_block(SeedReader(seed))

    def sample(self) -> str:
        """Return ``decode(random seed)``: a password drawn from the model distribution."""
        return self.decode(secrets.token_bytes(self.seed_len))

    # ---- PasswordModel ------------------------------------------------------------------

    def sample_like(self, password: str) -> str:
        """Return a different password with the same template and fresh segments (honeywords).

        Segments come from the (class, length) bucket when the model has one, else they are
        spelled from the class unigram. After 20 draws equal to ``password``, the last
        character is swapped for a different one of the same class.

        Raises:
            InvalidInputError: ``password`` is outside the §7.1 limits.
        """
        password = _validate_field(password, "password")
        shape = [(cls, len(seg)) for cls, seg in parse(password)]
        for _ in range(20):
            candidate = "".join(self._sample_segment(cls, n) for cls, n in shape)
            if candidate != password:
                return candidate
        last = password[-1]
        choices = [c for c in CLASS_CHARS[char_class(last)] if c != last]
        return password[:-1] + secrets.choice(choices)

    def probability(self, password: str) -> float:
        """Probability of ``password`` along the path ``encode`` takes, in (0, 1].

        Very long, unlikely passwords can underflow a float; the result is then clamped to
        the smallest positive float. Use ``log_probability`` for exact comparisons.

        Raises:
            InvalidInputError: ``password`` is outside the §7.1 limits.
        """
        return max(math.exp(self.log_probability(password)), math.ulp(0.0))

    def log_probability(self, password: str) -> float:
        """Natural log of the probability along the path ``encode`` takes (always <= 0).

        Raises:
            InvalidInputError: ``password`` is outside the §7.1 limits.
        """
        return self._log_p_block(_validate_field(password, "password"))
