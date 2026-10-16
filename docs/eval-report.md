# Evaluation report

> Owner: T1 (Dhruv; chi-squared by Nidhi). Numbers come from `backend/eval/results/latest.json`
> (full run, 2026-10-16T18:35:22Z, `meta.git_commit` `ec8052b` plus this branch's eval changes),
> produced by `python -m eval.run_all` with `pcfg-password-v2` and `pcfg-username-v1`. Metrics
> are defined in PROJECT-BRIEF.md §11. The username seed-uniformity tests fail. The password seed
> tests pass at the int level and narrowly fail at the byte level, but §4.2 shows that neither
> can see the v2 model's misfit. The official password and username distinguisher numbers miss
> their target, and right vs wrong unlock timing differs at the `demo` KDF profile. This report
> gives those numbers unchanged and explains them. Numbers marked *extra check* come from separate
> runs described where they appear, not from `latest.json`.

## Summary

| Check (§11) | Target | Result | Verdict |
|---|---|---|---|
| Round-trip `decode(encode(x)) == x` | 100% | **100%** (25,000 / 25,000, all held-out) | ✅ |
| `decode` totality on random seeds | 100% | **100%** (60,000 seeds, 0 failures) | ✅ |
| χ² (a) seed uniformity, held-out passwords | p > 0.05 | bytes **p = 0.020**, used ints **p = 0.82** (codec control p = 0.73) | ⚠️ bytes ❌ (run-to-run noise), ints ✅; neither test can see v2's misfit (§4.2) |
| χ² (a) seed uniformity, held-out usernames | p > 0.05 | bytes **p = 1.7 × 10⁻⁴⁶**, used ints **p = 1.1 × 10⁻¹⁸⁰** (codec control p = 0.56) | ❌ model fit (§4.2) |
| χ² (b) decoded templates vs model | p > 0.05 | **p = 0.60** passwords, **0.31** usernames | ✅ |
| Password distinguisher, official protocol (best of LR / RF) | ≤ 0.60 (ideal 0.50) | **0.736** (RF), 0.514 (LR) | ❌ |
| Password distinguisher, grouped CV / distinct strings | ≤ 0.60 | **0.526** / **0.541** (best of LR / RF) | ✅ supplementary (§4.3) |
| Username distinguisher, official / grouped / distinct | ≤ 0.60 | **0.821** / **0.718** / **0.736** | ❌ email suffix (§4.4) |
| Username distinguisher **without domain**, official / grouped / distinct | ≤ 0.60 | **0.772** / **0.518** / **0.554** | grouped / distinct ✅ (§4.4) |
| Dictionary attack: conventional vault | cracks | **cracked at guess #252 / 500** | ✅ |
| Dictionary attack: honey vault | no oracle | **500 distinct vaults from 500 guesses** | ✅ |
| Unlock p95, `default` KDF profile | < 1.5 s | **54 ms** (in-process) | ✅ |
| Unlock timing, right vs wrong master password (KS test) | p > 0.05 | **p = 0.79** `default`, **0.71** `server_lite`, **0.0021** `demo` | ✅ `default` / `server_lite`, ❌ `demo` (§4.5) |

### v1 → v2 (password model)

v1 numbers are from the previous version of this report (full run of 2026-10-14, commit `91e3171`).
Two things changed between the runs. The model went from `pcfg-password-v1` (SecLists RockYou,
Zipf-ranked weights) to `pcfg-password-v2` (`rockyou-withcount`, real counts). The held-out file
also changed: it used to be the first 50,000 held-out values in corpus order, which in the
count-sorted `rockyou-withcount` are the most frequent ones, and is now a seeded random sample of
the whole held-out split (§2).

| Password metric | v1 | v2 |
|---|---|---|
| Seed χ², bytes: p | 1.7 × 10⁻¹¹ | 0.020 |
| Seed χ², used ints: p | 1.3 × 10⁻⁷⁹ | 0.822 |
| Template goodness of fit: p | 0.925 | 0.603 |
| Distinguisher, with replacement (official): LR / RF | 0.517 / 0.740 | 0.514 / 0.736 |
| Distinguisher, grouped by string: LR / RF | 0.462 / 0.517 | 0.486 / 0.526 |
| Distinguisher, distinct strings only: LR / RF | 0.544 / 0.507 | 0.541 / 0.506 |
| *Extra check:* PIT seed test, both models on the new held-out sample: χ² (15 dof) | 1,242 (p = 1.5 × 10⁻²⁵⁵) | 1,614 (p < 10⁻³⁰⁰) |

The seed χ² p-values rise by many orders of magnitude, but that is mostly how the codec writes
v2's integer-count weights, not a better fit (§4.2). The PIT row, which does not depend on that,
shows no better fit, and no distinguisher protocol moved by more than 0.025.

## 1. Method

`backend/eval/run_all.py` runs every §11 measurement against the **real** honeycore through
`load_honeycore("real")`. It never uses the stub, whatever `HONEYCORE_IMPL` says, and writes one
strict-JSON file that `GET /api/eval/summary` serves.

| Section | What runs | Sample size (full) |
|---|---|---|
| `round_trip` | encode → decode on held-out passwords, held-out usernames and (username, password) entries; decode on uniform random seeds for the password, username and entry DTEs | 10,000 / 10,000 / 5,000; 20,000 seeds per DTE |
| `chi_squared` | `eval.chi_squared` (owner Nidhi): seed-byte (256 bins) and seed-int (top 4 bits, 16 bins) uniformity of encoded held-out values; codec control on model samples; template goodness of fit of decoded random seeds (top 50 templates + "other"); password and username models | n = 20,000 |
| `classifier` | `eval.classifier.run`: real held-out vs `model.sample()` decoys, 12 features, standardised logistic regression and 200-tree random forest, 5-fold CV under three protocols (§4.3). Usernames run twice: as stored, and `without_domain` (§4.4) | 10,000 per class |
| `attack` | `attack.simulator` on a fresh `demo`-profile honey vault and conventional vault with the same 8 synthetic entries; demo wordlist; real master password inserted at a random rank | 500 guesses |
| `kdf` | Argon2id derive time and 8-entry `HoneyVault.unlock` time per KDF profile | 15 reps per profile |
| `timing` | 8-entry `HoneyVault.unlock` with the right vs a fresh wrong master password, interleaved, per KDF profile; two-sample Kolmogorov-Smirnov test; a second right sample as A/A control; entry-DTE decode alone on real vs random seeds (§4.5) | 200 per class per profile; 2,000 decode rounds |

`meta` also records the sha256 of the two model files the loader read (`meta.model_sha256`) and of
the two held-out files (`meta.heldout_sha256`, `null` if a file is missing), never their contents.

A "pass" for a χ² or KS test means p > 0.05, i.e. the test found no evidence of a difference.
The distinguisher's headline accuracy is the **stronger** of the two classifiers. An attacker
would use the better tool, so that is the honest number.

## 2. Setup

| Item | Value |
|---|---|
| Corpus | Passwords: RockYou `rockyou-withcount` (frequency list), first 1,000,000 lines, real counts as weights, §7.3. Usernames: SecLists `xato-net-10-million-usernames`, first 1,000,000 lines, Zipf-ranked weights (`w ∝ 1/rank^0.9`), §7.4 |
| Training values | 796,251 passwords, 796,674 usernames (from the `train_pcfg.py` summary; the model files do not record it) |
| Held-out split | `pcfg.is_heldout` (sha256-based, ~20%), never trained on: 203,433 password and 203,317 username values among the lines read |
| Held-out sample | `data/processed/heldout_passwords.tsv` and `heldout_usernames.tsv`: a seeded uniform random sample of the held-out split (reservoir sampling, `random.Random(7)`), **50,000 values each**, written in corpus order with their weights (real counts for passwords, Zipf weights for usernames) |
| Held-out sha256 (`meta.heldout_sha256`) | passwords `c7bb2093aa39e0956e6a657de566325e667ea7bc809d43c122c5f78a792272ff`; usernames `29355460e52169cd3310b863f8ce42f4dadaa4a2aa6b5df6de7a4b5f3dc46629` |
| How the held-out files were made | `train_pcfg.py` per kind with `--out` pointing at a temporary file (§7). Both temporary models are byte-identical to the committed ones, so each split is exactly the one the committed model never saw |
| Models (`meta.model_sha256`) | `pcfg-password-v2`, sha256 `8b225bb35d85624a2da1f4a3611574f2895336030660f2a838a63a3f159e76a6`; `pcfg-username-v1`, sha256 `ec5ffa2dfe40b0f469e8fe1ec74b37f67eb7b03e720edbe3abe9f89a57a26578`. Entry seed 532 B (268 + 264) |
| Entry DTE | `honeycore.dte.entry_dte.PCFGEntryDTE` (`meta.entry_dte_impl`), the same one the vault uses |
| KDF profiles | `default` t=3, 64 MiB, p=4; `server_lite` t=2, 19 MiB, p=1; `demo` t=1, 8 MiB, p=1 |
| Hardware | Intel Core i9-14900HX, 16 GB RAM, Windows 11, Python 3.12.10 (scikit-learn 1.9.1, SciPy 1.18.1, NumPy 2.5.3) |
| Seed | 7 (NumPy RNG for held-out sampling, random seeds, CV folds). Decoys, salts, nonces, the codec's choice of seed ints, and the attack and timing passwords use `secrets`, so χ² seed, classifier, attack and timing numbers vary slightly between runs. |
| Runtime | 213 s (classifier 133 s, timing 57 s) |

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
| password | seed byte uniformity (held-out) | 20,000 | 303.3 | 255 | 0.020 | ❌ (narrow; §4.2) |
| password | seed int uniformity (held-out, used ints) | 20,000 | 10.0 | 15 | 0.822 | ✅ (§4.2) |
| password | seed int uniformity **control** (model samples) | 20,000 | 11.3 | 15 | 0.733 | ✅ |
| password | template goodness of fit (decoded random seeds) | 20,000 | 46.8 | 50 | 0.603 | ✅ |
| username | seed byte uniformity (held-out) | 20,000 | 724.0 | 255 | 1.7 × 10⁻⁴⁶ | ❌ |
| username | seed int uniformity (held-out, used ints) | 20,000 | 893.0 | 15 | 1.1 × 10⁻¹⁸⁰ | ❌ |
| username | seed int uniformity **control** (model samples) | 20,000 | 13.6 | 15 | 0.555 | ✅ |
| username | template goodness of fit | 20,000 | 54.5 | 50 | 0.306 | ✅ |

Top password templates. "Model" is P(PCFG) × P(template). "Decoys" is 20,000 decoded random
seeds. "Held-out" is 20,000 held-out values drawn by weight (real counts).

| Template | Model | Decoys | Held-out | Held-out ÷ model |
|---|---|---|---|---|
| L6 (6 letters) | 20.18% | 20.14% | 22.14% | 1.10 |
| L7 | 12.47% | 12.37% | 11.07% | 0.89 |
| D6 (6 digits) | 10.84% | 10.82% | 9.11% | 0.84 |
| L8 | 10.27% | 10.60% | 11.73% | 1.14 |
| L9 | 5.08% | 4.95% | 4.83% | 0.95 |
| L5 | 4.81% | 5.04% | 4.58% | 0.95 |
| L6D1 | 3.17% | 3.26% | 3.06% | 0.96 |
| L6D2 | 2.86% | 2.86% | 3.03% | 1.06 |
| L5D2 | 2.67% | 2.36% | 2.89% | 1.08 |
| L10 | 2.60% | 2.54% | 2.50% | 0.96 |
| L5D1 | 2.52% | 2.53% | 2.35% | 0.94 |
| L4D2 | 2.36% | 2.46% | 2.38% | 1.01 |
| L7D1 | 2.24% | 2.20% | 2.20% | 0.98 |
| D8 (8 digits) | 2.05% | 2.10% | 2.26% | 1.10 |
| L8D1 | 1.29% | 1.27% | 2.02% | **1.58** |

Every top-15 ratio is between 0.84 and 1.14 except `L8D1` (1.58). v1's largest outlier, `D5`
(5 digits, held-out ÷ model 0.13), is no longer in the top 15.

### 3.3 Distinguisher (10,000 real vs 10,000 decoys per field, 5-fold CV)

Accuracy is mean ± sd over the 5 folds. The three protocols are explained in §4.3.

**Passwords**

| Protocol | Rows | Logistic regression (acc / AUC) | Random forest (acc / AUC) |
|---|---|---|---|
| With replacement (official, `metrics`) | 20,000 (12,353 distinct strings) | 0.514 ± 0.006 / 0.518 | **0.736 ± 0.004 / 0.808** |
| Grouped by string (`grouped_results`) | 20,000 (12,353 groups) | 0.486 ± 0.015 / 0.470 | **0.526 ± 0.013 / 0.535** |
| Distinct strings only (`distinct_results`) | 5,632 per class | **0.541 ± 0.003 / 0.549** | 0.506 ± 0.006 / 0.514 |

For the official protocol, the random forest's precision is 0.727 and its recall 0.755 ("real" is
the positive class). They come from one extra CV pass with the same features, folds and seed and a
fresh set of decoys. The distinct protocol starts from 5,632 distinct real and 6,798 distinct
decoy strings and subsamples the larger class.

**Usernames, as stored** (`classifier.username`)

| Protocol | Rows | Logistic regression (acc / AUC) | Random forest (acc / AUC) |
|---|---|---|---|
| With replacement | 20,000 | 0.718 ± 0.007 / 0.750 | **0.821 ± 0.003 / 0.908** |
| Grouped by string | 20,000 (12,581 groups) | **0.718 ± 0.005 / 0.719** | 0.630 ± 0.037 / 0.732 |
| Distinct strings only | 4,908 per class (of 4,908 real, 7,696 decoy) | **0.736 ± 0.006 / 0.780** | 0.693 ± 0.010 / 0.765 |

**Usernames, known email domain stripped** (`classifier.username.without_domain`)

Same real sample (seed 7), fresh decoys. Before features, `eval.classifier.strip_known_domain`
removes `@domain` from any value whose domain is in the username model's own domain table, using
the model's §7.4 split (`pcfg.split_email`); other values are unchanged. It changed 0 of 10,000
real values and 4,589 of 10,000 decoys (45.9%) (`without_domain.transformed`).

| Protocol | Rows | Logistic regression (acc / AUC) | Random forest (acc / AUC) |
|---|---|---|---|
| With replacement | 20,000 | 0.538 ± 0.006 / 0.565 | **0.772 ± 0.006 / 0.859** |
| Grouped by string | 20,000 (11,024 groups) | **0.518 ± 0.045 / 0.533** | 0.498 ± 0.041 / 0.503 |
| Distinct strings only | 4,908 per class (of 4,908 real, 6,142 decoy) | **0.554 ± 0.010 / 0.579** | 0.524 ± 0.005 / 0.537 |

### 3.4 Dictionary attack (`demo` profile, 8 entries, 500 guesses from a 629-word list)

| | Conventional (AES-GCM) | Honey vault |
|---|---|---|
| Outcome | **CRACKED at guess #252** (= the real password's rank) | No guess can be singled out |
| Time | 1,771 ms (stops at the crack) | 3,516 ms for all 500 guesses (7.0 ms/guess) |
| Vaults produced | 1 (the real one; all 8 entries recovered) | **500 distinct vaults**, every one well-formed |
| Real password | Recognised by the AEAD tag | Recovers the real 8 entries, with no flag in the output |

### 3.5 KDF and unlock latency (in-process, ms)

| Profile | Params | Derive p50 / p95 | 8-entry unlock p50 / p95 |
|---|---|---|---|
| `default` (new vaults) | t=3, 64 MiB, p=4 | 52.7 / 108.1 | **51.1 / 54.1** |
| `server_lite` (honeywords) | t=2, 19 MiB, p=1 | 31.7 / 69.4 | 27.4 / 29.0 |
| `demo` (attack demo) | t=1, 8 MiB, p=1 | 7.2 / 10.8 | 10.2 / 35.7 |

Unlock time is about one KDF call. Decoding 8 entries adds well under 1 ms. With 15 reps the p95
is one or two slow calls. In this run `demo`'s unlock p95 (35.7 ms) is far above its derive p95
(10.8 ms), and the previous run's `default` unlock p95 was 151.5 ms against 54.1 ms here. The
200-sample p50s in §3.6 are the steadier numbers (`demo` 5.6 ms, `default` 52.0 ms).

### 3.6 Unlock timing: right vs wrong master password (`timing`, in-process, ms)

200 right and 200 wrong unlocks per profile on a fresh 8-entry vault, interleaved (order reversed
every other round); each wrong password is fresh and random, same length as the right one. "A/A"
compares the right sample with a second right sample taken in the same rounds.

| Profile | Right p50 / p95 | Wrong p50 / p95 | KS D | KS p (right vs wrong) | A/A control p | Same distribution |
|---|---|---|---|---|---|---|
| `default` | 52.01 / 145.26 | 51.87 / 140.81 | 0.065 | **0.793** | 0.997 | ✅ |
| `server_lite` | 22.72 / 31.58 | 22.65 / 30.52 | 0.070 | **0.713** | 0.866 | ✅ |
| `demo` | 5.62 / 6.22 | 5.56 / 6.05 | 0.185 | **0.0021** | 0.394 | ❌ |

Decode alone (`timing.decode_only_us`, 2,000 interleaved rounds, entry DTE only, no KDF): the 8
real entry seeds decode in **84.3 µs** p50 (p95 138.8), 8 random seeds in **45.4 µs** p50 (p95
60.5), KS p < 10⁻³⁰⁰. §4.5 explains what this does and does not leak.

## 4. Interpretation

### 4.1 What works
- **The DTEs are correct and total.** Every held-out password, username and entry round-trips
  exactly, and no random seed out of 60,000 fails to decode to a valid field. This is the
  property that makes `unlock()` unable to fail on a wrong password (AGENTS.md §1.2–1.3).
- **There is no offline oracle.** The conventional vault confirms the right password the
  moment it is tried (#252). The honey vault returns a complete, well-formed and *different*
  vault for every one of 500 guesses (500 / 500 distinct), and nothing marks the real one. §5
  traces why in the code.
- **Decoys follow the model** (template goodness of fit p = 0.60 for passwords, 0.31 for
  usernames). **The integer codec is unbiased** (control p = 0.73 and 0.56).
- **Latency is far below target.** p95 is 54 ms against a 1.5 s target, so there is headroom
  to raise the `default` Argon2 cost.
- **No detectable timing difference at the profiles real vaults use.** Right and wrong unlocks
  have the same latency distribution at `default` (p = 0.79) and `server_lite` (p = 0.71).

### 4.2 Seed uniformity: usernames fail; the password pass does not show a better fit

**Usernames fail both seed tests.** With the held-out usernames now a random sample of the
held-out split, `pcfg-username-v1` fails: bytes χ² = 724.0 (255 dof), **p = 1.7 × 10⁻⁴⁶**;
used ints χ² = 893.0 (15 dof), **p = 1.1 × 10⁻¹⁸⁰**. On the old held-out file (the first
50,000 held-out values) the previous report had p = 5.1 × 10⁻⁷⁶ and 6.0 × 10⁻²⁸². The new
sample gives smaller χ² values, but both tests still fail by a very wide margin. The codec
control passes (p = 0.555), and decoys follow the model (template goodness of fit p = 0.306), so
the cause is model fit: real xato usernames have different frequencies from the model's
probabilities.

**How the codec hides or shows a misfit.** `encode_choice` (§7.2) writes a choice as
`r = v + T·k`. Here `T` is the distribution's integer total, `v` is uniform in the chosen
symbol's slice of `[0, T)`, and `k` is a uniform multiple of `T` that fills the rest of the
32 bits.
- When `T` is close to 2³¹, the top bits of `r` are the top bits of `v`, so they show which part
  of the distribution real values land in. A frequency mismatch then shows up in the int test
  (top 4 bits) and in the byte test.
- When `T` is far below 2²⁸, the top 4 bits come mostly from `k` and are close to uniform
  whatever `v` is. The mismatch is still in `r mod T`, but these two tests barely look there.

The username model's template, segment and character distributions all have totals of 2³¹
(Zipf float weights, scaled by `rescale` to `MAX_TOTAL`), so its int test is fully sensitive.
Its email-domain choice has a total of about 2¹², so that choice cannot move the int test. **The
username int failure therefore comes from the local-part PCFG block, not from the email-domain
step.** Fixing the domain share alone would not make it pass.

**Passwords: why the v2 pass does not show a better fit.** `pcfg-password-v2` passes the int
test (χ² = 10.0, p = 0.822) and narrowly fails the byte test (χ² = 303.3, p = 0.020). v1 failed
both (p = 1.7 × 10⁻¹¹ and 1.3 × 10⁻⁷⁹). v1's distributions had totals of 2³¹, like the username
model's. v2's weights are integer counts that `rescale` keeps unchanged, so every v2 total is at
most 2^26.6 (templates 2^23.75, segment buckets at most 2^21.5). For v2 the two tests mostly see
`k`. An extra check settles whether the fit actually improved:

*Extra check (not in `latest.json`).* A randomized probability-integral transform of every used
int, `u = (r mod T + U) / T` with `U` uniform on [0, 1), is exactly uniform when real values
follow the model, whatever `T`. Same held-out sample as `latest.json` (n = 20,000, seed 7), 16
bins over about 130,000 used password ints and 164,000 username ints:

| Model | PIT χ² on held-out (15 dof) | PIT on model samples (control) |
|---|---|---|
| `pcfg-password-v2` | 1,614, p < 10⁻³⁰⁰ | p = 0.734 |
| `pcfg-password-v1` (file from git history) | 1,242, p = 1.5 × 10⁻²⁵⁵ | p = 0.568 |
| `pcfg-username-v1` | 2,986, p < 10⁻³⁰⁰ | p = 0.690 |

- By this test v2 fits held-out passwords no better than v1 does on the same values (larger χ²).
- The sampling change does not explain the v1 → v2 difference: v1 on the new sample still fails
  the byte and int tests (p = 2.1 × 10⁻⁸ and 1.7 × 10⁻¹¹¹).
- The byte failure in `latest.json` (p = 0.020) is run-to-run noise. The codec draws `v` and `k`
  from `secrets`, and re-encoding the same sample 10 times gave p = 0.11 to 0.83, none below
  0.05. In those 10 runs the byte test did not detect the misfit that the PIT finds.

**What this means.** The stored ciphertext is uniform either way, because seeds are XORed with an
AES-CTR keystream. What matters is whether decoded real values and decoys come from the same
distribution, which §4.3 and §4.4 measure. An attacker who knows the model can compute `r mod T`
from a seed just as the PIT does. So v2 passing the raw-bit tests does not make v2 vaults harder
to tell apart, and the password distinguisher numbers barely moved (§4.3). Training on real counts
did remove the training/held-out weight mismatch listed in the previous report. The top-15
template ratios now range from 0.84 to 1.58, against 0.13 to 1.36 for v1 (§3.2).

**For the username v2 decision:** judge a candidate model by the distinguisher and by a seed test
that does not depend on `T`, such as the PIT above, not by the current byte and int tests. A model
whose integer weights have small totals would pass those tests for the same reason password v2
does. Adding a PIT test to `eval.chi_squared` (owner Nidhi) would put it in every run.

<a id="43-distinguisher-0741-overall-mostly-from-repeated-strings-partly-from-real-mismatch"></a>

### 4.3 Password distinguisher: 0.736 with repeated strings, ~0.53–0.54 without them
All three protocols use the same features, classifiers and 5 folds. They differ in what the
classifier may see. Every v2 number is within 0.025 of its v1 value (Summary, v1 → v2).

- **With replacement (official §11 number): 0.736.** Real passwords are drawn *by weight with
  replacement* and decoys are `model.sample()`, so popular strings repeat. The 20,000 rows hold
  only 12,353 distinct strings, and real draws repeat more than decoys (5,632 distinct strings
  among 10,000 real draws, 6,798 among 10,000 decoys). Plain stratified folds put copies of the
  same string in both the training and the test fold. Several features are close to unique per
  string (`mean_char_unigram_logprob`, `template_logprob`, `shannon_entropy`), so the random
  forest can memorise "this string was labelled real (or decoy)" and recognise it in the test
  fold. Logistic regression cannot memorise and stays near chance (0.514). The protocol rewards
  string-level memory and frequency differences. An attacker holding a leaked password list has
  the same kind of knowledge, so this stays the official number.
- **Grouped by string: 0.526 (RF), 0.486 (LR).** `StratifiedGroupKFold` with one group per
  distinct string, so every copy of a string, real or decoy, sits in one fold. The test fold
  only holds strings the classifier never saw, still in their real-world proportions.
  Memorisation is impossible, and the forest drops from 0.736 to 0.526. Logistic regression
  lands slightly *below* chance (AUC 0.47), about 2 standard errors below 0.5. That carries no
  usable signal. Grouping puts popular strings, with many copies, into a single fold, so the
  class balance and the accuracy vary from fold to fold (sd 0.015 against 0.006 above).
- **Distinct strings only: 0.541 (LR), 0.506 (RF).** Each class is reduced to its distinct
  strings (5,632 real, 6,798 decoy), both subsampled to 5,632, and every string counts once.
  This asks whether decoy passwords *look* different from real ones, whatever their frequency.
  Both classifiers are near chance. The small linear edge is consistent with the remaining
  model misfit (§4.2) and template gaps such as `L8D1` (§3.2).

**Bottom line.** Most of the gap between 0.736 and 0.5 is memorisation of repeated strings: take
it away and the best classifier reaches 0.526 (grouped) or 0.541 (distinct), inside the ≤ 0.60
target. The remaining 3–4 points above chance are a real but small mismatch between the model
and real passwords. Retraining on real counts did not shrink it, which matches the PIT result in
§4.2. The decoys' *frequency* distribution also differs from the real one (real draws repeat
more), and a frequency-aware attacker can use that when ranking candidate vaults. We report 0.736
as the official §11 number and give the other two alongside it, not instead of it.

### 4.4 Username distinguisher: the email-domain suffix gives decoys away
As stored, real and decoy usernames separate under every protocol: 0.821 / 0.718 / 0.736
(official / grouped / distinct, best classifier). Unlike passwords, the signal survives grouping
and deduplication, and logistic regression already finds it, so it is not memorisation.

The cause is the email-domain step of the username model (§7.4). It appends a domain from the
fixed built-in table (`pcfg.email_domain_weights`) to a share of decoys, while the xato corpus is
bare usernames. The `without_domain` run in `latest.json` measures this:

| | As stored | Known domain stripped |
|---|---|---|
| Values changed by stripping | — | real 0 / 10,000, decoys 4,589 / 10,000 |
| With replacement (best) | 0.821 (RF) | 0.772 (RF); LR 0.718 → **0.538** |
| Grouped by string (best) | 0.718 (LR) | **0.518** (LR) |
| Distinct strings only (best) | 0.736 (LR) | **0.554** (LR) |

Without the suffix, grouped and distinct accuracy fall inside the ≤ 0.60 target and close to the
password numbers. What remains is the same pattern as §4.3: logistic regression's
with-replacement accuracy drops to 0.538, so most of the forest's 0.772 is memorisation of
repeated strings, and a few points of real local-part mismatch are left. §4.2 shows that the
local part also misfits at the seed level (int test p = 1.1 × 10⁻¹⁸⁰, which the domain step
cannot cause). With 20,000 values the χ² test detects that misfit easily, but per value it is
small (0.518 grouped, 0.554 distinct).

This is a mismatch between the model and *this test set*. It is not necessarily a mismatch with
real vaults, where many logins are email addresses (one of the eight demo entries is). The
held-out set cannot say whether ~45% is the right email share. Stripping is an analysis tool,
not a fix: the deployed DTE still emits the suffix, so the as-stored numbers are the honest ones
for this test set. Two ways forward, both owned by the username DTE track (Nidhi): calibrate the
domain share on login data that includes email addresses, or evaluate local parts and domains
separately. On this test set, a username v2 would have to change the domain step (for the
as-stored distinguisher) and fit local parts better (for the seed tests).

### 4.5 Timing: no difference at `default`; a small, value-dependent decode cost
At `default` and `server_lite` the KS test finds no difference between right and wrong unlocks
(p = 0.79 and 0.71). The A/A controls (0.997, 0.87) show the test is not over-sensitive here.

`demo` rejects in `latest.json`: p = 0.0021 (KS D = 0.185), with right unlocks about 0.06 ms
slower at p50, while its A/A control passes (p = 0.39). The previous report's run passed narrowly
(p = 0.088), and four development runs before it all rejected (p = 0.001 to 0.012). We read
`demo` as a real, small effect and `default` as no effect.

`decode_only_us` explains the effect. Decoding the 8 real entries takes about 39 µs longer than
decoding 8 random seeds (84.3 vs 45.4 µs p50). The decode does **not** exit early: it always
decodes every entry, and no branch depends on whether the key is right (§5). But how much work
it does depends on the *decoded value*. `_PCFGBase._decode_block` reads more codec choices for a
value spelled character by character (the chars fallback, or a template not in the model) than
for a common bucket word. The demo entries are deliberately unusual strings (`Gh!tide2026`,
`cl0ud&Rain!`), and random seeds mostly decode to common templates. 39 µs is about 0.7% of a
`demo` unlock and lost in the KDF's jitter at `default` (p95 − p50 ≈ 93 ms in this run).

What it leaks: decode time is, up to small noise, a function of the decoded vault, and every
unlock already returns that decoded vault. Timing tells an attacker roughly what the output
already tells them: how "model-typical" the decoded credentials are, the mismatch §4.3–4.4
measure. It is not a "correct password?" oracle. A strict reading of AGENTS.md §1.2 ("timing
class") would still want constant work. A constant-work decode (always consume every seed int)
is an option for honeycore (T1) if `demo` ever runs on a deployed instance.

## 5. Invariant audit: the honey-vault decrypt path

Traced from the API to the DTE (AGENTS.md §1.1–1.4) at commit `91e3171`. Re-checked at `ec8052b`:
the only change on this path since then is the password model id and file name
(`dte/password_dte.py` `MODEL_ID` / `DEFAULT_MODEL_PATH`, `vault.py` `DEFAULT_MODEL_IDS`).

| Step | Code (file:function) | MAC / tag / padding / checksum? | Depends on whether the key is right? |
|---|---|---|---|
| API | `backend/app/api/vault.py:unlock_vault_endpoint` | none | No. Always 200 with the same `UnlockResponse` shape; never logs the body |
| Service | `backend/app/services/vault_service.py:unlock_vault` | none | No. Loads the vault and returns `vault.unlock(...)`, no branch on the result |
| Vault | `backend/honeycore/vault.py:HoneyVault.unlock` | none | No. Derives the key once, then decrypts and decodes **every** entry in a plain loop: no comparison, no `break`, no `try` |
| KDF | `HoneyVault._keys` → `vault.py:_kdf_password` → `backend/honeycore/kdf.py:Argon2KDF.derive` → `kdf.py:derive_subkeys` | none; nothing derived is stored | No. `_kdf_password` maps lone surrogates so encoding cannot fail. `derive` checks only the salt length, which `from_dict` fixes. `derive_subkeys` is HMAC-SHA256 with fixed labels |
| Cipher | `backend/honeycore/cipher.py:AESCTRCipher.apply` | none: AES-256-CTR, no tag, length-preserving | No. Checks only the key (always 32 B) and nonce (16 B, fixed at load) lengths |
| Entry DTE | `backend/honeycore/dte/entry_dte.py:PCFGEntryDTE.decode` | none | No. Checks only that the seed is `ENTRY_SEED_LEN` (532 B), which `from_dict` and CTR guarantee |
| Field DTEs | `dte/username_dte.py:PCFGUsernameModel.decode`, `dte/password_dte.py:PCFGPasswordModel.decode` → `dte/pcfg.py:_PCFGBase._decode_block` → `dte/int_codec.py:decode_choice` | none: no padding or checksum to verify | No early exit. `decode_choice` is `bisect_right(cum, r % total)`, defined for every 32-bit int. The *amount* of work depends on the decoded value (§4.5) |
| Sigil | `backend/honeycore/sigil.py:compute_sigil` | none | No. Any 32-byte key gives a sigil; it raises only for a wrong key length, which `derive_subkeys` cannot produce |
| Blob | `vault.py:HoneyVault.to_dict` / `from_dict` | none: entries hold only id, service, nonce, ciphertext, timestamps; no verifier or key hash | `from_dict` errors depend only on the blob, never on a password |

Findings:
- **No integrity check anywhere on the path.** There is no MAC, tag, padding check, checksum,
  magic bytes or stored verifier, so any password yields some seed, and the total DTE turns it
  into a well-formed vault. §3.1 tests that totality (60,000 random seeds, 0 failures). §3.4
  shows the consequence (500 / 500 distinct vaults).
- **No early exit on a wrong key.** Every entry is always decrypted and decoded. The only checks
  that can raise are lengths fixed when the blob is loaded, never anything derived from the
  password.
- **Timing:** no measurable right-vs-wrong difference at `default` or `server_lite` (KS p = 0.79,
  0.71). At `demo`, a small value-dependent decode cost (~39 µs per 8 entries) is detectable
  (p = 0.0021 in this run). It reflects the decoded output, not a key check (§4.5).

The AES-GCM uses (`honeycore/baseline.py` conventional vault, share envelopes, key wrapping) are
outside this path, as AGENTS.md §1.9 allows.

## 6. Limitations
- **Seed uniformity (§4.2).** The username model fails both seed tests (p = 1.7 × 10⁻⁴⁶ and
  1.1 × 10⁻¹⁸⁰). The password model passes the int test, and its byte-test failure is run-to-run
  noise, but neither test can see a misfit when the distribution totals are small, as all of
  v2's are; the PIT extra check rejects both models. The codec control passes, so the codec is sound and
  the failures are model fit. The ciphertext is unaffected (AES-CTR), but decoded real values and
  decoys come from different distributions. This is an open issue.
- **Username email domain (§4.4).** The deployed username DTE adds a known email domain to about
  45% of decoys, and no real xato username has one. As stored, usernames miss the target under
  every protocol (best 0.821 / 0.718 / 0.736). `without_domain` shows that the suffix is the
  cause; it does not fix it. xato cannot tell us the right email share. The username DTE track
  owns this.
- **Value-dependent decode time (§4.5).** Not a key oracle, but the decode is not constant-work.
  It is detectable at `demo` (p = 0.0021 here) and not at `default`.
- **Independent fields:** decoy entries are independent, so password reuse across entries is
  not modelled (§13). A distinguisher working at vault level, not per credential, could do
  better than these per-field numbers. This evaluation does not measure that.
- **Latency and timing are in-process,** on a fast laptop (i9-14900HX) that was not otherwise
  idle. They do not include HTTP, the honeychecker, or Render's smaller instances, where network
  jitter would hide a 39 µs difference but could add others. §11 asks for a separate measurement
  on the deployed API. The 15-rep `kdf` p95 is sensitive to one or two slow calls (§3.5).
- **Run-to-run variation:** decoys, salts, the codec's seed ints and the attack and timing
  passwords use `secrets`, so the χ² seed, classifier, attack and timing numbers vary between runs
  (fold sd ≈ 0.003–0.010 for the plain protocols, up to 0.045 for grouped CV; the password byte
  χ² p-value ranged from 0.02 to 0.83; the `demo` KS p-value from 0.001 to 0.09). The real
  password's rank in the attack is random.
- **`dataset.training_samples` is `null`:** the model files don't record their training size
  (§2 gives it from the `train_pcfg.py` summary).

## 7. Reproduction

```bash
# from backend/, venv active. Corpora in data/raw/, held-out files in data/processed/ (gitignored):
python scripts/download_corpus.py --passwords rockyou-withcount --usernames seclists-xato

python scripts/train_pcfg.py --kind password --input ../data/raw/rockyou-withcount.txt.bz2 \
    --format withcount --max-lines 1000000 --out /tmp/pcfg_password_tmp.json.gz
python scripts/train_pcfg.py --kind username --input ../data/raw/xato-net-10-million-usernames.txt \
    --format plain --max-lines 1000000 --out /tmp/pcfg_username_tmp.json.gz
#   ^ --out elsewhere keeps the committed models untouched; data/processed/heldout_*.tsv are the
#     outputs we keep. train_pcfg.py also prints both sha256 digests.

# sha256 check (PowerShell: Get-FileHash -Algorithm SHA256 <file>)
sha256sum /tmp/pcfg_password_tmp.json.gz honeycore/models/pcfg_password_v2.json.gz
#   both 8b225bb35d85624a2da1f4a3611574f2895336030660f2a838a63a3f159e76a6
sha256sum /tmp/pcfg_username_tmp.json.gz honeycore/models/pcfg_username_v1.json.gz
#   both ec5ffa2dfe40b0f469e8fe1ec74b37f67eb7b03e720edbe3abe9f89a57a26578
sha256sum ../data/processed/heldout_passwords.tsv ../data/processed/heldout_usernames.tsv
#   c7bb2093aa39e0956e6a657de566325e667ea7bc809d43c122c5f78a792272ff  (meta.heldout_sha256.passwords)
#   29355460e52169cd3310b863f8ce42f4dadaa4a2aa6b5df6de7a4b5f3dc46629  (meta.heldout_sha256.usernames)

python -m eval.run_all            # full run (~215 s here), writes eval/results/latest.json
python -m eval.run_all --quick    # tiny sizes; also writes latest.json unless --out given
python -m eval.run_all --quick --out /tmp/quick.json   # leave latest.json untouched

# individual pieces
python -m eval.chi_squared -n 20000
python -m eval.classifier -n 10000   # three protocols, password + username (as stored only)

# serve it
uvicorn app.main:app --port 8000   # GET /api/eval/summary returns latest.json
```

Options: `--seed N` (default 7), `--heldout-passwords PATH`, `--heldout-usernames PATH`. Tests:
`pytest tests/core/test_run_all.py tests/core/test_classifier.py` (synthetic held-out data,
quick mode). The PIT extra check in §4.2 is not part of the repo; it uses the formula given
there on the same `sample_heldout(..., n=20000, seed=7)` values.
