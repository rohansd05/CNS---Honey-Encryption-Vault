"""Tests for ``honeycore.dte.password_dte`` (PROJECT-BRIEF.md §7.3). Owner: T1 — Nidhi.

The trained model may not exist yet, so most tests use a small synthetic model written to a
temp ``.json.gz`` (synthetic passwords only — never corpus lines in fixtures). Tests that need
the real model or the held-out split skip when those files are absent.
"""

from __future__ import annotations

import gzip
import json
import math
import secrets
import string
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from honeycore.dte.password_dte import (
    CHARS_TOKEN,
    DEFAULT_MODEL_PATH,
    MODEL_ID,
    PCFGPasswordModel,
    parse_template,
)
from honeycore.interfaces import (
    MAX_FIELD_LEN,
    PASSWORD_SEED_INTS,
    InvalidInputError,
    PasswordModel,
)

REPO = Path(__file__).resolve().parents[3]
HELDOUT = REPO / "data" / "processed" / "heldout_passwords.tsv"
SEED_LEN = PASSWORD_SEED_INTS * 4

printable_text = st.text(
    alphabet=st.characters(min_codepoint=0x20, max_codepoint=0x7E),
    min_size=1,
    max_size=MAX_FIELD_LEN,
)

# Synthetic training data: (password, count). Made up, not corpus lines.
_WORDS = {
    "monkey": 40,
    "dragon": 35,
    "shadow": 30,
    "sunny": 25,
    "tiger": 22,
    "honey": 20,
    "ocean": 18,
    "Pirate": 9,
    "blue": 15,
    "star": 14,
    "love": 30,
    "qwerty": 28,
    "secret": 12,
    "pass": 16,
}
_DIGITS = {"1": 50, "12": 30, "123": 40, "2000": 10, "99": 12, "7": 15, "1234": 20, "007": 5}
_SYMS = {"!": 30, "@": 10, ".": 8, "_": 6, "!!": 4, "#": 5}


def _training_set() -> list[tuple[str, int]]:
    data: list[tuple[str, int]] = []
    for w, wc in _WORDS.items():
        data.append((w, wc * 3))
        for d, dc in _DIGITS.items():
            data.append((w + d, wc * dc // 10 + 1))
            for s, sc in _SYMS.items():
                data.append((w + d + s, (wc * dc * sc) // 2000 + 1))
        for s, sc in _SYMS.items():
            data.append((w + s, wc * sc // 20 + 1))
            data.append((s + w, 1))
    for d, dc in _DIGITS.items():
        data.append((d * 2, dc))
        data.append((d, dc // 2 + 1))
    return data


def build_model(data: list[tuple[str, int]]) -> dict[str, Any]:
    """Tiny trainer following §7.3 (counts, __CHARS__ = max(1, 0.5% of bucket))."""
    templates: Counter[str] = Counter()
    segments: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    unigrams: dict[str, Counter[str]] = defaultdict(Counter)
    lengths: Counter[str] = Counter()
    for pw, count in data:
        template, segs = parse_template(pw)
        templates[template] += count
        lengths[str(len(pw))] += count
        for seg in segs:
            cls = parse_template(seg)[0][0]
            segments[cls][str(len(seg))][seg] += count
            for ch in seg:
                unigrams[cls][ch] += count
                unigrams["ANY"][ch] += count
    seg_out: dict[str, dict[str, dict[str, int]]] = {}
    for cls, by_len in segments.items():
        seg_out[cls] = {}
        for n, words in by_len.items():
            bucket = dict(words)
            bucket[CHARS_TOKEN] = max(1, sum(words.values()) // 200)
            seg_out[cls][n] = bucket
    return {
        "version": 1,
        "kind": "password",
        "max_len": MAX_FIELD_LEN,
        "path": {"pcfg": 999, "fallback": 1},
        "templates": dict(templates),
        "segments": seg_out,
        "unigrams": {c: dict(unigrams[c]) for c in ("L", "D", "S", "ANY")},
        "fallback_lengths": dict(lengths),
    }


def _write(path: Path, model: dict[str, Any]) -> Path:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(model, fh)
    return path


@pytest.fixture(scope="module")
def toy_dict() -> dict[str, Any]:
    return build_model(_training_set())


@pytest.fixture(scope="module")
def toy(toy_dict: dict[str, Any], tmp_path_factory: pytest.TempPathFactory) -> PCFGPasswordModel:
    path = _write(tmp_path_factory.mktemp("model") / "pcfg_password_v1.json.gz", toy_dict)
    return PCFGPasswordModel.from_file(path)


def _is_valid_password(pw: object) -> bool:
    return (
        isinstance(pw, str)
        and 1 <= len(pw) <= MAX_FIELD_LEN
        and all(0x20 <= ord(c) <= 0x7E for c in pw)
    )


# --- basics --------------------------------------------------------------------------------


def test_protocol_and_constants(toy: PCFGPasswordModel) -> None:
    assert isinstance(toy, PasswordModel)
    assert toy.model_id == MODEL_ID == "pcfg-password-v1"
    assert toy.seed_len == SEED_LEN == 264


def test_parse_template() -> None:
    assert parse_template("monkey12!") == ("L6D2S1", ["monkey", "12", "!"])
    assert parse_template("a b") == ("L1S1L1", ["a", " ", "b"])
    assert parse_template("!!") == ("S2", ["!!"])


def test_default_model_path_is_inside_package() -> None:
    assert DEFAULT_MODEL_PATH.parts[-3:] == ("honeycore", "models", "pcfg_password_v1.json.gz")


# --- encode / decode round trip ------------------------------------------------------------


@settings(max_examples=500, deadline=None)
@given(printable_text)
def test_roundtrip_any_printable(toy: PCFGPasswordModel, pw: str) -> None:
    seed = toy.encode(pw)
    assert len(seed) == SEED_LEN
    assert toy.decode(seed) == pw


@pytest.mark.parametrize(
    "pw",
    [
        "monkey123!",  # PCFG path, all vocab words
        "zzzzzz123!",  # PCFG template, L6 spelled via __CHARS__
        "honey7",
        "x",  # fallback (template L1 not in toy model)
        "~~~~ ~~~~",  # fallback
        "a1" * 16,  # 32 chars, 32 segments
        "Z" * 32,
        " ",
    ],
)
def test_roundtrip_examples(toy: PCFGPasswordModel, pw: str) -> None:
    assert toy.decode(toy.encode(pw)) == pw


def test_encode_is_randomised(toy: PCFGPasswordModel) -> None:
    a, b = toy.encode("monkey123!"), toy.encode("monkey123!")
    assert a != b
    assert toy.decode(a) == toy.decode(b) == "monkey123!"


@pytest.mark.parametrize("bad", ["", "a" * 33, "tab\there", "new\nline", "café", "\x7f"])
def test_encode_rejects_invalid(toy: PCFGPasswordModel, bad: str) -> None:
    with pytest.raises(InvalidInputError) as exc:
        toy.encode(bad)
    if bad:
        assert bad not in str(exc.value)


def test_encode_rejects_non_str(toy: PCFGPasswordModel) -> None:
    with pytest.raises(InvalidInputError):
        toy.encode(b"bytes")  # type: ignore[arg-type]


# --- totality ------------------------------------------------------------------------------


def test_decode_is_total_on_random_seeds(toy: PCFGPasswordModel) -> None:
    for _ in range(5000):
        assert _is_valid_password(toy.decode(secrets.token_bytes(SEED_LEN)))


@pytest.mark.parametrize("fill", [b"\x00", b"\xff", b"\x7f", b"\x80"])
def test_decode_is_total_on_constant_seeds(toy: PCFGPasswordModel, fill: bytes) -> None:
    assert _is_valid_password(toy.decode(fill * SEED_LEN))


@settings(max_examples=300)
@given(st.binary(min_size=SEED_LEN, max_size=SEED_LEN))
def test_decode_is_total_hypothesis(toy: PCFGPasswordModel, seed: bytes) -> None:
    assert _is_valid_password(toy.decode(seed))


@pytest.mark.parametrize("n", [0, 1, SEED_LEN - 1, SEED_LEN + 1, 532])
def test_decode_rejects_wrong_length(toy: PCFGPasswordModel, n: int) -> None:
    with pytest.raises(ValueError):
        toy.decode(b"\x00" * n)


def test_worst_case_seed_budget() -> None:
    # 32 one-char segments, each forced through __CHARS__: 2 + 32 + 32 = 66 ints exactly.
    template = "L1D1" * 16
    model = {
        "version": 1,
        "kind": "password",
        "max_len": 32,
        "path": {"pcfg": 1, "fallback": 1},
        "templates": {template: 1},
        "segments": {"L": {"1": {CHARS_TOKEN: 1}}, "D": {"1": {CHARS_TOKEN: 1}}},
        "unigrams": {},
        "fallback_lengths": {},
    }
    m = PCFGPasswordModel(model)
    pw = "a1" * 16
    assert m.decode(m.encode(pw)) == pw
    for _ in range(2000):
        assert _is_valid_password(m.decode(secrets.token_bytes(SEED_LEN)))


def test_minimal_model_is_total_and_roundtrips() -> None:
    # Empty unigrams / lengths / buckets are filled in by the loader.
    m = PCFGPasswordModel(
        {
            "version": 1,
            "kind": "password",
            "path": {"pcfg": 5, "fallback": 5},
            "templates": {"D4": 1},
        }
    )
    for pw in ["1234", "hello world!", "~"]:
        assert m.decode(m.encode(pw)) == pw
    for _ in range(500):
        assert _is_valid_password(m.decode(secrets.token_bytes(SEED_LEN)))


def test_float_weights_are_accepted() -> None:
    m = PCFGPasswordModel(
        {
            "version": 1,
            "kind": "password",
            "path": {"pcfg": 0.999, "fallback": 0.001},
            "templates": {"L4D2": 0.7, "L5": 0.3},
            "segments": {"L": {"4": {"blue": 0.5, CHARS_TOKEN: 0.01}}, "D": {"2": {"12": 1.5}}},
        }
    )
    for pw in ["blue12", "abcde", "zzzz99"]:
        assert m.decode(m.encode(pw)) == pw


# --- model validation ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "patch",
    [
        {"version": 2},
        {"kind": "username"},
        {"max_len": 16},
        {"path": {"pcfg": 1}},
        {"path": {"pcfg": 1, "fallback": 1, "other": 1}},
        {"templates": {}},
        {"templates": {"L6X2": 1}},
        {"templates": {"L3L2": 1}},
        {"templates": {"L33": 1}},
        {"templates": {"L0": 1}},
        {"segments": {"L": {"6": {"abc": 1}}}},
        {"unigrams": {"D": {"a": 1}}},
        {"fallback_lengths": {"33": 1}},
    ],
)
def test_malformed_models_rejected(toy_dict: dict[str, Any], patch: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        PCFGPasswordModel({**toy_dict, **patch})


def test_from_file_loads_gz(toy_dict: dict[str, Any], tmp_path: Path) -> None:
    m = PCFGPasswordModel.from_file(_write(tmp_path / "m.json.gz", toy_dict))
    assert m.decode(m.encode("dragon99")) == "dragon99"


# --- sample / sample_like ------------------------------------------------------------------


def test_samples_are_mostly_pcfg_vocab(toy: PCFGPasswordModel, toy_dict: dict[str, Any]) -> None:
    templates = set(toy_dict["templates"])
    vocab = {w for by_len in toy_dict["segments"].values() for b in by_len.values() for w in b}
    samples = [toy.sample() for _ in range(1000)]
    assert all(_is_valid_password(s) for s in samples)
    known_template = sum(parse_template(s)[0] in templates for s in samples)
    all_vocab = sum(all(seg in vocab for seg in parse_template(s)[1]) for s in samples)
    assert known_template >= 980  # path weight 999:1
    assert all_vocab >= 900  # __CHARS__ is ~0.5% per bucket
    assert len(set(samples)) > 100


@settings(max_examples=200, deadline=None)
@given(printable_text)
def test_sample_like_keeps_template(toy: PCFGPasswordModel, pw: str) -> None:
    out = toy.sample_like(pw)
    assert _is_valid_password(out)
    assert out != pw
    assert parse_template(out)[0] == parse_template(pw)[0]


@pytest.mark.parametrize("pw", ["monkey123!", "7", "!", "a", "Zz", "~~~~ ~~~~"])
def test_sample_like_examples(toy: PCFGPasswordModel, pw: str) -> None:
    for _ in range(50):
        out = toy.sample_like(pw)
        assert out != pw
        assert parse_template(out)[0] == parse_template(pw)[0]


def test_sample_like_falls_back_to_tail_tweak() -> None:
    # Only one D1 word and no __CHARS__ mass worth mentioning: 20 draws will almost always
    # return "7", forcing the tail tweak.
    m = PCFGPasswordModel(
        {
            "version": 1,
            "kind": "password",
            "path": {"pcfg": 1, "fallback": 1},
            "templates": {"D1": 1},
            "segments": {"D": {"1": {"7": 2**30, CHARS_TOKEN: 1}}},
        }
    )
    for _ in range(20):
        out = m.sample_like("7")
        assert out != "7"
        assert out in string.digits


def test_sample_like_rejects_invalid(toy: PCFGPasswordModel) -> None:
    with pytest.raises(InvalidInputError):
        toy.sample_like("")


# --- probability ---------------------------------------------------------------------------


@settings(max_examples=300, deadline=None)
@given(printable_text)
def test_probability_in_unit_interval(toy: PCFGPasswordModel, pw: str) -> None:
    p = toy.probability(pw)
    assert 0.0 < p <= 1.0
    assert toy.log_probability(pw) <= 0.0


def test_probability_matches_model_weights(
    toy: PCFGPasswordModel, toy_dict: dict[str, Any]
) -> None:
    path = toy_dict["path"]
    templates = toy_dict["templates"]
    bucket = toy_dict["segments"]["L"]["6"]
    expected = (
        path["pcfg"]
        / sum(path.values())
        * templates["L6"]
        / sum(templates.values())
        * bucket["monkey"]
        / sum(bucket.values())
    )
    assert toy.probability("monkey") == pytest.approx(expected, rel=1e-9)


def test_probability_orders_sensibly(toy: PCFGPasswordModel) -> None:
    assert toy.probability("monkey1") > toy.probability("mqnkey1")  # vocab > __CHARS__
    assert toy.probability("mqnkey1") > toy.probability("m0nkey1")  # PCFG > fallback


def test_probability_never_underflows_to_zero() -> None:
    m = PCFGPasswordModel(
        {
            "version": 1,
            "kind": "password",
            "path": {"pcfg": 1, "fallback": 2**30},
            "templates": {"L1S1" * 16: 1, "D1": 2**30},
            "segments": {"L": {"1": {"a": 2**29}}, "S": {"1": {"!": 2**29}}},
            "unigrams": {"L": {"a": 2**29}, "S": {"!": 2**29}},
        }
    )
    pw = "Z~" * 16
    assert m.log_probability(pw) < math.log(math.ulp(0.0))
    assert 0.0 < m.probability(pw) <= 1.0


def test_probability_rejects_invalid(toy: PCFGPasswordModel) -> None:
    with pytest.raises(InvalidInputError):
        toy.probability("a" * 33)


# --- real model / held-out data (skip until trained) ---------------------------------------

needs_default = pytest.mark.skipif(
    not DEFAULT_MODEL_PATH.exists(), reason="default model not trained yet (train_pcfg.py)"
)


@pytest.fixture(scope="module")
def default_model() -> PCFGPasswordModel:
    return PCFGPasswordModel.load_default()


@needs_default
def test_default_model_loads_and_is_total(default_model: PCFGPasswordModel) -> None:
    assert default_model.model_id == MODEL_ID
    assert isinstance(default_model, PasswordModel)
    for _ in range(1000):
        assert _is_valid_password(default_model.decode(secrets.token_bytes(SEED_LEN)))


@needs_default
@settings(max_examples=200, deadline=None)
@given(printable_text)
def test_default_model_roundtrip(default_model: PCFGPasswordModel, pw: str) -> None:
    assert default_model.decode(default_model.encode(pw)) == pw


@needs_default
@pytest.mark.skipif(not HELDOUT.exists(), reason="held-out split not generated yet")
def test_heldout_roundtrip(default_model: PCFGPasswordModel) -> None:
    passwords: list[str] = []
    with HELDOUT.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            pw = line.rstrip("\r\n").split("\t", 1)[0]
            if _is_valid_password(pw):
                passwords.append(pw)
            if len(passwords) == 2000:
                break
    assert passwords
    # Count failures without echoing corpus passwords into the test report.
    failures = sum(default_model.decode(default_model.encode(pw)) != pw for pw in passwords)
    assert failures == 0
