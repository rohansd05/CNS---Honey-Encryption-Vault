# Evaluation report

> Owner: T1 (Dhruv; chi-squared by Nidhi). Numbers come from `backend/eval/results/latest.json`
> (full run, commit `c8b08aa`, 2026-10-08T10:37:03Z), produced by `python -m eval.run_all`.
> Metrics are defined in PROJECT-BRIEF.md §11. Two of the five checks miss their targets. This
> report gives those numbers unchanged and explains them.

## Summary

| Check (§11) | Target | Result | Verdict |
|---|---|---|---|
| Round-trip `decode(encode(x)) == x` | 100% | **100%** (25,000 / 25,000) | ✅ |
| `decode` totality on random seeds | 100% | **100%** (60,000 seeds, 0 failures) | ✅ |
| χ² (a) seed uniformity, held-out passwords | p > 0.05 | **p = 9.4 × 10⁻⁸** (bytes) | ❌ model fit (codec control passes, p = 0.29) |
| χ² (b) decoded templates vs model | p > 0.05 | **p = 0.92** | ✅ |
| Distinguisher accuracy (best of LR / RF) | ≤ 0.60 (ideal 0.50) | **0.741** (RF), 0.501 (LR) | ❌ (0.514 on distinct strings, §4.3) |
| Dictionary attack: conventional vault | cracks | **cracked at guess #129 / 500** | ✅ |
| Dictionary attack: honey vault | no oracle | **500 distinct vaults from 500 guesses** | ✅ |
| Unlock p95, `default` KDF profile | < 1.5 s | **51 ms** (in-process) | ✅ |

## 1. Method

`backend/eval/run_all.py` runs every §11 measurement against the **real** honeycore. It never
uses the stub, whatever `HONEYCORE_IMPL` says, and writes one strict-JSON file that
`GET /api/eval/summary` serves.

| Section | What runs | Sample size (full) |
|---|---|---|
| `round_trip` | encode → decode on held-out passwords, usernames and (username, password) entries; decode on uniform random seeds for the password, username and entry DTEs | 10,000 / 10,000 / 5,000; 20,000 seeds per DTE |
| `chi_squared` | `eval.chi_squared` (owner Nidhi): seed-byte (256 bins) and seed-int (top 4 bits, 16 bins) uniformity of encoded held-out passwords; codec control on model samples; template goodness of fit of decoded random seeds (top 50 templates + "other") | n = 20,000 |
| `classifier` | `eval.classifier.run`: real held-out vs `model.sample()` decoys, 12 features, standardised logistic regression and 200-tree random forest, 5-fold stratified CV | 10,000 per class |
| `attack` | `attack.simulator` on a fresh `demo`-profile honey vault and conventional vault with the same 8 synthetic entries; demo wordlist; real master password inserted at a random rank | 500 guesses |
| `kdf` | Argon2id derive time and 8-entry `HoneyVault.unlock` time per KDF profile | 15 reps per profile |

A "pass" for a χ² test means p > 0.05, i.e. the test found no evidence of deviation. The
distinguisher's headline accuracy is the **stronger** of the two classifiers. An attacker would
use the better tool, so that is the honest number.

## 2. Setup

| Item | Value |
|---|---|
| Corpus | SecLists RockYou, Zipf-ranked weights (`w = 1/rank^0.9`), §7.3 |
| Held-out split | `pcfg.is_heldout` (sha256-based, ~20%), never trained on; `data/processed/heldout_passwords.tsv`, 50,000 valid passwords |
| Held-out usernames | **Not available.** `heldout_usernames.tsv` has not been generated and there is no raw username corpus locally. Username round-trip uses model samples; username χ² (a) and the username classifier are skipped. |
| Models | `pcfg-password-v1`, `pcfg-username-v1`; entry seed 532 B (268 + 264) |
| Entry DTE | `eval.run_all.ConcatEntryDTE` (§7.5 `username_seed ‖ password_seed`), because `honeycore.dte.entry_dte.PCFGEntryDTE` is still a placeholder. `run_all` switches to the real one automatically once it lands. |
| KDF profiles | `default` t=3, 64 MiB, p=4; `server_lite` t=2, 19 MiB, p=1; `demo` t=1, 8 MiB, p=1 |
| Hardware | Intel Core i9-14900HX, 16 GB RAM, Windows 11, Python 3.12.10 (scikit-learn 1.9.1, SciPy 1.18.1, NumPy 2.5.3) |
| Seed | 7 (NumPy RNG for held-out sampling, random seeds, CV folds). Decoys, salts, nonces and the attack password use `secrets`, so classifier and attack numbers vary slightly between runs. |
| Runtime | 48 s (classifier 31 s) |

## 3. Results

### 3.1 Round-trip and totality

| DTE | Round-trip trials | Exact matches | Rate | Random seeds | Failed decodes |
|---|---|---|---|---|---|
| Password (held-out) | 10,000 | 10,000 | 1.000 | 20,000 | 0 |
| Username (model samples) | 10,000 | 10,000 | 1.000 | 20,000 | 0 |
| Entry (532 B) | 5,000 | 5,000 | 1.000 | 20,000 | 0 |
| **Total** | **25,000** | **25,000** | **1.000** | **60,000** | **0** |

Every seed had the fixed length (0 wrong-length seeds), and every decoded value was a valid
1–32-character printable field.

### 3.2 Chi-squared

| Model | Test | n | χ² | dof | p | Pass |
|---|---|---|---|---|---|---|
| password | seed byte uniformity (held-out) | 20,000 | 390.6 | 255 | 9.4 × 10⁻⁸ | ❌ |
| password | seed int uniformity (held-out, used ints) | 20,000 | 426.6 | 15 | 1.7 × 10⁻⁸¹ | ❌ |
| password | seed int uniformity **control** (model samples) | 20,000 | 17.4 | 15 | 0.294 | ✅ |
| password | template goodness of fit (decoded random seeds) | 20,000 | 36.4 | 50 | 0.925 | ✅ |
| username | seed int uniformity **control** | 20,000 | 8.4 | 15 | 0.908 | ✅ |
| username | template goodness of fit | 20,000 | 54.5 | 50 | 0.306 | ✅ |
| username | seed uniformity (held-out) | — | — | — | — | skipped (no held-out usernames) |

Top password templates. "Model" is P(PCFG) × P(template). "Decoys" is 20,000 decoded random
seeds. "Held-out" is 20,000 weighted held-out samples.

| Template | Model | Decoys | Held-out | Held-out ÷ model |
|---|---|---|---|---|
| L6 (6 letters) | 21.19% | 21.02% | 21.34% | 1.01 |
| L7 | 12.62% | 12.67% | 15.07% | 1.19 |
| D6 (6 digits) | 12.02% | 12.12% | 9.05% | 0.75 |
| L8 | 11.33% | 11.10% | 11.33% | 1.00 |
| L9 | 4.88% | 4.84% | 4.21% | 0.86 |
| L5 | 4.30% | 4.38% | 5.84% | 1.36 |
| L6D1 | 2.64% | 2.63% | 3.16% | 1.19 |
| D5 (5 digits) | 2.59% | 2.61% | 0.33% | **0.13** |
| L6D2 | 2.37% | 2.51% | 2.73% | 1.15 |
| L10 | 2.32% | 2.32% | 2.14% | 0.92 |
| L5D2 | 2.20% | 2.44% | 1.99% | 0.90 |
| L5D1 | 2.11% | 2.21% | 2.72% | 1.29 |
| D8 | 2.07% | 2.07% | 1.70% | 0.82 |
| L4D2 | 1.95% | 1.96% | 1.87% | 0.96 |
| L7D1 | 1.86% | 1.89% | 1.96% | 1.05 |

### 3.3 Distinguisher (passwords, 10,000 real vs 10,000 decoys, 5-fold CV)

| Classifier | Accuracy (mean ± sd) | ROC-AUC | Precision | Recall |
|---|---|---|---|---|
| Logistic regression | 0.501 ± 0.005 | 0.517 | — | — |
| Random forest | **0.741 ± 0.005** | **0.810** | 0.736 | 0.761 |

Precision and recall ("real" is the positive class) come from one extra CV pass of the random
forest with the same features, folds and seed and a fresh set of decoys.
`eval.classifier.run` does not report them.

### 3.4 Dictionary attack (`demo` profile, 8 entries, 500 guesses from a 629-word list)

| | Conventional (AES-GCM) | Honey vault |
|---|---|---|
| Outcome | **CRACKED at guess #129** (= the real password's rank) | No guess can be singled out |
| Time | 698 ms (stops at the crack) | 3,360 ms for all 500 guesses (6.7 ms/guess) |
| Vaults produced | 1 (the real one; all 8 entries recovered) | **500 distinct vaults**, every one well-formed |
| Real password | Recognised by the AEAD tag | Recovers the real 8 entries, with no flag in the output |

### 3.5 KDF and unlock latency (in-process, ms)

| Profile | Params | Derive p50 / p95 | 8-entry unlock p50 / p95 |
|---|---|---|---|
| `default` (new vaults) | t=3, 64 MiB, p=4 | 49.6 / 58.2 | **49.2 / 51.3** |
| `server_lite` (honeywords) | t=2, 19 MiB, p=1 | 24.8 / 25.8 | 25.3 / 25.5 |
| `demo` (attack demo) | t=1, 8 MiB, p=1 | 6.1 / 6.3 | 6.4 / 6.5 |

Unlock time is about one KDF call. Decoding 8 entries adds well under 1 ms.

## 4. Interpretation

### 4.1 What works
- **The DTEs are correct and total.** Every held-out value round-trips exactly, and no random
  seed out of 60,000 fails to decode to a valid field. This is the property that makes
  `unlock()` unable to fail on a wrong password (AGENTS.md §1.2–1.3).
- **There is no offline oracle.** The conventional vault confirms the right password the
  moment it is tried (#129). The honey vault returns a complete, well-formed and *different*
  vault for every one of 500 guesses (500 / 500 distinct), and nothing marks the real one.
- **Decoys follow the model** (template goodness of fit p = 0.92 for passwords, 0.31 for
  usernames). **The integer codec is unbiased** (control p = 0.29 and 0.91).
- **Latency is far below target.** p95 is 51 ms against a 1.5 s target, so there is headroom
  to raise the `default` Argon2 cost.

### 4.2 Seed uniformity fails because of model fit, not the codec
On held-out passwords the seed tests reject uniformity (p ≈ 10⁻⁸ for bytes, 10⁻⁸¹ for used
ints). The control encodes values *sampled from the model* through the same codec and passes.
The bias therefore comes from real passwords having different frequencies from the model's
probabilities, not from the codec. The template table shows this directly. 5-digit passwords
(`D5`) are 2.6% of the model but 0.33% of held-out passwords. `D6` is over-weighted (12.0% vs
9.1%), while `L5` and `L7` are under-weighted (×1.36 and ×1.19).

This does not leak through the ciphertext. Seeds are XORed with an AES-CTR keystream, so the
stored bytes are uniform whatever the seed. The mismatch matters at the *decoded* level: real
vaults and decoys come from slightly different distributions. §4.3 measures exactly that.

### 4.3 Distinguisher: 0.741 overall, mostly from repeated strings, partly from real mismatch
The linear model finds **no signal** (0.501, AUC 0.52). The random forest reaches **0.741 (AUC
0.81)**, which misses the ≤ 0.60 target. An ad-hoc follow-up analysis (scratch script, same
seed and n; not part of `latest.json`) explains most of the gap:

- **Repeated strings.** The protocol samples real passwords *by weight with replacement* (Zipf
  weights). The 10,000 reals contain only 6,007 distinct strings and the 10,000 decoys 5,690, so
  43% of feature rows are duplicates. Feature importance is dominated by
  `mean_char_unigram_logprob` (0.81), which is close to unique per string. The forest therefore
  learns that a given string is real (or decoy) from training-fold copies and recognises it in
  the test fold.
- **On distinct strings the forest falls to 0.514**, near chance. Here each class is reduced to
  its distinct values (5,690 each).
- **A real signal remains in frequencies.** Decoys over-represent the most common passwords:
  the top-10 decoy strings are 15.6% of decoys, while the top-10 real strings are 7.2% of reals.
  The model's head is about twice as heavy as reality, consistent with the χ² failure. A
  frequency-aware attacker can exploit this when ranking candidate vaults.

**Bottom line.** Per distinct password, the decoys are close to indistinguishable (0.50 linear,
0.51 non-linear). The decoy *frequency* distribution is too peaked compared with real
passwords. A frequency-aware classifier can see this, and with the current protocol it shows
up as 0.741. We report 0.741 as the official §11 number and do not swap in the more favourable
0.514. Two fixes follow:
1. **Protocol:** use group-aware CV in `eval/classifier.py` (`StratifiedGroupKFold` grouped by
   string) so identical strings never appear in both train and test, and report both numbers.
2. **Model:** flatten the head when training (train on the `rockyou-withcount` frequencies
   instead of `1/rank^0.9`, or temper the weights), then re-run until the held-out seed χ² and
   the distinguisher move toward 0.5. It is also worth checking how `train_pcfg.py` assigns
   held-out weights, since the comparison assumes they match the training weights.

## 5. Limitations
- **Usernames:** there is no held-out username set yet. The username round-trip uses model
  samples, which makes it a weaker test, and username χ² (a) and the username distinguisher
  were not run.
- **Entry DTE:** results use the eval-side `ConcatEntryDTE`. It follows §7.5 exactly but is not
  the final `PCFGEntryDTE`, so re-run when that lands.
- **Independent fields:** decoy entries are independent, so password reuse across entries is
  not modelled (§13). A distinguisher working at vault level, not per password, would likely do
  better than 0.741. This evaluation does not measure that.
- **Latency is in-process,** on a fast laptop (i9-14900HX). It does not include HTTP or
  Render's smaller instances, so §11 asks for a separate measurement on the deployed API.
- **Run-to-run variation:** decoys, salts and the attack password use `secrets`, so the
  classifier and attack numbers vary slightly between runs (σ ≈ 0.005 accuracy across folds).
  The real password's rank in the attack is random.
- **Duplicate-free classifier numbers** (§4.3) come from an ad-hoc analysis, not from
  `run_all`. Fix 1 makes them part of the pipeline.
- **`dataset.training_samples` is `null`:** the model files don't record their training size.

## 6. Reproduction

```bash
# from backend/, venv active, held-out split present in data/processed/ (scripts/train_pcfg.py)
python -m eval.run_all            # full run (~1 min here), writes eval/results/latest.json
python -m eval.run_all --quick    # tiny sizes (~8 s); also writes latest.json unless --out given
python -m eval.run_all --quick --out /tmp/quick.json   # leave latest.json untouched

# individual pieces
python -m eval.chi_squared -n 20000
python -m eval.classifier -n 10000

# serve it
uvicorn app.main:app --port 8000   # GET /api/eval/summary returns latest.json
```

Options: `--seed N` (default 7), `--heldout-passwords PATH`, `--heldout-usernames PATH`. Tests:
`pytest tests/core/test_run_all.py` (synthetic held-out data, quick mode).
