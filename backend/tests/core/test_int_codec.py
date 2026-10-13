"""Tests for ``honeycore.dte.int_codec`` (PROJECT-BRIEF.md §7.2). Owner: T1 — Nidhi."""

from __future__ import annotations

import ast
import math
import secrets
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from honeycore.dte import int_codec
from honeycore.dte.int_codec import (
    MAX_TOTAL,
    UINT32,
    Distribution,
    SeedReader,
    SeedWriter,
    decode_choice,
    encode_choice,
    rescale,
)

BACKEND = Path(__file__).resolve().parents[2]

weight_lists = st.lists(st.integers(min_value=1, max_value=10**6), min_size=1, max_size=60)


def _dist(weights: list[int]) -> Distribution:
    return Distribution([(f"s{i}", w) for i, w in enumerate(weights)])


# --- constants ---------------------------------------------------------------------------


def test_constants() -> None:
    assert MAX_TOTAL == 2**31
    assert UINT32 == 2**32


# --- Distribution --------------------------------------------------------------------------


def test_distribution_from_mapping_preserves_order() -> None:
    d = Distribution({"b": 3, "a": 1, "c": 6})
    assert d.symbols == ("b", "a", "c")
    assert d.cum == (3, 4, 10)
    assert d.total == 10
    assert len(d) == 3


def test_distribution_from_sequence_preserves_order() -> None:
    d = Distribution([("x", 2), ("y", 5)])
    assert d.symbols == ("x", "y")
    assert d.cum == (2, 7)
    assert d.total == 7


def test_distribution_accessors() -> None:
    d = Distribution({"a": 1, "b": 3})
    assert d.index_of("b") == 1
    assert d.symbol_at(0) == "a"
    assert d.weight(0) == 1
    assert d.weight(1) == 3
    assert d.probability(1) == pytest.approx(0.75)


@given(weight_lists)
def test_distribution_probabilities_sum_to_one(weights: list[int]) -> None:
    d = _dist(weights)
    assert d.total == sum(weights)
    assert [d.weight(i) for i in range(len(d))] == weights
    assert math.fsum(d.probability(i) for i in range(len(d))) == pytest.approx(1.0)


def test_index_of_missing_raises_keyerror_without_echoing_symbol() -> None:
    d = Distribution({"a": 1})
    with pytest.raises(KeyError) as exc:
        d.index_of("hunter2")
    assert "hunter2" not in str(exc.value)


@pytest.mark.parametrize("i", [-1, 2, 100])
def test_out_of_range_index_raises(i: int) -> None:
    d = Distribution({"a": 1, "b": 1})
    with pytest.raises(IndexError):
        d.symbol_at(i)
    with pytest.raises(IndexError):
        d.weight(i)
    with pytest.raises(IndexError):
        encode_choice(d, i)


@pytest.mark.parametrize(
    "items",
    [
        {},
        [],
        {"a": 0},
        {"a": -1},
        {"a": 1.0},
        {"a": True},
        {"a": "3"},
        [("a", 1), ("a", 2)],
        [(1, 1)],
        {"a": MAX_TOTAL + 1},
        {"a": MAX_TOTAL, "b": 1},
    ],
)
def test_distribution_rejects_invalid(items: object) -> None:
    with pytest.raises(ValueError):
        Distribution(items)  # type: ignore[arg-type]


def test_distribution_accepts_max_total() -> None:
    d = Distribution({"a": MAX_TOTAL - 1, "b": 1})
    assert d.total == MAX_TOTAL


# --- encode / decode -----------------------------------------------------------------------


@given(weight_lists, st.data())
def test_decode_encode_roundtrip(weights: list[int], data: st.DataObject) -> None:
    d = _dist(weights)
    i = data.draw(st.integers(min_value=0, max_value=len(weights) - 1))
    r = encode_choice(d, i)
    assert 0 <= r < UINT32
    assert decode_choice(d, r) == i


@given(st.lists(st.integers(min_value=1, max_value=2**24), min_size=1, max_size=8))
def test_roundtrip_with_large_totals(weights: list[int]) -> None:
    # Scale towards MAX_TOTAL so few multiples of T fit in 2**32.
    big = rescale({f"s{i}": w for i, w in enumerate(weights)})
    d = Distribution(big)
    for i in range(len(d)):
        r = encode_choice(d, i)
        assert 0 <= r < UINT32
        assert decode_choice(d, r) == i


def test_roundtrip_every_index_at_max_total() -> None:
    d = Distribution({"a": 1, "b": MAX_TOTAL - 2, "c": 1})
    for i in range(3):
        for _ in range(200):
            r = encode_choice(d, i)
            assert 0 <= r < UINT32
            assert decode_choice(d, r) == i


@given(weight_lists, st.integers(min_value=0, max_value=UINT32 - 1))
def test_decode_is_total(weights: list[int], r: int) -> None:
    d = _dist(weights)
    assert 0 <= decode_choice(d, r) < len(weights)


def test_decode_edges() -> None:
    d = Distribution({"a": 1, "b": 2, "c": 3})
    assert decode_choice(d, 0) == 0
    assert decode_choice(d, 1) == 1
    assert decode_choice(d, 2) == 1
    assert decode_choice(d, 3) == 2
    assert decode_choice(d, 5) == 2
    assert decode_choice(d, 6) == 0  # wraps: 6 % 6 == 0
    assert 0 <= decode_choice(d, UINT32 - 1) < 3


def test_decode_frequencies_match_weights() -> None:
    weights = {"common": 500, "mid": 300, "rare": 150, "tiny": 49, "one": 1}
    d = Distribution(weights)
    n = 200_000
    counts = [0] * len(d)
    for _ in range(n):
        counts[decode_choice(d, secrets.randbits(32))] += 1
    for i in range(len(d)):
        assert abs(counts[i] / n - d.probability(i)) < 0.01


def test_encoded_ints_are_near_uniform() -> None:
    # Encoding choices sampled by weight should give r roughly uniform over [0, 2**32).
    d = Distribution({"a": 7, "b": 2, "c": 1})
    n = 50_000
    buckets = [0] * 8
    for _ in range(n):
        i = decode_choice(d, secrets.randbits(32))
        buckets[encode_choice(d, i) * 8 // UINT32] += 1
    for count in buckets:
        assert abs(count / n - 1 / 8) < 0.01


# --- rescale -------------------------------------------------------------------------------

positive_floats = st.floats(
    min_value=1e-12, max_value=1e12, allow_nan=False, allow_infinity=False, exclude_min=False
)
weight_maps = st.dictionaries(
    st.text(min_size=1, max_size=6),
    st.one_of(st.integers(min_value=1, max_value=2**40), positive_floats),
    min_size=1,
    max_size=60,
)


@settings(max_examples=300)
@given(weight_maps, st.sampled_from([MAX_TOTAL, 2**20, 1000, 60]))
def test_rescale_properties(weights: dict[str, int | float], max_total: int) -> None:
    out = rescale(weights, max_total)
    assert list(out) == list(weights)  # same keys, same order
    assert all(type(v) is int and v >= 1 for v in out.values())
    assert sum(out.values()) <= max_total
    assert rescale(weights, max_total) == out  # deterministic
    # Monotone: a larger weight never gets a smaller integer weight.
    keys = list(weights)
    for a in keys:
        for b in keys:
            if weights[a] > weights[b]:
                assert out[a] >= out[b]
    Distribution(out)  # always a valid distribution


def test_rescale_ints_that_fit_are_unchanged() -> None:
    w = {"a": 5, "b": 1, "c": 1000}
    assert rescale(w) == w


def test_rescale_is_proportional() -> None:
    w = {f"s{i}": 1 / (i + 1) ** 0.9 for i in range(1000)}  # Zipf, as in train_pcfg
    out = rescale(w)
    total_in = math.fsum(w.values())
    total_out = sum(out.values())
    assert total_out <= MAX_TOTAL
    assert total_out > MAX_TOTAL * 0.999
    for k in w:
        assert out[k] / total_out == pytest.approx(w[k] / total_in, rel=1e-4)


def test_rescale_large_ints_scaled_down() -> None:
    out = rescale({"a": 3 * 2**40, "b": 2**40})
    assert sum(out.values()) <= MAX_TOTAL
    assert out["a"] / out["b"] == pytest.approx(3.0, rel=1e-6)


def test_rescale_min_weight_bump_stays_within_budget() -> None:
    w = {"big": 1e9, **{f"t{i}": 1e-9 for i in range(50)}}
    out = rescale(w, 100)
    assert all(out[f"t{i}"] == 1 for i in range(50))
    assert sum(out.values()) <= 100
    assert out["big"] >= 49  # float rounding may cost one unit


def test_rescale_exactly_n_budget_gives_all_ones() -> None:
    out = rescale({"a": 1e6, "b": 1.0, "c": 3.5}, 3)
    assert out == {"a": 1, "b": 1, "c": 1}


def test_rescale_empty() -> None:
    assert rescale({}) == {}


@pytest.mark.parametrize(
    ("weights", "max_total"),
    [
        ({"a": 0}, MAX_TOTAL),
        ({"a": -1.5}, MAX_TOTAL),
        ({"a": float("nan")}, MAX_TOTAL),
        ({"a": float("inf")}, MAX_TOTAL),
        ({"a": True}, MAX_TOTAL),
        ({"a": "1"}, MAX_TOTAL),
        ({"a": 1, "b": 1, "c": 1}, 2),
        ({"a": 1}, 0),
    ],
)
def test_rescale_rejects_invalid(weights: dict[str, object], max_total: int) -> None:
    with pytest.raises(ValueError):
        rescale(weights, max_total)  # type: ignore[arg-type]


# --- SeedWriter / SeedReader ---------------------------------------------------------------


@given(
    st.lists(st.integers(min_value=0, max_value=UINT32 - 1), max_size=66),
    st.integers(min_value=0, max_value=20),
)
def test_writer_reader_roundtrip(ints: list[int], extra: int) -> None:
    w = SeedWriter()
    for r in ints:
        w.append(r)
    assert len(w) == len(ints)
    n = len(ints) + extra
    seed = w.to_bytes(n)
    assert len(seed) == 4 * n
    reader = SeedReader(seed)
    assert reader.remaining == n
    assert [reader.next() for _ in ints] == ints
    assert reader.remaining == extra
    for _ in range(extra):
        assert 0 <= reader.next() < UINT32
    assert reader.remaining == 0
    with pytest.raises(ValueError):
        reader.next()


def test_writer_is_big_endian() -> None:
    w = SeedWriter()
    w.append(0x01020304)
    assert w.to_bytes(1) == b"\x01\x02\x03\x04"


def test_writer_padding_is_random() -> None:
    w = SeedWriter()
    w.append(7)
    a, b = w.to_bytes(10), w.to_bytes(10)
    assert a[:4] == b[:4] == (7).to_bytes(4, "big")
    assert a[4:] != b[4:]  # 2**-288 chance of a false failure


def test_writer_rejects_overflow() -> None:
    w = SeedWriter()
    for r in range(3):
        w.append(r)
    with pytest.raises(ValueError):
        w.to_bytes(2)
    assert len(w.to_bytes(3)) == 12


@pytest.mark.parametrize("r", [-1, UINT32, 2**64, True, 1.0])
def test_writer_rejects_out_of_range(r: object) -> None:
    with pytest.raises(ValueError) as exc:
        SeedWriter().append(r)  # type: ignore[arg-type]
    assert str(r) not in str(exc.value)


def test_writer_rejects_negative_length() -> None:
    with pytest.raises(ValueError):
        SeedWriter().to_bytes(-1)


@pytest.mark.parametrize("seed", [b"\x00", b"\x00" * 5, b"\x00" * 7])
def test_reader_rejects_misaligned_seed(seed: bytes) -> None:
    with pytest.raises(ValueError):
        SeedReader(seed)


def test_reader_empty_seed() -> None:
    reader = SeedReader(b"")
    assert reader.remaining == 0
    with pytest.raises(ValueError):
        reader.next()


@given(st.binary(min_size=0, max_size=64).filter(lambda b: len(b) % 4 == 0))
def test_any_seed_decodes_with_any_distribution(seed: bytes) -> None:
    d = Distribution({"a": 3, "b": 1, "c": 9})
    reader = SeedReader(seed)
    while reader.remaining:
        assert 0 <= decode_choice(d, reader.next()) < 3


# --- invariant: no `random` module ---------------------------------------------------------


def _imports_random(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name.split(".")[0] == "random" for a in node.names):
                return True
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module.split(".")[0] == "random":
                return True
    return False


def test_int_codec_does_not_use_random_module() -> None:
    assert not _imports_random(Path(int_codec.__file__))
    assert "random" not in vars(int_codec)


@pytest.mark.parametrize("package", ["honeycore", "app"])
def test_no_random_module_in_package(package: str) -> None:
    offenders = [
        str(p.relative_to(BACKEND)) for p in (BACKEND / package).rglob("*.py") if _imports_random(p)
    ]
    assert offenders == []
