"""32-bit integer codec for weighted choices (PROJECT-BRIEF.md §7.2).

Owner: T1 — Nidhi. Phase 1.

Every probabilistic choice in a DTE consumes one 32-bit int ``r``. With integer weights
``w_i`` (total ``T <= 2**31``) and cumulative sums ``cum``:

- decode: ``i = bisect_right(cum, r % T)`` — total, any ``r`` maps to a valid index.
- encode(i): pick ``v`` uniformly in ``[cum[i-1], cum[i])``, then a uniform multiple of ``T``
  on top, so ``r`` is near-uniform over ``[0, 2**32)``.

Error messages never include symbols or seed ints: symbols can be password segments.
Randomness comes from ``secrets`` only.
"""

from __future__ import annotations

import math
import secrets
from bisect import bisect_right
from collections.abc import Mapping, Sequence

__all__ = [
    "MAX_TOTAL",
    "UINT32",
    "Distribution",
    "SeedReader",
    "SeedWriter",
    "decode_choice",
    "encode_choice",
    "rescale",
]

MAX_TOTAL = 2**31
UINT32 = 2**32


def _is_int(x: object) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


class Distribution:
    """An ordered, integer-weighted distribution over string symbols.

    Built from a ``Mapping[str, int]`` or a ``Sequence[tuple[str, int]]``; input order is
    preserved. Weights must be ints ``>= 1``; the total must be ``<= MAX_TOTAL``.

    Attributes:
        symbols: the symbols, in input order.
        cum: cumulative weights; ``cum[i] = w_0 + ... + w_i``.
        total: ``cum[-1]``.
    """

    __slots__ = ("symbols", "cum", "total", "_index")

    def __init__(self, items: Mapping[str, int] | Sequence[tuple[str, int]]) -> None:
        """Validate ``items`` and build the cumulative table.

        Raises:
            ValueError: empty input, duplicate or non-str symbols, non-int or < 1 weights,
                or total > ``MAX_TOTAL``.
        """
        pairs = list(items.items()) if isinstance(items, Mapping) else list(items)
        if not pairs:
            raise ValueError("distribution must have at least one symbol")
        symbols: list[str] = []
        cum: list[int] = []
        index: dict[str, int] = {}
        running = 0
        for pair in pairs:
            if len(pair) != 2:
                raise ValueError("distribution items must be (symbol, weight) pairs")
            symbol, weight = pair
            if not isinstance(symbol, str):
                raise ValueError("distribution symbols must be str")
            if symbol in index:
                raise ValueError("distribution symbols must be unique")
            if not _is_int(weight) or weight < 1:
                raise ValueError("distribution weights must be ints >= 1")
            running += weight
            if running > MAX_TOTAL:
                raise ValueError("distribution total exceeds MAX_TOTAL (2**31); rescale first")
            index[symbol] = len(symbols)
            symbols.append(symbol)
            cum.append(running)
        self.symbols: tuple[str, ...] = tuple(symbols)
        self.cum: tuple[int, ...] = tuple(cum)
        self.total: int = running
        self._index = index

    def __len__(self) -> int:
        """Number of symbols."""
        return len(self.symbols)

    def __repr__(self) -> str:
        return f"Distribution(n={len(self.symbols)}, total={self.total})"

    def index_of(self, symbol: str) -> int:
        """Return the index of ``symbol``.

        Raises:
            KeyError: ``symbol`` is not in the distribution (the symbol is not echoed).
        """
        try:
            return self._index[symbol]
        except KeyError:
            raise KeyError("symbol not in distribution") from None

    def symbol_at(self, i: int) -> str:
        """Return the symbol at index ``i`` (``IndexError`` if out of range)."""
        self._check_index(i)
        return self.symbols[i]

    def weight(self, i: int) -> int:
        """Return the integer weight of index ``i`` (``IndexError`` if out of range)."""
        self._check_index(i)
        return self.cum[i] - (self.cum[i - 1] if i else 0)

    def probability(self, i: int) -> float:
        """Return ``weight(i) / total``."""
        return self.weight(i) / self.total

    def _check_index(self, i: int) -> None:
        if not _is_int(i) or not 0 <= i < len(self.symbols):
            raise IndexError("distribution index out of range")


def encode_choice(dist: Distribution, index: int) -> int:
    """Encode choice ``index`` of ``dist`` as a random 32-bit int ``r`` (§7.2).

    ``decode_choice(dist, encode_choice(dist, i)) == i`` and ``0 <= r < 2**32``.

    Raises:
        IndexError: ``index`` is out of range.
    """
    dist._check_index(index)
    total = dist.total
    lo = dist.cum[index - 1] if index else 0
    hi = dist.cum[index]
    v = lo + secrets.randbelow(hi - lo)
    m = (UINT32 - 1 - v) // total
    return v + total * secrets.randbelow(m + 1)


def decode_choice(dist: Distribution, r: int) -> int:
    """Decode a 32-bit int ``r`` to a choice index of ``dist`` (§7.2). Never raises for ints."""
    return bisect_right(dist.cum, r % dist.total)


def rescale(weights: Mapping[str, int | float], max_total: int = MAX_TOTAL) -> dict[str, int]:
    """Turn positive weights into ints ``>= 1`` with total ``<= max_total``, keeping key order.

    - All ints whose sum already fits: returned unchanged (exactly proportional).
    - Otherwise (floats, or too large a sum): ``w' = max(1, floor(w * B / S))`` with
      ``S = sum(w)`` and budget ``B`` starting at ``max_total``; if the minimum-1 bumps push
      the total over ``max_total``, ``B`` is reduced by the excess and the step repeats.

    Deterministic: the same input (including order) always gives the same output. The
    mapping is monotone: a larger input weight never gets a smaller output weight.

    Raises:
        ValueError: a weight is not a finite number > 0, ``max_total < 1``, or there are more
            keys than ``max_total`` (each needs weight >= 1).
    """
    if not _is_int(max_total) or max_total < 1:
        raise ValueError("max_total must be an int >= 1")
    items = list(weights.items())
    if not items:
        return {}
    if len(items) > max_total:
        raise ValueError("more symbols than max_total; cannot give each weight >= 1")
    for _, w in items:
        if isinstance(w, bool) or not isinstance(w, int | float):
            raise ValueError("weights must be int or float")
        if not math.isfinite(w) or w <= 0:
            raise ValueError("weights must be finite and > 0")

    if all(_is_int(w) for _, w in items):
        int_total = sum(w for _, w in items)
        if int_total <= max_total:
            return {k: int(w) for k, w in items}
        return _rescale_loop(items, int_total, max_total, exact=True)
    return _rescale_loop(items, math.fsum(float(w) for _, w in items), max_total, exact=False)


def _rescale_loop(
    items: list[tuple[str, int | float]], total: int | float, max_total: int, *, exact: bool
) -> dict[str, int]:
    budget = max_total
    while True:
        if budget <= 0:
            scaled = [1] * len(items)
        elif exact:
            scaled = [max(1, int(w) * budget // int(total)) for _, w in items]
        else:
            factor = budget / total
            scaled = [max(1, math.floor(float(w) * factor)) for _, w in items]
        excess = sum(scaled) - max_total
        if excess <= 0:
            return {k: s for (k, _), s in zip(items, scaled, strict=True)}
        budget -= excess


class SeedWriter:
    """Collects 32-bit ints during encode and serialises them to a fixed-length seed."""

    __slots__ = ("_ints",)

    def __init__(self) -> None:
        """Start an empty writer."""
        self._ints: list[int] = []

    def __len__(self) -> int:
        """Number of ints appended so far."""
        return len(self._ints)

    def append(self, r: int) -> None:
        """Append one int ``r`` with ``0 <= r < 2**32``.

        Raises:
            ValueError: ``r`` is not an int in range (the value is not echoed).
        """
        if not _is_int(r) or not 0 <= r < UINT32:
            raise ValueError("seed int must be an int in [0, 2**32)")
        self._ints.append(r)

    def to_bytes(self, n_ints: int) -> bytes:
        """Return exactly ``4 * n_ints`` big-endian bytes, padding with ``secrets.randbits(32)``.

        Raises:
            ValueError: ``n_ints`` is negative or fewer than the ints already appended.
        """
        if not _is_int(n_ints) or n_ints < 0:
            raise ValueError("n_ints must be an int >= 0")
        if len(self._ints) > n_ints:
            raise ValueError("more ints appended than the seed can hold")
        ints = self._ints + [secrets.randbits(32) for _ in range(n_ints - len(self._ints))]
        return b"".join(r.to_bytes(4, "big") for r in ints)


class SeedReader:
    """Reads 32-bit big-endian ints from a seed, in order."""

    __slots__ = ("_seed", "_pos")

    def __init__(self, seed: bytes) -> None:
        """Wrap ``seed``.

        Raises:
            ValueError: ``len(seed)`` is not a multiple of 4.
        """
        if len(seed) % 4:
            raise ValueError("seed length must be a multiple of 4")
        self._seed = bytes(seed)
        self._pos = 0

    @property
    def remaining(self) -> int:
        """Number of ints not yet read."""
        return (len(self._seed) - self._pos) // 4

    def next(self) -> int:
        """Return the next int in ``[0, 2**32)``.

        Raises:
            ValueError: the seed is exhausted (callers size seeds so this never happens).
        """
        if self._pos >= len(self._seed):
            raise ValueError("seed exhausted")
        r = int.from_bytes(self._seed[self._pos : self._pos + 4], "big")
        self._pos += 4
        return r
