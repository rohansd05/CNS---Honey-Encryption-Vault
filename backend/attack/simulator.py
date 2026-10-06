"""Dictionary-attack simulator: honey vault vs conventional baseline (§11).

Owner: T1 -- Dhruv. Phase 1.

The point of the demo (PROJECT-BRIEF.md §11, docs/api-contract.md ``POST /api/attack/dictionary``):
run *the same* wordlist -- a demo list with the real master password slipped in at a random
rank -- against two stolen vaults.

* The **conventional** vault is an oracle: its AEAD tag lets the attacker recognise the right
  password, so it reports "CRACKED at guess #n" and hands back the real credentials.
* The **honey** vault has no oracle: *every* guess decrypts to a complete, plausible vault, so
  the attacker drowns in near-identical decoys and cannot tell which one is real. The real
  password's guess is reported among the samples **without any flag** -- that is the whole idea.

This module is pure library code: it works against any :class:`honeycore.factory.HoneyCore`
bundle (stub or real) through the frozen ``HoneyVaultAPI`` / ``ConventionalVaultAPI`` protocols,
and touches nothing but ``secrets`` for randomness (AGENTS.md §1.5).
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from honeycore.interfaces import WrongPasswordError

if TYPE_CHECKING:
    from honeycore.interfaces import DecodedEntry

from attack.fallback_wordlist import FALLBACK_WORDS

DEFAULT_WORDLIST_PATH = Path(__file__).resolve().parent / "wordlists" / "demo_wordlist.txt"
DEFAULT_SAMPLE_LIMIT = 25


# ---------------------------------------------------------------------------------------------
# Minimal structural views of the two vault protocols (just what the attack needs)
# ---------------------------------------------------------------------------------------------
class _HoneyVault(Protocol):
    def unlock(self, master_password: str) -> Any:
        """Return an ``UnlockResult`` (``.entries`` is a list of decoded entries). Never raises."""
        ...


class _BaselineVault(Protocol):
    def unlock(self, master_password: str) -> list[Any]:
        """Return the entries, or raise ``WrongPasswordError`` for a wrong password."""
        ...


# ---------------------------------------------------------------------------------------------
# Result dataclasses -- ``to_dict`` matches docs/api-contract.md POST /api/attack/dictionary
# ---------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class BaselineResult:
    """Outcome against the conventional (oracle) vault."""

    cracked: bool
    guess_index: int | None  # 1-based rank of the cracking guess, or ``None``
    elapsed_ms: int
    recovered_entries: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        """Serialise to the ``baseline`` object of the dictionary-attack response."""
        return {
            "cracked": self.cracked,
            "guess_index": self.guess_index,
            "elapsed_ms": self.elapsed_ms,
            "recovered_entries": self.recovered_entries,
        }


@dataclass(frozen=True)
class HoneySample:
    """One decoy (or the real) vault surfaced in the response, indistinguishable by shape."""

    guess_index: int  # 1-based rank of this guess in the guess list
    guess: str
    entries: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        """Serialise to one item of ``honey.samples``."""
        return {"guess_index": self.guess_index, "guess": self.guess, "entries": self.entries}


@dataclass(frozen=True)
class HoneyResult:
    """Outcome against the honey vault: every guess yields a vault, so nothing is 'cracked'."""

    guesses_tried: int
    elapsed_ms: int
    distinct_vaults: int
    samples: list[HoneySample]

    def to_dict(self) -> dict[str, Any]:
        """Serialise to the ``honey`` object of the dictionary-attack response."""
        return {
            "guesses_tried": self.guesses_tried,
            "elapsed_ms": self.elapsed_ms,
            "distinct_vaults": self.distinct_vaults,
            "samples": [s.to_dict() for s in self.samples],
        }


@dataclass(frozen=True)
class RevealResult:
    """The post-hoc reveal: where the real password actually sat (``None`` if it was absent)."""

    real_guess_index: int | None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to the ``reveal`` object of the dictionary-attack response."""
        return {"real_guess_index": self.real_guess_index}


@dataclass(frozen=True)
class AttackReport:
    """Full dictionary-attack response (``baseline`` + ``honey`` + ``reveal``)."""

    baseline: BaselineResult
    honey: HoneyResult
    reveal: RevealResult

    def to_dict(self) -> dict[str, Any]:
        """Serialise to the complete ``POST /api/attack/dictionary`` response body."""
        return {
            "baseline": self.baseline.to_dict(),
            "honey": self.honey.to_dict(),
            "reveal": self.reveal.to_dict(),
        }


# ---------------------------------------------------------------------------------------------
# Wordlist loading
# ---------------------------------------------------------------------------------------------
def load_wordlist(path: str | Path = DEFAULT_WORDLIST_PATH) -> list[str]:
    """Load the demo wordlist from ``path``, one guess per line.

    Blank lines (after stripping surrounding whitespace) are dropped. If the file cannot be
    read or contains no usable lines, the built-in :data:`FALLBACK_WORDS` is returned instead,
    so the attack demo always has a wordlist.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return list(FALLBACK_WORDS)
    words = [stripped for line in text.splitlines() if (stripped := line.strip())]
    return words or list(FALLBACK_WORDS)


# ---------------------------------------------------------------------------------------------
# Guess-list construction
# ---------------------------------------------------------------------------------------------
def _dedupe(words: list[str]) -> list[str]:
    """Return ``words`` with later duplicates removed, preserving first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    for word in words:
        if word not in seen:
            seen.add(word)
            out.append(word)
    return out


def build_guess_list(
    real_password: str,
    max_guesses: int,
    wordlist: list[str],
    position: int | None = None,
) -> tuple[list[str], int]:
    """Build the attack guess list and report where the real password landed (1-based).

    The wordlist is de-duplicated and every occurrence of ``real_password`` is removed, then the
    first ``max_guesses - 1`` survivors are kept and ``real_password`` is spliced back in exactly
    once. Its rank is ``position`` when given, otherwise a ``secrets``-random rank in
    ``[max(10, n // 10), n]`` where ``n`` is the final list length -- i.e. never trivially early.

    Returns ``(guesses, real_index_1based)`` with ``len(guesses) == n`` and
    ``guesses[real_index_1based - 1] == real_password``.
    """
    if max_guesses < 1:
        raise ValueError("max_guesses must be >= 1")
    pool = [word for word in _dedupe(wordlist) if word != real_password]
    n = min(max_guesses, len(pool) + 1)
    base = pool[: n - 1]

    hi = n
    lo = min(max(10, n // 10), hi)  # clamp the lower bound down for very short lists
    lo = max(lo, 1)
    if position is None:
        index = lo + secrets.randbelow(hi - lo + 1)
    else:
        index = min(max(position, 1), n)  # keep an explicit position in range

    guesses = base[: index - 1] + [real_password] + base[index - 1 :]
    return guesses, index


# ---------------------------------------------------------------------------------------------
# The attack
# ---------------------------------------------------------------------------------------------
def _entry_to_dict(entry: DecodedEntry) -> dict[str, str]:
    """Serialise a decoded entry to the contract's entry shape (public id/service/timestamps)."""
    return {
        "id": entry.id,
        "service": entry.service,
        "username": entry.username,
        "password": entry.password,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }


def _vault_digest(entries: list[DecodedEntry]) -> str:
    """SHA-256 over the canonical decoded entries -- the identity of one unlocked vault."""
    body = json.dumps(
        [_entry_to_dict(e) for e in entries],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _baseline_cracks(vault: _BaselineVault, guess: str) -> bool:
    """``True`` iff ``guess`` verifies against the conventional vault (the oracle HE removes)."""
    try_password = getattr(vault, "try_password", None)
    if callable(try_password):
        return bool(try_password(guess))
    try:
        vault.unlock(guess)
    except WrongPasswordError:
        return False
    return True


def _sample_indices(n: int, limit: int, real_index: int | None) -> list[int]:
    """Pick <= ``limit`` 1-based indices spread evenly over ``1..n``, always including the real one.

    When the real guess is not already among the evenly spaced picks, the nearest pick is swapped
    out for it, so the real vault is surfaced without changing the sample count or flagging it.
    """
    if n <= 0:
        return []
    limit = max(1, min(limit, n))
    if n <= limit:
        chosen = set(range(1, n + 1))
    else:
        chosen = set()
        if limit == 1:
            chosen.add(1)
        else:
            for i in range(limit):
                chosen.add(1 + round(i * (n - 1) / (limit - 1)))
        filler = 1
        while len(chosen) < limit and filler <= n:  # top up if rounding collapsed picks
            chosen.add(filler)
            filler += 1

    if real_index is not None and 1 <= real_index <= n and real_index not in chosen:
        nearest = min(chosen, key=lambda x: (abs(x - real_index), x))
        chosen.discard(nearest)
        chosen.add(real_index)
    return sorted(chosen)


def run_dictionary_attack(
    honey_vault: _HoneyVault,
    baseline_vault: _BaselineVault,
    guesses: list[str],
    real_guess_index: int | None,
    sample_limit: int = DEFAULT_SAMPLE_LIMIT,
) -> AttackReport:
    """Run ``guesses`` against both vaults and build the dictionary-attack report.

    The baseline stops at the first guess that verifies and recovers its real entries. The honey
    vault is unlocked for *every* guess; ``distinct_vaults`` counts unique decoded vaults (by
    :func:`_vault_digest`) and ``samples`` surfaces an even spread of them, always including the
    real guess's vault (unflagged). ``real_guess_index`` is echoed into ``reveal`` and is expected
    to coincide with ``baseline.guess_index`` when the real password is present.
    """
    # --- conventional baseline: stop at the first verifying guess ---
    start = time.perf_counter()
    cracked = False
    crack_index: int | None = None
    recovered: list[dict[str, str]] = []
    for rank, guess in enumerate(guesses, start=1):
        if _baseline_cracks(baseline_vault, guess):
            cracked = True
            crack_index = rank
            recovered = [_entry_to_dict(e) for e in baseline_vault.unlock(guess)]
            break
    baseline_ms = round((time.perf_counter() - start) * 1000)
    baseline = BaselineResult(cracked, crack_index, baseline_ms, recovered)

    # --- honey vault: every guess yields a vault ---
    start = time.perf_counter()
    digests = [_vault_digest(honey_vault.unlock(guess).entries) for guess in guesses]
    honey_ms = round((time.perf_counter() - start) * 1000)
    distinct = len(set(digests))

    samples = [
        HoneySample(
            guess_index=index,
            guess=guesses[index - 1],
            entries=[_entry_to_dict(e) for e in honey_vault.unlock(guesses[index - 1]).entries],
        )
        for index in _sample_indices(len(guesses), sample_limit, real_guess_index)
    ]
    honey = HoneyResult(
        guesses_tried=len(guesses),
        elapsed_ms=honey_ms,
        distinct_vaults=distinct,
        samples=samples,
    )

    return AttackReport(baseline, honey, RevealResult(real_guess_index))
