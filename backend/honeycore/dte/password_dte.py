"""Password DTE (66-int seed) implementing ``PasswordModel`` (PROJECT-BRIEF.md §7.3).

Owner: T1 — Nidhi. Phase 1.

Seed layout (``PASSWORD_SEED_INTS`` = 66 big-endian uint32, one per choice, see §7.2)::

    PCFG path:     [path] [template] then per segment: [vocab-or-__CHARS__] [word | char x n]
    fallback path: [path] [length] [char x length]
    rest:          secrets.randbits(32) padding

Worst case is 2 + 32 segments + 32 chars = 66 ints, so ``decode`` can never run out of seed.
``decode`` is total: every 264-byte string maps to a 1..32-char printable password.

Model loading normalises the file so totality and round-tripping hold for any trained model:
every unigram covers its whole character class, every fallback length 1..32 exists, and every
(class, length) bucket used by a template has a ``__CHARS__`` entry.

TODO(T1 Nidhi): move the template parser / model loader into ``dte/pcfg.py`` once it lands, so
``train_pcfg.py`` and ``username_dte.py`` can share it.
"""

from __future__ import annotations

import gzip
import json
import math
import re
import secrets
import string
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

from honeycore.dte.int_codec import (
    MAX_TOTAL,
    Distribution,
    SeedReader,
    SeedWriter,
    decode_choice,
    encode_choice,
    rescale,
)
from honeycore.interfaces import (
    INT_BYTES,
    MAX_FIELD_LEN,
    PASSWORD_SEED_INTS,
    PRINTABLE_MAX,
    PRINTABLE_MIN,
    InvalidInputError,
)

__all__ = [
    "CHARS_TOKEN",
    "DEFAULT_MODEL_PATH",
    "MODEL_ID",
    "PCFGPasswordModel",
    "parse_template",
]

MODEL_ID = "pcfg-password-v1"
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "pcfg_password_v1.json.gz"
CHARS_TOKEN = "__CHARS__"  # noqa: S105  (pseudo-terminal name, not a secret)

PRINTABLE = "".join(chr(c) for c in range(PRINTABLE_MIN, PRINTABLE_MAX + 1))
CLASS_CHARS: dict[str, str] = {
    "L": string.ascii_letters,
    "D": string.digits,
    "S": "".join(c for c in PRINTABLE if not c.isalnum()),
    "ANY": PRINTABLE,
}
_CHAR_CLASS = {c: cls for cls in ("L", "D", "S") for c in CLASS_CHARS[cls]}
_TEMPLATE_RE = re.compile(r"(?:[LDS][1-9][0-9]*)+")
_SEGMENT_RE = re.compile(r"([LDS])([1-9][0-9]*)")

Segment = tuple[str, int]  # (class, length)


def parse_template(password: str) -> tuple[str, list[str]]:
    """Split ``password`` into maximal L/D/S runs: returns (template, segments).

    ``parse_template("monkey12!")`` -> ``("L6D2S1", ["monkey", "12", "!"])``. Callers
    validate the input first; non-printable characters are classed as S.
    """
    segments: list[str] = []
    classes: list[str] = []
    for ch in password:
        cls = _CHAR_CLASS.get(ch, "S")
        if classes and classes[-1] == cls:
            segments[-1] += ch
        else:
            classes.append(cls)
            segments.append(ch)
    template = "".join(f"{c}{len(s)}" for c, s in zip(classes, segments, strict=True))
    return template, segments


def _validate_password(password: object) -> str:
    if not isinstance(password, str):
        raise InvalidInputError("password must be a string")
    if not 1 <= len(password) <= MAX_FIELD_LEN:
        raise InvalidInputError(f"password must be 1..{MAX_FIELD_LEN} characters")
    if any(not PRINTABLE_MIN <= ord(c) <= PRINTABLE_MAX for c in password):
        raise InvalidInputError("password must be printable ASCII (0x20-0x7E)")
    return password


def _template_segments(template: str) -> tuple[Segment, ...]:
    if not _TEMPLATE_RE.fullmatch(template):
        raise ValueError("malformed template in model")
    segs = tuple((c, int(n)) for c, n in _SEGMENT_RE.findall(template))
    if any(a[0] == b[0] for a, b in zip(segs, segs[1:], strict=False)):
        raise ValueError("non-canonical template in model (adjacent segments share a class)")
    if not 1 <= sum(n for _, n in segs) <= MAX_FIELD_LEN:
        raise ValueError("template length out of range in model")
    return segs


def _build_dist(
    weights: Mapping[str, Any], required: list[str] | tuple[str, ...] = ()
) -> Distribution:
    """Rescale ``weights`` and append any ``required`` symbol that is missing with weight 1."""
    missing = [s for s in required if s not in weights]
    scaled = rescale(dict(weights), MAX_TOTAL - len(missing)) if weights else {}
    return Distribution([*scaled.items(), *((s, 1) for s in missing)])


@lru_cache(maxsize=4)
def _read_model_file(path: str) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("password model file must contain a JSON object")
    return data


class PCFGPasswordModel:
    """PCFG password model and DTE (``PasswordModel``, PROJECT-BRIEF.md §7.3).

    ``PCFGPasswordModel()`` loads the default model (this is how ``load_honeycore("real")``
    instantiates it); ``from_file`` loads any model file; ``PCFGPasswordModel(model_dict)``
    uses an already-parsed model.
    """

    model_id: str = MODEL_ID
    seed_len: int = PASSWORD_SEED_INTS * INT_BYTES

    def __init__(self, model: Mapping[str, Any] | None = None) -> None:
        """Build the distributions from a parsed model dict (default model if ``None``).

        Raises:
            FileNotFoundError: ``model`` is ``None`` and the default model file is missing.
            ValueError: the model is malformed (wrong version/kind, bad template or segment).
        """
        if model is None:
            model = _read_model_file(str(DEFAULT_MODEL_PATH))
        self._load(model)

    @classmethod
    def from_file(cls, path: str | Path) -> PCFGPasswordModel:
        """Load a ``pcfg_password_v1.json.gz`` model file."""
        return cls(_read_model_file(str(Path(path).resolve())))

    @classmethod
    def load_default(cls) -> PCFGPasswordModel:
        """Load ``honeycore/models/pcfg_password_v1.json.gz`` (resolved relative to the package)."""
        return cls()

    # ---- model loading ------------------------------------------------------------------

    def _load(self, model: Mapping[str, Any]) -> None:
        if model.get("version") != 1 or model.get("kind") != "password":
            raise ValueError("not a version-1 password model")
        if model.get("max_len", MAX_FIELD_LEN) != MAX_FIELD_LEN:
            raise ValueError(f"password model max_len must be {MAX_FIELD_LEN}")

        path = dict(model.get("path") or {})
        if set(path) != {"pcfg", "fallback"}:
            raise ValueError("model path must have exactly 'pcfg' and 'fallback'")
        self._path = _build_dist(path)
        self._pcfg_idx = self._path.index_of("pcfg")
        self._fallback_idx = self._path.index_of("fallback")

        templates = dict(model.get("templates") or {})
        if not templates:
            raise ValueError("model has no templates")
        self._templates = _build_dist(templates)
        self._template_segs: dict[str, tuple[Segment, ...]] = {
            t: _template_segments(t) for t in self._templates.symbols
        }

        unigrams = model.get("unigrams") or {}
        self._unigrams: dict[str, Distribution] = {}
        for cls, chars in CLASS_CHARS.items():
            weights = dict(unigrams.get(cls) or {})
            if any(len(ch) != 1 or ch not in chars for ch in weights):
                raise ValueError(f"unigram {cls} has characters outside its class")
            self._unigrams[cls] = _build_dist(weights, tuple(chars))

        lengths = dict(model.get("fallback_lengths") or {})
        valid_lengths = tuple(str(n) for n in range(1, MAX_FIELD_LEN + 1))
        if any(k not in valid_lengths for k in lengths):
            raise ValueError(f"fallback lengths must be 1..{MAX_FIELD_LEN}")
        self._lengths = _build_dist(lengths, valid_lengths)

        segments = model.get("segments") or {}
        needed = {seg for segs in self._template_segs.values() for seg in segs}
        self._buckets: dict[Segment, Distribution] = {}
        self._chars_idx: dict[Segment, int] = {}
        for cls, n in sorted(needed):
            words = dict((segments.get(cls) or {}).get(str(n)) or {})
            for word in words:
                if word != CHARS_TOKEN and parse_template(word)[0] != f"{cls}{n}":
                    raise ValueError(f"segment bucket {cls}{n} has a word of the wrong shape")
            dist = _build_dist(words, (CHARS_TOKEN,))
            self._buckets[(cls, n)] = dist
            self._chars_idx[(cls, n)] = dist.index_of(CHARS_TOKEN)

    # ---- FieldDTE -----------------------------------------------------------------------

    def encode(self, value: str) -> bytes:
        """Encode a 1..32-char printable password to a random ``seed_len``-byte seed.

        Raises:
            InvalidInputError: ``value`` is outside the §7.1 limits (the value is not echoed).
        """
        password = _validate_password(value)
        w = SeedWriter()
        template, segments = parse_template(password)
        if template in self._template_segs:
            w.append(encode_choice(self._path, self._pcfg_idx))
            w.append(encode_choice(self._templates, self._templates.index_of(template)))
            for (cls, n), seg in zip(self._template_segs[template], segments, strict=True):
                bucket = self._buckets[(cls, n)]
                try:
                    w.append(encode_choice(bucket, bucket.index_of(seg)))
                except KeyError:
                    w.append(encode_choice(bucket, self._chars_idx[(cls, n)]))
                    self._encode_chars(w, self._unigrams[cls], seg)
        else:
            w.append(encode_choice(self._path, self._fallback_idx))
            w.append(encode_choice(self._lengths, self._lengths.index_of(str(len(password)))))
            self._encode_chars(w, self._unigrams["ANY"], password)
        return w.to_bytes(PASSWORD_SEED_INTS)

    @staticmethod
    def _encode_chars(w: SeedWriter, unigram: Distribution, text: str) -> None:
        for ch in text:
            w.append(encode_choice(unigram, unigram.index_of(ch)))

    def decode(self, seed: bytes) -> str:
        """TOTAL: map any ``seed_len``-byte seed to a valid 1..32-char printable password.

        Raises:
            ValueError: only if ``len(seed) != seed_len``.
        """
        if len(seed) != self.seed_len:
            raise ValueError(f"password seed must be {self.seed_len} bytes")
        reader = SeedReader(seed)
        if decode_choice(self._path, reader.next()) == self._pcfg_idx:
            template = self._templates.symbols[decode_choice(self._templates, reader.next())]
            parts: list[str] = []
            for cls, n in self._template_segs[template]:
                bucket = self._buckets[(cls, n)]
                i = decode_choice(bucket, reader.next())
                if i == self._chars_idx[(cls, n)]:
                    parts.append(self._decode_chars(reader, self._unigrams[cls], n))
                else:
                    parts.append(bucket.symbols[i])
            return "".join(parts)
        length = int(self._lengths.symbols[decode_choice(self._lengths, reader.next())])
        return self._decode_chars(reader, self._unigrams["ANY"], length)

    @staticmethod
    def _decode_chars(reader: SeedReader, unigram: Distribution, n: int) -> str:
        return "".join(unigram.symbols[decode_choice(unigram, reader.next())] for _ in range(n))

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
        password = _validate_password(password)
        _, segments = parse_template(password)
        shape = [(_CHAR_CLASS.get(seg[0], "S"), len(seg)) for seg in segments]
        for _ in range(20):
            candidate = "".join(self._sample_segment(cls, n) for cls, n in shape)
            if candidate != password:
                return candidate
        last = password[-1]
        choices = [c for c in CLASS_CHARS[_CHAR_CLASS.get(last, "S")] if c != last]
        return password[:-1] + secrets.choice(choices)

    def _sample_segment(self, cls: str, n: int) -> str:
        bucket = self._buckets.get((cls, n))
        if bucket is not None:
            i = decode_choice(bucket, secrets.randbits(32))
            if i != self._chars_idx[(cls, n)]:
                return bucket.symbols[i]
        unigram = self._unigrams[cls]
        return "".join(
            unigram.symbols[decode_choice(unigram, secrets.randbits(32))] for _ in range(n)
        )

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
        password = _validate_password(password)
        template, segments = parse_template(password)
        if template in self._template_segs:
            lp = _log_p(self._path, self._pcfg_idx)
            lp += _log_p(self._templates, self._templates.index_of(template))
            for (cls, n), seg in zip(self._template_segs[template], segments, strict=True):
                bucket = self._buckets[(cls, n)]
                try:
                    lp += _log_p(bucket, bucket.index_of(seg))
                except KeyError:
                    lp += _log_p(bucket, self._chars_idx[(cls, n)])
                    lp += _log_p_chars(self._unigrams[cls], seg)
            return lp
        lp = _log_p(self._path, self._fallback_idx)
        lp += _log_p(self._lengths, self._lengths.index_of(str(len(password))))
        return lp + _log_p_chars(self._unigrams["ANY"], password)


def _log_p(dist: Distribution, i: int) -> float:
    return math.log(dist.weight(i)) - math.log(dist.total)


def _log_p_chars(unigram: Distribution, text: str) -> float:
    return math.fsum(_log_p(unigram, unigram.index_of(ch)) for ch in text)
