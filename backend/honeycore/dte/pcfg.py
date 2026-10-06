"""PCFG model: parse, train, load/save ``pcfg_*_v1.json.gz``, shared DTE codec (§7.3-§7.4).

Owner: T1 — Nidhi. Phase 1 (password), Phase 2 (username + shared codec).

Pure library: the only I/O is reading/writing model files. Training input is an iterable
of ``(value, weight)`` pairs; the CLI that reads corpora is ``scripts/train_pcfg.py``.

Model format (v1)::

    {"version": 1, "kind": "password" | "username", "max_len": 32,
     "path": {"pcfg": 999, "fallback": 1},
     "templates": {"L6D2": ...},
     "segments": {"L": {"6": {"monkey": 123, "__CHARS__": 5}}, "D": {...}, "S": {...}},
     "unigrams": {"L": {...}, "D": {...}, "S": {...}, "ANY": {...}},
     "fallback_lengths": {"1": ..., ..., "32": ...},
     "email_domains": {"__NONE__": ..., "gmail.com": ..., ...}}     # username models only

Every weight is an int >= 1 and every distribution totals <= 2**31 (``int_codec.rescale``).

``_PCFGBase`` is the package-private 66-int encode/decode machinery shared by
``password_dte.PCFGPasswordModel`` and ``username_dte.PCFGUsernameModel``.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
import secrets
import string
from collections import defaultdict
from collections.abc import Container, Iterable, Iterator, Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar, Self

from honeycore.dte.int_codec import (
    MAX_TOTAL,
    Distribution,
    SeedReader,
    SeedWriter,
    decode_choice,
    encode_choice,
    rescale,
)
from honeycore.interfaces import MAX_FIELD_LEN, PRINTABLE_MAX, PRINTABLE_MIN, InvalidInputError

__all__ = [
    "CHARS_TOKEN",
    "CLASS_CHARS",
    "DEFAULT_TOP_K",
    "EMAIL_DOMAINS",
    "HELDOUT_THRESHOLD",
    "NO_DOMAIN",
    "NO_DOMAIN_SHARE",
    "PATH_WEIGHTS",
    "char_class",
    "email_domain_weights",
    "is_email_domain",
    "is_heldout",
    "is_valid_field",
    "load_model",
    "parse",
    "save_model",
    "split_email",
    "template",
    "train_password_model",
    "train_username_model",
]

CHARS_TOKEN = "__CHARS__"  # noqa: S105  (pseudo-terminal name, not a secret)
CHARS_FRACTION = 0.005  # __CHARS__ weight = max(1, 0.5% of the bucket)
PATH_WEIGHTS: dict[str, int] = {"pcfg": 999, "fallback": 1}
DEFAULT_TOP_K: dict[str, int] = {"L": 5000, "D": 2000, "S": 2000}
HELDOUT_THRESHOLD = 52  # sha256(pw)[0] < 52  ->  52/256 ~ 20.3% held out

NO_DOMAIN = "__NONE__"  # email-domain choice "not an email": the whole username is the PCFG part
NO_DOMAIN_SHARE = 0.55  # share of __NONE__ in the email-domain distribution
# Fixed built-in email-domain table (§7.4): plausible relative weights, not trained (the xato
# username list has no emails). Sorted by weight descending, then name.
EMAIL_DOMAINS: dict[str, int] = {
    "gmail.com": 620,
    "yahoo.com": 220,
    "hotmail.com": 200,
    "outlook.com": 130,
    "aol.com": 50,
    "icloud.com": 50,
    "yahoo.co.in": 45,
    "live.com": 40,
    "mail.ru": 40,
    "rediffmail.com": 40,
    "qq.com": 35,
    "163.com": 25,
    "msn.com": 25,
    "protonmail.com": 25,
    "yandex.ru": 25,
    "hotmail.co.uk": 22,
    "yahoo.co.uk": 22,
    "comcast.net": 20,
    "gmx.de": 18,
    "me.com": 18,
    "web.de": 18,
    "mail.com": 15,
    "ymail.com": 15,
    "att.net": 12,
    "gmx.com": 12,
    "sbcglobal.net": 12,
    "proton.me": 10,
    "verizon.net": 10,
    "zoho.com": 10,
    "btinternet.com": 8,
    "live.co.uk": 8,
}

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


def is_email_domain(domain: object) -> bool:
    """True iff ``domain`` can be an email-domain choice: printable, no ``@``, not ``__NONE__``,
    and at most ``MAX_FIELD_LEN - 2`` chars (so ``local@domain`` keeps a >= 1-char local part).
    """
    return (
        isinstance(domain, str)
        and is_valid_field(domain, MAX_FIELD_LEN - 2)
        and "@" not in domain
        and domain != NO_DOMAIN
    )


def split_email(value: str, domains: Container[str]) -> tuple[str | None, str]:
    """Split a username into ``(domain, local part)`` per §7.4, else ``(None, value)``.

    The split happens iff ``value`` has exactly one ``@``, the part after it is in ``domains``,
    and the local part is 1..``MAX_FIELD_LEN - len(domain) - 1`` chars.
    ``split_email("john@gmail.com", EMAIL_DOMAINS)`` -> ``("gmail.com", "john")``.
    """
    local, sep, domain = value.partition("@")
    if (
        sep
        and "@" not in domain
        and domain != NO_DOMAIN
        and domain in domains
        and 1 <= len(local) <= MAX_FIELD_LEN - len(domain) - 1
    ):
        return domain, local
    return None, value


def email_domain_weights() -> dict[str, int]:
    """The §7.4 email-domain distribution: ``__NONE__`` first (~55%), then ``EMAIL_DOMAINS``."""
    domains_total = sum(EMAIL_DOMAINS.values())
    none = round(domains_total * NO_DOMAIN_SHARE / (1 - NO_DOMAIN_SHARE))
    return _finalize({NO_DOMAIN: none, **EMAIL_DOMAINS}, sort=False)


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
    return _train_pcfg(pairs, "password", max_len, top_k)


def train_username_model(
    pairs: Iterable[tuple[str, float]],
    max_len: int = MAX_FIELD_LEN,
    top_k: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Train a v1 username PCFG from ``(username, weight)`` pairs (PROJECT-BRIEF.md §7.4).

    Same format and rules as ``train_password_model`` with ``kind = "username"``, plus
    ``email_domains`` = the fixed ``email_domain_weights()`` table. A training username that
    ``split_email`` maps to a known domain contributes only its local part to the PCFG, the
    same text the username DTE encodes for it.

    Raises:
        ValueError: no usable training pairs, or ``max_len`` out of range.
    """

    def local_parts() -> Iterator[tuple[str, float]]:
        for username, weight in pairs:
            if isinstance(username, str):
                username = split_email(username, EMAIL_DOMAINS)[1]
            yield username, weight

    model = _train_pcfg(local_parts(), "username", max_len, top_k)
    model["email_domains"] = email_domain_weights()
    return model


def _train_pcfg(
    pairs: Iterable[tuple[str, float]],
    kind: str,
    max_len: int,
    top_k: Mapping[str, int] | None,
) -> dict[str, Any]:
    """Shared trainer behind ``train_password_model`` / ``train_username_model``."""
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
        raise ValueError(f"no valid training {kind}s")

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
        "kind": kind,
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


# ---- shared DTE machinery (package-private) -----------------------------------------------

Segment = tuple[str, int]  # (class, length)

_TEMPLATE_RE = re.compile(r"(?:[LDS][1-9][0-9]*)+")
_SEGMENT_RE = re.compile(r"([LDS])([1-9][0-9]*)")


@lru_cache(maxsize=8)
def _read_model_file(path: str) -> dict[str, Any]:
    """Cached ``load_model``; callers must not mutate the returned dict."""
    return load_model(path)


def _validate_field(value: object, what: str) -> str:
    """Return ``value`` if it meets the §7.1 limits, else raise ``InvalidInputError``.

    The message names the field (``what``) but never echoes the value.
    """
    if not isinstance(value, str):
        raise InvalidInputError(f"{what} must be a string")
    if not 1 <= len(value) <= MAX_FIELD_LEN:
        raise InvalidInputError(f"{what} must be 1..{MAX_FIELD_LEN} characters")
    if any(not PRINTABLE_MIN <= ord(c) <= PRINTABLE_MAX for c in value):
        raise InvalidInputError(f"{what} must be printable ASCII (0x20-0x7E)")
    return value


def _template_segments(tmpl: str) -> tuple[Segment, ...]:
    if not _TEMPLATE_RE.fullmatch(tmpl):
        raise ValueError("malformed template in model")
    segs = tuple((c, int(n)) for c, n in _SEGMENT_RE.findall(tmpl))
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


def _log_p(dist: Distribution, i: int) -> float:
    return math.log(dist.weight(i)) - math.log(dist.total)


def _log_p_chars(unigram: Distribution, text: str) -> float:
    return math.fsum(_log_p(unigram, unigram.index_of(ch)) for ch in text)


class _PCFGBase:
    """Shared 66-int PCFG block codec for the password and username DTEs (§7.3-§7.4).

    A *block* is at most ``PASSWORD_SEED_INTS`` (66) big-endian uint32 choices (§7.2)::

        PCFG path:     [path] [template] then per segment: [vocab-or-__CHARS__] [word | char x n]
        fallback path: [path] [length] [char x length]

    Worst case is 2 + 32 segments + 32 chars = 66 ints. ``_decode_block`` is total: any ints
    give a 1..32-char printable string. Subclasses frame the block in their own seed (the
    password DTE pads it to 66 ints; the username DTE prefixes an email-domain choice) and
    set ``kind`` (the accepted model ``"kind"``) and ``default_model_path``.

    Loading normalises the model so totality and round-tripping hold for any trained model:
    every unigram covers its whole character class, every fallback length 1..32 exists, and
    every (class, length) bucket used by a template has a ``__CHARS__`` entry.
    """

    kind: ClassVar[str]
    default_model_path: ClassVar[Path]

    def __init__(self, model: Mapping[str, Any] | None = None) -> None:
        """Build the distributions from a parsed model dict (default model if ``None``).

        Raises:
            FileNotFoundError: ``model`` is ``None`` and the default model file is missing.
            ValueError: the model is malformed (wrong version/kind, bad template or segment).
        """
        if model is None:
            model = _read_model_file(str(self.default_model_path))
        self._load(model)

    @classmethod
    def from_file(cls, path: str | Path) -> Self:
        """Load a ``pcfg_<kind>_v1.json.gz`` model file."""
        return cls(_read_model_file(str(Path(path).resolve())))

    @classmethod
    def load_default(cls) -> Self:
        """Load ``default_model_path`` (resolved relative to the package)."""
        return cls()

    def _load(self, model: Mapping[str, Any]) -> None:
        kind = self.kind
        if model.get("version") != 1 or model.get("kind") != kind:
            raise ValueError(f"not a version-1 {kind} model")
        if model.get("max_len", MAX_FIELD_LEN) != MAX_FIELD_LEN:
            raise ValueError(f"{kind} model max_len must be {MAX_FIELD_LEN}")

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
                if word != CHARS_TOKEN and template(word) != f"{cls}{n}":
                    raise ValueError(f"segment bucket {cls}{n} has a word of the wrong shape")
            dist = _build_dist(words, (CHARS_TOKEN,))
            self._buckets[(cls, n)] = dist
            self._chars_idx[(cls, n)] = dist.index_of(CHARS_TOKEN)

    # ---- block encode / decode ----------------------------------------------------------

    def _encode_block(self, w: SeedWriter, text: str) -> None:
        """Append the <= 66 choices for a validated 1..32-char printable ``text`` to ``w``."""
        runs = parse(text)
        tmpl = "".join(f"{cls}{len(seg)}" for cls, seg in runs)
        if tmpl in self._template_segs:
            w.append(encode_choice(self._path, self._pcfg_idx))
            w.append(encode_choice(self._templates, self._templates.index_of(tmpl)))
            for cls, seg in runs:
                key = (cls, len(seg))
                bucket = self._buckets[key]
                try:
                    w.append(encode_choice(bucket, bucket.index_of(seg)))
                except KeyError:
                    w.append(encode_choice(bucket, self._chars_idx[key]))
                    _encode_chars(w, self._unigrams[cls], seg)
        else:
            w.append(encode_choice(self._path, self._fallback_idx))
            w.append(encode_choice(self._lengths, self._lengths.index_of(str(len(text)))))
            _encode_chars(w, self._unigrams["ANY"], text)

    def _decode_block(self, reader: SeedReader) -> str:
        """TOTAL: read <= 66 choices from ``reader``; return a 1..32-char printable string."""
        if decode_choice(self._path, reader.next()) == self._pcfg_idx:
            tmpl = self._templates.symbols[decode_choice(self._templates, reader.next())]
            parts: list[str] = []
            for cls, n in self._template_segs[tmpl]:
                bucket = self._buckets[(cls, n)]
                i = decode_choice(bucket, reader.next())
                if i == self._chars_idx[(cls, n)]:
                    parts.append(_decode_chars(reader, self._unigrams[cls], n))
                else:
                    parts.append(bucket.symbols[i])
            return "".join(parts)
        length = int(self._lengths.symbols[decode_choice(self._lengths, reader.next())])
        return _decode_chars(reader, self._unigrams["ANY"], length)

    def _log_p_block(self, text: str) -> float:
        """Natural log of the probability of the path ``_encode_block`` takes for ``text``."""
        runs = parse(text)
        tmpl = "".join(f"{cls}{len(seg)}" for cls, seg in runs)
        if tmpl in self._template_segs:
            lp = _log_p(self._path, self._pcfg_idx)
            lp += _log_p(self._templates, self._templates.index_of(tmpl))
            for cls, seg in runs:
                key = (cls, len(seg))
                bucket = self._buckets[key]
                try:
                    lp += _log_p(bucket, bucket.index_of(seg))
                except KeyError:
                    lp += _log_p(bucket, self._chars_idx[key])
                    lp += _log_p_chars(self._unigrams[cls], seg)
            return lp
        lp = _log_p(self._path, self._fallback_idx)
        lp += _log_p(self._lengths, self._lengths.index_of(str(len(text))))
        return lp + _log_p_chars(self._unigrams["ANY"], text)

    def _has_template(self, tmpl: str) -> bool:
        """True iff ``tmpl`` is one of the model's PCFG templates."""
        return tmpl in self._template_segs

    def _sample_segment(self, cls: str, n: int) -> str:
        """Draw an ``n``-char class-``cls`` segment: the bucket's vocab, else the unigram."""
        bucket = self._buckets.get((cls, n))
        if bucket is not None:
            i = decode_choice(bucket, secrets.randbits(32))
            if i != self._chars_idx[(cls, n)]:
                return bucket.symbols[i]
        unigram = self._unigrams[cls]
        return "".join(
            unigram.symbols[decode_choice(unigram, secrets.randbits(32))] for _ in range(n)
        )


def _encode_chars(w: SeedWriter, unigram: Distribution, text: str) -> None:
    for ch in text:
        w.append(encode_choice(unigram, unigram.index_of(ch)))


def _decode_chars(reader: SeedReader, unigram: Distribution, n: int) -> str:
    return "".join(unigram.symbols[decode_choice(unigram, reader.next())] for _ in range(n))
