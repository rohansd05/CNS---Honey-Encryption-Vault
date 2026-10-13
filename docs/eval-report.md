# Evaluation report

> Owner: T1 (Dhruv; chi-squared by Nidhi). Numbers come from `backend/eval/results/latest.json`
> (full run, 2026-10-12T15:26:05Z, `meta.git_commit` `0668556` plus this branch's eval changes),
> produced by `python -m eval.run_all`. Metrics are defined in PROJECT-BRIEF.md §11. Seed
> uniformity fails for both models, and the official password distinguisher number misses its
> target. This report gives those numbers unchanged and explains them.

## Summary

| Check (§11) | Target | Result | Verdict |
|---|---|---|---|
| Round-trip `decode(encode(x)) == x` | 100% | **100%** (25,000 / 25,000, all held-out) | ✅ |
| `decode` totality on random seeds | 100% | **100%** (60,000 seeds, 0 failures) | ✅ |
| χ² (a) seed uniformity, held-out passwords | p > 0.05 | **p = 6.8 × 10⁻¹²** (bytes) | ❌ model fit (codec control passes, p = 0.25) |
| χ² (a) seed uniformity, held-out usernames | p > 0.05 | **p = 4.7 × 10⁻⁵⁴** (bytes) | ❌ model fit (codec control passes, p = 0.97) |
| χ² (b) decoded templates vs model | p > 0.05 | **p = 0.92** passwords, **0.31** usernames | ✅ |
| Password distinguisher, official protocol (best of LR / RF) | ≤ 0.60 (ideal 0.50) | **0.748** (RF), 0.506 (LR) | ❌ |
| Password distinguisher, grouped CV / distinct strings | ≤ 0.60 | **0.545** / **0.544** (best of LR / RF) | ✅ supplementary (§4.3) |
| Username distinguisher, official / grouped / distinct | ≤ 0.60 | **0.823** / **0.738** / **0.762** | ❌ email suffix (§4.4) |
| Dictionary attack: conventional vault | cracks | **cracked at guess #447 / 500** | ✅ |
| Dictionary attack: honey vault | no oracle | **500 distinct vaults from 500 guesses** | ✅ |
| Unlock p95, `default` KDF profile | < 1.5 s | **62 ms** (in-process) | ✅ |

## 1. Method

`backend/eval/run_all.py` runs every §11 measurement against the **real** honeycore through
`load_honeycore("real")`. It never uses the stub, whatever `HONEYCORE_IMPL` says, and writes one
strict-JSON file that `GET /api/eval/summary` serves.

| Section | What runs | Sample size (full) |
|---|---|---|
| `round_trip` | encode → decode on held-out passwords, held-out usernames and (username, password) entries; decode on uniform random seeds for the password, username and entry DTEs | 10,000 / 10,000 / 5,000; 20,000 seeds per DTE |
| `chi_squared` | `eval.chi_squared` (owner Nidhi): seed-byte (256 bins) and seed-int (top 4 bits, 16 bins) uniformity of encoded held-out values; codec control on model samples; template goodness of fit of decoded random seeds (top 50 templates + "other"); password and username models | n = 20,000 |
| `classifier` | `eval.classifier.run`: real held-out vs `model.sample()` decoys, 12 features, standardised logistic regression and 200-tree random forest, 5-fold CV under three protocols (§4.3) | 10,000 per class |
| `attack` | `attack.simulator` on a fresh `demo`-profile honey vault and conventional vault with the same 8 synthetic entries; demo wordlist; real master password inserted at a random rank | 500 guesses |
| `kdf` | Argon2id derive time and 8-entry `HoneyVault.unlock` time per KDF profile | 15 reps per profile |

A "pass" for a χ² test means p > 0.05, i.e. the test found no evidence of deviation. The
distinguisher's headline accuracy is the **stronger** of the two classifiers. An attacker would
use the better tool, so that is the honest number.

## 2. Setup

| Item | Value |
|---|---|
| Corpus | Passwords: SecLists RockYou, Zipf-ranked weights (`w = 1/rank^0.9`), §7.3. Usernames: SecLists `xato-net-10-million-usernames`, Zipf-ranked, §7.4 |
| Held-out split | `pcfg.is_heldout` (sha256-based, ~20%), never trained on. `data/processed/heldout_passwords.tsv` and `heldout_usernames.tsv`, 50,000 valid values each |
| Held-out usernames | New in this run. Produced by `train_pcfg.py --kind username` (1M lines, `--format plain`) with `--out` pointing at a temporary file. That temporary model was identical to the committed `pcfg_username_v1`, so the split is exactly the one the committed model never saw |
| Models | `pcfg-password-v1`, `pcfg-username-v1`; entry seed 532 B (268 + 264) |
| Entry DTE | `honeycore.dte.entry_dte.PCFGEntryDTE` (`meta.entry_dte_impl`), the same one the vault uses. The eval-side fallback is gone |
| KDF profiles | `default` t=3, 64 MiB, p=4; `server_lite` t=2, 19 MiB, p=1; `demo` t=1, 8 MiB, p=1 |
| Hardware | Intel Core i9-14900HX, 16 GB RAM, Windows 11, Python 3.12.10 (scikit-learn 1.9.1, SciPy 1.18.1, NumPy 2.5.3) |
| Seed | 7 (NumPy RNG for held-out sampling, random seeds, CV folds). Decoys, salts, nonces and the attack password use `secrets`, so classifier and attack numbers vary slightly between runs. |
| Runtime | 99 s (classifier 78 s) |

## 3. Results

### 3.1 Round-trip and totality

| DTE | Round-trip trials | Exact matches | Rate | Random seeds | Failed decodes |
|---|---|---|---|---|---|
| Password (held-out) | 10,000 | 10,000 | 1.000 | 20,000 | 0 |
| Username (held-out) | 10,000 | 10,000 | 1.000 | 20,000 | 0 |
| Entry (532 B, held-out pairs) | 5,000 | 5,000 | 1.000 | 20,000 | 0 |
| **Total** | **25,000** | **25,000** | **1.000** | **60,000** | **0** |

Every seed had the fixed length (0 wrong-length seeds), and every decoded value was a valid
1–32-character printable field.

### 3.2 Chi-squared

| Model | Test | n | χ² | dof | p | Pass |
|---|---|---|---|---|---|---|
| password | seed byte uniformity (held-out) | 20,000 | 438.7 | 255 | 6.8 × 10⁻¹² | ❌ |
| password | seed int uniformity (held-out, used ints) | 20,000 | 382.2 | 15 | 3.7 × 10⁻⁷² | ❌ |
| password | seed int uniformity **control** (model samples) | 20,000 | 18.3 | 15 | 0.245 | ✅ |
| password | template goodness of fit (decoded random seeds) | 20,000 | 36.4 | 50 | 0.925 | ✅ |
| username | seed byte uniformity (held-out) | 20,000 | 776.4 | 255 | 4.7 × 10⁻⁵⁴ | ❌ |
| username | seed int uniformity (held-out, used ints) | 20,000 | 1,420.6 | 15 | 6.1 × 10⁻²⁹⁴ | ❌ |
| username | seed int uniformity **control** (model samples) | 20,000 | 6.4 | 15 | 0.972 | ✅ |
| username | template goodness of fit | 20,000 | 54.5 | 50 | 0.306 | ✅ |

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

### 3.3 Distinguisher (10,000 real vs 10,000 decoys per field, 5-fold CV)

Accuracy is mean ± sd over the 5 folds. The three protocols are explained in §4.3.

**Passwords**

| Protocol | Rows | Logistic regression (acc / AUC) | Random forest (acc / AUC) |
|---|---|---|---|
| With replacement (official, `metrics`) | 20,000 (11,479 distinct strings) | 0.506 ± 0.006 / 0.522 | **0.748 ± 0.003 / 0.816** |
| Grouped by string (`grouped_results`) | 20,000 (11,479 groups) | 0.473 ± 0.038 / 0.443 | **0.545 ± 0.039 / 0.555** |
| Distinct strings only (`distinct_results`) | 5,701 per class | **0.544 ± 0.009 / 0.566** | 0.516 ± 0.004 / 0.531 |

For the official protocol, the random forest's precision is 0.732 and its recall 0.761 ("real" is
the positive class). They come from one extra CV pass with the same features, folds and seed and a
fresh set of decoys. The distinct protocol starts from 6,007 distinct real and 5,701 distinct
decoy strings and subsamples the larger class.

**Usernames** (`classifier.username`)

| Protocol | Rows | Logistic regression (acc / AUC) | Random forest (acc / AUC) |
|---|---|---|---|
| With replacement | 20,000 | 0.739 ± 0.006 / 0.796 | **0.823 ± 0.005 / 0.913** |
| Grouped by string | 20,000 (11,956 groups) | **0.738 ± 0.006 / 0.786** | 0.552 ± 0.085 / 0.706 |
| Distinct strings only | 4,378 per class (of 4,378 real, 7,646 decoy) | **0.762 ± 0.007 / 0.789** | 0.675 ± 0.008 / 0.766 |

### 3.4 Dictionary attack (`demo` profile, 8 entries, 500 guesses from a 629-word list)

| | Conventional (AES-GCM) | Honey vault |
|---|---|---|
| Outcome | **CRACKED at guess #447** (= the real password's rank) | No guess can be singled out |
| Time | 2,925 ms (stops at the crack) | 3,062 ms for all 500 guesses (6.1 ms/guess) |
| Vaults produced | 1 (the real one; all 8 entries recovered) | **500 distinct vaults**, every one well-formed |
| Real password | Recognised by the AEAD tag | Recovers the real 8 entries, with no flag in the output |

### 3.5 KDF and unlock latency (in-process, ms)

| Profile | Params | Derive p50 / p95 | 8-entry unlock p50 / p95 |
|---|---|---|---|
| `default` (new vaults) | t=3, 64 MiB, p=4 | 46.5 / 63.5 | **52.0 / 61.8** |
| `server_lite` (honeywords) | t=2, 19 MiB, p=1 | 26.8 / 28.8 | 27.7 / 30.4 |
| `demo` (attack demo) | t=1, 8 MiB, p=1 | 7.6 / 8.1 | 8.1 / 9.6 |

Unlock time is about one KDF call. Decoding 8 entries adds well under 1 ms.

## 4. Interpretation

### 4.1 What works
- **The DTEs are correct and total.** Every held-out password, username and entry round-trips
  exactly, and no random seed out of 60,000 fails to decode to a valid field. This is the
  property that makes `unlock()` unable to fail on a wrong password (AGENTS.md §1.2–1.3).
- **There is no offline oracle.** The conventional vault confirms the right password the
  moment it is tried (#447). The honey vault returns a complete, well-formed and *different*
  vault for every one of 500 guesses (500 / 500 distinct), and nothing marks the real one.
- **Decoys follow the model** (template goodness of fit p = 0.92 for passwords, 0.31 for
  usernames). **The integer codec is unbiased** (control p = 0.25 and 0.97).
- **Latency is far below target.** p95 is 62 ms against a 1.5 s target, so there is headroom
  to raise the `default` Argon2 cost.

### 4.2 Seed uniformity fails because of model fit, not the codec
On held-out values the seed tests reject uniformity for both models (passwords: p ≈ 10⁻¹² for
bytes, 10⁻⁷² for used ints; usernames: 10⁻⁵⁴ and 10⁻²⁹⁴). The control encodes values *sampled
from the model* through the same codec and passes (p = 0.25 and 0.97). The bias therefore comes
from real values having different frequencies from the model's probabilities, not from the
codec. For passwords the template table shows this directly. 5-digit passwords (`D5`) are 2.6% of
the model but 0.33% of held-out passwords. `D6` is over-weighted (12.0% vs 9.05%), while `L5`
and `L7` are under-weighted (×1.36 and ×1.19). For usernames, the email-domain choice (§4.4)
adds to it: real xato usernames never take a domain, so the first used int of every real seed
falls in the same "no domain" band.

This does not leak through the ciphertext. Seeds are XORed with an AES-CTR keystream, so the
stored bytes are uniform whatever the seed. The mismatch matters at the *decoded* level: real
vaults and decoys come from slightly different distributions. §4.3 and §4.4 measure that.

<a id="43-distinguisher-0741-overall-mostly-from-repeated-strings-partly-from-real-mismatch"></a>

### 4.3 Password distinguisher: 0.748 with repeated strings, ~0.54 without them
All three protocols use the same features, classifiers and 5 folds. They differ in what the
classifier may see.

- **With replacement (official §11 number): 0.748.** Real passwords are drawn *by weight with
  replacement* and decoys are `model.sample()`, so popular strings repeat. The 20,000 rows hold
  only 11,479 distinct strings. Plain stratified folds put copies of the same string in both the
  training and the test fold. Several features are close to unique per string
  (`mean_char_unigram_logprob`, `template_logprob`, `shannon_entropy`), so the random forest can
  memorise "this string was labelled real (or decoy)" and recognise it in the test fold. Logistic
  regression cannot memorise and stays at chance (0.506). The protocol rewards string-level
  memory and frequency differences. An attacker holding a leaked password list has the same
  kind of knowledge, so this stays the official number.
- **Grouped by string: 0.545 (RF), 0.473 (LR).** `StratifiedGroupKFold` with one group per
  distinct string, so every copy of a string, real or decoy, sits in one fold. The test fold
  only holds strings the classifier never saw, still in their real-world proportions.
  Memorisation is impossible, and the forest drops from 0.748 to 0.545. Logistic regression
  lands slightly *below* chance (AUC 0.44). That carries no usable signal. Grouping puts
  popular strings, with hundreds of copies, into a single fold, so the class balance and the
  accuracy swing from fold to fold (sd 0.038 against 0.006 above). 0.473 is about 1.6 standard
  errors below 0.5.
- **Distinct strings only: 0.544 (LR), 0.516 (RF).** Each class is reduced to its distinct
  strings (6,007 real, 5,701 decoy), both subsampled to 5,701, and every string counts once.
  This asks whether decoy passwords *look* different from real ones, whatever their frequency.
  Both classifiers are near chance. The small linear edge fits the template mismatch in §4.2
  (too many all-digit decoys, too few short letter strings).

**Bottom line.** Most of the gap between 0.748 and 0.5 is memorisation of repeated strings: take
it away and the best classifier reaches 0.545 (grouped) or 0.544 (distinct), inside the ≤ 0.60
target. The remaining 4–5 points above chance are a real but small mismatch between the model
and real passwords, the same one the χ² seed tests detect. The decoys' *frequency* distribution
also differs from the real one, and a frequency-aware attacker can use that when ranking
candidate vaults. We report 0.748 as the official §11 number and give the other two alongside
it, not instead of it.

### 4.4 Username distinguisher: the email-domain suffix gives decoys away
With real held-out usernames now available, the username distinguisher runs for the first time,
and it separates real from decoy under every protocol: 0.823 / 0.738 / 0.762 (official /
grouped / distinct, best classifier). Unlike passwords, the signal survives grouping and
deduplication, and logistic regression already finds it, so it is not memorisation.

The cause is the email-domain step of the username model (§7.4). It appends a domain from the
fixed built-in table (`pcfg.email_domain_weights`) to a share of decoys, while the xato corpus is
bare usernames. An ad-hoc check (same seed and n, not part of `latest.json`) confirms it:

| | Real held-out | Decoys |
|---|---|---|
| Contains `@` | 0.0% | 45.3% |
| Mean length | 5.7 | 11.2 |
| Distinct-strings accuracy, decoys with `@domain` removed | — | 0.555 (LR), 0.523 (RF) |

Without the suffix, usernames are as close to chance as passwords. This is a mismatch between
the model and *this test set*. It is not necessarily a mismatch with real vaults, where many
logins are email addresses (one of the eight demo entries is). The held-out set cannot say
whether 45% is the right email share. Two ways forward, both owned by the username DTE track
(Nidhi): calibrate the domain share on login data that includes email addresses, or evaluate
local parts and domains separately.

## 5. Limitations
- **Seed uniformity fails for both models (§4.2).** The codec control passes, so the codec
  is sound. The failure is model fit, so real seeds are not uniform before encryption. The
  ciphertext is unaffected (AES-CTR), but decoded real values and decoys come from different
  distributions. This is an open issue, not fixed by this change.
- **Held-out password weights ≠ training weights.** `heldout_passwords.tsv` is byte-identical
  to the held-out split of `rockyou-withcount` (real counts). The committed password model does
  *not* match a `rockyou-withcount` retrain, which fits its recorded Zipf rank weights. Weighted
  real samples therefore follow real frequencies, while the model follows rank-based ones. Part
  of the frequency mismatch in the official 0.748 and in χ² (a) may come from this. Retraining
  the password model on `rockyou-withcount` and re-running would settle it.
- **Username email share (§4.4)** cannot be validated against xato, which has no email logins.
  The suffix numbers there come from an ad-hoc check, not from `run_all`.
- **Independent fields:** decoy entries are independent, so password reuse across entries is
  not modelled (§13). A distinguisher working at vault level, not per credential, could do
  better than these per-field numbers. This evaluation does not measure that.
- **Latency is in-process,** on a fast laptop (i9-14900HX). It does not include HTTP or
  Render's smaller instances, so §11 asks for a separate measurement on the deployed API.
- **Run-to-run variation:** decoys, salts and the attack password use `secrets`, so the
  classifier and attack numbers vary slightly between runs (fold sd ≈ 0.005 for the plain
  protocols, ≈ 0.04 for grouped CV). The real password's rank in the attack is random.
- **`dataset.training_samples` is `null`:** the model files don't record their training size.

## 6. Reproduction

```bash
# from backend/, venv active. Held-out files in data/processed/ (gitignored):
python scripts/download_corpus.py --passwords none --usernames seclists-xato
python scripts/train_pcfg.py --kind username --input ../data/raw/xato-net-10-million-usernames.txt \
    --format plain --max-lines 1000000 --out /tmp/pcfg_username_tmp.json.gz
#   ^ --out elsewhere keeps the committed model untouched; heldout_usernames.tsv is the output we keep

python -m eval.run_all            # full run (~100 s here), writes eval/results/latest.json
python -m eval.run_all --quick    # tiny sizes; also writes latest.json unless --out given
python -m eval.run_all --quick --out /tmp/quick.json   # leave latest.json untouched

# individual pieces
python -m eval.chi_squared -n 20000
python -m eval.classifier -n 10000   # all three protocols, password + username

# serve it
uvicorn app.main:app --port 8000   # GET /api/eval/summary returns latest.json
```

Options: `--seed N` (default 7), `--heldout-passwords PATH`, `--heldout-usernames PATH`. Tests:
`pytest tests/core/test_run_all.py tests/core/test_classifier.py` (synthetic held-out data,
quick mode).
