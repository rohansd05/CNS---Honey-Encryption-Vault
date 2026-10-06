"""Distinguisher: can a classifier tell real held-out credentials from DTE decoys? (§11).

Owner: T1 -- Dhruv. Phase 2.

Honey encryption only works if a decoy vault is *indistinguishable* from the real one. This
module measures that directly: it trains supervised classifiers to separate real held-out
passwords (never seen in training, ``pcfg.is_heldout``) from passwords sampled by the DTE model,
and reports their cross-validated accuracy. **Accuracy near 0.5 means the model's decoys are
indistinguishable from real passwords** (the goal, PROJECT-BRIEF.md §11: target <= 0.60); accuracy
near 1.0 would mean the DTE leaks.

Each credential becomes a small, interpretable feature vector (:func:`features`); real and decoy
sets of equal size are scored with 5-fold stratified cross-validation of a standardised logistic
regression and a random forest. The same machinery runs at the username level when a held-out
username set and model are available. ``python -m eval.classifier`` prints the report as JSON.

This is evaluation code (not ``honeycore`` / ``app``), so it may use ``numpy`` randomness with a
fixed seed for reproducibility; it never touches master passwords or keys.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from honeycore.dte.pcfg import parse, template

REPO = Path(__file__).resolve().parents[2]
DEFAULT_HELDOUT_PASSWORDS = REPO / "data" / "processed" / "heldout_passwords.tsv"
DEFAULT_HELDOUT_USERNAMES = REPO / "data" / "processed" / "heldout_usernames.tsv"

RF_TREES = 200
CV_FOLDS = 5
INTERPRETATION = "≈0.5 = indistinguishable"

FEATURE_NAMES: tuple[str, ...] = (
    "length",
    "n_lower",
    "n_upper",
    "n_digit",
    "n_symbol",
    "n_segments",
    "template_logprob",
    "mean_char_unigram_logprob",
    "longest_digit_run",
    "starts_with_capital",
    "ends_with_digit",
    "shannon_entropy",
)


# ---------------------------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------------------------
def _longest_digit_run(text: str) -> int:
    """Length of the longest run of consecutive ASCII digits in ``text``."""
    best = run = 0
    for ch in text:
        run = run + 1 if ch.isdigit() else 0
        best = max(best, run)
    return best


def _shannon_entropy(text: str) -> float:
    """Shannon entropy (bits) of ``text``'s character distribution; 0 for the empty string."""
    if not text:
        return 0.0
    n = len(text)
    return -sum((c / n) * math.log2(c / n) for c in Counter(text).values())


def _model_distributions(model: Any) -> tuple[Any, Any]:
    """Pull the template and ANY-class unigram distributions out of a PCFG model, if present.

    Read defensively: any object without the v1 PCFG internals (e.g. a stub or a test double)
    simply yields ``(None, None)``, and the two model-based features fall back to ``0.0`` so the
    feature vector keeps a fixed width for every input.
    """
    templates = getattr(model, "_templates", None)
    unigrams = getattr(model, "_unigrams", None)
    any_unigram = unigrams.get("ANY") if isinstance(unigrams, dict) else None
    return templates, any_unigram


def _template_logprob(templates: Any, password: str) -> float:
    """Natural log P(template) under the model; a small floor for a template it never saw."""
    if templates is None or not password:
        return 0.0
    try:
        index = templates.index_of(template(password))
    except KeyError:
        return math.log(1.0 / (templates.total + 1))
    return math.log(templates.probability(index))


def _mean_char_unigram_logprob(any_unigram: Any, password: str) -> float:
    """Mean natural log P(char) under the model's ANY-class unigram distribution."""
    if any_unigram is None or not password:
        return 0.0
    total = 0.0
    counted = 0
    for ch in password:
        try:
            index = any_unigram.index_of(ch)
        except KeyError:
            continue
        total += math.log(any_unigram.probability(index))
        counted += 1
    return total / counted if counted else 0.0


def features(password: str, model: Any = None) -> list[float]:
    """Return the fixed-width feature vector for ``password`` (order = :data:`FEATURE_NAMES`).

    ``model`` is an optional PCFG field model (e.g. ``PCFGPasswordModel``); when given, the
    ``template_logprob`` and ``mean_char_unigram_logprob`` features are scored against it,
    otherwise they are ``0.0``.
    """
    length = len(password)
    n_lower = sum(1 for c in password if c.islower())
    n_upper = sum(1 for c in password if c.isupper())
    n_digit = sum(1 for c in password if c.isdigit())
    n_symbol = sum(1 for c in password if not c.isalnum())
    n_segments = len(parse(password)) if password else 0
    templates, any_unigram = _model_distributions(model)
    return [
        float(length),
        float(n_lower),
        float(n_upper),
        float(n_digit),
        float(n_symbol),
        float(n_segments),
        _template_logprob(templates, password),
        _mean_char_unigram_logprob(any_unigram, password),
        float(_longest_digit_run(password)),
        1.0 if password[:1].isupper() else 0.0,
        1.0 if password[-1:].isdigit() else 0.0,
        _shannon_entropy(password),
    ]


# ---------------------------------------------------------------------------------------------
# Data + classifiers
# ---------------------------------------------------------------------------------------------
def _sample_heldout(path: str | Path, n: int, seed: int) -> list[str]:
    """Sample ``n`` held-out values (with replacement) from a ``value<TAB>weight`` TSV, by weight.

    Lines are ``value`` or ``value<TAB>weight``; a missing/invalid weight counts as 1. Sampling
    uses a seeded NumPy generator so a given ``seed`` always yields the same real set.
    """
    values: list[str] = []
    weights: list[float] = []
    with Path(path).open(encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line:
                continue
            value, _, weight_text = line.partition("\t")
            if not value:
                continue
            try:
                weight = float(weight_text) if weight_text else 1.0
            except ValueError:
                weight = 1.0
            values.append(value)
            weights.append(max(weight, 0.0))
    if not values:
        raise ValueError(f"no held-out values in {path}")
    w = np.asarray(weights, dtype=float)
    if w.sum() <= 0:
        w = np.ones(len(values))
    rng = np.random.default_rng(seed)
    picks = rng.choice(len(values), size=n, p=w / w.sum())
    return [values[i] for i in picks]


def _classifiers(seed: int) -> list[tuple[str, Any]]:
    """The two distinguishers: a standardised logistic regression and a random forest."""
    logreg = Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression(max_iter=1000))])
    forest = RandomForestClassifier(n_estimators=RF_TREES, random_state=seed)
    return [("logreg", logreg), ("random_forest", forest)]


def _score(clf: Any, x: np.ndarray, y: np.ndarray, seed: int) -> dict[str, float]:
    """5-fold stratified CV accuracy (mean/std) and ROC-AUC (mean) for one classifier."""
    skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=seed)
    cv = cross_validate(clf, x, y, cv=skf, scoring=("accuracy", "roc_auc"))
    return {
        "accuracy_mean": float(cv["test_accuracy"].mean()),
        "accuracy_std": float(cv["test_accuracy"].std()),
        "roc_auc_mean": float(cv["test_roc_auc"].mean()),
    }


def run(model: Any, heldout_path: str | Path, n: int = 10000, seed: int = 7) -> dict[str, Any]:
    """Score how distinguishable ``model``'s decoys are from real held-out values.

    Builds ``n`` real values (sampled by weight from ``heldout_path``) and ``n`` decoys
    (``model.sample()``), extracts :func:`features` for each, and runs 5-fold stratified CV of
    both classifiers. Returns ``n``, per-classifier accuracy mean/std and ROC-AUC mean, and an
    interpretation note. Accuracy near 0.5 means the decoys are indistinguishable.
    """
    reals = _sample_heldout(heldout_path, n, seed)
    decoys = [model.sample() for _ in range(n)]
    x = np.array([features(v, model) for v in (*reals, *decoys)], dtype=float)
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    y = np.array([1] * len(reals) + [0] * len(decoys))

    report: dict[str, Any] = {"n": len(reals)}
    for name, clf in _classifiers(seed):
        report[name] = _score(clf, x, y, seed)
    report["interpretation"] = INTERPRETATION
    return report


# ---------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------
def _load_password_model(path: Path | None) -> Any:
    """Load the PCFG password model (default committed model unless ``path`` is given)."""
    from honeycore.dte.password_dte import PCFGPasswordModel

    return PCFGPasswordModel.from_file(path) if path else PCFGPasswordModel.load_default()


def _load_username_model() -> Any | None:
    """Return a PCFG username model if the track has landed one, else ``None``."""
    try:
        from honeycore.dte.username_dte import PCFGUsernameModel
    except (ImportError, AttributeError):
        return None
    return PCFGUsernameModel()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: run the distinguisher(s) and print the report as JSON."""
    ap = argparse.ArgumentParser(description="Honey-encryption distinguisher (§11).")
    ap.add_argument("-n", "--n", type=int, default=10000, help="samples per class")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--model", type=Path, default=None, help="password model .json.gz (optional)")
    ap.add_argument("--heldout", type=Path, default=DEFAULT_HELDOUT_PASSWORDS)
    ap.add_argument("--username-heldout", type=Path, default=DEFAULT_HELDOUT_USERNAMES)
    args = ap.parse_args(argv)

    report: dict[str, Any] = {
        "password": run(_load_password_model(args.model), args.heldout, n=args.n, seed=args.seed)
    }
    username_model = _load_username_model()
    if args.username_heldout.exists() and username_model is not None:
        report["username"] = run(username_model, args.username_heldout, n=args.n, seed=args.seed)
    # Encode to UTF-8 explicitly: the report contains "≈", which a cp1252 console cannot print.
    out = json.dumps(report, indent=2, ensure_ascii=False)
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        buffer.write(out.encode("utf-8") + b"\n")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
