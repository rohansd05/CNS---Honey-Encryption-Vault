"""PCFG model: parse templates, train, load/save ``pcfg_*_v1.json.gz`` (PROJECT-BRIEF.md §7.3).

Owner: T1 — Nidhi. Phase 1.

Pure library: the only I/O is ``save_model`` / ``load_model``. Training input is an iterable
of ``(password, weight)`` pairs; the CLI that reads corpora is ``scripts/train_pcfg.py``.

Model format (v1)::

    {"version": 1, "kind": "password", "max_len": 32,
     "path": {"pcfg": 999, "fallback": 1},
     "templates": {"L6D2": ...},
     "segments": {"L": {"6": {"monkey": 123, "__CHARS__": 5}}, "D": {...}, "S": {...}},
     "unigrams": {"L": {...}, "D": {...}, "S": {...}, "ANY": {...}},
     "fallback_lengths": {"1": ..., ..., "32": ...}}

Every weight is an int >= 1 and every distribution totals <= 2**31 (``int_codec.rescale``).
"""

from __future__ import annotations

import gzip
import hashlib
import json
import string
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from honeycore.dte.int_codec import MAX_TOTAL, rescale
from honeycore.interfaces import MAX_FIELD_LEN, PRINTABLE_MAX, PRINTABLE_MIN

__all__ = [
    "CHARS_TOKEN",
    "CLASS_CHARS",
    "DEFAULT_TOP_K",
    "HELDOUT_THRESHOLD",
    "PATH_WEIGHTS",
    "char_class",
    "is_heldout",
    "is_valid_field",
    "load_model",
    "parse",
    "save_model",
    "template",
    "train_password_model",
]

CHARS_TOKEN = "__CHARS__"  # noqa: S105  (pseudo-terminal name, not a secret)
CHARS_FRACTION = 0.005  # __CHARS__ weight = max(1, 0.5% of the bucket)
PATH_WEIGHTS: dict[str, int] = {"pcfg": 999, "fallback": 1}
DEFAULT_TOP_K: dict[str, int] = {"L": 5000, "D": 2000, "S": 2000}
HELDOUT_THRESHOLD = 52  # sha256(pw)[0] < 52  ->  52/256 ~ 20.3% held out

PRINTABLE = "".join(chr(c) for c in range(PRINTABLE_MIN, PRINTABLE_MAX + 1))
CLASS_CHARS: dict[str, str] = {
    "L": string.ascii_letters,
    "D": string.digits,
    "S": "".join(c for c in PRINTABLE if not c.isalnum()),
    "ANY": PRINTABLE,
}
_CHAR_CLASS = {c: cls for cls in ("L", "D", "S") for c in CLASS_CHARS[cls]}


def char_class(ch: str) -> str:
    """Return ``"L"``, ``"D"`` or ``"S"`` for one character (anything not L/D is S)."""
    return _CHAR_CLASS.get(ch, "S")


def parse(password: str) -> list[tuple[str, str]]:
    """Split ``password`` into maximal same-class runs.

    ``parse("monkey12!")`` -> ``[("L", "monkey"), ("D", "12"), ("S", "!")]``.
    """
    runs: list[tuple[str, str]] = []
    for ch in password:
        cls = char_class(ch)
        if runs and runs[-1][0] == cls:
            runs[-1] = (cls, runs[-1][1] + ch)
        else:
            runs.append((cls, ch))
    return runs


def template(password: str) -> str:
    """Return the template of ``password``, e.g. ``"monkey12!"`` -> ``"L6D2S1"``."""
    return "".join(f"{cls}{len(seg)}" for cls, seg in parse(password))


def is_valid_field(s: object, max_len: int = MAX_FIELD_LEN) -> bool:
    """True iff ``s`` is a str of 1..``max_len`` printable ASCII chars (0x20-0x7E)."""
    return (
        isinstance(s, str)
        and 1 <= len(s) <= max_len
        and all(PRINTABLE_MIN <= ord(c) <= PRINTABLE_MAX for c in s)
    )


def is_heldout(password: str) -> bool:
    """Deterministic ~20% evaluation split: ``sha256(password.encode())[0] < 52``.

    Held-out passwords are never used for training.
    """
    return hashlib.sha256(password.encode()).digest()[0] < HELDOUT_THRESHOLD


def _ranked(weights: Mapping[str, float]) -> list[tuple[str, float]]:
    """Sort by weight descending, then key ascending (deterministic)."""
    return sorted(weights.items(), key=lambda kv: (-kv[1], kv[0]))


def _finalize(
    weights: Mapping[str, float], required: Iterable[str] = (), *, sort: bool = True
) -> dict[str, int]:
    """Rescale to ints >= 1 (total <= 2**31); missing ``required`` keys get weight 1.

    ``sort=True`` orders keys by weight (desc) then key; ``sort=False`` follows ``required``
    order (then any extra keys in input order).
    """
    items = dict(_ranked(weights)) if sort else dict(weights)
    required = list(required)
    missing = [k for k in required if k not in items]
    scaled = rescale(items, MAX_TOTAL - len(missing)) if items else {}
    if sort:
        return {**scaled, **dict.fromkeys(missing, 1)}
    order = required + [k for k in scaled if k not in set(required)]
    return {k: scaled.get(k, 1) for k in order}


def train_password_model(
    pairs: Iterable[tuple[str, float]],
    max_len: int = MAX_FIELD_LEN,
    top_k: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Train a v1 password PCFG from ``(password, weight)`` pairs (PROJECT-BRIEF.md §7.3).

    Invalid fields (not 1..``max_len`` printable ASCII) and weights <= 0 are skipped; the
    caller is responsible for removing held-out passwords. Repeated passwords accumulate.

    - templates: total weight per template.
    - segments: per (class, length), the ``top_k[class]`` heaviest segments plus
      ``__CHARS__`` = max(1, 0.5% of the full bucket weight).
    - unigrams: per-class char weights (and ``ANY`` over all chars); every char of the class
      is present (unseen chars get weight 1) so any password stays encodable.
    - fallback_lengths: password-length weights; every length 1..``max_len`` is present.

    Output is deterministic: keys are ordered by weight descending, then lexicographically
    (unigrams by code point, lengths numerically).

    Raises:
        ValueError: no usable training pairs, or ``max_len`` out of range.
    """
    if not 1 <= max_len <= MAX_FIELD_LEN:
        raise ValueError(f"max_len must be 1..{MAX_FIELD_LEN}")
    k = {**DEFAULT_TOP_K, **(top_k or {})}

    # defaultdict(int): integer counts stay ints (exact), float weights promote to float.
    templates: dict[str, float] = defaultdict(int)
    buckets: dict[tuple[str, int], dict[str, float]] = defaultdict(lambda: defaultdict(int))
    unigrams: dict[str, dict[str, float]] = {c: defaultdict(int) for c in CLASS_CHARS}
    lengths: dict[str, float] = defaultdict(int)

    used = 0
    for password, weight in pairs:
        if not is_valid_field(password, max_len) or not weight > 0:
            continue
        used += 1
        runs = parse(password)
        templates["".join(f"{c}{len(s)}" for c, s in runs)] += weight
        lengths[str(len(password))] += weight
        for cls, seg in runs:
            buckets[(cls, len(seg))][seg] += weight
            for ch in seg:
                unigrams[cls][ch] += weight
                unigrams["ANY"][ch] += weight
    if not used:
        raise ValueError("no valid training passwords")

    segments: dict[str, dict[str, dict[str, int]]] = {}
    for cls, n in sorted(buckets, key=lambda b: ("LDS".index(b[0]), b[1])):
        words = buckets[(cls, n)]
        kept = dict(_ranked(words)[: k[cls]])
        total = sum(words.values())
        if isinstance(total, int):
            kept[CHARS_TOKEN] = max(1, total // round(1 / CHARS_FRACTION))
        else:
            kept[CHARS_TOKEN] = max(1.0, CHARS_FRACTION * total)
        segments.setdefault(cls, {})[str(n)] = _finalize(kept)

    return {
        "version": 1,
        "kind": "password",
        "max_len": max_len,
        "path": dict(PATH_WEIGHTS),
        "templates": _finalize(templates),
        "segments": segments,
        "unigrams": {
            cls: _finalize(
                {ch: unigrams[cls][ch] for ch in chars if ch in unigrams[cls]}, chars, sort=False
            )
            for cls, chars in CLASS_CHARS.items()
        },
        "fallback_lengths": _finalize(
            {str(n): lengths[str(n)] for n in range(1, max_len + 1) if str(n) in lengths},
            [str(n) for n in range(1, max_len + 1)],
            sort=False,
        ),
    }


def save_model(model: Mapping[str, Any], path: str | Path) -> int:
    """Write ``model`` as gzipped JSON; byte-for-byte deterministic. Returns the file size.

    Key order is the model's insertion order (``train_password_model`` makes it
    deterministic); the gzip header carries no timestamp or file name.
    """
    data = json.dumps(model, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    blob = gzip.compress(data, compresslevel=9, mtime=0)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(blob)
    return len(blob)


def load_model(path: str | Path) -> dict[str, Any]:
    """Read a ``.json.gz`` model written by ``save_model`` (key order preserved).

    Raises:
        ValueError: the file is not a version-1 model object.
    """
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        model = json.load(fh)
    if not isinstance(model, dict) or model.get("version") != 1:
        raise ValueError("not a version-1 PCFG model file")
    return model
