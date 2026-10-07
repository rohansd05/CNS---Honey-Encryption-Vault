"""Chi-squared tests of the PCFG DTEs (PROJECT-BRIEF.md §11 "Chi-squared").

Owner: T1 — Nidhi. Phase 2.

Honey encryption needs two things from a DTE, and each has a test here:

(a) **Seeds of real values look uniform.** An attacker who decrypts with a wrong key sees a
    uniformly random seed; if seeds of *real* values were not uniform, the real vault would stand
    out. We encode held-out real values (never trained on, ``pcfg.is_heldout``) and test
    - ``seed_byte_uniformity``: every byte of every seed, 256 bins;
    - ``seed_int_uniformity``: the top 4 bits of each *used* 32-bit int, 16 bins (the random
      padding ints are excluded, so this is sensitive to integer-codec bias, §7.2).
    A small p here has two possible causes: codec bias, or real values whose frequencies differ
    from the model's probabilities (imperfect model fit). The report separates them with a
    control, ``seed_int_uniformity_control``: the same int test on values *sampled from the
    model*, which isolates the codec (it should pass whatever the model fit).
(b) **Decoys follow the model.** ``template_goodness_of_fit`` decodes random seeds and compares
    the observed template counts with the model's template probabilities (top 50 templates +
    "other"; bins with expected count < 5 are merged into "other").

Every test returns ``{"test", "n", "chi2", "dof", "p_value"}``. **p > 0.05 means no evidence of
a deviation** at the 5% level; a tiny p means the test detected one. With large ``n`` even a
small model/data mismatch gives a small p for (a) — report it honestly (§11).

Both the password and the username model are tested. ``run`` returns a JSON-serialisable dict;
``python -m eval.chi_squared`` prints it. Evaluation code (not ``honeycore``/``app``): sampling
uses a seeded NumPy generator for reproducibility; it never touches master passwords or keys.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import chisquare

from honeycore.dte.int_codec import SeedReader
from honeycore.dte.pcfg import is_valid_field, template
from honeycore.interfaces import INT_BYTES

REPO = Path(__file__).resolve().parents[2]
DEFAULT_HELDOUT_PASSWORDS = REPO / "data" / "processed" / "heldout_passwords.tsv"
DEFAULT_HELDOUT_USERNAMES = REPO / "data" / "processed" / "heldout_usernames.tsv"

ALPHA = 0.05
TOP_TEMPLATES = 50
MIN_EXPECTED = 5.0
INT_TOP_BITS = 4
OTHER = "other"
INTERPRETATION = "p > 0.05: no evidence of deviation (uniform seeds / decoys follow the model)"


def _result(test: str, n: int, f_obs: Iterable[float], f_exp: Iterable[float] | None) -> dict:
    """Run ``scipy.stats.chisquare`` and package the result as plain JSON types."""
    obs = np.asarray(list(f_obs), dtype=float)
    exp = None if f_exp is None else np.asarray(list(f_exp), dtype=float)
    stat, p = chisquare(obs, exp)
    return {
        "test": test,
        "n": int(n),
        "chi2": float(stat),
        "dof": len(obs) - 1,
        "p_value": float(p),
    }


def _take_valid(values: Iterable[str], n: int) -> list[str]:
    """The first ``n`` values that meet the §7.1 field limits."""
    if n < 1:
        raise ValueError("n must be >= 1")
    out: list[str] = []
    for v in values:
        if is_valid_field(v):
            out.append(v)
            if len(out) == n:
                break
    if not out:
        raise ValueError("no valid values to encode")
    return out


def _used_ints(model: Any, seed: bytes) -> list[int]:
    """The ints of ``seed`` that the DTE actually consumes (excludes the random padding).

    ``decode(encode(x))`` reads exactly the ints ``encode`` wrote, so replaying the decode
    with a ``SeedReader`` tells how many there are. Username seeds start with the
    email-domain choice, then the shared PCFG block (§7.4).
    """
    reader = SeedReader(seed)
    if model.kind == "username":
        reader.next()
    model._decode_block(reader)
    used = len(seed) // INT_BYTES - reader.remaining
    return [int.from_bytes(seed[i : i + INT_BYTES], "big") for i in range(0, used * INT_BYTES, 4)]


# ---- (a) seed uniformity --------------------------------------------------------------------


def seed_byte_uniformity(model: Any, values: Iterable[str], n: int) -> dict:
    """Chi-squared of all seed bytes (256 bins) from encoding up to ``n`` valid ``values``.

    ``n`` in the result is the number of values encoded. Raises ``ValueError`` if none is valid.
    """
    chosen = _take_valid(values, n)
    data = b"".join(model.encode(v) for v in chosen)
    counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256)
    return _result("seed_byte_uniformity", len(chosen), counts, None)


def seed_int_uniformity(model: Any, values: Iterable[str], n: int) -> dict:
    """Chi-squared of the top 4 bits of each USED 32-bit seed int (16 bins).

    Padding ints are uniformly random by construction, so only the ints the codec chose are
    counted: this catches integer-codec bias (§7.2) that the byte test would dilute.
    """
    chosen = _take_valid(values, n)
    ints: list[int] = []
    for v in chosen:
        ints.extend(_used_ints(model, model.encode(v)))
    top = np.asarray(ints, dtype=np.uint64) >> np.uint64(32 - INT_TOP_BITS)
    counts = np.bincount(top.astype(np.int64), minlength=2**INT_TOP_BITS)
    return _result("seed_int_uniformity", len(chosen), counts, None)


# ---- (b) template goodness of fit -----------------------------------------------------------


def _decode_pcfg_block(model: Any, seed: bytes) -> str:
    """Decode the PCFG block of ``seed`` (for usernames: after the email-domain choice).

    Templates are compared on the block output: the username domain suffix and its truncation
    of the local part are not part of the PCFG template distribution.
    """
    reader = SeedReader(seed)
    if model.kind == "username":
        reader.next()
    return model._decode_block(reader)


def template_goodness_of_fit(model: Any, n_samples: int, seed: int = 7) -> dict:
    """Observed template counts of ``n_samples`` decoded random seeds vs the model.

    Expected count of template ``t`` = ``n * P(pcfg path) * P(t)``. The top
    ``TOP_TEMPLATES`` templates by model probability get their own bin; the remaining mass
    (other templates and the char-by-char fallback path) is "other". Bins with expected count
    below ``MIN_EXPECTED`` are merged into "other"; if "other" itself ends below it, it is
    merged into the smallest kept bin. Raises ``ValueError`` if ``n_samples < 1`` or too
    small to leave at least two bins.
    """
    if n_samples < 1:
        raise ValueError("n_samples must be >= 1")
    rng = np.random.default_rng(seed)
    observed = Counter(
        template(_decode_pcfg_block(model, rng.bytes(model.seed_len))) for _ in range(n_samples)
    )

    p_pcfg = model._path.probability(model._pcfg_idx)
    dist = model._templates
    ranked = sorted(range(len(dist)), key=dist.weight, reverse=True)[:TOP_TEMPLATES]
    bins: dict[str, float] = {}
    for i in ranked:
        expected = n_samples * p_pcfg * dist.probability(i)
        if expected >= MIN_EXPECTED:
            bins[dist.symbols[i]] = expected
    f_obs = [float(observed[t]) for t in bins]
    f_exp = list(bins.values())
    other_obs = n_samples - sum(f_obs)
    other_exp = n_samples - sum(f_exp)
    if other_exp >= MIN_EXPECTED or not f_exp:
        f_obs.append(other_obs)
        f_exp.append(other_exp)
    else:
        j = int(np.argmin(f_exp))
        f_obs[j] += other_obs
        f_exp[j] += other_exp
    if len(f_exp) < 2:
        raise ValueError(
            f"n_samples={n_samples} too small: no template has expected count >= {MIN_EXPECTED}"
        )
    return _result("template_goodness_of_fit", n_samples, f_obs, f_exp)


# ---- driver ---------------------------------------------------------------------------------


def sample_heldout(path: str | Path, n: int, seed: int = 7) -> list[str]:
    """Sample ``n`` valid held-out values (with replacement) by weight from a TSV.

    Lines are ``value`` or ``value<TAB>weight`` (missing/invalid weight = 1), as written by
    ``scripts/train_pcfg.py``. Weighted sampling reproduces the real-world frequency of each
    value. Raises ``FileNotFoundError`` / ``ValueError`` if the file is missing / has none.
    """
    values: list[str] = []
    weights: list[float] = []
    with Path(path).open(encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            value, _, weight_text = raw.rstrip("\r\n").partition("\t")
            if not is_valid_field(value):
                continue
            try:
                weight = float(weight_text) if weight_text else 1.0
            except ValueError:
                weight = 1.0
            values.append(value)
            weights.append(max(weight, 0.0))
    if not values:
        raise ValueError(f"no valid held-out values in {path}")
    w = np.asarray(weights, dtype=float)
    if w.sum() <= 0:
        w = np.ones(len(values))
    picks = np.random.default_rng(seed).choice(len(values), size=n, p=w / w.sum())
    return [values[i] for i in picks]


def evaluate_model(model: Any, heldout: list[str], n: int, seed: int = 7) -> dict[str, Any]:
    """All three tests for one model (``heldout`` = real values to encode), plus the codec control.

    ``seed_int_uniformity_control`` encodes ``n`` values sampled from the model itself, so its
    ints are uniform unless the integer codec is biased (see the module docstring).
    """
    control = seed_int_uniformity(model, (model.sample() for _ in range(n)), n)
    control["test"] = "seed_int_uniformity_control"
    return {
        "model": model.model_id,
        "seed_byte_uniformity": seed_byte_uniformity(model, heldout, n),
        "seed_int_uniformity": seed_int_uniformity(model, heldout, n),
        "seed_int_uniformity_control": control,
        "template_goodness_of_fit": template_goodness_of_fit(model, n, seed=seed),
    }


def run(
    heldout_passwords_path: str | Path = DEFAULT_HELDOUT_PASSWORDS,
    heldout_usernames_path: str | Path = DEFAULT_HELDOUT_USERNAMES,
    n: int = 20000,
    seed: int = 7,
    *,
    password_model: Any = None,
    username_model: Any = None,
) -> dict[str, Any]:
    """Run every chi-squared test on the password and username models (JSON-serialisable).

    Models default to the committed ``pcfg_*_v1.json.gz``. ``n`` values are sampled from each
    held-out file and ``n`` random seeds are decoded per model.
    """
    if password_model is None:
        from honeycore.dte.password_dte import PCFGPasswordModel

        password_model = PCFGPasswordModel.load_default()
    if username_model is None:
        from honeycore.dte.username_dte import PCFGUsernameModel

        username_model = PCFGUsernameModel.load_default()
    return {
        "n": n,
        "seed": seed,
        "alpha": ALPHA,
        "interpretation": INTERPRETATION,
        "password": evaluate_model(
            password_model, sample_heldout(heldout_passwords_path, n, seed), n, seed
        ),
        "username": evaluate_model(
            username_model, sample_heldout(heldout_usernames_path, n, seed), n, seed
        ),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m eval.chi_squared [-n N] [--seed S]`` prints the report as JSON."""
    ap = argparse.ArgumentParser(description="Chi-squared tests of the PCFG DTEs (§11).")
    ap.add_argument("-n", "--n", type=int, default=20000, help="values / seeds per test")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--heldout-passwords", type=Path, default=DEFAULT_HELDOUT_PASSWORDS)
    ap.add_argument("--heldout-usernames", type=Path, default=DEFAULT_HELDOUT_USERNAMES)
    args = ap.parse_args(argv)
    report = run(args.heldout_passwords, args.heldout_usernames, n=args.n, seed=args.seed)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
