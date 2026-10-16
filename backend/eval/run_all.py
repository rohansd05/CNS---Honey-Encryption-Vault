"""Run every §11 evaluation and write ``eval/results/latest.json`` (served at /api/eval/summary).

Owner: T1 -- Dhruv. Phase 2.

``python -m eval.run_all [--quick]`` (from ``backend/``) computes, on the real honeycore:

* ``round_trip`` -- ``decode(encode(x)) == x`` for held-out passwords, usernames and whole
  entries, plus ``decode`` totality on uniformly random seeds (PROJECT-BRIEF.md §11).
* ``chi_squared`` -- :func:`eval.chi_squared.run` (seed uniformity + template goodness of fit).
* ``classifier`` -- :func:`eval.classifier.run` (LR + RF distinguisher, real vs decoy), with
  with-replacement, grouped-by-string and distinct-strings-only CV; usernames also run
  ``without_domain`` (known email domains stripped from real and decoy values).
* ``attack`` -- :mod:`attack.simulator` on a fresh ``demo``-profile honey vault and a conventional
  vault holding the same 8 synthetic entries, demo wordlist, 500 guesses.
* ``kdf`` -- Argon2id derive time and 8-entry unlock time for every KDF profile.
* ``timing`` -- 8-entry unlock latency with the right vs a wrong master password per KDF
  profile, plus a two-sample Kolmogorov-Smirnov test (AGENTS.md §1.2: no timing difference).
* ``meta`` -- commit, timestamp, model ids, dataset note, run configuration, and sha256 digests
  of the loaded model files and the held-out files (``null`` for a missing held-out file).

The file also carries the keys the frontend Evaluation page reads (``timestamp``, ``version``,
``dataset``, ``distinguisher``, ``template_frequencies``, ``performance`` and the page-shaped
``round_trip`` / ``chi_squared`` fields), mirroring ``frontend/src/mocks/handlers/eval.ts``.

``--quick`` uses tiny sample sizes (seconds, for tests and CI); full mode takes a few minutes.
Nothing secret is written: no master password, no guess list, no plaintext entry, and no
held-out (corpus) value -- only counts, rates and statistics (data/README.md).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import secrets
import shutil
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats
from sklearn.model_selection import StratifiedKFold, cross_validate

from attack import simulator
from eval import chi_squared, classifier
from honeycore.dte.pcfg import is_valid_field, template
from honeycore.interfaces import ENTRY_SEED_LEN, KDF_PROFILES, Entry
from honeycore.kdf import Argon2KDF, new_salt

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
DEFAULT_OUT = Path(__file__).resolve().parent / "results" / "latest.json"
DEFAULT_HELDOUT_PASSWORDS = chi_squared.DEFAULT_HELDOUT_PASSWORDS
DEFAULT_HELDOUT_USERNAMES = chi_squared.DEFAULT_HELDOUT_USERNAMES

RESULTS_VERSION = "1.0.0"
DATASET_NOTE = (
    "passwords: RockYou rockyou-withcount, real counts (pcfg-password-v2); "
    "usernames: SecLists xato-net, Zipf-ranked (pcfg-username-v1)"
)
TARGET_ACCURACY = 0.60
IDEAL_ACCURACY = 0.50
TARGET_UNLOCK_P95_MS = 1500
ATTACK_KDF_PROFILE = "demo"
TOP_TEMPLATE_ROWS = 15

# Synthetic demo entries (never corpus lines). Same 8 go into the honey and conventional vault.
SAMPLE_ENTRIES: tuple[Entry, ...] = (
    Entry("github.com", "octo.builder", "Gh!tide2026"),
    Entry("gmail.com", "ocean10.team@gmail.com", "seashell77"),
    Entry("bank.example", "acct-4471", "Vault#Keeper9"),
    Entry("netflix.com", "movie.night", "popcorn2024"),
    Entry("slack.com", "dhruv.t1", "standup-9am"),
    Entry("aws.amazon.com", "deploy-bot", "cl0ud&Rain!"),
    Entry("spit.ac.in", "student.cns", "honeypot42"),
    Entry("reddit.com", "lurker_808", "Upvote!123"),
)


@dataclass(frozen=True)
class RunConfig:
    """Sample sizes for one run mode."""

    round_trip_passwords: int
    round_trip_usernames: int
    round_trip_entries: int
    totality_seeds: int
    chi_n: int
    classifier_n: int
    template_n: int
    attack_guesses: int
    kdf_reps: int
    timing_n: int


FULL = RunConfig(10000, 10000, 5000, 20000, 20000, 10000, 20000, 500, 15, 200)
QUICK = RunConfig(200, 200, 100, 300, 300, 200, 300, 20, 1, 20)


# ---------------------------------------------------------------------------------------------
# honeycore wiring
# ---------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Core:
    """The real honeycore pieces the evaluation needs."""

    vault_cls: Any
    conventional_vault_cls: Any
    entry_dte: Any
    password_model: Any
    username_model: Any
    entry_dte_impl: str


def _honeycore() -> Core:
    """The real honeycore via ``load_honeycore("real")``, never the stub (``HONEYCORE_IMPL``).

    The vault is bound to ``honeycore.dte.entry_dte.PCFGEntryDTE``; the field models are the
    entry DTE's own instances, so every section measures exactly what the vault uses.
    """
    from honeycore.factory import load_honeycore

    hc = load_honeycore("real")
    return Core(
        vault_cls=hc.vault_cls,
        conventional_vault_cls=hc.conventional_vault_cls,
        entry_dte=hc.entry_dte,
        password_model=hc.password_model,
        username_model=hc.entry_dte.username_model,
        entry_dte_impl=f"{type(hc.entry_dte).__module__}.{type(hc.entry_dte).__name__}",
    )


# ---------------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------------
def _rate(ok: int, total: int) -> float:
    return ok / total if total else 0.0


def _ms_stats(samples: list[float]) -> dict[str, float]:
    """p50 / p95 / mean / min / max of millisecond timings, rounded to 0.01 ms."""
    arr = np.asarray(samples, dtype=float)
    return {
        "p50": round(float(np.percentile(arr, 50)), 2),
        "p95": round(float(np.percentile(arr, 95)), 2),
        "mean": round(float(arr.mean()), 2),
        "min": round(float(arr.min()), 2),
        "max": round(float(arr.max()), 2),
    }


def _timed_ms(fn: Callable[[], Any]) -> float:
    start = time.perf_counter()
    fn()
    return (time.perf_counter() - start) * 1000


def _load_valid(path: Path) -> list[str]:
    """Distinct valid (§7.1) values of a ``value[<TAB>weight]`` TSV, in file order."""
    seen: set[str] = set()
    out: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            value = raw.rstrip("\r\n").partition("\t")[0]
            if is_valid_field(value) and value not in seen:
                seen.add(value)
                out.append(value)
    return out


def _pick(values: list[str], n: int, rng: np.random.Generator) -> list[str]:
    """``n`` distinct values (fewer if ``values`` is shorter), chosen with a seeded RNG."""
    k = min(n, len(values))
    return [values[i] for i in rng.choice(len(values), size=k, replace=False)]


def _sanitize(obj: Any) -> Any:
    """Make ``obj`` strict-JSON safe: NaN/inf -> ``None``, NumPy scalars -> Python."""
    if isinstance(obj, dict):
        return {str(k): _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, np.generic):
        obj = obj.item()
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj


# ---------------------------------------------------------------------------------------------
# round_trip
# ---------------------------------------------------------------------------------------------
def _round_trip_block(
    values: Iterable[Any],
    encode: Callable[[Any], bytes],
    decode: Callable[[bytes], Any],
    n_bytes: int,
) -> dict[str, Any]:
    """Count exact round-trips and fixed seed length. Failing values are never recorded."""
    trials = ok = wrong_len = 0
    errors: Counter[str] = Counter()
    for value in values:
        trials += 1
        try:
            seed = encode(value)
            if len(seed) != n_bytes:
                wrong_len += 1
            if decode(seed) == value:
                ok += 1
        except Exception as exc:  # any exception is a failed trial
            errors[type(exc).__name__] += 1
    return {
        "trials": trials,
        "exact_match_count": ok,
        "success_rate": _rate(ok, trials),
        "wrong_seed_length": wrong_len,
        "errors": dict(errors),
    }


def _totality_block(
    decode: Callable[[bytes], Any],
    seed_len: int,
    n: int,
    rng: np.random.Generator,
    ok: Callable[[Any], bool],
) -> dict[str, Any]:
    """Decode ``n`` uniformly random seeds; a failure is an exception or an invalid output."""
    failed = 0
    for _ in range(n):
        try:
            if not ok(decode(rng.bytes(seed_len))):
                failed += 1
        except Exception:  # decode must be total: any exception is a failure
            failed += 1
    return {
        "random_seed_trials": n,
        "failed_decodes": failed,
        "totality_rate": _rate(n - failed, n),
    }


def round_trip(
    core: Core,
    heldout_passwords: Path,
    heldout_usernames: Path,
    cfg: RunConfig,
    seed: int,
) -> dict[str, Any]:
    """Round-trip success on held-out values and decode totality on random seeds (§11).

    Passwords come from the held-out split. Usernames come from the held-out username file when
    it exists, otherwise from the username model itself (recorded in ``usernames.source``).
    Entries pair those usernames and passwords through the entry DTE.
    """
    rng = np.random.default_rng(seed)
    pw_pool = _load_valid(heldout_passwords)
    passwords = _pick(pw_pool, cfg.round_trip_passwords, rng)
    if heldout_usernames.exists():
        usernames = _pick(_load_valid(heldout_usernames), cfg.round_trip_usernames, rng)
        username_source = "heldout"
    else:
        usernames = [core.username_model.sample() for _ in range(cfg.round_trip_usernames)]
        username_source = "model_samples (held-out username file missing)"

    pm, um, ed = core.password_model, core.username_model, core.entry_dte
    pw = _round_trip_block(passwords, pm.encode, pm.decode, pm.seed_len)
    un = _round_trip_block(usernames, um.encode, um.decode, um.seed_len)
    pairs = list(zip(usernames, passwords, strict=False))[: cfg.round_trip_entries]
    en = _round_trip_block(pairs, lambda p: ed.encode(*p), ed.decode, ENTRY_SEED_LEN)
    pw["source"] = "heldout"
    un["source"] = username_source
    en["source"] = f"(username, password) pairs from the two sets above; {username_source}"

    def entry_ok(pair: Any) -> bool:
        return len(pair) == 2 and all(is_valid_field(v) for v in pair)

    tot = {
        "password": _totality_block(
            pm.decode, pm.seed_len, cfg.totality_seeds, rng, is_valid_field
        ),
        "username": _totality_block(
            um.decode, um.seed_len, cfg.totality_seeds, rng, is_valid_field
        ),
        "entry": _totality_block(ed.decode, ENTRY_SEED_LEN, cfg.totality_seeds, rng, entry_ok),
    }
    trials = sum(b["trials"] for b in (pw, un, en))
    ok = sum(b["exact_match_count"] for b in (pw, un, en))
    seeds = sum(t["random_seed_trials"] for t in tot.values())
    failed = sum(t["failed_decodes"] for t in tot.values())
    return {
        "trials": trials,
        "exact_match_count": ok,
        "success_rate": _rate(ok, trials),
        "decode_totality": {
            "random_seed_trials": seeds,
            "failed_decodes": failed,
            "totality_rate": _rate(seeds - failed, seeds),
            "per_dte": tot,
        },
        "passwords": pw,
        "usernames": un,
        "entries": en,
        "heldout_passwords_available": len(pw_pool),
    }


# ---------------------------------------------------------------------------------------------
# chi_squared + template frequencies
# ---------------------------------------------------------------------------------------------
def _page_chi(result: dict[str, Any], note: str) -> dict[str, Any]:
    """One chi-squared result in the Evaluation page's shape."""
    return {
        "statistic": result["chi2"],
        "degrees_of_freedom": result["dof"],
        "p_value": result["p_value"],
        "null_hypothesis_accepted": result["p_value"] > chi_squared.ALPHA,
        "note": note,
        "n": result["n"],
    }


def run_chi_squared(
    core: Core, heldout_passwords: Path, heldout_usernames: Path, n: int, seed: int
) -> dict[str, Any]:
    """:func:`eval.chi_squared.run`, plus the page-shaped ``seed_uniformity`` / GOF summaries.

    When the held-out username file is missing, ``chi_squared.run`` cannot run as a whole; the
    password section is computed the same way and the username section keeps only the tests
    that need no real usernames (template goodness of fit and the codec control).
    """
    if heldout_usernames.exists():
        report = chi_squared.run(
            heldout_passwords,
            heldout_usernames,
            n=n,
            seed=seed,
            password_model=core.password_model,
            username_model=core.username_model,
        )
    else:
        um = core.username_model
        control = chi_squared.seed_int_uniformity(um, (um.sample() for _ in range(n)), n)
        control["test"] = "seed_int_uniformity_control"
        report = {
            "n": n,
            "seed": seed,
            "alpha": chi_squared.ALPHA,
            "interpretation": chi_squared.INTERPRETATION,
            "password": chi_squared.evaluate_model(
                core.password_model,
                chi_squared.sample_heldout(heldout_passwords, n, seed),
                n,
                seed,
            ),
            "username": {
                "model": um.model_id,
                "skipped": "seed_byte_uniformity / seed_int_uniformity: no held-out usernames",
                "seed_int_uniformity_control": control,
                "template_goodness_of_fit": chi_squared.template_goodness_of_fit(um, n, seed),
            },
        }
    pw = report["password"]
    report["seed_uniformity"] = _page_chi(
        pw["seed_byte_uniformity"],
        "Password model: bytes of seeds from encoding held-out passwords vs uniform (256 bins)",
    )
    report["template_goodness_of_fit"] = _page_chi(
        pw["template_goodness_of_fit"],
        "Password model: templates of decoded random seeds vs model probabilities",
    )
    return report


_CLASS_NAMES = {"L": ("letter", "letters"), "D": ("digit", "digits"), "S": ("symbol", "symbols")}


def describe_template(tmpl: str) -> str:
    """Human-readable template, e.g. ``L6D2`` -> ``6 letters + 2 digits``."""
    parts = []
    for cls, count in re.findall(r"([LDS])(\d+)", tmpl):
        one, many = _CLASS_NAMES[cls]
        parts.append(f"{count} {one if count == '1' else many}")
    return " + ".join(parts) or tmpl


def template_frequencies(
    core: Core, heldout_passwords: Path, n: int, seed: int
) -> list[dict[str, Any]]:
    """Top password templates: model probability vs decoded random seeds vs held-out passwords.

    ``model_frequency`` = P(PCFG path) * P(template); ``decoded_frequency`` = share of ``n``
    decoded random seeds; ``heldout_frequency`` = share of ``n`` weighted held-out samples.
    """
    model = core.password_model
    rng = np.random.default_rng(seed)
    decoded = Counter(template(model.decode(rng.bytes(model.seed_len))) for _ in range(n))
    real = Counter(template(v) for v in chi_squared.sample_heldout(heldout_passwords, n, seed))
    dist = model._templates
    p_pcfg = model._path.probability(model._pcfg_idx)
    ranked = sorted(range(len(dist)), key=dist.weight, reverse=True)[:TOP_TEMPLATE_ROWS]
    rows = []
    for i in ranked:
        tmpl = dist.symbols[i]
        rows.append(
            {
                "template": tmpl,
                "model_frequency": round(p_pcfg * dist.probability(i), 5),
                "decoded_frequency": round(decoded[tmpl] / n, 5),
                "heldout_frequency": round(real[tmpl] / n, 5),
                "description": describe_template(tmpl),
            }
        )
    return rows


# ---------------------------------------------------------------------------------------------
# classifier / distinguisher
# ---------------------------------------------------------------------------------------------
def _precision_recall(model: Any, heldout: Path, n: int, seed: int, name: str) -> dict[str, float]:
    """Precision / recall ("real" = positive) of classifier ``name`` with the same CV protocol.

    ``eval.classifier.run`` reports accuracy and ROC-AUC only; the page also shows precision and
    recall, so they come from one extra pass (same features, folds and seed; fresh decoys).
    """
    reals = classifier._sample_heldout(heldout, n, seed)
    decoys = [model.sample() for _ in range(n)]
    x = np.array([classifier.features(v, model) for v in (*reals, *decoys)], dtype=float)
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    y = np.array([1] * len(reals) + [0] * len(decoys))
    clf = dict(classifier._classifiers(seed))[name]
    skf = StratifiedKFold(n_splits=classifier.CV_FOLDS, shuffle=True, random_state=seed)
    cv = cross_validate(clf, x, y, cv=skf, scoring=("precision", "recall"))
    return {
        "precision": float(cv["test_precision"].mean()),
        "recall": float(cv["test_recall"].mean()),
    }


def run_classifier(
    core: Core, heldout_passwords: Path, heldout_usernames: Path, n: int, seed: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return ``(classifier, distinguisher)``: raw ``classifier.run`` output and the page view.

    The page's headline ``metrics`` are those of the *stronger* classifier (higher accuracy):
    the attacker picks the best tool, so that is the honest number to report. They use the
    with-replacement protocol; ``grouped_results`` / ``distinct_results`` add the grouped-CV and
    distinct-strings-only scores (see :mod:`eval.classifier`).
    """
    names = ("logreg", "random_forest")
    raw: dict[str, Any] = {
        "password": classifier.run(core.password_model, heldout_passwords, n=n, seed=seed)
    }
    if heldout_usernames.exists():
        um = core.username_model
        raw["username"] = classifier.run(um, heldout_usernames, n=n, seed=seed)
        domains = um._domain_set  # the model's own email-domain table (§7.4)
        without = classifier.run(
            um,
            heldout_usernames,
            n=n,
            seed=seed,
            transform=lambda v: classifier.strip_known_domain(v, domains),
        )
        without["note"] = (
            "known email domains (the username model's table) stripped from real and decoy "
            "values before features; same real sample, fresh decoys"
        )
        raw["username"]["without_domain"] = without
    else:
        raw["username"] = {"skipped": "no held-out usernames file"}

    pw = raw["password"]
    best = max(names, key=lambda k: pw[k]["accuracy_mean"])
    grouped = {k: pw["grouped"][k] for k in names if k in pw["grouped"]}  # absent if skipped
    distinct = {k: pw["distinct"][k] for k in names if k in pw["distinct"]}
    grouped_acc = max((s["accuracy_mean"] for s in grouped.values()), default=math.nan)
    distinct_acc = max((s["accuracy_mean"] for s in distinct.values()), default=math.nan)
    pr = _precision_recall(core.password_model, heldout_passwords, n, seed, best)
    acc = pw[best]["accuracy_mean"]
    if acc <= IDEAL_ACCURACY + 0.05:
        verdict = "near-ideal: decoys are close to indistinguishable from real passwords"
    elif acc <= TARGET_ACCURACY:
        verdict = "meets the <= 0.60 target, but the decoys are partly distinguishable"
    else:
        verdict = "misses the <= 0.60 target: the classifier separates real passwords from decoys"
    distinguisher = {
        "classifier": "Logistic Regression + Random Forest (5-fold stratified CV)",
        "features": list(classifier.FEATURE_NAMES),
        "metrics": {
            "accuracy": acc,
            "roc_auc": pw[best]["roc_auc_mean"],
            "precision": pr["precision"],
            "recall": pr["recall"],
            "baseline_chance": IDEAL_ACCURACY,
        },
        "metrics_classifier": best,
        "per_classifier": {k: pw[k] for k in names},
        "grouped_results": grouped,
        "distinct_results": distinct,
        "n_per_class": pw["n"],
        "target_accuracy": TARGET_ACCURACY,
        "ideal_accuracy": IDEAL_ACCURACY,
        "conclusion": (
            f"Password distinguisher ({best}) accuracy {acc:.3f} vs ideal 0.5: {verdict}. "
            f"Best accuracy with grouped CV (no string in both train and test) "
            f"{grouped_acc:.3f}; on distinct strings only {distinct_acc:.3f}."
        ),
    }
    return raw, distinguisher


# ---------------------------------------------------------------------------------------------
# attack
# ---------------------------------------------------------------------------------------------
def _fill(vault: Any, master: str) -> None:
    for entry in SAMPLE_ENTRIES:
        vault.add_entry(master, entry)


def _same_entries(decoded: Iterable[Any]) -> bool:
    got = [(e.service, e.username, e.password) for e in decoded]
    return got == [(e.service, e.username, e.password) for e in SAMPLE_ENTRIES]


def run_attack(core: Core, guesses: int) -> dict[str, Any]:
    """Dictionary attack (§11) on fresh ``demo`` honey + conventional vaults with 8 entries.

    The master password is random per run and never leaves this function; only counts,
    indices and timings are returned (no guesses, no decoy or real entries).
    """
    master = "demo-" + secrets.token_urlsafe(9)
    honey = core.vault_cls.new(ATTACK_KDF_PROFILE)
    _fill(honey, master)
    conventional = core.conventional_vault_cls.new(master, ATTACK_KDF_PROFILE)
    _fill(conventional, master)

    wordlist = simulator.load_wordlist()
    guess_list, real_index = simulator.build_guess_list(master, guesses, wordlist)
    report = simulator.run_dictionary_attack(honey, conventional, guess_list, real_index)
    base, hv = report.baseline, report.honey

    sample_fields_valid = all(
        is_valid_field(e["username"]) and is_valid_field(e["password"])
        for s in hv.samples
        for e in s.entries
    )
    recovered = [(e["service"], e["username"], e["password"]) for e in base.recovered_entries]
    expected = [(e.service, e.username, e.password) for e in SAMPLE_ENTRIES]
    return {
        "kdf_profile": ATTACK_KDF_PROFILE,
        "entries_per_vault": len(SAMPLE_ENTRIES),
        "wordlist": "attack/wordlists/demo_wordlist.txt",
        "wordlist_size": len(wordlist),
        "guesses": len(guess_list),
        "real_guess_index": report.reveal.real_guess_index,
        "conventional": {
            "cracked": base.cracked,
            "guess_index": base.guess_index,
            "elapsed_ms": base.elapsed_ms,
            "recovered_entries": len(base.recovered_entries),
            "recovered_entries_are_real": recovered == expected,
        },
        "honey": {
            "guesses_tried": hv.guesses_tried,
            "elapsed_ms": hv.elapsed_ms,
            "ms_per_guess": round(hv.elapsed_ms / max(hv.guesses_tried, 1), 2),
            "distinct_vaults": hv.distinct_vaults,
            "distinct_vault_rate": _rate(hv.distinct_vaults, hv.guesses_tried),
            "samples_returned": len(hv.samples),
            "sample_fields_well_formed": sample_fields_valid,
            "correct_password_recovers_real_entries": _same_entries(honey.unlock(master).entries),
        },
    }


# ---------------------------------------------------------------------------------------------
# kdf
# ---------------------------------------------------------------------------------------------
def run_kdf(core: Core, reps: int) -> dict[str, Any]:
    """Argon2id derive time and 8-entry honey-vault unlock time per KDF profile (in-process).

    The benchmark password is a fixed non-secret string; timings include no network/API cost.
    """
    kdf = Argon2KDF()
    bench_password = "kdf-benchmark-not-a-secret"  # noqa: S105 -- benchmark input, not a secret
    out: dict[str, Any] = {}
    for name, params in KDF_PROFILES.items():
        salt = new_salt()
        derive = [
            _timed_ms(lambda p=params, s=salt: kdf.derive(bench_password, s, p))
            for _ in range(reps)
        ]
        vault = core.vault_cls.new(name)
        _fill(vault, bench_password)
        unlock = [_timed_ms(lambda v=vault: v.unlock(bench_password)) for _ in range(reps)]
        out[name] = {
            "params": {
                "time_cost": params.time_cost,
                "memory_cost_kib": params.memory_cost_kib,
                "parallelism": params.parallelism,
                "hash_len": params.hash_len,
            },
            "reps": reps,
            "derive_ms": _ms_stats(derive),
            "unlock_ms": _ms_stats(unlock),
        }
    return out


def run_timing(core: Core, n: int) -> dict[str, Any]:
    """In-process 8-entry ``HoneyVault.unlock`` latency, right vs wrong master password.

    Per KDF profile: a fresh vault, one warm-up unlock, then ``n`` rounds of a right, a wrong
    and a second right ("control") unlock, order reversed every other round so drift hits all
    samples alike. Each wrong guess is a fresh random password of the same length. A two-sample
    Kolmogorov-Smirnov test asks whether right and wrong share one distribution (p > alpha: no
    detectable difference); the right-vs-control test is the A/A false-alarm check.
    ``decode_only_us`` times the entry DTE alone on the 8 real seeds vs 8 random seeds, which
    isolates the value-dependent decode cost. The passwords never leave this function.
    """
    profiles: dict[str, Any] = {}
    for name in KDF_PROFILES:
        master = secrets.token_urlsafe(12)
        vault = core.vault_cls.new(name)
        _fill(vault, master)
        vault.unlock(master)  # warm-up: first-call allocations and model caches
        right: list[float] = []
        wrong: list[float] = []
        control: list[float] = []
        for i in range(n):
            trio = [(right, master), (wrong, secrets.token_urlsafe(12)), (control, master)]
            for bucket, password in trio if i % 2 == 0 else trio[::-1]:
                bucket.append(_timed_ms(lambda v=vault, p=password: v.unlock(p)))
        ks = stats.ks_2samp(right, wrong)
        profiles[name] = {
            "right_ms": _ms_stats(right),
            "wrong_ms": _ms_stats(wrong),
            "ks_statistic": float(ks.statistic),
            "ks_p_value": float(ks.pvalue),
            "same_distribution": bool(ks.pvalue > chi_squared.ALPHA),
            "control_ks_p_value": float(stats.ks_2samp(right, control).pvalue),
        }

    dte = core.entry_dte
    real_seeds = [dte.encode(e.username, e.password) for e in SAMPLE_ENTRIES]
    real_us: list[float] = []
    random_us: list[float] = []
    for i in range(n * 10):
        random_seeds = [secrets.token_bytes(ENTRY_SEED_LEN) for _ in SAMPLE_ENTRIES]
        pair = [(real_us, real_seeds), (random_us, random_seeds)]
        for bucket, seeds in pair if i % 2 == 0 else pair[::-1]:
            bucket.append(1000 * _timed_ms(lambda s=seeds: [dte.decode(x) for x in s]))
    return {
        "n_per_class": n,
        "entries": len(SAMPLE_ENTRIES),
        "alpha": chi_squared.ALPHA,
        "method": (
            "in-process HoneyVault.unlock, right vs fresh wrong master password (plus a second "
            "right sample as A/A control), interleaved; two-sample Kolmogorov-Smirnov test"
        ),
        "profiles": profiles,
        "decode_only_us": {
            "rounds": n * 10,
            "real_seeds": _ms_stats(real_us),
            "random_seeds": _ms_stats(random_us),
            "ks_p_value": float(stats.ks_2samp(real_us, random_us).pvalue),
        },
    }


def _profile_label(name: str) -> str:
    p = KDF_PROFILES[name]
    return f"{name} (t={p.time_cost}, m={p.memory_cost_kib // 1024} MiB, p={p.parallelism})"


# ---------------------------------------------------------------------------------------------
# meta + driver
# ---------------------------------------------------------------------------------------------
def _git_commit() -> str | None:
    """Short HEAD commit via read-only ``git rev-parse``; ``None`` if git is unavailable."""
    git = shutil.which("git")
    if git is None:
        return None
    try:
        result = subprocess.run(  # noqa: S603 -- fixed argv, read-only command
            [git, "rev-parse", "--short", "HEAD"],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def _sha256(path: Path) -> str | None:
    """Hex SHA-256 of the file at ``path`` (digest only, never contents); ``None`` if missing."""
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def _model_file(model: Any) -> Path:
    """The file the real loader read: ``load_default`` parses the class's ``default_model_path``."""
    return Path(type(model).default_model_path)


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return path.name


def build_results(
    *,
    quick: bool = False,
    seed: int = 7,
    heldout_passwords: Path = DEFAULT_HELDOUT_PASSWORDS,
    heldout_usernames: Path = DEFAULT_HELDOUT_USERNAMES,
    log: Callable[[str], None] = lambda _msg: None,
) -> dict[str, Any]:
    """Run every evaluation and return the results dict (JSON-serialisable, strict JSON).

    Raises ``FileNotFoundError`` if the held-out password file is missing.
    """
    heldout_passwords = Path(heldout_passwords)
    heldout_usernames = Path(heldout_usernames)
    if not heldout_passwords.exists():
        raise FileNotFoundError(
            f"held-out passwords not found: {heldout_passwords} (run scripts/train_pcfg.py)"
        )
    cfg = QUICK if quick else FULL
    started = time.perf_counter()
    core = _honeycore()
    timings: dict[str, float] = {}

    def step(name: str, fn: Callable[[], Any]) -> Any:
        log(f"[run_all] {name} ...")
        t0 = time.perf_counter()
        value = fn()
        timings[name] = round(time.perf_counter() - t0, 2)
        log(f"[run_all] {name} done in {timings[name]} s")
        return value

    rt = step(
        "round_trip", lambda: round_trip(core, heldout_passwords, heldout_usernames, cfg, seed)
    )
    chi = step(
        "chi_squared",
        lambda: run_chi_squared(core, heldout_passwords, heldout_usernames, cfg.chi_n, seed),
    )
    templates = step(
        "template_frequencies",
        lambda: template_frequencies(core, heldout_passwords, cfg.template_n, seed),
    )
    clf, dist = step(
        "classifier",
        lambda: run_classifier(core, heldout_passwords, heldout_usernames, cfg.classifier_n, seed),
    )
    attack = step("attack", lambda: run_attack(core, cfg.attack_guesses))
    kdf = step("kdf", lambda: run_kdf(core, cfg.kdf_reps))
    timing = step("timing", lambda: run_timing(core, cfg.timing_n))

    vault_profile = os.environ.get("VAULT_KDF_PROFILE", "default")
    if vault_profile not in KDF_PROFILES:
        vault_profile = "default"
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    models = {
        "password_model": core.password_model.model_id,
        "username_model": core.username_model.model_id,
        "entry_seed_len": ENTRY_SEED_LEN,
    }
    results = {
        "timestamp": timestamp,
        "version": RESULTS_VERSION,
        "dataset": {
            "corpus": DATASET_NOTE,
            "training_samples": None,
            "test_samples": rt["heldout_passwords_available"],
            "heldout_passwords_file": _rel(heldout_passwords),
            "heldout_usernames_file": (
                _rel(heldout_usernames) if heldout_usernames.exists() else None
            ),
            "models": models,
        },
        "round_trip": rt,
        "chi_squared": chi,
        "classifier": clf,
        "distinguisher": dist,
        "template_frequencies": templates,
        "attack": attack,
        "kdf": kdf,
        "timing": timing,
        "performance": {
            "unlock_p50_ms": kdf[vault_profile]["unlock_ms"]["p50"],
            "unlock_p95_ms": kdf[vault_profile]["unlock_ms"]["p95"],
            "target_p95_ms": TARGET_UNLOCK_P95_MS,
            "argon2_kdf_profile": _profile_label(vault_profile),
            "entries": len(SAMPLE_ENTRIES),
            "measured": "in-process HoneyVault.unlock (no HTTP); see kdf for every profile",
        },
        "meta": {
            "git_commit": _git_commit(),
            "timestamp": timestamp,
            "mode": "quick" if quick else "full",
            "seed": seed,
            "config": cfg.__dict__,
            "models": models,
            "entry_dte_impl": core.entry_dte_impl,
            "honeycore_impl": "real",
            "dataset_note": DATASET_NOTE,
            "model_sha256": {
                "password_model": _sha256(_model_file(core.password_model)),
                "username_model": _sha256(_model_file(core.username_model)),
            },
            "heldout_sha256": {
                "passwords": _sha256(heldout_passwords),
                "usernames": _sha256(heldout_usernames),
            },
            "python": platform.python_version(),
            "platform": platform.platform(terse=True),
            "step_seconds": timings,
            "duration_s": round(time.perf_counter() - started, 2),
            "reproducibility": (
                "held-out sampling, random seeds and CV folds use NumPy RNG(seed); decoys "
                "(model.sample), vault salts/nonces and the attack password use `secrets`, "
                "so classifier/attack numbers vary slightly between runs"
            ),
        },
    }
    return _sanitize(results)


def write_results(results: dict[str, Any], out: Path) -> None:
    """Write ``results`` as strict, pretty UTF-8 JSON (raises on NaN)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False)
    out.write_text(text + "\n", encoding="utf-8")


def _headline(r: dict[str, Any]) -> str:
    chi = r["chi_squared"]
    d = r["distinguisher"]
    a = r["attack"]
    un = r["classifier"]["username"]
    extra = [
        f"{label} distinguisher best acc="
        f"{max(block[k]['accuracy_mean'] for k in ('logreg', 'random_forest')):.3f}"
        for label, block in (
            ("username", un),
            ("username without_domain", un.get("without_domain")),
        )
        if block and "skipped" not in block
    ]
    extra += [
        f"timing {k}: right p50 {t['right_ms']['p50']} / wrong p50 {t['wrong_ms']['p50']} ms, "
        f"KS p={t['ks_p_value']:.3g} (A/A control p={t['control_ks_p_value']:.3g})"
        for k, t in r["timing"]["profiles"].items()
    ]
    return "\n".join(
        [
            f"round-trip {r['round_trip']['success_rate']:.4f} "
            f"({r['round_trip']['exact_match_count']}/{r['round_trip']['trials']}), "
            f"totality {r['round_trip']['decode_totality']['totality_rate']:.4f}",
            f"chi2 seed bytes p={chi['seed_uniformity']['p_value']:.4g}, "
            f"template GOF p={chi['template_goodness_of_fit']['p_value']:.4g}",
            f"distinguisher {d['metrics_classifier']} acc={d['metrics']['accuracy']:.3f} "
            f"auc={d['metrics']['roc_auc']:.3f}; "
            + ", ".join(
                f"{p} {k}={s['accuracy_mean']:.3f}"
                for p in ("grouped", "distinct")
                for k, s in d[f"{p}_results"].items()
            ),
            f"attack: conventional cracked={a['conventional']['cracked']} at "
            f"#{a['conventional']['guess_index']}; honey distinct vaults "
            f"{a['honey']['distinct_vaults']}/{a['honey']['guesses_tried']}",
            f"unlock p95 {r['performance']['unlock_p95_ms']} ms "
            f"[{r['performance']['argon2_kdf_profile']}]",
            *extra,
        ]
    )


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m eval.run_all [--quick] [--out PATH]`` writes the results JSON."""
    ap = argparse.ArgumentParser(description="Run all §11 evaluations -> latest.json.")
    ap.add_argument("--quick", action="store_true", help="tiny sample sizes (tests/CI)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--heldout-passwords", type=Path, default=DEFAULT_HELDOUT_PASSWORDS)
    ap.add_argument("--heldout-usernames", type=Path, default=DEFAULT_HELDOUT_USERNAMES)
    args = ap.parse_args(argv)

    def log(msg: str) -> None:
        print(msg, file=sys.stderr, flush=True)

    results = build_results(
        quick=args.quick,
        seed=args.seed,
        heldout_passwords=args.heldout_passwords,
        heldout_usernames=args.heldout_usernames,
        log=log,
    )
    write_results(results, args.out)
    log(_headline(results))
    log(f"[run_all] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
