"""Tests for the honey-encryption distinguisher (``eval/classifier.py``). Owner: T1 -- Dhruv.

Everything runs on tiny synthetic data (n=200) so the suite stays fast and needs no corpus or
committed model. Two things are checked: the harness produces well-formed scores in ``[0, 1]`` on
indistinguishable-ish data, and -- as a power check -- it *can* separate a deliberately broken
decoy generator (every decoy 32 chars long) with accuracy > 0.9.
"""

from __future__ import annotations

import math

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from eval.classifier import CV_FOLDS, FEATURE_NAMES, features, folds, run, strip_known_domain
from honeycore.dte.password_dte import PCFGPasswordModel
from honeycore.dte.pcfg import train_password_model

# A small but varied synthetic corpus -> a real (if tiny) PCFG model.
_TRAIN_WORDS = [
    "password", "monkey123", "dragon", "qwerty", "letmein", "sunshine1", "football",
    "iloveyou", "princess", "shadow99", "master", "hello123", "welcome1", "abc123",
    "baseball", "superman", "trustno1", "charlie", "summer2020", "winter!", "orange7",
    "ninjaX", "secretA", "purple42", "guitar", "flower9", "banana", "coffee1",
]  # fmt: skip
PRINTABLE = "".join(chr(c) for c in range(0x20, 0x7F))


def _tiny_model() -> PCFGPasswordModel:
    model_dict = train_password_model((w, 10.0) for w in _TRAIN_WORDS)
    return PCFGPasswordModel(model_dict)


def _write_heldout(tmp_path, words: list[str]) -> str:
    path = tmp_path / "heldout.tsv"
    path.write_text("".join(f"{w}\t{10 + i}\n" for i, w in enumerate(words)), encoding="utf-8")
    return str(path)


class _FixedLengthModel:
    """A deliberately broken decoy generator: every sample is 32 identical characters."""

    def sample(self) -> str:
        return "x" * 32


# ---- features ----
def test_features_vector_shape_and_values() -> None:
    model = _tiny_model()
    vec = features("Monkey123", model)
    assert len(vec) == len(FEATURE_NAMES) == 12
    assert all(isinstance(v, float) and math.isfinite(v) for v in vec)
    # length, lower, upper, digit, symbol
    assert vec[0] == 9.0
    assert vec[1] == 5.0  # "onkey"
    assert vec[2] == 1.0  # "M"
    assert vec[3] == 3.0  # "123"
    assert vec[4] == 0.0  # no symbols
    assert vec[5] == 2.0  # segments: "Monkey" (L6) + "123" (D3)
    assert vec[8] == 3.0  # longest digit run "123"
    assert vec[9] == 1.0  # starts with capital
    assert vec[10] == 1.0  # ends with digit


def test_features_segments_and_entropy() -> None:
    assert features("monkey12!")[5] == 3.0  # L D S -> 3 segments
    assert features("aaaa")[11] == 0.0  # single symbol -> zero entropy
    assert features("ab")[11] == 1.0  # two equally likely chars -> 1 bit
    # starts_with_capital / ends_with_digit flags
    assert features("abc")[9] == 0.0
    assert features("abc")[10] == 0.0


def test_features_work_without_a_model() -> None:
    vec = features("hunter2")
    assert len(vec) == 12
    assert vec[6] == 0.0 and vec[7] == 0.0  # model-based features default to 0.0


@settings(max_examples=50, deadline=None)
@given(st.text(alphabet=PRINTABLE, min_size=1, max_size=32))
def test_features_always_finite_fixed_width(value: str) -> None:
    vec = features(value, _MODEL)
    assert len(vec) == 12
    assert all(math.isfinite(v) for v in vec)


# ---- run ----
def test_run_output_keys_and_accuracy_in_range(tmp_path) -> None:
    model = _tiny_model()
    heldout = _write_heldout(tmp_path, _TRAIN_WORDS)
    report = run(model, heldout, n=200, seed=7)

    assert report["n"] == 200
    assert report["interpretation"] == "≈0.5 = indistinguishable"
    for key in ("logreg", "random_forest"):
        scores = report[key]
        assert set(scores) == {"accuracy_mean", "accuracy_std", "roc_auc_mean"}
        assert 0.0 <= scores["accuracy_mean"] <= 1.0
        assert 0.0 <= scores["roc_auc_mean"] <= 1.0
        assert scores["accuracy_std"] >= 0.0


def test_run_grouped_and_distinct_protocols(tmp_path) -> None:
    model = _tiny_model()
    report = run(model, _write_heldout(tmp_path, _TRAIN_WORDS), n=200, seed=7)
    grouped, distinct = report["grouped"], report["distinct"]
    assert grouped["n"] == 200 and 1 <= grouped["distinct_strings"] <= 400
    assert distinct["n"] == min(distinct["distinct_real"], distinct["distinct_decoy"])
    assert distinct["distinct_real"] <= len(_TRAIN_WORDS)
    for block in (grouped, distinct):
        for key in ("logreg", "random_forest"):
            assert 0.0 <= block[key]["accuracy_mean"] <= 1.0
            assert 0.0 <= block[key]["roc_auc_mean"] <= 1.0


def test_grouped_folds_never_share_a_string() -> None:
    # Heavy repeats, and some strings carry both labels (a real that the model also decoys).
    values = [f"pw{i % 37}" for i in range(500)] + [f"pw{i % 23}x" for i in range(300)]
    values += ["pw1"] * 40
    y = np.array([1] * 500 + [0] * 340)
    splits = folds(values, y, seed=7, grouped=True)
    assert len(splits) == CV_FOLDS
    tested = np.concatenate([test for _, test in splits])
    assert sorted(tested) == list(range(len(values)))  # every row tested exactly once
    for train, test in splits:
        assert not {values[i] for i in train} & {values[i] for i in test}
        assert set(y[test]) == {0, 1}  # still stratified: both classes in every test fold
    # The plain protocol does leak strings across folds -- the reason grouped CV exists.
    plain = folds(values, y, seed=7)
    assert any({values[i] for i in tr} & {values[i] for i in te} for tr, te in plain)


def test_run_detects_distinguishable_decoys(tmp_path) -> None:
    # Real held-out passwords are short/varied; every decoy is 32 chars -> trivially separable.
    heldout = _write_heldout(tmp_path, _TRAIN_WORDS)
    report = run(_FixedLengthModel(), heldout, n=200, seed=7)
    assert report["logreg"]["accuracy_mean"] > 0.9
    assert report["random_forest"]["accuracy_mean"] > 0.9
    assert report["logreg"]["roc_auc_mean"] > 0.9
    # One decoy string cannot fill 5 grouped folds: both extra protocols are skipped, not NaN.
    assert "skipped" in report["grouped"] and "skipped" in report["distinct"]
    assert report["distinct"]["distinct_decoy"] == 1


def test_strip_known_domain_strips_only_known_domains() -> None:
    known = {"gmail.com", "yahoo.com"}
    assert strip_known_domain("john@gmail.com", known) == "john"
    assert strip_known_domain("a.b_c@yahoo.com", known) == "a.b_c"
    assert strip_known_domain("john@corp.example", known) == "john@corp.example"  # unknown
    assert strip_known_domain("john", known) == "john"  # bare username
    assert strip_known_domain("a@b@gmail.com", known) == "a@b@gmail.com"  # two @: not an email
    assert strip_known_domain("john@GMAIL.COM", known) == "john@GMAIL.COM"  # exact match only


class _EmailDecoyModel:
    """Decoys = training words, every other one with ``@gmail.com`` appended."""

    def __init__(self) -> None:
        self._i = 0

    def sample(self) -> str:
        self._i += 1
        word = _TRAIN_WORDS[self._i % len(_TRAIN_WORDS)]
        return f"{word}@gmail.com" if self._i % 2 else word


def test_run_transform_applies_to_both_classes(tmp_path) -> None:
    heldout = _write_heldout(tmp_path, [*_TRAIN_WORDS, "mate@gmail.com"])
    plain = run(_EmailDecoyModel(), heldout, n=200, seed=7)
    assert "transformed" not in plain
    stripped = run(
        _EmailDecoyModel(),
        heldout,
        n=200,
        seed=7,
        transform=lambda v: strip_known_domain(v, {"gmail.com"}),
    )
    assert stripped["transformed"]["decoy"] == 100  # every other decoy carried the suffix
    assert 0 < stripped["transformed"]["real"] < 200  # only the one real email was stripped
    for block in (stripped, stripped["grouped"], stripped["distinct"]):
        for key in ("logreg", "random_forest"):
            assert 0.0 <= block[key]["accuracy_mean"] <= 1.0


_MODEL = _tiny_model()
