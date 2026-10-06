"""Tests for the honey-encryption distinguisher (``eval/classifier.py``). Owner: T1 -- Dhruv.

Everything runs on tiny synthetic data (n=200) so the suite stays fast and needs no corpus or
committed model. Two things are checked: the harness produces well-formed scores in ``[0, 1]`` on
indistinguishable-ish data, and -- as a power check -- it *can* separate a deliberately broken
decoy generator (every decoy 32 chars long) with accuracy > 0.9.
"""

from __future__ import annotations

import math

from hypothesis import given, settings
from hypothesis import strategies as st

from eval.classifier import FEATURE_NAMES, features, run
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


def test_run_detects_distinguishable_decoys(tmp_path) -> None:
    # Real held-out passwords are short/varied; every decoy is 32 chars -> trivially separable.
    heldout = _write_heldout(tmp_path, _TRAIN_WORDS)
    report = run(_FixedLengthModel(), heldout, n=200, seed=7)
    assert report["logreg"]["accuracy_mean"] > 0.9
    assert report["random_forest"]["accuracy_mean"] > 0.9
    assert report["logreg"]["roc_auc_mean"] > 0.9


_MODEL = _tiny_model()
