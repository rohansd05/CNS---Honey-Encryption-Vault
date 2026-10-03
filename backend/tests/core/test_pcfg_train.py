"""Tests for ``honeycore.dte.pcfg`` and ``scripts/train_pcfg.py``. Owner: T1 — Nidhi.

Training data here is a fixed, synthetic list (~300 passwords) — never corpus lines.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import re
import secrets
import string
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from honeycore.dte.int_codec import MAX_TOTAL, Distribution
from honeycore.dte.password_dte import PCFGPasswordModel, parse_template
from honeycore.dte.pcfg import (
    CHARS_TOKEN,
    CLASS_CHARS,
    PATH_WEIGHTS,
    is_heldout,
    is_valid_field,
    load_model,
    parse,
    save_model,
    template,
    train_password_model,
)
from honeycore.interfaces import MAX_FIELD_LEN, PASSWORD_SEED_INTS
from scripts.train_pcfg import parse_withcount, read_corpus, split_heldout, zipf_weight

_BASES = ["sun", "blue", "tiger", "maple", "rocket", "pixel", "cobalt", "honey", "orbit", "zebra"]
_DIGITS = ["", "1", "12", "123", "2024", "7", "99", "007"]
_SYMS = ["", "!", "@", "#!", "."]


def _training_list() -> list[tuple[str, int]]:
    """Fixed synthetic list: 10 bases x (digit/symbol tails + variants), ~300 entries."""
    data: list[tuple[str, int]] = []
    for i, base in enumerate(_BASES):
        for j, d in enumerate(_DIGITS):
            data.append((base + d, 100 - 7 * i - 3 * j))
        for k, s in enumerate(_SYMS[1:]):
            data.append((base.capitalize() + "1" + s, 20 - k - i))
            data.append((s + base + "2024", 5 + k))
        data += [(base + d + "!", 8 + j) for j, d in enumerate(_DIGITS[1:])]
        data += [(base + s, 6 + k) for k, s in enumerate(_SYMS[1:])]
        data.append((base * 2, 3))
        data.append((base.upper(), 2))
    data += [(str(n) * 3, 30 - n) for n in range(10)]
    data += [("a b c", 1), ("~~~", 1), ("x" * 32, 1), ("Q", 4)]
    return data


TRAIN = _training_list()


def _shape(tmpl: str) -> list[tuple[str, int]]:
    return [(c, int(n)) for c, n in re.findall(r"([LDS])(\d+)", tmpl)]


@pytest.fixture(scope="module")
def model() -> dict:
    return train_password_model(TRAIN)


# --- parsing -------------------------------------------------------------------------------


def test_training_list_size() -> None:
    assert 250 <= len(TRAIN) <= 350


@pytest.mark.parametrize(
    ("pw", "runs", "tmpl"),
    [
        ("monkey12!", [("L", "monkey"), ("D", "12"), ("S", "!")], "L6D2S1"),
        ("P@ssw0rd", [("L", "P"), ("S", "@"), ("L", "ssw"), ("D", "0"), ("L", "rd")], "L1S1L3D1L2"),
        ("a b", [("L", "a"), ("S", " "), ("L", "b")], "L1S1L1"),
        ("2024", [("D", "2024")], "D4"),
        ("!!..", [("S", "!!..")], "S4"),
    ],
)
def test_parse_and_template(pw: str, runs: list[tuple[str, str]], tmpl: str) -> None:
    assert parse(pw) == runs
    assert template(pw) == tmpl


@given(st.text(alphabet=st.characters(min_codepoint=0x20, max_codepoint=0x7E), max_size=40))
def test_parse_is_lossless_and_maximal(pw: str) -> None:
    runs = parse(pw)
    assert "".join(seg for _, seg in runs) == pw
    assert all(a[0] != b[0] for a, b in zip(runs, runs[1:], strict=False))
    assert template(pw) == parse_template(pw)[0]  # agrees with the DTE's parser


def test_character_classes() -> None:
    assert CLASS_CHARS["L"] == string.ascii_letters
    assert CLASS_CHARS["D"] == string.digits
    assert len(CLASS_CHARS["S"]) == 95 - 62
    assert " " in CLASS_CHARS["S"]
    assert len(CLASS_CHARS["ANY"]) == 95


@pytest.mark.parametrize(
    ("s", "ok"),
    [("a", True), ("x" * 32, True), (" ", True), ("", False), ("x" * 33, False)]
    + [("tab\t", False), ("café", False), ("\x7f", False), (b"ab", False), (None, False)],
)
def test_is_valid_field(s: object, ok: bool) -> None:
    assert is_valid_field(s) is ok


# --- held-out split ------------------------------------------------------------------------


def test_heldout_matches_definition() -> None:
    for pw in ["alpha", "bravo", "charlie", "delta", "echo"]:
        assert is_heldout(pw) is (hashlib.sha256(pw.encode()).digest()[0] < 52)


def test_heldout_is_deterministic_and_about_20_percent() -> None:
    words = [f"pw{i}" for i in range(20_000)]
    first = [is_heldout(w) for w in words]
    assert first == [is_heldout(w) for w in words]
    rate = sum(first) / len(words)
    assert abs(rate - 52 / 256) < 0.01


# --- model format --------------------------------------------------------------------------


def test_model_top_level_format(model: dict) -> None:
    assert list(model) == [
        "version",
        "kind",
        "max_len",
        "path",
        "templates",
        "segments",
        "unigrams",
        "fallback_lengths",
    ]
    assert model["version"] == 1
    assert model["kind"] == "password"
    assert model["max_len"] == MAX_FIELD_LEN
    assert model["path"] == PATH_WEIGHTS == {"pcfg": 999, "fallback": 1}
    assert set(model["unigrams"]) == {"L", "D", "S", "ANY"}
    assert set(model["segments"]) <= {"L", "D", "S"}
    assert list(model["fallback_lengths"]) == [str(n) for n in range(1, 33)]


def _distributions(model: dict) -> list[dict[str, int]]:
    out = [model["path"], model["templates"], model["fallback_lengths"]]
    out += list(model["unigrams"].values())
    out += [b for by_len in model["segments"].values() for b in by_len.values()]
    return out


def test_all_weights_are_ints_and_totals_fit(model: dict) -> None:
    for dist in _distributions(model):
        assert dist
        assert all(type(w) is int and w >= 1 for w in dist.values())
        assert sum(dist.values()) <= MAX_TOTAL
        Distribution(dist)


def test_huge_weights_are_rescaled() -> None:
    m = train_password_model([("alpha1", 2**40), ("beta22", 3 * 2**40), ("gamma", 0.5)])
    for dist in _distributions(m):
        assert all(type(w) is int and w >= 1 for w in dist.values())
        assert sum(dist.values()) <= MAX_TOTAL
    assert m["templates"]["L4D2"] / m["templates"]["L5D1"] == pytest.approx(3.0, rel=1e-6)


def test_templates_and_segments_match_training(model: dict) -> None:
    expected_templates = {template(pw) for pw, _ in TRAIN}
    assert set(model["templates"]) == expected_templates
    for tmpl in model["templates"]:
        for cls, n in _shape(tmpl):
            assert str(n) in model["segments"][cls]
    assert model["segments"]["L"]["5"]["tiger"] > 0
    assert model["segments"]["D"]["3"]["123"] > model["segments"]["D"]["3"]["000"]


def test_counts_are_kept_exactly_for_ints(model: dict) -> None:
    total_l1 = sum(w for pw, w in TRAIN if template(pw) == "L1")
    assert model["templates"]["L1"] == total_l1


def test_chars_token_weight(model: dict) -> None:
    for by_len in model["segments"].values():
        for bucket in by_len.values():
            assert CHARS_TOKEN in bucket
    words_l5 = {}
    for pw, w in TRAIN:
        for cls, seg in parse(pw):
            if cls == "L" and len(seg) == 5:
                words_l5[seg] = words_l5.get(seg, 0) + w
    assert model["segments"]["L"]["5"][CHARS_TOKEN] == max(1, sum(words_l5.values()) // 200)


def test_top_k_prunes_buckets() -> None:
    m = train_password_model(TRAIN, top_k={"L": 3, "D": 2, "S": 1})
    for cls, k in (("L", 3), ("D", 2), ("S", 1)):
        for bucket in m["segments"][cls].values():
            assert len(bucket) <= k + 1  # + __CHARS__
    # The heaviest D4 segments survive pruning.
    assert "2024" in m["segments"]["D"]["4"]


def test_unigrams_cover_every_class_char(model: dict) -> None:
    for cls, chars in CLASS_CHARS.items():
        assert list(model["unigrams"][cls]) == list(chars)  # code-point order, all present
    assert model["unigrams"]["L"]["e"] > model["unigrams"]["L"]["J"]  # seen > unseen (=1)


def test_invalid_and_nonpositive_pairs_are_skipped() -> None:
    m = train_password_model([("ok123", 5), ("", 9), ("x" * 33, 9), ("tab\t", 9), ("neg1", 0)])
    assert set(m["templates"]) == {"L2D3"}


def test_training_requires_data() -> None:
    with pytest.raises(ValueError):
        train_password_model([("", 1)])
    with pytest.raises(ValueError):
        train_password_model(TRAIN, max_len=33)


def test_training_is_deterministic() -> None:
    a = train_password_model(TRAIN)
    b = train_password_model(list(reversed(TRAIN)))
    assert a == b
    assert list(a["templates"]) == list(b["templates"])


# --- save / load ---------------------------------------------------------------------------


def test_save_load_roundtrip(model: dict, tmp_path: Path) -> None:
    p1, p2 = tmp_path / "a.json.gz", tmp_path / "sub" / "b.json.gz"
    size = save_model(model, p1)
    assert size == p1.stat().st_size
    loaded = load_model(p1)
    assert loaded == model
    assert list(loaded["templates"]) == list(model["templates"])  # key order preserved
    save_model(loaded, p2)
    assert p1.read_bytes() == p2.read_bytes()  # byte-for-byte deterministic


def test_load_rejects_non_model(tmp_path: Path) -> None:
    p = tmp_path / "bad.json.gz"
    p.write_bytes(gzip.compress(b'{"version": 2}'))
    with pytest.raises(ValueError):
        load_model(p)


def test_trained_model_works_with_password_dte(model: dict, tmp_path: Path) -> None:
    path = tmp_path / "pcfg_password_v1.json.gz"
    save_model(model, path)
    dte = PCFGPasswordModel.from_file(path)
    for pw in ["tiger123!", "Maple1@", "unseen-Pw 42", "x" * 32, "Q"]:
        assert dte.decode(dte.encode(pw)) == pw
    for _ in range(500):
        out = dte.decode(secrets.token_bytes(PASSWORD_SEED_INTS * 4))
        assert is_valid_field(out)


# --- train_pcfg.py helpers -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("  290729 123456", ("123456", 290729)),
        ("5 two words", ("two words", 5)),
        ("7  leading space", (" leading space", 7)),
        ("12 ", ("", 12)),
        ("no count here", None),
        ("   0 zero", None),
        ("", None),
    ],
)
def test_parse_withcount(line: str, expected: tuple[str, int] | None) -> None:
    assert parse_withcount(line) == expected


def test_zipf_weight() -> None:
    assert zipf_weight(1000, 1000) == pytest.approx(1.0)
    assert zipf_weight(1, 1000) == pytest.approx(1000**0.9)
    assert zipf_weight(1, 1000) > zipf_weight(2, 1000) > zipf_weight(3, 1000)


def test_read_corpus_and_heldout_split() -> None:
    lines = [f"{100 - i} {pw}" for i, (pw, _) in enumerate(TRAIN[:100])]
    lines += ["garbage", "3 café"]
    stream = io.BytesIO("\n".join(lines).encode("latin-1"))
    stats = dict.fromkeys(
        ["lines", "malformed", "invalid", "valid", "kept", "heldout", "heldout_written"], 0
    )
    out = io.StringIO()
    kept = list(split_heldout(read_corpus(stream, "withcount", 10_000, stats), out, 5, stats))
    assert stats["lines"] == 102
    assert stats["malformed"] == 1
    assert stats["invalid"] == 1
    assert stats["valid"] == 100
    assert stats["kept"] + stats["heldout"] == 100
    assert not any(is_heldout(pw) for pw, _ in kept)
    written = out.getvalue().splitlines()
    assert len(written) == min(5, stats["heldout"]) == stats["heldout_written"]
    assert all(is_heldout(row.split("\t")[0]) for row in written)


def test_read_corpus_respects_max_lines_and_plain_weights() -> None:
    stream = io.BytesIO(b"first\nsecond\nthird\nfourth\n")
    stats = dict.fromkeys(["lines", "malformed", "invalid", "valid"], 0)
    pairs = list(read_corpus(stream, "plain", 3, stats))
    assert [pw for pw, _ in pairs] == ["first", "second", "third"]
    assert pairs[0][1] > pairs[1][1] > pairs[2][1] == pytest.approx(1.0)
    assert stats["lines"] == 3
