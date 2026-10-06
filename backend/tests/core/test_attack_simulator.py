"""Tests for the dictionary-attack simulator (``attack/simulator.py``). Owner: T1 -- Dhruv.

Exercises both honeycore bundles: always the ``stub`` implementation, and the ``real`` one too
when it loads in this environment (``load_honeycore('real')`` raises ``NotImplementedError`` while
a track's piece is still missing -- then we simply skip it). Everything uses the ``demo`` KDF
profile and stays well under the §11 20-second budget.
"""

from __future__ import annotations

import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from attack.fallback_wordlist import FALLBACK_WORDS
from attack.simulator import (
    DEFAULT_WORDLIST_PATH,
    AttackReport,
    build_guess_list,
    load_wordlist,
    run_dictionary_attack,
)
from honeycore.factory import HoneyCore, load_honeycore
from honeycore.interfaces import Entry

MASTER = "correct horse battery staple"
SAMPLE_ENTRIES = [
    Entry("github.com", "demo_developer", "ghp_K992jSkA0182mZls"),
    Entry("proton.me", "demo_secops@proton.me", "Tr0ub4dor&3#Priv"),
    Entry("aws.amazon.com", "aws_admin_demo", "AKIAIOSFODNN7EXMPL"),
]


def _try_real() -> HoneyCore | None:
    """Return the real bundle, or ``None`` if a honeycore piece is not implemented yet."""
    try:
        return load_honeycore("real")
    except NotImplementedError:
        return None


def _available_cores() -> list[HoneyCore]:
    cores = [load_honeycore("stub")]
    real = _try_real()
    if real is not None:
        cores.append(real)
    return cores


CORES = _available_cores()
CORE_IDS = [core.vault_cls.__name__ for core in CORES]


@pytest.fixture(params=CORES, ids=CORE_IDS)
def core(request: pytest.FixtureRequest) -> HoneyCore:
    """Each available honeycore bundle in turn (stub, and real when it loads)."""
    return request.param


def _build_vaults(core: HoneyCore):
    """A honey vault and a conventional baseline holding the same entries under ``MASTER``."""
    honey = core.vault_cls.new("demo")
    baseline = core.conventional_vault_cls.new(MASTER, "demo")
    for entry in SAMPLE_ENTRIES:
        honey.add_entry(MASTER, entry)
        baseline.add_entry(MASTER, entry)
    return honey, baseline


# ---- wordlist loading ----
def test_load_wordlist_reads_demo_file() -> None:
    words = load_wordlist()
    assert DEFAULT_WORDLIST_PATH.exists()
    assert isinstance(words, list) and len(words) > 100
    assert all(isinstance(w, str) and w == w.strip() and w for w in words)
    assert "password" in words


def test_load_wordlist_falls_back_when_missing_or_empty(tmp_path) -> None:
    assert load_wordlist(tmp_path / "does-not-exist.txt") == FALLBACK_WORDS
    empty = tmp_path / "empty.txt"
    empty.write_text("   \n\n\t\n", encoding="utf-8")
    assert load_wordlist(empty) == FALLBACK_WORDS


def test_fallback_words_are_valid_and_unique() -> None:
    assert len(FALLBACK_WORDS) >= 300
    assert len(set(FALLBACK_WORDS)) == len(FALLBACK_WORDS)
    for word in FALLBACK_WORDS:
        assert 1 <= len(word) <= 32
        assert all(0x20 <= ord(ch) <= 0x7E for ch in word)


# ---- build_guess_list ----
def test_build_guess_list_inserts_real_once_at_random_rank() -> None:
    words = [f"word{i}" for i in range(500)]
    guesses, index = build_guess_list(MASTER, 200, words)
    assert len(guesses) == 200
    assert guesses.count(MASTER) == 1
    assert guesses[index - 1] == MASTER
    assert len(set(guesses)) == len(guesses)
    assert max(10, 200 // 10) <= index <= 200


def test_build_guess_list_honours_explicit_position() -> None:
    words = [f"word{i}" for i in range(50)]
    guesses, index = build_guess_list(MASTER, 40, words, position=7)
    assert index == 7
    assert guesses[6] == MASTER


def test_build_guess_list_removes_existing_real_and_dedupes() -> None:
    words = ["a", "b", MASTER, "a", "c", MASTER, "d"]
    guesses, index = build_guess_list(MASTER, 100, words)
    assert guesses.count(MASTER) == 1
    assert len(guesses) == 5  # pool dedupes to a,b,c,d then real is spliced in
    assert sorted(guesses) == sorted(["a", "b", "c", "d", MASTER])
    assert guesses[index - 1] == MASTER


def test_build_guess_list_truncates_to_max_guesses() -> None:
    words = [f"word{i}" for i in range(500)]
    guesses, index = build_guess_list(MASTER, 10, words)
    assert len(guesses) == 10
    assert guesses[index - 1] == MASTER


def test_build_guess_list_rejects_zero() -> None:
    with pytest.raises(ValueError, match="max_guesses"):
        build_guess_list(MASTER, 0, ["a", "b"])


@settings(max_examples=100, deadline=None)
@given(
    size=st.integers(min_value=0, max_value=60), max_guesses=st.integers(min_value=1, max_value=80)
)
def test_build_guess_list_properties(size: int, max_guesses: int) -> None:
    words = [f"word{i}" for i in range(size)]
    guesses, index = build_guess_list(MASTER, max_guesses, words)
    n = min(max_guesses, size + 1)  # all words distinct and != MASTER
    assert len(guesses) == n
    assert guesses.count(MASTER) == 1
    assert len(set(guesses)) == len(guesses)
    lo = min(max(10, n // 10), n)
    assert lo <= index <= n
    assert guesses[index - 1] == MASTER


# ---- run_dictionary_attack ----
def test_dictionary_attack_cracks_baseline_but_not_honey(core: HoneyCore) -> None:
    honey, baseline = _build_vaults(core)
    guesses, index = build_guess_list(MASTER, 180, load_wordlist()[:200])
    report = run_dictionary_attack(honey, baseline, guesses, index, sample_limit=25)
    assert isinstance(report, AttackReport)

    real_triples = {(e.service, e.username, e.password) for e in SAMPLE_ENTRIES}

    # conventional oracle: cracks exactly where the real password sits, recovers real creds
    assert report.baseline.cracked
    assert report.baseline.guess_index == index
    assert {
        (e["service"], e["username"], e["password"]) for e in report.baseline.recovered_entries
    } == real_triples

    # honey vault: tried everything, (almost) every guess a distinct vault, nothing "cracked"
    assert report.honey.guesses_tried == len(guesses)
    assert report.honey.distinct_vaults >= 0.99 * len(guesses)

    # samples: capped at the limit, ranks in range and ordered, real guess present + unflagged
    samples = report.honey.samples
    assert len(samples) <= 25
    ranks = [s.guess_index for s in samples]
    assert ranks == sorted(set(ranks))
    assert all(1 <= rank <= len(guesses) for rank in ranks)
    real_samples = [s for s in samples if s.guess_index == index]
    assert len(real_samples) == 1
    real_sample = real_samples[0]
    assert real_sample.guess == MASTER
    assert {
        (e["service"], e["username"], e["password"]) for e in real_sample.entries
    } == real_triples
    assert set(real_sample.to_dict()) == {"guess_index", "guess", "entries"}

    assert report.reveal.real_guess_index == index


def test_dictionary_attack_report_matches_contract_shape(core: HoneyCore) -> None:
    honey, baseline = _build_vaults(core)
    guesses, index = build_guess_list(MASTER, 100, load_wordlist()[:120])
    data = run_dictionary_attack(honey, baseline, guesses, index).to_dict()

    assert set(data) == {"baseline", "honey", "reveal"}
    assert set(data["baseline"]) == {"cracked", "guess_index", "elapsed_ms", "recovered_entries"}
    assert set(data["honey"]) == {"guesses_tried", "elapsed_ms", "distinct_vaults", "samples"}
    assert set(data["reveal"]) == {"real_guess_index"}
    entry = data["honey"]["samples"][0]["entries"][0]
    assert set(entry) == {"id", "service", "username", "password", "created_at", "updated_at"}
    assert isinstance(data["honey"]["elapsed_ms"], int)
    json.dumps(data)  # must be JSON-serialisable for the API layer


def test_dictionary_attack_when_real_password_absent(core: HoneyCore) -> None:
    honey, baseline = _build_vaults(core)
    guesses = [w for w in load_wordlist()[:60] if w != MASTER][:50]
    assert MASTER not in guesses
    report = run_dictionary_attack(honey, baseline, guesses, None)

    assert not report.baseline.cracked
    assert report.baseline.guess_index is None
    assert report.baseline.recovered_entries == []
    assert report.reveal.real_guess_index is None
    assert report.honey.guesses_tried == len(guesses)
    assert len(report.honey.samples) <= 25
