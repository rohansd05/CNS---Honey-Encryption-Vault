"""Tests for ``eval.run_all`` (PROJECT-BRIEF.md §11). Owner: T1 -- Dhruv.

One ``--quick`` run on the committed PCFG models feeds most tests. Held-out files are synthetic
(values sampled from the models), never corpus lines, so no ``data/`` folder is needed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from eval import run_all
from eval.run_all import describe_template, main
from honeycore.dte.entry_dte import PCFGEntryDTE
from honeycore.dte.password_dte import DEFAULT_MODEL_PATH as PASSWORD_MODEL_PATH
from honeycore.dte.password_dte import PCFGPasswordModel
from honeycore.dte.username_dte import DEFAULT_MODEL_PATH as USERNAME_MODEL_PATH
from honeycore.dte.username_dte import PCFGUsernameModel

pytestmark = pytest.mark.skipif(
    not (PASSWORD_MODEL_PATH.exists() and USERNAME_MODEL_PATH.exists()),
    reason="default PCFG models not trained yet (scripts/train_pcfg.py)",
)

TASK_KEYS = {"round_trip", "chi_squared", "classifier", "attack", "kdf", "meta"}
PAGE_KEYS = {
    "timestamp",
    "version",
    "dataset",
    "round_trip",
    "chi_squared",
    "distinguisher",
    "template_frequencies",
    "performance",
}


def _write_tsv(path: Path, values: list[str]) -> Path:
    path.write_text("".join(f"{v}\t{1.0 / (i + 1)}\n" for i, v in enumerate(values)), "utf-8")
    return path


def _strict_load(path: Path) -> dict[str, Any]:
    def reject(token: str) -> Any:
        raise ValueError(f"non-standard JSON constant {token}")

    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)


@pytest.fixture(scope="module")
def heldout(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Synthetic held-out password + username files (model samples, never corpus lines)."""
    root = tmp_path_factory.mktemp("heldout")
    pw = PCFGPasswordModel.load_default()
    un = PCFGUsernameModel.load_default()
    return (
        _write_tsv(root / "pw.tsv", [pw.sample() for _ in range(400)]),
        _write_tsv(root / "un.tsv", [un.sample() for _ in range(400)]),
    )


@pytest.fixture(scope="module")
def quick_results(
    tmp_path_factory: pytest.TempPathFactory, heldout: tuple[Path, Path]
) -> dict[str, Any]:
    out = tmp_path_factory.mktemp("results") / "latest.json"
    pw, un = heldout
    argv = ["--quick", "--out", str(out), "--heldout-passwords", str(pw)]
    assert main([*argv, "--heldout-usernames", str(un)]) == 0
    return _strict_load(out)


CLASSIFIERS = {"logreg", "random_forest"}


def test_quick_has_all_top_level_keys(quick_results: dict[str, Any]) -> None:
    assert TASK_KEYS | PAGE_KEYS <= set(quick_results)
    assert quick_results["meta"]["mode"] == "quick"
    # New keys only: grouped-CV and distinct-strings protocols next to the existing ones.
    for kind in ("password", "username"):
        clf = quick_results["classifier"][kind]
        assert {"n", "interpretation", "grouped", "distinct"} | CLASSIFIERS <= set(clf)
        assert CLASSIFIERS <= set(clf["grouped"]) and CLASSIFIERS <= set(clf["distinct"])
    dist = quick_results["distinguisher"]
    assert {"metrics", "per_classifier", "metrics_classifier", "conclusion"} <= set(dist)
    for key in ("per_classifier", "grouped_results", "distinct_results"):
        assert set(dist[key]) == CLASSIFIERS
        for score in dist[key].values():
            assert 0.0 <= score["accuracy_mean"] <= 1.0


def test_quick_matches_evaluation_page_shape(quick_results: dict[str, Any]) -> None:
    r = quick_results
    rt = r["round_trip"]
    assert rt["success_rate"] == 1.0
    assert rt["decode_totality"]["failed_decodes"] == 0
    assert isinstance(rt["trials"], int) and isinstance(rt["exact_match_count"], int)
    for key in ("seed_uniformity", "template_goodness_of_fit"):
        chi = r["chi_squared"][key]
        assert 0.0 <= chi["p_value"] <= 1.0
        assert isinstance(chi["statistic"], float) and isinstance(chi["degrees_of_freedom"], int)
        assert chi["null_hypothesis_accepted"] == (chi["p_value"] > 0.05)
    metrics = r["distinguisher"]["metrics"]
    for key in ("accuracy", "roc_auc", "precision", "recall"):
        assert 0.0 <= metrics[key] <= 1.0
    assert r["distinguisher"]["target_accuracy"] == 0.6
    assert len(r["template_frequencies"]) == run_all.TOP_TEMPLATE_ROWS
    assert {"template", "model_frequency", "decoded_frequency", "description"} <= set(
        r["template_frequencies"][0]
    )
    perf = r["performance"]
    assert perf["unlock_p50_ms"] <= perf["unlock_p95_ms"]
    assert perf["target_p95_ms"] == 1500


def test_quick_attack_and_kdf(quick_results: dict[str, Any]) -> None:
    attack = quick_results["attack"]
    assert attack["conventional"]["cracked"] is True
    assert attack["conventional"]["guess_index"] == attack["real_guess_index"]
    assert attack["conventional"]["recovered_entries_are_real"] is True
    assert attack["honey"]["guesses_tried"] == attack["guesses"]
    assert attack["honey"]["correct_password_recovers_real_entries"] is True
    assert attack["honey"]["sample_fields_well_formed"] is True
    assert set(quick_results["kdf"]) == {"default", "server_lite", "demo"}


def test_quick_writes_old_and_new_keys(quick_results: dict[str, Any]) -> None:
    # Old keys (the frontend reads them) stay; the v3 keys sit beside them.
    assert TASK_KEYS | PAGE_KEYS | {"timing"} <= set(quick_results)
    un = quick_results["classifier"]["username"]
    assert {"grouped", "distinct", "without_domain"} | CLASSIFIERS <= set(un)
    wd = un["without_domain"]
    assert {"n", "grouped", "distinct", "transformed", "note"} | CLASSIFIERS <= set(wd)
    assert CLASSIFIERS <= set(wd["grouped"]) and CLASSIFIERS <= set(wd["distinct"])
    # The synthetic held-out usernames are model samples, so both classes carry domains.
    assert wd["transformed"]["real"] > 0 and wd["transformed"]["decoy"] > 0
    assert quick_results["meta"]["config"]["timing_n"] == run_all.QUICK.timing_n


def test_quick_timing_block(quick_results: dict[str, Any]) -> None:
    timing = quick_results["timing"]
    assert timing["n_per_class"] == run_all.QUICK.timing_n
    assert set(timing["profiles"]) == {"default", "server_lite", "demo"}
    for t in timing["profiles"].values():
        assert 0.0 <= t["ks_p_value"] <= 1.0
        assert 0.0 <= t["control_ks_p_value"] <= 1.0
        assert 0.0 <= t["ks_statistic"] <= 1.0
        assert t["same_distribution"] == (t["ks_p_value"] > timing["alpha"])
        for side in ("right_ms", "wrong_ms"):
            assert 0.0 < t[side]["p50"] <= t[side]["p95"]
    decode = timing["decode_only_us"]
    assert 0.0 <= decode["ks_p_value"] <= 1.0
    assert decode["real_seeds"]["p50"] > 0.0 and decode["random_seeds"]["p50"] > 0.0


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_meta_records_model_and_heldout_sha256(
    quick_results: dict[str, Any], heldout: tuple[Path, Path], tmp_path: Path
) -> None:
    meta = quick_results["meta"]
    assert meta["model_sha256"] == {
        "password_model": _digest(PASSWORD_MODEL_PATH),
        "username_model": _digest(USERNAME_MODEL_PATH),
    }
    assert meta["heldout_sha256"] == {
        "passwords": _digest(heldout[0]),
        "usernames": _digest(heldout[1]),
    }
    assert run_all._sha256(tmp_path / "missing.tsv") is None


def test_results_carry_no_plaintext_or_guesses(quick_results: dict[str, Any]) -> None:
    text = json.dumps(quick_results)
    assert "demo-" not in text  # the per-run attack master password prefix
    for entry in run_all.SAMPLE_ENTRIES:
        assert entry.password not in text
    assert "samples" not in quick_results["attack"]["honey"]


def test_missing_username_heldout_still_valid(tmp_path: Path, heldout: tuple[Path, Path]) -> None:
    core = run_all._honeycore()
    missing = tmp_path / "nope.tsv"
    chi = run_all.run_chi_squared(core, heldout[0], missing, n=300, seed=7)
    assert "skipped" in chi["username"]
    assert 0.0 <= chi["username"]["template_goodness_of_fit"]["p_value"] <= 1.0
    rt = run_all.round_trip(core, heldout[0], missing, run_all.QUICK, seed=7)
    assert rt["usernames"]["source"].startswith("model_samples")
    assert rt["success_rate"] == 1.0
    json.dumps(chi, allow_nan=False)


def test_missing_password_heldout_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        run_all.build_results(quick=True, heldout_passwords=tmp_path / "nope.tsv")


def test_uses_real_pcfg_entry_dte(quick_results: dict[str, Any]) -> None:
    core = run_all._honeycore()
    assert isinstance(core.entry_dte, PCFGEntryDTE)
    assert core.username_model is core.entry_dte.username_model
    assert core.password_model is core.entry_dte.password_model
    assert quick_results["meta"]["entry_dte_impl"] == "honeycore.dte.entry_dte.PCFGEntryDTE"
    assert quick_results["round_trip"]["usernames"]["source"] == "heldout"


def test_describe_template() -> None:
    assert describe_template("L6D2") == "6 letters + 2 digits"
    assert describe_template("L8S1D1") == "8 letters + 1 symbol + 1 digit"
