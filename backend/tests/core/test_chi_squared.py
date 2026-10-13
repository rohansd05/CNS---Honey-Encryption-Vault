"""Tests for ``eval.chi_squared`` (PROJECT-BRIEF.md §11). Owner: T1 — Nidhi.

Run on the committed PCFG models with small ``n``. Held-out files are synthetic (values sampled
from the model), never corpus lines. Biased encoder/decoder wrappers prove each test has power.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from eval import chi_squared
from eval.chi_squared import (
    _used_ints,
    run,
    sample_heldout,
    seed_byte_uniformity,
    seed_int_uniformity,
    template_goodness_of_fit,
)
from honeycore.dte.int_codec import SeedReader, SeedWriter
from honeycore.dte.password_dte import DEFAULT_MODEL_PATH as PASSWORD_MODEL_PATH
from honeycore.dte.password_dte import PCFGPasswordModel
from honeycore.dte.username_dte import DEFAULT_MODEL_PATH as USERNAME_MODEL_PATH
from honeycore.dte.username_dte import PCFGUsernameModel
from honeycore.interfaces import MAX_FIELD_LEN

pytestmark = pytest.mark.skipif(
    not (PASSWORD_MODEL_PATH.exists() and USERNAME_MODEL_PATH.exists()),
    reason="default PCFG models not trained yet (scripts/train_pcfg.py)",
)

RESULT_KEYS = {"test", "n", "chi2", "dof", "p_value"}
N = 300

printable_no_at = st.text(
    alphabet=st.characters(min_codepoint=0x20, max_codepoint=0x7E, blacklist_characters="@"),
    min_size=1,
    max_size=MAX_FIELD_LEN,
)


@pytest.fixture(scope="module")
def password_model() -> PCFGPasswordModel:
    return PCFGPasswordModel.load_default()


@pytest.fixture(scope="module")
def username_model() -> PCFGUsernameModel:
    return PCFGUsernameModel.load_default()


@pytest.fixture(scope="module", params=["password", "username"])
def model(
    request: pytest.FixtureRequest,
    password_model: PCFGPasswordModel,
    username_model: PCFGUsernameModel,
) -> Any:
    return password_model if request.param == "password" else username_model


@pytest.fixture(scope="module")
def values(model: Any) -> list[str]:
    return [model.sample() for _ in range(N)]


def _check(result: dict, test: str, n: int, dof: int | None = None) -> None:
    assert set(result) == RESULT_KEYS
    assert result["test"] == test
    assert result["n"] == n
    assert math.isfinite(result["chi2"]) and result["chi2"] >= 0
    assert 0.0 <= result["p_value"] <= 1.0
    if dof is not None:
        assert result["dof"] == dof
    json.dumps(result)  # plain JSON types only


# ---- biased wrappers (power) ----------------------------------------------------------------


class _Delegate:
    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class BiasedEncoder(_Delegate):
    """A codec bug: every seed int has its top bit cleared (the k*T spread of §7.2 dropped)."""

    def encode(self, value: str) -> bytes:
        seed = self._inner.encode(value)
        return b"".join(
            (int.from_bytes(seed[i : i + 4], "big") & 0x7FFFFFFF).to_bytes(4, "big")
            for i in range(0, len(seed), 4)
        )


class _QuarterReader:
    def __init__(self, reader: SeedReader) -> None:
        self._reader = reader

    @property
    def remaining(self) -> int:
        return self._reader.remaining

    def next(self) -> int:
        return self._reader.next() >> 2


class BiasedDecoder(_Delegate):
    """A decoder bug: ints are shifted right by 2, so only the low cumulative mass is reached."""

    def _decode_block(self, reader: SeedReader) -> str:
        return self._inner._decode_block(_QuarterReader(reader))


# ---- result shape ---------------------------------------------------------------------------


def test_seed_byte_uniformity_shape(model: Any, values: list[str]) -> None:
    _check(seed_byte_uniformity(model, values, N), "seed_byte_uniformity", N, dof=255)


def test_seed_int_uniformity_shape(model: Any, values: list[str]) -> None:
    _check(seed_int_uniformity(model, values, N), "seed_int_uniformity", N, dof=15)


def test_template_goodness_of_fit_shape(model: Any) -> None:
    result = template_goodness_of_fit(model, 2000)
    _check(result, "template_goodness_of_fit", 2000)
    assert 1 <= result["dof"] <= chi_squared.TOP_TEMPLATES


def test_template_goodness_of_fit_is_reproducible_and_fits(model: Any) -> None:
    """Decoding seeded random seeds is deterministic; the real models fit their own decoys."""
    first = template_goodness_of_fit(model, 3000, seed=11)
    assert template_goodness_of_fit(model, 3000, seed=11) == first
    assert first["p_value"] > 0.01


def test_template_goodness_of_fit_small_n_merges_bins(model: Any) -> None:
    large, small = template_goodness_of_fit(model, 5000), template_goodness_of_fit(model, 200)
    _check(small, "template_goodness_of_fit", 200)
    assert 1 <= small["dof"] < large["dof"]


def test_template_goodness_of_fit_rejects_single_bin(password_model: PCFGPasswordModel) -> None:
    with pytest.raises(ValueError, match="too small"):
        template_goodness_of_fit(password_model, 2)


def test_n_counts_only_valid_values(password_model: PCFGPasswordModel) -> None:
    mixed = ["", "ok1", "x" * (MAX_FIELD_LEN + 1), "café", "fine2", "third3"]
    assert seed_byte_uniformity(password_model, mixed, 10)["n"] == 3
    assert seed_int_uniformity(password_model, mixed, 2)["n"] == 2


@pytest.mark.parametrize("bad", [0, -1])
def test_rejects_non_positive_n(password_model: PCFGPasswordModel, bad: int) -> None:
    with pytest.raises(ValueError, match="n"):
        seed_byte_uniformity(password_model, ["abc"], bad)
    with pytest.raises(ValueError, match="n_samples"):
        template_goodness_of_fit(password_model, bad)


def test_rejects_no_valid_values(password_model: PCFGPasswordModel) -> None:
    with pytest.raises(ValueError, match="no valid values"):
        seed_int_uniformity(password_model, ["", "\t"], 5)


# ---- used ints ------------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(printable_no_at)
def test_used_ints_match_encoder_password(password_model: PCFGPasswordModel, pw: str) -> None:
    w = SeedWriter()
    password_model._encode_block(w, pw)
    seed = password_model.encode(pw)
    used = _used_ints(password_model, seed)
    assert len(used) == len(w)
    assert used == [int.from_bytes(seed[4 * i : 4 * i + 4], "big") for i in range(len(used))]


@settings(max_examples=100, deadline=None)
@given(printable_no_at)
def test_used_ints_match_encoder_username(username_model: PCFGUsernameModel, name: str) -> None:
    w = SeedWriter()
    username_model._encode_block(w, name)  # no "@": domain choice is __NONE__
    assert len(_used_ints(username_model, username_model.encode(name))) == 1 + len(w)


# ---- power: biased codecs give p < 0.01 -----------------------------------------------------


def test_biased_encoder_fails_byte_uniformity(model: Any, values: list[str]) -> None:
    assert seed_byte_uniformity(BiasedEncoder(model), values, N)["p_value"] < 0.01


def test_biased_encoder_fails_int_uniformity(model: Any, values: list[str]) -> None:
    assert seed_int_uniformity(BiasedEncoder(model), values, N)["p_value"] < 0.01


def test_biased_decoder_fails_template_fit(model: Any) -> None:
    assert template_goodness_of_fit(BiasedDecoder(model), 2000)["p_value"] < 0.01


# ---- held-out sampling, run(), CLI ----------------------------------------------------------


def _write_tsv(path: Path, rows: list[str]) -> Path:
    path.write_text("".join(f"{r}\n" for r in rows), encoding="utf-8")
    return path


def test_sample_heldout_weights_filters_and_is_reproducible(tmp_path: Path) -> None:
    tsv = _write_tsv(
        tmp_path / "h.tsv",
        ["common\t1000", "rare\t1", "noweight", "bad\tNaNx", "\t5", "x" * 40 + "\t9", ""],
    )
    picks = sample_heldout(tsv, 500, seed=3)
    assert picks == sample_heldout(tsv, 500, seed=3)
    assert set(picks) <= {"common", "rare", "noweight", "bad"}
    assert picks.count("common") > 450


def test_sample_heldout_errors(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        sample_heldout(tmp_path / "missing.tsv", 5)
    with pytest.raises(ValueError, match="no valid held-out values"):
        sample_heldout(_write_tsv(tmp_path / "empty.tsv", ["", "\t3"]), 5)


@pytest.fixture(scope="module")
def heldout_files(
    tmp_path_factory: pytest.TempPathFactory,
    password_model: PCFGPasswordModel,
    username_model: PCFGUsernameModel,
) -> tuple[Path, Path]:
    d = tmp_path_factory.mktemp("heldout")
    pw = _write_tsv(d / "pw.tsv", [f"{password_model.sample()}\t1" for _ in range(200)])
    un = _write_tsv(d / "un.tsv", [f"{username_model.sample()}\t1" for _ in range(200)])
    return pw, un


def _check_report(report: dict, n: int) -> None:
    assert {"n", "seed", "alpha", "interpretation", "password", "username"} <= set(report)
    for kind, model_id in (("password", "pcfg-password-v1"), ("username", "pcfg-username-v1")):
        section = report[kind]
        assert section["model"] == model_id
        _check(section["seed_byte_uniformity"], "seed_byte_uniformity", n, dof=255)
        _check(section["seed_int_uniformity"], "seed_int_uniformity", n, dof=15)
        _check(section["seed_int_uniformity_control"], "seed_int_uniformity_control", n, dof=15)
        _check(section["template_goodness_of_fit"], "template_goodness_of_fit", n)


def test_run_report_is_complete_and_json(
    heldout_files: tuple[Path, Path],
    password_model: PCFGPasswordModel,
    username_model: PCFGUsernameModel,
) -> None:
    report = run(
        *heldout_files, n=150, password_model=password_model, username_model=username_model
    )
    _check_report(report, 150)
    assert json.loads(json.dumps(report)) == report


def test_cli_prints_json(heldout_files: tuple[Path, Path], capsys: pytest.CaptureFixture) -> None:
    pw, un = heldout_files
    argv = ["-n", "100", "--heldout-passwords", str(pw), "--heldout-usernames", str(un)]
    assert chi_squared.main(argv) == 0
    _check_report(json.loads(capsys.readouterr().out), 100)
